#!/usr/bin/env python3
"""Syntax-check every JavaScript the suite ships — external files AND the inline
<script> blocks inside served HTML — with `node --check`.

This exists because of a real failure: an unterminated string was added to a
deck's inline script, so the WHOLE 52 KB script failed to parse and none of the
deck's client logic ran — yet the page still rendered its static shell, so it
looked fine. A parse error that silently disables a page must fail a gate, not
ship.

Exit codes: 0 = everything parses · 1 = a syntax error was found · 2 = node is
not available, so the check was skipped.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Shared external JS the decks/apps load with <script src>.
EXTERNAL_JS = [
    "design/vox-record.js", "design/vox-report.js",
    "design/vox-about.js", "design/vox-telemetry.js",
]
# Every shipped HTML page that carries an inline <script>.
INLINE_HTML = [
    "voxsuite/src/voxsuite/server/static/deck.html",
    "voxanalysis/vox-analysis/viewer/static/deck.html",
    "voxpolish/src/voxpolish/server/static/deck.html",
    "voxpolish/src/voxpolish/server/static/index.html",
    "pitchmonitor/index.html",
    "timbertones/index.html",
]
# <script> blocks WITHOUT a src attribute (i.e. inline code).
INLINE_RE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S)


def node_check(code: str, label: str, errors: list) -> None:
    """node --check one snippet; record (label, message) on failure."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as t:
        t.write(code)
        path = t.name
    try:
        r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
    finally:
        os.unlink(path)
    if r.returncode != 0:
        lines = (r.stderr or "").strip().splitlines()
        detail = next((l.strip() for l in lines if "SyntaxError" in l), lines[-1].strip() if lines else "syntax error")
        errors.append((label, detail))


def check_files(external=EXTERNAL_JS, html=INLINE_HTML) -> int:
    if not shutil.which("node"):
        print("check_js_syntax: node not found — SKIPPED (install Node.js to run this gate)")
        return 2
    errors: list = []
    for rel in external:
        f = ROOT / rel
        if f.is_file():
            node_check(f.read_text(encoding="utf-8"), rel, errors)
    for rel in html:
        f = ROOT / rel
        if not f.is_file():
            continue
        for i, block in enumerate(INLINE_RE.findall(f.read_text(encoding="utf-8"))):
            node_check(block, f"{rel} [inline script #{i}]", errors)
    if errors:
        print("JS SYNTAX ERRORS — a page's script will not run:")
        for label, detail in errors:
            print(f"  {label}\n      {detail}")
        return 1
    print("check_js_syntax: all external + inline scripts parse cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(check_files())
