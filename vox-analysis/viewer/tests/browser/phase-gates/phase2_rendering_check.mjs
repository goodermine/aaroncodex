import fs from 'node:fs';
import path from 'node:path';

const CDP_URL = process.env.CDP_URL || 'http://127.0.0.1:9225';
const APP_URL = process.env.APP_URL || 'http://100.103.207.54:8877/';
const EVIDENCE_DIR = process.env.EVIDENCE_DIR || '';
const artifactPath = name => EVIDENCE_DIR ? path.join(EVIDENCE_DIR, name) : null;
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
  if (message.method === 'Log.entryAdded' && ['error', 'warning'].includes(message.params.entry.level)) {
    consoleErrors.push(message.params.entry.text);
  }
  if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
    consoleErrors.push(message.params.args.map(value => value.value || value.description).join(' '));
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
const waitFor = async (expression, timeout = 6000) => {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 80));
  }
  throw new Error(`Timed out: ${expression}`);
};

await call('Page.enable');
await call('Runtime.enable');
await call('Log.enable');
await call('Network.enable');
await call('Emulation.setDeviceMetricsOverride', {
  width: 1440,
  height: 900,
  deviceScaleFactor: 1,
  mobile: false,
});
await call('Page.navigate', {url: APP_URL});
await waitFor("document.readyState === 'complete'");

const initialPage = await evaluate(`({
  content: document.body.innerText.trim().length,
  overlay: !!document.querySelector('[data-nextjs-dialog],.vite-error-overlay,#webpack-dev-server-client-overlay'),
  title: document.title
})`);

const fixtureSetup = await evaluate(`(async () => {
  const tile = document.createElement('canvas');
  tile.width = 120;
  tile.height = 180;
  const tileContext = tile.getContext('2d');
  const gradient = tileContext.createLinearGradient(0, 0, 0, 180);
  gradient.addColorStop(0, '#050505');
  gradient.addColorStop(1, '#202020');
  tileContext.fillStyle = gradient;
  tileContext.fillRect(0, 0, 120, 180);
  for (const row of [116, 80, 59, 44, 33, 24, 16, 8]) {
    tileContext.fillStyle = 'rgba(235,245,248,.82)';
    tileContext.fillRect(0, row, 120, 2);
  }
  const tileBlob = await new Promise(resolve => tile.toBlob(resolve, 'image/png'));

  const wav = new Uint8Array(44 + 8000);
  const wavView = new DataView(wav.buffer);
  const write = (at, value) => {
    for (let index = 0; index < value.length; index++) wav[at + index] = value.charCodeAt(index);
  };
  write(0, 'RIFF');
  wavView.setUint32(4, 36 + 8000, true);
  write(8, 'WAVEfmt ');
  wavView.setUint32(16, 16, true);
  wavView.setUint16(20, 1, true);
  wavView.setUint16(22, 1, true);
  wavView.setUint32(24, 8000, true);
  wavView.setUint32(28, 8000, true);
  wavView.setUint16(32, 1, true);
  wavView.setUint16(34, 8, true);
  write(36, 'data');
  wavView.setUint32(40, 8000, true);
  wav.fill(128, 44);
  const audioUrl = URL.createObjectURL(new Blob([wav], {type: 'audio/wav'}));

  window.__spectralRequests = [];
  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const url = String(input instanceof Request ? input.url : input);
    if (!url.includes('/mock/spectral/')) return realFetch(input, init);
    window.__spectralRequests.push(url);
    const source = url.includes('/original/') ? 'original' : 'vocals';
    if (url.endsWith('/descriptor')) {
      const descriptor = {
        version: 'voxai_spectral_v1', source, transform: 'librosa.cqt', display_only: true,
        t0: 0, fps: 21.533203125, duration_seconds: 120 / 21.533203125,
        total_frames: 120, midi_lo: 36, midi_hi: 96, bins_per_semitone: 3,
        n_bins: 180, row_order: 'high_to_low', db_floor: -80, db_ceil: 0,
        tiles: [{index: 0, frame_start: 0, frame_count: 120, width: 120, height: 180,
          url: '/mock/spectral/' + source + '/tiles/0'}],
      };
      return new Response(JSON.stringify(descriptor), {status: 200, headers: {'Content-Type': 'application/json'}});
    }
    if (url.endsWith('/harmonics')) {
      const values = {};
      for (let harmonic = 1; harmonic <= 8; harmonic++) {
        values['H' + harmonic] = Array.from({length: 56}, (_, index) =>
          index % 19 === 0 ? null : Math.max(-80, -3.5 * (harmonic - 1) - Math.sin(index / 4) * 2));
      }
      return new Response(JSON.stringify({
        version: 'voxai_spectral_v1', rate_hz: 10, t0: 0,
        units: 'db_relative_to_strongest_available_harmonic_per_frame', values,
      }), {status: 200, headers: {'Content-Type': 'application/json'}});
    }
    if (url.includes('/tiles/')) {
      if (source === 'vocals' && window.__holdVocalTile) {
        return new Promise((resolve, reject) => {
          const abort = () => {
            window.__oldAbortObserved = true;
            reject(new DOMException('superseded', 'AbortError'));
          };
          if (init?.signal?.aborted) abort();
          else init?.signal?.addEventListener('abort', abort, {once: true});
        });
      }
      return new Response(tileBlob, {status: 200, headers: {'Content-Type': 'image/png'}});
    }
    return new Response('', {status: 404});
  };

  const values = Array.from({length: 56}, (_, index) => -1200 + Math.sin(index / 3) * 18);
  const confidence = Array(56).fill(.96);
  const native = Array.from({length: 56}, (_, index) => -900 + Math.sin(index / 4) * 14);
  show({
    duration_seconds: 5.6,
    contour: {rate_hz: 10, units: 'cents_rel_A440', values, confidence},
    robust_min_note: 'A3', robust_max_note: 'A3',
    quality: {classification: 'reliable', flags: []},
    metadata: {comparison_enabled: true},
    audio_urls: {vocals: audioUrl, instrumental: audioUrl, original: audioUrl},
    reference: {
      status: 'ready',
      contour: {rate_hz: 10, values},
      native_contour: {rate_hz: 10, values: native, confidence},
      provenance: {title: 'Synthetic Harmonic Take', uploader: 'VOXAI Ground Truth'},
    },
    spectral: {status: 'ready', sources: {
      vocals: {status: 'ready', descriptor_url: '/mock/spectral/vocals/descriptor', harmonic_tracks_url: '/mock/spectral/vocals/harmonics'},
      original: {status: 'ready', descriptor_url: '/mock/spectral/original/descriptor', harmonic_tracks_url: '/mock/spectral/original/harmonics'},
    }},
    v2_analysis: null,
  });
  return true;
})()`);

