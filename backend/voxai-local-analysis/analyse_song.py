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
    (Optional) openai — for AI-generated natural language feedback

Author:     VOXAI Diagnostic Engine
=============================================================================
"""

import os
import sys
import json
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

warnings.filterwarnings('ignore')


# =============================================================================
# CONFIGURATION
# =============================================================================

# Minimum confidence threshold for voiced pitch frames
VOICED_CONFIDENCE_THRESHOLD = 0.5

# Minimum RMS level (dB) to be considered an active (non-silent) frame
SILENCE_THRESHOLD_DB = -60.0

# Jitter/Shimmer clinical reference thresholds (speech pathology standards)
JITTER_THRESHOLD_PCT = 1.04
SHIMMER_THRESHOLD_PCT = 3.81
HNR_CLEAN_THRESHOLD_DB = 20.0

# Spectral centroid ranges for resonance classification
CENTROID_DARK_THRESHOLD = 1200.0    # Hz — below this = dark/swallowed
CENTROID_BRIGHT_THRESHOLD = 2500.0  # Hz — above this = very bright/twangy


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

    if input_path.lower().endswith('.wav'):
        # Still re-encode to ensure mono + 44100 Hz
        pass

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


def find_first_stem_match(patterns):
    """Returns the first matching file path from a list of glob patterns."""
    for pattern in patterns:
        matches = sorted(glob.glob(pattern, recursive=True))
        if matches:
            return matches[0]
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

    vocals_path = find_first_stem_match([
        os.path.join(run_output_dir, "**", "*_(Vocals)_*.flac"),
        os.path.join(run_output_dir, "**", "*_(Vocals)_*.wav"),
        os.path.join(run_output_dir, "**", "*.vocals.wav"),
        os.path.join(run_output_dir, "**", "*vocals*.wav"),
    ])
    instrumental_path = find_first_stem_match([
        os.path.join(run_output_dir, "**", "*_(Instrumental)_*.flac"),
        os.path.join(run_output_dir, "**", "*_(Instrumental)_*.wav"),
        os.path.join(run_output_dir, "**", "*.instrumental.wav"),
        os.path.join(run_output_dir, "**", "*no_vocals*.wav"),
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

    Returns a dict of pitch statistics.
    """
    print("  [1/8] Pitch analysis (pyin)...")

    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=librosa.note_to_hz('C2'),   # ~65 Hz — lower limit for bass/baritenor
        fmax=librosa.note_to_hz('C6'),   # ~1047 Hz — upper limit for tenor
        sr=sr,
        frame_length=2048,
        hop_length=hop_length
    )

    voiced_f0 = f0[~np.isnan(f0)]
    n_total = len(f0)
    n_voiced = len(voiced_f0)

    if n_voiced < 10:
        return {"error": "Insufficient voiced frames detected. Check audio quality."}

    # Calculate pitch range in semitones
    pitch_range_semitones = round(
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
        "range_semitones": pitch_range_semitones,
        "voiced_percentage": round(n_voiced / n_total * 100, 1),
        "p25_hz": round(float(np.percentile(voiced_f0, 25)), 2),
        "p75_hz": round(float(np.percentile(voiced_f0, 75)), 2),
        "p95_hz": round(float(np.percentile(voiced_f0, 95)), 2),
        "sections": sections,
        "raw_f0": f0  # Keep for perturbation analysis
    }


