"""Fused web app tests — full job lifecycle over HTTP with fake engines."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from voxsuite.server.app import create_app
from test_orchestrator import FakeEngines


def _client(tmp):
    return TestClient(create_app(Path(tmp) / "base", engines=FakeEngines()))


def test_deck_serves_versioned_kit_wired():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        r = c.get("/deck")
        assert r.status_code == 200
        assert r.headers.get("cache-control") == "no-cache"
        assert "__ASSET_VERSION__" not in r.text
        for hook in ("vox-command", "vox-chain", "vox-scope", "vox-tray", "vox-procbar"):
            assert hook in r.text, hook
        assert "/static/vox-telemetry.js?v=" in r.text
        assert c.get("/static/vox-telemetry.js").status_code == 200
        # the shared "What this does" guide, wired to Fused mode
        assert "/static/vox-about.js?v=" in r.text and 'VOX_MODE="fused"' in r.text
        assert c.get("/static/vox-about.js").status_code == 200
        # in-browser recorder (Upload | Record)
        assert 'id="modeRecord"' in r.text and 'id="recMount"' in r.text
        assert "/static/vox-record.js?v=" in r.text and c.get("/static/vox-record.js").status_code == 200
        # "New take" — clears the fused deck so a fresh upload/recording can start
        assert 'id="newBtn"' in r.text and "function resetDeck" in r.text
        from voxsuite.server.app import _ALLOWED
        assert ".webm" in _ALLOWED


def test_full_fused_lifecycle_over_http():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        r = c.post("/api/fused-jobs",
                   data={"name": "Ada", "tune": "true"},
                   files={"file": ("take.wav", b"RIFF-bytes", "audio/wav")})
        assert r.status_code == 202
        jid = r.json()["id"]
        assert jid.startswith("fused_")
        status = None
        for _ in range(200):
            status = c.get(f"/api/fused-jobs/{jid}").json()
            if status["status"] in ("complete", "failed"):
                break
            time.sleep(0.02)
        assert status["status"] == "complete"
        assert status["stage"] == "export" and status["progress"] == 100
        assert status["analysis"]["score"]["overall"] == 7.4
        assert status["polish"]["revision"] == 1
        # both deliverables downloadable
        assert c.get(f"/api/fused-jobs/{jid}/report").status_code == 200
        assert c.get(f"/api/fused-jobs/{jid}/download").status_code == 200


def test_cross_mode_tabs_serve_html_never_json_download():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        for other in ("/polish", "/analyze"):
            r = c.get(other)
            assert "text/html" in r.headers["content-type"], other
        assert c.get("/fused").status_code == 200  # own mode → deck


def test_rejects_unsupported_upload():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        r = c.post("/api/fused-jobs", files={"file": ("notes.txt", b"hi", "text/plain")})
        assert r.status_code == 415


def test_unknown_job_is_404():
    with tempfile.TemporaryDirectory() as tmp:
        assert _client(tmp).get("/api/fused-jobs/nope").status_code == 404
