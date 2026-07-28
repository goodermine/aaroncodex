#!/usr/bin/env python3
"""Generate the plain-English metric reference from the LIVE calibration pack.

Aaron wanted to be able to read his own reports — to know what each measured
number means and what "good" looks like. The durable part (what each metric IS,
in plain language) lives in this script. The numbers ("good" ranges) are read
from the professional calibration pack at generation time, so they can never
drift from what the engine actually scores against.

Run it after any re-calibration and the reference is true again:

    python3 tools/metric_glossary.py

Writes docs/YOUR_METRICS_EXPLAINED.md. The ranges are p10 / p50 / p90 of the
professional reference vocals — "typical" is p50, a middle-of-the-pack pro,
which is what 10/10 anchors to.
"""

from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "voxanalysis/vox-analysis/engine/calibration/pro_reference.json")
OUT = os.path.join(ROOT, "docs/YOUR_METRICS_EXPLAINED.md")

# metric key in the pack -> (heading, plain-English meaning, direction, unit)
# direction: "low" = lower is better, "high" = higher is better, "dial" = neither.
METRICS = [
    ("group", "How clean the tone is", None, None),
    ("voice_quality_hnr_db_median",
     "HNR — clean tone vs breath", "high", "dB",
     "How much of your sound is pure tone versus air and noise. Higher is "
     "cleaner. A low number means breathy or fuzzy — though a room or phone mic "
     "drags this down too, so it is judged gently on live takes."),
    ("voice_quality_cpps_db",
     "CPPS — clarity and ring", "high", "dB",
     "How well-defined and 'present' the tone is — the difference between a dull "
     "sound and a ringing one. This is the number that jumps when a voice comes "
     "into focus."),
    ("voice_quality_jitter_local_percent_median",
     "Jitter — pitch steadiness", "low", "%",
     "Tiny cycle-to-cycle wobbles in pitch. Lower is steadier. High jitter reads "
     "as an unsteady, effortful tone. Sensitive to recording quality."),
    ("voice_quality_shimmer_local_percent_median",
     "Shimmer — loudness steadiness", "low", "%",
     "The same idea as jitter but for loudness — tiny wobbles in volume "
     "cycle-to-cycle. Lower is steadier."),

    ("group", "Pitch", None, None),
    ("intonation_median_abs_deviation_cents",
     "Pitch centre — how in-tune", "low", "cents",
     "How far you sit from the nearest correct note, in cents (100 cents = one "
     "semitone). Lower is more accurate. Note the pros are NOT at zero — "
     "dead-perfect pitch sounds robotic; humans sit slightly off and it reads as "
     "musical."),
    ("intonation_median_intra_note_drift_cents",
     "Held-note drift — does it stay put", "low", "cents",
     "How much a note slides around WHILE you hold it. Lower is steadier. This is "
     "different from pitch centre: you can start in tune and still drift."),

    ("group", "Breath — Aaron's ceiling", None, None),
    ("breath_pct_sagging_endings",
     "Phrase endings that sag", "low", "%",
     "The share of phrase-ends where the pitch slides off as the air runs out. "
     "Lower is better — but even pros sag on about a third of endings, because a "
     "falling ending is partly a style choice. This is the measured limiter on "
     "Aaron's voice: it runs near the top of the pro range."),
    ("phrasing_median_phrase_s",
     "Phrase length — how long you sustain", "dial", "s",
     "How long your phrases run before a breath. Longer needs more breath "
     "management; shorter is a valid pop/rock style, not a fault."),

    ("group", "Vibrato", None, None),
    ("vibrato_median_rate_hz",
     "Vibrato rate — how fast the wobble", "dial", "Hz",
     "Wobbles per second. Too slow reads as a wobble; too fast reads as nervous. "
     "There is a natural band pros sit in."),
    ("vibrato_median_extent_cents",
     "Vibrato width — how wide the wobble", "dial", "cents",
     "How far the pitch swings on each wobble. A stylistic choice, not a score."),
    ("vibrato_pct_notes_with_vibrato",
     "Vibrato usage — how often", "dial", "%",
     "The share of long notes carrying vibrato. Straight tone is a valid style; "
     "this is not a target to max out."),

    ("group", "Loudness and shape", None, None),
    ("dynamics_effective_dynamic_range_db",
     "Dynamic range — soft to loud", "high", "dB",
     "The gap between your quietest and loudest singing. Higher is more "
     "expressive; a flat, one-volume performance scores low. Moved by "
     "compression and mastering, so judged gently on processed audio."),
]

