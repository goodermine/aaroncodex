"""Re-score EVERY archived analysis with the current engine (rubric v4).

Writes a full snapshot of all singer takes (and, as a calibration sanity check,
the professional references) under docs/score-metrics/. The archived files carry
whatever score was baked in at capture time; this recomputes each against the
live compute_technical_score(), so the table always reflects today's rubric.

Run:  python3 docs/score-metrics/rescore_all.py
"""
import json, re, glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "voxanalysis/vox-analysis/engine"))
from analyse_song import compute_technical_score, load_calibration, DEFAULT_CALIBRATION_PATH  # noqa: E402

ARCH = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")
OUTDIR = os.path.join(ROOT, "docs/score-metrics")
cal = load_calibration(DEFAULT_CALIBRATION_PATH)
SINGERS = ("aaron", "rilda", "chris", "leo")
STAMP = "2026-07-25"


def is_take(name): return any(s in name.lower() for s in SINGERS)
def date_of(name):
    m = re.search(r"20\d\d-\d\d-\d\d", name); return m.group(0) if m else "0000-00-00"
def singer(name):
    for s in SINGERS:
        if s in name.lower(): return s
    return "reference"
def song(name):
    b = re.sub(r"_analysis$", "", name)
    b = re.sub(r"20\d\d-\d\d-\d\d-?", "", b)
    b = re.sub(r"^(aaron-g-|aaron-|rilda-|chris-|leo-)", "", b)
    b = re.sub(r"-normalized|-song-cut|-reference", "", b)
    return b.strip("-")


def score_row(f):
    name = os.path.basename(f).replace("_analysis.json", "")
    d = json.load(open(f))
    old = d.get("technical_score") or {}
    ts = compute_technical_score(d, cal) or {}
    comp = {k: v.get("score") for k, v in (ts.get("components") or {}).items()}
    inton = d.get("intonation", {}); vq = d.get("voice_quality", {})
    vib = d.get("vibrato", {}); phr = d.get("phrasing", {}); dyn = d.get("dynamics", {})
    return {
        "take": name, "singer": singer(name), "song": song(name), "date": date_of(name),
        "n_notes": inton.get("n_notes"),
        "old_baked_overall": old.get("overall_score_0_to_10"),
        "overall_v4": ts.get("overall_score_0_to_10"),
        "capture_fair_v4": ts.get("capture_fair_score_0_to_10"),
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
    "engine": (take_rows[0]["provenance"] if take_rows else "deterministic_rubric_v4"),
    "calibration": {"active": cal is not None, "n_references": cal.get("n_references") if cal else 0},
    "source": "voxanalysis/archive/scratch-analyses (re-scored with current engine)",
    "aggregate": {
        "takes": {"n": len(take_rows), "overall_v4": stats([r["overall_v4"] for r in take_rows]),
                  "capture_fair_v4": stats([r["capture_fair_v4"] for r in take_rows]),
                  "dynamics": stats([r["components"].get("dynamics_expression") for r in take_rows])},
        "references": {"n": len(ref_rows), "overall_v4": stats([r["overall_v4"] for r in ref_rows])},
    },
    "takes": take_rows, "references": ref_rows,
}
os.makedirs(OUTDIR, exist_ok=True)
json.dump(out, open(os.path.join(OUTDIR, f"all-takes-rescore-v4-{STAMP}.json"), "w"), indent=2)

# ---- markdown ----
def comp(r, k): return r["components"].get(k, "–")
md = [f"# All takes — re-scored with the current engine (rubric v4, {STAMP})", "",
      f"Every archived take re-scored with **{out['engine']}** "
      f"(calibration active, {out['calibration']['n_references']} pro references). "
      "`baked` is the score stored in the archived file at capture time; `v4` is the current recompute. "
      "`cf` = capture-fair (voice_quality **and** dynamics excluded — the capture-robust components).", "",
      "## Singer takes", "",
      f"Overall v4: min {out['aggregate']['takes']['overall_v4']['min']} · "
      f"max {out['aggregate']['takes']['overall_v4']['max']} · "
      f"mean {out['aggregate']['takes']['overall_v4']['mean']}. "
      f"Dynamics component now spreads {out['aggregate']['takes']['dynamics']['min']}–"
      f"{out['aggregate']['takes']['dynamics']['max']} (was a flat 10.0 for every take in v3).", "",
      "| singer | song | notes | baked | **v4** | cf | conf | inton | pitch | voice | vib | dyn | phrase |",
      "|---|---|--:|--:|--:|--:|:--|--:|--:|--:|--:|--:|--:|"]
for r in take_rows:
    md.append(f"| {r['singer']} | {r['song']} | {r['n_notes']} | {r['old_baked_overall']} | "
              f"**{r['overall_v4']}** | {r['capture_fair_v4']} | {r['confidence']} | "
              f"{comp(r,'intonation_accuracy')} | {comp(r,'pitch_stability')} | {comp(r,'voice_quality')} | "
              f"{comp(r,'vibrato_control')} | {comp(r,'dynamics_expression')} | {comp(r,'phrase_control')} |")
md += ["", "## Professional references (calibration sanity check)", "",
       f"Overall v4: min {out['aggregate']['references']['overall_v4'].get('min')} · "
       f"max {out['aggregate']['references']['overall_v4'].get('max')} · "
       f"mean {out['aggregate']['references']['overall_v4'].get('mean')} — pros should sit near the top.", "",
       "| reference | v4 | cf | inton | pitch | voice | vib | dyn | phrase |",
       "|---|--:|--:|--:|--:|--:|--:|--:|--:|"]
for r in ref_rows:
    md.append(f"| {r['song']} | **{r['overall_v4']}** | {r['capture_fair_v4']} | "
              f"{comp(r,'intonation_accuracy')} | {comp(r,'pitch_stability')} | {comp(r,'voice_quality')} | "
              f"{comp(r,'vibrato_control')} | {comp(r,'dynamics_expression')} | {comp(r,'phrase_control')} |")
open(os.path.join(OUTDIR, f"all-takes-rescore-v4-{STAMP}.md"), "w").write("\n".join(md) + "\n")
print(f"takes={len(take_rows)} refs={len(ref_rows)}")
print("takes overall_v4", out['aggregate']['takes']['overall_v4'])
print("takes dynamics  ", out['aggregate']['takes']['dynamics'])
print("refs  overall_v4", out['aggregate']['references']['overall_v4'])
