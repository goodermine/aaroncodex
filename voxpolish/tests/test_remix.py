"""Remix sum contract: exact per-stem gains; loudness/peaks are mastering's job."""

import numpy as np

from voxpolish.pipeline import Settings, mix_remix

SR = 44100


def _sine(freq, dur_s, amp):
    t = np.arange(int(dur_s * SR)) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)[None, :]


def test_balance_is_measured_by_default_in_both_modes():
    assert Settings.for_mode("song").remix_vocal_db is None
    assert Settings.for_mode("voice").remix_vocal_db is None


def test_mix_applies_per_stem_gains_exactly():
    vocal = _sine(440, 1.0, 0.2)
    instr = _sine(220, 1.0, 0.2)
    remix = mix_remix(vocal, instr, vocal_db=-2.0, instr_db=1.0)
    expected = vocal * 10 ** (-2 / 20) + instr * 10 ** (1 / 20)
    assert np.allclose(remix, expected, atol=1e-7)


def test_mix_does_not_normalize():
    vocal = _sine(440, 0.5, 0.9)
    instr = _sine(440, 0.5, 0.9)  # in phase: sum exceeds full scale
    remix = mix_remix(vocal, instr)
    assert np.max(np.abs(remix)) > 1.5, "mix must be untouched; mastering handles peaks"