def analyse_perturbation(f0):
    """
    MODULE 2: PERTURBATION ANALYSIS (Jitter & Shimmer)
    ────────────────────────────────────────────────────
    Jitter measures cycle-to-cycle frequency instability.
    Shimmer measures cycle-to-cycle amplitude instability.
    Both are elevated in breathy, strained, or intentionally distorted voices.

    Clinical thresholds (speech pathology):
        Jitter Local > 1.04% = abnormal
        Shimmer Local > 3.81% = abnormal
    In singing, especially with controlled grit, these thresholds will be exceeded
    intentionally — context is critical for interpretation.
    """
    print("  [2/8] Perturbation analysis (jitter)...")

    voiced_f0 = f0[~np.isnan(f0)]
    if len(voiced_f0) < 3:
        return {"error": "Insufficient data for perturbation analysis."}

    periods = 1.0 / voiced_f0
    period_diffs = np.abs(np.diff(periods))
    mean_period = float(np.mean(periods))

    # Local Jitter: mean absolute difference between consecutive periods
    jitter_local = float(np.mean(period_diffs) / mean_period) * 100

    # RAP (Relative Average Perturbation): 3-point smoothed jitter
    rap_diffs = []
    for i in range(1, len(periods) - 1):
        avg3 = (periods[i-1] + periods[i] + periods[i+1]) / 3
        rap_diffs.append(abs(periods[i] - avg3))
    jitter_rap = float(np.mean(rap_diffs) / mean_period) * 100 if rap_diffs else None

    # PPQ5 (Period Perturbation Quotient, 5-point smoothed)
    ppq_diffs = []
    for i in range(2, len(periods) - 2):
        avg5 = np.mean(periods[i-2:i+3])
        ppq_diffs.append(abs(periods[i] - avg5))
    jitter_ppq5 = float(np.mean(ppq_diffs) / mean_period) * 100 if ppq_diffs else None

    return {
        "jitter_local_percent": round(jitter_local, 4),
        "jitter_rap_percent": round(jitter_rap, 4) if jitter_rap else None,
        "jitter_ppq5_percent": round(jitter_ppq5, 4) if jitter_ppq5 else None,
        "threshold_local_pct": JITTER_THRESHOLD_PCT,
        "exceeds_threshold": jitter_local > JITTER_THRESHOLD_PCT
    }


def analyse_hnr(y):
    """
    MODULE 3: HARMONIC-TO-NOISE RATIO
    ───────────────────────────────────
    Separates the audio into harmonic (tonal) and percussive (noise-like)
    components using the HPSS algorithm, then computes the energy ratio.

    HNR > 20 dB = clean, well-supported phonation
    HNR 10-20 dB = mild breathiness or distortion
    HNR < 10 dB = heavy distortion, breathiness, or controlled grit
    """
    print("  [3/8] Harmonic-to-Noise Ratio analysis...")

    y_harmonic, y_percussive = librosa.effects.hpss(y)
    harmonic_power = float(np.mean(y_harmonic ** 2))
    noise = y - y_harmonic
    noise_power = float(np.mean(noise ** 2))

    hnr_db = 10 * np.log10(harmonic_power / noise_power) if noise_power > 0 else 99.0
    hpr_ratio = harmonic_power / float(np.mean(y_percussive ** 2)) if np.mean(y_percussive ** 2) > 0 else 99.0

    return {
        "hnr_db": round(float(hnr_db), 2),
        "hpr_db": round(10 * np.log10(hpr_ratio), 2) if hpr_ratio > 0 else 0,
        "classification": (
            "Clean / Well-supported" if hnr_db > HNR_CLEAN_THRESHOLD_DB else
            "Mild distortion / Breathiness" if hnr_db > 10 else
            "Heavy distortion / Controlled grit"
        )
    }


def analyse_resonance(y, sr, hop_length=512):
    """
    MODULE 4: RESONANCE ANALYSIS
    ──────────────────────────────
    Spectral Centroid: The 'centre of mass' of the spectrum. High values
    indicate bright, forward resonance. Low values indicate dark, swallowed tone.

    Spectral Rolloff: The frequency below which X% of the spectral energy lies.
    High rolloff = lots of high-frequency harmonic content.

    Spectral Flatness: 0 = perfectly tonal (sine wave); 1 = white noise.
    Very low values confirm the voice is tonal even under distortion.
    """
    print("  [4/8] Resonance analysis...")

    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    rolloff_85 = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length, roll_percent=0.85)[0]
    rolloff_95 = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length, roll_percent=0.95)[0]
    flatness = librosa.feature.spectral_flatness(y=y, hop_length=hop_length)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length)[0]
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=hop_length)

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
        "resonance_classification": resonance_class
    }


