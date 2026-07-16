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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from ..orchestrator import JobMeta, JobRunner

STATIC = Path(__file__).parent / "static"
# Assets whose content decides the cache-bust version stamped into the deck.
_VERSIONED = ("vox-tokens.css", "vox-kit.css", "vox-telemetry.js", "vox-about.js", "vox-theme.js", "vox-record.js", "vox-record.css", "deck.html")
_MEDIA = {"css": "text/css", "js": "text/javascript", "html": "text/html"}

# Accepted upload extensions (mirrors the engines' ingest surface).
_ALLOWED = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".mp4", ".mov", ".webm"}

# Served for cross-mode tabs when the deck runs standalone (see route below).
_MODE_HINT_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VOX Suite — switch modes</title></head>
<body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#070a0e;color:#eaf3f8;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif">
<div style="max-width:460px;text-align:center;padding:28px">
<div style="font:700 12px/1 ui-monospace,monospace;letter-spacing:.22em;color:#3fe0ff">VOX//SUITE</div>
<h1 style="font-size:20px;margin:14px 0 6px">Mode switching needs the unified deck</h1>
<p style="color:#7f93a4;line-height:1.6">You're on a single-mode server, so this tab can't switch here. Run the unified deck to get Analyze, Polish &amp; Fused on one address:</p>
<pre style="background:#0a141c;border:1px solid #263a4a;border-radius:8px;padding:12px;color:#bfeffb;font-size:13px;overflow:auto">vox --host 0.0.0.0 --port 8080</pre>
<p style="margin-top:18px"><a href="/deck" style="color:#3fe0ff;text-decoration:none">&larr; Back to this deck</a></p>
</div></body></html>"""


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

    # Mode tabs are same-origin on the unified server; standalone they'd 404 as
    # JSON (which Apple browsers download). Serve HTML here instead.
    @app.get("/fused", include_in_schema=False)
    def _mode_self():
        return RedirectResponse("/deck")

    @app.get("/polish", include_in_schema=False)
    @app.get("/analyze", include_in_schema=False)
    def _mode_elsewhere():
        return HTMLResponse(_MODE_HINT_HTML, status_code=404)

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
