# Genre references: measurement summary (updated 23 Oct 2026)

Step 3 of `docs/plans/GENRE_REFERENCE_CANDIDATES.md`. Frankie separated and measured the originals in #178, #179 and #183, all on the current engine (RoFormer stems, parselmouth voice quality, measurement era `28e854af22ea`). This page sets their raw measures against the current 50-pro pack and shows how today's rubric scores each genre's professionals.

**Nothing here changes a score.** The pack, the rubric and every archived score are untouched. Changing how a genre is scored is step 4, and needs Aaron's go-ahead.

**Seven references are held out of every median.** The engine flags them as *suspect*: a rough signal combined with better-than-90%-of-pros pitch behaviour, which is its signature for a pitch tracker following the band instead of the singer. They are:
- rock'n'roll: Don't Be Cruel, Runaway, Dream Lover, Let's Have a Party;
- hard rock: Smells Like Teen Spirit, Am I Ever Gonna See Your Face Again;
- oldies: Shout.

The plan says to drop any stem that is mostly band, so these need an ear check or a re-separation before they count. The 23 Oct update made this change. Holding them out reversed two of the 22 Oct findings, which are corrected below.

## What it shows

**Ear check, 23 Oct (Aaron):** clean, so counted again: Del Shannon, Wanda Jackson (occasional reverb), Nirvana (heavy reverb, no band), The Angels. Mixed, so still dropped: Elvis (backing singers under the lead), Bobby Darin (harmonies on line ends and some full lines), Isley Brothers Shout (background harmony). Rock'n'roll goes from 8 to 10 references: overall 8.8 to 9.1, capture-fair 9.1 to 9.6, held drift 57 to 51 c. Hard rock goes from 10 to 12: overall 7.6 to 7.7, capture-fair 7.2 to 7.8, held drift 77 to 65 c, held-note stability component 2.1 to 7.2, phrase control 4.5 to 3.1. So the earlier *Corrected* hard-rock held-note figure was too harsh: Nirvana and The Angels are real voices and they were what was pulling it up.

1. **Rock'n'roll fits the current yardstick (8 trusted references).**
   - Its professionals score a median 8.8 overall and 9.1 capture-fair, with held-note stability at 10.
   - Their raw measures sit inside the pack's normal band.
   - *Corrected:* the 22 Oct "cleaner entries" and "lower HNR on old masters" findings came from the contaminated stems. With them held out, entries (29%) and HNR (13.5 dB) match the pack.
   - With only 8 references, the held-drift median isn't settled (it swings 27 cents). Check or re-separate the 4 suspect stems before relying on it.

2. **Blues professionals are marked down on held-note stability** (12 references, all trusted).
   - Median component score 3.1. Held drift is 75 cents against the pack's 62.
   - Bends and blue notes read as "wandering".
   - The median is settled: it moves only 6 cents whichever 3 references are left out.

3. **Hard rock professionals are marked down on held notes, phrasing and voice quality** (10 trusted).
   - Held-note stability: median 2.1, with drift at 77 cents. *Corrected* from 7.2: two of the suspect stems were flattering this.
   - Phrase control: median 4.5. Their median line is 2.0 s against the pack's 3.8 s, so short, punchy lines read as choppy.
   - Voice quality: median 6.4. HNR is 11.2 dB against 13.6, because grit reads as a noisy voice.
   - Phrase endings sag more often: 41% against 33%.
   - The held-drift median isn't settled yet (it swings 26 cents). Add references before anchoring it.

4. **Rap scores lowest, as the plan expected** (all 12 in, all trusted).
   - Median 7.2 overall and 6.7 capture-fair, with held-note stability at 0 and phrase control at 4.6.
   - The rubric measures sung pitch, so rap still needs its own measures (flow and timing against the beat, diction) before it can be scored fairly.

5. **The six remaining oldies** are measured for key planning, not as a genre set. Five are trusted; Shout is suspect. They score like the pack (8.3 overall, 9.0 capture-fair), apart from lower voice quality (6.3) on the older masters.

## What this suggests for step 4 (Aaron's call)

