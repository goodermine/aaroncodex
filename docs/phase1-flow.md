# Candi Phase 1 Flow

Phase 1 exists to make the next singing take better, using the current local VOXAI backend and the Candi coaching wrapper.

## Intake

1. Receive a Telegram media file or local media path.
2. Run `python3 scripts/verify_voxai_knowledge.py`.
3. Save the raw upload under `openclaw-data/vox-coach/uploads/raw/`.
4. If singer or song is unknown, create a pending record and ask:

```text
I can analyse this properly - who is singing, and what song is it?
```

5. If singer and song are known, extract audio when the upload is video.
6. Run `backend/voxai-local-analysis/analyse_song.py`.
7. Normalise backend metrics into `openclaw-data/vox-coach/temp/metric-json/`.
8. Return a manifest for Candi to compose from.

## Required Candi Reply Sections

- Quick Summary
- Singer / Song / Context
- Performance Readiness
- What Is Working
- Main Issues
- Measured / Directly Heard
- Inferred
- Unverifiable
- Technical Breakdown
- One Primary Drill
- Next Recording Target

## Save Step

After the final Candi analysis is written to the manifest `analysis_record` path, run `save-report`.

That updates:

- main singer progress log
- singer plus song progress log
- runtime log

## Guardrails

- no fake metrics
- no invented timestamps
- no medical diagnosis
- separate measured, inferred, and unverifiable claims
- one primary drill unless a safety exception requires otherwise
- generated audio, raw uploads, temp files, logs, and progress history stay out of Git
