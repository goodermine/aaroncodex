# Genre references: first measurement summary (22 Oct 2026)

Step 3 of `docs/plans/GENRE_REFERENCE_CANDIDATES.md`. Frankie separated and measured the originals in #178 and #179, all on the current engine (RoFormer stems, parselmouth voice quality, measurement era `28e854af22ea`). This page sets their raw measures against the current 50-pro pack and shows how today's rubric scores each genre's professionals.

**Nothing here changes a score.** The pack, the rubric and every archived score are untouched. Changing how a genre is scored is step 4, and needs Aaron's go-ahead.

## What it shows

1. **Rock'n'roll already fits the current yardstick.**
   - Its professionals score a median 8.9 overall and 9.4 capture-fair.
   - Their raw measures sit inside the pack's normal band, with steadier held notes than the pack (51 against 62 cents) and cleaner entries (42% against 33%).
   - A separate rock'n'roll yardstick looks unnecessary.

2. **Blues professionals are marked down on held-note stability.**
   - Median component score 3.1. Held drift is 75 cents against the pack's 62.
   - Bends and blue notes read as "wandering".
   - The median is stable across subsets: 12 references settle it to within about 7 cents.

3. **Hard rock professionals are marked down on phrasing and voice quality.**
   - Phrase control has a median of 3.1. Their median line is 1.5 s against the pack's 3.8 s: short, punchy lines read as choppy.
   - Voice quality has a median of 6.4. HNR is 10.9 dB against 13.6, because grit and distortion read as a noisy voice.
   - Phrase endings sag more often: 41% against 33%.
   - The held-drift median is **not** settled yet: it swings 31 cents across subsets. Add references before anchoring it.

4. **Rap scores lowest, as the plan expected.**
   - Median 7.3 overall and 6.5 capture-fair, with held-note stability at 0.
   - The rubric measures sung pitch, so rap still needs its own measures (flow and timing against the beat, diction) before it can be scored fairly.
   - Only 5 of the 12 rap originals have arrived.

5. **The old-recording worry is only half borne out.**
   - The 1950s–60s masters read lower on HNR (11.9 against 13.6 dB), but their CPPS and dynamic range sit at the pack median.
   - The plan's suggested split still looks right: genre anchors for the voice components only, with the capture-sensitive components kept on the shared norms.

## What this suggests for step 4 (Aaron's call)

- **Leave rock'n'roll on the shared pack.**
- **Blues:** a genre anchor for held-note stability only.
- **Hard rock:** genre anchors for phrase control and breath, plus more references before held-drift is anchored. Whether voice quality should forgive grit is a judgement call: grit is the style, but it's also what the component measures.
- **Rap:** keep collecting, and don't score it on this rubric yet.
- **Still to fetch:**
  - 7 rap originals: Bust a Move, Funky Cold Medina, Juicy, HUMBLE., Doo Wop, Work It, Push It.
  - Summer of '69.
  - The 6 remaining oldies: Four Tops, The Foundations, Isley Brothers, KC and the Sunshine Band, The Drifters, The Easybeats.

**Housekeeping:** the references were archived with a `technical_score`. The plan said to strip it, but it's what makes the component table above possible. Decide whether they keep it.

## Data

Regenerate this section with `python3 tools/genre_reference_summary.py`.

Raw measures from the RoFormer-separated originals, read the way `build_calibration.py` reads them, set against the current 50-pro pack.

- **50s-60s rock'n'roll:** 12 of 12 measured
- **Blues:** 12 of 12 measured
- **Hard rock / grit:** 12 of 13 measured (missing: bryan-adams-summer-of-69)
- **Rap / hip-hop:** 5 of 12 measured (missing: young-mc-bust-a-move, tone-loc-funky-cold-medina, the-notorious-b-i-g-juicy, kendrick-lamar-humble, lauryn-hill-doo-wop-that-thing, missy-elliott-work-it, salt-n-pepa-push-it)

## Raw measures: genre median vs the 50-pro pack

Pack column is p10 / **p50** / p90. Genre column is the median of that genre's references, with n in brackets.

