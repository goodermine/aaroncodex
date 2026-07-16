# VOX Suite — beta-readiness audit (engine ↔ UI)

**Date:** 2026-07-16 · **Scope:** all three engines (Analyze, Polish, Fused), the unified
server, the three command decks, and the shared front-end layer (telemetry, recorder,
report, theme, kit). Four parallel deep audits plus live runtime reproduction; every
blocker below was verified against source, and the ones marked *(runtime-confirmed)*
were reproduced against a running server.

**Verdict: NOT beta-ready yet.** 8 release-blocking defects, ~20 major. The good news:
the API↔UI *contracts* are largely sound (see "Verified correct" at the end), the test
suites are green (245 tests), and most blockers are small, well-localised fixes. The
issues cluster in three themes: **error paths that wedge or lie to the user**, **the new
light theme shipping unreadable surfaces**, and **fused-mode results that are wrong or
dead on real runs**.

---

## Blockers (must fix before beta)

**B1 — Analyze: any job that hits the 30-min timeout is stuck "processing" forever.**
`viewer/app.py:272-274`. `subprocess.run(text=True)` does *not* decode
`TimeoutExpired.stdout` (bytes, empirically confirmed on this Python 3.11) — the
`(exc.stdout or "") + (exc.stderr or "")` concat raises `TypeError`, which escapes the
handler before the manifest is marked failed. The job stays `processing` forever, the
deck polls WORKING indefinitely, and the job permanently consumes one of the 10
`MAX_ACTIVE_JOBS` slots until restart.

**B2 — Analyze UI: progress snaps back to "01 Upload / 0%" for the back half of every run.**
`vox-telemetry.js:131-135` vs `engine/pitch_track.py:639-742`. The engine emits
`preparing_audio, running_v2_analysis, finding_original, analysing_original,
aligning_comparison, building_report`; `VIEWER_STAGE_KEY` maps **none** of them (it
holds stale names). Unknown keys clamp to stage 0 — so after Track Pitch (~29%) the
chain re-highlights "Upload" and the bar drops to 0% for the longest part of the job.
(The intended `idx<0 → 1` fallback is dead code because `Math.max(0, findIndex)` runs
first.) This is almost certainly one of the reported "issues with the UI".

**B3 — Fused: garbage scores presented as a normal result when separation is unavailable.**
`engines.py:40-53` + `orchestrator.py:104-110`. If `audio-separator` is missing or
fails, `isolate` silently returns the *raw upload* as the vocal stem and the analyze
stage scores the full mix (bass+guitar+vocals). The deck shows a confident scorecard;
the only hint is a small "Isolation skipped" note. Standalone Analyze treats separation
failure as a job failure — Fused must not silently downgrade to wrong numbers.

**B4 — Fused UI: playback is dead on every real run** *(runtime-confirmed at source)*.
`deck.html:212` plays `p.download_url`; `RealEngines.polish` returns only
`download_path` (`engines.py:98`) — an absolute server path, never a URL. Only the
`?demo=1` fake ever set `download_url`, so the play button has never worked on a real
fused job. Fix: deck should use `/api/fused-jobs/{id}/download`.

**B5 — Polish UI: rapid module toggles silently produce stale audio labelled COMPLETE**
*(runtime-confirmed: PUT 200/200/200, POST render 200/409/409)*.
`deck.html saveAndRender` checks neither the PUT nor the POST status. Toggle 2 and 3
save the document but their render request is 409-rejected; the poller attaches to the
*running* render and reports COMPLETE — audio matches toggle 1 only, and nothing ever
schedules the missing render. Sub-case: a stale-revision PUT 409 leaves the client and
server documents permanently diverged. Fix: check statuses; on render-409 queue a
re-render when the current one completes.

