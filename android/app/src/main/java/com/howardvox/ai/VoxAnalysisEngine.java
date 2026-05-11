package com.howardvox.ai;

import com.getcapacitor.JSObject;

import org.json.JSONArray;
import org.json.JSONException;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

class VoxAnalysisEngine {
    private static final int FRAME_SIZE = 4_096;
    private static final int HOP_SIZE = 1_024;
    private static final float MIN_PITCH_HZ = 50f;
    private static final float MAX_PITCH_HZ = 1_000f;

    static class Result {
        final File pitchFile;
        final File rmsFile;
        final File crestFile;
        final File reportFile;
        final File coachInputFile;
        final JSObject metrics;
        final JSObject rawMetrics;
        final JSObject derivedMetrics;
        final JSObject issueScores;
        final JSObject vocalProfile;
        final JSObject coachInput;
        final JSObject validation;
        final JSObject coachingSummary;
        final JSObject summary;
        final long analysisMs;

        Result(
            File pitchFile,
            File rmsFile,
            File crestFile,
            File reportFile,
            File coachInputFile,
            JSObject metrics,
            JSObject rawMetrics,
            JSObject derivedMetrics,
            JSObject issueScores,
            JSObject vocalProfile,
            JSObject coachInput,
            JSObject validation,
            JSObject coachingSummary,
            JSObject summary,
            long analysisMs
        ) {
            this.pitchFile = pitchFile;
            this.rmsFile = rmsFile;
            this.crestFile = crestFile;
            this.reportFile = reportFile;
            this.coachInputFile = coachInputFile;
            this.metrics = metrics;
            this.rawMetrics = rawMetrics;
            this.derivedMetrics = derivedMetrics;
            this.issueScores = issueScores;
            this.vocalProfile = vocalProfile;
            this.coachInput = coachInput;
            this.validation = validation;
            this.coachingSummary = coachingSummary;
            this.summary = summary;
            this.analysisMs = analysisMs;
        }
    }

    interface ProgressSink {
        void onProgress(int percent, String stage, String message);
    }

    Result analyze(File vocalsFile, File analysisDir) throws IOException, JSONException, VoxSeparationException {
        return analyze(vocalsFile, analysisDir, null, null);
    }

    Result analyze(File vocalsFile, File analysisDir, ProgressSink progressSink) throws IOException, JSONException, VoxSeparationException {
        return analyze(vocalsFile, analysisDir, null, progressSink);
    }

    Result analyze(File vocalsFile, File analysisDir, JSObject context, ProgressSink progressSink) throws IOException, JSONException, VoxSeparationException {
        long startedAt = System.currentTimeMillis();
        emit(progressSink, 90, "analyze", "Reading separated vocal stem");
        WavAudio.AudioBuffer vocals = WavAudio.readPcmWav(vocalsFile);
        float[] mono = toMono(vocals);
        int frameCount = Math.max(1, 1 + Math.max(0, mono.length - FRAME_SIZE) / HOP_SIZE);

        JSONArray pitchFrames = new JSONArray();
        JSONArray rmsFrames = new JSONArray();
        JSONArray crestFrames = new JSONArray();

        double rmsSum = 0d;
        float minRms = Float.MAX_VALUE;
        float maxRms = 0f;
        float maxPeak = 0f;
        float pitchSum = 0f;
        int voicedFrames = 0;
        float minPitch = Float.MAX_VALUE;
        float maxPitch = 0f;
        double crestSum = 0d;
        int crestFramesWithSignal = 0;
        float maxCrest = 0f;
        int silenceFrames = 0;
        double pitchConfidenceSum = 0d;
        float[] frameRmsValues = new float[frameCount];
        float[] framePitchValues = new float[frameCount];
        float[] framePitchConfidenceValues = new float[frameCount];

        for (int frameIndex = 0; frameIndex < frameCount; frameIndex++) {
            int start = frameIndex * HOP_SIZE;
            float timeSec = (float) start / vocals.sampleRate;
            FrameStats stats = computeFrame(mono, start, vocals.sampleRate);
            if (frameIndex == 0 || frameIndex == frameCount - 1 || frameIndex % 10 == 0) {
                int percent = 90 + Math.round(((float) (frameIndex + 1) / (float) frameCount) * 8f);
                emit(progressSink, percent, "analyze", "Analyzing vocal metrics frame " + (frameIndex + 1) + " of " + frameCount);
            }

            JSObject pitch = new JSObject();
            pitch.put("timeSec", round(timeSec, 4));
            pitch.put("pitchHz", stats.pitchHz > 0f ? round(stats.pitchHz, 2) : null);
            pitch.put("confidence", round(stats.pitchConfidence, 3));
            pitchFrames.put(pitch);

            JSObject rms = new JSObject();
            rms.put("timeSec", round(timeSec, 4));
            rms.put("rms", round(stats.rms, 6));
            rms.put("rmsDb", stats.rms > 0f ? round((float) (20d * Math.log10(stats.rms)), 2) : null);
            rmsFrames.put(rms);

            JSObject crest = new JSObject();
            crest.put("timeSec", round(timeSec, 4));
            crest.put("peak", round(stats.peak, 6));
            crest.put("crest", stats.rms > 0f ? round(stats.peak / stats.rms, 4) : null);
            crestFrames.put(crest);

            rmsSum += stats.rms;
            minRms = Math.min(minRms, stats.rms);
            maxRms = Math.max(maxRms, stats.rms);
            maxPeak = Math.max(maxPeak, stats.peak);
            frameRmsValues[frameIndex] = stats.rms;
            framePitchValues[frameIndex] = stats.pitchHz;
            framePitchConfidenceValues[frameIndex] = stats.pitchConfidence;
            pitchConfidenceSum += stats.pitchConfidence;
            if (stats.rms < 0.003f) {
                silenceFrames++;
            }
            if (stats.rms > 0f) {
                float crestValue = stats.peak / stats.rms;
                crestSum += crestValue;
                crestFramesWithSignal++;
                maxCrest = Math.max(maxCrest, crestValue);
            }

            if (stats.pitchHz > 0f) {
                pitchSum += stats.pitchHz;
                voicedFrames++;
                minPitch = Math.min(minPitch, stats.pitchHz);
                maxPitch = Math.max(maxPitch, stats.pitchHz);
            }
        }

        JSObject metrics = new JSObject();
        metrics.put("durationSec", round((float) vocals.frameCount / vocals.sampleRate, 3));
        metrics.put("sampleRate", vocals.sampleRate);
        metrics.put("frameSize", FRAME_SIZE);
        metrics.put("hopSize", HOP_SIZE);
        metrics.put("frameCount", frameCount);
        metrics.put("avgRms", round((float) (rmsSum / frameCount), 6));
        metrics.put("peakRms", round(maxRms, 6));
        metrics.put("minRms", minRms == Float.MAX_VALUE ? 0 : round(minRms, 6));
        metrics.put("peakAmplitude", round(maxPeak, 6));
        metrics.put("dynamicRangeDb", minRms > 0f ? round((float) (20d * Math.log10(maxRms / minRms)), 2) : null);
        metrics.put("voicedFrameCount", voicedFrames);
        metrics.put("avgPitchHz", voicedFrames > 0 ? round(pitchSum / voicedFrames, 2) : null);
        metrics.put("minPitchHz", voicedFrames > 0 ? round(minPitch, 2) : null);
        metrics.put("maxPitchHz", voicedFrames > 0 ? round(maxPitch, 2) : null);
        metrics.put("pitchRangeHz", voicedFrames > 0 ? round(maxPitch - minPitch, 2) : null);
        metrics.put("avgCrestFactor", crestFramesWithSignal > 0 ? round((float) (crestSum / crestFramesWithSignal), 4) : null);
        metrics.put("maxCrestFactor", crestFramesWithSignal > 0 ? round(maxCrest, 4) : null);
        metrics.put("silenceRatio", round((float) silenceFrames / (float) frameCount, 4));

        float averageRms = (float) (rmsSum / frameCount);
        JSObject phraseMetrics = buildPhraseMetrics(frameRmsValues, averageRms, vocals.sampleRate);
        JSObject pitchStabilityMetrics = buildPitchStabilityMetrics(
            framePitchValues,
            framePitchConfidenceValues,
            voicedFrames,
            frameCount,
            pitchConfidenceSum / frameCount,
            voicedFrames > 0 ? pitchSum / voicedFrames : Float.NaN
        );
        Float robustDynamics = robustDynamicRangeDb(frameRmsValues, averageRms);
        metrics.put("dynamicRangeDbRobust", robustDynamics == null ? null : round(robustDynamics, 2));
        metrics.put("phraseMetrics", phraseMetrics);
        metrics.put("pitchStabilityMetrics", pitchStabilityMetrics);
        metrics.put("analysedStem", "vocals");
        metrics.put("analysisScope", "separated_vocal_stem");
        metrics.put("notImplemented", buildNotImplemented());

        JSObject rawMetrics = buildRawMetrics(metrics);
        JSObject derivedMetrics = buildDerivedMetrics(rawMetrics);
        JSObject issueScores = buildIssueScores(rawMetrics);
        JSObject vocalProfile = buildVocalProfile(rawMetrics, derivedMetrics, issueScores);
        JSObject validation = buildValidationPlaceholder();
        JSObject coachInput = buildCoachInput(context, rawMetrics, derivedMetrics, issueScores, vocalProfile, validation);
        JSObject coachingSummary = buildCoachingSummary(rawMetrics, derivedMetrics);

        JSObject summary = new JSObject();
        summary.put("text", coachingSummary.optString("summary", buildSummary(metrics)));
        summary.put("analysisType", "offline-basic-vocal-metrics");
        summary.put("confidenceLevel", derivedMetrics.optString("confidenceLevel", "moderate"));

        JSObject pitchDoc = buildSeriesDoc("pitch", vocals, pitchFrames);
        JSObject rmsDoc = buildSeriesDoc("rms", vocals, rmsFrames);
        JSObject crestDoc = buildSeriesDoc("crest", vocals, crestFrames);

        File pitchFile = new File(analysisDir, "pitch.json");
        File rmsFile = new File(analysisDir, "rms.json");
        File crestFile = new File(analysisDir, "crest.json");
        File reportFile = new File(analysisDir, "analysis-report.json");
        File coachInputFile = new File(analysisDir, "coach-input.json");

        emit(progressSink, 99, "report", "Writing analysis artifacts");
        writeJson(pitchFile, pitchDoc);
        writeJson(rmsFile, rmsDoc);
        writeJson(crestFile, crestDoc);
        writeJson(coachInputFile, coachInput);

        JSObject report = new JSObject();
        report.put("status", "completed");
        report.put("summary", summary);
        report.put("metrics", metrics);
        report.put("rawMetrics", rawMetrics);
        report.put("derivedMetrics", derivedMetrics);
        report.put("phraseMetrics", rawMetrics.opt("phraseMetrics"));
        report.put("pitchStabilityMetrics", rawMetrics.opt("pitchStabilityMetrics"));
        report.put("issueScores", issueScores);
        report.put("vocalProfile", vocalProfile);
        report.put("coachInput", coachInput);
        report.put("coachOutput", null);
        report.put("validation", validation);
        report.put("notImplemented", rawMetrics.opt("notImplemented"));
        report.put("coachingSummary", coachingSummary);
        report.put("artifacts", buildArtifacts(pitchFile, rmsFile, crestFile, reportFile, coachInputFile));
        writeJson(reportFile, report);

        return new Result(
            pitchFile,
            rmsFile,
            crestFile,
            reportFile,
            coachInputFile,
            metrics,
            rawMetrics,
            derivedMetrics,
            issueScores,
            vocalProfile,
            coachInput,
            validation,
            coachingSummary,
            summary,
            System.currentTimeMillis() - startedAt
        );
    }

