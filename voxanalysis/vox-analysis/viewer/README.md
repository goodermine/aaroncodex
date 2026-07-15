# VOXAI-Alpha: Vocal Diagnostics and Analysis

Private/local upload page that separates vocals from backing music, plots the
notes from the vocal stem, and lets the listener toggle the backing stem while
the pitch contour plays.

This directory is the **web entry point only**. It is not the Candi Telegram
agent and it does not read or write Candi's singer memory. Both entry points
call the single shared engine in `../voxai-local-analysis/`; this service must
not maintain a separate copy of the analyser or calibration.

```bash
cd vox-analysis/viewer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:8766>. `ffmpeg` and `ffprobe` must be on `PATH`.

Jobs are limited to 100 MB and 15 minutes. Each job first runs the repository's
UVR two-stem separator, then analyzes the isolated vocal stem. The browser
plays the vocal stem by default; **Background: on** mixes the instrumental stem
back in and **Background: off** leaves the vocal isolated. Local job artifacts
expire after 24 hours. This service deliberately refuses to start with
`VOX_PITCH_ENV=production` while local storage is configured; hosted use
requires durable storage and an external worker queue.

Each job runs the complete V3 diagnostic engine after stem separation while
retaining the deterministic V2 calibrated score. The V3 diagnostics include
timestamped trouble spots, CPPS/strain, registers, breath, range, onset
quality, H1-H8 harmonic profile, singer's-formant projection and vowel-space
mapping. These diagnostic additions do not change the calibrated score.
The completed browser report contains component scores, measured pitch centre
and held-note drift, voice-quality metrics, vibrato, dynamics, phrase and
breath-end checks, range/register indicators, timestamped trouble spots, and a
bounded human-readable coaching summary. The full generated Markdown report
remains available from the completed job. Polling exposes separate pitch,
diagnostic-analysis and report-building stages while the bounded worker runs.

Singer name, song, original artist and optional recording conditions are
captured before upload. The worker resolves a provenance-labelled original,
rejects obvious cover/karaoke substitutions, runs the same shared stem-first
analysis on both recordings, and DTW-aligns the original contour after key
transposition compensation. The chart can show the orange original overlay,
play the original separately, retain the independent backing-track control,
and optionally colour the singer contour from violet toward red as distance
from the nearest equal-tempered note centre increases. Reference failure is a
visible partial result and never invalidates the singer's standalone report.
