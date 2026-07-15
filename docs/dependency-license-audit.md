# Third-party dependency license audit

**Product:** VoxPolish + Vox Analysis — a **paid, proprietary, closed-source**
product distributed to end users (desktop and possibly hosted).
**Audited:** July 2026, against the dependency manifests on `main`.
**Auditor:** Claude (automated). License facts web-verified against PyPI /
project repositories where they carry risk (sources linked inline).

> **Not legal advice.** This is an engineering audit to surface risk and guide
> action. Before selling, have a lawyer confirm the copyleft (GPL) and
> model-weight (CC-BY-NC) conclusions below — those are the two that can
> actually stop you shipping.

---

## Executive summary — can it ship commercially today?

**All separation/licensing blockers resolved for a hosted product.**
- **parselmouth (GPL)** — neutralized by hosting (server-side only, never
  distributed → copyleft does not trigger). No code change required.
- **Model weights (#2 + #3)** — **DONE & VALIDATED.** Both separation paths now
  use the **MIT-licensed KimberleyJSN Mel-Band RoFormer** (`audio-separator`).
  Demucs is removed from code and dependencies. Tested on real material —
  RoFormer confirmed the best separator (Aaron, July 2026). The temporary
  Demucs A/B testing fallback is retired.
- **YouTube/yt-dlp (#4)** — resolved by design (no audio retained; download
  tooling is founder-only and not shipped).

No licensing blockers remain. Everything shipped is permissive with routine
attribution (`NOTICE`). Keep the hosting boundary (parselmouth stays
server-side) and run the pre-ship gate before release.

| # | Item | Where | Problem | Verdict |
|---|------|-------|---------|---------|
| 1 | **praat-parselmouth** | voxanalysis engine | **GPLv3+ copyleft** — forces your linked code open | **BLOCKER** |
| 2 | **Demucs pretrained weights** | ~~voxpolish~~ removed | Was CC-BY-NC | **RESOLVED — replaced by MIT RoFormer, validated** |
| 3 | **UVR / audio-separator models** | ~~voxanalysis~~ pinned | Was mixed | **RESOLVED — pinned to MIT RoFormer, validated** |
| 4 | **yt-dlp usage** | founder calibration tooling only | Public-domain software; YouTube ToS/copyright concern — **resolved for the shipped product by design** (see §4) | **RESOLVED for product; residual personal-tooling note** |

Everything else (numpy, scipy, soundfile, pyloudnorm, torch, torchaudio,
fastapi, uvicorn, python-multipart, httpx, librosa, matplotlib, pyworld,
**silero-vad**, **deepfilternet**) is **permissive and safe for a paid
closed-source product**, requiring only that their notices be reproduced (see
`NOTICE`).

---

## Blockers — detail and fix options

### 1. praat-parselmouth — GPLv3+ (copyleft) — BLOCKER

`praat-parselmouth` is licensed **GPL v3 or later**
([PyPI](https://pypi.org/project/praat-parselmouth/),
[LICENSE](https://github.com/YannickJadoul/Parselmouth/blob/master/LICENSE)); it
embeds Praat (GPLv2+). It is a C-extension **linked into your Python process**,
so combining it with your proprietary code creates a derivative work that GPLv3
would require you to release under the GPL. That is incompatible with a
proprietary paid product. It is used by the analysis engine
(`voxanalysis/vox-analysis/engine/analyse_song.py`) for the Praat-grade metrics
(jitter, shimmer, HNR, CPPS, formants).

**Fix options (pick one):**
- **(A) Replace it** — reimplement the acoustic measures on permissively
  licensed libraries (numpy/scipy/librosa). Jitter/shimmer/HNR/CPPS/formants are
  well-documented algorithms; this is real work but yields a clean,
  fully-owned engine. *Recommended long-term.*
- **(B) Arm's-length separate process** — call the standalone **Praat** binary
  (GPLv2+) as a fully separate subprocess (no linking, data in/out over
  files/stdio). Under the "mere aggregation" principle this can keep your code
  out of the GPL, but you would still **distribute a GPL program** with the
  product (must offer Praat's source — trivial, it's public) and the boundary
  must be genuinely arm's-length. **Have a lawyer confirm** this boundary before
  relying on it.
- **(C) Drop the parselmouth-derived metrics** from the shipped product.

Do **not** ship parselmouth linked into the product as-is.

### 2. Demucs pretrained model weights — CONFIRMED non-commercial — BLOCKER

**Verified (July 2026):** Demucs **code** is MIT, but the default **pretrained
weights** (`htdemucs`, `htdemucs_ft` / `HDEMUCS_HIGH_MUSDB_PLUS`) are
**CC-BY-NC 4.0 — non-commercial**, because they were trained on MUSDB18-HQ
(a non-commercial dataset). Confirmed via PyTorch/Meta's own torchaudio pipeline
metadata and multiple model cards. The MIT license covers only the code.

**This does not improve under hosting.** "Non-commercial" restricts the *purpose
of use*, not distribution — a paid subscription is commercial use whether the
weights run on a server or a laptop. So the default Demucs weights **cannot be
used in the paid product**, hosted or shipped.

**Replacement options (ranked for a hosted, privacy-minded paid product):**

- **(D) ✅ RECOMMENDED — KimberleyJSN Mel-Band RoFormer vocal model (MIT).**
  A **specific, commercially-licensed, state-of-the-art** vocal/instrumental
  separator. Verified: the checkpoint at
  [huggingface.co/KimberleyJSN/melbandroformer](https://huggingface.co/KimberleyJSN/melbandroformer)
  is tagged **License: MIT** (relicensed from GPL-3.0 to MIT by the author in
  April 2026). Mel-Band / BS-RoFormer is **current SOTA — better than Demucs,
  far better than Spleeter** — and it separates exactly what we need
  (vocals vs. instrumental). The runner code (lucidrains BS-RoFormer,
  `python-audio-separator`, `melband-roformer-infer`) is all MIT. **Free,
  self-hosted, no per-use cost, no sending user audio to a third party** — the
  best fit for a hosted product that keeps audio private.
  - *Caveats:* pin to **this specific checkpoint** — the `melband-roformer-infer`
    catalogue mixes ~89 models of varying licenses, so do not use "the default."
    The GitHub `LICENSE` file wasn't retrievable; confirmation rests on the HF
    model-card MIT tag plus corroborating relicense reports — **save a dated copy
    of the model card as evidence** of the grant at time of use (it was
    relicensed recently). Training-data provenance is the author's
    responsibility under their MIT grant.
- **(A) Commercial stem-separation API** (LALAL.AI, AudioShake, Moises) — zero
  licensing ambiguity and top quality, but **ongoing per-use cost** and it
  **sends user audio to a third party** (a privacy downside for this product).
  A fallback if you'd rather not self-host GPU inference.
- **(B) Spleeter (Deezer)** — MIT, free, self-hostable, but **lower quality**
  (≈11 kHz ceiling — weak on sibilance/high end). A fallback only if RoFormer
  inference is too heavy to host.
- **(C) Train/own Demucs weights** on cleared data (Demucs code is MIT) — best
  only if you need full ownership and can invest in training.

**Note:** option (D) also resolves Blocker #3 — standardize **both** VoxPolish
song mode and Vox analysis stem separation on the one MIT RoFormer checkpoint,
instead of maintaining Demucs + a grab-bag of UVR models.

### 3. UVR / audio-separator community models — HIGH, verify per model

`audio-separator` the package is **MIT**
([repo](https://github.com/nomadkaraoke/python-audio-separator)) and only
requires UVR attribution. But it downloads **community model weights** (MDX-Net,
VR-arch, MDX23C, BS-RoFormer) whose **licenses vary by author** — several UVR
models are non-commercial or unstated. The analysis engine uses this via
`~/.venvs/vox-sep-uvr/`.

**Fix:** pin to **specific model files whose weights are confirmed
commercial-friendly**, record each model's license in `NOTICE`, and add the
required UVR attribution. Do not ship "whatever model the tool defaults to."

### 4. yt-dlp / YouTube downloading — RESOLVED for the shipped product

`yt-dlp` is released into the **public domain (Unlicense)** — no software-license
problem. The concern was **behavioral**: downloading YouTube content in a paid
product implicates **YouTube's Terms of Service** and **copyright** in the
fetched audio.

**Resolution (architecture decision, July 2026):**
- **No audio is ever retained.** The engine extracts acoustic metrics from a
  reference recording and keeps **only the derived numeric metrics** (facts /
  measurements), which are later used to compare songs. The copyrighted audio is
  never stored, served, or shipped.
- **yt-dlp and the download interface are founder-only calibration tooling.**
  The **shipped product will not include the YouTube-download front end** or the
  `yt-dlp` dependency; it operates on the pre-computed reference metrics.
- Therefore the **shipped product carries no YouTube ToS exposure and stores no
  copyrighted audio.**

**Residual note (not a product blocker):** the founder's own one-time
calibration downloading still technically touches YouTube's ToS (a personal,
account-level matter, not something baked into the product). Because only
derived metrics are kept — never the audio — the copyright posture is strong
(retaining measurements about a performance, used transformatively for
calibration). Where practical, prefer references you have rights to. Keep
`yt-dlp` out of the distributed/hosted codebase — a private calibration script,
not a product dependency.

---

## Full dependency table

Type: **L** = library code, **W** = model weights, **T** = tool/CLI.
"Ship?" = safe to distribute in a paid closed-source product.

| Dependency | Where | License | Type | Ship? | Notes |
|---|---|---|---|---|---|
| numpy | both (core) | BSD-3-Clause | L | ✅ | notice |
| scipy | both (core) | BSD-3-Clause | L | ✅ | notice |
| soundfile | both | BSD-3-Clause | L | ✅ | bundles **libsndfile (LGPL-2.1+)** — dynamically linked, OK; keep it replaceable + reproduce LGPL notice |
| pyloudnorm | voxpolish | MIT | L | ✅ | notice |
| torch | voxpolish extras | BSD-3-Clause | L | ✅ | reproduce bundled third-party notices |
| torchaudio | voxpolish extras | BSD-2-Clause | L | ✅ | notice |
| **silero-vad** | voxpolish `vad` | **MIT** (weights incl.) | L+W | ✅ | verified MIT — safe ([LICENSE](https://github.com/snakers4/silero-vad/blob/master/LICENSE)) |
| **deepfilternet** | voxpolish `clean` | **MIT / Apache-2.0** (weights incl.) | L+W | ✅ | verified dual-permissive — safe |
| **pyworld** (WORLD) | voxpolish `pitch` | MIT (wrapper) / modified-BSD (WORLD), no patents | L | ✅ | verified — safe |
| **demucs** (code) | voxpolish `separation` | MIT | L | ✅ | code only — **weights are Blocker #2** |
| Demucs **weights** | runtime | **CC-BY-NC 4.0 (confirmed)** | W | ⛔ | non-commercial — **Blocker #2**, replace |
| fastapi | both (ui) | MIT | L | ✅ | notice |
| uvicorn | both (ui) | BSD-3-Clause | L | ✅ | notice |
| python-multipart | both (ui) | Apache-2.0 | L | ✅ | notice + state changes if any |
| httpx | voxpolish dev, viewer | BSD-3-Clause | L | ✅ | notice |
| pytest | voxpolish dev | MIT | L | ✅ | dev only — not shipped |
| librosa | voxanalysis engine | ISC | L | ✅ | notice |
| matplotlib | voxanalysis engine | Matplotlib (BSD-style/PSF) | L | ✅ | notice |
| **praat-parselmouth** | voxanalysis engine | **GPL-3.0-or-later** | L | ⛔ | **Blocker #1** |
| **yt-dlp** | founder calibration tooling | Unlicense (public domain) | T | ✅ | not shipped in product; no audio retained — see §4 |
| **audio-separator** | voxanalysis stem sep | MIT (package) | T | ✅ | package OK; **models = Blocker #3** |
| UVR models | runtime | varies per model | W | ⚠️ | **Blocker #3** |
| openai *(commented)* | engine optional | Apache-2.0 (SDK) | L | ✅ | not shipped; API sends data out if enabled |
| spleeter *(commented)* | engine optional | MIT | L+W | ⚠️ | not shipped; verify model terms if enabled |
| crepe *(commented)* | engine optional | MIT | L+W | ✅ | not shipped |

---

## Recommended path to "clear to sell"

1. **parselmouth (Blocker #1) — resolved by hosting.** Keep it server-side only
   (never distribute a binary/desktop build containing it); GPL copyleft is not
   triggered by network use. If a downloadable build is ever needed, revisit
   (replace, or arm's-length Praat with legal sign-off).
2. **Swap the separation model (Blockers #2 + #3)** — replace Demucs (and the
   UVR models) with the **MIT-licensed KimberleyJSN Mel-Band RoFormer**
   checkpoint (§2, option D). Pin that exact checkpoint, keep a dated copy of its
   MIT model card, and add its attribution to `NOTICE`. One swap clears both
   weight blockers.
3. **yt-dlp (Blocker #4) — resolved by design.** Keep the YouTube-download
   tooling and `yt-dlp` out of the shipped product (founder-only calibration),
   and retain only derived metrics, never audio. Confirm the shipped build has
   no `yt-dlp` dependency before release.
4. **Ship the `NOTICE` file** with the product (attribution for all permissive
   deps).
5. **Have a lawyer review** the above and the final `NOTICE`/LICENSE before sale.

Once the model swap (step 2) lands and `NOTICE` ships, the permissive stack (the majority
of the tree) is clear for a paid closed-source product.
