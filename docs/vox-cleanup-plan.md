# Vox Cleanup Tool — Product & Engineering Plan

*Name TBD — will live under the Vox Coaching brand family (candidates in §7). An AI vocal
cleanup tool inspired by NoiseWorks VoiceAssist, with one big differentiator: you can feed
it a **full song**, not just a pre-isolated voice track.*

---

## 0. Decisions made

- **First users**: (a) vocalists/singers cleaning up vocals in their own music, and
  (b) people recording talks, sermons, and podcasts. Two audiences → two input modes (§1a).
- **Runtime**: runs **locally on the founder's Geekom A9 Max (AMD Ryzen, 128 GB RAM)**
  initially. No cloud, no hosting costs. The 128 GB of RAM fits every model in memory
  comfortably; inference runs on the strong Ryzen CPU (PyTorch CPU backend — a few
  minutes per song for separation, seconds for everything else). The integrated Radeon
  iGPU has no official ROCm support, so GPU acceleration is a later nice-to-have
  (likeliest path: ONNX Runtime + DirectML on Windows), not a requirement.
- **Brand**: this is an add-on to the Vox Coaching ecosystem (voice analysis/coaching).
  The "Pulse" name from this repo's old site is unrelated and dropped.

---

## 1. The core idea

VoiceAssist (and every tool like it — iZotope RX, Waves Clarity, Adobe Podcast Enhance)
assumes you already have a solo voice recording. Our version removes that assumption:

```
Full mixed song ──► Separate vocals ──► Analyze ──► Apply fixes ──► Outputs
                    (AI stem split)     (per-module)  (render pass)
```

**Outputs:**
1. **Cleaned vocal stem** — the isolated, repaired vocal on its own
2. **Remixed song** — cleaned vocal recombined with the original instrumental
3. **Removed** — audio of the targeted removal only (noise, breaths, bleed), for
   auditioning; intentional leveling gain is excluded by contract (a separate
   raw-vs-final "full difference" file covers that)
4. **Automation data** — the gain curves and event regions as exportable data (JSON/MIDI)

### 1a. Two input modes (one pipeline)

Serving both audiences means the separation stage is a *switch*, not a fixture:

- **Song mode** (vocalists/singers): full pipeline — separate the vocal from the mix,
  clean it, then either return the stem or remix it with the instrumental.
- **Voice mode** (talks, sermons, podcasts): the recording is already mostly voice, so
  separation is skipped — or optionally used to strip background music/bed from a talk
  recording, which is a killer feature for event recordings.

Everything downstream of Stage A (analysis + render) is identical in both modes. Only the
defaults differ: Song mode leans gentle on Gate/Breath (breaths are musical), Voice mode
leans harder on Gate, Dynamics, and Mouth-noise-style cleanup for spoken word.

**Design principle we keep from VoiceAssist: no black box.**
Every module's *analysis* pass produces human-readable, editable data (gain curves, breath
regions, sibilance regions, pause regions) *before* anything is rendered. The user can
inspect, adjust, or delete any decision the AI made, then render. This is what separates a
tool engineers trust from a one-click "enhance" button.

---

## 2. Pipeline architecture

Three strictly separated stages. This separation is the whole architecture.

### Stage A — Ingest & Separation
- Decode any input (mp3/wav/flac/m4a) → 44.1/48 kHz float32 WAV
- Stem separation: vocal vs. instrumental
  - Primary candidate: **Demucs (htdemucs_ft)** — MIT licensed, well-maintained, good quality
  - Stronger alternative: **BS-RoFormer / MDX23C models** via the `audio-separator` Python
    package — currently best-in-class separation; verify weight licenses per model
- Keep the instrumental untouched and phase-aligned so the remix is a clean sum

### Stage B — Analysis (produces the "Edit Document", renders nothing)
Each module analyzes the separated vocal and writes its decisions into one JSON document:

```json
{
  "gain_curve":      [[t, dB], ...],          // Dynamics
  "pauses":          [{"start", "end", "floor_db", "fade_ms"}],   // Gate
  "breaths":         [{"start", "end", "reduction_db"}],          // Breath
  "sibilants":       [{"start", "end", "reduction_db", "band"}],  // Sibilance
  "lowcut_hz":       [[t, hz], ...],          // Lowend (pitch-tracked)
  "resonances":      [{"hz", "q", "cut_db"}], // Lowend
  "denoise":         {"amount", "dereverb_amount"}                // Clean
}
```

