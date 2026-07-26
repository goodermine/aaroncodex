"""Build Aaron's breath-support practice sheet from the engine's exercise library.

Exercise text is copied verbatim from knowledge/prescription_map.json — the same
library the analysis prescribes from, so the sheet can't drift from the engine.
"""
import json, re, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, KeepTogether, HRFlowable, Image, PageBreak)

ENG = "/home/user/aaroncodex/voxanalysis/vox-analysis/engine"
OUT = "/home/user/aaroncodex/docs/practice/pressure-down-breath-support.pdf"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

lib = json.load(open(f"{ENG}/knowledge/prescription_map.json"))
cat = lib["categories"]["breath_support"]
analysis = json.load(open("/home/user/aaroncodex/voxanalysis/archive/scratch-analyses/"
                          "2026-07-25-aaron-pressure-down-captain-cook-tavern-take-001_analysis.json"))
pres = analysis["prescriptions"]["primary"]

def fields(detail):
    """Split a library entry into its labelled bullets."""
    out = {}
    for line in detail.split("\n"):
        m = re.match(r"-\s*([^:]+):\s*(.+)", line.strip())
        if m:
            k = m.group(1).split("(")[0].strip().lower()
            out[k] = m.group(2).strip()
    return out

INK = colors.HexColor("#12212b")
MUT = colors.HexColor("#5b6b78")
ACC = colors.HexColor("#0b6a86")
WARN = colors.HexColor("#8a5a00")
RULE = colors.HexColor("#c9d6de")
BAND = colors.HexColor("#eef5f8")

S = {
    "title": ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=INK),
    "sub": ParagraphStyle("s", fontName="Helvetica", fontSize=10, leading=14, textColor=MUT),
    "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=ACC,
                        spaceBefore=2, spaceAfter=3),
    "lbl": ParagraphStyle("l", fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=MUT),
    "body": ParagraphStyle("b", fontName="Helvetica", fontSize=9.7, leading=13.4, textColor=INK,
                           alignment=TA_LEFT),
    "warn": ParagraphStyle("w", fontName="Helvetica-Oblique", fontSize=8.8, leading=12, textColor=WARN),
    "sec": ParagraphStyle("sec", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=INK,
                          spaceBefore=8, spaceAfter=5),
}

doc = SimpleDocTemplate(OUT, pagesize=A4, topMargin=15 * mm, bottomMargin=14 * mm,
                        leftMargin=15 * mm, rightMargin=15 * mm,
                        title="Breath Support Practice Sheet - Aaron",
                        author="VOX Suite")
st = []

st.append(Paragraph("Breath Support &mdash; Practice Sheet", S["title"]))
st.append(Paragraph(
    "Aaron &middot; built from the measured analysis of <b>Pressure Down</b> (Captain Cook Tavern, 25 Jul 2026). "
    "All exercise text is copied verbatim from the engine's prescription library; the one shaded box at the end is a coaching note and is labelled as such.", S["sub"]))
st.append(Spacer(1, 7))
st.append(HRFlowable(width="100%", color=RULE, thickness=0.9))
st.append(Spacer(1, 8))

# ---- why ----
why = [
    ["Primary limiter", "<b>Breath support</b> &mdash; severity %.0f/100" % pres["severity_0_to_100"]],
    ["Evidence", "49% of phrase endings sag (25 of 51 phrases)"],
    ["What it sounds like", "Notes arrive on pitch, hold about a second, then slide down. Sliding, not breaking."],
    ["Where it bites", "Worst from 2:44 onward &mdash; 2:44 (-1.9 semitones), 3:01 (-2.2), 3:25 (-0.8). "
                       "Early in the song you slide <i>up</i> into notes instead."],
    ["Your cue", "<b>&ldquo;%s&rdquo;</b>" % pres["next_take_cue"]],
]
t = Table([[Paragraph(a, S["lbl"]), Paragraph(b, S["body"])] for a, b in why],
          colWidths=[32 * mm, 143 * mm])
t.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("BACKGROUND", (0, 0), (-1, -1), BAND),
    ("BOX", (0, 0), (-1, -1), 0.7, RULE),
    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
    ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
st.append(t)
st.append(Spacer(1, 10))

# ---- the evidence, as pictures ----
IMG = os.path.join(os.path.dirname(OUT), "img")
def figure(fname, caption, width_mm=175):
    path = os.path.join(IMG, fname)
    if not os.path.isfile(path):
        return []
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    img = Image(path, width=width_mm * mm, height=width_mm * h / w * mm)
    return [img, Spacer(1, 3), Paragraph(caption, S["sub"]), Spacer(1, 9)]

st.append(Paragraph("Where it goes wrong", S["sec"]))
st.extend(figure("trouble-map.png",
    "Every red band is a moment the pitch left the note. The orange dashed line is the passaggio "
    "(C#4) &mdash; where the voice changes gear. Five of the eight sit on D4/C#4, right on it, and "
    "three land on the chorus line &ldquo;take the pressure down&rdquo;."))
st.extend(figure("slide-shapes.png",
    "The shape of each slide, with pitch-tracker errors removed. Amber = sliding <i>up</i> into the "
    "note (early in the song). Red = sagging off it (from 2:44 on). Green band = within half a "
    "semitone, which is fine. The split by time in the song is the stamina story."))
st.append(PageBreak())

# ---- session ----
st.append(Paragraph("A 10-minute session", S["sec"]))
sess = [["1", "Straw Phonation in Water", "2 min", "warm up &mdash; and watch the bubbles stay even"],
        ["2", "Rib Cage Stationary Drill", "3 min", "names your exact fault: ribs must not collapse"],
        ["3", "Sibilant Hiss", "2 min", "closest to singing &mdash; air actually flowing"],
        ["4", "The 3:01 phrase", "3 min", "one phrase only, ribs staying wide"]]
