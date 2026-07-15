# Handoff for Howard (local machine agent)

From: Claude (remote coding agent) / Aaron
Date: 2026-07-11

A reference-song downloader was merged into `main` (PR #2). It lets you
fetch the original song from YouTube automatically whenever Aaron asks
for a take analysis — Aaron should never have to download originals
manually again.

## One-time setup on this machine

```bash
git pull origin main
pip install -r backend/reference-downloader/requirements.txt
ffmpeg -version   # already installed for the VOXAI backend; just confirm
```

Sanity check (should print JSON with "status": "ready" and a "path"):

```bash
python3 scripts/fetch_reference.py "Maneskin Beggin official audio"
```

## New standing behaviour

When Aaron sends a take and the song is known, fetch the original
yourself as part of `prepare`:

```bash
python3 scripts/candi_phase1.py prepare \
  --source-path "/path/to/take.mp3" \
  --message "Analyse this. It is Aaron singing Beggin." \
  --singer "Aaron" --song "Beggin" --artist "Maneskin" \
  --fetch-reference
```

- `--fetch-reference` searches YouTube for `<artist> <song> official audio`
  and downloads MP3 320kbps into `openclaw-data/vox-coach/uploads/reference/`.
- The manifest gains a `reference` block and `paths.reference_track` —
  use that file for take-vs-original comparison in the Candi report.
- Use `--reference-query "..."` or `--reference-url "..."` if the default
  search would be ambiguous (covers, remixes, live versions).
- Already-fetched songs are reused from the library (`"cached": true`),
  so repeat takes of the same song cost nothing.
- A failed fetch never blocks the take analysis; the manifest reports
  `reference.status: "error"` and you proceed as before.

For a one-off fetch outside an analysis, use
`scripts/fetch_reference.py` directly (it prints a JSON manifest).

Full details: the "Reference Tracks" section in `HANDOFF.md` and
`backend/reference-downloader/README.md`.

## Rules (unchanged, but they apply here)

- Copyright care: reference downloads are for private comparison and
  analysis only. Delete reference media when it is no longer needed.
- Do not commit anything in `uploads/reference/` (it is git-ignored).
