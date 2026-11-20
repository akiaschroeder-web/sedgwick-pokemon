"""Suburban props (props palette, top layer): water tower, bus shelter, parked cars
and pickups in several paint colours."""
from props import PAL_PROPS

O, ML, MM, MD, BK, WH, RD, RDD, GN, GND, WL, WM, WD, YL, SH = range(1, 16)


class Pic:
    def __init__(self, wt, ht):
        self.w, self.h, self.wt, self.ht = wt * 16, ht * 16, wt, ht
        self.p = [[0] * self.w for _ in range(self.h)]

    def rect(self, x0, y0, x1, y1, v):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                self.p[y][x] = v

    def px(self, x, y, v):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = v

    def tiles(self, prefix):
        return {f'{prefix}_{c}{r}': [row[c * 16:(c + 1) * 16] for row in self.p[r * 16:(r + 1) * 16]]
                for r in range(self.ht) for c in range(self.wt)}


def water_tower():
    """2 x 4: a round tank (top seen from above) on four legs, town-name band."""
    import math
    P = Pic(2, 4)
    cx = 16
    # tank: ellipse top, cylinder body, rounded bottom
    for y in range(4, 30):
        for x in range(2, 30):
            inside_top = ((x + .5 - cx) / 14) ** 2 + ((y + .5 - 8) / 4.5) ** 2 <= 1
            body = 8 <= y <= 24 and 2 <= x <= 29
            bottom = ((x + .5 - cx) / 14) ** 2 + ((y + .5 - 24) / 5) ** 2 <= 1
            if inside_top or body or bottom:
                t = (x - 2) / 27
                v = ML if t < .3 else (MM if t < .75 else MD)
                if inside_top and y < 8:
                    v = ML if t < .55 else MM
                P.px(x, y, v)
    # outline
    import copy
    g = copy.deepcopy(P.p)
    for y in range(P.h):
        for x in range(P.w):
            if g[y][x] and any(not (0 <= x + dx < P.w and 0 <= y + dy < P.h) or not g[y + dy][x + dx]
                               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                P.px(x, y, O)
    P.rect(3, 13, 28, 18, WH)               # name band (town name via a sign event)
    P.rect(3, 13, 28, 13, MD); P.rect(3, 18, 28, 18, MD)
    P.rect(15, 1, 16, 4, MD)                # finial
    # legs and bracing
    for lx in (6, 13, 18, 25):
        P.rect(lx, 29, lx + 1, 60, MM)
        P.px(lx - 1, 30, O); P.rect(lx - 1, 29, lx - 1, 60, O); P.rect(lx + 2, 29, lx + 2, 60, O)
    for y0 in (36, 48):
        for i in range(19):
            P.px(7 + i, y0 + (i * 8) // 19, MD)
            P.px(25 - i, y0 + (i * 8) // 19, MD)
    P.rect(12, 30, 19, 60, 0)
    P.rect(14, 30, 17, 60, MM); P.rect(13, 30, 13, 60, O); P.rect(18, 30, 18, 60, O)   # riser pipe
    P.rect(4, 61, 27, 62, SH)
    return P.tiles('water_tower')


def bus_shelter():
    """2 x 2: glass shelter with a roof plane and a bench, plus the stop sign pole."""
    P = Pic(2, 2)
    P.rect(1, 4, 26, 11, MM); P.rect(1, 4, 26, 4, ML); P.rect(0, 3, 27, 3, O)
    P.rect(0, 3, 0, 12, O); P.rect(27, 3, 27, 12, O); P.rect(0, 12, 27, 12, O)
    for x in (2, 25):
        P.rect(x, 13, x + 1, 27, MD)
    P.rect(4, 13, 23, 22, WH)                 # back glass panel
    P.rect(4, 13, 23, 13, ML)
    P.rect(5, 23, 22, 25, WM); P.rect(5, 23, 22, 23, WL); P.rect(4, 26, 23, 26, O)   # bench
    P.rect(2, 28, 26, 29, SH)
    P.rect(29, 2, 30, 28, MM); P.rect(28, 2, 28, 28, O); P.rect(31, 2, 31, 28, O)
    P.rect(27, 0, 31, 6, GN); P.rect(27, 0, 31, 0, O); P.rect(27, 6, 31, 6, O)       # stop sign
    P.rect(28, 2, 30, 3, WH)
    return P.tiles('bus_shelter')


def car(paint, dark, kind='sedan'):
    """2 x 1, facing east: Pokemon-style 3/4 view (roof seen from above, side below)."""
    P = Pic(2, 1)
    if kind == 'sedan':
        P.rect(3, 4, 28, 12, paint)            # body
        P.rect(3, 9, 28, 12, dark)
        P.rect(9, 1, 22, 6, paint)             # cabin roof
        P.rect(9, 3, 22, 6, WH if paint != WH else MM)   # windows band
        P.rect(15, 3, 16, 6, paint)
        P.rect(27, 6, 28, 7, YL)               # headlight
        P.rect(3, 6, 3, 7, RD if paint != RD else RDD)   # tail light
        outline = [(2, 4, 2, 12), (29, 4, 29, 12), (3, 13, 28, 13), (3, 3, 8, 3), (23, 3, 28, 3), (9, 0, 22, 0),
                   (8, 1, 8, 2), (23, 1, 23, 2)]
    else:   # pickup: cab at the front, open bed behind
        P.rect(2, 5, 29, 12, paint)
        P.rect(2, 9, 29, 12, dark)
        P.rect(17, 1, 26, 6, paint)
        P.rect(18, 3, 25, 6, WH if paint != WH else MM)
        P.rect(4, 6, 15, 8, dark)              # bed
        P.rect(28, 7, 29, 8, YL)
        outline = [(1, 5, 1, 12), (30, 5, 30, 12), (2, 13, 29, 13), (2, 4, 16, 4), (27, 4, 29, 4), (17, 0, 26, 0),
                   (16, 1, 16, 3), (27, 1, 27, 3)]
    for x0, y0, x1, y1 in outline:
        P.rect(x0, y0, x1, y1, O)
    for wx in (7, 23):                         # wheels
        P.rect(wx - 2, 11, wx + 2, 14, BK)
        P.rect(wx - 1, 12, wx, 12, MM)
    P.rect(3, 15, 28, 15, SH)
    return P.p


def vehicles():
    out = {}
    paints = {'red': (RD, RDD), 'green': (GN, GND), 'white': (WH, ML), 'black': (BK, O), 'silver': (ML, MM)}
    for name, (p, d) in paints.items():
        for kind in ('sedan', 'pickup'):
            g = car(p, d, kind)
            out[f'{kind}_{name}_0'] = [row[0:16] for row in g]
            out[f'{kind}_{name}_1'] = [row[16:32] for row in g]
    return out


def all_pieces():
    out = {}
    out.update(water_tower())
    out.update(bus_shelter())
    out.update(vehicles())
    return out
