# Melody Match — take vs original

| Field | Value |
|---|---|
| Take | `2026-10-11-aaron-you-could-be-mine-take-001_analysis.json` (Aaron) |
| Original | `reference-contour.json` (Guns N' Roses (original reference)) |
| Transposition | +0 semitones (removed before comparison) |
| Median absolute pitch difference | 30.0 cents |
| Frames within 50 cents of the melody | 69.8% |
| Timing spread | 20.69 s |

## Section by section

| Section | Pitch vs original | Read | Timing | Feel |
|---|---|---|---|---|
| 0:40-1:00 | -20.0 cents | on the melody | +1.46s | behind the original |
| 1:00-1:20 | +0.0 cents | on the melody | +4.49s | behind the original |
| 1:20-1:40 | +0.0 cents | on the melody | +1.31s | behind the original |
| 1:40-2:00 | +20.0 cents | on the melody | +3.34s | behind the original |
| 2:00-2:20 | +10.0 cents | on the melody | -5.64s | ahead of the original |
| 2:20-2:40 | +0.0 cents | on the melody | +3.71s | behind the original |
| 2:40-3:00 | +0.0 cents | on the melody | +8.15s | behind the original |
| 3:00-3:20 | +10.0 cents | on the melody | +3.87s | behind the original |
| 3:20-3:40 | +0.0 cents | on the melody | -6.43s | ahead of the original |
| 3:40-4:00 | +10.0 cents | on the melody | -3.08s | ahead of the original |
| 4:00-4:20 | +0.0 cents | on the melody | -2.93s | ahead of the original |
| 4:20-4:40 | -410.0 cents | flat of the original | -9.04s | ahead of the original |
| 4:40-5:00 | +10.0 cents | on the melody | -14.94s | ahead of the original |
| 5:00-5:20 | +10.0 cents | on the melody | -16.35s | ahead of the original |
| 5:20-5:40 | +0.0 cents | on the melody | -8.88s | ahead of the original |

*Similarity to the original performance, transposition removed. Departure from the original can be deliberate interpretation — judge by ear at the timestamps.*

## Interpretation and limits

The original was processed as a reference vocal only: raw pitch contour was extracted and compared with banded DTW. No VOX technical or overall score was calculated for the downloaded reference recording.

The broad match is close: 30 cents median absolute pitch difference, with 69.8% of aligned voiced frames within 50 cents, and no semitone transposition detected. The 4:20–4:40 window is an exception at -410 cents. It has 63 voiced aligned frames (31.2% of the aligned samples in that window) and a relative lag of -9.04 seconds, so treat it as a place to listen back, not a settled performance finding. Phrase alignment and the separated vocal contour can both affect that result. The 20.69-second timing spread also means the section lag labels are broad alignment guides, not a strict synchronisation judgement.

## Reference provenance

Source: `DVzcQ4_khsM-You Could Be Mine.wav`, the downloaded reference file (PCM 16-bit, 48 kHz, stereo; 343.64 seconds). SHA-256: `53f83ae72f83db00f2f9a9c70aaf1c865701b7cef40dc05a360d6ae26521a842`. The staged source matched byte-for-byte. Its separated vocal stem also measured 343.64 seconds. The comparison uses raw pitch contours only; no technical or overall score was calculated for the reference.
