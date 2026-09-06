# Handoff — where Phase 1c stands, 6 Sep 2026

Written for anyone picking this up cold: a new session, a human, or an agent
connected via Claude Code Remote Control. Read this before touching scores,
the archive, the `/tmp/phase1` worktree, or the calibration pack.

**One-paragraph version:** Phase 1c (re-analysing the archive on the fixed
engine) has made real progress since the 3 Sep handoff — 158 takes fixed/
re-analysed, 7 retired for having no recoverable source audio — but none of
that has a PR open yet, and there's a separate batch of 36 files sitting
uncommitted in the shared worktree with an unresolved quality flag. The
current true count is **33 takes still genuinely open** (not 69 — that
number is stale; see §2).

---

## 1. Where the actual work is sitting right now

| What | Where | Pushed to origin? |
|---|---|---|
| 158 re-analysed + 7 retired takes (commits `e9c0c2a`, `4a1e062`, `5bbc49c`, `945b040`) | Git worktree at `/tmp/phase1`, HEAD `945b040` | **Yes** — branch `phase1c-archive-reanalysis-wip`, verified identical to origin. **No PR open for it yet.** |
| Stem-collision fix in `reanalyse_archive.py` (`index_stems()` no longer silently picks whichever directory searched first) | Committed as `4a1e062` in the worktree above (cherry-picked from `0ce5f3e` on `claude/voiceassist-plugin-planning-krhz0d`) | Yes, as part of the same pushed branch |
| PRIMARY FOCUS stale-threshold fix (`_primary_focus()` now gates on the component's own calibrated score, not a bare cents number) | Isolated out of the same source branch into its own PR | **PR #73, still OPEN, not yet merged** — https://github.com/goodermine/aaroncodex/pull/73. Attempting to merge it directly from a session hit a local permission-classifier block; needs a human click or another attempt. |
| **36 uncommitted files**, re-analysed in an earlier 12:47–12:50 run *before* the collision fix existed — correct durations and the new fingerprint, but source switched from `.flac` to a `converted.wav` and note names got unicode-escaped | Uncommitted in the same `/tmp/phase1` working tree | **No — exists nowhere else.** This is the only genuinely at-risk content right now: if `/tmp/phase1` is ever cleaned up, this batch is gone. Not yet decided whether to keep, redo, or discard — flagged by Candi, never resolved. |

`/tmp/phase1`'s local branch is confusingly named `phase1a-reference-pack-28e854af22ea` — that name already exists on GitHub as a *different, already-merged, unrelated* branch (Phase 1a reference pack, safe to ignore). The local name is just mislabeled; the commit content is the real Phase 1c work described above.

## 2. The actual current count — corrected

Directly checked every archived analysis's `measurement_fingerprint` against the running engine (`28e854af22ea`) on 6 Sep:

- **237** total archive files
- **194** already on the current engine (includes the 36 uncommitted files above — if those get discarded rather than kept, this drops by up to 36)
- **43** still stale, of which:
  - **10** already retired (`technical_score.status == "retired_legacy_score"`) — finalized, not actionable, no source audio found after checking Dropbox
  - **33** genuinely open — this is the real number to work from, not the "69" that's been quoted; that reflects an earlier point before this session's progress landed

## 3. Breakdown of the 33 open takes

Ran `tools/reanalyse_archive.py --stale-measurement` across the three known stem roots (`mary-workspace/aaroncodex/voxanalysis/vox-analysis/engine/output/stems`, `.../engine/temp`, `candi-workspace/openclaw-data`) and `tools/pair_reference_audio.py --skip-current-era --refs voxanalysis/archive/scratch-analyses` against the live Dropbox `Song_Analysis` folder (`/mnt/c/Users/Rustwood/Dropbox/Song_Analysis`), both read-only, nothing written:

| Bucket | Count | Detail |
|---|---|---|
| Stem found — can re-analyse directly | **0** | None of the 33 have their exact recorded stem filename present in any of the three known roots. |
| Needs re-separation from a source mix | **6** | 4 have a plausible source matched by duration only, name disagreeing — needs a real listen to confirm or reject (e.g. "Bust a Move" duration-matched to "Love Shack (Homestead).wav", almost certainly wrong). 2 are ambiguous same-duration pairs where a `-Vocals` and `-Music` file share a length (Lean On Me, Pressure Down) — trivially resolvable by picking the right one. |
| No recoverable audio found in Dropbox at all | **27** | Checked against the full Dropbox `Song_Analysis` folder recursively. These are retirement candidates under the existing rule, pending the same "confirm by eye" scrutiny already applied to the 10 already-retired ones. |

Full lists (which take wants which stem, exact durations, exact candidate matches) are in `/tmp/phase1-frankie-dryrun-20260906.txt` and `/tmp/phase1-frankie-pairing-20260906.txt` on this machine.

## 4. Immediate next steps, in order

1. **Get PR #73 merged** (the PRIMARY FOCUS fix) — it's isolated, tested, verified against two real takes, just blocked on a permission click.
2. **Decide on the 36 uncommitted files** — keep (if the unicode-escaping/format-switch turns out harmless), redo from the collision-fixed tool, or discard. Whoever decides should check a sample by hand first.
3. **Open a PR for `phase1c-archive-reanalysis-wip`** once (2) is resolved — the 158+7 already-pushed commits deserve a real review path, not just a bare branch.
4. **Resolve the 6 "needs re-separation" takes** — listen to the 4 name-unsure candidates, pick between the 2 ambiguous pairs, then re-separate and re-analyse.
5. **Retire the 27 no-source-found takes**, following the same pattern as the existing 10 (`technical_score.status = "retired_legacy_score"`, with a `reason` and `action` field).

## 5. Reading order for a fresh pickup

1. This document, for current state.
2. `docs/handoffs/HANDOFF_SESSION_2026-09-03.md`, for how Phase 1c got here (the stem-collision bug, the 4 wrong-audio takes it caused).
3. `docs/handoffs/CANDI_PHASE1_REANALYSIS.md`, for the exact procedure.
4. `docs/VOX_SYSTEM_REVIEW_2026-09-02.md`, for why any of this matters.
5. `CLAUDE.md`, always, for the standing scoring rules.
