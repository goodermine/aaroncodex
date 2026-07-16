"""Upload flow, Clean vs Clean+AutoTune choice, and path safety."""

import io
import time

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from voxpolish.server.app import create_app
from voxpolish.server.workspace import Workspace, safe_stem

SR = 44100


def _wav_bytes(seconds=3.0, freq=220.0):
    t = np.arange(int(seconds * SR)) / SR
    x = (0.2 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, x, SR, format="WAV")
    return buf.getvalue()


@pytest.fixture()
def workspace_client(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    return TestClient(create_app(root))


def _run_upload(client, data, filename="take.wav", tune=None):
    files = {"file": (filename, data, "audio/wav")}
    form = {} if tune is None else {"tune": "true" if tune else "false"}
    r = client.post("/api/uploads", files=files, data=form)
    return r


def _await_job(client, job_id, timeout=60.0):
    start = time.time()
    while time.time() - start < timeout:
        s = client.get(f"/api/uploads/{job_id}").json()
        if s["status"] in ("done", "error"):
            return s
        time.sleep(0.1)
    raise TimeoutError


# ---------------------------------------------------------------- landing


def test_empty_workspace_reports_no_current(workspace_client):
    assert workspace_client.get("/api/workspace").json()["current"] is None
    # Editor routes 409 so the client shows the upload screen.
    assert workspace_client.get("/api/session").status_code == 409
    assert workspace_client.get("/api/document").status_code == 409


def test_upload_creates_session_and_becomes_current(workspace_client):
    r = _run_upload(workspace_client, _wav_bytes(), tune=True)
    assert r.status_code == 200, r.text
    job = _await_job(workspace_client, r.json()["id"])
    assert job["status"] == "done", job
    assert job["session_id"]
    # Now current, and the editor loads.
    assert workspace_client.get("/api/workspace").json()["current"] == job["session_id"]
    assert workspace_client.get("/api/session").status_code == 200


def test_upload_choice_tune_enables_tune(workspace_client):
    job = _await_job(workspace_client, _run_upload(workspace_client, _wav_bytes(), tune=True).json()["id"])
    doc = workspace_client.get("/api/document").json()["document"]
    assert doc["bypass"].get("tune") in (False, None)


def test_upload_choice_clean_only_bypasses_tune(workspace_client):
    job = _await_job(workspace_client, _run_upload(workspace_client, _wav_bytes(), tune=False).json()["id"])
    doc = workspace_client.get("/api/document").json()["document"]
    assert doc["bypass"].get("tune") is True


def test_default_choice_is_tune(workspace_client):
    """No tune field posted -> defaults to Clean + Auto Tune."""
    job = _await_job(workspace_client, _run_upload(workspace_client, _wav_bytes()).json()["id"])
    doc = workspace_client.get("/api/document").json()["document"]
    assert doc["bypass"].get("tune") in (False, None)


# ------------------------------------------------------------ validation


def test_invalid_extension_is_rejected(workspace_client):
    r = _run_upload(workspace_client, b"not audio", filename="malware.exe", tune=True)
    assert r.status_code == 422
    assert "unsupported" in r.json()["detail"].lower()


def test_undecodable_audio_reports_error_to_ui(workspace_client):
    # Right extension, garbage bytes: the decode error must reach the job.
    r = _run_upload(workspace_client, b"RIFFgarbage-not-a-wav", filename="broken.wav", tune=True)
    assert r.status_code == 200
    job = _await_job(workspace_client, r.json()["id"])
    assert job["status"] == "error"
    assert job["error"]


def test_empty_upload_is_rejected(workspace_client):
    r = _run_upload(workspace_client, b"", filename="empty.wav", tune=True)
    assert r.status_code == 422


# ------------------------------------------------------------ path safety


def test_safe_stem_strips_paths_and_traversal():
    assert "/" not in safe_stem("../../etc/passwd.wav")
    assert ".." not in safe_stem("..")
    assert safe_stem("/abs/path/song.mp3") == "song"
    assert safe_stem("") == "audio"


def test_session_id_traversal_is_rejected(tmp_path):
    ws = Workspace(tmp_path / "ws")
    for bad in ("..", "../evil", "a/b", "/etc"):
        with pytest.raises(KeyError):
            ws._session_dir(bad)
    assert ws.get("../evil") is None


def test_select_unknown_session_404(workspace_client):
    assert workspace_client.post("/api/session/nope/select").status_code == 404


def test_uploaded_session_is_selectable(workspace_client):
    job = _await_job(workspace_client, _run_upload(workspace_client, _wav_bytes()).json()["id"])
    sid = job["session_id"]
    assert workspace_client.post(f"/api/session/{sid}/select").status_code == 200
    assert workspace_client.get("/api/session").json()["id"] == sid


# ------------------------------------------------------ navigation assets


def test_editor_serves_navigation_and_upload_affordances(workspace_client):
    """Nav/upload UI is client-side JS; guard the served assets don't regress."""
    page = workspace_client.get("/").text
    for hook in ("landing", "scrollbar", "new-upload", "start-upload", 'name="tune"',
                 "download", "pitch-panel"):
        assert hook in page, f"missing UI hook: {hook}"
    js = workspace_client.get("/static/app.js").text
    for hook in ("mousedown", "drawScrollbar", "startUpload", "panBy",
                 "markManualPan", "drawPitch"):
        assert hook in js, f"missing JS behavior: {hook}"


def test_polish_command_deck_serves(workspace_client):
    """The unified command deck (Polish mode) is served, version-stamped, kit-wired."""
    r = workspace_client.get("/deck")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-cache"
    page = r.text
    assert "__ASSET_VERSION__" not in page  # version injected
    for hook in ("vox-command", "vox-chain", "vox-module", "vox-scope", "vox-tray", "vox-procbar"):
        assert hook in page, f"missing kit component: {hook}"
    assert "/static/vox-telemetry.js?v=" in page
    telem = workspace_client.get("/static/vox-telemetry.js")
    assert telem.status_code == 200 and "adaptPolish" in telem.text
    # the shared "What this does" guide, wired to Polish mode
    assert "/static/vox-about.js?v=" in page and 'VOX_MODE="polish"' in page
    assert workspace_client.get("/static/vox-about.js").status_code == 200


def test_peaks_expose_duration_for_navigation(workspace_client):
    _await_job(workspace_client, _run_upload(workspace_client, _wav_bytes(seconds=4.0)).json()["id"])
    peaks = workspace_client.get("/api/peaks/original").json()
    assert peaks["duration"] > 3.5
    assert len(peaks["min"]) == len(peaks["max"]) <= 2400


# ---------------------------------------------------------------- download


def test_download_serves_rendered_wav_as_attachment(workspace_client):
    _await_job(workspace_client,
               _run_upload(workspace_client, _wav_bytes(), filename="my song.wav").json()["id"])
    r = workspace_client.get("/api/download")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    disp = r.headers.get("content-disposition", "")
    assert "attachment" in disp
    # Friendly filename derived from the upload, safely, plus a tag. Spaces get
    # RFC 5987 percent-encoded, so normalize before checking.
    assert "voxpolish" in disp and ".wav" in disp
    assert "my" in disp.replace("%20", " ")
    assert r.content[:4] == b"RIFF"  # a real WAV


def test_download_reflects_the_current_render(workspace_client):
    _await_job(workspace_client, _run_upload(workspace_client, _wav_bytes()).json()["id"])
    before = workspace_client.get("/api/download").content

    # Bypass every module and re-render → the download changes.
    d = workspace_client.get("/api/document").json()
    doc = d["document"]
    doc["bypass"] = {k: True for k in ("dynamics", "gate", "breath", "sibilance", "tune")}
    workspace_client.put("/api/document", json={"revision": d["revision"], "document": doc})
    workspace_client.post("/api/render")
    while workspace_client.get("/api/render").json()["status"] == "running":
        time.sleep(0.05)
    after = workspace_client.get("/api/download").content
    assert after != before


def test_download_without_session_is_409(workspace_client):
    assert workspace_client.get("/api/download").status_code == 409
