"""Detail passes that fill the space between the data: driveways, parked cars,
backyards, yard trees, street furniture, farmsteads. All choices are seeded by
position hashes, so the result is stable and the same everywhere it's built."""
import numpy as np
from geo.gen import RES, RUR, h32, G_WATER, G_LAWN, G_FIELD, G_MEADOW, R_STREET, R_MAIN, R_GRAVEL, R_HWY

CARS = [f'sedan_{c}' for c in ('red', 'white', 'silver', 'black')] + ['pickup_white', 'pickup_green']


def ok(G, x, y, w=1, h=1):
    return G.free(x, y, w, h) and all((x + i, y + j) not in G.obj for i in range(w) for j in range(h))


def claim(G, x, y, w=1, h=1):
    G.occupied[y:y + h, x:x + w] = True


# ---------------------------------------------------------------- driveways
def driveway(G, hrec):
    x, y, w, rows, d, edge, garage_cols = (hrec[k] for k in ('x', 'y', 'w', 'rows', 'd', 'edge', 'gar'))
    bottom = y + rows - 1
    hs = hrec['hs']
    if d == 's':
        return            # drawn with the house (garage faces the street)
    if d == 'n':
        for side in ((x + w + 1,) if hs & 1 else ()) + (x - 3, x + w + 1):
            cells = [(side + i, yy) for yy in range(edge + 1, bottom + 1) for i in range(2)]
            if all(G.free(cx, cy) and (cx, cy) not in G.obj for cx, cy in cells):
                for yy in range(edge + 1, bottom + 1):
                    G.put(side, yy, RES, 'drive_l', True); G.put(side + 1, yy, RES, 'drive_r', True)
                G.put(side, edge, RES, 'drive_apron_s_l', True); G.put(side + 1, edge, RES, 'drive_apron_s_r', True)
                claim(G, side, edge + 1, 2, bottom - edge)
                return
    if d in 'ew':
        # side-entry garage: a 2-row drive from the street to the house's street-side wall,
        # level with the house's bottom two rows
        top = bottom - 1
        if d == 'e':
            xs = range(x + w, edge)
            apron = 'drive_apron_w'
        else:
            xs = range(edge + 1, x)
            apron = 'drive_apron_e'
        cells = [(cx, top + j) for cx in xs for j in range(2)]
        if cells and all((cx, cy) not in G.obj and not G.blocked[cy, cx] for cx, cy in cells):
            for cx in xs:
                G.put(cx, top, RES, 'drive_t', True); G.put(cx, top + 1, RES, 'drive_b', True)
            G.put(edge, top, RES, apron + '_t', True); G.put(edge, top + 1, RES, apron + '_b', True)
            claim(G, min(xs), top, len(xs), 2)
        return


def street_car(G, hrec):
    """Car parked at the north curb of an E-W street, in front of the house."""
    if hrec['d'] != 's' or hrec['hs'] % 6 != 0:
        return
    edge = hrec['edge']
    for cx in (hrec['x'] + 1, hrec['x'] + hrec['w'] - 3):
        lane = edge + 1
        if lane >= G.H or cx + 1 >= G.W:
            continue
        if all(G.road[lane, cx + i] == R_STREET and G.road[lane + 1, cx + i] in (R_STREET,) and
               G.road[edge, cx + i] == 0 and (cx + i, edge) not in G.obj and (cx + i, lane) not in G.obj
               for i in range(2)) and G.road[lane, cx - 1] and G.road[lane, cx + 2]:
            car = CARS[(hrec['hs'] >> 4) % len(CARS)]
            f = 'w' if (hrec['hs'] >> 9) & 1 else 'e'
            for c in range(2):
                G.put(cx + c, edge, RES, f'{car}_{f}_{c}0_curb', False)
                G.put(cx + c, lane, RES, f'{car}_{f}_{c}1', False)
            return


