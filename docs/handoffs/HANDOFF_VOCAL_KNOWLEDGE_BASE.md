# Handoff — Vocal Knowledge Base added to the repo

Date: 2026-07-26

Aaron's vocal knowledge base is now in the repo at **`vocal-knowledge-base/`** —
77 active documents, ~524,000 words, researched and written by Aaron Ellis
(Rustwood). It keeps its own `README.md`, `MANIFEST.md`, `TOPICS.md` and `LICENSE`.

**Licence: all rights reserved.** No permission is granted for reuse,
redistribution, or use as training data by anyone else. It is here because it is
Aaron's own material in Aaron's own repo — that is not a licence change.

## Verified against its stated contract

Checked rather than assumed. The contract holds, with two defects found and fixed:

| claim | result |
|---|---|
| 100 documents with valid YAML front matter | ✅ 100 (5 further `.md` are README/MANIFEST/TOPICS, correctly without) |
| `filter status: active` → 77 documents | ⚠️ gave **76** — fixed, now 77 |
| every doc has title/category/topics/words/author/status | ⚠️ **4 missing `words`** — fixed |
| topics drawn only from the controlled vocabulary | ✅ zero out-of-vocabulary tags |
| max 6 topics per document | ✅ zero documents over |
| ~526,000 words active | ✅ 523,849 actual |
| `sources/` + `archive/` carry `exclude_from_training` | ✅ 23 documents |

### Fix 1 — the training filter silently dropped the most important document

`06-voxai-system/aaron-vocal-blueprint-v2.md` carried **`status: current`**, not
`active`. So the documented filter (`status: active`) excluded it — and that file
is the one the README itself names as the entry point for *current coaching state*.
Anything built by following the stated instructions would have been missing
Aaron's live profile.

Changed to `status: active`. No information lost: the front matter already has
`supersedes: aaron-vocal-blueprint-v1`, which is what actually carries "this is
the live one".

### Fix 2 — four chapters missing the `words` key

`unlock-your-voice` chapters 05, 10, 13 and 14. Counted and filled in
(2,155 / 2,359 / 2,918 / 2,698). Front-matter completeness is what makes the corpus
machine-filterable, so a missing key is a real defect, not cosmetic.

## Worth noting: it independently corroborates the engine's measurement

`aaron-vocal-blueprint-v2.md` (written 26 Jul) states the primary target as
**phrase-ending breath sag** — "notes land, hold ~1s, then slide as the phrase runs
out of air. **25 of 51 phrase endings** affected in the benchmark take." Secondary:
early-phrase scooping. Main drill: **Rib Cage Stationary Drill**.

That is the same conclusion the audio analysis reached from the signal alone
(`HANDOFF_ALL_TAKES_SCORES_V4`, `docs/practice/`): 25 of 51 sagging phrase endings,
sliding rather than breaking, upward scoops early in the song, and Rib Cage
Stationary Drill as the most direct hit on the fault. Two independent routes —
measurement and Aaron's own written assessment — landing on the same number and
the same drill.

The knowledge base also notes the Four-Machine Course diagnostic table routes
"pitch scoops up or sags off phrase ends" → Breath, support/stamina, **Week 1**. So
the measured fault already has a designated week and drill in his own curriculum.

## Caveats carried over from Aaron's handoff — respect these

- **Provenance:** the material was synthesised with AI research tools (ChatGPT,
  Gemini Deep Research, Grok), which produce confident errors. `sources/` holds
  per-document reference lists — consult them before treating any specific
  technical claim as settled. Do not quote this library as authority for a
  physiological claim without checking.
- **Nothing here diagnoses anatomy, injury or a medical condition.**
- **The two books are separate works with overlapping chapter numbers.** Always
  name the work as well as the chapter number when citing.
- `archive/` holds a superseded 215,000-word compilation that duplicated 16 other
  documents verbatim. Excluded from training; do not resurrect it.

## Relationship to the engine's exercise library

The engine prescribes from `voxanalysis/vox-analysis/engine/knowledge/prescription_map.json`
(106 exercises, hash-verified, exercise text used verbatim). That remains the
**only** source for prescribed exercises — the rules in `CLAUDE.md` about a single
source of truth apply here too.

This knowledge base is **reference and coaching context**, not a second
prescription library. Several documents discuss the same drills (Farinelli, Rib
Cage Stationary) — useful for explaining *why* a drill works, but if the two ever
disagree on *what to do*, the engine's library wins, because that is what the
score and prescription were computed from.
