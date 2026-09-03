# Handoff — where things stand, 3 Sep 2026

Written for anyone picking this up cold: a new session, a human, or an agent
connected via Claude Code Remote Control. Read this before touching scores,
the archive, or the calibration pack — it says exactly what's done, what's
in flight, and what's blocked.

**One-paragraph version:** the 16 Aug drift-fix engine change was measured
correctly but never propagated to the 50-reference calibration pack or the
234 pre-fix archive takes, so every score since has been on the wrong ruler.
That's fixed for the references (merged). The archive fix is in progress,
was paused mid-run to checkpoint, and a real bug was found and fixed in the
re-analysis tool itself before it goes any further. See "Where we are right
now" below for the exact next step.

---

## 1. The chain of work, in order

### Phase 0 — provenance guard (done, merged)
`analyse_song.py` gained `measurement_fingerprint()`: a hash of the
measurement functions + constants, stamped on every analysis and carried in
`score_identity()` alongside the calibration pack's own stamp.
`score_conflict()` refuses to compare two stamped scores from different
measurement builds. `score_preflight.py` gained a check that fails when the
archive, references and running engine span more than one measurement era.
`report_builder.py` gained an interim reading rule: on a take measured after
the drift fix but scored against the pre-fix pack, `pitch_stability` is
withheld from the report (not from the JSON — the engine's number is
untouched) and the held-drift median is printed against an emulated
professional band instead. A new diagnostic, `analyse_word_drift`
("WORDS vs NOTES"), splits held-note drift into vowel-drift vs
boundary-excursion, per note, with timestamps — outside the measurement
fingerprint, so it changed no score.

Full reasoning: `docs/VOX_SYSTEM_REVIEW_2026-09-02.md`.

### Phase 1a — reference pack re-measured (done, merged)
All 50 professional reference analyses were re-run on the fixed engine from
retained stems (found via Howard's OpenClaw backup after the live workspace's
own copies had been lost — see §2 below) and the calibration pack rebuilt.

- **Merged:** PR #70, commit `95d4de1` on `main`.
- Pack fingerprint now matches the engine: `28e854af22ea`.
- Drift anchor moved from p10/p50/p90 `14.38/24.25/52.35` to
  `44.45/62.55/90.11` cents — the fabricated short-note zeros leaving the
  pack, exactly as predicted before the real re-measurement ran.
- **Verified clean** on 3 Sep: all 50 reference durations match their
  pre-rebuild values exactly (no wrong-source-audio problem here — see §3).

### Phase 1c — archive re-analysis (in progress, currently paused)
The 234 archive takes still on the pre-fix measurement need the same
treatment. Handoff: `docs/handoffs/CANDI_PHASE1_REANALYSIS.md` (Step 3b
covers re-separating anything with no retained stem).

Progress so far: stems were recovered from three places — Mary's live engine
tree, `candi-workspace`, and `~/.local/share/Trash/files` — and
`reanalyse_archive.py --stale-measurement --write` worked through them.
**106 archive takes were checkpointed** to branch
`phase1c-archive-reanalysis-wip` (commit `e9c0c2a`, based on `016c009`,
*not* on the later `main` tip — that's fine, it's independent content).

**Then Aaron told Candi to stop all running processes. The worker is
currently stopped, not running.**

---

## 2. What's currently blocking Phase 1c — read this before resuming

Reviewing the `phase1c-archive-reanalysis-wip` checkpoint found a real bug,
not just a data quirk.

**The bug:** `reanalyse_archive.py`'s `index_stems()` searched multiple
directories for a stem by filename and used `dict.setdefault()` — first
directory searched wins, silently, with no check that a same-named file in a
second directory might be a *different recording*. That's exactly what
happened: an untrimmed raw separation shared a filename with the actually
curated, trimmed take in a directory that was searched later.

**The damage — 4 of the 106 checkpointed takes have the wrong audio behind
them:**

| Take | Correct duration | Got (wrong) |
|---|---|---|
| `2026-08-01-aaron-reasons-take-003` | 210.0s | 273.17s |
| `2026-08-01-rilda-back-to-black-take-001` | 225.0s | 259.16s |
| `2026-08-01-aaron-kung-fu-fighting-take-004` | 187.0s | 211.48s |
| `2026-08-01-aaron-kung-fu-fighting-take-005` | 190.0s | 217.96s |

Each grew by exactly the length of the host talk / crowd noise / applause
that the take's own `take_context.note` says was deliberately trimmed out
when it was first curated. The other 102 of 106 files are clean — verified
duration match to the second, correct `measurement_fingerprint`, unchanged
`take_context`.

**The already-merged reference pack (Phase 1a) does NOT have this problem** —
checked separately, all 50 durations match exactly. This was isolated to the
unmerged WIP branch, which is exactly what checkpointing before the full run
finished was for.