# ---------------------------------------------------------------- backyards
def backyard(G, hrec):
    x, y, w, d, hs = hrec['x'], hrec['y'], hrec['w'], hrec['d'], hrec['hs']
    if d != 's':
        return
    kind = ('chainlink', 'privacy', None, 'privacy', 'chainlink')[(hs >> 11) % 5]
    depth = 4 + (hs >> 13) % 4
    # shrink the yard until it fits
    while depth >= 3:
        top = y - depth - 1
        if top >= 0 and ok(G, x - 1, top, w + 2, depth + 1 - 1):
            break
        depth -= 1
    else:
        return
    top = y - depth - 1
    if kind:
        G.put(x - 1, top, RES, f'{kind}_corner_nw', False)
        G.put(x + w, top, RES, f'{kind}_corner_ne', False)
        for cx in range(x, x + w):
            G.put(cx, top, RES, f'{kind}_h', False)
        for cy in range(top + 1, y + 1):
            G.put(x - 1, cy, RES, f'{kind}_v', False)
            G.put(x + w, cy, RES, f'{kind}_v', False)
    claim(G, x - 1, top, w + 2, 1)                 # the fence line; the yard stays open for trees
    # inside the yard: a shed, or a tree
    roll = (hs >> 15) % 4
    if roll == 0 and depth >= 4 and w >= 5:
        sx = x + w - 3 if (hs >> 17) & 1 else x
        sy = top + 1
        roof = ('charcoal', 'brown', 'red')[(hs >> 18) % 3]
        for c, (a, b, cc) in enumerate((('l', 'l', 'l'), ('m', 'm', 'sid'), ('r', 'r', 'r'))):
            G.put(sx + c, sy, RES, f'h_roof0_{a}_{roof}', False)
            G.put(sx + c, sy + 1, RES, f'h_roof2_{b}_{roof}', False)
            G.put(sx + c, sy + 2, RES, f'h_wall_{cc}_white', False)
        claim(G, sx - 1, sy, 5, 4)
    elif roll in (1, 2) and depth >= 3:
        tx = x + (hs >> 19) % max(1, w - 2)
        tree(G, tx, top + 1, RES)
        claim(G, tx, top + 1, 2, 2)


def tree(G, x, y, ts):
    for (i, j), m in zip(((0, 0), (1, 0), (0, 1), (1, 1)), ('1d4', '1d5', '1e4', '1e5')):
        G.put(x + i, y + j, ts, 'prim:' + m, False)


def front_tree(G, hrec):
    """A shade tree in the front yard on the side away from the driveway."""
    x, y, w, rows, d, edge, hs = (hrec[k] for k in ('x', 'y', 'w', 'rows', 'd', 'edge', 'hs'))
    if d != 's' or (hs >> 21) % 3 == 0:
        return
    bottom = y + rows - 1
    tx = x - 3 if hrec.get('garage') == 'r' else x + w + 1
    ty = bottom - 1
    if ok(G, tx, ty, 2, 2) and ty + 2 < edge:
        tree(G, tx, ty, RES)
        claim(G, tx, ty, 2, 2)


# ---------------------------------------------------------------- after autotiling
def furniture(G, tsg, names):
    """Streetlights on block corners, power poles along country roads."""
    H, W = names.shape
    lamp_at = {'block_corner_sw': (-1, 1), 'block_corner_se': (1, 1), 'block_corner_nw': (-1, -1), 'block_corner_ne': (1, -1)}
    n_lamp = n_pole = 0
    for (y, x) in zip(*np.nonzero(np.isin(names, list(lamp_at)))):
        if h32(x, y, 'lamp') % 3:
            continue
        dx, dy = lamp_at[names[y, x]]
        # only real intersections: both streets continue straight past the corner
        if not (G.road[min(H - 1, max(0, y - 3 * dy)), x - dx] and G.road[y - dy, min(W - 1, max(0, x - 3 * dx))]):
            continue
        lx, ly = x + dx, y + dy
        if dy > 0:
            ly += 1           # lamp base sits on the lower tile
        if 1 <= ly < H and 0 <= lx < W and names[ly, lx] == 'lawn' and names[ly - 1, lx] == 'lawn' \
                and (lx, ly) not in G.obj and (lx, ly - 1) not in G.obj:
            names[ly - 1, lx], names[ly, lx] = 'streetlight_top', 'streetlight_bottom'
            tsg[ly - 1, lx] = tsg[ly, lx] = RES
            n_lamp += 1
    # power poles: every 24 tiles on the lawn strip beside gravel and highway roads
    edge_names = ('gravel_edge_n', 'hwy_edge_n')
    for (y, x) in zip(*np.nonzero(np.isin(names, edge_names))):
        if (x + G.ox) % 24 or y < 2:
            continue
        if names[y - 1, x] == 'lawn' and names[y - 2, x] in ('lawn',) or str(names[y - 2, x]).startswith(('wheat', 'corn', 'soy', 'plowed', 'stubble')):
            if names[y - 1, x] == 'lawn':
                names[y - 2, x], names[y - 1, x] = 'power_pole_top', 'power_pole_bottom'
                tsg[y - 2, x] = tsg[y - 1, x] = RUR
                n_pole += 1
    for (y, x) in zip(*np.nonzero(np.isin(names, ('gravel_edge_w', 'hwy_edge_w')))):
        if (y + G.oy) % 24 or y < 1 or x < 1:
            continue
        if names[y, x - 1] == 'lawn' and names[y - 1, x - 1] == 'lawn':
            names[y - 1, x - 1], names[y, x - 1] = 'power_pole_top', 'power_pole_bottom'
            tsg[y - 1, x - 1] = tsg[y, x - 1] = RUR
            n_pole += 1
    G.stats['lamps'] = n_lamp
    G.stats['poles'] = n_pole


