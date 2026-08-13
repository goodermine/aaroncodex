# Handoff — TimberTones

_Quick orientation for a fresh coding session picking up TimberTones._

## What it is

**TimberTones** is a standalone web app: a **sampled upright piano fused with a
live pitch-match trainer**. You press a key — it plays a real piano note **and**
drops a target lane onto a scrolling pitch grid; you sing into the mic and bring
your voice up to the line to match it. Green inside the ±35-cent band, a cents
readout, and a hold-to-match streak. It's built for ear training: hear a pitch,
reproduce it with your voice, see how close you are.

A **key + scale picker** highlights the notes in a chosen key (out-of-scale keys
dim, tonic marked, in-scale grid lanes tinted) so you can practise matching
within a key. "Chromatic" turns the highlighting off.

## Where it lives

Repo root: **`timbertones/`**

```
timbertones/
  index.html          the whole app — inline CSS + JS, no build step, no deps
  samples/            <midi>.mp3 — 38 pitch-centre samples (e.g. 60.mp3 = middle C)
  samples/manifest.json   the list of shipped MIDI centres the app fetches
  README.md           usage + credits
```

Self-contained apart from the `samples/` dir. No framework, no bundler — open
`index.html` and it runs (the mic needs a secure context: `localhost` or HTTPS).

**Styling is deliberately its own palette** — TimberTones does *not* vendor
`vox-tokens.css` (unlike `pitchmonitor/`), and `design/sync.sh` intentionally
skips it here. The look is a decision, not an oversight; the CSS is inline in
`index.html`. (See `timbertones/README.md`.)

## How it's served

Two ways, same file:

1. **Standalone**: `cd timbertones && python3 -m http.server 8000` → open
   `http://localhost:8000/`.
2. **In the VOX Suite** at **`/timbertones`** (mirrors the pitch monitor's
   `/monitor`). Routes live in
   `voxsuite/src/voxsuite/server/unified.py`:
   - `GET /timbertones` → 307 redirect to `/timbertones/`
   - `GET /timbertones/` → serves `timbertones/index.html`
   - `GET /timbertones/{sub:path}` → serves sibling assets + the `samples/` tree
     (traversal-guarded, suffix-whitelisted: css/mp3/json/png/js)
   - Root override: `VOX_TIMBERTONES_ROOT` env var.
   Covered by `voxsuite/tests/test_unified.py` (`test_timbertones_serves_standalone_with_samples`).

## How it works (implementation notes)

- **Pitch detection**: YIN (cumulative mean normalized difference), adapted from
  `pitchmonitor/index.html` `detect()` — monophonic, robust against the octave
  errors plain autocorrelation makes on low notes. Same Hz↔MIDI↔note math and the
  same scrolling-grid approach, so TimberTones and the monitor behave identically.
- **Sampler**: the piano voice plays from real recordings pitch-shifted at most
  ±1 semitone per key, through a `DynamicsCompressor` so chords don't clip. The
  mic feeds the analyser **only** (never the output) — no feedback loop.
- **Samples**: FreePats "Upright Piano KW" (a real Kawai upright), **CC0**. Only
  the pitch centres ship (~1.4 MB); the app interpolates the rest. The repo
  gitignores `*.mp3`, so there's an explicit exception
  `!timbertones/samples/*.mp3` in `.gitignore` (these are app assets, not
  vocal recordings).
- Mobile-first: one big labelled octave on a phone, ~2 octaves + computer-keyboard
  mapping (`A S D F…` white, `W E T Y U…` black) on desktop; header wraps on
  narrow screens.

## Status

Merged to `main` in **PR #37** (commit `58db7d1`). Working and tested.

## Likely next steps / extension points

- **Section/scale practice** built on the trainer (e.g. drill a scale in a key).
- **Velocity sensitivity** and a **record/playback** transport.
- **MIDI-keyboard input** (Web MIDI) as an alternative to the on-screen keys.
- **Suite nav link** — `/timbertones` is reachable by URL but not yet linked from
  the deck nav or the systems hub card row (see `voxsuite/.../systems.py`, which
  already lists it for the `/hub` directory).

## Related

- `pitchmonitor/` — the sibling real-time pitch monitor (source of the shared DSP).
- `/hub` + `voxsuite/src/voxsuite/server/systems.py` — the systems directory that
  lists TimberTones alongside the other VOX apps.
