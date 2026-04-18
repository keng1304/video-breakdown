"""Pydantic v2 data models for all layers — quantitative composition & color."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Layer 0: Video Metadata ──

class VideoMetadata(BaseModel):
    path: str
    filename: str
    duration_sec: float
    fps: float
    width: int
    height: int
    codec: str = ""
    total_frames: int = 0
    audio_path: str | None = None


# ── Layer 1: Perception Outputs ──

class ShotBoundary(BaseModel):
    shot_index: int
    start_frame: int
    end_frame: int
    start_sec: float
    end_sec: float
    duration_sec: float
    transition_in: str = "hard_cut"
    transition_out: str = "hard_cut"
    confidence: float = 1.0


class CameraMotion(BaseModel):
    type: str = "static"
    intensity: float = 0.0  # 0-1
    dominant_direction: str = "none"
    avg_flow_magnitude: float = 0.0
    trajectory: list[list[float]] = Field(default_factory=list)  # [[dx, dy], ...]

    # Homography decomposition (if available)
    yaw_deg: float = 0.0   # pan angle (degrees/frame)
    pitch_deg: float = 0.0  # tilt angle
    roll_deg: float = 0.0   # dutch angle change


class PoseKeypoint(BaseModel):
    x: float  # 0-1 normalized
    y: float  # 0-1 normalized
    confidence: float


class CharacterPose(BaseModel):
    track_id: int = 0
    bbox: list[float] = Field(default_factory=list)  # [x1, y1, x2, y2] normalized 0-1

    # ── 精確位置數據 ──
    center_x: float = 0.5   # 主體中心 X (0=左邊, 1=右邊)
    center_y: float = 0.5   # 主體中心 Y (0=上方, 1=下方)
    frame_coverage: float = 0.0  # 主體佔畫面比例 (0-1, e.g. 0.23 = 23%)
    bbox_width: float = 0.0     # bbox 寬度比例
    bbox_height: float = 0.0    # bbox 高度比例

    # ── 構圖位置標籤 ──
    screen_position: str = "center"  # left_third, center, right_third
    vertical_position: str = "middle"  # top, middle, bottom
    nearest_thirds_point: str = ""   # 最近的三分法交叉點: "TL", "TR", "BL", "BR", "center"
    thirds_distance: float = 0.0     # 到最近三分法交叉點的距離 (0=完美對齊)

    # ── 構圖空間 ──
    headroom: float = 0.0    # 頭頂到畫面上緣的距離比例 (0-1)
    footroom: float = 0.0    # 腳底到畫面下緣的距離比例
    lead_room_left: float = 0.0   # 主體左側空間比例
    lead_room_right: float = 0.0  # 主體右側空間比例

    keypoints: list[PoseKeypoint] = Field(default_factory=list)
    action_tag: str = "unknown"


class AudioFeatures(BaseModel):
    bpm: float = 0.0
    beat_timestamps: list[float] = Field(default_factory=list)
    energy_curve: list[float] = Field(default_factory=list)
    onset_timestamps: list[float] = Field(default_factory=list)
    avg_energy: float = 0.0


# ── Layer 2: Per-Shot Structured Data ──

class SubjectLayout(BaseModel):
    """所有主體在畫面中的整體佈局。"""
    total_subjects: int = 0
    total_coverage: float = 0.0    # 所有主體合計佔畫面比例
    background_ratio: float = 1.0  # 背景佔畫面比例 (= 1 - total_coverage)
    centroid_x: float = 0.5        # 所有主體的質心 X
    centroid_y: float = 0.5        # 所有主體的質心 Y
    spread: float = 0.0            # 主體分散程度 (0=集中, 1=分散在畫面各處)
    symmetry_score: float = 0.5    # 左右對稱度 (0=完全偏一邊, 1=完美對稱)


class Composition(BaseModel):
    shot_size: str = "medium"
    shot_size_ratio: float = 0.0    # 最大主體的 bbox 高度比例 (精確數值)
    angle: str = "eye_level"
    depth_layers: int = 1

    # ── 三分法分析 ──
    rule_of_thirds_score: float = 0.0  # 0-1
    thirds_grid: list[float] = Field(default_factory=list)
    # 9 宮格每格的主體佔比 [TL, TC, TR, ML, MC, MR, BL, BC, BR]
    # 例如 [0, 0, 0.1, 0, 0.3, 0.2, 0, 0.1, 0] = 主體集中在中間偏右

    # ── 主體佈局 ──
    subject_layout: SubjectLayout = Field(default_factory=SubjectLayout)

    # ── 視覺重心 ──
    visual_weight_x: float = 0.5  # 整體視覺重心 X (含色彩亮度)
    visual_weight_y: float = 0.5  # 整體視覺重心 Y


class ColorEntry(BaseModel):
    """單一色彩條目，含精確數據。"""
    hex: str = ""           # e.g. "#1a3a4a"
    rgb: list[int] = Field(default_factory=list)  # [r, g, b]
    hsl: list[float] = Field(default_factory=list)  # [h°, s%, l%]
    weight: float = 0.0    # 在畫面中的佔比 (0-1)
    name: str = ""          # 近似色名 e.g. "深藍綠", "暖橙"


class ColorProfile(BaseModel):
    dominant_palette: list[str] = Field(default_factory=list)  # 向下相容：hex list
    palette_detailed: list[ColorEntry] = Field(default_factory=list)  # 精確版

    # ── 全域色彩數據 ──
    avg_brightness: float = 0.5     # 0-1
    avg_saturation: float = 0.5     # 0-1
    contrast_ratio: float = 1.0     # 標準差 / 128
    color_temp_k: int = 5500
    dominant_hue: float = 0.0       # 主色相角度 0-360°

    # ── 色彩分布 ──
    warm_ratio: float = 0.5  # 暖色佔比 (紅/橙/黃)
    cool_ratio: float = 0.5  # 冷色佔比 (藍/綠/紫)
    neutral_ratio: float = 0.0  # 中性色佔比 (灰/黑/白)

    # ── 亮度分布 ──
    shadow_ratio: float = 0.0   # 暗部 (< 0.25) 佔比
    midtone_ratio: float = 0.0  # 中間調 (0.25-0.75) 佔比
    highlight_ratio: float = 0.0  # 亮部 (> 0.75) 佔比


class AudioSync(BaseModel):
    beat_positions: list[float] = Field(default_factory=list)
    energy_level: float = 0.0
    is_on_beat_cut: bool = False
    onset_count: int = 0


class ShotData(BaseModel):
    shot_index: int
    timecode_start: str = ""
    timecode_end: str = ""
    duration_sec: float = 0.0
    transition_in: str = "hard_cut"
    transition_out: str = "hard_cut"
    camera_motion: CameraMotion = Field(default_factory=CameraMotion)
    characters: list[CharacterPose] = Field(default_factory=list)
    composition: Composition = Field(default_factory=Composition)
    color: ColorProfile = Field(default_factory=ColorProfile)
    audio_sync: AudioSync = Field(default_factory=AudioSync)
    keyframe_paths: list[str] = Field(default_factory=list)


# ── Layer 3: Director Fingerprint ──

class DirectorFingerprint(BaseModel):
    total_shots: int = 0
    total_duration_sec: float = 0.0
    cuts_per_minute: float = 0.0
    avg_shot_duration: float = 0.0
    median_shot_duration: float = 0.0
    shot_duration_std: float = 0.0
    shot_size_distribution: dict[str, int] = Field(default_factory=dict)
    transition_distribution: dict[str, int] = Field(default_factory=dict)
    camera_motion_distribution: dict[str, int] = Field(default_factory=dict)
    pacing: str = "moderate"
    dominant_shot_sizes: list[str] = Field(default_factory=list)
    signature_camera_moves: list[str] = Field(default_factory=list)
    color_fingerprint: list[str] = Field(default_factory=list)
    rhythm_pattern: str = ""


# ── Subject Anchor: 主體身份卡 ──

class SubjectAppearance(BaseModel):
    """單一主體的外觀描述 — 用於跨鏡頭一致性。"""
    # 色彩特徵
    dominant_colors: list[ColorEntry] = Field(default_factory=list)  # 主體上的主要顏色
    avg_brightness: float = 0.5

    # 尺寸特徵
    avg_height_ratio: float = 0.0    # 平均佔畫面高度比
    avg_width_ratio: float = 0.0
    aspect_ratio: float = 1.0        # 寬高比

    # 外觀描述 (由 Claude Vision 生成)
    appearance_description: str = ""  # e.g. "navy school uniform, white shirt, dark hair"
    material_texture: str = ""        # e.g. "matte fabric, cotton blend"


class SubjectIdentityCard(BaseModel):
    """主體身份卡 — 跨鏡頭追蹤同一主體的一致描述。"""
    subject_id: str = ""           # e.g. "person_01", "product_main"
    subject_type: str = "person"   # person, product, vehicle, prop
    first_seen_shot: int = 0
    last_seen_shot: int = 0
    appearance_count: int = 0      # 出現在幾個鏡頭中

    # 一致性描述 (英文，可直接放入 prompt)
    canonical_description: str = ""  # 跨鏡頭統一的外觀描述
    # e.g. "a Japanese high school girl in navy blazer and plaid skirt, shoulder-length black hair"

    appearance: SubjectAppearance = Field(default_factory=SubjectAppearance)

    # 出現的鏡頭列表
    shot_appearances: list[int] = Field(default_factory=list)

    # Reference image
    best_reference_path: str = ""  # 最佳參考圖片路徑 (最清晰、最完整)
    reference_crop_path: str = ""  # 裁切後的主體特寫


class ForegroundLayer(BaseModel):
    """前景分離結果。"""
    mask_path: str = ""            # 前景遮罩路徑
    foreground_path: str = ""      # 去背後的前景圖
    background_path: str = ""      # 移除前景後的背景圖
    foreground_ratio: float = 0.0  # 前景佔畫面比例
    background_ratio: float = 0.0


# ── Layer 4: Generation Prompts ──

class GenerationPrompt(BaseModel):
    shot_index: int
    scene_description: str = ""
    seedance_prompt: str = ""
    kling_prompt: str = ""
    negative_prompt: str = ""
    duration_hint: float = 0.0
    reference_image: str = ""      # 推薦作為 image reference 的 keyframe 路徑


# ── Top-level Output ──

class ProjectBrief(BaseModel):
    """專案 brief — 從 Round 1-6 累積的全域設定。"""
    # Round 1-2
    target_audience: str = ""           # 目標受眾 e.g. "25-35 歲職場女性"
    product_category: str = ""          # 品類 e.g. "保健食品"
    platform: str = "general"           # 投放平台: "youtube", "ig_reels", "tiktok", "tvc", "general"
    rhythm_multiplier: float = 1.0      # 全局節奏倍率 0.5-1.5

    # Round 4 美學
    aesthetic_mode: str = "brand"       # "artistic" or "brand"
    color_style: str = ""               # 從 COLOR_PALETTES 選
    lighting: str = ""                  # 從 LIGHTING_TYPES 選
    composition_method: str = ""        # 從 COMPOSITION_METHODS 選
    art_reference: str = ""             # 從 ART_REFERENCES 選
    natural_condition: str = ""         # 從 NATURAL_CONDITIONS 選
    camera_movement_gear: str = ""      # 從 CAMERA_MOVEMENT_GEAR 選

    # Round 5B 音樂
    music_style: str = ""               # 從 MUSIC_EMOTIONS 選
    sound_design_style: str = ""        # 從 SOUND_DESIGN_STYLES 選


class ShotMetadata(BaseModel):
    """每個 shot 的擴充資料 (Round 1-6)。"""
    # Round 1-2
    narrative_arc: str = "middle"       # "opening" / "verse" / "build" / "drop" / "outro"
    product_exposure: str = "present"   # "hero" / "present" / "none"
    composition_reserve: str = "none"   # "bottom" / "top" / "center" / "none"
    consistency_group_id: str = ""      # 同組必須同人物
    is_applicable: bool = True          # 客戶認為是否適合本品類

    # Round 3
    prompt_quality_score: int = 0       # 0-5 品質指紋分數
    forbidden_warnings: list[str] = Field(default_factory=list)

    # Round 5B
    music_section: str = ""             # intro/verse/build/drop/outro
    cut_beat_type: str = "on_beat"      # "pre_beat" / "on_beat" / "post_beat"
    cut_offset_frames: int = 0

    # Round 6
    scene_anchor_priority: int = 5      # 1-5 場景真實度級別
    real_footage_path: str = ""         # Hybrid 模式使用
    generation_mode: str = "ai"         # "ai" / "real_footage" / "hybrid_composite"


class VideoAnalysis(BaseModel):
    metadata: VideoMetadata
    shots: list[ShotData] = Field(default_factory=list)
    audio_features: AudioFeatures = Field(default_factory=AudioFeatures)
    fingerprint: DirectorFingerprint = Field(default_factory=DirectorFingerprint)
    prompts: list[GenerationPrompt] = Field(default_factory=list)
    subject_cards: list[SubjectIdentityCard] = Field(default_factory=list)

    # Round 1-6 新增
    brief: ProjectBrief = Field(default_factory=ProjectBrief)
    shot_metadata: dict[int, ShotMetadata] = Field(default_factory=dict)  # shot_index -> metadata
