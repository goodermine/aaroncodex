"""tools/analyse_takes.py — batch-analyse a folder of takes into the archive.

The repo archive holds 35 takes from 4 dates; the VOX Coach host holds ~128
performances going back to February, ~109 with a retained vocal stem. This tool
is how that history gets measured into the repo. Its risky parts are all in
identification: pairing a file with the right archive entry, not inventing a
second record of one performance, and never scoring a full mix as a vocal.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys


def _repo_root(start: str) -> str:
    path = start
    while path != os.path.dirname(path):
        if os.path.isfile(os.path.join(path, "CLAUDE.md")):
            return path
        path = os.path.dirname(path)
    raise RuntimeError(f"repo root not found above {start}")


ROOT = _repo_root(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools/analyse_takes.py")


def _load():
    spec = importlib.util.spec_from_file_location("analyse_takes", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_take_key_strips_only_pipeline_suffixes():
    """Separator and conversion suffixes are noise. But -normalized / -song-cut
    are part of the archive's own filenames, so stripping them would stop a take
    matching its existing entry."""
    m = _load()
    assert m.take_key("2026-07-25-aaron-my-babe-take-001_converted_(Vocals)_UVR_MDXNET_Main.flac") \
        == "2026-07-25-aaron-my-babe-take-001"
    assert m.take_key("2026-07-25-aaron-my-babe-take-001.mp3") \
        == "2026-07-25-aaron-my-babe-take-001"
    for kept in ("2026-07-12-aaron-goodbye-s-been-good-to-you-take-001-normalized",
                 "2026-07-12-aaron-come-out-and-play-captain-cook-tavern-take-001-song-cut",
                 "aaron-danger-zone-home-2026-07-11-normalized"):
        assert m.take_key(kept + "_(Vocals)_UVR_MDXNET_Main.flac") == kept


def test_artist_is_read_from_the_filename_longest_token_first():
    m = _load()
    assert m.artist_of("2026-07-11-aaron-g-vienna-take-001") == "Aaron G"
    assert m.artist_of("2026-07-11-aaron-danger-zone-take-003") == "Aaron"
    assert m.artist_of("2026-07-25-rilda-dreams-take-001") == "Rilda"
    assert m.artist_of("leo-chasin-that-neon-rainbow-2026-07-11") == "Leo"
    assert m.artist_of("2026-04-28-unknown-singer-unknown-song-take-001") == "Unknown Artist"


def test_a_stem_is_preferred_over_the_raw_mix(tmp_path):
    """Both exist for most takes. Using the stem skips separation entirely; using
    the raw mix would also mean scoring bass and guitar as though they were the
    voice unless separation re-runs."""
    m = _load()
    (tmp_path / "2026-07-25-aaron-my-babe-take-001.mp3").write_bytes(b"x")
    (tmp_path / "2026-07-25-aaron-my-babe-take-001_(Vocals)_UVR_MDXNET_Main.flac").write_bytes(b"x")
    takes = m.collect([str(tmp_path)])
    assert list(takes) == ["2026-07-25-aaron-my-babe-take-001"]
    slot = takes["2026-07-25-aaron-my-babe-take-001"]
    assert slot["stem"] is not None and slot["raw"] is not None
    assert m.is_stem(slot["stem"]) and not m.is_stem(slot["raw"])


def _run(args):
    return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)


def test_dry_run_classifies_new_partial_and_complete_without_writing(tmp_path):
    archive = tmp_path / "archive"; audio = tmp_path / "audio"
    archive.mkdir(); audio.mkdir()
    complete = {mod: {"x": 1} for mod in _load().LATER_MODULES}

    # a take the archive has never seen
    (audio / "2026-02-01-aaron-new-song-take-001_(Vocals)_UVR_MDXNET_Main.flac").write_bytes(b"x")
    # a take archived but missing the later modules
    (audio / "2026-07-11-aaron-old-song-take-001_(Vocals)_UVR_MDXNET_Main.flac").write_bytes(b"x")
    partial = archive / "2026-07-11-aaron-old-song-take-001_analysis.json"
    partial.write_text(json.dumps({"intonation": {"n_notes": 5}}))
    # a take already complete — must be skipped
    (audio / "2026-07-25-aaron-done-take-001_(Vocals)_UVR_MDXNET_Main.flac").write_bytes(b"x")
    done = archive / "2026-07-25-aaron-done-take-001_analysis.json"
    done.write_text(json.dumps(complete))

    before = {p.name: p.read_text() for p in archive.iterdir()}
    proc = _run([str(audio), "--archive", str(archive)])
    assert proc.returncode == 0, proc.stderr
    assert "NEW  — not in the archive   : 1" in proc.stdout
    assert "REFRESH — archived, partial : 1" in proc.stdout
    assert "already complete (skipped) : 1" in proc.stdout
    assert "DRY RUN" in proc.stdout
    assert {p.name: p.read_text() for p in archive.iterdir()} == before
    assert not (archive / "2026-02-01-aaron-new-song-take-001_analysis.json").exists()


def test_stems_only_defers_raw_mixes_rather_than_scoring_a_full_mix(tmp_path):
    """A score computed on a full mix is meaningless (CLAUDE.md rule 4). A raw
    mix must therefore either be separated first or deferred — never analysed
    as-is."""
    archive = tmp_path / "archive"; audio = tmp_path / "audio"
    archive.mkdir(); audio.mkdir()
    (audio / "2026-03-01-rilda-at-last-take-001.mp3").write_bytes(b"x")

    deferred = _run([str(audio), "--archive", str(archive), "--stems-only"])
    assert "deferred (need separation) : 1" in deferred.stdout
    assert "Nothing to do." in deferred.stdout

    included = _run([str(audio), "--archive", str(archive)])
    assert "SEPARATE+analyse" in included.stdout, included.stdout


def test_a_take_archived_under_a_variant_name_is_not_duplicated(tmp_path):
    """One performance, one archive record. A file whose name differs only by a
    pipeline artefact must update the existing entry, not create a rival."""
    archive = tmp_path / "archive"; audio = tmp_path / "audio"
    archive.mkdir(); audio.mkdir()
    (archive / "2026-07-12-rilda-she-s-not-there-take-001-normalized_analysis.json").write_text(
        json.dumps({"intonation": {"n_notes": 5}}))
    (audio / "2026-07-12-rilda-she-s-not-there-take-001_(Vocals)_UVR_MDXNET_Main.flac").write_bytes(b"x")

    proc = _run([str(audio), "--archive", str(archive)])
    assert proc.returncode == 0, proc.stderr
    assert "matched to an existing entry under a different name (1)" in proc.stdout
    assert "NEW  — not in the archive   : 0" in proc.stdout
