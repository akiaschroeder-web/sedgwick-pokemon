"""City pieces: road bridges and footbridges over Hoenn's animated water, an
interstate with shoulders and a median barrier, park furniture, and the river
confluence plaza with an original monument (plus a blank pedestal so the
project's own landmark sprite can be dropped in later).

Bridge pieces keep Hoenn's calm-water metatile (0x170) on the bottom layer, so the
water under and around a bridge keeps animating."""
import math
import street
from street import (paint, one, shade, asph_px, conc_px, grass_px,
                    CL, CC, CS, CX, A, B, WP, YP, YS, KD, AW)
from lib import blank, copy, hflip, vflip

# Hoenn calm water: bottom-layer tile entries copied from primary metatile 0x170
WATER_ENTRIES = [(454 | 4 << 12), (455 | 4 << 12), (455 | 4 << 12), (454 | 4 << 12)]


# ---------------------------------------------------------------- road bridge (street palette)
def _rail_row(v):
    """Concrete parapet seen from above: v = row inside a 6px band (0 = outer)."""
    return [CX, CL, CL, CC, CS, CX][v]


def bridge_pieces():
    """E-W bridge over a N-S river: rows N parapet / deck... / S parapet.
    N-S bridge: W parapet / deck / E parapet. Parapet tiles are top-layer over water."""
    out = {}
    # north parapet: water y<6 (transparent), parapet y6..11, deck below
    def n_par(x, y):
        if y < 6:
            return 0
        if y < 12:
            return _rail_row(y - 6)
        if y == 12:
            return KD
        return asph_px(x, y)
    def s_par(x, y):
        if y < 3:
            return asph_px(x, y)
        if y < 9:
            return [CL, CL, CC, CC, CS, CX][y - 3]       # outer face visible from the south
        if y == 9:
            return KD                                    # shadow on the water
        return 0
    out['bridge_ew_n'] = [[n_par(x, y) for x in range(16)] for y in range(16)]
    out['bridge_ew_s'] = [[s_par(x, y) for x in range(16)] for y in range(16)]
    def w_par(x, y):
        if x < 6:
            return 0
        if x < 12:
            return [CX, CL, CL, CC, CS, CX][x - 6]
        if x == 12:
            return KD
        return asph_px(x, y)
    out['bridge_ns_w'] = [[w_par(x, y) for x in range(16)] for y in range(16)]
    def e_par(x, y):
        if x > 9:
            return 0
        if x > 3:
            return [CX, CS, CC, CL, CL, CX][x - 4]
        if x == 3:
            return KD
        return asph_px(x, y)
    out['bridge_ns_e'] = [[e_par(x, y) for x in range(16)] for y in range(16)]
    # light posts on the parapet every few tiles
    lamp = copy(out['bridge_ew_n'])
    for y in range(2, 8):
        lamp[y][7] = CX
        lamp[y][8] = CS
    lamp[1][6], lamp[1][7], lamp[1][8], lamp[1][9] = CX, CL, CL, CX
    out['bridge_ew_n_lamp'] = lamp
    return out


def footbridge_pieces():
    """Narrow pedestrian bridge, one tile wide: wooden deck with steel rails."""
    WOOD_L, WOOD_D = CC, CS   # drawn in concrete tones (reads as a pale timber deck)
    def ns(x, y):
        if x < 2 or x > 13:
            return 0
        if x in (2, 13):
            return CX                                     # rail
        if x in (3, 12):
            return KD
        return WOOD_D if y % 4 == 3 else WOOD_L
    def ew(x, y):
        if y < 3 or y > 13:
            return 0
        if y == 3:
            return CX
        if y == 4:
            return CL
        if y in (12, 13):
            return [CS, CX][y - 12]
        return WOOD_D if x % 4 == 3 else WOOD_L
    return {'footbridge_ns': [[ns(x, y) for x in range(16)] for y in range(16)],
            'footbridge_ew': [[ew(x, y) for x in range(16)] for y in range(16)]}


