#!/usr/bin/env python3
"""Re-analyse archived takes with the current engine, from their vocal stems.

WHY THIS EXISTS
    34 of 35 archived takes were analysed before six measurement modules
    existed. They are missing `breath` (phrase-ending sag — the component added
    in rubric v5), plus `harmonics`, `onsets`, `range_map`, `registers` and
    `prescriptions`. Their scores are therefore computed over 6 of 7 components
    with weights renormalised, which every score now reports as
    `coverage: partial`.

    The gap CANNOT be back-filled from the archive: the frame-level pitch
    contour is stripped when an analysis is archived, and `analyse_breath()`
    needs it. Only re-analysis recovers this.

WHAT IT NEEDS
    The **vocal stems** those analyses were originally run on — the
    `*_(Vocals)_UVR_MDXNET_Main.flac` files. Each archived analysis records its
    own stem filename in `analysis_input_file`, and this tool matches on that
    exact basename, so nothing is guessed.

    Because the inputs are already isolated stems, **separation does not need to
    re-run** — the slow, GPU-ish part is skipped entirely. This is just engine
    passes over existing files.

    The stems are not in this repo (only the Captain Cook take's audio is). Run
    this on the machine that holds them.

USAGE
    # see what would happen — matches, misses, nothing written
    python3 tools/reanalyse_archive.py /path/to/stems

    # actually re-analyse and update the archive
    python3 tools/reanalyse_archive.py /path/to/stems --write

    # then, always:
    python3 docs/score-metrics/rescore_all.py
    python3 tools/score_preflight.py

Raw measurements are replaced wholesale by the fresh analysis — that is the
point, and it is why nothing is merged from the old file. Writes are atomic and
a failed engine run leaves the existing archive entry untouched.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_DIR = os.path.join(ROOT, "voxanalysis/vox-analysis/engine")
ARCHIVE = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")

# Modules that only exist in the current engine. Presence of `breath` is what
# decides whether a take can score breath_support at all.
LATER_MODULES = ("breath", "harmonics", "onsets", "range_map", "registers", "prescriptions")


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


def index_stems(dirs: list[str]) -> dict[str, str]:
    """basename -> full path, for every audio file under the given directories."""
    exts = (".flac", ".wav", ".mp3", ".m4a", ".aiff", ".aif", ".ogg")
    found: dict[str, str] = {}
    for d in dirs:
        for path in glob.glob(os.path.join(d, "**", "*"), recursive=True):
            if path.lower().endswith(exts):
                found.setdefault(os.path.basename(path), path)
    return found


def missing_modules(analysis: dict) -> list[str]:
    return [m for m in LATER_MODULES if not analysis.get(m)]


def _engine():
    """The one engine, imported lazily so the tool's dry-run/matching logic
    stays importable without the engine's audio dependencies."""
    if ENGINE_DIR not in sys.path:
        sys.path.insert(0, ENGINE_DIR)
    import analyse_song
    return analyse_song


def carry_forward(old: dict, new: dict) -> dict:
    """Declarative metadata the engine never produces must survive a re-run.
    `take_context` (intent / capture / superseded / note) was set by the singer
    at upload time and is not in the audio; dropping it would silently return
    a learning take to the leaderboard or un-retire a superseded capture."""
    if isinstance(old.get("take_context"), dict):
        new["take_context"] = old["take_context"]
    return new


