#!/usr/bin/env python3
"""Pair each calibration reference analysis with its source audio, safely.

WHY THIS EXISTS
    The 50 reference analyses record the stem they were made from
    (`..._(Vocals)_UVR_MDXNET_Main.flac`), not the original mix, and the source
    folder names its files differently. Exact-name matching found only 12 of 50.

    Hand-matching is the dangerous option. The calibration pack defines what
    "10" means for every score in the system, so pairing Adele's remaster to
    Adele's original — or worse, the wrong song of a similar length — shifts
    every score with nothing to flag it afterwards.

HOW IT PAIRS
    Two independent signals, and it only auto-stages when BOTH agree:

      * duration, within a tolerance, against `duration_seconds` recorded in the
        analysis. Strong evidence: it is a property of the recording itself.
      * name, after normalising case/punctuation, requiring every word of the
        reference name to appear in the candidate filename.

    A duration match with no name agreement is reported for a human to confirm,
    never staged silently. Ambiguous duration (two candidates in tolerance) is
    always reported, never guessed.

USAGE
    # report only — writes nothing
    python3 tools/pair_reference_audio.py <source-dir>

    # stage the confident pairs into a clean directory for separation
    python3 tools/pair_reference_audio.py <source-dir> --stage <staging-dir>

Requires ffprobe on PATH.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, "voxanalysis/vox-analysis/engine/calibration/references")
AUDIO_EXTS = (".flac", ".wav", ".mp3", ".m4a", ".mp4", ".aac", ".ogg", ".opus", ".webm")

# Words that carry no identifying information — present in the reference naming
# convention or in typical download filenames.
NOISE = {"official", "video", "audio", "lyrics", "lyric", "hd", "hq", "4k", "remastered",
         "remaster", "reference", "original", "music", "the", "a", "an", "and", "feat",
         "ft", "live", "version", "mv", "youtube"}


def norm_tokens(name: str) -> set[str]:
    base = os.path.splitext(os.path.basename(name))[0]
    base = re.sub(r"---[0-9a-f-]{8,}", " ", base)      # strip the uuid suffix
    words = re.split(r"[^a-z0-9]+", base.lower())
    return {w for w in words if w and w not in NOISE and not w.isdigit()}


def duration(path: str) -> float | None:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=60)
        return float(out.stdout.strip()) if out.stdout.strip() else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source_dir", help="Directory holding the original reference mixes")
    ap.add_argument("--stage", default="", help="Copy confident pairs into this directory")
    ap.add_argument("--refs", default=REFS, help="Reference analyses directory")
    ap.add_argument("--tolerance", type=float, default=2.0,
                    help="Duration tolerance in seconds (default 2.0)")
    args = ap.parse_args()

    refs = sorted(glob.glob(os.path.join(args.refs, "*_analysis.json")))
    if not refs:
        print(f"No reference analyses under {args.refs}")
        return 1
    sources = [os.path.join(args.source_dir, f) for f in sorted(os.listdir(args.source_dir))
               if f.lower().endswith(AUDIO_EXTS)]
    if not sources:
        print(f"No audio found under {args.source_dir}")
        return 1

    print(f"reference analyses : {len(refs)}")
    print(f"source audio files : {len(sources)}")
    print("probing durations…", flush=True)
    src = [(p, duration(p), norm_tokens(p)) for p in sources]
    unreadable = [p for p, d, _ in src if d is None]
    src = [(p, d, t) for p, d, t in src if d is not None]
    if unreadable:
        print(f"  {len(unreadable)} file(s) unreadable by ffprobe, ignored")

    confident, name_only, ambiguous, unmatched = [], [], [], []
    used: set[str] = set()
    for r in refs:
        data = json.load(open(r))
        key = os.path.basename(r).replace("_analysis.json", "")
        want = data.get("duration_seconds")
        rtok = norm_tokens(data.get("analysis_input_file") or key)
        near = [(p, d, t) for p, d, t in src
                if want is not None and abs(d - want) <= args.tolerance and p not in used]
        named = [c for c in near if c[2] and rtok and rtok.issubset(c[2] | rtok) and rtok & c[2]
                 and len(rtok & c[2]) >= max(1, len(rtok) - 1)]
        if len(named) == 1:
            confident.append((key, named[0][0], want, named[0][1])); used.add(named[0][0])
        elif len(near) == 1:
            name_only.append((key, near[0][0], want, near[0][1]))
        elif len(near) > 1:
            ambiguous.append((key, want, [p for p, _, _ in near]))
        else:
            unmatched.append((key, want))

    print(f"\nCONFIDENT  (duration AND name agree) : {len(confident)}")
    print(f"NAME UNSURE (duration only, 1 match) : {len(name_only)}   <- needs your eye")
    print(f"AMBIGUOUS  (several same length)     : {len(ambiguous)}   <- never guessed")
    print(f"NO MATCH                             : {len(unmatched)}")

    if name_only:
        print("\n--- CONFIRM THESE PAIRINGS BY EYE (duration matched, name did not) ---")
        for key, path, want, got in name_only:
            print(f"  {key}\n    -> {os.path.basename(path)}   ({want}s vs {got:.1f}s)")
    if ambiguous:
        print("\n--- AMBIGUOUS: same duration, cannot choose ---")
        for key, want, cands in ambiguous:
            print(f"  {key}  ({want}s)")
            for c in cands:
                print(f"      {os.path.basename(c)}")
    if unmatched:
        print("\n--- NO SOURCE FOUND ---")
        for key, want in unmatched:
            print(f"  {key}  ({want}s)")

    if args.stage:
        os.makedirs(args.stage, exist_ok=True)
        for key, path, _, _ in confident:
            shutil.copy2(path, os.path.join(args.stage, key + os.path.splitext(path)[1]))
        print(f"\nstaged {len(confident)} confident pair(s) into {args.stage}")
        print("Staged files are renamed to the reference basename so the analysis")
        print("matches its existing entry instead of creating a new one.")
        if name_only or ambiguous or unmatched:
            print(f"\n{len(name_only) + len(ambiguous) + len(unmatched)} reference(s) NOT staged.")
            print("Do not rebuild the calibration pack from a partial set without saying so —")
            print("the pack defines what 10 means for every score.")
    else:
        print("\nReport only. Re-run with --stage <dir> to copy the confident pairs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
