#!/usr/bin/env python3
"""Local/private VOXAI-Alpha vocal diagnostics service."""

from __future__ import annotations

import json
import importlib.util
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from report_builder import build_v2_report

RUNTIME = Path(os.getenv("VOX_PITCH_RUNTIME", HERE / "runtime")).resolve()
TRACKER = (HERE.parent / "engine" / "pitch_track.py").resolve()
V2_ANALYZER = (HERE.parent / "engine" / "analyse_song.py").resolve()
V2_CALIBRATION = (HERE.parent / "engine" / "calibration" / "pro_reference.json").resolve()
MAX_BYTES = 100 * 1024 * 1024
MAX_DURATION = 15 * 60
JOB_TTL_SECONDS = 24 * 60 * 60
MAX_ACTIVE_JOBS = 10
ANALYSIS_TIMEOUT = int(os.getenv("VOX_PITCH_TIMEOUT", "1800"))
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".mp4", ".mov"}
SPECTRAL_SOURCES = frozenset({"vocals", "original"})
SPECTRAL_DESCRIPTOR_FIELDS = (
    "version", "source", "transform", "display_only", "t0", "fps",
    "sample_rate", "hop_length", "duration_seconds", "total_frames",
    "midi_lo", "midi_hi", "midi_hi_exclusive", "bins_per_semitone",
    "bins_per_octave", "n_bins", "row_order", "row_formula",
    "time_formula", "db_floor", "db_ceil", "pixel_encoding",
    "tile_width_frames", "note",
)
SPECTRAL_TILE_FIELDS = (
    "index", "frame_start", "frame_count", "t0", "duration_seconds",
    "width", "height",
)
HARMONIC_TRACK_FIELDS = ("version", "rate_hz", "t0", "units", "values", "note")
PRIVATE_ARTIFACT_HEADERS = {
    "Cache-Control": "private, max-age=86400, immutable",
    "X-Content-Type-Options": "nosniff",
}
executor = ThreadPoolExecutor(max_workers=max(1, int(os.getenv("VOX_PITCH_WORKERS", "1"))))
manifest_lock = threading.Lock()


def _production_guard() -> None:
    if os.getenv("VOX_PITCH_ENV", "local").lower() == "production" and os.getenv("VOX_PITCH_STORAGE", "local") == "local":
        raise RuntimeError("Production requires durable job storage and an external worker queue.")


def _job_dir(job_id: str) -> Path:
    try:
        parsed = str(uuid.UUID(job_id))
    except ValueError as exc:
        raise HTTPException(404, "Job not found") from exc
    return RUNTIME / parsed


def _read_manifest(job_dir: Path) -> dict:
    path = job_dir / "job.json"
    if not path.exists():
        raise HTTPException(404, "Job not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "Job state is unavailable") from exc


def _write_manifest(job_dir: Path, value: dict) -> None:
    value["updated_at"] = time.time()
    temporary = job_dir / "job.json.tmp"
    with manifest_lock:
        temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
        temporary.replace(job_dir / "job.json")


def _error_code(output: str, timed_out: bool = False) -> str:
    if timed_out:
        return "analysis_timeout"
    for code in ("unsupported_media", "media_too_long", "no_reliable_pitch", "conversion_failed", "stem_separation_failed", "v2_analysis_failed"):
        if code in output:
            return code
    return "analysis_failed"


def _publish_spectral_metadata(analysis: dict, job_id: str) -> None:
    spectral = analysis.get("spectral")
    if not isinstance(spectral, dict):
        return
    raw_sources = spectral.get("sources")
    if not isinstance(raw_sources, dict):
        analysis["spectral"] = {"status": "unavailable", "sources": {}}
        return
    public_sources = {}
    for source in SPECTRAL_SOURCES:
        state = raw_sources.get(source)
        if not isinstance(state, dict):
            continue
        public = {
            key: state[key]
            for key in ("status", "reason", "tile_count", "artifact_bytes")
            if key in state
        }
        if state.get("status") == "ready":
            base = f"/api/pitch-jobs/{job_id}/spectral/{source}"
            public["descriptor_url"] = f"{base}/descriptor"
            public["harmonic_tracks_url"] = f"{base}/harmonics"
        public_sources[source] = public
    spectral["sources"] = public_sources


def _spectral_source(job_id: str, source: str) -> tuple[Path, dict]:
    if source not in SPECTRAL_SOURCES:
        raise HTTPException(404, "Spectral source not found")
    job_dir = _job_dir(job_id)
    manifest = _read_manifest(job_dir)
    if manifest.get("status") != "complete":
        raise HTTPException(409, "Spectral artifacts are not ready")
    state = (
        (manifest.get("result") or {}).get("spectral", {}).get("sources", {}).get(source)
    )
    if not isinstance(state, dict) or state.get("status") != "ready":
        raise HTTPException(409, "Spectral artifacts are unavailable")
    return job_dir / "spectral" / source, state


def _load_spectral_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "Spectral artifact is unavailable") from exc
    if not isinstance(value, dict):
        raise HTTPException(500, "Spectral artifact is invalid")
    return value


