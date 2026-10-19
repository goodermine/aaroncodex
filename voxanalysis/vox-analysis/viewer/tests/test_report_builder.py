from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from report_builder import build_v2_report, render_full_results_text

# A current-era score identity. A score with no identity is legacy under
# CLAUDE.md rule 3 and the report withholds its headline.
CURRENT_IDENTITY = {"contract": "voxai_score_v1", "rubric": "deterministic_rubric_v5"}


class ReportBuilderTests(unittest.TestCase):
    def fixture(self):
        return {
            "technical_score": {
                "identity": dict(CURRENT_IDENTITY),
                "overall_score_0_to_10": 8.4,
                "capture_fair_score_0_to_10": 8.8,
                "confidence": "high",
                "components": {
                    "intonation_accuracy": {"score": 7.5, "input": "measured"},
                    "pitch_stability": {"score": 6.2, "input": "measured"},
                },
            },
            "intonation": {
                "n_notes": 42,
                "median_abs_deviation_cents": 20.0,
                "p90_abs_deviation_cents": 44.0,
                "pct_notes_within_10_cents": 32.1,
                "pct_notes_within_25_cents": 67.9,
                "median_intra_note_drift_cents": 58.0,
                "worst_drift_notes": [
                    {"time": "01:02", "start_s": 62.0, "note": "A4", "held_drift_cents": 88.0, "deviation_cents": 21.0}
                ],
            },
            "voice_quality": {
                "reliability": "high",
                "jitter_local_percent_median": 0.4,
                "shimmer_local_percent_median": 4.1,
                "hnr_db_median": 19.2,
                "cpps_db": 13.4,
                "strain": {"n_strained": 0, "n_top_quartile_notes": 12, "pct_top_notes_strained": 0},
            },
            "vibrato": {"pct_notes_with_vibrato": 40.0, "median_rate_hz": 5.1},
            "dynamics": {"effective_dynamic_range_db": 27.0, "n_phrases": 9},
            "phrasing": {"median_phrase_s": 4.2},
            "breath": {"n_phrases_measured": 8, "n_sagging_endings": 2, "pct_sagging_endings": 25.0},
            "range_map": {"comfortable_core": "G3-D4", "extremes_touched": "E3-G4", "most_used_note": "A3"},
            "resonance": {
                "singers_formant_ratio_db": -14.2,
                "singers_formant_read": "Moderate projection",
            },
            "onsets": {
                "n_onsets": 30,
                "pct_clean": 70.0,
                "pct_scooped": 20.0,
                "pct_overshot": 10.0,
                "median_scoop_depth_cents": -48.0,
            },
            "harmonics": {
                "n_notes": 25,
                "H1_minus_H2_median_db": -1.2,
                "h1_h2_read": "Balanced source",
            },
            "formants": {
                "vowel_space": {
                    "n_notes_mapped": 32,
                    "n_notes_excluded_high_pitch": 4,
                    "vowel_distribution": {"eh (bet)": 12},
                    "reliability": "medium",
                }
            },
            "diagnostic_flags": [],
        }

    def test_builds_bounded_human_report(self):
        report = build_v2_report(self.fixture())
        self.assertEqual(report["score"]["overall"], 8.4)
        self.assertEqual(report["metrics"]["range"]["comfortable_core"], "G3-D4")
        self.assertEqual(report["main_focus"]["drill"], "Messa di Voce on Single Pitches")
        self.assertEqual(report["trouble_spots"][0]["start_s"], 62.0)
        self.assertEqual(report["practice_plan"]["immediate"]["duration"], "4-5 minutes before the next take")
        self.assertEqual(len(report["practice_plan"]["long_term"]["sessions"]), 3)
        self.assertEqual(report["version"], "voxai_v3_diagnostics_v2_score")
        self.assertEqual(report["metrics"]["onsets"]["clean_percent"], 70.0)
        self.assertEqual(report["metrics"]["harmonics"]["h1_minus_h2_db"], -1.2)
        self.assertEqual(report["metrics"]["resonance"]["singers_formant_read"], "Moderate projection")
        self.assertEqual(report["metrics"]["vowel_space"]["notes_mapped"], 32)

    def test_score_carries_capture_fair_and_provenance_for_the_badge(self):
        """The deck's score badge needs capture-fair, confidence, calibration
        provenance and a capture-risk flag — all on report['score']."""
        raw = self.fixture()
        raw["technical_score"]["calibration"] = {"active": True, "n_references": 50}
        raw["time_diagnostics"] = {"environment_risk": {"karaoke_or_room_contamination_risk": "elevated"}}
        score = build_v2_report(raw)["score"]
        self.assertEqual(score["capture_fair"], 8.8)
        self.assertEqual(score["confidence"], "high")
        self.assertTrue(score["calibrated"])
        self.assertEqual(score["calibration_references"], 50)
        self.assertTrue(score["capture_risk"])
        # uncalibrated / clean-capture fixture reports the opposite
        clean = build_v2_report(self.fixture())["score"]
        self.assertFalse(clean["calibrated"])
        self.assertFalse(clean["capture_risk"])

    def test_full_results_text_matches_the_web_digest_content(self):
        """render_full_results_text is the single source of truth for the
        'full results' a text client (Candi over Telegram) sends — it must carry
        the same sections the web page shows: scores + capture-fair + provenance,
        every metric group, focus, the evidence lists and the practice plan."""
        raw = self.fixture()
        raw["technical_score"]["calibration"] = {"active": True, "n_references": 50}
        report = build_v2_report(raw)
        text = render_full_results_text(report, {"file_name": "take.wav",
                                                 "robust_min_note": "E3", "robust_max_note": "A5"})
        # header + provenance
        self.assertIn("SINGNEXA — FULL RESULTS", text)
        self.assertIn("take.wav", text)
        self.assertIn("Overall: 8.4/10", text)
        self.assertIn("Capture-fair: 8.8/10", text)
        self.assertIn("10 = a typical pro", text)      # calibration provenance line
        self.assertIn("RANGE: E3 - A5", text)
        # sections
        for header in ("SCORES", "METRICS", "PRIMARY FOCUS", "MEASURED",
                       "UNVERIFIABLE FROM AUDIO", "PRACTICE PLAN"):
            self.assertIn(header, text)
        # a measured number actually made it in (not a curated summary)
        self.assertIn("median_deviation_cents: 20.0", text)
        self.assertIn("not a summary", text)

    def test_full_results_text_notes_a_withheld_score(self):
        raw = self.fixture()
        raw["technical_score"]["overall_score_0_to_10"] = None
        text = render_full_results_text(build_v2_report(raw))
        self.assertIn("score withheld", text.lower())

    def test_talk_cut_is_listed_with_recording_times_and_never_scored(self):
        raw = self.fixture()
        raw["audio_prep"] = {"talk_cut": {
            "method": "talk_cut_v1", "status": "cut", "offset_s": 41.87, "kept": [[41.87, 230.0]],
            "removed": [{"start": 0.0, "end": 41.87, "kind": "before_singing", "text": "thank you"},
                        {"start": 230.0, "end": 236.5, "kind": "after_singing", "text": ""}]}}
        report = build_v2_report(raw)
        self.assertEqual(report["audio_prep"]["starts_at"], "0:41.9")
        self.assertEqual(report["score"]["overall"], 8.4)            # unchanged: prep is not an input
        text = render_full_results_text(report)
        self.assertIn("AUDIO PREP", text)
        self.assertIn("0:00.0–0:41.9 before the singing (heard: “thank you”)", text)
        self.assertIn("3:50.0–3:56.5 after the singing", text)
        self.assertIn("0:41.9 into your recording", text)

    def test_no_talk_cut_means_no_audio_prep_section(self):
        report = build_v2_report(self.fixture())
        self.assertIsNone(report["audio_prep"])
        self.assertNotIn("AUDIO PREP", render_full_results_text(report))

    def test_strain_is_labelled_as_coaching_focus(self):
        raw = self.fixture()
        raw["voice_quality"]["strain"]["pct_top_notes_strained"] = 25
        report = build_v2_report(raw)
        self.assertEqual(report["main_focus"]["pillar"], "Ease and pressure")
        self.assertIn("heuristics", " ".join(report["unverifiable"]).lower())

    def test_high_drift_does_not_override_a_genuinely_strong_pitch_stability_score(self):
        """The 3 Sep 2026 pack rebuild moved the professional median for
        held-note drift to ~62.55 cents (docs/handoffs/HANDOFF_SESSION_2026-09-03.md).
        A hardcoded 45-cent threshold here, stale from before that rebuild,
        used to flag PRIMARY FOCUS as held-note stability even when its
        calibrated score was a perfect 10 — hijacking the focus away from an
        actually weak component. Real example: the 2026-09-04 'You Give Love
        a Bad Name' take scored pitch_stability 10.0 at 57.0 cents drift, but
        the report still picked it over voice_quality at 5.78."""
        raw = self.fixture()
        raw["technical_score"]["components"]["pitch_stability"]["score"] = 10.0
        raw["technical_score"]["components"]["voice_quality"] = {"score": 5.78, "input": "measured"}
        raw["intonation"]["median_intra_note_drift_cents"] = 57.0
        report = build_v2_report(raw)
        self.assertEqual(report["main_focus"]["pillar"], "Voice quality")

    def test_high_drift_still_overrides_when_pitch_stability_score_is_genuinely_severe(self):
        """The drift fast-path must still fire when the calibrated score says
        the drift really is bad — even if it is not the single lowest-scoring
        component — so a glaring stability problem is not buried under a
        marginally lower but less audible component."""
        raw = self.fixture()
        raw["technical_score"]["components"]["pitch_stability"]["score"] = 1.5
        raw["technical_score"]["components"]["voice_quality"] = {"score": 4.0, "input": "measured"}
        raw["intonation"]["median_intra_note_drift_cents"] = 95.0
        report = build_v2_report(raw)
        self.assertEqual(report["main_focus"]["pillar"], "Held-note stability")
        self.assertIn("95.0 cents", report["main_focus"]["why"])

    def test_recording_conditions_are_context_not_causation(self):
        report = build_v2_report(
            self.fixture(),
            conditions="Live room, lots of background noise, not warmed up and tired",
        )
        context = report["recording_context"]
        self.assertIn("stem separation", " ".join(context["measurement_effects"]))
        self.assertIn("No warm-up", " ".join(context["performance_effects"]))
        self.assertIn("not proof", context["caution"])


