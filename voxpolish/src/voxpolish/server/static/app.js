/* VoxPolish editor.
 *
 * Trust rules (disaster 2): this file holds NO private audio state. The
 * server's Edit Document is the truth; every mutation is PUT back with the
 * revision number and the UI re-reads what the server accepted. */

"use strict";

const $ = (id) => document.getElementById(id);
const canvas = $("wave");
const ctx = canvas.getContext("2d");
const audio = $("audio");

const COLORS = { pauses: "#e06060", breaths: "#5fbf77", sibilants: "#5fa8e0" };
const KINDS = ["pauses", "breaths", "sibilants"];
const AMOUNTS = ["dynamics", "breath", "sibilance", "tune"];
const BYPASSES = { dynamics: "dynamics", gate: "gate", breath: "breath",
                   sibilance: "sibilance", tune: "tune" };

let state = {
  revision: 0,
  doc: null,
  peaks: null,
  duration: 0,
  selected: null,          // {kind, index}
  source: "cleaned",
  view: { t0: 0, span: 0 }, // visible window in seconds; span 0 = fit
  pauseFollowUntil: 0,      // suppress playhead-follow briefly after manual pan
  ready: false,
};

// ------------------------------------------------------------------ api

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (e) {}
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

async function loadAll() {
  const d = await api("/api/document");
  state.revision = d.revision;
  state.doc = d.document;
  state.duration = state.doc.duration;
  if (!state.view.span) state.view = { t0: 0, span: state.duration };
  clampView();
  state.peaks = await api(`/api/peaks/${state.source}`);
  syncControls();
  draw();
}

async function saveDoc() {
  const r = await api("/api/document", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ revision: state.revision, document: state.doc }),
  });
  state.revision = r.revision;
}

// ------------------------------------------------------------------ render

async function render() {
  const btn = $("render");
  btn.disabled = true;
  setStatus("Rendering…");
  try {
    await saveDoc();
    await api("/api/render", { method: "POST" });
    let finalState;
    while (true) {
      await new Promise((r) => setTimeout(r, 400));
      finalState = await api("/api/render");
      if (finalState.status === "done") break;
      if (finalState.status === "error") throw new Error(finalState.error);
    }
    const notes = finalState.notes || [];
    setStatus(notes.length ? `Rendered — ${notes.join("; ")}` : "Rendered.");
    await loadAll();
    reloadAudio();
  } catch (e) {
    setStatus(e.message, true);
    await loadAll(); // re-sync with the server's truth after any failure
  } finally {
    btn.disabled = false;
  }
}

function setStatus(text, isError) {
  const el = $("status");
  el.textContent = text;
  el.className = "status" + (isError ? " error" : "");
}

// ------------------------------------------------------------------ knobs

function syncControls() {
  const bypass = state.doc.bypass || {};
  const amounts = state.doc.amounts || {};
  for (const key of Object.keys(BYPASSES)) {
    $(`on-${key}`).checked = !bypass[key];
  }
  for (const key of AMOUNTS) {
    const pct = Math.round((amounts[key] ?? 1.0) * 100);
    $(`amt-${key}`).value = pct;
    $(`amtv-${key}`).textContent = `${pct}%`;
  }
  $("count-pauses").textContent = state.doc.pauses.length;
  $("count-breaths").textContent = state.doc.breaths.length;
  $("count-sibilants").textContent = state.doc.sibilants.length;

  // Tune row: only live when the session has a correction curve.
  const p = state.doc.pitch || {};
  const hasTuner = (p.curve || []).length > 0;
  $("module-tune").classList.toggle("disabled", !hasTuner);
  $("on-tune").disabled = !hasTuner;
  $("amt-tune").disabled = !hasTuner;
  if (hasTuner) {
    $("count-tune").textContent = `${(p.notes || []).length} notes`;
    $("tune-key").textContent = `${p.key} · mean off ${p.mean_abs_dev_cents} cents`;
  } else {
    $("count-tune").textContent = "–";
    $("tune-key").textContent =
      p.error ? "analysis failed" : "no pitch data (recreate the session)";
  }
}

function wireControls() {
  for (const key of Object.keys(BYPASSES)) {
    $(`on-${key}`).addEventListener("change", (ev) => {
      state.doc.bypass = state.doc.bypass || {};
      state.doc.bypass[key] = !ev.target.checked;
      setStatus("Changed — press Render to apply.");
      draw();
    });
  }
  for (const key of AMOUNTS) {
    $(`amt-${key}`).addEventListener("input", (ev) => {
      state.doc.amounts = state.doc.amounts || {};
      state.doc.amounts[key] = ev.target.value / 100;
      $(`amtv-${key}`).textContent = `${ev.target.value}%`;
      setStatus("Changed — press Render to apply.");
    });
  }
}