# ---------------------------------------------------------------- interstate (E-W; N-S = transposed)
def _interstate_fn(kind):
    """kind: shoulder_n | lane | lane_dash | median_n | median | median_s | shoulder_s"""
    def f(x, y):
        a = asph_px(x, y)
        if kind == 'shoulder_n':            # grass, paved shoulder, white edge line
            if y < 4:
                return grass_px(x, y)
            if y == 4:
                return CX
            if y == 12:
                return WP
            return a
        if kind == 'shoulder_s':
            if y > 11:
                return grass_px(x, y)
            if y == 11:
                return CX
            if y == 3:
                return WP
            return a
        if kind == 'lane_dash':
            return WP if (y == 15 and x % 16 < 10) else a
        if kind == 'median_n':              # yellow edge line, inner shoulder, barrier top half
            if y == 3:
                return YP
            if y >= 12:
                return [CX, CL, CL, CC][y - 12]
            return a
        if kind == 'median_s':
            if y <= 3:
                return [CC, CS, CS, CX][y]
            if y == 4:
                return KD
            if y == 12:
                return YP
            return a
        return a
    return f


def interstate_pieces():
    out = {}
    for k in ('shoulder_n', 'lane', 'lane_dash', 'median_n', 'median_s', 'shoulder_s'):
        f = _interstate_fn(k)
        out[f'i_{k}'] = [[f(x, y) for x in range(16)] for y in range(16)]
        out[f'i_{k}_v'] = [[f(y, x) for x in range(16)] for y in range(16)]
    return out


# ---------------------------------------------------------------- park furniture (props palette, top layer)
from props import art as _art

PLAYGROUND_SLIDE = _art("""
................
................
....oooo........
...oLLLLo.......
...oMooMo.......
...oMooMoo......
...oyyyyyyo.....
...oMo.oyyyo....
...oMo..oyyyo...
...oMo...oyyyo..
...oMo....oyyyo.
...oMo.....oyyo.
...oMo......oo..
...ooo..........
...zzz....zzzz..
................
""")
SWINGS = _art("""
................
................
.oooooooooooooo.
.oLLLLLLLLLLLLo.
.oMoo.o..o.ooMo.
.oM...o..o...Mo.
.oM...o..o...Mo.
.oM...o..o...Mo.
.oM...o..o...Mo.
.oM..orro.orrMo.
.oM..oRRo.oRRMo.
.oM..........Mo.
.oM..........Mo.
.oo..........oo.
.zz..zzzz.zzzzz.
................
""")
BENCH = _art("""
................
................
................
................
................
................
..oooooooooooo..
..oppppppppppo..
..oqqqqqqqqqqo..
..oooooooooooo..
..oppppppppppo..
..oQQQQQQQQQQo..
..oDo......oDo..
..ooo......ooo..
..zzzzzzzzzzzz..
................
""")
PICNIC = _art("""
................
................
................
..oooooooooooo..
..oppppppppppo..
..oqqqqqqqqqqo..
.oooooooooooooo.
.oppppppppppppo.
.oqqqqqqqqqqqqo.
.oQQQQQQQQQQQQo.
.ooQoooooooQooo.
..oQo......oQo..
..ooo......ooo..
..zzzzzzzzzzzz..
................
................
""")
TRASH = _art("""
................
................
................
................
................
................
.....oooooo.....
....oDDDDDDo....
....oMLLLLMo....
....oMLLLLMo....
....oMLLLLMo....
....oMLLLLMo....
....oMMMMMMo....
.....oooooo.....
.....zzzzzz.....
................
""")


def pavilion(width=4):
    """width x 3 picnic shelter: green metal roof plane (top layer) on timber posts."""
    W = width * 16
    g = [[0] * W for _ in range(48)]
    def r(x0, y0, x1, y1, v):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if 0 <= x < W and 0 <= y < 48:
                    g[y][x] = v
    O, LM, GN, GD, WD, WM = 1, 2, 9, 10, 11, 12
    r(1, 4, W - 2, 26, GN)
    for x in range(6, W - 4, 6):
        r(x, 5, x, 25, GD)
    r(1, 4, W - 2, 4, LM)
    r(0, 3, W - 1, 3, O); r(0, 3, 0, 28, O); r(W - 1, 3, W - 1, 28, O)
    r(1, 27, W - 2, 28, GD)
    r(0, 29, W - 1, 29, O)
    for x in (4, W - 8):
        r(x, 30, x + 3, 44, WM)
        r(x, 30, x, 44, WD)
        r(x - 1, 30, x - 1, 44, O); r(x + 4, 30, x + 4, 44, O)
        r(x - 1, 45, x + 4, 45, O)
    return {f'pavilion_{c}{rr}': [row[c * 16:(c + 1) * 16] for row in g[rr * 16:(rr + 1) * 16]]
            for rr in range(3) for c in range(width)}


