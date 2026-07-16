/* ============================================================================
   VOX Suite — telemetry client  (Visual System v0.1 · §04, §07)
   Framework-free. Implements design/telemetry-contract.md: normalise a job's
   native status into the shared event, and drive the deck's live components
   (state LED, signal chain, processing bar, log, meters, gauges). Bound to real
   stages — never faked. Vendored into both apps by design/sync.sh.

   Global: window.VOX
   ============================================================================ */
(function (root) {
  "use strict";

  var REDUCE = matchMedia("(prefers-reduced-motion:reduce)").matches;

  /* ---- chains per mode (must match telemetry-contract.md) ------------------ */
  var CHAINS = {
    polish: [
      ["01", "Upload", "upload"], ["02", "Separate", "separate"], ["03", "Clean", "clean"],
      ["04", "Gate·Breath", "gate_breath"], ["05", "Sibilance", "sibilance"], ["06", "Tune", "tune"],
      ["07", "Render", "render"], ["08", "Export", "export"]
    ],
    analyze: [
      ["01", "Upload", "upload"], ["02", "Isolate", "isolate"], ["03", "Track pitch", "pitch"],
      ["04", "Analysis", "analysis"], ["05", "Find orig.", "match"], ["06", "Align", "align"],
      ["07", "Report", "report"]
    ],
    fused: [
      ["01", "Upload", "upload"], ["02", "Isolate", "isolate"], ["03", "Analyze", "analyze"],
      ["04", "Score", "score"], ["05", "Clean", "clean"], ["06", "Tune", "tune"],
      ["07", "Render", "render"], ["08", "Export", "export"]
    ]
  };

  /* state -> LED modifier class on .vox-led */
  var STATE_LED = {
    STANDBY: "is-standby", WORKING: "is-working", COMPLETE: "is-done",
    ALERT: "is-alert", ANALYZE: "is-analyze"
  };

  function el(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  var ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };
  function escHtml(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return ESC[c]; }); }

  // A failed event, rendered as escaped "<code> · <reason>" — safe to inject as
  // HTML. reason comes from the server's short, sanitised failure detail so a
  // failure explains itself on-screen without opening a log.
  function alertText(ev) {
    var e = (ev && ev.error) || {}, reason = e.reason || e.message || "", code = e.code || "error";
    return escHtml(code) + (reason && reason !== code
      ? ' <em style="font-style:normal;color:var(--vox-muted)">· ' + escHtml(reason) + "</em>" : "");
  }

  /* ---- render helpers ------------------------------------------------------ */

  // Build/refresh a .vox-chain from a mode + active step index.
  function renderChain(container, mode, activeIndex) {
    var steps = CHAINS[mode] || CHAINS.analyze, html = "";
    steps.forEach(function (s, i) {
      var cls = i < activeIndex ? "is-done" : (i === activeIndex ? "is-active" : "");
      html += '<div class="vox-step ' + cls + '"><span class="vox-step__n">' + s[0] + "</span>" + s[1] + "</div>";
    });
    container.innerHTML = html;
  }

  // Set the canonical state LED + its label.
  function setState(ledEl, labelEl, state) {
    if (ledEl) ledEl.className = "vox-led " + (STATE_LED[state] || "is-standby");
    if (labelEl) labelEl.textContent = state;
  }

  // Processing bar fill + %, and optional label.
  function setProgress(fillEl, pctEl, labEl, pct, label) {
    pct = clamp(Math.round(pct || 0), 0, 100);
    if (fillEl) fillEl.style.width = pct + "%";
    if (pctEl) pctEl.textContent = pct + "%";
    if (labEl && label) labEl.textContent = label;
  }

  // Reverse-chron telemetry log (newest first), capped. Messages are escaped —
  // decks log raw filenames, which must never reach innerHTML as markup.
  function makeLog(container, cap) {
    cap = cap || 6; var lines = [];
    return function (level, msg) {
      var cls = level === "warn" || level === "error" ? "a" : (level === "done" ? "g" : "t");
      lines.unshift('<div><span class="' + cls + '">▸</span> ' + escHtml(String(msg)) + "</div>");
      if (lines.length > cap) lines.pop();
      if (container) container.innerHTML = lines.join("");
    };
  }

  // A VU lane (uses .vox-meter from the kit). Level is 0..1; db is a string.
  function setMeter(fillEl, dbEl, level, db) {
    if (fillEl) fillEl.style.width = clamp(level * 100, 0, 100) + "%";
    if (dbEl != null && db != null) dbEl.textContent = db;
  }

  /* ---- canvas instruments -------------------------------------------------- */

  function fitCanvas(c) {
    var r = c.getBoundingClientRect(), d = Math.min(root.devicePixelRatio || 1, 2);
    c.width = Math.max(1, r.width * d); c.height = Math.max(1, r.height * d);
    c.getContext("2d").setTransform(d, 0, 0, d, 0, 0);
    return r;
  }

  // Radial compute gauge. val 0..100; goes amber only near the limit (>88).
  function drawGauge(canvas, val) {
    var x = canvas.getContext("2d"), w = canvas.width, h = canvas.height, cx = w / 2, cy = h / 2, r = w / 2 - 10;
    x.setTransform(1, 0, 0, 1, 0, 0);
    x.clearRect(0, 0, w, h); x.lineWidth = 9; x.lineCap = "round";
    x.strokeStyle = "#16242f"; x.beginPath(); x.arc(cx, cy, r, .75 * Math.PI, 2.25 * Math.PI); x.stroke();
    var end = .75 * Math.PI + 1.5 * Math.PI * (clamp(val, 0, 100) / 100), hot = val > 88;
    var grad = x.createLinearGradient(0, 0, w, h);
    if (hot) { grad.addColorStop(0, "#3fe0ff"); grad.addColorStop(1, "#ffb547"); }
    else { grad.addColorStop(0, "#1a9fc4"); grad.addColorStop(1, "#3fe0ff"); }
    x.strokeStyle = grad; x.shadowColor = hot ? "#ffb547" : "#3fe0ff"; x.shadowBlur = 10;
    x.beginPath(); x.arc(cx, cy, r, .75 * Math.PI, end); x.stroke(); x.shadowBlur = 0;
  }

  // Populate a mini bar meter (command bar) with N bars.
  function miniMeter(container, n) {
    n = n || 16; container.innerHTML = "";
    for (var i = 0; i < n; i++) container.appendChild(document.createElement("i"));
    return container.querySelectorAll("i");
  }

  /* ---- native -> contract adapters ---------------------------------------- */

  // VoxAnalysis viewer: /api/pitch-jobs/{id} -> { id, status, stage, result, error }
  // Keys mirror engine/pitch_track.py _write_stage() calls — keep the two in sync
  // (stale keys here made the chain snap back to "Upload / 0%" mid-run).
  var VIEWER_STAGE_KEY = {
    queued: "upload",
    separating_vocals: "isolate", preparing_audio: "isolate",
    tracking_pitch: "pitch",
    running_v2_analysis: "analysis",
    finding_original: "match", analysing_original: "match",
    aligning_comparison: "align",
    building_report: "report",
    // legacy aliases (older engine builds)
    converting: "upload", isolate: "isolate", pitch: "pitch", analysing: "analysis",
    analysis: "analysis", v2_analysis: "analysis", reference: "match",
    comparing: "align", align: "align", report: "report"
  };
  function adaptViewer(raw, mode) {
    mode = mode || "analyze";
    var steps = CHAINS[mode], state, idx = 0, queued = raw.status === "queued";
    // queued reads as WORKING: STANDBY made the deck re-show the upload intake
    // as if nothing had been submitted while a job waited for the worker.
    if (queued) { state = "WORKING"; idx = 0; }
    else if (raw.status === "processing") {
      state = "WORKING";
      var key = VIEWER_STAGE_KEY[raw.stage] || raw.stage;
      idx = steps.findIndex(function (s) { return s[2] === key; });
      if (idx < 0) idx = 1;  // unknown stage: show the first working step, never "Upload"
    } else if (raw.status === "complete") { state = "COMPLETE"; idx = steps.length; }
    else if (raw.status === "failed") { state = "ALERT"; idx = 0; }
    else { state = "STANDBY"; }
    var total = steps.length;
    var progress = state === "COMPLETE" ? 100 : Math.round((idx / total) * 100);
    var at = Math.min(idx, total - 1);
    return {
      mode: mode, state: state, job: { id: raw.id, name: (raw.name || "") },
      stage: { index: at, total: total, key: steps[at][2], label: queued ? "Queued" : steps[at][1] },
      progress: progress, error: raw.error || null
    };
  }

  // Fused orchestrator: /api/fused-jobs/{id} -> { status, stage, progress, ... }
  // (see design/fused-orchestrator.md). One job spanning both engines.
  function adaptFused(raw) {
    var steps = CHAINS.fused, state, idx = 0, queued = raw.status === "queued";
    if (queued) { state = "WORKING"; idx = 0; } // queued = submitted, keep the working UI
    else if (raw.status === "processing") {
      state = "WORKING";
      idx = steps.findIndex(function (s) { return s[2] === raw.stage; });
      if (idx < 0) idx = 1;  // unknown stage: show the first working step, never "Upload"
    } else if (raw.status === "complete") { state = "COMPLETE"; idx = steps.length; }
    else if (raw.status === "failed") { state = "ALERT"; idx = 0; }
    else { state = "STANDBY"; }
    var total = steps.length, at = Math.min(idx, total - 1);
    return {
      mode: "fused", state: state, job: { id: raw.id, name: (raw.name || "") },
      stage: { index: at, total: total, key: steps[at][2], label: queued ? "Queued" : steps[at][1] },
      progress: state === "COMPLETE" ? 100 : (raw.progress != null ? raw.progress : Math.round((idx / total) * 100)),
      analysis: raw.analysis || null, polish: raw.polish || null,
      isolation: raw.isolation || null, error: raw.error || null
    };
  }

  // VoxPolish: /api/render -> { status, ... } (+ upload job progress elsewhere)
  var POLISH_STATE = { idle: "STANDBY", running: "WORKING", done: "COMPLETE", error: "ALERT" };
  function adaptPolish(raw) {
    var steps = CHAINS.polish, state = POLISH_STATE[raw.status] || "STANDBY";
    var idx = state === "COMPLETE" ? steps.length : (state === "WORKING" ? (raw.step_index || 6) : 0);
    var total = steps.length, progress = state === "COMPLETE" ? 100 : Math.round((idx / total) * 100);
    return {
      mode: "polish", state: state, job: { id: raw.session || "", name: raw.name || "" },
      stage: { index: Math.min(idx, total - 1), total: total, key: steps[Math.min(idx, total - 1)][2], label: steps[Math.min(idx, total - 1)][1] },
      progress: progress, error: raw.error ? { message: raw.error } : null
    };
  }

  /* ---- poller -------------------------------------------------------------- */
  // Polls a status URL, normalises with `adapt`, calls onEvent(event). Backs off
  // by state: fast while WORKING, slow at STANDBY/COMPLETE. Returns stop().
  function poll(opts) {
    var stopped = false, timer = null;
    function loop() {
      if (stopped) return;
      fetch(opts.url, { headers: { "cache-control": "no-cache" } })
        .then(function (r) {
          if (r.status === 404) {
            // The job is gone (expired, or lost in a server restart). Silence here
            // used to map to STANDBY and spin forever — surface it and stop.
            if (!stopped) {
              var steps = CHAINS[opts.mode] || [["01", "", ""]];
              opts.onEvent({
                mode: opts.mode || "", state: "ALERT", job: { id: "", name: "" },
                stage: { index: 0, total: steps.length, key: steps[0][2], label: steps[0][1] },
                progress: 0,
                error: { code: "job_not_found", reason: "this job is no longer on the server — start a new take" }
              });
            }
            return null; // terminal
          }
          if (!r.ok) { // transient server trouble — keep watching
            if (!stopped) timer = setTimeout(loop, 2000);
            return null;
          }
          return r.json();
        })
        .then(function (raw) {
          if (stopped || raw == null) return;
          var ev = opts.adapt(raw, opts.mode);
          opts.onEvent(ev);
          var terminal = ev.state === "COMPLETE" || ev.state === "ALERT";
          if (terminal && opts.stopOnTerminal !== false) return;
          timer = setTimeout(loop, ev.state === "WORKING" ? 500 : 2000);
        })
        .catch(function () { if (!stopped) timer = setTimeout(loop, 2000); });
    }
    loop();
    return function stop() { stopped = true; if (timer) clearTimeout(timer); };
  }

  root.VOX = {
    CHAINS: CHAINS, STATE_LED: STATE_LED, REDUCE: REDUCE,
    el: el, clamp: clamp, escHtml: escHtml, alertText: alertText,
    renderChain: renderChain, setState: setState, setProgress: setProgress,
    makeLog: makeLog, setMeter: setMeter,
    fitCanvas: fitCanvas, drawGauge: drawGauge, miniMeter: miniMeter,
    adaptViewer: adaptViewer, adaptPolish: adaptPolish, adaptFused: adaptFused, poll: poll
  };
})(window);
