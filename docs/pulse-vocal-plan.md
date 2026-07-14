# PulseVocal — Product & Engineering Plan

*Working title. An AI vocal cleanup tool inspired by NoiseWorks VoiceAssist, with one big
differentiator: you feed it a **full song**, not a pre-isolated voice track.*

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
3. **Delta** — audio of everything that was removed (noise, breaths, bleed), for auditioning
4. **Automation data** — the gain curves and event regions as exportable data (JSON/MIDI)

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

### Phase 1 — The app (local web UI)
- FastAPI (Python) backend running the pipeline; job queue for long renders
- Browser UI: waveform display (peaks.js / wavesurfer.js), the six-module left rail,
  the editable gain curve overlay, region editing (drag boundaries, X to delete, + to add)
- The UI reads/writes the Edit Document — render button applies it
- Ship as: local app first (runs on the user's machine, GPU if available)

### Phase 2 — Productize (pick one lane)
- **Option A — Hosted web service**: users upload a song, GPU server processes, browser
  editor for tweaks. Easiest distribution, recurring revenue, but hosting GPU costs and
  upload friction.
- **Option B — Desktop app** (Tauri/Electron wrapping Phase 1): one-time purchase like
  VoiceAssist ($49–299 tiering worked for them), local processing, no cloud costs.
- Recommendation: **A for reach, B for margins** — Phase 1's architecture (HTTP API +
  browser UI) deliberately keeps both doors open.

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

## 6. Open decisions (to discuss)

1. **Who is the first user?** Musicians cleaning their own recorded vocals inside a rough
   mix? Cover/remix creators extracting vocals? Podcasters with music beds? This picks the
   defaults and the marketing.
2. **Local vs. hosted** processing (Phase 2 fork).
3. **Name** — "PulseVocal" ties into the existing Pulse branding in this repo; open to better.
4. **Python engine forever, or eventual C++ port** for the render stage (only matters if
   Phase 3 happens).
