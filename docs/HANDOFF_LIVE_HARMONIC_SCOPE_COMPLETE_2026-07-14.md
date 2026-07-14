# Complete Handoff — VOXAI Live Harmonic Scope

**Date:** 2026-07-14 (Australia/Brisbane)

**Owner and approval authority:** Aaron

**Audience:** Candi/OpenClaw and the next coding or test agent

**Repository:** `rustwoodagent-ops/vox-cloud-alpha`

**Feature:** post-take, VoceVista-style spectral energy and harmonic guides in the pitch viewer

---

## 1. Executive status

The Live Harmonic Scope is implemented in an isolated worktree and has passed the current 70-test suite, inline-JavaScript syntax check, protected-path check and focused final Tailnet browser harness. The broader rendering, lifecycle and four-minute-fixture performance harnesses are also preserved in the repository. The five technical stop-ship blockers found by the final handoff audit have now been resolved and encoded as permanent regressions.

It is **not release-approved yet**. The post-fix physical-device rerun and Aaron's separate next-step approval remain outstanding; no automated emulation result is being represented as hardware evidence.

Before these final technical fixes, Aaron reported that the physical-device gates passed in his own testing:

- iPhone Safari through the Tailnet — passed
- Android Chrome through the Tailnet — passed

On 2026-07-14 Aaron authorized branch-only commits and pushes for review. He did **not** authorize a pull request, merge, deployment or publication.

The feature adds:

- server-generated constant-Q spectral energy for the isolated vocal;
- the same artifacts for a verified original when comparison is available;
- H1–H8 time-resolved relative-energy tracks;
- private, allowlisted API routes for descriptors, tiles and harmonic tracks;
- default-off `Energy` and `Harmonics` controls;
- a readable but subordinate spectral layer, physically positioned harmonic guides and live H1–H8 meters;
- lazy tile loading, bounded decoded-image caching and stale tile/window render cancellation;
- mobile transport, rotation and foreground-recovery protections;
- a performance watchdog that removes only spectral energy if rendering falls below budget.

The spectral system is **display only**. It does not feed a metric, score, diagnostic flag, prescription or coaching claim.

---

## 2. Stop-ship status

| Gate | Status | Evidence |
|---|---|---|
| Phase 0: exporter and ground truth | Pass | Known A3/overtone mapping, descriptor, silence/null and size tests pass |
| Phase 1: API and additive integration | Pass | Source/path allowlists, cleanup, caught-exception isolation and public-contract tests pass |
| Exporter hang isolation | Pass | Export runs last in a killable child with a five-minute default / ten-minute hard cap, yields to the outer monotonic deadline with a 30-second publication reserve, and a real sleeping child is killed while the core job completes with spectral unavailable |
| Binding score-equivalence regression | Pass | Repeated flag-off fixed-input result bytes and V2 artifact bytes match; flag-on differs only by `spectral`, while protected scoring returns the exact same technical-score object |
| Phase 2: main browser rendering | Pass locally | Lazy default-off behaviour, draw order, source-isolated spectral artifacts and tested failure paths pass |
| Original A/B with both new layers off | Pass automated | Original media clock and native contour remain authoritative for all four Energy/Harmonics combinations; singer mode retains aligned contour |
| Missing component-score bar | Pass | Missing score has unavailable text/ARIA and no fill geometry; measured zero retains `aria-valuenow=0` and a valid 0% fill |
| Large-phone landscape above 900 CSS px | Pass automated | Coarse/no-hover landscape rule passes at 1024×600 and 1280×720; a non-coarse 1024×600 baseline retains desktop transport |
| Phase 3: cache/mobile/performance | Pass in automated browser testing | 60 FPS on the four-minute throttled fixture; mobile emulation and lifecycle checks pass |
| Real iPhone Safari | Prior owner pass; post-fix rerun required | Open the fresh `:8877` build and repeat the comparison workflow |
| Real Android Chrome | Prior owner pass; post-fix rerun required | Open the fresh `:8877` build and repeat comparison plus >900 CSS px landscape where supported |
| GitHub review branch | Authorized | Commit and push branch only; no PR and no merge |

Do not describe the feature as released or merged until the affected physical-device checks pass and Aaron approves the next action.

### Resolved technical release blockers from the final handoff audit

1. **Bound optional exporter execution.** `pitch_track.py` now invokes `spectral_export.py` through a JSON-stdin child-process CLI with a dedicated deadline. Optional exports run only after scoring and comparison complete, and the viewer passes its monotonic outer deadline so the exporter always reserves 30 seconds for result publication and cleanup. Timeout/error cleanup removes final and `.tmp` artifacts. A deterministic sleeping child is proven started, killed and reaped while `result.json` still completes with public `spectral_export_failed` semantics. Malformed timeout configuration safely falls back to the default.
2. **Prove the binding non-interference gate.** A permanent fixed-input regression runs export-off twice and requires byte-identical normal result JSON and deterministic V2 artifact bytes. Export-on must add exactly `spectral`; removing that key reproduces the flag-off bytes. The test also calls the protected scorer read-only on the same measurements with and without additive spectral metadata and requires an exactly identical technical score.
3. **Resolve and test Original A/B with layers off.** Original A/B now always selects original media duration first and the native-original contour, independent of Energy/Harmonics. The durable browser harness proves 92-second media ownership, 90-second native fallback and 60-second singer ownership for every layer combination.
4. **Remove the missing-score zero substitution.** Shared `scoreState()` / `scoreMeter()` helpers encode unavailable values with no fill or numeric ARIA value while preserving a measured zero. Primary and comparison component bars use the same contract.
5. **Cover large-phone landscape.** Compact transport and above-scope A/B now use `max-width:900px` or landscape plus primary coarse/no-hover input. The durable CDP matrix covers 390×844, 844×390, 1024×600 touch, 1280×720 touch and a non-coarse desktop control.

