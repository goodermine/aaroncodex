#!/usr/bin/env python3
"""Render the score-trends data JSON into a self-contained HTML dashboard.

Kept beside score_trends.py; imported by it. No external assets — the page
inlines its CSS, its data, and draws every chart client-side as SVG, so the
file opens standalone and can be published as an Artifact under the CSP.

The visual language is the VOX light kit (design/vox-tokens.css): deep calm
blue accent on a soft-grey page, system fonts, 10px card radius. Light-only on
purpose — the kit deleted its dark layer, so the dashboard matches the apps.

Honesty rules baked into the render:
- Every score is shown as the engine wrote it; nothing is recomputed.
- The per-song visual is the full scatter of takes over time plus a running
  personal-best line — never a single first-vs-latest arrow, which would call
  ordinary take-to-take variance a "decline".
- The provenance footer always states the calibration pack and the pro anchor;
  any legacy take dropped from the trends is named, not hidden.
"""

from __future__ import annotations

import json


def render(data: dict) -> str:
    payload = json.dumps(data, separators=(",", ":"))
    c = data["contract"]
    s = data["summary"]
    best = s.get("best") or {}
    singer = data["singer"].title()
    prov = (f'rubric {c.get("rubric","?")} · calibration '
            f'{c.get("calibration_fingerprint","?")[:12]} · '
            f'{c.get("calibration_references","?")} pro references')
    best_line = (f'{best.get("lead","—")} {best.get("which","")} · '
                 f'{best.get("song","—")}') if best else "—"

    return _TEMPLATE.format(
        singer=singer,
        prov=prov,
        span=f'{s.get("date_first","?")} → {s.get("date_latest","?")}',
        n_perf=s.get("n_performance", 0),
        n_songs=s.get("n_songs", 0),
        n_takes=s.get("n_takes", 0),
        n_learning=s.get("n_learning", 0),
        mean_lead=s.get("mean_lead", "—"),
        best_line=best_line,
        best_val=best.get("lead", "—"),
        anchor=data["anchor"],
        n_excluded=s.get("n_excluded_legacy", 0),
        payload=payload,
    )


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{singer} — Score Trends</title>
<style>
:root {{
  --page:#f6f7f9; --panel:#ffffff; --sunken:#eef1f4; --line:#e4e8ed;
  --line2:#cfd7df; --ink:#131a22; --muted:#5d6a77; --accent:#1d4ed8;
  --accent-deep:#1e40af; --accent-tint:#eef3fe; --good:#15803d;
  --good-tint:#ecf7f0; --watch:#b45309; --watch-tint:#fdf3e7;
  --radius:10px; --radius-sm:6px;
  --shadow-1:0 1px 2px rgba(19,26,34,.06),0 1px 3px rgba(19,26,34,.04);
  --shadow-2:0 4px 12px rgba(19,26,34,.08),0 1px 3px rgba(19,26,34,.05);
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--page); color:var(--ink);
  font-family:var(--sans); line-height:1.5;
  -webkit-font-smoothing:antialiased;
}}
.wrap {{ max-width:1080px; margin:0 auto; padding:32px 20px 64px; }}
header.top {{ margin-bottom:24px; }}
.eyebrow {{
  font:600 12px/1 var(--sans); letter-spacing:.08em; text-transform:uppercase;
  color:var(--accent); margin:0 0 8px;
}}
h1 {{ font:700 30px/1.1 var(--sans); margin:0 0 6px; letter-spacing:-.01em; }}
.sub {{ color:var(--muted); font-size:14px; margin:0; }}
.chips {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }}
.chip {{
  font:600 12px/1 var(--mono); color:var(--muted); background:var(--panel);
  border:1px solid var(--line); border-radius:999px; padding:6px 11px;
}}
.chip.good {{ color:var(--good); background:var(--good-tint); border-color:transparent; }}

section {{ margin-top:28px; }}
h2 {{
  font:650 13px/1 var(--sans); letter-spacing:.06em; text-transform:uppercase;
  color:var(--muted); margin:0 0 14px; padding-bottom:8px;
  border-bottom:1px solid var(--line);
}}

