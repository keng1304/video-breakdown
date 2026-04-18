"""Pose tracking pipeline: RTMPose via rtmlib + multi-frame aggregation + rich action tags."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from director.config import get_config
from director.perception.base import PerceptionPipeline
from director.structure.schema import CharacterPose, PoseKeypoint, ShotBoundary

log = logging.getLogger(__name__)

# COCO 17 keypoint indices
NOSE, L_EYE, R_EYE, L_EAR, R_EAR = 0, 1, 2, 3, 4
L_SHOULDER, R_SHOULDER = 5, 6
L_ELBOW, R_ELBOW = 7, 8
L_WRIST, R_WRIST = 9, 10
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14
L_ANKLE, R_ANKLE = 15, 16


class PoseTracker(PerceptionPipeline):
    name = "pose"

    def __init__(self):
        self._wholebody = None

    def load_model(self) -> None:
        try:
            from rtmlib import Wholebody
            self._wholebody = Wholebody(
                to_openpose=False,
                mode="lightweight",
                backend="onnxruntime",
            )
            log.info("rtmlib Wholebody loaded (RTMPose)")
        except Exception as e:
            log.error("Failed to load rtmlib: %s", e)
            self._wholebody = None

    def unload_model(self) -> None:
        self._wholebody = None

    def estimate_memory_gb(self) -> float:
        return 0.8

    def process(
        self,
        video_path: str | Path,
        shots: list[ShotBoundary],
        fps: float = 0,
    ) -> dict[int, list[CharacterPose]]:
        if self._wholebody is None:
            log.warning("Pose model not loaded, returning empty results")
            return {}

        cfg = get_config()
        results = {}
        for shot in shots:
            poses = self._analyze_shot(video_path, shot, cfg)
            results[shot.shot_index] = poses
        return results

    def _analyze_shot(self, video_path, shot, cfg) -> list[CharacterPose]:
        from director.input.decoder import decode_frames

        frames = decode_frames(
            video_path,
            fps=cfg.analysis_fps,
            max_height=cfg.max_process_resolution,
            start_sec=shot.start_sec,
            end_sec=shot.end_sec,
        )

        if len(frames) == 0:
            return []

        # Analyze multiple frames and aggregate
        sample_indices = _select_sample_indices(len(frames), max_samples=5)
        all_detections = []

        for idx in sample_indices:
            dets = self._detect_poses_in_frame(frames[idx])
            all_detections.append(dets)

        # Aggregate: use the frame with the most detected persons as representative
        # but enrich action tags from multi-frame analysis
        best_frame_idx = max(range(len(all_detections)), key=lambda i: len(all_detections[i]))
        characters = all_detections[best_frame_idx]

        # Multi-frame action refinement
        if len(all_detections) >= 3 and characters:
            characters = _refine_actions_multi_frame(all_detections, characters)

        return characters

    def _detect_poses_in_frame(self, frame: np.ndarray) -> list[CharacterPose]:
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        keypoints, scores = self._wholebody(frame_bgr)

        h, w = frame.shape[:2]
        characters = []
        cfg = get_config()

        for person_idx, (kps, scrs) in enumerate(zip(keypoints, scores)):
            if len(kps) == 0:
                continue

            valid = scrs > cfg.pose_confidence_threshold
            if not np.any(valid[:17]):  # check COCO keypoints only
                continue

            # Build keypoint list (COCO 17)
            pose_kps = []
            for i in range(min(len(kps), 17)):
                pose_kps.append(PoseKeypoint(
                    x=round(float(kps[i][0]) / w, 4),
                    y=round(float(kps[i][1]) / h, 4),
                    confidence=round(float(scrs[i]), 3),
                ))

            # Bbox from valid keypoints
            valid_kps = kps[:17][valid[:17]]
            if len(valid_kps) == 0:
                continue
            x1, y1 = valid_kps.min(axis=0)[:2]
            x2, y2 = valid_kps.max(axis=0)[:2]
            bbox = [
                round(float(x1) / w, 4), round(float(y1) / h, 4),
                round(float(x2) / w, 4), round(float(y2) / h, 4),
            ]

            # ── Precise position metrics ──
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            bw = bbox[2] - bbox[0]
            bh = bbox[3] - bbox[1]
            coverage = bw * bh

            # Screen position
            if cx < 0.33:
                screen_pos = "left_third"
            elif cx > 0.66:
                screen_pos = "right_third"
            else:
                screen_pos = "center"

            # Vertical position
            if cy < 0.33:
                vert_pos = "top"
            elif cy > 0.66:
                vert_pos = "bottom"
            else:
                vert_pos = "middle"

            # Nearest thirds intersection point
            thirds_pts = {
                "TL": (1/3, 1/3), "TR": (2/3, 1/3),
                "BL": (1/3, 2/3), "BR": (2/3, 2/3),
            }
            nearest = "center"
            min_dist = float("inf")
            for name, (tx, ty) in thirds_pts.items():
                d = ((cx - tx)**2 + (cy - ty)**2) ** 0.5
                if d < min_dist:
                    min_dist = d
                    nearest = name

            # Headroom / footroom / lead room
            headroom = bbox[1]           # top of bbox to top of frame
            footroom = 1.0 - bbox[3]     # bottom of bbox to bottom of frame
            lead_left = bbox[0]          # left of bbox to left of frame
            lead_right = 1.0 - bbox[2]   # right of bbox to right of frame

            # Action classification
            action = _classify_action_detailed(kps[:17], scrs[:17])

            characters.append(CharacterPose(
                track_id=person_idx,
                bbox=bbox,
                center_x=round(cx, 3),
                center_y=round(cy, 3),
                frame_coverage=round(coverage, 4),
                bbox_width=round(bw, 3),
                bbox_height=round(bh, 3),
                screen_position=screen_pos,
                vertical_position=vert_pos,
                nearest_thirds_point=nearest,
                thirds_distance=round(min_dist, 3),
                headroom=round(headroom, 3),
                footroom=round(footroom, 3),
                lead_room_left=round(lead_left, 3),
                lead_room_right=round(lead_right, 3),
                keypoints=pose_kps,
                action_tag=action,
            ))

        return characters


def _select_sample_indices(n_frames: int, max_samples: int = 5) -> list[int]:
    """Select evenly spaced frame indices for analysis."""
    if n_frames <= max_samples:
        return list(range(n_frames))
    step = n_frames / max_samples
    return [int(i * step) for i in range(max_samples)]


def _classify_action_detailed(kps: np.ndarray, scores: np.ndarray) -> str:
    """Rich action classification from COCO 17 keypoints geometry."""
    conf = 0.3

    def valid(idx):
        return idx < len(scores) and scores[idx] > conf

    def kp(idx):
        return kps[idx] if valid(idx) else None

    # Helper: vertical positions (lower y = higher in image)
    nose = kp(NOSE)
    l_sh, r_sh = kp(L_SHOULDER), kp(R_SHOULDER)
    l_hip, r_hip = kp(L_HIP), kp(R_HIP)
    l_knee, r_knee = kp(L_KNEE), kp(R_KNEE)
    l_ankle, r_ankle = kp(L_ANKLE), kp(R_ANKLE)
    l_wrist, r_wrist = kp(L_WRIST), kp(R_WRIST)
    l_elbow, r_elbow = kp(L_ELBOW), kp(R_ELBOW)

    # ── Lying down: shoulders and hips at similar Y ──
    if l_sh is not None and r_sh is not None and l_hip is not None and r_hip is not None:
        shoulder_y = (l_sh[1] + r_sh[1]) / 2
        hip_y = (l_hip[1] + r_hip[1]) / 2
        torso_height = abs(hip_y - shoulder_y)
        shoulder_spread = abs(l_sh[0] - r_sh[0])
        if torso_height < shoulder_spread * 0.5 and torso_height < 30:
            return "lying"

    # ── Sitting: hips close to knees vertically ──
    if l_hip is not None and r_hip is not None and l_knee is not None and r_knee is not None:
        hip_y = (l_hip[1] + r_hip[1]) / 2
        knee_y = (l_knee[1] + r_knee[1]) / 2
        if l_ankle is not None and r_ankle is not None:
            ankle_y = (l_ankle[1] + r_ankle[1]) / 2
            hip_knee = abs(knee_y - hip_y)
            knee_ankle = abs(ankle_y - knee_y)
            if hip_knee < knee_ankle * 0.6:
                return "sitting"

    # ── Crouching: knees significantly bent, torso lowered ──
    if l_hip is not None and l_knee is not None and l_ankle is not None:
        hip_y = l_hip[1]
        knee_y = l_knee[1]
        ankle_y = l_ankle[1]
        # When crouching, hip drops close to knee level
        total = abs(ankle_y - hip_y)
        if total > 0 and abs(knee_y - hip_y) / total < 0.3:
            return "crouching"

    # ── Arms raised (waving, celebrating, aiming) ──
    arms_raised = False
    if l_sh is not None and r_sh is not None:
        shoulder_y = (l_sh[1] + r_sh[1]) / 2
        wrists_above = 0
        if l_wrist is not None and l_wrist[1] < shoulder_y:
            wrists_above += 1
        if r_wrist is not None and r_wrist[1] < shoulder_y:
            wrists_above += 1
        if wrists_above >= 2:
            # Both arms above shoulders
            if nose is not None and l_wrist is not None and r_wrist is not None:
                if l_wrist[1] < nose[1] and r_wrist[1] < nose[1]:
                    return "hands_up"  # both hands above head
            return "arms_raised"
        elif wrists_above == 1:
            # One arm raised: pointing, waving, or aiming
            arms_raised = True

    # ── Arms extended forward (pushing, reaching, aiming) ──
    if l_sh is not None and l_wrist is not None and l_elbow is not None:
        # Arm is extended if wrist is far from shoulder horizontally
        arm_len = abs(l_wrist[0] - l_sh[0])
        torso_w = abs(l_sh[0] - r_sh[0]) if r_sh is not None else arm_len
        if arm_len > torso_w * 1.5:
            return "reaching"

    if r_sh is not None and r_wrist is not None and r_elbow is not None:
        arm_len = abs(r_wrist[0] - r_sh[0])
        torso_w = abs(l_sh[0] - r_sh[0]) if l_sh is not None else arm_len
        if arm_len > torso_w * 1.5:
            return "reaching"

    if arms_raised:
        return "one_arm_raised"

    # ── Walking/running detection (leg spread) ──
    if l_ankle is not None and r_ankle is not None and l_hip is not None and r_hip is not None:
        ankle_spread = abs(l_ankle[0] - r_ankle[0])
        hip_spread = abs(l_hip[0] - r_hip[0])
        if ankle_spread > hip_spread * 2.0:
            # Wide stance = walking or running
            if l_knee is not None and r_knee is not None:
                knee_diff = abs(l_knee[1] - r_knee[1])
                if knee_diff > 20:
                    return "running"
            return "walking"

    # ── Default ──
    return "standing"


def _refine_actions_multi_frame(
    all_detections: list[list[CharacterPose]],
    best_frame: list[CharacterPose],
) -> list[CharacterPose]:
    """Refine action tags using multi-frame consistency.

    If the same person has different action tags across frames, pick the most common.
    Also detect motion-based actions (walking, running) from position changes.
    """
    # Simple: for each person in best_frame, check if their action is consistent
    for char in best_frame:
        actions_seen = []
        for frame_dets in all_detections:
            # Find matching person by closest bbox overlap
            for det in frame_dets:
                if _bbox_iou(char.bbox, det.bbox) > 0.3:
                    actions_seen.append(det.action_tag)
                    break

        if actions_seen:
            # Most common action
            from collections import Counter
            most_common = Counter(actions_seen).most_common(1)[0][0]

            # Motion detection: if position changes significantly across frames
            positions = []
            for frame_dets in all_detections:
                for det in frame_dets:
                    if _bbox_iou(char.bbox, det.bbox) > 0.3:
                        cx = (det.bbox[0] + det.bbox[2]) / 2
                        cy = (det.bbox[1] + det.bbox[3]) / 2
                        positions.append((cx, cy))
                        break

            if len(positions) >= 3:
                total_dx = abs(positions[-1][0] - positions[0][0])
                total_dy = abs(positions[-1][1] - positions[0][1])
                total_movement = (total_dx**2 + total_dy**2) ** 0.5
                if total_movement > 0.1:  # significant movement across frames
                    if most_common == "standing":
                        most_common = "walking"

            char.action_tag = most_common

    return best_frame


def _bbox_iou(bbox1: list[float], bbox2: list[float]) -> float:
    """Compute IoU between two [x1, y1, x2, y2] bounding boxes."""
    if len(bbox1) < 4 or len(bbox2) < 4:
        return 0.0

    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - inter

    return inter / union if union > 0 else 0.0