All five technical rows pass automated verification. The changed A/B and responsive paths still require the honest post-fix physical-device rerun recorded above.

### Post-testing viewer refinements

Aaron's `:8877` review produced three additional viewer refinements, now encoded in the same branch:

1. **Version-neutral analysis wording.** Visible progress, signal-chain, component and full-report labels now say `Calibrated analysis` or `Calibrated VOXAI analysis`. The internal `running_v2_analysis` key remains unchanged for the backend/frontend stage contract.
2. **Honest low-confidence pitch.** A parallel `low_confidence` boolean array marks finite detected F0 below the reliable threshold. Unvoiced frames are explicitly masked to `NaN`, remain `null` in the public contour and never receive the flag. The scope renders only flagged detected pitch as a reduced-alpha dotted blue line, applies the same treatment under Accuracy, and uses a small dot only for an isolated uncertain detection.
3. **Readable optional layers.** The spectral raster uses a brighter, higher-contrast cyan treatment at guarded `0.38` display alpha. Harmonic guides use `0.50`/`0.36` alpha and `1.05` px width, remaining behind the fully opaque `2` px blue singer contour.

The deterministic Chrome gate proves a 10-frame uncertain section is dotted, a 10-frame breath section changes zero contour pixels, an isolated uncertain endpoint remains visible, Energy changes 402,838 pixels, and Harmonics changes 4,136 pixels. With both optional layers active, 881 of 951 blue-dominant pixels remain in the reliable singer regions (92.6%). No browser errors were recorded.

### Material changes made during implementation audit

The binding design was retained: server-side CQT, tiled PNGs, display-only data, default-off layers and no scoring dependency. Adversarial review added several protections beyond the seed plan:

- a per-generation `AbortController` and promise-identity guard after a stalled vocal fetch was found capable of blocking an Original A/B render;
- a full static-scope cache and pixel-bounded long contours after the first four-minute render path was too expensive;
- a three-second post-build watchdog grace period so cold decode is not mistaken for sustained playback failure;
- mobile Original A/B above the scope after the compact transport initially made A/B inaccessible;
- landscape sticky transport and expanded 44 px hitboxes after the first mobile audit exposed hidden or undersized controls;
- debounced same-size resize, page lifecycle snapshots and Media Session handlers after foreground/rotation testing exposed state ambiguity;
- a cancellable 1.5-second playback-start timeout after review found that a late `play()` promise could otherwise start audio after fallback was shown.

These changes reduced the identified failure modes without changing backend scores or the public meaning of any measurement.

---

## 3. Repository and worktree state

### Feature worktree

```text
/mnt/c/users/rustwood/documents/new project/vox-cloud-alpha-live-harmonic-scope
```

### Branch and base

```text
branch:        feature/live-harmonic-scope
feature base:  acef278796357243d568d06f7fe79a7248b7df07
base subject:  Handoff: live harmonic scope build brief for external agent (#14)
```

The branch is intentionally kept on this original base for review, without rebasing, so its feature diff remains clean.

At branch publication, `origin/main` had advanced by two commits:

```text
3b3695520e13d34cc1ed1666fa9e05b65554286a
data: re-analyse curated 50-reference pack with current engine

78fa4fa
Rubric v3 + 50-track calibration + docs (overview, manual, roster) (#15)
```

The initial implementation was published one feature commit ahead of `acef278`; the final stop-ship closure is a second scoped feature commit, and the post-testing viewer refinements are a third scoped commit on the same base. Current `origin/main` is two commits ahead of the base. Do **not** rebase this review branch. Eventual integration is expected to require a rebase onto current main and a merge conflict in `docs/metrics-methodology.md`, because both this feature and PR #15 edited it. Candi's protected reference-pack and rubric-v3 work must follow Aaron's normal approval and integration process.

The separate `main` worktree also currently contains nine modified generated analysis files under `backend/voxai-local-analysis/output/`. They are not part of this feature. Do not discard, stage or copy them into the feature worktree.

The historical `/tmp/voxai_reference_single_summary.json` 44-of-50 checkpoint is obsolete. Current `origin/main` already contains Candi's completed curated 50-track re-analysis (`3b36955`) and the rubric-v3 / 50-pack calibration merge (`78fa4fa`, PR #15). Do not resume the old temporary batch or copy its generated files into this branch.

### Current implementation inventory

Modified:

1. `backend/pitch-viewer/app.py`
2. `backend/pitch-viewer/static/index.html`
3. `backend/pitch-viewer/tests/test_api.py`
4. `backend/pitch-viewer/tests/test_pitch_track.py`
5. `backend/pitch-viewer/tests/test_ui_contract.py`
6. `backend/pitch-viewer/tests/ui_fixtures.json`
7. `backend/voxai-local-analysis/pitch_track.py`
8. `docs/metrics-methodology.md`

New in the feature commit:

9. `backend/voxai-local-analysis/spectral_export.py`
10. `backend/pitch-viewer/tests/test_spectral_export.py`
11. `docs/HANDOFF_LIVE_HARMONIC_SCOPE_COMPLETE_2026-07-14.md` — this handoff

