"""Commercial / multi-unit buildings from Celadon City's flat-roofed row buildings
(apartments, offices, storefront rows), plus parking lots.

A block is made of 4-column units. Each unit can have a rooftop AC unit and either
windows or a front door on the ground floor. Wall colour is a palette swap.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orig
from lib import EXP, load_jasc
from PIL import Image

SRC = orig.Source('general_frlg', 'celadon_city_frlg')

ROWS = {
    'roof0':   ([0x2ed, 0x2ee, 0x2ee, 0x2f6], [0x2ed, 0x2ee, 0x2df, 0x2f5]),   # (plain, with AC)
    'roof1':   ([0x2e0, 0x2e1, 0x2e1, 0x2e4], [0x2e0, 0x2e1, 0x2e2, 0x2e3]),
    'cornice': ([0x2e8, 0x2e9, 0x2eb, 0x2ec],) * 2,
    'upper':   ([0x2f0, 0x2f1, 0x2f3, 0x2f4], [0x314, 0x315, 0x316, 0x2f4]),   # (windows, above a door)
    'ground':  ([0x2f8, 0x2f9, 0x2fb, 0x2fc], [0x2e5, 0x03d, 0x2e7, 0x2fc]),
}
DOOR = 0x03d
IDS = sorted({m for v in ROWS.values() for opt in v for m in opt})

PIECES = {m: SRC.piece(m) for m in IDS}
BASE_PALS, ASSIGN = orig.pack([PIECES[m] for m in IDS])

WALL_GREENS = [(106, 148, 139), (115, 172, 148), (148, 205, 180), (189, 230, 222)]
WALL_VARIANTS = {
    'mint':  WALL_GREENS,
    'brick': [(156, 82, 74), (189, 106, 90), (222, 148, 123), (246, 197, 172)],
    'beige': [(164, 139, 106), (197, 172, 131), (222, 205, 164), (246, 238, 213)],
}
WALL_PAL = next(i for i, p in enumerate(BASE_PALS) if WALL_GREENS[1] in p)
OTHER_PAL = 1 - WALL_PAL


def wall_palette(variant):
    lut = dict(zip(WALL_GREENS, WALL_VARIANTS[variant]))
    return [lut.get(c, c) for c in BASE_PALS[WALL_PAL]]


def quad_palette(g):
    return ASSIGN[id(g)]


def plan(units, storeys=2, ac=(), doors=(0,)):
    """units = number of 4-wide units. Returns rows of metatile ids."""
    names = ['roof0', 'roof1', 'cornice'] + (['upper'] if storeys == 2 else []) + ['ground']
    rows = []
    for n in names:
        row = []
        for u in range(units):
            if n in ('roof0', 'roof1'):
                opt = ROWS[n][1 if u in ac else 0]
            elif n in ('upper', 'ground'):
                opt = ROWS[n][1 if u in doors else 0]
            else:
                opt = ROWS[n][0]
            row += opt
        rows.append(row)
    if storeys == 1:
        # without an upper storey the door frame row is dropped; keep the door itself
        pass
    return rows


def door_anim_png(dst, target_pal):
    """Re-index FRLG's generic door animation into our packed palette."""
    src = Image.open(f'{EXP}/graphics/door_anims/general_frlg.png')
    pal2 = load_jasc(f'{EXP}/data/tilesets/primary/general_frlg/palettes/02.pal')
    def nearest(c):
        return min(range(1, 16), key=lambda i: sum((a - b) ** 2 for a, b in zip(c, target_pal[i])))
    out = Image.new('P', src.size, 0)
    flat = [v for c in target_pal for v in c]
    out.putpalette(flat + [0] * (768 - len(flat)))
    for y in range(src.height):
        for x in range(src.width):
            v = src.getpixel((x, y)) & 15
            if v:
                out.putpixel((x, y), nearest(pal2[v]))
    out.save(dst)


# ---------------------------------------------------------------- parking lots (street palette)
def parking():
    import street
    A = street.asph_px
    WP = street.WP
    def tile(fn):
        return [[fn(x, y) or A(x, y) for x in range(16)] for y in range(16)]
    return {
        'lot_stalls_n': tile(lambda x, y: WP if (x == 0 and y >= 2) or (y == 15 and False) else 0),   # stalls facing north
        'lot_stalls_s': tile(lambda x, y: WP if (x == 0 and y <= 13) else 0),
        'lot_stalls_w': tile(lambda x, y: WP if (y == 0 and x >= 2) else 0),
        'lot_stalls_e': tile(lambda x, y: WP if (y == 0 and x <= 13) else 0),
        'lot_arrow_n':  tile(lambda x, y: WP if (x in (7, 8) and 5 <= y <= 12) or (y - 3 == abs(x - 7.5) // 1 and 3 <= y <= 7) else 0),
    }
