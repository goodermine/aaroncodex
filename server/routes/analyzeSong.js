import fs from "node:fs/promises";
import express from "express";
import { config } from "../config.js";
import { createJobId, ensureJobDirs, getJobPaths, saveUploadedFile, writeManifest } from "../services/jobStore.js";
import { getWorkerHealth, separateAudio } from "../services/pythonWorker.js";

function buildAnalysisPlaceholder(status = "pending") {
  return {
    status,
    summary: null,
    metrics: null,
    artifacts: {
      pitch: null,
      rms: null,
      crest: null,
      report: null,
    },
  };
}

function buildStages(overrides = {}) {
  return {
    ingest: "pending",
    transcode: "not_required",
    separate: "pending",
    analyze: "pending",
    report: "pending",
    ...overrides,
  };
}

function buildInputResponse(fileInfo, body = {}) {
  return {
    title: body.title || fileInfo.originalFileName || "Untitled upload",
    notes: body.notes || "",
    sourceType: body.sourceType || "upload",
    originalFileName: fileInfo.originalFileName,
    storedPath: fileInfo.storedPath,
    mimeType: fileInfo.mimeType,
    sizeBytes: fileInfo.sizeBytes,
  };
}

function buildErrorResponse(jobId, input, artifacts, warnings, code, message, status = 500, details = null) {
  return {
    status,
    body: {
      job: {
        id: jobId,
        status: "failed",
      },
      input,
      stages: buildStages({
        ingest: input?.storedPath ? "completed" : "failed",
        separate: "failed",
      }),
      separation: {
        status: "failed",
        error: {
          code,
          message,
          details,
        },
      },
      analysis: buildAnalysisPlaceholder("pending"),
      warnings,
      artifacts,
    },
  };
}

export function createAnalyzeSongRouter(upload) {
  const router = express.Router();

  router.post("/", upload.single("file"), async (req, res) => {
    const jobId = createJobId();
    const warnings = [];
    const paths = await ensureJobDirs(jobId);
    const artifacts = {
      jobDir: paths.jobDir,
      manifestPath: paths.manifestPath,
      stemsDir: paths.stemsDir,
    };

    let input = null;

    try {
      if (!req.file?.buffer) {
        res.status(400).json({
          error: "UPLOAD_REQUIRED",
          message: "POST /analyze-song requires an uploaded audio file under the form field 'file'.",
        });
        return;
      }

      const fileInfo = await saveUploadedFile(jobId, req.file);
      input = buildInputResponse(fileInfo, req.body);

      const initialManifest = {
        job: {
          id: jobId,
          status: "queued",
          pipelineVersion: "vox-transcription-v1",
          createdAt: new Date().toISOString(),
        },
        input,
        stages: buildStages({
          ingest: "completed",
        }),
        separation: {
          status: "pending",
        },
        analysis: buildAnalysisPlaceholder("pending"),
        warnings,
        artifacts,
      };

      await writeManifest(jobId, initialManifest);

      const processingManifest = {
        ...initialManifest,
        job: {
          ...initialManifest.job,
          status: "processing",
        },
        stages: buildStages({
          ingest: "completed",
          separate: "processing",
        }),
        separation: {
          status: "processing",
        },
      };

      await writeManifest(jobId, processingManifest);

      let workerHealth;
      try {
        workerHealth = await getWorkerHealth();
      } catch (error) {
        const result = buildErrorResponse(
          jobId,
          input,
          artifacts,
          warnings,
          "WORKER_UNAVAILABLE",
          "Python worker health check failed before separation.",
          502,
          error instanceof Error ? error.message : "Unknown worker failure"
        );
        await writeManifest(jobId, result.body);
        res.status(result.status).json(result.body);
        return;
      }

      const separationResponse = await separateAudio({
        jobId,
        inputPath: fileInfo.storedPath,
        outputDir: paths.stemsDir,
        stemMode: "vocals_instrumental",
        cleanupIntermediate: false,
        modelFilename: config.separatorModelFilename || undefined,
      });

      const responseBody = {
        job: {
          id: jobId,
          status: separationResponse.ok ? "completed" : "failed",
          pipelineVersion: "vox-transcription-v1",
          createdAt: initialManifest.job.createdAt,
        },
        input,
        stages: buildStages({
          ingest: "completed",
          separate: separationResponse.ok ? "completed" : "failed",
        }),
        separation: {
          status: separationResponse.ok ? "completed" : "failed",
          workerHealth,
          engine: separationResponse.engine || null,
          outputs: separationResponse.outputs || {},
          warnings: separationResponse.warnings || [],
          error: separationResponse.error || null,
        },
        analysis: buildAnalysisPlaceholder("pending"),
        warnings: [...warnings, ...(separationResponse.warnings || [])],
        artifacts,
      };

      await writeManifest(jobId, responseBody);
      res.status(separationResponse.ok ? 200 : 502).json(responseBody);
    } catch (error) {
      const result = buildErrorResponse(
        jobId,
        input,
        artifacts,
        warnings,
        "ANALYZE_SONG_FAILED",
        "Failed to create a separation job.",
        500,
        error instanceof Error ? error.message : "Unknown analyze-song failure"
      );

      try {
        await writeManifest(jobId, result.body);
      } catch {
        // Best effort manifest write only.
      }

      if (error?.status && error?.payload) {
        const payload = {
          ...result.body,
          stages: buildStages({
            ingest: input?.storedPath ? "completed" : "failed",
            separate: "failed",
          }),
          separation: {
            status: "failed",
            error: error.payload.error || {
              code: "SEPARATION_FAILED",
              message: error.message,
            },
          },
          analysis: buildAnalysisPlaceholder("pending"),
        };
        await writeManifest(jobId, payload);
        res.status(error.status >= 400 ? error.status : 502).json(payload);
        return;
      }

      res.status(result.status).json(result.body);
    }
  });

  router.get("/jobs/:jobId", async (req, res) => {
    try {
      const { manifestPath } = getJobPaths(req.params.jobId);
      const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
      res.json(manifest);
    } catch (error) {
      res.status(404).json({
        error: "JOB_NOT_FOUND",
        message: error instanceof Error ? error.message : "Unknown job lookup failure",
      });
    }
  });

  return router;
}
