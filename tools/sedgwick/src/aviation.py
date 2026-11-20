"""Airport, aircraft plants and the air base.

Runways/taxiways/aprons use the street palette. Hangars and plant buildings reuse
farm2's Vermilion corrugated-roof kit with a wide hangar door. The control tower,
parked aircraft, guard booth and gate arm are drawn new in an 'aviation' palette
following the same rules (dark blue-grey outline, light from the upper left)."""
import math
import street
from street import asph_px, conc_px, CL, CC, CS, CX, A, B, WP, YP, YS, KD
import farm2

# ---------------------------------------------------------------- airfield surfaces (street palette)
def _t(fn):
    return [[fn(x, y) for x in range(16)] for y in range(16)]


def airfield():
    out = {}
    a = asph_px
    # runway oriented E-W, 3 tiles wide: edge N, centre, edge S
    out['rwy_edge_n'] = _t(lambda x, y: street.grass_px(x, y) if y < 3 else (WP if y in (4, 5) else a(x, y)))
    out['rwy_edge_s'] = _t(lambda x, y: street.grass_px(x, y) if y > 12 else (WP if y in (10, 11) else a(x, y)))
    out['rwy_center'] = _t(lambda x, y: WP if (y in (7, 8) and x % 16 < 10) else a(x, y))
    out['rwy_plain'] = _t(a)
    # threshold "piano keys" (runway end, stripes run along the runway)
    out['rwy_threshold'] = _t(lambda x, y: WP if (y % 4 in (1, 2) and 2 <= x <= 13) else a(x, y))
    out['rwy_end_w'] = _t(lambda x, y: street.grass_px(x, y) if x < 3 else (WP if x in (4, 5) else a(x, y)))
    out['rwy_end_e'] = _t(lambda x, y: street.grass_px(x, y) if x > 12 else (WP if x in (10, 11) else a(x, y)))
    # taxiways: asphalt with a yellow centreline, grass shoulders
    out['twy_h'] = _t(lambda x, y: street.grass_px(x, y) if (y < 2 or y > 13) else (YP if y in (7, 8) else a(x, y)))
    out['twy_v'] = _t(lambda x, y: street.grass_px(x, y) if (x < 2 or x > 13) else (YP if x in (7, 8) else a(x, y)))
    out['twy_hold'] = _t(lambda x, y: street.grass_px(x, y) if (x < 2 or x > 13) else
                         (YP if y in (4, 6) or (y in (9, 11) and x % 4 < 2) else a(x, y)))
    # concrete apron with expansion joints
    out['apron'] = _t(lambda x, y: CS if (x % 16 == 15 or y % 16 == 15) else conc_px(x, y))
    out['apron_stand'] = _t(lambda x, y: YP if (x in (7, 8) and y > 2) else (CS if (x % 16 == 15 or y % 16 == 15) else conc_px(x, y)))
    return out


