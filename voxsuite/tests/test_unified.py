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


def test_single_light_theme_no_toggle():
    """v2 kit is light-only: the theme toggle is gone everywhere, the tokens
    define exactly one (light) palette, and no page ships dark-mode plumbing."""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        assert c.get("/static/vox-theme.js").status_code == 404   # module deleted
        tokens = c.get("/static/vox-tokens.css").text
        assert "data-theme" not in tokens                          # one palette
        assert "--vox-page:#f6f7f9" in tokens                      # and it is light
        for path in ("/", "/analyze", "/polish"):
            body = c.get(path).text
            assert "vox-theme" not in body, path                   # no module, no init
            assert "prefers-color-scheme" not in body, path
            assert "data-theme" not in body, path


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


def test_pitch_monitor_serves_standalone():
    """The real-time Pitch Monitor rides the suite's HTTPS origin at /monitor so
    the mic (getUserMedia) gets a secure context on phones. It's self-contained
    (no /static deps) and served no-cache so redeploys are never stale."""
    with tempfile.TemporaryDirectory() as tmp:
        r = _client(tmp).get("/monitor")
        assert r.status_code == 200
        assert "PITCH//MONITOR" in r.text          # the page's own marker
        assert "getFloatTimeDomainData" in r.text  # the live-detection path is present
        assert r.headers.get("cache-control") == "no-cache"


def test_timbertones_serves_standalone_with_samples():
    """TimberTones (piano + pitch-match trainer) rides the suite origin at
    /timbertones for the same secure-context reason as the monitor, and its
    samples/ tree is served under the trailing-slash path so the page's relative
    fetches resolve. The manifest and a sample must come back with the right
    media types; a traversal attempt must 404."""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        r = c.get("/timbertones")                      # bare path redirects to trailing slash
        assert r.status_code == 200                    # (test client follows the 307)
        assert "TimberTones" in r.text
        assert "getFloatTimeDomainData" in r.text      # the shared YIN detection path is present
        assert r.headers.get("cache-control") == "no-cache"
        man = c.get("/timbertones/samples/manifest.json")
        assert man.status_code == 200 and man.headers["content-type"].startswith("application/json")
        assert isinstance(man.json(), list) and 60 in man.json()   # middle C shipped as a centre
        mp3 = c.get("/timbertones/samples/60.mp3")
        assert mp3.status_code == 200 and mp3.headers["content-type"] == "audio/mpeg"
        assert c.get("/timbertones/../../etc/passwd").status_code == 404   # traversal guard
        assert c.get("/timbertones/index.py").status_code == 404          # suffix whitelist


def test_hub_lists_every_system_with_relative_links():
    """The systems directory at /hub renders every registry entry as a card with
    same-origin (relative) links, so it follows the suite to any address without
    going stale, and polls /api/systems to keep status live."""
    from voxsuite.server.systems import SYSTEMS
    with tempfile.TemporaryDirectory() as tmp:
        r = _client(tmp).get("/hub")
        assert r.status_code == 200
        assert r.headers.get("cache-control") == "no-cache"
        for s in SYSTEMS:
            assert s["name"] in r.text, s["name"]
            assert f'href="{s["path"]}"' in r.text, s["path"]      # relative, not absolute
        assert 'href="https://' not in r.text and 'href="http://' not in r.text  # nothing hard-coded
        assert "/api/systems" in r.text                             # the live-refresh source


def test_api_systems_is_absolute_and_route_checked():
    """The JSON registry stamps absolute URLs from the request origin (for a page
    hosted elsewhere) and marks each system live against the app's real routes."""
    from voxsuite.server.systems import SYSTEMS
    with tempfile.TemporaryDirectory() as tmp:
        j = _client(tmp).get("/api/systems").json()
        assert j["count"] == len(SYSTEMS)
        by_id = {s["id"]: s for s in j["systems"]}
        for sid in ("fused", "analyze", "polish", "monitor", "timbertones", "build"):
            assert by_id[sid]["live"] is True, sid                  # its route is really registered
            assert by_id[sid]["url"].startswith(j["origin"]), sid   # absolute under the origin


