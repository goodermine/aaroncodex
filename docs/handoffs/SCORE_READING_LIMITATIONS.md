# How to read a VOXAI score — five measured limitations

Findings from a deliberate validity investigation on 1–2 Aug 2026. Aaron
supplied historical takes he *knew* contained severe faults, to test whether
the engine would catch them. It did — but not where anyone was looking.

**Read this before quoting any `/10` to a singer.** Nothing here contradicts
rule 1: the engine remains the only scorer and the scores below are exactly as
measured. These are limits on *interpretation*, not on the engine's arithmetic.

---

## 1. A single catastrophic component cannot drag the headline below ~8

Demonstrated twice, independently, on two takes from different years:

| Take | The fault the engine found | OVERALL |
|---|---|---|
| Kryptonite (2024) | `breath_support` **1.25** — 82.9% of phrase ends sagging | **8.4** |
| 3AM (2019) | `pitch_stability` **2.31** — 67.1c held-note drift, 52% of entries scooped from 122.9c below | **8.9** |

Both takes were correctly diagnosed. Both headlines looked healthy.

**Why:** the overall is a weighted mean. `breath_support` and `phrase_control`
carry 0.10 each; `pitch_stability`, `vibrato_control` and `dynamics_expression`
0.15 each. A near-zero on a 0.10-weight column costs under a point. With the
other six components at 9–10, no single failure can produce a "bad" headline.

**Practice rule:** **never quote the overall alone.** Quote it with the weakest
component, always. The full report already prints `PRIMARY FOCUS` (the lowest
component) — that line is not decoration, it is the other half of the score.
A take can be an 8.9 and still contain a 2.31.

## 2. Grid deviation saturates at ±50 cents — gross errors are invisible

`intonation_accuracy` measures distance from the nearest equal-tempered grid
point. The nearest grid point is never more than 50 cents away, so **±50c is a
hard ceiling**. On the 2024 Lean On Me take, every one of the eight
worst-intonation notes reported exactly `-50.0`:

```
0:41 C3 -50.0   0:47 C3 -50.0   0:53 C3 -50.0   1:09 D#4 -50.0
1:13 F#3 -50.0  1:15 A#3 -50.0  ...
```

A note sung 80 cents flat is not reported as 80 cents flat. It is reported as
**the semitone below, sung 20 cents sharp** — and scores well. The metric can
see near-misses; it structurally cannot see a note that lands closer to the
wrong pitch.

There is a second, related bias: intonation scores **where a note settles**,
not the approach. Scooping is measured separately under `onsets` and does not
feed the intonation column at all. A take with 52% of entries scooped from
over a semitone below can still read `intonation_accuracy: 10.0`.

**Practice rule:** read `intonation_accuracy` together with
`onsets.pct_scooped` / `median_scoop_depth_cents`. A listener hears the
approach; the intonation column does not. This is why a singer's ear and the
engine can disagree while both are correct.

## 3. Contaminated stems produce impossibly perfect pitch — check signal first

Eight of Aaron's earliest archived takes (Feb–May 2026) carry
`separator: unknown` and show a physically impossible signature:

| Take | dev | drift | HNR | jitter |
|---|---|---|---|---|
| Rebel Yell | **0.0c** | **0.0c** | 7.5 dB | 4.7% |
| Lonely Boy | 10c | **0.0c** | 5.3 dB | **5.9%** |
| *(clean takes for contrast)* | 20–27c | 32–51c | 19–25 dB | 0.4–0.9% |

**A human cannot sing at 0.0 cents deviation with 0.0 cents drift.** Perfect
stability plus filthy signal quality is the signature of a pitch tracker
locking onto **backing instruments**, which are perfectly in tune and do not
wobble. These takes' pitch metrics describe the band, not the singer. CLAUDE.md
rule 4 already covers this: a full-mix score is meaningless — say so rather
than publishing it.

**Practice rule — the validity gate, run it BEFORE believing any pitch number:**

| Signal | Verdict |
|---|---|
| HNR ≥ 15 dB, jitter < 1.5%, separator named | measurement is sound |
| HNR < 13 dB or jitter > 2% **with** implausibly low deviation/drift | contamination — withhold, re-separate |

## 4. `pitch_stability` bottoms out at 80 cents of drift — "bad" and "far worse" score the same

The component is linear between two anchors and then stops:

```
formula: 10 at pro-reference median (24.25 cents), 0 at 80 cents, linear
```

Past 80 cents of median intra-note drift the score is 0.0 and **cannot fall
further**, so the engine has no way to say that one take is much worse than
another:

| Take | median intra-note drift | pitch_stability |
|---|---|---|
| Bad Things (2024) | **115.3c** | 0.00 |
| Mustang Sally (2024) | **112.4c** | 0.00 |
| You Spin Me Round (2024) | 80.3c | 0.00 |
| The Heat Is On (2026) | 81.2c | 0.00 |

115.3c is 44% worse than 80.3c and scores identically. Combined with
limitation 1 — a 0.15-weight component cannot move the headline much anyway —
this is the mechanism behind the blind-test result below: **a listener keeps
hearing a note get worse long after the score has stopped moving.**

This is not a defect in the anchors. 80 cents is already four-fifths of a
semitone of wander inside a single note; the pack's professionals sit at 24c.
It is a limitation on *reading*, exactly like the other three.

**Practice rule:** when `pitch_stability` reads 0.0, the score has stopped
measuring. Quote `intonation.median_intra_note_drift_cents` beside it — that
number keeps going, and it is what the ear is tracking.

## 5. ENTRY ACCURACY is measured in the region separation damages most

Peer-reviewed voice-science research on onset (folded into the library as
`01-vocal-science-technique/vocal-onset-how-notes-begin.md`, 40+ citations)
carries a finding aimed squarely at how the engine measures onsets:

> Voicing detection and F0 estimation degrade as SNR falls, and **the damage
> concentrates in the quiet onset region — exactly where scoop/overshoot lives —
> so automated scoop statistics from stem-separated audio can be artefacts, not
> singing.** (Dai & Dixon; Mauch & Dixon; separation-SNR literature.)

The engine measures `onsets.pct_clean/scooped/overshot` from **RoFormer-separated
vocal stems** — precisely the condition the research flags. The tracker is least
reliable in the first ~20–60 ms of a note, octave errors cluster at note starts,
and separation bleed is loudest where the note is quietest. So an absolute
onset number ("23.7% clean") carries more measurement noise than a steady-state
number like deviation, which is read from the settled middle of the note.

**What protects the finding, and what does not.**

- **The percentile is more trustworthy than the raw percent.** Aaron's 50
  professional references run through the *same* RoFormer pipeline, so whatever
  separation does to onset detection, it does to both sides. "16th percentile
  against the pack" is a same-pipeline comparison and largely survives; "23.7%
  clean" as an absolute is softer. This is the same logic as capture-fair —
  compare like measured against like.
- **The contamination gate already removes the worst cases** (limitation 3): a
  degraded stem with superhuman onset numbers is withheld, and 7 of Aaron's takes
  are. But the gate catches gross band-lock, not the subtler onset-region noise on
  an otherwise clean separation.
- **The honest gold standard, per the research, is a dry clean solo vocal** —
  recorded direct, not separated from a backing. Aaron's supply-your-own-backing
  path already produces this for home takes; those onset numbers are the ones to
  trust most, and a live-room stem the least.

**Practice rule:** quote the onset **percentile**, not the bare percent, and note
when a take was stem-separated. For a definitive onset read — the one that would
justify a coaching pivot — use a dry solo recording, exactly as the onset
document's Stage 0 says. The engine's onset numbers are a good weekly tracking
signal on consistent captures; they are not a lab measurement.

## 6. (added 2 Sep 2026) `pitch_stability` is on the wrong ruler for every post-16-Aug take

The 16 Aug drift fix removed a fabricated 0.0 drift from every note shorter than
the smoothing window. That moved the drift scale ~2.5× for everything analysed
afterwards, but the 50 references and 209 archived takes were not re-analysed,
so post-fix takes are scored against a pro anchor (24.25 c) that emulates to
~62.5 c on the fixed engine. Result: six of the eleven Aaron takes merged since
22 Aug read `pitch_stability` 0.0 regardless of the singing. Full evidence and
the fix in `docs/VOX_SYSTEM_REVIEW_2026-09-02.md` §3.1.

