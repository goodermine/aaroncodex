"""Phrase-ending fall rate against the ORIGINAL RECORDING of the same song.

Scoring sag against one pooled professional median makes the number partly a
measure of repertoire: across the reference pack the rate runs 10.3% (Kryptonite)
to 55.1% (Livin' On A Prayer). The delta against the same song reorders the
conclusions — Aaron's Kryptonite at 53.9% against an original at 10.3% is a far
bigger departure than his Livin' On A Prayer at 59.2% against an original at
55.1%, though the absolute scores say the opposite.

This is a RAW measure, so it must never be gated on provenance and must never
become a /10.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import analyse_song as A  # noqa: E402


def _results(pct, n_phrases=40, sags=(300.0, 400.0, 500.0), phrase_s=3.0):
    return {
        "breath": {"pct_sagging_endings": pct, "n_phrases_measured": n_phrases,
                   "sagging_phrase_ends": [{"sag_cents": s} for s in sags]},
        "phrasing": {"median_phrase_s": phrase_s},
    }


def test_reports_the_delta_against_the_same_songs_original():
    r = A.breath_vs_reference(_results(67.2), _results(30.1))
    assert r["available"] is True
    assert r["delta_percentage_points"] == 37.1
    assert r["take_pct_sagging_endings"] == 67.2
    assert r["original_pct_sagging_endings"] == 30.1
    assert "substantially more" in r["read"]


def test_matching_the_original_is_not_reported_as_a_weakness():
    """Livin' On A Prayer: 59.2% against an original at 55.1%. A poor absolute
    figure, but the song simply has falling phrase ends."""
    r = A.breath_vs_reference(_results(59.2), _results(55.1))
    assert r["delta_percentage_points"] == 4.1
    assert "matches the original" in r["read"]


def test_holding_endings_better_than_the_original_reads_as_such():
    r = A.breath_vs_reference(_results(20.0), _results(45.0))
    assert r["delta_percentage_points"] == -25.0
    assert "MORE than the original" in r["read"]


def test_it_is_never_a_score_and_carries_the_style_caveat():
    """Rule 1: only compute_technical_score() may produce a /10. And the measure
    counts downward pitch releases, not breath failure — professionals' flagged
    endings drop hundreds of cents too, so the payload must say so."""
    r = A.breath_vs_reference(_results(67.2), _results(30.1))
    for key in r:
        assert "score" not in key, f"{key} looks like a score; this is a raw measure"
    assert "0" not in str(r.get("read", ""))
    note = r["note"].lower()
    assert "not a score" in note
    assert "fall-off" in note or "phrasing" in note


def test_differing_phrase_lengths_are_flagged_not_silently_compared():
    """The tail window is a fixed 0.5 s, so a 0.6 s-phrase song and a 6 s-phrase
    song are not measuring the same quantity."""
    same = A.breath_vs_reference(_results(50.0, phrase_s=3.0), _results(40.0, phrase_s=3.4))
    assert same["comparable_phrase_lengths"] is True
    assert "CAUTION" not in same["note"]

    differing = A.breath_vs_reference(_results(50.0, phrase_s=0.6), _results(40.0, phrase_s=5.0))
    assert differing["comparable_phrase_lengths"] is False
    assert "CAUTION" in differing["note"]


def test_missing_measurement_on_either_side_degrades_cleanly():
    """22 archived takes predate analyse_breath. Those must report why rather
    than silently omitting the comparison."""
    no_take = A.breath_vs_reference({}, _results(30.1))
    assert no_take["available"] is False and "take" in no_take["reason"]
    no_ref = A.breath_vs_reference(_results(67.2), {})
    assert no_ref["available"] is False and "original" in no_ref["reason"]


def test_adding_this_did_not_change_the_scoring_fingerprint():
    """A reporting addition must not retire every stored score. The fingerprint
    hashes the scoring functions only — if this assertion ever fails, the change
    touched the rubric and needs the full retire/re-score cycle."""
    import json
    path = os.path.dirname(os.path.abspath(__file__))
    while path != os.path.dirname(path) and not os.path.isfile(os.path.join(path, "CLAUDE.md")):
        path = os.path.dirname(path)          # walk up, don't count dirnames
    pinned = json.load(open(os.path.join(path, "docs/score-metrics/SCORE_CONTRACT.json")))
    live = A.score_identity({}, A.load_calibration(A.DEFAULT_CALIBRATION_PATH))
    assert live["rubric_fingerprint"] == pinned["rubric_fingerprint"]