- **Leave rock'n'roll on the shared pack.** First, ear-check or re-separate its four suspect stems to confirm it.
- **Blues:** a genre anchor for held-note stability only. The evidence is solid.
- **Hard rock:** genre anchors for held-note stability, phrase control and breath, after more references settle held drift. Whether voice quality should forgive grit is a judgement call: grit is the style, but it's also what the component measures.
- **Rap:** don't score it on this rubric. It needs new measures first.
- **Summer of '69:** the hard-rock set now uses the 1984 Reckless voice (official-video audio, `bryan-adams-summer-of-69-video-edit`). The engine flags its stem as suspect, so it stays out of the medians until Aaron ear-checks it. The 2022 Classic re-recording is archived but not in any genre set.

**Housekeeping:** the references were archived with a `technical_score`. The plan said to strip it, but it's what makes the component table below possible. Decide whether they keep it.

## Data

Regenerate this section with `python3 tools/genre_reference_summary.py`.

Raw measures from the RoFormer-separated originals, read the way `build_calibration.py` reads them, set against the current 50-pro pack. References the engine flags as **suspect** (its contamination signature: a degraded signal with better-than-90%-of-pros pitch behaviour, i.e. the tracker followed the band) are left out of every median until their stems are checked by ear or re-separated. They are still listed in the per-reference table.

- **50s-60s rock'n'roll:** 12 of 12 measured; 10 used (suspect, held out: elvis-presley-dont-be-cruel, bobby-darin-dream-lover)
- **Blues:** 12 of 12 measured; 12 used
- **Hard rock / grit:** 13 of 13 measured; 12 used (suspect, held out: bryan-adams-summer-of-69-video-edit)
- **Rap / hip-hop:** 12 of 12 measured; 12 used
- **Oldies to learn (not a genre set):** 6 of 6 measured; 5 used (suspect, held out: the-isley-brothers-shout)

## Raw measures: genre median vs the 50-pro pack

Pack column is p10 / **p50** / p90. Genre column is the median of that genre's references, with n in brackets.

| Measure | 50-pro pack | 50s-60s rock'n'roll | Blues | Hard rock / grit | Rap / hip-hop | Oldies to learn (not a genre set) |
|---|---|---|---|---|---|---|
| Pitch centre: median deviation (c) | 10.0 / **20.0** / 20.0 | 20.0 (10) | 20.0 (12) | 20.1 (12) | 25.0 (12) | 20.0 (5) |
| Held-note drift (c) | 44.5 / **62.5** / 90.1 | 51.1 (10) | 74.6 (12) | 64.5 (12) | 85.1 (12) | 64.3 (5) |
| Long notes with vibrato (%) | 40.4 / **53.2** / 64.0 | 57.2 (10) | 51.4 (11) | 37.9 (12) | 30.1 (12) | 43.1 (5) |
| Vibrato extent (c) | 52.5 / **64.1** / 78.0 | 66.8 (10) | 69.6 (11) | 68.3 (12) | 75.5 (12) | 55.6 (5) |
| Median phrase length (s) | 1.64 / **3.80** / 6.81 | 3.43 (10) | 3.39 (12) | 1.52 (12) | 2.02 (12) | 3.67 (5) |
| Phrase endings that sag (%) | 23.2 / **33.3** / 45.6 | 27.5 (10) | 30.7 (12) | 40.6 (12) | 49.3 (12) | 25.9 (5) |
| Clean note entries (%) | 21.0 / **33.2** / 44.8 | 35.2 (10) | 27.9 (11) | 30.6 (12) | 20.7 (12) | 31.4 (5) |
| HNR (capture-sensitive) (dB) | 9.5 / **13.6** / 18.2 | 12.5 (10) | 14.5 (12) | 10.9 (12) | 11.5 (12) | 12.3 (5) |
| CPPS (capture-sensitive) (dB) | 13.7 / **15.4** / 16.9 | 16.0 (10) | 15.8 (12) | 15.9 (12) | 13.8 (12) | 14.6 (5) |
| Effective dynamic range (capture-sensitive) (dB) | 18.4 / **27.0** / 36.3 | 28.2 (10) | 34.5 (12) | 25.4 (12) | 24.8 (12) | 27.5 (5) |

## How the current rubric scores each genre's professionals

Median component score (0–10) across each genre's references, scored against the current 50-pro pack. A pro of the style scoring low on a component is the signal that the yardstick, not the singer, is off.

