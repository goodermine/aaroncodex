"""Re-score every archived analysis IN PLACE so the whole archive sits on one
calibration pack.

Why this exists
---------------
`rescore_all.py` recomputes every score and writes the SCORE TABLES, but it
never writes back into the archive. So an analysis produced against an older
calibration pack keeps that pack's stored `technical_score` forever, and every
tool that reads a stored score (`tools/ranked_takes.py`, `tools/show_results.py`,
the singer PDFs) silently mixes packs.

`is_legacy_score()` does not catch this — it checks the contract and the rubric,
and an older-pack score passes both. `score_conflict()` DOES catch it, which is
the contradiction this tool resolves: 113 of 182 archived analyses were anchored
to pack 0da01ef1e30f while the pinned contract said fb035034bebd, so preflight
passed while `score_conflict()` refused to compare them with each other.
Measured spread between the two packs: up to +/-0.5 on the overall, median 0.00,
62 takes moving by >=0.1. Small per take, fatal to a comparison.

What it does
------------
Recomputes `technical_score` with the live `compute_technical_score()` — the one
engine, per rule 1 — from the metrics already stored in each file. It never
touches audio and never touches a measurement; only the score block is rewritten.

`calibration.file` is preserved when one is already stored. That field is an
absolute path from whichever machine ran the analysis; it is a breadcrumb, not
part of the score identity (`score_identity()` does not include it). Preserving
it keeps this tool byte-idempotent and keeps the diff to actual score changes
instead of 182 machine-path rewrites.

Run:
    python3 docs/score-metrics/rescore_archive_inplace.py --dry-run   # report
    python3 docs/score-metrics/rescore_archive_inplace.py             # apply

Then refresh the tables and gate:
    python3 docs/score-metrics/rescore_all.py
    python3 tools/score_preflight.py
"""
import json, glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "voxanalysis/vox-analysis/engine"))
from analyse_song import (  # noqa: E402
    compute_technical_score, load_calibration, DEFAULT_CALIBRATION_PATH)

ARCHIVE = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")
DRY = "--dry-run" in sys.argv


def main() -> int:
    cal = load_calibration(DEFAULT_CALIBRATION_PATH)
    if cal is None:
        print("FAIL  no calibration pack loaded — refusing to re-score. "
              "Uncalibrated anchors read ~2-3 points too harsh.")
        return 1

    changed, unchanged, skipped = [], 0, []
    for path in sorted(glob.glob(os.path.join(ARCHIVE, "*_analysis.json"))):
        name = os.path.basename(path)
        with open(path) as fh:
            d = json.load(fh)
        old = d.get("technical_score") or {}

        # A retired-legacy stub carries no numbers by design. Re-scoring it here
        # would resurrect a score the retire step deliberately removed, so it is
        # left alone; rescore_all.py reports it as retired.
        if old.get("status") == "retired_legacy_score":
            skipped.append(name)
            continue

        new = compute_technical_score(d, cal)
        if not new:
            skipped.append(name)
            continue

        stored_file = (old.get("calibration") or {}).get("file")
        if stored_file and isinstance(new.get("calibration"), dict):
            new["calibration"]["file"] = stored_file

        if json.dumps(new, sort_keys=True) == json.dumps(old, sort_keys=True):
            unchanged += 1
            continue

        changed.append((name,
                        old.get("overall_score_0_to_10"),
                        new.get("overall_score_0_to_10"),
                        (old.get("identity") or {}).get("calibration_fingerprint"),
                        (new.get("identity") or {}).get("calibration_fingerprint")))
        if not DRY:
            d["technical_score"] = new
            with open(path, "w") as fh:
                json.dump(d, fh, indent=2, ensure_ascii=False)
                fh.write("\n")

    verb = "would be re-scored" if DRY else "re-scored"
    print(f"{len(changed)} {verb}, {unchanged} already current, "
          f"{len(skipped)} skipped (retired or unscoreable)")
    moved = [c for c in changed if c[1] is not None and c[2] is not None
             and abs(c[2] - c[1]) >= 0.05]
    if moved:
        moved.sort(key=lambda c: abs(c[2] - c[1]), reverse=True)
        print(f"\n{len(moved)} take(s) moved by >=0.05 — largest:")
        for name, o, n, fo, fn in moved[:10]:
            print(f"  {o:5.2f} -> {n:5.2f}  ({n - o:+.2f})  {fo} -> {fn}  {name}")
    if DRY and changed:
        print("\nDry run — nothing written. Re-run without --dry-run to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
