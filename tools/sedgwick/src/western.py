"""Old Cowtown: 1870s western buildings drawn new in the FRLG manner (dark outline,
light from the upper left, front faces seen straight on, roofs from above).

  storefront  4x4  false-front clapboard store: sign board, upstairs windows, porch awning
                   on posts, shop windows and a door onto the boardwalk.   door (2,3)
  cabin       4x3  shingle-roof house with a log front, door and window.   door (1,2)
  entry       8x5  the museum's entrance hall: tall false front with the COWTOWN sign,
                   front double doors into the town (3,4)/(4,4), and a back doorway
                   through the roof line from the street side (3,0)/(4,0) - a gatehouse.
  boardwalk, dirt  ground; hitching post, barrel, water trough, wagon (2x1) props.

Every building comes in several paint/wood colours: same tiles, different palette."""
WOOD = {
    'weathered': [(197, 189, 172), (156, 148, 131), (115, 106, 98), (148, 41, 49)],
    'red': [(222, 115, 90), (180, 74, 65), (131, 49, 49), (49, 74, 131)],
    'ochre': [(238, 205, 123), (205, 164, 90), (156, 115, 65), (148, 41, 49)],
    'white': [(246, 246, 238), (213, 213, 205), (164, 164, 156), (49, 98, 65)],
    'brown': [(197, 139, 90), (164, 106, 65), (123, 82, 49), (205, 164, 65)],
}
VARIANTS = list(WOOD)


def palette(v):
    hi, mid, dk, sign = WOOD[v]
    return [(255, 0, 255), (57, 41, 41), hi, mid, dk,
            (238, 230, 205), (197, 180, 148),
            (172, 222, 238), (82, 123, 172),
            (197, 131, 90), (156, 98, 65), (106, 65, 41),
            sign, (41, 33, 33), (222, 189, 131), (172, 131, 90)]


O, WH, WM, WD, TL, TM, GL, GD, RH, RM, RD, SG, IN, PL, PD = range(1, 16)


class Cv:
    def __init__(self, wt, ht, bg=0):
        self.wt, self.ht, self.w, self.h = wt, ht, wt * 16, ht * 16
        self.p = [[bg] * self.w for _ in range(self.h)]

    def r(self, x0, y0, x1, y1, v):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                self.p[y][x] = v

    def box(self, x0, y0, x1, y1, fill, edge=O):
        self.r(x0, y0, x1, y1, edge)
        self.r(x0 + 1, y0 + 1, x1 - 1, y1 - 1, fill)

    def px(self, x, y, v):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = v

    def tiles(self, prefix):
        return {f'{prefix}_{c}{r}': [row[c * 16:(c + 1) * 16] for row in self.p[r * 16:(r + 1) * 16]]
                for r in range(self.ht) for c in range(self.wt)}


def clapboard(cv, x0, y0, x1, y1, dark=False):
    """Horizontal boards: a lit edge on top of each board, a shadow line under it."""
    for y in range(y0, y1 + 1):
        k = (y - y0) % 4
        v = (WD if k == 3 else WM) if not dark else (WD if k in (2, 3) else WM)
        if k == 0 and not dark:
            v = WH
        cv.r(x0, y, x1, y, v)


