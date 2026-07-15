# VOX Cloud Alpha Handoff

This is the handoff for the coding agent taking VOX Cloud Alpha from a local working vocal-analysis pipeline toward a private/public SaaS MVP.

## Product Name

User-facing product direction: **VOX Cloud Alpha**

Core engine: **VOXAI**

Coach persona/output layer: **Candi** / **Candeza**

System role: a singing-analysis and coaching pipeline that receives a vocal take, measures the audio, converts the metrics into a warm but technically grounded coaching report, saves progress, and tells the singer what to record next.

## Current Status

The current system works locally on Aaron's computer through a Candi/OpenClaw Telegram workflow.

The clean product repo is:

```text
https://github.com/rustwoodagent-ops/vox-cloud-alpha
```

The repo is private.

The repo currently packages:

- VOXAI acoustic backend
- Candi Phase 1 helper scripts
- required VOXAI knowledge files
- runtime folder layout
- PDF/reporting notes
- optional whole-song training-plan expansion spec
- early SaaS MVP notes

It intentionally excludes:

- raw user uploads
- generated temp WAV files
- generated backend outputs
- generated PDFs
- private singer progress logs
- Telegram file cache data
- local secrets

## Repository Layout

```text
.
|-- README.md
|-- HANDOFF.md
|-- backend/
|   |-- reference-downloader/
|   |   |-- app.py
|   |   |-- reference_dl.py
|   |   |-- requirements.txt
|   |   `-- README.md
|   `-- voxai-local-analysis/
|       |-- analyse_song.py
|       |-- install.sh
|       |-- requirements.txt
|       `-- tools/stems/batch_stems.sh
|-- docs/
|   |-- phase1-flow.md
|   |-- pdf-reporting.md
|   |-- saas-mvp.md
|   |-- training-plan-expansion.md
|   |-- voxai_analysis_redcliffe.md
|   `-- voxai_technical_implementation.md
|-- openclaw-data/
|   `-- vox-coach/
|       |-- knowledge/
|       |-- uploads/
|       |-- temp/
|       |-- memory/
|       |-- logs/
|       `-- reports/pdf/
`-- scripts/
    |-- candi_phase1.py
    |-- fetch_reference.py
    `-- verify_voxai_knowledge.py
```

## What It Does Today

The working Phase 1 flow is:

```text
Telegram/local recording
  -> save raw upload
  -> fetch the original song from YouTube for comparison (agent-run, no manual download)
  -> extract audio if the upload is video
  -> run VOXAI backend
  -> optionally separate stems first
  -> analyse isolated vocals
  -> write raw backend JSON
  -> write backend Markdown report
  -> normalise metrics for Candi
  -> read VOXAI knowledge files
  -> return a manifest for the Candi report
  -> Candi writes final analysis markdown
  -> save-report updates progress logs
```

The Candi report is not meant to be a cold technical dump. It should produce practical vocal-coaching feedback:

- quick summary
- singer / song / context
- performance readiness
- what is working
- main issues
- measured / directly heard
- inferred
- unverifiable
- technical breakdown
- one primary drill
- next recording target

## Hard Knowledge Gate

Before claiming VOXAI Advanced compliance or treating a take as a full Candi analysis, run:

```bash
python3 scripts/verify_voxai_knowledge.py
```

Required files:

```text
openclaw-data/vox-coach/knowledge/VOXAI_Knowledge_Core.txt
openclaw-data/vox-coach/knowledge/VOXAI_Scientific_Exercise_Library.txt
```

The verifier checks presence, readability, retrievability, bytes, hash, and sample heading.

The latest verification passed in this repo.

## Backend Pipeline

Backend script:

```text
backend/voxai-local-analysis/analyse_song.py
```

Typical command:

```bash
cd backend/voxai-local-analysis
python analyse_song.py input/my_song.wav --name "Singer Name" --separate-stems
```

The backend stages:

1. Optional stem separation
2. ffmpeg conversion to mono 44.1 kHz WAV
3. audio load with librosa/soundfile
4. pitch analysis
5. perturbation analysis
6. HNR/noise analysis
7. resonance/spectral analysis
8. dynamics analysis
9. rhythm/onset analysis
10. formant analysis
11. vibrato analysis
12. time diagnostics
13. visual diagnostic plot generation
14. diagnostic flags/archetype
15. raw JSON output
16. backend Markdown report output

Outputs:

```text
backend/voxai-local-analysis/output/<file>_analysis.json
backend/voxai-local-analysis/reports/<file>_report.md
backend/voxai-local-analysis/reports/diagnostics/<file>_diagnostic_plot.png
```

Those outputs are generated artifacts and are ignored by Git.

## Stem Separation

Stem helper:

```text
backend/voxai-local-analysis/tools/stems/batch_stems.sh
```

Default model:

```text
UVR-MDX-NET-Inst_HQ_3.onnx
```

Default stem venv:

```text
~/.venvs/vox-sep-uvr
```

The helper:

1. checks for Python and ffmpeg
2. creates the stem-separation venv if missing
3. installs `audio-separator` and `onnxruntime`
4. runs `audio-separator` with the UVR MDX model
5. writes separated files into the requested output folder