This document is the UI's data model, the undo history, and the export format all at once.

### Stage C — Render (deterministic DSP, no ML)
Applies the Edit Document sample-accurately: gain automation, fades, per-region spectral
attenuation, filters. Re-running render with the same document is bit-identical —
that's what makes manual edits trustworthy.

---

## 3. The six modules — ours, with concrete tech choices

| Module | What it does | Candidate tech (all runnable locally) |
|---|---|---|
| **Clean** | Denoise + dereverb the separated vocal; removes separation bleed too | DeepFilterNet3 (MIT) for denoise; resemble-enhance or VoiceFixer for dereverb — needs evaluation on *singing*, not just speech |
| **Lowend** | Pitch-tracked low-cut, restore thin low end, notch boomy resonances | torchcrepe / librosa pyin for pitch → dynamic high-pass; long-term spectrum peak detection → dynamic notches |
| **Gate** | Mute the gaps between phrases without clipping word starts/ends | Silero VAD (MIT) for voice activity → pause regions with min-length + fade handles |
| **Dynamics** | Ride the vocal to a consistent loudness; editable gain curve | pyloudnorm / libebur128 for LUFS; short-term loudness → smoothed inverse gain curve; Speed / Smoothing / Target / Catch-Peaks params |
| **Breath** | Find breaths, turn them down naturally | v1: heuristic (VAD-negative regions + spectral flatness + energy profile); v2: small trained classifier |
| **Sibilance** | Tame harsh S/T/SH without dulling the vocal | 4–10 kHz band-energy onset detection → per-event spectral gain reduction (not a static de-esser) |

Notes:
- **Order matters**: Clean → Lowend → Gate → Breath → Sibilance → Dynamics (level last, so
  it rides the already-cleaned signal).
- The hard, differentiating problem is that **separated vocals are not studio vocals** —
  they carry separation artifacts and instrumental bleed. Our Clean module explicitly
  treats "separation residue" as a noise class. Nobody else does this; it's our moat.
- Music vocals ≠ dialogue. Models trained on speech (most denoisers) can mangle singing
  (vibrato, belts, harmonies). Every model choice above needs a singing-specific listening
  test before it's locked in.

---

## 4. Phased build plan

### Phase 0 — Proof of pipeline (Python CLI, ~1–2 weeks of work)
`pulsevocal process song.mp3` → separated + cleaned vocal, remix, delta.
- Wire Stage A end-to-end with Demucs
- Implement Dynamics (gain riding) + Gate (VAD) + a basic de-esser — the three cheapest,
  highest-payoff modules
- Pass-through Clean using DeepFilterNet as-is
- **Goal: prove the concept sounds good on 10 real songs before building any UI**

### Phase 0 audit (July 2026) — status vs. plan

Phase 0 shipped and exceeded scope after four real-song field tests:
- All planned modules except Lowend/dereverb, plus **unplanned** additions the
  field tests demanded: measured stem balancing, bounded mastering
  (−15 LUFS / −3 dBTP), BS.1770 measurement, speech-guard safety system,
  detector confidence, local gain ceiling + slope limiting. 71 tests.
- The "prove it on real songs first" gate was passed: three songs judged good,
  the fourth (quiet sparse vocal) drove three correction passes now locked in
  by regression tests.
- Decided sequence forward: **UI first, pitch correction second**, mute-region
  feature queued. Best input: studio recordings or clean stems (voice mode);
  song mode remains for full mixes.
- Still open: product name; Lowend module; dereverb.

### Phase 1 — The app (local web UI) — IN PROGRESS
- FastAPI (Python) backend serving sessions; render runs server-side with the
  same engine as the CLI — the browser never computes audio
- Browser UI: canvas waveform from precomputed peaks, module rail, gain-curve
  overlay, region editing (pauses/breaths/sibilants: inspect, delete)
- The UI reads/writes the Edit Document — render button applies it
- Ship as: local app first (`voxpolish ui recording.wav` → browser opens)

### Phase 1 disaster plan — the three ways this phase kills the product

**Disaster 1 — It loses Aaron's audio or work.** One overwritten master or
one lost editing session ends trust in a tool whose whole promise is safety.
Countermeasures, built in from the first commit: originals are never written —
the session folder gets a copy and all writes happen inside it; every file
write is atomic (temp file + rename, no half-written WAVs after a crash);
every render snapshots the prior edit document into `history/` (undo by file,
survives restarts).

