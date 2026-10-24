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

## Prompt to paste into Claude Code on your computer

```text
SIDE TASK: run this alongside whatever is already running in the background.
Do not stop, pause or interfere with that task.

Put Aaron's 19 analysis results from 23-25 Oct 2026 into Dropbox. Follow
docs/handoffs/FRANKIE_AARON_RESULTS_TO_DROPBOX_2026-10-25.md in goodermine/aaroncodex (it is on the branch of
PR #197, claude/voiceassist-plugin-planning-krhz0d, if not yet on main).

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