| Component | 50s-60s rock'n'roll | Blues | Hard rock / grit | Rap / hip-hop | Oldies to learn (not a genre set) |
|---|---|---|---|---|---|
| intonation_accuracy | 10.0 | 10.0 | 10.0 | 8.0 | 10.0 |
| pitch_stability | 10.0 | 3.1 | 7.2 | 0.0 | 9.0 |
| vibrato_control | 9.5 | 9.8 | 9.7 | 9.1 | 9.9 |
| phrase_control | 8.9 | 8.8 | 3.1 | 4.6 | 9.6 |
| breath_support | 10.0 | 10.0 | 8.7 | 7.2 | 10.0 |
| voice_quality | 8.7 | 9.9 | 6.4 | 8.4 | 6.3 |
| dynamics_expression | 8.5 | 7.9 | 9.1 | 9.2 | 9.4 |
| **Overall** | 9.1 (range 6.9–9.6) | 8.3 (range 6.0–9.8) | 7.7 (range 6.2–9.6) | 7.2 (range 5.8–8.3) | 8.3 (range 8.0–9.2) |
| **Capture-fair** | 9.6 (range 6.0–10.0) | 8.3 (range 5.0–9.9) | 7.8 (range 5.1–9.6) | 6.7 (range 4.2–8.6) | 9.0 (range 7.8–10.0) |

## Are the medians settled?

Widest spread of the genre median across every subset that leaves 3 of its references out. Small means the median is already stable; large means the genre needs more references before it can anchor a score.

| Measure | 50s-60s rock'n'roll (n=10) | Blues (n=12) | Hard rock / grit (n=12) | Rap / hip-hop (n=12) |
|---|---|---|---|---|
| Pitch centre: median deviation (c) | 0.0 | 0.0 | 5.0 | 2.5 |
| Held-note drift (c) | 13.0 | 6.1 | 30.3 | 28.7 |
| Long notes with vibrato (%) | 14.8 | 16.5 | 8.8 | 9.4 |
| Vibrato extent (c) | 19.0 | 14.0 | 8.7 | 6.1 |
| Median phrase length (s) | 0.9 | 1.4 | 1.0 | 0.7 |
| Phrase endings that sag (%) | 9.8 | 10.6 | 10.3 | 2.4 |
| Clean note entries (%) | 21.2 | 1.1 | 6.0 | 4.4 |
| HNR (capture-sensitive) (dB) | 2.1 | 1.5 | 0.9 | 1.0 |
| CPPS (capture-sensitive) (dB) | 2.1 | 1.7 | 1.5 | 0.4 |
| Effective dynamic range (capture-sensitive) (dB) | 6.6 | 1.3 | 4.0 | 3.0 |

## Per-reference detail

