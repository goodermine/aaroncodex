"""Every gate must catch damage we inflicted on purpose, or it does not ship.

There is no corpus of labelled compressed, autotuned or EQ'd vocals, so a gate
like "suspected compression" has nothing to be checked against. A detector nobody
can check is worse than no detector: it lends degraded numbers the authority of
having passed validation. This project has the receipts — `reliability: "medium
— verify by ear"` has shipped for months and nobody has ever verified by ear.

So ground truth is manufactured. Take the one real vocal stem in the repo, damage
it with known parameters, and require each gate to notice its own damage and stay
quiet on the clean original. The VALIDATED markings in gates.py are re-derived
here rather than trusted, so the claim and the evidence cannot drift apart.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ENGINE)
sys.path.insert(0, os.path.join(ENGINE, "standalone"))

import degrade  # noqa: E402
import gates  # noqa: E402

STEM = os.path.join(ENGINE, "temp",
                    "pressure_down_cook_(Vocals)_UVR_MDXNET_Main_converted.wav")
pytestmark = pytest.mark.skipif(not os.path.isfile(STEM),
                                reason="needs the reference vocal stem")


@pytest.fixture(scope="module")
def clean():
    import librosa
    y, sr = librosa.load(STEM, sr=44100, mono=True, duration=45.0)
    return y, sr


def _caught(gate, audio, sr, **kw):
    return not gate(audio, sr, **kw).passed


def test_clipping_catches_overdrive_and_passes_clean(clean):
    y, sr = clean
    assert not _caught(gates.gate_clipping, y, sr), "clean audio must not read as clipped"
    assert _caught(gates.gate_clipping, degrade.clip(y, -6.0), sr)


def test_snr_catches_added_noise(clean):
    y, sr = clean
    assert not _caught(gates.gate_snr, y, sr)
    assert _caught(gates.gate_snr, degrade.add_noise(y, snr_db=12.0), sr)


def test_compression_needs_active_frames_not_the_whole_file(clean):
    """The whole-file crest factor is dominated by silence between phrases and
    barely moves under 8:1 (22.1 -> 20.0 dB). Restricted to frames containing
    singing it separates: 13.5 -> 6.6 dB. This is the fix, so it is the test."""
    y, sr = clean
    squashed = degrade.compress(y, sr, threshold_db=-30.0, ratio=8.0)
    assert not _caught(gates.gate_compression, y, sr)
    assert _caught(gates.gate_compression, squashed, sr)

    whole_file_crest = lambda a: 20 * np.log10(
        (np.max(np.abs(a)) + 1e-12) / (np.sqrt(np.mean(a * a)) + 1e-12))
    assert abs(whole_file_crest(y) - whole_file_crest(squashed)) < 4.0, (
        "if the whole-file crest factor ever separates these, revisit the gate — "
        "but as measured it does not, which is why active frames are used")


def test_pitch_correction_catches_quantised_f0(clean):
    y, sr = clean
    short = y[: 20 * sr]
    assert not _caught(gates.gate_pitch_correction, short, sr)
    assert _caught(gates.gate_pitch_correction, degrade.quantise_pitch(short, sr), sr)


def test_pitch_track_catches_injected_octave_errors(clean):
    """Octave errors inflated drift readings in this project before. 3% injected
    must be caught."""
    import librosa
    y, sr = clean
    short = y[: 20 * sr]
    f0, _, vp = librosa.pyin(short, fmin=70, fmax=900, sr=sr, hop_length=512)
    assert not _caught(gates.gate_pitch_track, short, sr, f0=f0, voiced_prob=vp)
    broken = f0.copy()
    idx = np.where(np.isfinite(broken))[0]
    pick = np.random.default_rng(0).choice(idx, size=max(1, int(0.03 * len(idx))),
                                           replace=False)
    broken[pick] *= 2.0
    assert _caught(gates.gate_pitch_track, short, sr, f0=broken, voiced_prob=vp)


def test_unvalidated_gates_suppress_nothing(clean):
    """reverb and eq could not be made to pass. They must be reported and must
    not silence a metric, or the suppression rule becomes theatre."""
    y, sr = clean
    assert gates.REVERB_VALIDATED is False
    assert gates.EQ_VALIDATED is False
    res = gates.run_gates(y, sr)
    assert set(res["gates_not_validated"]) == {"reverb", "eq"}
    for name in ("reverb", "eq"):
        g = res["gates"][name]
        assert "note" in g, f"{name} must say it certifies nothing"


def test_a_gate_that_cannot_measure_does_not_read_as_clean(clean):
    """Dense singing supplies no isolated phrase endings, so the reverb gate has
    nothing to measure. 'Unknown' and 'clean' must not be the same outcome."""
    y, sr = clean
    r = gates.gate_reverb(y, sr)
    if not r.measurable:
        assert r.severity == "unknown"
        assert "certifies nothing" in r.to_dict()["note"]


def test_the_overall_verdict_ignores_unvalidated_and_unmeasurable_gates(clean):
    y, sr = clean
    res = gates.run_gates(y, sr)
    assert res["passed"] is True, "the clean stem must pass on every gate that can judge it"
    assert res["suppressed_metrics"] == []
    res_bad = gates.run_gates(degrade.clip(y, -6.0), sr)
    assert res_bad["passed"] is False
    assert "everything" in res_bad["suppressed_metrics"]
