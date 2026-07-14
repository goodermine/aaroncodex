"""The Tune module inside editor sessions: analyzed at create, honored at render."""

import numpy as np
import pytest
import soundfile as sf

from test_pitch import SR, _gap, _tone
from voxpolish.server.session import Session
from voxpolish.stages import pitch


@pytest.fixture()
def tuned_session(tmp_path):
    """A session over a melodic take with one deliberately flat note."""
    flat_a = 440.0 * 2 ** (-40 / 1200)
    x = np.concatenate([
        _tone(440.0, 0.8), _gap(0.3), _tone(flat_a, 0.9), _gap(0.3), _tone(392.0, 0.8),
    ])
    src = tmp_path / "take.wav"
    sf.write(src, x, SR)
    root = tmp_path / "take_session"
    Session.create(src, root)
    return Session(root)


def test_session_carries_pitch_analysis(tuned_session):
    doc = tuned_session.document()
    assert doc.pitch.get("curve"), "session must include the correction curve"
    assert doc.pitch.get("notes")
    assert "key" in doc.pitch


@pytest.mark.skipif(not pitch.vocoder_available(), reason="pyworld not installed")
def test_tune_toggle_changes_the_render(tuned_session):
    from voxpolish import audio_io

    s = tuned_session
    result = s.render()
    assert any("tuned" in n for n in result["notes"]), result
    tuned, _ = audio_io.load(s.root / "vocal_cleaned.wav")

    doc = s.document()
    doc.bypass = {**doc.bypass, "tune": True}
    s.update_document(doc.to_json(), expected_revision=s.revision())
    result = s.render()
    assert not any("tuned" in n for n in result["notes"])
    untuned, _ = audio_io.load(s.root / "vocal_cleaned.wav")

    assert not np.array_equal(tuned, untuned), "tune toggle must change the audio"


@pytest.mark.skipif(not pitch.vocoder_available(), reason="pyworld not installed")
def test_tune_amount_zero_equals_bypass(tuned_session):
    from voxpolish import audio_io

    s = tuned_session
    doc = s.document()
    doc.amounts = {**doc.amounts, "tune": 0.0}
    s.update_document(doc.to_json(), expected_revision=s.revision())
    s.render()
    at_zero, _ = audio_io.load(s.root / "vocal_cleaned.wav")

    doc = s.document()
    doc.amounts = {**doc.amounts, "tune": 1.0}
    doc.bypass = {**doc.bypass, "tune": True}
    s.update_document(doc.to_json(), expected_revision=s.revision())
    s.render()
    bypassed, _ = audio_io.load(s.root / "vocal_cleaned.wav")

    assert np.array_equal(at_zero, bypassed)


def test_sessions_without_pitch_still_render(speech_signal, tmp_path):
    """Pre-tuner sessions (no pitch field) keep rendering fine."""
    mono, sr, _ = speech_signal
    src = tmp_path / "talk.wav"
    sf.write(src, mono, sr)
    root = tmp_path / "talk_session"
    Session.create(src, root)
    s = Session(root)
    doc = s.document()
    doc.pitch = {}
    s.update_document(doc.to_json(), expected_revision=s.revision())
    result = s.render()
    assert result["rendered"]
    assert result["notes"] == []
