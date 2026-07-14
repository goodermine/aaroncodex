"""Local over-processing safety (Shimmer 00:50-01:05 findings).

Contracts:
- dynamics gain never exceeds the +6 dB boost ceiling, even after
  loudness-neutral correction;
- automation slope stays within 6 dB/s (0.6 dB per 100 ms hop);
- whole-song loudness neutrality survives the ceiling and slope limits;
- pauses cannot cover washed lyrics that sit below the detection threshold;
- low-confidence breath detections cannot punch through speech guards;
- weak sibilance evidence produces no forced minimum cut.
"""

import numpy as np

from conftest import SR, _silence, _voice_burst
from test_mastering import _active_lufs_over, _shimmer_like
from voxpolish.document import Region
from voxpolish.pipeline import Settings, analyze, confident_regions
from voxpolish.stages import gate, render, sibilance

HOP_S = 0.1


def _curve(doc):
    return np.asarray(doc.gain_curve, dtype=np.float64)


def test_boost_ceiling_holds_after_neutralization():
    """The Shimmer failure: neutralization pushed local gain to +11 dB."""
    mono, _ = _shimmer_like(phrase_levels=(-22, -40, -28, -44, -33))
    doc = analyze(np.atleast_2d(mono), SR, Settings.for_mode("song"))
    curve = _curve(doc)
    assert curve[:, 1].max() <= 6.05, f"boost reached +{curve[:, 1].max():.2f} dB"
    info = doc.analysis["dynamics"]
    assert info["gain_range_db"][1] <= 6.05


def test_gain_slope_is_bounded():
    mono, _ = _shimmer_like(phrase_levels=(-22, -40, -28, -44, -33))
    doc = analyze(np.atleast_2d(mono), SR, Settings.for_mode("song"))
    curve = _curve(doc)
    max_step = np.max(np.abs(np.diff(curve[:, 1])))
    assert max_step <= 6.0 * HOP_S + 0.01, f"gain stepped {max_step:.2f} dB per hop"
    assert doc.analysis["dynamics"]["max_slope_db_per_s"] <= 6.1


def test_neutrality_survives_ceiling_and_slope_limits():
    """Requirement 1: local safety must not undo whole-song neutrality."""
    for levels in ((-30,) * 5, (-22, -40, -28, -44, -33)):
        mono, marks = _shimmer_like(phrase_levels=levels)
        audio = np.atleast_2d(mono)
        doc = analyze(audio, SR, Settings.for_mode("song"))
        doc.pauses, doc.breaths, doc.sibilants = [], [], []
        out = render.render(audio, SR, doc)
        delta = _active_lufs_over(out[0], marks) - _active_lufs_over(mono, marks)
        assert abs(delta) <= 1.0, f"levels {levels}: moved {delta:+.2f} LU"


def test_bleed_is_not_boosted_as_vocal():
    """Leveling and neutralization only touch frames near the performance
    level: separation bleed between phrases stays essentially unboosted even
    when quiet phrases legitimately receive several dB."""
    mono, marks = _shimmer_like(phrase_levels=(-22, -40, -28, -44, -33))
    doc = analyze(np.atleast_2d(mono), SR, Settings.for_mode("song"))
    curve = _curve(doc)
    # marks[3] is the -44 dB phrase: it should get a real boost...
    quiet_gain = float(np.interp(np.mean(marks[3]), curve[:, 0], curve[:, 1]))
    assert quiet_gain > 1.0, f"quiet phrase not leveled ({quiet_gain:+.2f} dB)"
    # ...while the bleed stretch well before it stays near unity. (Up to
    # ~2 dB of smear is the slope limiter refusing to step, not leveling.)
    bleed_t = marks[2][1] + 0.8  # deep inside the bleed between phrases
    bleed_gain = float(np.interp(bleed_t, curve[:, 0], curve[:, 1]))
    assert bleed_gain <= 2.0, f"bleed boosted {bleed_gain:+.2f} dB"
    assert bleed_gain < quiet_gain - 3.0


