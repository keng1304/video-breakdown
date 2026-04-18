"""Cross-shot statistics for director fingerprinting — enhanced with audio-visual sync."""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np

from director.structure.schema import DirectorFingerprint, ShotData

log = logging.getLogger(__name__)


def compute_fingerprint(shots: list[ShotData], total_duration: float) -> DirectorFingerprint:
    """Compute director style fingerprint from all shots."""
    if not shots:
        return DirectorFingerprint()

    durations = [s.duration_sec for s in shots]
    n = len(shots)

    # ── Duration statistics ──
    avg_dur = float(np.mean(durations))
    median_dur = float(np.median(durations))
    std_dur = float(np.std(durations))
    cpm = (n / total_duration * 60) if total_duration > 0 else 0

    # ── Distributions ──
    shot_sizes = Counter(s.composition.shot_size for s in shots)
    transitions = Counter()
    for s in shots:
        transitions[s.transition_in] += 1
    camera_motions = Counter(s.camera_motion.type for s in shots)

    # ── Pacing classification ──
    if avg_dur < 1.0:
        pacing = "fast_cut"
    elif avg_dur < 2.5:
        pacing = "moderate"
    elif avg_dur < 5.0:
        pacing = "slow_burn"
    else:
        pacing = "very_slow"

    # Check for rhythmic pattern (low coefficient of variation)
    cv = std_dur / avg_dur if avg_dur > 0 else 1
    if cv < 0.25 and n > 5:
        pacing = "rhythmic"

    # Check for irregular pattern (high cv + some very short and very long)
    if cv > 0.8 and n > 5:
        pacing = "irregular"

    # ── Audio-visual sync analysis ──
    beat_sync_count = sum(1 for s in shots if s.audio_sync.is_on_beat_cut)
    beat_sync_ratio = beat_sync_count / max(n, 1)

    # Energy-cut correlation: do cuts tend to happen at high energy moments?
    high_energy_cuts = sum(1 for s in shots if s.audio_sync.energy_level > 0.6)
    energy_cut_ratio = high_energy_cuts / max(n, 1)

    # ── Rhythm pattern description ──
    rhythm_parts = []
    if beat_sync_ratio > 0.7:
        rhythm_parts.append("強節拍同步剪輯")
    elif beat_sync_ratio > 0.4:
        rhythm_parts.append("部分踩拍")
    else:
        rhythm_parts.append("自由節奏")

    if energy_cut_ratio > 0.6:
        rhythm_parts.append("高能量切換")

    # Detect acceleration/deceleration patterns
    if n >= 5:
        first_half = durations[:n // 2]
        second_half = durations[n // 2:]
        if np.mean(first_half) > np.mean(second_half) * 1.3:
            rhythm_parts.append("漸快")
        elif np.mean(second_half) > np.mean(first_half) * 1.3:
            rhythm_parts.append("漸慢")

    rhythm_pattern = " / ".join(rhythm_parts)

    # ── Camera motion analysis ──
    # Calculate motion intensity distribution
    intensities = [s.camera_motion.intensity for s in shots]
    avg_intensity = float(np.mean(intensities))
    motion_diversity = len(set(s.camera_motion.type for s in shots))

    # ── Dominant characteristics ──
    dominant_sizes = [s for s, _ in shot_sizes.most_common(3)]
    sig_moves = [m for m, _ in camera_motions.most_common(5) if m != "static"][:3]

    # ── Color fingerprint ──
    all_colors = []
    for s in shots:
        all_colors.extend(s.color.dominant_palette[:2])
    color_counter = Counter(all_colors)
    color_fingerprint = [c for c, _ in color_counter.most_common(8)]

    # ── Shot size progression ──
    # Track how shot sizes change: does the video tend to cut wide→close or close→wide?
    size_order = {"extreme_wide": 0, "wide": 1, "medium_wide": 2, "medium": 3,
                  "medium_close_up": 4, "close_up": 5, "extreme_close_up": 6}
    size_transitions = []
    for i in range(len(shots) - 1):
        s1 = size_order.get(shots[i].composition.shot_size, 3)
        s2 = size_order.get(shots[i + 1].composition.shot_size, 3)
        size_transitions.append(s2 - s1)

    if size_transitions:
        avg_size_change = np.mean(size_transitions)
        if avg_size_change > 0.5:
            rhythm_parts.append("趨向特寫")
        elif avg_size_change < -0.5:
            rhythm_parts.append("趨向全景")

    fp = DirectorFingerprint(
        total_shots=n,
        total_duration_sec=round(total_duration, 2),
        cuts_per_minute=round(cpm, 1),
        avg_shot_duration=round(avg_dur, 2),
        median_shot_duration=round(median_dur, 2),
        shot_duration_std=round(std_dur, 2),
        shot_size_distribution=dict(shot_sizes),
        transition_distribution=dict(transitions),
        camera_motion_distribution=dict(camera_motions),
        pacing=pacing,
        dominant_shot_sizes=dominant_sizes,
        signature_camera_moves=sig_moves,
        color_fingerprint=color_fingerprint,
        rhythm_pattern=rhythm_pattern,
    )

    log.info(
        "Fingerprint: %d shots, %.1f CPM, pacing=%s, beat_sync=%.0f%%, motion_diversity=%d",
        n, cpm, pacing, beat_sync_ratio * 100, motion_diversity,
    )
    return fp
