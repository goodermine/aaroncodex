# Handoff — Polish: Auto Tune silently bypassed, and no way to A/B

Date: 2026-07-26

Aaron reported on the live `/polish` deck: the **Original** chip doesn't play, and
un-ticking **Auto Tune** makes no audible difference. Candi diagnosed it; both
findings confirmed in the code, and one is worse than reported.

## What was wrong

**1. The CLEANED / ORIGINAL chips were inert `<span>` labels.** No click handler
existed. The deck only ever loaded `/api/audio/cleaned`. The endpoint
`/api/audio/original` (→ `work_vocal.wav`) already existed and was simply never
used, so there was no way to hear the render against the raw take — which is
exactly how you'd notice a module doing nothing.

**2. Auto Tune failed silently.** On Aaron's deployed host the WORLD vocoder
(`pyworld`) can't import because `pkg_resources` is missing, so
`pitch.apply_correction()` raises and the render falls back to untuned audio. The
server *did* record `"tuner skipped: …"` in the render notes and return it from
`GET /api/render` — but **the deck never read `notes` at all.** Not "didn't show
it clearly": it was discarded entirely. A broken vocoder was indistinguishable
from a working one with little to correct.

> Not reproducible in the dev sandbox — `pyworld` imports fine there. This is an
> environment fault on the deployed host, but the *silence* was a code fault.

## Fixed in the repo

- **`vocoder_status()`** replaces the bool-only check and returns *why* it failed.
  It now catches **any** exception, not just `ImportError`: a stripped setuptools
  makes `pyworld`'s `pkg_resources` import blow up in other ways, and a missing
  compiled library raises `OSError`. The `RuntimeError` message now includes the
  real import error.
- **Render notes are explicit about tune state**, every render:
  - `WARNING: Auto Tune was ON but could not be applied — <reason>`
  - `Auto Tune is off (bypassed) — no pitch correction applied`
  - `Auto Tune is on but this take has no correction curve`
  - `tuned (max N cents)` when it genuinely applied
- **`GET /api/session` now reports `capabilities.tune`** plus
  `tune_unavailable_reason`, so the UI can warn *before* the user hunts for a
  difference that was never applied.
- **Deck: the chips are real A/B buttons.** They switch the audio source and
  **preserve the playhead** across the switch, so the comparison lands on the same
  moment.
- **Deck: a render-notes panel** (amber when warning) shows the notes after every
  render, and on load shows a standing warning if `capabilities.tune` is false.
  Notes are also written to the telemetry log.
- Guard test in `voxsuite/tests/test_unified.py`.

Tests: voxpolish 150 passed, voxsuite 25 passed.

> One test previously asserted `result["notes"] == []` and another used a
> `"tuned" in note` substring check. The first was over-specified (an
> informational state note is wanted, not a failure) and now asserts *no warning*
> instead; the second was tripping on "un**tuned**", so the note was reworded to
> "no pitch correction applied". Neither assertion was weakened in intent.

## What still needs doing on the deployed host — Candi

The repo now *reports* the failure loudly, but the vocoder is still broken on the
server. Fix the environment:

```bash
# in the venv that runs the polish service
pip install --upgrade setuptools        # restores pkg_resources
python -c "import pyworld; print('vocoder OK')"
# if pyworld itself is missing:
pip install 'voxpolish[pitch]'
```

Then restart the service and confirm:

```bash
curl -s https://<host>/api/session | python3 -m json.tool | grep -A2 capabilities
# expect: "tune": true
```

Until that's done, the deck will show a standing amber warning that Auto Tune
cannot run, which is the correct behaviour — **the render genuinely is untuned**.

**Also worth re-rendering Aaron's Pressure-Down-Cook session afterwards.** Its
current `vocal_cleaned.wav` was rendered with tune bypassed, so whatever he has
been listening to has no correction in it at all.

## Note on this take specifically

Aaron's Pressure-Down-Cook analysis shows the sung pitch mostly *sliding* rather
than sitting off-centre (see `HANDOFF_ALL_TAKES_SCORES_V4` and
`docs/practice/`). Auto Tune corrects toward a grid; it will not fix a note that
sags 2 semitones over its length, and pushing the Tune amount up to chase that
will sound artificial. Worth telling him so he doesn't expect the tuner to solve
the breath-support issue.

---

## Follow-up (26 Jul): the fix was on main but not visible on the deployed deck

Aaron re-checked after Candi re-pulled and the **Original** button still wasn't
there. Verified: the fix **is** on `origin/main` (`54ff477`) in
`voxpolish/src/voxpolish/server/static/deck.html`. So this is a deployment
question, not a code one.

Note the deck HTML is `read_text()` per request, so a `git pull` alone should make
the Original button appear **without a restart**. The Python changes
(`session.py`, `app.py`, `pitch.py`) *do* need a restart.

**New: `GET /api/build`** (on both the unified server and standalone Polish)
answers "which build is live" from a browser. It hashes the deck files the running
process actually reads and reports the checkout's commit/branch/dirty state:

```
GET https://<host>/api/build
```

The fixed Polish deck hashes to **`a6be9074d2b8`**. If `decks.polish.sha1_12` is
anything else, the running service is not reading the pulled file.

Diagnostic order:

1. **Hit `/api/build`.** Compare `decks.polish.sha1_12` to `a6be9074d2b8`, and
   check `git.commit` is `54ff477…` or later.
2. **Check `decks.polish.path` and `git.checkout`.** If that path is not inside
   the directory Candi pulled, the service is running from a *different checkout*
   (or a site-packages copy) — that is the most likely cause. Restart the service
   from the pulled checkout, or reinstall.
3. **Check `git.branch`.** If it is not `main`, the pull landed somewhere else.
4. If the hash is right but the page still looks old, it is the **browser** —
   hard-refresh; on iOS, close the tab and reopen.

Also fixed: `deck.html` was missing from `_VERSIONED_ASSETS`, so the injected
`?v=` cache-buster never changed when the deck changed. Harmless for the HTML
(served no-cache) but it made the stamp useless as a change signal.
