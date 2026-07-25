# Handoff — score-metrics update from the last 10 analyses

Date: 2026-07-25

**What this is:** the 10 most recent singer takes in
`voxanalysis/archive/scratch-analyses/` re-scored with the **current** engine
(`deterministic_rubric_v3`, calibration active, 50 pro references), so we have a
current-engine picture of how the score behaves on real takes. This is the
"discrimination spread test" flagged as issue #4 in `HANDOFF_SCORING.md`, run on
real data.

**Data committed alongside this note:**
- `docs/score-metrics/last10-rescore-2026-07-25.json` — full per-take metrics + components + raw features.
- `docs/score-metrics/last10-rescore-2026-07-25.md` — the same as readable tables.

Regenerate with `docs/score-metrics/rescore.py` (loads `compute_technical_score` + the
committed calibration and re-scores the archive).

---

## Headline numbers

| | min | max | mean | spread |
|---|--:|--:|--:|--:|
| **overall (v3)** | 6.6 | 9.3 | 7.97 | 2.7 |
| **capture-fair (v3)** | 6.6 | 9.7 | 8.17 | 3.1 |

All 10 came back **high confidence**. Takes span Aaron, Rilda, Chris and Leo.

---

## Findings

### 1. The scale discriminates — the "everyone gets the same number" worry is unfounded here
Overall scores spread **6.6 → 9.3** across the 10 takes. The earlier 3.9/3.9
coincidence was not the scale collapsing; on this set it separates takes by ~3
points with clear per-component reasons.

### 2. The current rubric (v3) reproduces the archived v2 scores almost exactly
Per-take v2→v3 change **never exceeds 0.1**. The rubric version bump did not move
these numbers, so the archived scores are still trustworthy and no historical
re-score is needed for ranking. (Provenance still matters per Candi's handoff —
this is about the rubric maths being stable, not about cross-engine identity.)

### 3. `voice_quality` is the volatile, capture-driven axis — and capture-fair rescues it
`voice_quality` ranges **2.56 → 10.0**, and its lowest values are the room/live
captures, driven by shimmer and HNR (the recording chain), not the singing:

| take | voice | shimmer% | HNR dB | overall | capture-fair | Δ |
|---|--:|--:|--:|--:|--:|--:|
| come-out-and-play — Captain Cook **Tavern** (aaron) | 2.56 | 17.6 | 9.65 | 6.6 | **7.7** | +1.1 |
| chasin-that-neon-rainbow (leo) | 4.53 | 15.1 | 10.54 | 8.7 | **9.7** | +1.0 |
| feeling-good (chris) | 3.73 | 15.8 | 10.46 | 7.7 | **8.7** | +1.0 |

This is concrete evidence for issue #3 in `HANDOFF_SCORING.md`: for phone/room
captures the capture-fair number is ~1 point higher and fairer. **Recommendation
stands:** surface capture-fair (and lead with it when
`environment_risk` is elevated).

### 4. NEW: `dynamics_expression` scores 10.0 on **all 10** takes — it isn't discriminating
Every take maxes the 15%-weighted dynamics component. Combined with Candi's
incident (a separated stem's dynamics went to **0**), dynamics currently behaves
**bimodally** — 10 normally, 0 on a capture artefact — rather than as a graded
signal. Net effect: 15% of the weight is either a constant or a landmine, never
an informative middle. **Action:** review `dynamics_expression`'s anchors/inputs;
either make it grade meaningfully or reduce its weight, and give it the same
capture-sensitivity handling as voice_quality (see `HANDOFF_SCORING.md` issue 3
gap).

### 5. `pitch_stability` is the other big swinger — and corroborates Rilda's coaching note
Held-note drift drives pitch_stability from **0.0 → 10.0**. Rilda's takes have
the worst drift (this-masquerade 118.6 c → pitch 0.0; lets-stay-together 73.2 c →
pitch 1.23), which matches Candi's finding that Rilda's held-note drift is her
main gap. Note her overall still lands **8.1–8.3**: one zeroed component does
**not** tank the weighted overall — useful context for how much any single
capture-sensitive zero actually costs.

### 6. The 3.9 incident is not reproducible from repo data — and that's expected
None of these 10 archived takes re-scores below **6.6**. Aaron's reported 3.9 is
not in this archive; it's most likely a newer phone/live take living in Candi's
workspace (intentionally not committed). The **tavern take (6.6, voice 2.56)**
shows the mechanism by which a rough capture drags the number down, but we can't
reproduce the exact 3.9 here. Don't claim the 3.9 is explained — flag it as
"needs the actual take" if it matters.

---

## What to do with this

1. **Lead with capture-fair for non-studio captures** (finding 3) — highest
   user-facing impact, no engine risk.
2. **Fix `dynamics_expression`** (finding 4) — it's 15% of the weight doing no
   grading work; make it informative or reweight, and handle capture-sensitivity.
3. **Keep provenance pinning as the top priority** (Candi's handoff) — this
   re-score is single-engine and clean, but the moment a second engine scores the
   same audio the numbers diverge.
4. No historical re-score needed for ranking (finding 2).

_All numbers here are reproducible: `python3 docs/score-metrics/rescore.py` over the
committed archive + calibration._
