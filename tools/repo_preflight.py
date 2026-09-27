#!/usr/bin/env python3
"""Enforce branch, verification, and push gates for repository work.

Use ``start`` before changing a repository and ``finish`` immediately after
pushing a task branch.  ``finish`` fails closed unless it can prove the branch
still includes the fetched base, the worktree contains only declared residue,
all requested output paths exist, the requested tests pass, and the remote ref
matches local ``HEAD``.

Examples::

    python3 tools/repo_preflight.py start --branch codex/fix-report-validator
    python3 tools/repo_preflight.py finish \
      --branch codex/fix-report-validator \
      --expect-file scripts/candi_phase1.py \
      --test "python3 -m unittest tools/test_repo_preflight.py" \
      --test "python3 -m py_compile scripts/candi_phase1.py"

The default is deliberately strict: an untracked, modified, deleted, or staged
file blocks the run.  A caller may acknowledge a known unrelated untracked
file with ``--allow-untracked relative/path``; this exception is reported in
the final result and never hides modified or staged content.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Sequence


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


class Repository:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.root, text=True, capture_output=True
        )
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
            raise RuntimeError(f"git {' '.join(args)}: {detail}")
        return result.stdout.strip()


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def check_worktree(repo: Repository, allowed_untracked: set[str]) -> Check:
    entries = repo.git("status", "--porcelain=v1").splitlines()
    blocked: list[str] = []
    allowed: list[str] = []
    for entry in entries:
        if not entry:
            continue
        state, path = entry[:2], entry[3:]
        if state == "??" and path in allowed_untracked:
            allowed.append(path)
        else:
            blocked.append(entry)
    if blocked:
        return Check("clean worktree", False, "unresolved changes: " + "; ".join(blocked))
    if allowed:
        return Check("clean worktree", True, "declared untracked residue: " + ", ".join(allowed))
    return Check("clean worktree", True, "clean")


def check_fresh_base(repo: Repository, base_ref: str) -> Check:
    try:
        base = repo.git("rev-parse", "--verify", base_ref)
        common = repo.git("merge-base", "HEAD", base_ref)
    except RuntimeError as exc:
        return Check("fresh base", False, str(exc))
    if common != base:
        return Check(
            "fresh base", False,
            f"{base_ref} ({base[:12]}) is not an ancestor of HEAD; merge or rebase it first",
        )
    return Check("fresh base", True, f"includes {base_ref} at {base[:12]}")


def check_branch(repo: Repository, expected: str) -> Check:
    try:
        actual = repo.git("branch", "--show-current")
    except RuntimeError as exc:
        return Check("expected branch", False, str(exc))
    if actual != expected:
        return Check("expected branch", False, f"on {actual or 'detached HEAD'}, expected {expected}")
    return Check("expected branch", True, actual)


def check_outputs(root: Path, files: Sequence[str], directories: Sequence[str]) -> list[Check]:
    checks: list[Check] = []
    for value in files:
        path = resolve_path(root, value)
        checks.append(Check("output file", path.is_file(), str(path)))
    for value in directories:
        path = resolve_path(root, value)
        checks.append(Check("output directory", path.is_dir(), str(path)))
    return checks


def run_tests(root: Path, commands: Sequence[str]) -> list[Check]:
    checks: list[Check] = []
    for command in commands:
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            checks.append(Check("test", False, f"invalid command {command!r}: {exc}"))
            continue
        if not argv:
            checks.append(Check("test", False, "empty command"))
            continue
        result = subprocess.run(argv, cwd=root, text=True, capture_output=True)
        output = (result.stdout + result.stderr).strip().replace("\n", " | ")
        detail = f"{command!r} exited {result.returncode}"
        if output:
            detail += f": {output[-800:]}"
        checks.append(Check("test", result.returncode == 0, detail))
    return checks


def check_remote_sha(repo: Repository, branch: str) -> Check:
    try:
        upstream = repo.git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        if "/" not in upstream:
            return Check("remote SHA", False, f"unexpected upstream name {upstream!r}")
        remote, remote_branch = upstream.split("/", 1)
        if remote_branch != branch:
            return Check("remote SHA", False, f"upstream is {upstream}, expected {remote}/{branch}")
        local_sha = repo.git("rev-parse", "HEAD")
        remote_sha = repo.git("ls-remote", remote, f"refs/heads/{branch}").split()
    except RuntimeError as exc:
        return Check("remote SHA", False, str(exc))
    if not remote_sha:
        return Check("remote SHA", False, f"{remote}/{branch} does not exist")
    if remote_sha[0] != local_sha:
        return Check(
            "remote SHA", False,
            f"local {local_sha[:12]} != {remote}/{branch} {remote_sha[0][:12]}",
        )
    return Check("remote SHA", True, f"{remote}/{branch} == {local_sha[:12]}")


def report(status: str, repo: Repository, checks: Sequence[Check], *, json_output: bool) -> int:
    payload = {
        "status": status,
        "repository": str(repo.root),
        "head": repo.git("rev-parse", "HEAD"),
        "checks": [asdict(check) for check in checks],
    }
    if json_output:
        print(json.dumps(payload, indent=2))
    else:
        for check in checks:
            prefix = "ok" if check.ok else "FAIL"
            print(f"{prefix:4} {check.name}: {check.detail}")
        print(f"\nSTATUS: {status}")
    return 0 if status == "complete and verified" else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("start", "finish"))
    parser.add_argument("--repo", default=".", help="repository root (default: current directory)")
    parser.add_argument("--branch", required=True, help="branch that is authorised for this task")
    parser.add_argument("--base-ref", default="origin/main", help="fresh base ref (default: origin/main)")
    parser.add_argument("--allow-untracked", action="append", default=[], metavar="PATH")
    parser.add_argument("--expect-file", action="append", default=[], metavar="PATH")
    parser.add_argument("--expect-dir", action="append", default=[], metavar="PATH")
    parser.add_argument("--test", action="append", default=[], metavar="COMMAND")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)

    repo = Repository(Path(args.repo))
    checks: list[Check] = []
    try:
        repo.git("rev-parse", "--is-inside-work-tree")
        repo.git("fetch", "origin")
    except RuntimeError as exc:
        checks.append(Check("repository access", False, str(exc)))
        return report("blocked", repo, checks, json_output=args.json_output)

    checks.extend((
        check_branch(repo, args.branch),
        check_fresh_base(repo, args.base_ref),
        check_worktree(repo, set(args.allow_untracked)),
    ))
    if not all(check.ok for check in checks):
        return report("blocked", repo, checks, json_output=args.json_output)

    if args.phase == "start":
        return report("complete and verified", repo, checks, json_output=args.json_output)

    checks.extend(check_outputs(repo.root, args.expect_file, args.expect_dir))
    if not args.test:
        checks.append(Check("test execution", False, "finish requires at least one --test command"))
    if not all(check.ok for check in checks):
        return report("blocked", repo, checks, json_output=args.json_output)

    checks.extend(run_tests(repo.root, args.test))
    checks.append(check_remote_sha(repo, args.branch))
    if all(check.ok for check in checks):
        return report("complete and verified", repo, checks, json_output=args.json_output)
    return report("partially complete", repo, checks, json_output=args.json_output)


if __name__ == "__main__":
    raise SystemExit(main())
