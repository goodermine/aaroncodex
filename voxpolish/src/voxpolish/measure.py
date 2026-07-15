"""Loudness and peak measurement (BS.1770 via pyloudnorm).

All balance decisions use *vocal-active* measurements: loudness is computed
over the concatenated speech-guard intervals so instrumental intros, solos,
and gaps cannot skew stem ratios.
"""

from __future__ import annotations

import numpy as np
import pyloudnorm as pyln
from scipy import signal

# Below this much usable audio the BS.1770 meter is meaningless.
MIN_MEASURE_S = 0.5
# Below this much vocal-active time, fall back to full-length measurement.
MIN_ACTIVE_S = 5.0


def integrated_lufs(audio: np.ndarray, sr: int) -> float | None:
    """BS.1770 integrated loudness of (channels, samples) audio, or None."""
    audio = np.atleast_2d(audio)
    if audio.shape[1] < int(MIN_MEASURE_S * sr):
        return None
    val = pyln.Meter(sr).integrated_loudness(audio.T.astype(np.float64))
    return None if not np.isfinite(val) else float(val)


def active_audio(audio: np.ndarray, sr: int, intervals: list) -> np.ndarray:
    """Concatenate the samples inside [start, end] second intervals."""
    audio = np.atleast_2d(audio)
    segs = [audio[:, int(s * sr) : int(e * sr)] for s, e in intervals]
    segs = [s for s in segs if s.shape[1]]
    return np.concatenate(segs, axis=1) if segs else audio[:, :0]


def active_lufs(audio: np.ndarray, sr: int, intervals: list) -> tuple[float | None, str]:
    """Integrated loudness over vocal-active intervals.

    Returns (lufs, basis) where basis is "active" or "full" (fallback when
    active time is too short to be robust).
    """
    act = active_audio(audio, sr, intervals)
    if act.shape[1] >= int(MIN_ACTIVE_S * sr):
        val = integrated_lufs(act, sr)
        if val is not None:
            return val, "active"
    return integrated_lufs(audio, sr), "full"


def true_peak_db(audio: np.ndarray, sr: int) -> float:
    """True peak in dBTP via 4x oversampling (BS.1770 approximation)."""
    audio = np.atleast_2d(audio)
    if not audio.shape[1]:
        return -np.inf
    up = signal.resample_poly(audio.astype(np.float64), 4, 1, axis=1)
    peak = max(np.max(np.abs(up)), np.max(np.abs(audio)))
    return float(20 * np.log10(peak + 1e-12))


def loudness_range_lu(audio: np.ndarray, sr: int) -> float | None:
    """LRA per EBU Tech 3342 (approximated with 3 s / 1 s-hop windows)."""
    audio = np.atleast_2d(audio)
    n = audio.shape[1]
    win, hop = int(3.0 * sr), int(1.0 * sr)
    if n < int(MIN_MEASURE_S * sr):
        return None
    meter = pyln.Meter(sr)
    vals = []
    for start in range(0, max(1, n - win + 1), hop) if n >= win else [0]:
        seg = audio[:, start : start + win] if n >= win else audio
        v = meter.integrated_loudness(seg.T.astype(np.float64))
        if np.isfinite(v):
            vals.append(v)
    vals = np.asarray([v for v in vals if v > -70.0])
    if len(vals) < 2:
        return 0.0
    energy_mean = 10 * np.log10(np.mean(10 ** (vals / 10)))
    gated = vals[vals >= energy_mean - 20]
    if len(gated) < 2:
        return 0.0
    return float(np.percentile(gated, 95) - np.percentile(gated, 10))
