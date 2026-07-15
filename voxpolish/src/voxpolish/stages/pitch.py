"""Pitch analysis: track the vocal's pitch, detect the key, propose gentle
corrections toward the scale.

Analysis only — no audio is modified. The output is an editable report
(the tuner's half of the no-black-box contract): every note, its deviation
in cents, and the proposed correction. The rendering half (applying the
correction with a vocoder/PSOLA) comes later, behind the same data.

Tracker: YIN (de Cheveigné & Kawahara 2002) implemented with FFT
correlation — no extra dependencies.
"""

from __future__ import annotations

import numpy as np
from scipy import signal

FRAME = 2048  # ~46 ms at 44.1k: >2 periods of the 80 Hz floor
HOP = 512
FMIN, FMAX = 75.0, 900.0
YIN_THRESHOLD = 0.15
MIN_LEVEL_DB = -50.0

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Notes whose core deviation is inside this band are left completely alone.
DEADBAND_CENTS = 10.0
MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11}
MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10}
# Krumhansl-Schmuckler key profiles.
_KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def track(mono: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """YIN pitch track. Returns (times, f0_hz, confidence); f0=0 where unvoiced."""
    tau_min = max(2, int(sr / FMAX))
    tau_max = int(sr / FMIN)
    n_frames = max(0, (len(mono) - FRAME - tau_max) // HOP + 1)
    times = np.empty(n_frames)
    f0 = np.zeros(n_frames)
    conf = np.zeros(n_frames)

    for i in range(n_frames):
        start = i * HOP
        times[i] = (start + FRAME / 2) / sr
        long = np.asarray(mono[start : start + FRAME + tau_max], dtype=np.float64)
        seg = long[:FRAME]
        rms_db = 10 * np.log10(np.mean(seg**2) + 1e-12)
        if rms_db < MIN_LEVEL_DB:
            continue

        # d(tau) = E(0) + E(tau) - 2*C(tau), all via FFT / cumsum.
        corr = signal.correlate(long, seg, mode="valid", method="fft")
        cs = np.concatenate([[0.0], np.cumsum(long**2)])
        energy = cs[FRAME:] - cs[: tau_max + 1]
        d = energy[0] + energy - 2.0 * corr
        d = np.maximum(d, 0.0)

        # Cumulative-mean-normalized difference.
        cum = np.cumsum(d[1:])
        cmndf = np.ones_like(d)
        cmndf[1:] = d[1:] * np.arange(1, len(d)) / np.maximum(cum, 1e-12)

        search = cmndf[tau_min:tau_max]
        below = np.where(search < YIN_THRESHOLD)[0]
        if len(below):
            # First local minimum below threshold.
            j = below[0]
            while j + 1 < len(search) and search[j + 1] < search[j]:
                j += 1
        else:
            j = int(np.argmin(search))
            if search[j] > 0.5:
                continue  # unvoiced
        tau = float(j + tau_min)
        # Parabolic interpolation around the minimum. The vertex of a true
        # local minimum lies within half a bin; anything further means the
        # minimum sits on the search boundary (content near/below the f0
        # floor), where the parabola extrapolates wildly — clamp it.
        k = int(tau)
        if 1 <= k < len(cmndf) - 1:
            a, b, c = cmndf[k - 1], cmndf[k], cmndf[k + 1]
            denom = a - 2 * b + c
            if abs(denom) > 1e-12:
                tau = k + float(np.clip(0.5 * (a - c) / denom, -0.5, 0.5))
        f0[i] = sr / tau
        conf[i] = float(1.0 - cmndf[min(len(cmndf) - 1, max(0, int(round(tau))))])
    return times, f0, conf


def estimate_key(f0: np.ndarray) -> tuple[int, str, float]:
    """Best-fit (tonic pitch class, 'major'|'minor', correlation) from a pitch track."""
    voiced = f0 > 0
    if not voiced.any():
        return 0, "major", 0.0
    midi = 69 + 12 * np.log2(f0[voiced] / 440.0)
    hist = np.bincount(np.round(midi).astype(int) % 12, minlength=12).astype(float)
    if hist.sum() == 0:
        return 0, "major", 0.0
    best = (0, "major", -2.0)
    for tonic in range(12):
        for mode, profile in (("major", _KS_MAJOR), ("minor", _KS_MINOR)):
            r = np.corrcoef(np.roll(profile, tonic), hist)[0, 1]
            if np.isfinite(r) and r > best[2]:
                best = (tonic, mode, float(r))
    return best


def analyze(
    mono: np.ndarray,
    sr: int,
    strength: float = 0.4,
    retune_ms: float = 120.0,
    max_cents: float = 100.0,
    key: tuple[int, str] | None = None,
) -> dict:
    """Full pitch report: key, notes, deviations, proposed correction curve."""
    times, f0, conf = track(mono, sr)
    voiced = f0 > 0

    if key is None:
        tonic, mode, key_conf = estimate_key(f0)
    else:
        tonic, mode = key
        _, _, key_conf = estimate_key(f0)
    scale_pcs = MAJOR_SCALE if mode == "major" else MINOR_SCALE
    scale = sorted((tonic + pc) % 12 for pc in scale_pcs)

    midi = np.where(voiced, 69 + 12 * np.log2(np.maximum(f0, 1.0) / 440.0), 0.0)

    def nearest_scale_note(m: float) -> int:
        cands = []
        base = int(np.floor(m)) - 2
        for k in range(base, base + 6):
            if k % 12 in scale:
                cands.append(k)
        return min(cands, key=lambda k: abs(m - k))

    target = np.zeros_like(midi)
    for i in np.where(voiced)[0]:
        target[i] = nearest_scale_note(midi[i])
    dev_cents = np.where(voiced, (midi - target) * 100.0, 0.0)

    # NOTE-CENTRIC correction (field verdict: frame-chasing sounded "far too
    # strong and weird"). Each note gets ONE near-constant shift derived from
    # its core median deviation — vibrato, scoops, and micro-inflections ride
    # on top completely untouched. Notes inside the deadband, too unstable,
    # or low-confidence get exactly zero correction.
    hop_s = HOP / sr
    correction = np.zeros_like(dev_cents)
    notes = []
    i = 0
    while i < len(times):
        if not voiced[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(times) and voiced[j + 1] and target[j + 1] == target[i]:
            j += 1
        dur = times[j] - times[i] + hop_s
        if dur >= 0.1:
            # Core = the held part of the note, excluding attack/release
            # frames where scoops and consonant transitions live.
            k = min(int(0.05 / hop_s), (j - i) // 3)
            core = slice(i + k, j + 1 - k) if (j + 1 - k) > (i + k) else slice(i, j + 1)
            med_dev = float(np.median(dev_cents[core]))
            spread = float(np.std(dev_cents[core]))
            conf_mean = float(np.mean(conf[i : j + 1]))

            corr = 0.0
            if (
                abs(med_dev) >= DEADBAND_CENTS  # nearly in tune: hands off
                and spread <= 60.0  # a glide/run, not a held note: hands off
                and conf_mean >= 0.5  # shaky tracking: hands off
            ):
                corr = float(np.clip(-med_dev * strength, -max_cents, max_cents))

            if corr != 0.0:
                # Raised-cosine glide in over retune_ms (natural attack),
                # short release ramp at the note end.
                t_rel = times[i : j + 1] - times[i]
                w_in = 0.5 - 0.5 * np.cos(
                    np.pi * np.minimum(1.0, t_rel / max(retune_ms / 1000.0, 1e-3))
                )
                t_out = times[j] - times[i : j + 1]
                w_out = 0.5 - 0.5 * np.cos(np.pi * np.minimum(1.0, t_out / 0.04))
                correction[i : j + 1] = corr * w_in * w_out

            t = int(target[i])
            notes.append({
                "start": round(float(times[i]), 3),
                "end": round(float(times[j]), 3),
                "midi": t,
                "note": f"{NOTE_NAMES[t % 12]}{t // 12 - 1}",
                "mean_dev_cents": round(med_dev, 1),
                "proposed_cents": round(corr, 1),
                "confidence": round(conf_mean, 3),
            })
        i = j + 1

    voiced_devs = np.abs(dev_cents[voiced])

    # Pitch track for the editor lane: [time, sung_midi, correction_cents] at
    # voiced frames, downsampled so the JSON stays small on long takes. The
    # lane draws the sung line and (sung + correction * tune_amount) as the
    # corrected line, so you can see exactly what tuning changed.
    vidx = np.where(voiced)[0]
    stride = max(1, len(vidx) // 1800)
    lane_track = [
        [round(float(times[i]), 4), round(float(midi[i]), 3), round(float(correction[i]), 1)]
        for i in vidx[::stride]
    ]

    return {
        "applied": False,
        "key": f"{NOTE_NAMES[tonic]} {mode}",
        "key_confidence": round(key_conf, 3),
        "settings": {"strength": strength, "retune_ms": retune_ms, "max_cents": max_cents},
        "voiced_seconds": round(float(voiced.sum() * hop_s), 2),
        "mean_abs_dev_cents": round(float(np.mean(voiced_devs)), 1) if voiced.any() else 0.0,
        "notes": notes,
        "track": lane_track,
        "curve": [
            [round(float(t), 4), round(float(c), 1)]
            for t, c in zip(times[voiced], correction[voiced])
        ],
    }


# --------------------------------------------------------------- rendering


def vocoder_available() -> bool:
    try:
        import pyworld  # noqa: F401

        return True
    except ImportError:
        return False


def _dense_cents(world_times: np.ndarray, curve: list) -> np.ndarray:
    """Map the report's (voiced-only) correction curve onto vocoder frames.

    Frames farther than 50 ms from any curve point get zero correction, so
    gaps between phrases are never bridged by interpolation.
    """
    if not curve:
        return np.zeros_like(world_times)
    pts = np.asarray(curve, dtype=np.float64)
    cents = np.interp(world_times, pts[:, 0], pts[:, 1], left=0.0, right=0.0)
    idx = np.searchsorted(pts[:, 0], world_times).clip(1, len(pts) - 1)
    nearest = np.minimum(
        np.abs(world_times - pts[idx - 1, 0]), np.abs(world_times - pts[idx, 0])
    )
    cents[nearest > 0.05] = 0.0
    return cents


def _corrected_spans(curve: list, margin_s: float = 0.06) -> list:
    """(start, end) spans where the curve actually corrects (>0.5 cents)."""
    spans: list[list[float]] = []
    for t, c in curve:
        if abs(c) <= 0.5:
            continue
        if spans and t - spans[-1][1] <= 0.1:
            spans[-1][1] = t
        else:
            spans.append([t, t])
    merged: list[list[float]] = []
    for s, e in spans:
        s, e = s - margin_s, e + margin_s
        if merged and s <= merged[-1][1]:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return merged


def apply_correction(audio: np.ndarray, sr: int, curve: list) -> tuple[np.ndarray, dict]:
    """Apply a cents-correction curve to (channels, samples) audio.

    Uses the WORLD vocoder (pip install 'voxpolish[pitch]'), but ONLY inside
    the corrected note spans: everywhere else the output is the original
    audio, bit-identical, crossfaded at the span edges. Uncorrected takes
    pass through untouched entirely.
    """
    audio = np.atleast_2d(audio)
    spans = _corrected_spans(curve)
    if not spans:
        return audio.copy(), {"applied": False, "reason": "no correction above 0.5 cents"}

    if not vocoder_available():
        raise RuntimeError(
            "Pitch rendering needs the WORLD vocoder: pip install 'voxpolish[pitch]'"
        )
    import pyworld as pw

    n = audio.shape[1]
    xfade = int(0.02 * sr)
    out = audio.astype(np.float64).copy()
    applied_cents = 0.0
    approved: list[bool] | None = None
    for ch in range(audio.shape[0]):
        x = np.ascontiguousarray(audio[ch], dtype=np.float64)
        f0, t = pw.dio(x, sr, f0_floor=FMIN, f0_ceil=FMAX)
        f0 = pw.stonemask(x, f0, t, sr)

        # Stability guard (field garble fix): the vocoder trusts ITS OWN
        # pitch track inside a span. On noisy/separated audio that track
        # octave-jumps and voiced-flaps, and resynthesizing those frames is
        # the garble. An unstable span is skipped — original audio wins.
        # Decided once (first channel) so stereo stays consistent.
        if approved is None:
            approved = []
            for s, e in spans:
                f0s = f0[(t >= s) & (t <= e)]
                v = f0s > 0
                if len(f0s) < 4 or v.mean() < 0.6:
                    approved.append(False)
                    continue
                jumps = np.abs(np.diff(np.log2(f0s[v]))) > 0.4  # ~5 semitones
                approved.append(bool(jumps.mean() <= 0.1))
            if not any(approved):
                return audio.copy(), {
                    "applied": False,
                    "reason": "all corrected spans had unstable pitch tracking",
                    "skipped_unstable_spans": len(spans),
                }

        sp = pw.cheaptrick(x, f0, t, sr)
        ap = pw.d4c(x, f0, t, sr)
        cents = _dense_cents(t, curve)
        cents[f0 <= 0] = 0.0
        applied_cents = max(applied_cents, float(np.max(np.abs(cents))))
        y = pw.synthesize(f0 * 2 ** (cents / 1200.0), sp, ap, sr)
        y = y[:n] if len(y) >= n else np.pad(y, (0, n - len(y)))

        for k, (s, e) in enumerate(spans):
            if not approved[k]:
                continue
            i0, i1 = max(0, int(s * sr)), min(n, int(e * sr))
            if i1 - i0 < 4 * xfade:
                continue
            seg = y[i0:i1].copy()
            # Loudness must not shift: pin the span's RMS to the original.
            rms_in = np.sqrt(np.mean(x[i0:i1] ** 2))
            rms_out = np.sqrt(np.mean(seg**2))
            if rms_out > 1e-9 and rms_in > 1e-9:
                seg *= rms_in / rms_out
            w = np.ones(i1 - i0)
            ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(xfade) / xfade)
            w[:xfade] = ramp
            w[-xfade:] = ramp[::-1]
            out[ch, i0:i1] = x[i0:i1] * (1 - w) + seg * w

    return (
        np.clip(out, -1.0, 1.0).astype(np.float32),
        {
            "applied": True,
            "max_applied_cents": round(applied_cents, 1),
            "corrected_spans": int(sum(approved)),
            "skipped_unstable_spans": int(len(approved) - sum(approved)),
        },
    )
