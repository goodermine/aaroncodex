# How to read a VOXAI score — three measured limitations

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

### Methodological notes for whoever repeats this
- Estimates must be taken **blind and before** any score is shown. One estimate
  in this set (You Sexy Thing, 10 Jun) was revised from 7.2 to 6.8 *after* the
  engine's 6.2 was visible. The revision improves agreement (r 0.82 → 0.88) and
  is therefore **not independent evidence** — the blind 7.2 is retained as the
  primary figure.
- Do not fit an aggregation change on fewer than ~10 points spanning the range,
  and hold half out for testing. Two of the four hypotheses above would have
  survived a fit and failed a test.
