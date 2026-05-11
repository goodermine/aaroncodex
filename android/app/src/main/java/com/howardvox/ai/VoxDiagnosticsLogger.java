package com.howardvox.ai;

import android.app.ActivityManager;
import android.content.Context;
import android.os.Debug;

import com.getcapacitor.JSObject;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

class VoxDiagnosticsLogger {
    private static final String CSV_HEADER = "jobId,chunkIndex,totalChunks,onnxChunkElapsedMs,overlapAddElapsedMs,wavFlushElapsedMs,chunkTotalElapsedMs,writtenStemFrames,javaHeapUsedMb,javaHeapMaxMb,nativeHeapAllocatedMb,availableSystemMemMb,timestamp\n";

    private final Context context;
    private final String jobId;
    private final File diagnosticsDir;
    private final File eventsFile;
    private final File chunkTimingsFile;
    private final File runtimeSummaryFile;
    private final File currentPhaseFile;
    private final File stallFile;
    private final File errorFile;
    private final String songName;
    private final String sourceType;
    private final long durationMs;
    private final long startedAtMs;

    private int lastKnownChunk = 0;
    private int totalChunks = 0;
    private int currentChunk = 0;
    private String lastKnownStage = "queued";
    private String currentPhase = "queued";
    private JSObject lastChunkTiming = null;
    private long lastChunkProgressMs;
    private long currentPhaseStartedMs;
    private boolean stallRecorded = false;

    VoxDiagnosticsLogger(Context context, String jobId, File jobDir, JSObject input) throws IOException {
        this.context = context.getApplicationContext();
        this.jobId = jobId;
        this.diagnosticsDir = new File(jobDir, "diagnostics");
        this.eventsFile = new File(diagnosticsDir, "events.ndjson");
        this.chunkTimingsFile = new File(diagnosticsDir, "chunk_timings.csv");
        this.runtimeSummaryFile = new File(diagnosticsDir, "runtime_summary.json");
        this.currentPhaseFile = new File(diagnosticsDir, "current_phase.json");
        this.stallFile = new File(diagnosticsDir, "stall.json");
        this.errorFile = new File(diagnosticsDir, "error.txt");
        this.songName = input.optString("originalFileName", input.optString("title", "unknown"));
        this.sourceType = input.optString("sourceType", "unknown");
        this.durationMs = input.optLong("durationMs", -1L);
        this.startedAtMs = System.currentTimeMillis();
        this.lastChunkProgressMs = startedAtMs;
        this.currentPhaseStartedMs = startedAtMs;

        ensureDir(diagnosticsDir);
        if (!chunkTimingsFile.exists() || chunkTimingsFile.length() == 0L) {
            appendText(chunkTimingsFile, CSV_HEADER);
        }
        event("job_created", "queued", null);
        phase("queued", 0, 0);
        writeRuntimeSummary("queued", null);
    }

    synchronized void phase(String phase, int chunkIndex, int totalChunks) {
        try {
            long now = System.currentTimeMillis();
            this.currentPhase = defaultString(phase, "unknown");
            this.currentChunk = Math.max(0, chunkIndex);
            if (totalChunks > 0) {
                this.totalChunks = totalChunks;
            }
            this.currentPhaseStartedMs = now;
            writeCurrentPhase(now);
        } catch (Exception ignored) {
            // Diagnostics should never break the audio pipeline.
        }
    }

    synchronized void event(String type, String status, JSObject detail) {
        try {
            if (detail != null) {
                if (detail.has("plannedChunkCount")) {
                    totalChunks = detail.optInt("plannedChunkCount", totalChunks);
                }
                if (detail.has("chunkIndex")) {
                    lastKnownChunk = Math.max(lastKnownChunk, detail.optInt("chunkIndex", lastKnownChunk));
                    totalChunks = detail.optInt("totalChunks", totalChunks);
                }
            }
            JSObject event = baseEvent(type, status);
            if (detail != null && detail.length() > 0) {
                event.put("detail", new JSONObject(detail.toString()));
            }
            appendText(eventsFile, event.toString() + "\n");
        } catch (Exception ignored) {
            // Diagnostics should never break the audio pipeline.
        }
    }

