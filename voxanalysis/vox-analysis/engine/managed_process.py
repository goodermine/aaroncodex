#!/usr/bin/env python3
"""Managed subprocesses for the analysis pipeline.

Why this exists: an Aaron G analysis failed because the orchestration around
the engine had no process groups, no progress, no timeout of its own and no
error detail. An agent killed some separator PIDs by hand, left a RoFormer
child running, started a second separation on top of it, gave up after an
arbitrary eight minutes, and the wrapper reported only
``RuntimeError: Backend analysis failed``. The singer was then told to send a
shorter clip, although nothing had shown the clip was the problem.

This module gives every long-running stage the same guarantees:

* **One active separation per host/queue.** ``separation_lock`` takes an
  exclusive ``flock``. The lock's file descriptor is passed down to the
  separator, so a separator orphaned by a hard kill keeps holding the lock.
  The next job then waits in the queue (with a heartbeat that names the
  holder) instead of competing with it for the CPU.
* **Process groups and tree-safe cancellation.** Each child starts in its own
  session/process group. Timeouts, SIGTERM/SIGINT/SIGHUP and the ``cancel``
  command stop the whole group: SIGTERM, a grace period, then SIGKILL. Members
  of the group still alive after the leader exits are reaped too.
* **Structured failure records.** Every failure carries the command, stage,
  exit code, elapsed time, the stdout/stderr tails and the full log paths, and
  a ``kind``: timeout, resource_limit, busy, cancelled, killed, dependency or
  error. Only timeout and resource_limit set ``shorter_clip_may_help``.
* **Heartbeat.** A JSON status file is rewritten every few seconds with the
  state, elapsed time, timeout, PID/PGID and the separator's progress, and a
  one-line heartbeat is echoed to stderr.
* **Timeouts owned by the repository** (overridable by environment):
  ``VOX_SEPARATION_TIMEOUT`` (default 30 min, the same budget as
  ``pitch_track.STEM_TIMEOUT_SECONDS``), ``VOX_SEPARATION_LOCK_WAIT`` (30 min)
  and ``VOX_BACKEND_TIMEOUT`` (the lock wait plus the separation plus 20 min
  for the analysis itself). No caller should impose its own wall-clock rule.

CLI (use this instead of killing PIDs by hand)::

    python3 managed_process.py status            # who holds the separation lock
    python3 managed_process.py cancel            # stop the holder's whole tree
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

try:  # POSIX only; on other platforms the lock degrades to a no-op.
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None


def env_seconds(name: str, default: float, minimum: float = 1.0,
                maximum: float = 24 * 3600.0) -> float:
    """A positive, bounded duration from the environment, else ``default``."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return float(default)
    try:
        value = float(raw)
    except ValueError:
        return float(default)
    return float(min(max(value, minimum), maximum))


DEFAULT_SEPARATION_TIMEOUT_S = 30 * 60
DEFAULT_LOCK_WAIT_S = 30 * 60
ANALYSIS_MARGIN_S = 20 * 60
HEARTBEAT_INTERVAL_S = 15.0
KILL_GRACE_S = 10.0
TAIL_BYTES = 64 * 1024


def separation_timeout_s() -> float:
    return env_seconds("VOX_SEPARATION_TIMEOUT", DEFAULT_SEPARATION_TIMEOUT_S)


def lock_wait_s() -> float:
    return env_seconds("VOX_SEPARATION_LOCK_WAIT", DEFAULT_LOCK_WAIT_S, minimum=0.0)


def backend_timeout_s() -> float:
    default = lock_wait_s() + separation_timeout_s() + ANALYSIS_MARGIN_S
    return env_seconds("VOX_BACKEND_TIMEOUT", default)


def state_dir() -> Path:
    return Path(os.environ.get("VOX_STATE_DIR", Path.home() / ".cache" / "vox")).expanduser()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json_atomic(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _tail(path: Path | None, limit: int = TAIL_BYTES) -> str:
    if not path:
        return ""
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - limit))
            data = handle.read()
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")


# ---------------------------------------------------------------- progress

_TQDM = re.compile(r"(\d{1,3})%\|[^\r\n|]*\|\s*(\d+)/(\d+)")


def tqdm_progress(stderr_tail: str) -> dict | None:
    """Last tqdm bar in audio-separator's stderr, e.g. ``42%|... | 8/19``."""
    matches = list(_TQDM.finditer(stderr_tail))
    if not matches:
        return None
    pct, done, total = matches[-1].groups()
    return {"percent": int(pct), "done": int(done), "total": int(total)}


def heartbeat_line_progress(prefix: str):
    """Progress parser that surfaces a child's own last heartbeat line."""
    def parse(stderr_tail: str) -> dict | None:
        lines = [ln for ln in re.split(r"[\r\n]+", stderr_tail) if ln.startswith(prefix)]
        return {"child_heartbeat": lines[-1]} if lines else None
    return parse