**B6 — Upload rejection wedges the Polish and Fused decks** *(runtime-traced both sides)*.
- Polish `deck.html:354`: on 413/422 `j.id` is undefined → the deck polls
  `/api/uploads/undefined` (404) every 600 ms forever, stage stuck on "Processing…",
  and `#newBtn` never appears (apply() never runs). Hard reload is the only recovery.
- Fused `deck.html:283-285`: `setStage("Processing… isolating vocal")` fires *before*
  the fetch; a 415 leaves that overlay up forever with only a right-rail log line.

**B7 — Light theme: the Guide overlay and the results report are unreadable.**
- Guide: panel background hardcoded dark (`vox-kit.css:339`) while its text flips to
  light-theme ink — computed contrast **1.0:1** (invisible).
- Report (`vox-report.css`): sits outside the `.vox-scope` dark island and mixes
  hardcoded dark values with tokens — white panels with `#c4d3dd` text (~1.4:1) and
  dark cells with near-black text (~1.0:1). The entire analysis report is unreadable in
  light mode. The theme toggle shipped this week; light-mode users hit this immediately.

**B8 — Polish: the Clean (denoise) module is a placebo** *(runtime-confirmed:
byte-identical output after turning Clean off and re-rendering)*.
The UI writes `doc.denoise.amount/backend`, but denoise runs **once** at
`Session.create` and `render()` never reads `doc.denoise` (`session.py:181-204`). The
UI also writes `backend:"spectral"`, a backend that doesn't exist. Either wire denoise
into the render path or remove the slider (product decision).

---

## Major (fix before beta, or explicitly accept + document)

### Silent failure / lying UI
- **M1 — Dead job = silent vanish, on all decks** *(runtime-confirmed)*: a 404
  `{detail:...}` body maps to STANDBY with no error in all three adapters
  (`vox-telemetry.js`); STANDBY is non-terminal so the poller hits the dead job every
  2 s forever while `apply(STANDBY)` re-shows the upload intake. Triggers: server
  restart mid-fused-job (registry is memory-only, M4), expired analyze job (24 h TTL),
  bad `?job=` reattach, polish `/api/render` with no session. `poll()` needs an `r.ok`
  check and an ALERT path.
- **M2 — Analyze: `queued` renders as STANDBY** → with the single worker busy, a
  freshly uploaded job makes the deck revert to "Load your vocal take" as if nothing
  was submitted (`adaptViewer` + `apply()` else-branch).
- **M3 — Analyze: restart orphans `queued` jobs** — recovery flips `processing`→failed
  but never resubmits or fails `queued`; they sit 24 h eating `MAX_ACTIVE_JOBS` slots →
  new uploads get 503 `worker_unavailable`.
- **M4 — Fused: in-memory job registry** — restart mid-job loses all jobs (workdir
  artifacts survive but nothing reads them); no reattach exists for fused.
- **M5 — Polish: crash mid-`Session.create`** leaves a dir that passes `is_session`
  with no rendered audio → next boot the deck shows COMPLETE/READY, export 404s.

### Engine robustness
- **M6 — Analyze: timeout kills only the direct child** — `audio-separator`/`ffmpeg`
  grandchildren survive as orphans and keep consuming GPU while the next job starts
  (no process-group kill).
- **M7 — Analyze: `fetch_reference` doesn't wrap `TimeoutExpired`** — a yt-dlp stall
  fails the *whole job* instead of degrading to `reference: unavailable`.
- **M8 — Fused: thread-per-job, no cap** — two simultaneous uploads run two RoFormer
  separations on one GPU (Analyze has MAX_ACTIVE_JOBS=10 + 1 worker; Fused has nothing).
- **M9 — Fused: comparison is a no-op** — `build_v2_report(raw, meta.artist, None)`
  injects the artist as *recording conditions* and hardcodes `comparison=None`;
  `meta.song` is never used, though the intake promises "enables comparison".