    JSObject buildAnalysis(Result result) throws JSONException {
        JSObject timings = new JSObject();
        timings.put("analysisMs", result.analysisMs);

        JSObject analysis = new JSObject();
        analysis.put("status", "completed");
        analysis.put("summary", result.summary);
        analysis.put("metrics", result.metrics);
        analysis.put("rawMetrics", result.rawMetrics);
        analysis.put("derivedMetrics", result.derivedMetrics);
        analysis.put("phraseMetrics", result.rawMetrics.opt("phraseMetrics"));
        analysis.put("pitchStabilityMetrics", result.rawMetrics.opt("pitchStabilityMetrics"));
        analysis.put("issueScores", result.issueScores);
        analysis.put("vocalProfile", result.vocalProfile);
        analysis.put("coachInput", result.coachInput);
        analysis.put("coachOutput", null);
        analysis.put("validation", result.validation);
        analysis.put("notImplemented", result.rawMetrics.opt("notImplemented"));
        analysis.put("coachingSummary", result.coachingSummary);
        analysis.put("artifacts", buildArtifacts(result.pitchFile, result.rmsFile, result.crestFile, result.reportFile, result.coachInputFile));
        analysis.put("timings", timings);
        return analysis;
    }

    JSObject buildAnalysisFailed(String code, String message, String details) throws JSONException {
        JSObject error = new JSObject();
        error.put("code", code);
        error.put("message", message);
        error.put("details", details);

        JSObject analysis = new JSObject();
        analysis.put("status", "failed");
        analysis.put("summary", null);
        analysis.put("metrics", null);
        analysis.put("rawMetrics", null);
        analysis.put("derivedMetrics", null);
        analysis.put("issueScores", null);
        analysis.put("vocalProfile", null);
        analysis.put("coachInput", null);
        analysis.put("coachOutput", null);
        analysis.put("validation", null);
        analysis.put("coachingSummary", null);
        analysis.put("artifacts", buildEmptyArtifacts());
        analysis.put("error", error);
        return analysis;
    }

    private JSObject buildSeriesDoc(String type, WavAudio.AudioBuffer audio, JSONArray frames) throws JSONException {
        JSObject doc = new JSObject();
        doc.put("type", type);
        doc.put("sampleRate", audio.sampleRate);
        doc.put("frameSize", FRAME_SIZE);
        doc.put("hopSize", HOP_SIZE);
        doc.put("frames", frames);
        return doc;
    }

    private JSObject buildArtifacts(File pitchFile, File rmsFile, File crestFile, File reportFile, File coachInputFile) throws JSONException {
        JSObject artifacts = new JSObject();
        artifacts.put("pitch", artifact(pitchFile, "application/json"));
        artifacts.put("rms", artifact(rmsFile, "application/json"));
        artifacts.put("crest", artifact(crestFile, "application/json"));
        artifacts.put("report", artifact(reportFile, "application/json"));
        artifacts.put("coachInput", artifact(coachInputFile, "application/json"));
        return artifacts;
    }

    private JSObject buildEmptyArtifacts() throws JSONException {
        JSObject artifacts = new JSObject();
        artifacts.put("pitch", null);
        artifacts.put("rms", null);
        artifacts.put("crest", null);
        artifacts.put("report", null);
        artifacts.put("coachInput", null);
        return artifacts;
    }

    private JSObject artifact(File file, String mimeType) throws JSONException {
        JSObject artifact = new JSObject();
        artifact.put("path", file.getAbsolutePath());
        artifact.put("uri", file.toURI().toString());
        artifact.put("mimeType", mimeType);
        artifact.put("format", "json");
        return artifact;
    }

    private void writeJson(File file, JSObject object) throws IOException, JSONException {
        try (FileOutputStream outputStream = new FileOutputStream(file)) {
            outputStream.write(object.toString(2).getBytes(StandardCharsets.UTF_8));
        }
    }

    private void emit(ProgressSink progressSink, int percent, String stage, String message) {
        if (progressSink != null) {
            progressSink.onProgress(percent, stage, message);
        }
    }

    private float[] toMono(WavAudio.AudioBuffer audio) {
        float[] mono = new float[audio.frameCount];
        for (int frame = 0; frame < audio.frameCount; frame++) {
            mono[frame] = (audio.channels[0][frame] + audio.channels[1][frame]) * 0.5f;
        }
        return mono;
    }

