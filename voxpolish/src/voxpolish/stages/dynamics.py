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

# Absolute gate: frames below this are bleed/silence, never target material.
ABS_GATE_DB = -70.0
# A vocal leveling target outside this window is nonsense (Shimmer measured
# -44 dBFS from separation bleed); fall back to a robust upper estimate.
TARGET_SANITY_DB = (-35.0, -10.0)
# Only frames within this reach of the target are leveled. Content further
# below the performance level is separation bleed or wash, not vocal to
# amplify — boosting it produced Shimmer's over-amplified quiet passages.
BOOST_REACH_DB = 15.0


def _gated_loudness_db(levels: np.ndarray) -> float | None:
    """BS.1770-style gated loudness of a framewise level curve.

    The 0.4 s / 0.1 s-hop frames above match the meter's momentary blocks, so
    an absolute -70 gate plus a -10 relative gate approximates integrated
    loudness closely enough to neutralize leveling against it.
    """
    kept = levels[levels > ABS_GATE_DB]
    if len(kept) == 0:
        return None
    ungated = 10 * np.log10(np.mean(10 ** (kept / 10)))
    gated = kept[kept > ungated - 10]
    if len(gated) == 0:
        return float(ungated)
    return float(10 * np.log10(np.mean(10 ** (gated / 10))))


def _robust_target(levels: np.ndarray, voiced: np.ndarray) -> tuple[float, str]:
    """EBU R128-style two-pass gated target selection.

    On sparse stems the plain median of "voiced" frames sits on separation
    bleed, not singing. Gating relative to the energy mean keeps only frames
    near the actual performance level.
    """
    cand = levels[voiced] if voiced.any() else levels
    cand = cand[cand > ABS_GATE_DB]
    if len(cand) == 0:
        return float(np.median(levels)), "ungated-fallback"
    energy_mean = 10 * np.log10(np.mean(10 ** (cand / 10)))
    gated = cand[cand > energy_mean - 10]
    target = float(np.median(gated)) if len(gated) else float(energy_mean)
    method = "gated-median"
    if not (TARGET_SANITY_DB[0] <= target <= TARGET_SANITY_DB[1]):
        target = float(np.clip(np.percentile(cand, 90), *TARGET_SANITY_DB))
        method = "sanity-fallback"
    return target, method


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
    max_boost_db: float = 6.0,
    max_slope_db_s: float = 6.0,
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
        # Constant-level input (a steady tone/stem) leaves nothing above the
        # median; treat everything at or above it as voiced so the stage has a
        # non-empty population to work with.
        voiced = levels >= np.median(levels)
    if not voiced.any():
        voiced = np.ones_like(levels, dtype=bool)

    # Target: robust gated estimate of the performance level unless overridden.
    if target_db is not None:
        target, method = float(target_db), "custom"
    else:
        target, method = _robust_target(levels, voiced)

    leveled = voiced & (levels > target - BOOST_REACH_DB)
    gain = np.where(leveled, target - levels, 0.0)
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

    # Loudness-neutral invariant: leveling compresses AROUND the performance,
    # it never moves its measured loudness. The correction is computed with
    # BS.1770-style gating (not the median, not plain energy): on high-LRA
    # vocals the cuts land on the loud frames that carry the loudness, and
    # boosted quiet passages can cross the meter's relative gate — both move
    # integrated LUFS while leaving the median or total energy unchanged.
    #
    # The shift is weighted by a smoothed voiced mask so bleed and silence
    # are never boosted as if they were vocal, and the boost ceiling is
    # re-applied INSIDE the loop: neutralization can never push local gain
    # past max_boost_db (the Shimmer +11 dB failure).
    weight = np.clip(
        dsp.smooth_exponential(leveled.astype(float), HOP_S, 0.3), 0.0, 1.0
    )
    loudness_shift = 0.0
    before = _gated_loudness_db(levels)
    for _ in range(3):
        after = _gated_loudness_db(levels + gain)
        if before is None or after is None:
            break
        step = after - before
        gain -= step * weight
        loudness_shift += step
        gain = np.clip(gain, -max_gain_db, max_boost_db)

    # Slope limit: automation may not change faster than max_slope_db_s, so
    # neutralization/leveling can never create an audible level step.
    max_step = max_slope_db_s * HOP_S
    for i in range(1, len(gain)):
        lo, hi = gain[i - 1] - max_step, gain[i - 1] + max_step
        gain[i] = min(max(gain[i], lo), hi)
    gain = np.clip(gain, -max_gain_db, max_boost_db)

    after = _gated_loudness_db(levels + gain)
    residual = None if (before is None or after is None) else after - before
    diffs = np.abs(np.diff(gain)) if len(gain) > 1 else np.array([0.0])

    curve = [[round(float(t), 4), round(float(g), 3)] for t, g in zip(times, gain)]
    info = {
        "target_db": round(target, 2),
        "target_method": method,
        "loudness_shift_correction_db": round(loudness_shift, 3),
        "neutrality_residual_lu": None if residual is None else round(residual, 2),
        "gain_range_db": [round(float(gain.min()), 2), round(float(gain.max()), 2)],
        "max_slope_db_per_s": round(float(diffs.max() / HOP_S), 2),
        "voiced_level_range_db": [
            round(float(np.min(levels[voiced])), 2),
            round(float(np.max(levels[voiced])), 2),
        ],
    }
    return curve, info
