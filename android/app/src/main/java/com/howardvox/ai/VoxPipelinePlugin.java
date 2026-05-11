package com.howardvox.ai;

import android.Manifest;
import android.app.Activity;
import android.app.ActivityManager;
import android.content.ActivityNotFoundException;
import android.content.ContentResolver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.media.MediaMetadataRetriever;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.net.Uri;
import android.os.Build;
import android.os.Debug;
import android.os.PowerManager;
import android.provider.OpenableColumns;
import android.provider.Settings;
import android.util.Base64;

import androidx.core.content.FileProvider;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONException;
import org.json.JSONArray;
import org.json.JSONObject;

import androidx.activity.result.ActivityResult;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Date;
import java.util.Set;
import java.util.Locale;
import java.util.TimeZone;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

@CapacitorPlugin(name = "VoxPipeline")
public class VoxPipelinePlugin extends Plugin {
    private static final String PIPELINE_VERSION = "vox-android-local-v1";
    private static final long MAX_UPLOAD_BYTES = 100L * 1024L * 1024L;
    private static final long MAX_BRIDGE_UPLOAD_BYTES = 15L * 1024L * 1024L;
    private static final long MAX_ANDROID_AUDIO_DURATION_MS = 255_000L;
    private static final long DIAGNOSTIC_STALL_TIMEOUT_MS = 90_000L;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final ScheduledExecutorService watchdogExecutor = Executors.newSingleThreadScheduledExecutor();
    private final Set<String> cancelledJobs = ConcurrentHashMap.newKeySet();
    private final ConcurrentHashMap<String, Long> jobStartTimes = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Integer> lastProgressPercent = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Long> lastProgressWriteMs = new ConcurrentHashMap<>();
    private volatile String activeJobId = null;
    private volatile PowerManager.WakeLock pipelineWakeLock = null;

    @PluginMethod
    public void analyzeSong(PluginCall call) {
        String dataBase64 = call.getString("dataBase64");
        if (dataBase64 == null || dataBase64.isEmpty()) {
            call.reject("Missing audio payload for local Android execution.");
            return;
        }

        String jobId = createJobId();
        File jobDir = getJobDir(jobId);
        File inputDir = new File(jobDir, "input");
        File stemsDir = new File(jobDir, "stems");
        File analysisDir = new File(jobDir, "analysis");
        String createdAt = isoNow();
        jobStartTimes.put(jobId, System.currentTimeMillis());

        try {
            ensureDir(inputDir);
            ensureDir(stemsDir);
            ensureDir(analysisDir);

            String originalFileName = defaultString(call.getString("fileName"), "audio-upload.bin");
            String mimeType = defaultString(call.getString("mimeType"), "application/octet-stream");
            byte[] audioBytes = Base64.decode(dataBase64, Base64.DEFAULT);
            if (audioBytes.length > MAX_BRIDGE_UPLOAD_BYTES) {
                call.reject("Android local bridge upload is limited to 15 MB. Use the native audio picker for larger files.");
                return;
            }
            if (audioBytes.length > MAX_UPLOAD_BYTES) {
                call.reject("Android local execution accepts files up to 100 MB.");
                return;
            }

            File inputFile = new File(inputDir, "original" + safeExtension(originalFileName, mimeType));
            writeBytes(inputFile, audioBytes);

            JSObject manifest = createPreparedJob(
                jobId,
                createdAt,
                inputFile,
                originalFileName,
                mimeType,
                audioBytes.length,
                defaultString(call.getString("title"), originalFileName),
                defaultString(call.getString("notes"), ""),
                defaultString(call.getString("sourceType"), "android-local"),
                defaultString(call.getString("originalSourceFileName"), originalFileName),
                defaultString(call.getString("originalSourceMimeType"), mimeType),
                false
            );
            call.resolve(manifest);
        } catch (Exception error) {
            call.reject("Failed to create Android local VOX job: " + error.getMessage(), error);
        }
    }

    @PluginMethod
    public void pickAndAnalyzeSong(PluginCall call) {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("audio/*");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        startActivityForResult(call, intent, "handlePickedAudio");
    }

    @ActivityCallback
    private void handlePickedAudio(PluginCall call, ActivityResult result) {
        if (call == null) {
            return;
        }

        if (result.getResultCode() != Activity.RESULT_OK || result.getData() == null || result.getData().getData() == null) {
            call.reject("No audio file was selected.");
            return;
        }

        Uri uri = result.getData().getData();
        String jobId = createJobId();
        String createdAt = isoNow();
        jobStartTimes.put(jobId, System.currentTimeMillis());

        try {
            File jobDir = getJobDir(jobId);
            File inputDir = new File(jobDir, "input");
            File stemsDir = new File(jobDir, "stems");
            File analysisDir = new File(jobDir, "analysis");
            ensureDir(inputDir);
            ensureDir(stemsDir);
            ensureDir(analysisDir);

            ContentResolver resolver = getContext().getContentResolver();
            String originalFileName = queryDisplayName(resolver, uri);
            String mimeType = defaultString(resolver.getType(uri), "application/octet-stream");
            if (originalFileName == null || originalFileName.isEmpty()) {
                originalFileName = "selected-audio" + safeExtension(null, mimeType);
            }

            File inputFile = new File(inputDir, "original" + safeExtension(originalFileName, mimeType));
            long declaredSizeBytes = querySizeBytes(resolver, uri);
            long sizeBytes = declaredSizeBytes;
            if (declaredSizeBytes <= MAX_UPLOAD_BYTES) {
                sizeBytes = copyUriToFile(resolver, uri, inputFile);
            }

            JSObject manifest = createPreparedJob(
                jobId,
                createdAt,
                inputFile,
                originalFileName,
                mimeType,
                sizeBytes,
                defaultString(call.getString("title"), originalFileName),
                defaultString(call.getString("notes"), ""),
                defaultString(call.getString("sourceType"), "native picker"),
                originalFileName,
                mimeType,
                declaredSizeBytes > MAX_UPLOAD_BYTES
            );
            call.resolve(manifest);
        } catch (Exception error) {
            call.reject("Failed to import selected Android audio file: " + error.getMessage(), error);
        }
    }

    @PluginMethod
    public void getJob(PluginCall call) {
        String jobId = call.getString("jobId");
        if (jobId == null || jobId.isEmpty()) {
            call.reject("jobId is required.");
            return;
        }

        try {
            String json = readText(getManifestFile(jobId));
            call.resolve(new JSObject(json));
        } catch (Exception error) {
            call.reject("Job not found: " + jobId, error);
        }
    }

