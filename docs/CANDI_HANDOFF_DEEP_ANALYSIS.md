# HANDOFF: Candi — Deep-Analysis Engine (everything since Metrics V2)

Audience: Candi, the coaching agent that runs `analyse_song.py`, reads the
backend JSON, and writes singer-facing reports. This supersedes nothing —
`AGENT_HANDOFF_METRICS_V2.md` still applies in full (Praat metrics,
calibration workflow, scoring rules). This document covers everything
added since: capture-fair comparison, trouble spots, the deep-analysis
suite, the competitor-gap diagnostics, and two new tools.

## 0. First actions

1. Pull latest `main` of vox-cloud-alpha (tip at or after `1a89f5e`) and
   carry `analyse_song.py` + `tools/` into the working backend as usual.
2. No new Python dependencies — everything runs on the existing
   `voxai_env` (parselmouth, librosa, etc.).
3. Sanity check one analysis: the JSON should now contain `onsets`,
   `harmonics`, `registers`, `breath`, `range_map`,
   `resonance.singers_formant_ratio_db`, `pitch.f0_contour`, and
   `technical_score.capture_fair_score_0_to_10`. The diagnostic plot now
   has 5 panels (spectrogram added, 2–4 kHz band marked).

## 1. Scoring rules — two additions to what you already follow

1. **Capture-fair comparisons.** For ANY take-vs-original or cross-era
   comparison, compare `technical_score.capture_fair_score_0_to_10` on
   BOTH sides — never overall scores. Voice quality partly measures the
   recording chain: vintage separated stems read far worse than clean
   modern captures. Never declare a singer better than the original from
   overall scores. Overall score remains correct for a singer's absolute
   result and self-progress.
2. **Diagnostics are not scores.** Everything in sections 2–4 below is
   measurement and coaching material. None of it feeds the calibrated
   technical score yet (that is a future explicit "rubric v3" step after
   the reference pack is re-analysed). Do not invent numeric scores from
   diagnostics; quote the measured values with their timestamps.

## 2. Time-localised trouble spots (in `intonation`)

- `intonation.notes` — every sustained note: `time` (m:ss), note name,
  `deviation_cents` (tuning-corrected grid deviation), `drift_cents`,
  `held_drift_cents` (mid-note only; onset scoops/release slides excluded).
- `worst_intonation_notes` / `worst_drift_notes` — top offenders
  (>25 c off-grid / >40 c mid-note movement; >300 c excluded as deliberate
  slides or artifacts).
- `sections_20s`, `most_drift_sections`, `most_off_grid_sections` — which
  stretch of the song needs work.

**How to coach with it:** quote timestamps, not averages. "Park the first
second of the 2:32 A3" beats "watch your drift". Deviations near ±50 cents
mean halfway between semitones (the measurable maximum). Large mid-note
movement can be drift OR a deliberate run — listen at the timestamp before
prescribing.

## 3. Deep-analysis diagnostics (per-take)

| Block | Key fields | Coaching read | Cautions |
|---|---|---|---|
| `voice_quality.cpps_db` | CPPS in dB | Research-standard clarity; higher = clearer phonation (sung material typically ~8–14) | Diagnostic only |
| `voice_quality.strain` + `strained_notes` | % of top-quartile notes strained, timestamps | "Pushed" top notes: high + loud + HNR ≥4 dB below the take's own median | Intentional grit also trips it — confirm by ear |
| `registers` | % full vs light, `estimated_passaggio`, `transitions` (timestamped) | Where the voice shifts gear; passaggio estimate; may honestly report "no clear two-register split" (usually a well-blended mix — good) | Spectral heuristic, medium reliability |
| `vibrato.median_onset_delay_s` | seconds until vibrato blooms | Pros typically 0.2–0.6 s; near-zero can read as wobble, very late as afterthought | Per-note values in `vibrato.notes` |
| `breath` | `pct_sagging_endings`, `sagging_phrase_ends` (timestamped) | Pitch sagging in the final 0.5 s = likely running out of air on LONG phrases | Intentional fall-offs (rock/soul) also trip it |
| `groove` | `mean_offset_ms`, `feel`, `sections_20s` | Rushing (negative) / dragging (positive) vs the singer's own backing track, per section; under ~25 ms reads tight | Deliberate back-phrasing shows as consistent positive offset — style |
| `range_map` | `comfortable_core`, `extremes_touched`, `most_used_note` | Where the voice actually lives, time-weighted | Single take only; accumulate across songs for the true picture |