def run_engine(stem_path: str, artist: str, timeout: int) -> tuple[dict | None, str]:
    """Analyse one stem with the current engine. Returns (analysis, error)."""
    base = os.path.splitext(os.path.basename(stem_path))[0]
    out_json = os.path.join(ENGINE_DIR, "output", f"{base}_analysis.json")
    before = os.path.getmtime(out_json) if os.path.exists(out_json) else None
    cmd = [sys.executable, "analyse_song.py", stem_path, "--name", artist]
    try:
        proc = subprocess.run(cmd, cwd=ENGINE_DIR, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        return None, f"engine exited {proc.returncode}: {' / '.join(tail)}"
    if not os.path.exists(out_json):
        return None, f"engine wrote no {os.path.relpath(out_json, ROOT)}"
    if before is not None and os.path.getmtime(out_json) == before:
        return None, "engine did not refresh its output file"
    with open(out_json) as fh:
        return json.load(fh), ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stem_dirs", nargs="+", help="Directories holding the vocal stems")
    ap.add_argument("--write", action="store_true",
                    help="Actually re-analyse and update the archive (default: dry run)")
    ap.add_argument("--stale-measurement", action="store_true",
                    help="Select takes whose measurement era differs from this engine's "
                         "measurement_fingerprint (instead of takes missing modules). "
                         "This is the Phase 1 run of docs/VOX_SYSTEM_REVIEW_2026-09-02.md.")
    ap.add_argument("--only", default="",
                    help="Substring filter on the archived analysis filename")
    ap.add_argument("--limit", type=int, default=0, help="Stop after N takes (0 = all)")
    ap.add_argument("--timeout", type=int, default=1800,
                    help="Per-file engine timeout in seconds (default 1800)")
    ap.add_argument("--archive", default=ARCHIVE,
                    help="Archive directory to update (default: the repo archive). "
                         "Point this at a copy to rehearse the run safely.")
    args = ap.parse_args()
    archive_dir = args.archive

    stems = index_stems(args.stem_dirs)
    if not stems:
        print(f"No audio files found under: {', '.join(args.stem_dirs)}")
        return 1
    print(f"Indexed {len(stems)} audio file(s) under {len(args.stem_dirs)} director(ies).\n")

    archived = sorted(glob.glob(os.path.join(archive_dir, "*_analysis.json")))
    if args.only:
        archived = [p for p in archived if args.only in os.path.basename(p)]

    engine = live_fp = None
    if args.stale_measurement:
        engine = _engine()
        live_fp = engine.measurement_fingerprint()
        print(f"Selecting analyses not measured by this engine ({live_fp}).\n")

    todo, complete, unmatched = [], [], []
    for path in archived:
        with open(path) as fh:
            a = json.load(fh)
        if args.stale_measurement:
            era = engine.measurement_era(a)
            if era == live_fp:
                complete.append(os.path.basename(path))
                continue
            gaps = [f"measurement era {era} -> {live_fp}"]
        else:
            gaps = missing_modules(a)
            if not gaps:
                complete.append(os.path.basename(path))
                continue
        stem_name = a.get("analysis_input_file")
        stem_path = stems.get(stem_name) if stem_name else None
        if stem_path is None:
            unmatched.append((os.path.basename(path), stem_name, gaps))
        else:
            todo.append((path, stem_path, a.get("artist_name") or "Unknown Artist", gaps, a))

    print(f"already complete : {len(complete)}")
    print(f"to re-analyse    : {len(todo)}")
    print(f"stem not found   : {len(unmatched)}")
    if unmatched:
        print("\n  Missing stems (these takes cannot be re-analysed without the audio):")
        for name, stem, gaps in unmatched:
            print(f"    {name}\n      wants: {stem}")
    if not todo:
        print("\nNothing to do.")
        return 0

    if args.limit:
        todo = todo[:args.limit]

    if not args.write:
        print("\nDRY RUN — would re-analyse:")
        for path, stem_path, artist, gaps, _old in todo:
            print(f"  {os.path.basename(path)}")
            print(f"    from {stem_path}")
            print(f"    recovers: {', '.join(gaps)}")
        print("\nRe-run with --write to apply.")
        return 0

    ok, failed, no_breath = 0, [], []
    for i, (path, stem_path, artist, gaps, old) in enumerate(todo, 1):
        name = os.path.basename(path)
        print(f"[{i}/{len(todo)}] {name}")
        analysis, err = run_engine(stem_path, artist, args.timeout)
        if analysis is None:
            print(f"    FAILED: {err}  (archive entry left untouched)")
            failed.append((name, err))
            continue
        sag = (analysis.get("breath") or {}).get("pct_sagging_endings")
        if sag is None:
            # Not a failure: too few phrases is a legitimate outcome and the
            # scorer drops breath_support rather than publishing noise.
            no_breath.append(name)
            print("    note: no phrase-sag figure (too few phrases) — breath_support "
                  "will stay unscored for this take")
        else:
            print(f"    sag {sag}% of endings"
                  f" ({(analysis.get('breath') or {}).get('n_sagging_endings')}"
                  f"/{(analysis.get('breath') or {}).get('n_phrases_measured')})")
        if analysis.get("measurement_fingerprint"):
            print(f"    measured by {analysis['measurement_fingerprint']}")
        shutil.copy2(path, path + ".pre-reanalysis")
        atomic_write_json(path, carry_forward(old, analysis))
        ok += 1

    print(f"\nre-analysed: {ok}   failed: {len(failed)}   without a sag figure: {len(no_breath)}")
    if failed:
        print("\nFailures:")
        for name, err in failed:
            print(f"  {name}: {err}")
    print("\nPrevious versions kept alongside as *.pre-reanalysis — delete them once "
          "you are happy with the new numbers.")
    print("\nNOW RUN:")
    print("  python3 docs/score-metrics/rescore_all.py     # rebuild the score tables")
    print("  python3 tools/score_preflight.py              # must exit 0 before quoting a /10")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
