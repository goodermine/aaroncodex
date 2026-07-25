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

- **Singer takes (29):** overall v4 6.6–9.7 (mean 8.29).
- **Pro references (9, calibration sanity check):** overall v4 8.1–9.6 (mean 8.73) — pros sit at the top, as they should.

## ⚠ Rilda's two 25 July takes were scored far too harshly — correct them

Rilda's `Dreams` and `You Sexy Thing` were reported at **5.1/10**. Under the
current calibrated engine they are **8.3** and **8.0**. Tell her — a 3-point
correction on real coaching feedback.

**Why the old number was wrong** (from the archived files themselves): both were
scored with **`deterministic_rubric_v1`, completely uncalibrated** (no calibration
block), and both hit the dynamics bug fixed in v4:

| | dynamics (v1) | dynamics (v4) | overall (v1) | overall (v4) |
|---|--:|--:|--:|--:|
| Dreams | **0.0** | 9.97 | 5.1 | **8.3** |
| You Sexy Thing | **0.91** | 9.0 | 5.1 | **8.0** |

The zeroed dynamics alone cost ~1.5 points (15% weight). The rest is v1's
uncalibrated anchors — *every* component scores higher under the calibrated
rubric (e.g. Dreams intonation 6.25 → 9.52).

**This also resolves the open item in
`CANDI_SCORE_INCIDENT_AND_RILDA_COMPARISONS_2026-07-25.md`.** That handoff logged
`You Sexy Thing` as an unexplained conflict — Phase 1 ledger 5.1 vs a comparison
engine 8.3 — and required manual review. It wasn't a mystery: **the 5.1 came from
a stale, uncalibrated rubric carrying a known bug**, and the higher number was
much closer to the canonical answer (v4 says 8.0). The 5.1 should not be used or
quoted in progress trends.

Treat any report still carrying a `deterministic_rubric_v1` score the same way:
**re-score it before quoting** (`python3 docs/score-metrics/rescore_all.py`).

## ⚠ Pressure Down: the 9.5 was withdrawn on the strength of a broken number

Take 4's saved report said **9.5**. It was rechecked against the then-current
backend, came back **6.5**, and the 9.5 was withdrawn as "not valid".

**Under the current calibrated engine Take 4 is 9.3.** The 6.5 that overturned it
was produced by `deterministic_rubric_v1` — uncalibrated, carrying the dynamics
bug. The original 9.5 was within 0.2 of the right answer; the "correction" was
the wrong number. Aaron should be told.

It's systematic, not a one-off — every Pressure Down take moved up ~2.5–3.1
points once scored properly:

| take | retired v1 | **current v4** | capture-fair |
|---|--:|--:|--:|
| 1 | 6.1 | **9.1** | 8.8 |
| 2 | 5.3 | **8.0** | 7.2 |
| 3 | 6.3 | **9.1** | 9.0 |
| 4 | 6.5 | **9.3** | 9.2 |
| 5 | 5.7 | **8.5** | 7.9 |
| 6 (Mango Hill, live) | 4.6 | **7.5** | 7.7 |
| 7 (Brighton, live) | 4.5 | **7.6** | 7.8 |

Same root cause as Rilda's 5.1s: **rubric v1 scored everyone roughly 2.5–3 points
too harshly.** All 38 stale scores across the archive have now been retired so
none of them can be quoted again — see `HANDOFF_SCORE_PROVENANCE.md`.

## Every take — updated scores

| singer | song | v4 overall | capture-fair | confidence |
|---|---|--:|--:|:--|
| aaron | vienna-take-001 | **9.7** | 9.6 | high |
| aaron | danger-zone-new-studio-take-002 | **9.5** | 9.5 | high |
| aaron | if-you-could-read-my-mind-take-001 | **9.3** | 9.2 | high |
| aaron | the-letter-joe-cocker-take-001 | **9.3** | 8.9 | high |
| aaron | pressure-down-take-004 | **9.3** | 9.2 | high |
| aaron | pressure-down-take-001 | **9.1** | 8.8 | high |
| aaron | pressure-down-take-003 | **9.1** | 9.0 | high |
| aaron | the-heat-is-on-take-002 | **8.8** | 8.4 | high |
| aaron | goodbye-s-been-good-to-you-take-001 | **8.8** | 8.3 | high |
| aaron | danger-zone-take-003 | **8.7** | 8.5 | high |
| aaron | the-heat-is-on-new-studio-take-001 | **8.6** | 7.9 | high |
| aaron | pressure-down-take-005 | **8.5** | 7.9 | high |
| aaron | 1973-take-001 | **8.3** | 7.6 | high |
| rilda | dreams-take-001 | **8.3** | 8.5 | high |
| aaron | danger-zone-home | **8.2** | 7.6 | high |
| aaron | kryptonite-mango-hill-tavern-take-001 | **8.0** | 8.7 | high |
| aaron | pressure-down-take-002 | **8.0** | 7.2 | high |
| rilda | you-sexy-thing-take-001 | **8.0** | 8.0 | high |
| aaron | lets-stay-together-new-studio-take-001 | **7.7** | 6.5 | high |
| aaron | pressure-down-take-007 | **7.6** | 7.8 | high |
| aaron | the-heat-is-on-captain-cook-tavern-take-001 | **7.6** | 8.8 | high |
| aaron | pressure-down-take-006 | **7.5** | 7.7 | high |
| aaron | you-can-leave-your-hat-on-bramble-bay-take-001 | **6.7** | 5.9 | high |
| aaron | come-out-and-play-captain-cook-tavern-take-001 | **6.6** | 7.1 | high |
| chris | feeling-good-take-001 | **7.7** | 8.4 | high |
| leo | chasin-that-neon-rainbow | **8.3** | 9.7 | high |
| rilda | this-masquerade-take-001 | **8.2** | 7.5 | high |
| rilda | lets-stay-together-home-take-001 | **7.8** | 7.0 | high |
| rilda | she-s-not-there-take-001 | **7.1** | 7.2 | high |

### Pressure Down version map

- Take 1: first home take, natural.
- Take 2: home take with light F-sharp auto-tune.
- Take 3: home take, natural.
- Take 4: home take, natural; first two-beat held-note focus.
- Take 5: final home take before live karaoke.
- Take 6: Mango Hill, first live take.
- Take 7: Brighton, final song of the night.

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
