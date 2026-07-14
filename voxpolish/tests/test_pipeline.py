"""End-to-end voice-mode pipeline tests (no ML models needed)."""

import json

import numpy as np
import soundfile as sf

from voxpolish import audio_io
from voxpolish.document import EditDocument
from voxpolish.pipeline import Settings, analyze, process
from voxpolish.stages import render


def test_process_voice_mode_writes_all_outputs(speech_signal, tmp_path):
    mono, sr, _ = speech_signal
    src = tmp_path / "talk.wav"
    sf.write(src, mono, sr)

    outputs = process(src, tmp_path / "out", Settings.for_mode("voice"))

    assert set(outputs) == {"vocal_cleaned", "removed", "full_difference", "edit_document"}
    cleaned, csr = audio_io.load(outputs["vocal_cleaned"])
    assert csr == sr and cleaned.shape[1] == len(mono)

    doc = json.loads((tmp_path / "out" / "edit_document.json").read_text())
    assert doc["analysis"]["counts"]["pauses"] >= 1
    assert doc["analysis"]["counts"]["sibilants"] >= 1
    assert len(doc["gain_curve"]) > 10


def test_render_is_deterministic(speech_signal):
    mono, sr, _ = speech_signal
    audio = np.atleast_2d(mono)
    doc = analyze(audio, sr, Settings.for_mode("voice"))
    a = render.render(audio, sr, doc)
    b = render.render(audio, sr, doc)
    assert np.array_equal(a, b)


def test_document_roundtrip_renders_identically(speech_signal, tmp_path):
    mono, sr, _ = speech_signal
    audio = np.atleast_2d(mono)
    doc = analyze(audio, sr, Settings.for_mode("voice"))
    path = tmp_path / "doc.json"
    doc.save(path)
    doc2 = EditDocument.load(path)
    assert np.array_equal(render.render(audio, sr, doc), render.render(audio, sr, doc2))


def test_editing_the_document_changes_the_render(speech_signal):
    """The no-black-box promise: a human edit to the JSON must be honored exactly."""
    mono, sr, marks = speech_signal
    audio = np.atleast_2d(mono)
    doc = analyze(audio, sr, Settings.for_mode("voice"))

    base = render.render(audio, sr, doc)

    # A user deletes all gate decisions: pauses must come back untouched.
    doc_no_gate = analyze(audio, sr, Settings.for_mode("voice"))
    doc_no_gate.pauses = []
    ungated = render.render(audio, sr, doc_no_gate)

    s, e = marks["pause2"]
    seg = slice(int((s + 0.2) * sr), int((e - 0.2) * sr))
    assert np.abs(base[0, seg]).mean() < np.abs(ungated[0, seg]).mean()


def test_gate_actually_attenuates_the_pause(speech_signal):
    mono, sr, marks = speech_signal
    audio = np.atleast_2d(mono)
    doc = analyze(audio, sr, Settings.for_mode("voice"))
    out = render.render(audio, sr, doc)

    s, e = marks["pause2"]
    seg = slice(int((s + 0.25) * sr), int((e - 0.25) * sr))
    before = 20 * np.log10(np.abs(audio[0, seg]).mean() + 1e-12)
    after = 20 * np.log10(np.abs(out[0, seg]).mean() + 1e-12)
    assert after < before - 20, f"pause only dropped {before - after:.1f} dB"


def test_rerender_from_edited_doc_via_process(speech_signal, tmp_path):
    mono, sr, _ = speech_signal
    src = tmp_path / "talk.wav"
    sf.write(src, mono, sr)
    out1 = process(src, tmp_path / "o1", Settings.for_mode("voice"))

    doc = EditDocument.load(out1["edit_document"])
    doc.pauses = []  # simulated human edit
    out2 = process(src, tmp_path / "o2", Settings.for_mode("voice"), edit_doc=doc)

    a, _ = audio_io.load(out1["vocal_cleaned"])
    b, _ = audio_io.load(out2["vocal_cleaned"])
    assert not np.array_equal(a, b)
