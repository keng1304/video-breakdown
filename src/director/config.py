"""Global configuration for the Video Director Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    models_dir: Path = field(default=None)
    output_dir: Path = field(default=None)

    # Video processing
    max_process_resolution: int = 720  # resize to this height for processing
    scene_detect_fps: float = 0  # 0 = use original fps
    analysis_fps: float = 2.0  # fps for camera/pose analysis
    keyframe_max_edge: int = 1568  # max pixels on long edge for Claude Vision

    # Scene detection
    scene_threshold: float = 0.5  # TransNetV2 confidence threshold
    scene_fallback_threshold: float = 27.0  # PySceneDetect ContentDetector threshold

    # Camera analysis
    flow_resize_height: int = 480  # resize frames for optical flow
    homography_ransac_threshold: float = 3.0
    camera_motion_min_magnitude: float = 0.5  # below this = "static"

    # Pose tracking
    pose_confidence_threshold: float = 0.3
    pose_det_model: str = "rtmdet-nano"  # rtmlib detection model
    pose_model: str = "rtmpose-m"  # rtmlib pose model

    # Audio
    audio_sr: int = 22050  # librosa sample rate
    onset_strength_threshold: float = 0.5

    # Claude API
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 2048
    claude_batch_size: int = 5  # shots per API batch
    claude_batch_delay: float = 1.0  # seconds between batches

    # Higgsfield API
    higgsfield_model: str = "nanobanana 2"
    higgsfield_style_suffix: str = ""  # 線稿時留空，彩圖時加 photorealistic suffix

    # 影片生成
    # 靜態圖片生成: nanobanana 2 (超寫實)
    image_gen_model: str = "nanobanana 2"
    image_gen_style_suffix: str = (
        "photorealistic, hyperrealistic, shot on RED V-Raptor, "
        "8K RAW, natural skin texture, volumetric lighting, "
        "shallow depth of field, cinematic color grading"
    )

    # 動態影片生成: Kling 3.0
    video_gen_platform: str = "kling"  # "kling" or "higgsfield"
    video_gen_model: str = "kling-v3.0"
    video_gen_resolution: str = "1080p"
    video_gen_default_duration: int = 5
    video_gen_style_suffix: str = (
        "photorealistic, hyperrealistic, cinematic, "
        "natural lighting, shallow depth of field"
    )

    # Memory
    memory_budget_gb: float = 8.0  # conservative budget per pipeline

    # Device priority
    device_priority: list[str] = field(
        default_factory=lambda: ["coreml", "mps", "cpu"]
    )

    def __post_init__(self):
        if self.models_dir is None:
            self.models_dir = self.project_root / "models"
        if self.output_dir is None:
            self.output_dir = self.project_root / "output"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# Singleton
_config: Config | None = None


def get_config(**overrides) -> Config:
    global _config
    if _config is None or overrides:
        _config = Config(**overrides)
    return _config
