"""Fused orchestrator — one upload through both engines.

See design/fused-orchestrator.md. A fused job carries a single take through
isolate → analyze → polish → export, isolating the vocal ONCE and feeding that
stem to both VoxAnalysis (measure/score) and VoxPolish (repair/tune). The heavy
engine work sits behind the `Engines` protocol so the orchestration logic here is
deterministic and unit-testable with fakes, and the real adapter (engines.py) can
be swapped in wherever the audio deps are installed.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Protocol

# The fused signal chain (must match telemetry-contract.md → CHAINS.fused).
STAGES = ["upload", "isolate", "analyze", "score", "clean", "tune", "render", "export"]
# Progress checkpoints stamped as each stage begins (export = done).
_PROGRESS = {"upload": 5, "isolate": 15, "analyze": 35, "score": 55,
             "clean": 68, "tune": 82, "render": 92, "export": 100}


class Engines(Protocol):
    """The two engines, reduced to the three calls Fused needs. Isolation runs
    once; its stem feeds both analyze and polish."""

    def isolate(self, src: Path, workdir: Path) -> "IsolateResult": ...
    def analyze(self, stem: Path, workdir: Path, meta: "JobMeta") -> dict: ...
    def polish(self, stem: Path, workdir: Path, meta: "JobMeta") -> dict: ...


@dataclass
class IsolateResult:
    stem: Path                 # the isolated vocal (or the raw upload on fallback)
    skipped: bool = False      # True if separation was unavailable → stem == src
    note: str = ""


@dataclass
class JobMeta:
    performer: str = "Singer"
    song: str = ""
    artist: str = ""
    tune: bool = True


@dataclass
class FusedJob:
    id: str
    name: str
    status: str = "queued"      # queued | processing | complete | failed
    stage: str = "upload"
    progress: int = 0
    analysis: Optional[dict] = None   # {report_url, score, contour, ...}
    polish: Optional[dict] = None     # {download_url, document, ...}
    isolation: Optional[dict] = None  # {skipped, note}
    error: Optional[dict] = None
    log: list = field(default_factory=list)

    def to_status(self) -> dict:
        """The /api/fused-jobs/{id} payload the deck polls (adaptFused-shaped)."""
        return {
            "id": self.id, "name": self.name, "status": self.status,
            "stage": self.stage, "progress": self.progress,
            "analysis": self.analysis, "polish": self.polish,
            "isolation": self.isolation, "error": self.error, "log": self.log[-8:],
        }


def new_job(name: str) -> FusedJob:
    return FusedJob(id="fused_" + uuid.uuid4().hex[:12], name=name or "take")


def run_fused(
    job: FusedJob,
    src: Path,
    workdir: Path,
    engines: Engines,
    meta: JobMeta,
    on_update: Callable[[FusedJob], None] = lambda _job: None,
) -> FusedJob:
    """Drive one job across both engines, emitting a status update as each stage
    begins. Any engine failure fails the job cleanly with a structured error —
    it never raises out of here."""

    def advance(stage: str, msg: str) -> None:
        job.stage = stage
        job.progress = _PROGRESS[stage]
        job.log.append(msg)
        on_update(job)

    try:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        job.status = "processing"
        advance("upload", f"received · {job.name}")

        # 1) isolate ONCE — the stem feeds both engines
        advance("isolate", "separating vocal")
        iso = engines.isolate(src, workdir)
        job.isolation = {"skipped": iso.skipped, "note": iso.note}
        if iso.skipped:
            job.log.append("isolation skipped · " + (iso.note or "treating upload as vocal"))

        # 2) analyze the isolated stem (analyze + score chain steps)
        advance("analyze", "tracking pitch")
        analysis = engines.analyze(iso.stem, workdir, meta)
        advance("score", "building scorecard")
        job.analysis = analysis

        # 3) polish the SAME stem (clean → tune → render chain steps)
        advance("clean", "repairing · gate · breath · sibilance")
        polish = engines.polish(iso.stem, workdir, meta)
        advance("tune", "pitch-correcting to analyzed target")
        advance("render", "bouncing polished vocal")
        job.polish = polish

        # 4) export
        advance("export", "assembling deliverables")
        job.status = "complete"
        job.log.append("fused run complete")
        on_update(job)
    except Exception as exc:  # noqa: BLE001 — surface any engine failure as job state
        job.status = "failed"
        job.error = {"code": "fused_error", "message": str(exc)}
        job.log.append("failed · " + str(exc))
        on_update(job)
    return job


class JobRunner:
    """Tiny in-memory registry + background executor for fused jobs."""

    def __init__(self, engines: Engines, base: Path):
        self._engines = engines
        self._base = Path(base)
        self._jobs: dict[str, FusedJob] = {}
        self._lock = threading.Lock()

    def start(self, name: str, src: Path, meta: JobMeta, *, background: bool = True) -> FusedJob:
        job = new_job(name)
        with self._lock:
            self._jobs[job.id] = job
        workdir = self._base / job.id

        def work() -> None:
            run_fused(job, src, workdir, self._engines, meta, self._save)

        if background:
            threading.Thread(target=work, daemon=True).start()
        else:
            work()
        return job

    def _save(self, job: FusedJob) -> None:
        with self._lock:
            self._jobs[job.id] = job

    def get(self, job_id: str) -> Optional[FusedJob]:
        with self._lock:
            return self._jobs.get(job_id)
