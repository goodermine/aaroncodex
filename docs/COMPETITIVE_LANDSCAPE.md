# VOX — competitive landscape

Date: 2026-07-28

Prompted by the question "what's the world's best vocal software used by the
world's best vocal coaches and scientists?" — and by extension, what VOX is up
against when it ships.

**Caveat on sourcing.** Some tool details below come from vendor pages and
comparison sites, not independent testing. Treat feature claims as "as marketed"
unless we have used the tool ourselves. Where a competitor's depth is unverified
it is marked. This is a strategic map, not a benchmark.

---

## The one-line answer

There is **no single tool** that voice coaches and scientists all use. The field
splits into two camps that barely overlap, and **nobody occupies the middle** —
which is exactly where VOX sits.

- **Scientific tools** measure deeply and interpret nothing. They are
  microscopes.
- **Coaching apps** interpret lightly and measure almost nothing but pitch. They
  are games with a curriculum.

VOX is the middle: deep measurement **with a verdict on top**, that refuses to
lie about the verdict.

---

## Camp 1 — scientific / professional (coaches, voice scientists)

### VoceVista (Video / Video Pro)
The real answer to "what do serious singing teachers and voice scientists use."
Real-time high-resolution spectrogram, pitch tracking, formant overlays,
singer's-formant and vibrato visualisation, interactive spectral filtering. The
CVT-style spectrogram Aaron shared is this class of tool.

- **Strength:** mature, real-time, trusted, shows everything.
- **Gap vs VOX:** shows everything, **interprets nothing.** No score, no
  diagnosis, no "your weakest phrase is here." It hands the teacher a picture and
  the teacher supplies the judgement.

### Praat (+ Parselmouth)
The academic standard. Free, open-source, scriptable. Jitter, shimmer, HNR,
CPPS, formants, pitch. **VOX is built on this** — the engine calls Praat via
parselmouth for exactly those voice-quality measures.

- **Strength:** the ground truth for phonation science; everyone in research uses
  it or something built on it.
- **Gap vs VOX:** deliberately no interpretation and no calibration. VOX does not
  beat Praat on measurement — it *stands on* Praat and adds the layer Praat
  refuses to add.

### Sonic Visualiser
Layered spectrogram + annotation + analysis plugins for audio research. A
measurement workbench. Same shape as VoceVista/Praat: measures, does not judge.

### Melodyne (DNA — Direct Note Access)
The producer's note-level pitch/timing **editor**, not an assessor. Analysis in
service of correction. Adjacent to VOX's **Polish** deck, not its Analyze deck.

---

## Camp 2 — consumer coaching apps

Almost all the same product underneath: **real-time pitch feedback + graded
exercises.** This is where the market, the money and the user bases are.

| App | Measures | Notes |
|---|---|---|
| **Singing Carrots** | cents-level pitch, stability, per-note cross-session history, LLM chat coach | Closest to VOX's ambition; publishes outcome data; adaptive plans |
| **Yousician (Singing)** | pitch accuracy, timing | Structured curriculum, licensed songs, auto-transpose |
| **SingSharp** | range, tone, resonance, breath detection | Markets breath detection (depth unverified) |
| **Vanido** | exercise performance → difficulty | Clean daily-exercise loop, iOS only |
| **Smule** | pitch guidance + AI effects | Karaoke, not training; correction masks problems |
| **SingTrue / Erol / Singscope / Vocaberry** | pitch, ear training, range | Fundamentals and ear-training slices |

**What none of them measure:** phrase-ending breath sag, register transitions,
singer's formant, H1−H2 adduction, per-note quality degradation, vocal mode.
They live almost entirely on pitch accuracy.

---

## Where VOX is genuinely differentiated

Three things not found together anywhere else, in rough order of how defensible
they are.

### 1. Provenance discipline — believed to be unique
No competitor treats "the number might be wrong" as a first-class problem. VOX
does, because it has been burned: one engine may produce a score, scores refuse
to compare across separators or calibration packs, stale scores are retired
rather than quoted, a number is suppressed rather than emitted degraded, and
preflight fails closed. The last week of this project is entirely this. It is
unglamorous and it is the moat — it is what makes the verdict trustworthy, and it
is the hardest thing for a competitor to bolt on afterwards because it is a
discipline, not a feature.

### 2. A score calibrated against professional reference vocals — rare
"10 = a typical professional," anchored to a pack of real pro takes. VoceVista
will not tell you whether you are good. The apps grade you against an exercise,
not against Whitney Houston. VOX grades against the professional distribution and
reports your percentile against it.

### 3. The whole loop on one system — unique in this combination
Record → deep analysis → polish → ask the knowledge base *why*. Every competitor
does one slice. Nobody does capture + scientific-grade analysis + correction +
coaching knowledge in one place.

Plus the measurement depth itself: the standalone spec (metallic index, noise
gradient, per-note quality slope, H2−F1 passaggio crossings, support slope) is
Camp-1 depth aimed at a Camp-2 audience — with interpretation attached.

---

## Where VOX is behind, and should not pretend otherwise

- **Live spectrogram.** VoceVista's is mature and real-time. VOX's is planned but
  not drawn (see `VISION.md` pillar 4). The measurement exists; the picture does
  not.
- **Product polish and onboarding.** Singing Carrots' chat coach, adaptive plans
  and cross-session UX are ahead of VOX's decks.
- **Users.** The apps have real user bases. VOX has one singer and a handful of
  friends. "Most powerful" is a claim about depth and honesty; "most popular" is
  a different, much harder race VOX has not entered.

---

## The positioning that follows

> **VoceVista's measurement depth, with an actual verdict on top, that refuses to
> lie to you.**

That is a real gap in the market: the scientists' tools do not judge, and the
judges' tools do not measure. "Most powerful voice analysis app on the planet" is
defensible on **depth × honesty of measurement** — not on feature count and not
on popularity. The provenance discipline is the part no competitor is currently
even attempting, so it is the thing to keep sharpest.

### Strategic implications for the roadmap
- The **standalone analyser + spectrogram** is the feature that most directly
  challenges VoceVista on its own turf, with interpretation VoceVista lacks.
- The **KB ask layer** is what pulls ahead of Singing Carrots' chat coach — if it
  cites sources rather than confabulating.
- **Provenance is the moat; guard it.** Every shortcut that emits an
  unaccountable number erodes the one thing nobody else has.

---

## Sources

As-marketed unless noted; not independently benchmarked.

- VoceVista — https://www.vocevista.com/en/
- Vocal Process spectrograph overview — https://vocalprocess.co.uk/download-spectrograph-software/
- James Curtis PhD, *Acoustic Assessments of Voice* (Praat/VoceVista/tools) — https://www.jamescurtisphd.me/tutorials/voice/acoustic-assessments-of-voice
- Singing Carrots, *Top 7 AI Vocal Coaches* — https://singingcarrots.com/blog/top-7-ai-vocal-coaches/
- Celemony Melodyne 5 algorithms — https://helpcenter.celemony.com/M5/doc/melodyneStudio5/en/M5tour_AudioAlgorithms
- richlyai, voice-training app roundup — https://richlyai.com/blog/voice-training-app/