# ---------------------------------------------------------------- failures

_RESOURCE_PATTERNS = re.compile(
    r"MemoryError|Cannot allocate memory|out of memory|OOM|No space left on device"
    r"|std::bad_alloc|Killed\s*$",
    re.IGNORECASE | re.MULTILINE,
)

SHORTER_CLIP_KINDS = ("timeout", "resource_limit")


def classify(exit_code: int | None, timed_out: bool, cancelled: bool, stderr_tail: str) -> str:
    """timeout | cancelled | resource_limit | killed | error.

    A bare SIGKILL is ``killed``, not ``resource_limit``: an out-of-memory kill
    and a hand ``kill -9`` look the same from here, and only evidence in the
    output (MemoryError, "No space left on device", ...) confirms a resource
    limit. That keeps a hand-killed job from turning into "send a shorter clip".
    """
    if timed_out:
        return "timeout"
    if cancelled:
        return "cancelled"
    if _RESOURCE_PATTERNS.search(stderr_tail or ""):
        return "resource_limit"
    if exit_code is not None and (exit_code < 0 or exit_code in (128 + signal.SIGKILL, 128 + signal.SIGTERM)):
        return "killed"
    return "error"


class StageFailure(RuntimeError):
    """A stage failed. ``record`` is the structured, JSON-safe failure record."""

    def __init__(self, record: dict):
        self.record = record
        super().__init__(record.get("summary") or f"{record.get('stage')} failed")


def failure_record(*, stage: str, command, kind: str, exit_code=None, elapsed_s=None,
                   started_at=None, cwd=None, timeout_s=None, stdout_log=None, stderr_log=None,
                   summary=None, extra: dict | None = None) -> dict:
    stdout_tail = _tail(stdout_log)
    stderr_tail = _tail(stderr_log)
    if summary is None:
        last = [ln for ln in re.split(r"[\r\n]+", stderr_tail or stdout_tail) if ln.strip()]
        reason = last[-1].strip() if last else "no output"
        summary = {
            "timeout": f"{stage} exceeded its {int(timeout_s or 0)} s timeout",
            "cancelled": f"{stage} was cancelled",
            "resource_limit": f"{stage} ran out of memory/disk or was killed by the system: {reason}",
            "busy": f"{stage} could not start: another separation holds the lock",
            "killed": f"{stage} was killed by a signal (exit {exit_code}) with no sign of a resource limit",
            "dependency": f"{stage}: a required Python module is missing",
        }.get(kind, f"{stage} failed (exit {exit_code}): {reason}")
    record = {
        "status": "failed",
        "stage": stage,
        "kind": kind,
        "summary": summary,
        "shorter_clip_may_help": kind in SHORTER_CLIP_KINDS,
        "command": [str(c) for c in command] if command else None,
        "cwd": str(cwd) if cwd else None,
        "exit_code": exit_code,
        "elapsed_s": round(elapsed_s, 1) if elapsed_s is not None else None,
        "timeout_s": timeout_s,
        "started_at": started_at,
        "finished_at": _now(),
        "host": socket.gethostname(),
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "stdout_log": str(stdout_log) if stdout_log else None,
        "stderr_log": str(stderr_log) if stderr_log else None,
    }
    if extra:
        record.update(extra)
    return record


# ---------------------------------------------------------------- process groups

def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def terminate_group(pgid: int, proc: subprocess.Popen | None = None,
                    grace_s: float = KILL_GRACE_S) -> None:
    """SIGTERM the whole group, wait up to ``grace_s``, then SIGKILL it."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pgid, signal.SIGTERM)
    deadline = time.monotonic() + grace_s
    while time.monotonic() < deadline:
        if proc is not None:
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=0.2)
        else:
            time.sleep(0.2)
        if not _group_alive(pgid):
            return
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pgid, signal.SIGKILL)
    if proc is not None:
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=grace_s)


class _Cancelled(BaseException):
    def __init__(self, signum: int):
        self.signum = signum


@contextlib.contextmanager
def _cancel_on_signals():
    """Turn SIGTERM/SIGINT/SIGHUP into ``_Cancelled`` while a child runs, so
    the child's whole group is stopped before this process exits."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    def handler(signum, _frame):
        raise _Cancelled(signum)
    previous = {}
    for sig in (signal.SIGTERM, signal.SIGINT, getattr(signal, "SIGHUP", None)):
        if sig is not None:
            previous[sig] = signal.signal(sig, handler)
    try:
        yield
    finally:
        for sig, old in previous.items():
            signal.signal(sig, old)


