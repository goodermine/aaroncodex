"""Command-line interface.

    voxpolish process song.mp3 --mode song -o out/
    voxpolish process talk.wav --mode voice -o out/
    voxpolish process talk.wav --from-doc out/edit_document.json -o out2/
"""

from __future__ import annotations

import argparse
import sys
import time

from .document import EditDocument
from .pipeline import Settings, process


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="voxpolish", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("process", help="Clean up a song or voice recording")
    p.add_argument("input", help="Audio file (wav/flac work everywhere; mp3/m4a need ffmpeg)")
    p.add_argument("-o", "--out", default="voxpolish_out", help="Output directory")
    p.add_argument("--mode", choices=["song", "voice"], default="voice",
                   help="song: separate vocal from a full mix first; voice: input is already voice")
    p.add_argument("--strip-music-bed", action="store_true",
                   help="Voice mode only: use separation to remove background music")
    p.add_argument("--from-doc", metavar="JSON",
                   help="Skip analysis; render this (hand-edited) edit document instead")
    p.add_argument("--no-gate", action="store_true")
    p.add_argument("--no-dynamics", action="store_true")
    p.add_argument("--no-breath", action="store_true")
    p.add_argument("--no-sibilance", action="store_true")
    p.add_argument("--no-clean", action="store_true", help="Skip model-based denoising")
    p.add_argument("--target-db", type=float, default=None,
                   help="Dynamics target level in dBFS (default: match the recording)")
    p.add_argument("--gate-floor-db", type=float, default=None)
    p.add_argument("--smoothing", type=float, default=None,
                   help="Dynamics strength 0..1 (default 0.7 voice / 0.5 song)")

    args = parser.parse_args(argv)

    settings = Settings.for_mode(args.mode)
    settings.strip_music_bed = args.strip_music_bed
    settings.enable_gate = not args.no_gate
    settings.enable_dynamics = not args.no_dynamics
    settings.enable_breath = not args.no_breath
    settings.enable_sibilance = not args.no_sibilance
    if args.no_clean:
        settings.denoise_amount = 0.0
    if args.target_db is not None:
        settings.target_db = args.target_db
    if args.gate_floor_db is not None:
        settings.gate_floor_db = args.gate_floor_db
    if args.smoothing is not None:
        settings.dynamics_smoothing = args.smoothing

    edit_doc = EditDocument.load(args.from_doc) if args.from_doc else None

    start = time.time()
    outputs = process(args.input, args.out, settings, edit_doc=edit_doc)
    elapsed = time.time() - start

    print(f"Done in {elapsed:.1f}s. Outputs in {args.out}/")
    for name, path in outputs.items():
        print(f"  {name:16s} {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