# Not in the scored pack — diagnostics explained without a pro range.
DIAGNOSTICS = [
    ("H1−H2 — breathy vs pressed",
     "How firmly your vocal folds close. Your voice makes a fundamental (the "
     "note, H1) plus overtones; H2 is the second overtone. H1−H2 is simply how "
     "much LOUDER the fundamental is than that second overtone.\n\n"
     "  * Big positive (around +20 dB) = folds barely closing, air escaping = "
     "BREATHY. Weak falsetto lives here.\n"
     "  * Near zero or negative (−10 to −15 dB) = folds closing firmly, long "
     "closed phase = PRESSED and rich. Overdrive lives here.\n\n"
     "It is a DIAL, not a score — breathy suits a tender verse, pressed suits a "
     "belt. When a note 'falls out' and goes airy, that is H1−H2 climbing toward "
     "breathy. Measured on Aaron's own CVT reference test it swung from +22 dB "
     "(breathy) to −14 dB (pressed) — the whole weak-vs-reinforced-falsetto story "
     "in one number."),
    ("Metallic index — how much 'ring' / metal",
     "A composite of the spectral 'ring' measures (2–4 kHz energy, brightness, "
     "clarity, adduction). Higher = more metallic, carrying, present. It reports "
     "HOW MUCH metal, never WHICH vocal mode — all the loud modes are metallic, "
     "and telling them apart from one recording is not reliable. Scored within "
     "one file only, never compared across recordings."),
    ("Singer's formant — carrying power",
     "A cluster of energy around 2–4 kHz that lets a voice cut through without "
     "extra volume — the 'ring' that carries over an orchestra. Not yet anchored "
     "to the pro pack, so reported as a reading rather than a score."),
]


def fmt(v):
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


def main() -> int:
    if not os.path.isfile(PACK):
        print(f"No calibration pack at {PACK}")
        return 1
    pack = json.load(open(PACK))
    m = pack.get("metrics", {})
    n = pack.get("n_references", "?")

    lines = [
        "# Read your own metrics",
        "",
        "*Generated from the live calibration pack by `tools/metric_glossary.py`. "
        "Re-run it after any re-calibration so the numbers are never stale.*",
        "",
        f"Every measured number is compared to **{n} professional reference "
        "vocals**. The ranges below are:",
        "",
        "- **weak pro (p10)** — bottom 10% of the professionals",
        "- **typical (p50)** — a middle-of-the-pack professional. **This is what "
        "\"10 / 10\" anchors to** — you are measured against a working pro, not "
        "against perfection.",
        "- **strong pro (p90)** — top 10%",
        "",
        "So a 7 is a genuinely good singer. The scale was never zero-to-hero; it "
        "is zero-to-*professional*.",
        "",
        "---",
        "",
    ]

    for entry in METRICS:
        if entry[0] == "group":
            lines += [f"## {entry[1]}", ""]
            continue
        key, heading, direction, unit, meaning = entry
        s = m.get(key)
        arrow = {"low": "lower is better", "high": "higher is better",
                 "dial": "a dial, not a score — depends on the sound you want"}.get(direction, "")
        lines.append(f"### {heading}")
        lines.append("")
        lines.append(meaning)
        lines.append("")
        if s:
            lines.append(f"> **Pros:** weak {fmt(s['p10'])} · typical "
                         f"**{fmt(s['p50'])}** · strong {fmt(s['p90'])} {unit}"
                         + (f"  ·  _{arrow}_" if arrow else ""))
        else:
            lines.append(f"> _Not in the current pack ({key})._")
        lines.append("")

    lines += ["---", "", "## Diagnostics (measured, but not scored)", "",
              "These are reported to help you understand the sound, but they are "
              "not part of any score — they are dials or unanchored readings.", ""]
    for heading, meaning in DIAGNOSTICS:
        lines += [f"### {heading}", "", meaning, ""]

    lines += [
        "---", "",
        "## The two honest caveats",
        "",
        "1. **These ranges move when the pack is rebuilt.** The *meanings* above "
        "never change; the *numbers* are read live from the calibration pack, so "
        "re-running this script after a re-calibration keeps them true. If a "
        "number here ever disagrees with a fresh report, re-run the script.",
        "2. **Some metrics measure the microphone, not the voice.** HNR, CPPS, "
        "jitter and shimmer get dragged down by a room or phone recording — which "
        "is why live takes lead with the **capture-fair** score, which sets those "
        "aside. A low voice-quality number on a tavern take is usually the room, "
        "not you.",
        "",
    ]

    with open(OUT, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {os.path.relpath(OUT, ROOT)}  ({n} references)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