    private FrameStats computeFrame(float[] mono, int start, int sampleRate) {
        int available = Math.max(0, Math.min(FRAME_SIZE, mono.length - start));
        if (available <= 0) {
            return new FrameStats(0f, 0f, 0f, 0f);
        }

        double sumSquares = 0d;
        float peak = 0f;
        for (int offset = 0; offset < available; offset++) {
            float sample = mono[start + offset];
            sumSquares += sample * sample;
            peak = Math.max(peak, Math.abs(sample));
        }

        float rms = (float) Math.sqrt(sumSquares / available);
        PitchResult pitch = estimatePitch(mono, start, available, sampleRate, rms);
        return new FrameStats(rms, peak, pitch.pitchHz, pitch.confidence);
    }

    private PitchResult estimatePitch(float[] mono, int start, int available, int sampleRate, float rms) {
        if (rms < 0.003f || available < FRAME_SIZE / 2) {
            return new PitchResult(0f, 0f);
        }

        int minLag = Math.max(1, Math.round(sampleRate / MAX_PITCH_HZ));
        int maxLag = Math.min(available - 1, Math.round(sampleRate / MIN_PITCH_HZ));
        float bestCorrelation = 0f;
        int bestLag = -1;

        for (int lag = minLag; lag <= maxLag; lag++) {
            double sum = 0d;
            double energyA = 0d;
            double energyB = 0d;
            int count = available - lag;
            for (int index = 0; index < count; index++) {
                float a = mono[start + index];
                float b = mono[start + index + lag];
                sum += a * b;
                energyA += a * a;
                energyB += b * b;
            }

            double denom = Math.sqrt(energyA * energyB);
            float correlation = denom > 0d ? (float) (sum / denom) : 0f;
            if (correlation > bestCorrelation) {
                bestCorrelation = correlation;
                bestLag = lag;
            }
        }

        if (bestLag <= 0 || bestCorrelation < 0.35f) {
            return new PitchResult(0f, bestCorrelation);
        }

        return new PitchResult((float) sampleRate / bestLag, bestCorrelation);
    }

    private String buildSummary(JSObject metrics) {
        String avgPitch = metrics.isNull("avgPitchHz")
            ? "no stable pitch detected"
            : String.format(Locale.US, "average pitch %.2f Hz", metrics.optDouble("avgPitchHz"));
        return String.format(
            Locale.US,
            "Offline analysis complete: %s, average RMS %.4f, peak amplitude %.4f.",
            avgPitch,
            metrics.optDouble("avgRms"),
            metrics.optDouble("peakAmplitude")
        );
    }

    private JSObject buildPhraseMetrics(float[] rmsValues, float averageRms, int sampleRate) throws JSONException {
        float activeThreshold = Math.max(0.008f, averageRms * 0.35f);
        int minPhraseFrames = Math.max(2, Math.round(0.25f * sampleRate / HOP_SIZE));
        int minGapFrames = Math.max(1, Math.round(0.18f * sampleRate / HOP_SIZE));
        List<PhraseStats> phrases = new ArrayList<>();
        int phraseStart = -1;
        int quietRun = 0;
        int quietGapCount = 0;
        double quietGapSecondsSum = 0d;

        for (int index = 0; index < rmsValues.length; index++) {
            boolean active = rmsValues[index] >= activeThreshold;
            if (active) {
                if (phraseStart < 0) {
                    phraseStart = index;
                }
                quietRun = 0;
            } else if (phraseStart >= 0) {
                quietRun++;
                if (quietRun >= minGapFrames) {
                    int end = index - quietRun;
                    if (end - phraseStart + 1 >= minPhraseFrames) {
                        phrases.add(summarizePhrase(rmsValues, phraseStart, end, sampleRate));
                    }
                    quietGapCount++;
                    quietGapSecondsSum += (double) quietRun * (double) HOP_SIZE / (double) sampleRate;
                    phraseStart = -1;
                    quietRun = 0;
                }
            }
        }

        if (phraseStart >= 0 && rmsValues.length - phraseStart >= minPhraseFrames) {
            phrases.add(summarizePhrase(rmsValues, phraseStart, rmsValues.length - 1, sampleRate));
        }

        double durationSum = 0d;
        double rmsSum = 0d;
        double longest = 0d;
        double shortest = Double.MAX_VALUE;
        for (PhraseStats phrase : phrases) {
            durationSum += phrase.durationSec;
            rmsSum += phrase.averageRms;
            longest = Math.max(longest, phrase.durationSec);
            shortest = Math.min(shortest, phrase.durationSec);
        }
        double averagePhraseRms = phrases.isEmpty() ? Double.NaN : rmsSum / phrases.size();
        double variance = 0d;
        if (!phrases.isEmpty()) {
            for (PhraseStats phrase : phrases) {
                double diff = phrase.averageRms - averagePhraseRms;
                variance += diff * diff;
            }
            variance /= phrases.size();
        }
        double consistencyScore = phrases.isEmpty() || averagePhraseRms <= 0d
            ? Double.NaN
            : Math.max(0d, Math.min(100d, 100d - ((Math.sqrt(variance) / averagePhraseRms) * 120d)));

        JSONArray phraseRows = new JSONArray();
        for (int index = 0; index < phrases.size(); index++) {
            PhraseStats phrase = phrases.get(index);
            JSObject row = new JSObject();
            row.put("index", index + 1);
            row.put("startSec", round((float) phrase.startSec, 3));
            row.put("endSec", round((float) phrase.endSec, 3));
            row.put("durationSec", round((float) phrase.durationSec, 3));
            row.put("averageRms", round((float) phrase.averageRms, 6));
            row.put("peakRms", round((float) phrase.peakRms, 6));
            phraseRows.put(row);
        }

        JSObject metrics = new JSObject();
        metrics.put("phraseCount", phrases.size());
        metrics.put("averagePhraseDurationSec", phrases.isEmpty() ? null : round((float) (durationSum / phrases.size()), 3));
        metrics.put("longestPhraseDurationSec", phrases.isEmpty() ? null : round((float) longest, 3));
        metrics.put("shortestPhraseDurationSec", phrases.isEmpty() ? null : round((float) shortest, 3));
        metrics.put("averagePhraseRms", phrases.isEmpty() ? null : round((float) averagePhraseRms, 6));
        metrics.put("phraseRmsVariance", phrases.isEmpty() ? null : round((float) variance, 8));
        metrics.put("phraseEnergyConsistencyScore", Double.isNaN(consistencyScore) ? null : round((float) consistencyScore, 1));
        metrics.put("phraseEnergyConsistencyLabel", phraseConsistencyLabel(consistencyScore));
        metrics.put("quietGapCount", quietGapCount);
        metrics.put("averageQuietGapSec", quietGapCount > 0 ? round((float) (quietGapSecondsSum / quietGapCount), 3) : null);
        metrics.put("phrases", phraseRows);
        return metrics;
    }

    private PhraseStats summarizePhrase(float[] rmsValues, int startFrame, int endFrame, int sampleRate) {
        double sum = 0d;
        double peak = 0d;
        int count = Math.max(1, endFrame - startFrame + 1);
        for (int index = startFrame; index <= endFrame; index++) {
            sum += rmsValues[index];
            peak = Math.max(peak, rmsValues[index]);
        }
        double startSec = (double) startFrame * (double) HOP_SIZE / (double) sampleRate;
        double endSec = (double) (endFrame * HOP_SIZE + FRAME_SIZE) / (double) sampleRate;
        return new PhraseStats(startSec, endSec, Math.max(0d, endSec - startSec), sum / count, peak);
    }

    private Float robustDynamicRangeDb(float[] rmsValues, float averageRms) {
        float activeThreshold = Math.max(0.008f, averageRms * 0.35f);
        List<Float> activeDb = new ArrayList<>();
        for (float rms : rmsValues) {
            if (rms >= activeThreshold) {
                activeDb.add((float) (20d * Math.log10(Math.max(rms, 0.000001f))));
            }
        }
        if (activeDb.size() < 4) return null;
        float[] sorted = new float[activeDb.size()];
        for (int index = 0; index < activeDb.size(); index++) sorted[index] = activeDb.get(index);
        Arrays.sort(sorted);
        return percentile(sorted, 0.95f) - percentile(sorted, 0.10f);
    }

