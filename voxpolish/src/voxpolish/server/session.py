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
from ..stages import clean, pitch, render

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
    def create(
        cls,
        source: Path,
        root: Path,
        settings: Settings | None = None,
        tune: bool = True,
        progress=None,
        display_name: str | None = None,
    ) -> "Session":
        """Analyze a recording into a new session folder.

        tune: enable the Tune module for this session (default on, per the
        July 15 decision record). progress: optional callback(stage_str) for
        the upload UI. display_name: friendly source name for downloads.
        """
        def step(stage: str) -> None:
            if progress is not None:
                progress(stage)

        settings = settings or Settings.for_mode("voice")
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        (root / "history").mkdir(exist_ok=True)
        s = cls(root)
        s._write_meta(name=Path(display_name or source).stem)

        # Disaster 1: the user's file is copied in, then never touched again.
        step("decoding")
        source_copy = root / f"source{Path(source).suffix.lower()}"
        if not source_copy.exists():
            shutil.copy2(source, source_copy)

        vocal, sr = audio_io.load(source_copy)
        step("cleaning")
        raw_vocal = vocal
        vocal, wet_vocal, denoise_info = clean.process_split(vocal, sr, settings.denoise_amount)
        # The post-clean vocal is what render consumes; persisting it makes
        # every re-render fast (no model re-run) and deterministic.
        audio_io.save(root / "work_vocal.wav", vocal, sr)
        # Persist the raw + fully-wet pair so render() can re-blend the Clean
        # module to whatever amount the editor asks for — without these the
        # slider was decorative (denoise baked in once here, never re-read).
        if wet_vocal is not None:
            audio_io.save(root / "raw_vocal.wav", raw_vocal, sr)
            audio_io.save(root / "wet_vocal.wav", wet_vocal, sr)

        step("analyzing")
        doc = analyze(vocal, sr, settings)
        doc.denoise = denoise_info
        # Tuner analysis: key, notes, and the proposed correction curve. A
        # failure here must never kill session creation — record and move on.
        try:
            rep = pitch.analyze(audio_io.to_mono(vocal), sr)
            doc.pitch = {
                "key": rep["key"],
                "key_confidence": rep["key_confidence"],
                "mean_abs_dev_cents": rep["mean_abs_dev_cents"],
                "notes": rep["notes"],
                "track": rep["track"],
                "curve": rep["curve"],
                "settings": rep["settings"],
            }
        except Exception as e:
            doc.pitch = {"error": str(e)}
        # Clean vs Clean + Auto Tune: bypass the Tune module unless requested.
        doc.bypass = {**doc.bypass, "tune": not tune}
        # Start Auto Tune gentle (10%): field default so first renders are
        # subtle; the editor slider takes it up from there.
        doc.amounts = {**doc.amounts, "tune": 0.1}
        s._write_doc(doc, revision=1)
        step("rendering")
        s.render()
        step("done")
        return s

    @classmethod
    def is_session(cls, root: Path) -> bool:
        root = Path(root)
        return (root / "edit_document.json").exists() and (root / "work_vocal.wav").exists()

    def denoise_adjustable(self) -> bool:
        """True when render() can re-blend the Clean module (raw+wet persisted).
        False for legacy sessions and no-backend environments, where the editor
        must present Clean as fixed instead of a slider that does nothing."""
        return (self.root / "raw_vocal.wav").exists() and (self.root / "wet_vocal.wav").exists()

    # -------------------------------------------------------------- document

    def _doc_path(self) -> Path:
        return self.root / "edit_document.json"

    def _meta_path(self) -> Path:
        return self.root / "session.json"

    def _read_meta(self) -> dict:
        try:
            return json.loads(self._meta_path().read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_meta(self, **updates) -> None:
        meta = self._read_meta()
        meta.update(updates)
        atomic_write_text(self._meta_path(), json.dumps(meta))

    def revision(self) -> int:
        return int(self._read_meta().get("revision", 1))

    def name(self) -> str:
        return self._read_meta().get("name") or self.root.name

    def download_name(self) -> str:
        return f"{self.name()}_voxpolish.wav"

    def _write_doc(self, doc: EditDocument, revision: int) -> None:
        atomic_write_text(self._doc_path(), doc.to_json())
        self._write_meta(revision=revision)

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
        # Clean module: re-blend raw/wet to the document's amount. Sessions
        # created before the split (or without a denoise backend) have no
        # raw/wet pair and keep the create-time bake.
        raw_path, wet_path = self.root / "raw_vocal.wav", self.root / "wet_vocal.wav"
        if raw_path.exists() and wet_path.exists():
            amount = float(((doc.denoise or {}).get("amount")) or 0.0)
            raw, _ = audio_io.load(raw_path)
            if amount <= 0.0:
                vocal = raw
            else:
                wet, _ = audio_io.load(wet_path)
                vocal = clean.blend(raw, wet, amount)
        out = render.render(vocal, sr, doc)
        notes: list[str] = []

        # Tuner layer: scale the correction curve by the Tune amount, honor
        # the bypass, degrade gracefully if the vocoder isn't installed.
        tune_amt = float((doc.amounts or {}).get("tune", 1.0))
        curve = (doc.pitch or {}).get("curve") or []
        if curve and tune_amt > 0 and not (doc.bypass or {}).get("tune"):
            scaled = [[t, c * tune_amt] for t, c in curve]
            try:
                out, applied = pitch.apply_correction(out, sr, scaled)
                if applied.get("applied"):
                    notes.append(f"tuned (max {applied['max_applied_cents']} cents)")
            except RuntimeError as e:
                notes.append(f"tuner skipped: {e}")

        tmp = self.root / ".render-tmp.wav"
        audio_io.save(tmp, out, sr)
        os.replace(tmp, self.root / "vocal_cleaned.wav")
        return {"rendered": True, "revision": self.revision(), "notes": notes}

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
