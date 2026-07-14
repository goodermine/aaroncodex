"""Gate analysis: find the pauses between phrases without clipping word edges.

Backend order: Silero VAD (if torch + silero-vad are installed) -> energy VAD.
Both produce the same output: speech regions, from which pauses are derived.
"""

from __future__ import annotations

import numpy as np

from .. import dsp
from ..document import Region

FRAME_S = 0.03
HOP_S = 0.01

# Guard times around *detected* speech that gating must never touch. Weak word
# onsets (the breathy "H" in "Hello") begin before any VAD fires, and trailing
# consonants outlast it — so protection is asymmetric and generous.
ONSET_GUARD_S = 0.15  # protection before detected speech begins
OFFSET_GUARD_S = 0.25  # protection after detected speech ends


def _dilate(mask: np.ndarray, hop_s: float, pre_s: float, post_s: float) -> np.ndarray:
    """Extend a speech mask backward by pre_s and forward by post_s."""
    guarded = mask.copy()
    for k in range(1, int(round(pre_s / hop_s)) + 1):
        guarded[:-k] |= mask[k:]
    for k in range(1, int(round(post_s / hop_s)) + 1):
        guarded[k:] |= mask[:-k]
    return guarded


def speech_guards(
    times: np.ndarray,
    speech: np.ndarray,
    pre_s: float = ONSET_GUARD_S,
    post_s: float = OFFSET_GUARD_S,
) -> list:
    """Protected speech intervals [[start, end], ...] for the Edit Document."""
    if len(times) < 2 or not speech.any():
        return []
    hop = float(times[1] - times[0])
    guarded = _dilate(speech, hop, pre_s, post_s)
    return [
        [round(s, 4), round(e, 4)]
        for s, e in dsp.merge_frames_to_regions(guarded, times, 0.0, merge_gap_s=hop)
    ]


def subtract_intervals(intervals: list, holes: list) -> list:
    """Subtract hole intervals from [start, end] intervals, splitting as needed."""
    out = []
    for s, e in intervals:
        pieces = [[s, e]]
        for hs, he in holes:
            trimmed = []
            for a, b in pieces:
                if he <= a or hs >= b:
                    trimmed.append([a, b])
                    continue
                if hs > a:
                    trimmed.append([a, hs])
                if he < b:
                    trimmed.append([he, b])
            pieces = trimmed
        out.extend([round(a, 4), round(b, 4)] for a, b in pieces if b - a > 1e-3)
    return out


def _energy_vad(mono: np.ndarray, sr: int, margin_db: float) -> tuple[np.ndarray, np.ndarray]:
    """Speech mask from framewise energy vs an estimated noise floor.

    No hangover here: tail protection is the offset guard's job, applied
    uniformly to every VAD backend in analyze().
    """
    times, levels = dsp.frame_rms_db(mono, sr, FRAME_S, HOP_S)
    noise_floor = np.percentile(levels, 10)
    return times, levels > noise_floor + margin_db


def _silero_vad(mono: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray] | None:
    try:
        import torch
        from silero_vad import load_silero_vad, get_speech_timestamps
    except ImportError:
        return None
    model = load_silero_vad()
    # Silero expects 16 kHz mono.
    step = max(1, round(sr / 16000))
    x16 = mono[::step].astype(np.float32)
    stamps = get_speech_timestamps(torch.from_numpy(x16), model, sampling_rate=16000)
    times = np.arange(0, len(mono) / sr, HOP_S)
    speech = np.zeros(len(times), dtype=bool)
    scale = step / sr * (sr / step / 16000)  # samples@16k -> seconds
    for st in stamps:
        s, e = st["start"] / 16000, st["end"] / 16000
        speech[(times >= s) & (times < e)] = True
    return times, speech


# A guard-trimmed pause piece shorter than this is not worth gating.
MIN_GATED_S = 0.12


def analyze(
    mono: np.ndarray,
    sr: int,
    min_pause_s: float = 0.35,
    floor_db: float = -60.0,
    fade_ms: float = 60.0,
    margin_db: float = 12.0,
    use_ai: bool = True,
) -> tuple[list[Region], np.ndarray, np.ndarray]:
    """Return (pause regions, frame times, raw speech mask).

    min_pause_s applies to the raw silent gap (the documented user-facing
    meaning); guards are subtracted afterward, so a qualifying pause can be
    gated in its safe middle even when guards shrink it.
    """
    result = _silero_vad(mono, sr) if use_ai else None
    backend = "silero" if result is not None else "energy"
    if result is None:
        result = _energy_vad(mono, sr, margin_db)
    times, speech = result

    raw_pauses = dsp.merge_frames_to_regions(~speech, times, min_pause_s, merge_gap_s=0.05)
    guards = speech_guards(times, speech)
    duration = len(mono) / sr
    regions = []
    for s, e in subtract_intervals([[s, e] for s, e in raw_pauses], guards):
        s, e = max(0.0, s), min(duration, e)
        if e - s >= MIN_GATED_S:
            regions.append(
                Region(start=round(s, 4), end=round(e, 4), reduction_db=floor_db,
                       fade_ms=fade_ms, label=f"pause ({backend})")
            )
    return regions, times, speech
