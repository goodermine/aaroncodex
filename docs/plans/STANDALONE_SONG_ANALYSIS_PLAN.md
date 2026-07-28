# Plan — VOX Standalone Song Analysis

Date: 2026-07-28 · Spec: *VOX — Standalone Song Analysis: Metric Specification*

A second analysis path: **one audio file, one vocal, no reference of any kind.**
No professional pack, no take comparison, no `/10`, no coaching, no
prescriptions. It emits measurements, each carrying its own confidence, plus an
ordered diagnostic reading — and nothing else.

It is deliberately **not** the scored engine. `CLAUDE.md` rule 1 permits only
`compute_technical_score()` to produce a `/10`; this produces none, and the
thing to guard hardest is that it never quietly grows one.

---

## 1. Evidence that the hard part works

Before committing to build, the riskiest single assumption — that a within-file
spectral index separates vocal modes at all — was tested against the five CVT
app demonstrations Aaron recorded (Neutral, Neutral with audible air, Curbing,
Overdrive, Edge; same exercise, same pitches, same phone, minutes apart).

| mode | metallic index | noise gradient | H1−H2 |
|---|--:|--:|--:|
| Neutral | −1.41 | −2.75 | +22.05 dB |
| Neutral + audible air | −0.65 | −3.32 | +23.14 dB |
| Curbing | 0.23 | 2.65 | +4.45 dB |
| Overdrive | 0.46 | −0.68 | −14.39 dB |
| Edge | 1.38 | 4.11 | −9.57 dB |

Three things follow.

**The index orders all five correctly and monotonically**, from a formula never
tuned to them. Non-metallic → half-metallic → full metallic, as CVT describes.

**It reproduces the documented hard case.** Curbing→Overdrive is **0.23** against
~0.9 for both neighbouring gaps. The pair the literature says confuse each other
(~0.74 F1 apiece) are the pair this index cannot separate. That the failure lands
exactly where it was predicted is the strongest evidence the rest is real.

**H1−H2 spans 36 dB across modes**, against a 3.6 dB within-session noise floor
measured on Aaron's own repeated takes. An earlier caution in this project —
that H1−H2 was too noisy to carry the index — was wrong by an order of
magnitude. It is the cleanest single discriminator available.

**One anomaly, and it shapes the architecture.** *Neutral with audible air* scores
the **lowest** noise gradient of all five, below plain Neutral, with the highest
HNR in the set. Backwards from its own label — because these are medians over
loud voiced frames and "audible air" is an *onset* phenomenon. The file-level
statistic is blind to the thing the file is named after. Note- and onset-level
measurement is not a refinement over song-level aggregates here; it is the
difference between measuring the phenomenon and missing it entirely.

**Limits of this evidence:** one file per mode, the CVT demonstrator rather than
Aaron, 78 kbps AAC with nothing above 10 kHz, and z-scores computed across five
files — acceptable only because the capture chain is provably identical. It
establishes that the construction works. It establishes no threshold, and no
within-mode spread.

---

## 2. What exists and what does not

**Already in the engine:** spectral suite (centroid, bandwidth, flatness,
contrast, rolloff), F1–F3, H1–H8 and H1−H2, HNR/CPPS/jitter/shimmer, note
segmentation, onset types and scoop depth, per-note vibrato, phrase
segmentation, phrase-end sag, registers and passaggio, range map, strain flags,
groove. Hop is 512 @ 44.1 kHz = 11.6 ms, near the spec's 10 ms.

**To build:**

- the entire validity gate (§0) — none of it exists
- `alpha_ratio`, `sfr_2_4k`, `energy_above_2300`
- `H2_minus_F1` and the per-vowel crossing analysis
- `quality_slope_within_note` — CPPS/HNR regression across a note's own duration
- `intra_note_drift_shape`, `offset_type`, `vowel_stability`
- `support_slope` — RMS **and** CPPS across the phrase
- metallic index, noise gradient, fatigue slope, bimodality statistic
- frame-level time-series export (the contour is currently *stripped* on archive)
- per-metric confidence, and the diagnostic layer

`support_slope` is the energy criterion `analyse_breath()` promises in its
docstring and has never implemented. Building it here gives the discriminator in
a path where it retires no scores; porting it into the rubric stays a separate,
deliberate decision.