def analyse_dynamics(y, sr, hop_length=512):
    """
    MODULE 5: DYNAMICS ANALYSIS
    ─────────────────────────────
    RMS Energy measures the loudness of the signal over time.
    Dynamic Range is the difference between the loudest and quietest active frames.
    Effective Dynamic Range (P10-P90) removes outliers for a more realistic measure.

    A narrow effective dynamic range (< 12 dB) indicates a consistently loud,
    compressed delivery with little light and shade.
    """
    print("  [5/8] Dynamics analysis...")

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    active = rms_db[rms_db > SILENCE_THRESHOLD_DB]

    if len(active) == 0:
        return {"error": "No active audio frames detected."}

    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]

    return {
        "mean_rms_db": round(float(np.mean(active)), 2),
        "median_rms_db": round(float(np.median(active)), 2),
        "full_dynamic_range_db": round(float(np.max(active) - np.min(active)), 2),
        "effective_dynamic_range_db": round(float(np.percentile(active, 90) - np.percentile(active, 10)), 2),
        "p10_db": round(float(np.percentile(active, 10)), 2),
        "p90_db": round(float(np.percentile(active, 90)), 2),
        "zcr_mean": round(float(np.mean(zcr)), 6)
    }


def analyse_rhythm(y, sr, hop_length=512):
    """
    MODULE 6: RHYTHM AND ONSET ANALYSIS
    ─────────────────────────────────────
    Onset detection identifies the start of each note/syllable.
    Onset rate (onsets/second) indicates how densely packed the delivery is.
    Rhythmic regularity measures how consistent the spacing between onsets is.
    A value of 1.0 = perfectly metronomic; 0.0 = completely irregular.
    """
    print("  [6/8] Rhythm and onset analysis...")

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
        "total_onsets": len(onsets),
        "onsets_per_second": round(len(onsets) / duration, 2),
        **ioi_stats
    }


def analyse_formants(y, sr, hop_length=512):
    """
    MODULE 7: FORMANT ESTIMATION (LPC)
    ────────────────────────────────────
    Formants are the resonant frequencies of the vocal tract.
    F1 correlates with jaw height (low F1 = closed jaw, high F1 = open jaw).
    F2 correlates with tongue position (low F2 = back vowel, high F2 = front vowel).

    This uses Linear Predictive Coding (LPC) — an approximation.
    For clinical-grade formant analysis, Praat software is recommended.
    """
    print("  [7/8] Formant estimation (LPC)...")

    def get_formants(chunk, sr, order=12):
        pre_emphasis = 0.97
        chunk_pe = np.append(chunk[0], chunk[1:] - pre_emphasis * chunk[:-1])
        try:
            a = librosa.lpc(chunk_pe, order=order)
            roots = np.roots(a)
            roots = roots[np.imag(roots) >= 0]
            angles = np.arctan2(np.imag(roots), np.real(roots))
            freqs = sorted(angles * (sr / (2 * np.pi)))
            freqs = [f for f in freqs if 90 < f < sr / 2]
            return freqs[:4] if len(freqs) >= 4 else None
        except Exception:
            return None

    chunk_size = int(0.03 * sr)  # 30ms windows
    mid_start = int(len(y) * 0.25)
    mid_end = int(len(y) * 0.75)
    samples = []

    for start in range(mid_start, mid_end, chunk_size * 8):
        chunk = y[start:start + chunk_size]
        if len(chunk) == chunk_size and np.max(np.abs(chunk)) > 0.01:
            f = get_formants(chunk, sr)
            if f and len(f) >= 3:
                samples.append(f[:3])

    if not samples:
        return {"error": "Could not estimate formants. Audio may be too noisy."}

    arr = np.array(samples)
    return {
        "F1_mean_hz": round(float(np.mean(arr[:, 0])), 1),
        "F1_std_hz": round(float(np.std(arr[:, 0])), 1),
        "F2_mean_hz": round(float(np.mean(arr[:, 1])), 1),
        "F2_std_hz": round(float(np.std(arr[:, 1])), 1),
        "F3_mean_hz": round(float(np.mean(arr[:, 2])), 1),
        "F3_std_hz": round(float(np.std(arr[:, 2])), 1),
        "n_samples": len(samples),
        "note": "LPC formant estimation. For clinical accuracy, use Praat."
    }


