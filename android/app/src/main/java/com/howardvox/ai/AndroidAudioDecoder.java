package com.howardvox.ai;

import android.media.AudioFormat;
import android.media.MediaCodec;
import android.media.MediaExtractor;
import android.media.MediaFormat;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Locale;

class AndroidAudioDecoder {
    private static final int BUFFER_TIMEOUT_US = 10_000;
    private static final long DECODE_STALL_TIMEOUT_MS = 15_000L;

    WavAudio.AudioBuffer decodeToStereo(
        File inputFile,
        String mimeType,
        int targetSampleRate,
        AndroidOnnxSeparator.CancelSignal cancelSignal
    )
        throws IOException, VoxSeparationException {
        WavAudio.AudioBuffer decoded;
        if (isWav(inputFile, mimeType)) {
            decoded = WavAudio.readPcmWav(inputFile);
        } else {
            decoded = decodeWithMediaCodec(inputFile, mimeType, cancelSignal);
        }
        return resample(decoded, targetSampleRate);
    }

    private boolean isWav(File inputFile, String mimeType) {
        String lowerName = inputFile.getName().toLowerCase(Locale.US);
        return lowerName.endsWith(".wav")
            || "audio/wav".equals(mimeType)
            || "audio/x-wav".equals(mimeType);
    }

