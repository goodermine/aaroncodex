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


def test_tracker_survives_sub_floor_content():
    """Field crash (IndexError): content near/below the 75 Hz floor pushes
    the CMNDF minimum to the search boundary, where unclamped parabolic
    interpolation walked past the end of the array."""
    x = _tone(60.0, 1.0)  # below FMIN: the pathological case
    times, f0, conf = pitch.track(x, SR)  # must not raise
    voiced = f0 > 0
    if voiced.any():
        assert f0[voiced].min() >= pitch.FMIN * 0.9
        assert f0[voiced].max() <= pitch.FMAX * 1.1


def test_tracker_survives_hostile_signals():
    """Fuzz: mixed low rumble, clicks, DC, silence — never raises, always sane."""
    rng = np.random.default_rng(9)
    rumble = _tone(55.0, 0.8, amp=0.3)
    clicks = np.zeros(int(0.8 * SR), dtype=np.float32)
    clicks[:: SR // 13] = 0.9
    dc = np.full(int(0.5 * SR), 0.1, dtype=np.float32)
    noise = (rng.standard_normal(int(0.8 * SR)) * 0.2).astype(np.float32)
    hostile = np.concatenate([rumble, clicks, dc, noise, _tone(200.0, 0.6)])
    times, f0, conf = pitch.track(hostile, SR)  # must not raise
    voiced = f0 > 0
    assert np.all(np.isfinite(f0)) and np.all(np.isfinite(conf))
    if voiced.any():
        assert f0[voiced].min() >= pitch.FMIN * 0.9
        assert f0[voiced].max() <= pitch.FMAX * 1.1


def test_analyze_survives_sub_floor_content():
    """The full CLI path that crashed in the field must complete."""
    x = np.concatenate([_tone(60.0, 0.8), _gap(0.2), _tone(220.0, 0.8)])
    report = pitch.analyze(x, SR)  # must not raise
    assert "key" in report and "curve" in report


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
    assert {"key", "notes", "curve", "track", "mean_abs_dev_cents"} <= set(report)


def test_track_gives_sung_pitch_and_correction():
    """The pitch lane needs [time, sung_midi, correction_cents] per voiced frame."""
    flat = 440.0 * 2 ** (-40 / 1200)
    x = _tone(flat, 1.2)
    report = pitch.analyze(x, SR, strength=1.0, retune_ms=40.0, key=(9, "minor"))
    track = report["track"]
    assert track and all(len(pt) == 3 for pt in track)
    # Sung MIDI sits just under A4 (69); correction pulls up (positive cents).
    sung = np.array([m for _, m, _ in track])
    corr = np.array([c for _, _, c in track])
    assert 68.0 < np.median(sung) < 69.0
    assert np.max(corr) > 5.0, "a 40-cent-flat note should propose upward cents"


def test_track_is_downsampled_on_long_input():
    x = _tone(220.0, 20.0)  # long steady tone
    report = pitch.analyze(x, SR)
    assert len(report["track"]) <= 1900  # capped for JSON size
