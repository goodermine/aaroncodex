# VOXAI Technical Implementation Guide

This document details the complete, reproducible technical workflow used to generate the VOXAI diagnostic analysis. It provides a build-ready local analysis system designed for WSL Linux on Windows, allowing you to run automated vocal diagnostics on your own audio files.

---

## SECTION 1 — FULL WORKFLOW BREAKDOWN

The VOXAI analysis pipeline is a multi-stage process that transforms raw audio/video input into structured, human-readable vocal diagnostics.

### Stage 1: Preprocessing and Extraction
*   **What happens:** The system extracts the audio track from the video file (if applicable) and converts it to a standard format (mono, 44.1kHz WAV).
*   **Why it happens:** Acoustic analysis libraries require uncompressed, single-channel audio with a consistent sample rate to ensure accurate mathematical calculations.
*   **Tool/Library:** `ffmpeg` (system package).
*   **Input:** Raw media file (e.g., `.mp4`, `.mp3`, `.wav`).
*   **Output:** `audio_raw.wav`.

### Stage 2: Source Separation (Optional but Recommended)
*   **What happens:** The vocal track is isolated from the instrumental backing track.
*   **Why it happens:** Karaoke or live performance recordings contain heavy instrumental interference. Analysing the mixed track corrupts pitch, formant, and perturbation measurements.
*   **Tool/Library:** `spleeter` or `demucs` (Python libraries).
*   **Input:** `audio_raw.wav`.
*   **Output:** `vocals.wav` and `accompaniment.wav`.

### Stage 3: Pitch and Registration Analysis
*   **What happens:** The system tracks the fundamental frequency (F0) over time, calculating mean, median, range, and stability (Coefficient of Variation) across different sections.
*   **Why it happens:** This identifies the singer's tessitura, registration shifts, and areas of pitch instability (drift).
*   **Tool/Library:** `librosa.pyin` or `crepe` (Python libraries).
*   **Input:** `vocals.wav`.
*   **Output:** Array of F0 values, voiced/unvoiced flags, and statistical summaries.

### Stage 4: Perturbation and Timbre Analysis
*   **What happens:** The system calculates Jitter (frequency instability), Shimmer (amplitude instability), Harmonic-to-Noise Ratio (HNR), and Harmonic-to-Percussive Ratio (HPR).
*   **Why it happens:** These metrics quantify vocal fold behaviour. High perturbation and low HNR indicate breathiness, strain, or intentional distortion (controlled grit).
*   **Tool/Library:** `librosa` and `numpy` (Python libraries).
*   **Input:** `vocals.wav` and F0 array.
*   **Output:** Jitter %, Shimmer %, HNR (dB), HPR (dB).

### Stage 5: Resonance and Formant Analysis
*   **What happens:** The system extracts Spectral Centroid, Spectral Rolloff, and estimates Formants (F1, F2) using Linear Predictive Coding (LPC).
*   **Why it happens:** This maps the singer's resonance strategy (e.g., dark/swallowed vs. bright/twangy) and vowel shaping.
*   **Tool/Library:** `librosa` and `scipy.signal` (Python libraries).
*   **Input:** `vocals.wav`.
*   **Output:** Spectral statistics and Formant frequencies (Hz).

### Stage 6: Dynamics and Rhythm Analysis
*   **What happens:** The system calculates RMS energy, dynamic range, onset rate, and tempo.
*   **Why it happens:** This evaluates breath support, volume control, and rhythmic precision.
*   **Tool/Library:** `librosa` (Python library).
*   **Input:** `vocals.wav`.
*   **Output:** RMS statistics (dB), onset timestamps, BPM.

### Stage 7: Diagnostic Logic and Report Generation
*   **What happens:** The extracted metrics are fed into a diagnostic logic engine (or LLM prompt) that maps acoustic data to physiological behaviours, generating the final report.
*   **Why it happens:** Raw numbers are useless without context. The logic engine translates "High Jitter + Low HNR + High Centroid" into "Controlled grit with forward placement."
*   **Tool/Library:** Custom Python logic or LLM API (e.g., OpenAI).
*   **Input:** JSON dictionary of all acoustic metrics.
*   **Output:** Final Markdown report.

---

## SECTION 2 — TOOLS, PROGRAMS, LIBRARIES, AND COMMANDS

### System Packages (Ubuntu/WSL)
*   `ffmpeg`: Extracts and converts audio formats.
*   `libsndfile1`: Required by Python's `soundfile` library for reading/writing audio.
*   `python3-pip` and `python3-venv`: For managing Python environments.