def run_managed(command, *, stage: str, timeout_s: float, cwd=None, env=None,
                log_dir=None, status_path=None, heartbeat_s: float = HEARTBEAT_INTERVAL_S,
                progress_parser=None, pass_fds=(), on_start=None, echo=True) -> dict:
    """Run ``command`` in its own process group with a timeout and heartbeat.

    Returns a success record. Raises ``StageFailure`` (with a structured
    record) on a non-zero exit, timeout, cancellation or launch error.
    stdout/stderr go to log files (no pipe can fill and stall the child).
    """
    log_dir = Path(log_dir) if log_dir else Path(tempfile.mkdtemp(prefix=f"vox-{stage}-"))
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = log_dir / f"{stage}.stdout.log"
    stderr_log = log_dir / f"{stage}.stderr.log"
    started_at, t0 = _now(), time.monotonic()
    common = dict(stage=stage, command=command, cwd=cwd, timeout_s=timeout_s,
                  started_at=started_at, stdout_log=stdout_log, stderr_log=stderr_log)

    def status(state: str, proc=None, **more) -> None:
        if not status_path:
            return
        payload = {"stage": stage, "state": state, "command": [str(c) for c in command],
                   "started_at": started_at, "updated_at": _now(),
                   "elapsed_s": round(time.monotonic() - t0, 1), "timeout_s": timeout_s,
                   "pid": proc.pid if proc else None, "pgid": proc.pid if proc else None,
                   "host": socket.gethostname(), "stderr_log": str(stderr_log), **more}
        with contextlib.suppress(OSError):
            _write_json_atomic(Path(status_path), payload)

    with open(stdout_log, "wb") as out, open(stderr_log, "wb") as err, _cancel_on_signals():
        try:
            proc = subprocess.Popen([str(c) for c in command], cwd=cwd, env=env, stdout=out,
                                    stderr=err, start_new_session=True, pass_fds=tuple(pass_fds))
        except OSError as exc:
            record = failure_record(kind="error", elapsed_s=0.0,
                                    summary=f"{stage} could not start: {exc}", **common)
            status("failed", failure=record["summary"])
            raise StageFailure(record) from exc
        if on_start:
            on_start(proc)
        timed_out = cancelled = False
        try:
            while True:
                elapsed = time.monotonic() - t0
                if elapsed >= timeout_s:
                    timed_out = True
                    terminate_group(proc.pid, proc)
                    break
                try:
                    proc.wait(timeout=min(heartbeat_s, max(0.05, timeout_s - elapsed)))
                    break
                except subprocess.TimeoutExpired:
                    tail = _tail(stderr_log, 8192)
                    progress = progress_parser(tail) if progress_parser else None
                    status("running", proc, progress=progress)
                    if echo:
                        mins = int((time.monotonic() - t0) // 60)
                        secs = int((time.monotonic() - t0) % 60)
                        extra = ""
                        if progress and "percent" in progress:
                            extra = f", {progress['percent']}% ({progress['done']}/{progress['total']})"
                        print(f"[{stage}] running {mins}m{secs:02d}s of {int(timeout_s // 60)}m "
                              f"timeout{extra}", file=sys.stderr, flush=True)
        except _Cancelled:
            cancelled = True
            terminate_group(proc.pid, proc)
        finally:
            # Stragglers: anything left in the group after the leader exited.
            if proc.poll() is not None and _group_alive(proc.pid):
                terminate_group(proc.pid, None)

    elapsed = time.monotonic() - t0
    code = proc.returncode
    if timed_out or cancelled or code != 0:
        kind = classify(code, timed_out, cancelled, _tail(stderr_log))
        record = failure_record(kind=kind, exit_code=code, elapsed_s=elapsed, **common)
        status("failed", proc, kind=kind, failure=record["summary"])
        raise StageFailure(record)
    status("succeeded", proc)
    return {"status": "succeeded", "stage": stage, "command": [str(c) for c in command],
            "exit_code": code, "elapsed_s": round(elapsed, 1), "started_at": started_at,
            "finished_at": _now(), "stdout_log": str(stdout_log), "stderr_log": str(stderr_log)}


# ---------------------------------------------------------------- separation lock

def lock_paths(queue: str | None = None) -> tuple[Path, Path]:
    queue = re.sub(r"[^A-Za-z0-9_.-]+", "-", queue or os.environ.get("VOX_SEPARATION_QUEUE", "default"))
    base = state_dir() / "locks" / f"separation-{queue}.lock"
    return base, base.with_suffix(".lock.json")


class SeparationLock:
    """Handle yielded by ``separation_lock``: pass ``fds`` to the child."""

    def __init__(self, fd: int | None, holder_path: Path, info: dict):
        self.fd, self.holder_path, self.info = fd, holder_path, info

    @property
    def fds(self) -> tuple:
        return (self.fd,) if self.fd is not None else ()

    def note_child(self, proc: subprocess.Popen) -> None:
        self.info.update({"child_pid": proc.pid, "child_pgid": proc.pid, "child_started_at": _now()})
        with contextlib.suppress(OSError):
            _write_json_atomic(self.holder_path, self.info)


@contextlib.contextmanager
def separation_lock(*, label: str, wait_s: float | None = None, queue: str | None = None,
                    status_path=None, poll_s: float = 2.0, heartbeat_s: float = HEARTBEAT_INTERVAL_S,
                    echo=True):
    """Hold the host's single separation slot for the duration of the block."""
    lock_path, holder_path = lock_paths(queue)
    if fcntl is None:  # pragma: no cover
        yield SeparationLock(None, holder_path, {"label": label})
        return
    wait_s = lock_wait_s() if wait_s is None else wait_s
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    t0 = last_beat = time.monotonic()
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                waited = time.monotonic() - t0
                holder = _read_json(holder_path) or {}
                if waited >= wait_s:
                    record = failure_record(
                        stage="separation_queue", command=None, kind="busy", elapsed_s=waited,
                        timeout_s=wait_s,
                        summary=(f"waited {int(waited)} s for the separation slot; still held by "
                                 f"pid {holder.get('pid')} ({holder.get('label')}, since "
                                 f"{holder.get('acquired_at')})"),
                        extra={"lock_path": str(lock_path), "holder": holder})
                    raise StageFailure(record)
                if time.monotonic() - last_beat >= heartbeat_s:
                    last_beat = time.monotonic()
                    if status_path:
                        with contextlib.suppress(OSError):
                            _write_json_atomic(Path(status_path), {
                                "stage": "separation", "state": "waiting_for_lock", "label": label,
                                "waited_s": round(waited, 1), "lock_wait_s": wait_s,
                                "holder": holder, "updated_at": _now()})
                    if echo:
                        print(f"[separation] waiting {int(waited)}s for the separation slot "
                              f"(held by pid {holder.get('pid')}: {holder.get('label')})",
                              file=sys.stderr, flush=True)
                time.sleep(poll_s)
        info = {"pid": os.getpid(), "pgid": os.getpgrp(), "host": socket.gethostname(),
                "label": label, "acquired_at": _now(), "lock_path": str(lock_path)}
        with contextlib.suppress(OSError):
            _write_json_atomic(holder_path, info)
        yield SeparationLock(fd, holder_path, info)
    finally:
        # Close, never LOCK_UN: a child that inherited this descriptor (an
        # orphaned separator) must keep the slot until it has really exited.
        os.close(fd)


def lock_held(queue: str | None = None) -> bool:
    if fcntl is None:  # pragma: no cover
        return False
    lock_path, _ = lock_paths(queue)
    if not lock_path.exists():
        return False
    fd = os.open(str(lock_path), os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    else:
        return False
    finally:
        os.close(fd)


def cancel_holder(queue: str | None = None, grace_s: float = KILL_GRACE_S) -> dict:
    """Tree-safely stop whoever holds the separation slot."""
    _, holder_path = lock_paths(queue)
    holder = _read_json(holder_path) or {}
    if not lock_held(queue):
        return {"cancelled": False, "reason": "no separation is running", "holder": holder}
    groups = [holder["child_pgid"]] if holder.get("child_pgid") else []
    # The holder's own group is stopped only when the holder leads it (it was
    # started by run_managed, e.g. from candi_phase1.py). A holder sharing a
    # group with, say, the web server gets a SIGTERM to its PID alone; its
    # signal handler then stops its child group.
    if holder.get("pgid") and holder.get("pgid") == holder.get("pid"):
        groups.append(holder["pgid"])
    elif holder.get("pid") and int(holder["pid"]) != os.getpid():
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(int(holder["pid"]), signal.SIGTERM)
    groups = [g for g in dict.fromkeys(groups) if g != os.getpgrp()]  # never our own
    for pgid in groups:
        terminate_group(int(pgid), None, grace_s)
    return {"cancelled": True, "groups": groups, "holder": holder,
            "still_held": lock_held(queue)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or cancel the host's separation job.")
    parser.add_argument("action", choices=("status", "cancel"))
    parser.add_argument("--queue", default=None)
    args = parser.parse_args(argv)
    if args.action == "status":
        _, holder_path = lock_paths(args.queue)
        print(json.dumps({"held": lock_held(args.queue), "holder": _read_json(holder_path),
                          "separation_timeout_s": separation_timeout_s(),
                          "lock_wait_s": lock_wait_s(), "backend_timeout_s": backend_timeout_s()},
                         indent=2))
        return 0
    print(json.dumps(cancel_holder(args.queue), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
