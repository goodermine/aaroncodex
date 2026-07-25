# Handoff — score provenance pinned; stale scores retired

Date: 2026-07-25

Closes the "Required canonical fix" list in
`CANDI_SCORE_INCIDENT_AND_RILDA_COMPARISONS_2026-07-25.md`, and removes every
stale score from the repo so none can be quoted again.

## The rule, in one line

**A score may only be compared, trended or displayed next to another score whose
identity matches. A score with no identity is legacy — re-score it, never quote
it.**

## 1. Every score now carries a deterministic identity

`compute_technical_score()` returns an `identity` block:

```json
{ "contract": "voxai_score_v1",
  "rubric": "deterministic_rubric_v4",
  "rubric_fingerprint": "3478e29a0ee5",
  "calibrated": true, "calibration_references": 50,
  "calibration_fingerprint": "18b7fbeec6ba",
  "stem_model": "UVR_MDXNET_Main",
  "take_fingerprint": "bafa008ffcd2" }
```

- `rubric_fingerprint` hashes the scoring **source**, so a silent change to the
  maths shows up even if nobody bumps the version.
- `calibration_fingerprint` identifies the reference pack — same rubric against a
  different pack is still a different scale.
- `take_fingerprint` identifies the recording, so two scores can be checked to be
  of the *same take*. (Derived from file identity + duration + sample rate + note
  count — not a hash of audio bytes, which the scorer never sees.)
- **No timestamp, deliberately.** Identity answers "what would produce this same
  number", so it must stay deterministic: identical audio + identical engine →
  identical score *and* identical identity. Record when an artifact was written
  alongside it, not inside it.

## 2. Comparison is enforced, not advisory

```python
from analyse_song import is_legacy_score, scores_comparable, score_conflict

is_legacy_score(score)       # True => never quote/compare/trend; re-score
scores_comparable(a, b)      # True => may be compared / shown side by side
score_conflict(a, b)         # None, or a plain-English reason it's refused
```

Use `score_conflict` **before** putting two numbers together — including a take
against a reference recording. It fails closed: unknown provenance is refused.

## 3. Only one engine may issue a `/10`

The reference-comparison analyser must publish **raw contour/difference measures
only** — never a competing overall score. If a second scorer is ever added, its
output must carry its own identity and will be refused for comparison
automatically rather than silently disagreeing (this is what produced the
5.1-vs-8.3 confusion).

## 4. Stale scores are gone from the archive

`docs/score-metrics/retire_legacy_scores.py` replaced the stored score in **31
archived analyses** (rubric v1 and v2) with a stub carrying **no numbers**:

```json
{ "status": "retired_legacy_score", "retired_rubric": "deterministic_rubric_v1",
  "reason": "...", "action": "re-score with rescore_all.py", "do_not_use": true }
```

- **Raw measurements untouched** — every take re-scores exactly as before
  (verified: v4 scores byte-identical before and after retirement).
- The superseded **v3 last-10 snapshot and its tooling were deleted**
  (`last10-rescore-*.{json,md}`, `rescore.py`).
- `HANDOFF_SCORE_METRICS_UPDATE_2026-07-25.md` is now marked
  **diagnosis-trail-only, do not quote any number in it**.
- Original numbers remain in git history for audit; they are simply no longer
  reachable by anything that reads a score.

Run it after pulling new analyses (idempotent):

```
python3 docs/score-metrics/retire_legacy_scores.py --dry-run   # report
python3 docs/score-metrics/retire_legacy_scores.py             # apply
python3 docs/score-metrics/rescore_all.py                      # refresh the table
```

## 5. It's visible everywhere a score appears

- **Full-results text / Telegram:** a current score prints
  `Scored by: deterministic_rubric_v4 · build … · stem … (only compare with
  scores carrying this same identity)`. A legacy score prints
  `! LEGACY SCORE — produced by a superseded rubric. Do not quote, compare or
  trend it; re-score this take with the current engine.`
- **Analyze deck badge:** shows the rubric alongside the calibration line; a
  legacy score is visually drained (greyed, de-emphasised) and shows a red
  warning that overrides the capture-fair hint.

## 6. Tests

`voxanalysis/vox-analysis/engine/tests/test_scoring.py` (7 tests) covers: identity
present + deterministic; legacy scores refused; different calibration packs
refused; and Candi's **integration requirement** — one take through every entry
point returns the same canonical score or an explicit provenance conflict, never
two silently different numbers.

## For Candi

- The workspace score guard stays as-is; this makes its job easier — call
  `is_legacy_score()` / `score_conflict()` instead of inferring from ledgers.
- **Any report still carrying a legacy score must be re-scored before quoting.**
  Historical reports with unknown provenance = `needs manual review`, excluded
  from progress trends (Candi's item 6).
- Rilda's `Dreams` / `You Sexy Thing` 5.1s were the motivating case — retired;
  current scores are **8.3** and **8.0**.
