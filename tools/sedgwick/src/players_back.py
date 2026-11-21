"""Battle back sprites (64x64, 5 frames) for the two protagonists, edited from
FireRed's Red and Leaf back pics. Same palette index meanings as the overworld sprites."""
import os
from collections import deque
from PIL import Image
from players import BOY_PAL
from players_girl import GIRL_PAL
from lib import EXP

BACK = f'{EXP}/graphics/trainers/back_pics'


class _Frame(list):
    pass


def frames(name):
    im = Image.open(f'{BACK}/{name}.png')
    out = []
    for f in range(im.height // 64):
        fr = _Frame([[im.getpixel((x, f * 64 + y)) for x in range(64)] for y in range(64)])
        fr.index_ = f
        out.append(fr)
    return out


def _set_frame(g):
    FRAME[0] = getattr(g, 'index_', None)


def component(g, seed, vals):
    seen = {seed}
    q = deque([seed])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if 0 <= n[0] < 64 and 0 <= n[1] < 64 and n not in seen and g[n[1]][n[0]] in vals:
                seen.add(n)
                q.append(n)
    return seen


def hat(g, vals):
    """The hat: the component of `vals` holding the topmost such pixel."""
    for y in range(64):
        for x in range(64):
            if g[y][x] in vals:
                return component(g, (x, y), vals)
    return set()


def put(g, x0, y0, art, key):
    for r, row in enumerate(art):
        for c, ch in enumerate(row):
            if ch != '.' and 0 <= y0 + r < 64 and 0 <= x0 + c < 64:
                g[y0 + r][x0 + c] = key[ch]


# ---------------------------------------------------------------- boy (from Red)
BRIM = ["...666666",
        ".66bbbbbb",
        "6bbbbbccc",
        "66cccc666"]


def boy(g):
    _set_frame(g)
    g = debag(g, (11, 12, 6), (9, 10), (13, 14), (4, 1), (1, 4))
    cap = hat(g, {11, 12})
    cap |= {p for p in component(g, next(iter(cap)), {11, 12, 8, 15}) if p[1] <= max(y for _, y in cap)}
    xs = [x for x, _ in cap]
    ys = [y for _, y in cap]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    mid = (x0 + x1) // 2
    for y in range(y1 - 2, y1 + 3):                          # Red's brim (pointing forward) comes off
        for x in range(mid, 64):
            if g[y][x] in (9, 10, 6):
                g[y][x] = 0
    for x, y in cap:                                         # front panel (cream) faces the camera now
        v = g[y][x]
        if v == 8:
            g[y][x] = 6
        elif v == 15 and x0 < x < x1 and y0 < y < y1:
            g[y][x] = 9                                      # no strap hole on the front panel
        elif v in (11, 12):
            g[y][x] = (9 if v == 11 else 10) if x < mid + 3 else v
    face_left = {}
    for y in range(y1 - 2, min(64, y1 + 14)):
        skin = [x for x in range(64) if g[y][x] in (2, 3)]
        face_left[y] = min(skin) if skin else 64
    hair = {(x, y) for y in range(y1 - 2, min(64, y1 + 14)) for x in range(max(0, x0 - 4), min(64, x1 + 2))
            if g[y][x] in (1, 4, 8) and x < face_left[y]}
    top = {}
    for x, y in hair:
        top[x] = min(top.get(x, 99), y)
    for x, y in hair:                                        # hair: mid brown, lit tips, dark against the outline
        out = any(0 <= x + dx < 64 and 0 <= y + dy < 64 and g[y + dy][x + dx] == 0
                  for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if y - top[x] <= 1 or (g[y][x] == 4 and (x + 2 * y) % 5 == 0):
            g[y][x] = 5
        elif out or g[y][x] == 8 and (x + y) % 4 == 0:
            g[y][x] = 4
        else:
            g[y][x] = 1
    for y in range(y1 - 1, min(64, y1 + 13)):                # black lines inside the hair become dark brown
        for x in range(max(1, x0 - 4), min(63, x1 + 2)):
            if g[y][x] == 15:
                n = sum(g[y + dy][x + dx] in (1, 5) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= y + dy < 64)
                if n >= 2:
                    g[y][x] = 4
    put(g, x0 - 5, y1 - 3, BRIM, {'6': 6, 'b': 11, 'c': 12})  # navy brim over the back of the neck
    for y in range(64):
        for x in range(64):
            v = g[y][x]
            if y > y1 + 12 and (x, y) not in hair:
                g[y][x] = {5: 11, 7: 11}.get(v, v)                # sleeves navy
    return g


# ---------------------------------------------------------------- girl (from Leaf)
TAIL = ["....666....",
        "...61146...",
        "..6111446..",
        "..6dd6dd6..",
        ".6deddedd6.",
        "..6dd66dd6."]




BOY_BACK_PAL = list(BOY_PAL)
BOY_BACK_PAL[1] = (138, 84, 48)       # hair mid (the back sprite has its own palette)
BOY_BACK_PAL[4] = (86, 48, 32)        # hair dark
BOY_BACK_PAL[5] = (184, 118, 66)      # hair highlight (khaki is not on the back sprite)
BOY_BACK_PAL[7] = (150, 98, 60)
BOY_BACK_PAL[8] = (74, 42, 30)


def save(frames_, pal, path):
    im = Image.new('P', (64, 64 * len(frames_)))
    im.putpalette([c for col in pal for c in col])
    for f, g in enumerate(frames_):
        for y in range(64):
            for x in range(64):
                im.putpixel((x, f * 64 + y), g[y][x])
    im.save(path)


def preview(frames_, pal, scale=3):
    im = Image.new('RGB', (64 * len(frames_), 64))
    for f, g in enumerate(frames_):
        for y in range(64):
            for x in range(64):
                im.putpixel((f * 64 + x, y), pal[g[y][x]])
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


if __name__ == '__main__':
    import sys
    a = preview([boy(g) for g in frames('red')], BOY_BACK_PAL)
    b = preview([girl(g) for g in frames('red')], GIRL_PAL)
    o = Image.new('RGB', (a.width, a.height * 2 + 10), (30, 30, 30))
    o.paste(a, (0, 0)); o.paste(b, (0, a.height + 10))
    o.save(sys.argv[1])


# ---------------------------------------------------------------- Red without his backpack
def bag_pixels(g):
    """Red's backpack: its yellow pixels plus the dark lines drawn inside it."""
    B = {(x, y) for y in range(64) for x in range(64) if g[y][x] in (13, 14)}
    for _ in range(3):
        add = set()
        for y in range(64):
            for x in range(64):
                if (x, y) in B or g[y][x] not in (4, 15, 6, 8):
                    continue
                n = sum((x + dx, y + dy) in B for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if n >= 2:
                    add.add((x, y))
        B |= add
    return B


def debag(g, jacket, hood, stripe, strap, bag):
    if FRAME[0] in BACK_SPECS:
        return paint_back(g, BACK_SPECS[FRAME[0]], jacket, hood, stripe, strap, bag)
    return debag_auto(g, jacket, hood, stripe, strap, bag)


FRAME = [None]


def debag_auto(g, jacket, hood, stripe, strap, bag):
    """Repaint Red's backpack as the back of a jacket: a smooth back contour, three-tone
    fill, the hood hanging over the shoulders, the stripe, a strap from the far shoulder
    to a small bag at the near hip. jacket = (light, mid, dark); hood = (cream, shade)."""
    g = [r[:] for r in g]
    B = bag_pixels(g)
    if not B:
        return g
    L, M, D = jacket
    rows = sorted({y for _, y in B})
    # where the bag is the leftmost thing in its row, the back's contour has to be invented:
    # fit a smooth curve to the bag's left edge and pull it in a pixel or two
    lead = []
    for y in rows:
        xs = [x for x in range(64) if g[y][x]]
        if xs and (xs[0], y) in B:
            lead.append((y, xs[0]))
    contour = {}
    if len(lead) >= 3:
        n = len(lead)
        sy = sum(y for y, _ in lead) / n
        sx = sum(x for _, x in lead) / n
        k = sum((y - sy) * (x - sx) for y, x in lead) / max(1e-6, sum((y - sy) ** 2 for y, _ in lead))
        y_top = lead[0][0]
        for y, _ in lead:
            contour[y] = round(sx + k * (y - sy) + 1 + 1.5 * (y - y_top) / max(1, 63 - y_top))
    for x, y in B:
        g[y][x] = 0
    filled = set()
    for y in rows:
        x = 0
        while x < 64:
            if (x, y) in B:
                x2 = x
                while x2 + 1 < 64 and (x2 + 1, y) in B:
                    x2 += 1
                left_body = x > 0 and g[y][x - 1] != 0
                right_body = x2 < 63 and g[y][x2 + 1] != 0
                if left_body or (y in contour and contour[y] <= x2):
                    start = x if left_body else max(x, contour[y])
                    if right_body or left_body:
                        for xx in range(start, x2 + 1):
                            filled.add((xx, y))
                x = x2 + 1
            else:
                x += 1
    for x, y in filled:
        g[y][x] = M
    # outline the new edge, shade from it
    for x, y in filled:
        if any(not (0 <= x + dx < 64 and 0 <= y + dy < 64) or g[y + dy][x + dx] == 0
               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            g[y][x] = 15
    for x, y in filled:
        if g[y][x] != M:
            continue
        dl = next((d for d in range(1, 4) if g[y][x - d] == 15 and (x - d, y) in filled), None) if x >= 3 else None
        dr = next((d for d in range(1, 3) if x + d < 64 and (x + d, y) not in filled and g[y][x + d] != 0), None)
        if dl is not None and dl <= 2:
            g[y][x] = L
        elif dr is not None:
            g[y][x] = D
    if FRAME[0] not in (1,):
        return g                                             # turned side-on: just the jacket
    # the hood over the shoulders: rounded at the bottom
    frows = sorted({y for _, y in filled})
    y0 = frows[0]
    span = {y: (min(x for x, yy in filled if yy == y), max(x for x, yy in filled if yy == y)) for y in frows}
    for i, inset in enumerate((0, 0, 1, 2, 4)):
        y = y0 + i
        if y not in span:
            continue
        a_, b_ = span[y]
        for x in range(a_ + 1 + inset, b_ - inset):
            g[y][x] = hood[0] if x < (a_ + b_) / 2 + 2 else hood[1]
        if i == 4:
            for x in range(a_ + 1 + inset, b_ - inset):
                if y + 1 in span and (x, y + 1) in filled:
                    g[y + 1][x] = 15 if x in (a_ + 1 + inset, b_ - inset - 1) else hood[1]
    # stripe
    sy = y0 + 9
    for y, col in ((sy, stripe[0]), (sy + 1, stripe[1])):
        for x in range(64):
            if (x, y) in filled and g[y][x] != 15:
                g[y][x] = col
    # strap from the far shoulder to the near hip, two pixels wide, even steps
    xa, ya = span[y0 + 3][1] - 2, y0 + 3
    yb = 62
    xb = span[max(y for y in frows if y <= yb)][0] + 5
    for y in range(ya, yb + 1):
        t = (y - ya) / max(1, yb - ya)
        x = round(xa + (xb - xa) * t)
        for dx, col in ((0, strap[0]), (1, strap[1])):
            if (x + dx, y) in filled and g[y][x + dx] != 15:
                g[y][x + dx] = col
    # small bag at the hip, cut off by the bottom of the frame
    bx0 = span[max(frows)][0]
    art = ["oooooooo",
           "oBBBBBBo",
           "obbbbbbo",
           "oBBBBBBo",
           "oBBBBBBo"]
    for r, row in enumerate(art):
        for c, ch in enumerate(row):
            x, y = bx0 - 1 + c, 59 + r
            if 0 <= x < 64 and y < 64:
                g[y][x] = {'o': 15, 'B': bag[0], 'b': bag[1]}[ch]
    return g


# ---------------------------------------------------------------- girl, built on Red's back sprite
def girl(g):
    """Her reference: hair pulled up into a big wavy high ponytail (nape showing), a
    yellow ribbon tied at its base, bangs with a cream streak; maroon jacket, cream hood."""
    import math
    _set_frame(g)
    g = debag(g, (7, 5, 8), (9, 10), (13, 14), (6, 4), (9, 10))
    cap = hat(g, {11, 12})
    cap |= {p for p in component(g, next(iter(cap)), {11, 12, 8, 15}) if p[1] <= max(y for _, y in cap)}
    xs = [x for x, _ in cap]
    ys = [y for _, y in cap]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    mid = (x0 + x1) // 2
    for y in range(y1 - 2, y1 + 3):                          # Red's brim
        for x in range(mid, 64):
            if g[y][x] in (9, 10, 6):
                g[y][x] = 0
    for x, y in cap:
        g[y][x] = 0
    face_left = {}
    for y in range(y0, min(64, y1 + 14)):
        skin = [x for x in range(mid - 2, 64) if g[y][x] in (2, 3)]
        face_left[y] = min(skin) if skin else 64
    # Red's short hair at the nape: auburn wisps
    for y in range(y1 - 2, min(64, y1 + 13)):
        for x in range(max(0, x0 - 4), min(64, x1 + 2)):
            if x < face_left[y] and g[y][x] in (1, 4, 8):
                g[y][x] = {1: 1, 4: 1, 8: 4}[g[y][x]]
    put_hair(g, x0, y0, face_left)                           # traced from her sheet
    cx, rx = (x0 + x1) / 2 - 0.5, (x1 - x0) / 2
    face_l = lambda y: face_left.get(int(y), 64)
    # bangs over the forehead, with the cream lock
    fl = min(face_l(y) for y in range(y1 - 1, y1 + 3))
    bangs = [".oooooooo.",
             "ommmllmmmo",
             "omcmmmlmmo",
             "omcmommlmo",
             ".ocoo.omo.",
             "..o....o.."]
    put(g, fl - 3, y1 - 4, bangs, {'o': 6, 'm': 4, 'l': 1, 'c': 9})
    # clothes: Red's red jacket and blue sleeves become maroon
    for y in range(y1 + 8, 64):
        for x in range(64):
            v = g[y][x]
            if v in (11, 12, 6, 5):
                g[y][x] = {11: 7, 12: 5, 6: 8, 5: 5}[v]
    return g


# ---------------------------------------------------------------- hand-set geometry for the idle frames
# Frame 0 is on screen for the whole battle and frame 2 is the same pose mid-throw, so their
# jacket backs are laid out by hand: per row, the back contour (x of its outline) and the first
# column of the sleeve/arm that stays as Red drew it. Hood, stripe, strap and bag are placed
# explicitly rather than inferred.
BACK_SPECS = {
    0: dict(rows={44: (31, 45), 45: (29, 45), 46: (27, 45), 47: (26, 44), 48: (25, 42), 49: (24, 42),
                  50: (24, 42), 51: (23, 41), 52: (23, 41), 53: (22, 40), 54: (22, 40), 55: (22, 40),
                  56: (21, 41), 57: (21, 40), 58: (21, 40), 59: (21, 39), 60: (20, 38), 61: (20, 39),
                  62: (20, 39), 63: (20, 38)},
            hood={44: (32, 44), 45: (30, 44), 46: (29, 43), 47: (29, 41), 48: (31, 38)},
            stripe=53, strap=((41, 45), (27, 58)), bag=(19, 58)),
    2: dict(rows={44: (18, 29), 45: (24, 29), 46: (24, 29), 47: (23, 42), 48: (19, 42), 49: (19, 42),
                  50: (18, 39), 51: (17, 37), 52: (16, 35), 53: (16, 35), 54: (16, 34), 55: (15, 34),
                  56: (15, 33), 57: (15, 33), 58: (14, 32), 59: (14, 32), 60: (14, 31), 61: (13, 30),
                  62: (13, 30), 63: (13, 30)},
            hood={45: (26, 33), 46: (25, 34), 47: (25, 36), 48: (26, 36), 49: (28, 34)},
            stripe=53, strap=((37, 49), (22, 58)), bag=(12, 58)),
}


def paint_back(g, spec, jacket, hood, stripe, strap, bag):
    g = [r[:] for r in g]
    B = bag_pixels(g)
    L, M, D = jacket
    rows = spec['rows']
    for x, y in B:                                           # backpack off
        if y not in rows or x < rows[y][0] or x >= rows[y][1]:
            g[y][x] = 0
    for y, (c, r) in rows.items():
        g[y][c] = 15
        for x in range(c + 1, r):
            t = x - c
            g[y][x] = L if t <= 2 else (D if r - x <= 2 else M)
        if r < 64 and g[y][r] == 0:
            g[y][r - 1] = 15                                 # open side: close it with an outline
        for x in range(0, c):                                # nothing of the bag left outside
            if (x, y) in B:
                g[y][x] = 0
    top = min(rows)
    for x in range(rows[top][0], rows[top][1]):              # close the shoulders with an outline
        if g[top - 1][x] == 0:
            g[top - 1][x] = 15
    # hood draped over the shoulders, outlined along its bottom edge
    hood_px = {(x, y) for y, (a_, b_) in spec['hood'].items() for x in range(a_, b_ + 1)}
    for x, y in hood_px:
        a_, b_ = spec['hood'][y]
        g[y][x] = hood[0] if x < a_ + (b_ - a_) * 0.62 else hood[1]
    for x, y in hood_px:
        if (x, y + 1) not in hood_px and y + 1 in rows and rows[y + 1][0] < x < rows[y + 1][1]:
            g[y + 1][x] = 15
    # stripe
    for y, col in ((spec['stripe'], stripe[0]), (spec['stripe'] + 1, stripe[1])):
        c, r = rows[y]
        for x in range(c + 1, r):
            g[y][x] = col
    # strap: even steps from the far shoulder to the bag
    (xa, ya), (xb, yb) = spec['strap']
    for y in range(ya, yb + 1):
        x = round(xa + (xb - xa) * (y - ya) / (yb - ya))
        for dx, col in ((0, strap[0]), (1, strap[1])):
            if y in rows and rows[y][0] < x + dx < rows[y][1]:
                g[y][x + dx] = col
    # the bag at the hip, hanging just outside the back contour
    bx, by = spec['bag']
    art = ["oooooooo",
           "oBBBBBBo",
           "obbbbbbo",
           "oBBYBBBo",
           "oBBBBBBo",
           "oBBBBBBo"]
    for r_, row in enumerate(art):
        for c_, ch in enumerate(row):
            x, y = bx + c_, by + r_
            if 0 <= x < 64 and y < 64:
                g[y][x] = {'o': 15, 'B': bag[0], 'b': bag[1], 'Y': stripe[0]}[ch]
    return g


# ---------------------------------------------------------------- the girl's hair, traced from her sheet
REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'custom', 'source', 'girl_reference.png')
HAIR_SCALE = 0.19


def hair_patch():
    """Her back-view head from the reference sheet, shrunk to sprite size and snapped to her
    palette: dict (x, y) -> index, in patch coordinates."""
    im = Image.open(REF).convert('RGB')
    w, h = im.size
    crop = im.crop((int(w * 0.255), int(h * 0.015), int(w * 0.405), int(h * 0.185)))   # head, above the hood
    sw, sh = round(crop.width * HAIR_SCALE), round(crop.height * HAIR_SCALE)
    small = crop.resize((sw, sh), Image.LANCZOS)
    out, lums = {}, {}
    for y in range(sh):
        for x in range(sw):
            r, g_, b = small.getpixel((x, y))
            if r > 215 and g_ > 205 and b > 195:
                continue                                     # paper
            if r > 190 and g_ > 140 and b < 120 and r - b > 80:
                out[(x, y)] = 13 if g_ > 175 else 14         # ribbon
            elif r > 215 and g_ > 165 and b > 130:
                out[(x, y)] = 'skin'
            else:
                lums[(x, y)] = 0.3 * r + 0.59 * g_ + 0.11 * b
    ordered = sorted(lums.values())
    lo, hi = ordered[int(len(ordered) * 0.28)], ordered[int(len(ordered) * 0.80)]
    for p, l in lums.items():
        out[p] = 6 if l < lo else (4 if l < hi else 1)
    for _ in range(2):                                       # tidy single stray pixels
        nxt = dict(out)
        for (x, y), v in out.items():
            if v not in (1, 4, 6):
                continue
            n = [out.get((x + dx, y + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            n = [k for k in n if k in (1, 4, 6)]
            if len(n) == 4 and v not in n:
                nxt[(x, y)] = max(set(n), key=n.count)
        out = nxt
    for (x, y), v in list(out.items()):
        if v == 1 and sum(out.get((x + dx, y + dy)) == 1 for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy) <= 1:
            out[(x, y)] = 4
    # Gen 3 outline: hair pixels on the silhouette go dark
    for (x, y), v in list(out.items()):
        if v in (1, 4) and any((x + dx, y + dy) not in out for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            out[(x, y)] = 6
    return out


_PATCH = []


def put_hair(g, x0, y0, face_left):
    if not _PATCH:
        _PATCH.append(hair_patch())
    ox, oy = x0 - 18, y0 - 10
    for (x, y), v in _PATCH[0].items():
        X, Y = x + ox, y + oy
        if not (0 <= X < 64 and 0 <= Y < 64) or v == 'skin':
            continue
        if Y >= y0 + 12 and X >= face_left.get(Y, 64) - 1:
            continue                                         # leave the face and ear clear
        g[Y][X] = v
