# Handoff — Scoring issues & how the score actually works

_Context: Aaron and Candi both ran takes and got **3.9/10**, and the natural
question was "is that a calibrated score or mine?" This note explains what the
number is, why it lands where it does, and the concrete issues we've hit so
someone can pick them up cleanly._

All references are to `voxanalysis/vox-analysis/engine/analyse_song.py` unless
stated. The score is built in `compute_technical_score()` (~line 2037) and
surfaced to the deck by `viewer/report_builder.py`.

> **Read together with `CANDI_SCORE_INCIDENT_AND_RILDA_COMPARISONS_2026-07-25.md`.**
> That handoff covers a _different_ scoring problem: the **same vocal stem gets
> different `/10` scores from different engines/rubrics** (e.g. Phase 1 ledger
> 5.1 vs a comparison engine 8.3; a stale 9.5 vs a recomputed 6.5), and the
> provenance controls needed to stop that. **This** doc covers the
> _single-engine rubric semantics_ — what the calibrated number means and why it
> lands where it does. Neither replaces the other; the cross-engine provenance
> problem is the higher-severity one for anything user-facing.

---

## TL;DR

- The score **is calibrated** — anchored to a pack of **50 professional
  reference takes** (`engine/calibration/pro_reference.json`, `pro_reference_v1`:
  Whitney, Adele, Mariah, Beyoncé, Chris Stapleton, Billy Joel…).
- On each component, **"10" is the professional _median_** (`best = stats["p50"]`,
  ~line 2027), and **"0" is a theoretical worst anchor**. So a competent amateur
  scoring **~3.9 is 3.9 against a world-class bar** — the number is "correct,"
  it's just benchmarked against elite pros, not against other hobbyists.
- There's a second number, **`capture_fair_score`**, that excludes the
  microphone-sensitive voice-quality metrics. For phone/room recordings this is
  the fairer headline, and it's currently under-surfaced.

The score is **not** broken. The issues below are about **communication,
one doc/code mismatch, capture fairness, and a couple of things worth verifying.**

---

## How the score works (so the issues make sense)

Deterministic rubric v3 — same audio always yields the same number, no LLM
involvement. Six weighted components (weights renormalised over whichever are
measurable), ~lines 2062–2215:

| Component | Weight | Measures |
|---|---|---|
| intonation_accuracy | 25% | median \|cents\| off the tuning-corrected grid |
| voice_quality | 20% | Praat jitter / shimmer / HNR / CPPS on sustained notes |
| pitch_stability | 15% | median intra-note drift (cents) |
| vibrato_control | 15% | vibrato quality **or** straight-tone steadiness |
| dynamics_expression | 15% | phrase-level shaping / effective range |
| phrase_control | 10% | median phrase duration (breath management) |

Each component maps its measured value linearly from **worst → 0** to
**pro-median → 10** (`_linear_component` ~line 2014, `_scale` ~line 1990). Values
better than the pro median clip at 10; values past the theoretical worst clip
at 0.

**Why amateurs land low:** the two axes that most separate pros from amateurs
are voice_quality (jitter/shimmer/HNR — very clean in pros) and intonation. An
amateur can be genuinely good and still sit at ~40–60% of the pro-median bar on
several axes, which is a 4–6 on those components and drags the weighted overall
into the 3–5 range. Working as designed — but not obvious to a user.

---

## The issues

### 1. Users can't tell the score is calibrated (severity: high — it's the actual question asked)
Aaron asked directly: _"is that a calibrated score or mine?"_ The engine already
computes provenance — `provenance`, `calibration.active`, `calibration.n_references`
(~lines 2249, 2268) — and the deck payload carries `calibration_references`
(`report_builder.py` ~line 328). But the deck doesn't put it in front of the
user. **Fix direction:** surface a one-line badge near the score, e.g.
_"Calibrated to 50 professional reference takes — 10 = a typical pro."_ That one
sentence reframes 3.9 from "I failed" to "3.9 against Whitney Houston."

