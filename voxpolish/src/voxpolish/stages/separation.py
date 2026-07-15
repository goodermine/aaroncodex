"""Separation stage: split a full mix into vocal + instrumental.

Backend: the MIT-licensed KimberleyJSN Mel-Band RoFormer, run via
`audio-separator` (MIT). This replaces Demucs, whose pretrained weights are
CC-BY-NC (non-commercial) and cannot ship in a paid product. See
docs/separation-model-swap-plan.md and docs/dependency-license-audit.md §2.

Contract (unchanged): separate(path) -> (vocal, instrumental, sr), numpy
arrays shaped (channels, samples). The instrumental is derived as
`mix - vocal`, which guarantees `vocal + instrumental == mix` — the remix and
the instrumental-referenced bleed suppressor both rely on that.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from .. import audio_io

# Disaster-1 guard: ONE pinned, MIT-licensed model. Never silently substitute.
# huggingface.co/KimberleyJSN/melbandroformer (License: MIT). Recorded in
# docs/models/separation-model.md.
SEPARATION_MODEL = "vocals_mel_band_roformer.ckpt"


def available() -> bool:
    try:
        import audio_separator.separator  # noqa: F401

        return True
    except ImportError:
        return False


def _run_separator(path: str | Path, model: str, out_dir: Path) -> Path:
    """Run audio-separator; return the path to the vocals stem file."""
    from audio_separator.separator import Separator

    separator = Separator(output_dir=str(out_dir))
    separator.load_model(model_filename=model)
    outputs = separator.separate(str(path))
    # Resolve output paths (audio-separator may return names relative to out_dir).
    files = [out_dir / Path(name).name for name in outputs]
    # The model filename itself contains "vocals". Match the explicit stem
    # label, otherwise an `_(other)_...vocals_mel_band_roformer` output can be
    # mistaken for the vocal stem when it appears first in the backend output.
    vocal_files = [f for f in files if "_(vocals)_" in f.name.lower()]
    if not vocal_files:
        raise RuntimeError(
            f"separation produced no vocals stem (outputs: {[f.name for f in files]})"
        )
    return vocal_files[0]


def separate(path: str | Path) -> tuple[np.ndarray, np.ndarray, int]:
    """Return (vocal, instrumental, sample_rate), each (channels, samples).

    The model is deliberately not configurable at runtime: the product ships
    only the pinned MIT RoFormer checkpoint declared above.
    """
    if not available():
        raise RuntimeError(
            "Song mode needs the separation backend. Install it with: "
            "pip install 'voxpolish[separation]' (audio-separator). "
            "Or run --mode voice for recordings that are already mostly voice."
        )

    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        vocal_path = _run_separator(path, SEPARATION_MODEL, out_dir)
        vocal, sr = audio_io.load(vocal_path)
        mix, mix_sr = audio_io.load(path)

    # Disaster-2 guard: normalize sr / channels / length, then derive the
    # instrumental as mix - vocal so vocal + instrumental == mix exactly.
    if mix_sr != sr:
        mix = _resample(mix, mix_sr, sr)
    vocal, mix = _match_shape(vocal, mix)
    instrumental = mix - vocal
    return vocal.astype(np.float32), instrumental.astype(np.float32), sr


def _match_shape(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Align two (channels, samples) arrays to the same channels and length."""
    a = np.atleast_2d(a)
    b = np.atleast_2d(b)
    # Match channel count (broadcast mono up, or average down).
    if a.shape[0] != b.shape[0]:
        ch = max(a.shape[0], b.shape[0])
        a = _to_channels(a, ch)
        b = _to_channels(b, ch)
    n = min(a.shape[1], b.shape[1])
    return a[:, :n].copy(), b[:, :n].copy()


def _to_channels(x: np.ndarray, ch: int) -> np.ndarray:
    if x.shape[0] == ch:
        return x
    if x.shape[0] == 1:
        return np.repeat(x, ch, axis=0)
    if ch == 1:
        return x.mean(axis=0, keepdims=True)
    return np.repeat(x[:1], ch, axis=0)


def _resample(x: np.ndarray, sr_from: int, sr_to: int) -> np.ndarray:
    from scipy.signal import resample_poly

    from math import gcd

    g = gcd(int(sr_from), int(sr_to))
    return resample_poly(x, int(sr_to) // g, int(sr_from) // g, axis=1)
