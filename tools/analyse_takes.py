#!/usr/bin/env python3
"""Analyse a folder of takes into the repo archive — new takes and old ones.

WHY THIS EXISTS
    The repo archive holds 35 takes from 4 dates in July. The VOX Coach host
    holds ~128 identified singer performances going back to February, ~109 of
    them with an isolated vocal stem already retained. So most of the singers'
    history has never been measured into this repo at all.

    That matters more than the rubric-v5 coverage gap it started as. One take
    gives a score; a series gives a trend — and phrase-ending sag (the v5
    component) is only actionable as a trend. Seventeen You Sexy Thing takes
    across five months is the dataset that answers "is this improving".

WHAT IT DOES
    Walks the directories you give it, groups the audio into takes, and for each
    take runs the current engine and writes `<take>_analysis.json` into
    voxanalysis/archive/scratch-analyses/.

    * An **isolated vocal stem** is used when one exists (filenames containing
      `(Vocals)`), because separation does not then need to re-run.
    * A **raw mix** is analysed with `--separate-stems`, which is much slower.
      Use --stems-only to skip those on a first pass.
    * Takes already complete in the archive are **skipped**, so the run is
      resumable — interrupt it and run it again.

    Scoring a full mix as though it were a vocal is meaningless (rule 4 in
    CLAUDE.md), which is why a raw mix is never analysed without separation.

USAGE
    # rehearse: what would be analysed, what would be skipped, what needs separation
    python3 tools/analyse_takes.py /path/to/uploads /path/to/stems

    # stems only — the fast pass, no separation
    python3 tools/analyse_takes.py /path/to/stems --stems-only --write

    # everything, including raw mixes needing separation (slow)
    python3 tools/analyse_takes.py /path/to/uploads /path/to/stems --write

    # then, always:
    python3 docs/score-metrics/rescore_all.py
    python3 tools/score_preflight.py

Writes are atomic. An existing archive entry is replaced only after a successful
engine run, and its previous version is kept as *.pre-reanalysis.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_DIR = os.path.join(ROOT, "voxanalysis/vox-analysis/engine")
ARCHIVE = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")

AUDIO_EXTS = (".flac", ".wav", ".mp3", ".m4a", ".mp4", ".aiff", ".aif", ".ogg", ".opus")

# Modules that only exist in the current engine; a take missing any of them
# predates them and cannot score every rubric component.
LATER_MODULES = ("breath", "harmonics", "onsets", "range_map", "registers", "prescriptions")

# Suffixes added by the separator and the engine's own conversion step. Stripped
# to recover the take's identity. NOT stripped: -normalized / -song-cut, which
# some archive entries keep in their name and some do not — so those are only
# used for loose duplicate detection, never to rename an existing entry.
PIPELINE_SUFFIX = re.compile(
    r"(_\(Vocals\)_.*|_\(Instrumental\)_.*|_converted|_vocals|_Vocals)+$", re.IGNORECASE)
LOOSE_NOISE = re.compile(r"(-normalized|-song-cut|-converted)+", re.IGNORECASE)

ARTIST_NAMES = {"aaron-g": "Aaron G", "aaron": "Aaron", "rilda": "Rilda",
                "chris": "Chris", "leo": "Leo", "alex": "Alex", "athea": "Athea",
                "jack": "Jack", "teagan": "Teagan"}


def take_key(filename: str) -> str:
    """Filename -> the take's identity, with separator/conversion suffixes removed."""
    base = os.path.splitext(os.path.basename(filename))[0]
    return PIPELINE_SUFFIX.sub("", base)


def loose_key(name: str) -> str:
    """Aggressively normalised key, for spotting the same take under two names."""
    return LOOSE_NOISE.sub("", take_key(name)).strip("-_").lower()


def is_stem(path: str) -> bool:
    return "(vocals)" in os.path.basename(path).lower()


def artist_of(key: str) -> str:
    stripped = re.sub(r"^20\d\d-\d\d-\d\d-", "", key).lower()
    for token, name in ARTIST_NAMES.items():       # aaron-g before aaron
        if stripped.startswith(token + "-"):
            return name
    return "Unknown Artist"


def missing_modules(analysis: dict) -> list[str]:
    return [m for m in LATER_MODULES if not analysis.get(m)]


def atomic_write_json(path: str, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def collect(dirs: list[str]) -> dict[str, dict]:
    """take_key -> {"stem": path|None, "raw": path|None}. Stems win."""
    takes: dict[str, dict] = {}
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, "**", "*"), recursive=True)):
            if not path.lower().endswith(AUDIO_EXTS) or not os.path.isfile(path):
                continue
            slot = takes.setdefault(take_key(path), {"stem": None, "raw": None})
            key = "stem" if is_stem(path) else "raw"
            if slot[key] is None:
                slot[key] = path
    return takes


