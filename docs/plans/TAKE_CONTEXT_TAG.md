# Plan — optional take-context tag ("I'm still learning this one")

Stated by Aaron, 29 Jul 2026.

## The problem it solves

A first-ever attempt at a new song, or a take where the singer is *learning* a
new skill, gets scored on the same 50-pro scale and then ranked head-to-head with
songs they have drilled dozens of times. That is unfair and it hides the real
story.

The clearest example in the archive: Aaron's **You Sexy Thing** — 14 takes,
capture-fair from **4.6 up to 9.1**. That was the first song where he learned to
cross the passaggio into M2 and reach higher notes. Every *low* take was actually
his *highest reach* (topping G5/G♯5 at the edge of the new register). The engine
scored the reach honestly, but on a flat leaderboard those learning takes look
like failures next to a polished performance. They were the opposite: they were
the work that *built* the voice that later sang Farnham.

## The idea

An **optional** value the singer sets **when uploading or recording** a take,
declaring its intent — e.g. *first-time / learning this song* — so it is not
judged flat against their better, heavily-practised performance takes.

## Design decisions (made 29 Jul)

1. **Optional, set at capture/upload time.** Absent = `performance` (the default).
   No existing take changes meaning; everything already in the archive is a
   `performance` take unless retagged.

2. **A small preset, plus an optional free note:**
   - `performance` (default) — a real attempt, ranked normally.
   - `learning` — first-time / still learning this song or a new technique.
   - `warmup` — a throwaway warm-up, not meant to be judged.
   - optional `context_note` free text, e.g. "first time reaching the high note".

3. **It is METADATA. It NEVER touches the score.** This is the hard rule. The
   engine still produces the honest measured `/10` (CLAUDE.md rule 1 is
   untouched — no inflation, no deflation, no adjustment keyed to the tag). A
   learning take that measures 4.6 is still a 4.6. The tag only changes how the
   take is **grouped and presented**, never its number.

4. **How ranking honours it:**
   - **Performance** takes form the leaderboard, the per-song best-of, and the
     "mean of your takes" stat.
   - **Learning / warm-up** takes are pulled into their own *"Learning / in
     progress"* section — shown, never hidden, but not ranked against
     performance takes and excluded from best-of and the performance mean.
   - Learning takes are exactly what the **per-song learning-curve** view wants
     (see the You Sexy Thing arc): there, low scores at high reach are the point.

5. **Provenance-safe by construction.** Because the tag is declarative context
   and not a score input, it cannot reopen the "two different numbers for one
   take" problem. Scores stay comparable across takes regardless of tag; only the
   *grouping* differs.

## Where it touches the system

- **Capture / upload UI** (`design/vox-record.js` and the upload form): an
  optional intent selector + a note field. Default `performance`, one tap to
  change.
- **Pipeline → analysis JSON:** carry the choice through to a `take_context`
  block, e.g. `{"intent": "learning", "note": "first time on the high note"}`.
  Stored alongside the take; passed through untouched by the engine.
- **Ranking / report tooling** (`tools/progress_report.py`, the ranked-list and
  best-of views, `report_builder`): read `take_context.intent` and separate
  learning/warm-up from performance as above. Absent → treat as `performance`.
- **Reports:** show the tag and note so the context travels with the result
  ("Learning take — first time on the high note").

## Also expose it to other singers

Rilda (and anyone) gets the same option — so a singer trying a hard new song can
mark it "still learning" and see it judged fairly, in its own section, rather
than dragging down or hiding under their polished takes.

## Not in scope

- No auto-detection of "learning" from the audio. It is the singer's declaration.
- No score change of any kind. If a future idea wants the *score* to react to
  context, that is a separate proposal and must go through the rubric, not this
  tag.
