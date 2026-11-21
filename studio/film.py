"""The listening print. Each frame follows the clock used by the strings."""

from functools import lru_cache
import math
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from cloth import cloth
from lettering import INK, PAPER, PINE, QUIET, RUSSET, serif
from piece import (
    BEATS, BYLINE, CARDS, CENTRE, DURATION, LEAD_IN, PITCHES, SHEET, TITLE,
    at_beat, at_second,
)


W, H = 1440, 900
FPS = 24
LEFT, RIGHT = 96, W - 96
UNIT = (RIGHT - LEFT) / BEATS
BOTTOM, ROW = 793, 19
TOP = BOTTOM - ROW * (len(PITCHES) - 1)


@lru_cache(maxsize=None)
def font(size, italic=False):
    return ImageFont.truetype(str(serif(italic)), size)


def spaced(pen, pos, words, size, spacing, fill):
    x, y = pos
    face = font(size)
    for char in words:
        pen.text((x, y), char, font=face, fill=fill, anchor="ls")
        x += face.getlength(char) + spacing


def fade(value):
    x = min(1.0, max(0.0, value))
    return x * x * (3 - 2 * x)


def note_rect(n):
    x = LEFT + n.start * UNIT
    y = BOTTOM - n.row * ROW
    return (round(x + 1), y - 4, round(x + n.length * UNIT - 1), y + 4)


def make_ground():
    rng = np.random.default_rng(212)
    grain = rng.normal(0, 0.80, (H, W, 1))
    rgb = np.uint8(np.clip(np.array(PAPER) + grain, 0, 255))
    im = Image.fromarray(rgb)
    p = ImageDraw.Draw(im)
    spaced(p, (75, 59), "A TABLE DUET", 18, 3.25, RUSSET)
    author = "CODEX   /   2026"
    author_width = font(16).getlength(author) + (len(author) - 1) * 2.45
    spaced(p, (W - 75 - author_width, 59), author, 16, 2.45, QUIET)
    p.line((75, 83, W - 75, 83), fill=(184, 180, 161))

    # Both reading directions live on the same strip, as on the paper.
    for b in range(BEATS + 1):
        x = round(LEFT + b * UNIT)
        heavy = b % 4 == 0
        rgb = (174, 175, 155) if heavy else (222, 221, 206)
        end = 11 if heavy else 7
        p.line((x, TOP - end, x, BOTTOM + end), fill=rgb)
    for r, pitch in enumerate(PITCHES):
        y = BOTTOM - r * ROW
        p.line((LEFT - 5, y, RIGHT + 5, y), fill=(197, 198, 179))
        p.text((LEFT - 12, y), pitch, font=font(15), anchor="rm", fill=QUIET)
        # An upside-down name belongs to the person across the page.
        letter = Image.new("RGBA", (42, 25))
        ImageDraw.Draw(letter).text(
            (39, 12), pitch, font=font(15), anchor="rm", fill=QUIET,
        )
        letter = letter.transpose(Image.Transpose.ROTATE_180)
        im.paste(letter, (RIGHT + 9, TOP + r * ROW - 12), letter)
    for n in SHEET:
        p.rounded_rectangle(note_rect(n), radius=2, fill=RUSSET if n == CENTRE else (78, 84, 73))
    y = (BOTTOM + TOP) // 2
    for b in range(CENTRE.start, CENTRE.end):
        x = LEFT + (b + 0.5) * UNIT
        p.ellipse((x - 1.0, y - 1.0, x + 1.0, y + 1.0), fill=PAPER)
    for b in range(0, BEATS, 4):
        p.text((LEFT + (b + 2) * UNIT, BOTTOM + 37), str(1 + b // 4),
               font=font(16), anchor="ms", fill=QUIET)

    p.text((LEFT, 597), "Plucked string", font=font(25, True), anchor="ls", fill=PINE)
    p.text((RIGHT, 597), "Bowed string", font=font(25, True), anchor="rs", fill=RUSSET)
    for x, direction, ink in [(LEFT + 155, 1, PINE), (RIGHT - 146, -1, RUSSET)]:
        end = x + 38 * direction
        p.line((x, 588, end, 588), fill=ink, width=2)
        p.line((end - 6 * direction, 584, end, 588, end - 6 * direction, 592),
               fill=ink, width=2)
    return im


@lru_cache(maxsize=None)
def lettering(index):
    card = CARDS[index]
    panel = Image.new("RGBA", (576, 420))
    p = ImageDraw.Draw(panel)
    if card.style == "title":
        p.text((2, 177), card.lines[0], font=font(107), fill=INK, anchor="ls")
        p.text((2, 281), card.lines[1], font=font(107, True), fill=INK, anchor="ls")
    elif card.lines:
        italic = card.style == "italic"
        size = 67 if card.style == "alone" else 48
        while max(font(size, italic).getlength(line) for line in card.lines) > 520:
            size -= 1
        advance = size * 1.28
        y = 220 - (len(card.lines) - 1) * advance / 2
        for line in card.lines:
            p.text((3, y), line, font=font(size, italic), fill=INK, anchor="ls")
            y += advance
    return panel


def add_words(im, seconds):
    for i, card in enumerate(CARDS):
        if not card.lines:
            continue
        start = at_beat(card.beat)
        end = at_beat(CARDS[i + 1].beat) if i + 1 < len(CARDS) else DURATION + 1
        alpha = min(fade((seconds - start) / 0.53) if i else 1,
                    fade((end - seconds) / 0.38))
        if alpha <= 0:
            continue
        words = lettering(i)
        mask = words.getchannel("A")
        if alpha < 1:
            mask = mask.point(lambda v: round(v * alpha))
        im.paste(words, (75, 120), mask)


def add_players(im, beat):
    p = ImageDraw.Draw(im)
    heads = []
    for far in (False, True):
        physical = BEATS - beat if far else beat
        x = round(LEFT + physical * UNIT)
        color = RUSSET if far else PINE
        active = None
        for n in SHEET:
            on = n.start < physical <= n.end if far else n.start <= physical < n.end
            if on:
                active = n
                if n != CENTRE:
                    p.rounded_rectangle(note_rect(n), radius=2, fill=color)
                break
        heads.append((x, far, color, active))
    for x, far, color, active in heads:
        p.line((x, TOP - 14, x, BOTTOM + 14), fill=color, width=1)
        y, step = (BOTTOM + 13, 8) if far else (TOP - 13, -8)
        p.polygon([(x, y), (x - 4, y + step), (x + 4, y + step)], fill=color)
        if active:
            y = BOTTOM - active.row * ROW
            p.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color, outline=PAPER, width=2)


