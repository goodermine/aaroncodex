# Handoff for Frankie: analyse Aaron's 8 home takes from 23 Oct 2026

**From** Aaron (written by the cloud session) · **25 Oct 2026**

## Why

Aaron uploaded 19 unlabelled Insta360 recordings. The cloud session identified every song from its lyrics,
renamed the files in Dropbox (with Aaron's approval) and split the analysis so both machines work at once:

- **Frankie (this handoff):** the 8 home takes from Friday 23 Oct, below.
- **Cloud session:** the 11 takes from Gresh's place and the Captain Cook Tavern (24–25 Oct), cut from two long
  recordings and checked against the voice prints.

A ninth file from the 23rd, `audio_261023_192103_32bit_orig.wav` (Wake Me Up Before You Go-Go), is **not Aaron**.
Leave it alone: Aaron will listen and say who sang it.

## The takes

All in Dropbox `/Song_Analysis/Aaron/`. Insta360 mic, 32-bit float, mono 48 kHz. Recorded at Aaron's home on the
evening of Friday 23 Oct 2026, 6:17 pm to 8:19 pm, before the Brighton Hotel. Ear monitor and warm-up not recorded.

| Take name | Dropbox file | Length | Notes from the transcript |
|---|---|---|---|
| `2026-10-23-aaron-johnny-b-goode-take-001-home` | `2026-10-23 - Johnny B. Goode - Aaron - Home (audio_261023_181751).wav` | 1:51 | Singing from ~0:19 to ~1:27; short take |
| `2026-10-23-aaron-fireball-take-002-home` | `2026-10-23 - Fireball - Aaron - Home (audio_261023_182510).wav` | 4:09 | Starts singing almost at once; ends ~4:03 |
| `2026-10-23-aaron-kung-fu-fighting-take-001-home` | `2026-10-23 - Kung Fu Fighting - Aaron - Home (audio_261023_183135).wav` | 3:22 | Intro "oohs" from ~0:02 are sung, keep them; ends ~3:05 |
| `2026-10-23-aaron-you-could-be-mine-take-001-home` | `2026-10-23 - You Could Be Mine - Aaron - Home (audio_261023_183851).wav` | 5:41 | ~1:00 instrumental intro; "How you doing?" at ~5:40 is talk |
| `2026-10-23-aaron-let-s-stay-together-take-001-home` | `2026-10-23 - Let's Stay Together - Aaron - Home (audio_261023_185045).wav` | 3:21 | Singing from ~0:30 |
| `2026-10-23-aaron-let-s-go-take-001-home` | `2026-10-23 - Let's Go - Aaron - Home (audio_261023_191230).wav` | 3:19 | The Cars; singing from the start to ~3:12 |
| `2026-10-23-aaron-play-that-funky-music-take-002-home` | `2026-10-23 - Play That Funky Music - Aaron - Home (audio_261023_194122).wav` | 4:59 | Album version; "Wow!" at ~4:56 |
| `2026-10-23-aaron-tnt-take-001-home` | `2026-10-23 - TNT - Aaron - Home (audio_261023_201955).wav` | 3:25 | Singing ~0:30 to ~3:10; chat after ~3:14 |

`take-002` for Fireball and Play That Funky Music because `take-001-brighton` already exists for 23 Oct. These
home takes are different recordings: the Brighton analyses are longer than these whole files.

Transcript timings are approximate (Whisper base.en, first 130 s and last 30 s of each file). There is talk before
and sometimes inside songs: `talk_cut.py` handles it (it cuts talk out and joins the singing, the repo's tested
method). Check its plan against the notes above and correct the edges by hand where it clips a sung word.

## Prompt to paste into Claude Code on your computer

```text
SIDE TASK: run this alongside whatever is already running in the background.
Do not stop, pause or interfere with that task.

Analyse Aaron's 8 home takes from 23 Oct 2026. Follow docs/handoffs/FRANKIE_AARON_HOME_TAKES_2026-10-23.md
in goodermine/aaroncodex if it is on main; otherwise everything you need is in this prompt and the take table
Aaron pastes with it. Follow docs/handoffs/ANALYSIS_RUNBOOK.md for each step.

1. git fetch origin && git checkout -B frankie/aaron-home-2026-10-23 origin/main
   python3 tools/score_preflight.py  (must exit 0)
2. Download the 8 files from Dropbox /Song_Analysis/Aaron/ (names in the table). Do NOT touch
   audio_261023_192103_32bit_orig.wav (not Aaron), and never delete or rename anything in Dropbox.
3. For each: scale the float peak to -1 dBFS, save as <take name>.wav, separate with
   voxanalysis/vox-analysis/engine/tools/stems/batch_stems.sh (pinned RoFormer, run from the engine dir).
4. Run engine/talk_cut.py on each vocal stem with --plan. Check the kept window against the table's transcript
   notes and correct the edges by hand if it clips a sung word or keeps talk. Save the cut stem as
   <take name>_(vocals)_vocals_mel_band_roformer.wav in one folder.
5. python3 tools/analyse_takes.py <that folder> --stems-only --write --force
6. Stamp each JSON: take_context = {"intent": "performance", "capture": "home", "milestone": null,
   "superseded": false, "note": "Aaron at home, Friday 23 Oct 2026 (<time> pm, before the Brighton Hotel);
   <Song (Artist)>, karaoke backing. Insta360 mic (32-bit float, mono 48 kHz); ear monitor and warm-up not
   recorded. Dropbox source '<file>' (<length> s, peak <x> dBFS; scaled by <g> dB to -1 dBFS before RoFormer
   separation). talk_cut kept <a>-<b>[; edges corrected by hand: why]."} and audio_prep.talk_cut = the plan
   (method, status, kept, offset_s, removed with kind/text, transcript, duration_s, removed_s). Write with
   json.dump(..., indent=2), no trailing newline, as analyse_takes does.
7. python3 docs/score-metrics/retire_legacy_scores.py && python3 docs/score-metrics/rescore_all.py
   python3 tools/score_preflight.py --update && python3 tools/score_preflight.py  (must exit 0)
   python3 tools/check_take_integrity.py  (advisory; report anything it flags)
8. One commit per take JSON, then one commit for the score tables; push; open a PR to main titled
   "Analyse Aaron's 8 home takes (23 Oct)". If main has moved by the time you merge, re-run rescore_all
   after merging main so the tables cover the cloud session's 11 takes too.
9. Deliver: run python3 tools/show_results.py <take> for each and paste the full output to Aaron (CLAUDE.md
   rules 6 and 8), leading each with the higher of overall / capture-fair, confidence, "10 = a typical pro".
   The cloud session will also fold these 8 into its combined summary for Aaron.
```
