"""Unified VOX Suite server — one process, one port, one origin.

Runs the whole suite behind a single FastAPI app so it needs only **one**
Tailscale address and the mode tabs are same-origin links (no ports):

    GET /            → Fused deck (home)
    GET /analyze     → Analyze deck
    GET /polish      → Polish deck
    GET /fused       → Fused deck (same as /)
    GET /static/{n}  → one shared asset tree
    /api/pitch-jobs…  /api/document…  /api/fused-jobs…   (all three engines)

Each existing engine app stays authoritative for its own routes. This module
builds all three and harvests their *disjoint* ``/api/*`` routes onto the
unified app, then serves the three deck shells and one shared ``/static`` tree
itself. Because the API prefixes never collide, the decks' existing absolute
``/static`` / ``/api`` paths keep working unchanged — no per-mount rewriting.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.routing import APIRoute

# The shared kit + the Fused deck shell live in voxsuite's static dir, which is
# a superset of what every deck references — so one /static serves all three.
STATIC = Path(__file__).parent / "static"
_MEDIA = {"css": "text/css", "js": "text/javascript", "html": "text/html", "json": "application/json", "png": "image/png", "webmanifest": "application/manifest+json"}


def _analysis_root() -> Path:
    """Repo location of the (non-packaged) voxanalysis engine + viewer."""
    env = os.environ.get("VOX_ANALYSIS_ROOT")
    if env:
        return Path(env)
    # voxsuite/src/voxsuite/server/unified.py → parents[4] == repo root
    return Path(__file__).resolve().parents[4] / "voxanalysis" / "vox-analysis"


def _pitchmonitor_root() -> Path:
    """Repo location of the standalone Pitch Monitor page (self-contained)."""
    env = os.environ.get("VOX_PITCHMONITOR_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[4] / "pitchmonitor"


def _timbertones_root() -> Path:
    """Repo location of the standalone TimberTones page (piano + pitch-match
    trainer, self-contained apart from its samples/ asset dir)."""
    env = os.environ.get("VOX_TIMBERTONES_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[4] / "timbertones"


def _load_analyze_module(runtime: Path):
    """Import voxanalysis' viewer/app.py under an explicit module name.

    It's a loose script (no package), so its dir must be on sys.path for its
    own ``import report_builder`` to resolve. We stamp VOX_PITCH_RUNTIME first so
    the analyze job store lands under the unified base dir.
    """
    root = _analysis_root()
    os.environ.setdefault("VOX_PITCH_RUNTIME", str(runtime))
    for p in (root / "engine", root / "viewer"):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)
    spec = importlib.util.spec_from_file_location("vox_analyze_viewer_app", root / "viewer" / "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # runs the module's guard/cleanup + defines app
    return mod


def _harvest_api(dst: FastAPI, src: FastAPI) -> None:
    """Copy a sub-app's ``/api/*`` routes onto the unified app. The endpoints
    close over their sub-app's state, so they keep working as-is."""
    for route in src.router.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api"):
            dst.router.routes.append(route)


