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


def _energy_vad(mono: np.ndarray, sr: int, margin_db: float) -> tuple[np.ndarray, np.ndarray]:
    """Speech mask from framewise energy vs an estimated noise floor."""
    times, levels = dsp.frame_rms_db(mono, sr, FRAME_S, HOP_S)
    noise_floor = np.percentile(levels, 10)
    speech = levels > noise_floor + margin_db
    # Hangover: keep speech "on" briefly after it stops, so tails aren't clipped.
    hang = int(0.2 / HOP_S)
    on = np.where(speech)[0]
    for i in on:
        speech[i : i + hang] = True
    return times, speech


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


def analyze(
    mono: np.ndarray,
    sr: int,
    min_pause_s: float = 0.35,
    floor_db: float = -60.0,
    fade_ms: float = 60.0,
    margin_db: float = 12.0,
    edge_pad_s: float = 0.06,
    use_ai: bool = True,
) -> tuple[list[Region], np.ndarray, np.ndarray]:
    """Return (pause regions, frame times, speech mask)."""
    result = _silero_vad(mono, sr) if use_ai else None
    backend = "silero" if result is not None else "energy"
    if result is None:
        result = _energy_vad(mono, sr, margin_db)
    times, speech = result

    pauses = dsp.merge_frames_to_regions(~speech, times, min_pause_s, merge_gap_s=0.05)
    duration = len(mono) / sr
    regions = []
    for s, e in pauses:
        # Shrink into the pause so fades never eat word starts/ends.
        s, e = s + edge_pad_s, e - edge_pad_s
        s, e = max(0.0, s), min(duration, e)
        if e - s >= min_pause_s / 2:
            regions.append(
                Region(start=round(s, 4), end=round(e, 4), reduction_db=floor_db,
                       fade_ms=fade_ms, label=f"pause ({backend})")
            )
    return regions, times, speech
