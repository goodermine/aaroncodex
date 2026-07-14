"""Delta contract: removed.wav is targeted removal only; leveling is excluded.

Strictness contract, documented here and asserted below:
- outside an event region (+ its fade, already inside the region, + 60 ms of
  filter context for band-limited sibilance events), removal-delta amplitude
  must stay below ~1e-5 full scale (float32 rounding territory);
- inside non-target voiced intervals, removal-delta energy must sit at least
  80 dB below the voiced signal itself.
"""

from dataclasses import replace

import numpy as np

from voxpolish.pipeline import Settings, analyze
from voxpolish.stages import render

FLOAT_TOL = 1e-5  # amplitude floor for "effectively zero" (float32 rounding)
SIB_CONTEXT_S = 0.06  # documented filter context around sibilance events


def _removal_delta(audio, sr, doc):
    """removed.wav semantics: input minus a unity-gain (no dynamics) render."""
    return audio - render.render(audio, sr, replace(doc, gain_curve=[]))


def _single_op_doc(audio, sr, keep):
    doc = analyze(audio, sr, Settings.for_mode("voice"))
    if keep != "dynamics":
        doc.gain_curve = []
    for name in ("pauses", "breaths", "sibilants"):
        if name != keep:
            setattr(doc, name, [])
    return doc


def _outside_mask(n, sr, regions, context_s=0.0):
    mask = np.ones(n, dtype=bool)
    for r in regions:
        s = max(0, int((r.start - context_s) * sr))
        e = min(n, int((r.end + context_s) * sr) + 1)
        mask[s:e] = False
    return mask


def test_dynamics_only_removal_delta_is_zero(speech_signal):
    mono, sr, _ = speech_signal
    audio = np.atleast_2d(mono)
    doc = _single_op_doc(audio, sr, keep="dynamics")
    assert doc.gain_curve, "fixture must produce a dynamics curve"
    delta = _removal_delta(audio, sr, doc)
    assert np.max(np.abs(delta)) < FLOAT_TOL


def test_dynamics_only_full_difference_is_nonzero(speech_signal):
    mono, sr, _ = speech_signal
    audio = np.atleast_2d(mono)
    doc = _single_op_doc(audio, sr, keep="dynamics")
    full_diff = audio - render.render(audio, sr, doc)
    assert np.max(np.abs(full_diff)) > 1e-3, "leveling must show up in full_difference"


def test_gate_only_delta_confined_to_pauses(speech_signal):
    mono, sr, _ = speech_signal
    audio = np.atleast_2d(mono)
    doc = _single_op_doc(audio, sr, keep="pauses")
    assert doc.pauses
    delta = _removal_delta(audio, sr, doc)
    outside = _outside_mask(audio.shape[1], sr, doc.pauses)
    assert np.max(np.abs(delta[:, outside])) < FLOAT_TOL
    assert np.max(np.abs(delta[:, ~outside])) > 1e-4, "gated pauses must appear in delta"


def test_breath_only_delta_confined_to_breaths(speech_signal):
    mono, sr, _ = speech_signal
    audio = np.atleast_2d(mono)
    doc = _single_op_doc(audio, sr, keep="breaths")
    assert doc.breaths
    delta = _removal_delta(audio, sr, doc)
    outside = _outside_mask(audio.shape[1], sr, doc.breaths)
    assert np.max(np.abs(delta[:, outside])) < FLOAT_TOL
    assert np.max(np.abs(delta[:, ~outside])) > 1e-5


def test_sibilance_only_delta_confined_to_events(speech_signal):
    mono, sr, _ = speech_signal
    audio = np.atleast_2d(mono)
    doc = _single_op_doc(audio, sr, keep="sibilants")
    assert doc.sibilants
    delta = _removal_delta(audio, sr, doc)
    outside = _outside_mask(audio.shape[1], sr, doc.sibilants, context_s=SIB_CONTEXT_S)
    assert np.max(np.abs(delta[:, outside])) < FLOAT_TOL
    assert np.max(np.abs(delta[:, ~outside])) > 1e-5


def test_voiced_intervals_stay_out_of_removal_delta(speech_signal):
    """Non-target voiced audio must be >= 80 dB below itself in removed.wav."""
    mono, sr, marks = speech_signal
    audio = np.atleast_2d(mono)
    doc = _single_op_doc(audio, sr, keep="pauses")
    delta = _removal_delta(audio, sr, doc)
    for phrase in ("phrase_loud", "phrase_quiet", "phrase_mid"):
        s, e = marks[phrase]
        seg = slice(int((s + 0.1) * sr), int((e - 0.1) * sr))
        sig_rms = np.sqrt(np.mean(audio[0, seg] ** 2))
        delta_rms = np.sqrt(np.mean(delta[0, seg] ** 2))
        assert delta_rms < sig_rms * 1e-4, f"{phrase}: removal delta leaks voiced audio"
