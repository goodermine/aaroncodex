"""Dynamics analysis: ride the vocal toward a consistent loudness.

Produces an editable gain automation curve, never touches the audio. Parameters
mirror the mental model pros expect: speed (reaction time), smoothing (dry/wet),
noise floor (ignore quiet junk), target (match or custom), catch peaks.
"""

from __future__ import annotations

import numpy as np

from .. import dsp

WINDOW_S = 0.4
HOP_S = 0.1


def analyze(
    mono: np.ndarray,
    sr: int,
    speech_times: np.ndarray | None = None,
    speech_mask: np.ndarray | None = None,
    target_db: float | None = None,
    speed_ms: float = 600.0,
    smoothing: float = 0.7,
    noise_floor_db: float | None = None,
    max_gain_db: float = 12.0,
    catch_peaks: float = 0.5,
) -> tuple[list, dict]:
    """Return (gain_curve [[t, dB]...], analysis info)."""
    times, levels = dsp.frame_rms_db(mono, sr, WINDOW_S, HOP_S)

    # Which frames count as voice: caller-provided VAD if available, else energy.
    if speech_mask is not None and speech_times is not None and len(speech_times) > 1:
        voiced = np.interp(times, speech_times, speech_mask.astype(float)) > 0.5
    else:
        voiced = levels > np.percentile(levels, 20) + 6
    if noise_floor_db is not None:
        voiced &= levels > noise_floor_db
    if not voiced.any():
        voiced = levels > np.median(levels)

    # Target: match the recording's own typical voiced loudness unless overridden.
    target = float(target_db) if target_db is not None else float(np.median(levels[voiced]))

    gain = np.where(voiced, target - levels, 0.0)
    gain = np.clip(gain, -max_gain_db, max_gain_db)
    gain = dsp.smooth_exponential(gain, HOP_S, speed_ms / 1000.0)
    gain *= float(np.clip(smoothing, 0.0, 1.0))

    # Catch peaks: fast, separate pass that only pulls down transient overs.
    if catch_peaks > 0:
        ptimes, plevels = dsp.frame_rms_db(mono, sr, 0.05, 0.025)
        margin = 6.0
        over = np.maximum(0.0, plevels - (target + margin))
        reduction = -np.minimum(over * catch_peaks, 6.0)
        reduction = dsp.smooth_exponential(reduction, 0.025, 0.05)
        gain = gain + np.interp(times, ptimes, reduction)

    curve = [[round(float(t), 4), round(float(g), 3)] for t, g in zip(times, gain)]
    info = {
        "target_db": round(target, 2),
        "voiced_level_range_db": [
            round(float(np.min(levels[voiced])), 2),
            round(float(np.max(levels[voiced])), 2),
        ],
    }
    return curve, info