Final stop-ship closure modifies the relevant viewer/exporter/test/handoff files above and adds these durable browser assets:

12. `backend/pitch-viewer/tests/browser/README.md`
13. `backend/pitch-viewer/tests/browser/stop_ship_browser_check.mjs`
14. `backend/pitch-viewer/tests/browser/phase-gates/README.md`
15. `backend/pitch-viewer/tests/browser/phase-gates/phase2_rendering_check.mjs`
16. `backend/pitch-viewer/tests/browser/phase-gates/phase3_mobile_lifecycle_check.mjs`
17. `backend/pitch-viewer/tests/browser/phase-gates/phase3_performance_check.mjs`

Before this handoff, the tracked implementation diff was 848 insertions and 26 deletions; the two new code/test files added another 388 lines.

No dependency manifest was changed. `spectral_export.py` imports Pillow; the environment has Pillow 12.3.0, and the existing required `matplotlib>=3.7.0` dependency itself requires `pillow>=9`.

---

## 4. System architecture

```text
User upload
  -> existing stem separation
  -> isolated vocal + instrumental playback files
  -> existing pitch tracking and VOXAI V2 analysis
  -> optional viewer-only spectral exporter
       -> spectral/vocals/descriptor.json
       -> spectral/vocals/harmonic-tracks.json
       -> spectral/vocals/tile-NNN.png
  -> optional verified-original analysis
       -> spectral/original/... equivalent artifacts
  -> completed job result with public spectral metadata
  -> private FastAPI spectral endpoints
  -> browser fetches only the active source and only after user opt-in
  -> offscreen/static scope render + dynamic playhead
```

The normal analysis and score are produced before the optional display exporter runs. The exporter runs in a separately bounded child process and caps itself to the remaining outer deadline with a 30-second publication reserve, so exceptions and hangs degrade to an unavailable visual layer without changing the score or report or exhausting the global analysis timeout.

### Candi/OpenClaw isolation

`pitch_track.py` now accepts `--export-spectral`, but the corresponding Python argument defaults to `False`. The pitch viewer explicitly supplies the flag. Candi's direct engine workflow does not, so it receives the existing result shape with no `spectral` key.

`analyse_song.py` does not import the exporter and was not modified.

---

## 5. Engine-side spectral artifacts

The new module is `backend/voxai-local-analysis/spectral_export.py`.

### Constant-Q image

- mono audio at 44,100 Hz;
- hop length 2,048 samples;
- 21.533203125 frames per second;
- three bins per semitone / 36 bins per octave;
- visible C2–C7 range, with C7 exclusive;
- 180 visible image rows, stored high-frequency-first;
- an internal 289-bin CQT so upper H1–H8 samples remain available without extending the browser image;
- magnitude expressed relative to the strongest value in the visible C2–C7 CQT image across the take;
- clipped to −80 to 0 dB and mapped linearly to 8-bit grayscale;
- all-silent input maps to black, not false energy;
- sequential PNG tiles no wider than 2,048 frames;
- atomic temporary-directory generation and cleanup on failure.

The exact mappings are included in the descriptor:

```text
row = n_bins - 1 - (midi - midi_lo) * bins_per_semitone
frame = (time_seconds - t0) * fps
```

### Harmonic tracks

- H1 through H8;
- sampled at `k × measured F0`;
- a narrow three-CQT-bin peak is used around each target;
- output cadence follows the measured pitch contour, normally 10 Hz;
- each voiced frame is relative to its strongest available harmonic, where 0 dB is strongest;
- unvoiced, silent and out-of-range values remain JSON `null`;
- units are `db_relative_to_strongest_available_harmonic_per_frame`.

These values are useful for visual inspection but are not calibrated sound-pressure levels.

### Internal result state

When enabled, `pitch_track.py` can add:

```json
{
  "spectral": {
    "version": "voxai_spectral_v1",
    "status": "ready | partial | unavailable",
    "sources": {
      "vocals": {
        "status": "ready",
        "descriptor_file": "spectral/vocals/descriptor.json",
        "harmonic_tracks_file": "spectral/vocals/harmonic-tracks.json",
        "tile_count": 2,
        "artifact_bytes": 527801
      }
    }
  }
}
```

An exporter exception produces:

```json
{"status": "unavailable", "reason": "spectral_export_failed"}
```

Private exception details are written only to `spectral-<source>.log` inside the job directory when possible. A failure to write that private log is also isolated.

The original-source export occurs before its temporary analysis WAV is deleted.

---

## 6. FastAPI and public data contract

The pitch-viewer worker now appends `--export-spectral` to viewer analysis jobs.

New routes:

```text
GET /api/pitch-jobs/{job_id}/spectral/{source}/descriptor
GET /api/pitch-jobs/{job_id}/spectral/{source}/harmonics
GET /api/pitch-jobs/{job_id}/spectral/{source}/tiles/{tile_index}
```

Protections:

- source allowlist is exactly `vocals` or `original`;
- existing UUID/job-directory validation is reused;
- the job must be complete and the requested source must be ready;
- descriptor schema, source, display-only flag and harmonic filename are validated;
- tile indices and sequential `tile-NNN.png` filenames are validated;
- callers never supply a filesystem filename;
- JSON responses expose allowlisted fields only;
- private relative filenames are replaced with same-origin URLs;
- responses use `Cache-Control: private, max-age=86400, immutable`;
- responses use `X-Content-Type-Options: nosniff`;
- existing whole-job retention cleanup removes the spectral tree with the job.

