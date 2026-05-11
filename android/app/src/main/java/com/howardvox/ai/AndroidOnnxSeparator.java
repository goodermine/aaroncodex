package com.howardvox.ai;

import android.app.ActivityManager;
import android.content.Context;
import android.content.res.AssetManager;
import android.os.Debug;
import android.util.Log;

import ai.onnxruntime.NodeInfo;
import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OnnxValue;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;
import ai.onnxruntime.TensorInfo;

import com.getcapacitor.JSObject;

import org.jtransforms.fft.FloatFFT_1D;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Arrays;
import java.util.Collections;
import java.util.Map;

class AndroidOnnxSeparator {
    private static final String TAG = "AndroidOnnxSeparator";
    static final int SAMPLE_RATE = 44_100;
    static final int N_FFT = 5_120;
    static final int HOP_LENGTH = 1_024;
    static final int DIM_F = 2_560;
    static final int SEGMENT_SIZE = 256;
    static final float OVERLAP = 0.25f;
    static final float COMPENSATE = 1.010f;
    private static final long CHUNK_STALL_TIMEOUT_MS = 90_000L;

    private static final int TRIM = N_FFT / 2;
    private static final int CHUNK_SIZE = HOP_LENGTH * (SEGMENT_SIZE - 1);
    private static final int GEN_SIZE = CHUNK_SIZE - (2 * TRIM);
    private static final String MODEL_ASSET_PATH = "models/UVR_MDXNET_Main.onnx";
    private static final String MODEL_FILENAME = "UVR_MDXNET_Main.onnx";
    private static final String MODEL_DISPLAY_NAME = "UVR-MDX-NET-Inst_HQ_5.onnx";

    static class Result {
        final File vocalsFile;
        final File instrumentalFile;
        final int sampleRate;
        final int channels;
        final int frameCount;
        final String engineVersion;
        final String modelInputSummary;
        final String modelOutputSummary;
        final float peak;
        final long modelLoadMs;
        final long separateMs;

        Result(
            File vocalsFile,
            File instrumentalFile,
            int sampleRate,
            int channels,
            int frameCount,
            String engineVersion,
            String modelInputSummary,
            String modelOutputSummary,
            float peak,
            long modelLoadMs,
            long separateMs
        ) {
            this.vocalsFile = vocalsFile;
            this.instrumentalFile = instrumentalFile;
            this.sampleRate = sampleRate;
            this.channels = channels;
            this.frameCount = frameCount;
            this.engineVersion = engineVersion;
            this.modelInputSummary = modelInputSummary;
            this.modelOutputSummary = modelOutputSummary;
            this.peak = peak;
            this.modelLoadMs = modelLoadMs;
            this.separateMs = separateMs;
        }

        float durationSec() {
            return sampleRate > 0 ? (float) frameCount / (float) sampleRate : 0f;
        }
    }

    interface CancelSignal {
        boolean isCancelled();
    }

    interface ProgressSink {
        void onProgress(int percent, String stage, String message, JSObject detail);
    }

    interface PhaseSink {
        void onPhase(String phase, int chunkIndex, int totalChunks);
    }

    static class SeparationPlan {
        final long sourceFrames;
        final long mixtureFrames;
        final int chunkSizeFrames;
        final int stepFrames;
        final long chunkCount;
        final long decodedPcmEstimateBytes;
        final long estimatedSeparatorPeakMemoryBytes;
        final long streamingPeakEstimateBytes;
        final long minimumChunkWorkingBytes;

        SeparationPlan(
            long sourceFrames,
            long mixtureFrames,
            int chunkSizeFrames,
            int stepFrames,
            long chunkCount,
            long decodedPcmEstimateBytes,
            long estimatedSeparatorPeakMemoryBytes,
            long streamingPeakEstimateBytes,
            long minimumChunkWorkingBytes
        ) {
            this.sourceFrames = sourceFrames;
            this.mixtureFrames = mixtureFrames;
            this.chunkSizeFrames = chunkSizeFrames;
            this.stepFrames = stepFrames;
            this.chunkCount = chunkCount;
            this.decodedPcmEstimateBytes = decodedPcmEstimateBytes;
            this.estimatedSeparatorPeakMemoryBytes = estimatedSeparatorPeakMemoryBytes;
            this.streamingPeakEstimateBytes = streamingPeakEstimateBytes;
            this.minimumChunkWorkingBytes = minimumChunkWorkingBytes;
        }
    }

