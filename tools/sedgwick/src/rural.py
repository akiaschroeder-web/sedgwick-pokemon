"""Rural Sedgwick County: section-line gravel roads, a two-lane paved highway,
railroad, row crops, and farm buildings (barn, silo, machine shed, grain elevator).

Palettes (secondary slots):
  6 field   - wheat / stubble (lib.PAL_FIELD)
  7 milo    - same roles as field, rust-red heads; soil colours in 10-15
  8 corn    - same roles as field, green plants; soil colours in 10-15
  9 road    - gravel, asphalt, paint, rail
 10 farm    - barn red, white trim, metal, concrete
 11 house   - farmhouse colours for the house kit
 12 props   - props.PAL_PROPS
"""
import math
from lib import blank, copy, hflip, vflip
import street

GRASS = street.GRASS
def grass(x, y):
    return GRASS[y % 16][x % 16]

def hsh(x, y, k=0):
    return ((x * 73856093) ^ (y * 19349663) ^ (k * 83492791)) & 0xffff

# ---------------------------------------------------------------- palettes
SOIL = [(156, 115, 82), (123, 90, 65), (90, 65, 49), (180, 139, 98), (65, 49, 41), (106, 148, 74)]
PAL_MILO = [(255, 0, 255), (164, 213, 197), (115, 197, 164), (65, 180, 131), (24, 164, 106),
            (238, 164, 115), (213, 123, 82), (180, 90, 65), (139, 65, 57), (98, 49, 49)] + SOIL
PAL_CORN = [(255, 0, 255), (164, 213, 197), (115, 197, 164), (65, 180, 131), (24, 164, 106),
            (222, 230, 131), (148, 205, 90), (90, 164, 65), (57, 123, 57), (32, 82, 49)] + SOIL
S_MID, S_DARK, S_DEEP, S_LIGHT, S_OUT, S_LEAF = 10, 11, 12, 13, 14, 15

PAL_ROAD = [(255, 0, 255), (164, 213, 197), (115, 197, 164), (65, 180, 131), (24, 164, 106),
            (222, 205, 172), (197, 180, 148), (156, 139, 115),      # 5-7 gravel L/M/D
            (98, 98, 106), (74, 74, 85),                            # 8-9 asphalt
            (238, 238, 238), (238, 205, 82),                        # 10 white, 11 yellow
            (205, 205, 222), (98, 98, 115),                         # 12-13 rail light/dark
            (123, 90, 65), (57, 49, 49)]                            # 14 tie, 15 dark
GL_, GM, GD = 5, 6, 7
RA, RB, RW, RY, RL, RD, TIE, RK = 8, 9, 10, 11, 12, 13, 14, 15

PAL_FARM = [(255, 0, 255), (49, 41, 49),
            (222, 90, 74), (189, 57, 57), (139, 41, 49),            # 2-4 barn red
            (246, 246, 238),                                        # 5 white
            (205, 213, 222), (164, 172, 189), (115, 123, 139),      # 6-8 metal
            (230, 222, 205), (197, 189, 172), (156, 148, 131),      # 9-11 concrete
            (65, 74, 98), (156, 115, 74),                           # 12 dark opening, 13 wood
            (115, 197, 164), (164, 213, 197)]                       # 14-15 grass
F_O, F_RL, F_RM, F_RD, F_W, F_ML, F_MM, F_MD, F_CL, F_CM, F_CD, F_K, F_WD, F_G, F_GS = range(1, 16)

PAL_FARMHOUSE = [(255, 0, 255), (57, 57, 74),
                 (115, 164, 123), (82, 131, 98), (57, 106, 82), (41, 74, 65),   # green metal roof
                 (255, 255, 255), (230, 230, 230), (197, 197, 205),            # white siding
                 (255, 255, 255), (172, 222, 255), (98, 148, 222), (164, 49, 57), (148, 148, 156),
                 (115, 197, 164), (164, 213, 197)]


