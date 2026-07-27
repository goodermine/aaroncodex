"""Two singers must never be merged into one set of scores.

Aaron and Aaron G are different people. rescore_all.py classified takes by
substring, so every `aaron-g-*` take was filed under Aaron — and Aaron G's
Vienna was reported as Aaron's best result. Correcting it to match "aaron-g"
first then broke the other way, filing `aaron-goodbye-s-been-good-to-you` under
Aaron G, because "aaron-g" is a prefix of "aaron-goodbye".

Neither naive approach works. Matching is on a token boundary, longest name
first, and the archive's own `artist_name` field is the ground truth to check
against.
"""

from __future__ import annotations

import glob
import importlib.util
import json
import os
import sys


def _repo_root(start: str) -> str:
    path = start
    while path != os.path.dirname(path):
        if os.path.isfile(os.path.join(path, "CLAUDE.md")):
            return path
        path = os.path.dirname(path)
    raise RuntimeError(f"repo root not found above {start}")


ROOT = _repo_root(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")

EXPECTED_ARTIST = {"aaron": "Aaron", "aaron-g": "Aaron G", "rilda": "Rilda",
                   "chris": "Chris", "leo": "Leo"}


def _rescore_module():
    """Import rescore_all's helpers without executing its main body."""
    path = os.path.join(ROOT, "docs/score-metrics/rescore_all.py")
    src = open(path).read()
    cut = src.index("def score_row(")          # everything above is pure helpers
    # __file__ must be supplied: the script derives ROOT from it, and exec()
    # into a bare dict does not provide one.
    ns: dict = {"__file__": path, "__name__": "rescore_all_helpers"}
    sys.path.insert(0, os.path.join(ROOT, "voxanalysis/vox-analysis/engine"))
    cwd = os.getcwd()
    os.chdir(os.path.join(ROOT, "voxanalysis/vox-analysis/engine"))  # calibration path is relative
    try:
        exec(compile(src[:cut], path, "exec"), ns)
    finally:
        os.chdir(cwd)
    return ns


def test_aaron_g_is_not_filed_under_aaron():
    ns = _rescore_module()
    singer = ns["singer"]
    assert singer("2026-07-11-aaron-g-vienna-take-001") == "aaron-g"
    assert singer("2026-07-11-aaron-g-1973-take-001") == "aaron-g"
    assert singer("2026-07-11-aaron-g-if-you-could-read-my-mind-take-001") == "aaron-g"


def test_a_song_starting_with_g_is_not_mistaken_for_aaron_g():
    """"aaron-goodbye-s-been-good-to-you" begins with the characters "aaron-g".
    Only the token boundary separates it from "aaron-g-vienna"."""
    ns = _rescore_module()
    assert ns["singer"]("2026-07-12-aaron-goodbye-s-been-good-to-you-take-001-normalized") == "aaron"


def test_classification_matches_the_archives_own_artist_name():
    """The engine records artist_name at analysis time. Filename classification
    must agree with it for every archived take — that is the ground truth, and
    disagreeing means someone's scores are being reported under another name."""
    ns = _rescore_module()
    singer, is_take = ns["singer"], ns["is_take"]
    checked, mismatches = 0, []
    for path in sorted(glob.glob(os.path.join(ARCHIVE, "*_analysis.json"))):
        name = os.path.basename(path).replace("_analysis.json", "")
        if not is_take(name):
            continue
        artist = json.load(open(path)).get("artist_name")
        expected = EXPECTED_ARTIST.get(singer(name))
        checked += 1
        if expected is not None and artist != expected:
            mismatches.append(f"{name}: file says {artist!r}, classified {singer(name)!r}")
    assert checked > 0, "no takes found to check"
    assert not mismatches, "singer misclassification:\n  " + "\n  ".join(mismatches)


def test_leading_name_and_dated_name_both_classify():
    ns = _rescore_module()
    singer = ns["singer"]
    assert singer("aaron-danger-zone-home-2026-07-11-normalized") == "aaron"
    assert singer("leo-chasin-that-neon-rainbow-2026-07-11-normalized") == "leo"
    assert singer("tina-turner-lets-stay-together-reference") == "reference"
