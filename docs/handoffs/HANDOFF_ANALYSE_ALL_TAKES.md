# Handoff — Candi: measure the whole back catalogue into the repo

Date: 2026-07-27

**Short version:** the audio stays where it is. Nothing gets committed to the
repo except the analysis JSON that comes out the other end. Run two commands on
the host that holds the uploads.

---

## Why

The repo's archive holds **35 takes from 4 dates** (11–25 July). Candi's audit of
the host found **128 identified singer performances going back to February**,
**~109 with an isolated vocal stem already retained**. So roughly three quarters
of the singers' recorded history has never been measured into this repo.

That matters more than the reason this started. Rubric **v5** added
`breath_support` — the % of phrase endings that sag, which is Aaron's measured
primary limiter. **A single take gives a score; only a series gives a trend**, and
a trend is the thing that answers "is this getting better". Seventeen *You Sexy
Thing* takes across five months is worth more than any one analysis.

---

## Do this

### 0. Pull, and confirm which engine you are running

```bash
cd <repo>
git pull origin main
python3 tools/score_preflight.py        # must print PREFLIGHT PASSED / exit 0
```

Expect `deterministic_rubric_v5`. If preflight fails, **stop** — do not analyse
or quote anything until it passes (rule 2 in `CLAUDE.md`).

### 1. Rehearse — this writes nothing

```bash
python3 tools/analyse_takes.py \
    /home/rustwood/.openclaw/candi-workspace/openclaw-data/vox-coach/uploads/raw/ \
    <wherever the vocal stems live>
```

It prints four counts — found / already complete / NEW / REFRESH — plus anything
deferred because it would need separation. Read that before going further. If the
NEW count is wildly off, the folders are wrong.

**I need the stem directory path from you** — the audit says the stems are
retained but not where. Add every directory that holds them; the tool searches
recursively and takes as many paths as you give it.

### 2. The fast pass — stems only, no separation

```bash
python3 tools/analyse_takes.py <dirs...> --stems-only --write
```

`--stems-only` skips anything that would need separation to run, so this covers
the ~109 already-stemmed takes without re-running the slow step. It is
**resumable** — takes already complete are skipped, so if it is interrupted just
run it again.

If you want Aaron's trend first, narrow it: `--only aaron`.

### 3. The slow pass — the ~19 takes with no retained stem

```bash
python3 tools/analyse_takes.py <dirs...> --write
```

Without `--stems-only`, a take that has only a raw mix is analysed with
`--separate-stems`. That is much slower. It is never analysed as-is: a score
computed on a full mix is meaningless (rule 4), so the choice is separate-first
or skip.

### 4. Rebuild the tables and re-check

```bash
python3 docs/score-metrics/rescore_all.py
python3 tools/score_preflight.py
```

Then commit the changed `voxanalysis/archive/scratch-analyses/*.json` and
`docs/score-metrics/all-takes-rescore-*` and push.

---

## Do NOT commit the audio

~164 minutes of stems for the July takes alone, and far more across the whole
catalogue — several GB. Once it is in git history every future clone carries it
and removing it is painful. The tool reads from wherever the files sit on disk;
it never needs them inside the repo.

What belongs in the repo is the output: the analysis JSON, which is small.

---

## Safety behaviour, so you know what it will and won't do

- **Dry run is the default.** `--write` is required to change anything.
- **Resumable.** Takes already complete in the archive are skipped. `--force`
  overrides.
- **Atomic writes.** A failed engine run leaves the existing entry untouched.
- **Previous versions kept** alongside as `*.pre-reanalysis`. Delete once happy.
- **One performance, one record.** A file whose name differs from its archive
  entry only by a pipeline artefact (`_converted`, `_(Vocals)_UVR…`) updates that
  entry instead of creating a rival. It reports every such match.
- **Pairing is by filename.** A file named nothing like
  `YYYY-MM-DD-singer-song-take-NNN` cannot be paired with its archive entry and
  will be treated as a new take, and its artist will read "Unknown Artist". The
  dry run shows this before anything is written — check the NEW list for names
  that look like duplicates of takes already archived.

---

## The four unidentified uploads

From the audit:

- `2026-04-28-unknown-singer-unknown-song-take-001.m4a`
- `2026-04-28-unknown-singer-unknown-song-take-002.wav` (source missing, archived
  duplicate exists)
- `2026-07-09-unknown-singer-unknown-song-take-001.mp4` — "Run to Paradise",
  random male singer
- `2026-07-19-etta-james-tribute-unknown-song-take-001.mp4`

These will analyse fine but land under "Unknown Artist" and will not join any
singer's trend. **Better to identify and rename them first**, or leave them out
of this pass — an unattributed take in the archive is close to useless, since
every trend and comparison is per singer.

---

## Reference recordings — leave them alone for now

The 18 stored original-artist recordings are a separate question from singer
takes. The calibration pack is built from
`voxanalysis/vox-analysis/engine/calibration/references/` (50 analyses, already
current and complete) — **not** from the archive, so analysing more references
does not move the anchors and must not be assumed to.

If we later want to grow the calibration pack past 50, that is a deliberate
decision with its own re-scoring cycle, because changing the pack changes
`calibration_fingerprint` and retires every existing score. Not part of this job.

---

## What to expect at the end

- Aaron's history goes from 4 dates to roughly five months.
- Every newly analysed take carries `breath_support` and reports
  `coverage: "full"`; the 34 older archived takes lose their `coverage: partial`
  flag as they are refreshed.
- `rescore_all.py` will show a much larger table, and per-song series become
  possible for the first time — *You Sexy Thing* ×17, *Let's Stay Together*,
  *The Heat Is On* ×5, *Pressure Down* ×8.

Once that lands, tell Aaron the trend, not just the latest number.
