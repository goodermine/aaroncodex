#!/usr/bin/env python3
"""Aaron's 20-minute daily drill programme as a printable PDF.

House style from docs/handoffs/SINGER_REPORT_STANDARD.md: VOX//SUITE identity,
Aaron's blue accent, a second deeper accent for the table that carries the real
work, plain-words callouts, DejaVu throughout (required for the ♯ / ¢ glyphs).
KeepTogether on every block so nothing orphans across a page break.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, KeepTogether)

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DJ", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DJ-B", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DJ-M", F + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DJ", normal="DJ", bold="DJ-B")

BLUE = colors.HexColor("#1d4ed8")      # Aaron's accent
DEEP = colors.HexColor("#0f2a6b")      # the serious table
INK = colors.HexColor("#111827")
GREY = colors.HexColor("#4b5563")
RULE = colors.HexColor("#d1d5db")
TINT = colors.HexColor("#eff4ff")
WARN = colors.HexColor("#fdf2f2")
WARNE = colors.HexColor("#b91c1c")

OUT = "/home/user/aaroncodex/Aaron-Daily-Drill-Programme.pdf"

S = dict(
    h1=ParagraphStyle("h1", fontName="DJ-B", fontSize=21, leading=25, textColor=BLUE,
                      spaceAfter=2),
    sub=ParagraphStyle("sub", fontName="DJ", fontSize=10.5, leading=14, textColor=GREY,
                       spaceAfter=10),
    h2=ParagraphStyle("h2", fontName="DJ-B", fontSize=13.5, leading=17, textColor=DEEP,
                      spaceBefore=13, spaceAfter=5),
    h3=ParagraphStyle("h3", fontName="DJ-B", fontSize=11, leading=14.5, textColor=INK,
                      spaceBefore=9, spaceAfter=3),
    p=ParagraphStyle("p", fontName="DJ", fontSize=9.4, leading=13.4, textColor=INK,
                     spaceAfter=5, alignment=TA_LEFT),
    li=ParagraphStyle("li", fontName="DJ", fontSize=9.4, leading=13.4, textColor=INK,
                      leftIndent=9, bulletIndent=1, spaceAfter=2.5),
    note=ParagraphStyle("note", fontName="DJ", fontSize=9.1, leading=13, textColor=INK),
    small=ParagraphStyle("small", fontName="DJ", fontSize=8.2, leading=11.5, textColor=GREY,
                         spaceAfter=4),
)


def P(t, s="p"):
    return Paragraph(t, S[s])


def bullets(items):
    return [Paragraph(f"• {i}", S["li"]) for i in items]


def callout(html, tint=TINT, edge=BLUE):
    t = Table([[Paragraph(html, S["note"])]], colWidths=[168 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), tint),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, edge),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def grid(data, widths, header_bg=DEEP, align_right=(), font_size=8.8):
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    st = [
        ("FONT", (0, 0), (-1, 0), "DJ-B", font_size),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("FONT", (0, 1), (-1, -1), "DJ", font_size),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]
    for c in align_right:
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
                           "AARON — THE 20-MINUTE DAILY DRILL PROGRAMME")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(21 * mm, A4[1] - 14.5 * mm, A4[0] - 21 * mm, A4[1] - 14.5 * mm)
    canvas.line(21 * mm, 15 * mm, A4[0] - 21 * mm, 15 * mm)
    canvas.setFont("DJ", 7)
    canvas.drawString(21 * mm, 11 * mm,
                      "Built from 81 measured takes · rubric v5 · calibrated to 50 "
                      "professional reference vocals")
    canvas.drawRightString(A4[0] - 21 * mm, 11 * mm, f"{doc.page}")
    canvas.restoreState()


story = []
A = story.append

# ── header ───────────────────────────────────────────────────────────────────
A(P("The 20-Minute Daily Drill Programme", "h1"))
A(P("Aaron Ellis · built from 81 measured takes, June–August 2026 · "
    "every drill here exists because a number says it should", "sub"))

A(callout(
    "<b>Nothing in this programme is here because it is traditional, and nothing "
    "targets something you already do well.</b> Your pitch centring measures at "
    "professional level and gets no minutes at all. The drills come from the "
    "elite-coaching synthesis in your knowledge base; the <i>choice</i> of which "
    "drills comes from your own measurements."))
A(Spacer(1, 9))

# ── where you are ────────────────────────────────────────────────────────────
A(P("Where you actually are", "h2"))
A(grid([
    ["Measure", "You", "Professional", "Verdict"],
    ["Clean note entries", "23.7%  (16th pct)", "median 33.2%", "worst gap"],
    ["Entries scooped into", "47.9%  from −98.8¢", "median 41.6%", "rate is near normal"],
    ["Entries overshot", "29.3%", "median 24.0%", "the other half of the miss"],
    ["Phrase endings that sag", "51.5%", "Farnham 28.6–29.7%", "second worst"],
    ["Drift inside a held note", "39.8¢", "Farnham 15.1–24.0¢", "what listeners hear"],
    ["Median phrase length", "2.7 s", "You're the Voice 5.57 s", "half the length"],
    ["Deviation from the note you land on", "22.5¢", "20–25¢", "already reference level"],
], [56 * mm, 34 * mm, 38 * mm, 40 * mm], align_right=(1, 2)))
A(Spacer(1, 6))
A(callout(
    "<b>Your landing is fine. Your approach is not.</b> You arrive dead centre on "
    "the note — you just slide up into 47.9% of them from nearly a semitone below, "
    "and overshoot another 29.3%. Only <b>23.7%</b> start clean, against a "
    "professional median of 33.2%. You miss the centre in <i>both</i> directions.<br/><br/>"
    "For contrast: Farnham on <i>Pressure Down</i> scoops from −82.5¢ — barely "
    "shallower than you. He just does it <b>three times less often, and by choice.</b>"))
A(Spacer(1, 6))
A(callout(
    "<b>You live on your passaggio.</b> Most-used note <b>E4</b>. Working tessitura "
    "<b>A3–F♯4</b>. Passaggio estimates cluster <b>C♯4–F4</b>. The note you sing more "
    "than any other is the note your voice changes gear on — which is why full nights "
    "tax you, and why passaggio work is maintenance rather than an extra."))

# ── the programme ────────────────────────────────────────────────────────────
A(P("The programme — 20 minutes, 5–6 days a week", "h2"))
A(P("The seventh day is not laziness. It is when the adaptation lands.", "p"))
A(grid([
    ["#", "Block", "Min", "Moves this number"],
    ["0", "SOVT wake-up", "3", "prepares everything, costs nothing"],
    ["1", "Onset planting", "5", "clean 23.7% → 33%+"],
    ["2", "Sustain → messa di voce", "3", "drift 39.8¢ → under 25¢"],
    ["3", "Passaggio, vowels & range", "4", "strain at F4; M2 in songs"],
    ["4", "Twang", "2", "carrying power without volume"],
    ["5", "Song application", "1", "phrase 2.7 s → 4 s+"],
    ["6", "Cool-down", "2", "tomorrow's freshness"],
], [9 * mm, 55 * mm, 13 * mm, 91 * mm], align_right=(0, 2)))
A(Spacer(1, 5))
A(P("<b>15-minute version:</b> blocks 0, 1, 2 and 6. Never cut block 0, never cut "
    "the cool-down.", "p"))
A(Spacer(1, 4))
A(callout(
    "<b>The Farinelli breath comes OFF the clock — that is a promotion.</b> It is "
    "completely silent, so it costs your folds nothing, which means rationing it to "
    "one slot was the wrong call. Do it <b>three or four short goes a day</b>: "
    "driving, on the couch, before sleep, waiting for the kettle.<br/><br/>"
    "Inhale 4 — suspend 4 — exhale 4, six rounds, adding a count to the easiest "
    "phase each week. Then one steady hiss on “sss”, timed; <b>target 25 seconds</b> "
    "with no wobble and no collapse at the end.<br/><br/>"
    "<b>The whole exercise is the suspension, and the classic error is doing it in "
    "the wrong place.</b> The hold is your ribs staying wide — not your throat "
    "closing. Test: start a quiet hum straight out of the suspension. A click, a "
    "catch or a little push means you held it at the glottis."))

# ── blocks ───────────────────────────────────────────────────────────────────
A(P("The blocks", "h2"))

A(KeepTogether([
    P("Block 0 — SOVT wake-up  ·  3 min", "h3"),
    P("Always first. Always. Semi-occluded work gets the folds vibrating at a "
      "fraction of the collision force, so it prepares the instrument without "
      "spending it.", "p"),
    *bullets(["<b>Water jar</b>, tube 2–4 cm under, gentle sirens low→high→low — 90 seconds.",
              "<b>Straw or lip-trill glides</b>, five slow passes across your comfortable "
              "range — 90 seconds."]),
]))

A(KeepTogether([
    P("Block 1 — Onset planting  ·  5 min  ·  the biggest gap", "h3"),
    P("<b>1a. Three-onset contrast (2 min).</b> One comfortable pitch, say D4. Sing "
      "“ah” three ways and <i>feel</i> the difference — breathy (“haaah”, air first), "
      "hard (a small glottal click), and balanced (air and tone together, no h, no "
      "click). Five rounds. You cannot fix an onset you cannot feel.", "p"),
    P("<b>1b. Silent-target planting (2 min).</b> Play a note. <b>Stop the sound.</b> "
      "Hear it in your head. Breathe. Land it — no slide, straight onto the centre. "
      "Hold two seconds. Ten different pitches.", "p"),
    P("<b>1c. Deliberate contrast (1 min).</b> One phrase, sung scooping on purpose, "
      "then clean. Alternate three times. Contrast is how ears learn — you cannot "
      "currently hear your own scoops because they are your normal.", "p"),
    callout("<b>See it, land it, stay on it.</b> Scooping is what a voice does when it "
            "is <i>searching</i> for the note. Take away the search and you take away "
            "the scoop."),
]))

A(KeepTogether([
    P("Block 2 — Sustain, then messa di voce  ·  3 min", "h3"),
    P("<b>2a. Straight tone against a drone (2 min).</b> Play a drone — tuner app, "
      "keyboard, anything. Sustain against it: straight, no vibrato, no swell, 8–10 "
      "seconds. Five notes. Drift is nearly impossible to hear alone and instantly "
      "obvious against a reference pitch.", "p"),
    P("<b>2b. Messa di voce (1 min).</b> Same pitch, soft → full → soft on one breath. "
      "<b>Two notes only.</b> Better done twice properly than five times badly.", "p"),
    callout("<b>Steady first, shape second.</b> If the straight tone is not solid, skip "
            "the messa di voce today — you would be practising drift with volume added "
            "on top. Pushing the crescendo is the trap, and under load your measured "
            "pattern is to default to power. <b>The swell has to be earned.</b>",
            WARN, WARNE),
]))

A(KeepTogether([
    P("Block 3 — Passaggio, vowels & range  ·  4 min", "h3"),
    *bullets([
        "<b>Straw/tube glides through C♯4–F4</b> — slowly, listening for any audible "
        "gear change.",
        "<b>Descending 5-tone from above the passaggio</b> on “oo” or “ee”, coming "
        "<i>down</i> through C♯4–F4. Descending brings M2 down and blends it.",
    ]),
    P("<b>Vowel modification (aggiustamento) — 90 seconds.</b> Sing the same word up a "
      "scale through E4 and above, letting the vowel migrate as the pitch rises:", "p"),
    grid([["Vowel", "As you climb, move it toward", "Cue"],
          ["“ee”  /i/", "more open", "ee → ih"],
          ["“oo”  /u/", "more open", "oo → uh"],
          ["“ah”  /a/", "rounder", "ah → aw"]],
         [26 * mm, 62 * mm, 30 * mm], header_bg=BLUE),
    Spacer(1, 4),
    callout("<b>The tell is unmistakable: the note suddenly rings and gets easier.</b> "
            "If you are muscling something at F4, the vowel is the first thing to "
            "change — before the volume, before the support.<br/><br/>"
            "<b>Range grows from coordination, not force.</b> Extend at the top of a "
            "glide, never on a held note, a semitone at a time. A note you can only "
            "reach by pushing is not a range note, it is a risk."),
]))

A(KeepTogether([
    P("Block 4 — Twang  ·  2 min  ·  your alternative to volume", "h3"),
    P("Slide on <b>“ng”</b> (the end of <i>sing</i>) across the mid-range, then open it "
      "into a bratty, slightly nasal <b>“nay-nay-nay”</b> on a 5-tone scale. Keep it "
      "<b>bright and buzzy, never loud.</b> The tell is a focused ring you can feel in "
      "the front of your face.", "p"),
    callout("<b>Read this the night before a competition round.</b> Your measured "
            "failure mode under pressure — confirmed by two independent systems and by "
            "your own diagnosis of the semi-final you lost — is that you reach for "
            "<b>power</b>. Twang is the thing to reach for instead: louder in the "
            "frequencies a room actually hears, without being louder at the folds."
            "<br/><br/>“One gear in reserve” tells you what <i>not</i> to do. "
            "<b>This is the thing to do.</b>"),
]))

A(KeepTogether([
    P("Block 5 — Song application  ·  1 min", "h3"),
    P("One phrase. Not a whole song. Apply whatever today's focus was, then the "
      "phrase-length ladder — yours is <b>2.7 s</b> median, <i>You're the Voice</i> is "
      "<b>5.57 s</b>. Sing one long phrase on a single breath and add a beat when it "
      "is comfortable.", "p"),
    P("<b>“Last word loud”</b> — carry the intensity all the way to the final "
      "syllable instead of letting it trail. That is the sag, in one instruction.", "p"),
]))

A(KeepTogether([
    P("Block 6 — Cool-down  ·  2 min", "h3"),
    P("Gentle SOVT — hum or straw, quiet — then <b>descending glides only</b>, from "
      "comfortable down to the bottom, five or six passes. Nothing loud, nothing high. "
      "Two minutes returns the voice to neutral and reduces the fatigue you carry into "
      "tomorrow. <b>Do it after gigs too — especially after gigs.</b>", "p"),
]))

# ── phases ───────────────────────────────────────────────────────────────────
A(P("Two phases, and the second matters more than it looks", "h2"))
A(P("The blocks above are <b>blocked practice</b> — one coordination, repeated. That "
    "is the right way to <i>acquire</i> a skill and the wrong way to <i>keep</i> it "
    "under pressure. Motor-learning research is consistent and slightly "
    "counter-intuitive: <b>random and variable practice produce better retention and "
    "transfer, even though blocked practice looks better while you are doing it.</b> "
    "That distinction decides your December.", "p"))

A(KeepTogether([
    P("Phase 1 — blocked  ·  now → mid-September", "h3"),
    grid([["Day", "Heavy block"],
          ["Mon", "Onsets (1)"],
          ["Tue", "Sustain / messa di voce (2)"],
          ["Wed", "Light voice day — SOVT, twang, cool-down only"],
          ["Thu", "Onsets (1)"],
          ["Fri", "Passaggio & vowels (3)"],
          ["Sat", "Song application (5), or a gig"],
          ["Sun", "Off, or recovery version"]],
         [18 * mm, 100 * mm], header_bg=BLUE),
]))

A(KeepTogether([
    P("Phase 2 — variable  ·  mid-September → the competition", "h3"),
    P("Same minutes, same drills, deliberately disordered:", "p"),
    *bullets([
        "<b>Shuffle the order.</b> Do not run 0→6. Mix the blocks so you never know "
        "what is next — that is the whole point.",
        "<b>Interleave instead of blocking.</b> Rather than five straight minutes of "
        "onsets: onsets → sustain → onsets → passaggio, a minute at a time.",
        "<b>Vary the context.</b> Standing. Moving. Holding a mic. At performance "
        "volume. In shoes you would gig in.",
        "<b>Grow song application</b> — it becomes the biggest block, run under "
        "performance conditions with the backing track.",
    ]),
    callout("<b>Phase 2 will feel worse than Phase 1. That is the expected result, not "
            "a problem.</b> If you do not know that in advance, you will assume you "
            "have gone backwards and revert to the version that felt better.",
            WARN, WARNE),
]))

A(KeepTogether([
    P("Microphone technique — Phase 2, and it is not optional", "h3"),
    P("You have already lost one take to going too loud in a hot room. Concrete "
      "distances, from Shure's engineering guidance:", "p"),
    grid([["Line type", "Distance from the mic"],
          ["Quiet, intimate", "1 inch or less"],
          ["Normal", "1.5 – 3 inches"],
          ["Belting / money notes", "6 inches to arm's length"]],
         [46 * mm, 60 * mm], header_bg=BLUE),
    Spacer(1, 4),
    P("Turn slightly <b>off-axis</b> on plosives and on your loudest high notes. "
      "Working the mic is the difference between a room hearing dynamics and a room "
      "hearing distortion — and it lets you sing the big note at a sane level.", "p"),
]))

# ── rules ────────────────────────────────────────────────────────────────────
A(KeepTogether([
    P("The rules that override everything", "h2"),
    callout(
    "<b>1. Never train through hoarseness.</b> Mild post-load irritation that clears "
    "overnight is fatigue. Hoarseness still there after a full rest day is a stop sign."
    "<br/><b>2. Pain is always a stop.</b> Singing should feel free. It should never hurt."
    "<br/><b>3. Still hoarse a week later</b>, or top notes gone and not returning — "
    "that is a laryngologist, ideally one who scopes, not a wait-and-see."
    "<br/><b>4. Whisper is worse than quiet speech.</b> On a rest day, speak softly."
    "<br/><b>5. You cannot train two systems to failure at once.</b> You are mid "
    "rib-loading."
    "<br/><b>6. Fresh beats drilled</b>, especially inside nine weeks of a competition.",
    WARN, WARNE)]))
A(Spacer(1, 5))
A(P("<b>Recovery version</b> (post-gig, tired, mildly irritated): block 0, the "
    "Farinelli breath, block 6. Roughly six minutes, almost no cost to the folds, and "
    "it keeps the streak without the risk. <b>Deload every fourth week</b> — halve "
    "everything. Adaptation lands during the easy week, not the hard one.", "p"))

# ── tracking ─────────────────────────────────────────────────────────────────
A(KeepTogether([
    P("How you will know it is working", "h2"),
    P("Do not judge this by feel. Record <b>one take of Pressure Down or Reasons a "
      "month</b>, same conditions, and read four numbers:", "p"),
    grid([
    ["Number", "Today", "3-month target", "Where"],
    ["Clean entries", "23.7%  (16th pct)", "33%+  (50th)", "ENTRY ACCURACY"],
    ["Phrase endings sagging", "51.5%", "under 35%", "METRICS · breath"],
    ["Intra-note drift", "39.8¢", "under 25¢", "METRICS · intonation"],
    ["Median phrase length", "2.7 s", "4 s+", "METRICS · dynamics"],
], [46 * mm, 34 * mm, 32 * mm, 56 * mm], align_right=(1, 2))]))
A(Spacer(1, 6))
A(callout(
    "<b>Do not expect the overall /10 to move much, even if all four improve.</b> "
    "Phrase control and breath support carry 0.10 each, and onsets are not scored at "
    "all. The point of this programme is to sound better to a room, not to move a "
    "number — and the blind listening test proved your ear registers these things "
    "even when the score does not.<br/><br/>"
    "<b>The benchmark that should change the plan:</b> no movement on a coordination "
    "after <b>three to four months</b> of consistent work means the approach is wrong, "
    "not that you need more of it. Change the drill or get a second opinion."))

A(Spacer(1, 8))
A(P("Sources — the gaps targeted here are measured from your own archive (81 active "
    "takes, rubric v5, calibration 1d3e2991f144). The drills chosen to close them come "
    "from “Inside the Elite Contemporary Vocal Lesson” in the vocal knowledge base. "
    "No number in this document was rounded toward the flattering side.", "small"))

doc = BaseDocTemplate(OUT, pagesize=A4,
                      leftMargin=21 * mm, rightMargin=21 * mm,
                      topMargin=19 * mm, bottomMargin=19 * mm,
                      title="Aaron — The 20-Minute Daily Drill Programme",
                      author="VOX//SUITE")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=furniture)])
doc.build(story)
print("wrote", OUT)
