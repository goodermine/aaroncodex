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

let state = {
  revision: 0,
  doc: null,
  peaks: null,
  duration: 0,
  selected: null, // {kind, index}
  source: "cleaned",
};

// ------------------------------------------------------------------ api

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

async function loadAll() {
  const d = await api("/api/document");
  state.revision = d.revision;
  state.doc = d.document;
  state.duration = state.doc.duration;
  state.peaks = await api(`/api/peaks/${state.source}`);
  updateCounts();
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
    while (true) {
      await new Promise((r) => setTimeout(r, 400));
      const s = await api("/api/render");
      if (s.status === "done") break;
      if (s.status === "error") throw new Error(s.error);
    }
    setStatus("Rendered.");
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

// ------------------------------------------------------------------ drawing

function resize() {
  const r = canvas.getBoundingClientRect();
  canvas.width = r.width * devicePixelRatio;
  canvas.height = r.height * devicePixelRatio;
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  draw();
}

function xOf(t) {
  return (t / state.duration) * canvas.clientWidth;
}

function draw() {
  if (!state.peaks || !state.doc) return;
  const W = canvas.clientWidth, H = canvas.clientHeight, mid = H / 2;
  ctx.clearRect(0, 0, W, H);

  // Region overlays behind the waveform.
  for (const kind of KINDS) {
    ctx.fillStyle = COLORS[kind] + "33";
    for (const r of state.doc[kind]) {
      ctx.fillRect(xOf(r.start), 0, Math.max(2, xOf(r.end) - xOf(r.start)), H);
    }
  }
  // Selected region highlight.
  if (state.selected) {
    const r = state.doc[state.selected.kind][state.selected.index];
    if (r) {
      ctx.strokeStyle = COLORS[state.selected.kind];
      ctx.lineWidth = 2;
      ctx.strokeRect(xOf(r.start), 1, xOf(r.end) - xOf(r.start), H - 2);
    }
  }

  // Waveform from peaks.
  const { min, max } = state.peaks;
  const n = min.length;
  ctx.fillStyle = "#aeb6c2";
  const scale = mid * 0.92;
  for (let i = 0; i < n; i++) {
    const x = (i / n) * W;
    const w = Math.max(1, W / n);
    const y1 = mid - max[i] * scale;
    const y2 = mid - min[i] * scale;
    ctx.fillRect(x, y1, w, Math.max(1, y2 - y1));
  }

  // Gain curve (dynamics) over the top.
  const curve = state.doc.gain_curve;
  if (curve && curve.length) {
    ctx.strokeStyle = "#e8d44d";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < curve.length; i++) {
      const x = xOf(curve[i][0]);
      const y = mid - (curve[i][1] / 12) * mid * 0.9;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.stroke();
  }

  // Playhead.
  if (!audio.paused || audio.currentTime > 0) {
    ctx.strokeStyle = "#ffffff";
    ctx.beginPath();
    const x = xOf(audio.currentTime);
    ctx.moveTo(x, 0);
    ctx.lineTo(x, H);
    ctx.stroke();
  }
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

function updateCounts() {
  for (const kind of KINDS) $(`count-${kind}`).textContent = state.doc[kind].length;
  $("count-gain").textContent = state.doc.gain_curve.length ? "on" : "off";
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
  updateCounts();
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

// ------------------------------------------------------------------ events

canvas.addEventListener("click", (ev) => {
  const t = (ev.offsetX / canvas.clientWidth) * state.duration;
  const hit = regionAt(t);
  if (hit) {
    state.selected = hit;
  } else {
    state.selected = null;
    audio.currentTime = t;
  }
  showInspector();
  draw();
});

document.addEventListener("keydown", (ev) => {
  if (ev.key === "Delete" || ev.key === "Backspace") {
    if (document.activeElement.tagName !== "INPUT") deleteSelected();
  }
  if (ev.key === " " && document.activeElement.tagName !== "BUTTON") {
    ev.preventDefault();
    audio.paused ? audio.play() : audio.pause();
  }
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

setInterval(() => {
  $("time").textContent = fmtTime(audio.currentTime || 0);
  if (!audio.paused) draw();
}, 100);

window.addEventListener("resize", resize);

loadAll().then(() => {
  resize();
  reloadAudio();
  setStatus("Ready.");
}).catch((e) => setStatus(e.message, true));
