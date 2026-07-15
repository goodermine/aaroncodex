# Plan: replace Demucs + UVR with the MIT Mel-Band RoFormer

**Goal:** remove the two non-commercial weight blockers (#2 Demucs CC-BY-NC,
#3 UVR mixed) by standardizing **both** separation paths on the MIT-licensed
KimberleyJSN Mel-Band RoFormer, run through `audio-separator` (MIT).

**Verified feasibility:** `audio-separator` exposes the Kim MIT model as
`vocals_mel_band_roformer.ckpt` ("MelBand Roformer | Vocals by Kimberley
Jensen"), auto-downloaded on first use. One MIT toolchain covers both engines.

## The two seams (both narrow — this is why the swap is contained)

- **VoxPolish** — `voxpolish/src/voxpolish/stages/separation.py`:
  `separate(path, model, shifts) -> (vocal, instrumental, sr)` numpy arrays.
  Called once (`pipeline.py`). Downstream depends on: `instrumental` summing
  with `vocal` back to the mix (the bleed suppressor and the remix
  `cleaned_vocal + instrumental` both assume this).
- **Vox analysis** — `engine/tools/stems/batch_stems.sh` (runs `audio-separator`
  in venv `~/.venvs/vox-sep-uvr`, model `UVR_MDXNET_Main.onnx`) invoked by
  `pitch_track.py: separate_stems(input, job_dir) -> (vocals_path, instr_path)`,
  which locates outputs via `_find_stem(dir, "vocals"|"instrumental")`.

## The change

1. **VoxPolish**: rewrite `separate()` internals to run `audio-separator` with
   `vocals_mel_band_roformer.ckpt`; **derive `instrumental = mix − vocal`** for a
   guaranteed phase-coherent sum; normalize sample rate / channels / length.
   Keep the exact `(vocal, instrumental, sr)` contract. Default model → the MIT
   RoFormer. Drop `demucs` from the shipped dependency; keep the seam swappable.
2. **Vox analysis**: change `batch_stems.sh` default model to
   `vocals_mel_band_roformer.ckpt`; make `_find_stem` match RoFormer output
   naming. Keep the script/function interface identical.
3. **Pinning & provenance**: pin the exact model filename; record it + license in
   a manifest and in `NOTICE`; never silently fall back to a different model.
4. **Deps**: replace voxpolish `separation = [demucs, torch, torchaudio]` extra
   with `separation = [audio-separator]`; voxanalysis already uses it.

---

## The 3 ways this could go disastrously wrong (and the guards)

### Disaster 1 — Wrong / non-commercial / missing model silently breaks or re-taints the engine
`audio-separator` auto-downloads models by name from its registry. Failure modes:
(a) a typo or registry change pulls a **different RoFormer weight that is NON-
commercial**, silently defeating the entire legal purpose; (b) the download fails
at runtime (network / HF outage) and separation dies with an opaque error;
(c) a future package version renames/removes the model.

**Guards:**
- **Pin one exact filename** (`vocals_mel_band_roformer.ckpt`) in a single
  constant, plus a `docs/models/separation-model.md` manifest recording the
  model, its **MIT** source (HF card), and the file **SHA-256**.
- **Verify on load**: check the resolved model file's hash against the manifest;
  if it mismatches or is absent, **fail loudly with a clear message** — never
  auto-substitute another model.
- **Vendor/cache** the model into a known path for hosted deploys so runtime
  never depends on a live download.
- Keep a **dated copy of the MIT model card** as license evidence (audit §2).

### Disaster 2 — Output-contract mismatch corrupts everything downstream
The two engines have strict, *different* output expectations:
- **VoxPolish** expects numpy `(vocal, instrumental, sr)` where `vocal +
  instrumental ≈ mix`. RoFormer writes **files** at its own sr (44.1 kHz),
  stereo, and its instrumental is an **independent estimate** that may not sum
  back cleanly → the remix could double or gap the vocal, and the
  instrumental-referenced **bleed suppressor** (assumes `vocal+instr≈mix`) could
  produce artifacts.
- **Vox analysis** locates outputs by name; RoFormer/audio-separator filenames
  (`..._(Vocals)_....wav`) differ from the MDX naming `_find_stem` expects →
  `stem_separation_failed`.

**Guards:**
- VoxPolish: **derive `instrumental = mix − vocal`** (load the mix, subtract the
  separated vocal) — guarantees the sum reconstructs and makes the remix exactly
  `mix + (cleaned − raw)vocal`. Normalize sr, channel count, and length (min).
- Vox analysis: update `_find_stem` to match audio-separator's RoFormer output
  names (and/or rename outputs to canonical `vocals`/`instrumental`).
- **Contract tests** on both seams (mock the separator) asserting shapes, sr,
  and the sum-reconstruction property — so a wiring regression fails in CI, not
  in production.

### Disaster 3 — RoFormer is far heavier than the old models → CPU timeouts / OOM / unusable speed
The current MDX model was chosen because RoFormer was too heavy "for interactive
CPU uploads." On the AMD CPU, Mel-Band RoFormer can take minutes/song and lots of
RAM → (a) exceed the 30-min `STEM_TIMEOUT_SECONDS`; (b) OOM on long files;
(c) make VoxPolish renders unusably slow.

**Guards:**
- **Benchmark on the target CPU first** (part of the on-hardware validation).
- Keep the **timeout with a clear, actionable error** (never a silent hang).
- Provide a **configurable model** so a lighter checkpoint (e.g.
  `mel_band_roformer_kim_ft_unwa` or an MDX MIT model) can be selected if the
  default is too slow — the pin is the *default*, not a hard-wire.
- Recommend **GPU for the hosted deployment** (RoFormer is GPU-friendly); the
  hosted service is the real target, so CPU dev-box slowness is not a shipping
  blocker but must be a known, documented expectation.
- `audio-separator` already chunks internally; ensure large-file handling and a
  memory-bounded path.

---

## Self-audit of this plan

- **Does it actually remove the blockers?** Yes — both weight sources become the
  one MIT model; Demucs (NC) and UVR-default (mixed) are removed from the
  shipped default. #2 and #3 close together.
- **Biggest residual risk?** Disaster 3 (CPU performance). It cannot break
  *correctness*, only speed/timeouts, and it is mitigated by configurability +
  GPU-for-hosting. Acceptable.
- **What can I NOT verify in this environment?** The real model is multi-GB and
  RoFormer inference is heavy — **I cannot download or run it in the sandbox.**
  Therefore this change ships as: correct wiring + safety rails + **contract
  tests that pass without the model**, with the existing suites kept green. The
  **actual neural separation (quality, speed, that the MIT weight loads)** must
  be validated on the A9 Max — a handoff covers it. I will not claim end-to-end
  separation works from here.
- **Reversibility?** The Demucs backend code is preserved behind the seam
  (selectable), so a rollback is a one-line default change, not a revert.
- **Blast radius?** Contained to the two separation functions + config + deps.
  Voice-mode VoxPolish and all non-separation analysis are untouched.

## Implementation order

1. VoxPolish separation backend (audio-separator + mix−vocal) + contract tests.
2. Vox analysis `batch_stems.sh` model + `_find_stem` compatibility.
3. Model pin constant + `docs/models/separation-model.md` manifest + NOTICE.
4. Deps (pyproject extra), audit doc cross-links.
5. Handoff: on-hardware model download + separation quality + CPU benchmark.

## Status — implemented (wiring), pending on-hardware validation

**Done in code (this change):**
- VoxPolish `separate()` rewritten to the RoFormer/audio-separator backend with
  `instrumental = mix − vocal` and sr/channel/length normalization; default model
  pinned to `SEPARATION_MODEL`. Demucs removed from the `separation` extra.
- Vox analysis `batch_stems.sh` default model → `vocals_mel_band_roformer.ckpt`
  (`_find_stem` already matches RoFormer output naming — verified).
- Model manifest `docs/models/separation-model.md`; `NOTICE` updated.
- 5 VoxPolish contract tests (mocked separator) — full suite green (146);
  Vox analysis viewer suite unchanged (69 pass; the 1 pre-existing failure is the
  environment health check, not this change).

**NOT validated here (sandbox cannot download multi-GB models or run RoFormer):**
the model actually downloading as the MIT weight, separation quality, and CPU
speed/timeout behaviour. See `docs/handoffs/separation-swap-validation.md`.

## Provenance & the Demucs-fallback question (Candi's feedback, July 16)

Candi (VOX analysis) is right that a separator change **shifts the measurements**
(pitch coverage, HNR, jitter/shimmer, formants), so:
- **Every metrics JSON now records the separator + model** (implemented:
  `run_stem_separation` stamps `separator`, `separator_model`,
  `separator_backend`, `separator_license` into `stem_separation`, parsed from
  the actual output filename). SHA-256 / chunk / overlap are recorded on the
  target machine (`docs/models/separation-model.md`).
- **Do not compare a RoFormer score with a historical Demucs score** without
  marking the separator change. Treat RoFormer as a *new baseline*, validated
  against Demucs on 8–12 recordings (handoff), not an in-place score swap.

**VALIDATED (July 2026):** Aaron tested RoFormer on real material and confirmed
it is the best separator. RoFormer is the adopted baseline; the temporary Demucs
A/B testing fallback is **retired**. Demucs is gone from all VoxPolish code and
dependencies; the Vox analysis stem helper defaults to the RoFormer. Any future
Demucs use is founder-side offline provenance only (its weights are CC-BY-NC and
must never ship).

**Pre-ship gate (must pass before any paid release):**
- VoxPolish `SEPARATION_MODEL` and Vox analysis `SEP_MODEL` are the MIT RoFormer.
- No Demucs (or other CC-BY-NC / non-commercial) model is configured as a
  default or an automatic fallback in any shipped/hosted path.
- `demucs` is not a shipped dependency (confirmed: removed from the `separation`
  extra; audio-separator is the only separation backend).
- Any metrics JSON produced by the shipped product shows
  `separator_license: MIT` (the stamping flags non-MIT models as UNVERIFIED).
## Validation outcome — 16 July 2026

The hardware validation is complete. RoFormer was cleaner and clearer in the
full-song listening comparison and improved median voiced-frame coverage and
pitch confidence across ten representative excerpts without destabilising
median pitch drift. It is now the sole separator in the product path.

The Demucs test installation and the model-selection override have been
removed from VoxPolish. Historical Demucs metrics remain retained and labelled
as historical provenance; they are not recomputed or directly score-compared
with RoFormer output.
