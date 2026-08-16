# Candi — re-run the short-note takes on the drift-artefact fix

The engine bug that faked `0.0` held-note drift — which inflated `pitch_stability`
and the straight-tone `vibrato_control` path to 10/10 on short/fast (rap / funk /
disco) takes — is **fixed**. The 12 affected takes have their scores **withheld**
until they're re-analysed from the source audio, which only your box has.

---

## Step 1 — get the fixed engine SAFELY (no destructive reset)

> The canonical checkout is `~/.openclaw/mary-workspace/aaroncodex`. **Do NOT run
> `git reset --hard` on it** — it would discard any local state. Use a throwaway
> **git worktree** instead: it checks out the fixed branch in a separate folder
> and never touches the canonical tree.

```bash
# From the canonical checkout (adjust the path only if yours differs):
cd ~/.openclaw/mary-workspace/aaroncodex && \
git fetch origin claude/voiceassist-plugin-planning-krhz0d && \
# Isolated checkout of the fixed engine — the canonical tree is untouched.
# (If the mirror lag surfaces, replace FETCH_HEAD with the exact SHA 5449915.)
git worktree add /tmp/driftfix FETCH_HEAD && \
cd /tmp/driftfix && \
git log -1 --format='fixed engine on %h — %s' && \
grep -q "measurable_drifts" voxanalysis/vox-analysis/engine/analyse_song.py \
  && echo "FIX PRESENT ✅" || echo "FIX MISSING ❌ — stop, re-add worktree at SHA 5449915" && \
python3 -m pytest voxanalysis/vox-analysis/engine/tests/test_scoring.py -q 2>&1 | tail -3
```

Run the re-analysis (Step 2) **from `/tmp/driftfix`** — that worktree is on the
fix branch, so the corrected JSONs you write into its
`voxanalysis/archive/scratch-analyses/` overwrite the withheld stubs, and you
commit + push from there. When finished:

```bash
cd ~/.openclaw/mary-workspace/aaroncodex && git worktree remove /tmp/driftfix
```

> Prefer to work in the canonical checkout instead of a worktree? Only if it is
> clean: `git status --porcelain` must print nothing. Then `git fetch` +
> `git checkout claude/voiceassist-plugin-planning-krhz0d` (a normal checkout,
> **not** `reset --hard`). If it prints anything, stash or commit first.

## Step 2 — re-analyse each take from its isolated vocal stem

Run your normal one-RoFormer-model pipeline on each take below, using the **same
window and take-context** as the original. Each produces a fresh
`technical_score` (a real drift, or `None` + pitch-stability dropped if the take
genuinely has too few long notes). Copy each corrected JSON over its file in
`voxanalysis/archive/scratch-analyses/` — this replaces the withheld stub.

**Must re-analyse (drift fabricated to 0.0):**

| Singer | Take |
|---|---|
| Aaron | `2024-09-20-aaron-bust-a-move-take-001` |
| Aaron | `2026-04-29-aaron-lonely-boy-take-001` |
| Aaron | `2026-05-07-aaron-ellis-play-that-funky-music-take-001` |
| Aaron | `2026-06-13-aaron-come-out-and-play-take-001` |
| Aaron | `2026-07-02-aaron-funky-cold-medina-take-001` |
| Aaron | `2026-07-08-aaron-funky-cold-medina-take-001` |
| Rilda | `2026-07-09-rilda-sexy-eyes-take-001` |
| Rilda | `2026-07-10-rilda-sexy-eyes-take-001` |
| Rilda | `2026-07-17-rilda-hot-stuff-take-001` |
| Hot Chocolate | `2026-08-06-hot-chocolate-you-sexy-thing-reference` |

**Precautionary (near-zero drift on short-note takes — confirm):**

| Singer | Take |
|---|---|
| Aaron | `2020-01-01-aaron-hang-on-sloopy-take-001` |
| Aaron | `2026-07-07-aaron-you-sexy-thing-take-002` |

**Done — PR #57:** `2026-08-15-aaron-bust-a-move-take-001` re-analysed (5.9 / 6.4),
merged to `main`. ✅

**Held for PR #58 — `2026-07-16-aaron-open-road-take-001`.** This take was
analysed on the **pre-fix engine** (its JSON has no `drift_measurable_notes` /
`drift_note` field, and 46 short notes carry a fabricated `0.0` drift), so its
current 8.4 / 9.1 and pitch-stability 10.0 are **inflated**. Re-analyse it on the
fixed engine and commit the corrected JSON onto the PR #58 branch
`codex/live-bramble-bay-originals-2026-07-16-corrected`. The other two takes on
that PR (`that-s-my-flavor`, `carved-from-stone`) were already run on the fixed
engine and are fine — leave them. **PR #58 stays held until Open Road is
corrected**, then all three merge together.

## Step 3 — regenerate the score tables (ONLY after Step 2)

```bash
python3 docs/score-metrics/retire_legacy_scores.py && \
python3 docs/score-metrics/rescore_all.py && \
python3 tools/score_preflight.py     # must exit 0
```

---

## Two cautions (they matter)

- **Do NOT run `rescore_all.py` before Step 2.** It re-derives scores from the
  still-buggy stored drift metric and would reproduce the inflation.
- **Expect these scores to come out lower.** The two fake 10s come off — that's
  correct, not a regression. Long/medium-note takes across the rest of the
  archive are unchanged (the drift maths is identical for notes long enough to
  measure).

## Notes

- The fix currently lives on branch `claude/voiceassist-plugin-planning-krhz0d`
  (PR #54), not yet on `main` — Step 1 pulls the branch directly, so you're
  unblocked either way.
- When Bust a Move (PR #57) is re-run, send the real number and PR #57 can merge.
