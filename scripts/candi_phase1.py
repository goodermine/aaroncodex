#!/usr/bin/env python3
"""Phase 1 helpers for the Candi / VOX Coach MVP."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
DATA_DIR = WORKSPACE / "openclaw-data" / "vox-coach"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
UPLOADS_RAW_DIR = DATA_DIR / "uploads" / "raw"
UPLOADS_PROCESSED_DIR = DATA_DIR / "uploads" / "processed"
MEMORY_DIR = DATA_DIR / "memory"
TEMP_DIR = DATA_DIR / "temp"
LOG_PATH = DATA_DIR / "logs" / "vox-coach.log"

BACKEND_DIR = Path(
    os.environ.get("VOXAI_BACKEND_DIR", WORKSPACE / "backend" / "voxai-local-analysis")
).expanduser().resolve()
BACKEND_SCRIPT = BACKEND_DIR / "analyse_song.py"
BACKEND_PYTHON = BACKEND_DIR / "voxai_env" / "bin" / "python"
PYTHON_BIN = shutil.which("python3") or sys.executable

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


@dataclass
class Metadata:
    singer: str | None
    song: str | None
    artist: str | None
    context: str | None
    goal: str | None
    message: str
    sender_name: str | None
    sender_id: str | None
    chat_id: str | None
    recording_date: str


def slugify(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    normalised = unicodedata.normalize("NFKD", value)
    ascii_value = normalised.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or fallback


def verify_knowledge() -> dict:
    script = WORKSPACE / "scripts" / "verify_voxai_knowledge.py"
    result = subprocess.run(
        [PYTHON_BIN, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        raise RuntimeError("Knowledge verification produced no output.")
    payload = json.loads(result.stdout)
    payload["exit_code"] = result.returncode
    return payload


def next_take_number(recording_date: str, singer_slug: str, song_slug: str) -> int:
    pattern = re.compile(
        rf"^{re.escape(recording_date)}-{re.escape(singer_slug)}-{re.escape(song_slug)}-take-(\d{{3}})"
    )
    seen: list[int] = []
    scan_dirs = [
        UPLOADS_RAW_DIR,
        UPLOADS_PROCESSED_DIR,
        MEMORY_DIR / "analyses",
        MEMORY_DIR / "pending",
    ]
    for folder in scan_dirs:
        if not folder.exists():
            continue
        for item in folder.iterdir():
            match = pattern.match(item.stem)
            if match:
                seen.append(int(match.group(1)))
    return max(seen, default=0) + 1


def build_base_name(recording_date: str, singer_slug: str, song_slug: str, take_number: int) -> str:
    return f"{recording_date}-{singer_slug}-{song_slug}-take-{take_number:03d}"


def ensure_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not installed or not available in PATH.")
    return ffmpeg


def recording_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    return "document"


def extract_audio(source_path: Path, destination_path: Path) -> None:
    ffmpeg = ensure_ffmpeg()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "44100",
        str(destination_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Audio extraction failed.")


def run_backend(input_path: Path, singer_name: str) -> tuple[Path, Path]:
    if not BACKEND_SCRIPT.exists():
        raise RuntimeError(f"Missing backend script: {BACKEND_SCRIPT}")
    backend_python = str(BACKEND_PYTHON) if BACKEND_PYTHON.exists() else PYTHON_BIN
    cmd = [
        backend_python,
        str(BACKEND_SCRIPT),
        str(input_path),
        "--name",
        singer_name,
        "--separate-stems",
    ]
    result = subprocess.run(
        cmd,
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Backend analysis failed.")
    json_output = BACKEND_DIR / "output" / f"{input_path.stem}_analysis.json"
    report_output = BACKEND_DIR / "reports" / f"{input_path.stem}_report.md"
    if not json_output.exists():
        raise RuntimeError(f"Expected backend JSON output not found: {json_output}")
    if not report_output.exists():
        raise RuntimeError(f"Expected backend report not found: {report_output}")
    return json_output, report_output


def normalise_backend_metrics(raw_metrics: dict) -> dict:
    return {
        "source": "voxai-local-analysis/analyse_song.py",
        "metrics_available": True,
        "analysis_input_file": raw_metrics.get("analysis_input_file"),
        "file_name": raw_metrics.get("file_name"),
        "duration_seconds": raw_metrics.get("duration_seconds"),
        "sample_rate": raw_metrics.get("sample_rate"),
        "stem_separation": raw_metrics.get("stem_separation"),
        "pitch": raw_metrics.get("pitch"),
        "perturbation": raw_metrics.get("perturbation"),
        "hnr": raw_metrics.get("hnr"),
        "resonance": raw_metrics.get("resonance"),
        "dynamics": raw_metrics.get("dynamics"),
        "rhythm": raw_metrics.get("rhythm"),
        "formants": raw_metrics.get("formants"),
        "vibrato": raw_metrics.get("vibrato"),
        "time_diagnostics": raw_metrics.get("time_diagnostics"),
        "visual_diagnostics": raw_metrics.get("visual_diagnostics"),
        "diagnostic_flags": raw_metrics.get("diagnostic_flags", []),
        "archetype": raw_metrics.get("archetype"),
        "notes": [
            "Metrics were normalised directly from the existing local VOX backend JSON.",
            "Time buckets and visual diagnostics are supporting evidence only, especially for karaoke/live-room recordings.",
        ],
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_memory_paths(base_name: str, singer_slug: str, song_slug: str) -> dict:
    return {
        "singer_memory": str(MEMORY_DIR / "singers" / f"{singer_slug}.md"),
        "song_memory": str(MEMORY_DIR / "songs" / f"{song_slug}.md"),
        "analysis_record": str(MEMORY_DIR / "analyses" / f"{base_name}.md"),
        "progress_log": str(MEMORY_DIR / "progress" / f"{singer_slug}-progress-log.md"),
        "song_progress_log": str(MEMORY_DIR / "progress" / f"{singer_slug}-{song_slug}-progress-log.md"),
        "best_take": str(MEMORY_DIR / "best-takes" / f"{singer_slug}-{song_slug}-current-best.md"),
        "drill_history": str(MEMORY_DIR / "drill-history" / f"{singer_slug}-drill-history.md"),
    }


def append_log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else ""
    LOG_PATH.write_text(existing + message + "\n", encoding="utf-8")


def save_pending_record(base_name: str, raw_path: Path, metadata: Metadata) -> Path:
    pending_path = MEMORY_DIR / "pending" / f"{base_name}.md"
    lines = [
        "# Pending VOX Upload",
        "",
        f"- Date: {metadata.recording_date}",
        f"- File: {raw_path}",
        f"- Message: {metadata.message}",
        f"- Sender: {metadata.sender_name or 'Unknown'}",
        f"- Chat ID: {metadata.chat_id or 'Unknown'}",
        "- Missing: singer and/or song",
    ]
    pending_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return pending_path


def prepare_command(args: argparse.Namespace) -> int:
    source_path = Path(args.source_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_path}")

    metadata = Metadata(
        singer=args.singer,
        song=args.song,
        artist=args.artist,
        context=args.context,
        goal=args.goal,
        message=args.message,
        sender_name=args.sender_name,
        sender_id=args.sender_id,
        chat_id=args.chat_id,
        recording_date=args.recording_date or date.today().isoformat(),
    )

    singer_slug = slugify(metadata.singer, "unknown-singer")
    song_slug = slugify(metadata.song, "unknown-song")
    take_number = args.take_number or next_take_number(metadata.recording_date, singer_slug, song_slug)
    base_name = build_base_name(metadata.recording_date, singer_slug, song_slug, take_number)
    raw_destination = UPLOADS_RAW_DIR / f"{base_name}{source_path.suffix.lower()}"
    raw_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, raw_destination)

    if not metadata.singer or not metadata.song:
        pending_path = save_pending_record(base_name, raw_destination, metadata)
        payload = {
            "status": "needs_clarification",
            "clarification_prompt": "I can analyse this properly — who is singing, and what song is it?",
            "raw_upload_path": str(raw_destination),
            "pending_record_path": str(pending_path),
            "recording_type": recording_type_for(source_path),
            "message": metadata.message,
        }
        print(json.dumps(payload, indent=2))
        return 0

    knowledge_check = verify_knowledge()
    knowledge_check_path = TEMP_DIR / "metric-json" / f"{base_name}-knowledge-check.json"
    write_json(knowledge_check_path, knowledge_check)

    processed_audio_path: Path | None = None
    analysis_input_path = raw_destination
    if source_path.suffix.lower() in VIDEO_EXTENSIONS:
        processed_audio_path = UPLOADS_PROCESSED_DIR / f"{base_name}.wav"
        extract_audio(raw_destination, processed_audio_path)
        analysis_input_path = processed_audio_path

    backend_json_path, backend_report_path = run_backend(analysis_input_path, metadata.singer)
    raw_metrics = json.loads(backend_json_path.read_text(encoding="utf-8"))
    normalised_metrics = normalise_backend_metrics(raw_metrics)
    normalised_metrics_path = TEMP_DIR / "metric-json" / f"{base_name}-normalised.json"
    write_json(normalised_metrics_path, normalised_metrics)

    memory_paths = build_memory_paths(base_name, singer_slug, song_slug)
    manifest = {
        "status": "ready",
        "advanced_compliance": bool(knowledge_check.get("advanced_compliant")),
        "knowledge_check_path": str(knowledge_check_path),
        "metadata": {
            "date": metadata.recording_date,
            "singer": metadata.singer,
            "song": metadata.song,
            "artist": metadata.artist,
            "take_number": take_number,
            "recording_type": recording_type_for(source_path),
            "message": metadata.message,
            "context": metadata.context,
            "goal": metadata.goal,
            "sender_name": metadata.sender_name,
            "sender_id": metadata.sender_id,
            "chat_id": metadata.chat_id,
        },
        "paths": {
            "raw_upload": str(raw_destination),
            "processed_audio": str(processed_audio_path) if processed_audio_path else None,
            "analysis_input": str(analysis_input_path),
            "backend_json": str(backend_json_path),
            "backend_report": str(backend_report_path),
            "visual_diagnostics": (
                raw_metrics.get("visual_diagnostics", {}).get("plot_path")
                if isinstance(raw_metrics.get("visual_diagnostics"), dict)
                else None
            ),
            "normalised_metrics": str(normalised_metrics_path),
            "knowledge_core": str(KNOWLEDGE_DIR / "VOXAI_Knowledge_Core.txt"),
            "exercise_library": str(KNOWLEDGE_DIR / "VOXAI_Scientific_Exercise_Library.txt"),
            **memory_paths,
        },
        "memory_exists": {
            key: Path(path).exists()
            for key, path in memory_paths.items()
        },
        "required_analysis_sections": [
            "Quick Summary",
            "Singer / Song / Context",
            "Performance Readiness Score",
            "What Is Working",
            "Main Issues Holding It Back",
            "Measured / Directly Heard",
            "Inferred",
            "Unverifiable",
            "Technical Breakdown",
            "Drill Prescription",
            "Next Recording Target",
        ],
        "optional_expansion": {
            "name": "Whole Song Training Plan",
            "offer_in_reply": True,
            "trigger": "User asks for the expanded plan, full-song plan, or more exercises.",
            "max_supporting_drills": 5,
            "principle": (
                "Keep the main reply focused on one primary drill. If requested, add five supporting drills "
                "for secondary song issues without replacing the primary drill."
            ),
            "supporting_drill_targets": [
                "Pitch / Intonation",
                "Rhythm / Timing",
                "Intensity / Shouting Control",
                "Tone / Resonance",
                "Phrase Shape / Performance Delivery",
            ],
            "required_sections": [
                "Whole-Song Diagnosis",
                "Primary Drill Recap",
                "Five Supporting Exercises",
                "Seven-Day Practice Plan",
                "Next Full-Song Recording Target",
            ],
        },
    }
    manifest_path = TEMP_DIR / "metric-json" / f"{base_name}-manifest.json"
    write_json(manifest_path, manifest)
    print(json.dumps({"manifest_path": str(manifest_path), **manifest}, indent=2))
    return 0


def append_progress_entry(path: Path, entry: str) -> None:
    def normalise_block(block: str) -> str:
        return block.strip().removeprefix("## ").strip()

    heading = normalise_block(entry.splitlines()[0])
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    blocks = [normalise_block(block) for block in re.split(r"(?m)^## ", existing) if block.strip()]
    filtered_blocks = [block for block in blocks if block.splitlines()[0].strip() != heading]

    new_blocks = [*filtered_blocks, normalise_block(entry)]
    rendered = "\n\n".join(f"## {block}" for block in new_blocks) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def save_report_command(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser().resolve()
    analysis_path = Path(args.analysis_path).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "ready":
        raise RuntimeError("Manifest is not in ready state.")
    if not analysis_path.exists():
        raise FileNotFoundError(f"Analysis markdown not found: {analysis_path}")

    metadata = manifest["metadata"]
    take_number = metadata["take_number"]
    song_name = metadata["song"] or "Unknown Song"
    progress_entry = "\n".join(
        [
            f"## {metadata['date']} — {song_name} — Take {take_number}",
            "",
            "Summary:",
            f"- {args.summary}",
            "",
            "Primary Pillars:",
            f"- {args.primary_pillar}",
            "",
            "Main Improvement:",
            f"- {args.main_improvement}",
            "",
            "Still Present:",
            f"- {args.still_present}",
            "",
            "Prescribed Drill:",
            f"- {args.drill_name}",
            "",
            "Drill Result:",
            f"- {args.drill_result}",
            "",
            "Next-Take Target:",
            f"- {args.next_take_target}",
            "",
            "Memory Decision:",
            f"- {args.memory_decision}",
            "",
            "Expansion Plan:",
            f"- Offered: {args.expansion_offered}",
            f"- Requested: {args.expansion_requested}",
            f"- Path: {args.expansion_plan_path or 'none'}",
            "",
        ]
    )

    progress_log = Path(manifest["paths"]["progress_log"])
    song_progress_log = Path(manifest["paths"]["song_progress_log"])
    append_progress_entry(progress_log, progress_entry)
    append_progress_entry(song_progress_log, progress_entry)
    append_log(f"{metadata['date']} saved analysis for {metadata['singer']} / {song_name} take {take_number}")

    payload = {
        "status": "saved",
        "analysis_path": str(analysis_path),
        "progress_log": str(progress_log),
        "song_progress_log": str(song_progress_log),
    }
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 1 helpers for the Candi VOX Coach MVP.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Save a raw upload, run the backend, and build a Candi manifest.")
    prepare.add_argument("--source-path", required=True)
    prepare.add_argument("--message", required=True)
    prepare.add_argument("--singer")
    prepare.add_argument("--song")
    prepare.add_argument("--artist")
    prepare.add_argument("--context")
    prepare.add_argument("--goal")
    prepare.add_argument("--take-number", type=int)
    prepare.add_argument("--sender-name")
    prepare.add_argument("--sender-id")
    prepare.add_argument("--chat-id")
    prepare.add_argument("--recording-date")
    prepare.set_defaults(func=prepare_command)

    save_report = subparsers.add_parser("save-report", help="Update progress logs for a completed Candi analysis.")
    save_report.add_argument("--manifest", required=True)
    save_report.add_argument("--analysis-path", required=True)
    save_report.add_argument("--summary", required=True)
    save_report.add_argument("--primary-pillar", required=True)
    save_report.add_argument("--main-improvement", required=True)
    save_report.add_argument("--still-present", required=True)
    save_report.add_argument("--drill-name", required=True)
    save_report.add_argument("--next-take-target", required=True)
    save_report.add_argument("--drill-result", default="unknown")
    save_report.add_argument("--memory-decision", default="progress log")
    save_report.add_argument("--expansion-offered", default="true")
    save_report.add_argument("--expansion-requested", default="false")
    save_report.add_argument("--expansion-plan-path")
    save_report.set_defaults(func=save_report_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
