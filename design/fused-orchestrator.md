# VOX Suite — Fused orchestrator (design)

Status: draft · Visual System v0.1 · pairs with `telemetry-contract.md`

The **Fused** run is the suite's capstone: **upload once**, and one job carries the
take through *both* engines — isolate → analyze → polish → export — surfacing a
single command deck with one signal chain, one telemetry stream, and one export
tray that holds *both* the analysis report and the polished vocal.

## Why an orchestrator

VoxAnalysis (measure/score) and VoxPolish (repair/tune) are separate engines with
separate pipelines. Today a user runs them independently and uploads twice. Fused
removes the seam: a thin **orchestrator** accepts one upload and drives a single
job across both, so the user never re-uploads and never reconciles two UIs.

## Fused chain (8 stages)

Matches `telemetry-contract.md` → `CHAINS.fused`:

| # | key | stage | engine |
|---|-----|-------|--------|
| 1 | `upload`  | receive + validate the take            | orchestrator |
| 2 | `isolate` | separate vocal from backing (**once**) | shared isolation |
| 3 | `analyze` | pitch track + measure                  | VoxAnalysis |
| 4 | `score`   | calibrated scorecard + report          | VoxAnalysis |
| 5 | `clean`   | denoise · gate · breath · sibilance    | VoxPolish |
| 6 | `tune`    | pitch-correct to the analyzed target   | VoxPolish |
| 7 | `render`  | bounce the polished vocal              | VoxPolish |
| 8 | `export`  | assemble deliverables                  | orchestrator |

**Isolate once.** The whole point of Fused is a single separation whose vocal
stem feeds *both* analyze and polish — no double-separation, and both engines see
the exact same isolated signal. (If an engine can't accept a pre-isolated stem,
the orchestrator falls back to letting it separate internally and logs that the
optimization was skipped — never silently.)

**Analyze informs tune.** Stage 4's measured pitch target is handed to stage 6 so
the polish tuner corrects toward what analysis actually found, not a blind guess.

## Fused job status (orchestrator → deck)

The orchestrator exposes a job the Fused deck polls. Its status normalizes to the
shared telemetry event via `VOX.adaptFused`:

```json
{
  "id": "fused_<uuid>",
  "status": "queued | processing | complete | failed",
  "stage": "upload | isolate | analyze | score | clean | tune | render | export",
  "progress": 0-100,
  "analysis": { "report_url": "...", "score": {...}, "contour": {...} },
  "polish":   { "download_url": "...", "document": {...} },
  "error": { "code": "...", "message": "..." }
}
```

`adaptFused(raw)` maps `status`+`stage` to `{state, stage:{index,total}, progress}`
exactly as `adaptViewer`/`adaptPolish` do for their engines. `complete` reveals an
export tray with **both** the report (from `analysis.report_url`) and the polished
vocal (from `polish.download_url`), plus the editable edit-document.

## Implementation options (decide against the engine map)

- **A — in-process**: one orchestrator imports both engines' pipeline functions,
  runs isolate once, hands the stem to each. Cleanest data handoff; requires both
  packages importable together with compatible deps. Testable headless like the
  Polish deck.
- **B — HTTP fan-out**: orchestrator POSTs the take to each engine's existing API
  and aggregates. Fully decoupled, no dependency surgery, but each engine
  separates its own copy (isolate-once not honored) unless a stem-input param is
  added. Heavier to verify (two servers + orchestrator).

Chosen approach + the exact per-stage engine calls are filled in once the engine
entry-point map lands. The deck UI and this status contract are stable either way.

## Deck surface

The Fused deck reuses the shared kit exactly like the Analyze/Polish decks: command
bar, the 8-step fused chain, telemetry rail, processing bar, export tray. Its left
rail shows **both** an analysis readout *and* the polish module summary — the two
engines, one face. Reached from either deck's **Fused run** button (today a stub).