    static SeparationPlan estimatePlan(long durationMs) {
        long sourceFrames = durationMs > 0L ? Math.max(1L, Math.round((durationMs / 1000d) * SAMPLE_RATE)) : -1L;
        long pad = sourceFrames > 0L ? GEN_SIZE + TRIM - (sourceFrames % GEN_SIZE) : -1L;
        long mixtureFrames = sourceFrames > 0L ? TRIM + sourceFrames + pad : -1L;
        int step = Math.max(1, (int) ((1f - OVERLAP) * CHUNK_SIZE));
        long chunkCount = mixtureFrames > 0L ? Math.max(1L, (mixtureFrames + step - 1L) / step) : -1L;
        long decodedPcmBytes = sourceFrames > 0L ? stereoFloatBytes(sourceFrames) : -1L;
        long paddedStereoBytes = mixtureFrames > 0L ? stereoFloatBytes(mixtureFrames) : -1L;
        long spectrumBytes = 1L * 4L * DIM_F * SEGMENT_SIZE * Float.BYTES;
        long chunkAudioBytes = stereoFloatBytes(CHUNK_SIZE);
        long istftPaddedFrames = ((SEGMENT_SIZE - 1L) * HOP_LENGTH) + N_FFT;
        long istftBytes = stereoFloatBytes(istftPaddedFrames) + (istftPaddedFrames * Float.BYTES);
        long minimumChunkWorkingBytes = (spectrumBytes * 2L) + (chunkAudioBytes * 2L) + istftBytes;
        long estimatedPeakBytes = decodedPcmBytes > 0L && paddedStereoBytes > 0L
            ? (decodedPcmBytes * 4L) + (paddedStereoBytes * 3L) + minimumChunkWorkingBytes
            : -1L;
        long streamingPeakBytes = decodedPcmBytes > 0L
            ? decodedPcmBytes + stereoFloatBytes(CHUNK_SIZE * 3L) + minimumChunkWorkingBytes
            : -1L;

        return new SeparationPlan(
            sourceFrames,
            mixtureFrames,
            CHUNK_SIZE,
            step,
            chunkCount,
            decodedPcmBytes,
            estimatedPeakBytes,
            streamingPeakBytes,
            minimumChunkWorkingBytes
        );
    }

    private final Context context;
    private final AndroidAudioDecoder audioDecoder = new AndroidAudioDecoder();
    private final FloatFFT_1D fft = new FloatFFT_1D(N_FFT);
    private final float[] stftWindow = hann(N_FFT);

    AndroidOnnxSeparator(Context context) {
        this.context = context;
    }

    Result separate(
        File inputFile,
        String mimeType,
        File stemsDir,
        CancelSignal cancelSignal,
        ProgressSink progressSink,
        PhaseSink phaseSink
    ) throws IOException, VoxSeparationException {
        throwIfCancelled(cancelSignal);
        emit(progressSink, 2, "model", "Preparing bundled ONNX model");
        long loadStart = System.currentTimeMillis();
        File modelFile = copyModelAsset();
        throwIfCancelled(cancelSignal);
        emit(progressSink, 7, "decode", "Decoding source audio");
        WavAudio.AudioBuffer decoded = audioDecoder.decodeToStereo(inputFile, mimeType, SAMPLE_RATE, cancelSignal);
        throwIfCancelled(cancelSignal);

        try {
            OrtEnvironment environment = OrtEnvironment.getEnvironment();
            emit(progressSink, 12, "model", "Loading ONNX Runtime session");
            try (OrtSession.SessionOptions options = new OrtSession.SessionOptions();
                 OrtSession session = environment.createSession(modelFile.getAbsolutePath(), options)) {
                long modelLoadMs = System.currentTimeMillis() - loadStart;
                String inputName = firstKey(session.getInputInfo());
                String outputName = firstKey(session.getOutputInfo());
                TensorInfo inputInfo = tensorInfo(session.getInputInfo().get(inputName));
                TensorInfo outputInfo = tensorInfo(session.getOutputInfo().get(outputName));

                validateMdxIo(inputInfo, outputInfo, session);

                long separateStart = System.currentTimeMillis();
                emit(progressSink, 15, "separate", "Starting native vocal separation");
                File vocalsFile = new File(stemsDir, "vocals.wav");
                File instrumentalFile = new File(stemsDir, "instrumental.wav");
                float peak = normalizeInPlace(decoded.channels);
                demixToStemFiles(
                    environment,
                    session,
                    inputName,
                    decoded.channels,
                    decoded.frameCount,
                    decoded.sampleRate,
                    peak,
                    vocalsFile,
                    instrumentalFile,
                    cancelSignal,
                    progressSink,
                    phaseSink
                );
                throwIfCancelled(cancelSignal);
                emit(progressSink, 88, "separate", "Stem files written");

                return new Result(
                    vocalsFile,
                    instrumentalFile,
                    decoded.sampleRate,
                    2,
                    decoded.frameCount,
                    environment.getVersion(),
                    summarize(session.getInputInfo()),
                    summarize(session.getOutputInfo()),
                    peak,
                    modelLoadMs,
                    System.currentTimeMillis() - separateStart
                );
            }
        } catch (OrtException error) {
            throw new VoxSeparationException("ONNX_INFERENCE_FAILED", "ONNX Runtime failed during native MDX separation.", error.getMessage());
        }
    }

