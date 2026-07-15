import fs from 'node:fs';

const CDP_URL = process.env.CDP_URL || 'http://127.0.0.1:9225';
const APP_URL = process.env.APP_URL || 'http://100.103.207.54:8877/';
const CHECKS = process.env.CHECKS || 'all';
const EVIDENCE_DIR = process.env.EVIDENCE_DIR || '';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const pages = await (await fetch(`${CDP_URL}/json/list`)).json();
const page = pages.find(item => item.type === 'page');
if (!page) throw new Error(`No browser page is available through ${CDP_URL}`);

const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.onopen = resolve;
  ws.onerror = reject;
});

let nextId = 1;
const pending = new Map();
const browserErrors = [];
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
    browserErrors.push(
      message.params.exceptionDetails?.exception?.description ||
      message.params.exceptionDetails?.text ||
      'Runtime exception',
    );
  }
  if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') {
    browserErrors.push(message.params.entry.text);
  }
  if (
    message.method === 'Runtime.consoleAPICalled' &&
    message.params.type === 'error'
  ) {
    browserErrors.push(
      message.params.args.map(value => value.value || value.description).join(' '),
    );
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
    throw new Error(
      output.exceptionDetails.exception?.description || output.exceptionDetails.text,
    );
  }
  return output.result.value;
};

const waitFor = async (expression, timeout = 8000) => {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 80));
  }
  throw new Error(`Timed out waiting for: ${expression}`);
};

async function setViewport(width, height, touch) {
  await call('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: touch ? 2 : 1,
    mobile: touch,
  });
  await call('Emulation.setTouchEmulationEnabled', {
    enabled: touch,
    ...(touch ? {maxTouchPoints: 5} : {}),
  });
}

async function navigate() {
  await call('Page.navigate', {url: APP_URL});
  await waitFor("document.readyState === 'complete'");
  await waitFor("typeof scopeDuration === 'function'");
}

await call('Page.enable');
await call('Runtime.enable');
await call('Log.enable');
await call('Network.enable');
await setViewport(1440, 900, false);
await navigate();

const pageState = await evaluate(`({
  title: document.title,
  contentLength: document.body.innerText.trim().length,
  overlay: !!document.querySelector('[data-nextjs-dialog],.vite-error-overlay,#webpack-dev-server-client-overlay')
})`);
assert(pageState.contentLength > 100, 'The application page is blank');
assert(!pageState.overlay, 'A browser error overlay is visible');

const results = {appUrl: APP_URL, page: pageState};

if (CHECKS === 'all' || CHECKS === 'ab') {
  const ab = await evaluate(`(() => {
    const aligned = {rate_hz: 10, values: Array(600).fill(-1200)};
    const native = {rate_hz: 10, values: Array(900).fill(-900)};
    result = {
      duration_seconds: 60,
      contour: {rate_hz: 10, values: Array(600).fill(-1200), confidence: Array(600).fill(.98)},
      reference: {status: 'ready', contour: aligned, native_contour: native},
    };
    clearTimeout(viewportTimer);
    viewportTimer = 0;
    viewer.style.display = 'block';
    wrap.style.width = '800px';
    wrap.style.height = '400px';
    resize();
    originalOverlayOn = true;
    Object.defineProperty(originalAudio, 'duration', {configurable: true, value: 92});
    const combinations = [];
    originalMode = true;
    for (const [energy, harmonics] of [[false,false],[true,false],[false,true],[true,true]]) {
      spectralOn = energy;
      harmonicGuidesOn = harmonics;
      combinations.push({
        energy,
        harmonics,
        duration: scopeDuration(),
        nativeReference: activeReferenceContour() === native,
        originalClock: activeClock() === originalAudio,
      });
    }
    delete originalAudio.duration;
    spectralOn = false;
    harmonicGuidesOn = false;
    const nativeFallbackDuration = scopeDuration();
    originalMode = false;
    const singer = {
      duration: scopeDuration(),
      alignedReference: activeReferenceContour() === aligned,
      vocalClock: activeClock() === audio,
    };
    const savedResult = result;
    result = null;
    setOriginalModeState(true);
    const controlsOn = [originalListen, mobileOriginalListen].map(button => ({
      text: button.textContent,
      pressed: button.getAttribute('aria-pressed'),
    }));
    setOriginalModeState(false);
    const controlsOff = [originalListen, mobileOriginalListen].map(button => ({
      text: button.textContent,
      pressed: button.getAttribute('aria-pressed'),
    }));
    result = savedResult;
    return {combinations, nativeFallbackDuration, singer, controlsOn, controlsOff};
  })()`);
  for (const state of ab.combinations) {
    assert(state.duration === 92, `A/B duration changed with layer state: ${JSON.stringify(state)}`);
    assert(state.nativeReference, 'A/B selected the aligned contour instead of native original');
    assert(state.originalClock, 'A/B did not retain original audio as master clock');
  }
  assert(ab.nativeFallbackDuration === 90, 'A/B native-contour duration fallback failed');
  assert(ab.singer.duration === 60, 'Singer mode did not retain singer duration');
  assert(ab.singer.alignedReference, 'Singer mode did not retain aligned comparison contour');
  assert(ab.singer.vocalClock, 'Singer mode did not retain vocal master clock');
  assert(ab.controlsOn.every(item => item.text === 'Return to vocal' && item.pressed === 'true'), 'A/B controls did not synchronize on');
  assert(ab.controlsOff.every(item => item.text === 'Original A/B' && item.pressed === 'false'), 'A/B controls did not synchronize off');
  results.ab = ab;
}

