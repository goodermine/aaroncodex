"""The pinned score contract must match the engine, and the rules must exist.

If someone changes the scoring maths without re-pinning the contract, this test
fails — which is the point. `tools/score_preflight.py` uses the same comparison to
stop a stale engine publishing a score, so this test protects that guarantee.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, os.path.dirname(HERE))
import analyse_song as A  # noqa: E402

CONTRACT = os.path.join(REPO, "docs/score-metrics/SCORE_CONTRACT.json")


def test_pinned_contract_matches_the_engine():
    """A rubric change must be accompanied by re-pinning the contract:
        python3 tools/score_preflight.py --update
    """
    assert os.path.isfile(CONTRACT), f"missing pinned contract at {CONTRACT}"
    with open(CONTRACT) as fh:
        pinned = json.load(fh)
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    live = A.score_identity({}, cal)
    # The measurement build is part of the contract from Sep 2026: a change to
    # how a scored input is MEASURED must be as deliberate as a rubric change.
    live["measurement_fingerprint"] = A.measurement_fingerprint()
    for key in ("contract", "rubric", "rubric_fingerprint", "calibration_fingerprint",
                "measurement_fingerprint"):
        assert pinned.get(key) == live.get(key), (
            f"{key} drifted: contract={pinned.get(key)!r} engine={live.get(key)!r} — "
            "re-pin with `python3 tools/score_preflight.py --update` and commit it")


def test_repo_ships_standing_rules_for_agents():
    """CLAUDE.md is read automatically by agents working in this repo; it is the
    only durable place to state the scoring rules. Its absence is what let a
    second implementation drift onto an old rubric."""
    path = os.path.join(REPO, "CLAUDE.md")
    assert os.path.isfile(path), "CLAUDE.md missing — agents get no standing rules"
    text = open(path).read()
    for required in ("score_preflight", "is_legacy_score", "capture-fair",
                     "render_full_results_text", "ONE scoring engine"):
        assert required in text, f"CLAUDE.md no longer states: {required}"


def test_preflight_tool_exists_and_is_runnable():
    path = os.path.join(REPO, "tools/score_preflight.py")
    assert os.path.isfile(path)
    assert "--update" in open(path).read()


def test_every_archived_score_is_on_the_pinned_calibration_pack():
    """A score anchored to an older pack passes `is_legacy_score()` — it has the
    right contract and the right rubric — but `score_conflict()` refuses to
    compare it with a current one. That gap let 113 of 182 archived analyses sit
    on a superseded pack while preflight reported "safe to publish", so the
    leaderboard, the archive average and a cross-era comparison were all built
    from two rulers that disagreed by up to 0.5.

    A second, legitimate reason a stored score can sit on an older pack: its
    MEASUREMENT era differs from the pack's (`A.scale_mismatch`). Phase 1a
    (Sep 2026) rebuilt the calibration pack from the drift-fix engine before
    re-analysing the 234 archive takes still measured on the pre-fix engine —
    deliberately, since scoring those stored (flattered) inputs against the
    corrected pack would put them on the wrong ruler in the other direction.
    Those are exempt here the same way a retired/withheld stub is: not a
    forgotten re-score, a deferred one (Phase 1c re-analyses them; until then
    they are simply not comparable to current scores, which score_conflict()
    already enforces).

    Fix when this fails on a score that IS on the current measurement era:
        python3 docs/score-metrics/rescore_archive_inplace.py
        python3 docs/score-metrics/rescore_all.py
    """
    import glob

    archive = os.path.join(REPO, "voxanalysis/archive/scratch-analyses")
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    pinned = A.score_identity({}, cal)["calibration_fingerprint"]

    stale = []
    for path in sorted(glob.glob(os.path.join(archive, "*_analysis.json"))):
        with open(path) as fh:
            data = json.load(fh) or {}
        score = data.get("technical_score")
        # Score-less stubs carry no calibration by design and are exempt: a
        # legacy rubric retirement, or a score withheld pending re-analysis
        # (e.g. the short-note drift artefact). Both lack an identity, so
        # is_legacy_score()/score_conflict() already refuse to quote them.
        if (not isinstance(score, dict)
                or score.get("status") in ("retired_legacy_score", "withheld_measurement_artefact")):
            continue
        if A.scale_mismatch(data, cal):
            continue
        fp = (score.get("identity") or {}).get("calibration_fingerprint")
        if fp != pinned:
            stale.append((os.path.basename(path), fp))

    assert not stale, (
        f"{len(stale)} archived score(s) anchored to a superseded calibration pack "
        f"(pinned {pinned}), e.g. {stale[:3]} — re-score with "
        "docs/score-metrics/rescore_archive_inplace.py")


def test_knowledge_base_is_valid_and_its_manifest_is_current():
    """The library stayed clean for 78 hand-maintained documents, then gained a
    collaborator and broke five times in two days — a document with 8 tags
    against a limit of 6, tags outside the controlled vocabulary, an invented
    category, and MANIFEST word counts wrong on four separate occasions. None of
    it failed anything. This is what fails now."""
    import subprocess

    for tool, args in (("kb_validate.py", []), ("kb_manifest.py", ["--check"])):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "tools", tool), *args],
            capture_output=True, text=True)
        assert proc.returncode == 0, f"{tool} failed:\n{proc.stdout}{proc.stderr}"


def test_no_private_document_can_reach_the_public_build():
    """The privacy boundary, asserted rather than assumed. Aaron's measured
    profile, his blueprint and his drill programme are private by his decision
    of 3 Aug 2026; another creator's transcript cannot ship in a library
    licensed to him."""
    import subprocess

    proc = subprocess.run(
        [sys.executable, os.path.join(REPO, "tools", "kb_build_public.py"), "--dry-run"],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "private/ is never published" in proc.stdout
    assert "08-external-reference/ is never published" in proc.stdout
