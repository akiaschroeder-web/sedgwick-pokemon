"""Detail layer: the custom pieces that sit on top of the base map.

place(G)                  before houses: parks, playgrounds, ball diamonds, pavilions, cemeteries,
                          the confluence plaza and Keeper, Botanica's conservatory, the zoo arch,
                          bus shelters, fast food on its own lot
building(G, b, box)       pass_buildings hook: hangars, aircraft plants, big-box stores, fast food
finish(G, tsg, names, walk)  after the autotile: bridges, footbridges, docks, the floodway channel,
                          river banks in town, the interstate and its overpasses, runways and
                          taxiways, golf course surfaces, traffic signals, crosswalks, stop
                          signs, street signs, hydrants, railroad crossing signals, lot arrows,
                          the air base gate.
Everything comes from OSM where OSM maps it."""
import math
import numpy as np
from geo.gen import RES, RUR, h32, G_WATER, G_LAWN, G_PARK, G_CEMETERY, G_MEADOW, G_PRAIRIE, R_HWY, R_STREET, R_MAIN

COM, LM, AV, CITY, RETAIL, CONF = 2, 5, 6, 7, 8, 9
KEEPER = (-97.34968, 37.69138)        # Keeper of the Plains (OSM node 984831116 has no feature tags)
BOTANICA = 'The Wichita Botanica Gardens'
BIGBOX_SHOPS = ('supermarket', 'department_store', 'doityourself', 'wholesale', 'hardware')
PLANT_NAMES = ('spirit', 'textron', 'cessna', 'beech', 'bombardier', 'learjet', 'boeing', 'airbus', 'aircraft')
LAWNISH = (G_LAWN, G_PARK, G_MEADOW, G_PRAIRIE, G_CEMETERY)


# ------------------------------------------------------------------ helpers
def _loc(G, x, y):
    return int(round(x - G.ox)), int(round(y - G.oy))