def analyse_vibrato(y, sr, f0, hop_length=512):
    """
    MODULE 8: VIBRATO DETECTION
    ─────────────────────────────
    Vibrato is a periodic pitch modulation, typically in the 4-8 Hz range.
    Detected by taking the FFT of the pitch contour and looking for peaks
    in the vibrato frequency range.
    """
    print("  [8/8] Vibrato detection...")

    voiced_f0 = f0[~np.isnan(f0)]
    if len(voiced_f0) < 50:
        return {"error": "Insufficient data for vibrato analysis."}

    f0_interp = f0.copy()
    nans = np.isnan(f0_interp)
    if not np.all(nans):
        f0_interp[nans] = np.interp(
            np.flatnonzero(nans), np.flatnonzero(~nans), f0_interp[~nans]
        )
        f0_cents = 1200 * np.log2(f0_interp / np.mean(voiced_f0))
        pitch_sr = sr / hop_length
        fft_pitch = np.abs(np.fft.rfft(f0_cents - np.mean(f0_cents)))
        fft_freqs = np.fft.rfftfreq(len(f0_cents), d=1.0 / pitch_sr)

        vibrato_mask = (fft_freqs >= 4) & (fft_freqs <= 8)
        if np.any(vibrato_mask):
            vib_power = float(np.max(fft_pitch[vibrato_mask]))
            vib_freq = float(fft_freqs[vibrato_mask][np.argmax(fft_pitch[vibrato_mask])])
            total_power = float(np.sum(fft_pitch))
            return {
                "dominant_rate_hz": round(vib_freq, 2),
                "vibrato_power_ratio_pct": round(vib_power / total_power * 100, 3) if total_power > 0 else 0,
                "classification": "Vibrato present" if vib_power / total_power > 0.01 else "Minimal vibrato"
            }

    return {"error": "Could not compute vibrato."}


