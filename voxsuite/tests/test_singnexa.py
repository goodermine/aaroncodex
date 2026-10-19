"""Singnexa beta app: sign-in, ownership, CSRF guard, uploads, kept results.

The analysis itself is faked (the real path is the canonical viewer runner, run
in the deploy smoke test); the report is built by the real report_builder from a
real archived analysis, so the page payload is exactly what users will get.
"""

from __future__ import annotations

import io
import json
import shutil
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voxsuite.singnexa.app import create_app, lead_score
from voxsuite.singnexa.store import Store, verify_password, hash_password

REPO = Path(__file__).resolve().parents[2]
ARCHIVE = REPO / "voxanalysis" / "archive" / "scratch-analyses"
SAMPLE = ARCHIVE / "2026-10-16-aaron-lose-control-take-003_analysis.json"
H = {"X-Singnexa": "1"}

needs_ffprobe = pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe not installed")


class FakePipeline:
    def __init__(self, work: Path, outcome="complete", preflight_ok=True):
        self.work = work
        self.outcome = outcome
        self.preflight = {"ok": preflight_ok, "summary": "test", "checked_at": 0}
        self.submitted = []

    def job_dir(self, job_id):
        return self.work / job_id

    def new_upload_path(self, job_id, suffix):
        d = self.job_dir(job_id)
        d.mkdir(parents=True)
        return d / f"upload{suffix}"

    def discard(self, job_id):
        shutil.rmtree(self.job_dir(job_id), ignore_errors=True)

    def stage(self, job_id):
        return None

    def submit(self, job_id, upload, meta, on_finish, on_start=None):
        self.submitted.append((job_id, upload, meta))
        if on_start:
            on_start(job_id)
        shutil.rmtree(self.job_dir(job_id), ignore_errors=True)   # as the real runner does
        if self.outcome == "complete":
            raw = json.loads(SAMPLE.read_text(encoding="utf-8"))
            on_finish(job_id, {"status": "complete", "raw": raw,
                               "result": {"duration_seconds": 212.6, "robust_min_note": "G3", "robust_max_note": "G5"},
                               "technical_md": "# Technical report\n\nok"})
        else:
            on_finish(job_id, {"status": "failed", "code": "stem_separation_failed"})


