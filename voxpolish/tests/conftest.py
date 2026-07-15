"""Synthetic test signals: a fake 'spoken phrase' recording we control exactly."""

import numpy as np
import pytest

SR = 44100


def _voice_burst(dur_s, level_db, sr=SR, seed=0):
    """Band-limited (300 Hz - 3 kHz) noise burst that behaves like voiced speech."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    x = rng.standard_normal(n)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    spec[(freqs < 300) | (freqs > 3000)] = 0
    x = np.fft.irfft(spec, n)
    x /= np.sqrt(np.mean(x**2)) + 1e-12
    x *= 10 ** (level_db / 20)
    # 10 ms edge fades so bursts don't click.
    fade = int(0.01 * sr)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x


def _sibilant_burst(dur_s, level_db, sr=SR, seed=1):
    """High-band (5-9 kHz) noise burst, like a harsh 'S'."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    x = rng.standard_normal(n)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    spec[(freqs < 5000) | (freqs > 9000)] = 0
    x = np.fft.irfft(spec, n)
    x /= np.sqrt(np.mean(x**2)) + 1e-12
    return x * 10 ** (level_db / 20)


def _breath_burst(dur_s, level_db, sr=SR, seed=2):
    """Broadband flat noise at low level, like a breath between phrases."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    x = rng.standard_normal(n)
    x /= np.sqrt(np.mean(x**2)) + 1e-12
    fade = int(0.02 * sr)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x * 10 ** (level_db / 20)


def _silence(dur_s, sr=SR, noise_db=-70.0, seed=3):
    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    return rng.standard_normal(n) * 10 ** (noise_db / 20)


@pytest.fixture(scope="session")
def speech_signal():
    """~7 s: loud phrase / pause / breath / quiet phrase with a sibilant / pause / phrase.

    Returns (mono float32, sr, landmarks dict with segment times).
    """
    parts = [
        ("phrase_loud", _voice_burst(1.2, -14, seed=10)),
        ("pause1", _silence(0.8, seed=11)),
        ("breath", _breath_burst(0.3, -38, seed=12)),
        ("gap", _silence(0.15, seed=13)),
        ("phrase_quiet", _voice_burst(1.2, -30, seed=14)),
        ("sibilant", _sibilant_burst(0.12, -16, seed=15)),
        ("pause2", _silence(1.0, seed=16)),
        ("phrase_mid", _voice_burst(1.5, -20, seed=17)),
        ("tail", _silence(0.5, seed=18)),
    ]
    landmarks = {}
    t = 0.0
    chunks = []
    for name, x in parts:
        landmarks[name] = (t, t + len(x) / SR)
        t += len(x) / SR
        chunks.append(x)
    return np.concatenate(chunks).astype(np.float32), SR, landmarks
