# Pitch Monitor

A real-time vocal/instrument pitch monitor — a from-scratch build inspired by
*Vocal Pitch Monitor*. Sing or play into the mic and your pitch is drawn, live,
across a scrolling musical note grid.

It's a single self-contained page (`index.html`) — no build step, no
dependencies. It reuses the VOX suite's conventions (note/cents/frequency math,
canvas note-grid rendering, the dark analyzer aesthetic) but runs entirely
client-side.

## What works now

- **Real-time pitch detection** using the **YIN** algorithm (cumulative mean
  normalized difference) — accurate to well under 1 cent across E2–C6, and
  robust against the octave errors a plain autocorrelation makes on low notes.
- **Scrolling note grid** — vertical axis is the musical scale (labelled
  octaves + semitone lines), horizontal axis is time, scrolling right→left.
- **Big note readout** with cents (or Hz) and a **tuner strip** showing cents
  deviation with a green in-tune indicator.
- **HOLD** to freeze the display, and a **record / stop / play** transport.
  Recording captures both the **audio** (MediaRecorder) and the pitch trace;
  pressing play plays the sound back with the note graph replayed in
  lock-step (driven off the audio's own playhead). Falls back to a silent
  trace replay if the browser has no MediaRecorder.
- **Scale highlighting** — tonic and in-scale notes are tinted on the grid.
- **Settings**, persisted to `localStorage`: volume threshold, horizontal &
  vertical zoom, smoothing, A4 calibration, note names (C D E / Do Re Mi),
  octave numbering, scale, semitone lines/labels, auto-scroll, Hz display,
  tuner toggle, pitch-line colour.

## Running it

`getUserMedia` needs a **secure context**, so the mic works on `https://` or
`http://localhost`. Opening the file over `file://` works in some desktop
browsers; on a phone, serve it over HTTPS.

The unified VOX server serves it at **`/monitor`**, so on the suite's Tailscale
address it's e.g. `https://<host>:<port>/monitor` — the HTTPS origin gives the
mic the secure context it needs on a phone. (Override its location with the
`VOX_PITCHMONITOR_ROOT` env var if the repo isn't at the default path.)

## Roadmap (not yet built)

- Save/load takes (the audio blob is in memory only — lost on reload).
- Metronome + tempo/beat lines (BPM, 4/4 · 3/4).
- Transpose for Bb / Eb / F instruments.
- Full key picker (tonic + mode) rather than a fixed scale list.
- PWA manifest + service worker so it installs to the home screen.

## Onset trainer (TRAIN)

Dream idea D1. Tap **TRAIN** (mic must be running): the monitor plays a target
note, goes silent for one beat — *hear it in your head, that silence is the
exercise* — then listens. The entry is verdicted from the **first 250 ms** of
raw (unsmoothed) pitch against the target:

- **CLEAN** — started within ±35 cents. Streak +1.
- **SCOOP** — slid up from below («arrive, don't reach»). Streak resets.
- **OVERSHOOT** — dropped from above («place it, don't throw it»). Streak resets.
- **—** landed on a different note or too little voice: doesn't count either way.

The target line + clean-zone band draw on the grid; the strip tracks streak and
clean-% over the last ten. Targets randomise between the range set in Settings
(default A3–F4 — the working range). Thresholds match the engine's ENTRY
ACCURACY diagnostic, so the trainer and the reports speak the same language.

Smoke check: `node tests/trainer_check.mjs` (start `python3 -m http.server 8123`
in this folder first; uses Chrome's fake-mic flags, asserts the LISTEN→HEAR
IT→SING machine runs and a verdict lands).