    private void validateMdxIo(TensorInfo inputInfo, TensorInfo outputInfo, OrtSession session) throws VoxSeparationException, OrtException {
        if (inputInfo == null || outputInfo == null) {
            throw new VoxSeparationException("UNSUPPORTED_MODEL_IO", "The ONNX model must expose tensor input and output metadata.");
        }

        long[] inputShape = inputInfo.getShape();
        long[] outputShape = outputInfo.getShape();
        if (!isMdxShape(inputShape) || !isMdxShape(outputShape)) {
            throw new VoxSeparationException(
                "UNSUPPORTED_MODEL_IO",
                "The bundled ONNX model is not the expected UVR MDX spectrogram separator.",
                "expected=[1,4,2560,256]; input=" + summarize(session.getInputInfo()) + "; output=" + summarize(session.getOutputInfo())
            );
        }
    }

    private boolean isMdxShape(long[] shape) {
        return shape != null
            && shape.length == 4
            && (shape[0] == 1 || shape[0] < 0)
            && shape[1] == 4
            && shape[2] == DIM_F
            && shape[3] == SEGMENT_SIZE;
    }

    private void demixToStemFiles(
        OrtEnvironment environment,
        OrtSession session,
        String inputName,
        float[][] normalizedSource,
        int sourceFrames,
        int sampleRate,
        float peak,
        File vocalsFile,
        File instrumentalFile,
        CancelSignal cancelSignal,
        ProgressSink progressSink,
        PhaseSink phaseSink
    ) throws OrtException, VoxSeparationException, IOException {
        int pad = GEN_SIZE + TRIM - (sourceFrames % GEN_SIZE);
        int mixtureFrames = TRIM + sourceFrames + pad;
        int step = Math.max(1, (int) ((1f - OVERLAP) * CHUNK_SIZE));
        int totalChunks = Math.max(1, (mixtureFrames + step - 1) / step);
        int chunkIndex = 0;
        RollingStemAccumulator accumulator = new RollingStemAccumulator(
            normalizedSource,
            sourceFrames,
            peak,
            CHUNK_SIZE + step + 1,
            sampleRate,
            vocalsFile,
            instrumentalFile
        );
        float[][] chunk = new float[2][CHUNK_SIZE];
        float[] fullOverlapWindow = OVERLAP == 0f ? null : hann(CHUNK_SIZE);
        long separationStartedAtMs = System.currentTimeMillis();
        long completedChunkElapsedMs = 0L;
        long[] recentChunkElapsedMs = new long[5];
        int recentChunkCursor = 0;
        int recentChunkCount = 0;

        try {
            for (int start = 0; start < mixtureFrames; start += step) {
                throwIfCancelled(cancelSignal);
                int activeChunk = chunkIndex + 1;
                emitPhase(phaseSink, "chunk_start", activeChunk, totalChunks);
                long chunkCycleStartMs = System.currentTimeMillis();
                int end = Math.min(start + CHUNK_SIZE, mixtureFrames);
                int actualSize = end - start;
                emitPhase(phaseSink, "preparing_onnx_input", activeChunk, totalChunks);
                fillChunk(normalizedSource, sourceFrames, start, actualSize, chunk);

                long onnxStartMs = System.currentTimeMillis();
                float[][] prediction = runMdxChunk(environment, session, inputName, chunk, phaseSink, activeChunk, totalChunks);
                long onnxElapsedMs = System.currentTimeMillis() - onnxStartMs;
                if (onnxElapsedMs > CHUNK_STALL_TIMEOUT_MS) {
                    throw new VoxSeparationException(
                        "ANDROID_LOCAL_SEPARATOR_STALLED",
                        "Android local separator stalled while processing a vocal separation chunk.",
                        "phase=onnx; chunk=" + (chunkIndex + 1) + "/" + totalChunks + "; elapsedMs=" + onnxElapsedMs
                    );
                }

                long overlapStartMs = System.currentTimeMillis();
                emitPhase(phaseSink, "overlap_add_start", activeChunk, totalChunks);
                float[] overlapWindow = OVERLAP == 0f
                    ? null
                    : (actualSize == CHUNK_SIZE ? fullOverlapWindow : hann(actualSize));
                for (int channel = 0; channel < 2; channel++) {
                    for (int frame = 0; frame < actualSize; frame++) {
                        float weight = overlapWindow == null ? 1f : overlapWindow[frame];
                        accumulator.add(channel, start + frame, prediction[channel][frame], weight);
                    }
                }
                emitPhase(phaseSink, "overlap_add_complete", activeChunk, totalChunks);
                long overlapElapsedMs = System.currentTimeMillis() - overlapStartMs;

                chunkIndex++;
                int percent = 15 + Math.round(((float) chunkIndex / (float) totalChunks) * 65f);
                int nextStart = Math.min(mixtureFrames, start + step);
                long flushStartMs = System.currentTimeMillis();
                emitPhase(phaseSink, "wav_flush_start", chunkIndex, totalChunks);
                accumulator.flushUntil(nextStart);
                emitPhase(phaseSink, "wav_flush_complete", chunkIndex, totalChunks);
                long flushElapsedMs = System.currentTimeMillis() - flushStartMs;
                long chunkTotalElapsedMs = System.currentTimeMillis() - chunkCycleStartMs;
                completedChunkElapsedMs += chunkTotalElapsedMs;
                recentChunkElapsedMs[recentChunkCursor] = chunkTotalElapsedMs;
                recentChunkCursor = (recentChunkCursor + 1) % recentChunkElapsedMs.length;
                recentChunkCount = Math.min(recentChunkCount + 1, recentChunkElapsedMs.length);
                if (chunkTotalElapsedMs > CHUNK_STALL_TIMEOUT_MS) {
                    throw new VoxSeparationException(
                        "ANDROID_LOCAL_SEPARATOR_STALLED",
                        "Android local separator stalled while processing a vocal separation chunk.",
                        "phase=" + slowestPhase(onnxElapsedMs, overlapElapsedMs, flushElapsedMs)
                            + "; chunk=" + chunkIndex + "/" + totalChunks
                            + "; totalElapsedMs=" + chunkTotalElapsedMs
                            + "; onnxElapsedMs=" + onnxElapsedMs
                            + "; overlapElapsedMs=" + overlapElapsedMs
                            + "; flushElapsedMs=" + flushElapsedMs
                    );
                }

                JSObject detail = buildChunkProgressDetail(
                    chunkIndex,
                    totalChunks,
                    onnxElapsedMs,
                    overlapElapsedMs,
                    flushElapsedMs,
                    chunkTotalElapsedMs,
                    accumulator.frameCount(),
                    separationStartedAtMs,
                    completedChunkElapsedMs,
                    recentChunkElapsedMs,
                    recentChunkCount
                );
                long progressStartMs = System.currentTimeMillis();
                emitPhase(phaseSink, "manifest_write_start", chunkIndex, totalChunks);
                emit(progressSink, percent, "separate", "Separating vocals chunk " + chunkIndex + " of " + totalChunks, detail);
                emitPhase(phaseSink, "manifest_write_complete", chunkIndex, totalChunks);
                emitPhase(phaseSink, "chunk_complete", chunkIndex, totalChunks);
                long progressElapsedMs = System.currentTimeMillis() - progressStartMs;
                Log.i(
                    TAG,
                    "Separated chunk " + chunkIndex + "/" + totalChunks
                        + " onnx=" + onnxElapsedMs + "ms"
                        + " overlap=" + overlapElapsedMs + "ms"
                        + " flush=" + flushElapsedMs + "ms"
                        + " progress=" + progressElapsedMs + "ms"
                );
            }

            emitPhase(phaseSink, "wav_flush_start", totalChunks, totalChunks);
            accumulator.flushUntil(mixtureFrames);
            emitPhase(phaseSink, "wav_flush_complete", totalChunks, totalChunks);
            accumulator.close();
        } catch (IOException | OrtException | VoxSeparationException | RuntimeException error) {
            accumulator.abort();
            throw error;
        }
    }

