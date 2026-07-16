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
          '<div class="vrec-reviewhead"><span class="vrec-check-ic">&#10003;</span>Take captured <b class="vrec-dur vox-tnum"></b></div>' +
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
        if (blobUrl) URL.revokeObjectURL(blobUrl); blobUrl = URL.createObjectURL(blob);
        el._blob = blob; $(".vrec-player").src = blobUrl; $(".vrec-dur").textContent = fmt((performance.now() - startAt) / 1000);
        stage("review");
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

    function commit() {
      var blob = el._blob; if (!blob) return;
      var file = new File([blob], "recording." + mime[1], { type: blob.type });
      teardown();
      opts.onAnalyze && opts.onAnalyze(file);
    }
    function teardown() { cancelAnimationFrame(raf); if (stream) stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; try { ac && ac.close(); } catch (e) {} ac = null; }

    $(".vrec-enable").addEventListener("click", openMic);
    $(".vrec-device").addEventListener("change", function () { deviceId = this.value; openMic(); });
    $(".vrec-start").addEventListener("click", function () { if (ac && ac.state === "suspended") ac.resume(); startFlow(); });
    $(".vrec-stop").addEventListener("click", stopRecording);
    $(".vrec-again").addEventListener("click", function () { openMic(); });
    $(".vrec-analyze").addEventListener("click", commit);

    return { teardown: teardown, el: el };
  }

  root.VOXRecord = { mount: mount, supported: function () { return !!(root.MediaRecorder && navigator.mediaDevices && navigator.mediaDevices.getUserMedia); } };
})(window);