def _validated_descriptor(job_id: str, source: str) -> tuple[Path, dict]:
    source_dir, _ = _spectral_source(job_id, source)
    descriptor = _load_spectral_json(source_dir / "descriptor.json")
    if (
        descriptor.get("version") != "voxai_spectral_v1"
        or descriptor.get("source") != source
        or descriptor.get("display_only") is not True
        or descriptor.get("harmonic_tracks_file") != "harmonic-tracks.json"
        or not isinstance(descriptor.get("tiles"), list)
    ):
        raise HTTPException(500, "Spectral descriptor is invalid")
    for expected_index, tile in enumerate(descriptor["tiles"]):
        expected_file = f"tile-{expected_index:03d}.png"
        if (
            not isinstance(tile, dict)
            or tile.get("index") != expected_index
            or tile.get("file") != expected_file
        ):
            raise HTTPException(500, "Spectral descriptor is invalid")
    return source_dir, descriptor


def _process(job_id: str) -> None:
    job_dir = RUNTIME / job_id
    manifest = _read_manifest(job_dir)
    manifest.update(status="processing", stage="separating_vocals")
    _write_manifest(job_dir, manifest)
    log_path = job_dir / "analysis.log"
    try:
        analysis_deadline = time.monotonic() + ANALYSIS_TIMEOUT
        command = [
            sys.executable,
            str(TRACKER),
            str(job_dir / manifest["upload_file"]),
            "--job-dir",
            str(job_dir),
            "--name",
            manifest.get("performer_name", "Singer"),
            "--song",
            manifest.get("song_name", ""),
            "--artist",
            manifest.get("original_artist", ""),
            "--conditions",
            manifest.get("recording_conditions", ""),
            "--stage-file",
            str(job_dir / "stage.json"),
            "--export-spectral",
            "--analysis-deadline-monotonic",
            repr(analysis_deadline),
        ]
        if not manifest.get("comparison_enabled", True):
            command.append("--skip-comparison")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=ANALYSIS_TIMEOUT,
        )
        log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            manifest.update(status="failed", stage="failed", error={"code": _error_code(result.stdout + result.stderr)})
        else:
            analysis = json.loads((job_dir / "result.json").read_text(encoding="utf-8"))
            files = analysis.pop("audio_files", {})
            v2_analysis_file = analysis.pop("v2_analysis_file", None)
            v2_report_file = analysis.pop("v2_report_file", None)
            if not {"vocals", "instrumental"}.issubset(files):
                raise RuntimeError("Stem result did not provide both playback tracks")
            if not v2_analysis_file or not v2_report_file:
                raise RuntimeError("VOXAI V2 result artifacts are unavailable")
            raw_v2 = json.loads((job_dir / v2_analysis_file).read_text(encoding="utf-8"))
            reference = analysis.get("reference") or {}
            reference_analysis_file = reference.pop("analysis_file", None)
            if reference_analysis_file:
                reference_raw = json.loads((job_dir / reference_analysis_file).read_text(encoding="utf-8"))
                reference["v2_analysis"] = build_v2_report(reference_raw)
            analysis["v2_analysis"] = build_v2_report(
                raw_v2,
                conditions=manifest.get("recording_conditions", ""),
                comparison=analysis.get("comparison"),
            )
            analysis["v2_report_url"] = f"/api/pitch-jobs/{job_id}/report"
            analysis["audio_urls"] = {
                "vocals": f"/api/pitch-jobs/{job_id}/audio?track=vocals",
                "instrumental": f"/api/pitch-jobs/{job_id}/audio?track=instrumental",
            }
            if reference.get("status") == "ready":
                analysis["audio_urls"]["original"] = f"/api/pitch-jobs/{job_id}/audio?track=original"
            _publish_spectral_metadata(analysis, job_id)
            manifest.update(status="complete", stage="complete", result=analysis)
    except subprocess.TimeoutExpired as exc:
        log_path.write_text((exc.stdout or "") + (exc.stderr or ""), encoding="utf-8")
        manifest.update(status="failed", stage="failed", error={"code": "analysis_timeout"})
    except Exception as exc:  # details stay in the private server log
        log_path.write_text(repr(exc), encoding="utf-8")
        manifest.update(status="failed", stage="failed", error={"code": "analysis_failed"})
    _write_manifest(job_dir, manifest)


