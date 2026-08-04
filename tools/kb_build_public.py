#!/usr/bin/env python3
"""Assemble the publishable subset of the vocal knowledge base.

    python3 tools/kb_build_public.py [--out build/kb-public] [--dry-run]

**Never publish the working tree.** Build from it. A private document leaks by
being forgotten, not by being deliberately included, so the safe shape is an
allowlist: start from nothing and copy in only what has explicitly declared
itself publishable.

Excluded, and why:
  private/                  one singer's measured body — Aaron's decision,
                            3 Aug 2026: split out and keep private for now
  08-external-reference/    another creator's work, correctly attributed; it
                            cannot ship inside a library licensed to Aaron
  sources/                  works-cited blocks — an audit trail to search, not
                            documents to read
  archive/                  superseded, retained rather than deleted
  visibility: private       per-file, wherever it appears

The folder rules and the per-file `visibility` key are deliberately redundant.
Folders get reorganised; a file gets moved; either guard alone would eventually
fail quietly, and the cost of failing here is not a typo.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kb_common import CONTENT_DIRS, KB, iter_docs, read_doc  # noqa: E402

# Folders whose contents never ship, whatever their front matter says.
EXCLUDED_DIRS = ("private", "sources", "archive", "08-external-reference")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("build", "kb-public"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    included, excluded = [], []
    for rel, full in iter_docs():
        folder = rel.split(os.sep)[0]
        fm, _body, words = read_doc(full)
        vis = fm.get("visibility")
        if folder in EXCLUDED_DIRS:
            excluded.append((rel, f"{folder}/ is never published"))
        elif folder not in CONTENT_DIRS:
            excluded.append((rel, "not in a content folder"))
        elif vis != "public":
            excluded.append((rel, f"visibility: {vis or 'unset'}"))
        else:
            included.append((rel, full, words))

    print(f"include {len(included)} document(s) · {sum(d[2] for d in included):,} words")
    print(f"exclude {len(excluded)} document(s):")
    seen: dict[str, int] = {}
    for _rel, reason in excluded:
        seen[reason] = seen.get(reason, 0) + 1
    for reason, n in sorted(seen.items(), key=lambda kv: -kv[1]):
        print(f"        {n:3}  {reason}")

    # Anything private must be in the excluded set. This is the assertion the
    # whole tool exists for, so it is checked rather than assumed.
    leaked = [rel for rel, full, _w in included
              if read_doc(full)[0].get("visibility") == "private"]
    if leaked:
        print("\nFAIL  private documents in the public set: " + ", ".join(leaked))
        return 1

    if args.dry_run:
        print("\nDry run — nothing written.")
        return 0

    out = os.path.abspath(args.out)
    if os.path.exists(out):
        shutil.rmtree(out)
    for rel, full, _words in included:
        dest = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(full, dest)
    for name in ("README.md", "TOPICS.md", "MANIFEST.md", "LICENSE"):
        src = os.path.join(KB, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(out, name))

    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