    private JSObject buildPitchStabilityMetrics(
        float[] pitchValues,
        float[] confidenceValues,
        int voicedFrames,
        int frameCount,
        double meanPitchConfidence,
        float averagePitch
    ) throws JSONException {
        List<Float> usable = new ArrayList<>();
        double confidenceSum = 0d;
        int confidenceCount = 0;
        for (int index = 0; index < pitchValues.length; index++) {
            if (pitchValues[index] > 0f && confidenceValues[index] >= 0.45f) {
                usable.add(pitchValues[index]);
                confidenceSum += confidenceValues[index];
                confidenceCount++;
            }
        }

        Float median = null;
        Float stdHz = null;
        Float stdCents = null;
        if (!usable.isEmpty()) {
            float[] sorted = new float[usable.size()];
            for (int index = 0; index < usable.size(); index++) sorted[index] = usable.get(index);
            Arrays.sort(sorted);
            median = percentile(sorted, 0.50f);
            if (usable.size() > 1 && averagePitch > 0f) {
                double sumSquares = 0d;
                double sumCentsSquares = 0d;
                for (float hz : usable) {
                    double diff = hz - averagePitch;
                    sumSquares += diff * diff;
                    double cents = 1200d * (Math.log(hz / averagePitch) / Math.log(2d));
                    sumCentsSquares += cents * cents;
                }
                stdHz = (float) Math.sqrt(sumSquares / usable.size());
                stdCents = (float) Math.sqrt(sumCentsSquares / usable.size());
            }
        }

        double usableRatio = frameCount > 0 ? (double) usable.size() / (double) frameCount : 0d;
        double usableVoicedRatio = voicedFrames > 0 ? (double) usable.size() / (double) voicedFrames : 0d;
        double meanUsableConfidence = confidenceCount > 0 ? confidenceSum / confidenceCount : meanPitchConfidence;

        JSObject metrics = new JSObject();
        metrics.put("voicedFrameCount", voicedFrames);
        metrics.put("usablePitchFrameCount", usable.size());
        metrics.put("usablePitchFrameRatio", round((float) usableRatio, 4));
        metrics.put("usableVoicedPitchFrameRatio", round((float) usableVoicedRatio, 4));
        metrics.put("meanPitchConfidence", round((float) meanUsableConfidence, 3));
        metrics.put("averagePitchHz", Float.isNaN(averagePitch) ? null : round(averagePitch, 2));
        metrics.put("medianPitchHz", median == null ? null : round(median, 2));
        metrics.put("pitchStdDevHz", stdHz == null ? null : round(stdHz, 2));
        metrics.put("pitchStdDevCents", stdCents == null ? null : round(stdCents, 1));
        metrics.put("pitchTrackVariabilityLabel", pitchVariabilityLabel(stdCents));
        metrics.put("pitchTrackingConfidenceLabel", pitchTrackingConfidenceLabel(usableRatio, meanUsableConfidence));
        return metrics;
    }

    private JSONArray buildNotImplemented() {
        JSONArray values = new JSONArray();
        values.put(notImplemented("Timing accuracy", "No beat grid, target timing, or onset comparison is analysed yet."));
        values.put(notImplemented("Rhythm consistency", "VOX does not yet compare vocal events against rhythm or accompaniment."));
        values.put(notImplemented("Breath noise", "No spectral breath-noise detector is implemented yet."));
        values.put(notImplemented("Breath support", "Current metrics cannot diagnose breath support."));
        values.put(notImplemented("Note-by-note tuning", "VOX does not yet compare pitch frames with a target melody."));
        values.put(notImplemented("Vibrato", "No vibrato-rate or vibrato-depth analysis is implemented yet."));
        values.put(notImplemented("Vocal strain", "Current metrics cannot detect vocal strain."));
        values.put(notImplemented("Resonance", "No formant or resonance analysis is implemented yet."));
        values.put(notImplemented("Diction", "No lyric or consonant clarity analysis is implemented yet."));
        values.put(notImplemented("True vocal range", "Raw pitch extremes are not a vocal range test."));
        return values;
    }

    private JSObject notImplemented(String name, String reason) {
        JSObject item = new JSObject();
        item.put("name", name);
        item.put("status", "Not analysed yet");
        item.put("reason", reason);
        return item;
    }

    private JSObject optMetricObject(JSObject parent, String key) {
        Object value = parent.opt(key);
        return value instanceof JSObject ? (JSObject) value : null;
    }

    private JSObject buildRawMetrics(JSObject metrics) throws JSONException {
        JSObject raw = new JSObject();
        raw.put("averagePitchHz", nullable(metrics, "avgPitchHz"));
        raw.put("avgPitchHz", nullable(metrics, "avgPitchHz"));
        raw.put("pitchMinHz", nullable(metrics, "minPitchHz"));
        raw.put("minPitchHz", nullable(metrics, "minPitchHz"));
        raw.put("pitchMaxHz", nullable(metrics, "maxPitchHz"));
        raw.put("maxPitchHz", nullable(metrics, "maxPitchHz"));
        raw.put("pitchRangeHz", nullable(metrics, "pitchRangeHz"));
        raw.put("averageRms", nullable(metrics, "avgRms"));
        raw.put("peakRms", nullable(metrics, "peakRms"));
        raw.put("minRms", nullable(metrics, "minRms"));
        raw.put("peakAmplitude", nullable(metrics, "peakAmplitude"));
        raw.put("crestFactor", nullable(metrics, "avgCrestFactor"));
        raw.put("avgCrestFactor", nullable(metrics, "avgCrestFactor"));
        raw.put("maxCrestFactor", nullable(metrics, "maxCrestFactor"));
        raw.put("dynamicRangeDb", nullable(metrics, "dynamicRangeDb"));
        raw.put("dynamicRangeDbLegacy", nullable(metrics, "dynamicRangeDb"));
        raw.put("dynamicRangeDbRobust", nullable(metrics, "dynamicRangeDbRobust"));
        raw.put("durationSeconds", nullable(metrics, "durationSec"));
        raw.put("durationSec", nullable(metrics, "durationSec"));
        raw.put("sampleRate", nullable(metrics, "sampleRate"));
        raw.put("frameCount", nullable(metrics, "frameCount"));
        raw.put("voicedFrameCount", nullable(metrics, "voicedFrameCount"));
        raw.put("clippingRisk", metrics.optDouble("peakAmplitude", 0d) >= 0.98d);
        raw.put("silenceRatio", nullable(metrics, "silenceRatio"));
        raw.put("analysedStem", "vocals");
        raw.put("phraseMetrics", metrics.opt("phraseMetrics"));
        raw.put("pitchStabilityMetrics", metrics.opt("pitchStabilityMetrics"));
        raw.put("notImplemented", metrics.opt("notImplemented"));
        return raw;
    }

