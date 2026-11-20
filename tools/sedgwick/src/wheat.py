"""Wheat field metatiles (centre, 4 edges, 4 outer corners), harvested stubble,
and the 5-frame 'walking through wheat' field-effect sprite."""
from lib import blank, copy

H, G, M, D, K = 5, 6, 7, 8, 9
GR, GL = 2, 1  # grass base / speck
CM = {'H': H, 'G': G, 'M': M, 'D': D, 'K': K}

EAR = [".H..", "HGK.", "HGMK", "GGMK", "GMMK", ".MDK", ".MD.", ".D.."]
EAR2 = ["..H.", ".HGK", "HGMK", "HGMK", "GMMK", "GMDK", ".MD.", "..D."]
TOP = [(0, 0, 0), (5, 1, 1), (11, 0, 0)]
BOT = [(2, 8, 1), (8, 9, 0), (13, 8, 1)]
NOISE = [(4, 7), (10, 7), (15, 6), (1, 15), (7, 15), (12, 14), (6, 4), (15, 12)]
SPECKS = [(2, 1), (9, 0), (13, 2), (6, 3), (1, 12), (10, 14), (14, 9), (5, 6)]


def stamp(g, ears, wrap_x=True, wrap_y=True, clip=None, sprites=None):
    sprites = sprites or (EAR, EAR2)
    for ex, ey, s in ears:
        for dy, row in enumerate(sprites[s]):
            for dx, c in enumerate(row):
                if c == '.':
                    continue
                x, y = ex + dx, ey + dy
                if wrap_x:
                    x %= 16
                if wrap_y:
                    y %= 16
                if not (0 <= x < 16 and 0 <= y < 16):
                    continue
                if clip and not clip(x, y):
                    continue
                g[y][x] = CM[c]


def field(top=False, bottom=False, left=False, right=False, sprites=None):
    """Wheat with grass showing on the requested sides."""
    def inside(x, y):
        return not ((top and y < 6) or (bottom and y > 12) or (left and x < 4) or (right and x > 11))

    g = blank(D)
    for y in range(16):
        for x in range(16):
            if not inside(x, y):
                g[y][x] = GR
    for x, y in SPECKS:
        if not inside(x, y):
            g[y][x] = GL
    for x, y in NOISE:
        if inside(x, y):
            g[y][x] = K
    top_row = [(x, y + (3 if top else 0), s) for x, y, s in TOP]
    bot_row = [(x, y - (3 if bottom else 0), s) for x, y, s in BOT]
    ears = top_row + bot_row
    # drop ears whose stalk would stand on grass at a side edge
    if left:
        ears = [e for e in ears if e[0] >= 3] + [(4, (8 if not bottom else 5), 0)]
    if right:
        ears = [e for e in ears if e[0] + 4 <= 13]
    wrapx = not (left or right)
    wrapy = not (top or bottom)
    # ears may lean up to 1px past the field edge (organic outline), but not further
    def clip(x, y):
        return ((not top or y >= 3) and (not bottom or y <= 13)
                and (not left or x >= 3) and (not right or x <= 12))
    stamp(g, ears, wrap_x=wrapx, wrap_y=wrapy, clip=clip, sprites=sprites)
    # soft dark rim where the field base meets lawn
    for y in range(16):
        for x in range(16):
            if g[y][x] == D:
                for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < 16 and 0 <= ny < 16 and g[ny][nx] in (GR, GL):
                        g[y][x] = K
                        break
    return g


def stubble():
    g = blank(G)
    for y in range(16):
        for x in range(16):
            if (x * 5 + y * 3) % 13 == 0:
                g[y][x] = H
    for base, offs in ((2, [0, 3, 5, 9, 12, 14]), (10, [1, 4, 7, 10, 13, 15])):
        for x in range(16):
            g[base + 3][x] = M
        for x in offs:
            g[base][x] = M
            g[base + 1][x] = M
            g[base + 2][x] = D
            g[base + 1][(x + 1) % 16] = D
    return g


