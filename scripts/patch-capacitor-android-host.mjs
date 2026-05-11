import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const systemBarsPath = resolve(
  "node_modules/@capacitor/android/capacitor/src/main/java/com/getcapacitor/plugin/SystemBars.java"
);
const api35Constant = "Build.VERSION_CODES.VANILLA_ICE_CREAM";
const api35Literal = "35";

if (!existsSync(systemBarsPath)) {
  console.log("Capacitor SystemBars.java not found; skipping Android host patch.");
  process.exit(0);
}

const source = readFileSync(systemBarsPath, "utf8");

if (!source.includes(api35Constant)) {
  console.log("Capacitor Android host patch already applied.");
  process.exit(0);
}

writeFileSync(systemBarsPath, source.replaceAll(api35Constant, api35Literal));
console.log("Patched Capacitor SystemBars.java for API 34 ARM64 host build.");