# ---------------------------------------------------------------- band painter
def paint(region_w, region_h, fn):
    out = {}
    for r in range(region_h):
        for c in range(region_w):
            g = blank()
            for y in range(16):
                for x in range(16):
                    g[y][x] = fn(c * 16 + x, r * 16 + y)
            out[(c, r)] = g
    return out

def one(fn):
    return paint(1, 1, fn)[(0, 0)]

def transpose(fn):
    return lambda x, y: fn(y, x)


# ---------------------------------------------------------------- gravel roads
def gravel_px(x, y):
    h = hsh(x, y) % 23
    if h == 0:
        return GD
    if h in (1, 2, 3):
        return GL_
    return GM

def gravel_band(d, x, y):
    """d = distance into the road from its edge (negative = outside)."""
    if d < 0:
        return grass(x, y)
    if d < 1.5:
        return GL_ if hsh(x, y, 2) % 3 else grass(x, y)   # loose gravel spilling onto the verge
    return gravel_px(x, y)

def gravel():
    t = {}
    t['gravel'] = one(gravel_px)
    t['gravel_edge_n'] = one(lambda x, y: gravel_band(y - 4, x, y))           # verge north of road
    t['gravel_edge_s'] = one(lambda x, y: gravel_band(12 - y, x, y))
    t['gravel_edge_w'] = one(lambda x, y: gravel_band(x - 4, x, y))
    t['gravel_edge_e'] = one(lambda x, y: gravel_band(12 - x, x, y))
    # rounded outer corners where two gravel roads meet (verge in the named corner)
    for tag, (cx, cy) in {'nw': (0, 0), 'ne': (16, 0), 'sw': (0, 16), 'se': (16, 16)}.items():
        t[f'gravel_corner_{tag}'] = one(lambda x, y, cx=cx, cy=cy: gravel_band(math.hypot(x + .5 - cx, y + .5 - cy) - 4, x, y))
    # inner corners (road on the named corner's diagonal side only)
    for tag, (cx, cy) in {'nw': (0, 0), 'ne': (16, 0), 'sw': (0, 16), 'se': (16, 16)}.items():
        t[f'gravel_inner_{tag}'] = one(lambda x, y, cx=cx, cy=cy: gravel_band(12 - math.hypot(x + .5 - cx, y + .5 - cy), x, y))
    return t


# ---------------------------------------------------------------- two-lane highway (K-42, US-54 style)
def hwy_band(d, x, y, along):
    """d = distance from the outer shoulder edge into the pavement."""
    if d < 0:
        return grass(x, y)
    if d < 4:
        return gravel_px(x, y)                     # gravel shoulder
    if d < 5:
        return RW                                  # white fog line
    return RA if hsh(x, y, 5) % 17 else RB

def highway():
    t = {}
    asp = lambda x, y: RA if hsh(x, y, 5) % 17 else RB
    t['hwy_asphalt'] = one(asp)
    t['hwy_edge_n'] = one(lambda x, y: hwy_band(y - 2, x, y, x))
    t['hwy_edge_s'] = one(lambda x, y: hwy_band(13 - y, x, y, x))
    t['hwy_edge_w'] = one(lambda x, y: hwy_band(x - 2, x, y, y))
    t['hwy_edge_e'] = one(lambda x, y: hwy_band(13 - x, x, y, y))
    # centre line: solid yellow (no passing) and dashed (passing allowed)
    t['hwy_center_h'] = one(lambda x, y: RY if y in (7, 8) else asp(x, y))
    t['hwy_center_v'] = one(lambda x, y: RY if x in (7, 8) else asp(x, y))
    t['hwy_center_dash_h'] = one(lambda x, y: RY if y in (7, 8) and x % 16 < 9 else asp(x, y))
    t['hwy_center_dash_v'] = one(lambda x, y: RY if x in (7, 8) and y % 16 < 9 else asp(x, y))
    # gravel road meeting the highway shoulder (gravel to the north / south)
    t['hwy_gravel_join_n'] = one(lambda x, y: gravel_px(x, y) if y < 6 else hwy_band(y - 2, x, y, x) if y >= 6 else 0)
    t['hwy_gravel_join_s'] = one(lambda x, y: gravel_px(x, y) if y > 9 else hwy_band(13 - y, x, y, x))
    return t


