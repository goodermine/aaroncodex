from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
FIXTURES = json.loads((Path(__file__).with_name("ui_fixtures.json")).read_text(encoding="utf-8"))


class UiContractTests(unittest.TestCase):
    def test_preserves_functional_control_ids(self):
        required = {
            "analysis", "artistName", "audio", "background", "cents", "chart", "comparisonMode",
            "chartWrap", "conditions", "drop", "empty", "error", "file", "follow",
            "instrumental", "minus", "new", "note", "originalAudio",
            "originalIdentity", "originalListen", "originalOverlay", "originalPlayer",
            "pitchColour", "plus", "reset", "singerName", "songName", "status",
            "statusText", "technicalReport", "uploadCard", "viewer", "warning"
        }
        ids = set(re.findall(r'id="([^"]+)"', HTML))
        self.assertTrue(required.issubset(ids), required - ids)

    def test_signal_chain_matches_backend_stages(self):
        stages = re.findall(r'data-stage="([^"]+)"', HTML)
        self.assertEqual(stages, FIXTURES["processing_stages"])

    def test_flagship_copy_and_accessibility_contract(self):
        self.assertIn("Your voice.<br>In full resolution.", HTML)
        self.assertIn("VOXAI // Performance Intelligence", HTML)
        self.assertIn('role="alert"', HTML)
        self.assertIn('aria-live="polite"', HTML)
        self.assertIn("prefers-reduced-motion", HTML)

    def test_heavy_report_is_deferred(self):
        self.assertIn("Open this rack to load the full report.", HTML)
        self.assertIn("if(technicalLoaded)return", HTML)
        names = {fixture["name"] for fixture in FIXTURES["result_states"]}
        self.assertIn("long_technical_report", names)

    def test_v3_diagnostics_are_distinct_from_v2_score(self):
        self.assertIn("V3 diagnostics", HTML)
        self.assertIn("V2 calibrated score", HTML)
        self.assertIn("Clean onsets", HTML)
        self.assertIn("Singer’s-formant ratio", HTML)
        self.assertIn("H1−H2", HTML)

    def test_single_track_mode_is_explicit_and_suppresses_comparison(self):
        self.assertIn("comparisonEnabled", HTML)
        self.assertIn("body.append('comparison',comparisonEnabled?'true':'false')", HTML)
        self.assertIn("body.append('song',song)", HTML)
        self.assertIn("body.append('artist',artist)", HTML)
        self.assertNotIn("song.disabled=!enabled", HTML)
        self.assertIn("Original artist or composer (optional)", HTML)
        self.assertIn("if(reference?.status==='skipped')return''", HTML)
        names = {fixture["name"] for fixture in FIXTURES["result_states"]}
        self.assertIn("single_track", names)

    def test_pitch_variance_colour_reserves_red_for_large_errors(self):
        self.assertIn("error<=15?0", HTML)
        self.assertIn("error<=30?(error-15)/15*.22", HTML)
        self.assertIn("error<=40?.22+(error-30)/10*.38", HTML)
        self.assertIn(".6+(error-40)/10*.4", HTML)

    def test_warning_fixtures_cover_evidence_risks(self):
        flags = {
            flag
            for fixture in FIXTURES["result_states"]
            for flag in fixture.get("quality_flags", [])
        }
        self.assertEqual(
            flags,
            {"low_voiced_coverage", "low_pitch_confidence", "clipping_detected"},
        )


if __name__ == "__main__":
    unittest.main()
