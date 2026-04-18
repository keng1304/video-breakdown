"""Frame I/O helpers + quantitative color analysis."""

from __future__ import annotations

import colorsys
from pathlib import Path

import cv2
import numpy as np


def load_frame(path: str | Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Cannot read frame: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def save_frame(frame: np.ndarray, path: str | Path, quality: int = 90) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(str(path), bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok or not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"cv2.imwrite failed for {path}")
    return path


def resize_frame(frame: np.ndarray, max_height: int) -> np.ndarray:
    h, w = frame.shape[:2]
    if h <= max_height:
        return frame
    scale = max_height / h
    new_w = int(w * scale)
    return cv2.resize(frame, (new_w, max_height), interpolation=cv2.INTER_AREA)


# ── Color Names (zh) ──

_COLOR_NAMES = [
    ((0, 15), "紅"),      ((15, 35), "橙"),     ((35, 55), "黃"),
    ((55, 80), "黃綠"),    ((80, 160), "綠"),    ((160, 200), "青"),
    ((200, 250), "藍"),    ((250, 290), "紫"),   ((290, 330), "紫紅"),
    ((330, 360), "紅"),
]


def _color_name_zh(h: float, s: float, l: float) -> str:
    """Map HSL to a Chinese color name."""
    if s < 0.1:
        if l < 0.15:
            return "黑"
        elif l > 0.85:
            return "白"
        else:
            return "灰"
    if l < 0.12:
        return "深黑"
    if l > 0.88:
        return "亮白"

    prefix = ""
    if l < 0.3:
        prefix = "深"
    elif l > 0.7:
        prefix = "亮"

    hue_name = "灰"
    for (lo, hi), name in _COLOR_NAMES:
        if lo <= h < hi:
            hue_name = name
            break

    return prefix + hue_name


def extract_dominant_colors(frame: np.ndarray, k: int = 5) -> list[str]:
    """Extract k dominant colors as hex strings (backward compat)."""
    entries = extract_color_entries(frame, k)
    return [e["hex"] for e in entries]


def extract_color_entries(frame: np.ndarray, k: int = 5) -> list[dict]:
    """Extract k dominant colors with full metadata: hex, rgb, hsl, weight, name."""
    pixels = frame.reshape(-1, 3).astype(np.float32)
    n_pixels = len(pixels)

    # Subsample for speed
    if n_pixels > 20000:
        indices = np.random.choice(n_pixels, 20000, replace=False)
        pixels = pixels[indices]

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
    centers = centers.astype(np.uint8)
    counts = np.bincount(labels.flatten(), minlength=k)
    total = counts.sum()

    # Sort by frequency
    order = np.argsort(-counts)
    entries = []
    for idx in order:
        r, g, b = int(centers[idx][0]), int(centers[idx][1]), int(centers[idx][2])
        weight = round(float(counts[idx]) / total, 3)

        # RGB → HSL
        h_norm, l_norm, s_norm = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        h_deg = round(h_norm * 360, 1)
        s_pct = round(s_norm * 100, 1)
        l_pct = round(l_norm * 100, 1)

        name = _color_name_zh(h_deg, s_norm, l_norm)

        entries.append({
            "hex": f"#{r:02x}{g:02x}{b:02x}",
            "rgb": [r, g, b],
            "hsl": [h_deg, s_pct, l_pct],
            "weight": weight,
            "name": name,
        })

    return entries


def analyze_color_distribution(frame: np.ndarray) -> dict:
    """Analyze color distribution: warm/cool/neutral ratios, brightness distribution."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
    h = hsv[:, :, 0] * 2  # OpenCV HSV H is 0-180, convert to 0-360
    s = hsv[:, :, 1] / 255.0
    v = hsv[:, :, 2] / 255.0

    n = h.size

    # Warm/cool/neutral classification
    # Warm: red(330-360, 0-30), orange(30-60), yellow(60-80)
    # Cool: green(80-160), cyan(160-200), blue(200-250), purple(250-330)
    # Neutral: low saturation (< 0.15)
    neutral_mask = s.flatten() < 0.15
    warm_hues = ((h.flatten() < 80) | (h.flatten() > 330)) & ~neutral_mask
    cool_hues = ((h.flatten() >= 80) & (h.flatten() <= 330)) & ~neutral_mask

    warm_ratio = round(float(np.sum(warm_hues)) / n, 3)
    cool_ratio = round(float(np.sum(cool_hues)) / n, 3)
    neutral_ratio = round(float(np.sum(neutral_mask)) / n, 3)

    # Brightness distribution
    brightness = v.flatten()
    shadow_ratio = round(float(np.sum(brightness < 0.25)) / n, 3)
    midtone_ratio = round(float(np.sum((brightness >= 0.25) & (brightness <= 0.75))) / n, 3)
    highlight_ratio = round(float(np.sum(brightness > 0.75)) / n, 3)

    # Average saturation
    avg_saturation = round(float(np.mean(s)), 3)

    # Dominant hue (weighted by saturation)
    # Circular mean using unit vectors
    s_flat = s.flatten()
    h_rad = np.radians(h.flatten())
    sin_sum = np.sum(np.sin(h_rad) * s_flat)
    cos_sum = np.sum(np.cos(h_rad) * s_flat)
    dominant_hue = round(float(np.degrees(np.arctan2(sin_sum, cos_sum))) % 360, 1)

    return {
        "avg_saturation": avg_saturation,
        "dominant_hue": dominant_hue,
        "warm_ratio": warm_ratio,
        "cool_ratio": cool_ratio,
        "neutral_ratio": neutral_ratio,
        "shadow_ratio": shadow_ratio,
        "midtone_ratio": midtone_ratio,
        "highlight_ratio": highlight_ratio,
    }


def compute_visual_weight(frame: np.ndarray) -> tuple[float, float]:
    """Compute the visual weight center of a frame (0-1 normalized x, y).

    Brighter and more saturated regions have more visual weight.
    """
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY).astype(np.float32)
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
    saturation = hsv[:, :, 1] / 255.0

    # Visual weight = brightness * 0.6 + saturation * 0.4
    weight_map = (gray / 255.0) * 0.6 + saturation * 0.4
    total_weight = weight_map.sum()

    if total_weight < 1e-6:
        return 0.5, 0.5

    y_coords, x_coords = np.mgrid[0:h, 0:w]
    vw_x = float(np.sum(x_coords * weight_map) / total_weight / w)
    vw_y = float(np.sum(y_coords * weight_map) / total_weight / h)

    return round(vw_x, 3), round(vw_y, 3)


def compute_nine_grid(frame: np.ndarray, bboxes: list[list[float]]) -> list[float]:
    """Compute subject coverage in each of the 9 grid cells (3x3 rule of thirds).

    Returns [TL, TC, TR, ML, MC, MR, BL, BC, BR] — each 0-1 representing
    the fraction of that grid cell covered by any subject bbox.
    """
    h, w = frame.shape[:2]
    grid = [0.0] * 9

    # Grid boundaries in normalized coords
    cols = [0, 1 / 3, 2 / 3, 1.0]
    rows = [0, 1 / 3, 2 / 3, 1.0]

    for bbox in bboxes:
        if len(bbox) < 4:
            continue
        bx1, by1, bx2, by2 = bbox
        bbox_area = (bx2 - bx1) * (by2 - by1)
        if bbox_area < 1e-6:
            continue

        for r in range(3):
            for c in range(3):
                # Intersection with this grid cell
                gx1, gy1 = cols[c], rows[r]
                gx2, gy2 = cols[c + 1], rows[r + 1]

                ix1 = max(bx1, gx1)
                iy1 = max(by1, gy1)
                ix2 = min(bx2, gx2)
                iy2 = min(by2, gy2)

                if ix2 > ix1 and iy2 > iy1:
                    inter_area = (ix2 - ix1) * (iy2 - iy1)
                    cell_area = (gx2 - gx1) * (gy2 - gy1)
                    grid[r * 3 + c] += inter_area / cell_area

    # Cap at 1.0
    return [round(min(1.0, v), 3) for v in grid]
