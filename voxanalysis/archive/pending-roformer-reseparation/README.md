# Pending RoFormer re-separation

These 9 singer takes were still on the old **UVR_MDXNET_Main** separator after
Candi's migration pass — they were missed. They are held here, OUT of the scored
archive, so `scratch-analyses/` is uniformly RoFormer and preflight passes. They
are not lost: they carry full MDX-NET analyses and simply need re-separating with
the pinned RoFormer model, re-analysing, and moving back into `scratch-analyses/`.

**Includes Aaron's Captain Cook benchmark take** — the one discussed all session.

To complete (on the machine with the audio + separator):
```
bash voxanalysis/vox-analysis/engine/tools/stems/batch_stems.sh \
    --input <dir with these 9 originals> --output <stems_out>
python3 tools/analyse_takes.py <stems_out> --write --force
# move the refreshed analyses back:
mv voxanalysis/archive/pending-roformer-reseparation/*_analysis.json \
   voxanalysis/archive/scratch-analyses/   # (after they are regenerated there)
python3 docs/score-metrics/retire_legacy_scores.py
python3 docs/score-metrics/rescore_all.py
python3 tools/score_preflight.py --update && python3 tools/score_preflight.py
```