await new Promise(resolve => setTimeout(resolve, 250));
const defaultState = await evaluate(`({
  requests: __spectralRequests.slice(),
  energyDisabled: spectralButton.disabled,
  energyPressed: spectralButton.getAttribute('aria-pressed'),
  harmonicDisabled: harmonicButton.disabled,
  harmonicPressed: harmonicButton.getAttribute('aria-pressed'),
  status: spectralStatus.textContent
})`);

await evaluate('spectralButton.click()');
await waitFor("spectralWindow && spectralWindow.source === 'vocals'");
const energyState = await evaluate(`({
  requests: __spectralRequests.slice(),
  source: spectralWindow.source,
  blitted: (draw(), spectralBlitted),
  harmonicsLoaded: harmonicTracks.has('vocals'),
  cacheSize: spectralImageCache.size,
  canvas: [spectralCanvas.width, spectralCanvas.height]
})`);

await evaluate('harmonicButton.click()');
await waitFor("harmonicTracks.has('vocals')");
await evaluate("audio.currentTime = .5; draw(); document.querySelector('.scope-deck').scrollIntoView({block: 'start'}); document.querySelector('.scope-deck').style.transform = 'translateZ(0)'; document.body.offsetHeight");
await new Promise(resolve => setTimeout(resolve, 500));
const harmonicState = await evaluate(`({
  requests: __spectralRequests.slice(),
  readoutHidden: document.querySelector('#harmonicReadout').hidden,
  guidePressed: harmonicButton.getAttribute('aria-pressed'),
  sourceLabel: document.querySelector('#harmonicSource').textContent,
  meterRows: document.querySelectorAll('[data-harmonic]').length,
  status: spectralStatus.textContent
})`);

await call('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
await new Promise(resolve => setTimeout(resolve, 300));
const screenshot = await call('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
const screenshotPath = artifactPath('phase2-rendering.png');
if (screenshotPath) {
  fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, 'base64'));
}

