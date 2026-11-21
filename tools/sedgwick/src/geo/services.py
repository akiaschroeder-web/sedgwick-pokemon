"""Pokémon Centers (1-2 per town) and Poké Marts (every gas station).

  python3 geo/services.py plan   -> ../../services.json  (county-wide, exact tile spots)
  build(G)                       stamps the planned buildings inside a generator window

Planning is done once for the whole county from the OSM data alone, so every region
that overlaps a building stamps it at the same place. A Center goes on the nearest
open ground to the town's centre whose door faces a street within a few tiles, and it
keeps clear of every mapped building and address point (so no house is displaced).
A Mart replaces the gas station building itself."""
import json, math, os, pickle, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geo import extract

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(HERE, '..', '..', 'services.json')
LM, RES = 5, 0
PC_W, PC_H, PC_DOOR = 5, 5, (2, 4)
MART_W, MART_H, MART_DOOR = 4, 4, (2, 3)
# A whole station: the store (4x4, top-left) beside a pump canopy (5x3) on a concrete pad,
# price-sign pylon on the lawn at the front corner. Drive lane in front reaches the street.
STN_W, STN_H = 11, 6
CEL_COLORS = ('mint', 'brick', 'beige')
TWO_CENTERS = 10000                      # towns at least this big get a second Center
ROAD_HALF = {'street': 3, 'service': 3, 'highway': 4, 'gravel': 3, 'alley': 2, 'track': 2, 'motorway': 6}
NOT_TOWNS = {'Sedgwick', 'Andover', 'Rose Hill'}   # their centres lie outside the county


def load():
    if not os.path.exists(PLAN):
        return []
    return json.load(open(PLAN))['buildings']


# ---------------------------------------------------------------- planning
def _towns(nodes, ways, rels, ring):
    from geo.boundary import rings, inside
    pops = {}
    for k, (la, lo, t) in nodes.items():
        if t and t.get('place') in ('city', 'town', 'village') and t.get('name'):
            pops[t['name']] = (lo, la, int(t['population']) if t.get('population', '').isdigit() else 0)
    names = {'Wichita'} | {v[1].get('name') for v in rels.values()
                           if v[1].get('boundary') == 'administrative' and v[1].get('admin_level') == '8'}
    out = []
    for name in sorted(n for n in names if n and n not in NOT_TOWNS):
        if name in pops:
            lo, la, pop = pops[name]
        else:                             # no place node (Kechi): centre of its city limits
            rel = next(v for v in rels.values() if v[1].get('name') == name and v[1].get('admin_level') == '8')
            pts = [q for r in rings(rel, ways, nodes, 'outer') for q in r]
            lo, la, pop = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), 0
        x, y = extract.proj(lo, la)
        if inside((x, y), [ring]):
            out.append({'name': name, 'x': x, 'y': y, 'pop': pop})
    return out


def _second_anchor(F, town):
    """k-means (k=2) over the town's address points; the centre farther from downtown."""
    pts = np.array([(a['x'], a['y']) for a in F['addresses'] if a['tags'].get('addr:city', '').lower() == town['name'].lower()])
    if len(pts) < 50:
        return None
    c = np.array([pts.min(0), pts.max(0)], float)
    for _ in range(30):
        lab = ((pts[:, None, :] - c[None]) ** 2).sum(-1).argmin(1)
        c = np.array([pts[lab == k].mean(0) if (lab == k).any() else c[k] for k in range(2)])
    d = ((c - [town['x'], town['y']]) ** 2).sum(1)
    return tuple(c[d.argmax()])


