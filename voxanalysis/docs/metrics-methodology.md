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
| Onset density & regularity (`rhythm`) | librosa onsets on the vocal; onset rate + inter-onset regularity | Onset *density/regularity* of the delivery only; its beat-track tempo is indicative (low-confidence on an isolated stem). Timing-vs-the-song is the `groove` module, not this. |
| Groove / timing (`groove`) | Vocal-stem onsets vs the half-beat grid of the **vocal-free instrumental** stem (unbiased); tempo cross-checked against the **original pre-split mix** | Canonical timing scorer. Confidence high when the mix and instrumental tempos agree, medium with a single reference. The mix is used as the cross-check (not the offset grid) so the vocal can't self-reference the beat phase. |
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

### Rubric v3 (current)

v3 keeps v2's six components and weights unchanged, with one refinement and
a deliberate set of exclusions:

- **CPPS joins the voice-quality component.** Voice quality is now the mean
  of jitter / shimmer / HNR / **CPPS** sub-scores (still 20% weight). CPPS
  (cepstral peak prominence) is the modern research-standard clarity
  measure; it discriminates properly (validated: clarity 13→5 dB drops the
  voice-quality component 10.0→7.8) and, being capture-sensitive like the
  other three, rides inside the capture-fair exclusion automatically.
- **Everything else measured since v2 is reported but deliberately NOT
  scored**, each for a documented reason:
  - *Vibrato onset delay* — measured, but all 50 professional references
    read 0.0 s on this pop/rock/soul/country pack (the "straight-then-bloom"
    is a classical technique). It does not discriminate here, so scoring it
    would be dead weight or would penalize the pros. Kept diagnostic.
  - *Singer's formant / projection* — a real pro trait, but low by *style*
    for intimate/dark singers (e.g. Norah Jones) and partly a function of
    the microphone. Scoring it would penalize legitimate style and reward
    capture. Reported with a pro-percentile; never scored.
  - *Strain, onset scoops/overshoots, breath-end sag* — style choices or
    heuristics (deliberate grit, soul scooping, expressive fall-offs).
    Scoring them would punish artistry. Prescription triggers and
    diagnostics only.
  - *Registers, groove, range, harmonic profile, vowel space* — heuristic,
    context-dependent, or descriptive rather than quality axes.

This exclusion list is a feature: the score rewards technical execution a
better singer genuinely controls, and refuses to move on things that are
style, capture, or guesswork.

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

### Capture-fair comparison score

`technical_score.capture_fair_score_0_to_10` is the same rubric with the
voice_quality component excluded (weights renormalised). Jitter, shimmer
and HNR partly measure the recording chain rather than the singer: a
vintage master ripped and run through stem separation reads 2–3× worse on
these than a clean modern capture of an equal voice (observed across every
vintage reference: shimmer 13–15% vs ≤5% for clean captures).

Rules of use:
- **Take vs original / any cross-era comparison** → compare capture-fair
  scores on both sides. Never declare a singer "better than the original"
  from overall scores.
- **Absolute result and self-progress** (same singer, same setup over
  time) → use the overall score; there voice quality legitimately reflects
  technique and capture improvements the singer controls.

### Reference-pack admission policy

The calibration pack defines what "professional" measures as — so what goes
in matters as much as how it's measured. Policy (owner: Aaron):

- **Studio recordings only.** Live recordings (PA bleed, crowd noise, room
  reverb) and pre-hi-fi-era transfers (narrowband, noisy) measure worse on
  voice quality *because of the capture chain, not the singer* — including
  them drags the professional anchors and makes the whole scale less honest.
  Removed on this basis (2026-07): Bon Jovi Live 8 2005, Joe Cocker at
  Woodstock, Cold Chisel Bow River Live 1983, Judy Garland 1939. All four
  artists remain represented (or eligible) via studio recordings.
- **One performance per recording** (no duplicate files of the same take;
  different recordings of the same song by different artists are fine).
- **Prominent lead vocal, sustained-note-rich, minimal audible pitch
  correction** — calibration needs real sustained phonation and honest
  intonation, so heavily autotuned productions are poor references.
- Balance targets: roughly even male/female, a spread of eras and styles
  (belt, croon, straight-tone, vibrato-led, country, soul, rock, pop,
  theatre), pack size ~50.

### What the score does NOT measure

