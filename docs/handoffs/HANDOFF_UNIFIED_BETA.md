# Handoff for Candi — the unified deck + beta fix round

Everything below is merged to `main`. This replaces the old two-server routine:
**one venv, one command, one address** now runs the whole suite.

## 1. One-time setup (replaces the two-venv setup)

```bash
cd aaroncodex
git pull                              # branch: main (or claude/voiceassist-plugin-planning-krhz0d — same code)
python3 -m venv .venv && source .venv/bin/activate     # ONE venv at the repo root
pip install -e voxpolish'[ui,pitch,separation]' -e voxsuite
```

If `git pull` complains about divergence: `git fetch origin && git reset --hard origin/main`.

## 2. Run it (every time)

```bash
source .venv/bin/activate
vox                                   # binds 0.0.0.0:8080 by default
```

Open **one** URL from any device on the tailnet:

- `http://a9max.<tailnet>.ts.net:8080/`

That's it — no more starting two servers, no more two Tailscale addresses.
**Hard-refresh once** (or use a private tab) so the new assets load.

## 3. What's new since your last pull

- **One deck, three modes.** The page opens on **Fused** (upload once → analysis
  report + polished vocal together). The **Polish / Analyze** tabs at the top-left
  now switch modes on the same address — the "downloads a JSON file" bug on
  Apple browsers is fixed.
- **Light / dark theme toggle** — sun/moon button top-right, next to Guide. It
  remembers your choice and follows the device setting on first visit. The
  scope stays dark in light mode on purpose (like a DAW display).
- **↻ New take** (top-right) appears once a job is running — clears the deck
  back to the start so you can record/upload another take without reloading.
- **Recorder Stop button fixed** — it sits right under the waveform now instead
  of being pushed off-screen.
- **Polish module sliders are real sliders** — press and drag the amount bars;
  the take re-renders. Scrubbing works across the whole song (transport bar
  and waveform), with a bigger touch-friendly seek handle.
- **Backing-track playback no longer stutters/jumps** on mobile (your fix,
  merged).

## 4. Just landed: a full audit + fix round (please re-test these)

We audited every engine↔UI path for beta readiness and fixed all 8 blockers:

1. **Progress bar** no longer snaps back to "Upload / 0%" halfway through an
   analysis — the chain now walks 01→07 properly. *(This was the "stuck on
   upload" weirdness.)*
2. **Fused playback works** — the play button lights up after a fused run and
   plays the polished vocal. (It literally never worked before outside demo.)
3. **Wrong-file uploads can't freeze the deck** — dropping a bad file now shows
   a clear red error + the New take button, on all three modes.
4. **Fast module toggling on Polish** now always renders your latest settings —
   before, quick flips could silently keep old audio while saying COMPLETE.
5. **If a job disappears** (server restarted mid-job, old link), the deck now
   says "job no longer on the server — start a new take" instead of silently
   going back to the upload screen.
6. **Queued jobs say "Queued"** instead of pretending nothing was submitted.
7. **Light theme is fully readable** — the results report and the Guide overlay
   were unreadable in light mode; both are fixed (check them in light!).
8. **The Clean module is real now** — dragging Clean actually changes the audio
   on re-render. On machines without the denoise engine installed it honestly
   shows "fixed at import" instead of a slider that does nothing.
9. **Fused runs warn you loudly** (amber banner on the score) if vocal isolation
   didn't run — so a full-song upload can't masquerade as a clean vocal score.
10. **Analysis timeouts can't wedge the server** any more (jobs used to get
    stuck "processing" forever and clog the queue).

## 5. What to test / how to report

- Record → Stop → Analyze on phone + desktop; then **↻ New take** and do a second
  one without reloading.
- Fused run end-to-end: upload once, wait for COMPLETE, **press play**, export both.
- Polish: drag the sliders (incl. Clean), toggle modules quickly, scrub the song.
- Flip the **theme** and open the **Guide** and a **results report** in light mode.
- Drop a `.txt` on purpose — you should get a red error + New take, never a
  frozen "Processing…".

When something misbehaves: say **which mode**, **what you did**, and the message
in the **Telemetry Log** (right rail) — those log lines are our breadcrumbs.

## 6. Known limits (real, not bugs to report)

- **One job at a time is the happy path.** Parallel uploads from two devices at
  once aren't protected yet (next fix round).
- **A server restart loses in-flight Fused jobs** (the deck will tell you now).
- The **classic pages** (old viewer/editor) aren't wired into the unified
  server — the deck is the UI.
- `pip install` must be **editable** (`-e`) from the repo, as in the setup above.
