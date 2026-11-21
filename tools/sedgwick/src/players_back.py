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
    for x, y in cap:                                         # front panel (cream) faces the camera now
        v = g[y][x]
        if v == 8:
            g[y][x] = 6
        elif v == 15 and x0 < x < x1 and y0 < y < y1:
            g[y][x] = 9                                      # no strap hole on the front panel
        elif v in (11, 12):
            g[y][x] = (9 if v == 11 else 10) if x < mid + 3 else v
    for y in range(y1 - 2, y1 + 3):                          # Red's brim (pointing forward) comes off
        for x in range(mid, 64):
            if g[y][x] in (9, 10, 6):
                g[y][x] = 0
    for y in range(y1 - 2, min(64, y1 + 16)):                # hair: brown
        for x in range(max(0, x0 - 4), min(64, x1 + 2)):
            g[y][x] = {8: 4, 4: 1}.get(g[y][x], g[y][x])
    put(g, x0 - 5, y1 - 3, BRIM, {'6': 6, 'b': 11, 'c': 12})  # navy brim over the back of the neck
    for y in range(64):
        for x in range(64):
            v = g[y][x]
            if y > y1 + 6:
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
    g = [r[:] for r in g]
    h = hat(g, {9, 10})
    h |= {p for p in component(g, next(iter(h)), {9, 10, 11, 12, 6, 8, 15})
          if p[1] <= max(y for _, y in h) + 1}
    ys = sorted({y for _, y in h})
    y0, y1 = ys[0], ys[-1]
    crown = [x for x, y in h if y <= y0 + (y1 - y0) * 0.5]
    cx0, cx1 = min(crown), max(crown)
    for x, y in h:
        g[y][x] = 0                                          # hat off
    for y in range(y0, min(64, y1 + 3)):                     # and any brim pixels left over
        for x in range(64):
            if g[y][x] in (9, 10, 11, 12):
                g[y][x] = 0
    # rounded crown of hair where the hat was, lit from the upper left
    cx, rx = (cx0 + cx1) / 2 - 1, (cx1 - cx0) / 2 + 1
    top = y0 + 1
    ry = y1 + 2 - top
    for y in range(top, y1 + 3):
        for x in range(64):
            e = ((x + .5 - cx) / rx) ** 2 + ((y + .5 - (y1 + 2)) / ry) ** 2
            if e <= 1 and (g[y][x] == 0 or y <= y1):
                edge = e > 0.80 and y < y1
                lit = (x - cx) / rx + (y - top) / ry * 0.9 < -0.15
                g[y][x] = 6 if edge else (1 if lit else 4)
    for y in range(y1 - 1, min(64, y1 + 4)):                 # seam where hat met hair: hair now
        row = [x for x in range(64) if g[y][x]]
        for x in row:
            if x > cx + rx + 1:
                g[y][x] = 0 if g[y][x] in (6, 15) else g[y][x]
            elif g[y][x] in (6, 15, 8) and x != row[0] and x < cx + rx * 0.4:
                g[y][x] = 4
    for y in range(64):
        for x in range(64):
            v = g[y][x]
            if y > y1 and v == 8 and y < y1 + 18:
                g[y][x] = 4 if y < y1 + 5 else 6             # hair (no hat shadow any more)
            elif y > y1 + 8:
                g[y][x] = {6: 5, 5: 7, 13: 9, 14: 10}.get(v, v)
    put(g, int(cx - rx) + 3, top - 5, TAIL, {'6': 6, '1': 1, '4': 4, 'd': 13, 'e': 14})
    return g


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
    a = preview([boy(g) for g in frames('red')], BOY_PAL)
    b = preview([girl(g) for g in frames('leaf')], GIRL_PAL)
    o = Image.new('RGB', (a.width, a.height * 2 + 10), (30, 30, 30))
    o.paste(a, (0, 0)); o.paste(b, (0, a.height + 10))
    o.save(sys.argv[1])