def test_api_systems_flags_a_removed_route_as_down():
    """A registry entry whose path is no longer served must report live=False —
    the hub can't quietly claim a dead system is up."""
    from voxsuite.server import systems as S
    from voxsuite.server.unified import create_unified_app
    with tempfile.TemporaryDirectory() as tmp:
        try:
            app = create_unified_app(Path(tmp) / "base", engines=FakeEngines())
        except Exception as exc:
            pytest.skip(f"unified app unavailable: {exc}")
        resolved = S.resolve(app, base_url="https://x")
        ghost = S.is_live({"path": "/does-not-exist"}, S.registered_paths(app))
        assert ghost is False
        assert all(s["url"].startswith("https://x") for s in resolved)


def test_standalone_hub_is_self_contained():
    """tools/build_hub.py emits one file with only the given base's links — no
    /static deps, no CDN — and wires its refresh at <base>/api/systems."""
    import importlib.util
    from voxsuite.server.systems import SYSTEMS
    path = Path(__file__).resolve().parents[2] / "tools" / "build_hub.py"
    spec = importlib.util.spec_from_file_location("build_hub", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    base = "https://vox.example.ts.net"
    html = mod.build(base)
    for s in SYSTEMS:
        assert base + s["path"] in html, s["path"]                 # absolute links baked in
    assert "/static/" not in html                                  # self-contained
    assert "cdn" not in html.lower() and "googleapis" not in html.lower()
    assert base + "/api/systems" in html                           # self-refresh target
    # the only external origin referenced is the base we asked for
    import re
    hosts = {m for m in re.findall(r'https?://[^"\')\s]+', html)}
    assert all(h.startswith(base) for h in hosts), hosts


def test_every_page_carries_the_nav_bar():
    """A visible top nav bar is injected into every served page (decks, monitor,
    TimberTones) from the registry, so navigation is one tap anywhere — and it
    marks the current page active."""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        pages = {"/": "/", "/analyze": "/analyze", "/polish": "/polish",
                 "/monitor/": "/monitor", "/timbertones/": "/timbertones"}
        for url, active in pages.items():
            body = c.get(url).text
            assert 'id="vox-nav-tpl"' in body, f"nav bar missing on {url}"
            # links to the hub and the other apps are present
            for href in ('href="/hub"', 'href="/analyze"', 'href="/timbertones"', 'href="/monitor"'):
                assert href in body, f"{href} missing on {url}"
            # the current page is marked active
            assert f'class="link active" href="{active}"' in body, f"{url} not marked active"
        # the hub carries the bar too (consistent navigation, never a dead-end)
        hub = c.get("/hub").text
        assert 'id="vox-nav-tpl"' in hub and 'class="link active" href="/hub"' in hub


def test_served_page_scripts_parse():
    """Every inline <script> in a SERVED page (deck shells + the injected nav bar
    + the generated hub) must parse under `node --check`. A syntax error silently
    kills a whole page's JS while its static shell still renders — the exact bug
    that shipped once. Skips where node isn't installed."""
    import os
    import re
    import shutil
    import subprocess
    import tempfile as _tf
    if not shutil.which("node"):
        pytest.skip("node not available")
    inline = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S)
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        for url in ("/", "/analyze", "/polish", "/monitor/", "/timbertones/", "/hub"):
            html = c.get(url).text
            for i, block in enumerate(inline.findall(html)):
                with _tf.NamedTemporaryFile("w", suffix=".js", delete=False) as t:
                    t.write(block)
                    path = t.name
                try:
                    r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
                finally:
                    os.unlink(path)
                assert r.returncode == 0, f"{url} inline script #{i} has a JS syntax error:\n{r.stderr}"


def test_hub_links_stay_relative_behind_a_proxy():
    """The live hub's cards AND its refresh script use same-origin relative paths,
    so links keep working behind a reverse proxy (Tailscale) where the server's own
    base_url is an unreachable internal address — the bug that made them dead."""
    with tempfile.TemporaryDirectory() as tmp:
        hub = _client(tmp).get("/hub").text
        assert 'href="/analyze"' in hub and 'href="/timbertones"' in hub  # relative cards
        assert 'href="http' not in hub                                    # nothing absolute baked in
        assert "REL=true" in hub                                          # refresh is in relative mode
        assert "(REL&&s.path)?s.path:s.url" in hub                        # and uses the relative path


