"""Backing swap: clean-track alignment against a room-captured backing (synthetic)."""

import numpy as np
import pytest
import soundfile as sf
from scipy import signal

from conftest import SR
from voxpolish import audio_io
from voxpolish.document import EditDocument
from voxpolish.pipeline import Settings, process
from voxpolish.stages import align, separation


def _track(dur_s=40.0, seed=0):
    """A non-repeating 'karaoke track': random drum-like hits over a soft pad."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * SR)
    x = 0.02 * rng.standard_normal(n)
    t = 0.0
    while t < dur_s - 0.2:
        s = int(t * SR)
        hit = rng.standard_normal(int(0.08 * SR)) * np.exp(-np.linspace(0, 8, int(0.08 * SR)))
        x[s:s + len(hit)] += 0.4 * hit
        t += rng.uniform(0.15, 0.45)
    return np.vstack([x, x]).astype(np.float32)


def _room_capture(clean, offset_s, total_s, seed=1):
    """The clean track as a phone in a room hears it: late, dull, quieter, noisy."""
    placed = align.place(clean, SR, offset_s, int(total_s * SR), 2)
    sos = signal.butter(4, 3500 / (SR / 2), output="sos")
    dull = signal.sosfilt(sos, placed, axis=1) * 0.25
    smear = signal.fftconvolve(dull, np.exp(-np.linspace(0, 10, int(0.05 * SR)))[None, :] * 0.02,
                               axes=1)[:, : dull.shape[1]]
    rng = np.random.default_rng(seed)
    return (dull + smear + 0.003 * rng.standard_normal(dull.shape)).astype(np.float32)


def test_finds_a_known_offset_through_a_room():
    clean = _track()
    captured = _room_capture(clean, 3.217, 48.0)
    rep = align.find_offset(clean, captured, SR)
    assert rep["offset_s"] == pytest.approx(3.217, abs=0.005)
    assert "warning" not in rep


def test_track_started_before_the_recording():
    clean = _track()
    captured = _room_capture(clean, -2.0, 30.0)
    assert align.find_offset(clean, captured, SR)["offset_s"] == pytest.approx(-2.0, abs=0.005)


def test_speed_drift_is_reported():
    clean = _track()
    faster = signal.resample(clean, int(clean.shape[1] / 1.004), axis=1).astype(np.float32)
    captured = _room_capture(faster, 1.0, 45.0)
    rep = align.find_offset(clean, captured, SR)
    assert rep["drift_spread_s"] > align.DRIFT_WARN_S
    assert "warning" in rep


def test_place_pads_and_crops():
    clean = np.ones((2, SR), dtype=np.float32)
    out = align.place(clean, SR, 0.5, 2 * SR, 2)
    assert out[:, : SR // 2].sum() == 0 and out[:, SR // 2 : SR // 2 + SR].min() == 1
    early = align.place(clean, SR, -0.25, SR, 2)
    assert early[:, : int(0.75 * SR)].min() == 1 and early[:, int(0.75 * SR) :].sum() == 0


def test_pipeline_swaps_in_the_clean_backing(tmp_path, monkeypatch):
    clean = _track(30.0, seed=4)
    captured = _room_capture(clean, 2.5, 34.0)
    rng = np.random.default_rng(5)
    vocal = (0.05 * rng.standard_normal(captured.shape)).astype(np.float32)
    clean_path = tmp_path / "karaoke.wav"
    sf.write(clean_path, clean.T, SR)
    src = tmp_path / "take.wav"
    sf.write(src, (vocal + captured).T, SR)
    monkeypatch.setattr(separation, "available", lambda: True)
    monkeypatch.setattr(separation, "separate",
                        lambda path, model=None, shifts=1: (vocal, captured, SR))

    s = Settings.for_mode("song")
    s.backing_path = str(clean_path)
    out = process(src, tmp_path / "o", s)

    # The written instrumental IS the clean track (not the dull capture), placed
    # within a few ms of where it really plays.
    inst, _ = audio_io.load(out["instrumental"])
    expected = align.place(clean, SR, 2.5, captured.shape[1], 2)
    seg = slice(5 * SR, 15 * SR)
    xc = signal.fftconvolve(inst[0, seg], expected[0, seg][::-1])
    lag_s = (np.argmax(xc) - (seg.stop - seg.start - 1)) / SR
    assert abs(lag_s) < 0.005
    peak = xc.max() / (np.linalg.norm(inst[0, seg]) * np.linalg.norm(expected[0, seg]))
    assert peak > 0.99
    rep = EditDocument.load(out["edit_document"]).analysis["backing"]
    assert rep["offset_s"] == pytest.approx(2.5, abs=0.005)


def test_backing_needs_song_mode(tmp_path):
    src = tmp_path / "talk.wav"
    sf.write(src, np.zeros(2 * SR, dtype=np.float32), SR)
    s = Settings.for_mode("voice")
    s.backing_path = str(src)
    with pytest.raises(ValueError, match="song"):
        process(src, tmp_path / "o", s)
