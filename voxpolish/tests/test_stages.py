"""Module-level tests against the synthetic phrase signal."""

import numpy as np

from voxpolish import dsp
from voxpolish.stages import breath, dynamics, gate, sibilance


def _overlaps(regions, start, end):
    return [r for r in regions if r.start < end and r.end > start]


def test_gate_finds_pauses_not_phrases(speech_signal):
    mono, sr, marks = speech_signal
    pauses, times, mask = gate.analyze(mono, sr, use_ai=False)

    assert _overlaps(pauses, *marks["pause2"]), "the long pause should be gated"
    for phrase in ("phrase_loud", "phrase_quiet", "phrase_mid"):
        s, e = marks[phrase]
        # No pause region may cover the middle of a phrase.
        mid = (s + e) / 2
        assert not _overlaps(pauses, mid - 0.1, mid + 0.1), f"gate ate {phrase}"


def test_gate_speech_mask_covers_phrases(speech_signal):
    mono, sr, marks = speech_signal
    _, times, mask = gate.analyze(mono, sr, use_ai=False)
    for phrase in ("phrase_loud", "phrase_mid"):
        s, e = marks[phrase]
        frames = (times > s + 0.1) & (times < e - 0.1)
        assert mask[frames].mean() > 0.9


def test_dynamics_levels_the_quiet_phrase(speech_signal):
    mono, sr, marks = speech_signal
    _, times, mask = gate.analyze(mono, sr, use_ai=False)
    curve, info = dynamics.analyze(
        mono, sr, speech_times=times, speech_mask=mask, smoothing=1.0
    )
    curve = np.asarray(curve)

    def mean_gain(seg):
        s, e = marks[seg]
        sel = (curve[:, 0] > s + 0.2) & (curve[:, 0] < e - 0.2)
        return curve[sel, 1].mean()

    # Quiet phrase (-30 dB) should be boosted well above the loud one (-14 dB).
    assert mean_gain("phrase_quiet") > mean_gain("phrase_loud") + 6
    # The loud phrase sits above target, so it should not be boosted.
    assert mean_gain("phrase_loud") <= 1.0


def test_dynamics_reduces_level_spread(speech_signal):
    mono, sr, marks = speech_signal
    _, times, mask = gate.analyze(mono, sr, use_ai=False)
    curve, _ = dynamics.analyze(mono, sr, speech_times=times, speech_mask=mask, smoothing=1.0)
    curve = np.asarray(curve)

    t = np.arange(len(mono)) / sr
    gain_db = np.interp(t, curve[:, 0], curve[:, 1])
    leveled = mono * 10 ** (gain_db / 20)

    def phrase_levels(x):
        out = []
        for p in ("phrase_loud", "phrase_quiet", "phrase_mid"):
            s, e = marks[p]
            seg = x[int((s + 0.2) * sr) : int((e - 0.2) * sr)]
            out.append(20 * np.log10(np.sqrt(np.mean(seg**2)) + 1e-12))
        return np.array(out)

    before, after = phrase_levels(mono), phrase_levels(leveled)
    # The +6 dB boost ceiling caps how far a 16 dB spread can close: the
    # -30 dB phrase may rise at most 6 dB. Spread must still shrink markedly.
    assert after.std() < before.std() - 2.0, f"spread {before.std():.1f} -> {after.std():.1f} dB"
    gain_max = curve[:, 1].max()
    assert gain_max <= 6.05, f"boost ceiling violated: +{gain_max:.2f} dB"


def test_sibilance_detects_the_s_burst(speech_signal):
    mono, sr, marks = speech_signal
    _, times, mask = gate.analyze(mono, sr, use_ai=False)
    events = sibilance.analyze(mono, sr, speech_times=times, speech_mask=mask)
    hits = _overlaps(events, *marks["sibilant"])
    assert hits, "the 5-9 kHz burst should be flagged as sibilant"
    assert all(h.reduction_db < 0 and h.band for h in hits)
    # Voiced phrases (300-3000 Hz) must not be flagged.
    for phrase in ("phrase_loud", "phrase_mid"):
        s, e = marks[phrase]
        mid = (s + e) / 2
        assert not _overlaps(events, mid - 0.2, mid + 0.2)


def test_breath_detects_the_breath(speech_signal):
    mono, sr, marks = speech_signal
    _, times, mask = gate.analyze(mono, sr, use_ai=False)
    regions = breath.analyze(mono, sr, times, mask)
    assert _overlaps(regions, *marks["breath"]), "the breath burst should be found"
    for phrase in ("phrase_loud", "phrase_quiet", "phrase_mid"):
        s, e = marks[phrase]
        mid = (s + e) / 2
        assert not _overlaps(regions, mid - 0.2, mid + 0.2), f"breath flagged inside {phrase}"


def test_band_split_reconstructs(speech_signal):
    mono, sr, _ = speech_signal
    seg = mono[: sr // 2].astype(np.float64)
    low, high = dsp.band_split(seg, sr, 4000)
    assert np.allclose(low + high, seg, atol=1e-9)
