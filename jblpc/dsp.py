"""
Acoustic DSP utility module for Parametric Equalization (PEQ) and headroom scaling.

Prevents digital clipping (intersample peak distortion at 0 dBFS) by computing
pre-amp attenuation (headroom trim) based on maximum band gain boosts.
"""

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class PEQBand:
    """Parametric EQ Band configuration."""
    frequency_hz: float
    gain_db: float
    q_factor: float = 1.414  # Standard Butterworth/peaking Q
    filter_type: str = "peaking"  # "peaking", "low_shelf", "high_shelf"


def calculate_preamp_headroom(gains_db: Sequence[float]) -> float:
    """
    Calculate required pre-amp attenuation (negative gain in dB) to avoid clipping.

    If any band has positive gain, the master pre-amp must attenuate by at least
    the peak boost value to keep the composite filter response below 0 dBFS.

    Example:
        gains = [6.0, 4.0, 0.0, -2.0]
        peak = 6.0 dB
        preamp_headroom = -6.0 dB
    """
    if not gains_db:
        return 0.0
    peak_gain = max(gains_db)
    if peak_gain > 0.0:
        return -peak_gain
    return 0.0


def normalize_band_gains_with_headroom(
    gains_db: Sequence[float],
    min_db: float = -12.0,
    max_db: float = 12.0,
) -> tuple[list[float], float]:
    """
    Clamp band gains to [min_db, max_db] and compute recommended pre-amp trim.

    Returns:
        (clamped_gains, preamp_trim_db)
    """
    clamped = [max(min_db, min(max_db, float(g))) for g in gains_db]
    headroom = calculate_preamp_headroom(clamped)
    return clamped, headroom

