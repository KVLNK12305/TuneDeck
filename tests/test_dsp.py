"""
Unit tests for acoustic DSP safety and headroom scaling (jblpc.dsp).
"""

import pytest
from jblpc.dsp import (
    calculate_preamp_headroom,
    normalize_band_gains_with_headroom,
    PEQBand,
)


def test_headroom_with_flat_eq():
    """Flat EQ (0 dB everywhere) requires 0 dB attenuation."""
    gains = [0.0] * 10
    assert calculate_preamp_headroom(gains) == 0.0


def test_headroom_with_cuts_only():
    """Cutting frequencies (negative gains only) does not clip; headroom is 0 dB."""
    gains = [-2.0, -4.0, -1.0, 0.0]
    assert calculate_preamp_headroom(gains) == 0.0


def test_headroom_with_positive_boost():
    """Boosting frequencies requires negative pre-amp trim equal to the peak boost."""
    gains = [6.0, 4.0, 2.0, 0.0, -1.0]
    # Peak boost is +6.0 dB, so required headroom is -6.0 dB
    assert calculate_preamp_headroom(gains) == -6.0


def test_headroom_empty_gains():
    """Empty gains list safely returns 0.0."""
    assert calculate_preamp_headroom([]) == 0.0


def test_normalize_band_gains():
    """Gain clamping to min/max limits and headroom calculation."""
    raw_gains = [15.0, 8.0, 0.0, -20.0]
    clamped, trim = normalize_band_gains_with_headroom(raw_gains, min_db=-12.0, max_db=12.0)

    # Clamped to +12 and -12
    assert clamped == [12.0, 8.0, 0.0, -12.0]
    # Peak boost is +12.0, so trim must be -12.0 dB
    assert trim == -12.0


def test_peq_band_dataclass():
    """PEQBand creates immutable configuration with defaults."""
    band = PEQBand(frequency_hz=1000.0, gain_db=3.5)
    assert band.frequency_hz == 1000.0
    assert band.gain_db == 3.5
    assert band.q_factor == 1.414
    assert band.filter_type == "peaking"