class Window:
    """Obstacle raster of one area, from OSM: roads, buildings, water, rail, addresses."""
    def __init__(self, F, cx, cy, R, ignore_buildings=(), ignore_near=None, addresses=True):
        self.ox, self.oy, self.S = int(cx) - R, int(cy) - R, 2 * R
        S = self.S
        road = Image.new('L', (S, S), 0); rd = ImageDraw.Draw(road)
        hard = Image.new('1', (S, S), 0); hd = ImageDraw.Draw(hard)
        L = lambda p: [(q[0] - self.ox, q[1] - self.oy) for q in p]
        code = {'motorway': 9}
        for r in F['roads']:
            w = ROAD_HALF.get(r['cls'])
            if not w or r['cls'] == 'driveway':
                continue
            rd.line(L(r['pts']), fill=code.get(r['cls'], 1), width=2 * w + 1)
        for rl in F['rail']:
            hd.line(L(rl['pts']), fill=1, width=5)
        for a in F['areas']:
            if a['cls'] == 'water':
                hd.polygon(L(a['poly']), fill=1)
        for b in F['buildings']:
            if b['id'] not in ignore_buildings:
                hd.polygon(L(b['poly']), fill=1, outline=1)
        for a in (F['addresses'] if addresses else []):
            if ignore_near and math.dist((a['x'], a['y']), ignore_near) < 12:
                continue
            x, y = a['x'] - self.ox, a['y'] - self.oy
            hd.rectangle([x - 6, y - 6, x + 6, y + 6], fill=1)
        self.road = np.array(road)
        self.free = ~(np.array(hard, bool) | (self.road > 0))
        ii = np.zeros((S + 1, S + 1), np.int32)
        ii[1:, 1:] = np.cumsum(np.cumsum(~self.free, 0), 1)
        self.ii = ii

    def clear(self, x, y, w, h):
        if x < 0 or y < 0 or x + w > self.S or y + h > self.S:
            return False
        ii = self.ii
        return ii[y + h, x + w] - ii[y, x + w] - ii[y + h, x] + ii[y, x] == 0

    def street_below(self, x, y, reach):
        """Tiles from (x, y) straight down to a non-motorway road, or None."""
        for d in range(reach + 1):
            yy = y + d
            if yy >= self.S:
                return None
            if self.road[yy, x]:
                return d if self.road[yy, x] != 9 else None
            if not self.free[yy, x]:
                return None
        return None

    def best(self, cx, cy, w, h, door, reach, R, avoid=()):
        best = None
        ax, ay = int(cx) - self.ox, int(cy) - self.oy
        for y in range(max(1, ay - R), min(self.S - h - 1, ay + R)):
            for x in range(max(1, ax - R), min(self.S - w - 1, ax + R)):
                d0 = (x + w / 2 - ax) ** 2 + (y + h / 2 - ay) ** 2
                if best is not None and d0 >= best[0]:
                    continue
                if not self.clear(x - 1, y - 1, w + 2, h + 2):
                    continue
                if any(math.dist((x + self.ox, y + self.oy), a) < 40 for a in avoid):
                    continue
                d = self.street_below(x + door[0], y + h, reach)
                if d is None:
                    continue
                best = (d0 + 4 * d * d, x, y)
        return best and (best[1] + self.ox, best[2] + self.oy)


