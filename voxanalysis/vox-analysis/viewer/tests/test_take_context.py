"""take_context upload fields: sanitised, optional, never score-bearing."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from app import _sanitise_take_context  # noqa: E402


def test_valid_fields_pass_through():
    ctx = _sanitise_take_context("learning", "live", "first run at the bridge")
    assert ctx == {"intent": "learning", "capture": "live",
                   "note": "first run at the bridge"}


def test_absent_fields_yield_none():
    assert _sanitise_take_context("", "", "") is None
    assert _sanitise_take_context("  ", None or "", "   ") is None


def test_unknown_values_are_dropped_not_stored():
    assert _sanitise_take_context("bogus", "moon", "") is None
    ctx = _sanitise_take_context("PERFORMANCE", "Home", "")
    assert ctx == {"intent": "performance", "capture": "home"}


def test_note_is_whitespace_collapsed_and_bounded():
    ctx = _sanitise_take_context("", "", "  a   lot\n of   space  " + "x" * 500)
    assert ctx["note"].startswith("a lot of space")
    assert len(ctx["note"]) <= 200