    private void fillChunk(float[][] source, int sourceFrames, int start, int actualSize, float[][] chunk) {
        for (int channel = 0; channel < 2; channel++) {
            for (int frame = 0; frame < CHUNK_SIZE; frame++) {
                if (frame >= actualSize) {
                    chunk[channel][frame] = 0f;
                    continue;
                }
                int sourceIndex = start + frame - TRIM;
                chunk[channel][frame] = sourceIndex >= 0 && sourceIndex < sourceFrames
                    ? source[channel][sourceIndex]
                    : 0f;
            }
        }
    }

    private void throwIfCancelled(CancelSignal cancelSignal) throws VoxSeparationException {
        if (cancelSignal != null && cancelSignal.isCancelled()) {
            throw new VoxSeparationException("JOB_CANCELLED", "Android local VOX job was cancelled.");
        }
    }

    private void emit(ProgressSink progressSink, int percent, String stage, String message) {
        emit(progressSink, percent, stage, message, null);
    }

    private void emit(ProgressSink progressSink, int percent, String stage, String message, JSObject detail) {
        if (progressSink != null) {
            progressSink.onProgress(percent, stage, message, detail);
        }
    }

    private void emitPhase(PhaseSink phaseSink, String phase, int chunkIndex, int totalChunks) {
        if (phaseSink != null) {
            phaseSink.onPhase(phase, chunkIndex, totalChunks);
        }
    }

