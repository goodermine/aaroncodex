from __future__ import annotations

import importlib.util
import json
import math
import os
import tempfile
import time
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

    def test_confidence_filter_marks_detected_lows_and_keeps_unvoiced_blank(self):
        f0 = np.array(
            [440.0, 440.0, 440.0, 440.0, np.nan, np.nan, 440.0, 440.0]
        )
        confidence = np.array([0.9, 0.9, 0.1, 0.1, 0.0, 0.0, 0.55, 0.55])
        values, probabilities, low_confidence = pitch_track._sample_contour(
            f0, confidence, 8.0, 4.0, 0.55
        )
        self.assertEqual(values, [0.0, 0.0, None, 0.0])
        self.assertEqual(probabilities, [0.9, 0.1, None, 0.55])
        self.assertEqual(low_confidence, [False, True, False, False])

        sparse_values, _, sparse_low_confidence = pitch_track._sample_contour(
            np.array([440.0, np.nan, np.nan, np.nan]),
            np.array([0.9, 0.0, 0.0, 0.0]),
            4.0,
            1.0,
            0.55,
        )
        self.assertEqual(sparse_values, [0.0])
        self.assertEqual(sparse_low_confidence, [False])

    def test_canonical_display_keeps_pyin_voiced_frames(self):
        f0 = np.array([440.0, 440.0, np.nan, 440.0])
        confidence = np.array([0.9, 0.1, 0.0, 0.2])
        values, probabilities, low_confidence = pitch_track._canonical_display_contour(
            f0, confidence, 4.0, 4.0
        )
        self.assertEqual(values, [0.0, 0.0, None, 0.0])
        self.assertEqual(probabilities, [0.9, 0.1, None, 0.2])
        self.assertEqual(low_confidence, [False, True, False, True])

    def test_finite_pitch_without_confidence_is_marked_uncertain(self):
        for sampler, arguments in (
            (pitch_track._canonical_display_contour, (1.0, 1.0)),
            (pitch_track._sample_contour, (1.0, 1.0, 0.55)),
        ):
            values, probabilities, low_confidence = sampler(
                np.array([440.0]), np.array([np.nan]), *arguments
            )
            self.assertEqual(values, [0.0])
            self.assertEqual(probabilities, [None])
            self.assertEqual(low_confidence, [True])
            self.assertEqual(len(values), len(probabilities))
            self.assertEqual(len(values), len(low_confidence))

    def test_voiced_mask_overrides_finite_pyin_pitch_before_publication(self):
        frame_count = 30
        f0 = np.full(frame_count, 440.0)
        voiced = np.ones(frame_count, dtype=bool)
        probability = np.full(frame_count, 0.9)
        voiced[0] = False
        probability[0] = 0.99
        probability[1] = 0.1
        audio = np.full(5120, 0.1)

        with patch.object(
            pitch_track.librosa, "load", return_value=(audio, 5120)
        ), patch.object(
            pitch_track.librosa,
            "pyin",
            return_value=(f0, voiced, probability),
        ):
            result = pitch_track.analyze_wav(Path("unused.wav"), 3.0)

        contour = result["contour"]
        self.assertIsNone(contour["values"][0])
        self.assertIsNone(contour["confidence"][0])
        self.assertFalse(contour["low_confidence"][0])
        self.assertEqual(contour["values"][1], 0.0)
        self.assertEqual(contour["confidence"][1], 0.1)
        self.assertTrue(contour["low_confidence"][1])

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
        contour = result["contour"]
        self.assertEqual(len(contour["values"]), len(contour["low_confidence"]))
        self.assertTrue(
            any(
                value is not None and flagged
                for value, flagged in zip(
                    contour["values"], contour["low_confidence"]
                )
            )
        )
        self.assertTrue(
            all(
                not flagged
                for value, flagged in zip(
                    contour["values"], contour["low_confidence"]
                )
                if value is None
            )
        )

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
            ), patch.object(pitch_track, "fetch_reference") as fetch_reference, patch.object(
                pitch_track, "_run_spectral_export"
            ) as spectral_export:
                result = pitch_track.analyze(
                    Path(folder) / "take.wav",
                    job_dir,
                    performer_name="Test Singer",
                    comparison_enabled=False,
                )
        fetch_reference.assert_not_called()
        spectral_export.assert_not_called()
        self.assertEqual(result["reference"], {"status": "skipped", "reason": "single_track_mode"})
        self.assertFalse(result["metadata"]["comparison_enabled"])
        self.assertNotIn("spectral", result)

    def test_fixed_input_spectral_export_is_strictly_additive_and_score_neutral(self):
        analyzer_path = TRACKER_PATH.with_name("analyse_song.py")
        analyzer_spec = importlib.util.spec_from_file_location(
            "protected_analyse_song_score_equivalence", analyzer_path
        )
        analyzer = importlib.util.module_from_spec(analyzer_spec)
        assert analyzer_spec.loader
        analyzer_spec.loader.exec_module(analyzer)

        fixed_measurements = {
            "intonation": {
                "median_abs_deviation_cents": 8.0,
                "median_intra_note_drift_cents": 12.0,
                "n_notes": 10,
            },
            "voice_quality": {
                "method": "praat sustained-note metrics",
                "jitter_local_percent_median": 0.4,
                "shimmer_local_percent_median": 3.0,
                "hnr_db_median": 19.0,
            },
            "vibrato": {
                "n_notes_analysed": 5,
                "pct_notes_with_vibrato": 60.0,
                "median_rate_hz": 6.0,
                "median_extent_cents": 70.0,
            },
            "dynamics": {
                "phrase_level_spread_db": 7.0,
                "effective_dynamic_range_db": 14.0,
            },
            "phrasing": {"median_phrase_s": 3.0},
            "time_diagnostics": {
                "environment_risk": {
                    "karaoke_or_room_contamination_risk": "low"
                }
            },
        }
        technical_score = analyzer.compute_technical_score(fixed_measurements)
        measurements_with_spectral = json.loads(json.dumps(fixed_measurements))
        measurements_with_spectral["spectral"] = {
            "version": "voxai_spectral_v1",
            "status": "ready",
        }
        self.assertEqual(
            analyzer.compute_technical_score(measurements_with_spectral),
            technical_score,
        )

        fixed_analysis = {
            "duration_seconds": 5.0,
            "contour": {
                "rate_hz": 10,
                "units": "cents_rel_A440",
                "values": [0.0, 2.0, None, -1.0],
                "confidence": [0.98, 0.96, None, 0.97],
            },
            "quality": {"classification": "reliable", "flags": []},
        }
        fixed_v2_analysis = {
            **fixed_measurements,
            "technical_score": technical_score,
        }

        def run_fixed(root: Path, export_enabled: bool) -> tuple[dict, bytes, bytes]:
            job_dir = root / "job"
            stems = root / "stems"
            stems.mkdir(parents=True)
            vocals = stems / "vocals.wav"
            instrumental = stems / "instrumental.wav"
            vocals.touch()
            instrumental.touch()

            def create_output(command, _error_code):
                Path(command[-1]).parent.mkdir(parents=True, exist_ok=True)
                Path(command[-1]).touch()

            def write_fixed_v2(_wav_path, target_job_dir, _performer_name):
                analysis_path = target_job_dir / "v2" / "output" / "fixed-take_analysis.json"
                report_path = target_job_dir / "v2" / "reports" / "fixed-take_report.md"
                analysis_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.parent.mkdir(parents=True, exist_ok=True)
                analysis_path.write_text(
                    json.dumps(fixed_v2_analysis, indent=2), encoding="utf-8"
                )
                report_path.write_text("# Fixed report\n", encoding="utf-8")
                return (
                    str(analysis_path.relative_to(target_job_dir)),
                    str(report_path.relative_to(target_job_dir)),
                )

            def export_fixture(
                _wav_path, output_dir, _contour, source, _timeout_seconds
            ):
                output_dir.mkdir(parents=True)
                descriptor = {
                    "source": source,
                    "harmonic_tracks_file": "harmonic-tracks.json",
                    "tiles": [],
                }
                (output_dir / "descriptor.json").write_text(
                    json.dumps(descriptor), encoding="utf-8"
                )
                (output_dir / "harmonic-tracks.json").write_text(
                    "{}", encoding="utf-8"
                )
                return descriptor

            with patch.object(pitch_track, "probe_duration", return_value=5.0), patch.object(
                pitch_track, "separate_stems", return_value=(vocals, instrumental)
            ), patch.object(pitch_track, "_run", side_effect=create_output), patch.object(
                pitch_track, "analyze_wav", return_value=fixed_analysis.copy()
            ), patch.object(
                pitch_track,
                "run_v2_analysis",
                side_effect=write_fixed_v2,
            ), patch.object(
                pitch_track, "_run_spectral_export", side_effect=export_fixture
            ):
                result = pitch_track.analyze(
                    root / "fixed-take.wav",
                    job_dir,
                    performer_name="Fixed Singer",
                    song_name="Fixed Song",
                    original_artist="Fixed Composer",
                    comparison_enabled=False,
                    export_spectral_enabled=export_enabled,
                )
            return (
                result,
                (job_dir / "result.json").read_bytes(),
                (job_dir / result["v2_analysis_file"]).read_bytes(),
            )

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            disabled, disabled_bytes, disabled_v2_bytes = run_fixed(
                root / "disabled-a", False
            )
            disabled_repeat, disabled_repeat_bytes, disabled_repeat_v2_bytes = run_fixed(
                root / "disabled-b", False
            )
            enabled, _enabled_bytes, enabled_v2_bytes = run_fixed(
                root / "enabled", True
            )

        self.assertEqual(disabled_bytes, disabled_repeat_bytes)
        self.assertEqual(disabled_v2_bytes, disabled_repeat_v2_bytes)
        self.assertEqual(enabled_v2_bytes, disabled_v2_bytes)
        self.assertEqual(disabled, disabled_repeat)
        self.assertEqual(set(enabled) - set(disabled), {"spectral"})
        enabled_core = enabled.copy()
        spectral = enabled_core.pop("spectral")
        self.assertEqual(enabled_core, disabled)
        self.assertEqual(
            json.dumps(enabled_core, indent=2).encode("utf-8"), disabled_bytes
        )
        disabled_score = json.loads(disabled_v2_bytes)["technical_score"]
        enabled_score = json.loads(enabled_v2_bytes)["technical_score"]
        self.assertEqual(enabled_score, disabled_score)
        self.assertEqual(enabled_score, technical_score)
        self.assertEqual(spectral["status"], "ready")
        self.assertEqual(set(spectral["sources"]), {"vocals"})

    def test_spectral_export_failure_does_not_fail_analysis(self):
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

            def create_output(command, _error_code):
                Path(command[-1]).parent.mkdir(parents=True, exist_ok=True)
                Path(command[-1]).touch()

            with patch.object(pitch_track, "probe_duration", return_value=5.0), patch.object(
                pitch_track, "separate_stems", return_value=(vocals, instrumental)
            ), patch.object(pitch_track, "_run", side_effect=create_output), patch.object(
                pitch_track, "analyze_wav", return_value=minimal_pitch
            ), patch.object(
                pitch_track, "run_v2_analysis", return_value=("v2/output/take_analysis.json", "v2/reports/analysis_report.md")
            ), patch.object(
                pitch_track,
                "_run_spectral_export",
                side_effect=RuntimeError("sentinel /private/path"),
            ) as spectral_export:
                result = pitch_track.analyze(
                    Path(folder) / "take.wav",
                    job_dir,
                    performer_name="Test Singer",
                    comparison_enabled=False,
                    export_spectral_enabled=True,
                    stage_file=job_dir / "stage.json",
                )

            spectral_export.assert_called_once()
            self.assertEqual(result["spectral"]["status"], "unavailable")
            self.assertEqual(
                result["spectral"]["sources"]["vocals"],
                {"status": "unavailable", "reason": "spectral_export_failed"},
            )
            self.assertNotIn("sentinel", json.dumps(result))
            self.assertEqual(result["v2_analysis_file"], "v2/output/take_analysis.json")
            self.assertEqual(json.loads((job_dir / "stage.json").read_text())["stage"], "building_report")
            self.assertTrue((job_dir / "result.json").is_file())
            self.assertFalse((job_dir / "analysis.wav").exists())

    def test_spectral_export_hang_is_bounded_and_job_still_completes(self):
        minimal_pitch = {
            "contour": {"rate_hz": 10, "values": [0.0], "confidence": [0.9]},
            "quality": {"classification": "reliable", "flags": []},
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job_dir = root / "job"
            stems = root / "stems"
            stems.mkdir()
            vocals = stems / "vocals.wav"
            instrumental = stems / "instrumental.wav"
            vocals.touch()
            instrumental.touch()
            hanging_exporter = root / "hanging_exporter.py"
            hanging_exporter.write_text(
                "import json, os, pathlib, sys, time\n"
                "output = pathlib.Path(sys.argv[2])\n"
                "temporary = output.with_name(output.name + '.tmp')\n"
                "temporary.mkdir(parents=True)\n"
                "(output.parents[1] / 'hang-started.json').write_text(json.dumps({'pid': os.getpid()}))\n"
                "json.load(sys.stdin)\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )

            def create_output(command, _error_code):
                Path(command[-1]).parent.mkdir(parents=True, exist_ok=True)
                Path(command[-1]).touch()

            started = time.monotonic()
            with patch.object(pitch_track, "probe_duration", return_value=5.0), patch.object(
                pitch_track, "separate_stems", return_value=(vocals, instrumental)
            ), patch.object(pitch_track, "_run", side_effect=create_output), patch.object(
                pitch_track, "analyze_wav", return_value=minimal_pitch
            ), patch.object(
                pitch_track,
                "run_v2_analysis",
                return_value=("v2/output/take_analysis.json", "v2/reports/analysis_report.md"),
            ), patch.object(
                pitch_track, "SPECTRAL_EXPORTER", hanging_exporter
            ), patch.object(
                pitch_track, "SPECTRAL_EXPORT_TIMEOUT_SECONDS", 1.0
            ):
                result = pitch_track.analyze(
                    root / "take.wav",
                    job_dir,
                    performer_name="Test Singer",
                    comparison_enabled=False,
                    export_spectral_enabled=True,
                    stage_file=job_dir / "stage.json",
                )

            self.assertLess(time.monotonic() - started, 3.0)
            marker = json.loads((job_dir / "hang-started.json").read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(marker["pid"], 0)
            self.assertEqual(result["spectral"]["status"], "unavailable")
            self.assertEqual(
                result["spectral"]["sources"]["vocals"],
                {"status": "unavailable", "reason": "spectral_export_failed"},
            )
            self.assertEqual(
                json.loads((job_dir / "stage.json").read_text())["stage"],
                "building_report",
            )
            self.assertTrue((job_dir / "result.json").is_file())
            self.assertFalse((job_dir / "analysis.wav").exists())
            spectral_dir = job_dir / "spectral" / "vocals"
            self.assertFalse(spectral_dir.exists())
            self.assertFalse(
                spectral_dir.with_name(spectral_dir.name + ".tmp").exists()
            )
            self.assertNotIn("hanging_exporter", json.dumps(result))

    def test_spectral_export_yields_to_outer_job_deadline(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(
            pitch_track.time, "monotonic", return_value=100.0
        ), patch.object(pitch_track, "_run_spectral_export") as exporter:
            result = pitch_track._maybe_export_spectral(
                True,
                Path(folder) / "analysis.wav",
                Path(folder) / "spectral" / "vocals",
                Path(folder),
                {"rate_hz": 10, "values": [0.0]},
                "vocals",
                analysis_deadline=(
                    100.0 + pitch_track.SPECTRAL_FINALIZATION_RESERVE_SECONDS
                ),
            )
        exporter.assert_not_called()
        self.assertEqual(
            result,
            {"status": "unavailable", "reason": "spectral_export_failed"},
        )

    def test_malformed_spectral_timeout_falls_back_without_import_failure(self):
        with patch.dict(
            os.environ, {"VOX_SPECTRAL_EXPORT_TIMEOUT": "not-a-number"}
        ):
            self.assertEqual(
                pitch_track._bounded_timeout_env(
                    "VOX_SPECTRAL_EXPORT_TIMEOUT", 300.0
                ),
                300.0,
            )

    def test_temporary_audio_cleanup_cannot_fail_completed_analysis(self):
        with patch.object(
            Path, "unlink", side_effect=PermissionError("cleanup denied")
        ):
            pitch_track._unlink_temporary_audio(Path("optional-analysis.wav"))

    def test_original_spectral_input_is_retained_for_deferred_export(self):
        minimal_pitch = {
            "contour": {"rate_hz": 10, "values": [0.0], "confidence": [0.9]},
            "quality": {"classification": "reliable", "flags": []},
        }
        with tempfile.TemporaryDirectory() as folder:
            job_dir = Path(folder) / "job"
            job_dir.mkdir()
            reference = Path(folder) / "reference.mp3"
            vocals = Path(folder) / "vocals.wav"
            instrumental = Path(folder) / "instrumental.wav"
            reference.touch()
            vocals.touch()
            instrumental.touch()

            def create_output(command, _error_code):
                Path(command[-1]).parent.mkdir(parents=True, exist_ok=True)
                Path(command[-1]).touch()

            def export_before_unlink(
                wav_path, output_dir, _contour, _source, _timeout_seconds
            ):
                self.assertTrue(wav_path.is_file())
                output_dir.mkdir(parents=True)
                (output_dir / "descriptor.json").write_text("{}", encoding="utf-8")
                (output_dir / "harmonic-tracks.json").write_text("{}", encoding="utf-8")
                return {"harmonic_tracks_file": "harmonic-tracks.json", "tiles": []}

            with patch.object(pitch_track, "probe_duration", return_value=5.0), patch.object(
                pitch_track, "separate_stems", return_value=(vocals, instrumental)
            ), patch.object(pitch_track, "_run", side_effect=create_output), patch.object(
                pitch_track, "analyze_wav", return_value=minimal_pitch
            ), patch.object(
                pitch_track, "run_v2_analysis", return_value=("v2/output/original_analysis.json", "v2/reports/original_report.md")
            ), patch.object(
                pitch_track, "_run_spectral_export", side_effect=export_before_unlink
            ):
                result = pitch_track.analyze_original(
                    reference,
                    job_dir,
                    "Original Artist",
                    export_spectral_enabled=True,
                )

            pending = result.pop("_spectral_input")
            self.assertNotIn("spectral", result)
            self.assertTrue(pending["wav_path"].is_file())
            with patch.object(
                pitch_track,
                "_run_spectral_export",
                side_effect=export_before_unlink,
            ):
                spectral = pitch_track._maybe_export_spectral(
                    True,
                    pending["wav_path"],
                    job_dir / "spectral" / "original",
                    job_dir,
                    pending["contour"],
                    "original",
                )
            self.assertEqual(spectral["status"], "ready")
            pending["wav_path"].unlink()
            self.assertFalse((job_dir / "reference" / "analysis.wav").exists())

    def test_spectral_failure_stays_isolated_when_private_log_cannot_be_written(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(
            pitch_track, "_run_spectral_export", side_effect=OSError("disk full")
        ), patch.object(Path, "write_text", side_effect=OSError("disk full")):
            result = pitch_track._maybe_export_spectral(
                True,
                Path(folder) / "analysis.wav",
                Path(folder) / "spectral",
                Path(folder),
                {"rate_hz": 10, "values": []},
                "vocals",
            )
        self.assertEqual(result, {"status": "unavailable", "reason": "spectral_export_failed"})


if __name__ == "__main__":
    unittest.main()
