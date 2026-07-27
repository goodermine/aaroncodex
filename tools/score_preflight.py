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

    print("\nPREFLIGHT PASSED — safe to score and publish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
