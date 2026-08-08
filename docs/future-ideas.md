# Future ideas

Surfaced from the `/dream` review of 2026-08-05. These are system improvements
identified from patterns in recent sessions. Pick up any of them when the time
is right.

## F1. Song-fit predictor

**Status:** parked

Analyse a song's tessitura from a reference stem (or YouTube rip) before Aaron
records it. Reports whether the song sits in his strong M2/mixed zone (A3–B4)
or forces register crossover. Would help pick setlist songs strategically and
set realistic score expectations.

**Why it matters:** The Oh What A Night vs Rebel Yell comparison (Aug 2026)
showed the clearest evidence that tessitura determines score outcome. The data
exists — the lookup isn't productised yet.

## F2. Recording-chain auto-detect

**Status:** parked

Detect TazCam mixer compression from the audio itself (phrase-level dynamic
spread below ~20 dB = compressed). Tag the analysis with
`capture_chain: "compressed"` or `"natural"` so the report builder
automatically leads with capture-fair on mixer recordings.

**Why it matters:** Two Oh What A Night takes from the same session, same voice,
different scores purely because of the desk. This will keep happening.

## F3. Archetype timeline

**Status:** parked

A per-song progress view showing archetype shifts over time (e.g. Pitch Slider →
Hybrid on Oh What A Night between Jul 8 and Aug 4). Could be a column in the
score tables or a standalone artifact.

**Why it matters:** The archetype shift is the most motivating signal in the
archive but it's buried in JSON. There may be other songs showing movement we
haven't noticed.

## F4. Reference library expansion

**Status:** active

Build a library of analysed reference vocals for Aaron's regular setlist songs.
With reference stems for his top 5–10 songs, every future analysis can
auto-compare against the original — highlighting where phrasing, pitch, or
timing diverges, the way the Oh What A Night comparison was done manually.

**Why it matters:** The Oh What A Night comparison (Aaron vs Frankie Valli)
produced the most useful coaching insight of the session. Doing it once was
labour; doing it systematically is a tool.

## F5. Full-session auto-segmenter

**Status:** parked

Auto-segment a long recording (warmup through singing) into individual takes
by detecting silence gaps between songs. Queue each segment for batch analysis
with no manual splitting.

**Why it matters:** Aaron's workflow is moving toward longer recording sessions.
The manual split step is the bottleneck.

## F6. Daily drill + pitch monitor integration

**Status:** parked

Add a specific 5-minute slot in the daily drill PDF: "open the pitch monitor in
onset mode, work through these 8 notes, screenshot your landing accuracy." Closes
the loop between the drill doc and the onset trainer (D1) that was already built.

**Why it matters:** The core training gap (pitch matching / onset accuracy) has a
purpose-built tool that isn't getting daily use yet.

## F7. Score trend dashboard

**Status:** parked

A persistent artifact showing Aaron's score progression over time — per song and
overall — with annotations for archetype shifts, calibration changes, and capture
method. Would replace ad-hoc "what are my top 5" queries with a living dashboard.

**Why it matters:** With 150+ analyses, querying the archive ad-hoc is slow and
lossy. A dashboard makes progress visible at a glance.