def field_set(prefix, beh, sprites=None):
    sides = {'': {}, '_n': dict(top=True), '_s': dict(bottom=True), '_w': dict(left=True),
             '_e': dict(right=True), '_nw': dict(top=True, left=True), '_ne': dict(top=True, right=True),
             '_sw': dict(bottom=True, left=True), '_se': dict(bottom=True, right=True)}
    return {prefix + k: (field(sprites=sprites, **kw), beh) for k, kw in sides.items()}


# Corn: broad leaves instead of grain heads (drawn with the same 5 colour roles)
CORN = ["..H.", "HHGK", ".HGM", "HGMK", "GGMK", ".GMD", "HMDK", ".D.."]
CORN2 = [".H..", "KGHH", "MGH.", "KMGH", "KMGG", "DMG.", "KDMH", "..D."]


def metatiles():
    out = field_set('wheat', 'MB_TALL_WHEAT')
    out['stubble'] = (stubble(), 'MB_NORMAL')
    return out


def corn_metatiles():
    return field_set('corn', 'MB_TALL_GRASS', sprites=(CORN, CORN2))


# ---------------------------------------------------------------- field effect sprite
# Same 5-frame layout as graphics/field_effects/pics/tall_grass.png (80x16):
# 0 = settled (covers the walker's feet), 1 = stalks pushed apart,
# 2-3 = chaff flying, 4 = settling.  The game plays 1,2,3,4 then rests on 0.
FX_PAL = [(115, 189, 238),  # 0 transparent (matches vanilla sprite palettes)
          (255, 246, 180), (238, 213, 115), (213, 172, 82), (180, 131, 65), (123, 90, 49)] + [(0, 0, 0)] * 10
fH, fG, fM, fD, fK = 1, 2, 3, 4, 5
FM = {'H': fH, 'G': fG, 'M': fM, 'D': fD, 'K': fK, '.': 0}

FRAMES = [
# 0 settled: a low band of wheat heads across the bottom
"""
................
................
................
................
................
................
................
................
.H....H.....H...
HGK..HGK...HGK..
HGMKHHGMK.HGGMK.
GGMKGGGMKHGGMMKH
GMMKGMMDKGGMMDKG
DMDKDMDDKDMDDKDM
KDDKKDDKKDDDKKDD
.KK..KK..KKK.KK.
""",
# 1 pushed apart: stalks lean outward, taller
"""
................
................
.H............H.
HGK..........HGK
HGMK........HGMK
GGMK.H....H.GGMK
GMMKHGK..HGKGMMK
.MDKHGMK.HGMKMD.
..DKGGMK.GGMKD..
...DGMMKDGMMKD..
..H.DMDK.DMDK.H.
.HGK.DD...DD.HGK
HGMMKD.....DKHGM
GMMDK.......KGMD
DDDKK.......KKDD
.KK...........KK
""",
# 2 chaff flying up
"""
.......H........
..G.........H...
.....H..........
.G.........G....
..........H..G..
...H............
.......G........
................
.H....H.....H...
HGK..HGK...HGK..
HGMK.HGMK.HGGMK.
GGMKGGGMKHGGMMKH
GMMKGMMDKGGMMDKG
DMDKDMDDKDMDDKDM
KDDKKDDKKDDDKKDD
.KK..KK..KKK.KK.
""",
# 3 chaff drifting down
"""
................
................
....H...........
..........G.....
.G..............
......H......H..
............G...
..G..H..........
.H....H....GH...
HGK..HGK...HGK..
HGMK.HGMK.HGGMK.
GGMKGGGMKHGGMMKH
GMMKGMMDKGGMMDKG
DMDKDMDDKDMDDKDM
KDDKKDDKKDDDKKDD
.KK..KK..KKK.KK.
""",
# 4 settling: one last speck
"""
................
................
................
................
................
................
.........H......
...G............
.H....H.....H...
HGK..HGK...HGK..
HGMKHHGMK.HGGMK.
GGMKGGGMKHGGMMKH
GMMKGMMDKGGMMDKG
DMDKDMDDKDMDDKDM
KDDKKDDKKDDDKKDD
.KK..KK..KKK.KK.
""",
]


def fx_frames():
    out = []
    for f in FRAMES:
        rows = f.strip('\n').split('\n')
        assert len(rows) == 16 and all(len(r) == 16 for r in rows), [len(r) for r in rows]
        out.append([[FM[c] for c in r] for r in rows])
    return out
