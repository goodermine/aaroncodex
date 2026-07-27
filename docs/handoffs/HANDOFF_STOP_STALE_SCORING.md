# Handoff — why scores keep going wrong, and the fix

Date: 2026-07-25

Aaron's observation: Candi keeps producing confused results — old rubrics, wrong
withholdings, numbers that contradict the repo. This is **not** carelessness. It's
an architecture problem with three specific causes, all now addressed.

## Root cause

1. **Two scoring implementations.** The canonical rubric lives in
   `voxanalysis/vox-analysis/engine/analyse_song.py`. Candi's workspace has its own
   *"Phase 1 backend ledger"* (`scripts/candi_phase1.py`) that computes and
   validates scores separately. Two implementations drift — that is what produced
   `5.1` vs `8.3` on one stem, and the `9.5` withdrawn in favour of a broken `6.5`.

2. **No standing rules in the repo.** There was **no `CLAUDE.md` / `AGENTS.md`
   anywhere in this repo.** An agent pulling it received zero instruction about
   which engine is canonical, which number to quote, or when to withhold. Rules
   lived only in Candi's own workspace, where they went stale relative to the
   engine — she was still applying a rule written for rubric **v1**.

3. **Nothing detected a stale engine.** An old engine produces confident,
   plausible, *wrong* numbers — roughly **2.5–3 points too harsh**. Nothing checked.

## The fix (all committed)

### 1. `CLAUDE.md` at the repo root — read automatically, every session

Standing rules, each one written because it was broken in practice:

1. **One scoring engine.** Never re-implement, adjust or "sanity-check" a score.
   A comparison analyser may publish raw differences only, never a rival `/10`.
2. **Run preflight before publishing any score.**
3. **Never quote a score without current provenance** (`is_legacy_score`,
   `score_conflict`).
4. **Withhold only on a provenance conflict** — explicitly *not* on
   capture-sensitive dynamics or a low live-capture `voice_quality`.
5. **Which number to give:** overall for studio, **capture-fair for live/room/phone**;
   always state confidence and that 10 = a typical pro.
6. **Always send the full results**, never a summary; if the score is withheld,
   still send everything else.
7. **Don't coach off a capture artefact** (the engine's PRIMARY FOCUS can name the
   room, not the singer).

`AGENTS.md` symlinks to it for non-Claude tooling.

### 2. `tools/score_preflight.py` — fails closed on a stale engine

```bash
python3 tools/score_preflight.py
```

Verifies (a) the running engine matches `docs/score-metrics/SCORE_CONTRACT.json`
— rubric name **and** a fingerprint of the scoring source, so silent maths changes
are caught; (b) the 50-reference calibration pack is loaded; (c) no archived
analysis still carries a quotable legacy score.

Exit 0 = safe to publish. **Exit 1 = publish nothing**, with the fix printed:

```
FAIL  the engine you are running is NOT the repo's engine:
        - rubric: repo expects 'deterministic_rubric_v4', this engine has 'deterministic_rubric_v1'
      DO NOT publish a score from this engine. Fix:
        git fetch origin main && git merge --ff-only origin/main
```

Maintainers re-pin intentionally with `--update` (and commit it).

### 3. Tests that stop the rules and contract drifting

`engine/tests/test_score_contract.py` fails if the rubric changes without
re-pinning the contract, if `CLAUDE.md` goes missing, or if it stops stating the
key rules.

## Audit: the repo is already clean — there is only ONE engine here

Checked explicitly (25 July):

```
grep -rln "def compute_technical_score" .   →  1 file
find . -name "analyse_song*.py"             →  1 file
```

`voxanalysis/vox-analysis/engine/analyse_song.py` is the only scoring
implementation in this repo. **There are no old/duplicate engine copies to
delete here** — so "get rid of the old engines" is entirely a **workspace-side**
job, not a repo one.

Two *readers* of scores were, however, comparing and trending without a
provenance check, and are now fixed:

- **`pitch_track.py`** built the take-vs-original comparison by pairing the two
  stored scores directly. Pairing a stale-rubric score with a current one invents
  a gap that isn't there. It now calls `score_conflict()` and, on conflict,
  withholds the *score pair only* (`scores_comparable: false` plus the reason)
  while still reporting all the raw contour/timing measures.
- **`tools/progress_report.py`** trended "technical score" across takes with no
  provenance check at all, and carried a footnote claiming scores from different
  calibration packs were "approximately comparable" — the exact false assumption.
  It now excludes non-comparable takes from the **score** trends (showing
  `re-score`, with a note saying how many were dropped and why), keeps them in the
  **raw-metric** trends (those are always comparable), and states the rule
  correctly.

> This mattered: without it, Aaron's progress chart would have shown a fake ~3-point
> jump that was purely the rubric changing, not his singing.

## What Candi needs to do in her workspace

The repo half is done. Two workspace changes remain, and they're the ones that
actually stop the recurrence:

1. **Delete the local scoring path.** `scripts/candi_phase1.py` must stop computing
   or validating `/10` values of its own. Replace with: call
   `compute_technical_score()` from this repo, and use `is_legacy_score()` /
   `score_conflict()` for validation. Keep the *guard* concept — just source the
   truth from one engine.
2. **Make preflight mandatory** in the analysis flow: run
   `python3 tools/score_preflight.py` and refuse to send a `/10` on non-zero exit.

Then update the withholding rule per CLAUDE.md §4 — the dynamics-zero condition
cannot occur under v4 or v5 and only causes false withholdings (it blocked
Aaron's best Pressure Down take, which reads **8.2 / 9.2 capture-fair** under v5;
the 8.3 / 9.5 it read under v4 is retired — do not quote it).

## Why this should hold

The failure mode was *silence*: a stale engine looks identical to a current one,
and a wrong score looks exactly like a right one. All three fixes convert silence
into a loud, actionable failure — preflight exits 1, provenance checks refuse, and
the tests break. Combined with `CLAUDE.md` being read every session, an agent
would have to override explicit instructions **and** a failing check to publish a
stale number again.
