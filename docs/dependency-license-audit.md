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

**Not yet.** Two hard blockers and one product-legal issue must be resolved
first. Everything else is clear (permissive) with routine attribution.

| # | Item | Where | Problem | Verdict |
|---|------|-------|---------|---------|
| 1 | **praat-parselmouth** | voxanalysis engine | **GPLv3+ copyleft** — forces your linked code open | **BLOCKER** |
| 2 | **Demucs pretrained weights** | voxpolish `separation` | Code MIT, but **weight license unstated / reported CC-BY-NC (non-commercial)** | **BLOCKER until resolved** |
| 3 | **UVR / audio-separator models** | voxanalysis stem sep | Package MIT, but **individual model weights vary**; some non-commercial | **HIGH — verify per model** |
| 4 | **yt-dlp usage** | voxanalysis downloader/viewer | Software is public-domain, but **downloading YouTube content in a paid product breaches YouTube ToS / copyright** | **HIGH (product-legal, not a license)** |

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

### 2. Demucs pretrained model weights — ambiguous / possibly non-commercial — BLOCKER until resolved

Demucs **code** is **MIT**
([repo](https://github.com/facebookresearch/demucs)), which permits commercial
use. But the **pretrained weights** (`htdemucs`, `htdemucs_ft`) are **not given
an explicit license in the repo**, and third-party summaries report the weights
as **CC-BY-NC 4.0 (non-commercial)**. For a paid product this ambiguity is a
blocker: MIT code does not automatically license the weights.

**Fix options:**
- **(A) Resolve the weight license** — get an authoritative/written answer from
  the authors, or find the model card that states the weight terms. If
  confirmed commercial-OK, document it and proceed.
- **(B) Switch to a separation model with clearly commercial-friendly weights**,
  and document that model's license.
- Until (A) or (B), treat Demucs-based separation as **not cleared for sale**.
  (Note also: separating third-party songs raises its own copyright question
  about the *source audio*, independent of the model license.)

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

### 4. yt-dlp / YouTube downloading — HIGH (product-legal, separate from license)

`yt-dlp` is released into the **public domain (Unlicense)** — no software-license
problem. The risk is **behavioral**: a commercial product that downloads YouTube
(or other site) content likely violates **YouTube's Terms of Service** and can
implicate **copyright** in the fetched material. This is a product/legal
decision, not a dependency license.

**Fix:** confirm with a lawyer whether the download feature can ship in a paid
product; consider restricting it to user-owned/licensed sources, or removing it.

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
| Demucs **weights** | runtime | unstated / reported CC-BY-NC | W | ⛔ | **Blocker #2** |
| fastapi | both (ui) | MIT | L | ✅ | notice |
| uvicorn | both (ui) | BSD-3-Clause | L | ✅ | notice |
| python-multipart | both (ui) | Apache-2.0 | L | ✅ | notice + state changes if any |
| httpx | voxpolish dev, viewer | BSD-3-Clause | L | ✅ | notice |
| pytest | voxpolish dev | MIT | L | ✅ | dev only — not shipped |
| librosa | voxanalysis engine | ISC | L | ✅ | notice |
| matplotlib | voxanalysis engine | Matplotlib (BSD-style/PSF) | L | ✅ | notice |
| **praat-parselmouth** | voxanalysis engine | **GPL-3.0-or-later** | L | ⛔ | **Blocker #1** |
| **yt-dlp** | voxanalysis dl/viewer | Unlicense (public domain) | T | ⚠️ | license fine; **YouTube ToS — Blocker #4** |
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
4. **Decide the yt-dlp feature (Blocker #4)** — legal call; restrict or remove.
5. **Ship the `NOTICE` file** with the product (attribution for all permissive
   deps) — draft added alongside this report.
6. **Have a lawyer review** items 1–4 and the final `NOTICE`/LICENSE before sale.

Once 1–4 are closed and `NOTICE` ships, the permissive stack (the large majority
of the tree) is clear for a paid closed-source product.
