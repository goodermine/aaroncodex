#!/usr/bin/env python3
"""Aaron's Blinding Lights practice sheet, in the VOX//SUITE house style.

Style copied from aaroncodex tools/build_drill_pdf.py (SINGER_REPORT_STANDARD):
Aaron blue accent, a deeper accent for the drill table, plain-words callouts,
DejaVu throughout (needed for the flat/sharp glyphs), KeepTogether on blocks.

Raw measures only (seconds held, time on note) from take 1 vs the original's
engine analysis — no score is quoted. Lyrics are referenced by short cues only;
the vowel runs use Aaron's own vowel-code sheet.
"""
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, KeepTogether, PageBreak)

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DJ", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DJ-B", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DJ-M", F + "DejaVuSansMono.ttf"))
pdfmetrics.registerFont(TTFont("DJ-MB", F + "DejaVuSansMono-Bold.ttf"))
pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJ-B")
pdfmetrics.registerFontFamily("DJ-M", normal="DJ-M", bold="DJ-MB")

BLUE = colors.HexColor("#1d4ed8")      # Aaron's accent
DEEP = colors.HexColor("#0f2a6b")      # the serious table
INK = colors.HexColor("#111827")
GREY = colors.HexColor("#4b5563")
RULE = colors.HexColor("#d1d5db")
TINT = colors.HexColor("#eff4ff")
GOOD = colors.HexColor("#ecfdf3")
GOODE = colors.HexColor("#15803d")

OUT = (sys.argv[1] if len(sys.argv) > 1 else
       "/home/user/aaroncodex/docs/practice/blinding-lights-practice-sheet.pdf")

S = dict(
    h1=ParagraphStyle("h1", fontName="DJ-B", fontSize=21, leading=25, textColor=BLUE, spaceAfter=2),
    sub=ParagraphStyle("sub", fontName="DJ", fontSize=10.2, leading=14, textColor=GREY, spaceAfter=10),
    h2=ParagraphStyle("h2", fontName="DJ-B", fontSize=13.5, leading=17, textColor=DEEP,
                      spaceBefore=12, spaceAfter=5),
    h3=ParagraphStyle("h3", fontName="DJ-B", fontSize=11, leading=14.5, textColor=INK,
                      spaceBefore=8, spaceAfter=3),
    p=ParagraphStyle("p", fontName="DJ", fontSize=9.4, leading=13.4, textColor=INK,
                     spaceAfter=5, alignment=TA_LEFT),
    li=ParagraphStyle("li", fontName="DJ", fontSize=9.4, leading=13.4, textColor=INK,
                      leftIndent=11, bulletIndent=1, spaceAfter=2.5),
    note=ParagraphStyle("note", fontName="DJ", fontSize=9.2, leading=13.2, textColor=INK),
    cell=ParagraphStyle("cell", fontName="DJ", fontSize=8.8, leading=11.6, textColor=INK),
    cellw=ParagraphStyle("cellw", fontName="DJ-B", fontSize=8.8, leading=11.6, textColor=colors.white),
    run=ParagraphStyle("run", fontName="DJ-M", fontSize=9.6, leading=13, textColor=INK),
    big=ParagraphStyle("big", fontName="DJ-MB", fontSize=12.5, leading=18, textColor=DEEP),
    small=ParagraphStyle("small", fontName="DJ", fontSize=8.2, leading=11.5, textColor=GREY, spaceAfter=4),
)


def P(t, s="p"):
    return Paragraph(t, S[s])


def bullets(items):
    return [Paragraph(f"• {i}", S["li"]) for i in items]


def steps(items):
    return [Paragraph(f"<b>{n}.</b> {i}", S["li"]) for n, i in enumerate(items, 1)]


def callout(html, tint=TINT, edge=BLUE):
    t = Table([[Paragraph(html, S["note"])]], colWidths=[168 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), tint),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, edge),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def grid(rows, widths, header_bg=DEEP, center=(), run_cols=()):
    """rows[0] is the header. Cells become Paragraphs so long text wraps."""
    data = []
    for r, row in enumerate(rows):
        out = []
        for c, v in enumerate(row):
            if r == 0:
                out.append(Paragraph(v, S["cellw"]))
            elif c in run_cols:
                out.append(Paragraph(v, S["run"]))
            else:
                out.append(Paragraph(v, S["cell"]))
        data.append(out)
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    st = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]
    for c in center:
        st.append(("ALIGN", (c, 0), (c, -1), "CENTER"))
    t.setStyle(TableStyle(st))
    return t


