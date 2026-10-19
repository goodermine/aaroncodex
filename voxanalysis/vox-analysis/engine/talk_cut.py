#!/usr/bin/env python3
"""Find the talking in a separated vocal and cut it out before scoring.

Live and home takes carry speech the singer never meant to be scored: an MC
introduction, chat before the song, "thank you" after it, the shouted name of
the next singer, crowd chatter that leaks into the vocal stem. Scored as
singing, that speech reads as wildly off-pitch notes. Until now it was found
and trimmed by hand from a transcript; this module does the same job.

How it decides, in order:

1. **Phrases.** A fast pYIN pass over the vocal stem (16 kHz) finds voiced
   phrases. For each one it measures how much of it sits on a held pitch
   (within 35 cents for at least 150 ms). Singing holds notes; speech glides.
2. **The sung window.** The first and last phrases that hold notes, sit at the
   song's level and have other sung phrases around them mark where the singing
   starts and ends. Everything before and after is removed.
3. **Lyrics extend it.** Whisper transcribes the stem. A transcript segment
   just outside the window whose words repeat the song's own lyrics (a
   shouted outro, "play that funky music" one more time) is singing, so the
   window grows to include it. Chat that shares no lyrics stays out.
4. **Talk inside the song.** A transcript segment inside the window, for
   example chat over an instrumental break, is cut only when it reads as stage
   talk ("thank you", "give it up"), shares no lyrics and holds no notes.
   Ad-libs and spoken lyrics stay in.

Removed spans are CUT OUT, exactly as the hand trims did: the kept singing
is joined end to end (short crossfades at any inner cut). Silencing them in
place was tried first and rejected: it moved the measured held-note drift by
~9 cents on a hand-trimmed archive take (The Wanderer, 15 Oct, take 2: 8.8 ->
9.3), while a crop at the hand-trim window reproduced the archived 8.8 / 8.4
exactly. The plan records where the kept singing sits in the recording, so
the report can say how its times map back to the singer's file.

This is audio preparation, not scoring: it never reads or changes a score
(CLAUDE.md rule 1). Its plan is recorded with the take so the singer sees
exactly what was removed and can check it by ear.

Whisper is optional. Without it, steps 3 and 4 are skipped and only the edges
are trimmed from the pitch evidence alone.

Usage:
    python3 talk_cut.py <vocal_stem> --out <cut.wav> [--plan plan.json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

METHOD = "talk_cut_v1"
SR = 16000
HOP = 320
FRAME_RATE = SR / HOP

VOICING_PROB = 0.05        # pYIN voiced probability; low, so weak live vocals still count
PHRASE_GAP_S = 0.35        # voiced runs closer than this join into one phrase
HELD_TOLERANCE_CENTS = 35
HELD_MIN_S = 0.15
SUNG_MIN_S = 0.5           # a sung phrase: long enough,
SUNG_MIN_HELD = 0.45       # mostly on held notes,
SUNG_MIN_LONGEST_S = 0.25  # with at least one real held note,
SUNG_LEVEL_DROP_DB = 18    # and no quieter than this below the song's level
SUPPORT_SPAN_S = 20        # the first/last sung phrase needs this much singing
SUPPORT_MIN_S = 5          # ...within this span, so a lone "woo" can't open the song
CHAIN_GAP_S = 6            # earlier/later sung phrases this close still belong
EDGE_PAD_S = 0.25
LYRIC_GAP_S = 3            # a transcript segment this close to an edge may extend it
LYRIC_OVERLAP = 0.5        # share of its words that must already be lyrics
INNER_MAX_HELD = 0.35      # inner talk holds fewer notes than this
MIN_REMOVED_S = 0.5        # shorter spans are left alone
MIN_KEPT_S = 20            # never keep less than this...
MIN_KEPT_SHARE = 0.25      # ...or this share of the recording; if so, cut nothing
FADE_S = 0.03

TALK_PATTERNS = re.compile(
    r"\b(thank you|thanks|thank u|cheers|give it up|round of applause|make some noise|"
    r"ladies and gentlemen|how are (we|you|ya)|everybody|next up|up next|this one|"
    r"this song|one more|good night|goodnight|sorry|check|one two|finish(ed)?)\b",
    re.I,
)
_WORD = re.compile(r"[a-z']+")
_STOPWORDS = frozenset(
    "a an and the i you me my we us our it is are was be to of in on at for so oh "
    "yeah ooh ah hey well do did that this with your just".split()
)


# ---- measurement ---------------------------------------------------------

def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    edges = np.flatnonzero(np.diff(np.r_[0, mask.astype(np.int8), 0]))
    return list(zip(edges[::2].tolist(), edges[1::2].tolist()))


def measure(y: np.ndarray) -> dict:
    """pYIN pitch, voicing and level for a 16 kHz mono signal."""
    import librosa

    f0, _, voiced_prob = librosa.pyin(y, fmin=70, fmax=1000, sr=SR, frame_length=1024, hop_length=HOP)
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=HOP)[0][: len(f0)]
    return {"f0": f0, "voiced_prob": voiced_prob, "rms": rms}


def find_phrases(f0: np.ndarray, voiced_prob: np.ndarray, rms: np.ndarray) -> list[dict]:
    voiced = np.isfinite(f0) & (voiced_prob > VOICING_PROB)
    with np.errstate(divide="ignore", invalid="ignore"):
        cents = 1200 * np.log2(np.where(voiced, f0, np.nan) / 440.0)
    held = np.zeros(len(f0), bool)
    min_held = int(HELD_MIN_S * FRAME_RATE)
    for a, b in _runs(voiced):
        start = a
        for t in range(a + 1, b + 1):
            if t == b or abs(cents[t] - np.nanmedian(cents[start:t])) > HELD_TOLERANCE_CENTS:
                if t - start >= min_held:
                    held[start:t] = True
                start = t
    merged: list[list[int]] = []
    for a, b in _runs(voiced):
        if merged and a - merged[-1][1] < PHRASE_GAP_S * FRAME_RATE:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    phrases = []
    for a, b in merged:
        n_voiced = int(voiced[a:b].sum())
        longest = max((y - x for x, y in _runs(held[a:b])), default=0)
        phrases.append({
            "start": a / FRAME_RATE, "end": b / FRAME_RATE, "duration": (b - a) / FRAME_RATE,
            "held": float(held[a:b].sum() / max(1, n_voiced)),
            "longest_held": longest / FRAME_RATE,
            "level_db": float(20 * np.log10(np.mean(rms[a:b]) + 1e-9)),
        })
    return phrases


def held_share(phrases: list[dict], start: float, end: float) -> float:
    """Held-note share of the voiced material between start and end."""
    total = held = 0.0
    for p in phrases:
        overlap = min(p["end"], end) - max(p["start"], start)
        if overlap > 0:
            total += overlap
            held += overlap * p["held"]
    return held / total if total else 0.0


# ---- the sung window -------------------------------------------------------

def sung_phrases(phrases: list[dict]) -> list[dict]:
    body = [p for p in phrases if p["duration"] >= 1.0] or phrases
    if not body:
        return []
    song_level = float(np.median([p["level_db"] for p in body]))
    return [p for p in phrases
            if p["duration"] >= SUNG_MIN_S and p["held"] >= SUNG_MIN_HELD
            and p["longest_held"] >= SUNG_MIN_LONGEST_S
            and p["level_db"] >= song_level - SUNG_LEVEL_DROP_DB]


def sung_window(phrases: list[dict]) -> tuple[float, float] | None:
    sung = sung_phrases(phrases)
    if not sung:
        return None

    def support_after(p):
        return sum(min(q["end"], p["start"] + SUPPORT_SPAN_S) - q["start"]
                   for q in sung if p["start"] <= q["start"] < p["start"] + SUPPORT_SPAN_S)

    def support_before(p):
        return sum(q["end"] - max(q["start"], p["end"] - SUPPORT_SPAN_S)
                   for q in sung if p["end"] - SUPPORT_SPAN_S < q["end"] <= p["end"])

    first = next((i for i, p in enumerate(sung) if support_after(p) >= SUPPORT_MIN_S), None)
    last = next((i for i in range(len(sung) - 1, -1, -1) if support_before(sung[i]) >= SUPPORT_MIN_S), None)
    if first is None or last is None or sung[first]["start"] >= sung[last]["end"]:
        return None
    # Quiet or sparsely voiced opening lines: keep earlier sung phrases that
    # chain onto the supported one.
    while first > 0 and sung[first]["start"] - sung[first - 1]["end"] <= CHAIN_GAP_S:
        first -= 1
    while last < len(sung) - 1 and sung[last + 1]["start"] - sung[last]["end"] <= CHAIN_GAP_S:
        last += 1
    return sung[first]["start"], sung[last]["end"]


# ---- transcript --------------------------------------------------------------

def transcribe(path: Path) -> list[dict] | None:
    """Whisper segments with word timings, or None when Whisper is unavailable."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    model = WhisperModel(os.environ.get("VOX_TALK_MODEL", "small.en"), device="auto", compute_type="int8")
    segments, _ = model.transcribe(str(path), word_timestamps=True, vad_filter=True,
                                   condition_on_previous_text=False)
    return [{"start": s.start, "end": s.end, "text": s.text.strip(),
             "words": [{"start": w.start, "end": w.end, "word": w.word} for w in (s.words or [])]}
            for s in segments]


