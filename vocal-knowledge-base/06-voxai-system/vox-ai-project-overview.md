---
title: "VOX AI Project Overview"
category: coaching-system
topics: [recording, warm-up, pitch-accuracy, tone]
words: 592
author: "Aaron Ellis"
status: active
---

# VOX AI Project Overview

## VOX AI \| Vocal Protocol Analyst

**Visionary:** Aaron Ellis (2026) **Core Mission:** To bridge the gap between technical signal processing and emotive vocal performance through the VOXAI Protocol 6.

### 1. Project Objective

VOX AI is a high-performance web-based application designed to provide singers with professional-grade vocal coaching in real-time and post-performance. By combining traditional digital signal processing (DSP) with the Gemini AI engine, the tool offers a "coach in your pocket" experience that is technically precise, body-aware, and transformation-focused.

### 2. Core Functional Pillars

#### A. Real-Time Pitch Engine

- **Precision Tuner:** A high-visibility interface providing note identification and a "needle" gauge for cents-level accuracy.

- **Stability Tracker:** A scrolling spectral history graph that tracks pitch over time.

  - **Color-Coding:** Green for "Locked" (perfect intonation), Amber for Sharp, and Blue for Flat.

  - **Musical Axis:** A vertical Y-axis mapped to musical notes (C2–C6), allowing singers to visualize their melodic contours and "scoops."

- **Vocal Range Discovery:** Automated tracking of the "Vocal Floor" (lowest note) and "Vocal Ceiling" (highest note) during a session.

#### B. Diagnostic Suite

The system converts complex audio data into three user-friendly percentage metrics:

1.  **Vocal Power (RMS):** Measures raw energy and breath support efficiency.

2.  **Signal Texture (Crest Factor):** Analyzes the "punch" or compression of the vocal tone, identifying breathy vs. resonant delivery.

3.  **Scoop Precision:** Tracks how cleanly a singer lands on a note versus sliding into it.

#### C. The VOXAI Protocol 6 Analysis

Upon completing a recording (up to 5 minutes) or uploading a high-quality M4A file, the AI Analyst performs a deep-dive diagnostic:

- **Vocal Archetype:** Identifying the singer's current delivery style (e.g., "Chest Pusher," "Mixed Specialist").

- **Technical Breakdown:** Detailed analysis of pitch, tone, timing, breath control, support, registration, and physical tension.

- **Physical Corrections:** Direct advice on what a correction should *feel* like in the body (e.g., "Feel the expansion in your lower ribs").

- **Emotional Coaching:** Character prompts and phrasing advice to evolve the next take.

### 3. Technical Architecture

#### Signal Processing (DSP)

- **Fast-AMDF Algorithm:** An optimized Average Magnitude Difference Function for low-latency pitch detection that works efficiently on mobile devices without starving the UI thread.

- **Stability Filtering:** Logic that distinguishes between background noise and intentional singing to ensure range markers (Floor/Ceiling) are accurate.

- **Hardware Calibration:** User-adjustable Mic Input Gain and a digital Noise Gate to ensure signal clarity in various environments.

#### AI Integration

- **Model:** Powered by **Gemini 2.5 Flash**, utilizing its advanced audio-understanding capabilities.

- **Multi-Modal Input:** The system converts recorded Blobs or uploaded M4A files into Base64 data, routed with a strict "Elite Vocal Coach" system prompt.

### 4. User Workflow

1.  **Initialization:** The user syncs their hardware (mic) to the VOX Core.

2.  **Calibration:** Adjust Gain and Noise Gate based on the "Current Signal" meter to filter out room noise.

3.  **Warm-up:** Use the **Analyse Pitch** mode to check the vocal floor and ceiling or practice scales with the Stability Tracker.

4.  **Capture:** Record a performance (up to 5 minutes) or upload a pre-recorded high-quality file (e.g., from Dolby On).

5.  **Transformation:** Receive the VOXAI Protocol 6 feedback, including specific physical drills and emotional character character character characters characters character prompts for the next take.

### 5. Future Evolution

The project is built as a single-file, portable web module, ensuring it can be integrated into larger studio environments or used as a standalone mobile tool for touring artists. The 2026 roadmap focuses on "body-aware" coaching, emphasizing the physical sensations of singing over abstract musical theory.
