# VoxPolish (working name)

AI vocal cleanup: drop in a **song** or a **talk/podcast recording**, get back a
repaired vocal. Phase 0 command-line proof of concept — see
[`docs/vox-cleanup-plan.md`](../docs/vox-cleanup-plan.md) for the full plan.

```
Full song ──► Separate vocals ──► Analyze ──► Apply fixes ──► cleaned vocal,
              (Demucs, song mode)  (6 modules)  (render)       remix, delta,
                                                               edit_document.json
```

**No black box**: analysis writes every decision (gain curve, pauses, breaths,
sibilants) into `edit_document.json`. Edit it, re-render, and your edits are
applied exactly — rendering is deterministic DSP.

## Install (Apple Silicon Mac)

```bash
cd voxpolish
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                        # core: runs voice mode with DSP fallbacks
pip install -e '.[separation]'          # + Demucs for song mode (uses the M-series GPU)
pip install -e '.[clean]'               # + DeepFilterNet denoising
pip install -e '.[vad]'                 # + Silero AI voice detection (better gating)
brew install ffmpeg                     # mp3/m4a decoding
```

Everything ML is optional: without it the pipeline still runs (voice mode) using
DSP fallbacks, and upgrades itself automatically when the models are installed.

## Use

```bash
# A talk / sermon / podcast recording:
voxpolish process talk.wav --mode voice -o out/

# A full mixed song — separates the vocal first, returns stem + remix:
voxpolish process song.mp3 --mode song -o out/

# A talk with background music under it — strip the bed:
voxpolish process event.wav --mode voice --strip-music-bed -o out/

# The no-black-box loop: edit out/edit_document.json by hand, then:
voxpolish process talk.wav --from-doc out/edit_document.json -o out2/
```

Outputs: `vocal_cleaned.wav`, `delta.wav` (everything that was removed — listen
to verify nothing musical was lost), `edit_document.json`, and in song mode
also `instrumental.wav` + `remix.wav`.

Useful flags: `--no-gate --no-dynamics --no-breath --no-sibilance --no-clean`,
`--target-db -18`, `--gate-floor-db -30`, `--smoothing 0.5`.

## The six modules

| Module | Phase 0 status |
|---|---|
| Clean | DeepFilterNet denoise (optional install), dry/wet blend; dereverb later |
| Lowend | not yet — Phase 0.5 (pitch-tracked low-cut, resonance notches) |
| Gate | Silero VAD or energy fallback; edge padding so words aren't clipped |
| Dynamics | loudness riding with speed/smoothing/target/catch-peaks; editable curve |
| Breath | heuristic (level band + spectral flatness); classifier later |
| Sibilance | event-based 4.5–10 kHz detection, per-event band-limited reduction |

## Develop

```bash
pip install -e '.[dev]'
python -m pytest tests/ -q    # 13 tests, all synthetic audio, no models needed
```

Known Phase 0 rough edges: sibilance over-triggers near phrase boundaries
(tuning); breath heuristic needs validation on real recordings; song-mode
defaults (gentle gate, musical breaths) are first guesses.
