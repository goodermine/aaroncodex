"""FastAPI app for the editor UI.

Disaster-3 defenses: renders run in a background worker with a single-flight
lock (a second request gets a clean 409, never a pile-up); audio streams with
HTTP range support; waveforms are served as small precomputed peak files.
"""

from __future__ import annotations

import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from .session import ConflictError, Session

STATIC = Path(__file__).parent / "static"


def create_app(session_root: Path) -> FastAPI:
    app = FastAPI(title="VoxPolish", docs_url=None, redoc_url=None)
    session = Session(Path(session_root))
    if not Session.is_session(session.root):
        raise RuntimeError(f"{session_root} is not a VoxPolish session")

    lock = threading.Lock()
    render_state = {"status": "idle", "error": None, "revision": session.revision()}

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

    @app.get("/api/session")
    def get_session():
        doc = session.document()
        return {
            "revision": session.revision(),
            "duration": doc.duration,
            "sample_rate": doc.sample_rate,
            "mode": doc.mode,
            "render": dict(render_state),
        }

    @app.get("/api/document")
    def get_document():
        return JSONResponse(
            content={"revision": session.revision(), "document": _doc_json(session)}
        )

    @app.put("/api/document")
    async def put_document(request: Request):
        body = await request.json()
        try:
            new_rev = session.update_document(
                _as_json(body["document"]), expected_revision=int(body["revision"])
            )
        except ConflictError as e:
            raise HTTPException(409, str(e))
        except (KeyError, TypeError, ValueError) as e:
            raise HTTPException(422, f"document rejected: {e}")
        return {"revision": new_rev}

    @app.post("/api/render")
    def start_render():
        if not lock.acquire(blocking=False):
            raise HTTPException(409, "a render is already running")
        render_state.update(status="running", error=None)

        def work():
            try:
                result = session.render()
                render_state.update(
                    status="done",
                    revision=result["revision"],
                    notes=result.get("notes", []),
                )
            except Exception as e:  # surfaced to the UI, never silent
                render_state.update(status="error", error=str(e))
            finally:
                lock.release()

        threading.Thread(target=work, daemon=True).start()
        return {"status": "running"}

    @app.get("/api/render")
    def render_status():
        return dict(render_state)

    @app.get("/api/peaks/{name}")
    def peaks(name: str):
        try:
            return session.peaks(name)
        except KeyError:
            raise HTTPException(404, f"unknown audio '{name}'")
        except FileNotFoundError:
            raise HTTPException(404, f"'{name}' not rendered yet")

    @app.get("/api/audio/{name}")
    def audio(name: str):
        try:
            path = session._audio_path(name)
        except KeyError:
            raise HTTPException(404, f"unknown audio '{name}'")
        if not path.exists():
            raise HTTPException(404, f"'{name}' not rendered yet")
        # FileResponse handles HTTP range requests for streaming playback.
        return FileResponse(path, media_type="audio/wav")

    return app


def _doc_json(session: Session):
    import json

    return json.loads(session.document().to_json())


def _as_json(document) -> str:
    import json

    return json.dumps(document) if not isinstance(document, str) else document


def serve(session_root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    uvicorn.run(create_app(session_root), host=host, port=port, log_level="warning")
