"""The words onset map must line words up with notes and never invent a score.

Transcription (faster-whisper) is not exercised here — it needs the audio stem
and a model download. Everything after it is: the window offset, section
labels, word cleaning, word-to-note lookup and the render itself.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from word_onset_map import (analysis_offset, clean_words, parse_sections,  # noqa: E402
                            render, word_at)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")


def test_offset_read_from_trimmed_take_note():
    take = {"take_context": {"note": "chatter trimmed (analysed 30.0s to 179.5s of the vocal stem)"}}
    assert analysis_offset(take) == 30.0


def test_offset_defaults_to_zero_when_untrimmed():
    assert analysis_offset({}) == 0.0
    assert analysis_offset({"take_context": {"note": "studio take"}}) == 0.0


def test_sections_parse_and_reject_garbage():
    s = parse_sections("0-9.7=opening chorus; 89.5-103=sax break")
    assert s == [{"w": "(opening chorus)", "s": 0.0, "e": 9.7},
                 {"w": "(sax break)", "s": 89.5, "e": 103.0}]
    assert parse_sections("") == []
    with pytest.raises(ValueError):
        parse_sections("10-20")


def test_clean_drops_long_words_and_words_inside_sections():
    raw = [{"w": "whop", "s": 1.0, "e": 1.2},      # inside the section
           {"w": "Tutti", "s": 10.0, "e": 10.3},
           {"w": "draaag", "s": 12.0, "e": 16.0}]   # 4 s "word" = hallucination
    out = clean_words(raw, parse_sections("0-9.7=intro"))
    assert [w["w"] for w in out] == ["(intro)", "Tutti"]


def test_word_at_matches_inside_near_and_not_far():
    words = [{"w": "girl", "s": 26.0, "e": 26.5}, {"w": "Sue", "s": 27.3, "e": 27.7}]
    assert word_at(words, 26.2) == "girl"
    assert word_at(words, 25.9) == "girl"         # note starts just before the word
    assert word_at(words, 27.0) == "Sue"          # nearest start within 0.4 s
    assert word_at(words, 40.0) == ""
    assert word_at([], 1.0) == ""


def test_render_produces_a_real_file(tmp_path):
    take = os.path.join(ARCH, "2026-07-24-aaron-pressure-down-take-001_analysis.json")
    words = [{"w": "pressure", "s": 5.0, "e": 5.6}, {"w": "down", "s": 5.6, "e": 6.2}]
    out = str(tmp_path / "words.png")
    assert render(take, words, out) == out
    assert os.path.getsize(out) > 50_000
