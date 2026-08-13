"""Renderer for the VOX systems hub — one directory page of every system.

Used by both surfaces so they stay identical:
  * the live ``GET /hub`` route (same-origin links, api_url="/api/systems"),
  * the standalone file Candy hosts (absolute links, api_url=<suite>/api/systems).

The stylesheet is inlined rather than pulled from ``/static`` so the page has
zero external dependencies — it renders the same whether served by the suite or
opened as a lone file, and can't come up unstyled if a kit file fails to load.
"""

from __future__ import annotations

import html
import json

_CSS = """
:root{--bg:#eef1f6;--surface:#fff;--surface2:#f7f9fc;--line:#e0e5ee;--ink:#18202e;
  --muted:#657084;--accent:#0e7aa8;--accent-ink:#fff;--green:#17a34a;--amber:#d97706;--red:#dc2626;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}
@media(prefers-color-scheme:dark){:root{--bg:#0f1319;--surface:#171d26;--surface2:#1c232e;--line:#2a323e;
  --ink:#eef2f7;--muted:#93a0b0;--accent:#38bdf8;--accent-ink:#06121b;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.5}
.wrap{max-width:960px;margin:0 auto;padding:28px 20px 60px}
header{display:flex;align-items:center;gap:14px;padding-bottom:20px;border-bottom:1px solid var(--line);margin-bottom:8px}
.glyph{width:38px;height:38px;color:var(--accent);flex:0 0 auto}
.brand{font:800 20px/1 var(--sans);letter-spacing:.02em}.brand b{color:var(--accent)}
.brand small{display:block;font:600 10px/1.4 var(--mono);letter-spacing:.18em;color:var(--muted);margin-top:5px}
.spacer{flex:1}
.refresh{font:600 11px var(--mono);letter-spacing:.08em;color:var(--muted);display:flex;align-items:center;gap:7px}
.refresh .dot{width:8px;height:8px;border-radius:50%;background:var(--muted)}
.refresh.ok .dot{background:var(--green)}.refresh.off .dot{background:var(--amber)}
h2{font:700 11px var(--mono);letter-spacing:.16em;color:var(--muted);margin:26px 0 12px;text-transform:uppercase}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
a.card{display:flex;gap:13px;align-items:flex-start;text-decoration:none;color:inherit;background:var(--surface);
  border:1px solid var(--line);border-radius:14px;padding:15px 16px;transition:.14s;position:relative}
a.card:hover{border-color:var(--accent);transform:translateY(-1px);box-shadow:0 6px 20px rgba(15,30,60,.08)}
.code{flex:0 0 auto;width:42px;height:42px;border-radius:10px;background:var(--surface2);border:1px solid var(--line);
  display:flex;align-items:center;justify-content:center;font:700 13px var(--mono);letter-spacing:.02em;color:var(--accent)}
.body{flex:1;min-width:0}
.row{display:flex;align-items:center;gap:8px}
.name{font:700 15px var(--sans)}
.dot{width:9px;height:9px;border-radius:50%;background:var(--muted);flex:0 0 auto}
.dot.live{background:var(--green)}.dot.down{background:var(--red)}
.path{font:600 11px var(--mono);color:var(--muted);margin-left:auto}
.blurb{color:var(--muted);font-size:13px;margin-top:5px}
footer{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}
footer code{font-family:var(--mono);background:var(--surface2);padding:1px 6px;border-radius:5px;border:1px solid var(--line)}
"""

_GLYPH = ('<svg class="glyph" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
          'stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h3l2-7 4 15 3-11 2 5h6"/></svg>')

