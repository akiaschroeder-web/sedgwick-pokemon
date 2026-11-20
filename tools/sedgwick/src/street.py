"""Streets: asphalt, curbs, sidewalks, lane paint, and shaped pieces (45 deg and
shallow diagonals, curves, cul-de-sac bulbs) painted from analytic masks so the
GIS road network can be drawn without being grid-aligned.

Palette slot 7 ('street')."""
import math
from lib import blank, copy, hflip, vflip

PAL_STREET = [(255, 0, 255),
    (164, 213, 197), (115, 197, 164), (65, 180, 131), (24, 164, 106),   # 1-4 Hoenn grass (exact)
    (230, 230, 222), (205, 205, 197), (172, 172, 164), (123, 123, 131), # 5-8 concrete L C S X
    (98, 98, 106), (74, 74, 85),                                        # 9-10 asphalt A B
    (238, 238, 238), (238, 205, 82), (189, 156, 57),                    # 11 white paint, 12-13 yellow paint
    (57, 57, 74), (115, 115, 123)]                                      # 14 crack/outline, 15 worn asphalt

GL, GR, G3, G4 = 1, 2, 3, 4
CL, CC, CS, CX = 5, 6, 7, 8
A, B = 9, 10
WP, YP, YS = 11, 12, 13
KD, AW = 14, 15

# Exact Hoenn general-tileset grass (metatile 0x001) so our edges blend seamlessly.
GRASS = [[int(c) for c in r] for r in """
2223222122232222
2211222222222223
2311222222222222
2222222221222222
2222222222221122
2222222223221122
2122322222222223
2222222222222222
2223222222232221
2222222322112222
2222222223112222
2122222222222222
2222112222222222
2322112222222222
2222222321223222
2222222222222222""".split()]

ASPH = [[{'A': A, 'B': B, 'X': AW}[c] for c in r] for r in """
AAAAAAAAAAAAAAAA
AAXAAAAAAABAAAAA
AAAAAAAAAAAAAAAA
AAAAABAAAAAAAXAA
AAAAAAAAAAAAAAAA
ABAAAAAAAXAAAAAA
AAAAAAAAAAAAAAAA
AAAAAAAAAAAABAAA
AAAXAAAAAAAAAAAA
AAAAAAABAAAAAAAA
AAAAAAAAAAAAAAAA
ABAAAAAAAAAXAAAA
AAAAAAAAAAAAAAAA
AAAAAXAAAAAAAAAB
AAAAAAAAAAAAAAAA
AAAAAAAAABAAAAAA""".split()]

def grass_px(x, y):
    return GRASS[y % 16][x % 16]

def asph_px(x, y):
    return ASPH[y % 16][x % 16]

def conc_px(x, y):
    # concrete with a few speckles, 8px slab joints handled by caller
    return CS if ((x * 7 + y * 13) % 29 == 0) else CC


# ---------------------------------------------------------------- generic painter
def shade(d, X, Y, sidewalk=True, joints=None):
    """Colour for a pixel at signed distance d from the curb line
    (d < 0 road side, d >= 0 block side). Matches the straight pieces exactly:
    asphalt | face | lip | sidewalk (CS, concrete x6, CL lip, CX) | grass."""
    if d < -2:
        return asph_px(X, Y)
    if d < -1:
        return CX
    if d < 0:
        return CL
    if not sidewalk:
        return grass_px(X, Y)
    if d < 1:
        return CS
    if d < 7:
        if joints and joints(X, Y):
            return CS
        return conc_px(X, Y)
    if d < 8:
        return CL
    if d < 9:
        return CX
    return grass_px(X, Y)


def paint(region_w, region_h, sdf, sidewalk=True, joints=None, ox=0, oy=0):
    """Paint region_w x region_h metatiles. sdf(px,py): negative on the road side.
    ox, oy offset the texture so pieces line up with their neighbours."""
    out = {}
    for row in range(region_h):
        for col in range(region_w):
            g = blank()
            for y in range(16):
                for x in range(16):
                    X, Y = col * 16 + x, row * 16 + y
                    g[y][x] = shade(sdf(X + 0.5, Y + 0.5), X + ox, Y + oy, sidewalk, joints)
            out[(col, row)] = g
    return out