if (CHECKS === 'all' || CHECKS === 'scores') {
  const scores = await evaluate(`(() => {
    const host = document.createElement('div');
    host.innerHTML = scoreMeter(null, 'Missing fixture') + scoreMeter(0, 'Zero fixture') + scoreMeter(5, 'Midpoint fixture');
    const [missing, zero, midpoint] = host.querySelectorAll('[role="meter"]');
    return {
      missing: {
        text: scoreState(null).text,
        unavailable: missing.classList.contains('unavailable'),
        valueNow: missing.getAttribute('aria-valuenow'),
        valueText: missing.getAttribute('aria-valuetext'),
        hasFill: !!missing.querySelector('i'),
      },
      zero: {
        text: scoreState(0).text,
        unavailable: zero.classList.contains('unavailable'),
        valueNow: zero.getAttribute('aria-valuenow'),
        width: zero.querySelector('i')?.style.width,
      },
      midpoint: {
        valueNow: midpoint.getAttribute('aria-valuenow'),
        width: midpoint.querySelector('i')?.style.width,
      },
    };
  })()`);
  assert(scores.missing.text === 'Not available', 'Missing score text is not explicit');
  assert(scores.missing.unavailable, 'Missing score lacks unavailable meter state');
  assert(scores.missing.valueNow === null, 'Missing score has a numeric aria value');
  assert(scores.missing.valueText === 'Not available', 'Missing score lacks unavailable aria text');
  assert(!scores.missing.hasFill, 'Missing score still renders numeric fill geometry');
  assert(scores.zero.text === '0' && !scores.zero.unavailable, 'Measured zero was treated as unavailable');
  assert(scores.zero.valueNow === '0' && scores.zero.width === '0%', 'Measured zero lost its valid geometry');
  assert(scores.midpoint.valueNow === '5' && scores.midpoint.width === '50%', 'Measured midpoint geometry is incorrect');
  results.scores = scores;
}

