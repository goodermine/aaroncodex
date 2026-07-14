import fs from 'node:fs';
import path from 'node:path';

const CDP_URL = process.env.CDP_URL || 'http://127.0.0.1:9225';
const APP_URL = process.env.APP_URL || 'http://100.103.207.54:8877/';
const JOB_ID = process.env.JOB_ID || '';
const EVIDENCE_DIR = process.env.EVIDENCE_DIR || '';
const artifactPath = name => EVIDENCE_DIR ? path.join(EVIDENCE_DIR, name) : null;
if (!/^[0-9a-f-]{36}$/i.test(JOB_ID)) {
  throw new Error('Set JOB_ID to a completed pitch-viewer job UUID');
}
if (EVIDENCE_DIR) fs.mkdirSync(EVIDENCE_DIR, {recursive: true});

const pages = await (await fetch(`${CDP_URL}/json/list`)).json();
const page = pages.find(item => item.type === 'page' && item.url.startsWith(APP_URL)) ||
  pages.find(item => item.type === 'page');
if (!page) throw new Error(`No browser page is available through ${CDP_URL}`);

const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.onopen = resolve;
  ws.onerror = reject;
});

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
  if (output.exceptionDetails) {
    throw new Error(output.exceptionDetails.exception?.description || output.exceptionDetails.text);
  }
  return output.result.value;
};

const waitFor = async (expression, timeout = 12000) => {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 80));
  }
  throw new Error(`Timed out: ${expression}`);
};

const setViewport = async (width, height, angle = 0) => {
  await call('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    screenWidth: width,
    screenHeight: height,
    deviceScaleFactor: 3,
    mobile: true,
    screenOrientation: {
      type: angle === 0 ? 'portraitPrimary' : 'landscapePrimary',
      angle,
    },
  });
  await call('Emulation.setTouchEmulationEnabled', {
    enabled: true,
    maxTouchPoints: 5,
  });
};

const screenshot = async name => {
  const destination = artifactPath(name);
  await new Promise(resolve => setTimeout(resolve, 250));
  if (!destination) return null;
  const capture = await call('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
  });
  fs.writeFileSync(destination, Buffer.from(capture.data, 'base64'));
  return destination;
};

await call('Page.enable');
await call('Runtime.enable');
await call('Log.enable');
await call('Network.enable');
await setViewport(390, 844, 0);
await call('Page.navigate', {url: APP_URL});
await waitFor("document.readyState === 'complete'");

const initial = await evaluate(`(() => {
  const navigation = performance.getEntriesByType('navigation')[0];
  const paints = Object.fromEntries(performance.getEntriesByType('paint').map(entry => [entry.name, entry.startTime]));
  return {
    url: location.href,
    title: document.title,
    bodyCharacters: document.body.innerText.trim().length,
    overlay: !!document.querySelector('[data-nextjs-dialog],.vite-error-overlay,#webpack-dev-server-client-overlay'),
    keyElements: ['file','comparisonMode','spectralLayer','harmonicGuides','chart','playToggle','background'].every(id => !!document.getElementById(id)),
    timingMs: {
      domInteractive: navigation?.domInteractive ?? null,
      domContentLoaded: navigation?.domContentLoadedEventEnd ?? null,
      load: navigation?.loadEventEnd ?? null,
      firstContentfulPaint: paints['first-contentful-paint'] ?? null,
    },
  };
})()`);

const loaded = await evaluate(`(async () => {
  window.__phase3SpectralRequests = [];
  const realFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = String(input instanceof Request ? input.url : input);
    if (url.includes('/spectral/')) window.__phase3SpectralRequests.push(url);
    return realFetch(input, init);
  };
  const response = await realFetch('/api/pitch-jobs/${JOB_ID}');
  if (!response.ok) throw new Error('real Phase 3 fixture failed to load');
  const job = await response.json();
  show(job.result);
  return {
    status: job.status,
    duration: job.result.duration_seconds,
    points: job.result.contour.values.length,
    comparisonEnabled: job.result.metadata?.comparison_enabled,
  };
})()`);

await waitFor("result && viewer.style.display === 'block'");
await waitFor('audio.readyState >= 1 && instrumental.readyState >= 1');
const defaultState = await evaluate(`({
  spectralRequests: __phase3SpectralRequests.slice(),
  energyPressed: spectralButton.getAttribute('aria-pressed'),
  harmonicsPressed: harmonicButton.getAttribute('aria-pressed'),
})`);

await evaluate(`(() => {
  document.querySelector('.scope-deck').scrollIntoView({block: 'start'});
  spectralButton.click();
  harmonicButton.click();
})()`);
await waitFor("spectralWindow && spectralWindow.source === 'vocals' && harmonicTracks.has('vocals')");
const portraitScreenshot = await screenshot('phase3-mobile-portrait.png');

