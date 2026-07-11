# VOX Cloud Alpha

Private MVP repository for turning the working local VOXAI/Candi vocal analysis flow into a small service.

Start here for agent-to-agent context:

- `HANDOFF.md`

This repo packages the clean pieces of the current working pipeline:

- VOXAI acoustic backend in `backend/voxai-local-analysis`
- Candi Phase 1 intake/report helpers in `scripts/`
- reference-song downloader (agent CLI + web page) in `backend/reference-downloader`
- required VOXAI knowledge files in `openclaw-data/vox-coach/knowledge/`
- runtime folders for uploads, metrics, reports, and progress logs
- notes for the PDF/report workflow and SaaS MVP path in `docs/`

Generated files, private singer progress logs, uploads, temporary WAVs, Telegram caches, and PDFs are intentionally ignored.

## Current MVP Flow

```text
recording upload
  -> save raw file
  -> fetch original song from YouTube for comparison (agent-run)
  -> extract audio when needed
  -> run backend analyse_song.py
  -> normalise metrics
  -> retrieve VOXAI knowledge
  -> compose Candi analysis
  -> offer optional whole-song training plan
  -> save analysis markdown
  -> update singer and song progress logs
```

## Quick Local Check

```bash
python3 scripts/verify_voxai_knowledge.py
```

Expected result: `advanced_compliant: true`.

## Backend Setup

```bash
cd backend/voxai-local-analysis
chmod +x install.sh
./install.sh
```

Or manually:

```bash
cd backend/voxai-local-analysis
python3 -m venv voxai_env
source voxai_env/bin/activate
pip install -r requirements.txt
```

System dependency required:

```bash
sudo apt install ffmpeg
```

## Run A Phase 1 Take

```bash
python3 scripts/candi_phase1.py prepare \
  --source-path "/absolute/path/to/recording.mp3" \
  --message "Analyse this. It is Aaron singing Beggin." \
  --singer "Aaron" \
  --song "Beggin" \
  --artist "Maneskin" \
  --fetch-reference
```

`--fetch-reference` makes the agent download the original song from
YouTube automatically (searching `<artist> <song> official audio`) so it
is available for comparison — no manual download step. The manifest then
includes `paths.reference_track`. See `backend/reference-downloader/README.md`.

After composing the Candi analysis markdown, save it to the `analysis_record` path in the returned manifest, then run:

```bash
python3 scripts/candi_phase1.py save-report \
  --manifest "/absolute/path/to/manifest.json" \
  --analysis-path "/absolute/path/to/analysis.md" \
  --summary "Short summary of the take." \
  --primary-pillar "Pitch / Intonation" \
  --main-improvement "Chorus landed more cleanly than the previous attempt." \
  --still-present "Verse timing still rushes under intensity." \
  --drill-name "Straw Phonation in Water" \
  --next-take-target "Record the chorus only at 80 percent volume with the vowel narrowed before the high note." \
  --expansion-offered true
```

The standard Candi reply stays focused on one primary drill. If the user asks for a fuller plan, generate the optional five-drill whole-song expansion described in `docs/training-plan-expansion.md`.

## Runtime Override

By default, Candi uses:

```text
backend/voxai-local-analysis
```

To point at another backend:

```bash
export VOXAI_BACKEND_DIR=/absolute/path/to/voxai-local-analysis
```

## SaaS Direction

The first service version should be private and small:

- password-protected upload page
- `POST /api/takes`
- background worker for audio analysis
- stored report page
- singer/song/take records
- later: accounts, billing, object storage, and public onboarding

See `docs/saas-mvp.md`.
