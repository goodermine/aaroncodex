"""Pitch analysis tests: tracking, key detection, correction proposals."""

import numpy as np

from voxpolish.stages import pitch

SR = 44100


def _tone(freq, dur_s, amp=0.2, vibrato_hz=0.0, vibrato_cents=0.0):
    t = np.arange(int(dur_s * SR)) / SR
    f = freq * 2 ** (vibrato_cents / 1200 * np.sin(2 * np.pi * vibrato_hz * t))
    phase = 2 * np.pi * np.cumsum(f) / SR
    x = amp * np.sin(phase)
    fade = int(0.01 * SR)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x


def _gap(dur_s):
    return np.zeros(int(dur_s * SR))


def test_tracker_finds_a_pure_tone():
    x = _tone(220.0, 1.0)
    times, f0, conf = pitch.track(x, SR)
    voiced = f0 > 0
    assert voiced.mean() > 0.8
    assert abs(np.median(f0[voiced]) - 220.0) < 2.0
    assert np.median(conf[voiced]) > 0.8


def test_tracker_handles_vibrato():
    x = _tone(330.0, 1.5, vibrato_hz=5.5, vibrato_cents=30)
    _, f0, _ = pitch.track(x, SR)
    voiced = f0 > 0
    assert abs(np.median(f0[voiced]) - 330.0) < 4.0


def test_noise_is_unvoiced():
    rng = np.random.default_rng(1)
    x = rng.standard_normal(SR) * 0.05
    _, f0, _ = pitch.track(x, SR)
    assert (f0 > 0).mean() < 0.2


def test_key_detection_on_a_major_ish_line():
    # A line built from C major tones: C4 E4 G4 A4 F4 D4 C4.
    freqs = [261.63, 329.63, 392.0, 440.0, 349.23, 293.66, 261.63]
    x = np.concatenate([_tone(f, 0.45) for f in freqs])
    _, f0, _ = pitch.track(x, SR)
    tonic, mode, conf = pitch.estimate_key(f0)
    # C major and its relative A minor share pitches; both are correct.
    assert (tonic, mode) in ((0, "major"), (9, "minor"))
    assert conf > 0.5


def test_flat_note_gets_a_sharpening_proposal():
    # A4 sung 40 cents flat, in an A-minor context.
    flat_a = 440.0 * 2 ** (-40 / 1200)
    x = np.concatenate([_tone(440.0, 0.5), _gap(0.2), _tone(flat_a, 0.8), _gap(0.2)])
    report = pitch.analyze(x, SR, strength=0.5, key=(9, "minor"))

    flat_notes = [n for n in report["notes"] if n["start"] > 0.6]
    assert flat_notes, "the flat note must be segmented"
    n = flat_notes[0]
    assert n["note"].startswith("A")
    assert -50 < n["mean_dev_cents"] < -25, f"deviation {n['mean_dev_cents']}"
    # Proposed correction pulls UP (sharpening), scaled by strength.
    assert 10 < n["proposed_cents"] < 30


def test_in_tune_note_gets_near_zero_proposal():
    x = _tone(440.0, 1.0)
    report = pitch.analyze(x, SR, strength=0.5, key=(9, "minor"))
    assert report["notes"], "the note must be found"
    assert abs(report["notes"][0]["proposed_cents"]) < 8


def test_correction_is_capped_and_subtle():
    # A quarter-tone (50 cents) off at full strength still stays bounded.
    off = 440.0 * 2 ** (55 / 1200)
    x = _tone(off, 1.0)
    report = pitch.analyze(x, SR, strength=1.0, max_cents=100.0, key=(9, "minor"))
    for _, cents in report["curve"]:
        assert abs(cents) <= 100.0


def test_report_shape_is_serializable():
    import json

    x = np.concatenate([_tone(261.63, 0.5), _gap(0.3), _tone(392.0, 0.5)])
    report = pitch.analyze(x, SR)
    text = json.dumps(report)
    assert json.loads(text)["voiced_seconds"] > 0.5
    assert {"key", "notes", "curve", "mean_abs_dev_cents"} <= set(report)
