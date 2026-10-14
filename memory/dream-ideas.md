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

---

*(D3 — new evidence, 2026-10-14: Aaron asked "what's all the recent good results
of good songs that I've got now as a selection?" — answered by hand from
`ranked_takes.py` plus a temporary merge of an unmerged branch. A per-song
best/consistency page would have answered it at a glance. Status unchanged:
parked, re-surfaced for Aaron's call.)*

## D7 — Sung-window finder (talk trimmer) · `status: proposed` *(2026-10-14)*

A `tools/find_sung_window.py` that takes a vocal stem and proposes the sung
window plus mute masks for spoken bits inside it (MC, pre-song chat, spoken
titles, asides in instrumental breaks), using stem energy + pitch steadiness +
word timings. It prints a review table (time, kind, confidence) and writes the
cut/mask so the same edges drive both the analysis and the polish.

- **Seed:** every take on 13–14 Oct was cut by hand: You Could Be Mine (Tribe,
  plus the 4:16 aside), Let's Stay Together (spoken title), Play That Funky Music
  (MC + TikTok chat), the 11 Oct "he's still going" and the mis-muted opening "I"
  that Aaron caught.
- **Moves:** turnaround per take, and fewer wrong cuts reaching Aaron.
- **Size:** ~1 day. No scoring change.

## D8 — Take identity guard · `status: proposed` *(2026-10-14)*

Before a new take is archived, compare its **vocal stem** against same-song
takes already in the archive (sample-level / contour correlation on the voice,
never the mix) and flag: (a) same performance from another mic, (b) exact
duplicates (same length + identical scores), (c) "same backing, different night"
— so dates and duplicates are never decided by backing alignment.

- **Seed:** I wrongly called the 14 Oct Let's Stay Together the 11 Oct
  performance because the karaoke backing lined up (Aaron: "The ones that I've
  uploaded today were from today"); and the 25 Feb / 7 May PTFM takes look like
  one recording scored twice (both 3:50, identical 7.4 / 8.1).
- **Moves:** archive integrity; trend lines without double-counted takes.
- **Size:** ~half a day; extends `check_take_integrity.py`. No scoring change.

## D9 — Arrangement as a first-class field · `status: proposed` *(2026-10-14)*

Make `take_context.arrangement` (single / album / extended / acoustic …) a
recognised field in `tools/take_context.py`, and have `ranked_takes.py` and the
progress tools group and trend by song **and** arrangement, saying so when a
comparison crosses versions.

- **Seed:** Aaron: "all ... except for the last two takes of Play That Funky
  Music were ... the single version" — the 14 Oct jump partly reflects a longer
  arrangement with longer lines. Tagged by hand today.
- **Moves:** honest like-for-like song trends.
- **Size:** a few hours. Grouping only — scores untouched.

## D10 — Breath map generator · `status: proposed` *(2026-10-14)*

From any analysed take, auto-build the phone breath cheat sheet: phrase runs,
endings that sag, the longest no-breath stretches, mapped to lyric line openers
from word timings — then, after the next take of the same song, a "did the plan
work?" before/after per spot.

- **Seed:** the You Could Be Mine breath map and the Tribe follow-up check were
  built by hand on 14 Oct; Aaron used the sheet on stage the same day and the
  plan measurably worked (breath 3.3 → 6.8).
- **Moves:** breath support — the PRIMARY FOCUS on Play That Funky Music tonight.
- **Size:** ~1–2 days. Reads existing measures; no scoring change.

## D11 — Gig-day vocal load log · `status: proposed` *(2026-10-14)*

A one-line log per day — warm-up, songs sung at home (full voice or marked),
gig songs — entered from the phone, shown beside each take in reports, and
later checked against breath / pitch dips across many days.

- **Seed:** Aaron: "I probably was a little bit taxed, maybe, but I didn't
  realise it" — nine full songs on 14 Oct; the last song of the night was his
  lowest Let's Stay Together.
- **Moves:** gig-day preparation; explains dips instead of guessing.
- **Size:** ~1 day for log + display. Never feeds the score.

## D12 — Applause meter · `status: proposed` *(2026-10-14)* · **wildcard**

Measure the crowd: from the separated backing/room stem, score the cheer and
applause after each song (level, length, how fast it starts) and print it next
to the technical score as "room response" — never blended into the /10. Over a
season it would show which songs land with an audience versus which score well
technically.

- **Seed:** none — the night's wildcard. (Adjacent: Aaron's "everyone's saying
  it sounds pretty good" about You Could Be Mine, which scored modestly.)
- **Size:** ~1 day prototype. Explicitly not a scoring change.
