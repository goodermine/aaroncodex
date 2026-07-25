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
    for key in ("contract", "rubric", "rubric_fingerprint", "calibration_fingerprint"):
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
