"""Farm buildings built from FireRed's Vermilion City warehouse-roof house.

The corrugated metal roof and wall tiles are copied as-is (they already use
one palette, Vermilion's palette 8), the stucco walls are re-textured as
vertical boards / ribbed metal, and the palette is recoloured:
  BARN palette  - grey metal roof, barn-red board walls
  SHED palette  - galvanised roof and ribbed grey walls (also silos, elevator)
Silo and grain elevator are drawn new using the same colour roles, outline
colour and top-down 3/4 view as the copied art.
"""
import math
from PIL import Image
from lib import EXP, load_jasc

P = f'{EXP}/data/tilesets/primary/general_frlg'
S = f'{EXP}/data/tilesets/secondary/vermilion_city_frlg'


def _load(path):
    im = Image.open(path + '/tiles.png')
    px = im.load()
    w = im.size[0] // 8
    return px, w


_PX = {'p': _load(P), 's': _load(S)}


def T(spec):
    """Original tile by id (with optional 'h'/'v' flip suffix)."""
    s = str(spec)
    hf, vf = 'h' in s, 'v' in s
    t = int(s.rstrip('hv'))
    px, w = _PX['p'] if t < 640 else _PX['s']
    tt = t if t < 640 else t - 640
    tx, ty = (tt % w) * 8, (tt // w) * 8
    g = [[px[tx + x, ty + y] & 15 for x in range(8)] for y in range(8)]
    if hf:
        g = [r[::-1] for r in g]
    if vf:
        g = g[::-1]
    return g


BASE = load_jasc(S + '/palettes/08.pal')
BASE[0] = (255, 0, 255)
BASE[14] = (0, 0, 0)

def recolor(roof, walls, base_strip):
    p = list(BASE)
    p[2], p[3], p[4] = roof
    p[1], p[10], p[11], p[12], p[15] = walls
    p[13] = base_strip
    return p

PAL_BARN = recolor(roof=[(213, 222, 230), (172, 180, 197), (131, 139, 156)],
                   walls=[(246, 148, 123), (230, 106, 90), (205, 74, 74), (164, 49, 57), (139, 41, 49)],
                   base_strip=(156, 156, 164))
PAL_SHED = recolor(roof=[(205, 213, 222), (164, 172, 189), (123, 131, 148)],
                   walls=[(246, 246, 250), (222, 228, 236), (197, 205, 218), (164, 172, 189), (139, 146, 164)],
                   base_strip=(148, 148, 156))
# roles
OUT, G5, G6, WHITE, LGRAY = 7, 5, 6, 8, 9
R_L, R_M, R_D = 2, 3, 4
W_HI, W_L, W_M, W_D, W_E = 1, 10, 11, 12, 15
BASE_STRIP = 13


def boards(g, period=4):
    """Replace the stucco texture (indices 11/12 dots) with vertical boards."""
    out = []
    for y, row in enumerate(g):
        r = []
        for x, v in enumerate(row):
            if v in (W_M, W_D):
                k = x % period
                v = W_D if k == period - 1 else (W_L if k == 0 else W_M)
            r.append(v)
        out.append(r)
    return out


EMPTY = None


def piece(top, under=None, layer='NORMAL', beh='MB_NORMAL', tex=True):
    """top/under: 4 tile specs (TL, TR, BL, BR); None = empty / lawn."""
    def conv(spec):
        if spec is None:
            return None
        if isinstance(spec, list):
            return spec
        g = T(spec)
        return boards(g) if tex else g
    return dict(top=[conv(s) for s in top], under=[conv(s) for s in (under or [None] * 4)],
                layer=layer, beh=beh)


def kit():
    k = {}
    k['roofA_l'] = piece([None, None, 641, 642])
    k['roofA_m'] = piece([None, None, 642, 642])
    k['roofA_r'] = piece([None, None, 642, 643])
    k['roofB_l'] = piece([657, 658, 657, 658])
    k['roofB_m'] = piece([658, 658, 658, 658])
    k['roofB_r'] = piece([658, 659, 658, 659])
    U_C = [674, 674, 690, 690]
    U_D = [586, 586, 602, 602]
    k['wallC_l'] = piece([673, None, 689, None], U_C)
    k['wallC_m'] = piece(U_C)
    k['wallC_r'] = piece([None, 675, None, 691], U_C)
    U_M = [586, 586, 586, 586]
    k['wallM_l'] = piece([585, None, 585, None], U_M, layer='COVERED')
    k['wallM_m'] = piece(U_M, layer='COVERED')
    k['wallM_r'] = piece([None, 587, None, 587], U_M, layer='COVERED')
    k['wallD_l'] = piece([585, None, 601, None], U_D, layer='COVERED')
    k['wallD_m'] = piece(U_D, layer='COVERED')
    k['wallD_r'] = piece([None, 587, None, 603], U_D, layer='COVERED')
    return k


def _door_tiles(kind, tall=False):
    """A 32px wide door across two metatiles, drawn over the wall rows.
    Canvas rows: C bottom half (8px), [M row (16px) if tall], D row (16px)."""
    base_c = boards(T(690))
    base_m = boards(T(586))
    base_d1 = boards(T(602))
    bands = [base_c] + ([base_m, base_m] if tall else []) + [base_m, base_d1]
    H = 8 * len(bands)
    canvas = [[bands[y // 8][y % 8][x % 8] for x in range(32)] for y in range(H)]
    x0, x1, y0, y1 = 4, 27, 3, H - 8           # door rectangle; stops above the base strip
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            edge = x in (x0, x1) or y == y0
            if kind == 'barn':
                v = WHITE if edge or x in (15, 16) else W_M
            else:
                v = OUT if edge else (G5 if (y - y0) % 3 == 0 else LGRAY)
            canvas[y][x] = v
    if kind == 'barn':
        for lx0, lx1 in ((x0 + 1, 14), (17, x1 - 1)):
            for (ax, ay, bx, by) in ((lx0, y0 + 1, lx1, y1), (lx1, y0 + 1, lx0, y1)):
                n = max(abs(bx - ax), abs(by - ay))
                for i in range(n + 1):
                    canvas[round(ay + (by - ay) * i / n)][round(ax + (bx - ax) * i / n)] = WHITE
    out = {}
    for col in range(2):
        for band in range(len(bands)):
            g = [row[col * 16:(col + 1) * 16] for row in canvas[band * 8:(band + 1) * 8]]
            out[(col, band, 0)] = [r[0:8] for r in g]
            out[(col, band, 1)] = [r[8:16] for r in g]
    return out, len(bands)


def door_pieces(kind, tall=False):
    d, n = _door_tiles(kind, tall)
    res = {}
    for col in range(2):
        res[f'wallC_door{col}'] = dict(top=[T(674), T(674), d[(col, 0, 0)], d[(col, 0, 1)]],
                                      under=[None] * 4, layer='NORMAL', beh='MB_NORMAL')
        band = 1
        if tall:
            res[f'wallM_door{col}'] = dict(top=[d[(col, 1, 0)], d[(col, 1, 1)], d[(col, 2, 0)], d[(col, 2, 1)]],
                                          under=[None] * 4, layer='COVERED', beh='MB_NORMAL')
            band = 3
        res[f'wallD_door{col}'] = dict(top=[d[(col, band, 0)], d[(col, band, 1)], d[(col, band + 1, 0)], d[(col, band + 1, 1)]],
                                      under=[None] * 4, layer='COVERED', beh='MB_NORMAL')
    return res


def plan(width, roof_rows=1, door_at=None, tall=False):
    rows = [['roofA_l'] + ['roofA_m'] * (width - 2) + ['roofA_r']]
    for _ in range(roof_rows):
        rows.append(['roofB_l'] + ['roofB_m'] * (width - 2) + ['roofB_r'])
    walls = ['C'] + (['M'] if tall else []) + ['D']
    if door_at is None:
        door_at = (width - 2) // 2
    for w in walls:
        row = [f'wall{w}_l'] + [f'wall{w}_m'] * (width - 2) + [f'wall{w}_r']
        row[door_at], row[door_at + 1] = f'wall{w}_door0', f'wall{w}_door1'
        rows.append(row)
    return rows


# ---------------------------------------------------------------- drawn pieces (shed palette roles)
class Canvas:
    def __init__(self, wt, ht):
        self.w, self.h = wt * 16, ht * 16
        self.wt, self.ht = wt, ht
        self.p = [[0] * self.w for _ in range(self.h)]

    def px(self, x, y, v):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = v

    def rect(self, x0, y0, x1, y1, v):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, v)

    def ellipse(self, cx, cy, rx, ry, shade, outline=OUT):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                d = ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2
                if d <= 1:
                    self.px(x, y, shade(x, y))
        # outline: pixels inside whose 4-neighbour is outside
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                inside = ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1
                if not inside:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if ((nx + .5 - cx) / rx) ** 2 + ((ny + .5 - cy) / ry) ** 2 > 1:
                        self.px(x, y, outline)
                        break

    def cylinder(self, x0, x1, y0, y1, hoops=6):
        """Concrete cylinder body, lit from the upper left, with a rounded bottom."""
        w = x1 - x0
        cx = (x0 + x1) / 2
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                t = (x - x0) / w
                v = W_HI if t < .12 else W_L if t < .4 else W_M if t < .75 else W_D if t < .92 else W_E
                if hoops and (y - y0) % hoops == hoops - 1:
                    v = W_D if t > .4 else W_M
                self.px(x, y, v)
        for y in range(y0, y1 + 1):
            self.px(x0 - 1, y, OUT)
            self.px(x1 + 1, y, OUT)
        # rounded base
        ry = 3
        for x in range(x0 - 1, x1 + 2):
            dy = ry * math.sqrt(max(0, 1 - ((x + .5 - cx) / (w / 2 + 1)) ** 2))
            yb = int(y1 + dy)
            for y in range(y1, yb):
                t = (x - x0) / w
                self.px(x, y, W_D if t > .5 else W_M)
            self.px(x, yb, OUT)

    def tiles(self):
        out = {}
        for r in range(self.ht):
            for c in range(self.wt):
                g = [row[c * 16:(c + 1) * 16] for row in self.p[r * 16:(r + 1) * 16]]
                out[(c, r)] = g
        return out


def dome_shade(cx, cy, rx, ry):
    def f(x, y):
        t = ((x - (cx - rx)) / (2 * rx)) * .7 + ((y - (cy - ry)) / (2 * ry)) * .3
        return R_L if t < .38 else R_M if t < .68 else R_D
    return f


def silo():
    """2 x 5 concrete stave silo with a metal dome, seen from the front-above."""
    C = Canvas(2, 5)
    C.cylinder(3, 28, 14, 72)
    C.ellipse(16, 13, 13.5, 7, dome_shade(16, 13, 13.5, 7))
    C.rect(14, 5, 17, 7, G5)                    # roof vent
    C.rect(14, 5, 17, 5, OUT)
    C.px(13, 6, OUT); C.px(18, 6, OUT); C.px(13, 7, OUT); C.px(18, 7, OUT)
    for y in range(18, 72, 3):                  # chute / ladder on the shaded side
        C.rect(22, y, 24, y, G6)
    C.rect(22, 16, 22, 72, G5); C.rect(24, 16, 24, 72, G5)
    return {f'silo_{c}{r}': g for (c, r), g in C.tiles().items()}


def grain_elevator():
    """6 x 7 concrete elevator: four bins (tops seen from above), a gallery and a headhouse."""
    C = Canvas(6, 7)
    # bins
    for i in range(4):
        x0 = 2 + i * 23
        C.cylinder(x0 + 1, x0 + 21, 30, 100, hoops=0)
    for i in range(4):
        x0 = 2 + i * 23
        C.ellipse(x0 + 11, 30, 11.5, 4.5, lambda x, y: W_HI if y < 30 else W_L)
    # gallery running across the bin tops: flat roof seen from above + front face
    C.rect(1, 18, 94, 24, LGRAY)
    C.rect(1, 18, 94, 18, OUT); C.rect(1, 18, 1, 28, OUT); C.rect(94, 18, 94, 28, OUT)
    C.rect(2, 25, 93, 28, W_M)
    C.rect(1, 29, 94, 29, OUT)
    for x in range(6, 92, 8):
        C.rect(x, 26, x + 2, 27, G6)            # gallery windows
    # headhouse rising above the gallery
    C.rect(58, 2, 86, 8, LGRAY)                  # roof plane
    C.rect(58, 2, 86, 2, OUT); C.rect(58, 2, 58, 17, OUT); C.rect(86, 2, 86, 17, OUT)
    C.rect(59, 9, 85, 17, W_L)
    C.rect(59, 9, 85, 9, G5)
    for x in (63, 71, 79):
        C.rect(x, 11, x + 3, 15, G6)
    # name band (the town name is shown by a sign event)
    C.rect(12, 50, 83, 58, WHITE)
    C.rect(12, 50, 83, 50, OUT); C.rect(12, 58, 83, 58, OUT); C.rect(12, 50, 12, 58, OUT); C.rect(83, 50, 83, 58, OUT)
    # scale house at the foot, Pokemon-style roof plane + wall
    C.rect(64, 86, 95, 92, R_M); C.rect(64, 86, 95, 86, OUT); C.rect(64, 86, 64, 104, OUT); C.rect(95, 86, 95, 104, OUT)
    C.rect(65, 87, 94, 87, R_L)
    C.rect(65, 93, 94, 104, W_L); C.rect(65, 93, 94, 93, G5)
    C.rect(70, 96, 75, 103, G6)
    C.rect(84, 96, 89, 100, G6)
    C.rect(64, 105, 95, 105, OUT)
    return {f'elevator_{c}{r}': g for (c, r), g in C.tiles().items()}
