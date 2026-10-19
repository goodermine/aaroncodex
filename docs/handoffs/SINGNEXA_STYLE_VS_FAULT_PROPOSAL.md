# Proposal — stop Singnexa marking deliberate rock/soul style as faults

**Status:** PROPOSAL ONLY — nothing in this document has been implemented.
Aaron decides; no rubric, measurement or calibration change happens without his
explicit go-ahead (CLAUDE.md rule 1).
**Written:** 19 Oct 2026 · **Raised by:** Frankie (a9max smoke test) · **Context:** Singnexa beta (#140)

---

## The problem, in one paragraph

The first live Singnexa test on a9max was a rock vocal — *Born To Be Wild*
(Steppenwolf), 3:09, home capture — and it scored **7.2 overall / 6.1
capture-fair** (high confidence). The components that pulled it down are the
ones a rock singer moves *on purpose*: **held-note stability 0.0**, **breath
support 2.38**, **clean entries 18.9 %** with **44 % scooped** (entries are
diagnostic only, not in the score). Before outside testers upload rock, soul or
blues, we should decide whether that is a fair reading or the engine mistaking
style for a fault.

## What is actually true today (checked in the code and the pack)

1. **The pros the scale is built on do include rock** — Bon Jovi, Aerosmith,
   Journey, 3 Doors Down, The Offspring, Joe Cocker (×2), John Farnham, Queen,
   Hozier, Teddy Swims (×2) — but the 50-reference pack
   (`engine/calibration/pro_reference.json`) **leans towards ballads and pop
   divas** (Whitney, Mariah, Céline ×2, Adele, Idina Menzel, Sia, Beyoncé …).
   So "matches or beats N % of pros" on drift and scoops is measured against a
   mostly-ballad yardstick.
2. **The breath measure is pitch-only.** `analyse_breath()` (`analyse_song.py`
   ≈ line 1879) flags a phrase ending when the pitch falls > 40 cents with a
   slope steeper than −60 c/s over the last 0.5 s. Its docstring says "pitch
   sags *and energy collapses*", but **energy is never checked**. A deliberate
   fall-off (sung at full volume) and air running out (volume dying with the
   pitch) are scored the same. The function's own note already says
   "intentional fall-offs are common in rock/soul — judge by ear".
3. **We have measured this on originals already.** In the 16 Oct
   originals comparison (`docs/score-metrics/comparisons/2026-10-16-aaron-vs-originals-batch.md`)
   the original singers' *own* phrase endings "fall" at: Bon Jovi 60 %, Teddy
   Swims (*Bad Dreams*) 54 %, Frankie Valli 52 %, The Temptations 49 %,
   Bill Withers 43 % — style, not lack of air.
4. **Held-note stability** is median intra-note drift against the pack; bends,
   scoops-into and growl on held notes all count as drift. A 0.0 means the
   take drifted more than nearly every pro in the pack.

So: part of the low reading is genuine (it is a real measurement and the singer
may well have room to improve), and part is the yardstick and a measurement
that cannot tell style from fatigue. The breath measure is the clearest
measurement gap.

## Options (Aaron to choose; can combine)

### Option 1 — Explain it on the results page (recommended for the beta, now)

No change to any number. Add a short, plain-English note on Singnexa results
when the take shows the pattern (e.g. scoops ≥ 40 % or falling endings ≥ 50 %
or held-note stability below 3):

> *Rock, soul and blues singers bend into notes and let line-endings fall on
> purpose. Our scale is built on 50 professional vocals, many of them ballads,
> so deliberate style can read as wobble or running out of air. Listen at the
> timestamps — if it was on purpose, it's style, not a fault.*

- Effort: small (results page + test). Risk: none to scores or the archive.
- Satisfies rule 7 (don't coach off an artefact) for the public product.

### Option 2 — Make the breath measure check energy too (engine change)

Count a phrase ending as "sagging" only when the pitch falls **and** the level
collapses (e.g. RMS in the last 0.5 s drops > X dB relative to the phrase
body). Report the pure-pitch falls separately as "stylistic fall-offs".

- Effort: medium. Needs: the change in `analyse_breath()`, unit tests,
  re-analysis of the 50-pro calibration pack (new measurement fingerprint),
  re-scoring the archive (`retire_legacy_scores.py`, `rescore_all.py`),
  `score_preflight.py --update`, and a written note of the score shift.
- **Scores move.** Every archived breath score changes; trends across the
  change need the era rule (rule 3).
- Best done with a before/after table on ~20 takes (rock and ballad) so Aaron
  can see the effect before it ships.

### Option 3 — Genre-aware yardstick (largest)

Calibrate against the pros of the same style (rock/soul vs ballad/pop), or
weight the pack by genre.

- Effort: large. Needs more rock/soul references (the pack has ~11 that fit),
  a genre tag on uploads, and a decision on how a singer's "one number" works
  across genres. Changes the meaning of "10 = a typical pro".
- Worth doing only after Option 2, and only if Option 1's note isn't enough.

## Recommendation

1. **Now:** Option 1 (wording only) before inviting outside testers.
2. **Next:** Option 2 as its own PR with the before/after table for Aaron to
   approve — it fixes a real measurement gap, not just presentation.
3. **Later, maybe:** Option 3, only with more rock/soul reference vocals.

## Also open (small, separate)

- **PR #160** (draft): `/healthz` reports the deployed code commit. Answers
  Frankie's question — the report's "build 7cbd02df8f62" is the **scorer's
  rubric fingerprint** (pinned in `SCORE_CONTRACT.json`), identical on every
  correct deploy, not the code commit. No scoring change.
- **PR #159** (draft, another session): `AGENTS.md` into `.dockerignore`, to fix
  the a9max build ("invalid file request AGENTS.md"). Frankie will verify it at
  the next Singnexa rebuild.
- **Speed:** a9max took 12 min 8 s for a 3:09 song (≈ 3.8× real time) — the
  same as a 4-CPU box, so extra cores don't help; a GPU is the lever (~5
  songs/hour today).

## Where the beta stands (19 Oct 2026)

Installed by Frankie on a9max, tailnet-only at
`https://a9max.tail8e8c02.ts.net:8451/` (8443 belongs to karaokemaker), main
`bacd64b`, healthz `{"ok":true,"scores_published":true}`, Aaron's admin account
set up. Not public; no funnel.
