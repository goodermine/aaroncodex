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


def test_tune_enabled_by_default(tuned_session):
    """Decision record (July 15): Tune is enabled by default in new sessions."""
    doc = tuned_session.document()
    assert doc.bypass.get("tune") is False


def test_tune_starts_gentle_at_ten_percent(tuned_session):
    """Field default: Auto Tune comes up at 10% so first renders are subtle."""
    assert tuned_session.document().amounts.get("tune") == 0.1


def test_session_pitch_includes_track(tuned_session):
    """The editor pitch lane needs the sung-pitch track in the document."""
    doc = tuned_session.document()
    assert doc.pitch.get("track")
    assert all(len(pt) == 3 for pt in doc.pitch["track"])


def test_clean_only_session_bypasses_tune(tmp_path):
    """The 'Clean vocal' upload choice creates a session with Tune bypassed."""
    from voxpolish.server.session import Session

    flat = 440.0 * 2 ** (-40 / 1200)
    x = np.concatenate([_tone(440.0, 0.6), _gap(0.3), _tone(flat, 0.9)])
    src = tmp_path / "take.wav"
    sf.write(src, x, SR)
    s = Session.create(src, tmp_path / "clean_only", tune=False)
    assert s.document().bypass.get("tune") is True
    result = s.render()
    assert not any("tuned" in n for n in result["notes"])


@pytest.mark.skipif(not pitch.vocoder_available(), reason="pyworld not installed")
def test_tune_toggle_changes_the_render(tuned_session):
    from voxpolish import audio_io

    s = tuned_session
    # Default session has Tune on -> baseline is tuned; bypass to get untuned.
    doc = s.document()
    doc.bypass = {**doc.bypass, "tune": True}
    s.update_document(doc.to_json(), expected_revision=s.revision())
    s.render()
    untuned, _ = audio_io.load(s.root / "vocal_cleaned.wav")

    doc = s.document()
    doc.bypass = {**doc.bypass, "tune": False}  # user opts back in
    s.update_document(doc.to_json(), expected_revision=s.revision())
    result = s.render()
    assert any("tuned" in n for n in result["notes"]), result
    tuned, _ = audio_io.load(s.root / "vocal_cleaned.wav")

    assert not np.array_equal(tuned, untuned), "tune toggle must change the audio"


@pytest.mark.skipif(not pitch.vocoder_available(), reason="pyworld not installed")
def test_tune_amount_zero_equals_bypass(tuned_session):
    from voxpolish import audio_io

    s = tuned_session
    doc = s.document()
    doc.bypass = {**doc.bypass, "tune": False}  # enabled...
    doc.amounts = {**doc.amounts, "tune": 0.0}  # ...but amount zero
    s.update_document(doc.to_json(), expected_revision=s.revision())
    s.render()
    at_zero, _ = audio_io.load(s.root / "vocal_cleaned.wav")

    doc = s.document()
    doc.amounts = {**doc.amounts, "tune": 1.0}
    doc.bypass = {**doc.bypass, "tune": True}  # bypassed at full amount
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
