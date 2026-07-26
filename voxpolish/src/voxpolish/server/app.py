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

import hashlib
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

from .session import ConflictError, Session
from .workspace import Workspace

STATIC = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB: generous for a full song

# When the deck runs standalone (single mode), the mode tabs point at sibling
# routes that only exist on the unified server. Serve a friendly HTML page there
# instead of a JSON 404 — Apple browsers *download* a JSON body, which reads as
# "the button broke". Points the user at the unified deck.
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

# Front-end assets whose content decides the cache-busting version stamped into
# index.html. A changed file → new version → the browser refetches instead of
# serving a stale cached UI (the "I updated it but still see the old look" bug).
# deck.html included: without it the injected ?v= never changed when the deck
# itself changed, so the stamp was useless as a "did my edit land?" signal.
_VERSIONED_ASSETS = ("deck.html", "index.html", "vox-tokens.css", "vox-kit.css", "style.css", "app.js", "vox-telemetry.js", "vox-about.js", "vox-theme.js", "vox-record.js", "vox-record.css")


def _asset_version() -> str:
    h = hashlib.sha1()
    for name in _VERSIONED_ASSETS:
        path = STATIC / name
        if path.is_file():
            h.update(path.read_bytes())
    return h.hexdigest()[:12]


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
        html = (STATIC / "index.html").read_text().replace("__ASSET_VERSION__", _asset_version())
        # no-cache = cache but always revalidate, so the shell (and its versioned
        # asset links) can never be served stale after a redeploy.
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})

    @app.get("/deck", response_class=HTMLResponse)
    def deck():
        """Unified VOX Suite command deck (Polish mode), on the shared kit.
        Additive alongside the classic editor at /."""
        html = (STATIC / "deck.html").read_text().replace("__ASSET_VERSION__", _asset_version())
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})

    @app.get("/api/build")
    def build(request: Request, format: str | None = None):
        """Which build is live — see the unified server's note. Duplicated here
        (small, no shared dep) so a standalone Polish server can answer it too.
        Browsers get HTML: Apple browsers download a JSON body instead of showing
        it, which is exactly what made this useless on a phone."""
        import hashlib
        import subprocess

        def h(p: Path):
            try:
                return hashlib.sha1(p.read_bytes()).hexdigest()[:12]
            except OSError:
                return None

        git = {"commit": None, "branch": None, "checkout": None}
        try:
            top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(STATIC),
                                 capture_output=True, text=True, timeout=5)
            if top.returncode == 0:
                git["checkout"] = top.stdout.strip()
                for k, a in (("commit", ["rev-parse", "--short=12", "HEAD"]),
                             ("branch", ["rev-parse", "--abbrev-ref", "HEAD"])):
                    r = subprocess.run(["git"] + a, cwd=git["checkout"],
                                       capture_output=True, text=True, timeout=5)
                    if r.returncode == 0:
                        git[k] = r.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        # Compare the served deck with this checkout's HEAD — self-validating,
        # so no expected hash has to be written down anywhere.
        at_head = None
        if git["checkout"]:
            try:
                rel = subprocess.run(["git", "ls-files", "--full-name", str(STATIC / "deck.html")],
                                     cwd=git["checkout"], capture_output=True, text=True, timeout=5)
                name = rel.stdout.strip().splitlines()[0] if rel.stdout.strip() else None
                if name:
                    blob = subprocess.run(["git", "show", f"HEAD:{name}"], cwd=git["checkout"],
                                          capture_output=True, timeout=10)
                    if blob.returncode == 0:
                        at_head = hashlib.sha1(blob.stdout).hexdigest()[:12]
            except (OSError, subprocess.SubprocessError, IndexError):
                pass
        on_disk = h(STATIC / "deck.html")
        match = None if at_head is None or on_disk is None else (on_disk == at_head)
        info = {
            "decks": {"polish": {"path": str(STATIC / "deck.html"), "sha1_12": on_disk,
                                 "exists": (STATIC / "deck.html").is_file(),
                                 "sha1_at_head": at_head, "matches_head": match}},
            "assets": {n: h(STATIC / n) for n in ("vox-kit.css", "vox-record.js")},
            "git": git,
            "matches_head": match,
            "static_dir": str(STATIC),
        }
        if format == "json" or "text/html" not in request.headers.get("accept", ""):
            return JSONResponse(info)
        try:
            from voxsuite.server.buildpage import render as render_build
        except Exception:
            return JSONResponse(info)
        return HTMLResponse(render_build(info, title="Polish build"),
                            headers={"Cache-Control": "no-store"})

    @app.get("/static/{name}")
    def static_file(name: str):
        path = STATIC / name
        if not path.is_file() or path.parent != STATIC:
            raise HTTPException(404)
        media = {"js": "text/javascript", "css": "text/css", "png": "image/png",
                 "webmanifest": "application/manifest+json"}.get(path.suffix[1:], "text/plain")
        # FileResponse streams bytes — the old read_text() corrupted binary assets.
        return FileResponse(path, media_type=media)

    # Mode tabs are same-origin on the unified server; standalone they'd 404 as
    # JSON (which Apple browsers download). Serve HTML here instead.
    @app.get("/polish", include_in_schema=False)
    def _mode_self():
        return RedirectResponse("/deck")

    @app.get("/analyze", include_in_schema=False)
    @app.get("/fused", include_in_schema=False)
    def _mode_elsewhere():
        return HTMLResponse(_MODE_HINT_HTML, status_code=404)

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
        # Report whether the pitch vocoder can actually run. Without this the UI
        # can only find out that Auto Tune is inert by rendering and reading the
        # notes — which is how a broken environment silently shipped untuned
        # audio that looked tuned.
        from ..stages import pitch as _pitch
        tune_ok, tune_why = _pitch.vocoder_status()
        return {
            "id": ws.current_id,
            "revision": s.revision(),
            "duration": doc.duration,
            "sample_rate": doc.sample_rate,
            "mode": doc.mode,
            "render": dict(render_state),
            "capabilities": {
                "tune": tune_ok,
                "tune_unavailable_reason": tune_why,
            },
        }

    @app.get("/api/document")
    def get_document():
        s = require_current()
        return JSONResponse(content={
            "revision": s.revision(),
            "document": _doc_json(s),
            # whether the Clean module can actually be re-blended at render time
            "denoise_adjustable": s.denoise_adjustable(),
        })

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
    def start_render(force: bool = False):
        s = require_current()
        if not lock.acquire(blocking=False):
            # A render is in flight — unless the worker that holds the lock is
            # dead. That leaked lock made every later render 409 forever, so the
            # UI sat on "working" with no way out. Detect it and take over.
            worker = render_state.get("_thread")
            stale = worker is None or not worker.is_alive()
            if not (stale or force):
                raise HTTPException(409, "a render is already running")
            try:
                lock.release()
            except RuntimeError:
                pass
            if not lock.acquire(blocking=False):
                raise HTTPException(409, "a render is already running")
            if stale:
                render_state.update(
                    notes=list(render_state.get("notes") or [])
                    + ["previous render did not finish cleanly — restarted"])
        render_state.update(status="running", error=None, session=ws.current_id,
                            started_at=time.time(), finished_at=None)

        def work():
            try:
                result = s.render()
                render_state.update(status="done", revision=result["revision"],
                                    notes=result.get("notes", []))
            # BaseException, not Exception: anything that escapes here (a native
            # crash surfacing as SystemExit, a MemoryError) must still move the
            # status off "running", or the UI waits forever for a COMPLETE that
            # can never arrive.
            except BaseException as e:  # noqa: BLE001
                render_state.update(status="error", error=f"{type(e).__name__}: {e}")
            finally:
                render_state.update(finished_at=time.time())
                try:
                    lock.release()
                except RuntimeError:
                    pass

        t = threading.Thread(target=work, daemon=True)
        render_state["_thread"] = t
        t.start()
        return {"status": "running"}

    # A render this long has almost certainly wedged; the UI says so rather than
    # showing a progress bar that never moves.
    RENDER_STALL_SECONDS = 180

    @app.get("/api/render")
    def render_status():
        require_current()
        out = {k: v for k, v in render_state.items() if not k.startswith("_")}
        started, finished = out.get("started_at"), out.get("finished_at")
        if out.get("status") == "running" and started:
            out["elapsed_s"] = round(time.time() - started, 1)
            worker = render_state.get("_thread")
            out["worker_alive"] = bool(worker and worker.is_alive())
            out["stalled"] = (out["elapsed_s"] > RENDER_STALL_SECONDS
                              or not out["worker_alive"])
        elif started and finished:
            out["elapsed_s"] = round(finished - started, 1)
        return out

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
