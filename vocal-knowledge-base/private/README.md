# Private — singer profiles

**Nothing in this folder is ever published.** It holds material about a specific
singer's body: measured range, passaggio, weak columns, take history, and the
practice programmes built from them.

`tools/kb_build_public.py` excludes this folder outright, and every document in
it carries `visibility: private` in its front matter as well. Two independent
guards, because a folder can be renamed or a file moved and a mistake here is a
privacy leak, not a typo.

## Why the split exists

`06-voxai-system/` used to hold both the VOXAI coaching system and Aaron's own
measurements. Publishing that folder would have published his body along with
the method. Aaron decided on 3 Aug 2026 to split them and keep the profiles
private for now.

The split is also the only version of this decision that stays **reversible**,
and it had to happen anyway the moment a second singer got a profile — Rilda,
Leo and Chris are all measured in the same archive.

## What lives here

| Document | What it is |
|---|---|
| `aaron-vocal-blueprint-v2.md` | Current coaching profile — range, passaggio, active target |
| `aaron-vocal-blueprint-v1.md` | Superseded, retained not deleted |
| `voxai-master-vocal-profile-aaron.md` | Measured vocal map across 34 tracks |
| `aaron-daily-drill-programme.md` | 20-minute programme built from 81 measured takes |

## Adding a profile for another singer

Same folder, same rules: `visibility: private`, `category: singer-profile`, and
name the file for the singer. The validator enforces the front matter; the
public build tool enforces the exclusion.

## What is NOT private

The **method** is public. `06-voxai-system/` keeps the VOXAI coaching system,
the knowledge core, the study guide and the implementation handoff — those
describe how the system works, not what one person's larynx does. A worked
example is persuasive, but it is a decision to make deliberately and it has not
been made.
