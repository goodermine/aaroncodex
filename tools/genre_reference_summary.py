"""Per-genre summary of the genre reference originals against the 50-pro pack.

Step 3 of docs/plans/GENRE_REFERENCE_CANDIDATES.md: raw measures only, read
the same way tools/build_calibration.py reads them, plus how the current
rubric scores each genre's professionals.

    python3 tools/genre_reference_summary.py   # prints the data section as markdown
"""
import itertools
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "voxanalysis/vox-analysis/engine/tools"))
import build_calibration as B  # noqa: E402

ARCHIVE = ROOT / "voxanalysis/archive/scratch-analyses"
PACK = json.loads((ROOT / "voxanalysis/vox-analysis/engine/calibration/pro_reference.json").read_text())["metrics"]

GENRES = {
    "50s-60s rock'n'roll": ["elvis-presley-dont-be-cruel", "little-richard-tutti-frutti", "chuck-berry-johnny-b-goode",
                           "jerry-lee-lewis-great-balls-of-fire", "dion-runaround-sue", "del-shannon-runaway",
                           "bobby-darin-dream-lover", "roy-orbison-oh-pretty-woman", "ben-e-king-stand-by-me",
                           "lulu-to-sir-with-love", "wanda-jackson-lets-have-a-party", "brenda-lee-sweet-nothins"],
    "Blues": ["little-walter-my-babe", "b-b-king-the-thrill-is-gone", "muddy-waters-mannish-boy",
              "howlin-wolf-smokestack-lightnin", "john-lee-hooker-boom-boom", "bobby-blue-bland-ill-take-care-of-you",
              "etta-james-id-rather-go-blind", "koko-taylor-wang-dang-doodle", "bonnie-raitt-love-me-like-a-man",
              "tracy-chapman-give-me-one-reason", "stevie-ray-vaughan-pride-and-joy", "gary-moore-still-got-the-blues"],
    "Hard rock / grit": ["jimmy-barnes-working-class-man", "billy-idol-rebel-yell", "guns-n-roses-you-could-be-mine",
                         "nirvana-smells-like-teen-spirit", "steppenwolf-born-to-be-wild", "ac-dc-highway-to-hell",
                         "led-zeppelin-whole-lotta-love", "the-angels-am-i-ever-gonna-see-your-face-again",
                         "heart-barracuda", "pat-benatar-hit-me-with-your-best-shot",
                         "joan-jett-and-the-blackhearts-i-love-rock-n-roll", "the-black-keys-lonely-boy",
                         "bryan-adams-summer-of-69"],
    "Rap / hip-hop": ["eminem-lose-yourself", "pitbull-ft-john-ryan-fireball", "sir-mix-a-lot-baby-got-back",
                      "c-c-music-factory-things-that-make-you-go-hmmm", "run-dmc-its-tricky",
                      "young-mc-bust-a-move", "tone-loc-funky-cold-medina", "the-notorious-b-i-g-juicy",
                      "kendrick-lamar-humble", "lauryn-hill-doo-wop-that-thing", "missy-elliott-work-it", "salt-n-pepa-push-it"],
}

# (pack key, label, unit, which way is "better" for a singer; None = no direction)
SHOWN = [
    ("intonation_median_abs_deviation_cents", "Pitch centre: median deviation", "c", -1),
    ("intonation_median_intra_note_drift_cents", "Held-note drift", "c", -1),
    ("vibrato_pct_notes_with_vibrato", "Long notes with vibrato", "%", None),
    ("vibrato_median_extent_cents", "Vibrato extent", "c", None),
    ("phrasing_median_phrase_s", "Median phrase length", "s", None),
    ("breath_pct_sagging_endings", "Phrase endings that sag", "%", -1),
    ("onsets_pct_clean", "Clean note entries", "%", +1),
    ("voice_quality_hnr_db_median", "HNR (capture-sensitive)", "dB", +1),
    ("voice_quality_cpps_db", "CPPS (capture-sensitive)", "dB", +1),
    ("dynamics_effective_dynamic_range_db", "Effective dynamic range (capture-sensitive)", "dB", None),
]
COMPONENTS = ["intonation_accuracy", "pitch_stability", "vibrato_control", "phrase_control", "breath_support",
              "voice_quality", "dynamics_expression"]


def load(slug):
    hits = sorted(ARCHIVE.glob(f"*{slug}-reference_analysis.json"))
    return json.loads(hits[-1].read_text()) if hits else None


def metric(data, key):
    path, needs_praat = B.METRIC_PATHS[key]
    if needs_praat and not str(data.get("voice_quality", {}).get("method", "")).startswith("praat"):
        return None
    guard = B.METRIC_GUARDS.get(key)
    if guard and (B.dig(data, guard[0]) or 0) < guard[1]:
        return None
    return B.dig(data, path)


