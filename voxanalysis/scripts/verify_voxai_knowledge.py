#!/usr/bin/env python3
"""Hard verification for the two required VOXAI knowledge files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = WORKSPACE / "openclaw-data" / "vox-coach" / "knowledge"
REQUIRED_FILES = [
    "VOXAI_Knowledge_Core.txt",
    "VOXAI_Scientific_Exercise_Library.txt",
]


def inspect_file(path: Path) -> dict:
    result = {
        "path": str(path),
        "present": path.exists(),
        "is_file": path.is_file(),
        "readable": False,
        "retrievable": False,
        "bytes": 0,
        "sha256": None,
        "sample_heading": None,
    }
    if not path.exists() or not path.is_file():
        return result

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    result["readable"] = True
    result["retrievable"] = bool(text.strip())
    result["bytes"] = path.stat().st_size
    result["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    for line in text.splitlines():
        line = line.strip()
        if line:
            result["sample_heading"] = line[:160]
            break
    return result


def main() -> int:
    files = {
        name: inspect_file(KNOWLEDGE_DIR / name)
        for name in REQUIRED_FILES
    }
    advanced_compliant = all(
        item["present"] and item["is_file"] and item["readable"] and item["retrievable"]
        for item in files.values()
    )
    payload = {
        "knowledge_dir": str(KNOWLEDGE_DIR),
        "required_files": REQUIRED_FILES,
        "files": files,
        "advanced_compliant": advanced_compliant,
    }
    print(json.dumps(payload, indent=2))
    return 0 if advanced_compliant else 1


if __name__ == "__main__":
    raise SystemExit(main())