_REFRESH_JS = """
(function(){
  var API=%(api)s, REL=%(rel)s;   // REL: use same-origin relative paths (live hub) vs absolute urls (standalone)
  var elStat=document.getElementById('refresh');
  function dotClass(live){return live===true?'dot live':live===false?'dot down':'dot';}
  function group(g){var id='grp-'+g,el=document.getElementById(id);
    if(!el){var sec=document.createElement('section');
      var h=document.createElement('h2');h.textContent=g;sec.appendChild(h);
      var gr=document.createElement('div');gr.className='grid';gr.id=id;sec.appendChild(gr);
      document.getElementById('groups').appendChild(sec);el=gr;}
    return el;}
  function upsert(s){
    var card=document.querySelector('a.card[data-id="'+s.id+'"]');
    if(!card){card=document.createElement('a');card.className='card';card.setAttribute('data-id',s.id);
      card.innerHTML='<div class="code"></div><div class="body"><div class="row">'
        +'<span class="name"></span><span class="dot"></span><span class="path"></span></div>'
        +'<div class="blurb"></div></div>';
      group(s.group).appendChild(card);}
    card.href=(REL&&s.path)?s.path:s.url;   // relative on the live hub so it survives a reverse proxy
    card.querySelector('.code').textContent=s.code;
    card.querySelector('.name').textContent=s.name;
    card.querySelector('.path').textContent=s.path;
    card.querySelector('.blurb').textContent=s.blurb;
    card.querySelector('.dot').className=dotClass(s.live);
  }
  function refresh(){
    fetch(API,{cache:'no-store'}).then(function(r){return r.ok?r.json():Promise.reject();})
      .then(function(d){(d.systems||[]).forEach(upsert);
        if(elStat){elStat.className='refresh ok';elStat.querySelector('.txt').textContent='LIVE';}})
      .catch(function(){if(elStat){elStat.className='refresh off';elStat.querySelector('.txt').textContent='CACHED';}});
  }
  refresh(); setInterval(refresh, 30000);
})();
"""


def _card(s: dict) -> str:
    live = s.get("live")
    dot = "dot live" if live is True else "dot down" if live is False else "dot"
    return (
        f'<a class="card" data-id="{html.escape(s["id"])}" href="{html.escape(s["url"])}">'
        f'<div class="code">{html.escape(s["code"])}</div>'
        f'<div class="body"><div class="row">'
        f'<span class="name">{html.escape(s["name"])}</span>'
        f'<span class="{dot}"></span>'
        f'<span class="path">{html.escape(s["path"])}</span></div>'
        f'<div class="blurb">{html.escape(s["blurb"])}</div></div></a>'
    )


def render(systems: list[dict], *, api_url: str = "/api/systems",
           standalone: bool = False, base_url: str = "", generated: str = "") -> str:
    """Full HTML for the hub. ``systems`` is the resolved registry (each with
    ``url``/``live``/``group``); ``api_url`` is what the page polls to stay live."""
    groups: dict[str, list[dict]] = {}
    for s in systems:
        groups.setdefault(s["group"], []).append(s)
    sections = []
    for g, items in groups.items():
        cards = "".join(_card(s) for s in items)
        sections.append(f'<section><h2>{html.escape(g)}</h2>'
                        f'<div class="grid" id="grp-{html.escape(g)}">{cards}</div></section>')

    if standalone:
        note = ("This copy points at <code>" + html.escape(base_url or "the suite") + "</code>. "
                "It refreshes automatically whenever that address is reachable"
                + (f", and was generated {html.escape(generated)}" if generated else "") + ".")
    else:
        note = ("Links are same-origin — they follow the suite to whatever address it's hosted on, "
                "so they never go stale. This page is generated live from the server's own routes.")

    js = _REFRESH_JS % {"api": json.dumps(api_url), "rel": json.dumps(not standalone)}
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>VOX Suite — Systems</title>"
        f"<style>{_CSS}</style></head><body><div class=\"wrap\">"
        f"<header>{_GLYPH}<div class=\"brand\">VOX<b>//</b>SUITE<small>SYSTEMS DIRECTORY</small></div>"
        "<div class=\"spacer\"></div>"
        "<div class=\"refresh\" id=\"refresh\"><span class=\"dot\"></span><span class=\"txt\">…</span></div>"
        "</header>"
        f"<div id=\"groups\">{''.join(sections)}</div>"
        f"<footer>{note}</footer>"
        f"</div><script>{js}</script></body></html>"
    )
