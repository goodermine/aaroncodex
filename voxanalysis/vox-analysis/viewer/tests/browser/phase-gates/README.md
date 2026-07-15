# Preserved browser phase gates

These dependency-free Node/CDP harnesses preserve the material browser checks
used during the Live Harmonic Scope build. They complement
`../stop_ship_browser_check.mjs`; they are not substitutes for physical iPhone
Safari or Android Chrome testing.

## Requirements

- Node.js 22 or newer, providing global `fetch` and `WebSocket`;
- an isolated Chromium instance with remote debugging enabled;
- a running pitch viewer reachable through `APP_URL`;
- for the mobile/lifecycle and performance profiles, a completed job UUID from
  that same server with playable vocal and instrumental audio.

All scripts accept:

- `APP_URL` — pitch-viewer root, default `http://100.103.207.54:8877/`;
- `CDP_URL` — Chromium debugging endpoint, default `http://127.0.0.1:9225`;
- `EVIDENCE_DIR` — optional directory for JSON and PNG artifacts. With no
  value, results are printed to stdout and no artifact files are written.

The mobile/lifecycle and performance scripts additionally require `JOB_ID`.
They reject a missing or malformed UUID instead of silently using a stale
temporary fixture.

## Harnesses

### Phase 2 rendering and lazy-cache behavior

`phase2_rendering_check.mjs` uses deterministic in-page audio and spectral
fixtures. It exercises default-off lazy requests, Energy and Harmonics, source
switching, stale-fetch cancellation, missing-original isolation, watchdog
behavior, and cache eviction.

```bash
APP_URL=http://100.103.207.54:8877/ \
CDP_URL=http://127.0.0.1:9225 \
EVIDENCE_DIR=/tmp/voxai-phase-gates/phase2 \
node vox-analysis/viewer/tests/browser/phase-gates/phase2_rendering_check.mjs
```

### Phase 3 mobile and lifecycle behavior

`phase3_mobile_lifecycle_check.mjs` exercises the real media endpoints from a
completed job, portrait/landscape layout, transport hitboxes, rotation while
playing, seek/rate/background synchronization, same-size resize, foreground
recovery policy, explicit external pause, blocked resume, delayed-start
cancellation, and reduced motion.

```bash
APP_URL=http://100.103.207.54:8877/ \
CDP_URL=http://127.0.0.1:9225 \
JOB_ID=<completed-job-uuid> \
EVIDENCE_DIR=/tmp/voxai-phase-gates/mobile \
node vox-analysis/viewer/tests/browser/phase-gates/phase3_mobile_lifecycle_check.mjs
```

### Phase 3 four-minute performance profile

`phase3_performance_check.mjs` combines real job audio with a deterministic
four-minute contour, harmonic tracks, and three synthetic spectral tiles. It
profiles Vocal + Energy, Vocal + all layers, and Original A/B + all layers at
4x CPU throttle. It also records opt-in requests, cache use, watchdog state,
background/drift recovery, source isolation, and long tasks.

```bash
APP_URL=http://100.103.207.54:8877/ \
CDP_URL=http://127.0.0.1:9225 \
JOB_ID=<completed-job-uuid> \
EVIDENCE_DIR=/tmp/voxai-phase-gates/performance \
node vox-analysis/viewer/tests/browser/phase-gates/phase3_performance_check.mjs
```

The performance release budget remains: visually smooth playback, no recurring
long task above 100 ms, and no watchdog removal during normal playback. Preserve
the full JSON output with the device, Chromium version, host, and throttle
context; headless same-host results are not physical-device or remote-Tailnet
latency evidence.
