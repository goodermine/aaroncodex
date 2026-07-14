"""Sibilance analysis: find harsh S/T/SH events and decide per-event reduction.

Event-based rather than a static de-esser: each detected sibilant becomes an
editable Region with its own band-limited gain reduction.
"""

from __future__ import annotations

import numpy as np
from scipy import signal

from .. import dsp
from ..document import Region

SIB_LO, SIB_HI = 4500.0, 10000.0
REF_LO, REF_HI = 200.0, 3000.0


def analyze(
    mono: np.ndarray,
    sr: int,
    speech_times: np.ndarray | None = None,
    speech_mask: np.ndarray | None = None,
    sensitivity: float = 0.5,
    threshold_db: float = -3.0,
    max_reduction_db: float = 10.0,
) -> list[Region]:
    nper = 1024
    freqs, times, stft = signal.stft(mono, sr, nperseg=nper, noverlap=nper - 256)
    mag = np.abs(stft)

    high = dsp.band_energy_db(mag, freqs, SIB_LO, min(SIB_HI, sr / 2 * 0.95))
    ref = dsp.band_energy_db(mag, freqs, REF_LO, REF_HI)
    ratio = high - ref

    # A frame is sibilant when highs dominate the mids AND the highs are loud
    # in absolute terms (so quiet noise doesn't trigger events).
    loud_high = high > np.percentile(high, 75)
    sib = (ratio > threshold_db) & loud_high
    if speech_mask is not None and speech_times is not None and len(speech_times) > 1:
        sib &= np.interp(times, speech_times, speech_mask.astype(float)) > 0.5

    regions = []
    for s, e in dsp.merge_frames_to_regions(sib, times, min_dur_s=0.03, merge_gap_s=0.02):
        frames = (times >= s) & (times <= e)
        excess = float(np.mean(np.maximum(0.0, ratio[frames] - threshold_db)))
        reduction = -min(max_reduction_db, max(2.0, excess * (0.5 + sensitivity)))
        regions.append(
            Region(start=round(s, 4), end=round(e, 4), reduction_db=round(reduction, 2),
                   fade_ms=10.0, band=[SIB_LO, SIB_HI], label="sibilant")
        )
    return regions
