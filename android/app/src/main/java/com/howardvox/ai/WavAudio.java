package com.howardvox.ai;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

class WavAudio {
    static class AudioBuffer {
        final float[][] channels;
        final int sampleRate;
        final int channelCount;
        final int frameCount;

        AudioBuffer(float[][] channels, int sampleRate, int channelCount, int frameCount) {
            this.channels = channels;
            this.sampleRate = sampleRate;
            this.channelCount = channelCount;
            this.frameCount = frameCount;
        }

        float durationSec() {
            return sampleRate > 0 ? (float) frameCount / (float) sampleRate : 0f;
        }
    }

    static AudioBuffer readPcmWav(File file) throws IOException, VoxSeparationException {
        byte[] bytes = readAll(file);
        if (bytes.length < 44 || !"RIFF".equals(ascii(bytes, 0, 4)) || !"WAVE".equals(ascii(bytes, 8, 4))) {
            throw new VoxSeparationException("UNSUPPORTED_AUDIO_FORMAT", "Only PCM WAV input is supported by the first native Android separator.");
        }

        int offset = 12;
        int audioFormat = -1;
        int channelCount = -1;
        int sampleRate = -1;
        int bitsPerSample = -1;
        int dataOffset = -1;
        int dataSize = -1;

        while (offset + 8 <= bytes.length) {
            String chunkId = ascii(bytes, offset, 4);
            int chunkSize = readIntLE(bytes, offset + 4);
            int chunkDataOffset = offset + 8;

            if ("fmt ".equals(chunkId)) {
                audioFormat = readShortLE(bytes, chunkDataOffset);
                channelCount = readShortLE(bytes, chunkDataOffset + 2);
                sampleRate = readIntLE(bytes, chunkDataOffset + 4);
                bitsPerSample = readShortLE(bytes, chunkDataOffset + 14);
            } else if ("data".equals(chunkId)) {
                dataOffset = chunkDataOffset;
                dataSize = chunkSize;
                break;
            }

            offset = chunkDataOffset + chunkSize + (chunkSize % 2);
        }

        if (audioFormat != 1 && audioFormat != 3) {
            throw new VoxSeparationException("UNSUPPORTED_WAV_ENCODING", "Only PCM integer and IEEE float WAV encodings are supported.");
        }
        if (channelCount < 1 || channelCount > 2 || sampleRate <= 0 || dataOffset < 0 || dataSize <= 0) {
            throw new VoxSeparationException("UNSUPPORTED_WAV_ENCODING", "WAV metadata is incomplete or unsupported.");
        }
        if (audioFormat == 1 && bitsPerSample != 16 && bitsPerSample != 24 && bitsPerSample != 32) {
            throw new VoxSeparationException("UNSUPPORTED_WAV_ENCODING", "Only 16-bit, 24-bit, and 32-bit PCM WAV files are supported.");
        }
        if (audioFormat == 3 && bitsPerSample != 32) {
            throw new VoxSeparationException("UNSUPPORTED_WAV_ENCODING", "Only 32-bit float WAV files are supported.");
        }

        int bytesPerSample = bitsPerSample / 8;
        int frameCount = dataSize / (bytesPerSample * channelCount);
        float[][] channels = new float[2][frameCount];

        for (int frame = 0; frame < frameCount; frame++) {
            for (int sourceChannel = 0; sourceChannel < channelCount; sourceChannel++) {
                int sampleOffset = dataOffset + ((frame * channelCount + sourceChannel) * bytesPerSample);
                float sample = decodeSample(bytes, sampleOffset, bitsPerSample, audioFormat);
                channels[sourceChannel][frame] = sample;
                if (channelCount == 1) {
                    channels[1][frame] = sample;
                }
            }
        }

        return new AudioBuffer(channels, sampleRate, 2, frameCount);
    }

    static void writePcm16Wav(File file, float[][] channels, int sampleRate, int frameCount) throws IOException {
        int channelCount = 2;
        int bitsPerSample = 16;
        int byteRate = sampleRate * channelCount * bitsPerSample / 8;
        int blockAlign = channelCount * bitsPerSample / 8;
        int dataSize = frameCount * blockAlign;

        try (FileOutputStream outputStream = new FileOutputStream(file)) {
            outputStream.write(ascii("RIFF"));
            writeIntLE(outputStream, 36 + dataSize);
            outputStream.write(ascii("WAVE"));
            outputStream.write(ascii("fmt "));
            writeIntLE(outputStream, 16);
            writeShortLE(outputStream, 1);
            writeShortLE(outputStream, channelCount);
            writeIntLE(outputStream, sampleRate);
            writeIntLE(outputStream, byteRate);
            writeShortLE(outputStream, blockAlign);
            writeShortLE(outputStream, bitsPerSample);
            outputStream.write(ascii("data"));
            writeIntLE(outputStream, dataSize);

            for (int frame = 0; frame < frameCount; frame++) {
                writePcm16Sample(outputStream, channels[0][frame]);
                writePcm16Sample(outputStream, channels[1][frame]);
            }
        }
    }

    static StreamingPcm16WavWriter openPcm16WavWriter(File file, int sampleRate) throws IOException {
        return new StreamingPcm16WavWriter(file, sampleRate);
    }

    static class StreamingPcm16WavWriter implements AutoCloseable {
        private static final int PCM_BUFFER_BYTES = 256 * 1024;

        private final File file;
        private final RandomAccessFile output;
        private final int sampleRate;
        private final int channelCount = 2;
        private final int bitsPerSample = 16;
        private final byte[] pcmBuffer = new byte[PCM_BUFFER_BYTES];
        private int frameCount = 0;
        private int bufferPosition = 0;
        private boolean closed = false;
        private boolean aborted = false;

