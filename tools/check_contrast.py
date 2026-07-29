#!/usr/bin/env python3
"""WCAG contrast gate for the VOX design tokens.

Reads design/vox-tokens.css and verifies every text/surface pairing the UI
actually uses meets WCAG AA (4.5:1 for normal text). The pair list below IS
the contract: add a pair when a component puts token text on a token surface.

`--vox-dim` is exempt by declaration (tertiary, never essential text), and the
magma spectrogram ramp is chart data, not text.

Exit 0 = all pairs pass. Exit 1 = failures listed.
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS = os.path.join(ROOT, "design/vox-tokens.css")

# (foreground, background, minimum ratio)
PAIRS = [
    ("--vox-ink",       "--vox-panel",       4.5),
    ("--vox-ink",       "--vox-page",        4.5),
    ("--vox-ink",       "--vox-sunken",      4.5),
    ("--vox-body",      "--vox-panel",       4.5),
    ("--vox-body",      "--vox-page",        4.5),
    ("--vox-body",      "--vox-sunken",      4.5),
    ("--vox-muted",     "--vox-panel",       4.5),
    ("--vox-muted",     "--vox-page",        4.5),
    ("--vox-muted",     "--vox-sunken",      4.5),
    ("--vox-accent",    "--vox-panel",       4.5),
    ("--vox-accent",    "--vox-page",        4.5),
    ("--vox-accent",    "--vox-accent-tint", 4.5),
    ("--vox-on-accent", "--vox-accent",      4.5),
    ("--vox-good",      "--vox-panel",       4.5),
    ("--vox-watch",     "--vox-panel",       4.5),
    ("--vox-weak",      "--vox-panel",       4.5),
    ("--vox-good",      "--vox-good-tint",   4.5),
    ("--vox-watch",     "--vox-watch-tint",  4.5),
    ("--vox-weak",      "--vox-weak-tint",   4.5),
]


def parse_tokens(path: str) -> dict:
    css = open(path).read()
    out = {}
    for name, val in re.findall(r"(--vox-[a-z0-9-]+)\s*:\s*([^;]+);", css):
        val = val.strip()
        m = re.fullmatch(r"#([0-9a-fA-F]{6})", val)
        if m:
            out[name] = tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    return out


def rel_lum(rgb) -> float:
    def chan(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg) -> float:
    l1, l2 = sorted((rel_lum(fg), rel_lum(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def main() -> int:
    toks = parse_tokens(TOKENS)
    failures = []
    for fg, bg, minimum in PAIRS:
        if fg not in toks or bg not in toks:
            failures.append(f"{fg} on {bg}: token missing from {TOKENS}")
            continue
        r = ratio(toks[fg], toks[bg])
        mark = "ok  " if r >= minimum else "FAIL"
        print(f"{mark} {r:5.2f}:1  {fg} on {bg}  (min {minimum})")
        if r < minimum:
            failures.append(f"{fg} on {bg}: {r:.2f}:1 < {minimum}:1")
    if failures:
        print("\nCONTRAST GATE FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("\ncontrast gate passed — all pairs AA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
