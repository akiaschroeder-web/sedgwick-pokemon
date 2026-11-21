"""Battle back sprites (64x64, 5 frames) for the two protagonists, edited from
FireRed's Red and Leaf back pics. Same palette index meanings as the overworld sprites."""
from collections import deque
from PIL import Image
from players import BOY_PAL
from players_girl import GIRL_PAL
from lib import EXP

BACK = f'{EXP}/graphics/trainers/back_pics'


def frames(name):
    im = Image.open(f'{BACK}/{name}.png')
    return [[[im.getpixel((x, f * 64 + y)) for x in range(64)] for y in range(64)] for f in range(im.height // 64)]


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
    g = debag(g, (11, 12, 6), (9, 10), (13, 14), 4, 1)
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
def debag(g, jacket, hood, stripe, strap, bag):
    """Repaint Red's backpack as the back of a jacket: the hood hanging over the top,
    a stripe across, a strap from the far shoulder to a small bag at the hip.
    jacket = (light, mid, dark) indices; hood = (cream, shade); stripe = (main, shadow)."""
    g = [r[:] for r in g]
    rows = [y for y in range(64) if any(v in (13, 14) for v in g[y])]
    if not rows:
        return g
    top, bottom = rows[0], 63
    region = {}
    prev = None
    for y in range(top - 1, bottom + 1):
        bag_x = [x for x in range(64) if g[y][x] in (13, 14)]
        if bag_x:
            xl = bag_x[0]
            while xl > 0 and g[y][xl - 1] and g[y][xl - 1] not in (2, 3, 5, 7):
                xl -= 1
            xl = max(0, xl - 1) if xl > 0 and g[y][xl - 1] == 0 else xl
            x = bag_x[-1]
            stop = None
            while x < 63:
                x += 1
                v = g[y][x]
                if v == 0 or v in (5, 7, 2, 3) or (v == 6 and x + 2 < 64 and g[y][x + 1] in (5, 6) and g[y][x + 2] in (5, 6)):
                    stop = x
                    break
            stop = stop or 63
            prev = (xl, stop)
        elif prev:
            xl, stop = prev
            while xl < stop and g[y][xl] == 0:
                xl += 1
        else:
            continue
        if stop - xl > 2:
            region[y] = (xl, stop)
    L, M, D = jacket
    for y, (xl, stop) in region.items():
        for x in range(xl + 1, stop - 1):
            t = (x - xl) / max(1, stop - xl)
            g[y][x] = L if t < 0.3 else (M if t < 0.8 else D)
        g[y][xl] = 15
        if stop - 1 > xl:
            g[y][stop - 1] = 15
    # the hood hangs over the upper back
    ys = sorted(region)
    y0 = ys[0]
    for y in ys[:5]:
        xl, stop = region[y]
        inset = (y - y0) * 2
        for x in range(xl + 1 + inset // 2, stop - 1 - inset // 3):
            g[y][x] = hood[0] if (x - xl) < (stop - xl) * 0.6 else hood[1]
        if y == ys[4]:
            for x in range(xl + 1 + inset // 2, stop - 1 - inset // 3):
                g[y][x] = 15 if g[y - 1][x] in hood else g[y][x]
    # stripe a third of the way down
    sy = y0 + max(7, (bottom - y0) // 3)
    for y in (sy, sy + 1):
        if y in region:
            xl, stop = region[y]
            for x in range(xl + 1, stop - 1):
                g[y][x] = stripe[0] if y == sy else stripe[1]
    # strap: from the far shoulder down to the near hip
    sx0, sy0 = region[ys[0]][1] - 2, ys[0] + 1
    sx1, sy1 = region[ys[-1]][0] + 6, 63
    n = max(1, sy1 - sy0)
    for i in range(n + 1):
        y = sy0 + i
        x = round(sx0 + (sx1 - sx0) * i / n)
        for dx in (0, 1):
            if y in region and region[y][0] < x + dx < region[y][1] - 1:
                g[y][x + dx] = strap
    # the bag itself just shows at the bottom edge by the hip
    xl = region[ys[-1]][0]
    for y in range(58, 64):
        for x in range(xl, xl + 9):
            if 0 <= x < 64 and g[y][x]:
                edge = y == 58 or x == xl or x == xl + 8
                g[y][x] = 15 if edge else bag
    return g


# ---------------------------------------------------------------- girl, built on Red's back sprite
def girl(g):
    """Her reference: hair pulled up into a big wavy high ponytail (nape showing), a
    yellow ribbon tied at its base, bangs with a cream streak; maroon jacket, cream hood."""
    import math
    g = debag(g, (7, 5, 8), (9, 10), (13, 14), 6, 9)
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
    # hair is drawn as layered shapes, each with its own dark outline so locks separate
    def shape(inside, light_dir=(-1, -1)):
        pts = {(x, y) for y in range(64) for x in range(64) if inside(x + .5, y + .5)}
        for x, y in pts:
            edge = any((x + dx, y + dy) not in pts for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            g[y][x] = 6 if edge else 4
        return pts

    def shade(pts, centre_fn):
        for x, y in pts:
            if g[y][x] == 6:
                continue
            off = centre_fn(x + .5, y + .5)
            if -0.8 < off < -0.15:
                g[y][x] = 1
            elif off > 0.82:
                g[y][x] = 6

    def lock(path, wave=0.0, phase=0.0):
        """A lock of hair along path [(x, y, r)...] with a wavy edge."""
        segs = list(zip(path, path[1:]))

        def near(x, y):
            best = None
            for (ax, ay, ar), (bx_, by_, br) in segs:
                vx, vy = bx_ - ax, by_ - ay
                t = max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy)))
                qx, qy = ax + vx * t, ay + vy * t
                r = ar + (br - ar) * t
                r += wave * math.sin((ay + vy * t) * 0.9 + phase)
                dist = math.hypot(x - qx, y - qy)
                # signed: negative on the left of the direction of travel (the lit side)
                side = (x - qx) * vy - (y - qy) * vx
                if best is None or dist / r < best[0]:
                    best = (dist / r, math.copysign(dist / r, -side))
            return best

        pts = shape(lambda x, y: near(x, y)[0] <= 1)
        shade(pts, lambda x, y: near(x, y)[1])
        return pts

    X, Y = x0, y0                                            # anchor: top-left of Red's cap
    cx, cy = (x0 + x1) / 2 - 0.5, y1 + 2.0
    rx, ry = (x1 - x0) / 2, (y1 - y0) + 1.0
    face_l = lambda y: face_left.get(int(y), 64)
    crown = shape(lambda x, y: ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1
                  and not (y >= y1 - 0.5 and x >= face_l(y) - 1) and (y < y1 + 1 or g[int(y)][int(x)] in (0, 1, 4, 8, 15)))
    shade(crown, lambda x, y: ((x - cx) / rx + (y - cy) / ry) * 0.9)
    for k in (0.35, 0.65):                                   # two strands combed up to the ponytail
        for t in range(40):
            tt = t / 39
            x = int(cx + rx * (0.15 + 0.5 * k) - (rx * 0.9) * tt * tt)
            y = int(cy - ry * 0.15 - ry * 0.75 * tt + k * 3)
            if (x, y) in crown and g[y][x] != 6:
                g[y][x] = 6
    # the ponytail: a puff above the crown, then locks falling down the back of the head
    lock([(X + 6, Y + 1, 5.5), (X + 1, Y - 5, 6.5), (X - 6, Y - 4, 5.5)], wave=0.6)
    lock([(X - 2, Y - 2, 5.0), (X - 9, Y + 4, 5.0), (X - 10, Y + 12, 4.0), (X - 7, Y + 18, 2.5)], wave=0.8, phase=1)
    lock([(X + 3, Y + 1, 4.0), (X - 4, Y + 7, 4.0), (X - 5, Y + 14, 3.0), (X - 2, Y + 18, 2.0)], wave=0.7, phase=2)
    # yellow ribbon tied at the base of the ponytail, loops pointing up and back
    ribbon = ["...6666.......",
              "..6dddd6..66..",
              ".6ddddde66dd6.",
              ".6dddeeddddde6",
              "..66ddeedde66.",
              "....6edde6....",
              "...6dde66d6...",
              "..6dde6..6e6..",
              "..666.....6..."]
    put(g, X + 3, Y - 7, ribbon, {'6': 6, 'd': 13, 'e': 14})
    # bangs over the forehead, one cream lock
    fl = min(face_l(y) for y in range(y1 - 1, y1 + 3))
    for i, x in enumerate(range(fl - 2, int(cx + rx) + 1)):
        tip = y1 + (2 if i % 3 == 2 else 1)
        for y in range(y1 - 3, min(64, tip + 1)):
            if y == tip:
                g[y][x] = 6
            elif i == 2:
                g[y][x] = 9 if y < tip - 1 else 10
            else:
                g[y][x] = 1 if (i + y) % 3 == 0 else 4
    # clothes: Red's red jacket and blue sleeves become maroon
    for y in range(y1 + 8, 64):
        for x in range(64):
            v = g[y][x]
            if v in (11, 12, 6, 5):
                g[y][x] = {11: 7, 12: 5, 6: 8, 5: 5}[v]
    return g
