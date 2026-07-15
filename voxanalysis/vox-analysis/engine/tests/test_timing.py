"""Timing / groove — the canonical timing scorer (analyse_groove) and the
relabeled onset-density module (analyse_rhythm).

Builds a synthetic percussive backing at a known tempo and a vocal onset train
offset by a controlled amount, then checks the sign/feel of the measured offset,
the mix-vs-instrumental cross-check, and the confidence tiers.
"""

import os
import sys
import tempfile

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import analyse_song as A  # noqa: E402

SR = 22050
BPM = 120.0
BEAT = 60.0 / BPM
DUR = 24.0


def _clicks(times, n, decay_s, gain, seed):
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    length = int(0.03 * SR)
    env = np.exp(-np.arange(length) / (decay_s * SR))
    for ct in times:
        i = int(ct * SR)
        if 0 <= i < n:
            seg = rng.standard_normal(length) * env
            end = min(n, i + length)
            y[i:end] += seg[: end - i]
    return y * gain


def _make_take(offset_s):
    """Backing clicks on the beat; vocal clicks shifted by offset_s (+ = late)."""
    n = int(DUR * SR)
    beats = np.arange(0.5, DUR - 0.5, BEAT)
    backing = _clicks(beats, n, decay_s=0.008, gain=0.9, seed=1)
    vocal = _clicks(beats + offset_s, n, decay_s=0.02, gain=0.6, seed=2)
    d = tempfile.mkdtemp()
    mix = os.path.join(d, "mix.wav")
    inst = os.path.join(d, "inst.wav")
    sf.write(mix, backing + vocal, SR)
    sf.write(inst, backing, SR)
    return vocal, mix, inst


def test_groove_detects_dragging():
    vocal, mix, inst = _make_take(offset_s=+0.045)
    r = A.analyse_groove(vocal, SR, inst, mix_path=mix)
    assert "error" not in r, r
    assert r["mean_offset_ms"] > 20
    assert r["feel"] == "dragging"


def test_groove_detects_rushing():
    vocal, mix, inst = _make_take(offset_s=-0.045)
    r = A.analyse_groove(vocal, SR, inst, mix_path=mix)
    assert "error" not in r, r
    assert r["mean_offset_ms"] < -20
    assert r["feel"] == "rushing"


def test_groove_high_confidence_when_references_agree():
    vocal, mix, inst = _make_take(offset_s=0.0)
    r = A.analyse_groove(vocal, SR, inst, mix_path=mix)
    assert r["confidence"] == "high"
    assert r["cross_check"]["agree"] is True
    # Offset is scored against the vocal-free instrumental grid (unbiased)...
    assert "vocal-free" in r["grid_source"]
    # ...and validated against the pre-split mix's tempo (the cross-check).
    assert r["cross_check"]["mix_tempo_bpm"] > 0


def test_groove_medium_confidence_with_single_reference():
    vocal, _mix, inst = _make_take(offset_s=0.0)
    r = A.analyse_groove(vocal, SR, inst, mix_path=None)
    assert r["confidence"] == "medium"
    assert r["cross_check"] is None
    assert "instrumental" in r["grid_source"]


def test_groove_errors_without_any_backing():
    vocal, _mix, _inst = _make_take(offset_s=0.0)
    r = A.analyse_groove(vocal, SR, instrumental_path=None, mix_path=None)
    assert "error" in r


def test_rhythm_is_relabeled_as_onset_density_not_timing():
    """analyse_rhythm must no longer masquerade as timing-vs-the-song."""
    vocal, _mix, _inst = _make_take(offset_s=0.0)
    r = A.analyse_rhythm(vocal, SR, is_isolated_stem=True)
    assert "onset density" in r["measures"]
    assert "analyse_groove" in r["timing_vs_backing"]
    assert "indicative only" in r["tempo_confidence"]
