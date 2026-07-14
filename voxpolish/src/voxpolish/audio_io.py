"""Audio loading/saving. soundfile first, ffmpeg CLI as decode fallback."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


def load(path: str | Path) -> tuple[np.ndarray, int]:
    """Load audio as float32 with shape (channels, samples)."""
    path = Path(path)
    try:
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
        return data.T.copy(), sr
    except Exception:
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                f"Could not decode {path.name} with libsndfile and ffmpeg is not "
                "installed. Install ffmpeg (macOS: `brew install ffmpeg`) or "
                "convert the file to WAV/FLAC first."
            )
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "decoded.wav"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(path), "-acodec", "pcm_f32le", str(tmp)],
            check=True,
        )
        data, sr = sf.read(str(tmp), dtype="float32", always_2d=True)
        return data.T.copy(), sr


def save(path: str | Path, audio: np.ndarray, sr: int) -> None:
    """Save (channels, samples) float32 audio as 24-bit WAV."""
    audio = np.atleast_2d(audio)
    sf.write(str(path), audio.T, sr, subtype="PCM_24")


def to_mono(audio: np.ndarray) -> np.ndarray:
    """Downmix (channels, samples) to a mono analysis signal."""
    return np.atleast_2d(audio).mean(axis=0)
