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

**Not yet — but the list is down to two.** Two hard blockers remain (parselmouth,
model weights). The YouTube/yt-dlp concern is **resolved for the shipped product**
by design (no audio retained, download tooling is founder-only and not shipped —
see §4). Everything else is clear (permissive) with routine attribution.

| # | Item | Where | Problem | Verdict |
|---|------|-------|---------|---------|
| 1 | **praat-parselmouth** | voxanalysis engine | **GPLv3+ copyleft** — forces your linked code open | **BLOCKER** |
| 2 | **Demucs pretrained weights** | voxpolish `separation` | Code MIT, but **weights CONFIRMED CC-BY-NC (non-commercial)** — not usable in a paid product | **BLOCKER — replace (see §2 options)** |
| 3 | **UVR / audio-separator models** | voxanalysis stem sep | Package MIT, but **individual model weights vary**; some non-commercial | **HIGH — verify per model** |
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

**Replacement options (best per situation):**
- **(A) Commercial stem-separation API/SDK** (e.g. LALAL.AI, AudioShake, Moises).
  Paid per-use/subscription, but **zero licensing ambiguity and top quality**.
  Since the product is hosted, calling a paid separation API server-side is
  clean and offloads the whole problem. *Best for licensing clarity.*
- **(B) Spleeter (Deezer)** — MIT code; models trained on Deezer's **own**
  catalog (not the NC MUSDB18) and bundled in the MIT repo, so widely used
  commercially. **Free and self-hostable**, but lower quality (≈11 kHz ceiling —
  weak on sibilance/high end, which matters for the Sibilance module and
  analysis). Small residual: the repo licenses "code" explicitly and models by
  inclusion. *Best if staying free/self-hosted and quality can drop.*
- **(C) Train/fine-tune Demucs weights yourself** on data you own or license
  (Demucs code is MIT). **Best quality + fully owned**, but requires a cleared
  training set and training effort. *Best long-term if quality is paramount.*
- **(D) A specific open model with explicitly commercial weights** (some
  Apache/MIT BS-RoFormer / MDX23C checkpoints) — verify each checkpoint
  individually; many popular ones are non-commercial or unstated.

**Note:** this same choice resolves Blocker #3 — pick **one** commercially-clear
separation solution and use it for both VoxPolish song mode and Vox analysis
stem separation, instead of maintaining two model stacks.

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

1. **Resolve parselmouth (Blocker #1)** — decide replace (A) vs arm's-length
   Praat (B); if (B), get legal sign-off on the boundary.
2. **Resolve Demucs weights (Blocker #2)** — get the weight license in writing or
   switch models; document the answer.
3. **Pin & document UVR models (Blocker #3)** — choose commercial-safe model
   files, record each license, add UVR attribution.
4. **yt-dlp (Blocker #4) — resolved by design.** Keep the YouTube-download
   tooling and `yt-dlp` out of the shipped product (founder-only calibration),
   and retain only derived metrics, never audio. Confirm the shipped build has
   no `yt-dlp` dependency before release.
5. **Ship the `NOTICE` file** with the product (attribution for all permissive
   deps) — draft added alongside this report.
6. **Have a lawyer review** items 1–4 and the final `NOTICE`/LICENSE before sale.

Once 1–4 are closed and `NOTICE` ships, the permissive stack (the large majority
of the tree) is clear for a paid closed-source product.
