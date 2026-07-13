# VOXAI entry-point architecture

VOXAI is one product with one measurement engine and two independent entry
points.

```text
Candi / Telegram ---------\
                           > shared analyse_song.py + calibration
VOXAI-Alpha web ----------/
```

## Candi / Telegram

The Telegram path is orchestrated by `scripts/candi_phase1.py` and the Candi
OpenClaw workspace. It owns natural-language intake, VOXAI knowledge retrieval,
singer/song memory, coaching replies, drill history and progress logs. Telegram
transport configuration, chat identifiers and private runtime data do not
belong in the web application.

## VOXAI-Alpha web

`backend/pitch-viewer/` owns browser uploads, asynchronous local jobs, audio
playback, pitch visualisation, original-track comparison and web-formatted
reports. It does not act as a Telegram bot and does not own Candi's durable
memory. Its runtime job directory is ignored and must be replaced by durable
storage and an external queue before public production deployment.

## Shared engine contract

`backend/voxai-local-analysis/` is the only acoustic-analysis implementation.
Both entry points must call its `analyse_song.py` and use the same calibration.
The current product contract is:

- V3 diagnostic surface: deep trouble spots, CPPS/strain, registers, breath,
  groove, range, onset quality, harmonics, singer's formant and vowel space;
- V2 calibrated scoring rubric: overall, capture-fair and six component scores;
- diagnostic fields do not silently alter calibrated scores;
- measured, inferred and unverifiable findings remain visibly separate.

Presentation code may transform the shared JSON into Telegram coaching or a
browser payload. It must not recompute acoustic metrics or invent replacement
scores.

## Deployment boundary

The two entry points may eventually run as separate cloud services or
containers. They should depend on the same versioned analysis worker/API rather
than copying the engine. Secrets, uploads, downloaded references, reports and
private singer history must remain outside Git.
