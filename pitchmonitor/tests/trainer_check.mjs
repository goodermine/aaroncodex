// Onset trainer smoke check — loads the pitch monitor with Chrome's fake mic,
// starts audio, enters trainer mode, and asserts the state machine advances
// PLAY → HEAR IT → SING and a verdict eventually lands. Any console error fails.
// Run:  node pitchmonitor/tests/trainer_check.mjs
// Needs playwright (globally installed is fine) + the preinstalled chromium.
// Serves nothing itself: start `python3 -m http.server 8123` in pitchmonitor/ first,
// or pass URL=... in the environment.
const PW = process.env.PLAYWRIGHT_HOME || "/opt/node22/lib/node_modules/playwright/index.mjs";
const { chromium } = await import(PW);

const url = process.env.URL || "http://127.0.0.1:8123/index.html";
const browser = await chromium.launch({
  executablePath: "/opt/pw-browsers/chromium",
  args: [
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    "--autoplay-policy=no-user-gesture-required",
  ],
});
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
page.on("requestfailed", (r) => errors.push("requestfailed: " + r.url()));
page.on("response", (r) => { if (r.status() >= 400 && !/favicon/.test(r.url())) errors.push("http " + r.status() + ": " + r.url()); });
page.on("console", (m) => { if (m.type() === "error" && !/favicon/.test((m.location() && m.location().url) || "")) errors.push("console: " + m.text()); });

await page.goto(url);
await page.waitForTimeout(400);

// tokens loaded?
const title = await page.title();
if (/FAILED/.test(title)) { console.error("FAIL tokens: " + title); process.exit(1); }

// TRAIN before mic → must refuse politely, not crash
await page.click("#trainBtn");
const pre = await page.textContent("#trVerdict");
if (!/start the microphone/.test(pre)) { console.error("FAIL pre-mic guard, got: " + pre); process.exit(1); }

// start the (fake) mic
await page.click("#startBtn");
try {
  await page.waitForSelector(".gate.hidden", { timeout: 5000, state: "attached" });
} catch {
  const err = await page.textContent("#gateErr");
  console.error("gate did not hide; gateErr =", JSON.stringify(err));
  console.error("mediaDevices?", await page.evaluate(() => !!navigator.mediaDevices));
  process.exit(1);
}

// enter trainer
await page.click("#trainBtn");
await page.waitForSelector(".trainer.show", { timeout: 3000, state: "attached" });

// phase machine advances
const phases = new Set();
const t0 = Date.now();
let verdictSeen = null;
while (Date.now() - t0 < 15000) {
  const ph = await page.textContent("#trPhase");
  for (const p of ["LISTEN", "HEAR IT", "SING"]) if (ph.includes(p)) phases.add(p);
  const cls = await page.getAttribute("#trVerdict", "class");
  const m = /verdict (clean|scoop|overshoot|miss)/.exec(cls || "");
  if (m) { verdictSeen = m[1]; if (phases.size === 3) break; }
  await page.waitForTimeout(150);
}
console.log("phases seen:", [...phases].join(", "), "| verdict:", verdictSeen);

// leave trainer; strip hides
await page.click("#trainBtn");
const shown = await page.$(".trainer.show");

await browser.close();

if (phases.size < 3) { console.error("FAIL: phase machine did not reach all of LISTEN/HEAR IT/SING"); process.exit(1); }
if (!verdictSeen) { console.error("FAIL: no verdict was ever produced"); process.exit(1); }
if (shown) { console.error("FAIL: trainer strip still visible after stop"); process.exit(1); }
if (errors.length) { console.error("FAIL console errors:\n" + errors.join("\n")); process.exit(1); }
console.log("TRAINER CHECK PASSED");
