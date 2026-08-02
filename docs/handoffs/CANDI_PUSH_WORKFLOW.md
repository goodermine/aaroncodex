# Handoff: how Candi pushes a new analysis to GitHub

The routine for getting a freshly analysed take from Candi's machine onto
GitHub so it lands fast, correctly tagged, and conflict-free. Written after the
Bramble Bay night (30 Jul 2026) exposed each failure mode below in practice.

The one-line version:

> **Session branch → context stamped at birth → commit-per-song, pushed
> immediately → no score-table churn → PR when the night's done.**

---

## 1. One branch per session, named for the session

```bash
git fetch origin main
git checkout -b codex/live-brighton-2026-07-31 origin/main
```

Name it for the **date/venue (or session)**, not the first song analysed.

> Why: the 30 Jul branch was called `codex/new-song-aaron-reasons` and ended up
> carrying You Sexy Thing, Kung Fu Fighting, a duet, and a Rilda song. A
> session name stays honest no matter how many songs the night produces.

## 2. Stamp `take_context` at analysis time

Candi knows where the take was sung; the engine does not — a separated vocal
from a 105 dB pub reads the same as a studio take (`capture_risk_elevated` is
False everywhere). So the analysis JSON must carry the context from birth:

```json
"take_context": {
    "intent": "performance",
    "capture": "live",
    "note": "live at Brighton Hotel, JBL wireless, ~105 dB room"
}
```

- `capture`: `live` (leads capture-fair) / `home` / `studio` (lead overall).
- `intent`: `performance` unless the singer declares it a `learning`/`warmup`
  take.
- `note`: venue, mic, and anything that explains the numbers later.
- The tag NEVER changes a score (rule 1) — it only sets which number leads and
  how the take groups. See `tools/take_context.py`.

> Why: every 30 Jul take landed untagged and had to be retro-stamped before the
> leaderboard read honestly.

## 3. Commit and push immediately after each song — one commit per song

```bash
git add voxanalysis/archive/scratch-analyses/2026-07-31-aaron-<song>-take-001_analysis.json
git commit -m "Analyse Aaron: <song> live at Brighton Hotel"
git pull --rebase && git push -u origin codex/live-brighton-2026-07-31
```

Analyse → commit → push as **one motion**. Never batch "for later".

> Why: Kung Fu Fighting sat analysed-but-uncommitted on Candi's disk while the
> singer was told to look for it — the repo is the only thing anyone else can
> see. The `pull --rebase` first avoids the rejected-push stall when the branch
> moved.

## 4. Do NOT regenerate the score tables on the side branch

Commit **only the analysis JSONs** (plus report/notes artefacts if wanted).
Leave `docs/score-metrics/all-takes-rescore-*` untouched; whoever merges runs
`retire_legacy_scores.py` + `rescore_all.py` once, after merge.

> Why: two branches regenerating the tables collide every time — this was the
> repeated merge-conflict source.

## 4b. Never commit into `engine/output/` — it is gitignored

`voxanalysis/.gitignore` ignores `vox-analysis/engine/output/*`. A file
committed there on one branch is invisible to every ranking, scoring and report
tool on another, and `git status` will not show it as missing. This has now cost
two folds: analyses landing there instead of `archive/scratch-analyses/`, and a
blind-listening-test record that had to be relocated by hand.

| Artefact | Where it goes |
|---|---|
| A take's analysis | `voxanalysis/archive/scratch-analyses/<date>-<singer>-<song>-take-NNN_analysis.json` |
| A listening-test / by-ear record | `docs/score-metrics/blind-listening-tests/` |
| Anything else score-related | `docs/score-metrics/` |

A by-ear record must carry `"is_voxai_score": false` and is **never** trended,
averaged or compared against engine scores — it is a different measuring
instrument (rule 3 in spirit: raw human ratings are not a `/10` from the engine).

## 4c. If you re-analyse anything, re-score the archive in place

An analysis scored against an older calibration pack keeps that pack's stored
score forever, and `is_legacy_score()` will not flag it — but `score_conflict()`
refuses to compare it with a current one. After any merge that brings in
analyses from another machine or an older pack:

```bash
python3 docs/score-metrics/rescore_archive_inplace.py   # one pack, in place
python3 docs/score-metrics/rescore_all.py               # rebuild the tables
python3 tools/score_preflight.py                        # now gates on this
```

Preflight fails on a mixed archive since 2 Aug 2026. Before that gate existed,
113 of 182 analyses were silently on a superseded pack.

## 5. The standing guardrails still apply

- `python3 tools/score_preflight.py` **before** scoring (rule 2) — exit 1 means
  do not publish a number.
- Deliver the FULL results to the singer in the conversation (rules 6+8):
  `python3 tools/show_results.py <take>` and paste all of it. **The push is
  plumbing, not the deliverable.**

## 6. When the session is over

Open a PR from the session branch so the takes get folded into `main` (score
tables and any curation happen at merge). If the singer's takes need
`superseded` trimming or milestone tags, flag it in the PR body rather than
editing other songs' files on the session branch.

---

## Checklist (copy per session)

- [ ] Branch `codex/live-<venue>-<date>` cut from fresh `origin/main`
- [ ] Preflight passed before first score
- [ ] Every analysis JSON carries `take_context` (intent + capture + note)
- [ ] One commit per song, pushed immediately (`pull --rebase` first)
- [ ] No `docs/score-metrics` table changes on this branch
- [ ] Full results delivered to the singer in chat, not just pushed
- [ ] PR opened at end of session
