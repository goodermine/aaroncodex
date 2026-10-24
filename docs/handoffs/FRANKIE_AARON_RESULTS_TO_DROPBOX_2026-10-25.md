# Handoff for Frankie: put Aaron's 19 results from 23–25 Oct into Dropbox

**From** Aaron (written by the cloud session) · **25 Oct 2026**

## Why

All 19 of Aaron's takes from 23–25 Oct are analysed: Frankie's 8 home takes are in PR #196, the cloud session's
11 from Gresh's place and the Captain Cook Tavern are in PR #197. Aaron has the results in chat; he now wants them
in Dropbox, as with earlier nights (`/From Claude/Song Analysis Results/17 Oct - Prince of Wales + Home/`).
The cloud session can only write text files to Dropbox, so the onset-map images need your machine.

## Where and how to name them

Folder (create it): `/From Claude/Song Analysis Results/23-25 Oct - Home, Gresh's + Captain Cook/`

For each take: `<Song> - Aaron - <Place> <D Mon> (results).txt` — the full `tools/show_results.py` output — and,
when the song has a reference original, `<Song> - Aaron - <Place> <D Mon> (onset map).png`.

| Take name (archive) | Results file name stem | PR |
|---|---|---|
| `2026-10-23-aaron-johnny-b-goode-take-001-home` | `Johnny B. Goode - Aaron - Home 23 Oct` | #196 |
| `2026-10-23-aaron-fireball-take-002-home` | `Fireball - Aaron - Home 23 Oct` | #196 |
| `2026-10-23-aaron-kung-fu-fighting-take-001-home` | `Kung Fu Fighting - Aaron - Home 23 Oct` | #196 |
| `2026-10-23-aaron-you-could-be-mine-take-001-home` | `You Could Be Mine - Aaron - Home 23 Oct` | #196 |
| `2026-10-23-aaron-let-s-stay-together-take-001-home` | `Let's Stay Together - Aaron - Home 23 Oct` | #196 |
| `2026-10-23-aaron-let-s-go-take-001-home` | `Let's Go - Aaron - Home 23 Oct` | #196 |
| `2026-10-23-aaron-play-that-funky-music-take-002-home` | `Play That Funky Music - Aaron - Home 23 Oct` | #196 |
| `2026-10-23-aaron-tnt-take-001-home` | `TNT - Aaron - Home 23 Oct` | #196 |
| `2026-10-24-aaron-get-ready-for-this-take-001-greshs-place` | `Get Ready for This - Aaron - Greshs 24 Oct` | #197 |
| `2026-10-24-aaron-you-could-be-mine-take-001-greshs-place` | `You Could Be Mine - Aaron - Greshs 24 Oct` | #197 |
| `2026-10-24-aaron-are-you-gonna-be-my-girl-take-001-greshs-place` | `Are You Gonna Be My Girl - Aaron - Greshs 24 Oct` | #197 |
| `2026-10-24-aaron-fireball-take-001-greshs-place` | `Fireball - Aaron - Greshs 24 Oct` | #197 |
| `2026-10-24-aaron-tnt-take-001-greshs-place` | `TNT - Aaron - Greshs 24 Oct` | #197 |
| `2026-10-24-aaron-these-boots-are-made-for-walkin-take-001-greshs-place` | `These Boots Are Made for Walkin' - Aaron - Greshs 24 Oct` | #197 |
| `2026-10-24-aaron-tnt-take-002-captain-cook-tavern` | `TNT - Aaron - Captain Cook 24 Oct` | #197 |
| `2026-10-24-aaron-working-class-man-take-001-captain-cook-tavern` | `Working Class Man - Aaron - Captain Cook 24 Oct` | #197 |
| `2026-10-24-aaron-working-class-man-take-002-greshs-place` | `Working Class Man - Aaron - Greshs 24 Oct` | #197 |
| `2026-10-25-aaron-fortunate-son-take-001-greshs-place` | `Fortunate Son - Aaron - Greshs 25 Oct` | #197 |
| `2026-10-25-aaron-every-morning-take-001-greshs-place` | `Every Morning - Aaron - Greshs 25 Oct` | #197 |

