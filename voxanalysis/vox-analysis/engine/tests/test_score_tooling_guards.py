"""Guards from the 17 Oct 2026 scoring-engine review: tools that read or rewrite
scores must fail loudly rather than hand a singer a hollow report or wipe the
archive from a stale checkout."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_retire_refuses_on_a_stale_checkout(tmp_path, monkeypatch):
    retire = _load("docs/score-metrics/retire_legacy_scores.py", "retire_under_test")
    newer = {"technical_score": {"overall_score_0_to_10": 9.0,
                                 "identity": {"contract": "voxai_score_v1",
                                              "rubric": "deterministic_rubric_v99"}}}
    path = tmp_path / "2026-01-01-aaron-x-take-001_analysis.json"
    path.write_text(json.dumps(newer))
    monkeypatch.setattr(retire, "ARCHIVE", str(tmp_path))
    assert retire.main() == 1
    assert json.loads(path.read_text())["technical_score"]["overall_score_0_to_10"] == 9.0


def test_show_results_does_not_turn_a_renderer_bug_into_a_hollow_report(monkeypatch, tmp_path):
    show = _load("tools/show_results.py", "show_results_under_test")
    sys.path.insert(0, str(ROOT / "voxanalysis/vox-analysis/viewer"))
    import report_builder as R

    def broken(*_a, **_k):
        raise TypeError("bug inside the renderer")

    monkeypatch.setattr(R, "render_full_results_text", broken)
    take = tmp_path / "take_analysis.json"
    take.write_text(json.dumps({"technical_score": {"overall_score_0_to_10": 8.0}}))
    with pytest.raises(TypeError):
        show.render(str(take))


@pytest.mark.parametrize("name, song", [
    ("2026-09-16-aaron-all-that-she-wants-home-instamic-sep16220_analysis", "all-that-she-wants"),
    ("2026-09-16-aaron-tennessee-whiskey-home-instamic-first-take-sep16-226_analysis", "tennessee-whiskey"),
    ("2026-09-16-aaron-you-sexy-thing-home-instamic-brand-new-take-001_analysis", "you-sexy-thing"),
    ("2026-09-17-aaron-oh-what-a-night-bramble-instamic-first-live-take-001_analysis", "oh-what-a-night"),
    ("2026-09-17-aaron-the-letter-bramble-instamic-take-001_analysis", "the-letter"),
    ("2026-07-08-aaron-do-wah-diddy-diddy-take-002_analysis", "do-wah-diddy"),
    ("2026-10-15-aaron-the-wanderer-take-003_analysis", "the-wanderer"),
])
def test_one_song_is_one_group_in_the_score_tables(name, song):
    rescore = _load("docs/score-metrics/rescore_all.py", "rescore_under_test")
    assert rescore.song(name) == song


# ---- parselmouth guard, 22 Oct 2026 ----

def _archive_with(tmp_path, approximated):
    # A current, fully measured take, so every earlier preflight check passes.
    src = ROOT / "voxanalysis/archive/scratch-analyses/2026-10-21-aaron-the-wanderer-take-003-redcliffe-leagues-heat-1_analysis.json"
    data = json.loads(src.read_text())
    if approximated:
        data["engine"]["parselmouth_available"] = False
        data["voice_quality"]["method"] = "frame_f0_approximation"
    (tmp_path / "2026-10-21-aaron-x-take-001_analysis.json").write_text(json.dumps(data))


def test_preflight_names_archived_scores_made_without_parselmouth(tmp_path, monkeypatch, capsys):
    pre = _load("tools/score_preflight.py", "preflight_under_test")
    _archive_with(tmp_path, approximated=True)
    monkeypatch.setattr(pre, "ARCHIVE", str(tmp_path))
    assert pre.main() == 0
    out = capsys.readouterr().out
    assert "1 archived score(s) were made without parselmouth" in out
    assert "2026-10-21-aaron-x-take-001_analysis.json" in out


def test_preflight_is_quiet_when_voice_quality_was_measured(tmp_path, monkeypatch, capsys):
    pre = _load("tools/score_preflight.py", "preflight_under_test")
    _archive_with(tmp_path, approximated=False)
    monkeypatch.setattr(pre, "ARCHIVE", str(tmp_path))
    assert pre.main() == 0
    assert "voice quality measured with parselmouth throughout" in capsys.readouterr().out


def test_preflight_fails_on_an_engine_without_parselmouth(tmp_path, monkeypatch, capsys):
    pre = _load("tools/score_preflight.py", "preflight_under_test")
    _archive_with(tmp_path, approximated=False)
    monkeypatch.setattr(pre, "ARCHIVE", str(tmp_path))
    sys.path.insert(0, str(ROOT / "voxanalysis/vox-analysis/engine"))
    import analyse_song
    monkeypatch.setattr(analyse_song, "PARSELMOUTH_AVAILABLE", False)
    assert pre.main() == 1
    assert "praat-parselmouth is not installed" in capsys.readouterr().out
