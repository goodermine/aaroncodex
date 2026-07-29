"""Render build info as a page a phone browser will actually display.

Apple browsers download a JSON body instead of showing it (the same reason the
mode-hint route serves HTML), so /api/build content-negotiates: JSON for curl and
fetch, this page for anything that asks for HTML.
"""

from __future__ import annotations

import html

_CSS = """
:root{color-scheme:light}
body{margin:0;padding:22px 16px 60px;background:var(--vox-page);color:var(--vox-ink);
  font-family:var(--vox-sans);
  -webkit-text-size-adjust:100%}
.wrap{max-width:760px;margin:0 auto}
.kick{font:700 11px/1 var(--vox-mono);letter-spacing:.22em;color:var(--vox-accent)}
h1{font-size:21px;margin:12px 0 4px}
p.sub{color:var(--vox-muted);font-size:13px;line-height:1.6;margin:0 0 18px}
.card{border:1px solid var(--vox-line);border-radius:12px;background:var(--vox-panel);padding:14px 16px;margin:0 0 14px}
.card h2{font:700 11px/1 var(--vox-mono);letter-spacing:.16em;text-transform:uppercase;
  color:var(--vox-muted);margin:0 0 10px}
.row{display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-bottom:1px solid var(--vox-line);
  font-size:13.5px;align-items:baseline}
.row:last-child{border-bottom:0}
.row b{font-family:var(--vox-mono);font-weight:600;color:var(--vox-ink);word-break:break-all;text-align:right}
.k{color:var(--vox-muted);flex:0 0 auto}
.big{font:700 15px/1.4 var(--vox-mono);padding:12px 14px;border-radius:10px;margin:0 0 16px}
.ok{background:var(--vox-good-tint);border:1px solid var(--vox-good);color:var(--vox-good)}
.bad{background:var(--vox-weak-tint);border:1px solid var(--vox-weak);color:var(--vox-weak)}
.warn{background:var(--vox-watch-tint);border:1px solid var(--vox-watch);color:var(--vox-watch)}
code{font-family:var(--vox-mono);background:var(--vox-sunken);border:1px solid var(--vox-line-2);
  border-radius:5px;padding:1px 5px;font-size:12.5px}
"""

def _rows(pairs) -> str:
    out = []
    for k, v in pairs:
        out.append(f'<div class="row"><span class="k">{html.escape(str(k))}</span>'
                   f"<b>{html.escape('—' if v is None else str(v))}</b></div>")
    return "".join(out)


def render(info: dict, title: str = "Build") -> str:
    decks = info.get("decks") or {}
    git = info.get("git") or {}
    assets = info.get("assets") or {}

    # Verdict: does the file being served match what this checkout's HEAD has?
    matches = info.get("matches_head")
    if matches is True:
        verdict = ('<div class="big ok">SERVING THIS CHECKOUT&rsquo;S COMMITTED FILES<br>'
                   "The running service is reading the files in this git checkout.</div>")
    elif matches is False:
        verdict = ('<div class="big bad">MISMATCH &mdash; the files being served are NOT '
                   "this checkout&rsquo;s committed version.<br>Either the working tree has "
                   "uncommitted edits, or the service is reading a different directory. "
                   "Check <code>path</code> and <code>checkout</code> below.</div>")
    else:
        verdict = ('<div class="big warn">Could not compare against git '
                   "(not a checkout, or git unavailable). Compare the hashes below by hand.</div>")

    deck_cards = ""
    for name, d in decks.items():
        deck_cards += (
            f'<div class="card"><h2>{html.escape(name)} deck</h2>'
            + _rows([
                ("content hash", d.get("sha1_12")),
                ("matches HEAD", {True: "yes", False: "NO", None: "unknown"}.get(d.get("matches_head"), "unknown")),
                ("file exists", "yes" if d.get("exists") else "NO"),
                ("path", d.get("path")),
            ])
            + "</div>"
        )

    return (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(title)} &mdash; VOX Suite</title>"
        '<link rel="stylesheet" href="/static/vox-tokens.css">'
        f"<style>{_CSS}</style></head><body><div class=wrap>"
        '<div class="kick">VOX//SUITE</div>'
        "<h1>Which build is live?</h1>"
        '<p class="sub">The hashes below are of the files this running process is actually reading '
        "from disk right now. If a fix is in git but not here, the service is not reading the "
        "files you pulled.</p>"
        + verdict
        + deck_cards
        + '<div class="card"><h2>git checkout</h2>'
        + _rows([("commit", git.get("commit")), ("branch", git.get("branch")),
                 ("uncommitted changes", {True: "yes", False: "no", None: "unknown"}.get(git.get("dirty"), "unknown")),
                 ("checkout path", git.get("checkout"))])
        + "</div>"
        + ('<div class="card"><h2>shared assets</h2>' + _rows(sorted(assets.items())) + "</div>" if assets else "")
        + '<p class="sub">Machine-readable: add <code>?format=json</code> to this URL.</p>'
        + "</div></body></html>"
    )
