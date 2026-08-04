---
name: dream
description: Nightly dreaming pass, two phases — (1) memory consolidation: review the last 24h of transcripts against memory/MEMORY.md and propose additions/retirements with transcript evidence; (2) dream forward: generate improvement ideas for the system (UI, workflow, tooling, out-of-the-box) grounded in observed friction. Use when the user types /dream, when a scheduled run fires, or with arguments — "apply N"/"apply all" for memories, "build DN"/"park DN"/"dismiss DN" for ideas.
---

# /dream — nightly consolidation AND forward dreaming

Modeled on a dreaming pass: while Aaron sleeps, review what happened, decide
what is worth remembering, and **imagine what could be better** — then
**propose, never decide**. Both phases produce proposals; Aaron approves.

## Ground rules (override everything below)

1. **NEVER add, rewrite, or retire a memory without Aaron's approval.** The only
   auto-applied changes are trivial safe fixes: typos in memory files, a broken
   or out-of-date `MEMORY.md` index entry. When unsure, propose — don't act.
2. Facts are never deleted — retirement means `status: retired` plus a reason,
   preserving the file (the same convention as the rest of this repo).
3. Memory lives in `memory/` **in the repo** and every change is committed and
   pushed. The container is ephemeral; an uncommitted memory does not exist.
4. Memory files may contain Aaron's personal data. `memory/` is not part of the
   knowledge base and must never be included in any public build.

## The review pass (no arguments, or a scheduled run)

1. **Read the transcripts** from the last 24 hours:
   `/root/.claude/projects/*/*.jsonl` (files modified within a day; skip
   `subagents/`). They are large — stream/grep them, don't load whole.
   Mine the **user messages and corrections** first; assistant text second.
2. **Read `memory/MEMORY.md`** and every fact file it lists.
3. **Compare**, hunting five kinds of finding:
   - **Corrections Aaron gave** (he said something I had wrong — highest value)
   - **Preferences he repeated or stated** (how he likes to work/be coached)
   - **New durable facts** worth keeping (equipment, people, venues, decisions)
   - **Stale or wrong memories** (contradicted by newer sessions) → propose retirement
   - **Duplicates** (same fact twice, or already covered by CLAUDE.md /
     handoffs — prefer the existing home; do not duplicate CLAUDE.md into memory)
4. **Propose every change as a NUMBERED LIST.** Each item: the proposed fact
   file name, one-line gist, and a **short direct quote from the transcript**
   as evidence (with the session date). Number continuously so
   `apply N` is unambiguous.
5. **Auto-apply only the trivial fixes** from rule 1, and say which were applied.
6. **Deliver:**
   - If Aaron is present (interactive session): show the list in the reply.
   - If nobody is here (scheduled overnight run): write the list to
     `memory/dream-report.md` (overwrite — it is the standing inbox, and its
     proposals stay valid until applied or dismissed), commit, push. Do not
     apply anything beyond rule-1 fixes. Do not message anyone.

## Phase 2 — Dream forward (REM mode)

After the memory pass, generate **3–6 improvement ideas** for the whole system:
VOX Suite UI, the pitch monitor, coaching workflow, capture, reports, the
knowledge base, competition prep — anything. Rules:

1. **Ground most ideas in observed friction.** Each idea names its *seed*: the
   moment in a recent transcript (or repo state) that suggested it — a thing
   Aaron did manually twice, a number nobody looks at, a drill with no tooling.
   **One idea per night may be a pure out-of-the-box wildcard** with no seed;
   label it `wildcard`.
2. **Number ideas D1, D2, …** continuing from the ledger, so `build D7` is
   unambiguous forever.
3. **Write them into `memory/dream-ideas.md`** — the ideas ledger. Each idea:
   one-paragraph pitch, its seed/evidence, rough size (hours/days), what
   measured or felt thing it would improve, `status: proposed`.
4. **Never build overnight.** Not even small ones. Statuses move only on
   Aaron's word: `build DN` (I implement it next session-time), `park DN`
   (keep, not now), `dismiss DN` (retired with a reason, never deleted).
5. **Respect the engine's constitution.** Ideas may touch the UI, tooling,
   drills, capture, reports. Ideas that would change *scoring* must say so
   loudly and cite the v6 precedent (built, tested, rejected) — the bar is a
   measured improvement, not a neat thought.
6. Quality over quantity: a night with one good idea beats six fillers. Re-read
   the parked list first; re-proposing a parked idea with new evidence is
   better than inventing a duplicate.

## Applying — memories (`/dream apply 1,3` · `apply all` · `dismiss 2`)

- For each approved number: create `memory/NNN-short-slug.md` containing the
  fact, its evidence quote, the session date, and `status: active` — then add
  its line to `MEMORY.md`'s Facts section.
- For an approved retirement: set `status: retired` + reason in the fact file,
  and annotate the index line.
- Remove applied/dismissed items from `dream-report.md`, commit everything,
  push. Confirm in one short list what was applied and what was skipped.

## Acting on ideas (`/dream build D2` · `park D3` · `dismiss D4`)

- `build DN` — set `status: building` in the ledger, then implement it as
  normal interactive work (plan → build → test → deliver), and mark `built`
  with a pointer to the commit when done.
- `park DN` / `dismiss DN` — update status (+ reason for dismissals). Parked
  ideas are re-read every night and may be re-proposed with new evidence.

## Fact file format

```markdown
---
id: 001
slug: short-slug
status: active
learned: YYYY-MM-DD
---
One or two sentences stating the fact plainly.

> evidence: "short transcript quote" — session of YYYY-MM-DD
```

Keep facts small and separable — one fact per file, so retiring one never
touches another.
