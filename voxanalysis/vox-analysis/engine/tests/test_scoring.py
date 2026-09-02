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


def test_visual_severity_tolerates_unmeasurable_section_drift():
    """Short-note sections now report drift=None; diagnostics must still render."""
    assert A._severity_color(10.0, None) == "#2a9d3a"
    assert A._severity_color(A.TROUBLE_DEV_CENTS + 1, None) == "#d62728"


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
        # v5: phrase-ending sag. Pro pack median is 34.85% of endings.
        "breath": {"n_phrases_measured": 30, "n_sagging_endings": 10,
                   "pct_sagging_endings": 33.3},
        "time_diagnostics": {"environment_risk": {"karaoke_or_room_contamination_risk": "low"}},
    }


def _with_sag(pct, n_phrases=30):
    r = _base_results(22.0, 30.0)
    r["breath"] = {"n_phrases_measured": n_phrases,
                   "n_sagging_endings": round(n_phrases * pct / 100),
                   "pct_sagging_endings": pct}
    return r


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
    # Derived, not spelled out: a hardcoded "v4" here passed straight through a
    # rubric bump in the engine's own provenance string without anyone noticing.
    assert ts["provenance"].startswith(A.RUBRIC_NAME)


def test_breath_support_is_scored_and_discriminates():
    """v5: phrase-ending sag was measured from the start and fed nothing. A take
    that holds its phrase endings must beat one that sags on most of them."""
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    def bs(pct):
        return A.compute_technical_score(_with_sag(pct), cal)["components"]["breath_support"]
    # The pro median is read from the live calibration pack — it MOVES when the
    # pack is rebuilt (it shifted with the RoFormer re-separation), so the test
    # derives it rather than hardcoding a number that goes stale. Matching the
    # median or beating it earns 10 (10 anchored at p50, then clipped); the
    # discrimination is all on the worse-than-median side.
    median_sag = A._calib_metric(cal, "breath_pct_sagging_endings")["p50"]
    at_median, better, worse, saggy = bs(median_sag), bs(median_sag * 0.4), \
        bs(median_sag + 15), bs(median_sag + 40)
    assert at_median["score"] == 10.0 and better["score"] == 10.0
    assert 10.0 > worse["score"] > saggy["score"], (worse["score"], saggy["score"])
    assert saggy["score"] < 5.0
    assert "phrase endings" in at_median["input"]


def test_breath_support_counts_inside_capture_fair():
    """The whole point of the component: air running out is the singer, not the
    room. If it were treated as capture-sensitive, a phone take would stop being
    scored on the fault that actually limits it."""
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    solid = A.compute_technical_score(_with_sag(12.0), cal)
    saggy = A.compute_technical_score(_with_sag(75.0), cal)
    assert solid["capture_fair_score_0_to_10"] > saggy["capture_fair_score_0_to_10"]
    assert solid["components"]["breath_support"]["capture_sensitive"] is False


def test_breath_support_is_dropped_when_too_few_phrases():
    """A "% of endings that sag" over 3 phrases is noise. Better to drop the
    component (weights renormalise) than publish a number off two endings."""
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    ts = A.compute_technical_score(_with_sag(80.0, n_phrases=3), cal)
    assert "breath_support" not in ts["components"]
    assert ts["coverage"] == "partial"
    assert "breath_support" in ts["components_unscored"]


def test_partial_coverage_is_reported_but_is_not_a_provenance_conflict():
    """Analyses made before analyse_breath() existed have no sag data, so they
    score on six components while a current take scores on seven. That must be
    VISIBLE — a renormalised overall otherwise looks complete. It is deliberately
    not a hard conflict: the full-vs-partial gap is ~0.25 points at most, so
    refusing to compare would cost more than the distortion it avoids."""
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    full = A.compute_technical_score(_base_results(22.0, 30.0), cal)
    old = _base_results(22.0, 30.0)
    del old["breath"]                                    # a pre-breath analysis
    partial = A.compute_technical_score(old, cal)

    assert full["coverage"] == "full"
    assert full["coverage_note"] is None
    assert partial["coverage"] == "partial"
    assert partial["components_unscored"] == ["breath_support"]
    assert "breath_support" in partial["coverage_note"]
    assert A.score_conflict(full, partial) is None        # comparable, with the caveat stated
    assert set(full["components_scored"]) == set(A.ALL_COMPONENTS)


