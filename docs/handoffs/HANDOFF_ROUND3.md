# Handoff round 3: upload flow, Clean vs Auto-Tune choice, waveform panning

For Daisy. Covers the editor changes since round 2: a browser upload/landing
flow, a Clean vs Clean + Auto Tune choice, and fixed waveform navigation
(drag / scrollbar / zoom). This is the round that needs REAL BROWSER testing —
the interactions are client-side JS I could only asset-verify, not drive live.

Current commit: `ca3d7dd`. Baseline: **134 passed**.

Scope rules: do NOT edit code, tune DSP defaults, or build features on this
pass. The mute-region feature and the editor pitch lane remain queued — do not
build them.

## 1. Update and sanity-check

```bash
cd aaroncodex && git pull    # branch: claude/voiceassist-plugin-planning-krhz0d
cd voxpolish
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e '.[ui,dev,pitch]'
python -m pytest tests/ -q
```

Expected: **134 passed**. `python-multipart` is a new dependency of the `[ui]`
extra (for uploads); the install above pulls it. Any failure: STOP and report
verbatim.

## 2. Upload flow — start from the browser (feature 2)

```bash
voxpolish ui          # no file: opens on the upload screen
```

Hard-refresh the browser (Ctrl+Shift+R) if a session was open before. Aaron:

1. Upload a **WAV** by clicking the drop zone; then try **drag-and-drop** of an
   **MP3**. Both should be accepted.
2. Watch the progress bar/stage text while it processes; the page must stay
   responsive (not frozen).
3. On completion it should drop straight into the editor with the new take.
4. Try an invalid file (rename a .txt to .png or upload a non-audio file) and a
   truncated/corrupt audio file — confirm a clear error message appears on the
   upload screen, not a silent hang or a false success.
5. From inside a loaded session, click **New upload** in the header and confirm
   it returns to the upload screen.

Also confirm the CLI still works unchanged:
`voxpolish ui take.wav` opens that file directly.

## 3. Clean vs Clean + Auto Tune (feature 3)

On the upload screen, before **Start**, there is a plain-language choice:

1. Leave the default (**Clean + Auto Tune**), process a clean vocal, and confirm
   in the editor that the **Tune** module is ON (checkbox checked, key shown).
2. New upload of the same file, choose **Clean vocal**, and confirm Tune is OFF
   in the editor (Clean-only route applies no pitch correction).
3. In either session, toggle Tune and press **Render**; confirm the audio
   changes accordingly and the status line reports the tuning.

Reminder of the caveat (shown on the upload screen, keep it in mind): tuning is
reliable on clean vocals/stems; noisy or full-mix sources may keep artefacts.

## 4. Waveform navigation — the main thing to verify (feature 1)

This is the round-2 complaint: zoom worked but panning didn't. Acceptance test:

1. Open a **multi-minute** session (upload or CLI).
2. **Fit** the whole waveform.
3. **Ctrl+scroll** to zoom into a single phrase.
4. Pan at least **20 s left and right** using each method:
   - click-drag on the waveform,
   - normal mouse-wheel / trackpad scroll,
   - the horizontal scrollbar under the waveform (drag the thumb; click the track).
5. Start **playback**: the view should follow the playhead, but NOT fight you
   while you're manually panning (there's a ~2.5 s pause-follow after a pan).
6. Confirm click-to-select a region and Delete still work, and a plain click on
   empty space still seeks — dragging must not be mistaken for a click.
7. Confirm the layout is readable on Aaron's monitor.

## 5. Report back

1. Test-suite count.
2. Upload: which formats worked; error messages seen for invalid/corrupt files;
   whether the page stayed responsive; runtime to process a real take.
3. Tune choice: Tune state observed for each choice; toggle+re-render result.
4. Navigation: which pan methods worked, which felt wrong; playhead-follow vs
   manual-pan behaviour; any drag-vs-click confusion.
5. Any traceback (server terminal) or browser-console error, verbatim.
6. Which missing control Aaron reaches for next (region boundary dragging?
   pitch lane? gate-depth slider?) — that decides the next build.

## Notes for the tester

- Uploads and CLI sessions both live as folders under a workspace dir
  (`./voxpolish_workspace` by default, or the file's folder for CLI). Multiple
  uploads accumulate as separate sessions.
- A constant-tone/steady input that used to crash analysis is now handled; if
  any upload still errors, capture the job error text from the UI.
- Live browser drag/scroll/zoom was NOT verified upstream — your browser pass
  is the first real test of it. Report anything that feels off.