if (CHECKS === 'all' || CHECKS === 'refinements') {
  await setViewport(1440, 900, false);
  await navigate();
  const refinements = await evaluate(`(() => {
    uploadCard.style.display = 'none';
    viewer.style.display = 'block';
    wrap.style.width = '1000px';
    wrap.style.height = '500px';
    canvas.width = 1000;
    canvas.height = 500;
    ctx.setTransform(1, 0, 0, 1, 0, 0);

    const reliableA = Array.from({length: 10}, (_, index) => -1200 + Math.sin(index / 2) * 8);
    const uncertain = Array.from({length: 10}, (_, index) => -1150 + Math.sin(index / 2) * 8);
    const breath = Array(10).fill(null);
    const reliableB = Array.from({length: 10}, (_, index) => -1100 + Math.sin(index / 2) * 8);
    const values = [...reliableA, ...uncertain, ...breath, ...reliableB];
    const confidence = [...Array(10).fill(.96), ...Array(10).fill(.2), ...Array(10).fill(null), ...Array(10).fill(.96)];
    const lowConfidence = [...Array(10).fill(false), ...Array(10).fill(true), ...Array(20).fill(false)];
    result = {
      duration_seconds: 4,
      contour: {rate_hz: 10, units: 'cents_rel_A440', values, confidence, low_confidence: lowConfidence},
      quality: {classification: 'caution', flags: ['low_pitch_confidence'], minimum_confidence: .55},
      metadata: {comparison_enabled: false},
      reference: {status: 'skipped'},
    };
    originalMode = false;
    originalOverlayOn = false;
    zoom = 1;
    offset = 0;
    const geometry = {w: 1000, h: 500, pad: 44, v: {start: 0, end: 4, window: 4}, lo: 36, hi: 96, range: 60};

    const spectrum = document.createElement('canvas');
    spectrum.width = geometry.w - geometry.pad;
    spectrum.height = geometry.h;
    const spectrumContext = spectrum.getContext('2d');
    const gradient = spectrumContext.createLinearGradient(0, 0, 0, spectrum.height);
    gradient.addColorStop(0, '#07121a');
    gradient.addColorStop(.5, '#416978');
    gradient.addColorStop(1, '#0b1820');
    spectrumContext.fillStyle = gradient;
    spectrumContext.fillRect(0, 0, spectrum.width, spectrum.height);
    for (const row of [90, 145, 205, 265, 325, 385]) {
      spectrumContext.fillStyle = 'rgba(210,245,255,.9)';
      spectrumContext.fillRect(0, row, spectrum.width, 3);
    }
    spectralWindow = {
      canvas: spectrum,
      source: 'vocals',
      start: 0,
      end: 4,
      viewWindow: 4,
      lo: geometry.lo,
      range: geometry.range,
      plotWidth: geometry.w - geometry.pad,
      height: geometry.h,
      pixelsPerSecond: (geometry.w - geometry.pad) / 4,
    };

    const pixels = () => new Uint8ClampedArray(ctx.getImageData(0, 0, geometry.w, geometry.h).data);
    const xAt = seconds => Math.round(geometry.pad + seconds / 4 * (geometry.w - geometry.pad));
    const difference = (baseline, image, startSeconds, endSeconds) => {
      const x0 = xAt(startSeconds), x1 = xAt(endSeconds);
      let changed = 0, energy = 0;
      for (let y = 0; y < geometry.h; y++) {
        for (let x = x0; x < x1; x++) {
          const index = (y * geometry.w + x) * 4;
          const delta = Math.abs(image[index] - baseline[index]) + Math.abs(image[index + 1] - baseline[index + 1]) + Math.abs(image[index + 2] - baseline[index + 2]);
          if (delta > 24) changed++;
          energy += delta;
        }
      }
      return {changed, energy};
    };
    const wholeDifference = (baseline, image) => difference(baseline, image, 0, 4);
    const render = (energyOn, harmonicsOn, accuracyOn = false) => {
      spectralOn = energyOn;
      harmonicGuidesOn = harmonicsOn;
      pitchColourOn = accuracyOn;
      renderStaticScope(geometry, [energyOn, harmonicsOn, accuracyOn, Math.random()].join(':'));
      return pixels();
    };

    spectralOn = false;
    harmonicGuidesOn = false;
    pitchColourOn = false;
    ctx.clearRect(0, 0, geometry.w, geometry.h);
    drawNoteLanes(geometry);
    const gridOnly = pixels();

    const realStroke = ctx.stroke.bind(ctx);
    const trace = [];
    ctx.stroke = (...args) => {
      trace.push({dash: [...ctx.getLineDash()], alpha: ctx.globalAlpha, width: ctx.lineWidth, style: String(ctx.strokeStyle)});
      return realStroke(...args);
    };
    const singerOnly = render(false, false, false);
    const accuracyOffTrace = trace.splice(0);
    render(false, false, true);
    const accuracyOnTrace = trace.splice(0);
    ctx.stroke = realStroke;

    ctx.clearRect(0, 0, geometry.w, geometry.h);
    drawNoteLanes(geometry);
    drawContour(
      [null, -1200], 1, {start: 0, end: 2, window: 2},
      geometry.lo, geometry.range, geometry.w, geometry.h, geometry.pad,
      '#3b82f6', 2, false, 0, [false, true],
    );
    const isolatedEndpoint = wholeDifference(gridOnly, pixels());

    const energyOnly = render(true, false, false);
    const harmonicsOnly = render(false, true, false);
    const allLayers = render(true, true, false);
    const reliableRegion = difference(gridOnly, singerOnly, .1, .9);
    const uncertainRegion = difference(gridOnly, singerOnly, 1.1, 1.9);
    const breathRegion = difference(gridOnly, singerOnly, 2.12, 2.88);
    const energyDelta = wholeDifference(singerOnly, energyOnly);
    const harmonicsDelta = wholeDifference(singerOnly, harmonicsOnly);
    const countReliableBlue = image => {
      let count = 0;
      for (let index = 0; index < image.length; index += 4) {
        const x = (index / 4) % geometry.w;
        const inReliableRegion = (x >= xAt(.1) && x < xAt(.9)) || (x >= xAt(3.1) && x < xAt(3.9));
        if (!inReliableRegion) continue;
        if (image[index + 2] >= 180 && image[index + 2] - Math.max(image[index], image[index + 1]) >= 60) count++;
      }
      return count;
    };
    const singerBluePixels = countReliableBlue(singerOnly), bluePixels = countReliableBlue(allLayers);
    const dashedOff = accuracyOffTrace.filter(item => item.dash.join(',') === LOW_CONFIDENCE_DASH.join(',') && Math.abs(item.alpha - LOW_CONFIDENCE_ALPHA) < .001).length;
    const dashedOn = accuracyOnTrace.filter(item => item.dash.join(',') === LOW_CONFIDENCE_DASH.join(',') && Math.abs(item.alpha - LOW_CONFIDENCE_ALPHA) < .001).length;
    wrap.scrollIntoView({block: 'center'});
    return {
      versionNeutral: {
        signal: document.querySelector('[data-stage="running_v2_analysis"]').textContent,
        oldVisibleLabels: ['V3 diagnostics', 'V2 calibrated score', 'V2 component profile'].filter(label => document.body.innerText.includes(label)),
      },
      contract: {
        lowCount: lowConfidence.filter(Boolean).length,
        breathNull: values.slice(20, 30).every(value => value === null),
        breathFlagsClear: lowConfidence.slice(20, 30).every(value => value === false),
      },
      contour: {reliableRegion, uncertainRegion, breathRegion, isolatedEndpoint, dashedOff, dashedOn},
      layers: {
        energyDelta,
        harmonicsDelta,
        singerBluePixels,
        bluePixels,
        spectralAlpha: SPECTRAL_DISPLAY_ALPHA,
        harmonicNearAlpha: HARMONIC_GUIDE_NEAR_ALPHA,
        harmonicFarAlpha: HARMONIC_GUIDE_FAR_ALPHA,
        harmonicWidth: HARMONIC_GUIDE_WIDTH,
        singerWidth: 2,
      },
    };
  })()`);
  if (EVIDENCE_DIR) {
    fs.mkdirSync(EVIDENCE_DIR, {recursive: true});
    fs.writeFileSync(
      `${EVIDENCE_DIR}/refinement-result.json`,
      `${JSON.stringify(refinements, null, 2)}\n`,
    );
  }
  assert(refinements.versionNeutral.signal === 'Calibrated analysis', 'Signal-chain wording is not version-neutral');
  assert(refinements.versionNeutral.oldVisibleLabels.length === 0, `Versioned labels remain visible: ${refinements.versionNeutral.oldVisibleLabels.join(', ')}`);
  assert(refinements.contract.lowCount === 10, 'Low-confidence fixture flags were not retained');
  assert(refinements.contract.breathNull && refinements.contract.breathFlagsClear, 'Unvoiced fixture was converted into uncertain pitch');
  assert(refinements.contour.reliableRegion.changed > 20, 'Reliable singer contour is not visible');
  assert(refinements.contour.uncertainRegion.changed > 8, 'Low-confidence singer contour is not visible');
  assert(refinements.contour.uncertainRegion.changed < refinements.contour.reliableRegion.changed, 'Low-confidence contour is not visually sparser than reliable pitch');
  assert(refinements.contour.breathRegion.changed === 0, `Singer contour crossed a breath gap (${refinements.contour.breathRegion.changed} changed pixels)`);
  assert(refinements.contour.isolatedEndpoint.changed > 0, 'An isolated low-confidence endpoint was not visible');
  assert(refinements.contour.dashedOff > 0, 'Low-confidence singer contour did not use a dotted stroke');
  assert(refinements.contour.dashedOn > refinements.contour.dashedOff, 'Accuracy overlay repainted uncertainty without dotted strokes');
  assert(refinements.layers.energyDelta.changed > 1000, 'Energy layer does not create a material visible delta');
  assert(refinements.layers.harmonicsDelta.changed > 100, 'Harmonic guides do not create a material visible delta');
  assert(refinements.layers.singerBluePixels > 20, 'Singer-only fixture did not establish a visible blue baseline');
  assert(refinements.layers.bluePixels >= refinements.layers.singerBluePixels * .9, 'Optional layers obscured more than 10% of the blue singer contour');
  assert(refinements.layers.spectralAlpha > .26 && refinements.layers.spectralAlpha < .6, 'Spectral visibility uplift is outside the guarded range');
  assert(refinements.layers.harmonicNearAlpha > .34 && refinements.layers.harmonicFarAlpha > .22, 'Harmonic guide visibility was not raised');
  assert(refinements.layers.harmonicWidth < refinements.layers.singerWidth, 'Harmonic guide width competes with singer contour');
  results.refinements = refinements;

  if (EVIDENCE_DIR) {
    fs.mkdirSync(EVIDENCE_DIR, {recursive: true});
    const scopeCanvas = await evaluate("canvas.toDataURL('image/png')");
    fs.writeFileSync(
      `${EVIDENCE_DIR}/refinement-scope-canvas.png`,
      Buffer.from(scopeCanvas.split(',')[1], 'base64'),
    );
    const screenshot = await call('Page.captureScreenshot', {
      format: 'png',
      captureBeyondViewport: false,
    });
    fs.writeFileSync(
      `${EVIDENCE_DIR}/refinement-layers.png`,
      Buffer.from(screenshot.data, 'base64'),
    );
  }
}