    private JSObject buildDerivedMetrics(JSObject raw) throws JSONException {
        double pitch = raw.optDouble("averagePitchHz", Double.NaN);
        double rms = raw.optDouble("averageRms", Double.NaN);
        double peak = raw.optDouble("peakAmplitude", Double.NaN);
        double dynamicRange = raw.optDouble("dynamicRangeDbRobust", raw.optDouble("dynamicRangeDb", Double.NaN));
        double crest = raw.optDouble("crestFactor", Double.NaN);
        JSObject phrase = optMetricObject(raw, "phraseMetrics");
        JSObject pitchStability = optMetricObject(raw, "pitchStabilityMetrics");

        JSObject derived = new JSObject();
        derived.put("pitchBandLabel", Double.isNaN(pitch) ? "No stable average pitch detected" : "Around " + hzToNote(pitch));
        derived.put("vocalEnergyLabel", energyLabel(rms));
        derived.put("dynamicsLabel", dynamicsLabel(dynamicRange));
        derived.put("consistencyLabel", phrase != null ? phrase.optString("phraseEnergyConsistencyLabel", consistencyLabel(dynamicRange, crest)) : consistencyLabel(dynamicRange, crest));
        derived.put("phraseEnergyConsistencyLabel", phrase != null ? phrase.optString("phraseEnergyConsistencyLabel", "Not analysed") : "Not analysed");
        derived.put("pitchTrackVariabilityLabel", pitchStability != null ? pitchStability.optString("pitchTrackVariabilityLabel", "Not analysed") : "Not analysed");
        derived.put("pitchTrackingConfidenceLabel", pitchStability != null ? pitchStability.optString("pitchTrackingConfidenceLabel", "Not analysed") : "Not analysed");
        derived.put("clippingRiskLabel", clippingRiskLabel(peak));
        derived.put("levelPeakConfidence", Double.isNaN(rms) || Double.isNaN(peak) ? "low" : "high");
        derived.put("pitchTrackingConfidence", pitchStability != null ? pitchStability.optString("pitchTrackingConfidenceLabel", "limited") : "limited");
        derived.put("confidenceLevel", pitchStability != null ? overallConfidence(pitchStability.optDouble("usablePitchFrameRatio", 0d)) : "moderate");
        return derived;
    }

    private JSObject buildIssueScores(JSObject raw) throws JSONException {
        JSObject phrase = optMetricObject(raw, "phraseMetrics");
        JSObject pitchStability = optMetricObject(raw, "pitchStabilityMetrics");
        double rms = raw.optDouble("averageRms", Double.NaN);
        double peak = raw.optDouble("peakAmplitude", Double.NaN);
        double robustDynamics = raw.optDouble("dynamicRangeDbRobust", Double.NaN);
        double crest = raw.optDouble("crestFactor", Double.NaN);
        double maxCrest = raw.optDouble("maxCrestFactor", crest);
        double silenceRatio = raw.optDouble("silenceRatio", Double.NaN);
        double phraseScore = phrase == null ? Double.NaN : phrase.optDouble("phraseEnergyConsistencyScore", Double.NaN);
        int phraseCount = phrase == null ? 0 : phrase.optInt("phraseCount", 0);
        double pitchStdCents = pitchStability == null ? Double.NaN : pitchStability.optDouble("pitchStdDevCents", Double.NaN);
        double pitchUsableRatio = pitchStability == null ? 0d : pitchStability.optDouble("usablePitchFrameRatio", 0d);
        double pitchConfidence = pitchStability == null ? 0d : pitchStability.optDouble("meanPitchConfidence", 0d);
        boolean pitchEligible = pitchStability != null && pitchUsableRatio >= 0.2d && pitchConfidence >= 0.45d;

        double lowVocalEnergy = Double.isNaN(rms) ? 0d : scoreDescending(rms, 0.02d, 0.06d);
        double peakRisk = Double.isNaN(peak) ? 0d : scoreAscending(peak, 0.85d, 0.98d);
        double wideDynamics = Double.isNaN(robustDynamics) ? 0d : scoreAscending(robustDynamics, 30d, 60d);
        double phraseInconsistency = phraseCount >= 2 && !Double.isNaN(phraseScore) ? clamp(100d - phraseScore) : 0d;
        double pitchVariability = pitchEligible && !Double.isNaN(pitchStdCents) ? scoreAscending(pitchStdCents, 55d, 150d) : 0d;
        double lowPitchConfidence = pitchStability == null ? 100d : Math.max(scoreDescending(pitchUsableRatio, 0.15d, 0.45d), scoreDescending(pitchConfidence, 0.35d, 0.62d));
        double highSilence = Double.isNaN(silenceRatio) ? 0d : scoreAscending(silenceRatio, 0.15d, 0.55d);
        double crestPeakiness = Double.isNaN(crest) ? 0d : Math.max(scoreAscending(crest, 6d, 16d), scoreAscending(maxCrest, 12d, 30d) * 0.8d);

        JSObject scores = new JSObject();
        scores.put("lowVocalEnergyScore", roundScore(lowVocalEnergy));
        scores.put("peakRiskScore", roundScore(peakRisk));
        scores.put("wideDynamicsScore", roundScore(wideDynamics));
        scores.put("phraseInconsistencyScore", roundScore(phraseInconsistency));
        scores.put("pitchVariabilityScore", roundScore(pitchVariability));
        scores.put("lowPitchConfidenceScore", roundScore(lowPitchConfidence));
        scores.put("highSilenceRatioScore", roundScore(highSilence));
        scores.put("crestPeakinessScore", roundScore(crestPeakiness));
        scores.put("pitchVariabilityEligible", pitchEligible);
        scores.put("phraseInconsistencyEligible", phraseCount >= 2);
        scores.put("primaryFocus", selectPrimaryFocus(scores));
        scores.put("secondaryFocus", selectSecondaryFocus(scores, scores.optString("primaryFocus")));
        scores.put("overallPriority", roundScore(maxActionableScore(scores)));
        return scores;
    }

    private JSObject buildVocalProfile(JSObject raw, JSObject derived, JSObject issueScores) throws JSONException {
        JSObject phrase = optMetricObject(raw, "phraseMetrics");
        JSObject pitchStability = optMetricObject(raw, "pitchStabilityMetrics");
        double pitch = raw.optDouble("averagePitchHz", Double.NaN);
        String archetype = selectArchetype(raw, issueScores);
        JSObject profile = new JSObject();
        profile.put("archetype", archetype);
        profile.put("pitchCentreSummary", Double.isNaN(pitch) ? "no stable average pitch centre" : "average pitch centre around " + hzToNote(pitch));
        profile.put("energyProfile", derived.optString("vocalEnergyLabel", "Measured") + " vocal energy");
        profile.put("peakProfile", derived.optString("clippingRiskLabel", "Measured peak level").toLowerCase(Locale.US));
        profile.put("dynamicsProfile", derived.optString("dynamicsLabel", "Measured dynamics").toLowerCase(Locale.US));
        profile.put("phraseProfile", phrase == null ? "phrase consistency not available" : phrase.optString("phraseEnergyConsistencyLabel", "measured phrase energy").toLowerCase(Locale.US));
        profile.put("pitchTrackProfile", pitchStability == null ? "pitch tracking unavailable" : pitchStability.optString("pitchTrackVariabilityLabel", "pitch track measured").toLowerCase(Locale.US));
        profile.put("confidenceProfile", "level and peak metrics are stronger than pitch metrics");
        profile.put("mainTakeaway", focusLabel(issueScores.optString("primaryFocus", "maintenance_refinement")));
        profile.put("safeStrengths", safeStrengths(raw, derived, phrase));
        profile.put("safeFocusAreas", safeFocusAreas(issueScores));
        return profile;
    }

    private JSObject buildCoachInput(JSObject context, JSObject raw, JSObject derived, JSObject issueScores, JSObject vocalProfile, JSObject validation) throws JSONException {
        JSObject input = new JSObject();
        input.put("version", "coach-input-v1");
        input.put("jobId", context == null ? null : context.opt("jobId"));
        input.put("songTitle", context == null ? null : context.opt("songTitle"));
        input.put("analysedStem", raw.optString("analysedStem", "vocals"));
        input.put("durationSeconds", raw.opt("durationSeconds"));
        input.put("inputSizeMb", context == null ? null : context.opt("inputSizeMb"));
        input.put("rawMetrics", raw);
        input.put("derivedMetrics", derived);
        input.put("phraseMetrics", raw.opt("phraseMetrics"));
        input.put("pitchStabilityMetrics", raw.opt("pitchStabilityMetrics"));
        input.put("confidence", buildConfidence(raw, derived));
        input.put("issueScores", issueScores);
        input.put("vocalProfile", vocalProfile);
        input.put("notImplemented", raw.opt("notImplemented"));
        input.put("safetyRules", buildSafetyRules());
        input.put("historyComparison", null);
        input.put("userIntent", context == null ? "practice" : context.optString("userIntent", "practice"));
        input.put("styleContext", context == null ? null : context.opt("styleContext"));
        input.put("validation", validation);
        return input;
    }

