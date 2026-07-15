#!/bin/bash
# =============================================================================
# VOXAI Local Analysis System — WSL Installer
# =============================================================================
# Purpose:   Set up the complete VOXAI vocal analysis environment on WSL Ubuntu.
# Tested on: Ubuntu 22.04 LTS (WSL2 on Windows 10/11)
# Usage:     chmod +x install.sh && ./install.sh
# =============================================================================

set -e  # Exit immediately if any command fails

echo ""
echo "=============================================="
echo "  VOXAI Local Analysis System — Installer"
echo "=============================================="
echo ""

# ─── STEP 1: System Update ────────────────────────────────────────────────────
# Refreshes the package list and upgrades any outdated packages.
# This ensures you have the latest security patches and compatible library versions.
echo "[1/7] Updating system packages..."
sudo apt update -y && sudo apt upgrade -y

# ─── STEP 2: System Dependencies ─────────────────────────────────────────────
# ffmpeg:         The industry-standard media conversion tool.
#                 Used to extract audio from video files (mp4 → wav) and to
#                 convert between audio formats (mp3 → wav).
#
# libsndfile1:    A C library for reading/writing audio files.
#                 Required by Python's 'soundfile' package.
#
# libsndfile1-dev: Development headers for libsndfile. Required to compile
#                  certain Python audio packages from source.
#
# python3-pip:    The Python package installer.
#
# python3-venv:   Allows creation of isolated Python virtual environments,
#                 preventing dependency conflicts with other Python projects.
#
# build-essential: GCC compiler and make tools. Required by some Python packages
#                  that compile C extensions (e.g., scipy, librosa internals).
echo "[2/7] Installing system dependencies..."
sudo apt install -y \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    python3-pip \
    python3-venv \
    build-essential \
    git

# ─── STEP 3: Project Directory Structure ─────────────────────────────────────
# Creates the required folder layout for the project.
# -p flag: creates parent directories if they don't exist; no error if exists.
echo "[3/7] Creating project directory structure..."
mkdir -p input      # Place your raw audio/video files here before running analysis
mkdir -p output     # JSON data files and intermediate processing outputs
mkdir -p temp       # Temporary files (ffmpeg conversions, stem separation)
mkdir -p models     # Downloaded AI model weights (e.g., Spleeter, CREPE)
mkdir -p reports    # Final Markdown diagnostic reports

echo "    Directories created: input/ output/ temp/ models/ reports/"

# ─── STEP 4: Python Virtual Environment ──────────────────────────────────────
# Creates an isolated Python environment in ./voxai_env/
# This means all Python packages are installed here, not system-wide,
# which prevents conflicts and keeps the system Python clean.
echo "[4/7] Creating Python virtual environment..."
python3 -m venv voxai_env

# Activate the virtual environment for the remainder of this script
source voxai_env/bin/activate

echo "    Virtual environment created at: ./voxai_env/"

# ─── STEP 5: Upgrade pip ─────────────────────────────────────────────────────
# Always upgrade pip before installing packages to avoid resolver issues.
echo "[5/7] Upgrading pip..."
pip install --upgrade pip setuptools wheel

# ─── STEP 6: Install Python Dependencies ─────────────────────────────────────
# Installing in a specific order to avoid dependency resolution issues.
echo "[6/7] Installing Python dependencies..."

# numpy: Foundational numerical computing library.
#        Used for array operations, statistical calculations (mean, std, percentile),
#        and as the base for all other scientific libraries.
pip install numpy

# scipy: Scientific computing library.
#        Used specifically for LPC (Linear Predictive Coding) formant estimation
#        and signal processing utilities.
pip install scipy

# soundfile: Python bindings for libsndfile.
#            Used to read and write WAV files reliably.
pip install soundfile

# librosa: The core acoustic analysis engine.
#          Provides: pyin (pitch tracking), spectral features (centroid, rolloff,
#          flatness, bandwidth, contrast), RMS energy, onset detection,
#          beat tracking, HPSS (harmonic/percussive separation), and MFCCs.
pip install librosa

# matplotlib: Plotting library.
#             Used to generate visual charts of pitch contours, spectrograms,
#             and energy curves in the output reports.
pip install matplotlib

# openai: OpenAI Python client.
#         Used in the report generation stage to send acoustic metrics to
#         a language model (GPT-4) for conversion into natural language feedback.
#         OPTIONAL — remove this line if you do not have an OpenAI API key.
pip install openai

# ─── STEP 7: Optional — Vocal Isolation (Spleeter) ───────────────────────────
# Spleeter is an AI-based source separation tool by Deezer.
# It separates vocals from the instrumental backing track, which dramatically
# improves the accuracy of pitch and perturbation measurements on mixed recordings.
#
# IMPORTANT: Spleeter requires TensorFlow and downloads ~200MB of model weights
# on first use. It also requires a GPU for fast processing (CPU is slow but works).
# Uncomment the lines below to install it.
#
# echo "    Installing Spleeter (vocal isolation)..."
# pip install spleeter

# ─── STEP 8: Optional — High-Accuracy Pitch Tracking (CREPE) ─────────────────
# CREPE is a neural network pitch tracker that outperforms librosa's pyin,
# especially on distorted or raspy vocals.
# Requires TensorFlow. Uncomment to install.
#
# echo "    Installing CREPE (neural pitch tracker)..."
# pip install crepe

# ─── STEP 9: Write requirements.txt ──────────────────────────────────────────
# Freeze the installed packages to a requirements file for reproducibility.
# Anyone can recreate this exact environment with: pip install -r requirements.txt
echo "[7/7] Saving requirements.txt..."
pip freeze > requirements.txt

# ─── COMPLETE ─────────────────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo "  Installation Complete!"
echo "=============================================="
echo ""
echo "  Next steps:"
echo "  1. Activate the environment:"
echo "     source voxai_env/bin/activate"
echo ""
echo "  2. Place an audio file in the input/ folder."
echo ""
echo "  3. Run the analysis:"
echo "     python analyse_song.py input/your_file.wav"
echo ""
echo "  4. Recommended stem-first analysis:"
echo "     python analyse_song.py input/your_file.wav --separate-stems"
echo ""
echo "  5. Find your results in the output/ and reports/ folders."
echo ""
echo "  OPTIONAL: To use the AI report generation feature,"
echo "  set your OpenAI API key:"
echo "     export OPENAI_API_KEY='your-key-here'"
echo ""