**Disaster 2 — The editor lies.** If what the waveform shows ever diverges
from what render produces, the no-black-box promise is dead. Countermeasures:
the Edit Document on disk is the single source of truth — the UI holds no
private state, and every render re-reads the persisted document; documents are
validated by round-tripping through the schema before being accepted; writes
carry a revision number and stale writes are rejected (no lost-update
clobbering); render stays deterministic (already regression-tested), so
saved document ⇒ reproducible audio, always.

**Disaster 3 — Real sessions melt it.** A 45-minute sermon WAV shipped raw to
a browser tab, or a blocking render freezing the app, reads as "broken" even
when the engine is fine. Countermeasures: the browser never receives raw
audio for drawing — waveforms come from small precomputed peak files; audio
playback streams with HTTP range requests; renders run in a background worker
with a status endpoint and a single-flight lock (a second render request gets
a clean "busy", not a pile-up); session state is polled, never assumed.

(The fourth classic disaster — audio quality regression — is already covered
by the 71-test suite plus the Mary/A9Max field-test loop, and stays covered:
every UI feature goes through the same regression gate.)

### Phase 2 — Productize (decided: local-first)
Everything runs locally on the founder's Geekom A9 Max to start — the Phase 1 app
(local server + browser UI) IS the product for now. When it's time to share it:
- **Nearest step**: package as a desktop app (Tauri/Electron wrapping Phase 1) —
  local processing, no cloud costs; cross-platform (Windows/Linux/macOS) since the
  engine is plain Python + PyTorch CPU.
- **Later option**: hosted web service tied into the Vox Coaching site (upload → process →
  browser editor), if reach matters more than margins. Phase 1's architecture (HTTP API +
  browser UI) deliberately keeps this door open.

### Phase 3 — DAW plugin (only if the product earns it)
- A real ARA plugin (JUCE + ARA SDK, C++) is a 12–18 month effort and the reason
  VoiceAssist is impressive. Do **not** start here.
- Stepping stone: VoiceAssist's own "Transfer Mode" trick — a simple VST3/AU insert that
  captures audio during playback and hands it to our engine — gets us "in the DAW"
  for ~5% of ARA's engineering cost.

---

## 5. Risks & realities

1. **Separation quality is the ceiling.** If the stem split is bad, no downstream module
   saves it. Mitigate by supporting multiple separation models and letting users pick.
2. **Compute**: Demucs on CPU ≈ 1–3 min per song; seconds on GPU. Fine for an offline
   tool, dictates the hosted-vs-local decision economics.
3. **Speech-model bias**: denoisers/dereverbs are trained on speech; validate on singing early.
4. **Legal/brand**: we build *inspired by*, not a clone — original name, original UI,
   no reuse of NoiseWorks copy or assets. Verify the license of every model weight we
   ship (Demucs MIT ✓, DeepFilterNet ✓, Silero ✓; UVR community weights vary — check each).
5. **Scope creep**: VoiceAssist has 7 modules, 3 editions, 4 integration modes — built by a
   funded team over years. Phase 0 wins by doing *one* flow brilliantly: song in,
   better vocal out.

---

## 6. Remaining open decisions

1. **Name** (see §7 shortlist) — pick before Phase 1 UI work so branding is baked in.
2. **Python engine forever, or eventual C++ port** for the render stage (only matters if
   Phase 3 / plugin ambitions materialize).
3. **How this connects to Vox Coaching** — standalone tool, or a "cleanup" tab inside a
   future Vox analysis app? Affects Phase 1 packaging, not Phase 0.

---

## 7. Naming — shortlist under the Vox brand

The tool should read as part of the Vox Coaching family. Candidates (availability of
domains/trademarks unchecked — avoid anything close to "VoiceAssist"):

- **VoxPolish** — says exactly what it does; friendly for non-engineers
- **VoxClean** — plainest possible; strong for the podcast/talks audience
- **VoxRefine** — slightly more premium feel
- **VoxRestore** — leans into the repair/rescue angle (bad recordings saved)
- **VoxLab** — roomier umbrella if this later merges with the analysis/coaching tooling

Working recommendation: **VoxPolish** for the tool, keeping **VoxLab** in reserve as the
umbrella name if the coaching-analysis suite and this cleanup tool ever ship together.
