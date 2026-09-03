# Dream report — proposals awaiting Aaron's approval

Run: 2026-08-09 · 1 transcript reviewed (this session) · memory at 20 facts on main.

> **Renumbered 030–033.** These were first written as 021–024, but PR #50
> (`claude/stemscribe-handoff-l3cjhv`) already claims **021–029** for a
> different set of facts. Moved clear rather than collide — the same class of
> silent clash that idea D11 exists to prevent, caught this time before it
> landed.

## Recovered before proposing anything

**D7–D10 had been silently deleted from `memory/dream-ideas.md`.** Added 4 Aug
(`edf9b0a`), landed on main via PR #31 (`8bc4c68`), then overwritten five days
later by two commits from another branch (`f8627f6`, `caf106b`) carrying a
pre-D7 copy of the ledger. Restored from git history in their parked state.
Aaron had explicitly asked for these to be kept ("put those aside for later"),
so this is honouring that instruction, not a new decision. Prevention proposed
as idea D11.

## Memory proposals — nothing applied, awaiting approval

1. **NEW → `memory/030-felt-difficulty-is-signal.md`**
   Aaron's subjective read of a song is evidence worth acting on: twice in one
   exchange it caught an error the measured model had made. He said *Oh What A
   Night* was hard (it is — falsetto-led, ~61% head voice) and that *Hat On*
   felt easier (it is — its "hard" rating came from backing-vocal bleed, not
   his voice). Treat "this feels hard/easy" as a prompt to re-check the data,
   not as something the numbers overrule.
   > evidence: "I've only ever sang. Oh what a night once and I actually sang it again today. It's a really hard song to sing. I think and for me something like I'm Joe Cocker's leave. Your hat on is feels easier to what's your thoughts on that." — 2026-08-09

2. **NEW → `memory/031-timbertones.md`**
   TimberTones is a built, merged app in this repo (`timbertones/`, served at
   `/timbertones`): a sampled upright piano fused with a live pitch-match
   trainer — press a key, it plays the note and drops a target lane; sing to
   match, ±35-cent band, cents readout, streak. It targets fact 012 (conscious
   pitch matching) directly. Spelling trap: **TimberTones**, not "Timbre" —
   searching the timbre spelling finds nothing.
   > evidence: "Read handoff. docs/handoffs/TIMBERTONES_HANDOFF.md → pushed on claude/voiceassist-plugin-planning-krhz0d, opened as draft PR #46" — 2026-08-09

3. **NEW → `memory/032-song-guide-workflow.md`** *(re-proposed — pending since 4 Aug)*
   How Aaron builds a how-to-sing guide: he has ChatGPT map a song's vowels,
   drafts his own exercises from that, then wants the engine-measured layer
   added (range, breath map, prep plan). Source `.txt` files go in a Dropbox
   folder he calls his "extreme files"; he says "check for a new" to trigger a
   build. Store the description, **not the share URL** — it carries an access
   token and this repo is public.
   > evidence: "thus where I'm saving my extreme files. check for a new." — 2026-08-04

4. **NEW → `memory/033-listening-pdfs.md`** *(re-proposed — pending since 4 Aug)*
   Distinct from fact 005 (reading PDFs): some coaching docs should also be
   produced as **narration-optimised** PDFs — flowing prose, no tables, note
   names spelled out — for listening via ElevenLabs Reader while resting. The
   20-minute improvement brief in that form worked (he fell asleep to it).
   > evidence: "make it a PDF… because I'm going to put it in eleven readers so that I can just listen to this, um, while I go and have a little bit of a rest" / "Well I think it was great cause I actually fell asleep." — 2026-08-04/09

## Skipped as duplicates — already homed, per the skill's rule

- **TimberTones keeps its own palette** — recorded in `timbertones/README.md`,
  the `design/sync.sh` comment, and `HANDOFF_SESSION_2026-08-09.md`.
- **Packaging direction (Docker → PWA → cloud+login; Windows last)** —
  `docs/plans/PACKAGING_AND_DEPLOYMENT_PLAN.md`.
- **Earplugs rejected as a singing aid** — already fact 013, plus the gear note.
- **Creep is a historical learning take** — the archive JSON's `take_context`
  and the song-fit sheet appendix.

## Auto-applied

None. `MEMORY.md` was checked against disk: 20 listed, 20 present, no orphans,
no missing files — the index is clean and needed no repair.

## Ideas (phase 2) — written to the ledger as `proposed`

- **D11** Ledger merge-safety check — fail a merge that drops a D-number or fact id.
- **D12** Range-map trust flags — automatic octave-lock and backing-vocal-bleed
  detection; would unblock the nine takes stuck in the song-fit appendix.
- **D13** Sing against your own best take *(wildcard)* — your own best contour
  as the target line, not a piano tone.

Approve memories with `/dream apply 1,3` or `/dream apply all`; act on ideas
with `build DN` / `park DN` / `dismiss DN`.
