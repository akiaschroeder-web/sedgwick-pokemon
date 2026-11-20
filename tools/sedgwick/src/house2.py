"""Houses rebuilt from FireRed's Pallet Town house art.

The original 8x8 tiles are copied and re-indexed into two merged palettes
(ROOF and WALL). Variants are palette swaps, so every roof colour works with
every siding colour at no extra tile cost.

Kit (each piece is one 16x16 metatile; build houses left to right):
  roof rows   : roof0_{l,m,r} (ridge), roof1_{l,m,r} (slope), roof2_{l,m,r} (eave)
  lower wall  : wall_l, wall_sid, wall_door, wall_win_a + wall_win_b, wall_gar_a + wall_gar_b, wall_r
  upper wall  : up_l, up_sid, up_win_a + up_win_b, up_r      (two-storey houses only)
Ranch house  = roof0, roof2, lower wall          (3 rows)
Two-storey   = roof0, roof1, roof2, upper, lower (5 rows)  -- the original Pallet proportions
The door is a full-size animated door (MB_ANIMATED_DOOR) using Pallet's door animation.
"""
import struct
from PIL import Image
from lib import EXP, load_jasc

P = f'{EXP}/data/tilesets/primary/general_frlg'
S = f'{EXP}/data/tilesets/secondary/pallet_town_frlg'