# ---------------------------------------------------------------- hangar door on the farm2 kit
def hangar_door_pieces(width=4, kind='shed'):
    """A tall hangar door `width` metatiles wide across rows C, M, D of the farm2 kit."""
    base_c = farm2.boards(farm2.T(690))
    base_m = farm2.boards(farm2.T(586))
    base_d1 = farm2.boards(farm2.T(602))
    bands = [base_c, base_m, base_m, base_m, base_d1]
    W, H = width * 16, 8 * len(bands)
    canvas = [[bands[y // 8][y % 8][x % 8] for x in range(W)] for y in range(H)]
    O, G5, G6, LG = farm2.OUT, farm2.G5, farm2.G6, farm2.LGRAY
    x0, x1, y0, y1 = 2, W - 3, 3, H - 8
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if x in (x0, x1) or y == y0:
                v = O
            elif (x - x0) % 16 == 0:
                v = G6                                  # door leaf seams
            elif (y - y0) % 4 == 0:
                v = G5
            else:
                v = LG
            canvas[y][x] = v
    out = {}
    for c in range(width):
        def q(band, half):
            g = canvas[band * 8:(band + 1) * 8]
            return [row[c * 16 + half * 8:c * 16 + half * 8 + 8] for row in g]
        out[f'wallC_hangar{c}'] = dict(top=[farm2.T(674), farm2.T(674), q(0, 0), q(0, 1)], under=[None] * 4,
                                       layer='NORMAL', beh='MB_NORMAL')
        out[f'wallM_hangar{c}'] = dict(top=[q(1, 0), q(1, 1), q(2, 0), q(2, 1)], under=[None] * 4,
                                       layer='COVERED', beh='MB_NORMAL')
        out[f'wallD_hangar{c}'] = dict(top=[q(3, 0), q(3, 1), q(4, 0), q(4, 1)], under=[None] * 4,
                                       layer='COVERED', beh='MB_NORMAL')
    return out


def hangar_plan(width, door_width=4, roof_rows=2):
    rows = [['roofA_l'] + ['roofA_m'] * (width - 2) + ['roofA_r']]
    for _ in range(roof_rows):
        rows.append(['roofB_l'] + ['roofB_m'] * (width - 2) + ['roofB_r'])
    d0 = (width - door_width) // 2
    for w in ('C', 'M', 'D'):
        row = [f'wall{w}_l'] + [f'wall{w}_m'] * (width - 2) + [f'wall{w}_r']
        for i in range(door_width):
            row[d0 + i] = f'wall{w}_hangar{i}'
        rows.append(row)
    return rows


PAL_PLANT = farm2.recolor(roof=[(156, 197, 238), (106, 156, 213), (74, 115, 180)],
                          walls=[(255, 255, 255), (238, 242, 246), (213, 222, 230), (180, 189, 205), (148, 156, 172)],
                          base_strip=(98, 106, 123))

# ---------------------------------------------------------------- aviation palette and drawn pieces
PAL_AV = [(255, 0, 255), (57, 65, 90),
          (255, 255, 255), (222, 230, 238), (180, 189, 205), (131, 139, 156),
          (172, 222, 255), (98, 164, 222), (57, 106, 172),
          (222, 74, 74), (156, 41, 57),
          (246, 205, 82), (205, 205, 197), (164, 164, 156), (98, 106, 115), (90, 98, 115)]
O, WH, L, M, D, GLL, GLM, GLD, RED, REDD, YEL, CN, CND, TYRE, SHADOW = range(1, 16)


class Pic:
    def __init__(self, wt, ht):
        self.w, self.h, self.wt, self.ht = wt * 16, ht * 16, wt, ht
        self.p = [[0] * self.w for _ in range(self.h)]

    def px(self, x, y, v):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = v

    def rect(self, x0, y0, x1, y1, v):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, v)

    def poly(self, pts, v):
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
                if (y1 <= y + .5 < y2) or (y2 <= y + .5 < y1):
                    xs.append(x1 + (y + .5 - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(round(xs[i])), int(round(xs[i + 1]))):
                    self.px(x, y, v)

    def outline(self):
        g = [row[:] for row in self.p]
        for y in range(self.h):
            for x in range(self.w):
                if g[y][x] and g[y][x] != SHADOW:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if not (0 <= nx < self.w and 0 <= ny < self.h) or g[ny][nx] in (0, SHADOW):
                            self.p[y][x] = O
                            break

    def tiles(self, prefix):
        return {f'{prefix}_{c}{r}': [row[c * 16:(c + 1) * 16] for row in self.p[r * 16:(r + 1) * 16]]
                for r in range(self.ht) for c in range(self.wt)}


def control_tower():
    """2 x 5: concrete shaft with a glass cab and a railed roof."""
    P = Pic(2, 5)
    P.rect(11, 30, 20, 76, CN); P.rect(11, 30, 12, 76, L); P.rect(18, 30, 20, 76, CND)
    for y in range(36, 76, 8):
        P.rect(14, y, 17, y + 2, GLD)
    P.rect(3, 22, 28, 29, CND)                       # cab underside
    P.rect(3, 12, 28, 21, GLM)                       # glass cab
    P.rect(3, 12, 28, 14, GLL)
    for x in (9, 16, 22):
        P.rect(x, 12, x, 21, D)
    P.rect(2, 6, 29, 11, M); P.rect(2, 6, 29, 7, L)  # roof plane
    P.rect(15, 1, 16, 5, D)                          # antenna
    P.rect(14, 1, 17, 1, RED)
    P.outline()
    P.rect(8, 77, 23, 78, SHADOW)
    return P.tiles('tower')


def jet():
    """4 x 3 regional jet seen from above, nose to the east."""
    P = Pic(4, 3)
    cy = 24
    P.poly([(6, cy - 3), (54, cy - 3), (62, cy), (54, cy + 3), (6, cy + 3)], WH)     # fuselage
    P.rect(8, cy - 3, 52, cy - 2, L)
    P.poly([(26, cy - 3), (38, cy - 3), (24, cy - 21), (19, cy - 21)], L)            # wings
    P.poly([(26, cy + 3), (38, cy + 3), (24, cy + 21), (19, cy + 21)], M)
    P.poly([(6, cy - 2), (12, cy - 2), (4, cy - 10), (1, cy - 10)], L)               # tailplane
    P.poly([(6, cy + 2), (12, cy + 2), (4, cy + 10), (1, cy + 10)], M)
    P.rect(28, cy - 10, 33, cy - 7, D); P.rect(28, cy + 7, 33, cy + 10, D)           # engines
    P.rect(4, cy - 1, 14, cy + 1, RED)                                               # tail fin seen from above
    P.rect(16, cy - 1, 52, cy - 1, GLM)                                              # window line / livery
    P.rect(55, cy - 1, 58, cy, GLD)                                                  # cockpit
    P.outline()
    for x in range(10, 56):
        P.px(x, cy + 5, SHADOW)
    return P.tiles('jet')


def prop_plane():
    """2 x 2 high-wing single-engine plane seen from above, nose east."""
    P = Pic(2, 2)
    cy = 16
    P.poly([(5, cy - 2), (24, cy - 2), (28, cy), (24, cy + 2), (5, cy + 2)], WH)
    P.rect(14, cy - 13, 19, cy + 13, L)                                              # straight high wing
    P.rect(14, cy - 13, 19, cy - 12, WH)
    P.rect(16, cy - 13, 17, cy + 13, M)
    P.rect(2, cy - 6, 6, cy + 6, L)                                                  # tailplane
    P.rect(7, cy - 1, 22, cy - 1, RED)                                               # stripe
    P.rect(28, cy - 4, 29, cy + 4, D)                                                # propeller
    P.outline()
    return P.tiles('cessna')


def guard_booth():
    """1 x 2 gatehouse with a flat roof and windows."""
    P = Pic(1, 2)
    P.rect(1, 6, 14, 12, M); P.rect(1, 6, 14, 7, L)
    P.rect(2, 13, 13, 29, WH)
    P.rect(4, 15, 11, 21, GLM); P.rect(4, 15, 11, 16, GLL)
    P.rect(2, 26, 13, 29, D)
    P.outline()
    return P.tiles('guard_booth')


def gate_arm():
    """1 x 1 striped barrier arm across a lane."""
    P = Pic(1, 1)
    P.rect(1, 6, 3, 13, M)
    for x in range(3, 16):
        P.rect(x, 7, x, 9, RED if (x // 3) % 2 else WH)
    P.outline()
    return {'gate_arm': P.p}


def drawn():
    out = {}
    for fn in (control_tower, jet, prop_plane, guard_booth):
        out.update(fn())
    out.update(gate_arm())
    return out
