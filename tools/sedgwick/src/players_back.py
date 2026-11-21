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
    g = [r[:] for r in g]
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
                g[y][x] = {13: 1, 14: 4, 5: 11, 7: 11, 6: 12}.get(v, v)   # bag brown, sleeves navy
    # yellow stripe across the sleeves and jacket, a third of the way down the torso
    body = [y for y in range(y1 + 8, 64) if any(g[y][x] in (11, 12) for x in range(64))]
    if body:
        sy = body[0] + max(4, len(body) // 3)
        for y in (sy, sy + 1):
            if y < 64:
                for x in range(64):
                    if g[y][x] in (11, 12):
                        g[y][x] = 13 if y == sy else 14
    return g


# ---------------------------------------------------------------- girl (from Leaf)
TAIL = ["....666....",
        "...61146...",
        "..6111446..",
        "..6dd6dd6..",
        ".6deddedd6.",
        "..6dd66dd6."]


def girl(g):
    import math
    g = [r[:] for r in g]
    h = hat(g, {9, 10})
    h |= {p for p in component(g, next(iter(h)), {9, 10, 11, 12, 6, 8, 15})
          if p[1] <= max(y for _, y in h) + 1}
    ys = sorted({y for _, y in h})
    y0 = ys[0]
    crown = [x for x, y in h if y <= y0 + (ys[-1] - y0) * 0.5]
    cx0, cx1 = min(crown), max(crown)
    y1 = max(y for y in range(y0, min(64, y0 + 20)) if sum(g[y][x] in (9, 10) for x in range(64)) >= 4)   # brim bottom
    for x, y in h:
        g[y][x] = 0                                          # hat off
    for y in range(y0, min(64, y1 + 1)):
        for x in range(64):
            if g[y][x] in (9, 10, 11, 12):
                g[y][x] = 0
    # skull: an ellipse whose bottom sits at eye level, lit from the upper left
    cx, cy = (cx0 + cx1) / 2 - 0.5, y1 + 1.5
    rx, ry = (cx1 - cx0) / 2 + 0.5, 11.0
    px, py = cx + rx * 0.45, cy - ry + 1                     # parting at the front of the crown
    face_x = min((x for y in range(y1 + 1, y1 + 4) for x in range(int(cx), min(64, int(cx + rx) + 4))
                  if g[y][x] in (2, 3)), default=int(cx + rx))
    for y in range(int(cy - ry), y1 + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            u, v = (x + .5 - cx) / rx, (y + .5 - cy) / ry
            d = math.hypot(u, v)
            if d > 1 or not (0 <= x < 64 and 0 <= y < 64):
                continue
            if y >= y1 - 1 and x >= face_x - 1:
                continue                                     # forehead and eyes stay visible
            ang = math.atan2(y + .5 - py, x + .5 - px)
            strand = (ang * 5) % 1.0 < 0.12 and 0.3 < d < 0.85
            if d > 0.9 and v < 0.45:
                v_ = 6
            elif u + v * 0.8 < -0.45:
                v_ = 4 if strand else 1
            elif u < -0.55 and v > 0.2:
                v_ = 6 if strand else 4
            else:
                v_ = 6 if strand and v > -0.2 else 4
            g[y][x] = v_
    # seam where the brim was: hair, then a fringe over the forehead
    for y in range(y1 - 1, min(64, y1 + 3)):
        for x in range(int(cx - rx) - 2, int(cx + rx) + 3):
            if 0 <= x < 64 and g[y][x] in (6, 8, 15) and x < face_x - 1 and x > int(cx - rx):
                g[y][x] = 4
            elif 0 <= x < 64 and g[y][x] in (6, 15) and x > cx + rx:
                g[y][x] = 0
    for y in range(y0, y1 + 1):                              # brim tip beyond the face
        for x in range(int(cx + rx) + 2, 64):
            if g[y][x] == 6:
                g[y][x] = 0
    for y in range(y1 - 2, min(64, y1 + 4)):                 # close gaps between crown and hair
        for x in range(int(cx - rx) + 1, face_x - 1):
            if g[y][x] == 0:
                g[y][x] = 4
    for i, x in enumerate(range(face_x - 1, int(cx + rx) + 1)):
        tip = y1 + (1 if i % 3 == 1 else 0)
        for y in range(y1 - 2, min(64, tip + 1)):
            g[y][x] = 6 if y == tip else (1 if (i + y) % 4 == 0 else 4)
    for y in range(64):
        for x in range(64):
            v = g[y][x]
            if y > y1 and v == 8 and y < y1 + 18:
                g[y][x] = 4 if y < y1 + 5 else 6
            elif y > y1 + 8:
                g[y][x] = {6: 5, 5: 7, 13: 9, 14: 10}.get(v, v)
    for y in range(max(0, y0 - 2), min(64, y1 + 3)):         # drop stray brim pixels
        for x in range(64):
            if g[y][x] and not any(0 <= x + dx < 64 and 0 <= y + dy < 64 and g[y + dy][x + dx]
                                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy):
                g[y][x] = 0
    # high ponytail at the back of the crown, bow at its base
    bx, by = int(cx - rx * 0.75), int(cy - ry) + 3
    put(g, bx - 6, by - 6, PONY, {'6': 6, '1': 1, '4': 4, 'd': 13, 'e': 14})
    return g


PONY = ["...666......",
        "..61146.....",
        ".6111446....",
        ".61446666...",
        "6144466dd6..",
        "614446deed6.",
        "6144646dd6..",
        "6144466.....",
        "61446.......",
        ".6146.......",
        ".6146.......",
        "..616.......",
        "..66........"]


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
    b = preview([girl(g) for g in frames('leaf')], GIRL_PAL)
    o = Image.new('RGB', (a.width, a.height * 2 + 10), (30, 30, 30))
    o.paste(a, (0, 0)); o.paste(b, (0, a.height + 10))
    o.save(sys.argv[1])
