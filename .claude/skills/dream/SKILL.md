---
name: dream
description: Nightly memory consolidation — review the last 24h of session transcripts against memory/MEMORY.md, propose additions/retirements as a numbered list with transcript evidence, auto-apply only trivial fixes. Use when the user types /dream, when a scheduled dream run fires, or with "apply N"/"apply all" arguments to enact previously proposed changes.
---

# /dream — nightly memory consolidation

Modeled on a dreaming pass: while Aaron sleeps, review what happened, decide
what is worth remembering, and **propose — never decide** what enters memory.

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

## Applying (`/dream apply 1,3` · `/dream apply all` · `/dream dismiss 2`)

- For each approved number: create `memory/NNN-short-slug.md` containing the
  fact, its evidence quote, the session date, and `status: active` — then add
  its line to `MEMORY.md`'s Facts section.
- For an approved retirement: set `status: retired` + reason in the fact file,
  and annotate the index line.
- Remove applied/dismissed items from `dream-report.md`, commit everything,
  push. Confirm in one short list what was applied and what was skipped.

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
