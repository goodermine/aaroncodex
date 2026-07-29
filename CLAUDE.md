# Working rules for this repo

Read this before doing anything with scores, analyses, or reports. These rules
exist because each one was broken in practice and a real singer was given a wrong
number as a result.

---

## 1. There is exactly ONE scoring engine. Never write your own.

The only thing permitted to produce a `/10` is:

```
voxanalysis/vox-analysis/engine/analyse_song.py  ->  compute_technical_score()
```

- **Do not** re-implement, approximate, cache, adjust, round, or "sanity-check"
  a score with your own logic or a separate ledger.
- **Do not** let a comparison/reference analyser emit a competing overall score —
  it may publish raw contour/difference measures only.
- If you have a local scoring path in your own workspace, it is **wrong by
  definition**. Delete it and call this engine.

> This is what produced the `5.1` vs `8.3` confusion and the withdrawn `9.5`:
> two implementations, silently disagreeing.

## 2. Run preflight before publishing any score

```bash
python3 tools/score_preflight.py
```

Exit 0 = safe to publish. **Exit 1 = do not publish a number**, follow its
instructions (usually `git fetch origin main && git merge --ff-only origin/main`).

It verifies the engine matches the repo's pinned contract, calibration is loaded,
and no stale scores remain. A stale engine scores **~2.5–3 points too harshly** —
that is the single most damaging failure mode here.

## 3. Never quote a score without current provenance

```python
from analyse_song import is_legacy_score, scores_comparable, score_conflict
```

- `is_legacy_score(score)` → **True means never quote, compare or trend it.**
  Re-score the take.
- Before putting two numbers side by side (including a take vs a reference
  recording), call `score_conflict(a, b)`. Non-`None` = refuse.
- Archived analyses whose stored score was retired carry
  `technical_score.status == "retired_legacy_score"`. That is not a score. Do not
  reconstruct a number from it; re-score.

**Trends and comparisons are covered by the same rule.** Score trends may only
combine takes from the same rubric + calibration pack (`tools/progress_report.py`
excludes the rest and says so); a take-vs-original comparison withholds the score
pair on conflict and reports the raw measures instead. Raw metrics (cents, dB, %)
are always comparable — only *scores* need provenance.

Refresh everything after new takes land:

```bash
python3 docs/score-metrics/retire_legacy_scores.py   # strip stale scores
python3 docs/score-metrics/rescore_all.py            # rebuild the score tables
```

## 4. Withhold a score ONLY on a provenance conflict

Legitimate reasons to withhold: `is_legacy_score()` is true, `score_conflict()`
is non-`None`, preflight fails, or separation did not run (a full-mix score is
meaningless — say so rather than publishing it).

**Not** a reason to withhold:

- capture-sensitive dynamics, or a low/odd dynamics component
- a low `voice_quality` on a live/room/phone recording
- the score being lower or higher than expected

> Dynamics **cannot** reach 0 under the current rubric — it is graded and floored,
> and excluded from capture-fair by declaration. Any guard keyed to "dynamics
> zeroed" is obsolete and will only produce false withholdings. This wrongly
> blocked Aaron's best Pressure Down take (8.2 / **9.2 capture-fair** under v5;
> it read 8.3 / 9.5 under v4, before breath support entered the score).

## 5. Which number to give the singer

- **Studio / clean capture** → lead with **overall**.
- **Live, tavern, phone, room** → lead with **capture-fair**. It excludes the
  components that measure the microphone rather than the voice
  (`voice_quality`, `dynamics_expression`), and typically reads ~1 point higher.
  It does **not** exclude `breath_support` (v5) — phrase-ending sag is air
  running out, not the room, so a live take is still scored on it.
- Always state **confidence**, and that the scale is **calibrated to 50
  professional reference vocals — 10 = a typical pro**. A 7 is a good amateur
  result, not a failure.
- Never substitute a rounded, "listener-impact", legacy or manually adjusted
  number.

## 6. Always send the FULL results, never a summary

```python
from report_builder import build_v2_report, render_full_results_text
text = render_full_results_text(build_v2_report(raw), result)
```

or `GET /api/pitch-jobs/{id}/full-results`.

This is the single source of truth and matches the web page exactly. Send all of
it — chunk across messages for Telegram's 4096-char limit; never truncate, never
hide it in a file only. If a score is withheld, **still send everything else**:
only the headline `/10` is ever withheld, never the analysis.

## 7. Don't coach off a capture artefact

The engine picks `PRIMARY FOCUS` as the lowest-scoring component, which on a live
capture is often `voice_quality` — i.e. the room, not the singer. Check whether
the weak component is capture-sensitive before turning it into coaching advice.

## 8. An analysis is not done until the singer has been GIVEN the results

Running the engine, committing the JSON and pushing the branch is **plumbing, not
delivery.** The job is done only when the person who asked has received the
**actual analysis** — not a git status.

After every analysis you run, you MUST hand back, in the conversation:

1. **The headline `/10`** — with the right number led per rule 5 (overall for a
   clean capture, capture-fair for live/room/phone), stated confidence, and the
   "10 = a typical pro" anchor.
2. **The full results** — rendered via rule 6
   (`render_full_results_text(build_v2_report(raw), result)` or
   `GET /api/pitch-jobs/{id}/full-results`). Send all of it; chunk for length.
   Never hide it in a committed file only.

A commit hash, a branch name, "preflight passed" and "worktree clean" are
**confirmations of the plumbing** — necessary, but they are NOT the deliverable
and never stand in for it. If you cannot render the full results for any reason,
say so explicitly and give the headline score plus the component table — never
report "complete" with nothing the singer can read.

> This rule exists because a full, valid analysis of "Reasons" (8.0/10) was
> computed, verified, committed and pushed — and the singer was handed only a
> commit hash and a row of green checkmarks. The one thing the whole system
> exists to produce, the result, was the one thing not delivered.

---

## Repo orientation

- `voxanalysis/vox-analysis/engine/` — the analysis engine and rubric (canonical).
- `voxanalysis/vox-analysis/viewer/` — API + Analyze deck + `report_builder.py`.
- `voxsuite/` — unified server (Analyze / Polish / Fused + `/monitor`) on one origin.
- `pitchmonitor/` — real-time pitch monitor, served at `/monitor`.
- `docs/score-metrics/` — pinned score contract, score tables, re-score tooling.
- `docs/handoffs/` — operational handoffs. Read the score ones before scoring.
- `design/` — shared UI kit, vendored into apps by `design/sync.sh`.

Tests: `voxanalysis/vox-analysis` (pytest) and `voxsuite` (pytest). Run the
scoring tests after touching the rubric: `engine/tests/test_scoring.py`.
