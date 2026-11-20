"""Church: a Pallet-style house body with a steeple rising through the roof.
The steeple is drawn entirely in the house ROOF palette (stone greys + roof colour
for the spire), so where it overlaps the roof both share one palette and any of the
roof colour variants applies to it."""
import house2

O, G1, G2, G3 = 4, 1, 2, 3            # outline, light / mid / dark stone
S_L, S_M, S_D, S_K = 6, 7, 8, 9       # spire: lit, mid, shaded, darkest


def steeple():
    """32 x 64 px: spire (rows 0-27) on a square belfry tower (rows 28-63)."""
    W, H = 32, 64
    g = [[0] * W for _ in range(H)]
    for y in range(1, 28):
        half = 1 + (y * 9) / 27
        x0, x1 = round(16 - half), round(15 + half)
        for x in range(x0, x1 + 1):
            g[y][x] = S_L if x < 15 else (S_M if x < 17 else S_D)
        g[y][x0] = O
        g[y][x1] = O
    g[0][15] = g[0][16] = O
    for x in range(5, 27):
        g[27][x] = O
        g[26][x] = S_K if g[26][x] else g[26][x]
    # tower
    for y in range(28, 64):
        for x in range(7, 25):
            g[y][x] = G1 if x < 10 else (G2 if x < 21 else G3)
        g[y][6] = O
        g[y][25] = O
    for x in range(6, 26):
        g[28][x] = O
        g[29][x] = G3
    # louvred belfry opening
    for y in range(33, 45):
        for x in range(11, 21):
            g[y][x] = O if (y - 33) % 3 == 0 or x in (11, 20) else G3
    for x in range(11, 21):
        g[32][x] = O
    # round window
    for y in range(49, 57):
        for x in range(12, 20):
            d = (x + .5 - 16) ** 2 + (y + .5 - 53) ** 2
            if d <= 14:
                g[y][x] = G1 if d < 8 else O
    return g


def pieces(roof_top_rows=('roof0_m', 'roof1_m')):
    """Steeple metatiles: rows 0-1 stand on lawn above the house, rows 2-3 are
    drawn over the house's first two roof rows. Returns {'steeple_<c><r>': [4 quads]}
    where each quad is an 8x8 roof-palette grid (None = empty)."""
    st = steeple()
    house = house2.pieces()
    out = {}
    for r in range(4):
        for c in range(2):
            quads = []
            under = None
            if r >= 2:
                under = house[roof_top_rows[r - 2]]['top']
            for qi, (oy, ox) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
                g = [[0] * 8 for _ in range(8)]
                base = under[qi] if under is not None else None
                for y in range(8):
                    for x in range(8):
                        v = st[r * 16 + oy + y][c * 16 + ox + x]
                        if not v and base is not None:
                            v = base[y][x]
                        g[y][x] = v
                quads.append(g if any(v for row in g for v in row) else None)
            out[f'steeple_{c}{r}'] = quads
    return out
