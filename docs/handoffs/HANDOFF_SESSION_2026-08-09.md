# Handoff — session of 9 Aug 2026: coaching docs corrected, practice tools linked, packaging planned

_What landed, what was decided, and what is queued. Written for whoever picks up
next — including Candi, who owns two of the open threads._

Everything below is on `main` unless marked otherwise.

---

## 1. What landed

| Change | Where | PR |
|---|---|---|
| Song-fit reference sheet — ranking model reworked | `docs/practice/aaron-song-fit-reference.{md,pdf}` | #45 |
| Loop earplugs gear note — corrected with the A/B result | `docs/practice/gear-loop-earplugs.{md,pdf}` | #45 |
| Practice tools linked from all three decks | `design/vox-kit.css`, the three `deck.html` | #47 |
| `design/sync.sh` — tokens-only targets as a list, missing-dir safe | `design/sync.sh` | #47 |
| TimberTones' dead tokens copy removed | `timbertones/` | #47 |

Earlier in the same session (already merged before these): the 20-minute daily
drill programme, the improvement brief in both listening and reading form, the
`/dream` routine, and the songbook how-to-sing guides.

## 2. Decisions recorded — do not re-litigate these

**Earplugs are not a singing aid.** The A/B ran (Do Wah Diddy, 4 Aug): plugs
**in** measured 20c median deviation / 31.1% clean entries; **out** measured
10c / 40.3%. Worse on both counts. They stay in use for hearing protection at
~105 dB rooms — that case is untouched — but they should not be worn for takes
intended for measurement or for competition rounds. `memory/013`.

> The prediction (occlusion effect → hears himself better → cleaner entries) was
> wrong, and the gear note now says so explicitly. Hearing yourself *louder* is
> not hearing yourself *accurately*: occlusion colours the self-signal, and
> conscious pitch matching is already the weak point (`memory/012`).

**TimberTones keeps its own palette.** Aaron's call: the current colours are the
intended look, not a pending design-system migration. `timbertones/vox-tokens.css`
was vendored but never referenced (no `<link>`, no `@import`, zero `--vox-`
variables), so it is deleted, `sync.sh` deliberately excludes TimberTones with a
comment saying why, and the README no longer claims a shared palette.

**The song-fit ranking model changed.** It previously assumed *low = easy, high =
hard*. Per `memory/016`, the strong zone is **M2/mixed, core A3–B4, gear change
~D4**; songs sitting **lower** (E3–G4) force register crossings, trigger the
Pitch Slider scooping and measure *worse*. Songs are now placed on position
relative to A3–B4 and register-crossing load, with sag/drift as tie-breakers.

**Difficulty and execution are separate axes.** Oh What A Night is technically
demanding (falsetto-led, ~61% head voice, frequent flips) *and* Aaron's
best-measured performance. An earlier proposal to simply move it to "Hard" would
have been misleading — the sheet now records both facts.

## 3. What is planned next

**`docs/plans/PACKAGING_AND_DEPLOYMENT_PLAN.md`** — new. How VOX ships.

Short version: unification is already done (`unified.py` serves everything on one
origin); the gap is distribution, and there is no deployment artefact of any kind
in the repo. The system splits by weight — a light half (monitor, TimberTones,
recorder: browser-only, phone-capable) and a heavy half (separation/analysis/
polish: ~2.5–4 GB of torch and friends). Recommended sequence:

1. **Docker the unified server** — one artefact for Candi's box *and* a cloud host.
2. **PWA the light half** — installable practice apps on the phone, zero hosting.
3. **Cloud instance + login** — the stated VISION goal; fix M8/M10/M11 with it.
4. **Windows build last**, only if testers demand offline — it is the most
   expensive path and the only one that ships the calibration pack to strangers.

Aaron has approved starting at step 1.

## 4. Open threads

### Needs Candi
- **Re-analyse the octave-error takes.** Beggin', Rebel Yell, Sex Bomb, Don't Be
  Cruel, Sunshine Smile, Lonely Boy, Wild Thing all read as bass (the tracker
  octave-locked onto the backing) and cannot be range-ranked until re-run from a
  clean vocal stem. They are **not** hard songs — several score well.
- **She's Not There** — anomalous dark reading (centroid 585 Hz); verify by ear.
- **Only You** — separation failed, the analysis ran on the full mix; its score
  and vocal metrics are withdrawn and it needs a rerun.
- **You Can Leave Your Hat On** — its F5 was backing-vocal bleed, not Aaron
  (Joe Cocker's own lead is only B3–A4). Needs a clean solo-vocal re-analysis
  before it can be ranked.
- **`docs/handoffs/TIMBERTONES_HANDOFF.md`** still describes `vox-tokens.css` as
  "vendored suite design tokens". That file lives only on
  `claude/voiceassist-plugin-planning-krhz0d` (PR #46), not `main`, so it could
  not be corrected from here — drop that line when the PR lands.

### Untested experiments worth recording
- **Single-plug earplug config** — one plug in the speaker-facing ear. Keeps most
  of the dose reduction while leaving one undistorted reference; the one
  configuration the A/B did not cover.
- **Rebel Yell up 2–3 semitones** — follows from the M2/mixed model (raise it
  toward A3–B4). Nobody has tried it; the sheet flags it as untested.

### Parked
Dream ideas **D7–D10** are `status: parked` in `memory/dream-ideas.md` at Aaron's
request: session bootstrap for engine/PDF deps (D7), guide-freshness linter for
the songbook library (D8), auto listening-version PDF generator (D9), and the
with/without-earplugs A/B one-pager (D10 — partly overtaken by the manual A/B).

Two `/dream` memory proposals from 9 Aug are also still pending Aaron's approval:
the song-guide workflow (ChatGPT vowel map → Dropbox drop → measured guide) and
the ElevenLabs listening-PDF preference.

## 5. Gotcha for the next session

A fresh container **cannot run the engine or build a PDF out of the box**.
`score_preflight.py` needs `numpy`, `scipy`, `librosa` before it will import;
PDFs need `reportlab` (+ `pdfplumber`/`pypdfium2` to verify); the unified server
additionally needs `pyloudnorm`, `soundfile`, `python-multipart`, `httpx`. There
is no `poppler-utils`, so PDF page rendering falls back to `pypdfium2`, and
Playwright must be launched with `executable_path=/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.

This is dream idea **D7**, and the packaging plan folds it in.
