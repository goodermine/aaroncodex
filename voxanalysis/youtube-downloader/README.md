# VOX Reference Downloader

Tools for grabbing original/reference songs from YouTube so they can be
compared against a singer's take in the VOXAI pipeline. Two front doors,
one shared engine (`reference_dl.py`):

1. **Agent CLI** (`fetch_reference.py`) — what Candi/the agent
   runs so the user never downloads anything manually.
2. **Web page** (`app.py`) — a yt5s-style page for humans: paste a link
   or type a song name, press **Start**, switch between **MP3** and
   **MP4**, and hit a download button.

Every download is served to your browser **and** kept in the reference
library so the analysis pipeline can reach it:

```text
openclaw-data/vox-coach/uploads/reference/
```

## Setup

```bash
cd youtube-downloader
pip install -r requirements.txt
python3 app.py
```

Then open <http://127.0.0.1:8765>.

Requires `ffmpeg` on PATH (the VOXAI backend already needs it).

Optional: newer yt-dlp versions warn that a JavaScript runtime (e.g.
[deno](https://deno.com)) improves YouTube format availability. Downloads
work without it, but installing deno silences the warning and can unlock
higher-quality formats.

## Formats

- **MP3**: 320 / 256 / 192 / 128 / 64 kbps (best audio, re-encoded with ffmpeg)
- **MP4**: up to 1080p / 720p / 480p / 360p (capped at what the video offers)

For VOXAI comparison work, MP3 320kbps is the sensible default — the
analysis backend converts everything to mono 44.1 kHz WAV anyway.

## Endpoints

| Endpoint        | Purpose                                        |
| --------------- | ---------------------------------------------- |
| `GET /`         | The downloader page                            |
| `GET /api/info` | Video metadata + available qualities (`?url=`) |
| `GET /api/download` | Fetch a file (`?url=&fmt=mp3|mp4&quality=`) |
| `GET /api/library`  | List files currently in the reference library |

## Agent workflow (no manual download step)

The agent fetches the original song itself — by search query, no URL
needed:

```bash
python3 youtube-downloader/fetch_reference.py "Maneskin Beggin official audio"
```

Prints a JSON manifest with the downloaded file's path (`"status":
"ready"`, `"path": ...`). If the same video was fetched before, the
library copy is reused (`"cached": true`). `--info-only` resolves
metadata without downloading; `--fmt mp4` and `--quality` are available
too.

Or in one step during take analysis — `candi_phase1.py prepare` can fetch
the original alongside the singer's take:

```bash
python3 scripts/candi_phase1.py prepare \
  --source-path "/path/to/aaron-take.mp3" \
  --message "Analyse this. It is Aaron singing Beggin." \
  --singer "Aaron" --song "Beggin" --artist "Maneskin" \
  --fetch-reference
```

`--fetch-reference` searches YouTube for `<artist> <song> official audio`;
use `--reference-query "..."` or `--reference-url "..."` to override the
search. The manifest then contains a `reference` block and
`paths.reference_track`, so Candi can compare the take against the
original. A failed reference fetch never blocks the take analysis — the
manifest just reports `reference.status: "error"`.

## Copyright care

Reference-track comparison requires copyright care. Use downloads for private comparison/analysis only, keep
this tool bound to `127.0.0.1` (the default), and delete reference media
when it is no longer needed. Downloading YouTube content is subject to
YouTube's Terms of Service and the rights of the content owners.

The `uploads/reference/` folder is git-ignored so reference media is never
committed.
