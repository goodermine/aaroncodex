#!/usr/bin/env python3
"""
Builds the deterministic prescription map from the VOXAI Scientific
Exercise Library.

    python tools/build_prescription_map.py \
        [--library ../../openclaw-data/vox-coach/knowledge/VOXAI_Scientific_Exercise_Library.txt] \
        [--out knowledge/prescription_map.json]

Everything in the output is extracted VERBATIM from the library: category
headings, exercise numbers/names, next-take cues, and each prescribed
exercise's full 7-field entry. The map records the library's sha256 so the
engine can detect when the library has changed since the map was built
(then it warns instead of silently prescribing from stale content).

Re-run this tool whenever the library is edited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime

# Category key per selector heading + the 7-day template that matches it
# (templates A-F are defined at the end of the library itself).
SELECTOR_META = {
    "If the main limiter is BREATH / SUPPORT": ("breath_support", "B"),
    "If the singer sounds PRESSED / STRAINED": ("pressed_strained", "A"),
    "If the singer sounds BREATHY / LEAKY": ("breathy_leaky", "A"),
    "If high notes are the issue": ("high_notes", "C"),
    "If the voice flips or breaks through the bridge": ("register_bridge", "C"),
    "If tone is muffled, swallowed, or dull": ("muffled_dull", "E"),
    "If tone is nasal, pinched, or overly bright": ("nasal_bright", "E"),
    "If jaw or tongue tension is obvious": ("jaw_tongue_tension", "E"),
    "If pitch accuracy is unstable": ("pitch_accuracy", "D"),
    "If runs, riffs, or fast notes are messy": ("runs_riffs", "F"),
    "If the singer needs a warm-up/reset": ("warmup_reset", None),
    "If the singer is tired or post-performance": ("recovery", None),
    "If vibrato is absent, uneven, forced, or wobbly": ("vibrato", None),
}


def parse_library(text):
    # Selector blocks
    categories = {}
    selector_re = re.compile(
        r"^## (If [^\n]+)\nUse: ([^\n]+)\nBest next-take cue: ([^\n]+)", re.M)
    for heading, use_line, cue in selector_re.findall(text):
        heading = heading.strip()
        meta = SELECTOR_META.get(heading)
        if not meta:
            print(f"  WARNING: selector heading not in SELECTOR_META, skipped: {heading}")
            continue
        key, template = meta
        # Split on commas, then parse each item as "<num> <name>" or a
        # range "<num>–<num> <name>". Names may legitimately contain
        # digits and periods ("33 1.5 Scale Lip Bubbles"), so never split
        # inside an item.
        exercises = []
        for item in use_line.rstrip(".").split(","):
            item = item.strip()
            m = re.match(r"^(\d+)\s*[–-]\s*(\d+)\s+(.*)$", item)
            if m:
                lo, hi, name = int(m.group(1)), int(m.group(2)), m.group(3).strip()
                for num in range(lo, hi + 1):
                    exercises.append({"num": num, "name": name})
                continue
            m = re.match(r"^(\d+)\s+(.*)$", item)
            if m:
                exercises.append({"num": int(m.group(1)), "name": m.group(2).strip()})
            elif item:
                print(f"  WARNING: unparseable selector item in '{heading}': {item!r}")
        categories[key] = {
            "selector_heading": heading,
            "exercises": exercises,
            "next_take_cue": cue.strip().strip("“”\""),
            "seven_day_template": template,
        }

    # Full exercise entries (verbatim 7-field bodies)
    entries = {}
    entry_re = re.compile(r"^### (\d+)\. ([^\n]+)\n((?:- [^\n]+\n?)+)", re.M)
    for num, name, body in entry_re.findall(text):
        entries[int(num)] = {"name": name.strip(), "body": body.strip()}
    return categories, entries


def main():
    parser = argparse.ArgumentParser(description="Build the VOXAI prescription map.")
    parser.add_argument("--library",
                        default="../../openclaw-data/vox-coach/knowledge/VOXAI_Scientific_Exercise_Library.txt")
    parser.add_argument("--out", default="knowledge/prescription_map.json")
    args = parser.parse_args()

    lib_path = os.path.abspath(args.library)
    with open(lib_path, encoding="utf-8") as f:
        text = f.read()
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()

    categories, entries = parse_library(text)
    missing = []
    for key, cat in categories.items():
        for ex in cat["exercises"]:
            entry = entries.get(ex["num"])
            if entry:
                ex["detail"] = entry["body"]
                # Name from the entry header is authoritative
                ex["name"] = entry["name"]
            else:
                missing.append((key, ex["num"]))

    # Store the library location RELATIVE to the backend root so the hash
    # check works on any machine, not just the one that built the map.
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    payload = {
        "version": "prescription_map_v1",
        "built": datetime.now().isoformat(timespec="seconds"),
        "library_path": os.path.relpath(lib_path, backend_root),
        "library_sha256": sha,
        "n_categories": len(categories),
        "n_exercises_in_library": len(entries),
        "categories": categories,
        "note": (
            "All content extracted verbatim from the exercise library. "
            "Re-run tools/build_prescription_map.py after any library edit; "
            "the engine warns when the library hash no longer matches."
        ),
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Prescription map written: {args.out}")
    print(f"  Library: {lib_path}")
    print(f"  sha256: {sha[:16]}…")
    print(f"  Categories: {len(categories)} | exercises in library: {len(entries)}")
    for key, cat in categories.items():
        print(f"  {key}: {len(cat['exercises'])} exercises (template {cat['seven_day_template']})")
    if missing:
        print("  WARNING — selector references without a matching entry:")
        for key, num in missing:
            print(f"    {key}: exercise {num}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