def _content_words(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in _STOPWORDS and len(w) > 1]


def lyric_overlap(text: str, lyrics: set[str]) -> float:
    words = _content_words(text)
    return sum(w in lyrics for w in words) / len(words) if words else 0.0


def _text_between(segments: list[dict], start: float, end: float) -> str:
    words = [w["word"].strip() for s in segments for w in s["words"]
             if start <= (w["start"] + w["end"]) / 2 < end]
    text = " ".join(w for w in words if w)
    return text if len(text) <= 160 else text[:157].rstrip() + "..."


# ---- the plan ---------------------------------------------------------------

def plan_cut(phrases: list[dict], segments: list[dict] | None, duration: float) -> dict:
    plan = {"method": METHOD, "transcript": "whisper" if segments is not None else "unavailable",
            "duration_s": round(duration, 2), "removed": []}
    window = sung_window(phrases)
    if window is None:
        return {**plan, "status": "no_change", "reason": "no clear sung section was found, so nothing was cut"}
    start, end = window
    segments = segments or []
    lyrics = {w for s in segments if start <= (s["start"] + s["end"]) / 2 <= end
              for w in _content_words(s["text"])}
    # Lyrics just outside the window are singing too.
    for seg in sorted(segments, key=lambda s: s["start"]):
        if end < seg["start"] <= end + LYRIC_GAP_S and lyric_overlap(seg["text"], lyrics) >= LYRIC_OVERLAP:
            end = max(end, seg["end"])
    for seg in sorted(segments, key=lambda s: -s["end"]):
        if start - LYRIC_GAP_S <= seg["end"] < start and lyric_overlap(seg["text"], lyrics) >= LYRIC_OVERLAP:
            start = min(start, seg["start"])
    start = max(0.0, start - EDGE_PAD_S)
    end = min(duration, end + EDGE_PAD_S)
    kept = end - start
    if kept < MIN_KEPT_S or kept < MIN_KEPT_SHARE * duration:
        return {**plan, "status": "no_change",
                "reason": "the singing found was too short to trust a cut, so nothing was cut"}

    removed = []
    if start >= MIN_REMOVED_S:
        removed.append({"start": 0.0, "end": start, "kind": "before_singing"})
    inside = [s for s in segments if start <= s["start"] and s["end"] <= end]
    for seg in inside:
        if seg["end"] - seg["start"] < MIN_REMOVED_S or not TALK_PATTERNS.search(seg["text"]):
            continue
        # Compare with the OTHER lines' words: a line is always its own lyric.
        others = {w for s in inside if s is not seg for w in _content_words(s["text"])}
        if (lyric_overlap(seg["text"], others) < 0.3
                and held_share(phrases, seg["start"], seg["end"]) < INNER_MAX_HELD):
            removed.append({"start": seg["start"], "end": seg["end"], "kind": "talk"})
    if duration - end >= MIN_REMOVED_S:
        removed.append({"start": end, "end": duration, "kind": "after_singing"})
    for span in removed:
        span["text"] = _text_between(segments, span["start"], span["end"])
        span["start"], span["end"] = round(span["start"], 2), round(span["end"], 2)
    inner = sorted((s for s in removed if s["kind"] == "talk"), key=lambda s: s["start"])
    kept, cursor = [], start
    for span in inner:
        if span["start"] > cursor:
            kept.append([round(cursor, 2), span["start"]])
        cursor = max(cursor, span["end"])
    kept.append([round(cursor, 2), round(end, 2)])
    return {**plan, "status": "cut" if removed else "no_change",
            **({} if removed else {"reason": "no talking was found"}),
            "sung_window": [round(start, 2), round(end, 2)],
            "kept": kept,
            "offset_s": kept[0][0],
            "removed": removed,
            "removed_s": round(sum(s["end"] - s["start"] for s in removed), 2)}