    @PluginMethod
    public void saveCoachArtifacts(PluginCall call) {
        String jobId = call.getString("jobId");
        if (jobId == null || jobId.isEmpty()) {
            call.reject("jobId is required.");
            return;
        }

        try {
            File analysisDir = new File(getJobDir(jobId), "analysis");
            ensureDir(analysisDir);

            File coachInputFile = new File(analysisDir, "coach-input.json");
            File coachOutputFile = new File(analysisDir, "coach-output.json");
            File coachValidationFile = new File(analysisDir, "coach-validation.json");

            JSObject coachInput = call.getObject("coachInput");
            JSObject coachOutput = call.getObject("coachOutput");
            JSObject validation = call.getObject("validation");
            if (coachOutput == null || validation == null) {
                call.reject("coachOutput and validation are required.");
                return;
            }

            if (coachInput != null) {
                writeBytes(coachInputFile, coachInput.toString(2).getBytes(StandardCharsets.UTF_8));
            }
            writeBytes(coachOutputFile, coachOutput.toString(2).getBytes(StandardCharsets.UTF_8));
            writeBytes(coachValidationFile, validation.toString(2).getBytes(StandardCharsets.UTF_8));

            File manifestFile = getManifestFile(jobId);
            if (manifestFile.exists()) {
                JSONObject manifest = new JSONObject(readText(manifestFile));
                JSONObject analysis = manifest.optJSONObject("analysis");
                if (analysis != null) {
                    analysis.put("coachOutput", new JSONObject(coachOutput.toString()));
                    analysis.put("validation", new JSONObject(validation.toString()));
                    JSONObject artifacts = analysis.optJSONObject("artifacts");
                    if (artifacts == null) {
                        artifacts = new JSONObject();
                        analysis.put("artifacts", artifacts);
                    }
                    if (coachInput != null) artifacts.put("coachInput", jsonArtifact(coachInputFile, "application/json"));
                    artifacts.put("coachOutput", jsonArtifact(coachOutputFile, "application/json"));
                    artifacts.put("coachValidation", jsonArtifact(coachValidationFile, "application/json"));
                    writeManifest(jobId, new JSObject(manifest.toString()));
                }
            }

            JSObject result = new JSObject();
            result.put("coachOutputPath", coachOutputFile.getAbsolutePath());
            result.put("coachValidationPath", coachValidationFile.getAbsolutePath());
            call.resolve(result);
        } catch (Exception error) {
            call.reject("Failed to save coaching artifacts: " + error.getMessage(), error);
        }
    }

    @PluginMethod
    public void getArtifact(PluginCall call) {
        String jobId = call.getString("jobId");
        String artifactKey = call.getString("artifactKey");
        if (jobId == null || artifactKey == null) {
            call.reject("jobId and artifactKey are required.");
            return;
        }

        try {
            JSONObject manifest = new JSONObject(readText(getManifestFile(jobId)));
            JSONObject artifact = findArtifact(manifest, artifactKey);
            if (artifact == null) {
                call.reject("Artifact not found: " + artifactKey);
                return;
            }

            File artifactFile = new File(artifact.getString("path"));
            JSObject result = new JSObject();
            result.put("uri", artifactFile.toURI().toString());
            result.put("mimeType", artifact.optString("mimeType", "audio/" + artifact.optString("format", "wav")));
            call.resolve(result);
        } catch (Exception error) {
            call.reject("Failed to resolve artifact: " + artifactKey, error);
        }
    }

    @PluginMethod
    public void getLatestJob(PluginCall call) {
        try {
            File latestManifest = findLatestManifestFile();
            if (latestManifest == null) {
                call.reject("No Android local VOX jobs found.");
                return;
            }
            call.resolve(new JSObject(readText(latestManifest)));
        } catch (Exception error) {
            call.reject("Failed to recover latest Android VOX job: " + error.getMessage(), error);
        }
    }

    @PluginMethod
    public void exportDiagnostics(PluginCall call) {
        String jobId = call.getString("jobId");
        try {
            if (jobId == null || jobId.isEmpty()) {
                File latestManifest = findLatestManifestFile();
                if (latestManifest == null) {
                    call.reject("No Android local VOX jobs found.");
                    return;
                }
                jobId = latestManifest.getParentFile().getParentFile().getName();
            }

            File zipFile = createDiagnosticsZip(jobId);
            Uri contentUri = FileProvider.getUriForFile(getContext(), getContext().getPackageName() + ".fileprovider", zipFile);

            Intent shareIntent = new Intent(Intent.ACTION_SEND);
            shareIntent.setType("application/zip");
            shareIntent.putExtra(Intent.EXTRA_STREAM, contentUri);
            shareIntent.putExtra(Intent.EXTRA_SUBJECT, "HOWARD VOX diagnostics " + jobId);
            shareIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            Intent chooser = Intent.createChooser(shareIntent, "Export HOWARD VOX diagnostics");
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(chooser);

            JSObject result = new JSObject();
            result.put("jobId", jobId);
            result.put("path", zipFile.getAbsolutePath());
            result.put("uri", contentUri.toString());
            result.put("mimeType", "application/zip");
            result.put("shared", true);
            call.resolve(result);
        } catch (Exception error) {
            call.reject("Failed to export Android VOX diagnostics: " + error.getMessage(), error);
        }
    }

    @PluginMethod
    public void cancelJob(PluginCall call) {
        String jobId = call.getString("jobId");
        if (jobId == null || jobId.isEmpty()) {
            call.reject("jobId is required.");
            return;
        }

        try {
            cancelledJobs.add(jobId);
            JSONObject manifest = new JSONObject(readText(getManifestFile(jobId)));
            markCancelled(manifest);
            writeManifest(jobId, new JSObject(manifest.toString()));
            call.resolve(new JSObject(manifest.toString()));
        } catch (Exception error) {
            call.reject("Failed to cancel job: " + jobId, error);
        }
    }

    @PluginMethod
    public void resetAppData(PluginCall call) {
        if (activeJobId != null) {
            call.reject("A job is currently running. Cancel the job before resetting.");
            return;
        }

        try {
            releasePipelineWakeLock();
            stopForegroundProcessing();
            cancelledJobs.clear();
            jobStartTimes.clear();
            lastProgressPercent.clear();
            lastProgressWriteMs.clear();

            File voxFilesDir = new File(getContext().getFilesDir(), "vox");
            File diagnosticsCacheDir = new File(getContext().getCacheDir(), "vox-diagnostics");
            boolean filesCleared = deleteRecursively(voxFilesDir);
            boolean diagnosticsCleared = deleteRecursively(diagnosticsCacheDir);

            JSObject result = new JSObject();
            result.put("filesDir", voxFilesDir.getAbsolutePath());
            result.put("diagnosticsCacheDir", diagnosticsCacheDir.getAbsolutePath());
            result.put("filesCleared", filesCleared);
            result.put("diagnosticsCleared", diagnosticsCleared);
            result.put("downloadsNote", "Diagnostics ZIP files already exported to Downloads are outside app-private storage and may need to be removed manually.");
            call.resolve(result);
        } catch (Exception error) {
            call.reject("Failed to reset Howard VOX app data: " + error.getMessage(), error);
        }
    }

    @PluginMethod
    public void getBackgroundProcessingStatus(PluginCall call) {
        try {
            call.resolve(buildBackgroundProcessingStatus("status_checked"));
        } catch (Exception error) {
            call.reject("Failed to read Android background processing status: " + error.getMessage(), error);
        }
    }

    @PluginMethod
    public void requestBackgroundProcessingAccess(PluginCall call) {
        try {
            String action = "already_ready";
            if (!hasNotificationPermission()) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && getActivity() != null) {
                    getActivity().requestPermissions(new String[] { Manifest.permission.POST_NOTIFICATIONS }, 4107);
                    action = "notification_permission_requested";
                } else {
                    action = "notification_permission_unavailable";
                }
            } else if (!isIgnoringBatteryOptimizations()) {
                action = openBatteryOptimizationApproval();
            }

