# VOX Suite — testing handoff

Everything below is on `main`. Three command decks now share one look and one
telemetry system:

| Deck | App | URL (once running) |
|------|-----|--------------------|
| **Polish** — repair / level / tune | VoxPolish | `http://<host>:8765/deck` |
| **Analyze** — measure / score / compare | VoxAnalysis viewer | `http://<host>:8766/deck` |
| **Fused** — upload once, both engines | VoxSuite | `http://<host>:8767/deck` |

Each classic UI still lives at `/` — the decks are additive, nothing was removed.
Append `?demo=1` to any deck URL for a **no-backend walkthrough** (great for a first look).

---

## 0. Clean slate (get rid of the old stuff)

You almost certainly have an old clone with stale branches, virtualenvs, and
leftover session/runtime folders. Wipe all of it and get exactly what's on `main`.

**Option A — reset the existing folder in place (keeps your git remote + creds):**
```bash
cd aaroncodex                 # your existing clone
git fetch origin
git checkout main
git reset --hard origin/main  # discard any local edits, match main exactly
git clean -fdx                # ⚠️ DELETES all untracked/ignored files:
                              #    old venvs, __pycache__, runtime dirs, sessions, uploads
# delete every local branch except main:
git branch | grep -vE '^\*?\s*main$' | xargs -r git branch -D
```
`git clean -fdx` is the hammer — it removes anything not tracked by git, which is
exactly the accumulated "shit" (build junk, old `.venv`s, session folders). It does
**not** touch your committed code. If you keep anything hand-made in the repo folder
that you want to save, copy it out first.

**Option B — nuke and re-clone (simplest, if you don't mind re-entering creds):**
```bash
cd ..
rm -rf aaroncodex
git clone https://github.com/goodermine/aaroncodex.git
cd aaroncodex
```

Confirm you're current:
```bash
git log --oneline -1     # should be the latest commit on main
```

---

## Prereqs (once per machine)

- **Python 3.10+** and **ffmpeg + ffprobe** on `PATH`
  (`sudo apt install ffmpeg` on Linux).
- Each app below gets its **own** virtualenv — don't share one for the two
  individual decks; they have different dependency stacks.
- To reach the decks from your **phone/other devices** (e.g. over Tailscale), start
  each server with `--host 0.0.0.0` (shown below) and use the machine's Tailscale
  name or LAN IP as `<host>`. On localhost only, use `127.0.0.1`.

---

## 1. Polish deck  →  `:8765/deck`

```bash
cd voxpolish
python3 -m venv .venv && source .venv/bin/activate
# CPU-only AMD box: install the CPU torch wheel FIRST, then the extras
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -e '.[separation,clean,vad]'     # or just: pip install -e .   (voice mode, DSP fallbacks)
voxpolish ui --host 0.0.0.0 --port 8765
```
Open `http://<host>:8765/deck`. Upload a vocal take → the Signal Modules rail,
waveform, and export tray are live. (`voxpolish ui` with no flags stays on
localhost.)

## 2. Analyze deck  →  `:8766/deck`

```bash
cd voxanalysis/vox-analysis/viewer
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# device access needs 0.0.0.0 (plain `python app.py` binds localhost only):
python -m uvicorn app:app --host 0.0.0.0 --port 8766
```
Open `http://<host>:8766/deck`. Upload a take → watch the chain, pitch scope,
readout and report. First separation may pull the UVR model; give it a minute.

## 3. Fused deck  →  `:8767/deck`

**Preview it now (no setup):** open any running deck and click **Fused run**, or go
straight to `http://<host>:8767/deck?demo=1` once step 3a is up — it plays a full
simulated run so you can see the shape.

**3a. Serve the deck** (this alone gives you `?demo=1` and the UI):
```bash
cd /path/to/aaroncodex
python3 -m venv .venv-suite && source .venv-suite/bin/activate
pip install -e voxsuite
python -c "from voxsuite.server.app import create_app; import uvicorn; \
  uvicorn.run(create_app('./_fused'), host='0.0.0.0', port=8767)"
```

**3b. Real Fused run (advanced — one shared venv holds everything).** The Fused
orchestrator imports *both* engines, so a live run needs their deps together:
```bash
source .venv-suite/bin/activate
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -e './voxpolish[separation,clean,vad]'          # VoxPolish engine
pip install -r voxanalysis/vox-analysis/viewer/requirements.txt   # Analyze engine deps
export VOX_ANALYSIS_ROOT="$PWD/voxanalysis/vox-analysis"    # point the adapter at the engine
python -c "from voxsuite.server.app import create_app; import uvicorn; \
  uvicorn.run(create_app('./_fused'), host='0.0.0.0', port=8767)"
```
Then upload once at `:8767/deck`. If vocal separation isn't available in that env,
the deck says so ("Isolation skipped") and still runs on the upload as a vocal —
it degrades loudly, never silently.

---

## What to poke at

- **Mode switch** (top-left of each deck) jumps between Polish / Analyze / Fused —
  it links by hostname + port, so all three servers must be running and reachable
  for the switch to work across the suite.
- **Export tray** — every deck ends in downloadable deliverables (polished vocal,
  analysis report, edit document; Fused gives all three).
- **Light/dark, phone/desktop** — the kit is responsive and theme-aware.
- **The classic UIs at `/`** are untouched if you want to compare.

## Known limits (so nothing surprises you)

- Real **Fused** needs the combined venv in 3b; the two individual decks (1 & 2)
  are the fully-proven path for this round.
- First-ever separation downloads the UVR model (one-time, needs network).
- The Analyze viewer's `python app.py` binds localhost; use the `uvicorn ... 0.0.0.0`
  line for device testing.

Ping me with anything that looks off — screenshots of the deck state + which URL
help most.
