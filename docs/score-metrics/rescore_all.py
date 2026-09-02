"""Re-score EVERY archived analysis with the current engine.

Writes a full snapshot of all singer takes (and, as a calibration sanity check,
the professional references) under docs/score-metrics/. Scores from superseded
rubrics are retired from the archive by retire_legacy_scores.py, so every number
produced here is a fresh compute against the live compute_technical_score() —
the table always reflects today's rubric and carries no stale scores.

Run:  python3 docs/score-metrics/rescore_all.py
"""
import json, re, glob, os, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "voxanalysis/vox-analysis/engine"))
from analyse_song import (  # noqa: E402
    ALL_COMPONENTS, RUBRIC_VERSION, compute_technical_score, load_calibration,
    scale_mismatch, measurement_era, pack_measurement_era,
    DEFAULT_CALIBRATION_PATH)

ARCH = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")
OUTDIR = os.path.join(ROOT, "docs/score-metrics")
cal = load_calibration(DEFAULT_CALIBRATION_PATH)
# Aaron and Aaron G are DIFFERENT SINGERS and must never be merged: Vienna,
# 1973 and If You Could Read My Mind are Aaron G's. Matching is on a token
# boundary, longest name first, because neither naive approach works:
#   plain substring "aaron"   -> swallows every aaron-g take into Aaron
#   plain substring "aaron-g" -> swallows "aaron-goodbye-s-been-good-to-you"
# The trailing hyphen is what separates "aaron-g-vienna" from "aaron-goodbye".
#
# A DUET is its own singer, listed before either half of it. One stem carrying
# two voices measures neither of them: the Burning Down the House duet was filed
# under Aaron and counted in his solo average, with its song name mangled to
# "and-rilda-burning-down-the-house". The archive's own artist_name field ("Aaron
# and Rilda") is the ground truth, and test_singer_identity.py checks against it.
SINGERS = ("aaron-and-rilda", "aaron-g", "aaron", "rilda", "chris", "leo")


def _sings(name, token):
    return re.search(rf"(?:^|-){re.escape(token)}-", name.lower()) is not None
# Rubric label and filenames come from the ENGINE, never a literal: a
# hardcoded "v4" here wrote v5 scores into a file named -v4- on the first
# rubric bump, which is precisely the stale-label failure this repo guards.
RUBRIC = RUBRIC_VERSION
STAMP = os.environ.get("RESCORE_STAMP") or date.today().isoformat()


def is_take(name): return any(_sings(name, s) for s in SINGERS)
def date_of(name):
    m = re.search(r"20\d\d-\d\d-\d\d", name); return m.group(0) if m else "0000-00-00"
def singer(name):
    for s in SINGERS:                      # longest first: aaron-g before aaron
        if _sings(name, s): return s
    return "reference"
def song(name):
    b = re.sub(r"_analysis$", "", name)
    b = re.sub(r"20\d\d-\d\d-\d\d-?", "", b)
    b = re.sub(r"^(" + "|".join(s + "-" for s in SINGERS) + r")", "", b)
    b = re.sub(r"-normalized|-song-cut|-reference", "", b)
    return b.strip("-")


