"""Backing swap: line a clean instrumental up with the backing captured in the room.

A home take is usually sung over a karaoke track played through a speaker, so
the separated "instrumental" is that speaker heard through the room — dull,
thin, roomy. If the singer has the karaoke file itself, it can replace the
captured backing outright. The only hard part is timing, and the captured
backing is exactly the reference needed: the clean track is placed where its
own sound already is in the recording.

Two passes:

1. **Coarse** — onset-strength (spectral flux) cross-correlation of the whole
   tracks at 100 frames/s. Robust to the room's tone and level, and searching
   the full length handles a track started anywhere (even before the
   recording began).
2. **Fine** — high-passed log-energy envelopes at 1 ms resolution, compared
   only within ±60 ms of the coarse lag, so a looping synth pattern can't
   pull the answer a bar away (observed: independent 15 s windows on Blinding
   Lights landed anywhere from -105 s to +88 s; constrained, they agreed to
   within 30 ms).

Drift is checked by repeating the fine pass on windows across the song: a
clean track playing at a slightly different speed shows up as a spread, which
is reported (with a warning past 50 ms) rather than silently ignored.
"""

from __future__ import annotations

from math import gcd

import numpy as np
from scipy import signal

from .. import audio_io

COARSE_FPS = 100
FINE_HOP_S = 0.001
FINE_SEARCH_S = 0.06
DRIFT_WARN_S = 0.05


def _onset_strength(mono: np.ndarray, sr: int) -> np.ndarray:
    hop = sr // COARSE_FPS
    win = 2048 if sr > 32000 else 1024
    _, _, z = signal.stft(mono, sr, nperseg=win, noverlap=win - hop, boundary=None)
    flux = np.maximum(np.diff(np.log1p(np.abs(z)), axis=1), 0).sum(axis=0)
    return (flux - flux.mean()) / (flux.std() + 1e-12)


def _fine_hop(sr: int) -> int:
    return max(1, int(FINE_HOP_S * sr))


def _fine_envelope(mono: np.ndarray, sr: int) -> np.ndarray:
    hop = _fine_hop(sr)
    n = len(mono) // hop
    e = np.log(np.sqrt(np.mean(mono[: n * hop].reshape(n, hop) ** 2, axis=1)) + 1e-6)
    k = int(0.2 / FINE_HOP_S)
    return e - np.convolve(e, np.ones(k) / k, mode="same")


def _lag_curve(a: np.ndarray, b: np.ndarray, start: int, lags: range) -> np.ndarray:
    """Correlation of a against b[start + lag:] for every lag (NaN off the end)."""
    a = a - a.mean()
    na = np.linalg.norm(a) + 1e-12
    out = np.full(len(lags), np.nan)
    for i, lag in enumerate(lags):
        s = start + lag
        if s < 0 or s + len(a) > len(b):
            continue
        seg = b[s : s + len(a)]
        seg = seg - seg.mean()
        out[i] = np.dot(a, seg) / (na * (np.linalg.norm(seg) + 1e-12))
    return out


def _best_lag(a: np.ndarray, b: np.ndarray, start: int, lags: range) -> tuple[int, float]:
    """Lag (in b frames) maximizing correlation of a against b[start + lag:]."""
    curve = _lag_curve(a, b, start, lags)
    if np.all(np.isnan(curve)):
        return 0, -np.inf
    i = int(np.nanargmax(curve))
    return lags[i], float(curve[i])