    synchronized void recordProgress(
        int percent,
        String stage,
        String message,
        JSObject detail,
        boolean cancelled,
        boolean foregroundServiceActive
    ) {
        lastKnownStage = defaultString(stage, "processing");
        try {
            JSObject eventDetail = new JSObject();
            eventDetail.put("percent", percent);
            eventDetail.put("message", defaultString(message, ""));
            eventDetail.put("cancelled", cancelled);
            eventDetail.put("foregroundServiceActive", foregroundServiceActive);
            if (detail != null && detail.length() > 0) {
                eventDetail.put("progressDetail", new JSONObject(detail.toString()));
            }
            event("progress", cancelled ? "cancelled" : "running", eventDetail);

            if (detail != null && detail.has("chunkIndex")) {
                int chunkIndex = detail.optInt("chunkIndex", lastKnownChunk);
                if (chunkIndex > lastKnownChunk) {
                    lastKnownChunk = chunkIndex;
                    currentChunk = chunkIndex;
                    totalChunks = detail.optInt("totalChunks", totalChunks);
                    lastChunkProgressMs = System.currentTimeMillis();
                    lastChunkTiming = new JSObject(detail.toString());
                    appendChunkTiming(detail);
                    currentPhase = "chunk_complete";
                    currentPhaseStartedMs = lastChunkProgressMs;
                    writeCurrentPhase(lastChunkProgressMs);
                }
            }
            writeRuntimeSummary(cancelled ? "cancelled" : "running", detail);
        } catch (Exception ignored) {
            // Best effort diagnostic record.
        }
    }

    synchronized void finalStatus(String status, JSObject detail) {
        event("final_status", status, detail);
        writeRuntimeSummary(status, detail);
    }

    synchronized void error(String status, String code, String message, String details) {
        try {
            String text = "status=" + defaultString(status, "failed")
                + "\ncode=" + defaultString(code, "UNKNOWN")
                + "\nmessage=" + defaultString(message, "")
                + "\ndetails=" + defaultString(details, "")
                + "\ntimestamp=" + isoNow()
                + "\n";
            appendText(errorFile, text);

            JSObject detail = new JSObject();
            detail.put("code", defaultString(code, "UNKNOWN"));
            detail.put("message", defaultString(message, ""));
            detail.put("details", defaultString(details, ""));
            event("error", defaultString(status, "failed"), detail);
            writeRuntimeSummary(defaultString(status, "failed"), detail);
        } catch (Exception ignored) {
            // Best effort diagnostic record.
        }
    }

    synchronized void writeStallIfNeeded(long stallTimeoutMs, boolean cancelled, boolean foregroundServiceActive) {
        if (stallRecorded || cancelled) {
            return;
        }

        long now = System.currentTimeMillis();
        long elapsedMs = now - lastChunkProgressMs;
        if (elapsedMs < stallTimeoutMs) {
            return;
        }

        try {
            writeCurrentPhase(now);
            JSObject stall = new JSObject();
            stall.put("jobId", jobId);
            stall.put("songName", songName);
            stall.put("sourceType", sourceType);
            stall.put("lastCompletedChunk", lastKnownChunk);
            stall.put("currentChunk", currentChunk);
            stall.put("totalChunks", totalChunks);
            stall.put("lastKnownStage", lastKnownStage);
            JSONObject currentPhaseObject = readCurrentPhaseObject();
            stall.put("currentPhase", currentPhaseObject == null ? JSONObject.NULL : currentPhaseObject);
            stall.put("elapsedMsSinceLastChunkComplete", elapsedMs);
            stall.put("elapsedMsInCurrentPhase", Math.max(0L, now - currentPhaseStartedMs));
            stall.put("lastSuccessfulChunkTiming", lastChunkTiming == null ? JSONObject.NULL : new JSONObject(lastChunkTiming.toString()));
            stall.put("currentlySuspectedPhase", defaultString(currentPhase, suspectedPhase()));
            stall.put("cancelled", cancelled);
            stall.put("foregroundServiceActive", foregroundServiceActive);
            stall.put("timestamp", isoNow());
            putRuntime(stall);
            writeBytes(stallFile, stall.toString(2).getBytes(StandardCharsets.UTF_8));
            stallRecorded = true;
            event("stall", "stalled", stall);
            writeRuntimeSummary("stalled", stall);
        } catch (Exception ignored) {
            // Best effort diagnostic record.
        }
    }

