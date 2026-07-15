"""Workspace: many sessions under one base directory, plus upload jobs.

The editor talks to whichever session is "current". The CLI opens a specific
file as the current session; the web upload flow creates new sessions and
switches current to them. Uploads run as background jobs with progress so the
browser stays responsive and every failure is surfaced, never swallowed.
"""

from __future__ import annotations

import re
import secrets
import threading
from pathlib import Path

from ..pipeline import Settings
from .session import Session, atomic_write_bytes

# Formats we accept for upload. Extension-validated up front; the actual
# decode (and its errors) happen in Session.create via audio_io.
ALLOWED_EXT = {".wav", ".mp3", ".m4a", ".flac", ".aif", ".aiff", ".ogg"}
SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


def safe_stem(name: str) -> str:
    """A filesystem-safe slug from a user filename (never a path)."""
    stem = Path(name).stem
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-.") or "audio"
    return slug[:48]


class UploadJob:
    def __init__(self, job_id: str, filename: str, tune: bool):
        self.id = job_id
        self.filename = filename
        self.tune = tune
        self.status = "queued"      # queued | running | done | error
        self.stage = "queued"       # decoding | cleaning | analyzing | rendering | done
        self.error: str | None = None
        self.session_id: str | None = None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "tune": self.tune,
            "status": self.status,
            "stage": self.stage,
            "error": self.error,
            "session_id": self.session_id,
        }


class Workspace:
    def __init__(self, base: Path, current_id: str | None = None):
        self.base = Path(base)
        self.base.mkdir(parents=True, exist_ok=True)
        self.current_id = current_id
        self._jobs: dict[str, UploadJob] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ sessions

    def _session_dir(self, session_id: str) -> Path:
        if not SAFE_ID.match(session_id or "") or session_id in (".", ".."):
            raise KeyError(f"invalid session id {session_id!r}")
        # Resolve and confine to base — defense in depth against traversal.
        path = (self.base / session_id).resolve()
        if path.parent != self.base.resolve():
            raise KeyError(f"session id escapes workspace: {session_id!r}")
        return path

    def get(self, session_id: str) -> Session | None:
        try:
            path = self._session_dir(session_id)
        except KeyError:
            return None
        return Session(path) if Session.is_session(path) else None

    def current(self) -> Session | None:
        return self.get(self.current_id) if self.current_id else None

    def register(self, session_dir: Path) -> str:
        """Adopt an existing on-disk session (e.g. from the CLI) by folder name."""
        session_dir = Path(session_dir)
        self.current_id = session_dir.name
        return self.current_id

    def list(self) -> list[dict]:
        out = []
        for child in sorted(self.base.iterdir()):
            if child.is_dir() and Session.is_session(child):
                out.append({"id": child.name})
        return out

    # ------------------------------------------------------------- uploads

    def start_upload(self, filename: str, data: bytes, tune: bool) -> UploadJob:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            raise ValueError(
                f"unsupported format '{ext or '?'}' — use WAV, MP3, M4A, or FLAC"
            )
        if not data:
            raise ValueError("empty upload")

        job_id = "job-" + secrets.token_hex(6)
        session_id = f"{safe_stem(filename)}-{secrets.token_hex(4)}"
        job = UploadJob(job_id, filename, tune)
        with self._lock:
            self._jobs[job_id] = job

        # Stash the bytes in the session folder before processing, safely named.
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        upload_path = session_dir / f"upload{ext}"
        atomic_write_bytes(upload_path, data)

        def work():
            job.status = "running"
            try:
                def progress(stage: str) -> None:
                    job.stage = stage

                Session.create(
                    upload_path, session_dir,
                    settings=Settings.for_mode("voice"),
                    tune=tune, progress=progress, display_name=filename,
                )
                job.session_id = session_id
                self.current_id = session_id
                job.status = "done"
                job.stage = "done"
            except Exception as e:  # decode/model/render errors reach the UI
                job.status = "error"
                job.error = str(e)

        threading.Thread(target=work, daemon=True).start()
        return job

    def job(self, job_id: str) -> UploadJob | None:
        return self._jobs.get(job_id)