        StreamingPcm16WavWriter(File file, int sampleRate) throws IOException {
            this.file = file;
            this.sampleRate = sampleRate;
            this.output = new RandomAccessFile(file, "rw");
            this.output.setLength(0L);
            writeHeader(0);
        }

        void writeFrame(float left, float right) throws IOException {
            ensureOpen();
            writePcm16Sample(left);
            writePcm16Sample(right);
            frameCount++;
        }

        int frameCount() {
            return frameCount;
        }

        void abort() {
            aborted = true;
            try {
                close();
            } catch (IOException ignored) {
                // Best effort cleanup below removes incomplete output.
            }
            if (file.exists()) {
                file.delete();
            }
        }

        @Override
        public void close() throws IOException {
            if (closed) {
                return;
            }

            try {
                if (!aborted) {
                    flushBuffer();
                    patchHeader();
                }
            } finally {
                closed = true;
                output.close();
            }
        }

        private void ensureOpen() throws IOException {
            if (closed || aborted) {
                throw new IOException("WAV writer is closed.");
            }
        }

        private void writePcm16Sample(float sample) throws IOException {
            if (bufferPosition + 2 > pcmBuffer.length) {
                flushBuffer();
            }

            int value = Math.max(-32768, Math.min(32767, Math.round(sample * 32767f)));
            pcmBuffer[bufferPosition++] = (byte) (value & 0xff);
            pcmBuffer[bufferPosition++] = (byte) ((value >> 8) & 0xff);
        }

        private void flushBuffer() throws IOException {
            if (bufferPosition > 0) {
                output.write(pcmBuffer, 0, bufferPosition);
                bufferPosition = 0;
            }
        }

        private void patchHeader() throws IOException {
            long currentPosition = output.getFilePointer();
            output.seek(0L);
            writeHeader(frameCount);
            output.seek(currentPosition);
        }

        private void writeHeader(int frames) throws IOException {
            int byteRate = sampleRate * channelCount * bitsPerSample / 8;
            int blockAlign = channelCount * bitsPerSample / 8;
            int dataSize = frames * blockAlign;

            output.write(ascii("RIFF"));
            writeIntLE(output, 36 + dataSize);
            output.write(ascii("WAVE"));
            output.write(ascii("fmt "));
            writeIntLE(output, 16);
            writeShortLE(output, 1);
            writeShortLE(output, channelCount);
            writeIntLE(output, sampleRate);
            writeIntLE(output, byteRate);
            writeShortLE(output, blockAlign);
            writeShortLE(output, bitsPerSample);
            output.write(ascii("data"));
            writeIntLE(output, dataSize);
        }
    }

    private static float decodeSample(byte[] bytes, int offset, int bitsPerSample, int audioFormat) {
        if (audioFormat == 3) {
            return ByteBuffer.wrap(bytes, offset, 4).order(ByteOrder.LITTLE_ENDIAN).getFloat();
        }
        if (bitsPerSample == 16) {
            return (short) readShortLE(bytes, offset) / 32768f;
        }
        if (bitsPerSample == 24) {
            int value = (bytes[offset] & 0xff) | ((bytes[offset + 1] & 0xff) << 8) | (bytes[offset + 2] << 16);
            return value / 8388608f;
        }
        int value = readIntLE(bytes, offset);
        return value / 2147483648f;
    }

    private static void writePcm16Sample(FileOutputStream outputStream, float sample) throws IOException {
        int value = Math.max(-32768, Math.min(32767, Math.round(sample * 32767f)));
        writeShortLE(outputStream, value);
    }

    private static void writePcm16Sample(RandomAccessFile output, float sample) throws IOException {
        int value = Math.max(-32768, Math.min(32767, Math.round(sample * 32767f)));
        writeShortLE(output, value);
    }

    private static byte[] readAll(File file) throws IOException {
        try (FileInputStream inputStream = new FileInputStream(file);
             ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = inputStream.read(buffer)) >= 0) {
                outputStream.write(buffer, 0, read);
            }
            return outputStream.toByteArray();
        }
    }

    private static String ascii(byte[] bytes, int offset, int length) {
        return new String(bytes, offset, length);
    }

    private static byte[] ascii(String value) {
        return value.getBytes();
    }

    private static int readShortLE(byte[] bytes, int offset) {
        return (bytes[offset] & 0xff) | ((bytes[offset + 1] & 0xff) << 8);
    }

    private static int readIntLE(byte[] bytes, int offset) {
        return (bytes[offset] & 0xff)
            | ((bytes[offset + 1] & 0xff) << 8)
            | ((bytes[offset + 2] & 0xff) << 16)
            | (bytes[offset + 3] << 24);
    }

    private static void writeShortLE(FileOutputStream outputStream, int value) throws IOException {
        outputStream.write(value & 0xff);
        outputStream.write((value >> 8) & 0xff);
    }

    private static void writeIntLE(FileOutputStream outputStream, int value) throws IOException {
        outputStream.write(value & 0xff);
        outputStream.write((value >> 8) & 0xff);
        outputStream.write((value >> 16) & 0xff);
        outputStream.write((value >> 24) & 0xff);
    }

    private static void writeShortLE(RandomAccessFile output, int value) throws IOException {
        output.write(value & 0xff);
        output.write((value >> 8) & 0xff);
    }

    private static void writeIntLE(RandomAccessFile output, int value) throws IOException {
        output.write(value & 0xff);
        output.write((value >> 8) & 0xff);
        output.write((value >> 16) & 0xff);
        output.write((value >> 24) & 0xff);
    }
}
