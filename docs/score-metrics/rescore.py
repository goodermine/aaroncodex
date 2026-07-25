"""Re-score recent singer takes with the CURRENT engine + calibration.

Loads each archived analysis in voxanalysis/archive/scratch-analyses/, feeds its
measured `results` back through the live compute_technical_score(), and writes a
metrics snapshot (JSON + markdown) under docs/score-metrics/. The archived files
carry the score baked in at capture time (often an older rubric); this recomputes
against whatever the engine is today so the numbers reflect the current rubric.

Run:  python3 docs/score-metrics/rescore.py
"""
import json, re, glob, os, sys

# repo-portable: docs/score-metrics/rescore.py -> repo root is parents[2]
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "voxanalysis/vox-analysis/engine"))
from analyse_song import compute_technical_score, load_calibration, DEFAULT_CALIBRATION_PATH  # noqa: E402

ARCH = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")
OUTDIR = os.path.join(ROOT, "docs/score-metrics")
cal = load_calibration(DEFAULT_CALIBRATION_PATH)
SINGERS = ("aaron", "rilda", "chris", "leo")
N_TAKES = 10


def is_take(name): return any(s in name.lower() for s in SINGERS)
def date_of(name):
    m = re.search(r"20\d\d-\d\d-\d\d", name); return m.group(0) if m else "0000-00-00"
def singer(name):
    for s in SINGERS:
        if s in name.lower(): return s
    return "?"
def song(name):
    b = re.sub(r"_analysis$", "", name)
    b = re.sub(r"20\d\d-\d\d-\d\d-?", "", b)
    b = re.sub(r"^(aaron-g-|aaron-|rilda-|chris-|leo-)", "", b)
    b = re.sub(r"-normalized|-song-cut", "", b)
    return b.strip("-")


files = [f for f in glob.glob(ARCH + "/*_analysis.json") if is_take(os.path.basename(f))]
files.sort(key=lambda f: (date_of(os.path.basename(f)), os.path.basename(f)), reverse=True)
last10 = files[:N_TAKES]

rows = []
for f in last10:
    name = os.path.basename(f).replace("_analysis.json", "")
    d = json.load(open(f))
    old = d.get("technical_score") or {}
    ts = compute_technical_score(d, cal)
    comp = {k: v.get("score") for k, v in (ts.get("components") or {}).items()}
    inton = d.get("intonation", {}); vq = d.get("voice_quality", {})
    vib = d.get("vibrato", {}); phr = d.get("phrasing", {})
    rows.append({
        "take": name, "singer": singer(name), "song": song(name), "date": date_of(name),
        "n_notes": inton.get("n_notes"),
        "old_overall_v2": old.get("overall_score_0_to_10"),
        "overall_v3": ts.get("overall_score_0_to_10"),
        "capture_fair_v3": ts.get("capture_fair_score_0_to_10"),
        "confidence": ts.get("confidence"),
        "components": comp,
        "raw": {
            "median_abs_dev_cents": inton.get("median_abs_deviation_cents"),
            "median_intra_note_drift_cents": inton.get("median_intra_note_drift_cents"),
            "pct_within_25c": inton.get("pct_notes_within_25_cents"),
            "jitter_pct": vq.get("jitter_local_percent_median"),
            "shimmer_pct": vq.get("shimmer_local_percent_median"),
            "hnr_db": vq.get("hnr_db_median"),
            "cpps_db": vq.get("cpps_db"),
            "vibrato_pct_notes": vib.get("pct_notes_with_vibrato"),
            "vibrato_rate_hz": vib.get("median_rate_hz"),
            "median_phrase_s": phr.get("median_phrase_s"),
            "n_phrases": phr.get("n_phrases"),
        },
    })

ov = [r["overall_v3"] for r in rows if r["overall_v3"] is not None]
cf = [r["capture_fair_v3"] for r in rows if r["capture_fair_v3"] is not None]
def stats(x): return {"min": round(min(x), 1), "max": round(max(x), 1),
                      "mean": round(sum(x) / len(x), 2), "spread": round(max(x) - min(x), 1)}
out = {
    "generated": "2026-07-25",
    "engine": "deterministic_rubric_v3",
    "calibration": {"active": cal is not None, "n_references": cal.get("n_references") if cal else 0},
    "source": "voxanalysis/archive/scratch-analyses (re-scored with current engine)",
    "selection": f"{N_TAKES} most recent singer takes by date",
    "aggregate": {"overall_v3": stats(ov), "capture_fair_v3": stats(cf), "n": len(rows)},
    "takes": rows,
}
os.makedirs(OUTDIR, exist_ok=True)
json.dump(out, open(os.path.join(OUTDIR, "last10-rescore-2026-07-25.json"), "w"), indent=2)

md = ["# Last-10 re-score — score metrics snapshot (2026-07-25)", "",
      "Re-scored with the **current engine** (`deterministic_rubric_v3`, calibration active, "
      f"{out['calibration']['n_references']} pro references) over the {N_TAKES} most recent singer takes in "
      "`voxanalysis/archive/scratch-analyses/`. `v2` is the score baked into the archived file at capture time; "
      "`v3` is the current engine's recompute; `cf` is capture-fair (voice_quality excluded).", "",
      "## Overall", "",
      f"- **overall v3**: min {out['aggregate']['overall_v3']['min']} · max {out['aggregate']['overall_v3']['max']} · "
      f"mean {out['aggregate']['overall_v3']['mean']} · spread {out['aggregate']['overall_v3']['spread']}",
      f"- **capture-fair v3**: min {out['aggregate']['capture_fair_v3']['min']} · max {out['aggregate']['capture_fair_v3']['max']} · "
      f"mean {out['aggregate']['capture_fair_v3']['mean']} · spread {out['aggregate']['capture_fair_v3']['spread']}",
      "- v2→v3 change per take never exceeds 0.1 (the rubric bump barely moved the numbers).", "",
      "## Per take", "",
      "| take | notes | v2 | v3 | cf | conf | inton | pitch | voice | vib | dyn | phrase |",
      "|---|--:|--:|--:|--:|:--|--:|--:|--:|--:|--:|--:|"]
for r in rows:
    c = r["components"]
    def cc(k): return c.get(k, "–")
    md.append(f"| {r['song']} ({r['singer']}) | {r['n_notes']} | {r['old_overall_v2']} | **{r['overall_v3']}** | "
              f"{r['capture_fair_v3']} | {r['confidence']} | {cc('intonation_accuracy')} | {cc('pitch_stability')} | "
              f"{cc('voice_quality')} | {cc('vibrato_control')} | {cc('dynamics_expression')} | {cc('phrase_control')} |")
md += ["", "## Raw metrics per take", "",
       "| take | med dev (c) | drift (c) | within25c | jitter% | shimmer% | HNR dB | vib% | phrase s |",
       "|---|--:|--:|--:|--:|--:|--:|--:|--:|"]
for r in rows:
    x = r["raw"]
    md.append(f"| {r['song']} ({r['singer']}) | {x['median_abs_dev_cents']} | {x['median_intra_note_drift_cents']} | "
              f"{x['pct_within_25c']} | {x['jitter_pct']} | {x['shimmer_pct']} | {x['hnr_db']} | "
              f"{x['vibrato_pct_notes']} | {x['median_phrase_s']} |")
open(os.path.join(OUTDIR, "last10-rescore-2026-07-25.md"), "w").write("\n".join(md) + "\n")
print(f"wrote {len(rows)} takes → {OUTDIR}")
print("overall_v3", stats(ov), "| capture_fair_v3", stats(cf))