def create_unified_app(base_dir, engines=None) -> FastAPI:
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    (base / "polish").mkdir(exist_ok=True)
    (base / "fused").mkdir(exist_ok=True)
    (base / "analyze").mkdir(exist_ok=True)

    # Build each engine app (each authoritative for its own /api/* routes).
    from voxpolish.server.app import STATIC as POLISH_STATIC, create_app as polish_create
    from .app import _asset_version, create_app as fused_create

    analyze_mod = _load_analyze_module(base / "analyze")
    analyze_app = analyze_mod.app
    polish_app = polish_create(base / "polish")
    fused_app = fused_create(base / "fused", engines=engines)

    shells = {
        "fused": STATIC / "deck.html",
        "analyze": analyze_mod.HERE / "static" / "deck.html",
        "polish": POLISH_STATIC / "deck.html",
    }

    app = FastAPI(title="VOX Suite", docs_url=None, redoc_url=None)
    # Keep the sub-apps referenced so their route closures (state) stay alive.
    app.state.sub_apps = {"analyze": analyze_app, "polish": polish_app, "fused": fused_app}

    def _shell(path: Path) -> HTMLResponse:
        html = path.read_text(encoding="utf-8").replace("__ASSET_VERSION__", _asset_version())
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})

    @app.get("/", response_class=HTMLResponse)
    @app.get("/fused", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        return _shell(shells["fused"])

    @app.get("/analyze", response_class=HTMLResponse)
    def analyze_deck() -> HTMLResponse:
        return _shell(shells["analyze"])

    @app.get("/polish", response_class=HTMLResponse)
    def polish_deck() -> HTMLResponse:
        return _shell(shells["polish"])

    @app.get("/monitor")
    def pitch_monitor_redirect():
        """The monitor lives under /monitor/ (trailing slash) so its RELATIVE
        asset link (vox-tokens.css) resolves to /monitor/vox-tokens.css. Served
        at bare /monitor the browser asked for /vox-tokens.css, 404'd, and the
        page rendered unstyled with a black canvas grid."""
        return RedirectResponse(url="/monitor/", status_code=307)

    @app.get("/monitor/", response_class=HTMLResponse)
    def pitch_monitor() -> HTMLResponse:
        """Real-time pitch monitor. Rides the suite's HTTPS origin for the
        secure context the mic (getUserMedia) needs on phones."""
        path = _pitchmonitor_root() / "index.html"
        if not path.is_file():
            raise HTTPException(404, "pitch monitor not installed")
        return HTMLResponse(path.read_text(encoding="utf-8"), headers={"Cache-Control": "no-cache"})

    @app.get("/monitor/{asset}")
    def pitch_monitor_asset(asset: str):
        """Sibling assets for the monitor (vox-tokens.css, vendored by
        design/sync.sh) — lets the page use one relative link that also works
        when the directory is served or opened standalone."""
        clean = Path(asset).name
        path = _pitchmonitor_root() / clean
        if clean != asset or not path.is_file() or path.suffix not in {".css", ".png", ".webmanifest"}:
            raise HTTPException(404, "not found")
        media = {".css": "text/css", ".png": "image/png", ".webmanifest": "application/manifest+json"}[path.suffix]
        return Response(path.read_bytes(), media_type=media, headers={"Cache-Control": "no-cache"})

    @app.get("/timbertones")
    def timbertones_redirect():
        """Same trailing-slash reasoning as /monitor: TimberTones' relative asset
        links (vox-tokens.css, samples/…) must resolve under /timbertones/."""
        return RedirectResponse(url="/timbertones/", status_code=307)

    @app.get("/timbertones/", response_class=HTMLResponse)
    def timbertones() -> HTMLResponse:
        """TimberTones — a sampled piano fused with a live pitch-match trainer.
        Rides the suite's HTTPS origin so the mic (getUserMedia) has the secure
        context it needs on phones, same as the monitor."""
        path = _timbertones_root() / "index.html"
        if not path.is_file():
            raise HTTPException(404, "timbertones not installed")
        return HTMLResponse(path.read_text(encoding="utf-8"), headers={"Cache-Control": "no-cache"})

    @app.get("/timbertones/{sub:path}")
    def timbertones_asset(sub: str):
        """Sibling assets and the samples/ tree (vox-tokens.css, manifest.json,
        <midi>.mp3). Resolved inside the app root with a suffix whitelist and a
        traversal guard so a crafted path can't escape the directory."""
        root = _timbertones_root().resolve()
        path = (root / sub).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            raise HTTPException(404, "not found")
        media = {".css": "text/css", ".png": "image/png", ".webmanifest": "application/manifest+json",
                 ".mp3": "audio/mpeg", ".json": "application/json", ".js": "text/javascript"}.get(path.suffix)
        if not path.is_file() or media is None:
            raise HTTPException(404, "not found")
        return Response(path.read_bytes(), media_type=media, headers={"Cache-Control": "no-cache"})

    @app.get("/hub", response_class=HTMLResponse)
    def hub() -> HTMLResponse:
        """The systems directory — every VOX system as a card with a live status
        dot, rendered from the registry + this app's own route table so a moved
        or removed path shows up immediately. Same-origin (relative) links, so
        they follow the suite to whatever address it's hosted on."""
        from .hubpage import render
        from .systems import resolve
        systems = resolve(app, base_url="")   # relative paths: never stale on host change
        return HTMLResponse(render(systems, api_url="/api/systems"), headers={"Cache-Control": "no-cache"})

    @app.get("/api/systems")
    def api_systems(request: Request):
        """Machine-readable registry — the source the standalone hub polls to stay
        current. URLs are absolute (built from this request's origin) so a page
        hosted elsewhere gets working links; ``path`` stays relative alongside."""
        from .systems import resolve
        base = str(request.base_url).rstrip("/")
        systems = resolve(app, base_url=base)
        return JSONResponse({"origin": base, "count": len(systems), "systems": systems})

    @app.get("/api/build")
    def build(request: Request, format: str | None = None):
        """Which build is live. Hashes the deck files this process actually reads
        and compares them with this checkout's HEAD, so "did the pull reach the
        running service?" is answerable without shell access.

        Content-negotiated: a browser gets a readable page, curl/fetch get JSON.
        Apple browsers *download* a JSON body rather than displaying it (the same
        reason the mode-hint route serves HTML), which made a JSON-only endpoint
        useless on the very phone it was meant to help."""
        from .buildinfo import build_info
        from .buildpage import render as render_build
        info = build_info(shells, extra={
            "vox-kit.css": STATIC / "vox-kit.css",
            "vox-record.js": STATIC / "vox-record.js",
        })
        if format == "json" or "text/html" not in request.headers.get("accept", ""):
            return JSONResponse(info)
        return HTMLResponse(render_build(info), headers={"Cache-Control": "no-store"})

    @app.get("/favicon.ico")
    def favicon():
        return Response(status_code=204)  # no icon; keeps the console clean

    @app.get("/static/{name}")
    def static_file(name: str):
        path = STATIC / name
        if not path.is_file() or path.parent != STATIC:
            raise HTTPException(404)
        return FileResponse(path, media_type=_MEDIA.get(path.suffix[1:], "text/plain"))

    _harvest_api(app, analyze_app)
    _harvest_api(app, polish_app)
    _harvest_api(app, fused_app)
    return app


def serve(base_dir="./_vox", host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run the unified server. Defaults to 0.0.0.0 so it's reachable over the
    Tailscale interface for multi-device testing."""
    import uvicorn

    uvicorn.run(create_unified_app(base_dir), host=host, port=port, log_level="warning")


def main(argv=None) -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="vox", description="Run the unified VOX Suite server (Analyze + Polish + Fused, one port).")
    ap.add_argument("--host", default="0.0.0.0", help="bind address (default 0.0.0.0 for tailnet access)")
    ap.add_argument("--port", type=int, default=8080, help="port (default 8080)")
    ap.add_argument("--base", default=os.environ.get("VOX_BASE", "./_vox"), help="work dir for job state")
    args = ap.parse_args(argv)
    serve(args.base, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
