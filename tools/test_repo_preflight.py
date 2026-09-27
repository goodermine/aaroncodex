"""Behaviour tests for tools/repo_preflight.py.

Run with: python3 -m unittest tools/test_repo_preflight.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "repo_preflight.py"


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)


class RepositoryPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.remote = self.root / "origin.git"
        self.repo = self.root / "work"
        run("git", "init", "--bare", str(self.remote))
        run("git", "clone", str(self.remote), str(self.repo))
        run("git", "config", "user.email", "test@example.invalid", cwd=self.repo)
        run("git", "config", "user.name", "Preflight Test", cwd=self.repo)
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        run("git", "add", "README.md", cwd=self.repo)
        run("git", "commit", "-m", "base", cwd=self.repo)
        run("git", "branch", "-M", "main", cwd=self.repo)
        run("git", "push", "-u", "origin", "main", cwd=self.repo)
        run("git", "checkout", "-b", "codex/preflight-test", cwd=self.repo)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def invoke(self, phase: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOL), phase, "--repo", str(self.repo),
             "--branch", "codex/preflight-test", "--json", *args],
            text=True, capture_output=True,
        )

    def test_start_accepts_fresh_clean_branch(self) -> None:
        result = self.invoke("start")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "complete and verified")

    def test_start_blocks_dirty_worktree(self) -> None:
        (self.repo / "scratch.txt").write_text("untracked\n", encoding="utf-8")
        result = self.invoke("start")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("scratch.txt", str(payload["checks"]))

    def test_start_blocks_wrong_branch(self) -> None:
        result = self.invoke("start", "--branch", "codex/not-this-task")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "blocked")
        branch = next(x for x in payload["checks"] if x["name"] == "expected branch")
        self.assertFalse(branch["ok"])

    def test_start_blocks_base_that_advanced_remotely(self) -> None:
        updater = self.root / "updater"
        run("git", "clone", str(self.remote), str(updater))
        run("git", "config", "user.email", "test@example.invalid", cwd=updater)
        run("git", "config", "user.name", "Preflight Test", cwd=updater)
        run("git", "checkout", "-b", "main", "origin/main", cwd=updater)
        (updater / "README.md").write_text("new main\n", encoding="utf-8")
        run("git", "add", "README.md", cwd=updater)
        run("git", "commit", "-m", "advance main", cwd=updater)
        run("git", "push", "origin", "main", cwd=updater)

        result = self.invoke("start")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "blocked")
        fresh = next(x for x in payload["checks"] if x["name"] == "fresh base")
        self.assertFalse(fresh["ok"])

    def test_finish_verifies_outputs_tests_and_remote_sha(self) -> None:
        (self.repo / "result.txt").write_text("done\n", encoding="utf-8")
        run("git", "add", "result.txt", cwd=self.repo)
        run("git", "commit", "-m", "result", cwd=self.repo)
        run("git", "push", "-u", "origin", "codex/preflight-test", cwd=self.repo)
        # Narrow-fetch repositories may not have this local tracking ref. The
        # guard must still verify the configured upstream via git ls-remote.
        run("git", "update-ref", "-d", "refs/remotes/origin/codex/preflight-test", cwd=self.repo)
        outside_output = self.root / "generated.txt"
        outside_output.write_text("generated\n", encoding="utf-8")
        result = self.invoke(
            "finish", "--expect-file", str(outside_output),
            "--test", f"{sys.executable} -c \"print('ok')\"",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "complete and verified")
        self.assertTrue(next(x for x in payload["checks"] if x["name"] == "remote SHA")["ok"])


if __name__ == "__main__":
    unittest.main()