- **M10 — Polish concurrency triple**: (a) `update_document` is check-then-act with no
  lock — concurrent PUTs can both 200 and silently lose one edit; (b) the upload worker
  unconditionally steals `ws.current_id` — a slower job hijacks the session another tab
  is editing; (c) `render_state` is one shared dict — switching sessions mid-render
  stamps A's done/error onto B's deck.
- **M11 — Memory DoS**: Polish `await file.read()` buffers the whole body *before* the
  500 MB check; Fused has **no** size cap or validation at all (202-accepts garbage).

### Unified server / packaging
- **M12 — Multi-instantiation hazards** *(runtime-confirmed)*: `VOX_PITCH_RUNTIME` is
  `setdefault` — a second `create_unified_app()` (or a pre-exported env var) sends
  analyze jobs to the wrong dir; each call re-executes the viewer module (leaked
  ThreadPoolExecutor, and `_cleanup(recover_interrupted=True)` stamps the previous
  instance's live jobs failed). Single long-running `vox` server is unaffected; tests
  and embeddings are not.
- **M13 — Non-editable `pip install voxsuite` breaks**: `engines.py parents[3]` and
  `unified.py parents[4]` resolve wrong from site-packages; no package-data means a
  wheel ships without `static/`. Works only as editable install from the monorepo —
  fine for beta if documented, broken for distribution.
- **M14 — Unified cache-busting hole**: all three shells are stamped with voxsuite's
  `_asset_version`, whose tuple omits `vox-report.js/.css` — a report-only design change
  keeps the same `?v=` and browsers serve the stale renderer.

### Front-end layer
- **M15 — Log XSS via filename**: `makeLog` injects unescaped `innerHTML`; all decks log
  raw `file.name` (`<img src=x onerror=…>.wav` executes). `escHtml` exists; use it.
- **M16 — Overlapping pollers**: every `pollStop = VOX.poll(...)` assignment except
  resetDeck's abandons the previous live poller — two interleaved loops flip the
  chain/LED/progress between jobs (drop a second file mid-job to trigger).
- **M17 — Light theme, scope island incomplete**: the `.vox-scope` dark-island override
  re-declares cyan/ink/surfaces but not violet/green/amber/red or their glows — WORKING
  LEDs, clip warnings, recorder errors and tray icons render muddy light-theme colors
  on the dark stage. Also `.vox-btn:hover{color:#fff}` → button labels vanish on hover
  in light mode (1.09:1).
- **M18 — Recorder teardown leaks**: "New take" wipes `#recMount` without stopping
  tracks/AudioContext — the mic-in-use indicator stays lit until reload; a failed
  device switch keeps the old stream hot on the idle screen and retries the dead
  device forever.

---

## Minor (worth fixing, not beta-gating)

- Polish upload progress pinned at the 60% fallback (`as_dict` has no `progress`);
  stage strings never surfaced.
- Analyze deck reads `res.file_name` — never sent → generic export filenames.
- Upload-rejection log fallback references out-of-scope `r.status` (latent
  ReferenceError; analyze chain also lacks a `.catch` for non-JSON bodies).
- `/api/audio/cleaned` has no Cache-Control and the deck re-sets the same URL after
  re-render → browser may play the previous render (add `?rev=`).
- Module-amount drag: no `pointercancel` → sticky drag on touch.
- Recorder: Stop is a no-op during the 3-2-1 count-in (no way to abort); `MAX_SECONDS`
  only enforced in rAF (background tab records past the cap); blob URLs revoked late;
  mic stays live during review.
- Guide overlay: no focus trap (Tab escapes the modal).
- Touch targets under 44 px: module toggle 34×18, theme button ~32, dlone/about-x 34,
  report timeline markers 10×30.
- Light-theme leftovers (list in kit audit): `.vox-step.is-done` 2.0:1, meter/gauge
  tracks stay dark in the light rail, `aria-pressed` button bg, brand glyph borders.
- `to_status` leaks absolute server paths + full report JSON every 500 ms tick.
- Fused export tray links `target=_blank` at endpoints that 404 as JSON post-restart
  (the Apple download-a-JSON failure again); Edit-doc item `href="#"` when absent.
- Unified: "Classic view →" links go to `/` (the Fused deck); polish classic editor
  isn't routed/servable on the unified origin.
- Fused: no TTL/cleanup for uploads/workdirs/registry (grows unbounded).
- Analyze: blocking ffprobe/TTL-rmtree inside async handler (event-loop stalls);
  MAX_ACTIVE_JOBS TOCTOU; TTL rmtree can race a live report read (500);
  report GET writes into the job dir (side-effectful read).
- `sys.path.insert` of `viewer/`+`engine/` is process-global — generic module names
  (`app`, `report_builder`) can shadow later imports.
- Polish `_write_doc` doc+meta writes not atomic as a pair; `_jobs` unbounded; upload
  stored twice; rejection message lists the wrong format set.
- Classic viewer/editor pages don't load the theme system (dark-only) — fine while
  classic is standalone-only, confusing if linked from a light deck.

---

## Verified correct (audit coverage — things that checked out)

- **Contracts**: `get_job` whitelist ↔ deck hydration; `VOXReport.render` inputs are all
  genuinely produced; `to_status` ↔ `adaptFused` field-for-field; `adaptPolish` status
  map; error payload shapes ↔ `alertText` (escaped) on all three APIs.
- **Route harvesting is safe today**: no sub-app middleware/exception
  handlers/lifespans/dependency-overrides exist to lose; the three `/api` namespaces
  are disjoint; page routes are not harvested; mode-hint pages don't leak into unified.
- **Security posture**: path traversal blocked on all static + job routes (uuid
  canonicalisation, whitelists, parent checks); analyze upload size enforced by
  streamed count (spoof-proof); manifest writes atomic under lock; report sanitiser
  strips absolute paths; vox-report.js escapes all server strings.
- **Shared assets**: all vendored copies byte-identical; sync.sh covers every asset the
  decks load; `.vox-stage > canvas` fix holds; theme head-snippet order prevents FOUC;
  localStorage guarded; `--vox-muted` passes AA on light surfaces.
- **Poller mechanics**: stops at terminal states, backs off correctly, survives network
  blips, `stop()` suppresses late events. (Its gap is `r.ok` — M1.)
- **Engines**: separation stem classification correct (incl. RoFormer naming); polish
  render single-flight lock releases in `finally`; atomic render replace; fused
  `run_fused` never raises out of a stage.
- **Suites**: 245 tests green (18 voxsuite / 149 voxpolish / 78 viewer) — but none of
  them exercise the failure paths above; the fix list should land with tests.

---

## Recommended fix order (smallest work → biggest user pain first)

1. **B2** stage-key map (one table in vox-telemetry.js) — instantly fixes the most
   visible "UI is broken" symptom.
2. **B4** fused playback URL (one line in deck.html → `/api/fused-jobs/{id}/download`).
3. **B1** timeout handler decode (two lines) + **M6** process-group kill.
4. **B6** upload-rejection handling in polish+fused decks (check `r.ok`, restore
   intake, show ALERT) + **M15** escape log messages.
5. **B5** saveAndRender: check statuses, queue re-render on 409 — plus **M16** stop the
   previous poller.
6. **M1/M2** poll `r.ok` + 404→ALERT ("job not found — start a new take"), map
   `queued` to WORKING("Queued…") instead of STANDBY.
7. **B7/M17** light-theme CSS pass on report + guide + scope island semantics.
8. **B3** fused isolate: fail the job (or hard on-deck warning) when separation
   unavailable; **M9** wire song/artist into the report call properly.
9. **B8** Clean module: product decision — wire denoise into render or remove slider.
10. Then the majors by subsystem (concurrency trio M10, caps M8/M11, unified
    instantiation M12, packaging M13/M14, recorder teardown M18).

Items 1–6 are a day-scale patch series; 7–9 are each self-contained.
