---
title: "VOX Suite — Docker deployment"
category: ops
status: active
created: 2026-08-09
topics: [docker, deployment, cloud, hosting]
---

# VOX Suite — Docker deployment

One image runs the whole suite — Analyze, Polish, Fused, `/monitor`,
`/timbertones` and `/hub` — on **one port (8080)**. The *same image* runs on
Candi's machine and on a cloud host, which is the point (see
`docs/plans/PACKAGING_AND_DEPLOYMENT_PLAN.md`, Option C).

Files: `Dockerfile`, `docker-compose.yml`, `.dockerignore` (all at the repo root).

## Build

```bash
# Full image — includes RoFormer separation + auto-tune (what scoring uses).
docker build -t voxsuite .

# Lean image — light apps + scoring only, DSP-fallback separation (smaller/faster
# to build, but NOT canonical-separation reproducible).
docker build -t voxsuite:lite \
  --build-arg WITH_SEPARATION=0 --build-arg WITH_PITCH=0 .
```

The full image is large (~2.5–4 GB) — that's the torch/onnxruntime + separation
model, and it's expected (the plan calls this out). Build args:

| Arg | Default | Effect |
|---|---|---|
| `WITH_SEPARATION` | `1` | Install `audio-separator` + `onnxruntime` (RoFormer stems). Required for canonical scores and Fused end-to-end. |
| `WITH_PITCH` | `1` | Install `pyworld` for Polish auto-tune. |
| `PREFETCH_MODEL` | `1` | Bake the pinned `vocals_mel_band_roformer.ckpt` into the image (best-effort; downloads on first run if the build host is offline). |

## Run

```bash
docker compose up --build          # → http://localhost:8080
# or plain docker:
docker run -p 8080:8080 -v vox-data:/data voxsuite
```

- **Data**: job state, uploads and new analyses are written to **`/data`** — the
  compose file mounts a named volume so they survive restarts and rebuilds. With
  bare `docker run`, always pass `-v vox-data:/data`.
- **Config**: the app needs no env to run. The engine/app roots and `VOX_BASE`
  are already set in the image.

## How Candi uses it

The container is the *sealed engine*; Candi (the OpenClaw agent) stays on the
host and calls into it. Two ways, unchanged from today:

- **Run the engine directly** (her current pattern) — exec the CLI against a file
  on the mounted volume:
  ```bash
  docker exec -it <container> \
    python voxanalysis/vox-analysis/engine/analyse_song.py /data/uploads/take.mp3
  ```
- **HTTP** — upload/drive through the same `/api/*` endpoints the web decks use.

Her Telegram flow doesn't change: song in → Candi runs the analysis (now via the
container) → result back → hand to Claude to interpret.

## Putting it on a cloud server

The image is the artefact; the cloud move is `docker run` on the host plus three
things that become real once strangers can reach it:

1. **TLS/HTTPS** — the browser mic (monitor, TimberTones) only works on a secure
   context, and you want TLS anyway. Front `vox` with a reverse proxy that
   terminates TLS: **Caddy** (auto-HTTPS from a domain) or Traefik. See the
   commented `proxy:` block in `docker-compose.yml`.
2. **Auth** — the scoring engine, the 50-reference calibration pack and **private
   singer data** must sit behind a login. Add basic-auth at the proxy, or keep
   the instance on Tailscale. Do not expose port 8080 to the public internet
   unproxied.
3. **A persistent volume** — same `/data` volume, on managed storage so results
   survive redeploys.

**GPU:** RoFormer separation runs on CPU but is slow. For a GPU host, base the
image on `nvidia/cuda:12.x-cudnn-runtime` instead of `python:3.11-slim`, install
`onnxruntime-gpu`, and add the `deploy.resources` GPU block (commented in the
compose file). The light half (monitor/TimberTones/hub/report viewing) needs no
GPU at all — a cheap always-on box can serve it while heavy analysis runs
elsewhere.

## Acceptance checklist (run on a host that can complete the build)

From the packaging plan — this proves the image is correct end to end:

```bash
# 1. builds and starts with no host Python
docker compose up --build -d

# 2. every surface answers
for p in / /analyze /polish /monitor/ /timbertones/ /hub; do
  echo -n "$p -> "; curl -s -o /dev/null -w '%{http_code}\n' localhost:8080$p
done
curl -s localhost:8080/api/systems | head -c 200      # registry JSON

# 3. the engine + calibration pack are baked in correctly
docker compose exec vox python3 tools/score_preflight.py   # must exit 0

# 4. tests pass inside the image
docker compose exec vox python3 -m pytest voxsuite/tests -q
docker compose exec vox python3 -m pytest voxanalysis/vox-analysis/engine/tests/test_scoring.py -q

# 5. one real take runs end to end through Fused (separation → analysis → polish)
#    upload a file via the deck at localhost:8080 and confirm a full result.
```

## Notes / gotchas

- **Headless plots**: `MPLBACKEND=Agg` is set so matplotlib (onset PNGs) works
  without a display.
- **Separation model cache**: prefetched at build when possible; otherwise the
  ~200 MB model downloads on the first analysis. It lives in the container's
  writable layer — for a stable cache across container recreation, confirm your
  `audio-separator` version's model dir and mount a volume there.
- **Non-root**: the container runs as user `vox` (uid 10001); `/data` is
  writable by it.
- **Two separation paths**: voxpolish imports `audio-separator` in-process (the
  Fused path); `engine/tools/stems/batch_stems.sh` uses a dedicated venv at
  `~/.venvs/vox-sep-uvr` — both are provisioned in the image without duplicating
  torch.