// ------------------------------------------------------------------ view

function clampView() {
  const v = state.view;
  v.span = Math.min(Math.max(v.span, 0.25), state.duration || 1);
  v.t0 = Math.min(Math.max(v.t0, 0), Math.max(0, state.duration - v.span));
}

function zoom(factor, centerT) {
  const v = state.view;
  const c = centerT ?? v.t0 + v.span / 2;
  const rel = (c - v.t0) / v.span;
  v.span *= factor;
  clampView();
  v.t0 = c - rel * v.span;
  clampView();
  markManualPan();
  draw();
}

function panBy(seconds) {
  state.view.t0 += seconds;
  clampView();
  markManualPan();
  draw();
}

function markManualPan() {
  state.pauseFollowUntil = Date.now() + 2500;
}

function xOf(t) {
  return ((t - state.view.t0) / state.view.span) * canvas.clientWidth;
}

function tOf(x) {
  return state.view.t0 + (x / canvas.clientWidth) * state.view.span;
}

// ------------------------------------------------------------------ drawing

function resize() {
  const r = canvas.getBoundingClientRect();
  canvas.width = r.width * devicePixelRatio;
  canvas.height = r.height * devicePixelRatio;
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  draw();
}

function draw() {
  if (!state.peaks || !state.doc) return;
  const W = canvas.clientWidth, H = canvas.clientHeight, mid = H / 2;
  ctx.clearRect(0, 0, W, H);
  const bypass = state.doc.bypass || {};

  const dimmed = { pauses: bypass.gate, breaths: bypass.breath, sibilants: bypass.sibilance };
  for (const kind of KINDS) {
    ctx.fillStyle = COLORS[kind] + (dimmed[kind] ? "14" : "33");
    for (const r of state.doc[kind]) {
      if (r.end < state.view.t0 || r.start > state.view.t0 + state.view.span) continue;
      ctx.fillRect(xOf(r.start), 0, Math.max(2, xOf(r.end) - xOf(r.start)), H);
    }
  }
  if (state.selected) {
    const r = state.doc[state.selected.kind][state.selected.index];
    if (r) {
      ctx.strokeStyle = COLORS[state.selected.kind];
      ctx.lineWidth = 2;
      ctx.strokeRect(xOf(r.start), 1, xOf(r.end) - xOf(r.start), H - 2);
    }
  }

  const { min, max } = state.peaks;
  const n = min.length;
  const bucketDur = state.duration / n;
  const i0 = Math.max(0, Math.floor(state.view.t0 / bucketDur));
  const i1 = Math.min(n, Math.ceil((state.view.t0 + state.view.span) / bucketDur));
  ctx.fillStyle = "#aeb6c2";
  const scale = mid * 0.92;
  for (let i = i0; i < i1; i++) {
    const x = xOf(i * bucketDur);
    const w = Math.max(1, W / (i1 - i0));
    const y1 = mid - max[i] * scale;
    const y2 = mid - min[i] * scale;
    ctx.fillRect(x, y1, w, Math.max(1, y2 - y1));
  }

  const curve = state.doc.gain_curve;
  if (curve && curve.length && !bypass.dynamics) {
    const amt = (state.doc.amounts || {}).dynamics ?? 1.0;
    ctx.strokeStyle = "#e8d44d";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    let started = false;
    for (const [t, g] of curve) {
      if (t < state.view.t0 - 1 || t > state.view.t0 + state.view.span + 1) continue;
      const x = xOf(t);
      const y = mid - ((g * amt) / 12) * mid * 0.9;
      started ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      started = true;
    }
    ctx.stroke();
  }

  ctx.strokeStyle = "#ffffff";
  ctx.beginPath();
  const px = xOf(audio.currentTime || 0);
  ctx.moveTo(px, 0);
  ctx.lineTo(px, H);
  ctx.stroke();

  drawScrollbar();
}

function drawScrollbar() {
  const bar = $("scrollbar"), thumb = $("scrollthumb");
  if (!state.duration) return;
  const frac = Math.min(1, state.view.span / state.duration);
  const start = state.view.t0 / state.duration;
  const w = bar.clientWidth;
  thumb.style.width = Math.max(20, frac * w) + "px";
  thumb.style.left = start * w + "px";
}

// ------------------------------------------------------------------ regions

