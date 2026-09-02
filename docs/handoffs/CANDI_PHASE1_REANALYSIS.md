# Candi — Phase 1: put the whole archive and the reference pack on ONE measurement

**Why (two sentences).** The 16 Aug drift fix changed how held-note drift is
measured, but the 50 professional references and ~208 archived takes were never
re-run, so every take analysed since is scored on pitch-stability against a pro
anchor built on the old measurement (~2.5× too strict). This run re-analyses
everything not on the current engine from its retained RoFormer stem, rebuilds
the pack, and re-scores — full story in `docs/VOX_SYSTEM_REVIEW_2026-09-02.md` §3.1.

No separation re-runs. This is engine passes over existing stems, overnight.

---

## Step 1 — get the Phase-0 engine SAFELY (worktree, no reset)

```bash
cd ~/.openclaw/mary-workspace/aaroncodex && \
git fetch origin claude/voiceassist-plugin-planning-krhz0d && \
git worktree add /tmp/phase1 FETCH_HEAD && \
cd /tmp/phase1 && \
git log -1 --format='engine on %h — %s' && \
python3 -c "import sys; sys.path.insert(0,'voxanalysis/vox-analysis/engine'); import analyse_song as A; print('measurement fingerprint:', A.measurement_fingerprint())"
```

The last line **must print `28e854af22ea`**. If it prints anything else, stop
and send me the output — the worktree is not on the Phase-0 engine.
(If the mirror lag surfaces and FETCH_HEAD is stale, fetch the branch by its
current SHA from the PR #59 page and use that instead of FETCH_HEAD.)

Then confirm the problem is visible from here:

```bash
python3 tools/score_preflight.py | tail -25
```

Expected: `FAIL  the archive + reference pack span more than one MEASUREMENT era`
with roughly `208 archive, 50 references` pre-drift-fix and `26 archive`
post-drift-fix. That FAIL is what Phase 1 clears.

## Step 2 — rehearse (dry run, writes nothing)

`<STEMS>` = the folder(s) holding the retained RoFormer vocal stems, for both the
singers' takes and the reference originals. Give as many directories as needed.

```bash
cd /tmp/phase1 && \
python3 tools/reanalyse_archive.py <STEMS> --stale-measurement 2>&1 | tee /tmp/phase1-archive-dryrun.txt && \
python3 tools/reanalyse_archive.py <STEMS> --stale-measurement \
    --archive voxanalysis/vox-analysis/engine/calibration/references 2>&1 | tee /tmp/phase1-refs-dryrun.txt
```

Read the two summaries:

- `to re-analyse` + `stem not found` — together 237 for the archive and 50
  for the references (verified on this engine); ideally almost all of them in
  `to re-analyse`.
- `stem not found` — **send me this list before the write run.** Each line is a
  take whose stem is not under `<STEMS>`; it cannot be re-analysed without the
  audio. (Retired stubs without an `analysis_input_file` also land here — that
  is expected; ignore those.)
- `already complete` — anything already stamped `28e854af22ea` (none yet).

The tool matches each analysis to its stem by the **exact basename** it
recorded in `analysis_input_file`. Nothing is guessed.

## Step 3 — the write run (overnight; resumable)

```bash
cd /tmp/phase1 && \
python3 tools/reanalyse_archive.py <STEMS> --stale-measurement --write 2>&1 | tee /tmp/phase1-archive-run.txt && \
python3 tools/reanalyse_archive.py <STEMS> --stale-measurement --write \
    --archive voxanalysis/vox-analysis/engine/calibration/references 2>&1 | tee /tmp/phase1-refs-run.txt
```

- Interrupt and re-run any time: takes already stamped `28e854af22ea` are
  skipped, so it resumes where it stopped.
- Each take's previous JSON is kept beside it as `*.pre-reanalysis`. **Do not
  commit those.** Delete them once Step 5 passes.
- `take_context` (intent / capture / superseded / note) is carried forward from
  the old file automatically — the singer's tags survive the re-run.
- A failed take leaves its old file untouched and is listed under `Failures:`
  at the end. Send me that list too.

## Step 4 — rebuild the pack, re-score everything, re-pin

Only after **both** write runs finish:

```bash
cd /tmp/phase1 && \
python3 voxanalysis/vox-analysis/engine/tools/build_calibration.py \
    voxanalysis/vox-analysis/engine/calibration/references \
    --out voxanalysis/vox-analysis/engine/calibration/pro_reference.json && \
python3 -c "
import json; p=json.load(open('voxanalysis/vox-analysis/engine/calibration/pro_reference.json'))
d=p['metrics']['intonation_median_intra_note_drift_cents']
print('pack measurement:', p.get('measurement_fingerprint')); print('drift p10/p50/p90:', d['p10'], d['p50'], d['p90'])" && \
python3 docs/score-metrics/rescore_archive_inplace.py && \
python3 docs/score-metrics/retire_legacy_scores.py && \
python3 docs/score-metrics/rescore_all.py && \
python3 tools/score_preflight.py --update && \
python3 tools/score_preflight.py
```

Expected:

- `pack measurement: 28e854af22ea` (not `None` — if None, some reference was
  not re-analysed; go back to the refs dry run).
- drift p50 lands somewhere near **60 cents** (it was 24.25). That rise is the
  fabricated zeros leaving the pack, not a regression.
- The final preflight prints `PREFLIGHT PASSED`. The `--update` re-pins
  `docs/score-metrics/SCORE_CONTRACT.json` to the new calibration fingerprint —
  commit that file with the rest.

## Step 5 — tests, then one PR

```bash
cd /tmp/phase1/voxanalysis/vox-analysis && python3 -m pytest engine/tests -q 2>&1 | tail -3
cd /tmp/phase1 && find voxanalysis -name '*.pre-reanalysis' -delete && git status --short | head
```

Commit everything that changed (re-analysed archive + reference JSONs, the
rebuilt `pro_reference.json`, `SCORE_CONTRACT.json`, the regenerated score
tables) as **one PR to `main`** titled
`Phase 1: archive + references re-analysed on one measurement era`. In the PR
body paste: the two dry-run summaries, the missing-stem list, the failures list,
the pack's old vs new drift p10/p50/p90, and the final preflight output.

When done: `cd ~/.openclaw/mary-workspace/aaroncodex && git worktree remove /tmp/phase1`.

---

## Two cautions (they matter)

- **Do not quote `pitch_stability` from the rebuilt pack yet.** Rebuilding the
  pack lifts the interim reading rule (the stamps now match), but the
  component's zero anchor ("0 at 80 cents") was set against the old scale — on
  the new one the professional p90 sits near 90 cents, so a good take can still
  read 0. Phase 2 re-anchors it. Until Phase 2 lands, keep quoting the held-drift
  median against the pro band, as now. Every other component is fine to quote.
- **Expect scores to move.** Pitch-stability changes on every take (both
  directions — pre-fix takes lose their fabricated zeros, post-fix takes gain a
  fair anchor). Intonation, voice quality, dynamics, phrase control and breath
  do not change. If a component other than pitch-stability moves on a take,
  send me the take name.

## Send back

1. `/tmp/phase1-archive-dryrun.txt` and `/tmp/phase1-refs-dryrun.txt` (before writing)
2. missing-stem and failures lists
3. the pack's new drift p10/p50/p90 and its `measurement fingerprint`
4. the final preflight output
5. the PR link
