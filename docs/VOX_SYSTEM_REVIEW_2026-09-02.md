# VOX system review — what it measures, where it stands, and what takes it to the next level

Date: 2026-09-02 · Reviewer: Claude (Fable 5.1 session) · Scope: the whole repo —
`CLAUDE.md`, `VISION.md`, the metrics methodology, every scoring handoff, the
engine (`analyse_song.py`, 4,170 lines), the report builder, the calibration
pack, and the 222-file analysis archive. **No engine code was changed for this
review.** Every number below is either read from committed JSON or is an
emulation computed from the per-note data those JSONs already carry; each
emulation is labelled as one.

Read in this order: §1 (what VOX is), §2 (the verdict), §3.1 (the one finding
that changes how the last fortnight's numbers should be read), then the rest.

---

## 1. What VOX is, and what it can measure today

VOX is a self-enclosed vocal-analysis system. A recording goes in, the voice is
separated from the backing (one pinned model, Mel-Band RoFormer), the isolated
vocal is measured with research-grade acoustics, a deterministic rubric turns
seven of those measurements into a `/10` anchored to fifty professional
recordings, and a rules engine maps the weak measurements to exercises drawn
verbatim from a hash-pinned library. The `/10` is one number produced by exactly
one function (`compute_technical_score`), stamped with the rubric build, the
calibration pack and the separation model that produced it, and refused for
display whenever any of those three differ between two scores.

### 1.1 The seven scored components (rubric v5)

| Component | Weight (share) | Measured from | "10" = pro median |
|---|---|---|---|
| Intonation accuracy | 0.25 (22.7%) | median distance of each sustained note's centre from the nearest semitone, tuning offset removed | 20 cents |
| Voice quality | 0.20 (18.2%) | mean of four Praat sub-scores per sustained note: jitter, shimmer, HNR, CPPS | 0.85% / 9.4% / 13.6 dB / 15.4 dB |
| Pitch stability | 0.15 (13.6%) | median spread of the vibrato-removed contour across each note | 24.25 cents (see §3.1) |
| Vibrato control | 0.15 (13.6%) | best of: vibrato presence/rate/extent, or straight-tone steadiness | presence ≥40%, rate 4.9–6.0 Hz, extent 53–78 cents |
| Dynamics / expression | 0.15 (13.6%) | best of: phrase-level level spread, or effective RMS range (p10–p90) | 21.8 dB / 27.0 dB |
| Phrase control | 0.10 (9.1%) | median phrase length | 3.8 s |
| Breath support | 0.10 (9.1%) | share of phrase endings whose pitch falls in the final 0.5 s | 33.3% |

Two headline numbers come out: **overall** (all seven) and **capture-fair**
(voice quality and dynamics excluded — the two that measure the microphone and
the master as much as the singer). The capture-fair design was validated this
fortnight by a natural experiment: the same Reasons performance captured on two
different microphones scored 5.6 vs 6.4 on voice quality and an identical 7.1
on capture-fair.

### 1.2 Measured but deliberately not scored (diagnostics)

Onset quality (clean / scooped / overshot, with a pro percentile), timing
against the backing track (vocal onsets vs the half-beat grid of the vocal-free
instrumental, tempo cross-checked against the original mix), strain flags,
register map and estimated passaggio, vibrato onset delay, singer's formant,
H1−H2 phonation weight, the H1–H8 harmonic profile, vowel space, range map,
per-note timestamps for every trouble spot, 20-second section maps, and a
sag-versus-the-original-recording comparison. Each carries a stated reliability.
The decision not to score these is documented per metric and is correct: they
are style, capture, or heuristic, and folding them in would punish artistry.

### 1.3 What the engine cannot see, by its own account

Artistry, emotion, interpretation, stagecraft, repertoire choice, and — once
the vocal is separated — whether the room was a pub or a bedroom (the engine's
own capture-risk flag reads "normal" on 132 of Aaron's 134 current-rubric takes,
including every tavern take; the singer's `take_context.capture` tag is what
decides which score leads).

---

## 2. Verdict

**The engine is well built, unusually honest, and close to as good as its
present measurements allow. The next level is not more features. It is
measurement consistency, and one specific inconsistency is live right now.**

What is genuinely strong, and should be protected:

- **Provenance discipline.** One scorer, fingerprinted identity on every score,
  preflight that fails closed, scores withheld rather than invented, refusal to
  compare across rubric builds, calibration packs or separation models. No
  competitor surveyed in `COMPETITIVE_LANDSCAPE.md` attempts this. It is the moat.
- **Calibration to real professionals**, with the pro percentile printed
  beside every component so any score can be audited by hand.
- **Empirical self-scepticism.** The v6 onset component was built, tested
  against fourteen by-ear estimates, and rejected because it did not improve
  agreement. The blind A/B ran, overturned the standing explanation, and the
  retracted reasoning was kept in the record. The song-specific sag diagnosis
  was corrected when it turned out to be a separator artefact. This is the
  behaviour of a system that will keep getting more right.
- **Design decisions that keep the score honest:** capture-fair; the
  take-context tag that groups without ever touching a number; the
  timing scorer's vocal-free grid; the 106-exercise library pinned by hash;
  "no trigger → no drill".

What limits it, ranked by how much it distorts what a singer is told:

| # | Finding | Effect on a singer's numbers | Fix class |
|---|---|---|---|
| 3.1 | Pitch-stability is scored against a pro anchor built on the pre-fix drift measurement | every take analysed since 16 Aug reads pitch-stability ≈0 against a ruler ~2.5× too strict; pre- and post-fix takes are not comparable and `score_conflict()` cannot tell | re-analyse refs + archive, rebuild pack, re-anchor (v6) |
| 3.2 | Pitch is tracked at 10-cent resolution | intonation, the heaviest component, can only take five values; 47% of Aaron's takes sit at 10.0 | finer f0 for note centres, bundled with 3.1 |
| 3.3 | Pitch-stability scores the full-note span (scoop + release included), not the held part | the component measures onsets as much as holding | score the mid-note spread, bundled with 3.1 |
| 3.4 | Breath support counts stylistic fall-offs; the energy criterion in its own docstring is unimplemented; fixed 0.5 s tail | breath is partly a measure of repertoire | energy criterion + proportional tail, bundled with 3.1 |
| 3.5 | Three components carrying half the weight barely discriminate | the overall is effectively decided by four components | weight review inside the v6 validation |
| 3.6 | Confidence is "high" on 99% of takes; capture context is untagged on 74% | which number to lead with depends on metadata that is usually absent | measurable confidence; auto capture detection |
| 3.7 | Archive metadata is unvalidated | two wrong context claims reached PRs this week | archive validator, same-performance test, singer roster |
| 3.8 | Coaching loop gaps | take-vs-previous comparison is done by hand; no longitudinal narrative; the drill Aaron is on has no matching diagnostic | three small tools |
| 3.9 | Knowledge base has content, no retrieval | pillar 6 of the vision is a folder | local BM25 with citations, no server needed |

---

## 3. Findings

### 3.1 The drift fix changed the measurement scale, and the calibration pack was never rebuilt — so pitch-stability is now scored against the wrong ruler

**What happened.** On 16 Aug the engine stopped fabricating a drift of exactly
0.0 cents for any note shorter than the ~0.36 s smoothing window (commit
`e3c5200`). That was the right fix: a real voice cannot hold a note at zero
drift. But the fix was applied "surgically" — the rubric fingerprint did not
move, twelve grossly affected takes were re-analysed, and everything else,
**including all fifty professional references, was left on the old
measurement.** I was part of that decision and it was wrong in scope.

**The evidence, from the committed JSON.**

- All 50 reference analyses in `engine/calibration/references/` predate the
  fix (analysed 28 Jul; none carries the post-fix `drift_measurable_notes`
  field). Across them, **3,229 of 9,688 notes carry a fabricated 0.0 drift** —
  every one of the 3,228 notes shorter than 0.36 s, plus one. One reference
  (Hot Chocolate, *You Sexy Thing*) has a stored median drift of **0.0 cents**,
  which is physically impossible and is the artefact's signature.
- Of the 219 current-rubric analyses in the archive, **209 were analysed
  pre-fix and 10 post-fix.** Every take merged since 22 Aug — To Be With You,
  Pretty Woman, Reasons take 4 (both captures), Cry in Shame, Lose Control,
  KFF take 9, Bow River, Let's Go — is post-fix.
- **Emulation** (recomputing each stored median with the short-note zeros
  excluded, which is exactly what the fixed engine does):

| | Stored (pre-fix) p10 / p50 / p90 | Fixed-engine emulation p10 / p50 / p90 |
|---|---|---|
| 50 pro references, full-note drift | 14.4 / **24.25** / 52.4 cents | 44.5 / **62.5** / 90.1 cents |
| 209 pre-fix archive takes, shift in median | — | +5.5 min / **+39.5 median** / +109.9 max; 190 of 209 move by more than 20 cents |

  Every one of the fifty references moves by more than 5 cents. The pro anchor
  for pitch-stability is therefore roughly **2.5× too strict** for any take
  measured on the fixed engine.

- **The consequence is visible in the last fortnight's reports.** Post-fix
  takes read median drift 59–142 cents against a "10 at 24.25, 0 at 80" scale,
  so pitch-stability came out **exactly 0.0 on six of the eleven** Aaron takes
  merged since 22 Aug and under 1.0 on eight, and the report's PRIMARY FOCUS
  landed on held-note stability every time. Pre-fix takes from the same month read 19–46 cents on the same
  component and scored 6–10. The two eras are on different rulers, and
  `score_conflict()` passes them as comparable because rubric fingerprint,
  calibration fingerprint and separation model are all identical.

**What Aaron's pitch stability actually is, on one ruler.** The engine also
stores a *held* drift per note (the middle 60% of the contour, which excludes
the scoop in and the fall out). Emulating that on notes long enough to measure
it (≥0.6 s) for both sides:

| | Held-note drift, median |
|---|---|
| 50 professional references | 23.7 / **37.5** / 51.2 cents (p10 / p50 / p90) |
| Aaron, 147 takes | 33.4 / **47.9** / 82.5 cents |
| Aaron by month, 2026 | Jun 56.4 → Jul 51.0 → **Aug 45.8** |
| Rilda, 37 takes | 57.3 cents |

Aaron's typical held note wanders about **10 cents more than a typical pro's**,
and the trend across the summer is in the right direction. That is a real,
coachable gap. It is not the "0.0 out of 10" that the last two weeks of
reports printed, and the CT/cry work he is doing is aimed at the right thing —
just at a smaller target than the score implied. (Emulation caveat: the true
post-rebuild numbers will differ slightly; the direction and rough size will
not.)

**Why the existing guards missed it.** The rubric fingerprint hashes only the
scoring functions, by design; the calibration fingerprint hashes the pack; the
separation model is read from the stem filename. None of them encodes *which
measurement code produced the inputs.* A measurement change is invisible to
every provenance check in the repo. This is the same failure class as the
5.1-vs-8.3 incident that created `CLAUDE.md` rule 1, one level down.

**The fix — the single most valuable thing the project can do next.**

1. **Re-analyse all 50 references and all 209 pre-fix takes on the fixed
   engine** from the retained RoFormer stems on Candi's box (no re-separation;
   the identity already records RoFormer on every file). Mechanical and
   batchable overnight.