await evaluate('setOriginalModeState(true)');
await waitFor("spectralWindow && spectralWindow.source === 'original' && harmonicTracks.has('original')");
const originalState = await evaluate(`({
  active: activeSpectralSource(),
  windowSource: spectralWindow.source,
  requests: __spectralRequests.slice(),
  readout: document.querySelector('#harmonicSource').textContent
})`);

await evaluate(`setOriginalModeState(false); clearSpectralImageCache(); invalidateSpectralWindow(); window.__holdVocalTile = true; window.__oldAbortObserved = false; requestSpectralWindow(scopeGeometry(), true)`);
await waitFor("spectralBuildPromise !== null");
await evaluate('setOriginalModeState(true)');
await waitFor("spectralWindow && spectralWindow.source === 'original'");
const abortRaceState = await evaluate(`({
  oldFetchAborted: window.__oldAbortObserved,
  active: activeSpectralSource(),
  windowSource: spectralWindow.source,
  buildActive: spectralBuildPromise === null || spectralWindow.source === activeSpectralSource()
})`);
await evaluate('window.__holdVocalTile = false; setOriginalModeState(false)');
await waitFor("spectralWindow && spectralWindow.source === 'vocals'");

const missingOriginalState = await evaluate(`(() => {
  spectralSources.delete('original');
  setOriginalModeState(true);
  return {
    active: activeSpectralSource(),
    energyDisabled: spectralButton.disabled,
    harmonicDisabled: harmonicButton.disabled,
    windowCleared: spectralWindow === null,
    status: spectralStatus.textContent,
  };
})()`);

await evaluate('setOriginalModeState(false)');
await waitFor("spectralWindow && spectralWindow.source === 'vocals'");
const restoredState = await evaluate(`({
  active: activeSpectralSource(),
  energyDisabled: spectralButton.disabled,
  harmonicDisabled: harmonicButton.disabled,
  energyPressed: spectralButton.getAttribute('aria-pressed'),
  windowSource: spectralWindow.source
})`);

const watchdogState = await evaluate(`(() => {
  const savedClock = activeClock;
  activeClock = () => ({paused: false, currentTime: 0});
  spectralWanted = true; spectralOn = true; spectralBlitted = true; chartVisible = true;
  resetSpectralWatchdog();
  watchdogGraceUntil = 0;
  for (let now = 20; now <= 4200; now += 20) {
    spectralBlitted = true;
    observeSpectralFrame(now);
  }
  const pass45 = spectralOn;
  resetSpectralWatchdog();
  watchdogGraceUntil = 0;
  spectralWanted = true; spectralOn = true; spectralBlitted = true;
  for (let now = 34; now <= 4500; now += 34) {
    spectralBlitted = true;
    observeSpectralFrame(now);
    if (!spectralOn) break;
  }
  const disabledBelow45 = !spectralOn;
  const notice = spectralStatus.textContent;
  activeClock = savedClock;
  return {pass45, disabledBelow45, notice};
})()`);

const cacheEvictionState = await evaluate(`(() => {
  clearSpectralImageCache();
  const closed = [];
  for (let index = 0; index < 9; index++) {
    spectralImageCache.set('mock:' + index, {
      image: {close: () => closed.push(index)},
      bytes: 1024,
    });
  }
  trimSpectralImageCache();
  return {
    size: spectralImageCache.size,
    oldestClosed: closed[0] === 0,
    closed,
    retained: [...spectralImageCache.keys()],
    withinEntryLimit: spectralImageCache.size <= SPECTRAL_CACHE_LIMIT,
    withinByteLimit: [...spectralImageCache.values()].reduce((sum, entry) => sum + entry.bytes, 0) <= SPECTRAL_CACHE_BYTES,
  };
})()`);

const finalPage = await evaluate(`({
  content: document.body.innerText.trim().length,
  overlay: !!document.querySelector('[data-nextjs-dialog],.vite-error-overlay,#webpack-dev-server-client-overlay'),
  scope: !!document.querySelector('#chart'),
  status: spectralStatus.textContent
})`);

const results = {
  initialPage, fixtureSetup, defaultState, energyState, harmonicState, originalState, abortRaceState,
  missingOriginalState, restoredState, watchdogState, finalPage, consoleErrors,
  cacheEvictionState,
  screenshot: screenshotPath,
};
const resultPath = artifactPath('phase2-rendering-result.json');
if (resultPath) fs.writeFileSync(resultPath, `${JSON.stringify(results, null, 2)}\n`);
console.log(JSON.stringify(results, null, 2));
ws.close();