def furniture(canvas, doc):
    canvas.saveState()
    canvas.setFont("DJ-B", 7.4)
    canvas.setFillColor(BLUE)
    canvas.drawString(21 * mm, A4[1] - 12 * mm, "VOX//SUITE")
    canvas.setFont("DJ", 7.4)
    canvas.setFillColor(GREY)
    canvas.drawRightString(A4[0] - 21 * mm, A4[1] - 12 * mm,
                           "AARON — BLINDING LIGHTS PRACTICE SHEET")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(21 * mm, A4[1] - 14.5 * mm, A4[0] - 21 * mm, A4[1] - 14.5 * mm)
    canvas.line(21 * mm, 15 * mm, A4[0] - 21 * mm, 15 * mm)
    canvas.setFont("DJ", 7)
    canvas.drawString(21 * mm, 11 * mm,
                      "Take 1 (home, 7 Oct 2026) vs the original · raw measures only, no score "
                      "quoted · one take: an early read, not a verdict")
    canvas.drawRightString(A4[0] - 21 * mm, 11 * mm, f"{doc.page}")
    canvas.restoreState()


HOLD, CLIP, BR = "━━━", "•", "✓"
story = []
A = story.append

# ── page 1: what the take showed ─────────────────────────────────────────────
A(P("Blinding Lights — Practice Sheet", "h1"))
A(P("Aaron Ellis · built from your take 1 (home, 7 Oct 2026) measured note-by-note "
    "against The Weeknd's original · vowel runs from your own vowel-code sheet", "sub"))
A(callout(
    "<b>You can sing these notes. You're holding the wrong ones.</b><br/><br/>"
    "In the original, The Weeknd <b>holds the “Ooh”s</b> (about 3 seconds each) and "
    "<b>clips the line endings</b> short. You do the opposite: shorter Oohs, long "
    "endings. The long endings are where your pitch drops. <b>Every one of your "
    "worst-pitch notes is a line ending you held too long.</b>"))
A(Spacer(1, 4))

A(P("What your take showed", "h2"))
A(grid([
    ["Measure", "The Weeknd", "You", "What it means"],
    ["Chorus “Ooh” (F4)", "held ~3.0 s", "2.2–2.5 s", "give these more time"],
    ["Endings: lights / night (E♭4)", "clipped, ~0.6 s", "held 1.5–2.6 s", "the main fix"],
    ["Time spent on D4 (not in the song's key)", "2.0 s", "12.8 s", "your E♭s drooping flat"],
    ["Time spent on E4 (not in the key)", "1.5 s", "8.1 s", "your Fs drooping flat"],
    ["The hook (“…walking by…”)", "F4–G4", "F3–G3", "you sang it an octave low"],
    ["Phrase endings that sag", "—", "56%", "breath running out"],
], [62 * mm, 30 * mm, 30 * mm, 46 * mm], center=(1, 2)))
A(Spacer(1, 6))
A(callout(
    "<b>The good news.</b> Your <b>Oohs are your steadiest notes</b> — the OO vowel "
    "holds pitch well for you. The chorus sits on E♭4–F4, which is inside your strongest "
    "mixed zone (A3–B4): this is not a range problem. And clipping the endings "
    "<b>also fixes your breath</b> — right now one chorus phrase runs 10 seconds "
    "without a breath, because there's no gap to breathe in.", tint=GOOD, edge=GOODE))

A(P("Where to listen in your recording", "h2"))
A(P("Times are in your actual recording file. Which word sits on which note is read "
    "from the repeating chorus pattern, so <b>check each one by ear</b>.", "p"))
A(grid([
    ["File time", "Word", "What happened"],
    ["1:28  and  2:24", "“night” (E♭4)", "held ~2.5 s — your two worst notes"],
    ["1:18 · 2:14 · 2:47", "“lights” (E♭4)", "held 1.5–2 s; original clips it"],
    ["2:18  and  2:51", "“touch” (F4)", "sagging down to E4"],
    ["1:11  and  2:07", "pre-chorus endings", "held ~1.5 s, sagging to D4"],
    ["2:33 – 2:41", "the hook", "sung an octave below the original"],
    ["~2:58 – 3:18", "the climax section", "mostly not sung (optional — see page 3)"],
], [40 * mm, 40 * mm, 88 * mm]))