const portrait = await evaluate(`(() => {
  const visible = element => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
  };
  const targets = [...document.querySelectorAll('button,input[type="range"],summary')]
    .filter(visible)
    .map(element => {
      const rect = element.getBoundingClientRect();
      return {id: element.id, width: Math.round(rect.width * 10) / 10, height: Math.round(rect.height * 10) / 10};
    });
  const transport = document.querySelector('.transport');
  const transportRect = transport.getBoundingClientRect();
  const controls = document.querySelector('.scope-controls');
  return {
    viewport: [innerWidth, innerHeight],
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    scopeControlOverflowContained: controls.scrollWidth >= controls.clientWidth && document.documentElement.scrollWidth === document.documentElement.clientWidth,
    undersizedTargets: targets.filter(target => target.width < 44 || target.height < 44),
    targets,
    transport: {
      position: getComputedStyle(transport).position,
      withinViewport: transportRect.left >= 0 && transportRect.right <= innerWidth && transportRect.bottom <= innerHeight + 1,
      playVisible: visible(playToggle),
      seekVisible: visible(seek),
      backgroundVisible: visible(document.querySelector('#background')),
      originalHidden: !visible(document.querySelector('#originalListen')),
      durationHidden: !visible(document.querySelector('#durationTime')),
    },
    layerState: {
      energy: spectralButton.getAttribute('aria-pressed'),
      harmonics: harmonicButton.getAttribute('aria-pressed'),
      blitted: (draw(), spectralBlitted),
      harmonicRows: document.querySelectorAll('[data-harmonic]').length,
    },
  };
})()`);

const playbackStart = await evaluate(`(async () => {
  audio.currentTime = 5;
  instrumental.currentTime = 5;
  backgroundOn = true;
  document.querySelector('#background').setAttribute('aria-pressed', 'true');
  await audio.play();
  syncInstrument(true);
  return {paused: audio.paused, currentTime: audio.currentTime};
})()`);
await new Promise(resolve => setTimeout(resolve, 900));
const playbackBeforeRotate = await evaluate(`({
  paused: audio.paused,
  currentTime: audio.currentTime,
  instrumentalPaused: instrumental.paused,
  driftMs: Math.round(Math.abs(instrumental.currentTime - audio.currentTime) * 1000),
  energy: spectralOn,
  harmonics: harmonicGuidesOn,
})`);

await setViewport(844, 390, 90);
await evaluate("window.dispatchEvent(new Event('orientationchange'))");
await new Promise(resolve => setTimeout(resolve, 450));
const landscapeScreenshot = await screenshot('phase3-mobile-landscape.png');
const landscape = await evaluate(`(() => {
  const visible = element => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
  };
  const transport = document.querySelector('.transport');
  const rect = transport.getBoundingClientRect();
  return {
    viewport: [innerWidth, innerHeight],
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    transport: {
      position: getComputedStyle(transport).position,
      withinViewport: rect.left >= 0 && rect.right <= innerWidth && rect.bottom <= innerHeight + 1,
      originalHidden: !visible(document.querySelector('#originalListen')),
      durationHidden: !visible(document.querySelector('#durationTime')),
    },
    playbackPreserved: !audio.paused,
    timeAdvanced: audio.currentTime > ${playbackBeforeRotate.currentTime},
    driftMs: Math.round(Math.abs(instrumental.currentTime - audio.currentTime) * 1000),
    energyPreserved: spectralOn,
    harmonicsPreserved: harmonicGuidesOn,
    spectralWindowReady: !!spectralWindow && spectralWindow.source === 'vocals',
  };
})()`);

const interaction = await evaluate(`(async () => {
  const beforeSeek = audio.currentTime;
  seek.value = 420;
  seek.dispatchEvent(new Event('input', {bubbles: true}));
  await new Promise(resolve => setTimeout(resolve, 180));
  const expected = (audio.duration || scopeDuration()) * .42;
  const seekErrorMs = Math.round(Math.abs(audio.currentTime - expected) * 1000);
  audio.playbackRate = 1.25;
  await new Promise(resolve => setTimeout(resolve, 180));
  const rateSynced = instrumental.playbackRate === 1.25;
  const driftAfterSeekMs = Math.round(Math.abs(instrumental.currentTime - audio.currentTime) * 1000);
  document.querySelector('#plus').click();
  await new Promise(resolve => setTimeout(resolve, 260));
  document.dispatchEvent(new Event('visibilitychange'));
  await new Promise(resolve => setTimeout(resolve, 120));
  return {
    beforeSeek,
    seekErrorMs,
    rateSynced,
    driftAfterSeekMs,
    zoom,
    energy: spectralOn,
    harmonics: harmonicGuidesOn,
    windowCoversView: spectralWindowCovers(scopeGeometry()),
    stillPlaying: !audio.paused,
  };
})()`);

