"""Retire stale scores so they can never be quoted again.

Any archived analysis whose stored `technical_score` predates the provenance
contract (or came from an older rubric) has that score REPLACED with a stub
carrying no numbers. The raw measurements are untouched, so the take can always
be re-scored with the current engine — but there is no stale `/10` left in the
file for anything to read, display, trend or paste into a report.

The original numbers remain in git history for audit; they are simply no longer
reachable by any code path that reads a score.

Idempotent — safe to re-run. Run after pulling new analyses:

    python3 docs/score-metrics/retire_legacy_scores.py            # apply
    python3 docs/score-metrics/retire_legacy_scores.py --dry-run  # report only
"""
import json, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "voxanalysis/vox-analysis/engine"))
from analyse_song import is_legacy_score, RUBRIC_NAME  # noqa: E402

ARCHIVE = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")
DRY = "--dry-run" in sys.argv


def retired_stub(old: dict) -> dict:
    """A score block with NO score in it — only the fact that one was retired."""
    return {
        "status": "retired_legacy_score",
        "retired_rubric": (old.get("provenance") or "unknown").split(" —")[0],
        "reason": (
            "Scored by a superseded rubric before the provenance contract existed. "
            "Older rubrics carried known defects (e.g. the dynamics component could "
            "score a flat 10 or crater to 0), and uncalibrated runs used theoretical "
            "anchors rather than the professional reference pack. The number was not "
            "comparable to current scores and has been removed."
        ),
        "action": (
            f"Re-score with the current engine ({RUBRIC_NAME}) before quoting, "
            "displaying or trending: python3 docs/score-metrics/rescore_all.py"
        ),
        "do_not_use": True,
    }


def _rubric_number(name):
    m = re.fullmatch(r"deterministic_rubric_v(\d+)", str(name or ""))
    return int(m.group(1)) if m else None


def newer_than_engine(files):
    """Archived scores from a NEWER rubric than this engine. Any at all means
    this checkout is stale: is_legacy_score() would call every current score
    "legacy" and this script would wipe them. Refuse instead."""
    running = _rubric_number(RUBRIC_NAME)
    newer = []
    for path in files:
        try:
            with open(path) as fh:
                score = (json.load(fh) or {}).get("technical_score") or {}
        except (OSError, ValueError):
            continue
        stored = _rubric_number((score.get("identity") or {}).get("rubric"))
        if running is not None and stored is not None and stored > running:
            newer.append((os.path.basename(path), stored))
    return newer


def main() -> int:
    files = sorted(glob.glob(os.path.join(ARCHIVE, "*_analysis.json")))
    newer = newer_than_engine(files)
    if newer:
        print(f"REFUSING: {len(newer)} archived score(s) come from a newer rubric than this "
              f"engine ({RUBRIC_NAME}), e.g. {newer[0][0]} (v{newer[0][1]}).")
        print("This checkout is stale; retiring now would destroy current scores.")
        print("Fix: git fetch origin main && git merge --ff-only origin/main, then "
              "python3 tools/score_preflight.py, then re-run this script.")
        return 1
    retired, already, current = [], 0, 0
    for path in files:
        with open(path) as fh:
            data = json.load(fh)
        score = data.get("technical_score")
        if not isinstance(score, dict):
            continue
        if score.get("status") == "retired_legacy_score":
            already += 1
            continue
        if not is_legacy_score(score):
            current += 1
            continue
        retired.append((os.path.basename(path), score.get("overall_score_0_to_10"),
                        (score.get("provenance") or "?").split(" —")[0]))
        if not DRY:
            data["technical_score"] = retired_stub(score)
            with open(path, "w") as fh:
                json.dump(data, fh, indent=2)
                fh.write("\n")

    verb = "would retire" if DRY else "retired"
    print(f"{verb} {len(retired)} stale score(s); {already} already retired; "
          f"{current} already current ({RUBRIC_NAME})")
    for name, val, rubric in retired:
        print(f"  - {val}  [{rubric}]  {name}")
    if retired and not DRY:
        print("\nRaw measurements untouched — re-score with rescore_all.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
