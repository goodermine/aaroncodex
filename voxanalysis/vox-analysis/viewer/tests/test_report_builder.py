from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from report_builder import build_v2_report, render_full_results_text


class ReportBuilderTests(unittest.TestCase):
    def fixture(self):
        return {
            "technical_score": {
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
        self.assertIn("VOX ANALYSIS — FULL RESULTS", text)
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

    def test_strain_is_labelled_as_coaching_focus(self):
        raw = self.fixture()
        raw["voice_quality"]["strain"]["pct_top_notes_strained"] = 25
        report = build_v2_report(raw)
        self.assertEqual(report["main_focus"]["pillar"], "Ease and pressure")
        self.assertIn("heuristics", " ".join(report["unverifiable"]).lower())

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


def test_capture_fair_line_is_capture_aware():
    """Declared clean captures say to quote the OVERALL; declared live says to
    quote capture-fair; undeclared keeps the neutral wording. The take context
    itself is echoed so it travels with the results."""
    base = {"technical_score": {"overall_score_0_to_10": 8.7,
                                "capture_fair_score_0_to_10": 8.1,
                                "confidence": "high"}}
    def text_for(ctx):
        raw = dict(base)
        if ctx:
            raw["take_context"] = ctx
        return render_full_results_text(build_v2_report(raw))
    home = text_for({"intent": "performance", "capture": "home"})
    assert "shown for completeness" in home and "OVERALL" in home
    assert "Take context: performance · home capture" in home
    live = text_for({"capture": "live", "note": "tavern set"})
    assert "declared live capture, so quote THIS number" in live
    assert "tavern set" in live
    plain = text_for(None)
    assert "quote this for live or rough captures" in plain
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
