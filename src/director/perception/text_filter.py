"""Text detection and filtering — ignore subtitles, title cards, and logos in analysis.

Two strategies:
1. Detect text regions in keyframes → mask them out before color/composition analysis
2. Instruct Claude Vision to ignore text overlays when generating prompts
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

log = logging.getLogger(__name__)


def detect_text_regions(frame: np.ndarray, min_area: int = 500) -> list[list[int]]:
    """Detect text/subtitle regions in a frame.

    Returns list of [x1, y1, x2, y2] bounding boxes (pixel coordinates).

    Strategy: MSER (Maximally Stable Extremal Regions) + morphological grouping.
    Fast, no model needed, works well for subtitles and title cards.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape

    # MSER for text-like regions
    mser = cv2.MSER_create()
    mser.setMinArea(60)
    mser.setMaxArea(int(h * w * 0.05))  # max 5% of frame
    regions, _ = mser.detectRegions(gray)

    if not regions:
        return []

    # Convert regions to bounding boxes
    boxes = []
    for region in regions:
        x, y, bw, bh = cv2.boundingRect(region)
        # Filter: text tends to be wider than tall, or small and dense
        aspect = bw / max(bh, 1)
        if 0.1 < aspect < 15 and bw * bh > min_area:
            boxes.append([x, y, x + bw, y + bh])

    if not boxes:
        return []

    # Group nearby boxes (subtitles are usually clustered)
    grouped = _group_boxes(boxes, h, w)

    # Filter: keep only regions that look like text areas
    text_regions = []
    for box in grouped:
        x1, y1, x2, y2 = box
        region_h = y2 - y1
        region_w = x2 - x1

        # Text regions are typically:
        # - In bottom 30% (subtitles) or top 20% (title cards) of frame
        # - Or span a wide horizontal area (lower thirds)
        is_subtitle_zone = y1 > h * 0.65  # bottom 35%
        is_title_zone = y2 < h * 0.25      # top 25%
        is_wide = region_w > w * 0.3        # spans >30% width
        is_lower_third = y1 > h * 0.6 and is_wide

        if is_subtitle_zone or is_title_zone or is_lower_third:
            text_regions.append(box)

    log.debug("Detected %d text regions from %d candidates", len(text_regions), len(boxes))
    return text_regions


def mask_text_regions(
    frame: np.ndarray,
    text_regions: list[list[int]] | None = None,
) -> np.ndarray:
    """Return a copy of the frame with text regions inpainted (removed).

    If text_regions is None, auto-detect them first.
    """
    if text_regions is None:
        text_regions = detect_text_regions(frame)

    if not text_regions:
        return frame

    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    for x1, y1, x2, y2 in text_regions:
        # Expand slightly for better inpainting
        pad = 5
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(frame.shape[1], x2 + pad)
        y2 = min(frame.shape[0], y2 + pad)
        mask[y1:y2, x1:x2] = 255

    # Inpaint
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    inpainted = cv2.inpaint(bgr, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
    result = cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)

    log.debug("Masked %d text regions", len(text_regions))
    return result


def has_significant_text(frame: np.ndarray, threshold: float = 0.05) -> bool:
    """Check if a frame has significant text overlay (>threshold of frame area)."""
    regions = detect_text_regions(frame)
    if not regions:
        return False

    h, w = frame.shape[:2]
    total_area = h * w
    text_area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in regions)
    ratio = text_area / total_area

    return ratio > threshold


def get_text_ignore_instruction() -> str:
    """Return the instruction string to append to Claude Vision prompts."""
    return (
        "\n\nIMPORTANT: Completely IGNORE any text overlays visible in the keyframes — "
        "including subtitles, title cards, lower thirds, watermarks, and logos. "
        "These are post-production additions and should NOT appear in your generated prompts. "
        "Describe only the visual scene, subjects, camera movement, and lighting. "
        "Never include text content, font styles, or text positioning in the output prompts."
    )


def _group_boxes(boxes: list[list[int]], h: int, w: int, merge_dist: int = 20) -> list[list[int]]:
    """Group nearby bounding boxes into larger regions."""
    if not boxes:
        return []

    # Sort by y1 then x1
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))

    merged = []
    used = [False] * len(boxes)

    for i in range(len(boxes)):
        if used[i]:
            continue

        x1, y1, x2, y2 = boxes[i]
        used[i] = True

        # Merge with nearby boxes
        changed = True
        while changed:
            changed = False
            for j in range(len(boxes)):
                if used[j]:
                    continue
                jx1, jy1, jx2, jy2 = boxes[j]

                # Check if boxes are close enough to merge
                if (jx1 <= x2 + merge_dist and jx2 >= x1 - merge_dist and
                        jy1 <= y2 + merge_dist and jy2 >= y1 - merge_dist):
                    x1 = min(x1, jx1)
                    y1 = min(y1, jy1)
                    x2 = max(x2, jx2)
                    y2 = max(y2, jy2)
                    used[j] = True
                    changed = True

        merged.append([x1, y1, x2, y2])

    return merged
