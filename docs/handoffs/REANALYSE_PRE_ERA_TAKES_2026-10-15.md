# Re-analyse queue — five takes from before measurement-era stamping

> **Side task.** This is a side task to run alongside whatever is already running
> in the background. Do not stop, pause or interfere with that task — work on
> this in parallel and leave the background job untouched.

## Why these five

On 15 Oct 2026 a full sweep of every unmerged analysis branch found 33 of
Aaron's takes that are not yet on `main`. 28 pass the engine's provenance checks
and are quotable. **These five do not.**

All five fail for the same reason: they were analysed on 31 Aug – 1 Sep 2026 on
an engine build from **before measurement-era stamping**. Their JSON carries no
`measurement_fingerprint` and no calibration-pack stamp, so
`score_conflict()` against any current take returns:

> *anchored to different calibration packs — re-score both against one pack*

Nothing is wrong with the audio: Praat was available, `coverage` is `full`, and
the vocal stems were RoFormer. Only the engine version is stale. Their stored
scores **must not be quoted, ranked or trended** until they are re-run.

(This is a different problem from `REANALYSE_WHEN_PRAAT_RESTORED.md`, which is
about takes measured without Praat. That queue is still empty — all 28 quotable
takes in the sweep have full 7-of-7 coverage.)

## Targets — what a cleared take must show

From `tools/score_preflight.py` on 15 Oct 2026 (PREFLIGHT PASSED):

| Check | Required value |
|---|---|
| rubric build | `deterministic_rubric_v5`, build `7cbd02df8f62` |
| calibration pack | `4c52716b5aed` (50 pro references) |
| measurement era | `measurement_fingerprint == 28e854af22ea` |
| separation | RoFormer |
| coverage | `technical_score.coverage == "full"` |
| provenance | `is_legacy_score() is False` and `score_conflict()` vs a current `main` take is `None` |

## The queue

In priority order. Source audio is the untouched original WAV in Dropbox;
**never modify or delete an original** (memory 033).

| # | Take | Singer | Branch it lives on | Vocal stem (`analysis_input_file`) | Notes | Status |
|---|---|---|---|---|---|---|
| 1 | `2026-08-31-aaron-fireball-take-001` | Aaron | `codex/homestead-rildo-verified-2026-08-31` | `2026-08-31-rilda-fireball-take-001_(vocals)_vocals_mel_band_roformer.flac` | Live, Homestead, Rildo's device (`2026-08-31-rilda-fireball-take-001.wav`). **Singer is Aaron** — attribution was corrected from Rilda, but the stem and source files still carry the `rilda-` name; match on that exact basename. High value: Fireball is now in Aaron's top tier (9.0, 10 Sep instamic take). | ☐ |
| 2 | `2026-08-31-aaron-fly-like-an-eagle-take-001` | Aaron | `codex/homestead-rildo-verified-2026-08-31` | `2026-08-31-aaron-fly-like-an-eagle-take-001_(vocals)_vocals_mel_band_roformer.flac` | Live, Homestead, Rildo's device. This Rildo capture is the **single canonical source**. The older Dropbox file `Fly Like An Eagle HomeStead.wav` is the *same performance* — do **not** analyse it as a second take. | ☐ |
| 3 | `2026-09-01-aaron-let-s-go-take-002` | Aaron | `codex/lets-go-take2-2026-09-01` | `2026-09-01-aaron-let-s-go-take-002_(vocals)_vocals_mel_band_roformer.flac` | Home recording via Dropbox, 96 kHz 24-bit stereo WAV. Distinct Take 2 (Take 1 is 2026-08-31). | ☐ |
| 4 | `2026-08-31-aaron-and-rilda-love-shack-take-001` | Aaron **and** Rilda | `codex/homestead-rildo-verified-2026-08-31` | `2026-08-31-aaron-and-rilda-love-shack-take-001_(vocals)_vocals_mel_band_roformer.flac` | Live **duet**, Homestead, Rildo's device. The engine measures one combined vocal stem, so the score covers **both voices** and singer-specific metrics can't be attributed. Deliver to both singers with that caveat stated. | ☐ |
| 5 | `2026-08-31-aaron-cry-in-shame-take-002-rildo-capture-variant` | Aaron | `codex/homestead-rildo-verified-2026-08-31` | `2026-08-31-aaron-cry-in-shame-take-002_(vocals)_vocals_mel_band_roformer.flac` | **Optional / lowest priority.** A superseded alternate capture of the same performance already archived on `main` as `2026-08-30-aaron-cry-in-shame-take-002`. It is excluded from rankings, averages and progress counts. Re-run only to make the record consistent. | ☐ |

