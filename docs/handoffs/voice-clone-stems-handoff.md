# Handoff: Locate isolated vocal stems for Kits.ai voice clone

**Date:** 2026-08-06
**From:** Carson (session `claude/voiceassist-plugin-planning-krhz0d`)
**To:** Mary
**Priority:** When convenient — Aaron has a chest infection and is resting this week

---

## What Aaron needs

A voice clone on **Kits.ai** built from his best singing. Requirements:

- **Minimum 15 minutes** of high-quality audio (we have ~35 minutes selected)
- **Dry isolated vocals only** — no reverb, no backing tracks, no harmonies
- **Stem-separated** if the original recording has any bleed or backing
- WAV format preferred, highest quality available

## The 10 selected takes

These are Aaron's highest-scoring takes with voice quality 9+, chosen for
variety across songs and vocal range. The analysis JSONs are in
`voxanalysis/archive/scratch-analyses/` — **the audio files are NOT in the
repo** (rule 9). You need to locate the original recordings from Aaron's
devices or Dropbox and stem-separate them.

| # | Song | Score | VQ | Duration | Analysis file |
|---|------|:-----:|:--:|:--------:|---------------|
| 1 | Oh What A Night | 9.4 | 10.0 | 3.5m | `2026-08-04-aaron-oh-what-a-night-take-001_analysis.json` |
| 2 | Pressure Down | 9.2 | 10.0 | 3.8m | `2026-07-24-aaron-pressure-down-take-003_analysis.json` |
| 3 | Do Wah Diddy | 9.1 | 10.0 | 2.4m | `2026-08-04-aaron-do-wah-diddy-take-003_analysis.json` |
| 4 | Pressure Down (take 1) | 9.0 | 10.0 | 4.0m | `2026-07-24-aaron-pressure-down-take-001_analysis.json` |
| 5 | 3am | 8.9 | 10.0 | 4.7m | `2019-12-31-aaron-3am-take-001_analysis.json` |
| 6 | My Babe | 8.6 | 10.0 | 2.6m | `2026-07-16-aaron-my-babe-take-001_analysis.json` |
| 7 | Kryptonite | 8.8 | 10.0 | 3.9m | `2026-07-27-aaron-kryptonite-take-001_analysis.json` |
| 8 | Lose Control | 8.7 | 9.8 | 3.5m | `2019-12-31-aaron-lose-control-take-001_analysis.json` |
| 9 | Play That Funky Music | 8.7 | 9.9 | 3.4m | `2026-07-25-aaron-play-that-funky-music-take-001_analysis.json` |
| 10 | Danger Zone (New Studio) | 8.7 | 9.1 | 3.6m | `2026-07-11-aaron-danger-zone-new-studio-take-002_analysis.json` |
| 11 | Kung Fu Fighting | 8.6 | 9.2 | 3.4m | `2026-08-04-aaron-kung-fu-fighting-take-001_analysis.json` |
| 12 | One | 8.6 | 9.3 | 3.5m | `2026-07-24-aaron-one-take-001_analysis.json` |
| 13 | You Sexy Thing | 8.5 | 9.4 | 2.9m | `2026-07-30-aaron-you-sexy-thing-take-001_analysis.json` |

**Total: ~45 minutes** across 12 different songs.

Items 11–13 were added on 2026-08-06 (Aaron's request: "a really good take of
kung fu fighting and two others"). They add three distinct textures the
funk-heavy top 10 was light on — mid funk (Kung Fu Fighting), a sustained
ballad (One), and upper-register funk (You Sexy Thing). All three are clean
VQ-9+ takes.

## Where the originals might be

- **2026-08-04 takes** (Oh What A Night, Do Wah Diddy): recorded on TazCam
  mixer (MP3) and phone (M4A). The TazCam versions are preferred — higher
  voice quality scores. Check Dropbox for the Aug 4 session files.
- **2026-07-24/25 takes** (Pressure Down x2, Play That Funky Music): check
  Dropbox July uploads.
- **2026-07-27** (Kryptonite), **2026-07-16** (My Babe),
  **2026-07-11** (Danger Zone): check Dropbox July uploads.
- **2026-08-04** (Kung Fu Fighting take-001): same Aug 4 session as Oh What A
  Night / Do Wah Diddy — TazCam and phone versions likely both exist.
- **2026-07-24** (One), **2026-07-30** (You Sexy Thing): check Dropbox July
  uploads. You Sexy Thing has a Hot Chocolate reference already analysed, so
  the original vocal is well characterised for a quality cross-check.
- **2019-12-31 takes** (3am, Lose Control): these are older recordings —
  Aaron may need to check his phone/computer archives for these.

## What to do with each file

1. **If the recording is already an isolated vocal** (recorded dry with
   headphones, no speakers): it may be usable as-is. Check for room echo
   or backing track bleed.
2. **If there's any bleed or backing track**: stem-separate with RoFormer
   to extract the vocal. The repo has stem separation tooling.
3. **Output format**: WAV, highest sample rate available. Name each file
   clearly: `aaron-[song]-voice-clone.wav`
4. **Upload**: put the finished stems in a Dropbox folder Aaron can point
   Kits.ai at, or concatenate them into one file if Kits.ai prefers that.

## Quality check

Each stem should be:
- [ ] Dry (no reverb, no room echo)
- [ ] Isolated (no backing track, no harmonies)
- [ ] Clean (no clipping, no heavy compression artefacts)
- [ ] Aaron's voice only (no other singers)

If a take's original audio can't be found, skip it — we have 35 minutes
of material, so losing one or two still clears the 15-minute minimum.

## Do NOT

- Commit audio files to the repo (rule 9)
- Re-analyse or re-score anything — the scores are already verified
- Modify any analysis JSONs
