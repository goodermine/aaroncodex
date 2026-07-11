"""Shared download logic for VOX reference tracks.

Used by both the web page (app.py) and the agent-facing CLI
(scripts/fetch_reference.py). Accepts either a YouTube URL or a free-text
search query ("Maneskin Beggin official audio") and downloads the top
match into the reference library:

    openclaw-data/vox-coach/uploads/reference/

Requires yt-dlp and ffmpeg.
"""

from __future__ import annotations

import shutil
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = REPO_ROOT / "openclaw-data" / "vox-coach" / "uploads" / "reference"

MP3_BITRATES = ["320", "256", "192", "128", "64"]
MP4_HEIGHTS = [1080, 720, 480, 360]

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

# yt-dlp + ffmpeg post-processing is CPU/IO heavy; serialise downloads so
# concurrent requests don't fetch the same video twice.
_download_lock = threading.Lock()


class ReferenceError(RuntimeError):
    """A download/lookup failed in a way the caller should report."""


def is_url(text: str) -> bool:
    return urlparse(text.strip()).scheme in ("http", "https")


def is_youtube_url(text: str) -> bool:
    return urlparse(text.strip()).hostname in ALLOWED_HOSTS


def _resolve_target(target: str) -> str:
    """Turn user input into something yt-dlp can fetch.

    URLs must be YouTube; anything else is treated as a search query and
    resolved to the top YouTube result.
    """
    target = target.strip()
    if not target:
        raise ReferenceError("Empty song name / link.")
    if is_url(target):
        if not is_youtube_url(target):
            raise ReferenceError("Only YouTube links are supported.")
        return target
    return f"ytsearch1:{target}"


def _first_entry(meta: dict) -> dict:
    """Unwrap a search-result playlist down to the single video entry."""
    while meta.get("_type") in ("playlist", "multi_video"):
        entries = meta.get("entries") or []
        if not entries:
            raise ReferenceError("No YouTube results for that search.")
        meta = entries[0]
    return meta


def _summary(meta: dict) -> dict:
    duration = int(meta.get("duration") or 0)
    return {
        "id": meta.get("id"),
        "title": meta.get("title"),
        "uploader": meta.get("uploader"),
        "duration_seconds": duration,
        "duration": f"{duration // 60}:{duration % 60:02d}" if duration else "",
        "thumbnail": meta.get("thumbnail"),
        "webpage_url": meta.get("webpage_url") or meta.get("url"),
    }


def fetch_info(target: str) -> dict:
    """Metadata for a URL or search query, without downloading."""
    resolved = _resolve_target(target)
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            meta = _first_entry(ydl.extract_info(resolved, download=False))
    except yt_dlp.utils.DownloadError as exc:
        raise ReferenceError(f"Could not read that link/search: {exc}") from exc

    heights = sorted(
        {
            f.get("height")
            for f in meta.get("formats", [])
            if f.get("height") and f.get("vcodec") not in (None, "none")
        },
        reverse=True,
    )
    info = _summary(meta)
    info["mp3_bitrates"] = MP3_BITRATES
    info["mp4_heights"] = [h for h in MP4_HEIGHTS if heights and h <= heights[0]] or [360]
    return info


def _find_cached(video_id: str, ext: str) -> Path | None:
    if not video_id or not REFERENCE_DIR.exists():
        return None
    marker = f"[{video_id}]"
    for p in REFERENCE_DIR.iterdir():
        if p.is_file() and marker in p.name and p.suffix == f".{ext}":
            return p
    return None


def download_reference(
    target: str,
    fmt: str = "mp3",
    quality: str = "320",
    reuse_cached: bool = True,
) -> dict:
    """Download a reference track and return a small manifest dict.

    target: YouTube URL or free-text search query.
    fmt: "mp3" (for analysis) or "mp4".
    quality: bitrate for mp3 (320/256/192/128/64), height for mp4.
    """
    if fmt not in ("mp3", "mp4"):
        raise ReferenceError("Format must be mp3 or mp4.")
    if fmt == "mp3" and quality not in MP3_BITRATES:
        raise ReferenceError(f"MP3 bitrate must be one of {MP3_BITRATES}.")
    if fmt == "mp4" and (not quality.isdigit() or int(quality) not in MP4_HEIGHTS):
        raise ReferenceError(f"MP4 quality must be one of {MP4_HEIGHTS}.")
    if shutil.which("ffmpeg") is None:
        raise ReferenceError(
            "ffmpeg not found on PATH - install it (the VOXAI backend needs it too)."
        )

    resolved = _resolve_target(target)
    info_opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            meta = _first_entry(ydl.extract_info(resolved, download=False))
    except yt_dlp.utils.DownloadError as exc:
        raise ReferenceError(f"Could not read that link/search: {exc}") from exc

    result = _summary(meta)
    result.update({"format": fmt, "quality": quality, "cached": False})

    if reuse_cached:
        cached = _find_cached(result["id"], fmt)
        if cached is not None:
            result.update({"path": str(cached), "cached": True})
            return result

    video_url = result["webpage_url"]
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    # Download into a fresh temp dir first so the finished file is easy to
    # find regardless of what yt-dlp names it, then move it to the library.
    with _download_lock, tempfile.TemporaryDirectory(dir=REFERENCE_DIR) as tmp:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": True,
            "restrictfilenames": True,
            "outtmpl": str(Path(tmp) / "%(title).120s [%(id)s].%(ext)s"),
        }
        if fmt == "mp3":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }
            ]
        else:
            h = int(quality)
            opts["format"] = (
                f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
                f"/best[height<={h}][ext=mp4]/best[height<={h}]/best"
            )
            opts["merge_output_format"] = "mp4"

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(video_url, download=True)
        except yt_dlp.utils.DownloadError as exc:
            raise ReferenceError(f"Download failed: {exc}") from exc

        files = [p for p in Path(tmp).iterdir() if p.is_file()]
        if not files:
            raise ReferenceError("Download produced no file.")
        produced = max(files, key=lambda p: p.stat().st_size)

        final = REFERENCE_DIR / produced.name
        if final.exists():
            final = REFERENCE_DIR / f"{produced.stem}_{quality}{produced.suffix}"
        shutil.move(str(produced), final)

    result["path"] = str(final)
    return result


def list_library() -> dict:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    entries = sorted(
        (p for p in REFERENCE_DIR.iterdir() if p.is_file() and p.name != ".gitkeep"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return {
        "dir": str(REFERENCE_DIR),
        "files": [
            {"name": p.name, "size_mb": round(p.stat().st_size / 1048576, 1)}
            for p in entries
        ],
    }
