"""take_context upload fields: sanitised, optional, never score-bearing."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from app import _sanitise_take_context  # noqa: E402


def test_valid_fields_pass_through():
    ctx = _sanitise_take_context("learning", "live", "first run at the bridge")
    assert ctx == {"intent": "learning", "capture": "live",
                   "note": "first run at the bridge"}


def test_absent_fields_yield_none():
    assert _sanitise_take_context("", "", "") is None
    assert _sanitise_take_context("  ", None or "", "   ") is None


def test_unknown_values_are_dropped_not_stored():
    assert _sanitise_take_context("bogus", "moon", "") is None
    ctx = _sanitise_take_context("PERFORMANCE", "Home", "")
    assert ctx == {"intent": "performance", "capture": "home"}


def test_note_is_whitespace_collapsed_and_bounded():
    ctx = _sanitise_take_context("", "", "  a   lot\n of   space  " + "x" * 500)
    assert ctx["note"].startswith("a lot of space")
    assert len(ctx["note"]) <= 200


def test_viewer_requires_name_and_capture():
    """No take enters the archive anonymous or unlocated: create_job rejects a
    missing singer name or capture before touching the upload."""
    from fastapi.testclient import TestClient
    import app as viewer_app
    c = TestClient(viewer_app.app)
    wav = {"file": ("take.wav", b"RIFF0000WAVE", "audio/wav")}
    r = c.post("/api/pitch-jobs", data={"take_capture": "live"}, files=wav)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "missing_performer_name"
    r = c.post("/api/pitch-jobs", data={"name": "Rilda"}, files=wav)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "missing_take_capture"
    r = c.post("/api/pitch-jobs", data={"name": "Rilda", "take_capture": "bar"}, files=wav)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "missing_take_capture"


def test_backing_upload_is_optional_and_validated():
    """Supply-your-own-backing: a second file is accepted and recorded on the
    manifest; a bad extension is rejected; absence is fine (separation path)."""
    import json as _json
    from pathlib import Path as _Path
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    import app as viewer_app
    c = TestClient(viewer_app.app)
    probe = type("P", (), {"returncode": 0, "stdout": "12.5"})()
    wav = ("take.wav", b"RIFF0000WAVE", "audio/wav")
    with patch.object(viewer_app.subprocess, "run", return_value=probe), \
         patch.object(viewer_app.executor, "submit"):
        # backing accepted + recorded
        r = c.post("/api/pitch-jobs",
                   data={"name": "Aaron", "take_capture": "home", "comparison": "false"},
                   files={"file": wav, "backing": ("band.mp3", b"ID3backing", "audio/mpeg")})
        assert r.status_code == 202, r.text
        jid = r.json()["id"]
        man = _json.loads((_Path(viewer_app.RUNTIME) / jid / "job.json").read_text())
        assert man["backing_file"] == "backing.mp3"
        # bad backing extension rejected
        r = c.post("/api/pitch-jobs",
                   data={"name": "Aaron", "take_capture": "home", "comparison": "false"},
                   files={"file": wav, "backing": ("notes.txt", b"x", "text/plain")})
        assert r.status_code == 415 and r.json()["detail"]["detail"] == "backing"
        # no backing at all is fine
        r = c.post("/api/pitch-jobs",
                   data={"name": "Aaron", "take_capture": "home", "comparison": "false"}, files={"file": wav})
        assert r.status_code == 202
        man = _json.loads((_Path(viewer_app.RUNTIME) / r.json()["id"] / "job.json").read_text())
        assert "backing_file" not in man