    private void appendChunkTiming(JSObject detail) throws IOException {
        Runtime runtime = Runtime.getRuntime();
        long usedHeap = runtime.totalMemory() - runtime.freeMemory();
        long maxHeap = runtime.maxMemory();
        ActivityManager.MemoryInfo memoryInfo = memoryInfo();
        String row = csv(jobId)
            + "," + detail.optInt("chunkIndex", 0)
            + "," + detail.optInt("totalChunks", 0)
            + "," + detail.optLong("onnxChunkElapsedMs", -1L)
            + "," + detail.optLong("overlapAddElapsedMs", -1L)
            + "," + detail.optLong("wavFlushElapsedMs", -1L)
            + "," + detail.optLong("chunkTotalElapsedMs", detail.optLong("chunkElapsedMs", -1L))
            + "," + detail.optInt("writtenStemFrames", 0)
            + "," + mb(usedHeap)
            + "," + mb(maxHeap)
            + "," + mb(Debug.getNativeHeapAllocatedSize())
            + "," + mb(memoryInfo == null ? -1L : memoryInfo.availMem)
            + "," + csv(isoNow())
            + "\n";
        appendText(chunkTimingsFile, row);
    }

    private void writeRuntimeSummary(String status, JSObject latestDetail) {
        try {
            JSObject summary = new JSObject();
            summary.put("jobId", jobId);
            summary.put("songName", songName);
            summary.put("sourceType", sourceType);
            summary.put("durationMs", durationMs >= 0L ? durationMs : JSONObject.NULL);
            summary.put("status", defaultString(status, "running"));
            summary.put("lastKnownStage", lastKnownStage);
            summary.put("lastKnownChunk", lastKnownChunk);
            summary.put("currentChunk", currentChunk);
            summary.put("currentPhase", defaultString(currentPhase, "unknown"));
            summary.put("totalChunks", totalChunks);
            summary.put("startedAt", isoNow(startedAtMs));
            summary.put("updatedAt", isoNow());
            summary.put("elapsedMs", Math.max(0L, System.currentTimeMillis() - startedAtMs));
            summary.put("lastChunkTiming", lastChunkTiming == null ? JSONObject.NULL : new JSONObject(lastChunkTiming.toString()));
            summary.put("latestDetail", latestDetail == null ? JSONObject.NULL : new JSONObject(latestDetail.toString()));
            putRuntime(summary);
            writeBytes(runtimeSummaryFile, summary.toString(2).getBytes(StandardCharsets.UTF_8));
        } catch (Exception ignored) {
            // Best effort diagnostic record.
        }
    }

    private JSObject baseEvent(String type, String status) throws JSONException {
        JSObject event = new JSObject();
        event.put("timestamp", isoNow());
        event.put("jobId", jobId);
        event.put("songName", songName);
        event.put("sourceType", sourceType);
        event.put("durationMs", durationMs >= 0L ? durationMs : JSONObject.NULL);
        event.put("type", type);
        event.put("status", defaultString(status, "running"));
        event.put("lastKnownStage", lastKnownStage);
        event.put("lastKnownChunk", lastKnownChunk);
        event.put("totalChunks", totalChunks);
        putRuntime(event);
        return event;
    }

    private void putRuntime(JSObject object) throws JSONException {
        Runtime runtime = Runtime.getRuntime();
        long usedHeap = runtime.totalMemory() - runtime.freeMemory();
        long freeHeap = runtime.maxMemory() - usedHeap;
        object.put("javaHeapUsedBytes", usedHeap);
        object.put("javaHeapFreeBytes", Math.max(0L, freeHeap));
        object.put("javaHeapMaxBytes", runtime.maxMemory());
        object.put("javaHeapUsedMb", mb(usedHeap));
        object.put("javaHeapMaxMb", mb(runtime.maxMemory()));
        object.put("nativeHeapAllocatedBytes", Debug.getNativeHeapAllocatedSize());
        object.put("nativeHeapFreeBytes", Debug.getNativeHeapFreeSize());
        object.put("nativeHeapAllocatedMb", mb(Debug.getNativeHeapAllocatedSize()));

        ActivityManager.MemoryInfo memoryInfo = memoryInfo();
        if (memoryInfo != null) {
            object.put("systemAvailableMemoryBytes", memoryInfo.availMem);
            object.put("availableSystemMemMb", mb(memoryInfo.availMem));
            object.put("systemLowMemory", memoryInfo.lowMemory);
        }
    }

