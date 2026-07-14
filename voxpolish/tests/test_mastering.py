"""Balance and mastering contract tests (handoff spec, all synthetic audio)."""

import numpy as np

from conftest import SR, _silence, _voice_burst
from voxpolish import measure
from voxpolish.document import EditDocument
from voxpolish.pipeline import Settings, analyze, compute_balance
from voxpolish.stages import master, render


def _band_noise(dur_s, rms_db, lo=100, hi=8000, seed=0):
    """Continuous band-limited noise at an exact RMS level, music-bed stand-in."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * SR)
    x = rng.standard_normal(n)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    spec[(freqs < lo) | (freqs > hi)] = 0
    x = np.fft.irfft(spec, n)
    x /= np.sqrt(np.mean(x**2)) + 1e-12
    return (x * 10 ** (rms_db / 20)).astype(np.float32)[None, :]


def _shimmer_like():
    """Sparse quiet vocal over separation bleed: the Shimmer failure shape.

    20% real silence, mostly low-level bleed, five short -30 dB phrases.
    Returns (mono audio, list of phrase (start, end) marks).
    """
    rng = np.random.default_rng(7)
    parts, marks, t = [], [], 0.0

    def add(x, is_phrase=False):
        nonlocal t
        if is_phrase:
            marks.append((t, t + len(x) / SR))
        t += len(x) / SR
        parts.append(x)

    add(rng.standard_normal(int(2.0 * SR)) * 10 ** (-80 / 20))  # true silence
    for i in range(5):
        add(rng.standard_normal(int(1.6 * SR)) * 10 ** (-50 / 20))  # bleed
        add(_voice_burst(0.5, -30, seed=40 + i), is_phrase=True)
    add(rng.standard_normal(int(1.0 * SR)) * 10 ** (-50 / 20))
    return np.concatenate(parts).astype(np.float32), marks


# ---------------------------------------------------------------- dynamics


def test_shimmer_like_vocal_is_not_buried():
    mono, marks = _shimmer_like()
    audio = np.atleast_2d(mono)
    doc = analyze(audio, SR, Settings.for_mode("song"))
    doc.pauses, doc.breaths, doc.sibilants = [], [], []  # isolate leveling
    out = render.render(audio, SR, doc)

    info = doc.analysis["dynamics"]
    assert info["target_db"] > -36, f"bleed-poisoned target: {info['target_db']}"

    shifts = []
    for s, e in marks:
        seg = slice(int((s + 0.05) * SR), int((e - 0.05) * SR))
        before = 20 * np.log10(np.sqrt(np.mean(audio[0, seg] ** 2)) + 1e-12)
        after = 20 * np.log10(np.sqrt(np.mean(out[0, seg] ** 2)) + 1e-12)
        shifts.append(after - before)
    mean_shift = float(np.mean(shifts))
    assert abs(mean_shift) < 1.5, f"vocal level moved {mean_shift:+.1f} dB"


def test_dynamics_reports_target_method(speech_signal):
    mono, sr, _ = speech_signal
    doc = analyze(np.atleast_2d(mono), sr, Settings.for_mode("voice"))
    info = doc.analysis["dynamics"]
    assert info["target_method"] in ("gated-median", "sanity-fallback")
    assert "median_shift_correction_db" in info


# ---------------------------------------------------------------- measurement


def test_active_measurement_excludes_instrumental_intro():
    intro = _band_noise(6.0, -10, seed=1)  # loud intro, no vocals
    bed = _band_noise(8.0, -24, seed=2)  # quiet bed under the vocals
    instr = np.concatenate([intro, bed], axis=1)
    active = [[6.0, 14.0]]

    act_val, basis = measure.active_lufs(instr, SR, active)
    full_val = measure.integrated_lufs(instr, SR)
    assert basis == "active"
    assert act_val < full_val - 3, "active measurement must ignore the loud intro"


def test_short_active_time_falls_back_to_full():
    bed = _band_noise(8.0, -20, seed=3)
    val, basis = measure.active_lufs(bed, SR, [[0.0, 1.0]])
    assert basis == "full" and val is not None


def test_true_peak_sees_intersample_overs():
    x = _band_noise(2.0, -12, lo=8000, hi=18000, seed=4)
    assert measure.true_peak_db(x, SR) >= 20 * np.log10(np.max(np.abs(x)))


# ---------------------------------------------------------------- balance


def test_already_balanced_needs_near_zero_correction():
    vocal = _band_noise(10.0, -18, lo=300, hi=3000, seed=5)
    instr = _band_noise(10.0, -21, seed=6)
    bal = compute_balance(vocal, vocal, instr, SR, [[0.0, 10.0]])
    assert abs(bal["vocal_gain_db"]) < 0.5
    assert abs(bal["instr_gain_db"]) < 0.5


def test_balance_restores_cleaning_drift():
    raw = _band_noise(10.0, -18, lo=300, hi=3000, seed=7)
    cleaned = raw * 10 ** (-4 / 20)  # cleaning dropped the vocal 4 dB
    instr = _band_noise(10.0, -21, seed=8)
    bal = compute_balance(raw, cleaned, instr, SR, [[0.0, 10.0]])
    assert 2.9 <= bal["vocal_gain_db"] <= 3.0, "vocal correction capped at bound"
    assert -1.2 <= bal["instr_gain_db"] <= -0.8, "remainder moves the instrumental"
    assert abs(bal["residual_db"]) < 0.2


def test_balance_bounds_and_residual_reporting():
    raw = _band_noise(10.0, -18, lo=300, hi=3000, seed=9)
    cleaned = raw * 10 ** (-10 / 20)  # pathological 10 dB drop
    instr = _band_noise(10.0, -21, seed=10)
    bal = compute_balance(raw, cleaned, instr, SR, [[0.0, 10.0]])
    assert bal["vocal_gain_db"] == 3.0
    assert bal["instr_gain_db"] == -2.0
    assert 4.5 <= bal["residual_db"] <= 5.5
    assert "reason" in bal


# ---------------------------------------------------------------- mastering


def test_final_loudness_consistency_across_inputs():
    finals = []
    for rms, seed in ((-21, 11), (-16, 12), (-11, 13)):
        out, report = master.master(_band_noise(10.0, rms, seed=seed), SR)
        assert report["target_reached"], report["reasons"]
        finals.append(report["final_lufs"])
    for v in finals:
        assert abs(v - (-15.0)) <= 1.0
    assert max(finals) - min(finals) <= 1.5


def test_loud_live_recording_is_turned_down():
    hot = _band_noise(10.0, -10, seed=14)
    out, report = master.master(hot, SR)
    assert report["gain_applied_db"] < 0
    assert report["final_true_peak_dbtp"] <= -3.0 + 0.1
    assert abs(report["final_lufs"] - (-15.0)) <= 1.0


def test_beyond_gain_bound_is_a_reported_miss_not_a_crush():
    """Hotter than the gain bound can reach: quality preserved, miss reported."""
    very_hot = _band_noise(10.0, -6, seed=17)
    out, report = master.master(very_hot, SR)
    assert report["gain_applied_db"] == -8.0
    assert not report["target_reached"]
    assert any("clamped" in r for r in report["reasons"])


def test_true_peak_ceiling_is_enforced():
    # Bright content whose peaks land near the ceiling after +gain.
    x = _band_noise(8.0, -19, lo=4000, hi=16000, seed=15)
    out, report = master.master(x, SR)
    assert measure.true_peak_db(out, SR) <= -3.0 + 0.1
    assert report["final_true_peak_dbtp"] <= -3.0 + 0.1


def test_high_dynamic_range_source_is_protected():
    """Quiet bed + huge transients: limiter GR stays bounded, miss is reported."""
    rng = np.random.default_rng(16)
    x = (_band_noise(10.0, -30, seed=16)).copy()
    for pos in np.linspace(0.5, 9.5, 8):
        i = int(pos * SR)
        x[0, i : i + 40] = 0.9 * np.sign(rng.standard_normal(40))
    out, report = master.master(x, SR)
    assert report["limiter_max_gr_db"] <= 3.6, "limiter crushed beyond its bound"
    assert measure.true_peak_db(out, SR) <= -3.0 + 0.1
    assert not report["target_reached"]
    assert report["reasons"], "a bounded miss must be reported"


# ---------------------------------------------------------------- contracts


def test_master_report_does_not_affect_render(speech_signal):
    mono, sr, _ = speech_signal
    audio = np.atleast_2d(mono)
    doc = analyze(audio, sr, Settings.for_mode("voice"))
    a = render.render(audio, sr, doc)
    doc.analysis["master"] = {"final_lufs": -15.0}
    doc.analysis["balance"] = {"vocal_gain_db": 1.0}
    b = render.render(audio, sr, doc)
    assert np.array_equal(a, b), "reports are documentation, never processing"


def test_reports_survive_document_roundtrip(tmp_path, speech_signal):
    mono, sr, _ = speech_signal
    doc = analyze(np.atleast_2d(mono), sr, Settings.for_mode("voice"))
    doc.analysis["balance"] = {"vocal_gain_db": 1.5, "method": "measured"}
    doc.analysis["master"] = {"final_lufs": -15.1, "target_reached": True,
                              "reasons": []}
    path = tmp_path / "doc.json"
    doc.save(path)
    loaded = EditDocument.load(path)
    assert loaded.analysis["balance"] == doc.analysis["balance"]
    assert loaded.analysis["master"] == doc.analysis["master"]
