# Handoff: run the VOX Suite over Tailscale for multi-device testing (Candi)

Goal: get **both** services running on the A9 Max, reachable over Tailscale, so
Aaron can test on **Android, iPhone, and desktop**. The two apps:

- **VoxPolish editor** — the cleanup/tune UI (default port **8765**)
- **VoxAnalysis viewer** — the analysis UI (default port **8766**)

Both default to `127.0.0.1` (localhost only). To reach them from other devices
they must bind to `0.0.0.0` (all interfaces) so the Tailscale interface is
included. Commands below do that.

## 0. Prereqs (mostly already done)

- Tailscale installed and logged in on the A9 Max **and** on each test device
  (iPhone/Android/desktop), all on the same tailnet.
- The repo pulled and both stacks installed (Candi already validated RoFormer):
  ```bash
  cd aaroncodex && git pull            # branch: claude/voiceassist-plugin-planning-krhz0d
  # VoxPolish
  cd voxpolish && python3 -m venv .venv && source .venv/bin/activate
  pip install -e '.[ui,pitch,separation]'
  # VoxAnalysis viewer (separate shell/venv)
  cd ../voxanalysis/vox-analysis/viewer
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  # ffmpeg on PATH; the RoFormer stem venv (~/.venvs/vox-sep-uvr) already set up
  ```
- Get the A9 Max's tailnet name/IP (use in the URLs below):
  ```bash
  tailscale status          # shows the machine name, e.g. a9max
  tailscale ip -4           # the 100.x.y.z tailnet IP
  ```
  The hostname form looks like `a9max.<tailnet>.ts.net` (e.g. `a9max.tail8e8c02.ts.net`).

## 1. Start both services bound to the tailnet

Two shells (or `tmux`/`screen`), each with its venv activated:

```bash
# Shell A — VoxPolish editor
cd aaroncodex/voxpolish && source .venv/bin/activate
voxpolish ui --host 0.0.0.0 --port 8765

# Shell B — VoxAnalysis viewer
cd aaroncodex/voxanalysis/vox-analysis/viewer && source .venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8766
```

Leave both running.

## 2. Open from any device on the tailnet

In the browser on iPhone / Android / desktop:

- VoxPolish editor: `http://a9max.<tailnet>.ts.net:8765/`
- VoxAnalysis viewer: `http://a9max.<tailnet>.ts.net:8766/`

(Or use the `100.x.y.z` tailnet IP instead of the hostname.) **Hard-refresh**
each page (or use a private tab) so the new **cyan** UI loads, not a cached copy.

## 3. Recommended for mobile — HTTPS via `tailscale serve`

Plain HTTP works on the tailnet, but mobile browsers show a "Not secure" label
and some features prefer HTTPS. `tailscale serve` puts a real cert in front
while the apps stay on localhost. Keep the apps started on `127.0.0.1` (drop the
`--host 0.0.0.0`) and run:

```bash
tailscale serve --bg --https=8443 127.0.0.1:8765   # VoxPolish  -> https://a9max.<tailnet>.ts.net:8443
tailscale serve --bg --https=9443 127.0.0.1:8766   # Viewer     -> https://a9max.<tailnet>.ts.net:9443
tailscale serve status                              # confirm the mappings
```

Use **separate ports** (not paths) — both apps use absolute `/static` and `/api`
URLs, so path-mounting would break them; port-based proxying is clean.
To tear down: `tailscale serve --https=8443 off` (and 9443).

## 4. What to test (the end-to-end flow)

VoxPolish editor, on each device:
1. Upload a vocal (drag-drop + file picker); pick **Clean + Auto Tune** vs Clean.
2. Watch processing; land in the editor.
3. A/B original vs cleaned; toggle modules; move sliders (Tune starts at 10%);
   check the **pitch lane** and the waveform pan / zoom / scrollbar.
4. **Render**, then **Download** — confirm the file is the take you approved.
5. A full song exercises **RoFormer separation** (song mode) — first run
   downloads the MIT model; expect it to be **slow on CPU** (that's known/fine).

VoxAnalysis viewer, on each device:
1. Upload a vocal, run an analysis; confirm the report renders and playback works.
2. Confirm the UI is the shared **cyan** VOX Suite look (design tokens adopted).

Report per device (Android / iPhone / desktop): layout issues, touch-target
problems, anything that doesn't fit or work, plus any server-side traceback.

## Notes

- **Reachability:** `0.0.0.0` exposes the ports on *all* the A9 Max's networks,
  not only Tailscale. On a trusted home network that's fine for testing; for
  tighter scope, bind to the tailnet IP instead (`--host 100.x.y.z`) or use the
  `tailscale serve` HTTPS path in §3.
- **Firewall:** if a device can't connect, check the A9 Max host firewall allows
  inbound on 8765/8766 (or 8443/9443 for the serve path).
- RoFormer on CPU is heavy (song-mode separation minutes/song) — expected; GPU is
  the hosting plan, not a dev-box requirement.
