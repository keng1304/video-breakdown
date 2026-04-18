"""FFmpeg-based video decoder: frame extraction and audio separation."""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class VideoManifest:
    video_path: Path
    audio_path: Path | None
    fps: float
    width: int
    height: int
    duration_sec: float
    total_frames: int
    codec: str
    temp_dir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="director_")))


def probe_video(video_path: str | Path) -> dict:
    """Get video metadata via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def create_manifest(video_path: str | Path) -> VideoManifest:
    """Probe video and create a manifest with metadata."""
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    info = probe_video(video_path)

    # Find video stream
    video_stream = None
    has_audio = False
    for stream in info.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        elif stream["codec_type"] == "audio":
            has_audio = True

    if video_stream is None:
        raise ValueError(f"No video stream found in {video_path}")

    # Parse FPS
    fps_str = video_stream.get("r_frame_rate", "24/1")
    num, den = map(int, fps_str.split("/"))
    fps = num / den if den else 24.0

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    duration = float(info.get("format", {}).get("duration", 0))
    total_frames = int(video_stream.get("nb_frames", int(duration * fps)))
    codec = video_stream.get("codec_name", "unknown")

    manifest = VideoManifest(
        video_path=video_path,
        audio_path=None,
        fps=fps,
        width=width,
        height=height,
        duration_sec=duration,
        total_frames=total_frames,
        codec=codec,
    )

    # Extract audio if present
    if has_audio:
        manifest.audio_path = _extract_audio(video_path, manifest.temp_dir)

    return manifest


def _extract_audio(video_path: Path, temp_dir: Path) -> Path:
    """Extract audio track to WAV."""
    audio_path = temp_dir / "audio.wav"
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
        str(audio_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    log.info("Audio extracted to %s", audio_path)
    return audio_path


def decode_frames(
    video_path: str | Path,
    fps: float | None = None,
    max_height: int | None = None,
    start_sec: float = 0,
    end_sec: float | None = None,
) -> np.ndarray:
    """Decode video frames as a numpy array (N, H, W, 3) RGB.

    Args:
        video_path: Path to video file.
        fps: Target FPS (None = original).
        max_height: Resize to this height (None = original).
        start_sec: Start time in seconds.
        end_sec: End time in seconds (None = to end).
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    orig_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = 1 if fps is None else max(1, int(round(orig_fps / fps)))

    if start_sec > 0:
        cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)

    frames = []
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if end_sec is not None and current_sec > end_sec:
            break

        if frame_count % frame_interval == 0:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if max_height and frame_rgb.shape[0] > max_height:
                scale = max_height / frame_rgb.shape[0]
                new_w = int(frame_rgb.shape[1] * scale)
                frame_rgb = cv2.resize(frame_rgb, (new_w, max_height), interpolation=cv2.INTER_AREA)
            frames.append(frame_rgb)

        frame_count += 1

    cap.release()
    if not frames:
        raise RuntimeError(f"No frames decoded from {video_path}")

    return np.stack(frames)


def decode_frame_at(video_path: str | Path, timestamp_sec: float, max_height: int | None = None) -> np.ndarray:
    """Decode a single frame at a specific timestamp."""
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError(f"Cannot decode frame at {timestamp_sec}s from {video_path}")
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    if max_height and frame_rgb.shape[0] > max_height:
        scale = max_height / frame_rgb.shape[0]
        new_w = int(frame_rgb.shape[1] * scale)
        frame_rgb = cv2.resize(frame_rgb, (new_w, max_height), interpolation=cv2.INTER_AREA)
    return frame_rgb
