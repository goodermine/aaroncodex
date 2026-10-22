# Genre reference candidates — first picks (22 Oct 2026)

**Status: CHOSEN LIST.** Nothing has been fetched, analysed or added to the
calibration pack. This is step 1 of the genre-aware scoring plan in
`docs/handoffs/SINGNEXA_STYLE_VS_FAULT_PROPOSAL.md`. That plan was parked on
22 Oct with genre-aware scoring as the next step.

The aim is to give each thin genre its own set of professional reference
vocals, so a take can later be scored against pros of its own style. The first
batch is **12 songs per gap genre**. ✓ marks songs that Aaron, Rilda or Gresh
already sing and that are already in the archive. Those originals do two jobs:
they become a genre reference, and they allow a take-vs-original comparison.

## How the songs were picked

- **The original studio recording only.** No live versions or remasters that
  change the vocal, and no covers.
- **One clear lead singer.** Duets and two-part harmony leads were skipped,
  because separation and pitch tracking can't follow two lead lines. That's
  why the Everly Brothers are left out, even though *Wake Up Little Susie* and
  *Bye Bye Love* are sung here.
- **No heavy auto-tune.**
- **A spread of voices:** male and female, and different decades within each
  genre.
- **Not already in the 50-track pack.**

## 1. 50s–60s rock'n'roll (pack has ~0)

| # | Artist — Song | Note |
|---|---|---|
| 1 | Elvis Presley — Don't Be Cruel | ✓ |
| 2 | Little Richard — Tutti Frutti | ✓ |
| 3 | Chuck Berry — Johnny B. Goode | ✓ · already on Howard's oldies list |
| 4 | Jerry Lee Lewis — Great Balls of Fire | ✓ · already on Howard's oldies list |
| 5 | Dion — Runaround Sue | ✓ · already on Howard's oldies list (*The Wanderer* already measured) |
| 6 | Del Shannon — Runaway | ✓? — confirm Aaron's 16 Oct *Runaway* is Del Shannon, not Bon Jovi |
| 7 | Bobby Darin — Dream Lover | ✓ |
| 8 | Roy Orbison — Oh, Pretty Woman | ✓ |
| 9 | Ben E. King — Stand By Me | ✓ |
| 10 | Paul Anka — Lonely Boy | ✓? — confirm Aaron's Apr *Lonely Boy* is Paul Anka, not The Black Keys |
| 11 | Wanda Jackson — Let's Have a Party | female rockabilly |
| 12 | Brenda Lee — Sweet Nothin's | female |

## 2. Blues (pack has ~0)

| # | Artist — Song | Note |
|---|---|---|
| 1 | Little Walter — My Babe | ✓ · already a Howard retry |
| 2 | B.B. King — The Thrill Is Gone | |
| 3 | Muddy Waters — Mannish Boy | |
| 4 | Howlin' Wolf — Smokestack Lightnin' | |
| 5 | John Lee Hooker — Boom Boom | |
| 6 | Bobby "Blue" Bland — I'll Take Care of You | |
| 7 | Etta James — I'd Rather Go Blind | female |
| 8 | Koko Taylor — Wang Dang Doodle | female |
| 9 | Bonnie Raitt — Love Me Like a Man | female |
| 10 | Tracy Chapman — Give Me One Reason | ✓ · female, blues-folk |
| 11 | Stevie Ray Vaughan — Pride and Joy | blues-rock |
| 12 | Gary Moore — Still Got the Blues | blues-rock |

## 3. Hard rock / grit (pack has ~11 rock, mostly melodic)

| # | Artist — Song | Note |
|---|---|---|
| 1 | Jimmy Barnes — Working Class Man | ✓ |
| 2 | Billy Idol — Rebel Yell | ✓ |
| 3 | Guns N' Roses — You Could Be Mine | ✓ · compared once already (12 Oct) |
| 4 | Nirvana — Smells Like Teen Spirit | ✓ |
| 5 | Steppenwolf — Born to Be Wild | the first Singnexa test song |
| 6 | AC/DC — Highway to Hell | |
| 7 | Led Zeppelin — Whole Lotta Love | |
| 8 | The Angels — Am I Ever Gonna See Your Face Again | Australian pub rock |
| 9 | Bryan Adams — Summer of '69 | already on Howard's oldies list |
| 10 | Heart — Barracuda | female |
| 11 | Pat Benatar — Hit Me With Your Best Shot | female |
| 12 | Joan Jett & the Blackhearts — I Love Rock 'n' Roll | female |

## 4. Rap / hip-hop (pack has 0)

**Collect, but don't use for scoring yet.** The rubric measures sung pitch, so
rap first needs new measures, such as flow/timing against the beat and diction
(see the proposal). Measuring these originals now gives that work real data.

| # | Artist — Song | Note |
|---|---|---|
| 1 | Eminem — Lose Yourself | ✓ |
| 2 | Pitbull ft. John Ryan — Fireball | ✓ · original already measured (16 Oct) |
| 3 | Sir Mix-a-Lot — Baby Got Back | ✓ |
| 4 | Young MC — Bust a Move | ✓ |
| 5 | Tone Lōc — Funky Cold Medina | ✓ |
| 6 | C+C Music Factory — Things That Make You Go Hmmm… | ✓ · rap verses, sung hook |
| 7 | Run-DMC — It's Tricky | |
| 8 | The Notorious B.I.G. — Juicy | |
| 9 | Kendrick Lamar — HUMBLE. | |
| 10 | Lauryn Hill — Doo Wop (That Thing) | female, rap and sung |
| 11 | Missy Elliott — Work It | female |
| 12 | Salt-N-Pepa — Push It | female |

## Things to check when these are measured

- **Old recordings.** 1950s–60s masters are often mono, with tape hiss and
  slapback echo, which happens to suit Elvis and Sun-era records.
  - That lowers the capture-sensitive readings (`voice_quality`, `dynamics`).
    A genre yardstick built from them would score a modern home recording too
    kindly on those components.
  - The likely fix: the genre yardstick covers only the voice components
    (pitch centre, held-note stability, vibrato, phrasing, breath), and
    capture-sensitive components stay on the shared norms. Decide this when
    the numbers are in.
- **Slapback echo and doubled vocals** may disturb drift and onset readings.
  Check each separated stem by ear before trusting it.
- **Separation check per track:** apply the same "(vocals)" label and stem
  verification as every other analysis. A track whose stem is mostly band is
  dropped.
- **How many per genre is enough** is still open. Twelve is a first batch.
  Before any genre gets its own yardstick, check whether the genre's medians
  settle (for example, compare 8 against 12 references) and add more if they
  don't.

## Next steps (when Aaron says go)

1. A Howard handoff to fetch these originals, using the same rules as the
   16 Oct batch: SHA-256 provenance, a "DELETE AFTER" folder, and analysis
   only. Skip any already supplied: Fireball, and the oldies-list songs if they
   have arrived.
2. RoFormer separation and reference analysis of each track, with
   `technical_score` stripped. These are references, not scored takes.
3. A per-genre summary of the raw measures against the current 50-pro pack.
   That's the evidence for deciding how the genre yardstick works.
4. Only then, with Aaron's approval: a deliberate calibration rebuild with a
   new fingerprint, `score_preflight.py --update` and an archive re-score.
