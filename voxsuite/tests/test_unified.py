"""Unified server — all three decks + all three engine APIs on one origin.

The unified app pulls in the real voxanalysis viewer module (loaded by path),
which needs its analysis deps present. Where those are absent (minimal CI), the
whole module is skipped rather than failed.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from test_orchestrator import FakeEngines


def _client(tmp):
    try:
        from voxsuite.server.unified import create_unified_app
        app = create_unified_app(Path(tmp) / "base", engines=FakeEngines())
    except Exception as exc:  # analysis deps (librosa/parselmouth) not importable
        pytest.skip(f"unified app unavailable in this env: {exc}")
    return TestClient(app)


def test_all_three_decks_serve_on_one_origin():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        # / and /fused are the same home deck; /analyze and /polish are the others.
        for path, mode in (("/", "fused"), ("/fused", "fused"), ("/analyze", "analyze"), ("/polish", "polish")):
            r = c.get(path)
            assert r.status_code == 200, path
            assert r.headers.get("cache-control") == "no-cache", path
            assert "__ASSET_VERSION__" not in r.text, path  # version injected
            assert f'VOX_MODE="{mode}"' in r.text, path


def test_mode_tabs_are_same_origin_no_ports():
    """The reported bug: tabs hardcoded to :8765/:8766 break over Tailscale.
    Every served deck must be free of port-based navigation."""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        for path in ("/", "/analyze", "/polish"):
            body = c.get(path).text
            for port in (":8765", ":8766", ":8767"):
                assert port not in body, f"{path} still navigates to {port}"


def test_shared_static_serves_the_kit():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        for asset in ("vox-telemetry.js", "vox-kit.css", "vox-record.js", "vox-report.js", "vox-about.js"):
            assert c.get(f"/static/{asset}").status_code == 200, asset
        assert c.get("/static/../app.py").status_code == 404  # traversal guarded


def test_light_dark_theme_toggle_is_wired():
    """Every deck ships the theme module + no-flash init, and the kit defines a
    light palette the toggle flips to."""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        assert c.get("/static/vox-theme.js").status_code == 200
        theme_js = c.get("/static/vox-theme.js").text
        assert "data-theme" in theme_js and "vox-theme" in theme_js  # persists + sets attr
        # the light palette exists in the shared tokens
        assert ':root[data-theme="light"]' in c.get("/static/vox-tokens.css").text
        for path in ("/", "/analyze", "/polish"):
            body = c.get(path).text
            assert "/static/vox-theme.js?v=" in body, path        # module loaded
            assert "prefers-color-scheme" in body, path           # no-flash head init


def test_phone_layer_and_pwa_are_wired():
    """Phone declutter + install-to-home-screen: console rail tagged for the
    drawer, manifest + icons served, decks link them."""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        for path in ("/", "/analyze", "/polish"):
            body = c.get(path).text
            assert "vox-rail--console" in body, path
            assert "site.webmanifest" in body, path
        assert c.get("/static/site.webmanifest").status_code == 200
        icon = c.get("/static/vox-icon-192.png")
        assert icon.status_code == 200 and icon.content[:4] == b"\x89PNG"
        kit = c.get("/static/vox-kit.css").text
        assert ".vox-console-btn" in kit and "vox-console-open" in kit


def test_report_ships_copy_full_results():
    """Every rendered report must carry the one-tap full-results copy — the
    complete analysis, not a curated summary, is what gets pasted around."""
    with tempfile.TemporaryDirectory() as tmp:
        js = _client(tmp).get("/static/vox-report.js").text
        assert "buildDigest" in js and "Copy full results" in js
        assert "Capture-fair" in js  # digest always carries the capture-fair line


def test_wrap_is_border_box():
    """.vox-wrap must be border-box: content-box made it viewport+padding wide,
    phones expanded their layout viewport past the breakpoints, and the whole
    mobile layer switched off (right-edge clipping on real devices)."""
    with tempfile.TemporaryDirectory() as tmp:
        kit = _client(tmp).get("/static/vox-kit.css").text.replace(" ", "")
        assert "box-sizing:border-box" in kit.split(".vox-wrap{",1)[1].split("}")[0]


def test_stage_canvas_rule_is_child_scoped():
    """The full-height stage-canvas rule must target the scope canvas as a DIRECT
    child, or it also stretches the recorder's nested waveform and pushes the
    Stop button off-screen."""
    with tempfile.TemporaryDirectory() as tmp:
        css = _client(tmp).get("/static/vox-kit.css").text.replace(" ", "")
        assert ".vox-stage>canvas{" in css
        # the un-scoped descendant form must not survive (would re-match .vrec-wave)
        assert ".vox-stagecanvas{" not in css


def test_analyze_deck_ships_the_analyzer_lane_stack():
    """The Analyze deck is a stacked, time-aligned analyzer (VoceVista-style): a
    vibrato strip on top, a dominant pitch-over-spectrogram main lane with an
    on-axis harmonics panel, and a full-take waveform navigator at the bottom —
    all sharing one playhead + zoom window. The old view-switcher chips
    (PITCH/WAVEFORM/SPECTRUM) are retired. Guards the redesign against regressing
    to the single toggled canvas."""
    with tempfile.TemporaryDirectory() as tmp:
        body = _client(tmp).get("/analyze").text
        for marker in ('id="lanes"', 'id="laneVib"', 'id="laneMain"', 'id="laneNav"',
                       'id="vibCanvas"', 'id="navCanvas"', 'id="harmSide"', 'id="harmTable"'):
            assert marker in body, marker
        # the renderers that drive the three lanes must all be present
        for fn in ("drawVib(", "drawNav(", "drawHarmPanel(", "buildNavPeaks("):
            assert fn in body, fn
        # the stage gets a firm floor once seekable so lanes never collapse (the
        # bug where the open export tray starved the main lane to zero on phones)
        assert ".vox-stage.seekable{min-height" in body.replace(" ", "")
        # the retired view-switcher chips must not come back
        assert "vox-scope__chips" not in body
        for chip in (">PITCH<", ">WAVEFORM<", ">SPECTRUM<"):
            assert chip not in body, chip


def test_all_three_engine_apis_are_reachable():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        # Polish namespace (empty workspace answers, doesn't 404 the route)
        assert c.get("/api/workspace").status_code == 200
        # Analyze namespace
        assert c.get("/api/health").status_code == 200
        # Fused namespace
        assert c.get("/api/fused-jobs/nope").status_code == 404  # route exists, job doesn't


def test_fused_lifecycle_runs_through_the_unified_app():
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        r = c.post("/api/fused-jobs", data={"name": "Ada", "tune": "true"},
                   files={"file": ("take.wav", b"RIFF-bytes", "audio/wav")})
        assert r.status_code == 202
        jid = r.json()["id"]
        status = None
        for _ in range(200):
            status = c.get(f"/api/fused-jobs/{jid}").json()
            if status["status"] in ("complete", "failed"):
                break
            time.sleep(0.02)
        assert status["status"] == "complete"
        assert c.get(f"/api/fused-jobs/{jid}/report").status_code == 200
        assert c.get(f"/api/fused-jobs/{jid}/download").status_code == 200