            call.resolve(buildBackgroundProcessingStatus(action));
        } catch (Exception error) {
            call.reject("Failed to request Android background processing access: " + error.getMessage(), error);
        }
    }

    @Override
    protected void handleOnDestroy() {
        if (activeJobId == null) {
            releasePipelineWakeLock();
            watchdogExecutor.shutdownNow();
            executor.shutdownNow();
        }
    }

    private void runSeparationJob(String jobId, String createdAt, File inputFile, String mimeType, String inputJson) {
        activeJobId = jobId;
        String separatorDiagnostics = "";
        VoxDiagnosticsLogger diagnosticsLogger = null;
        ScheduledFuture<?> watchdog = null;
        try {
            if (isCancelled(jobId)) {
                return;
            }

            JSObject input = new JSObject(inputJson);
            diagnosticsLogger = new VoxDiagnosticsLogger(getContext(), jobId, getJobDir(jobId), input);
            VoxDiagnosticsLogger loggerRef = diagnosticsLogger;
            watchdog = watchdogExecutor.scheduleAtFixedRate(
                () -> loggerRef.writeStallIfNeeded(DIAGNOSTIC_STALL_TIMEOUT_MS, isCancelled(jobId), jobId.equals(activeJobId)),
                15L,
                15L,
                TimeUnit.SECONDS
            );
            acquirePipelineWakeLock(jobId);
            updateForegroundProcessing(jobId, 1, "preflight", "Preparing Howard VOX background processing");
            JSObject diagnostics = buildSeparatorDiagnostics(inputFile, mimeType, input, "preflight");
            separatorDiagnostics = diagnostics.toString();
            diagnosticsLogger.event("preflight", "running", diagnostics);
            writeProgressManifest(
                jobId,
                createdAt,
                "processing",
                input,
                buildStages("completed", "not_required", "processing", "pending", "pending"),
                buildSeparationPending("processing"),
                buildAnalysisPlaceholder(),
                new JSONArray(),
                3,
                "preflight",
                "Checking Android separator memory budget",
                diagnostics,
                true
            );

            AndroidOnnxSeparator separator = new AndroidOnnxSeparator(getContext());
            AndroidOnnxSeparator.ProgressSink separationProgress = (percent, stage, message, detail) -> {
                try {
                    loggerRef.recordProgress(percent, stage, message, detail, isCancelled(jobId), jobId.equals(activeJobId));
                    writeProgressManifest(
                        jobId,
                        createdAt,
                        "processing",
                        input,
                        buildStages("completed", "not_required", "processing", "pending", "pending"),
                        buildSeparationPending("processing"),
                        buildAnalysisPlaceholder(),
                        new JSONArray(),
                        percent,
                        stage,
                        message,
                        detail,
                        false
                    );
                } catch (Exception ignored) {
                    // The durable manifest will be updated at the next pipeline checkpoint.
                }
            };
            AndroidOnnxSeparator.PhaseSink separationPhase = (phase, chunkIndex, totalChunks) ->
                loggerRef.phase(phase, chunkIndex, totalChunks);
            AndroidOnnxSeparator.Result result = separator.separate(
                inputFile,
                mimeType,
                new File(getJobDir(jobId), "stems"),
                () -> isCancelled(jobId),
                separationProgress,
                separationPhase
            );
            if (isCancelled(jobId)) {
                diagnosticsLogger.finalStatus("cancelled", null);
                return;
            }

            JSObject separationCompleted = buildSeparationCompleted(separator, result);
            diagnosticsLogger.event("separation_completed", "running", separationCompleted);
            JSObject analyzingManifest = buildManifest(
                jobId,
                createdAt,
                "processing",
                input,
                buildStages("completed", "not_required", "completed", "processing", "pending"),
                separationCompleted,
                buildAnalysisPlaceholder("processing"),
                new JSONArray(),
                buildProgress(jobId, 90, "analyze", "Starting offline vocal metrics analysis")
            );
            writeManifest(jobId, analyzingManifest);

            VoxAnalysisEngine analysisEngine = new VoxAnalysisEngine();
            try {
                VoxAnalysisEngine.ProgressSink analysisProgress = (percent, stage, message) -> {
                    try {
                        loggerRef.recordProgress(percent, stage, message, null, isCancelled(jobId), jobId.equals(activeJobId));
                        writeProgressManifest(
                            jobId,
                            createdAt,
                            "processing",
                            input,
                            buildStages("completed", "not_required", "completed", "processing", "pending"),
                            separationCompleted,
                            buildAnalysisPlaceholder("processing"),
                            new JSONArray(),
                            percent,
                            stage,
                            message,
                            false
                        );
                    } catch (Exception ignored) {
                        // The terminal manifest will surface the final analysis result.
                    }
                };
                VoxAnalysisEngine.Result analysisResult = analysisEngine.analyze(
                    result.vocalsFile,
                    new File(getJobDir(jobId), "analysis"),
                    buildAnalysisContext(jobId, input),
                    analysisProgress
                );
                if (isCancelled(jobId)) {
                    diagnosticsLogger.finalStatus("cancelled", null);
                    return;
                }

                JSObject completedManifest = buildManifest(
                    jobId,
                    createdAt,
                    "completed",
                    input,
                    buildStages("completed", "not_required", "completed", "completed", "completed"),
                    separationCompleted,
                    analysisEngine.buildAnalysis(analysisResult),
                    new JSONArray(),
                    buildProgress(jobId, 100, "completed", "Separation and offline analysis completed")
                );
                writeManifest(jobId, completedManifest);
                diagnosticsLogger.finalStatus("completed", completedManifest);
            } catch (Exception analysisError) {
                JSONArray warnings = new JSONArray()
                    .put("Separation completed, but offline analysis failed: " + defaultString(analysisError.getMessage(), analysisError.toString()));
                JSObject completedWithAnalysisFailure = buildManifest(
                    jobId,
                    createdAt,
                    "completed",
                    input,
                    buildStages("completed", "not_required", "completed", "failed", "pending"),
                    separationCompleted,
                    analysisEngine.buildAnalysisFailed(
                        "ANDROID_LOCAL_ANALYSIS_FAILED",
                        defaultString(analysisError.getMessage(), "Offline Android analysis failed."),
                        analysisError.toString()
                    ),
                    warnings,
                    buildProgress(jobId, 100, "completed", "Separation completed; analysis failed. See warnings.")
                );
                writeManifest(jobId, completedWithAnalysisFailure);
                diagnosticsLogger.error(
                    "completed",
                    "ANDROID_LOCAL_ANALYSIS_FAILED",
                    defaultString(analysisError.getMessage(), "Offline Android analysis failed."),
                    analysisError.toString()
                );
                diagnosticsLogger.finalStatus("completed", completedWithAnalysisFailure);
            }
        } catch (VoxSeparationException error) {
            if (diagnosticsLogger != null) {
                diagnosticsLogger.error("failed", error.getCode(), error.getMessage(), error.getDetails());
            }
            writeFailedManifest(jobId, createdAt, inputJson, error.getCode(), error.getMessage(), error.getDetails());
        } catch (OutOfMemoryError error) {
            if (diagnosticsLogger != null) {
                diagnosticsLogger.error("failed", "ANDROID_LOCAL_OUT_OF_MEMORY", "Android local separator exhausted its available memory while separating vocals.", error.toString());
            }
            writeFailedManifest(
                jobId,
                createdAt,
                inputJson,
                "ANDROID_LOCAL_OUT_OF_MEMORY",
                "Android local separator exhausted its available memory while separating vocals.",
                error.toString() + "; diagnostics=" + separatorDiagnostics
            );
        } catch (Exception error) {
            if (diagnosticsLogger != null) {
                diagnosticsLogger.error(
                    "failed",
                    "ANDROID_LOCAL_SEPARATION_FAILED",
                    error.getMessage() != null ? error.getMessage() : "Native Android separation failed.",
                    error.toString()
                );
            }
            writeFailedManifest(
                jobId,
                createdAt,
                inputJson,
                "ANDROID_LOCAL_SEPARATION_FAILED",
                error.getMessage() != null ? error.getMessage() : "Native Android separation failed.",
                error.toString()
            );
        } finally {
            if (watchdog != null) {
                watchdog.cancel(false);
            }
            releasePipelineWakeLock();
            stopForegroundProcessing();
            if (jobId.equals(activeJobId)) {
                activeJobId = null;
            }
        }
    }

    private void writeFailedManifest(
        String jobId,
        String createdAt,
        String inputJson,
        String errorCode,
        String errorMessage,
        String errorDetails
    ) {
        try {
            if (isCancelled(jobId)) {
                return;
            }

            JSObject failedManifest = buildManifest(
                jobId,
                createdAt,
                "failed",
                new JSObject(inputJson),
                buildStages("completed", "not_required", "failed", "pending", "pending"),
                buildSeparationFailed(errorCode, errorMessage, errorDetails),
                buildAnalysisPlaceholder(),
                new JSONArray(),
                buildFailureProgress(jobId, errorMessage)
            );
            writeManifest(jobId, failedManifest);
        } catch (Exception ignored) {
            // The upload call has already resolved; polling will surface the last durable manifest.
        }
    }

    private JSObject createPreparedJob(
        String jobId,
        String createdAt,
        File inputFile,
        String originalFileName,
        String mimeType,
        long sizeBytes,
        String title,
        String notes,
        String sourceType,
        String originalSourceFileName,
        String originalSourceMimeType,
        boolean skipDurationProbe
    ) throws IOException, JSONException {
        long durationMs = skipDurationProbe ? -1L : readDurationMs(inputFile);
        JSObject input = buildInputValues(
            title,
            notes,
            sourceType,
            originalFileName,
            inputFile,
            mimeType,
            sizeBytes,
            originalSourceFileName,
            originalSourceMimeType,
            durationMs
        );

        if (sizeBytes > MAX_UPLOAD_BYTES) {
            JSObject failedManifest = buildRejectedManifest(
                jobId,
                createdAt,
                input,
                "ANDROID_LOCAL_FILE_TOO_LARGE",
                "This APK build accepts audio files up to 100 MB.",
                "sizeBytes=" + sizeBytes + "; maxBytes=" + MAX_UPLOAD_BYTES
            );
            writeManifest(jobId, failedManifest);
            return failedManifest;
        }

        if (durationMs > MAX_ANDROID_AUDIO_DURATION_MS) {
            JSObject failedManifest = buildRejectedManifest(
                jobId,
                createdAt,
                input,
                "ANDROID_LOCAL_AUDIO_TOO_LONG",
                "This APK build currently supports songs up to about 4 minutes. Longer full-song mobile separation needs the next streaming optimization.",
                "durationMs=" + durationMs + "; maxDurationMs=" + MAX_ANDROID_AUDIO_DURATION_MS
            );
            writeManifest(jobId, failedManifest);
            return failedManifest;
        }

        JSObject queuedManifest = buildManifest(
            jobId,
            createdAt,
            "queued",
            input,
            buildStages("completed", "not_required", "pending", "pending", "pending"),
            buildSeparationPending("pending"),
            buildAnalysisPlaceholder(),
            new JSONArray(),
            buildProgress(jobId, 0, "queued", queuedMessage(jobId))
        );
        writeManifest(jobId, queuedManifest);

        executor.execute(() -> runSeparationJob(jobId, createdAt, inputFile, mimeType, input.toString()));
        return queuedManifest;
    }

    private JSObject buildRejectedManifest(
        String jobId,
        String createdAt,
        JSObject input,
        String errorCode,
        String errorMessage,
        String errorDetails
    ) throws JSONException {
        return buildManifest(
            jobId,
            createdAt,
            "failed",
            input,
            buildStages("completed", "not_required", "failed", "pending", "pending"),
            buildSeparationFailed(errorCode, errorMessage, errorDetails),
            buildAnalysisPlaceholder(),
            new JSONArray(),
            buildProgress(jobId, 0, "failed", "Pipeline rejected before separation: " + errorMessage)
        );
    }

    private JSObject buildManifest(
        String jobId,
        String createdAt,
        String jobStatus,
        JSObject input,
        JSObject stages,
        JSObject separation,
        JSObject analysis,
        JSONArray warnings,
        JSObject progress
    ) throws JSONException {
        JSObject job = new JSObject();
        job.put("id", jobId);
        job.put("status", jobStatus);
        job.put("pipelineVersion", PIPELINE_VERSION);
        job.put("createdAt", createdAt);
        job.put("updatedAt", isoNow());

        JSObject manifest = new JSObject();
        manifest.put("job", job);
        manifest.put("input", input);
        manifest.put("stages", stages);
        manifest.put("progress", progress);
        manifest.put("separation", separation);
        manifest.put("analysis", analysis);
        manifest.put("warnings", warnings);
        manifest.put("artifacts", buildArtifacts(jobId));
        return manifest;
    }

    private void writeProgressManifest(
        String jobId,
        String createdAt,
        String jobStatus,
        JSObject input,
        JSObject stages,
        JSObject separation,
        JSObject analysis,
        JSONArray warnings,
        int percent,
        String stage,
        String message,
        boolean force
    ) throws IOException, JSONException {
        writeProgressManifest(jobId, createdAt, jobStatus, input, stages, separation, analysis, warnings, percent, stage, message, null, force);
    }

    private void writeProgressManifest(
        String jobId,
        String createdAt,
        String jobStatus,
        JSObject input,
        JSObject stages,
        JSObject separation,
        JSObject analysis,
        JSONArray warnings,
        int percent,
        String stage,
        String message,
        JSObject detail,
        boolean force
    ) throws IOException, JSONException {
        int boundedPercent = clampPercent(percent);
        long now = System.currentTimeMillis();
        Integer previousPercent = lastProgressPercent.get(jobId);
        Long previousWriteMs = lastProgressWriteMs.get(jobId);
        if (!force && previousPercent != null && previousPercent == boundedPercent && previousWriteMs != null && now - previousWriteMs < 800L) {
            return;
        }

        JSObject manifest = buildManifest(
            jobId,
            createdAt,
            jobStatus,
            input,
            stages,
            separation,
            analysis,
            warnings,
            buildProgress(jobId, boundedPercent, stage, message, detail)
        );
        writeManifest(jobId, manifest);
        updateForegroundProcessing(jobId, boundedPercent, stage, message);
    }

    private JSObject buildProgress(String jobId, int percent, String stage, String message) throws JSONException {
        return buildProgress(jobId, percent, stage, message, null);
    }

    private JSObject buildProgress(String jobId, int percent, String stage, String message, JSObject detailOverride) throws JSONException {
        long now = System.currentTimeMillis();
        long startedAt = jobStartTimes.containsKey(jobId) ? jobStartTimes.get(jobId) : now;
        int boundedPercent = clampPercent(percent);

        JSObject detail = detailOverride == null ? new JSObject() : new JSObject(detailOverride.toString());
        String active = activeJobId;
        if ("queued".equals(stage) && active != null && !jobId.equals(active)) {
            detail.put("activeJobId", active);
        }

        JSObject progress = new JSObject();
        progress.put("percent", boundedPercent);
        progress.put("stage", defaultString(stage, "processing"));
        progress.put("message", defaultString(message, "Waiting for the next Android pipeline update."));
        progress.put("updatedAt", isoNow());
        progress.put("elapsedMs", Math.max(0L, now - startedAt));
        progress.put("detail", detail.length() > 0 ? detail : JSONObject.NULL);
        copyProgressField(detail, progress, "averageChunkMs");
        copyProgressField(detail, progress, "recentAverageChunkMs");
        copyProgressField(detail, progress, "estimatedRemainingMs");
        copyProgressField(detail, progress, "estimatedSeparationRemainingMs");
        copyProgressField(detail, progress, "estimatedTotalRemainingMs");
        copyProgressField(detail, progress, "lastProgressAt");
        copyProgressField(detail, progress, "chunksCompleted");
        copyProgressField(detail, progress, "totalChunks");
        copyProgressField(detail, progress, "chunksRemaining");

        lastProgressPercent.put(jobId, boundedPercent);
        lastProgressWriteMs.put(jobId, now);
        return progress;
    }

    private void copyProgressField(JSObject source, JSObject target, String key) throws JSONException {
        if (source != null && source.has(key) && !source.isNull(key)) {
            target.put(key, source.get(key));
        }
    }

    private JSObject buildFailureProgress(String jobId, String errorMessage) throws JSONException {
        Integer previousPercent = lastProgressPercent.get(jobId);
        return buildProgress(
            jobId,
            previousPercent == null ? 0 : previousPercent,
            "failed",
            "Pipeline failed: " + defaultString(errorMessage, "Native Android separation failed.")
        );
    }

    private String queuedMessage(String jobId) {
        String active = activeJobId;
        if (active != null && !jobId.equals(active)) {
            return "Queued behind active Android job " + active;
        }
        return "Queued for Android local processing";
    }

    private void acquirePipelineWakeLock(String jobId) {
        try {
            releasePipelineWakeLock();
            PowerManager powerManager = (PowerManager) getContext().getSystemService(Context.POWER_SERVICE);
            if (powerManager == null) {
                return;
            }

            PowerManager.WakeLock wakeLock = powerManager.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "HowardVox:Pipeline:" + defaultString(jobId, "active")
            );
            wakeLock.setReferenceCounted(false);
            wakeLock.acquire(30L * 60L * 1000L);
            pipelineWakeLock = wakeLock;
        } catch (Exception ignored) {
            // The foreground service still provides the primary user-visible background affordance.
        }
    }

    private void releasePipelineWakeLock() {
        PowerManager.WakeLock wakeLock = pipelineWakeLock;
        pipelineWakeLock = null;
        if (wakeLock == null) {
            return;
        }

        try {
            if (wakeLock.isHeld()) {
                wakeLock.release();
            }
        } catch (Exception ignored) {
            // Best-effort cleanup.
        }
    }

    private void updateForegroundProcessing(String jobId, int percent, String stage, String message) {
        try {
            VoxPipelineForegroundService.startOrUpdate(getContext(), jobId, percent, stage, message);
        } catch (Exception ignored) {
            // Missing notification approval or OEM policy should not fail the actual job.
        }
    }

    private void stopForegroundProcessing() {
        try {
            VoxPipelineForegroundService.stop(getContext());
        } catch (Exception ignored) {
            // The OS will clean up the service if it is already gone.
        }
    }

    private JSObject buildBackgroundProcessingStatus(String action) throws JSONException {
        JSObject status = new JSObject();
        boolean notificationGranted = hasNotificationPermission();
        boolean batteryUnrestricted = isIgnoringBatteryOptimizations();
        status.put("action", defaultString(action, "status_checked"));
        status.put("executionTarget", "android-local");
        status.put("notificationsGranted", notificationGranted);
        status.put("batteryOptimizationIgnored", batteryUnrestricted);
        status.put("wakeLockPermissionDeclared", true);
        status.put("foregroundServiceAvailable", true);
        status.put("foregroundServiceType", "dataSync");
        status.put("activeJobId", activeJobId == null ? JSONObject.NULL : activeJobId);
        status.put("ready", notificationGranted && batteryUnrestricted);
        status.put(
            "message",
            notificationGranted && batteryUnrestricted
                ? "Background processing is approved for long separations."
                : "Allow notifications and unrestricted battery use so Android does not pause long separations."
        );
        return status;
    }

    private boolean hasNotificationPermission() {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
            || getContext().checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED;
    }

    private boolean isIgnoringBatteryOptimizations() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return true;
        }

        try {
            PowerManager powerManager = (PowerManager) getContext().getSystemService(Context.POWER_SERVICE);
            return powerManager != null && powerManager.isIgnoringBatteryOptimizations(getContext().getPackageName());
        } catch (Exception ignored) {
            return false;
        }
    }

    private String openBatteryOptimizationApproval() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return "battery_optimization_not_required";
        }

        Uri packageUri = Uri.parse("package:" + getContext().getPackageName());
        try {
            Intent requestIntent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
            requestIntent.setData(packageUri);
            requestIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(requestIntent);
            return "battery_optimization_approval_opened";
        } catch (ActivityNotFoundException | SecurityException error) {
            try {
                Intent fallbackIntent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                fallbackIntent.setData(packageUri);
                fallbackIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                getContext().startActivity(fallbackIntent);
                return "app_settings_opened";
            } catch (Exception ignored) {
                return "battery_optimization_approval_unavailable";
            }
        }
    }

    private JSObject buildSeparatorDiagnostics(File inputFile, String mimeType, JSObject input, String failureStage) throws JSONException {
        JSObject media = inspectMedia(inputFile);
        long inputDurationMs = input.optLong("durationMs", -1L);
        long mediaDurationMs = media.optLong("durationMs", -1L);
        long durationMs = inputDurationMs > 0L ? inputDurationMs : mediaDurationMs;
        AndroidOnnxSeparator.SeparationPlan plan = AndroidOnnxSeparator.estimatePlan(durationMs);

        Runtime runtime = Runtime.getRuntime();
        long runtimeMaxHeapBytes = runtime.maxMemory();
        long runtimeUsedHeapBytes = runtime.totalMemory() - runtime.freeMemory();
        long runtimeAvailableHeapBytes = Math.max(0L, runtimeMaxHeapBytes - runtimeUsedHeapBytes);

        ActivityManager activityManager = (ActivityManager) getContext().getSystemService(Context.ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo memoryInfo = new ActivityManager.MemoryInfo();
        if (activityManager != null) {
            activityManager.getMemoryInfo(memoryInfo);
        }

        JSObject diagnostics = new JSObject();
        diagnostics.put("inputFileBytes", inputFile.length());
        diagnostics.put("durationSeconds", durationMs > 0L ? durationMs / 1000d : JSONObject.NULL);
        diagnostics.put("sourceSampleRate", media.has("sampleRate") ? media.optInt("sampleRate") : JSONObject.NULL);
        diagnostics.put("sourceChannels", media.has("channels") ? media.optInt("channels") : JSONObject.NULL);
        diagnostics.put("sourceMimeType", media.optString("mimeType", defaultString(mimeType, "application/octet-stream")));
        diagnostics.put("decodedPcmEstimateBytes", plan.decodedPcmEstimateBytes > 0L ? plan.decodedPcmEstimateBytes : JSONObject.NULL);
        diagnostics.put("androidMemoryClassBytes", activityManager == null ? JSONObject.NULL : activityManager.getMemoryClass() * 1024L * 1024L);
        diagnostics.put("androidLargeMemoryClassBytes", activityManager == null ? JSONObject.NULL : activityManager.getLargeMemoryClass() * 1024L * 1024L);
        diagnostics.put("runtimeMaxHeapBytes", runtimeMaxHeapBytes);
        diagnostics.put("runtimeUsedHeapBytes", runtimeUsedHeapBytes);
        diagnostics.put("runtimeAvailableHeapBytes", runtimeAvailableHeapBytes);
        diagnostics.put("nativeHeapAllocatedBytes", Debug.getNativeHeapAllocatedSize());
        diagnostics.put("systemAvailableMemoryBytes", activityManager == null ? JSONObject.NULL : memoryInfo.availMem);
        diagnostics.put("separatorMemoryBudgetBytes", runtimeAvailableHeapBytes);
        diagnostics.put("estimatedSeparatorPeakMemoryBytes", plan.estimatedSeparatorPeakMemoryBytes > 0L ? plan.estimatedSeparatorPeakMemoryBytes : JSONObject.NULL);
        diagnostics.put("streamingSeparatorPeakMemoryBytes", plan.streamingPeakEstimateBytes > 0L ? plan.streamingPeakEstimateBytes : JSONObject.NULL);
        diagnostics.put("minimumChunkWorkingBytes", plan.minimumChunkWorkingBytes);
        diagnostics.put("plannedChunkSizeFrames", plan.chunkSizeFrames);
        diagnostics.put("plannedChunkSizeSeconds", plan.chunkSizeFrames / (double) AndroidOnnxSeparator.SAMPLE_RATE);
        diagnostics.put("plannedChunkCount", plan.chunkCount > 0L ? plan.chunkCount : JSONObject.NULL);
        diagnostics.put("processingMode", "chunked_onnx_inference_with_streamed_overlap_add");
        diagnostics.put("adaptiveDiskStreamingAvailable", true);
        diagnostics.put("failureStage", defaultString(failureStage, "preflight"));
        return diagnostics;
    }

    private JSObject inspectMedia(File inputFile) throws JSONException {
        JSObject media = new JSObject();
        MediaExtractor extractor = new MediaExtractor();
        try {
            extractor.setDataSource(inputFile.getAbsolutePath());
            for (int index = 0; index < extractor.getTrackCount(); index++) {
                MediaFormat format = extractor.getTrackFormat(index);
                String trackMime = format.containsKey(MediaFormat.KEY_MIME) ? format.getString(MediaFormat.KEY_MIME) : null;
                if (trackMime != null && trackMime.startsWith("audio/")) {
                    media.put("mimeType", trackMime);
                    if (format.containsKey(MediaFormat.KEY_SAMPLE_RATE)) {
                        media.put("sampleRate", format.getInteger(MediaFormat.KEY_SAMPLE_RATE));
                    }
                    if (format.containsKey(MediaFormat.KEY_CHANNEL_COUNT)) {
                        media.put("channels", format.getInteger(MediaFormat.KEY_CHANNEL_COUNT));
                    }
                    if (format.containsKey(MediaFormat.KEY_DURATION)) {
                        media.put("durationMs", Math.max(0L, format.getLong(MediaFormat.KEY_DURATION) / 1000L));
                    }
                    break;
                }
            }
        } catch (Exception error) {
            media.put("error", error.getClass().getSimpleName() + ": " + defaultString(error.getMessage(), ""));
        } finally {
            extractor.release();
        }
        return media;
    }

    private int clampPercent(int percent) {
        return Math.max(0, Math.min(100, percent));
    }

    private JSObject buildInput(PluginCall call, File inputFile, long sizeBytes) throws JSONException {
        return buildInputValues(
            defaultString(call.getString("title"), defaultString(call.getString("fileName"), "Untitled upload")),
            defaultString(call.getString("notes"), ""),
            defaultString(call.getString("sourceType"), "android-local"),
            defaultString(call.getString("fileName"), inputFile.getName()),
            inputFile,
            defaultString(call.getString("mimeType"), "application/octet-stream"),
            sizeBytes,
            defaultString(call.getString("originalSourceFileName"), defaultString(call.getString("fileName"), inputFile.getName())),
            defaultString(call.getString("originalSourceMimeType"), defaultString(call.getString("mimeType"), "application/octet-stream")),
            -1L
        );
    }

    private JSObject buildInputValues(
        String title,
        String notes,
        String sourceType,
        String originalFileName,
        File inputFile,
        String mimeType,
        long sizeBytes,
        String originalSourceFileName,
        String originalSourceMimeType,
        long durationMs
    ) throws JSONException {
        JSObject input = new JSObject();
        input.put("title", defaultString(title, defaultString(originalFileName, "Untitled upload")));
        input.put("notes", defaultString(notes, ""));
        input.put("sourceType", defaultString(sourceType, "android-local"));
        input.put("originalFileName", defaultString(originalFileName, inputFile.getName()));
        input.put("storedPath", inputFile.getAbsolutePath());
        input.put("mimeType", defaultString(mimeType, "application/octet-stream"));
        input.put("sizeBytes", sizeBytes);
        input.put("originalSourceFileName", defaultString(originalSourceFileName, defaultString(originalFileName, inputFile.getName())));
        input.put("originalSourceMimeType", defaultString(originalSourceMimeType, defaultString(mimeType, "application/octet-stream")));
        input.put("durationMs", durationMs >= 0L ? durationMs : JSONObject.NULL);
        return input;
    }

    private JSObject buildAnalysisContext(String jobId, JSObject input) throws JSONException {
        JSObject context = new JSObject();
        context.put("jobId", jobId);
        context.put("songTitle", input.optString("title", input.optString("originalFileName", "Untitled vocal take")));
        context.put("durationSeconds", input.isNull("durationMs") ? JSONObject.NULL : input.optDouble("durationMs", 0d) / 1000d);
        context.put("inputSizeMb", input.optLong("sizeBytes", 0L) > 0L ? input.optLong("sizeBytes", 0L) / (1024d * 1024d) : JSONObject.NULL);
        context.put("userIntent", "practice");
        context.put("styleContext", JSONObject.NULL);
        return context;
    }

    private JSObject buildSeparationPending(String status) throws JSONException {
        JSObject separation = new JSObject();
        separation.put("status", status);
        separation.put("workerHealth", JSONObject.NULL);
        separation.put("engine", JSONObject.NULL);
        separation.put("outputs", new JSObject());
        separation.put("warnings", new JSONArray());
        separation.put("error", JSONObject.NULL);
        return separation;
    }

    private JSObject buildSeparationCompleted(AndroidOnnxSeparator separator, AndroidOnnxSeparator.Result result) throws JSONException {
        JSObject separation = new JSObject();
        separation.put("status", "completed");
        separation.put("workerHealth", JSONObject.NULL);
        separation.put("engine", separator.buildEngine(result));
        separation.put("outputs", separator.buildOutputs(result));
        separation.put("warnings", new JSONArray());
        separation.put("error", JSONObject.NULL);
        return separation;
    }

    private JSObject buildSeparationFailed(String errorCode, String errorMessage, String errorDetails) throws JSONException {
        JSObject error = new JSObject();
        error.put("code", errorCode);
        error.put("message", defaultString(errorMessage, "Native Android separation failed."));
        error.put("details", defaultString(errorDetails, ""));

        JSObject separation = new JSObject();
        separation.put("status", "failed");
        separation.put("workerHealth", JSONObject.NULL);
        separation.put("engine", JSONObject.NULL);
        separation.put("outputs", new JSObject());
        separation.put("warnings", new JSONArray());
        separation.put("error", error);
        return separation;
    }

    private JSObject buildArtifacts(String jobId) throws JSONException {
        JSObject artifacts = new JSObject();
        artifacts.put("jobDir", getJobDir(jobId).getAbsolutePath());
        artifacts.put("manifestPath", getManifestFile(jobId).getAbsolutePath());
        artifacts.put("stemsDir", new File(getJobDir(jobId), "stems").getAbsolutePath());
        return artifacts;
    }

    private File createDiagnosticsZip(String jobId) throws IOException, JSONException {
        File jobDir = getJobDir(jobId);
        File manifestFile = getManifestFile(jobId);
        if (!manifestFile.exists()) {
            throw new IOException("Manifest not found for job: " + jobId);
        }

        File exportDir = new File(getContext().getCacheDir(), "vox-diagnostics");
        ensureDir(exportDir);
        File zipFile = new File(exportDir, jobId + "-diagnostics.zip");
        if (zipFile.exists()) {
            zipFile.delete();
        }

        JSONObject manifest = new JSONObject(readText(manifestFile));
        try (ZipOutputStream zip = new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(zipFile)))) {
            addFileToZip(zip, manifestFile, "analysis/manifest.json");
            addDiagnosticsFile(zip, jobDir, "events.ndjson");
            addDiagnosticsFile(zip, jobDir, "chunk_timings.csv");
            addDiagnosticsFile(zip, jobDir, "runtime_summary.json");
            addDiagnosticsFile(zip, jobDir, "current_phase.json");
            addDiagnosticsFile(zip, jobDir, "stall.json");
            addDiagnosticsFile(zip, jobDir, "error.txt");
            addAnalysisArtifacts(zip, manifest);
            addStemMetadata(zip, manifest);
        }
        return zipFile;
    }

    private void addDiagnosticsFile(ZipOutputStream zip, File jobDir, String name) throws IOException {
        addFileToZip(zip, new File(jobDir, "diagnostics/" + name), "diagnostics/" + name);
    }

    private void addAnalysisArtifacts(ZipOutputStream zip, JSONObject manifest) throws IOException, JSONException {
        JSONObject analysis = manifest.optJSONObject("analysis");
        JSONObject artifacts = analysis == null ? null : analysis.optJSONObject("artifacts");
        if (artifacts == null) {
            return;
        }

        for (String key : new String[] { "pitch", "rms", "crest", "report", "coachInput", "coachOutput", "coachValidation" }) {
            Object value = artifacts.opt(key);
            if (!(value instanceof JSONObject)) {
                continue;
            }
            String path = ((JSONObject) value).optString("path", "");
            if (!path.isEmpty()) {
                addFileToZip(zip, new File(path), "analysis/" + new File(path).getName());
            }
        }
    }

    private void addStemMetadata(ZipOutputStream zip, JSONObject manifest) throws IOException, JSONException {
        JSONObject metadata = new JSONObject();
        JSONObject separation = manifest.optJSONObject("separation");
        JSONObject outputs = separation == null ? null : separation.optJSONObject("outputs");
        JSONObject metadataOutputs = outputs == null ? new JSONObject() : new JSONObject(outputs.toString());
        metadata.put("jobId", manifest.getJSONObject("job").optString("id"));
        metadata.put("separationStatus", separation == null ? JSONObject.NULL : separation.optString("status", ""));
        metadata.put("outputs", metadataOutputs);

        if (metadataOutputs.length() > 0) {
            for (String key : new String[] { "vocals", "instrumental" }) {
                JSONObject artifact = metadataOutputs.optJSONObject(key);
                if (artifact == null) {
                    continue;
                }
                File file = new File(artifact.optString("path", ""));
                artifact.put("exists", file.exists());
                artifact.put("sizeBytes", file.exists() ? file.length() : JSONObject.NULL);
                artifact.remove("path");
                artifact.remove("uri");
            }
        }
        addTextToZip(zip, "diagnostics/stem_metadata.json", metadata.toString(2));
    }

    private void addFileToZip(ZipOutputStream zip, File file, String entryName) throws IOException {
        if (file == null || !file.exists() || !file.isFile()) {
            return;
        }

        ZipEntry entry = new ZipEntry(entryName);
        entry.setTime(file.lastModified());
        zip.putNextEntry(entry);
        try (BufferedInputStream input = new BufferedInputStream(new FileInputStream(file))) {
            byte[] buffer = new byte[64 * 1024];
            int read;
            while ((read = input.read(buffer)) >= 0) {
                zip.write(buffer, 0, read);
            }
        }
        zip.closeEntry();
    }

    private void addTextToZip(ZipOutputStream zip, String entryName, String text) throws IOException {
        zip.putNextEntry(new ZipEntry(entryName));
        zip.write(text.getBytes(StandardCharsets.UTF_8));
        zip.closeEntry();
    }

    private File findLatestManifestFile() {
        File jobsDir = new File(getContext().getFilesDir(), "vox/jobs");
        File[] jobDirs = jobsDir.listFiles(File::isDirectory);
        if (jobDirs == null || jobDirs.length == 0) {
            return null;
        }

        return Arrays.stream(jobDirs)
            .map((dir) -> new File(dir, "analysis/manifest.json"))
            .filter(File::exists)
            .max(Comparator.comparingLong(File::lastModified))
            .orElse(null);
    }

    private JSObject buildAnalysisPlaceholder() throws JSONException {
        return buildAnalysisPlaceholder("pending");
    }

    private JSObject buildAnalysisPlaceholder(String status) throws JSONException {
        JSObject analysisArtifacts = new JSObject();
        analysisArtifacts.put("pitch", JSONObject.NULL);
        analysisArtifacts.put("rms", JSONObject.NULL);
        analysisArtifacts.put("crest", JSONObject.NULL);
        analysisArtifacts.put("report", JSONObject.NULL);

        JSObject analysis = new JSObject();
        analysis.put("status", status);
        analysis.put("summary", JSONObject.NULL);
        analysis.put("metrics", JSONObject.NULL);
        analysis.put("artifacts", analysisArtifacts);
        return analysis;
    }

    private JSObject buildStages(String ingest, String transcode, String separate, String analyze, String report) throws JSONException {
        JSObject stages = new JSObject();
        stages.put("ingest", ingest);
        stages.put("transcode", transcode);
        stages.put("separate", separate);
        stages.put("analyze", analyze);
        stages.put("report", report);
        return stages;
    }

    private void writeManifest(String jobId, JSObject manifest) throws IOException, JSONException {
        File manifestFile = getManifestFile(jobId);
        ensureDir(manifestFile.getParentFile());
        writeBytes(manifestFile, manifest.toString(2).getBytes("UTF-8"));
    }

    private void markCancelled(JSONObject manifest) throws JSONException {
        manifest.getJSONObject("job").put("status", "cancelled");
        manifest.getJSONObject("job").put("updatedAt", isoNow());

        JSONObject stages = manifest.optJSONObject("stages");
        if (stages != null) {
            markStageCancelled(stages, "separate");
            markStageCancelled(stages, "analyze");
            markStageCancelled(stages, "report");
        }

        JSONObject separation = manifest.optJSONObject("separation");
        if (separation != null) {
            String status = separation.optString("status", "pending");
            if (!"completed".equals(status) && !"failed".equals(status)) {
                separation.put("status", "cancelled");
            }
        }

        JSONObject analysis = manifest.optJSONObject("analysis");
        if (analysis != null) {
            String status = analysis.optString("status", "pending");
            if (!"completed".equals(status) && !"failed".equals(status)) {
                analysis.put("status", "cancelled");
            }
        }

        JSONObject progress = manifest.optJSONObject("progress");
        if (progress == null) {
            progress = new JSONObject();
            manifest.put("progress", progress);
        }
        progress.put("percent", progress.has("percent") ? progress.optInt("percent", 0) : 0);
        progress.put("stage", "cancelled");
        progress.put("message", "Job cancelled by user.");
        progress.put("updatedAt", isoNow());
    }

    private void markStageCancelled(JSONObject stages, String key) throws JSONException {
        String status = stages.optString(key, "pending");
        if (!"completed".equals(status) && !"failed".equals(status)) {
            stages.put(key, "cancelled");
        }
    }

    private boolean isCancelled(String jobId) {
        if (cancelledJobs.contains(jobId)) {
            return true;
        }

        try {
            JSONObject manifest = new JSONObject(readText(getManifestFile(jobId)));
            return "cancelled".equals(manifest.getJSONObject("job").optString("status"));
        } catch (Exception error) {
            return false;
        }
    }

    private JSONObject findArtifact(JSONObject manifest, String artifactKey) throws JSONException {
        JSONObject outputs = manifest.optJSONObject("separation") == null
            ? null
            : manifest.getJSONObject("separation").optJSONObject("outputs");
        if (outputs != null && outputs.has(artifactKey)) {
            return outputs.getJSONObject(artifactKey);
        }

        JSONObject analysisArtifacts = manifest.optJSONObject("analysis") == null
            ? null
            : manifest.getJSONObject("analysis").optJSONObject("artifacts");
        if (analysisArtifacts != null && analysisArtifacts.has(artifactKey)) {
            Object artifact = analysisArtifacts.get(artifactKey);
            return artifact instanceof JSONObject ? (JSONObject) artifact : null;
        }
        return null;
    }

    private JSONObject jsonArtifact(File file, String mimeType) throws JSONException {
        JSONObject artifact = new JSONObject();
        artifact.put("path", file.getAbsolutePath());
        artifact.put("uri", file.toURI().toString());
        artifact.put("mimeType", mimeType);
        artifact.put("format", "json");
        return artifact;
    }

    private File getJobDir(String jobId) {
        return new File(getContext().getFilesDir(), "vox/jobs/" + jobId);
    }

    private File getManifestFile(String jobId) {
        return new File(getJobDir(jobId), "analysis/manifest.json");
    }

    private boolean deleteRecursively(File file) {
        if (file == null || !file.exists()) {
            return true;
        }

        File[] children = file.listFiles();
        if (children != null) {
            for (File child : children) {
                if (!deleteRecursively(child)) {
                    return false;
                }
            }
        }
        return file.delete();
    }

    private void ensureDir(File dir) throws IOException {
        if (!dir.exists() && !dir.mkdirs()) {
            throw new IOException("Could not create directory: " + dir.getAbsolutePath());
        }
    }

    private void writeBytes(File file, byte[] bytes) throws IOException {
        try (FileOutputStream outputStream = new FileOutputStream(file)) {
            outputStream.write(bytes);
        }
    }

    private String readText(File file) throws IOException {
        byte[] buffer = new byte[(int) file.length()];
        try (FileInputStream inputStream = new FileInputStream(file)) {
            int offset = 0;
            while (offset < buffer.length) {
                int read = inputStream.read(buffer, offset, buffer.length - offset);
                if (read < 0) break;
                offset += read;
            }
        }
        return new String(buffer, "UTF-8");
    }

    private long copyUriToFile(ContentResolver resolver, Uri uri, File outputFile) throws IOException {
        ensureDir(outputFile.getParentFile());
        long total = 0L;
        try (InputStream inputStream = resolver.openInputStream(uri);
             FileOutputStream outputStream = new FileOutputStream(outputFile)) {
            if (inputStream == null) {
                throw new IOException("Could not open selected audio file.");
            }

            byte[] buffer = new byte[1024 * 1024];
            int read;
            while ((read = inputStream.read(buffer)) >= 0) {
                total += read;
                if (total <= MAX_UPLOAD_BYTES) {
                    outputStream.write(buffer, 0, read);
                }
                if (total > MAX_UPLOAD_BYTES) {
                    break;
                }
            }
        }
        return total;
    }

    private String queryDisplayName(ContentResolver resolver, Uri uri) {
        try (Cursor cursor = resolver.query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) {
                    return cursor.getString(index);
                }
            }
        } catch (Exception ignored) {
            // Fallback below.
        }

        String path = uri.getLastPathSegment();
        if (path == null || path.isEmpty()) {
            return null;
        }
        int slashIndex = path.lastIndexOf('/');
        return slashIndex >= 0 && slashIndex < path.length() - 1 ? path.substring(slashIndex + 1) : path;
    }

    private long querySizeBytes(ContentResolver resolver, Uri uri) {
        try (Cursor cursor = resolver.query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.SIZE);
                if (index >= 0 && !cursor.isNull(index)) {
                    return cursor.getLong(index);
                }
            }
        } catch (Exception ignored) {
            // Size is optional for content providers.
        }
        return -1L;
    }

    private long readDurationMs(File inputFile) {
        if (!inputFile.exists() || inputFile.length() == 0L) {
            return -1L;
        }

        MediaMetadataRetriever retriever = new MediaMetadataRetriever();
        try {
            retriever.setDataSource(inputFile.getAbsolutePath());
            String duration = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION);
            return duration == null || duration.isEmpty() ? -1L : Long.parseLong(duration);
        } catch (Exception ignored) {
            return -1L;
        } finally {
            try {
                retriever.release();
            } catch (Exception ignored) {
                // Older platform implementations can throw during release.
            }
        }
    }

    private String createJobId() {
        SimpleDateFormat format = new SimpleDateFormat("yyyyMMddHHmmss", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        return "job_android_" + format.format(new Date()) + "_" + UUID.randomUUID().toString().substring(0, 6);
    }

    private String isoNow() {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        return format.format(new Date());
    }

    private String safeExtension(String originalFileName, String mimeType) {
        String lowerName = originalFileName == null ? "" : originalFileName.toLowerCase(Locale.US);
        int dotIndex = lowerName.lastIndexOf('.');
        if (dotIndex >= 0 && dotIndex < lowerName.length() - 1) {
            return lowerName.substring(dotIndex);
        }

        if ("audio/wav".equals(mimeType) || "audio/x-wav".equals(mimeType)) return ".wav";
        if ("audio/mpeg".equals(mimeType) || "audio/mp3".equals(mimeType)) return ".mp3";
        if ("audio/mp4".equals(mimeType)) return ".m4a";
        if ("audio/ogg".equals(mimeType)) return ".ogg";
        if ("audio/webm".equals(mimeType)) return ".webm";
        return ".bin";
    }

    private String defaultString(String value, String fallback) {
        return value == null || value.isEmpty() ? fallback : value;
    }
}
