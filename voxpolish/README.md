# VoxPolish (working name)

AI vocal cleanup: drop in a **song** or a **talk/podcast recording**, get back a
repaired vocal. Phase 0 command-line proof of concept — see
[`docs/vox-cleanup-plan.md`](../docs/vox-cleanup-plan.md) for the full plan.

```
Full song ──► Separate vocals ──► Analyze ──► Apply fixes ──► cleaned vocal,
              (MIT RoFormer)       (6 modules)  (render)       remix, delta,
                                                               edit_document.json
```

**No black box**: analysis writes every decision (gain curve, pauses, breaths,
sibilants) into `edit_document.json`. Edit it, re-render, and your edits are
applied exactly — rendering is deterministic DSP.

## Install (Geekom A9 Max — AMD Ryzen, 128 GB RAM)

```bash
cd voxpolish
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .                        # core: runs voice mode with DSP fallbacks

# IMPORTANT on this CPU-only AMD machine: install the CPU torch wheel FIRST,
# otherwise the extras below drag in ~2 GB of unusable CUDA/NVIDIA packages.
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

pip install -e '.[separation]'          # + MIT RoFormer for song mode
pip install -e '.[clean]'               # + DeepFilterNet denoising
pip install -e '.[vad]'                 # + Silero AI voice detection (better gating)
```

Also install ffmpeg for mp3/m4a decoding: `winget install ffmpeg` (Windows) or
`sudo apt install ffmpeg` (Linux).

Models run on the Ryzen CPU via PyTorch — with 128 GB of RAM everything fits in
memory; expect a few minutes per song for separation and seconds for the rest.
(The integrated Radeon iGPU isn't supported by ROCm, so there's no GPU path yet;
ONNX Runtime + DirectML is the future option on Windows.)

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

Outputs:

- `vocal_cleaned.wav` — the result.
- `removed.wav` — **targeted removal only** (denoise, gate, breath, sibilance),
  computed against a unity-gain baseline. Audible vocal or musical content in
  this file is a bug — this is the diagnostic to listen to.
- `full_difference.wav` — raw minus final, *including* intentional leveling
  gain. Whenever Dynamics is active this necessarily contains a gain-scaled
  copy of the vocal; that is expected, not a defect.
- `edit_document.json` — every decision, editable. Dynamics info lives at
  `analysis.dynamics`; event counts at `analysis.counts`; protected speech at
  `speech_guards` (render never lets a pause or breath dip touch these).
- Song mode also writes `instrumental.wav` + `remix.wav`.

Useful flags: `--no-gate --no-dynamics --no-breath --no-sibilance --no-clean`,
`--target-db -18`, `--gate-floor-db -30`, `--smoothing 0.5`.

## The editor UI (Phase 1)

```bash
pip install -e '.[ui]'
voxpolish ui                    # opens the browser on the upload screen
voxpolish ui recording.wav      # analyzes into recording_session/, opens browser
voxpolish ui recording_session  # reopen an existing session
```

Start from the browser: the **upload screen** accepts a WAV/MP3/M4A/FLAC vocal
recording or clean stem (drag-and-drop or pick a file), then offers one plain
choice before processing:

- **Clean + Auto Tune** (default) — cleanup plus subtle pitch correction.
- **Clean vocal** — cleanup only, no pitch correction.

Best results come from clean vocals or clean stems; noisy or full-mix sources
may keep some artefacts. **New upload** in the header starts another at any
time; the CLI file/session workflow above still works unchanged.

The editor: waveform with the module rail, region overlays (gate red, breath
green, sibilance blue), the dynamics gain curve, the **Tune** module (shows the
detected key; toggle it and re-render), A/B playback of original vs cleaned,
click-to-select and Delete-to-remove regions, Render to apply, and **Download**
to save the current rendered track as a WAV. Navigate with **Fit / + / −**,
drag or scroll the waveform to pan, Ctrl+scroll to zoom at the pointer, and the
scrollbar under the waveform; the view follows playback unless you're panning.

Below the waveform, the **pitch lane** shows the sung pitch (grey) against the
tuned result (purple) and the target notes (dashed) — so you can see exactly
what Auto Tune changed. The tuned line updates live as you move the Tune
amount slider. Auto Tune starts gentle at **10%** in new sessions; slide it up
if you want more.

