# VOX Cloud Alpha — System Overview

*What has been built, how good it is, what it is for, and every metric it produces.*

This is the technical/product reference. A plain-language companion for
singers is in `docs/USER_MANUAL.md`.

---

## 1. What this is

VOX Cloud Alpha (engine name **VOXAI**, coach persona **Candi**) is a
singing-analysis and coaching system. It takes a vocal recording, isolates
the voice, measures it with research-grade acoustics, scores it against a
pack of professional recordings, locates problems by timestamp, prescribes
exercises from a curated library, and renders the whole thing as visuals
and a coaching report.

**The founding principle, and the thing that makes it trustworthy:**

> Every number the system shows is a real measurement or a documented
> formula over real measurements. Nothing numeric is generated, guessed,
> or adjusted by a language model.

The one place a language model is used is the coach layer (Candi), which
turns the measured numbers into warm, readable coaching prose — and is
contractually forbidden (via a scoring policy) from inventing, rescaling,
or "rounding up" any number. The score you read is the score the math
produced.

---

## 2. How it was built (and why you can trust it)

The system began as a tool that **invented** its headline scores at the
language-model layer and computed several "clinical" metrics in ways that
made their professional comparisons invalid. Every one of those problems
was found and fixed. The rebuild followed one discipline throughout:

- **Measure, don't guess.** Replaced approximate/mislabelled metrics with
  the actual algorithms voice scientists use (Praat, via parselmouth).
- **Gate every metric to where it's valid.** Voice-quality metrics are
  measured only on sustained sung notes — never across pauses, consonants,
  or note changes — because a melody moving between pitches is musicianship,
  not instability.
- **Adversarial validation.** Every feature shipped only after ground-truth
  tests. Several first implementations *failed their own validation* and
  were fixed before merging: a vibrato detector that measured note-change
  rate, a register detector that forced a fake 50/50 split, an onset
  detector that counted slides as errors, a prescription parser that
  invented a phantom exercise. Catching these is the point — the standard
  is that a wrong-but-plausible number never ships.
- **Label reliability honestly.** Every module reports its method and, where
  relevant, a reliability level. A fallback approximation is never presented
  as a clinical measurement.

**Validation evidence (representative):**
- Synthesised a clean in-tune voice and a deliberately flawed voice; the
  scorer separated them correctly (≈8.5–9.4 vs ≈4–5.5) with per-metric
  values matching the synthesis parameters.
- The professional reference pack scores ~9.0 median against its own
  calibration; the flawed synthetic control scores ~5.5 — a wide, honest gap.
- Score determinism verified: the same audio always produces the same score.
- Every visual verified by rendering and inspection; the harmonic/onset/
  register modules re-validated after their bugs were fixed.

---

## 3. What it is for (uses)

- **Self-coaching for singers.** Record a take, get a measured score, a
  ranked list of what to work on, timestamped trouble spots, and a
  prescribed drill — then track improvement take over take.
- **Take-vs-original comparison.** Measure your performance against the
  actual studio recording of the same song (melody, timing, key), fairly.
- **Teaching.** A voice teacher gets objective, non-confrontational evidence
  (VoceVista/Sing&See-style visuals) plus automated diagnosis, pre-navigated
  to the moments that matter.
- **Progress tracking.** A per-singer, per-song ledger of every metric's
  trajectory across sessions.
- **Multi-singer studios.** The same pipeline serves any singer; the
  professional pack is the shared yardstick.

---

## 4. Architecture (one paragraph)

A recording enters, is separated into isolated-vocal and instrumental stems
(UVR/MDX), and the vocal is analysed by the engine (`analyse_song.py`) into
a structured JSON of measurements. A deterministic rubric turns measurements
into a 0–10 score, calibrated against a pack of professional reference
analyses. A prescription engine maps measured problems to exercises
extracted verbatim from the knowledge library. Visuals and a per-note CSV
are rendered. The coach layer (Candi) reads the JSON and writes the
singer-facing report, bound by a policy that forbids altering any number.
Two delivery surfaces exist: a Telegram/local flow, and a web app (upload →
interactive pitch scope → report).

---

## 5. The scores

### Overall technical score (/10)
A weighted average of six measured components. With the professional pack
loaded, **10 = the median of the professional pack** — matching a typical
pro on a given component is the top of the scale. Weak performances still
score low (the zero-anchors stay fixed). Every component reports its input
value, its formula, and the singer's **percentile vs the pack** ("matches
or beats X% of N pro references"), so any score is auditable by hand.

| Component | Weight | Measures |
|---|---|---|
| Intonation accuracy | 25% | How centred sustained notes are on the pitch grid |
| Pitch stability | 15% | How steady a note stays once landed (drift) |
| Voice quality | 20% | Jitter + shimmer + HNR (fold-vibration cleanliness) |
| Vibrato control | 15% | Vibrato quality **or** deliberate straight-tone steadiness |
| Dynamics/expression | 15% | Loud-soft range and phrase-level shaping |
| Phrase control | 10% | Breath/phrase length |

A **confidence** level (high/medium/low) accompanies every score, reflecting
whether clinical metrics were available, how many sustained notes were
found, and whether capture-risk markers were raised.

### Capture-fair score (/10)
The same rubric with the voice-quality component removed. Jitter/shimmer/HNR
partly measure the **recording chain**, not the singer — a vintage master
run through stem separation reads 2–3× rougher than a clean modern capture
of an equal voice. **Rule:** for any comparison to an original recording, or
across eras, compare capture-fair scores on both sides. Never call a singer
"better than the original" from the overall score.

### What the score deliberately excludes
Artistry, emotion, lyric interpretation, and style-appropriateness are human
judgements and are **not** scored. Any "listener impact" impression is
labelled subjective and never expressed as a measured number.

---

