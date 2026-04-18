"""Audio analysis pipeline: BPM, beats, energy, onsets, speech/music/silence classification."""

from __future__ import annotations

import logging
from pathlib import Path

import librosa
import numpy as np

from director.config import get_config
from director.perception.base import PerceptionPipeline
from director.structure.schema import AudioFeatures

log = logging.getLogger(__name__)


class AudioAnalyzer(PerceptionPipeline):
    name = "audio"

    def load_model(self) -> None:
        pass

    def unload_model(self) -> None:
        pass

    def estimate_memory_gb(self) -> float:
        return 0.2

    def process(self, audio_path: str | Path, duration_sec: float = 0) -> AudioFeatures:
        cfg = get_config()
        audio_path = Path(audio_path)
        if not audio_path.exists():
            log.warning("No audio file found at %s, returning empty features", audio_path)
            return AudioFeatures()

        log.info("Loading audio: %s", audio_path)
        y, sr = librosa.load(str(audio_path), sr=cfg.audio_sr, mono=True)
        log.info("Audio loaded: %.1fs at %d Hz", len(y) / sr, sr)

        # ── BPM and beat tracking ──
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(np.atleast_1d(tempo)[0])
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        # ── Energy (RMS) with finer resolution ──
        hop_length = 512
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        rms_max = rms.max() if rms.max() > 0 else 1.0
        energy_normalized = rms / rms_max
        energy_curve = energy_normalized.tolist()
        avg_energy = float(np.mean(energy_normalized))

        # ── Onset detection ──
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length).tolist()

        # ── Spectral features for classification ──
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
        zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)

        # ── Segment classification: silence / speech / music ──
        segment_labels = _classify_segments(
            energy_normalized, spectral_centroid, zcr, spectral_rolloff, mfccs, sr, hop_length
        )

        # ── Dynamic range ──
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        dynamic_range = float(np.ptp(rms_db))  # peak-to-peak in dB

        # ── Energy contour stats ──
        # Detect energy build-ups and drops
        energy_diff = np.diff(energy_normalized)
        n_buildups = int(np.sum((energy_diff > 0.05)))
        n_drops = int(np.sum((energy_diff < -0.05)))

        features = AudioFeatures(
            bpm=round(bpm, 1),
            beat_timestamps=beat_times,
            energy_curve=energy_curve,
            onset_timestamps=onset_times,
            avg_energy=round(avg_energy, 3),
        )

        # Store extended features in a way that doesn't break the schema
        # Add them as extra data that gets serialized
        features._segment_labels = segment_labels
        features._dynamic_range_db = round(dynamic_range, 1)
        features._n_energy_buildups = n_buildups
        features._n_energy_drops = n_drops
        features._spectral_centroid_mean = round(float(np.mean(spectral_centroid)), 1)

        log.info(
            "Audio analysis: BPM=%.1f, %d beats, %d onsets, dynamic_range=%.1fdB, "
            "segments: %d silence / %d speech / %d music",
            bpm, len(beat_times), len(onset_times), dynamic_range,
            segment_labels.count("silence"),
            segment_labels.count("speech"),
            segment_labels.count("music"),
        )
        return features


def _classify_segments(
    energy: np.ndarray,
    centroid: np.ndarray,
    zcr: np.ndarray,
    rolloff: np.ndarray,
    mfccs: np.ndarray,
    sr: int,
    hop_length: int,
    segment_length_sec: float = 0.5,
) -> list[str]:
    """Classify audio into segments of silence / speech / music.

    Uses simple heuristics based on spectral features:
    - Silence: very low energy
    - Speech: moderate energy, lower spectral centroid, higher ZCR variance
    - Music: higher energy, higher spectral centroid, more tonal content
    """
    n_frames = len(energy)
    segment_frames = max(1, int(segment_length_sec * sr / hop_length))
    labels = []

    for start in range(0, n_frames, segment_frames):
        end = min(start + segment_frames, n_frames)
        seg_energy = np.mean(energy[start:end])
        seg_centroid = np.mean(centroid[start:end])
        seg_zcr = np.mean(zcr[start:end])
        seg_zcr_var = np.var(zcr[start:end])
        seg_rolloff = np.mean(rolloff[start:end])

        # MFCC variance (tonal content indicator)
        seg_mfcc_var = np.mean(np.var(mfccs[:, start:end], axis=1))

        if seg_energy < 0.05:
            labels.append("silence")
        elif seg_centroid < 2000 and seg_zcr_var > 0.001 and seg_mfcc_var > 5:
            # Speech: lower centroid, variable ZCR, variable MFCCs
            labels.append("speech")
        else:
            # Music: higher centroid or more stable spectral characteristics
            labels.append("music")

    return labels