def ball_diamond():
    """4x4 infield: dirt diamond with bases and a pitcher's mound (top layer over lawn)."""
    N = 64
    g = [[0] * N for _ in range(N)]
    cx, cy = 32, 36
    DIRT, DIRT_D, WHITE, O = 11, 12, 6, 1
    for y in range(N):
        for x in range(N):
            d = abs(x + .5 - cx) + abs(y + .5 - cy)
            if d < 22:
                g[y][x] = DIRT if (x * 7 + y * 3) % 13 else DIRT_D
            if 22 <= d < 23:
                g[y][x] = DIRT_D
    # base lines and bases
    for (bx, by) in ((cx, cy + 20), (cx + 20, cy), (cx, cy - 20), (cx - 20, cy)):
        for y in range(by - 1, by + 2):
            for x in range(bx - 1, bx + 2):
                g[y][x] = WHITE
    for y in range(cy - 2, cy + 3):
        for x in range(cx - 2, cx + 3):
            if (x - cx) ** 2 + (y - cy) ** 2 <= 5:
                g[y][x] = DIRT_D
    g[cy][cx] = WHITE
    return {f'diamond_{c}{r}': [row[c * 16:(c + 1) * 16] for row in g[r * 16:(r + 1) * 16]]
            for r in range(4) for c in range(4)}


# ---------------------------------------------------------------- confluence plaza (street palette ground)
def plaza_pieces():
    """Round paved plaza (6x6) with a planted ring; the monument stands in the middle."""
    cx, cy, R = 48.0, 48.0, 44.0
    def f(X, Y):
        d = math.hypot(X + .5 - cx, Y + .5 - cy)
        if d > R:
            return grass_px(X, Y)
        if d > R - 1:
            return CX
        if 26 < d < 30:                 # planted ring
            return 3 if (X + Y) % 3 else 4
        if d < 10:                      # inner pavement circle
            return CL if (int(math.atan2(Y - cy, X - cx) * 4) % 2) else CC
        return CS if (int(d) % 6 == 0) else CC
    out = {}
    for r in range(6):
        for c in range(6):
            out[f'plaza_{c}{r}'] = [[f(c * 16 + x, r * 16 + y) for x in range(16)] for y in range(16)]
    return out


def park_props():
    return {'playground_slide': PLAYGROUND_SLIDE, 'swings': SWINGS, 'bench': BENCH,
            'picnic_table': PICNIC, 'trash_can': TRASH}


# ---------------------------------------------------------------- river banks (nature palette, over water)
PAL_NATURE = [(255, 0, 255),
    (164, 213, 197), (115, 197, 164), (65, 180, 131), (24, 164, 106),       # 1-4 Hoenn grass
    (238, 222, 172), (205, 180, 131), (164, 139, 98), (115, 98, 74),        # 5-8 sand / mud
    (222, 238, 246), (115, 180, 230),                                       # 9 foam, 10 shallow edge
    (189, 148, 98), (148, 106, 65), (248, 248, 248), (41, 41, 57), (82, 98, 115)]
N_GR = {1: 1, 2: 2, 3: 3, 4: 4}


def bank_shade(d, X, Y):
    """d = distance from the waterline, positive on land."""
    if d < -2:
        return 0                     # open water (animated tiles underneath)
    if d < -1:
        return 10
    if d < 0:
        return 9                     # foam line
    if d < 1:
        return 8
    if d < 2.5:
        return 7
    if d < 4.5:
        return 6 if (X * 5 + Y * 3) % 7 else 7
    if d < 5.5:
        return 5
    if d < 6.5:
        return 4
    return grass_px(X, Y)


def bank_pieces():
    out = {}
    def tile(f):
        return [[bank_shade(f(x + .5, y + .5), x, y) for x in range(16)] for y in range(16)]
    # straight banks: land on the named side
    out['bank_n'] = tile(lambda x, y: 9 - y)
    out['bank_s'] = tile(lambda x, y: y - 7)
    out['bank_w'] = tile(lambda x, y: 9 - x)
    out['bank_e'] = tile(lambda x, y: x - 7)
    # inner corners: land on the two named sides, water in the opposite corner
    for tag, (cx, cy) in {'nw': (16, 16), 'ne': (0, 16), 'sw': (16, 0), 'se': (0, 0)}.items():
        out[f'bank_in_{tag}'] = tile(lambda x, y, cx=cx, cy=cy: math.hypot(x - cx, y - cy) - 7)
    # outer corners (a point of land; water on the two sides away from the named corner)
    for tag, (cx, cy) in {'nw': (0, 0), 'ne': (16, 0), 'sw': (0, 16), 'se': (16, 16)}.items():
        out[f'bank_out_{tag}'] = tile(lambda x, y, cx=cx, cy=cy: 9 - math.hypot(x - cx, y - cy))
    return out


