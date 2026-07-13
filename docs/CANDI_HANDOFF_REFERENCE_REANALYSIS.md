# HANDOFF: Candi — Re-analyse the Reference Pack with the Current Engine

Task type: batch re-analysis on the local machine, pushed to
`vox-cloud-alpha` `main`. Prerequisite: pull `main` at or after PR #12
(`e26213c` — includes the prescription-map parser fixes).

## Why

All 38 reference JSONs in `calibration/references/` were produced by
earlier engine versions. None contain the newer measurements: CPPS,
strain, singer's formant, onsets, harmonics, breath, registers, range
map, vowel space, or the persisted `pitch.f0_contour`. Until the pack is
re-analysed:

- **Rubric v3 is blocked** — the new metrics can't join the calibrated
  score without professional anchor distributions.
- **Melody-match against originals doesn't work** — `compare_takes.py`
  needs `f0_contour` in the reference JSON.
- New prescription triggers fall back to threshold severity instead of
  pro-percentile severity.

## The task

1. **Locate the source audio** for each of the 38 references (the
   original downloads in the media/inbound and reference folders). If any
   track's audio is missing, report it — do NOT keep the stale JSON
   silently; the pack membership must be explicit.

2. **Re-analyse each with the current engine**, exactly as reference
   analyses are normally run:
   ```bash
   python analyse_song.py "<reference audio>" --name "Reference" --separate-stems --calibration none
   ```
   Notes:
   - `--calibration none` — references must be measured, not scored
     against themselves (the technical_score in a reference JSON is
     informational only, but keep it uncontaminated).
   - Male-voice tracks: add `--formant-ceiling 5000`.
   - Stem separation runs fresh each time; expect a few minutes per track.

3. **Replace in place**: each new JSON overwrites the SAME filename in
   `backend/voxai-local-analysis/calibration/references/`. No renames, no
   additions, no removals without reporting. Pack membership stays
   identical (38 tracks) unless audio is missing (report those).

4. **Verify completeness** before committing — every reference must have
   the new fields:
   ```bash
   python3 - <<'EOF'
   import json, glob
   bad = []
   for p in sorted(glob.glob('calibration/references/*.json')):
       d = json.load(open(p))
       ok = (d.get('pitch', {}).get('f0_contour')
             and d.get('voice_quality', {}).get('cpps_db') is not None
             and d.get('resonance', {}).get('singers_formant_ratio_db') is not None
             and 'onsets' in d and 'harmonics' in d)
       if not ok:
           bad.append(p)
   print('incomplete:', bad or 'none — all references current')
   EOF
   ```

5. **Do NOT rebuild `calibration/pro_reference.json` yet.** The
   calibration builder needs extending to collect the new metrics first —
   that happens on the cloud side after your push (rubric v3 work).
   Rebuilding now with the current builder would produce a valid but
   incomplete calibration; leave the existing one in place.

6. **Commit and push to `main`** with a message like
   `data: re-analyse 38-reference pack with current engine`, then reply
   with: how many re-analysed, any missing audio, any capture-risk flags
   raised, and total runtime.

## After this lands (cloud side, not yours)

- `build_calibration.py` gets the new metric paths (CPPS, singer's
  formant, strain rate, onset consistency, breath sag).
- `pro_reference.json` is rebuilt from your new JSONs.
- Rubric v3 is designed and validated with the same gates as v2: the pack
  must score ~9 median against its own calibration, the flawed synthetic
  control must stay low, and every anchor change is documented — nothing
  moves silently.