    private JSObject buildValidationPlaceholder() throws JSONException {
        JSObject validation = new JSObject();
        validation.put("isValid", true);
        validation.put("blockedClaims", new JSONArray());
        validation.put("fallbackUsed", false);
        validation.put("validatorVersion", "native-placeholder-v1");
        return validation;
    }

    private JSObject buildConfidence(JSObject raw, JSObject derived) throws JSONException {
        JSObject confidence = new JSObject();
        confidence.put("levelPeakConfidence", derived.optString("levelPeakConfidence", "low"));
        confidence.put("pitchTrackingConfidence", derived.optString("pitchTrackingConfidenceLabel", "limited"));
        confidence.put("overallCoachingConfidence", derived.optString("confidenceLevel", "limited"));
        confidence.put("scope", "separated_vocal_stem");
        return confidence;
    }

    private JSObject buildSafetyRules() throws JSONException {
        JSObject rules = new JSObject();
        JSONArray allowed = new JSONArray();
        allowed.put("average detected pitch centre");
        allowed.put("vocal energy from RMS");
        allowed.put("peak level and clipping risk");
        allowed.put("robust dynamic movement");
        allowed.put("phrase energy consistency");
        allowed.put("pitch-track variability only when confidence is adequate");
        JSONArray forbidden = new JSONArray();
        forbidden.put("timing judgement");
        forbidden.put("breath support diagnosis");
        forbidden.put("breath noise diagnosis");
        forbidden.put("note-level tuning judgement");
        forbidden.put("vocal strain diagnosis");
        forbidden.put("vibrato judgement");
        forbidden.put("resonance judgement");
        forbidden.put("diction judgement");
        forbidden.put("true vocal range claim");
        rules.put("allowedClaims", allowed);
        rules.put("forbiddenClaims", forbidden);
        return rules;
    }

    private JSONArray safeStrengths(JSObject raw, JSObject derived, JSObject phrase) {
        JSONArray strengths = new JSONArray();
        double peak = raw.optDouble("peakAmplitude", Double.NaN);
        double rms = raw.optDouble("averageRms", Double.NaN);
        double dynamicRange = raw.optDouble("dynamicRangeDbRobust", Double.NaN);
        if (!Double.isNaN(peak) && peak < 0.9d) strengths.put("safe peak level");
        if (!Double.isNaN(rms) && rms >= 0.035d) strengths.put("usable vocal energy");
        if (!Double.isNaN(dynamicRange) && dynamicRange >= 18d && dynamicRange <= 45d) strengths.put("controlled dynamic range");
        if (phrase != null && phrase.optDouble("phraseEnergyConsistencyScore", 0d) >= 70d) strengths.put("steady phrase energy");
        if (!Double.isNaN(raw.optDouble("averagePitchHz", Double.NaN))) strengths.put("measurable average pitch centre");
        if (strengths.length() == 0) strengths.put("separated vocal stem was analysed successfully");
        return strengths;
    }

    private JSONArray safeFocusAreas(JSObject issueScores) {
        JSONArray focus = new JSONArray();
        String primary = issueScores.optString("primaryFocus", "maintenance_refinement");
        String secondary = issueScores.optString("secondaryFocus", "");
        focus.put(focusLabel(primary));
        if (!secondary.isEmpty() && !"maintenance_refinement".equals(secondary)) focus.put(focusLabel(secondary));
        return focus;
    }

    private String selectArchetype(JSObject raw, JSObject scores) {
        JSObject phrase = optMetricObject(raw, "phraseMetrics");
        double duration = raw.optDouble("durationSeconds", Double.NaN);
        double silence = raw.optDouble("silenceRatio", Double.NaN);
        int phraseCount = phrase == null ? 0 : phrase.optInt("phraseCount", 0);
        if (!Double.isNaN(duration) && duration < 30d) return "short_clip_limited_data";
        if ((!Double.isNaN(silence) && silence >= 0.55d) || phraseCount == 0) return "sparse_or_quiet_take";
        if (scores.optDouble("lowPitchConfidenceScore", 0d) >= 65d) return "pitch_limited";
        if (scores.optDouble("peakRiskScore", 0d) >= 55d || scores.optDouble("crestPeakinessScore", 0d) >= 70d) return "peak_heavy";
        if (scores.optDouble("phraseInconsistencyScore", 0d) >= 45d && scores.optDouble("wideDynamicsScore", 0d) >= 35d) return "phrase_inconsistent";
        if (scores.optDouble("wideDynamicsScore", 0d) >= 65d) return "wide_dynamics";
        if (scores.optDouble("lowVocalEnergyScore", 0d) >= 55d && scores.optDouble("peakRiskScore", 0d) < 30d) return "low_energy_safe_peak";
        if (scores.optBoolean("pitchVariabilityEligible", false) && scores.optDouble("pitchVariabilityScore", 0d) >= 55d) return "pitch_variable";
        return "balanced_usable_take";
    }

    private String selectPrimaryFocus(JSObject scores) {
        String focus = "maintenance_refinement";
        double best = 35d;
        String[] keys = {
            "lowVocalEnergyScore",
            "peakRiskScore",
            "wideDynamicsScore",
            "phraseInconsistencyScore",
            "pitchVariabilityScore",
            "crestPeakinessScore"
        };
        for (String key : keys) {
            if (!isIssueEligible(key, scores)) continue;
            double score = scores.optDouble(key, 0d);
            if (score > best) {
                best = score;
                focus = focusForScoreKey(key);
            }
        }
        if (focus.equals("maintenance_refinement") && scores.optDouble("lowPitchConfidenceScore", 0d) >= 65d) {
            return "pitch_tracking_limited";
        }
        return focus;
    }

    private String selectSecondaryFocus(JSObject scores, String primary) {
        String focus = "";
        double best = 35d;
        String[] keys = {
            "lowVocalEnergyScore",
            "peakRiskScore",
            "wideDynamicsScore",
            "phraseInconsistencyScore",
            "pitchVariabilityScore",
            "crestPeakinessScore",
            "lowPitchConfidenceScore"
        };
        for (String key : keys) {
            if (!isIssueEligible(key, scores) && !"lowPitchConfidenceScore".equals(key)) continue;
            String candidate = "lowPitchConfidenceScore".equals(key) ? "pitch_tracking_limited" : focusForScoreKey(key);
            if (candidate.equals(primary)) continue;
            double score = scores.optDouble(key, 0d);
            if (score > best) {
                best = score;
                focus = candidate;
            }
        }
        return focus;
    }

    private double maxActionableScore(JSObject scores) {
        double max = 0d;
        String[] keys = {
            "lowVocalEnergyScore",
            "peakRiskScore",
            "wideDynamicsScore",
            "phraseInconsistencyScore",
            "pitchVariabilityScore",
            "crestPeakinessScore"
        };
        for (String key : keys) {
            if (isIssueEligible(key, scores)) max = Math.max(max, scores.optDouble(key, 0d));
        }
        return max;
    }

    private boolean isIssueEligible(String key, JSObject scores) {
        if ("pitchVariabilityScore".equals(key)) return scores.optBoolean("pitchVariabilityEligible", false);
        if ("phraseInconsistencyScore".equals(key)) return scores.optBoolean("phraseInconsistencyEligible", false);
        if ("wideDynamicsScore".equals(key)) return scores.optDouble("wideDynamicsScore", 0d) > 0d;
        return true;
    }

    private String focusForScoreKey(String key) {
        if ("lowVocalEnergyScore".equals(key)) return "low_vocal_energy";
        if ("peakRiskScore".equals(key)) return "peak_control";
        if ("wideDynamicsScore".equals(key)) return "wide_dynamic_movement";
        if ("phraseInconsistencyScore".equals(key)) return "phrase_volume_consistency";
        if ("pitchVariabilityScore".equals(key)) return "pitch_track_variability";
        if ("crestPeakinessScore".equals(key)) return "sudden_peak_control";
        return "maintenance_refinement";
    }

