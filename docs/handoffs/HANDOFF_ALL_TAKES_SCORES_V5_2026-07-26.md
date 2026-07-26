# Handoff — rubric v5: breath support enters the score. All takes re-scored.

Date: 2026-07-26 · **Supersedes `HANDOFF_ALL_TAKES_SCORES_V4_2026-07-25.md`, which
has been deleted.** Every v4 number is retired. Quote only the table below.

```bash
python3 tools/score_preflight.py     # must exit 0 before quoting any /10
```
Currently passing: `deterministic_rubric_v5`, build `7cbd02df8f62`, 50 pro references.

---

## What changed and why

**Phrase-ending sag has been measured since v1 and fed nothing.** The score read
five measurement modules; nine contributed nothing, `breath` among them.
`phrase_control` scores how *long* a phrase is — never whether the note held its
pitch to the end of it. Sag reached the score only indirectly, diluted into
median intra-note drift taken across every note in the song.

That is the fault Aaron's analysis calls his primary limiter, and his own written
blueprint independently names. It now has its own component.

**`breath_support`** — % of phrase endings that sag, anchored to the pro pack.

| | value |
|---|---|
| pro pack median (= 10 on the scale) | **34.85%** of endings sag |
| pro pack p10 / p90 | 23.2% / 47.8% |
| pro pack full range | 10.3% – 55.1% |
| theoretical zero anchor | 90% of endings |
| relative weight | 0.10 → **9.1%** of the score |
| capture-sensitive? | **No — and that is the point** |

Anchors came from the 50 reference analyses already stored in
`engine/calibration/references/`, so **no audio was re-analysed**: this was a
`build_calibration.py` extension. `onsets_pct_scooped` and
`onsets_median_scoop_depth_cents` were anchored in the same pass so a scooping
component can be added later without a second calibration run.

### It is deliberately inside capture-fair

`voice_quality` and `dynamics_expression` are excluded from capture-fair because
they measure the recording chain. **Air running out is the singer, not the room**,
so `breath_support` stays in. A phone or tavern take is now scored on the fault
that actually limits it.

This is the change Aaron will feel: his Captain Cook take's capture-fair moves
**9.5 → 9.2**, because that 9.5 was flattered by excluding the one thing holding
the take back.

### Verified against the pro pack before shipping

- pro pack median on `breath_support` = **10.00**, p10 = 7.66, min = 6.33 — the
  anchoring is right, and the component discriminates rather than sitting flat.
- Overall scores across the 50 references move by **at most ±0.26** (mean +0.02).
  Adding the component did not destabilise the scale.
- Worst-affected reference: Bon Jovi, *Livin' On A Prayer* (55.1% of endings sag,
  the pack's worst) → 8.53 to 8.33. Best-affected: Chris Stapleton, *Tennessee
  Whiskey* → 7.15 to 7.41.

> Worth knowing before this gets over-read: **professionals sag too.** The pack
> median is 34.85% of endings, and one reference sags on 55%. Sag is a
> matter of degree, not a pass/fail.

---

## Aaron — where he actually stands on it

His benchmark take sags on **25 of 51 phrase endings = 49.0%**, which
**beats only 6% of the 50 professional references.** So it is a genuine weakness,
correctly identified, and still inside the professional range rather than off the
chart. It scores **7.43/10**.

Captain Cook tavern take, *Pressure Down* (25 Jul) — the only take with full
seven-component coverage:

| | v5 |
|---|---|
| **Overall** | **8.2** |
| **Capture-fair** | **9.2** ← lead with this, it is a tavern capture |
| Confidence | high |
| Coverage | full (7 of 7) |

| component | score |
|---|---|
| Held-note stability | 10.0 |
| Phrase control | 9.94 |
| Pitch centre | 9.52 |
| Vibrato control | 8.72 |
| Dynamics | 7.92 |
| **Breath support** | **7.43** |
| Voice quality | 4.64 |

Full text: `docs/score-metrics/pressure-down-captain-cook-full-results.txt`
(regenerated under v5).

---

## Every take, re-scored under v5

