"""Process groups, the separation slot, heartbeats and structured failures.

These pin the fixes for the Aaron G incident: a hand-killed parent left a
RoFormer child running, a second separation competed with it, an arbitrary
eight-minute wall clock gave up, and the only error that survived was
"Backend analysis failed" — which was then answered with "send a shorter clip".
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
import managed_process as M  # noqa: E402

pytestmark = pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX")


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("VOX_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("VOX_SEPARATION_QUEUE", raising=False)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # A zombie still answers kill(0); treat it as gone.
    try:
        with open(f"/proc/{pid}/stat") as handle:
            return handle.read().split()[2] != "Z"
    except OSError:
        return True


def _wait_gone(pid: int, seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not _alive(pid):
            return True
        time.sleep(0.05)
    return not _alive(pid)


def _py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_success_returns_a_record(tmp_path):
    rec = M.run_managed(_py("print('hello')"), stage="demo", timeout_s=30, log_dir=tmp_path)
    assert rec["status"] == "succeeded" and rec["exit_code"] == 0
    assert Path(rec["stdout_log"]).read_text().strip() == "hello"


def test_failure_keeps_command_exit_code_output_and_elapsed(tmp_path):
    code = "import sys; print('partial'); sys.stderr.write('torch exploded\\n'); sys.exit(3)"
    with pytest.raises(M.StageFailure) as info:
        M.run_managed(_py(code), stage="separation", timeout_s=30, log_dir=tmp_path)
    rec = info.value.record
    assert rec["stage"] == "separation" and rec["kind"] == "error"
    assert rec["exit_code"] == 3 and rec["elapsed_s"] is not None
    assert "torch exploded" in rec["stderr_tail"] and "partial" in rec["stdout_tail"]
    assert rec["command"][0] == sys.executable
    assert "torch exploded" in rec["summary"]
    assert rec["shorter_clip_may_help"] is False
    json.dumps(rec)  # JSON-safe


def test_timeout_kills_the_whole_tree(tmp_path):
    pidfile = tmp_path / "grandchild.pid"
    code = ("import subprocess,sys,time;"
            f"p=subprocess.Popen(['sleep','60']);open({str(pidfile)!r},'w').write(str(p.pid));"
            "time.sleep(60)")
    with pytest.raises(M.StageFailure) as info:
        M.run_managed(_py(code), stage="separation", timeout_s=1.5, log_dir=tmp_path,
                      heartbeat_s=0.2, echo=False)
    rec = info.value.record
    assert rec["kind"] == "timeout" and rec["shorter_clip_may_help"] is True
    assert _wait_gone(int(pidfile.read_text()))


def test_stragglers_are_reaped_after_the_leader_exits(tmp_path):
    pidfile = tmp_path / "straggler.pid"
    code = ("import subprocess;"
            f"p=subprocess.Popen(['sleep','60']);open({str(pidfile)!r},'w').write(str(p.pid))")
    M.run_managed(_py(code), stage="demo", timeout_s=30, log_dir=tmp_path)
    assert _wait_gone(int(pidfile.read_text()))


def test_resource_limit_needs_evidence_and_bare_sigkill_does_not_count(tmp_path):
    oom = "import sys; sys.stderr.write('MemoryError\\n'); sys.exit(1)"
    with pytest.raises(M.StageFailure) as info:
        M.run_managed(_py(oom), stage="separation", timeout_s=30, log_dir=tmp_path / "a")
    assert info.value.record["kind"] == "resource_limit"
    assert info.value.record["shorter_clip_may_help"] is True

    hand_kill = "import os,signal; os.kill(os.getpid(), signal.SIGKILL)"
    with pytest.raises(M.StageFailure) as info:
        M.run_managed(_py(hand_kill), stage="separation", timeout_s=30, log_dir=tmp_path / "b")
    assert info.value.record["kind"] == "killed"
    assert info.value.record["shorter_clip_may_help"] is False


def test_heartbeat_reports_separator_progress(tmp_path):
    status = tmp_path / "status.json"
    code = ("import sys,time;"
            "sys.stderr.write(' 42%|####      | 8/19 [01:00<01:20]\\r'); sys.stderr.flush();"
            "time.sleep(1.5)")
    M.run_managed(_py(code), stage="separation", timeout_s=30, log_dir=tmp_path,
                  status_path=status, heartbeat_s=0.2,
                  progress_parser=M.tqdm_progress, echo=False)
    final = json.loads(status.read_text())
    assert final["state"] == "succeeded"


def test_tqdm_and_child_heartbeat_parsers():
    tail = " 5%|▌   | 1/19 [00:56<16:49]\r 11%|█   | 2/19 [01:14<09:35]"
    assert M.tqdm_progress(tail) == {"percent": 11, "done": 2, "total": 19}
    parse = M.heartbeat_line_progress("[separation]")
    assert parse("x\n[separation] running 1m00s of 30m timeout, 11% (2/19)\n") == {
        "child_heartbeat": "[separation] running 1m00s of 30m timeout, 11% (2/19)"}


def test_one_separation_per_host_second_job_queues_then_reports_busy():
    with M.separation_lock(label="first take", wait_s=0) as slot:
        assert M.lock_held()
        with pytest.raises(M.StageFailure) as info:
            with M.separation_lock(label="second take", wait_s=0.5, poll_s=0.1):
                pass
        rec = info.value.record
        assert rec["kind"] == "busy" and rec["shorter_clip_may_help"] is False
        assert rec["holder"]["label"] == "first take"
        assert slot.fds
    assert not M.lock_held()


def test_an_orphaned_separator_keeps_the_slot_until_it_really_exits(tmp_path):
    with M.separation_lock(label="take", wait_s=0) as slot:
        child = subprocess.Popen(["sleep", "60"], pass_fds=slot.fds, start_new_session=True)
        slot.note_child(child)
    # The parent let go, but the separator still holds the inherited descriptor:
    # a new job must wait instead of competing with it.
    assert M.lock_held()
    result = M.cancel_holder(grace_s=2)
    assert result["cancelled"] is True
    child.wait(timeout=5)
    assert not M.lock_held()


def test_sigterm_to_the_orchestrator_stops_the_child_group(tmp_path):
    """Cancel the parent and the separator goes with it."""
    pidfile = tmp_path / "child.pid"
    child = tmp_path / "child.py"
    child.write_text(
        "import subprocess, sys, time\n"
        "p = subprocess.Popen(['sleep', '60'])\n"
        "open(sys.argv[1], 'w').write(str(p.pid))\n"
        "time.sleep(60)\n")
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(ENGINE)!r})\n"
        "import managed_process as M\n"
        "try:\n"
        f"    M.run_managed([sys.executable, {str(child)!r}, {str(pidfile)!r}], stage='separation',\n"
        f"                  timeout_s=60, log_dir={str(tmp_path / 'logs')!r}, heartbeat_s=0.2, echo=False)\n"
        "except M.StageFailure as f:\n"
        "    print(f.record['kind'])\n"
        "    sys.exit(9)\n")
    proc = subprocess.Popen([sys.executable, str(runner)], stdout=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 10
    while not pidfile.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert pidfile.exists()
    proc.send_signal(signal.SIGTERM)  # the parent only, as the agent did
    out, _ = proc.communicate(timeout=20)
    assert proc.returncode == 9 and out.strip() == "cancelled"
    assert _wait_gone(int(pidfile.read_text()))


def test_timeouts_are_owned_by_the_repo_and_bounded(monkeypatch):
    assert M.separation_timeout_s() == 30 * 60
    assert M.backend_timeout_s() > M.separation_timeout_s() + M.lock_wait_s()
    monkeypatch.setenv("VOX_SEPARATION_TIMEOUT", "120")
    assert M.separation_timeout_s() == 120
    monkeypatch.setenv("VOX_SEPARATION_TIMEOUT", "not a number")
    assert M.separation_timeout_s() == 30 * 60
    monkeypatch.setenv("VOX_SEPARATION_TIMEOUT", "0")
    assert M.separation_timeout_s() >= 1


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="batch_stems.sh requires ffmpeg")
def test_batch_stems_stops_the_separator_when_only_the_script_is_killed(tmp_path):
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "activate").write_text("")
    pidfile = tmp_path / "sep.pid"
    fake = venv / "bin" / "audio-separator"
    fake.write_text(f"#!/bin/sh\necho $$ > {pidfile}\nexec sleep 60\n")
    fake.chmod(0o755)
    (tmp_path / "song.wav").write_bytes(b"RIFF")
    env = dict(os.environ, PATH=f"{venv / 'bin'}:{os.environ['PATH']}")
    proc = subprocess.Popen(
        ["bash", str(ENGINE / "tools" / "stems" / "batch_stems.sh"), "--input",
         str(tmp_path / "song.wav"), "--output", str(tmp_path / "out"), "--venv", str(venv)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + 10
    while not (pidfile.exists() and pidfile.read_text().strip()) and time.monotonic() < deadline:
        time.sleep(0.05)
    sep_pid = int(pidfile.read_text())
    proc.send_signal(signal.SIGTERM)  # the script's PID only
    proc.wait(timeout=20)
    assert _wait_gone(sep_pid)


def _load_candi(monkeypatch, tmp_path, backend_body: str):
    path = ENGINE.parents[1] / "scripts" / "candi_phase1.py"
    spec = importlib.util.spec_from_file_location("candi_phase1_under_test", path)
    candi = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, candi)  # dataclasses need it registered
    spec.loader.exec_module(candi)
    backend = tmp_path / "backend"
    backend.mkdir()
    script = backend / "analyse_song.py"
    script.write_text(backend_body)
    monkeypatch.setattr(candi, "BACKEND_DIR", backend)
    monkeypatch.setattr(candi, "BACKEND_SCRIPT", script)
    monkeypatch.setattr(candi, "BACKEND_PYTHON", backend / "missing-python")
    monkeypatch.setattr(candi, "PYTHON_BIN", sys.executable)
    monkeypatch.setattr(candi, "TEMP_DIR", tmp_path / "temp")
    return candi


def test_candi_surfaces_the_engine_stage_failure_not_a_generic_error(monkeypatch, tmp_path):
    body = (
        "import json, os, sys\n"
        "json.dump({'stage': 'separation', 'kind': 'timeout', 'summary': 'separation exceeded its 1800 s timeout',\n"
        "           'shorter_clip_may_help': True, 'stderr_tail': 'tqdm 40%'}, open(os.environ['VOX_FAILURE_RECORD'], 'w'))\n"
        "sys.exit(1)\n")
    candi = _load_candi(monkeypatch, tmp_path, body)
    with pytest.raises(candi.BackendFailure) as info:
        candi.run_backend(tmp_path / "take.wav", "Aaron G", "take-001")
    rec = info.value.record
    assert rec["failed_stage"] == "separation" and rec["kind"] == "timeout"
    assert rec["exit_code"] == 1 and rec["command"]
    payload = candi.backend_failure_payload(rec, tmp_path / "f.json")
    assert payload["suggest_shorter_clip"] is True


def test_candi_never_suggests_a_shorter_clip_for_a_plain_error(monkeypatch, tmp_path):
    body = "import sys\nsys.stderr.write('ModuleNotFoundError: No module named librosa\\n')\nsys.exit(1)\n"
    candi = _load_candi(monkeypatch, tmp_path, body)
    with pytest.raises(candi.BackendFailure) as info:
        candi.run_backend(tmp_path / "take.wav", "Aaron G", "take-002")
    rec = info.value.record
    assert rec["kind"] == "error" and "librosa" in rec["stderr_tail"]
    payload = candi.backend_failure_payload(rec, tmp_path / "f.json")
    assert payload["suggest_shorter_clip"] is False
    assert "shorter" in payload["reply_guidance"] and "Do not ask" in payload["reply_guidance"]