.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; }}
.stat {{
  background:var(--panel); border:1px solid var(--line); border-radius:var(--radius);
  padding:16px 18px; box-shadow:var(--shadow-1);
}}
.stat .k {{ font:600 11px/1 var(--sans); letter-spacing:.05em; text-transform:uppercase; color:var(--muted); }}
.stat .v {{ font:700 26px/1.1 var(--sans); margin-top:8px; font-variant-numeric:tabular-nums; }}
.stat .v small {{ font-weight:600; font-size:13px; color:var(--muted); }}
.stat.hero {{ background:var(--accent); border-color:transparent; color:#fff; }}
.stat.hero .k {{ color:#c9d8ff; }}
.stat.hero .v {{ color:#fff; }}
.stat.hero .v small {{ color:#c9d8ff; }}

.panel {{
  background:var(--panel); border:1px solid var(--line); border-radius:var(--radius);
  padding:18px; box-shadow:var(--shadow-1);
}}
.legend {{ display:flex; flex-wrap:wrap; gap:16px; margin-top:12px; font-size:12.5px; color:var(--muted); }}
.legend span {{ display:inline-flex; align-items:center; gap:6px; }}
.dot {{ width:9px; height:9px; border-radius:50%; display:inline-block; }}
.dot.ov {{ background:var(--accent); }}
.dot.cf {{ background:var(--watch); }}
.swatch {{ width:16px; height:0; border-top:2px dashed var(--line2); display:inline-block; }}
.swatch.best {{ border-top:2px solid var(--good); }}

.cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:14px; }}
.card {{
  background:var(--panel); border:1px solid var(--line); border-radius:var(--radius);
  padding:14px 15px; box-shadow:var(--shadow-1); display:flex; flex-direction:column; gap:8px;
}}
.card .song {{ font:650 15px/1.2 var(--sans); }}
.card .row {{ display:flex; align-items:baseline; justify-content:space-between; gap:8px; }}
.card .best {{ font:700 22px/1 var(--sans); font-variant-numeric:tabular-nums; }}
.card .meta {{ font-size:12px; color:var(--muted); }}
.badge {{
  font:600 11px/1 var(--sans); padding:4px 8px; border-radius:999px;
  background:var(--sunken); color:var(--muted); white-space:nowrap;
}}
.badge.slider {{ background:var(--accent-tint); color:var(--accent-deep); }}
.badge.hybrid {{ background:var(--watch-tint); color:var(--watch); }}
.shift {{ font-size:11.5px; color:var(--watch); }}

table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
.tablewrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:var(--radius); background:var(--panel); }}
th, td {{ text-align:left; padding:10px 12px; border-bottom:1px solid var(--line); white-space:nowrap; }}
th {{
  font:600 11px/1 var(--sans); letter-spacing:.04em; text-transform:uppercase;
  color:var(--muted); cursor:pointer; user-select:none; position:sticky; top:0;
  background:var(--panel);
}}
th:hover {{ color:var(--ink); }}
td.num {{ font-variant-numeric:tabular-nums; text-align:right; }}
tr:last-child td {{ border-bottom:none; }}
tbody tr:hover {{ background:var(--sunken); }}
.pill {{ font:600 12px/1 var(--mono); padding:3px 7px; border-radius:var(--radius-sm); }}

.foot {{
  margin-top:32px; padding:18px; background:var(--panel); border:1px solid var(--line);
  border-radius:var(--radius); font-size:12.5px; color:var(--muted);
}}
.foot b {{ color:var(--ink); }}
.foot code {{ font:600 12px/1.4 var(--mono); background:var(--sunken); padding:2px 6px; border-radius:4px; }}
a {{ color:var(--accent); }}
@media (max-width:520px) {{ h1 {{ font-size:24px; }} .wrap {{ padding:24px 14px 48px; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <p class="eyebrow">VOXAI · Progress</p>
    <h1>{singer} — Score Trends</h1>
    <p class="sub">Every take {singer} has recorded, scored by the one engine and read straight from the archive. {span}.</p>
    <div class="chips">
      <span class="chip good">{prov}</span>
      <span class="chip" id="chip-excluded"></span>
    </div>
  </header>

  <section>
    <div class="stats">
      <div class="stat hero"><div class="k">Best take</div><div class="v">{best_val} <small>{best_line}</small></div></div>
      <div class="stat"><div class="k">Mean lead</div><div class="v">{mean_lead} <small>/ 10</small></div></div>
      <div class="stat"><div class="k">Performance takes</div><div class="v">{n_perf} <small>of {n_takes}</small></div></div>
      <div class="stat"><div class="k">Songs</div><div class="v">{n_songs}</div></div>
    </div>
  </section>

  <section>
    <h2>Overall progression — every performance take</h2>
    <div class="panel">
      <div id="overall"></div>
      <div class="legend">
        <span><span class="dot ov"></span> overall lead</span>
        <span><span class="dot cf"></span> capture-fair lead</span>
        <span><span class="swatch best"></span> personal best so far</span>
        <span><span class="swatch"></span> 10 = a typical pro</span>
      </div>
    </div>
  </section>

  <section>
    <h2>Top songs — best lead, all takes over time</h2>
    <div class="cards" id="cards"></div>
  </section>

  <section>
    <h2>Every song — performance takes</h2>
    <div class="tablewrap"><table id="tbl">
      <thead><tr>
        <th data-k="song">Song</th>
        <th data-k="best_lead" class="num">Best</th>
        <th data-k="n_takes" class="num">Takes</th>
        <th data-k="latest_lead" class="num">Latest</th>
        <th data-k="archetype_latest">Archetype</th>
        <th data-k="shifts" class="num">Shifts</th>
      </tr></thead>
      <tbody></tbody>
    </table></div>
  </section>

  <section id="learning-section">
    <h2>Learning &amp; warm-up takes</h2>
    <p class="sub" style="margin:-6px 0 14px">Practice and rehearsal takes, scored the same way but kept off the leaderboard — never ranked head-to-head with a polished performance. Watch these climb as you re-record them.</p>
    <div class="tablewrap"><table id="ltbl">
      <thead><tr>
        <th data-k="song">Song</th>
        <th data-k="best_lead" class="num">Best</th>
        <th data-k="n_takes" class="num">Takes</th>
        <th data-k="latest_lead" class="num">Latest</th>
        <th data-k="trend">Trend</th>
        <th data-k="span">Recorded</th>
      </tr></thead>
      <tbody></tbody>
    </table></div>
  </section>

  <div class="foot">
    <p style="margin:0 0 8px"><b>How to read this.</b> {anchor}
    The lead number per take is capture-fair on a degraded capture (live / room / phone) and overall otherwise — the same honest rule the rest of the kit uses.</p>
    <p style="margin:0 0 8px"><b>Provenance.</b> {prov}. Scores are read from the stored analyses, never recomputed. Score lines only ever join takes on this one calibration pack; a take on a superseded rubric is dropped from the trends (not hidden) because a stale score reads ~2.5–3 points too harsh.</p>
    <p style="margin:0"><b>Refresh.</b> After new takes land: <code>python3 docs/score-metrics/rescore_all.py</code> then <code>python3 tools/score_trends.py</code>. Data through {span}.</p>
  </div>
</div>

<script id="data" type="application/json">{payload}</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const NS = 'http://www.w3.org/2000/svg';
const el = (t, a={{}}, kids=[]) => {{
  const n = document.createElementNS(NS, t);
  for (const k in a) n.setAttribute(k, a[k]);
  (Array.isArray(kids)?kids:[kids]).forEach(k => k!=null && n.appendChild(typeof k==='string'?document.createTextNode(k):k));
  return n;
}};
const C = {{ accent:'#1d4ed8', watch:'#b45309', good:'#15803d', line:'#e4e8ed', line2:'#cfd7df', muted:'#5d6a77', sunken:'#eef1f4' }};
const dnum = d => {{ const [y,m,da]=d.split('-').map(Number); return y*372 + (m-1)*31 + (da-1); }};

// chip: excluded legacy count
(function(){{
  const n = DATA.summary.n_excluded_legacy||0;
  const c = document.getElementById('chip-excluded');
  c.textContent = n===0 ? 'no legacy scores — all takes comparable' : n+' legacy take(s) excluded from trends';
  if (n===0) c.classList.add('good');
}})();

// ---- Overall progression scatter ----
(function(){{
  const takes = [];
  DATA.songs.forEach(b => b.takes.forEach(t => takes.push(t)));
  takes.sort((a,b)=> dnum(a.date)-dnum(b.date));
  if (!takes.length) return;
  const host = document.getElementById('overall');
  const W = Math.max(560, host.clientWidth||880), H = 300;
  const m = {{l:34, r:14, t:14, b:34}};
  const iw = W-m.l-m.r, ih = H-m.t-m.b;
  const xs = takes.map(t=>dnum(t.date));
  const x0 = Math.min(...xs), x1 = Math.max(...xs) || x0+1;
  const X = v => m.l + (x1===x0?iw/2:(v-x0)/(x1-x0)*iw);
  const Y = v => m.t + (10-v)/10*ih;
  const svg = el('svg',{{viewBox:`0 0 ${{W}} ${{H}}`, width:'100%', role:'img','aria-label':'Score of every take over time'}});
  // gridlines + y labels
  for (let g=0; g<=10; g+=2) {{
    svg.appendChild(el('line',{{x1:m.l,y1:Y(g),x2:W-m.r,y2:Y(g),stroke:C.line,'stroke-width':1}}));
    svg.appendChild(el('text',{{x:m.l-6,y:Y(g)+4,'text-anchor':'end','font-size':11,fill:C.muted}}, String(g)));
  }}
  // "typical pro = 10" line
  svg.appendChild(el('line',{{x1:m.l,y1:Y(10),x2:W-m.r,y2:Y(10),stroke:C.line2,'stroke-width':1,'stroke-dasharray':'4 3'}}));
  // running personal best step line
  let best=-1; const pts=[];
  takes.forEach(t => {{ best=Math.max(best,t.lead); pts.push([X(dnum(t.date)),Y(best)]); }});
  let dstr = pts.map((p,i)=> (i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ');
  svg.appendChild(el('path',{{d:dstr,fill:'none',stroke:C.good,'stroke-width':2,'stroke-linejoin':'round',opacity:.85}}));
  // dots
  takes.forEach(t => {{
    svg.appendChild(el('circle',{{cx:X(dnum(t.date)),cy:Y(t.lead),r:3.6,
      fill: t.which==='capture-fair'?C.watch:C.accent, opacity:.8,
      stroke:'#fff','stroke-width':1}},
      [el('title',{{}}, `${{t.song}} — ${{t.date}} — ${{t.lead}} ${{t.which}}`)]));
  }});
  // x axis end labels
  svg.appendChild(el('text',{{x:m.l,y:H-10,'font-size':11,fill:C.muted}}, takes[0].date));
  svg.appendChild(el('text',{{x:W-m.r,y:H-10,'text-anchor':'end','font-size':11,fill:C.muted}}, takes[takes.length-1].date));
  host.appendChild(svg);
}})();

// ---- Per-song sparkline ----
function spark(b){{
  const W=210, H=52, pad=4;
  const ts=b.takes.slice().sort((a,c)=>dnum(a.date)-dnum(c.date));
  const svg=el('svg',{{viewBox:`0 0 ${{W}} ${{H}}`, width:'100%','aria-hidden':'true'}});
  const xs=ts.map(t=>dnum(t.date));
  const x0=Math.min(...xs), x1=Math.max(...xs)||x0+1;
  const X=v=> pad + (x1===x0?(W-2*pad)/2:(v-x0)/(x1-x0)*(W-2*pad));
  const Y=v=> pad + (10-v)/10*(H-2*pad);
  // running best line
  let best=-1; const pts=[];
  ts.forEach(t=>{{best=Math.max(best,t.lead);pts.push([X(dnum(t.date)),Y(best)]);}});
  svg.appendChild(el('path',{{d:pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' '),
    fill:'none',stroke:C.good,'stroke-width':1.5,opacity:.7}}));
  ts.forEach(t=> svg.appendChild(el('circle',{{cx:X(dnum(t.date)),cy:Y(t.lead),r:2.8,
    fill:t.which==='capture-fair'?C.watch:C.accent,opacity:.85}})));
  return svg;
}}
function archClass(a){{ return a==='Hybrid'?'hybrid':(a==='Pitch Slider'?'slider':''); }}
(function(){{
  const host=document.getElementById('cards');
  DATA.songs.slice(0,9).forEach(b=>{{
    const card=document.createElement('div'); card.className='card';
    const song=document.createElement('div'); song.className='song'; song.textContent=b.song; card.appendChild(song);
    const row=document.createElement('div'); row.className='row';
    const best=document.createElement('span'); best.className='best'; best.textContent=b.best_lead;
    const badge=document.createElement('span'); badge.className='badge '+archClass(b.archetype_latest);
    badge.textContent=b.archetype_latest||'—';
    row.appendChild(best); row.appendChild(badge); card.appendChild(row);
    card.appendChild(spark(b));
    const meta=document.createElement('div'); meta.className='meta';
    meta.textContent=`${{b.n_takes}} take${{b.n_takes>1?'s':''}} · latest ${{b.latest.lead}} ${{b.latest.which}}`;
    card.appendChild(meta);
    if (b.archetype_shifts && b.archetype_shifts.length){{
      const sh=document.createElement('div'); sh.className='shift';
      const last=b.archetype_shifts[b.archetype_shifts.length-1];
      sh.textContent=`↳ shifted ${{last.from}} → ${{last.to}} (${{last.date}})`;
      card.appendChild(sh);
    }}
    host.appendChild(card);
  }});
}})();

// ---- Full table (sortable) ----
(function(){{
  const rows=DATA.songs.map(b=>({{
    song:b.song, best_lead:b.best_lead, n_takes:b.n_takes,
    latest_lead:b.latest.lead, latest_which:b.latest.which,
    archetype_latest:b.archetype_latest||'—', shifts:(b.archetype_shifts||[]).length
  }}));
  const tb=document.querySelector('#tbl tbody');
  let sortK='best_lead', dir=-1;
  function draw(){{
    rows.sort((a,b)=>{{
      let x=a[sortK], y=b[sortK];
      if (typeof x==='string') return dir*x.localeCompare(y);
      return dir*((x||0)-(y||0));
    }});
    tb.innerHTML='';
    rows.forEach(r=>{{
      const tr=document.createElement('tr');
      const ac=archClass(r.archetype_latest);
      tr.innerHTML=`<td>${{r.song}}</td>`+
        `<td class="num"><b>${{r.best_lead}}</b></td>`+
        `<td class="num">${{r.n_takes}}</td>`+
        `<td class="num">${{r.latest_lead}} <span style="color:var(--muted);font-size:11px">${{r.latest_which==='capture-fair'?'cf':'ov'}}</span></td>`+
        `<td><span class="badge ${{ac}}">${{r.archetype_latest}}</span></td>`+
        `<td class="num">${{r.shifts||''}}</td>`;
      tb.appendChild(tr);
    }});
  }}
  document.querySelectorAll('#tbl th').forEach(th=>{{
    th.addEventListener('click',()=>{{
      const k=th.dataset.k==='shifts'?'shifts':th.dataset.k;
      if (sortK===k) dir*=-1; else {{ sortK=k; dir=(k==='song')?1:-1; }}
      draw();
    }});
  }});
  draw();
}})();

// ---- Learning & warm-up table (sortable) ----
(function(){{
  const blocks=DATA.learning||[];
  const sec=document.getElementById('learning-section');
  if (!blocks.length) {{ if (sec) sec.style.display='none'; return; }}
  const rows=blocks.map(b=>{{
    const ts=b.takes.slice().sort((a,c)=>dnum(a.date)-dnum(c.date));
    const span = ts.length>1 ? `${{ts[0].date}} → ${{ts[ts.length-1].date}}` : ts[0].date;
    return {{
      song:b.song, best_lead:b.best_lead, n_takes:b.n_takes,
      latest_lead:b.latest.lead, latest_which:b.latest.which,
      trend:b.trend||'', span, _spanKey:ts[0].date
    }};
  }});
  const tb=document.querySelector('#ltbl tbody');
  let sortK='best_lead', dir=-1;
  const trendColor=t=> t==='improving'?'var(--good)':(t==='slipping'?'var(--watch)':'var(--muted)');
  function draw(){{
    rows.sort((a,b)=>{{
      let x=a[sortK==='span'?'_spanKey':sortK], y=b[sortK==='span'?'_spanKey':sortK];
      if (typeof x==='string') return dir*x.localeCompare(y);
      return dir*((x||0)-(y||0));
    }});
    tb.innerHTML='';
    rows.forEach(r=>{{
      const tr=document.createElement('tr');
      tr.innerHTML=`<td>${{r.song}}</td>`+
        `<td class="num"><b>${{r.best_lead}}</b></td>`+
        `<td class="num">${{r.n_takes}}</td>`+
        `<td class="num">${{r.latest_lead}} <span style="color:var(--muted);font-size:11px">${{r.latest_which==='capture-fair'?'cf':'ov'}}</span></td>`+
        `<td>${{r.trend?`<span style="color:${{trendColor(r.trend)}};font-weight:600">${{r.trend}}</span>`:'<span style="color:var(--muted)">— single take</span>'}}</td>`+
        `<td style="color:var(--muted);font-size:12.5px">${{r.span}}</td>`;
      tb.appendChild(tr);
    }});
  }}
  document.querySelectorAll('#ltbl th').forEach(th=>{{
    th.addEventListener('click',()=>{{
      const k=th.dataset.k;
      if (sortK===k) dir*=-1; else {{ sortK=k; dir=(k==='song'||k==='trend')?1:-1; }}
      draw();
    }});
  }});
  draw();
}})();
</script>
</body>
</html>
"""
