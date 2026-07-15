#!/usr/bin/env python3
"""Fetch an original/reference song from YouTube for VOXAI comparison.

Agent-facing one-shot CLI: give it a song name (search) or a YouTube URL
and it downloads the top match into the reference library, printing a
JSON manifest on stdout so the calling agent can pick up the file path.

Examples:

    python3 youtube-downloader/fetch_reference.py "Maneskin Beggin official audio"
    python3 youtube-downloader/fetch_reference.py "https://www.youtube.com/watch?v=..." --quality 192
    python3 youtube-downloader/fetch_reference.py "Adele Hello" --info-only

Output (stdout, JSON):

    {
      "status": "ready",
      "path": ".../openclaw-data/vox-coach/uploads/reference/<file>.mp3",
      "title": "...", "uploader": "...", "duration": "3:33",
      "webpage_url": "...", "cached": false, ...
    }

or {"status": "error", "error": "..."} with exit code 1.

If the same video was fetched before, the library copy is reused
("cached": true) instead of downloading again.

Requires yt-dlp and ffmpeg (pip install -r
youtube-downloader/requirements.txt).

Copyright care per HANDOFF.md: private comparison/analysis use only;
delete reference media when no longer needed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import reference_dl as rd
except ImportError:
    print(
        json.dumps(
            {
                "status": "error",
                "error": (
                    "yt-dlp is not installed. Run: "
                    "pip install -r youtube-downloader/requirements.txt"
                ),
            }
        )
    )
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download a reference song from YouTube for VOXAI comparison."
    )
    parser.add_argument("target", help="Song name to search for, or a YouTube URL.")
    parser.add_argument("--fmt", choices=["mp3", "mp4"], default="mp3")
    parser.add_argument(
        "--quality",
        default="320",
        help="MP3 bitrate (320/256/192/128/64) or MP4 height (1080/720/480/360). Default 320.",
    )
    parser.add_argument(
        "--info-only",
        action="store_true",
        help="Only resolve and print metadata; do not download.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Re-download even if the video is already in the reference library.",
    )
    args = parser.parse_args()

    try:
        if args.info_only:
            result = rd.fetch_info(args.target)
        else:
            result = rd.download_reference(
                args.target,
                fmt=args.fmt,
                quality=args.quality,
                reuse_cached=not args.no_cache,
            )
        result["status"] = "ready"
        print(json.dumps(result, indent=2))
        return 0
    except rd.ReferenceError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
