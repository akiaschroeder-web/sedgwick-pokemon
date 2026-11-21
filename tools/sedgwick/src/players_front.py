"""Battle front sprites (64x64: trainer card, intro, facing them in battle), edited from
FireRed's Red and Leaf: same pose and face, new palette, hand-placed edits for the cap,
hair and clothes."""
from PIL import Image
from lib import EXP

FRONT = f'{EXP}/graphics/trainers/front_pics'

# boy: Red's indices keep their roles; colours change (11 becomes hair brown)
BOY_FRONT_PAL = [(115, 197, 164), (255, 230, 180), (230, 189, 156), (205, 148, 115), (96, 58, 40),
                 (214, 196, 150), (172, 148, 104), (128, 104, 70), (24, 30, 60),
                 (226, 62, 56), (248, 196, 48), (150, 96, 56), (88, 106, 172), (50, 60, 118),
                 (246, 240, 220), (0, 0, 0)]
# girl: Leaf's indices; 12 and 11 become auburn hair, 5-7 maroon, 13 the dark shorts
GIRL_FRONT_PAL = [(115, 197, 164), (255, 230, 180), (230, 189, 156), (205, 148, 115), (92, 40, 36),
                  (200, 84, 96), (154, 48, 64), (104, 30, 44), (40, 38, 50),
                  (226, 62, 56), (248, 200, 56), (206, 120, 80), (150, 72, 52), (74, 72, 88),
                  (246, 240, 220), (0, 0, 0)]


def load(name):
    im = Image.open(f'{FRONT}/{name}.png')
    return [[im.getpixel((x, y)) for x in range(64)] for y in range(64)]


def overlay(g, x0, y0, art, key):
    for r, row in enumerate(art):
        for c, ch in enumerate(row):
            if ch != '.':
                g[y0 + r][x0 + c] = 0 if ch == '_' else key[ch]


def save(g, pal, path):
    im = Image.new('P', (64, 64))
    im.putpalette([c for col in pal for c in col])
    for y in range(64):
        for x in range(64):
            im.putpixel((x, y), g[y][x])
    im.save(path)


def preview(g, pal, scale=6):
    im = Image.new('RGB', (64, 64))
    for y in range(64):
        for x in range(64):
            im.putpixel((x, y), pal[g[y][x]])
    return im.resize((64 * scale, 64 * scale), Image.NEAREST)


def dump(g, y0=0, y1=64):
    print('    ' + ''.join(str(x % 10) for x in range(64)))
    for y in range(y0, y1):
        print(f'{y:2d}  ' + ''.join('.' if v == 0 else '%x' % v for v in g[y]))


# ---------------------------------------------------------------- boy (from Red)
BK = {'k': 8, 'N': 13, 'n': 12, 'c': 14, 'C': 5, 'h': 11, 'H': 4, 'o': 15, 's': 1, 'S': 2, 't': 3, 'y': 10, 'r': 9}

BOY_CAP = [                 # x 23.., y 8..: the back of the cap faces us
    "......kkkk.........",
    "....kkcccnnk.......",
    "...kccccnnnnNk.....",
    "..kcccccnnnnNNk....",
    "..kcccCcnnnnnNk....",
    "..kccCnnkkkknNNk...",
    "..kcCnnkhHhkNNNk...",
    ".kkkkkkkhhhkkkkkk..",
    "kHhhHkhhHhhkhHhhHk.",
    ".hHtHhstSHhsSHtHh..",
]
BOY_SIDE_HAIR = [           # x 22.., y 15..: spikes out from under the cap
    "k................Hk",
    "Hh...............hH",
    ".H................H",
    ".k.................",
]


def boy():
    g = load('red')
    src = [r[:] for r in g]
    for y in range(64):
        for x in range(64):
            v = src[y][x]
            ball = 42 <= x <= 50 and 29 <= y <= 35
            if ball and v in (12, 13):
                g[y][x] = 9                                  # the Poke Ball stays red
            elif v == 9:
                g[y][x] = 14 if y >= 55 else (9 if ball else 5)
            elif v == 10:
                g[y][x] = 4                                  # bag straps dark brown
            # yellow shirt down the open front of the jacket
            if 31 <= x <= 33 and 27 <= y <= 38 and v not in (0, 15):
                g[y][x] = 10
            elif x in (30, 34) and 27 <= y <= 38 and v not in (0, 15):
                g[y][x] = 14                                 # white piping on the jacket's edges
            # long sleeves: the bare upper arms become navy, cream cuffs at the wrists
            if v in (1, 2, 3) and ((16 <= x <= 27 and 19 <= y <= 27 and x + y >= 38 and not (x >= 24 and y <= 23)) or (36 <= x <= 42 and 33 <= y <= 37)):
                g[y][x] = 12 if v == 1 else 13
            if v in (1, 2, 3) and ((x in (16, 17) and 19 <= y <= 23) or (x == 43 and 33 <= y <= 37)):
                g[y][x] = 14
    for y in (31, 32):                                       # yellow stripe across the chest and sleeves
        for x in range(26, 42):
            if g[y][x] in (12, 13, 8) and src[y][x] not in (15,):
                g[y][x] = 10
    for x in range(20, 27):                                  # and on the raised sleeve
        y = 45 - x
        if 0 <= y < 64 and g[y][x] in (12, 13):
            g[y][x] = 10
    g[59][23] = 10                                           # sneakers: a flash of yellow
    g[60][37] = 10 if g[60][37] in (13, 8) else g[60][37]
    overlay(g, 23, 8, BOY_CAP, BK)
    overlay(g, 22, 15, BOY_SIDE_HAIR, BK)
    for x in range(29, 33):
        if g[18][x] == 4:
            g[18][x] = 1                                     # no hair between the eyes
    return g


