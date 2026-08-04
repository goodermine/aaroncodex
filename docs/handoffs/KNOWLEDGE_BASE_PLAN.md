# Vocal Knowledge Base — structure, maintenance, and the road to public

**Status: DECIDED and PHASES 1–2 BUILT, 3 Aug 2026.**
Aaron's decisions are recorded below in place. Phase 3 remains open.

Scope set by Aaron: **fix structure and maintenance**, with **other singers /
the public** as the eventual audience. This plan does *not* cover wiring the
library into the scoring engine — that was considered and explicitly not chosen.

---

## What the audit found

**The library is in good condition.** This is not a rescue job.

| Check | Result |
|---|---|
| Documents | 79 (excluding `sources/`, `archive/`, meta files) |
| Words | 533,032 |
| Broken internal links | **0** |
| Missing front matter | **0** |
| Docs with no `topics:` | **0** |
| Tags outside `TOPICS.md` | 0 (after fixing the one doc added 2 Aug) |
| Sources audit trail | present, 21 files, excluded from training |
| External material | flagged `exclude_from_training`, author attributed |

Zero broken links across 533k words is unusual and worth protecting.

### What has drifted

1. **`README.md` is stale.** It claims *77 documents · ~525,000 words · seven
   categories*. Actual: **79 · 533,032 · eight folders**. `08-external-reference/`
   does not appear in the structure table at all.
2. **`MANIFEST.md` is hand-maintained.** There is no generator. Word counts were
   hand-edited on 2 Aug, which is precisely how a manifest goes wrong — it drifts
   silently and nothing fails.
3. **`category:` is ungoverned.** `TOPICS.md` is a controlled vocabulary for
   `topics:` and it is followed perfectly. Nothing governs `category:`, which has
   accumulated `coaching-system`, `singer-profile`, `training-programme`,
   `voxai-system`, `long-form`, `vocal-science`, `technique`, `reference`,
   `song-guide`, `artist-analysis`, `sources`, `superseded`. Some of those are
   folders by another name; some are genuine kinds.

> The one document that broke the rules was the drill programme added on 2 Aug:
> 8 tags against a limit of 6, 5 tags outside the vocabulary, and a `category:`
> nobody else used. Fixed. Noted here because it is the argument for a validator:
> **the library stayed clean for 78 documents and broke on the 79th, silently.**

---

## The two decisions only Aaron can make

Everything mechanical waits behind these. Neither is a filing problem.

### Decision 1 — external material

`08-external-reference/reinforced-falsetto-jose-simerilla-romero.md` is a
transcript of another creator's video. It carries `author: "Jose Simerilla
Romero"`, `source_type: external-video-transcript`, and a source video ID. It is
correctly flagged for internal use, and it **cannot ship in a public library
licensed "all rights reserved" to Aaron.**

Options:
- **(a)** Keep it internal — exclude `08-external-reference/` from any public
  build. Simplest, costs nothing, keeps the research value.
- **(b)** Replace it with Aaron's own write-up of the technique, citing Romero as
  a source rather than reproducing him.
- **(c)** Seek permission. Slowest, and probably not worth it for one document.

**Recommendation: (a) now, (b) later if the topic earns a chapter.**

> **DECIDED — (a) exclude.** `08-external-reference/` stays in the repo for its
> research value and never ships. Enforced twice: the folder is on the public
> build's exclusion list, and the document carries `visibility: private`.

### Decision 2 — the personal/general split

`06-voxai-system/` currently holds both the coaching system and **Aaron's own
body**: `aaron-vocal-blueprint-v2.md`, `voxai-master-vocal-profile-aaron.md`, and
`aaron-daily-drill-programme.md` — the last built from his measured take history,
including his weakest columns and his passaggio.

Publishing that folder publishes his measurements. That may be exactly what he
wants — a worked example is the most persuasive thing in a technique library, and
"here is my actual 16th-percentile onset accuracy" is far more convincing than an
anonymous illustration. But it is a decision to make deliberately, once.

Options:
- **(a)** Split the folder: `06-voxai-system/` (the system, public) and a new
  private location for singer profiles. Clean, and it generalises to Rilda, Leo,
  Chris and anyone else measured later.
- **(b)** Publish the profiles as a deliberate case study, with a clear framing
  page. Higher impact, irreversible.
- **(c)** Keep everything internal for now and decide at publication.

**Recommendation: (a).** It is the only option that stays reversible, and the
split has to happen anyway the moment a second singer gets a profile.

> **DECIDED — (a) split, and private for now.** Aaron's blueprint (v1 and v2),
> his master vocal profile and his drill programme moved to
> `vocal-knowledge-base/private/`. `06-voxai-system/` keeps the *method* — the
> knowledge core, the study guide, the implementation handoff — which describes
> how the system works rather than what one person's larynx does. Rilda, Leo and
> Chris profiles go in the same place when they are written.
>
> "Private for now" is the point: publishing a worked example is still available
> later, and this is the only version of the decision that can be reversed.

### The item to decide early, not late — provenance of claims

`README.md` describes the library as *"researched, synthesised and written by
Aaron Ellis"*, and `sources/` preserves the works-cited blocks "from the original
research". For an internal reference that is entirely sufficient.

