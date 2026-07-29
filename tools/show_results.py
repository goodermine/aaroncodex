#!/usr/bin/env python3
"""Print the FULL analysis report for a take — the deliverable rule 8 requires.

An analysis is NOT done until the singer has been GIVEN the results (CLAUDE.md
rule 8). Committing the JSON and pushing the branch is plumbing; the deliverable
is the actual report in the singer's hands. This renders that report from a
stored analysis so the last step of any analysis run is one command whose output
you paste straight back to the singer — there is no excuse to hand over a commit
hash instead of the result.

    python3 tools/show_results.py <analysis.json>
    python3 tools/show_results.py two-strong-hearts      # substring of the take name

It renders via the one source of truth, `report_builder.render_full_results_text`
(rule 6) — the exact text the web page shows. It reads a stored analysis and
computes no score, so it never touches the scoring path.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEWER = os.path.join(ROOT, "voxanalysis/vox-analysis/viewer")
ARCHIVE = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")


def resolve(arg: str) -> str | None:
    """A file path, or a substring matched against archived analyses."""
    if os.path.isfile(arg):
        return arg
    hits = sorted(glob.glob(os.path.join(ARCHIVE, f"*{arg}*_analysis.json")))
    if len(hits) == 1:
        return hits[0]
    if not hits:
        print(f"no analysis matches {arg!r} in {os.path.relpath(ARCHIVE, ROOT)}/",
              file=sys.stderr)
        return None
    print(f"{arg!r} matches {len(hits)} analyses — be more specific:", file=sys.stderr)
    for h in hits:
        print("  " + os.path.basename(h), file=sys.stderr)
    return None


def render(path: str) -> str:
    raw = json.load(open(path))
    sys.path.insert(0, VIEWER)
    import report_builder as R

    rep = R.build_v2_report(raw)
    # signature has varied; the current one takes (report, raw_result)
    for call in (lambda: R.render_full_results_text(rep, raw),
                 lambda: R.render_full_results_text(rep),
                 lambda: R.render_full_results_text(raw)):
        try:
            return call()
        except TypeError:
            continue
    raise RuntimeError("render_full_results_text: no known signature matched")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("take", help="analysis JSON path, or a substring of the take name")
    a = ap.parse_args()
    path = resolve(a.take)
    if not path:
        return 1
    try:
        text = render(path)
    except Exception as exc:  # noqa: BLE001
        # Rule 8: if the full report cannot be rendered, say so loudly and still
        # give the singer the headline + component table — never report "done"
        # with nothing readable.
        print(f"COULD NOT RENDER FULL REPORT: {type(exc).__name__}: {exc}\n",
              file=sys.stderr)
        d = json.load(open(path)).get("technical_score", {})
        print("Fallback — headline + components (still owe the singer the full report):")
        print(f"  overall     : {d.get('overall_score_0_to_10')}/10")
        print(f"  capture-fair: {d.get('capture_fair_score_0_to_10')}/10")
        print(f"  confidence  : {d.get('confidence')}")
        for k, v in (d.get("components") or {}).items():
            if isinstance(v, dict):
                print(f"    {k:22} {v.get('score')}")
        return 2
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
