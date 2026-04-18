"""Prompt Builder — 組裝高品質 Prompt，符合品質指紋 5 項必備。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PromptFingerprint:
    """品質指紋 — 檢查 prompt 是否包含 5 項必備元素。"""
    has_camera_spec: bool = False      # 攝影機型號
    has_lens_spec: bool = False        # 鏡頭焦距 + 光圈
    has_optical_detail: bool = False   # 光學瑕疵 (grain, aberration)
    has_physical_detail: bool = False  # 物理細節 (pore, reflection, dust)
    has_gear_movement: bool = False    # 運鏡器材

    @property
    def score(self) -> int:
        return sum([self.has_camera_spec, self.has_lens_spec, self.has_optical_detail,
                    self.has_physical_detail, self.has_gear_movement])

    @property
    def missing(self) -> list[str]:
        result = []
        if not self.has_camera_spec: result.append("攝影機")
        if not self.has_lens_spec: result.append("鏡頭參數")
        if not self.has_optical_detail: result.append("光學瑕疵")
        if not self.has_physical_detail: result.append("物理細節")
        if not self.has_gear_movement: result.append("運鏡器材")
        return result


def analyze_prompt_fingerprint(prompt: str) -> PromptFingerprint:
    """分析 prompt 是否符合 5 項必備。"""
    p = prompt.lower()

    camera_keywords = ["arri", "alexa", "red", "sony", "canon", "eos", "cooke", "venice"]
    lens_keywords = ["mm,", "f/", "f/1", "f/2", "f/4", "f/8", "macro", "prime", "anamorphic"]
    optical_keywords = ["grain", "aberration", "halation", "flare", "bokeh", "vignette"]
    physical_keywords = ["pore", "subsurface", "dust", "reflection", "fingerprint", "texture", "micro-scratch"]
    gear_keywords = ["gimbal", "steadicam", "handheld", "tripod", "dolly", "crane", "drone"]

    return PromptFingerprint(
        has_camera_spec=any(k in p for k in camera_keywords),
        has_lens_spec=any(k in p for k in lens_keywords),
        has_optical_detail=any(k in p for k in optical_keywords),
        has_physical_detail=any(k in p for k in physical_keywords),
        has_gear_movement=any(k in p for k in gear_keywords),
    )


def build_quality_prompt(
    base_description: str,
    color_style: str | None = None,
    composition_method: str | None = None,
    lighting: str | None = None,
    art_reference: str | None = None,
    camera_movement: str | None = None,
    natural_condition: str | None = None,
    product_category: str | None = None,
    reserve_composition: str | None = None,  # "bottom" / "top" / "center"
    custom_negative: str = "",
) -> tuple[str, str, PromptFingerprint]:
    """組裝品質 Prompt。

    Returns:
        (positive_prompt, negative_prompt, fingerprint)
    """
    from director.aesthetics.library import (
        COLOR_PALETTES, COMPOSITION_METHODS, LIGHTING_TYPES,
        ART_REFERENCES, CAMERA_MOVEMENT_GEAR, CATEGORY_AESTHETICS, NATURAL_CONDITIONS,
    )

    parts = [base_description.strip()]

    # ── 構圖 ──
    if composition_method and composition_method in COMPOSITION_METHODS:
        parts.append(COMPOSITION_METHODS[composition_method]["prompt"])

    # ── 光線 ──
    if lighting and lighting in LIGHTING_TYPES:
        parts.append(LIGHTING_TYPES[lighting]["prompt"])
    elif natural_condition and natural_condition in NATURAL_CONDITIONS:
        parts.append(NATURAL_CONDITIONS[natural_condition]["prompt"])

    # ── 色彩 ──
    if color_style and color_style in COLOR_PALETTES:
        parts.append(COLOR_PALETTES[color_style]["prompt"])

    # ── 藝術風格 ──
    if art_reference and art_reference in ART_REFERENCES:
        parts.append(ART_REFERENCES[art_reference]["prompt"])

    # ── 運鏡器材 ──
    if camera_movement and camera_movement in CAMERA_MOVEMENT_GEAR:
        parts.append(CAMERA_MOVEMENT_GEAR[camera_movement]["prompt"])

    # ── 品類預設（如果沒指定其他）──
    if product_category and product_category in CATEGORY_AESTHETICS and not color_style:
        preset = CATEGORY_AESTHETICS[product_category]
        color_preset = preset["colors"][0]
        if color_preset in COLOR_PALETTES:
            parts.append(COLOR_PALETTES[color_preset]["prompt"])

    # ── 構圖保留空間（字幕/Logo）──
    if reserve_composition == "bottom":
        parts.append("bottom 20% of frame reserved for subtitles, keep main subject in upper 80%")
    elif reserve_composition == "top":
        parts.append("top 20% of frame reserved for logo, keep main subject in lower 80%")
    elif reserve_composition == "center":
        parts.append("centered composition with 15% breathing space on top and bottom for potential text overlay")

    # ── 品質指紋 5 項必備 ──
    quality_suffix = (
        "shot on ARRI Alexa 35 with Cooke S7/i 40mm prime lens at f/2.8, "
        "subtle film grain (Kodak 250D emulation), slight chromatic aberration at edges, "
        "natural skin pore detail and subsurface scattering, "
        "tiny dust particles in air catching light, "
        "gimbal-stabilized smooth camera movement"
    )
    parts.append(quality_suffix)

    positive = ", ".join(parts)

    # ── Negative prompt (統一 AI 感過濾) ──
    negative_base = (
        "plastic-looking skin, perfect symmetry, over-smoothed textures, "
        "uncanny valley, airbrushed appearance, digital illustration style, "
        "CGI rendering, 3D model look, blurry, low quality, distorted, watermark, "
        "deformed faces, extra fingers, text artifacts, wrong logos"
    )
    if custom_negative:
        negative_base = f"{negative_base}, {custom_negative}"

    fingerprint = analyze_prompt_fingerprint(positive)

    return positive, negative_base, fingerprint