The public job payload exposes only status, reason, tile count, artifact bytes and ready URLs. A currently verified real single-track job returns:

```json
{
  "version": "voxai_spectral_v1",
  "status": "ready",
  "sources": {
    "vocals": {
      "status": "ready",
      "tile_count": 2,
      "artifact_bytes": 527801,
      "descriptor_url": "/api/pitch-jobs/ef36dff3-7b33-4208-8fdc-4caf40e9d81b/spectral/vocals/descriptor",
      "harmonic_tracks_url": "/api/pitch-jobs/ef36dff3-7b33-4208-8fdc-4caf40e9d81b/spectral/vocals/harmonics"
    }
  }
}
```

---

## 7. Browser implementation

All browser work remains in `backend/pitch-viewer/static/index.html`; no frontend framework or external decorative asset was added.

### Controls and presentation

- `Energy` toggles the readable, subordinate spectral raster.
- `Harmonics` toggles physical H2–H8 guide curves and the live H1–H8 meter rack.
- Both toggles are off by default.
- Legacy jobs without artifacts show `Re-analyse to enable` and make no spectral request.
- H1–H8 unavailable values display `—` and are not converted to zero. Component-score meters likewise render unavailable text and no fill geometry, while a measured zero remains a valid 0% measurement.
- The legend and status copy explicitly label spectral energy as display only.
- A mobile `Original A/B` control sits above the scope instead of crowding the sticky transport.

Approved existing behaviour was preserved:

- singer contour remains blue;
- the Accuracy variance overlay remains narrow/subtle near correct notes and strongly red only for large errors;
- original contour remains orange;
- single-track mode still accepts optional song title and original artist/composer metadata;
- Background on/off, zoom, reset, Follow and native audio fallback remain available;
- Original A/B remains exclusive rather than mixing original, vocal and instrumental together.

### Lazy loading and validation

`show()` and spectral configuration inspect metadata only. They do not fetch a descriptor, harmonic JSON or tile. The first request occurs after the corresponding user gesture.

Browser validation enforces:

- same-origin artifact URLs;
- schema version and display-only status;
- finite rates, bounds and dimensions;
- contiguous tile frames;
- a 2,048-frame limit per tile;
- bounded total frames, tile counts and canvas dimensions;
- valid H1–H8 arrays and nullable numeric values.

An optional-layer failure disables only that layer and leaves pitch, playback and native controls working.

### Physical draw order

The static scene is rendered in this exact order:

1. spectral energy;
2. equal-tempered note lanes;
3. H2–H8 guide curves;
4. singer's blue F0 contour;
5. narrow Accuracy overlay;
6. original contour;
7. dynamic playhead.

Guide offsets use the unrounded physical formula:

```text
12 × log2(k) semitones
```

Non-octave harmonics therefore sit between equal-tempered note lanes when physics requires it.

### Rendering and cache protections

- detached offscreen canvases;
- approximately three view-widths of overscan;
- only tiles intersecting the requested window are decoded;
- preferred `ImageBitmap` decode with Safari-compatible `Image` fallback;
- insertion/LRU cache capped at eight images and 32 MiB decoded;
- offscreen raster capped at 8,192 px and 3,000,000 pixels;
- source-aware generation tokens;
- `AbortController` cancellation on source/view invalidation;
- promise-identity checks so an old build cannot clear a newer one;
- 15-second request/build timeout;
- no vocal-artifact fallback while Original A/B is active;
- a static full-scope canvas so normal playback redraws the cached scene plus playhead;
- long full-take contours reduced to roughly one point per horizontal pixel while null gaps and zoomed detail remain intact.

Tile/window builds are cancelled on invalidation. Descriptor and harmonic JSON requests use independent 15-second timeout controllers and may finish after a source change; source checks prevent them from being rendered as the active source, but those JSON requests are not aborted solely because A/B changes.

### Performance watchdog

After a three-second cold-render grace period, the viewer measures frames only while playback, the chart and spectral energy are active. Two consecutive two-second windows below 45 FPS disable spectral energy and show:

```text
Spectral energy was disabled to protect smooth playback. Harmonic guides remain available.
```

Pitch, harmonic guides, audio and native controls remain usable. Energy can be enabled again manually.

---

## 8. Audio, A/B and mobile lifecycle

- Vocal audio is the normal master clock.
- Instrumental playback follows vocal play, seek and rate and is corrected when drift exceeds 120 ms.
- Background controls instrumental inclusion only.
- Original A/B makes original audio the exclusive clock and pauses vocal/instrumental.
- Returning from Original A/B restores vocal/background playback at the matched position.
- The active source controls the playback clock, current-pitch readout, optional spectral raster, harmonic guides and H1–H8 tracks. The base singer contour remains visible by design, and the optional original contour can remain as a comparison overlay. Spectral artifacts themselves are never mixed between sources.
- Native vocal controls remain as a fallback.

Original A/B duration and contour ownership is independent of Energy/Harmonics. Original media duration is authoritative; native-contour duration and then descriptor duration are fallbacks. Singer mode retains singer duration and the aligned comparison contour.

Mobile changes verified at phone widths and coarse-pointer landscape widths above 900 CSS px:

- portrait and landscape use a fixed minimal transport containing play/pause, time, seek and Background only;
- all tested interactive hitboxes are at least 44 × 44 CSS pixels;
- scope controls use a contained horizontal rail rather than causing page overflow;
- the A/B listening control remains available above the scope;
- resize and orientation events are debounced and same-size resize is idempotent;
- `visibilitychange`, `pagehide`, `pageshow` and orientation settling preserve source, position, rate, Background and intended play state;
- a rejected resume shows `Tap play to resume after returning to VOXAI.`;
- startup is bounded at 1.5 seconds, late starts are paused and failed playback intent is cleared;
- Media Session play/pause handlers preserve explicit lock-screen/headset decisions where supported.

The compact media rule now also selects coarse/no-hover landscape devices. Automated checks pass at 1024 × 600 and 1280 × 720, while a non-coarse 1024 × 600 control remains on the desktop transport. Headless CDP proves the coarse/non-coarse branch; it is not physical pointer-capability evidence.

If a browser lacks Media Session support, it may not be possible to distinguish every hidden user pause from browser-initiated suspension. This is why physical testing remains mandatory; Aaron's earlier iPhone Safari and Android Chrome passes predate the final A/B and responsive fixes.

---

## 9. Verification evidence

### Automated suite

Latest isolated-worktree audit run on 2026-07-14:

```text
Ran 70 tests in 35.877s
OK
```

Breakdown:

| Suite | Tests |
|---|---:|
| API | 17 |
| Pitch bridge | 21 |
| Report builder | 3 |
| Spectral ground truth | 6 |
| UI contract | 23 |

Only non-blocking `audioread` future deprecation warnings for `aifc`, `audioop` and `sunau` appeared.

Feature coverage includes:

- known A3 and exact overtone geometry;
- descriptor/image row and time mappings;
- silent-image and nullable harmonic behaviour;
- four-minute artifact size;
- exporter failure and real-child hang isolation, including outer-deadline reservation, malformed configuration, cleanup and log-write failure;
- fixed-input result-byte, V2-artifact and protected technical-score equivalence;
- successful child-process exporter CLI contract;
- deferred original export timing and best-effort temporary-audio cleanup;
- source/path allowlisting and traversal rejection;
- cleanup and public response sanitization;
- lazy default-off browser behaviour;
- layer order and unrounded harmonic offsets;
- A/B spectral-source isolation and stale tile/window-build abortion;
- cache limits and oldest-entry closure;
- layer-independent Original A/B time/contour ownership;
- missing-score versus measured-zero meter semantics;
- mobile hitboxes, >900 CSS px coarse landscape transport and lifecycle;
- watchdog pass/fail thresholds.

The deterministic four-minute high-entropy format test produced:

```text
5,168 frames
3 PNG tiles
1,059,879 bytes / 1.011 MiB total artifacts
```

This is below the 3 MiB stop-ship budget.

### Real take

Verified single-track fixture:

```text
duration:        146.453 seconds
pitch points:    1,402
spectral tiles:  2
artifact bytes:  527,801 / approximately 0.503 MiB
```

The image and harmonic guides were visually cross-checked over this real contour.

### Four-minute throttled browser profile

Environment:

```text
Chrome 150.0.7871.46, headless
host: AMD Ryzen AI 9 HX 370, 12 cores / 24 threads
viewport: 390 × 844
device scale factor: 3
CPU throttle: 4×
fixture duration: exactly 240 seconds
pitch points: 2,400
tile widths: 2,048 + 2,048 + 1,184
profile windows: three 8-second playback samples across the 240-second fixture
```

Results:

| Playback state | FPS | p95 frame | Max frame | Tasks >100 ms |
|---|---:|---:|---:|---:|
| Vocal + Energy | 60.002 | 16.8 ms | 16.8 ms | 0 |
| Vocal + all layers | 60.002 | 16.7 ms | 16.8 ms | 0 |
| Original A/B + all layers | 60.002 | 16.8 ms | 16.8 ms | 0 |

Additional results:

- no spectral requests before user opt-in;
- Energy ready in approximately 93 ms;
- six decoded vocal/original tiles used 7,603,200 bytes, below eight entries/32 MiB;
- deliberately introduced 500 ms instrumental drift recovered to 78 ms;
- return to vocal mode produced 93 ms drift, inside the 120 ms contract;
- background recovery produced 0 ms drift;
- all current and maximum watchdog strike counts remained zero;
- the Long Tasks observer was supported for every profile;
- no console errors or network failures.

### Responsive and lifecycle checks

- same-host headless-browser first contentful paint through the machine's own Tailnet address: approximately 52 ms; this is not a remote-phone Tailnet latency measurement;
- 390 × 844 portrait: zero horizontal page overflow and no undersized targets;
- 844 × 390 landscape: fixed transport remained in the viewport;
- 1,024 × 768 and 1,440 × 900: spectral layer rendered with no page overflow;
- rotation preserved playback, Energy, Harmonics and the spectral window;
- same-size resize did not increment the spectral generation or rebuild the window;
- system interruption resumed with rate and Background preserved;
- deliberate user pause remained paused;
- external/lock-screen pause policy cleared the saved resume state;
- rejected autoplay displayed the exact fallback message;
- a delayed start was cancelled and remained paused;
- no console or network errors.

Current screenshot evidence is temporary and will disappear with `/tmp` cleanup:

