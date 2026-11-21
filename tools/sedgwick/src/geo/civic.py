"""Civic buildings at their real points of interest, and the downtown storefront
row along Main Street. Runs before houses so they keep their frontage."""
import numpy as np
from geo.gen import RES, h32, R_STREET, R_MAIN

COM, DT = 2, 3          # commercial and downtown tileset indices (see gen.TILESETS)


def rect_ok(G, x, y, w, h):
    return G.free(x - 1, y - 1, w + 2, h + 2) and all((x + i, y + j) not in G.obj for i in range(w) for j in range(h))


def spot(G, cx, cy, w, h, r=14):
    """Nearest free w x h box to a point."""
    best = None
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            x, y = cx - w // 2 + dx, cy - h // 2 + dy
            if rect_ok(G, x, y, w, h):
                d = dx * dx + dy * dy
                if best is None or d < best[0]:
                    best = (d, x, y)
    return best and best[1:]


def place_rows(G, rows, x, y, ts, fmt, doors=()):
    for r, row in enumerate(rows):
        for c, m in enumerate(row):
            G.put(x + c, y + r, ts, fmt.format(m), m in doors)
    G.occupied[y - 1:y + len(rows) + 1, x - 1:x + len(rows[0]) + 1] = True


def cel(G, x, y, units, storeys, color, hs):
    import commercial
    ac = tuple(u for u in range(units) if (hs >> u) & 1)
    rows = commercial.plan(units, storeys, ac, doors=(units // 2,))
    place_rows(G, rows, x, y, COM, 'cel_{:03x}_' + color, {commercial.DOOR})


def church(G, x, y, width=8, roof='charcoal', wall='white'):
    import house2
    rows = house2.plan(width, 2, None, windows=width)
    door_col = width // 2 - 1
    lower = ['wall_l'] + ['wall_sid'] * (width - 2) + ['wall_r']
    lower[door_col] = 'wall_door'
    for i in list(range(1, door_col - 1, 2)) + list(range(door_col + 1, width - 2, 2)):
        lower[i], lower[i + 1] = 'wall_win_a', 'wall_win_b'
    rows[-1] = lower
    for r, row in enumerate(rows):
        for c, piece in enumerate(row):
            variant = roof if piece.startswith('roof') else wall
            G.put(x + c, y + 2 + r, RES, f'h_{piece}_{variant}', piece == 'wall_door')
    sx = x + width // 2 - 1
    for r in range(4):
        for c in range(2):
            G.put(sx + c, y + r, RES, f'church_steeple_{c}{r}_{roof}', False)
    G.occupied[y - 1:y + 2 + len(rows) + 1, x - 1:x + width + 1] = True


def pass_elevators(G):
    """Grain elevator beside each rail siding or spur (that's what Kansas sidings serve)."""
    n = 0
    for r in G.F['rail']:
        if r['service'] not in ('siding', 'spur') or r['state'] == 'abandoned':
            continue
        p = G.local(r['pts'])
        mx, my = p[len(p) // 2]
        if not (0 <= int(my) < G.H and 0 <= int(mx) < G.W) or G.metro[int(my), int(mx)] or G.zone[int(my), int(mx)] and G.land is not None and G.land[int(my), int(mx)] in (23, 24):
            continue
        s = spot(G, int(mx), int(my), 6, 7, 16)
        if s:
            for c in range(6):
                for rr in range(7):
                    G.put(s[0] + c, s[1] + rr, 1, f'elevator_{c}{rr}', False)
            G.occupied[s[1] - 1:s[1] + 8, s[0] - 1:s[0] + 7] = True
            n += 1
    G.stats['elevators'] = n


def pass_civic(G):
    n = 0
    for p in G.F['pois'] + [a for a in G.F['addresses']]:
        t = p['tags']
        x, y = int(p['x'] - G.ox), int(p['y'] - G.oy)
        if not (20 <= x < G.W - 20 and 20 <= y < G.H - 20):
            continue
        if G.metro[y, x]:
            continue
        hs = h32(t.get('name', ''), x, y)
        kind = t.get('amenity') or t.get('shop') or t.get('man_made') or t.get('office')
        if kind == 'water_tower':
            s = spot(G, x, y, 2, 4)
            if s:
                for r in range(4):
                    for c in range(2):
                        G.put(s[0] + c, s[1] + r, RES, f'water_tower_{c}{r}', False)
                G.occupied[s[1] - 1:s[1] + 5, s[0] - 1:s[0] + 3] = True
                n += 1
        elif kind == 'place_of_worship':
            s = spot(G, x, y, 8, 7)
            if s:
                church(G, s[0], s[1], 8, ('charcoal', 'brown', 'red')[hs % 3], 'white')
                n += 1
        elif kind in ('school', 'university', 'college'):
            if any(abs(x - qx) < 30 and abs(y - qy) < 30 for qx, qy in G.civic_done):
                continue
            s = spot(G, x, y, 16, 5, 20)
            if s:
                cel(G, s[0], s[1], 4, 2, 'beige', hs)
                G.civic_done.append((x, y))
                n += 1
        elif kind in ('library', 'post_office', 'police', 'fire_station', 'townhall', 'supermarket',
                      'social_facility', 'convenience', 'bank'):
            if kind == 'supermarket' and any(min(q[0] for q in b['poly']) <= p['x'] <= max(q[0] for q in b['poly']) and
                                             min(q[1] for q in b['poly']) <= p['y'] <= max(q[1] for q in b['poly'])
                                             for b in G.F['buildings']):
                continue                  # its own building becomes a big-box store (extras)
            units = 3 if kind in ('supermarket', 'social_facility') else 2
            s = spot(G, x, y, units * 4, 4 if units == 3 else 5)
            if s:
                cel(G, s[0], s[1], units, 1 if units == 3 else 2, 'brick' if hs & 1 else 'mint', hs)
                n += 1
    G.stats['civic'] = n


def pass_downtown(G):
    """Two-storey brick blocks shoulder to shoulder along Main Street, where the
    shops and civic buildings cluster."""
    pts = []
    for p in G.F['pois'] + G.F['addresses']:
        t = p['tags']
        if any(k in t for k in ('shop', 'amenity', 'office', 'craft')):
            x, y = int(p['x'] - G.ox), int(p['y'] - G.oy)
            if 0 <= x < G.W and 0 <= y < G.H and not G.metro[y, x]:
                row = G.road[y, max(0, x - 25):x + 25]
                if (row == R_MAIN).any():
                    pts.append(y)
    if len(pts) < 3:
        return
    pts.sort()
    # densest run of points with gaps under 40 tiles
    runs, cur = [], [pts[0]]
    for v in pts[1:]:
        if v - cur[-1] < 40:
            cur.append(v)
        else:
            runs.append(cur); cur = [v]
    runs.append(cur)
    run = max(runs, key=len)
    y0, y1 = run[0] - 20, run[-1] + 20
    n = 0
    for y in range(max(0, y0), min(G.H, y1)):
        xs = np.nonzero(G.road[y] == R_MAIN)[0]
        if not len(xs):
            continue
    # walk each side of Main: west side buildings end at the sidewalk, east side start after it
    main_x = {}
    for y in range(max(0, y0), min(G.H, y1)):
        xs = np.nonzero(G.road[y] == R_MAIN)[0]
        if len(xs) >= 3:
            main_x[y] = (xs.min(), xs.max())
    if not main_x:
        return
    y = min(main_x)
    while y < max(main_x):
        if y not in main_x:
            y += 1
            continue
        lo, hi = main_x[y]
        hs = h32('dt', y + G.oy)
        units = 2 + hs % 2
        w, h = units * 4, 5
        color = ('brick', 'beige', 'mint', 'brick')[(hs >> 2) % 4]
        placed = False
        for x in (lo - 1 - w, hi + 2):              # flush against Main's sidewalk
            far = x - 1 if x < lo else x + w
            if G.free(x, y, w, h) and G.free(far, y, 1, h) and all((x + i, y + j) not in G.obj for i in range(w) for j in range(h)):
                cel(G, x, y, units, 2, color, hs)
                n += 1
                placed = True
            hs = h32('dt2', y + G.oy, x)
            units = 2 + hs % 2
            w = units * 4
            color = ('brick', 'beige', 'mint', 'brick')[(hs >> 2) % 4]
        y += h + 1 if placed else 1
    # pave the frontage band on both sides between and around the storefronts
    ys = sorted(main_x)
    for y in range(ys[0], ys[-1] + 1):
        if y not in main_x:
            continue
        lo, hi = main_x[y]
        for x in list(range(lo - 14, lo - 1)) + list(range(hi + 2, hi + 15)):
            if 0 <= x < G.W and G.road[y, x] == 0 and (x, y) not in G.obj and not G.blocked[y, x]:
                G.put(x, y, COM, 'sidewalk', True)
                G.occupied[y, x] = True
    G.stats['storefronts'] = n


def _near_store(G, x, y):
    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        o = G.obj.get((x + dx, y + dy))
        if o and o[0] == COM and o[1].startswith('cel_'):
            return True
    return False
