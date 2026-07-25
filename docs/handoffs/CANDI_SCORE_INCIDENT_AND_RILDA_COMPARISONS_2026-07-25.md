# Candi hand-off — score incident and Rilda reference comparisons

Date: 25 July 2026
Status: needs manual review for cross-engine scoring; raw comparison findings are complete.

> **UPDATE (later on 25 July) — BOTH incidents below are RESOLVED, and both
> resolved the *opposite* way to the original conclusion.** The common cause:
> `deterministic_rubric_v1` was uncalibrated and carried the dynamics bug, so it
> scored takes roughly **2.5–3 points too harshly**.
>
> **Aaron — `Pressure Down` Take 4:** the 9.5 was withdrawn in favour of a
> recheck at 6.5. The current calibrated engine says **9.3** — the 6.5 was the
> broken number and the withdrawal was unwarranted. Every Pressure Down take rose
> ~2.5–3 points on re-scoring.
>
> **Rilda — `You Sexy Thing` / `Dreams`:** Both takes are now archived in the repo, and their stored scores
> show they were computed with **`deterministic_rubric_v1`, uncalibrated**, with
> the dynamics component cratered (0.0 on `Dreams`, 0.91 on `You Sexy Thing`) —
> the bug fixed in rubric **v4**. Re-scored with the current calibrated engine:
> **`Dreams` 8.3** and **`You Sexy Thing` 8.0**. The 5.1 was not a valid
> alternative reading; it came from a stale rubric carrying a known bug, and the
> comparison engine's higher number was closer to correct. Do not quote 5.1 or
> use it in progress trends — see
> `HANDOFF_ALL_TAKES_SCORES_V4_2026-07-25.md`. The provenance-pinning work in
> "Required canonical fix" below still stands; this resolves the specific
> incident, not the general control gap.

## Executive summary

Two separate score-control problems were found while analysing recent vocal takes:

1. Aaron's `Pressure Down` Take 4 had an old **9.5/10** written into a report even though the then-current deterministic Phase 1 backend ledger said **6.5/10**. The 9.5 was not valid and was withdrawn.
2. Rilda's `You Sexy Thing` report correctly passed the new Phase 1 ledger check at **5.1/10**, but an internal current comparison-engine pass on the same isolated vocal stem produced **8.3/10**. The 5.1 was not invented or stale *within its own Phase 1 ledger*, but this proves that a ledger-only guard is not sufficient when more than one engine/rubric can issue a score.

The immediate safe rule is therefore: **do not publish a new `/10` score unless the report, its source metrics, and the comparison all name the same pinned engine and rubric version.** If that cannot be established, withhold the overall score and publish only the measured findings and caveats.

## What happened

### 1. Aaron — `Pressure Down`, Take 4

- An older saved report stated **9.5/10**.
- Rechecking against the current deterministic Phase 1 backend ledger returned **6.5/10**, high confidence.
- That 6.5 included a zero dynamics component because a separated vocal stem's internal dynamic range exceeded the rubric's capture-sensitive threshold. The zero was a calibration limitation, not a finding that Aaron sang with no dynamics.
- The correct decision was to withdraw the 9.5 and withhold an overall score pending calibration review, while retaining the raw findings: 20-cent median pitch deviation, 36.1-cent median held-note drift, 3.89-second median phrase length, 0.49% jitter, 4.04% shimmer, and 22.66 dB HNR.

### 2. Rilda — `Dreams` (Fleetwood Mac), Bramble Bay

- A live isolated vocal stem was compared directly with a Fleetwood Mac official-audio reference using persisted pitch contours and dynamic-time-warp alignment.
- The take was estimated one semitone above the reference; that transposition was removed before melody comparison.
- Resulting raw comparison: 40-cent median contour distance and 57.5% of matched voiced frames within 50 cents of the reference contour.
- Pitch-centre result: Rilda 20 cents median grid deviation; reference 20 cents.
- Main gap: held-note drift, Rilda 44.6 cents versus reference 30.6 cents. Notes within 25 cents: Rilda 56.9%; reference 67.6%.
- Numeric score was correctly withheld because the Phase 1 dynamics component was capture-sensitive.
- Coaching conclusion remains valid: do not imitate Stevie Nicks' recorded colour; keep Rilda's neutral-balanced tone and let the first beat of a held vowel settle before adding expression.

### 3. Rilda — `You Sexy Thing` (Hot Chocolate), Brighton

