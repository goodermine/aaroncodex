"""tools/reanalyse_archive.py — the operator tool that closes the coverage gap.

34 of 35 archived takes predate six measurement modules, so they cannot score
breath_support. The gap can only be closed by re-analysing the original vocal
stems, and the tool matches each archived analysis to its stem by the exact
`analysis_input_file` basename it recorded — never by guessing at the name.

These cover the matching and safety logic. The end-to-end engine pass is
validated by running it against the one take whose audio is in the repo, which
reproduces its archived figure (25 of 51 endings, 49.0%) exactly.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys

def _repo_root(start: str) -> str:
    """Walk up to the repo root rather than counting `dirname` calls — this file
    sits four levels down and an off-by-one is silent until the tool moves."""
    path = start
    while path != os.path.dirname(path):
        if os.path.isfile(os.path.join(path, "CLAUDE.md")):
            return path
        path = os.path.dirname(path)
    raise RuntimeError(f"repo root not found above {start}")


ROOT = _repo_root(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools/reanalyse_archive.py")


def _load():
    spec = importlib.util.spec_from_file_location("reanalyse_archive", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_missing_modules_spots_a_pre_breath_analysis():
    m = _load()
    current = {mod: {"x": 1} for mod in m.LATER_MODULES}
    assert m.missing_modules(current) == []
    old = dict(current)
    del old["breath"]
    assert m.missing_modules(old) == ["breath"]
    assert m.missing_modules({}) == list(m.LATER_MODULES)


def test_stem_index_finds_audio_by_basename(tmp_path):
    m = _load()
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "take_(Vocals)_UVR_MDXNET_Main.flac").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("not audio")
    idx = m.index_stems([str(tmp_path)])
    assert "take_(Vocals)_UVR_MDXNET_Main.flac" in idx
    assert "notes.txt" not in idx


def test_dry_run_reports_matches_and_writes_nothing(tmp_path):
    """The default must be a rehearsal: an operator pointing this at the wrong
    folder should get a report, not 35 rewritten analyses."""
    archive = tmp_path / "archive"
    stems = tmp_path / "stems"
    archive.mkdir(); stems.mkdir()
    stem_name = "2026-01-01-aaron-song-take-001_(Vocals)_UVR_MDXNET_Main.flac"
    (stems / stem_name).write_bytes(b"x")
    entry = archive / "2026-01-01-aaron-song-take-001_analysis.json"
    payload = {"analysis_input_file": stem_name, "artist_name": "Aaron",
               "intonation": {"n_notes": 10}}
    entry.write_text(json.dumps(payload))
    before = entry.read_text()

    proc = subprocess.run([sys.executable, TOOL, str(stems), "--archive", str(archive)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "to re-analyse    : 1" in proc.stdout
    assert "DRY RUN" in proc.stdout
    assert entry.read_text() == before, "a dry run must not modify the archive"


def test_a_take_whose_stem_is_absent_is_reported_not_skipped_silently(tmp_path):
    """The missing-stem list is the shopping list of audio Aaron needs to supply.
    Silently omitting those takes would read as 'nothing left to do'."""
    archive = tmp_path / "archive"
    stems = tmp_path / "stems"
    archive.mkdir(); stems.mkdir()
    (stems / "unrelated.flac").write_bytes(b"x")
    (archive / "take_analysis.json").write_text(json.dumps(
        {"analysis_input_file": "gone_(Vocals)_UVR_MDXNET_Main.flac", "artist_name": "Aaron"}))

    proc = subprocess.run([sys.executable, TOOL, str(stems), "--archive", str(archive)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "stem not found   : 1" in proc.stdout
    assert "gone_(Vocals)_UVR_MDXNET_Main.flac" in proc.stdout