**Practice rule:** do not quote `pitch_stability` on a post-fix take (the
report builder withholds it). Quote the held-drift median against the emulated
professional band (p10/p50/p90 = 23.7 / 37.5 / 51.2 c) — Aaron's archive
median is 47.9 c, about ten cents wider than a typical pro. Preflight fails
until the pack is rebuilt; `measurement_fingerprint` now travels with every
score so this cannot recur silently.

## What the validity test did NOT establish

Three historical takes (2019 ×1, 2024 ×2) against 65 recent clean captures is
not a baseline. Breath and stability span nearly the full 0–10 range *within*
every era — the 2019 take scored `breath_support` 10.0, the 2024 Kryptonite
scored 1.25 — so **no era-to-era trend in those columns can be claimed from
this data**, in either direction. An early draft of this analysis asserted such
a trend by comparing one old take against a hand-picked recent best; that
comparison was unsound and is retracted here.

What *is* stable across all three eras: **median pitch deviation of 20–25
cents**, matching the 3 Doors Down and John Farnham reference masters. Aaron's
pitch-centring measured at reference level in 2019 and still does. It is not
where his development has happened, and it is not where his remaining gap to
the references lies — on the same song, the professional's advantage was breath
(10.0 vs 1.9) and held-note drift (28c vs 42c).

Note also that the engine measures seven acoustic properties of one take. It
does not measure repertoire, stagecraft, night-to-night consistency, recovery,
or song selection — and Aaron has no historical multi-venue night to compare
against his 1 Aug 2026 one. The most visible recent development may be entirely
outside what these numbers can see.

---

## Addendum — the blind calibration test (2 Aug 2026)

The investigation above was extended with a **blind calibration set**: Aaron
gave a by-ear score for eight takes he had not seen scores for, chosen by the
analyst to span the range. Estimates were recorded before any number was
revealed.

**Result: on current material the engine and the singer agree closely.**

| Set | n | correlation | mean abs error | bias |
|---|---|---|---|---|
| Recent takes (current pipeline) | 8 | **+0.82** | **0.53** | +0.23 |
| Historical Zoom-H8 uploads | 3 | +0.32 | 2.11 | +2.11 |

The engine independently scored two of the eight in the 6s (6.2, 6.5) and was
*harsher* than the singer on one. **There is no floor compression and no
systematic inflation on current takes.**

### Four hypotheses tested and rejected
Each was proposed to explain the historical gap, and each was killed by data:

1. **Aggregation blend** (0.75·mean + 0.25·worst) — fit two takes to within 0.3,
   then missed Lose Control by 1.6. Textbook overfitting on n=2.
2. **Floor compression** — refuted by the recent set scoring 6.2 and 6.5.
3. **Processed/AI-training source files** — refuted; the historical takes were
   recorded on a Zoom H8 field recorder, which explains their clean signal
   (HNR 22 dB) mundanely.
4. **More scooping in the old era** — refuted; scooping is *higher* now
   (49.1% median) than historically (38.0%).

### What remains
The ~2-point gap appears only on historical material, whose measurements are
technically sound. The most parsimonious remaining explanation is that the
singer's retrospective judgement of old material is harsher than the recordings
warrant — supported by contemporaneous external listeners who rated him well at
the time, and by the fact that he approached those files stating in advance that
he knew they were poor. **Not yet tested:** a blind A/B where a third party
queues old and recent takes unlabelled, removing the expectation effect. Until
that runs, the gap is unexplained, not explained.

> **SUPERSEDED — the blind A/B ran on 2 Aug 2026 and refuted this paragraph.**
> Blind, Aaron still rated the old material 1.5 points lower. It was not
> expectation; it was intra-note drift the engine stops measuring at 80 cents.
> See the final addendum, "the blind A/B RAN", and limitation 4. The paragraph
> is kept as written because retracted reasoning is part of the record.


### Round 2 — sighted calibration extended to 14 takes (2 Aug 2026)

A second round of six by-ear estimates on previously unrated recent takes
brings the calibration set to **n=14**:

| Set | n | correlation | mean abs error | bias |
|---|---|---|---|---|
| Round 1 | 8 | +0.82 | 0.53 | +0.23 |
| Round 2 | 6 | +0.82 | 0.37 | -0.23 |
| **Both rounds** | **14** | **+0.776** | **0.46** | **+0.03** |

A bias of +0.03 across fourteen takes means there is no systematic offset
between the singer's ear and the engine on current material.

