# UI redesign — audit + execution method

Direction locked with Aaron (29 Jul 2026): **professional light-only UI**
("clean & precise": white surfaces, one restrained accent, data-forward),
**two tailored layouts** (desktop workstation + mobile capture-first), dark
mode removed entirely. Target: world-class.

This is the audit of what exists, what the redesign actually touches, and the
quality gates that make "world-class" checkable instead of a vibe.

---

## A. What exists (audited 29 Jul)

### Surfaces — 6 pages across 4 apps + a standalone monitor

| Surface | Role | State |
|---|---|---|
| `voxsuite/.../static/deck.html` | Unified shell (Analyze/Polish/Fused) | On kit; 23 lines inline CSS |
| `voxanalysis/.../static/deck.html` | Analyze deck | On kit; 109 lines inline CSS |
| `voxanalysis/.../static/index.html` | **Legacy** viewer page — still routed (`app.py:371`) | **161 hard-coded colours**, off-kit |
| `voxpolish/.../static/deck.html` + `index.html` | Polish app (4th app — in `sync.sh` targets) | On kit; small inline CSS |
| `pitchmonitor/index.html` | Real-time monitor | **Entirely off-kit**: own mini-palette (`--bg:#000`), 86 lines inline CSS, canvas colours hard-coded in JS |
| `design/vox-suite-{concept,spec}.html` | Design docs | Archive of the old look |

### The kit (canonical `design/`, vendored by `sync.sh`)

- 919 lines: `vox-tokens.css` (163), `vox-kit.css` (435), `vox-record.css`,
  `vox-report.css`, `vox-theme.js`, plus record/report/telemetry/about JS.
- **Zero vendor drift** across all three targets (voxpolish, viewer, voxsuite) —
  the sync mechanism is sound and stays.
- ~45 components in `vox-kit.css` (buttons, cards, meters, gauges, transport,
  command bar, readout grid…). Real component vocabulary exists; it's the
  *skin* that is dark-native, not the structure.

### Findings that shape the plan

1. **Dark is the base, not a mode.** `:root` in `vox-tokens.css` IS the dark
   palette (`--vox-void:#070a0e`, neon cyan/violet, glow/gradient tokens);
   light is an override applied by `vox-theme.js` + anti-flash snippets in
   every `<head>` + dark `theme-color` metas + `site.webmanifest` colours.
   Removing dark mode = **rebasing the tokens**, then deleting the toggle
   layer, snippets, and metas.
2. **Colour leaks outside the tokens.** Hundreds of hex values live outside
   `vox-tokens.css`: legacy viewer index (161), pitchmonitor (36), decks
   (15–33 each), `buildpage.py` (15 — the server emits styled HTML with its
   own colours), and even the kit CSS itself (14 in `vox-kit.css`). A palette
   swap alone would leave dark shards everywhere.
3. **Canvas is invisible to CSS.** Waveform/scope drawing hard-codes colours
   in JS (`vox-record.js`: `#3fe0ff`; pitchmonitor: spectrogram LUT, grid,
   labels). The new kit needs a **canvas palette bridge** — JS reads tokens
   via `getComputedStyle` at draw-init — so canvases obey the same palette.
4. **Responsive is ad hoc.** 8 scattered breakpoints (980/760/720/680/640/
   560/520). No layout system. The two tailored layouts need defined
   breakpoints and layout primitives, not more clamps.
5. **A11y skeleton is decent, unverified for light.** 17 `:focus-visible`
   rules, ARIA in the kit JS, `prefers-reduced-motion` handled. But every
   contrast pair was tuned for dark and must be re-validated for light;
   tabular numerals are used exactly once (should be every figure); touch
   sizing is not systematic.
6. **World-class gaps:** no print stylesheet for the report (a results page
   someone might hand to a vocal coach should print clean), no
   `safe-area-inset` handling on the capture screen (phone notch), manifest/
   PWA colours dark, legacy index page still routed.

---

## B. How we'll do it

### Phase 0 — Lock the look (no app code)
Build the two hero screens as static mockups **on top of a draft of the new
`vox-tokens.css`** — the mockup doubles as the first draft of the kit, not
throwaway art:
- **Desktop results/report** (the money screen), **mobile capture** (the
  centerpiece of the tailored-mobile bet).
