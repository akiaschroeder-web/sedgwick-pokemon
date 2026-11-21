"""Wichita-region player sprites, made by editing FireRed/LeafGreen's Red and Leaf.

Each sheet is read as palette indices, edited (cap turned backwards, hair, clothes)
and written with the character's own 16-colour palette."""
import os
from PIL import Image
from lib import EXP

PEOPLE = f'{EXP}/graphics/object_events/pics/people'

BOY_PAL = [(115, 197, 164), (160, 104, 60), (255, 206, 160), (222, 148, 115), (112, 62, 48),
           (176, 150, 106), (40, 44, 88), (210, 190, 146), (128, 104, 72),
           (246, 238, 213), (205, 190, 156), (92, 108, 170), (56, 64, 118),
           (248, 196, 48), (200, 140, 32), (0, 0, 0)]


def load(path):
    im = Image.open(path)
    w, h = im.size
    px = im.load()
    return [[[px[f * 16 + x, y] for x in range(16)] for y in range(32)] for f in range(w // 16)]


def top_row(fr):
    return next(y for y in range(32) if any(fr[y]))


def save(frames, pal, path):
    im = Image.new('P', (16 * len(frames), 32))
    im.putpalette([c for col in pal for c in col])
    for f, fr in enumerate(frames):
        for y in range(32):
            for x in range(16):
                im.putpixel((f * 16 + x, y), fr[y][x])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def preview(frames, pal, scale=8):
    im = Image.new('RGB', (16 * len(frames), 32))
    for f, fr in enumerate(frames):
        for y in range(32):
            for x in range(16):
                im.putpixel((f * 16 + x, y), pal[fr[y][x]])
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)