def to_recording_time(t: float, plan: dict) -> float:
    """Map a time in the cut audio back to the singer's original recording."""
    elapsed = 0.0
    for a, b in plan.get("kept") or [[0.0, plan.get("duration_s", t)]]:
        if t <= elapsed + (b - a):
            return a + (t - elapsed)
        elapsed += b - a
    return t + (plan.get("offset_s") or 0.0)


def apply_plan(in_path: Path, out_path: Path, plan: dict) -> None:
    """Write only the kept spans of in_path, joined with short crossfades.

    Applied to the vocal and the backing alike, so the two stay aligned."""
    import soundfile as sf

    audio, sr = sf.read(str(in_path), always_2d=True, dtype="float32")
    fade = max(1, int(FADE_S * sr))
    pieces = [audio[int(a * sr):min(len(audio), int(b * sr))] for a, b in plan["kept"]]
    out = pieces[0]
    for piece in pieces[1:]:
        n = min(fade, len(out), len(piece))
        if n:
            ramp = np.linspace(0, 1, n, dtype=np.float32)[:, None]
            out = np.concatenate([out[:-n], out[-n:] * (1 - ramp) + piece[:n] * ramp, piece[n:]])
        else:
            out = np.concatenate([out, piece])
    sf.write(str(out_path), out, sr, subtype="PCM_24")


def cut_talk(vocal_path: Path, out_path: Path, *, use_transcript: bool = True) -> dict:
    """Plan and apply the cut. Returns the plan; writes out_path only when cutting."""
    import librosa

    y, _ = librosa.load(str(vocal_path), sr=SR, mono=True)
    duration = len(y) / SR
    m = measure(y)
    phrases = find_phrases(m["f0"], m["voiced_prob"], m["rms"])
    segments = transcribe(vocal_path) if use_transcript else None
    plan = plan_cut(phrases, segments, duration)
    if plan["status"] == "cut":
        apply_plan(vocal_path, out_path, plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("vocal", type=Path, help="separated vocal stem")
    parser.add_argument("--out", type=Path, required=True, help="where to write the cut vocal")
    parser.add_argument("--plan", type=Path, help="write the cut plan here as JSON")
    parser.add_argument("--no-transcript", action="store_true", help="pitch evidence only (no Whisper)")
    args = parser.parse_args()
    plan = cut_talk(args.vocal, args.out, use_transcript=not args.no_transcript)
    text = json.dumps(plan, indent=2)
    if args.plan:
        args.plan.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
