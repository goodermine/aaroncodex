# Whole-Song Training Plan Expansion

The normal Candi analysis should remain focused: one primary drill, one clear cue, and one next-take target.

When the user asks for more, Candi can generate a whole-song training plan with five supporting exercises. This gives the singer a fuller path without burying the first reply in too many tasks.

## Trigger Phrases

Generate the expansion when the user asks for:

- a training plan
- the full-song plan
- more exercises
- five drills
- how to sing the whole song better
- what to work on across the whole song

Do not generate the expansion by default.

## Structure

Use this structure:

1. Whole-Song Diagnosis
2. Primary Drill Recap
3. Five Supporting Exercises
4. Seven-Day Practice Plan
5. Next Full-Song Recording Target

## The Five Supporting Exercises

Choose drills that match secondary issues directly heard or reasonably inferred from the take.

Default target spread:

- pitch / intonation
- rhythm / timing
- intensity / shouting control
- tone / resonance
- phrase shape / performance delivery

If one category is not relevant, replace it with another real issue from the take. Do not invent a problem just to fill a category.

## Drill Format

Each supporting drill should include:

- name
- target problem
- exact exercise
- how long to practise
- what the singer should feel
- what to avoid
- where in the song to apply it

Example format:

```text
1. Pitch Anchor Drill
Target: chorus note is arriving slightly flat.
Exercise: sing the chorus entry on "mum" at 70 percent volume, then switch to the real lyric.
Time: 5 minutes.
Feel: smaller vowel, earlier pitch centre, less push.
Avoid: adding volume before the note is centred.
Song spot: first chorus entry.
```

## Seven-Day Plan

Keep it practical:

- Day 1: isolate the main problem section
- Day 2: pitch and vowel shaping
- Day 3: rhythm and lyric placement
- Day 4: intensity control
- Day 5: tone/resonance balance
- Day 6: phrase-to-phrase run
- Day 7: record a full-song take

Adjust the order if the song needs a different sequence.

## Guardrails

- Keep the primary drill clearly marked as the main priority.
- Keep the five supporting drills shorter than the primary diagnosis.
- Do not prescribe medical treatment or diagnose injury.
- Keep measured, inferred, and unverifiable claims separate when making technical claims.
- Make the plan song-specific, not a generic vocal workout.
- Do not overload the singer with more than five supporting drills in one expansion.

## Product Surface

In the SaaS UI, the report page should show:

```text
Primary fix
  visible by default

Whole-song training plan
  collapsed by default
  generated when requested
```

This keeps the core feedback sharp while giving motivated singers a complete path through the song.
