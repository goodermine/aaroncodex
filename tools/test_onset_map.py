"""The onset map must find the right reference and never block a report.

D4 (dream ledger): every full report whose song has a scored reference ships
the two-panel onset figure. Matching is filename-token based, so the tests pin
the cases that could silently mis-pair a singer with the wrong original.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from onset_map import find_reference, song_slug  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")


def test_song_slug_strips_date_singer_and_take():
    assert song_slug("2026-07-24-aaron-pressure-down-take-001_analysis.json") == "pressure-down"
    assert song_slug("2026-07-09-aaron-the-letter-take-002_analysis.json") == "the-letter"
    assert song_slug("2026-07-11-aaron-g-vienna-take-001_analysis.json") == "vienna"
    assert song_slug("2026-08-01-john-farnham-pressure-down-reference_analysis.json").endswith("pressure-down")


def test_pressure_down_finds_the_farnham_reference():
    ref = find_reference(os.path.join(ARCH, "2026-07-24-aaron-pressure-down-take-001_analysis.json"))
    assert ref and "john-farnham-pressure-down" in ref


def test_the_letter_finds_joe_cocker():
    ref = find_reference(os.path.join(ARCH, "2026-07-09-aaron-the-letter-take-001_analysis.json"))
    assert ref and "joe-cocker-the-letter" in ref


def test_kung_fu_finds_the_carl_douglas_reference():
    # Once the reference library gained Carl Douglas (F4), Kung Fu takes pair
    # with it. This guards that the matcher keeps finding it.
    ref = find_reference(os.path.join(ARCH, "2026-08-01-aaron-kung-fu-fighting-take-005_analysis.json"))
    assert ref and "carl-douglas-kung-fu-fighting" in ref


def test_song_without_reference_returns_none():
    # A synthetic song that can never have a reference — kept stable against the
    # growing library, since find_reference only parses the take's filename and
    # globs the reference files (it never opens the take itself).
    ref = find_reference(os.path.join(ARCH, "2099-01-01-aaron-a-song-with-no-reference-xyzzy-take-001_analysis.json"))
    assert ref is None


def test_render_produces_a_real_file(tmp_path):
    from onset_map import render_onset_map
    take = os.path.join(ARCH, "2026-07-24-aaron-pressure-down-take-001_analysis.json")
    ref = find_reference(take)
    out = str(tmp_path / "map.png")
    assert render_onset_map(ref, take, out) == out
    assert os.path.getsize(out) > 50_000
