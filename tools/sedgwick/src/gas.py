"""Gas station: canopy over a concrete pad with pumps, and a price-sign pylon.
Drawn new (neither game has one) using FRLG building rules: dark blue-grey
outline, light from the upper left, roof plane seen from above, short front face."""
PAL_GAS = [(255, 0, 255), (65, 74, 106),
           (246, 246, 255), (205, 213, 222), (164, 172, 189), (123, 131, 148),
           (238, 106, 90), (205, 65, 65), (148, 41, 49), (246, 213, 74),
           (230, 230, 222), (205, 205, 197), (172, 172, 164),
           (156, 213, 255), (98, 164, 222), (57, 57, 65)]
O, WH, L, M, D, RL, R, RD, Y, CL, CC, CS, GL, GD, K = range(1, 16)


def pad_px(x, y):
    if x % 32 == 31 or y % 32 == 31:
        return CS                       # expansion joints
    return CS if (x * 7 + y * 13) % 31 == 0 else CC


class Pic:
    def __init__(self, wt, ht, bg=None):
        self.w, self.h, self.wt, self.ht = wt * 16, ht * 16, wt, ht
        self.p = [[(bg(x, y) if bg else 0) for x in range(self.w)] for y in range(self.h)]

    def rect(self, x0, y0, x1, y1, v):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                self.p[y][x] = v

    def tiles(self, prefix):
        return {f'{prefix}_{c}{r}': [row[c * 16:(c + 1) * 16] for row in self.p[r * 16:(r + 1) * 16]]
                for r in range(self.ht) for c in range(self.wt)}


def canopy(width=5):
    """width x 3: two rows of canopy roof (top layer, walk under) and a row of pumps."""
    W = width * 16
    top = Pic(width, 2)
    # roof plane
    top.rect(0, 2, W - 1, 21, L)
    for x in range(8, W - 4, 16):
        top.rect(x, 3, x, 20, M)        # panel seams
    top.rect(1, 3, W - 2, 3, WH)        # lit back edge
    top.rect(0, 2, W - 1, 2, O)
    top.rect(0, 2, 0, 29, O)
    top.rect(W - 1, 2, W - 1, 29, O)
    # red fascia on the front edge
    top.rect(1, 22, W - 2, 28, R)
    top.rect(1, 22, W - 2, 22, RL)
    top.rect(1, 25, W - 2, 25, WH)      # white stripe
    top.rect(1, 28, W - 2, 28, RD)
    top.rect(0, 29, W - 1, 29, O)
    # pillars below the fascia
    for x in (6, W - 10):
        top.rect(x, 30, x + 3, 31, M)
        top.rect(x - 1, 30, x - 1, 31, O)
        top.rect(x + 4, 30, x + 4, 31, O)
    pumps = Pic(width, 1, bg=pad_px)
    for x in (6, W - 10):               # pillars continue down to the pad
        pumps.rect(x, 0, x + 3, 12, M)
        pumps.rect(x, 0, x, 12, L)
        pumps.rect(x - 1, 0, x - 1, 12, O)
        pumps.rect(x + 4, 0, x + 4, 12, O)
        pumps.rect(x - 1, 13, x + 4, 13, O)
    for i, x in enumerate(range(16, W - 16, 16)):
        pumps.rect(x + 2, 1, x + 11, 13, WH)     # pump body
        pumps.rect(x + 2, 1, x + 11, 3, R)       # brand band
        pumps.rect(x + 4, 5, x + 9, 8, GD)       # screen
        pumps.rect(x + 4, 5, x + 9, 5, GL)
        pumps.rect(x + 3, 10, x + 10, 11, M)     # nozzle holster
        pumps.rect(x + 1, 0, x + 1, 13, O)
        pumps.rect(x + 12, 0, x + 12, 13, O)
        pumps.rect(x + 1, 0, x + 12, 0, O)
        pumps.rect(x + 1, 14, x + 12, 14, O)
        pumps.rect(x + 2, 15, x + 11, 15, CS)    # shadow on the pad
    return top.tiles('gas_canopy'), pumps.tiles('gas_pumps')


def pad():
    p = Pic(1, 1, bg=pad_px)
    return p.p


def price_sign():
    """1 x 2 pylon: red sign box with yellow price digits (abstract) on a pole."""
    t = Pic(1, 2)
    t.rect(2, 2, 13, 17, R)
    t.rect(2, 2, 13, 2, RL)
    t.rect(1, 1, 14, 1, O); t.rect(1, 18, 14, 18, O); t.rect(1, 1, 1, 18, O); t.rect(14, 1, 14, 18, O)
    t.rect(3, 4, 12, 7, WH)                 # logo panel
    t.rect(5, 5, 10, 6, R)
    for yy in (10, 14):                     # two price rows
        t.rect(3, yy, 12, yy + 2, K)
        for xx in (4, 7, 10):
            t.rect(xx, yy, xx + 1, yy + 2, Y)
    t.rect(7, 19, 8, 29, M)
    t.rect(6, 19, 6, 29, O); t.rect(9, 19, 9, 29, O)
    t.rect(5, 30, 10, 30, O)
    return t.tiles('gas_sign')
