"""Session storage for the editor UI.

Disaster-1 defenses live here: the original file is copied into the session
and never written; every write is atomic (temp + rename); every accepted
document change snapshots the previous version into history/.

Disaster-2 defenses too: the on-disk Edit Document is the single source of
truth, documents are validated by schema round-trip before acceptance, and
every write carries a revision number so stale updates are rejected.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import numpy as np

from .. import audio_io
from ..document import EditDocument
from ..pipeline import Settings, analyze
from ..stages import clean, render

PEAK_BUCKETS = 2400  # points per waveform; a few KB regardless of file size


def atomic_write_bytes(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


class Session:
    """One recording being edited: a folder, fully self-contained."""

    def __init__(self, root: Path):
        self.root = Path(root)

    # -------------------------------------------------------------- creation

    @classmethod
    def create(cls, source: Path, root: Path, settings: Settings | None = None) -> "Session":
        settings = settings or Settings.for_mode("voice")
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        (root / "history").mkdir(exist_ok=True)
        s = cls(root)

        # Disaster 1: the user's file is copied in, then never touched again.
        source_copy = root / f"source{Path(source).suffix.lower()}"
        if not source_copy.exists():
            shutil.copy2(source, source_copy)

        vocal, sr = audio_io.load(source_copy)
        vocal, denoise_info = clean.process(vocal, sr, settings.denoise_amount)
        # The post-clean vocal is what render consumes; persisting it makes
        # every re-render fast (no model re-run) and deterministic.
        audio_io.save(root / "work_vocal.wav", vocal, sr)

        doc = analyze(vocal, sr, settings)
        doc.denoise = denoise_info
        s._write_doc(doc, revision=1)
        s.render()
        return s

    @classmethod
    def is_session(cls, root: Path) -> bool:
        root = Path(root)
        return (root / "edit_document.json").exists() and (root / "work_vocal.wav").exists()

    # -------------------------------------------------------------- document

    def _doc_path(self) -> Path:
        return self.root / "edit_document.json"

    def _meta_path(self) -> Path:
        return self.root / "session.json"

    def revision(self) -> int:
        try:
            return json.loads(self._meta_path().read_text())["revision"]
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            return 1

    def _write_doc(self, doc: EditDocument, revision: int) -> None:
        atomic_write_text(self._doc_path(), doc.to_json())
        atomic_write_text(self._meta_path(), json.dumps({"revision": revision}))

    def document(self) -> EditDocument:
        return EditDocument.load(self._doc_path())

    def update_document(self, raw_json: str, expected_revision: int) -> int:
        """Validate + accept a new document. Returns the new revision.

        Raises ValueError on schema failure, ConflictError on stale revision.
        """
        current = self.revision()
        if expected_revision != current:
            raise ConflictError(f"stale revision {expected_revision}, current {current}")
        # Disaster 2: schema round-trip before anything is persisted.
        doc = EditDocument.from_json(raw_json)
        # Snapshot what we're replacing — undo by file, survives restarts.
        snap = self.root / "history" / f"doc-{current:04d}.json"
        shutil.copy2(self._doc_path(), snap)
        self._write_doc(doc, revision=current + 1)
        return current + 1

    # -------------------------------------------------------------- rendering

    def render(self) -> dict:
        """Render the persisted document (never an in-memory copy)."""
        vocal, sr = audio_io.load(self.root / "work_vocal.wav")
        doc = self.document()
        out = render.render(vocal, sr, doc)
        tmp = self.root / ".render-tmp.wav"
        audio_io.save(tmp, out, sr)
        os.replace(tmp, self.root / "vocal_cleaned.wav")
        return {"rendered": True, "revision": self.revision()}

    # ------------------------------------------------------------------ peaks

    def peaks(self, name: str) -> dict:
        """Downsampled min/max waveform peaks — small no matter the file size."""
        path = self._audio_path(name)
        cache = self.root / f".peaks-{name}.json"
        if cache.exists() and cache.stat().st_mtime >= path.stat().st_mtime:
            return json.loads(cache.read_text())
        audio, sr = audio_io.load(path)
        mono = np.asarray(audio_io.to_mono(audio), dtype=np.float64)
        n = len(mono)
        bucket = max(1, -(-n // PEAK_BUCKETS))  # ceil division: count <= PEAK_BUCKETS
        usable = (n // bucket) * bucket
        chunks = mono[:usable].reshape(-1, bucket)
        data = {
            "sample_rate": sr,
            "duration": n / sr,
            "min": np.round(chunks.min(axis=1), 4).tolist(),
            "max": np.round(chunks.max(axis=1), 4).tolist(),
        }
        atomic_write_text(cache, json.dumps(data))
        return data

    def _audio_path(self, name: str) -> Path:
        allowed = {
            "original": "work_vocal.wav",
            "cleaned": "vocal_cleaned.wav",
        }
        if name not in allowed:
            raise KeyError(name)
        return self.root / allowed[name]


class ConflictError(Exception):
    pass
