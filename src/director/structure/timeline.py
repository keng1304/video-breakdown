"""Timeline alignment engine: merge all pipeline outputs per shot."""

from __future__ import annotations

import logging

from director.structure.schema import (
    AudioFeatures,
    AudioSync,
    CameraMotion,
    CharacterPose,
    ShotBoundary,
    ShotData,
)

log = logging.getLogger(__name__)


def format_timecode(seconds: float) -> str:
    """Format seconds as MM:SS.mmm."""
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:06.3f}"


def align_timeline(
    shots: list[ShotBoundary],
    camera_motions: dict[int, CameraMotion],
    poses: dict[int, list[CharacterPose]],
    audio: AudioFeatures,
) -> list[ShotData]:
    """Merge all Layer 1 outputs into per-shot ShotData objects."""
    result = []

    for shot in shots:
        idx = shot.shot_index

        # Camera motion for this shot
        cam = camera_motions.get(idx, CameraMotion())

        # Poses for this shot
        chars = poses.get(idx, [])

        # Audio sync: slice beat/onset timestamps within shot time range
        beat_positions = [
            round(t - shot.start_sec, 3)
            for t in audio.beat_timestamps
            if shot.start_sec <= t <= shot.end_sec
        ]
        onset_in_shot = [
            t for t in audio.onset_timestamps
            if shot.start_sec <= t <= shot.end_sec
        ]

        # Check if this cut is on a beat
        is_on_beat = False
        for bt in audio.beat_timestamps:
            if abs(bt - shot.start_sec) < 0.08:  # within 80ms of a beat
                is_on_beat = True
                break

        # Compute energy level for this shot from energy curve
        energy_level = 0.0
        if audio.energy_curve and audio.beat_timestamps:
            # Map shot time range to energy curve indices
            total_dur = audio.beat_timestamps[-1] if audio.beat_timestamps else 1.0
            curve_len = len(audio.energy_curve)
            if total_dur > 0:
                i_start = int(shot.start_sec / total_dur * curve_len)
                i_end = int(shot.end_sec / total_dur * curve_len)
                i_start = max(0, min(i_start, curve_len - 1))
                i_end = max(i_start + 1, min(i_end, curve_len))
                shot_energy = audio.energy_curve[i_start:i_end]
                if shot_energy:
                    energy_level = round(sum(shot_energy) / len(shot_energy), 3)

        audio_sync = AudioSync(
            beat_positions=beat_positions,
            energy_level=energy_level,
            is_on_beat_cut=is_on_beat,
            onset_count=len(onset_in_shot),
        )

        shot_data = ShotData(
            shot_index=idx,
            timecode_start=format_timecode(shot.start_sec),
            timecode_end=format_timecode(shot.end_sec),
            duration_sec=shot.duration_sec,
            transition_in=shot.transition_in,
            transition_out=shot.transition_out,
            camera_motion=cam,
            characters=chars,
            audio_sync=audio_sync,
        )
        result.append(shot_data)

    log.info("Timeline aligned: %d shots", len(result))
    return result
