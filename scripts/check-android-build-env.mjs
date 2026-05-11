import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { execFileSync } from "node:child_process";

const variablesPath = resolve("android/variables.gradle");
const localPropertiesPath = resolve("android/local.properties");
const gradlePropertiesPath = resolve("android/gradle.properties");

function fail(message) {
  console.error(message);
  process.exit(1);
}

function readCompileSdk() {
  const text = readFileSync(variablesPath, "utf8");
  const match = text.match(/compileSdkVersion\s*=\s*(\d+)/);
  return match ? match[1] : null;
}

function readLocalSdkDir() {
  if (!existsSync(localPropertiesPath)) return null;

  const text = readFileSync(localPropertiesPath, "utf8");
  const match = text.match(/^sdk\.dir\s*=\s*(.+)$/m);
  if (!match) return null;

  return match[1].trim().replace(/\\:/g, ":").replace(/\\\\/g, "\\");
}

function readGradleProperty(name) {
  if (!existsSync(gradlePropertiesPath)) return null;

  const text = readFileSync(gradlePropertiesPath, "utf8");
  const escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = text.match(new RegExp(`^${escapedName}\\s*=\\s*(.+)$`, "m"));
  return match ? match[1].trim() : null;
}

function commandExists(command) {
  try {
    execFileSync("bash", ["-lc", `command -v ${command}`], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

const compileSdk = readCompileSdk();
if (!compileSdk) {
  fail("Could not determine compileSdkVersion from android/variables.gradle.");
}

if (!commandExists("java")) {
  fail("Java is required to build the Android APK. Install JDK 17+ and retry.");
}

const sdkDir = process.env.ANDROID_HOME || process.env.ANDROID_SDK_ROOT || readLocalSdkDir();
if (!sdkDir) {
  fail(
    "Android SDK location is not configured. Set ANDROID_HOME or create android/local.properties with sdk.dir=/absolute/path/to/android-sdk."
  );
}

const resolvedSdkDir = resolve(sdkDir);
if (!existsSync(resolvedSdkDir)) {
  fail(`Android SDK directory does not exist: ${resolvedSdkDir}`);
}

const platformJar = join(resolvedSdkDir, "platforms", `android-${compileSdk}`, "android.jar");
if (!existsSync(platformJar)) {
  fail(`Android SDK platform android-${compileSdk} is missing. Install platforms;android-${compileSdk}.`);
}

const aapt2Name = process.platform === "win32" ? "aapt2.exe" : "aapt2";
const aapt2Override = readGradleProperty("android.aapt2FromMavenOverride");

let latestBuildTools = "override";
let aapt2Path = aapt2Override;

if (!aapt2Path) {
  const buildToolsDir = join(resolvedSdkDir, "build-tools");
  if (!existsSync(buildToolsDir)) {
    fail("Android SDK build-tools are missing. Install a build-tools package compatible with Android Gradle Plugin.");
  }

  const buildToolVersions = readdirSync(buildToolsDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();

  if (!buildToolVersions.length) {
    fail("Android SDK build-tools directory exists, but no build-tools versions are installed.");
  }

  latestBuildTools = buildToolVersions[buildToolVersions.length - 1];
  aapt2Path = join(buildToolsDir, latestBuildTools, aapt2Name);
}

if (!existsSync(aapt2Path)) {
  fail(`Android build-tools ${latestBuildTools} is missing ${aapt2Name}.`);
}

try {
  execFileSync(aapt2Path, ["version"], { stdio: "ignore" });
} catch {
  fail(`Android build-tools ${latestBuildTools} ${aapt2Name} could not run on this host architecture.`);
}

console.log(`Android build environment OK: SDK=${resolvedSdkDir}, compileSdk=${compileSdk}, buildTools=${latestBuildTools}, aapt2=${aapt2Path}`);
