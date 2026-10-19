/* Singnexa beta — page logic. One file, picked by <body data-page>. */
(function () {
  "use strict";
  var $ = function (s) { return document.querySelector(s); };
  var esc = function (v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var STAGES = {
    queued: "Waiting in the queue",
    separating_vocals: "Separating your voice from the music — this is the slow part (a few minutes)",
    cutting_talk: "Finding and cutting out any talking",
    preparing_audio: "Preparing the audio",
    tracking_pitch: "Tracking your pitch",
    running_v2_analysis: "Measuring and scoring",
    complete: "Done"
  };

  function api(method, url, body) {
    var opts = { method: method, credentials: "same-origin", headers: { "X-Singnexa": "1" } };
    if (body !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
    return fetch(url, opts).then(function (r) {
      var ct = r.headers.get("content-type") || "";
      var parse = ct.indexOf("json") >= 0 ? r.json() : r.text();
      return parse.then(function (data) {
        if (r.status === 401 && document.body.dataset.page !== "login") { location.href = "/login"; throw new Error("signed out"); }
        if (!r.ok) { var e = new Error(message(data, r.status)); e.status = r.status; e.data = data; throw e; }
        return data;
      });
    });
  }
  function message(data, status) {
    var d = data && data.detail;
    if (d && d.message) return d.message;
    if (d && d.code === "media_too_large") return "That file is over the " + (d.max_mb || "") + " MB limit.";
    if (d && d.code === "password_change_required") { location.href = "/account"; return "Choose a new password first."; }
    if (d && d.code) return "Something went wrong (" + d.code + ").";
    return "Something went wrong (" + status + ").";
  }
  function say(el, text, kind) { el.className = "sx-msg " + (kind || "info"); el.textContent = text || ""; }
  // The small Markdown subset the coaching notes use: ### headings, - bullets,
  // **bold**, paragraphs. Everything is escaped first, so no HTML gets through.
  function md(text) {
    var out = [], list = false, para = [];
    function inline(s) { return esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>"); }
    function flush() { if (para.length) { out.push("<p>" + inline(para.join(" ")) + "</p>"); para = []; } }
    function close() { if (list) { out.push("</ul>"); list = false; } }
    String(text || "").split(/\r?\n/).forEach(function (line) {
      var t = line.trim(), h = /^#{1,4}\s+(.*)$/.exec(t), li = /^[-*]\s+(.*)$/.exec(t);
      if (!t) { flush(); close(); return; }
      if (h) { flush(); close(); out.push("<h3>" + inline(h[1]) + "</h3>"); return; }
      if (li) { flush(); if (!list) { out.push("<ul>"); list = true; } out.push("<li>" + inline(li[1]) + "</li>"); return; }
      close(); para.push(t);
    });
    flush(); close();
    return out.join("");
  }
  function when(ts) {
    try { return new Date(ts * 1000).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }); }
    catch (e) { return ""; }
  }
  function fmt(v) { return v == null ? "—" : Number(v).toFixed(1); }

  function chrome(user) {
    var out = $("#signOut");
    if (out) out.addEventListener("click", function () { api("POST", "/api/logout").then(function () { location.href = "/login"; }); });
    if (user && user.is_admin && $("#navAdmin")) $("#navAdmin").hidden = false;
  }

  function pill(job) {
    if (job.status === "complete" && job.lead) return '<span class="sx-pill good">' + fmt(job.lead.value) + "/10</span>";
    if (job.status === "complete") return '<span class="sx-pill">results</span>';
    if (job.status === "failed") return '<span class="sx-pill weak">failed</span>';
    return '<span class="sx-pill">analysing…</span>';
  }
  function jobItem(job) {
    var title = job.song || job.original_filename || "Recording";
    var sub = [job.singer, job.artist, job.capture, when(job.created_at)].filter(Boolean).join(" · ");
    return '<li><a href="/results/' + esc(job.id) + '"><span><span class="t">' + esc(title) + '</span><br><span class="s">' +
      esc(sub) + "</span></span>" + pill(job) + "</a></li>";
  }

  // ---- pages ------------------------------------------------------------
  var pages = {};

  pages.login = function () {
    $("#loginForm").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var msg = $("#msg"); say(msg, "");
      api("POST", "/api/login", { username: $("#username").value, password: $("#password").value })
        .then(function (d) { location.href = d.user.must_change_password ? "/account" : "/"; })
        .catch(function (e) { say(msg, e.message, "err"); });
    });
  };

  pages.home = function (me) {
    var lim = me.limits || {};
    if (lim.formats) $("#limits").textContent = "WAV or FLAC up to " + lim.max_upload_mb + " MB and " + lim.max_minutes + " minutes (" + lim.formats.join(", ") + ")";
    function load() {
      api("GET", "/api/jobs").then(function (d) {
        $("#jobs").innerHTML = d.jobs.length ? d.jobs.map(jobItem).join("") :
          '<li class="sx-muted" style="padding:12px 2px">No results yet. Upload your first recording above.</li>';
        if (d.jobs.some(function (j) { return j.status === "queued" || j.status === "processing"; })) setTimeout(load, 8000);
      });
    }
    load();
    $("#uploadForm").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var f = $("#file").files[0], msg = $("#msg"), btn = $("#uploadBtn"), bar = $("#bar"), fill = bar.querySelector("i");
      if (!f) return;
      if (lim.max_upload_mb && f.size > lim.max_upload_mb * 1048576) { say(msg, "That file is over the " + lim.max_upload_mb + " MB limit.", "err"); return; }
      var fd = new FormData($("#uploadForm"));
      var xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/jobs");
      xhr.setRequestHeader("X-Singnexa", "1");
      xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) { fill.style.width = Math.round(e.loaded / e.total * 100) + "%"; say(msg, "Uploading… " + Math.round(e.loaded / e.total * 100) + "%"); }
      };
      xhr.onload = function () {
        var data = {}; try { data = JSON.parse(xhr.responseText); } catch (e) {}
        if (xhr.status === 202) { say(msg, "Uploaded. Opening your results page…", "ok"); location.href = data.url; return; }
        btn.disabled = false; bar.hidden = true; say(msg, message(data, xhr.status), "err");
      };
      xhr.onerror = function () { btn.disabled = false; bar.hidden = true; say(msg, "The upload was interrupted. Check your connection and try again.", "err"); };
      btn.disabled = true; bar.hidden = false; fill.style.width = "0";
      xhr.send(fd);
    });
  };

  pages.results = function (me) {
    var id = location.pathname.split("/").pop();
    $("#txtLink").href = "/api/jobs/" + encodeURIComponent(id) + "/full-results";
    $("#txtLink").setAttribute("download", "singnexa-results.txt");
    $("#deleteBtn").addEventListener("click", function () {
      if (!confirm("Delete this result for good? This can't be undone.")) return;
      api("DELETE", "/api/jobs/" + encodeURIComponent(id)).then(function () { location.href = "/"; })
        .catch(function (e) { say($("#msg"), e.message, "err"); });
    });
    function summary(job) {
      var title = esc(job.song || job.original_filename || "Recording");
      var meta = [job.singer, job.artist, job.capture, when(job.created_at)].filter(Boolean).map(esc).join(" · ");
      var head = "<h1>" + title + '</h1><p class="sx-muted">' + meta + "</p>";
      if (job.status === "failed") return head + '<div class="sx-msg err">' + esc(job.error.message) + "</div>";
      if (job.status !== "complete") {
        return head + '<p><b>' + esc(STAGES[job.stage] || "Analysing") + "…</b></p>" +
          '<p class="sx-muted">You can leave this page and come back — the result will be under My results.</p>' +
          '<div class="sx-progress"><i style="width:' + ({ queued: 5, separating_vocals: 30, cutting_talk: 50, preparing_audio: 60, tracking_pitch: 70, running_v2_analysis: 85 }[job.stage] || 15) + '%"></i></div>';
      }
      var s = (job.report && job.report.score) || {}, lead = job.lead;
      var score = lead
        ? '<div class="sx-lead"><span class="big">' + fmt(lead.value) + '</span><span class="of">/ 10</span><span class="lbl">' + esc(lead.label) +
          (lead.other_value != null ? " · " + esc(lead.other_label) + " " + fmt(lead.other_value) : "") + "</span></div>"
        : '<div class="sx-msg info">The headline score is withheld' + (s.withheld_reason ? ": " + esc(s.withheld_reason) : "") + ". Everything else below is measured as normal.</div>";
      return head + score +
        "<p><b>" + esc(s.confidence || "") + (s.confidence ? " confidence" : "") + "</b>" + (s.confidence ? " · " : "") +
        "Calibrated to 50 professional reference vocals — <b>10 = a typical pro</b>. A 7 is a good amateur result, not a failure.</p>" +
        '<p class="sx-muted">We show the higher of your two scores first. Capture-fair leaves out the parts that measure the microphone and room rather than your voice.</p>';
    }
    function prep(job) {
      // What was cut before scoring (talk_cut), so the singer can check it by ear.
      var p = job.report && job.report.audio_prep;
      if (!p || !p.removed || !p.removed.length) return "";
      return '<p class="sx-muted">Before scoring we cut out talking at ' + p.removed.map(function (r) {
        return esc(r.from + "–" + r.to) + (r.text ? " (“" + esc(r.text) + "”)" : "");
      }).join(", ") + "." + (p.starts_at ? " Times below start at your first sung note, " + esc(p.starts_at) +
        " into your recording." : "") + "</p>";
    }
    var writeupTries = 0;
    function showWriteup(w) {
      var box = $("#writeup");
      if (!w || w.status === "disabled" || w.status === "failed") { box.hidden = true; return false; }
      box.hidden = false;
      if (w.status === "ready") { box.innerHTML = "<h2>Your coaching notes</h2>" + md(w.markdown || ""); return false; }
      box.innerHTML = '<h2>Your coaching notes</h2><p class="sx-muted">Being written now. They appear here in a minute or so; the full results are below.</p>';
      return true;
    }
    function pollWriteup() {
      if (++writeupTries > 40) { $("#writeup").hidden = true; return; }
      api("GET", "/api/jobs/" + encodeURIComponent(id)).then(function (job) {
        if (showWriteup(job.writeup)) setTimeout(pollWriteup, 6000);
      }).catch(function () {});
    }
    function load() {
      api("GET", "/api/jobs/" + encodeURIComponent(id)).then(function (job) {
        $("#summary").innerHTML = summary(job) + (job.status === "complete" ? prep(job) : "");
        document.title = (job.song || "Results") + " · Singnexa";
        if (job.status === "queued" || job.status === "processing") { setTimeout(load, 5000); return; }
        $("#tools").hidden = false;
        if (job.status === "complete" && showWriteup(job.writeup)) setTimeout(pollWriteup, 6000);
        if (job.status === "complete" && window.VOXReport) {
          VOXReport.render($("#report"), { report: job.report, result: job.result,
            reportUrl: "/api/jobs/" + encodeURIComponent(id) + "/technical.md" });
        }
      }).catch(function (e) {
        $("#summary").innerHTML = '<div class="sx-msg err">' + esc(e.status === 404 ? "We couldn't find that result." : e.message) + "</div>";
      });
    }
    load();
  };

  pages.account = function (me) {
    if (me.user.must_change_password) { $("#firstNote").hidden = false; var nav = $("#nav"); if (nav) nav.querySelectorAll("a").forEach(function (a) { a.hidden = true; }); }
    $("#pwUser").value = me.user.username;
    $("#pwForm").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var msg = $("#msg");
      if ($("#new").value !== $("#new2").value) { say(msg, "The two new passwords don't match.", "err"); return; }
      api("POST", "/api/password", { current: $("#current").value, "new": $("#new").value })
        .then(function () { say(msg, "Saved.", "ok"); if (me.user.must_change_password) setTimeout(function () { location.href = "/"; }, 600); })
        .catch(function (e) { say(msg, e.message, "err"); });
    });
  };

  pages.admin = function () {
    function load() {
      api("GET", "/api/admin/overview").then(function (d) {
        $("#users").innerHTML = "<tr><th>Name</th><th>Username</th><th>Results</th><th></th></tr>" + d.users.map(function (u) {
          var flags = [u.is_admin ? "admin" : "", u.disabled ? "disabled" : "", u.must_change_password ? "not signed in yet" : ""].filter(Boolean).join(", ");
          return "<tr><td>" + esc(u.display_name) + (flags ? '<br><span class="sx-muted">' + esc(flags) + "</span>" : "") + "</td><td>" + esc(u.username) +
            "</td><td>" + esc(u.jobs) + '</td><td><button class="sx-btn ghost" data-act="reset" data-id="' + u.id + '">New password</button> ' +
            '<button class="sx-btn ghost" data-act="' + (u.disabled ? "enable" : "disable") + '" data-id="' + u.id + '">' + (u.disabled ? "Enable" : "Disable") + "</button></td></tr>";
        }).join("");
        var pf = d.preflight || {};
        $("#preflight").innerHTML = pf.ok === true ? "✅ Passed — scores are being published." :
          "⚠️ Not passing — headline scores are withheld. " + esc(pf.summary || "");
        $("#alljobs").innerHTML = d.jobs.map(jobItem).join("") || '<li class="sx-muted" style="padding:12px 2px">No results yet.</li>';
      }).catch(function (e) { say($("#msg"), e.message, "err"); });
    }
    function showTemp(user, pw) {
      $("#temp").hidden = false;
      $("#tempPw").textContent = "Username: " + user + "  ·  One-time password: " + pw;
    }
    $("#users").addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-act]"); if (!b) return;
      api("POST", "/api/admin/users/" + b.dataset.id + "/" + b.dataset.act).then(function (d) {
        if (d.temporary_password) showTemp(d.username, d.temporary_password);
        load();
      }).catch(function (e) { say($("#msg"), e.message, "err"); });
    });
    $("#newUser").addEventListener("submit", function (ev) {
      ev.preventDefault();
      api("POST", "/api/admin/users", { display_name: $("#nuName").value, username: $("#nuUser").value, is_admin: $("#nuAdmin").checked })
        .then(function (d) { say($("#msg"), "Created " + d.user.username + ".", "ok"); showTemp(d.user.username, d.temporary_password); $("#newUser").reset(); load(); })
        .catch(function (e) { say($("#msg"), e.message, "err"); });
    });
    $("#rerunPreflight").addEventListener("click", function () {
      $("#preflight").textContent = "Running…";
      api("POST", "/api/admin/preflight").then(load);
    });
    load();
  };

  var page = document.body.dataset.page;
  if (page === "login") { pages.login(); return; }
  api("GET", "/api/me").then(function (me) {
    chrome(me.user);
    if (me.user.must_change_password && page !== "account") { location.href = "/account"; return; }
    (pages[page] || function () {})(me);
  }).catch(function () {});
})();
