/* ============================================================================
   VOX Suite — "What this does" guide overlay  (shared, vendored by sync.sh)
   Self-injects a Guide trigger into the command bar and opens an accessible
   overlay explaining the suite to a new user: what it is, the three modes, how
   to use each, and what you get. Set window.VOX_MODE ("polish"|"analyze"|
   "fused") before loading to highlight the deck the user is on.
   Styling lives in vox-kit.css (.vox-about*). Global: none.
   ============================================================================ */
(function () {
  "use strict";

  var MODES = [
    {
      key: "polish", tag: "POLISH", accent: "cyan",
      title: "Polish", tagline: "Repair, level & gently tune a take",
      body: "Clean up a recording without losing the performance: reduce noise, close awkward pauses, soften breaths and harsh ‘s’ sounds, and apply gentle pitch correction. Every module is non-destructive — toggle each one on or off and hear the take re-render.",
      how: [
        "Open Polish and drop in a vocal take.",
        "Toggle modules (Clean, Dynamics, Gate, Breath, Sibilance, Tune) to taste — each edit re-renders.",
        "Play it back, then export the polished vocal + an editable edit document."
      ]
    },
    {
      key: "analyze", tag: "ANALYZE", accent: "violet",
      title: "Analyze", tagline: "Measure, score & compare",
      body: "Understand a take objectively. VOX tracks your pitch frame by frame and measures accuracy, range, tone, timing and more, then builds a calibrated scorecard with a clear coaching focus. Add a song and artist and it will compare you against the original.",
      how: [
        "Open Analyze and upload a take (add song + artist to enable comparison).",
        "Watch the pitch scope and stage chain as it measures and scores.",
        "Read the report, seek to flagged moments, and export the scorecard."
      ]
    },
    {
      key: "fused", tag: "FUSED", accent: "cyanviolet",
      title: "Fused", tagline: "Upload once — analyze & polish together",
      body: "The whole suite in one pass. Your take is isolated a single time, then analyzed and polished from that same clean vocal — so you get the measured report and the finished file together, without uploading twice.",
      how: [
        "Open Fused and upload once.",
        "Let the run carry the take through isolate → analyze → polish.",
        "Export both the analysis report and the polished vocal at the end."
      ]
    }
  ];

  var current = (window.VOX_MODE || "").toLowerCase();

  function h(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }

  function modeCard(m) {
    var here = m.key === current;
    return (
      '<article class="vox-about__mode ' + m.accent + (here ? " is-here" : "") + '">' +
        '<div class="vox-about__mtag"><span class="vox-led"></span>' + m.tag + (here ? '<em>you are here</em>' : '') + '</div>' +
        '<h3>' + m.title + ' <span>' + m.tagline + '</span></h3>' +
        '<p>' + m.body + '</p>' +
        '<ol>' + m.how.map(function (s) { return '<li>' + s + '</li>'; }).join('') + '</ol>' +
      '</article>'
    );
  }

  function buildOverlay() {
    var el = h(
      '<div class="vox-about" id="voxAbout" role="dialog" aria-modal="true" aria-labelledby="voxAboutTitle" hidden>' +
        '<div class="vox-about__scrim" data-close></div>' +
        '<div class="vox-about__panel" role="document">' +
          '<button class="vox-about__x" type="button" aria-label="Close guide" data-close>×</button>' +
          '<div class="vox-about__eyebrow"><span class="vox-led"></span>What this does</div>' +
          '<h2 id="voxAboutTitle">One workspace for your voice — from raw take to polished &amp; understood.</h2>' +
          '<p class="vox-about__lede">VOX Suite is a private, on-device studio for a single vocal recording. Pick a mode for what you need right now — the three share one deck, so moving between them feels like flipping a channel, not switching apps.</p>' +
          '<div class="vox-about__modes">' + MODES.map(modeCard).join('') + '</div>' +
          '<div class="vox-about__start">' +
            '<h4>Getting started</h4>' +
            '<ul>' +
              '<li>Choose a mode from the <b>switch at the top-left</b> of the deck.</li>' +
              '<li>Drop in a recording — <b>WAV, MP3, M4A, FLAC, and more</b>. Everything runs locally.</li>' +
              '<li>Every mode ends in an <b>export tray</b>: the polished vocal, the analysis report, or both.</li>' +
              '<li>New here? Add <b><code>?demo=1</code></b> to any deck URL for a guided walkthrough with no upload.</li>' +
            '</ul>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
    el.addEventListener("click", function (e) { if (e.target.hasAttribute("data-close")) close(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !el.hidden) close(); });
    return el;
  }

  var overlay, trigger, lastFocus;
  function open() {
    lastFocus = document.activeElement;
    overlay.hidden = false;
    document.body.style.overflow = "hidden";
    trigger.setAttribute("aria-expanded", "true");
    overlay.querySelector(".vox-about__x").focus();
  }
  function close() {
    overlay.hidden = true;
    document.body.style.overflow = "";
    trigger.setAttribute("aria-expanded", "false");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function mount() {
    var bar = document.querySelector(".vox-command");
    if (!bar) return;
    trigger = h(
      '<button class="vox-about-btn" type="button" aria-haspopup="dialog" aria-expanded="false" aria-controls="voxAbout">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/></svg>' +
        'Guide</button>'
    );
    trigger.addEventListener("click", function () { overlay.hidden ? open() : close(); });
    bar.appendChild(trigger);
    overlay = buildOverlay();
    document.body.appendChild(overlay);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
