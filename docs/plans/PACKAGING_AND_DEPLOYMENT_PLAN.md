---
title: "Plan — packaging & deployment: how VOX ships"
category: plan
status: in-progress
created: 2026-08-09
updated: 2026-08-09
topics: [packaging, deployment, docker, pwa, distribution, hosting, licensing]
---

# Plan — packaging & deployment: how VOX ships

**Status:** in progress — **step 1 (Docker) is built** on
`claude/voiceassist-plugin-planning-krhz0d` (PR #46), not yet merged.

> ### Update — 9 Aug, later the same day
>
> Three things changed after this plan was first written, and two of them change
> the recommendation rather than just its status.
>
> **1. Docker is built.** `Dockerfile`, `.dockerignore`, `docker-compose.yml` and
> `docs/DEPLOYMENT.md` landed on PR #46, explicitly implementing Option C below.
> It ships two variants — a full heavy image (RoFormer separation + auto-tune)
> and a `--build-arg WITH_SEPARATION=0 WITH_PITCH=0` lean image — plus a GPU note
> and build-commit stamping for `/api/build`. The claim below that "no deployment
> artefact of any kind exists" was true when written and is now false.
>
> **2. A GPL constraint makes Option B (desktop) a licensing problem, not just an
> expensive one.** The voice-quality metrics run through `praat-parselmouth`,
> which is **GPLv3 linked in-process** — combining it with the proprietary engine
> makes a derivative work. That blocks any desktop / plugin / on-prem /
> embeddable build. **Hosted-only neutralises it entirely** (no distribution → no
> copyleft trigger). Lowest-effort fix if an off-server build is ever wanted:
> de-link and call the standalone Praat CLI at arm's length (identical numbers,
> so no re-calibration). See `memory/028-parselmouth-gpl-constraint.md` and
> `docs/dependency-license-audit.md`.
>
> **This is now the strongest argument for cloud-first** — stronger than the moat
> argument below, because it is a legal constraint rather than a preference.
> Note it also applies to *distributing* the Docker image to third parties;
> running it on our own host is fine.
>
> **3. A sale is being explored** (`memory/027`), which sharpens the same point:
> resolving the GPL constraint is listed as a pre-sale value lever, and an
> engine that never leaves the server is easier to sell than one already shipped
> to users' disks.