def fmt(v, unit):
    return "—" if v is None else (f"{v:.1f}" if unit in ("c", "%", "dB") else f"{v:.2f}")


def settle(values):
    """Spread of the median across every 8-reference subset: does 12 settle it?"""
    if len(values) < 10:
        return None
    meds = [st.median(c) for c in itertools.combinations(values, 8)]
    return max(meds) - min(meds)


print("## Data\n")
print("Regenerate this section with `python3 tools/genre_reference_summary.py`.\n")
print("Raw measures from the RoFormer-separated originals, "
      "read the way `build_calibration.py` reads them, set against the current 50-pro pack.\n")

rows = {}
for genre, slugs in GENRES.items():
    data = {s: load(s) for s in slugs}
    have = {s: d for s, d in data.items() if d}
    rows[genre] = have
    print(f"- **{genre}:** {len(have)} of {len(slugs)} measured"
          + (f" (missing: {', '.join(s for s in slugs if s not in have)})" if len(have) < len(slugs) else ""))

print("\n## Raw measures: genre median vs the 50-pro pack\n")
print("Pack column is p10 / **p50** / p90. Genre column is the median of that genre's references, with n in brackets.\n")
print("| Measure | 50-pro pack | " + " | ".join(rows) + " |")
print("|---|---|" + "---|" * len(rows))
for key, label, unit, _ in SHOWN:
    p = PACK[key]
    cells = []
    for genre, have in rows.items():
        vals = [v for v in (metric(d, key) for d in have.values()) if v is not None]
        cells.append(f"{fmt(st.median(vals), unit)} ({len(vals)})" if vals else "—")
    print(f"| {label} ({unit}) | {fmt(p['p10'], unit)} / **{fmt(p['p50'], unit)}** / {fmt(p['p90'], unit)} | "
          + " | ".join(cells) + " |")

print("\n## How the current rubric scores each genre's professionals\n")
print("Median component score (0–10) across each genre's references, scored against the current 50-pro pack. "
      "A pro of the style scoring low on a component is the signal that the yardstick, not the singer, is off.\n")
print("| Component | " + " | ".join(rows) + " |")
print("|---|" + "---|" * len(rows))
for comp in COMPONENTS:
    cells = []
    for have in rows.values():
        vals = [(d["technical_score"]["components"].get(comp) or {}).get("score") for d in have.values()]
        vals = [v for v in vals if v is not None]
        cells.append(f"{st.median(vals):.1f}" if vals else "—")
    print(f"| {comp} | " + " | ".join(cells) + " |")
for label, field in (("**Overall**", "overall_score_0_to_10"), ("**Capture-fair**", "capture_fair_score_0_to_10")):
    cells = []
    for have in rows.values():
        vals = [d["technical_score"].get(field) for d in have.values() if d["technical_score"].get(field) is not None]
        cells.append(f"{st.median(vals):.1f} (range {min(vals):.1f}–{max(vals):.1f})" if vals else "—")
    print(f"| {label} | " + " | ".join(cells) + " |")

print("\n## Do 12 references settle the medians?\n")
print("Widest spread of the genre median across every possible 8-reference subset of the 12. Small means the "
      "median is already stable; large means the genre needs more references before it can anchor a score.\n")
print("| Measure | " + " | ".join(g for g, h in rows.items() if len(h) >= 10) + " |")
print("|---|" + "---|" * sum(1 for h in rows.values() if len(h) >= 10))
for key, label, unit, _ in SHOWN:
    cells = []
    for have in rows.values():
        if len(have) < 10:
            continue
        vals = [v for v in (metric(d, key) for d in have.values()) if v is not None]
        s = settle(vals)
        cells.append("—" if s is None else f"{s:.1f}")
    print(f"| {label} ({unit}) | " + " | ".join(cells) + " |")

print("\n## Per-reference detail\n")
print("| Genre | Reference | Overall / capture-fair | Pitch dev (c) | Held drift (c) | Sag (%) | Phrase (s) | HNR (dB) | Entry reliability |")
print("|---|---|---|---|---|---|---|---|---|")
for genre, have in rows.items():
    for slug, d in have.items():
        ts = d["technical_score"]
        print(f"| {genre} | {slug} | {ts.get('overall_score_0_to_10')} / {ts.get('capture_fair_score_0_to_10')} | "
              f"{fmt(metric(d, 'intonation_median_abs_deviation_cents'), 'c')} | "
              f"{fmt(metric(d, 'intonation_median_intra_note_drift_cents'), 'c')} | "
              f"{fmt(metric(d, 'breath_pct_sagging_endings'), '%')} | {fmt(metric(d, 'phrasing_median_phrase_s'), 's')} | "
              f"{fmt(metric(d, 'voice_quality_hnr_db_median'), 'dB')} | {(d.get('entry_accuracy') or {}).get('reliability', '—')} |")
