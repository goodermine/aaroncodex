import fs from 'node:fs';
import path from 'node:path';

const CDP_URL = process.env.CDP_URL || 'http://127.0.0.1:9225';
const APP_URL = process.env.APP_URL || 'http://100.103.207.54:8877/';
const JOB_ID = process.env.JOB_ID || '';
const EVIDENCE_DIR = process.env.EVIDENCE_DIR || '';
const DURATION_SECONDS = 240;
const FPS = 22;
const TOTAL_FRAMES = DURATION_SECONDS * FPS;
const artifactPath = name => EVIDENCE_DIR ? path.join(EVIDENCE_DIR, name) : null;
if (!/^[0-9a-f-]{36}$/i.test(JOB_ID)) {
  throw new Error('Set JOB_ID to a completed pitch-viewer job UUID');
}
if (EVIDENCE_DIR) fs.mkdirSync(EVIDENCE_DIR, {recursive: true});
const writeJsonArtifact = (name, value) => {
  const destination = artifactPath(name);
  if (destination) fs.writeFileSync(destination, `${JSON.stringify(value, null, 2)}\n`);
  return destination;
};

const pages = await (await fetch(`${CDP_URL}/json/list`)).json();
const page = pages.find(item => item.type === 'page' && item.url.startsWith(APP_URL)) ||
  pages.find(item => item.type === 'page');
if (!page) throw new Error(`No browser page is available through ${CDP_URL}`);
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });

let nextId = 1;
const pending = new Map();
const consoleErrors = [];
const networkFailures = [];
ws.onmessage = event => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    const waiter = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
    else waiter.resolve(message.result);
    return;
  }
  if (message.method === 'Runtime.exceptionThrown') {
    consoleErrors.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || 'Runtime exception');
  }
  if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') {
    consoleErrors.push(message.params.entry.text);
  }
  if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
    consoleErrors.push(message.params.args.map(value => value.value || value.description).join(' '));
  }
  if (message.method === 'Network.loadingFailed' && !message.params.canceled) {
    networkFailures.push(`${message.params.type}: ${message.params.errorText}`);
  }
};

const call = (method, params = {}) => new Promise((resolve, reject) => {
  const id = nextId++;
  pending.set(id, {resolve, reject});
  ws.send(JSON.stringify({id, method, params}));
});
const evaluate = async expression => {
  const output = await call('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  });
  if (output.exceptionDetails) throw new Error(output.exceptionDetails.exception?.description || output.exceptionDetails.text);
  return output.result.value;
};
const waitFor = async (expression, timeout = 18000) => {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 80));
  }
  throw new Error(`Timed out: ${expression}`);
};