def _washed_lyric_signal():
    """Phrase, then washed low-confidence lyrics (below the detection
    threshold, above the protection threshold), then a phrase."""
    parts = [
        ("lead", _voice_burst(1.2, -18, seed=51)),
        ("gap1", _silence(0.4, seed=52)),
        ("washed", _voice_burst(1.0, -59, seed=53)),
        ("gap2", _silence(0.4, seed=54)),
        ("phrase", _voice_burst(1.2, -20, seed=55)),
        ("tail", _silence(0.8, seed=56)),
    ]
    marks, chunks, t = {}, [], 0.0
    for name, x in parts:
        marks[name] = (t, t + len(x) / SR)
        t += len(x) / SR
        chunks.append(x)
    return np.concatenate(chunks).astype(np.float32), marks


def test_pauses_cannot_cover_washed_lyrics():
    mono, marks = _washed_lyric_signal()
    pauses, times, mask = gate.analyze(mono, SR, use_ai=False)
    ws, we = marks["washed"]
    # The detection mask misses the washed segment (that's the premise)...
    frames = (times > ws + 0.1) & (times < we - 0.1)
    assert mask[frames].mean() < 0.5, "fixture must sit below detection"
    # ...but no pause may cover it.
    for p in pauses:
        assert p.end <= ws or p.start >= we, (
            f"pause [{p.start:.2f},{p.end:.2f}] covers washed lyrics [{ws:.2f},{we:.2f}]"
        )


def test_washed_lyrics_survive_full_render():
    mono, marks = _washed_lyric_signal()
    audio = np.atleast_2d(mono)
    doc = analyze(audio, SR, Settings.for_mode("song"))
    doc.gain_curve = []  # measure protective behavior, not leveling
    out = render.render(audio, SR, doc)
    ws, we = marks["washed"]
    seg = slice(int((ws + 0.05) * SR), int((we - 0.05) * SR))
    before = np.sqrt(np.mean(audio[0, seg].astype(np.float64) ** 2))
    after = np.sqrt(np.mean(out[0, seg].astype(np.float64) ** 2))
    assert after / before >= 0.7, f"washed lyrics kept only {after / before:.0%}"


def test_low_confidence_breaths_cannot_punch_guards():
    regions = [
        Region(1.0, 1.3, -12.0, label="breath", confidence=0.9),
        Region(2.0, 2.4, -12.0, label="breath", confidence=0.2),
    ]
    punchers = confident_regions(regions)
    assert [r.start for r in punchers] == [1.0], "only high confidence may punch"


def test_breath_regions_carry_confidence(speech_signal):
    mono, sr, _ = speech_signal
    doc = analyze(np.atleast_2d(mono), sr, Settings.for_mode("voice"))
    assert doc.breaths
    for b in doc.breaths:
        assert 0.0 <= b.confidence <= 1.0


def test_sibilance_has_no_forced_minimum_cut(speech_signal):
    mono, sr, marks = speech_signal
    _, times, mask = gate.analyze(mono, sr, use_ai=False)
    events = sibilance.analyze(mono, sr, speech_times=times, speech_mask=mask)
    assert events, "the strong sibilant must still be detected"
    for ev in events:
        assert ev.reduction_db <= -1.5, "sub-threshold events must be dropped"
        assert 0.0 <= ev.confidence <= 1.0
    hits = [e for e in events if e.start < marks["sibilant"][1] and e.end > marks["sibilant"][0]]
    assert hits, "the real sibilant survived the conservatism change"


def test_region_confidence_roundtrips(tmp_path, speech_signal):
    from voxpolish.document import EditDocument

    mono, sr, _ = speech_signal
    doc = analyze(np.atleast_2d(mono), sr, Settings.for_mode("voice"))
    path = tmp_path / "doc.json"
    doc.save(path)
    loaded = EditDocument.load(path)
    assert [b.confidence for b in loaded.breaths] == [b.confidence for b in doc.breaths]
    assert [s.confidence for s in loaded.sibilants] == [s.confidence for s in doc.sibilants]