    private void writeCurrentPhase(long now) throws IOException, JSONException {
        JSObject phase = new JSObject();
        phase.put("jobId", jobId);
        phase.put("chunkIndex", currentChunk);
        phase.put("totalChunks", totalChunks);
        phase.put("phase", defaultString(currentPhase, "unknown"));
        phase.put("phaseStartedAt", isoNow(currentPhaseStartedMs));
        phase.put("lastUpdatedAt", isoNow(now));
        phase.put("elapsedMsInPhase", Math.max(0L, now - currentPhaseStartedMs));
        putRuntime(phase);
        writeBytes(currentPhaseFile, phase.toString(2).getBytes(StandardCharsets.UTF_8));
    }

    private JSONObject readCurrentPhaseObject() {
        try {
            if (currentPhaseFile.exists()) {
                byte[] bytes = new byte[(int) currentPhaseFile.length()];
                try (FileInputStream inputStream = new FileInputStream(currentPhaseFile)) {
                    int offset = 0;
                    while (offset < bytes.length) {
                        int read = inputStream.read(bytes, offset, bytes.length - offset);
                        if (read < 0) {
                            break;
                        }
                        offset += read;
                    }
                }
                return new JSONObject(new String(bytes, StandardCharsets.UTF_8));
            }
        } catch (Exception ignored) {
            // Fall through to an in-memory snapshot.
        }

        try {
            JSObject fallback = new JSObject();
            fallback.put("jobId", jobId);
            fallback.put("chunkIndex", currentChunk);
            fallback.put("totalChunks", totalChunks);
            fallback.put("phase", defaultString(currentPhase, "unknown"));
            fallback.put("phaseStartedAt", isoNow(currentPhaseStartedMs));
            fallback.put("lastUpdatedAt", isoNow());
            fallback.put("elapsedMsInPhase", Math.max(0L, System.currentTimeMillis() - currentPhaseStartedMs));
            putRuntime(fallback);
            return new JSONObject(fallback.toString());
        } catch (Exception ignored) {
            return null;
        }
    }

    private ActivityManager.MemoryInfo memoryInfo() {
        ActivityManager activityManager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        if (activityManager == null) {
            return null;
        }
        ActivityManager.MemoryInfo info = new ActivityManager.MemoryInfo();
        activityManager.getMemoryInfo(info);
        return info;
    }

    private String suspectedPhase() {
        if (lastChunkTiming == null) {
            return defaultString(lastKnownStage, "unknown");
        }
        long onnx = lastChunkTiming.optLong("onnxChunkElapsedMs", -1L);
        long overlap = lastChunkTiming.optLong("overlapAddElapsedMs", -1L);
        long flush = lastChunkTiming.optLong("wavFlushElapsedMs", -1L);
        if (flush >= onnx && flush >= overlap) return "wav_flush";
        if (overlap >= onnx) return "overlap_add";
        return "onnx";
    }

    private static void ensureDir(File dir) throws IOException {
        if (!dir.exists() && !dir.mkdirs()) {
            throw new IOException("Could not create diagnostics directory: " + dir.getAbsolutePath());
        }
    }

    private static void appendText(File file, String text) throws IOException {
        ensureDir(file.getParentFile());
        try (FileWriter writer = new FileWriter(file, true)) {
            writer.write(text);
        }
    }

    private static void writeBytes(File file, byte[] bytes) throws IOException {
        ensureDir(file.getParentFile());
        try (FileOutputStream outputStream = new FileOutputStream(file)) {
            outputStream.write(bytes);
        }
    }

    private static String csv(String value) {
        String safe = defaultString(value, "");
        if (!safe.contains(",") && !safe.contains("\"") && !safe.contains("\n")) {
            return safe;
        }
        return "\"" + safe.replace("\"", "\"\"") + "\"";
    }

    private static String defaultString(String value, String fallback) {
        return value == null || value.isEmpty() ? fallback : value;
    }

    private static double mb(long bytes) {
        return bytes < 0L ? -1d : Math.round((bytes / 1024d / 1024d) * 100d) / 100d;
    }

    private static String isoNow() {
        return isoNow(System.currentTimeMillis());
    }

    private static String isoNow(long timestampMs) {
        java.text.SimpleDateFormat format = new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", java.util.Locale.US);
        format.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
        return format.format(new java.util.Date(timestampMs));
    }
}
