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

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
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

    @app.get("/monitor", response_class=HTMLResponse)
    def pitch_monitor() -> HTMLResponse:
        """Standalone real-time pitch monitor. Self-contained (no /static deps),
        so riding the suite's HTTPS origin gives it the secure context the mic
        (getUserMedia) needs on phones."""
        path = _pitchmonitor_root() / "index.html"
        if not path.is_file():
            raise HTTPException(404, "pitch monitor not installed")
        return HTMLResponse(path.read_text(encoding="utf-8"), headers={"Cache-Control": "no-cache"})

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
