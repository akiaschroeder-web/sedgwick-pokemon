"""Gym sites (gyms.json) built into the map before houses take the space."""
import json, os, math
import numpy as np
from geo import extract
from geo.gen import RES, RUR, h32, G_WATER, G_LAWN, G_PARK, G_FIELD, G_WOOD, G_MEADOW, G_PRAIRIE

LM, AV, DT = 5, 6, 3          # landmarks, aviation, downtown tileset indices
HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    return json.load(open(os.path.join(HERE, '..', '..', 'gyms.json')))['gyms']


def _poly(G, way_id):
    for coll in (G.F['areas'], G.F['buildings']):
        for a in coll:
            if a['id'] == way_id:
                return G.local(a['poly'])
    return None


def _clear(G, x, y, w, h):
    return 0 < x and 0 < y and x + w < G.W and y + h < G.H and not G.blocked[y:y + h, x:x + w].any() \
        and not G.occupied[y:y + h, x:x + w].any() and all((x + i, y + j) not in G.obj for i in range(w) for j in range(h))


def _near(G, cx, cy, w, h, r=40):
    best = None
    for dy in range(-r, r + 1, 1):
        for dx in range(-r, r + 1, 1):
            x, y = cx - w // 2 + dx, cy - h // 2 + dy
            if (best is None or dx * dx + dy * dy < best[0]) and _clear(G, x - 1, y - 1, w + 2, h + 2):
                best = (dx * dx + dy * dy, x, y)
    return best and best[1:]


def _stamp(G, plan, x, y, ts, door_names=()):
    for r, row in enumerate(plan):
        for c, nm in enumerate(row):
            if nm:
                G.put(x + c, y + r, ts, nm, nm in door_names)
    G.occupied[y - 1:y + len(plan) + 1, x - 1:x + len(plan[0]) + 1] = True


def _walk_to_street(G, x, y):
    """Concrete walk from a door south (or north) to the nearest street edge."""
    for dy in (1, -1):
        cells = []
        yy = y + dy
        while 0 < yy < G.H - 1 and len(cells) < 30:
            if G.road[yy, x]:
                break
            cells.append(yy)
            yy += dy
        if 0 < yy < G.H - 1 and G.road[yy, x] and len(cells) < 30:
            for c in cells:
                if (x, c) not in G.obj:
                    G.put(x, c, RES, 'sidewalk', True)
            G.occupied[min(cells + [y]):max(cells + [y]) + 1, x] = True
            return


def _gym(G, x, y, record, name):
    import landmarks
    plan = landmarks.plan('gym')
    door = 'lm_gym_34'
    _stamp(G, plan, x, y, LM, {door})
    G.gyms.append({'id': record['id'], 'name': name, 'door': (x + 3, y + 4)})
    _walk_to_street(G, x + 3, y + 4)


