# HANDOFF: Live Harmonic Scope — VoceVista-style interactive spectral display

**Audience:** the build agent (external LLM agent) taking on this feature.
**Owner:** Aaron (product decisions, merges). Repo: `rustwoodagent-ops/vox-cloud-alpha`, base branch `main`.
**Written by:** the cloud agent that built the current analysis engine and merged the pitch viewer. Everything below is verified against the code at `main` ≥ `84198b5`.

---

## 0. Mission and mandatory process

**Mission:** the web pitch viewer's interactive scope (canvas) must render the singer's actual spectral energy — harmonics visible as bands, VoceVista-style — as a toggleable layer under the existing pitch line, staying in sync with zoom/pan/seek/playback. Post-take precomputed data only: **no live microphone tracking** (explicitly ruled out by Aaron), **no EGG**.

**Process (non-negotiable order, each step is a deliverable Aaron sees before the next begins):**
1. **PLAN** — your own full implementation plan. A seed design is in §6; you may deviate, but every deviation from a **BINDING** item must be argued explicitly.
2. **AUDIT the plan** — verify your plan's claims against the actual code (paths, formats, rates below have been verified once, but re-verify what your plan depends on). List what the audit changed.
3. **PRE-MORTEM** — the three biggest ways this goes disastrously wrong and the specific countermeasure for each, built into the plan as acceptance criteria (a seed pre-mortem is in §8 — extend it, don't just repeat it).
4. **BUILD** — in phases, each ending with the validation evidence in §7. Ship behind toggles that default OFF.

**Project-wide principles you must not violate (these are the product's identity):**
- Every number shown to a user is a real measurement or a documented formula. Nothing numeric is LLM-generated. The spectral display is **display-only**: no metric, score, or prescription may ever read from it.
- The calibrated technical score, the calibration pack (`backend/voxai-local-analysis/calibration/`), the prescription map (`backend/voxai-local-analysis/knowledge/`), and the exercise library (`openclaw-data/vox-coach/knowledge/`) are **untouchable** in this build. Verify the score of a test analysis is byte-identical before/after your changes.
- Validation is adversarial: every prior feature shipped only after ground-truth synthetic tests, and several first implementations failed their own validation and were fixed before merging (phantom map entries, fake register splits, slides counted as drift). Expect the same standard.
- Style choices are never errors (straight tone, scoops, back-phrasing). Nothing in this feature judges; it only shows.

---

## 1. System map (verified)

```
vox-cloud-alpha/
├── backend/
│   ├── voxai-local-analysis/          # the analysis engine
│   │   ├── analyse_song.py            # ~3.4k lines; all measurement, scoring, plots, CSV
│   │   ├── pitch_track.py             # 517 lines; the VIEWER's pipeline bridge (see §2)
│   │   ├── tools/                     # compare_takes.py, progress_report.py,
│   │   │                              # build_calibration.py, build_prescription_map.py
│   │   ├── calibration/               # pro_reference.json + references/*.json  [DO NOT TOUCH]
│   │   └── knowledge/prescription_map.json                                     [DO NOT TOUCH]
│   ├── pitch-viewer/                  # the web app (FastAPI + single-file frontend)
│   │   ├── app.py                     # 321 lines; job API, see §2
│   │   ├── report_builder.py          # 423 lines; engine JSON -> viewer report payload
│   │   ├── static/index.html          # 85 dense lines; ALL frontend (CSS+HTML+JS, no framework)
│   │   ├── tests/                     # pytest: test_api, test_pitch_track,
│   │   │                              #         test_report_builder, test_ui_contract
│   │   ├── requirements.txt           # fastapi, uvicorn, python-multipart, httpx, yt-dlp
│   │   │                              # + "-r ../voxai-local-analysis/requirements.txt"
│   │   └── runtime/                   # per-job artifacts (gitignored)
│   └── reference-downloader/          # yt-dlp original fetcher (used by pitch_track)
├── docs/metrics-methodology.md        # audit trail for every metric — add your layer's section
└── openclaw-data/vox-coach/knowledge/ # coaching knowledge files                [DO NOT TOUCH]
```

Run the app: `cd backend/pitch-viewer && python app.py` → uvicorn on `127.0.0.1:8766`.
Run tests: `cd backend/pitch-viewer && python -m pytest tests/`.

---

## 2. How a job flows today (verified against code)

1. `POST /api/pitch-jobs` (multipart upload + fields) → job dir `runtime/<job_id>/` with `job.json` manifest; `202` returned; background thread runs `_process()` (app.py:81).
2. `_process` shells out to **`pitch_track.py`** with `--job-dir`, `--name`, `--song`, `--artist`, `--conditions`, `--stage-file stage.json`, optional `--skip-comparison`. Timeout `ANALYSIS_TIMEOUT`.
3. `pitch_track.py` does: stem separation (UVR via audio-separator) → runs the engine (`analyse_song.py`, referenced as `SHARED_ANALYZER`) → optionally fetches + analyses the verified original (yt-dlp) → melody comparison via `tools/compare_takes.py` (`load_contour`/`dtw_align` imported as a library) → writes `result.json` into the job dir, including:
   - `contour`: the **browser display contour** — pitch_track runs its own pyin with confidence and downsamples via `_sample_contour()` (~10 Hz bins, median cents per bin, 350-cent octave-outlier rejection, `null` for unvoiced/low-confidence). Units: **cents relative to A440**; JS converts via `midi()`.
   - `reference.contour` (same format) when comparison ran, `duration_seconds`, `quality` flags, `robust_min/max_note`.
   - `audio_files` → served as `audio_urls`: `/api/pitch-jobs/{id}/audio?track=vocals|instrumental|original`.
   - `v2_analysis_file`/`v2_report_file` → engine JSON + markdown; `report_builder.build_v2_report()` shapes the viewer payload.
4. Frontend polls `GET /api/pitch-jobs/{id}` (stage names drive the signal-chain UI: `separating_vocals`, `tracking_pitch`, `running_v2_analysis`, `finding_original`, `analysing_original`, `aligning_comparison`, `building_report`).
5. `_cleanup()` prunes old job dirs on startup (retention exists — reuse it for your artifacts).

## 3. Frontend scope internals (verified)

All in `static/index.html` (vanilla JS, one `<canvas id="chart">`, 2D context):
- `draw()` fully redraws every call: note lanes per semitone (`lo..hi` from the 5th–95th percentile of visible contours, min 6 semitone range), left pad **44px** for note labels, clipped plot region, contours, playhead.
- `drawContour(values, rate, view, lo, range, w, h, pad, colour, width, colourByPitch)` — segment-by-segment lines; `colourByPitch=true` applies `pitchErrorColour(value)` (the **Accuracy** overlay).
- Current colours (recent product decisions — respect them): singer's main line **blue `#3b82f6`** (Aaron chose this explicitly), original overlay `#ff935c`, playhead `#4dd9ff`, Accuracy palette unchanged and **toggle defaults OFF** (`pitchColourOn=false`). Legend swatches at index.html line ~33.
- Controls: `#originalOverlay`, `#pitchColour` (Accuracy), zoom `#plus/#minus/#reset` (zoom up to 16×), `#follow`, transport with vocal/instrumental sync and original A/B. `view()` computes `{start, end, window}` from zoom/offset/follow.
- Repaints are driven by a self-scheduling `requestAnimationFrame(tick)` loop (plus seek/resize/toggle events). **Your spectrogram layer must not be recomputed inside that loop** — render it to an offscreen canvas on view changes only and let `tick` blit it.

## 4. Engine facts relevant to this build

- The engine persists `pitch.f0_contour` (10 Hz cents, nulls unvoiced) in every analysis JSON — the melody-match tool consumes it. Your time-resolved harmonic export should follow the same JSON conventions (`rate_hz`, `values`, units documented).
- The engine already computes per-note H1–H8 medians (`harmonics` block) and singer's-formant band energy — but **nothing time-resolved**. Static plots already draw k×F0 harmonic traces on a spectrogram (see `generate_visual_diagnostics`, panel 6) — reuse its conventions, not its code.
- Engine outputs must never gain a hard dependency on your exporter: wrap it so failure degrades to "no spectral layer" while analysis, score, and report complete normally.
- `docs/metrics-methodology.md` documents every output — add a section for your artifacts (format, rates, limits, display-only status).

## 5. Environment gotchas (all hit during previous builds)

- **CPU-only**, no GPU. Stem separation is the slow stage (~minutes/track).
- **GitHub release downloads 403** behind this infra's proxy; the UVR model was fetched from the HuggingFace mirror into `/tmp/audio-separator-models/`. `ffmpeg` must be installed (`apt-get update && apt-get install -y ffmpeg` on the cloud container; already present on Aaron's machine).
- **Aaron's production server has ~12 GB disk** (per HANDOFF.md): size budgets are real. Viewer artifacts live under `runtime/<job_id>/` and ride the existing `_cleanup()` retention.
- **Canvas/image limits on mobile Safari** (~16,384 px max dimension; decoded-image memory caps): a 3-minute take at fine time resolution exceeds a single image — hence tiling (§6).
- Local agents: "Howard" (machine/git admin) and "Candi" (coaching agent, runs the Telegram flow). Candi's flow calls the engine directly — your engine-side exporter must be **flag-gated OFF by default** so her pipeline is unaffected until deliberately enabled.

## 6. Seed technical design (BINDING items marked)

**Data (Phase 0):**
- **BINDING: constant-Q transform, not linear STFT.** The scope's y-axis is semitones; linear FFT resolution (~11 Hz at n_fft 4096) is coarser than a semitone below ~C3 and smears the display. Use `librosa.cqt` (or VQT), 2–4 bins/semitone, range ≈ C2–C7, hop giving 20–45 frames/sec.
- **BINDING: precompute server-side during the job; no client DSP.** Export as tiled 8-bit grayscale PNGs (≤2048 px wide per tile) + JSON descriptor `{t0, fps, midi_lo, bins_per_semitone, tiles:[...], db_floor, db_ceil}`. PNG = free decode + GPU-friendly `drawImage`.
- Time-resolved `harmonic_tracks`: H1–H8 dB (relative to strongest) at ~10 Hz, from k×F0 band peaks — powers a live readout, small JSON.
- Exporter lives in the **engine** (new module or flag on `analyse_song.py`), invoked by `pitch_track.py` for viewer jobs; also run for the reference original when comparison is on.

**Backend (Phase 1):** serve tiles + descriptors via new `GET /api/pitch-jobs/{id}/spectral?...` endpoints (same job-dir security model as `get_audio` — note its path-traversal guard `_job_dir`). Extend `result.json` with `spectral` metadata + URLs. Feature-detect: absent artifacts → viewer disables the toggle with "re-analyse to enable".

**Frontend (Phase 2):**
- Layer order: spectrogram (offscreen canvas, redrawn **only on view change**, never per playback frame) → note lanes → harmonic guide curves (harmonic k = the blue line shifted up by exactly **12·log₂(k)** semitones: +12.00, +19.02, +24.00, +27.86, +31.02, +33.69, +36.00 — note that only octave harmonics align with note lanes; H3/H5/H6/H7 sit *between* lanes and that is physically correct) → singer's blue line → Accuracy overlay → reference contour → playhead.
- **BINDING: monochrome-dim spectrogram** (dark cyan/grey ramp, low alpha) so the blue line and Accuracy palette stay dominant; **both new toggles default OFF** ("clean by default" is Aaron's standing instruction).
- Readout rail: live H1–H8 meters at the playhead from `harmonic_tracks`.
- A/B mode shows the **active source's** spectrogram only — never two at once.

**Phase 3:** lazy tile decode around the view; graceful cache eviction; mobile pass.

## 7. Validation gates (each phase blocks on its gate)

1. **Ground truth:** synthesize a tone with known harmonics (e.g. 220 Hz + exact overtone series, known onset time; additive synthesis with numpy/soundfile). The rendered layer must put H1 on the A3 lane and each Hk at exactly **12·log₂(k) semitones above F0** (+12.00, +19.02, +24.00, +27.86, … — do NOT assert integer lanes; non-octave harmonics legitimately sit between lanes), time-aligned to the known onset within one frame. Automate as a pytest that checks the descriptor math (row/col ↔ midi/time mapping), not by eyeballing.
2. **Alignment cross-check in-app:** guide curves over the image — any engine-vs-display misalignment is visible by construction. Screenshot evidence on a real take.
3. **Performance:** with the layer ON, a 3–4 minute take must hold ≥45 fps during playback on a mid/low-tier device profile (CPU-throttled Chrome is acceptable evidence) and startup decode must not block first paint. A frame-time watchdog auto-disables the layer above budget and surfaces a notice.
4. **Regression:** every existing scope behavior unchanged with toggles OFF (the `test_ui_contract.py` pattern exists — extend it); engine analysis JSON of a fixed input is **identical** with the exporter flag off, and the technical score identical with it on.
5. **Size budget:** ≤ ~3 MB spectral artifacts per typical take (measure and report actuals); artifacts under `runtime/<job_id>/` and covered by `_cleanup()`.

## 8. Seed pre-mortem (extend with your own)

1. **Performance collapse** → offscreen-canvas discipline, watchdog auto-degrade, default-off toggles, perf gate before merge (details §7.3).
2. **Beautiful but wrong** (misaligned or artifact-driven display teaching singers falsehoods) → ground-truth pytest, guide-curve cross-check, "spectral energy — display only" labelling in the legend, and the hard rule that nothing numeric reads from this layer.
3. **Pipeline blowup** (analysis time/disk doubles; Candi's flow or the 12 GB server breaks) → engine flag default-off, failure-isolated exporter, size budget, runtime-dir retention. The analysis must succeed even if the exporter throws.

## 9. Working agreements

- **Branch:** create `feature/live-harmonic-scope` from latest `main`. Never commit to `main` directly; never rewrite others' history; PRs to `main` as **draft** — Aaron says "merge". Squash-merge is the repo convention.
- Commit messages: imperative summary + body explaining what/why + validation evidence. Do not include model identifiers.
- Do not touch: calibration files, prescription map, knowledge files, scoring code paths, Candi's handoff docs. Colour decisions in §3 stand unless Aaron says otherwise.
- **Report back to Aaron** at each gate with: what was validated, the evidence (numbers/screenshots), what changed from the plan and why, and what's next. If a gate fails, say so plainly and stop — failed validation is a report, not a silent rework.
- Known open work by others (don't collide): Candi is re-analysing the 38-track reference pack (`docs/CANDI_HANDOFF_REFERENCE_REANALYSIS.md`); rubric v3 will follow on the cloud side. Neither touches the viewer.

## 10. Quick-start checklist

```bash
git clone <repo> && cd vox-cloud-alpha
git checkout -b feature/live-harmonic-scope origin/main
pip install -r backend/pitch-viewer/requirements.txt   # pulls engine deps incl. praat-parselmouth
apt-get install -y ffmpeg                               # if missing
cd backend/pitch-viewer && python -m pytest tests/      # green before you start
python app.py                                            # http://127.0.0.1:8766
# analyse any mp3/m4a through the UI once to see the current end-to-end flow
```

Deliverable #1 is your PLAN (with audit + pre-mortem), not code.
