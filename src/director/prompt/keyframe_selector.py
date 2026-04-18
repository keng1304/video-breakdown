"""Select representative keyframes per shot."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from director.config import get_config
from director.structure.schema import ShotBoundary
from director.utils.video import save_frame

log = logging.getLogger(__name__)


def select_keyframes(
    video_path: str | Path,
    shots: list[ShotBoundary],
    output_dir: str | Path,
    max_per_shot: int = 3,
) -> dict[int, list[str]]:
    """Select 1-3 keyframes per shot, save to disk, return {shot_idx: [paths]}.

    Strategy:
    - Always include the middle frame.
    - For shots > 2s, also pick the visually most distinctive frames.
    """
    cfg = get_config()
    output_dir = Path(output_dir) / "keyframes"
    output_dir.mkdir(parents=True, exist_ok=True)

    from director.input.decoder import decode_frames

    result = {}

    for shot in shots:
        frames = decode_frames(
            video_path,
            fps=cfg.analysis_fps,
            max_height=cfg.keyframe_max_edge,
            start_sec=shot.start_sec,
            end_sec=shot.end_sec,
        )

        if len(frames) == 0:
            result[shot.shot_index] = []
            continue

        # Always pick middle frame
        indices = [len(frames) // 2]

        # For longer shots, pick frames with highest visual distinctiveness
        if len(frames) >= 4 and max_per_shot > 1:
            diffs = []
            for i in range(1, len(frames)):
                diff = np.mean(np.abs(frames[i].astype(float) - frames[i - 1].astype(float)))
                diffs.append((i, diff))
            diffs.sort(key=lambda x: -x[1])

            for idx, _ in diffs:
                if idx not in indices:
                    indices.append(idx)
                if len(indices) >= max_per_shot:
                    break

        indices.sort()
        paths = []
        for i, frame_idx in enumerate(indices):
            path = output_dir / f"shot_{shot.shot_index:04d}_key{i}.jpg"
            save_frame(frames[frame_idx], path, quality=90)
            paths.append(str(path.resolve()))  # 絕對路徑

        result[shot.shot_index] = paths

    total_kf = sum(len(v) for v in result.values())
    log.info("Selected %d keyframes across %d shots", total_kf, len(shots))
    return result
