"""Which build is actually being served?

A deployed deck looked identical before and after a fix, so "did the pull reach
the running service?" could only be answered by reading source on the box. This
reports the content hash of the files the server is *actually* reading, plus the
git commit of the checkout it is reading them from, so the question is answerable
from a browser.
"""

from __future__ import annotations

import hashlib
import os
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
    if not info.get("commit"):
        # Container images ship without git or a .git dir; the commit is baked in
        # at build time (VOX_BUILD_COMMIT) so the build page isn't blank there.
        baked = os.environ.get("VOX_BUILD_COMMIT")
        if baked:
            info["commit"] = baked[:12]
            info["branch"] = os.environ.get("VOX_BUILD_BRANCH") or info.get("branch")
            info["source"] = "baked at image build (no git in container)"
    return info


def head_hash(repo: str, path: Path) -> str | None:
    """Hash of `path` as committed at HEAD, for comparison with what's on disk.

    This makes the check self-validating: no hash has to be written down or kept
    in sync — the served file is compared against the checkout's own HEAD, so a
    service reading some *other* directory shows up immediately.
    """
    try:
        rel = subprocess.run(["git", "ls-files", "--full-name", str(path)], cwd=repo,
                             capture_output=True, text=True, timeout=5)
        name = rel.stdout.strip().splitlines()[0] if rel.stdout.strip() else None
        if not name:
            return None
        blob = subprocess.run(["git", "show", f"HEAD:{name}"], cwd=repo,
                              capture_output=True, timeout=10)
        if blob.returncode != 0:
            return None
        return hashlib.sha1(blob.stdout).hexdigest()[:12]
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


def build_info(shells: dict[str, Path], extra: dict[str, Path] | None = None) -> dict:
    """`shells` maps deck name -> the deck.html path this process serves."""
    any_shell = next((Path(p) for p in shells.values()), Path.cwd())
    git = git_commit(any_shell.parent)
    repo = git.get("checkout")
    decks, verdicts = {}, []
    for name, path in shells.items():
        p = Path(path)
        on_disk = file_hash(p)
        at_head = head_hash(repo, p) if repo else None
        match = None if at_head is None or on_disk is None else (on_disk == at_head)
        if match is not None:
            verdicts.append(match)
        decks[name] = {"path": str(p), "sha1_12": on_disk, "exists": p.is_file(),
                       "sha1_at_head": at_head, "matches_head": match}
    out = {
        "decks": decks,
        "git": git,
        # True only when every comparable deck matches this checkout's HEAD.
        "matches_head": (all(verdicts) if verdicts else None),
    }
    if extra:
        out["assets"] = {n: file_hash(Path(p)) for n, p in extra.items()}
    return out
