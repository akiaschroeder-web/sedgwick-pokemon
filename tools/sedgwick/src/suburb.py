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
    """2 x 2, facing west, drawn to match FRLG's moving truck (SS Anne dock): side view
    with a sliver of roof, big pale windows, dark outline, skirt and hubbed wheels."""
    P = Pic(2, 2)
    glass, glint = (ML, WH) if paint != WH else (MM, ML)
    hi = WH if paint not in (WH, ML) else (WH if paint == ML else ML)
    if kind == 'sedan':
        P.rect(1, 18, 30, 23, paint)                       # body sides
        P.rect(1, 22, 30, 25, dark)                        # lower body
        P.rect(2, 18, 29, 18, hi)                          # beltline glint
        for y in range(10, 18):                            # cabin: slanted windscreen and rear glass
            t = y - 10
            x0, x1 = 10 - t * 4 // 7, 21 + t * 4 // 7
            P.rect(x0, y, x1, y, paint if y <= 11 else glass)
        P.rect(10, 10, 21, 10, hi)                         # roof seen from above
        P.rect(15, 12, 16, 17, paint)                      # B pillar
        P.rect(8, 12, 9, 13, glint); P.rect(18, 12, 19, 12, glint)
        P.rect(1, 20, 2, 21, YL)                           # headlight (front = west)
        P.rect(29, 20, 30, 21, RD if paint != RD else RDD) # tail light
        P.rect(1, 24, 4, 25, MM); P.rect(27, 24, 30, 25, MM)   # bumpers
        wheels = (7, 24)
    else:
        P.rect(1, 17, 30, 23, paint)
        P.rect(1, 22, 30, 25, dark)
        P.rect(2, 17, 15, 17, hi)
        for y in range(9, 17):                             # cab well forward, upright back
            t = y - 9
            x0 = 9 - t * 4 // 7
            P.rect(x0, y, 15, y, paint if y <= 10 else glass)
        P.rect(9, 9, 15, 9, hi)
        P.rect(12, 11, 12, 16, paint)
        P.rect(7, 11, 8, 12, glint)
        P.rect(17, 15, 30, 17, paint); P.rect(17, 15, 30, 15, hi)   # bed rail
        P.rect(18, 16, 29, 17, dark)                       # bed seen over the side
        P.rect(1, 19, 2, 20, YL)
        P.rect(29, 18, 30, 19, RD if paint != RD else RDD)
        P.rect(1, 24, 4, 25, MM); P.rect(27, 24, 30, 25, MM)
        wheels = (7, 24)
    for wx in wheels:                                      # wheel wells and tyres
        for y in range(22, 30):
            for x in range(wx - 4, wx + 5):
                if (x - wx) ** 2 + ((y - 26) * 1.15) ** 2 <= 15:
                    P.px(x, y, BK)
        P.rect(wx - 1, 25, wx, 27, MM); P.px(wx - 1, 25, ML)   # hub
    g = [row[:] for row in P.p]
    for y in range(P.h):                                   # outline the silhouette
        for x in range(P.w):
            if g[y][x] and g[y][x] != BK and any(not (0 <= x + dx < P.w and 0 <= y + dy < P.h) or not g[y + dy][x + dx]
                                                  for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                P.px(x, y, O)
    for x in range(3, 29):
        if not P.p[30][x]:
            P.px(x, 30, SH)
    return P.p


VEHICLES = {'sedan': ('red', 'white', 'silver', 'black'), 'pickup': ('white', 'green')}


def vehicles():
    """name -> 16x16 grid: '<kind>_<colour>_<w|e>_<col><row>'. Row 1 sits in the lane,
    row 0 (roof) on the tile above it."""
    out = {}
    paints = {'red': (RD, RDD), 'green': (GN, GND), 'white': (WH, ML), 'black': (BK, O), 'silver': (ML, MM)}
    for kind, colours in VEHICLES.items():
        for name in colours:
            p, d = paints[name]
            g = car(p, d, kind)
            for facing, gg in (('w', g), ('e', [row[::-1] for row in g])):
                for r in range(2):
                    for c in range(2):
                        out[f'{kind}_{name}_{facing}_{c}{r}'] = [row[c * 16:(c + 1) * 16] for row in gg[r * 16:(r + 1) * 16]]
    return out


def all_pieces():
    out = {}
    out.update(water_tower())
    out.update(bus_shelter())
    return out
