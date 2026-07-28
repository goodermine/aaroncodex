"""Deliberate, known degradations — the ground truth the validity gates need.

A gate that detects "suspected compression" has nothing to be checked against.
There is no corpus of labelled compressed vocals, and a detector nobody can
check is worse than no detector: it lends degraded numbers the authority of
having passed validation. See docs/plans/STANDALONE_SONG_ANALYSIS_PLAN.md §5.1.

So the ground truth is manufactured. Take a clean recording, damage it in a way
whose parameters are known exactly, and require the gate to notice. A gate that
cannot catch damage we inflicted on purpose does not ship enabled.

These live in the package rather than in the test file on purpose: the claim
"this gate is validated" and the thing it was validated against must not be able
to drift apart.
"""

from __future__ import annotations

import numpy as np
import scipy.signal as sps


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x))) + 1e-12)


def clip(y: np.ndarray, headroom_db: float = -6.0) -> np.ndarray:
    """Drive the signal into the ceiling and hard-clip it.

    headroom_db is how far the pre-clip peak is pushed ABOVE full scale, so
    -6 dB of "headroom" means 6 dB of overdrive. Returns audio with a known
    proportion of samples pinned at ±1.
    """
    peak = float(np.max(np.abs(y))) + 1e-12
    return np.clip(y / peak * (10 ** (-headroom_db / 20.0)), -1.0, 1.0)


def add_noise(y: np.ndarray, snr_db: float, seed: int = 0) -> np.ndarray:
    """Pink noise at a known signal-to-noise ratio.

    Pink rather than white: room and preamp noise falls off with frequency, and
    a white-noise test would flatter any detector that keys on high-band energy.
    """
    rng = np.random.default_rng(seed)
    white = rng.standard_normal(len(y))
    # 1/f shaping in the frequency domain
    spec = np.fft.rfft(white)
    freqs = np.arange(len(spec))
    spec /= np.sqrt(np.maximum(freqs, 1.0))
    pink = np.fft.irfft(spec, n=len(y))
    pink *= _rms(y) / (_rms(pink) * (10 ** (snr_db / 20.0)))
    return (y + pink).astype(np.float32)


def reverb(y: np.ndarray, sr: int, rt60_s: float = 1.2, seed: int = 0) -> np.ndarray:
    """Convolve with a synthetic exponential-decay impulse response.

    Not a real room, but the decay constant is exactly known, which is what the
    RT60 proxy has to recover.
    """
    rng = np.random.default_rng(seed)
    n = int(sr * rt60_s)
    ir = rng.standard_normal(n) * np.exp(-6.9078 * np.arange(n) / n)  # -60 dB over rt60
    ir[0] += 1.0                                                      # keep the direct sound
    ir /= np.sqrt(np.sum(ir ** 2))
    wet = sps.fftconvolve(y, ir, mode="full")[: len(y)]
    return (0.6 * y + 0.4 * wet / (np.max(np.abs(wet)) + 1e-12) * np.max(np.abs(y))).astype(np.float32)


def compress(y: np.ndarray, sr: int, threshold_db: float = -24.0, ratio: float = 8.0,
             attack_ms: float = 5.0, release_ms: float = 80.0) -> np.ndarray:
    """Feed-forward compressor with a known ratio, then make-up gain.

    Make-up matters: a compressor that only turns things down is trivially
    detectable from level alone. Restoring the peak forces the detector to key
    on crest factor and level variance, which is what the spec asks of it.
    """
    env = np.abs(y).astype(np.float64)
    a_at = np.exp(-1.0 / (sr * attack_ms / 1000.0))
    a_rl = np.exp(-1.0 / (sr * release_ms / 1000.0))
    smoothed = np.empty_like(env)
    prev = 0.0
    for i, v in enumerate(env):                       # sample-accurate envelope
        coef = a_at if v > prev else a_rl
        prev = coef * prev + (1 - coef) * v
        smoothed[i] = prev
    level_db = 20 * np.log10(np.maximum(smoothed, 1e-9))
    over = np.maximum(level_db - threshold_db, 0.0)
    gain_db = -over * (1.0 - 1.0 / ratio)
    out = y * (10 ** (gain_db / 20.0))
    peak_in, peak_out = np.max(np.abs(y)) + 1e-12, np.max(np.abs(out)) + 1e-12
    return (out * (peak_in / peak_out)).astype(np.float32)


def shelf_eq(y: np.ndarray, sr: int, gain_db: float = 9.0, cutoff_hz: float = 3000.0) -> np.ndarray:
    """High shelf of known gain — the 'suspected EQ' ground truth."""
    nyq = sr / 2.0
    b, a = sps.butter(2, min(cutoff_hz / nyq, 0.99), btype="highpass")
    high = sps.filtfilt(b, a, y)
    out = y + high * (10 ** (gain_db / 20.0) - 1.0)
    return (out / (np.max(np.abs(out)) + 1e-12) * (np.max(np.abs(y)) + 1e-12)).astype(np.float32)


def quantise_pitch(y: np.ndarray, sr: int, hop: int = 512, strength: float = 1.0) -> np.ndarray:
    """Snap f0 to the nearest semitone, segment by segment — a crude auto-tune.

    Deliberately crude: the detector should key on the pitch histogram and on
    how sharply f0 moves between targets, not on the artefacts of one particular
    correction algorithm.
    """
    import librosa
    f0, _, _ = librosa.pyin(y, fmin=70, fmax=900, sr=sr, hop_length=hop)
    out = np.zeros_like(y)
    win = hop * 8
    for start in range(0, len(y) - win, win):
        seg = y[start:start + win]
        fi = slice(start // hop, max(start // hop + 1, (start + win) // hop))
        seg_f0 = f0[fi]
        seg_f0 = seg_f0[np.isfinite(seg_f0)]
        if len(seg_f0) == 0:
            out[start:start + win] += seg * np.hanning(len(seg))
            continue
        med = float(np.median(seg_f0))
        semis = round(12 * np.log2(med / 440.0))
        target = 440.0 * (2 ** (semis / 12.0))
        shift = 12 * np.log2(target / med) * strength
        if abs(shift) > 0.01:
            seg = librosa.effects.pitch_shift(y=seg, sr=sr, n_steps=shift)
        out[start:start + win] += seg[:win] * np.hanning(win)
    return (out / (np.max(np.abs(out)) + 1e-12) * (np.max(np.abs(y)) + 1e-12)).astype(np.float32)