function regionAt(t) {
  for (const kind of KINDS) {
    const list = state.doc[kind];
    for (let i = 0; i < list.length; i++) {
      if (t >= list[i].start && t <= list[i].end) return { kind, index: i };
    }
  }
  return null;
}

function showInspector() {
  const box = $("inspector");
  if (!state.selected) return box.classList.add("hidden");
  const r = state.doc[state.selected.kind][state.selected.index];
  $("inspector-text").textContent =
    `${r.label || state.selected.kind} ${r.start.toFixed(2)}–${r.end.toFixed(2)}s ` +
    `(${r.reduction_db} dB)`;
  box.classList.remove("hidden");
}

function deleteSelected() {
  if (!state.selected) return;
  state.doc[state.selected.kind].splice(state.selected.index, 1);
  state.selected = null;
  syncControls();
  showInspector();
  draw();
  setStatus("Region removed — press Render to apply.");
}

// ------------------------------------------------------------------ audio

function reloadAudio() {
  const t = audio.currentTime;
  const wasPlaying = !audio.paused;
  audio.src = `/api/audio/${state.source}?v=${state.revision}`;
  audio.currentTime = t;
  if (wasPlaying) audio.play();
}

function fmtTime(s) {
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}

// ------------------------------------------------------------------ pan/drag

let drag = null; // {startX, startT0, moved}

canvas.addEventListener("mousedown", (ev) => {
  drag = { startX: ev.offsetX, startT0: state.view.t0, moved: false };
});

window.addEventListener("mousemove", (ev) => {
  if (!drag) return;
  const rect = canvas.getBoundingClientRect();
  const dx = ev.clientX - rect.left - drag.startX;
  if (Math.abs(dx) > 4) drag.moved = true;
  if (drag.moved) {
    canvas.classList.add("panning");
    const dt = (dx / canvas.clientWidth) * state.view.span;
    state.view.t0 = drag.startT0 - dt;
    clampView();
    markManualPan();
    draw();
  }
});

window.addEventListener("mouseup", (ev) => {
  if (!drag) return;
  canvas.classList.remove("panning");
  if (!drag.moved) {
    // A real click: select a region or seek the playhead.
    const rect = canvas.getBoundingClientRect();
    const t = tOf(ev.clientX - rect.left);
    const hit = regionAt(t);
    if (hit) {
      state.selected = hit;
    } else {
      state.selected = null;
      audio.currentTime = Math.max(0, Math.min(state.duration, t));
    }
    showInspector();
    draw();
  }
  drag = null;
});

canvas.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  if (ev.ctrlKey || ev.metaKey) {
    zoom(ev.deltaY > 0 ? 1.25 : 0.8, tOf(ev.offsetX));
  } else {
    // Horizontal pan; trackpads send deltaX, wheels send deltaY.
    const delta = Math.abs(ev.deltaX) > Math.abs(ev.deltaY) ? ev.deltaX : ev.deltaY;
    panBy(delta * state.view.span * 0.0025);
  }
}, { passive: false });

// Scrollbar thumb + track panning.
let thumbDrag = null;
$("scrollthumb").addEventListener("mousedown", (ev) => {
  ev.stopPropagation();
  thumbDrag = { startX: ev.clientX, startT0: state.view.t0 };
});
window.addEventListener("mousemove", (ev) => {
  if (!thumbDrag) return;
  const w = $("scrollbar").clientWidth;
  const dt = ((ev.clientX - thumbDrag.startX) / w) * state.duration;
  state.view.t0 = thumbDrag.startT0 + dt;
  clampView();
  markManualPan();
  draw();
});
window.addEventListener("mouseup", () => (thumbDrag = null));
$("scrollbar").addEventListener("mousedown", (ev) => {
  if (ev.target.id === "scrollthumb") return;
  const w = $("scrollbar").clientWidth;
  const frac = ev.offsetX / w;
  state.view.t0 = frac * state.duration - state.view.span / 2;
  clampView();
  markManualPan();
  draw();
});

// ------------------------------------------------------------------ keys/buttons

document.addEventListener("keydown", (ev) => {
  if (!$("landing").classList.contains("hidden")) return;
  const tag = document.activeElement.tagName;
  if ((ev.key === "Delete" || ev.key === "Backspace") && tag !== "INPUT") deleteSelected();
  if (ev.key === " " && tag !== "BUTTON" && tag !== "INPUT") {
    ev.preventDefault();
    audio.paused ? audio.play() : audio.pause();
  }
});

