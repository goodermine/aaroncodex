"""Separation stage: split a full mix into vocal + instrumental with Demucs.

Only used in Song mode. Requires the `separation` extra (demucs + torch).
Device is auto-picked: CUDA or Apple MPS when present, otherwise CPU — which
is the expected path on the AMD Ryzen dev machine (no ROCm for its iGPU).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def available() -> bool:
    try:
        import demucs.api  # noqa: F401

        return True
    except ImportError:
        return False


def _pick_device() -> str:
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def separate(path: str | Path, model: str = "htdemucs_ft") -> tuple[np.ndarray, np.ndarray, int]:
    """Return (vocal, instrumental, sample_rate), each (channels, samples)."""
    if not available():
        raise RuntimeError(
            "Song mode needs Demucs. Install with: pip install 'voxpolish[separation]' "
            "(or run in --mode voice for recordings that are already mostly voice)."
        )
    from demucs.api import Separator

    sep = Separator(model=model, device=_pick_device())
    _, stems = sep.separate_audio_file(str(path))
    vocal = stems["vocals"].numpy()
    others = [v.numpy() for k, v in stems.items() if k != "vocals"]
    instrumental = np.sum(others, axis=0)
    return vocal, instrumental, sep.samplerate