# ── page 2: how to read a vowel run ──────────────────────────────────────────
A(PageBreak())
A(P("How to read a vowel run", "h2"))
A(P("<b>The idea in one sentence:</b> you can only hold a note on a <b>vowel</b> — "
    "consonants just start and stop it. So a vowel run is the line with the consonants "
    "taken out, leaving the vowels in order. <b>One syllable = one vowel = one sung note.</b>", "p"))

A(P("Worked example — one line, word by word", "h3"))
A(P("Take this chorus line from your sheet: <i>“I said, ooh, I'm blinded by the lights.”</i> "
    "Find the vowel in each syllable:", "p"))
A(grid([
    ["Word", "I", "said", "ooh", "I'm", "blinded", "by", "the", "lights"],
    ["Your code", "AY", "s-<b>EH</b>-d", "OO", "<b>AY</b>-m", "bl-<b>AY</b>-nd-<b>IH</b>-d",
     "b-<b>AY</b>", "th-<b>OE</b>", "l-<b>AY</b>-ts"],
    ["<b>Vowel kept</b>", "<b>AY</b>", "<b>EH</b>", "<b>OO</b>", "<b>AY</b>", "<b>AY · IH</b>",
     "<b>AY</b>", "<b>OE</b>", "<b>AY</b>"],
], [22 * mm, 13 * mm, 18 * mm, 15 * mm, 17 * mm, 28 * mm, 16 * mm, 18 * mm, 21 * mm],
    center=(1, 2, 3, 4, 5, 6, 7, 8)))
A(P("<i>blinded</i> has two syllables, so it gives two vowels.", "small"))
A(P("Strip the consonants, keep the vowels in order — <b>9 syllables, 9 vowels, 9 notes</b>:", "p"))
A(callout("<font name='DJ-M'>AY · EH · OO · AY · AY · IH · AY · OE · AY</font>"))
A(Spacer(1, 4))
A(P("Then add the timing marks from the original — hold the Ooh, clip the ending, breathe:", "p"))
A(callout(f"<font name='DJ-MB'>AY · EH · OO{HOLD} · AY · AY · IH · AY · OE · AY{CLIP} {BR}</font>"))

A(KeepTogether([
    P("How the vowels link — the three steps", "h3"),
    *steps([
        "<b>Say it.</b> Speak just the vowels in the line's rhythm: "
        "<i>ah – eh – oooo – ah – ah – ih – ah – uh – ah.</i>",
        "<b>Sing it, joined.</b> Sing those vowels on the real melody as <b>one unbroken "
        "sound</b>: the air never stops, each vowel melts straight into the next. That's "
        "what the dots mean — <b>link, don't stop</b>.",
        "<b>Put the words back.</b> Sing the real words, but make each consonant a quick "
        "flick in the middle of that same unbroken sound. If the line goes choppy or a note "
        "dips, go back to step 2.",
    ]),
    P("<b>Why it works:</b> your pitch and tone only exist on vowels. Practising with the "
      "consonants removed trains the part that actually carries the note — and you hear "
      "straight away if the line breaks or sags.", "p"),
]))

A(KeepTogether([
    P("The marks", "h3"),
    grid([
        ["Mark", "Meaning", "Mark", "Meaning"],
        [f"<font name='DJ-MB'>OO{HOLD}</font>", "hold — the full long note (~3 s)",
         f"<font name='DJ-MB'>{BR}</font>", "breathe here"],
        [f"<font name='DJ-MB'>AY{CLIP}</font>", "clip — short (under ~½ s), then stop",
         "no mark", "a passing vowel — keep it moving"],
    ], [22 * mm, 62 * mm, 22 * mm, 62 * mm]),
]))