t2 = Table([[Paragraph(c, S["body"]) for c in r] for r in sess],
           colWidths=[8 * mm, 52 * mm, 18 * mm, 97 * mm])
t2.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
    ("BOX", (0, 0), (-1, -1), 0.7, RULE),
    ("LEFTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
st.append(t2)
st.append(Spacer(1, 4))
st.append(Paragraph(
    "Every exercise in this library carries the same transfer rule: <b>apply the sensation to one short "
    "phrase only &mdash; do not run the whole song until the cue holds.</b>", S["body"]))
st.append(Spacer(1, 10))

# ---- the eight ----
st.append(Paragraph("The eight breath-support exercises", S["sec"]))
ORDER_NOTE = {
    "The Farinelli Maneuver": "The one your analysis prescribed first.",
    "Rib Cage Stationary Drill": "Most direct hit on your fault.",
    "The Sibilant Hiss": "Closest to real singing.",
}
for i, ex in enumerate(cat["exercises"], 1):
    f = fields(ex["detail"])
    rows = []
    for label, key in (("Do this", "how to do it"), ("Should feel", "how it should feel"),
                       ("Pass / fail", "pass/fail metric")):
        if f.get(key):
            rows.append([Paragraph(label, S["lbl"]), Paragraph(f[key], S["body"])])
    blk = [Paragraph(f"{i}. {ex['name']}", S["h"])]
    tag = []
    if f.get("pedagogical target"): tag.append("Target: " + f["pedagogical target"])
    if ORDER_NOTE.get(ex["name"]): tag.append("<b>" + ORDER_NOTE[ex["name"]] + "</b>")
    if tag: blk.append(Paragraph(" &middot; ".join(tag), S["sub"]))
    blk.append(Spacer(1, 3))
    tb = Table(rows, colWidths=[24 * mm, 151 * mm])
    tb.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    blk.append(tb)
    if f.get("common failure / safety note"):
        blk.append(Spacer(1, 2))
        note = f["common failure / safety note"]
        note = note[0].upper() + note[1:]
        blk.append(Paragraph(note, S["warn"]))
    blk.append(Spacer(1, 3))
    blk.append(HRFlowable(width="100%", color=RULE, thickness=0.5))
    blk.append(Spacer(1, 6))
    st.append(KeepTogether(blk))

# ---- straw phonation: from a different category, plus a flagged addition ----
straw = next(e for e in lib["categories"]["warmup_reset"]["exercises"]
             if e["name"] == "Straw Phonation in Water")
fw = fields(straw["detail"])
blk = [Paragraph("Warm-up &mdash; Straw Phonation in Water", S["sec"]),
       Paragraph("Target: %s &middot; <b>Not a breath-support exercise</b> &mdash; it sits in the "
                 "warm-up/reset set. Included because it is the only drill here where you make sound "
                 "while training airflow, and the bubbles show your fault directly."
                 % fw.get("pedagogical target", "Water-Resistance Massage"), S["sub"]),
       Spacer(1, 3)]
rows = [[Paragraph(l, S["lbl"]), Paragraph(fw[k], S["body"])]
        for l, k in (("Do this", "how to do it"), ("Should feel", "how it should feel"),
                     ("Pass / fail", "pass/fail metric")) if fw.get(k)]
tb = Table(rows, colWidths=[24 * mm, 151 * mm])
tb.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
blk.append(tb)
if fw.get("common failure / safety note"):
    n = fw["common failure / safety note"]
    blk.append(Spacer(1, 2)); blk.append(Paragraph(n[0].upper() + n[1:], S["warn"]))
st.append(KeepTogether(blk))
st.append(Spacer(1, 5))

# Everything above is library text. This box is not — label it as such.
add = [Paragraph("How to progress it &mdash; <b>coaching note, NOT from the library</b>", S["lbl"]),
       Spacer(1, 3),
       Paragraph("Blow for as long as you can <b>while the bubbles stay even</b>, keeping the ribs wide, "
                 "and push that a little further each session.", S["body"]),
       Spacer(1, 3),
       Paragraph("<b>Measure steady seconds, not total seconds.</b> The moment the bubbles go uneven or "
                 "you feel the throat take over, the rep is finished &mdash; stop there. Chasing maximum "
                 "duration means squeezing out the last of the air with collapsing ribs, which is exactly "
                 "the fault you are trying to remove: you would be rehearsing the sag. Steady-bubble "
                 "seconds is a real progressive measure of the thing that is actually broken, and unlike "
                 "a 1-semitone sag you can see it happening.", S["body"]),
       Spacer(1, 3),
       Paragraph("Log the number each session. Next time this song is recorded, check whether the "
                 "49% phrase-ending sag has moved.", S["body"])]
box = Table([[add]], colWidths=[175 * mm])
box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf6e6")),
                         ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#e2c98a")),
                         ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                         ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
st.append(KeepTogether(box))
st.append(Spacer(1, 8))

st.append(Spacer(1, 2))
st.append(Paragraph(
    "<b>Safety.</b> Every exercise here shares one stop rule: dizziness, shoulder lifting, throat gripping "
    "or breath-holding means stop or ease off. This sheet relays the library your analysis prescribes from "
    "and is not a substitute for a teacher watching you do it.", S["warn"]))

doc.build(st)
print("wrote", OUT, os.path.getsize(OUT), "bytes")