def _wav_bytes(seconds=1.0, rate=8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buf.getvalue()


@pytest.fixture
def env(tmp_path):
    if not SAMPLE.is_file():
        pytest.skip("sample analysis not in archive")
    fake = FakePipeline(tmp_path / "work")
    app = create_app(tmp_path / "data", pipeline=fake, cookie_secure=False)
    store: Store = app.state.store
    return TestClient(app), store, fake, tmp_path


def _signin(client, store, username, admin=False, password="correct horse battery"):
    store.create_user(username, username.title(), is_admin=admin, password=password)
    r = client.post("/api/login", json={"username": username, "password": password}, headers=H)
    assert r.status_code == 200, r.text
    return client


def _upload(client, name="take.wav", data=None, capture="live", song="Lose Control"):
    return client.post("/api/jobs", headers=H,
                       files={"file": (name, data if data is not None else _wav_bytes(), "audio/wav")},
                       data={"song": song, "artist": "Teddy Swims", "capture": capture})


def test_passwords_hash_and_verify():
    h = hash_password("a long passphrase")
    assert h.startswith("scrypt$") and "a long passphrase" not in h
    assert verify_password("a long passphrase", h)
    assert not verify_password("wrong", h)


def test_lead_score_is_the_higher_number():
    assert lead_score({"overall": 8.2, "capture_fair": 7.3})["label"] == "overall"
    lead = lead_score({"overall": 7.2, "capture_fair": 7.9})
    assert (lead["value"], lead["label"], lead["other_value"]) == (7.9, "capture-fair", 7.2)
    assert lead_score({"overall": None, "capture_fair": None}) is None


def test_everything_needs_sign_in(env):
    client, *_ = env
    assert client.get("/", follow_redirects=False).headers["location"] == "/login"
    assert client.get("/admin", follow_redirects=False).status_code == 303
    assert client.get("/api/jobs").status_code == 401
    assert client.get("/login").status_code == 200
    health = client.get("/healthz").json()
    assert health["ok"] is True and "commit" in health


def test_bad_password_and_throttle(env):
    client, store, *_ = env
    store.create_user("jess", "Jess", password="correct horse battery")
    for _ in range(8):
        assert client.post("/api/login", json={"username": "jess", "password": "nope"}, headers=H).status_code == 401
    r = client.post("/api/login", json={"username": "jess", "password": "correct horse battery"}, headers=H)
    assert r.status_code == 429


def test_state_changes_need_the_csrf_header(env):
    client, store, *_ = env
    store.create_user("jess", "Jess", password="correct horse battery")
    r = client.post("/api/login", json={"username": "jess", "password": "correct horse battery"})
    assert r.status_code == 403


def test_first_sign_in_forces_a_new_password(env):
    client, store, *_ = env
    _, temp = store.create_user("sam", "Sam")
    assert client.post("/api/login", json={"username": "sam", "password": temp}, headers=H).json()["user"]["must_change_password"]
    assert client.get("/api/jobs").status_code == 403
    assert client.get("/", follow_redirects=False).headers["location"] == "/account"
    assert client.post("/api/password", json={"current": temp, "new": "short"}, headers=H).status_code == 400
    assert client.post("/api/password", json={"current": temp, "new": "my own long password"}, headers=H).status_code == 200
    assert client.get("/api/jobs").status_code == 200


@needs_ffprobe
def test_upload_analyse_and_keep_results(env):
    client, store, fake, tmp = env
    _signin(client, store, "aaron")
    r = _upload(client)
    assert r.status_code == 202, r.text
    job_id = r.json()["id"]
    meta = fake.submitted[0][2]
    assert meta["take_context"] == {"capture": "live"} and meta["performer_name"] == "Aaron"
    assert not (fake.work / job_id).exists()          # audio gone once the report exists
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "complete"
    assert job["lead"] == {"value": 8.2, "label": "overall", "other_value": 7.3, "other_label": "capture-fair"}
    assert job["report"]["score"]["confidence"] == "high"
    text = client.get(f"/api/jobs/{job_id}/full-results").text
    assert "8.2/10" in text and "Lead with" in text
    assert client.get(f"/api/jobs/{job_id}/technical.md").text.startswith("# Technical report")
    assert [j["id"] for j in client.get("/api/jobs").json()["jobs"]] == [job_id]
    assert client.get(f"/results/{job_id}").status_code == 200
    # nothing but the measured results is kept
    kept = sorted(p.name for p in (tmp / "data" / "results" / job_id).iterdir())
    assert kept == ["analysis.json", "result.json", "technical.md"]


@needs_ffprobe
def test_other_users_cannot_see_a_result_but_admins_can(env):
    client, store, *_ = env
    _signin(client, store, "aaron")
    job_id = _upload(client).json()["id"]
    other = TestClient(client.app)
    _signin(other, store, "jess")
    assert other.get(f"/api/jobs/{job_id}").status_code == 404
    assert other.get(f"/api/jobs/{job_id}/full-results").status_code == 404
    assert other.delete(f"/api/jobs/{job_id}", headers=H).status_code == 404
    assert other.get("/api/jobs").json()["jobs"] == []
    admin = TestClient(client.app)
    _signin(admin, store, "boss", admin=True)
    assert admin.get(f"/api/jobs/{job_id}").status_code == 200
    assert job_id in [j["id"] for j in admin.get("/api/admin/overview").json()["jobs"]]


@needs_ffprobe
def test_failed_separation_gives_no_score(env):
    client, store, fake, _ = env
    fake.outcome = "failed"
    _signin(client, store, "aaron")
    job = client.get(f"/api/jobs/{_upload(client).json()['id']}").json()
    assert job["status"] == "failed" and job["lead"] is None
    assert job["error"]["code"] == "stem_separation_failed"
    assert "full-mix" in job["error"]["message"]


@needs_ffprobe
def test_failed_preflight_withholds_only_the_headline(env):
    client, store, fake, _ = env
    fake.preflight = {"ok": False, "summary": "FAIL engine mismatch"}
    _signin(client, store, "aaron")
    job = client.get(f"/api/jobs/{_upload(client).json()['id']}").json()
    assert job["status"] == "complete" and job["lead"] is None
    assert "preflight" in job["report"]["score"]["withheld_reason"]
    assert job["report"]["metrics"]                     # the analysis itself is still there


def test_upload_rules(env):
    client, store, *_ = env
    _signin(client, store, "aaron")
    assert _upload(client, name="take.exe").status_code == 415
    assert _upload(client, capture="").status_code == 422
    r = client.post("/api/jobs", headers={**H, "Content-Length": str(10 ** 10)}, content=b"x")
    assert r.status_code == 413


@needs_ffprobe
def test_undecodable_audio_is_rejected_and_cleaned_up(env):
    client, store, fake, _ = env
    _signin(client, store, "aaron")
    assert _upload(client, data=b"not audio at all").status_code == 415
    assert not any(fake.work.iterdir()) if fake.work.exists() else True


@needs_ffprobe
def test_user_can_delete_their_result(env):
    client, store, _, tmp = env
    _signin(client, store, "aaron")
    job_id = _upload(client).json()["id"]
    assert client.delete(f"/api/jobs/{job_id}", headers=H).status_code == 200
    assert client.get(f"/api/jobs/{job_id}").status_code == 404
    assert not (tmp / "data" / "results" / job_id).exists()


def test_admin_creates_and_resets_users(env):
    client, store, *_ = env
    _signin(client, store, "boss", admin=True)
    r = client.post("/api/admin/users", json={"username": "Jess", "display_name": "Jess"}, headers=H)
    assert r.status_code == 200
    temp = r.json()["temporary_password"]
    assert r.json()["user"]["username"] == "jess"
    user = store.user_by_username("jess")
    assert verify_password(temp, user["password_hash"]) and user["must_change_password"]
    reset = client.post(f"/api/admin/users/{user['id']}/reset", headers=H).json()["temporary_password"]
    assert reset != temp
    assert client.post(f"/api/admin/users/{user['id']}/disable", headers=H).status_code == 200
    jess = TestClient(client.app)
    assert jess.post("/api/login", json={"username": "jess", "password": reset}, headers=H).status_code == 401
    plain = TestClient(client.app)
    _signin(plain, store, "pat")
    assert plain.get("/api/admin/overview").status_code == 403


def test_security_headers(env):
    client, *_ = env
    r = client.get("/login")
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"