Artistry, emotional delivery, lyric interpretation, groove feel and
style-appropriateness are human judgements. They are deliberately excluded.
If a report includes a "listener impact" style estimate, it must be
labelled as a subjective impression and must not be presented as a numeric
measurement — this is enforced in the Candi manifest `scoring_policy`.

## Time-localised trouble spots

The intonation block also reports WHERE problems live, not just their size:

- `intonation.notes` — every sustained note with timestamp, note name,
  tuning-corrected grid deviation, whole-note drift, and mid-note drift
  (middle 60% of the contour, so onset scoops and release slides don't
  read as held-note drift).
- `worst_intonation_notes` / `worst_drift_notes` — top offenders past the
  trouble thresholds (25 cents off-grid / 40 cents mid-note movement);
  mid-note movement above 300 cents is treated as a deliberate slide or
  segmentation artifact and excluded.
- `sections_20s`, `most_drift_sections`, `most_off_grid_sections` — 20-second
  section map for "which part of the song needs work".
- The Markdown report renders these plus long sustains (≥1.2 s) without
  vibrato (a style check, not automatically a fault). Large mid-note
  movement can be drift OR intentional runs — the timestamps exist so a
  human can judge by ear.

## Deep-analysis diagnostics (reported, not yet scored)

These modules ship as timestamped diagnostics. They deliberately do NOT
feed the calibrated technical score until the reference pack is
re-analysed with them (a future, explicit rubric-v3 step) — anchors must
never shift silently.

| Module | What it measures | Reliability |
|---|---|---|
| CPPS (`voice_quality.cpps_db`) | Cepstral peak prominence (Praat) — research-standard phonation clarity | high |
| Strain (`voice_quality.strain*`) | Top-quartile notes that are loud with HNR ≥4 dB below the take's own median — timestamped "pushed note" flags | medium (intentional grit also trips it) |
| Registers (`registers`) | Per-note spectral-balance 2-means → chest/head split, estimated passaggio, timestamped transitions; honestly reports "no clear split" when clustering separation is weak | medium (heuristic) |
| Vibrato onset delay (`vibrato.median_onset_delay_s`) | Time from note start until vibrato blooms (pros ~0.2–0.6 s) | medium |
| Breath (`breath`) | Phrase-end pitch sag (final 0.5 s slope) — timestamped "ran out of air" flags | medium (intentional fall-offs also trip it) |
| Groove (`groove`) | Vocal onsets vs half-beat grid of the vocal-free instrumental stem — rushing/dragging in ms, per 20 s section; tempo cross-checked against the original pre-split mix | high when mix↔instrumental tempos agree, else medium (needs a rhythmic backing) |
| Range map (`range_map`) | Time-weighted seconds-per-semitone, comfortable core (mid-80%), extremes | high |

Competitor-parity diagnostics (post-take equivalents of what VoceVista /
Sing&See display live; no live tracking, no EGG by design):

| Module | What it measures | Reliability |
|---|---|---|
| Singer's formant (`resonance.singers_formant_ratio_db`) | Median 2–4 kHz vs 80 Hz–2 kHz energy on active frames — projection/"ring" | high (heuristic labels) |
| Onset quality (`onsets`) | Per-note approach: clean / scoop (>25 c below, sliding up) / overshoot (>25 c above, settling); timestamped worst offenders | high measurement, style-neutral interpretation |
| Harmonic profile (`harmonics`) | Median H1–H8 relative strengths + H1−H2 phonation-weight proxy | medium (read H5+ cautiously on separated stems) |
| Vowel space (`formants.vowel_space`) | Per-note F1/F2 mapped to nearest cardinal vowel; distribution + timestamps; notes above F0 350 Hz excluded (physics limit) | medium |
| Spectrogram panel | Added to the diagnostics plot with the 2–4 kHz band marked | visual aid |

### Visual report v2

The diagnostics output is now three artifacts, all rendered from already-measured data (no new metrics, scores unchanged):

- **Main plot (7 panels)**: section-health ribbon (green/amber/red from the trouble thresholds), waveform, pitch contour on a note-named axis with the comfortable-core band shaded, RMS, vibrato rate/extent timeline with the pro 5–7 Hz band, F1/F2 vowel chart with cardinal targets, and the spectrogram with F0 + H2–H6 harmonic traces and the singer's-formant band.
- **Note inspection cards** (`*_note_cards.png`): up to 3 flagged notes (strained first, then worst drift/off-centre) — spectrum slice, harmonic peak markers, H1–H8 table in note+cents / Hz / dB format.
- **Per-note CSV** (`*_notes.csv`): every sustained note with intonation, vibrato and onset columns, joined on the shared note start time.