```text
/tmp/voxai-phase3-mobile-portrait.png
/tmp/voxai-phase3-mobile-landscape.png
/tmp/voxai-phase3-tablet-1024x768.png
/tmp/voxai-phase3-desktop-1440x900.png
/tmp/voxai-phase3-four-minute-performance.png
/tmp/voxai-live-harmonic-phase2.png
/tmp/voxai-post-refinement-stop-ship/refinement-scope-canvas.png
/tmp/voxai-post-refinement-full/stop-ship-browser-result.json
/tmp/voxai-post-refinement-performance/phase3-performance-result.json
```

The current aggregate performance result is saved as JSON with `gate: "pass"` and an empty `gateFailures` list. The durable harness now fails on FPS, p95/max frame time, unsupported Long Tasks observation, tasks above 100 ms, transient or final watchdog strikes, layer removal, source errors, drift above 120 ms, console errors and network failures. `/tmp` evidence remains disposable and can be regenerated from the committed harnesses.

### Static integrity

- inline JavaScript parses with Node;
- the tracked implementation diff passes `git diff --check`;
- the three newly added deliverables were separately checked for trailing whitespace before the feature commit;
- protected-path status, working-tree diff and staged diff are empty;
- no runtime or browser error overlay was observed.

Protected paths intentionally unchanged:

```text
backend/voxai-local-analysis/analyse_song.py
backend/voxai-local-analysis/calibration/
backend/voxai-local-analysis/knowledge/
openclaw-data/vox-coach/knowledge/
```

Recorded hashes for the isolated worktree:

```text
analyse_song.py:
7cdc2cd5628890807ad72fff17641a40bcb8a39df4c71f8a76a55e988c485d08

calibration/pro_reference.json:
e1ac6c66595f82ecb4b8f458029898d92752e5dbca798d9747bab5e44e9a1cbd

knowledge/prescription_map.json:
229f9a5cd00b51d7d5c99a158abc2a925a904f40d469f53314ba0ae52e0fe6cc

VOXAI_Knowledge_Core.txt:
2ec9747673ac499ce5e078419ce5f20a663eab82e860aa598e870f9eeebd2292

VOXAI_Scientific_Exercise_Library.txt:
6562ad35c2f04768f399f82587efce88718c20d23cf6c6deb1a235e6b39f31f7
```

---

## 10. Reproducing repository checks

Run from the isolated worktree unless noted otherwise.

### Full suite

```bash
cd "/mnt/c/users/rustwood/documents/new project/vox-cloud-alpha-live-harmonic-scope/backend/pitch-viewer"
"/mnt/c/users/rustwood/documents/new project/vox-cloud-alpha/backend/pitch-viewer/.venv/bin/python" \
  -m unittest discover -s tests -v
```

### Embedded JavaScript syntax

```bash
cd "/mnt/c/users/rustwood/documents/new project/vox-cloud-alpha-live-harmonic-scope"
set -o pipefail
"/mnt/c/users/rustwood/documents/new project/vox-cloud-alpha/backend/pitch-viewer/.venv/bin/python" - <<'PY' | node --check -
from pathlib import Path
import re

html = Path("backend/pitch-viewer/static/index.html").read_text(encoding="utf-8")
scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S)
if not scripts:
    raise SystemExit("no inline scripts found")
print("\n".join(scripts))
PY
```

### Diff and protected files

```bash
cd "/mnt/c/users/rustwood/documents/new project/vox-cloud-alpha-live-harmonic-scope"
git diff --check
git status --short --branch
git rev-list --left-right --count HEAD...origin/main
git log --oneline HEAD..origin/main

git status --short -- \
  backend/voxai-local-analysis/analyse_song.py \
  backend/voxai-local-analysis/calibration \
  backend/voxai-local-analysis/knowledge \
  openclaw-data/vox-coach/knowledge

git diff --exit-code -- \
  backend/voxai-local-analysis/analyse_song.py \
  backend/voxai-local-analysis/calibration \
  backend/voxai-local-analysis/knowledge \
  openclaw-data/vox-coach/knowledge

git diff --cached --exit-code -- \
  backend/voxai-local-analysis/analyse_song.py \
  backend/voxai-local-analysis/calibration \
  backend/voxai-local-analysis/knowledge \
  openclaw-data/vox-coach/knowledge
```

Before the initial feature commit, ordinary `git diff --check` did not inspect the three newly added files. The following explicit check was used:

```bash
python3 - <<'PY'
from pathlib import Path

paths = [
    Path("backend/voxai-local-analysis/spectral_export.py"),
    Path("backend/pitch-viewer/tests/test_spectral_export.py"),
    Path("docs/HANDOFF_LIVE_HARMONIC_SCOPE_COMPLETE_2026-07-14.md"),
]
bad = []
for path in paths:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.rstrip(" \t") != line:
            bad.append(f"{path}:{number}")
if bad:
    raise SystemExit("trailing whitespace: " + ", ".join(bad))
print("new-file whitespace check: OK")
PY
```

The focused stop-ship browser harness is now a repository deliverable:

```text
backend/pitch-viewer/tests/browser/stop_ship_browser_check.mjs
backend/pitch-viewer/tests/browser/README.md
```

It has no npm dependency and parameterizes `APP_URL`, `CDP_URL`, `CHECKS` and `EVIDENCE_DIR`. It consolidates the final A/B, missing-score and responsive-layout regressions. Current harness SHA-256:

```text
fa6c2045f46cac6720531cd4ae78104fb558bf19ab5e7854413c59c1f5341500
```

The material broader harnesses are also preserved rather than left in `/tmp`:

```text
backend/pitch-viewer/tests/browser/phase-gates/phase2_rendering_check.mjs
backend/pitch-viewer/tests/browser/phase-gates/phase3_mobile_lifecycle_check.mjs
backend/pitch-viewer/tests/browser/phase-gates/phase3_performance_check.mjs
backend/pitch-viewer/tests/browser/phase-gates/README.md
```

They parameterize `APP_URL`, `CDP_URL`, optional `EVIDENCE_DIR` and, for real-media checks, required `JOB_ID`. Their SHA-256 values are:

```text
e6ce90025de76bc878e18dfebc17fcec5645d3f74a09e35324985804ad7f525e  phase2_rendering_check.mjs
5fd6c8bdf70f618f16201a2bc73d28811214d36b9d6c875498c71109151bf095  phase3_mobile_lifecycle_check.mjs
f54f168b27f9407f98ec9f047b6c4e058b728ff99893be069314e0a2e7568975  phase3_performance_check.mjs
df8161f4c9a29d88db7eb2b4b2643ce3e3435e217f27827e12e5e55d688c4fa6  phase-gates/README.md
```

The preserved Phase 2 deterministic harness passed against `:8877`. The mobile/lifecycle and four-minute performance harnesses were verified mechanically against the existing completed job on `:8876`; those runs prove the durable harnesses operate but do not replace the pending post-fix physical-device comparison run on `:8877`.

While the files still exist, launch the same isolated browser profile if no CDP browser is already listening:

```bash
/snap/bin/chromium \
  --headless=new \
  --no-sandbox \
  --remote-debugging-port=9225 \
  --user-data-dir=/tmp/voxai-phase3-final-chrome-profile \
  --no-first-run \
  --disable-default-apps \
  --autoplay-policy=no-user-gesture-required \
  --window-size=1440,900 \
  --noerrdialogs \
  --ozone-platform=headless \
  --use-angle=swiftshader-webgl \
  http://100.103.207.54:8877/
```

Then, in separate runs so CPU-heavy checks do not contaminate each other:

```bash
APP_URL=http://100.103.207.54:8877/ \
CDP_URL=http://127.0.0.1:9225 \
EVIDENCE_DIR=/tmp/voxai-stop-ship-final-publish \
node backend/pitch-viewer/tests/browser/stop_ship_browser_check.mjs
```

The final all-check result JSON and screenshot were written to `/tmp/voxai-stop-ship-final-publish/`; their SHA-256 values were `c00536b0abbc68b76ee69d17b55ecfe83779dfddc863adbac42e16bfb05895c6` and `2ecd01f41706feb417dcf83e21d0713f8609976a996bcc704ccf1118ad9bc68a` respectively.

---

## 11. Current Tailnet test server

The corrected isolated build was verified live on 2026-07-14 from a fresh current-source process.

```text
MagicDNS:  http://a9max.tail8e8c02.ts.net:8877/
Direct IP: http://100.103.207.54:8877/
```

Both addresses returned HTTP 200 and byte-identical HTML.

Current process characteristics:

```text
working directory:
/mnt/c/users/rustwood/documents/new project/vox-cloud-alpha-live-harmonic-scope/backend/pitch-viewer

command:
/mnt/c/users/rustwood/documents/new project/vox-cloud-alpha/backend/pitch-viewer/.venv/bin/python \
  -m uvicorn app:app --host 100.103.207.54 --port 8877 --log-level info

runtime:
backend/pitch-viewer/runtime (isolated worktree default)
```

The process was restarted from the current source at 2026-07-14 11:58:31 AEST. Served HTML was SHA-256 byte-identical to the isolated worktree (`bc870d9484cae742b35a5ead71ad9fc31335f23e7ea2953bef55c84da9a3ab93`) during the final browser run, and `/api/health` reported all core tools available.

This is a temporary Tailnet-only test process, not a deployment or persistent service. It does not change existing routes on ports 443, 8443, 8765 or 8766. Do not use the older `:8443` build to validate this feature.

At audit time, Tailscale Serve on `:8443` still proxied to `127.0.0.1:8767` and served the older main-worktree build.

Health checks:

```bash
curl --max-time 10 -fsS -o /dev/null -w 'magic_dns %{http_code}\n' \
  http://a9max.tail8e8c02.ts.net:8877/
curl --max-time 10 -fsS -o /dev/null -w 'direct_ip %{http_code}\n' \
  http://100.103.207.54:8877/
curl --max-time 10 -fsS http://100.103.207.54:8877/api/health
ps -ef | rg "uvicorn app:app.*8877"
```

Do not stop the `:8877` server unannounced while Aaron may be performing the post-fix hardware rerun. It is separate from and does not disturb the existing `:8876` process.

The previous real job remains under the older `:8876` temporary runtime with ID:

```text
ef36dff3-7b33-4208-8fdc-4caf40e9d81b
```

It is not final evidence for `:8877`. There is no user-facing completed-job deep link, so the post-fix physical-device test must upload/analyse a comparison take through the fresh page. Stem separation is CPU-heavy and may take several minutes.

---

## 12. Physical-device gate — prior pass, post-fix rerun pending

Aaron reported that iPhone Safari and Android Chrome passed before the five final technical fixes. Because the fixes changed A/B source ownership and coarse-pointer landscape layout, the affected checklist must now be repeated on the fresh `:8877` build. No automated CDP result should be substituted for this hardware evidence.

Connect each device to Tailscale and open:

```text
http://a9max.tail8e8c02.ts.net:8877/
```

