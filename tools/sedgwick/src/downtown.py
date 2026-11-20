"""Downtown Wichita: stone office towers (stackable floors) and tan mid-rise blocks
from Rustboro City, the grand Devon Corporation building as a historic hall, and
the Battle Dome as a domed arena. Brick Old Town blocks come from commercial.py.

Rustboro's building palettes (10 = grey stone, 11 = tan) are copied whole into our
slots; the Battle Dome only uses the Emerald primary palettes, which every map
already loads, so it costs no palette slots at all."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orig
from lib import load_jasc, EXP

RB = orig.Source('general', 'rustboro', frlg=False)
BF = orig.Source('general', 'battle_frontier_outside_west', frlg=False)

SLOT_GRAY, SLOT_TAN = 8, 9
RB_PALMAP = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 10: SLOT_GRAY, 11: SLOT_TAN}
BF_PALMAP = {i: i for i in range(6)}
PAL_GRAY = load_jasc(f'{EXP}/data/tilesets/secondary/rustboro/palettes/10.pal')
PAL_TAN = load_jasc(f'{EXP}/data/tilesets/secondary/rustboro/palettes/11.pal')

# ---- grey stone tower: any width, any number of floors
TOWER = {
    'roof0': (0x224, 0x225, 0x226),
    'roof1': (0x236, 0x23e, 0x237),
    'roof2': (0x22c, 0x22d, 0x22e),
    'win':   (0x214, (0x242, 0x215), 0x216),     # middle alternates window / pier
    'plain': (0x214, 0x215, 0x216),
    'base':  (0x21c, 0x21d, 0x21e),
}
TOWER_DOOR_TOP, TOWER_DOOR = 0x217, 0x21f

# ---- tan mid-rise block (Pokemon School style)
TAN = {
    'roof0': (0x220, 0x221, (0x222, 0x223)),     # right end has two pieces
    'roof1': (0x228, 0x229, (0x22a, 0x22b)),
    'roof2': (0x230, 0x231, (0x231, 0x233)),
    'win':   (0x238, (0x23a, 0x239), 0x23b),
    'base':  (0x240, 0x241, 0x243),
}
TAN_DOOR_TOP, TAN_DOOR = 0x227, 0x22f

# ---- fixed blocks
HALL = [[0x288, 0x289, 0x289, 0x28b, 0x28c, 0x28c, 0x28d, 0x289, 0x289, 0x28a],
        [0x290, 0x291, 0x291, 0x293, 0x294, 0x294, 0x295, 0x291, 0x291, 0x292],
        [0x298, 0x299, 0x29a, 0x28e, 0x28f, 0x296, 0x297, 0x29a, 0x29a, 0x29b],
        [0x2a0, 0x2a1, 0x2a2, 0x29c, 0x29d, 0x29d, 0x29e, 0x2a2, 0x2a2, 0x2a3],
        [0x298, 0x299, 0x29a, 0x2a4, 0x2a5, 0x2a5, 0x2a6, 0x29a, 0x29a, 0x29b],
        [0x2a0, 0x2a1, 0x2a2, 0x29c, 0x29d, 0x29d, 0x29e, 0x2a2, 0x2a2, 0x2a3],
        [0x2a8, 0x2a9, 0x2a9, 0x2a4, 0x2a5, 0x2a5, 0x2a6, 0x2aa, 0x2aa, 0x2ab],
        [0x2b0, 0x2b1, 0x2b1, 0x2ac, 0x2ad, 0x2ad, 0x2ae, 0x2b2, 0x2b2, 0x2b3],
        [None, None, None, 0x2b4, 0x2b5, 0x2b5, 0x2b6, None, None, None]]
HALL_DOORS = {0x2b5}

ARENA_X0, ARENA_Y0 = 13, 5
ARENA = None   # filled from the Battle Frontier layout below


PLAZA = {0x268, 0x269, 0x26a, 0x26b, 0x270, 0x271, 0x272, 0x273, 0x279}


def _arena_ids():
    import json, struct
    L = json.load(open(f'{EXP}/data/layouts/layouts.json'))['layouts']
    lay = [l for l in L if l['id'] == 'LAYOUT_BATTLE_FRONTIER_OUTSIDE_WEST'][0]
    W = lay['width']
    b = open(f"{EXP}/{lay['blockdata_filepath']}", 'rb').read()
    ids = [struct.unpack('<H', b[i:i + 2])[0] & 0x3ff for i in range(0, len(b), 2)]
    rows = []
    for y in range(5, 18):
        row = []
        for x in range(13, 26):
            m = ids[y * W + x]
            # plain primary ground and the checkered plaza pieces -> our lawn
            row.append(None if m < 0x200 or m in PLAZA else m)
        rows.append(row)
    return rows


ARENA = _arena_ids()
ARENA_DOORS = {0x28a}


def all_rb_ids():
    s = set()
    for spec in list(TOWER.values()) + list(TAN.values()):
        for part in spec:
            s.update(part if isinstance(part, tuple) else (part,))
    s |= {TOWER_DOOR_TOP, TOWER_DOOR, TAN_DOOR_TOP, TAN_DOOR}
    s |= {m for row in HALL for m in row if m}
    return sorted(s)


def rb_piece(m):
    return orig.piece_indexed(RB, m, RB_PALMAP, ground_pals=(8,))


def bf_piece(m):
    return orig.piece_indexed(BF, m, BF_PALMAP, ground_pals=())


def tower_plan(width, floors, door_at=None):
    """Grey tower `width` metatiles wide (>= 3) with `floors` window rows."""
    inner = width - 2
    if door_at is None:
        door_at = inner // 2 if (inner // 2) % 2 == 1 else max(1, inner // 2 - 1)
    def row(spec, alt=False):
        l, mid, r = spec
        cells = []
        for i in range(inner):
            if isinstance(mid, tuple):
                cells.append(mid[i % 2])
            else:
                cells.append(mid)
        return [l] + cells + [r]
    rows = [row(TOWER['roof0']), row(TOWER['roof1']), row(TOWER['roof2'])]
    for f in range(floors):
        rows.append(row(TOWER['plain'] if f % 3 == 2 else TOWER['win']))
    base = row(TOWER['base'])
    base[1 + door_at] = TOWER_DOOR
    rows[-1][1 + door_at] = TOWER_DOOR_TOP
    rows.append(base)
    return rows


def tan_plan(width, floors=2, door_at=None):
    inner = width - 3
    if door_at is None:
        door_at = inner // 2 + 1
    rows = []
    for key in ('roof0', 'roof1', 'roof2'):
        l, mid, r = TAN[key]
        rows.append([l] + [mid] * inner + list(r))
    for _ in range(floors):
        l, mid, r = TAN['win']
        rows.append([l] + [mid[i % 2] for i in range(inner + 1)] + [r])
    l, mid, r = TAN['base']
    base = [l] + [mid] * (inner + 1) + [r]
    base[door_at] = TAN_DOOR
    rows[-1][door_at] = TAN_DOOR_TOP
    rows.append(base)
    return rows


# ---------------------------------------------------------------- school sports field (props palette)
def sports_field(wt=8, ht=5):
    """Football field inside a running track, as top-layer art over lawn (props palette).
    Index roles from props.PAL_PROPS: 1 outline, 6 white, 7/8 red, 9/10 green."""
    W, H = wt * 16, ht * 16
    g = [[0] * W for _ in range(H)]
    import math
    cx, cy = W / 2, H / 2
    rx_out, ry_out = W / 2 - 1, H / 2 - 1
    def in_stadium(x, y, rx, ry):
        # straight sides with semicircular ends (a real track shape)
        r = ry
        straight = rx - r
        dx = abs(x - cx)
        if dx <= straight:
            return abs(y - cy) <= r
        return math.hypot(dx - straight, y - cy) <= r
    for y in range(H):
        for x in range(W):
            X, Y = x + .5, y + .5
            if in_stadium(X, Y, rx_out, ry_out):
                g[y][x] = 7 if (y % 4) else 8                 # rubber track with lane lines
                if not in_stadium(X, Y, rx_out - 1, ry_out - 1):
                    g[y][x] = 1
                if in_stadium(X, Y, rx_out - 7, ry_out - 7):
                    g[y][x] = 6                                # curb inside the track
                if in_stadium(X, Y, rx_out - 8, ry_out - 8):
                    stripe = int((x - (cx - (rx_out - 8))) // 6) % 2
                    g[y][x] = 9 if stripe else 10              # mowed turf stripes
    # yard lines and end zones
    left, right = int(cx - (rx_out - 8 - ry_out + 8)) , int(cx + (rx_out - 8 - ry_out + 8))
    for x in range(left, right + 1, 6):
        for y in range(int(cy - ry_out + 9), int(cy + ry_out - 8)):
            if g[y][x] in (9, 10):
                g[y][x] = 6
    return {f'field_{c}{r}': [row[c * 16:(c + 1) * 16] for row in g[r * 16:(r + 1) * 16]]
            for r in range(ht) for c in range(wt)}
