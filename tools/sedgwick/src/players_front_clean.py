"""Fire Red-style cleanup of the imported front sprites: curated three-tone ramps per material
(lit from the upper left), stray pixels removed, a single dark outline, then hand fixes."""
from collections import Counter
from PIL import Image
from lib import EXP

FRONT = f'{EXP}/graphics/trainers/front_pics'
O = (16, 16, 24)
BOY_PAL = [(115, 197, 164), O,
           (40, 48, 88), (64, 80, 136), (108, 124, 180),        # navy  dark / mid / light
           (208, 144, 32), (248, 204, 64),                      # yellow shade / yellow
           (204, 188, 156), (248, 240, 216),                    # cream shade / cream
           (130, 104, 68), (180, 154, 106), (206, 184, 134),    # khaki dark / mid / light
           (84, 54, 38), (150, 94, 56),                          # brown dark / mid (hair, bag)
           (212, 144, 104), (248, 202, 154)]                    # skin shade / skin
GIRL_PAL = [(115, 197, 164), O,
            (52, 48, 60), (86, 84, 98),                          # black top / charcoal shorts
            (96, 40, 36), (154, 72, 54), (206, 118, 82),         # hair dark / mid / light
            (110, 32, 48), (162, 52, 72), (206, 98, 110),        # maroon dark / mid / light
            (248, 200, 56),                                      # yellow
            (210, 190, 152), (248, 236, 212),                    # cream shade / cream
            (176, 104, 80), (214, 150, 112), (248, 204, 160)]    # skin dark / shade / light


def load(who):
    im = Image.open(f'{FRONT}/sedgwick_{who}.png')
    pal = im.getpalette()
    return [[(None if im.getpixel((x, y)) == 0 else tuple(pal[im.getpixel((x, y)) * 3:im.getpixel((x, y)) * 3 + 3]))
             for x in range(64)] for y in range(64)]


def nearest(c, pal):
    return min(range(1, len(pal)), key=lambda k: sum((c[j] - pal[k][j]) ** 2 for j in range(3)))


def mapped(rgb, pal):
    return [[0 if c is None else (1 if sum(c) < 110 else nearest(c, pal)) for c in row] for row in rgb]


N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def reshade(g, ramp):
    """Re-light one material (ramp = dark, mid, light indices): light along its upper-left
    edges, dark along its lower-right edges and on the artist's folds, mid elsewhere."""
    D, M, L = ramp
    mat = {(x, y) for y in range(64) for x in range(64) if g[y][x] in ramp}
    out = {}
    for x, y in mat:
        up_left = (x - 1, y) not in mat or (x, y - 1) not in mat
        down_right = (x + 1, y) not in mat or (x, y + 1) not in mat
        fold = g[y][x] == D and sum(g[y + dy][x + dx] == D for dx, dy in N4 if 0 <= x + dx < 64 and 0 <= y + dy < 64) >= 1
        if down_right and not up_left:
            out[(x, y)] = D
        elif fold:
            out[(x, y)] = D
        elif up_left and not down_right:
            out[(x, y)] = L
        else:
            out[(x, y)] = M
    for (x, y), v in out.items():
        g[y][x] = v


def despeckle(g, keep=()):
    """A pixel that matches none of its four neighbours takes their most common colour
    (outline and the listed detail colours are left alone)."""
    nxt = [r[:] for r in g]
    for y in range(1, 63):
        for x in range(1, 63):
            v = g[y][x]
            if v in (0, 1) or v in keep:
                continue
            n = [g[y + dy][x + dx] for dx, dy in N4]
            if v not in n:
                m = Counter(k for k in n if k not in (0, 1))
                if m and m.most_common(1)[0][1] >= 2:
                    nxt[y][x] = m.most_common(1)[0][0]
    return nxt


def outline(g):
    for y in range(64):
        for x in range(64):
            if g[y][x] and any(not (0 <= x + dx < 64 and 0 <= y + dy < 64) or g[y + dy][x + dx] == 0 for dx, dy in N4):
                g[y][x] = 1
    return g


BOY_RAMPS = [(2, 3, 4), (9, 10, 11)]                         # navy jacket, khaki pants
GIRL_RAMPS = [(4, 5, 6), (7, 8, 9)]                          # hair, maroon


def clean(who):
    pal = BOY_PAL if who == 'boy' else GIRL_PAL
    g = mapped(load(who), pal)
    keep = (14, 15, 12, 13) if who == 'boy' else (13, 14, 15, 10)
    g = despeckle(despeckle(g, keep), keep)
    for ramp in (BOY_RAMPS if who == 'boy' else GIRL_RAMPS):
        reshade(g, ramp)
    if who == 'girl':
        girl_fixes(g)
    return outline(g)


def girl_fixes(g):
    for y in range(19, 33):                                  # black top under the jacket
        for x in range(24, 38):
            if g[y][x] == 3:
                g[y][x] = 2
    for y in range(33, 41):                                  # charcoal shorts
        for x in range(25, 38):
            if g[y][x] == 2:
                g[y][x] = 3
    for y in range(33, 41):                                  # cream bag at her right hip, maroon trim
        for x in range(19, 26):
            v = g[y][x]
            if v in (13, 14):
                g[y][x] = 11
            elif v == 4:
                g[y][x] = 7
    # face: the boy's eyes and mouth, pixel for pixel (lash, white, pupil | 3 skin | pupil,
    # white, lash; mouth one skin-shade pixel three rows below, centred)
    face = {14: [1, 12, 1, 15, 15, 15, 1, 12, 1],
            15: [14, 12, 1, 15, 15, 15, 1, 12, 1],
            16: [14, 15, 15, 15, 15, 15, 15, 15, 14]}
    for y, row in face.items():
        for i, v in enumerate(row):
            g[y][26 + i] = v
    g[17][30] = 14
    for x, v in ((31, 4), (32, 5), (33, 4)):                  # bangs closed above the right eye
        g[13][x] = v
    for x, y in ((21, 36), (22, 36), (21, 37), (22, 37)):     # Poke Ball emblem on the flap
        if g[y][x] not in (0, 1):
            g[y][x] = 9 if y == 36 else 12


def preview(g, pal, s=6):
    im = Image.new('RGB', (64, 64))
    for y in range(64):
        for x in range(64):
            im.putpixel((x, y), pal[g[y][x]])
    return im.resize((64 * s, 64 * s), Image.NEAREST)


def dump(g):
    print('    ' + ''.join(str(x % 10) for x in range(64)))
    for y in range(64):
        row = ''.join('.' if v == 0 else '%x' % v for v in g[y])
        if row.strip('.'):
            print(f'{y:2d}  ' + row)


def install():
    """Run after players_front_import.install(): overwrite the imported pictures with the cleaned ones."""
    import players_front_import as pi
    for who in ('boy', 'girl'):
        g = clean(who)
        pi.save(g, BOY_PAL if who == 'boy' else GIRL_PAL, f'{FRONT}/sedgwick_{who}.png')


if __name__ == '__main__':
    import players_front_import
    players_front_import.install()
    install()
    print('front pictures imported and cleaned')
