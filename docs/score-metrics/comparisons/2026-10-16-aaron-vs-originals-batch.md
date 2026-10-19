# Aaron vs the originals — 16 Oct 2026

> **Snapshot as of 16 Oct 2026 (archive state before the Greshman's 16 Oct and later takes landed).** Takes analysed since — e.g. The Door 16 Oct, My Girl 16 and 18 Oct, You Give Love a Bad Name 18 Oct — are not in these tables; "No Aaron takes yet" means none at snapshot time.

Fourteen original studio recordings supplied by Howard (Dropbox `/Song_Analysis/Originals for analysis - DELETE AFTER/`), each verified against its SHA-256 in PROVENANCE.txt, scaled losslessly to −1 dBFS where they peaked above it, separated with the pinned RoFormer model, and analysed as **reference vocals only**: raw measures were kept and **no VOX score was calculated or kept for any original**. Aaron's takes were compared with `tools/compare_takes.py` (banded DTW on the persisted pitch contours, transposition removed and reported). Audio, stems and reference JSONs are not committed; the originals are deleted after analysis.

Measures: held-note drift (median intra-note drift, cents), phrase endings falling (% of endings with a downward pitch release — the measure is pitch-only and counts stylistic fall-offs too), clean entries (% of note onsets landing on pitch), overshot entries (%).

## Carl Douglas - Kung Fu Fighting (original)

Original as measured: centre E4, range E3–E5, core F♯3-D5 · drift 46.6 c · endings falling 35.5% · clean entries 38.1% · overshot 31.0%

| take | score (higher of two) | key vs original | melody within 50 c | drift | falling | clean | overshot |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-07-30-aaron-kung-fu-fighting-take-001 | 7.8 | +0 | 67.7% | 82.2 | 48.7% | 26.4% | 31.2% |
| 2026-07-31-aaron-kung-fu-fighting-take-002 | 7.7 | -2 | 69.0% | 98.5 | 43.5% | 24.6% | 36.9% |
| 2026-08-01-aaron-kung-fu-fighting-take-003 | 7.9 | -2 | 65.1% | 78.4 | 70.7% | 27.8% | 34.1% |
| 2026-08-01-aaron-kung-fu-fighting-take-004 | 9.4 | -1 | 66.8% | 57.3 | 50.0% | 25.0% | 26.6% |
| 2026-08-01-aaron-kung-fu-fighting-take-005 | 9.0 | +0 | 65.6% | 69.2 | 35.9% | 26.2% | 33.1% |
| 2026-08-09-aaron-kung-fu-fighting-take-006 | 8.1 | +0 | 67.9% | 74.2 | 46.9% | 33.9% | 29.8% |
| 2026-08-13-aaron-kung-fu-fighting-take-007 | 8.0 | +0 | 73.2% | 49.3 | 60.0% | 34.9% | 29.4% |
| 2026-08-14-aaron-kung-fu-fighting-take-008 | 9.1 | -1 | 65.7% | 59.5 | 38.2% | 29.3% | 36.4% |
| 2026-08-15-aaron-kung-fu-fighting-take-009 | 8.9 | +0 | 72.5% | 50.5 | 46.2% | 34.3% | 31.3% |
| 2026-08-29-aaron-kung-fu-fighting-take-009 | 9.1 | +0 | 74.8% | 59.0 | 35.9% | 31.3% | 34.8% |
| 2026-09-12-aaron-kung-fu-fighting-take-001 | 9.3 | +0 | 67.3% | 61.1 | 53.7% | 28.3% | 34.1% |
| 2026-09-13-aaron-kung-fu-fighting-take-002 | 9.0 | +0 | 70.9% | 56.1 | 52.9% | 28.6% | 36.4% |
| 2026-09-26-aaron-kung-fu-fighting-redcliffe-leagues-club-open-mic-take-001 | 9.6 | +0 | 69.8% | 52.5 | 42.1% | 33.9% | 23.6% |
| 2026-09-26-aaron-kung-fu-fighting-take-001 | 8.0 | -2 | 64.8% | 70.4 | 57.7% | 24.2% | 35.3% |
| 2026-10-11-aaron-kung-fu-fighting-take-001 | 8.5 | +0 | 68.6% | 66.9 | 29.7% | 28.3% | 35.2% |

Provenance: `Carl Douglas - Kung Fu Fighting (original).webm` · YouTube: Carl Douglas, https://www.youtube.com/watch?v=hq5REevpSP8 · Opus in WebM, 48 kHz · 03:17.701 · SHA-256 `b38e13db487ca51837c9701e5e785f87b3ea408bb4c0d6cfcbb1ba33587633d0` (verified)

## Bon Jovi - You Give Love a Bad Name (original)

Original as measured: centre E4, range G♯3–G5, core B3-G♯4 · drift 53.9 c · endings falling 60.0% · clean entries 40.3% · overshot 33.3%

| take | score (higher of two) | key vs original | melody within 50 c | drift | falling | clean | overshot |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-09-04-aaron-you-give-love-a-bad-name-take-001 | 9.4 | +0 | 71.7% | 57.0 | 50.0% | 29.5% | 37.2% |
| 2026-09-13-aaron-you-give-love-a-bad-name-take-001 | 6.7 | -1 | 65.8% | 85.7 | 46.7% | 21.7% | 33.1% |
| 2026-09-20-aaron-you-give-love-a-bad-name-bonnyview-take-001 | 6.8 | -1 | 66.2% | 110.2 | 60.0% | 19.1% | 33.3% |
| 2026-09-24-aaron-you-give-love-a-bad-name-take-001 | 7.6 | -1 | 65.2% | 126.7 | 66.7% | 13.8% | 33.6% |
| 2026-09-26-aaron-you-give-love-a-bad-name-redcliffe-leagues-club-open-mic-take-001 | 6.9 | +0 | 69.2% | 104.1 | 58.3% | 20.1% | 35.8% |
| 2026-10-02-aaron-you-give-love-a-bad-name-take-001 | 6.1 | +0 | 72.7% | 80.5 | 61.7% | 23.3% | 35.8% |
| 2026-10-03-aaron-you-give-love-a-bad-name-take-001 | 7.4 | +1 | 67.4% | 75.2 | 50.0% | 16.4% | 41.8% |
| 2026-10-09-aaron-you-give-love-a-bad-name-take-001 | 6.8 | +0 | 70.1% | 88.2 | 51.4% | 18.1% | 27.1% |

Provenance: `Bon Jovi - You Give Love a Bad Name (original).webm` · YouTube: Bon Jovi, https://www.youtube.com/watch?v=KrZHPOeOxQQ · Opus in WebM, 48 kHz · 03:50.601 · SHA-256 `73dec4261fe0cbef2c85df0b6427eeda28cfb78bce53d5fc97eb3db6116ea89e` (verified)

## John Farnham - Pressure Down (original)

Original as measured: centre C♯4, range E3–A♯5, core F♯3-F5 · drift 32.6 c · endings falling 28.6% · clean entries 58.8% · overshot 29.4%

| take | score (higher of two) | key vs original | melody within 50 c | drift | falling | clean | overshot |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-07-24-aaron-pressure-down-take-001 | 7.9 | -3 | 67.4% | 83.2 | 58.1% | 23.8% | 27.7% |
| 2026-07-24-aaron-pressure-down-take-002 | 7.8 | +1 | 63.4% | 81.4 | 45.2% | 23.7% | 33.3% |
| 2026-07-24-aaron-pressure-down-take-003 | 8.8 | +1 | 70.4% | 69.7 | 40.0% | 27.7% | 32.8% |
| 2026-07-24-aaron-pressure-down-take-004 | 8.4 | +1 | 68.9% | 66.5 | 51.0% | 24.2% | 35.2% |
| 2026-07-24-aaron-pressure-down-take-005 | 8.1 | -2 | 70.2% | 79.6 | 44.2% | 19.0% | 40.5% |
| 2026-07-24-aaron-pressure-down-take-006 | 7.6 | +0 | 73.3% | 67.3 | 43.8% | 25.0% | 33.3% |
| 2026-07-25-aaron-pressure-down-captain-cook-tavern-take-001 | 8.4 | -1 | 72.6% | 63.8 | 55.7% | 36.7% | 34.0% |
| 2026-07-25-aaron-pressure-down-take-007 | 7.6 | +0 | 68.7% | 69.8 | 52.9% | 25.8% | 35.9% |
| 2026-07-25-aaron-pressure-down-take-008 | 8.4 | -1 | 72.6% | 63.8 | 55.7% | 36.7% | 34.0% |
| 2026-08-01-aaron-pressure-down-take-009 | 7.8 | +0 | 67.8% | 74.4 | 42.9% | 29.4% | 31.9% |
| 2026-08-01-aaron-pressure-down-take-010 | 7.5 | +2 | 75.0% | 70.8 | 45.3% | 28.3% | 32.1% |
| 2026-08-04-aaron-pressure-down-take-001 | 7.6 | -2 | 69.1% | 71.9 | 57.1% | 31.2% | 20.0% |

Provenance: `John Farnham - Pressure Down (original).webm` · YouTube Music Topic: John Farnham, https://www.youtube.com/watch?v=tF0gqm4uUNo · Opus in WebM, 48 kHz · 03:47.381 · SHA-256 `91fb260c85d664354ef38e62fdf79e5a816e869cd254d05a94c86328da1195b7` (verified)

## Pitbull ft. John Ryan - Fireball (original)

Original as measured: centre C4, range A2–F♯5, core C♯3-C♯5 · drift 102.7 c · endings falling 48.6% · clean entries 23.2% · overshot 30.5%

| take | score (higher of two) | key vs original | melody within 50 c | drift | falling | clean | overshot |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-09-03-aaron-fireball-take-001 | 6.9 | +0 | 67.7% | 88.3 | 36.5% | 19.2% | 45.7% |
| 2026-09-11-aaron-fireball-take-001 | 7.7 | -2 | 60.7% | 89.1 | 51.2% | 19.4% | 43.1% |
| 2026-09-12-aaron-fireball-take-002 | 6.4 | -2 | 63.7% | 91.9 | 53.2% | 23.3% | 51.7% |
| 2026-09-12-aaron-fireball-take-003 | 7.9 | -4 | 66.9% | 77.1 | 36.6% | 26.4% | 34.2% |
| 2026-09-13-aaron-fireball-take-004 | 7.4 | +0 | 66.0% | 84.4 | 44.9% | 19.4% | 44.0% |
| 2026-09-26-aaron-fireball-take-001 | 6.8 | -2 | 57.9% | 71.2 | 51.9% | 21.4% | 39.3% |
| 2026-10-02-aaron-fireball-take-001 | 6.6 | +2 | 65.8% | 77.0 | 44.6% | 29.7% | 37.5% |

Provenance: `Pitbull ft. John Ryan - Fireball (original).webm` · YouTube: Pitbull, https://www.youtube.com/watch?v=If27FnxvjZA · Opus in WebM, 48 kHz · 03:56.221 · SHA-256 `9ee013fa7a9095f8bdda8f850b9acdc7d0df3990d6248fb7c11f7b94c7bcab94` (verified)

## Maneskin - Beggin' (original)

Original as measured: centre C♯4, range B2–G4, core F♯3-E4 · drift 81.0 c · endings falling 33.3% · clean entries 22.2% · overshot 33.3%

| take | score (higher of two) | key vs original | melody within 50 c | drift | falling | clean | overshot |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-04-28-aaron-beggin-take-002 | 7.3 | +0 | 74.5% | 93.3 | 53.8% | 24.4% | 34.7% |
| 2026-05-06-aaron-beggin-take-001 | 7.9 | +0 | 77.4% | 77.2 | 46.9% | 20.7% | 30.5% |

Provenance: `Maneskin - Beggin' (original).wav` · YouTube: Måneskin Official, https://www.youtube.com/watch?v=D557gnClcwc · PCM WAV, 48 kHz, 16-bit (from YouTube Opus source) · 03:30.760 · SHA-256 `dbc9f53a5c470f1bc6a8b43e305a06ec2fa7748b61dc84c0e2a77e99588d7841` (verified)

## The Temptations - My Girl (original)

Original as measured: centre C♯4, range A2–B4, core G3-G4 · drift 45.9 c · endings falling 48.8% · clean entries 41.7% · overshot 27.8%

| take | score (higher of two) | key vs original | melody within 50 c | drift | falling | clean | overshot |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-10-15-aaron-my-girl-bramble-take-001 | 9.4 | -1 | 70.5% | 51.2 | 38.7% | 36.0% | 28.0% |
| 2026-10-15-aaron-my-girl-take-001 | 8.2 | -1 | 75.3% | 82.9 | 37.5% | 16.7% | 32.4% |
| 2026-10-15-aaron-my-girl-take-002 | 8.5 | +0 | 64.9% | 80.1 | 29.0% | 20.6% | 30.8% |

Provenance: `The Temptations - My Girl (original).wav` · YouTube: The Temptations, https://www.youtube.com/watch?v=C7ht_xsRkAY · PCM WAV, 48 kHz, 16-bit (from YouTube Opus source) · 02:57.733 · SHA-256 `ef1bcde837d0be972b32fd9a1c668b1203ba5e3f633106ffd8b4b2635a7a895e` (verified)

## Dion - The Wanderer (original)

Original as measured: centre A3, range G2–F4, core C3-D♯4 · drift 38.1 c · endings falling 30.0% · clean entries 45.2% · overshot 33.0%

| take | score (higher of two) | key vs original | melody within 50 c | drift | falling | clean | overshot |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-10-15-aaron-the-wanderer-take-001 | 8.8 | +0 | 79.2% | 70.9 | 64.7% | 18.6% | 31.8% |
| 2026-10-15-aaron-the-wanderer-take-002 | 8.8 | +0 | 75.6% | 69.1 | 65.0% | 26.2% | 22.1% |
| 2026-10-15-aaron-the-wanderer-take-003 | 9.6 | +0 | 78.4% | 51.6 | 52.0% | 35.0% | 22.5% |

Provenance: `Dion - The Wanderer (original).wav` · YouTube: Dion, https://www.youtube.com/watch?v=SbYa7NBYyRc · PCM WAV, 48 kHz, 16-bit (from YouTube Opus source) · 02:43.707 · SHA-256 `0b2c32cc24affb35655c3aae308c6e0100c330dca157e9fc8c39fcaf429fa177` (verified)

## James Brown - I Got You (I Feel Good) (original)

Original as measured: centre G4, range G♯3–A5, core C♯4-D♯5 · drift 46.8 c · endings falling 23.5% · clean entries 40.7% · overshot 14.0%

| take | score (higher of two) | key vs original | melody within 50 c | drift | falling | clean | overshot |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-09-11-aaron-i-feel-good-take-001 | 7.2 | -2 | 62.4% | 124.5 | 63.3% | 19.0% | 45.7% |
| 2026-10-15-aaron-i-feel-good-take-001 | 6.8 | -1 | 64.9% | 131.4 | 79.5% | 16.0% | 43.0% |

Provenance: `James Brown - I Got You (I Feel Good) (original).wav` · YouTube: James Brown, https://www.youtube.com/watch?v=pTdihu-mp90 · PCM WAV, 48 kHz, 16-bit (from YouTube Opus source) · 02:45.593 · SHA-256 `41ac15f53e499590b24e57ed126cefea3cfe0f14471b35097e44e3b98293b2f8` (verified)

## Van Morrison - Brown Eyed Girl (original)

Original as measured: centre C4, range G3–A♯5, core G♯3-G♯5 · drift 54.6 c · endings falling 31.8% · clean entries 40.9% · overshot 14.8%

| take | score (higher of two) | key vs original | melody within 50 c | drift | falling | clean | overshot |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-10-15-aaron-brown-eyed-girl-take-001 | 7.1 | -2 | 63.0% | 168.4 | 68.4% | 8.9% | 33.7% |

Provenance: `Van Morrison - Brown Eyed Girl (original).wav` · YouTube: Van Morrison, https://www.youtube.com/watch?v=UfmkgQRmmeE · PCM WAV, 48 kHz, 16-bit (from YouTube Opus source) · 03:04.285 · SHA-256 `479d803ddc1dc857c35450339fde6e728cfec708ad9fd3d5a291f721e01f7896` (verified)

## Frankie Valli & The Four Seasons - December, 1963 (Oh, What a Night) (original)

Original as measured: centre F4, range F♯2–D♯5, core A♯3-A♯4 · drift 99.3 c · endings falling 52.2% · clean entries 28.3% · overshot 42.5%

| take | score (higher of two) | key vs original | melody within 50 c | drift | falling | clean | overshot |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-07-08-aaron-oh-what-a-night-take-001 | 7.9 | -1 | 64.6% | 78.5 | 39.3% | 20.5% | 36.9% |
| 2026-08-04-aaron-oh-what-a-night-take-001 | 8.5 | +0 | 69.0% | 72.7 | 41.2% | 26.5% | 36.3% |
| 2026-08-04-aaron-oh-what-a-night-take-002 | 8.0 | +1 | 56.7% | 66.2 | 35.7% | 27.4% | 37.2% |
| 2026-09-17-aaron-oh-what-a-night-bramble-instamic-first-live-take-001 | 7.7 | -1 | 62.8% | 69.3 | 35.9% | 29.4% | 34.3% |

Provenance: `Frankie Valli & The Four Seasons - December, 1963 (Oh, What a Night) (original).wav` · YouTube: Frankie Valli and the Four Seasons, https://www.youtube.com/watch?v=mTUhnIY3oRM · PCM WAV, 48 kHz, 16-bit (from YouTube Opus source) · 03:20.911 · SHA-256 `e075bd314ad86d83095efe41e31910623770a9bbff30f215af4142785249beed` (verified)

## Bill Withers - Ain't No Sunshine (original)

Original as measured: centre A3, range A2–G♯4, core G3-D♯4 · drift 63.5 c · endings falling 42.9% · clean entries 34.1% · overshot 24.2%

No Aaron takes yet — measured for song selection.

Provenance: `Bill Withers - Ain't No Sunshine (original).wav` · YouTube: Bill Withers, https://www.youtube.com/watch?v=YuKfiH0Scao · PCM WAV, 48 kHz, 16-bit (from YouTube Opus source) · 02:06.400 · SHA-256 `017ada87cec8ac1b51fcf91de5b8650b8f085c144f0dadcaf874b1b8e4831cd3` (verified)

## Maneskin - I Wanna Be Your Slave (original)

Original as measured: centre G3, range G♯2–D4, core G♯2-A♯3 · drift 44.9 c · endings falling 44.0% · clean entries 43.6% · overshot 20.0%

No Aaron takes yet — measured for song selection.

Provenance: `Maneskin - I Wanna Be Your Slave (original).wav` · YouTube: Måneskin Official, https://www.youtube.com/watch?v=yOb9Xaug35M · PCM WAV, 48 kHz, 16-bit (from YouTube Opus source) · 02:52.687 · SHA-256 `d974f50652fd6655b1f1a31d1dcfdb5a1f22c8178e99c4e65c54f53793683cb7` (verified)

## Teddy Swims - The Door (original)

Original as measured: centre D♯4, range F♯3–G5, core A♯3-G♯4 · drift 39.7 c · endings falling 33.3% · clean entries 39.8% · overshot 16.5%

No Aaron takes yet — measured for song selection.

Provenance: `Teddy Swims - The Door (original).wav` · YouTube: Teddy Swims, https://www.youtube.com/watch?v=VSXT4a2kRHA · PCM WAV, 48 kHz, 16-bit (from YouTube Opus source) · 03:31.476 · SHA-256 `96dcb101e382a9ac1afe8e31137617ac49edec26d332443a6364d8a45fcec2aa` (verified)

## Teddy Swims - Bad Dreams (original)

Original as measured: centre D♯4, range F3–C5, core G♯3-G4 · drift 54.7 c · endings falling 53.8% · clean entries 33.3% · overshot 21.4%

No Aaron takes yet — measured for song selection.

Provenance: `Teddy Swims - Bad Dreams (original).wav` · YouTube: Teddy Swims, https://www.youtube.com/watch?v=pAv3IXlKeNU · PCM WAV, 48 kHz, 16-bit (from YouTube Opus source) · 03:04.610 · SHA-256 `618afe87adca42535d6020f6e70f07f0b71fecf9a1257a9759106bfebc103d91` (verified)

