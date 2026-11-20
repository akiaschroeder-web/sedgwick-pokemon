"""Nature and leisure pieces.

City tileset (street / props / nature palettes): the Wichita-Valley Center floodway
(concrete-lined channel over animated water), wooden docks, a golf course
(fairway, green with flag, bunker, tee), a cemetery (headstones, iron fence), and a
glass conservatory for the botanical garden plus a zoo entrance arch.
Rural tileset (road palette): oil pumpjack, corral fence and cattle."""
import math
import street
from street import CL, CC, CS, CX, KD, grass_px, conc_px

# ---------------------------------------------------------------- floodway (street palette, over water)
def canal():
    """Concrete channel walls: the slope is seen from above, land on the named side."""
    def slope(d, X, Y):
        # d = distance from the waterline toward land
        if d < 0:
            return 0
        if d < 1:
            return KD                         # wet shadow line
        if d < 6:
            return CS if int(d) % 2 else CC   # sloped concrete with form lines
        if d < 7:
            return CL                         # top lip
        if d < 8:
            return CX
        return grass_px(X, Y)
    def t(f):
        return [[slope(f(x + .5, y + .5), x, y) for x in range(16)] for y in range(16)]
    return {'canal_n': t(lambda x, y: 12 - y), 'canal_s': t(lambda x, y: y - 4),
            'canal_w': t(lambda x, y: 12 - x), 'canal_e': t(lambda x, y: x - 4)}


# ---------------------------------------------------------------- props-palette art
from props import art as _art

DOCK_NS = _art("""
...oppppppppo...
...oqqqqqqqqo...
...oppppppppo...
...oQQQQQQQQo...
...oppppppppo...
...oqqqqqqqqo...
...oppppppppo...
...oQQQQQQQQo...
...oppppppppo...
...oqqqqqqqqo...
...oppppppppo...
...oQQQQQQQQo...
...oppppppppo...
...oqqqqqqqqo...
...oppppppppo...
...oQQQQQQQQo...
""")
DOCK_END = _art("""
...oppppppppo...
...oqqqqqqqqo...
...oppppppppo...
...oQQQQQQQQo...
...oppppppppo...
...oqqqqqqqqo...
...oppppppppo...
...oQQQQQQQQo...
...oppppppppo...
...oqqqqqqqqo...
...ooooooooooo..
...oQo....oQo...
...oQo....oQo...
....z......z....
................
................
""")
FLAG = _art("""
................
......orrr......
......orrrrr....
......orRRRr....
......orrr......
......oM........
......oM........
......oL........
......oM........
......oL........
......oM........
.....oooo.......
................
................
................
................
""")
HEADSTONE = _art("""
................
................
................
................
....oooooo......
...oLLLLLLo.....
...oLMMMMLo.....
...oLLLLLLo.....
...oLMMMMLo.....
...oLLLLLMo.....
...oLLLLLMo.....
...oooooooo.....
...zzzzzzzz.....
................
................
................
""")
CROSS_STONE = _art("""
................
................
......oo........
.....oLLo.......
...ooLLLLoo.....
...oLLLLLLMo....
...ooLLLLMoo....
.....oLLMo......
.....oLLMo......
.....oLLMo......
....oLLLLMo.....
....oooooooo....
....zzzzzzzz....
................
................
................
""")
IRON_FENCE = _art("""
................
..o...o...o...o.
..o...o...o...o.
.oDo.oDo.oDo.oDo
..D...D...D...D.
oooooooooooooooo
..D...D...D...D.
..D...D...D...D.
..D...D...D...D.
..D...D...D...D.
oooooooooooooooo
..D...D...D...D.
.oDo.oDo.oDo.oDo
..zzzzzzzzzzzzzz
................
................
""")


