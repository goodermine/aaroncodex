# Handoff for Frankie — what "analyse this song" actually means

You have the same repo/tool access Candi has, but not her accumulated context.
This is that context.

**Read first, in full:** `CLAUDE.md` (repo root) and
`docs/handoffs/ANALYSIS_RUNBOOK.md`. Everything below is a compressed version
of those two files — if anything here seems to contradict them, they win.

## The one rule that matters most

Analysing a take is not "run the engine." It's a 5-step pipeline that ends
with you pasting the actual results back into the conversation. A commit hash
is not a deliverable. This has been screwed up twice before (full analyses of
"Reasons" and "Two Strong Hearts" were computed, committed, and pushed — and
the singer only got a commit hash).

## The 5 steps

### 1. Get the current engine and prove it

```bash
git fetch origin
git checkout -B codex/<task-name> origin/main
python3 tools/score_preflight.py        # MUST exit 0 before you touch anything else
```

If this fails, follow its own instructions (usually
`git merge --ff-only origin/main`). A stale engine scores ~2.5–3 points too
harsh — do not skip this.

### 2. Separate the vocal with the pinned model

```bash
bash voxanalysis/vox-analysis/engine/tools/stems/batch_stems.sh \
    --input <recording-or-dir> --output <stems_out>
```

Pinned model only: `vocals_mel_band_roformer.ckpt` (it's the default). Never
UVR_MDXNET or anything else. When picking the output stem, match the
parenthesised `(Vocals)` tag exactly — not just the bare word "vocals."

Source recordings live in Dropbox: `/mnt/c/Users/Rustwood/Dropbox/Song_Analysis`
(or wherever Aaron says he just uploaded to — ask if unclear).

### 3. Analyse, then refresh the tables and re-verify

```bash
python3 tools/analyse_takes.py <stems_out> --stems-only --write --force
python3 docs/score-metrics/retire_legacy_scores.py
python3 docs/score-metrics/rescore_all.py
python3 tools/score_preflight.py --update && python3 tools/score_preflight.py   # MUST exit 0
python3 tools/check_take_integrity.py    # advisory — flags if it matches a reference original's duration too closely
```

`analyse_takes.py` alone (no `--stems-only`) can take a raw mix directly and
separate it for you — slower, but useful for a single new upload. Run it
dirs-only first without `--write` to see what it'll do (dry run is the
default).

### 4. Commit — JSON only, never audio/stems

```bash
git add voxanalysis/archive/scratch-analyses/*_analysis.json docs/score-metrics/
git commit -m "Analyse <song> (RoFormer)"
git push -u origin codex/<task-name>
```

Filename convention: `20YY-MM-DD-<singer>-<song>-take-001_analysis.json`,
singer = `aaron`/`aaron-g`/`rilda`/`chris`/`leo`. Getting this wrong breaks
the "songs sung more than once" grouping.

### 5. Deliver — the step that's been skipped before

```bash
python3 tools/show_results.py <the-new-take-name>
```

Paste the *entire* output back into the conversation. State the headline
`/10`: **overall** for a clean/studio capture, **capture-fair** for
live/tavern/phone/room — capture-fair excludes the mic-sensitive components.
Always state confidence and the "10 = a typical pro (calibrated to 50 pro
reference vocals)" anchor. If a scored reference exists for the song,
`show_results.py` also renders an onset-map PNG — send that image too.

Finally: open a PR to `main` for the branch (or add to the existing session
PR) — that's mandatory archive plumbing under rule 9, but it comes *after*
delivery, never instead of it.

## Things that will trip you up (learned the hard way this week)

- **Stale-branch trap**: your local session sometimes forks a new analysis
  branch from an old commit instead of fresh `origin/main`. Before
  opening/merging a PR, always `git fetch origin && git merge-base HEAD
  origin/main` and diff — if your branch predates a recent engine/tooling fix
  on main, `git merge origin/main` into your branch before pushing.
- **Rule 3**: never quote a score without checking `is_legacy_score()` and
  `score_conflict()` first — see `CLAUDE.md` §3.
- **Rule 4**: a low `dynamics_expression` or `voice_quality` on a live/room
  capture is not a reason to withhold — that's the room, not the singer.
- **`artist_name`** in the analysis JSON must be the actual singer, never
  "Unknown Artist" — double check it before committing.
- Never commit source audio or separated stems, only the analysis JSON.

If Aaron just says "analyse this song" with nothing else, that means: run
this entire 5-step pipeline on whatever he just uploaded, end to end,
including step 5. Don't stop at "committed and pushed."
