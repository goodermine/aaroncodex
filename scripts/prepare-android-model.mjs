import { createHash } from "node:crypto";
import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { basename, resolve } from "node:path";

const MODEL_FILENAME = "UVR_MDXNET_Main.onnx";
const SOURCE_MODEL_FILENAMES = ["UVR-MDX-NET-Inst_HQ_5.onnx", MODEL_FILENAME];
const EXPECTED_AUDIO_SEPARATOR_HASH = "cb790d0c913647ced70fc6b38f5bea1a";
const HASH_BYTES = 10_000 * 1024;
const targetPath = resolve("android/app/src/main/assets/models", MODEL_FILENAME);

const candidates = [
  process.env.VOX_ANDROID_MODEL,
  process.env.VOX_SEPARATOR_MODEL_PATH,
  ...SOURCE_MODEL_FILENAMES.flatMap((filename) => [
    resolve("models", filename),
    resolve("storage/models", filename),
    resolve("python_worker/models", filename),
    resolve(process.env.HOME || "", ".cache/audio-separator/models", filename),
  ]),
].filter(Boolean);

function audioSeparatorHash(path) {
  const stats = statSync(path);
  const bytes = readFileSync(path);
  const slice = stats.size < HASH_BYTES ? bytes : bytes.subarray(stats.size - HASH_BYTES);
  return createHash("md5").update(slice).digest("hex");
}

function verify(path) {
  const hash = audioSeparatorHash(path);
  if (hash !== EXPECTED_AUDIO_SEPARATOR_HASH) {
    throw new Error(
      `${basename(path)} hash mismatch. Expected ${EXPECTED_AUDIO_SEPARATOR_HASH}, received ${hash}. ` +
        "Use the UVR-MDX-NET-Inst_HQ_5.onnx model that matches the backend audio-separator contract."
    );
  }
}

try {
  if (existsSync(targetPath)) {
    verify(targetPath);
    console.log(`Android model already prepared: ${targetPath}`);
    process.exit(0);
  }

  const sourcePath = candidates.find((candidate) => existsSync(candidate));
  if (!sourcePath) {
    throw new Error(
      `Missing ${MODEL_FILENAME}. Set VOX_ANDROID_MODEL=/absolute/path/${MODEL_FILENAME} ` +
        `or place the verified UVR-MDX-NET-Inst_HQ_5.onnx source model at ${targetPath}.`
    );
  }

  verify(sourcePath);
  mkdirSync(resolve("android/app/src/main/assets/models"), { recursive: true });
  copyFileSync(sourcePath, targetPath);
  console.log(`Copied ${sourcePath} -> ${targetPath}`);
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