def _cent(G, pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return _loc(G, sum(xs) / len(xs), sum(ys) / len(ys))


def _inb(G, x, y, w=1, h=1):
    return x >= 1 and y >= 1 and x + w < G.W - 1 and y + h < G.H - 1


def _clear(G, x, y, w, h, margin=1):
    """Free lawn-type ground, nothing placed, no road."""
    if not _inb(G, x - margin, y - margin, w + 2 * margin, h + 2 * margin):
        return False
    ys, xs = slice(y - margin, y + h + margin), slice(x - margin, x + w + margin)
    if G.occupied[ys, xs].any() or G.blocked[ys, xs].any():
        return False
    if not np.isin(G.ground[y:y + h, x:x + w], LAWNISH).all():
        return False
    return not any((x + i, y + j) in G.obj for i in range(-margin, w + margin) for j in range(-margin, h + margin))


def _spot(G, cx, cy, w, h, r=10, margin=1):
    best = None
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = dx * dx + dy * dy
            if best is not None and d >= best[0]:
                continue
            x, y = cx - w // 2 + dx, cy - h // 2 + dy
            if _clear(G, x, y, w, h, margin):
                best = (d, x, y)
    return best and best[1:]


def _grid(G, x, y, w, h, ts, prefix, walk_rows=()):
    for r in range(h):
        for c in range(w):
            G.put(x + c, y + r, ts, f'{prefix}_{c}{r}', r in walk_rows)
    G.occupied[y:y + h, x:x + w] = True


def _one(G, x, y, ts, name, walk=False):
    G.put(x, y, ts, name, walk)
    G.occupied[y, x] = True


def _tall(G, x, y, ts, base):
    """base_top at y-1, base_bottom at y."""
    G.put(x, y - 1, ts, base + '_top', False)
    G.put(x, y, ts, base + '_bottom', False)
    G.occupied[y - 1:y + 1, x] = True


# ------------------------------------------------------------------ before houses
def place(G):
    st = {k: 0 for k in ('playgrounds', 'diamonds', 'pavilions', 'park_props', 'headstones', 'shelters', 'fastfood_lots')}
    _landmarks(G, st)
    feats = G.F.get('feat', [])
    # playgrounds and ball diamonds at their OSM spots
    pg = [f['pts'] for f in feats if f['tags'].get('leisure') == 'playground'] + \
         [[(n['x'], n['y'])] for n in G.F.get('nfeat', []) if n['tags'].get('leisure') == 'playground']
    for pts in pg:
        cx, cy = _cent(G, pts)
        s = _spot(G, cx, cy, 4, 1, r=6)
        if s:
            x, y = s
            _one(G, x, y, CITY, 'playground_slide'); _one(G, x + 2, y, CITY, 'swings'); _one(G, x + 3, y, CITY, 'swings')
            st['playgrounds'] += 1
    for f in feats:
        t = f['tags']
        if t.get('leisure') == 'pitch' and t.get('sport') in ('baseball', 'softball') and f['closed']:
            cx, cy = _cent(G, f['pts'])
            s = _spot(G, cx, cy, 4, 4, r=4, margin=0)
            if s:
                _grid(G, *s, 4, 4, CITY, 'diamond', walk_rows=(0, 1, 2, 3))
                st['diamonds'] += 1
    # parks: a pavilion with a picnic table and bin in each sizeable park
    for a in G.F['areas']:
        if a['tags'].get('leisure') != 'park':
            continue
        xs = [p[0] for p in a['poly']]; ys = [p[1] for p in a['poly']]
        if (max(xs) - min(xs)) * (max(ys) - min(ys)) < 900:
            continue
        cx, cy = _cent(G, a['poly'])
        s = _spot(G, cx, cy, 6, 4, r=14)
        if s:
            x, y = s
            _grid(G, x + 1, y, 4, 3, CITY, 'pavilion', walk_rows=(0, 1))
            _one(G, x, y + 3, CITY, 'picnic_table'); _one(G, x + 5, y + 3, CITY, 'trash_can')
            st['pavilions'] += 1
    # mapped benches, picnic tables and bins
    kinds = {'bench': 'bench', 'picnic_table': 'picnic_table', 'waste_basket': 'trash_can'}
    for n in G.F.get('nfeat', []):
        t = n['tags']
        k = kinds.get(t.get('amenity')) or kinds.get(t.get('leisure'))
        if not k:
            continue
        x, y = _loc(G, n['x'], n['y'])
        s = _spot(G, x, y, 1, 1, r=3, margin=0)
        if s:
            _one(G, *s, CITY, k)
            st['park_props'] += 1
    # synthetic benches along park paths
    for p in G.F.get('paths', []):
        if p['bridge']:
            continue
        for (ax, ay), (bx, by) in zip(p['pts'], p['pts'][1:]):
            L = math.hypot(bx - ax, by - ay)
            for k in range(int(L // 30)):
                px, py = _loc(G, ax + (bx - ax) * (k + 0.5) * 30 / L, ay + (by - ay) * (k + 0.5) * 30 / L)
                if not _inb(G, px, py, 2, 2) or G.ground[py, px] != G_PARK or h32(px + G.ox, py + G.oy, 'bench') % 2:
                    continue
                for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                    if _clear(G, px + dx, py + dy, 1, 1, 0):
                        _one(G, px + dx, py + dy, CITY, 'bench' if h32(px, py) % 3 else 'trash_can')
                        st['park_props'] += 1
                        break
    _cemeteries(G, st)
    # bus shelters
    for n in G.F.get('nfeat', []):
        t = n['tags']
        if t.get('highway') == 'bus_stop' or (t.get('amenity') == 'shelter' and t.get('shelter_type') == 'public_transport'):
            x, y = _loc(G, n['x'], n['y'])
            s = _spot(G, x, y, 2, 2, r=5, margin=0)
            if s:
                _grid(G, *s, 2, 2, RES, 'bus_shelter', walk_rows=())
                st['shelters'] += 1
    # fast food mapped only as a point: its own little lot
    for n in G.F.get('nfeat', []):
        if n['tags'].get('amenity') != 'fast_food':
            continue
        x, y = _loc(G, n['x'], n['y'])
        if not _inb(G, x, y) or G.metro[y, x] or not G.zone[y, x]:
            continue
        if any(b_inside(b, n['x'], n['y']) for b in G.F['buildings']):
            continue                     # its building gets the restaurant in pass_buildings
        s = _spot(G, x, y, 5, 3, r=8)
        if s:
            _fastfood(G, *s)
            st['fastfood_lots'] += 1
    G.stats.update(st)


def _shop_sites(G):
    if not hasattr(G, '_shops'):
        out = []
        for f in G.F.get('feat', []):
            if f['tags'].get('shop') in BIGBOX_SHOPS:
                xs = [p[0] for p in f['pts']]; ys = [p[1] for p in f['pts']]
                out.append((min(xs), min(ys), max(xs), max(ys), f['tags']['shop']))
        for n in G.F.get('nfeat', []):
            if n['tags'].get('shop') in BIGBOX_SHOPS:
                out.append((n['x'] - 3, n['y'] - 3, n['x'] + 3, n['y'] + 3, n['tags']['shop']))
        G._shops = out
    return G._shops


def b_inside(b, x, y):
    xs = [p[0] for p in b['poly']]; ys = [p[1] for p in b['poly']]
    return min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys)


def _fastfood(G, x, y):
    """4x3 restaurant at (x, y) with its sign on the lawn to the east."""
    _grid(G, x, y, 4, 3, RETAIL, 'ff')
    G.obj[(x + 2, y + 2)] = (RETAIL, 'ff_22', True)       # glass doors
    if (x + 4, y + 1) not in G.obj and (x + 4, y + 2) not in G.obj and x + 4 < G.W:
        G.put(x + 4, y + 1, RETAIL, 'ff_sign_00', False); G.put(x + 4, y + 2, RETAIL, 'ff_sign_01', False)
        G.occupied[y + 1:y + 3, x + 4] = True


def _landmarks(G, st):
    import json, os
    feats = G.F.get('feat', [])
    # the Keeper of the Plains on its plaza at the confluence
    from geo import extract
    for kx, ky in [extract.proj(*KEEPER)]:
        cx, cy = _loc(G, kx, ky)
        x0, y0 = cx - 3, cy - 3
        if not _inb(G, x0, y0, 6, 6):
            continue
        for r in range(6):
            for c in range(6):
                G.obj.pop((x0 + c, y0 + r), None)
                G.put(x0 + c, y0 + r, CONF, f'plaza_{c}{r}', True)
                G.ground[y0 + r, x0 + c] = G_PARK
        lay = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'custom', 'landmark_layout.json')
        if os.path.exists(lay):
            L = json.load(open(lay))
            ox, oy = L['origin']
            for name in L['pieces']:
                if name in G.ids[CONF]:
                    _, c, r = name.split('_')
                    G.put(x0 + ox + int(c), y0 + oy + int(r), CONF, name, (oy + int(r)) < 2)
        G.occupied[y0 - 6:y0 + 7, x0 - 1:x0 + 7] = True
        st['keeper'] = 1
    for f in feats:
        t = f['tags']
        if t.get('name') == BOTANICA:
            cx, cy = _cent(G, f['pts'])
            s = _spot(G, cx, cy, 5, 3, r=20)
            if s:
                _grid(G, *s, 5, 3, CITY, 'conservatory')
                G.obj[(s[0] + 2, s[1] + 2)] = (CITY, 'conservatory_22', True)
                st['botanica'] = 1
        if t.get('tourism') == 'zoo' and f['closed']:
            # entrance arch where the grounds come closest to a street
            best = None
            for px, py in f['pts']:
                x, y = _loc(G, px, py)
                if not _inb(G, x, y, 1, 1):
                    continue
                dirs = G.street_dirs(x, y, 25)
                if dirs:
                    d = min(v[0] for v in dirs.values())
                    if best is None or d < best[0]:
                        best = (d, x, y)
            if not best:
                continue
            s = _spot(G, best[1], best[2], 3, 2, r=8, margin=0)
            if s:
                _grid(G, *s, 3, 2, CITY, 'zoo_gate', walk_rows=(1,))
                st['zoo_gate'] = 1


def _cemeteries(G, st):
    for a in G.F['areas']:
        if a['cls'] != 'cemetery':
            continue
        m = G.poly_mask([G.local(a['poly'])])
        if m.sum() < 30:
            continue
        inner = m.copy()
        inner[1:] &= m[:-1]; inner[:-1] &= m[1:]; inner[:, 1:] &= m[:, :-1]; inner[:, :-1] &= m[:, 1:]
        edge = m & ~inner
        free = ~(G.road_ring() | G.occupied | G.blocked)
        for y, x in zip(*np.nonzero(edge & free)):
            if (x, y) not in G.obj:
                _one(G, x, y, CITY, 'iron_fence')
        deep = inner.copy()
        deep[1:] &= inner[:-1]; deep[:-1] &= inner[1:]; deep[:, 1:] &= inner[:, :-1]; deep[:, :-1] &= inner[:, 1:]
        for y, x in zip(*np.nonzero(deep & free)):
            gx, gy = x + G.ox, y + G.oy
            if gx % 2 == 0 and gy % 3 == 0 and (x, y) not in G.obj:
                _one(G, x, y, CITY, 'cross_stone' if h32(gx, gy, 'grave') % 5 == 0 else 'headstone')
                st['headstones'] += 1


# ------------------------------------------------------------------ special buildings (before houses)
def special_buildings(G):
    G.used_buildings = getattr(G, 'used_buildings', set())
    for b in G.F['buildings']:
        if b['id'] in G.used_buildings:
            continue
        xs = [p[0] - G.ox for p in b['poly']]; ys = [p[1] - G.oy for p in b['poly']]
        x0, y0, x1, y1 = int(min(xs)), int(min(ys)), int(math.ceil(max(xs))), int(math.ceil(max(ys)))
        w, h = x1 - x0, y1 - y0
        if w < 3 or h < 2 or not _inb(G, x0, y0, w, h) or G.metro[min((y0 + y1) // 2, G.H - 1), min((x0 + x1) // 2, G.W - 1)]:
            continue
        if building(G, b, x0, y0, w, h):
            G.used_buildings.add(b['id'])


def building(G, b, x0, y0, w, h):
    """Returns True when the footprint became one of the special buildings."""
    t = dict(b['tags'])
    if not _inb(G, x0, y0, w, h) or G.occupied[y0:y0 + h, x0:x0 + w].any() or \
            ((G.road[y0:y0 + h, x0:x0 + w] > 0) & ~G.parking[y0:y0 + h, x0:x0 + w]).any() or \
            (G.ground[y0:y0 + h, x0:x0 + w] == G_WATER).any():
        return False
    if 'shop' not in t:
        # a store mapped as a point or a site polygon around the building
        for f in _shop_sites(G):
            if f[0] <= (x0 + w / 2 + G.ox) <= f[2] and f[1] <= (y0 + h / 2 + G.oy) <= f[3]:
                t['shop'] = f[4]
                break
    name = (t.get('name', '') + ' ' + t.get('operator', '')).lower()
    if t.get('building') == 'hangar' or t.get('aeroway') == 'hangar' or \
            (t.get('building') in ('industrial', 'manufacture', 'factory', 'yes') and w >= 14 and any(k in name for k in PLANT_NAMES)):
        import aviation
        prefix = 'plant' if (w >= 16 or 'hangar' not in (t.get('building'), t.get('aeroway'))) else 'hgr'
        width = max(5, min(w, 28))
        rr = max(1, min(4, h - 4))
        rows = aviation.hangar_plan(width, door_width=min(4, width - 2), roof_rows=rr)
        y = y0 + h - len(rows)
        if y < 1:
            return False
        for r, row in enumerate(rows):
            for c, piece in enumerate(row):
                G.put(x0 + c, y + r, AV, f'{prefix}_{piece}', piece in aviation.WALK_IN)
        G.occupied[y - 1:y0 + h + 1, x0 - 1:x0 + width + 1] = True
        G.stats['hangars'] = G.stats.get('hangars', 0) + 1
        return True
    if t.get('shop') in BIGBOX_SHOPS and w >= 8 and h >= 5:
        import retail
        width = min(w, 26)
        rows = retail.bigbox_plan(width)
        y = y0 + h - len(rows)
        for r, row in enumerate(rows):
            for c, m in enumerate(row):
                G.put(x0 + c, y + r, RETAIL, f'bb_{m:03x}', m == retail.DOOR)
        G.occupied[y - 1:y0 + h + 1, x0 - 1:x0 + width + 1] = True
        G.stats['bigbox'] = G.stats.get('bigbox', 0) + 1
        return True
    ff = t.get('amenity') == 'fast_food' or any(
        n['tags'].get('amenity') == 'fast_food' and b_inside(b, n['x'], n['y']) for n in G.F.get('nfeat', ()))
    if ff and w <= 16 and h <= 12:
        x = x0 + max(0, (w - 4) // 2)
        y = y0 + max(0, h - 3)
        _fastfood(G, x, y)
        G.stats['fastfood'] = G.stats.get('fastfood', 0) + 1
        return True
    return False


# ------------------------------------------------------------------ after the autotile
def finish(G, tsg, names, walk):
    H, W = names.shape
    core = G.road
    placed = np.zeros((H, W), bool)
    for (x, y) in G.obj:
        placed[y, x] = True
    st = {}

    def setn(y, x, ts, nm, wk=True):
        names[y, x] = nm; tsg[y, x] = ts; walk[y, x] = wk

    water = G.ground == G_WATER
    ring = G.road_ring() & (core == 0)
    # ---- road bridges: railings where the curb row crosses water
    nb = 0
    pc = np.pad(core > 0, 1)
    for y, x in zip(*np.nonzero(ring & water & ~placed)):
        n, s, w_, e = pc[y, x + 1], pc[y + 2, x + 1], pc[y + 1, x], pc[y + 1, x + 2]
        if e and not w_:
            setn(y, x, CITY, 'bridge_ns_w', False)
        elif w_ and not e:
            setn(y, x, CITY, 'bridge_ns_e', False)
        elif s and not n:
            setn(y, x, CITY, 'bridge_ew_n_lamp' if (x + G.ox) % 12 == 0 else 'bridge_ew_n', False)
        elif n and not s:
            setn(y, x, CITY, 'bridge_ew_s', False)
        else:
            continue
        nb += 1
    st['bridge_tiles'] = nb
    # ---- footbridges and piers over water
    nf = 0
    for p in G.F.get('paths', []):
        if not p['bridge']:
            continue
        for x, y, vert in _cells(G, p['pts']):
            if water[y, x] and not core[y, x] and not placed[y, x]:
                setn(y, x, CITY, 'footbridge_ns' if vert else 'footbridge_ew', True)
                nf += 1
    for f in G.F.get('feat', []):
        if f['tags'].get('man_made') != 'pier' or f['closed']:
            continue
        cells = [(x, y, v) for x, y, v in _cells(G, f['pts']) if water[y, x] and not placed[y, x]]
        for k, (x, y, vert) in enumerate(cells):
            setn(y, x, CITY, ('dock_end' if k == len(cells) - 1 else 'dock_ns') if vert else 'footbridge_ew', True)
            nf += 1
    st['footbridge_tiles'] = nf
    # ---- the floodway: concrete channel walls; town rivers: sandy banks
    shore = {0x1be: 'n', 0x1ae: 's', 0x1b7: 'w', 0x1b5: 'e', 0x1a4: 'nw', 0x1a3: 'ne', 0x19c: 'sw', 0x19b: 'se',
             0x1bf: 'inw', 0x1bd: 'ine', 0x1af: 'isw', 0x1ad: 'ise'}
    canal = G.poly_mask([G.local(a['poly']) for a in G.F['areas'] if a['cls'] == 'water' and
                         (a['tags'].get('water') == 'canal' or 'floodway' in a['tags'].get('name', '').lower())])
    river = G.poly_mask([G.local(a['poly']) for a in G.F['areas'] if a['cls'] == 'water' and
                         (a['tags'].get('water') == 'river' or a['tags'].get('waterway') == 'riverbank')])
    BANK = {'n': 'bank_n', 's': 'bank_s', 'w': 'bank_w', 'e': 'bank_e', 'nw': 'bank_in_nw', 'ne': 'bank_in_ne',
            'sw': 'bank_in_sw', 'se': 'bank_in_se', 'inw': 'bank_out_nw', 'ine': 'bank_out_ne', 'isw': 'bank_out_sw',
            'ise': 'bank_out_se'}
    CANAL = {'n': 'canal_n', 's': 'canal_s', 'w': 'canal_w', 'e': 'canal_e',
             'nw': 'canal_n', 'ne': 'canal_n', 'sw': 'canal_s', 'se': 'canal_s'}
    nbank = 0
    for y, x in zip(*np.nonzero(water & ~placed & (canal | (river & G.zone)))):
        nm = names[y, x]
        if not (isinstance(nm, str) and nm.startswith('prim:')):
            continue
        k = shore.get(int(nm[5:], 16))
        if not k:
            continue
        if canal[y, x]:
            if k in CANAL:
                setn(y, x, CITY, CANAL[k], False); nbank += 1
        else:
            setn(y, x, CITY, BANK[k], False); nbank += 1
    st['bank_tiles'] = nbank
    # ---- interstate
    st.update(_interstate(G, tsg, names, walk, placed))
    # ---- runways and taxiways
    st.update(_airfield(G, tsg, names, walk, placed))
    # ---- golf
    st['golf_tiles'] = _golf(G, tsg, names, walk, placed)
    # ---- street details
    st.update(_street_details(G, tsg, names, walk, placed))
    G.stats.update(st)


def _cells(G, pts):
    """Tiles along a polyline with the local direction (vertical?)."""
    seen = set()
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        ax, ay, bx, by = ax - G.ox, ay - G.oy, bx - G.ox, by - G.oy
        vert = abs(by - ay) > abs(bx - ax)
        n = max(1, int(math.hypot(bx - ax, by - ay) * 2))
        for i in range(n + 1):
            x, y = int(round(ax + (bx - ax) * i / n)), int(round(ay + (by - ay) * i / n))
            if (x, y) not in seen and 0 <= x < G.W and 0 <= y < G.H:
                seen.add((x, y))
                yield x, y, vert


# ---------------------------------------------------------------- interstate
def _interstate(G, tsg, names, walk, placed):
    H, W = names.shape
    motor = getattr(G, 'motor', None)
    if motor is None or not motor.any():
        return {}
    ovp = G.ovp
    m = motor & ~placed
    role = {}
    # horizontal carriageways: vertical runs of 4-5 motorway cells in a column
    for x in range(W):
        col = m[:, x]
        if not col.any():
            continue
        y = 0
        while y < H:
            if not col[y]:
                y += 1
                continue
            y1 = y
            while y1 < H and col[y1]:
                y1 += 1
            L = y1 - y
            if 4 <= L <= 5 and _straight(m, x, y, y1, horizontal=True):
                up = _other(motor, x, y - 1, -1, True)
                dn = _other(motor, x, y1, 1, True)
                if dn is not None and (up is None or dn <= up):
                    rows = ['shoulder_n', 'lane_dash', 'lane'] + ['lane'] * (L - 4) + ['median_n']
                elif up is not None:
                    rows = ['median_s', 'lane_dash', 'lane'] + ['lane'] * (L - 4) + ['shoulder_s']
                else:
                    rows = ['shoulder_n', 'lane_dash', 'lane'] + ['lane'] * (L - 4) + ['shoulder_s']
                for k in range(L):
                    role[(y + k, x)] = (rows[k], 'h')
            y = y1
    for y in range(H):
        row = m[y]
        if not row.any():
            continue
        x = 0
        while x < W:
            if not row[x]:
                x += 1
                continue
            x1 = x
            while x1 < W and row[x1]:
                x1 += 1
            L = x1 - x
            if 4 <= L <= 5 and _straight(m, y, x, x1, horizontal=False) and not any((y, x + k) in role for k in range(L)):
                lf = _other(motor, y, x - 1, -1, False)
                rt = _other(motor, y, x1, 1, False)
                if rt is not None and (lf is None or rt <= lf):
                    cols = ['shoulder_n', 'lane_dash', 'lane'] + ['lane'] * (L - 4) + ['median_n']
                elif lf is not None:
                    cols = ['median_s', 'lane_dash', 'lane'] + ['lane'] * (L - 4) + ['shoulder_s']
                else:
                    cols = ['shoulder_n', 'lane_dash', 'lane'] + ['lane'] * (L - 4) + ['shoulder_s']
                for k in range(L):
                    role[(y, x + k)] = (cols[k], 'v')
            x = x1
    n = 0
    for (y, x), (r, o) in role.items():
        nm = f'i_{r}' + ('_v' if o == 'v' else '')
        if o == 'h' and x + 1 < W and ovp[y, x + 1]:
            nm = f'ovp_w_{r}'
        elif o == 'h' and x > 0 and ovp[y, x - 1]:
            nm = f'ovp_e_{r}'
        names[y, x], tsg[y, x], walk[y, x] = nm, CITY, True
        n += 1
    # the gravel shoulders beside a drawn interstate become grass (the shoulder piece has its own verge)
    done = np.zeros((H, W), bool)
    for (y, x) in role:
        done[y, x] = True
    near = np.zeros_like(done)
    near[1:] |= done[:-1]; near[:-1] |= done[1:]; near[:, 1:] |= done[:, :-1]; near[:, :-1] |= done[:, 1:]
    for y, x in zip(*np.nonzero(near & ~done & ~placed)):
        if str(names[y, x]).startswith('hwy_') and G.road[y, x] == 0:
            names[y, x] = 'lawn'
    return {'interstate_tiles': n}


def _straight(m, a, b0, b1, horizontal):
    """The run's neighbours a few cells along the road share its extent (not a curve/junction)."""
    for d in (-2, 2):
        if horizontal:
            x = a + d
            if x < 0 or x >= m.shape[1] or not m[b0:b1, x].all():
                return False
            if (b0 > 0 and m[b0 - 1, x]) or (b1 < m.shape[0] and m[b1, x]):
                return False
        else:
            y = a + d
            if y < 0 or y >= m.shape[0] or not m[y, b0:b1].all():
                return False
            if (b0 > 0 and m[y, b0 - 1]) or (b1 < m.shape[1] and m[y, b1]):
                return False
    return True


def _other(motor, a, b, step, horizontal, reach=40):
    """Distance to the next motorway cell beyond the run (the other carriageway)."""
    for k in range(reach):
        if horizontal:
            y, x = b + k * step, a
        else:
            y, x = a, b + k * step
        if not (0 <= y < motor.shape[0] and 0 <= x < motor.shape[1]):
            return None
        if motor[y, x]:
            return k
    return None


# ---------------------------------------------------------------- airfields
def _airfield(G, tsg, names, walk, placed):
    H, W = names.shape
    core = G.road
    nr = nt = 0
    for f in G.F.get('feat', []):
        t = f['tags']
        a = t.get('aeroway')
        if a not in ('runway', 'taxiway', 'taxilane') or f['closed'] and a != 'runway':
            continue
        pts = [(p[0] - G.ox, p[1] - G.oy) for p in f['pts']]
        if a == 'runway':
            try:
                wm = float(str(t.get('width', '30')).split()[0])
            except ValueError:
                wm = 30
            half = max(2, min(6, int(wm / 2.5 * 0.6 / 2)))
            (ax, ay), (bx, by) = pts[0], pts[-1]
            if f['closed']:          # mapped as an area: use its long axis
                xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                if max(xs) - min(xs) > max(ys) - min(ys):
                    ax, bx, ay = min(xs), max(xs), (min(ys) + max(ys)) / 2; by = ay
                else:
                    ay, by, ax = min(ys), max(ys), (min(xs) + max(xs)) / 2; bx = ax
            dx, dy = bx - ax, by - ay
            L = math.hypot(dx, dy)
            if L < 20:
                continue
            horiz, vert = abs(dy) < 0.42 * abs(dx), abs(dx) < 0.42 * abs(dy)     # within ~23 deg of the grid
            for i in range(int(L * 2) + 1):
                px, py = ax + dx * i / (2 * L), ay + dy * i / (2 * L)
                along = i / 2
                for k in range(-half, half + 1):
                    if horiz:
                        x, y = int(round(px)), int(round(py)) + k
                    elif vert:
                        x, y = int(round(px)) + k, int(round(py))
                    else:
                        x, y = int(round(px - dy / L * k)), int(round(py + dx / L * k))
                    if not (0 <= x < W and 0 <= y < H) or placed[y, x] or core[y, x]:
                        continue
                    end = along < 4 or along > L - 4
                    if horiz:
                        nm = 'rwy_edge_n' if k == -half else 'rwy_edge_s' if k == half else (
                            'rwy_threshold' if end else 'rwy_center' if k == 0 and int(along) % 4 < 2 else 'rwy_plain')
                    elif vert:
                        nm = 'rwy_end_w' if k == -half else 'rwy_end_e' if k == half else 'rwy_plain'
                        if end and abs(k) < half:
                            names[y, x], tsg[y, x], walk[y, x] = 'crosswalk_ns', RES, True
                            nr += 1
                            continue
                    else:
                        nm = 'rwy_plain'
                    names[y, x], tsg[y, x], walk[y, x] = nm, AV, True
                    nr += 1
        else:
            for x, y, v in _cells(G, f['pts']):
                if placed[y, x] or core[y, x] or str(names[y, x]).startswith('rwy'):
                    continue
                names[y, x], tsg[y, x], walk[y, x] = ('twy_v' if v else 'twy_h'), AV, True
                nt += 1
    return {'runway_tiles': nr, 'taxiway_tiles': nt}


# ---------------------------------------------------------------- golf
def _golf(G, tsg, names, walk, placed):
    feats = [f for f in G.F.get('feat', []) if f['closed'] and f['tags'].get('golf') in ('fairway', 'tee', 'green', 'bunker')]
    if not feats:
        return 0
    n = 0
    piece = {'fairway': 'fairway', 'tee': 'tee_box', 'green': 'golf_green', 'bunker': 'bunker'}
    greens = []
    for kind in ('fairway', 'tee', 'green', 'bunker'):
        polys = [G.local(f['pts']) for f in feats if f['tags']['golf'] == kind]
        m = G.poly_mask(polys) & ~placed & (G.road == 0) & (G.ground != G_WATER)
        lawnish = np.vectorize(lambda s: s == 'lawn' or str(s).startswith('prim:1') or s == 'prim:00d')(names) if m.any() else m
        m &= lawnish
        names[m] = piece[kind]; tsg[m] = CITY; walk[m] = True
        n += int(m.sum())
        if kind == 'green':
            greens = polys
    pins = [(n_['x'] - G.ox, n_['y'] - G.oy) for n_ in G.F.get('nfeat', []) if n_['tags'].get('golf') == 'pin']
    for p in greens:
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        pin = next(((px, py) for px, py in pins if min(xs) <= px <= max(xs) and min(ys) <= py <= max(ys)), (cx, cy))
        x, y = int(round(pin[0])), int(round(pin[1]))
        if 0 <= x < G.W and 0 <= y < G.H and names[y, x] == 'golf_green':
            names[y, x] = 'golf_flag'; walk[y, x] = False
    return n


# ---------------------------------------------------------------- street details
def _street_details(G, tsg, names, walk, placed):
    H, W = names.shape
    core = G.road
    st = {'signals': 0, 'crosswalks': 0, 'stop_signs': 0, 'street_signs': 0, 'hydrants': 0,
          'rr_signals': 0, 'lot_arrows': 0, 'gates': 0}
    LAWN = ('lawn',)
    rr_done = []
    gate_done, gate_band = [], None

    def free(y, x):
        return 0 <= y < H and 0 <= x < W and names[y, x] in LAWN and not placed[y, x]

    def tall(y, x, ts, base):
        if free(y, x) and free(y - 1, x):
            names[y - 1, x], names[y, x] = base + '_top', base + '_bottom'
            tsg[y - 1, x] = tsg[y, x] = ts
            walk[y - 1, x] = walk[y, x] = False
            placed[y - 1, x] = placed[y, x] = True
            return True
        return False

    def near_tall(cx, cy, ts, base, r=6):
        best = None
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                y, x = cy + dy, cx + dx
                if free(y, x) and free(y - 1, x) and _touches_ring(G, y, x):
                    d = dx * dx + dy * dy
                    if best is None or d < best[0]:
                        best = (d, y, x)
        return best is not None and tall(best[1], best[2], ts, base)

    for n in G.F.get('nfeat', []):
        t = n['tags']
        x, y = _loc(G, n['x'], n['y'])
        if not (2 <= x < W - 2 and 2 <= y < H - 2):
            continue
        if t.get('highway') == 'traffic_signals':
            if near_tall(x, y, RES, 'traffic_signal'):
                st['signals'] += 1
            st['crosswalks'] += _crosswalks(G, names, tsg, walk, placed, x, y)
        elif t.get('highway') == 'stop':
            if near_tall(x, y, RES, 'stop_sign', r=5):
                st['stop_signs'] += 1
        elif t.get('emergency') == 'fire_hydrant':
            for dy in range(-3, 4):
                done = False
                for dx in range(-3, 4):
                    if free(y + dy, x + dx):
                        names[y + dy, x + dx], tsg[y + dy, x + dx], walk[y + dy, x + dx] = 'hydrant', RES, False
                        placed[y + dy, x + dx] = True
                        st['hydrants'] += 1
                        done = True
                        break
                if done:
                    break
        elif t.get('railway') == 'level_crossing':
            if any(abs(x - a) + abs(y - b) < 10 for a, b in rr_done):
                continue
            best = None
            for dy in range(-4, 5):
                for dx in range(-5, 6):
                    if free(y + dy, x + dx) and free(y + dy - 1, x + dx) and _touches_ring(G, y + dy, x + dx) \
                            and _near_rail(G, y + dy, x + dx) and (best is None or abs(dx) + abs(dy) < best[0]):
                        best = (abs(dx) + abs(dy), y + dy, x + dx)
            if best and tall(best[1], best[2], RES, 'rr_crossing'):
                st['rr_signals'] += 1
                rr_done.append((x, y))
        elif t.get('barrier') in ('lift_gate', 'gate') or t.get('military') == 'checkpoint':
            # air base entrances: gates on a road near the base fence
            if gate_band is None:
                gate_band = _base_edge(G)
            if not gate_band[y, x] or any(abs(x - a) + abs(y - b) < 80 for a, b in gate_done):
                continue
            if _gate(G, names, tsg, walk, placed, x, y):
                st['gates'] += 1
                gate_done.append((x, y))
    # street-name signs on some town corners, hydrants every ~40 tiles along town curbs
    corner = {'block_corner_sw': (-1, 1), 'block_corner_se': (1, 1), 'block_corner_nw': (-1, -1), 'block_corner_ne': (1, -1)}
    for (y, x) in zip(*np.nonzero(np.isin(names, list(corner)))):
        if h32(x + G.ox, y + G.oy, 'ssign') % 4:
            continue
        dx, dy = corner[names[y, x]]
        if not (G.road[min(H - 1, max(0, y - 3 * dy)), x - dx] and G.road[y - dy, min(W - 1, max(0, x - 3 * dx))]):
            continue
        sx, sy = x + dx, y + dy + (1 if dy > 0 else 0)
        if tall(sy, sx, RES, 'street_sign'):
            st['street_signs'] += 1
    edge_out = {'road_edge_s': (0, 1), 'road_edge_n': (0, -1), 'road_edge_e': (1, 0), 'road_edge_w': (-1, 0)}
    for (y, x) in zip(*np.nonzero(np.isin(names, list(edge_out)))):
        dx, dy = edge_out[names[y, x]]
        along = (x + G.ox) if dy else (y + G.oy)
        if along % 41 != 13 or not G.zone[y, x] or G.metro[y, x]:
            continue
        if free(y + dy, x + dx):
            names[y + dy, x + dx], tsg[y + dy, x + dx], walk[y + dy, x + dx] = 'hydrant', RES, False
            placed[y + dy, x + dx] = True
            st['hydrants'] += 1
    # parking lot arrows in the aisles
    if getattr(G, 'parking', None) is not None:
        for (y, x) in zip(*np.nonzero(G.parking & (names == 'asphalt'))):
            if (y + G.oy) % 4 == 2 and (x + G.ox) % 15 == 7:
                names[y, x], tsg[y, x] = 'lot_arrow_n', COM
                st['lot_arrows'] += 1
    return st


def _base_edge(G):
    from geo.gen import box_dilate
    mil = G.poly_mask([G.local(f['pts']) for f in G.F.get('feat', []) if f['closed'] and
                       f['tags'].get('aeroway') == 'aerodrome' and
                       ('military' in f['tags'] or 'air force' in f['tags'].get('name', '').lower())])
    if not mil.any():
        return mil
    return mil & box_dilate(~mil, 40) & (G.road > 0)


def _touches_ring(G, y, x):
    r = G.road_ring_cache if hasattr(G, 'road_ring_cache') else None
    if r is None:
        G.road_ring_cache = r = G.road_ring()
    H, W = r.shape
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and r[yy, xx]:
                return True
    return False


def _near_rail(G, y, x, d=3):
    return G.rail[max(0, y - d):y + d + 1, max(0, x - d):x + d + 1].any()


def _crosswalks(G, names, tsg, walk, placed, px, py):
    """Zebra stripes across each arm of a signalled intersection, just outside the box."""
    H, W = names.shape
    core = G.road > 0
    if not core[py, px]:
        return 0

    def extent(x, y, vertical):
        n = 0
        if vertical:
            yy = y
            while yy >= 0 and core[yy, x]:
                yy -= 1; n += 1
            yy = y + 1
            while yy < H and core[yy, x]:
                yy += 1; n += 1
        else:
            xx = x
            while xx >= 0 and core[y, xx]:
                xx -= 1; n += 1
            xx = x + 1
            while xx < W and core[y, xx]:
                xx += 1; n += 1
        return n

    made = 0
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        vertical = dx != 0            # an E-W arm: its cross-section is a column
        far = (px + dx * 16, py + dy * 16)
        if not (0 <= far[0] < W and 0 <= far[1] < H) or not core[far[1], far[0]]:
            continue
        arm = extent(far[0], far[1], vertical)
        if arm > 6:
            continue
        for k in range(1, 14):
            x, y = px + dx * k, py + dy * k
            if not (0 <= x < W and 0 <= y < H) or not core[y, x]:
                break
            if extent(x, y, vertical) <= arm:
                cells = []
                if vertical:
                    yy = y
                    while yy >= 0 and core[yy, x]:
                        cells.append((yy, x)); yy -= 1
                    yy = y + 1
                    while yy < H and core[yy, x]:
                        cells.append((yy, x)); yy += 1
                else:
                    xx = x
                    while xx >= 0 and core[y, xx]:
                        cells.append((y, xx)); xx -= 1
                    xx = x + 1
                    while xx < W and core[y, xx]:
                        cells.append((y, xx)); xx += 1
                for (yy, xx) in cells:
                    if names[yy, xx] in ('asphalt', 'hwy_asphalt') and not placed[yy, xx]:
                        names[yy, xx] = 'crosswalk_ew' if vertical else 'crosswalk_ns'
                        tsg[yy, xx] = RES
                        made += 1
                break
    return made


def _gate(G, names, tsg, walk, placed, x, y):
    """Guard booth beside the road with the gate arm across one lane (air base entrances)."""
    H, W = names.shape
    if not G.road[y, x]:
        return False
    for dx in range(1, 6):
        for sx in (x - dx, x + dx):
            if 0 < sx < W and names[y, sx] == 'lawn' and names[y - 1, sx] == 'lawn' and not placed[y, sx]:
                names[y - 1, sx], names[y, sx] = 'guard_booth_00', 'guard_booth_01'
                tsg[y - 1, sx] = tsg[y, sx] = AV
                walk[y - 1, sx] = walk[y, sx] = False
                gx = sx + (1 if sx < x else -1)
                while 0 < gx < W and not G.road[y, gx]:
                    gx += 1 if sx < x else -1
                if 0 < gx < W:
                    names[y, gx], tsg[y, gx], walk[y, gx] = 'gate_arm', AV, False
                return True
    return False


# ---------------------------------------------------------------- Old Cowtown (future Elite Four)
WEST = 10
# property in county tiles: east of the museum parking lot, between Sim Park Drive / Museum
# Boulevard and McLean Boulevard (OSM maps only the museum point, so the outline is set here)
COWTOWN = (15662, 9700, 15868, 9758)


def cowtown(G):
    """Fenced 1870s town: entrance hall on the north fence line (a gatehouse: back doorway from
    the street, front doors into town), Main Street and Second Street of dirt with boardwalks and
    false-front stores, cabins along a south lane, a farm corral, a church."""
    from geo.gen import RUR, G_LAWN
    X0, Y0, X1, Y1 = (COWTOWN[0] - G.ox, COWTOWN[1] - G.oy, COWTOWN[2] - G.ox, COWTOWN[3] - G.oy)
    if X1 < -10 or Y1 < -10 or X0 > G.W + 10 or Y0 > G.H + 10:
        return
    W, H = X1 - X0, Y1 - Y0
    ys, xs = slice(max(0, Y0 - 5), min(G.H, Y1 + 1)), slice(max(0, X0), min(G.W, X1 + 1))
    # the museum grounds replace whatever OSM drew there
    inside = np.zeros((G.H, G.W), bool)
    inside[max(0, Y0):min(G.H, Y1 + 1), max(0, X0):min(G.W, X1 + 1)] = True
    G.road[inside] = 0
    G.ground[inside & (G.ground != G_WATER)] = G_LAWN
    G.zone[inside] = True
    G.metro[inside] = False
    for b in G.F['buildings']:
        cx = sum(p[0] for p in b['poly']) / len(b['poly']) - G.ox
        cy = sum(p[1] for p in b['poly']) / len(b['poly']) - G.oy
        if X0 - 6 <= cx <= X1 and Y0 - 6 <= cy <= Y1:
            G.used_buildings = getattr(G, 'used_buildings', set()); G.used_buildings.add(b['id'])
    G.cowtown = inside
    hs = lambda *a: h32('cowtown', *a)

    def P(x, y, ts, name, walk=False):
        if 0 <= X0 + x < G.W and 0 <= Y0 + y < G.H:
            G.obj[(X0 + x, Y0 + y)] = (ts, name, walk)
            G.occupied[Y0 + y, X0 + x] = True

    def dirt(x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                P(x, y, WEST, 'wdirt', True)

    def bld(kind, v, x, y, w, h, doors):
        for r in range(h):
            for c in range(w):
                P(x + c, y + r, WEST, f'{kind}_{v}_{c}{r}', (c, r) in doors)

    # fence all round, broken only by the entrance hall
    ex = 4                                   # entrance hall columns ex .. ex+7, rows -4 .. 0
    for x in range(0, W + 1):
        if not (ex <= x <= ex + 7):
            P(x, 0, RUR, 'corral_h')
        P(x, H, RUR, 'corral_h')
    for y in range(1, H):
        P(0, y, RUR, 'corral_v'); P(W, y, RUR, 'corral_v')
    bld('wentry', 'red', ex, -4, 8, 5, {(3, 4), (4, 4), (3, 0), (4, 0)})
    G.doors.append((X0 + ex + 3, Y0 - 4, 'cowtown_gate', 'Old Cowtown'))
    G.doors.append((X0 + ex + 3, Y0, 'cowtown_hall', 'Old Cowtown'))
    # walk from the street-side doorway north to the street
    for c in (3, 4):
        y = -5
        while Y0 + y > 0 and not G.road[Y0 + y, X0 + ex + c] and y > -40:
            P(ex + c, y, RES, 'sidewalk', True)
            y -= 1
    # streets: a lane from the hall's front doors down to Main Street, then Main and Second
    MAIN, SECOND, LANE = 11, 29, 46
    dirt(ex + 3, 1, ex + 4, MAIN)
    dirt(1, MAIN, W - 1, MAIN + 2)
    dirt(1, SECOND, W - 1, SECOND + 2)
    dirt(1, LANE, W - 1, LANE + 1)
    for x in (44, 96, 148, W - 12):
        dirt(x, MAIN, x + 1, LANE)
    # Main Street: false-front stores on the north side, boardwalk in front
    n_store = 0
    church_done = False
    x = ex + 9
    while x + 4 < W - 2:
        if x in range(43, 46) or x in range(95, 98) or x in range(147, 150):
            x += 3
            continue
        k = hs(x, 'main')
        if not church_done and x > W // 2 and x + 8 < W - 2:
            church_done = True
            from geo.civic import church
            church(G, X0 + x, Y0 + MAIN - 7, 8, 'brown', 'white')
            x += 10
            continue
        v = VARIANTS_W[k % len(VARIANTS_W)]
        bld('wstore', v, x, MAIN - 5, 4, 4, {(2, 3)})
        for c in range(4):
            P(x + c, MAIN - 1, WEST, 'wwalk', True)
        G.doors.append((X0 + x + 2, Y0 + MAIN - 2, 'cowtown_store', 'Old Cowtown'))
        n_store += 1
        x += 5 if k % 3 else 6
    # props along the street edge
    for x in range(ex + 9, W - 2, 7):
        if (X0 + x, Y0 + MAIN + 3) not in G.obj or G.obj[(X0 + x, Y0 + MAIN + 3)][1] == 'wdirt':
            pass
        P(x, MAIN + 2, WEST, ('whitch_dirt', 'wbarrel_dirt', 'wtrough_dirt')[hs(x, 'prop') % 3], False)
    # Second Street: stores and cabins facing it
    x = 3
    while x + 4 < W - 2:
        if any(a - 4 <= x <= a + 1 for a in (44, 96, 148, W - 12)):
            x += 2
            continue
        k = hs(x, 'second')
        v = VARIANTS_W[k % len(VARIANTS_W)]
        if k % 2:
            bld('wstore', v, x, SECOND - 5, 4, 4, {(2, 3)})
            for c in range(4):
                P(x + c, SECOND - 1, WEST, 'wwalk', True)
            G.doors.append((X0 + x + 2, Y0 + SECOND - 2, 'cowtown_store', 'Old Cowtown'))
            n_store += 1
        else:
            bld('wcabin', v, x, SECOND - 3, 4, 3, {(1, 2)})
            G.doors.append((X0 + x + 1, Y0 + SECOND - 1, 'cowtown_cabin', 'Old Cowtown'))
        x += 6
    # the south lane: homesteads west, the farm corral east
    x = 3
    n_cabin = 0
    while x + 4 < W * 0.6:
        if any(a - 4 <= x <= a + 1 for a in (44, 96, 148)):
            x += 2
            continue
        v = VARIANTS_W[hs(x, 'lane') % len(VARIANTS_W)]
        bld('wcabin', v, x, LANE - 3, 4, 3, {(1, 2)})
        G.doors.append((X0 + x + 1, Y0 + LANE - 1, 'cowtown_cabin', 'Old Cowtown'))
        n_cabin += 1
        x += 8
    cx0, cx1, cy0, cy1 = int(W * 0.62), W - 16, LANE + 3, H - 3
    for xx in range(cx0, cx1 + 1):
        P(xx, cy0, RUR, 'corral_h'); P(xx, cy1, RUR, 'corral_h')
    for yy in range(cy0 + 1, cy1):
        P(cx0, yy, RUR, 'corral_v'); P(cx1, yy, RUR, 'corral_v')
    G.occupied[max(0, Y0 + cy0):max(0, Y0 + cy1), max(0, X0 + cx0):max(0, X0 + cx1)] = True     # open pasture
    for k in range(8):
        cx, cy = cx0 + 3 + hs(k, 'cx') % max(1, cx1 - cx0 - 5), cy0 + 2 + hs(k, 'cy') % max(1, cy1 - cy0 - 3)
        P(cx, cy, RUR, 'cow_angus' if k % 2 else 'cow_holstein')
    P(cx0 - 3, LANE + 3, WEST, 'wwagon_00'); P(cx0 - 2, LANE + 3, WEST, 'wwagon_10')
    # everything not drawn stays open grass (trees may grow there); nothing else builds inside
    # (gen adds G.cowtown to G.blocked)
    G.stats['cowtown_stores'] = n_store
    G.stats['cowtown_cabins'] = n_cabin


VARIANTS_W = ('weathered', 'red', 'ochre', 'white', 'brown')
