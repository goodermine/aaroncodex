"""Render-time knobs: bypass and amounts are honored, non-destructively."""

import numpy as np

from voxpolish.document import EditDocument
from voxpolish.pipeline import Settings, analyze
from voxpolish.stages import render


def _doc(audio, sr):
    return analyze(audio, sr, Settings.for_mode("voice"))


def _rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)))


def test_gate_bypass_leaves_pauses_untouched(speech_signal):
    mono, sr, marks = speech_signal
    audio = np.atleast_2d(mono)
    doc = _doc(audio, sr)
    assert doc.pauses
    doc.gain_curve, doc.breaths, doc.sibilants = [], [], []
    doc.bypass = {"gate": True}
    out = render.render(audio, sr, doc)
    s, e = marks["pause2"]
    seg = slice(int((s + 0.2) * sr), int((e - 0.2) * sr))
    assert abs(_rms(out[0, seg]) - _rms(audio[0, seg])) / _rms(audio[0, seg]) < 0.01


def test_dynamics_amount_zero_equals_no_curve(speech_signal):
    mono, sr, _ = speech_signal
    audio = np.atleast_2d(mono)
    doc = _doc(audio, sr)
    doc.pauses, doc.breaths, doc.sibilants = [], [], []
    doc.amounts["dynamics"] = 0.0
    with_zero = render.render(audio, sr, doc)
    doc.gain_curve = []
    without = render.render(audio, sr, doc)
    assert np.array_equal(with_zero, without)


def test_dynamics_amount_scales_the_curve(speech_signal):
    mono, sr, marks = speech_signal
    audio = np.atleast_2d(mono)
    doc = _doc(audio, sr)
    doc.pauses, doc.breaths, doc.sibilants = [], [], []
    s, e = marks["phrase_quiet"]
    seg = slice(int((s + 0.2) * sr), int((e - 0.2) * sr))

    doc.amounts["dynamics"] = 1.0
    full = 20 * np.log10(_rms(render.render(audio, sr, doc)[0, seg]) + 1e-12)
    doc.amounts["dynamics"] = 0.5
    half = 20 * np.log10(_rms(render.render(audio, sr, doc)[0, seg]) + 1e-12)
    base = 20 * np.log10(_rms(audio[0, seg]) + 1e-12)

    boost_full, boost_half = full - base, half - base
    assert boost_full > 2.0
    assert 0.35 < boost_half / boost_full < 0.65, "50% amount should halve the boost"


def test_breath_amount_scales_reduction(speech_signal):
    mono, sr, marks = speech_signal
    audio = np.atleast_2d(mono)
    doc = _doc(audio, sr)
    assert doc.breaths
    doc.gain_curve, doc.pauses, doc.sibilants = [], [], []
    s, e = marks["breath"]
    seg = slice(int((s + 0.05) * sr), int((e - 0.05) * sr))

    doc.amounts["breath"] = 1.0
    full = _rms(render.render(audio, sr, doc)[0, seg])
    doc.amounts["breath"] = 0.0
    off = _rms(render.render(audio, sr, doc)[0, seg])
    assert full < off * 0.9, "breath amount 0 must disable the dip"
    # And the doc still carries the breath data (non-destructive).
    assert doc.breaths


def test_controls_roundtrip_and_render_identically(tmp_path, speech_signal):
    mono, sr, _ = speech_signal
    audio = np.atleast_2d(mono)
    doc = _doc(audio, sr)
    doc.bypass = {"sibilance": True}
    doc.amounts = {"dynamics": 0.8, "breath": 0.5, "sibilance": 1.2}
    path = tmp_path / "doc.json"
    doc.save(path)
    loaded = EditDocument.load(path)
    assert loaded.bypass == doc.bypass
    assert loaded.amounts == doc.amounts
    assert np.array_equal(render.render(audio, sr, doc), render.render(audio, sr, loaded))


def test_old_documents_without_controls_still_load(tmp_path, speech_signal):
    """Sessions created before the knobs existed must keep working."""
    import json

    mono, sr, _ = speech_signal
    doc = _doc(np.atleast_2d(mono), sr)
    raw = json.loads(doc.to_json())
    del raw["bypass"], raw["amounts"]
    loaded = EditDocument.from_json(json.dumps(raw))
    assert loaded.bypass == {}
    assert loaded.amounts == {"dynamics": 1.0, "breath": 1.0, "sibilance": 1.0}
