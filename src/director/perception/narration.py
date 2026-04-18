"""Narration extraction — transcribe voiceover and align to shots.

Uses mlx-whisper (Apple Silicon native) for local transcription.
Output: timestamped segments that align to the shot timeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class NarrationSegment:
    start_sec: float
    end_sec: float
    text: str
    language: str = ""
    confidence: float = 0.0


@dataclass
class NarrationResult:
    segments: list[NarrationSegment] = field(default_factory=list)
    full_text: str = ""
    language: str = ""
    has_narration: bool = False


def transcribe_audio(
    audio_path: str | Path,
    language: str | None = None,
    model_size: str = "base",
) -> NarrationResult:
    """Transcribe audio using mlx-whisper (Apple Silicon optimized).

    Args:
        audio_path: Path to WAV audio file
        language: Force language (None = auto-detect)
        model_size: "tiny", "base", "small", "medium", "large-v3"
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        log.warning("Audio file not found: %s", audio_path)
        return NarrationResult()

    try:
        import mlx_whisper
    except ImportError:
        log.warning("mlx-whisper not installed, skipping transcription")
        return NarrationResult()

    model_name = f"mlx-community/whisper-{model_size}-mlx"
    log.info("Transcribing with %s: %s", model_name, audio_path)

    try:
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=model_name,
            language=language,
            word_timestamps=True,
        )
    except Exception as e:
        log.error("Transcription failed: %s", e)
        return NarrationResult()

    segments = []
    for seg in result.get("segments", []):
        segments.append(NarrationSegment(
            start_sec=round(seg["start"], 3),
            end_sec=round(seg["end"], 3),
            text=seg["text"].strip(),
            confidence=round(seg.get("avg_logprob", 0) * -1, 3),  # lower = more confident
        ))

    full_text = result.get("text", "").strip()
    lang = result.get("language", "")

    # Determine if there's meaningful narration (not just music/noise)
    has_narration = bool(segments) and len(full_text) > 20

    log.info("Transcribed: %d segments, language=%s, has_narration=%s",
             len(segments), lang, has_narration)

    return NarrationResult(
        segments=segments,
        full_text=full_text,
        language=lang,
        has_narration=has_narration,
    )


def align_narration_to_shots(
    narration: NarrationResult,
    shots: list,  # list of ShotBoundary or ShotData
) -> dict[int, list[NarrationSegment]]:
    """Align narration segments to shots by timecode overlap.

    Returns {shot_index: [NarrationSegment, ...]}.
    """
    if not narration.segments:
        return {}

    result = {}
    for shot in shots:
        shot_start = shot.start_sec if hasattr(shot, 'start_sec') else _tc_to_sec(shot.timecode_start)
        shot_end = shot.end_sec if hasattr(shot, 'end_sec') else _tc_to_sec(shot.timecode_end)
        idx = shot.shot_index

        aligned = []
        for seg in narration.segments:
            # Check overlap
            if seg.end_sec > shot_start and seg.start_sec < shot_end:
                aligned.append(seg)

        if aligned:
            result[idx] = aligned

    return result


def _tc_to_sec(tc: str) -> float:
    parts = tc.split(":")
    if len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return 0.0
