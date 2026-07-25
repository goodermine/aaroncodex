# Handoff — Pressure Down (Captain Cook Tavern) DOES score: 8.3 / 9.5 capture-fair

Date: 2026-07-25

Aaron submitted `Pressure_Down_Cook.m4a` (live, Captain Cook Tavern, 4:06) and
Candi **withheld the score** citing live dynamics. That withholding is no longer
correct — the condition it protects against was fixed in rubric **v4**.

The take has been analysed end-to-end and archived:
`voxanalysis/archive/scratch-analyses/2026-07-25-aaron-pressure-down-captain-cook-tavern-take-001_analysis.json`

## The result

| | |
|---|--:|
| **Overall** | **8.3 / 10** |
| **Capture-fair** (quote this — live take) | **9.5 / 10** |
| Confidence | high |
| Identity | `deterministic_rubric_v4` · build `3478e29a0ee5` · stem `UVR_MDXNET_Main` · calibrated (50 refs) |

| component | score |
|---|--:|
| Pitch centre | 9.52 |
| **Held-note stability** | **10.0** |
| Voice quality | 4.64 ← the room, not the singer |
| Vibrato control | 8.72 |
| Dynamics | 7.92 |
| Phrase control | 9.94 |

**This is his best Pressure Down take.** Capture-fair 9.5 is the highest of all
eight, and held-note stability is a perfect **10.0** — the next best Pressure Down
take manages 8.05. Aaron said he thought it was one of his best; the measurements
agree. Tell him.

Comparable by provenance with every other Pressure Down take (`scores_comparable`
returns True — same rubric, calibration pack and stem model), so the ranking is
valid:

| take | overall | capture-fair | held-note stability |
|---|--:|--:|--:|
| **Captain Cook (this one, live)** | 8.3 | **9.5** | **10.0** |
| take-004 (home, previous best) | 9.3 | 9.2 | 7.95 |
| take-003 | 9.1 | 9.0 | 6.32 |
| take-001 | 9.1 | 8.8 | 7.11 |
| take-005 | 8.5 | 7.9 | 5.68 |
| take-007 (Brighton, live) | 7.6 | 7.8 | 8.05 |
| take-006 (Mango Hill, live) | 7.5 | 7.7 | 7.95 |
| take-002 | 8.0 | 7.2 | 5.99 |

## Why the withholding was wrong — and what to change

The guard withholds when the **dynamics component is capture-sensitive / zero**.
That rule was written against rubric **v1**, where a separated stem's dynamic
range could crater the component to **0.0** and drag or invalidate the score.

**v4 fixed exactly that:**

1. Dynamics is now **graded and floored** — 10 at the pro median, easing to ~7
   across the pro range, and *never* below ~3 beyond it. It cannot reach 0. Here
   it scored **7.92**, a perfectly usable value.
2. Dynamics is now **capture-sensitive by declaration** and is excluded from
   `capture_fair_score` alongside `voice_quality`. The capture-driven risk the
   guard existed to catch is now handled inside the rubric.

**Change the guard to:** withhold only on a genuine **provenance conflict**
(`is_legacy_score()` / `score_conflict()` from `analyse_song`), never on
capture-sensitive dynamics. See `HANDOFF_SCORE_PROVENANCE.md`. A zeroed dynamics
component can no longer occur under v4, so a rule keyed to it will only ever
produce false withholdings like this one.

## Reproducing it

```bash
# 1. separate (same model, so the score stays provenance-comparable)
audio-separator take.wav -m UVR_MDXNET_Main.onnx --output_format FLAC
# 2. analyse the vocal stem with the current engine
python3 analyse_song.py "take_(Vocals)_UVR_MDXNET_Main.flac" --name "Aaron"
# 3. full results text for Telegram (web-identical)
#    report_builder.render_full_results_text(build_v2_report(raw), result)
```

The full-results text for this take is what Aaron should receive — it carries the
scores, the provenance line, every metric group, the trouble spots and the
practice plan.

## Coaching content worth passing on (measured)

- **Held notes are now genuinely steady** — median intra-note drift 23.9 cents,
  his best on this song. Whatever he changed, it worked.
- **Phrasing is strong** — 51 phrases, median 3.13 s, longest 14.27 s.
- **Onsets are the real technical target:** only 33.3% clean; 34.0% scooped
  (median scoop depth −75.6 cents), 32.6% overshot. That's a landing-accuracy
  issue, not a support issue.
- **Breath endings:** 49% of phrase endings sag — worth a look.
- The 8 listed trouble spots (drift 169–253 c) cluster on D4 / C♯4 around his
  estimated passaggio (C♯4) — likely transition moments, verify by ear.
- Range: comfortable core G♯3–F♯4, extremes touched A♯2–G♯5, most-used D4.

## One caveat to be honest about

The engine's `PRIMARY FOCUS` for this take says **"Voice quality"**, because it
picks the lowest-scoring component — and voice quality (4.64) is low purely
because of the venue (shimmer 16.4%, HNR 10.1 dB on a live PA/room capture).
**Do not coach Aaron to fix his voice quality off this take.** The genuine
technical target here is onset accuracy.

Follow-up worth doing in the engine: when a component is `capture_sensitive`,
exclude it from primary-focus selection (and/or when `environment_risk` is
elevated). Note this take's `environment_risk` reads `normal` despite being an
obvious room capture, so the existing flag alone would not have caught it.
