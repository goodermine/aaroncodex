"""Singnexa beta web app: invite-only sign-in, uploads, kept results.

    singnexa --host 0.0.0.0 --port 8090 --data /data/singnexa

Routes (all but /login, /healthz and /static need a signed-in user):

    GET  /                     upload + "My results"
    GET  /results/{id}         the full results page
    GET  /account              change password (forced at first sign-in)
    GET  /admin                users + every result (admins only)
    POST /api/login | /api/logout | /api/password
    GET  /api/me
    POST /api/jobs             upload (multipart: file, song, artist, capture, intent, note)
    GET  /api/jobs             my results
    GET  /api/jobs/{id}        status, and the report once complete
    GET  /api/jobs/{id}/full-results   plain text (report_builder, rule 6)
    GET  /api/jobs/{id}/technical.md   the engine's technical report
    DELETE /api/jobs/{id}      delete a result
    /api/admin/...             user management

Every state-changing request must carry ``X-Singnexa: 1`` (a cross-site page
cannot add that header, so it is the CSRF guard).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response

from . import writeup
from .pipeline import ERROR_TEXT, CanonicalPipeline, analysis_root
from .store import Store

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
SHARED_STATIC = HERE.parent / "server" / "static"   # vendored design kit (design/sync.sh)
COOKIE = "singnexa_session"

ALLOWED_SUFFIXES = {".wav", ".flac", ".aif", ".aiff", ".mp3", ".m4a", ".aac", ".ogg", ".opus"}
CAPTURES = {"studio", "home", "live"}
INTENTS = {"performance", "learning", "warmup"}
MAX_DURATION = 15 * 60

_PAGES = {"login": "login.html", "home": "home.html", "results": "results.html",
          "account": "account.html", "admin": "admin.html"}
_STATIC_OWN = {"singnexa.css": "text/css", "singnexa.js": "text/javascript"}
_STATIC_SHARED = {"vox-tokens.css": "text/css", "vox-report.css": "text/css",
                  "vox-report.js": "text/javascript", "vox-icon-192.png": "image/png",
                  "vox-icon-180.png": "image/png"}

SECURITY_HEADERS = {
    "Content-Security-Policy": ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                                "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
                                "base-uri 'none'; form-action 'self'"),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _report_builder():
    viewer = analysis_root() / "viewer"
    if str(viewer) not in sys.path:
        sys.path.insert(0, str(viewer))
    import report_builder
    return report_builder


def lead_score(score: dict) -> dict | None:
    """Rule 5: lead with the HIGHER of overall and capture-fair, the other beside it."""
    o, c = score.get("overall"), score.get("capture_fair")
    if o is None and c is None:
        return None
    if c is None or (o is not None and o >= c):
        return {"value": o, "label": "overall", "other_value": c, "other_label": "capture-fair"}
    return {"value": c, "label": "capture-fair", "other_value": o, "other_label": "overall"}


class Throttle:
    """Failed sign-ins per key in a sliding window."""

    def __init__(self, limit: int, window_s: int):
        self.limit, self.window = limit, window_s
        self.hits: dict[str, deque] = defaultdict(deque)

    def blocked(self, key: str) -> bool:
        q, now = self.hits[key], time.time()
        while q and q[0] < now - self.window:
            q.popleft()
        return len(q) >= self.limit

    def fail(self, key: str) -> None:
        self.hits[key].append(time.time())

    def clear(self, key: str) -> None:
        self.hits.pop(key, None)


def create_app(data_dir, pipeline=None, *, cookie_secure: bool | None = None,
               writeup_client=None) -> FastAPI:
    data = Path(data_dir)
    data.mkdir(parents=True, exist_ok=True)
    results_dir = data / "results"
    results_dir.mkdir(exist_ok=True)
    store = Store(data / "singnexa.db")
    if pipeline is None:
        pipeline = CanonicalPipeline(data / "work", workers=_env_int("SINGNEXA_WORKERS", 1))
    if cookie_secure is None:
        cookie_secure = os.environ.get("SINGNEXA_COOKIE_SECURE", "1") != "0"
    max_bytes = _env_int("SINGNEXA_MAX_UPLOAD_MB", 300) * 1024 * 1024
    daily_limit = _env_int("SINGNEXA_DAILY_LIMIT", 10)
    per_user_active = _env_int("SINGNEXA_USER_ACTIVE", 2)
    max_queue = _env_int("SINGNEXA_MAX_QUEUE", 20)
    rb = _report_builder()
    # Write-ups wait on the network, so they get their own thread and never hold
    # an analysis worker.
    writeup_on = writeup_client is not None or writeup.enabled()
    writer = ThreadPoolExecutor(max_workers=2) if writeup_on else None

    # Jobs the previous process never finished: its queue lived in memory.
    for job in store.interrupted_jobs():
        store.update_job(job["id"], status="failed", stage="failed", error_code="worker_unavailable")
        pipeline.discard(job["id"])

    app = FastAPI(title="Singnexa", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store, app.state.pipeline = store, pipeline
    user_throttle, ip_throttle = Throttle(8, 15 * 60), Throttle(40, 15 * 60)

    # ---- middleware: CSRF header, upload size gate, security headers -----
    @app.middleware("http")
    async def guard(request: Request, call_next):
        path, method = request.url.path, request.method
        if path.startswith("/api/") and method in {"POST", "PUT", "PATCH", "DELETE"}:
            if request.headers.get("x-singnexa") != "1":
                return JSONResponse({"detail": {"code": "bad_request_origin"}}, status_code=403)
        if path == "/api/jobs" and method == "POST":
            length = request.headers.get("content-length")
            if not length or not length.isdigit():
                return JSONResponse({"detail": {"code": "length_required"}}, status_code=411)
            if int(length) > max_bytes + 1024 * 1024:
                return JSONResponse({"detail": {"code": "media_too_large",
                                                "max_mb": max_bytes // (1024 * 1024)}}, status_code=413)
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if cookie_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        if path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    # ---- helpers --------------------------------------------------------
    def current_user(request: Request) -> dict | None:
        return store.session_user(request.cookies.get(COOKIE))

    def require_user(request: Request, allow_pending: bool = False) -> dict:
        user = current_user(request)
        if not user:
            raise HTTPException(401, {"code": "sign_in_required"})
        if user["must_change_password"] and not allow_pending:
            raise HTTPException(403, {"code": "password_change_required"})
        return user

    def require_admin(request: Request) -> dict:
        user = require_user(request)
        if not user["is_admin"]:
            raise HTTPException(403, {"code": "admin_only"})
        return user

    def public_user(u: dict) -> dict:
        return {"username": u["username"], "display_name": u["display_name"], "is_admin": bool(u["is_admin"]),
                "must_change_password": bool(u["must_change_password"])}

    def owned_job(request: Request, job_id: str) -> tuple[dict, dict]:
        user = require_user(request)
        try:
            job_id = str(uuid.UUID(job_id))
        except ValueError:
            raise HTTPException(404, {"code": "not_found"})
        job = store.job(job_id)
        if not job or (job["user_id"] != user["id"] and not user["is_admin"]):
            raise HTTPException(404, {"code": "not_found"})   # never confirm someone else's job exists
        return user, job

    def build_report(job: dict) -> tuple[dict, dict]:
        folder = results_dir / job["id"]
        raw = json.loads((folder / "analysis.json").read_text(encoding="utf-8"))
        result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        report = rb.build_v2_report(raw, conditions=result.get("recording_conditions", ""))
        pf = pipeline.preflight or {}
        if pf.get("ok") is not True:
            score = report.setdefault("score", {})
            score["overall"] = score["capture_fair"] = None
            score["withheld_reason"] = ("this server's engine check (score preflight) did not pass, so the "
                                        "headline score is withheld; everything else below is measured as normal")
        return report, result

    def job_view(job: dict, include_report: bool = False) -> dict:
        view = {k: job[k] for k in ("id", "status", "stage", "song", "artist", "capture", "intent",
                                    "original_filename", "duration_s", "confidence", "created_at", "updated_at")}
        view["lead"] = lead_score({"overall": job["overall"], "capture_fair": job["capture_fair"]})
        if job.get("username"):
            view["singer"] = job.get("display_name") or job["username"]
        if job["status"] in {"queued", "processing"}:
            view["stage"] = pipeline.stage(job["id"]) or job["stage"]
        if job["status"] == "failed":
            code = job["error_code"] or "analysis_failed"
            view["error"] = {"code": code, "message": ERROR_TEXT.get(code, ERROR_TEXT["analysis_failed"])}
        if include_report and job["status"] == "complete":
            report, result = build_report(job)
            view["report"], view["result"] = report, result
            view["lead"] = lead_score(report.get("score") or {})
            view["writeup"] = read_writeup(job["id"])
        return view

    def read_writeup(job_id: str) -> dict:
        try:
            saved = json.loads((results_dir / job_id / "writeup.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"status": "pending" if writeup_on else "disabled"}
        return {k: saved[k] for k in ("status", "markdown") if k in saved}

    def write_up(job_id: str) -> None:
        """Runs on the writer thread; a failure only means no write-up."""
        folder = results_dir / job_id
        try:
            job = store.job(job_id) or {}
            singer = store.user_by_id(job["user_id"]) or {}
            report, result = build_report(job)
            text = rb.render_full_results_text(report, result)
            raw = json.loads((folder / "analysis.json").read_text(encoding="utf-8"))
            outcome = writeup.generate(
                text, client=writeup_client, singer=singer.get("display_name") or singer.get("username") or "",
                song=job.get("song") or "", artist=job.get("artist") or "",
                take_context=raw.get("take_context"))
        except Exception as exc:
            outcome = {"status": "failed", "reason": exc.__class__.__name__}
        if folder.is_dir():   # the singer may have deleted the result meanwhile
            (folder / "writeup.json").write_text(json.dumps(outcome), encoding="utf-8")

    def on_finish(job_id: str, outcome: dict) -> None:
        if outcome.get("status") != "complete":
            store.update_job(job_id, status="failed", stage="failed",
                             error_code=outcome.get("code") or "analysis_failed",
                             error_reason=(outcome.get("reason") or "")[:200])
            return
        folder = results_dir / job_id
        folder.mkdir(parents=True, exist_ok=True)
        job = store.job(job_id) or {}
        result = dict(outcome.get("result") or {})
        result["file_name"] = job.get("original_filename") or "upload"
        (folder / "analysis.json").write_text(json.dumps(outcome["raw"]), encoding="utf-8")
        (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
        (folder / "technical.md").write_text(outcome.get("technical_md") or "", encoding="utf-8")
        store.update_job(job_id, status="complete", stage="complete")
        report, _ = build_report(store.job(job_id))
        s = report.get("score") or {}
        store.update_job(job_id, overall=s.get("overall"), capture_fair=s.get("capture_fair"),
                         confidence=s.get("confidence"))
        if writer is not None:
            writer.submit(write_up, job_id)

    # ---- pages ----------------------------------------------------------
    def page(name: str) -> HTMLResponse:
        html = (STATIC / _PAGES[name]).read_text(encoding="utf-8")
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})

    def gate(request: Request, admin: bool = False):
        user = current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        if user["must_change_password"]:
            return RedirectResponse("/account", status_code=303)
        if admin and not user["is_admin"]:
            return RedirectResponse("/", status_code=303)
        return None

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request):
        return RedirectResponse("/", status_code=303) if current_user(request) else page("login")

    @app.get("/", response_class=HTMLResponse)
    def home_page(request: Request):
        return gate(request) or page("home")

    @app.get("/results/{job_id}", response_class=HTMLResponse)
    def results_page(request: Request, job_id: str):
        return gate(request) or page("results")

    @app.get("/account", response_class=HTMLResponse)
    def account_page(request: Request):
        return page("account") if current_user(request) else RedirectResponse("/login", status_code=303)

    @app.get("/admin", response_class=HTMLResponse)
    def admin_page(request: Request):
        return gate(request, admin=True) or page("admin")

    @app.get("/static/{name}")
    def static_file(name: str):
        if name in _STATIC_OWN:
            return FileResponse(STATIC / name, media_type=_STATIC_OWN[name], headers={"Cache-Control": "no-cache"})
        if name in _STATIC_SHARED and (SHARED_STATIC / name).is_file():
            return FileResponse(SHARED_STATIC / name, media_type=_STATIC_SHARED[name], headers={"Cache-Control": "no-cache"})
        raise HTTPException(404)

    @app.get("/favicon.ico")
    def favicon():
        return Response(status_code=204)

    @app.get("/healthz")
    def healthz():
        pf = pipeline.preflight or {}
        # commit = the deployed code (VOX_BUILD_COMMIT build arg); the "build"
        # in a report is the scorer's rubric fingerprint, a different thing.
        return {"ok": True, "scores_published": pf.get("ok") is True,
                "commit": os.environ.get("VOX_BUILD_COMMIT") or None}

    # ---- auth API -------------------------------------------------------
    @app.post("/api/login")
    async def login(request: Request):
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(400, {"code": "bad_request"})
        username = str(body.get("username") or "").strip().lower()[:64]
        password = str(body.get("password") or "")[:256]
        ip = request.client.host if request.client else "?"
        if user_throttle.blocked(username) or ip_throttle.blocked(ip):
            raise HTTPException(429, {"code": "too_many_attempts",
                                      "message": "Too many attempts. Wait 15 minutes and try again."})
        user = store.authenticate(username, password)
        if not user:
            user_throttle.fail(username)
            ip_throttle.fail(ip)
            raise HTTPException(401, {"code": "bad_credentials", "message": "Wrong username or password."})
        user_throttle.clear(username)
        token = store.start_session(user["id"])
        resp = JSONResponse({"user": public_user(user)})
        resp.set_cookie(COOKIE, token, max_age=30 * 24 * 3600, httponly=True, secure=cookie_secure,
                        samesite="lax", path="/")
        return resp

    @app.post("/api/logout")
    def logout(request: Request):
        store.end_session(request.cookies.get(COOKIE))
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(COOKIE, path="/")
        return resp

    @app.get("/api/me")
    def me(request: Request):
        user = require_user(request, allow_pending=True)
        return {"user": public_user(user), "limits": {"max_upload_mb": max_bytes // (1024 * 1024),
                                                      "daily_uploads": daily_limit,
                                                      "max_minutes": MAX_DURATION // 60,
                                                      "formats": sorted(s.lstrip(".") for s in ALLOWED_SUFFIXES)}}

    @app.post("/api/password")
    async def change_password(request: Request):
        user = require_user(request, allow_pending=True)
        body = await request.json()
        if not store.authenticate(user["username"], str(body.get("current") or "")):
            raise HTTPException(400, {"code": "bad_credentials", "message": "Your current password is wrong."})
        new = str(body.get("new") or "")
        if new == str(body.get("current") or ""):
            raise HTTPException(400, {"code": "same_password", "message": "Choose a new password."})
        try:
            store.set_password(user["id"], new)
        except ValueError as exc:
            raise HTTPException(400, {"code": "weak_password", "message": str(exc)})
        store.end_sessions(user["id"], keep=request.cookies.get(COOKIE))
        return {"ok": True}

    # ---- jobs API -------------------------------------------------------
    @app.post("/api/jobs", status_code=202)
    async def create_job(request: Request, file: UploadFile = File(...), song: str = Form(""),
                         artist: str = Form(""), capture: str = Form(""), intent: str = Form(""),
                         note: str = Form(""), keep_talk: str = Form("")):
        user = require_user(request)
        try:
            capture = capture.strip().lower()
            if capture not in CAPTURES:
                raise HTTPException(422, {"code": "missing_capture",
                                          "message": "Choose studio, home or live."})
            suffix = Path(file.filename or "").suffix.lower()
            if suffix not in ALLOWED_SUFFIXES:
                raise HTTPException(415, {"code": "unsupported_media",
                                          "message": "Upload WAV, FLAC, AIFF, MP3, M4A, AAC, OGG or Opus."})
            if store.active_jobs(user["id"]) >= per_user_active:
                raise HTTPException(429, {"code": "busy",
                                          "message": "Wait for your current analysis to finish first."})
            if store.jobs_since(user["id"], time.time() - 24 * 3600) >= daily_limit and not user["is_admin"]:
                raise HTTPException(429, {"code": "daily_limit",
                                          "message": f"The beta allows {daily_limit} uploads a day."})
            if store.active_jobs() >= max_queue:
                raise HTTPException(503, {"code": "queue_full", "message": "The queue is full. Try again soon."})
            job_id = str(uuid.uuid4())
            dest = pipeline.new_upload_path(job_id, suffix)
            size = 0
            try:
                with dest.open("wb") as out:
                    while chunk := await file.read(1024 * 1024):
                        size += len(chunk)
                        if size > max_bytes:
                            raise HTTPException(413, {"code": "media_too_large",
                                                      "max_mb": max_bytes // (1024 * 1024)})
                        out.write(chunk)
                duration = _probe_duration(dest)
                if duration <= 0:
                    raise HTTPException(415, {"code": "unsupported_media",
                                              "message": "That file couldn't be decoded as audio."})
                if duration > MAX_DURATION:
                    raise HTTPException(422, {"code": "media_too_long",
                                              "message": "Recordings can be up to 15 minutes."})
            except BaseException:
                pipeline.discard(job_id)
                raise
            clean = lambda v, n: " ".join((v or "").split())[:n]
            intent = intent.strip().lower()
            meta = {"song": clean(song, 160), "artist": clean(artist, 160), "capture": capture,
                    "intent": intent if intent in INTENTS else "", "note": clean(note, 200),
                    "original_filename": clean(Path(file.filename or "").name, 160),
                    "size_bytes": size, "duration_s": round(duration, 2)}
            store.create_job(job_id, user["id"], **meta)
            ctx = {"capture": capture, **({"intent": meta["intent"]} if meta["intent"] else {}),
                   **({"note": meta["note"]} if meta["note"] else {})}
            try:
                cut_talk = keep_talk.strip() != "1" and os.environ.get("SINGNEXA_CUT_TALK", "1") != "0"
                pipeline.submit(job_id, dest, {**meta, "performer_name": user["display_name"],
                                               "take_context": ctx, "cut_talk": cut_talk}, on_finish,
                                on_start=lambda jid: store.update_job(jid, status="processing",
                                                                      stage="separating_vocals"))
            except Exception:
                pipeline.discard(job_id)
                store.update_job(job_id, status="failed", stage="failed", error_code="worker_unavailable")
                raise HTTPException(503, {"code": "worker_unavailable", "message": ERROR_TEXT["worker_unavailable"]})
            return {"id": job_id, "status": "queued", "url": f"/results/{job_id}"}
        finally:
            await file.close()

    @app.get("/api/jobs")
    def list_jobs(request: Request):
        user = require_user(request)
        return {"jobs": [job_view(j) for j in store.jobs_for(user["id"])]}

    @app.get("/api/jobs/{job_id}")
    def get_job(request: Request, job_id: str):
        _, job = owned_job(request, job_id)
        return job_view(job, include_report=True)

    @app.get("/api/jobs/{job_id}/full-results")
    def full_results(request: Request, job_id: str):
        _, job = owned_job(request, job_id)
        if job["status"] != "complete":
            raise HTTPException(409, {"code": "not_ready"})
        report, result = build_report(job)
        text = rb.render_full_results_text(report, result)
        return PlainTextResponse(text)

    @app.get("/api/jobs/{job_id}/technical.md")
    def technical(request: Request, job_id: str):
        _, job = owned_job(request, job_id)
        path = results_dir / job["id"] / "technical.md"
        if job["status"] != "complete" or not path.is_file():
            raise HTTPException(409, {"code": "not_ready"})
        return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")

    @app.delete("/api/jobs/{job_id}")
    def delete_job(request: Request, job_id: str):
        _, job = owned_job(request, job_id)
        if job["status"] in {"queued", "processing"}:
            raise HTTPException(409, {"code": "still_running", "message": "Wait until the analysis finishes."})
        shutil.rmtree(results_dir / job["id"], ignore_errors=True)
        store.delete_job(job["id"])
        return {"ok": True}

    # ---- admin API ------------------------------------------------------
    @app.get("/api/admin/overview")
    def admin_overview(request: Request):
        require_admin(request)
        users = store.list_users()
        return {"users": [{**u, "is_admin": bool(u["is_admin"]), "disabled": bool(u["disabled"]),
                           "must_change_password": bool(u["must_change_password"])} for u in users],
                "jobs": [job_view(j) for j in store.jobs_for(None)],
                "preflight": pipeline.preflight}

    @app.post("/api/admin/users")
    async def admin_create_user(request: Request):
        require_admin(request)
        body = await request.json()
        try:
            user, temp = store.create_user(str(body.get("username") or ""), str(body.get("display_name") or ""),
                                           is_admin=bool(body.get("is_admin")))
        except ValueError as exc:
            raise HTTPException(400, {"code": "bad_user", "message": str(exc)})
        return {"user": public_user(user), "temporary_password": temp}

    def _target(user_id: int, me: dict) -> dict:
        target = store.user_by_id(user_id)
        if not target:
            raise HTTPException(404, {"code": "not_found"})
        if target["id"] == me["id"]:
            raise HTTPException(400, {"code": "self", "message": "Use the account page for your own login."})
        return target

    @app.post("/api/admin/users/{user_id}/reset")
    def admin_reset(request: Request, user_id: int):
        target = _target(user_id, require_admin(request))
        return {"username": target["username"], "temporary_password": store.reset_password(target["id"])}

    @app.post("/api/admin/users/{user_id}/disable")
    def admin_disable(request: Request, user_id: int):
        store.set_disabled(_target(user_id, require_admin(request))["id"], True)
        return {"ok": True}

    @app.post("/api/admin/users/{user_id}/enable")
    def admin_enable(request: Request, user_id: int):
        store.set_disabled(_target(user_id, require_admin(request))["id"], False)
        return {"ok": True}

    @app.post("/api/admin/preflight")
    def admin_preflight(request: Request):
        require_admin(request)
        refresh = getattr(pipeline, "refresh_preflight", None)
        return refresh() if refresh else pipeline.preflight

    return app


def _probe_duration(path: Path) -> float:
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=nw=1:nk=1", str(path)],
                               capture_output=True, text=True, timeout=60)
        return float(probe.stdout.strip()) if probe.returncode == 0 else 0.0
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0


def main(argv=None) -> None:
    import argparse

    import uvicorn

    ap = argparse.ArgumentParser(prog="singnexa", description="Run the Singnexa beta web app.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--data", default=os.environ.get("SINGNEXA_DATA", "./_singnexa"))
    args = ap.parse_args(argv)
    # proxy_headers: the HTTPS tunnel/proxy in front sets X-Forwarded-*.
    uvicorn.run(create_app(args.data), host=args.host, port=args.port, log_level="info",
                proxy_headers=True, forwarded_allow_ips=os.environ.get("SINGNEXA_TRUSTED_PROXIES", "127.0.0.1"))


if __name__ == "__main__":
    main()
