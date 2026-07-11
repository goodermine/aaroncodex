#!/usr/bin/env python3
"""
Builds a professional-reference calibration file for the VOXAI technical
score from backend analysis JSONs of professional vocal takes.

Workflow:
  1. Analyse 15-20 professional reference tracks (songs the human ear
     already certifies as 9-10) with the normal pipeline:
         python analyse_song.py pro_track.mp3 --name "Reference" --separate-stems
  2. Point this tool at the resulting *_analysis.json files (or the
     output/ folder that contains them):
         python tools/build_calibration.py output/ --out calibration/pro_reference.json
  3. From then on analyse_song.py automatically anchors component "10"s to
     the professional distribution (p25/p75 of the references) and reports
     each singer's percentile against the pack.

The calibration file stores the raw sorted reference values per metric, so
every anchored score remains fully auditable: "you scored 8.7 on intonation
because you beat 62% of these N references" is verifiable by hand.

Quality gates:
  * JSONs whose voice_quality was measured in fallback mode (no parselmouth)
    are excluded from voice-quality metrics — approximations must not set
    professional anchors.
  * Fewer than 5 usable values for a metric -> that metric stays on
    theoretical anchors (the scorer enforces the same minimum).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime

import numpy as np

MIN_RECOMMENDED_REFERENCES = 10

# metric key in calibration file -> (path into analysis JSON, requires_praat)
METRIC_PATHS = {
    "intonation_median_abs_deviation_cents": (("intonation", "median_abs_deviation_cents"), False),
    "intonation_median_intra_note_drift_cents": (("intonation", "median_intra_note_drift_cents"), False),
    "voice_quality_jitter_local_percent_median": (("voice_quality", "jitter_local_percent_median"), True),
    "voice_quality_shimmer_local_percent_median": (("voice_quality", "shimmer_local_percent_median"), True),
    "voice_quality_hnr_db_median": (("voice_quality", "hnr_db_median"), True),
    "vibrato_median_rate_hz": (("vibrato", "median_rate_hz"), False),
    "vibrato_median_extent_cents": (("vibrato", "median_extent_cents"), False),
    "vibrato_pct_notes_with_vibrato": (("vibrato", "pct_notes_with_vibrato"), False),
    "dynamics_phrase_level_spread_db": (("dynamics", "phrase_level_spread_db"), False),
    "dynamics_effective_dynamic_range_db": (("dynamics", "effective_dynamic_range_db"), False),
    "phrasing_median_phrase_s": (("phrasing", "median_phrase_s"), False),
}


def collect_json_paths(inputs):
    paths = []
    for item in inputs:
        if os.path.isdir(item):
            paths.extend(sorted(glob.glob(os.path.join(item, "**", "*_analysis.json"), recursive=True)))
        elif os.path.isfile(item) and item.endswith(".json"):
            paths.append(item)
        else:
            print(f"  WARNING: skipping {item} (not a dir or .json file)")
    # de-duplicate, preserve order
    seen = set()
    unique = []
    for p in paths:
        rp = os.path.realpath(p)
        if rp not in seen:
            seen.add(rp)
            unique.append(p)
    return unique


def dig(data, path):
    node = data
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    if isinstance(node, (int, float)) and np.isfinite(node):
        return float(node)
    return None


def main():
    parser = argparse.ArgumentParser(description="Build VOXAI pro-reference calibration.")
    parser.add_argument("inputs", nargs="+", help="Analysis JSON files and/or folders containing *_analysis.json")
    parser.add_argument("--out", default="calibration/pro_reference.json", help="Output calibration path")
    args = parser.parse_args()

    json_paths = collect_json_paths(args.inputs)
    if not json_paths:
        print("No analysis JSONs found.")
        return 1

    values = {key: [] for key in METRIC_PATHS}
    sources = []
    excluded = []

    for path in json_paths:
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as exc:
            print(f"  WARNING: cannot read {path}: {exc}")
            continue
        if "technical_score" not in data and "pitch" not in data:
            print(f"  WARNING: {path} does not look like a backend analysis JSON — skipped")
            continue

        praat_ok = str(data.get("voice_quality", {}).get("method", "")).startswith("praat")
        if not praat_ok:
            excluded.append(os.path.basename(path))

        used_any = False
        for key, (metric_path, requires_praat) in METRIC_PATHS.items():
            if requires_praat and not praat_ok:
                continue
            value = dig(data, metric_path)
            if value is not None:
                values[key].append(value)
                used_any = True
        if used_any:
            sources.append(os.path.basename(path))

    if not sources:
        print("No usable reference analyses found.")
        return 1

    metrics = {}
    for key, vals in values.items():
        if len(vals) < 2:
            continue
        arr = np.sort(np.asarray(vals, dtype=float))
        metrics[key] = {
            "n": len(arr),
            "values_sorted": [round(float(v), 4) for v in arr],
            "p10": round(float(np.percentile(arr, 10)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p50": round(float(np.percentile(arr, 50)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
            "p90": round(float(np.percentile(arr, 90)), 4),
        }

    calibration = {
        "version": "pro_reference_v1",
        "created": datetime.now().isoformat(timespec="seconds"),
        "n_references": len(sources),
        "source_files": sources,
        "praat_excluded_files": excluded,
        "note": (
            "Professional reference distributions for VOXAI technical-score "
            "anchoring. Component '10' anchors use p25 (lower-is-better) or "
            "p75 (higher-is-better) of these values; theoretical zero anchors "
            "are unchanged. Metrics with n < 5 are ignored by the scorer."
        ),
        "metrics": metrics,
    }

    out_path = args.out
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(calibration, f, indent=2)

    print(f"\nCalibration written: {out_path}")
    print(f"  References used: {len(sources)}")
    if excluded:
        print(f"  Excluded from voice-quality anchors (no Praat metrics): {len(excluded)}")
    for key, stats in metrics.items():
        marker = "" if stats["n"] >= 5 else "  (n<5 — scorer will ignore)"
        print(f"  {key}: n={stats['n']} median={stats['p50']}{marker}")
    if len(sources) < MIN_RECOMMENDED_REFERENCES:
        print(f"\n  NOTE: only {len(sources)} references — {MIN_RECOMMENDED_REFERENCES}+ recommended "
              f"(15-20 ideal) for stable professional anchors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
