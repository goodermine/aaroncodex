import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { config } from "../config.js";

function timestampIdPart(date = new Date()) {
  return date.toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
}

export function createJobId(date = new Date()) {
  return `job_${timestampIdPart(date)}_${crypto.randomBytes(3).toString("hex")}`;
}

export function getJobPaths(jobId) {
  const jobDir = path.join(config.jobsRoot, jobId);
  return {
    jobDir,
    inputDir: path.join(jobDir, "input"),
    stemsDir: path.join(jobDir, "stems"),
    analysisDir: path.join(jobDir, "analysis"),
    logsDir: path.join(jobDir, "logs"),
    manifestPath: path.join(jobDir, "analysis", "manifest.json"),
  };
}

export async function ensureJobDirs(jobId) {
  const paths = getJobPaths(jobId);
  await Promise.all(Object.values(paths).slice(0, 5).map((dir) => fs.mkdir(dir, { recursive: true })));
  return paths;
}

function safeExtension(originalname = "", mimetype = "") {
  const rawExt = path.extname(originalname).toLowerCase();
  if (rawExt) {
    return rawExt;
  }

  const mimeMap = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
  };

  return mimeMap[mimetype] || ".bin";
}

export async function saveUploadedFile(jobId, file) {
  if (!file?.buffer) {
    throw new Error("No uploaded file buffer was provided.");
  }

  const paths = await ensureJobDirs(jobId);
  const extension = safeExtension(file.originalname, file.mimetype);
  const storedPath = path.join(paths.inputDir, `original${extension}`);

  await fs.writeFile(storedPath, file.buffer);

  return {
    storedPath,
    sizeBytes: file.size ?? file.buffer.length,
    mimeType: file.mimetype || "application/octet-stream",
    originalFileName: file.originalname || path.basename(storedPath),
  };
}

export async function writeManifest(jobId, payload) {
  const { manifestPath } = await ensureJobDirs(jobId);
  await fs.writeFile(manifestPath, JSON.stringify(payload, null, 2));
  return manifestPath;
}
