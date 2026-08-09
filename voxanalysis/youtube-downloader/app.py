#!/usr/bin/env python3
"""VYT Downloader (VOX YouTube Downloader).

Small self-hosted web tool for grabbing original/reference songs from
YouTube so they can be compared against a singer's take in the VOXAI
pipeline. One page: search for an artist, song, or topic (or paste a
link), pick from the results, choose MP3 (for analysis) or MP4, and
download. Every download is also kept in the reference library folder so
candi_phase1.py / analyse_song.py can pick it up:

    openclaw-data/vox-coach/uploads/reference/

Run:

    pip install -r requirements.txt
    python3 app.py            # serves http://127.0.0.1:8765

Requires ffmpeg on PATH (already required by the VOXAI backend).

Agents should use youtube-downloader/fetch_reference.py instead of this
page - it wraps the same download logic (reference_dl.py) as a one-shot
CLI.

Product rule reminder: reference-track comparison requires copyright
care - use downloads for private comparison/analysis only and do not
retain reference media longer than needed.
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

try:
    import reference_dl as rd
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Dependencies missing. Run: pip install -r requirements.txt"
    ) from exc

app = FastAPI(title="VYT Downloader")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE_HTML


@app.get("/api/search")
def search(q: str = Query(...), limit: int = Query(8)) -> dict:
    try:
        return {"results": rd.search(q, limit=limit)}
    except rd.ReferenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/info")
def info(url: str = Query(...)) -> dict:
    try:
        return rd.fetch_info(url)
    except rd.ReferenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/download")
def download(
    url: str = Query(...),
    fmt: str = Query(..., pattern="^(mp3|mp4)$"),
    quality: str = Query(...),
) -> FileResponse:
    try:
        result = rd.download_reference(url, fmt=fmt, quality=quality)
    except rd.ReferenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    media_type = "audio/mpeg" if fmt == "mp3" else "video/mp4"
    final = result["path"]
    return FileResponse(final, media_type=media_type, filename=final.rsplit("/", 1)[-1])


@app.get("/api/library")
def library() -> dict:
    return rd.list_library()


PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VYT Downloader — VOX YouTube Downloader</title>
<style>
  :root {
    --bg: #0b0e1c;
    --panel: rgba(255,255,255,.045);
    --panel-border: rgba(255,255,255,.09);
    --text: #eef0ff;
    --muted: #9aa0c3;
    --a1: #8b5cf6;
    --a2: #3b82f6;
    --a3: #22d3ee;
    --good: #34d399;
    --bad: #f87171;
  }
  * { box-sizing: border-box; margin: 0; padding: 0;
      font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  html { color-scheme: dark; }
  body {
    background: var(--bg) fixed;
    background-image:
      radial-gradient(60rem 40rem at 85% -10%, rgba(139,92,246,.22), transparent 60%),
      radial-gradient(50rem 35rem at -10% 20%, rgba(59,130,246,.18), transparent 60%),
      radial-gradient(40rem 30rem at 50% 110%, rgba(34,211,238,.12), transparent 60%);
    color: var(--text);
    min-height: 100vh;
  }
  header {
    position: sticky; top: 0; z-index: 10;
    display: flex; align-items: center; gap: 14px;
    padding: 14px 22px;
    background: rgba(11,14,28,.75);
    backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--panel-border);
  }
  .logo {
    width: 40px; height: 40px; border-radius: 12px; flex: none;
    background: linear-gradient(135deg, var(--a1), var(--a2) 55%, var(--a3));
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 1.25rem; color: #fff;
    box-shadow: 0 4px 18px rgba(99,102,241,.45);
  }
  .brand { line-height: 1.15; }
  .brand .name { font-weight: 800; font-size: 1.18rem; letter-spacing: .06em; }
  .brand .tag { font-size: .68rem; letter-spacing: .28em; color: var(--muted); }
  main { max-width: 680px; margin: 0 auto; padding: 40px 18px 70px; }
  h1 {
    text-align: center; font-size: 2.3rem; line-height: 1.2; font-weight: 800;
    background: linear-gradient(90deg, #c4b5fd, #93c5fd 55%, #67e8f9);
    -webkit-background-clip: text; background-clip: text; color: transparent;
    margin-bottom: 12px;
  }
  .sub { text-align: center; color: var(--muted); margin: 0 auto 30px; max-width: 46ch; }
  .searchbox {
    display: flex; gap: 10px; padding: 10px;
    background: var(--panel); border: 1px solid var(--panel-border);
    border-radius: 18px; box-shadow: 0 10px 40px rgba(0,0,0,.35);
  }
  .searchbox:focus-within { border-color: rgba(139,92,246,.6); box-shadow: 0 0 0 4px rgba(139,92,246,.15), 0 10px 40px rgba(0,0,0,.35); }
  input#url {
    flex: 1; min-width: 0; padding: 13px 14px; font-size: 1.02rem;
    background: transparent; border: 0; outline: none; color: var(--text);
  }
  input#url::placeholder { color: #6b7194; }
  button#start {
    padding: 13px 26px; font-size: 1.02rem; font-weight: 700; color: #fff;
    background: linear-gradient(135deg, var(--a1), var(--a2));
    border: 0; border-radius: 12px; cursor: pointer; flex: none;
    transition: transform .12s, box-shadow .12s;
  }
  button#start:hover { transform: translateY(-1px); box-shadow: 0 6px 22px rgba(99,102,241,.5); }
  button#start:disabled { opacity: .55; cursor: wait; transform: none; box-shadow: none; }
  #error {
    display: none; margin-top: 16px; padding: 12px 16px; border-radius: 12px;
    background: rgba(248,113,113,.12); border: 1px solid rgba(248,113,113,.35); color: var(--bad);
  }
  .fade { animation: fadeUp .35s ease both; }
  @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
  #results { display: none; margin-top: 26px; }
  .rhead { color: var(--muted); font-size: .8rem; letter-spacing: .18em; margin: 0 4px 12px; }
  .result {
    display: flex; gap: 14px; align-items: center; padding: 10px;
    background: var(--panel); border: 1px solid var(--panel-border);
    border-radius: 16px; margin-bottom: 12px; cursor: pointer;
    transition: transform .12s, border-color .12s, background .12s;
  }
  .result:hover { transform: translateY(-2px); border-color: rgba(139,92,246,.55); background: rgba(139,92,246,.08); }
  .thumbwrap { position: relative; flex: none; }
  .thumbwrap img { width: 132px; height: 74px; object-fit: cover; border-radius: 10px; background: #171b33; display: block; }
  .dur {
    position: absolute; right: 5px; bottom: 5px; padding: 2px 7px;
    font-size: .7rem; font-weight: 700; border-radius: 6px;
    background: rgba(0,0,0,.75); color: #fff;
  }
  .result .rt { font-weight: 650; font-size: .97rem; line-height: 1.35; }
  .result .ru { color: var(--muted); font-size: .83rem; margin-top: 4px; }
  #back {
    display: none; margin: 24px 0 0; background: none; border: 0;
    color: #a5b4fc; font-size: .95rem; font-weight: 650; cursor: pointer;
  }
  #back:hover { color: #c7d2fe; }
  #video {
    display: none; margin-top: 20px; padding: 18px;
    background: var(--panel); border: 1px solid var(--panel-border);
    border-radius: 20px; text-align: center;
  }
  #video img { max-width: 100%; border-radius: 14px; }
  #video .t { font-weight: 700; font-size: 1.05rem; margin-top: 14px; line-height: 1.35; }
  #video .u { color: var(--muted); font-size: .9rem; margin-top: 4px; }
  .tabs { display: none; justify-content: center; margin: 26px 0 18px; }
  .seg {
    display: flex; padding: 5px; gap: 4px;
    background: var(--panel); border: 1px solid var(--panel-border); border-radius: 14px;
  }
  .tab {
    padding: 10px 38px; font-size: 1.02rem; font-weight: 800; letter-spacing: .04em;
    border-radius: 10px; cursor: pointer; color: var(--muted); transition: all .15s;
  }
  .tab.active { color: #fff; background: linear-gradient(135deg, var(--a1), var(--a2)); box-shadow: 0 4px 16px rgba(99,102,241,.4); }
  #grid { display: none; }
  .qrow {
    display: flex; align-items: center; justify-content: space-between;
    padding: 13px 18px; margin-bottom: 10px;
    background: var(--panel); border: 1px solid var(--panel-border); border-radius: 14px;
  }
  .qrow .ql { font-weight: 800; font-size: 1.05rem; width: 92px; text-align: left; }
  .chip {
    padding: 3px 12px; font-size: .74rem; font-weight: 800; letter-spacing: .1em;
    border-radius: 999px; color: #c7d2fe; background: rgba(139,92,246,.16); border: 1px solid rgba(139,92,246,.4);
  }
  .dl {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 10px 20px; font-size: .92rem; font-weight: 750; color: #06281f;
    background: linear-gradient(135deg, #34d399, #22d3ee); border: 0; border-radius: 11px;
    cursor: pointer; transition: transform .12s, box-shadow .12s; min-width: 132px; justify-content: center;
  }
  .dl:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(52,211,153,.35); }
  .dl:disabled { opacity: .6; cursor: wait; transform: none; box-shadow: none; }
  .dl.saved { background: rgba(52,211,153,.15); color: var(--good); border: 1px solid rgba(52,211,153,.5); }
  .spin {
    width: 14px; height: 14px; border-radius: 50%; flex: none;
    border: 2px solid rgba(6,40,31,.3); border-top-color: #06281f;
    animation: rot .7s linear infinite;
  }
  @keyframes rot { to { transform: rotate(360deg); } }
  footer { max-width: 680px; margin: 0 auto; padding: 0 18px 46px; color: #6b7194; font-size: .82rem; text-align: center; line-height: 1.6; }
  @media (max-width: 480px) {
    h1 { font-size: 1.7rem; }
    .searchbox { flex-direction: column; }
    button#start { width: 100%; }
    .thumbwrap img { width: 104px; height: 60px; }
    .tab { padding: 10px 26px; }
  }
</style>
</head>
<body>
<header>
  <div class="logo">V</div>
  <div class="brand">
    <div class="name">VYT DOWNLOADER</div>
    <div class="tag">VOX YOUTUBE DOWNLOADER</div>
  </div>
</header>
<main>
  <h1>Grab original songs for VOXAI comparison</h1>
  <p class="sub">Search an artist, song, or topic — or paste a YouTube link. Pick a result, then download MP3 (for analysis) or MP4. Files are also saved to the reference library.</p>
  <div class="searchbox">
    <input id="url" type="text" placeholder="Search or paste YouTube link here" autocomplete="off">
    <button id="start">Search</button>
  </div>
  <div id="error"></div>
  <div id="results"></div>
  <button id="back">&larr; Back to results</button>
  <div id="video"><img id="thumb" alt=""><div class="t" id="title"></div><div class="u" id="meta"></div></div>
  <div class="tabs"><div class="seg">
    <div class="tab active" data-tab="mp3">MP3</div>
    <div class="tab" data-tab="mp4">MP4</div>
  </div></div>
  <div id="grid"></div>
</main>
<footer>Private VOXAI tool. Use downloads for reference-track comparison only and delete them when no longer needed (copyright care per product rules).</footer>
<script>
const $ = s => document.querySelector(s);
let current = null, activeTab = "mp3", lastResults = [];

function showError(msg) { const e = $("#error"); e.textContent = msg; e.style.display = "block"; }
function clearError() { $("#error").style.display = "none"; }
function hideVideo() {
  $("#video").style.display = "none";
  document.querySelector(".tabs").style.display = "none";
  $("#grid").style.display = "none";
  $("#back").style.display = "none";
}

$("#start").addEventListener("click", async () => {
  clearError();
  const input = $("#url").value.trim();
  if (!input) return showError("Search for a song or paste a YouTube link first.");
  const btn = $("#start");
  btn.disabled = true; btn.textContent = "Searching\\u2026";
  try {
    if (/^https?:\\/\\//i.test(input)) {
      lastResults = [];
      $("#results").style.display = "none";
      await loadVideo(input);
    } else {
      const r = await fetch("/api/search?q=" + encodeURIComponent(input));
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Search failed.");
      lastResults = data.results;
      hideVideo();
      renderResults();
    }
  } catch (err) { showError(err.message); }
  finally { btn.disabled = false; btn.textContent = "Search"; }
});

$("#url").addEventListener("keydown", e => { if (e.key === "Enter") $("#start").click(); });

function renderResults() {
  const box = $("#results");
  box.innerHTML = "";
  const head = document.createElement("div");
  head.className = "rhead";
  head.textContent = "RESULTS \\u2014 PICK ONE TO DOWNLOAD";
  box.appendChild(head);
  for (const item of lastResults) {
    const div = document.createElement("div");
    div.className = "result fade";
    const wrap = document.createElement("div"); wrap.className = "thumbwrap";
    const img = document.createElement("img");
    img.loading = "lazy";
    if (item.thumbnail) img.src = item.thumbnail;
    wrap.appendChild(img);
    if (item.duration) {
      const d = document.createElement("span"); d.className = "dur"; d.textContent = item.duration;
      wrap.appendChild(d);
    }
    const txt = document.createElement("div");
    const t = document.createElement("div"); t.className = "rt"; t.textContent = item.title || "";
    const u = document.createElement("div"); u.className = "ru"; u.textContent = item.uploader || "";
    txt.append(t, u);
    div.append(wrap, txt);
    div.addEventListener("click", () => selectResult(item));
    box.appendChild(div);
  }
  box.style.display = "block";
}

async function selectResult(item) {
  clearError();
  $("#results").style.display = "none";
  try {
    await loadVideo(item.webpage_url);
    if (lastResults.length) $("#back").style.display = "inline-block";
  } catch (err) {
    showError(err.message);
    $("#results").style.display = "block";
  }
}

$("#back").addEventListener("click", () => { hideVideo(); $("#results").style.display = "block"; });

async function loadVideo(url) {
  const r = await fetch("/api/info?url=" + encodeURIComponent(url));
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || "Could not read that link.");
  current = { url, ...data };
  $("#thumb").src = data.thumbnail || "";
  $("#title").textContent = data.title || "";
  $("#meta").textContent = [data.uploader, data.duration].filter(Boolean).join(" \\u00b7 ");
  $("#video").style.display = "block";
  $("#video").classList.add("fade");
  document.querySelector(".tabs").style.display = "flex";
  renderGrid();
}

document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", () => {
  activeTab = t.dataset.tab;
  document.querySelectorAll(".tab").forEach(x => x.classList.toggle("active", x === t));
  renderGrid();
}));

function renderGrid() {
  const grid = $("#grid");
  grid.innerHTML = "";
  const rows = activeTab === "mp3"
    ? current.mp3_bitrates.map(b => ({ label: b + " kbps", q: b }))
    : current.mp4_heights.map(h => ({ label: h + "p", q: String(h) }));
  for (const row of rows) {
    const div = document.createElement("div");
    div.className = "qrow fade";
    const l = document.createElement("div"); l.className = "ql"; l.textContent = row.label;
    const c = document.createElement("span"); c.className = "chip"; c.textContent = activeTab.toUpperCase();
    const b = document.createElement("button"); b.className = "dl";
    b.innerHTML = "\\u2b73&nbsp; Download";
    b.addEventListener("click", () => startDownload(b, row.q));
    div.append(l, c, b);
    grid.appendChild(div);
  }
  grid.style.display = "block";
}

async function startDownload(btn, quality) {
  clearError();
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> Downloading\\u2026';
  try {
    // Use the resolved video URL so a search query isn't re-resolved.
    const target = current.webpage_url || current.url;
    const qs = `url=${encodeURIComponent(target)}&fmt=${activeTab}&quality=${quality}`;
    const r = await fetch("/api/download?" + qs);
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw new Error(data.detail || "Download failed.");
    }
    const blob = await r.blob();
    const name = (r.headers.get("Content-Disposition") || "").match(/filename="?([^\";]+)/)?.[1]
      || `reference.${activeTab}`;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    URL.revokeObjectURL(a.href);
    btn.classList.add("saved");
    btn.innerHTML = "Saved \\u2713";
    setTimeout(() => { btn.classList.remove("saved"); btn.innerHTML = "\\u2b73&nbsp; Download"; btn.disabled = false; }, 2500);
    return;
  } catch (err) {
    showError(err.message);
    btn.disabled = false;
    btn.innerHTML = "\\u2b73&nbsp; Download";
  }
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
