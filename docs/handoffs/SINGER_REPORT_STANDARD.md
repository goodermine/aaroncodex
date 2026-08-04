# The Singer Report standard — "The No-Fluff Report"

The house format for a singer's full vocal-profile PDF. First produced for
Aaron and Rilda on 1 Aug 2026; from now on **every singer report follows this
standard**. The point of the format: hard, fully-analysed numbers a coach can
trust, AND a document the singer can actually read end-to-end without a
translator.

## Identity

- Title block: `VOX//SUITE · THE NO-FLUFF REPORT` → singer's name (large) →
  subtitle **"Measured. Not Flattered."**
- Opening paragraph states the deal in one breath: measured by a machine with
  no opinion, N takes, date span, rubric + build fingerprint, 50 pro
  references, **10 = a typical professional, not perfection**.
- Footer on every page: `NAME — THE NO-FLUFF REPORT · deterministic rubric v5
  · calibrated to 50 professional references · 10 = a typical pro`.

## The two non-negotiable reader features (the "norm")

1. **"In plain words" boxes** — a tinted callout after every section (and on
   the cover) translating that section's numbers into everyday language with
   analogies (parked-car-rolling for drift, home-streets for tessitura,
   gear-change for passaggio, trailing-sentence for sag). No term is used
   before or without its translation. Written TO the singer ("you"), warm but
   never softening the numbers.
2. **Appendix: The Word-Guide** — a plain-English glossary of every term in
   the report (cent, median, tessitura, passaggio, chest/head, vibrato
   rate/extent, sag, scoop, jitter/shimmer/HNR/CPPS, overall vs room-fair,
   the 10-anchor), personalised where possible ("yours is centred on F4").

## Section order

1. **Cover** — stat tiles (PB, average, songs, takes / range, tessitura,
   passaggio, signature stat) + "Who this singer is, in one paragraph" +
   its translation box.
2. **Range & Tessitura** — reliable working range (per-take robust modes),
   tessitura (central ~70% of time-weighted sung seconds), heart of the voice
   (most-sung notes), extremes (labelled display-territory). Time-weighted
   seconds-per-note chart with the transition band shaded.
3. **The Passaggio** — per-take estimate clusters, trouble-note chart, and the
   tessitura-vs-passaggio finding if present.
4. **Measured Strengths** — what is already pro-level; protect, don't rebuild.
5. **Growth Edges** — each gap with current median, pro median, and the drill;
   never more than ~4 gaps; name the underlying family if there is one.
6. **Score History** — trend chart, top-ten table, averages, and the 2–3
   stories the numbers tell.
7. *(optional)* **Reference benchmark** — original-artist comparison, raw
   measures only unless single-pack comparable (rule 3).
8. **What Demonstrably Works** — evidence-backed rituals for THIS singer.
9. **The Next Level — and the practice that is not optional** — the honest
   sentence ("on the current pattern you stay the singer you are now"), then
   a distinctly-coloured drill table: minutes, drill, how, and WHICH measured
   number it moves. End with the two-way door: "If the minutes happen, the
   next report reads differently. If they don't, it won't."
10. *(optional)* Campaign/competition section, if one is live.
11. Appendices: Word-Guide → best-take-per-song → Methodology & Provenance.

## Colour

- Base layout identical for everyone; **accent colour is the singer's** —
  Aaron blue (#1d4ed8 family), Rilda red (#b91c1c family). One accent family
  plus neutrals; the drill table gets a second, deeper accent so it reads as
  the serious table. Charts re-rendered in the same accent (single-series,
  validated for contrast on white).

## Honesty rules (inherited from CLAUDE.md, restated for reports)

- Every score from the one engine; identity/provenance printed; no
  self-computed or rounded-kindly numbers ("No number in this document was
  rounded toward the flattering side" appears in the methodology appendix).
- Live takes lead room-fair; clean captures lead overall — stated where used.
- Aggregate medians include practice/live takes and are LABELLED as harsher
  than performance bests.
- Capture artefacts (bleed, vintage masters, two-voice duets, style-slide
  songs) are flagged as capture/style, never scored as voice; held-out takes
  are named as held out and why.
- Small archives: say so on the cover ("early reads, not verdicts").

## Mechanics

- Data mined from `voxanalysis/archive/scratch-analyses/*_analysis.json`
  (respecting take_context: superseded excluded from rankings, learning kept
  off leaderboards, reference takes excluded from singer stats).
- Charts: matplotlib, single accent hue, thin marks, no gridlines, direct
  annotations; skill-trend panels restricted to the consistent-pipeline era.
- PDF: ReportLab (Letter) with DejaVu fonts (required for ♯/♭/¢ glyphs);
  render every page to images and EYEBALL before delivery (orphans, overflow).
- Regenerate a singer's report after major archive changes (new era of takes,
  rubric change, competition milestones) — same file, updated numbers.
