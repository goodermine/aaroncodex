# Diagnosis — why two songs "break" Aaron's breath score, and what the measure is really counting

Date: 2026-07-27 · 100 Aaron takes · rubric v5

The five-month findings flagged *You Sexy Thing* (breath 3.85) and *Bye Bye Love*
(2.62) as anomalies against 7–10 across the rest of the repertoire. Diagnosing
them changed the picture twice, and the second change matters more than the first.

---

## 1. It is not tessitura, register or phrase length

All three obvious explanations fail:

| | You Sexy Thing (bad) | Play That Funky Music (good) |
|---|--:|--:|
| median pitch | 311 Hz | 320 Hz |
| estimated passaggio | 316 Hz | 316 Hz |
| register transitions | 66 | 67 |
| median phrase | 2.06 s | 2.87 s |
| **breath score** | **3.85** | **8.38** |

Same tessitura, same passaggio, same number of register crossings, and the
*good* song has the **longer** phrases. Across all 88 takes the correlation
between phrase length and breath score is only **r = −0.278**.

---

## 2. What the measure is actually counting

`sagging_phrase_ends` records the drop in cents. Aaron's, and everyone's, are
enormous:

| | median sag at a flagged ending |
|---|--:|
| Aaron — You Sexy Thing | 600 cents |
| Aaron — My Babe | 265 cents |
| Hot Chocolate — You Sexy Thing | 395 cents |
| Bon Jovi — Livin' On A Prayer | 480 cents |
| Carpenters — This Masquerade | 135 cents |
| Carrie Underwood — Before He Cheats | 595 cents |

**600 cents is six semitones.** Air running out sags a phrase ending by tens of
cents. Drops of 2–6 semitones in the final half-second are *stylistic fall-offs*,
and every professional reference in the pack does them.

So `pct_sagging_endings` is not counting breath failures. It is counting
**downward pitch releases at phrase ends**, most of which are deliberate. The
engine's own note already warns that "on short phrases, intentional fall-offs are
common in rock/soul — judge by ear". The measure cannot tell the two apart.

### The implementation gap behind this

`analyse_breath()`'s docstring says:

> Running out of air shows at phrase ends: pitch **sags and energy collapses** in
> the final half-second.

The implementation never measures energy. Its `y` (audio) parameter is unused —
it fits a pitch slope and nothing else. A supported stylistic fall holds its
energy; air running out does not. **The criterion that would separate them is
described in the docstring and absent from the code.**

---

## 3. The comparison that does work: Aaron against the original of the same song

Sag rate is heavily song-dependent — the references span **10.3% to 55.1%** of
endings. So an absolute sag rate scored against one pooled pro median partly
measures *which songs a singer chose*. Comparing each take with the original
recording of the same song removes that:

| song | takes | Aaron | original | delta |
|---|--:|--:|--:|--:|
| Kryptonite | 2 | 53.9% | 10.3% | **+43.5** |
| You Sexy Thing | 12 | 67.2% | 30.1% | **+37.1** |
| Danger Zone | 1 | 63.3% | 29.4% | **+33.9** |
| The Heat Is On | 5 | 50.6% | 22.2% | **+28.4** |
| The Letter | 5 | 51.7% | 34.6% | +17.1 |
| Play That Funky Music | 4 | 43.8% | 32.1% | +11.7 |
| Livin' On A Prayer | 3 | 59.2% | 55.1% | +4.1 |
| Let's Stay Together | 3 | 50.7% | 47.7% | +3.0 |

Two things fall out of this that the absolute score hid:

**Kryptonite is his worst song, not You Sexy Thing.** It scored a mid-table 6.55
on breath because 53.9% is less bad than 67.2% in absolute terms — but the
original falls on only 10.3% of its endings. Relative to the song as written,
that is the largest gap in the catalogue.

**Livin' On A Prayer and Let's Stay Together are not weaknesses at all.** Both
score poorly in absolute terms (59.2%, 50.7%) but sit within 4 points of the
original artist. Those songs simply have falling phrase ends.

> Confidence note: Kryptonite is 2 takes and Danger Zone is 1. The You Sexy Thing
> figure (12 takes) and The Heat Is On (5) are the solid ones.

---

## 4. What this means for coaching

- **Do not prescribe general breath support off the absolute score.** It is
  substantially a function of repertoire.
- The songs worth working are the ones where Aaron departs most from the
  original's own phrasing: **Kryptonite, You Sexy Thing, Danger Zone, The Heat Is
  On** — not the ones with the lowest raw score.
- Before drilling any of them, **listen at the flagged timestamps**. The measure
  cannot currently distinguish "he ran out of air" from "he chose to fall off the
  note, more often than the record does". Those need different responses: the
  first is support, the second is a phrasing decision.

---

## 5. Recommended engine changes — NOT done here

Both would change the rubric and retire every score, so they are decisions, not
housekeeping:

1. **Add the energy criterion the docstring already promises.** Flag an ending
   only when pitch falls *and* RMS collapses. This is what separates a supported
   fall from air running out, and it is the difference between measuring style
   and measuring breath.
2. **Report sag against the reference recording** where one exists, alongside the
   absolute figure. The delta table above is more diagnostic than the raw
   percentage and needs no rubric change to *report* — only to score.

A third, smaller one already noted in `HANDOFF_AARON_FIVE_MONTH_FINDINGS.md`: the
0.5 s tail window is a fixed duration rather than a proportion of the phrase.