if (CHECKS === 'all' || CHECKS === 'layout') {
  const matrix = [
    {name: 'phone-portrait', width: 390, height: 844, touch: true, compact: true},
    {name: 'phone-landscape', width: 844, height: 390, touch: true, compact: true},
    {name: 'large-touch-landscape', width: 1024, height: 600, touch: true, compact: true},
    {name: 'tablet-touch-landscape', width: 1280, height: 720, touch: true, compact: true},
    {name: 'non-coarse-desktop-landscape', width: 1024, height: 600, touch: false, compact: false},
  ];
  results.layout = [];
  for (const entry of matrix) {
    await setViewport(entry.width, entry.height, entry.touch);
    await navigate();
    const state = await evaluate(`(() => {
      viewer.style.display = 'block';
      originalListen.disabled = false;
      mobileOriginalListen.disabled = false;
      const visible = element => getComputedStyle(element).display !== 'none';
      const rect = element => {
        const value = element.getBoundingClientRect();
        return {left:value.left, top:value.top, right:value.right, bottom:value.bottom, width:value.width, height:value.height};
      };
      return {
        landscape: matchMedia('(orientation:landscape)').matches,
        coarse: matchMedia('(pointer:coarse)').matches,
        noHover: matchMedia('(hover:none)').matches,
        compactQuery: matchMedia('(max-width:900px), (orientation:landscape) and (hover:none) and (pointer:coarse)').matches,
        transportPosition: getComputedStyle(document.querySelector('.transport')).position,
        transportRect: rect(document.querySelector('.transport')),
        mobileAbVisible: visible(mobileOriginalListen),
        desktopAbVisible: visible(originalListen),
        mobileAbRect: rect(mobileOriginalListen),
        playVisible: visible(playToggle),
        timeVisible: visible(document.querySelector('.timecode')),
        seekVisible: visible(seek),
        seekRect: rect(seek),
        backgroundVisible: visible(background),
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      };
    })()`);
    assert(state.compactQuery === entry.compact, `${entry.name}: media-query precondition mismatch`);
    assert(state.overflow <= 1, `${entry.name}: horizontal overflow is ${state.overflow}px`);
    assert(state.playVisible && state.timeVisible && state.seekVisible && state.backgroundVisible, `${entry.name}: a required transport control is hidden`);
    if (entry.compact) {
      assert(state.transportPosition === 'fixed', `${entry.name}: transport is not fixed`);
      assert(state.mobileAbVisible && !state.desktopAbVisible, `${entry.name}: accessible mobile A/B selection failed`);
      assert(state.mobileAbRect.width >= 44 && state.mobileAbRect.height >= 44, `${entry.name}: mobile A/B target is below 44px`);
      assert(state.seekRect.height >= 44, `${entry.name}: seek target is below 44px`);
      assert(state.transportRect.left >= 0 && state.transportRect.right <= entry.width + 1 && state.transportRect.bottom <= entry.height + 1, `${entry.name}: fixed transport leaves the viewport`);
    } else {
      assert(state.transportPosition === 'relative', `${entry.name}: non-coarse desktop baseline received compact transport`);
      assert(!state.mobileAbVisible && state.desktopAbVisible, `${entry.name}: desktop A/B selection failed`);
    }
    results.layout.push({...entry, ...state});
  }
}

await new Promise(resolve => setTimeout(resolve, 250));
assert(browserErrors.length === 0, `Browser errors: ${browserErrors.join(' | ')}`);
results.browserErrors = browserErrors;

if (EVIDENCE_DIR) {
  fs.mkdirSync(EVIDENCE_DIR, {recursive: true});
  fs.writeFileSync(
    `${EVIDENCE_DIR}/stop-ship-browser-result.json`,
    `${JSON.stringify(results, null, 2)}\n`,
  );
  const screenshot = await call('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
  });
  fs.writeFileSync(
    `${EVIDENCE_DIR}/stop-ship-browser.png`,
    Buffer.from(screenshot.data, 'base64'),
  );
}

console.log(JSON.stringify(results, null, 2));
ws.close();