Safety architecture (see `docs/vox-cleanup-plan.md`, "Phase 1 disaster plan"):
your original file is copied into the session and never written; every write
is atomic; every accepted edit snapshots the previous document into
`history/`; the on-disk Edit Document is the single source of truth (the
browser holds no private state, stale writes are rejected by revision);
waveforms come from small precomputed peak files and audio streams with range
requests, so long recordings never flood the browser; renders run in a
background worker with a single-flight lock.

## The tuner (subtle pitch correction)

```bash
voxpolish pitch vocal.wav --strength 0.4              # analyze only: report
voxpolish pitch vocal.wav --strength 0.4 --apply      # + write vocal_tuned.wav
voxpolish pitch vocal.wav --key "F# major" --apply    # force the key
voxpolish pitch vocal.wav --from-report edited.json   # apply a hand-edited report
```

Tracks the vocal's pitch (built-in YIN tracker), detects the key, segments
notes, and writes `<name>_pitch.json`: every note with its deviation in cents
and the proposed correction (strength- and retune-speed-shaped, capped at
±100 cents). With `--apply` the corrections are rendered through the WORLD
vocoder (`pip install 'voxpolish[pitch]'`).

Correction is **note-centric** (redesigned after field listening): each note
gets one near-constant shift derived from its core median deviation, so
vibrato, scoops, and micro-inflections ride through untouched. Notes within
10 cents of the scale (the deadband), unstable glides, and low-confidence
stretches get exactly zero correction.

Transparency contract: only corrected note spans are resynthesized —
everything else is the original audio **bit-identical**, crossfaded at span
edges; corrections never bridge gaps; span loudness is pinned to the input.
Edit the JSON, re-apply with `--from-report` — same no-black-box loop as
everything else. In the editor, the Tune module starts **off** (opt-in per
session). Works best on clean vocals: studio takes or clean stems.

## Bleed suppression (song mode)

Separated vocals always leak some instrumental. Because we hold the
instrumental stem, anything in the vocal stem that tracks it is bleed by
definition — so the instrumental becomes a per-band noise reference for a
bounded Wiener-style mask (leakage ratio calibrated from the vocal stem's
quiet frames, attenuation floored at 15 dB, mask smoothed, dry/wet
blendable). Runs automatically between separation and Clean; what it removes
shows up in `removed.wav`; stats land in `analysis.bleed`.

- `--bleed-strength 0.9` — push harder on a leaky mix (default 0.7, 0 = off)
The separator is deliberately pinned to the MIT KimberleyJSN Mel-Band RoFormer
checkpoint. It is not selectable from the CLI: this prevents accidental use of
non-commercial model weights in a shipped workflow.

## Balance & mastering (song mode)

The remix goes through measured balancing and bounded mastering:

1. **Balance** — vocal-active loudness (BS.1770) of raw vocal, cleaned vocal,
   and instrumental is measured over the speech-guard intervals (intros and
   gaps excluded). The correction restores the recording's *own* original
   vocal-to-backing ratio — never a fixed offset, never forced-equal LUFS.
   Bounds: vocal ±3 dB, instrumental ±2 dB; anything beyond is reported as a
   residual, not forced. `--remix-vocal-db` overrides measurement manually.
2. **Mastering** — bounded normalization toward **−15 LUFS** integrated
   (`--target-lufs`), then a **−3 dBTP** true-peak ceiling (`--true-peak-db`)
   via a lookahead limiter capped at 3 dB gain reduction; overshoot beyond
   the cap comes out of makeup gain (a reported loudness miss, not a crush).

Every measurement, applied gain, bound hit, and miss is serialized in
`edit_document.json` under `analysis.balance` and `analysis.master`
(final LUFS, LRA, true peak, target_reached, reasons).

Leveling safety (the "Shimmer" fixes): the Dynamics module is
loudness-neutral — its gain curve is corrected against a BS.1770-gated
loudness so cleaned active vocal LUFS tracks raw within ~1 LU — and locally
bounded: a hard **+6 dB boost ceiling** re-applied after the neutrality
correction, a **6 dB/s automation slope limit** so gain can never step
audibly, and leveling restricted to frames within 15 dB of the performance
level so separation bleed and washed passages are never amplified as vocal.
Protection guards use a more sensitive threshold than detection, so quiet
washed lyrics cannot be gated as pauses; breath edits only override guards at
high detector confidence; sibilance cuts scale with evidence (no forced
minimum). Reports include `gain_range_db`, `max_slope_db_per_s`, and
`neutrality_residual_lu`.

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
