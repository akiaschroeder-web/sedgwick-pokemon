"""Map generator prototype: classified OSM features -> metatile cells.

This is the reference for the runtime generator. Passes run in a fixed order:
  1. zones      town (residential tileset) vs country (rural tileset)
  2. ground     lawn / crops / wood / water / parking from land-use polygons
  3. roads      cores drawn with a square brush, then edge rings autotiled
  4. rail
  5. houses     one per address point, facing its own street
  6. buildings  remaining OSM footprints (civic / commercial), from the house kit
  7. trees      yard trees, wood areas, windbreaks
Output: per-tile (tileset index, metatile name, walkable)."""
import json, math, os, zlib
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
TSDIR = os.path.join(HERE, '..', '..')
TILESETS = ['sedgwick_residential', 'sedgwick_rural', 'sedgwick_commercial', 'sedgwick_downtown']
RES, RUR = 0, 1

# ground classes
G_LAWN, G_FIELD, G_WOOD, G_WATER, G_PARK, G_PARKING, G_CEMETERY, G_MEADOW, G_FARMYARD, G_DITCH, G_PRAIRIE = range(11)
# NLCD 2025 land cover classes -> ground (None = keep the default)
NLCD_GROUND = {11: G_WATER, 31: G_MEADOW, 41: G_WOOD, 42: G_WOOD, 43: G_WOOD, 52: G_PRAIRIE, 71: G_PRAIRIE,
               81: G_MEADOW, 82: G_FIELD, 90: G_WOOD, 95: G_PRAIRIE}
# road classes (core cells)
R_NONE, R_STREET, R_MAIN, R_HWY, R_GRAVEL, R_ALLEY = range(6)
WIDTH = {'street': 2, 'service': 2, 'highway': 3, 'gravel': 2, 'alley': 1, 'track': 1, 'motorway': 4}
RCLS = {'street': R_STREET, 'service': R_STREET, 'highway': R_HWY, 'gravel': R_GRAVEL, 'alley': R_ALLEY,
        'track': R_GRAVEL, 'motorway': R_HWY}
CROPS = ['wheat', 'wheat', 'soybeans', 'corn', 'stubble', 'plowed', 'wheat', 'soybeans']


def box_dilate(m, r):
    c = np.pad(m.astype(np.int32), ((r + 1, r), (r + 1, r))).cumsum(0).cumsum(1)
    s = c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]
    return s > 0


def vnoise(H, W, ox, oy, cell, seed):
    """Smooth value noise in [0, 1) on world coordinates (stable across map edges)."""
    gx0, gy0 = ox // cell, oy // cell
    gw, gh = (ox + W) // cell - gx0 + 2, (oy + H) // cell - gy0 + 2
    jj, ii = np.mgrid[0:gh, 0:gw]
    v = ((ii + gx0).astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15)) ^ \
        ((jj + gy0).astype(np.uint64) * np.uint64(0xC2B2AE3D27D4EB4F)) ^ np.uint64(zlib.crc32(seed.encode()))
    v ^= v >> np.uint64(31); v *= np.uint64(0xBF58476D1CE4E5B9)          # splitmix64 finaliser
    v ^= v >> np.uint64(27); v *= np.uint64(0x94D049BB133111EB)
    v ^= v >> np.uint64(31)
    g = (v >> np.uint64(40)).astype(np.float64) / float(1 << 24)
    ys, xs = np.mgrid[0:H, 0:W]
    fx, fy = (xs + ox) / cell - gx0, (ys + oy) / cell - gy0
    ix, iy = fx.astype(int), fy.astype(int)
    tx, ty = fx - ix, fy - iy
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a, b = g[iy, ix], g[iy, ix + 1]
    c, d = g[iy + 1, ix], g[iy + 1, ix + 1]
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty


def h32(*a):
    return zlib.crc32(repr(a).encode()) & 0xffffffff


