#!/usr/bin/env python3
"""Export display-only constant-Q spectral artifacts for the pitch viewer.

This module is deliberately separate from the measurement and scoring engine.
Nothing in ``analyse_song.py`` imports it, and no score or prescription reads
its output.  The viewer bridge opts in after its normal analysis has finished.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import librosa
import numpy as np
from PIL import Image

SCHEMA_VERSION = "voxai_spectral_v1"
SAMPLE_RATE = 44_100
HOP_LENGTH = 2_048
BINS_PER_SEMITONE = 3
BINS_PER_OCTAVE = 12 * BINS_PER_SEMITONE
MIDI_LO = 36.0  # C2
MIDI_HI = 96.0  # C7, exclusive
VISIBLE_BINS = int((MIDI_HI - MIDI_LO) * BINS_PER_SEMITONE)
# Highest CQT bin remains below Nyquist at 44.1 kHz and covers H8 for every
# fundamental in the visible C2-C7 range. Only the first VISIBLE_BINS are
# exported to PNG; these extra bins power the H1-H8 readout.
ANALYSIS_BINS = 289
TILE_WIDTH_FRAMES = 2_048
DB_FLOOR = -80.0
DB_CEIL = 0.0


def harmonic_midi(fundamental_midi: float, harmonic_number: int) -> float:
    """Return the equal-tempered MIDI position of harmonic ``k``."""
    if harmonic_number < 1:
        raise ValueError("harmonic_number must be positive")
    return fundamental_midi + 12.0 * math.log2(harmonic_number)


def midi_to_row(midi_value: float) -> float:
    """Map MIDI to a high-to-low image row; values outside C2-C7 may overflow."""
    return (VISIBLE_BINS - 1) - (midi_value - MIDI_LO) * BINS_PER_SEMITONE


def time_to_frame(time_seconds: float, fps: float = SAMPLE_RATE / HOP_LENGTH) -> float:
    return (time_seconds * fps)


def _atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def _db_pixels(magnitude: np.ndarray) -> np.ndarray:
    peak = float(np.max(magnitude))
    if peak <= np.finfo(np.float32).eps:
        return np.zeros_like(magnitude, dtype=np.uint8)
    db = librosa.amplitude_to_db(magnitude, ref=peak, top_db=abs(DB_FLOOR))
    db = np.clip(db, DB_FLOOR, DB_CEIL)
    scaled = np.rint((db - DB_FLOOR) / (DB_CEIL - DB_FLOOR) * 255.0)
    return np.asarray(scaled, dtype=np.uint8)


def _write_tiles(
    pixels: np.ndarray,
    output_dir: Path,
    fps: float,
    tile_width_frames: int = TILE_WIDTH_FRAMES,
) -> list[dict]:
    if pixels.ndim != 2 or pixels.dtype != np.uint8:
        raise ValueError("spectral tile source must be a two-dimensional uint8 array")
    if tile_width_frames < 1:
        raise ValueError("tile_width_frames must be positive")
    tiles = []
    for index, frame_start in enumerate(range(0, pixels.shape[1], tile_width_frames)):
        frame_stop = min(pixels.shape[1], frame_start + tile_width_frames)
        file_name = f"tile-{index:03d}.png"
        Image.fromarray(pixels[:, frame_start:frame_stop]).save(
            output_dir / file_name,
            format="PNG",
            compress_level=9,
            optimize=False,
        )
        frame_count = frame_stop - frame_start
        tiles.append(
            {
                "index": index,
                "file": file_name,
                "frame_start": frame_start,
                "frame_count": frame_count,
                "t0": round(frame_start / fps, 6),
                "duration_seconds": round(frame_count / fps, 6),
                "width": frame_count,
                "height": pixels.shape[0],
            }
        )
    return tiles


def _harmonic_tracks(
    magnitude: np.ndarray,
    pitch_contour: dict,
    cqt_fps: float,
) -> dict:
    rate_hz = float(pitch_contour.get("rate_hz") or 10.0)
    pitch_values = pitch_contour.get("values") or []
    tracks: dict[str, list[float | None]] = {
        f"H{number}": [] for number in range(1, 9)
    }

    for pitch_index, cents in enumerate(pitch_values):
        peaks: list[float | None] = []
        if cents is None or not math.isfinite(float(cents)):
            peaks = [None] * 8
        else:
            fundamental_midi = 69.0 + float(cents) / 100.0
            cqt_column = min(
                magnitude.shape[1] - 1,
                max(0, int(round((pitch_index / rate_hz) * cqt_fps))),
            )
            for number in range(1, 9):
                target_midi = harmonic_midi(fundamental_midi, number)
                target_bin = (target_midi - MIDI_LO) * BINS_PER_SEMITONE
                if target_bin < 0 or target_bin >= magnitude.shape[0]:
                    peaks.append(None)
                    continue
                center = int(round(target_bin))
                start = max(0, center - 1)
                stop = min(magnitude.shape[0], center + 2)
                peaks.append(float(np.max(magnitude[start:stop, cqt_column])))

        available = [value for value in peaks if value is not None and value > 0]
        strongest = max(available) if available else None
        for number, value in enumerate(peaks, start=1):
            relative = None
            if strongest is not None and value is not None and value > 0:
                relative = round(max(DB_FLOOR, 20.0 * math.log10(value / strongest)), 1)
            tracks[f"H{number}"].append(relative)

    return {
        "version": SCHEMA_VERSION,
        "rate_hz": rate_hz,
        "t0": 0.0,
        "units": "db_relative_to_strongest_available_harmonic_per_frame",
        "values": tracks,
        "note": (
            "Display-only H1-H8 band peaks sampled at k times measured F0. "
            "Null means unvoiced or outside the analysed frequency range."
        ),
    }


def export_spectral(
    wav_path: Path,
    output_dir: Path,
    pitch_contour: dict,
    source: str,
) -> dict:
    """Create tiled grayscale CQT data and time-resolved H1-H8 tracks."""
    wav_path = Path(wav_path)
    output_dir = Path(output_dir)
    temporary = output_dir.with_name(output_dir.name + ".tmp")
    shutil.rmtree(temporary, ignore_errors=True)
    temporary.mkdir(parents=True)

    try:
        audio, sample_rate = librosa.load(wav_path, sr=SAMPLE_RATE, mono=True)
        if not len(audio):
            raise ValueError("spectral source is empty")
        magnitude = np.abs(
            librosa.cqt(
                audio,
                sr=sample_rate,
                hop_length=HOP_LENGTH,
                fmin=librosa.midi_to_hz(MIDI_LO),
                n_bins=ANALYSIS_BINS,
                bins_per_octave=BINS_PER_OCTAVE,
            )
        ).astype(np.float32, copy=False)
        cqt_fps = sample_rate / HOP_LENGTH
        visible = _db_pixels(magnitude[:VISIBLE_BINS])
        visible = np.flipud(visible)  # high frequencies at the top of Canvas

        tiles = _write_tiles(visible, temporary, cqt_fps)

        harmonic_file = "harmonic-tracks.json"
        harmonic_data = _harmonic_tracks(magnitude, pitch_contour, cqt_fps)
        _atomic_json(temporary / harmonic_file, harmonic_data)

        descriptor = {
            "version": SCHEMA_VERSION,
            "source": source,
            "transform": "librosa.cqt",
            "display_only": True,
            "t0": 0.0,
            "fps": cqt_fps,
            "sample_rate": sample_rate,
            "hop_length": HOP_LENGTH,
            "duration_seconds": round(len(audio) / sample_rate, 6),
            "total_frames": visible.shape[1],
            "midi_lo": MIDI_LO,
            "midi_hi": MIDI_HI,
            "midi_hi_exclusive": True,
            "bins_per_semitone": BINS_PER_SEMITONE,
            "bins_per_octave": BINS_PER_OCTAVE,
            "n_bins": VISIBLE_BINS,
            "row_order": "high_to_low",
            "row_formula": "row = n_bins - 1 - (midi - midi_lo) * bins_per_semitone",
            "time_formula": "frame = (time_seconds - t0) * fps",
            "db_floor": DB_FLOOR,
            "db_ceil": DB_CEIL,
            "pixel_encoding": "uint8_grayscale_linear_between_db_floor_and_db_ceil",
            "tile_width_frames": TILE_WIDTH_FRAMES,
            "tiles": tiles,
            "harmonic_tracks_file": harmonic_file,
            "note": (
                "Spectral energy for visual inspection only. It is not consumed by "
                "VOXAI metrics, scoring, prescriptions or coaching claims."
            ),
        }
        _atomic_json(temporary / "descriptor.json", descriptor)
        shutil.rmtree(output_dir, ignore_errors=True)
        temporary.replace(output_dir)
        return descriptor
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("source", choices=("vocals", "original"))
    args = parser.parse_args()
    pitch_contour = json.load(sys.stdin)
    if not isinstance(pitch_contour, dict):
        raise ValueError("pitch contour must be a JSON object")
    export_spectral(args.wav_path, args.output_dir, pitch_contour, args.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
