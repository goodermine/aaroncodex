# TimberTones

A sampled upright piano fused with a live **pitch-match trainer**. Press a key —
it plays the note *and* drops a target lane onto a scrolling pitch grid. Sing
into the mic and bring your voice up to the line to match it.

Built for ear-training: hear a pitch, then reproduce it with your voice and see
exactly how close you are.

## How it works

1. **Press a key** (tap, click, drag, or your computer keyboard). You hear the
   note and it becomes the **target** — a dashed lane on the grid with a
   ±35-cent "clean" band.
2. **Sing it.** Your live pitch scrolls across the grid as a contour: green
   inside the band, amber close, grey off. The readout shows the exact cents you
   are sharp/flat.
3. **Hold it** inside the band for ~0.45 s and it counts as a match — a chime
   fires and your streak ticks up.

- **Hold target** keeps the same note until you nail it; **Auto-clear** lets each
  new key press move the target on.
- **Octave shift**: the ◀ ▶ buttons or `Z` / `X`.
- **Computer keyboard**: `A S D F G H J …` for white keys, `W E T Y U …` for
  black keys (shown on desktop).

## Running it

The microphone needs a **secure context** — `https://` or `localhost`. From this
folder:

```bash
python3 -m http.server 8000
# open http://localhost:8000/
```

Headphones are recommended so the piano doesn't leak into the mic and confuse
the pitch detector.

## What's inside

Fully self-contained — one `index.html` with inline CSS/JS, no build step, no
dependencies. It reuses the sibling pitch monitor's proven parts so both apps
behave identically:

- **Pitch detection**: YIN (cumulative mean normalized difference), the same
  algorithm as `pitchmonitor/index.html` — monophonic, robust against the
  octave errors plain autocorrelation makes on low notes.
- **Note math**: identical Hz ↔ MIDI ↔ note-name helpers (A4 = 440).
- **Sampler**: the piano voice is played from real recordings, pitch-shifted at
  most ±1 semitone per key, through a compressor so chords don't clip. The mic
  feeds the analyser only (never the output), so there is no feedback loop.

```
index.html          the whole app
samples/            <midi>.mp3 — the pitch centres, plus manifest.json
samples/manifest.json
vox-tokens.css      vendored design tokens (shared suite palette)
```

## Samples — credit & licence

The piano is **"Upright Piano KW"** from the FreePats project — a real Kawai
upright, recorded by Gonzalo and Roberto (2017), released under **Creative
Commons CC0** (public domain). http://freepats.zenvoid.org/

Only the pitch-centre samples are shipped (every ~2–3 semitones); the app
pitch-shifts them to cover all 88 keys, so the footprint stays ~1.4 MB. The
originals are 8-second sustains; these are trimmed to 4 s with a short fade and
encoded to MP3.
