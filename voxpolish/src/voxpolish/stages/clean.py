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


def process(audio: np.ndarray, sr: int, amount: float = 1.0) -> tuple[np.ndarray, dict]:
    """Denoise (channels, samples) audio. Returns (audio, settings-dict for the doc)."""
    backend = available_backend()
    amount = float(np.clip(amount, 0.0, 1.0))
    if backend == "none" or amount == 0.0:
        return audio, {"amount": 0.0, "backend": "none"}

    import torch
    from df.enhance import enhance, init_df

    model, df_state, _ = init_df()
    model_sr = df_state.sr()
    out = np.empty_like(audio)
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
        out[ch] = amount * wet + (1 - amount) * x
    return out, {"amount": amount, "backend": backend}