    private float[][] runMdxChunk(
        OrtEnvironment environment,
        OrtSession session,
        String inputName,
        float[][] chunk,
        PhaseSink phaseSink,
        int chunkIndex,
        int totalChunks
    ) throws OrtException, VoxSeparationException {
        float[][][][] spectrum = stft(chunk);
        for (int plane = 0; plane < 4; plane++) {
            for (int freq = 0; freq < 3; freq++) {
                for (int time = 0; time < SEGMENT_SIZE; time++) {
                    spectrum[0][plane][freq][time] = 0f;
                }
            }
        }

        emitPhase(phaseSink, "onnx_run_start", chunkIndex, totalChunks);
        try (OnnxTensor tensor = OnnxTensor.createTensor(environment, spectrum);
             OrtSession.Result result = session.run(Collections.singletonMap(inputName, tensor))) {
            emitPhase(phaseSink, "onnx_run_complete", chunkIndex, totalChunks);
            emitPhase(phaseSink, "output_copy_start", chunkIndex, totalChunks);
            OnnxValue output = result.get(0);
            Object value = output.getValue();
            if (!(value instanceof float[][][][])) {
                throw new VoxSeparationException("UNSUPPORTED_MODEL_IO", "UVR MDX model output must be a rank-4 float tensor.");
            }
            float[][] prediction = istft((float[][][][]) value, CHUNK_SIZE);
            emitPhase(phaseSink, "output_copy_complete", chunkIndex, totalChunks);
            return prediction;
        }
    }

    private float[][][][] stft(float[][] audio) {
        float[][][][] spectrum = new float[1][4][DIM_F][SEGMENT_SIZE];
        for (int channel = 0; channel < 2; channel++) {
            float[] complex = new float[N_FFT * 2];
            for (int time = 0; time < SEGMENT_SIZE; time++) {
                Arrays.fill(complex, 0f);
                int frameStart = (time * HOP_LENGTH) - TRIM;
                for (int sample = 0; sample < N_FFT; sample++) {
                    int audioIndex = frameStart + sample;
                    float value = audioIndex >= 0 && audioIndex < audio[channel].length ? audio[channel][audioIndex] : 0f;
                    complex[sample * 2] = value * stftWindow[sample];
                }

                fft.complexForward(complex);
                int realPlane = channel * 2;
                int imagPlane = realPlane + 1;
                for (int freq = 0; freq < DIM_F; freq++) {
                    spectrum[0][realPlane][freq][time] = complex[freq * 2];
                    spectrum[0][imagPlane][freq][time] = complex[(freq * 2) + 1];
                }
            }
        }
        return spectrum;
    }

    private float[][] istft(float[][][][] spectrum, int outputFrames) {
        int paddedFrames = ((SEGMENT_SIZE - 1) * HOP_LENGTH) + N_FFT;
        float[][] padded = new float[2][paddedFrames];
        float[] divider = new float[paddedFrames];

        for (int channel = 0; channel < 2; channel++) {
            int realPlane = channel * 2;
            int imagPlane = realPlane + 1;
            float[] complex = new float[N_FFT * 2];
            for (int time = 0; time < SEGMENT_SIZE; time++) {
                Arrays.fill(complex, 0f);
                for (int freq = 0; freq < DIM_F; freq++) {
                    complex[freq * 2] = spectrum[0][realPlane][freq][time];
                    complex[(freq * 2) + 1] = spectrum[0][imagPlane][freq][time];
                }

                for (int freq = 1; freq < N_FFT / 2; freq++) {
                    int mirror = N_FFT - freq;
                    complex[mirror * 2] = complex[freq * 2];
                    complex[(mirror * 2) + 1] = -complex[(freq * 2) + 1];
                }

                fft.complexInverse(complex, true);
                int frameStart = time * HOP_LENGTH;
                for (int sample = 0; sample < N_FFT; sample++) {
                    int index = frameStart + sample;
                    float weight = stftWindow[sample];
                    padded[channel][index] += complex[sample * 2] * weight;
                    if (channel == 0) {
                        divider[index] += weight * weight;
                    }
                }
            }
        }

        float[][] output = new float[2][outputFrames];
        for (int channel = 0; channel < 2; channel++) {
            for (int frame = 0; frame < outputFrames; frame++) {
                int paddedIndex = TRIM + frame;
                float weight = divider[paddedIndex];
                output[channel][frame] = weight == 0f ? padded[channel][paddedIndex] : padded[channel][paddedIndex] / weight;
            }
        }
        return output;
    }