def plan():
    from geo.boundary import county_ring
    nodes, ways, rels = pickle.load(open('/home/claude/osm_in/raw.pkl', 'rb'))
    ring = [extract.proj(*q) for q in county_ring(rels[973225], ways, nodes)]
    F = extract.extract((nodes, ways, rels), None)
    F['bbox'] = (0, 0, extract.WIDTH, extract.HEIGHT)
    from geo import county, rectify
    warps = pickle.load(open(f'{county.OUT}/warps.pkl', 'rb'))
    county.apply_warps(F, warps, [])
    fns = [rectify.warp_fn(wp['ang'], wp['poly']) for wp in warps]
    def warp(p):
        for f in fns:
            p = f(p)
        return p
    from geo import gyms
    gym_pts = [extract.proj(g['lon'], g['lat']) for g in gyms.load()]
    out = []
    # Pokémon Centers
    for t in _towns(nodes, ways, rels, ring):
        t['x'], t['y'] = warp((t['x'], t['y']))
        anchors = [(t['x'], t['y'])]
        if t['pop'] >= TWO_CENTERS:
            a2 = _second_anchor(F, t)
            if a2:
                anchors.append(a2)   # address points are already warped
        for k, (ax, ay) in enumerate(anchors):
            spot = None
            for R in (60, 140, 260):
                W = Window(F, ax, ay, R + 20)
                spot = W.best(ax, ay, PC_W, PC_H, PC_DOOR, 5, R, avoid=gym_pts + [(o['x'], o['y']) for o in out])
                if spot:
                    break
            if not spot:
                print('no Center spot for', t['name'], k)
                continue
            name = t['name'] + ('' if len(anchors) == 1 else (' downtown' if k == 0 else ' (second)'))
            out.append({'kind': 'pc', 'town': t['name'], 'name': f'{name} Pokémon Center', 'x': spot[0], 'y': spot[1]})
            print('Center', name, spot, 'from anchor', (int(ax), int(ay)))
    # Poké Marts: every gas station
    from geo.boundary import inside
    stations = []
    for b in F['buildings']:
        if b['tags'].get('amenity') == 'fuel':
            xs = [p[0] for p in b['poly']]; ys = [p[1] for p in b['poly']]
            stations.append((sum(xs) / len(xs), sum(ys) / len(ys), b['tags'].get('name') or b['tags'].get('brand', ''), [b['id']]))
    for a in F['areas']:
        if a['tags'].get('amenity') == 'fuel':
            xs = [p[0] for p in a['poly']]; ys = [p[1] for p in a['poly']]
            stations.append((sum(xs) / len(xs), sum(ys) / len(ys), a['tags'].get('name') or a['tags'].get('brand', ''), []))
    for la, lo, t in nodes.values():          # straight from OSM: tagged nodes with an address skip F['pois']
        if t and t.get('amenity') == 'fuel':
            stations.append((*warp(extract.proj(lo, la)), t.get('name') or t.get('brand', ''), []))
    seen = []
    for sx, sy, nm, ids in stations:
        if not inside((sx, sy), [ring]) or any(math.dist((sx, sy), s) < 15 for s in seen):
            continue
        seen.append((sx, sy))
        # the station's own buildings (shop, canopy) make way for the Mart
        own = set(ids) | {b['id'] for b in F['buildings'] if any(math.dist(q, (sx, sy)) < 18 for q in b['poly'][:1])}
        W = Window(F, sx, sy, 40, ignore_buildings=own, ignore_near=(sx, sy))
        W2 = Window(F, sx, sy, 50, ignore_buildings=own, ignore_near=(sx, sy), addresses=False)
        layout, spot = 'station', W.best(sx, sy, STN_W, STN_H, (2, 0), 8, 24)
        if not spot:      # tight commercial lot: let neighbouring address pins go, reach further
            spot = W2.best(sx, sy, STN_W, STN_H, (2, 0), 10, 30)
        if not spot:      # no room for pumps: the store alone
            layout, spot = 'store', W.best(sx, sy, MART_W, MART_H, MART_DOOR, 8, 24) or \
                W2.best(sx, sy, MART_W, MART_H, MART_DOOR, 12, 32)
        if not spot:
            print('no Mart spot for', nm, (int(sx), int(sy)))
            continue
        # about two in five keep a plain convenience store instead of a Mart
        hsh = (int(sx) * 73856093 ^ int(sy) * 19349663) & 0xffff
        store = 'mart' if hsh % 5 >= 2 else 'cel:' + CEL_COLORS[hsh // 5 % 3]
        out.append({'kind': 'mart' if store == 'mart' else 'gas', 'name': nm or 'Gas station', 'x': spot[0], 'y': spot[1],
                    'layout': layout, 'store': store, 'replaces': sorted(own)})
    print(sum(o['kind'] == 'pc' for o in out), 'Centers,', sum(o['kind'] == 'mart' for o in out), 'Marts,',
          sum(o['kind'] == 'gas' for o in out), 'plain stations,', sum(o.get('layout') == 'station' for o in out), 'with pumps')
    json.dump({'_doc': 'Generated by geo/services.py plan: Pokémon Centers and Poké Marts (gas stations). x, y = top-left tile.',
               'buildings': out}, open(PLAN, 'w'), indent=1, ensure_ascii=False)


# ---------------------------------------------------------------- stamping
COM = 2


def _landmark(G, piece, x, y, door):
    import landmarks
    dn = f'lm_{piece}_{door[0]}{door[1]}'
    for r, row in enumerate(landmarks.plan(piece)):
        for c, nm in enumerate(row):
            G.put(x + c, y + r, LM, nm, nm == dn)
    return (x + door[0], y + door[1])


def _store(G, store, x, y):
    if store == 'mart':
        return _landmark(G, 'mart', x, y, MART_DOOR)
    import commercial
    color = store.split(':')[1]
    rows = commercial.plan(1, 1, (), doors=(0,))
    door = None
    for r, row in enumerate(rows):
        for c, m in enumerate(row):
            G.put(x + c, y + r, COM, f'cel_{m:03x}_{color}', m == commercial.DOOR)
            if m == commercial.DOOR:
                door = (x + c, y + r)
    return door or (x + 1, y + len(rows) - 1)


def _station(G, x, y):
    """Pad, pump canopy and price sign around a store at (x, y)."""
    for r in range(STN_H):
        for c in range(STN_W - 1):
            G.put(x + c, y + r, COM, 'gas_pad', True)
    cx = x + 5
    for c in range(5):
        G.put(cx + c, y + 1, COM, f'gas_canopy_{c}0', True)
        G.put(cx + c, y + 2, COM, f'gas_canopy_{c}1', True)
        G.put(cx + c, y + 3, COM, f'gas_pumps_{c}0', c not in (0, 4))
    G.put(x + STN_W - 1, y + 3, COM, 'gas_sign_00', False)
    G.put(x + STN_W - 1, y + 4, COM, 'gas_sign_01', False)


def build(G):
    import landmarks
    from geo import gyms
    G.services = []
    G.used_buildings = getattr(G, "used_buildings", set())
    n = {'pc': 0, 'mart': 0, 'gas': 0, 'pumps': 0}
    for s in load():
        if s['kind'] == 'pc':
            w, h = PC_W, PC_H
        elif s.get('layout') == 'station':
            w, h = STN_W, STN_H
        else:
            w, h = MART_W, MART_H
        x, y = int(s['x'] - G.ox), int(s['y'] - G.oy)
        if not (-w < x < G.W and -h < y < G.H):
            continue
        for bid in s.get('replaces', []):
            G.used_buildings.add(bid)
        # anything else mapped under the footprint makes way too
        for b in G.F['buildings']:
            xs = [p[0] - G.ox for p in b['poly']]; ys = [p[1] - G.oy for p in b['poly']]
            if min(xs) < x + w + 1 and max(xs) > x - 1 and min(ys) < y + h + 1 and max(ys) > y - 1:
                G.used_buildings.add(b['id'])
        y0, y1, x0, x1 = max(0, y - 1), min(G.H, y + h + 1), max(0, x - 1), min(G.W, x + w + 1)
        G.road[y0:y1, x0:x1] = 0
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                G.obj.pop((xx, yy), None)
        if s['kind'] == 'pc':
            door = _landmark(G, 'pc', x, y, PC_DOOR)
            walk_from = door
        else:
            if s.get('layout') == 'station':
                _station(G, x, y)
                n['pumps'] += 1
            door = _store(G, s.get('store', 'mart'), x, y)
            walk_from = (x + 2, y + STN_H - 1) if s.get('layout') == 'station' else door
        G.occupied[y0:y1, x0:x1] = True
        if 0 < walk_from[0] < G.W - 1 and 0 < walk_from[1] < G.H - 1:
            gyms._walk_to_street(G, *walk_from)
        G.services.append(dict(s, door=door))
        n[s['kind']] += 1
    G.stats['gas_stations'] = n['gas']
    G.stats['pump_canopies'] = n['pumps']
    G.stats['centers'] = n['pc']
    G.stats['marts'] = n['mart']


if __name__ == '__main__':
    if sys.argv[1:] == ['plan']:
        plan()
