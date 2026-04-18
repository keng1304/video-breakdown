"""Director style synthesis — thin wrapper; main logic is in statistics.py."""

from __future__ import annotations

from director.fingerprint.statistics import compute_fingerprint
from director.structure.schema import DirectorFingerprint, ShotData


def generate_style_fingerprint(shots: list[ShotData], total_duration: float) -> DirectorFingerprint:
    """Generate director style fingerprint (delegates to statistics module)."""
    return compute_fingerprint(shots, total_duration)
