"""Runs Singnexa uploads through the ONE canonical analysis path.

The work itself is the Analyze viewer's own job runner (viewer/app.py
``_process`` -> engine/pitch_track.py -> RoFormer separation -> analyse_song.py
-> compute_technical_score). Nothing here scores, rounds or adjusts anything
(CLAUDE.md rule 1). This module only:

  * hands the upload to that runner (comparison/YouTube lookup always OFF),
  * copies the finished, measured results into durable storage,
  * deletes the upload, stems and playback audio straight afterwards,
  * runs tools/score_preflight.py at start-up so a stale engine can never
    publish a headline score (rule 2).

A failed separation fails the job — a full-mix score is never produced (rule 4).
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

# Formats the separation helper takes as-is; anything else is losslessly
# re-encoded to FLAC first (AIFF, Opus, Ogg, AAC ...).
NATIVE_SUFFIXES = {".wav", ".flac", ".mp3", ".m4a"}

ERROR_TEXT = {
    "stem_separation_failed": "We couldn't separate the voice from the music, so no score was made. "
                              "A full-mix score would be meaningless.",
    "unsupported_media": "That file couldn't be decoded. Try a WAV or FLAC export.",
    "media_too_long": "That recording is longer than the 15-minute limit.",
    "no_reliable_pitch": "We couldn't find a clear sung pitch in this recording.",
    "conversion_failed": "The audio couldn't be converted for analysis.",
    "v2_analysis_failed": "The analysis engine stopped before finishing.",
    "analysis_timeout": "The analysis took too long and was stopped.",
    "worker_unavailable": "The server restarted while this was running. Please upload it again.",
    "analysis_failed": "The analysis failed.",
}


def analysis_root() -> Path:
    env = os.environ.get("VOX_ANALYSIS_ROOT")
    if env:
        return Path(env)
    # voxsuite/src/voxsuite/singnexa/pipeline.py -> parents[4] == repo root
    return Path(__file__).resolve().parents[4] / "voxanalysis" / "vox-analysis"


def repo_root() -> Path:
    return analysis_root().resolve().parents[1]


def _load_viewer(runtime: Path):
    """Import viewer/app.py with its job store pointed at our work dir."""
    root = analysis_root()
    os.environ["VOX_PITCH_RUNTIME"] = str(runtime)
    for p in (root / "engine", root / "viewer"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    spec = importlib.util.spec_from_file_location("singnexa_viewer_app", root / "viewer" / "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_preflight(timeout: int = 180) -> dict:
    script = repo_root() / "tools" / "score_preflight.py"
    started = time.time()
    if not script.is_file():
        return {"ok": False, "summary": "score_preflight.py is not installed", "checked_at": started}
    try:
        proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                              timeout=timeout, cwd=str(repo_root()))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "summary": f"preflight could not run: {exc.__class__.__name__}", "checked_at": started}
    lines = [l for l in (proc.stdout + proc.stderr).splitlines() if l.strip()]
    fails = [l.strip() for l in lines if l.lstrip().startswith("FAIL")]
    summary = "; ".join(fails[:3]) if fails else (lines[-1].strip() if lines else "")
    return {"ok": proc.returncode == 0, "summary": summary[:300], "checked_at": started}


class CanonicalPipeline:
    """Queue + runner. ``on_finish(job_id, outcome)`` is called once per job
    with either {"status": "complete", "raw": ..., "result": ..., "technical_md": ...}
    or {"status": "failed", "code": ..., "reason": ...}."""

    def __init__(self, work_dir: Path, workers: int = 1):
        self.work = Path(work_dir)
        self.work.mkdir(parents=True, exist_ok=True)
        self.viewer = _load_viewer(self.work)
        self.executor = ThreadPoolExecutor(max_workers=max(1, workers))
        # Synchronous on purpose: no score is served before the check has run.
        self.preflight = run_preflight()

    def refresh_preflight(self) -> dict:
        self.preflight = run_preflight()
        return self.preflight

    def job_dir(self, job_id: str) -> Path:
        return self.work / job_id

    def new_upload_path(self, job_id: str, suffix: str) -> Path:
        d = self.job_dir(job_id)
        d.mkdir(parents=True, exist_ok=False)
        return d / f"upload{suffix}"

    def discard(self, job_id: str) -> None:
        shutil.rmtree(self.job_dir(job_id), ignore_errors=True)

    def stage(self, job_id: str) -> str | None:
        for name in ("stage.json", "job.json"):
            try:
                return json.loads((self.job_dir(job_id) / name).read_text(encoding="utf-8"))["stage"]
            except (OSError, ValueError, KeyError):
                continue
        return None

    def submit(self, job_id: str, upload: Path, meta: dict, on_finish: Callable[[str, dict], None],
               on_start: Callable[[str], None] | None = None) -> None:
        manifest = {
            "id": job_id, "status": "queued", "stage": "queued",
            "upload_file": upload.name,
            "performer_name": meta.get("performer_name") or "Singer",
            "song_name": meta.get("song", ""), "original_artist": meta.get("artist", ""),
            "recording_conditions": meta.get("conditions", ""),
            "comparison_enabled": False,          # no YouTube lookup on the public service
            "export_spectral": False,             # display-only tiles; deleted anyway
            "created_at": time.time(),
        }
        if meta.get("take_context"):
            manifest["take_context"] = meta["take_context"]
        self.viewer._write_manifest(self.job_dir(job_id), manifest)
        self.executor.submit(self._run, job_id, on_finish, on_start)

    def _run(self, job_id: str, on_finish, on_start=None) -> None:
        job_dir = self.job_dir(job_id)
        try:
            if on_start:
                on_start(job_id)
            outcome = self._analyse(job_id, job_dir)
        except Exception as exc:  # never leave a job hanging
            outcome = {"status": "failed", "code": "analysis_failed", "reason": exc.__class__.__name__}
        finally:
            # Audio, stems and playback files go as soon as the report exists.
            shutil.rmtree(job_dir, ignore_errors=True)
        on_finish(job_id, outcome)

    def _analyse(self, job_id: str, job_dir: Path) -> dict:
        manifest = self.viewer._read_manifest(job_dir)
        upload = job_dir / manifest["upload_file"]
        if upload.suffix.lower() not in NATIVE_SUFFIXES:
            flac = job_dir / "upload.flac"
            proc = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(upload), "-vn", "-c:a", "flac", str(flac)],
                                  capture_output=True, text=True, timeout=600)
            if proc.returncode or not flac.is_file():
                return {"status": "failed", "code": "conversion_failed"}
            upload.unlink(missing_ok=True)
            manifest["upload_file"] = flac.name
            self.viewer._write_manifest(job_dir, manifest)
        self.viewer._process(job_id)
        manifest = self.viewer._read_manifest(job_dir)
        if manifest.get("status") != "complete":
            err = manifest.get("error") or {}
            return {"status": "failed", "code": err.get("code", "analysis_failed"), "reason": err.get("reason")}
        analyses = sorted((job_dir / "v2" / "output").glob("*_analysis.json"))
        if not analyses:
            return {"status": "failed", "code": "v2_analysis_failed"}
        raw = json.loads(analyses[0].read_text(encoding="utf-8"))
        result = dict(manifest.get("result") or {})
        for key in ("audio_urls", "spectral", "v2_report_url", "reference", "v2_analysis", "comparison"):
            result.pop(key, None)
        technical = ""
        reports = sorted((job_dir / "v2" / "reports").glob("*_report.md"))
        if reports:
            technical = reports[0].read_text(encoding="utf-8").replace(str(job_dir), "[private job artifact]")
        return {"status": "complete", "raw": raw, "result": result, "technical_md": technical}
