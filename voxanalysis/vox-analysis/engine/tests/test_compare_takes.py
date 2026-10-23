"""Key detection in the take-vs-original melody match (tools/compare_takes.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "compare_takes", Path(__file__).resolve().parents[1] / "tools" / "compare_takes.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

RATE = 9.57


def melody(seconds=150, lead_in=0.0, shift=0):
    """A repeating four-note tune in cents re A440, at the stored contour rate."""
    rng = np.random.default_rng(1)
    tune = np.array([-900, -700, -500, -400]) + 100 * shift
    n = int(seconds * RATE)
    notes = np.repeat(np.resize(tune, n // 8 + 1), 8)[:n].astype(float)
    notes += rng.normal(0, 8, n)
    notes[rng.random(n) < 0.3] = np.nan          # unvoiced gaps
    return np.concatenate([np.full(int(lead_in * RATE), np.nan), notes])


def test_a_take_with_a_longer_intro_keeps_its_key():
    # 18 s of extra intro used to read as a 4-semitone shift.
    offset, semitones = C.transposition_offset(melody(lead_in=18.0), melody())
    assert semitones == 0 and offset == 0.0


def test_a_transposed_take_reads_its_shift():
    assert C.transposition_offset(melody(shift=3, lead_in=7.0), melody())[1] == 3
    assert C.transposition_offset(melody(shift=-2), melody())[1] == -2


def test_an_octave_down_is_recognised():
    assert C.transposition_offset(melody(shift=-12, lead_in=5.0), melody())[1] == -12
