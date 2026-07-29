"""take_context reads context safely and NEVER lets it near a score."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_context import read_context, leads_capture_fair, is_performance, is_learning


def test_absent_or_malformed_defaults_to_performance():
    for bad in ({}, {"take_context": None}, {"take_context": "learning"},
                {"take_context": {"intent": "bogus", "capture": "moon"}}):
        c = read_context(bad)
        assert c == {"intent": "performance", "capture": None,
                     "milestone": None, "note": None}
        assert is_performance(bad) and not is_learning(bad)


def test_valid_context_is_read():
    a = {"take_context": {"intent": "learning", "capture": "live",
                          "milestone": "first_live_take", "note": " high note "}}
    c = read_context(a)
    assert c["intent"] == "learning"
    assert c["capture"] == "live"
    assert c["milestone"] == "first_live_take"
    assert c["note"] == " high note "     # preserved, only blank-rejected
    assert is_learning(a) and not is_performance(a)


def test_blank_note_becomes_none():
    assert read_context({"take_context": {"note": "   "}})["note"] is None


def test_capture_decides_lead_not_score():
    assert leads_capture_fair({"take_context": {"capture": "live"}}) is True
    assert leads_capture_fair({"take_context": {"capture": "home"}}) is False
    assert leads_capture_fair({"take_context": {"capture": "studio"}}) is False
    assert leads_capture_fair({}) is None           # undeclared -> caller falls back


def test_context_never_exposes_a_score_field():
    # guard: the reader returns only grouping/context keys, never a number
    c = read_context({"take_context": {"intent": "learning", "score": 9.9,
                                       "overall": 1.0}})
    assert set(c) == {"intent", "capture", "milestone", "note"}
    assert 9.9 not in c.values() and 1.0 not in c.values()
