#!/usr/bin/env python3
"""
=============================================================================
VOXAI Local Analysis Tool — analyse_song.py
=============================================================================
Purpose:    Extracts a comprehensive set of acoustic and vocal features from
            an audio file and generates a structured JSON report plus a
            human-readable Markdown diagnostic document.

Usage:      python analyse_song.py <path_to_audio_file> [--name "Artist Name"]
            python analyse_song.py input/my_song.wav --name "Aaron Rustwood"
            python analyse_song.py input/my_song.wav --name "Aaron Rustwood" --separate-stems

Outputs:
    output/<filename>_analysis.json     Raw acoustic measurements
    reports/<filename>_report.md        Human-readable diagnostic report

Dependencies:
    numpy, scipy, librosa, soundfile, matplotlib
    praat-parselmouth — clinical-grade jitter/shimmer/HNR/formants (Praat)
    (Optional) openai — for AI-generated natural language feedback

Measurement policy:
    * Voice-quality metrics (jitter, shimmer, HNR, formants) are computed
      with Praat algorithms (via parselmouth) on sustained voiced segments
      only — never across pauses or note changes.
    * Every derived judgement carries a "method" and "reliability" label.
    * The technical score is a deterministic, documented rubric over the
      measured values: the same audio always produces the same score.
      Nothing in this file asks a language model for a number.

Author:     VOXAI Diagnostic Engine
=============================================================================
"""

import os
import sys
import json
import math
import argparse
import warnings
import subprocess
import glob
from datetime import datetime

import numpy as np
import scipy.signal
import librosa
import librosa.display
import soundfile as sf
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for WSL (no display required)
import matplotlib.pyplot as plt

try:
    import parselmouth
    from parselmouth.praat import call as praat_call
    PARSELMOUTH_AVAILABLE = True
except ImportError:
    PARSELMOUTH_AVAILABLE = False

warnings.filterwarnings('ignore')


# =============================================================================
# CONFIGURATION
# =============================================================================

# Pitch tracking range for sung vocals
PYIN_FMIN_NOTE = 'C2'   # ~65 Hz — lower limit for bass/baritenor
PYIN_FMAX_NOTE = 'D6'   # ~1175 Hz — covers high tenor/falsetto and most female range
PRAAT_PITCH_FLOOR = 65.0
PRAAT_PITCH_CEILING = 1200.0

# Minimum RMS level (dB) to be considered an active (non-silent) frame
SILENCE_THRESHOLD_DB = -60.0

# Sustained-note segmentation
VOICED_GAP_BRIDGE_FRAMES = 2      # bridge voiced gaps up to ~23 ms
NOTE_SPLIT_CENTS = 60.0           # split a voiced run when smoothed pitch jumps this much
NOTE_MIN_DURATION_S = 0.25        # minimum sustained note for intonation/voice-quality
VIBRATO_NOTE_MIN_S = 0.50         # minimum note length for per-note vibrato analysis
PHRASE_GAP_BRIDGE_S = 0.30        # voiced runs closer than this belong to one phrase

# Speech-pathology reference thresholds (kept for context in reports only —
# a sung melody is NOT directly comparable to a sustained spoken vowel)
JITTER_THRESHOLD_PCT = 1.04
SHIMMER_THRESHOLD_PCT = 3.81
HNR_CLEAN_THRESHOLD_DB = 20.0

# Singing-oriented interpretation bands for sustained sung notes
SINGING_JITTER_GOOD_PCT = 0.5
SINGING_SHIMMER_GOOD_PCT = 3.0
SINGING_HNR_GOOD_DB = 15.0

# Spectral centroid ranges for resonance classification
CENTROID_DARK_THRESHOLD = 1200.0    # Hz — below this = dark/swallowed
CENTROID_BRIGHT_THRESHOLD = 2500.0  # Hz — above this = very bright/twangy

# Vibrato detection
VIBRATO_RATE_MIN_HZ = 4.0
VIBRATO_RATE_MAX_HZ = 8.0
VIBRATO_SEARCH_MIN_HZ = 3.0
VIBRATO_SEARCH_MAX_HZ = 9.0
VIBRATO_MIN_EXTENT_CENTS = 10.0
VIBRATO_MAX_EXTENT_CENTS = 300.0
VIBRATO_MIN_BAND_RATIO = 0.15


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def convert_to_wav(input_path, temp_dir="temp"):
    """
    Converts any audio/video file to a standard mono 44.1kHz WAV using ffmpeg.
    This is the first step in the pipeline, ensuring consistent input format.

    Returns the path to the converted WAV file.
    """
    os.makedirs(temp_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(temp_dir, f"{base_name}_converted.wav")

    print(f"  Converting to standard WAV format...")
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vn",               # No video stream
        "-acodec", "pcm_s16le",  # 16-bit PCM (uncompressed)
        "-ar", "44100",      # 44.1kHz sample rate
        "-ac", "1",          # Mono channel
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr}")
        raise RuntimeError("Audio conversion failed. Is ffmpeg installed?")

    print(f"  Converted: {output_path}")
    return output_path


def resolve_repo_path(path_value):
    """Resolves a relative path from the repository root (script directory)."""
    if os.path.isabs(path_value):
        return path_value
    repo_root = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(repo_root, path_value)


def find_first_stem_match(patterns, exclude_substrings=()):
    """
    Returns the first matching file path from a list of glob patterns.

    exclude_substrings filters out false positives — e.g. the loose pattern
    "*vocals*" would otherwise happily match "no_vocals" (the instrumental).
    """
    for pattern in patterns:
        matches = sorted(glob.glob(pattern, recursive=True))
        for match in matches:
            lower_name = os.path.basename(match).lower()
            if any(bad in lower_name for bad in exclude_substrings):
                continue
            return match
    return None


