"""A visible top navigation bar, injected into every page the suite serves.

Built once from the systems registry so it's identical on every page and
auto-updates when the registry changes. The bar's own markup lives in a shadow
DOM so its styles can't clash with — or be clobbered by — each app's CSS (the
pitch monitor and TimberTones ship their own palettes).

The hard part is that some apps own the whole viewport (the monitor is
``#app{position:fixed;inset:0}``), so a plain fixed bar would cover them. At
runtime the injected script moves all existing page content into a wrapper
pinned *below* the bar. The wrapper carries a ``transform`` so it becomes the
containing block for ``position:fixed`` descendants too — that's what keeps a
full-viewport app tucked under the bar instead of behind it.

Links are same-origin (relative), so the bar follows the suite to any address
(Tailscale, cloud, localhost) without going stale.
"""

from __future__ import annotations

import html as _html

BAR_H = 46  # px — keep in sync between the fixed bar and the content wrapper offset

# Groups shown in the bar (the SYSTEM/diagnostic entries are left out).
_MENU_GROUPS = ("STUDIO", "PRACTICE")

_TEMPLATE = """
<template id="vox-nav-tpl"><style>
:host{display:block}
*{box-sizing:border-box}
.bar{display:flex;align-items:center;gap:4px;height:%(h)dpx;padding:0 10px;
  background:#12161c;border-bottom:1px solid #2a323d;overflow-x:auto;white-space:nowrap;
  -webkit-overflow-scrolling:touch;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.bar::-webkit-scrollbar{height:0}
.brand{flex:0 0 auto;font:800 13px system-ui;color:#e8edf3;letter-spacing:.02em;padding:0 8px 0 2px}
.brand b{color:#3b82f6}
.link{flex:0 0 auto;display:inline-flex;align-items:center;gap:7px;text-decoration:none;color:#cdd6e2;
  padding:7px 11px;border-radius:9px;font:600 13px system-ui}
.link:hover{background:#1e242c}
.link.active{background:rgba(59,130,246,.18);color:#cfe0ff}
.code{font:700 9px ui-monospace,Menlo,monospace;color:#7fb0ff;background:#1e242c;border:1px solid #2a323d;
  border-radius:5px;padding:2px 5px}
.link.active .code{background:#1d3357;border-color:#2f4f86}
</style>
<nav class="bar"><span class="brand">VOX<b>//</b></span>__ITEMS__</nav>
</template>
<script>
(function(){
  if(window.__voxNav)return; window.__voxNav=1;
  var BAR=%(h)d, tpl=document.getElementById('vox-nav-tpl');
  if(!tpl)return;
  // Move existing page content (everything except scripts/this template) below the bar.
  var kids=[], ch=document.body.children, i;
  for(i=0;i<ch.length;i++){var c=ch[i]; if(c!==tpl && c.tagName!=='SCRIPT') kids.push(c);}
  var below=document.createElement('div'); below.id='vox-below';
  for(i=0;i<kids.length;i++) below.appendChild(kids[i]);
  var bar=document.createElement('div'); bar.id='vox-topbar';
  bar.attachShadow({mode:'open'}).appendChild(tpl.content.cloneNode(true));
  document.body.appendChild(bar); document.body.appendChild(below);
  var st=document.createElement('style');
  st.textContent='#vox-topbar{position:fixed;top:0;left:0;right:0;height:'+BAR+'px;z-index:2147483647}'+
    '#vox-below{position:fixed;top:'+BAR+'px;left:0;right:0;bottom:0;overflow:auto;'+
    'transform:translateZ(0);-webkit-overflow-scrolling:touch}';
  (document.head||document.documentElement).appendChild(st);
})();
</script>
"""


def _norm(path: str) -> str:
    p = (path or "/").rstrip("/")
    return p or "/"


def render(systems: list[dict], current_path: str) -> str:
    """The injectable top-bar snippet. ``systems`` is the resolved registry;
    ``current_path`` marks the active link."""
    cur = _norm(current_path)
    entries = [{"name": "Hub", "code": "⌂", "path": "/hub", "group": "TOP"}]
    entries += [s for s in systems if s.get("group") in _MENU_GROUPS]

    links = []
    for e in entries:
        active = " active" if _norm(e["path"]) == cur else ""
        links.append(
            f'<a class="link{active}" href="{_html.escape(e["path"])}">'
            f'<span class="code">{_html.escape(e["code"])}</span>'
            f'<span>{_html.escape(e["name"])}</span></a>'
        )
    return (_TEMPLATE % {"h": BAR_H}).replace("__ITEMS__", "".join(links))


def inject(page_html: str, snippet: str) -> str:
    """Insert the snippet just before </body> (or append if there isn't one)."""
    idx = page_html.lower().rfind("</body>")
    if idx == -1:
        return page_html + snippet
    return page_html[:idx] + snippet + page_html[idx:]
