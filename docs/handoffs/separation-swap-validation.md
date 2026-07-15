# Handoff: validate the RoFormer separation swap on hardware (for Daisy / Aaron)

The code swap from Demucs/UVR to the **MIT Mel-Band RoFormer** is done and the
test suites are green, BUT the real model was **not** run in the build sandbox
(multi-GB download + heavy inference). This handoff is the on-hardware
validation — it's what confirms the swap actually works, not just wires up.

Context: `docs/separation-model-swap-plan.md` (plan + the 3 disaster guards),
`docs/models/separation-model.md` (the pinned model), `docs/dependency-license-audit.md` §2.

## 1. Setup

```bash
cd aaroncodex && git pull
# VoxPolish
cd voxpolish && source .venv/bin/activate
pip install -e '.[separation,ui,pitch,dev]'   # separation now = audio-separator
python -m pytest tests/ -q                      # expect 146 passed
```

## 2. Disaster-1 check — the RIGHT (MIT) model loads

```bash
python - <<'PY'
from voxpolish.stages import separation
print("pinned:", separation.SEPARATION_MODEL)   # vocals_mel_band_roformer.ckpt
print("backend available:", separation.available())
PY
```

Then process a real song and confirm the model downloads as the Kim MIT
checkpoint:

```bash
voxpolish process song.mp3 --mode song -o out_roformer/
```

- Record the model directory audio-separator prints, and:
  `sha256sum <that dir>/vocals_mel_band_roformer.ckpt`
  → **write the hash into `docs/models/separation-model.md`** (fills the TODO).
- Confirm it's the Kim vocals model (not some other RoFormer/UVR default).

## 3. Disaster-2 check — output contract holds

- Confirm `out_roformer/` has `vocal_cleaned.wav`, `instrumental.wav`,
  `remix.wav`, `removed.wav`.
- **Listen to the remix**: it should sound like the original song with the
  cleaned vocal — no doubled vocal, no dropouts (proves `vocal + instrumental ==
  mix`). If the vocal sounds doubled or the backing has holes, report it.
- **Listen to `removed.wav`**: cleanup residue only — no full instrumental
  leaking in.
- Vox analysis side: run one analysis that triggers stem separation and confirm
  it finds both stems (no `stem_separation_failed`), e.g. via the engine/viewer
  path that calls `separate_stems`.

## 4. Disaster-3 check — CPU speed / memory (the real risk)

RoFormer is much heavier than the old MDX model. On the A9 Max CPU:

- **Time a full-song separation** (`time voxpolish process song.mp3 --mode song ...`).
  Record seconds/song and peak RAM.
- If it exceeds the 30-min Vox-analysis timeout (`STEM_TIMEOUT_SECONDS`) or is
  painfully slow: note it. Mitigations already supported — pass a lighter model
  via `--model` (Vox analysis) / `settings.separation_model` (VoxPolish), e.g.
  `mel_band_roformer_kim_ft_unwa.ckpt`, or plan GPU for the hosted deployment.
- Decide: is CPU separation acceptable for dev, with GPU for hosting? (Expected
  answer: yes — hosting is the real target.)

## 4a. VOX A/B validation matrix (Candi's protocol)

Because a separator change shifts the measurements, RoFormer must be validated
as a *new baseline* against Demucs — not assumed better. Run **8–12
representative recordings** through **both** separators (Demucs is retained as an
internal validation/provenance tool only — NOT a shipped runtime fallback, since
its weights are CC-BY-NC) and compare:

- Audible vocal clarity and backing-vocal bleed
- Residual instruments in quiet vocal passages
- Pitch-tracker voiced-frame coverage and confidence
- Changes in pitch deviation, drift, HNR, jitter, shimmer
- Runtime and memory use

Acceptance: RoFormer becomes the baseline **only if** it produces cleaner stems
without destabilising the measurements. Confirm each metrics JSON now carries
the `separator` / `separator_model` / `separator_license` provenance (stamped by
`run_stem_separation`), and that historical Demucs scores are **kept and labelled
by separator**, never overwritten or compared cross-separator without a marker.

## 5. Report back

1. Test suite count (expect 146 VoxPolish).
2. Model: confirmed MIT Kim checkpoint? SHA-256 recorded?
3. Remix / removed.wav listening verdict (contract holds?).
4. Vox analysis separation: found both stems, no failure?
5. CPU: seconds/song, peak RAM, and whether a lighter model or GPU is needed.
6. Any traceback verbatim.

Scope: do NOT change tuning/DSP defaults or other features. If separation
quality is worse than the old Demucs/UVR on real material, report where — that
decides whether to keep this checkpoint or pick another MIT one.
