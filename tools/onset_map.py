#!/usr/bin/env python3
"""Onset map — a reference vs a singer, note by note.

    python3 tools/onset_map.py REFERENCE.json TAKE.json \
        --ref-label "John Farnham" --take-label "Aaron" \
        --song "Pressure Down" --out onset-map.png

Each note is plotted by HOW IT STARTS relative to its own settled centre —
scooped up from below (blue, down), overshot from above (amber, up), or clean
(grey, near zero). It makes the scoop/overshoot pattern (ENTRY ACCURACY,
docs/handoffs/SCORE_READING_LIMITATIONS.md limitation 5) visible where a single
percentage cannot: a reference is usually clean with a few deep DELIBERATE
scoops, while a habitual scooper slides into most notes.

The onset deviation is reconstructed from the stored F0 contour (first ~0.25 s
vs the note's settled centre) and matches the engine's own onset percentages
closely. It is a DIAGNOSTIC VISUALISATION, not a score — CLAUDE.md rule 1 is
untouched, no /10 is produced. The two panels are different performances on
their own clocks: read the pattern, never note-for-note. Onsets off a
stem-separated take carry measurement noise in the quiet note-start region, so
prefer dry solo recordings for a definitive read (limitation 5).
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for fp in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
    font_manager.fontManager.addfont(fp)
plt.rcParams["font.family"] = "DejaVu Sans"

BLUE = "#1d4ed8"    # scoop (started below, slid up)
AMBER = "#b45309"   # overshoot (started above, settled down)
GREY = "#9aa2af"    # clean
INK = "#111827"
MUTE = "#6b7280"
BAND = "#eef1f5"
CLEAN_TH = 35       # +/- cents = the "clean zone"

import argparse
ap = argparse.ArgumentParser(description="Onset map: reference vs singer, note by note.")
ap.add_argument("reference", help="path to the reference _analysis.json")
ap.add_argument("take", help="path to the singer's _analysis.json")
ap.add_argument("--ref-label", default="Reference")
ap.add_argument("--take-label", default="This take")
ap.add_argument("--song", default="")
ap.add_argument("--out", default="/home/user/aaroncodex/Onset-Map.png")
args = ap.parse_args()
FILES = [(args.ref_label, args.reference), (args.take_label, args.take)]


def per_note(f):
    d = json.load(open(f))
    fc = d["pitch"]["f0_contour"]
    rate, vals = fc["rate_hz"], fc["values"]
    rows = []
    for n in d["intonation"]["notes"]:
        s, dur = n.get("start_s"), n.get("duration_s")
        if s is None or dur is None or dur < 0.2:
            continue
        seg = [v for v in vals[int(round(s * rate)):int(round((s + dur) * rate))] if v is not None]
        if len(seg) < 3:
            continue
        onset = float(np.mean(seg[:max(2, int(round(0.25 * rate)))]))
        settled = float(np.median(seg[len(seg) // 2:]))
        rows.append((s, onset - settled, n.get("note", "")))
    return rows, d["onsets"], d.get("duration_seconds")


fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.6), sharex=False)
fig.subplots_adjust(left=0.085, right=0.79, top=0.83, bottom=0.085, hspace=0.42)

for ax, (title, f) in zip(axes, FILES):
    rows, eng, dur = per_note(f)
    dev = np.array([r[1] for r in rows])
    t = np.array([r[0] for r in rows])
    clean = np.abs(dev) <= CLEAN_TH
    scoop = dev < -CLEAN_TH
    over = dev > CLEAN_TH

    ax.axhspan(-CLEAN_TH, CLEAN_TH, color=BAND, zorder=0)
    ax.axhline(0, color="#c3c9d2", lw=0.8, zorder=1)

    # lollipop stems from zero, dot at the deviation
    for mask, col in ((scoop, BLUE), (over, AMBER)):
        ax.vlines(t[mask], 0, dev[mask], color=col, lw=1.3, alpha=0.85, zorder=2)
        ax.scatter(t[mask], dev[mask], s=22, color=col, zorder=3,
                   edgecolor="white", linewidth=0.6)
    ax.scatter(t[clean], dev[clean], s=16, color=GREY, zorder=3,
               edgecolor="white", linewidth=0.5)

    # annotate the deepest deliberate scoops (Farnham) / worst (Aaron)
    order = np.argsort(dev)
    for idx in order[:4]:
        if dev[idx] < -120:
            ax.annotate(rows[idx][2], (t[idx], dev[idx]),
                        xytext=(0, -11), textcoords="offset points",
                        ha="center", va="top", fontsize=7.5, color=BLUE)

    ax.set_ylim(-560, 440)
    ax.set_xlim(-3, (dur or t.max()) + 3)
    ax.set_title(title, fontsize=12, fontweight="bold", color=INK, loc="left", pad=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c9d2")
    ax.tick_params(colors=MUTE, labelsize=8)
    ax.set_ylabel("cents from the\nnote's own centre", fontsize=8.5, color=MUTE)

    # per-panel stat box, to the right
    txt = (f"clean  {eng['pct_clean']:.0f}%\n"
           f"scooped  {eng['pct_scooped']:.0f}%\n"
           f"overshot  {eng['pct_overshot']:.0f}%\n"
           f"scoop depth  {eng['median_scoop_depth_cents']:.0f}c")
    ax.text(1.015, 0.5, txt, transform=ax.transAxes, fontsize=9, va="center",
            ha="left", color=INK, family="DejaVu Sans",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f7f9fc", ec="#dbe0e8"))

axes[1].set_xlabel("time through the song (seconds)", fontsize=8.5, color=MUTE)

fig.suptitle(f"How each note STARTS{' — ' + args.song if args.song else ''}",
             fontsize=15.5, fontweight="bold", color=INK, x=0.085, ha="left", y=0.975)
fig.text(0.085, 0.935,
         "Each dot is one note entry. Shaded band = the clean zone (±35c of the note's centre).",
         fontsize=9, color=MUTE, ha="left")
fig.text(0.085, 0.912,
         "Below it = scooped up from below · above it = overshot from above. "
         "Two different takes — read the pattern, not note-for-note.",
         fontsize=9, color=MUTE, ha="left")

handles = [
    plt.Line2D([0], [0], marker="o", color=BLUE, lw=0, markersize=7, label="scoop"),
    plt.Line2D([0], [0], marker="o", color=AMBER, lw=0, markersize=7, label="overshoot"),
    plt.Line2D([0], [0], marker="o", color=GREY, lw=0, markersize=7, label="clean"),
]
fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.995, 0.965),
           frameon=False, fontsize=9, labelcolor=INK, ncol=1,
           handletextpad=0.4, labelspacing=0.5)

fig.savefig(args.out, dpi=170, facecolor="white")
print("wrote", args.out)