35 singer takes: overall min 6.6 · max 9.7 · **mean 8.3**. Capture-fair mean 8.19.
9 references: min 8.1 · max 9.6 · mean 8.73.

`cf` = capture-fair. A blank `breath` means the analysis predates
`analyse_breath()` — see the coverage note below.

| singer | date | song | overall | cf | breath |
|---|---|---|--:|--:|--:|
| aaron | 07-11 | vienna-take-001 | **9.7** | 9.6 | – |
| aaron | 07-11 | danger-zone-new-studio-take-002 | **9.5** | 9.5 | – |
| aaron | 07-11 | if-you-could-read-my-mind-take-001 | **9.3** | 9.2 | – |
| aaron | 07-11 | the-letter-joe-cocker-take-001 | **9.3** | 8.9 | – |
| aaron | 07-24 | pressure-down-take-004 | **9.3** | 9.2 | – |
| aaron | 07-24 | pressure-down-take-001 | **9.1** | 8.8 | – |
| aaron | 07-24 | pressure-down-take-003 | **9.1** | 9.0 | – |
| aaron | 07-11 | the-heat-is-on-take-002 | **8.8** | 8.4 | – |
| aaron | 07-12 | goodbye-s-been-good-to-you-take-001 | **8.8** | 8.3 | – |
| aaron | 07-11 | danger-zone-take-003 | **8.7** | 8.5 | – |
| aaron | 07-25 | play-that-funky-music-take-001 | **8.7** | 8.1 | – |
| aaron | 07-11 | the-heat-is-on-new-studio-take-001 | **8.6** | 7.9 | – |
| aaron | 07-24 | pressure-down-take-005 | **8.5** | 7.9 | – |
| aaron | 07-25 | tutti-frutti-take-001 | **8.5** | 7.8 | – |
| aaron | 07-25 | my-babe-take-001 | **8.4** | 8.8 | – |
| aaron | 07-25 | my-babe-take-002 | **8.4** | 8.1 | – |
| aaron | 07-11 | 1973-take-001 | **8.3** | 7.6 | – |
| aaron | 07-25 | **pressure-down-captain-cook-tavern-take-001** | **8.2** | **9.2** | **7.43** |
| aaron | 07-11 | danger-zone-home | **8.2** | 7.6 | – |
| aaron | 07-11 | kryptonite-mango-hill-tavern-take-001 | **8.0** | 8.7 | – |
| aaron | 07-24 | pressure-down-take-002 | **8.0** | 7.2 | – |
| aaron | 07-25 | my-babe-take-003 | **8.0** | 8.1 | – |
| aaron | 07-11 | lets-stay-together-new-studio-take-001 | **7.7** | 6.5 | – |
| aaron | 07-11 | the-heat-is-on-captain-cook-tavern-take-001 | **7.6** | 8.8 | – |
| aaron | 07-25 | pressure-down-take-007 | **7.6** | 7.8 | – |
| aaron | 07-24 | pressure-down-take-006 | **7.5** | 7.7 | – |
| aaron | 07-11 | you-can-leave-your-hat-on-bramble-bay-take-001 | **6.7** | 5.9 | – |
| aaron | 07-12 | come-out-and-play-captain-cook-tavern-take-001 | **6.6** | 7.1 | – |
| leo | 07-11 | chasin-that-neon-rainbow | **8.3** | 9.7 | – |
| rilda | 07-25 | dreams-take-001 | **8.3** | 8.5 | – |
| rilda | 07-11 | this-masquerade-take-001 | **8.2** | 7.5 | – |
| rilda | 07-25 | you-sexy-thing-take-001 | **8.0** | 8.0 | – |
| rilda | 07-11 | lets-stay-together-home-take-001 | **7.8** | 7.0 | – |
| chris | 07-11 | feeling-good-take-001 | **7.7** | 8.4 | – |
| rilda | 07-12 | she-s-not-there-take-001 | **7.1** | 7.2 | – |

Machine-readable: `docs/score-metrics/all-takes-rescore-v5-2026-07-26.json`
(+ the `.md` twin with every component). **Never hardcode that filename** — the
rubric version is in it, and the generator derives it from the engine.

