# Handoff: validate the timing / groove readout (Candi)

Quick check that the new **canonical timing scorer** reads correctly. Best done
with a song where you already know the singer **rushes** (early) or **drags**
(late), so the sign is predictable.

## 1. Run a full song (song mode, with separation)

The groove/timing scorer only runs when there's a backing to reference, so use a
**full mix** and enable stem separation:

```bash
cd aaroncodex/voxanalysis/vox-analysis/engine
python analyse_song.py <song.mp3> --name "<singer>" --separate-stems \
  --song "<title>" --artist "<original artist>"
```

Or through the viewer (upload a full song, fill in song + artist). Either way,
first run downloads the MIT RoFormer and is **slow on CPU** — expected.

## 2. Read the GROOVE / TIMING section

In the markdown report (or the viewer), look for **GROOVE / TIMING (vs backing
track — canonical timing scorer)**:

| Field | What to check |
|---|---|
| **Mean onset offset** | `+ms` = dragging (late), `−ms` = rushing (early). Sign should match what you hear. |
| **Timing consistency (spread)** | Lower = tighter. Big spread = timing wanders. |
| **Reference grid** | Should say **instrumental stem (mix − vocal, vocal-free)** — that's the unbiased grid. |
| **Confidence** | **high** = the pre-split mix and the instrumental agree on tempo. **medium** = only one reference. |
| Cross-check note | On a `high`, shows `mix … / inst … BPM` — the two tempos should be close. |

Rule of thumb: persistent `|offset|` under ~25 ms reads as **in the pocket**.
Consistent positive offsets (soul/jazz back-phrasing) are **style, not error**.

## 3. What to report back

- A song where the offset **sign is wrong** (says dragging but the singer rushes,
  or vice-versa) — that's the important failure to catch.
- Any run where **confidence is `low`** with a note that the references disagree
  on tempo (possible half/double-time or a separation artifact) — send the song.
- Sanity: the vocal-only **ONSET DENSITY & REGULARITY** section (further down) is
  *not* timing — it's how densely the delivery is phrased. Its tempo is
  indicative only; don't read timing accuracy from it.

## Notes

- If a song has **little or no percussion**, beat tracking is shakier — expect
  `medium` confidence and treat the offset as a guide.
- Needs both stems, so always pass `--separate-stems` (or use the viewer's song
  upload). Voice-only recordings won't produce a groove section.
