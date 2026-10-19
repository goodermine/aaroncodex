"""Singnexa coaching write-up and talk cutting: the parts that sit around the
engine. Claude is faked; the guard that keeps it from inventing a score is real."""

from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest

from voxsuite.singnexa import writeup
from test_singnexa import H, FakePipeline, SAMPLE, _signin, _upload, needs_ffprobe

from fastapi.testclient import TestClient
from voxsuite.singnexa.app import create_app

RESULTS = "SCORES\nOverall: 8.2/10  (high confidence)\nLead with: 8.2/10 overall\n- 1:04  F#4  drift 224.8c\n"


class FakeClient:
    """Stands in for anthropic.Anthropic(); replies in order."""

    def __init__(self, *replies, stop_reason="end_turn"):
        self.replies = list(replies)
        self.stop_reason = stop_reason
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        text = self.replies.pop(0) if self.replies else ""
        return SimpleNamespace(stop_reason=self.stop_reason, model=kwargs["model"],
                               content=[SimpleNamespace(type="text", text=text)],
                               usage=SimpleNamespace(input_tokens=100, output_tokens=50))


def test_claims_not_in_the_results_are_caught():
    ok = "### The score\nYou scored 8.2/10. Listen back at 1:04."
    assert writeup.unsupported_claims(ok, RESULTS) == []
    bad = "### The score\nYou scored 8.5 out of 10. Listen back at 2:10."
    assert writeup.unsupported_claims(bad, RESULTS) == ["2:10", "8.5/10"]


def test_ready_write_up_uses_opus_with_the_refusal_fallback():
    client = FakeClient("### The score\nYou scored 8.2/10.")
    out = writeup.generate(RESULTS, client=client, singer="Aaron", song="Lose Control",
                           take_context={"capture": "live", "intent": "learning"})
    assert out["status"] == "ready" and "8.2/10" in out["markdown"]
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5" and call["fallbacks"] == "default"
    assert call["output_config"] == {"effort": "medium"}
    prompt = call["messages"][0]["content"]
    assert "Lead with: 8.2/10" in prompt and "Take type: learning" in prompt


def test_an_invented_score_gets_one_retry_then_no_write_up():
    client = FakeClient("You scored 9.1/10.", "Still 9.1/10.")
    out = writeup.generate(RESULTS, client=client)
    assert out["status"] == "failed" and out["reason"] == "unsupported_numbers"
    assert len(client.calls) == 2 and "9.1/10" in client.calls[1]["messages"][-1]["content"]


def test_a_corrected_retry_is_accepted():
    client = FakeClient("You scored 9.1/10.", "You scored 8.2/10.")
    assert writeup.generate(RESULTS, client=client)["status"] == "ready"


def test_a_declined_request_means_no_write_up():
    out = writeup.generate(RESULTS, client=FakeClient("x", stop_reason="refusal"))
    assert out == {"status": "failed", "reason": "declined", "model": "claude-opus-5-5"}


def test_no_key_means_switched_off(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert writeup.generate(RESULTS) == {"status": "disabled"}


def test_haiku_is_sent_without_the_fallback(monkeypatch):
    monkeypatch.setenv("SINGNEXA_WRITEUP_MODEL", "claude-haiku-5-5")
    client = FakeClient("8.2/10")
    writeup.generate(RESULTS, client=client)
    assert "fallbacks" not in client.calls[0]


@pytest.fixture
def env_with_writer(tmp_path):
    if not SAMPLE.is_file():
        pytest.skip("sample analysis not in archive")
    fake = FakePipeline(tmp_path / "work")
    client = FakeClient("### The score\nYou scored 8.2/10 overall.")
    app = create_app(tmp_path / "data", pipeline=fake, cookie_secure=False, writeup_client=client)
    return TestClient(app), app.state.store, fake, tmp_path, client


@needs_ffprobe
def test_results_page_gets_the_write_up(env_with_writer):
    http, store, fake, tmp, client = env_with_writer
    _signin(http, store, "aaron")
    job_id = _upload(http).json()["id"]
    for _ in range(50):
        job = http.get(f"/api/jobs/{job_id}").json()
        if job["writeup"]["status"] != "pending":
            break
        time.sleep(0.1)
    assert job["writeup"] == {"status": "ready", "markdown": "### The score\nYou scored 8.2/10 overall."}
    prompt = client.calls[0]["messages"][0]["content"]
    assert "Singer: Aaron" in prompt and "FULL RESULTS:" in prompt and "8.2/10" in prompt
    saved = json.loads((tmp / "data" / "results" / job_id / "writeup.json").read_text())
    assert saved["status"] == "ready"


@needs_ffprobe
def test_talk_is_cut_unless_the_singer_keeps_everything(env_with_writer):
    http, store, fake, *_ = env_with_writer
    _signin(http, store, "aaron")
    _upload(http)
    http.post("/api/jobs", headers=H,
              files={"file": ("take.wav", fake_wav(), "audio/wav")},
              data={"song": "x", "capture": "home", "keep_talk": "1"})
    assert [m["cut_talk"] for _, _, m in fake.submitted] == [True, False]


def fake_wav():
    from test_singnexa import _wav_bytes
    return _wav_bytes()
