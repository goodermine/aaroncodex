# Vocal Knowledge Base

A structured reference library on singing, vocal technique and vocal pedagogy.
Researched, synthesised and written by **Aaron Ellis** (artist name: Rustwood).

**78 documents · ~528,000 words** of knowledge, across seven categories.

**Licence: all rights reserved.** See `LICENSE`.

---

## Structure

| Folder | Contents | Docs |
|---|---|---|
| `01-vocal-science-technique/` | Core technique and vocal science — pedagogy, bel canto, breath, health, diction | 20 |
| `02-course-book/` | Three long-form works: one training course, two complete books. See folder README | 18 |
| `03-technique-deep-dives/` | Single-topic studies — registers, belting, vibrato, agility, passaggio, practice design | 13 |
| `04-artist-analyses/` | Technique breakdowns of specific vocalists | 7 |
| `05-song-guides/` | Song-by-song sing-through guides and song selection | 7 |
| `06-voxai-system/` | The VOXAI coaching system, plus Aaron's current vocal blueprint | 8 |
| `07-reference/` | Glossary, ear training, tone/resonance reference | 5 |
| `sources/` | Reference lists extracted from the research documents — audit trail only | 21 |
| `archive/` | Superseded documents, retained not deleted | 2 |

---

## Start here

- **Want something to train from this week?** `02-course-book/four-machine-course/` — the
  most directly practical material in the library. Four weeks, one system per week.
- **Diagnosing a specific problem?** The diagnostic table in the Four-Machine Course maps a
  failing note to the machine causing it. Then `03-technique-deep-dives/` by symptom.
- **Current coaching state?** `06-voxai-system/aaron-vocal-blueprint-v2.md` — active target
  is phrase-ending airflow stamina.
- **Reading front-to-back?** `02-course-book/singing-fundamentals-compiled/` is the fullest
  single work at 21 chapters.
- **Looking up a term?** `07-reference/vocal-training-glossary-terminology.md`.

---

## Provenance

These documents are Aaron's own synthesis, built during a period of intensive
self-directed study using AI research tools (ChatGPT, Gemini Deep Research, Grok) and
then written up. The reference lists those tools produced have been moved out of the
document bodies into `sources/` — they were the audit trail for the research, not part
of the written knowledge.

Nothing was deleted in that move. Every extracted list names the document it came from.

---

## Notes on the build

**Deduplication.** `Document Your Singing Journey` was a 215,000-word compilation that
reproduced sixteen other documents in this library verbatim, plus three more in part, and
repeated 263 of its own paragraphs internally. Moved to `archive/`; the individual
documents are now the single source of truth.

**Source extraction.** 21 documents carried `Works cited` blocks totalling ~16,000 words
of raw URLs. Split cleanly at the heading into `sources/`. Verified afterwards: every
document body ends on real prose, and no URLs remain in any body text.

**The two books are separate works.** Verified paragraph-by-paragraph: zero shared text
between the 21-chapter compiled book and the 15-chapter chapter series. They use
different chapter numbering for overlapping topics. See `02-course-book/README.md`.

**Chapter order.** The compiled book's Chapters 10 and 11 originally sat ahead of
Chapters 5–9. Moved into sequence; the file now runs 1→21, with line count verified
unchanged before and after.

**Versioning.** `aaron-vocal-blueprint-v2` supersedes v1. v1 is in `archive/`, not deleted.

**Second book completed and identified.** The eleven loose chapter files turned out to be
part of a titled work — *Unlock Your Voice: Yes, You Can Become a Better Singer in Six
Months*. The four missing chapters (5, 10, 13, 14) were located and added, so the book is
now complete at 15 chapters. The folder has been renamed from `chapter-series/` to
`unlock-your-voice/` to reflect the actual title.

**Heading hierarchy normalised.** In the compiled encyclopedia, chapter headings had been
applied at `##`, `###` and `####` depth at random while body content sat at a uniform depth
throughout. All 21 chapters now sit at `###`, with parts and sections above and body content
nested beneath. 754 headings relevelled; word count and line count verified unchanged.

**Table of contents removed.** The compiled book opened with 1,561 lines of dead `(#)` links
carrying Word page numbers — 21% of the file. Stripped after validating that the removed
region contained nothing but TOC links and duplicate title lines. All 21 chapter headings
verified intact afterwards; the book now opens straight into the Introduction.

---

## Known gaps

None outstanding. Both previously-recorded gaps are closed — see *Notes on the build*.

---

## Training readiness

Complete. The corpus is prepared:

- **Every document carries YAML front matter** — title, category, topics, word count,
  author, status. All 96 documents parse as valid YAML. Schema in `TOPICS.md`.
- **Topics come from a controlled vocabulary** of 38 tags, assigned by distinctiveness
  rather than raw word frequency — a document is tagged `breath-support` because it is
  about breath, not because it mentions breathing. Maximum six tags each.
- **Exclusions are machine-readable.** The 23 documents in `sources/` and `archive/`
  carry `exclude_from_training: true`. Filter on that key alone.
- **Bodies are clean prose.** No reference lists, no dead links, no URLs, no
  table-of-contents cruft anywhere in the knowledge base.

Filter to `status: active` and you have 73 documents, ~515,500 words, no duplication.

One caveat worth holding onto: AI research tools do produce confident errors, and the
reference lists were what made claims checkable. They still exist in `sources/`, mapped
per document — worth consulting before treating any specific technical claim as settled.

---

## Conventions

- One Markdown file per source document.
- Filenames lowercase and hyphenated.
- Document assets live in `assets/<document-name>/` beside the document that uses them.
- `MANIFEST.md` lists every file with its word count.
