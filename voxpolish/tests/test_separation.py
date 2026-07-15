"""Separation contract tests.

The real MIT RoFormer model is multi-GB and heavy — it is NOT run here (that is
validated on target hardware). These tests lock the *contract and wiring* the
downstream code depends on, by mocking the neural separator: the stem-file
resolution, the mix-minus-vocal instrumental derivation, sr/channel/length
normalization, and the clean-error path when the backend is absent.
"""

import numpy as np
import pytest
import soundfile as sf

from voxpolish import audio_io
from voxpolish.stages import separation


def test_pinned_model_is_the_mit_roformer():
    # Disaster-1 guard: the default must stay the pinned MIT checkpoint.
    assert separation.SEPARATION_MODEL == "vocals_mel_band_roformer.ckpt"


def test_missing_backend_raises_clear_error(monkeypatch):
    monkeypatch.setattr(separation, "available", lambda: False)
    with pytest.raises(RuntimeError, match="separation backend"):
        separation.separate("whatever.wav")


def _fake_song(tmp_path, sr=44100, seconds=1.0):
    """A stereo 'mix' = vocal + instrumental, and the ground-truth vocal."""
    n = int(sr * seconds)
    rng = np.random.default_rng(3)
    vocal = 0.2 * rng.standard_normal((2, n)).astype(np.float32)
    instr = 0.1 * rng.standard_normal((2, n)).astype(np.float32)
    mix = vocal + instr
    # Lossless float WAV so the contract math is exact (no PCM quantization).
    mix_path = tmp_path / "song.wav"
    sf.write(mix_path, mix.T, sr, subtype="FLOAT")
    voc_path = tmp_path / "song_(Vocals)_melband.wav"
    sf.write(voc_path, vocal.T, sr, subtype="FLOAT")
    return mix_path, voc_path, vocal, instr, sr


def test_instrumental_is_mix_minus_vocal(monkeypatch, tmp_path):
    """The core safety property: vocal + instrumental reconstructs the mix."""
    mix_path, voc_path, vocal, instr, sr = _fake_song(tmp_path)
    monkeypatch.setattr(separation, "available", lambda: True)
    monkeypatch.setattr(separation, "_run_separator", lambda p, m, o: voc_path)

    out_vocal, out_instr, out_sr = separation.separate(mix_path)

    assert out_sr == sr
    assert out_vocal.shape == out_instr.shape
    # vocal + instrumental == mix (within float tolerance)
    mix, _ = audio_io.load(mix_path)
    n = out_vocal.shape[1]
    assert np.allclose(out_vocal + out_instr, mix[:, :n], atol=1e-5)
    # And the derived instrumental matches the planted one.
    assert np.allclose(out_instr, instr[:, :n], atol=1e-5)


def test_length_mismatch_is_aligned(monkeypatch, tmp_path):
    mix_path, _, vocal, _, sr = _fake_song(tmp_path)
    # Vocal stem a few samples shorter than the mix (realistic for RoFormer).
    short = tmp_path / "short_vocals.wav"
    sf.write(short, vocal[:, : vocal.shape[1] - 137].T, sr, subtype="FLOAT")
    monkeypatch.setattr(separation, "available", lambda: True)
    monkeypatch.setattr(separation, "_run_separator", lambda p, m, o: short)

    v, i, _ = separation.separate(mix_path)
    assert v.shape == i.shape
    assert v.shape[1] == vocal.shape[1] - 137


def test_no_vocals_output_is_a_clear_error(tmp_path):
    """_run_separator must fail loudly if the backend yields no vocals file —
    exercised by injecting a fake audio_separator.separator module."""
    import sys
    import types

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "song_(Instrumental)_melband.wav").write_bytes(b"")

    class FakeSep:
        def __init__(self, *a, **k):
            pass

        def load_model(self, *a, **k):
            pass

        def separate(self, *a, **k):
            return ["song_(Instrumental)_melband.wav"]  # no vocals

    pkg = types.ModuleType("audio_separator")
    mod = types.ModuleType("audio_separator.separator")
    mod.Separator = FakeSep
    pkg.separator = mod
    sys.modules["audio_separator"] = pkg
    sys.modules["audio_separator.separator"] = mod
    try:
        with pytest.raises(RuntimeError, match="no vocals stem"):
            separation._run_separator("song.wav", separation.SEPARATION_MODEL, out_dir)
    finally:
        del sys.modules["audio_separator.separator"]
        del sys.modules["audio_separator"]
