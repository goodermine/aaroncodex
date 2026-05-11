/* global process */
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVER_DIR = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(SERVER_DIR, "..");

function numberFromEnv(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export const config = {
  projectRoot: PROJECT_ROOT,
  storageRoot: process.env.VOX_STORAGE_ROOT || path.join(PROJECT_ROOT, "storage"),
  jobsRoot: process.env.VOX_JOBS_ROOT || path.join(PROJECT_ROOT, "storage", "jobs"),
  workerBaseUrl: process.env.VOX_PYTHON_WORKER_URL || "http://127.0.0.1:8797",
  workerTimeoutMs: numberFromEnv(process.env.VOX_PYTHON_WORKER_TIMEOUT_MS, 10 * 60 * 1000),
  analyzePort: numberFromEnv(process.env.PORT, 8787),
  separatorModelFilename: process.env.VOX_SEPARATOR_MODEL_FILENAME || "UVR_MDXNET_Main.onnx",
};
