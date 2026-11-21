"""A little length of linen, drawn one strip of the weave at a time."""

import math

import numpy as np
from PIL import Image, ImageDraw

from piece import MIDDLE, OTHER_SIDE, SHEET


CORDS = 80
PICKS = 48
U, V = np.meshgrid(np.linspace(0, 1, CORDS + 1), np.linspace(0, 1, PICKS + 1))
SPAN = np.sin(np.pi * U).clip(0) ** 0.83
WIDTH = np.sin(np.pi * V).clip(0) ** 0.85
TAU = 2 * np.pi


def surface(beat):
    u, v = U, V
    lift = math.exp(-((beat - MIDDLE) / 12) ** 2)
    drift = 0.17 * math.sin(beat * 0.12)
    x = 2.70 * (u - 0.5) + 0.12 * SPAN * np.sin(TAU * (v + 0.42 * u) + drift)
    depth = 1.56 * (v - 0.5) * (1 - 0.21 * SPAN) + 0.13 * np.sin(TAU * u)

    z = (0.39 + 0.61 * lift) * SPAN - (0.40 - 0.22 * SPAN) * WIDTH
    z += (0.06 + 0.26 * SPAN) * np.sin(TAU * (1.27 * v - 0.54 * u) + drift)
    z += SPAN * 0.12 * np.sin(TAU * (2.79 * v + 0.61 * u) + 1.11 - drift)
    z += 0.21 * (2 * u - 1) * (2 * v - 1)
    z += 0.10 * SPAN * np.sin(TAU * (1.9 * u - 0.83 * v) + beat * 0.065)

    # A disturbance travels inwards from the edge of each sounding player.
    for notes, distance, direction in ((SHEET, u, 1), (OTHER_SIDE, 1 - u, -1)):
        for note in notes:
            age = beat - note.start
            if 0 < age < 6:
                crest = distance - age / 4.8
                ripple = np.exp(-35 * crest ** 2 - age * 0.45)
                z += 0.057 * SPAN * ripple * np.sin(10 * crest + 3.8 * v * direction)
    return x, depth, z


def cloth(size, beat):
    """Return a transparent, antialiased impression at the requested size."""
    width, height = size
    scale = 2
    x, depth, z = surface(beat)
    paper_x = 0.499 + 0.276 * (x + 0.49 * depth - 0.035 * z)
    paper_y = 0.578 - 0.449 * (0.195 * x - 0.43 * depth + 0.94 * z)
    px = np.rint(paper_x * width * scale).astype(int).tolist()
    py = np.rint(paper_y * height * scale).astype(int).tolist()
    points = [list(zip(xx, yy)) for xx, yy in zip(px, py)]

    space = np.stack([x, depth, z], axis=-1)
    normal = np.cross(np.gradient(space, axis=1), np.gradient(space, axis=0))
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    light = normal @ [-0.44, -0.32, 0.84]
    shadow = np.clip(0.91 - light, 0, 1.32)
    shade = np.rint(shadow * 31).astype(int).tolist()

    im = Image.new("RGBA", (width * scale, height * scale))
    pen = ImageDraw.Draw(im)
    broadcloth = (253, 250, 235)
    madder = (174, 76, 49)
    seam = (96, 87, 66)
    line_width = max(1, round(width * scale / 1200))
    for j in range(PICKS):
        far, near = points[j], points[j + 1]
        red = j in (38, 39, 42)
        ground = madder if red else broadcloth
        for i in range(CORDS):
            darkness = shade[j][i]
            rgb = tuple(c - darkness for c in ground)
            pen.polygon((far[i], far[i + 1], near[i + 1], near[i]), fill=rgb)
            # The cross threads emerge in the shadows. The stagger of the
            # darker stitches keeps them woven into the surface as it moves.
            cross = 7 + darkness // 2 + (i % 3 == 0) * 5
            pen.line((far[i], near[i]), fill=tuple(c - cross for c in rgb), width=line_width)
            if (i + j) % 3 == 0:
                pen.line((near[i], near[i + 1]), fill=tuple(c - 13 for c in rgb), width=line_width)
        ink = tuple(c - (28 if j % 3 == 0 else 18) for c in ground)
        pen.line(near, fill=ink, width=line_width)
        for edge in (0, CORDS):
            pen.line((far[edge], near[edge]), fill=seam, width=line_width)
        if j in (0, 46):
            for i in range(0, CORDS, 2):
                p, q = near[i], near[i + 1]
                pen.line((p, q), fill=(156, 146, 118), width=line_width)
    return im.resize(size, Image.Resampling.LANCZOS)
