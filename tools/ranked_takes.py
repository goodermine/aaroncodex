#!/usr/bin/env python3
"""Rank a singer's takes — honestly, and honouring the learning tag.

A committed, reproducible replacement for ad-hoc ranking one-liners. Two rules
baked in so the list can't mislead:

1. **Lead number per take is the honest one.** Overall for a clean capture;
   capture-fair only when the engine flags the CAPTURE as degraded
   (`confidence_basis.capture_risk_elevated`) — i.e. live pub/tavern takes, not
   a quiet home take. A home recording is a clean/studio capture and leads with
   overall.
2. **Learning takes are not ranked against performance takes.** `take_context`
   (see docs/plans/TAKE_CONTEXT_TAG.md) splits them: performance takes form the
   leaderboard; `learning`/`warmup` takes are listed separately, never head-to-
   head with polished takes. The tag never changes a score — only the grouping.

    python3 tools/ranked_takes.py              # every singer
    python3 tools/ranked_takes.py aaron        # one singer
    python3 tools/ranked_takes.py rilda --best-of   # one row per song (its best)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")
# Longest name FIRST — the regex alternation is ordered, so "aaron" placed
# before "aaron-and-rilda" would swallow the duet into Aaron's solo stats. A
# duet is its own singer, not either half of it: one stem carries two voices,
# so every per-voice measurement in it describes neither of them cleanly.
SINGERS = ("aaron-and-rilda", "aaron-g", "aaron", "rilda", "chris", "leo")

sys.path.insert(0, os.path.join(ROOT, "tools"))
from take_context import read_context, leads_capture_fair  # noqa: E402


def _singer(name: str) -> str | None:
    m = re.match(r"20\d\d-\d\d-\d\d-(" + "|".join(SINGERS) + r")-", name)
    return m.group(1) if m else None


def _song(name: str, singer: str) -> str:
    s = re.sub(r"^20\d\d-\d\d-\d\d-" + re.escape(singer) + r"-", "", name)
    s = re.sub(r"-take-\d+.*$", "", s)
    s = re.sub(r"_analysis\.json$", "", s)
    return s.replace("-", " ").strip().title()


def _lead(ts: dict, analysis: dict):
    """(lead_score, which, overall, capture_fair).

    Lead capture-fair when the take is a degraded capture, else overall. A
    singer's declared `capture` context wins (live -> capture-fair, studio/home
    -> overall); if undeclared, fall back to the engine's `capture_risk_elevated`
    flag, which currently reads False everywhere — so undeclared takes lead
    overall until the capture tag is set at upload.
    """
    ov = ts.get("overall_score_0_to_10")
    cf = ts.get("capture_fair_score_0_to_10")
    declared = leads_capture_fair(analysis)
    if declared is None:
        declared = bool((ts.get("confidence_basis") or {}).get("capture_risk_elevated"))
    if declared:
        return cf, "capture-fair", ov, cf
    return ov, "overall", ov, cf


def collect(singer_filter: str | None):
    rows = []
    superseded_count = {}
    for p in sorted(glob.glob(os.path.join(ARCHIVE, "*_analysis.json"))):
        name = os.path.basename(p).replace("_analysis.json", "")
        singer = _singer(name)
        if not singer or (singer_filter and singer != singer_filter):
            continue
        try:
            d = json.load(open(p))
        except (OSError, json.JSONDecodeError):
            continue
        ctx = read_context(d)
        # Retired duplicates are kept on disk but never ranked or averaged.
        if ctx["superseded"]:
            superseded_count[singer] = superseded_count.get(singer, 0) + 1
            continue
        ts = d.get("technical_score", {})
        lead, which, ov, cf = _lead(ts, d)
        if lead is None:
            continue
        rows.append({
            "singer": singer, "song": _song(name, singer), "name": name,
            "lead": lead, "which": which, "overall": ov, "capture_fair": cf,
            "intent": ctx["intent"], "milestone": ctx["milestone"], "note": ctx["note"],
        })
    return rows, superseded_count


def _print_block(title: str, rows: list, best_of: bool):
    if best_of:
        best = {}
        for r in rows:
            b = best.get(r["song"])
            if b is None or r["lead"] > b["lead"]:
                best[r["song"]] = r
        rows = list(best.values())
    rows = sorted(rows, key=lambda r: (r["lead"], r["overall"] or -1), reverse=True)
    if not rows:
        return
    leads = [r["lead"] for r in rows]
    print(f"\n{title} — {len(rows)} {'songs' if best_of else 'takes'} · "
          f"mean {sum(leads)/len(leads):.2f} · best {max(leads)}")
    for i, r in enumerate(rows, 1):
        star = " *milestone:%s" % r["milestone"] if r["milestone"] else ""
        note = f'  — {r["note"]}' if r["note"] else ""
        tag = {"overall": "ov", "capture-fair": "cf"}.get(r["which"], r["which"])
        print(f'  {i:>3}. {r["lead"]:>4} {tag}  {r["song"]}{star}{note}')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("singer", nargs="?", help="aaron / aaron-g / rilda / chris / leo")
    ap.add_argument("--best-of", action="store_true", help="one row per song (its best take)")
    a = ap.parse_args()
    rows, superseded = collect(a.singer)
    if not rows:
        print("no takes found")
        return 1
    for singer in SINGERS:
        srows = [r for r in rows if r["singer"] == singer]
        if not srows:
            continue
        perf = [r for r in srows if r["intent"] == "performance"]
        learn = [r for r in srows if r["intent"] != "performance"]
        print(f"\n===== {singer.upper()} =====")
        _print_block("Performance", perf, a.best_of)
        if learn:
            _print_block("Learning / warm-up (not ranked against performance)", learn, False)
        retired = superseded.get(singer, 0)
        if retired:
            print(f"\n  ({retired} retired duplicate take(s) kept on disk but not ranked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
