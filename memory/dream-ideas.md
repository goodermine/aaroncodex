# Dream ideas — the forward-dreaming ledger

Ideas the nightly /dream proposes for improving the system. Statuses:
`proposed` → Aaron says `build DN` / `park DN` / `dismiss DN`. Nothing is ever
built overnight; dismissed ideas keep their entry with a reason. D-numbers are
permanent and never reused.

---

## D1 — Onset trainer in the pitch monitor · `status: built` *(2026-08-04)*

A drill mode at `/monitor`: it plays a target note, goes silent for one beat
(the audiation moment), then listens — and verdicts the entry **clean / scoop /
overshoot** with the cents trace of your first 250 ms, keeping a streak count.
Block 1 of the drill programme, turned into a game with instant truth.

- **Seed:** memory 003 — first-timer drills need a "how do I know I'm doing it
  right" check; the walkthrough already tells Aaron to eyeball the monitor
  trace. This closes the loop automatically.
- **Moves:** clean entries 23.7% → 33% target — the #1 measured gap.
- **Size:** a few days (monitor already tracks pitch live; needs note targets,
  a 250 ms classifier, and UI).
- **Built:** TRAIN mode in pitchmonitor/index.html — play→hear→sing state
  machine, raw-pitch 250 ms classifier (thresholds shared with ENTRY ACCURACY),
  target line + clean-zone band on the grid, streak/clean-% tally, range +
  volume settings; headless smoke check in pitchmonitor/tests/.

## D2 — Guided drill-session player · `status: parked` *(2026-08-04)*

A "practice mode" page that runs the 20 minutes for you: block timers,
on-screen step-by-step instructions (the beginner walkthrough, not the card),
the day's heavy-block rotation, one tap to switch to the 6-minute recovery
version. Phase 2 (mid-September) flips it to shuffled/interleaved order
automatically — the variable-practice progression enforced by the tool.

- **Seed:** "First time I've done this stuff… explain exactly how I go through
  each drill step by step" — a static PDF can't pace, time, or shuffle.
- **Moves:** adherence and correctness of the daily 20 minutes; the blocked→
  variable transition that decides December.
- **Size:** a few days on the existing VOX Suite kit.

## D3 — Progress dashboard: the four numbers · `status: parked` *(2026-08-04)*

One page plotting the four tracked measures — clean entries %, phrase-ending
sag %, intra-note drift, median phrase length — per month from dry home takes,
against their 3-month targets, with the entry-accuracy reliability flag
respected. Data already exists in every archive JSON and the rescore tables.

- **Seed:** the "How you will know it is working" table lives only in a PDF;
  today the trend check was me running Python by hand.
- **Moves:** makes the monthly check a glance instead of an analysis session.
- **Size:** ~a day (all data present; chart kit exists).

## D4 — Onset map in every full report · `status: built` *(2026-08-04)*

Wire `tools/onset_map.py` into the report pipeline: whenever a take's song has
a scored reference in the archive, the full results include the two-panel
"how each note starts" figure automatically.

- **Seed:** Aaron asked "can I see Farnham's pitch graph and mine overlaid" —
  built and run by hand today; nothing regenerates it for future takes.
- **Built:** tools/onset_map.py refactored importable (find_reference +
  render_onset_map); tools/show_results.py renders the figure automatically and
  instructs sending it with the results; ANALYSIS_RUNBOOK updated; 5 tests.
- **Moves:** every future take shows the scoop pattern shrinking (or not) at a
  glance.
- **Size:** hours.

## D5 — Song-fit picker from the songbook catalogue · `status: parked` *(2026-08-04 — Aaron: "a good option later")*

Rank the ~68k-song karaoke catalogue by fit to Aaron's measured voice:
tessitura overlap with A3–A4, time spent in the C♯4–F4 passaggio, and a
**"cold-open safe" flag** (low-lying, more spoken than sung, short phrases —
the *Satisfaction* profile) for walk-in-and-sing situations.

- **Seed:** the campaign's song-shape selection rule + the cold open at
  Redcliffe Leagues; songbook_lite.csv already exists in the songbook repo.
- **Honest hard part:** the catalogue has no per-song range data — it would
  need a source for key/melody info, or start with only the songs that have
  references/takes in the archive. Scope carefully before building.
- **Size:** days, plus the data question.

## D6 — "Ghost duet" mode · `status: parked` *(2026-08-04)* · **wildcard**

Sing Pressure Down while the monitor scrolls **Farnham's actual stored pitch
contour** ahead of you like a driving line — you sing *into* his trace, seeing
your line lay over his in real time. Audiation practice against the real
reference, not a piano note. Every reference in the archive already carries its
full F0 contour, so the data is sitting there.

- **Seed:** none — the permitted nightly wildcard. (Adjacent evidence: today's
  overlay figure landed well.)
- **Moves:** onset + phrasing imitation in the most direct way possible;
  also just delightful, which keeps practice happening.
- **Size:** days; the risk is UI busy-ness — prototype on one song first.