    private File copyModelAsset() throws IOException, VoxSeparationException {
        File modelDir = new File(context.getFilesDir(), "vox/models");
        if (!modelDir.exists() && !modelDir.mkdirs()) {
            throw new IOException("Could not create model directory: " + modelDir.getAbsolutePath());
        }

        File modelFile = new File(modelDir, MODEL_FILENAME);
        if (modelFile.exists() && modelFile.length() > 0) {
            return modelFile;
        }

        AssetManager assets = context.getAssets();
        try (InputStream inputStream = assets.open(MODEL_ASSET_PATH);
             FileOutputStream outputStream = new FileOutputStream(modelFile)) {
            byte[] buffer = new byte[1024 * 1024];
            int read;
            while ((read = inputStream.read(buffer)) >= 0) {
                outputStream.write(buffer, 0, read);
            }
        } catch (IOException error) {
            throw new VoxSeparationException(
                "MODEL_NOT_FOUND",
                "Bundled ONNX model asset is missing.",
                "Expected Android asset: " + MODEL_ASSET_PATH
            );
        }

        return modelFile;
    }

    private float normalizeInPlace(float[][] audio) {
        float peak = 0f;
        for (int channel = 0; channel < 2; channel++) {
            for (int frame = 0; frame < audio[channel].length; frame++) {
                peak = Math.max(peak, Math.abs(audio[channel][frame]));
            }
        }

        if (peak <= 0f) {
            return 1f;
        }

        for (int channel = 0; channel < 2; channel++) {
            for (int frame = 0; frame < audio[channel].length; frame++) {
                audio[channel][frame] /= peak;
            }
        }
        return peak;
    }

    JSObject buildOutputs(Result result) throws JSONException {
        JSObject outputs = new JSObject();
        outputs.put("vocals", buildArtifact(result.vocalsFile, result));
        outputs.put("instrumental", buildArtifact(result.instrumentalFile, result));
        return outputs;
    }

    JSObject buildEngine(Result result) throws JSONException {
        JSObject timings = new JSObject();
        timings.put("modelLoadMs", result.modelLoadMs);
        timings.put("separateMs", result.separateMs);

        JSObject engine = new JSObject();
        engine.put("name", "onnxruntime-android");
        engine.put("version", result.engineVersion);
        engine.put("model", MODEL_DISPLAY_NAME);
        engine.put("mode", "uvr-mdx-stft");
        engine.put("sampleRate", SAMPLE_RATE);
        engine.put("nFft", N_FFT);
        engine.put("hopLength", HOP_LENGTH);
        engine.put("dimF", DIM_F);
        engine.put("segmentSize", SEGMENT_SIZE);
        engine.put("overlap", OVERLAP);
        engine.put("compensate", COMPENSATE);
        engine.put("peak", result.peak);
        engine.put("input", result.modelInputSummary);
        engine.put("output", result.modelOutputSummary);
        engine.put("timings", timings);
        return engine;
    }

    private JSObject buildArtifact(File file, Result result) throws JSONException {
        JSObject artifact = new JSObject();
        artifact.put("path", file.getAbsolutePath());
        artifact.put("uri", file.toURI().toString());
        artifact.put("format", "wav");
        artifact.put("sampleRate", result.sampleRate);
        artifact.put("channels", result.channels);
        artifact.put("durationSec", result.durationSec());
        return artifact;
    }

