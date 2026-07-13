from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

TRACKER_PATH = Path(__file__).parents[2] / "voxai-local-analysis" / "pitch_track.py"
SPEC = importlib.util.spec_from_file_location("pitch_track", TRACKER_PATH)
pitch_track = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pitch_track)


class PitchMathTests(unittest.TestCase):
    def test_a4_is_zero_cents_and_midi_69(self):
        self.assertAlmostEqual(pitch_track.cents_from_hz(440.0), 0.0)
        self.assertEqual(pitch_track.note_from_cents(0.0), "A4")

    def test_note_octave_boundary(self):
        c4_cents = 1200 * math.log2(261.625565 / 440.0)
        self.assertEqual(pitch_track.note_from_cents(c4_cents), "C4")

    def test_confidence_filter_keeps_null_gaps(self):
        f0 = np.array([440.0] * 8)
        confidence = np.array([0.9, 0.9, 0.1, 0.1, 0.9, 0.9, 0.1, 0.1])
        values, _ = pitch_track._sample_contour(f0, confidence, 8.0, 4.0, 0.55)
        self.assertEqual(values, [0.0, None, 0.0, None])

    def test_canonical_display_keeps_pyin_voiced_frames(self):
        f0 = np.array([440.0, 440.0, np.nan, 440.0])
        confidence = np.array([0.9, 0.1, 0.0, 0.2])
        values, probabilities = pitch_track._canonical_display_contour(
            f0, confidence, 4.0, 4.0
        )
        self.assertEqual(values, [0.0, 0.0, None, 0.0])
        self.assertEqual(probabilities, [0.9, 0.1, None, 0.2])

    def test_low_confidence_contour_uses_caution_fallback(self):
        sr = 44100
        seconds = 3
        t = np.arange(sr * seconds) / sr
        y = 0.25 * np.sin(2 * np.pi * 440 * t)
        with tempfile.TemporaryDirectory() as folder:
            wav = Path(folder) / "a4.wav"
            sf.write(wav, y, sr)
            original = pitch_track.RELIABLE_CONFIDENCE
            try:
                pitch_track.RELIABLE_CONFIDENCE = 1.1
                result = pitch_track.analyze_wav(wav, seconds)
            finally:
                pitch_track.RELIABLE_CONFIDENCE = original
        self.assertEqual(result["quality"]["classification"], "caution")
        self.assertIn("low_pitch_confidence", result["quality"]["flags"])

    def test_finds_vocal_and_instrumental_stems(self):
        with tempfile.TemporaryDirectory() as folder:
            stem_dir = Path(folder)
            (stem_dir / "take_(Vocals)_UVR.wav").touch()
            (stem_dir / "take_(Instrumental)_UVR.wav").touch()
            self.assertEqual(pitch_track._find_stem(stem_dir, "vocals").name, "take_(Vocals)_UVR.wav")
            self.assertEqual(pitch_track._find_stem(stem_dir, "instrumental").name, "take_(Instrumental)_UVR.wav")

    def test_reference_metadata_rejects_karaoke_substitution(self):
        with self.assertRaises(pitch_track.PitchTrackError):
            pitch_track._validate_reference_metadata(
                {"title": "Bye Bye Love karaoke backing track", "uploader": "Tracks"},
                "Bye Bye Love",
                "The Everly Brothers",
            )

    def test_reference_metadata_accepts_identified_original(self):
        pitch_track._validate_reference_metadata(
            {"title": "Everly Brothers - Bye Bye Love - Original HQ Audio", "uploader": "Archive"},
            "Bye Bye Love",
            "The Everly Brothers",
        )

    def test_synthetic_a4_track(self):
        sr = 44100
        seconds = 3
        t = np.arange(sr * seconds) / sr
        y = 0.25 * np.sin(2 * np.pi * 440 * t)
        with tempfile.TemporaryDirectory() as folder:
            wav = Path(folder) / "a4.wav"
            sf.write(wav, y, sr)
            result = pitch_track.analyze_wav(wav, seconds)
        detected = [x for x in result["contour"]["values"] if x is not None]
        self.assertGreater(len(detected), 20)
        self.assertLess(abs(float(np.median(detected))), 15)
        self.assertEqual(result["robust_min_note"], "A4")
        self.assertEqual(result["robust_max_note"], "A4")

    def test_comparison_aligns_reference_and_detects_transposition(self):
        values = [None] * 5 + [0.0, 100.0, 200.0, 100.0] * 8
        take_values = [None if value is None else value - 100.0 for value in values]
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            take = folder / "take.json"
            reference = folder / "reference.json"
            base = {"pitch": {"f0_contour": {"rate_hz": 10, "values": values}}, "technical_score": {"overall_score_0_to_10": 9}}
            take_data = {**base, "pitch": {"f0_contour": {"rate_hz": 10, "values": take_values}}}
            take.write_text(json.dumps(take_data), encoding="utf-8")
            reference.write_text(json.dumps(base), encoding="utf-8")
            comparison, aligned = pitch_track.compare_with_reference(take, reference)
        self.assertEqual(comparison["transposition_semitones"], -1)
        self.assertLessEqual(comparison["median_abs_pitch_diff_cents"], 1)
        self.assertEqual(len(aligned), len(take_values))

    def test_single_track_analysis_skips_reference_resolution(self):
        minimal_pitch = {
            "contour": {"rate_hz": 10, "values": [0.0], "confidence": [0.9]},
            "quality": {"classification": "reliable", "flags": []},
        }
        with tempfile.TemporaryDirectory() as folder:
            job_dir = Path(folder) / "job"
            stems = Path(folder) / "stems"
            stems.mkdir()
            vocals = stems / "vocals.wav"
            instrumental = stems / "instrumental.wav"
            vocals.touch()
            instrumental.touch()
            with patch.object(pitch_track, "probe_duration", return_value=5.0), patch.object(
                pitch_track, "separate_stems", return_value=(vocals, instrumental)
            ), patch.object(pitch_track, "_run"), patch.object(
                pitch_track, "analyze_wav", return_value=minimal_pitch
            ), patch.object(
                pitch_track, "run_v2_analysis", return_value=("v2/output/take_analysis.json", "v2/reports/analysis_report.md")
            ), patch.object(pitch_track, "fetch_reference") as fetch_reference:
                result = pitch_track.analyze(
                    Path(folder) / "take.wav",
                    job_dir,
                    performer_name="Test Singer",
                    comparison_enabled=False,
                )
        fetch_reference.assert_not_called()
        self.assertEqual(result["reference"], {"status": "skipped", "reason": "single_track_mode"})
        self.assertFalse(result["metadata"]["comparison_enabled"])


if __name__ == "__main__":
    unittest.main()