**Decision inputs:** VISION.md pillar goal ("all of it on a cloud server behind a
login for public testing"); the unify plan is already built; at the time of
writing no deployment artefact of any kind existed in the repo (see update above).

## Why now

The question Aaron asked: *"how do we put all this together in one concise
application, and how could it be packaged — a Windows download, a web server,
something else?"*

The first half is largely **already answered**: `voxsuite/server/unified.py`
serves Analyze, Polish, Fused, `/monitor`, `/timbertones` and `/hub` from **one
FastAPI app on one origin**, and `systems.py` is a single registry that the hub
directory reads. Unification is not the gap.

The gap is **distribution**. There is no `Dockerfile`, no `docker-compose.yml`,
no `fly.toml`/`render.yaml`, no systemd unit, no PyInstaller spec anywhere in
the repo. Today the suite runs on Candi's machine and is reached over Tailscale.
`docs/beta-readiness-audit.md` already lists packaging as majors **M13/M14**.

## The fact that drives every option

The system splits cleanly in two **by weight**, and this decides everything:

| Half | What's in it | Needs |
|---|---|---|
| **Light** | Pitch monitor, TimberTones, spectrum, onset trainer, recorder | Browser Web Audio only — **no server**, runs on a phone |
| **Heavy** | Separation (RoFormer), analysis, polish, auto-tune | torch + onnxruntime + librosa + parselmouth + model weights ≈ **2.5–4 GB installed** |

The heavy half is why "just ship a Windows .exe" is harder than it sounds: a
PyInstaller bundle carrying torch is a multi-gigabyte download, needs code
signing to avoid SmartScreen warnings, and torch bundling is notoriously
fragile.

## The options

### A. Cloud web app + login — *matches the stated vision*
One server; users sign in and upload. Works on any device including the phone
(which matters — the phone is the recorder, `memory/004`). One place to update.
**The scoring engine and the 50-reference calibration pack never leave the
server** — that is the moat, and it stays unreverse-engineerable.

*Costs:* a CPU box able to run RoFormer separation ≈ **$20–60/month**. Needs
auth, storage and a job queue, and the concurrency majors (M8/M10/M11) become
real the moment strangers use it.

### B. Windows desktop app — **blocked on licensing, not just cost**
Best built as a **Tauri/Electron shell over a bundled Python sidecar** — cheap
*because* `unified.py` already serves everything on one origin, so the desktop
window is a browser pointed at localhost.

> **Blocker:** `praat-parselmouth` is GPLv3 and linked in-process, so shipping it
> with the proprietary engine makes a derivative work. **This option cannot ship
> as proprietary software until that is resolved** (de-link to the Praat CLI, or
> replace it and re-validate). `memory/028`.

*Pros:* no server bill, users' own CPUs do the work, audio never leaves the
machine, works offline.
*Cons:* the GPL blocker above; 2.5–4 GB installer; code-signing cert
(~$100–400/yr) or scary warnings; an update mechanism to build; and it ships the
engine + calibration pack onto strangers' disks.

### C. Docker container — one artefact, both destinations ⭐
Package the unified server once. The **same image** then runs on Candi's machine
for Aaron *and* on a cloud host for testers — no divergence, no "works on my
machine." Removes the Tailscale-only fragility and is the prerequisite for A.

### D. PWA for the light half — the quick win
The monitor and TimberTones are already standalone, dependency-free pages. They
can be **installable on a phone**, offline, at zero hosting cost, independent of
the heavy engine. `VISION.md` already lists "PWA install" as a known gap.

## Recommended sequence

They build on each other rather than competing:

1. **Docker the unified server** (C) — ✅ **built** on PR #46; needs review and
   merge. Makes deployment repeatable and unblocks everything else.
2. **Ship the light half as a PWA** (D) — small; gives Aaron a real installable
   practice app on his phone now. **Note:** the light half (monitor,
   TimberTones, recorder) touches no parselmouth, so it is unaffected by the GPL
   constraint and can be distributed freely.
3. **Stand up the cloud instance with login** (A) — the stated vision and the
   right home for public testing. Fix the concurrency/job-cap majors as part of
   this, not after.
4. **Windows build** (B) — **parked on the GPL blocker**, not merely deferred.
   Reconsider only after parselmouth is de-linked *and* testers actually demand
   offline/local.

**Why cloud-first, in order of force:**

1. **Licensing.** Hosted-only means no distribution, so GPLv3 copyleft never
   triggers. Every off-server option needs the parselmouth work done first.
   This is a legal constraint, not a preference.
2. **The moat.** The goal is "the most powerful voice analysis app on the
   planet," and the moat is the calibrated scoring engine. Option A keeps it on
   the server; option B mails it to everyone — and with a sale being explored
   (`memory/027`), an engine that has never left the server is the easier asset
   to sell.
3. **Cost and reach.** One place to update, works on the phone, no installer.

## Known blockers before strangers touch it

From `docs/beta-readiness-audit.md` — the 8 release blockers are fixed, but
these remain and are load-bearing for a public instance:

- **M10** concurrency trio · **M8/M11** job caps · **M12** unified instantiation
- **M13/M14** packaging (this plan)
- **M18** recorder teardown

Plus one discovered in this session and parked as dream idea **D7**: a fresh
container cannot run the engine or render a PDF out of the box — `numpy`,
`scipy`, `librosa` are needed before `score_preflight.py` will even import, and
`reportlab`/`pdfplumber` before any PDF builds. Whatever image gets built must
bake these in; a `tools/setup.sh` or SessionStart hook would fix the local case
at the same time.

## Verification for step 1 (Docker)

- `docker build` produces an image that starts the unified server with no host
  Python.
- Inside the container: `/`, `/analyze`, `/polish`, `/monitor`, `/timbertones`,
  `/hub` all return 200; `/api/systems` returns the registry.
- `python3 tools/score_preflight.py` exits 0 **inside the image** (proves the
  engine deps and calibration pack are baked in correctly).
- `voxsuite/tests/` and the engine scoring tests pass inside the image.
- One real take runs end to end through Fused (separation → analysis → polish).
