# Live Harmonic Scope browser stop-ship harness

`stop_ship_browser_check.mjs` is the durable regression harness for the five
technical blockers closed after the original Live Harmonic Scope audit. It has
no npm dependencies and targets an already-running Chromium debugging endpoint.

It verifies:

- Original A/B uses native-original time, pitch and clock with Energy and
  Harmonics both off or on;
- desktop and mobile Original A/B controls keep synchronized state;
- missing component scores have unavailable semantics while measured zero
  remains a valid zero-width measurement;
- compact transport selection at phone widths and above 900 CSS pixels on a
  coarse-pointer landscape device;
- desktop transport selection for a non-coarse landscape baseline;
- 44 px A/B and seek targets, viewport containment, horizontal overflow,
  meaningful page content and browser errors;
- version-neutral analysis labels;
- dotted, dimmed detected-low-confidence pitch without bridging unvoiced gaps;
- materially visible Energy and Harmonics layers with the blue singer contour
  retained above them.

Example against the isolated Tailnet server:

```bash
APP_URL=http://100.103.207.54:8877/ \
CDP_URL=http://127.0.0.1:9225 \
EVIDENCE_DIR=/tmp/voxai-stop-ship-evidence \
node vox-analysis/viewer/tests/browser/stop_ship_browser_check.mjs
```

Use `CHECKS=ab`, `CHECKS=scores`, `CHECKS=refinements` or `CHECKS=layout` for a focused gate after a related fix.
The full release gate uses the default `CHECKS=all`.

This automated harness complements, but does not replace, the required
physical iPhone Safari and Android Chrome comparison-workflow checks.

The material Phase 2 rendering/lazy-cache, Phase 3 mobile/lifecycle, and Phase 3
four-minute performance profiles are preserved under [`phase-gates/`](phase-gates/README.md).
Those scripts retain the broader browser evidence that this focused stop-ship
harness intentionally does not reproduce.