# ---------------------------------------------------------------- railroad
def rail_px(u, v):
    """u along the track, v across (0..15). Rails at v=4,5 and v=10,11."""
    if v < 1 or v > 14:
        return None
    tie = (u % 4) in (0, 1) and 2 <= v <= 13
    if v in (4, 10):
        return RL
    if v in (5, 11):
        return RD
    if tie:
        return TIE if (u % 4) == 0 else RK
    return GD if hsh(u, v, 9) % 5 == 0 else GM      # ballast

def railroad():
    t = {}
    t['rail_h'] = one(lambda x, y: rail_px(x, y) or grass(x, y))
    t['rail_v'] = one(lambda x, y: rail_px(y, x) or grass(x, y))
    # road crossings: rubber/timber panels with the rails showing
    t['rail_x_gravel_h'] = one(lambda x, y: (RL if x in (4, 10) else RD if x in (5, 11) else gravel_px(x, y)))
    t['rail_x_gravel_v'] = one(lambda x, y: (RL if y in (4, 10) else RD if y in (5, 11) else gravel_px(x, y)))
    t['rail_x_asphalt_h'] = one(lambda x, y: (RL if x in (4, 10) else RD if x in (5, 11) else (RA if hsh(x, y, 5) % 17 else RB)))
    t['rail_x_asphalt_v'] = one(lambda x, y: (RL if y in (4, 10) else RD if y in (5, 11) else (RA if hsh(x, y, 5) % 17 else RB)))
    return t


# ---------------------------------------------------------------- soil and low crops (milo/corn palettes)
def plowed():
    return one(lambda x, y: (S_DARK if y % 4 == 3 else S_LIGHT if y % 4 == 0 and hsh(x, y) % 3 == 0 else S_MID))

def soybeans():
    def f(x, y):
        r = y % 8
        if r in (0, 7):
            return S_DARK if r == 7 else S_MID
        # rounded bushes along the row
        k = (x + (y // 8) * 3) % 6
        if r == 1 and k in (1, 2, 3):
            return 1
        if r in (2, 3, 4, 5):
            if k == 0:
                return 4 if r > 3 else 3
            return 3 if (x + y) % 3 == 0 else 2 if r < 4 else 3
        return 4
    return one(f)

def soybeans_edge(side):
    base = soybeans()
    g = copy(base)
    for y in range(16):
        for x in range(16):
            if (side == 'n' and y < 4) or (side == 's' and y > 11):
                g[y][x] = grass(x, y)
    return g


# ---------------------------------------------------------------- drawing canvas for buildings
class Pic:
    def __init__(self, w, h):
        self.w, self.h = w * 16, h * 16
        self.tw, self.th = w, h
        self.p = [[F_G if GRASS[y % 16][x % 16] != 1 else F_GS for x in range(self.w)] for y in range(self.h)]

    def rect(self, x0, y0, x1, y1, c):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                self.p[y][x] = c

    def box(self, x0, y0, x1, y1, fill, outline=F_O):
        self.rect(x0, y0, x1, y1, outline)
        self.rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, fill)

    def hline(self, x0, x1, y, c):
        self.rect(x0, y, x1, y, c)

    def vline(self, x, y0, y1, c):
        self.rect(x, y0, x, y1, c)

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = c

    def line(self, x0, y0, x1, y1, c):
        n = max(abs(x1 - x0), abs(y1 - y0))
        for i in range(n + 1):
            self.px(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n), c)

    def tiles(self, prefix):
        out = {}
        for r in range(self.th):
            for c in range(self.tw):
                out[f'{prefix}_{c}{r}'] = [row[c * 16:(c + 1) * 16] for row in self.p[r * 16:(r + 1) * 16]]
        return out


