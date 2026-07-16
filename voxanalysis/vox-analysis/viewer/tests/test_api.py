from __future__ import annotations

import importlib.util
import asyncio
import json
import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import httpx


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ["VOX_PITCH_RUNTIME"] = cls.temp.name
        app_path = Path(__file__).parents[1] / "app.py"
        spec = importlib.util.spec_from_file_location("pitch_viewer_app", app_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        cls.module = module
        cls.app = module.app

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_health_checks_media_tools(self):
        response = self.request("GET", "/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertTrue(response.json()["checks"]["voxai_v2"])
        self.assertIn("reference_lookup", response.json()["checks"])

    def test_rejects_unsupported_extension(self):
        response = self.request("POST", "/api/pitch-jobs", files={"file": ("notes.txt", b"hello", "text/plain")})
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["detail"]["code"], "unsupported_media")

    def test_single_track_job_preserves_optional_song_metadata(self):
        probe = type("Probe", (), {"returncode": 0, "stdout": "12.5"})()
        with patch.object(self.module.subprocess, "run", return_value=probe), patch.object(
            self.module.executor, "submit"
        ) as submit:
            response = self.request(
                "POST",
                "/api/pitch-jobs",
                data={
                    "name": "Test Singer",
                    "song": "Original Song",
                    "artist": "Test Composer",
                    "comparison": "false",
                },
                files={"file": ("take.wav", b"RIFF-test", "audio/wav")},
            )
        self.assertEqual(response.status_code, 202)
        manifest = self.module._read_manifest(Path(self.temp.name) / response.json()["id"])
        self.assertFalse(manifest["comparison_enabled"])
        self.assertEqual(manifest["song_name"], "Original Song")
        self.assertEqual(manifest["original_artist"], "Test Composer")
        submit.assert_called_once()

    def test_comparison_job_still_requires_song_and_artist(self):
        probe = type("Probe", (), {"returncode": 0, "stdout": "12.5"})()
        with patch.object(self.module.subprocess, "run", return_value=probe), patch.object(
            self.module.executor, "submit"
        ) as submit:
            response = self.request(
                "POST",
                "/api/pitch-jobs",
                data={"name": "Test Singer", "comparison": "true"},
                files={"file": ("take.wav", b"RIFF-test", "audio/wav")},
            )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "missing_song_metadata")
        submit.assert_not_called()

    def test_unknown_job_is_not_found(self):
        response = self.request("GET", "/api/pitch-jobs/00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, 404)

    def test_serves_separated_playback_tracks(self):
        job_dir = Path(self.temp.name) / str(uuid.uuid4())
        job_dir.mkdir()
        manifest = {"id": job_dir.name, "status": "complete", "updated_at": time.time()}
        (job_dir / "job.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
        (job_dir / "vocals.mp3").write_bytes(b"vocal")
        (job_dir / "instrumental.mp3").write_bytes(b"music")
        vocals = asyncio.run(self.module.get_audio(job_dir.name, "vocals"))
        backing = asyncio.run(self.module.get_audio(job_dir.name, "instrumental"))
        self.assertEqual(Path(vocals.path).name, "vocals.mp3")
        self.assertEqual(Path(backing.path).name, "instrumental.mp3")
        self.assertEqual(vocals.media_type, "audio/mpeg")
        self.assertEqual(backing.media_type, "audio/mpeg")

    def test_routine_cleanup_preserves_active_job(self):
        job_dir = Path(self.temp.name) / str(uuid.uuid4())
        job_dir.mkdir()
        manifest = {"id": job_dir.name, "status": "processing", "updated_at": time.time()}
        (job_dir / "job.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
        self.module._cleanup()
        current = self.module._read_manifest(job_dir)
        self.assertEqual(current["status"], "processing")

    def test_processing_job_exposes_current_v2_stage(self):
        job_dir = Path(self.temp.name) / str(uuid.uuid4())
        job_dir.mkdir()
        manifest = {"id": job_dir.name, "status": "processing", "stage": "separating_vocals", "updated_at": time.time()}
        (job_dir / "job.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
        (job_dir / "stage.json").write_text('{"stage":"running_v2_analysis"}', encoding="utf-8")
        response = self.request("GET", f"/api/pitch-jobs/{job_dir.name}")
        self.assertEqual(response.json()["stage"], "running_v2_analysis")

    def test_serves_generated_v2_report(self):
        job_dir = Path(self.temp.name) / str(uuid.uuid4())
        reports = job_dir / "v2" / "reports"
        reports.mkdir(parents=True)
        manifest = {"id": job_dir.name, "status": "complete", "updated_at": time.time()}
        (job_dir / "job.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
        (reports / "analysis_report.md").write_text("# VOXAI V2", encoding="utf-8")
        response = self.request("GET", f"/api/pitch-jobs/{job_dir.name}/report")
        self.assertEqual(response.status_code, 200)
        self.assertIn("VOXAI V2", response.text)

    def test_v2_report_hides_private_job_path(self):
        job_dir = Path(self.temp.name) / str(uuid.uuid4())
        reports = job_dir / "v2" / "reports"
        reports.mkdir(parents=True)
        manifest = {"id": job_dir.name, "status": "complete", "updated_at": time.time()}
        (job_dir / "job.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
        (reports / "analysis_report.md").write_text(f"Plot: {job_dir}/private.png", encoding="utf-8")
        response = self.request("GET", f"/api/pitch-jobs/{job_dir.name}/report")
        self.assertNotIn(str(job_dir), response.text)
        self.assertIn("[private job artifact]", response.text)

    def make_spectral_job(self, *, source="vocals", descriptor_tile_file="tile-000.png"):
        job_dir = Path(self.temp.name) / str(uuid.uuid4())
        source_dir = job_dir / "spectral" / source
        source_dir.mkdir(parents=True)
        descriptor = {
            "version": "voxai_spectral_v1",
            "source": source,
            "transform": "librosa.cqt",
            "display_only": True,
            "fps": 21.533203125,
            "midi_lo": 36,
            "midi_hi": 96,
            "n_bins": 180,
            "harmonic_tracks_file": "harmonic-tracks.json",
            "private_path": str(job_dir / "must-not-leak"),
            "tiles": [{
                "index": 0,
                "file": descriptor_tile_file,
                "frame_start": 0,
                "frame_count": 1,
                "width": 1,
                "height": 180,
                "private_path": str(job_dir / "must-not-leak"),
            }],
        }
        (source_dir / "descriptor.json").write_text(json.dumps(descriptor), encoding="utf-8")
        (source_dir / "harmonic-tracks.json").write_text(json.dumps({
            "version": "voxai_spectral_v1",
            "rate_hz": 10,
            "t0": 0,
            "units": "db_relative_to_strongest_available_harmonic_per_frame",
            "values": {f"H{number}": [0.0] for number in range(1, 9)},
            "private_path": str(job_dir / "must-not-leak"),
        }), encoding="utf-8")
        (source_dir / "tile-000.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        manifest = {
            "id": job_dir.name,
            "status": "complete",
            "stage": "complete",
            "updated_at": time.time(),
            "result": {"spectral": {
                "version": "voxai_spectral_v1",
                "status": "ready",
                "sources": {source: {
                    "status": "ready",
                    "descriptor_file": f"spectral/{source}/descriptor.json",
                    "harmonic_tracks_file": f"spectral/{source}/harmonic-tracks.json",
                    "tile_count": 1,
                    "artifact_bytes": 123,
                }},
            }},
        }
        (job_dir / "job.json").write_text(json.dumps(manifest), encoding="utf-8")
        return job_dir

    def test_serves_allowlisted_spectral_descriptor_tracks_and_tile(self):
        job_dir = self.make_spectral_job()
        job = self.request("GET", f"/api/pitch-jobs/{job_dir.name}")
        public_source = job.json()["result"]["spectral"]["sources"]["vocals"]
        self.assertNotIn("descriptor_file", public_source)
        self.assertNotIn("harmonic_tracks_file", public_source)
        self.assertEqual(
            public_source["descriptor_url"],
            f"/api/pitch-jobs/{job_dir.name}/spectral/vocals/descriptor",
        )

        descriptor = self.request("GET", public_source["descriptor_url"])
        self.assertEqual(descriptor.status_code, 200)
        self.assertTrue(descriptor.json()["display_only"])
        self.assertNotIn("private_path", descriptor.json())
        self.assertNotIn("file", descriptor.json()["tiles"][0])
        self.assertEqual(
            descriptor.json()["tiles"][0]["url"],
            f"/api/pitch-jobs/{job_dir.name}/spectral/vocals/tiles/0",
        )
        self.assertIn("private", descriptor.headers["cache-control"])

        tracks = self.request("GET", public_source["harmonic_tracks_url"])
        self.assertEqual(tracks.status_code, 200)
        self.assertEqual(set(tracks.json()["values"]), {f"H{number}" for number in range(1, 9)})
        self.assertNotIn("private_path", tracks.json())

        tile = self.request("GET", descriptor.json()["tiles"][0]["url"])
        self.assertEqual(tile.status_code, 200)
        self.assertEqual(tile.headers["content-type"], "image/png")
        self.assertEqual(tile.content, b"\x89PNG\r\n\x1a\nfixture")

    def test_spectral_endpoint_rejects_unknown_source_and_tile(self):
        job_dir = self.make_spectral_job()
        bad_source = self.request(
            "GET", f"/api/pitch-jobs/{job_dir.name}/spectral/../../descriptor"
        )
        self.assertIn(bad_source.status_code, {404, 405})
        unknown_source = self.request(
            "GET", f"/api/pitch-jobs/{job_dir.name}/spectral/mix/descriptor"
        )
        self.assertEqual(unknown_source.status_code, 404)
        unknown_tile = self.request(
            "GET", f"/api/pitch-jobs/{job_dir.name}/spectral/vocals/tiles/9"
        )
        self.assertEqual(unknown_tile.status_code, 404)

    def test_serves_original_spectral_source_through_same_allowlist(self):
        job_dir = self.make_spectral_job(source="original")
        response = self.request(
            "GET", f"/api/pitch-jobs/{job_dir.name}/spectral/original/descriptor"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "original")
        self.assertIn("/spectral/original/tiles/0", response.json()["tiles"][0]["url"])

    def test_spectral_descriptor_rejects_traversal_filename(self):
        job_dir = self.make_spectral_job(descriptor_tile_file="../secret.png")
        (job_dir / "spectral" / "secret.png").write_bytes(b"secret")
        response = self.request(
            "GET", f"/api/pitch-jobs/{job_dir.name}/spectral/vocals/tiles/0"
        )
        self.assertEqual(response.status_code, 500)
        self.assertNotEqual(response.content, b"secret")

    def test_spectral_endpoint_requires_complete_ready_job(self):
        job_dir = self.make_spectral_job()
        manifest = self.module._read_manifest(job_dir)
        manifest["status"] = "processing"
        self.module._write_manifest(job_dir, manifest)
        response = self.request(
            "GET", f"/api/pitch-jobs/{job_dir.name}/spectral/vocals/descriptor"
        )
        self.assertEqual(response.status_code, 409)

    def test_cleanup_removes_expired_spectral_artifacts_with_job(self):
        job_dir = self.make_spectral_job()
        manifest = self.module._read_manifest(job_dir)
        manifest["updated_at"] = time.time() - self.module.JOB_TTL_SECONDS - 10
        (job_dir / "job.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.module._cleanup()
        self.assertFalse(job_dir.exists())

    def test_viewer_worker_enables_export_with_outer_deadline(self):
        job_dir = Path(self.temp.name) / str(uuid.uuid4())
        job_dir.mkdir()
        (job_dir / "upload.wav").touch()
        self.module._write_manifest(job_dir, {
            "id": job_dir.name,
            "status": "queued",
            "stage": "queued",
            "upload_file": "upload.wav",
            "comparison_enabled": False,
        })
        failed = type("Result", (), {"returncode": 2, "stdout": "analysis_failed", "stderr": ""})()
        with patch.object(
            self.module.time, "monotonic", return_value=1_000.0
        ), patch.object(self.module.subprocess, "run", return_value=failed) as run:
            self.module._process(job_dir.name)
        command = run.call_args.args[0]
        self.assertIn("--export-spectral", command)
        self.assertIn("--skip-comparison", command)
        deadline_index = command.index("--analysis-deadline-monotonic") + 1
        self.assertEqual(
            float(command[deadline_index]), 1_000.0 + self.module.ANALYSIS_TIMEOUT
        )
        self.assertEqual(run.call_args.kwargs["timeout"], self.module.ANALYSIS_TIMEOUT)

    def test_deck_shell_serves_command_deck(self):
        """The unified command deck is served, version-stamped, kit-wired."""
        response = self.request("GET", "/deck")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("cache-control"), "no-cache")
        body = response.text
        self.assertNotIn("__ASSET_VERSION__", body)  # version injected
        for hook in ("vox-command", "vox-chain", "vox-deck", "vox-tray", "vox-procbar"):
            self.assertIn(hook, body, f"missing kit component: {hook}")
        self.assertIn("/static/vox-telemetry.js?v=", body)

    def test_shared_telemetry_js_is_served(self):
        response = self.request("GET", "/static/vox-telemetry.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response.headers["content-type"])
        self.assertIn("adaptViewer", response.text)

    def test_static_route_still_rejects_traversal(self):
        self.assertEqual(self.request("GET", "/static/app.py").status_code, 404)

    @classmethod
    def request(cls, method, path, **kwargs):
        async def send():
            transport = httpx.ASGITransport(app=cls.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(send())


if __name__ == "__main__":
    unittest.main()