    private JSObject buildChunkProgressDetail(
        int chunkIndex,
        int totalChunks,
        long onnxElapsedMs,
        long overlapElapsedMs,
        long flushElapsedMs,
        long chunkTotalElapsedMs,
        int writtenFrames,
        long separationStartedAtMs,
        long completedChunkElapsedMs,
        long[] recentChunkElapsedMs,
        int recentChunkCount
    ) {
        JSObject detail = new JSObject();
        Runtime runtime = Runtime.getRuntime();
        long usedHeap = runtime.totalMemory() - runtime.freeMemory();
        long availableHeap = Math.max(0L, runtime.maxMemory() - usedHeap);
        long now = System.currentTimeMillis();
        int chunksRemaining = Math.max(0, totalChunks - chunkIndex);
        long averageChunkMs = chunkIndex > 0 ? Math.round(completedChunkElapsedMs / (double) chunkIndex) : -1L;
        long recentAverageChunkMs = averageRecent(recentChunkElapsedMs, recentChunkCount);
        long etaBasisMs = recentAverageChunkMs > 0L ? recentAverageChunkMs : averageChunkMs;
        long estimatedSeparationRemainingMs = chunkIndex >= 3 && etaBasisMs > 0L ? etaBasisMs * chunksRemaining : -1L;

        detail.put("chunkIndex", chunkIndex);
        detail.put("totalChunks", totalChunks);
        detail.put("chunksCompleted", chunkIndex);
        detail.put("chunksRemaining", chunksRemaining);
        detail.put("chunkElapsedMs", chunkTotalElapsedMs);
        detail.put("onnxChunkElapsedMs", onnxElapsedMs);
        detail.put("overlapAddElapsedMs", overlapElapsedMs);
        detail.put("wavFlushElapsedMs", flushElapsedMs);
        detail.put("chunkTotalElapsedMs", chunkTotalElapsedMs);
        detail.put("elapsedMs", Math.max(0L, now - separationStartedAtMs));
        detail.put("averageChunkMs", averageChunkMs > 0L ? averageChunkMs : JSONObject.NULL);
        detail.put("recentAverageChunkMs", recentAverageChunkMs > 0L ? recentAverageChunkMs : JSONObject.NULL);
        detail.put("estimatedRemainingMs", estimatedSeparationRemainingMs >= 0L ? estimatedSeparationRemainingMs : JSONObject.NULL);
        detail.put("estimatedSeparationRemainingMs", estimatedSeparationRemainingMs >= 0L ? estimatedSeparationRemainingMs : JSONObject.NULL);
        detail.put("estimatedTotalRemainingMs", estimatedSeparationRemainingMs >= 0L ? estimatedSeparationRemainingMs : JSONObject.NULL);
        detail.put("lastProgressAt", isoNow(now));
        detail.put("writtenStemFrames", writtenFrames);
        detail.put("runtimeUsedHeapBytes", usedHeap);
        detail.put("runtimeAvailableHeapBytes", availableHeap);
        detail.put("runtimeMaxHeapBytes", runtime.maxMemory());
        detail.put("nativeHeapAllocatedBytes", Debug.getNativeHeapAllocatedSize());

        ActivityManager activityManager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        if (activityManager != null) {
            ActivityManager.MemoryInfo memoryInfo = new ActivityManager.MemoryInfo();
            activityManager.getMemoryInfo(memoryInfo);
            detail.put("systemAvailableMemoryBytes", memoryInfo.availMem);
            detail.put("systemLowMemory", memoryInfo.lowMemory);
        }

        return detail;
    }

    private long averageRecent(long[] values, int count) {
        if (values == null || count <= 0) {
            return -1L;
        }
        long total = 0L;
        int valid = 0;
        for (int index = 0; index < Math.min(count, values.length); index++) {
            long value = values[index];
            if (value > 0L) {
                total += value;
                valid++;
            }
        }
        return valid > 0 ? Math.round(total / (double) valid) : -1L;
    }

    private static String isoNow(long timestampMs) {
        java.text.SimpleDateFormat format = new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", java.util.Locale.US);
        format.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
        return format.format(new java.util.Date(timestampMs));
    }

    private String slowestPhase(long onnxElapsedMs, long overlapElapsedMs, long flushElapsedMs) {
        if (flushElapsedMs >= onnxElapsedMs && flushElapsedMs >= overlapElapsedMs) {
            return "wav_flush";
        }
        if (overlapElapsedMs >= onnxElapsedMs) {
            return "overlap_add";
        }
        return "onnx";
    }

    private static class RollingStemAccumulator {
        private final float[][] source;
        private final int sourceFrames;
        private final float peak;
        private final int capacity;
        private final float[][] result;
        private final float[][] divider;
        private final WavAudio.StreamingPcm16WavWriter vocalsWriter;
        private final WavAudio.StreamingPcm16WavWriter instrumentalWriter;
        private int baseIndex = 0;
        private boolean closed = false;

        RollingStemAccumulator(
            float[][] source,
            int sourceFrames,
            float peak,
            int capacity,
            int sampleRate,
            File vocalsFile,
            File instrumentalFile
        ) throws IOException {
            this.source = source;
            this.sourceFrames = sourceFrames;
            this.peak = peak;
            this.capacity = capacity;
            this.result = new float[2][capacity];
            this.divider = new float[2][capacity];
            this.vocalsWriter = WavAudio.openPcm16WavWriter(vocalsFile, sampleRate);
            this.instrumentalWriter = WavAudio.openPcm16WavWriter(instrumentalFile, sampleRate);
        }

