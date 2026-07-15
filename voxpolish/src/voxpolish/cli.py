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
    p.add_argument("--sep-model", default=None,
                   help="audio-separator model for separation "
                        "(default: the MIT Mel-Band RoFormer)")
    p.add_argument("--sep-shifts", type=int, default=None,
                   help="(legacy, ignored by the RoFormer backend)")
    p.add_argument("--bleed-strength", type=float, default=None,
                   help="Instrumental-bleed suppression on the vocal stem, 0..1 "
                        "(default 0.7; 0 disables)")
    p.add_argument("--remix-vocal-db", type=float, default=None,
                   help="MANUAL vocal balance override in the remix sum, dB. "
                        "Default: balance is measured and the original "
                        "vocal-to-backing ratio restored within safety bounds")
    p.add_argument("--target-lufs", type=float, default=None,
                   help="Mastering loudness target, LUFS integrated (default -15)")
    p.add_argument("--true-peak-db", type=float, default=None,
                   help="Final true-peak ceiling, dBTP (default -3)")

    t = sub.add_parser("pitch", help="Analyze pitch and propose gentle corrections (no audio changes)")
    t.add_argument("input", help="A clean vocal recording or stem")
    t.add_argument("-o", "--out", default=None, help="Report path (default: <input>_pitch.json)")
    t.add_argument("--strength", type=float, default=0.4,
                   help="Correction strength 0..1 (default 0.4 = subtle)")
    t.add_argument("--retune-ms", type=float, default=120.0,
                   help="Retune speed; higher = more natural glide (default 120)")
    t.add_argument("--key", default=None,
                   help="Force key, e.g. 'A minor' or 'F# major' (default: auto-detect)")
    t.add_argument("--apply", action="store_true",
                   help="Actually apply the corrections: writes <input>_tuned.wav")
    t.add_argument("--from-report", metavar="JSON", default=None,
                   help="Skip analysis; apply this (hand-edited) pitch report's curve")

    u = sub.add_parser("ui", help="Open the browser editor (with a file, or empty to upload)")
    u.add_argument("input", nargs="?", default=None,
                   help="Audio file or session dir; omit to open the upload screen")
    u.add_argument("-o", "--session", default=None,
                   help="Session directory (default: <input>_session next to the file)")
    u.add_argument("--workspace", default=None,
                   help="Workspace dir for uploads (default: ./voxpolish_workspace)")
    u.add_argument("--port", type=int, default=8765)
    u.add_argument("--no-clean", action="store_true", help="Skip model-based denoising")

    args = parser.parse_args(argv)

    if args.command == "ui":
        return _run_ui(args)
    if args.command == "pitch":
        return _run_pitch(args)

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
    if args.sep_model is not None:
        settings.separation_model = args.sep_model
    if args.sep_shifts is not None:
        settings.separation_shifts = args.sep_shifts
    if args.bleed_strength is not None:
        settings.bleed_strength = args.bleed_strength
    if args.remix_vocal_db is not None:
        settings.remix_vocal_db = args.remix_vocal_db
    if args.target_lufs is not None:
        settings.target_lufs = args.target_lufs
    if args.true_peak_db is not None:
        settings.true_peak_db = args.true_peak_db

    edit_doc = EditDocument.load(args.from_doc) if args.from_doc else None

    start = time.time()
    outputs = process(args.input, args.out, settings, edit_doc=edit_doc)
    elapsed = time.time() - start

    print(f"Done in {elapsed:.1f}s. Outputs in {args.out}/")
    for name, path in outputs.items():
        print(f"  {name:16s} {path}")
    return 0


def _run_pitch(args) -> int:
    import json
    from pathlib import Path

    from . import audio_io
    from .stages import pitch

    key = None
    if args.key:
        parts = args.key.strip().split()
        try:
            tonic = pitch.NOTE_NAMES.index(parts[0].upper().replace("♯", "#"))
            mode = parts[1].lower()
            assert mode in ("major", "minor")
            key = (tonic, mode)
        except (ValueError, IndexError, AssertionError):
            print(f"Unrecognized key '{args.key}' — use e.g. 'A minor' or 'F# major'",
                  file=sys.stderr)
            return 1

    audio, sr = audio_io.load(args.input)
    mono = audio_io.to_mono(audio)
    if args.from_report:
        report = json.loads(Path(args.from_report).read_text())
    else:
        report = pitch.analyze(mono, sr, strength=args.strength,
                               retune_ms=args.retune_ms, key=key)

    if args.apply or args.from_report:
        tuned, applied = pitch.apply_correction(audio, sr, report["curve"])
        report = {**report, **applied}
        tuned_path = Path(args.input).with_name(Path(args.input).stem + "_tuned.wav")
        audio_io.save(tuned_path, tuned, sr)
        if applied["applied"]:
            print(f"Tuned audio: {tuned_path} (max applied {applied['max_applied_cents']} cents)")
        else:
            print(f"Tuned audio: {tuned_path} (passthrough — {applied['reason']})")

    out = Path(args.out) if args.out else Path(args.input).with_suffix("").with_name(
        Path(args.input).stem + "_pitch.json")
    out.write_text(json.dumps(report, indent=2))

    print(f"Key: {report['key']} (confidence {report['key_confidence']})")
    print(f"Voiced: {report['voiced_seconds']}s across {len(report['notes'])} notes")
    print(f"Mean deviation: {report['mean_abs_dev_cents']} cents")
    worst = sorted(report["notes"], key=lambda n: -abs(n["mean_dev_cents"]))[:5]
    if worst:
        print("Most off-pitch notes:")
        for n in worst:
            print(f"  {n['note']:4s} {n['start']:7.2f}s  {n['mean_dev_cents']:+6.1f} cents"
                  f"  -> proposed {n['proposed_cents']:+6.1f}")
    print(f"Report: {out}")
    return 0


def _run_ui(args) -> int:
    from pathlib import Path

    try:
        from .server.app import serve
        from .server.session import Session
    except ImportError:
        print("The editor needs FastAPI: pip install 'voxpolish[ui]'", file=sys.stderr)
        return 1

    if args.input is None:
        # No file: open the workspace on the upload/landing screen.
        root = Path(args.workspace) if args.workspace else Path.cwd() / "voxpolish_workspace"
        root.mkdir(parents=True, exist_ok=True)
        print(f"Workspace: {root}  — upload a recording from the browser")
    else:
        src = Path(args.input)
        if src.is_dir() and Session.is_session(src):
            root = src
        else:
            root = Path(args.session) if args.session else src.with_name(src.stem + "_session")
            if not Session.is_session(root):
                settings = Settings.for_mode("voice")
                if args.no_clean:
                    settings.denoise_amount = 0.0
                print(f"Analyzing {src.name} into {root}/ ...")
                Session.create(src, root, settings)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"VoxPolish editor: {url}  (Ctrl+C to stop)")
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        pass
    serve(root, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