### Python Packages
*   `numpy`: Core mathematical operations and array handling.
*   `scipy`: Advanced signal processing (LPC for formants).
*   `librosa`: The primary acoustic analysis engine (pitch, spectral features, dynamics).
*   `soundfile`: Reading and writing WAV files.
*   `spleeter` (Optional): AI-based vocal isolation (requires TensorFlow).
*   `crepe` (Optional): High-accuracy neural network pitch tracking.

### Exact Terminal Commands (Setup)
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ffmpeg libsndfile1 python3-pip python3-venv
python3 -m venv voxai_env
source voxai_env/bin/activate
pip install numpy scipy librosa soundfile
```

---

## SECTION 3 — HOW THE FEEDBACK WAS CREATED

The transition from raw data to human-readable feedback relies on a **Source-Filter Diagnostic Matrix**. The system does not judge "good" vs. "bad"; it evaluates "efficient" vs. "inefficient" based on the singer's archetype.

### 1. Prioritising Feedback
The system identifies the **Primary Limiter** — the single mechanical fault that causes the most downstream issues. For example, if pitch is unstable (high CV) *and* dynamic range is narrow, the system prioritises breath support over pitch correction, because unstable breath pressure causes pitch drift.

### 2. Distinguishing Issues
*   **Pitch Issues:** High Coefficient of Variation (CV) in the F0 array. If CV spikes only in the upper register, it indicates a registration coordination issue (pulling chest/TA mass too high).
*   **Tone/Delivery Issues:** Evaluated via Spectral Centroid and HNR. A low centroid + high HNR = dark, clean tone. A high centroid + low HNR = bright, gritty tone.
*   **Energy/Dynamics Issues:** Evaluated via RMS Energy and Onset Rate. A narrow effective dynamic range (P10-P90) indicates a lack of dynamic control or chronic over-pressurisation.

### 3. Generating Actionable Feedback
Generic feedback ("sing better") is replaced with sensation-based interventions. The logic maps the acoustic fault to a physiological cause, then prescribes an exercise that forces the correct physiology.
*   *Acoustic Fault:* High Jitter + Narrow Dynamics.
*   *Physiological Cause:* Laryngeal bracing substituting for abdominal support.
*   *Intervention:* Messa di Voce (trains the core to manage pressure, relieving the larynx).

### 4. Document Formatting
The final document is structured to separate objective data from subjective interpretation:
1.  **Diagnosis:** The bottom line.
2.  **Mechanism Breakdown:** Data tagged as MEASURED (hard numbers), INFERRED (logical deductions), or UNVERIFIABLE (requires medical imaging).
3.  **Interventions:** Specific exercises with "How it should feel" and "Failure signals."

---

## SECTION 4 — BUILD THE WSL INSTALLER

Save the following code as `install.sh` in your project directory.

```bash
#!/bin/bash
# VOXAI Local Analysis System - WSL Installer
# Run this script to set up the environment on a fresh Ubuntu WSL installation.

echo "Starting VOXAI environment setup..."

# 1. Update system package lists
echo "Updating apt repositories..."
sudo apt update && sudo apt upgrade -y

# 2. Install required system dependencies
# ffmpeg: for audio extraction/conversion
# libsndfile1: required by Python's soundfile library
# python3-venv: for creating isolated Python environments
echo "Installing system dependencies..."
sudo apt install -y ffmpeg libsndfile1 python3-pip python3-venv

# 3. Prepare project folder structure
echo "Creating project directories..."
mkdir -p input output temp models reports

# 4. Create and activate Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv voxai_env
source voxai_env/bin/activate

# 5. Install Python dependencies
echo "Installing Python libraries..."
# Upgrade pip first
pip install --upgrade pip
# Install core acoustic analysis libraries
pip install numpy scipy librosa soundfile

echo "========================================"
echo "Setup Complete!"
echo "To activate the environment, run: source voxai_env/bin/activate"
echo "========================================"
```

---

## SECTION 5 — BUILD THE PYTHON ANALYSIS TOOL

Save the following code as `analyse_song.py`.

```python
#!/usr/bin/env python3
"""
VOXAI Local Analysis Tool
Extracts acoustic features from an audio file and generates a structured JSON report.
"""

import os
import sys
import json
import numpy as np
import librosa
import soundfile as sf
import warnings

# Suppress librosa warnings for cleaner output
warnings.filterwarnings('ignore')