2. **Rebuild the pack** (`tools/build_calibration.py`), which moves the
   calibration fingerprint, then `rescore_archive_inplace.py` — the exact
   procedure already used when the onset metrics were added.
3. **Re-anchor pitch-stability as rubric v6.** The zero anchor ("0 at 80
   cents") was chosen against the flattered scale; on the fixed scale the
   professional p90 is 90 cents, so the current anchor would zero one pro in
   ten. Score the **held** spread (§3.3), 10 at the new pro median, 0 at a
   zero anchor re-derived from the pack (e.g. the pro p90 plus the same
   margin the old anchor had over the old p90). The straight-tone path of
   vibrato control uses the same 12/80 anchors and moves with it.
4. **Validate v6 the way v6-onset was validated,** against the fourteen
   sighted by-ear estimates and the twelve blind clips — with the stated
   expectation that agreement should *improve*, because drift was the one
   metric that tracked Aaron's blind ear (r = −0.65) and it is the metric
   whose scale is being corrected.
5. **Close the provenance hole:** add a `measurement_fingerprint` (hash of the
   measurement functions, or the engine git commit) to `score_identity()`,
   store it in every analysis, have `score_conflict()` refuse across it, and
   have `score_preflight.py` fail when any archived analysis carries a
   different one. Then a future measurement fix cannot silently split the
   archive into two eras again.

**Interim reading rule until step 2 lands** (costs nothing, applies today):
on any take carrying `drift_measurable_notes`, do not quote the
pitch-stability component or a PRIMARY FOCUS derived from it. Quote the
held-drift median beside the emulated pro band above, and say why.

### 3.2 Pitch is tracked at 10-cent resolution, so the heaviest component can only take five values

`librosa.pyin` is called with its default `resolution` of 0.1 semitone. Every
per-note deviation in the archive is a multiple of 10 cents (24,599 notes
checked; the only exceptions are half-steps introduced when the tuning offset
is subtracted). The per-take median therefore lands on 10, 20, 25 or 30, and
the component — 10 at the pro median, 0 at 45 — becomes a five-step ladder:
10.0 / 9.0 / 8.0 / 7.0 / 6.0. Observed on Aaron's 134 takes: 63 at 10.0, 25 at
8.0, 30 at 6.0, and eleven in between.

The reference pack shows the same quantisation from the other side: its
intonation values are 10, 15, 20 and 25 only, with **p50 = p90 = 20 cents**. The
"typical pro" anchor for the most heavily weighted component sits exactly on
the tracker's step size, which is why 47% of Aaron's takes are indistinguishable
from a professional on it and why intonation has the weakest correlation with
the overall of any component (r = 0.37).

**Fix.** Keep pyin for voicing and segmentation (it is the right tool for
that), but take each note's centre and contour from a continuous estimator —
the Praat pitch track the engine already computes for jitter, or `librosa.yin`
with parabolic interpolation — so deviations resolve to ~1 cent. Raising pyin's
own resolution is not the answer: its HMM cost grows with the square of the bin
count. This is a measurement change, so it belongs in the same re-analysis
pass as §3.1 rather than as a separate event; two era splits are worse than one.

### 3.3 Pitch-stability scores the whole note, not the held part

The scored input is the spread of the smoothed contour across the **entire**
note — scoop in, hold, fall out. The engine separately computes `held_drift`
(middle 60%) precisely so that "onset scoops and release slides don't read as
the held note drifted", then uses it only for the worst-note list. On Aaron's
post-fix takes the full-note median runs 59–142 cents while the held median
runs 34–101; on the references the emulated full-note p50 is 62.5 against a
held p50 of 37.5. Scoring the held spread measures what the name promises and
what the singer is training. Bundle with §3.1.

### 3.4 Breath support is partly a measure of the song

Three separate documents have found this and the code has not caught up:

- `analyse_breath()`'s docstring promises "pitch sags **and energy collapses**";
  the implementation fits a pitch slope and never reads the audio it is passed.
  A supported stylistic fall keeps its energy; air running out does not.
- Flagged sags have median depths of 265–600 cents — two to six semitones.
  Those are releases, not fatigue. Every professional in the pack does them; the
  pack's sag rate spans 12.9% to 81.5% by song.
- The 0.5 s tail is fixed, not proportional; on sub-second phrases it spans the
  whole phrase.

This week's Let's Go pair showed the cost: Aaron consciously held vowels
longer (phrase length 2.23 → 2.57 s) and the sag rate went from 40% to 75%,
because endings that were previously cut short now existed to be measured.
The component fell from 8.75 to 2.56 for doing the thing the coaching asked.

**Fix.** (a) Implement the energy criterion — flag an ending only when pitch
falls *and* RMS collapses relative to the phrase body (the standalone plan's
`support_slope`). (b) Make the tail proportional with a floor. (c) The
reference-relative comparison already exists (`breath_vs_reference`) — print
its delta beside the absolute rate in every report where a reference exists,
since sag-versus-the-original is the number that separates "he ran out of
air" from "this song falls off its endings". (a) and (b) are rubric changes;
bundle with §3.1.

### 3.5 Half the weight sits on components that barely move

Across Aaron's 134 current-rubric takes:

| Component | Mean | SD | r with overall |
|---|---|---|---|
| Intonation (0.25) | 8.49 | 1.63 | 0.37 |
| Vibrato control (0.15) | 9.03 | 0.74 | 0.46 |
| Dynamics (0.15) | 8.82 | 0.90 | 0.25 |
| Pitch stability (0.15) | 5.92 | 3.13 | 0.53 |
| Phrase control (0.10) | 6.94 | 2.80 | 0.44 |
| Breath support (0.10) | 6.48 | 2.28 | 0.28 |
| Voice quality (0.20) | 7.82 | 2.44 | 0.37 |

Intonation, vibrato and dynamics carry 0.55 of 1.10 relative weight and have
the three smallest spreads. Vibrato control is "best of two paths", which makes
it near-maximal for almost everyone; dynamics is graded to floor at 3 rather
than 0 by design. The overall is in practice decided by pitch stability, phrase
control, voice quality and breath — of which one is on the wrong ruler (§3.1),
one is capture-sensitive, and one is partly repertoire (§3.4).

This is not an argument for tinkering: the v6-onset rejection established the
bar, and the rubric matches Aaron's ear at r = 0.78 with no bias. It is an
argument that the v6 pass of §3.1 should include a weight review **as part of
the same validation**, since three of the four discriminating components are
being re-measured anyway. Fixing §3.2 will also restore spread to intonation on
its own.

### 3.6 Confidence does not discriminate, and capture context is usually missing

`confidence` is "high" on 132 of 134 takes because its inputs (Praat present,
≥8 notes, capture risk not elevated) are nearly always satisfied — the capture
risk flag has never fired on a tavern take. Meanwhile `take_context.capture`
is absent on 99 of 134 and `intent` on 95, so the rule "live leads
capture-fair" has nothing to read on three takes in four, and `superseded` /
`learning` grouping depends on a human remembering to tag.

**Fix.** (a) Derive confidence from things that vary: number of drift-measurable
notes, the limitation-3 validity gate (HNR / jitter / implausible stability),
section coverage, separator known, capture tag present. (b) Auto-detect capture
chain from the audio and *propose* the tag for the singer to confirm: the
`engine/standalone/gates.py` framework already exists with synthetic-degradation
tests for exactly this (clipping, SNR, reverb, compression). Future-ideas F2
names the same thing. The two-mic Reasons pair and the TazCam 11 dB vs phone
44 dB observation are ready-made validation fixtures.

### 3.7 Archive metadata is unvalidated, and this week it cost two corrections

- PR #64 declared the H8 recording of To Be With You "the exact same
  performance" as the 22 Aug take and marked it `superseded: true`, on the
  evidence that 77% of aligned frames fell within 50 cents. Two takes of the
  same song by the same singer will always align that well. Aaron confirmed it
  was a different night.
- PR #68 attributed Fireball to Rilda; it was Aaron.
- About twenty archive files do not follow the `<date>-<singer>-<song>-take-NNN`
  convention that `progress_report.py` and `check_take_integrity.py` parse;
  the singer roster is a hard-coded tuple in one tool; a naïve parse of the
  archive yields "singers" called `creep`, `home`, `zone` and `neon`.

**Fix.** A `tools/archive_validate.py` run by the contract test and by
preflight: filename convention, `take_context` schema, provenance identity
present and current, singer in a committed roster file, and — for any
`superseded: true` — a pointer to the evidence. Pair it with a
`tools/same_performance.py` that answers "same recording?" with a criterion
that can actually say no: duration match within a fraction of a second *and*
a near-zero-lag envelope cross-correlation peak (or a DTW path whose median
warp is under ~50 ms). Make its verdict a required line in any PR that claims
a variant capture.

### 3.8 The coaching loop has three cheap gaps

1. **Take-vs-previous.** The Let's Go take-1 vs take-2 table (component deltas,
   20-second drift and sag by section, worst-note lists side by side) was built
   by hand this week. `compare_takes.py` aligns a take to the *original*;
   nothing compares a take to the singer's own previous take of the song. A
   `tools/diff_takes.py a.json b.json` over the stored per-note and per-section
   data is a day's work and would run on every re-take automatically.
