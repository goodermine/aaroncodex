"""Final mastering: bounded loudness normalization + true-peak ceiling.

Order of authority: quality > ceiling > loudness target. Gain toward the LUFS
target is clamped; peak control uses a lookahead limiter only up to its
gain-reduction bound; anything beyond that is taken back out of makeup gain
(missing the loudness target) rather than crushed. Every clamp and miss is
reported.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import maximum_filter1d

from .. import measure


def _limit(audio: np.ndarray, sr: int, ceiling_lin: float) -> tuple[np.ndarray, float]:
    """Lookahead peak limiter. Returns (audio, max gain reduction in dB).

    Block-based envelope (1 ms hops, 5 ms lookahead, 60 ms release), instant
    attack via sliding max, applied equally to all channels.
    """
    hop = max(1, int(0.001 * sr))
    absx = np.max(np.abs(audio), axis=0)
    n_blocks = int(np.ceil(len(absx) / hop))
    pad = n_blocks * hop - len(absx)
    block_peak = np.pad(absx, (0, pad)).reshape(n_blocks, hop).max(axis=1)

    look_blocks = 5
    peaks = maximum_filter1d(block_peak, size=2 * look_blocks + 1, mode="nearest")
    need = np.minimum(1.0, ceiling_lin / np.maximum(peaks, 1e-12))

    release_blocks = 60
    alpha = 1.0 - np.exp(-1.0 / release_blocks)
    env = np.empty_like(need)
    acc = 1.0
    for i, v in enumerate(need):
        acc = v if v < acc else acc + alpha * (v - acc)
        env[i] = acc

    block_t = (np.arange(n_blocks) + 0.5) * hop
    gain = np.interp(np.arange(len(absx)), block_t, env)
    max_gr_db = float(-20 * np.log10(max(np.min(env), 1e-12)))
    return audio * gain[None, :], max_gr_db


def master(
    audio: np.ndarray,
    sr: int,
    target_lufs: float = -15.0,
    ceiling_dbtp: float = -3.0,
    max_gain_db: float = 8.0,
    max_limiter_gr_db: float = 3.0,
) -> tuple[np.ndarray, dict]:
    """Master (channels, samples) audio toward target_lufs under ceiling_dbtp."""
    audio = np.atleast_2d(audio).astype(np.float64)
    reasons: list[str] = []

    pre_lufs = measure.integrated_lufs(audio, sr)
    if pre_lufs is None:
        reasons.append("input too short/quiet to measure; mastering skipped")
        gain = 0.0
    else:
        wanted = target_lufs - pre_lufs
        gain = float(np.clip(wanted, -max_gain_db, max_gain_db))
        if gain != wanted:
            reasons.append(f"mastering gain clamped ({wanted:+.1f} -> {gain:+.1f} dB)")
    x = audio * 10 ** (gain / 20)

    # True-peak control: limiter up to its bound, global trim beyond it.
    ceiling_lin = 10 ** (ceiling_dbtp / 20)
    tp = measure.true_peak_db(x, sr)
    trim_db = 0.0
    limiter_gr_db = 0.0
    if tp > ceiling_dbtp:
        over = tp - ceiling_dbtp
        if over > max_limiter_gr_db:
            trim_db = over - max_limiter_gr_db
            x *= 10 ** (-trim_db / 20)
            reasons.append(
                f"peak overshoot {over:.1f} dB exceeds limiter bound; "
                f"trimmed {trim_db:.1f} dB (loudness target sacrificed)"
            )
        x, limiter_gr_db = _limit(x, sr, ceiling_lin)
        # Inter-sample peaks can survive the sample-domain limiter; a final
        # deterministic trim guarantees the ceiling.
        tp2 = measure.true_peak_db(x, sr)
        if tp2 > ceiling_dbtp:
            x *= 10 ** ((ceiling_dbtp - tp2) / 20)

    final_lufs = measure.integrated_lufs(x, sr)
    reached = (
        pre_lufs is not None
        and final_lufs is not None
        and abs(final_lufs - target_lufs) <= 1.0
    )
    if not reached and pre_lufs is not None and not reasons:
        reasons.append("target missed after bounded processing")

    report = {
        "target_lufs": target_lufs,
        "ceiling_dbtp": ceiling_dbtp,
        "pre_master_lufs": None if pre_lufs is None else round(pre_lufs, 2),
        "gain_applied_db": round(gain - trim_db, 2),
        "limiter_max_gr_db": round(limiter_gr_db, 2),
        "final_lufs": None if final_lufs is None else round(final_lufs, 2),
        "final_lra_lu": _round(measure.loudness_range_lu(x, sr)),
        "final_true_peak_dbtp": round(measure.true_peak_db(x, sr), 2),
        "target_reached": bool(reached),
        "reasons": reasons,
    }
    return np.clip(x, -1.0, 1.0).astype(np.float32), report


def _round(v: float | None) -> float | None:
    return None if v is None else round(v, 2)