def test_take_vs_reference_comparison_withholds_on_provenance_conflict():
    """pitch_track builds a take-vs-original comparison. Pairing a stale-rubric
    score with a current one invents a gap that isn't there, so the score pair is
    withheld (raw contour measures still reported) with the reason stated."""
    import pitch_track  # noqa: F401  (import guard: the helper must exist)
    current = A.compute_technical_score(_base_results(22.0, 30.0),
                                        A.load_calibration(A.DEFAULT_CALIBRATION_PATH))
    legacy = {"overall_score_0_to_10": 5.1, "provenance": "deterministic_rubric_v1 — x"}
    assert A.score_conflict(current, legacy) is not None
    assert A.score_conflict(current, current) is None


def test_progress_trend_drops_non_comparable_scores():
    """A stale score must never be trended against a current one — that fakes
    progress. Raw metrics stay comparable and are unaffected."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
    from progress_report import score_is_trendable
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    current = {"technical_score": A.compute_technical_score(_base_results(22.0, 30.0), cal)}
    retired = {"technical_score": {"status": "retired_legacy_score", "do_not_use": True}}
    legacy = {"technical_score": {"overall_score_0_to_10": 5.1,
                                  "provenance": "deterministic_rubric_v1 — x"}}
    assert score_is_trendable(current)
    assert not score_is_trendable(retired)
    assert not score_is_trendable(legacy)


def test_scores_from_different_separators_are_not_comparable():
    """The separation model is part of what produced a measurement. Measured on
    Aaron's archive, the same song under MDX-NET vs Mel-Band RoFormer moves
    phrase-sag by up to 29 points in both directions — the size of the effects
    being diagnosed. score_identity always recorded stem_model; nothing checked
    it, so a licence-driven separator swap silently made every old take look
    comparable with every new one."""
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    old = _base_results(22.0, 30.0)
    old["analysis_input_file"] = "take_(Vocals)_UVR_MDXNET_Main.flac"
    new = _base_results(22.0, 30.0)
    new["analysis_input_file"] = "take_(vocals)_vocals_mel_band_roformer.flac"

    a = A.compute_technical_score(old, cal)
    b = A.compute_technical_score(new, cal)
    assert a["identity"]["stem_model"] == "UVR_MDXNET_Main"
    assert b["identity"]["stem_model"] == "RoFormer"
    conflict = A.score_conflict(a, b)
    assert conflict is not None and "separated by different models" in conflict
    assert not A.scores_comparable(a, b)
    # ...and the same separator on both sides still compares fine
    assert A.score_conflict(a, A.compute_technical_score(old, cal)) is None


# ---------------------------------------------------------------------------
# ENTRY ACCURACY — the diagnostic that must never become a score.
# ---------------------------------------------------------------------------

def _onset_take(pct_clean=24.2, pct_scooped=44.6, pct_overshot=29.2, n=130):
    return {"onsets": {"n_onsets": n, "pct_clean": pct_clean,
                       "pct_scooped": pct_scooped, "pct_overshot": pct_overshot,
                       "median_scoop_depth_cents": -98.6,
                       "method": "first 0.25 s of each sustained note vs its settled centre"}}


def test_entry_accuracy_is_never_a_score():
    """An onset_accuracy COMPONENT was built and rejected in Aug 2026 for making
    agreement with the singer's ear worse. The diagnostic that replaced it must
    carry no /10 and must never appear among the scored components, because a
    second /10 beside the real one is the exact failure CLAUDE.md rule 1 exists
    to prevent."""
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    ea = A.compute_entry_accuracy(_onset_take(), cal)
    assert ea is not None
    assert ea["is_score"] is False
    for key, value in ea.items():
        assert not (isinstance(value, (int, float)) and not isinstance(value, bool)
                    and key.endswith("_0_to_10")), f"{key} looks like a score"
    assert "onset_accuracy" not in A.ALL_COMPONENTS
    assert "entry_accuracy" not in A.ALL_COMPONENTS


def test_entry_accuracy_does_not_move_the_overall():
    """It is computed outside compute_technical_score precisely so that adding
    it changes no number and does not move rubric_fingerprint."""
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    take = _onset_take()
    before = A.compute_technical_score(take, cal)
    A.compute_entry_accuracy(take, cal)
    after = A.compute_technical_score(take, cal)
    assert json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)


def test_entry_accuracy_reports_a_professional_percentile():
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    ea = A.compute_entry_accuracy(_onset_take(pct_clean=24.2), cal)
    assert 0 <= ea["percentile_vs_pro_pack"] <= 100
    assert ea["n_references"] == 50
    assert ea["pro_median_pct_clean"] == 33.2
    # Higher clean rate must never score worse against the pack.
    better = A.compute_entry_accuracy(_onset_take(pct_clean=45.0), cal)
    assert better["percentile_vs_pro_pack"] > ea["percentile_vs_pro_pack"]


def test_entry_accuracy_withheld_when_there_are_too_few_onsets():
    """A percentage over a handful of entries is noise, not a diagnostic."""
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    assert A.compute_entry_accuracy(_onset_take(n=4), cal) is None
    assert A.compute_entry_accuracy({}, cal) is None
    assert A.compute_entry_accuracy({"onsets": {"n_onsets": 200}}, cal) is None


def test_entry_accuracy_survives_without_calibration():
    ea = A.compute_entry_accuracy(_onset_take(), None)
    assert ea["pct_clean"] == 24.2
    assert "percentile_vs_pro_pack" not in ea


def _contaminated():
    """Degraded signal WITH superhuman pitch behaviour — a tracker locked onto
    the backing band. Real example: You Sexy Thing 7 Jul 2026."""
    t = _onset_take(pct_clean=91.5, pct_scooped=5.1, pct_overshot=3.4, n=59)
    t["voice_quality"] = {"hnr_db_median": 8.0, "jitter_local_percent_median": 0.98}
    t["intonation"] = {"median_intra_note_drift_cents": 1.8}
    return t


def _harsh_room():
    """Aaron's BEST take on file — Kung Fu Fighting, Prince of Wales, 9.4
    capture-fair. Rough room, entirely human numbers. Must not be withheld."""
    t = _onset_take(pct_clean=26.2, n=140)
    t["voice_quality"] = {"hnr_db_median": 12.8, "jitter_local_percent_median": 1.00}
    t["intonation"] = {"median_intra_note_drift_cents": 33.2}
    return t


def test_contaminated_stem_has_its_entry_accuracy_withheld():
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    ea = A.compute_entry_accuracy(_contaminated(), cal)
    assert ea["reliability"] == "suspect"
    assert "percentile_vs_pro_pack" not in ea, (
        "a contaminated stem must never publish a professional percentile — "
        "it would read as beating every professional")


def test_a_harsh_room_is_reported_not_withheld():
    """The gate is conjunctive on purpose. Bad signal alone is a loud venue, and
    withholding it would false-alarm on his best performance."""
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    ea = A.compute_entry_accuracy(_harsh_room(), cal)
    assert ea["reliability"] == "reduced"
    assert ea["percentile_vs_pro_pack"] is not None
    assert "degraded capture" in ea["reliability_reason"]


def test_a_clean_capture_is_flagged_high():
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    t = _onset_take()
    t["voice_quality"] = {"hnr_db_median": 20.9, "jitter_local_percent_median": 0.60}
    t["intonation"] = {"median_intra_note_drift_cents": 38.2}
    assert A.compute_entry_accuracy(t, cal)["reliability"] == "high"


# ── Short-note drift artefact (the "0.0 cents / auto-10 stability" bug) ──────
# Notes shorter than the ~0.35 s drift smoothing window used to be flattened to
# a constant, whose spread is a fabricated 0.0 — reading as "perfectly steady"
# and pinning pitch_stability (and the straight-tone vibrato path) to 10/10 on
# short, fast phrasing (rap/funk/patter). The fix: exclude unmeasurable notes,
# report drift as None when too few remain, and let the scorer drop the
# component rather than credit the fake zero. This guards against regression.

def _f0_notes(note_len_s, n_notes=12, sr=22050, hop=512, base_hz=220.0,
              wobble_cents=25.0, gap_s=0.15):
    """A synthetic f0 track: n_notes stable-pitch plateaus (with a little
    vibrato-like wobble) separated by silence. note_len_s sets how long each
    sustained note is."""
    import numpy as np
    fps = sr / hop
    frames = []
    for i in range(n_notes):
        hz = base_hz * 2 ** ([0, 2, 4, 5, 7][i % 5] / 12)
        t = np.arange(int(note_len_s * fps)) / fps
        frames.append(hz * 2 ** ((wobble_cents * np.sin(2 * np.pi * 5 * t)) / 1200.0))
        frames.append(np.full(int(gap_s * fps), np.nan))
    return np.concatenate(frames), sr, hop


def test_short_notes_do_not_fabricate_zero_drift():
    # 0.30 s notes sit below the ~0.35 s smoothing window: drift is unmeasurable,
    # and MUST come back as None — never 0.0.
    f0, sr, hop = _f0_notes(0.30)
    r = A.analyse_intonation(f0, sr, hop)
    assert r["median_intra_note_drift_cents"] is None, (
        "short notes must report drift as unmeasurable (None), not a fabricated 0.0")
    assert r["drift_measurable_notes"] == 0
    # per-note values are None, not 0.0, so nothing downstream reads a fake zero
    assert all(n["drift_cents"] is None for n in r["notes"])


def test_long_notes_still_measure_real_drift():
    # 0.90 s notes are comfortably measurable: drift is a real, non-None number.
    f0, sr, hop = _f0_notes(0.90)
    r = A.analyse_intonation(f0, sr, hop)
    assert r["median_intra_note_drift_cents"] is not None
    assert r["drift_measurable_notes"] >= 5


def test_pitch_stability_dropped_when_drift_unmeasurable():
    # When drift is None the component must be ABSENT (weights renormalise),
    # never present at a fake 10.0.
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    r = _base_results(22.0, 30.0)
    r["intonation"] = {"method": "grid", "n_notes": 20,
                       "median_abs_deviation_cents": 15.0,
                       "median_intra_note_drift_cents": None}
    ts = A.compute_technical_score(r, cal)
    assert "pitch_stability" not in ts["components"], (
        "unmeasurable drift must drop pitch_stability, not score it 10/10")
    assert "pitch_stability" in ts["components_unscored"]
    # the straight-tone vibrato path must not claim steadiness it never measured
    vib = ts["components"].get("vibrato_control")
    if vib is not None:
        assert "straight-tone" not in vib.get("input", ""), (
            "straight-tone vibrato path must be skipped when drift is unmeasurable")


def test_measurable_drift_still_scores_pitch_stability():
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    ts = A.compute_technical_score(_base_results(22.0, 30.0), cal)  # drift = 20.0
    assert "pitch_stability" in ts["components"]


# ---------------------------------------------------------------------------
# MEASUREMENT ERA — the provenance hole the 16 Aug 2026 drift fix fell through.
# ---------------------------------------------------------------------------

def test_measurement_fingerprint_is_deterministic_and_travels_in_identity():
    """The rubric fingerprint hashes the scoring maths only, so a change to how a
    metric is MEASURED left every identity field identical and the two eras
    looked comparable. The measurement stamp closes that: stamped by main() on
    the analysis, carried into the score identity, None on older analyses."""
    fp = A.measurement_fingerprint()
    assert fp and fp == A.measurement_fingerprint()
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    stamped = _base_results(22.0, 30.0)
    stamped["measurement_fingerprint"] = fp
    ident = A.compute_technical_score(stamped, cal)["identity"]
    assert ident["measurement_fingerprint"] == fp
    # the committed pack predates the stamp: recorded honestly as None
    assert ident["calibration_measurement_fingerprint"] is None
    unstamped = A.compute_technical_score(_base_results(22.0, 30.0), cal)["identity"]
    assert unstamped["measurement_fingerprint"] is None
    # adding the stamp must not have moved the rubric fingerprint
    assert ident["rubric_fingerprint"] == unstamped["rubric_fingerprint"]


def test_scores_from_different_measurement_builds_are_not_comparable():
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    a = _base_results(22.0, 30.0); a["measurement_fingerprint"] = "aaaaaaaaaaaa"
    b = _base_results(22.0, 30.0); b["measurement_fingerprint"] = "bbbbbbbbbbbb"
    sa, sb = A.compute_technical_score(a, cal), A.compute_technical_score(b, cal)
    conflict = A.score_conflict(sa, sb)
    assert conflict is not None and "different engine builds" in conflict
    # same build compares; an unstamped (pre-stamp) score is left to preflight's
    # era inference rather than refused outright
    assert A.score_conflict(sa, A.compute_technical_score(a, cal)) is None
    assert A.score_conflict(sa, A.compute_technical_score(_base_results(22.0, 30.0), cal)) is None


def test_measurement_era_places_unstamped_analyses_by_the_drift_fix_marker():
    assert A.measurement_era({"measurement_fingerprint": "abc"}) == "abc"
    assert A.measurement_era({"intonation": {"drift_measurable_notes": 93}}) \
        == "post-drift-fix (unstamped)"
    assert A.measurement_era({"intonation": {"median_intra_note_drift_cents": 30.2}}) \
        == "pre-drift-fix (unstamped)"
    assert A.measurement_era(None) == "unknown"


def test_scale_mismatch_refuses_cross_era_scoring_in_both_directions():
    """After the pack is rebuilt on the fixed engine, a pre-fix take's flattered
    drift must not be re-scored against it (it would read ~10); before that, a
    post-fix take against the pre-fix pack is the mismatch the interim rule
    covers. The re-score tools skip both; the tables show them withheld."""
    old_pack = {"metrics": {}}                                  # unstamped, pre-fix
    new_pack = {"metrics": {}, "measurement_fingerprint": "newnewnewnew"}
    pre_fix = {"intonation": {"median_intra_note_drift_cents": 30.0}}
    post_fix_unstamped = {"intonation": {"drift_measurable_notes": 90}}
    stamped = {"measurement_fingerprint": "newnewnewnew"}
    assert A.pack_measurement_era(old_pack) == "pre-drift-fix (unstamped)"
    assert A.pack_measurement_era(new_pack) == "newnewnewnew"
    assert not A.scale_mismatch(pre_fix, old_pack)               # today's archive: fine
    assert A.scale_mismatch(post_fix_unstamped, old_pack)        # today's post-fix takes: interim rule
    assert A.scale_mismatch(pre_fix, new_pack)                   # tomorrow's hazard: refused
    assert A.scale_mismatch(post_fix_unstamped, new_pack)        # unproven era: refused
    assert not A.scale_mismatch(stamped, new_pack)               # re-analysed on the engine: fine
    assert not A.scale_mismatch(pre_fix, None)                   # no pack: nothing to mismatch