| Measure | 50-pro pack | 50s-60s rock'n'roll | Blues | Hard rock / grit | Rap / hip-hop |
|---|---|---|---|---|---|
| Pitch centre: median deviation (c) | 10.0 / **20.0** / 20.0 | 20.0 (12) | 20.0 (12) | 20.1 (12) | 25.0 (5) |
| Held-note drift (c) | 44.5 / **62.5** / 90.1 | 51.1 (12) | 74.6 (12) | 64.5 (12) | 87.7 (5) |
| Long notes with vibrato (%) | 40.4 / **53.2** / 64.0 | 56.8 (12) | 51.4 (11) | 37.9 (12) | 27.0 (5) |
| Vibrato extent (c) | 52.5 / **64.1** / 78.0 | 61.8 (12) | 69.6 (11) | 68.3 (12) | 71.3 (5) |
| Median phrase length (s) | 1.64 / **3.80** / 6.81 | 3.00 (12) | 3.39 (12) | 1.52 (12) | 2.18 (5) |
| Phrase endings that sag (%) | 23.2 / **33.3** / 45.6 | 27.5 (12) | 30.7 (12) | 40.6 (12) | 47.6 (5) |
| Clean note entries (%) | 21.0 / **33.2** / 44.8 | 41.6 (12) | 27.9 (11) | 30.6 (12) | 22.2 (5) |
| HNR (capture-sensitive) (dB) | 9.5 / **13.6** / 18.2 | 11.9 (12) | 14.5 (12) | 10.9 (12) | 11.1 (5) |
| CPPS (capture-sensitive) (dB) | 13.7 / **15.4** / 16.9 | 15.1 (12) | 15.8 (12) | 15.9 (12) | 14.2 (5) |
| Effective dynamic range (capture-sensitive) (dB) | 18.4 / **27.0** / 36.3 | 26.4 (12) | 34.5 (12) | 25.4 (12) | 23.5 (5) |

## How the current rubric scores each genre's professionals

Median component score (0–10) across each genre's references, scored against the current 50-pro pack. A pro of the style scoring low on a component is the signal that the yardstick, not the singer, is off.

| Component | 50s-60s rock'n'roll | Blues | Hard rock / grit | Rap / hip-hop |
|---|---|---|---|---|
| intonation_accuracy | 10.0 | 10.0 | 10.0 | 8.0 |
| pitch_stability | 10.0 | 3.1 | 7.2 | 0.0 |
| vibrato_control | 9.5 | 9.8 | 9.7 | 8.9 |
| phrase_control | 7.6 | 8.8 | 3.1 | 5.1 |
| breath_support | 10.0 | 10.0 | 8.7 | 7.5 |
| voice_quality | 8.3 | 9.9 | 6.4 | 8.7 |
| dynamics_expression | 8.5 | 7.9 | 9.1 | 8.6 |
| **Overall** | 8.9 (range 6.9–9.6) | 8.3 (range 6.0–9.8) | 7.7 (range 6.2–9.6) | 7.3 (range 5.8–7.6) |
| **Capture-fair** | 9.4 (range 6.0–10.0) | 8.3 (range 5.0–9.9) | 7.8 (range 5.1–9.6) | 6.5 (range 4.2–6.9) |

## Do 12 references settle the medians?

Widest spread of the genre median across every possible 8-reference subset of the 12. Small means the median is already stable; large means the genre needs more references before it can anchor a score.

| Measure | 50s-60s rock'n'roll | Blues | Hard rock / grit |
|---|---|---|---|
| Pitch centre: median deviation (c) | 0.0 | 0.0 | 6.2 |
| Held-note drift (c) | 10.0 | 7.3 | 31.3 |
| Long notes with vibrato (%) | 10.0 | 16.5 | 11.1 |
| Vibrato extent (c) | 17.1 | 14.0 | 11.5 |
| Median phrase length (s) | 1.2 | 1.5 | 1.1 |
| Phrase endings that sag (%) | 9.1 | 11.7 | 14.3 |
| Clean note entries (%) | 17.8 | 1.1 | 6.4 |
| HNR (capture-sensitive) (dB) | 2.7 | 2.8 | 1.4 |
| CPPS (capture-sensitive) (dB) | 2.2 | 1.8 | 1.6 |
| Effective dynamic range (capture-sensitive) (dB) | 7.8 | 2.0 | 6.1 |

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
| Rap / hip-hop | eminem-lose-yourself | 6.4 / 6.4 | 25.0 | 129.7 | 47.6 | 2.87 | 9.1 | reduced |
| Rap / hip-hop | pitbull-ft-john-ryan-fireball | 7.3 / 6.7 | 20.0 | 87.7 | 48.6 | 1.39 | 12.1 | reduced |
| Rap / hip-hop | sir-mix-a-lot-baby-got-back | 5.8 / 4.2 | 30.0 | 107.4 | 54.9 | 0.86 | 11.1 | reduced |
| Rap / hip-hop | c-c-music-factory-things-that-make-you-go-hmmm | 7.3 / 6.5 | 25.0 | 78.7 | 45.5 | 2.18 | 14.4 | high |
| Rap / hip-hop | run-dmc-its-tricky | 7.6 / 6.9 | 22.5 | 82.5 | 38.2 | 3.14 | 9.7 | reduced |
