#!/usr/bin/env python3
"""
Progress ledger: metric trajectories for a singer across analysed takes.

Usage:
    python tools/progress_report.py output/ --singer aaron [--song danger-zone]
    python tools/progress_report.py output/ --singer aaron --out reports/aaron-progress.md

Scans analysis JSONs (skips reference originals), groups by singer (and
optionally song) using the standard `<date>-<singer>-<song>-take-NNN`
file naming, orders by date + take number, and reports how each headline
metric is trending. Pure reporting — reads the JSONs Candi already
produces, no audio work.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re

import numpy as np

TAKE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+?)-take-(\d{3})")

METRICS = [
    ("technical score", ("technical_score", "overall_score_0_to_10"), "higher"),
    ("capture-fair score", ("technical_score", "capture_fair_score_0_to_10"), "higher"),
    ("intonation (median cents off)", ("intonation", "median_abs_deviation_cents"), "lower"),
    ("intra-note drift (cents)", ("intonation", "median_intra_note_drift_cents"), "lower"),
    ("notes within 10 cents (%)", ("intonation", "pct_notes_within_10_cents"), "higher"),
    ("jitter (%)", ("voice_quality", "jitter_local_percent_median"), "lower"),
    ("HNR (dB)", ("voice_quality", "hnr_db_median"), "higher"),
    ("CPPS (dB)", ("voice_quality", "cpps_db"), "higher"),
    ("vibrato presence (%)", ("vibrato", "pct_notes_with_vibrato"), "higher"),
    ("phrase length (s)", ("phrasing", "median_phrase_s"), "higher"),
    ("sagging phrase ends (%)", ("breath", "pct_sagging_endings"), "lower"),
]


def dig(data, path):
    node = data
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node if isinstance(node, (int, float)) else None


def collect(inputs, singer, song=None):
    takes = []
    for item in inputs:
        paths = (sorted(glob.glob(os.path.join(item, "**", "*_analysis.json"), recursive=True))
                 if os.path.isdir(item) else [item])
        for p in paths:
            base = os.path.basename(p)
            m = TAKE_PATTERN.match(base)
            if not m:
                continue                      # references / unnamed files
            date, slug, take_no = m.group(1), m.group(2), int(m.group(3))
            if singer.lower() not in slug.lower():
                continue
            if song and song.lower() not in slug.lower():
                continue
            try:
                data = json.load(open(p))
            except Exception:
                continue
            song_slug = slug.lower().replace(singer.lower(), "").strip("-")
            takes.append({"date": date, "song": song_slug, "take": take_no,
                          "analysed_at": data.get("analysed_at", ""),
                          "file": base, "data": data})
    # Order by recording date, then analysis timestamp (present in newer
    # JSONs), then take number — same-day takes from different venues stay
    # in true chronological order when the timestamp exists.
    takes.sort(key=lambda t: (t["date"], t["analysed_at"], t["take"]))
    return takes


def trend(values, direction):
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return "—"
    delta = vals[-1] - vals[0]
    if abs(delta) < 1e-9:
        return "steady"
    improving = delta > 0 if direction == "higher" else delta < 0
    arrow = "improving" if improving else "worse"
    return f"{arrow} ({vals[0]} → {vals[-1]})"


def main():
    parser = argparse.ArgumentParser(description="VOXAI progress ledger.")
    parser.add_argument("inputs", nargs="+", help="Folders or analysis JSONs")
    parser.add_argument("--singer", required=True)
    parser.add_argument("--song", help="Restrict to one song slug")
    parser.add_argument("--out", help="Write Markdown report here")
    args = parser.parse_args()

    takes = collect(args.inputs, args.singer, args.song)
    if not takes:
        raise SystemExit("No matching takes found (expected <date>-<singer>-<song>-take-NNN naming).")

    lines = [
        f"# Progress Ledger — {args.singer}" + (f" — {args.song}" if args.song else ""),
        "",
        f"{len(takes)} takes, {takes[0]['date']} → {takes[-1]['date']}.",
        "",
        "| Take | Date | Song | Score | Fair | Cents off | Drift | Vibrato % |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for t in takes:
        d = t["data"]
        lines.append("| {file} | {date} | {song} | {sc} | {fair} | {dev} | {drift} | {vib} |".format(
            file=f"take {t['take']:03d}", date=t["date"], song=t["song"][:24],
            sc=dig(d, ("technical_score", "overall_score_0_to_10")) or "—",
            fair=dig(d, ("technical_score", "capture_fair_score_0_to_10")) or "—",
            dev=dig(d, ("intonation", "median_abs_deviation_cents")) or "—",
            drift=dig(d, ("intonation", "median_intra_note_drift_cents")) or "—",
            vib=dig(d, ("vibrato", "pct_notes_with_vibrato")) or "—",
        ))

    lines += ["", "## Trends (first take → latest)", "", "| Metric | Trend |", "|---|---|"]
    for label, path, direction in METRICS:
        values = [dig(t["data"], path) for t in takes]
        lines.append(f"| {label} | {trend(values, direction)} |")

    lines += [
        "",
        "*Scores from different calibration-pack sizes are approximately comparable; "
        "raw metrics (cents, dB, %) are exactly comparable. Trends use first vs latest take.*",
    ]

    report = "\n".join(lines)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            f.write(report + "\n")


if __name__ == "__main__":
    main()
