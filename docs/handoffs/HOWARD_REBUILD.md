# Howard — sync & rebuild the live VOX Suite

The standing, copy-paste procedure for the box Howard runs on the Tailscale
network. Use it whenever `main` has moved and the live service needs to catch up.

## The two checkouts (don't mix them up)

| Purpose | Path | Notes |
|---|---|---|
| **Live deployment** | `~/.openclaw/workspace/vox-suite-deploy` | This is what the running container is built from. Compose project `vox-suite-deploy`, base `docker-compose.yml` **+ untracked `docker-compose.override.yml`** (the override maps host **18080** → container 8080). Rebuild happens **here**. |
| Dev/source clone | `~/.openclaw/mary-workspace/aaroncodex` | A working clone for reading/editing. Not what serves traffic. |

The untracked `docker-compose.override.yml` carries the 18080 mapping and is
**not** touched by `git reset` — leave it in place.

---

## ⚠️ The stale git-mirror trap — read before any sync

Howard's environment fetches through a git mirror/cache that can lag GitHub. The
symptom: `git fetch origin main` reports the **wrong, older** commit (it landed on
`7f54567` repeatedly while GitHub's real `main` was far ahead), and files that
exist on GitHub look "missing." **Because of this, never `git reset --hard
origin/main` here** — under a stale mirror that command drags the checkout
*backwards*. Always sync to an **explicit commit SHA** instead.

Get the current `main` SHA from GitHub (`github.com/goodermine/aaroncodex` → latest
commit on `main`), call it `<SHA>`, and use it everywhere below.

If even `git fetch origin <SHA>` fails with "couldn't find remote ref," the mirror
is badly stale — check `git remote -v` and any
`git config --get-regexp 'url\..*\.insteadof'` rewrite, or re-clone fresh from
`https://github.com/goodermine/aaroncodex.git`.

---

## Step 1 — sync the live checkout to `<SHA>` (and verify before building)

```bash
cd ~/.openclaw/workspace/vox-suite-deploy && \
git fetch origin <SHA> && \
git reset --hard <SHA> && \
test "$(git rev-parse HEAD)" = "<SHA>" && echo "OK on <SHA>" || echo "STOP — HEAD is not <SHA>"
```

If it prints `STOP`, do **not** build — the mirror served the wrong commit. Re-run
the fetch-by-SHA, or fix `origin` per the trap section above.

## Step 2 — is a rebuild even needed?

The image bakes source at build time, so a running container keeps its old code
until rebuilt. But a rebuild is only *worth the downtime* when either:

- **application code changed** since the running image, or
- the **dependency layer** changed (most importantly a `setuptools` / pyproject
  pin — the `setuptools<70` fix that keeps `pkg_resources` importable for Auto
  Tune).

Check both without touching the live service:

```bash
# a) what commit is the running image, vs your checkout HEAD?
curl -fsS http://localhost:18080/api/build | python3 -c "import sys,json;d=json.load(sys.stdin);print('running image commit:',d.get('git',{}).get('commit'))"
git -C ~/.openclaw/workspace/vox-suite-deploy rev-parse --short=12 HEAD

# b) are the Auto Tune deps already correct inside the running container?
docker exec vox-suite-deploy-vox-1 python -c "import setuptools, pkg_resources; print('setuptools', setuptools.__version__, '| pkg_resources OK'); import pyworld; print('pyworld OK')"
```

- If the two commits in (a) differ **only** by docs/analysis/memory files, and (b)
  prints `setuptools 69.x … pkg_resources OK` + `pyworld OK`, then **the live
  service already has every fix — do not rebuild.** (A `pkg_resources`
  DeprecationWarning is fine; only an ImportError matters.)
- If application code differs, or (b) errors (`No module named 'pkg_resources'`,
  setuptools ≥ 70, or pyworld missing), continue to Step 3.

## Step 3 — rebuild (only if Step 2 says so)

From the deploy dir, compose auto-loads `docker-compose.yml` + the override and
uses project `vox-suite-deploy` — no extra flags. Build **first** so the service
stays up until the swap (minimal downtime):

```bash
cd ~/.openclaw/workspace/vox-suite-deploy && \
docker compose build --no-cache && \
docker compose up -d && \
sleep 5 && \
curl -fsS http://localhost:18080/api/build | python3 -m json.tool
```

`--no-cache` is what forces the dependency layer to re-resolve (the whole point of
the Auto Tune fix). Then confirm `/api/build` shows `"commit": "<SHA prefix>…"` and
`"matches_head": true`. If it still shows the old commit, the image didn't
rebuild — re-run `docker compose build --no-cache`; if that fails on disk space,
`docker system prune -f` to free the layer cache first.

## Smoke test (after a rebuild)

- `/` and `/polish` return **200** (editable-install fix — no more HTTP 500).
- `/hub` loads and its links are **clickable**, not dead.
- **Polish** → upload a full song → choose **"Full song (isolate)"** → the deep
  bleed / warble artefact should be gone (the take is separated before processing).
- **Auto Tune** runs without the `pkg_resources` error.
- `/timbertones` and `/monitor` — mic works over the **Tailscale HTTPS** URL, and
  the gate slider responds.

## Serving it on the tailnet (HTTPS for mic access)

The mic only works from a secure context, so serve the suite over Tailscale's
HTTPS proxy rather than raw `http://<ip>:18080`:

```bash
tailscale serve --bg --https=443 http://localhost:18080
tailscale serve status
```

Then reach it at `https://<machine>.<tailnet>.ts.net/` from any device signed into
the tailnet. `/monitor`, `/timbertones`, and the Vox recorder all need this HTTPS
origin for `getUserMedia` to grant the microphone.

---

*This is rebuild plumbing. The singer-facing deliverable is always the full
analysis (see `ANALYSIS_RUNBOOK.md`), never a build hash.*