class Gen:
    def __init__(self, F, town_rings, land=None, canopy=None):
        self.F = F
        x0, y0, x1, y1 = F['bbox']
        self.ox, self.oy = x0, y0
        self.W, self.H = x1 - x0, y1 - y0
        W, H = self.W, self.H
        self.ids = [json.load(open(f'{TSDIR}/{t}_metatiles.json')) for t in TILESETS]
        limits = self.poly_mask([self.local(r) for r in town_rings])
        # town style only where the town is built up: near streets and addresses
        im = Image.new('1', (W, H), 0)
        d = ImageDraw.Draw(im)
        for r in F['roads']:
            if r['cls'] in ('street', 'service', 'alley'):
                d.line(self.local(r['pts']), fill=1)
        for a in F['addresses']:
            d.point((a['x'] - self.ox, a['y'] - self.oy), fill=1)
        dev = box_dilate(np.array(im, bool), 28)
        if land is not None:
            # satellite built-up land (NLCD developed 21-24) bounds the town style
            built = np.isin(land, (21, 22, 23, 24)) | (land == 250)
            dev &= box_dilate(built, 6)
        lu = self.poly_mask([self.local(a['poly']) for a in F['areas'] if a['cls'] in ('residential', 'commercial')])
        if land is not None:
            lu &= dev
        self.zone = (limits & dev) | lu
        self.ground = np.full((H, W), G_FIELD, np.uint8)
        self.ground[self.zone] = G_LAWN
        self.road = np.zeros((H, W), np.uint8)
        self.roadid = np.zeros((H, W), np.int32)
        self.oneway = np.zeros((H, W), bool)      # index+1 into F['roads'] for name lookups
        self.rail = np.zeros((H, W), bool)
        self.obj = {}                                # (x, y) -> (ts, name, walk)   placed pieces
        self.occupied = np.zeros((H, W), bool)       # footprint reservations
        self.signs = []
        self.stats = {}
        self.houses = []
        self.featured = []
        self.no_infill = []
        self.doors = []              # (x, y, kind, address): door / mat cells for warps
        self.land, self.canopy = land, canopy        # NLCD grids on this map's tiles (or None)
        self.civic_done = []

    # ------------------------------------------------------------ helpers
    def local(self, p):
        return [(x - self.ox, y - self.oy) for x, y in p]

    def poly_mask(self, polys, holes=()):
        im = Image.new('1', (self.W, self.H), 0)
        d = ImageDraw.Draw(im)
        for p in polys:
            if len(p) >= 3:
                d.polygon([(x, y) for x, y in p], fill=1)
        for p in holes:
            q = self.local(p)
            if len(q) >= 3:
                d.polygon(q, fill=0)
        return np.array(im, bool)

    def brush_line(self, pts, w, fn):
        """Sweep a w x w square along the polyline; fn(x, y) for each covered tile."""
        seen = set()
        half = w / 2
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(bx - ax, by - ay) * 3))
            for i in range(n + 1):
                px, py = ax + (bx - ax) * i / n, ay + (by - ay) * i / n
                tx0, ty0 = int(round(px - half)), int(round(py - half))
                for ty in range(ty0, ty0 + w):
                    for tx in range(tx0, tx0 + w):
                        if (tx, ty) not in seen and 0 <= tx < self.W and 0 <= ty < self.H:
                            seen.add((tx, ty))
                            fn(tx, ty)

    def put(self, x, y, ts, name, walk=False):
        if 0 <= x < self.W and 0 <= y < self.H:
            assert name in self.ids[ts] or name.startswith('prim:'), name
            self.obj[(x, y)] = (ts, name, walk)

    # ------------------------------------------------------------ passes
    def pass_ground(self):
        order = ['farmland', 'meadow', 'farmyard', 'park', 'cemetery', 'wood', 'parking', 'water']
        cls = {'farmland': G_FIELD, 'meadow': G_MEADOW, 'farmyard': G_FARMYARD, 'park': G_PARK,
               'cemetery': G_CEMETERY, 'wood': G_WOOD, 'parking': G_PARKING, 'water': G_WATER}
        self.field_id = np.zeros((self.H, self.W), np.int32)
        have = None
        if self.land is not None:
            # satellite land cover first; OSM land use only adds what it maps precisely
            have = self.land != 250
            for code, gc in NLCD_GROUND.items():
                m = (self.land == code)
                if gc != G_WATER and gc != G_WOOD:
                    m &= ~self.zone
                self.ground[m] = gc
        for k in order:
            if have is not None and k in ('farmland', 'meadow'):
                continue
            for a in self.F['areas']:
                if a['cls'] != k:
                    continue
                m = self.poly_mask([self.local(a['poly'])], a.get('holes', ()))
                if k == 'farmland' or k == 'meadow':
                    m &= ~self.zone if k == 'farmland' else m
                    self.field_id[m] = a['id'] & 0x7fffffff
                self.ground[m] = cls[k]
        # fields with no polygon: one crop per quarter-section (half-mile square, 322 tiles)
        ys, xs = np.mgrid[0:self.H, 0:self.W]
        q = ((ys + self.oy) // 322) * 1000 + (xs + self.ox) // 322
        nofield = (self.field_id == 0)
        self.field_id[nofield] = q[nofield] + 1

    def pass_roads(self):
        prio = {R_ALLEY: 1, R_GRAVEL: 2, R_STREET: 3, R_MAIN: 4, R_HWY: 5}
        for i, r in enumerate(self.F['roads']):
            c = r['cls']
            if c in ('driveway',) or c not in WIDTH:
                continue
            rc = RCLS[c]
            p = self.local(r['pts'])
            if r.get('link') and sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(p, p[1:])) < 80:
                continue                     # short turn ramps only clutter a Gen 3 junction
            if c in ('street', 'service'):
                from geo import octi
                p = octi.snap(p)
            w = WIDTH[c]
            if c == 'street' and r['name'].endswith('Main Street'):
                rc, w = R_MAIN, 3
            ow = bool(r.get('oneway'))
            def f(x, y, rc=rc, i=i, ow=ow):
                if prio[rc] > prio.get(int(self.road[y, x]), 0):
                    self.road[y, x] = rc
                    self.roadid[y, x] = i + 1
                    self.oneway[y, x] = ow
            self.brush_line(p, w, f)
        # parking lots: asphalt with curbs, drawn as low-priority street cores
        self.parking = np.zeros((self.H, self.W), bool)
        self.reserved = np.zeros((self.H, self.W), bool)
        self.bulbs = []
        for a in self.F['areas']:
            if a['cls'] == 'parking':
                m = self.poly_mask([self.local(a['poly'])]) & (self.road == 0)
                self.road[m] = R_STREET
                self.parking |= m
        self.find_bulbs()
        for r in self.F['rail']:
            if r['state'] == 'abandoned':
                continue
            p = self.local(r['pts'])
            def f(x, y):
                self.rail[y, x] = True
            self.brush_line(p, 1, f)

    # ------------------------------------------------------------ houses
    def street_dirs(self, x, y, maxd=40):
        """Nearest street core in each direction: {dir: (dist, roadid)}."""
        out = {}
        for d, (dx, dy) in (('n', (0, -1)), ('s', (0, 1)), ('w', (-1, 0)), ('e', (1, 0))):
            for k in range(1, maxd):
                X, Y = x + dx * k, y + dy * k
                if not (0 <= X < self.W and 0 <= Y < self.H):
                    break
                if self.road[Y, X] in (R_STREET, R_MAIN, R_HWY, R_GRAVEL):
                    out[d] = (k, int(self.roadid[Y, X]))
                    break
        return out

    def find_bulbs(self):
        """Cul-de-sac bulbs at OSM turning circles on 2-lane streets."""
        core = self.road == R_STREET
        for t in self.F.get('turns', []):
            px, py = int(round(t['x'] - self.ox)), int(round(t['y'] - self.oy))
            if not (8 <= px < self.W - 8 and 8 <= py < self.H - 8):
                continue
            # which way does the street leave the circle?
            runs = {}
            for d, (dx, dy) in (('n', (0, -1)), ('s', (0, 1)), ('w', (-1, 0)), ('e', (1, 0))):
                k = 0
                while k < 10 and core[py + dy * (k + 1), px + dx * (k + 1)] if 0 <= py + dy * (k + 1) < self.H and 0 <= px + dx * (k + 1) < self.W else False:
                    k += 1
                runs[d] = k
            d = max(runs, key=runs.get)
            if runs[d] < 4 or sorted(runs.values())[-2] >= 3:
                continue                       # not a clean dead end
            if d in 'ns':
                xs = [x for x in range(px - 3, px + 4) if core[py + (-3 if d == 'n' else 3), x]]
                if len(xs) != 2:
                    continue
                x0, y0 = xs[0] - 2, py - 3
                kind = '' if d == 'n' else 'N'
            else:
                ys = [y for y in range(py - 3, py + 4) if core[y, px + (-3 if d == 'w' else 3)]]
                if len(ys) != 2:
                    continue
                x0, y0 = px - 3, ys[0] - 2
                kind = 'E' if d == 'w' else 'W'
            if x0 < 1 or y0 < 1 or x0 + 7 > self.W or y0 + 7 > self.H:
                continue
            self.bulbs.append((x0, y0, kind))
            self.reserved[y0 - 1:y0 + 7, x0 - 1:x0 + 7] = True

    def stamp_bulbs(self, tsg, names):
        import math as m
        for x0, y0, kind in self.bulbs:
            for r in range(6):
                for c in range(6):
                    # native frame (street from the north) for the inside test
                    if kind == '':
                        nc, nr = c, r
                    elif kind == 'N':
                        nc, nr = c, 5 - r
                    elif kind == 'E':
                        nc, nr = r, c
                    else:
                        nc, nr = r, 5 - c
                    name = f'culdesac{kind}_{c}{r}'
                    if name not in self.ids[RES]:
                        px, py = nc * 16 + 8, nr * 16 + 8
                        inside = m.hypot(px - 48, py - 52) < 40 or (py < 52 and abs(px - 48) < 20)
                        name = 'asphalt' if inside else 'lawn'
                    if (x0 + c, y0 + r) in self.obj and name == 'lawn':
                        continue
                    names[y0 + r, x0 + c] = name
                    tsg[y0 + r, x0 + c] = RES

    def road_ring(self):
        core = self.road > 0
        ring = np.zeros_like(core)
        ring[1:] |= core[:-1]; ring[:-1] |= core[1:]; ring[:, 1:] |= core[:, :-1]; ring[:, :-1] |= core[:, 1:]
        ring[1:, 1:] |= core[:-1, :-1]; ring[1:, :-1] |= core[:-1, 1:]; ring[:-1, 1:] |= core[1:, :-1]; ring[:-1, :-1] |= core[1:, 1:]
        return core | ring

    def pass_houses(self):
        roads = self.road_ring()
        self.blocked = roads | self.rail | (self.ground == G_WATER) | self.reserved
        bmask = {}
        for b in self.F['buildings']:
            xs = [p[0] - self.ox for p in b['poly']]; ys = [p[1] - self.oy for p in b['poly']]
            bmask[b['id']] = (min(xs), min(ys), max(xs), max(ys), b)
        self.used_buildings = set()
        placed = skipped = 0
        norm = lambda s: s.lower().replace('north ', '').replace('south ', '').replace('east ', '').replace('west ', '')
        for a in sorted(self.F['addresses'], key=lambda a: (not a.get('featured'), a['y'], a['x'])):
            t = a['tags']
            if any(k in t for k in ('amenity', 'shop', 'office', 'leisure', 'craft')):
                continue
            x, y = int(a['x'] - self.ox), int(a['y'] - self.oy)
            if not (0 <= x < self.W and 0 <= y < self.H) or not self.zone[y, x]:
                continue
            dirs = self.street_dirs(x, y)
            if not dirs:
                skipped += 1
                continue
            want = norm(a['street'])
            match = [d for d, (k, rid) in dirs.items() if rid and norm(self.F['roads'][rid - 1]['name']) == want]
            d = min(match or dirs, key=lambda d: dirs[d][0])
            # footprint from an OSM building under the point, else a typical ranch house
            fw = None
            for bx0, by0, bx1, by1, b in bmask.values():
                if bx0 <= x <= bx1 and by0 <= y <= by1:
                    fw = (bx1 - bx0) if d in 'ns' else (by1 - by0)
                    self.used_buildings.add(b['id'])
                    break
            hs = h32(a['num'], a['street'])
            width = max(5, min(9, int(round(fw)) if fw else 6 + hs % 2))
            storeys = 2 if hs % 5 == 0 else 1
            st = a.get('style') or {}
            width, storeys = st.get('width', width), st.get('storeys', storeys)
            self.style = st
            if a.get('featured'):
                self.featured.append((x, y, f"{a['num']} {a['street']}"))
            if self.place_house(x, y, d, dirs[d][0], width, storeys, hs, f"{a['num']} {a['street']}"):
                placed += 1
                if st.get('neighbors_east') and d == 's' and not getattr(self, 'skip_neighbors', False):
                    self.fix_neighbors_east(self.houses[-1], st['neighbors_east'])
            elif self.place_house(x, y, d, dirs[d][0], 5, 1, hs, f"{a['num']} {a['street']}"):
                placed += 1
            else:
                skipped += 1
        self.stats['houses'] = placed
        self.stats['house_skipped'] = skipped

    def place_house(self, ax, ay, d, dist, width, storeys, hs, address):
        rows = 3 if storeys == 1 else 5
        st = getattr(self, 'style', {}) or {}
        self.style = {}
        self._hstyle = st
        roof = st.get('roof', ('red', 'brown', 'charcoal')[hs % 3])
        wall = st.get('wall', ('white', 'tan')[(hs >> 3) % 2])
        garage = st.get('garage', 'l' if (hs >> 5) % 2 else 'r')
        setback = 3 + (hs >> 7) % 2
        # position the house box (x0, y0, width, rows) relative to the street
        if d == 's':        # street below: wall row faces it
            edge = ay + dist - 1                      # first ring row above the core
            y0 = edge - setback - rows
            x0 = ax - width // 2
        elif d == 'n':      # street above: roof faces it, door on the far (south) side
            edge = ay - dist + 1
            y0 = edge + setback
            x0 = ax - width // 2
            garage = None
        elif d == 'e':
            edge = ax + dist - 1
            x0 = edge - setback - width
            y0 = ay - rows // 2
            garage = None
        else:
            edge = ax - dist + 1
            x0 = edge + setback
            y0 = ay - rows // 2
            garage = None
        for shift in (0, 1, -1, 2, -2, 3, -3):
            X0, Y0 = (x0 + shift, y0) if d in 'ns' else (x0, y0 + shift)
            if self.free(X0 - 1, Y0 - 1, width + 2, rows + 2):
                self.draw_house(X0, Y0, width, storeys, roof, wall, garage, d, edge, address)
                return True
        return False

    def free(self, x, y, w=1, h=1):
        if x < 0 or y < 0 or x + w > self.W or y + h > self.H:
            return False
        return not (self.occupied[y:y + h, x:x + w].any() or self.blocked[y:y + h, x:x + w].any())

    def draw_house(self, x, y, width, storeys, roof, wall, garage, d, edge, address):
        import house2
        rows = house2.plan(width, storeys, garage, windows=1 if width < 7 else 2)
        if d == 'n':
            # street is to the north: we see the back of the house, so the south wall
            # gets windows instead of the door; the door is on the hidden north side
            low = rows[-1]
            i = low.index('wall_door')
            if i + 1 < len(low) - 1 and low[i + 1] == 'wall_sid':
                low[i], low[i + 1] = 'wall_win_a', 'wall_win_b'
            elif i - 1 > 0 and low[i - 1] == 'wall_sid':
                low[i - 1], low[i] = 'wall_win_a', 'wall_win_b'
            else:
                low[i] = 'wall_sid'
        gar_cols = []
        door = None
        for r, row in enumerate(rows):
            for c, piece in enumerate(row):
                variant = roof if piece.startswith('roof') else wall
                walk = piece == 'wall_door'
                self.put(x + c, y + r, RES, f'h_{piece}_{variant}', walk)
                if piece == 'wall_gar_a':
                    gar_cols.append(x + c)
                if walk:
                    door = (x + c, y + r)
        self.occupied[y - 1:y + len(rows) + 1, x - 1:x + width + 1] = True
        bottom = y + len(rows) - 1
        self.houses.append({'x': x, 'y': y, 'w': width, 'rows': len(rows), 'd': d, 'edge': edge,
                            'gar': gar_cols, 'garage': garage, 'hs': h32(address),
                            'style': getattr(self, '_hstyle', {}) or {}})
        if d == 's':
            mx = x + width + 1 if garage != 'r' else x - 2
            if gar_cols and edge + 1 < self.H and self.road[edge + 1, gar_cols[0]] and self.road[edge + 1, gar_cols[0] + 1] \
                    and not self.road[edge, gar_cols[0]] and not self.road[edge, gar_cols[0] + 1]:
                gx = gar_cols[0]
                for yy in range(bottom + 1, edge):
                    self.put(gx, yy, RES, 'drive_l', True); self.put(gx + 1, yy, RES, 'drive_r', True)
                    self.occupied[yy, gx:gx + 2] = True
                self.put(gx, edge, RES, 'drive_apron_l', True); self.put(gx + 1, edge, RES, 'drive_apron_r', True)
                mx = gx - 1 if garage == 'l' else gx + 2
                mx = gx + 2 if garage == 'l' else gx - 1
            self.mailbox(mx, edge - 1, address)
        elif d == 'n':
            # front walk from the sidewalk to the stoop at the roof's north edge
            dx = x + width // 2
            for yy in range(edge + 1, y - 1):
                self.put(dx, yy, RES, 'sidewalk', True)
            self.put(dx, y - 1, RES, 'porch_mat', True)
            self.doors.append((dx, y - 1, 'mat', address))
            self.occupied[edge + 1:y, dx] = True
            self.mailbox(dx + 1, edge + 1, address)
        elif d == 'e':
            self.mailbox(edge - 1, bottom - 2, address)     # clear of the side drive
        else:
            self.mailbox(edge + 1, bottom - 2, address)

    def mailbox(self, x, y, address):
        if 0 <= x < self.W and 0 <= y < self.H and (x, y) not in self.obj and not self.blocked[y, x]:
            self.put(x, y, RES, 'mailbox', False)
            self.occupied[y, x] = True
            if not address.startswith('#'):
                self.signs.append((x, y, address))

    def fix_neighbors_east(self, h, n):
        """The owner told us how many houses lie between theirs and the street's east
        end: reserve that frontage and put exactly n evenly spaced houses on it."""
        edge = h['edge']
        x = h['x'] + h['w']
        # stop where this street's name ends (West Autumn Blaze -> Autumn Blaze is another street)
        rid0 = int(self.roadid[edge + 1, h['x'] + h['w'] // 2])
        name0 = self.F['roads'][rid0 - 1]['name'] if rid0 else None
        while x < self.W - 1 and self.road[edge + 1, x] and not self.road[edge, x]:
            rid = int(self.roadid[edge + 1, x])
            if name0 and rid and self.F['roads'][rid - 1]['name'] != name0:
                break
            x += 1
        x0, x1 = h['x'] + h['w'] + 1, x - 1
        top = edge - 12
        self.no_infill.append((x0, top, x1, edge))
        L = min(9, (x1 - x0 + 1) / n)            # ordinary lot width, starting right next door
        for k in range(n):
            ax = int(x0 + L * (k + 0.5))
            hs = h32('nbr', k, h['x'])
            width = 6 + hs % 2
            if not self.place_house(ax, edge - 4, 's', 5, width, 2 if hs % 5 == 0 else 1, hs, f'#{ax},{edge}'):
                self.place_house(ax, edge - 4, 's', 5, 5, 1, hs, f'#{ax},{edge}')

    def pass_infill(self):
        """Houses on empty residential frontage where the address data has gaps.
        Real address points were placed first, so these only take what's left."""
        core = (self.road == R_STREET)
        ok = self.zone & (self.ground == G_LAWN)
        H, W = self.H, self.W
        n = 0
        cand = []
        for y, x in zip(*np.nonzero(core)):
            if x % 3 and y % 3:
                continue
            if y > 6 and not self.road[y - 1, x] and core[y, x]:
                cand.append((x, y - 5, 's', 5))
            if y < H - 6 and not self.road[y + 1, x]:
                cand.append((x, y + 5, 'n', 5))
            if x > 6 and not self.road[y, x - 1]:
                cand.append((x - 5, y, 'e', 5))
            if x < W - 6 and not self.road[y, x + 1]:
                cand.append((x + 5, y, 'w', 5))
        for ax, ay, d, dist in cand:
            if not (0 <= ax < W and 0 <= ay < H) or not ok[ay, ax]:
                continue
            if any(bx0 - 4 <= ax <= bx1 + 4 and by0 <= ay <= by1 + 6 for bx0, by0, bx1, by1 in self.no_infill):
                continue
            hs = h32('infill', ax + self.ox, ay + self.oy)
            if hs % 6 == 0:
                continue                      # leave the odd empty lot
            width = 5 + hs % 3
            storeys = 2 if hs % 7 == 0 else 1
            if self.place_house(ax, ay, d, dist, width, storeys, hs, f'#{ax},{ay}'):
                n += 1
        self.stats['infill'] = n

    # ------------------------------------------------------------ other buildings
    def pass_buildings(self):
        n = 0
        for b in self.F['buildings']:
            if b['id'] in self.used_buildings:
                continue
            xs = [p[0] - self.ox for p in b['poly']]; ys = [p[1] - self.oy for p in b['poly']]
            x0, y0, x1, y1 = int(min(xs)), int(min(ys)), int(math.ceil(max(xs))), int(math.ceil(max(ys)))
            w, h = x1 - x0, y1 - y0
            if w < 3 or h < 2 or x0 < 1 or y0 < 1 or x1 >= self.W - 1 or y1 >= self.H - 1:
                continue
            if not self.zone[min(y1, self.H - 1), min(x1, self.W - 1)]:
                ts = RUR
            else:
                ts = RES
            w = max(4, w); h = max(3, h)
            if self.occupied[y0:y0 + h, x0:x0 + w].any() or self.blocked[y0:y0 + h, x0:x0 + w].any():
                continue
            if ts == RUR:
                for yy in range(max(0, y0 - 2), min(self.H, y0 + h + 3)):
                    for xx in range(max(0, x0 - 2), min(self.W, x0 + w + 2)):
                        if not self.blocked[yy, xx] and (xx, yy) not in self.obj and self.ground[yy, xx] != G_WATER:
                            self.put(xx, yy, RUR, 'gravel' if yy >= y0 + h else 'lawn', True)
            self.flat_building(x0, y0, w, h, ts, h32(b['id']))
            n += 1
        self.stats['buildings'] = n

    def flat_building(self, x, y, w, h, ts, hs):
        """Large footprint from the house kit: roof rows fill the depth, wall row at the bottom."""
        roof = ('charcoal', 'brown', 'red')[hs % 3] if ts == RES else 'green'
        wall = ('white', 'tan')[(hs >> 3) % 2] if ts == RES else 'white'
        sfx = lambda v: f'_{v}' if v else ''
        for r in range(h):
            kind = 'roof0' if r == 0 else ('roof2' if r == h - 2 else ('wall' if r == h - 1 else 'roof1'))
            for c in range(w):
                if kind == 'wall':
                    piece = 'wall_l' if c == 0 else 'wall_r' if c == w - 1 else (
                        'wall_door' if c == w // 2 else ('wall_win_a' if c % 3 == 1 else 'wall_win_b' if c % 3 == 2 else 'wall_sid'))
                    name = f'h_{piece}' + sfx(wall)
                else:
                    piece = f'{kind}_' + ('l' if c == 0 else 'r' if c == w - 1 else 'm')
                    name = f'h_{piece}' + sfx(roof)
                if name.endswith('wall_win_b') or name.endswith('wall_win_b' + sfx(wall)):
                    pass
                self.put(x + c, y + r, ts, name, piece == 'wall_door')
        # fix lone window halves: win_a must be followed by win_b
        for c in range(1, w - 1):
            k = (x + c, y + h - 1)
            ts_, name, wk = self.obj[k]
            if '_win_a' in name and '_win_b' not in self.obj.get((x + c + 1, y + h - 1), (0, ''))[1]:
                self.obj[k] = (ts_, name.replace('_win_a', '_sid'), wk)
            if '_win_b' in name and '_win_a' not in self.obj.get((x + c - 1, y + h - 1), (0, ''))[1]:
                self.obj[k] = (ts_, name.replace('_win_b', '_sid'), wk)
        self.occupied[y - 1:y + h + 1, x - 1:x + w + 1] = True

    # ------------------------------------------------------------ trees
    def pass_trees(self):
        """Trees in groves, not sprinkles: smooth noise picks where groves sit, the
        canopy % (or a per-ground default) picks how much of the land they cover.
        Inside a grove every free 2x2 spot gets a tree, so stands read as solid."""
        free = ~(self.road_ring() | self.rail | self.occupied | (self.ground == G_WATER))
        H, W = self.H, self.W
        nz = 0.9 * vnoise(H, W, self.ox, self.oy, 10, 'grove') + 0.1 * vnoise(H, W, self.ox, self.oy, 3, 'grove2')
        # rank-transform to uniform so "cover fraction f" means f of the land
        u = np.empty(nz.size, np.float32)
        u[np.argsort(nz, axis=None)] = np.linspace(0, 1, nz.size, dtype=np.float32)
        u = u.reshape(H, W)
        g = self.ground
        if self.canopy is not None:
            c = np.where(self.canopy <= 100, self.canopy, 0).astype(np.float32) / 100
        else:
            c = np.zeros((H, W), np.float32)
        base = np.select([g == G_WOOD, g == G_PARK, g == G_CEMETERY, self.zone & (g == G_LAWN),
                          g == G_PRAIRIE, g == G_MEADOW, g == G_LAWN],
                         [1.0, 0.30, 0.35, 0.30, 0.12, 0.08, 0.12], 0.0)
        f = np.where(g == G_WOOD, 1.0, np.maximum(base, np.minimum(1.0, c * 1.4)))
        f[np.isin(g, (G_FIELD, G_WATER, G_PARKING, G_FARMYARD))] = 0
        want = u > 1 - f
        n = 0
        slot = np.zeros((H // 2, W // 2), bool)
        for y in range(0, H - 1, 2):
            for x in range(0, W - 1, 2):
                if want[y, x] and free[y:y + 2, x:x + 2].all() and \
                        not any((x + i, y + j) in self.obj for i in range(2) for j in range(2)):
                    slot[y // 2, x // 2] = True
                    n += 1
        for sy, sx in zip(*np.nonzero(slot)):
            y, x = sy * 2, sx * 2
            ts_ = RES if self.zone[y, x] else RUR
            for (i, j), m in zip(((0, 0), (1, 0), (0, 1), (1, 1)), ('1d4', '1d5', '1e4', '1e5')):
                self.put(x + i, y + j, ts_, 'prim:' + m, False)
        self.stats['trees'] = n

    # ------------------------------------------------------------ final autotile
    def resolve(self):
        """Returns tsgrid (H, W) uint8 and namegrid (H, W) object, walk (H, W) bool."""
        H, W = self.H, self.W
        names = np.empty((H, W), object)
        tsg = np.where(self.zone, RES, RUR).astype(np.uint8)
        walk = np.ones((H, W), bool)
        core = self.road
        pad = np.pad(core, 1)
        N, S, Wn, E = pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]
        NE, NW, SE, SW = pad[:-2, 2:], pad[:-2, :-2], pad[2:, 2:], pad[2:, :-2]
        # ground first
        g = self.ground
        names[:] = 'CROP'
        names[(tsg == RES) | np.isin(g, (G_LAWN, G_PARK, G_CEMETERY, G_MEADOW, G_FARMYARD, G_WOOD, G_PRAIRIE))] = "lawn"
        names[(g == G_PARKING) & (tsg == RES)] = 'asphalt'
        names[(g == G_PARKING) & (tsg == RUR)] = 'gravel'
        names[g == G_WATER] = 'prim:170'
        self._shore(names, g == G_WATER)
        # prairie / pasture grass: short with drifts of tall grass (wild encounters)
        pr = (g == G_PRAIRIE) & (tsg == RUR)
        if pr.any():
            nz = 0.65 * vnoise(H, W, self.ox, self.oy, 14, 'grass') + 0.35 * vnoise(H, W, self.ox, self.oy, 5, 'grass2')
            names[pr & (nz > 0.56)] = 'prim:00d'
        # crops: one crop per field, edges where the field ends
        crop = names == 'CROP'
        ring = self.road_ring()
        ditch = np.zeros_like(ring)
        ditch[1:] |= ring[:-1]; ditch[:-1] |= ring[1:]; ditch[:, 1:] |= ring[:, :-1]; ditch[:, :-1] |= ring[:, 1:]
        crop &= ~(ring | ditch)
        names[(names == 'CROP') & ~crop] = 'lawn'
        fid = self.field_id
        cp = np.pad(crop, 1)
        fp = np.pad(fid, 1)
        ys, xs = np.nonzero(crop)
        for y, x in zip(ys, xs):
            f = fid[y, x]
            c = CROPS[h32(int(f)) % len(CROPS)]
            def same(dy, dx):
                return cp[y + 1 + dy, x + 1 + dx] and fp[y + 1 + dy, x + 1 + dx] == f
            n_, s_, w_, e_ = not same(-1, 0), not same(1, 0), not same(0, -1), not same(0, 1)
            if c in ('wheat', 'corn'):
                tag = ('n' if n_ else 's' if s_ else '') + ('w' if w_ else 'e' if e_ else '')
                names[y, x] = c + ('_' + tag if tag else '')
            elif c == 'soybeans':
                names[y, x] = 'soybeans_n' if n_ else 'soybeans_s' if s_ else 'soybeans'
            else:
                names[y, x] = c
        # road cores
        for y, x in zip(*np.nonzero(core)):
            rc = core[y, x]
            t = tsg[y, x]
            if rc == R_GRAVEL or rc == R_ALLEY or (t == RUR and rc != R_HWY):
                names[y, x] = 'gravel'
                tsg[y, x] = RUR
            elif rc == R_HWY:
                names[y, x] = 'hwy_asphalt'
                tsg[y, x] = RUR
            else:
                names[y, x] = 'asphalt'
                tsg[y, x] = RES
        # 45-degree streets: road cells at the inner step of a diagonal curb
        cb = core > 0
        cpad = np.pad(cb, 1)
        C = lambda y, x, dx, dy: cpad[y + 1 + dy, x + 1 + dx]
        DIAG = {(-1, -1): 'nw', (1, -1): 'ne', (-1, 1): 'sw', (1, 1): 'se'}
        for y, x in zip(*np.nonzero(cb & (tsg == RES))):
            if names[y, x] != 'asphalt':
                continue
            for (sx, sy), k in DIAG.items():
                if not C(y, x, sx, 0) and not C(y, x, 0, sy) and C(y, x, -sx, sy) and C(y, x, sx, -sy):
                    names[y, x] = f'diag45_{k}_3'
                    break
        # parking lots: two rows of stalls, two rows of aisle, inside the curbs
        pk = self.parking & (names == 'asphalt')
        inner = pk.copy()
        inner[1:] &= pk[:-1]; inner[:-1] &= pk[1:]; inner[:, 1:] &= pk[:, :-1]; inner[:, :-1] &= pk[:, 1:]
        for y, x in zip(*np.nonzero(inner)):
            if (y + self.oy) % 4 in (0, 1):
                names[y, x] = 'lot_stalls_n'
                tsg[y, x] = 2
        # centre lines on 3-wide Main Street / highway: middle cell of a straight run
        for y, x in zip(*np.nonzero((core == R_MAIN) | (core == R_HWY))):
            rc = core[y, x]
            if names[y, x] not in ('asphalt', 'hwy_asphalt'):
                continue
            if N[y, x] == rc and S[y, x] == rc and Wn[y, x] != rc and E[y, x] != rc:
                pass
            if Wn[y, x] == rc and E[y, x] == rc and N[y, x] != rc and S[y, x] != rc:
                pass
            if (y > 0 and y < H - 1 and core[y - 1, x] == rc and core[y + 1, x] == rc and
                    (y < 2 or core[y - 2, x] != rc) and (y > H - 3 or core[y + 2, x] != rc)):
                names[y, x] = 'center_yellow_h' if rc == R_MAIN else ('hwy_center_dash_h' if self.oneway[y, x] else 'hwy_center_h')
            elif (x > 0 and x < W - 1 and core[y, x - 1] == rc and core[y, x + 1] == rc and
                  (x < 2 or core[y, x - 2] != rc) and (x > W - 3 or core[y, x + 2] != rc)):
                names[y, x] = 'center_yellow_v' if rc == R_MAIN else ('hwy_center_dash_v' if self.oneway[y, x] else 'hwy_center_v')
        # edge ring
        ry, rx = np.nonzero(ring & (core == 0))
        for y, x in zip(ry, rx):
            n, s, w, e = N[y, x], S[y, x], Wn[y, x], E[y, x]
            cls = max(n, s, w, e, NE[y, x], NW[y, x], SE[y, x], SW[y, x])
            gravelish = cls in (R_GRAVEL, R_ALLEY) or (tsg[y, x] == RUR and cls != R_HWY)
            if cls == R_HWY:
                tsg[y, x] = RUR
                if (n or s) and not (w or e):
                    names[y, x] = 'hwy_edge_s' if n else 'hwy_edge_n'
                elif (w or e) and not (n or s):
                    names[y, x] = 'hwy_edge_e' if w else 'hwy_edge_w'
                else:
                    names[y, x] = 'hwy_asphalt'
            elif gravelish:
                tsg[y, x] = RUR
                if (n and s) or (w and e):
                    names[y, x] = 'gravel'
                elif n and e:
                    names[y, x] = 'gravel_inner_sw'
                elif n and w:
                    names[y, x] = 'gravel_inner_se'
                elif s and e:
                    names[y, x] = 'gravel_inner_nw'
                elif s and w:
                    names[y, x] = 'gravel_inner_ne'
                elif n:
                    names[y, x] = 'gravel_edge_s'
                elif s:
                    names[y, x] = 'gravel_edge_n'
                elif w:
                    names[y, x] = 'gravel_edge_e'
                elif e:
                    names[y, x] = 'gravel_edge_w'
                elif SE[y, x]:
                    names[y, x] = 'gravel_corner_nw'
                elif SW[y, x]:
                    names[y, x] = 'gravel_corner_ne'
                elif NE[y, x]:
                    names[y, x] = 'gravel_corner_sw'
                else:
                    names[y, x] = 'gravel_corner_se'
            else:
                tsg[y, x] = RES
                diag = None
                for (sx, sy), k in DIAG.items():
                    if C(y, x, -sx, 0) and C(y, x, 0, -sy) and not C(y, x, sx, 0) and not C(y, x, 0, sy) \
                            and not C(y, x, -sx, sy) and not C(y, x, sx, -sy):
                        diag = f'diag45_{k}_2'
                    elif C(y, x, -sx, -sy) and not (n or s or w or e) and C(y, x, -sx, -sy):
                        diag = f'diag45_{k}_1'
                if diag:
                    names[y, x] = diag
                elif (n and s) or (w and e) or (n and e and s) or (n and w and s):
                    names[y, x] = 'asphalt'
                elif n and e:
                    names[y, x] = 'block_corner_sw'
                elif n and w:
                    names[y, x] = 'block_corner_se'
                elif s and e:
                    names[y, x] = 'block_corner_nw'
                elif s and w:
                    names[y, x] = 'block_corner_ne'
                elif n:
                    names[y, x] = 'road_edge_s'
                elif s:
                    names[y, x] = 'road_edge_n'
                elif w:
                    names[y, x] = 'road_edge_e'
                elif e:
                    names[y, x] = 'road_edge_w'
                elif SE[y, x] or SW[y, x]:
                    names[y, x] = 'road_edge_n'
                else:
                    names[y, x] = 'road_edge_s'
        self.stamp_bulbs(tsg, names)
        # rail over everything below it
        for y, x in zip(*np.nonzero(self.rail)):
            horiz = (x > 0 and self.rail[y, x - 1]) or (x < W - 1 and self.rail[y, x + 1])
            o = 'h' if horiz else 'v'
            base = names[y, x]
            if core[y, x] or (ring[y, x] and core[y, x] == 0 and base not in ('lawn',) and not str(base).startswith(('wheat', 'corn', 'soy', 'plowed', 'stubble'))):
                names[y, x] = f'rail_x_{"asphalt" if tsg[y, x] == RES or base.startswith("hwy") else "gravel"}_{o}'
            else:
                names[y, x] = f'rail_{o}'
            tsg[y, x] = RUR
        # placed objects on top
        for (x, y), (t, name, wk) in self.obj.items():
            names[y, x] = name
            tsg[y, x] = t
            walk[y, x] = wk
        # tileset fallbacks: residential has no crops etc; rural has no sidewalks
        return tsg, names, walk

    SHORE = {'n': 0x1be, 's': 0x1ae, 'w': 0x1b7, 'e': 0x1b5,
             'nw': 0x1a4, 'ne': 0x1a3, 'sw': 0x19c, 'se': 0x19b,
             'inw': 0x1bf, 'ine': 0x1bd, 'isw': 0x1af, 'ise': 0x1ad}

    def _shore(self, names, wm):
        """Hoenn pond banks on the edge cells of every water body."""
        p = np.pad(wm, 1, constant_values=True)
        N, S, Wd, E = ~p[:-2, 1:-1], ~p[2:, 1:-1], ~p[1:-1, :-2], ~p[1:-1, 2:]
        NW, NE, SW, SE = ~p[:-2, :-2], ~p[:-2, 2:], ~p[2:, :-2], ~p[2:, 2:]
        K = self.SHORE
        def put(mask, key):
            names[wm & mask] = 'prim:%03x' % K[key]
        put(~N & ~S & ~Wd & ~E & SE, "ise")
        put(~N & ~S & ~Wd & ~E & SW, 'isw')
        put(~N & ~S & ~Wd & ~E & NE, 'ine')
        put(~N & ~S & ~Wd & ~E & NW, 'inw')
        put(N & ~S & ~Wd & ~E, 'n'); put(S & ~N & ~Wd & ~E, 's')
        put(Wd & ~E & ~N & ~S, 'w'); put(E & ~Wd & ~N & ~S, 'e')
        put(N & Wd & ~S & ~E, 'nw'); put(N & E & ~S & ~Wd, 'ne')
        put(S & Wd & ~N & ~E, 'sw'); put(S & E & ~N & ~Wd, 'se')

    def run(self):
        self.pass_ground()
        self.pass_roads()
        from geo import civic
        roads = self.road_ring()
        self.blocked = roads | self.rail | (self.ground == G_WATER) | self.reserved
        civic.pass_elevators(self)
        civic.pass_downtown(self)
        civic.pass_civic(self)
        self.pass_houses()
        self.pass_infill()
        from geo import detail
        for h in self.houses:
            detail.driveway(self, h)
            detail.street_car(self, h)
        for h in self.houses:
            detail.backyard(self, h)
            detail.front_tree(self, h)
        self.pass_buildings()
        detail.farmsteads(self)
        self.pass_trees()
        tsg, names, walk = self.resolve()
        detail.furniture(self, tsg, names)
        return tsg, names, walk
