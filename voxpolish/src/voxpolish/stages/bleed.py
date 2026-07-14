"""Bleed suppression: remove instrumental leakage from the separated vocal.

The advantage nobody else has at this point in the chain: we hold the
instrumental stem. Whatever energy in the vocal stem tracks the instrumental
is bleed by definition, so the instrumental becomes a per-band noise
reference for a Wiener-style mask.

Method: estimate the leakage ratio per frequency band from the vocal stem's
quiet frames (where anything present is bleed), predict the bleed spectrum as
ratio x instrumental, and attenuate bins where predicted bleed dominates the
vocal. Bounded (attenuation floor), smoothed (no musical noise), blendable
(strength), and reported like every other module.
"""

from __future__ import annotations

import numpy as np
from scipy import signal
from scipy.ndimage import uniform_filter

NPER = 2048
HOP = 512
EPS = 1e-10


def suppress(
    vocal: np.ndarray,
    instrumental: np.ndarray,
    sr: int,
    strength: float = 0.7,
    max_att_db: float = 15.0,
    oversubtraction: float = 2.0,
) -> tuple[np.ndarray, dict]:
    """Suppress instrumental bleed in (channels, samples) vocal. Returns
    (vocal, report)."""
    vocal = np.atleast_2d(vocal)
    instrumental = np.atleast_2d(instrumental)
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength == 0.0:
        return vocal.copy(), {"applied": False, "reason": "strength 0"}

    n = min(vocal.shape[1], instrumental.shape[1])
    inst_mono = instrumental[:, :n].mean(axis=0)
    _, _, I = signal.stft(inst_mono, sr, nperseg=NPER, noverlap=NPER - HOP)
    aI = np.abs(I)

    out = np.empty_like(vocal)
    att_quiet_db = []
    alphas = []
    for ch in range(vocal.shape[0]):
        freqs, times, V = signal.stft(
            vocal[ch, :n], sr, nperseg=NPER, noverlap=NPER - HOP
        )
        aV = np.abs(V)

        # Quiet vocal frames: the bottom stretch of frame energy — whatever
        # lives there is not the singer, so it calibrates the leakage ratio.
        frame_db = 10 * np.log10(np.sum(aV**2, axis=0) + EPS)
        quiet = frame_db <= np.percentile(frame_db, 25)
        if quiet.sum() >= 5:
            alpha = np.median(
                aV[:, quiet] / (aI[:, quiet] + EPS), axis=1, keepdims=True
            )
        else:  # wall-to-wall vocals: fall back to a conservative low quantile
            alpha = np.quantile(aV / (aI + EPS), 0.10, axis=1, keepdims=True)
        alpha = np.clip(alpha, 0.0, 2.0)
        alphas.append(float(np.median(alpha)))

        # Oversubtraction: a plain Wiener mask only reaches -6 dB where the
        # bleed estimate equals the observed energy; scaling the estimate
        # pushes confirmed bleed toward the floor while bins the singer
        # dominates still pass at ~unity.
        bleed_est = oversubtraction * alpha * aI
        gain = aV**2 / (aV**2 + bleed_est**2 + EPS)
        floor = 10 ** (-max_att_db / 20)
        gain = floor + (1.0 - floor) * gain
        # Smooth across time and frequency so the mask never flutters.
        gain = uniform_filter(gain, size=(3, 3))
        gain = (1.0 - strength) + strength * gain  # dry/wet on the mask

        att_quiet_db.append(
            float(-20 * np.log10(np.mean(gain[:, quiet]) + EPS)) if quiet.any() else 0.0
        )

        _, y = signal.istft(V * gain, sr, nperseg=NPER, noverlap=NPER - HOP)
        y = y[: vocal.shape[1]]
        if len(y) < vocal.shape[1]:
            y = np.pad(y, (0, vocal.shape[1] - len(y)))
        out[ch] = y.astype(vocal.dtype)

    return out, {
        "applied": True,
        "strength": strength,
        "max_att_db": max_att_db,
        "leakage_ratio_median": round(float(np.median(alphas)), 4),
        "quiet_attenuation_db": round(float(np.mean(att_quiet_db)), 2),
    }