    private String focusLabel(String focus) {
        if ("low_vocal_energy".equals(focus)) return "bring the vocal slightly more forward";
        if ("peak_control".equals(focus)) return "control sudden loud peaks";
        if ("wide_dynamic_movement".equals(focus)) return "smooth wide dynamic movement";
        if ("phrase_volume_consistency".equals(focus)) return "smooth phrase-level volume";
        if ("pitch_track_variability".equals(focus)) return "review pitch-track steadiness estimate";
        if ("sudden_peak_control".equals(focus)) return "reduce sudden peaks versus sustained level";
        if ("pitch_tracking_limited".equals(focus)) return "treat pitch feedback as limited for this take";
        return "maintenance and refinement";
    }

    private double scoreAscending(double value, double start, double full) {
        if (Double.isNaN(value)) return 0d;
        if (value <= start) return 0d;
        if (value >= full) return 100d;
        return ((value - start) / (full - start)) * 100d;
    }

    private double scoreDescending(double value, double full, double zero) {
        if (Double.isNaN(value)) return 0d;
        if (value <= full) return 100d;
        if (value >= zero) return 0d;
        return ((zero - value) / (zero - full)) * 100d;
    }

    private double clamp(double value) {
        return Math.max(0d, Math.min(100d, value));
    }

    private int roundScore(double value) {
        return (int) Math.round(clamp(value));
    }

    private JSObject buildCoachingSummary(JSObject raw, JSObject derived) throws JSONException {
        double pitch = raw.optDouble("averagePitchHz", Double.NaN);
        double minPitch = raw.optDouble("pitchMinHz", Double.NaN);
        double maxPitch = raw.optDouble("pitchMaxHz", Double.NaN);
        double rms = raw.optDouble("averageRms", Double.NaN);
        double peak = raw.optDouble("peakAmplitude", Double.NaN);
        double legacyDynamicRange = raw.optDouble("dynamicRangeDb", Double.NaN);
        double dynamicRange = raw.optDouble("dynamicRangeDbRobust", legacyDynamicRange);
        double crest = raw.optDouble("crestFactor", Double.NaN);
        boolean clippingRisk = raw.optBoolean("clippingRisk", false);
        JSObject phrase = optMetricObject(raw, "phraseMetrics");
        JSObject pitchStability = optMetricObject(raw, "pitchStabilityMetrics");

        JSONArray strengths = new JSONArray();
        JSONArray topIssues = new JSONArray();
        JSONArray evidence = new JSONArray();
        JSONArray recommendedDrills = new JSONArray();

        if (!Double.isNaN(peak) && peak < 0.9d) {
            strengths.put("No clipping risk detected; the peak level stayed below the danger zone.");
            evidence.put(String.format(Locale.US, "Peak amplitude was %.4f, below clipping level.", peak));
        } else if (!Double.isNaN(peak) && peak < 0.98d) {
            strengths.put("Peak level is usable, but loud phrases are worth watching.");
            topIssues.put("Peak level is close enough to clipping that loud moments should be controlled.");
            evidence.put(String.format(Locale.US, "Peak amplitude was %.4f; this is below clipping but high enough to monitor.", peak));
        } else if (clippingRisk) {
            topIssues.put("Clipping risk detected from very high peak level.");
            evidence.put(String.format(Locale.US, "Peak amplitude was %.4f, close to digital clipping.", peak));
        }

        if (!Double.isNaN(rms)) {
            evidence.put(String.format(Locale.US, "Average RMS was %.4f, which VOX treats as %s vocal energy.", rms, derived.optString("vocalEnergyLabel", "measured")));
            if (rms < 0.035d) {
                topIssues.put("Vocal energy may be low; projection or mic distance is worth checking.");
            } else {
                strengths.put("The vocal level stayed within a usable analysis range.");
            }
        }

        if (!Double.isNaN(dynamicRange)) {
            String dynamicsEvidence = Double.isNaN(legacyDynamicRange)
                ? String.format(Locale.US, "Dynamics: %.1f dB robust estimate — %s.", dynamicRange, derived.optString("dynamicsLabel", "measured dynamic movement").toLowerCase(Locale.US))
                : String.format(Locale.US, "Dynamics: %.1f dB robust / %.1f dB legacy — %s.", dynamicRange, legacyDynamicRange, derived.optString("dynamicsLabel", "measured dynamic movement").toLowerCase(Locale.US));
            evidence.put(dynamicsEvidence);
            if (dynamicRange > 45d) {
                topIssues.put("Main focus: smoother phrase-level volume.");
            } else if (dynamicRange < 18d) {
                topIssues.put("Main focus: add more controlled dynamic contrast.");
            } else {
                strengths.put("The performance had controlled dynamic movement.");
            }
        }

        if (!Double.isNaN(pitch)) {
            evidence.put(String.format(Locale.US, "Average detected pitch was %.1f Hz, around %s. This is the average pitch in this recording, not your full vocal range.", pitch, hzToNote(pitch)));
            strengths.put("Pitch centre was measurable from the separated vocal stem.");
        } else {
            topIssues.put("Pitch centre could not be measured reliably from the available stem.");
        }

        if (pitchStability != null) {
            evidence.put(String.format(
                Locale.US,
                "Pitch track variability: %s (%s tracking confidence).",
                pitchStability.optString("pitchTrackVariabilityLabel", "measured"),
                pitchStability.optString("pitchTrackingConfidenceLabel", "limited")
            ));
        }

        if (!Double.isNaN(crest)) {
            evidence.put(String.format(Locale.US, "Average crest factor was %.2f, which helps describe sudden peaks versus sustained level.", crest));
            if (crest > 12d) {
                topIssues.put("Sudden peaks may be stronger than the sustained vocal level.");
            }
        }

        if (phrase != null) {
            String phraseLabel = phrase.optString("phraseEnergyConsistencyLabel", "measured");
            evidence.put(String.format(
                Locale.US,
                "Phrase consistency: %s across %d detected phrase(s).",
                phraseLabel,
                phrase.optInt("phraseCount", 0)
            ));
            if (phrase.optDouble("phraseEnergyConsistencyScore", 100d) < 55d) {
                topIssues.put("Main focus: phrase volume consistency.");
            } else if (phrase.optInt("phraseCount", 0) > 0) {
                strengths.put("Phrase-level energy was measurable from the separated vocal.");
            }
        }

        if (topIssues.length() == 0) {
            topIssues.put("No critical technical issues detected. Suggested focus: smoother phrase-level volume.");
        }

        recommendedDrills.put(selectPrimaryDrill(rms, peak, dynamicRange, crest));
        recommendedDrills.put(pitchAwarenessDrill(pitch));

        JSObject coaching = new JSObject();
        coaching.put("summary", buildCoachingText(raw, derived));
        coaching.put("strengths", strengths);
        coaching.put("mainFocus", nextPracticeFocus(rms, peak, dynamicRange));
        coaching.put("topIssues", topIssues);
        coaching.put("evidence", evidence);
        coaching.put("recommendedDrills", recommendedDrills);
        coaching.put("nextPracticeFocus", nextPracticeFocus(rms, peak, dynamicRange));
        coaching.put("notImplemented", buildNotImplemented());
        coaching.put(
            "confidenceNote",
            "Level and peak metrics are reliable for the separated vocal stem. Pitch feedback is more limited because pitch tracking is autocorrelation-based and no target melody is analysed. Timing, breath noise, note-level tuning, strain, vibrato, resonance, diction, and true vocal range are not included."
        );
        return coaching;
    }

    private String buildCoachingText(JSObject raw, JSObject derived) {
        double pitch = raw.optDouble("averagePitchHz", Double.NaN);
        String pitchText = Double.isNaN(pitch) ? "no stable average pitch centre" : "an average pitch area around " + hzToNote(pitch);
        String mainFocus = nextPracticeFocus(
            raw.optDouble("averageRms", Double.NaN),
            raw.optDouble("peakAmplitude", Double.NaN),
            raw.optDouble("dynamicRangeDbRobust", raw.optDouble("dynamicRangeDb", Double.NaN))
        ).toLowerCase(Locale.US);
        return String.format(
            Locale.US,
            "VOX separated and analysed your vocal. The take shows %s, %s vocal energy, %s, and %s. Main focus: %s.",
            pitchText,
            derived.optString("vocalEnergyLabel", "measured").toLowerCase(Locale.US),
            derived.optString("clippingRiskLabel", "measured peak level").toLowerCase(Locale.US),
            derived.optString("dynamicsLabel", "measured dynamics").toLowerCase(Locale.US),
            mainFocus
        );
    }

