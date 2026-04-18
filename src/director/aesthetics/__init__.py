"""美學知識庫 — 色彩/構圖/光線/藝術家/鏡頭/運鏡。"""
from director.aesthetics.library import (
    COLOR_PALETTES, COMPOSITION_METHODS, LIGHTING_TYPES,
    ART_REFERENCES, CAMERA_MOVEMENT_GEAR, CATEGORY_AESTHETICS,
    NATURAL_CONDITIONS, MUSIC_EMOTIONS, SOUND_DESIGN_STYLES,
    FORBIDDEN_PATTERNS,
)
from director.aesthetics.prompt_builder import build_quality_prompt, PromptFingerprint
from director.aesthetics.forbidden import detect_forbidden_zones, FORBIDDEN_RULES

__all__ = [
    "COLOR_PALETTES", "COMPOSITION_METHODS", "LIGHTING_TYPES",
    "ART_REFERENCES", "CAMERA_MOVEMENT_GEAR", "CATEGORY_AESTHETICS",
    "NATURAL_CONDITIONS", "MUSIC_EMOTIONS", "SOUND_DESIGN_STYLES",
    "FORBIDDEN_PATTERNS", "build_quality_prompt", "PromptFingerprint",
    "detect_forbidden_zones", "FORBIDDEN_RULES",
]
