# Re-analyse queue — takes measured while Praat was unavailable

Some takes were analysed on a host where **praat-parselmouth was not installed**.
On those, the clinical voice metrics (jitter/shimmer/HNR/CPPS) don't compute, so
the engine drops the **voice_quality** component and scores on **6 of 7**
(`coverage: partial`, medium confidence). Aaron's voice_quality is consistently
his *strongest* component, so a partial score reads meaningfully lower than the
true full-coverage number.

These are **not** provenance-broken — they're on the current pack and measurement
era, and their scores are correct *for 6 components*. They just need re-running
once Praat is restored to gain the 7th.

## How to clear an item
1. Confirm `praat-parselmouth` is installed (it's in
   `voxanalysis/vox-analysis/engine/requirements.txt`; see the env-completion
   handoff).
2. Re-analyse the take from its RoFormer vocal stem on the current engine.
3. Verify the new JSON has `technical_score.coverage == "full"` and a scored
   `voice_quality` component, current pack `4c52716b5aed` + measurement
   `28e854af22ea`.
4. Commit the corrected JSON and tick it off below.

## Queue

| Take | Analysed | Partial score (6/7) | Branch | Status |
|---|---|---|---|---|
| `2026-09-13-aaron-you-give-love-a-bad-name-take-001` | 13 Sep 2026 | 6.0 / 5.9, medium conf | `codex/dropbox-vocal-batch-2026-09-12` | ✅ **CLEARED** — Praat restored, re-run `3703f3d`: now full coverage, voice_quality 9.73, overall 6.7 / cf 5.9, high confidence |

**Queue is empty** as of the Praat env install. Any future take analysed on a
host without praat-parselmouth would reopen this list — the tell is
`technical_score.coverage == "partial"` with `voice_quality` in
`components_unscored`.

> Note: the 09-12 batch (15 takes) was analysed while Praat *was* working — those
> carry full voice_quality and are not in this queue. The gap opened between
> 09-12 and 09-13, so check any take analysed from 09-13 onward until the
> env-completion install is confirmed.