def barn():
    """4 wide x 4 tall red gambrel barn, front view."""
    P = Pic(4, 4)
    # gambrel roof outline: steep lower slopes, shallow upper
    pts_l = [(2, 30), (10, 12), (32, 4)]
    for y in range(4, 31):
        # half width at height y
        if y >= 12:
            hw = 22 + (y - 12) * 8 / 18
        else:
            hw = 0 + (y - 4) * 22 / 8
        x0, x1 = round(32 - hw), round(31 + hw)
        P.hline(x0, x1, y, F_MM)
        P.px(x0, y, F_O); P.px(x1, y, F_O)
        if (y - 4) % 3 == 0:
            P.hline(x0 + 1, x1 - 1, y, F_ML)
    P.hline(9, 54, 12, F_MD)
    P.hline(1, 62, 31, F_O)
    # walls
    P.box(3, 31, 60, 61, F_RM)
    for x in range(5, 59, 4):
        P.vline(x, 32, 60, F_RD)              # board-and-batten
    P.vline(4, 32, 60, F_RL)
    # loft door
    P.box(26, 34, 37, 44, F_RL)
    P.line(27, 35, 36, 43, F_W); P.line(36, 35, 27, 43, F_W)
    P.rect(26, 34, 37, 34, F_W); P.rect(26, 44, 37, 44, F_W)
    P.vline(26, 34, 44, F_W); P.vline(37, 34, 44, F_W)
    # big sliding doors with white X trim
    P.box(18, 47, 45, 61, F_RM)
    P.rect(18, 47, 45, 48, F_W); P.vline(18, 47, 61, F_W); P.vline(45, 47, 61, F_W); P.vline(31, 47, 61, F_W); P.vline(32, 47, 61, F_W)
    P.line(19, 49, 30, 60, F_W); P.line(30, 49, 19, 60, F_W)
    P.line(33, 49, 44, 60, F_W); P.line(44, 49, 33, 60, F_W)
    P.hline(3, 60, 62, F_O)
    # corner trim
    P.vline(3, 31, 61, F_W); P.vline(60, 31, 61, F_W)
    return P.tiles('barn')


def silo():
    """2 wide x 5 tall concrete stave silo with a metal dome."""
    P = Pic(2, 5)
    cx = 16
    for y in range(6, 18):
        hw = round(13 * math.sqrt(max(0, 1 - ((17 - y) / 12) ** 2)))
        for x in range(cx - hw, cx + hw):
            t = (x - (cx - hw)) / max(1, 2 * hw)
            P.px(x, y, F_ML if t < .35 else F_MM if t < .75 else F_MD)
        P.px(cx - hw - 1, y, F_O); P.px(cx + hw, y, F_O)
    P.hline(cx - 2, cx + 1, 5, F_O)
    for y in range(18, 78):
        for x in range(3, 29):
            t = (x - 3) / 26
            c = F_CL if t < .3 else F_CM if t < .72 else F_CD
            if (y - 18) % 6 == 0:
                c = F_CD if t > .5 else F_CM          # steel hoops
            P.px(x, y, c)
        P.px(2, y, F_O); P.px(29, y, F_O)
    P.hline(2, 29, 18, F_O)
    # chute / ladder
    for y in range(20, 76, 3):
        P.hline(22, 24, y, F_MD)
    P.vline(22, 20, 76, F_MD); P.vline(24, 20, 76, F_MD)
    P.hline(2, 29, 78, F_O)
    return P.tiles('silo')