---

## Coverage: read this before comparing takes

**Only 1 of 35 archived takes has phrase-sag data.** The other 34 were analysed
before `analyse_breath()` existed, so they score on **6 of 7 components** with
weights renormalised. Every score now reports this:

```json
"coverage": "partial",
"components_scored": [...],
"components_unscored": ["breath_support"]
```

This is **deliberately not** treated as a provenance conflict. The full-vs-partial
difference is at most ~0.25 points on the reference pack, so refusing to compare
would cost far more than the distortion it avoids — and rule 4 of `CLAUDE.md`
exists precisely because a false withholding once blocked Aaron's best take. The
gap is stated, not hidden.

**To close it properly: re-analyse the archived takes with the current engine.**
The audio is not in the repo (only the Captain Cook take is), so this needs
Aaron's originals from the host or his devices. Until then, the older takes'
overalls are very slightly flattering, in a way that is visible in every payload.

---

## Also fixed in this pass — four stale strings that were misleading readers

These were found by checking claims against data instead of trusting comments.

1. **`cpps_note` said CPPS was "diagnostic only until the reference pack is
   re-analysed with it."** It was already anchored (n=50, p50 11.53 dB) and is
   already one of four `voice_quality` sub-scores. So every full-results report
   told the singer a number carrying ~5% of their score didn't count. Corrected.
2. **`_linear_component`'s docstring claimed p25/p75 anchors.** The code has
   always used **p50** — `git log -S` confirms `stats["p25"]` was never present.
   The same wrong claim was baked into `pro_reference.json`'s own `note` field by
   the builder. Both corrected.
3. **The engine's `provenance` string hardcoded `"deterministic_rubric_v4"`**, so
   a rubric bump would have silently reported the wrong version. Now derived from
   `RUBRIC_NAME`. A test asserted the literal `"v4"` too — it now asserts
   `A.RUBRIC_NAME`.
4. **`rescore_all.py` hardcoded `v4`** in its filenames, keys and headings, so
   its first run under v5 wrote v5 scores into a file named `-v4-`. Now derived
   from the engine. The v4 tables are deleted.

`singers_formant_note` was checked and is **accurate** — the singer's formant
genuinely has no pro anchors and is not in the score. That is the next
zero-cost anchoring candidate, and it is also what a live spectrum meter would
display.

---

## Two follow-ups worth doing (not done here)

**1. `PRIMARY FOCUS` can still name the room.** Rule 7 warns about this. The
picker now prefers capture-*robust* components when the analysis flags elevated
room/mic contamination, and `breath_support` gives it something real to fall back
to. But the Captain Cook take reports `karaoke_or_room_contamination_risk:
"normal"`, so the fix does not fire and the focus is still "Voice quality" —
4.64, driven by jitter/shimmer/HNR/CPPS that all sit at the very bottom of the
pro distribution on a tavern phone capture. The detector only looks at **clipping
and voiced-percentage**; it has no measure of room reverb or noise floor, so a
level-controlled room take reads clean. Retuning it changes `confidence` on every
take, so it needs its own validation pass — deliberately left alone.

**2. The sag > 50% trigger in `report_builder._primary_focus` is miscalibrated.**
It predates the anchors. Pro p90 is 47.8%, so a 50% threshold only fires above
the professional range — Aaron's 49% misses it. Now that the component is
anchored, that branch should key off `breath_support` being weakest instead of a
hand-picked percentage.

---

## Rules that still apply, unchanged

- One engine produces the `/10`. Preflight before publishing. No second ledger.
- `is_legacy_score()` / `score_conflict()` before quoting, comparing or trending.
  Every v4 score is now legacy — `retire_legacy_scores.py` retired the last one.
- Lead with **capture-fair** for live/tavern/phone; state confidence; the scale is
  calibrated to 50 pro vocals where **10 = a typical pro**.
- Send the **full** results, never a summary. Only the headline `/10` is ever
  withheld, never the analysis.

Tests: engine + viewer **105 passed**, voxsuite **27 passed**, preflight **exit 0**.