def build(G):
    import landmarks, downtown
    G.gyms = []
    for g in load():
        x, y = extract.proj(g['lon'], g['lat'])
        x, y = int(x - G.ox), int(y - G.oy)
        if not (0 <= x < G.W and 0 <= y < G.H):
            continue
        k = g['kind']
        poly = _poly(G, g.get('osm_way')) if g.get('osm_way') else None
        if poly:
            xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
            bx0, by0, bx1, by1 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
        else:
            bx0, by0, bx1, by1 = x - 20, y - 15, x + 20, y + 15
        if k in ('park_gym', 'farm_gym'):
            if k == 'farm_gym':
                # gravel yard in the fields, a drive out to the nearest road
                for yy in range(y - 6, y + 8):
                    for xx in range(x - 8, x + 9):
                        if 0 < xx < G.W and 0 < yy < G.H and not G.blocked[yy, xx]:
                            G.ground[yy, xx] = G_MEADOW
                            G.put(xx, yy, RUR, 'gravel' if yy >= y + 2 else 'lawn', True)
                G.occupied[y - 6:y + 8, x - 8:x + 9] = False
            s = _near(G, x, y, 7, 5)
            if s:
                _gym(G, s[0], s[1], g, g['name'])
        elif k == 'zoo':
            # pens across the park on a path grid, the Gym as the gate building at the south edge;
            # the whole park is kept free of houses
            cx = (bx0 + bx1) // 2
            if poly:
                G.blocked |= G.poly_mask([poly])
            s = _near(G, cx, by1 - 3, 7, 5, r=30)
            if s:
                _gym(G, s[0], s[1], g, g['name'])
            n = 0
            for py in range(by0 + 4, by1 - 12, 9):
                for px in range(bx0 + 4, bx1 - 8, 10):
                    nm = 'pen_pool' if h32('pen', px, py) & 1 else 'pen_sand'
                    if _clear(G, px - 1, py - 1, 9, 7):
                        _stamp(G, landmarks.plan(nm), px, py, LM)
                        for xx in range(px - 1, px + 8):
                            if (xx, py + 5) not in G.obj:
                                G.put(xx, py + 5, RES, 'sidewalk', True)
                        n += 1
            G.stats['zoo_pens'] = n
        elif k == 'waterpark':
            cx = (bx0 + bx1) // 2
            for yy in range(by0, by1 + 1):
                for xx in range(bx0, bx1 + 1):
                    if 0 < xx < G.W and 0 < yy < G.H and not G.blocked[yy, xx] and (xx, yy) not in G.obj:
                        G.put(xx, yy, RES, 'sidewalk', True)
            for k2 in range(5):
                hs = h32('pool', k2, g['id'])
                pw, ph = 6 + hs % 6, 4 + (hs >> 4) % 4
                px = bx0 + 3 + (hs >> 8) % max(1, bx1 - bx0 - pw - 6)
                py = by0 + 3 + (hs >> 16) % max(1, by1 - by0 - ph - 12)
                for yy in range(py, py + ph):
                    for xx in range(px, px + pw):
                        if 0 < xx < G.W and 0 < yy < G.H and not G.blocked[yy, xx]:
                            G.put(xx, yy, RES, 'prim:170', False)
            G.occupied[by0:by1 + 1, bx0:bx1 + 1] = True
            G.occupied[by1 - 5:by1 + 1, cx - 4:cx + 5] = False
            for yy in range(by1 - 5, by1 + 1):
                for xx in range(cx - 4, cx + 5):
                    G.obj.pop((xx, yy), None)
            s = _near(G, cx, by1 - 2, 7, 5, r=12)
            if s:
                _gym(G, s[0], s[1], g, g['name'])
        elif k == 'museum':
            mp = landmarks.plan('museum')
            w, h = len(mp[0]), len(mp)
            mx = (bx0 + bx1) // 2 - w // 2
            my = by1 - h + 1
            for yy in range(my - 6, my + h):
                for xx in range(mx, mx + w):
                    G.obj.pop((xx, yy), None)
            G.occupied[my - 7:my + h + 1, mx - 1:mx + w + 1] = False
            _stamp(G, mp, mx, my, LM, {'lm_museum_55'})
            # the control tower rising out of the middle of the terminal
            for r in range(5):
                for c in range(2):
                    G.put(mx + w // 2 - 1 + c, my - 5 + r + 1, AV, f'tower_{c}{r}', False)
            G.occupied[my - 6:my + h + 1, mx - 1:mx + w + 1] = True
            G.gyms.append({'id': g['id'], 'name': g['name'], 'door': (mx + 5, my + 5)})
            ramp = _poly(G, g.get('ramp_way'))
            if ramp:
                rx = [p[0] for p in ramp]; ry = [p[1] for p in ramp]
                rx0, ry0, rx1, ry1 = int(min(rx)), int(min(ry)), int(max(rx)), int(max(ry))
                for yy in range(ry0, ry1 + 1):
                    for xx in range(rx0, rx1 + 1):
                        if 0 < xx < G.W and 0 < yy < G.H and (xx, yy) not in G.obj and not G.blocked[yy, xx]:
                            G.put(xx, yy, AV, 'apron', True)
                planes = 0
                for yy in range(ry0 + 2, ry1 - 3, 9):
                    for xx in range(rx0 + 2, rx1 - 4, 11):
                        if planes >= 12:
                            break
                        big = h32('plane', xx, yy) % 3 == 0
                        pw, ph = (4, 3) if big else (2, 2)
                        if all(G.obj.get((xx + i, yy + j), (0, ''))[1] == 'apron' for i in range(pw) for j in range(ph)):
                            for i in range(pw):
                                for j in range(ph):
                                    G.put(xx + i, yy + j, AV, f'{"jet" if big else "cessna"}_{i}{j}', False)
                            planes += 1
                G.occupied[ry0:ry1 + 1, rx0:rx1 + 1] = True
                G.stats['museum_planes'] = planes
        elif k == 'arena':
            A = downtown.ARENA
            w, h = len(A[0]), len(A)
            ax = (bx0 + bx1) // 2 - w // 2
            ay = (by0 + by1) // 2 - h // 2
            for yy in range(ay - 3, ay + h + 3):
                for xx in range(ax - 3, ax + w + 3):
                    G.obj.pop((xx, yy), None)
                    if 0 < xx < G.W and 0 < yy < G.H and not G.blocked[yy, xx]:
                        G.put(xx, yy, RES, 'sidewalk', True)
            G.occupied[ay - 4:ay + h + 4, ax - 4:ax + w + 4] = False
            plan = [[(f'bf_{m:03x}' if m else None) for m in row] for row in A]
            _stamp(G, plan, ax, ay, DT, {f'bf_{m:03x}' for m in downtown.ARENA_DOORS})
            G.occupied[ay - 4:ay + h + 4, ax - 4:ax + w + 4] = True
            G.gyms.append({'id': g['id'], 'name': g['name'], 'door': None})
        elif k == 'safari_gate':
            sp = landmarks.plan('safari')
            s = _near(G, max(8, x + 4), y - 7, 6, 6, r=20)
            if s:
                _stamp(G, sp, s[0], s[1], LM, {'lm_safari_25'})
                G.gyms.append({'id': g['id'], 'name': g['name'], 'door': (s[0] + 2, s[1] + 5)})
                _walk_to_street(G, s[0] + 2, s[1] + 5)
    G.stats['gyms'] = len(G.gyms)