---

## 3. Architecture

Physically separate and obviously non-scoring:

```
voxanalysis/vox-analysis/engine/standalone/
    gates.py        validity gates, each returning (passed, severity, evidence)
    frames.py       frame-level series + per-frame confidence
    notes.py        note-level metrics on the existing segmentation
    phrases.py      phrase-level metrics
    indices.py      metallic, noise gradient, fatigue
    diagnose.py     ordered candidates
    report.py       assembly + suppression
analyse_standalone.py     CLI entry, imports the shared measurement primitives
```

It imports measurement code from `analyse_song.py`; it must never import
`compute_technical_score`, and a test will assert that.

**Output:** summary JSON as the spec's §7 schema, plus frame series to a
**separate sidecar** (`<name>_frames.npz`). A 4-minute song is ~24,000 frames ×
~20 fields; inlining that makes the summary unreadable and unstorable, and the
existing archive strips contours for exactly this reason.

---

## 4. Build order

Each phase ends with something verifiable on real audio.

1. **Gates + suppression harness.** Nothing else is trustworthy first. Ends with:
   run over a known-clean take and a deliberately-degraded copy, gates fire
   correctly on the degraded one.
2. **Frame layer + sidecar.** `alpha_ratio`, `sfr_2_4k`, `energy_above_2300`,
   `H2_minus_F1`, per-frame confidence.
3. **Note layer.** `quality_slope_within_note` first — the spec calls it the most
   diagnostic note-level metric, and the Captain Cook take carries 209 sustained
   notes, so the >600 ms subset should be well populated.
4. **Phrase layer.** `support_slope`, `dynamic_shape`, sag as a proportion.
5. **Indices.** Metallic, noise gradient, fatigue. Validated against the five CVT
   files as a regression fixture.
6. **Diagnostic layer.** Last, and gated on everything above (see §5.3).

---

## 5. Audit — the three ways this fails miserably

Written before building, from failures this project has already had.

### 5.1 The gates cannot be validated, so suppression becomes theatre

§0 is the spine: "suppress the affected metrics rather than emitting them with a
caveat", because "a number that survives into a report gets believed regardless
of what the footnote says". Correct — and this repo has proved it. The engine has
shipped `reliability: "medium — verify by ear"` for months on register and vowel
metrics. Nobody has ever verified by ear.

But the gates are heuristics with **no ground truth**. Suspected compression,
suspected pitch correction, suspected EQ, RT60 proxy, separation artefact level —
each is a detector nobody can check. Two outcomes, both fatal:

- **Too sensitive:** everything is suppressed, the tool emits an empty report, and
  it gets switched off or the thresholds get quietly relaxed until it passes.
- **Too lax:** nothing is ever suppressed, the rule is decoration, and degraded
  numbers flow through with the extra authority of having "passed validation".

There is no way to tell which one is happening by looking at the output. That is
what makes it the worst of the three.

**Mitigation — build ground truth synthetically.** Every gate ships with a test
that takes a known-clean take and produces a deliberately degraded copy:

| gate | synthetic degradation |
|---|---|
| Clipping | normalise to +6 dB and hard-clip |
| SNR | mix in pink noise at known SNRs |
| Reverb | convolve with an impulse response of known RT60 |
| Compression | apply a known ratio/threshold, measure crest-factor change |
| Pitch correction | quantise f0 to the grid, resynthesise |
| EQ | apply a known shelf |
| Separation artefact | compare stem against mix-minus-instrumental residual |

Each gate must fire on the degraded copy and stay silent on the clean one, at a
stated margin. **A gate without a passing synthetic test ships disabled**, and the
report says which gates were not run rather than implying a clean bill.

**Go/no-go:** if fewer than two thirds of gates can be made to pass their
synthetic test, stop and reduce scope — a partial gate layer is worse than none,
because it looks complete.

### 5.2 Within-file z-scoring is blind to the uniform case, and amplifies noise

The design premise is that within-file relative structure carries the
interpretation. It is right about mic/room/EQ — and today's separator incident
proved it in the most expensive possible way. But it has two failure modes that
the spec does not address.

