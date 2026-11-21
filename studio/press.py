"""Set the two facing texts and their one shared, reversible score."""

from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from cloth import cloth
from lettering import INK, QUIET, RUSSET, serif
from piece import BEATS, BYLINE, CENTRE, MIDDLE, PITCHES, SHEET, TITLE


W, H = landscape(A4)
MARGIN = 38
START, FINISH = 55, W - 55
UNIT = (FINISH - START) / BEATS
STEP = 13.6
STAVE = H / 2 - 4 * STEP


def color(c, rgb, stroke=False):
    setter = c.setStrokeColorRGB if stroke else c.setFillColorRGB
    setter(*(value / 255 for value in rgb))


def label(c, x, y, words, size=7.8, tracking=1.5):
    text = c.beginText(x, y)
    text.setFont("Text", size)
    text.setCharSpace(tracking)
    text.textOut(words)
    text.setCharSpace(0)
    c.drawText(text)


def rule(c, x0, y0, x1, y1, rgb, weight):
    color(c, rgb, stroke=True)
    c.setLineWidth(weight)
    c.line(x0, y0, x1, y1)


def facing_text(c, bowed):
    color(c, RUSSET)
    label(c, MARGIN + 1, 180, "A TABLE DUET BY CODEX")
    c.setFont("Text", 36.5)
    color(c, INK)
    c.drawString(MARGIN - 1, 137, TITLE)

    if bowed:
        lines = [
            ("I kept the sheet. Between the lift and the fold there’s a little", "Text"),
            ("while when the air has a roof. I set a D in the crease for four", "Text"),
            ("beats. When I put the parts face to face, four seemed stingy.", "Text"),
            ("I gave it six.", "TextItalic"),
        ]
    else:
        lines = [
            ("I tried a childhood in eight words.", "Text"),
            ("My mother took two corners of the sheet.", "TextItalic"),
            ("I could put a pale stripe on her wrist where her watch had been.", "Text"),
            ("It was the ease of the wrist that made me stop.", "Text"),
        ]
    for line, (words, face) in enumerate(lines):
        c.setFont(face, 11.35)
        c.drawString(MARGIN + 1, 106 - line * 16, words)

    art = cloth((1050, 630), MIDDLE if bowed else 0)
    plate = Image.new("RGB", art.size, "white")
    plate.paste(art, mask=art.getchannel("A"))
    c.drawImage(ImageReader(plate), 361, 48, 179, 108)

    edge = 566
    color(c, RUSSET)
    label(c, edge, 180, "BOWED STRING" if bowed else "PLUCKED STRING")
    color(c, INK)
    directions = (
        "Fold the short edges together, then open the page.",
        "Sit facing each other along the long edges.",
        "Begin counting together, each at your own left.",
        "Each column is one beat. Use the pitches at left.",
        "Sound the bars for their full width. Rest in the gaps.",
    )
    c.setFont("Text", 10.8)
    for line, words in enumerate(directions):
        c.drawString(edge, 146 - line * 14.4, words)
    c.setFont("TextItalic", 11)
    c.drawString(edge, 59, "Gently, about 64 beats a minute.")


def facing_labels(c):
    color(c, INK)
    c.setFont("Text", 9.5)
    for i, pitch in enumerate(PITCHES):
        c.drawRightString(START - 8.6, STAVE + i * STEP - 3.3, pitch)
    color(c, QUIET)
    c.setFont("Text", 8.2)
    for i in range(0, BEATS, 4):
        c.drawCentredString(START + (i + 2) * UNIT, STAVE - 21.5, str(i // 4 + 1))


def score(c):
    low = STAVE - STEP * 0.50
    high = H - low
    for beat in range(BEATS + 1):
        x = START + beat * UNIT
        heavy = beat % 4 == 0
        rgb = (156, 159, 143) if heavy else (219, 219, 205)
        overhang = 2.6 if heavy else 0
        rule(c, x, low - overhang, x, high + overhang, rgb, 0.42 if heavy else 0.26)
    for i in range(len(PITCHES)):
        y = STAVE + i * STEP
        rule(c, START - 4, y, FINISH + 4, y, (179, 182, 165), 0.42)

    for n in SHEET:
        y = STAVE + n.row * STEP
        x = START + n.start * UNIT + 0.34
        w = n.length * UNIT - 0.68
        color(c, RUSSET if n == CENTRE else INK)
        c.roundRect(x, y - 2.55, w, 5.1, 1.3, fill=1, stroke=0)
        if n == CENTRE:
            c.setFillColorRGB(1, 1, 1)
            for beat in range(n.start, n.end):
                c.circle(START + (beat + 0.5) * UNIT, y, 0.63, stroke=0, fill=1)


def render_pdf(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont("Text", str(serif())))
    pdfmetrics.registerFont(TTFont("TextItalic", str(serif(italic=True))))
    c = canvas.Canvas(str(path), pagesize=(W, H), pageCompression=1, invariant=1)
    c.setTitle(TITLE)
    c.setAuthor(BYLINE)
    c.setCreator(BYLINE)
    c.setDateFormatter(lambda *_: "D:20261121")
    c.setSubject("One melody read simultaneously from opposite edges of the paper")
    score(c)
    for bowed in (False, True):
        c.saveState()
        if bowed:
            c.translate(W, H)
            c.rotate(180)
        facing_labels(c)
        facing_text(c, bowed)
        # The crease runs between the two small marks.
        rule(c, W / 2, 11, W / 2, 22, (162, 119, 93), 0.48)
        c.restoreState()
    c.showPage()
    c.save()