def find_offset(clean: np.ndarray, captured: np.ndarray, sr: int) -> dict:
    """Where the clean track starts inside the captured recording, in seconds.

    Positive: the clean track starts that long after the recording began.
    """
    c = audio_io.to_mono(clean).astype(np.float64)
    r = audio_io.to_mono(captured).astype(np.float64)

    oc, orr = _onset_strength(c, sr), _onset_strength(r, sr)
    xc = signal.fftconvolve(orr, oc[::-1])
    coarse = int(np.argmax(xc)) - (len(oc) - 1)
    coarse_peak = float(xc.max() / min(len(oc), len(orr)))

    ec, er = _fine_envelope(c, sr), _fine_envelope(r, sr)
    # Frames per second of the fine envelope. Exact, not 1/FINE_HOP_S: the hop
    # is a whole number of samples (44 at 44.1 kHz = 0.998 ms), and treating it
    # as 1 ms put a 10 s offset 23 ms late.
    per_s = sr / _fine_hop(sr)
    base = int(round(coarse / COARSE_FPS * per_s))
    reach = int(FINE_SEARCH_S * per_s)
    span = range(-reach, reach + 1)

    # Fine offset: correlation-vs-lag curves from windows across the song are
    # SUMMED and the peak of the sum is taken — steadier than any one window
    # when a room-captured backing correlates at only r~0.2.
    win = int(10 * per_s)
    starts = range(0, max(1, len(ec) - win), win)
    curves, peaks = [], []
    for s0 in starts:
        c = _lag_curve(ec[s0 : s0 + win], er, s0 + base, span)
        if np.all(np.isnan(c)):
            continue
        curves.append(c)
        peaks.append((base + span[int(np.nanargmax(c))]) / per_s)
    if not curves:
        return {"offset_s": coarse / COARSE_FPS, "method": "coarse_only",
                "coarse_peak": round(coarse_peak, 3), "windows": 0,
                "warning": "no overlap long enough for fine alignment"}

    total = np.nansum(np.vstack(curves), axis=0)
    i = int(np.argmax(total))
    # Parabolic interpolation for sub-millisecond resolution.
    frac = 0.0
    if 0 < i < len(total) - 1:
        y0, y1, y2 = total[i - 1], total[i], total[i + 1]
        den = y0 - 2 * y1 + y2
        frac = 0.5 * (y0 - y2) / den if den else 0.0
    peaks = np.asarray(peaks)
    report = {
        "offset_s": round((base + span[i] + frac) / per_s, 4),
        "method": "onset_xcorr+summed_envelope_refine",
        "coarse_offset_s": round(coarse / COARSE_FPS, 3),
        "coarse_peak": round(coarse_peak, 3),
        "windows": int(len(curves)),
        # Middle 80% of per-window peaks: robust to the odd confused window.
        "drift_spread_s": round(float(np.percentile(peaks, 90) - np.percentile(peaks, 10)), 4),
        "peak_r": round(float(total[i] / len(curves)), 3),
    }
    if report["drift_spread_s"] > DRIFT_WARN_S:
        report["warning"] = (f"timing drifts {report['drift_spread_s'] * 1000:.0f} ms across "
                             "the song — the clean track may be a different speed or edit")
    return report


def place(clean: np.ndarray, sr: int, offset_s: float, n_samples: int, channels: int) -> np.ndarray:
    """Lay ``clean`` into a silent (channels, n_samples) buffer at ``offset_s``."""
    clean = np.atleast_2d(clean)
    if clean.shape[0] != channels:
        clean = np.repeat(clean[:1], channels, axis=0) if clean.shape[0] == 1 else \
            np.repeat(clean.mean(axis=0, keepdims=True), channels, axis=0)
    out = np.zeros((channels, n_samples), dtype=np.float32)
    s = int(round(offset_s * sr))
    src0 = max(0, -s)
    dst0 = max(0, s)
    n = min(clean.shape[1] - src0, n_samples - dst0)
    if n > 0:
        out[:, dst0 : dst0 + n] = clean[:, src0 : src0 + n]
    return out


def load_backing(path, sr: int) -> np.ndarray:
    """Load a clean instrumental at the session's sample rate."""
    x, xsr = audio_io.load(path)
    if xsr != sr:
        g = gcd(int(xsr), int(sr))
        x = signal.resample_poly(x, int(sr) // g, int(xsr) // g, axis=1).astype(np.float32)
    return x


def swap_backing(captured: np.ndarray, sr: int, path, offset_s: float | None = None) -> tuple[np.ndarray, dict]:
    """Replace the captured backing with the clean track at the right time."""
    clean = load_backing(path, sr)
    if offset_s is None:
        report = find_offset(clean, captured, sr)
    else:
        report = {"offset_s": float(offset_s), "method": "given"}
    captured = np.atleast_2d(captured)
    placed = place(clean, sr, report["offset_s"], captured.shape[1], captured.shape[0])
    report["source"] = str(path)
    return placed, report