2. **Longitudinal narrative.** `progress_report.py` and `score_trends.py` have
   the trajectories; nothing turns them into "since last month, sag on this song
   fell from 60% to 40%; drift unchanged". With 158 Aaron takes across 34+
   dates the per-song learning curves (future-ideas F3/F7) are ready to draw.
3. **A diagnostic that matches the drill Aaron is on.** His CT/cry work targets
   pitch being knocked off as consonants change inside a held phrase — Candi's
   transcription showed the high-drift "notes" are multi-word segments. The
   engine can already split that: measure drift within vowel-stable frames
   (high HNR, voiced) separately from drift at consonant boundaries, and report
   "held-vowel drift" vs "boundary drift" per note. That is the standalone
   plan's `vowel_stability`; it needs no rubric change and it would tell him
   directly whether the anchor is holding through the words.

Also keep the onset numbers as percentiles, not percentages, per the
limitation-5 rule — separation damages the onset region most.

### 3.9 The knowledge base needs a retrieval layer, and it does not need a server

77 documents and ~524,000 words with clean front-matter and a controlled
vocabulary, and no way to ask it anything. A local lexical index (BM25 over
sections, MIT-licensed `rank_bm25`) returning passages with document and
heading citations is a small tool, keeps the "self-enclosed" principle (no
audio or text leaves the machine), and gives the chat layer — Claude or Candi —
something to quote rather than recall. The two constraints in `VISION.md`
(cite the source; the exercise library wins on *what to do*) are enforceable in
that tool's output format.

