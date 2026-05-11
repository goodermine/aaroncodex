from __future__ import annotations

from pathlib import Path


def ensure_existing_file(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")
    return path


def ensure_output_dir(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_within_dir(file_path: Path, parent_dir: Path) -> Path:
    resolved_file = file_path.resolve()
    resolved_parent = parent_dir.resolve()
    if resolved_parent not in resolved_file.parents and resolved_file != resolved_parent:
        raise ValueError(f"Output file escaped the configured directory: {resolved_file}")
    return resolved_file