def _tiles(path):
    im = Image.open(path + '/tiles.png')
    px = im.load()
    w, h = im.size
    return [[[px[tx * 8 + x, ty * 8 + y] & 15 for x in range(8)] for y in range(8)]
            for ty in range(h // 8) for tx in range(w // 8)]


_TP, _TS = _tiles(P), _tiles(S)
_PALS = [load_jasc(f'{P if i < 7 else S}/palettes/{i:02d}.pal') for i in range(13)]

ROOF_BASE = [(255, 0, 255),
             (148, 164, 180), (123, 123, 131), (90, 90, 115), (65, 74, 106),
             (255, 205, 139), (238, 148, 115), (222, 106, 98), (205, 82, 74), (172, 32, 41)] + [(0, 0, 0)] * 6
WALL_BASE = [(255, 0, 255),
             (246, 246, 255), (205, 222, 238), (172, 189, 205), (148, 164, 180),
             (123, 123, 131), (65, 74, 106), (205, 180, 106),
             (156, 213, 255), (115, 189, 246), (98, 164, 222), (90, 90, 115),
             (246, 164, 131), (222, 139, 106), (189, 98, 74), (0, 0, 0)]
# door colours with no exact match in WALL_BASE
_DOOR_MAP = {(189, 197, 222): (172, 189, 205), (156, 205, 246): (156, 213, 255),
             (98, 156, 238): (115, 189, 246), (57, 123, 222): (98, 164, 222)}

ROOF_VARIANTS = {
    'red':      ROOF_BASE,
    'brown':    ROOF_BASE[:5] + [(230, 197, 148), (197, 156, 115), (172, 131, 98), (148, 106, 82), (106, 74, 57)] + ROOF_BASE[10:],
    'charcoal': ROOF_BASE[:5] + [(189, 197, 205), (148, 156, 164), (123, 131, 139), (98, 106, 115), (65, 74, 82)] + ROOF_BASE[10:],
    'green':    ROOF_BASE[:5] + [(189, 222, 172), (131, 189, 131), (98, 156, 106), (74, 131, 90), (49, 98, 74)] + ROOF_BASE[10:],
}
WALL_VARIANTS = {
    'white': WALL_BASE,
    'tan':   [WALL_BASE[0], (255, 246, 225), (238, 226, 196), (214, 198, 162), (181, 166, 134)] + WALL_BASE[5:12]
             + [(148, 205, 131), (106, 164, 98), (74, 123, 82), (0, 0, 0)],
    'blue':  [WALL_BASE[0], (230, 238, 255), (189, 205, 238), (156, 172, 213), (131, 148, 189)] + WALL_BASE[5:12]
             + [(246, 238, 222), (213, 205, 189), (172, 164, 148), (0, 0, 0)],
    'yellow': [WALL_BASE[0], (255, 250, 213), (246, 230, 164), (222, 205, 131), (189, 172, 106)] + WALL_BASE[5:12]
             + [(205, 98, 82), (172, 65, 65), (131, 49, 57), (0, 0, 0)],
}


def _orig(t):
    return _TP[t] if t < 640 else _TS[t - 640]


def _reindex(t, pal_slot, target):
    lut = {c: i for i, c in enumerate(target) if i}
    src = _PALS[pal_slot]
    out = []
    for row in _orig(t):
        r = []
        for v in row:
            if v == 0:
                r.append(0)
            else:
                c = _DOOR_MAP.get(src[v], src[v])
                r.append(lut[c])
        out.append(r)
    return out


def R(t):   # roof tile (FRLG palette 2)
    return _reindex(t, 2, ROOF_BASE)


def W(t):   # wall tile (FRLG palette 3); '557h' = horizontally flipped
    if isinstance(t, str) and t.endswith('h'):
        return [row[::-1] for row in _reindex(int(t[:-1]), 3, WALL_BASE)]
    return _reindex(t, 3, WALL_BASE)


def D(t):   # door tile (Pallet palette 8)
    return _reindex(t, 8, WALL_BASE)


EMPTY = [[0] * 8 for _ in range(8)]


def garage():
    """32x16 roll-up garage door in the Pallet siding style, as 8 tiles (2 metatiles)."""
    g = [[0] * 32 for _ in range(16)]
    for y in range(16):
        for x in range(32):
            if y == 15:
                v = 6
            elif y == 14:
                v = 5
            elif x in (1, 30) or y == 2:
                v = 6                        # dark frame
            elif x in (0, 31) or y < 2:
                v = 2                        # siding around the frame
            elif y == 3:
                v = 4                        # shadow under the header
            elif (y - 4) % 3 == 2:
                v = 4                        # panel seams
            elif x in (2, 29):
                v = 3
            else:
                v = 1 if (y - 4) % 3 == 0 else 2
            g[y][x] = v
    # small windows in the top panel row
    for wx in (5, 11, 18, 24):
        for x in range(wx, wx + 4):
            g[5][x] = 9
            g[4][x] = 8
    tiles = []
    for c in range(4):
        tiles.append(([row[c * 8:c * 8 + 8] for row in g[0:8]], [row[c * 8:c * 8 + 8] for row in g[8:16]]))
    return tiles   # list of (top_tile, bottom_tile) per 8px column


def pieces():
    """name -> dict(top=[4 tiles], under=[4 tiles or None], pal='roof'|'wall', layer, beh)
    `under` tiles are drawn on the bottom layer in the wall palette (siding behind
    window/door pixels); None means lawn."""
    out = {}
    roof_rows = {
        0: ([None, None, (296, 297)], [None, None, (315, 315)], [None, None, (298, 299)]),
    }
    # roof: quadrant order TL, TR, BL, BR
    def roof(name, tl, tr, bl, br):
        out[name] = dict(top=[R(t) if t else EMPTY for t in (tl, tr, bl, br)], under=[None] * 4,
                         pal='roof', layer='NORMAL', beh='MB_NORMAL')
    roof('roof0_l', 0, 0, 296, 297)
    roof('roof0_m', 0, 0, 315, 315)
    roof('roof0_r', 0, 0, 298, 299)
    roof('roof1_l', 312, 313, 312, 313)
    roof('roof1_m', 314, 314, 314, 314)
    roof('roof1_r', 330, 331, 330, 331)
    roof('roof2_l', 312, 313, 374, 527)
    roof('roof2_m', 314, 314, 362, 362)
    roof('roof2_r', 330, 331, 543, 375)

    SID_L = (581, 597)        # lower siding column (top, bottom)
    SID_U = (581, 520)        # upper siding column (has the floor line)

    def wall(name, cols, upper=False, beh='MB_NORMAL', tiles=None):
        """cols: two (top, bottom) original tile ids, or 'G0'..'G3' for garage columns."""
        top, under = [], []
        sid = SID_U if upper else SID_L
        g = garage()
        qt = [None] * 4
        for ci, col in enumerate(cols):
            if isinstance(col, str) and col.startswith('G'):
                tt, bt = g[int(col[1])]
            elif isinstance(col, str) and col.startswith('D'):
                a, b = {'D0': (684, 700), 'D1': (685, 701)}[col]
                tt, bt = D(a), D(b)
            else:
                tt, bt = W(col[0]), W(col[1])
            qt[ci] = tt
            qt[2 + ci] = bt
        # siding behind everything except the outer edge columns
        und = []
        for q in range(4):
            col = cols[q % 2]
            edge = col in ((580, 596), (582, 598), (580, 580), (582, 582))
            if edge:
                und.append(None)
            else:
                und.append(W(sid[0]) if q < 2 else W(sid[1]))
        out[name] = dict(top=qt, under=und, pal='wall', layer='COVERED', beh=beh)

    wall('wall_l', [(580, 596), SID_L])
    wall('wall_r', [SID_L, (582, 598)])
    wall('wall_sid', [SID_L, SID_L])
    wall('wall_door', ['D0', 'D1'], beh='MB_ANIMATED_DOOR')
    wall('wall_win_a', [SID_L, (557, 573)])
    wall('wall_win_b', [(558, 574), ('557h', '573h')])
    wall('wall_gar_a', ['G0', 'G1'])
    wall('wall_gar_b', ['G2', 'G3'])
    wall('up_l', [(580, 580), SID_U], upper=True)
    wall('up_r', [SID_U, (582, 582)], upper=True)
    wall('up_sid', [SID_U, SID_U], upper=True)
    wall('up_win_a', [SID_U, (557, 573)], upper=True)
    wall('up_win_b', [(558, 574), ('557h', '573h')], upper=True)
    return out


def door_anim_png(path, wall_pal=WALL_BASE):
    """Re-index Pallet's door animation (16x48, 3 frames) into the WALL palette."""
    src = Image.open(f'{EXP}/graphics/door_anims/pallet.png')
    lut = {c: i for i, c in enumerate(wall_pal) if i}
    pal8 = _PALS[8]
    out = Image.new('P', src.size, 0)
    flat = [c for col in wall_pal for c in col]
    out.putpalette(flat + [0] * (768 - len(flat)))
    for y in range(src.height):
        for x in range(src.width):
            v = src.getpixel((x, y)) & 15
            if v:
                c = _DOOR_MAP.get(pal8[v], pal8[v])
                out.putpixel((x, y), lut[c])
    out.save(path)


def plan(width, storeys=1, garage_side='r', windows=1):
    """Return rows of piece names for a house `width` metatiles wide (>= 4)."""
    roof_rows = ['roof0', 'roof2'] if storeys == 1 else ['roof0', 'roof1', 'roof2']
    rows = [[f'{r}_l'] + [f'{r}_m'] * (width - 2) + [f'{r}_r'] for r in roof_rows]
    inner = width - 2
    lower = []
    if garage_side and inner >= 4:
        gar = ['wall_gar_a', 'wall_gar_b']
    else:
        gar = []
    rest = inner - len(gar)
    mid = ['wall_door']
    rest -= 1
    while rest >= 2 and windows > 0:
        mid += ['wall_win_a', 'wall_win_b']
        rest -= 2
        windows -= 1
    mid += ['wall_sid'] * rest
    lower = (gar + mid) if garage_side == 'l' else (mid + gar)
    if storeys == 2:
        up = []
        r = inner
        while r >= 2:
            up += ['up_win_a', 'up_win_b']
            r -= 2
        up += ['up_sid'] * r
        rows.append(['up_l'] + up + ['up_r'])
    rows.append(['wall_l'] + lower + ['wall_r'])
    return rows
