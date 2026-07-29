# VOX Suite — shared design layer

The single source of truth for the visual system that unifies **VoxPolish**
(`voxpolish/`) and **VoxAnalysis** (`voxanalysis/`). See the full spec (Visual
System v0.1) for the reasoning behind every decision here.

## Files

| File | What it is |
|---|---|
| `vox-tokens.css` | The palette + type + effect tokens (CSS custom properties, all `--vox-*`). |
| `vox-kit.css` | Framework-free primitives (`.vox-led`, `.vox-chain`, `.vox-meter`, `.vox-btn`, …) **plus the full command-deck shell layer** (`.vox-command`, `.vox-modeswitch`, `.vox-deck`, `.vox-rail`, `.vox-module`, `.vox-readout`, `.vox-scope`, `.vox-transport`, `.vox-tray`, `.vox-teleblock`, `.vox-procbar`). Depends on the tokens. |
| `sync.sh` | Vendors the two CSS files into each app's static directory. |
| `telemetry-contract.md` | The one event shape both back-ends emit (state, chain stage, progress, levels, log) so the shell's LED / chain / procbar / meters bind to real job stages. |
| `vox-suite-spec.html` · `vox-suite-concept.html` | Reference only: the written Visual System v0.1 and the animated command-deck concept. Open in a browser; not production code. |

## Palette law (v2 "clean & precise")

- **One accent** (`--vox-accent`, deep calm blue) — primary actions, active and
  focus state. Nothing else is decorated.
- **Good / watch / weak** (`--vox-good/watch/weak` + tints) are **semantic
  only** — judgement colours. Never accents or decoration.
- **Magma ramp** (`--vox-spec-0..8` + `--vox-spec-trace`) is **chart data**:
  spectrograms only — the one deliberate dark instrument in the light UI,
  because coaches and professionals read spectrograms in those colours.
- **Categorical** tokens (`--vox-cat-*`) are for information encoding
  (waveform regions, chart series) and are kept separate from chrome.
- The suite is deliberately **single-theme and light**: white surfaces,
  hairline structure, figures in tabular numerals. There is no dark mode and
  no toggle. Canvases read tokens at draw time via `getComputedStyle` (the
  canvas palette bridge) — no colour may be defined outside `vox-tokens.css`
  (enforced by `tools/ui_guard.sh`, with WCAG AA checked by
  `tools/check_contrast.py`).
- The dark-era names (`--vox-cyan`, `--vox-violet`, surfaces, grads, glows)
  survive only as deprecated aliases at the bottom of the tokens file.

## How it's shared

These two apps are served independently (each has its own static root and no
shared bundler), so the canonical files live here in `/design` and are
**vendored** into each app by `sync.sh`. Edit the files here, then run:

```bash
./design/sync.sh
```

This copies `vox-tokens.css` and `vox-kit.css` into:

- `voxpolish/src/voxpolish/server/static/`
- `voxanalysis/vox-analysis/viewer/static/`  *(pending viewer adoption)*

Each app loads them **before** its own stylesheet, so app CSS can consume the
`--vox-*` tokens and override where a screen needs to.

## Adoption status

- **VoxPolish** — tokens + kit wired in; palette adopted, yellow retired. ✅ (first increment)
- **VoxAnalysis viewer** — next: replace its inline `:root` blocks with the shared tokens and map its components onto the kit.
- **Live telemetry components** (state LED, signal chain, meters bound to real job stages) — kit ships the primitives; wiring them to each engine's stage/progress events is the following increment.
