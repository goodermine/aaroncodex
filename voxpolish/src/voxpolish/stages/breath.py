"""Breath analysis: find breath sounds between phrases and turn them down.

Phase 0 heuristic: a breath is short, sits well above silence but well below
speech level, and is noise-like (high spectral flatness — voiced sound is
harmonic/band-limited, breaths are broadband). We deliberately do not require
the VAD to call it non-speech: simple energy VADs mark breaths as speech.
A trained classifier can replace this later behind the same API.
"""

from __future__ import annotations

import numpy as np
from scipy import signal

from .. import dsp
from ..document import Region


def analyze(
    mono: np.ndarray,
    sr: int,
    speech_times: np.ndarray,
    speech_mask: np.ndarray,
    reduction_db: float = -12.0,
    min_dur_s: float = 0.12,
    max_dur_s: float = 1.2,
    flatness_min: float = 0.25,
) -> list[Region]:
    if len(speech_times) < 2:
        return []
    times, levels = dsp.frame_rms_db(mono, sr, 0.03, 0.01)
    speech = np.interp(times, speech_times, speech_mask.astype(float)) > 0.5

    silence_floor = np.percentile(levels, 10)
    speech_level = np.percentile(levels[speech], 50) if speech.any() else np.max(levels)

    nper = 1024
    sfreqs, stimes, stft = signal.stft(mono, sr, nperseg=nper, noverlap=nper - 256)
    # Flatness of the breathy band only (300 Hz - 8 kHz), where breaths are broadband.
    band = (sfreqs >= 300) & (sfreqs <= min(8000, sr / 2 * 0.95))
    flat = dsp.spectral_flatness(np.abs(stft[band]))
    flat_i = np.interp(times, stimes, flat)

    candidate = (
        (levels > silence_floor + 6)
        & (levels < speech_level - 8)
        & (flat_i > flatness_min)
    )
    regions = []
    for s, e in dsp.merge_frames_to_regions(candidate, times, min_dur_s, merge_gap_s=0.05):
        if e - s <= max_dur_s:
            # Confidence from the flatness margin: broadband breaths score
            # high; washed/reverby lyric material hovers near the threshold
            # and must never override the speech guards.
            frames = (times >= s) & (times <= e)
            flat_mean = float(np.mean(flat_i[frames])) if frames.any() else flatness_min
            conf = float(np.clip((flat_mean - flatness_min) / (0.5 - flatness_min), 0.0, 1.0))
            regions.append(
                Region(start=round(s, 4), end=round(e, 4), reduction_db=reduction_db,
                       fade_ms=40.0, label="breath", confidence=round(conf, 3))
            )
    return regions
