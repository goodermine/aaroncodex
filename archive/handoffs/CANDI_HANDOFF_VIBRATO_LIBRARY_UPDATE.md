# HANDOFF: Candi — Add Vibrato Exercises to the Scientific Library (from source)

Task type: knowledge-base content update, on the local machine, pushed to
`vox-cloud-alpha` `main`. Read fully before editing anything.

## Why

An audit of the prescription-engine plan found the exercise library
(`openclaw-data/vox-coach/knowledge/VOXAI_Scientific_Exercise_Library.txt`)
contains **zero vibrato exercises** — the word does not appear once, and
the library ends at exercise 100. Meanwhile a knowledge assistant
("Maestro Resonance") described vibrato drills citing "exercises 85, 93,
122, 129" — numbers that either don't exist in the library or belong to
different exercises (85 = Dynamic Agility Scales, 93 = VFE Downward
Glide). Conclusion: the vibrato content lives in the **fuller source
compendium** the library was distilled from (library header: "Source
distilled from: Scientific Singing Exercises.txt"), and the distillation
dropped it. The deterministic prescription engine can only prescribe what
is literally in the library file — so the library must be updated from
the source.

## The task

1. **Locate the source compendium** on this machine — likely named
   `Scientific Singing Exercises.txt` (or similar); search the OpenClaw
   workspace, uploads, and knowledge folders. Confirm it contains a
   vibrato section (expected drills include: pitch oscillation/toggle
   between close pitches, staccato-to-legato transitions, aspirated/
   fricative onsets with silent-repeat release, gentle diaphragm/beggar's
   pulse, straight-tone-vs-vibrato alternation, sirens with delayed
   vibrato).

2. **Extract the vibrato exercises VERBATIM** — no paraphrasing, no
   summarising. If the source's wording lacks any of the library's seven
   standard fields, fill only the missing fields, marking additions
   clearly (e.g. "Pass/Fail metric (added at distillation): ...").

3. **Append to the library** following ALL of these rules:
   - Numbering: new exercises take **101, 102, 103, ...** — NEVER renumber
     or edit exercises 1–100 (the prescription map and past reports
     reference them by number).
   - Format: the exact 7-field template every existing exercise uses
     (Use when / Pedagogical target / How to do it / How it should feel /
     Common failure & safety note / Pass/Fail metric / Song transfer).
   - Section: add a new `## VIBRATO DEVELOPMENT / CONTROL` section after
     `## HABILITATION / STAMINA / RECOVERY`.
   - Selector: add one entry to the QUICK PRESCRIPTION SELECTOR:
     `## If vibrato is absent, uneven, forced, or wobbly` listing the new
     exercise numbers in recommended order, with one best next-take cue —
     phrased from the source's own guidance (vibrato emerges from
     airflow/relaxation balance; never force it from jaw or throat).
   - Safety: carry over the source's cautions verbatim (e.g. forceful
     abdominal pulsing creates artificial tremolo — discouraged).

4. **Do NOT change anything else in the file.** No reflowing, no typo
   fixes elsewhere, no renumbering. The file is hash-tracked
   (`verify_voxai_knowledge.py`); the hash will change — that is expected
   and fine, but the diff must contain only the additions above.

5. **Verify, commit, push:**
   - `python3 scripts/verify_voxai_knowledge.py` still passes.
   - `git diff` shows only additions (new section + selector entry).
   - Commit to `vox-cloud-alpha` `main` with a message like
     `knowledge: add vibrato exercises 101-10X from source compendium`.
   - Reply with: how many exercises were added, their numbers and names,
     and the exact name/path of the source document used.

## If the source document cannot be found

Do NOT author vibrato exercises from memory or from Maestro Resonance's
summary — his citations already failed verification once. Report back
"source not found, searched <locations>" and Aaron will decide between
locating the source elsewhere or approving human-written content.

## After this lands

The prescription-engine build will map the measured vibrato metrics
(`vibrato.pct_notes_with_vibrato`, rate/extent vs pro bands,
`median_onset_delay_s`) to the new selector category — with the style
guard that deliberate straight tone is never auto-prescribed against;
vibrato drills only trigger when vibrato is attempted-but-uneven, or the
singer's stated goal includes developing it.