def window(cv, x0, y0, x1, y1):
    cv.box(x0, y0, x1, y1, TL)
    cv.r(x0 + 2, y0 + 2, x1 - 2, y1 - 2, GD)
    cv.r(x0 + 2, y0 + 2, x1 - 2, y0 + 2 + (y1 - y0 - 4) // 2, GL)
    cv.r((x0 + x1) // 2, y0 + 1, (x0 + x1) // 2, y1 - 1, TM)      # muntin
    cv.r(x0 + 1, y1, x1 - 1, y1, TM)                                 # sill shadow


def door(cv, x0, y0, x1, y1):
    cv.box(x0, y0, x1, y1, WD)
    cv.r(x0 + 2, y0 + 2, x1 - 2, y0 + 7, GD)                        # glass top
    cv.r(x0 + 2, y0 + 2, x1 - 2, y0 + 3, GL)
    cv.r(x0 + 2, y0 + 9, x1 - 2, y1, IN)
    cv.r(x0 + 3, y0 + 10, x1 - 3, y1, WD)                           # panel
    cv.px(x1 - 3, (y0 + y1) // 2 + 3, TL)                            # knob


def awning(cv, x0, y0, x1, y1):
    cv.r(x0, y0, x1, y1, RM)
    cv.r(x0, y0, x1, y0, RH)
    for x in range(x0, x1 + 1, 4):
        cv.r(x, y0 + 1, x, y1 - 1, RD)                               # tin roof ribs
    cv.r(x0, y1, x1, y1, O)


def boardwalk(cv, y0, y1, x0=0, x1=None):
    x1 = cv.w - 1 if x1 is None else x1
    for y in range(y0, y1 + 1):
        cv.r(x0, y, x1, y, PD if (y - y0) % 3 == 2 else PL)
    for x in range(x0 + 7, x1, 16):
        cv.r(x, y0, x, y1, PD)


def letters(cv, text, x0, y0, v):
    font = {'C': ['01110', '10001', '10000', '10000', '10000', '10001', '01110'],
            'O': ['01110', '10001', '10001', '10001', '10001', '10001', '01110'],
            'W': ['10001', '10001', '10001', '10101', '10101', '11011', '10001'],
            'T': ['11111', '00100', '00100', '00100', '00100', '00100', '00100'],
            'N': ['10001', '11001', '10101', '10101', '10011', '10001', '10001']}
    for i, ch in enumerate(text):
        for yy, row in enumerate(font[ch]):
            for xx, b in enumerate(row):
                if b == '1':
                    cv.px(x0 + i * 7 + xx, y0 + yy, v)


def storefront():
    cv = Cv(4, 4)
    W = cv.w - 1
    # false front: square parapet with a raised centre and a cap
    cv.box(0, 3, W, 20, WM)
    cv.box(14, 0, W - 14, 6, WM)
    cv.r(1, 4, W - 1, 5, TL); cv.r(15, 1, W - 15, 2, TL)
    cv.r(15, 3, W - 15, 6, WM); cv.r(14, 3, 14, 6, O); cv.r(W - 14, 3, W - 14, 6, O)
    cv.r(1, 4, 13, 5, TL); cv.r(W - 13, 4, W - 1, 5, TL)
    # sign board with lettering
    cv.box(5, 8, W - 5, 18, TL)
    for x in range(10, W - 9, 4):
        cv.r(x, 11, x + 2, 15, SG)
    # upper storey
    clapboard(cv, 1, 21, W - 1, 38)
    cv.r(0, 21, 0, 63, O); cv.r(W, 21, W, 63, O)
    window(cv, 8, 23, 22, 36); window(cv, W - 22, 23, W - 8, 36)
    # porch awning on posts
    awning(cv, 0, 39, W, 44)
    clapboard(cv, 1, 45, W - 1, 59, dark=True)
    for x in (2, W - 4):
        cv.box(x, 44, x + 3, 60, TM)
    # shop windows and the door (column 2)
    window(cv, 8, 47, 30, 58)
    window(cv, 50, 47, W - 8, 58)
    door(cv, 34, 46, 46, 60)
    boardwalk(cv, 60, 63)
    return cv.tiles('wstore')


def cabin():
    cv = Cv(4, 3)
    W = cv.w - 1
    # shingle roof seen from the front-top, eaves overhanging the log wall
    cv.box(2, 1, W - 2, 27, RM)
    for y in range(4, 26, 5):
        cv.r(3, y, W - 3, y, RD)
        for x in range(3 + (y // 5 % 2) * 4, W - 3, 8):
            cv.r(x, y - 4, x, y - 1, RD)
    cv.r(3, 2, W - 3, 2, RH)
    cv.r(0, 25, W, 27, RD); cv.r(0, 27, W, 27, O); cv.r(0, 24, 0, 27, O); cv.r(W, 24, W, 27, O)
    # log wall: rounded logs with chinking
    for y in range(28, 47):
        k = (y - 28) % 5
        cv.r(2, y, W - 2, y, WH if k == 0 else WD if k == 4 else WM)
    for y in range(28, 47, 5):                       # log ends poking out at the corners
        for x in (0, W - 3):
            cv.box(x, y, x + 3, min(46, y + 4), WM)
    cv.r(0, 47, W, 47, O)
    door(cv, 19, 31, 29, 47)
    window(cv, 38, 31, 54, 42)
    return cv.tiles('wcabin')


def entry():
    cv = Cv(8, 5)
    W = cv.w - 1
    # row 0: the flat roof from above, with the street-side doorway through it
    cv.box(0, 2, W, 17, RD)
    for y in range(4, 16, 3):
        cv.r(1, y, W - 1, y, RM)
    cv.box(50, 2, 77, 17, IN)                        # back doorway (cols 3-4)
    cv.r(52, 4, 75, 4, TM)
    cv.r(51, 16, 76, 17, PD)
    # tall false front with the COWTOWN sign
    cv.box(0, 16, W, 39, WM)
    cv.box(30, 12, W - 30, 20, WM)
    cv.r(31, 13, W - 31, 14, TL)
    cv.r(1, 17, W - 1, 18, TL)
    cv.box(10, 21, W - 10, 36, TL)
    cv.r(12, 23, W - 12, 34, SG)
    letters(cv, 'COWTOWN', 64 - 24, 25, TL)
    # upper storey
    clapboard(cv, 1, 40, W - 1, 55)
    cv.r(0, 40, 0, 79, O); cv.r(W, 40, W, 79, O)
    for x in (8, 34, 76, 102):
        window(cv, x, 42, x + 17, 54)
    awning(cv, 0, 56, W, 61)
    clapboard(cv, 1, 62, W - 1, 76, dark=True)
    for x in (2, 40, 84, W - 4):
        cv.box(x, 61, x + 3, 77, TM)
    window(cv, 8, 64, 36, 75); window(cv, W - 36, 64, W - 8, 75)
    door(cv, 50, 63, 63, 77); door(cv, 64, 63, 77, 77)
    boardwalk(cv, 77, 79)
    return cv.tiles('wentry')


def ground():
    out = {}
    b = Cv(1, 1)
    boardwalk(b, 0, 15)
    out['wwalk'] = b.p
    d = Cv(1, 1, PL)
    for y in range(16):
        for x in range(16):
            h = (((x * 37 + y * 101 + x * y * 7) * 2654435761) >> 9) & 0xff
            if h < 22:
                d.px(x, y, PD)
            elif h < 30:
                d.px(x, y, TM)
    out['wdirt'] = d.p
    return out


def props():
    out = {}
    h = Cv(1, 1)                                     # hitching post
    h.box(1, 6, 14, 8, WM); h.r(2, 6, 13, 6, WH)
    for x in (2, 12):
        h.box(x, 6, x + 2, 15, WM)
    out['whitch'] = h.p
    b = Cv(1, 1)                                     # barrel
    b.box(3, 2, 12, 15, WM)
    b.r(4, 3, 11, 4, WH)
    for y in (5, 11):
        b.r(3, y, 12, y, O)
    b.r(4, 6, 5, 13, WH)
    out['wbarrel'] = b.p
    t = Cv(1, 1)                                     # water trough
    t.box(0, 6, 15, 14, WD)
    t.r(1, 7, 14, 9, GD); t.r(1, 7, 14, 7, GL)
    t.r(1, 10, 14, 13, WM)
    out['wtrough'] = t.p
    w = Cv(2, 1)                                     # freight wagon, side view
    w.box(2, 2, 29, 9, WM); w.r(3, 3, 28, 3, WH)
    for cx in (7, 24):
        w.box(cx - 5, 7, cx + 5, 15, WD)
        w.r(cx - 3, 9, cx + 3, 13, TM)
        w.box(cx - 1, 10, cx + 1, 12, O)
    out.update(w.tiles('wwagon'))
    return out


BUILDINGS = {'wstore': (4, 4, [(2, 3)]), 'wcabin': (4, 3, [(1, 2)]), 'wentry': (8, 5, [(3, 4), (4, 4), (3, 0), (4, 0)])}


def building_pieces():
    return {**storefront(), **cabin(), **entry()}
