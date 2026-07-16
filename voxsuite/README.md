# VoxSuite — Fused orchestrator

The suite layer above the two vocal engines. A **Fused** run lets a singer
**upload once** and carries that take through *both* engines in a single pass:

```
upload → isolate (once) → analyze → score → clean → tune → render → export
         └────────────── VoxAnalysis ──────┘ └──────── VoxPolish ────────┘
```

The vocal is **isolated once** and the same stem feeds both engines — no
double-separation — surfacing one command deck with one signal chain, one
telemetry stream, and one export tray holding **both** the analysis report and
the polished vocal. See `design/fused-orchestrator.md` for the design and
`design/telemetry-contract.md` for the shared event shape.

## Layout

- `src/voxsuite/orchestrator.py` — the fused job model + `run_fused` stage driver.
  Engine work sits behind the `Engines` protocol, so the orchestration is
  deterministic and unit-tested with fakes.
- `src/voxsuite/engines.py` — `RealEngines`, the adapter wiring to the installed
  pipelines (`voxpolish.stages.separation`, `pitch_track`, `voxpolish` `Session`).
  Imports are lazy/guarded so the app loads without the heavy audio deps.
- `src/voxsuite/server/app.py` — FastAPI: the Fused deck at `/deck` and the job
  API (`POST /api/fused-jobs`, `GET /api/fused-jobs/{id}`, `.../report`,
  `.../download`). The engine adapter is injectable for tests.
- `src/voxsuite/server/static/deck.html` — the Fused command deck (shared kit).

## Run

```bash
pip install -e voxsuite          # + voxpolish, and the VoxAnalysis engine deps,
                                 #   for real runs (ffmpeg + audio-separator etc.)
python -c "from voxsuite.server.app import create_app; import uvicorn; \
           uvicorn.run(create_app('./_fused'), port=8767)"
# open http://127.0.0.1:8767/deck   (append ?demo=1 for a no-backend preview)
```

Real end-to-end runs require the same audio stack the engines need (ffmpeg,
`audio-separator`/RoFormer weights, librosa, parselmouth). Where a dep is
missing, `isolate` degrades gracefully (treats the upload as an already-vocal
signal and says so) and the affected stage reports a clear error rather than
hanging.

## Test

```bash
cd voxsuite && python -m pytest -q      # orchestration + web lifecycle, fakes only
```
