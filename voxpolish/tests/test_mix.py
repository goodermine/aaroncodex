"""Mix stage (Phase 2) contract tests — all synthetic audio, no models."""

import json

import numpy as np
import pytest
import soundfile as sf

from conftest import SR, _sibilant_burst, _silence, _voice_burst
from voxpolish import audio_io, cli, measure
from voxpolish.document import EditDocument
from voxpolish.pipeline import Settings, process
from voxpolish.stages import mix, separation


def _shaped_noise(dur_s, tilt_db_per_oct, level_db=-20.0, seed=0, top_hz=None):
    """Voice-like noise (120 Hz - top) with a spectral tilt relative to 700 Hz."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * SR)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    shape = np.zeros_like(f)
    band = (f >= 120) & (f <= (top_hz or SR / 2))
    shape[band] = 10 ** (tilt_db_per_oct * np.log2(f[band] / 700.0) / 20)
    x = np.fft.irfft(spec * shape, n)
    x /= np.sqrt(np.mean(x**2)) + 1e-12
    return (x * 10 ** (level_db / 20)).astype(np.float32)[None, :]


def _phrases(dur_s=12.0, **kw):
    """Phrases with short gaps, so there is vocal-active audio to measure."""
    x = _shaped_noise(dur_s, **kw)
    env = np.ones(x.shape[1])
    for start in np.arange(1.5, dur_s, 2.0):
        s = int(start * SR)
        env[s:s + int(0.3 * SR)] = 1e-3
    # 20 ms ramps: hard steps would be clicks, splashing energy above 16 kHz.
    ramp = np.hanning(int(0.02 * SR))
    env = np.convolve(env, ramp / ramp.sum(), mode="same")
    return (x * env[None, :]).astype(np.float32)


# ----------------------------------------------------------------- tone


def test_dark_vocal_gets_presence_and_air_within_bounds():
    dark = _phrases(tilt_db_per_oct=-9.0)
    plan = mix.plan_tone(mix.tone_profile(dark, SR))
    gains = {b["label"]: b["gain_db"] for b in plan["bands"]}
    assert 0 < gains["presence"] <= mix.TONE_BOUNDS["presence_boost_db"]
    assert 0 < gains["air"] <= mix.TONE_BOUNDS["air_boost_db"]
    assert gains["mud"] <= 0


def test_bright_vocal_is_not_brightened():
    bright = _phrases(tilt_db_per_oct=0.0)
    gains = {b["label"]: b["gain_db"] for b in mix.plan_tone(mix.tone_profile(bright, SR))["bands"]}
    assert gains["presence"] <= 0
    assert gains["air"] <= 0
    assert gains["presence"] >= -mix.TONE_BOUNDS["presence_cut_db"]


def test_bandwidth_limited_source_caps_the_air_shelf():
    """An MP3-style low-pass leaves nothing up top to lift but codec noise."""
    mp3ish = _phrases(tilt_db_per_oct=-9.0, top_hz=15000)
    plan = mix.plan_tone(mix.tone_profile(mp3ish, SR))
    air = next(b["gain_db"] for b in plan["bands"] if b["label"] == "air")
    assert air <= mix.AIR_LIMITED_MAX_BOOST_DB
    assert any("bandwidth-limited" in n for n in plan["notes"])


def test_eq_moves_the_measured_profile_toward_target():
    dark = _phrases(tilt_db_per_oct=-9.0)
    before = mix.tone_profile(dark, SR)
    after = mix.tone_profile(mix.apply_eq(dark, SR, mix.plan_tone(before)), SR)
    assert after["presence_db"] > before["presence_db"] + 2
    assert after["air_db"] > before["air_db"] + 2


def test_highpass_removes_rumble():
    t = np.arange(2 * SR) / SR
    rumble = (0.3 * np.sin(2 * np.pi * 40 * t))[None, :]
    out = mix.apply_eq(rumble, SR, {"highpass_hz": 85.0, "bands": []})
    tail = slice(SR // 2, None)  # skip the filter's settling time
    drop = 20 * np.log10(np.abs(out[0, tail]).max() / np.abs(rumble[0, tail]).max())
    assert drop < -10


# ------------------------------------------------------------- dynamics


def test_compressor_narrows_loud_quiet_spread_and_is_deterministic():
    loud = _voice_burst(1.0, -8, seed=1)
    quiet = _voice_burst(1.0, -28, seed=2)
    x = np.concatenate([loud, _silence(0.3), quiet, _silence(0.3), loud]).astype(np.float32)[None, :]
    out, rep = mix.compress(x, SR, threshold_db=-24, ratio=3, attack_ms=8, release_ms=120)
    out2, _ = mix.compress(x, SR, threshold_db=-24, ratio=3, attack_ms=8, release_ms=120)
    assert np.array_equal(out, out2)

    def spread(a):
        n = SR
        return 20 * np.log10(np.std(a[0, :n]) / np.std(a[0, n + int(0.3 * SR): 2 * n + int(0.3 * SR)]))
    assert spread(out) < spread(x) - 6
    assert rep["max_gr_db"] > 3


def test_vocal_chain_is_loudness_neutral():
    v = _phrases(tilt_db_per_oct=-6.0)
    s = Settings.for_mode("song")
    s.mix_reverb_db = s.mix_delay_db = None
    plan = mix.analyze(v, SR, None, [], s)
    out, rep = mix.render_vocal(v, SR, plan, [])
    assert abs(measure.integrated_lufs(out, SR) - measure.integrated_lufs(v, SR)) < 0.5


def test_deesser_cuts_sibilants_not_vowels():
    vowel = _voice_burst(0.6, -18, seed=3)
    ess = _sibilant_burst(0.15, -18, seed=4)
    x = np.concatenate([vowel, ess, vowel]).astype(np.float32)[None, :]
    out, rep = mix.deess(x, SR, max_reduction_db=6.0)
    v = slice(int(0.1 * SR), int(0.5 * SR))
    e = slice(int(0.62 * SR), int(0.73 * SR))
    db = lambda a, s: 20 * np.log10(np.std(a[0, s]) + 1e-12)  # noqa: E731
    assert abs(db(out, v) - db(x, v)) < 0.5, "vowels must pass untouched"
    assert db(out, e) < db(x, e) - 2, "the 's' must come down"
    assert rep["max_reduction_db"] <= 6.0 + 1e-6


# ----------------------------------------------------------------- space


def _space_params(**over):
    p = {"reverb": {"on": True, "rt60_s": 1.0, "predelay_ms": 20.0, "hp_hz": 250.0,
                    "lp_hz": 7000.0, "level_db": -18.0, "seed": 7},
         "delay": {"on": False}}
    p["reverb"].update(over)
    return p


def test_reverb_is_deterministic_and_leaves_a_tail():
    burst = np.concatenate([_voice_burst(1.0, -18, seed=5), _silence(1.5)]).astype(np.float32)[None, :]
    a, _ = mix.space(burst, SR, _space_params(), [])
    b, _ = mix.space(burst, SR, _space_params(), [])
    assert np.array_equal(a, b)
    after = slice(int(1.1 * SR), int(1.5 * SR))
    assert np.std(a[0, after]) > 10 * np.std(burst[0, after])


def test_reverb_send_level_is_relative_to_the_dry_vocal():
    v = _phrases(tilt_db_per_oct=-6.0)
    out, _ = mix.space(v, SR, _space_params(level_db=-18.0), [])
    wet = out - v
    rel = measure.integrated_lufs(wet, SR) - measure.integrated_lufs(v, SR)
    assert abs(rel - (-18.0)) < 1.0


def test_tempo_estimate_finds_a_click_track():
    bpm = 120.0
    x = np.zeros(int(12 * SR))
    for k in range(int(12 * bpm / 60)):
        s = int(k * 60 / bpm * SR)
        x[s:s + 200] = np.hanning(200)
    est, conf = mix.estimate_tempo(x[None, :], SR)
    assert est is not None and conf > 0.2
    assert min(abs(est - bpm), abs(est - bpm / 2), abs(est - bpm * 2)) < 2


# --------------------------------------------------------------- balance


def test_forward_balance_seats_the_vocal_above_the_backing():
    v = _phrases(tilt_db_per_oct=-6.0, level_db=-16.0)
    i = _shaped_noise(12.0, -3.0, level_db=-30.0, seed=9)
    rep = mix.compute_forward_balance(v, i, SR, [], vocal_forward_db=3.0)
    vv = v * 10 ** (rep["vocal_gain_db"] / 20)
    ii = i * 10 ** (rep["instr_gain_db"] / 20)
    ratio = measure.integrated_lufs(vv, SR) - measure.integrated_lufs(ii, SR)
    assert abs(ratio - 3.0) < 0.2
    assert rep["instr_gain_db"] > 0, "a buried backing comes up; the vocal is not cut"


def test_forward_balance_reports_rather_than_forces_a_miss():
    v = _phrases(tilt_db_per_oct=-6.0, level_db=-10.0)
    i = _shaped_noise(12.0, -3.0, level_db=-50.0, seed=9)
    rep = mix.compute_forward_balance(v, i, SR, [], vocal_forward_db=3.0,
                                      max_instr_db=9.0, max_vocal_db=3.0)
    assert rep["instr_gain_db"] == pytest.approx(9.0)
    assert rep["vocal_gain_db"] == pytest.approx(-3.0)
    assert abs(rep["residual_db"]) > 1 and "reason" in rep


# -------------------------------------------------------------- pipeline


@pytest.fixture
def song(tmp_path, monkeypatch):
    """A 14 s 'song': phrases over a quiet bed, separation served from the stems."""
    vocal = np.repeat(_phrases(14.0, tilt_db_per_oct=-8.0, level_db=-18.0), 2, axis=0)
    instr = np.repeat(_shaped_noise(14.0, -4.0, level_db=-30.0, seed=11), 2, axis=0)
    src = tmp_path / "song.wav"
    sf.write(src, (vocal + instr).T, SR)
    monkeypatch.setattr(separation, "available", lambda: True)
    monkeypatch.setattr(separation, "separate",
                        lambda path, model=None, shifts=1: (vocal, instr, SR))
    return src


def test_default_settings_leave_the_phase1_output_unchanged(song, tmp_path):
    out = process(song, tmp_path / "o", Settings.for_mode("song"))
    assert "vocal_produced" not in out
    assert EditDocument.load(out["edit_document"]).mix == {}


def test_produce_preset_end_to_end(song, tmp_path):
    out = process(song, tmp_path / "o", Settings.for_mode("song").produce())
    assert {"vocal_produced", "remix"} <= set(out)
    doc = json.loads((tmp_path / "o" / "edit_document.json").read_text())
    assert doc["mix"]["balance"]["mode"] == "forward"
    assert doc["analysis"]["balance"]["method"] == "forward"
    m = doc["analysis"]["master"]
    assert abs(m["final_lufs"] - (-14.0)) <= 1.0
    assert m["final_true_peak_dbtp"] <= -1.0 + 0.05


def test_produce_rerenders_bit_identically_from_the_document(song, tmp_path):
    s = Settings.for_mode("song").produce()
    a = process(song, tmp_path / "a", s)
    doc = EditDocument.load(a["edit_document"])
    b = process(song, tmp_path / "b", s, edit_doc=doc)
    ra, _ = audio_io.load(a["remix"])
    rb, _ = audio_io.load(b["remix"])
    assert np.array_equal(ra, rb)


def test_hand_edit_to_mix_is_honored(song, tmp_path):
    s = Settings.for_mode("song").produce()
    a = process(song, tmp_path / "a", s)
    doc = EditDocument.load(a["edit_document"])
    doc.mix["bypass"]["space"] = True
    b = process(song, tmp_path / "b", s, edit_doc=doc)
    va, _ = audio_io.load(a["vocal_produced"])
    vb, _ = audio_io.load(b["vocal_produced"])
    assert not np.array_equal(va, vb)
    assert "space" not in EditDocument.load(b["edit_document"]).analysis["mix"]


def test_trim_cuts_the_intro_and_is_remembered(song, tmp_path):
    s = Settings.for_mode("song")
    s.trim_start_s = 3.0
    out = process(song, tmp_path / "o", s)
    cleaned, _ = audio_io.load(out["vocal_cleaned"])
    assert cleaned.shape[1] == int(11.0 * SR)
    assert EditDocument.load(out["edit_document"]).analysis["trim"]["start_s"] == 3.0


def test_cli_rejects_unknown_bypass_module(tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["process", "x.wav", "--mix-bypass", "tone,sparkle"])
