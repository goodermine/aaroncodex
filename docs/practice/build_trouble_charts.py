import json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = "/home/user/aaroncodex"
SP = "/tmp/claude-0/-home-user-aaroncodex/779bc529-6d36-543d-9ec0-66bbb7d1c6af/scratchpad/pd_cook"
d = json.load(open(f"{ROOT}/voxanalysis/archive/scratch-analyses/"
                   "2026-07-25-aaron-pressure-down-captain-cook-tavern-take-001_analysis.json"))
W = json.load(open(f"{SP}/words.json"))

c = d["pitch"]["f0_contour"]
rate = c["rate_hz"]
vals = c["values"]
t = [i / rate for i in range(len(vals))]
midi = [(69 + v / 100) if v is not None else None for v in vals]

spots = sorted(d["intonation"]["worst_drift_notes"], key=lambda x: x["start_s"])
PASS_HZ = d["registers"]["estimated_passaggio_hz"]
PASS_MIDI = 69 + 12 * math.log2(PASS_HZ / 440)

NAMES = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"]
def nn(m):
    r = int(round(m)); return NAMES[r % 12] + str(r // 12 - 1)
def mmss(s): return f"{int(s)//60}:{int(s)%60:02d}"
def words_at(t0, t1, pad=0.8):
    ws = [w["word"] for w in W if w["end"] >= t0 - pad and w["start"] <= t1 + pad]
    return " ".join(ws)

# Words confirmed by ear by Aaron; Whisper misheard "pressure" as "brushes".
CONFIRMED = {"0:35":"(sustained)","1:01":"...take the pressure DOWN","1:17":"(line end)",
             "1:51":"(sustained)","2:44":"(sustained)","3:01":"...take the pressure DOWN",
             "3:18":"...pressure DOWN","3:25":"(sustained)"}

INK, BG, GRID = "#eaf3f8", "#0a1218", "#22303b"
CY, RED, AMB = "#3fe0ff", "#ff5d6c", "#ffc158"

fig = plt.figure(figsize=(17, 12), facecolor=BG)
gs = fig.add_gridspec(3, 3, height_ratios=[1.5, 1, 1], hspace=0.42, wspace=0.18)

# ---------- overview ----------
ax = fig.add_subplot(gs[0, :], facecolor=BG)
seg_t, seg_m = [], []
for i in range(len(midi)):
    if midi[i] is None:
        if seg_t: ax.plot(seg_t, seg_m, color=CY, lw=1.0); seg_t, seg_m = [], []
    else:
        seg_t.append(t[i]); seg_m.append(midi[i])
if seg_t: ax.plot(seg_t, seg_m, color=CY, lw=1.0)

lo, hi = 50, 79
for m in range(lo, hi + 1):
    ax.axhline(m, color=GRID, lw=0.6 if m % 12 else 1.0, zorder=0)
ax.axhline(PASS_MIDI, color=AMB, lw=1.4, ls="--", zorder=1)
ax.text(2, PASS_MIDI + 0.5, f"passaggio ≈ {d['registers']['estimated_passaggio']} — where the voice changes gear",
        color=AMB, fontsize=10, va="bottom")

for i, s in enumerate(spots, 1):
    t0, t1 = s["start_s"], s["start_s"] + s["duration_s"]
    ax.add_patch(Rectangle((t0, lo), max(t1 - t0, 1.2), hi - lo, color=RED, alpha=0.20, zorder=2))
    ax.text((t0 + t1) / 2, hi - 1.2, str(i), color="#fff", fontsize=11, fontweight="bold",
            ha="center", bbox=dict(boxstyle="circle,pad=0.22", fc=RED, ec="none"), zorder=4)

ax.set_xlim(0, d["duration_seconds"]); ax.set_ylim(lo, hi)
ax.set_yticks(range(lo, hi + 1, 3)); ax.set_yticklabels([nn(m) for m in range(lo, hi + 1, 3)], color=INK, fontsize=9)
ax.set_xticks(range(0, int(d["duration_seconds"]) + 1, 20))
ax.set_xticklabels([mmss(x) for x in range(0, int(d["duration_seconds"]) + 1, 20)], color=INK, fontsize=9)
ax.set_title("Pressure Down — Captain Cook Tavern.  8 worst pitch-collapse moments (red)",
             color=INK, fontsize=15, pad=14, loc="left")
ax.set_ylabel("note", color=INK)
for sp in ax.spines.values(): sp.set_color(GRID)
ax.tick_params(colors=INK)

# ---------- the 3 worst, zoomed ----------
worst = sorted(spots, key=lambda x: -x["held_drift_cents"])[:3]
for k, s in enumerate(worst):
    axz = fig.add_subplot(gs[1, k], facecolor=BG)
    t0, t1 = s["start_s"], s["start_s"] + s["duration_s"]
    a, b = t0 - 1.0, t1 + 1.0
    xs = [t[i] for i in range(len(midi)) if midi[i] is not None and a <= t[i] <= b]
    ys = [midi[i] for i in range(len(midi)) if midi[i] is not None and a <= t[i] <= b]
    axz.plot(xs, ys, color=CY, lw=1.8, marker="o", ms=2.5)
    axz.add_patch(Rectangle((t0, 0), t1 - t0, 200, color=RED, alpha=0.16, zorder=0))
    target = round(69 + 12 * math.log2(
        440 * 2 ** ((int(round(69 + 12 * math.log2(440 / 440)))) / 12) / 440))  # placeholder
    tgt = round(sum(ys) / len(ys)) if ys else 60
    axz.axhline(tgt, color="#5ae08a", lw=1.2, ls=":")
    if ys:
        axz.set_ylim(min(ys) - 1.5, max(ys) + 1.5)
        yl = range(int(min(ys)) - 1, int(max(ys)) + 2)
        axz.set_yticks(list(yl)); axz.set_yticklabels([nn(m) for m in yl], color=INK, fontsize=8)
    axz.set_xlim(a, b)
    axz.set_xticks([t0, t1]); axz.set_xticklabels([mmss(t0), mmss(t1)], color=INK, fontsize=8)
    wtxt = CONFIRMED.get(s["time"],"")
    axz.set_title(f"#{spots.index(s)+1}  {s['time']}  {s['note']}  ·  slides {s['held_drift_cents']:.0f} cents\n"
                  f"“{wtxt[:38]}”",
                  color=INK, fontsize=10.5, pad=8)
    for sp in axz.spines.values(): sp.set_color(GRID)
    axz.tick_params(colors=INK)

# ---------- table ----------
axt = fig.add_subplot(gs[2, :], facecolor=BG); axt.axis("off")
rows = [["#", "time", "note", "slides", "words being sung"]]
for i, s in enumerate(spots, 1):
    t0, t1 = s["start_s"], s["start_s"] + s["duration_s"]
    w = CONFIRMED.get(s["time"], "(sustained)")
    rows.append([str(i), s["time"], s["note"], f"{s['held_drift_cents']:.0f}c", w[:52]])
tbl = axt.table(cellText=rows[1:], colLabels=rows[0], loc="upper center",
                cellLoc="left", colWidths=[0.04, 0.07, 0.07, 0.08, 0.55])
tbl.auto_set_font_size(False); tbl.set_fontsize(10.5); tbl.scale(1, 1.55)
for (r, cc), cell in tbl.get_celld().items():
    cell.set_edgecolor(GRID)
    cell.set_facecolor("#0e1a22" if r else "#16232c")
    cell.get_text().set_color(INK if r else CY)
    if r and rows[r + 0][2] in ("D4", "C♯4"):
        cell.get_text().set_color("#ffd0d4")
axt.set_title("Every collapse, with the word (confirmed by ear) — note the clustering on D4 / C♯4 and the chorus line",
              color=INK, fontsize=13, loc="left", pad=2)

fig.savefig(f"{SP}/pressure-down-trouble.png", dpi=115, facecolor=BG, bbox_inches="tight")
print("saved")