When `analyse_song.py` runs with `--separate-stems`, it:

1. creates a dated output folder under `output/stems/`
2. calls `tools/stems/batch_stems.sh`
3. searches for a vocals stem using patterns such as:

```text
*_(Vocals)_*.flac
*_(Vocals)_*.wav
*.vocals.wav
*vocals*.wav
```

4. searches for instrumental/no-vocal stems using patterns such as:

```text
*_(Instrumental)_*.flac
*_(Instrumental)_*.wav
*.instrumental.wav
*no_vocals*.wav
```

5. analyses the vocals stem, not the full mix
6. stores stem metadata in the backend JSON/report

This matters because karaoke/live-room recordings often contain backing track bleed. Isolating the vocal improves pitch and tone analysis, but the report must still treat metrics as supporting evidence where capture quality is uncertain.

## New Diagnostics Added

The uncommitted local backend changes were carried into this repo.

They add:

- `analyse_time_diagnostics`
- `generate_visual_diagnostics`
- `time_diagnostics` in the backend JSON
- `visual_diagnostics` in the backend JSON
- visual-diagnostic metadata in the backend Markdown report

Visual plot panels:

- waveform amplitude
- pitch contour F0
- RMS energy in dB
- spectral centroid brightness

The diagnostics include capture/environment risk markers such as low voiced detection or near clipping. These should be presented as caution/supporting evidence, not medical proof.

## Candi Phase 1 Wrapper

Wrapper script:

```text
scripts/candi_phase1.py
```

Prepare command:

```bash
python3 scripts/candi_phase1.py prepare \
  --source-path "/absolute/path/to/upload.mp3" \
  --message "Analyse this. It is Aaron singing Beggin." \
  --singer "Aaron" \
  --song "Beggin" \
  --artist "Maneskin" \
  --fetch-reference
```

What `prepare` does:

1. copies the raw upload into `openclaw-data/vox-coach/uploads/raw/`
2. if singer or song is missing, creates a pending record
3. runs the knowledge gate
4. fetches the original song from YouTube when requested (see Reference Tracks below)
5. extracts audio for video uploads
6. runs the backend with `--separate-stems`
7. loads backend JSON
8. normalises metrics
9. writes normalised metrics JSON
10. builds a manifest with all paths Candi needs

## Reference Tracks (Original Song Comparison)

Standing instruction: when the user asks for an analysis and the song is
known, the agent fetches the original song itself for comparison. The
user should never have to download the original manually.

Default path — add `--fetch-reference` to `prepare` (as in the example
above). It searches YouTube for `<artist> <song> official audio`,
downloads the top match as MP3 320kbps into
`openclaw-data/vox-coach/uploads/reference/`, and adds a `reference`
block plus `paths.reference_track` to the manifest. Use
`--reference-query "..."` or `--reference-url "..."` when the default
search would be ambiguous, and `--reference-quality` to change the
bitrate.

Standalone fetch (outside a take analysis):

```bash
python3 scripts/fetch_reference.py "Maneskin Beggin official audio"
```

Prints a JSON manifest (`status`, `path`, `title`, `cached`, ...). A
video that is already in the reference library is reused
(`"cached": true`) instead of re-downloaded.

Rules:

- a failed reference fetch must never block the take analysis; the
  manifest reports `reference.status: "error"` and the analysis proceeds
- requires `yt-dlp` (`pip install -r backend/reference-downloader/requirements.txt`)
  and `ffmpeg`
- copyright care applies (see Important Product Rules): private
  comparison/analysis use only, and delete reference media when no
  longer needed
- there is also a human-facing web page (`backend/reference-downloader/app.py`,
  binds to 127.0.0.1:8765) that shares the same download engine

Save command:

```bash
python3 scripts/candi_phase1.py save-report \
  --manifest "/absolute/path/to/manifest.json" \
  --analysis-path "/absolute/path/to/analysis.md" \
  --summary "Short summary" \
  --primary-pillar "Pitch / Intonation" \
  --main-improvement "What improved" \
  --still-present "What still needs work" \
  --drill-name "Primary drill" \
  --next-take-target "Next recording target"
```

What `save-report` does:

1. confirms the manifest is ready
2. confirms the final analysis markdown exists
3. updates the singer progress log
4. updates the singer+song progress log
5. writes the runtime log

## Primary Drill Plus Optional Expansion

Original Candi design: one primary drill only.

Current product design: keep the main analysis focused on one primary drill, then offer an optional expansion:

```text
If you want the fuller version, I can also turn this into a five-drill whole-song training plan.
```

The expansion is only generated when the user asks.

Expansion spec:

```text
docs/training-plan-expansion.md
```

Expansion sections:

1. Whole-Song Diagnosis
2. Primary Drill Recap
3. Five Supporting Exercises
4. Seven-Day Practice Plan
5. Next Full-Song Recording Target

Default five supporting drill targets:

- pitch / intonation
- rhythm / timing
- intensity / shouting control
- tone / resonance
- phrase shape / performance delivery

