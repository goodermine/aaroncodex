/* global Buffer */
import decodeAudio from "audio-decode";
import { normalizeFeatures } from "./pulse.js";

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function parsePcmWav(fileBuffer) {
  const buffer = Buffer.isBuffer(fileBuffer) ? fileBuffer : Buffer.from(fileBuffer);

  if (buffer.toString("ascii", 0, 4) !== "RIFF" || buffer.toString("ascii", 8, 12) !== "WAVE") {
    throw new Error("Not a RIFF/WAVE file.");
  }

  let offset = 12;
  let fmt = null;
  let dataOffset = -1;
  let dataSize = 0;

  while (offset + 8 <= buffer.length) {
    const chunkId = buffer.toString("ascii", offset, offset + 4);
    const chunkSize = buffer.readUInt32LE(offset + 4);
    const chunkStart = offset + 8;

    if (chunkId === "fmt ") {
      fmt = {
        audioFormat: buffer.readUInt16LE(chunkStart),
        channels: buffer.readUInt16LE(chunkStart + 2),
        sampleRate: buffer.readUInt32LE(chunkStart + 4),
        bitsPerSample: buffer.readUInt16LE(chunkStart + 14),
      };
    } else if (chunkId === "data") {
      dataOffset = chunkStart;
      dataSize = chunkSize;
      break;
    }

    offset = chunkStart + chunkSize + (chunkSize % 2);
  }

  if (!fmt || dataOffset < 0 || !dataSize) {
    throw new Error("WAV file missing fmt or data chunk.");
  }

  if (fmt.audioFormat !== 1 || fmt.bitsPerSample !== 16) {
    throw new Error("Only 16-bit PCM WAV fallback is supported.");
  }

  const frameCount = Math.floor(dataSize / (fmt.channels * 2));
  const channelData = Array.from({ length: fmt.channels }, () => new Float32Array(frameCount));

  for (let frame = 0; frame < frameCount; frame += 1) {
    for (let channel = 0; channel < fmt.channels; channel += 1) {
      const byteOffset = dataOffset + (frame * fmt.channels + channel) * 2;
      channelData[channel][frame] = buffer.readInt16LE(byteOffset) / 32768;
    }
  }

  return {
    channelData,
    sampleRate: fmt.sampleRate,
  };
}

function getDecodedAudio(fileBuffer) {
  return decodeAudio(fileBuffer).catch(() => parsePcmWav(fileBuffer));
}

function buildActivityBlocks(samples, blockSize) {
  const blocks = [];

  for (let index = 0; index < samples.length; index += blockSize) {
    let sumSquares = 0;
    let localPeak = 0;
    let count = 0;

    for (let step = 0; step < blockSize && index + step < samples.length; step += 1) {
      const value = samples[index + step];
      const abs = Math.abs(value);
      sumSquares += value * value;
      localPeak = Math.max(localPeak, abs);
      count += 1;
    }

    blocks.push({
      peak: localPeak,
      rms: Math.sqrt(sumSquares / Math.max(1, count)),
    });
  }

  return blocks;
}

function analyzePhrases(blocks) {
  const activityThreshold = 0.04;
  const phrases = [];
  let start = null;

  blocks.forEach((block, index) => {
    const active = block.peak >= activityThreshold;
    if (active && start === null) start = index;
    if (!active && start !== null) {
      phrases.push([start, index - 1]);
      start = null;
    }
  });

  if (start !== null) {
    phrases.push([start, blocks.length - 1]);
  }

  return phrases;
}

