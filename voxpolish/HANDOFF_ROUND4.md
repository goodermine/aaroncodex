# Handoff round 4: Download the rendered track (for Daisy)

Small, focused round. Aaron tested round 3 personally — upload, the Clean vs
Auto-Tune choice, and waveform panning all worked; he dialled the Tune amount
down slightly and re-rendered to a good result. The one gap he hit: no way to
save the track you like. This round adds a **Download** button.

Current commit: `b878591`. Baseline: **137 passed**.

Scope rules: do NOT edit code, tune DSP defaults, or build features. The
mute-region feature and the pitch lane remain queued.

## 1. Update and sanity-check

```bash
cd aaroncodex && git pull    # branch: claude/voiceassist-plugin-planning-krhz0d
cd voxpolish
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e '.[ui,dev,pitch]'
python -m pytest tests/ -q
```

Expected: **137 passed**. Any failure: STOP and report verbatim.

## 2. Download check

```bash
voxpolish ui            # upload a take, or open an existing session
```

Hard-refresh the browser (Ctrl+Shift+R). Then Aaron:

1. Process/open a take so a rendered vocal is playing. Click **Download** in the
   header (next to New upload / Render).
2. Confirm a WAV file downloads with a sensible name like
   `<yoursong>_voxpolish.wav`, and that it plays back correctly outside the app.
3. The real test of "download the one I like": change a setting (e.g. lower the
   **Tune** amount, or toggle a module off), press **Render**, wait for it to
   finish, then **Download** again. Confirm the new file reflects the change —
   i.e. Download gives the *latest* render, not the first one.
4. A/B the downloaded file against what you hear in the editor's Cleaned
   playback — they should match.

## 3. Report back

1. Test-suite count.
2. Download: filename you got, whether it played back fine, and whether a
   re-render then re-download reflected the change (step 3).
3. Any traceback (server terminal) or browser-console error, verbatim.
4. Still open for Aaron's call: whether to lower the editor's default Tune
   amount from 100% to ~80% so first renders come up gentler (a UI default, not
   a DSP change). Note his preference.
5. Which control Aaron reaches for next (region boundary dragging? pitch lane?
   gate-depth slider?) — decides the next build.

## Note

Download serves the current session's rendered `vocal_cleaned.wav` as an
attachment; the filename comes from the uploaded/CLI source name. It always
reflects the newest render (revision-tagged, no stale cache).
