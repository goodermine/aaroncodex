"""talk_cut: find the talking in a vocal stem and cut it before scoring."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import talk_cut as tc  # noqa: E402

FR = tc.FRAME_RATE


def _track(spans, total_s):
    """Synthetic pYIN output. spans = [(start, end, kind)], kind 'sung' holds
    a note for 0.5 s at a time, 'speech' glides continuously."""
    n = int(total_s * FR)
    f0 = np.full(n, np.nan)
    prob = np.zeros(n)
    rms = np.full(n, 1e-4)
    for start, end, kind in spans:
        a, b = int(start * FR), int(end * FR)
        t = np.arange(b - a) / FR
        if kind == "sung":
            steps = 220 * 2 ** (np.floor(t / 0.5) % 4 / 12)       # held notes, a step every 0.5 s
            f0[a:b] = steps
        else:
            f0[a:b] = 160 * 2 ** (np.sin(2 * np.pi * 3 * t) * 3 / 12)   # constant glide
        prob[a:b] = 0.9
        rms[a:b] = 0.05
    return f0, prob, rms


def _song(talk_before=(2, 10), sing=(12, 70), talk_after=(72, 78), total=80):
    spans = [(talk_before[0], talk_before[1], "speech")]
    t = sing[0]
    while t < sing[1]:                       # sung phrases with breaths between
        spans.append((t, min(t + 3.5, sing[1]), "sung"))
        t += 4
    spans.append((talk_after[0], talk_after[1], "speech"))
    return _track(spans, total), total


def test_held_notes_read_as_singing_and_glides_do_not():
    (f0, prob, rms), _ = _song()
    phrases = tc.find_phrases(f0, prob, rms)
    sung = tc.sung_phrases(phrases)
    assert sung and all(12 <= p["start"] and p["end"] <= 70.1 for p in sung)


def test_talk_before_and_after_the_song_is_removed():
    (f0, prob, rms), total = _song()
    plan = tc.plan_cut(tc.find_phrases(f0, prob, rms), None, total)
    assert plan["status"] == "cut"
    kinds = [r["kind"] for r in plan["removed"]]
    assert kinds == ["before_singing", "after_singing"]
    start, end = plan["sung_window"]
    assert 11 <= start <= 12.1 and 69.9 <= end <= 71
    assert plan["kept"] == [[start, end]] and plan["offset_s"] == start


def test_a_lone_woo_cannot_open_the_song():
    (f0, prob, rms), total = _song()
    woo_f0, woo_prob, woo_rms = _track([(3, 4.2, "sung")], total)
    mask = np.isfinite(woo_f0)
    f0[mask], prob[mask], rms[mask] = woo_f0[mask], woo_prob[mask], woo_rms[mask]
    window = tc.sung_window(tc.find_phrases(f0, prob, rms))
    assert window[0] >= 11


def _seg(start, end, text):
    words = text.split()
    step = (end - start) / max(1, len(words))
    return {"start": start, "end": end, "text": text,
            "words": [{"start": start + i * step, "end": start + (i + 1) * step, "word": w}
                      for i, w in enumerate(words)]}


def test_lyrics_just_after_the_window_extend_it_and_chat_does_not():
    (f0, prob, rms), total = _song(talk_after=(76, 78))
    phrases = tc.find_phrases(f0, prob, rms)
    lyrics = [_seg(20, 24, "play that funky music white boy"), _seg(40, 44, "lay down the boogie")]
    outro = _seg(71, 73.5, "play that funky music white boy")
    chat = _seg(76, 78, "always reminds me of pulp fiction")
    plan = tc.plan_cut(phrases, lyrics + [outro, chat], total)
    assert plan["sung_window"][1] >= 73.5          # the shouted outro is singing
    after = [r for r in plan["removed"] if r["kind"] == "after_singing"][0]
    assert "pulp fiction" in after["text"]


def test_stage_talk_inside_the_song_is_cut_but_lyrics_stay():
    (f0, prob, rms), total = _song()
    gap_f0, gap_prob, gap_rms = _track([(40.5, 43.2, "speech")], total)   # chat over a break
    f0[int(40 * FR):int(44 * FR)] = gap_f0[int(40 * FR):int(44 * FR)]
    prob[int(40 * FR):int(44 * FR)] = gap_prob[int(40 * FR):int(44 * FR)]
    rms[int(40 * FR):int(44 * FR)] = gap_rms[int(40 * FR):int(44 * FR)]
    segs = [_seg(20, 24, "whatever you want to do"), _seg(40.5, 43.2, "thank you so much give it up"),
            _seg(50, 53, "whatever you want")]
    plan = tc.plan_cut(tc.find_phrases(f0, prob, rms), segs, total)
    inner = [r for r in plan["removed"] if r["kind"] == "talk"]
    assert len(inner) == 1 and inner[0]["start"] == pytest.approx(40.5)
    assert len(plan["kept"]) == 2


def test_too_little_singing_cuts_nothing():
    f0, prob, rms = _track([(10, 14, "sung"), (14.5, 18, "sung")], 120)
    plan = tc.plan_cut(tc.find_phrases(f0, prob, rms), None, 120)
    assert plan["status"] == "no_change" and plan["removed"] == []


def test_apply_plan_crops_vocal_and_backing_alike(tmp_path):
    sf = pytest.importorskip("soundfile")
    sr = 8000
    x = np.arange(10 * sr, dtype=np.float32) / (10 * sr)
    for name in ("v.wav", "b.wav"):
        sf.write(tmp_path / name, x, sr)
    plan = {"kept": [[1.0, 4.0], [6.0, 9.0]]}
    tc.apply_plan(tmp_path / "v.wav", tmp_path / "v_cut.wav", plan)
    tc.apply_plan(tmp_path / "b.wav", tmp_path / "b_cut.wav", plan)
    v, _ = sf.read(tmp_path / "v_cut.wav")
    b, _ = sf.read(tmp_path / "b_cut.wav")
    assert len(v) == len(b)
    assert abs(len(v) / sr - 6.0) < 0.05     # 3 s + 3 s, minus the crossfade overlap


def test_report_times_map_back_to_the_recording():
    plan = {"kept": [[41.9, 100.0], [103.0, 200.0]], "offset_s": 41.9}
    assert tc.to_recording_time(0.0, plan) == pytest.approx(41.9)
    assert tc.to_recording_time(60.0, plan) == pytest.approx(104.9)