# ---------------------------------------------------------------- farmsteads
def farmsteads(G):
    """Country addresses become farmyards: farmhouse, barn, metal shed or silo,
    a windbreak of trees on the north side and a gravel yard."""
    import farm2, house2
    n = 0
    for a in G.F['addresses']:
        x, y = int(a['x'] - G.ox), int(a['y'] - G.oy)
        if not (8 <= x < G.W - 30 and 12 <= y < G.H - 12) or G.zone[y, x]:
            continue
        if any(k in a['tags'] for k in ('amenity', 'shop', 'office')):
            continue
        hs = h32(a['num'], a['street'], 'farm')
        # yard box: 26 x 14, centred on the address
        X0, Y0, w, h = x - 10, y - 7, 26, 14
        if not ok(G, X0, Y0, w, h):
            continue
        # mowed farmyard under everything
        for yy in range(Y0, Y0 + h):
            for xx in range(X0, X0 + w):
                G.put(xx, yy, RUR, 'lawn', True)
        # windbreak along the north edge
        for tx in range(X0, X0 + w - 1, 2):
            tree(G, tx, Y0, RUR)
        # farmhouse
        rows = house2.plan(6, 2 if hs & 1 else 1, None, windows=1)
        hy = Y0 + 3
        for r, row in enumerate(rows):
            for c, piece in enumerate(row):
                variant = 'green' if piece.startswith('roof') else 'white'
                G.put(X0 + 1 + c, hy + r, RUR, f'h_{piece}_{variant}', piece == 'wall_door')
        G.put(X0 + 1, hy + len(rows), RUR, 'mailbox', False)
        G.signs.append((X0 + 1, hy + len(rows), f"{a['num']} {a['street']}"))
        # barn and shed/silo
        bx = X0 + 9
        rowsb = farm2.plan(6, 1, None, True)
        for r, row in enumerate(rowsb):
            for c, piece in enumerate(row):
                G.put(bx + c, Y0 + 3 + r, RUR, f'barn_{piece}', False)
        if hs >> 3 & 1:
            for c in range(2):
                for r in range(5):
                    G.put(bx + 7 + c, Y0 + 2 + r, RUR, f'silo_{c}{r}', False)
        else:
            rowss = farm2.plan(5, 1, 1, False)
            for r, row in enumerate(rowss):
                for c, piece in enumerate(row):
                    G.put(bx + 7 + c, Y0 + 3 + r, RUR, f'shed_{piece}', False)
        # gravel yard in front of the buildings, hay bales
        for yy in range(Y0 + 9, Y0 + 12):
            for xx in range(X0 + 8, X0 + w - 1):
                G.put(xx, yy, RUR, 'gravel', True)
        if hs >> 5 & 1:
            G.put(X0 + 4, Y0 + 11, RUR, 'hay_bales', False)
            G.put(X0 + 6, Y0 + 11, RUR, 'hay_bales', False)
        claim(G, X0, Y0, w, h)
        n += 1
    G.stats['farmsteads'] = n