def run_stem_separation(input_path, script_path="tools/stems/batch_stems.sh"):
    """
    Runs the dedicated stem-separation script and returns the detected
    vocals/instrumental output paths.
    """
    absolute_script_path = resolve_repo_path(script_path)
    if not os.path.isfile(absolute_script_path):
        raise RuntimeError(f"Stem script not found: {absolute_script_path}")

    os.makedirs("output/stems", exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_output_dir = os.path.join("output", "stems", f"{base_name}_{run_stamp}")
    os.makedirs(run_output_dir, exist_ok=True)

    print("  Running stem separation (vocals + instrumental)...")
    cmd = [
        "bash",
        absolute_script_path,
        "--input",
        input_path,
        "--output",
        run_output_dir,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise RuntimeError("Stem separation failed. Check the command output above.")

    vocals_path = find_first_stem_match(
        [
            os.path.join(run_output_dir, "**", "*_(Vocals)_*.flac"),
            os.path.join(run_output_dir, "**", "*_(Vocals)_*.wav"),
            os.path.join(run_output_dir, "**", "*.vocals.wav"),
            os.path.join(run_output_dir, "**", "*vocals*.wav"),
            os.path.join(run_output_dir, "**", "*vocals*.flac"),
        ],
        exclude_substrings=("no_vocals", "instrumental"),
    )
    instrumental_path = find_first_stem_match([
        os.path.join(run_output_dir, "**", "*_(Instrumental)_*.flac"),
        os.path.join(run_output_dir, "**", "*_(Instrumental)_*.wav"),
        os.path.join(run_output_dir, "**", "*.instrumental.wav"),
        os.path.join(run_output_dir, "**", "*no_vocals*.wav"),
        os.path.join(run_output_dir, "**", "*no_vocals*.flac"),
    ])

    if not vocals_path:
        raise RuntimeError(
            f"Stem separation completed but no vocals stem was found in: {run_output_dir}"
        )

    print(f"  Vocals stem selected for analysis: {vocals_path}")
    if instrumental_path:
        print(f"  Instrumental stem saved: {instrumental_path}")

    return {
        "enabled": True,
        "script_path": absolute_script_path,
        "output_dir": run_output_dir,
        "vocals_path": vocals_path,
        "instrumental_path": instrumental_path,
    }


def load_audio(wav_path):
    """
    Loads a WAV file into a numpy array using librosa.
    Returns (y, sr) — the audio signal and sample rate.
    """
    y, sr = librosa.load(wav_path, sr=44100, mono=True)
    return y, sr


def hz_to_note_safe(hz):
    """Safely converts Hz to note name, handling edge cases."""
    try:
        if hz > 0:
            return librosa.hz_to_note(float(hz))
        return "N/A"
    except Exception:
        return "N/A"


def hz_to_cents(hz_values):
    """Converts Hz to cents relative to A4 = 440 Hz (NaN-safe)."""
    hz_values = np.asarray(hz_values, dtype=float)
    out = np.full(hz_values.shape, np.nan)
    valid = np.isfinite(hz_values) & (hz_values > 0)
    out[valid] = 1200.0 * np.log2(hz_values[valid] / 440.0)
    return out


def moving_average(values, window_frames):
    """Centred moving average with reflected edges (window forced odd, >=3)."""
    window_frames = max(3, int(window_frames) | 1)
    if len(values) < window_frames:
        return np.full(len(values), np.mean(values))
    padded = np.pad(values, window_frames // 2, mode='reflect')
    kernel = np.ones(window_frames) / window_frames
    return np.convolve(padded, kernel, mode='valid')


def safe_float(value, decimals=None):
    """Converts to a JSON-safe float, mapping NaN/inf to None."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return round(value, decimals) if decimals is not None else value


# =============================================================================
# VOICED-SEGMENT AND NOTE SEGMENTATION
# =============================================================================

def segment_voiced_runs(f0, hop_length, sr, min_duration_s=NOTE_MIN_DURATION_S,
                        bridge_frames=VOICED_GAP_BRIDGE_FRAMES):
    """
    Finds contiguous runs of voiced frames in the F0 track, bridging very
    short unvoiced gaps. Returns a list of (start_frame, end_frame) pairs
    (end exclusive). All downstream voice-quality analysis is restricted to
    these runs so that pauses and consonants never contaminate the metrics.
    """
    voiced = np.isfinite(f0)
    if bridge_frames > 0:
        voiced_bridged = voiced.copy()
        gap_start = None
        for i, v in enumerate(voiced):
            if v:
                if gap_start is not None and 0 < i - gap_start <= bridge_frames:
                    voiced_bridged[gap_start:i] = True
                gap_start = None
            elif gap_start is None:
                gap_start = i
        voiced = voiced_bridged

    min_frames = max(3, int(min_duration_s * sr / hop_length))
    runs = []
    start = None
    for i, v in enumerate(voiced):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_frames:
                runs.append((start, i))
            start = None
    if start is not None and len(voiced) - start >= min_frames:
        runs.append((start, len(voiced)))
    return runs


def segment_sustained_notes(f0, hop_length, sr, min_duration_s=NOTE_MIN_DURATION_S):
    """
    Splits voiced runs into sustained-note segments at melodic pitch jumps.

    The pitch contour is median-filtered so vibrato does not trigger splits,
    then a new note begins wherever the smoothed contour jumps more than
    NOTE_SPLIT_CENTS between adjacent frames.

    Returns a list of dicts: {start, end, start_s, end_s, duration_s,
    median_hz, cents_contour (relative to A440)}.
    """
    frame_s = hop_length / sr
    min_frames = max(3, int(min_duration_s / frame_s))
    notes = []

    for run_start, run_end in segment_voiced_runs(f0, hop_length, sr,
                                                  min_duration_s=min_duration_s):
        seg_f0 = f0[run_start:run_end].copy()
        # Fill bridged NaN frames by interpolation inside the run
        nans = ~np.isfinite(seg_f0)
        if nans.any():
            seg_f0[nans] = np.interp(
                np.flatnonzero(nans), np.flatnonzero(~nans), seg_f0[~nans]
            )
        cents = hz_to_cents(seg_f0)
        smoothed = scipy.signal.medfilt(cents, kernel_size=5)
        jumps = np.abs(np.diff(smoothed))
        split_points = np.flatnonzero(jumps > NOTE_SPLIT_CENTS) + 1

        boundaries = [0, *split_points.tolist(), len(seg_f0)]
        for b_start, b_end in zip(boundaries[:-1], boundaries[1:]):
            if b_end - b_start < min_frames:
                continue
            note_f0 = seg_f0[b_start:b_end]
            notes.append({
                "start": run_start + b_start,
                "end": run_start + b_end,
                "start_s": (run_start + b_start) * frame_s,
                "end_s": (run_start + b_end) * frame_s,
                "duration_s": (b_end - b_start) * frame_s,
                "median_hz": float(np.median(note_f0)),
                "cents_contour": hz_to_cents(note_f0),
            })
    return notes


def segment_phrases(f0, hop_length, sr):
    """
    Groups voiced runs separated by less than PHRASE_GAP_BRIDGE_S into
    phrases. Used for breath/phrase-length metrics.
    """
    frame_s = hop_length / sr
    runs = segment_voiced_runs(f0, hop_length, sr, min_duration_s=0.1)
    if not runs:
        return []
    max_gap_frames = int(PHRASE_GAP_BRIDGE_S / frame_s)
    phrases = [list(runs[0])]
    for start, end in runs[1:]:
        if start - phrases[-1][1] <= max_gap_frames:
            phrases[-1][1] = end
        else:
            phrases.append([start, end])
    return [
        {"start_s": s * frame_s, "end_s": e * frame_s, "duration_s": (e - s) * frame_s}
        for s, e in phrases
    ]


# =============================================================================
# ANALYSIS MODULES
# =============================================================================

def analyse_pitch(y, sr, hop_length=512):
    """
    MODULE 1: PITCH ANALYSIS
    ─────────────────────────
    Uses the pyin algorithm (Probabilistic YIN) to extract the fundamental
    frequency (F0) over time. pyin is more robust than basic autocorrelation
    and handles distorted/raspy vocals better than naive methods.

    The reported pitch range uses the 2.5th–97.5th percentile of voiced
    frames ("robust range"): a single octave-error frame from the tracker
    would otherwise wildly inflate the range. The absolute min/max frames
    are still reported separately for reference.

    Returns a dict of pitch statistics.
    """
    print("  [1/10] Pitch analysis (pyin)...")

    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=librosa.note_to_hz(PYIN_FMIN_NOTE),
        fmax=librosa.note_to_hz(PYIN_FMAX_NOTE),
        sr=sr,
        frame_length=2048,
        hop_length=hop_length
    )

    voiced_f0 = f0[~np.isnan(f0)]
    n_total = len(f0)
    n_voiced = len(voiced_f0)

    if n_voiced < 10:
        return {"error": "Insufficient voiced frames detected. Check audio quality."}

    p2_5 = float(np.percentile(voiced_f0, 2.5))
    p97_5 = float(np.percentile(voiced_f0, 97.5))
    robust_range_semitones = round(12 * np.log2(p97_5 / p2_5), 1) if p2_5 > 0 else 0
    full_range_semitones = round(
        12 * np.log2(np.max(voiced_f0) / np.min(voiced_f0)), 1
    ) if np.min(voiced_f0) > 0 else 0

    # Per-section pitch stability (10-second windows)
    window_frames = int(10 * sr / hop_length)
    n_windows = n_total // window_frames
    sections = []
    for i in range(n_windows):
        start = i * window_frames
        end = (i + 1) * window_frames
        sec_f0 = f0[start:end]
        sec_voiced = sec_f0[~np.isnan(sec_f0)]
        if len(sec_voiced) > 5:
            mean_hz = float(np.mean(sec_voiced))
            std_hz = float(np.std(sec_voiced))
            cv = (std_hz / mean_hz * 100) if mean_hz > 0 else 0
            sections.append({
                "time_range": f"{i*10}-{(i+1)*10}s",
                "mean_hz": round(mean_hz, 2),
                "mean_note": hz_to_note_safe(mean_hz),
                "std_hz": round(std_hz, 2),
                "cv_percent": round(cv, 2),
                "voiced_pct": round(len(sec_voiced) / len(sec_f0) * 100, 1)
            })

    return {
        "mean_hz": round(float(np.mean(voiced_f0)), 2),
        "median_hz": round(float(np.median(voiced_f0)), 2),
        "min_hz": round(float(np.min(voiced_f0)), 2),
        "max_hz": round(float(np.max(voiced_f0)), 2),
        "std_hz": round(float(np.std(voiced_f0)), 2),
        "mean_note": hz_to_note_safe(np.mean(voiced_f0)),
        "median_note": hz_to_note_safe(np.median(voiced_f0)),
        "min_note": hz_to_note_safe(np.min(voiced_f0)),
        "max_note": hz_to_note_safe(np.max(voiced_f0)),
        "robust_min_hz": round(p2_5, 2),
        "robust_max_hz": round(p97_5, 2),
        "robust_min_note": hz_to_note_safe(p2_5),
        "robust_max_note": hz_to_note_safe(p97_5),
        "range_semitones": robust_range_semitones,
        "range_semitones_note": "Robust range (2.5th-97.5th percentile of voiced frames). Immune to single octave-error frames.",
        "full_range_semitones": full_range_semitones,
        "voiced_percentage": round(n_voiced / n_total * 100, 1),
        "p25_hz": round(float(np.percentile(voiced_f0, 25)), 2),
        "p75_hz": round(float(np.percentile(voiced_f0, 75)), 2),
        "p95_hz": round(float(np.percentile(voiced_f0, 95)), 2),
        "sections": sections,
        "raw_f0": f0  # Keep for downstream segment analysis
    }


def analyse_voice_quality(wav_path, f0, sr, hop_length=512):
    """
    MODULE 2: VOICE QUALITY — JITTER, SHIMMER, HNR (Praat)
    ────────────────────────────────────────────────────────
    Clinical-grade perturbation analysis using Praat algorithms via
    parselmouth, computed PER SUSTAINED NOTE and aggregated with the median.

    Why per-note: jitter/shimmer are defined for sustained phonation. A sung
    melody moves between pitches by design; measuring across note changes
    (or worse, across pauses) counts musicianship as pathology. Restricting
    each measurement window to one sustained note removes that bias.

    Reported thresholds: the classic 1.04% jitter / 3.81% shimmer figures
    are speech-pathology norms for sustained spoken vowels. Sung notes with
    vibrato naturally run slightly higher, so interpretation bands here are
    singing-oriented and clearly labelled.

    Falls back to a frame-based F0 approximation (clearly labelled
    low-reliability, jitter only) if parselmouth is not installed.
    """
    print("  [2/10] Voice quality — jitter/shimmer/HNR...")

    notes = segment_sustained_notes(f0, hop_length, sr)
    long_notes = [n for n in notes if n["duration_s"] >= NOTE_MIN_DURATION_S]

    if not long_notes:
        return {
            "error": "No sustained notes (>= 0.25 s) found — cannot measure voice quality.",
            "method": "none",
            "reliability": "none",
        }

    if not PARSELMOUTH_AVAILABLE:
        return _voice_quality_fallback(long_notes)

    snd = parselmouth.Sound(wav_path)
    point_process = praat_call(
        snd, "To PointProcess (periodic, cc)", PRAAT_PITCH_FLOOR, PRAAT_PITCH_CEILING
    )
    harmonicity = snd.to_harmonicity_cc(
        time_step=0.01,
        minimum_pitch=PRAAT_PITCH_FLOOR,
        silence_threshold=0.1,
        periods_per_window=1.0,
    )

    per_note = {"jitter_local": [], "jitter_rap": [], "jitter_ppq5": [],
                "shimmer_local": [], "shimmer_apq3": [], "shimmer_db": [],
                "hnr_db": []}

    for note in long_notes:
        t0, t1 = note["start_s"], note["end_s"]
        try:
            values = {
                "jitter_local": praat_call(point_process, "Get jitter (local)", t0, t1, 0.0001, 0.02, 1.3) * 100,
                "jitter_rap": praat_call(point_process, "Get jitter (rap)", t0, t1, 0.0001, 0.02, 1.3) * 100,
                "jitter_ppq5": praat_call(point_process, "Get jitter (ppq5)", t0, t1, 0.0001, 0.02, 1.3) * 100,
                "shimmer_local": praat_call([snd, point_process], "Get shimmer (local)", t0, t1, 0.0001, 0.02, 1.3, 1.6) * 100,
                "shimmer_apq3": praat_call([snd, point_process], "Get shimmer (apq3)", t0, t1, 0.0001, 0.02, 1.3, 1.6) * 100,
                "shimmer_db": praat_call([snd, point_process], "Get shimmer (local_dB)", t0, t1, 0.0001, 0.02, 1.3, 1.6),
                "hnr_db": praat_call(harmonicity, "Get mean", t0, t1),
            }
        except Exception:
            continue
        for key, value in values.items():
            if value is not None and math.isfinite(value):
                per_note[key].append(float(value))

    n_measured = len(per_note["jitter_local"])
    if n_measured == 0:
        return _voice_quality_fallback(long_notes)

    def median_of(key, decimals=4):
        return safe_float(np.median(per_note[key]), decimals) if per_note[key] else None

    jitter_med = median_of("jitter_local")
    shimmer_med = median_of("shimmer_local")
    hnr_med = median_of("hnr_db", 2)

    return {
        "method": "praat_parselmouth_per_sustained_note",
        "reliability": "high" if n_measured >= 5 else "medium",
        "n_notes_measured": n_measured,
        "n_sustained_notes_found": len(long_notes),
        "jitter_local_percent_median": jitter_med,
        "jitter_rap_percent_median": median_of("jitter_rap"),
        "jitter_ppq5_percent_median": median_of("jitter_ppq5"),
        "shimmer_local_percent_median": shimmer_med,
        "shimmer_apq3_percent_median": median_of("shimmer_apq3"),
        "shimmer_local_db_median": median_of("shimmer_db"),
        "hnr_db_median": hnr_med,
        "hnr_db_p25": safe_float(np.percentile(per_note["hnr_db"], 25), 2) if per_note["hnr_db"] else None,
        "hnr_db_p75": safe_float(np.percentile(per_note["hnr_db"], 75), 2) if per_note["hnr_db"] else None,
        "interpretation": _interpret_voice_quality(jitter_med, shimmer_med, hnr_med),
        "reference": {
            "speech_pathology_jitter_pct": JITTER_THRESHOLD_PCT,
            "speech_pathology_shimmer_pct": SHIMMER_THRESHOLD_PCT,
            "note": "Speech norms are for sustained spoken vowels; sung notes with vibrato run naturally higher. Interpretation above uses singing-oriented bands.",
        },
    }


def _voice_quality_fallback(long_notes):
    """
    Frame-based jitter approximation, restricted to within-note windows.
    Only used when parselmouth is unavailable. Shimmer and HNR are NOT
    reported here — an unreliable number is worse than an honest gap.
    """
    per_note_jitter = []
    for note in long_notes:
        contour = note["cents_contour"]
        if len(contour) < 8:
            continue
        # Remove slow melodic/vibrato movement; residual reflects instability
        residual = contour - moving_average(contour, 7)
        hz = note["median_hz"] * (2 ** (residual / 1200.0))
        periods = 1.0 / hz
        jitter = np.mean(np.abs(np.diff(periods))) / np.mean(periods) * 100
        per_note_jitter.append(float(jitter))

    return {
        "method": "frame_f0_approximation",
        "reliability": "low",
        "note": (
            "parselmouth is not installed — this is a coarse frame-level "
            "approximation, not clinical jitter. Install praat-parselmouth "
            "for real cycle-to-cycle measurements. Shimmer and HNR are "
            "intentionally omitted rather than guessed."
        ),
        "n_notes_measured": len(per_note_jitter),
        "n_sustained_notes_found": len(long_notes),
        "jitter_local_percent_median": safe_float(np.median(per_note_jitter), 4) if per_note_jitter else None,
        "shimmer_local_percent_median": None,
        "hnr_db_median": None,
        "interpretation": "Unavailable at full reliability (parselmouth missing).",
    }


def _interpret_voice_quality(jitter_pct, shimmer_pct, hnr_db):
    """Singing-oriented interpretation of sustained-note voice quality."""
    if jitter_pct is None and hnr_db is None:
        return "Insufficient data."
    concerns = []
    if hnr_db is not None:
        if hnr_db >= SINGING_HNR_GOOD_DB:
            concerns.append("clean, well-supported phonation")
        elif hnr_db >= 8:
            concerns.append("mild breathiness or intentional grit")
        else:
            concerns.append("heavy breathiness/distortion (verify capture quality)")
    if jitter_pct is not None:
        if jitter_pct <= SINGING_JITTER_GOOD_PCT:
            concerns.append("very stable fold vibration")
        elif jitter_pct <= 1.5:
            concerns.append("normal sung-note perturbation")
        else:
            concerns.append("elevated frequency perturbation")
    if shimmer_pct is not None and shimmer_pct > 2 * SINGING_SHIMMER_GOOD_PCT:
        concerns.append("elevated amplitude perturbation")
    return "; ".join(concerns).capitalize() + "."


def analyse_harmonic_balance(y):
    """
    MODULE 3: HARMONIC / RESIDUAL BALANCE (HPSS)
    ──────────────────────────────────────────────
    Separates the audio into harmonic and residual components using HPSS and
    computes the whole-file energy ratio.

    IMPORTANT: this is a global tonal-balance descriptor, NOT clinical HNR.
    (Earlier versions mislabelled it "HNR" — real HNR is per-frame
    autocorrelation harmonicity on voiced segments, reported by the voice
    quality module.) It includes silence and consonants, so use it only as a
    rough texture indicator.
    """
    print("  [3/10] Harmonic/residual balance (HPSS)...")

    y_harmonic, y_percussive = librosa.effects.hpss(y)
    harmonic_power = float(np.mean(y_harmonic ** 2))
    noise = y - y_harmonic
    noise_power = float(np.mean(noise ** 2))

    ratio_db = 10 * np.log10(harmonic_power / noise_power) if noise_power > 0 else 99.0
    percussive_power = float(np.mean(y_percussive ** 2))
    hpr_db = 10 * np.log10(harmonic_power / percussive_power) if percussive_power > 0 else 99.0

    return {
        "harmonic_residual_db": round(float(ratio_db), 2),
        "harmonic_percussive_db": round(float(hpr_db), 2),
        "method": "hpss_whole_file",
        "note": (
            "Global tonal-balance descriptor over the whole file (includes "
            "silence/consonants). NOT clinical HNR — see voice_quality.hnr_db_median."
        ),
    }


def analyse_resonance(y, sr, hop_length=512):
    """
    MODULE 4: RESONANCE ANALYSIS
    ──────────────────────────────
    Spectral Centroid: The 'centre of mass' of the spectrum. High values
    indicate bright, forward resonance. Low values indicate dark, swallowed tone.

    Spectral Rolloff: The frequency below which X% of the spectral energy lies.
    Spectral Flatness: 0 = perfectly tonal (sine wave); 1 = white noise.

    All statistics are computed over ACTIVE frames only (frame RMS above the
    silence threshold). On isolated stems with long silent gaps, unmuted
    low-level noise would otherwise dominate the averages and skew the
    brightness classification.
    """
    print("  [4/10] Resonance analysis (active frames only)...")

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    active_mask = rms_db > SILENCE_THRESHOLD_DB

    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    rolloff_85 = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length, roll_percent=0.85)[0]
    rolloff_95 = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length, roll_percent=0.95)[0]
    flatness = librosa.feature.spectral_flatness(y=y, hop_length=hop_length)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length)[0]
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=hop_length)

    n_frames = min(len(active_mask), len(centroid))
    mask = active_mask[:n_frames]
    if not mask.any():
        return {"error": "No active frames above the silence threshold."}

    centroid, flatness, bandwidth = centroid[:n_frames][mask], flatness[:n_frames][mask], bandwidth[:n_frames][mask]
    rolloff_85, rolloff_95 = rolloff_85[:n_frames][mask], rolloff_95[:n_frames][mask]
    contrast = contrast[:, :n_frames][:, mask]

    mean_centroid = float(np.mean(centroid))
    resonance_class = (
        "Dark / Swallowed" if mean_centroid < CENTROID_DARK_THRESHOLD else
        "Neutral / Balanced" if mean_centroid < CENTROID_BRIGHT_THRESHOLD else
        "Bright / Forward / Twangy"
    )

    return {
        "spectral_centroid_mean_hz": round(mean_centroid, 2),
        "spectral_centroid_median_hz": round(float(np.median(centroid)), 2),
        "spectral_rolloff_85_mean_hz": round(float(np.mean(rolloff_85)), 2),
        "spectral_rolloff_95_mean_hz": round(float(np.mean(rolloff_95)), 2),
        "spectral_flatness_mean": round(float(np.mean(flatness)), 6),
        "spectral_bandwidth_mean_hz": round(float(np.mean(bandwidth)), 2),
        "spectral_contrast_overall_mean_db": round(float(np.mean(contrast)), 2),
        "active_frame_percentage": round(float(np.mean(mask)) * 100, 1),
        "resonance_classification": resonance_class,
        "method": "librosa_active_frames_only",
    }


def analyse_dynamics(y, sr, f0=None, hop_length=512):
    """
    MODULE 5: DYNAMICS ANALYSIS
    ─────────────────────────────
    RMS Energy measures the loudness of the signal over time.
    Effective Dynamic Range (P10-P90) removes outliers for a realistic measure.

    Note: dB values are relative to the loudest frame in THIS file (ref=max),
    so they describe internal contrast, not absolute loudness.

    Also reports phrase-level dynamic shaping: the spread of per-phrase mean
    levels, which captures light-and-shade across the performance.
    """
    print("  [5/10] Dynamics analysis...")

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    active = rms_db[rms_db > SILENCE_THRESHOLD_DB]

    if len(active) == 0:
        return {"error": "No active audio frames detected."}

    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]

    result = {
        "mean_rms_db": round(float(np.mean(active)), 2),
        "median_rms_db": round(float(np.median(active)), 2),
        "full_dynamic_range_db": round(float(np.max(active) - np.min(active)), 2),
        "effective_dynamic_range_db": round(float(np.percentile(active, 90) - np.percentile(active, 10)), 2),
        "p10_db": round(float(np.percentile(active, 10)), 2),
        "p90_db": round(float(np.percentile(active, 90)), 2),
        "zcr_mean": round(float(np.mean(zcr)), 6),
        "reference_note": "dB relative to the loudest frame in this file (internal contrast, not absolute loudness).",
    }

    if f0 is not None:
        phrases = segment_phrases(f0, hop_length, sr)
        phrase_levels = []
        for phrase in phrases:
            i0 = int(phrase["start_s"] * sr / hop_length)
            i1 = min(int(phrase["end_s"] * sr / hop_length), len(rms_db))
            if i1 > i0:
                phrase_levels.append(float(np.mean(rms_db[i0:i1])))
        if len(phrase_levels) >= 3:
            result["phrase_level_spread_db"] = round(float(np.percentile(phrase_levels, 90) - np.percentile(phrase_levels, 10)), 2)
            result["n_phrases"] = len(phrase_levels)

    return result


def analyse_rhythm(y, sr, is_isolated_stem=False, hop_length=512):
    """
    MODULE 6: RHYTHM AND ONSET ANALYSIS
    ─────────────────────────────────────
    Onset detection identifies the start of each note/syllable.
    Onset rate (onsets/second) indicates how densely packed the delivery is.

    Tempo estimation via beat tracking is designed for full mixes with
    percussive content — on an isolated vocal stem it is LOW CONFIDENCE and
    flagged as such.
    """
    print("  [6/10] Rhythm and onset analysis...")

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    tempo_val = float(tempo) if np.isscalar(tempo) else float(tempo[0])

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length, onset_envelope=onset_env)
    onset_times = librosa.frames_to_time(onsets, sr=sr, hop_length=hop_length)
    duration = librosa.get_duration(y=y, sr=sr)

    ioi_stats = {}
    if len(onset_times) > 1:
        ioi = np.diff(onset_times)
        ioi_stats = {
            "mean_ioi_s": round(float(np.mean(ioi)), 4),
            "std_ioi_s": round(float(np.std(ioi)), 4),
            "rhythmic_regularity": round(float(1.0 - np.std(ioi) / np.mean(ioi)), 4)
        }

    return {
        "estimated_tempo_bpm": round(tempo_val, 1),
        "tempo_confidence": "low (isolated vocal stem — beat tracking expects a full mix)" if is_isolated_stem else "medium",
        "total_onsets": len(onsets),
        "onsets_per_second": round(len(onsets) / duration, 2),
        **ioi_stats
    }


def analyse_formants(wav_path, y, sr, f0, hop_length=512, formant_ceiling=5500.0):
    """
    MODULE 7: FORMANT ANALYSIS
    ────────────────────────────
    Formants are the resonant frequencies of the vocal tract.
    F1 correlates with jaw height; F2 with tongue position.

    Primary method: Praat Burg algorithm (via parselmouth), sampled at the
    centres of sustained voiced notes only, aggregated with median +/- IQR.

    Fallback (parselmouth missing): LPC on audio DOWNSAMPLED to ~11 kHz with
    order ~= sr/1000 + 2, voiced frames only. (LPC order 12 at 44.1 kHz — the
    old approach — cannot resolve vocal-tract formants and produced noise.)
    """
    print("  [7/10] Formant analysis...")

    notes = segment_sustained_notes(f0, hop_length, sr)
    if not notes:
        return {"error": "No sustained voiced notes for formant analysis.", "method": "none"}

    if PARSELMOUTH_AVAILABLE:
        snd = parselmouth.Sound(wav_path)
        formant = snd.to_formant_burg(
            time_step=0.01,
            max_number_of_formants=5,
            maximum_formant=formant_ceiling,
            window_length=0.025,
            pre_emphasis_from=50.0,
        )
        samples = {1: [], 2: [], 3: []}
        for note in notes:
            # Sample a few points inside each sustained note
            for frac in (0.3, 0.5, 0.7):
                t = note["start_s"] + frac * note["duration_s"]
                for i in (1, 2, 3):
                    value = formant.get_value_at_time(i, t)
                    if value is not None and math.isfinite(value):
                        samples[i].append(float(value))
        if not samples[1]:
            return {"error": "Praat returned no valid formant samples.", "method": "praat_burg"}
        result = {"method": "praat_burg_sustained_notes", "reliability": "high",
                  "formant_ceiling_hz": formant_ceiling,
                  "n_samples": len(samples[1])}
        for i in (1, 2, 3):
            if samples[i]:
                arr = np.array(samples[i])
                result[f"F{i}_median_hz"] = round(float(np.median(arr)), 1)
                result[f"F{i}_iqr_hz"] = round(float(np.percentile(arr, 75) - np.percentile(arr, 25)), 1)
        return result

    # ── Fallback: correctly-scaled LPC ────────────────────────────────────
    target_sr = 11025
    y_ds = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
    order = int(target_sr / 1000) + 2

    def get_formants(chunk):
        pre_emphasis = 0.97
        chunk_pe = np.append(chunk[0], chunk[1:] - pre_emphasis * chunk[:-1])
        try:
            a = librosa.lpc(chunk_pe, order=order)
            roots = np.roots(a)
            roots = roots[np.imag(roots) >= 0.01]
            angles = np.arctan2(np.imag(roots), np.real(roots))
            freqs = sorted(angles * (target_sr / (2 * np.pi)))
            freqs = [freq for freq in freqs if 200 < freq < target_sr / 2 - 200]
            return freqs[:3] if len(freqs) >= 3 else None
        except Exception:
            return None

    chunk_size = int(0.03 * target_sr)
    samples = []
    for note in notes:
        start = int(note["start_s"] * target_sr)
        end = int(note["end_s"] * target_sr)
        for cstart in range(start, end - chunk_size, chunk_size * 2):
            chunk = y_ds[cstart:cstart + chunk_size]
            if len(chunk) == chunk_size and np.max(np.abs(chunk)) > 0.01:
                freqs = get_formants(chunk)
                if freqs:
                    samples.append(freqs)

    if not samples:
        return {"error": "Could not estimate formants.", "method": "lpc_downsampled"}

    arr = np.array(samples)
    return {
        "method": "lpc_downsampled_11kHz_voiced_only",
        "reliability": "medium",
        "note": "LPC fallback. Install praat-parselmouth for Burg-method formants.",
        "F1_median_hz": round(float(np.median(arr[:, 0])), 1),
        "F2_median_hz": round(float(np.median(arr[:, 1])), 1),
        "F3_median_hz": round(float(np.median(arr[:, 2])), 1),
        "n_samples": len(samples),
    }


def analyse_vibrato(f0, sr, hop_length=512):
    """
    MODULE 8: PER-NOTE VIBRATO ANALYSIS
    ─────────────────────────────────────
    Vibrato is a periodic pitch modulation, typically 4-8 Hz, on SUSTAINED
    notes. Each note >= 0.5 s is analysed individually:

      1. Convert the note's pitch contour to cents.
      2. Remove the slow melodic trend (moving average) so only the
         oscillation remains.
      3. FFT the residual; a prominent peak in the vibrato band with a
         musically plausible extent counts as vibrato.

    (A single FFT over the whole song's contour — the old approach — mostly
    measures the rate of note changes, not vibrato.)

    Reports per-note rate/extent plus aggregate statistics. Professional
    vibrato typically runs ~5-7 Hz at 20-150 cents extent with high
    regularity.
    """
    print("  [8/10] Vibrato analysis (per sustained note)...")

    pitch_sr = sr / hop_length
    notes = [n for n in segment_sustained_notes(f0, hop_length, sr)
             if n["duration_s"] >= VIBRATO_NOTE_MIN_S]

    if not notes:
        return {
            "error": f"No sustained notes >= {VIBRATO_NOTE_MIN_S}s — vibrato cannot be assessed.",
            "n_notes_analysed": 0,
        }

    per_note = []
    for note in notes:
        contour = note["cents_contour"]
        trend = moving_average(contour, int(0.35 * pitch_sr))
        residual = contour - trend
        windowed = residual * np.hanning(len(residual))
        spectrum = np.abs(np.fft.rfft(windowed)) ** 2
        freqs = np.fft.rfftfreq(len(windowed), d=1.0 / pitch_sr)

        search = (freqs >= VIBRATO_SEARCH_MIN_HZ) & (freqs <= VIBRATO_SEARCH_MAX_HZ)
        total = (freqs >= 0.5)
        if not search.any() or spectrum[total].sum() <= 0:
            continue

        peak_idx = np.argmax(spectrum[search])
        rate = float(freqs[search][peak_idx])
        # Peak band power (peak bin +/- ~0.75 Hz) vs all modulation power
        band = (freqs >= rate - 0.75) & (freqs <= rate + 0.75)
        band_ratio = float(spectrum[band].sum() / spectrum[total].sum())
        extent = float((np.percentile(residual, 97.5) - np.percentile(residual, 2.5)) / 2)

        has_vibrato = (
            VIBRATO_RATE_MIN_HZ <= rate <= VIBRATO_RATE_MAX_HZ
            and band_ratio >= VIBRATO_MIN_BAND_RATIO
            and VIBRATO_MIN_EXTENT_CENTS <= extent <= VIBRATO_MAX_EXTENT_CENTS
        )
        per_note.append({
            "start_s": round(note["start_s"], 2),
            "duration_s": round(note["duration_s"], 2),
            "note": hz_to_note_safe(note["median_hz"]),
            "rate_hz": round(rate, 2),
            "extent_cents": round(extent, 1),
            "band_power_ratio": round(band_ratio, 3),
            "has_vibrato": has_vibrato,
        })

    if not per_note:
        return {"error": "Vibrato analysis produced no valid notes.", "n_notes_analysed": 0}

    vibrato_notes = [n for n in per_note if n["has_vibrato"]]
    pct = len(vibrato_notes) / len(per_note) * 100

    summary = {
        "method": "per_note_fft_of_detrended_cents_contour",
        "n_notes_analysed": len(per_note),
        "n_notes_with_vibrato": len(vibrato_notes),
        "pct_notes_with_vibrato": round(pct, 1),
        "notes": per_note,
    }
    if vibrato_notes:
        summary["median_rate_hz"] = round(float(np.median([n["rate_hz"] for n in vibrato_notes])), 2)
        summary["median_extent_cents"] = round(float(np.median([n["extent_cents"] for n in vibrato_notes])), 1)
        summary["median_regularity"] = round(float(np.median([n["band_power_ratio"] for n in vibrato_notes])), 3)
    summary["classification"] = (
        "Consistent vibrato" if pct >= 60 else
        "Selective vibrato" if pct >= 25 else
        "Minimal vibrato"
    )
    return summary


def analyse_intonation(f0, sr, hop_length=512):
    """
    MODULE 9: INTONATION ANALYSIS
    ───────────────────────────────
    Measures how accurately sustained notes sit on the equal-tempered pitch
    grid — the closest audio-only proxy for "singing in tune" without a
    reference melody.

      1. Each sustained note's median pitch -> cents deviation from the
         nearest semitone.
      2. A global tuning offset (median deviation) is removed first, so a
         track tuned slightly off A440 (common on older records/tape) is
         not penalised.
      3. Also reports intra-note drift: how much the slow (vibrato-removed)
         contour wanders within each note.

    Professional reference: median absolute deviation under ~10 cents reads
    as in tune; under ~5 cents is exceptional. The just-noticeable
    difference for most listeners is roughly 10-25 cents in melodic context.
    """
    print("  [9/10] Intonation analysis...")

    pitch_sr = sr / hop_length
    notes = segment_sustained_notes(f0, hop_length, sr)
    if len(notes) < 3:
        return {"error": "Fewer than 3 sustained notes — intonation cannot be assessed.",
                "n_notes": len(notes)}

    # Deviation of each note's median pitch from the nearest semitone, in cents
    raw_devs = []
    for note in notes:
        cents_abs = 1200.0 * np.log2(note["median_hz"] / 440.0)
        dev = ((cents_abs + 50) % 100) - 50   # -> [-50, 50)
        raw_devs.append(dev)
    raw_devs = np.array(raw_devs)

    tuning_offset = float(np.median(raw_devs))
    devs = raw_devs - tuning_offset
    # Re-wrap in case offset removal pushed values past +/-50
    devs = ((devs + 50) % 100) - 50
    abs_devs = np.abs(devs)

    # Intra-note drift of the slow contour (vibrato excluded by smoothing)
    drifts = []
    for note in notes:
        contour = note["cents_contour"]
        slow = moving_average(contour, int(0.35 * pitch_sr))
        drifts.append(float(np.percentile(slow, 95) - np.percentile(slow, 5)))

    median_abs = float(np.median(abs_devs))
    return {
        "method": "sustained_note_deviation_from_equal_tempered_grid",
        "n_notes": len(notes),
        "tuning_offset_cents": round(tuning_offset, 1),
        "median_abs_deviation_cents": round(median_abs, 1),
        "p90_abs_deviation_cents": round(float(np.percentile(abs_devs, 90)), 1),
        "pct_notes_within_10_cents": round(float(np.mean(abs_devs <= 10) * 100), 1),
        "pct_notes_within_25_cents": round(float(np.mean(abs_devs <= 25) * 100), 1),
        "median_intra_note_drift_cents": round(float(np.median(drifts)), 1),
        "classification": (
            "Exceptional accuracy" if median_abs <= 5 else
            "Professional accuracy" if median_abs <= 10 else
            "Good accuracy" if median_abs <= 20 else
            "Inconsistent intonation" if median_abs <= 35 else
            "Poor intonation (or unreliable pitch tracking — check capture quality)"
        ),
        "caveat": (
            "Grid-deviation is a proxy: expressive slides, blue notes and "
            "non-12-TET material register as deviation. Interpret alongside "
            "the recording context."
        ),
    }


def analyse_time_diagnostics(y, sr, f0, pitch_results, dynamics_results, resonance_results, hop_length=512):
    """
    MODULE 10: TIME-BASED DIAGNOSTICS
    Summarises time-based diagnostics for Candi.

    These are supporting indicators for coaching, especially on karaoke/live-room
    recordings where backing track bleed and room noise can confuse F0 detection.
    """
    print("  [10/10] Time diagnostics...")
    duration = librosa.get_duration(y=y, sr=sr)
    block_seconds = 10
    block_size = sr * block_seconds
    energy_blocks = []

    for start in range(0, len(y), block_size):
        block = y[start:start + block_size]
        if len(block) < 100:
            continue
        block_rms = np.sqrt(np.mean(block ** 2))
        block_db = librosa.amplitude_to_db(np.array([block_rms]), ref=1.0)[0]
        energy_blocks.append({
            "time_range": f"{start / sr:.0f}-{min((start + block_size) / sr, duration):.0f}s",
            "rms_db": round(float(block_db), 2),
        })

    problem_zones = []
    for section in pitch_results.get("sections", []):
        if section.get("cv_percent", 0) > 30:
            problem_zones.append({
                "time_range": section.get("time_range"),
                "category": "Pitch",
                "flag": "unstable_f0",
                "value": f"{section.get('cv_percent')}% CV",
                "note": "F0 varied heavily in this 10-second window. Treat cautiously if backing vocals or room noise are present.",
            })
        elif section.get("voiced_pct", 100) < 15:
            problem_zones.append({
                "time_range": section.get("time_range"),
                "category": "Pitch",
                "flag": "low_voiced_detection",
                "value": f"{section.get('voiced_pct')}% voiced",
                "note": "Low reliable vocal pitch detection in this window.",
            })

    effective_range = dynamics_results.get("effective_dynamic_range_db")
    if effective_range is not None and effective_range < 12:
        problem_zones.append({
            "time_range": "whole_take",
            "category": "Dynamics",
            "flag": "compressed_loudness",
            "value": f"{effective_range} dB effective range",
            "note": "Delivery stayed in a narrow intensity band.",
        })

    centroid = resonance_results.get("spectral_centroid_mean_hz")
    if centroid is not None and centroid > CENTROID_BRIGHT_THRESHOLD:
        problem_zones.append({
            "time_range": "whole_take",
            "category": "Resonance",
            "flag": "bright_forward_spectrum",
            "value": f"{centroid} Hz mean centroid",
            "note": "Strong forward/bright energy. Useful for cut, but can also include room bleed or harsh mic capture.",
        })

    peak_amplitude = float(np.max(np.abs(y))) if len(y) else 0.0
    clipped_sample_pct = float(np.mean(np.abs(y) >= 0.98) * 100) if len(y) else 0.0
    voiced_pct = pitch_results.get("voiced_percentage", 0)
    hnr_like_risk = clipped_sample_pct > 0.05 or peak_amplitude > 0.98 or voiced_pct < 35
    environment_risk = {
        "karaoke_or_room_contamination_risk": "elevated" if hnr_like_risk else "normal",
        "peak_amplitude": round(peak_amplitude, 4),
        "near_clip_sample_percent": round(clipped_sample_pct, 4),
        "voiced_percentage": voiced_pct,
        "note": (
            "Elevated risk means F0, brightness, and roughness metrics should be treated as supporting evidence, not absolute truth."
            if hnr_like_risk
            else "No obvious global capture-risk marker was detected."
        ),
    }

    return {
        "energy_blocks_10s": energy_blocks,
        "problem_zones": problem_zones,
        "environment_risk": environment_risk,
    }


# =============================================================================
# DETERMINISTIC TECHNICAL SCORE
# =============================================================================

# Default location of the professional-reference calibration file, built by
# tools/build_calibration.py from analyses of pro vocal takes.
DEFAULT_CALIBRATION_PATH = "calibration/pro_reference.json"

# Minimum number of reference values before a calibrated anchor is trusted
CALIBRATION_MIN_REFS = 5


def load_calibration(path):
    """
    Loads a pro-reference calibration file (see tools/build_calibration.py).
    Returns the parsed dict, or None if the file is absent/invalid.
    """
    if not path:
        return None
    # The repo-committed calibration is canonical; only fall back to a
    # cwd-relative file when the repo has none. (Trying cwd first once let a
    # stale test file silently shadow the real 23-reference pack.)
    candidates = [resolve_repo_path(path), path] if not os.path.isabs(path) else [path]
    resolved = next((c for c in candidates if os.path.isfile(c)), None)
    if resolved is None:
        return None
    try:
        with open(resolved) as f:
            calibration = json.load(f)
        if calibration.get("version") != "pro_reference_v1":
            print(f"  WARNING: unrecognised calibration version in {resolved} — ignoring.")
            return None
        calibration["_path"] = resolved
        return calibration
    except Exception as exc:
        print(f"  WARNING: could not load calibration {resolved}: {exc}")
        return None


def _calib_metric(calibration, key):
    """Returns the reference stats for a metric if enough references exist."""
    if not calibration:
        return None
    stats = calibration.get("metrics", {}).get(key)
    if stats and stats.get("n", 0) >= CALIBRATION_MIN_REFS:
        return stats
    return None


def _reference_percentile(value, stats, lower_is_better):
    """Share of professional references this value equals or beats (0-100)."""
    values = stats.get("values_sorted", [])
    if not values:
        return None
    values = np.asarray(values, dtype=float)
    beats = np.mean(value <= values) if lower_is_better else np.mean(value >= values)
    return round(float(beats) * 100, 1)


def _scale(value, best, worst):
    """
    Maps value linearly to a 0-10 score where `best` (or better) = 10 and
    `worst` (or beyond) = 0. Works whichever direction is "better".
    """
    if value is None:
        return None
    if best == worst:
        return 10.0
    frac = (value - worst) / (best - worst)
    return round(float(np.clip(frac, 0.0, 1.0)) * 10, 2)


def _peak_scale(value, ideal_low, ideal_high, zero_low, zero_high):
    """10 inside [ideal_low, ideal_high], falling linearly to 0 at the zero bounds."""
    if value is None:
        return None
    if ideal_low <= value <= ideal_high:
        return 10.0
    if value < ideal_low:
        return _scale(value, ideal_low, zero_low)
    return _scale(value, ideal_high, zero_high)


def _linear_component(value, key, calibration, default_best, worst, unit, lower_is_better=True):
    """
    Builds a linear component score. Without calibration, `default_best`
    earns 10. With calibration, "10" is re-anchored to the professional
    reference distribution (p25 for lower-is-better metrics, p75 for
    higher-is-better), and the value's percentile vs the references is
    reported. The theoretical `worst` (score 0) anchor is never softened.
    """
    stats = _calib_metric(calibration, key)
    if stats:
        # The pack median earns 10: "as good as a typical professional
        # reference" IS the top of the scale. Values beyond the theoretical
        # worst anchor still fall to 0, so weak takes stay low.
        best = stats["p50"]
        pct = _reference_percentile(value, stats, lower_is_better)
        formula = (f"10 at pro-reference median ({best}{unit}), "
                   f"0 at {worst}{unit}, linear")
        basis = f"= {value}{unit} — matches or beats {pct}% of {stats['n']} pro references"
        return _scale(value, best, worst), formula, basis
    formula = f"10 at {default_best}{unit} or better, 0 at {worst}{unit}, linear (uncalibrated anchors)"
    return _scale(value, default_best, worst), formula, f"= {value}{unit}"


def compute_technical_score(results, calibration=None):
    """
    DETERMINISTIC TECHNICAL SCORE — RUBRIC v2
    ───────────────────────────────────────────
    A transparent, formula-based 0-10 score over the measured metrics.
    The same audio always yields the same score; no component is generated
    or adjusted by a language model. Every component reports its input
    value, formula, and weight so the number can be audited.

    Calibration: when a professional-reference file exists (built by
    tools/build_calibration.py from analyses of pro vocal takes), the
    "10" anchors come from the pro distribution itself — a singer matching
    the professional pack scores 9-10 because that is measurably where the
    pros sit. Without calibration, documented theoretical anchors apply.

    v2 changes vs v1 (fairness to real-world material):
      * vibrato_control is style-aware: consistent deliberate straight tone
        scores via note-steadiness instead of being penalised for lacking
        vibrato (presence requirement relaxed 70% -> 40% on the vibrato path).
      * dynamics_expression takes the best of phrase-level shaping vs
        effective range: mastered/compressed stems no longer punish the
        singer for the mixing engineer's compressor.
      * phrase_control anchor relaxed (2.5 s median = 10) — short pop
        phrasing is a style, not a breath defect.

    Components (weights renormalised over whichever are measurable):
      intonation_accuracy  25%  median |cents| from tuning-corrected grid
      pitch_stability      15%  median intra-note drift (cents)
      voice_quality        20%  Praat jitter/shimmer/HNR on sustained notes
      vibrato_control      15%  vibrato quality OR straight-tone steadiness
      dynamics_expression  15%  phrase-level shaping / effective range
      phrase_control       10%  median phrase duration (breath management)

    IMPORTANT SCOPE NOTE: this measures technical execution observable in
    the audio. It cannot measure artistry, emotional delivery, lyric
    interpretation, or style-appropriateness — those are inherently human
    judgements and are NOT folded into this number.
    """
    components = {}

    intonation = results.get("intonation", {})
    drift = intonation.get("median_intra_note_drift_cents")
    if intonation.get("median_abs_deviation_cents") is not None:
        value = intonation["median_abs_deviation_cents"]
        score, formula, basis = _linear_component(
            value, "intonation_median_abs_deviation_cents", calibration,
            default_best=5, worst=45, unit=" cents")
        components["intonation_accuracy"] = {
            "weight": 0.25,
            "input": f"median abs grid deviation {basis}",
            "formula": formula,
            "score": score,
        }
        if drift is not None:
            score, formula, basis = _linear_component(
                drift, "intonation_median_intra_note_drift_cents", calibration,
                default_best=10, worst=80, unit=" cents")
            components["pitch_stability"] = {
                "weight": 0.15,
                "input": f"median intra-note drift {basis}",
                "formula": formula,
                "score": score,
            }

    vq = results.get("voice_quality", {})
    if vq.get("method", "").startswith("praat"):
        subscores = []
        detail = []
        jitter = vq.get("jitter_local_percent_median")
        if jitter is not None:
            score, _, basis = _linear_component(
                jitter, "voice_quality_jitter_local_percent_median", calibration,
                default_best=0.3, worst=2.5, unit="%")
            subscores.append(score)
            detail.append(f"jitter {basis}")
        shimmer = vq.get("shimmer_local_percent_median")
        if shimmer is not None:
            score, _, basis = _linear_component(
                shimmer, "voice_quality_shimmer_local_percent_median", calibration,
                default_best=2.5, worst=12.0, unit="%")
            subscores.append(score)
            detail.append(f"shimmer {basis}")
        hnr = vq.get("hnr_db_median")
        if hnr is not None:
            score, _, basis = _linear_component(
                hnr, "voice_quality_hnr_db_median", calibration,
                default_best=20.0, worst=5.0, unit=" dB", lower_is_better=False)
            subscores.append(score)
            detail.append(f"HNR {basis}")
        subscores = [s for s in subscores if s is not None]
        if subscores:
            components["voice_quality"] = {
                "weight": 0.20,
                "input": "; ".join(detail),
                "formula": "mean of jitter/shimmer/HNR sub-scores (Praat, per sustained note)",
                "score": round(float(np.mean(subscores)), 2),
            }

    vib = results.get("vibrato", {})
    if vib.get("n_notes_analysed", 0) >= 3:
        pct = vib.get("pct_notes_with_vibrato", 0)

        # Path A — vibrato-led singing: quality of the vibrato itself
        vib_subscores = [_scale(pct, 40, 0)]
        vib_detail = [f"{pct}% of long notes carry vibrato (10 at >=40%)"]
        if vib.get("median_rate_hz") is not None:
            rate_stats = _calib_metric(calibration, "vibrato_median_rate_hz")
            extent_stats = _calib_metric(calibration, "vibrato_median_extent_cents")
            rate_lo, rate_hi = (rate_stats["p10"], rate_stats["p90"]) if rate_stats else (5.0, 7.0)
            ext_lo, ext_hi = (extent_stats["p10"], extent_stats["p90"]) if extent_stats else (25.0, 130.0)
            vib_subscores.append(_peak_scale(vib["median_rate_hz"], rate_lo, rate_hi, 3.0, 9.0))
            vib_subscores.append(_peak_scale(vib["median_extent_cents"], ext_lo, ext_hi, 5.0, 300.0))
            vib_detail.append(f"rate {vib['median_rate_hz']} Hz (ideal {rate_lo}-{rate_hi})")
            vib_detail.append(f"extent {vib['median_extent_cents']} cents (ideal {ext_lo}-{ext_hi})")
        vibrato_path = float(np.mean([s for s in vib_subscores if s is not None]))

        # Path B — deliberate straight tone: steadiness of held notes.
        # Consistent straight tone is a valid professional style and must
        # not be scored as "missing vibrato".
        candidates = [(vibrato_path, "vibrato-led")]
        if drift is not None:
            candidates.append((_scale(drift, 12, 80), "straight-tone"))
            vib_detail.append(f"intra-note drift {drift} cents (straight-tone path)")
        best_score, style = max(candidates, key=lambda c: c[0])
        components["vibrato_control"] = {
            "weight": 0.15,
            "input": "; ".join(vib_detail),
            "formula": "best of vibrato-quality path and straight-tone steadiness path (consistent straight tone is a valid professional style)",
            "style_detected": style,
            "score": round(best_score, 2),
        }

    dyn = results.get("dynamics", {})
    dyn_candidates = []
    dyn_detail = []
    phrase_spread = dyn.get("phrase_level_spread_db")
    if phrase_spread is not None:
        spread_stats = _calib_metric(calibration, "dynamics_phrase_level_spread_db")
        lo, hi = (spread_stats["p10"], spread_stats["p90"]) if spread_stats else (3.0, 12.0)
        dyn_candidates.append(_peak_scale(phrase_spread, lo, hi, 0.5, 25.0))
        dyn_detail.append(f"phrase-level spread {phrase_spread} dB (ideal {lo}-{hi})")
    eff = dyn.get("effective_dynamic_range_db")
    if eff is not None:
        eff_stats = _calib_metric(calibration, "dynamics_effective_dynamic_range_db")
        lo, hi = (eff_stats["p10"], eff_stats["p90"]) if eff_stats else (6.0, 22.0)
        dyn_candidates.append(_peak_scale(eff, lo, hi, 2.0, 35.0))
        dyn_detail.append(f"effective range {eff} dB (ideal {lo}-{hi})")
    dyn_candidates = [c for c in dyn_candidates if c is not None]
    if dyn_candidates:
        components["dynamics_expression"] = {
            "weight": 0.15,
            "input": "; ".join(dyn_detail),
            "formula": "best of phrase-level shaping and effective range (mastered/compressed stems limit raw range through no fault of the singer)",
            "score": round(float(max(dyn_candidates)), 2),
        }

    phrases = results.get("phrasing", {})
    if phrases.get("median_phrase_s") is not None:
        value = phrases["median_phrase_s"]
        score, formula, basis = _linear_component(
            value, "phrasing_median_phrase_s", calibration,
            default_best=2.5, worst=0.5, unit=" s", lower_is_better=False)
        components["phrase_control"] = {
            "weight": 0.10,
            "input": f"median phrase length {basis}",
            "formula": formula,
            "score": score,
        }

    scored = {k: v for k, v in components.items() if v.get("score") is not None}
    if not scored:
        return {"error": "No components could be scored.", "components": components}

    total_weight = sum(v["weight"] for v in scored.values())
    overall = sum(v["score"] * v["weight"] for v in scored.values()) / total_weight

    # Capture-fair score: the same rubric with voice_quality excluded
    # (weights renormalised). Jitter/shimmer/HNR measure the recording
    # chain as much as the singer when sources differ in era or mastering —
    # a vintage master run through stem separation reads 2-3x worse on
    # these than a clean modern capture of an equal voice. For any
    # singer-vs-singer comparison across different recordings (e.g. a take
    # vs the original record), compare capture-fair scores on BOTH sides.
    fair = {k: v for k, v in scored.items() if k != "voice_quality"}
    capture_fair = (
        sum(v["score"] * v["weight"] for v in fair.values())
        / sum(v["weight"] for v in fair.values())
        if fair else overall
    )

    env = results.get("time_diagnostics", {}).get("environment_risk", {})
    capture_risk = env.get("karaoke_or_room_contamination_risk") == "elevated"
    n_notes = results.get("intonation", {}).get("n_notes", 0)
    praat_used = results.get("voice_quality", {}).get("method", "").startswith("praat")
    confidence = (
        "high" if praat_used and n_notes >= 8 and not capture_risk else
        "medium" if n_notes >= 4 else
        "low"
    )

    calibrated = calibration is not None
    provenance = (
        "deterministic_rubric_v2 — computed from measured audio features; "
        "identical audio yields an identical score; no LLM involvement; "
        + ("anchored to professional reference distribution" if calibrated else
           "theoretical anchors (no pro calibration file found)")
    )

    return {
        "overall_score_0_to_10": round(float(overall), 1),
        "capture_fair_score_0_to_10": round(float(capture_fair), 1),
        "capture_fair_note": (
            "Rubric with voice_quality excluded (weights renormalised). "
            "Jitter/shimmer/HNR partly measure the recording chain: vintage "
            "masters run through stem separation read far worse than clean "
            "modern captures of an equal voice. Use capture_fair on BOTH "
            "sides for any take-vs-original or cross-era comparison; use "
            "overall_score for a singer's absolute result and self-progress."
        ),
        "provenance": provenance,
        "calibration": {
            "active": calibrated,
            "file": calibration.get("_path") if calibrated else None,
            "n_references": calibration.get("n_references") if calibrated else 0,
            "note": None if calibrated else (
                "Run tools/build_calibration.py over analyses of 15-20 professional "
                "reference takes to anchor 9-10 to the professional distribution."
            ),
        },
        "confidence": confidence,
        "confidence_basis": {
            "praat_metrics_available": praat_used,
            "n_sustained_notes": n_notes,
            "capture_risk_elevated": capture_risk,
        },
        "components": components,
        "weights_note": "Weights renormalised over measurable components.",
        "scope_note": (
            "Technical execution only. Artistry, emotion, interpretation and "
            "style-appropriateness are human judgements and are not part of "
            "this number. Any 'listener impact' figure elsewhere in a report "
            "is a subjective estimate, not a measurement."
        ),
    }


def analyse_phrasing(f0, sr, hop_length=512):
    """Breath/phrase-length statistics from voiced-run grouping."""
    phrases = segment_phrases(f0, hop_length, sr)
    if not phrases:
        return {"error": "No phrases detected."}
    durations = [p["duration_s"] for p in phrases]
    return {
        "n_phrases": len(phrases),
        "median_phrase_s": round(float(np.median(durations)), 2),
        "max_phrase_s": round(float(np.max(durations)), 2),
        "method": f"voiced runs merged across gaps < {PHRASE_GAP_BRIDGE_S}s",
    }


def generate_visual_diagnostics(y, sr, f0, output_path, title, hop_length=512):
    """Generates a Manus-style diagnostic plot for quick visual review."""
    print("  Generating visual diagnostic plot...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pitch_times = librosa.times_like(f0, sr=sr, hop_length=hop_length)
    voiced_f0 = f0[~np.isnan(f0)] if f0 is not None else np.array([])
    mean_f0 = float(np.mean(voiced_f0)) if len(voiced_f0) else None

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    rms_times = librosa.times_like(rms, sr=sr, hop_length=hop_length)

    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    centroid_times = librosa.times_like(spectral_centroid, sr=sr, hop_length=hop_length)

    fig, axes = plt.subplots(4, 1, figsize=(16, 13))
    fig.suptitle(title, fontsize=13, fontweight='bold')

    librosa.display.waveshow(y, sr=sr, ax=axes[0], color='steelblue', alpha=0.8)
    axes[0].set_title('Waveform (Amplitude over Time)', fontsize=11)
    axes[0].set_xlabel('Time (s)')
    axes[0].set_ylabel('Amplitude')

    axes[1].plot(pitch_times, f0, color='darkorange', linewidth=0.9, label='F0 (Hz)', alpha=0.85)
    axes[1].set_title('Pitch Contour (F0) — Vocal Melody Tracking', fontsize=11)
    axes[1].set_xlabel('Time (s)')
    axes[1].set_ylabel('Frequency (Hz)')
    axes[1].set_ylim([60, 900])
    if mean_f0:
        axes[1].axhline(y=mean_f0, color='red', linestyle='--', linewidth=0.8, label=f'Mean F0 ({mean_f0:.0f}Hz)')
    axes[1].legend(fontsize=9)

    axes[2].fill_between(rms_times, rms_db, alpha=0.6, color='crimson')
    axes[2].plot(rms_times, rms_db, color='crimson', linewidth=0.6)
    axes[2].set_title('RMS Energy (dB) — Volume / Intensity over Time', fontsize=11)
    axes[2].set_xlabel('Time (s)')
    axes[2].set_ylabel('dB')
    axes[2].axhline(y=np.mean(rms_db), color='black', linestyle='--', linewidth=0.8, label=f'Mean ({np.mean(rms_db):.1f}dB)')
    axes[2].legend(fontsize=9)

    axes[3].plot(centroid_times, spectral_centroid, color='mediumseagreen', linewidth=0.8, alpha=0.85)
    axes[3].set_title('Spectral Centroid (Hz) — Vocal Brightness / Presence', fontsize=11)
    axes[3].set_xlabel('Time (s)')
    axes[3].set_ylabel('Hz')
    axes[3].axhline(y=np.mean(spectral_centroid), color='black', linestyle='--', linewidth=0.8, label=f'Mean ({np.mean(spectral_centroid):.0f}Hz)')
    axes[3].legend(fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Visual diagnostics saved to: {output_path}")


# =============================================================================
# DIAGNOSTIC LOGIC ENGINE
# =============================================================================

def generate_diagnostic_flags(results):
    """
    Applies the Source-Filter Diagnostic Matrix to the raw measurements.
    Translates acoustic data into physiological inferences and flags.

    This is the core of the feedback logic. Each flag maps to a specific
    intervention recommendation.
    """
    flags = []
    archetype_scores = {
        "Volume Chaser": 0,
        "Pusher": 0,
        "Floater": 0,
        "Pitch Slider": 0,
        "Nasal Tone": 0
    }

    # ─── DYNAMICS FLAGS ───────────────────────────────────────────────────
    dyn = results.get("dynamics", {})
    eff_range = dyn.get("effective_dynamic_range_db", 20)
    if eff_range < 12:
        flags.append({
            "category": "Dynamics",
            "flag": "Narrow effective dynamic range",
            "value": f"{eff_range} dB",
            "interpretation": "Consistently loud delivery. Limited light and shade.",
            "likely_cause": "Clavicular breathing / chronic over-pressurisation.",
            "intervention": "Messa di Voce"
        })
        archetype_scores["Volume Chaser"] += 2

    # ─── INTONATION FLAGS ─────────────────────────────────────────────────
    intonation = results.get("intonation", {})
    med_dev = intonation.get("median_abs_deviation_cents")
    if med_dev is not None and med_dev > 20:
        flags.append({
            "category": "Pitch",
            "flag": "Sustained notes landing off the pitch grid",
            "value": f"median {med_dev} cents from nearest semitone (tuning-corrected)",
            "interpretation": "Notes are consistently settling off-centre.",
            "likely_cause": "Ear-to-onset calibration, or breath pressure bending sustained pitch.",
            "intervention": "Slow sirens onto held target notes with drone reference"
        })
        archetype_scores["Pitch Slider"] += 2

    drift = intonation.get("median_intra_note_drift_cents")
    if drift is not None and drift > 40:
        flags.append({
            "category": "Pitch",
            "flag": "High intra-note pitch drift",
            "value": f"median {drift} cents drift within sustained notes",
            "interpretation": "Held notes wander rather than sitting still.",
            "likely_cause": "Breath pressure decay or TA-dominant registration pulling pitch.",
            "intervention": "Fry to Head / Lip Trill / Messa di Voce on single pitches"
        })
        archetype_scores["Pitch Slider"] += 1

    # ─── VOICE QUALITY FLAGS ──────────────────────────────────────────────
    vq = results.get("voice_quality", {})
    jitter = vq.get("jitter_local_percent_median")
    hnr = vq.get("hnr_db_median")
    if jitter is not None and jitter > 1.5:
        if hnr is not None and hnr < 8:
            flags.append({
                "category": "Vocal Fold Behaviour",
                "flag": "Elevated jitter + low HNR on sustained notes",
                "value": f"Jitter: {jitter}% | HNR: {hnr} dB (Praat, per-note median)",
                "interpretation": "Compression-led distortion (controlled grit) or breathiness.",
                "likely_cause": "Intentional supraglottic compression. Confirm against context.",
                "intervention": "Bratty Nay (if resonance is dark) / Lip Trill (if breath is leaky)"
            })
            archetype_scores["Pusher"] += 1
        else:
            flags.append({
                "category": "Vocal Fold Behaviour",
                "flag": "Elevated jitter on sustained notes",
                "value": f"Jitter: {jitter}% (Praat, per-note median)",
                "interpretation": "Some fold irregularity. May indicate fatigue or onset instability.",
                "likely_cause": "Inconsistent breath onset or sub-optimal fold closure.",
                "intervention": "Mum 1-5-3-1 (forward mix onset)"
            })

    # ─── RESONANCE FLAGS ──────────────────────────────────────────────────
    res = results.get("resonance", {})
    centroid = res.get("spectral_centroid_mean_hz", 1800)
    if centroid < CENTROID_DARK_THRESHOLD:
        flags.append({
            "category": "Resonance",
            "flag": "Low spectral centroid — dark/swallowed resonance",
            "value": f"{centroid} Hz (active frames only)",
            "interpretation": "Tone is dark and lacks projection.",
            "likely_cause": "Depressed larynx or retracted tongue root.",
            "intervention": "Bratty Nay / NG Siren"
        })
        archetype_scores["Nasal Tone"] -= 1  # Opposite of nasal
    elif centroid > CENTROID_BRIGHT_THRESHOLD:
        flags.append({
            "category": "Resonance",
            "flag": "High spectral centroid — bright/forward resonance",
            "value": f"{centroid} Hz (active frames only)",
            "interpretation": "Strong forward placement. Good projection and cut.",
            "likely_cause": "Aryepiglottic twang / raised larynx / wide oral cavity.",
            "intervention": "Maintain — no correction needed. Monitor for laryngeal elevation."
        })

    # ─── ARCHETYPE DETERMINATION ──────────────────────────────────────────
    dominant_archetype = max(archetype_scores, key=archetype_scores.get)
    if archetype_scores[dominant_archetype] == 0:
        dominant_archetype = "Hybrid"

    return flags, dominant_archetype


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_markdown_report(results, flags, archetype, artist_name, file_name, output_path):
    """
    Converts the structured JSON results and diagnostic flags into a
    human-readable Markdown report following the VOXAI format.
    """
    now = datetime.now().strftime("%d %B %Y")
    pitch = results.get("pitch", {})
    vq = results.get("voice_quality", {})
    harm = results.get("harmonic_balance", {})
    res = results.get("resonance", {})
    dyn = results.get("dynamics", {})
    rhythm = results.get("rhythm", {})
    formants = results.get("formants", {})
    vibrato = results.get("vibrato", {})
    intonation = results.get("intonation", {})
    score = results.get("technical_score", {})
    stem_info = results.get("stem_separation")
    visual_info = results.get("visual_diagnostics")

    lines = [
        f"# VOXAI Diagnostic Report",
        f"",
        f"| Field | Detail |",
        f"|---|---|",
        f"| **Subject** | {artist_name} |",
        f"| **File** | `{file_name}` |",
        f"| **Duration** | {results.get('duration_seconds', 'N/A')}s |",
        f"| **Archetype** | {archetype} |",
        f"| **Analysis Date** | {now} |",
    ]

    if stem_info:
        lines += [
            f"",
            f"---",
            f"",
            f"## STEM PREPROCESSING",
            f"",
            f"| Field | Value |",
            f"|---|---|",
            f"| Vocals stem analysed | `{stem_info.get('vocals_path', 'N/A')}` |",
            f"| Instrumental stem | `{stem_info.get('instrumental_path', 'N/A')}` |",
            f"| Stem output folder | `{stem_info.get('output_dir', 'N/A')}` |",
        ]

    if visual_info:
        lines += [
            f"",
            f"---",
            f"",
            f"## VISUAL DIAGNOSTICS",
            f"",
            f"| Field | Value |",
            f"|---|---|",
            f"| Diagnostic plot | `{visual_info.get('plot_path', 'N/A')}` |",
            f"| Panels | {', '.join(visual_info.get('panels', []))} |",
            f"| Caution | {visual_info.get('note', 'Supporting diagnostics only.')} |",
        ]

    # ── Technical score ──────────────────────────────────────────────────
    if score and not score.get("error"):
        calib = score.get("calibration", {})
        calib_line = (
            f"Calibrated against {calib.get('n_references')} professional references."
            if calib.get("active")
            else "Uncalibrated (theoretical anchors) — build a pro-reference calibration with tools/build_calibration.py."
        )
        lines += [
            f"",
            f"---",
            f"",
            f"## TECHNICAL SCORE (DETERMINISTIC)",
            f"",
            f"> **{score.get('overall_score_0_to_10', 'N/A')} / 10** — confidence: {score.get('confidence', 'N/A')}",
            f">",
            f"> Capture-fair score: **{score.get('capture_fair_score_0_to_10', 'N/A')} / 10** — use this (on both sides) when comparing against an original recording from a different era/recording chain.",
            f">",
            f"> {calib_line}",
            f">",
            f"> {score.get('scope_note', '')}",
            f"",
            f"| Component | Score | Weight | Basis |",
            f"|---|---|---|---|",
        ]
        for name, comp in score.get("components", {}).items():
            lines.append(
                f"| {name.replace('_', ' ').title()} | {comp.get('score', 'N/A')} | {comp.get('weight')} | {comp.get('input', '')} |"
            )
        lines.append("")
        lines.append(f"*Provenance: {score.get('provenance', '')}*")

    lines += [
        f"",
        f"---",
        f"",
        f"## PRIMARY LIMITER",
        f"",
    ]

    # Derive primary limiter from top flag
    if flags:
        top_flag = flags[0]
        lines.append(f"> **{top_flag['flag']}** — {top_flag['interpretation']}")
        lines.append(f"> *Likely cause:* {top_flag['likely_cause']}")
        lines.append(f"> *Recommended intervention:* **{top_flag['intervention']}**")
    else:
        lines.append("> No dominant limiter identified. Voice appears well-coordinated.")

    lines += [
        f"",
        f"---",
        f"",
        f"## PITCH ANALYSIS",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Mean Pitch | {pitch.get('mean_hz', 'N/A')} Hz ({pitch.get('mean_note', 'N/A')}) |",
        f"| Median Pitch | {pitch.get('median_hz', 'N/A')} Hz ({pitch.get('median_note', 'N/A')}) |",
        f"| Robust Pitch Range | {pitch.get('robust_min_note', 'N/A')} – {pitch.get('robust_max_note', 'N/A')} ({pitch.get('range_semitones', 'N/A')} semitones, 2.5th–97.5th pct) |",
        f"| Extreme Frames | {pitch.get('min_note', 'N/A')} – {pitch.get('max_note', 'N/A')} ({pitch.get('full_range_semitones', 'N/A')} semitones, may include tracker errors) |",
        f"| Voiced Frames | {pitch.get('voiced_percentage', 'N/A')}% |",
        f"",
        f"---",
        f"",
        f"## INTONATION (sustained notes vs pitch grid)",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Sustained notes analysed | {intonation.get('n_notes', 'N/A')} |",
        f"| Tuning offset (removed) | {intonation.get('tuning_offset_cents', 'N/A')} cents |",
        f"| Median abs deviation | {intonation.get('median_abs_deviation_cents', 'N/A')} cents |",
        f"| Notes within ±10 cents | {intonation.get('pct_notes_within_10_cents', 'N/A')}% |",
        f"| Notes within ±25 cents | {intonation.get('pct_notes_within_25_cents', 'N/A')}% |",
        f"| Intra-note drift (median) | {intonation.get('median_intra_note_drift_cents', 'N/A')} cents |",
        f"| Classification | **{intonation.get('classification', 'N/A')}** |",
        f"",
        f"*{intonation.get('caveat', '')}*",
        f"",
        f"---",
        f"",
        f"## VOICE QUALITY (Praat, per sustained note)",
        f"",
        f"| Metric | Value | Method |",
        f"|---|---|---|",
        f"| Jitter (local, median) | {vq.get('jitter_local_percent_median', 'N/A')}% | {vq.get('method', 'N/A')} |",
        f"| Shimmer (local, median) | {vq.get('shimmer_local_percent_median', 'N/A')}% | reliability: {vq.get('reliability', 'N/A')} |",
        f"| HNR (median) | {vq.get('hnr_db_median', 'N/A')} dB | {vq.get('n_notes_measured', 'N/A')} notes measured |",
        f"| Interpretation | {vq.get('interpretation', 'N/A')} | — |",
        f"",
        f"*Speech-pathology thresholds (jitter {JITTER_THRESHOLD_PCT}%, shimmer {SHIMMER_THRESHOLD_PCT}%) describe sustained spoken vowels; sung notes with vibrato naturally run higher.*",
        f"",
        f"---",
        f"",
        f"## VIBRATO (per sustained note ≥ {VIBRATO_NOTE_MIN_S}s)",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Long notes analysed | {vibrato.get('n_notes_analysed', 'N/A')} |",
        f"| Notes with vibrato | {vibrato.get('n_notes_with_vibrato', 'N/A')} ({vibrato.get('pct_notes_with_vibrato', 'N/A')}%) |",
        f"| Median rate | {vibrato.get('median_rate_hz', 'N/A')} Hz |",
        f"| Median extent | {vibrato.get('median_extent_cents', 'N/A')} cents |",
        f"| Classification | **{vibrato.get('classification', 'N/A')}** |",
        f"",
        f"---",
        f"",
        f"## RESONANCE (active frames only)",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Spectral Centroid (Mean) | {res.get('spectral_centroid_mean_hz', 'N/A')} Hz |",
        f"| Spectral Rolloff (85%) | {res.get('spectral_rolloff_85_mean_hz', 'N/A')} Hz |",
        f"| Spectral Flatness | {res.get('spectral_flatness_mean', 'N/A')} (0=tonal, 1=noise) |",
        f"| Active frames | {res.get('active_frame_percentage', 'N/A')}% |",
        f"| Classification | **{res.get('resonance_classification', 'N/A')}** |",
        f"",
        f"---",
        f"",
        f"## FORMANTS",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| F1 (median) | {formants.get('F1_median_hz', 'N/A')} Hz |",
        f"| F2 (median) | {formants.get('F2_median_hz', 'N/A')} Hz |",
        f"| F3 (median) | {formants.get('F3_median_hz', 'N/A')} Hz |",
        f"| Method | {formants.get('method', 'N/A')} (reliability: {formants.get('reliability', 'N/A')}) |",
        f"",
        f"---",
        f"",
        f"## DYNAMICS",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Mean RMS Energy | {dyn.get('mean_rms_db', 'N/A')} dB (relative to file peak) |",
        f"| Effective Dynamic Range (P10–P90) | {dyn.get('effective_dynamic_range_db', 'N/A')} dB |",
        f"| Phrase-level spread | {dyn.get('phrase_level_spread_db', 'N/A')} dB |",
        f"| Full Dynamic Range | {dyn.get('full_dynamic_range_db', 'N/A')} dB |",
        f"",
        f"---",
        f"",
        f"## RHYTHM",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Estimated Tempo | {rhythm.get('estimated_tempo_bpm', 'N/A')} BPM (confidence: {rhythm.get('tempo_confidence', 'N/A')}) |",
        f"| Onset Rate | {rhythm.get('onsets_per_second', 'N/A')} onsets/sec |",
        f"| Rhythmic Regularity | {rhythm.get('rhythmic_regularity', 'N/A')} (0=irregular, 1=metronomic) |",
        f"",
        f"---",
        f"",
        f"## HARMONIC BALANCE (whole-file texture — not clinical HNR)",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Harmonic/residual ratio | {harm.get('harmonic_residual_db', 'N/A')} dB |",
        f"| Note | {harm.get('note', '')} |",
        f"",
        f"---",
        f"",
        f"## DIAGNOSTIC FLAGS",
        f"",
    ]

    if flags:
        for i, flag in enumerate(flags, 1):
            lines += [
                f"### Flag {i}: {flag['flag']}",
                f"",
                f"**Category:** {flag['category']}  ",
                f"**Value:** {flag['value']}  ",
                f"**Interpretation:** {flag['interpretation']}  ",
                f"**Likely Cause:** {flag['likely_cause']}  ",
                f"**Recommended Intervention:** **{flag['intervention']}**",
                f"",
            ]
    else:
        lines.append("No significant flags raised.")

    lines += [
        f"---",
        f"",
        f"*VOXAI Diagnostic Engine — Transformation over validation.*",
        f"*All scores in this report are deterministic measurements or documented formulas — never model-generated estimates.*",
    ]

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"  Report saved to: {output_path}")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="VOXAI Local Vocal Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: python analyse_song.py input/my_song.wav --name 'Aaron Rustwood'"
    )
    parser.add_argument("input_file", help="Path to the audio/video file to analyse.")
    parser.add_argument("--name", default="Unknown Artist", help="Name of the performer.")
    parser.add_argument("--no-convert", action="store_true", help="Skip ffmpeg conversion (use if already a clean WAV).")
    parser.add_argument(
        "--separate-stems",
        action="store_true",
        help="Run stem separation first and analyse the isolated vocals stem.",
    )
    parser.add_argument(
        "--stems-script",
        default="tools/stems/batch_stems.sh",
        help="Path to stem separation helper script (relative to repo or absolute).",
    )
    parser.add_argument(
        "--formant-ceiling",
        type=float,
        default=5500.0,
        help="Praat formant ceiling in Hz (5000 typical for adult male, 5500 for female).",
    )
    parser.add_argument(
        "--calibration",
        default=DEFAULT_CALIBRATION_PATH,
        help="Path to pro-reference calibration JSON (built by tools/build_calibration.py). "
             "Pass 'none' to force theoretical anchors.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: File not found: {args.input_file}")
        sys.exit(1)

    os.makedirs("output", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    os.makedirs("temp", exist_ok=True)

    base_name = os.path.splitext(os.path.basename(args.input_file))[0]
    json_output = os.path.join("output", f"{base_name}_analysis.json")
    report_output = os.path.join("reports", f"{base_name}_report.md")
    visual_output = os.path.join("reports", "diagnostics", f"{base_name}_diagnostic_plot.png")

    print(f"\n{'='*60}")
    print(f"  VOXAI Analysis: {args.name} — {os.path.basename(args.input_file)}")
    print(f"{'='*60}\n")

    if not PARSELMOUTH_AVAILABLE:
        print("  WARNING: praat-parselmouth is not installed.")
        print("  Voice quality (jitter/shimmer/HNR) and formants will run in")
        print("  reduced-reliability fallback mode. Install with:")
        print("      pip install praat-parselmouth\n")

    analysis_input_path = args.input_file
    stem_metadata = None

    # Stage 0: Optional stem separation
    if args.separate_stems:
        try:
            stem_metadata = run_stem_separation(args.input_file, script_path=args.stems_script)
            analysis_input_path = stem_metadata["vocals_path"]
        except Exception as stem_error:
            print(f"  Stem separation error: {stem_error}")
            sys.exit(1)

    # Stage 1: Convert audio
    if args.no_convert:
        wav_path = analysis_input_path
    else:
        wav_path = convert_to_wav(analysis_input_path)

    # Stage 2: Load audio
    print("Loading audio...")
    y, sr = load_audio(wav_path)
    duration = librosa.get_duration(y=y, sr=sr)
    print(f"  Duration: {duration:.2f}s | Sample rate: {sr} Hz\n")

    results = {
        "file_name": os.path.basename(args.input_file),
        "analysis_input_file": os.path.basename(analysis_input_path),
        "artist_name": args.name,
        "duration_seconds": round(duration, 2),
        "sample_rate": sr,
        "engine": {
            "parselmouth_available": PARSELMOUTH_AVAILABLE,
            "measurement_policy": "voice-quality metrics restricted to sustained voiced notes; deterministic scoring rubric v1",
        },
    }

    if stem_metadata:
        results["stem_separation"] = stem_metadata

    # Stage 3: Run all analysis modules
    print("Running analysis pipeline...")
    pitch_results = analyse_pitch(y, sr)
    raw_f0 = pitch_results.pop("raw_f0", None)  # Extract raw F0 for segment analysis
    results["pitch"] = pitch_results

    if raw_f0 is not None:
        results["voice_quality"] = analyse_voice_quality(wav_path, raw_f0, sr)

    results["harmonic_balance"] = analyse_harmonic_balance(y)
    results["resonance"] = analyse_resonance(y, sr)
    results["dynamics"] = analyse_dynamics(y, sr, f0=raw_f0)
    results["rhythm"] = analyse_rhythm(y, sr, is_isolated_stem=bool(stem_metadata))

    if raw_f0 is not None:
        results["formants"] = analyse_formants(
            wav_path, y, sr, raw_f0, formant_ceiling=args.formant_ceiling
        )
        results["vibrato"] = analyse_vibrato(raw_f0, sr)
        results["intonation"] = analyse_intonation(raw_f0, sr)
        results["phrasing"] = analyse_phrasing(raw_f0, sr)
        results["time_diagnostics"] = analyse_time_diagnostics(
            y,
            sr,
            raw_f0,
            results["pitch"],
            results["dynamics"],
            results["resonance"],
        )
        generate_visual_diagnostics(
            y,
            sr,
            raw_f0,
            visual_output,
            f"VOXAI Audio Analysis — {base_name}\n{args.name}",
        )
        results["visual_diagnostics"] = {
            "plot_path": os.path.abspath(visual_output),
            "panels": [
                "waveform_amplitude",
                "pitch_contour_f0",
                "rms_energy_db",
                "spectral_centroid_brightness",
            ],
            "note": "Supporting visual diagnostics. In karaoke/live-room recordings, backing track bleed and mic clipping can affect these traces.",
        }

    # Stage 4: Deterministic technical score
    print("\nComputing deterministic technical score...")
    calibration = None if args.calibration.lower() == "none" else load_calibration(args.calibration)
    if calibration:
        print(f"  Calibration: {calibration['_path']} ({calibration.get('n_references')} pro references)")
    else:
        print("  Calibration: none — using theoretical anchors. "
              "Build one with tools/build_calibration.py for pro-anchored scoring.")
    results["technical_score"] = compute_technical_score(results, calibration=calibration)
    if "overall_score_0_to_10" in results["technical_score"]:
        print(f"  Technical score: {results['technical_score']['overall_score_0_to_10']}/10 "
              f"(confidence: {results['technical_score']['confidence']})")

    # Stage 5: Diagnostic logic
    print("\nRunning diagnostic logic engine...")
    flags, archetype = generate_diagnostic_flags(results)
    results["archetype"] = archetype
    results["diagnostic_flags"] = flags
    print(f"  Archetype: {archetype}")
    print(f"  Flags raised: {len(flags)}")

    # Stage 6: Save JSON
    with open(json_output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Raw data saved: {json_output}")

    # Stage 7: Generate Markdown report
    print("\nGenerating diagnostic report...")
    generate_markdown_report(results, flags, archetype, args.name, os.path.basename(args.input_file), report_output)

    print(f"\n{'='*60}")
    print(f"  Analysis complete!")
    print(f"  JSON data:  {json_output}")
    print(f"  Report:     {report_output}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
