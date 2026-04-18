"""Camera motion analysis: optical flow + homography decomposition + compound motion."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from director.config import get_config
from director.perception.base import PerceptionPipeline
from director.structure.schema import CameraMotion, ShotBoundary

log = logging.getLogger(__name__)


class CameraAnalyzer(PerceptionPipeline):
    name = "camera"

    def __init__(self):
        self._ort_session = None
        self._use_raft = False

    def load_model(self) -> None:
        cfg = get_config()
        raft_path = cfg.models_dir / "raft" / "raft_small.onnx"

        if raft_path.exists():
            try:
                import onnxruntime as ort
                from director.utils.device import get_onnx_providers
                providers = get_onnx_providers()
                self._ort_session = ort.InferenceSession(str(raft_path), providers=providers)
                self._use_raft = True
                log.info("RAFT-Small ONNX loaded with providers: %s", providers)
                return
            except Exception as e:
                log.warning("RAFT ONNX load failed: %s", e)

        log.info("Using OpenCV Farneback optical flow (fallback)")
        self._use_raft = False

    def unload_model(self) -> None:
        self._ort_session = None

    def estimate_memory_gb(self) -> float:
        return 1.5 if self._use_raft else 0.5

    def process(
        self,
        video_path: str | Path,
        shots: list[ShotBoundary],
        fps: float = 0,
    ) -> dict[int, CameraMotion]:
        cfg = get_config()
        results = {}
        for shot in shots:
            motion = self._analyze_shot(video_path, shot, cfg)
            results[shot.shot_index] = motion
        return results

    def _analyze_shot(self, video_path, shot, cfg) -> CameraMotion:
        from director.input.decoder import decode_frames

        frames = decode_frames(
            video_path,
            fps=cfg.analysis_fps,
            max_height=cfg.flow_resize_height,
            start_sec=shot.start_sec,
            end_sec=shot.end_sec,
        )

        if len(frames) < 2:
            return CameraMotion(type="static", intensity=0.0)

        # Compute per-pair analysis
        pair_results = []
        for i in range(len(frames) - 1):
            pair = self._analyze_pair(frames[i], frames[i + 1], cfg)
            if pair is not None:
                pair_results.append(pair)

        if not pair_results:
            return CameraMotion(type="static", intensity=0.0)

        return self._aggregate_pairs(pair_results)

    def _analyze_pair(self, frame1: np.ndarray, frame2: np.ndarray, cfg) -> dict | None:
        """Analyze a single frame pair: flow + homography decomposition."""
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_RGB2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_RGB2GRAY)

        # Compute optical flow
        if self._use_raft and self._ort_session is not None:
            flow = self._compute_flow_raft(frame1, frame2)
        else:
            flow = cv2.calcOpticalFlowFarneback(
                gray1, gray2, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )

        if flow is None:
            return None

        h, w = flow.shape[:2]

        # ── Homography decomposition for precise camera motion ──
        homography_result = self._decompose_homography(gray1, gray2, cfg)

        # ── Flow statistics ──
        mean_dx = float(np.mean(flow[:, :, 0]))
        mean_dy = float(np.mean(flow[:, :, 1]))
        magnitude = float(np.sqrt(mean_dx**2 + mean_dy**2))

        # Zoom signal: radial flow divergence
        cx, cy = w / 2, h / 2
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        radial_x = ((x_coords - cx) / (w / 2 + 1e-6)).astype(np.float32)
        radial_y = ((y_coords - cy) / (h / 2 + 1e-6)).astype(np.float32)
        radial_norm = np.sqrt(radial_x**2 + radial_y**2 + 1e-6)
        radial_x /= radial_norm
        radial_y /= radial_norm
        zoom_signal = float(np.mean(flow[:, :, 0] * radial_x + flow[:, :, 1] * radial_y))

        # Rotation signal: tangential flow
        tang_x = -radial_y
        tang_y = radial_x
        rotation_signal = float(np.mean(flow[:, :, 0] * tang_x + flow[:, :, 1] * tang_y))

        # Flow variance (handheld detection)
        flow_var = float(np.var(flow))

        # Residual flow after removing global motion (subject motion indicator)
        residual_flow = flow.copy()
        residual_flow[:, :, 0] -= mean_dx
        residual_flow[:, :, 1] -= mean_dy
        residual_magnitude = float(np.mean(np.sqrt(
            residual_flow[:, :, 0]**2 + residual_flow[:, :, 1]**2
        )))

        return {
            "mean_dx": mean_dx,
            "mean_dy": mean_dy,
            "magnitude": magnitude,
            "zoom_signal": zoom_signal,
            "rotation_signal": rotation_signal,
            "flow_var": flow_var,
            "residual_magnitude": residual_magnitude,
            "homography": homography_result,
        }

    def _decompose_homography(self, gray1, gray2, cfg) -> dict | None:
        """Use feature matching + homography to get precise camera transform."""
        try:
            # ORB feature detection
            orb = cv2.ORB_create(nfeatures=500)
            kp1, des1 = orb.detectAndCompute(gray1, None)
            kp2, des2 = orb.detectAndCompute(gray2, None)

            if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
                return None

            # BFMatcher
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)

            if len(matches) < 10:
                return None

            matches = sorted(matches, key=lambda x: x.distance)[:100]

            pts1 = np.float32([kp1[m.queryIdx].pt for m in matches])
            pts2 = np.float32([kp2[m.trainIdx].pt for m in matches])

            H, mask = cv2.findHomography(
                pts1, pts2, cv2.RANSAC, cfg.homography_ransac_threshold
            )

            if H is None:
                return None

            inlier_ratio = float(np.sum(mask)) / len(mask) if len(mask) > 0 else 0

            # Decompose homography to get rotation and translation
            h, w = gray1.shape
            # Approximate camera matrix
            K = np.array([[w, 0, w / 2], [0, w, h / 2], [0, 0, 1]], dtype=np.float64)

            try:
                n_solutions, rotations, translations, normals = cv2.decomposeHomographyMat(H, K)
                if n_solutions > 0:
                    # Pick solution with smallest rotation
                    best_idx = 0
                    min_angle = float("inf")
                    for idx in range(n_solutions):
                        angle = np.arccos(np.clip((np.trace(rotations[idx]) - 1) / 2, -1, 1))
                        if angle < min_angle:
                            min_angle = angle
                            best_idx = idx

                    R = rotations[best_idx]
                    t = translations[best_idx].flatten()

                    # Extract Euler angles (approximate)
                    yaw = float(np.arctan2(R[1, 0], R[0, 0]))  # pan
                    pitch = float(np.arctan2(-R[2, 0], np.sqrt(R[2, 1]**2 + R[2, 2]**2)))  # tilt
                    roll = float(np.arctan2(R[2, 1], R[2, 2]))  # dutch angle

                    return {
                        "yaw_deg": round(float(np.degrees(yaw)), 2),
                        "pitch_deg": round(float(np.degrees(pitch)), 2),
                        "roll_deg": round(float(np.degrees(roll)), 2),
                        "translation": [round(float(x), 4) for x in t],
                        "inlier_ratio": round(inlier_ratio, 3),
                    }
            except Exception:
                pass

            return {"inlier_ratio": round(inlier_ratio, 3)}

        except Exception:
            return None

    def _compute_flow_raft(self, frame1, frame2) -> np.ndarray | None:
        try:
            def preprocess(img):
                img = img.astype(np.float32) / 255.0
                img = np.transpose(img, (2, 0, 1))
                return np.expand_dims(img, 0)

            inp1 = preprocess(frame1)
            inp2 = preprocess(frame2)
            input_names = [i.name for i in self._ort_session.get_inputs()]
            outputs = self._ort_session.run(None, {input_names[0]: inp1, input_names[1]: inp2})
            flow = outputs[0][0]
            return np.transpose(flow, (1, 2, 0))
        except Exception as e:
            log.warning("RAFT failed: %s — using Farneback", e)
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_RGB2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_RGB2GRAY)
            return cv2.calcOpticalFlowFarneback(gray1, gray2, None, 0.5, 3, 15, 3, 5, 1.2, 0)

    def _aggregate_pairs(self, pairs: list[dict]) -> CameraMotion:
        """Aggregate per-pair analysis into a single CameraMotion for the shot."""
        cfg = get_config()

        avg_dx = np.mean([p["mean_dx"] for p in pairs])
        avg_dy = np.mean([p["mean_dy"] for p in pairs])
        avg_mag = np.mean([p["magnitude"] for p in pairs])
        avg_zoom = np.mean([p["zoom_signal"] for p in pairs])
        avg_rot = np.mean([p["rotation_signal"] for p in pairs])
        avg_var = np.mean([p["flow_var"] for p in pairs])
        avg_residual = np.mean([p["residual_magnitude"] for p in pairs])

        # Homography-based angles (if available)
        yaw_deg = 0.0
        pitch_deg = 0.0
        roll_deg = 0.0
        h_count = 0
        for p in pairs:
            h = p.get("homography")
            if h and "yaw_deg" in h:
                yaw_deg += h["yaw_deg"]
                pitch_deg += h["pitch_deg"]
                roll_deg += h["roll_deg"]
                h_count += 1
        if h_count > 0:
            yaw_deg /= h_count
            pitch_deg /= h_count
            roll_deg /= h_count

        # ── Classification with compound motion support ──
        motions = []
        min_mag = cfg.camera_motion_min_magnitude

        # Check handheld first (high variance, low coherent motion)
        is_handheld = avg_var > 3.0 and avg_mag < 2.0

        # Pan (horizontal)
        if abs(avg_dx) > min_mag or abs(yaw_deg) > 0.5:
            if avg_dx > 0 or yaw_deg > 0.5:
                motions.append("pan_right")
            else:
                motions.append("pan_left")

        # Tilt (vertical)
        if abs(avg_dy) > min_mag or abs(pitch_deg) > 0.5:
            if avg_dy > 0 or pitch_deg > 0.5:
                motions.append("tilt_down")
            else:
                motions.append("tilt_up")

        # Zoom
        if abs(avg_zoom) > 0.3:
            motions.append("zoom_in" if avg_zoom > 0 else "zoom_out")

        # Rotation (Dutch angle change)
        if abs(avg_rot) > 0.5 or abs(roll_deg) > 1.0:
            motions.append("rotate")

        # Dolly (translation along Z, detected via homography)
        if h_count > 0:
            avg_tz = np.mean([
                p["homography"]["translation"][2]
                for p in pairs
                if p.get("homography") and "translation" in p["homography"]
            ]) if any(p.get("homography") and "translation" in p.get("homography", {}) for p in pairs) else 0
            if abs(avg_tz) > 0.01:
                motions.append("dolly_in" if avg_tz > 0 else "dolly_out")

        # Determine primary motion type
        if not motions or (avg_mag < min_mag and abs(avg_zoom) < 0.3):
            motion_type = "handheld" if is_handheld else "static"
        elif is_handheld and len(motions) <= 1:
            motion_type = "handheld"
        elif len(motions) == 1:
            motion_type = motions[0]
        else:
            # Compound motion: pick dominant, note secondary
            # Priority: zoom > dolly > pan/tilt > rotate
            priority = ["zoom_in", "zoom_out", "dolly_in", "dolly_out",
                        "pan_left", "pan_right", "tilt_up", "tilt_down", "rotate"]
            motion_type = next((m for m in priority if m in motions), motions[0])

        # Direction
        direction_map = {
            "pan_left": "left", "pan_right": "right",
            "tilt_up": "up", "tilt_down": "down",
            "zoom_in": "forward", "zoom_out": "backward",
            "dolly_in": "forward", "dolly_out": "backward",
            "static": "none", "handheld": "none", "rotate": "none",
        }
        direction = direction_map.get(motion_type, "none")

        # Intensity (0-1)
        intensity = min(1.0, avg_mag / 10.0)
        if "zoom" in motion_type:
            intensity = min(1.0, abs(avg_zoom) / 3.0)

        # Trajectory
        trajectory = []
        for p in pairs:
            trajectory.append([round(p["mean_dx"], 2), round(p["mean_dy"], 2)])

        return CameraMotion(
            type=motion_type,
            intensity=round(intensity, 3),
            dominant_direction=direction,
            avg_flow_magnitude=round(float(avg_mag), 3),
            trajectory=trajectory,
        )