$("zoom-in").addEventListener("click", () => zoom(0.5));
$("zoom-out").addEventListener("click", () => zoom(2.0));
$("zoom-fit").addEventListener("click", () => {
  state.view = { t0: 0, span: state.duration, ...{} };
  state.pauseFollowUntil = 0;
  draw();
});
$("delete-region").addEventListener("click", deleteSelected);
$("render").addEventListener("click", render);
$("play").addEventListener("click", () => (audio.paused ? audio.play() : audio.pause()));
audio.addEventListener("play", () => ($("play").textContent = "Pause"));
audio.addEventListener("pause", () => ($("play").textContent = "Play"));
$("source").addEventListener("change", async (ev) => {
  state.source = ev.target.value;
  state.peaks = await api(`/api/peaks/${state.source}`);
  reloadAudio();
  draw();
});
$("new-upload").addEventListener("click", showLanding);

setInterval(() => {
  $("time").textContent = fmtTime(audio.currentTime || 0);
  if (!audio.paused && state.ready) {
    const t = audio.currentTime;
    const v = state.view;
    // Follow the playhead only if the user hasn't panned recently.
    if (Date.now() > state.pauseFollowUntil &&
        (t < v.t0 || t > v.t0 + v.span * 0.95)) {
      v.t0 = t - v.span * 0.1;
      clampView();
    }
    draw();
  }
}, 100);

window.addEventListener("resize", resize);

// ------------------------------------------------------------------ landing / upload

function showLanding() {
  $("landing").classList.remove("hidden");
  $("close-landing").classList.toggle("hidden", !state.ready);
  $("landing-error").textContent = "";
  $("upload-progress").classList.add("hidden");
  $("start-upload").classList.remove("hidden");
}

function hideLanding() {
  $("landing").classList.add("hidden");
}

function wireLanding() {
  const fileInput = $("file");
  const drop = $("drop");
  const startBtn = $("start-upload");

  const setFile = (f) => {
    if (!f) return;
    fileInput._file = f;
    $("drop-label").textContent = f.name;
    drop.classList.add("has-file");
    startBtn.disabled = false;
  };

  fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
  ["dragenter", "dragover"].forEach((e) =>
    drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add("hover"); }));
  ["dragleave", "drop"].forEach((e) =>
    drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.remove("hover"); }));
  drop.addEventListener("drop", (ev) => setFile(ev.dataTransfer.files[0]));

  $("close-landing").addEventListener("click", hideLanding);
  startBtn.addEventListener("click", () => startUpload(fileInput._file));
}

async function startUpload(file) {
  if (!file) return;
  const tune = document.querySelector('input[name="tune"]:checked').value === "tune";
  const form = new FormData();
  form.append("file", file);
  form.append("tune", tune ? "true" : "false");

  $("start-upload").classList.add("hidden");
  $("close-landing").classList.add("hidden");
  $("landing-error").textContent = "";
  $("upload-progress").classList.remove("hidden");
  setUploadStage("uploading", 0.15);

  let job;
  try {
    job = await api("/api/uploads", { method: "POST", body: form });
  } catch (e) {
    return uploadFailed(e.message);
  }

  const STAGES = { decoding: 0.4, cleaning: 0.6, analyzing: 0.75, rendering: 0.9, done: 1 };
  while (true) {
    await new Promise((r) => setTimeout(r, 500));
    let s;
    try { s = await api(`/api/uploads/${job.id}`); }
    catch (e) { return uploadFailed(e.message); }
    if (s.status === "error") return uploadFailed(s.error || "processing failed");
    setUploadStage(s.stage, STAGES[s.stage] ?? 0.3);
    if (s.status === "done") {
      hideLanding();
      await openEditor();
      return;
    }
  }
}

function setUploadStage(stage, frac) {
  $("upload-stage").textContent = `${stage}…`;
  $("upload-bar").style.width = `${Math.round(frac * 100)}%`;
}

function uploadFailed(msg) {
  $("upload-progress").classList.add("hidden");
  $("start-upload").classList.remove("hidden");
  $("close-landing").classList.toggle("hidden", !state.ready);
  $("landing-error").textContent = msg;
}

// ------------------------------------------------------------------ startup

async function openEditor() {
  state.view = { t0: 0, span: 0, ...{} };
  state.selected = null;
  await loadAll();
  resize();
  reloadAudio();
  state.ready = true;
  setStatus("Ready.");
}

async function init() {
  wireControls();
  wireLanding();
  try {
    await api("/api/session");    // 409 if no current session
    await openEditor();
  } catch (e) {
    if (e.status === 409) {
      showLanding();
    } else {
      setStatus(e.message, true);
    }
  }
}

init();
