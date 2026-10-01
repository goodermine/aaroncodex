# Handoff for Sterling — receiving a song by Dropbox link, then analysing it

You're running on Aaron's own computer, so you have one extra job the other
helpers (Candi, Frankie) don't: **taking a recording in from a Dropbox link
Aaron pastes into the conversation**, before any of the usual analysis steps
even start. This doc covers that intake step, then the same pipeline
everyone else follows.

**Read first, in full:** `CLAUDE.md` (repo root) and
`docs/handoffs/ANALYSIS_RUNBOOK.md`. Everything below is a compressed version
of those two files plus the Dropbox-specific intake step — if anything here
contradicts them, they win.

## The one rule that matters most

Analysing a take is not "run the engine." It's a pipeline that ends with you
pasting the actual results back into the conversation. A commit hash is not
a deliverable. This has been screwed up twice before in this project (full
analyses of "Reasons" and "Two Strong Hearts" were computed, committed, and
pushed — and the singer only got a commit hash).

## Step 0: Aaron sends you a Dropbox link

When Aaron pastes a Dropbox share link (a file or a folder) and says
something like "analyse this," here's what to actually do with it:

1. **Open the link and confirm what it points to** — a single recording, or
   a folder of several. Don't guess from the filename alone; check the
   duration and that it's audio (or audio+video you can pull audio from).
2. **Pull the file down to where the pipeline expects source recordings.**
   The established convention on this machine is the local Dropbox sync
   path, e.g. `/mnt/c/Users/Rustwood/Dropbox/Song_Analysis` — if the link
   Aaron sent already lands inside that synced folder once you open it
   (which it usually will, since it's the same Dropbox account), you don't
   need to copy anything, just note the local path. If it's a link to
   something *outside* that folder (a one-off share, a different account),
   download it into a working folder under your own workspace instead —
   never straight into the repo, and never commit the audio itself (see
   step 4 below).
3. **Say back to Aaron, in one line, what you found** — the filename,
   duration, and which song/take you believe it is — before you spend time
   separating and analysing it. This catches a wrong link or a corrupted
   download early, rather than after 10+ minutes of stem separation.
4. **If the link is a folder with several recordings**, don't assume you
   should analyse all of them — confirm which one(s) Aaron actually means,
   unless he's already said "analyse everything in there."

Once you've got the file confirmed and sitting locally, move to Step 1.

## The pipeline, step by step

### 1. Get the current engine and prove it

```bash
git fetch origin
git checkout -B codex/<task-name> origin/main
python3 tools/score_preflight.py        # MUST exit 0 before you continue
```

If this fails, follow its own instructions (usually
`git merge --ff-only origin/main`). A stale engine scores ~2.5–3 points too
harsh — do not skip this, and do it *before* touching the audio you just
pulled from Dropbox, not after.

### 2. Separate the vocal with the pinned model

```bash
bash voxanalysis/vox-analysis/engine/tools/stems/batch_stems.sh \
    --input <recording-or-dir> --output <stems_out>
```

Pinned model only: `vocals_mel_band_roformer.ckpt` (it's the default). Never
UVR_MDXNET or anything else. When picking the output stem, match the
parenthesised `(Vocals)` tag exactly — not just the bare word "vocals."

### 3. Analyse, then refresh the tables and re-verify

```bash
python3 tools/analyse_takes.py <stems_out> --stems-only --write --force
python3 docs/score-metrics/retire_legacy_scores.py
python3 docs/score-metrics/rescore_all.py
python3 tools/score_preflight.py --update && python3 tools/score_preflight.py   # MUST exit 0
python3 tools/check_take_integrity.py    # advisory — flags if it matches a reference original's duration too closely
```

`analyse_takes.py` alone (no `--stems-only`) can take a raw mix directly and
separate it for you — slower, but useful for a single new upload straight
off a Dropbox link. Run it dirs-only first without `--write` to see what
it'll do (dry run is the default).

### 4. Commit — JSON only, never the audio you downloaded

```bash
git add voxanalysis/archive/scratch-analyses/*_analysis.json docs/score-metrics/
git commit -m "Analyse <song> (RoFormer)"
git push -u origin codex/<task-name>
```

Filename convention: `20YY-MM-DD-<singer>-<song>-take-001_analysis.json`,
singer = `aaron`/`aaron-g`/`rilda`/`chris`/`leo`. Getting this wrong breaks
the "songs sung more than once" grouping — and if the recording came from a
new venue or session tag that isn't already handled, check
`docs/score-metrics/rescore_all.py`'s `DESCRIPTOR_SUFFIXES` list and add it
if missing (this has bitten the archive twice already this month — see the
grouping-fix PRs in the git log if you want the history).

Never commit the audio file itself, the separated stems, or anything you
downloaded from Dropbox — only the analysis JSON. Delete or leave the
downloaded audio in your own local workspace, outside the repo.

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
PR) — that's mandatory archive plumbing, but it comes *after* delivery,
never instead of it.

## The coaching persona — use it once step 5 is delivered

Once the full results are pasted, switch into **the No-Fluff Coach** —
measured, not flattering, but warm. Translate every technical term into
plain language the moment you use it. Ground every claim in what was
actually measured on *this* take, or a genuinely comparable prior take —
never invent a cause (fatigue, drink, lack of practice) unless Aaron tells
you that himself, and if he does, write it into a handoff rather than
asserting it as fact next time. Pull drills from what's already established
(`docs/practice/aaron-improvement-brief-reading.md`) rather than inventing
new ones. Shape of a reply: the headline number restated plainly, one or two
things already working, up to ~3 growth edges each tied to a specific number
and a specific drill, then the honest two-way door on what practice does and
doesn't change.

## Things that will trip you up

- **Stale-branch trap**: don't fork your analysis branch from an old local
  clone. Always `git fetch origin && git checkout -B <branch> origin/main`
  fresh, and before opening/merging a PR, `git merge-base HEAD origin/main`
  to confirm you're not behind — if you are, `git merge origin/main` into
  your branch before pushing. This has happened repeatedly across every
  helper working on this repo, not just you.
- **Rule 3**: never quote a score without checking `is_legacy_score()` and
  `score_conflict()` first — see `CLAUDE.md` §3.
- **Rule 4**: a low `dynamics_expression` or `voice_quality` on a live/room
  capture is not a reason to withhold — that's the room, not the singer.
- **`artist_name`** in the analysis JSON must be the actual singer, never
  "Unknown Artist" — double check it before committing.
- **New venue/session tags in a filename** (a tavern name, a device name, a
  one-off word like "tribe" or a house name) need to be in
  `DESCRIPTOR_SUFFIXES` in `rescore_all.py` or the take will silently
  fragment into its own song bucket instead of joining the singer's other
  takes of the same song. Check for this whenever the recording's source
  filename (from the Dropbox link) has an unfamiliar word in it.

If Aaron just sends you a Dropbox link with "analyse this," that means: pull
it in per Step 0, then run the entire pipeline end to end, including Step 5.
Don't stop at "committed and pushed."
