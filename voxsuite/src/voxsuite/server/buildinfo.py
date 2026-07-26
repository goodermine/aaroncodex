"""Which build is actually being served?

A deployed deck looked identical before and after a fix, so "did the pull reach
the running service?" could only be answered by reading source on the box. This
reports the content hash of the files the server is *actually* reading, plus the
git commit of the checkout it is reading them from, so the question is answerable
from a browser.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def file_hash(path: Path) -> str | None:
    """Short content hash of a file as the server sees it on disk right now."""
    try:
        return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:12]
    except OSError:
        return None


def git_commit(start: Path) -> dict:
    """Best-effort commit of the checkout that `start` lives in."""
    info: dict = {"commit": None, "branch": None, "dirty": None}
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=str(start),
            capture_output=True, text=True, timeout=5,
        )
        if root.returncode != 0:
            return info
        top = root.stdout.strip()
        info["checkout"] = top
        for key, args in (("commit", ["rev-parse", "--short=12", "HEAD"]),
                          ("branch", ["rev-parse", "--abbrev-ref", "HEAD"])):
            r = subprocess.run(["git"] + args, cwd=top, capture_output=True,
                               text=True, timeout=5)
            if r.returncode == 0:
                info[key] = r.stdout.strip()
        st = subprocess.run(["git", "status", "--porcelain"], cwd=top,
                            capture_output=True, text=True, timeout=10)
        if st.returncode == 0:
            info["dirty"] = bool(st.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return info


def build_info(shells: dict[str, Path], extra: dict[str, Path] | None = None) -> dict:
    """`shells` maps deck name -> the deck.html path this process serves."""
    decks = {}
    for name, path in shells.items():
        p = Path(path)
        decks[name] = {"path": str(p), "sha1_12": file_hash(p),
                       "exists": p.is_file()}
    any_shell = next((Path(p) for p in shells.values()), Path.cwd())
    out = {"decks": decks, "git": git_commit(any_shell.parent)}
    if extra:
        out["assets"] = {n: file_hash(Path(p)) for n, p in extra.items()}
    return out