Reports use VoceVista-style `note+cents` notation (`F♯3+24ct`) via the additive `note_detailed` field; existing `note` fields are unchanged for compatibility.

### Live harmonic scope artifacts (display only)

Viewer jobs may opt into post-take spectral artifacts after the normal VOXAI
analysis succeeds. These artifacts are visual evidence only: no metric, score,
diagnostic flag, prescription or coaching claim reads from them.

- **Spectral tiles:** `librosa.cqt` over the isolated vocal, sampled at
  44.1 kHz with a 2048-sample hop (21.5332 frames/s), 3 bins per semitone and
  a visible C2–C7 range. Magnitudes are converted to dB relative to the take's
  strongest CQT value, clipped to −80–0 dB, mapped linearly to 8-bit grayscale,
  stored high-frequency-first, and split into PNG tiles no wider than 2048
  frames. The descriptor records the exact time/MIDI mapping and declares C7
  as the exclusive upper boundary.
- **Harmonic tracks:** H1–H8 band peaks are sampled at `k × F0` using the
  measured browser pitch-contour cadence. Each voiced frame is expressed in dB
  relative to its strongest available harmonic; unvoiced and out-of-range
  values are `null`. The internal CQT extends above the visible image solely so
  upper harmonics can be sampled without expanding the browser plot.
- **Limits:** CQT window support can show faint energy shortly before a sharp
  onset, stem-separation artifacts can create false upper-band energy, and
  display intensity is relative within the take rather than calibrated SPL.
  These limitations are why the layer is labelled `Spectral energy — display
  only` and cannot feed downstream numeric analysis.

The exporter is flag-gated off by default. Export failure is isolated from the
analysis pipeline and yields an unavailable layer rather than a failed score or
report. Artifacts live under the viewer job directory and inherit its existing
retention cleanup.

### Companion tools

- **`tools/compare_takes.py take.json original.json`** — melody-match: DTW
  alignment of the persisted 10 Hz pitch contours (`pitch.f0_contour`),
  global transposition detected and removed (singing in a lower key is a
  choice, not an error), then per-20 s section: sharp/flat vs the original
  melody and ahead/behind timing feel. Validated on ground truth: a +3
  semitone, +15 cent synthetic copy was recovered as exactly +3 st and
  ~10–15 cents.
- **`tools/progress_report.py output/ --singer NAME [--song SLUG]`** — the
  progress ledger: per-take metric table plus first→latest trends for
  score, intonation, drift, voice quality, vibrato, phrasing and breath.

## Deterministic prescription engine (v1)

`prescriptions` maps measured limiters to exercise categories extracted
**verbatim** from the Scientific Exercise Library — rules, not language
models. The map (`knowledge/prescription_map.json`, built by
`tools/build_prescription_map.py`) is pinned to the library's sha256; the
engine warns when the library has changed since the map was built.

Triggers (each carries evidence + severity = 100 − pro-pack percentile
where calibration exists):

| Trigger | Category | Guards |
|---|---|---|
| Median grid deviation > 20 c | pitch_accuracy | — |
| Held-note drift > 40 c / >30% sagging phrase ends | breath_support | fall-off style caveat in evidence |
| ≥25% of top notes strained | pressed_strained (+25 safety boost, SOVT-first) | suppressed on capture risk / non-Praat |
| Jitter ≥1.5% AND HNR ≤10 dB | breathy_leaky | suppressed on capture risk / non-Praat |
| Singer's formant < −20 dB AND dark centroid | muffled_dull | — |
| Vibrato on 8–40% of long notes, or rate outside 4.5–7.5 Hz | vibrato (exercises 101–106) | <8% presence = straight-tone style, never triggered |
| Register transitions > 35% of notes | register_bridge | low-confidence label |

Primary = highest severity; up to 5 supporting. No trigger → no drill
("exercises are prescriptions, not rewards"). Measured issues without a
library category (e.g. groove/timing) are surfaced as `no_direct_coverage`,
never force-fitted. Candi may choose among the prescribed category's
exercises using drill history, or deviate with explicit justification
(enforced in the manifest scoring_policy).

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