## 6. The metrics (complete catalogue)

All voice-quality metrics are measured **per sustained note** (Praat
algorithms) and aggregated with the median, unless noted.

### Pitch & intonation
| Metric | What it measures | Reference |
|---|---|---|
| Median grid deviation (cents) | How far the typical held note lands from note-centre (tuning offset removed) | ≤10 pro, ≤5 exceptional |
| Intra-note drift (cents) | Wander within a held note (vibrato excluded) | Lower = steadier breath support |
| % within 10 / 25 cents | Share of notes landing close to centre | Higher = more accurate |
| Robust pitch range | Comfortable range, immune to tracker octave errors | — |

### Voice quality (Praat)
| Metric | Plain meaning | Reference |
|---|---|---|
| Jitter % | Cycle-to-cycle pitch micro-instability | ≤0.5 very stable (sung) |
| Shimmer % | Cycle-to-cycle loudness micro-instability | lower = smoother |
| HNR (dB) | Clear tone vs breath-noise ratio | ≥15 clean singing |
| CPPS (dB) | Modern research-standard clarity measure | ~8–14 typical sung |
| Strain flags | High + loud + clarity-collapse notes, timestamped | heuristic; grit trips it |

### Vibrato
| Metric | Plain meaning | Pro reference |
|---|---|---|
| Presence % | Share of long notes carrying vibrato | style-dependent |
| Rate (Hz) | Wobbles per second | 5–7 Hz |
| Extent (cents) | Width of the wobble | ~25–130 |
| Onset delay (s) | Straight-then-bloom timing | ~0.2–0.6 |

### Onsets, registers, breath, groove, range
| Metric | Plain meaning |
|---|---|
| Onset quality | Each note entered clean / scooped / overshot (style-neutral, timestamped) |
| Register map | Chest vs head balance, estimated passaggio, transitions (heuristic) |
| Breath / phrase-end sag | Pitch dying in the final 0.5 s (air running out) — timestamped |
| Phrase length | Breath-management proxy |
| Groove/timing | Vocal onsets vs the backing beat, ms early (rush) / late (drag), per section |
| Range map | Time-weighted seconds-per-note; comfortable core; extremes |

### Tone / resonance (VoceVista/Sing&See vocabulary)
| Metric | Plain meaning |
|---|---|
| Singer's formant ratio (dB) | 2–4 kHz "ring"/projection band vs the body of the voice |
| Harmonic profile H1–H8 | Overtone strengths (numeric overtone sliders) |
| H1−H2 (dB) | Phonation "weight": flutey ↔ balanced ↔ pressed |
| Vowel space (F1/F2) | Each held note mapped to its nearest cardinal vowel |

### Time-localised detail
Every sustained note is stored with timestamp, note name, deviation, and
drift. Worst-offender lists and a 20-second section map answer *where* in
the song the problems live — not just how big they are on average.

---

## 7. The prescription engine

Measured problems map to exercise categories drawn **verbatim** from the
Scientific Exercise Library (106 exercises). It is rules over measurements —
no language model chooses the drill. Each prescription carries its trigger,
the measured evidence, and a severity (the singer's percentile below the
pro pack). Guards enforce the product's values:
- **Style is never corrected**: deliberate straight tone, scooping, and
  back-phrasing don't trigger drills.
- **Capture-aware**: voice-quality-driven triggers are suppressed when the
  recording may be introducing artifacts.
- **Safety-first**: strain outranks other triggers and steers to gentle
  (SOVT) work, never belting.
- **Honesty**: a measured problem with no matching exercise is reported as
  "no library coverage" rather than force-fitted.
- **No trigger → no drill.** Exercises are prescriptions, not rewards.

The library is hash-pinned: if it's edited without rebuilding the map, the
engine warns rather than prescribing from stale content.

---

## 8. The visuals

Every analysis renders:
- **A 7-panel diagnostic plot**: section-health traffic-light ribbon;
  waveform; pitch contour on a note-named axis with the comfortable-range
  band; energy; vibrato rate/extent timeline vs the pro band; F1/F2 vowel
  chart; and a spectrogram with the fundamental + harmonic traces and the
  singer's-formant band marked.
- **Note inspection cards**: close-up spectra of the flagged notes with an
  H1–H8 table — auto-parked on the moments a teacher would hunt for by hand.
- **A per-note CSV** for spreadsheet users.

A web app adds an interactive pitch scope (zoom/seek/playback, original A/B
overlay). A live harmonic-overlay upgrade to that scope is specified and
handed off for build.

---

## 9. Companion tools
- **Melody-match** (`compare_takes.py`): aligns your take to the original,
  removes your key change, and reports section-by-section whether you're
  sharp/flat of the melody and ahead/behind the timing.
- **Progress ledger** (`progress_report.py`): per-singer/song metric
  trajectories across all takes.
- **Calibration builder** / **prescription-map builder**: regenerate the
  professional anchors and the drill map from source.

---

## 10. Quality summary & honest limits

**Strengths:** research-grade measurement; deterministic, auditable scores
anchored to real professionals; capture-fair honesty; time-localised
diagnosis; verbatim-from-library prescriptions; industry-standard visuals,
pre-navigated to what matters.

**Known limits (all documented in `metrics-methodology.md`):**
- Stem-separation artifacts degrade all downstream metrics on messy
  captures; a capture-risk flag lowers confidence accordingly.
- Intonation vs the 12-tone grid penalises deliberate microtonal styling.
- Register, strain, and vowel mapping are labelled medium-reliability
  heuristics — verify by ear at the timestamps.
- The score measures technical execution only — not artistry.
- Rubric v3 (folding the newer metrics into the score) is pending a
  re-analysis of the reference pack on the current engine.

---

*VOXAI — every number measured, every word composed. Transformation over
validation.*