    private JSObject selectPrimaryDrill(double rms, double peak, double dynamicRange, double crest) throws JSONException {
        if (!Double.isNaN(peak) && peak >= 0.9d) {
            return drill(
                "Peak Control Drill",
                "Sing the loudest phrase at 80% effort.",
                "Keep the vowel open and avoid shouting.",
                "Record again and check whether the peak level drops while the tone stays clear."
            );
        }
        if (!Double.isNaN(rms) && rms < 0.035d) {
            return drill(
                "Forward Tone Projection Drill",
                "Sing the chorus line on 'mum' or 'nay'.",
                "Aim for clear tone without pushing.",
                "Record again and compare whether the average vocal energy rises safely."
            );
        }
        if (!Double.isNaN(dynamicRange) && dynamicRange > 45d) {
            return drill(
                "Volume Ladder Drill",
                "Sing the same phrase at 40%, 60%, and 80% volume.",
                "Keep pitch steady while changing loudness.",
                "Repeat three times and aim for smoother jumps between levels."
            );
        }
        if (!Double.isNaN(dynamicRange) && dynamicRange < 18d) {
            return drill(
                "Dynamic Contrast Drill",
                "Sing one phrase gently, then repeat with a clear but controlled lift.",
                "Avoid forcing the louder version.",
                "Listen back for expressive contrast without harsh peaks."
            );
        }
        if (!Double.isNaN(crest) && crest > 12d) {
            return drill(
                "Phrase Smoothing Drill",
                "Sing the phrase legato on one vowel before adding lyrics.",
                "Reduce sudden accents that jump out of the line.",
                "Record again and listen for smoother phrase energy."
            );
        }
        return drill(
            "Phrase Control Drill",
            "Sing the hook at a comfortable medium volume.",
            "Keep tone clear and volume even across the phrase.",
            "Repeat three times and compare consistency."
        );
    }

    private JSObject pitchAwarenessDrill(double pitch) throws JSONException {
        String note = Double.isNaN(pitch) ? "your comfortable centre" : hzToNote(pitch);
        return drill(
            "Pitch-Centre Awareness Drill",
            "Hum gently around " + note + ", then sing a short phrase from the song.",
            "Listen for whether the phrase settles back to the same centre.",
            "This checks pitch awareness only; it is not a full tuning score."
        );
    }

    private JSObject drill(String name, String stepOne, String stepTwo, String stepThree) throws JSONException {
        JSObject drill = new JSObject();
        JSONArray steps = new JSONArray();
        steps.put(stepOne);
        steps.put(stepTwo);
        steps.put(stepThree);
        drill.put("name", name);
        drill.put("steps", steps);
        return drill;
    }

    private String nextPracticeFocus(double rms, double peak, double dynamicRange) {
        if (!Double.isNaN(peak) && peak >= 0.9d) return "controlling loud peaks without losing intensity";
        if (!Double.isNaN(rms) && rms < 0.035d) return "building clearer forward vocal energy";
        if (!Double.isNaN(dynamicRange) && dynamicRange > 45d) return "smoothing volume consistency while keeping expression";
        if (!Double.isNaN(dynamicRange) && dynamicRange < 18d) return "adding more expressive dynamic contrast";
        return "keeping phrase control consistent across the take";
    }

    private String energyLabel(double rms) {
        if (Double.isNaN(rms)) return "Not analysed";
        if (rms < 0.035d) return "Low";
        if (rms < 0.09d) return "Moderate";
        return "High";
    }

    private String dynamicsLabel(double dynamicRangeDb) {
        if (Double.isNaN(dynamicRangeDb)) return "Not analysed";
        if (dynamicRangeDb < 18d) return "Narrow dynamic range detected";
        if (dynamicRangeDb > 45d) return "Wide dynamic range detected";
        return "Controlled dynamic range detected";
    }

    private String consistencyLabel(double dynamicRangeDb, double crestFactor) {
        if (!Double.isNaN(dynamicRangeDb) && dynamicRangeDb > 45d) return "Volume consistency may vary";
        if (!Double.isNaN(crestFactor) && crestFactor > 12d) return "Sudden peaks may stand out";
        if (!Double.isNaN(dynamicRangeDb) && dynamicRangeDb < 18d) return "Delivery may be dynamically even";
        return "No major consistency warning from available metrics";
    }

    private String clippingRiskLabel(double peak) {
        if (Double.isNaN(peak)) return "Peak level not analysed";
        if (peak >= 0.98d) return "Clipping risk";
        if (peak >= 0.9d) return "Watch loud peaks";
        return "Safe peak level";
    }

    private String phraseConsistencyLabel(double score) {
        if (Double.isNaN(score)) return "Not enough phrases detected";
        if (score >= 78d) return "Consistent phrase energy";
        if (score >= 55d) return "Moderate phrase consistency";
        return "Phrase volume varies";
    }

    private String pitchVariabilityLabel(Float stdCents) {
        if (stdCents == null) return "Not enough usable pitch frames";
        if (stdCents < 35f) return "Low pitch-track variability";
        if (stdCents < 85f) return "Moderate pitch-track variability";
        return "High pitch-track variability";
    }

    private String pitchTrackingConfidenceLabel(double usableRatio, double meanConfidence) {
        if (usableRatio >= 0.45d && meanConfidence >= 0.62d) return "good";
        if (usableRatio >= 0.2d && meanConfidence >= 0.45d) return "limited";
        return "low";
    }

    private String overallConfidence(double usablePitchRatio) {
        if (usablePitchRatio >= 0.45d) return "moderate-high";
        if (usablePitchRatio >= 0.2d) return "moderate";
        return "limited";
    }

    private float percentile(float[] sortedValues, float percentile) {
        if (sortedValues.length == 0) return Float.NaN;
        float clamped = Math.max(0f, Math.min(1f, percentile));
        float rawIndex = clamped * (sortedValues.length - 1);
        int lower = (int) Math.floor(rawIndex);
        int upper = (int) Math.ceil(rawIndex);
        if (lower == upper) return sortedValues[lower];
        float weight = rawIndex - lower;
        return sortedValues[lower] + ((sortedValues[upper] - sortedValues[lower]) * weight);
    }

    private Object nullable(JSObject object, String key) {
        return object.isNull(key) ? null : object.opt(key);
    }

    private String hzToNote(double hz) {
        if (Double.isNaN(hz) || hz <= 0d) {
            return "unknown";
        }
        String[] names = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
        int midi = (int) Math.round(69d + (12d * (Math.log(hz / 440d) / Math.log(2d))));
        int noteIndex = Math.floorMod(midi, 12);
        int octave = (midi / 12) - 1;
        return names[noteIndex] + octave;
    }

    private float round(float value, int places) {
        double scale = Math.pow(10d, places);
        return (float) (Math.round(value * scale) / scale);
    }

    private static class FrameStats {
        final float rms;
        final float peak;
        final float pitchHz;
        final float pitchConfidence;

        FrameStats(float rms, float peak, float pitchHz, float pitchConfidence) {
            this.rms = rms;
            this.peak = peak;
            this.pitchHz = pitchHz;
            this.pitchConfidence = pitchConfidence;
        }
    }

    private static class PitchResult {
        final float pitchHz;
        final float confidence;

        PitchResult(float pitchHz, float confidence) {
            this.pitchHz = pitchHz;
            this.confidence = confidence;
        }
    }

    private static class PhraseStats {
        final double startSec;
        final double endSec;
        final double durationSec;
        final double averageRms;
        final double peakRms;

        PhraseStats(double startSec, double endSec, double durationSec, double averageRms, double peakRms) {
            this.startSec = startSec;
            this.endSec = endSec;
            this.durationSec = durationSec;
            this.averageRms = averageRms;
            this.peakRms = peakRms;
        }
    }
}