Also add `00 - Scores (23-25 Oct).txt`: the 19 headline scores, highest first, each as
`<Song> (<Place>, <date>): <overall> overall · <capture-fair> capture-fair`, with the line
"10 = a typical pro (calibrated to 50 professional vocals)" at the top. Lead with the higher number as the reports'
`Lead with:` line says (every one of these 19 leads with overall).

## The recordings were renamed again (25 Oct, Aaron's choice)

The cloud session renamed all 18 of Aaron's recordings in `/Song_Analysis/Aaron/` to his usual style,
`<Song> - Aaron - <Place> <D Month>.wav`, without the camera stamp (Wake Me Up Before You Go-Go,
`audio_261023_192103_32bit_orig.wav`, is untouched until Aaron knows who sang it). PR #197's notes are updated.
The 8 notes in **your PR #196** still cite the first-round names, so update them:

| Note in #196 cites | Now called |
|---|---|
| `2026-10-23 - Johnny B. Goode - Aaron - Home (audio_261023_181751).wav` | `Johnny B. Goode - Aaron - Home 23 October.wav` |
| `2026-10-23 - Fireball - Aaron - Home (audio_261023_182510).wav` | `Fireball - Aaron - Home 23 October.wav` |
| `2026-10-23 - Kung Fu Fighting - Aaron - Home (audio_261023_183135).wav` | `Kung Fu Fighting - Aaron - Home 23 October.wav` |
| `2026-10-23 - You Could Be Mine - Aaron - Home (audio_261023_183851).wav` | `You Could Be Mine - Aaron - Home 23 October.wav` |
| `2026-10-23 - Let's Stay Together - Aaron - Home (audio_261023_185045).wav` | `Let's Stay Together - Aaron - Home 23 October.wav` |
| `2026-10-23 - Let's Go - Aaron - Home (audio_261023_191230).wav` | `Let's Go - Aaron - Home 23 October.wav` |
| `2026-10-23 - Play That Funky Music - Aaron - Home (audio_261023_194122).wav` | `Play That Funky Music - Aaron - Home 23 October.wav` |
| `2026-10-23 - TNT - Aaron - Home (audio_261023_201955).wav` | `TNT - Aaron - Home 23 October.wav` |

Write it as `Dropbox source '/Song_Analysis/Aaron/<new name>' (Insta360 file audio_2610xx_xxxxxx)`, as #197 does,
so the camera original can still be matched. Wording only: no re-analysis, no score change.

## Prompt to paste into Claude Code on your computer

```text
SIDE TASK: run this alongside whatever is already running in the background.
Do not stop, pause or interfere with that task.

Put Aaron's 19 analysis results from 23-25 Oct 2026 into Dropbox. Follow
docs/handoffs/FRANKIE_AARON_RESULTS_TO_DROPBOX_2026-10-25.md in goodermine/aaroncodex (it is on the branch of
PR #197, claude/voiceassist-plugin-planning-krhz0d, if not yet on main).

0. On your branch frankie/aaron-home-2026-10-23 (PR #196), update the 8 take_context notes to the new Dropbox
   names in the handoff's rename table (wording only), run python3 tools/score_preflight.py, commit
   "chore: point the 8 home takes at Aaron's final Dropbox file names" and push.
1. git fetch origin. Make a scratch worktree from origin/main and bring in the 19 analysis JSONs from the two PR
   branches without merging anything:
     git checkout origin/frankie/aaron-home-2026-10-23 -- voxanalysis/archive/scratch-analyses/2026-10-23-aaron-*-home_analysis.json
     git checkout origin/claude/voiceassist-plugin-planning-krhz0d -- voxanalysis/archive/scratch-analyses/2026-10-2[45]-aaron-*_analysis.json
   python3 tools/score_preflight.py (must exit 0).
2. For each take in the handoff's table: python3 tools/show_results.py <take> > "<stem> (results).txt".
   If it renders Onset-Map-<take>.png, rename that to "<stem> (onset map).png".
3. Create Dropbox "/From Claude/Song Analysis Results/23-25 Oct - Home, Gresh's + Captain Cook/" and copy the
   19 results files, the onset maps and "00 - Scores (23-25 Oct).txt" into it.
4. Never delete, rename or move anything else in Dropbox, and never commit these scratch files.
5. Tell Aaron the folder is ready and list the files.
```
