# Howard — pull & rebuild the VOX Suite

The standing, copy-paste rebuild for the box Howard runs on the Tailscale network.
Use this whenever `main` has moved and the running service needs to catch up.

The checkout lives at `~/.openclaw/mary-workspace/aaroncodex` — the commands below
use that path.

---

## If `main` looks stale after a fetch (read this first)

Howard's environment fetches through a git mirror/cache that can lag GitHub. The
symptom is a `git fetch origin main` that reports the **wrong, older** commit
(e.g. it lands on `7f54567` when GitHub's real `main` is newer) — often several
times in a row — and files that exist on GitHub appear "missing." A plain fetch
will not shake it loose.

The fix is to fetch the **exact commit SHA** and hard-reset to it, which bypasses
the cached branch ref. Get the current `main` SHA from GitHub
(`github.com/goodermine/aaroncodex` → latest commit on `main`), then:

```bash
cd ~/.openclaw/mary-workspace/aaroncodex && \
git fetch origin <FULL_SHA> && \
git reset --hard <FULL_SHA> && \
git log -1 --format='Now on %h — %s'
```

If even the explicit-SHA fetch fails with "couldn't find remote ref," `origin` is
pointing at a stale mirror — check `git remote -v` and any
`git config --get-regexp 'url\..*\.insteadof'` rewrite, or re-clone fresh from
`https://github.com/goodermine/aaroncodex.git`.

## When a FULL (`--no-cache`) rebuild is required

A plain `docker compose build` reuses cached layers and is fine for HTML/JS/Python
edits. A **full rebuild** is only needed when the dependency layer changed —
most importantly a **`setuptools` / pyproject pin change** (the one that fixed the
Auto Tune `pkg_resources` error). When in doubt, do the full rebuild: it is slower
(~10–20 min) but never wrong.

## The one command

```bash
cd ~/.openclaw/mary-workspace/aaroncodex && \
git fetch origin main && \
git checkout main && \
git reset --hard origin/main && \
git log -1 --format='Now on %h — %s' && \
docker compose down && \
docker compose build --no-cache && \
docker compose up -d && \
sleep 5 && \
curl -fsS http://localhost:18080/api/build | python3 -m json.tool
```

The last line prints what the running service is actually serving. Confirm:

- `"commit"` matches the `git log` line printed just above, and
- `"matches_head": true`.

If those two agree, the rebuild is live. If `/api/build` still shows the old
commit, the container did not rebuild — re-run `docker compose build --no-cache`,
and if that fails on disk space, `docker system prune -f` to free the layer cache
first.

## Smoke test (once it's up)

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
