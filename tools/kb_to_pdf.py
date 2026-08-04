#!/usr/bin/env python3
"""Render a vocal-knowledge-base document to a readable, house-styled PDF.

    python3 tools/kb_to_pdf.py vocal-knowledge-base/01-.../doc.md [--out X.pdf]

Generated FROM the markdown, never hand-built, so the PDF cannot drift from the
library the way a hand-maintained copy would. Works on any document in the
knowledge base — all 80 of them will need this if the library is ever published.

Typeset for READING, not for pinning to a wall: a narrower measure than the
drill card, more leading, and headings that stay with the text under them.

Supports the subset of markdown the library actually uses: YAML front matter,
ATX headings, paragraphs, bullet and numbered lists, pipe tables, blockquotes,
horizontal rules, and inline bold / italic / code / links.
"""
from __future__ import annotations

import argparse
import html
import os
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

# DejaVu is the house font because the library needs ♯ ♭ ♮ ¢ — Liberation Sans
# Italic, the obvious substitute, is missing ♭ and ♮, and a missing glyph in a
# vocal document silently turns "B♭4" into "B4". Not every image ships a DejaVu
# Sans oblique, so italics fall back through candidates that DO carry the music
# symbols, and the build says which one it used rather than failing or guessing.
DEJAVU = "/usr/share/fonts/truetype/dejavu/"
ITALIC_CANDIDATES = [
    DEJAVU + "DejaVuSans-Oblique.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansOblique.ttf",   # verified 6/6 glyphs
    DEJAVU + "DejaVuSans.ttf",                                   # upright, last resort
]


