"""VOX Suite — Fused orchestrator web app.

Serves the Fused command deck and a single job API that carries one upload
through both engines. The engine adapter is injectable so tests drive the whole
lifecycle with fakes (no heavy audio deps).
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ..orchestrator import JobMeta, JobRunner

STATIC = Path(__file__).parent / "static"
# Assets whose content decides the cache-bust version stamped into the deck.
_VERSIONED = ("vox-tokens.css", "vox-kit.css", "vox-telemetry.js", "vox-about.js", "deck.html")
_MEDIA = {"css": "text/css", "js": "text/javascript", "html": "text/html"}

# Accepted upload extensions (mirrors the engines' ingest surface).
_ALLOWED = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".mp4", ".mov"}


def _asset_version() -> str:
    h = hashlib.sha1()
    for name in _VERSIONED:
        p = STATIC / name
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()[:12]


def create_app(base_dir, engines=None) -> FastAPI:
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    if engines is None:  # lazy so the app imports without the heavy deps present
        from ..engines import RealEngines
        engines = RealEngines()
    runner = JobRunner(engines, base)
    app = FastAPI(title="VoxSuite — Fused", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    @app.get("/deck", response_class=HTMLResponse)
    def deck():
        html = (STATIC / "deck.html").read_text().replace("__ASSET_VERSION__", _asset_version())
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})

    @app.get("/static/{name}")
    def static_file(name: str):
        path = STATIC / name
        if not path.is_file() or path.parent != STATIC:
            raise HTTPException(404)
        return FileResponse(path, media_type=_MEDIA.get(path.suffix[1:], "text/plain"))

    @app.post("/api/fused-jobs", status_code=202)
    async def create_fused_job(
        file: UploadFile = File(...),
        name: str = Form("Singer"),
        song: str = Form(""),
        artist: str = Form(""),
        tune: str = Form("true"),
    ):
        ext = Path(file.filename or "").suffix.lower()
        if ext not in _ALLOWED:
            raise HTTPException(415, {"code": "unsupported_media", "ext": ext})
        uploads = base / "uploads"
        uploads.mkdir(exist_ok=True)
        dest = uploads / f"{uuid.uuid4().hex[:8]}{ext}"
        dest.write_bytes(await file.read())
        meta = JobMeta(performer=name or "Singer", song=song, artist=artist,
                       tune=str(tune).lower() in ("1", "true", "yes", "on"))
        job = runner.start(file.filename or dest.name, dest, meta)
        return {"id": job.id, "status": job.status, "status_url": f"/api/fused-jobs/{job.id}"}

    @app.get("/api/fused-jobs/{job_id}")
    def get_fused_job(job_id: str):
        job = runner.get(job_id)
        if job is None:
            raise HTTPException(404, "unknown job")
        return JSONResponse(job.to_status())

    @app.get("/api/fused-jobs/{job_id}/report")
    def get_report(job_id: str):
        job = runner.get(job_id)
        path = (job.analysis or {}).get("report_path") if job else None
        if not path or not Path(path).is_file():
            raise HTTPException(404, "report not ready")
        return FileResponse(path, media_type="text/markdown", filename="analysis_report.md")

    @app.get("/api/fused-jobs/{job_id}/download")
    def get_download(job_id: str):
        job = runner.get(job_id)
        path = (job.polish or {}).get("download_path") if job else None
        if not path or not Path(path).is_file():
            raise HTTPException(404, "polished vocal not ready")
        return FileResponse(path, media_type="audio/wav", filename="polished_vocal.wav")

    return app
