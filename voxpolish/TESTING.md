# First-run test checklist (for the agent on the A9 Max)

Goal: verify the Phase 0 pipeline runs on this machine and produce a listening
report on real recordings. Follow in order; capture output of every step.

## 1. Setup

```bash
git clone https://github.com/goodermine/aaroncodex.git   # or git fetch && checkout if cloned
cd aaroncodex
git checkout claude/voiceassist-plugin-planning-krhz0d
cd voxpolish
python3 -m venv .venv && source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
```

## 2. Sanity check — the test suite must pass before anything else

```bash
python -m pytest tests/ -q
```

Expected: `13 passed`. If not, STOP and report the failure output.

## 3. Voice mode on a real recording (no ML installs needed)

Pick a real talk/podcast/sermon recording (wav or flac; for mp3/m4a install
ffmpeg first). Then:

```bash
voxpolish process /path/to/talk.wav --mode voice -o out_talk/
```

Capture: total runtime printed by the CLI, and the `counts` + `dynamics`
values from `out_talk/edit_document.json`.

## 4. Optional: better backends, then song mode

```bash
pip install -e '.[vad]'          # Silero VAD — re-run step 3, compare pause counts
pip install -e '.[clean]'        # DeepFilterNet denoising
pip install -e '.[separation]'   # Demucs (large download, ~2 GB with torch)
voxpolish process /path/to/song.mp3 --mode song -o out_song/
```

Capture: separation runtime (this is the number we care about on this CPU),
and whether `remix.wav` sounds like the original song with a cleaner vocal.

## 5. Report back

For each processed file, note:
1. Runtimes (per stage if visible, else total).
2. `edit_document.json` event counts: pauses / breaths / sibilants.
3. Listening notes on `vocal_cleaned.wav`: does the gate clip word starts/ends?
   Do the leveled sections sound natural or pumpy?
4. Listening notes on `delta.wav`: this is everything that was REMOVED —
   flag anything musical or vocal audible in it (that's a bug).
5. Any crash/traceback verbatim.

Do NOT tune parameters or edit code on this pass — raw first impressions of the
defaults are the data we need.
