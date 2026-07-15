# Handoff to ChatGPT: third-party dependency license audit

**For: ChatGPT (has read access to the `goodermine/aaroncodex` repository).**

## Goal

Audit every third-party dependency in this repository for compatibility with a
**paid, proprietary, closed-source commercial product that is distributed to
end users** (both a local/desktop app and a possible hosted service). The
product's own code is under a proprietary "all rights reserved" license (see
`/LICENSE`). Your job is to determine which bundled/relied-upon components are
**safe to ship in that model**, which are **not**, and what to do about the
ones that aren't.

This is the decisive question: *for a paid closed-source product we distribute,
does each dependency's license permit that?* Flag anything that doesn't.

## What to produce

1. **A per-dependency table** with columns:
   `name | version constraint | where declared | license (SPDX) | type (library code / AI model weights / CLI tool) | commercial closed-source distribution OK? (Yes/No/Conditional) | risk (None/Low/Medium/High/Blocker) | notes & required action`.
2. **A "blockers" section** listing anything that cannot be shipped as-is in a
   paid proprietary product, with a concrete recommended action for each
   (replace with X, isolate as a separate process, obtain a commercial license,
   remove the feature, etc.).
3. **A draft `NOTICE` file** listing every component that requires attribution
   in distributed software, with the exact attribution text each demands.
4. **A short executive summary**: can this ship commercially today, and if not,
   the shortest path to yes.

## What to flag as high-risk / blocker

- **Copyleft licenses**: GPL, AGPL, LGPL, MPL, EUPL, CDDL — any that can force
  disclosure of our source or impose license terms on our product when
  distributed or linked. AGPL is especially dangerous for a hosted service.
- **AI model *weights* with non-commercial or research-only terms** — the code
  can be permissively licensed (MIT) while the downloaded model checkpoint is
  CC-BY-NC, research-only, or has a separate commercial-use restriction. Check
  weights and code **separately**.
- **"Source-available but not for commercial use"** licenses.
- **Attribution / notice requirements** (BSD, Apache-2.0, MIT still require the
  notice to be reproduced) — not blockers, but must be honored in the NOTICE.
- **Patent clauses** (Apache-2.0 grant; any patent-retaliation terms).
- **Service Terms of Use**, distinct from software license — e.g. yt-dlp is
  permissively licensed, but downloading third-party (YouTube) content in a
  commercial product raises separate ToS and copyright issues; call this out.

## Dependencies to audit (exact, from the manifests)

### Component 1 — VoxPolish (`voxpolish/pyproject.toml`)
Core: `numpy`, `scipy`, `soundfile`, `pyloudnorm`
Extras:
- `separation`: `demucs`, `torch`, `torchaudio`
- `clean`: `deepfilternet`
- `vad`: `torch`, `silero-vad`
- `ui`: `fastapi`, `uvicorn`, `python-multipart`
- `pitch`: `pyworld`
- `dev`: `pytest`, `httpx`

### Component 2 — Vox Analysis (`voxanalysis/`)
Engine (`vox-analysis/engine/requirements.txt`): `numpy`, `scipy`, `librosa`,
`soundfile`, `matplotlib`, **`praat-parselmouth`** (wraps Praat — verify its
license carefully), and commented-optional: `openai`, `spleeter`, `crepe`.
Viewer (`vox-analysis/viewer/requirements.txt`): `fastapi`, `uvicorn`,
`python-multipart`, `httpx`, **`yt-dlp`** (+ inherits the engine list).
Downloader (`youtube-downloader/requirements.txt`): `fastapi`, `uvicorn`,
`yt-dlp`.

### Runtime-downloaded models & tools NOT in any requirements file (audit these too)
These are fetched or invoked at runtime — their weights/licenses matter as much
as the pip packages:
- **Demucs** model weights (e.g. `htdemucs_ft`) — separation.
- **DeepFilterNet** (DeepFilterNet3) model weights — denoise.
- **Silero VAD** model weights — gating.
- **WORLD vocoder** (via `pyworld`) — pitch correction.
- **UVR / `audio-separator`** and its models (BS-RoFormer, MDX23C, etc.),
  invoked from a separate venv at `~/.venvs/vox-sep-uvr/` (see the health check
  in `voxanalysis/vox-analysis/viewer/app.py`) — **community stem-separation
  model weights vary widely and several are non-commercial; scrutinize each.**
- Optional if enabled: `spleeter`, `crepe` (TensorFlow models), `openai` (API).

## Method notes for the auditor

- For each package, check both the **library license** and, where applicable,
  the **model-weight license** (they differ often for ML).
- Prefer the license as stated in the project's repository/PyPI metadata for the
  pinned/minimum version we use; note if a newer version changed license.
- Where a dependency is only used in an optional extra or a commented-out line,
  say so — it changes whether it ships.
- Consider both distribution modes: **(a)** bundled in a desktop app we ship,
  and **(b)** run server-side in a hosted SaaS (AGPL matters for (b)).
- Do **not** modify code. Produce the audit as a report (and the draft NOTICE).

## Context files worth reading

- `/LICENSE` — our proprietary product license (holder/contact are placeholders).
- `/README.md` — product overview and structure.
- `voxpolish/README.md`, `voxanalysis/README.md` — per-component detail.
- The manifests listed above.
