/* ============================================================================
   VOX Suite — analysis results renderer  (shared, vendored by sync.sh)
   Ports the classic viewer's full report panel — executive summary, component
   scores, calibrated measurements, timestamped trouble spots, original
   comparison, evidence, practice plan and the full technical report — into a
   single self-contained call so the command deck shows the SAME results, not a
   thinner summary. Decoupled from any page globals.

   VOXReport.render(container, { report, result, reportUrl, onSeek })
     report    : result.v2_analysis (the built report payload)
     result    : the job result (duration, quality, reference, ...)
     reportUrl : URL of the full Markdown technical report (lazy-loaded)
     onSeek(t) : called when a trouble-spot marker is tapped (seconds)
   ============================================================================ */
(function (root) {
  "use strict";

  var esc = function (v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var shown = function (v, suffix) {
    suffix = suffix || "";
    return v === null || v === undefined || v === "" ? "Not available" : esc(v) + suffix;
  };
  function scoreState(value) {
    var ok = value !== null && value !== undefined && value !== "" && isFinite(Number(value));
    if (!ok) return { available: false, value: null, width: null, text: "Not available" };
    var n = Number(value);
    return { available: true, value: n, width: Math.max(0, Math.min(100, n * 10)), text: esc(value) };
  }
  function scoreMeter(value, title, className, fillClass) {
    title = title || "Measured component";
    var st = scoreState(value),
      attrs = st.available ? 'aria-valuenow="' + st.value + '" aria-valuetext="' + st.value + ' out of 10"' : 'aria-valuetext="Not available"',
      classes = "meter" + (className ? " " + esc(className) : "") + (st.available ? "" : " unavailable"),
      fillAttr = fillClass ? ' class="' + esc(fillClass) + '"' : "";
    return '<div class="' + classes + '" role="meter" aria-valuemin="0" aria-valuemax="10" ' + attrs +
      ' title="' + esc(st.available ? title : "Component score not available") + '">' +
      (st.available ? "<i" + fillAttr + ' style="width:' + st.width + '%"></i>' : "") + "</div>";
  }
  function metric(label, value, suffix, help) {
    return '<div class="metric"><small>' + esc(label) + "</small><strong>" + shown(value, suffix || "") + "</strong>" +
      (help ? "<small>" + esc(help) + "</small>" : "") + "</div>";
  }
  function list(title, items, badge) {
    badge = badge || "measured";
    var safe = Array.isArray(items) ? items : [];
    return '<div class="report-band"><h3><span class="evidence-badge ' + badge + '">' + esc(badge) + "</span> " + esc(title) + "</h3>" +
      (safe.length ? '<ul class="report-list">' + safe.map(function (i) { return "<li>" + esc(i) + "</li>"; }).join("") + "</ul>"
        : '<p class="quality">Not available for this recording.</p>') + "</div>";
  }
  function rack(title, summary, body, open, className) {
    // Phones read the executive summary first and open racks on demand —
    // starting them expanded is what made the report feel like a metric wall.
    if (open && typeof matchMedia === "function" && matchMedia("(max-width:760px)").matches) open = false;
    return '<details class="rack ' + (className || "") + '" ' + (open ? "open" : "") +
      '><summary><div><div class="kicker">Analysis rack</div><strong>' + esc(title) + "</strong></div>" +
      '<span class="rack-summary">' + esc(summary) + '</span></summary><div class="rack-body">' + body + "</div></details>";
  }
  function contextHtml(context) {
    if (!context) return "";
    return '<div class="context-note"><h3>Recording context</h3><p><b>Reported:</b> ' + shown(context.reported) +
      "</p><p><b>Measurement context:</b> " + esc((context.measurement_effects || []).join(" ") || "Not available") +
      "</p><p><b>Performance context:</b> " + esc((context.performance_effects || []).join(" ") || "Not available") +
      '</p><p class="quality">' + shown(context.caution) + "</p></div>";
  }
  function inlineMarkdown(v) {
    return esc(v).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  }
  function markdownReport(source) {
    var lines = source.replace(/\r/g, "").split("\n"), out = [], i = 0, listOpen = false;
    var closeList = function () { if (listOpen) { out.push("</ul>"); listOpen = false; } };
    while (i < lines.length) {
      var line = lines[i];
      if (line.startsWith("|") && i + 1 < lines.length && /^\|?[\s:|-]+\|/.test(lines[i + 1])) {
        closeList(); var rows = [];
        while (i < lines.length && lines[i].trim().startsWith("|")) {
          rows.push(lines[i].trim().replace(/^\||\|$/g, "").split("|").map(function (c) { return c.trim(); })); i++;
        }
        var header = rows[0], body = rows.slice(2);
        out.push('<div class="table-scroll"><table><thead><tr>' + header.map(function (c) { return "<th>" + inlineMarkdown(c) + "</th>"; }).join("") +
          "</tr></thead><tbody>" + body.map(function (r) { return "<tr>" + r.map(function (c) { return "<td>" + inlineMarkdown(c) + "</td>"; }).join("") + "</tr>"; }).join("") + "</tbody></table></div>");
        continue;
      }
      if (/^#{1,3} /.test(line)) { closeList(); var lvl = line.match(/^#+/)[0].length; out.push("<h" + lvl + ">" + inlineMarkdown(line.slice(lvl + 1)) + "</h" + lvl + ">"); }
      else if (/^---+$/.test(line.trim())) { closeList(); out.push("<hr>"); }
      else if (/^[-*] /.test(line)) { if (!listOpen) { out.push("<ul>"); listOpen = true; } out.push("<li>" + inlineMarkdown(line.slice(2)) + "</li>"); }
      else if (!line.trim()) { closeList(); }
      else { closeList(); out.push("<p>" + inlineMarkdown(line) + "</p>"); }
      i++;
    }
    closeList(); return out.join("");
  }
  function loadTechnical(url, host) {
    if (!host || host.dataset.loaded) return;
    host.dataset.loaded = "1";
    if (!url) { host.innerHTML = '<p class="quality">The full technical report is unavailable for this job.</p>'; return; }
    host.innerHTML = '<p class="technical-loading">Loading technical measurements…</p>';
    fetch(url).then(function (r) { if (!r.ok) throw new Error(); return r.text(); })
      .then(function (t) { host.innerHTML = markdownReport(t); })
      .catch(function () { host.innerHTML = '<p class="quality">The technical report could not be loaded.</p>'; });
  }

  function comparisonHtml(report, result) {
    var comparison = report.comparison, reference = result.reference, context = report.recording_context;
    if (reference && reference.status === "skipped") return "";
    if (!comparison || !reference || reference.status !== "ready")
      return rack("Original comparison", "Reference unavailable",
        '<p class="quality">A verified original was not available for this job, so no singer-versus-original claims are shown.</p>' + contextHtml(context));
    var p = reference.provenance || {}, shift = comparison.transposition_semitones,
      direction = shift === 0 ? "Same key" : shift < 0 ? Math.abs(shift) + " semitone" + (Math.abs(shift) === 1 ? "" : "s") + " lower" : shift + " semitone" + (shift === 1 ? "" : "s") + " higher",
      originalComponents = new Map(((reference.v2_analysis && reference.v2_analysis.score && reference.v2_analysis.score.components) || []).map(function (it) { return [it.key, it]; })),
      componentRows = ((report.score && report.score.components) || []).map(function (item) {
        var original = originalComponents.get(item.key); if (!original) return "";
        var ss = scoreState(item.score), os = scoreState(original.score);
        return '<div class="compare-row"><span>' + esc(item.label) + "</span>" + scoreMeter(item.score, item.label + " singer component", "", "singer-fill") +
          "<b>" + (ss.available ? ss.value.toFixed(1) : ss.text) + "</b>" + scoreMeter(original.score, item.label + " original component", "original-bar", "original-fill") +
          '<b class="original-score">' + (os.available ? os.value.toFixed(1) : os.text) + "</b></div>";
      }).join("");
    var body = '<section class="comparison"><p>' + esc(comparison.note || "Comparison complete.") + '</p><div class="comparison-grid">' +
      '<div class="comparison-cell"><small>Melody match</small><strong>' + shown(comparison.pct_frames_within_50_cents, "%") + "</strong></div>" +
      '<div class="comparison-cell"><small>Median difference</small><strong>' + shown(comparison.median_abs_pitch_diff_cents, " cents") + "</strong></div>" +
      '<div class="comparison-cell"><small>Key relationship</small><strong>' + esc(direction) + "</strong></div>" +
      '<div class="comparison-cell"><small>Timing spread</small><strong>' + shown(comparison.timing_spread_s, " s") + "</strong></div>" +
      '<div class="comparison-cell"><small>Singer capture-fair</small><strong>' + shown(comparison.singer_capture_fair, " / 10") + "</strong></div>" +
      '<div class="comparison-cell"><small>Original capture-fair</small><strong>' + shown(comparison.original_capture_fair, " / 10") + "</strong></div></div>" +
      (componentRows ? '<div class="compare-components"><h3>Calibrated component profile</h3><p class="quality">Singer in violet · original in orange</p>' + componentRows + "</div>" : "") +
      '<div class="provenance"><b>Verified original reference</b><p>' + esc(p.title || p.requested_song || "Original") + " · " + esc(p.uploader || p.requested_artist || "") + "</p>" +
      '<p class="quality">Source: ' + esc(p.webpage_url || "private reference library") + " · " + (p.cached ? "reused verified file" : "newly resolved file") + "</p></div>" + contextHtml(context) + "</section>";
    return rack("Original comparison", shown(comparison.pct_frames_within_50_cents, "%") + " melody match", body);
  }

  function practiceHtml(plan) {
    if (!plan) return "";
    var immediate = plan.immediate || {}, long = plan.long_term || {};
    var body = '<section class="practice"><p>Built from the main measured limiter in this recording.</p><div class="practice-grid">' +
      '<div class="practice-block"><h3>Immediate correction</h3><p class="dose">' + shown(immediate.duration) + '</p><ol class="steps">' +
      (immediate.steps || []).map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("") + '</ol><p class="success"><b>Ready for the next take when:</b><br>' + shown(immediate.success) + "</p></div>" +
      '<div class="practice-block long"><h3>Longer-term development</h3><p class="dose">' + shown(long.frequency) + "</p>" +
      (long.sessions || []).map(function (s) { return '<div class="practice-session"><b>' + esc(s.name) + "</b><span>" + esc(s.dose) + "</span><p>" + esc(s.instruction) + "</p></div>"; }).join("") +
      '<p class="success"><b>Measure progress:</b><br>' + shown(long.progress) + "</p></div></div></section>";
    return rack("Coaching and practice", "Targeted next actions", body);
  }

  // Plain-text digest of the ENTIRE analysis — every score, metric and caveat,
  // nothing summarised away. One tap copies it so the full result (not a
  // curated excerpt) is what gets pasted into chats and coaching write-ups.
  function buildDigest(report, result) {
    var s = report.score || {}, m = report.metrics || {}, L = [];
    function line(t) { L.push(t); }
    function flat(obj) {
      var parts = [];
      for (var k in obj) { var v = obj[k]; if (typeof v === "number" || typeof v === "string" || typeof v === "boolean") parts.push(k + ": " + v); }
      return parts.join(" · ");
    }
    line("VOX ANALYSIS — FULL RESULTS");
    if (report.headline) line(report.headline);
    line("");
    line("SCORES");
    line("Overall: " + (s.overall != null ? s.overall + "/10" : "—") + "  (" + (s.confidence || "—") + " confidence)");
    line("Capture-fair: " + (s.capture_fair != null ? s.capture_fair + "/10" : "—") + "  — same rubric minus mic/room-sensitive voice-quality metrics; quote this for live or rough captures");
    (s.components || []).forEach(function (c) {
      line("- " + (c.label || c.key || "?") + ": " + (c.score != null ? c.score : "—") + (c.basis ? "  [" + c.basis + "]" : ""));
    });
    if (result.robust_min_note || result.robust_max_note) { line(""); line("RANGE: " + (result.robust_min_note || "?") + " – " + (result.robust_max_note || "?")); }
    line("");
    line("METRICS");
    for (var group in m) { if (m[group] && typeof m[group] === "object") { var f = flat(m[group]); if (f) line(group + " — " + f); } }
    var trouble = report.trouble_spots || [];
    if (trouble.length) {
      line(""); line("TROUBLE SPOTS (" + trouble.length + ")");
      trouble.forEach(function (t) { line("- " + (t.time || "?") + "  " + (t.note || "?") + "  drift " + (t.drift_cents != null ? t.drift_cents + "c" : "?")); });
    }
    var focus = report.main_focus || {};
    if (focus.pillar || focus.title || focus.why) { line(""); line("PRIMARY FOCUS: " + (focus.pillar || focus.title || "—") + (focus.why ? " — " + focus.why : "")); }
    function block(title, arr) { if (arr && arr.length) { line(""); line(title); arr.forEach(function (i) { line("- " + i); }); } }
    block("WORKING WELL", report.what_is_working);
    block("MEASURED", report.measured);
    block("INFERRED (verify by ear)", report.inferred);
    block("UNVERIFIABLE FROM AUDIO", report.unverifiable);
    line("");
    line("Deterministic VOXAI rubric — identical audio gives identical scores; calibrated against 50 professional reference vocals.");
    return L.join("\n");
  }

  function render(container, opts) {
    opts = opts || {};
    var report = opts.report, result = opts.result || {}, reportUrl = opts.reportUrl, onSeek = opts.onSeek || function () {};
    container.classList.add("vox-report");
    if (!report) {
      container.innerHTML = '<div class="vox-rpt-warn">The detailed VOXAI report is unavailable for this recording.</div>';
      container.removeAttribute("hidden"); return;
    }
    var s = report.score || {}, m = report.metrics || {}, intonation = m.intonation || {}, voice = m.voice_quality || {},
      vibrato = m.vibrato || {}, dynamics = m.dynamics || {}, breath = m.breath || {}, range = m.range || {},
      resonance = m.resonance || {}, onsets = m.onsets || {}, harmonics = m.harmonics || {}, vowels = m.vowel_space || {},
      focus = report.main_focus || {};
    var components = (s.components || []).map(function (c) {
      var st = scoreState(c.score);
      return '<div class="component"><span>' + esc(c.label) + "</span>" + scoreMeter(c.score, c.basis || "Measured component") + "<b>" + st.text + "</b></div>";
    }).join("");
    var trouble = report.trouble_spots || [], duration = result.duration_seconds || 1;
    var timeline = trouble.length ? '<div class="timeline" aria-label="Timestamped trouble spots">' +
      trouble.map(function (t) {
        return '<button class="spot" style="left:' + Math.min(99, t.start_s / duration * 100) + '%" data-time="' + t.start_s +
          '" aria-label="Seek to ' + esc(t.time) + '"><span>' + esc(t.time) + " · " + esc(t.note || "note") + " · " + shown(t.drift_cents, "c drift") + "</span></button>";
      }).join("") + "</div><small>Tap a marker to seek to that moment.</small>"
      : '<p class="quality">No bounded timestamped trouble spots were reported for this take.</p>';
    var metrics = [
      metric("Pitch-centre deviation", intonation.median_deviation_cents, " cents", "Lower is more centred."),
      metric("Held-note drift", intonation.held_drift_cents, " cents", "Lower is steadier."),
      metric("Within ±25 cents", intonation.within_25_percent, "%", "Higher is more accurate."),
      metric("HNR", voice.hnr_db, " dB", "Harmonic signal clarity."),
      metric("CPPS", voice.cpps_db, " dB", "Phonation clarity measure."),
      metric("Strain flags", voice.strain_percent, "%", "Coaching heuristic only."),
      metric("Vibrato use", vibrato.use_percent, "%"), metric("Vibrato rate", vibrato.rate_hz, " Hz"),
      metric("Dynamic range", dynamics.effective_range_db, " dB"), metric("Breath-end sag", breath.sag_percent, "%"),
      metric("Comfortable core", range.comfortable_core), metric("Most-used note", range.most_used_note),
      metric("Clean onsets", onsets.clean_percent, "%", "Scoops and overshoots may be stylistic."),
      metric("Singer’s-formant ratio", resonance.singers_formant_ratio_db, " dB", "Projection heuristic."),
      metric("H1−H2", harmonics.h1_minus_h2_db, " dB", harmonics.read),
      metric("Vowels mapped", vowels.notes_mapped, " notes", "Approximate sung-vowel map.")
    ].join("");
    var capture = (result.quality && result.quality.classification) || "not available";
    var working = (report.what_is_working || []).slice(0, 3);
    var executive = '<div class="executive"><section class="executive-main"><div class="kicker">Executive analysis</div><h2>' + shown(report.headline) +
      '</h2><p class="overview">' + shown(report.overview) + '</p><div class="evidence-row">' +
      '<span class="evidence-badge measured">Measured</span><span class="evidence-badge inferred">Inferred</span>' +
      '<span class="evidence-badge coaching">Coaching</span><span class="evidence-badge unverifiable">Not verifiable</span></div>' +
      (working.length ? '<div class="report-band"><h3>Strongest signals</h3><ul class="report-list">' + working.map(function (i) { return "<li>" + esc(i) + "</li>"; }).join("") + "</ul></div>" : "") +
      '<div class="focus"><div class="kicker">Primary coaching focus</div><h3>' + shown(focus.pillar) + "</h3><p>" + shown(focus.why) + "</p><p><b>" + shown(focus.drill) +
      '</b></p><p class="cue">' + shown(focus.cue) + "</p><p>" + shown(focus.target) + "</p></div></section>" +
      '<aside class="score-panel"><div class="score-unit"><div class="score-value">' + shown(s.overall) + '</div><div class="score-label">Overall / 10</div></div>' +
      '<div class="score-unit"><div class="score-value">' + shown(s.capture_fair) + '</div><div class="score-label">Capture-fair / 10</div>' +
      '<div class="score-context" style="margin-top:6px">Same rubric minus the mic/room-sensitive voice-quality metrics — <b>quote this one for live or rough captures</b>.</div></div>' +
      '<div class="score-context"><b>' + shown(s.confidence) + " confidence</b> · Capture status: " + esc(capture) + ". Scores must be read with the visible capture warnings above.</div></aside></div>";
    var profile = rack("Technical profile", "Core component scores", components || '<p class="quality">Not available.</p>', true);
    var measurements = rack("Core measurements", "Pitch, voice, dynamics, range and calibrated diagnostics", '<div class="metric-grid">' + metrics + "</div>", true);
    var troubleRack = rack("Trouble spots", trouble.length + " timestamped event" + (trouble.length === 1 ? "" : "s"), timeline);
    var evidence = rack("Evidence and interpretation", "Measured vs inferred",
      list("Measured / directly observed", report.measured, "measured") +
      list("Inferred coaching interpretation", report.inferred, "inferred") +
      list("Unverifiable from audio alone", report.unverifiable, "unverifiable"));
    var technical = '<details class="rack technical-report" id="voxTechnicalRack"><summary><div><div class="kicker">Analysis rack</div><strong>Full technical report</strong></div>' +
      '<span class="rack-summary">Calibrated VOXAI analysis</span></summary><div class="rack-body technical-body" id="voxTechnicalReport"><p class="quality">Open this rack to load the full report.</p></div></details>';

    var actions = '<div class="report-actions"><button type="button" class="vox-rpt-copy">&#10697; Copy full results</button>' +
      '<span class="report-actions__hint">copies every score, metric and caveat as text — paste the whole thing, not a summary</span></div>';
    container.innerHTML = actions + executive + profile + measurements + troubleRack + comparisonHtml(report, result) + evidence + practiceHtml(report.practice_plan) + technical;
    container.removeAttribute("hidden");
    var copyBtn = container.querySelector(".vox-rpt-copy");
    if (copyBtn) copyBtn.addEventListener("click", function () {
      var digest = buildDigest(report, result);
      function done(ok) { copyBtn.textContent = ok ? "✓ Copied — paste it all" : "Copy failed — use Export instead"; setTimeout(function () { copyBtn.innerHTML = "&#10697; Copy full results"; }, 2600); }
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(digest).then(function () { done(true); }, function () { done(false); });
      else {
        var ta = document.createElement("textarea"); ta.value = digest; document.body.appendChild(ta); ta.select();
        try { done(document.execCommand("copy")); } catch (e) { done(false); }
        ta.remove();
      }
    });
    container.querySelectorAll(".spot").forEach(function (elm) { elm.onclick = function () { onSeek(Number(elm.dataset.time)); }; });
    var techRack = container.querySelector("#voxTechnicalRack");
    if (techRack) techRack.addEventListener("toggle", function (e) {
      if (e.currentTarget.open) loadTechnical(reportUrl, container.querySelector("#voxTechnicalReport"));
    }, { once: true });
  }

  root.VOXReport = { render: render, markdownReport: markdownReport };
})(window);
