#!/usr/bin/env python3
"""VOX Reference Downloader.

Small self-hosted web tool for grabbing original/reference songs from
YouTube so they can be compared against a singer's take in the VOXAI
pipeline. One page: paste a link (or type a song name), press Start,
pick MP3 (for analysis) or MP4, and download. Every download is also
kept in the reference library folder so candi_phase1.py /
analyse_song.py can pick it up:

    openclaw-data/vox-coach/uploads/reference/

Run:

    pip install -r requirements.txt
    python3 app.py            # serves http://127.0.0.1:8765

Requires ffmpeg on PATH (already required by the VOXAI backend).

Agents should use scripts/fetch_reference.py instead of this page - it
wraps the same download logic (reference_dl.py) as a one-shot CLI.

Product rule reminder (HANDOFF.md): reference-track comparison requires
copyright care - use downloads for private comparison/analysis only and
do not retain reference media longer than needed.
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

app = FastAPI(title="VOX Reference Downloader")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE_HTML


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
<title>VOX Reference Downloader</title>
<style>
  :root { --navy: #3d4577; --blue: #1e88f7; }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  body { background: #fff; color: #212529; }
  header { background: var(--navy); color: #fff; padding: 18px 24px; font-size: 1.4rem; font-weight: 600; }
  main { max-width: 640px; margin: 0 auto; padding: 28px 16px 60px; }
  h1 { text-align: center; font-size: 2.1rem; line-height: 1.25; margin-bottom: 14px; }
  .sub { text-align: center; color: #444; margin-bottom: 26px; }
  input#url { width: 100%; padding: 16px 18px; font-size: 1.05rem; border: 2px solid var(--navy); border-radius: 12px; outline: none; }
  button#start { width: 100%; margin-top: 14px; padding: 15px; font-size: 1.2rem; font-weight: 600; color: #fff; background: var(--blue); border: 0; border-radius: 10px; cursor: pointer; }
  button#start:disabled { opacity: .6; cursor: wait; }
  #error { display: none; margin-top: 14px; padding: 12px 14px; border-radius: 8px; background: #fdecea; color: #b3261e; }
  #video { display: none; margin-top: 24px; text-align: center; }
  #video img { max-width: 100%; border-radius: 12px; }
  #video .t { font-weight: 600; margin-top: 10px; }
  #video .u { color: #666; font-size: .92rem; margin-top: 2px; }
  .tabs { display: none; justify-content: center; gap: 14px; margin: 26px 0 18px; }
  .tab { padding: 12px 34px; font-size: 1.15rem; font-weight: 700; border-radius: 10px; cursor: pointer; border: 2px solid transparent; }
  .tab.mp3 { color: #fff; background: linear-gradient(90deg, #7b2ff7, #4a5cf0); }
  .tab.mp4 { color: #111; background: #fff; border-color: #e040a5; }
  .tab.inactive { filter: grayscale(1); opacity: .55; }
  table { display: none; width: 100%; border-collapse: collapse; }
  thead th { background: #eceef1; padding: 13px 8px; font-size: .95rem; letter-spacing: .04em; }
  tbody td { padding: 14px 8px; text-align: center; border-bottom: 1px solid #eee; font-weight: 600; }
  tbody td.fmt { color: #556; }
  .dl { display: inline-flex; align-items: center; justify-content: center; width: 52px; height: 44px; border: 2px solid #26a69a; border-radius: 10px; background: #fff; cursor: pointer; font-size: 1.2rem; }
  .dl:disabled { opacity: .5; cursor: wait; }
  footer { max-width: 640px; margin: 0 auto; padding: 0 16px 40px; color: #777; font-size: .85rem; text-align: center; }
</style>
</head>
<body>
<header>VOX Reference Downloader</header>
<main>
  <h1>Grab original songs for VOXAI comparison</h1>
  <p class="sub">Paste a YouTube link or type a song name to pull the original track as MP3 (for analysis) or MP4. Files are also saved to the reference library.</p>
  <input id="url" type="text" placeholder="Search or paste YouTube link here" autocomplete="off">
  <button id="start">Start &nbsp;&rarr;</button>
  <div id="error"></div>
  <div id="video"><img id="thumb" alt=""><div class="t" id="title"></div><div class="u" id="meta"></div></div>
  <div class="tabs">
    <div class="tab mp3" data-tab="mp3">MP3</div>
    <div class="tab mp4 inactive" data-tab="mp4">MP4</div>
  </div>
  <table id="grid">
    <thead><tr><th>QUALITY</th><th>FORMAT</th><th>ACTION</th></tr></thead>
    <tbody></tbody>
  </table>
</main>
<footer>Private tool for VOX Cloud Alpha. Use downloads for reference-track comparison only and delete them when no longer needed (copyright care per product rules).</footer>
<script>
const $ = s => document.querySelector(s);
let current = null, activeTab = "mp3";

function showError(msg) { const e = $("#error"); e.textContent = msg; e.style.display = "block"; }
function clearError() { $("#error").style.display = "none"; }

$("#start").addEventListener("click", async () => {
  clearError();
  const url = $("#url").value.trim();
  if (!url) return showError("Paste a YouTube link or type a song name first.");
  const btn = $("#start");
  btn.disabled = true; btn.textContent = "Fetching\\u2026";
  try {
    const r = await fetch("/api/info?url=" + encodeURIComponent(url));
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Could not read that link.");
    current = { url, ...data };
    $("#thumb").src = data.thumbnail || "";
    $("#title").textContent = data.title || "";
    $("#meta").textContent = [data.uploader, data.duration].filter(Boolean).join(" \\u00b7 ");
    $("#video").style.display = "block";
    document.querySelector(".tabs").style.display = "flex";
    renderGrid();
  } catch (err) { showError(err.message); }
  finally { btn.disabled = false; btn.innerHTML = "Start &nbsp;&rarr;"; }
});

document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", () => {
  activeTab = t.dataset.tab;
  document.querySelectorAll(".tab").forEach(x => x.classList.toggle("inactive", x !== t));
  renderGrid();
}));

function renderGrid() {
  const body = $("#grid tbody");
  body.innerHTML = "";
  const rows = activeTab === "mp3"
    ? current.mp3_bitrates.map(b => ({ label: b + "kbps", q: b }))
    : current.mp4_heights.map(h => ({ label: h + "p", q: String(h) }));
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.label}</td><td class="fmt">${activeTab.toUpperCase()}</td>` +
      `<td><button class="dl" title="Download">\\u2b73</button></td>`;
    tr.querySelector("button").addEventListener("click", ev => startDownload(ev.target, row.q));
    body.appendChild(tr);
  }
  $("#grid").style.display = "table";
}

async function startDownload(btn, quality) {
  clearError();
  btn.disabled = true; btn.textContent = "\\u23f3";
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
  } catch (err) { showError(err.message); }
  finally { btn.disabled = false; btn.textContent = "\\u2b73"; }
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
