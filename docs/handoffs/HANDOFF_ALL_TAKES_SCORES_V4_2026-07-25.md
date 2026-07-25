# Handoff — updated scores for ALL takes (rubric v4, 2026-07-25)

**For Candi:** pull `main` and these are the current scores for every take. They
were recomputed with the **fixed** scoring engine (`deterministic_rubric_v4`), so they
supersede any older number in a saved report. Give Aaron the **v4 overall** for
his absolute result; give the **capture-fair** number for any room/live/phone
recording or when comparing against an original studio record (it drops the
components that measure the microphone rather than the voice).

## What changed in v4 (why scores moved slightly)

The `dynamics_expression` component was broken: it returned a **flat 10.0 for
every take** (a wide flat-topped curve over the whole professional range) and
cratered to **0** on a stem-separation artefact. It's now **graded** — 10 at the
professional median, easing to ~7 across the pro range, floored (never 0) beyond
it — and it's treated as **capture-sensitive**, so it now joins `voice_quality`
in the capture-fair calculation. Net effect: most overalls shifted by ~0.1–0.5
and the dynamics component finally discriminates (7.5–10.0 instead of a constant 10).

Any **new** analysis run through the engine now uses v4 automatically — nothing
to switch on. To refresh this table after new takes land:
`python3 docs/score-metrics/rescore_all.py`.

## Aggregate

- **Singer takes (22):** overall v4 6.6–9.7 (mean 8.24).
- **Pro references (9, calibration sanity check):** overall v4 8.1–9.6 (mean 8.73) — pros sit at the top, as they should.

## Every take — updated scores

| singer | song | v4 overall | capture-fair | confidence |
|---|---|--:|--:|:--|
| aaron | vienna-take-001 | **9.7** | 9.6 | high |
| aaron | danger-zone-new-studio-take-002 | **9.5** | 9.5 | high |
| aaron | if-you-could-read-my-mind-take-001 | **9.3** | 9.2 | high |
| aaron | the-letter-joe-cocker-take-001 | **9.3** | 8.9 | high |
| aaron | the-heat-is-on-take-002 | **8.8** | 8.4 | high |
| aaron | goodbye-s-been-good-to-you-take-001 | **8.8** | 8.3 | high |
| aaron | danger-zone-take-003 | **8.7** | 8.5 | high |
| aaron | the-heat-is-on-new-studio-take-001 | **8.6** | 7.9 | high |
| aaron | 1973-take-001 | **8.3** | 7.6 | high |
| rilda | dreams-take-001 | **8.3** | 8.5 | high |
| aaron | danger-zone-home | **8.2** | 7.6 | high |
| aaron | kryptonite-mango-hill-tavern-take-001 | **8.0** | 8.7 | high |
| rilda | you-sexy-thing-take-001 | **8.0** | 8.0 | high |
| aaron | lets-stay-together-new-studio-take-001 | **7.7** | 6.5 | high |
| aaron | the-heat-is-on-captain-cook-tavern-take-001 | **7.6** | 8.8 | high |
| aaron | you-can-leave-your-hat-on-bramble-bay-take-001 | **6.7** | 5.9 | high |
| aaron | come-out-and-play-captain-cook-tavern-take-001 | **6.6** | 7.1 | high |
| chris | feeling-good-take-001 | **7.7** | 8.4 | high |
| leo | chasin-that-neon-rainbow | **8.3** | 9.7 | high |
| rilda | this-masquerade-take-001 | **8.2** | 7.5 | high |
| rilda | lets-stay-together-home-take-001 | **7.8** | 7.0 | high |
| rilda | she-s-not-there-take-001 | **7.1** | 7.2 | high |

## Professional references (for context — these are the calibration pack)

| singer | song | v4 overall | capture-fair | confidence |
|---|---|--:|--:|:--|
| reference | carpenters-this-masquerade | **9.3** | 9.0 | high |
| reference | glenn-frey-the-heat-is-on | **8.1** | 8.7 | high |
| reference | james-blunt-1973 | **8.5** | 9.6 | high |
| reference | joe-cocker-the-letter | **8.3** | 9.1 | high |
| reference | joe-cocker-you-can-leave-your-hat-on | **8.3** | 8.9 | high |
| reference | kenny-loggins-danger-zone-official-audio-top-gun | **8.6** | 9.9 | high |
| reference | kryptonite-3-doors-down | **9.6** | 9.7 | high |
| reference | michael-buble-feeling-good | **9.4** | 9.2 | high |
| reference | tina-turner-lets-stay-together | **8.5** | 8.5 | high |

## Notes for giving Aaron his scores

- **Overall vs capture-fair:** studio takes — use overall. Tavern/live/phone
  takes — lead with capture-fair (it's typically ~1 point higher because it
  ignores mic/room-driven voice-quality and dynamic-range readings). Example:
  the Captain Cook Tavern "Heat Is On" reads 7.6 overall but **8.8 capture-fair**.
- **All takes are high confidence** on this set.
- **Component detail** (intonation / pitch stability / voice / vibrato / dynamics
  / phrase) for every take is in
  `docs/score-metrics/all-takes-rescore-v4-2026-07-25.md` (+ the `.json` for
  machine use).
- The earlier `HANDOFF_SCORE_METRICS_UPDATE_2026-07-25.md` (v3, last-10 only) is
  what revealed the dynamics bug; it's superseded by this v4 run for actual scores.
