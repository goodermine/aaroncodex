# Sprint 1 Spectral Metrics Design Plan

## 1. Sprint 1 Overview

Goal: design safe tone/spectral metrics for a later implementation sprint without changing runtime code in this sprint.

Sprint 1 is plan-only. It does not implement spectral metrics and does not modify Java, JavaScript, CSS, separator logic, ONNX model, playback, reset, diagnostics, routing, report UI, or current metric calculations.

Proposed user-facing labels:

| User-facing label | Internal field |
| --- | --- |
| Tone brightness | `spectralCentroidMeanHz` |
| Noise-like texture estimate | `spectralFlatnessMeanDb` |
| Tone clarity estimate | `hprDb`, `hprLabel` |
| Upper tone energy | `spectralRolloff85MeanHz` |
| Advanced tone fingerprint | `mfccMeans` optional |
| Spectral confidence | `spectralAnalysisConfidence` |

Allowed `hprLabel` values: `tonal`, `mixed`, `textured-estimate`.

Mandatory user-facing safety copy:

> Spectral tone metrics are estimates based on the separated vocal stem. They are not a medical or vocal-health diagnosis.

Sprint 2 must add these metrics as a separate `Tone Metrics` data group first. Do not feed them into `issueScores`, `vocalProfile`, or coaching priorities until a later approved sprint.

## 2. Current Analysis Pipeline Map

Current Android flow:

1. `VoxPipelinePlugin` owns the Android local job lifecycle.
2. Native separation completes first and produces stem files, including `vocals.wav`.
3. After separation, `VoxPipelinePlugin` builds an `analyze` progress manifest and calls:

```text
new VoxAnalysisEngine().analyze(result.vocalsFile, analysisDir, buildAnalysisContext(...), progressSink)
```

4. `VoxAnalysisEngine.analyze(...)` reads `vocals.wav` with `WavAudio.readPcmWav(...)`.
5. It converts the stem to mono, frames it with current constants:
   - `FRAME_SIZE = 4096`
   - `HOP_SIZE = 1024`
6. It currently computes:
   - RMS frames
   - peak amplitude
   - crest factor
   - autocorrelation pitch estimate
   - phrase metrics from RMS frames
   - pitch stability metrics from pitch frames
   - robust dynamic range from active RMS frames
7. It writes:
   - `analysis/pitch.json`
   - `analysis/rms.json`
   - `analysis/crest.json`
   - `analysis/coach-input.json`
   - `analysis/analysis-report.json`
8. `VoxAnalysisEngine.buildAnalysis(...)` inserts the result into the manifest `analysis` object.
9. `src/lib/api/voxClient.js` normalizes the manifest, generates/caches `coachOutput`, and persists coach artifacts back through `VoxPipeline.saveCoachArtifacts(...)`.

Current pitch approach:

- Pitch is estimated with normalized autocorrelation over lag range.
- It is not YIN, pYIN, or a target-melody tuning analyser.
- Existing pitch data remains suitable only for cautious pitch-centre and pitch-movement feedback.

Current frequency-domain status:

- No STFT or spectral tone analysis is currently computed on `vocals.wav`.
- Sprint 2 should add spectral analysis only inside the existing offline analysis stage, after the vocal stem is available.

Recommended Sprint 2 integration point:

- Add `SpectralAnalyser.java`.
- Call it from `VoxAnalysisEngine.analyze(...)` after `WavAudio.readPcmWav(...)` and mono conversion, before `rawMetrics`, `derivedMetrics`, `coachInput`, and `analysis-report.json` are finalized.
- Do not call it from `AndroidOnnxSeparator`.
- Do not alter separator, ONNX inference, chunking, WAV writing, playback, reset, diagnostics, or report routing.

## 3. `SpectralAnalyser.java` Design

Class location for Sprint 2:

```text
android/app/src/main/java/com/howardvox/ai/SpectralAnalyser.java
```

Input:

- `float[] mono`
- `int sampleRate`
- `double durationSeconds`
- Optional context: separation quality/status if already available

Reasoning:

- The current analysis engine already reads `vocals.wav` and converts it to mono.
- Passing mono samples avoids re-reading the WAV file and avoids coupling spectral analysis to file I/O.
- Use the actual sample rate from `WavAudio.AudioBuffer`; do not assume 22050 Hz.

Output object:

```text
SpectralFeatures
```

Fields:

- `Double spectralCentroidMeanHz`
- `Double spectralFlatnessMeanDb`
- `Double spectralRolloff85MeanHz`
- `Double hprDb`
- `String hprLabel`
- `String spectralAnalysisConfidence`
- `double[] mfccMeans` optional, nullable
- `int spectralFrameCount`
- `String spectralScope`, fixed to `separated_vocal_stem`

If duration is under 2 seconds, Sprint 2 should return null metric values and `spectralAnalysisConfidence = "low"`.

## 4. STFT Approach

Use a pure Java STFT implementation.

Parameters:

- `nFft = 2048`
- `hopLength = 512`
- Window: Hann
- Frequency bins: `nFft / 2 + 1`
- Output shape: `frequencyBins x frameCount`

Frame processing:

1. Slice mono samples into overlapping frames.
2. Zero-pad the final frame if needed.
3. Apply Hann window:
   - `w[n] = 0.5 - 0.5 * cos(2*pi*n/(nFft - 1))`
4. Compute magnitude spectrum for bins `0..nFft/2`.
5. Store or stream per-frame magnitudes.

Implementation note:

- For Sprint 2, a direct DFT is acceptable for this limited offline analyser if performance is acceptable on Android test clips.
- If direct DFT is too slow, implement an in-class radix-2 FFT for `nFft = 2048`.
- Do not add heavy external DSP dependencies unless Sprint 2 testing proves pure Java is not viable.

Numerical stability:

- Use `epsilon = 1e-12` when dividing or taking logs.
- Skip frames whose total spectral energy is below a small silence floor.
- Track valid spectral frame count separately from total frame count.

## 5. Metric Formulas

### `spectralCentroidMeanHz`

User label: Tone brightness.

Per frame:

```text
centroidHz = sum(freqHz[k] * magnitude[k]) / sum(magnitude[k])
```

Final value:

```text
mean(validFrameCentroids)
```

Interpretation bounds for later UI copy:

- Lower estimate: darker tone estimate
- Middle estimate: balanced tone brightness
- Higher estimate: brighter tone estimate

No placement, larynx, or resonance diagnosis is allowed.

### `spectralFlatnessMeanDb`

User label: Noise-like texture estimate.

Per frame:

```text
flatness = geometricMean(power[k] + epsilon) / arithmeticMean(power[k] + epsilon)
flatnessDb = 10 * log10(flatness + epsilon)
```

Use log-sum for the geometric mean:

```text
geometricMean = exp(mean(log(power[k] + epsilon)))
```

Final value:

```text
mean(validFrameFlatnessDb)
```

Safe interpretation:

- More tonal
- Mixed tone/noise-like texture estimate
- More textured estimate

Do not call this breath analysis.

### `spectralRolloff85MeanHz`

User label: Upper tone energy.

Per frame:

1. Compute total spectral energy.
2. Walk bins from low to high.
3. Find the first bin where cumulative energy reaches 85% of total.
4. Convert that bin to Hz.

Final value:

```text
mean(validFrameRolloffHz)
```

Safe interpretation:

- Lower upper-tone energy estimate
- Moderate upper-tone energy estimate
- Higher upper-tone energy estimate

Do not infer resonance, placement, diction, or vocal health.

### `hprDb`

User label: Tone clarity estimate.

Sprint 2 should use a lightweight HPSS-style estimate from the magnitude spectrogram:

- Harmonic estimate: median filter along the time axis, kernel size `31`.
- Percussive/noise-like estimate: median filter along the frequency axis, kernel size `31`.
- Compare total harmonic-like and percussive/noise-like energy:

```text
hprDb = 10 * log10((sum(harmonic^2) + epsilon) / (sum(percussive^2) + epsilon))
```

Clamp:

```text
[-20, 40] dB
```

Label thresholds:

- `tonal`: `hprDb > 10`
- `mixed`: `0 <= hprDb <= 10`
- `textured-estimate`: `hprDb < 0`

Safe wording:

- Tone clarity estimate: tonal
- Tone clarity estimate: mixed
- Tone clarity estimate: textured estimate
- Based on the separated vocal stem

Do not use this metric to diagnose breath, strain, vocal fold behavior, or health.

### Optional `mfccMeans`

User label: Advanced tone fingerprint.

Sprint 2 may defer this field if implementation time is better spent validating the main four metrics.

If implemented:

1. Build mel filterbank, recommended `128` mel bands.
2. Apply mel filters to power spectrum.
3. Log-compress mel energies.
4. Apply DCT.
5. Keep first `13` coefficients.
6. Average each coefficient across valid frames.

User-facing display should keep MFCCs in Advanced Metrics only.

## 6. JSON Fields To Add Later

Add a nested `spectralMetrics` object rather than scattering fields across unrelated sections.

Recommended shape:

```json
{
  "spectralMetrics": {
    "spectralCentroidMeanHz": 0,
    "spectralFlatnessMeanDb": 0,
    "spectralRolloff85MeanHz": 0,
    "hprDb": 0,
    "hprLabel": "tonal",
    "spectralAnalysisConfidence": "high",
    "mfccMeans": null,
    "spectralFrameCount": 0,
    "spectralScope": "separated_vocal_stem"
  }
}
```

Sprint 2 should place this object in:

- `metrics.spectralMetrics`
- `rawMetrics.spectralMetrics`
- top-level `analysis.spectralMetrics`
- `coachInput.spectralMetrics`

Optional artifact:

- `analysis/spectral.json`
- `analysis.artifacts.spectral`

Do not add spectral metrics to `issueScores` or `vocalProfile` until a later approved sprint.

## 7. Coaching Language Rules

Allowed labels:

- Tone brightness
- Noise-like texture estimate
- Tone clarity estimate
- Upper tone energy
- Advanced tone fingerprint

Allowed support phrases:

- Based on the separated vocal stem
- Estimate
- Metric-based coaching
- Not a medical or vocal-health diagnosis
- Tone reads darker/brighter
- More tonal
- Mixed
- Textured estimate

Forbidden claims:

- Breath support
- Breath noise
- Vocal strain
- Resonance diagnosis
- Larynx position
- Diction quality
- Tuning accuracy
- True vocal range
- Medical or vocal-health diagnosis

Forbidden value rule:

- Do not use the retired unsafe HPR label that implies breath detection. The only allowed `hprLabel` values are `tonal`, `mixed`, and `textured-estimate`.

Example safe copy:

- "Tone brightness estimate: slightly brighter than average for this take."
- "Noise-like texture estimate: mixed. Based on the separated vocal stem."
- "Tone clarity estimate: tonal. This is not a medical or vocal-health diagnosis."
- "Upper tone energy estimate: moderate."

Unsafe copy pattern:

- Any wording that presents spectral metrics as evidence of unsupported physiological, medical, diction, tuning, or range conclusions is forbidden.

Sprint 2 UI placement:

- Add a separate Tone Metrics section only.
- Keep MFCCs and raw spectral frame counts under Advanced Metrics.
- Keep the mandatory disclaimer visible wherever tone metrics are summarized.

## 8. Validation Rules

Sprint 2 implementation should enforce:

- If `durationSeconds < 2`, set spectral metric values to null and `spectralAnalysisConfidence = "low"`.
- `spectralCentroidMeanHz` must be within `[50, 12000]`; otherwise set it to null and lower confidence.
- `spectralFlatnessMeanDb` must be within `[-60, 0]`; otherwise set it to null and lower confidence.
- `spectralRolloff85MeanHz` must be within `[50, sampleRate / 2]`; otherwise set it to null and lower confidence.
- `hprDb` must be clamped to `[-20, 40]`.
- `hprLabel` must be exactly one of `tonal`, `mixed`, `textured-estimate`.
- `spectralAnalysisConfidence` must be exactly one of `high`, `medium`, `low`.
- `spectralScope` must be `separated_vocal_stem`.
- No `NaN`, `Infinity`, or `-Infinity` values may be written to JSON.

Suggested confidence rules:

- `high`: duration over 5 seconds, enough valid non-silent spectral frames, vocal stem present.
- `medium`: duration 2 to 5 seconds or limited valid frames.
- `low`: duration under 2 seconds, too few valid frames, invalid values, or failed spectral calculation.

Failure handling:

- Spectral analyser failure must not fail the whole job if separation and existing offline analysis succeeded.
- If spectral analysis fails, write null spectral fields, low confidence, and a warning.
- Do not fabricate tone metrics.

## 9. Test Fixture Plan

### Java Unit Fixtures

Add Android/JUnit tests in Sprint 2 for `SpectralAnalyser`.

Synthetic inputs:

1. `440 Hz sine wave`
   - Expected centroid near `440 Hz`, allowing tolerance for windowing.
   - Expected flatness low, closer to tonal than noise-like.
   - Expected HPR label `tonal`.
   - Expected rolloff near the sine energy region, not near Nyquist.

2. `White noise`
   - Expected flatness closer to `0 dB` than sine.
   - Expected wider/high rolloff.
   - Expected HPR label likely `textured-estimate` or `mixed`.

3. `Silence`
   - Expected null spectral fields or low confidence.
   - No NaN values.

4. `Short clip under 2 seconds`
   - Expected null metric values.
   - Expected `spectralAnalysisConfidence = "low"`.

### Integration Fixture

After Sprint 2 wiring, run one Android local analysis and confirm:

- `analysis.spectralMetrics` exists.
- `analysis.rawMetrics.spectralMetrics` exists.
- `analysis.coachInput.spectralMetrics` exists.
- `hprLabel` is one of `tonal`, `mixed`, `textured-estimate`.
- Values are finite or null.
- Existing pitch/RMS/phrase/coach fields still exist.
- No separator or ONNX behavior changed.

### Coach Fixture Updates

Add spectral fixture variants later:

- `tone-bright.json`
- `tone-dark.json`
- `tone-textured.json`
- `tone-tonal.json`
- `tone-low-confidence.json`

Each fixture should verify:

- Safe labels only.
- Mandatory disclaimer appears.
- No forbidden claims appear.
- Spectral metrics remain separate from Top Issues unless a later sprint explicitly approves integration.

## 10. Sprint 2 Verification Commands

Sprint 2 implementation must run:

```bash
npm run lint
npm run build
node scripts/test-coach-writer.mjs
npm run android:debug
cd android && ./gradlew :app:compileDebugJavaWithJavac
```

Additional Sprint 2 checks:

```bash
cd android && ./gradlew testDebugUnitTest
```

Manual phone test:

1. Analyse a short clip.
2. Analyse a full song.
3. Confirm existing separation still produces `vocals.wav` and `instrumental.wav`.
4. Confirm existing pitch/RMS/phrase report still appears.
5. Confirm Tone Metrics section appears only when spectral values are available.
6. Confirm low-confidence/null state is truthful when data is insufficient.
7. Confirm no forbidden claims appear.

## 11. Approval Gate

Sprint 2 must not begin until Aaron reviews and approves this Sprint 1 plan.

No Java or JavaScript implementation code for spectral metrics may be written until approval is confirmed.

Sprint 1 deliverable is this document only.