def test_analyze_deck_ships_the_score_badge():
    """The score badge surfaces overall + capture-fair + confidence + the
    calibration provenance line, so a user can see whether the number is
    pro-anchored (the "is this calibrated or mine?" question) without opening the
    full report."""
    with tempfile.TemporaryDirectory() as tmp:
        body = _client(tmp).get("/analyze").text
        for marker in ('id="scoreBadge"', 'id="scoreOverall"', 'id="scoreCF"',
                       'id="scoreConf"', 'id="scoreCal"', "renderScoreBadge("):
            assert marker in body, marker
        assert "capture-fair" in body
        assert "10 = a typical pro" in body  # the calibration provenance line


def test_recorder_ships_trim_for_recorded_and_imported_takes():
    """Trimming dead air/chatter off the ends is part of intake, not a manual
    step in another app. It must work for a take recorded here AND for one
    imported (a live gig captured on a phone app, which the browser can't record
    itself because iOS suspends recording on screen lock) — hence loadFile()."""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        js = c.get("/static/vox-record.js").text
        for marker in ("vrec-trim", "loadFile", "sliceToWav", "showTrim", "suggestStart"):
            assert marker in js, marker
        # the trimmed take is submitted as WAV — re-encoding lossily here would
        # discard the detail the voice-quality metrics measure
        assert 'type: "audio/wav"' in js
        css = c.get("/static/vox-record.css").text.replace(" ", "")
        # the trim row must claim full width: .vrec-stage is justify-items:center,
        # which otherwise shrink-wraps it to ~0 and breaks the handles
        assert ".vrec-trim,.vrec-trimbar,.vrec-trimnote{width:100%" in css
        # a chosen file routes through trim rather than straight to analysis
        assert "intake_file(" in c.get("/analyze").text


def test_polish_deck_can_ab_and_never_fails_a_module_silently():
    """Two reported bugs. (1) The CLEANED/ORIGINAL chips were inert labels, so
    there was no way to hear the render against the raw take — which is how you
    notice a module doing nothing. (2) The server reported "Auto Tune was ON but
    could not be applied" and the deck threw it away, making a broken vocoder
    indistinguishable from a working one with little to correct."""
    with tempfile.TemporaryDirectory() as tmp:
        c = _client(tmp)
        body = c.get("/polish").text
        # A/B: both chips must be real buttons wired to a source switch
        assert '<button type="button" class="vox-chip is-hot" id="scopeSource"' in body
        assert 'id="scopeOriginal"' in body and "setSource(" in body
        assert '/api/audio/"+name' in body  # switches the audio element's source
        # failures must surface: notes panel + the up-front capability warning
        assert 'id="renderNotes"' in body and "showRenderNotes(" in body
        assert "refreshRenderNotes(" in body
        assert "capabilities" in body and "Auto Tune cannot run on this server" in body
        assert ".vox-rnotes{" in c.get("/static/vox-kit.css").text.replace(" ", "")


def test_build_endpoint_identifies_the_live_build():
    """A deployed fix looked absent because nothing on the page said which build
    was live — "did the pull reach the running service?" could only be answered by
    reading source on the box. /api/build hashes the deck files this process
    actually reads and reports the checkout's commit."""
    with tempfile.TemporaryDirectory() as tmp:
        j = _client(tmp).get("/api/build").json()
        assert set(j["decks"]) == {"fused", "analyze", "polish"}
        for name, info in j["decks"].items():
            assert info["exists"], name
            assert info["sha1_12"] and len(info["sha1_12"]) == 12, name
            assert info["path"].endswith("deck.html"), name
        assert "git" in j and "commit" in j["git"]
        assert "vox-kit.css" in j["assets"]


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
        r = c.post("/api/fused-jobs", data={"name": "Ada", "tune": "true", "take_capture": "home"},
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