### 3.10 Smaller notes

- **Timing.** The groove scorer's design is sound (vocal-free grid, mix
  cross-check). Its headline is a mean offset, which hides alternating
  rush/drag: Baby Got Back read −5.3 ms mean with a 62 ms spread. Report the
  median, the spread and a pocket rate (share of onsets within ±25 ms) per
  section.
- **Grid deviation saturates at ±50 cents** and scooping never feeds
  intonation; both are documented limitations with reading rules. The finer
  pitch of §3.2 does not remove the wrap, but a "nearest pitch in the *sung
  melody*" mode using the reference contour (already persisted for
  `compare_takes.py`) would see a note that landed on the wrong semitone.
- **Vibrato onset delay** reads 0.0 s on all fifty references; either the
  detector's half-extent threshold is too easy or the pack is genuinely
  bloom-free. Worth a look before it is ever trusted.
- **Reference pack composition.** 19 female / 31 male, studio only, broad
  style spread — good. It has no rap, funk or patter references, which is why
  short-note material trips edge cases; the take-context `learning` tag and
  the rap timing-first handoff are the right way to handle that until the pack
  grows.
- **Rule 7 is implemented** in `report_builder._primary_focus()` — but its
  capture check keys on the engine's risk flag, which never fires (§3.6), so
  in practice the switch to capture-robust components never happens. Key it on
  `take_context.capture == "live"` as well.

