# VOX — what we are building

Stated by Aaron, 26 Jul 2026. This is the north star. Anything in this repo that
does not serve one of these six pillars is a side quest.

> A self-enclosed system that analyses a singer's vocals and tells them how to
> improve. Record inside the system or upload; analyse either. Measure pitch,
> spectrum and harmonics in real time. Polish a song recorded here or elsewhere.
> Ask the knowledge base questions — as the singer or as their coach — and get
> answers drawn from it. All of it on a cloud server behind a login for public
> testing.
>
> The goal is the most powerful voice analysis app on the planet.

**Self-enclosed is the point.** A singer should never have to leave for a
different tool, and never have to send audio to a third party to get a number.

---

## The six pillars, and where each one actually stands

Honest status. "Built" means it works end to end today; it does not mean it is
finished or beta-ready (see `docs/beta-readiness-audit.md`).

### 1. Capture — record in the system
**Built.** `design/vox-record.js` records in-browser with the processing
defaults off (`noiseSuppression`, `echoCancellation`, `autoGainControl` all
false — a take that has been de-noised by the browser cannot be measured
honestly). Trim start/end with waveform peaks and preview before committing.
Uploads route through the same trim path, so an imported file and a recorded
one arrive at the engine identically.

*Gap:* no `/capture` standalone entry point; no save/reload of takes between
sessions; iOS suspends recording on screen lock and we do not yet warn about it.

### 2. Analysis — measure it and score it
**Built, and this is the strongest part of the system.** Fourteen measurement
modules, one calibrated score, full provenance pinning. See
`docs/score-metrics/SCORE_CONTRACT.json` and rule 1 of `CLAUDE.md`: exactly one
engine may produce a `/10`, and it is
`voxanalysis/vox-analysis/engine/analyse_song.py`.

Everything a competitor would call a feature — jitter/shimmer/HNR/CPPS per
sustained note, vibrato rate and extent, phrase-ending sag in cents, register
transitions, singer's formant, H1−H2 — is already measured.

*Gap:* the calibration pack is 50 pro references; more, and more genre-specific,
would tighten the scale. Voice quality still has no pro-pack anchor for CPPS.

### 3. Feedback — tell them how to improve
**Built.** `prescriptions` names the primary limiter with severity and pulls
exercises verbatim from the 106-exercise hash-verified library
(`engine/knowledge/prescription_map.json`). `report_builder.render_full_results_text()`
is the single source of truth for what gets sent, and it matches the web page
exactly.

*Gap:* feedback is per-take. There is no longitudinal "here is what changed
since last month, keep doing X" narrative yet — `tools/progress_report.py` has
the trend data but nothing turns it into coaching.

### 4. Real time — pitch, spectrum, harmonics live
**Partly built — real-time pitch AND live spectrum/harmonics now in the monitor.**
`pitchmonitor/` does real-time pitch: YIN detection (chosen because plain
autocorrelation locked onto 1633 Hz for a 110 Hz note), verified 82–1046 Hz to
within 0.4 cents, with note labels on both axes.

*Live spectrum + harmonic display — built (28 Jul).* A **SPEC** toggle in the
monitor switches the stage to a scrolling spectrogram on a fixed log-frequency
axis (55 Hz–8 kHz), loudness as colour. The detected pitch is drawn as a solid
f₀ line with its overtones (2f, 3f … 10f) marked, and the 2–4 kHz singer's
"ring" band is highlighted — so the harmonics are read against where they sit,
not eyeballed. The FFT was already running for YIN (`getFloatFrequencyData` on
the same `AnalyserNode`, bumped to 4096 for finer lines while YIN keeps a 2048
slice), so this was drawing, not new signal work.

*Full-take render — first version built (28 Jul).*
`tools/render_take_spectrogram.py` draws a whole take as one image in the same
style (inferno spectrogram, log axis with note lines, ring band) with the sung
pitch overlaid in green — solid where the pitch is a steady held note, dotted
where it is jumpy/uncertain. It is a CLI renderer, not yet wired into the
analyser deck; that UI integration is the remaining piece.

*Gap:* still missing: metronome, tempo/beat lines, transpose, PWA install, a
live metallic-index readout beside the picture, and folding the full-take render
above into the standalone analyser UI.

*Planned — the same spectrogram inside the standalone analyser UI.* The scrolling
spectrogram is live in the monitor and the full-take still image exists as a CLI
tool; the remaining work is drawing it in the deck:

- **After a take, in the standalone analyser** — the frame layer already computes
  the same data (`alpha_ratio`, `sfr_2_4k`, the H1–H8 harmonic tracks, §2 of
  `docs/plans/STANDALONE_SONG_ANALYSIS_PLAN.md`). It comes out as numbers today;
  drawing it is a rendering step on top.

Where ours should go beyond a raw spectrogram: overlay where the harmonics
*should* sit, mark the 2–4 kHz "ring" band, and show the metallic-index value
beside the picture — so the singer is not left eyeballing brightness. The
measurement exists or is being built; only the drawing is outstanding.

### 5. Polish — clean and correct a take
**Built.** `voxpolish/`: clean/de-noise with a re-blendable amount, auto-tune
with a correction curve, master, A/B against the original with the playhead
preserved, atomic writes, single-flight render with stale-lock takeover.

*Gap (root cause fixed 29 Jul):* Auto Tune was silently bypassed on the deployed
host because the WORLD vocoder (`pyworld`) imports `pkg_resources`, which ships
inside `setuptools` — absent by default on Python 3.12+. The `pitch` extra now
declares `setuptools>=68`, so `pip install 'voxpolish[pitch]'` restores it. The
deck already reports the failure loudly rather than handing back untuned audio.
Remaining: the host must pull + reinstall the pitch extra and restart, then
re-render Pressure-Down-Cook (its cached render was made with tune bypassed). See
`HANDOFF_POLISH_AUTOTUNE_BYPASS.md`.

### 6. Knowledge base — ask it questions
**Content built. The asking is not.** `vocal-knowledge-base/` holds 77 active
documents, ~524,000 words, front-matter clean and topic-tagged against a
controlled vocabulary.

*Gap:* there is **no retrieval layer, no query interface, no citation
mechanism**. Right now it is a folder of markdown a human can grep. Turning it
into "a coach or singer asks a question and gets an answer pulled from the
knowledge base" is unbuilt work, and it carries two hard constraints:

- **Provenance.** The material was synthesised with AI research tools, which
  produce confident errors. Answers must cite the document and point at
  `sources/`. Never present it as settled physiology without the reference.
- **The engine's exercise library wins.** If the KB and
  `prescription_map.json` disagree on *what to do*, the prescription library is
  authoritative — that is what the score was computed from. The KB explains
  *why* a drill works; it does not prescribe.

---

## The seventh thing: cloud, login, multi-user

**Not built at all.** Today VOX is single-user by construction: a Tailscale host,
one flat workspace directory, no accounts, no auth on any route, no per-user
data isolation. `voxsuite/src/voxsuite/server/unified.py` has no concept of who
is asking.

Public testing behind a login needs, at minimum:

- accounts and sessions, on every route including `/api/*`
- per-user workspaces — takes, scores and sessions scoped to an owner
- job quotas and concurrency caps per user (the current caps are global; see
  M8/M10/M11 in the beta audit)
- a real storage story — sessions are folders on local disk today
- upload limits, and a decision on retention: whose audio, kept how long

This is the largest single body of unbuilt work in the project, and none of the
existing engines need to change to do it — it is a layer above them.

---

## What "most powerful on the planet" has to mean in practice

Not "most features". Three things, in order:

1. **The numbers are right.** Every rule in `CLAUDE.md` exists because a real
   singer was handed a wrong number. One engine, provenance on every score,
   preflight before publishing, and a withheld score rather than a plausible
   invented one. A competitor with a prettier chart and a made-up score is not
   a competitor.
2. **It measures what actually limits the singer.** Phrase-ending sag in cents,
   with the count and the timestamps, beats a five-star "pitch" rating. The
   capture-fair score exists so a phone recording is judged on the voice and not
   the room.
3. **It says what it cannot do.** No artistry score. No anatomy, injury or
   medical claim. `PRIMARY FOCUS` gets checked against capture sensitivity
   before it becomes coaching advice.

---

## Nearest-term work, ordered by distance from the goal

1. ~~**Live spectrum + harmonics in the monitor**~~ — **done (28 Jul).** SPEC
   toggle draws a scrolling spectrogram with f₀ + overtone overlay and the
   2–4 kHz ring band (see pillar 4). Still to draw: the same view in the
   standalone analyser once its frame layer lands.
2. **KB retrieval + ask interface** — the content is done, the product is not.
3. **Auth and per-user isolation** — the gate on public testing.
4. **Fix the vocoder on the deployed host**, then re-render Pressure-Down-Cook.
5. **Clear the beta audit's remaining majors** — concurrency trio, job caps,
   packaging.
