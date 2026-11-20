"""Shared helpers for building Sedgwick County tiles in GBA (Gen 3 decomp) format.

A metatile here is a dict:
  {'pal': slot, 'px': 16x16 list of colour indices (0 = transparent),
   'top': optional 16x16 top-layer grid, 'beh': behaviour name, 'layer': 'normal'|'covered'|'split'}
"""
import json, os, struct
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))  # repo root

# ---------------------------------------------------------------- palettes
# Slot 6: fields / pavement (the approved sample palette)
PAL_FIELD = [(255, 0, 255),
    (164, 213, 197), (115, 197, 164), (65, 180, 131), (24, 164, 106),        # 1-4 Hoenn grass (exact)
    (255, 246, 180), (238, 213, 115), (213, 172, 82), (180, 131, 65), (123, 90, 49),  # 5-9 wheat
    (230, 230, 222), (205, 205, 197), (172, 172, 164), (123, 123, 131),      # 10-13 concrete
    (98, 98, 106), (74, 74, 85)]                                             # 14-15 asphalt

def grid(s, key):
    rows = s.strip('\n').split('\n')
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), [len(r) for r in rows]
    return [[key[c] for c in r] for r in rows]

def blank(v=0):
    return [[v] * 16 for _ in range(16)]

def copy(g):
    return [list(r) for r in g]

def hflip(g):
    return [r[::-1] for r in g]

def vflip(g):
    return [list(r) for r in g[::-1]]

def to_image(g, pal, scale=1, bg=None):
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    px = im.load()
    for y in range(16):
        for x in range(16):
            v = g[y][x]
            if v:
                px[x, y] = pal[v] + (255,)
    if scale != 1:
        im = im.resize((16 * scale, 16 * scale), Image.NEAREST)
    return im

def jasc(colors):
    return 'JASC-PAL\r\n0100\r\n16\r\n' + ''.join(f'{r} {g} {b}\r\n' for r, g, b in colors)

def rgb555_round(c):
    """GBA colours are 5 bits per channel; round to what the hardware can show."""
    return tuple(min(255, (v >> 3) * 8 + ((v >> 3) * 8 >> 5)) for v in c)

# ---------------------------------------------------------------- Emerald references
def load_jasc(p):
    return [tuple(int(x) for x in l.split()) for l in open(p).read().split('\n')[3:19]]

def em_metatile_img(index, primary='general', npal=6, ntiles=512):
    """Render an Emerald primary metatile as an RGB 16x16 image (both layers)."""
    base = f'{EXP}/data/tilesets/primary/{primary}'
    tiles_im = Image.open(base + '/tiles.png')
    pals = [load_jasc(f'{base}/palettes/{i:02d}.pal') for i in range(npal)]
    d = open(base + '/metatiles.bin', 'rb').read()
    e = struct.unpack('<8H', d[index * 16:index * 16 + 16])
    out = Image.new('RGB', (16, 16))
    tp = tiles_im.load()
    for layer in range(2):
        for q in range(4):
            v = e[layer * 4 + q]
            t, hf, vf, pl = v & 0x3ff, v >> 10 & 1, v >> 11 & 1, v >> 12
            if t >= ntiles or pl >= npal:
                continue
            tx, ty = (t % 16) * 8, (t // 16) * 8
            for y in range(8):
                for x in range(8):
                    c = tp[tx + (7 - x if hf else x), ty + (7 - y if vf else y)] & 15
                    if layer == 1 and c == 0:
                        continue
                    out.putpixel(((q % 2) * 8 + x, (q // 2) * 8 + y), pals[pl][c])
    return out