Use the direct IP URL if MagicDNS fails.

Record device model, OS version, browser version, pass/fail and a screenshot for any failure.

### Required checks on iPhone Safari and Android Chrome

1. Confirm the page loads without an error overlay or horizontal page scroll.
2. Run a short single-track analysis.
3. Confirm Energy and Harmonics begin off.
4. Enable Energy, then Harmonics; verify the blue pitch line stays dominant.
5. Play, pause, seek, zoom, drag and use Follow.
6. Toggle Background off and on; confirm only the backing track changes.
7. Rotate while playing; confirm time, rate, Background and layer state survive.
8. On any landscape viewport wider than 900 CSS px, confirm the intended compact transport remains accessible and Original A/B is still available above the scope.
9. Lock the screen for 15 seconds and return; browser-suspended playback should recover or show the tap-to-resume message.
10. Pause explicitly from lock-screen/headset controls; returning should remain paused where Media Session is supported.
11. Confirm the sticky transport clears Safari/Chrome browser chrome and the home indicator.
12. Run a comparison analysis with a verified original.
13. Confirm mobile `Original A/B` is available above the scope.
14. Enter A/B and confirm original is the only audible source and original artifacts are shown.
15. Return to vocal and confirm vocal/background resume without obvious drift.
16. Confirm native vocal playback remains usable if a custom or secondary playback action fails.

Stop ship for:

- audible drift above 120 ms;
- simultaneous original, vocal and instrumental playback;
- blocked or obscured controls;
- Energy/Harmonics fetching before opt-in;
- wrong-source spectral artifacts;
- hidden warnings or fallback messages;
- horizontal page overflow;
- recurring stutter or watchdog removal during normal playback;
- failure to recover from foreground/rotation;
- a user-paused track resuming unexpectedly.

---

## 13. Known limitations and honest interpretation

- This is post-take analysis, not live microphone tracking.
- Legacy jobs must be re-analysed to obtain spectral artifacts.
- The visible range is C2–C7.
- Intensity is relative within a take, not calibrated SPL.
- CQT window support can show faint energy just before a sharp onset.
- Stem-separation artifacts can create false upper-band energy.
- Harmonic guides show physical `k × F0` positions; they are not proof that every nearby bright band is healthy or intentional resonance.
- The 1.5-second media-start path passed Aaron's phone testing, but remains a documented risk on unusually slow startup paths.
- Browsers without Media Session support cannot perfectly distinguish every hidden user pause from automatic suspension.
- Older Canvas implementations may show neutral grayscale rather than the cyan tint; geometry and data remain valid.
- The Tailnet server, runtime data and screenshots are temporary; the consolidated browser harness is now durable in the repository.
- Aaron's earlier iPhone Safari and Android Chrome passes predate the final A/B and large-landscape fixes; the affected hardware checks remain pending on `:8877`.

---

## 14. Safe continuation runbook

1. Continue only in the isolated feature worktree.
2. Keep the durable browser harness under `backend/pitch-viewer/tests/browser/`; `/tmp` evidence may be regenerated.
3. Treat the five technical blockers as closed only while the 70-test suite, JavaScript syntax, browser harnesses and protected-path checks remain green.
4. Do not touch scoring, calibration, prescription or coaching knowledge.
5. Use the fresh `:8877` Tailnet build for the affected iPhone Safari and Android Chrome hardware rerun.
6. Test comparison mode with Energy/Harmonics both off and on, Original A/B source changes, seeking, Background, foreground return and rotation.
7. On a large phone/tablet landscape wider than 900 CSS px, confirm the fixed compact transport and above-scope Original A/B remain usable.
8. If a regression fails, capture the exact device/browser, reproduction steps, visible message, screenshot and whether audio continued.
9. Keep the branch on base `acef278`; do not rebase or resolve `docs/metrics-methodology.md` because the cloud agent owns eventual integration.
10. Do not open a pull request or merge. Aaron must explicitly authorize the next repository action after reviewing the evidence.

No agent receiving this handoff has authority to infer GitHub or deployment approval from the feature approval already given.

---

## 15. Definition of done

The feature is genuinely done only when all of the following are true:

- all repository tests and integrity checks remain green;
- optional exporter hangs are bounded without failing the completed core analysis;
- fixed-input flag-off JSON identity and flag-on technical-score identity are proven;
- Original A/B behaviour is correct and tested with Energy/Harmonics both off and on;
- missing component scores remain unavailable in both text and meter semantics;
- large-phone/tablet landscape above 900 CSS px has the intended transport and accessible A/B control;
- browser harnesses or equivalent reproducible checks are preserved durably;
- the four-minute performance and artifact budgets remain green;
- the current feature files are reviewed against the latest intended base;
- iPhone Safari passes the affected `:8877` Tailnet checklist — post-fix owner confirmation pending;
- Android Chrome passes the affected `:8877` Tailnet checklist — post-fix owner confirmation pending;
- no protected scoring/knowledge file changed;
- warnings, relative units and display-only status remain clear;
- Aaron reviews the evidence and explicitly authorizes the next repository action.

Until then, the correct state is:

```text
IMPLEMENTED + PARTIALLY VERIFIED + TAILNET TEST SERVER AVAILABLE
FIVE TECHNICAL STOP-SHIP GATES PASS AUTOMATED VERIFICATION
POST-FIX PHYSICAL DEVICE RERUN PENDING
NOT RELEASE-APPROVED
```