## How to clear them

1. **Work on a branch that contains the five archive entries.** They are not on
   `main` yet. Start from current `main` and merge
   `codex/homestead-rildo-verified-2026-08-31` and
   `codex/lets-go-take2-2026-09-01` into it.
2. **Install the engine's dependencies**, including `praat-parselmouth`:
   `pip install -r voxanalysis/vox-analysis/engine/requirements.txt`.
3. **Re-analyse.** Pick the path that matches what's on the machine:
   - **Stems available** (fast — no separation): put the five `*_(vocals)_vocals_mel_band_roformer.flac`
     files in one folder, then
     ```bash
     python3 tools/reanalyse_archive.py /path/to/stems           # dry run: check all 5 match
     python3 tools/reanalyse_archive.py /path/to/stems --write   # re-analyse and update the archive
     ```
     The tool matches each archive entry on its exact `analysis_input_file`
     basename, so nothing is guessed. A failed run leaves the old entry untouched.
   - **No stems**: re-run from the untouched original WAV with RoFormer
     separation, e.g.
     ```bash
     cd voxanalysis/vox-analysis/engine
     python analyse_song.py "/path/to/2026-08-31-rilda-fireball-take-001.wav" --name "Aaron - Fireball" --separate-stems
     ```
     Then put the new JSON in place of the old archive entry.
4. **Verify each take** against every row in the Targets table above.
5. **Refresh and check:**
   ```bash
   python3 docs/score-metrics/rescore_all.py
   python3 tools/score_preflight.py     # must exit 0
   ```
6. **Archive through a PR** (CLAUDE.md rule 9): commit one song's analysis JSON
   per commit, push, and make sure a PR to `main` exists.
7. **Deliver the results** (CLAUDE.md rules 5, 6 and 8). For every cleared take,
   run `python3 tools/show_results.py <take-name>` and hand the **full** report
   to the singer. Lead with the higher of overall and capture-fair with the other
   beside it, state confidence, and the anchor "calibrated to 50 professional
   reference vocals — 10 = a typical pro". A commit hash is not a delivery.
8. Tick the row off in the queue above.

## Related, not in scope

The sweep's other 28 takes all pass provenance. As of 15 Oct, **10 are on
`main`**: the 11 Oct set via PR #117 (including Kryptonite, 9.2) and the 14 Oct
set via PR #120 (including Play That Funky Music, 9.4), with the current score
table rebuilt as `all-takes-rescore-v5-2026-10-15.*`.

**18 are still on unmerged branches**, so the official table doesn't include
them yet — among them Do Wah Diddy 10 Oct (9.7, `codex/redcliffe-tavern-2026-10-10`)
and the 10 Sep Fireball / This Is How We Do It takes
(`codex/split-and-analyse-2026-09-10`). The other branches are
`codex/aaron-fireball-heroes`, `codex/all-that-she-wants-home-instamic-20260915`,
`codex/bramble-you-give-love-a-bad-name-20260924`, `codex/greshmans-fcm-2026-10-10`,
`codex/home-2026-10-09`, `codex/home-blinding-lights-2026-10-07`,
`codex/kedron-2026-10-09`, `codex/kedron-yglabn-2026-10-09` and
`codex/live-redcliffe-tavern-2026-10-10`. Merging them (then `rescore_all.py`
and preflight) is a separate job.

## Paste-ready prompt for Frankie

```text
SIDE TASK: run this alongside whatever is already running in the background.
Do not stop, pause or interfere with that task.

In the goodermine/aaroncodex repo, follow
docs/handoffs/REANALYSE_PRE_ERA_TAKES_2026-10-15.md to re-analyse five takes
from 31 Aug - 1 Sep 2026 that were measured on an engine build from before
measurement-era stamping (Fireball, Fly Like an Eagle, Let's Go take 2,
Love Shack duet, and the optional Cry in Shame capture variant).

The source WAVs are in Dropbox; never modify or delete an original. Use the
RoFormer vocal stems if you have them (tools/reanalyse_archive.py), otherwise
re-run from the original WAVs with --separate-stems. Verify every take against
the Targets table (measurement 28e854af22ea, pack 4c52716b5aed, full coverage,
no score_conflict), run rescore_all.py and score_preflight.py (must pass),
archive one JSON per commit via a PR, and give Aaron (and Rilda for Love Shack)
the full results from tools/show_results.py for each take.
```