if __name__ == "__main__":
    unittest.main()


def test_lead_with_the_higher_score():
    """House rule: lead with whichever of overall / capture-fair is HIGHER, on any
    capture, and give the other beside it. The take context is echoed so it
    travels with the results."""
    def text_for(overall, cf, ctx=None):
        raw = {"technical_score": {"identity": dict(CURRENT_IDENTITY),
                                   "overall_score_0_to_10": overall,
                                   "capture_fair_score_0_to_10": cf,
                                   "confidence": "high"}}
        if ctx:
            raw["take_context"] = ctx
        return render_full_results_text(build_v2_report(raw))
    # live take where overall is the higher number (Rilda, On The Radio)
    live = text_for(7.9, 7.2, {"capture": "live", "note": "tavern set"})
    assert "Lead with: 7.9/10 overall — the higher of the two; give 7.2/10 capture-fair beside it" in live
    assert "quote THIS number" not in live
    assert "tavern set" in live
    # studio take where capture-fair is the higher number
    home = text_for(8.1, 8.7, {"intent": "performance", "capture": "home"})
    assert "Lead with: 8.7/10 capture-fair — the higher of the two; give 8.1/10 overall beside it" in home
    assert "Take context: performance · home capture" in home
    plain = text_for(8.7, 8.1)
    assert "Lead with: 8.7/10 overall" in plain
    assert "Take context:" not in plain


