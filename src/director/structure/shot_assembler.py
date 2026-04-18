"""Shot enrichment: quantitative color, composition, subject layout, visual weight."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from director.structure.schema import (
    ColorEntry, ColorProfile, Composition, ShotData, SubjectLayout,
)

log = logging.getLogger(__name__)


def enrich_shots(
    shots: list[ShotData],
    video_path: str | Path,
    fps: float,
) -> list[ShotData]:
    """Enrich each shot with quantitative color, composition, and layout metrics."""
    from director.input.decoder import decode_frame_at
    from director.utils.video import (
        analyze_color_distribution,
        compute_nine_grid,
        compute_visual_weight,
        extract_color_entries,
    )

    for shot in shots:
        mid_time = (shot.duration_sec / 2) + _timecode_to_sec(shot.timecode_start)

        try:
            frame = decode_frame_at(video_path, mid_time, max_height=480)
        except Exception as e:
            log.warning("Cannot decode frame for shot %d: %s", shot.shot_index, e)
            continue

        # ── Text filtering: remove subtitles/overlays before analysis ──
        from director.perception.text_filter import mask_text_regions
        frame = mask_text_regions(frame)

        # ── Color profile (quantitative) ──
        shot.color = _analyze_color(frame)

        # ── Composition (quantitative) ──
        shot.composition = _analyze_composition(shot, frame)

    return shots


def _timecode_to_sec(tc: str) -> float:
    parts = tc.split(":")
    if len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return 0.0


def _analyze_color(frame: np.ndarray) -> ColorProfile:
    """Full quantitative color analysis."""
    from director.utils.video import analyze_color_distribution, extract_color_entries

    entries_raw = extract_color_entries(frame, k=6)
    palette_hex = [e["hex"] for e in entries_raw]
    palette_detailed = [
        ColorEntry(
            hex=e["hex"],
            rgb=e["rgb"],
            hsl=e["hsl"],
            weight=e["weight"],
            name=e["name"],
        )
        for e in entries_raw
    ]

    # Global brightness
    gray = np.mean(frame, axis=2)
    avg_brightness = round(float(np.mean(gray)) / 255.0, 3)
    contrast = round(float(np.std(gray)) / 128.0, 3)

    # Color temperature estimate
    mean_rgb = np.mean(frame.reshape(-1, 3), axis=0)
    r, g, b = mean_rgb
    if r > b * 1.2:
        color_temp = 3500
    elif b > r * 1.2:
        color_temp = 7500
    else:
        color_temp = 5500

    # Distribution analysis
    dist = analyze_color_distribution(frame)

    return ColorProfile(
        dominant_palette=palette_hex,
        palette_detailed=palette_detailed,
        avg_brightness=avg_brightness,
        avg_saturation=dist["avg_saturation"],
        contrast_ratio=contrast,
        color_temp_k=int(color_temp),
        dominant_hue=dist["dominant_hue"],
        warm_ratio=dist["warm_ratio"],
        cool_ratio=dist["cool_ratio"],
        neutral_ratio=dist["neutral_ratio"],
        shadow_ratio=dist["shadow_ratio"],
        midtone_ratio=dist["midtone_ratio"],
        highlight_ratio=dist["highlight_ratio"],
    )


def _analyze_composition(shot: ShotData, frame: np.ndarray) -> Composition:
    """Quantitative composition analysis: shot size, 9-grid, visual weight, subject layout."""
    from director.utils.video import compute_nine_grid, compute_visual_weight

    chars = shot.characters

    # ── Shot size from bbox ──
    max_bbox_h = 0.0
    for c in chars:
        max_bbox_h = max(max_bbox_h, c.bbox_height)

    shot_size = _classify_shot_size(max_bbox_h)

    # ── 9-grid analysis ──
    bboxes = [c.bbox for c in chars if len(c.bbox) == 4]
    nine_grid = compute_nine_grid(frame, bboxes)

    # ── Rule of thirds score ──
    thirds_score = 0.0
    for c in chars:
        # Score based on how close to a thirds intersection
        thirds_score += max(0, 1.0 - c.thirds_distance * 3)
    if chars:
        thirds_score /= len(chars)

    # ── Visual weight ──
    vw_x, vw_y = compute_visual_weight(frame)

    # ── Subject layout ──
    layout = _compute_subject_layout(chars)

    return Composition(
        shot_size=shot_size,
        shot_size_ratio=round(max_bbox_h, 3),
        angle="eye_level",  # needs camera pose for accurate detection
        depth_layers=min(3, len(chars)) if chars else 1,
        rule_of_thirds_score=round(thirds_score, 3),
        thirds_grid=nine_grid,
        subject_layout=layout,
        visual_weight_x=vw_x,
        visual_weight_y=vw_y,
    )


def _compute_subject_layout(chars) -> SubjectLayout:
    """Compute overall subject layout metrics."""
    if not chars:
        return SubjectLayout()

    total_coverage = sum(c.frame_coverage for c in chars)
    total_coverage = min(1.0, total_coverage)

    # Centroid of all subjects (weighted by coverage)
    total_w = sum(c.frame_coverage for c in chars) or 1
    centroid_x = sum(c.center_x * c.frame_coverage for c in chars) / total_w
    centroid_y = sum(c.center_y * c.frame_coverage for c in chars) / total_w

    # Spread: how dispersed are subjects
    if len(chars) >= 2:
        positions = [(c.center_x, c.center_y) for c in chars]
        dists = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                d = ((positions[i][0] - positions[j][0])**2 +
                     (positions[i][1] - positions[j][1])**2) ** 0.5
                dists.append(d)
        spread = min(1.0, sum(dists) / len(dists) / 0.7)  # normalize: 0.7 = max diagonal/2
    else:
        spread = 0.0

    # Symmetry: how balanced are subjects left vs right
    left_weight = sum(c.frame_coverage for c in chars if c.center_x < 0.5)
    right_weight = sum(c.frame_coverage for c in chars if c.center_x >= 0.5)
    total = left_weight + right_weight
    if total > 0:
        symmetry = 1.0 - abs(left_weight - right_weight) / total
    else:
        symmetry = 0.5

    return SubjectLayout(
        total_subjects=len(chars),
        total_coverage=round(total_coverage, 3),
        background_ratio=round(1.0 - total_coverage, 3),
        centroid_x=round(centroid_x, 3),
        centroid_y=round(centroid_y, 3),
        spread=round(spread, 3),
        symmetry_score=round(symmetry, 3),
    )


def _classify_shot_size(bbox_height_ratio: float) -> str:
    if bbox_height_ratio > 0.85:
        return "extreme_close_up"
    elif bbox_height_ratio > 0.7:
        return "close_up"
    elif bbox_height_ratio > 0.55:
        return "medium_close_up"
    elif bbox_height_ratio > 0.4:
        return "medium"
    elif bbox_height_ratio > 0.25:
        return "medium_wide"
    elif bbox_height_ratio > 0.1:
        return "wide"
    else:
        return "extreme_wide"