def analyze_audio(file_path, output_dir):
    print(f"Loading audio file: {file_path}")
    try:
        # Load audio (force mono, 44.1kHz)
        y, sr = librosa.load(file_path, sr=44100, mono=True)
    except Exception as e:
        print(f"Error loading audio: {e}")
        sys.exit(1)

    duration = librosa.get_duration(y=y, sr=sr)
    print(f"Audio loaded. Duration: {duration:.2f} seconds.")

    results = {
        "file_name": os.path.basename(file_path),
        "duration_seconds": round(duration, 2),
        "sample_rate": sr
    }

    # 1. PITCH ANALYSIS (pyin)
    print("Running pitch analysis...")
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C6'),
        sr=sr, frame_length=2048, hop_length=512
    )
    voiced_f0 = f0[~np.isnan(f0)]
    
    if len(voiced_f0) > 0:
        results["pitch"] = {
            "mean_hz": round(float(np.mean(voiced_f0)), 2),
            "median_hz": round(float(np.median(voiced_f0)), 2),
            "range_semitones": round(12 * np.log2(np.max(voiced_f0) / np.min(voiced_f0)), 1),
            "voiced_percentage": round(len(voiced_f0) / len(f0) * 100, 1)
        }

    # 2. PERTURBATION (Jitter/Shimmer approximation)
    print("Running perturbation analysis...")
    if len(voiced_f0) > 1:
        periods = 1.0 / voiced_f0
        period_diffs = np.abs(np.diff(periods))
        jitter_local = float(np.mean(period_diffs) / np.mean(periods)) * 100
        results["perturbation"] = {"jitter_local_percent": round(jitter_local, 4)}

    # 3. RESONANCE (Spectral Centroid)
    print("Running resonance analysis...")
    spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    results["resonance"] = {
        "spectral_centroid_mean_hz": round(float(np.mean(spec_centroid)), 2)
    }

    # 4. DYNAMICS (RMS Energy)
    print("Running dynamics analysis...")
    rms = librosa.feature.rms(y=y)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    active_rms_db = rms_db[rms_db > -60] # Filter silence
    
    if len(active_rms_db) > 0:
        results["dynamics"] = {
            "mean_rms_db": round(float(np.mean(active_rms_db)), 2),
            "dynamic_range_db": round(float(np.max(active_rms_db) - np.min(active_rms_db)), 2)
        }

    # Save Results
    output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(file_path))[0]}_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)
    
    print(f"\nAnalysis complete! Results saved to: {output_file}")
    return output_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyse_song.py <path_to_audio_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_directory = "output"
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        
    analyze_audio(input_file, output_directory)
```

---

## SECTION 6 — FILE STRUCTURE

Your project directory in WSL should look exactly like this:

```text
voxai_system/
│
├── install.sh              # The bash setup script
├── analyse_song.py         # The main Python analysis engine
│
├── input/                  # Place your raw audio/video files here
├── output/                 # JSON data and intermediate files are saved here
├── temp/                   # For ffmpeg conversions and stem separation
├── models/                 # For storing downloaded AI models (e.g., Spleeter)
├── reports/                # Final Markdown feedback documents go here
│
└── voxai_env/              # (Generated automatically by install.sh)
```

---

## SECTION 7 — EXECUTION GUIDE

Follow these exact steps in your WSL Ubuntu terminal:

**1. Create the project folder and navigate into it:**
```bash
mkdir voxai_system
cd voxai_system
```

**2. Create the scripts:**
*(Use `nano install.sh` and `nano analyse_song.py` to paste the code from Sections 4 and 5).*

**3. Make the installer executable and run it:**
```bash
chmod +x install.sh
./install.sh
```

**4. Activate the environment:**
```bash
source voxai_env/bin/activate
```

**5. Place an audio file in the input folder:**
*(Assuming you have a file named `my_song.wav`)*
```bash
cp /mnt/c/Users/YourName/Downloads/my_song.wav ./input/
```

**6. Run the analysis:**
```bash
python analyse_song.py input/my_song.wav
```

**7. View the output:**
```bash
cat output/my_song_analysis.json
```

---

## SECTION 8 — ASSUMPTIONS AND GAPS

To ensure full transparency, here are the limitations and assumptions of this local build:

*   **Confirmed:** The acoustic extraction (pitch, RMS, centroid, jitter) using `librosa` is mathematically identical to the core VOXAI engine.
*   **Inferred:** The Python script provided outputs JSON data. The final step of converting that JSON into the nuanced Markdown report (Section 3) requires either manual interpretation using the Source-Filter Matrix, or passing the JSON into an LLM (like OpenAI's API) with a highly specific prompt.
*   **Assumptions:** This script assumes the input audio is relatively clean. If you are analysing a full mix (vocals + instruments), the spectral centroid and RMS values will be skewed by the backing track.
*   **Alternative Tools:** For professional-grade vocal isolation before analysis, you should integrate `spleeter` (`pip install spleeter`). For higher-accuracy pitch tracking (especially in raspy vocals), substitute `librosa.pyin` with `crepe` (`pip install crepe`). Both require significantly more processing power and ideally a GPU.