A(KeepTogether([
    P("What each code sounds like", "h3"),
    grid([
        ["Code", "Sounds like", "Code", "Sounds like", "Code", "Sounds like"],
        ["AY", "“my” (ah → ee) *", "EH", "“bed”", "AO", "“law”"],
        ["EE", "“see”", "AE", "“cat”", "OE", "lazy “uh” in “sofa”"],
        ["IH", "“sit”", "AH", "“cup”", "OO", "“food”"],
        ["AW", "“now” (ah → oo) *", "UH", "“book”", "OW", "“go” (oh → oo) *"],
    ], [13 * mm, 43 * mm, 13 * mm, 43 * mm, 13 * mm, 43 * mm]),
    Spacer(1, 4),
    P("<b>* Two-part vowels.</b> AY, AW and OW are two sounds glued together: hold the "
      "<b>first</b>, close to the second only at the very last moment. <b>One correction "
      "to your sheet:</b> your AY covers two sounds. In <b>I / lights / night / time</b> it "
      "starts on “ah” (as in “my”); in <b>hey / say / baby / maybe</b> it starts on “eh” "
      "(as in “day”).", "p"),
]))

# ── page 3: the vowel runs ───────────────────────────────────────────────────
A(KeepTogether([
    P("The chorus — your main fix", "h2"),
    P("Learn the <b>skeleton</b> first: just the held notes, in order. This is the shape of "
      "the whole chorus.", "p"),
    callout(f"<font name='DJ-MB' size='12'>OO{HOLD} → AY{CLIP} → AH{CLIP} → OO{HOLD} → AY{CLIP} → AH{CLIP}</font><br/>"
            "<font size='8.5' color='#4b5563'>F4 (long) · E♭4 (short) · F4 (short) · "
            "F4 (long) · E♭4 (short) · F4 (short)</font>"),
    Spacer(1, 6),
    grid([
        ["Line ends…", "Vowel run"],
        ["…the lights", f"AY · EH · <b>OO{HOLD}</b> · AY · AY · IH · AY · OE · <b>AY{CLIP}</b> {BR}"],
        ["…your touch", f"OW · AY · AE · EE · OE · IH · AY · EE · AO · <b>AH{CLIP}</b> {BR}"],
        ["…in the night", f"AY · EH · <b>OO{HOLD}</b> · AY · AW · IH · IH · OE · <b>AY{CLIP}</b> {BR}"],
        ["…one I trust", f"OW · EH · AY · AY · IH · AO · OE · AH · AY · <b>AH{CLIP}</b> {BR}"],
    ], [32 * mm, 136 * mm], run_cols=(1,)),
]))

A(KeepTogether([
    P("Three rules for the chorus", "h3"),
    *steps([
        "<b>AY is “ah”, then “ee” at the last instant.</b> On the short endings this is "
        "quick — just never sit on the “ee”: it spreads and pulls you off the note.",
        "<b>Stop the note with the final consonant.</b> Every chorus line ends on a stop: "
        "ligh<b>TS</b>, nigh<b>T</b>, tou<b>CH</b>, trus<b>T</b>. Land it on the beat and "
        "the note ends clean — that's where the original's crisp cut-offs come from.",
        "<b>Keep the “uh” in touch and trust tall.</b> Jaw dropped, space up, so it "
        "doesn't collapse flat — your “touch” is drooping to E4.",
    ]),
    P("<b>On the Ooh:</b> it isn't dead still in the original — it moves about two "
      "semitones across the hold. Listen to how he shapes it and copy that; don't add "
      "your own slide.", "p"),
]))

A(KeepTogether([
    P("Pre-chorus — clip the endings", "h2"),
    P("In the original these are short. You held them about 1.5 s and they sagged to D4.", "p"),
    grid([
        ["Line ends…", "Vowel run"],
        ["…empty (oh)", f"IH · IH · EE · OW · AE · EH · EE · <b>OW{CLIP}</b> {BR}"],
        ["…judge me (oh)", f"OW · AH · OE · AW · OE · AH · EE · <b>OW{CLIP}</b> {BR}"],
        ["…when you're gone", f"AY · AE · EE · IH · EE · EH · AO · <b>AO{CLIP}</b> {BR}"],
    ], [32 * mm, 136 * mm], run_cols=(1,)),
    P("Second time through, the first line starts on OE instead of IH.", "small"),
]))

A(KeepTogether([
    P("The hook — sing it up the octave", "h2"),
    P("The original sits around <b>F4–G4</b> — inside your best zone. Dropping it to "
      "F3–G3 takes the energy out of the section.", "p"),
    grid([
        ["Line ends…", "Vowel run"],
        ["…let you know", "AY · AH · AO · IH · AY · OE · EH · OO · OW"],
        ["…on the phone", "AY · UH · EH · OE · AY · IH · AO · OE · OW"],
        ["…this time (ooh)", "IH · EH · OE · EH · OO · OW · IH · AY · (OO)"],
    ], [32 * mm, 136 * mm], run_cols=(1,)),
]))

