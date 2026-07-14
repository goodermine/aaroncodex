from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image


EXPORTER_PATH = Path(__file__).parents[2] / "voxai-local-analysis" / "spectral_export.py"
SPEC = importlib.util.spec_from_file_location("spectral_export", EXPORTER_PATH)
spectral_export = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(spectral_export)


class SpectralGroundTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.sample_rate = 44_100
        cls.duration = 2.0
        cls.onset = 0.35
        times = np.arange(round(cls.sample_rate * cls.duration)) / cls.sample_rate
        local_time = np.maximum(0.0, times - cls.onset)
        active = (times >= cls.onset) & (times < 1.75)
        signal = np.zeros_like(times)
        for harmonic in range(1, 9):
            amplitude = 10 ** (-(harmonic - 1) * 3.0 / 20.0)
            signal += active * amplitude * np.sin(2 * np.pi * 220.0 * harmonic * local_time)
        fade_samples = round(0.02 * cls.sample_rate)
        onset_index = round(cls.onset * cls.sample_rate)
        offset_index = round(1.75 * cls.sample_rate)
        signal[onset_index : onset_index + fade_samples] *= np.linspace(0, 1, fade_samples)
        signal[offset_index - fade_samples : offset_index] *= np.linspace(1, 0, fade_samples)
        signal *= 0.8 / max(np.max(np.abs(signal)), 1e-9)
        cls.wav_path = cls.root / "a3-harmonics.wav"
        sf.write(cls.wav_path, signal, cls.sample_rate, subtype="PCM_24")

        rate_hz = 10.0
        contour = {
            "rate_hz": rate_hz,
            "units": "cents_rel_A440",
            "values": [
                -1200.0 if cls.onset <= index / rate_hz < 1.75 else None
                for index in range(math.ceil(cls.duration * rate_hz))
            ],
        }
        cls.contour = contour
        cls.output_dir = cls.root / "spectral"
        cls.descriptor = spectral_export.export_spectral(
            cls.wav_path,
            cls.output_dir,
            contour,
            "vocals",
        )
        cls.images = [
            np.asarray(Image.open(cls.output_dir / tile["file"]))
            for tile in cls.descriptor["tiles"]
        ]
        cls.pixels = np.concatenate(cls.images, axis=1)
        cls.harmonics = json.loads(
            (cls.output_dir / cls.descriptor["harmonic_tracks_file"]).read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_descriptor_and_grayscale_tiles_are_self_consistent(self):
        descriptor = self.descriptor
        self.assertEqual(descriptor["version"], "voxai_spectral_v1")
        self.assertTrue(descriptor["display_only"])
        self.assertEqual(descriptor["transform"], "librosa.cqt")
        self.assertAlmostEqual(descriptor["fps"], 44_100 / 2_048)
        self.assertEqual(descriptor["midi_lo"], 36.0)
        self.assertEqual(descriptor["midi_hi"], 96.0)
        self.assertTrue(descriptor["midi_hi_exclusive"])
        self.assertEqual(descriptor["bins_per_semitone"], 3)
        self.assertEqual(descriptor["n_bins"], 180)
        self.assertEqual(descriptor["row_order"], "high_to_low")
        self.assertEqual(descriptor["db_floor"], -80.0)
        self.assertEqual(descriptor["db_ceil"], 0.0)
        self.assertEqual(self.pixels.dtype, np.uint8)
        self.assertEqual(self.pixels.shape, (180, descriptor["total_frames"]))
        self.assertEqual(sum(tile["frame_count"] for tile in descriptor["tiles"]), descriptor["total_frames"])
        self.assertTrue(all(tile["width"] <= 2_048 for tile in descriptor["tiles"]))
        self.assertTrue(all(image.ndim == 2 for image in self.images))

    def test_child_process_cli_writes_the_production_descriptor_contract(self):
        output_dir = self.root / "spectral-cli"
        completed = subprocess.run(
            [
                sys.executable,
                str(EXPORTER_PATH),
                str(self.wav_path),
                str(output_dir),
                "vocals",
            ],
            input=json.dumps(self.contour),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        descriptor = json.loads(
            (output_dir / "descriptor.json").read_text(encoding="utf-8")
        )
        self.assertEqual(descriptor["version"], "voxai_spectral_v1")
        self.assertEqual(descriptor["source"], "vocals")
        self.assertTrue(descriptor["display_only"])
        self.assertTrue((output_dir / descriptor["harmonic_tracks_file"]).is_file())

    def test_time_and_harmonic_mapping_match_known_a3_series(self):
        fps = self.descriptor["fps"]
        threshold = round((-20.0 - self.descriptor["db_floor"]) / 80.0 * 255.0)
        visible_columns = np.flatnonzero(np.max(self.pixels, axis=0) >= threshold)
        self.assertTrue(len(visible_columns))
        measured_onset = visible_columns[0] / fps
        self.assertLessEqual(abs(measured_onset - self.onset), 1.0 / fps)

        stable_column = round(1.0 * fps)
        fundamental_midi = 57.0
        for harmonic in range(1, 9):
            expected_midi = spectral_export.harmonic_midi(fundamental_midi, harmonic)
            expected_row = spectral_export.midi_to_row(expected_midi)
            center = round(expected_row)
            start = max(0, center - 3)
            stop = min(self.pixels.shape[0], center + 4)
            local = self.pixels[start:stop, stable_column]
            measured_row = start + int(np.argmax(local))
            self.assertLessEqual(abs(measured_row - expected_row), 1.1, f"H{harmonic}")
            self.assertGreater(int(np.max(local)), 120, f"H{harmonic}")

        self.assertAlmostEqual(spectral_export.time_to_frame(1.0), fps)

    def test_harmonic_tracks_are_normalized_and_use_null_for_silence(self):
        self.assertEqual(self.harmonics["rate_hz"], 10.0)
        self.assertEqual(
            self.harmonics["units"],
            "db_relative_to_strongest_available_harmonic_per_frame",
        )
        self.assertEqual(set(self.harmonics["values"]), {f"H{number}" for number in range(1, 9)})
        self.assertTrue(all(self.harmonics["values"][key][0] is None for key in self.harmonics["values"]))
        active_values = [self.harmonics["values"][f"H{number}"][10] for number in range(1, 9)]
        self.assertTrue(all(value is not None and value <= 0 for value in active_values))
        self.assertAlmostEqual(max(active_values), 0.0, places=1)

    def test_silent_magnitude_maps_to_black_not_false_peak_energy(self):
        pixels = spectral_export._db_pixels(np.zeros((12, 20), dtype=np.float32))
        self.assertEqual(int(np.max(pixels)), 0)

    def test_four_minute_artifact_format_stays_under_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            rng = np.random.default_rng(20260713)
            frames = math.ceil(240 * 44_100 / 2_048)
            pixels = rng.integers(0, 256, size=(180, frames), dtype=np.uint8)
            tiles = spectral_export._write_tiles(pixels, folder, 44_100 / 2_048)
            tracks = {
                "rate_hz": 10,
                "values": {
                    f"H{number}": [round(-number * 2.5, 1)] * 2_400
                    for number in range(1, 9)
                },
            }
            (folder / "harmonic-tracks.json").write_text(json.dumps(tracks), encoding="utf-8")
            (folder / "descriptor.json").write_text(json.dumps({"tiles": tiles}), encoding="utf-8")
            total_bytes = sum(path.stat().st_size for path in folder.iterdir())
            self.assertLessEqual(total_bytes, 3 * 1024 * 1024)
            self.assertEqual([tile["frame_start"] for tile in tiles], [0, 2_048, 4_096])


if __name__ == "__main__":
    unittest.main()
