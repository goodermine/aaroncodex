# Candi — re-run the short-note takes on the drift-artefact fix

The engine bug that faked `0.0` held-note drift — which inflated `pitch_stability`
and the straight-tone `vibrato_control` path to 10/10 on short/fast (rap / funk /
disco) takes — is **fixed**. The 12 affected takes have their scores **withheld**
until they're re-analysed from the source audio, which only your box has.

---

## Step 1 — sync to the fixed engine + prove it's live

```bash
# Go to your aaroncodex checkout (adjust the path if yours differs)
cd ~/.openclaw/candi-workspace/aaroncodex && \
# Get the fixed engine. If a plain branch fetch lands on an old commit (the
# mirror lag we've seen), fetch the exact SHA instead: 5449915.
git fetch origin claude/voiceassist-plugin-planning-krhz0d && \
git checkout claude/voiceassist-plugin-planning-krhz0d && \
git reset --hard FETCH_HEAD && \
git log -1 --format='engine now on %h — %s' && \
# Prove the fix is present and the guards pass
grep -q "measurable_drifts" voxanalysis/vox-analysis/engine/analyse_song.py \
  && echo "FIX PRESENT ✅" || echo "FIX MISSING ❌ — stop, re-fetch by SHA 5449915" && \
python3 -m pytest voxanalysis/vox-analysis/engine/tests/test_scoring.py -q 2>&1 | tail -3
```

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

**Also — held for PR #57:** `2026-08-15-aaron-bust-a-move-take-001`. Re-analyse it
and send the real score; that unblocks the PR.

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