class InterimStabilityRuleTests(unittest.TestCase):
    """docs/VOX_SYSTEM_REVIEW_2026-09-02.md §3.1: a take measured after the drift
    fix but scored against the pre-fix pack must not quote pitch_stability; the
    held-drift median is read against the professional band instead."""

    def post_fix_take(self):
        notes = [{"duration_s": 0.8, "held_drift_cents": c} for c in (30.0, 45.0, 50.0, 60.0, 90.0)]
        notes.append({"duration_s": 0.3, "held_drift_cents": 0.0})   # too short: ignored
        return {
            "technical_score": {
                "overall_score_0_to_10": 7.3, "capture_fair_score_0_to_10": 6.2,
                "confidence": "high",
                "identity": {"contract": "voxai_score_v1", "rubric": "deterministic_rubric_v5",
                             "rubric_fingerprint": "7cbd02df8f62",
                             "measurement_fingerprint": None,
                             "calibration_measurement_fingerprint": None},
                "components": {
                    "intonation_accuracy": {"score": 10.0, "input": "measured"},
                    "pitch_stability": {"score": 0.0, "input": "median intra-note drift = 103.7 cents"},
                    "breath_support": {"score": 2.56, "input": "measured"},
                },
            },
            "intonation": {"n_notes": 129, "median_abs_deviation_cents": 20.0,
                           "median_intra_note_drift_cents": 103.7,
                           "drift_measurable_notes": 93, "notes": notes},
            "voice_quality": {"strain": {"pct_top_notes_strained": 0}},
            "breath": {"pct_sagging_endings": 40.0},
        }

    def test_pitch_stability_is_withheld_and_held_drift_read_against_the_band(self):
        report = build_v2_report(self.post_fix_take())
        rows = {c["key"]: c for c in report["score"]["components"]}
        self.assertTrue(rows["pitch_stability"]["withheld"])
        self.assertIsNone(rows["pitch_stability"]["score"])
        self.assertEqual(rows["intonation_accuracy"]["score"], 10.0)
        interim = report["interim_stability"]
        self.assertEqual(interim["held_drift_median_cents"], 50.0)   # median of the 5 long notes
        self.assertIn("wider than a typical pro", interim["read"])
        # the focus must not be picked from the withheld component or the drift threshold
        self.assertNotEqual(report["main_focus"]["pillar"], "Held-note stability")
        text = render_full_results_text(report)
        self.assertIn("HELD-NOTE STABILITY (interim reading", text)
        self.assertIn("Held-note stability: —", text)
        self.assertNotIn("PRIMARY FOCUS: Held-note stability", text)

    def test_rule_lifts_when_take_and_pack_share_a_measurement_stamp(self):
        raw = self.post_fix_take()
        raw["technical_score"]["identity"]["measurement_fingerprint"] = "abc123abc123"
        raw["technical_score"]["identity"]["calibration_measurement_fingerprint"] = "abc123abc123"
        report = build_v2_report(raw)
        rows = {c["key"]: c for c in report["score"]["components"]}
        self.assertFalse(rows["pitch_stability"]["withheld"])
        self.assertEqual(rows["pitch_stability"]["score"], 0.0)
        self.assertIsNone(report["interim_stability"])

    def test_pre_fix_take_is_untouched(self):
        raw = self.post_fix_take()
        del raw["intonation"]["drift_measurable_notes"]
        report = build_v2_report(raw)
        self.assertIsNone(report["interim_stability"])
        self.assertFalse({c["key"]: c for c in report["score"]["components"]}["pitch_stability"]["withheld"])


