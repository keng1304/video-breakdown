"""音樂結構偵測 + 踩拍偏移量分析 (Round 5B)。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class MusicSection:
    name: str      # intro / verse / build / drop / outro
    start_sec: float
    end_sec: float
    avg_energy: float = 0.0
    bpm: float = 0.0


@dataclass
class BeatAnalysis:
    timestamps: list[float] = field(default_factory=list)
    bpm: float = 0.0
    sections: list[MusicSection] = field(default_factory=list)
    energy_curve: list[float] = field(default_factory=list)


@dataclass
class CutTimingAnalysis:
    """每個 cut 相對最近 beat 的偏移量。"""
    shot_index: int
    cut_timestamp: float
    nearest_beat: float
    offset_frames: int  # negative = pre-beat, positive = post-beat
    beat_type: str      # "pre_beat", "on_beat", "post_beat"


def analyze_music_structure(audio_path: str | Path, fps: float = 30.0) -> BeatAnalysis:
    """完整音樂結構分析：beats + sections + energy curve。"""
    audio_path = Path(audio_path)
    if not audio_path.exists():
        return BeatAnalysis()

    try:
        import librosa
        import numpy as np
    except ImportError:
        log.warning("librosa not available")
        return BeatAnalysis()

    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    hop = 512

    # BPM + beats
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop)
    bpm = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop).tolist()

    # Energy curve
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    rms_norm = (rms / (rms.max() if rms.max() > 0 else 1.0)).tolist()

    # Section detection
    sections = _detect_sections(y, sr, rms, hop, bpm, len(rms))

    return BeatAnalysis(
        timestamps=beat_times,
        bpm=bpm,
        sections=sections,
        energy_curve=rms_norm,
    )


def _detect_sections(y, sr, rms, hop, bpm, total_frames) -> list[MusicSection]:
    """偵測 intro / verse / build / drop / outro。"""
    import numpy as np
    import librosa

    total_sec = len(y) / sr
    if total_sec < 5:
        return [MusicSection("full", 0, total_sec)]

    # Spectral flux for section boundary detection
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)

    # Simplified section segmentation based on energy profile
    energy = np.array(rms)
    n = len(energy)
    if n == 0:
        return [MusicSection("full", 0, total_sec)]

    # Smooth energy
    window = max(1, int(sr / hop * 2))  # 2-second window
    smoothed = np.convolve(energy, np.ones(window) / window, mode='same')

    # Simple heuristic: divide into 5 sections based on energy pattern
    section_boundaries_frac = []
    max_energy = smoothed.max() if smoothed.max() > 0 else 1

    # Intro: first 15% or until energy > 0.4 * max
    intro_end_frame = 0
    for i, e in enumerate(smoothed):
        if e > max_energy * 0.4 or i > n * 0.2:
            intro_end_frame = i
            break

    # Drop: find energy peak after 50% mark
    drop_start_frame = int(n * 0.5)
    peak_window = smoothed[int(n * 0.5):]
    if len(peak_window) > 0:
        peak_offset = int(np.argmax(peak_window))
        drop_start_frame = int(n * 0.5) + peak_offset

    # Outro: last 15%
    outro_start_frame = int(n * 0.85)

    # Build: between intro end and drop start
    build_start_frame = max(intro_end_frame, int(n * 0.35))
    verse_end_frame = build_start_frame

    def frame_to_sec(f):
        return librosa.frames_to_time(f, sr=sr, hop_length=hop)

    def section_energy(start_f, end_f):
        if start_f >= end_f or start_f >= len(energy):
            return 0.0
        return float(np.mean(energy[start_f:min(end_f, len(energy))]))

    sections = [
        MusicSection("intro", 0, frame_to_sec(intro_end_frame), section_energy(0, intro_end_frame), bpm),
        MusicSection("verse", frame_to_sec(intro_end_frame), frame_to_sec(verse_end_frame), section_energy(intro_end_frame, verse_end_frame), bpm),
        MusicSection("build", frame_to_sec(build_start_frame), frame_to_sec(drop_start_frame), section_energy(build_start_frame, drop_start_frame), bpm),
        MusicSection("drop", frame_to_sec(drop_start_frame), frame_to_sec(outro_start_frame), section_energy(drop_start_frame, outro_start_frame), bpm),
        MusicSection("outro", frame_to_sec(outro_start_frame), total_sec, section_energy(outro_start_frame, n), bpm),
    ]

    # Filter out zero-duration sections
    return [s for s in sections if s.end_sec > s.start_sec + 0.1]


def analyze_cut_timing(
    cut_timestamps: list[float],
    beat_timestamps: list[float],
    fps: float = 30.0,
    threshold_frames: int = 2,
) -> list[CutTimingAnalysis]:
    """分析每個剪接點相對最近 beat 的偏移量。"""
    if not beat_timestamps:
        return []

    results = []
    beat_arr = beat_timestamps

    for idx, cut_ts in enumerate(cut_timestamps):
        # Find nearest beat
        nearest_idx = min(range(len(beat_arr)), key=lambda i: abs(beat_arr[i] - cut_ts))
        nearest_beat = beat_arr[nearest_idx]

        # Offset in frames
        offset_sec = cut_ts - nearest_beat
        offset_frames = int(round(offset_sec * fps))

        # Classify
        if abs(offset_frames) <= threshold_frames:
            beat_type = "on_beat"
        elif offset_frames < 0:
            beat_type = "pre_beat"
        else:
            beat_type = "post_beat"

        results.append(CutTimingAnalysis(
            shot_index=idx,
            cut_timestamp=cut_ts,
            nearest_beat=nearest_beat,
            offset_frames=offset_frames,
            beat_type=beat_type,
        ))

    return results


def get_section_for_time(sections: list[MusicSection], time_sec: float) -> str:
    """查詢某個時間點屬於哪個音樂段落。"""
    for s in sections:
        if s.start_sec <= time_sec < s.end_sec:
            return s.name
    return "unknown"