## 4. Competitor-parity diagnostics (VoceVista / Sing&See vocabulary)

| Block | Key fields | Coaching read | Cautions |
|---|---|---|---|
| `resonance.singers_formant_ratio_db` | dB + `singers_formant_read` | The 2–4 kHz "ring"/projection band: > −12 strong ring, −12 to −20 moderate, < −20 soft/dark | Heuristic bands until pro anchors exist |
| `onsets` | `pct_clean` / `pct_scooped` / `pct_overshot`, `deepest_scoops` (timestamped) | How notes are approached. **Scooping is a legitimate style** — Al Green measures 55% scooped at −133 cents. Coach CONSISTENCY and intent, never "stop scooping" by default | Compare with the original via melody-match to see if the artist scoops in the same places |
| `harmonics` | H1–H8 relative dB, `H1_minus_H2_median_db` + read | Overtone balance; H1−H2: >+6 light/flutey source, −6..+6 balanced, <−6 rich/pressed | Read H5+ cautiously on separated stems |
| `formants.vowel_space` | per-note vowel map, `vowel_distribution` | What vowels the singer actually produces; useful for vowel-modification coaching | Notes above F0 350 Hz excluded — physics limit, not a bug. Sung vowels are approximate |
| Diagnostic plot | 5th panel: spectrogram | Show singers the harmonics and the marked 2–4 kHz band — the visual language of VoceVista/Sing&See | — |

## 5. New tools

**Melody-match** — the take-vs-original comparison:
```bash
python tools/compare_takes.py output/<take>_analysis.json calibration/references/<original>_analysis.json --out reports/<name>-melody-match.md
```
- Works from the persisted `pitch.f0_contour` — no audio re-processing.
- Detects and removes transposition (report it neutrally: "sung 3 semitones
  down — a key choice, not an error").
- Per-20 s section: sharp/flat of the original melody, ahead/behind feel,
  worst sections. Departure can be deliberate interpretation — judge by ear
  at the timestamps before coaching it as a fault.

**Progress ledger** — the singer's trajectory:
```bash
python tools/progress_report.py output/ --singer aaron [--song danger-zone] [--out reports/aaron-progress.md]
```
- Per-take table + first→latest trends across all headline metrics.
- Run it whenever a singer asks "am I getting better?" — and cite raw
  metrics (cents, dB, %) for exact comparisons; scores from different
  calibration-pack sizes are only approximately comparable.

## 6. Report-writing guidance (Aaron's product intent)

- Lead with what's working; the deep diagnostics exist to make praise and
  prescriptions SPECIFIC ("your H1−H2 says balanced source; your 2–4 kHz
  ring is moderate and strongest in the chorus").
- One primary drill, as always — pick it from the single worst *calibrated
  score component*, then use trouble-spot timestamps to make the drill
  concrete.
- Style-neutrality is policy: scoops, straight tone, back-phrasing and
  fall-offs are styles to be consistent about, not defects. The measured
  pro references (Al Green et al.) prove it — cite them when reassuring a
  singer.
- Keep the measured / inferred / unverifiable discipline. Every new block
  carries `method` and `reliability` — anything marked medium-reliability
  or heuristic goes in "inferred", not "measured", when you make claims
  from it.

## 7. Sanity checks after adopting

1. Analyse one take; confirm the new JSON blocks and the 5-panel plot.
2. Run melody-match on a take that has an analysed original; confirm the
   transposition and section table read sensibly.
3. Run the progress ledger for one singer; confirm ordering (newer JSONs
   carry `analysed_at` for exact ordering).
4. Confirm the technical score for an already-analysed file is unchanged
   after re-analysis — the rubric did not move in this upgrade.
