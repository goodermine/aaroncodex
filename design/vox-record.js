/* ============================================================================
   VOX Suite — in-browser recorder  (shared, vendored by sync.sh)
   Record → review → analyze. Captures a clean, unprocessed take (echo-cancel /
   noise-suppression / auto-gain OFF so pitch & harmonics aren't altered),
   Opus in the best container the browser supports. Mic device picker, live
   input level + clip warning, optional 3-2-1 count-in, and a review player
   before committing.

   VOXRecord.mount(container, { onAnalyze(file), onStage(stage) }) -> controller
     onAnalyze(File) : fires when the user commits a take (ready to upload)
   ============================================================================ */
(function (root) {
  "use strict";

  var MIME = [["audio/webm;codecs=opus", "webm"], ["audio/ogg;codecs=opus", "ogg"],
              ["audio/mp4", "mp4"], ["audio/webm", "webm"]];
  function pickMime() {
    if (!root.MediaRecorder) return null;
    for (var i = 0; i < MIME.length; i++) if (MediaRecorder.isTypeSupported(MIME[i][0])) return MIME[i];
    return ["", "webm"];
  }
  var MAX_SECONDS = 15 * 60;

  function h(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
  function fmt(s) { return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(Math.floor(s % 60)).padStart(2, "0"); }

  function mount(container, opts) {
    opts = opts || {};
    var mime = pickMime();
    var el = h(
      '<div class="vrec">' +
        '<div class="vrec-stage" data-stage="idle">' +
          '<button class="vrec-btn vrec-enable" type="button">Enable microphone</button>' +
          '<p class="vrec-note">We capture a clean, unprocessed take — no echo-cancel or auto-gain — so the analysis is faithful.</p>' +
        '</div>' +
        '<div class="vrec-stage" data-stage="monitor" hidden>' +
          '<label class="vrec-field"><span>Microphone</span><select class="vrec-device"></select></label>' +
          '<div class="vrec-meter"><i class="vrec-meter__fill"></i><b class="vrec-meter__peak"></b></div>' +
          '<div class="vrec-levelmsg">Checking input…</div>' +
          '<div class="vrec-row"><label class="vrec-check"><input type="checkbox" class="vrec-countin" checked> 3-2-1 count-in</label>' +
            '<button class="vrec-btn vrec-btn--rec vrec-start" type="button"><span class="vrec-dot"></span>Record</button></div>' +
        '</div>' +
        '<div class="vrec-stage" data-stage="live" hidden>' +
          '<canvas class="vrec-wave"></canvas>' +
          '<div class="vrec-count" hidden></div>' +
          '<div class="vrec-row"><span class="vrec-rec"><span class="vrec-dot is-live"></span><span class="vrec-recstate">REC</span> <b class="vrec-timer vox-tnum">00:00</b></span>' +
            '<button class="vrec-btn vrec-btn--stop vrec-stop" type="button"><span class="vrec-sq"></span>Stop</button></div>' +
        '</div>' +
        '<div class="vrec-stage" data-stage="review" hidden>' +
          '<div class="vrec-reviewhead"><span class="vrec-check-ic">&#10003;</span><span class="vrec-reviewlbl">Take captured</span> <b class="vrec-dur vox-tnum"></b></div>' +
          '<div class="vrec-trim">' +
            '<canvas class="vrec-trimwave"></canvas>' +
            '<div class="vrec-shade vrec-shade--in"></div><div class="vrec-shade vrec-shade--out"></div>' +
            '<div class="vrec-grip vrec-grip--in" role="slider" aria-label="Trim start" tabindex="0"></div>' +
            '<div class="vrec-grip vrec-grip--out" role="slider" aria-label="Trim end" tabindex="0"></div>' +
            '<div class="vrec-cursor" hidden></div>' +
            '<div class="vrec-trimwait">Reading audio…</div>' +
          '</div>' +
          '<div class="vrec-trimbar">' +
            '<span class="vrec-tl">Start <b class="vrec-in vox-tnum">00:00</b></span>' +
            '<span class="vrec-prevs">' +
              '<button class="vrec-btn vrec-btn--tiny vrec-p-in" type="button" title="Hear the first seconds after the start point">&#9654; start</button>' +
              '<button class="vrec-btn vrec-btn--tiny vrec-p-all" type="button" title="Play the whole trimmed take">&#9654; trimmed</button>' +
              '<button class="vrec-btn vrec-btn--tiny vrec-p-out" type="button" title="Hear the last seconds before the end point">&#9654; end</button>' +
              '<button class="vrec-btn vrec-btn--tiny vrec-p-stop" type="button" hidden>&#10073;&#10073; stop</button>' +
            '</span>' +
            '<span class="vrec-tl">End <b class="vrec-out vox-tnum">00:00</b></span>' +
          '</div>' +
          '<div class="vrec-trimnote">Drag the handles to cut dead air, chatter or applause — then listen to check. ' +
            'Trimmed length <b class="vrec-len vox-tnum">—</b> <button class="vrec-linkbtn vrec-reset" type="button">reset</button></div>' +
          '<audio class="vrec-player" controls></audio>' +
          '<div class="vrec-row"><button class="vrec-btn vrec-again" type="button">&#8635; Re-record</button>' +
            '<button class="vrec-btn vrec-btn--go vrec-analyze" type="button">Analyze this take</button></div>' +
        '</div>' +
        '<div class="vrec-err" hidden></div>' +
      "</div>"
    );
    container.appendChild(el);
    var $ = function (s) { return el.querySelector(s); };
    function stage(name) { el.querySelectorAll(".vrec-stage").forEach(function (s) { s.hidden = s.dataset.stage !== name; }); if (opts.onStage) opts.onStage(name); }
    function fail(msg) { var e = $(".vrec-err"); e.textContent = msg; e.hidden = false; }

    if (!root.isSecureContext) { $(".vrec-enable").disabled = true; fail("Recording needs a secure (https) connection. Open the deck over https, or use Upload."); }
    if (!mime) { $(".vrec-enable").disabled = true; fail("This browser can't record audio — please use Upload."); }

    var stream = null, ac = null, analyser = null, tdat = null, recorder = null, chunks = [], startAt = 0, raf = 0, blobUrl = null, deviceId = null;

    function openMic() {
      $(".vrec-err").hidden = true;
      var constraints = { audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 } };
      if (deviceId) constraints.audio.deviceId = { exact: deviceId };
      navigator.mediaDevices.getUserMedia(constraints).then(function (s) {
        if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
        stream = s;
        if (!ac) { ac = new (root.AudioContext || root.webkitAudioContext)(); analyser = ac.createAnalyser(); analyser.fftSize = 1024; tdat = new Uint8Array(analyser.fftSize); }
        try { srcNode && srcNode.disconnect(); } catch (e) {}
        srcNode = ac.createMediaStreamSource(stream); srcNode.connect(analyser);
        return navigator.mediaDevices.enumerateDevices();
      }).then(function (devs) {
        var sel = $(".vrec-device"); sel.innerHTML = "";
        devs.filter(function (d) { return d.kind === "audioinput"; }).forEach(function (d, i) {
          var o = document.createElement("option"); o.value = d.deviceId; o.textContent = d.label || ("Microphone " + (i + 1)); sel.appendChild(o);
        });
        if (deviceId) sel.value = deviceId;
        stage("monitor"); monitor();
      }).catch(function (err) {
        stage("idle");
        fail(err && err.name === "NotAllowedError" ? "Microphone access was blocked. Allow it in your browser, or use Upload."
          : err && err.name === "NotFoundError" ? "No microphone was found. Plug one in, or use Upload."
          : "Could not open the microphone (" + (err && err.name || "error") + "). Try Upload.");
      });
    }
    var srcNode = null;

    function levels() { // {rms, peak}
      analyser.getByteTimeDomainData(tdat); var sum = 0, peak = 0;
      for (var i = 0; i < tdat.length; i++) { var v = (tdat[i] - 128) / 128; sum += v * v; if (Math.abs(v) > peak) peak = Math.abs(v); }
      return { rms: Math.sqrt(sum / tdat.length), peak: peak };
    }
    function monitor() {
      cancelAnimationFrame(raf);
      (function loop() {
        if (el.querySelector('[data-stage="monitor"]').hidden) return;
        var l = levels(), pct = Math.min(100, l.rms * 240);
        $(".vrec-meter__fill").style.width = pct + "%";
        $(".vrec-meter__fill").style.background = l.peak > 0.98 ? "var(--vox-red)" : l.peak > 0.85 ? "var(--vox-amber)" : "linear-gradient(90deg,var(--vox-cyan-deep),var(--vox-cyan))";
        $(".vrec-levelmsg").textContent = l.peak > 0.98 ? "Too hot — back off the mic or lower input gain." : l.rms < 0.006 ? "Very quiet — move closer or raise input gain." : "Input level looks good.";
        raf = requestAnimationFrame(loop);
      })();
    }

    function beginRecording() {
      chunks = []; try { recorder = new MediaRecorder(stream, mime[0] ? { mimeType: mime[0], audioBitsPerSecond: 192000 } : undefined); }
      catch (e) { fail("Recording failed to start — please use Upload."); stage("monitor"); return; }
      recorder.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
      recorder.onstop = function () {
        var blob = new Blob(chunks, { type: mime[0] || "audio/webm" });
        el._name = "recording." + mime[1];
        $(".vrec-dur").textContent = fmt((performance.now() - startAt) / 1000);
        showTrim(blob, "Take captured");
      };
      recorder.start(); startAt = performance.now(); stage("live"); liveLoop();
    }
    function startFlow() {
      if ($(".vrec-countin").checked) countIn(3, beginRecording); else beginRecording();
    }
    function countIn(n, done) {
      stage("live"); var c = $(".vrec-count"); c.hidden = false; $(".vrec-wave").style.opacity = ".25";
      (function tick() {
        if (n <= 0) { c.hidden = true; $(".vrec-wave").style.opacity = "1"; done(); return; }
        c.textContent = n; beep(n === 1 ? 880 : 520); n--; setTimeout(tick, 800);
      })();
    }
    function beep(f) { try { var o = ac.createOscillator(), g = ac.createGain(); o.frequency.value = f; o.connect(g); g.connect(ac.destination); g.gain.value = 0.0001; g.gain.exponentialRampToValueAtTime(0.15, ac.currentTime + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + 0.18); o.start(); o.stop(ac.currentTime + 0.2); } catch (e) {} }

    function liveLoop() {
      var wave = $(".vrec-wave"), wx = wave.getContext("2d");
      cancelAnimationFrame(raf);
      (function loop() {
        if (el.querySelector('[data-stage="live"]').hidden) return;
        var secs = (performance.now() - startAt) / 1000; $(".vrec-timer").textContent = fmt(secs);
        if (secs >= MAX_SECONDS) { stopRecording(); return; }
        var r = wave.getBoundingClientRect(), d = Math.min(root.devicePixelRatio || 1, 2);
        if (wave.width !== r.width * d) { wave.width = r.width * d; wave.height = r.height * d; wx.setTransform(d, 0, 0, d, 0, 0); }
        wx.clearRect(0, 0, r.width, r.height); analyser.getByteTimeDomainData(tdat);
        // No per-frame shadowBlur: it's costly on mobile and thrashes compositing,
        // which is what made the Stop button vanish. A crisp 1.6px stroke reads fine.
        wx.strokeStyle = "#3fe0ff"; wx.lineWidth = 1.6; wx.beginPath();
        for (var i = 0; i < tdat.length; i++) { var x = i / (tdat.length - 1) * r.width, y = r.height / 2 + ((tdat[i] - 128) / 128) * r.height * 0.42; i ? wx.lineTo(x, y) : wx.moveTo(x, y); }
        wx.stroke();
        raf = requestAnimationFrame(loop);
      })();
    }
    function stopRecording() { if (recorder && recorder.state !== "inactive") recorder.stop(); }

    /* ---------------------------------------------------------------- trim ---
       Dead air, chatter and applause at the ends skew the analysis (and waste
       separation time), so a take is trimmed before it is submitted. The take is
       decoded once into an AudioBuffer: that drives the waveform, the audible
       preview of each edit point, and the final slice.

       Trimming is deliberately manual-first. Auto-detecting the start by silence
       works on a quiet home take but guesses badly on a live venue capture,
       where the "silence" before the first line is actually crowd and backing
       music — exactly the case where getting it wrong costs the most. So we
       suggest a start only when the take really does begin quiet, and always let
       the ear be the judge.                                                    */
    var audioBuf = null, peaks = null, trimIn = 0, trimOut = 0, previewSrc = null, previewRaf = 0;
    var QUIET = 0.02;   // rms below this counts as "no signal yet"

    function decodeCtx() { return ac || new (root.AudioContext || root.webkitAudioContext)(); }

    function showTrim(blob, label) {
      el._blob = blob;
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      blobUrl = URL.createObjectURL(blob);
      $(".vrec-player").src = blobUrl;
      if (label) $(".vrec-reviewlbl").textContent = label;
      audioBuf = null; peaks = null;
      $(".vrec-trimwait").hidden = false;
      setTrimEnabled(false);
      stage("review");
      blob.arrayBuffer().then(function (ab) { return decodeCtx().decodeAudioData(ab); })
        .then(function (buf) {
          audioBuf = buf; peaks = buildPeaks(buf, 1400);
          trimIn = suggestStart(buf); trimOut = buf.duration;
          $(".vrec-trimwait").hidden = true; setTrimEnabled(true);
          $(".vrec-dur").textContent = fmt(buf.duration);
          drawTrim(); syncTrimLabels();
        })
        .catch(function () {
          // Undecodable in this browser — fall back to submitting the take whole.
          $(".vrec-trimwait").textContent = "Trimming isn't available for this file — it will be analysed in full.";
          audioBuf = null;
        });
    }
    function setTrimEnabled(on) {
      [".vrec-p-in", ".vrec-p-all", ".vrec-p-out", ".vrec-reset"].forEach(function (s) {
        var b = $(s); if (b) b.disabled = !on;
      });
      el.querySelectorAll(".vrec-grip").forEach(function (g) { g.style.display = on ? "" : "none"; });
    }
    function buildPeaks(buf, cols) {
      var data = buf.getChannelData(0), step = data.length / cols;
      var mn = new Float32Array(cols), mx = new Float32Array(cols), rms = new Float32Array(cols);
      for (var c = 0; c < cols; c++) {
        var s0 = Math.floor(c * step), s1 = Math.min(data.length, Math.floor((c + 1) * step));
        var lo = 0, hi = 0, sum = 0;
        for (var i = s0; i < s1; i++) { var v = data[i]; if (v < lo) lo = v; if (v > hi) hi = v; sum += v * v; }
        mn[c] = lo; mx[c] = hi; rms[c] = Math.sqrt(sum / Math.max(1, s1 - s0));
      }
      return { cols: cols, mn: mn, mx: mx, rms: rms };
    }
    /** Suggest a start only for takes that genuinely begin quiet. Returns 0 when
        the take is loud from the first moment (a live capture), so we never drop
        the singer's first word on a bad guess. */
    function suggestStart(buf) {
      if (!peaks) return 0;
      if (peaks.rms[0] > QUIET) return 0;                 // loud from the off — live
      for (var c = 0; c < peaks.cols; c++) {
        if (peaks.rms[c] > QUIET) {
          var t = c / peaks.cols * buf.duration - 0.25;   // 250ms of air before the entry
          return Math.max(0, Math.min(t, buf.duration));
        }
      }
      return 0;
    }
    function trimGeom() {
      var wrap = $(".vrec-trim"), w = wrap.getBoundingClientRect().width;
      var dur = audioBuf ? audioBuf.duration : 1;
      return { w: w, dur: dur, x: function (t) { return t / dur * w; }, t: function (x) { return Math.max(0, Math.min(dur, x / w * dur)); } };
    }
    function drawTrim() {
      var cv = $(".vrec-trimwave"), wrap = $(".vrec-trim");
      var r = wrap.getBoundingClientRect(), d = Math.min(root.devicePixelRatio || 1, 2);
      if (!r.width) return;
      cv.width = Math.round(r.width * d); cv.height = Math.round(r.height * d);
      var cx = cv.getContext("2d"); cx.setTransform(d, 0, 0, d, 0, 0);
      cx.clearRect(0, 0, r.width, r.height);
      if (!peaks) return;
      var mid = r.height / 2;
      for (var px = 0; px < r.width; px++) {
        var c = Math.floor(px / r.width * peaks.cols); if (c >= peaks.cols) break;
        var t = px / r.width * (audioBuf ? audioBuf.duration : 1);
        var kept = t >= trimIn && t <= trimOut;
        cx.fillStyle = kept ? "#3fe0ff" : "rgba(127,147,164,.35)";
        var y1 = mid - peaks.mx[c] * mid * 0.92, y2 = mid - peaks.mn[c] * mid * 0.92;
        cx.fillRect(px, y1, 1, Math.max(1, y2 - y1));
      }
      var g = trimGeom();
      $(".vrec-shade--in").style.width = g.x(trimIn) + "px";
      $(".vrec-shade--out").style.left = g.x(trimOut) + "px";
      $(".vrec-shade--out").style.width = Math.max(0, g.w - g.x(trimOut)) + "px";
      $(".vrec-grip--in").style.left = g.x(trimIn) + "px";
      $(".vrec-grip--out").style.left = g.x(trimOut) + "px";
    }
    function syncTrimLabels() {
      $(".vrec-in").textContent = fmt(trimIn);
      $(".vrec-out").textContent = fmt(trimOut);
      $(".vrec-len").textContent = fmt(Math.max(0, trimOut - trimIn));
    }
    function dragGrip(which, ev) {
      var g = trimGeom(), wrap = $(".vrec-trim"), left = wrap.getBoundingClientRect().left;
      function move(e) {
        var t = g.t((e.clientX != null ? e.clientX : e.touches[0].clientX) - left);
        if (which === "in") trimIn = Math.min(t, trimOut - 0.5); else trimOut = Math.max(t, trimIn + 0.5);
        trimIn = Math.max(0, trimIn); trimOut = Math.min(g.dur, trimOut);
        drawTrim(); syncTrimLabels();
      }
      function up() { root.removeEventListener("pointermove", move); root.removeEventListener("pointerup", up); }
      root.addEventListener("pointermove", move); root.addEventListener("pointerup", up);
      move(ev);
    }
    function stopPreview() {
      try { previewSrc && previewSrc.stop(); } catch (e) {}
      previewSrc = null; cancelAnimationFrame(previewRaf);
      $(".vrec-cursor").hidden = true; $(".vrec-p-stop").hidden = true;
    }
    function preview(from, secs) {
      if (!audioBuf) return;
      stopPreview();
      var ctx = decodeCtx();
      if (ctx.state === "suspended") ctx.resume();
      var dur = Math.max(0.05, Math.min(secs, trimOut - from));
      previewSrc = ctx.createBufferSource(); previewSrc.buffer = audioBuf;
      previewSrc.connect(ctx.destination);
      previewSrc.onended = stopPreview;
      previewSrc.start(0, from, dur);
      $(".vrec-p-stop").hidden = false;
      var t0 = ctx.currentTime, cur = $(".vrec-cursor"), g = trimGeom();
      cur.hidden = false;
      (function tick() {
        if (!previewSrc) return;
        var at = from + (ctx.currentTime - t0);
        cur.style.left = g.x(Math.min(at, trimOut)) + "px";
        previewRaf = requestAnimationFrame(tick);
      })();
    }
    /** Slice [trimIn, trimOut] to a 16-bit PCM WAV. WAV because the engine
        converts to WAV anyway — re-encoding to a lossy format here would throw
        away exactly the detail the voice-quality metrics measure. */
    function sliceToWav(buf, from, to) {
      var sr = buf.sampleRate, chans = Math.min(buf.numberOfChannels, 2);
      var s0 = Math.floor(from * sr), s1 = Math.min(buf.length, Math.floor(to * sr));
      var n = Math.max(0, s1 - s0), bytes = 44 + n * chans * 2;
      var out = new DataView(new ArrayBuffer(bytes)), p = 0;
      function str(s) { for (var i = 0; i < s.length; i++) out.setUint8(p++, s.charCodeAt(i)); }
      function u32(v) { out.setUint32(p, v, true); p += 4; }
      function u16(v) { out.setUint16(p, v, true); p += 2; }
      str("RIFF"); u32(bytes - 8); str("WAVE");
      str("fmt "); u32(16); u16(1); u16(chans); u32(sr); u32(sr * chans * 2); u16(chans * 2); u16(16);
      str("data"); u32(n * chans * 2);
      var chData = [];
      for (var c = 0; c < chans; c++) chData.push(buf.getChannelData(c));
      for (var i2 = 0; i2 < n; i2++) {
        for (var c2 = 0; c2 < chans; c2++) {
          var v = Math.max(-1, Math.min(1, chData[c2][s0 + i2] || 0));
          out.setInt16(p, v < 0 ? v * 0x8000 : v * 0x7fff, true); p += 2;
        }
      }
      return new Blob([out.buffer], { type: "audio/wav" });
    }

    function commit() {
      var blob = el._blob; if (!blob) return;
      var file;
      var trimmed = audioBuf && (trimIn > 0.01 || trimOut < audioBuf.duration - 0.01);
      if (trimmed) {
        file = new File([sliceToWav(audioBuf, trimIn, trimOut)], "take-trimmed.wav", { type: "audio/wav" });
      } else {
        file = new File([blob], el._name || ("recording." + mime[1]), { type: blob.type });
      }
      stopPreview(); teardown();
      opts.onAnalyze && opts.onAnalyze(file);
    }
    function teardown() { cancelAnimationFrame(raf); if (stream) stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; try { ac && ac.close(); } catch (e) {} ac = null; }

    $(".vrec-enable").addEventListener("click", openMic);
    $(".vrec-device").addEventListener("change", function () { deviceId = this.value; openMic(); });
    $(".vrec-start").addEventListener("click", function () { if (ac && ac.state === "suspended") ac.resume(); startFlow(); });
    $(".vrec-stop").addEventListener("click", stopRecording);
    $(".vrec-again").addEventListener("click", function () { stopPreview(); openMic(); });
    $(".vrec-analyze").addEventListener("click", commit);

    // ---- trim controls
    $(".vrec-grip--in").addEventListener("pointerdown", function (e) { e.preventDefault(); dragGrip("in", e); });
    $(".vrec-grip--out").addEventListener("pointerdown", function (e) { e.preventDefault(); dragGrip("out", e); });
    $(".vrec-p-in").addEventListener("click", function () { preview(trimIn, 4); });
    $(".vrec-p-out").addEventListener("click", function () { preview(Math.max(trimIn, trimOut - 4), 4); });
    $(".vrec-p-all").addEventListener("click", function () { preview(trimIn, trimOut - trimIn); });
    $(".vrec-p-stop").addEventListener("click", stopPreview);
    $(".vrec-reset").addEventListener("click", function () {
      if (!audioBuf) return; trimIn = 0; trimOut = audioBuf.duration; drawTrim(); syncTrimLabels();
    });
    // keyboard nudge for accessibility (and fine adjustment on desktop)
    el.querySelectorAll(".vrec-grip").forEach(function (g) {
      g.addEventListener("keydown", function (e) {
        if (!audioBuf) return;
        var step = e.shiftKey ? 1 : 0.1, isIn = g.classList.contains("vrec-grip--in");
        if (e.key === "ArrowLeft") { isIn ? (trimIn = Math.max(0, trimIn - step)) : (trimOut = Math.max(trimIn + 0.5, trimOut - step)); }
        else if (e.key === "ArrowRight") { isIn ? (trimIn = Math.min(trimOut - 0.5, trimIn + step)) : (trimOut = Math.min(audioBuf.duration, trimOut + step)); }
        else return;
        e.preventDefault(); drawTrim(); syncTrimLabels();
      });
    });
    root.addEventListener("resize", function () { if (!el.querySelector('[data-stage="review"]').hidden) drawTrim(); });

    return {
      teardown: function () { stopPreview(); teardown(); },
      el: el,
      /** Bring an already-recorded file (e.g. a Dolby On export of a live gig,
          which the browser cannot capture itself because iOS suspends recording
          when the screen locks) straight into the trim view. */
      loadFile: function (file) {
        el._name = (file && file.name) || "upload";
        showTrim(file, "Imported");
      },
    };
  }

  root.VOXRecord = { mount: mount, supported: function () { return !!(root.MediaRecorder && navigator.mediaDevices && navigator.mediaDevices.getUserMedia); } };
})(window);