await call('Page.enable');
await call('Runtime.enable');
await call('Log.enable');
await call('Network.enable');
await call('Emulation.setCPUThrottlingRate', {rate: 1});
await call('Emulation.setDeviceMetricsOverride', {
  width: 390,
  height: 844,
  screenWidth: 390,
  screenHeight: 844,
  deviceScaleFactor: 3,
  mobile: true,
  screenOrientation: {type: 'portraitPrimary', angle: 0},
});
await call('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 5});
await call('Page.navigate', {url: APP_URL});
await waitFor("document.readyState === 'complete'");

const setup = await evaluate(`(async () => {
  const jobResponse = await fetch('/api/pitch-jobs/${JOB_ID}');
  if (!jobResponse.ok) throw new Error('real audio fixture failed to load');
  const realJob = await jobResponse.json();
  const tileWidths = [2048, 2048, ${TOTAL_FRAMES - 4096}];
  const tileBlobs = [];
  for (let tileIndex = 0; tileIndex < tileWidths.length; tileIndex++) {
    const width = tileWidths[tileIndex];
    const tile = document.createElement('canvas');
    tile.width = width;
    tile.height = 180;
    const context = tile.getContext('2d');
    context.fillStyle = '#050709';
    context.fillRect(0, 0, width, 180);
    const gradient = context.createLinearGradient(0, 0, 0, 180);
    gradient.addColorStop(0, '#172026');
    gradient.addColorStop(.48, '#3b4b52');
    gradient.addColorStop(1, '#080b0e');
    context.globalAlpha = .58;
    context.fillStyle = gradient;
    for (let x = 0; x < width; x += 5) {
      const height = 30 + ((x * 17 + tileIndex * 31) % 120);
      context.fillRect(x, 180 - height, 2, height);
    }
    context.globalAlpha = .75;
    context.fillStyle = '#d9e5e8';
    for (const row of [116, 80, 59, 44, 33, 24, 16, 8]) context.fillRect(0, row, width, 1);
    tileBlobs.push(await new Promise(resolve => tile.toBlob(resolve, 'image/png')));
  }

  const makeHarmonics = phase => {
    const values = {};
    for (let harmonic = 1; harmonic <= 8; harmonic++) {
      values['H' + harmonic] = Array.from({length: ${DURATION_SECONDS * 10}}, (_, index) =>
        index % 97 === 0 ? null : Math.max(-80, -(harmonic - 1) * 4.4 - Math.sin(index / 17 + phase) * 2.2));
    }
    return {version: 'voxai_spectral_v1', rate_hz: 10, t0: 0,
      units: 'db_relative_to_strongest_available_harmonic_per_frame', values};
  };
  const harmonicsBySource = {vocals: makeHarmonics(0), original: makeHarmonics(.7)};
  const realFetch = window.fetch.bind(window);
  window.__phase3PerfRequests = [];
  window.fetch = async (input, init) => {
    const url = String(input instanceof Request ? input.url : input);
    if (!url.includes('/phase3/spectral/')) return realFetch(input, init);
    window.__phase3PerfRequests.push(url);
    const source = url.includes('/original/') ? 'original' : 'vocals';
    if (url.endsWith('/descriptor')) {
      let frameStart = 0;
      const tiles = tileWidths.map((width, index) => {
        const descriptor = {index, frame_start: frameStart, frame_count: width, width, height: 180,
          url: '/phase3/spectral/' + source + '/tiles/' + index};
        frameStart += width;
        return descriptor;
      });
      return new Response(JSON.stringify({
        version: 'voxai_spectral_v1', source, transform: 'librosa.cqt', display_only: true,
        t0: 0, fps: ${FPS}, duration_seconds: ${DURATION_SECONDS}, total_frames: ${TOTAL_FRAMES},
        midi_lo: 36, midi_hi: 96, bins_per_semitone: 3, n_bins: 180,
        row_order: 'high_to_low', db_floor: -80, db_ceil: 0, tiles,
      }), {headers: {'Content-Type': 'application/json'}});
    }
    if (url.endsWith('/harmonics')) {
      return new Response(JSON.stringify(harmonicsBySource[source]), {headers: {'Content-Type': 'application/json'}});
    }
    if (url.includes('/tiles/')) {
      const tileIndex = Number(url.slice(url.lastIndexOf('/') + 1));
      return new Response(tileBlobs[tileIndex], {headers: {'Content-Type': 'image/png'}});
    }
    return new Response('', {status: 404});
  };

  const contour = Array.from({length: ${DURATION_SECONDS * 10}}, (_, index) =>
    index % 89 < 9 ? null : -950 + Math.sin(index / 20) * 145 + Math.sin(index / 5) * 18);
  const native = Array.from({length: ${DURATION_SECONDS * 10}}, (_, index) =>
    index % 101 < 8 ? null : -870 + Math.sin(index / 21) * 135 + Math.sin(index / 6) * 15);
  const confidence = contour.map(value => value === null ? 0 : .96);
  show({
    duration_seconds: ${DURATION_SECONDS},
    contour: {rate_hz: 10, units: 'cents_rel_A440', values: contour, confidence},
    robust_min_note: 'G3', robust_max_note: 'D4',
    quality: {classification: 'reliable', flags: []},
    metadata: {comparison_enabled: true},
    audio_urls: {
      vocals: realJob.result.audio_urls.vocals,
      instrumental: realJob.result.audio_urls.instrumental,
      original: realJob.result.audio_urls.vocals,
    },
    reference: {
      status: 'ready',
      contour: {rate_hz: 10, values: contour},
      native_contour: {rate_hz: 10, values: native, confidence: native.map(value => value === null ? 0 : .95)},
      provenance: {title: 'Four-minute performance fixture', uploader: 'VOXAI Phase 3'},
    },
    spectral: {status: 'ready', sources: {
      vocals: {status: 'ready', descriptor_url: '/phase3/spectral/vocals/descriptor', harmonic_tracks_url: '/phase3/spectral/vocals/harmonics'},
      original: {status: 'ready', descriptor_url: '/phase3/spectral/original/descriptor', harmonic_tracks_url: '/phase3/spectral/original/harmonics'},
    }},
    v2_analysis: null,
  });
  audio.pause();
  instrumental.pause();
  originalAudio.pause();
  playbackIntent = false;
  stopAnimationLoop();
  return {
    duration: scopeDuration(),
    contourPoints: contour.length,
    tileWidths,
    tileEncodedBytes: tileBlobs.reduce((sum, blob) => sum + blob.size, 0),
    defaultSpectralRequests: window.__phase3PerfRequests.slice(),
  };
})()`);

await waitFor('audio.readyState >= 1 && instrumental.readyState >= 1 && originalAudio.readyState >= 1');
const initialMedia = await evaluate(`({audioPaused: audio.paused, instrumentalPaused: instrumental.paused, originalPaused: originalAudio.paused})`);
await evaluate(`(() => {
  document.querySelector('#chartWrap').scrollIntoView({block: 'center'});
  originalOverlayOn = false;
  document.querySelector('#originalOverlay').setAttribute('aria-pressed', 'false');
  window.__phase3ToggleStarted = performance.now();
  spectralButton.click();
})()`);
await waitFor("chartVisible && spectralWindow && spectralWindow.source === 'vocals' && (draw(), spectralBlitted)");

const vocalReady = await evaluate(`(() => ({
  readyMs: performance.now() - window.__phase3ToggleStarted,
  requests: window.__phase3PerfRequests.slice(),
  tileRequests: window.__phase3PerfRequests.filter(url => url.includes('/vocals/tiles/')).length,
  harmonicRequests: window.__phase3PerfRequests.filter(url => url.includes('/vocals/harmonics')).length,
  cacheEntries: spectralImageCache.size,
  cacheBytes: [...spectralImageCache.values()].reduce((sum, entry) => sum + entry.bytes, 0),
  window: spectralWindow && {source: spectralWindow.source, width: spectralWindow.canvas.width, height: spectralWindow.canvas.height},
  blitted: (draw(), spectralBlitted),
  chartVisible,
}))()`);

await call('Emulation.setCPUThrottlingRate', {rate: 4});
await evaluate(`(() => {
  window.__phase3ProductObserve = observeSpectralFrame;
  window.__runPhase3Perf = async (label, durationMs = 8000) => {
    document.querySelector('#chartWrap').scrollIntoView({block: 'center'});
    const clock = activeClock();
    window.__phase3TickSamples = [];
    window.__phase3WatchdogMax = 0;
    observeSpectralFrame = now => {
      window.__phase3TickSamples.push({now, energy: spectralOn, blitted: spectralBlitted});
      const before = watchdogLowWindows, energyBefore = spectralOn;
      const output = window.__phase3ProductObserve(now);
      window.__phase3WatchdogMax = Math.max(
        window.__phase3WatchdogMax,
        before,
        watchdogLowWindows,
        energyBefore && !spectralOn ? SPECTRAL_WATCHDOG_FAILURES : 0,
      );
      return output;
    };
    resetSpectralWatchdog();
    if (clock.paused) await playWithStartupTimeout(clock);
    if (!originalMode) syncInstrument(true);
    const warmStartTime = clock.currentTime;
    await new Promise(resolve => {
      const started = performance.now();
      const warm = now => now - started >= 1500 ? resolve() : requestAnimationFrame(warm);
      requestAnimationFrame(warm);
    });
    resetSpectralWatchdog();
    window.__phase3WatchdogMax = 0;
    window.__phase3TickSamples = [];
    const longTasks = [];
    const longTaskTypeSupported = 'PerformanceObserver' in window &&
      PerformanceObserver.supportedEntryTypes?.includes('longtask');
    const observer = longTaskTypeSupported ? new PerformanceObserver(list => {
      for (const entry of list.getEntries()) longTasks.push(entry.duration);
    }) : null;
    let longTaskObserverStarted = false;
    try {
      observer?.observe({type: 'longtask', buffered: false});
      longTaskObserverStarted = Boolean(observer);
    } catch {}
    const startTime = clock.currentTime;
    await new Promise(resolve => {
      const started = performance.now();
      const finish = now => now - started >= durationMs ? resolve() : requestAnimationFrame(finish);
      requestAnimationFrame(finish);
    });
    observer?.disconnect();
    const samples = window.__phase3TickSamples.slice();
    const intervals = samples.slice(1).map((sample, index) => sample.now - samples[index].now);
    const elapsed = samples.length > 1 ? samples.at(-1).now - samples[0].now : 0;
    const sorted = intervals.slice().sort((a, b) => a - b);
    return {
      label,
      elapsedMs: elapsed,
      frames: samples.length,
      fps: elapsed ? (samples.length - 1) * 1000 / elapsed : 0,
      p95FrameMs: sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * .95))] || 0,
      maxFrameMs: Math.max(0, ...intervals),
      longTaskObserverSupported: longTaskObserverStarted,
      longTasksOver100ms: longTasks.filter(value => value > 100).length,
      maxLongTaskMs: Math.max(0, ...longTasks),
      playing: !clock.paused,
      mediaAdvancedDuringWarmup: clock.currentTime > warmStartTime + .2,
      timeAdvancedSeconds: clock.currentTime - startTime,
      energyStillOn: spectralOn,
      harmonicsStillOn: harmonicGuidesOn,
      activeSource: activeSpectralSource(),
      windowSource: spectralWindow?.source,
      watchdogLowWindows,
      watchdogMaxLowWindows: window.__phase3WatchdogMax,
      status: spectralStatus.textContent,
    };
  };
})()`);

const vocalEnergyPerformance = await evaluate(`(async () => {
  audio.currentTime = 0;
  instrumental.currentTime = 0;
  backgroundOn = true;
  document.querySelector('#background').setAttribute('aria-pressed', 'true');
  return window.__runPhase3Perf('vocal energy', 8000);
})()`);
writeJsonArtifact('phase3-vocal-energy.json', vocalEnergyPerformance);

const backgroundRecovery = await evaluate(`(async () => {
  if (instrumental.paused) {
    backgroundOn = false;
    document.querySelector('#background').click();
    await new Promise(resolve => setTimeout(resolve, 600));
  }
  return {playing: !instrumental.paused, driftMs: Math.round(Math.abs(instrumental.currentTime - audio.currentTime) * 1000), message: transportMessage.textContent};
})()`);

await evaluate(`(() => {
  originalOverlayOn = true;
  document.querySelector('#originalOverlay').setAttribute('aria-pressed', 'true');
  harmonicButton.click();
  invalidateScopeBounds();
  if (spectralOn) invalidateSpectralWindow();
  requestSpectralWindow(scopeGeometry(), true);
  draw();
})()`);
await waitFor("spectralWindow && spectralWindow.source === 'vocals' && harmonicTracks.has('vocals') && (draw(), spectralBlitted)");
const vocalAllPerformance = await evaluate("window.__runPhase3Perf('vocal all layers', 8000)");
writeJsonArtifact('phase3-vocal-all.json', vocalAllPerformance);

const driftRecovery = await evaluate(`(async () => {
  const introducedMs = 500;
  instrumental.currentTime = Math.min(instrumental.duration || audio.currentTime + .5, audio.currentTime + .5);
  const beforeMs = Math.round(Math.abs(instrumental.currentTime - audio.currentTime) * 1000);
  await new Promise(resolve => setTimeout(resolve, 800));
  return {introducedMs, beforeMs, afterMs: Math.round(Math.abs(instrumental.currentTime - audio.currentTime) * 1000)};
})()`);

const mobileABControl = await evaluate(`(() => {
  const button = document.querySelector('#mobileOriginalListen');
  const style = getComputedStyle(button);
  const rect = button.getBoundingClientRect();
  return {visible: style.display !== 'none' && rect.width >= 44 && rect.height >= 44,
    aboveScope: !!button.closest('.scope-head'), inTransport: !!button.closest('.transport')};
})()`);
await evaluate('toggleOriginalMode()');
await waitFor("originalMode && chartVisible && spectralWindow && spectralWindow.source === 'original' && harmonicTracks.has('original') && (draw(), spectralBlitted)");

const originalReady = await evaluate(`({
  requests: window.__phase3PerfRequests.slice(),
  originalTileRequests: window.__phase3PerfRequests.filter(url => url.includes('/original/tiles/')).length,
  cacheEntries: spectralImageCache.size,
  cacheBytes: [...spectralImageCache.values()].reduce((sum, entry) => sum + entry.bytes, 0),
  windowSource: spectralWindow?.source,
  guideSourceIsNative: activeGuideContour() === result.reference.native_contour,
  vocalPaused: audio.paused,
  instrumentalPaused: instrumental.paused,
  harmonicSource: document.querySelector('#harmonicSource').textContent,
})`);

const originalPerformance = await evaluate("window.__runPhase3Perf('original all layers', 8000)");
writeJsonArtifact('phase3-original-all.json', originalPerformance);
await evaluate('toggleOriginalMode()');
await waitFor("!originalMode && spectralWindow && spectralWindow.source === 'vocals' && !audio.paused");
await new Promise(resolve => setTimeout(resolve, 800));
const returnedVocal = await evaluate(`({
  activeSource: activeSpectralSource(),
  windowSource: spectralWindow?.source,
  originalPaused: originalAudio.paused,
  vocalPlaying: !audio.paused,
  instrumentalPlaying: !instrumental.paused,
  driftMs: Math.round(Math.abs(instrumental.currentTime - audio.currentTime) * 1000),
})`);

await call('Emulation.setCPUThrottlingRate', {rate: 1});
await evaluate('audio.pause(); instrumental.pause(); originalAudio.pause(); setOriginalModeState(false); draw()');
const capture = await call('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
const screenshotPath = artifactPath('phase3-four-minute-performance.png');
if (screenshotPath) {
  fs.writeFileSync(screenshotPath, Buffer.from(capture.data, 'base64'));
}

const results = {
  profile: {viewport: '390x844', deviceScaleFactor: 3, cpuThrottle: 4, fixtureDurationSeconds: DURATION_SECONDS},
  setup,
  initialMedia,
  vocalReady,
  vocalEnergyPerformance,
  backgroundRecovery,
  vocalAllPerformance,
  driftRecovery,
  mobileABControl,
  originalReady,
  originalPerformance,
  returnedVocal,
  consoleErrors,
  networkFailures,
  screenshot: screenshotPath,
};
const gateFailures = [];
const assert = (condition, message) => {
  if (!condition) gateFailures.push(message);
};
const assertProfile = (profile, {harmonics}) => {
  assert(profile.fps >= 45, `${profile.label}: ${profile.fps.toFixed(1)} FPS is below 45`);
  assert(profile.p95FrameMs <= 34, `${profile.label}: p95 ${profile.p95FrameMs.toFixed(1)} ms exceeds 34 ms`);
  assert(profile.maxFrameMs < 100, `${profile.label}: max frame ${profile.maxFrameMs.toFixed(1)} ms reached 100 ms`);
  assert(profile.longTaskObserverSupported, `${profile.label}: Long Tasks observer is unavailable`);
  assert(profile.longTasksOver100ms === 0, `${profile.label}: ${profile.longTasksOver100ms} long task(s) exceeded 100 ms`);
  assert(profile.playing && profile.mediaAdvancedDuringWarmup && profile.timeAdvancedSeconds > 1,
    `${profile.label}: media did not advance during the profile`);
  assert(profile.energyStillOn, `${profile.label}: the spectral watchdog disabled Energy`);
  assert(profile.harmonicsStillOn === harmonics, `${profile.label}: Harmonics state changed unexpectedly`);
  assert(profile.watchdogLowWindows === 0, `${profile.label}: watchdog recorded ${profile.watchdogLowWindows} low-FPS window(s)`);
  assert(profile.watchdogMaxLowWindows === 0, `${profile.label}: watchdog reached ${profile.watchdogMaxLowWindows} transient low-FPS window(s)`);
};
assertProfile(vocalEnergyPerformance, {harmonics: false});
assertProfile(vocalAllPerformance, {harmonics: true});
assertProfile(originalPerformance, {harmonics: true});
assert(vocalReady.blitted && vocalReady.tileRequests > 0, 'the spectral raster was not visible');
assert(backgroundRecovery.playing && backgroundRecovery.driftMs <= 120,
  `background recovery drifted by ${backgroundRecovery.driftMs} ms`);
assert(driftRecovery.afterMs <= 120, `forced background drift recovered only to ${driftRecovery.afterMs} ms`);
assert(mobileABControl.visible && mobileABControl.aboveScope && !mobileABControl.inTransport,
  'mobile Original A/B control is not accessible above the scope');
assert(originalReady.windowSource === 'original' && originalReady.guideSourceIsNative,
  'Original A/B did not switch both raster and guide sources');
assert(returnedVocal.windowSource === 'vocals' && returnedVocal.originalPaused && returnedVocal.vocalPlaying,
  'returning from Original A/B did not restore the vocal source');
assert(returnedVocal.driftMs <= 120, `returned vocal/background drift is ${returnedVocal.driftMs} ms`);
assert(consoleErrors.length === 0, `browser errors: ${consoleErrors.join(' | ')}`);
assert(networkFailures.length === 0, `network failures: ${networkFailures.join(' | ')}`);

results.gate = gateFailures.length ? 'failed' : 'pass';
results.gateFailures = gateFailures;
writeJsonArtifact('phase3-performance-result.json', results);
console.log(JSON.stringify(results, null, 2));
ws.close();
if (gateFailures.length) {
  throw new Error(`Phase 3 performance gate failed: ${gateFailures.join(' | ')}`);
}
