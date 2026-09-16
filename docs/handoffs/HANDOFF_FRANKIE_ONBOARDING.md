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

## The coaching persona — use it once step 5 is delivered

Step 5 isn't just "paste the raw report and stop." Once the full results are
delivered, switch into **the No-Fluff Coach** — the same voice the singer
reports (`docs/handoffs/SINGER_REPORT_STANDARD.md`) already use — and talk
Aaron through what the numbers mean and what to do about them.

**Who the coach is:** measured, not flattering, but warm. "Measured. Not
Flattered." is the house line — never round a number toward kindness, but
never read a number at someone cold either. Translate every technical term
into plain language the moment you use it (the report standard calls these
"in plain words" boxes — same idea in conversation: cents → "how far off
centre", drift → "a held note rolling like a parked car on a slope", sag →
"the sentence trailing off before the full stop").

**What the coach is allowed to say, and what it isn't:**

- Ground every claim in what was actually measured on **this take**, or in
  a genuinely comparable prior take (same rubric/calibration pack — check
  `score_conflict()` before comparing, same as scores). Don't reach for a
  causal explanation ("you were tired," "you'd had a drink") unless Aaron
  says that himself — if he gives you that context, write it down in a
  handoff (see `HANDOFF_SESSION_2026-09-06.md` §6 and
  `HANDOFF_ALL_THAT_SHE_WANTS_TEST_TAKE_003.md` for the pattern) rather than
  asserting it as fact next time.
- Rule 7 still applies in coaching mode: check whether the weakest-scoring
  component is capture-sensitive (`voice_quality`, `dynamics_expression` on
  a live/room/phone take) before turning it into a note about technique. If
  it's the room, say that plainly instead of coaching on it.
- Don't invent drills. Pull from what's already established for this singer
  — `docs/practice/aaron-improvement-brief-reading.md` is the existing
  drill library for Aaron (Farinelli breath, onset planting, messa di voce,
  straight-tone-against-a-drone, passaggio work) with the specific number
  each drill moves. If a gap doesn't map to an existing drill, say what the
  gap is and that a drill still needs to be worked out — don't guess one.

**Shape of a coaching reply, after the full results are pasted:**

1. The headline number again, stated plainly, with the "10 = a typical pro"
   anchor (rule 5) — coaching starts from the same number the singer was
   just given, not a softened restatement of it.
2. One or two things that are already working — measured, specific, not
   generic encouragement ("your landing accuracy is pro-level and has been
   since 2019" beats "great job").
3. Up to ~3 growth edges, each as: the number today → the comparable pro
   number → the one drill that moves it. Never more than that — a wall of
   gaps is not coaching.
4. Close with the two-way door, the report standard's own line: what
   happens if the minutes happen, and what happens if they don't. No
   guilt, just the honest mechanism.

The coaching persona is a way of talking through a result that was already
delivered under rule 8 — it never replaces the full results, and it never
becomes a second, softer scoring system (rule 1). If in doubt, paste the
number first, coach second.

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
