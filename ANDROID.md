# HOWARD VOX AI Android

This repo now has a Capacitor Android shell for the existing Vite app.

## Current execution modes

- Browser/dev default: `http`, using the existing `/analyze-song` backend.
- Native Android default: `android-local`, using the `VoxPipeline` Capacitor plugin.

The Android plugin creates app-private VOX jobs, stores the uploaded input, writes the same manifest shape used by the backend, and runs a native ONNX Runtime separation pass in the APK.

The upload call returns a queued manifest immediately. The app then polls `VoxPipeline.getJob` while the plugin updates the manifest:

- `job.status`: `queued` -> `processing` -> `completed` or `failed`
- `stages.ingest`: `completed`
- `stages.separate`: `pending` -> `processing` -> `completed` or `failed`
- `stages.analyze`: `pending` -> `processing` -> `completed` or `failed`
- `analysis.status`: `pending` -> `processing` -> `completed` or `failed`
- `separation.outputs.vocals`: written when native separation succeeds
- `separation.outputs.instrumental`: written when native separation succeeds
- `analysis.artifacts.pitch/rms/crest/report`: written when offline analysis succeeds

## Native ONNX model asset

Bundle the separation model at:

```text
android/app/src/main/assets/models/UVR_MDXNET_Main.onnx
```

The verified source model is `UVR-MDX-NET-Inst_HQ_5.onnx`; the APK stores it under `UVR_MDXNET_Main.onnx` because that is the stable asset name used by the native plugin.

Prepare the model with:

```bash
VOX_ANDROID_MODEL=/absolute/path/UVR-MDX-NET-Inst_HQ_5.onnx npm run android:prepare-model
```

The script verifies the audio-separator MD5-window hash before copying the model. Expected hash: `cb790d0c913647ced70fc6b38f5bea1a`.

The Gradle config keeps `.onnx` assets uncompressed so ONNX Runtime can load them reliably after the plugin copies the model into app-private storage.

The native plugin accepts browser-uploaded audio directly. WAV files use the local PCM parser; common compressed formats use Android `MediaExtractor`/`MediaCodec`, then resample to stereo 44.1 kHz before MDX separation.

The ONNX separator expects the UVR MDX spectrogram contract `[1, 4, 2560, 256]`. If the bundled model exposes another contract, the manifest fails truthfully with `UNSUPPORTED_MODEL_IO` instead of fabricating stems.

## Commands

```bash
npm run build
npm run lint
npm run android:doctor
npm run android:patch-capacitor
npm run android:prepare-model
npm run android:sync
```

Build a debug APK when Android SDK 34 is installed and `ANDROID_HOME` or `android/local.properties` is configured:

```bash
npm run android:debug
```

`npm run android:doctor` checks Java, the configured Android SDK path, the configured compile SDK platform, and SDK build-tools before Gradle starts. This fails early with a clear setup message instead of a late Gradle error.

On this ARM64 Android-hosted workspace, the Google SDK `aapt2` binary is x86-64. The project therefore uses Ubuntu's ARM64 `aapt2`, compiles against SDK 34, and runs `npm run android:patch-capacitor` to replace Capacitor's API 35 constant reference with the numeric SDK value `35`.

If you build from `android/local.properties`, use:

```properties
sdk.dir=/absolute/path/to/android-sdk
```

The APK output path is:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

## Runtime controls

The Android app can cancel an active local job from the UI. Cancellation marks the manifest as `cancelled`, stops polling, and prevents queued jobs from being overwritten back to `processing` when the native worker starts.

## Next native pipeline step

Validate the MDX output quality on a real device against the Python backend fixture, then tune chunk overlap/performance if needed.
