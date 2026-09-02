"""Preflight: prove the engine you are about to score with is the current one.

Run this BEFORE producing any `/10` for a singer. It fails loudly (exit 1) if the
running engine does not match the score contract committed in this repo — which
is exactly how stale-rubric scores (the v1 5.1s, the withdrawn 9.5) reached real
people.

    python3 tools/score_preflight.py            # check, exit 1 on mismatch
    python3 tools/score_preflight.py --update   # re-pin the contract (maintainers)

Checks:
  1. the engine imports, and its rubric + fingerprints match SCORE_CONTRACT.json
  2. the professional calibration pack is loaded (uncalibrated => harsh scores)
  3. no archived analysis still carries a quotable legacy score
"""
import json, glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "voxanalysis/vox-analysis/engine"))
CONTRACT = os.path.join(ROOT, "docs/score-metrics/SCORE_CONTRACT.json")
ARCHIVE = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")

FAIL, WARN, OK = "FAIL", "WARN", "ok  "


def running_identity():
    import analyse_song as A
    cal = A.load_calibration(A.DEFAULT_CALIBRATION_PATH)
    ident = A.score_identity({}, cal)
    return A, cal, {k: ident[k] for k in
                    ("contract", "rubric", "rubric_fingerprint",
                     "calibrated", "calibration_references", "calibration_fingerprint")}