        void add(int channel, int mixtureIndex, float value, float weight) throws VoxSeparationException {
            int distance = mixtureIndex - baseIndex;
            if (distance < 0 || distance >= capacity) {
                throw new VoxSeparationException(
                    "ANDROID_LOCAL_STREAMING_BUFFER_OVERFLOW",
                    "Android local separator streaming buffer could not hold the active overlap window.",
                    "mixtureIndex=" + mixtureIndex + "; baseIndex=" + baseIndex + "; capacity=" + capacity
                );
            }

            int offset = ringOffset(mixtureIndex);
            result[channel][offset] += value * weight;
            divider[channel][offset] += weight;
        }

        void flushUntil(int exclusiveMixtureIndex) throws IOException {
            while (baseIndex < exclusiveMixtureIndex) {
                int offset = ringOffset(baseIndex);
                int sourceIndex = baseIndex - TRIM;
                if (sourceIndex >= 0 && sourceIndex < sourceFrames) {
                    float leftInstrumental = sampleAt(0, offset) * peak;
                    float rightInstrumental = sampleAt(1, offset) * peak;
                    float leftSource = source[0][sourceIndex] * peak;
                    float rightSource = source[1][sourceIndex] * peak;
                    instrumentalWriter.writeFrame(leftInstrumental, rightInstrumental);
                    vocalsWriter.writeFrame(
                        leftSource - (leftInstrumental * COMPENSATE),
                        rightSource - (rightInstrumental * COMPENSATE)
                    );
                }

                clearOffset(offset);
                baseIndex++;
            }
        }

        int frameCount() {
            return vocalsWriter.frameCount();
        }

        void close() throws IOException {
            if (closed) {
                return;
            }
            closed = true;
            IOException failure = null;
            try {
                vocalsWriter.close();
            } catch (IOException error) {
                failure = error;
            }
            try {
                instrumentalWriter.close();
            } catch (IOException error) {
                if (failure == null) {
                    failure = error;
                }
            }
            if (failure != null) {
                throw failure;
            }
        }

        void abort() {
            closed = true;
            vocalsWriter.abort();
            instrumentalWriter.abort();
        }

        private float sampleAt(int channel, int offset) {
            float weight = divider[channel][offset];
            return weight == 0f ? result[channel][offset] : result[channel][offset] / weight;
        }

        private void clearOffset(int offset) {
            result[0][offset] = 0f;
            result[1][offset] = 0f;
            divider[0][offset] = 0f;
            divider[1][offset] = 0f;
        }

        private int ringOffset(int mixtureIndex) {
            int offset = mixtureIndex % capacity;
            return offset < 0 ? offset + capacity : offset;
        }
    }

    private TensorInfo tensorInfo(NodeInfo nodeInfo) {
        if (nodeInfo == null || !(nodeInfo.getInfo() instanceof TensorInfo)) {
            return null;
        }
        return (TensorInfo) nodeInfo.getInfo();
    }

    private String firstKey(Map<String, NodeInfo> map) throws VoxSeparationException {
        if (map == null || map.isEmpty()) {
            throw new VoxSeparationException("UNSUPPORTED_MODEL_IO", "The ONNX model has no inputs or outputs.");
        }
        return map.keySet().iterator().next();
    }

    private String summarize(Map<String, NodeInfo> map) {
        StringBuilder builder = new StringBuilder();
        for (Map.Entry<String, NodeInfo> entry : map.entrySet()) {
            builder.append(entry.getKey()).append(":");
            TensorInfo info = tensorInfo(entry.getValue());
            if (info == null) {
                builder.append("non_tensor");
            } else {
                builder.append(info.type).append("[");
                long[] shape = info.getShape();
                for (int index = 0; index < shape.length; index++) {
                    if (index > 0) builder.append(",");
                    builder.append(shape[index]);
                }
                builder.append("]");
            }
            builder.append(" ");
        }
        return builder.toString().trim();
    }

    private static float[] hann(int size) {
        float[] window = new float[size];
        if (size == 1) {
            window[0] = 1f;
            return window;
        }
        for (int index = 0; index < size; index++) {
            window[index] = (float) (0.5d - (0.5d * Math.cos((2d * Math.PI * index) / (size - 1))));
        }
        return window;
    }

    private static long stereoFloatBytes(long frames) {
        return frames <= 0L ? -1L : frames * 2L * Float.BYTES;
    }
}