**The fix — pushed, not yet applied to Candi's worktree:**
`0ce5f3e` on `claude/voiceassist-plugin-planning-krhz0d`. `index_stems()` now
collects every candidate per basename; candidates within 2% file size are
treated as copies of the same recovered file (resolves quietly, the common
case); candidates that differ by more are a genuine collision — excluded
from the run entirely and reported by name with paths and sizes, never
guessed. Tests cover both the harmless-duplicate case and the
must-not-guess collision case.

## 3. Where we are right now — the next step

Candi has been given (via Aaron) a 5-step corrected instruction set:

1. Pull `0ce5f3e` into the `/tmp/phase1` worktree (`git cherry-pick 0ce5f3e`
   — the worker is stopped, so no concurrency concern).
2. Revert the 4 known-bad files to their pre-checkpoint content
   (`git checkout 016c009 -- <4 paths>`), uncommitted — just gets them back
   to correctly-flagged-as-needing-work rather than silently wrong.
3. Re-run the dry run with the fixed tool across all the stem directories
   used so far, and check the new "CONFLICTING candidates" section — this
   surfaces every basename collision across the search directories, not
   just the 4 already known, so there may be more to resolve.
4. For the 4 known-bad takes specifically: locate the correct trimmed stem
   for each (durations above) and confirm with the paths before re-running.
5. Once the collision report is clear, resume the `--write` pass for
   everything else — it picks up exactly where it left off.

**As of this document, no confirmation has come back yet that Candi has
started on this.** Whoever picks this up next: ask for that status before
assuming any of the 5 steps are done.

## 4. Branches, PRs, and where things live

| Branch | State | Contains |
|---|---|---|
| `main` | — | Phase 0 + Phase 1a, merged (`95d4de1`) |
| `claude/voiceassist-plugin-planning-krhz0d` | open work | Phase 1b tooling, Phase 1c handoff, the collision-detection fix (`0ce5f3e`, latest) — **not yet merged to main**, no PR blocking it, just hasn't been opened as one yet |
| `phase1c-archive-reanalysis-wip` | WIP checkpoint | 106 re-analysed archive takes, 4 known-bad (see §2), based on `016c009` not the later `main` tip |
| `phase1a-reference-pack-28e854af22ea` | merged (as part of PR #70) | superseded, safe to ignore |

`docs/score-metrics/SCORE_CONTRACT.json` on `main` is pinned to
`measurement_fingerprint: 28e854af22ea`. `score_preflight.py` on `main`
currently **fails** on check 3b/5 (234 archive takes on a superseded pack) —
correct and expected until Phase 1c completes. Do not quote a leaderboard,
trend, or archive average until it passes.

## 5. Delivery to Aaron in the meantime

The interim reading rule (Phase 0, live on `main`) means single-take
delivery is unaffected by any of the above — `pitch_stability` is
automatically withheld on pre-fix takes with the held-drift median shown
against the pro band instead. Full results can still be sent for any new
take normally.

## 6. Side channel — Remote Control (unresolved, not blocking)

Aaron connected a local Claude Code session (`rustwood-c1`, WSL2, working
dir `/home/rustwood` — Candi's actual machine) via Remote Control, hoping
for direct session-to-session messaging instead of relaying through Telegram
via Aaron. Current state:

- The local→cloud direction works: one cross-session message arrived here
  successfully, from address `bridge:session_015Vwtq3z8etjqa8eaJ1vmiw`,
  confirming the local session's name (`rustwood-c1`) and working directory.
- The cloud→local direction does **not** work from this session: both
  `SendMessage` to `rustwood-c1` (not found in this session's `ListAgents`)
  and to the bridge address (explicit `auth` error: "this cloud session
  cannot message other sessions yet") failed. This is a one-way link right
  now, not a bug to keep retrying — the platform said so explicitly.
- Aaron may check whether this needs an explicit enable somewhere (the docs
  mention Team/Enterprise plans need an Owner to turn on Remote Control in
  admin settings; unclear if a similar toggle governs outbound cross-session
  messaging specifically).
- Not used for anything yet. If it becomes bidirectional, the obvious use is
  handing Phase 1c steps directly to a session with real filesystem access
  instead of relaying through Candi/Telegram — but that needs an explicit
  decision with Aaron on how it coordinates with Candi's own work first, so
  two things aren't editing the same archive files unsupervised.

## 7. Reading order for a fresh pickup

1. This document, for current state.
2. `docs/VOX_SYSTEM_REVIEW_2026-09-02.md`, for why any of this matters and
   the full findings (§3.1 is the drift-scale root cause).
3. `docs/handoffs/CANDI_PHASE1_REANALYSIS.md`, for the exact Phase 1c
   procedure (Step 3b is the re-separation path this document's §2 bug was
   found inside).
4. `CLAUDE.md`, always, for the standing scoring rules.