def landmark_from_png(path, plaza=None, max_w=64, max_h=128, footprint=22):
    """Project-supplied landmark sprite (PNG with a transparent background, 1 px = 1 px).

    The sprite is centred horizontally on the plaza and its base sits so the bottom
    `footprint` px straddle the plaza centre; anything above the plaza is drawn over
    lawn. Colours are packed into up to three 15-colour palettes.

    Returns (pieces, palettes, origin) where pieces maps 'landmark_<col>_<row>' to
    (bottom_grid_name, [4 top quads as RGB grids or None]) and origin is the
    (col, row) offset of the top-left piece relative to the plaza's top-left tile.
    Returns ({}, [], (0, 0)) when the file is missing."""
    import os
    from PIL import Image
    if not os.path.exists(path):
        return {}, [], (0, 0)
    im = Image.open(path).convert('RGBA')
    if im.width > max_w or im.height > max_h:
        im.thumbnail((max_w, max_h), Image.NEAREST)
    import colorsys
    alpha = im.split()[3]
    def is_warm(c):
        h, l, sat = colorsys.rgb_to_hls(*(v / 255 for v in c))
        return sat > 0.22 or l < 0.16
    warm, cool = [], []
    for y in range(im.height):
        for x in range(im.width):
            p = im.getpixel((x, y))
            if p[3] >= 128:
                (warm if is_warm(p[:3]) else cool).append(p[:3])
    def quantise(cols, n=15):
        if not cols:
            return []
        strip = Image.new('RGB', (len(cols), 1))
        strip.putdata(cols)
        q = strip.quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        pal = q.getpalette()[:3 * n]
        return sorted({tuple(v >> 3 << 3 for v in pal[i:i + 3]) for i in range(0, len(pal), 3)})
    group_pals = [p for p in (quantise(warm), quantise(cool)) if p]
    cx, cy = 48, 48                       # plaza centre in plaza pixels
    left = cx - im.width // 2
    bottom = cy + footprint // 2
    top = bottom - im.height
    c0, r0 = left // 16, top // 16        # may be negative (above the plaza)
    c1, r1 = (left + im.width - 1) // 16, (bottom - 1) // 16
    pieces = {}
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            quads = []
            any_px = False
            for oy, ox in ((0, 0), (0, 8), (8, 0), (8, 8)):
                g = [[None] * 8 for _ in range(8)]
                for y in range(8):
                    for x in range(8):
                        X, Y = c * 16 + ox + x - left, r * 16 + oy + y - top
                        if 0 <= X < im.width and 0 <= Y < im.height:
                            p = im.getpixel((X, Y))
                            if p[3] >= 128:
                                g[y][x] = tuple(v >> 3 << 3 for v in p[:3])   # GBA 15-bit colour
                                any_px = True
                quads.append(g if any(v for row in g for v in row) else None)
            if not any_px:
                continue
            under = f'plaza_{c}{r}' if 0 <= c < 6 and 0 <= r < 6 else 'lawn'
            pieces[f'landmark_{c - c0}_{r - r0}'] = (under, quads)
    # each 8x8 tile takes the palette that fits most of its pixels; others snap to it
    def near(c, pal):
        return min(pal, key=lambda k: sum((a - b) ** 2 for a, b in zip(c, k)))
    pals = [[(255, 0, 255)] + gp + [(0, 0, 0)] * (15 - len(gp)) for gp in group_pals]
    assign = {}
    for name, (under, quads) in pieces.items():
        for qi, g in enumerate(quads):
            if g is None:
                continue
            cols = [v for row in g for v in row if v]
            best = min(range(len(group_pals)), key=lambda i: sum(sum((a - b) ** 2 for a, b in zip(c, near(c, group_pals[i]))) for c in cols))
            ng = [[near(v, group_pals[best]) if v else None for v in row] for row in g]
            quads[qi] = ng
            assign[id(ng)] = best
    return pieces, (pals, assign), (c0, r0)
