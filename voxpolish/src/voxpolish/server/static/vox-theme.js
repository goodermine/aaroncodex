/* ============================================================================
   VOX Suite — light / dark theme toggle  (shared, vendored by sync.sh)
   Self-injects a toggle into the command bar (next to Guide) that flips
   data-theme on <html> and remembers the choice in localStorage. Default
   follows the device's prefers-color-scheme until the user picks explicitly.

   To avoid a flash of the wrong theme, also add this tiny snippet in each
   deck's <head> so the attribute is set before first paint:
     <script>try{var t=localStorage.getItem('vox-theme')||
       (matchMedia('(prefers-color-scheme:light)').matches?'light':'dark');
       document.documentElement.setAttribute('data-theme',t);}catch(e){}</script>
   Styling lives in vox-kit.css (.vox-theme-btn). Global: none.
   ============================================================================ */
(function () {
  "use strict";

  var KEY = "vox-theme";
  var root = document.documentElement;

  function system() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme:light)").matches ? "light" : "dark";
  }
  function saved() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function current() {
    return root.getAttribute("data-theme") || saved() || system();
  }
  function apply(theme) {
    root.setAttribute("data-theme", theme);
    if (btn) {
      btn.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
      btn.title = theme === "light" ? "Switch to dark theme" : "Switch to light theme";
      btn.setAttribute("aria-label", btn.title);
    }
  }

  // Set the attribute immediately (documentElement exists in <head>), so if this
  // script is loaded early there's no flash before the button mounts.
  apply(current());

  var btn = null;

  function h(html) {
    var t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstChild;
  }

  function mount() {
    var bar = document.querySelector(".vox-command");
    if (!bar || document.querySelector(".vox-theme-btn")) return;
    btn = h(
      '<button class="vox-theme-btn" type="button" aria-pressed="false">' +
        '<svg class="vox-theme-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>' +
        '<svg class="vox-theme-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8"/></svg>' +
        "</button>"
    );
    btn.addEventListener("click", function () {
      var next = current() === "light" ? "dark" : "light";
      try { localStorage.setItem(KEY, next); } catch (e) {}
      apply(next);
    });
    // Sit right after the Guide button if it's already there, else append.
    var guide = bar.querySelector(".vox-about-btn");
    if (guide && guide.nextSibling) bar.insertBefore(btn, guide.nextSibling);
    else bar.appendChild(btn);
    apply(current());
  }

  // Follow the device if the user hasn't chosen explicitly.
  if (window.matchMedia) {
    try {
      window.matchMedia("(prefers-color-scheme:light)").addEventListener("change", function (e) {
        if (!saved()) apply(e.matches ? "light" : "dark");
      });
    } catch (e) {}
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
