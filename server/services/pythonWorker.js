import { config } from "../config.js";

async function requestWorker(endpoint, payload, timeoutMs = config.workerTimeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${config.workerBaseUrl}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const message = data?.error?.message || data?.message || `Worker request failed with status ${response.status}`;
      const error = new Error(message);
      error.status = response.status;
      error.payload = data;
      throw error;
    }

    return data;
  } finally {
    clearTimeout(timer);
  }
}

export async function getWorkerHealth() {
  return requestWorker("/health", {});
}

export async function separateAudio(payload) {
  return requestWorker("/separate", payload);
}
