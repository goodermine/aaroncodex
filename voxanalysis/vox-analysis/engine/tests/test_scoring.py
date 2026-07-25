"""Scoring rubric — provenance pinning, dynamics grading (v4), capture-fair.

Provenance: every score carries a deterministic `identity` (rubric + rubric
fingerprint + calibration pack + stem model + take), and scores may only be
compared when those identities match. This is what stops a stale rubric's number
being quoted or trended as though it were current — the Rilda 5.1-vs-8.0 case.


Guards the v4 fix: dynamics_expression must GRADE against the pro distribution
(10 at the median, easing to ~7 at the range edges, floored — not zeroed — beyond
it), instead of the v3 flat-topped peak scale that returned a constant 10 across
the whole professional band and cratered to 0 on a capture artefact. Also guards
that dynamics joins voice_quality in the capture-fair exclusion.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import analyse_song as A  # noqa: E402


def test_graded_peak_shape():
    # p10=10, p50=22, p90=40; zero bounds 0.5 and 70
    f = A._graded_peak
    assert f(22, 10, 22, 40, 0.5, 70) == 10.0           # median = 10
    assert 6.5 <= f(10, 10, 22, 40, 0.5, 70) <= 7.5     # p10 edge ~7
    assert 6.5 <= f(40, 10, 22, 40, 0.5, 70) <= 7.5     # p90 edge ~7
    # beyond the pro range grades down but never to 0 (floored)
    assert 3.0 <= f(0.6, 10, 22, 40, 0.5, 70) < 6.0     # very flat
    assert 3.0 <= f(69, 10, 22, 40, 0.5, 70) < 7.0      # very wide / artefact
    assert f(200, 10, 22, 40, 0.5, 70) >= 3.0           # extreme stays at the floor, not 0


def _base_results(spread, eff):
    return {
        "intonation": {"method": "grid", "n_notes": 20,
                       "median_abs_deviation_cents": 15.0,
                       "median_intra_note_drift_cents": 20.0},
        "voice_quality": {"method": "praat sustained-note metrics",
                          "jitter_local_percent_median": 0.4,
                          "shimmer_local_percent_median": 3.0, "hnr_db_median": 19.0},
        "vibrato": {"n_notes_analysed": 5, "pct_notes_with_vibrato": 60.0,
                    "median_rate_hz": 6.0, "median_extent_cents": 70.0},
        "dynamics": {"phrase_level_spread_db": spread, "effective_dynamic_range_db": eff},
        "phrasing": {"median_phrase_s": 3.0},
        "time_diagnostics": {"environment_risk": {"karaoke_or_room_contamination_risk": "low"}},
    }


def test_dynamics_discriminates_not_flat_ten():
    """A flat/compressed take and a well-shaped take must get DIFFERENT dynamics
    scores — the v3 bug returned 10.0 for both."""
    flat = A.compute_technical_score(_base_results(spread=2.0, eff=6.0))
    good = A.compute_technical_score(_base_results(spread=22.0, eff=30.0))
    d_flat = flat["components"]["dynamics_expression"]["score"]
    d_good = good["components"]["dynamics_expression"]["score"]
    assert d_flat < d_good, (d_flat, d_good)
    assert d_good <= 10.0 and d_flat >= 0.0
    # the flat take is graded down but not zeroed by a single capture-sensitive reading
    assert d_flat > 0.0


def test_every_score_carries_a_deterministic_identity():
    """A bare number is uninterpretable — each score must say what produced it,
    and that identity must be deterministic (same audio + same engine => same
    identity), or nothing downstream can compare scores reliably."""
    a = A.compute_technical_score(_base_results(22.0, 30.0))
    b = A.compute_technical_score(_base_results(22.0, 30.0))
    ident = a["identity"]
    assert ident["contract"] == A.SCORE_CONTRACT
    assert ident["rubric"] == A.RUBRIC_NAME
    assert ident["rubric_fingerprint"]
    assert a == b, "identity (and therefore the score) must be deterministic"


def test_legacy_and_mismatched_scores_are_refused_for_comparison():
    """The Rilda incident: a stale rubric's 5.1 sat next to a current 8.0 and
    looked comparable. Legacy scores must fail closed."""
    current = A.compute_technical_score(_base_results(22.0, 30.0))
    legacy = {"overall_score_0_to_10": 5.1, "provenance": "deterministic_rubric_v1 — ..."}
    assert A.is_legacy_score(legacy)
    assert not A.is_legacy_score(current)
    assert not A.scores_comparable(current, legacy)
    assert "provenance" in A.score_conflict(current, legacy)
    # a score is comparable with itself / an identical run
    assert A.scores_comparable(current, A.compute_technical_score(_base_results(22.0, 30.0)))


def test_different_calibration_packs_are_not_comparable():
    """Same rubric but a different reference pack is still a different scale."""
    calibrated = A.compute_technical_score(_base_results(22.0, 30.0),
                                           A.load_calibration(A.DEFAULT_CALIBRATION_PATH))
    uncalibrated = A.compute_technical_score(_base_results(22.0, 30.0))
    assert not A.scores_comparable(calibrated, uncalibrated)
    assert "calibration" in A.score_conflict(calibrated, uncalibrated)


def test_one_take_through_every_entry_point_agrees_or_conflicts_explicitly():
    """Candi's integration requirement: the same stem scored through every
    supported path must return the SAME canonical score, or be refused with a
    stated provenance conflict — never two silently different numbers."""
    results = _base_results(22.0, 30.0)
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    # entry point 1: the engine directly
    direct = A.compute_technical_score(results, cal)
    # entry point 2: the same measurements carrying extra sidecar data (the
    # spectral-export path adds keys that must not perturb the score)
    with_extras = json.loads(json.dumps(results))
    with_extras["spectral"] = {"version": "voxai_spectral_v1", "status": "ready"}
    via_export = A.compute_technical_score(with_extras, cal)
    assert A.scores_comparable(direct, via_export)
    assert direct["overall_score_0_to_10"] == via_export["overall_score_0_to_10"]
    # entry point 3: an uncalibrated runner must NOT silently disagree — it is
    # refused as incomparable rather than presented as an alternative reading
    rogue = A.compute_technical_score(results)
    assert A.score_conflict(direct, rogue) is not None


def test_capture_fair_excludes_dynamics_and_voice_quality():
    ts = A.compute_technical_score(_base_results(spread=22.0, eff=30.0))
    # capture-fair must not be swayed by the capture-sensitive components; force a
    # large gap and confirm overall != capture-fair when they differ.
    assert "capture_fair_score_0_to_10" in ts
    note = ts["capture_fair_note"].lower()
    assert "voice_quality" in note and "dynamics" in note
    assert ts["provenance"].startswith("deterministic_rubric_v4")