def _cleanup(recover_interrupted: bool = False) -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - JOB_TTL_SECONDS
    for entry in RUNTIME.iterdir():
        if not entry.is_dir():
            continue
        try:
            manifest = _read_manifest(entry)
            if recover_interrupted and manifest.get("status") == "processing":
                manifest.update(status="failed", stage="failed", error={"code": "worker_unavailable"})
                _write_manifest(entry, manifest)
            elif manifest.get("updated_at", entry.stat().st_mtime) < cutoff:
                shutil.rmtree(entry)
        except HTTPException:
            if entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry)


_production_guard()
_cleanup(recover_interrupted=True)
app = FastAPI(title="VOXAI-Alpha: Vocal Diagnostics and Analysis")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return (HERE / "static" / "index.html").read_text(encoding="utf-8")


# Shared VOX Suite design layer, vendored from /design via design/sync.sh.
# Whitelisted by exact name (no path traversal) so the single-source palette
# is served to the viewer without inlining a copy that would drift.
_SHARED_CSS = {"vox-tokens.css", "vox-kit.css"}


@app.get("/static/{name}")
async def static_asset(name: str) -> FileResponse:
    if name not in _SHARED_CSS:
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(HERE / "static" / name, media_type="text/css")


@app.post("/api/pitch-jobs", status_code=202)
async def create_job(
    request: Request,
    file: UploadFile,
    name: str = Form("Singer"),
    song: str = Form(""),
    artist: str = Form(""),
    conditions: str = Form(""),
    comparison: bool = Form(True),
) -> dict:
    _cleanup()
    active_jobs = 0
    for manifest_path in RUNTIME.glob("*/job.json"):
        try:
            if json.loads(manifest_path.read_text(encoding="utf-8")).get("status") in {"queued", "processing"}:
                active_jobs += 1
        except (OSError, json.JSONDecodeError):
            continue
    if active_jobs >= MAX_ACTIVE_JOBS:
        raise HTTPException(503, {"code": "worker_unavailable"})
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, {"code": "unsupported_media"})
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BYTES + 1024 * 1024:
        raise HTTPException(413, {"code": "media_too_large"})
    job_id = str(uuid.uuid4())
    job_dir = RUNTIME / job_id
    job_dir.mkdir(parents=True)
    upload_name = f"upload{suffix}"
    size = 0
    try:
        with (job_dir / upload_name).open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, {"code": "media_too_large"})
                destination.write(chunk)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(job_dir / upload_name)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        try:
            duration = float(probe.stdout.strip()) if probe.returncode == 0 else 0
        except ValueError:
            duration = 0
        if duration <= 0:
            raise HTTPException(415, {"code": "unsupported_media"})
        if duration > MAX_DURATION:
            raise HTTPException(422, {"code": "media_too_long"})
        performer_name = " ".join((name or "Singer").strip().split())[:80] or "Singer"
        song_name = " ".join((song or "").strip().split())[:160]
        original_artist = " ".join((artist or "").strip().split())[:160]
        recording_conditions = " ".join((conditions or "").strip().split())[:1000]
        if comparison and (not song_name or not original_artist):
            raise HTTPException(422, {"code": "missing_song_metadata"})
        manifest = {
            "id": job_id,
            "status": "queued",
            "stage": "queued",
            "upload_file": upload_name,
            "performer_name": performer_name,
            "song_name": song_name,
            "original_artist": original_artist,
            "recording_conditions": recording_conditions,
            "comparison_enabled": comparison,
            "created_at": time.time(),
        }
        _write_manifest(job_dir, manifest)
        executor.submit(_process, job_id)
        return {"id": job_id, "status": "queued", "status_url": f"/api/pitch-jobs/{job_id}"}
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    finally:
        await file.close()


