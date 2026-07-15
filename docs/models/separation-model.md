# Pinned separation model — provenance & verification

This is the single source of truth for the stem-separation model both components
use. Disaster-1 guard from `docs/separation-model-swap-plan.md`: never let the
engine silently use a different (possibly non-commercial) model.

## The model

- **Name (audio-separator):** `vocals_mel_band_roformer.ckpt`
- **What it is:** Mel-Band RoFormer (vocals) by **Kimberley Jensen**
- **License:** **MIT** — commercial use permitted
- **Source of truth:** https://huggingface.co/KimberleyJSN/melbandroformer
  (model card tagged `License: mit`; relicensed GPL-3.0 → MIT by the author,
  April 2026)
- **Runner:** `audio-separator` (MIT), which resolves and downloads this exact
  filename from its model registry.

Referenced by:
- VoxPolish: `voxpolish/src/voxpolish/stages/separation.py` → `SEPARATION_MODEL`
- Vox analysis: `voxanalysis/vox-analysis/engine/tools/stems/batch_stems.sh` →
  `SEP_MODEL`

## Verification checklist (do on the target machine, once)

1. Let `audio-separator` download the model on first run.
2. **Record the file's SHA-256 below** so future runs can be verified against it:

   ```
   sha256sum ~/.cache/audio-separator-models/vocals_mel_band_roformer.ckpt
   # (path varies; audio-separator prints the model dir on load)
   ```

   - **SHA-256:** `TODO — fill in after first verified download`

3. **Save a dated copy/screenshot of the HF model card** showing `License: mit`
   as evidence of the grant at time of use (the relicense is recent).
4. For hosted deploys, **vendor the model file** into the image/volume so runtime
   never depends on a live download.

## If you change the model

Any non-default model (e.g. a lighter checkpoint for CPU speed) is allowed
*technically*, but **you own the license check** — confirm its weights permit
commercial use before shipping, and update this file. Do not use the
audio-separator "default" or arbitrary UVR community models: several are
non-commercial (see `docs/dependency-license-audit.md` Blocker #3).
