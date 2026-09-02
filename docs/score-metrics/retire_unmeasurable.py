#!/usr/bin/env python3
"""Retire the score of analyses that can no longer be re-measured.

Phase 1 of docs/VOX_SYSTEM_REVIEW_2026-09-02.md re-analyses every take on one
measurement. A take whose vocal stem AND original mix are both gone cannot be
re-measured, and its stored score sits on the old measurement scale forever.
Leaving that score quotable would keep the archive split across two eras; this
replaces it with a stub that carries no number, exactly like
retire_legacy_scores.py does for superseded rubrics. The raw measurements stay
in the file for the record; nothing that reads a score can reach a number.

Never guess which takes qualify: the list comes from the reanalyse_archive.py
"stem not found" report AFTER pair_reference_audio.py has failed to find a
source mix for them. Idempotent.

    python3 docs/score-metrics/retire_unmeasurable.py --list missing.txt --dry-run
    python3 docs/score-metrics/retire_unmeasurable.py --list missing.txt
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARCHIVE = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")
STATUS = "retired_legacy_score"     # the status every reader already refuses to quote


def stub(old: dict, era: str) -> dict:
    return {
        "status": STATUS,
        "retired_rubric": ((old or {}).get("provenance") or "unknown").split(" —")[0],
        "retired_measurement_era": era,
        "reason": (
            "Measured on a superseded measurement build (pre-16-Aug-2026 held-note "
            "drift) and its source audio is no longer available, so it cannot be "
            "re-measured on the current engine. The score was on a different scale "
            "from current scores and has been removed; the raw measurements remain "
            "for the record."
        ),
        "action": "Supply the original mix or vocal stem and re-run tools/reanalyse_archive.py.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", required=True,
                    help="Text file: one archived analysis basename per line "
                         "(with or without _analysis.json); '#' comments allowed")
    ap.add_argument("--archive", default=ARCHIVE)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, os.path.join(ROOT, "voxanalysis/vox-analysis/engine"))
    import analyse_song as A
    live = A.measurement_fingerprint()

    wanted = []
    for line in open(args.list):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split()[0]
        name = name[:-len("_analysis.json")] if name.endswith("_analysis.json") else name
        wanted.append(name)

    retired, skipped, missing = [], [], []
    for name in wanted:
        path = os.path.join(args.archive, f"{name}_analysis.json")
        if not os.path.isfile(path):
            missing.append(name)
            continue
        with open(path) as fh:
            data = json.load(fh)
        era = A.measurement_era(data)
        score = data.get("technical_score")
        if era == live:
            skipped.append((name, "already on the current measurement — not retired"))
            continue
        if isinstance(score, dict) and score.get("status") == STATUS:
            skipped.append((name, "already retired"))
            continue
        data["technical_score"] = stub(score if isinstance(score, dict) else {}, era)
        if not args.dry_run:
            tmp = path + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(data, fh, indent=2)
                fh.write("\n")
            os.replace(tmp, path)
        retired.append(name)

    print(f"{'would retire' if args.dry_run else 'retired'} : {len(retired)}")
    for n in retired:
        print(f"    {n}")
    if skipped:
        print(f"skipped : {len(skipped)}")
        for n, why in skipped:
            print(f"    {n}  ({why})")
    if missing:
        print(f"not in archive : {len(missing)}")
        for n in missing:
            print(f"    {n}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