@app.get("/api/pitch-jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job_dir = _job_dir(job_id)
    manifest = _read_manifest(job_dir)
    stage_path = job_dir / "stage.json"
    if manifest.get("status") == "processing" and stage_path.is_file():
        try:
            manifest["stage"] = json.loads(stage_path.read_text(encoding="utf-8"))["stage"]
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    if manifest.get("status") == "complete" and isinstance(manifest.get("result"), dict):
        _publish_spectral_metadata(manifest["result"], job_id)
        analyses = sorted((job_dir / "v2" / "output").glob("*_analysis.json"))
        if analyses:
            try:
                manifest["result"]["v2_analysis"] = build_v2_report(
                    json.loads(analyses[0].read_text(encoding="utf-8")),
                    conditions=manifest.get("recording_conditions", ""),
                    comparison=manifest["result"].get("comparison"),
                )
            except (OSError, json.JSONDecodeError, ValueError):
                pass
    return {key: manifest[key] for key in ("id", "status", "stage", "result", "error") if key in manifest}


@app.get("/api/pitch-jobs/{job_id}/audio")
async def get_audio(job_id: str, track: str = Query("vocals", pattern="^(vocals|instrumental|original)$")) -> FileResponse:
    job_dir = _job_dir(job_id)
    manifest = _read_manifest(job_dir)
    file_name = {"vocals": "vocals.mp3", "instrumental": "instrumental.mp3", "original": "original.mp3"}[track]
    if manifest.get("status") != "complete" or not (job_dir / file_name).exists():
        raise HTTPException(409, "Audio is not ready")
    return FileResponse(job_dir / file_name, media_type="audio/mpeg", filename=f"pitch-{track}.mp3")


@app.get("/api/pitch-jobs/{job_id}/spectral/{source}/descriptor")
async def get_spectral_descriptor(job_id: str, source: str) -> JSONResponse:
    _, descriptor = _validated_descriptor(job_id, source)
    public = {key: descriptor[key] for key in SPECTRAL_DESCRIPTOR_FIELDS if key in descriptor}
    public["harmonic_tracks_url"] = f"/api/pitch-jobs/{job_id}/spectral/{source}/harmonics"
    public["tiles"] = [
        {
            **{key: tile[key] for key in SPECTRAL_TILE_FIELDS if key in tile},
            "url": f"/api/pitch-jobs/{job_id}/spectral/{source}/tiles/{tile['index']}",
        }
        for tile in descriptor["tiles"]
    ]
    return JSONResponse(public, headers=PRIVATE_ARTIFACT_HEADERS)


@app.get("/api/pitch-jobs/{job_id}/spectral/{source}/harmonics")
async def get_harmonic_tracks(job_id: str, source: str) -> JSONResponse:
    source_dir, descriptor = _validated_descriptor(job_id, source)
    tracks = _load_spectral_json(source_dir / descriptor["harmonic_tracks_file"])
    if tracks.get("version") != "voxai_spectral_v1" or not isinstance(tracks.get("values"), dict):
        raise HTTPException(500, "Harmonic tracks are invalid")
    public = {key: tracks[key] for key in HARMONIC_TRACK_FIELDS if key in tracks}
    return JSONResponse(public, headers=PRIVATE_ARTIFACT_HEADERS)


@app.get("/api/pitch-jobs/{job_id}/spectral/{source}/tiles/{tile_index}")
async def get_spectral_tile(job_id: str, source: str, tile_index: int) -> FileResponse:
    source_dir, descriptor = _validated_descriptor(job_id, source)
    if tile_index < 0 or tile_index >= len(descriptor["tiles"]):
        raise HTTPException(404, "Spectral tile not found")
    file_name = f"tile-{tile_index:03d}.png"
    path = source_dir / file_name
    if not path.is_file():
        raise HTTPException(500, "Spectral tile is unavailable")
    return FileResponse(path, media_type="image/png", headers=PRIVATE_ARTIFACT_HEADERS)


@app.get("/api/pitch-jobs/{job_id}/report")
async def get_v2_report(job_id: str) -> FileResponse:
    job_dir = _job_dir(job_id)
    manifest = _read_manifest(job_dir)
    reports = sorted((job_dir / "v2" / "reports").glob("*_report.md"))
    if manifest.get("status") != "complete" or not reports:
        raise HTTPException(409, "VOXAI V2 report is not ready")
    public_report = job_dir / "voxai-v2-report.md"
    content = reports[0].read_text(encoding="utf-8")
    content = content.replace(str(job_dir), "[private job artifact]")
    public_report.write_text(content, encoding="utf-8")
    return FileResponse(public_report, media_type="text/markdown", filename="voxai-v2-report.md")


@app.get("/api/health")
async def health() -> dict:
    checks = {name: bool(shutil.which(name)) for name in ("ffmpeg", "ffprobe")}
    checks["stem_separator"] = (Path.home() / ".venvs" / "vox-sep-uvr" / "bin" / "audio-separator").is_file()
    checks["voxai_v2"] = V2_ANALYZER.is_file() and V2_CALIBRATION.is_file()
    checks["reference_lookup"] = importlib.util.find_spec("yt_dlp") is not None
    core_checks = ("ffmpeg", "ffprobe", "stem_separator", "voxai_v2")
    return {"ok": all(checks[name] for name in core_checks), "checks": checks, "worker_limit": executor._max_workers}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8766)