def frame(ground, seconds):
    beat = at_second(seconds)
    im = ground.copy()
    opening = fade((beat - 33) / 2.3) * (1 - fade((beat - 36.7) / 2.3))
    width = round(785 + 150 * opening)
    height = round(458 + 28 * opening)
    left = round(595 * (1 - opening) + (W - width) / 2 * opening)
    top = round(104 - 13 * opening)
    fabric = cloth((width, height), beat)
    im.paste(fabric, (left, top), fabric)
    add_words(im, seconds)
    if LEAD_IN <= seconds < at_beat(BEATS):
        add_players(im, beat)
    return im


def subtitles(path):
    web = path.suffix == ".vtt"

    def stamp(t):
        ms = round(t * 1000)
        s, ms = divmod(ms, 1000)
        m, s = divmod(s, 60)
        separator = "." if web else ","
        return f"00:{m:02}:{s:02}{separator}{ms:03}"

    blocks = []
    for i, card in enumerate(CARDS):
        start = at_beat(card.beat) if i else 0
        end = at_beat(CARDS[i + 1].beat) if i + 1 < len(CARDS) else DURATION
        words = " ".join(card.lines)
        if i == 0:
            words = "Hold the other end\n[A plucked string opens. A bowed string answers.]"
        if not words:
            words = "[The two strings sound the same D for six beats.]"
        blocks.append(f"{i + 1}\n{stamp(start)} --> {stamp(end)}\n{words}\n")
    header = "WEBVTT\n\n" if web else ""
    path.write_text(header + "\n".join(blocks), encoding="utf-8")


def render_film(wav, path, poster):
    ground = make_ground()
    cover = frame(ground, 0)
    cover.save(poster, quality=93, optimize=True, subsampling=0)
    frames = math.ceil(DURATION * FPS)
    with tempfile.TemporaryDirectory() as temp:
        script = Path(temp) / "words.srt"
        subtitles(script)
        command = [
            "ffmpeg", "-v", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
            "-r", str(FPS), "-i", "pipe:0", "-i", str(wav), "-i", str(script),
            "-map", "0:v", "-map", "1:a", "-map", "2:s",
            "-vf", "scale=out_color_matrix=bt709,format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-c:a", "aac", "-b:a", "192k", "-c:s", "mov_text",
            "-disposition:s:0", "0", "-metadata:s:s:0", "language=eng",
            "-metadata:s:s:0", "handler_name=Words and sound",
            "-metadata", f"title={TITLE}", "-metadata", f"artist={BYLINE}",
            "-movflags", "+faststart", str(path),
        ]
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            try:
                for i in range(frames):
                    encoder.stdin.write(frame(ground, i / FPS).tobytes())
            finally:
                encoder.stdin.close()
            if encoder.wait():
                raise RuntimeError("The film encoder exited before the print was finished.")