export async function extractFeaturesFromUpload(fileBuffer) {
  const audioBuffer = await getDecodedAudio(fileBuffer);
  const channelData = Array.isArray(audioBuffer.channelData)
    ? audioBuffer.channelData
    : typeof audioBuffer.getChannelData === "function" && Number.isFinite(audioBuffer.numberOfChannels)
      ? Array.from({ length: audioBuffer.numberOfChannels }, (_, index) => audioBuffer.getChannelData(index))
      : [];

  if (!channelData.length || !channelData[0]?.length) {
    throw new Error("Decoded audio did not contain usable PCM channel data.");
  }

  const channels = channelData.length;
  const samples = channelData[0];
  const sampleRate = Number(audioBuffer.sampleRate || 0);
  const sampleCount = 72;
  const blockSize = Math.max(1, Math.floor(samples.length / sampleCount));
  const waveform = [];
  const blocks = buildActivityBlocks(samples, blockSize);
  const phrases = analyzePhrases(blocks);

  let peak = 0;
  let sumSquares = 0;
  let zeroCrossings = 0;
  let transientCount = 0;

  for (let index = 1; index < samples.length; index += 1) {
    const current = samples[index];
    const previous = samples[index - 1];
    const abs = Math.abs(current);
    const delta = Math.abs(current - previous);

    peak = Math.max(peak, abs);
    sumSquares += current * current;

    if ((current >= 0 && previous < 0) || (current < 0 && previous >= 0)) {
      zeroCrossings += 1;
    }

    if (delta > 0.18) {
      transientCount += 1;
    }
  }

  for (let index = 0; index < sampleCount; index += 1) {
    let localPeak = 0;

    for (let step = 0; step < blockSize; step += 1) {
      const sampleIndex = index * blockSize + step;
      const value = Math.abs(samples[sampleIndex] || 0);
      localPeak = Math.max(localPeak, value);
    }

    waveform.push(Number(localPeak.toFixed(3)));
  }

  const rms = Math.sqrt(sumSquares / Math.max(1, samples.length));
  const crest = peak / Math.max(rms, 0.0001);
  const brightness = zeroCrossings / Math.max(1, samples.length);
  const transientDensity = transientCount / Math.max(1, samples.length);
  const duration = sampleRate > 0 ? Number(samples.length / sampleRate) : Number(audioBuffer.duration || 0);
  const phraseCount = phrases.length;

  let onsetDrift = 0;
  let sustainStability = 100;

  if (phrases.length) {
    const onsetValues = [];
    const sustainValues = [];

    phrases.forEach(([start, end]) => {
      const phraseBlocks = blocks.slice(start, end + 1);
      if (!phraseBlocks.length) return;

      const maxPeak = Math.max(...phraseBlocks.map((block) => block.peak));
      const maxPeakIndex = phraseBlocks.findIndex((block) => block.peak >= maxPeak * 0.95);
      onsetValues.push(maxPeakIndex <= 0 ? 0 : maxPeakIndex / Math.max(1, phraseBlocks.length - 1));

      const sustainSlice = phraseBlocks.slice(Math.floor(phraseBlocks.length * 0.25), Math.max(Math.ceil(phraseBlocks.length * 0.75), 1));
      const sustainRms = sustainSlice.map((block) => block.rms).filter((value) => value > 0);
      if (sustainRms.length) {
        const mean = sustainRms.reduce((sum, value) => sum + value, 0) / sustainRms.length;
        const variance = sustainRms.reduce((sum, value) => sum + (value - mean) ** 2, 0) / sustainRms.length;
        const cv = Math.sqrt(variance) / Math.max(mean, 0.0001);
        sustainValues.push(clamp(100 - cv * 220, 0, 100));
      }
    });

    if (onsetValues.length) {
      onsetDrift = Number((onsetValues.reduce((sum, value) => sum + value, 0) / onsetValues.length).toFixed(3));
    }

    if (sustainValues.length) {
      sustainStability = Number((sustainValues.reduce((sum, value) => sum + value, 0) / sustainValues.length).toFixed(1));
    }
  }

  const range =
    crest > 4.5 ? "Wide dynamic range" : crest > 3 ? "Balanced dynamics" : "Compressed dynamic shape";
  const energy =
    rms > 0.22 ? "High intensity" : rms > 0.11 ? "Controlled intensity" : "Light intensity";
  const clarity =
    brightness > 0.16 ? "Brighter edge" : brightness > 0.09 ? "Balanced edge" : "Rounder tone";
  const attack =
    transientDensity > 0.015 ? "Sharper phrase attacks" : transientDensity > 0.008 ? "Balanced phrase attacks" : "Softer phrase attacks";

  return normalizeFeatures({
    duration,
    avgRms: Number(rms.toFixed(3)),
    peakRms: Number(peak.toFixed(3)),
    crest: Number(crest.toFixed(2)),
    channels,
    brightness: Number(brightness.toFixed(4)),
    transientDensity: Number(transientDensity.toFixed(4)),
    onsetDrift,
    sustainStability,
    phraseCount,
    range,
    energy,
    clarity,
    attack,
    decoder: typeof audioBuffer.getChannelData === "function" ? "audio-buffer" : "channel-data",
    waveform,
    score: Math.round(clamp(62 + rms * 80 + crest * 3, 58, 94)),
  });
}
