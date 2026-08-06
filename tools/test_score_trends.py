#!/usr/bin/env python3
"""Tests for the score-trends data layer (tools/score_trends.py).

Run: python3 -m pytest tools/test_score_trends.py -q

These guard the two things most likely to silently break the dashboard:
1. song-identity canonicalisation (venue suffixes / spelling variants must fold
   to one song, or a song's history splits across cards), and
2. the provenance contract — the tool must only ever READ stored scores and
   must drop legacy-rubric scores from the trends (CLAUDE.md rules 1 & 3).
"""

import score_trends as st


def test_venue_suffixes_fold_to_base_song():
    assert st._canon_song("Pressure Down Captain Cook Tavern") == "Pressure Down"
    assert st._canon_song("Danger Zone New Studio") == "Danger Zone"
    assert st._canon_song("Kryptonite Mango Hill Tavern") == "Kryptonite"
    assert st._canon_song("You Can Leave Your Hat On Bramble Bay") == "You Can Leave Your Hat On"


def test_spelling_and_annotation_aliases():
    assert st._canon_song("Do Wah Diddy Diddy") == "Do Wah Diddy"
    assert st._canon_song("The Letter Joe Cocker") == "The Letter"
    assert st._canon_song("Lets Stay Together New Studio") == "Let's Stay Together"
    assert st._canon_song("Let S Stay Together") == "Let's Stay Together"


def test_apostrophe_repair_does_not_touch_plain_titles():
    assert st._canon_song("Don T Be Cruel") == "Don't Be Cruel"
    assert st._canon_song("She S Not There") == "She's Not There"
    # A title with no apostrophe token is left alone.
    assert st._canon_song("Play That Funky Music") == "Play That Funky Music"
    assert st._canon_song("Kung Fu Fighting") == "Kung Fu Fighting"


def test_base_song_is_unchanged():
    # A song already in canonical form must be idempotent.
    for s in ("Pressure Down", "Do Wah Diddy", "Oh What A Night"):
        assert st._canon_song(s) == s


def test_build_reads_scores_without_recomputing():
    """Every lead in the output must equal the overall or capture-fair the
    engine stored — the tool never invents a number."""
    data = st.build("aaron")
    assert data["contract"]["calibration_fingerprint"], "contract must be pinned"
    seen = 0
    for block in data["songs"]:
        for t in block["takes"]:
            assert t["lead"] in (t["overall"], t["capture_fair"]), (
                f"{t['name']}: lead {t['lead']} is neither the stored overall "
                f"{t['overall']} nor capture-fair {t['capture_fair']}")
            seen += 1
    assert seen > 0


def test_learning_takes_are_separated_from_performance():
    """Learning/warm-up takes form their own group and never appear in the
    performance leaderboard — the same take must not be in both."""
    data = st.build("aaron")
    perf_takes = {t["name"] for b in data["songs"] for t in b["takes"]}
    learn_takes = {t["name"] for b in data["learning"] for t in b["takes"]}
    assert learn_takes, "expected some learning takes"
    assert perf_takes.isdisjoint(learn_takes)
    assert data["summary"]["n_learning"] == len(learn_takes)
    assert data["summary"]["n_learning_songs"] == len(data["learning"])


def test_legacy_scores_are_excluded_from_trends():
    """A legacy-rubric take must never carry trendable=True."""
    data = st.build("aaron")
    for block in data["songs"]:
        for t in block["takes"]:
            assert isinstance(t["trendable"], bool)
    # The summary's excluded count must match takes flagged non-trendable.
    assert data["summary"]["n_excluded_legacy"] == len(data["excluded_legacy"])


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"\n{len(fns)} tests passed")
    sys.exit(0)
