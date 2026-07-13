from __future__ import annotations

import importlib.util
import asyncio
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

    @classmethod
    def request(cls, method, path, **kwargs):
        async def send():
            transport = httpx.ASGITransport(app=cls.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(send())


if __name__ == "__main__":
    unittest.main()