---

## 4. Recommended sequence — nothing here needs a server

| Phase | What | Where it runs | Effort | Retires scores? |
|---|---|---|---|---|
| 0 — today | Interim reading rule for post-fix takes (§3.1). Add `measurement_fingerprint` to `score_identity()` and a preflight check that the archive is on one measurement era. | repo | hours | no |
| 1 — this week | Re-analyse 50 refs + 209 pre-fix takes on the fixed engine from retained stems; rebuild pack; `rescore_archive_inplace.py`; regenerate tables and singer PDFs. | Candi's box | one batch run, then review | calibration fingerprint moves (handled by existing tooling) |
| 2 — next | Rubric v6 in one deliberate step: held-drift scoring with re-derived anchors (§3.1, §3.3), fine-resolution note pitch (§3.2), breath energy criterion + proportional tail (§3.4), weight review (§3.5). One re-analysis, one validation against the 14 by-ear + 12 blind clips, one archive retirement — not four. | repo, then Candi's box | days, plus the validation | yes, once |
| 3 | `archive_validate.py`, `same_performance.py`, singer roster; capture-chain auto-detection from `standalone/gates.py`; measurable confidence. | repo | days | no |
| 4 | `diff_takes.py`; per-song learning-curve report; vowel-vs-boundary drift diagnostic. | repo | days | no |
| 5 | KB retrieval with citations. | repo | days | no |

