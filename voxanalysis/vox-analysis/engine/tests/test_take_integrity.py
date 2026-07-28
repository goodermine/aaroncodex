"""Screen for a reference original mislabeled as a singer's take.

The Andy Gibb original scored 9.2 as Aaron's best take and was only caught by
ear. This screens for the signature — same song, near-exact duration to a
reference — but must NOT hard-block, because a karaoke cover over the
original-length backing track matches legitimately (Aaron's real covers land
0.5-1.5s from their originals). Same-song is required so duration coincidences
between different songs do not fire.
"""

from __future__ import annotations

import importlib.util
import json
import os

import pytest


def _repo_root(start):
    p = start
    while p != os.path.dirname(p):
        if os.path.isfile(os.path.join(p, "CLAUDE.md")):
            return p
        p = os.path.dirname(p)
    raise RuntimeError("repo root not found")


ROOT = _repo_root(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "check_take_integrity", os.path.join(ROOT, "tools/check_take_integrity.py"))
CHK = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CHK)


def _write(d, name, dur, extra=None):
    payload = {"duration_seconds": dur}
    if extra:
        payload.update(extra)
    (d / f"{name}_analysis.json").write_text(json.dumps(payload))


def test_a_dead_ringer_cover_of_a_reference_is_flagged(tmp_path):
    arch = tmp_path / "arch"; refs = tmp_path / "refs"
    arch.mkdir(); refs.mkdir()
    _write(refs, "andy-gibb-i-just-want-to-be-your-everything", 225.67)
    _write(arch, "2026-07-10-aaron-i-just-want-to-be-your-everything-take-001", 225.65)
    hits = CHK.scan(str(arch), str(refs))
    assert len(hits) == 1 and hits[0]["gap_s"] <= 0.25


def test_a_different_song_of_similar_length_is_not_flagged(tmp_path):
    """Don't Be Cruel and Rolling In The Deep are both ~234s — different songs,
    must not fire."""
    arch = tmp_path / "arch"; refs = tmp_path / "refs"
    arch.mkdir(); refs.mkdir()
    _write(refs, "adele-rolling-in-the-deep", 233.88)
    _write(arch, "2026-05-28-aaron-don-t-be-cruel-take-001", 233.85)
    assert CHK.scan(str(arch), str(refs)) == []


def test_a_reference_duplicate_in_the_archive_is_not_a_take(tmp_path):
    """The 9 reference duplicates living in the archive are references, not
    takes — scanning them against themselves would flag every one."""
    arch = tmp_path / "arch"; refs = tmp_path / "refs"
    arch.mkdir(); refs.mkdir()
    _write(refs, "carpenters-this-masquerade-reference", 291.24)
    _write(arch, "carpenters-this-masquerade-reference", 291.24)  # the duplicate
    assert CHK.scan(str(arch), str(refs)) == []


def test_a_genuine_cover_a_second_off_is_not_flagged(tmp_path):
    """Aaron's real Heat Is On cover lands ~0.5s+ from the Glenn Frey original.
    Within the loose duration band but past the confirm threshold — must not
    fire, or the screen would reject his real covers."""
    arch = tmp_path / "arch"; refs = tmp_path / "refs"
    arch.mkdir(); refs.mkdir()
    _write(refs, "glenn-frey-the-heat-is-on-reference", 226.06)
    _write(arch, "2026-07-11-aaron-danger-zone-take-003", 212.0)   # different song anyway
    _write(arch, "2026-07-15-aaron-the-heat-is-on-take-009", 227.6)  # same song, 1.5s off
    assert CHK.scan(str(arch), str(refs)) == []


def test_the_live_archive_has_no_unresolved_aaron_mislabel():
    """Guard against a regression on the real data: after the Andy Gibb removal,
    no AARON take should be a dead-ringer for a reference. (Other singers may
    surface for confirmation; this asserts only Aaron's set is clean.)"""
    hits = [h for h in CHK.scan() if "-aaron-" in h["take"].lower()]
    assert hits == [], f"an Aaron take matches a reference original: {hits}"
