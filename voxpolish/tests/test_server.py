"""Editor server tests: the three disaster contracts, exercised over HTTP."""

import json
import time

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from voxpolish.server.app import create_app
from voxpolish.server.session import Session


@pytest.fixture()
def session_dir(speech_signal, tmp_path):
    mono, sr, _ = speech_signal
    src = tmp_path / "talk.wav"
    sf.write(src, mono, sr)
    root = tmp_path / "talk_session"
    Session.create(src, root)
    return src, root


@pytest.fixture()
def client(session_dir):
    _, root = session_dir
    return TestClient(create_app(root))


def _wait_render(client, timeout=30.0):
    start = time.time()
    while time.time() - start < timeout:
        s = client.get("/api/render").json()
        if s["status"] in ("done", "error"):
            return s
        time.sleep(0.05)
    raise TimeoutError


# ----------------------------------------------------- disaster 1: data loss


def test_original_file_is_never_touched(session_dir):
    src, root = session_dir
    before = src.read_bytes()
    session = Session(root)
    doc = session.document()
    doc.pauses = []
    session.update_document(doc.to_json(), expected_revision=session.revision())
    session.render()
    assert src.read_bytes() == before, "the user's original file changed"


def test_history_snapshot_on_every_accepted_edit(client, session_dir):
    _, root = session_dir
    d = client.get("/api/document").json()
    d["document"]["pauses"] = []
    r = client.put("/api/document", json={"revision": d["revision"], "document": d["document"]})
    assert r.status_code == 200
    snaps = sorted((root / "history").glob("doc-*.json"))
    assert snaps, "no history snapshot written"
    old = json.loads(snaps[-1].read_text())
    assert old["pauses"], "snapshot must contain the pre-edit document"


# -------------------------------------------------- disaster 2: editor lies


def test_stale_revision_is_rejected(client):
    d = client.get("/api/document").json()
    ok = client.put("/api/document", json={"revision": d["revision"], "document": d["document"]})
    assert ok.status_code == 200
    stale = client.put("/api/document", json={"revision": d["revision"], "document": d["document"]})
    assert stale.status_code == 409, "stale write must be rejected, not clobber"


def test_invalid_document_is_rejected(client):
    d = client.get("/api/document").json()
    broken = dict(d["document"])
    broken["pauses"] = [{"nonsense": True}]
    r = client.put("/api/document", json={"revision": d["revision"], "document": broken})
    assert r.status_code == 422


def test_render_reflects_the_persisted_document(client, session_dir):
    _, root = session_dir
    before = (root / "vocal_cleaned.wav").read_bytes()

    d = client.get("/api/document").json()
    assert d["document"]["pauses"], "fixture must have pauses to remove"
    d["document"]["pauses"] = []
    client.put("/api/document", json={"revision": d["revision"], "document": d["document"]})
    assert client.post("/api/render").status_code == 200
    assert _wait_render(client)["status"] == "done"

    after = (root / "vocal_cleaned.wav").read_bytes()
    assert after != before, "render must reflect the edited document"


# ----------------------------------------------- disaster 3: session melts


def test_second_render_gets_clean_busy(client):
    first = client.post("/api/render")
    assert first.status_code == 200
    second = client.post("/api/render")
    # Either the first finished already (tiny fixture) or we get a clean 409.
    assert second.status_code in (200, 409)
    _wait_render(client)


def test_peaks_are_small_and_shaped(client):
    p = client.get("/api/peaks/original").json()
    assert len(p["min"]) == len(p["max"]) <= 2400
    assert p["duration"] > 0 and p["sample_rate"] > 0


def test_audio_supports_range_requests(client):
    r = client.get("/api/audio/cleaned", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206
    assert len(r.content) == 100


def test_unknown_audio_is_404(client):
    assert client.get("/api/audio/master").status_code == 404
    assert client.get("/api/peaks/master").status_code == 404


# ------------------------------------------------------------ session basics


def test_session_survives_reopen(session_dir):
    _, root = session_dir
    assert Session.is_session(root)
    s = Session(root)
    doc = s.document()
    assert doc.duration > 0
    assert s.revision() >= 1
