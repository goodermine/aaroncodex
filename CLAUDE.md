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
> blocked Aaron's best Pressure Down take (8.3 / **9.5 capture-fair**).

## 5. Which number to give the singer

- **Studio / clean capture** → lead with **overall**.
- **Live, tavern, phone, room** → lead with **capture-fair**. It excludes the
  components that measure the microphone rather than the voice
  (`voice_quality`, `dynamics_expression`), and typically reads ~1 point higher.
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
