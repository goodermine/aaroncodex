# Candi — re-pull required, and what changed (2–4 Aug 2026)

Three days of work landed on `claude/voiceassist-plugin-planning-krhz0d`
(draft PR #30). Some of it changes **how your analysis sessions must run**, so
re-pull before the next one.

## 1. Re-pull

```bash
git fetch origin
git checkout claude/voiceassist-plugin-planning-krhz0d && git pull
```

**Until PR #30 merges, cut your session branches from THIS branch, not main.**
Main still carries the old calibration pack and none of the new gates — takes
analysed off main will score against a superseded pack and be refused at fold-in
(see §3). After the PR merges, go back to cutting from fresh `origin/main` as
your workflow doc says.

## 2. The one thing you must run after any pull or merge

```bash
python3 docs/score-metrics/rescore_archive_inplace.py   # whole archive onto ONE pack
python3 docs/score-metrics/rescore_all.py               # rebuild the tables
python3 tools/score_preflight.py                        # must end PASSED
```

`rescore_archive_inplace.py` is new. It re-scores every stored
`technical_score` in place through the one engine — never touching audio or
measurements — so the whole archive sits on one calibration pack. It exists
because 113 of 182 archived analyses were silently anchored to a superseded
pack while preflight said "safe to publish".

## 3. Preflight now REFUSES a mixed archive

`score_preflight.py` gained check 3b: any stored score anchored to a
calibration pack other than the pinned one fails the run, with the fix printed.
The pinned pack is now **1d3e2991f144** (onset anchors added; every
pre-existing anchor byte-identical, zero scores moved — verified across all
182 analyses). If your preflight fails after pulling: run §2, it will pass.

## 4. ENTRY ACCURACY — new in every analysis and every report

The engine now emits an `entry_accuracy` block (clean / scooped / overshot
entries, with percentiles vs the 50 references) and the full-results text
prints it under its own heading. Rules:

- It is a **diagnostic, never a score** — no `/10`, never averaged with one.
  (An onset score component was built, tested and REJECTED —
  `docs/handoffs/V6_ONSET_COMPONENT_REJECTED.md`.)
- **Quote the percentile, not the bare percent.**
- It carries a reliability flag: `suspect` (contaminated stem — withheld),
  `reduced` (harsh room — read as indicative), `high`. Respect it.
- For a **definitive** onset read use a dry supply-your-own-backing take;
  stems carry noise exactly in the note-start region
  (`SCORE_READING_LIMITATIONS.md`, limitation 5 — the doc is now FIVE
  limitations, re-read it before quoting anything).

## 5. The onset map is part of the deliverable now

`tools/show_results.py` — your rule-8 final step — automatically renders
`Onset-Map-<take>.png` (singer vs reference, how each note starts) whenever
the take's song has a scored reference in the archive, and tells you on the
last line. **Send the image WITH the results.** No reference → no figure,
nothing owed. Runbook step 5 updated.

## 6. Your workflow doc grew two sections — read them

`CANDI_PUSH_WORKFLOW.md` §4b and §4c:

- **Never commit into `engine/output/`** — it is gitignored and invisible on
  other branches. This bit us twice, including your blind-test record, which
  now lives at `docs/score-metrics/blind-listening-tests/` (its permanent
  home; listening-test records carry `is_voxai_score: false` and are never
  mixed with engine scores).
- **Re-score in place after merges** (§2 above).

## 7. Knowledge base: private split + validators (only if you touch KB files)

- Singer profiles moved to `vocal-knowledge-base/private/` — **never published,
  never in any public build.** `08-external-reference/` likewise excluded.
- Every document carries `visibility: public|private` in front matter.
- After editing any KB document: `python3 tools/kb_validate.py` must pass and
  `python3 tools/kb_manifest.py` regenerates MANIFEST/README counts — **never
  hand-edit MANIFEST.md again.** Both run in the test suite.

## 8. New, for awareness (no action)

- **Pitch monitor TRAIN mode** — onset trainer at `/monitor`: plays a target,
  silent audiation beat, verdicts the entry clean/scoop/overshoot from the
  first 250 ms. Same thresholds as ENTRY ACCURACY. Smoke check in
  `pitchmonitor/tests/`.
- **`memory/` + `.claude/skills/dream/`** — a session-memory system with a
  nightly review routine. The `memory/` folder is Claude's working memory,
  approved fact-by-fact by Aaron: don't edit it by hand; if a fact in it is
  wrong, tell Aaron and the /dream routine will propose the correction.
- **Aaron's drill programme** (now in `private/`) was rebuilt on the onset
  research at `01-vocal-science-technique/vocal-onset-how-notes-begin.md`; the
  blind A/B you ran is written up in `SCORE_READING_LIMITATIONS.md` — the era
  gap was real (drift the engine floors at 80c), not expectation. Your test
  design held up; thank you for running it properly.

## Quick checklist for your next session

- [ ] Re-pull per §1; branch from `claude/voiceassist-plugin-planning-krhz0d`
- [ ] §2 trio runs clean; preflight PASSED before scoring anything
- [ ] Analyses land in `voxanalysis/archive/scratch-analyses/` (never `engine/output/`)
- [ ] Full results delivered per rule 8 — including the onset map when one is produced
- [ ] Quote onset findings as percentiles; respect the reliability flag
