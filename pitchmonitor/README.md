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
- **HOLD** to freeze the display, and a **record / stop / play** transport that
  captures the pitch trace and replays it.
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

- Record the **audio** too (MediaRecorder) and save/load takes.
- Metronome + tempo/beat lines (BPM, 4/4 · 3/4).
- Transpose for Bb / Eb / F instruments.
- Full key picker (tonic + mode) rather than a fixed scale list.
- PWA manifest + service worker so it installs to the home screen.
