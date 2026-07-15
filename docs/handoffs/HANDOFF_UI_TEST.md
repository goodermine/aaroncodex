# Handoff: Phase 1 editor first-run test (for Daisy on the A9 Max)

Goal: verify the new browser editor runs on this machine, prove the safety
contracts against a real recording, then hand the open editor to Aaron for a
five-minute human click-around and collect his feedback.

Scope rules: do NOT edit code, tune parameters, or implement features on this
pass. The mute-region feature is queued separately — do not build it.

## 1. Update and sanity-check

```bash
cd aaroncodex && git pull    # branch: claude/voiceassist-plugin-planning-krhz0d
cd voxpolish
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e '.[ui,dev]'
python -m pytest tests/ -q
```

Expected: `81 passed`. If not, STOP and report the failure output verbatim.

## 2. Create a session on a real recording

Pick a clean vocal recording (studio take or clean stem — Aaron's preference)
or a talk recording. Then:

```bash
voxpolish ui /path/to/recording.wav --port 8765
```

Capture: analysis time printed before the server starts, and confirm the
session folder appeared next to the file (`<name>_session/`).

## 3. Safety-contract spot checks (while the server runs)

From another terminal:

```bash
# a) Original untouched: checksum the SOURCE file before and after everything.
md5sum /path/to/recording.wav          # Windows: certutil -hashfile <file> MD5

# b) API alive and consistent:
curl -s http://127.0.0.1:8765/api/session
curl -s http://127.0.0.1:8765/api/render

# c) Busy lock: trigger two renders back-to-back; the second should say
#    "a render is already running" (409) OR succeed if the first finished.
curl -s -X POST http://127.0.0.1:8765/api/render
curl -s -X POST http://127.0.0.1:8765/api/render
```

After the whole test, re-run the checksum from (a) — it must be identical.
Also confirm `history/` inside the session folder gains a `doc-XXXX.json`
snapshot after any edit is saved from the browser.

## 4. Hand to Aaron — the five-minute click-around

Have Aaron open http://127.0.0.1:8765 and try, in order:

1. Play the **Cleaned** audio; switch the dropdown to **Original**; A/B a few
   times. Does switching feel instant? Does the playhead track?
2. Click a red (gate), green (breath), or blue (sibilance) region — does the
   inspector show sensible times/dB? Press Delete, then **Render**, then
   re-listen to that spot. Did the edit do exactly what it said?
3. Click empty waveform to move the playhead; spacebar to play/pause.
4. Look at the yellow gain curve — does it visually match what he hears the
   leveling doing?

Collect his raw reactions, especially: what confused him in the first minute,
what he reached for that isn't there, and whether Render round-trip time feels
acceptable on a full-length recording.

## 5. Report back

1. Test-suite result and analysis/render timings.
2. Source-file checksum before vs after (must match).
3. Result of the busy-lock check and whether history snapshots appeared.
4. Any traceback or browser-console error, verbatim.
5. Aaron's click-around notes, unfiltered.
6. Browser and OS used.
