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

### Scale guides

Pick a **key** (tonic) and a **scale** in the header and TimberTones highlights
the notes that belong to it — so you can practise matching pitches *within a
key*:

- out-of-scale keys dim on the keyboard; the tonic gets a marker (a dot on white
  keys, an accent ring on black keys);
- the grid tints the in-scale lanes and brightens their labels, with the tonic
  lane picked out, so you can see the key's shape while you sing.

It's a guide, not a cage — every key still plays, so you can wander outside the
scale. Set the scale to **Chromatic** to turn the highlighting off. Included:
Major, Natural/Harmonic minor, Dorian, Mixolydian, Major/Minor pentatonic, Blues.

## Running it

The microphone needs a **secure context** — `https://` or `localhost`. From this
folder:

```bash
python3 -m http.server 8000
# open http://localhost:8000/
```

Headphones are recommended so the piano doesn't leak into the mic and confuse
the pitch detector.

### In the VOX Suite

The unified server also serves it at **`/timbertones`** (alongside the pitch
monitor at `/monitor`), so it rides the suite's HTTPS origin — the secure
context the mic needs on phones — with no separate deploy. The route serves this
folder's `index.html` and its `samples/` tree directly; override the location
with the `VOX_TIMBERTONES_ROOT` env var.

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
index.html          the whole app — inline CSS + JS, no build step, no deps
samples/            <midi>.mp3 — the pitch centres, plus manifest.json
samples/manifest.json
```

**Styling is deliberately self-contained.** TimberTones keeps its own palette
rather than inheriting the suite design tokens — the look is a decision, not an
oversight, so `design/sync.sh` intentionally does not vendor `vox-tokens.css`
here (unlike `pitchmonitor/`).

## Samples — credit & licence

The piano is **"Upright Piano KW"** from the FreePats project — a real Kawai
upright, recorded by Gonzalo and Roberto (2017), released under **Creative
Commons CC0** (public domain). http://freepats.zenvoid.org/

Only the pitch-centre samples are shipped (every ~2–3 semitones); the app
pitch-shifts them to cover all 88 keys, so the footprint stays ~1.4 MB. The
originals are 8-second sustains; these are trimmed to 4 s with a short fade and
encoded to MP3.
