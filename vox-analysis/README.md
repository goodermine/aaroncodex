# VOX Analysis — the metrics part

Everything that **measures and scores** a vocal take. Two pieces that work
together and never reach the internet:

```text
vox-analysis/
├── engine/     the measurement core (analyse_song.py + calibration + knowledge + tools)
└── viewer/     the local web app that renders a take (http://127.0.0.1:8766)
```

The viewer calls the engine by relative path (`../engine/`), so the two must
stay side by side under `vox-analysis/`.

## `engine/` — the measurement core

`analyse_song.py` is the single source of truth for every acoustic number:

- **Praat-grade acoustics** (via `praat-parselmouth`): jitter, shimmer, HNR,
  CPPS, formants — measured per sustained note, aggregated by median.
- **Deterministic scoring rubric**: six components (intonation, pitch
  stability, voice quality, vibrato, dynamics, phrase control), each anchored
  to the professional reference pack. "10" = the pro-pack median; scores are
  reported as percentiles you can verify by hand.
- **Capture-fair comparison**: voice-quality is excluded when comparing across
  recording eras/conditions so old records aren't unfairly penalised.
- **Diagnostic blocks** (never alter the score): trouble spots, strain,
  registers, breath, groove, range map, onset quality, harmonics, singer's
  formant, vowel space.
- **Deterministic prescriptions**: exercises are looked up from the knowledge
  library by a hash-pinned map — never invented.

Every value is measured or from a documented formula. No number is produced by
a language model. Full audit trail: `../docs/metrics-methodology.md`.

Key sub-folders:

| Path | Contents |
|---|---|
| `engine/calibration/` | `pro_reference.json` (the 50-track anchor) + the per-track reference analyses |
| `engine/knowledge/` | `prescription_map.json` (hash-pinned to the exercise library) |
| `engine/tools/` | `build_calibration.py`, `build_prescription_map.py`, `compare_takes.py`, `progress_report.py` |
| `engine/output/` | scratch analysis JSONs (git-ignored) |

### Setup & run

```bash
cd vox-analysis/engine
chmod +x install.sh && ./install.sh        # or python3 -m venv voxai_env && pip install -r requirements.txt
sudo apt install ffmpeg
python analyse_song.py "/path/to/take.mp3" --name "Aaron - Vienna" --separate-stems
```

## `viewer/` — the local web app

Upload a take, watch its confidently-detected pitch line against synchronised
playback, toggle the harmonic scope, and read the calibrated report. Low-
confidence pitch is drawn as a dotted line; breaths and silence stay blank —
nothing is ever invented.

```bash
cd vox-analysis/viewer
pip install -r requirements.txt
python app.py        # open http://127.0.0.1:8766
```

Tests (viewer ↔ engine bridge, honesty constraints, spectral ground truth):

```bash
cd vox-analysis/viewer
python -m unittest discover -s tests
```