def run_engine(audio: str, artist: str, separate: bool, timeout: int):
    base = os.path.splitext(os.path.basename(audio))[0]
    out_json = os.path.join(ENGINE_DIR, "output", f"{base}_analysis.json")
    before = os.path.getmtime(out_json) if os.path.exists(out_json) else None
    cmd = [sys.executable, "analyse_song.py", audio, "--name", artist]
    if separate:
        cmd.append("--separate-stems")
    try:
        proc = subprocess.run(cmd, cwd=ENGINE_DIR, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        return None, f"engine exited {proc.returncode}: {' / '.join(tail)}"
    if not os.path.exists(out_json):
        return None, "engine wrote no analysis JSON"
    if before is not None and os.path.getmtime(out_json) == before:
        return None, "engine did not refresh its output file"
    with open(out_json) as fh:
        return json.load(fh), ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", help="Directories holding takes (searched recursively)")
    ap.add_argument("--write", action="store_true", help="Apply (default: dry run)")
    ap.add_argument("--stems-only", action="store_true",
                    help="Skip takes that would need stem separation to run")
    ap.add_argument("--force", action="store_true",
                    help="Re-analyse even takes already complete in the archive")
    ap.add_argument("--only", default="", help="Substring filter on the take name")
    ap.add_argument("--limit", type=int, default=0, help="Stop after N takes")
    ap.add_argument("--timeout", type=int, default=2400, help="Per-take engine timeout (s)")
    ap.add_argument("--archive", default=ARCHIVE, help="Archive directory to write into")
    args = ap.parse_args()

    takes = collect(args.dirs)
    if not takes:
        print(f"No audio found under: {', '.join(args.dirs)}")
        return 1

    existing = {os.path.basename(p).replace("_analysis.json", ""): p
                for p in glob.glob(os.path.join(args.archive, "*_analysis.json"))}
    existing_loose = {loose_key(k): k for k in existing}

    fresh, refresh, complete, needs_sep, dupes = [], [], [], [], []
    for key, paths in sorted(takes.items()):
        if args.only and args.only not in key:
            continue
        audio, separate = (paths["stem"], False) if paths["stem"] else (paths["raw"], True)
        if audio is None:
            continue
        entry = existing.get(key)
        # Same take already archived under a slightly different name? Reuse that
        # entry rather than creating a second record of one performance.
        if entry is None:
            alias = existing_loose.get(loose_key(key))
            if alias:
                entry = existing[alias]
                dupes.append((key, alias))
        if entry is not None:
            with open(entry) as fh:
                gaps = missing_modules(json.load(fh))
            if not gaps and not args.force:
                complete.append(key)
                continue
            target = entry
            bucket = refresh
        else:
            target = os.path.join(args.archive, f"{key}_analysis.json")
            bucket = fresh
        if separate and args.stems_only:
            needs_sep.append(key)
            continue
        bucket.append((key, audio, target, artist_of(key), separate))

    print(f"takes found in the folders : {len(takes)}")
    print(f"already complete (skipped) : {len(complete)}")
    print(f"NEW  — not in the archive   : {len(fresh)}")
    print(f"REFRESH — archived, partial : {len(refresh)}")
    if needs_sep:
        print(f"deferred (need separation) : {len(needs_sep)}   [--stems-only]")
    if dupes:
        print(f"\nmatched to an existing entry under a different name ({len(dupes)}):")
        for key, alias in dupes[:8]:
            print(f"  {key}\n    -> {alias}")

    work = fresh + refresh
    if args.limit:
        work = work[:args.limit]
    if not work:
        print("\nNothing to do.")
        return 0

    if not args.write:
        print("\nDRY RUN — would analyse:")
        for key, audio, target, artist, separate in work:
            tag = "SEPARATE+analyse" if separate else "analyse stem"
            print(f"  [{tag}] {key}  ({artist})")
            print(f"      {audio}")
        print(f"\n{len(work)} take(s). Re-run with --write to apply.")
        return 0

    ok, failed = 0, []
    for i, (key, audio, target, artist, separate) in enumerate(work, 1):
        print(f"[{i}/{len(work)}] {key}" + ("  (separating first)" if separate else ""))
        analysis, err = run_engine(audio, artist, separate, args.timeout)
        if analysis is None:
            print(f"    FAILED: {err}")
            failed.append((key, err))
            continue
        sag = (analysis.get("breath") or {}).get("pct_sagging_endings")
        score = (analysis.get("technical_score") or {}).get("overall_score_0_to_10")
        print(f"    overall {score}   sag {sag if sag is not None else 'n/a'}"
              f"{'%' if sag is not None else ''}")
        if os.path.exists(target):
            shutil.copy2(target, target + ".pre-reanalysis")
        atomic_write_json(target, analysis)
        ok += 1

    print(f"\nanalysed: {ok}   failed: {len(failed)}")
    for key, err in failed:
        print(f"  {key}: {err}")
    print("\nNOW RUN:")
    print("  python3 docs/score-metrics/rescore_all.py")
    print("  python3 tools/score_preflight.py")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