def one(sdf, **kw):
    return paint(1, 1, sdf, **kw)[(0, 0)]


def mirrors(sdf):
    """The four mirror images of an sdf defined for one orientation (inside a 16px tile)."""
    return {
        '': sdf,
        'h': lambda px, py: sdf(16 - px, py),
        'v': lambda px, py: sdf(px, 16 - py),
        'hv': lambda px, py: sdf(16 - px, 16 - py),
    }


def is_plain(g):
    flat = {v for r in g for v in r}
    return flat <= {A, B, AW} or flat <= {GL, GR, G3, G4}


def collect(prefix, region_w, region_h, sdf, **kw):
    """Paint a region and keep every tile that isn't plain grass or plain asphalt."""
    out = {}
    for (c, r), g in paint(region_w, region_h, sdf, **kw).items():
        if not is_plain(g):
            out[f'{prefix}_{c}{r}'] = g
    return out


# ---------------------------------------------------------------- straight pieces
def straight():
    t = {}
    t['asphalt'] = [[asph_px(x, y) for x in range(16)] for y in range(16)]
    jh = lambda X, Y: X % 8 == 7      # slab joints across an E-W sidewalk
    jv = lambda X, Y: Y % 8 == 7
    # block (sidewalk + lawn) on the named side, road on the other
    t['road_edge_n'] = one(lambda px, py: 12 - py, joints=jh)
    t['road_edge_s'] = one(lambda px, py: py - 4, joints=jh)
    t['road_edge_w'] = one(lambda px, py: 12 - px, joints=jv)
    t['road_edge_e'] = one(lambda px, py: px - 4, joints=jv)

    def paint_over(base, fn):
        g = copy(base)
        for y in range(16):
            for x in range(16):
                v = fn(x, y)
                if v:
                    g[y][x] = v
        return g
    asp = t['asphalt']
    t['center_yellow_h'] = paint_over(asp, lambda x, y: YP if y in (6, 9) else (YS if y in (7, 10) else 0))
    t['center_yellow_v'] = paint_over(asp, lambda x, y: YP if x in (6, 9) else (YS if x in (7, 10) else 0))
    t['lane_dash_h'] = paint_over(asp, lambda x, y: WP if (y == 7 and 2 <= x <= 11) else 0)
    t['lane_dash_v'] = paint_over(asp, lambda x, y: WP if (x == 7 and 2 <= y <= 11) else 0)
    t['crosswalk_ew'] = paint_over(asp, lambda x, y: WP if (y % 4 in (1, 2)) and 1 <= x <= 14 else 0)
    t['crosswalk_ns'] = paint_over(asp, lambda x, y: WP if (x % 4 in (1, 2)) and 1 <= y <= 14 else 0)
    t['stop_bar_h'] = paint_over(asp, lambda x, y: WP if y in (7, 8) else 0)
    t['stop_bar_v'] = paint_over(asp, lambda x, y: WP if x in (7, 8) else 0)
    return t


def sd_corner(px, py, cx=12, cy=12, r=5):
    """Rounded block corner: block occupies x<cx, y<cy. Negative = road."""
    qx, qy = px - cx + r, py - cy + r
    out = math.hypot(max(qx, 0), max(qy, 0))
    ins = min(max(qx, qy), 0)
    return -(out + ins - r)


def corners():
    """Block corners where the sidewalk wraps around (block on the named side)."""
    out = {}
    for name, f in mirrors(sd_corner).items():
        out['block_corner_' + {'': 'nw', 'h': 'ne', 'v': 'sw', 'hv': 'se'}[name]] = one(f)
    # inner corners: road on the named side only at the corner (where a driveway-less
    # block edge meets a perpendicular street end)
    return out


# ---------------------------------------------------------------- shaped pieces
def diag45():
    """45 degree road edge, block to the NW (3 phases along the diagonal).
    Other orientations are mirror images (tile flips, no extra tile memory)."""
    base = collect('d', 3, 3, lambda px, py: (48 - (px + py)) / math.sqrt(2))
    keep = {}
    for k, g in sorted(base.items()):
        c, r = int(k[-2]), int(k[-1])
        keep.setdefault(c + r, g)
    out = {}
    for ph, g in keep.items():
        out[f'diag45_nw_{ph}'] = g
        out[f'diag45_ne_{ph}'] = hflip(g)
        out[f'diag45_sw_{ph}'] = vflip(g)
        out[f'diag45_se_{ph}'] = hflip(vflip(g))
    return out


