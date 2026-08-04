# Rubric v6 proposal — onset_accuracy — BUILT, TESTED, REJECTED

**Status: not shipped. The engine remains v5, 7 components. Do not re-propose
this without reading the results below.**

Aaron approved building a v6 proposal on 2 Aug 2026 to score onset accuracy —
how cleanly a note is started — which the engine measures on every take and
scores nowhere. It was implemented in full, regression-tested, and rejected on
the evidence. All engine changes were reverted.

---

## What was built

- `onsets_pct_clean` added to `tools/build_calibration.py` and the pack rebuilt
  from the same 50 references. **Verified: every pre-existing anchor came out
  byte-identical** — the ruler did not move. New anchor: p10 20.98, **p50 33.2**,
  p90 44.81.
- `onset_accuracy` added as an 8th component in `compute_technical_score`,
  weight 0.15, 10 at the professional median (33.2% clean), 0 at 0%.
- Declared **not** capture-sensitive on evidence: Aaron's live takes score
  24.6% clean vs 23.7% home/studio, a difference under one point, so there is
  no sign the room degrades onset detection.

### Why pct_clean and not pct_scooped
The pack already contained `onsets_pct_scooped`. It is the wrong basis:

| | clean | scooped | overshot |
|---|---|---|---|
| 50 professionals | 33.2% | 41.5% | 24.0% |
| Aaron | 19.7% | 49.1% | 29.3% |

On scooping alone Aaron is 7.6 points worse; on clean entrances he is 13.5
points worse, because **he also overshoots more**. Only `pct_clean` sees both
failure modes.

## Why it was rejected

**1. It does not describe reality better.** Against Aaron's 14 by-ear estimates —
the only external ground truth available:

| | correlation | mean abs error | bias |
|---|---|---|---|
| v5 (shipped) | **+0.777** | **0.461** | +0.032 |
| v6 (proposed) | +0.725 | 0.500 | −0.100 |

**2. No weight rescues it.** Sweeping 0.05 → 0.30, only 0.12 beat v5, and by
0.004 — noise. Choosing it after the fact would be exactly the overfitting that
killed two earlier hypotheses in this investigation.

| weight | 0.05 | 0.08 | 0.10 | 0.12 | 0.15 | 0.20 | 0.25 | 0.30 |
|---|---|---|---|---|---|---|---|---|
| error | .471 | .464 | .471 | **.457** | .500 | .507 | .536 | .579 |

**3. It barely helps the takes it was designed for, and hurts one.** The whole
motivation was the ~2-point ear/engine gap on the historical takes:

| take | ear | v5 gap | v6 gap | |
|---|---|---|---|---|
| Lose Control | 5.9 | 2.80 | 2.40 | improved 0.40 |
| 3AM | 6.95 | 1.95 | 1.75 | improved 0.20 |
| Twist & Shout | 6.25 | 1.55 | **1.85** | **worsened 0.30** |

Twist & Shout scored **10.0** on the new component — its 37.4% clean rate is
*above* the professional median. The "pusher / volume chaser" take has better
onset accuracy than the professionals, so the component pushed it further from
Aaron's ear, not closer.

**4. The professionals were fine either way** (median 9.05 → 8.95, mean shift
+0.03), so regression 1 passed — but a change must earn its cost, and this one
did not.

## The cost it would have carried
Every one of 182 archived scores changes; both singer PDFs regenerate; v5 and
v6 scores become permanently non-comparable under rule 3. Not worth paying for
no measured improvement.

## What was done instead (3 Aug 2026) — the ENTRY ACCURACY diagnostic

Aaron asked for the onset measurement to be **reported next to the score without
being folded into it**. That is a different request from v6 and it was built:

- `compute_entry_accuracy()` in the engine — clean / scooped / overshot, each
  with a **percentile against the 50-reference pack**, in the same "matches or
  beats X% of N pro references" language the components already use.
- It emits **no `/10`**, by design. A second ten-point number beside the real one
  is precisely the failure CLAUDE.md rule 1 exists to prevent. A percentile is a
  number that goes up as he improves and cannot be mistaken for the score.
- It lives **outside `compute_technical_score`**, so `rubric_fingerprint` did not
  move and no existing score became non-comparable.
- `onsets_pct_clean` and `onsets_pct_overshot` were added to the calibration
  pack. **Every pre-existing anchor came out byte-identical again, and all 182
  archived scores and every component were verified unchanged** — only
  `calibration_fingerprint` moved (fb035034bebd → 1d3e2991f144), which the
  in-place re-score and the preflight gate handle.

So the rejection stands and the measurement is now visible. Those are compatible.

## What remains true and useful

**Onset accuracy is still a real, measured deficit and a good coaching target —
just not a score component.**

- Aaron lands clean **19.7%** of the time; the professional median is **33.2%**.
  Only 5 of his 75 clean-capture takes reach it. His median sits below the
  professional 10th percentile.
- It correlates with his overall at r = +0.577, so it tracks quality — it simply
  adds nothing the existing seven components were not already capturing.
- Track it as a **raw metric** (`onsets.pct_clean`) alongside cents and dB, the
  way the other diagnostics are used. Do not convert it into a `/10`.

## The wider conclusion

The v5 rubric already matches this singer's ear at r = 0.78 with essentially
zero bias. An eighth component, correctly built and honestly anchored, could not
improve on it. **That is evidence the scoring engine is close to as good as this
metric set allows** — and the strongest argument yet against further rubric
tinkering.

The two documented blind spots in `SCORE_READING_LIMITATIONS.md` stand: read
`intonation_accuracy` alongside `onsets.pct_scooped`, and never quote a headline
without its weakest component. Those are interpretation rules, and they cost
nothing.
