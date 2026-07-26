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