- Accent: deep calm blue. Score bands stay semantic but muted + AA-valid.
- Deliverables: type scale, spacing scale, palette — all as tokens.
Iterate with Aaron on screenshots until signed off. Nothing else starts.

### Phase 1 — Rebuild the kit, light-only
- `vox-tokens.css` rewritten as the single light palette + type/spacing
  scales. Glow/gradient tokens retired.
- `vox-kit.css` / `vox-record.css` / `vox-report.css` rebuilt on it.
- `vox-theme.js` deleted (from repo and `sync.sh` list); anti-flash snippets
  and toggle references stripped from every head.
- Canvas palette bridge added; `vox-record.js` reads tokens.
- **Quality gates land here as scripts** (see C) so every later phase is held
  to them automatically.

### Phase 2 — Desktop workstation
voxsuite deck + Analyze deck + voxpolish deck on the new kit; inline CSS in
decks reduced to layout-only or folded into the kit. `buildpage.py` consumes
kit classes instead of emitting its own colours. **Legacy viewer
`index.html`: retire** — route to the deck (it's the biggest off-palette
mass and its job is done by deck.html).

### Phase 3 — Mobile capture-first shell
Its own layout (not squished desktop): record + live level/pitch dominant,
latest result next, history after. `safe-area-inset`, ≥44px targets,
thumb-reachable controls.

### Phase 4 — Pitch monitor on the kit
Kill its private palette; rebuild on tokens + canvas bridge. It keeps its
full-screen instrument character — light, not neon.

### Phase 5 — Sweep and verify
Manifest/theme-color/icons re-done for light; print stylesheet for the
report; screenshots at phone/laptop/wide via headless Chromium for review;
design docs + READMEs updated; both pytest suites green; `sync.sh` run and
drift-checked.

### Sequencing note
Take-context UI (upload selector — part 3 of that feature) should land
**after** Phase 1 so it's built once, on the new kit.

---

## C. Definition of world-class (checkable, not a vibe)

Enforced by scripts where possible (added in Phase 1, e.g.
`tools/ui_guard.sh` + a token-contrast checker):

1. **One source of colour truth** — zero hex outside `vox-tokens.css`
   (scripted grep gate across CSS/JS/HTML/`buildpage.py`).
2. **WCAG AA contrast** for every token pair in use (scripted check).
3. **No dark remnants** — no `data-theme`, `prefers-color-scheme`, theme
   toggle, or dark metas anywhere (scripted grep gate).
4. **Keyboard** — every interactive element reachable, visible focus.
5. **Touch** — ≥44px targets on mobile layouts.
6. **Motion** — `prefers-reduced-motion` respected everywhere.
7. **Numbers** — tabular numerals on every figure; scores/cents/dB align.
8. **Layout integrity** — no horizontal scroll 320px→4K; notch-safe.
9. **Print** — the report page prints clean (headline + components + metrics).
10. **Zero vendor drift** — `sync.sh` remains the only path; drift check in
    the gate script.
11. **Screenshot review each phase** — rendered in Chromium, judged by eye
    with Aaron. Automated gates catch regressions; taste is approved by a
    human.

---

## Status — 29 Jul 2026

All phases landed on this branch:

- **Phase 0** — three hero mocks approved (report, capture, player), harmonics
  folded in as a magma side-spectrogram per Aaron's direction (`design/next/`).
- **Phase 1** — kit rebuilt light-only on tokens v2; dark layer deleted;
  canvas palette bridge; gates live (`tools/ui_guard.sh`,
  `tools/check_contrast.py` — 19/19 pairs AA).
- **Phase 2** — legacy dark viewer retired; `/` serves the deck.
- **Phase 3** — take-context chips in the shared recorder and both deck
  upload forms; sanitised server-side and stamped into the analysis JSON
  after scoring (never a score input).
- **Phase 4** — pitch monitor on the kit: light grid instrument, magma
  spectrogram from the token ramp, `--vox-spec-trace` green over magma.
- **Phase 5** — print styles for the report, light PWA icons, docs updated.

Remaining ideas (not scheduled): learning-curve view per song; ranked views
surfacing take-context in the deck UI; full-texture spectrogram in the deck
player (design/next mock shows the target).