def analyse_time_diagnostics(y, sr, f0, pitch_results, dynamics_results, resonance_results, hop_length=512):
    """
    Summarises time-based diagnostics for Candi.

    These are supporting indicators for coaching, especially on karaoke/live-room
    recordings where backing track bleed and room noise can confuse F0 detection.
    """
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

    # ─── PITCH STABILITY FLAGS ────────────────────────────────────────────
    pitch = results.get("pitch", {})
    sections = pitch.get("sections", [])
    unstable_sections = [s for s in sections if s.get("cv_percent", 0) > 30]
    if len(unstable_sections) > len(sections) * 0.4:
        flags.append({
            "category": "Pitch",
            "flag": "High pitch instability in upper register",
            "value": f"{len(unstable_sections)}/{len(sections)} sections with CV > 30%",
            "interpretation": "Pitch drift in upper-mid and upper register passages.",
            "likely_cause": "TA-dominant registration pulling chest mass too high. Breath pressure decay.",
            "intervention": "Fry to Head / Lip Trill"
        })
        archetype_scores["Pitch Slider"] += 2

    # ─── PERTURBATION FLAGS ───────────────────────────────────────────────
    pert = results.get("perturbation", {})
    jitter = pert.get("jitter_local_percent", 0)
    if jitter > JITTER_THRESHOLD_PCT:
        hnr = results.get("hnr", {}).get("hnr_db", 20)
        if hnr < 10:
            flags.append({
                "category": "Vocal Fold Behaviour",
                "flag": "Elevated jitter + low HNR",
                "value": f"Jitter: {jitter}% | HNR: {hnr} dB",
                "interpretation": "Compression-led distortion (controlled grit) or breathiness.",
                "likely_cause": "Intentional supraglottic compression. Confirm against context.",
                "intervention": "Bratty Nay (if resonance is dark) / Lip Trill (if breath is leaky)"
            })
            archetype_scores["Pusher"] += 1
        else:
            flags.append({
                "category": "Vocal Fold Behaviour",
                "flag": "Elevated jitter with moderate HNR",
                "value": f"Jitter: {jitter}%",
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
            "value": f"{centroid} Hz",
            "interpretation": "Tone is dark and lacks projection.",
            "likely_cause": "Depressed larynx or retracted tongue root.",
            "intervention": "Bratty Nay / NG Siren"
        })
        archetype_scores["Nasal Tone"] -= 1  # Opposite of nasal
    elif centroid > CENTROID_BRIGHT_THRESHOLD:
        flags.append({
            "category": "Resonance",
            "flag": "High spectral centroid — bright/forward resonance",
            "value": f"{centroid} Hz",
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
    pert = results.get("perturbation", {})
    hnr = results.get("hnr", {})
    res = results.get("resonance", {})
    dyn = results.get("dynamics", {})
    rhythm = results.get("rhythm", {})
    formants = results.get("formants", {})
    vibrato = results.get("vibrato", {})
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
        f"| Pitch Range | {pitch.get('min_note', 'N/A')} – {pitch.get('max_note', 'N/A')} ({pitch.get('range_semitones', 'N/A')} semitones) |",
        f"| Voiced Frames | {pitch.get('voiced_percentage', 'N/A')}% |",
        f"| Std Dev | {pitch.get('std_hz', 'N/A')} Hz |",
        f"",
        f"---",
        f"",
        f"## VOCAL FOLD BEHAVIOUR",
        f"",
        f"| Metric | Value | Clinical Threshold |",
        f"|---|---|---|",
        f"| Jitter (Local) | {pert.get('jitter_local_percent', 'N/A')}% | < {JITTER_THRESHOLD_PCT}% |",
        f"| Jitter (RAP) | {pert.get('jitter_rap_percent', 'N/A')}% | < 0.68% |",
        f"| HNR | {hnr.get('hnr_db', 'N/A')} dB | > {HNR_CLEAN_THRESHOLD_DB} dB (clean) |",
        f"| Classification | {hnr.get('classification', 'N/A')} | — |",
        f"",
        f"---",
        f"",
        f"## RESONANCE",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Spectral Centroid (Mean) | {res.get('spectral_centroid_mean_hz', 'N/A')} Hz |",
        f"| Spectral Rolloff (85%) | {res.get('spectral_rolloff_85_mean_hz', 'N/A')} Hz |",
        f"| Spectral Flatness | {res.get('spectral_flatness_mean', 'N/A')} (0=tonal, 1=noise) |",
        f"| Classification | **{res.get('resonance_classification', 'N/A')}** |",
        f"",
        f"---",
        f"",
        f"## DYNAMICS",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Mean RMS Energy | {dyn.get('mean_rms_db', 'N/A')} dB |",
        f"| Effective Dynamic Range (P10–P90) | {dyn.get('effective_dynamic_range_db', 'N/A')} dB |",
        f"| Full Dynamic Range | {dyn.get('full_dynamic_range_db', 'N/A')} dB |",
        f"",
        f"---",
        f"",
        f"## RHYTHM",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Estimated Tempo | {rhythm.get('estimated_tempo_bpm', 'N/A')} BPM |",
        f"| Onset Rate | {rhythm.get('onsets_per_second', 'N/A')} onsets/sec |",
        f"| Rhythmic Regularity | {rhythm.get('rhythmic_regularity', 'N/A')} (0=irregular, 1=metronomic) |",
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
        "sample_rate": sr
    }

    if stem_metadata:
        results["stem_separation"] = stem_metadata

    # Stage 3: Run all analysis modules
    print("Running analysis pipeline...")
    pitch_results = analyse_pitch(y, sr)
    raw_f0 = pitch_results.pop("raw_f0", None)  # Extract raw F0 for perturbation
    results["pitch"] = pitch_results

    if raw_f0 is not None:
        results["perturbation"] = analyse_perturbation(raw_f0)

    results["hnr"] = analyse_hnr(y)
    results["resonance"] = analyse_resonance(y, sr)
    results["dynamics"] = analyse_dynamics(y, sr)
    results["rhythm"] = analyse_rhythm(y, sr)
    results["formants"] = analyse_formants(y, sr)

    if raw_f0 is not None:
        results["vibrato"] = analyse_vibrato(y, sr, raw_f0)
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

    # Stage 4: Diagnostic logic
    print("\nRunning diagnostic logic engine...")
    flags, archetype = generate_diagnostic_flags(results)
    results["archetype"] = archetype
    results["diagnostic_flags"] = flags
    print(f"  Archetype: {archetype}")
    print(f"  Flags raised: {len(flags)}")

    # Stage 5: Save JSON
    with open(json_output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Raw data saved: {json_output}")

    # Stage 6: Generate Markdown report
    print("\nGenerating diagnostic report...")
    generate_markdown_report(results, flags, archetype, args.name, os.path.basename(args.input_file), report_output)

    print(f"\n{'='*60}")
    print(f"  Analysis complete!")
    print(f"  JSON data:  {json_output}")
    print(f"  Report:     {report_output}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
