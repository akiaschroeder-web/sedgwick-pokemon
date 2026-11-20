"""Retail: a big-box store widened from Celadon's department-style gym building
(sign and emblem removed, wood roof recoloured to a pale membrane roof), and a
fast-food restaurant drawn in the gas-station palette."""
import colorsys
import orig, gas

SRC = orig.Source('general_frlg', 'celadon_city_frlg')
ROWS = {
    'roof0': (0x139, 0x13a, 0x13b),
    'roof1': (0x141, 0x142, 0x143),
    'roof2': (0x149, 0x14a, 0x14b),
    'wall':  (0x150, 0x155, 0x156),
    'base':  (0x158, 0x15d, 0x15e),
}
DOOR = 0x15b
IDS = sorted({m for v in ROWS.values() for m in v} | {DOOR})


def _membrane(c):
    """Warm wood roof colours -> cool grey of the same lightness."""
    r, g, b = c
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if s > 0.18 and 0.04 < h < 0.17:
        v = int(l * 255)
        return (max(0, v - 6) >> 3 << 3, v >> 3 << 3, min(255, v + 10) >> 3 << 3)
    return c


def _recolor_piece(p):
    def q(g):
        if g in (None, 'LAWN'):
            return g
        return [[None if c is None else _membrane(c) for c in row] for row in g]
    return dict(bottom=[q(g) for g in p['bottom']], top=[q(g) for g in p['top']], layer=p['layer'])


PIECES = {m: _recolor_piece(SRC.piece(m)) for m in IDS}
PALS, ASSIGN = orig.pack([PIECES[m] for m in IDS])


def bigbox_plan(width):
    """width >= 5 metatiles; sliding doors in the middle of the front."""
    rows = []
    for key in ('roof0', 'roof1', 'roof2', 'wall', 'base'):
        l, m, r = ROWS[key]
        rows.append([l] + [m] * (width - 2) + [r])
    rows[-1][width // 2] = DOOR
    return rows


# ---------------------------------------------------------------- fast food (gas palette)
def fastfood():
    """4 x 3 restaurant: red roof plane with a yellow fascia, glass front, and a
    drive-through window on the right; plus a 1 x 2 pole sign."""
    from gas import Pic, O, WH, L, M, D, RL, R, RD, Y, CL, CC, CS, GL, GD, K
    p = Pic(4, 3)
    W = 64
    p.rect(1, 3, W - 2, 22, R)                 # roof plane
    p.rect(1, 3, W - 2, 4, RL)
    for x in range(8, W - 4, 12):
        p.rect(x, 5, x + 5, 9, RD)             # rooftop units
        p.rect(x, 5, x + 5, 5, M)
    p.rect(0, 2, W - 1, 2, O); p.rect(0, 2, 0, 46, O); p.rect(W - 1, 2, W - 1, 46, O)
    p.rect(1, 23, W - 2, 27, Y)                # fascia band
    p.rect(1, 23, W - 2, 23, WH)
    p.rect(1, 28, W - 2, 28, O)
    p.rect(1, 29, W - 2, 45, WH)               # front wall
    for x0 in (4, 18, 44):                     # windows
        p.rect(x0, 31, x0 + 10, 40, GL)
        p.rect(x0, 36, x0 + 10, 40, GD)
        p.rect(x0 - 1, 30, x0 + 11, 30, O); p.rect(x0 - 1, 41, x0 + 11, 41, O)
        p.rect(x0 - 1, 30, x0 - 1, 41, O); p.rect(x0 + 11, 30, x0 + 11, 41, O)
    p.rect(31, 31, 40, 45, GD)                 # glass double door
    p.rect(31, 31, 40, 33, GL)
    p.rect(35, 31, 36, 45, O)
    p.rect(30, 30, 41, 30, O); p.rect(30, 30, 30, 45, O); p.rect(41, 30, 41, 45, O)
    p.rect(1, 43, W - 2, 45, R)                # red base band
    p.rect(1, 46, W - 2, 46, O)
    p.rect(0, 47, W - 1, 47, CS)
    pieces = p.tiles('ff')
    s = Pic(1, 2)
    s.rect(2, 1, 13, 14, R); s.rect(1, 0, 14, 0, O); s.rect(1, 15, 14, 15, O); s.rect(1, 0, 1, 15, O); s.rect(14, 0, 14, 15, O)
    s.rect(2, 1, 13, 1, RL)
    for (x, y) in ((7, 3), (6, 4), (8, 4), (5, 6), (9, 6), (7, 6), (4, 7), (10, 7), (6, 9), (8, 9), (7, 11)):
        s.rect(x, y, x + 1, y + 1, Y)           # abstract star logo
    s.rect(7, 16, 8, 29, M); s.rect(6, 16, 6, 29, O); s.rect(9, 16, 9, 29, O); s.rect(5, 30, 10, 30, O)
    pieces.update(s.tiles('ff_sign'))
    return pieces