For **533,000 words of technique guidance given to strangers**, it becomes the
highest-risk item in the project. A wrong claim about belting or range extension
can cost a reader their voice, and unlike a score there is no engine to catch it.

This is not an accusation about how anything was written, and it is not a
blocker. It is a thing to settle before the first document is published rather
than after:

- Which claims are **load-bearing** (someone could hurt themselves) versus
  descriptive? Those are the ones that need a checkable citation.
- Is `sources/` complete enough to support them, given it is "as-extracted,
  run-on numbered lists, an archive to search, not documents to read"?
- Does anything need review by a voice professional before it goes out?

**Recommendation: triage the load-bearing claims only.** Do not attempt to
re-cite 533k words. Vocal health, belting, range extension and anything with a
"do this" imperative are the set that matters.

---

## Phase 1 — make the metadata self-maintaining  ✅ BUILT

The actual "structure and maintenance" ask. All mechanical, no decisions needed,
and it stops the drift permanently.

1. **`tools/kb_manifest.py`** — generate `MANIFEST.md` from the front matter and
   real word counts. Never hand-edit it again.
2. **`tools/kb_validate.py`** — a linter that fails on:
   - missing front matter, or a missing required key
   - `topics:` outside `TOPICS.md`, or more than six
   - `category:` outside a new controlled list (added to `TOPICS.md`)
   - broken internal `.md` links (currently zero — keep it that way)
   - `README.md` / `MANIFEST.md` counts disagreeing with reality
3. **A test** that runs the validator, so CI catches it rather than a person.
4. **Regenerate `README.md`'s structure table** from the same source as the
   manifest, so the 77-vs-79 drift cannot recur.

**This is the piece I would do first.** It is small, it is entirely reversible,
and every later phase depends on the metadata being trustworthy.

> **BUILT.** `tools/kb_common.py` (shared discovery and front-matter parsing, so
> the three tools can never disagree about what a document is),
> `tools/kb_manifest.py` (generates MANIFEST.md and the README table; `--check`
> fails when the committed copy is stale) and `tools/kb_validate.py`. Both run in
> `test_score_contract.py`. `sources/` and `archive/` are held to a lighter
> standard — they are extracted works-cited blocks, not documents, and 44
> permanent meaningless failures would just teach everyone to ignore the
> validator.

## Phase 2 — the public/private boundary  ✅ BUILT

Once Decision 2 is made:

1. Move singer profiles out of `06-voxai-system/` into a private location.
2. Add a front-matter key — `visibility: public | private` — and make the
   validator require it on every document. Explicit beats inferred-from-folder,
   because folders get reorganised and a mistake here is a privacy leak.
3. Add `tools/kb_build_public.py`: assemble a public tree containing only
   `visibility: public`, excluding `sources/`, `archive/`, `08-external-reference/`
   and anything `exclude_from_training`. Never publish the working tree directly —
   build from it, so a private document cannot ship by being forgotten.

> **BUILT.** Current split: **76 public documents · 526,510 words**; 27 excluded
> (21 sources, 4 private, 1 external, 1 archived). The two guards were tested by
> flipping a public document to `visibility: private` — the validator failed with
> *"marked private but sits in a published folder"* and the build excluded it.
> Both then went green on restore.

## Phase 3 — publication readiness

Only worth starting once 1 and 2 are done.

1. **Deduplication pass.** 533k words across 79 documents will contain
   overlapping coverage (breath support appears in the science folder, the
   deep-dives, the course book and the profile). For an internal library that is
   harmless redundancy; for a published one it reads as padding. Needs measuring
   before it needs fixing.
2. **Load-bearing claim triage** — see above.
3. **Editorial consistency** — one voice, one heading convention, one
   terminology set across documents written over a long period.
4. **Decide the unit of publication.** A 533k-word library is not a product; a
   course, a book or a topic-indexed reference site is. `02-course-book/` already
   contains three long-form works and is the most likely first product.
5. **Licence and distribution** — currently all rights reserved, which is a
   position for private material, not a plan for public material.

---

## What is deliberately NOT in this plan

- **Wiring the library into the engine.** Considered and not chosen. Worth
  recording why it is a real fork: the engine's coaching is deterministic and
  verbatim (`prescription_map.json`, 106 exercises, sha256-checked against its
  source library). Feeding prose into coaching means either extracting structure
  the same way, or putting a model in the loop — and a model in the loop conflicts
  with "identical audio yields an identical score, no LLM involvement".
- **Search / serving in VOX Suite.** Not chosen. Note it becomes much cheaper
  after Phase 1, because a generated manifest is most of an index.

## Suggested order

| | Work | Blocked by |
|---|---|---|
| 1 | Phase 1 — manifest generator, validator, test, README regeneration | nothing |
| 2 | Decision 1 (external material) — 5 minutes | Aaron |
| 3 | Decision 2 (personal/general split) | Aaron |
| 4 | Phase 2 — visibility key + public build tool | Decision 2 |
| 5 | Measure duplication; triage load-bearing claims | Phase 1 |
| 6 | Phase 3 — editorial, product shape, licence | everything above |