def score_row(f):
    name = os.path.basename(f).replace("_analysis.json", "")
    d = json.load(open(f))
    old = d.get("technical_score") or {}
    # A retired score can represent measurements that are known to be
    # contaminated and cannot yet be regenerated from source audio.  Running
    # those stored measurements back through the current scorer would recreate
    # the very number the retirement stub is meant to withhold (for example the
    # short-note 0.0-cent drift artefact).  Keep the row for audit/raw metrics,
    # but never manufacture a replacement score from a retired record.
    retired = old.get("status") == "retired_legacy_score"
    # Measurement-era guard (see rescore_archive_inplace.py): inputs from a
    # different era than the pack's anchors are withheld from the tables, never
    # scored against the wrong ruler.
    cross_era = (not retired) and scale_mismatch(d, cal)
    ts = {} if (retired or cross_era) else (compute_technical_score(d, cal) or {})
    comp = {k: v.get("score") for k, v in (ts.get("components") or {}).items()}
    inton = d.get("intonation", {}); vq = d.get("voice_quality", {})
    vib = d.get("vibrato", {}); phr = d.get("phrasing", {}); dyn = d.get("dynamics", {})
    return {
        "take": name, "singer": singer(name), "song": song(name), "date": date_of(name),
        "n_notes": inton.get("n_notes"),
        "prior_score_status": ("retired_legacy" if retired
                               else ("current" if old.get("identity") else "none")),
        "score_status": "withheld" if (retired or cross_era) else "current",
        "withheld_reason": (old.get("reason") if retired else
                            (f"measured on {measurement_era(d)}, pack built from "
                             f"{pack_measurement_era(cal)} — re-analyse on the current engine")
                            if cross_era else None),
        "overall": ts.get("overall_score_0_to_10"),
        "capture_fair": ts.get("capture_fair_score_0_to_10"),
        "coverage": ts.get("coverage"),
        "components_unscored": ts.get("components_unscored") or [],
        "confidence": ts.get("confidence"),
        "provenance": (ts.get("provenance") or "").split(" —")[0],
        "components": comp,
        "raw": {
            "median_abs_dev_cents": inton.get("median_abs_deviation_cents"),
            "median_intra_note_drift_cents": inton.get("median_intra_note_drift_cents"),
            "pct_within_25c": inton.get("pct_notes_within_25_cents"),
            "jitter_pct": vq.get("jitter_local_percent_median"),
            "shimmer_pct": vq.get("shimmer_local_percent_median"),
            "hnr_db": vq.get("hnr_db_median"),
            "vibrato_pct_notes": vib.get("pct_notes_with_vibrato"),
            "dyn_phrase_spread_db": dyn.get("phrase_level_spread_db"),
            "dyn_effective_range_db": dyn.get("effective_dynamic_range_db"),
            "median_phrase_s": phr.get("median_phrase_s"),
            # Entry accuracy travels with the raw measures, never the scores:
            # it is a diagnostic and is not part of any /10. Tracked here so the
            # monthly progress check can trend it like cents and dB.
            "onsets_pct_clean": (d.get("onsets") or {}).get("pct_clean"),
            "onsets_pct_scooped": (d.get("onsets") or {}).get("pct_scooped"),
            "onsets_pct_overshot": (d.get("onsets") or {}).get("pct_overshot"),
            "entry_accuracy_reliability": (d.get("entry_accuracy") or {}).get("reliability"),
        },
    }


allf = glob.glob(ARCH + "/*_analysis.json")
takes = sorted([f for f in allf if is_take(os.path.basename(f))],
               key=lambda f: (singer(os.path.basename(f)), date_of(os.path.basename(f)), os.path.basename(f)))
refs = sorted([f for f in allf if not is_take(os.path.basename(f))],
              key=lambda f: os.path.basename(f))

take_rows = [score_row(f) for f in takes]
ref_rows = [score_row(f) for f in refs]


def stats(x):
    x = [v for v in x if v is not None]
    return {"min": round(min(x), 1), "max": round(max(x), 1),
            "mean": round(sum(x) / len(x), 2), "spread": round(max(x) - min(x), 1)} if x else {}


out = {
    "generated": STAMP,
    "rubric": RUBRIC,
    "engine": (take_rows[0]["provenance"] if take_rows else f"deterministic_rubric_{RUBRIC}"),
    "calibration": {"active": cal is not None, "n_references": cal.get("n_references") if cal else 0},
    "source": "voxanalysis/archive/scratch-analyses (re-scored with current engine)",
    "aggregate": {
        "takes": {"n": len(take_rows), "overall": stats([r["overall"] for r in take_rows]),
                  "capture_fair": stats([r["capture_fair"] for r in take_rows]),
                  "dynamics": stats([r["components"].get("dynamics_expression") for r in take_rows])},
        "references": {"n": len(ref_rows), "overall": stats([r["overall"] for r in ref_rows])},
    },
    "takes": take_rows, "references": ref_rows,
}
os.makedirs(OUTDIR, exist_ok=True)
json.dump(out, open(os.path.join(OUTDIR, f"all-takes-rescore-{RUBRIC}-{STAMP}.json"), "w"), indent=2)

