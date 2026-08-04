#!/usr/bin/env python3
"""Read a take's optional context tag — and NEVER its score.

`take_context` is declarative metadata a singer sets at upload/record time (see
docs/plans/TAKE_CONTEXT_TAG.md). It does NOT affect the measured `/10` — rule 1
is untouched, the score is always exactly what was measured. The tag only changes
how a take is GROUPED: `performance` takes are ranked; `learning` and `warmup`
takes are shown in their own "in progress" section, never head-to-head with
polished takes.

Stored in the analysis JSON under a top-level `take_context` block, e.g.:

    "take_context": {
        "intent": "learning",
        "capture": "live",
        "milestone": "first_live_take",
        "note": "first time reaching the high note"
    }

`capture` records where it was sung, because the engine cannot tell a noisy pub
from a clean home take once the vocal is separated (`capture_risk_elevated` reads
False even on tavern takes). It decides which score LEADS — `live` leads
capture-fair (the room/PA is judging the mic, not the voice); `studio`/`home` are
clean captures and lead overall. It never changes a score, only which one is
shown first.

Absent or malformed -> performance intent, unknown capture, no milestone/note.
Everything already in the archive therefore reads as a normal performance take
with capture unknown, unchanged.
"""

from __future__ import annotations

INTENTS = ("performance", "learning", "warmup")
CAPTURES = ("studio", "home", "live")   # studio/home -> overall; live -> capture-fair
MILESTONES = ("first_live_take",)
DEFAULT = {"intent": "performance", "capture": None, "milestone": None,
           "note": None, "superseded": False}


def read_context(analysis: dict) -> dict:
    """Return {intent, milestone, note}, defaulting safely for absent/bad data.

    Intentionally forgiving: an unknown intent or milestone falls back to the
    default rather than raising, so a stray value can never break ranking or
    (worse) be mistaken for a scoring input.
    """
    tc = analysis.get("take_context") if isinstance(analysis, dict) else None
    if not isinstance(tc, dict):
        return dict(DEFAULT)
    intent = tc.get("intent")
    if intent not in INTENTS:
        intent = "performance"
    capture = tc.get("capture")
    if capture not in CAPTURES:
        capture = None
    milestone = tc.get("milestone")
    if milestone not in MILESTONES:
        milestone = None
    note = tc.get("note")
    if not isinstance(note, str) or not note.strip():
        note = None
    # `superseded` retires an over-recorded take from ranking WITHOUT deleting it
    # or its score: the file and the score stay exactly as measured (rule 1), the
    # take just drops out of the leaderboard/average. Strict `is True` so a stray
    # truthy value (a string, a 1) can never silently retire a real take.
    superseded = tc.get("superseded") is True
    return {"intent": intent, "capture": capture, "milestone": milestone,
            "note": note, "superseded": superseded}


def leads_capture_fair(analysis: dict) -> bool | None:
    """True -> lead capture-fair (declared live), False -> lead overall (declared
    studio/home), None -> undeclared (caller falls back to the engine's flag)."""
    cap = read_context(analysis)["capture"]
    if cap == "live":
        return True
    if cap in ("studio", "home"):
        return False
    return None


def is_performance(analysis: dict) -> bool:
    """True for takes that belong on the leaderboard (the default)."""
    return read_context(analysis)["intent"] == "performance"


def is_learning(analysis: dict) -> bool:
    return read_context(analysis)["intent"] in ("learning", "warmup")


def is_superseded(analysis: dict) -> bool:
    """True for a take retired from ranking (an over-recorded duplicate curated
    out of the leaderboard). The file and its measured score are untouched."""
    return read_context(analysis)["superseded"]
