# Blind A/B protocol — does the singer rate his old takes lower when he can't tell they're old?

The outstanding experiment from the 2 Aug 2026 validity investigation. Both
calibration rounds so far were **sighted** — Aaron knew which take he was
rating — so the expectation effect is uncontrolled. This removes it.

**The question:** the engine rates Aaron's 2019–2020 takes ~2 points above his
ear. Is that because the recordings contain something the engine can't see, or
because he approaches old material expecting to hear a worse singer?

---

## Materials

**12 clips, 25–30 seconds each, vocals only, loudness-matched.**

| Set | Source | Status |
|---|---|---|
| 6 × 2024 | voice-cloning split (I'm a Believer, You Spin Me Round, Bad Things, Stand by Me, The Letter, Mustang Sally) | already in Dropbox `/Song_Analysis` |
| 6 × 2026 | The Heat Is On (16 Jul), The Letter (9 Jul), Do Wah Diddy (8 Jul), Let's Stay Together (8 Jul), G Vienna (11 Jul), Pressure Down (24 Jul) | **need RoFormer vocal stems exported** |

### What to ask Candi for
1. **Vocal stems only** for the six 2026 takes — never the mix. The 2024 set is
   already dry vocals; if half the clips have a band on them the test is dead
   before it starts.
2. **A 25–30 second excerpt** from each of all twelve — ideally a verse-into-
   chorus, avoiding the first 15 seconds (settling) and the very end.
3. **Loudness-matched** — normalise every clip to the same LUFS. Louder clips
   score higher in listening tests; this is well established and it will
   contaminate the result if skipped.
4. Delivered as `01.wav` … `12.wav` **after** shuffling (see below), with the
   key held by the shuffler, not by Aaron.

## Roles

**The shuffler (Rilda or Aaron's partner — NOT Aaron):**
- Randomises the order of all twelve clips and renames them `01`–`12`.
- Writes the key down privately and does not reveal it until scoring is done.
- Does not tell Aaron how many clips come from each era.
- Plays each clip once, in order, pausing between for the score.

**Aaron:**
- Scores each clip **0–10** for singing quality.
- **One pass. No replaying, no going back to compare.** First impression is the
  measurement.
- Same headphones, same volume, one sitting.
- Says the number out loud; the shuffler writes it down.

## Known limitation — read this before interpreting

**Song identity partially leaks era.** Aaron knows his own repertoire and will
recognise most songs. The 25–30 second vocals-only excerpts reduce arrangement
cues and push attention toward the voice, but they do not eliminate recognition.

This is why the design carries an **internal control**: *The Letter* appears in
both sets (2024 and 2026). Same song, both eras, indistinguishable by title.
**That single pair is the cleanest comparison in the experiment** — if the two
Letters are rated far apart, the era difference is real; if they land together,
it is expectation.

Two further cautions:
- The first clip acts as an anchor. Consider having the shuffler play one
  unscored throwaway clip first to set the scale.
- The three 2019–2020 takes (3AM, Twist & Shout, Lose Control) are **burned** —
  Aaron has already heard and rated them knowing what they were. They cannot be
  used here, which is why this test uses the 2024 set instead.

## Reading the result

| Outcome | Interpretation |
|---|---|
| Old and new rated about the same | The gap was expectation, not hearing. Engine and ear both sound; Aaron was harsh on his own history. |
| Old still rated clearly lower | Something real in the old material that the engine cannot see. Worth hunting properly. |
| The two Letters rated far apart | Strongest evidence for a genuine era difference. |
| The two Letters rated together | Strongest evidence for the expectation effect. |

Compare Aaron's blind scores against the engine's `overall` (**not**
capture-fair — that substitution was tested and made agreement worse; a singer
judges the recording as heard, capture flaws included).

## Recording the outcome

Whatever happens, write it into `SCORE_READING_LIMITATIONS.md` alongside the
sighted rounds — including if the result is null or contradicts the current
working explanation.