Important: do not invent issues just to fill five categories. If a category is not relevant, choose another real secondary issue from the take.

## PDF And Report Layer

PDF/HTML is a secondary artifact, not the core Phase 1 flow.

Canonical analysis storage:

```text
openclaw-data/vox-coach/memory/analyses/
```

Generated PDF/HTML storage:

```text
openclaw-data/vox-coach/reports/pdf/
```

These files are ignored by Git because they may contain private singer data.

Target report pipeline:

```text
analysis markdown
  -> structured report data
  -> HTML template
  -> PDF renderer
  -> stored PDF artifact
```

Recommended implementation:

- Jinja2 for HTML templates
- Playwright/Chromium or WeasyPrint for rendering
- object storage later for generated PDFs

More detail:

```text
docs/pdf-reporting.md
```

## What Has Been Built So Far

Commit history:

```text
87759ed Initial VOX Cloud Alpha MVP package
3ba8dcc Add optional whole-song training plan expansion
```

Initial package included:

- backend code
- stem-separation helper
- Candi Phase 1 wrapper
- knowledge files
- clean runtime layout
- PDF/report docs
- SaaS MVP notes

Second commit added:

- optional whole-song training-plan contract
- five-drill expansion spec
- manifest metadata for the expansion
- save-report metadata for expansion offered/requested/path

## Current Limitations

This is not yet a public SaaS.

Current limitations:

- runs locally, not hosted
- no web upload UI yet
- no API server yet
- no background job queue yet
- no user accounts
- no database
- no billing
- no object storage
- no public onboarding
- no automated PDF generator
- no automated Candi LLM/report generation service in this repo
- privacy/security hardening not complete

## Next-Level Plan: Local Pipeline To Public SaaS

Build this in controlled stages.

### Stage 1: Server Audit

Before deploying to Aaron's web server, confirm whether it is a VPS or restricted shared hosting.

Run:

```bash
uname -a
df -h
free -h
python3 --version
ffmpeg -version
which pip
which git
```

Need:

- Python 3
- ffmpeg
- ability to install packages
- enough CPU for audio analysis
- enough disk for temp WAV/stem work

If the server only has 12 GB disk, use it for Alpha only. Keep uploads short-lived and store only reports/metrics long-term.

### Stage 2: Build Internal API

Add a small API service, likely FastAPI:

```text
POST /api/takes
GET /api/takes/{id}
GET /api/takes/{id}/report
```

`POST /api/takes` should accept:

- audio/video file
- singer name
- song name
- optional artist/reference context
- user/account identifier
- goal/context

It should create a job record and return a job/take ID.

### Stage 3: Add Background Worker

Do not process uploads inside the HTTP request.

Use a worker queue:

- Redis + RQ
- Redis + Celery
- Arq

Worker steps:

```text
fetch upload
  -> run candi_phase1.py prepare
  -> generate Candi report
  -> save report
  -> mark job complete
```

### Stage 4: Add Minimal Web UI

Build a password-protected private page first:

- upload file
- singer name
- song name
- optional notes/goal
- status page
- report page
- optional button: "Create whole-song training plan"

Avoid a large dashboard at first.

### Stage 5: Add Persistence

Start simple, then move to Postgres.

Tables/entities:

- users
- singers
- songs
- takes
- jobs
- metrics
- reports
- drills/training plans
- progress entries

Audio files should move to object storage later:

- S3
- Cloudflare R2
- Backblaze B2
- MinIO if self-hosting

### Stage 6: Add PDF Generator

Add a report renderer:

```text
Markdown/JSON -> HTML -> PDF
```

Keep the PDF secondary to the stored Markdown/JSON report.

### Stage 7: Public MVP Hardening

Before public users:

- auth
- HTTPS
- file size limits
- upload type validation
- malware/media sanity checks
- queue limits
- per-user storage quotas
- deletion/retention policy
- privacy policy
- terms of use
- medical disclaimer
- copyright/reference-track policy
- backup/restore
- monitoring/logging

### Stage 8: Billing

Only after the private Alpha works:

- free trial analyses
- pay-per-report
- monthly plan
- teacher/studio multi-singer plan

## Important Product Rules

- Candi must feel like a supportive vocal coach, not a cold metrics bot.
- Transformation matters more than validation.
- Do not fake metrics.
- Do not invent timestamps.
- Do not diagnose medical conditions.
- Separate measured/directly heard, inferred, and unverifiable claims.
- Main reply gives one primary drill.
- Whole-song plan gives up to five supporting drills only when requested.
- Reference-track comparison requires copyright care.
- Raw uploads and reference media should not be retained longer than needed unless the user has explicitly consented.

## Best First Task For The Coding Agent

Start with the smallest deployable private Alpha:

1. Add a FastAPI app.
2. Add `POST /api/takes`.
3. Save an uploaded file into the existing runtime layout.
4. Queue or run one local `prepare` job.
5. Return manifest/status JSON.
6. Add a minimal upload page.
7. Confirm one real take can be uploaded through the browser and produce the same Candi-ready manifest as the Telegram/local flow.

Do not start with payments, public signup, or a complex dashboard.
