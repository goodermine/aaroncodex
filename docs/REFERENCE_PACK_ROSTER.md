# Professional Reference Pack — Canonical Roster (50 tracks)

This is the authoritative list of recordings the VOXAI calibration is built
from. "Professional" is defined by what these 50 measure — so membership is
governed by the admission policy in `docs/metrics-methodology.md` (studio
recordings only, prominent sustained-note-rich lead vocal, minimal audible
pitch correction, balanced across voice type / era / style).

The analysis JSONs live in `vox-analysis/engine/calibration/references/`.
`pro_reference.json` is rebuilt from them with `tools/build_calibration.py`.

## The 50

| # | Artist | Song |
|---|---|---|
| 1 | Bon Jovi | Livin' on a Prayer |
| 2 | Céline Dion | My Heart Will Go On |
| 3 | Hot Chocolate | You Sexy Thing |
| 4 | Whitney Houston | I Have Nothing |
| 5 | Dimash | My Heart Will Go On |
| 6 | Mariah Carey | Vision of Love |
| 7 | Whitney Houston | I Will Always Love You |
| 8 | Adele | Rolling in the Deep |
| 9 | Aerosmith | Dream On |
| 10 | Al Green | Let's Stay Together |
| 11 | Alan Jackson | Chasin' That Neon Rainbow |
| 12 | Alicia Keys | If I Ain't Got You |
| 13 | Amy Winehouse | Back to Black |
| 14 | Andy Gibb | I Just Want to Be Your Everything |
| 15 | Aretha Franklin | (You Make Me Feel Like) A Natural Woman |
| 16 | Beyoncé | Halo |
| 17 | Billy Joel | Vienna |
| 18 | Bruno Mars | When I Was Your Man |
| 19 | Carly Simon | You're So Vain |
| 20 | The Carpenters | This Masquerade |
| 21 | Carrie Underwood | Before He Cheats |
| 22 | Chris Stapleton | Tennessee Whiskey |
| 23 | Dolly Parton | Jolene |
| 24 | Donna Summer | On the Radio |
| 25 | George Michael | Careless Whisper |
| 26 | Glenn Frey | The Heat Is On |
| 27 | Gordon Lightfoot | If You Could Read My Mind |
| 28 | Hozier | Take Me to Church |
| 29 | Idina Menzel | Let It Go |
| 30 | James Blunt | 1973 |
| 31 | Joe Cocker | The Letter |
| 32 | Joe Cocker | You Can Leave Your Hat On |
| 33 | John Farnham | You're the Voice |
| 34 | Journey | Don't Stop Believin' |
| 35 | Kenny Loggins | Danger Zone |
| 36 | 3 Doors Down | Kryptonite |
| 37 | Marvin Gaye | Let's Get It On |
| 38 | Michael Bublé | Feeling Good |
| 39 | Norah Jones | Don't Know Why |
| 40 | The Offspring | Come Out and Play |
| 41 | Queen | Somebody to Love |
| 42 | Sam Smith | Stay With Me |
| 43 | Sia | Chandelier |
| 44 | Stevie Wonder | Isn't She Lovely |
| 45 | Teddy Swims | Goodbye's Been Good to You |
| 46 | Teddy Swims | Lose Control |
| 47 | The Zombies | She's Not There |
| 48 | Tina Turner | Let's Stay Together |
| 49 | Tina Turner | What's Love Got to Do with It |
| 50 | Wild Cherry | Play That Funky Music |

## Balance

- **Voice type:** ~19 female-lead, ~31 male-lead — a spread of belters,
  crooners, and straight-tone voices in each.
- **Era:** late-1960s (The Zombies) through the 2020s (Teddy Swims), with
  the 1970s–2010s well represented; the pre-hi-fi and live recordings that
  measure rough for capture reasons were deliberately excluded.
- **Style:** rock, pop, soul/R&B, country (Alan Jackson, Carrie Underwood,
  Dolly Parton, Chris Stapleton), musical theatre (Idina Menzel), falsetto-
  led (Andy Gibb, Sam Smith), and soft/near-straight-tone (Norah Jones) —
  so the "professional" anchor isn't biased toward one way of singing.

## Notes

- Two artists appear twice with *different* songs (Whitney, Tina Turner,
  Joe Cocker, Teddy Swims) — different performances, which is legitimate;
  duplicate files of the same take are not allowed.
- One production-risk entry: Sia — Chandelier is reverb-heavy; if its stem
  separates poorly (elevated capture-risk flag), swap for another modern
  female belt (e.g. Adele — Someone Like You).
- All 50 must be analysed on the **current engine** before the calibration
  is rebuilt for rubric v3 (see `docs/CANDI_HANDOFF_REFERENCE_REANALYSIS.md`).