const lifecycle = await evaluate(`(async () => {
  const generationBefore = spectralGeneration;
  const windowBefore = spectralWindow;
  for (let index = 0; index < 5; index++) window.dispatchEvent(new Event('resize'));
  await new Promise(resolve => setTimeout(resolve, 350));
  const unchangedResize = {
    generationStable: spectralGeneration === generationBefore,
    windowStable: spectralWindow === windowBefore,
    stillCoversView: spectralWindowCovers(scopeGeometry()),
  };

  setOriginalModeState(false);
  backgroundOn = true;
  audio.playbackRate = 1.25;
  playbackIntent = true;
  if (audio.paused) await playWithStartupTimeout(audio);
  lifecycleSnapshot = null;
  rememberLifecycleState();
  const interruptedSnapshot = {...lifecycleSnapshot};
  audio.pause();
  await restoreLifecycleState();
  await new Promise(resolve => setTimeout(resolve, 180));
  const systemInterrupted = {
    snapshotResume: interruptedSnapshot.resume,
    resumed: !audio.paused,
    rateRestored: audio.playbackRate === 1.25,
    backgroundRestored: backgroundOn,
    driftMs: Math.round(Math.abs(instrumental.currentTime - audio.currentTime) * 1000),
  };

  playbackIntent = false;
  audio.pause();
  lifecycleSnapshot = null;
  rememberLifecycleState();
  const pausedSnapshot = {...lifecycleSnapshot};
  await restoreLifecycleState();
  const userPaused = {
    snapshotResume: pausedSnapshot.resume,
    remainedPaused: audio.paused,
  };

  lifecycleSnapshot = {resume: true};
  playbackIntent = true;
  pauseFromExternalControl();
  const externalPausePolicy = {
    snapshotCleared: lifecycleSnapshot.resume === false,
    intentCleared: playbackIntent === false,
    remainedPaused: audio.paused,
  };
  lifecycleSnapshot = null;

  const realPlay = audio.play;
  audio.play = () => Promise.reject(new DOMException('gesture required', 'NotAllowedError'));
  playbackIntent = true;
  lifecycleSnapshot = {
    resume: true,
    originalMode: false,
    position: audio.currentTime,
    rate: 1,
    backgroundOn: true,
  };
  await restoreLifecycleState();
  audio.play = realPlay;
  const rejectedResume = {
    remainedPaused: audio.paused,
    exactFallback: transportMessage.textContent === 'Tap play to resume after returning to VOXAI.',
    message: transportMessage.textContent,
  };
  playbackIntent = false;
  audio.pause();
  instrumental.pause();
  const delayed = {paused: true, cancelled: false, pauseCalls: 0};
  delayed.play = () => new Promise(resolve => setTimeout(() => {
    if (!delayed.cancelled) delayed.paused = false;
    resolve();
  }, 1700));
  delayed.pause = () => {
    delayed.cancelled = true;
    delayed.paused = true;
    delayed.pauseCalls++;
  };
  const timeoutStarted = performance.now();
  let timeoutRejected = false;
  try { await playWithStartupTimeout(delayed); } catch { timeoutRejected = true; }
  await new Promise(resolve => setTimeout(resolve, 260));
  const delayedStart = {
    timeoutRejected,
    elapsedMs: Math.round(performance.now() - timeoutStarted),
    pauseCalled: delayed.pauseCalls > 0,
    remainedPaused: delayed.paused,
  };
  return {unchangedResize, systemInterrupted, userPaused, externalPausePolicy, rejectedResume, delayedStart};
})()`);

await call('Emulation.setEmulatedMedia', {features: [{name: 'prefers-reduced-motion', value: 'reduce'}]});
const reducedMotion = await evaluate(`(() => {
  const sample = document.querySelector('button');
  return {
    matches: matchMedia('(prefers-reduced-motion: reduce)').matches,
    transitionDuration: getComputedStyle(sample).transitionDuration,
    animationDuration: getComputedStyle(document.querySelector('.bar i')).animationDuration,
  };
})()`);

const results = {
  initial,
  loaded,
  defaultState,
  portrait,
  playbackStart,
  playbackBeforeRotate,
  landscape,
  interaction,
  lifecycle,
  reducedMotion,
  consoleErrors,
  networkFailures,
  screenshots: [portraitScreenshot, landscapeScreenshot].filter(Boolean),
};
const resultPath = artifactPath('phase3-mobile-lifecycle-result.json');
if (resultPath) fs.writeFileSync(resultPath, `${JSON.stringify(results, null, 2)}\n`);
console.log(JSON.stringify(results, null, 2));

ws.close();
