# Plan: unify VOX Suite into one server (one container, one port, one address)

**Status:** proposed · **Decision inputs:** home mode = **Fused**; scope = **full merge**
(one app + one shared `/static`, not just a gateway).

## Why

Candi currently starts **two/three** servers on separate ports (Polish 8765,
Analyze 8766, Fused 8767), each behind its own Tailscale exposure. Two failures
follow directly:

1. **Two Tailscale addresses** — one per server.
2. **Mode tabs break Polish↔Analyze** — the deck tabs navigate to hardcoded
   `host:8765` / `host:8766`. Over Tailscale, if only one address is
   reachable/funneled, switching modes lands on a dead port.

Goal: **one process, one port, one Tailscale address**, with mode tabs that are
plain same-origin links and therefore never depend on a port.

## What makes this clean

- **The engines already run together in one process.** `voxsuite`'s
  `RealEngines` drives both `voxpolish` (installed package) and `voxanalysis`
  (imported by path) in a single Python process. One-container is already proven.
- **Dependencies don't conflict.** Shared numpy/scipy/soundfile/fastapi;
  Analyze adds librosa/parselmouth/matplotlib, Polish adds audio-separator/pyworld.
  One venv holds everything.
- **API routes are already disjoint.** The only overlapping paths across the
  three apps are `/`, `/deck`, `/static/{name}`. Every API lives on a distinct
  prefix already:
  - Analyze: `/api/pitch-jobs/…`, `/api/health`
  - Polish:  `/api/workspace`, `/api/session`, `/api/uploads`, `/api/document`,
             `/api/render`, `/api/peaks`, `/api/audio`, `/api/download`
  - Fused:   `/api/fused-jobs/…`

  Because the API prefixes don't collide, all three route sets can be `include_router`'d
  onto **one app at the root origin** — which means the decks' existing absolute
  `/static/…` and `/api/…` paths keep working **unchanged**. No `<base href>`
  rewriting, no per-mount prefix juggling. Only the mode-tab navigation changes.

## Target architecture

One FastAPI app (`vox.server.app:create_app(base)`), one origin:

```
http://a9max.<tailnet>.ts.net:8080/
  GET  /                      → Fused deck (home)
  GET  /analyze               → Analyze deck
  GET  /polish                → Polish deck
  GET  /fused                 → Fused deck (same as /)
  GET  /static/{name}         → ONE shared static dir
  …/api/pitch-jobs/…          → Analyze router  (+ /api/health)
  …/api/{workspace,session,uploads,document,render,peaks,audio,download}
                              → Polish router
  …/api/fused-jobs/…          → Fused router
```

Mode tabs become `/analyze`, `/polish`, `/fused` — same origin, **no host, no port**.

### Static consolidation (kills the 3× vendoring)

Today `design/sync.sh` copies the 8 shared-kit files into **three** static dirs.
The three dirs also each carry their own `deck.html`, and Analyze+Polish each
carry `index.html`; Polish additionally has the classic editor `app.js`/`style.css`.

Merge into one `vox/server/static/`:
- Shared kit (8 files) — **one** copy (the three current copies are byte-identical).
- Per-mode deck shells renamed to avoid the `deck.html` collision:
  `deck-analyze.html`, `deck-polish.html`, `deck-fused.html`.
- Keep Polish's classic editor assets (`app.js`, `style.css`, its `index.html`)
  if we still want the legacy `/` editor reachable; otherwise retire them.
- `design/sync.sh` now targets **one** dir.

## Work breakdown (staged, each stage independently shippable)

### Stage 1 — Unified serving (fixes Candi's pain)
- New `vox/server/app.py` with `create_app(base)` that:
  - Serves the three deck shells at `/` (Fused), `/analyze`, `/polish`, `/fused`.
  - `include_router`s the three API routers.
  - Serves one `/static/{name}`.
- **Refactor Analyze into an includable router.** Today `viewer/app.py` is a
  module-level `app` with import-time side effects (`_production_guard()`,
  `_cleanup(recover_interrupted=True)` at import) and module globals
  (`RUNTIME`, `executor`, `manifest_lock`) plus a `sys.path` hack for
  `report_builder`. Wrap these in a factory (`build_analyze_router(runtime)`),
  moving the guard/cleanup into app startup. Its subprocess engine call
  (`engine/pitch_track.py`) stays exactly as-is — no engine behavior change.
- Polish and Fused are already `create_app()` factories → convert their route
  bodies into `APIRouter`s (mechanical; state stays per-router closures).
- Change the three decks' mode tabs to same-origin links (`/analyze` etc.);
  delete the hardcoded `:8765`/`:8766`/`:8767` navigation.
- **Fixes both problems.** One port, one address, working tabs.

### Stage 2 — Single static tree
- Move shared kit + renamed deck shells into `vox/server/static/`.
- Point `design/sync.sh` at the one dir; delete the redundant vendored copies.
- Update each deck shell's asset refs only where filenames changed.

### Stage 3 — Packaging & launch
- One console script: `vox serve --host 0.0.0.0 --port 8080`.
- One install extra that pulls both engines' deps:
  `pip install -e '.[all]'` (voxpolish[ui,pitch,separation] + voxanalysis engine/viewer reqs).
- Decide voxanalysis packaging: add a minimal `pyproject.toml` so it imports as a
  package (cleaner than the `sys.path` injection), **or** keep path-import via
  `VOX_ANALYSIS_ROOT`. Recommend making it a package.
- Optional (the literal "container"): a `Dockerfile` + `docker run -p 8080:8080`
  so Candi runs `docker run` instead of a venv. Nice-to-have, not required for
  one-address.

### Stage 4 — Tests & docs
- Fold the three test suites; keep each mode's API tests, add route tests that
  assert `/`, `/analyze`, `/polish`, `/fused` all serve their deck and that the
  tabs are same-origin (no `:876x` in any shell).
- Headless: verify mode-switching across one origin with no console errors.
- Rewrite `docs/handoffs/tailscale-multi-device-test.md`: one venv, one command,
  one URL.

## Decisions taken (defaults, override anytime)

- **Home = Fused** (`/` serves the Fused deck).
- **Keep all three modes** (Analyze / Polish / Fused) — Fused already fuses both,
  so it's free to keep.
- **Analyze keeps its subprocess engine** — no engine rewrite, lowest risk.
- **Job storage stays per-mode** (Analyze on-disk runtime, Polish workspace,
  Fused in-memory) — independent subsystems; unifying storage is out of scope.

## Risks / watch-items

- Analyze's import-time `_production_guard()`/`_cleanup()` must move to startup so
  importing the router doesn't fire them prematurely (esp. under pytest).
- `RUNTIME`/`executor` globals → per-app instances to avoid cross-test leakage.
- Static filename collisions (`deck.html` ×3, `index.html` ×2) resolved by the
  per-mode rename in Stage 2.
- The shared-kit copies are byte-identical today; de-duping assumes that stays
  true (enforced by the single `sync.sh` target going forward).

## Rollout

Stage 1 alone solves the reported problem and is safe to ship first. Stages 2–4
are cleanup/packaging that can follow without further user-visible change. Old
per-app entrypoints (`voxpolish serve`, `uvicorn app:app`) can remain during the
transition and be retired once the unified `vox serve` is validated over Tailscale.