- A live isolated vocal stem was compared with an accessible upload of Hot Chocolate's original recording.
- Direct persisted-contour comparison found zero semitone transposition, 40-cent median contour distance, and 61.1% of aligned voiced frames within 50 cents.
- Phase 1 ledger metrics: 25-cent median pitch deviation, 49.3% of notes within 25 cents, 50.2-cent median held-note drift, 32 detected phrases with 3.41-second median phrase length, E3–F5 robust range, and 46.1% of analysed long notes carrying vibrato at a 4.99 Hz median rate.
- The original mix's harmonic key detector favoured F major. The live full-mix detector was nearly tied between B-flat major and F major because of backing/room audio, but the direct vocal comparison found zero semitone shift. Operational conclusion: Rilda sang in the reference vocal key; do not treat the full-mix B-flat result as a transposition.
- The user-facing report stated **5.1/10**, high confidence, only after `validate-report` returned `verified` against the Phase 1 ledger.
- A separate current comparison-engine analysis of the same stem later reported **8.3/10**. This number was not published to the user and must not be compared to the Phase 1 number. The disagreement demonstrates a missing cross-engine provenance control.

## What was changed locally

The Candi Phase 1 workspace now has a fail-closed score gate in `scripts/candi_phase1.py`:

- `score_verdict` marks a score `verified` only when the backend score, confidence and component checks pass.
- Capture-sensitive dynamics failures with a zero component score cause the verdict to be `withheld`.
- `validate-report` rejects a report whose `/10` score is stale, invented, mismatched, or present when the verdict is withheld.
- `save-report` runs the same validation, preventing an invalid score from entering the progress record.
- The operating guidance in `TOOLS.md`, `AGENTS.md`, and the deep Telegram vocal-analysis skill requires validation before a scored reply.

Regression check run on 25 July 2026:

```text
python3 -m unittest -v tests/test_score_guard.py

Ran 4 tests ... OK
```

The four checks cover matching-score acceptance, scoreless reports when a score is withheld, stale/invented score rejection, and capture-sensitive score withholding.

## Important limitation of the local fix

The local gate validates against one manifest's Phase 1 ledger. It does **not** know whether another engine version has analysed the same audio with a different rubric. That is why it allowed the Rilda `You Sexy Thing` 5.1: it was exact for the Phase 1 artifact, but it did not detect the current comparison-engine's 8.3 for the same stem.

Do not describe this as a user error or as proof that either singer's performance changed. It is a system provenance and calibration problem.

## Required canonical fix

Implement the following in the canonical scoring path before treating `/10` values as comparable across reports:

1. **Pin provenance in every score artifact.** Store engine name, engine version/commit, rubric version, stem-separation model, input-audio hash, vocal-stem hash, and analysis timestamp.
2. **Make scores engine-scoped.** A score may only be compared with, validated against, or displayed beside a score from the same engine-plus-rubric identity.
3. **Require a report contract.** A rendered report must include the exact provenance ID that its validator checks; score text without that match must fail closed.
4. **Disable dual scoring.** The reference-comparison analyser may provide raw contour/difference measures, but must not emit a competing overall `/10` unless it is the declared canonical scoring engine.
5. **Add an integration test.** Analyse a fixed vocal stem through every supported entry point. The system must either return the same canonical score or withhold one of them with a clear provenance-conflict reason.
6. **Reconcile historical reports.** Mark past reports with unknown or legacy provenance as `needs manual review`; do not use them in progress trends until mapped to a canonical rubric.

## Safe operating rule until the canonical fix lands

- Use one pinned Phase 1 engine/rubric for any numeric technical score.
- Run report validation immediately before sending and immediately before saving.
- If the report also uses a different comparison engine, publish only non-score comparison measures unless both engines share the same canonical score contract.
- When calibration is capture-sensitive or provenance conflicts, say `score withheld pending calibration review`; never substitute a rounded, listener-impact, legacy, or manually adjusted score.

## Source artefacts in the Candi workspace

- `openclaw-data/vox-coach/memory/analyses/2026-07-25-rilda-dreams-take-001.md`
- `openclaw-data/vox-coach/memory/analyses/2026-07-25-rilda-you-sexy-thing-take-001.md`
- `openclaw-data/vox-coach/temp/metric-json/2026-07-25-rilda-you-sexy-thing-take-001-normalised.json`
- `openclaw-data/vox-coach/temp/metric-json/2026-07-25-rilda-you-sexy-thing-vs-hot-chocolate.md`
- `scripts/candi_phase1.py`
- `tests/test_score_guard.py`

Those recordings and local analysis artifacts are intentionally not added to this repository. This hand-off contains the reproducible operational facts and the required implementation direction.