def golf():
    """Golf pieces painted in the nature palette (grass, sand) over nothing (opaque)."""
    from civic import PAL_NATURE
    def fairway(x, y):
        return 3 if (x // 4) % 2 else 2              # mowed stripes
    def green(x, y, cx=8, cy=8, r=7.5):
        d = math.hypot(x + .5 - cx, y + .5 - cy)
        if d < r - 1:
            return 3 if (x + y) % 3 else 4
        if d < r:
            return 4
        return grass_px(x, y)
    def bunker(x, y):
        d = ((x + .5 - 8) / 7) ** 2 + ((y + .5 - 8) / 5) ** 2
        if d < .8:
            return 5 if (x * 3 + y) % 5 else 6
        if d < 1:
            return 7
        return grass_px(x, y)
    def tee(x, y):
        if 3 <= x <= 12 and 4 <= y <= 11:
            return 3 if (x + y) % 3 else 2
        if 2 <= x <= 13 and 3 <= y <= 12:
            return 4
        return grass_px(x, y)
    t = lambda f: [[f(x, y) for x in range(16)] for y in range(16)]
    return {'fairway': t(fairway), 'golf_green': t(green), 'bunker': t(bunker), 'tee_box': t(tee)}


def conservatory():
    """5 x 3 glass conservatory (props palette): curved glass roof seen from above and a
    framed glass door centred on the middle column (conservatory_22), resting on the ground."""
    W, H = 80, 48
    g = [[0] * W for _ in range(H)]
    O, L, M, D, WH = 1, 2, 3, 4, 6
    def r(x0, y0, x1, y1, v):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if 0 <= x < W and 0 <= y < H:
                    g[y][x] = v
    for y in range(4, 30):
        t = (y - 4) / 26
        x0 = round(6 - 4 * math.sin(t * math.pi))
        for x in range(x0, W - x0):
            v = WH if (x - x0) % 6 == 0 else (L if t < .45 else M)
            if (y - 4) % 6 == 0:
                v = M
            g[y][x] = v
    r(2, 30, W - 3, 32, D)
    r(2, 33, W - 3, 47, L)
    for x in range(6, W - 6, 6):
        if not 33 <= x <= 46:
            r(x, 33, x, 47, M)
    # outline the silhouette (the wall runs to the tile bottom, like Pokemon building fronts)
    s = [row[:] for row in g]
    for y in range(H):
        for x in range(W):
            if s[y][x] and any(not (0 <= x + dx < W and 0 <= y + dy < H) or not s[y + dy][x + dx]
                               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                g[y][x] = O
    # door: dark frame, two glass leaves, open at the bottom so it meets the ground
    r(34, 34, 45, 47, O)
    r(35, 35, 44, 47, D)
    r(36, 36, 39, 44, WH); r(40, 36, 43, 44, WH)
    r(36, 36, 39, 37, L); r(40, 36, 43, 37, L)
    r(39, 36, 40, 47, O)
    r(35, 45, 44, 47, M)                 # kick plates
    return {f'conservatory_{c}{rr}': [row[c * 16:(c + 1) * 16] for row in g[rr * 16:(rr + 1) * 16]]
            for rr in range(3) for c in range(5)}


def zoo_gate():
    """3 x 2 entrance arch with a name panel (props palette)."""
    W, H = 48, 32
    g = [[0] * W for _ in range(H)]
    O, L, M, D, GN, GND, WL, WM = 1, 2, 3, 4, 9, 10, 11, 12
    def r(x0, y0, x1, y1, v):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g[y][x] = v
    for x0 in (3, 39):                     # stone piers
        r(x0, 6, x0 + 6, 29, M); r(x0, 6, x0 + 1, 29, L); r(x0 + 5, 6, x0 + 6, 29, D)
        r(x0 - 1, 5, x0 + 7, 5, O); r(x0 - 1, 5, x0 - 1, 30, O); r(x0 + 7, 5, x0 + 7, 30, O); r(x0 - 1, 30, x0 + 7, 30, O)
    r(2, 1, 45, 9, GN); r(2, 1, 45, 2, GND)   # green name board
    r(1, 0, 46, 0, O); r(1, 10, 46, 10, O); r(1, 0, 1, 10, O); r(46, 0, 46, 10, O)
    r(8, 4, 39, 6, WL)                     # lettering band (name via a sign event)
    return {f'zoo_gate_{c}{rr}': [row[c * 16:(c + 1) * 16] for row in g[rr * 16:(rr + 1) * 16]]
            for rr in range(2) for c in range(3)}


def city_pieces():
    """name -> (grid, palette key, layer, over) ; over = 'water' | 'lawn' | None (opaque)."""
    out = {}
    for k, g in canal().items():
        out[k] = (g, 'street', 'COVERED', 'water')
    out['dock_ns'] = (DOCK_NS, 'props', 'COVERED', 'water')
    out['dock_end'] = (DOCK_END[::-1], 'props', 'COVERED', 'water')   # posts at the water end (north)
    for k, g in golf().items():
        out[k] = (g, 'nature', 'NORMAL', None)
    out['golf_flag'] = (FLAG, 'props', 'COVERED', 'golf_green')
    out['headstone'] = (HEADSTONE, 'props', 'COVERED', 'lawn')
    out['cross_stone'] = (CROSS_STONE, 'props', 'COVERED', 'lawn')
    out['iron_fence'] = (IRON_FENCE, 'props', 'COVERED', 'lawn')
    for k, g in {**conservatory(), **zoo_gate()}.items():
        tall = k.endswith('0')
        out[k] = (g, 'props', 'NORMAL' if tall else 'COVERED', 'lawn')
    return out


# ---------------------------------------------------------------- rural (road palette)
# road palette: 1-4 grass, 5-7 gravel, 8-9 asphalt, 10 white, 11 yellow, 12-13 rail, 14 tie brown, 15 dark
def pumpjack():
    """2 x 2 oil pumpjack: walking beam with horse head, samson post, counterweight."""
    W, H = 32, 32
    g = [[0] * W for _ in range(H)]
    K, Y, R1, R2, T, WH, G2, G3 = 15, 11, 12, 13, 14, 10, 6, 7
    def r(x0, y0, x1, y1, v):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if 0 <= x < W and 0 <= y < H:
                    g[y][x] = v
    r(3, 26, 29, 28, G3); r(3, 26, 29, 26, G2)              # concrete pad
    r(13, 10, 15, 25, R2); r(16, 10, 18, 25, R1)            # samson post (A-frame)
    r(11, 24, 13, 25, K); r(18, 24, 20, 25, K)
    r(3, 7, 26, 9, Y); r(3, 7, 26, 7, WH)                   # walking beam
    r(24, 5, 29, 14, Y); r(24, 5, 29, 5, WH)                # horse head
    r(26, 14, 27, 26, K)                                    # polished rod to the wellhead
    r(4, 12, 10, 21, R1); r(4, 12, 10, 13, R2)              # counterweight crank
    r(6, 14, 8, 19, K)
    r(2, 10, 3, 12, K)
    s = [row[:] for row in g]
    for y in range(H):
        for x in range(W):
            if s[y][x] and s[y][x] not in (G2, G3) and any(
                    not (0 <= x + dx < W and 0 <= y + dy < H) or not s[y + dy][x + dx]
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                g[y][x] = K
    return {f'pumpjack_{c}{rr}': [row[c * 16:(c + 1) * 16] for row in g[rr * 16:(rr + 1) * 16]]
            for rr in range(2) for c in range(2)}


def corral():
    """Three-rail wooden corral fence, horizontal and vertical, plus a corner post."""
    T, K, L = 14, 15, 5
    h = [[0] * 16 for _ in range(16)]
    for y in (4, 8, 12):
        for x in range(16):
            h[y][x] = L
            h[y + 1][x] = T
    for y in range(3, 15):
        h[y][0] = K; h[y][1] = T; h[y][2] = K
    v = [[0] * 16 for _ in range(16)]
    for y in range(16):
        v[y][6] = K; v[y][7] = L; v[y][8] = T; v[y][9] = K
    for y in (0, 8):
        for x in range(5, 11):
            v[y][x] = K
    return {'corral_h': h, 'corral_v': v}


def cow(kind):
    """1 x 1 cow, side view facing east. kind 'holstein' (black and white) or 'angus'."""
    WH, K, T, G = 10, 15, 14, 7
    body, spot = (WH, K) if kind == 'holstein' else (K, K)
    g = [[0] * 16 for _ in range(16)]
    def r(x0, y0, x1, y1, v):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g[y][x] = v
    r(2, 5, 11, 10, body)
    if kind == 'holstein':
        r(4, 6, 6, 8, spot); r(8, 8, 10, 9, spot)
    r(11, 3, 14, 7, body); r(14, 5, 14, 6, T)        # head and muzzle
    r(12, 2, 12, 2, K)                               # ear
    for lx in (3, 5, 9, 10):
        r(lx, 11, lx, 13, K)
    r(1, 5, 1, 8, K)                                 # tail
    s = [row[:] for row in g]
    for y in range(16):
        for x in range(16):
            if s[y][x] and any(not (0 <= x + dx < 16 and 0 <= y + dy < 16) or not s[y + dy][x + dx]
                               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                g[y][x] = K
    for x in range(2, 12):
        g[14][x] = 4
    return g


def rural_pieces():
    out = {}
    out.update(pumpjack())
    out.update(corral())
    out['cow_holstein'] = cow('holstein')
    out['cow_angus'] = cow('angus')
    return out