def diag21():
    """2:1 slope (drops 1 tile every 2 tiles), block to the north-west side."""
    out = {}
    reg = paint(4, 3, lambda px, py: ((24 + px / 2) - py) / 1.118)
    for (c, r), g in reg.items():
        if is_plain(g):
            continue
        out[f'diag21_n_{c}{r}'] = g
        out[f'diag21_nrev_{3 - c}{r}'] = hflip(g)
        out[f'diag21_s_{c}{2 - r}'] = vflip(g)
        out[f'diag21_srev_{3 - c}{2 - r}'] = hflip(vflip(g))
    return out


def curves():
    """90 degree street bends with sidewalks on both sides, sized so the ends line
    up with the straight pieces (curb-to-curb 40px). Ri = inner curb radius.
    Orientation names the corner the bend's centre sits in; other corners are flips."""
    out = {}
    for Ri in (28, 44):
        Ro = Ri + 40
        n = math.ceil((Ro + 9) / 16)
        def sdf(px, py, Ri=Ri, Ro=Ro):
            r = math.hypot(px, py)
            return max(Ri - r, r - Ro)
        for (c, w), g in paint(n, n, sdf).items():
            if is_plain(g):
                continue
            out[f'bend{Ri}_nw_{c}{w}'] = g
            out[f'bend{Ri}_ne_{n - 1 - c}{w}'] = hflip(g)
            out[f'bend{Ri}_sw_{c}{n - 1 - w}'] = vflip(g)
            out[f'bend{Ri}_se_{n - 1 - c}{n - 1 - w}'] = hflip(vflip(g))
    return out


def culdesac():
    """6x6 turnaround bulb opening north onto a standard street
    (edge, asphalt, asphalt, edge = columns 1-4). Right half mirrors the left."""
    cx, cy, R, hw = 48.0, 52.0, 40.0, 20.0
    def sdf(px, py):
        d = math.hypot(px - cx, py - cy) - R
        if py < cy:
            d = min(d, abs(px - cx) - hw)
        return d
    reg = paint(6, 6, sdf)
    out = {}
    for (c, r), g in reg.items():
        if c >= 3:
            g = hflip(reg[(5 - c, r)])
        if not is_plain(g):
            out[f'culdesac_{c}{r}'] = g
    return out


def orient(g, hf=False, vf=False):
    if hf:
        g = hflip(g)
    if vf:
        g = vflip(g)
    return g


def driveways():
    """Two-tile-wide concrete driveway from a garage to the street.
    drive_l/r = on the lawn; apron_l/r = crossing the sidewalk with a flush curb
    (replaces road_edge_n where the driveway meets a street to its south)."""
    def body(side):
        g = blank()
        for y in range(16):
            for x in range(16):
                v = CS if y == 15 else conc_px(x, y)
                if side == 'l':
                    if x < 3:
                        v = grass_px(x, y)
                    elif x == 3:
                        v = CX
                    elif x == 4:
                        v = CL
                else:
                    if x > 12:
                        v = grass_px(x, y)
                    elif x == 12:
                        v = CX
                    elif x == 11:
                        v = CS
                g[y][x] = v
        return g
    def apron(side):
        g = copy(body(side))
        edge = one(lambda px, py: 12 - py, joints=lambda X, Y: X % 8 == 7)
        for y in range(16):
            for x in range(16):
                if y >= 3:
                    g[y][x] = edge[y][x]
                if y == 13:
                    g[y][x] = CS          # flush ramp instead of a curb face
                if 3 <= y <= 4 and ((side == 'l' and x > 4) or (side == 'r' and x < 11)):
                    g[y][x] = CC          # driveway concrete runs over the sidewalk edge
        return g
    return {'drive_l': body('l'), 'drive_r': body('r'),
            'drive_apron_l': apron('l'), 'drive_apron_r': apron('r')}


def metatiles():
    out = {}
    out.update(driveways())
    out.update(straight())
    out.update(corners())
    out.update(diag45())
    out.update(diag21())
    out.update(curves())
    out.update(culdesac())
    return {k: (v, 'MB_NORMAL') for k, v in out.items()}
