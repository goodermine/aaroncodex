# VOXAI Metrics Methodology

This document is the audit trail for every number VOXAI reports: what is
measured, how, and what its limits are. The design rule is simple —
**every figure is either a real measurement or a documented formula over
real measurements. Nothing numeric is generated or adjusted by a language
model.**

## Measurement principles

1. **Sustained-note gating.** Jitter, shimmer, HNR, formants, vibrato and
   intonation are only meaningful on sustained phonation. The pitch track
   (librosa pyin, C2–D6) is segmented into voiced runs, which are split into
   sustained notes wherever the median-filtered contour jumps more than 60
   cents. All voice-quality measurement happens inside these notes — never
   across pauses, consonants, or note changes. This is what makes the
   metrics comparable to professional/clinical references: a melody moving
   between pitches is musicianship, not instability.
2. **Praat algorithms for clinical metrics.** Jitter (local/RAP/PPQ5),
   shimmer (local/APQ3/dB), HNR and formants (Burg) are computed with Praat
   via `praat-parselmouth` — the same algorithms used in voice research.
   Each is measured per sustained note and aggregated with the median. If
   parselmouth is missing, the tool falls back to clearly-labelled
   low-reliability approximations and omits (rather than guesses) shimmer
   and HNR.
3. **Method + reliability labels.** Every module reports `method` and,
   where relevant, `reliability`, so downstream reports can't silently
   present a fallback as a clinical measurement.
4. **Active-frame gating for spectral stats.** Brightness (centroid,
   rolloff, flatness) is averaged over frames above the −60 dB silence
   threshold only. On isolated stems with long gaps, silence would
   otherwise skew the averages.
5. **Robust statistics.** Pitch range uses the 2.5th–97.5th percentile of
   voiced frames (single octave-error frames from the tracker cannot
   inflate it); extremes are reported separately, flagged as possibly
   containing tracker errors.

## Module summary

| Module | Method | Notes / limits |
|---|---|---|
| Pitch | librosa pyin, C2–D6 | Robust range = P2.5–P97.5 of voiced frames |
| Voice quality | Praat jitter/shimmer/HNR per sustained note, median | Speech-pathology thresholds (1.04% / 3.81%) are for spoken vowels; singing bands are used for interpretation |
| Intonation | Sustained-note median pitch vs equal-tempered grid, global tuning offset removed | Proxy for accuracy — expressive slides/blue notes register as deviation |
| Vibrato | Per note ≥ 0.5 s: FFT of detrended cents contour; rate 4–8 Hz, extent 10–300 cents, band-power prominence | Whole-song FFT (old method) measured note-change rate, not vibrato |
| Formants | Praat Burg at sustained-note centres, median ± IQR; ceiling configurable (`--formant-ceiling`) | LPC fallback downsampled to 11 kHz with order sr/1000+2 |
| Resonance | librosa spectral features, active frames only | Classification thresholds 1200/2500 Hz are heuristics |
| Dynamics | RMS dB relative to file peak; effective range = P10–P90; phrase-level spread | Internal contrast, not absolute loudness |
| Rhythm | librosa onsets + beat track | Tempo flagged low-confidence on isolated stems |
| Harmonic balance | HPSS whole-file ratio | Texture descriptor only — explicitly *not* clinical HNR (older versions mislabelled it) |
| Phrasing | Voiced runs merged across gaps < 0.3 s | Breath/phrase-length proxy |

## Deterministic technical score (rubric v2)

`technical_score.overall_score_0_to_10` is a weighted mean of documented
component formulas (weights renormalised over the components that could be
measured for that take):

| Component | Weight | Uncalibrated formula |
|---|---|---|
| Intonation accuracy | 25% | 10 at ≤5 cents median grid deviation → 0 at ≥45 |
| Pitch stability | 15% | 10 at ≤10 cents intra-note drift → 0 at ≥80 |
| Voice quality | 20% | mean of jitter (10 @ ≤0.3%), shimmer (10 @ ≤2.5%), HNR (10 @ ≥20 dB) sub-scores |
| Vibrato control | 15% | best of two style paths: vibrato quality (presence 10 @ ≥40% of long notes, rate ideal 5–7 Hz, extent ideal 25–130 cents) OR straight-tone steadiness (10 @ ≤12 cents drift) — deliberate straight tone is a valid professional style |
| Dynamics/expression | 15% | best of phrase-level spread (ideal 3–12 dB) and effective range (ideal 6–22 dB) — mastered/compressed stems limit raw range through no fault of the singer |
| Phrase control | 10% | 10 at ≥2.5 s median phrase → 0 at ≤0.5 s |

Each component's JSON output includes its input value, formula and weight,
so any score can be audited by hand. A `confidence` field (high/medium/low)
reflects whether Praat metrics were available, how many sustained notes
were found, and whether capture-risk markers were raised.

### Professional-reference calibration

Theoretical anchors answer "is this physically excellent?"; calibration
answers the question singers actually ask — "how do I compare to the people
on the radio?". Workflow:

1. Analyse 15–20 professional reference takes (tracks the human ear already
   certifies as 9–10) with the normal pipeline.
2. `python tools/build_calibration.py output/ --out calibration/pro_reference.json`
3. `analyse_song.py` then loads the calibration automatically (or via
   `--calibration <path>`; `--calibration none` forces theoretical anchors).

With calibration active, each linear component's "10" anchor moves to the
professional pack **median** — matching a typical professional reference IS
the top of the scale; band components (vibrato rate/extent, dynamics) take
their ideal bands from the pro p10–p90. Zero anchors stay theoretical, so
weak performances still score low. Validated against the initial 11-track
pack: the references themselves score 8.4–10.0 (median 9.0) against their
own calibration, while a deliberately flawed synthetic control scores 5.5. The output reports, per component, the
percentile of the singer against the reference pack ("matches or beats X%
of N pro references") — the score is anchored to verified human-certified
material while remaining fully deterministic and auditable. References
whose voice-quality metrics came from the non-Praat fallback are excluded
from voice-quality anchors; any metric with fewer than 5 reference values
stays on theoretical anchors.

### What the score does NOT measure

Artistry, emotional delivery, lyric interpretation, groove feel and
style-appropriateness are human judgements. They are deliberately excluded.
If a report includes a "listener impact" style estimate, it must be
labelled as a subjective impression and must not be presented as a numeric
measurement — this is enforced in the Candi manifest `scoring_policy`.

## Known remaining limits

- Stem separation artifacts (phasey tails, backing-vocal bleed) degrade all
  downstream metrics; the `environment_risk` block flags elevated risk and
  the score confidence drops accordingly.
- Intonation vs the 12-TET grid penalises deliberate microtonal styling.
- pyin can still octave-flip on breathy onsets; robust statistics limit but
  don't eliminate the effect.
- The "Advanced compliance" check (`verify_voxai_knowledge.py`) verifies
  only that the knowledge files exist and are readable — it is not a claim
  about analysis quality and should not be presented as one.
