"""Shared DSP helpers used by analysis and render."""

from __future__ import annotations

import numpy as np
from scipy import signal

EPS = 1e-10


def frame_rms_db(x: np.ndarray, sr: int, window_s: float, hop_s: float) -> tuple[np.ndarray, np.ndarray]:
    """Framewise RMS level in dBFS. Returns (times, levels_db); times are frame centers."""
    win = max(1, int(window_s * sr))
    hop = max(1, int(hop_s * sr))
    n_frames = max(1, 1 + (len(x) - win) // hop) if len(x) >= win else 1
    times = np.empty(n_frames)
    levels = np.empty(n_frames)
    for i in range(n_frames):
        seg = x[i * hop : i * hop + win]
        times[i] = (i * hop + len(seg) / 2) / sr
        levels[i] = 20 * np.log10(np.sqrt(np.mean(seg**2) + EPS))
    return times, levels


def smooth_exponential(x: np.ndarray, hop_s: float, time_constant_s: float) -> np.ndarray:
    """Bidirectional exponential smoothing (zero-lag) of a framewise curve."""
    if time_constant_s <= 0:
        return x.copy()
    alpha = 1 - np.exp(-hop_s / time_constant_s)
    fwd = np.empty_like(x)
    acc = x[0]
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        fwd[i] = acc
    bwd = np.empty_like(x)
    acc = fwd[-1]
    for i in range(len(fwd) - 1, -1, -1):
        acc += alpha * (fwd[i] - acc)
        bwd[i] = acc
    return bwd


def spectral_flatness(mag: np.ndarray) -> np.ndarray:
    """Per-frame spectral flatness (0..1) from a magnitude spectrogram (bins, frames)."""
    gmean = np.exp(np.mean(np.log(mag + EPS), axis=0))
    amean = np.mean(mag, axis=0) + EPS
    return gmean / amean


def band_energy_db(mag: np.ndarray, freqs: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Per-frame energy in [lo, hi] Hz of a magnitude spectrogram, in dB."""
    band = (freqs >= lo) & (freqs < hi)
    e = np.sum(mag[band] ** 2, axis=0)
    return 10 * np.log10(e + EPS)


def merge_frames_to_regions(
    mask: np.ndarray, times: np.ndarray, min_dur_s: float, merge_gap_s: float
) -> list[tuple[float, float]]:
    """Turn a boolean frame mask into (start, end) regions, merging small gaps."""
    regions: list[list[float]] = []
    hop = float(times[1] - times[0]) if len(times) > 1 else 0.01
    for i, on in enumerate(mask):
        if not on:
            continue
        start, end = times[i] - hop / 2, times[i] + hop / 2
        if regions and start - regions[-1][1] <= merge_gap_s:
            regions[-1][1] = end
        else:
            regions.append([start, end])
    return [(max(0.0, s), e) for s, e in regions if e - s >= min_dur_s]


def fade_envelope(
    n_samples: int, sr: int, regions: list, base_db: float = 0.0
) -> np.ndarray:
    """Build a per-sample gain envelope (dB) that dips into each Region with linear fades."""
    env = np.full(n_samples, base_db, dtype=np.float64)
    for r in regions:
        s = int(round(r.start * sr))
        e = int(round(r.end * sr))
        s, e = max(0, s), min(n_samples, e)
        if e <= s:
            continue
        fade = min(int(r.fade_ms / 1000 * sr), (e - s) // 2)
        depth = r.reduction_db
        env[s + fade : e - fade] = np.minimum(env[s + fade : e - fade], depth)
        if fade > 0:
            ramp = np.linspace(0.0, 1.0, fade)
            env[s : s + fade] = np.minimum(env[s : s + fade], depth * ramp)
            env[e - fade : e] = np.minimum(env[e - fade : e], depth * ramp[::-1])
    return env


def band_split(x: np.ndarray, sr: int, split_hz: float, order: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """Zero-phase split into (low, high) bands that sum back to ~x."""
    nyq = sr / 2
    split_hz = min(split_hz, nyq * 0.95)
    sos = signal.butter(order, split_hz / nyq, btype="low", output="sos")
    low = signal.sosfiltfilt(sos, x)
    return low, x - low