**Round 2 was NOT blind** — the songs and dates were named to him. It is a
second sighted round, not the outstanding blind A/B, which still requires a
third party to shuffle and relabel. The expectation effect remains uncontrolled
in both rounds.

**A fifth rejected hypothesis:** substituting capture-fair for overall on
degraded-capture takes (HNR < 15) was tried as a fairer comparator and made
agreement *worse* (r 0.776 -> 0.688, error 0.46 -> 0.63). The singer judges the
recording as heard, capture flaws included; capture-fair deliberately discounts
exactly what he is listening to. **Overall is the correct comparator against a
by-ear estimate.**

**Component-level accuracy:** on two takes he volunteered breath specifically
("struggle with breath towards the end") without prompting. Both were confirmed
— Heat Is On breath 4.86 / 63.2% sag, Pressure Down breath 5.78 / 58.1% sag. He
identifies the failing component by ear, not merely the overall standard.


### Correction — the professional reference distribution (2 Aug 2026)

An earlier step in this investigation compared Aaron's takes against the **10**
reference analyses that happen to be copied into `archive/scratch-analyses`,
and concluded that his 2019 beginner take "out-scores 7 of 10 professional
masters" — presented as evidence of a validity failure.

**That was a small-sample artefact.** The calibration pack contains **50**
scored professional references (`engine/calibration/references/`, all on
calibration pack `0da01ef1e30f`). The full distribution:

| min | p10 | median | p90 | max |
|---|---|---|---|---|
| 8.1 | 8.3 | **9.05** | 9.6 | 9.8 |

The 10-file subset was skewed low (median 8.6 vs 9.05). Against all fifty,
Aaron's 2019 take (8.9) out-scores **20/50 (40%)** and sits just *below* the
professional median — notable, but not the validity failure previously claimed.
**The case for a v6 rubric change is correspondingly weaker.**

Two further notes:
- Do not compare a **capture-fair** score against professional **overalls**;
  capture-fair strips two components and is not the same measure. Aaron's KFF
  Prince of Wales is 8.85 overall, not the 9.4 room-fair figure.
- Useful framing that falls out of the full distribution: **no professional
  master in the set scores below 8.1**, so the professional band on this scale
  is 8.1–9.8. Aaron's best takes (8.8–9.3 overall) fall inside it; his active
  average of 7.96 falls just below it. His ceiling is professional; his
  consistency is not yet.

### Methodological notes for whoever repeats this
- Estimates must be taken **blind and before** any score is shown. One estimate
  in this set (You Sexy Thing, 10 Jun) was revised from 7.2 to 6.8 *after* the
  engine's 6.2 was visible. The revision improves agreement (r 0.82 → 0.88) and
  is therefore **not independent evidence** — the blind 7.2 is retained as the
  primary figure.
- Do not fit an aggregation change on fewer than ~10 points spanning the range,
  and hold half out for testing. Two of the four hypotheses above would have
  survived a fit and failed a test.

---

## Addendum — the blind A/B RAN (2 Aug 2026). It overturned the standing explanation.

Twelve clips, 28 seconds, vocals only, loudness-matched to −20.5 LUFS,
cryptographically shuffled by a third party who held the key until every score
was in. Six 2026 RoFormer stems, six 2024 voice-cloning dry vocals. Aaron scored
each 0–10 by ear, one pass. Record:
`docs/score-metrics/blind-listening-tests/2026-08-02-aaron-recent-vs-voice-cloning.json`
(subjective listener ratings — **not** VOXAI scores, and never to be mixed with
them).

**Result: the era gap is REAL. It is not an expectation effect.**

| | 2026 (n=6) | 2024 (n=6) | gap |
|---|---|---|---|
| Aaron, blind | 7.93 | 6.43 | **+1.50** |
| Engine (overall) | 8.18 | 7.47 | **+0.72** |

He could not see the labels and still separated the eras: **34 of 36
cross-era pairs went to the 2026 clip**, and five of six 2026 clips scored above
every 2024 clip. The engine sees the same difference in the same direction — but
**less than half of it**.

**The internal control went the same way.** *The Letter*, the one song in both
sets, indistinguishable by title:

| The Letter | ear | engine |
|---|---|---|
| 2024 | 6.8 | 8.00 |
| 2026 | 7.7 | 8.20 |
| separation | **+0.9** | **+0.20** |

Same song, same singer, blind — his ear separates the two takes 4.5× more than
the engine does.