# ---- markdown ----
def comp(r, k): return r["components"].get(k, "–")
take_stats = out["aggregate"]["takes"]["overall"]
take_dynamics_stats = out["aggregate"]["takes"]["dynamics"]
md = [f"# All takes — re-scored with the current engine (rubric {RUBRIC}, {STAMP})", "",
      f"Every eligible archived take re-scored with **{out['engine']}** "
      f"(calibration active, {out['calibration']['n_references']} pro references). "
      "Scores from superseded rubrics have been retired from the archive "
      "(retire_legacy_scores.py), so every numeric score here is a current recompute. "
      "Retired or source-blocked records remain visible as **withheld** rows and are not "
      "recomputed from contaminated stored measurements. `cf` = capture-fair "
      "(voice_quality **and** dynamics "
      "excluded — the capture-robust components; **breath** is deliberately kept in, "
      "because air running out is the singer, not the room).", "",
      f"`breath` is new in {RUBRIC}. A blank means the analysis predates "
      "`analyse_breath()` and has no phrase-sag data, so it scored on "
      f"{len(ALL_COMPONENTS) - 1} of {len(ALL_COMPONENTS)} components (`coverage: partial`; "
      "weights renormalised). Re-analyse those takes with the current engine to close "
      "the gap — the difference is at most ~0.25 points, which is why they are still "
      "shown rather than withheld.", "",
      "## Singer takes", "",
      f"Overall: min {take_stats.get('min', 'n/a')} · "
      f"max {take_stats.get('max', 'n/a')} · "
      f"mean {take_stats.get('mean', 'n/a')}. "
      f"Dynamics component spreads {take_dynamics_stats.get('min', 'n/a')}–"
      f"{take_dynamics_stats.get('max', 'n/a')} (was a flat 10.0 for every take in v3).", "",
      f"Full coverage: {sum(1 for r in take_rows if r['coverage'] == 'full')}/{len(take_rows)} takes.", "",
      f"| singer | song | notes | **{RUBRIC}** | cf | conf | inton | pitch | voice | vib | dyn | phrase | breath |",
      "|---|---|--:|--:|--:|:--|--:|--:|--:|--:|--:|--:|--:|"]
for r in take_rows:
    if r["score_status"] == "withheld":
        md.append(f"| {r['singer']} | {r['song']} | {r['n_notes']} | "
                  "**withheld** | – | – | – | – | – | – | – | – | – |")
    else:
        md.append(f"| {r['singer']} | {r['song']} | {r['n_notes']} | "
                  f"**{r['overall']}** | {r['capture_fair']} | {r['confidence']} | "
                  f"{comp(r,'intonation_accuracy')} | {comp(r,'pitch_stability')} | {comp(r,'voice_quality')} | "
                  f"{comp(r,'vibrato_control')} | {comp(r,'dynamics_expression')} | {comp(r,'phrase_control')} | "
                  f"{comp(r,'breath_support')} |")
md += ["", "## Professional references (calibration sanity check)", "",
       f"Overall: min {out['aggregate']['references']['overall'].get('min')} · "
       f"max {out['aggregate']['references']['overall'].get('max')} · "
       f"mean {out['aggregate']['references']['overall'].get('mean')} — pros should sit near the top.", "",
       f"| reference | {RUBRIC} | cf | inton | pitch | voice | vib | dyn | phrase | breath |",
       "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|"]
for r in ref_rows:
    if r["score_status"] == "withheld":
        md.append(f"| {r['song']} | **withheld** | – | – | – | – | – | – | – | – |")
    else:
        md.append(f"| {r['song']} | **{r['overall']}** | {r['capture_fair']} | "
                  f"{comp(r,'intonation_accuracy')} | {comp(r,'pitch_stability')} | {comp(r,'voice_quality')} | "
                  f"{comp(r,'vibrato_control')} | {comp(r,'dynamics_expression')} | {comp(r,'phrase_control')} | "
                  f"{comp(r,'breath_support')} |")
open(os.path.join(OUTDIR, f"all-takes-rescore-{RUBRIC}-{STAMP}.md"), "w").write("\n".join(md) + "\n")
print(f"takes={len(take_rows)} refs={len(ref_rows)}")
print("takes overall", out['aggregate']['takes']['overall'])
print("takes dynamics  ", out['aggregate']['takes']['dynamics'])
print("refs  overall", out['aggregate']['references']['overall'])