def machine_shed():
    """5 wide x 3 tall corrugated metal shed with a big roll-up door."""
    P = Pic(5, 3)
    for y in range(6, 18):
        P.hline(1, 78, y, F_ML if y % 2 else F_MM)
    P.hline(0, 79, 5, F_O); P.hline(0, 79, 18, F_O)
    for y in range(19, 46):
        for x in range(2, 78):
            P.px(x, y, F_MM if x % 3 else F_MD)
    P.vline(1, 18, 46, F_O); P.vline(78, 18, 46, F_O)
    P.box(10, 24, 46, 46, F_ML)
    for y in range(26, 46, 3):
        P.hline(11, 45, y, F_MD)
    P.box(56, 30, 64, 46, F_RM)                 # walk-in door
    P.px(62, 38, F_W)
    P.hline(1, 78, 46, F_O)
    return P.tiles('shed')


def grain_elevator():
    """6 wide x 7 tall concrete elevator: four bins with a taller headhouse."""
    P = Pic(6, 7)
    # headhouse
    P.box(36, 2, 60, 30, F_CM)
    P.rect(37, 3, 59, 4, F_CL)
    for y in (10, 18, 26):
        P.rect(42, y, 45, y + 3, F_K); P.rect(51, y, 54, y + 3, F_K)
    P.vline(59, 5, 29, F_CD)
    # bins: four cylinders side by side
    for i in range(4):
        x0 = 2 + i * 23
        for y in range(22, 106):
            for x in range(x0, x0 + 22):
                t = (x - x0) / 21
                c = F_CL if t < .3 else F_CM if t < .75 else F_CD
                P.px(x, y, c)
            P.px(x0 - 1, y, F_O)
        P.vline(x0 + 22, 22, 106, F_O)
        P.hline(x0, x0 + 21, 22, F_O)
        P.hline(x0 + 2, x0 + 19, 21, F_O)
        P.hline(x0 + 1, x0 + 20, 23, F_CL)
    # gallery across the top of the bins
    P.box(0, 16, 95, 22, F_CM)
    P.hline(1, 94, 17, F_CL)
    # lettering band (town name goes in a sign event, not baked in)
    P.box(10, 46, 85, 54, F_W)
    P.hline(1, 94, 106, F_O)
    # ground-level scale house
    P.box(66, 92, 95, 107, F_RM)
    P.rect(70, 97, 76, 103, F_K)
    return P.tiles('elevator')


def hay_bales():
    P = Pic(1, 1)
    for cx in (5, 11):
        for y in range(5, 14):
            for x in range(cx - 4, cx + 4):
                if (x - cx + .5) ** 2 / 16 + (y - 9.5) ** 2 / 20 < 1:
                    P.px(x, y, F_WD if (x + y) % 3 else F_CD)
        P.line(cx - 2, 7, cx - 2, 12, F_CL)
    return {'hay_bales': P.p}


def metatiles():
    """name -> (grid, palette_key, behaviour, passable)"""
    out = {}
    for k, g in gravel().items():
        out[k] = (g, 'road', 'MB_NORMAL', True)
    for k, g in highway().items():
        out[k] = (g, 'road', 'MB_NORMAL', True)
    for k, g in railroad().items():
        out[k] = (g, 'road', 'MB_NORMAL', True)
    out['plowed'] = (plowed(), 'milo', 'MB_NORMAL', True)
    out['soybeans'] = (soybeans(), 'milo', 'MB_NORMAL', True)
    out['soybeans_n'] = (soybeans_edge('n'), 'milo', 'MB_NORMAL', True)
    out['soybeans_s'] = (soybeans_edge('s'), 'milo', 'MB_NORMAL', True)
    for name, fn in (('barn', barn), ('silo', silo), ('shed', machine_shed), ('elevator', grain_elevator)):
        for k, g in fn().items():
            out[k] = (g, 'farm', 'MB_NORMAL', False)
    for k, g in hay_bales().items():
        out[k] = (g, 'farm', 'MB_NORMAL', False)
    return out