A(KeepTogether([
    P("Optional — the climax after the hook", "h3"),
    P("Over the “hey, hey, hey” section the original has a long held <b>G4</b> (about "
      "3.8 s) and high falsetto flips (D♯5–G♯5). Your take goes mostly quiet there — "
      "that's why you spent 2.4 s on G4 against his 9.5 s. Leave this until the chorus "
      "is solid.", "p"),
]))

# ── page 4: the session ──────────────────────────────────────────────────────
A(KeepTogether([
    P("The 20-minute session", "h2"),
    P("After your normal warm-up. Five or six days a week.", "p"),
    grid([
        ["#", "Drill", "Min", "Moves this number"],
        ["1", "Chorus skeleton on vowels", "5", "line-end holds 1.5–2.6 s → under 0.7 s"],
        ["2", "Clip with the consonant", "5", "sagging phrase endings 56% → well under"],
        ["3", "The Ooh on the water jar", "5", "Oohs 2.2–2.5 s → a steady 3 s"],
        ["4", "Hook up the octave", "3", "hook F3–G3 → F4–G4"],
        ["5", "Full chorus + record", "2", "time on D4 / E4: 12.8 / 8.1 s → toward 2.0 / 1.5 s"],
    ], [9 * mm, 52 * mm, 13 * mm, 94 * mm], center=(0, 2)),
]))

DRILLS = [
    ("1 — Chorus skeleton on vowels · 5 min",
     ["Play the original quietly.",
      "Sing only the skeleton from page 3, at tempo: long OO, short AY, short AH — twice.",
      "Then sing all four chorus vowel runs, joined (step 2 of “How the vowels link”)."],
     "the Oohs feel long and the endings feel almost too short, like you're dropping "
     "them. That's correct."),
    ("2 — Clip with the consonant · 5 min",
     ["Speak the chorus words in rhythm. Hit the T, TS and CH exactly on the beat.",
      "Sing it the same way — the consonant is your off-switch.",
      "Breathe in every gap the clip gives you (the ✓ marks)."],
     "there's a clear gap of silence after each line, and you breathe in it without "
     "trying."),
    ("3 — The Ooh on the water jar · 5 min",
     ["Water-jar rig, tube a few cm under.",
      "Hold F4 for 3 seconds through the tube — five times.",
      "Then sing OO the same way without the tube, then the chorus “Ooh”s in the song."],
     "the pitch feels locked and the sound doesn't thin out at the end of the hold."),
    ("4 — Hook up the octave · 3 min",
     ["Sing the three hook vowel runs at F4–G4 in a light mix — not pushed.",
      "Then the words."],
     "it feels speech-like and easy, not belted."),
    ("5 — Full chorus + record · 2 min",
     ["Sing a full chorus with the breath marks.",
      "Record it on your phone — the same way as take 1, so the takes compare."],
     "you finish the chorus with air left, not gasping."),
]
for title, how, check in DRILLS:
    A(KeepTogether([
        P(title, "h3"),
        P(" → ".join(how), "li"),
        P(f"<b>✓ Doing it right:</b> {check}", "li"),
    ]))

A(Spacer(1, 6))
A(callout(
    "<b>Don't watch a tuner while you sing.</b> You sing in tune when you're not chasing "
    "it. These drills fix the timing and the vowels; the pitch follows. Check afterwards "
    "with a new recorded take."))
A(Spacer(1, 4))
A(KeepTogether([
    P("What “better” looks like on the next take", "h3"),
    *bullets([
        "Time on <b>D4</b> and <b>E4</b> drops toward the original's 2.0 s and 1.5 s "
        "(from your 12.8 s and 8.1 s).",
        "Line endings come in <b>under about 0.7 s</b>.",
        "Sagging phrase endings fall well below <b>56%</b>.",
        "The hook sits at <b>F4–G4</b>.",
    ]),
    Spacer(1, 6),
    callout("<b>If the minutes happen, the next report reads differently. "
            "If they don't, it won't.</b>"),
]))

doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=21 * mm, rightMargin=21 * mm,
                      topMargin=21 * mm, bottomMargin=21 * mm,
                      title="Blinding Lights — Practice Sheet", author="VOX//SUITE")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=furniture)])
doc.build(story)
print("wrote", OUT)
