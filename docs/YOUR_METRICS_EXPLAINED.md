# Read your own metrics

*Generated from the live calibration pack by `tools/metric_glossary.py`. Re-run it after any re-calibration so the numbers are never stale.*

Every measured number is compared to **50 professional reference vocals**. The ranges below are:

- **weak pro (p10)** — bottom 10% of the professionals
- **typical (p50)** — a middle-of-the-pack professional. **This is what "10 / 10" anchors to** — you are measured against a working pro, not against perfection.
- **strong pro (p90)** — top 10%

So a 7 is a genuinely good singer. The scale was never zero-to-hero; it is zero-to-*professional*.

---

## How clean the tone is

### HNR — clean tone vs breath

How much of your sound is pure tone versus air and noise. Higher is cleaner. A low number means breathy or fuzzy — though a room or phone mic drags this down too, so it is judged gently on live takes.

> **Pros:** weak 9.458 · typical **13.64** · strong 18.224 dB  ·  _higher is better_

### CPPS — clarity and ring

How well-defined and 'present' the tone is — the difference between a dull sound and a ringing one. This is the number that jumps when a voice comes into focus.

> **Pros:** weak 13.683 · typical **15.395** · strong 16.927 dB  ·  _higher is better_

### Jitter — pitch steadiness

Tiny cycle-to-cycle wobbles in pitch. Lower is steadier. High jitter reads as an unsteady, effortful tone. Sensitive to recording quality.

> **Pros:** weak 0.6106 · typical **0.8538** · strong 1.3327 %  ·  _lower is better_

### Shimmer — loudness steadiness

The same idea as jitter but for loudness — tiny wobbles in volume cycle-to-cycle. Lower is steadier.

> **Pros:** weak 5.6024 · typical **9.4492** · strong 14.3784 %  ·  _lower is better_

## Pitch

### Pitch centre — how in-tune

How far you sit from the nearest correct note, in cents (100 cents = one semitone). Lower is more accurate. Note the pros are NOT at zero — dead-perfect pitch sounds robotic; humans sit slightly off and it reads as musical.

> **Pros:** weak 10 · typical **20** · strong 20 cents  ·  _lower is better_

### Held-note drift — does it stay put

How much a note slides around WHILE you hold it. Lower is steadier. This is different from pitch centre: you can start in tune and still drift.

> **Pros:** weak 14.38 · typical **24.25** · strong 52.35 cents  ·  _lower is better_

## Breath — Aaron's ceiling

### Phrase endings that sag

The share of phrase-ends where the pitch slides off as the air runs out. Lower is better — but even pros sag on about a third of endings, because a falling ending is partly a style choice. This is the measured limiter on Aaron's voice: it runs near the top of the pro range.

> **Pros:** weak 23.19 · typical **33.3** · strong 45.62 %  ·  _lower is better_

### Phrase length — how long you sustain

How long your phrases run before a breath. Longer needs more breath management; shorter is a valid pop/rock style, not a fault.

> **Pros:** weak 1.639 · typical **3.8** · strong 6.813 s  ·  _a dial, not a score — depends on the sound you want_

## Vibrato

### Vibrato rate — how fast the wobble

Wobbles per second. Too slow reads as a wobble; too fast reads as nervous. There is a natural band pros sit in.

> **Pros:** weak 4.877 · typical **5.41** · strong 5.99 Hz  ·  _a dial, not a score — depends on the sound you want_

### Vibrato width — how wide the wobble

How far the pitch swings on each wobble. A stylistic choice, not a score.

> **Pros:** weak 52.55 · typical **64.1** · strong 78.02 cents  ·  _a dial, not a score — depends on the sound you want_

### Vibrato usage — how often

The share of long notes carrying vibrato. Straight tone is a valid style; this is not a target to max out.

> **Pros:** weak 40.36 · typical **53.2** · strong 63.99 %  ·  _a dial, not a score — depends on the sound you want_

## Loudness and shape

### Dynamic range — soft to loud

The gap between your quietest and loudest singing. Higher is more expressive; a flat, one-volume performance scores low. Moved by compression and mastering, so judged gently on processed audio.

> **Pros:** weak 18.398 · typical **26.965** · strong 36.303 dB  ·  _higher is better_

---

## Diagnostics (measured, but not scored)

These are reported to help you understand the sound, but they are not part of any score — they are dials or unanchored readings.

### H1−H2 — breathy vs pressed

How firmly your vocal folds close. Your voice makes a fundamental (the note, H1) plus overtones; H2 is the second overtone. H1−H2 is simply how much LOUDER the fundamental is than that second overtone.

  * Big positive (around +20 dB) = folds barely closing, air escaping = BREATHY. Weak falsetto lives here.
  * Near zero or negative (−10 to −15 dB) = folds closing firmly, long closed phase = PRESSED and rich. Overdrive lives here.

It is a DIAL, not a score — breathy suits a tender verse, pressed suits a belt. When a note 'falls out' and goes airy, that is H1−H2 climbing toward breathy. Measured on Aaron's own CVT reference test it swung from +22 dB (breathy) to −14 dB (pressed) — the whole weak-vs-reinforced-falsetto story in one number.

### Metallic index — how much 'ring' / metal

A composite of the spectral 'ring' measures (2–4 kHz energy, brightness, clarity, adduction). Higher = more metallic, carrying, present. It reports HOW MUCH metal, never WHICH vocal mode — all the loud modes are metallic, and telling them apart from one recording is not reliable. Scored within one file only, never compared across recordings.

### Singer's formant — carrying power

A cluster of energy around 2–4 kHz that lets a voice cut through without extra volume — the 'ring' that carries over an orchestra. Not yet anchored to the pro pack, so reported as a reading rather than a score.

---

## The two honest caveats

1. **These ranges move when the pack is rebuilt.** The *meanings* above never change; the *numbers* are read live from the calibration pack, so re-running this script after a re-calibration keeps them true. If a number here ever disagrees with a fresh report, re-run the script.
2. **Some metrics measure the microphone, not the voice.** HNR, CPPS, jitter and shimmer get dragged down by a room or phone recording — which is why live takes lead with the **capture-fair** score, which sets those aside. A low voice-quality number on a tavern take is usually the room, not you.