### The previous explanation is retracted

The sighted rounds concluded that "the singer's retrospective judgement of old
material is harsher than the recordings warrant." **That is now refuted.** Blind,
with no idea which era he was hearing, he rated the old material a point and a
half lower. He was hearing something. The engine under-reads it.

### What he was hearing: drift

Correlating his twelve blind scores against every raw metric, exactly one tracks
his ear, and it is the one limitation 4 describes:

| metric | r with blind ear score | 2026 median | 2024 median |
|---|---|---|---|
| **median intra-note drift** | **−0.653** | **39.6c** | **77.8c** |
| vibrato rate | +0.527 | 5.19 Hz | 4.46 Hz |
| HNR | −0.349 | 18.2 dB | 20.6 dB |
| pct scooped onsets | −0.274 | 51.6% | 51.2% |
| median deviation from grid | −0.209 | 21.3c | 25.0c |
| % notes within 25c | +0.065 | 51.7% | 52.3% |

(−0.662 for drift after dropping the two clips flagged below; direction and size
hold.)

The old takes wander nearly **twice as far inside a note** — 77.8c against 39.6c.
Four of the six sit at or past the 80c floor where `pitch_stability` stops
counting, so the engine records "0.0, same as the others" while the ear keeps
hearing it get worse. The slower vibrato in the old set (4.46 Hz vs 5.19 Hz) is
the same phenomenon heard from the other side: a slow wide wobble *is* drift.

Note what is **not** on the list. Deviation from the grid barely moves (21c vs
25c) and the within-25-cents rate is flat. His pitch *centring* was already
reference-level in the old takes — consistent with everything the sighted rounds
found. What changed is his ability to **hold** a note once he lands on it.

### What this does and does not change

- **It does not make the engine wrong.** The direction is right, the mechanism is
  identified and measured, and on 2026 material the engine sat +0.25 from his
  blind ear across six clips. It compresses one specific failure mode at the
  extreme.
- **It does not license a rubric change.** The v6 attempt (see
  `V6_ONSET_COMPONENT_REJECTED.md`) is the standing precedent: a change must
  measurably improve agreement across the range, not just on the takes that
  motivated it, and it must be fit on more than a handful of points. Six old
  takes is not that. **Read drift beside the score instead.**
- **It does change how a cross-era claim may be made.** A gap of "+0.72 by
  engine" between eras must be reported alongside the fact that a blind listener
  put it at +1.50 and that four of the six old takes are jammed against the
  `pitch_stability` floor.

### Caveats on this run, stated plainly

- **Two clips could not be matched to a specific archived take.** Candi cut clip
  04 (Let's Stay Together) and clip 09 (Do Wah Diddy) from "the first distinct
  source / take-001"; **no take-001 exists in the archive for either song on
  2026-07-08.** Clip 04 was matched to take-003 (8.5, the only one) and clip 09
  to take-002 (7.7) — but Do Wah Diddy take-003 scores **8.7**, a full point
  apart, so that clip's engine number is uncertain across a 1.0 range. Clip 04
  is also the single largest ear/engine disagreement in the set (+1.8) and may
  be an artefact of the mismatch. Both are 2026 clips, so if anything they make
  the engine's era separation look *larger* than it is; the finding is not
  resting on them. Dropping both: ear gap **+1.79**, engine gap **+0.76** — the
  under-reading gets wider, not narrower.
- **Clip 09 fails the limitation-3 validity gate** — HNR 9.8 dB, jitter 2.75%,
  separator `unknown`, drift 5.2c. Its pitch numbers are not trustworthy.
- **Song identity still leaks era**, as the protocol warned. The Letter control
  is the defence against that, and it agreed with the overall result.
- n=6 per era. The within-2026 correlation on this set is r=+0.04, but the range
  is only 6.7–8.8 and one point dominates; it does not overturn the r=+0.776
  measured across the fourteen sighted takes, and it is not evidence of anything
  on its own.

### The honest summary for the singer

He was right that something is off, and right about which direction — but not
about the conclusion he feared. The engine is not flattering him *now*; on 2026
material it agreed with his blind ear to a quarter of a point. It is **too kind
to his 2024 self**, because the thing that was wrong back then — notes sliding
around inside themselves — is the one fault this rubric stops being able to
measure past a point. He has improved, by more than the scores say.
