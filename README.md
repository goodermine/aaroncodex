# Vox

Tools for working with the human voice, built for the Vox Coaching ecosystem.

This repository currently holds **VoxPolish**, an AI vocal cleanup and tuning
tool. It is structured so a second component — the **Vox analysis / coaching**
tooling (currently in a separate repository) — can be merged in alongside it
without collisions: each component lives in its own top-level directory.

```
.
├── voxpolish/        # AI vocal cleanup + subtle tuning (CLI + local web editor)
├── docs/
│   ├── vox-cleanup-plan.md   # product & engineering plan
│   └── handoffs/             # development handoffs / decision records
└── README.md         # you are here
```

> Planned: a `voxanalysis/` (or similar) directory for the coaching-analysis
> component when the two repositories are merged. Both share the same brand and
> can share Python utilities over time.

---

## VoxPolish

Drop in a **song** or a **vocal/talk recording** and get back a repaired vocal:
separate the vocal from the mix, clean it (denoise, de-reverb, bleed removal),
level it, tame breaths and sibilance, and optionally apply subtle pitch
correction — all editable, nothing a black box.

- **Song mode** separates the vocal from a full mix (Demucs), suppresses
  instrumental bleed, cleans, levels, and can remix over the original backing.
- **Voice mode** cleans an already-isolated vocal, clean stem, talk, or podcast.
- **Editor** — a local web app: upload a file, choose *Clean* or *Clean + Auto
  Tune*, then inspect and adjust every decision (gain curve, gate/breath/
  sibilance regions, a pitch lane showing sung vs tuned), re-render, and
  download the result.

Its design principle, carried from the plan: **no black box.** Every analysis
decision is written to an editable `edit_document.json`; rendering is
deterministic DSP that applies that document, so what you see is what you get.

### Quickstart

```bash
cd voxpolish
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e '.[ui,pitch]'          # editor + tuner; add separation/clean/vad as needed

# Command line
voxpolish process song.mp3 --mode song -o out/       # full song -> cleaned vocal + remix
voxpolish process talk.wav --mode voice -o out/      # a talk/podcast/clean stem
voxpolish pitch take.wav --strength 0.4 --apply      # subtle tuning -> take_tuned.wav

# Browser editor
voxpolish ui                          # opens the upload screen
voxpolish ui take.wav                 # opens a specific file
```

Runs locally on CPU (validated on a Geekom A9 Max, AMD Ryzen). ML backends are
optional extras; the pipeline falls back to DSP when they are absent.

Full package documentation: [`voxpolish/README.md`](voxpolish/README.md).
Product & engineering plan: [`docs/vox-cleanup-plan.md`](docs/vox-cleanup-plan.md).

### Status

Phase 1 (local web editor) — working and validated by ear on real songs
across separation → bleed suppression → cleanup → leveling/balance/mastering →
subtle tuning. The full test suite covers the pipeline, the editor server, and
the tuner:

```bash
cd voxpolish && pip install -e '.[ui,dev,pitch]' && python -m pytest tests/ -q
```

Queued next: user-authored mute regions; the coaching-analysis merge.

---

## Merging notes

- VoxPolish is self-contained under `voxpolish/` — a Python package with its own
  `pyproject.toml`, source, and tests. Merging another component beside it needs
  no path changes here.
- Runtime audio, sessions, and workspaces are git-ignored (see `.gitignore`);
  only source, tests, and docs are tracked.
- **License:** not yet chosen. Pick one before publishing — note that several
  optional model dependencies (Demucs, DeepFilterNet, Silero, WORLD) carry their
  own licenses to review before distribution.
