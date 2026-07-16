"""Clean stage: model-based denoise of the (separated) vocal.

Backend: DeepFilterNet if installed, otherwise pass-through. This is the one
stage that runs *before* analysis, so every detector sees the cleaned signal.
Amount blends dry/wet so the model never has the final word.
"""

from __future__ import annotations

import numpy as np


def available_backend() -> str:
    try:
        import df.enhance  # noqa: F401

        return "deepfilternet"
    except ImportError:
        return "none"


def process_split(audio: np.ndarray, sr: int, amount: float = 1.0) -> tuple[np.ndarray, np.ndarray | None, dict]:
    """Denoise (channels, samples) audio.

    Returns (blended, wet, settings-dict). ``wet`` is the fully-denoised signal
    (model output at 100%), or None when no backend is available. Callers that
    persist ``wet`` alongside the raw input can re-blend to ANY amount later
    with plain arithmetic — no model re-run (this is what lets the editor's
    Clean slider actually work at render time instead of being decorative).
    The wet signal is computed whenever the backend exists, even at amount 0,
    so a later increase of the slider has something to blend against.
    """
    backend = available_backend()
    amount = float(np.clip(amount, 0.0, 1.0))
    if backend == "none":
        return audio, None, {"amount": 0.0, "backend": "none"}

    import torch
    from df.enhance import enhance, init_df

    model, df_state, _ = init_df()
    model_sr = df_state.sr()
    wet_all = np.empty_like(audio)
    for ch in range(audio.shape[0]):
        x = audio[ch]
        # DeepFilterNet runs at its own rate; resample in and out if needed.
        if sr != model_sr:
            import torchaudio

            t = torchaudio.functional.resample(torch.from_numpy(x), sr, model_sr)
        else:
            t = torch.from_numpy(x.copy())
        wet = enhance(model, df_state, t.unsqueeze(0)).squeeze(0)
        if sr != model_sr:
            import torchaudio

            wet = torchaudio.functional.resample(wet, model_sr, sr)
        wet = wet.numpy()[: len(x)]
        if len(wet) < len(x):
            wet = np.pad(wet, (0, len(x) - len(wet)))
        wet_all[ch] = wet
    blended = blend(audio, wet_all, amount)
    return blended, wet_all, {"amount": amount, "backend": backend}


def blend(raw: np.ndarray, wet: np.ndarray, amount: float) -> np.ndarray:
    """amount·wet + (1−amount)·raw — the stage's canonical dry/wet mix."""
    amount = float(np.clip(amount, 0.0, 1.0))
    if amount <= 0.0:
        return raw
    n = min(raw.shape[-1], wet.shape[-1])
    return amount * wet[..., :n] + (1 - amount) * raw[..., :n]


def process(audio: np.ndarray, sr: int, amount: float = 1.0) -> tuple[np.ndarray, dict]:
    """Denoise (channels, samples) audio. Returns (audio, settings-dict for the doc)."""
    blended, _wet, info = process_split(audio, sr, amount)
    return blended, info
