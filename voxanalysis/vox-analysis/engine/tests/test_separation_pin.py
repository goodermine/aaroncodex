"""One separation model, or nothing gets published.

Separation sits upstream of every measurement and mixing models is invisible in
the numbers. On this archive the SAME SONG under MDX-NET vs Mel-Band RoFormer
moved phrase-ending sag by up to 29 points in both directions — larger than the
effects being diagnosed — and silently invalidated a published finding. Raw
measures carry no provenance gate the way scores do, so the check has to be a
failing test rather than a note someone remembers.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import analyse_song as A  # noqa: E402


def _repo_root(start):
    path = start
    while path != os.path.dirname(path):
        if os.path.isfile(os.path.join(path, "CLAUDE.md")):
            return path
        path = os.path.dirname(path)
    raise RuntimeError("repo root not found")


def test_the_pin_matches_the_documented_source_of_truth():
    """docs/models/separation-model.md is the stated single source of truth. If
    the engine's pin drifts from it, the executable check stops meaning what the
    document says."""
    doc = os.path.join(_repo_root(os.path.dirname(os.path.abspath(__file__))),
                       "docs/models/separation-model.md")
    text = open(doc).read()
    assert A.PINNED_SEPARATION_MODEL in text, (
        f"{A.PINNED_SEPARATION_MODEL} is not named in separation-model.md")


def test_the_pinned_model_resolves_to_the_pinned_marker():
    """_stem_model reads the stem filename. The pinned checkpoint must produce
    the marker preflight compares against, or the check silently never matches."""
    produced = A._stem_model(
        {"analysis_input_file": "take_(vocals)_vocals_mel_band_roformer.flac"})
    assert produced == A.PINNED_SEPARATOR


def test_the_three_separators_actually_present_are_told_apart():
    """The archive turned out to hold three, not two — UVR_MDXNET_Main,
    UVR-MDX-NET and RoFormer. Collapsing any pair would hide a real mismatch."""
    cases = {
        "t_(Vocals)_UVR_MDXNET_Main.flac": "UVR_MDXNET_Main",
        "t_(Vocals)_UVR-MDX-NET.flac": "UVR-MDX-NET",
        "t_(vocals)_vocals_mel_band_roformer.flac": "RoFormer",
    }
    got = {f: A._stem_model({"analysis_input_file": f}) for f in cases}
    assert got == cases, got
    assert len(set(got.values())) == 3, "separators must not collapse together"


def test_an_unseparated_analysis_reports_no_model_rather_than_guessing():
    assert A._stem_model({"analysis_input_file": "raw_take.wav"}) is None
    assert A._stem_model({"analysis_input_file": "raw.wav",
                          "stem_separation": {"enabled": True}}) == "unknown_separator"