def main() -> int:
    problems = []
    try:
        A, cal, ident = running_identity()
    except Exception as exc:
        print(f"{FAIL}  engine will not import: {exc}")
        print("\n      Fix: run from the repo root with the engine's deps available.")
        return 1

    if "--update" in sys.argv:
        os.makedirs(os.path.dirname(CONTRACT), exist_ok=True)
        with open(CONTRACT, "w") as fh:
            json.dump(ident, fh, indent=2)
            fh.write("\n")
        print(f"{OK}  contract re-pinned to {ident['rubric']} "
              f"(build {ident['rubric_fingerprint']})")
        return 0

    # 1. engine matches the committed contract
    if not os.path.isfile(CONTRACT):
        print(f"{WARN}  no committed contract at {os.path.relpath(CONTRACT, ROOT)} "
              f"— running {ident['rubric']}; pin it with --update")
    else:
        with open(CONTRACT) as fh:
            expected = json.load(fh)
        for key in ("contract", "rubric", "rubric_fingerprint", "calibration_fingerprint"):
            if expected.get(key) != ident.get(key):
                problems.append(
                    f"{key}: repo expects {expected.get(key)!r}, "
                    f"this engine has {ident.get(key)!r}")
        if problems:
            print(f"{FAIL}  the engine you are running is NOT the repo's engine:")
            for p in problems:
                print(f"        - {p}")
            print("\n      DO NOT publish a score from this engine. Fix:")
            print("        git fetch origin main && git merge --ff-only origin/main")
            print("      then re-run this preflight. If you maintain the rubric and this")
            print("      change is intentional, re-pin with --update and commit it.")
            return 1
        print(f"{OK}  engine matches the repo contract: {ident['rubric']} "
              f"(build {ident['rubric_fingerprint']})")

    # 2. calibration present
    if not ident["calibrated"]:
        print(f"{FAIL}  no professional calibration pack loaded — scores would use "
              f"theoretical anchors and read ~2-3 points too harsh.")
        print("      DO NOT publish a score. Check "
              "voxanalysis/vox-analysis/engine/calibration/pro_reference.json")
        return 1
    print(f"{OK}  calibration active: {ident['calibration_references']} pro references")

    # 3. no quotable legacy scores left in the archive
    stale = []
    for path in sorted(glob.glob(os.path.join(ARCHIVE, "*_analysis.json"))):
        try:
            with open(path) as fh:
                score = (json.load(fh) or {}).get("technical_score")
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(score, dict) and score.get("status") != "retired_legacy_score" \
                and A.is_legacy_score(score):
            stale.append(os.path.basename(path))
    if stale:
        print(f"{FAIL}  {len(stale)} archived analysis(es) still carry a quotable "
              f"legacy score:")
        for name in stale[:5]:
            print(f"        - {name}")
        if len(stale) > 5:
            print(f"        … and {len(stale) - 5} more")
        print("\n      Fix: python3 docs/score-metrics/retire_legacy_scores.py")
        return 1
    print(f"{OK}  no legacy scores left in the archive")

    # 3b. one calibration pack across every stored score.
    #
    # is_legacy_score() checks the contract and the rubric, and an analysis
    # scored against an OLDER calibration pack passes both — so check 3 above
    # waves it through. score_conflict() does not: it refuses to compare two
    # scores anchored to different packs. That contradiction sat in this archive
    # unnoticed — 113 of 182 analyses stored pack 0da01ef1e30f while the pinned
    # contract said fb035034bebd, so preflight said "safe to publish" for a
    # leaderboard, an average and a cross-era comparison that score_conflict()
    # would have refused take by take. The two packs disagreed by up to 0.5 on
    # the overall. Per take that is small; across a comparison it is the whole
    # effect. Anything reading a STORED score (tools/ranked_takes.py,
    # tools/show_results.py, the singer PDFs) is exposed, because only
    # rescore_all.py recomputes and it writes tables, not the archive.
    packs = {}
    for path in sorted(glob.glob(os.path.join(ARCHIVE, "*_analysis.json"))):
        try:
            with open(path) as fh:
                score = (json.load(fh) or {}).get("technical_score")
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(score, dict) or score.get("status") == "retired_legacy_score":
            continue
        fp = (score.get("identity") or {}).get("calibration_fingerprint")
        packs.setdefault(fp, []).append(os.path.basename(path))

    stale_packs = {fp: files for fp, files in packs.items()
                   if fp != ident["calibration_fingerprint"]}
    if stale_packs:
        n = sum(len(f) for f in stale_packs.values())
        print(f"{FAIL}  {n} archived score(s) are anchored to a superseded "
              f"calibration pack — score_conflict() refuses to compare them:")
        for fp, files in sorted(stale_packs.items(), key=lambda kv: -len(kv[1])):
            print(f"        - {fp}: {len(files)} analyses")
        print(f"        - {ident['calibration_fingerprint']}: "
              f"{len(packs.get(ident['calibration_fingerprint'], []))} analyses  <- pinned")
        print("\n      DO NOT publish a leaderboard, an average or any comparison.")
        print("      Fix: python3 docs/score-metrics/rescore_archive_inplace.py")
        print("           python3 docs/score-metrics/rescore_all.py")
        return 1
    print(f"{OK}  one calibration pack throughout: {ident['calibration_fingerprint']}")

    # 4. one separation model across everything that gets compared.
    #
    # Separation is upstream of every measurement, and mixing models is invisible
    # in the numbers themselves. Measured on this archive, the SAME SONG under
    # MDX-NET vs Mel-Band RoFormer moved phrase-ending sag by up to 29 points in
    # both directions — larger than the effects being diagnosed. That silently
    # invalidated a published finding before anyone noticed, because raw measures
    # carry no provenance gate the way scores do. So the check lives here.
    CAL_REFS = os.path.join(ROOT, "voxanalysis/vox-analysis/engine/calibration/references")
    seen = {}
    for path in sorted(glob.glob(os.path.join(ARCHIVE, "*_analysis.json"))
                       + glob.glob(os.path.join(CAL_REFS, "*_analysis.json"))):
        try:
            with open(path) as fh:
                data = json.load(fh) or {}
        except (OSError, json.JSONDecodeError):
            continue
        model = A._stem_model(data)
        if model:
            seen.setdefault(model, []).append(os.path.basename(path))

    if len(seen) > 1:
        print(f"{FAIL}  the archive is separated by {len(seen)} different models — "
              f"measurements across them are NOT comparable:")
        for model, files in sorted(seen.items(), key=lambda kv: -len(kv[1])):
            mark = "  <- pinned" if model == A.PINNED_SEPARATOR else ""
            print(f"        - {model}: {len(files)} analyses{mark}")
        off = [m for m in seen if m != A.PINNED_SEPARATOR]
        print(f"\n      Pinned model: {A.PINNED_SEPARATION_MODEL} "
              f"(docs/models/separation-model.md)")
        print(f"      DO NOT publish a score or compare takes until this is one model.")
        print(f"      Fix: re-separate everything on {', '.join(off)} with the pinned")
        print("      model, re-analyse, rebuild the calibration pack, then re-score:")
        print("        bash voxanalysis/vox-analysis/engine/tools/stems/batch_stems.sh …")
        print("        python3 tools/analyse_takes.py <stems> --write --force")
        print("        python3 voxanalysis/vox-analysis/engine/tools/build_calibration.py \\")
        print("            voxanalysis/vox-analysis/engine/calibration/references \\")
        print("            --out voxanalysis/vox-analysis/engine/calibration/pro_reference.json")
        print("        python3 docs/score-metrics/retire_legacy_scores.py")
        print("        python3 docs/score-metrics/rescore_all.py")
        print("        python3 tools/score_preflight.py --update   # re-pin the contract")
        return 1

    if seen and A.PINNED_SEPARATOR not in seen:
        only = next(iter(seen))
        print(f"{WARN}  everything is separated by {only}, but the repo pins "
              f"{A.PINNED_SEPARATION_MODEL}.")
        print("      Internally consistent, so comparisons are valid — but the pinned")
        print("      model is the MIT-licensed one. Migrate before shipping publicly.")
    else:
        print(f"{OK}  one separation model throughout: {A.PINNED_SEPARATOR}")

    # 5. one MEASUREMENT era across the archive, the reference pack and this engine.
    #
    # The rubric fingerprint hashes the scoring maths only, so a change to how a
    # metric is MEASURED leaves every identity field identical and score_conflict()
    # passes the two eras as comparable. That is how the 16 Aug 2026 drift fix
    # split the archive: 209 takes and all 50 references stayed on the old
    # measurement while every later take was scored against their anchors on a
    # scale ~2.5x stricter (docs/VOX_SYSTEM_REVIEW_2026-09-02.md §3.1). Analyses
    # now carry measurement_fingerprint; older ones are placed by inference from
    # the drift fix's own marker. Any mix is a FAIL.
    live_era = A.measurement_fingerprint()
    eras = {}
    for label, folder in (("archive", ARCHIVE), ("references", CAL_REFS)):
        for path in sorted(glob.glob(os.path.join(folder, "*_analysis.json"))):
            try:
                with open(path) as fh:
                    data = json.load(fh) or {}
            except (OSError, json.JSONDecodeError):
                continue
            score = data.get("technical_score")
            if label == "archive" and isinstance(score, dict) \
                    and score.get("status") in ("retired_legacy_score",
                                                "withheld_measurement_artefact"):
                continue
            eras.setdefault(A.measurement_era(data), {}).setdefault(label, []) \
                .append(os.path.basename(path))
    pack_era = cal.get("measurement_fingerprint")
    split = len(eras) > 1 or (eras and live_era not in eras) or pack_era != live_era
    if split:
        n_total = sum(len(f) for by in eras.values() for f in by.values())
        print(f"{FAIL}  the archive + reference pack span more than one MEASUREMENT era "
              f"({len(eras)} found across {n_total} analyses; this engine is {live_era}):")
        for era, by in sorted(eras.items(), key=lambda kv: -sum(len(f) for f in kv[1].values())):
            counts = ", ".join(f"{len(files)} {label}" for label, files in sorted(by.items()))
            mark = "  <- this engine" if era == live_era else ""
            print(f"        - {era}: {counts}{mark}")
        print(f"        - calibration pack built from: "
              f"{pack_era or 'unstamped (pre-Sep-2026 pack)'}"
              + ("  <- this engine" if pack_era == live_era else ""))
        print("\n      Scores from different eras are on different scales, and the pack's")
        print("      anchors only mean 'a typical pro' for takes measured the same way.")
        print("      DO NOT quote pitch_stability, a leaderboard, a trend or any cross-era")
        print("      comparison. Single-take delivery continues under the interim reading")
        print("      rule (CLAUDE.md rule 5): full results with pitch_stability withheld.")
        print("      Fix (see the review §3.1): re-analyse every analysis not on this engine")
        print("      from its retained RoFormer stem, then rebuild the pack and re-score:")
        print("        python3 tools/analyse_takes.py <stems> --write --force")
        print("        python3 voxanalysis/vox-analysis/engine/tools/build_calibration.py \\")
        print("            voxanalysis/vox-analysis/engine/calibration/references \\")
        print("            --out voxanalysis/vox-analysis/engine/calibration/pro_reference.json")
        print("        python3 docs/score-metrics/rescore_archive_inplace.py")
        print("        python3 docs/score-metrics/rescore_all.py")
        print("        python3 tools/score_preflight.py --update   # re-pin the contract")
        return 1
    print(f"{OK}  one measurement era throughout: {live_era}")

    print("\nPREFLIGHT PASSED — safe to score and publish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