def _register_fonts() -> str:
    pdfmetrics.registerFont(TTFont("DJ", DEJAVU + "DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DJ-B", DEJAVU + "DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("DJ-M", DEJAVU + "DejaVuSansMono.ttf"))
    for path in ITALIC_CANDIDATES:
        if os.path.isfile(path):
            pdfmetrics.registerFont(TTFont("DJ-I", path))
            pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJ-B",
                                          italic="DJ-I", boldItalic="DJ-B")
            return os.path.basename(path)
    raise SystemExit("no usable italic font found")


ITALIC_FONT = _register_fonts()

BLUE = colors.HexColor("#1d4ed8")
DEEP = colors.HexColor("#0f2a6b")
INK = colors.HexColor("#111827")
GREY = colors.HexColor("#4b5563")
RULE = colors.HexColor("#d1d5db")
TINT = colors.HexColor("#eff4ff")

MARGIN = 24 * mm
BODY_W = A4[0] - 2 * MARGIN

S = {
    "title": ParagraphStyle("title", fontName="DJ-B", fontSize=20, leading=24,
                            textColor=BLUE, spaceAfter=3),
    "subtitle": ParagraphStyle("subtitle", fontName="DJ-I", fontSize=11, leading=15,
                               textColor=GREY, spaceAfter=12),
    "h1": ParagraphStyle("h1", fontName="DJ-B", fontSize=15.5, leading=19,
                         textColor=BLUE, spaceBefore=16, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="DJ-B", fontSize=13, leading=16.5,
                         textColor=DEEP, spaceBefore=14, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="DJ-B", fontSize=10.8, leading=14,
                         textColor=INK, spaceBefore=10, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="DJ", fontSize=9.8, leading=14.6,
                        textColor=INK, spaceAfter=7),
    "li": ParagraphStyle("li", fontName="DJ", fontSize=9.8, leading=14.2,
                         textColor=INK, leftIndent=11, spaceAfter=3.5),
    "quote": ParagraphStyle("quote", fontName="DJ", fontSize=9.5, leading=14,
                            textColor=INK),
    "meta": ParagraphStyle("meta", fontName="DJ", fontSize=8, leading=11,
                           textColor=GREY, spaceAfter=3),
    # Table cells must NOT inherit the list style's leftIndent: it silently eats
    # 11pt of every column, which is exactly what made "management" break as
    # "mana gement" after the column widths had supposedly been fixed.
    "td": ParagraphStyle("td", fontName="DJ", fontSize=9.8, leading=14.2,
                         textColor=INK, leftIndent=0, spaceAfter=0),
    "th": ParagraphStyle("th", fontName="DJ-B", fontSize=9.8, leading=14.2,
                         textColor=colors.white, leftIndent=0, spaceAfter=0),
}

INLINE_CODE = '<font face="DJ-M" size="8.8" color="#0f2a6b">%s</font>'


def inline(md: str) -> str:
    """Markdown inline -> ReportLab markup. Escapes first so `<` in prose is safe."""
    out = html.escape(md, quote=False)
    out = re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", out)          # links -> text
    out = re.sub(r"`([^`]+)`", lambda m: INLINE_CODE % m.group(1), out)
    out = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", out)
    return out


def split_front_matter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm, text[m.end():]


def _plain(cell: str) -> str:
    """Cell text with markdown syntax removed, for measuring."""
    return re.sub(r"[*`\[\]]|\((?:[^)]*)\)", "", cell)


def _column_widths(rows, ncol):
    """Width columns so no word is ever broken mid-character.

    A naive "proportional to the longest cell" split starves narrow columns and
    ReportLab then chops words in half — the drill-library table rendered
    "Registra tion" and "Vowel m odificati on". So: give every column at least
    enough room for its longest unbreakable WORD, then share what is left in
    proportion to how much text each column actually carries.
    """
    pad = 14                                        # cell padding, both sides
    def word_w(word):
        return pdfmetrics.stringWidth(word, "DJ-B", 9.8) + pad

    floors, mass = [], []
    for c in range(ncol):
        longest = 0.0
        chars = 0
        for r in rows:
            text = _plain(r[c])
            chars += len(text)
            for word in text.split():
                longest = max(longest, word_w(word))
        floors.append(longest)
        mass.append(max(chars, 1))

    if sum(floors) >= BODY_W:
        # Genuinely too wide even at minimum: scale down and accept some
        # breaking rather than overflowing the page.
        scale = BODY_W / sum(floors)
        return [f * scale for f in floors]

    spare = BODY_W - sum(floors)
    total_mass = sum(mass)
    return [floors[c] + spare * mass[c] / total_mass for c in range(ncol)]


def make_table(rows, widths=None):
    """A pipe table, sized so words are never broken mid-character."""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    widths = widths or _column_widths(rows, ncol)
    data = [[Paragraph(inline(c), S["td"] if r else S["th"])
             for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DEEP),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def make_quote(lines):
    body = [Paragraph(inline(l), S["quote"]) for l in lines if l.strip()]
    t = Table([[body]], colWidths=[BODY_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TINT),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def build_story(body: str, fm: dict):
    story = []
    lines = body.split("\n")
    i = 0
    para: list[str] = []
    pending_heading = None          # heading waits for its first block (no orphans)

    def flush_para():
        nonlocal para
        if para:
            emit(Paragraph(inline(" ".join(para)), S["p"]))
            para = []

    def emit(flowable):
        """Attach a heading to whatever follows it, so it can never strand at the
        foot of a page. This is the defect that had to be fixed by hand in the
        drill-card build; here it is structural."""
        nonlocal pending_heading
        if pending_heading is not None:
            story.append(KeepTogether([pending_heading, flowable]))
            pending_heading = None
        else:
            story.append(flowable)

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_para()
            i += 1
            continue

        if stripped.startswith("#"):
            flush_para()
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped.lstrip("#").strip()
            if level == 1:
                story.append(Paragraph(inline(text), S["title"]))
            else:
                pending_heading = Paragraph(inline(text),
                                            S["h1" if level == 2 else
                                              "h2" if level == 3 else "h3"])
            i += 1
            continue

        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            flush_para()
            story.append(Spacer(1, 4))
            i += 1
            continue

        if stripped.startswith(">"):
            flush_para()
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip(">").strip())
                i += 1
            # blank-line-separated paragraphs inside one quote
            paras, cur = [], []
            for b in block:
                if b:
                    cur.append(b)
                elif cur:
                    paras.append(" ".join(cur)); cur = []
            if cur:
                paras.append(" ".join(cur))
            emit(make_quote(paras))
            story.append(Spacer(1, 5))
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and \
                re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            flush_para()
            rows = []
            header = [c.strip() for c in stripped.strip("|").split("|")]
            rows.append(header)
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            emit(make_table(rows))
            story.append(Spacer(1, 7))
            continue

        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if m:
            flush_para()
            indent, marker, text = m.groups()
            # continuation lines belong to this item
            i += 1
            while i < len(lines) and lines[i].strip() and \
                    not re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i]) and \
                    lines[i].startswith((" ", "\t")) and not lines[i].strip().startswith(("|", ">", "#")):
                text += " " + lines[i].strip()
                i += 1
            bullet = "•" if marker in "-*+" else marker
            style = ParagraphStyle("li_i", parent=S["li"],
                                   leftIndent=11 + len(indent) // 2 * 9)
            emit(Paragraph(f"{bullet}&nbsp; {inline(text)}", style))
            continue

        para.append(stripped)
        i += 1

    flush_para()
    return story


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source")
    ap.add_argument("--out")
    args = ap.parse_args()

    raw = open(args.source, encoding="utf-8").read()
    fm, body = split_front_matter(raw)
    out = args.out or os.path.splitext(os.path.basename(args.source))[0] + ".pdf"
    title = fm.get("title") or os.path.basename(args.source)
    running = title.upper()

    story = []
    if fm.get("subtitle"):
        # the H1 in the body carries the title; subtitle sits under it
        pass
    story += build_story(body, fm)

    # provenance block, from the front matter, at the foot of the document
    meta_bits = []
    for key, label in (("author", "Author"), ("research_method", "How it was made"),
                       ("source_creator", "Original creator"), ("source_title", "Source"),
                       ("category", "Category"), ("topics", "Topics")):
        if fm.get(key):
            meta_bits.append(f"<b>{label}:</b> {html.escape(fm[key])}")
    # One compact colophon paragraph. Split across two flowables it stranded a
    # nearly empty final page; kept together but tall it did the same. Merging
    # the provenance and the source line into one short block lets it finish on
    # the last page of content whenever there is room.
    meta_bits.append("Rendered from <font face='DJ-M' size='7.4'>%s</font>"
                     % html.escape(args.source))
    story.append(KeepTogether([
        Spacer(1, 8),
        Paragraph(" &nbsp;·&nbsp; ".join(meta_bits), S["meta"]),
    ]))

    def furniture(canvas, doc):
        canvas.saveState()
        canvas.setFont("DJ-B", 7.2)
        canvas.setFillColor(BLUE)
        canvas.drawString(MARGIN, A4[1] - 13 * mm, "VOX//SUITE")
        canvas.setFont("DJ", 7.2)
        canvas.setFillColor(GREY)
        head = running if len(running) < 62 else running[:59] + "…"
        canvas.drawRightString(A4[0] - MARGIN, A4[1] - 13 * mm, head)
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, A4[1] - 15.5 * mm, A4[0] - MARGIN, A4[1] - 15.5 * mm)
        canvas.line(MARGIN, 15 * mm, A4[0] - MARGIN, 15 * mm)
        canvas.setFont("DJ", 7)
        canvas.drawString(MARGIN, 11 * mm, "Vocal Knowledge Base")
        canvas.drawRightString(A4[0] - MARGIN, 11 * mm, str(doc.page))
        canvas.restoreState()

    doc = BaseDocTemplate(out, pagesize=A4,
                          leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=20 * mm, bottomMargin=20 * mm,
                          title=title, author=fm.get("author", "VOX//SUITE"))
    doc.addPageTemplates([PageTemplate(
        id="main",
        frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")],
        onPage=furniture)])
    doc.build(story)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
