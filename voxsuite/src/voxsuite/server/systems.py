"""The one registry of VOX systems — the single source of truth for the hub.

Edit THIS list when a system is added, renamed, moved, or retired. Everything
downstream reads it:

  * the live directory at ``GET /hub`` (renders this + a route-table liveness
    check, so a moved/removed path shows up immediately),
  * the machine-readable ``GET /api/systems`` (JSON, absolute URLs),
  * the standalone page Candy hosts (``tools/build_hub.py`` bakes this in and the
    page also re-reads /api/systems live when it can reach the suite).

``path`` is always a same-origin path on the unified server. Keeping it relative
is deliberate: the suite runs behind one address (a Tailscale/ngrok origin that
changes), and a relative link can never point at a stale host.
"""

from __future__ import annotations

# group -> ordering weight (lower shows first)
GROUPS = {"STUDIO": 0, "PRACTICE": 1, "SYSTEM": 2}

SYSTEMS = [
    {
        "id": "fused", "name": "Fused", "code": "FS", "group": "STUDIO", "path": "/",
        "blurb": "Upload a take once → isolate, analyze, score, clean, tune, export. "
                 "The whole pipeline behind one drop.",
    },
    {
        "id": "analyze", "name": "Analyze", "code": "AZ", "group": "STUDIO", "path": "/analyze",
        "blurb": "Score a take against 50 professional reference vocals, with the full "
                 "component breakdown and capture-fair reading.",
    },
    {
        "id": "polish", "name": "Polish", "code": "PL", "group": "STUDIO", "path": "/polish",
        "blurb": "Clean up and gently tune a vocal take — the finishing pass.",
    },
    {
        "id": "monitor", "name": "Pitch Monitor", "code": "MON", "group": "PRACTICE", "path": "/monitor",
        "blurb": "Real-time pitch, tuner and spectrogram, plus the onset trainer — "
                 "sing and watch your intonation live.",
    },
    {
        "id": "timbertones", "name": "TimberTones", "code": "TT", "group": "PRACTICE", "path": "/timbertones",
        "blurb": "Play a note on the piano and match it with your voice. Sampled "
                 "upright + a live pitch-match trainer with scale guides.",
    },
    {
        "id": "build", "name": "Build / status", "code": "SYS", "group": "SYSTEM", "path": "/api/build",
        "blurb": "Which build is live — the deck files this server is actually running, "
                 "checked against the checkout.",
    },
]


def registered_paths(app) -> set[str]:
    """Every path the given FastAPI app actually serves — used to flag a system
    whose route has moved or been removed so the hub never lies about liveness."""
    paths: set[str] = set()
    for route in getattr(app.router, "routes", []):
        p = getattr(route, "path", None)
        if p:
            paths.add(p)
    return paths


def is_live(system: dict, paths: set[str]) -> bool:
    """A system is live if its path (or its trailing-slash form) is registered.
    ``/monitor`` and ``/timbertones`` register the redirect at the bare path and
    the page at the slash form; either presence counts."""
    p = system["path"]
    return p in paths or (p.rstrip("/") + "/") in paths or p.rstrip("/") in paths


def resolve(app=None, base_url: str = "") -> list[dict]:
    """The registry as an ordered, enriched list: each entry gains ``live`` (vs
    the app's route table, when an app is given) and ``url`` (absolute, when a
    base_url is given). Sorted by group then declared order."""
    paths = registered_paths(app) if app is not None else set()
    base = base_url.rstrip("/")
    out = []
    for i, s in enumerate(SYSTEMS):
        e = dict(s)
        e["live"] = is_live(s, paths) if app is not None else None
        e["url"] = (base + s["path"]) if base else s["path"]
        e["_order"] = (GROUPS.get(s["group"], 99), i)
        out.append(e)
    out.sort(key=lambda e: e["_order"])
    for e in out:
        del e["_order"]
    return out
