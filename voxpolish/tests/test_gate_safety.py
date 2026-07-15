"""Gate safety: pauses may never touch protected speech, at analysis or render.

Contract asserted here:
- every generated pause keeps clear-speech guards on both sides
  (>= ONSET_GUARD_S of clearance before speech resumes, >= OFFSET_GUARD_S after
  it ends, measured against the raw VAD mask);
- weak word onsets right after a pause survive rendering with >= 90% of their
  RMS energy;
- render enforces the guards even for hand-edited documents.
"""

import numpy as np
import pytest

from conftest import SR, _breath_burst, _silence, _voice_burst
from voxpolish.document import EditDocument, Region
from voxpolish.pipeline import Settings, analyze
from voxpolish.stages import gate, render


def _weak_onset_signal(onset_db, pause_s):
    """Phrase, pause, then a weak onset ("Hello"-like) leading a normal phrase."""
    parts = [
        ("lead", _voice_burst(1.0, -18, seed=21)),
        ("pause", _silence(pause_s, seed=22)),
        ("onset", _voice_burst(0.15, onset_db, seed=23)),
        ("phrase", _voice_burst(1.0, -18, seed=24)),
        ("tail", _silence(0.6, seed=25)),
    ]
    marks, chunks, t = {}, [], 0.0
    for name, x in parts:
        marks[name] = (t, t + len(x) / SR)
        t += len(x) / SR
        chunks.append(x)
    return np.concatenate(chunks).astype(np.float32), marks


def _rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=np.float64) ** 2)))


@pytest.mark.parametrize("onset_db", [-40, -34, -28])
@pytest.mark.parametrize("pause_s", [0.6, 1.2])
def test_pauses_never_overlap_speech_guards(onset_db, pause_s):
    mono, _ = _weak_onset_signal(onset_db, pause_s)
    pauses, times, mask = gate.analyze(mono, SR, use_ai=False)
    guards = gate.speech_guards(times, mask)
    assert pauses, "a pause this long must be detected"
    for p in pauses:
        for gs, ge in guards:
            assert p.end <= gs or p.start >= ge, (
                f"pause [{p.start:.2f},{p.end:.2f}] overlaps guard [{gs:.2f},{ge:.2f}]"
            )


@pytest.mark.parametrize("onset_db", [-40, -34, -28])
@pytest.mark.parametrize("pause_s", [0.6, 1.2])
def test_every_pause_has_guard_clearance_on_both_sides(onset_db, pause_s):
    mono, _ = _weak_onset_signal(onset_db, pause_s)
    pauses, times, mask = gate.analyze(mono, SR, use_ai=False)
    hop = float(times[1] - times[0])
    speech_times = times[mask]
    for p in pauses:
        before = speech_times[speech_times < p.start]
        after = speech_times[speech_times > p.end]
        if len(before):
            assert p.start - before.max() >= gate.OFFSET_GUARD_S - 2 * hop
        if len(after):
            assert after.min() - p.end >= gate.ONSET_GUARD_S - 2 * hop


@pytest.mark.parametrize("onset_db", [-40, -34, -28])
@pytest.mark.parametrize("pause_s", [0.6, 1.2])
def test_weak_onset_survives_gate_render(onset_db, pause_s):
    mono, marks = _weak_onset_signal(onset_db, pause_s)
    audio = np.atleast_2d(mono)
    doc = analyze(audio, SR, Settings.for_mode("voice"))
    doc.gain_curve, doc.breaths, doc.sibilants = [], [], []  # isolate the gate
    out = render.render(audio, SR, doc)

    s, e = marks["onset"]
    seg = slice(int(s * SR), int(e * SR))
    ratio = _rms(out[0, seg]) / (_rms(audio[0, seg]) + 1e-12)
    assert ratio >= 0.9, f"weak onset lost energy: kept {ratio:.2%}"


def test_first_and_last_phonemes_retain_energy_after_full_render(speech_signal):
    mono, sr, marks = speech_signal
    audio = np.atleast_2d(mono)
    doc = analyze(audio, sr, Settings.for_mode("voice"))
    doc.gain_curve = []  # measure gating/breath/sibilance only, not leveling
    out = render.render(audio, sr, doc)
    for phrase in ("phrase_loud", "phrase_quiet", "phrase_mid"):
        s, e = marks[phrase]
        for name, seg in (
            ("first", slice(int(s * sr), int((s + 0.08) * sr))),
            ("last", slice(int((e - 0.08) * sr), int(e * sr))),
        ):
            ratio = _rms(out[0, seg]) / (_rms(audio[0, seg]) + 1e-12)
            assert ratio >= 0.7, f"{phrase} {name} phoneme kept only {ratio:.2%}"


def test_render_trims_hand_edited_pause_off_speech():
    """A user drags a pause onto a word: render must protect the guarded speech."""
    mono, marks = _weak_onset_signal(-28, 1.0)
    audio = np.atleast_2d(mono)
    _, times, mask = gate.analyze(mono, SR, use_ai=False)

    doc = EditDocument(sample_rate=SR, duration=len(mono) / SR)
    doc.speech_guards = gate.speech_guards(times, mask)
    ps, pe = marks["pause"]
    # Malicious/mistaken edit: pause extended to swallow the onset and phrase start.
    doc.pauses = [Region(start=ps, end=marks["phrase"][0] + 0.5, reduction_db=-60.0)]
    out = render.render(audio, SR, doc)

    s, e = marks["onset"]
    seg = slice(int(s * SR), int(e * SR))
    ratio = _rms(out[0, seg]) / (_rms(audio[0, seg]) + 1e-12)
    assert ratio >= 0.9, "render let an edited pause mute guarded speech"
    # And the legitimate part of the pause is still attenuated.
    mid = slice(int((ps + 0.35) * SR), int((pe - 0.35) * SR))
    assert _rms(out[0, mid]) < _rms(audio[0, mid])


def test_breath_beside_voiced_consonant_does_not_dim_the_word():
    """A breath directly before a word: reduction must not leak into the word."""
    parts = [
        ("lead", _voice_burst(0.8, -18, seed=31)),
        ("gap", _silence(0.5, seed=32)),
        ("breath", _breath_burst(0.3, -36, seed=33)),
        ("microgap", _silence(0.03, seed=34)),
        ("word", _voice_burst(0.8, -22, seed=35)),
        ("tail", _silence(0.5, seed=36)),
    ]
    marks, chunks, t = {}, [], 0.0
    for name, x in parts:
        marks[name] = (t, t + len(x) / SR)
        t += len(x) / SR
        chunks.append(x)
    mono = np.concatenate(chunks).astype(np.float32)
    audio = np.atleast_2d(mono)

    doc = analyze(audio, SR, Settings.for_mode("voice"))
    doc.gain_curve, doc.sibilants = [], []
    out = render.render(audio, SR, doc)

    s, e = marks["word"]
    seg = slice(int(s * SR), int((s + 0.15) * SR))  # the word's onset
    ratio = _rms(out[0, seg]) / (_rms(audio[0, seg]) + 1e-12)
    assert ratio >= 0.9, f"breath reduction dimmed the word onset: kept {ratio:.2%}"