# ---- scoring-engine review fixes, 17 Oct 2026 ----

def _scored(overall=8.0, cf=8.5, identity=None, components=None, **extra):
    raw = {"technical_score": {"identity": identity if identity is not None else dict(CURRENT_IDENTITY),
                               "overall_score_0_to_10": overall,
                               "capture_fair_score_0_to_10": cf,
                               "confidence": "high",
                               "components": components or {}}}
    raw.update(extra)
    return raw


def test_an_older_rubric_with_a_contract_is_legacy_and_withheld():
    raw = _scored(identity={"contract": "voxai_score_v1", "rubric": "deterministic_rubric_v4"})
    report = build_v2_report(raw)
    assert report["score"]["legacy"] is True
    assert report["score"]["overall"] is None and report["score"]["capture_fair"] is None
    text = render_full_results_text(report)
    assert "8.0/10" not in text and "withheld: legacy score" in text
    assert "LEGACY SCORE" in text


def test_an_unseparated_score_is_withheld_unless_it_declares_a_dry_source():
    identity = dict(CURRENT_IDENTITY, stem_model=None)
    report = build_v2_report(_scored(identity=identity))
    assert report["score"]["overall"] is None
    assert "stem separation did not run" in render_full_results_text(report)

    for source in ("dry", "isolated_stem"):
        ok = build_v2_report(_scored(identity=dict(identity), take_context={"vocal_source": source}))
        assert ok["score"]["overall"] == 8.0
    supplied = build_v2_report(_scored(identity=dict(identity),
                                       stem_separation={"source": "supplied_backing"}))
    assert supplied["score"]["overall"] == 8.0
    separated = build_v2_report(_scored(identity=dict(CURRENT_IDENTITY, stem_model="RoFormer")))
    assert separated["score"]["overall"] == 8.0


def test_voice_quality_is_never_the_focus_on_an_elevated_room_capture():
    components = {"voice_quality": {"score": 3.0, "input": "room"},
                  "breath_support": {"score": 6.0, "input": "measured"},
                  "intonation_accuracy": {"score": 9.0, "input": "measured"}}
    raw = _scored(components=components,
                  time_diagnostics={"environment_risk": {"karaoke_or_room_contamination_risk": "elevated"}},
                  breath={"n_phrases_measured": 10, "n_sagging_endings": 6, "pct_sagging_endings": 60.0})
    report = build_v2_report(raw)
    rows = {c["key"]: c for c in report["score"]["components"]}
    assert rows["voice_quality"]["capture_sensitive"] is True
    assert report["main_focus"]["pillar"] != "Voice quality"


def test_breath_support_focus_gets_a_breath_practice_plan():
    components = {"breath_support": {"score": 2.0, "input": "measured"},
                  "intonation_accuracy": {"score": 9.0, "input": "measured"}}
    # Sag under the 50% "Phrase endings" shortcut, so the weakest-component path
    # names the pillar "Breath support" — the path that fell back to pitch drills.
    raw = _scored(components=components,
                  breath={"n_phrases_measured": 10, "n_sagging_endings": 4, "pct_sagging_endings": 40.0})
    report = build_v2_report(raw)
    assert report["main_focus"]["pillar"] == "Breath support"
    steps = " ".join(report["practice_plan"]["immediate"]["steps"])
    assert "ribs" in steps and "drone" not in steps