### 2. Doc/code mismatch on the "10" anchor (severity: medium — real inconsistency)
`_linear_component`'s docstring (~line 2018) says the anchor is _"p25 for
lower-is-better metrics, p75 for higher-is-better"_ — but the code uses
**`best = stats["p50"]`** (the median) for every metric (~line 2027). Anyone
reasoning about the scale from the docstring will be wrong by a whole quartile.
**Fix direction:** decide which is intended and make them agree. If p50 is
intended (10 = typical pro), fix the docstring. If p25/p75 was intended (10 =
top-quartile pro, which would push everyone's scores _down_ further), that's a
deliberate scaling change and should be decided, not left ambiguous.

### 3. Capture-fair score is under-used (severity: high for phone recordings)
voice_quality (jitter/shimmer/HNR/CPPS) partly measures the **recording chain**,
not the singer — mic, room, distance, mastering, and stem-separation artefacts
all move it. `capture_fair_score` re-runs the rubric with voice_quality removed
(~lines 2224–2236). For Aaron recording on a phone in a room, the 20%
voice_quality slice is likely penalising the _capture_, not the _voice_, so his
capture-fair number is probably meaningfully higher and fairer. **Open
question / fix direction:** for non-studio captures (we already flag
`environment_risk.karaoke_or_room_contamination_risk`, ~line 2238), consider
leading with capture-fair, or at least showing both with a plain-English "use
this one if you recorded on a phone" note. The engine already emits
`capture_fair_note` explaining this — again, it's just not surfaced.

**Gap capture-fair does _not_ close (from Candi's incidents):** `capture_fair`
only drops **voice_quality** (`fair = {k: v … if k != "voice_quality"}`,
~line 2231). But Candi hit a case where the **dynamics_expression** component
went to **zero** because a _separated vocal stem's_ dynamic range exceeded the
rubric's capture-sensitive threshold — a calibration artefact, not the singer
performing flat. That zero is still inside capture-fair, so capture-fair does
**not** protect against it. Either dynamics needs the same capture-sensitivity
handling, or capture-fair should also exclude a capture-flagged dynamics
component. This is why Candi's workspace currently _withholds_ the overall score
when dynamics zeroes out on a separated stem.

### 4. Does the scale discriminate? — partly answered, still worth a clean test (severity: medium)
The initial worry was two takes both landing at **3.9/10** (Aaron's _"The Heat is
On"_, Candi's _"Brighton Hotel"_), suggesting the amateur band might be
compressed. Candi's later data shows the scale **does** spread — 5.1, 6.5, and
8.3 across her recent takes — so it isn't collapsing everyone to one number.
**But** those numbers came from _different engines/rubrics_ (see her handoff), so
they don't cleanly prove discrimination within one engine. **Action:** run
several takes of clearly different quality through a **single pinned**
`compute_technical_score` and confirm the spread (pros ~8–10, strong amateurs
~6, rough takes ~2–3). Do this only after the cross-engine provenance issue is
pinned, or the result is confounded.

### 5. Fused mode scores the full mix when separation is unavailable (severity: high — from the beta audit, B3)
See `docs/beta-readiness-audit.md` §B3. When stem separation is unavailable, the
Fused path scores bass+guitar+vocals together and still shows a confident
scorecard — a meaningless (usually low) number presented as a real result.
**Note:** separation was also **environmentally blocked in the sandbox** (403 on
the RoFormer model download), so some of our low test scores were this, not the
singing. **Fix direction:** when separation didn't run, either suppress the
score or clearly mark it "full-mix, not vocal-isolated — not comparable."

### 6. Confidence is computed but quiet (severity: low)
`confidence` (high/medium/low) already downgrades on room/karaoke contamination
and low note counts (~lines 2238–2246). Make sure the deck shows it next to the
score — a "medium confidence" tag changes how a 3.9 should be read.

---

## What is NOT wrong

- The maths is deterministic and auditable — every component reports its input,
  formula, and weight. Aaron's own read was _"that score is correct"_ and that's
  consistent with the design.
- Calibration is present and healthy (50 references, 13 metrics, n=50 each).
- v2/v3 already added real fairness fixes: straight-tone singing isn't punished
  for lacking vibrato, compressed masters don't punish dynamics, short pop
  phrasing isn't treated as a breath defect (~lines 2052–2060).

---

## Suggested order of work

0. **Pin score provenance / stop dual scoring** — the canonical fix in Candi's
   handoff (engine + rubric + stem-model + audio-hash stamped on every score;
   only compare scores of the same identity; one canonical scoring engine).
   Highest severity: it's what let the same stem read 5.1 and 8.3. Everything
   below assumes a single pinned engine.
1. **Surface provenance + confidence + capture-fair on the deck** (issues 1, 3,
   6) — high impact, no engine risk, directly answers the question users are
   asking.
2. **Handle dynamics capture-sensitivity** (issue 3, gap) — give
   dynamics_expression the same capture-sensitive treatment as voice_quality, or
   exclude a capture-flagged dynamics from capture-fair, so a separated stem
   doesn't zero it and drag/withhold the score.
3. **Resolve the p50 vs p25/p75 doc/code mismatch** (issue 2) — decide intent,
   make code and docs agree.
4. **Run the single-engine discrimination spread test** (issue 4) — after step 0.
5. **Guard the Fused full-mix score** (issue 5) — coordinate with the B3 fix in
   the beta audit.

_Beyond step 0's provenance plumbing, the rest is surfacing what the engine
already computes, one capture-sensitivity fix, one docstring fix, and one data
check — no re-training or LLM changes._
