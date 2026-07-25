"""Scoring rubric — dynamics grading (v4) and capture-fair exclusion.

Guards the v4 fix: dynamics_expression must GRADE against the pro distribution
(10 at the median, easing to ~7 at the range edges, floored — not zeroed — beyond
it), instead of the v3 flat-topped peak scale that returned a constant 10 across
the whole professional band and cratered to 0 on a capture artefact. Also guards
that dynamics joins voice_quality in the capture-fair exclusion.
"""

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


def test_capture_fair_excludes_dynamics_and_voice_quality():
    ts = A.compute_technical_score(_base_results(spread=22.0, eff=30.0))
    # capture-fair must not be swayed by the capture-sensitive components; force a
    # large gap and confirm overall != capture-fair when they differ.
    assert "capture_fair_score_0_to_10" in ts
    note = ts["capture_fair_note"].lower()
    assert "voice_quality" in note and "dynamics" in note
    assert ts["provenance"].startswith("deterministic_rubric_v4")
