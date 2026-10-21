#!/usr/bin/env python3
"""Words onset map — one take, with the sung word under every note entry.

    python3 tools/word_onset_map.py TAKE_analysis.json --stem VOCAL_STEM.flac
        [--lyrics lyrics.txt] [--sections "0-9.7=opening chorus;89.5-103=sax break"]
        [--offset 30] [--words words.json] [--title "..."] [--out map.png]

Aaron's on-request chart (21 Oct 2026, first made for Tutti Frutti at the
Prince of Wales): the same onset dots as `tools/onset_map.py` (blue = scooped
up into the note, amber = landed above it, grey = clean within ±35c), split
into four rows down the song, with the word being sung and the note name
printed under each dot so he can see WHICH words he scoops or overshoots.

Words come from faster-whisper (medium.en) word timestamps on the vocal stem.
Pass the song's lyrics with --lyrics: they prime the recogniser and are the
biggest single accuracy win. Whisper cannot read scat, shouts or instrumental
breaks reliably — mark those spans with --sections and they are labelled by
name instead of guessed. The transcription is saved beside the PNG as
`<out>.words.json`; pass it back with --words to re-render without re-running
Whisper (e.g. after adjusting --sections).

The stem must be the same file the engine analysed. If the analysis used a
trimmed window, its start is read from the take note ("analysed 30.0s to
179.5s of the vocal stem"); override with --offset.

DIAGNOSTIC VISUALISATION, not a score — CLAUDE.md rule 1 is untouched.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import onset_map as om  # noqa: E402  (also sets the Agg backend + fonts)
import matplotlib.pyplot as plt  # noqa: E402

N_ROWS = 4
MAX_WORD_S = 2.5          # longer "words" are Whisper dragging a hallucination
WORD_LEAD_S = 0.15        # a note may start just before Whisper's word start
NEAREST_WORD_S = 0.4


def analysis_offset(take: dict) -> float:
    """Start of the analysed window within the stem, from the take note."""
    note = (take.get("take_context") or {}).get("note") or ""
    m = re.search(r"analysed\s+([\d.]+)\s*s\s+to\s+[\d.]+\s*s", note)
    return float(m.group(1)) if m else 0.0


def parse_sections(spec: str) -> list[dict]:
    """'0-9.7=opening chorus;89.5-103=sax break' -> labelled spans."""
    out = []
    for part in filter(None, (p.strip() for p in (spec or "").split(";"))):
        span, _, label = part.partition("=")
        a, _, b = span.partition("-")
        if not (label and a and b):
            raise ValueError(f"bad section {part!r}: want START-END=label")
        out.append({"w": f"({label.strip()})", "s": float(a), "e": float(b)})
    return out


def clean_words(words: list[dict], sections: list[dict]) -> list[dict]:
    """Drop over-long words and anything inside a labelled section, add the labels."""
    def inside(w):
        return any(s["s"] <= w["s"] < s["e"] for s in sections)
    kept = [w for w in words if w["e"] - w["s"] <= MAX_WORD_S and not inside(w)]
    return sorted(kept + sections, key=lambda w: w["s"])


def word_at(words: list[dict], t: float) -> str:
    """The word sung at note start t ('' when nothing is close enough)."""
    for w in words:
        if w["s"] - WORD_LEAD_S <= t < w["e"] + 0.05:
            return w["w"]
    if not words:
        return ""
    near = min(words, key=lambda w: abs(w["s"] - t))
    return near["w"] if abs(near["s"] - t) < NEAREST_WORD_S else ""


def transcribe(stem: str, start: float, end: float, lyrics: str = "") -> list[dict]:
    """Word timestamps for stem[start:end], relative to start."""
    from faster_whisper import WhisperModel  # heavy; only needed here
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(start), "-to", str(end), "-i", stem,
         "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    # numpy input, not a path: some PyAV builds break on faster-whisper's file decode.
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    model = WhisperModel("medium.en", device="cpu", compute_type="int8",
                         cpu_threads=os.cpu_count() or 4)
    segs, _ = model.transcribe(audio, word_timestamps=True, beam_size=5,
                               initial_prompt=lyrics or None, vad_filter=False,
                               condition_on_previous_text=True)
    return [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)}
            for s in segs for w in (s.words or [])]


def render(take_path: str, words: list[dict], out: str, title: str = "") -> str:
    rows, eng, dur = om._per_note(take_path)
    dur = dur or max(r[0] for r in rows)
    span = dur / N_ROWS
    fig, axes = plt.subplots(N_ROWS, 1, figsize=(16, 4.9 * N_ROWS))
    fig.subplots_adjust(left=0.06, right=0.98, top=0.915, bottom=0.07, hspace=0.62)
    for i, ax in enumerate(axes):
        lo, hi = i * span, (i + 1) * span
        ax.axhspan(-om.CLEAN_TH, om.CLEAN_TH, color=om.BAND, zorder=0)
        ax.axhline(0, color="#c3c9d2", lw=0.8, zorder=1)
        for t, dev, note in (r for r in rows if lo <= r[0] < hi):
            col = om.BLUE if dev < -om.CLEAN_TH else om.AMBER if dev > om.CLEAN_TH else om.GREY
            d = float(np.clip(dev, -430, 330))
            if col != om.GREY:
                ax.vlines(t, 0, d, color=col, lw=1.3, alpha=0.85, zorder=2)
            ax.scatter([t], [d], s=26, color=col, zorder=3, edgecolor="white", linewidth=0.6)
            w = word_at(words, t)
            ax.text(t, -0.03, f"{w}  {note}" if w else note, rotation=90, ha="center",
                    va="top", transform=ax.get_xaxis_transform(), fontsize=8,
                    color=om.INK if w else om.MUTE)
        ax.set_xlim(lo - 0.5, hi + 0.5)
        ax.set_ylim(-460, 360)
        ax.xaxis.tick_top()
        ax.spines["bottom"].set_visible(False)
        ax.spines["right"].set_visible(False)
        m0, s0 = divmod(int(lo), 60)
        m1, s1 = divmod(int(hi), 60)
        ax.set_title(f"{m0}:{s0:02d} – {m1}:{s1:02d}", loc="left", pad=22, fontsize=11,
                     color=om.INK, fontweight="bold")
        ax.tick_params(colors=om.MUTE, labelsize=8)
        ax.set_ylabel("cents from note centre", fontsize=8.5, color=om.MUTE)

    fig.suptitle(title or "How each note STARTS — with the words", x=0.06, ha="left",
                 fontsize=16, fontweight="bold", color=om.INK)
    fig.text(0.06, 0.952,
             "Blue = scooped up into the note · amber = landed above it · grey = clean (±35c). "
             "Under each dot: the word you were singing, then the note.  "
             f"clean {eng['pct_clean']:.0f}% · scooped {eng['pct_scooped']:.0f}% · "
             f"overshot {eng['pct_overshot']:.0f}%",
             fontsize=9.5, color=om.MUTE, ha="left")
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("take", help="the take's _analysis.json")
    ap.add_argument("--stem", help="vocal stem the engine analysed (needed unless --words)")
    ap.add_argument("--words", help="reuse a saved <out>.words.json instead of Whisper")
    ap.add_argument("--lyrics", help="text file of the song's lyrics (primes Whisper)")
    ap.add_argument("--sections", default="", help='"START-END=label;..." spans to label, not transcribe')
    ap.add_argument("--offset", type=float, help="analysed window start in the stem (s)")
    ap.add_argument("--title", default="")
    ap.add_argument("--out", help="PNG path (default: Onset-Map-WORDS-<take>.png at repo root)")
    a = ap.parse_args()

    take = json.load(open(a.take))
    base = re.sub(r"_analysis\.json$", "", os.path.basename(a.take))
    out = a.out or os.path.join(om.ROOT, f"Onset-Map-WORDS-{base}.png")
    if a.words:
        raw = json.load(open(a.words))
    elif a.stem:
        start = a.offset if a.offset is not None else analysis_offset(take)
        lyrics = open(a.lyrics).read() if a.lyrics else ""
        raw = transcribe(a.stem, start, start + float(take["duration_seconds"]), lyrics)
        with open(out + ".words.json", "w") as f:
            json.dump(raw, f, indent=0)
    else:
        ap.error("need --stem (to transcribe) or --words (saved transcription)")
    words = clean_words(raw, parse_sections(a.sections))
    print(f"{len(words)} words · wrote {render(a.take, words, out, a.title)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