The order matters. Phase 1 is prerequisite to everything that quotes
pitch-stability, and Phase 2 must be one event because every rubric change
retires every score — the project has already paid that cost twice and should
pay it once more, deliberately, with the validation set that now exists.

---

## 5. What this review did not do

- It changed no engine code and re-ran no audio. All fixed-engine figures in
  §3.1 are emulations from the per-note data stored in the committed JSON
  (drop notes shorter than 0.36 s whose stored drift is exactly 0.0; for held
  drift, keep notes ≥0.6 s). They reproduce the fixed engine's rule exactly
  for the median but not any second-order effect of re-running pyin.
- It did not check retained-stem coverage on Candi's box. Phase 1 assumes the
  RoFormer stems exist for the 209 pre-fix takes and the 50 references; any
  without a stem must be re-separated with the pinned model.
- It could not run the test suites here (no numpy in this container); the 84
  engine tests, 19 tool tests and 36 suite tests were green at the last
  session that ran them.

## 6. Reproducing the numbers

All statistics above come from `voxanalysis/archive/scratch-analyses/*.json`
and `engine/calibration/references/*.json` with the standard library only.
The emulation rule: for each `intonation.notes[]` entry, exclude it from the
drift median when `duration_s < 0.36 and drift_cents == 0.0`; for held drift,
take the median of `held_drift_cents` over notes with `duration_s >= 0.6`.
Component statistics use current-rubric (`7cbd02df8f62`), non-retired,
non-superseded Aaron takes (n = 134).
