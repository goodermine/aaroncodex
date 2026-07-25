# Handoff — Candi Telegram replies must send the FULL results (web parity)

Date: 2026-07-25

**Goal:** when Aaron analyses a take through Telegram, Candi hands back the
**complete measured analysis — the same content as the web page**, not a trimmed
summary. This is a standing request ("I want the full analysis every time, not
hidden in a file").

There is now **one source of truth** for that text in the repo, so Candi's
Telegram output can match the web exactly. Pull `main` and use one of the two
paths below.

## The single source of truth

`voxanalysis/vox-analysis/viewer/report_builder.py` →
**`render_full_results_text(report, result=None)`**.

It renders the same sections the web page's "Copy full results" produces —
scores, capture-fair, calibration provenance, every metric group, trouble spots,
primary focus, the Measured / Inferred / Unverifiable evidence lists, and the
practice plan — as plain text. `report` is `build_v2_report(raw)`; `result` is
the job result dict (for the range line + file name).

### Path A — Python (Candi runs the engine directly)

```python
from report_builder import build_v2_report, render_full_results_text

report = build_v2_report(raw_analysis)          # raw_analysis = the *_analysis.json dict
text = render_full_results_text(report, result) # result carries robust_min/max_note, file_name
# send `text` to Telegram — in full (see chunking below)
```

### Path B — HTTP (same server the web uses)

```
GET /api/pitch-jobs/{job_id}/full-results        → text/plain, the full results
```

Added to the analyze app and harvested onto the unified server, so it's on the
same origin as the deck. Use this if Candi already talks to the vox API. (For the
deepest technical detail, `GET /api/pitch-jobs/{job_id}/report` still returns the
full technical markdown — attach it alongside if you want the raw tables too.)

## What "full" must include (and what the text already contains)

- **Scores:** overall **and** capture-fair, confidence, and the calibration
  provenance line — "Calibrated · 50 pro refs · 10 = a typical pro". This is what
  answers "is that a calibrated score or mine?".
- **Every component** (intonation / pitch stability / voice / vibrato / dynamics
  / phrase) with its basis.
- **Every metric group**, the **trouble spots**, the **primary focus**, the
  **Measured / Inferred / Unverifiable** lists, and the **practice plan**.
- A comparison block when a reference was compared.

Do **not** curate it down. The text ends with "This is the full measured
analysis, not a summary." on purpose.

## Reconciling with the score guard

The score guard (Candi's `candi_phase1.py`) may **withhold the /10** when
provenance/calibration is uncertain — that's correct and stays. It does **not**
mean sending less. When the score is withheld:

- `render_full_results_text` already prints **"Overall: — (score withheld
  pending calibration review)"** and still includes **all** the measured
  findings, capture-fair, components and practice plan.
- So the rule is: **always send the full results; only the single `/10` headline
  is ever withheld, never the analysis.**

Use the **capture-fair** number for live/phone/room takes and any cross-era
comparison (the text flags this inline when the engine detects a room/live
capture).

## Telegram delivery note

The full text can exceed Telegram's **4096-character** per-message limit. Send it
in **multiple messages** (split on blank lines / section headers), never truncate.
Plain text renders fine; if you prefer, wrap it in a monospace block. If a take
is very long, an alternative is to send the headline scores inline **and attach
the full text as a `.txt`/`.md` file** — but the default should be the text in
the chat, per the standing request.

## Note for whoever maintains Candi's Telegram skill

Candi's Telegram/bot code lives in her workspace (`openclaw-data/vox-coach/…`,
not in this repo). This handoff + the shared `render_full_results_text` /
`/full-results` endpoint are the repo-side half. The workspace-side change is:
in the deep Telegram vocal-analysis skill, replace any summarised reply with the
output of `render_full_results_text` (or the `/full-results` fetch), chunked to
Telegram's limit. Everything needed to produce web-identical output is now in the
repo.
