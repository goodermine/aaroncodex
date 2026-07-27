# Findings — Aaron's back catalogue, February to July 2026

Date: 2026-07-27 · 100 Aaron takes, 34 dates, rubric v5, preflight passing.

Candi's first pass added 88 analyses. This is the first time there has been
enough measured history to look at anything other than a single take. The
headline is not the one anyone expected.

---

## 1. There is no measurable overall trend, and the data cannot support one

| month | n | overall | capture-fair | breath |
|---|--:|--:|--:|--:|
| 2026-02 | 1 | 7.70 | 8.50 | 8.94 |
| 2026-04 | 2 | 7.30 | 8.70 | 10.00 |
| 2026-05 | 5 | 7.52 | 8.78 | 10.00 |
| 2026-06 | 12 | 7.12 | 7.18 | 4.83 |
| 2026-07 | 80 | 8.12 | 7.98 | 7.03 |

**Do not read improvement or decline into this.** July holds 69 of the 88 breath
scores; February through May hold 8 takes between them. A regression across all
88 dated takes gives a slope of **+0.31 over the entire span** — flat. The
month-to-month movement is repertoire and capture changing, not the singer.

The one thing the series *can* answer is far more useful.

---

## 2. Breath support is song-specific, not a general deficit

This is the finding. Same singer, same weeks, wildly different results:

| June date | song | breath |
|---|---|--:|
| 06-09 | You Sexy Thing | **1.36** |
| 06-10 | You Sexy Thing | **0.49** |
| 06-12 | **Sex Bomb** | **9.94** |
| 06-13 | **Come Out And Play** | **10.00** |
| 06-23 | You Sexy Thing | **0.31** |

Three days apart, Aaron scores 10.00 on one song and 0.31 on another.

### It is not explained by phrase length

The obvious hypothesis — longer phrases need more air — does not hold. Across 88
takes the correlation between median phrase length and breath score is only
**r = −0.278**, and holding phrase length roughly constant (2.0–3.5 s) inverts it:

| song | n | median phrase | breath |
|---|--:|--:|--:|
| Bye Bye Love | 3 | 2.59 s | **2.62** |
| You Sexy Thing | 12 | 2.06 s | **3.85** |
| Tutti Frutti | 2 | 3.36 s | 4.69 |
| Pressure Down | 8 | 3.29 s | 7.11 |
| My Babe | 11 | 3.32 s | **7.50** |
| Do Wah Diddy Diddy | 2 | 2.12 s | **8.27** |
| Play That Funky Music | 4 | 2.87 s | **8.38** |

*My Babe* and *Pressure Down* have **longer** phrases than *You Sexy Thing* and
score more than double on breath.

**So the question to ask is not "why is Aaron's breath support weak" — it is
"what do You Sexy Thing and Bye Bye Love demand that My Babe does not".**
Tessitura, tempo, and where the phrases sit relative to the passaggio are the
obvious candidates and are all already measured per take.

### Why this matters for coaching

A general "breath support" prescription is the wrong response to a song-specific
failure. Aaron holds phrase endings competently on most of his repertoire. Two
songs break him. That is a repertoire-and-placement problem to diagnose, not a
fundamentals problem to drill from scratch — and it directly contradicts reading
the sag as evidence of an unchecked fundamental.

---

## 3. Measurement caveat found while checking this

`analyse_breath()` fits its slope over a **fixed 0.5 s tail**, not a proportion of
the phrase. On material with phrases shorter than about 1 s that window spans
most of the phrase and possibly what precedes it, so it is not measuring the same
quantity it measures on a 5 s phrase.

Checked before trusting any of the above: the short-phrase takes are **not**
scoring well through lack of data — *Come Out And Play* measured 142 phrase
endings with 33.8% sagging, at the pro median of 34.85%. The 10.00 is earned.

Still, **compare `pct_sagging_endings` only between takes of similar
`median_phrase_s`.** The engine's own note now says so. Making the window
proportional is a rubric change and would retire every score, so it is not done
here — but it should be considered before breath support is weighted any higher.

---

## 4. State of the archive

- 110 takes: **Aaron 100**, Aaron G 3, Rilda 5, Chris 1, Leo 1, plus 9 references.
- Coverage: 88 full / 22 partial (the partial ones predate `analyse_breath`).
- Aaron overall mean **7.95**, capture-fair mean **7.94**, range 6.1–9.5.
- Preflight passes; every take's classification agrees with its recorded
  `artist_name`.

### Still outstanding

- **4 takes failed stem separation**: Only You, Let's Stay Together, The Heat Is
  On, You Sexy Thing. Worth retrying — the You Sexy Thing one especially, since
  that song is now the most interesting thing in the dataset.
- **Rilda, Leo, Chris** have not had the same pass. Rilda has 20 files on the
  host and 5 analysed.
- **22 takes still partial** — re-analysing them closes the last of the coverage
  gap.
