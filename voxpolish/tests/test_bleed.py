"""Bleed suppression: instrumental leakage drops, the singer survives."""

import numpy as np

from conftest import SR, _silence, _voice_burst
from voxpolish.stages import bleed


def _instrumental(dur_s, seed=3):
    """Tonal 'music': a chord of steady tones plus band noise."""
    t = np.arange(int(dur_s * SR)) / SR
    rng = np.random.default_rng(seed)
    x = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (110, 220, 330, 587))
    x = x / np.max(np.abs(x)) * 0.3
    noise = rng.standard_normal(len(t)) * 0.02
    return (x + noise).astype(np.float32)[None, :]


def _leaky_vocal_fixture(leak=0.12):
    """A 'separated vocal stem': real vocal bursts + instrumental leakage."""
    vocal = np.concatenate([
        _voice_burst(1.2, -16, seed=61), _silence(1.0, seed=62),
        _voice_burst(1.2, -20, seed=63), _silence(1.2, seed=64),
        _voice_burst(1.5, -18, seed=65), _silence(0.9, seed=66),
    ]).astype(np.float32)[None, :]
    instr = _instrumental(len(vocal[0]) / SR + 0.1)[:, : vocal.shape[1]]
    stem = vocal + leak * instr
    marks = {"pause": (1.3, 2.1), "phrase": (2.25, 3.35)}
    return stem, instr, vocal, marks


def _rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)) + 1e-12)


def test_bleed_is_reduced_in_pauses():
    stem, instr, _, marks = _leaky_vocal_fixture()
    out, report = bleed.suppress(stem, instr, SR, strength=0.9)
    assert report["applied"]
    s, e = marks["pause"]
    seg = slice(int((s + 0.1) * SR), int((e - 0.1) * SR))
    drop = _rms_db(stem[0, seg]) - _rms_db(out[0, seg])
    assert drop >= 6.0, f"bleed only dropped {drop:.1f} dB in the pause"


def test_vocal_phrases_survive():
    stem, instr, _, marks = _leaky_vocal_fixture()
    out, _ = bleed.suppress(stem, instr, SR, strength=0.9)
    s, e = marks["phrase"]
    seg = slice(int((s + 0.1) * SR), int((e - 0.1) * SR))
    change = abs(_rms_db(out[0, seg]) - _rms_db(stem[0, seg]))
    assert change < 2.0, f"vocal phrase level moved {change:.1f} dB"


def test_attenuation_is_floored():
    stem, instr, _, marks = _leaky_vocal_fixture(leak=0.3)
    out, _ = bleed.suppress(stem, instr, SR, strength=1.0, max_att_db=12.0)
    s, e = marks["pause"]
    seg = slice(int((s + 0.1) * SR), int((e - 0.1) * SR))
    drop = _rms_db(stem[0, seg]) - _rms_db(out[0, seg])
    assert drop <= 14.0, f"attenuation {drop:.1f} dB blew past the floor"


def test_strength_zero_is_identity():
    stem, instr, _, _ = _leaky_vocal_fixture()
    out, report = bleed.suppress(stem, instr, SR, strength=0.0)
    assert not report["applied"]
    assert np.array_equal(out, stem)


def test_length_is_preserved():
    stem, instr, _, _ = _leaky_vocal_fixture()
    out, _ = bleed.suppress(stem, instr, SR)
    assert out.shape == stem.shape


def test_clean_stem_is_barely_touched():
    """No leakage in, essentially the same vocal out."""
    _, instr, vocal, marks = _leaky_vocal_fixture(leak=0.0)
    out, report = bleed.suppress(vocal, instr, SR, strength=0.9)
    s, e = marks["phrase"]
    seg = slice(int((s + 0.1) * SR), int((e - 0.1) * SR))
    change = abs(_rms_db(out[0, seg]) - _rms_db(vocal[0, seg]))
    assert change < 1.5
    assert report["leakage_ratio_median"] < 0.2
