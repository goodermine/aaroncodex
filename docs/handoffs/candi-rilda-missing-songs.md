# Candi task — analyse Rilda's un-analysed host songs

Rilda has ~11 recordings on the host that have never been through the engine.
Separate them with the **pinned RoFormer** model and analyse them, exactly like
the nine-takes migration you just finished. Additive only — you are creating new
analysis files, not changing any existing one.

## Which songs (host → repo)

Already in the repo — **do NOT redo these**:
Let's Stay Together (home), This Masquerade, She's Not There, Dreams, You Sexy Thing.

**To separate + analyse** (on the host):

- At Last
- Black Velvet
- Blue Bayou
- Hot Stuff
- Make It With You
- Moondance
- Moonlight Serenade  (there are ~3 takes — do each)
- On The Radio
- Sexy Eyes  (there are ~2 takes — do each)
- Sway With My Heart

**Skip for now — needs a name from Rilda before scoring:**
- "Unidentified Song"

If you find any Rilda recording on the host that is not in either list above,
STOP and list it — do not guess the title. (The host list came from an earlier
audit and may be incomplete; This Masquerade is in the repo but wasn't on that
audit list, so the audit is not the whole truth.)

## The recipe — pinned RoFormer only

Do NOT use UVR_MDXNET_Main or the audio-separator default. The one pinned model
is `vocals_mel_band_roformer.ckpt` (Mel-Band RoFormer, MIT). `batch_stems.sh`
already defaults to it via `SEP_MODEL` — just run it:

```
# 1. separate every Rilda original into vocal stems (RoFormer)
bash voxanalysis/vox-analysis/engine/tools/stems/batch_stems.sh \
    --input <dir with Rilda originals> --output <stems_out>

# 2. analyse the stems (prefers the stem, never mixes separators)
python3 tools/analyse_takes.py <stems_out> --write --force

# 3. land the new analyses in the scored archive, named like the others:
#    2026-07-28-rilda-<song>-take-001_analysis.json
#    (analyse_takes.py writes there; just confirm the names match the convention)

# 4. refresh the score tables and verify
python3 docs/score-metrics/retire_legacy_scores.py
python3 docs/score-metrics/rescore_all.py
python3 tools/score_preflight.py --update && python3 tools/score_preflight.py
```

## Before you commit — checks that must pass

1. `python3 tools/score_preflight.py` exits **0** ("one separation model
   throughout: RoFormer"). If it complains about a separator, a stem slipped
   through on the wrong model — fix before committing.
2. `python3 tools/check_take_integrity.py` — advisory. If any new Rilda take
   matches a reference **original's** song AND duration to a fraction of a
   second (like the Andy Gibb 0.02s case), FLAG it and do not trust the score
   until Rilda confirms it's her singing. Her "She's Not There" already tripped
   this once (0.07s off the Zombies original) — apply the same caution to any
   new near-exact match.
3. Do **NOT** commit any audio (originals or stems). Analyses (JSON) only.

## Branch

Base this on the latest **main**. It is separate from your
`codex/roformer-migration-v2` nine-takes branch — these are all new files, so
they won't conflict. Commit the new analyses + refreshed score tables together
with a clear message (e.g. "Analyse Rilda's un-analysed host songs (RoFormer)").