**It cannot see a uniform fault.** Z-scoring forces the mean to zero. A singer
pressing on *every* note produces a metallic index centred on zero with small
spread — indistinguishable from a singer never pressing. The worst note reads as
average because everything is equally bad. For a tool whose purpose is "all the
bad bits", the systematically-bad case is the one it structurally cannot report.

**It amplifies noise when the file is genuinely uniform.** z = (x − μ)/σ. When σ
is at the measurement noise floor, the z-scores are large and meaningless.
Measured on this project's own data: five Pressure Down takes from one sitting
held CPPS to a **0.26 dB** spread. Z-score within that and pure measurement noise
becomes ±2σ "structure", which the diagnostic layer will then interpret.

**Mitigation.**

- Emit **raw alongside z-scored**, always — the spec asks for this; it must not be
  dropped under output-size pressure, because the raw value is the only thing
  that can say "high" rather than "higher than the rest of this file".
- Emit a **dispersion statistic per z-scored metric**, and when within-file spread
  is below a stated floor, **suppress the z-scores and say the file is uniform on
  this measure**. Uniformity is a finding, not an absence of one.
- Establish the noise floor empirically per metric from repeated takes of the same
  performance, not by assumption. The 0.26 dB CPPS / 3.6 dB H1−H2 figures already
  measured are the start of that table.
- The diagnostic layer must never run on z-scores alone.

**Go/no-go:** synthesise a uniformly-pressed file by concatenating five copies of
one strained phrase. The tool must report "uniform, no internal contrast"
rather than a flat profile that reads as healthy.

### 5.3 The single principal candidate will be confidently, plausibly wrong

§6 requires exactly one `principal_candidate` — "the single most upstream finding
that would explain the others" — and warns that a list of seven findings is a
failure of diagnosis. The instinct is right. The risk is that it is the highest
consequence component in the whole design.

**This project has already made exactly this error, twice, this week.** A
song-specific breath diagnosis was published with a confident causal reading; it
was substantially a separator artefact, and the correction had to withdraw the
headline. Before that, Kryptonite was named as the worst song on a two-take
sample; on consistent data it is dead average. Both were single, confident,
upstream-looking conclusions drawn from real measurements. Both were wrong.

A single principal candidate is **maximally believable and maximally
wrong-able**, and this tool has no reference and no second opinion to catch it.

**Mitigation.**

- The principal candidate must **name the evidence and the runner-up it beat**,
  with the margin. A verdict without a stated alternative is not a diagnosis.
- **Suppress it entirely when the top two candidates fall within a stated
  margin.** "Two candidates, indistinguishable on this recording" is a correct and
  useful output. Forcing a winner from a coin-flip is how the sag diagnosis
  happened.
- **Refuse to emit it when any gate affecting its inputs has failed**, even at
  reduced confidence.
- It names a **measurement pattern**, never a cause, and never a person-level
  trait. "Phrase-ending pitch falls cluster in the upper third of the range" is
  admissible; "breath support is the limiting factor" is not.
- No numeric diagnostic confidence. A `0.82` will be read as a score, and rule 1
  exists because this repo produces wrong numbers when two things can emit one.

**Go/no-go:** run it over ten takes and hand the principal candidates to Aaron
blind. If they do not survive his ear, the layer ships **off** and the tool emits
the ordered candidate list without electing a winner.

---

## 6. Decisions still needed

Assumptions made where an answer is missing — all reversible, all flagged:

1. **Location** — assumed a separate `standalone/` package and CLI, not a flag on
   the scoring engine.
2. **Frame output** — assumed sidecar `.npz`, summary JSON stays readable.
3. **Separation gate** — assumed *hard*: without separation, spectral metrics are
   suppressed and the tool runs the non-spectral subset rather than refusing
   outright.
4. **Audience** — assumed any single vocal file, not only Aaron's catalogue.
5. **Priority** — assumed parallel to the RoFormer migration, and **behind**
   verifying that migration's re-score when it lands.

---

## 7. Out of scope, restated because it will be tempting

No mode label from a single sample. No absolute cross-recording spectral
thresholds. Onset type never feeds a mode classifier. No formant term in the
Overdrive/Edge discrimination. No density or contact quotient. No artistry, no
emotion, no style. Nothing medical. And no `/10`, ever.
