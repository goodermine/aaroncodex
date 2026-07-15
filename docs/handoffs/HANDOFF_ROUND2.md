# Handoff round 2: bleed suppression, tuner, editor knobs (for Daisy)

Covers the three features added since the last handoff (`HANDOFF_UI_TEST.md`):
instrumental-bleed suppression on separated vocals, the pitch tuner
(analysis + apply), and the editor's new knobs/zoom layout.

Scope rules: do NOT edit code, tune defaults, or implement features on this
pass. The mute-region feature remains queued — do not build it.

## 1. Update and sanity-check

```bash
cd aaroncodex && git pull    # branch: claude/voiceassist-plugin-planning-krhz0d
cd voxpolish
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e '.[ui,dev,pitch]'
python -m pytest tests/ -q
```

Expected: `106 passed` (pitch-apply tests need pyworld from the `[pitch]`
extra; if pyworld fails to install, report it — the rest still counts as
100 passed + 6 skipped). Any failure: STOP and report verbatim.

## 2. Bleed suppression A/B (the music-leak fix)

Use the song where Aaron heard music leaking through the isolated vocal:

```bash
voxpolish process song.wav --mode song -o out_default/
voxpolish process song.wav --mode song --bleed-strength 0.9 --sep-shifts 2 -o out_strong/
```

Capture for each run: total runtime, and `analysis.bleed` from
`edit_document.json` (leakage_ratio_median, quiet_attenuation_db).

Aaron listens to `vocal_cleaned.wav` from both runs for:
1. Is the music leak gone or acceptably buried?
2. Does the VOCAL now sound swirly/underwater anywhere? (That means the
   suppressor is too aggressive — report where, with timestamps.)
3. `removed.wav` should now contain the leaked music — and still no
   sustained lead vocal.

## 3. Tuner on a real clean vocal

Use a studio take or clean stem (not a separated vocal for this first test):

```bash
voxpolish pitch take.wav --strength 0.4                  # analysis report only
voxpolish pitch take.wav --strength 0.4 --apply          # writes take_tuned.wav
```

Capture: detected key + confidence, mean deviation, the "most off-pitch
notes" list. Aaron checks two things by ear:
1. Does the detected key match what he sang in?
2. A/B `take_tuned.wav` vs the original — is the correction audible as
   *tuning* (good) or as vocoder artifacts: hollowness, breathiness changing
   character (bad — report where)?

## 4. Editor round 2

```bash
voxpolish ui take.wav
```

Hard-refresh the browser (Ctrl+Shift+R) if a session was open before.
Aaron's click-around:
1. Module toggles: switch Gate off, Render, confirm pauses come back;
   switch on, Render, confirm they're gated again.
2. Sliders: set Breath to ~50%, Render, confirm breaths are half-tamed
   rather than gone.
3. Zoom: Fit, then Ctrl+scroll into a single phrase; scroll to pan; play and
   confirm the view follows the playhead.
4. Is the layout now readable on his monitor? Anything still oversized?

## 5. Report back

1. Test-suite result; runtimes for both song runs and the tuner.
2. `analysis.bleed` numbers from both runs; Aaron's bleed verdict (leak gone?
   vocal artifacts? removed.wav contents).
3. Tuner: key/confidence, deviation stats, Aaron's tuned-vs-original verdict.
4. Editor: results of the four checks, plus which missing control Aaron
   reached for first (gate-depth slider? region boundary dragging? pitch
   lane?) — that decides the next build.
5. Any traceback or browser-console error, verbatim.
