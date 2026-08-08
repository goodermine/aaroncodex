#!/usr/bin/env python3
"""Generate the standalone VOX systems hub — a single self-contained HTML file
Candy can host anywhere (any static host, or ``python3 -m http.server``).

It reads the ONE registry (``voxsuite/src/voxsuite/server/systems.py``) and bakes
in each system's absolute URL under the base you give it. The page also polls
``<base>/api/systems`` on load and every 30 s, so even without re-running this it
picks up systems that were added/renamed/moved whenever the suite is reachable —
and falls back to the baked-in list when it isn't.

Re-run this whenever the suite's public address changes:

    python3 tools/build_hub.py --base https://vox.example.ts.net
    # writes voxsuite/dist/hub.html  → hand that file to Candy

The live, always-current version lives at ``<suite>/hub``; this is the portable
mirror for when Candy hosts it herself off a different origin.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "voxsuite" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def build(base: str, generated: str | None = None) -> str:
    """Return the standalone hub HTML with absolute links under ``base``."""
    from voxsuite.server.hubpage import render
    from voxsuite.server.systems import resolve

    base = base.rstrip("/")
    systems = resolve(app=None, base_url=base)   # live=None: the page's refresh fills the dots
    return render(
        systems,
        api_url=base + "/api/systems",
        standalone=True,
        base_url=base,
        generated=generated or date.today().isoformat(),
    )


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="build_hub", description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True,
                    help="the suite's public base address, e.g. https://vox.example.ts.net")
    ap.add_argument("--out", default=str(REPO / "voxsuite" / "dist" / "hub.html"),
                    help="output file (default voxsuite/dist/hub.html)")
    args = ap.parse_args(argv)

    html = build(args.base)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  ({len(html):,} bytes, pointing at {args.base.rstrip('/')})")
    print("Host that single file anywhere; it self-refreshes from the suite when reachable.")


if __name__ == "__main__":
    main()