    private WavAudio.AudioBuffer decodeWithMediaCodec(
        File inputFile,
        String originalMimeType,
        AndroidOnnxSeparator.CancelSignal cancelSignal
    ) throws IOException, VoxSeparationException {
        MediaExtractor extractor = new MediaExtractor();
        MediaCodec codec = null;
        MediaFormat inputFormat = null;
        MediaFormat outputFormat = null;
        String trackMime = null;

        try {
            extractor.setDataSource(inputFile.getAbsolutePath());
            int trackIndex = findAudioTrack(extractor);
            if (trackIndex < 0) {
                throw new VoxSeparationException(
                    "UNSUPPORTED_AUDIO_FORMAT",
                    "No audio track was found in the uploaded file.",
                    decodeDetails(inputFile, originalMimeType, null, null, null, null)
                );
            }

            extractor.selectTrack(trackIndex);
            inputFormat = extractor.getTrackFormat(trackIndex);
            trackMime = inputFormat.getString(MediaFormat.KEY_MIME);
            if (trackMime == null || !trackMime.startsWith("audio/")) {
                throw new VoxSeparationException(
                    "UNSUPPORTED_AUDIO_FORMAT",
                    "The selected track is not an audio stream.",
                    decodeDetails(inputFile, originalMimeType, trackMime, inputFormat, null, null)
                );
            }

            codec = MediaCodec.createDecoderByType(trackMime);
            codec.configure(inputFormat, null, null, 0);
            codec.start();

            StereoBuilder builder = new StereoBuilder();
            MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
            outputFormat = inputFormat;
            boolean inputDone = false;
            boolean outputDone = false;
            long lastProgressMs = System.currentTimeMillis();

            while (!outputDone) {
                throwIfCancelled(cancelSignal);

                if (!inputDone) {
                    int inputBufferIndex = codec.dequeueInputBuffer(BUFFER_TIMEOUT_US);
                    if (inputBufferIndex >= 0) {
                        ByteBuffer inputBuffer = codec.getInputBuffer(inputBufferIndex);
                        if (inputBuffer == null) {
                            throw new VoxSeparationException("AUDIO_DECODE_FAILED", "Android decoder input buffer was unavailable.");
                        }

                        inputBuffer.clear();
                        int sampleSize = extractor.readSampleData(inputBuffer, 0);
                        if (sampleSize < 0) {
                            codec.queueInputBuffer(inputBufferIndex, 0, 0, 0L, MediaCodec.BUFFER_FLAG_END_OF_STREAM);
                            inputDone = true;
                            lastProgressMs = System.currentTimeMillis();
                        } else {
                            codec.queueInputBuffer(
                                inputBufferIndex,
                                0,
                                sampleSize,
                                extractor.getSampleTime(),
                                extractor.getSampleFlags()
                            );
                            extractor.advance();
                            lastProgressMs = System.currentTimeMillis();
                        }
                    }
                }

                int outputBufferIndex = codec.dequeueOutputBuffer(info, BUFFER_TIMEOUT_US);
                if (outputBufferIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    outputFormat = codec.getOutputFormat();
                    lastProgressMs = System.currentTimeMillis();
                } else if (outputBufferIndex >= 0) {
                    ByteBuffer outputBuffer = codec.getOutputBuffer(outputBufferIndex);
                    if (outputBuffer != null && info.size > 0) {
                        outputBuffer.position(info.offset);
                        outputBuffer.limit(info.offset + info.size);
                        appendPcm(outputBuffer.slice(), info.size, outputFormat, builder);
                        lastProgressMs = System.currentTimeMillis();
                    }

                    codec.releaseOutputBuffer(outputBufferIndex, false);
                    if ((info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) {
                        outputDone = true;
                        lastProgressMs = System.currentTimeMillis();
                    }
                }

                if (System.currentTimeMillis() - lastProgressMs > DECODE_STALL_TIMEOUT_MS) {
                    throw new VoxSeparationException(
                        "AUDIO_DECODE_TIMEOUT",
                        "Android decoder stalled while reading this audio file.",
                        decodeDetails(inputFile, originalMimeType, trackMime, inputFormat, outputFormat, null)
                    );
                }
            }

            int sampleRate = getInteger(outputFormat, MediaFormat.KEY_SAMPLE_RATE, getInteger(inputFormat, MediaFormat.KEY_SAMPLE_RATE, 0));
            if (sampleRate <= 0 || builder.size() == 0) {
                throw new VoxSeparationException(
                    "AUDIO_DECODE_FAILED",
                    "Android decoder produced no PCM audio.",
                    decodeDetails(inputFile, originalMimeType, trackMime, inputFormat, outputFormat, null)
                );
            }

            return new WavAudio.AudioBuffer(builder.channels(), sampleRate, 2, builder.size());
        } catch (VoxSeparationException error) {
            throw error;
        } catch (Exception error) {
            throw new VoxSeparationException(
                "AUDIO_DECODE_FAILED",
                "Android MediaCodec could not decode this audio file.",
                decodeDetails(inputFile, originalMimeType, trackMime, inputFormat, outputFormat, error)
            );
        } finally {
            if (codec != null) {
                try {
                    codec.stop();
                } catch (Exception ignored) {
                    // Decoder may fail before start; release still needs to run.
                }
                codec.release();
            }
            extractor.release();
        }
    }

    private void throwIfCancelled(AndroidOnnxSeparator.CancelSignal cancelSignal) throws VoxSeparationException {
        if (cancelSignal != null && cancelSignal.isCancelled()) {
            throw new VoxSeparationException("JOB_CANCELLED", "Android local VOX job was cancelled.");
        }
    }

    private String decodeDetails(
        File inputFile,
        String originalMimeType,
        String trackMime,
        MediaFormat inputFormat,
        MediaFormat outputFormat,
        Exception error
    ) {
        return "file=" + inputFile.getName()
            + "; sizeBytes=" + inputFile.length()
            + "; originalMime=" + originalMimeType
            + "; trackMime=" + trackMime
            + "; inputFormat=" + describeFormat(inputFormat)
            + "; outputFormat=" + describeFormat(outputFormat)
            + "; error=" + (error == null ? "" : error.getClass().getSimpleName() + ": " + error.getMessage());
    }

    private String describeFormat(MediaFormat format) {
        return format == null ? "unavailable" : format.toString();
    }

    private int findAudioTrack(MediaExtractor extractor) {
        for (int index = 0; index < extractor.getTrackCount(); index++) {
            MediaFormat format = extractor.getTrackFormat(index);
            String mime = format.getString(MediaFormat.KEY_MIME);
            if (mime != null && mime.startsWith("audio/")) {
                return index;
            }
        }
        return -1;
    }

    private void appendPcm(ByteBuffer buffer, int size, MediaFormat format, StereoBuilder builder)
        throws VoxSeparationException {
        int channelCount = getInteger(format, MediaFormat.KEY_CHANNEL_COUNT, 2);
        int pcmEncoding = getInteger(format, MediaFormat.KEY_PCM_ENCODING, AudioFormat.ENCODING_PCM_16BIT);
        int bytesPerSample;

        if (pcmEncoding == AudioFormat.ENCODING_PCM_FLOAT) {
            bytesPerSample = 4;
        } else if (pcmEncoding == AudioFormat.ENCODING_PCM_16BIT) {
            bytesPerSample = 2;
        } else {
            throw new VoxSeparationException("UNSUPPORTED_AUDIO_ENCODING", "Only 16-bit PCM and float PCM decoder output are supported.");
        }

        if (channelCount < 1) {
            throw new VoxSeparationException("UNSUPPORTED_AUDIO_ENCODING", "Decoded audio has no channels.");
        }

        buffer.order(ByteOrder.LITTLE_ENDIAN);
        int frameSize = channelCount * bytesPerSample;
        int frameCount = size / frameSize;

        for (int frame = 0; frame < frameCount; frame++) {
            float left = readSample(buffer, pcmEncoding);
            float right = channelCount > 1 ? readSample(buffer, pcmEncoding) : left;
            for (int channel = 2; channel < channelCount; channel++) {
                readSample(buffer, pcmEncoding);
            }
            builder.append(left, right);
        }
    }

    private float readSample(ByteBuffer buffer, int pcmEncoding) {
        if (pcmEncoding == AudioFormat.ENCODING_PCM_FLOAT) {
            return clamp(buffer.getFloat());
        }
        return buffer.getShort() / 32768f;
    }

    private WavAudio.AudioBuffer resample(WavAudio.AudioBuffer source, int targetSampleRate) {
        if (source.sampleRate == targetSampleRate) {
            return source;
        }

        int outputFrames = Math.max(1, Math.round((float) source.frameCount * targetSampleRate / source.sampleRate));
        float[][] output = new float[2][outputFrames];
        float ratio = (float) source.sampleRate / (float) targetSampleRate;

        for (int frame = 0; frame < outputFrames; frame++) {
            float sourcePosition = frame * ratio;
            int index = (int) Math.floor(sourcePosition);
            int nextIndex = Math.min(source.frameCount - 1, index + 1);
            float fraction = sourcePosition - index;

            for (int channel = 0; channel < 2; channel++) {
                float a = source.channels[channel][Math.min(index, source.frameCount - 1)];
                float b = source.channels[channel][nextIndex];
                output[channel][frame] = a + ((b - a) * fraction);
            }
        }

        return new WavAudio.AudioBuffer(output, targetSampleRate, 2, outputFrames);
    }

    private int getInteger(MediaFormat format, String key, int fallback) {
        return format != null && format.containsKey(key) ? format.getInteger(key) : fallback;
    }

    private float clamp(float sample) {
        return Math.max(-1f, Math.min(1f, sample));
    }

    private static class StereoBuilder {
        private float[] left = new float[8192];
        private float[] right = new float[8192];
        private int size = 0;

        void append(float leftSample, float rightSample) {
            ensure(size + 1);
            left[size] = leftSample;
            right[size] = rightSample;
            size++;
        }

        int size() {
            return size;
        }

        float[][] channels() {
            if (left.length != size) {
                float[] exactLeft = new float[size];
                float[] exactRight = new float[size];
                System.arraycopy(left, 0, exactLeft, 0, size);
                System.arraycopy(right, 0, exactRight, 0, size);
                left = exactLeft;
                right = exactRight;
            }
            return new float[][] { left, right };
        }

        private void ensure(int needed) {
            if (needed <= left.length) {
                return;
            }

            int next = left.length * 2;
            while (next < needed) {
                next *= 2;
            }

            float[] nextLeft = new float[next];
            float[] nextRight = new float[next];
            System.arraycopy(left, 0, nextLeft, 0, size);
            System.arraycopy(right, 0, nextRight, 0, size);
            left = nextLeft;
            right = nextRight;
        }
    }
}
