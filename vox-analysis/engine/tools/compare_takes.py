#!/usr/bin/env python3
"""
Melody-match: compare a singer's take against the original, phrase by phrase.

Usage:
    python tools/compare_takes.py <take_analysis.json> <original_analysis.json> \
        [--out reports/comparison.md]

Both JSONs must come from the v2+ engine (they carry `pitch.f0_contour`,
the compact 10 Hz pitch contour persisted at analysis time) — no audio
re-processing is needed.

Method:
  1. Load both cents contours; estimate and remove the global transposition
     (singing a key lower is a choice, not an error — the shift is reported,
     not penalised).
  2. Align the two performances with dynamic time warping (banded), so
     verse-to-verse tempo differences don't break the comparison.
  3. Report, per 20-second stretch of the original: median pitch difference
     (sharp/flat vs the original melody), timing lead/lag from the warping
     path, and the worst mismatch moments with timestamps.

Everything here is a measurement of similarity to the original performance.
Departing from the original can be deliberate artistry — the timestamps
exist so a human can judge which is which.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

DTW_BAND_S = 20.0          # max local time misalignment considered
UNVOICED_COST = 55.0       # cents-equivalent cost when one side is silent
TROUBLE_PITCH_CENTS = 35.0


def load_contour(path):
    with open(path) as f:
        data = json.load(f)
    contour = data.get("pitch", {}).get("f0_contour")
    if not contour or not contour.get("values"):
        raise SystemExit(
            f"{path} has no pitch.f0_contour — re-analyse it with the current engine."
        )
    values = np.array([np.nan if v is None else float(v) for v in contour["values"]])
    return values, float(contour["rate_hz"]), data


def transposition_offset(take, ref):
    """Median cents difference over voiced frames, snapped to semitones."""
    n = min(len(take), len(ref))
    both = np.isfinite(take[:n]) & np.isfinite(ref[:n])
    if both.sum() < 20:
        return 0.0, 0
    rough = float(np.median(take[:n][both] - ref[:n][both]))
    semitones = int(round(rough / 100.0))
    return semitones * 100.0, semitones


def dtw_align(take, ref, rate):
    """
    Banded DTW over the cents contours. Returns the warping path as index
    pairs (i_take, j_ref). Frame-wise cost = |pitch difference| on voiced
    pairs, UNVOICED_COST when exactly one side is voiced, small cost when
    both silent.
    """
    n, m = len(take), len(ref)
    band = int(DTW_BAND_S * rate)
    INF = 1e12
    cost = np.full((n + 1, m + 1), INF)
    cost[0, 0] = 0.0
    for i in range(1, n + 1):
        j_lo = max(1, int(i * m / n) - band)
        j_hi = min(m, int(i * m / n) + band)
        ti = take[i - 1]
        for j in range(j_lo, j_hi + 1):
            rj = ref[j - 1]
            if np.isfinite(ti) and np.isfinite(rj):
                d = min(abs(ti - rj), 2 * UNVOICED_COST)
            elif np.isfinite(ti) != np.isfinite(rj):
                d = UNVOICED_COST
            else:
                d = 2.0
            cost[i, j] = d + min(cost[i - 1, j - 1], cost[i - 1, j], cost[i, j - 1])

    # Backtrack
    path = []
    i, j = n, m
    if not np.isfinite(cost[n, m]):
        raise SystemExit("DTW failed — takes may be wildly different lengths.")
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        moves = ((cost[i - 1, j - 1], i - 1, j - 1),
                 (cost[i - 1, j], i - 1, j),
                 (cost[i, j - 1], i, j - 1))
        _, i, j = min(moves, key=lambda x: x[0])
    path.reverse()
    return path


def mmss(seconds):
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


def main():
    parser = argparse.ArgumentParser(description="Melody-match a take against the original.")
    parser.add_argument("take_json")
    parser.add_argument("reference_json")
    parser.add_argument("--out", help="Write a Markdown report here as well.")
    args = parser.parse_args()

    take, rate_t, take_data = load_contour(args.take_json)
    ref, rate_r, ref_data = load_contour(args.reference_json)
    if abs(rate_t - rate_r) > 0.01:
        raise SystemExit("Contour rates differ — re-analyse both with the same engine version.")
    rate = rate_t

    offset_cents, semitones = transposition_offset(take, ref)
    take_shifted = take - offset_cents

    path = dtw_align(take_shifted, ref, rate)

    # Per-aligned-pair stats
    pitch_diffs, lags, ref_times = [], [], []
    for i, j in path:
        ref_times.append(j / rate)
        lags.append((i - j) / rate)
        if np.isfinite(take_shifted[i]) and np.isfinite(ref[j]):
            pitch_diffs.append(take_shifted[i] - ref[j])
        else:
            pitch_diffs.append(np.nan)
    pitch_diffs = np.array(pitch_diffs)
    lags = np.array(lags)
    ref_times = np.array(ref_times)
    lags = lags - np.median(lags)          # remove global start offset

    voiced = np.isfinite(pitch_diffs)
    overall = {
        "transposition_semitones": semitones,
        "median_abs_pitch_diff_cents": round(float(np.median(np.abs(pitch_diffs[voiced]))), 1) if voiced.any() else None,
        "pct_frames_within_50_cents": round(float(np.mean(np.abs(pitch_diffs[voiced]) <= 50) * 100), 1) if voiced.any() else None,
        "median_timing_lag_s": 0.0,
        "timing_spread_s": round(float(np.percentile(lags, 90) - np.percentile(lags, 10)), 2),
    }

    # 20-second section table (in original-song time)
    sections = []
    for sec_start in np.arange(0, ref_times.max(), 20.0):
        mask = (ref_times >= sec_start) & (ref_times < sec_start + 20.0)
        v = mask & voiced
        if v.sum() < 10:
            continue
        med_diff = float(np.median(pitch_diffs[v]))
        med_lag = float(np.median(lags[mask]))
        sections.append({
            "time_range": f"{mmss(sec_start)}-{mmss(sec_start + 20)}",
            "median_pitch_diff_cents": round(med_diff, 1),
            "read": ("sharp of the original" if med_diff > 20 else
                     "flat of the original" if med_diff < -20 else "on the melody"),
            "median_lag_s": round(med_lag, 2),
            "feel": ("behind the original" if med_lag > 0.25 else
                     "ahead of the original" if med_lag < -0.25 else "with the original"),
        })

    worst = sorted(
        (s for s in sections if abs(s["median_pitch_diff_cents"]) > TROUBLE_PITCH_CENTS),
        key=lambda s: -abs(s["median_pitch_diff_cents"]))[:5]

    result = {
        "method": "banded_dtw_on_persisted_f0_contours",
        "take": os.path.basename(args.take_json),
        "reference": os.path.basename(args.reference_json),
        "take_artist": take_data.get("artist_name"),
        "reference_artist": ref_data.get("artist_name"),
        "overall": overall,
        "sections_20s": sections,
        "worst_sections": worst,
        "note": (
            "Similarity to the original performance, transposition removed. "
            "Departure from the original can be deliberate interpretation — "
            "judge by ear at the timestamps."
        ),
    }
    print(json.dumps(result, indent=2))

    if args.out:
        lines = [
            "# Melody Match — take vs original",
            "",
            f"| Field | Value |",
            f"|---|---|",
            f"| Take | `{result['take']}` ({result['take_artist']}) |",
            f"| Original | `{result['reference']}` ({result['reference_artist']}) |",
            f"| Transposition | {semitones:+d} semitones (removed before comparison) |",
            f"| Median pitch difference | {overall['median_abs_pitch_diff_cents']} cents |",
            f"| Frames within 50 cents of the melody | {overall['pct_frames_within_50_cents']}% |",
            f"| Timing spread | {overall['timing_spread_s']} s |",
            "",
            "## Section by section",
            "",
            "| Section | Pitch vs original | Read | Timing | Feel |",
            "|---|---|---|---|---|",
        ]
        for s in sections:
            lines.append(
                f"| {s['time_range']} | {s['median_pitch_diff_cents']:+} cents | {s['read']} | {s['median_lag_s']:+}s | {s['feel']} |")
        lines += ["", f"*{result['note']}*", ""]
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            f.write("\n".join(lines))
        print(f"\nMarkdown report: {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
