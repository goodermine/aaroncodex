# VOX Suite — telemetry event contract (v0.1)

One event shape both back-ends emit, so the shared shell's **state LED, signal
chain, processing bar, meters and log are driven by real job stages** — never
faked (Visual System v0.1 §04, §07). Define it once here; VoxPolish and
VoxAnalysis each map their native job state onto it, and one small front-end
telemetry client renders it.

This is a **read model**: the shell polls (or, later, subscribes to) a single
status endpoint per app that returns the object below. It is deliberately a
superset — every field except `state`, `mode`, `stage` and `progress` is
optional, so an engine emits only what it actually measures.

## The event

```jsonc
{
  "mode": "polish",            // "polish" | "analyze" | "fused"
  "state": "WORKING",          // see State ↔ LED below
  "job":   { "id": "…", "name": "take_07_vienna.wav" },

  "stage": {                   // drives the signal chain + procbar label
    "index": 4,                // 0-based index of the ACTIVE step
    "total": 8,                // number of steps in this mode's chain
    "key":   "gate_breath",    // stable machine key (see Chains below)
    "label": "Gate·Breath"     // display label (mono caps in the UI)
  },
  "progress": 52,              // 0–100 overall; procbar fill + %

  // ---- all optional below ----
  "levels":  { "l": -7.0, "r": -6.0, "sum": -4.0 },   // dBFS, VU lanes
  "compute": { "gpu": 72, "cpu": 54 },                 // %, the two gauges
  "log": [                                             // newest first
    { "level": "info", "msg": "gate stage engaged" },  // info|warn|done|error
    { "level": "done", "msg": "clean complete" }
  ],
  "error": null                // { "code": "...", "message": "..." } on ALERT
}
```

### State ↔ LED (Visual System §04)

| `state`     | LED class (`vox-led …`) | Meaning                              |
|-------------|-------------------------|--------------------------------------|
| `STANDBY`   | `is-standby` (cyan pulse)| Deck armed, awaiting a take          |
| `WORKING`   | `is-working` (amber blink)| A stage is running                  |
| `COMPLETE`  | `is-done` (green settle) | Job finished; export tray reveals    |
| `ALERT`     | `is-alert` (red blink)   | Error/clip; `error` is populated     |
| `ANALYZE`*  | `is-analyze` (violet)    | Optional mode tint while idle/standby in Analyze |

\* `ANALYZE` is a cosmetic tint only; a running Analyze job still reports
`WORKING`. Work is amber, done is green — so a glance always means something.

### Chains (the signal-chain steps per mode)

`stage.index` indexes into these ordered `key`/`label` lists. Steps before the
index render `is-done`, the index renders `is-active`, the rest are upcoming.

- **polish**: `upload` · `separate` · `clean` · `gate_breath` · `sibilance` · `tune` · `render` · `export`
- **analyze**: `upload` · `isolate` · `pitch` · `analysis` · `match` · `align` · `report`
- **fused**: `upload` · `isolate` · `analyze` · `score` · `clean` · `tune` · `render` · `export`

## Per-app mapping (native → contract)

Each app already has a status source; the adapter is thin.

### VoxAnalysis viewer
`GET /api/pitch-jobs/{id}` → `{ id, status, stage, result, error }`.

| native `status` | contract `state` | notes |
|---|---|---|
| `queued`     | `STANDBY` | before the worker picks it up |
| `processing` | `WORKING` | `stage` (from `stage.json`) maps to a chain `key` |
| `complete`   | `COMPLETE`| `result` present; export tray = report + metrics |
| `failed`     | `ALERT`   | `error.code` → `error` |

The viewer already streams `stage` strings (`separating_vocals`, …) via
`stage.json`; map each to the analyze/fused chain `key`.

### VoxPolish
`GET /api/render` → `render_state = { status, error, revision, session, notes }`,
plus upload-job progress at `GET /api/uploads/{id}`.

| native `status` | contract `state` |
|---|---|
| `idle`    | `STANDBY` |
| `running` | `WORKING` (map the active pipeline step to a polish chain `key`) |
| `done`    | `COMPLETE` (export tray = vocal, remix, stem, `edit_document.json`) |
| `error`   | `ALERT` |

## Front-end client (to build in the shell increment)

A single `telemetry.js` that: polls the active app's status endpoint, normalises
to the event above, and calls small render fns — `setState(led)`,
`setChain(index,total)`, `setProgress(pct)`, `setLevels()`, `pushLog()`. The
concept (`design/vox-suite-concept.html`) already contains the exact render
functions driven by simulated data; the client swaps the simulator for this
feed. Poll interval ~500 ms while `WORKING`, back off to ~2 s at `STANDBY`/
`COMPLETE`.

## Notes

- **Bound to truth:** a step lights because that stage started; a meter moves
  because a level moved. Do not animate a stage the engine hasn't reported.
- **Levels/compute are best-effort:** CPU-only dev boxes may omit `compute`;
  the gauges simply hide. Never fabricate a GPU reading.
- **Reduced motion:** the client still updates values; the kit stops the loops.
