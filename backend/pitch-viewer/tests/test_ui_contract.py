from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
FIXTURES = json.loads((Path(__file__).with_name("ui_fixtures.json")).read_text(encoding="utf-8"))
BROWSER_HARNESS = (
    Path(__file__).with_name("browser") / "stop_ship_browser_check.mjs"
).read_text(encoding="utf-8")
PERFORMANCE_HARNESS = (
    Path(__file__).with_name("browser")
    / "phase-gates"
    / "phase3_performance_check.mjs"
).read_text(encoding="utf-8")


class UiContractTests(unittest.TestCase):
    def test_preserves_functional_control_ids(self):
        required = {
            "analysis", "artistName", "audio", "background", "cents", "chart", "comparisonMode",
            "chartWrap", "conditions", "drop", "empty", "error", "file", "follow",
            "instrumental", "minus", "new", "note", "originalAudio",
            "originalIdentity", "originalListen", "originalOverlay", "originalPlayer",
            "pitchColour", "plus", "reset", "singerName", "songName", "status",
            "statusText", "technicalReport", "uploadCard", "viewer", "warning",
            "spectralLayer", "harmonicGuides", "spectralStatus", "harmonicReadout",
            "harmonicMeters", "mobileOriginalListen"
        }
        ids = set(re.findall(r'id="([^"]+)"', HTML))
        self.assertTrue(required.issubset(ids), required - ids)

    def test_signal_chain_matches_backend_stages(self):
        stages = re.findall(r'data-stage="([^"]+)"', HTML)
        self.assertEqual(stages, FIXTURES["processing_stages"])

    def test_flagship_copy_and_accessibility_contract(self):
        self.assertIn("Your voice.<br>In full resolution.", HTML)
        self.assertIn("VOXAI // Performance Intelligence", HTML)
        self.assertIn('role="alert"', HTML)
        self.assertIn('aria-live="polite"', HTML)
        self.assertIn("prefers-reduced-motion", HTML)

    def test_mobile_transport_and_scope_controls_keep_safe_touch_targets(self):
        compact_query = (
            "@media(max-width:900px),(orientation:landscape) "
            "and (hover:none) and (pointer:coarse)"
        )
        self.assertGreaterEqual(HTML.count(compact_query), 2)
        self.assertIn(".seek{height:44px}", HTML)
        self.assertIn(
            ".scope-controls #minus,.scope-controls #plus{min-width:44px}", HTML
        )
        self.assertIn(
            ".transport .timecode span,.transport #durationTime,.transport #originalListen{display:none}",
            HTML,
        )
        self.assertIn(".native-fallback summary{min-height:44px", HTML)
        self.assertIn(".spot{width:44px;height:44px;min-height:44px", HTML)
        self.assertIn(".mobile-reference-listen{display:none}", HTML)
        self.assertIn(
            '<button class="mobile-reference-listen" id="mobileOriginalListen"',
            HTML,
        )
        self.assertIn("$('#mobileOriginalListen').onclick=toggleOriginalMode", HTML)

    def test_large_touch_landscape_has_durable_browser_coverage(self):
        self.assertIn("width: 1024, height: 600, touch: true, compact: true", BROWSER_HARNESS)
        self.assertIn("width: 1280, height: 720, touch: true, compact: true", BROWSER_HARNESS)
        self.assertIn("width: 1024, height: 600, touch: false, compact: false", BROWSER_HARNESS)
        self.assertIn("Emulation.setTouchEmulationEnabled", BROWSER_HARNESS)
        self.assertIn("matchMedia('(pointer:coarse)')", BROWSER_HARNESS)
        self.assertIn("mobileAbRect.width >= 44", BROWSER_HARNESS)
        self.assertIn("state.overflow <= 1", BROWSER_HARNESS)

    def test_mobile_lifecycle_recovery_is_stateful_and_debounced(self):
        self.assertIn("function rememberLifecycleState()", HTML)
        self.assertIn("function restoreLifecycleState()", HTML)
        self.assertIn("async function playWithStartupTimeout(media)", HTML)
        self.assertIn("media.pause();reject(new Error('Playback did not start'))", HTML)
        self.assertIn("clearTimeout(timer)", HTML)
        self.assertIn("if(clock.paused)playbackIntent=false", HTML)
        self.assertIn("Tap play to resume after returning to VOXAI.", HTML)
        self.assertIn("function pauseFromExternalControl()", HTML)
        self.assertIn("if(lifecycleSnapshot)lifecycleSnapshot.resume=false", HTML)
        self.assertIn("setActionHandler('pause',pauseFromExternalControl)", HTML)
        self.assertIn("addEventListener('pagehide'", HTML)
        self.assertIn("addEventListener('pageshow'", HTML)
        self.assertIn("addEventListener('orientationchange'", HTML)
        self.assertIn("function scheduleViewportSettle(delay=100)", HTML)
        resize = re.search(r"^function resize\(\).*", HTML, re.MULTILINE).group(0)
        self.assertIn("canvas.width===width&&canvas.height===height", resize)
        self.assertIn("return false", resize)

    def test_heavy_report_is_deferred(self):
        self.assertIn("Open this rack to load the full report.", HTML)
        self.assertIn("if(technicalLoaded)return", HTML)
        names = {fixture["name"] for fixture in FIXTURES["result_states"]}
        self.assertIn("long_technical_report", names)

    def test_calibrated_analysis_wording_is_version_neutral(self):
        self.assertIn(">Calibrated analysis</div>", HTML)
        self.assertIn("Running the calibrated VOXAI analysis…", HTML)
        self.assertIn("Calibrated VOXAI analysis", HTML)
        self.assertIn("Calibrated component profile", HTML)
        self.assertNotIn("V3 diagnostics", HTML)
        self.assertNotIn("V2 calibrated score", HTML)
        self.assertNotIn("V2 component profile", HTML)
        self.assertIn('data-stage="running_v2_analysis"', HTML)
        self.assertIn("Clean onsets", HTML)
        self.assertIn("Singer’s-formant ratio", HTML)
        self.assertIn("H1−H2", HTML)

    def test_single_track_mode_is_explicit_and_suppresses_comparison(self):
        self.assertIn("comparisonEnabled", HTML)
        self.assertIn("body.append('comparison',comparisonEnabled?'true':'false')", HTML)
        self.assertIn("body.append('song',song)", HTML)
        self.assertIn("body.append('artist',artist)", HTML)
        self.assertNotIn("song.disabled=!enabled", HTML)
        self.assertIn("Original artist or composer (optional)", HTML)
        self.assertIn("if(reference?.status==='skipped')return''", HTML)
        names = {fixture["name"] for fixture in FIXTURES["result_states"]}
        self.assertIn("single_track", names)

    def test_pitch_variance_colour_reserves_red_for_large_errors(self):
        self.assertIn("error<=15?0", HTML)
        self.assertIn("error<=30?(error-15)/15*.22", HTML)
        self.assertIn("error<=40?.22+(error-30)/10*.38", HTML)
        self.assertIn(".6+(error-40)/10*.4", HTML)

    def test_spectral_controls_are_accessible_default_off_and_lazy(self):
        self.assertRegex(
            HTML,
            r'<button id="spectralLayer"[^>]*aria-pressed="false"[^>]*disabled',
        )
        self.assertRegex(
            HTML,
            r'<button id="harmonicGuides"[^>]*aria-pressed="false"[^>]*disabled',
        )
        self.assertIn("spectralOn=false", HTML)
        self.assertIn("harmonicGuidesOn=false", HTML)
        self.assertIn('id="spectralStatus" role="status" aria-live="polite"', HTML)
        self.assertIn("Spectral energy — display only", HTML)
        show = re.search(r"^function show\(data\).*", HTML, re.MULTILINE).group(0)
        configure = re.search(
            r"^function configureSpectral\(spectral\).*", HTML, re.MULTILINE
        ).group(0)
        for body in (show, configure):
            self.assertNotIn("fetch(", body)
            self.assertNotIn("ensureSpectralDescriptor(", body)
            self.assertNotIn("ensureHarmonicTracks(", body)

    def test_scope_draw_order_preserves_pitch_dominance(self):
        draw = re.search(r"^function draw\(geometry=null\).*", HTML, re.MULTILINE).group(0)
        static = re.search(
            r"^function renderStaticScope\(g,key\).*", HTML, re.MULTILINE
        ).group(0)
        static_calls = [
            "blitSpectrogram(g)",
            "drawNoteLanes(g)",
            "drawHarmonicGuides(g)",
            "drawSingerContour(g)",
            "drawAccuracyOverlay(g)",
            "drawReferenceContour(g)",
        ]
        positions = [static.index(call) for call in static_calls]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(draw.index("renderStaticScope(g,key)"), draw.index("drawPlayhead(g)"))
        self.assertLess(draw.index("blitStaticScope()"), draw.index("drawPlayhead(g)"))
        self.assertIn("scopeStaticCanvas=document.createElement('canvas')", HTML)
        singer = re.search(
            r"^function drawSingerContour\(g\).*", HTML, re.MULTILINE
        ).group(0)
        accuracy = re.search(
            r"^function drawAccuracyOverlay\(g\).*", HTML, re.MULTILINE
        ).group(0)
        self.assertIn("'#3b82f6',2,false", singer)
        self.assertIn("if(!pitchColourOn)return", accuracy)
        self.assertIn("1.15,true", accuracy)

    def test_low_confidence_pitch_is_dotted_without_bridging_unvoiced_gaps(self):
        contour = HTML.split("function drawContour", 1)[1].split(
            "function pitchErrorColour", 1
        )[0]
        singer = re.search(
            r"^function drawSingerContour\(g\).*", HTML, re.MULTILINE
        ).group(0)
        accuracy = re.search(
            r"^function drawAccuracyOverlay\(g\).*", HTML, re.MULTILINE
        ).group(0)
        readout = re.search(
            r"^function updateReadout\(\).*", HTML, re.MULTILINE
        ).group(0)
        self.assertIn("lowConfidence=null", contour)
        self.assertIn("if(lowConfidence?.[j])uncertain=true", contour)
        self.assertIn(
            "if(gap||value===null||value===undefined){previous=null;continue}",
            contour,
        )
        self.assertIn("ctx.setLineDash(LOW_CONFIDENCE_DASH)", contour)
        self.assertIn("ctx.globalAlpha=LOW_CONFIDENCE_ALPHA", contour)
        self.assertIn("if(styled&&uncertain&&!colourByPitch&&!previous)", contour)
        self.assertIn("nextIndex<end?values[nextIndex]:null", contour)
        self.assertIn("if(!nextVisible)", contour)
        self.assertIn("LOW_CONFIDENCE_DASH=[3,4]", HTML)
        self.assertIn("LOW_CONFIDENCE_ALPHA=.48", HTML)
        self.assertIn("contourLowConfidence(contour)", singer)
        self.assertIn("contourLowConfidence(contour)", accuracy)
        self.assertIn("Low-confidence pitch", HTML)
        self.assertIn("Low-confidence detection", readout)
        self.assertNotIn("q<.05", readout)
        self.assertIn("refinements.contract.breathNull", BROWSER_HARNESS)
        self.assertIn("refinements.contour.breathRegion.changed === 0", BROWSER_HARNESS)
        self.assertIn("refinements.contour.dashedOff > 0", BROWSER_HARNESS)
        self.assertIn("refinements.contour.isolatedEndpoint.changed > 0", BROWSER_HARNESS)
        self.assertIn(
            "refinements.contour.uncertainRegion.changed < "
            "refinements.contour.reliableRegion.changed",
            BROWSER_HARNESS,
        )
        self.assertIn(
            "refinements.contour.dashedOn > refinements.contour.dashedOff",
            BROWSER_HARNESS,
        )

    def test_energy_and_harmonics_are_readable_but_behind_singer(self):
        self.assertIn("SPECTRAL_DISPLAY_ALPHA=.38", HTML)
        self.assertIn(
            "sepia(.18) saturate(1.65) contrast(1.28) brightness(1.18) hue-rotate(145deg)",
            HTML,
        )
        self.assertIn("HARMONIC_GUIDE_NEAR_ALPHA=.5", HTML)
        self.assertIn("HARMONIC_GUIDE_FAR_ALPHA=.36", HTML)
        self.assertIn("HARMONIC_GUIDE_WIDTH=1.05", HTML)
        self.assertIn("ctx.globalAlpha=SPECTRAL_DISPLAY_ALPHA", HTML)
        self.assertIn("k<5?HARMONIC_GUIDE_NEAR_ALPHA", HTML)
        self.assertIn("'#3b82f6',2,false", HTML)
        guide_width = float(
            re.search(r"HARMONIC_GUIDE_WIDTH=([0-9.]+)", HTML).group(1)
        )
        singer_width = float(
            re.search(r"'#3b82f6',([0-9.]+),false", HTML).group(1)
        )
        self.assertLess(guide_width, singer_width)
        self.assertIn("refinements.layers.energyDelta.changed > 1000", BROWSER_HARNESS)
        self.assertIn("refinements.layers.harmonicsDelta.changed > 100", BROWSER_HARNESS)
        self.assertIn(
            "refinements.layers.bluePixels >= "
            "refinements.layers.singerBluePixels * .9",
            BROWSER_HARNESS,
        )

    def test_harmonic_geometry_uses_unrounded_physical_offsets(self):
        self.assertIn("function harmonicOffset(k){return 12*Math.log2(k)}", HTML)
        guides = re.search(
            r"^function drawHarmonicGuides\(g\).*", HTML, re.MULTILINE
        ).group(0)
        self.assertIn("for(let k=2;k<=8;k++)", guides)
        self.assertIn("harmonicOffset(k)", guides)
        self.assertIn("originalMode?(result?.reference?.native_contour||null)", HTML)
        self.assertIn("for(let k=1;k<=8;k++)", HTML)

    def test_long_contours_are_pixel_bounded_without_changing_zoomed_detail(self):
        self.assertIn(
            "function contourStride(rate,v,w,pad){return Math.max(1,Math.floor(v.window*rate/Math.max(1,w-pad)))}",
            HTML,
        )
        contour = HTML.split("function drawContour", 1)[1].split(
            "function pitchErrorColour", 1
        )[0]
        self.assertIn("stride=contourStride(rate,v,w,pad)", contour)
        self.assertIn("if(stride>1)", contour)
        self.assertIn("gap=true", contour)

    def test_ab_source_switch_never_falls_back_between_artifacts(self):
        self.assertIn(
            "function activeSpectralSource(){return originalMode?'original':'vocals'}",
            HTML,
        )
        source_change = re.search(
            r"^function handleSpectralSourceChange\(\).*", HTML, re.MULTILINE
        ).group(0)
        self.assertIn("invalidateSpectralWindow()", source_change)
        self.assertIn("refreshSpectralControls(true)", source_change)
        state_change = re.search(
            r"^function setOriginalModeState\(enabled\).*", HTML, re.MULTILINE
        ).group(0)
        self.assertIn("handleSpectralSourceChange()", state_change)
        self.assertNotIn("||'vocals'", source_change)

    def test_original_ab_timeline_and_contour_do_not_depend_on_visual_layers(self):
        duration = re.search(
            r"^function scopeDuration\(\).*", HTML, re.MULTILINE
        ).group(0)
        reference = re.search(
            r"^function activeReferenceContour\(\).*", HTML, re.MULTILINE
        ).group(0)
        for body in (duration, reference):
            self.assertNotIn("spectralOn", body)
            self.assertNotIn("harmonicGuidesOn", body)
        self.assertIn("if(originalMode)return result.reference.native_contour", reference)
        self.assertIn("mediaDuration=Number(originalAudio.duration)", duration)
        self.assertLess(
            duration.index("originalAudio.duration"), duration.index("native_contour")
        )
        contract = FIXTURES["ab_timeline_contract"]
        self.assertNotEqual(
            contract["singer_duration_seconds"],
            contract["original_audio_duration_seconds"],
        )
        self.assertNotEqual(
            contract["original_native_duration_seconds"],
            contract["original_audio_duration_seconds"],
        )

    def test_missing_component_score_has_unavailable_not_zero_geometry(self):
        states = {item["name"]: item for item in FIXTURES["component_score_states"]}
        self.assertTrue(states["measured_zero"]["available"])
        self.assertEqual(states["measured_zero"]["width_percent"], 0)
        self.assertFalse(states["missing"]["available"])
        self.assertIsNone(states["missing"]["width_percent"])
        score_state = re.search(
            r"^function scoreState\(value\).*", HTML, re.MULTILINE
        ).group(0)
        score_meter = re.search(
            r"^function scoreMeter\(value,title='Measured component',className='',fillClass=''\).*",
            HTML,
            re.MULTILINE,
        ).group(0)
        render = re.search(
            r"^function renderAnalysis\(report,reportUrl\).*", HTML, re.MULTILINE
        ).group(0)
        comparison = re.search(
            r"^function comparisonHtml\(report\).*", HTML, re.MULTILINE
        ).group(0)
        self.assertIn("value!==null", score_state)
        self.assertIn("available:false,value:null,width:null", score_state)
        self.assertIn("aria-valuetext=\"Not available\"", score_meter)
        self.assertIn("state.available?`<i${fillClassAttribute} style=\"width:${state.width}%\"", score_meter)
        self.assertIn("scoreMeter(c.score", render)
        self.assertIn("scoreMeter(item.score", comparison)
        self.assertIn("scoreMeter(original.score", comparison)
        self.assertNotIn("Number(c.score||0)", HTML)

    def test_spectral_renderer_is_bounded_offscreen_and_not_rebuilt_by_draw(self):
        draw = re.search(r"^function draw\(geometry=null\).*", HTML, re.MULTILINE).group(0)
        for forbidden in ("fetch(", "createImageBitmap", "buildSpectralWindow("):
            self.assertNotIn(forbidden, draw)
        self.assertIn("spectralCanvas=document.createElement('canvas')", HTML)
        self.assertIn("SPECTRAL_OVERSCAN=3", HTML)
        self.assertIn("SPECTRAL_CACHE_LIMIT=8", HTML)
        self.assertIn("SPECTRAL_CACHE_BYTES=32*1024*1024", HTML)
        self.assertIn("SPECTRAL_CANVAS_MAX_WIDTH=8192", HTML)
        self.assertIn("entry.image.close?.()", HTML)
        self.assertIn("const image=new Image()", HTML)
        build = re.search(
            r"^async function buildSpectralWindow\(g,descriptor,source,token,signal\).*",
            HTML,
            re.MULTILINE,
        ).group(0)
        blit = re.search(
            r"^function blitSpectrogram\(g\).*", HTML, re.MULTILINE
        ).group(0)
        self.assertIn(
            "bufferContext.filter='sepia(.18) saturate(1.65) contrast(1.28) "
            "brightness(1.18) hue-rotate(145deg)'",
            build,
        )
        self.assertNotIn("ctx.filter=", blit)
        self.assertIn("(tile.frame_start-.5)/descriptor.fps", HTML)
        self.assertIn("descriptor.n_bins-.5", HTML)
        self.assertIn("token!==spectralGeneration", HTML)
        self.assertIn("controller=new AbortController()", HTML)
        self.assertIn("spectralBuildAbortController?.abort()", HTML)
        self.assertIn("credentials:'same-origin',signal", HTML)
        self.assertIn("tile.frame_count>2048", HTML)
        self.assertIn("SPECTRAL_REQUEST_TIMEOUT_MS=15000", HTML)
        self.assertIn(
            "pointercancel',()=>{drag=null;settleScopeNavigation()}", HTML
        )
        navigation = re.search(
            r"^function settleScopeNavigation\(\).*", HTML, re.MULTILINE
        ).group(0)
        self.assertIn("invalidateSpectralWindow()", navigation)
        self.assertIn("requestSpectralWindow(geometry)", navigation)

    def test_watchdog_requires_two_sustained_sub_45_fps_windows(self):
        self.assertIn("SPECTRAL_WATCHDOG_FPS=45", HTML)
        self.assertIn("SPECTRAL_WATCHDOG_WINDOW_MS=2000", HTML)
        self.assertIn("SPECTRAL_WATCHDOG_FAILURES=2", HTML)
        self.assertIn("SPECTRAL_WATCHDOG_GRACE_MS=3000", HTML)
        watchdog = re.search(
            r"^function observeSpectralFrame\(now\).*", HTML, re.MULTILINE
        ).group(0)
        for condition in (
            "!spectralOn",
            "!spectralBlitted",
            "clock.paused",
            "document.hidden",
            "!chartVisible",
        ):
            self.assertIn(condition, watchdog)
        self.assertIn("disabled to protect smooth playback", watchdog)
        self.assertIn("watchdogGraceUntil<0", watchdog)
        self.assertIn("now<watchdogGraceUntil", watchdog)
        self.assertIn("profile.fps >= 45", PERFORMANCE_HARNESS)
        self.assertIn("profile.p95FrameMs <= 34", PERFORMANCE_HARNESS)
        self.assertIn("profile.maxFrameMs < 100", PERFORMANCE_HARNESS)
        self.assertIn("profile.longTaskObserverSupported", PERFORMANCE_HARNESS)
        self.assertIn("profile.watchdogMaxLowWindows === 0", PERFORMANCE_HARNESS)
        self.assertIn("results.gate = gateFailures.length ? 'failed' : 'pass'", PERFORMANCE_HARNESS)

    def test_spectral_fixtures_cover_ready_legacy_and_failure_states(self):
        names = {fixture["name"] for fixture in FIXTURES["spectral_states"]}
        self.assertEqual(
            names,
            {
                "ready_both_sources",
                "ready_vocals_only",
                "legacy_absent",
                "export_unavailable",
                "artifact_fetch_failure",
            },
        )

    def test_warning_fixtures_cover_evidence_risks(self):
        flags = {
            flag
            for fixture in FIXTURES["result_states"]
            for flag in fixture.get("quality_flags", [])
        }
        self.assertEqual(
            flags,
            {"low_voiced_coverage", "low_pitch_confidence", "clipping_detected"},
        )


if __name__ == "__main__":
    unittest.main()
