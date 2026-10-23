# Handoff for Frankie: ear-check the 7 suspect genre-reference stems

**From** Aaron (written by the cloud session) · **23 Oct 2026**

## Why

The engine flags 7 of the genre-reference originals as **suspect**. Each has a rough signal (low HNR) and, at the same time, better-than-90%-of-pros pitch behaviour: very clean entries and very steady held notes. That combination is the engine's signature for a pitch tracker that followed the band instead of the singer (`analyse_song.py`, entry-accuracy validity gate).

Until someone listens, `tools/genre_reference_summary.py` leaves them out of every genre median (see `docs/plans/GENRE_REFERENCE_SUMMARY_2026-10-22.md`). Four of the seven are rock'n'roll, so that genre currently stands on only 8 references.

| # | Reference (analysis in `voxanalysis/archive/scratch-analyses/`) | HNR dB | held drift c | clean entries |
|---|---|---|---|---|
| 1 | `2026-10-22-elvis-presley-dont-be-cruel-reference` | 10.1 | 53 | 47% |
| 2 | `2026-10-22-del-shannon-runaway-reference` | 12.0 | 38 | 46% |
| 3 | `2026-10-22-bobby-darin-dream-lover-reference` | 7.5 | 42 | 47% |
| 4 | `2026-10-22-wanda-jackson-lets-have-a-party-reference` | 10.8 | 28 | 58% |
| 5 | `2026-10-22-nirvana-smells-like-teen-spirit-reference` | 10.9 | 44 | 49% |
| 6 | `2026-10-22-the-angels-am-i-ever-gonna-see-your-face-again-reference` | 7.9 | 41 | 49% |
| 7 | `2026-10-22-the-isley-brothers-shout-reference` | 9.2 | 32 | 44% |

The flag is a heuristic. Old 1950s–60s masters (tape hiss, slapback echo) can read rough while the singer really is that steady. **Only a listen settles it.**

## What a verdict means

| Verdict | Meaning | Effect |
|---|---|---|
| `clean` | Mostly the lead voice. Slapback echo or a little bleed is fine | Counted in the genre medians again |
| `mixed` | Voice plus a clearly audible instrument or backing vocal for long stretches | Left out |
| `band` | Mostly instruments | Left out; replace the song if the genre needs the numbers |

The verdict lives in each reference JSON as a top-level field, which the summary tool reads:

```json
"reference_check": {"stem": "clean", "by": "Aaron", "date": "2026-10-2x", "note": "slapback echo, voice clear"}
```

Don't re-separate with a different model. The archive is pinned to RoFormer (preflight check 4), so a `band` stem is dropped, not swapped.

## Prompt to paste into Claude Code on your computer

```text
SIDE TASK: run this alongside whatever is already running in the background.
Do not stop, pause or interfere with that task.

Aaron needs to listen to 7 separated vocal stems from the genre-reference originals and tell us whether
each is the singer or the band. Follow docs/handoffs/FRANKIE_SUSPECT_REFERENCE_STEMS_2026-10-23.md in
goodermine/aaroncodex (pull main first).

1. For each of the 7 references in the table, find the RoFormer vocal stem you made when you analysed it
   (its file name is the "file_name" field of the analysis JSON, e.g.
   2026-10-22-elvis-presley-dont-be-cruel-reference_(vocals)_vocals_mel_band_roformer.flac).
   If a stem is gone, re-separate that original from Dropbox "/Song_Analysis/Originals for analysis -
   DELETE AFTER/" with voxanalysis/vox-analysis/engine/tools/stems/batch_stems.sh (pinned RoFormer),
   scaling float peaks to -1 dBFS first as usual. Don't re-run the analysis.
2. Make a 192 kbps MP3 listening copy of each vocal stem, named "<Artist> - <Song> (vocal stem).mp3",
   and put all 7 in Dropbox "From Claude/Reference stem check (23 Oct)/" (create it).
   Tell Aaron they're there and ask him for one word per song: clean, mixed or band
   (clean = mostly the lead voice, echo is fine; mixed = an instrument or backing vocal clearly there for
   long stretches; band = mostly instruments).
3. When he answers, add his verdict to each reference JSON as a top-level field:
   "reference_check": {"stem": "<verdict>", "by": "Aaron", "date": "<YYYY-MM-DD>", "note": "<his words>"}
   Write it with json.dump(..., indent=2) and change nothing else in the file.
4. Run: python3 tools/genre_reference_summary.py > /tmp/genre_data.md, then replace the section from
   "## Data" to the end of docs/plans/GENRE_REFERENCE_SUMMARY_2026-10-22.md with it. Add one line under
   "What it shows" saying which stems were confirmed clean and which were dropped, and how the
   rock'n'roll and hard-rock medians moved. Then run python3 tools/score_preflight.py (must pass).
5. One commit for the 7 verdicts plus one for the summary, on a branch, and open a PR to main.
6. NEVER delete or modify anything in Dropbox except creating the new listening folder, and never delete
   an original recording. Leave the "Originals for analysis - DELETE AFTER" folder alone: Aaron decides
   when it's cleared.
```
