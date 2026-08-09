"""A floating "jump to any app" menu, injected into every page the suite serves.

Built once from the systems registry so it's identical on every page and
auto-updates when the registry changes. Rendered inside a **shadow DOM** so its
styles can't clash with — or be clobbered by — each app's own CSS (the pitch
monitor and TimberTones ship their own palettes). Injected at serve time, so the
self-contained apps get it without editing their HTML.

Links are same-origin (relative), so the menu follows the suite to any address
(Tailscale, cloud, localhost) without going stale.
"""

from __future__ import annotations

import html as _html
import json

# Groups shown in the menu (the SYSTEM/diagnostic entries are left out).
_MENU_GROUPS = ("STUDIO", "PRACTICE")

_TEMPLATE = """
<div id="vox-nav" style="position:fixed;left:16px;bottom:16px;z-index:2147483647"></div>
<template id="vox-nav-tpl"><style>
:host,*{box-sizing:border-box}
.fab{width:46px;height:46px;border-radius:50%;border:1px solid rgba(255,255,255,.14);
  background:#1b2129;color:#e8edf3;cursor:pointer;display:flex;align-items:center;justify-content:center;
  box-shadow:0 6px 20px rgba(0,0,0,.35);transition:transform .12s,background .12s;padding:0}
.fab:hover{background:#242c36;transform:translateY(-1px)}
.fab svg{width:22px;height:22px}
.panel{position:absolute;left:0;bottom:56px;width:230px;background:#12161c;color:#e8edf3;
  border:1px solid #2a323d;border-radius:14px;padding:8px;box-shadow:0 12px 40px rgba(0,0,0,.5);
  font:14px/1.3 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.panel[hidden]{display:none}
.title{font:700 10px/1 system-ui;letter-spacing:.16em;color:#8b97a7;text-transform:uppercase;padding:8px 10px 6px}
.item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:9px;text-decoration:none;color:#e8edf3}
.item:hover{background:#1e242c}
.item.active{background:rgba(59,130,246,.18);color:#cfe0ff}
.item .code{flex:0 0 auto;width:30px;height:24px;border-radius:6px;background:#1e242c;border:1px solid #2a323d;
  display:flex;align-items:center;justify-content:center;font:700 10px ui-monospace,Menlo,monospace;color:#7fb0ff}
.item.active .code{background:#1d3357;border-color:#2f4f86}
.sep{height:1px;background:#232a33;margin:6px 4px}
</style>
<button class="fab" aria-label="Open VOX menu" aria-haspopup="true">
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="5" r="2"/><circle cx="12" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="12" cy="19" r="2"/><circle cx="19" cy="19" r="2"/></svg>
</button>
<nav class="panel" hidden>__ITEMS__</nav>
</template>
<script>
(function(){
  var host=document.getElementById('vox-nav');
  if(!host||host.shadowRoot)return;
  var tpl=document.getElementById('vox-nav-tpl');
  var root=host.attachShadow({mode:'open'});
  root.appendChild(tpl.content.cloneNode(true));
  tpl.remove();
  var fab=root.querySelector('.fab'), panel=root.querySelector('.panel');
  function set(open){panel.hidden=!open;fab.setAttribute('aria-expanded',open?'true':'false');}
  fab.addEventListener('click',function(e){e.stopPropagation();set(panel.hidden);});
  root.addEventListener('click',function(e){e.stopPropagation();});
  document.addEventListener('click',function(){set(false);});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')set(false);});
})();
</script>
"""


def _norm(path: str) -> str:
    p = (path or "/").rstrip("/")
    return p or "/"


def render(systems: list[dict], current_path: str) -> str:
    """The injectable menu snippet. ``systems`` is the resolved registry;
    ``current_path`` marks the active entry."""
    cur = _norm(current_path)
    # Hub first (the full directory), then the app entries.
    entries = [{"name": "Systems Hub", "code": "⌂", "path": "/hub", "group": "TOP"}]
    entries += [s for s in systems if s.get("group") in _MENU_GROUPS]

    rows, last_group = [], "TOP"
    for e in entries:
        g = e.get("group", "")
        if g != last_group and g != "TOP":
            rows.append('<div class="sep"></div>')
        last_group = g
        active = " active" if _norm(e["path"]) == cur else ""
        rows.append(
            f'<a class="item{active}" href="{_html.escape(e["path"])}">'
            f'<span class="code">{_html.escape(e["code"])}</span>'
            f'<span>{_html.escape(e["name"])}</span></a>'
        )
    return _TEMPLATE.replace("__ITEMS__", "".join(rows))


def inject(page_html: str, snippet: str) -> str:
    """Insert the snippet just before </body> (or append if there isn't one)."""
    idx = page_html.lower().rfind("</body>")
    if idx == -1:
        return page_html + snippet
    return page_html[:idx] + snippet + page_html[idx:]
