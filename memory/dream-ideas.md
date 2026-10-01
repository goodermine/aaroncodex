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

## D7 — Session bootstrap for engine + PDF deps · `status: parked` *(2026-08-04)*

A `tools/setup.sh` (or a SessionStart hook — the `session-start-hook` skill
exists) that installs the engine and document deps a fresh container lacks:
`numpy scipy librosa` (without them `score_preflight.py` / `show_results.py`
won't import) and `reportlab pdfplumber pypdfium2` for PDF build/verify, and
notes that `poppler-utils` is absent so page-render falls back to pypdfium2.

- **Seed:** this session, `/dream`'s own run-up — preflight failed three times
  in a row (`No module named 'numpy'` → `scipy` → `librosa`) before it would
  pass, and every PDF this session needed reportlab/pdfplumber pip-installed
  first. A fresh session cannot score or render out of the box.
- **Moves:** any session runs preflight / show_results / onset_map and renders
  PDFs immediately; removes a repeated per-session tax and a failure that looks
  like a broken engine but is just a missing dep.
- **Size:** hours.

## D8 — Guide-freshness check for the songbook library · `status: parked` *(2026-08-04)*

A small linter: for each `songbook/guides/<artist>/<song>.md`, find the latest
archived take of that song and flag when a newer take supersedes the one the
guide's "measured" section cites, so the reference library doesn't silently go
stale as takes accumulate.

- **Seed:** this session — the Kung Fu Fighting and Pressure Down guides cite
  specific takes/measures, and new home-studio + live takes (KFF 003–005, PD
  009–010) landed on branches the same week; nothing tells a guide it's now
  behind.
- **Moves:** keeps the how-to-sing guides honest against the archive; makes
  "fold the new takes into the guides" a flagged to-do, not a memory task.
- **Size:** ~a day (archive JSONs already carry song + date; the guides name
  their source takes in a Sources line).

## D9 — Auto "listening version" of any coaching doc · `status: parked` *(2026-08-04)*

A generator that turns any handoff/brief into a **narration-optimised PDF** for
ElevenLabs Reader: flowing second-person prose, no tables/bullets, note names
spelled out ("C sharp four"), symbols removed, length tuned to a ~20-minute
listen (~3,000 words). Pairs with the existing `kb_to_pdf.py` reading renderer.

- **Seed:** Aaron asked for a 20-minute narrated brief to listen to while
  resting ("put it in eleven readers so that I can just listen to this… while I
  go and have a little bit of a rest"), and it worked — he fell asleep to it.
  Built by hand this session; nothing regenerates it for the next doc.
- **Moves:** makes audio a first-class deliverable for the format Aaron
  actually consumes lying down, not a one-off.
- **Size:** ~a day (a TTS-sanitiser pass over the PDF pipeline).

## D10 — With/without-earplugs A/B one-pager · `status: parked` *(2026-08-04)*

A one-pager that takes two takes of the same song and lays their onset /
scoop / drift measures and the D4 onset maps side by side — turning a
controlled self-experiment into evidence. First use: the Loop-earplugs test
(plugs-in vs plugs-out, same song, same loud level) to see whether hearing
himself better tightens his entries.

- **Seed:** Aaron bought Loop Experience 2 earplugs and is testing whether the
  occlusion effect (own voice louder, band quieter) cuts his scooping; we
  designed the A/B this session but there's no report that renders it.
- **Honest hard part:** `tools/compare_takes.py` already exists for
  take-vs-original — this reuses/extends it for take-vs-take with an onset
  focus rather than building fresh; scope to that.
- **Moves:** converts the earplug question (and future gear/technique
  experiments) into a measured yes/no on the #1 gap.
- **Size:** hours, on `compare_takes.py` + `onset_map.py`.

## D11 — Ledger merge-safety check · `status: proposed` *(2026-08-09)*

A tiny CI/pre-merge check that fails if `memory/dream-ideas.md` or
`memory/MEMORY.md` comes out of a merge with **fewer** entries than either
parent had — i.e. a D-number or a fact id present before is absent after. Print
the missing ids and refuse.

- **Seed:** D7–D10 were added on 4 Aug (commit `edf9b0a`), landed on main via
  PR #31 (`8bc4c68`), and were then **silently dropped** when two later commits
  from another branch (`f8627f6` Build D4, `caf106b` Build D1) overwrote the
  ledger with a version predating them. Nobody noticed for five days; this
  `/dream` run found it only because it went looking for its own last output.
- **Moves:** the ledgers are append-mostly by design and D-numbers are declared
  permanent — but nothing enforced it, so a routine merge quietly deleted four
  of Aaron's parked decisions. The same class of loss can hit `MEMORY.md`.
- **Size:** hours (a ~40-line script + a workflow step, or a pre-commit hook).

## D12 — Range-map trust flags: octave-lock and backing-vocal bleed · `status: proposed` *(2026-08-09)*

Two automatic diagnostics on `range_map`, emitted as `diagnostic_flags` so the
range numbers carry their own confidence:

1. **Octave-lock** — most-used note below ~E3 *while* spectral centroid is bright
   (>~1900 Hz) means the tracker latched onto the backing, not the voice. A
   bright lead cannot have a bass tessitura.
2. **Backing-vocal bleed** — a sustained ceiling several semitones above the
   take's own core, carrying little time and sitting where a backing part would,
   is almost certainly not the lead.

- **Seed:** this session, both failure modes bit the song-fit sheet. Seven songs
  (Beggin', Rebel Yell, Sex Bomb, Don't Be Cruel, Sunshine Smile, Lonely Boy,
  Wild Thing) read as bass and are still unrankable; *You Can Leave Your Hat On*
  was ranked **Hard with a "drop it 6 semitones"** recommendation entirely
  because backing singers put an F5 in the stem — Joe Cocker's own lead only
  reaches A4. Both tests were run by hand, ad hoc, and are not in the pipeline.
- **Moves:** stops range-derived coaching being confidently wrong, and unblocks
  the nine takes currently sitting in the sheet's "not ranked" appendix.
- **Honest caveat:** thresholds were eyeballed on a handful of takes; they need
  validating against the reference pack before they gate anything.
- **Size:** ~a day, measurement only — no scoring change (rule 1 untouched).

## D13 — Sing against your own best take · `status: proposed` *(2026-08-09)* · **wildcard**

In TimberTones/the monitor, offer Aaron's **own best stored take** of a song as
the target line instead of a piano tone — his Oh What A Night contour scrolling
ahead of him, to sing back into. Same machinery as D6's ghost duet, but the
reference is *him at his best* rather than the original artist.

- **Seed:** the permitted wildcard, but it has one anyway — fact 012 says his
  in-tune singing happens when his voice "just goes there" rather than when he
  consciously matches, and fact 016 says the M2/mixed sound is where he is most
  precise yet least comfortable *because he is not used to hearing it*. Playing
  his own best M2/mixed take back at him attacks exactly that unfamiliarity.
- **Moves:** conscious pitch-matching (the #1 gap) with a timbre he can actually
  match — his own — and normalises the M2/mixed sound he currently distrusts.
- **Size:** days; depends on D6's contour-overlay work, so build that first.
