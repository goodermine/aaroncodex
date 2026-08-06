#!/usr/bin/env python3
"""Score-trend data layer for the progress dashboard (future-idea F7).

Pure reporting. Reads the analysis JSONs Candi already produced and emits one
structured JSON describing a singer's score progression — per song and overall —
plus archetype shifts and capture method. It renders that JSON into a
self-contained HTML dashboard.

    python3 tools/score_trends.py                 # aaron -> docs/score-metrics/score-trends.{json,html}
    python3 tools/score_trends.py --singer rilda
    python3 tools/score_trends.py --json-only     # data layer only, no HTML

WHAT THIS TOOL IS NOT
---------------------
It never produces a `/10`. Every number here is *read* from a stored analysis,
exactly as the engine wrote it — there is no scoring, rounding, adjusting, or
"sanity-checking" (CLAUDE.md rule 1). It reuses the same provenance gate as
`voxanalysis/vox-analysis/engine/tools/progress_report.py`: a score may only be
trended against scores from the same rubric + calibration pack. A legacy score
(which reads ~2.5-3 points too harsh) is dropped from the score trends and
flagged "re-score" — never silently mixed in (rule 3). Raw metrics (cents, dB,
%) are always comparable, so they are kept for every take.

The lead number per take follows the same honesty rule the rest of the repo
uses (see ranked_takes.py): capture-fair when the capture is degraded, overall
otherwise.
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
CONTRACT = os.path.join(ROOT, "docs/score-metrics/SCORE_CONTRACT.json")
OUT_JSON = os.path.join(ROOT, "docs/score-metrics/score-trends.json")
OUT_HTML = os.path.join(ROOT, "docs/score-metrics/score-trends.html")

sys.path.insert(0, os.path.join(ROOT, "tools"))
from take_context import read_context  # noqa: E402
from ranked_takes import _singer, _song, _lead  # noqa: E402

# Same provenance predicate progress_report.py uses — imported from the engine
# so there is exactly one definition of "is this score legacy?" in the repo.
_ENGINE = os.path.join(ROOT, "voxanalysis/vox-analysis/engine")
sys.path.insert(0, _ENGINE)
from analyse_song import is_legacy_score, score_conflict  # noqa: E402

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")

# Capture-location / session suffixes baked into filenames. They tag WHERE a
# take was recorded, not WHICH song it is — a tavern take and a studio take of
# the same song must share one card (the take's own capture-fair-vs-overall lead
# already carries the venue signal). Longest first so multi-word venues match
# before their prefixes. These are the Brisbane venues from memory 006 plus the
# home "new studio" tag.
_VENUE_SUFFIXES = (
    "captain cook tavern", "mango hill tavern", "mango hill",
    "bramble bay", "new studio",
)

# Genuine spelling/annotation variants of one song, folded to a single identity.
# Keys and values are the title-cased, apostrophe-cleaned display strings.
_SONG_ALIASES = {
    "Do Wah Diddy Diddy": "Do Wah Diddy",
    "The Letter Joe Cocker": "The Letter",
    "Lets Stay Together": "Let's Stay Together",
    "Let S Stay Together": "Let's Stay Together",
}


def _canon_song(title: str) -> str:
    """Fold capture-location suffixes and spelling variants to one song name.

    Without this, `Pressure Down` and `Pressure Down Captain Cook Tavern` count
    as two songs and split one song's history across two cards.
    """
    # Repair apostrophes mangled to " S "/" T " by the slug pipeline
    # ("Don T Be Cruel" -> "Don't Be Cruel", "She S Not There" -> "She's...").
    t = re.sub(r"\bDon T\b", "Don't", title)
    t = re.sub(r"\b(\w+) S\b", r"\1's", t)
    low = t.lower()
    for suf in _VENUE_SUFFIXES:
        if low.endswith(" " + suf):
            t = t[: len(t) - len(suf) - 1].rstrip()
            break
    return _SONG_ALIASES.get(t, t)

# Anchor line every score surface in the repo carries (rule 5).
ANCHOR = ("Scale calibrated to 50 professional reference vocals — "
          "10 = a typical pro. A 7 is a good amateur result, not a failure.")


def _archetype(analysis: dict) -> str | None:
    a = analysis.get("archetype")
    if isinstance(a, str):
        return a
    if isinstance(a, dict):
        return a.get("label") or a.get("archetype")
    return None


def _trendable(analysis: dict) -> bool:
    """True when this take's score may sit on a trend line with the others.

    Mirrors progress_report.score_is_trendable: a legacy-rubric score is not
    comparable to a current one and is excluded from the score trends.
    """
    score = (analysis or {}).get("technical_score") or {}
    if is_legacy_score(score):
        return False
    return True


def collect(singer: str) -> list[dict]:
    takes = []
    for p in sorted(glob.glob(os.path.join(ARCHIVE, "*_analysis.json"))):
        name = os.path.basename(p).replace("_analysis.json", "")
        if _singer(name) != singer:
            continue
        m = DATE_RE.match(name)
        if not m:
            continue
        try:
            d = json.load(open(p))
        except (OSError, json.JSONDecodeError):
            continue
        ctx = read_context(d)
        if ctx["superseded"]:
            continue  # retired duplicates are kept on disk but never trended
        ts = d.get("technical_score", {})
        lead, which, ov, cf = _lead(ts, d)
        if lead is None:
            continue
        takes.append({
            "name": name,
            "date": m.group(1),
            "analysed_at": d.get("analysed_at", ""),
            "song": _canon_song(_song(name, singer)),
            "overall": ov,
            "capture_fair": cf,
            "lead": lead,
            "which": which,
            "archetype": _archetype(d),
            "intent": ctx["intent"],
            "milestone": ctx["milestone"],
            "trendable": _trendable(d),
        })
    takes.sort(key=lambda t: (t["date"], t["analysed_at"], t["name"]))
    return takes


def _trend_word(first: float, last: float) -> str:
    delta = round(last - first, 2)
    if abs(delta) < 0.05:
        return "steady"
    return "improving" if delta > 0 else "slipping"


def build(singer: str) -> dict:
    contract = json.load(open(CONTRACT))
    takes = collect(singer)
    perf = [t for t in takes if t["intent"] == "performance"]

    # Per-song grouping — one card per song, chronological takes inside.
    songs: dict[str, list[dict]] = {}
    for t in perf:
        songs.setdefault(t["song"], []).append(t)

    song_blocks = []
    for song, ts in songs.items():
        trendable = [t for t in ts if t["trendable"]]
        arche_seq = [(t["date"], t["archetype"]) for t in ts if t["archetype"]]
        shifts = []
        for i in range(1, len(arche_seq)):
            if arche_seq[i][1] != arche_seq[i - 1][1]:
                shifts.append({
                    "date": arche_seq[i][0],
                    "from": arche_seq[i - 1][1],
                    "to": arche_seq[i][1],
                })
        block = {
            "song": song,
            "n_takes": len(ts),
            "best_lead": max((t["lead"] for t in ts), default=None),
            "latest": ts[-1],
            "archetype_latest": arche_seq[-1][1] if arche_seq else None,
            "archetype_shifts": shifts,
            "takes": ts,
            "n_excluded": len(ts) - len(trendable),
        }
        if len(trendable) >= 2:
            block["trend"] = _trend_word(trendable[0]["lead"], trendable[-1]["lead"])
        else:
            block["trend"] = None  # not enough comparable scores to draw a line
        song_blocks.append(block)

    # Best song first, then by take count — most-worked songs surface.
    song_blocks.sort(key=lambda b: (b["best_lead"] or -1, b["n_takes"]), reverse=True)

    best = max(perf, key=lambda t: t["lead"], default=None)
    leads = [t["lead"] for t in perf]
    excluded = [t for t in takes if not t["trendable"]]

    return {
        "generated_from": "voxanalysis/archive/scratch-analyses",
        "singer": singer,
        "contract": contract,
        "anchor": ANCHOR,
        "summary": {
            "n_takes": len(takes),
            "n_performance": len(perf),
            "n_songs": len(song_blocks),
            "n_learning": len(takes) - len(perf),
            "mean_lead": round(sum(leads) / len(leads), 2) if leads else None,
            "best": best,
            "date_first": takes[0]["date"] if takes else None,
            "date_latest": takes[-1]["date"] if takes else None,
            "n_excluded_legacy": len(excluded),
        },
        "songs": song_blocks,
        "excluded_legacy": [
            {"name": t["name"], "date": t["date"], "song": t["song"]}
            for t in excluded
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--singer", default="aaron")
    ap.add_argument("--json-only", action="store_true",
                    help="write the data JSON but not the HTML dashboard")
    ap.add_argument("--stdout", action="store_true",
                    help="print the data JSON to stdout instead of writing files")
    a = ap.parse_args()

    data = build(a.singer)
    if a.stdout:
        print(json.dumps(data, indent=2))
        return 0

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {os.path.relpath(OUT_JSON, ROOT)} "
          f"({data['summary']['n_performance']} performance takes, "
          f"{data['summary']['n_songs']} songs)")

    if not a.json_only:
        from score_trends_html import render  # local module, kept beside this one
        html = render(data)
        with open(OUT_HTML, "w") as f:
            f.write(html)
        print(f"wrote {os.path.relpath(OUT_HTML, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
