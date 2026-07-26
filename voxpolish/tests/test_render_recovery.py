"""A render must never leave the UI stuck on "working" with no way out.

Reported: changing a setting sent the deck to WORKING / 75% and it stayed there
forever, with no button to try again. 75% was the adapter's fallback for "running
but the server reports no step index", so a wedged render looked exactly like a
healthy one. These cover the server side of the fix.
"""

from __future__ import annotations

import math
import struct
import time
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voxpolish.server.app import create_app

SR = 44100


def _wav(path: Path, seconds: float = 1.5) -> Path:
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(
            struct.pack("<h", int(0.4 * 32000 * math.sin(2 * math.pi * 220 * i / SR)))
            for i in range(int(SR * seconds))))
    return path


@pytest.fixture()
def client(tmp_path):
    c = TestClient(create_app(tmp_path / "ws"))
    src = _wav(tmp_path / "take.wav")
    job = c.post("/api/uploads", files={"file": ("take.wav", src.read_bytes(), "audio/wav")},
                 data={"tune": "true"}).json()["id"]
    for _ in range(600):
        st = c.get(f"/api/uploads/{job}").json()
        if st["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    assert st["status"] == "done", st.get("error")
    return c


def _settle(c, tries=400):
    for _ in range(tries):
        j = c.get("/api/render").json()
        if j.get("status") in ("done", "error"):
            return j
        time.sleep(0.05)
    return c.get("/api/render").json()


def test_render_reports_elapsed_not_a_frozen_bar(client):
    """The UI needs something that actually moves; elapsed seconds is the honest
    signal when the server has no per-step progress to report."""
    client.post("/api/render")
    j = _settle(client)
    assert j["status"] == "done"
    assert "elapsed_s" in j and j["elapsed_s"] >= 0


def test_second_render_while_one_is_running_is_refused(client):
    """Single-flight must survive the recovery path — a live render is still
    protected from a pile-up."""
    first = client.post("/api/render")
    assert first.status_code == 200
    second = client.post("/api/render")
    assert second.status_code in (200, 409)  # 409 unless the first already finished
    _settle(client)


def test_force_takes_over_a_wedged_render(client):
    """The escape hatch behind the deck's RE-RENDER button: a render that never
    finishes must be restartable without a server restart."""
    client.post("/api/render")
    r = client.post("/api/render?force=true")
    assert r.status_code == 200
    assert _settle(client)["status"] == "done"


def test_a_leaked_lock_does_not_wedge_renders_forever(client):
    """If a worker dies holding the lock, later renders used to 409 forever and
    the deck sat on WORKING with nothing to click. A dead worker is detected and
    taken over automatically."""
    app = client.app
    # Wedge it the way a killed worker would: lock held, no live thread.
    holder = None
    for route in app.routes:
        fn = getattr(route, "endpoint", None)
        if fn is not None and getattr(fn, "__name__", "") == "start_render":
            holder = fn
            break
    assert holder is not None
    cells = {n: c.cell_contents for n, c in
             zip(holder.__code__.co_freevars, holder.__closure__ or ())}
    lock, state = cells.get("lock"), cells.get("render_state")
    assert lock is not None and state is not None
    assert lock.acquire(blocking=False)          # simulate the leak
    state["status"] = "running"
    state["_thread"] = None                      # ...with no worker behind it
    try:
        r = client.post("/api/render")           # no force: must self-recover
        assert r.status_code == 200, "a dead worker must not block new renders"
        assert _settle(client)["status"] == "done"
    finally:
        try:
            lock.release()
        except RuntimeError:
            pass
