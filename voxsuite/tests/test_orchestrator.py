"""Deterministic orchestration tests with fake engines (no audio deps)."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from voxsuite.orchestrator import (
    STAGES, FusedJob, IsolateResult, JobMeta, JobRunner, new_job, run_fused,
)


class FakeEngines:
    def __init__(self, *, isolate_skip=False, fail_in=None):
        self.calls = []
        self.isolate_skip = isolate_skip
        self.fail_in = fail_in  # "isolate" | "analyze" | "polish"

    def isolate(self, src, workdir):
        self.calls.append("isolate")
        if self.fail_in == "isolate":
            raise RuntimeError("boom-isolate")
        return IsolateResult(stem=Path(src), skipped=self.isolate_skip,
                             note="fallback" if self.isolate_skip else "isolated once")

    def analyze(self, stem, workdir, meta):
        self.calls.append("analyze")
        if self.fail_in == "analyze":
            raise RuntimeError("boom-analyze")
        report = Path(workdir) / "report.md"
        report.write_text("# report\n")
        return {"report_path": str(report), "score": {"overall": 7.4}, "contour": {"values": [0, 1]}}

    def polish(self, stem, workdir, meta):
        self.calls.append("polish")
        if self.fail_in == "polish":
            raise RuntimeError("boom-polish")
        out = Path(workdir) / "vocal_cleaned.wav"
        out.write_bytes(b"RIFF")
        return {"download_path": str(out), "revision": 1, "document": {"bypass": {}}}


def _run(engines, **kw):
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "take.wav"
        src.write_bytes(b"RIFF")
        job = new_job("take.wav")
        run_fused(job, src, Path(d) / "work", engines, JobMeta(**kw))
        return job


def test_happy_path_completes_through_all_stages():
    eng = FakeEngines()
    job = _run(eng)
    assert job.status == "complete"
    assert job.stage == "export" and job.progress == 100
    assert eng.calls == ["isolate", "analyze", "polish"]  # isolate ran once
    assert job.analysis and job.analysis["score"]["overall"] == 7.4
    assert job.polish and job.polish["revision"] == 1
    assert job.isolation == {"skipped": False, "note": "isolated once"}
    assert job.error is None


def test_status_payload_is_adaptfused_shaped():
    job = _run(FakeEngines())
    s = job.to_status()
    assert set(["id", "status", "stage", "progress", "analysis", "polish", "error"]) <= set(s)
    assert s["stage"] in STAGES


def test_isolate_skip_is_recorded_not_hidden():
    job = _run(FakeEngines(isolate_skip=True))
    assert job.status == "complete"
    assert job.isolation["skipped"] is True
    assert any("isolation skipped" in line for line in job.log)


def test_engine_failure_fails_job_cleanly():
    for stage in ("isolate", "analyze", "polish"):
        eng = FakeEngines(fail_in=stage)
        job = _run(eng)
        assert job.status == "failed", stage
        assert job.error["code"] == "fused_error"
        assert f"boom-{stage}" in job.error["message"]


def test_progress_never_decreases():
    seen = []
    eng = FakeEngines()
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "t.wav"; src.write_bytes(b"RIFF")
        job = new_job("t.wav")
        run_fused(job, src, Path(d) / "w", eng, JobMeta(),
                  on_update=lambda j: seen.append(j.progress))
    assert seen == sorted(seen)
    assert seen[-1] == 100


def test_job_runner_registers_and_serves_status():
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "t.wav"; src.write_bytes(b"RIFF")
        runner = JobRunner(FakeEngines(), Path(d) / "jobs")
        job = runner.start("t.wav", src, JobMeta(), background=True)
        for _ in range(100):
            if runner.get(job.id).status in ("complete", "failed"):
                break
            time.sleep(0.02)
        assert runner.get(job.id).status == "complete"
        assert runner.get("nope") is None
