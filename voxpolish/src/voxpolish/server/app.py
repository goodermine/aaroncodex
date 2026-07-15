"""FastAPI app for the editor UI.

Workspace model: many sessions under one base dir with a "current" pointer.
The CLI opens a file as the current session; the web upload flow creates new
sessions. All editor routes act on the current session.

Disaster-3 defenses: renders run in a background worker with a single-flight
lock (a second request gets a clean 409, never a pile-up); audio streams with
HTTP range support; waveforms are served as small precomputed peak files;
uploads process in a background job with polled progress.
"""

from __future__ import annotations

import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from .session import ConflictError, Session
from .workspace import Workspace

STATIC = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB: generous for a full song


def create_app(root: Path) -> FastAPI:
    """root may be a single session folder (CLI) or a workspace base dir."""
    root = Path(root)
    if Session.is_session(root):
        ws = Workspace(root.parent)
        ws.register(root)
    else:
        ws = Workspace(root)

    app = FastAPI(title="VoxPolish", docs_url=None, redoc_url=None)
    lock = threading.Lock()
    # Render progress for the current session; reset whenever current changes.
    render_state = {"status": "idle", "error": None, "revision": 0, "session": None}

    def require_current() -> Session:
        s = ws.current()
        if s is None:
            raise HTTPException(409, "no session loaded — upload a recording to start")
        # Reset render state when the current session changed underneath us.
        if render_state.get("session") != ws.current_id:
            render_state.update(status="idle", error=None,
                                revision=s.revision(), session=ws.current_id, notes=[])
        return s

    # ----------------------------------------------------------------- pages

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (STATIC / "index.html").read_text()

    @app.get("/static/{name}")
    def static_file(name: str):
        path = STATIC / name
        if not path.is_file() or path.parent != STATIC:
            raise HTTPException(404)
        media = {"js": "text/javascript", "css": "text/css"}.get(path.suffix[1:], "text/plain")
        return Response(path.read_text(), media_type=media)

    # ------------------------------------------------------------- workspace

    @app.get("/api/workspace")
    def workspace():
        return {"current": ws.current_id, "sessions": ws.list()}

    @app.post("/api/session/{session_id}/select")
    def select_session(session_id: str):
        if ws.get(session_id) is None:
            raise HTTPException(404, f"unknown session '{session_id}'")
        ws.current_id = session_id
        return {"current": ws.current_id}

    # ---------------------------------------------------------------- upload

    @app.post("/api/uploads")
    async def create_upload(
        file: UploadFile = File(...),
        tune: bool = Form(True),
    ):
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "file too large (500 MB max)")
        try:
            job = ws.start_upload(file.filename or "audio", data, tune)
        except ValueError as e:
            raise HTTPException(422, str(e))
        return job.as_dict()

    @app.get("/api/uploads/{job_id}")
    def upload_status(job_id: str):
        job = ws.job(job_id)
        if job is None:
            raise HTTPException(404, f"unknown job '{job_id}'")
        return job.as_dict()

    # ---------------------------------------------------------------- editor

    @app.get("/api/session")
    def get_session():
        s = require_current()
        doc = s.document()
        return {
            "id": ws.current_id,
            "revision": s.revision(),
            "duration": doc.duration,
            "sample_rate": doc.sample_rate,
            "mode": doc.mode,
            "render": dict(render_state),
        }

    @app.get("/api/document")
    def get_document():
        s = require_current()
        return JSONResponse(content={"revision": s.revision(), "document": _doc_json(s)})

    @app.put("/api/document")
    async def put_document(request: Request):
        s = require_current()
        body = await request.json()
        try:
            new_rev = s.update_document(
                _as_json(body["document"]), expected_revision=int(body["revision"])
            )
        except ConflictError as e:
            raise HTTPException(409, str(e))
        except (KeyError, TypeError, ValueError) as e:
            raise HTTPException(422, f"document rejected: {e}")
        return {"revision": new_rev}

    @app.post("/api/render")
    def start_render():
        s = require_current()
        if not lock.acquire(blocking=False):
            raise HTTPException(409, "a render is already running")
        render_state.update(status="running", error=None, session=ws.current_id)

        def work():
            try:
                result = s.render()
                render_state.update(status="done", revision=result["revision"],
                                    notes=result.get("notes", []))
            except Exception as e:  # surfaced to the UI, never silent
                render_state.update(status="error", error=str(e))
            finally:
                lock.release()

        threading.Thread(target=work, daemon=True).start()
        return {"status": "running"}

    @app.get("/api/render")
    def render_status():
        require_current()
        return dict(render_state)

    @app.get("/api/peaks/{name}")
    def peaks(name: str):
        s = require_current()
        try:
            return s.peaks(name)
        except KeyError:
            raise HTTPException(404, f"unknown audio '{name}'")
        except FileNotFoundError:
            raise HTTPException(404, f"'{name}' not rendered yet")

    @app.get("/api/audio/{name}")
    def audio(name: str):
        s = require_current()
        try:
            path = s._audio_path(name)
        except KeyError:
            raise HTTPException(404, f"unknown audio '{name}'")
        if not path.exists():
            raise HTTPException(404, f"'{name}' not rendered yet")
        # FileResponse handles HTTP range requests for streaming playback.
        return FileResponse(path, media_type="audio/wav")

    @app.get("/api/download")
    def download():
        s = require_current()
        path = s._audio_path("cleaned")
        if not path.exists():
            raise HTTPException(404, "nothing rendered to download yet")
        # filename= sets Content-Disposition: attachment, so the browser saves.
        return FileResponse(path, media_type="audio/wav", filename=s.download_name())

    return app


def _doc_json(session: Session):
    import json

    return json.loads(session.document().to_json())


def _as_json(document) -> str:
    import json

    return json.dumps(document) if not isinstance(document, str) else document


def serve(root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    uvicorn.run(create_app(root), host=host, port=port, log_level="warning")