SYM_BOY = {'.': 0, 's': 1, 'S': 2, 't': 3, 'H': 4, 'k': 5, 'K': 6, 'j': 7, 'M': 8, 'r': 9, 'y': 10,
           'h': 11, 'n': 12, 'N': 13, 'c': 14, 'o': 15}


def boy_drawn():
    """Red's head (cap turned round, see boy()) on a body redrawn to the reference sheet."""
    import players_front_art as A
    g = boy()
    for y, row in A.BOY.items():
        g[y][8:56] = [SYM_BOY[ch] for ch in row]
    return g


SYM_GIRL = {'.': 0, 's': 1, 'S': 2, 't': 3, 'd': 4, 'R': 5, 'M': 6, 'D': 7, 'b': 8, 'r': 9, 'y': 10,
            'l': 11, 'm': 12, 'g': 13, 'c': 14, 'o': 15, 'H': 4}


def girl_drawn():
    """Leaf's pose redrawn to the girl's reference sheet."""
    import players_front_art as A
    g = [[0] * 64 for _ in range(64)]
    for y, segs in A.GIRL_SEGS.items():
        for i, s in segs:
            for k, ch in enumerate(s):
                if ch != '.':
                    g[y][8 + i + k] = SYM_GIRL[ch]
    for y, i in A.GIRL_STRAP:
        for dx in (0, 1):
            if g[y][8 + i + dx] not in (0, 15):
                g[y][8 + i + dx] = 4
    # shift the whole figure to sit centred like Leaf (x 12..52)
    return [[0] * 4 + row[:60] for row in g]


# ---------------------------------------------------------------- girl, edited from Leaf's front sprite
GK = {'d': 4, 'm': 12, 'l': 11, 'y': 10, 'Y': 3, 'c': 14, 's': 1, 'S': 2, 't': 3, 'o': 15, '_': 0}

GIRL_HAIR_TOP = [            # x 18.., y 0..: big high ponytail, bow at its base, crown, bangs
    "........dddddd.............",
    "......ddllllmmd............",
    ".....dllllmmmmmd...........",
    "....dllmmmmmmmmmd..........",
    "...dlmmmmmdmmmmmmd.........",
    "..dlmmmmddmmmmmmmd...dd.dd.",
    ".dmmdmmd..dmmmmmmd..dyydyyd",
    ".dmd.dd...dmmmmmmmddyyyyyd.",
    "..d.......dmmmmmmmdyyyyyyd.",
    ".........ddmmmmmmmmdyyyd...",
    "........dmmllllmmmmmddd....",
    ".......dmllllllmmmmmmd.....",
    "......dmllmmmmmmmmmmmmd....",
    ".....dmlmmmmmmmmmmmmmmmd...",
    ".....dmlmmmmdmmmmmmmmmmd...",
    ".....dmmmcmdmmmmmdmmmmmmd..",
    ".....dmmccmdmmmmdmmmmdmmmd.",
    ".....dmdccdsdmmdsdmmdsdmmd.",
]
GIRL_LEFT_LOCKS = [          # x 20.., y 18..: wavy hair down her right side
    "dmd.",
    "dmmd",
    "dlmd",
    "dmmd",
    ".dmd",
    "dmmd",
    "dlmd",
    "dmd.",
    ".dd.",
]


def girl():
    g = load('leaf')
    src = [r[:] for r in g]
    for y in range(64):
        for x in range(64):
            v = src[y][x]
            if y <= 17 and 20 <= x <= 44:
                g[y][x] = 0                                  # the hat comes off
                continue
            ball = x <= 20 and 32 <= y <= 38
            if ball and v in (12, 13):
                g[y][x] = 9                                  # Poke Ball red
            elif v == 9:
                g[y][x] = 14
            # Leaf's long hair: auburn
            elif v in (4, 3, 8) and ((x >= 36 and 16 <= y <= 31) or (y == 18 and 29 <= x <= 31)):
                g[y][x] = {4: 12, 3: 11, 8: 4}[v]
    overlay(g, 18, 0, GIRL_HAIR_TOP, GK)
    overlay(g, 20, 18, GIRL_LEFT_LOCKS, GK)
    for y in range(18, 21):                                  # grey-green eyes, not Leaf's blue
        for x in range(24, 37):
            if src[y][x] in (6, 7):
                g[y][x] = 8
    return g
