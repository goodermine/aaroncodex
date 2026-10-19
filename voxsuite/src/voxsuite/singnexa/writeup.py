"""The plain-English coaching write-up shown above the full results.

Claude reads the full measured results (the same text the singer can
download) and explains them in everyday words. It explains; it never scores.
Every /10 and every listen-back time in the write-up must already appear in
the results, or the write-up is rejected and the page shows the full results
alone (CLAUDE.md rule 1: one engine, no second number).

Only the results text is sent, never the audio. Configure with:

  ANTHROPIC_API_KEY           required; without it the write-up is switched off
  SINGNEXA_WRITEUP            "0" switches it off even with a key
  SINGNEXA_WRITEUP_MODEL      default claude-opus-5-5
  SINGNEXA_WRITEUP_EFFORT     default medium
"""

from __future__ import annotations

import os
import re

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "medium"
# Models that take the server-side refusal fallback ("default" routing).
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM_PROMPT = """\
You write the plain-English coaching notes for a Singnexa vocal analysis. The \
singer reads them on a phone, just above the full technical results.

Hard rules:
1. Every score and number you give must appear in the results exactly as written. \
Never calculate, round, average, adjust or invent a score, percentage or measurement. \
Never give a /10 that is not in the results.
2. Open with the score the results say to lead with (the "Lead with" line), the other \
score beside it, the confidence, and that the scale is calibrated to 50 professional \
vocals where 10 is a typical pro, so a 7 is a good amateur result, not a failure. If the \
headline score is withheld, say so and why in plain words, and give no headline number.
3. Translate units into words: 100 cents is one semitone, the gap between two \
neighbouring piano keys, so say "about three-quarters of a semitone", not "76 cents". \
Describe decibels as louder or quieter.
4. On live, room or phone recordings, voice quality and dynamics mostly measure the \
microphone and the room. Say that, and don't turn them into coaching.
5. The drills come from the results' practice plan. Anything else you suggest (a key \
change, rest, a different song) is your own suggestion: say so.
6. Never compare the singer with a named singer. Don't comment on health, fatigue, \
smoking, pain or mood; the engine can't measure those.
7. If the take is a learning take or a first attempt, say so and judge it as a first go.
8. If talking was removed before the analysis, mention it in one line with its times so \
the singer can check it.
9. Only use listen-back times (m:ss) that appear in the results.

Format, in Markdown:
- Use these ### headings in order: The score, What's working, What to work on, Listen \
back to, Practice plan, What the engine can't tell.
- Short paragraphs and bullets. No tables and no code blocks.
- 350 to 600 words, warm and direct, in Australian English. Talk to the singer as "you".
"""

_SCORE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*(?:/|out of)\s*10\b")
_TIME = re.compile(r"\b(\d{1,2}:\d{2})\b")


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get("SINGNEXA_WRITEUP", "1") != "0"


def build_prompt(results_text: str, *, singer: str = "", song: str = "", artist: str = "",
                 take_context: dict | None = None) -> str:
    ctx = take_context or {}
    lines = [f"Singer: {singer or 'the singer'}"]
    if song:
        lines.append(f"Song: {song}" + (f" ({artist})" if artist else ""))
    if ctx.get("capture"):
        lines.append(f"Recorded: {ctx['capture']}")
    if ctx.get("intent"):
        lines.append(f"Take type: {ctx['intent']}")
    if ctx.get("note"):
        lines.append(f"Singer's note: {ctx['note']}")
    return "\n".join(lines) + "\n\nFULL RESULTS:\n" + results_text


def unsupported_claims(writeup: str, results_text: str) -> list[str]:
    """Scores and times in the write-up that the results don't contain."""
    known_scores = {_norm_score(m) for m in _SCORE.findall(results_text)}
    known_times = set(_TIME.findall(results_text))
    bad = [f"{s}/10" for s in _SCORE.findall(writeup) if _norm_score(s) not in known_scores]
    bad += [t for t in _TIME.findall(writeup) if t not in known_times]
    return sorted(set(bad))


def _norm_score(value: str) -> str:
    return f"{float(value):.1f}"


def generate(results_text: str, *, client=None, **context) -> dict:
    """Ask Claude for the write-up. Returns {"status": ..., ...}; never raises."""
    if client is None and not enabled():
        return {"status": "disabled"}
    model = os.environ.get("SINGNEXA_WRITEUP_MODEL", DEFAULT_MODEL)
    effort = os.environ.get("SINGNEXA_WRITEUP_EFFORT", DEFAULT_EFFORT)
    try:
        import anthropic
    except ImportError:
        return {"status": "disabled", "reason": "the anthropic package is not installed"}
    try:
        client = client or anthropic.Anthropic()
        prompt = build_prompt(results_text, **context)
        messages = [{"role": "user", "content": prompt}]
        for attempt in range(2):
            text, response = _ask(client, model, effort, messages)
            if text is None:
                return {"status": "failed", "reason": "declined", "model": model}
            bad = unsupported_claims(text, results_text)
            if not bad:
                return {"status": "ready", "markdown": text, "model": getattr(response, "model", model),
                        "usage": _usage(response)}
            messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": "These are not in the results: " + ", ".join(bad) +
                 ". Rewrite the notes using only scores and times that appear in the results."},
            ]
        return {"status": "failed", "reason": "unsupported_numbers", "model": model, "unsupported": bad}
    except anthropic.APIError as exc:
        return {"status": "failed", "reason": exc.__class__.__name__, "model": model}


def _ask(client, model: str, effort: str, messages: list[dict]):
    kwargs = {}
    if model in FALLBACK_MODELS:
        kwargs = {"betas": [FALLBACK_BETA], "fallbacks": "default"}
    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": effort},
        messages=messages,
        **kwargs,
    )
    if response.stop_reason == "refusal":
        return None, response
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return (text or None), response


def _usage(response) -> dict:
    usage = getattr(response, "usage", None)
    return {"input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None)} if usage else {}