| Genre | Reference | Overall / capture-fair | Pitch dev (c) | Held drift (c) | Sag (%) | Phrase (s) | HNR (dB) | Entry reliability |
|---|---|---|---|---|---|---|---|---|
| 50s-60s rock'n'roll | elvis-presley-dont-be-cruel | 8.8 / 9.1 | 20.0 | 53.0 | 22.9 | 1.59 | 10.1 | suspect |
| 50s-60s rock'n'roll | little-richard-tutti-frutti | 9.2 / 9.7 | 22.5 | 49.7 | 21.1 | 4.81 | 13.0 | high |
| 50s-60s rock'n'roll | chuck-berry-johnny-b-goode | 9.0 / 8.7 | 20.0 | 61.9 | 30.0 | 1.07 | 14.4 | high |
| 50s-60s rock'n'roll | jerry-lee-lewis-great-balls-of-fire | 6.9 / 6.0 | 27.5 | 92.0 | 46.7 | 2.15 | 14.3 | high |
| 50s-60s rock'n'roll | dion-runaround-sue | 8.5 / 9.5 | 20.0 | 48.9 | 14.8 | 2.51 | 10.8 | reduced |
| 50s-60s rock'n'roll | del-shannon-runaway | 9.6 / 9.8 | 10.0 | 38.3 | 12.5 | 11.17 | 12.0 | suspect |
| 50s-60s rock'n'roll | bobby-darin-dream-lover | 8.3 / 9.4 | 20.0 | 42.4 | 31.2 | 2.68 | 7.5 | suspect |
| 50s-60s rock'n'roll | roy-orbison-oh-pretty-woman | 7.5 / 7.7 | 20.0 | 76.3 | 43.3 | 3.10 | 11.9 | reduced |
| 50s-60s rock'n'roll | ben-e-king-stand-by-me | 9.3 / 10.0 | 20.0 | 52.5 | 25.0 | 3.76 | 10.7 | reduced |
| 50s-60s rock'n'roll | lulu-to-sir-with-love | 8.3 / 7.8 | 20.0 | 92.4 | 33.3 | 7.80 | 19.4 | high |
| 50s-60s rock'n'roll | wanda-jackson-lets-have-a-party | 9.5 / 9.9 | 20.0 | 27.8 | 33.3 | 3.83 | 10.8 | suspect |
| 50s-60s rock'n'roll | brenda-lee-sweet-nothins | 9.4 / 9.6 | 20.0 | 46.0 | 23.5 | 2.89 | 14.0 | high |
| Blues | little-walter-my-babe | 9.2 / 9.0 | 20.0 | 69.3 | 41.4 | 4.47 | 15.9 | high |
| Blues | b-b-king-the-thrill-is-gone | 9.1 / 9.5 | 20.0 | 56.1 | 23.5 | 2.58 | 15.0 | high |
| Blues | muddy-waters-mannish-boy | 7.6 / 6.7 | 20.0 | 98.7 | 45.3 | 1.64 | 11.3 | reduced |
| Blues | howlin-wolf-smokestack-lightnin | 8.4 / 9.3 | 20.0 | 48.1 | 28.6 | 2.41 | 11.8 | reduced |
| Blues | john-lee-hooker-boom-boom | 6.0 / 5.0 | 30.0 | 75.4 | 29.4 | 0.82 | 11.4 | — |
| Blues | bobby-blue-bland-ill-take-care-of-you | 8.1 / 8.7 | 20.0 | 69.8 | 53.3 | 5.67 | 11.4 | reduced |
| Blues | etta-james-id-rather-go-blind | 8.1 / 7.5 | 20.0 | 83.2 | 41.7 | 3.16 | 13.5 | high |
| Blues | koko-taylor-wang-dang-doodle | 7.7 / 7.0 | 20.0 | 75.9 | 40.0 | 1.27 | 14.7 | high |
| Blues | bonnie-raitt-love-me-like-a-man | 8.8 / 8.7 | 20.0 | 73.7 | 30.0 | 4.61 | 19.4 | high |
| Blues | tracy-chapman-give-me-one-reason | 8.3 / 8.0 | 20.0 | 77.8 | 31.4 | 3.97 | 17.6 | high |
| Blues | stevie-ray-vaughan-pride-and-joy | 9.8 / 9.9 | 20.0 | 49.5 | 14.3 | 3.62 | 14.3 | high |
| Blues | gary-moore-still-got-the-blues | 8.3 / 8.0 | 20.0 | 89.5 | 15.4 | 3.93 | 17.1 | high |
| Hard rock / grit | jimmy-barnes-working-class-man | 8.3 / 8.8 | 20.0 | 49.9 | 41.7 | 1.42 | 10.6 | reduced |
| Hard rock / grit | billy-idol-rebel-yell | 7.7 / 7.9 | 30.0 | 56.5 | 41.2 | 2.46 | 10.3 | reduced |
| Hard rock / grit | guns-n-roses-you-could-be-mine | 6.8 / 6.6 | 20.1 | 82.2 | 45.0 | 1.50 | 11.0 | reduced |
| Hard rock / grit | nirvana-smells-like-teen-spirit | 8.3 / 8.9 | 10.0 | 43.8 | 25.5 | 1.46 | 10.8 | suspect |
| Hard rock / grit | steppenwolf-born-to-be-wild | 7.5 / 6.6 | 30.0 | 107.0 | 9.5 | 4.82 | 14.5 | high |
| Hard rock / grit | ac-dc-highway-to-hell | 6.6 / 5.1 | 30.0 | 97.8 | 52.2 | 1.18 | 13.6 | high |
| Hard rock / grit | led-zeppelin-whole-lotta-love | 6.2 / 5.9 | 27.5 | 80.6 | 25.7 | 1.31 | 11.5 | reduced |
| Hard rock / grit | the-angels-am-i-ever-gonna-see-your-face-again | 7.7 / 8.2 | 20.0 | 40.5 | 58.8 | 0.81 | 7.9 | suspect |
| Hard rock / grit | heart-barracuda | 9.6 / 9.5 | 20.0 | 50.3 | 31.4 | 2.58 | 16.1 | high |
| Hard rock / grit | pat-benatar-hit-me-with-your-best-shot | 7.1 / 6.6 | 25.0 | 72.5 | 56.8 | 1.54 | 12.3 | reduced |
| Hard rock / grit | joan-jett-and-the-blackhearts-i-love-rock-n-roll | 8.8 / 9.6 | 15.0 | 47.4 | 26.7 | 3.95 | 8.4 | reduced |
| Hard rock / grit | the-black-keys-lonely-boy | 7.7 / 7.8 | 20.0 | 87.0 | 40.0 | 5.98 | 10.3 | reduced |
| Hard rock / grit | bryan-adams-summer-of-69-video-edit | 8.8 / 9.5 | 10.0 | 39.0 | 24.3 | 2.50 | 10.2 | suspect |
| Rap / hip-hop | eminem-lose-yourself | 6.4 / 6.4 | 25.0 | 129.7 | 47.6 | 2.87 | 9.1 | reduced |
| Rap / hip-hop | pitbull-ft-john-ryan-fireball | 7.3 / 6.7 | 20.0 | 87.7 | 48.6 | 1.39 | 12.1 | reduced |
| Rap / hip-hop | sir-mix-a-lot-baby-got-back | 5.8 / 4.2 | 30.0 | 107.4 | 54.9 | 0.86 | 11.1 | reduced |
| Rap / hip-hop | c-c-music-factory-things-that-make-you-go-hmmm | 7.3 / 6.5 | 25.0 | 78.7 | 45.5 | 2.18 | 14.4 | high |
| Rap / hip-hop | run-dmc-its-tricky | 7.6 / 6.9 | 22.5 | 82.5 | 38.2 | 3.14 | 9.7 | reduced |
| Rap / hip-hop | young-mc-bust-a-move | 8.3 / 7.9 | 30.0 | 65.7 | 37.1 | 4.08 | 13.4 | high |
| Rap / hip-hop | tone-loc-funky-cold-medina | 6.3 / 5.1 | 30.0 | 152.2 | 62.5 | 1.65 | 13.1 | high |
| Rap / hip-hop | the-notorious-b-i-g-juicy | 8.0 / 8.3 | 25.0 | 67.1 | 50.0 | 6.37 | 12.8 | reduced |
| Rap / hip-hop | kendrick-lamar-humble | 6.8 / 5.8 | 25.1 | 186.8 | 51.4 | 1.53 | 11.2 | reduced |
| Rap / hip-hop | lauryn-hill-doo-wop-that-thing | 7.1 / 6.7 | 22.5 | 109.1 | 50.0 | 2.38 | 10.9 | reduced |
| Rap / hip-hop | missy-elliott-work-it | 8.1 / 8.6 | 20.0 | 45.5 | 43.9 | 1.85 | 10.1 | reduced |
| Rap / hip-hop | salt-n-pepa-push-it | 7.2 / 6.9 | 20.0 | 70.9 | 60.0 | 1.03 | 11.9 | reduced |
| Oldies to learn (not a genre set) | four-tops-i-cant-help-myself-sugar-pie-honey-bunch | 8.3 / 7.8 | 20.0 | 74.8 | 47.6 | 3.67 | 12.3 | reduced |
| Oldies to learn (not a genre set) | the-foundations-build-me-up-buttercup | 8.3 / 8.0 | 20.0 | 83.9 | 12.5 | 4.35 | 13.4 | high |
| Oldies to learn (not a genre set) | the-isley-brothers-shout | 7.7 / 8.8 | 20.0 | 31.7 | 38.8 | 1.25 | 9.2 | suspect |
| Oldies to learn (not a genre set) | kc-and-the-sunshine-band-thats-the-way-i-like-it | 8.0 / 9.0 | 20.0 | 54.8 | 15.0 | 1.26 | 8.7 | reduced |
| Oldies to learn (not a genre set) | the-drifters-under-the-boardwalk | 9.2 / 10.0 | 20.0 | 39.7 | 33.3 | 5.30 | 13.2 | high |
| Oldies to learn (not a genre set) | the-easybeats-friday-on-my-mind | 8.6 / 9.6 | 20.0 | 64.3 | 25.9 | 3.58 | 8.6 | reduced |
