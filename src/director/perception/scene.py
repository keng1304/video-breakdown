"""Scene detection pipeline: TransNetV2 + PySceneDetect fallback + transition type classification."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from director.config import get_config
from director.perception.base import PerceptionPipeline
from director.structure.schema import ShotBoundary

log = logging.getLogger(__name__)


class SceneDetector(PerceptionPipeline):
    name = "scene"

    def __init__(self):
        self._model = None

    def load_model(self) -> None:
        try:
            from transnetv2_pytorch import TransNetV2
            self._model = TransNetV2()
            log.info("TransNetV2 loaded")
        except Exception as e:
            log.warning("TransNetV2 load failed: %s — will use PySceneDetect fallback", e)
            self._model = None

    def unload_model(self) -> None:
        self._model = None

    def estimate_memory_gb(self) -> float:
        return 0.5

    def process(
        self,
        video_path: str | Path,
        fps: float = 0,
        total_frames: int = 0,
    ) -> list[ShotBoundary]:
        """Detect shot boundaries and classify transition types."""
        if self._model is not None:
            shots = self._process_transnet(video_path, fps, total_frames)
        else:
            shots = self._process_scenedetect(video_path, fps)

        # Post-process: classify transition types between shots
        if len(shots) > 0:
            shots = self._classify_transitions(video_path, shots, fps)

        return shots

    def _process_transnet(
        self,
        video_path: str | Path,
        fps: float,
        total_frames: int,
    ) -> list[ShotBoundary]:
        """Primary: TransNetV2 shot boundary detection."""
        import torch

        cfg = get_config()
        log.info("Running TransNetV2 on %s", video_path)

        from director.input.decoder import decode_frames

        frames = decode_frames(video_path, max_height=cfg.max_process_resolution)
        log.info("Decoded %d frames for scene detection", len(frames))

        # TransNetV2 expects (N, 27, 48, 3) uint8 tensor
        target_h, target_w = self._model._input_size[:2]
        resized = np.stack([
            cv2.resize(f, (target_w, target_h), interpolation=cv2.INTER_AREA)
            for f in frames
        ])
        frames_tensor = torch.from_numpy(resized).to(self._model.device)

        predictions = self._model.predict_frames(frames_tensor)
        if isinstance(predictions, tuple):
            predictions = predictions[0]

        predictions = np.array(predictions).flatten()
        threshold = cfg.scene_threshold
        boundary_frames = np.where(predictions > threshold)[0]

        return self._boundaries_to_shots(boundary_frames, len(frames), fps)

    def _process_scenedetect(
        self,
        video_path: str | Path,
        fps: float,
    ) -> list[ShotBoundary]:
        """Fallback: PySceneDetect ContentDetector."""
        cfg = get_config()
        log.info("Running PySceneDetect on %s", video_path)

        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector

        video = open_video(str(video_path))
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=cfg.scene_fallback_threshold))
        scene_manager.detect_scenes(video)

        scene_list = scene_manager.get_scene_list()
        actual_fps = fps if fps > 0 else video.frame_rate

        shots = []
        for i, (start, end) in enumerate(scene_list):
            start_frame = start.get_frames()
            end_frame = end.get_frames()
            shots.append(ShotBoundary(
                shot_index=i,
                start_frame=start_frame,
                end_frame=end_frame,
                start_sec=round(start_frame / actual_fps, 3),
                end_sec=round(end_frame / actual_fps, 3),
                duration_sec=round((end_frame - start_frame) / actual_fps, 3),
                transition_in="hard_cut",
                transition_out="hard_cut",
                confidence=1.0,
            ))

        log.info("PySceneDetect found %d shots", len(shots))
        return shots

    @staticmethod
    def _boundaries_to_shots(
        boundary_frames: np.ndarray,
        total_frames: int,
        fps: float,
    ) -> list[ShotBoundary]:
        """Convert boundary frame indices to ShotBoundary list."""
        if fps <= 0:
            fps = 24.0

        starts = [0] + (boundary_frames + 1).tolist()
        ends = boundary_frames.tolist() + [total_frames - 1]

        shots = []
        for i, (s, e) in enumerate(zip(starts, ends)):
            if e <= s:
                continue
            shots.append(ShotBoundary(
                shot_index=i,
                start_frame=int(s),
                end_frame=int(e),
                start_sec=round(s / fps, 3),
                end_sec=round(e / fps, 3),
                duration_sec=round((e - s) / fps, 3),
                transition_in="hard_cut",
                transition_out="hard_cut",
                confidence=1.0,
            ))

        log.info("TransNetV2 found %d shots from %d boundary frames", len(shots), len(boundary_frames))
        return shots

    @staticmethod
    def _classify_transitions(
        video_path: str | Path,
        shots: list[ShotBoundary],
        fps: float,
    ) -> list[ShotBoundary]:
        """Classify transition types between adjacent shots by analyzing boundary frames.

        Detects: hard_cut, dissolve, fade_in, fade_out, wipe
        """
        if fps <= 0:
            fps = 24.0

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return shots

        transition_window = int(fps * 0.5)  # check 0.5s around each boundary

        for i in range(len(shots)):
            # Classify transition_in (beginning of this shot)
            if i == 0:
                # First shot: check for fade_in
                trans = _detect_fade_in(cap, shots[i].start_frame, min(transition_window, 10))
                shots[i].transition_in = trans
            else:
                # Transition between previous shot end and this shot start
                prev_end = shots[i - 1].end_frame
                curr_start = shots[i].start_frame
                trans = _classify_boundary(cap, prev_end, curr_start, transition_window)
                shots[i].transition_in = trans
                shots[i - 1].transition_out = trans

        # Last shot: check for fade_out
        if len(shots) > 0:
            last = shots[-1]
            trans = _detect_fade_out(cap, last.end_frame, min(transition_window, 10))
            if trans != "hard_cut":
                last.transition_out = trans

        cap.release()

        # Count transitions
        trans_types = {}
        for s in shots:
            trans_types[s.transition_in] = trans_types.get(s.transition_in, 0) + 1
        log.info("Transition types: %s", trans_types)

        return shots


def _read_frame_gray(cap: cv2.VideoCapture, frame_idx: int) -> np.ndarray | None:
    """Read a single frame as grayscale."""
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if not ret:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def _classify_boundary(
    cap: cv2.VideoCapture,
    prev_end: int,
    curr_start: int,
    window: int,
) -> str:
    """Classify transition type at a shot boundary.

    Strategies:
    - hard_cut: abrupt change in 1-2 frames
    - dissolve: gradual blend over multiple frames (high cross-correlation, gradual histogram change)
    - wipe: spatial boundary moves across frame (detect edge sweep pattern)
    - fade: goes through dark frames
    """
    # Sample frames around boundary
    n_samples = min(window, 8)
    pre_frames = []
    post_frames = []

    for offset in range(n_samples):
        f = _read_frame_gray(cap, max(0, prev_end - n_samples + offset))
        if f is not None:
            pre_frames.append(f)
        f = _read_frame_gray(cap, curr_start + offset)
        if f is not None:
            post_frames.append(f)

    if len(pre_frames) < 2 or len(post_frames) < 2:
        return "hard_cut"

    # 1. Check for dissolve: gradual change in mean intensity across boundary
    pre_means = [float(np.mean(f)) for f in pre_frames]
    post_means = [float(np.mean(f)) for f in post_frames]
    all_means = pre_means + post_means

    # Dissolve: smooth change rather than abrupt jump
    diffs = [abs(all_means[i + 1] - all_means[i]) for i in range(len(all_means) - 1)]
    max_diff = max(diffs) if diffs else 0
    avg_diff = sum(diffs) / len(diffs) if diffs else 0

    # 2. Check for fade (through black/white)
    boundary_brightness = (pre_means[-1] + post_means[0]) / 2
    min_brightness = min(all_means)

    if min_brightness < 15:
        # Very dark frame at boundary → fade
        if pre_means[0] > 30 and min_brightness < 15:
            return "fade_out"  # was bright, went dark
        if post_means[-1] > 30 and min_brightness < 15:
            return "fade_in"  # was dark, got bright

    # 3. Dissolve detection: frame difference spreads evenly across frame
    if len(pre_frames) >= 2 and len(post_frames) >= 2:
        # Compare histogram correlation across the boundary
        hist_pre = cv2.calcHist([pre_frames[-1]], [0], None, [64], [0, 256])
        hist_post = cv2.calcHist([post_frames[0]], [0], None, [64], [0, 256])
        hist_mid = cv2.calcHist([pre_frames[-2]], [0], None, [64], [0, 256])

        corr_direct = cv2.compareHist(hist_pre, hist_post, cv2.HISTCMP_CORREL)
        corr_gradual = cv2.compareHist(hist_mid, hist_post, cv2.HISTCMP_CORREL)

        # If histogram changes gradually (mid-to-post similar to pre-to-post), it's a dissolve
        if corr_direct > 0.7 and avg_diff < max_diff * 0.6 and max_diff < 20:
            return "dissolve"

    # 4. Wipe detection: spatial edge sweep
    if len(pre_frames) >= 1 and len(post_frames) >= 1:
        wipe_score = _detect_wipe(pre_frames[-1], post_frames[0])
        if wipe_score > 0.6:
            return "wipe"

    # Default: hard cut
    return "hard_cut"


def _detect_wipe(frame_a: np.ndarray, frame_b: np.ndarray) -> float:
    """Detect wipe transition by checking if difference has a spatial sweep pattern.

    Returns a score 0-1 (higher = more likely a wipe).
    """
    if frame_a.shape != frame_b.shape:
        frame_b = cv2.resize(frame_b, (frame_a.shape[1], frame_a.shape[0]))

    diff = cv2.absdiff(frame_a, frame_b)

    # Split frame into vertical strips
    h, w = diff.shape
    n_strips = 8
    strip_w = w // n_strips
    strip_means = []
    for i in range(n_strips):
        strip = diff[:, i * strip_w : (i + 1) * strip_w]
        strip_means.append(float(np.mean(strip)))

    if not strip_means or max(strip_means) == 0:
        return 0.0

    # Wipe pattern: high difference concentrated on one side
    # Check if strip means are monotonically increasing or decreasing
    increasing = all(strip_means[i] <= strip_means[i + 1] + 5 for i in range(len(strip_means) - 1))
    decreasing = all(strip_means[i] >= strip_means[i + 1] - 5 for i in range(len(strip_means) - 1))

    if increasing or decreasing:
        # Check contrast between first and last strip
        contrast = abs(strip_means[-1] - strip_means[0]) / (max(strip_means) + 1)
        return min(1.0, contrast)

    return 0.0


def _detect_fade_in(cap: cv2.VideoCapture, start_frame: int, n_check: int) -> str:
    """Check if the first few frames are dark (fade in from black)."""
    frames = []
    for i in range(n_check):
        f = _read_frame_gray(cap, start_frame + i)
        if f is not None:
            frames.append(float(np.mean(f)))

    if len(frames) >= 3 and frames[0] < 15 and frames[-1] > 30:
        return "fade_in"
    return "hard_cut"


def _detect_fade_out(cap: cv2.VideoCapture, end_frame: int, n_check: int) -> str:
    """Check if the last few frames go dark (fade out to black)."""
    frames = []
    for i in range(n_check):
        f = _read_frame_gray(cap, max(0, end_frame - n_check + i))
        if f is not None:
            frames.append(float(np.mean(f)))

    if len(frames) >= 3 and frames[0] > 30 and frames[-1] < 15:
        return "fade_out"
    return "hard_cut"
