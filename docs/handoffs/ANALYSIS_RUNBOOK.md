# Analysis runbook — how to analyse a take AND deliver it

The canonical steps for anyone (human or agent) running an analysis. Point a
helper at **this file**; it ends with the step that has been missed twice —
delivering the result to the singer.

> **The job is not done at "committed and pushed."** It is done when the singer
> has the actual report in hand (CLAUDE.md rule 8). A commit hash is plumbing.

---

## 1. Get the current engine and PROVE it (before analysing anything)

A stale engine scores ~2.5–3 points too harshly — the worst failure mode here.

```bash
git fetch origin
git checkout -B codex/<task-name> origin/main
python3 tools/score_preflight.py        # MUST exit 0 before you continue
```

Basing off `origin/main` freshly-fetched also means the score tables you
regenerate cover the whole current archive, not a stale subset.

## 2. Separate with the pinned RoFormer model

```bash
bash voxanalysis/vox-analysis/engine/tools/stems/batch_stems.sh \
    --input <recording(s)> --output <stems_out>
```

Pinned model only (`vocals_mel_band_roformer.ckpt`). NOT UVR_MDXNET, NOT the
audio-separator default. Note the model name itself contains "vocals" — match
the parenthesised `(Vocals)` tag, never the bare word, when picking the stem.

## 3. Analyse the vocal stem(s), then refresh + verify

```bash
python3 tools/analyse_takes.py <stems_out> --stems-only --write --force
python3 docs/score-metrics/retire_legacy_scores.py
python3 docs/score-metrics/rescore_all.py
python3 tools/score_preflight.py --update && python3 tools/score_preflight.py   # MUST exit 0
python3 tools/check_take_integrity.py                                           # advisory
```

Integrity is advisory: if a take matches a reference **original's** song AND
duration to a fraction of a second (the Andy Gibb 0.02s failure mode), flag it
and do not trust the score until the singer confirms it is them, not the record.

## 4. Commit — analyses (JSON) only, never audio

```bash
git add voxanalysis/archive/scratch-analyses/*_analysis.json docs/score-metrics/
git commit -m "Analyse <song> (RoFormer)"
git push -u origin codex/<task-name>
```

Name files `20YY-MM-DD-<singer>-<song>-take-001_analysis.json` (singer =
aaron / aaron-g / rilda / chris / leo) so they group correctly.

## 5. **DELIVER THE RESULT — the analysis is not done until you do this**

Run this and **paste the entire output back to the singer, in the conversation:**

```bash
python3 tools/show_results.py <the-new-take-name>
```

That prints the full report from the single source of truth (rule 6). Also state
the headline `/10` led per rule 5 — **overall** for a clean/studio capture,
**capture-fair** for live/room/phone — with confidence and the "10 = a typical
pro" anchor.

**If the song has a scored reference in the archive**, the same command now also
renders `Onset-Map-<take>.png` — the "how each note starts" figure, singer vs
reference — and tells you so on the last line. **Send the image with the
results; it is part of the deliverable.** (It is a diagnostic visualisation,
never a score. No reference for the song → no figure, and nothing is owed.)

A commit hash, branch name, "preflight passed" and "worktree clean" are
confirmations of the plumbing. **They are NOT the deliverable and never stand in
for it.** If `show_results.py` cannot render for any reason, say so and give the
headline + component table it prints as a fallback — never report "done" with
nothing the singer can read.

> This step is written down because it was skipped on "Reasons" (8.0) and again
> on "Two Strong Hearts" (7.8): both were fully analysed, verified, committed and
> pushed — and the singer was handed only a commit hash and green checkmarks. The
> one thing the whole system exists to produce was the one thing not delivered.
