# HANDOFF: VOXAI Metrics Engine v2 — for the analysis agent (Candi/OpenClaw)

Audience: the agent that runs `analyse_song.py`, reads the backend JSON, and
writes the singer-facing analysis/report. Read this fully before running the
next analysis.

## Why this handoff exists

An audit found two classes of problems in the previous pipeline:

1. The headline scores in results ("listener-impact estimate", "deep
   technical score") were **not computed by any code** — they were generated
   or rescaled at the report layer. Manual instructions like "treat 9.8 as a
   10" confirmed the numbers were subjective, not measured.
2. Several metrics compared against clinical/professional thresholds were
   measured invalidly: jitter counted melody as pathology, shimmer was
   documented but never computed, an HPSS ratio was mislabelled as HNR,
   LPC formants at 44.1 kHz/order 12 produced noise, and "vibrato" was one
   FFT over the whole song (which mostly measures note-change rate).

Both are fixed. The engine now measures with Praat algorithms on sustained
notes and computes a **deterministic technical score** from documented
formulas. Your job changes accordingly — see "Operating rules" below.

## 1. Getting the new engine

The upgraded code lives in `rustwoodagent-ops/vox-cloud-alpha`, branch
`claude/voxai-metrics-validation-giecvu` (PR #1). Files changed:

```text
backend/voxai-local-analysis/analyse_song.py    (rewritten measurement core)
backend/voxai-local-analysis/requirements.txt   (adds praat-parselmouth)
scripts/candi_phase1.py                         (new metric keys + scoring_policy in manifest)
docs/metrics-methodology.md                     (audit trail for every metric/formula)
```

If you run from the standalone `voxai-local-analysis` repo on the local
machine, copy `analyse_song.py` and `requirements.txt` from
`backend/voxai-local-analysis/` over your local copies (they are the same
layout), then:

```bash
# inside voxai_env
pip install praat-parselmouth
```

Verify the install before trusting any results:

```bash
python -c "import parselmouth; print(parselmouth.VERSION)"
```

If parselmouth is missing the engine still runs, but voice-quality drops to
a clearly labelled low-reliability fallback (approximate jitter only;
shimmer/HNR honestly omitted) and score confidence falls. Do not present
fallback output as clinical measurement — check the `method` fields.

## 2. What changed in the backend JSON

Renamed/replaced keys — update anything that reads the JSON:

| Old key | New key | Change |
|---|---|---|
| `perturbation` | `voice_quality` | Praat jitter/shimmer/HNR, per sustained note, median-aggregated; includes `method`, `reliability`, `n_notes_measured` |
| `hnr` | `harmonic_balance` | Same HPSS ratio, honestly labelled: whole-file texture, NOT clinical HNR. Clinical HNR is `voice_quality.hnr_db_median` |
| `vibrato` | `vibrato` | Now per-note: `n_notes_analysed`, `pct_notes_with_vibrato`, `median_rate_hz`, `median_extent_cents`, per-note list |
| `formants` | `formants` | Praat Burg at sustained-note centres, `F1/F2/F3_median_hz` ± IQR |
| — | `intonation` | NEW: sustained-note deviation from equal-tempered grid (tuning offset removed), `median_abs_deviation_cents`, `pct_notes_within_10_cents`, intra-note drift, classification |
| — | `phrasing` | NEW: phrase count/durations (breath-management proxy) |
| — | `technical_score` | NEW: deterministic 0–10 score with full component breakdown |
| `pitch.range_semitones` | same | Now robust (P2.5–P97.5); extreme frames reported separately as `full_range_semitones` |

Interpretation guidance per metric (thresholds, formulas, known limits) is
in `docs/metrics-methodology.md`. Quick anchors:

- Intonation: median abs deviation ≤5 cents = exceptional, ≤10 = professional,
  ≤20 = good, >35 = poor or unreliable tracking.
- Vibrato: professional ≈ 5–7 Hz, 25–130 cents extent, on most long notes.
- Voice quality (sung sustained notes): jitter ≤0.5% very stable, HNR ≥15 dB
  clean; the speech thresholds (1.04%/3.81%) are for spoken vowels — do not
  flag a singer against them directly.

## 3. Operating rules (this is the important part)

The manifest from `candi_phase1.py prepare` now includes a `scoring_policy`
block. These rules are binding:

1. **Quote `technical_score` verbatim** — the overall number, its
   `confidence`, and the component breakdown. Never invent, rescale, curve,
   or "round up" a numeric score. The old instruction "anything above 9.8
   is a 10 / 9 is close to a 10" is retired: if a score feels miscalibrated,
   say so in prose and flag it to Aaron so the rubric (not the number) gets
   changed.
2. **Listener impact / artistry commentary is welcome but must be labelled
   as a subjective impression and must not be expressed as a numeric
   score.** The technical score deliberately excludes artistry, emotion,
   interpretation, and style — those are yours to describe in words.
3. **Check `method` and `reliability` fields before making claims.** If
   `voice_quality.method` is `frame_f0_approximation`, say the clinical
   metrics were unavailable rather than reporting them as measured.
4. **Respect `confidence` and `environment_risk`.** On elevated capture
   risk (karaoke bleed, clipping, low voiced %), present metrics as
   supporting evidence, not verdicts. Tempo on isolated stems is flagged
   low-confidence — don't build coaching around it.
5. **"VOXAI Advanced compliance" only means the two knowledge files exist
   and are readable.** Do not present it as a claim about analysis quality.
6. Keep the existing measured / inferred / unverifiable tagging discipline
   from the knowledge core. The new JSON gives you more genuinely
   "measured" material; use it.

## 3b. Professional-reference calibration (rubric v2)

The score can be anchored to real professional performances instead of
theoretical thresholds. Once Aaron supplies 15–20 pro reference tracks:

1. Analyse each with the normal pipeline (`--separate-stems`).
2. Build the calibration:
   `python tools/build_calibration.py output/ --out calibration/pro_reference.json`
3. All later runs pick it up automatically; the JSON then shows
   `technical_score.calibration.active = true` and each component reports
   "matches or beats X% of N pro references".

When presenting a calibrated score, say what it means: "9–10 = sitting
inside the professional reference pack, measured identically." Until the
calibration file exists, scores use theoretical anchors and the JSON says
so — mention that scores will re-anchor once the pro references are in.

Rubric v2 fairness notes (already in the formulas — do not re-penalise in
prose): deliberate straight tone is a valid style (scored via steadiness,
not missing vibrato); compressed/mastered stems limit raw dynamic range
through no fault of the singer (phrase-level shaping is scored instead);
short pop phrasing is a style, not a breath defect.

## 3c. Take-vs-original comparisons: use the capture-fair score

`technical_score.capture_fair_score_0_to_10` excludes voice_quality
(weights renormalised). For ANY comparison between a singer's take and an
original recording — or between recordings from different eras/chains —
compare capture-fair scores on both sides. Voice quality (jitter/shimmer/
HNR) partly measures the recording chain: vintage separated stems read far
worse than clean modern captures, so overall-score head-to-heads
systematically flatter the newer recording. Never report a singer as
out-scoring the original based on overall scores; if the capture-fair
comparison still favours the singer, present it with the methodology
caveat. The overall score remains correct for absolute results and
tracking the same singer's progress over time.

## 4. Sanity checks after switching

Run these once after adopting the new engine:

1. `python analyse_song.py <known_track>.wav --name "Test" --separate-stems`
   completes and the JSON contains `technical_score.overall_score_0_to_10`,
   `intonation`, and `voice_quality.method` = `praat_parselmouth_per_sustained_note`.
2. Run the same file twice — the technical score must be identical
   (determinism is the whole point; if it differs, something is wrong).
3. Confirm the vocals stem path in `stem_separation.vocals_path` is the
   actual vocal (a former bug could select the `no_vocals` instrumental —
   fixed, but verify once on your separator's naming).
4. Re-run a professional reference (e.g. the Andy Gibb take) and check the
   components read sensibly: strong pro vocals should show intonation
   median ≤10 cents, consistent 5–7 Hz vibrato, HNR well above 15 dB.

Expected calibration from synthetic validation: a clean in-tune voice with
5.5 Hz vibrato scores 8.5/10 (high confidence); an off-pitch, drifting,
breathy, dynamically flat voice scores 4.1/10.

## 5. Format for the singer-facing report (unchanged sections, new sources)

- "Performance Readiness Score" → use `technical_score` verbatim with its
  confidence, plus a one-line plain-language summary of the top and bottom
  components.
- "Measured / Directly Heard" → intonation, vibrato, voice quality,
  dynamics values (they are now genuinely measured).
- "Inferred" → physiological causes (breath pressure, registration, larynx
  position) remain inferences; keep the "likely/suggests" language.
- "Unverifiable" → artistry/emotion/listener impact — prose only, labelled
  subjective.
