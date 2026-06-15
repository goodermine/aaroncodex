# VOX Cloud Alpha SaaS MVP

The SaaS MVP should prove the working local pipeline can run from a browser upload.

## First Private Build

Build only:

- private upload page
- singer name field
- song name field
- recording upload
- status page
- final Candi report page
- stored metrics/report files

Avoid at first:

- public launch
- payment system
- social features
- big dashboard
- old VOX history migration
- PDF as the primary flow

## Service Shape

```text
Frontend
  upload page
  report page

API
  POST /api/takes
  GET /api/takes/{id}
  GET /api/takes/{id}/report

Worker
  extracts audio
  runs analyse_song.py
  normalises metrics
  saves manifest
  prepares Candi report

Storage
  Postgres later for users/singers/songs/takes
  local disk for alpha
  object storage later for uploads and PDFs
```

## Server Suitability Check

Before deployment, run:

```bash
uname -a
df -h
free -h
python3 --version
ffmpeg -version
which pip
which git
```

A VPS is suitable for Alpha if it supports Python, ffmpeg, dependency installation, and enough CPU for audio processing.

Shared hosting may not be suitable because VOX needs background jobs and media processing.

## Alpha Storage Rule

For a 12 GB server:

- keep raw uploads only while processing
- keep metrics, manifests, and final reports
- delete temp WAVs and reference media after use
- move raw audio/PDF archives to object storage later

## Commercial MVP Offer

Upload a singing take and receive a coach-level vocal report with measured pitch, tone, dynamics, one practical drill, and the next recording target.
