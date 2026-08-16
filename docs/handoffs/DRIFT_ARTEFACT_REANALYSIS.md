# Re-analyse the short-note takes hit by the drift artefact

**Why:** a bug flattened held-note drift to a fake `0.0` on notes shorter than the
~0.35 s smoothing window, which pinned `pitch_stability` and the straight-tone
`vibrato_control` path to 10/10 and inflated the published scores on short/fast
(rap/funk/disco) takes. The engine is now fixed (`analyse_song.py`,
`analyse_intonation` excludes unmeasurable notes; drift reports `None` when too
few notes are long enough). The fix changes the **measurement**, so the affected
takes must be **re-analysed from the source audio** — their scores cannot be
corrected on paper.

The 12 takes below have their `technical_score` **withheld** in the archive (a
status stub, measurements intact) so nothing quotes the inflated numbers until
the re-run lands.

## Must re-analyse (drift fabricated to 0.0)

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

## Precautionary (near-zero drift on short-note takes — confirm)

| Singer | Take |
|---|---|
| Aaron | `2020-01-01-aaron-hang-on-sloopy-take-001` |
| Aaron | `2026-07-07-aaron-you-sexy-thing-take-002` |

## Also

- `2026-08-15-aaron-bust-a-move-take-001` — **PR #57**, held unmerged. Re-analyse
  it on the fixed engine and re-issue its real score; then the PR can proceed.

## Steps (on the box that holds the source audio)

1. Pull the fixed engine (branch `claude/voiceassist-plugin-planning-krhz0d`,
   or `main` once merged). Confirm the fix is present:
   ```bash
   grep -n "measurable_drifts" voxanalysis/vox-analysis/engine/analyse_song.py   # should match
   python3 -m pytest voxanalysis/vox-analysis/engine/tests/test_scoring.py -q     # green
   ```
2. Re-run the engine on each take's **isolated RoFormer vocal stem** (one model
   throughout), exactly as originally analysed — same window, same take-context.
   Each produces a fresh `technical_score` (real drift, or `None` + dropped
   pitch-stability if genuinely too short).
3. Copy each corrected JSON over its file in
   `voxanalysis/archive/scratch-analyses/` (this replaces the withheld stub).
4. Regenerate the score tables **only after** the metrics are corrected:
   ```bash
   python3 docs/score-metrics/retire_legacy_scores.py
   python3 docs/score-metrics/rescore_all.py
   python3 tools/score_preflight.py            # must exit 0
   ```
   (Do NOT run `rescore_all.py` before step 3 — it re-derives from the stored
   drift metric and would reproduce the inflation.)
5. Verify provenance on each corrected take (rubric v5 / fp 7cbd02df8f62 / cal
   1d3e2991f144 / RoFormer / not legacy), then deliver the corrected numbers.

## Expected direction

Scores move **down** on these takes — two components that were pinned at 10 come
off (either measured honestly, or pitch-stability dropped with weights
renormalised). Long/medium-note takes across the rest of the archive are
unchanged: the drift computation is identical for notes long enough to measure.
