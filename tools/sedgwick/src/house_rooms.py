"""Simple one-room house interiors: ~100 reusable layouts built from Hoenn's own house
furniture, and the table that assigns one to every house on the county map.

How the rooms are made
  1. harvest(): every vanilla Hoenn house that uses gTileset_Building + gTileset_GenericBuilding
     is split into a background (back wall rows, the shadow row under the wall, the floor,
     the left-edge floor strip) and the furniture on top of it. Each 8-connected group of
     non-background cells becomes a "stamp" that keeps its exact metatiles and collision:
     wall stamps (TV cabinets, bookshelves, sink + fridge, windows, potted plants against the
     wall) and floor stamps (tables with chairs, rugs, beds, plants, vases, cushions).
  2. room(seed): picks a theme (floor/wall style), a size, and furniture, places wall stamps
     along the back wall and floor stamps on the floor without touching each other, keeps a
     clear aisle from the door mat, and checks with a flood fill that every free floor tile
     can still be reached from the door.
  3. write_all(): writes SedgwickHouse001..100 as indoor maps whose door mats warp back to
     whichever house the player came in by (MAP_DYNAMIC), like the other Sedgwick interiors.

Assignment: interior_for(key) picks one of the layouts for a house from a hash of its address
(or its door tile when it has none), so the same house always gets the same room and
neighbours rarely match."""
import json, os, random, struct, sys, zlib
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import EXP
from interiors import Room, exits

N_LAYOUTS = 100
COLL = 0x0C00
MAT = (0x208, 0x209)
SKIP = ('TRICK', 'FAN_CLUB', 'TOWN_HALL', 'GAME_CORNER', 'DECORATION_SHOP', 'WANDAS')


def _warp_cells():
    """layout id -> set of (x, y) warp tiles (stairs, ladders) from the maps that use it."""
    out = {}
    root = f'{EXP}/data/maps'
    for d in os.listdir(root):
        f = f'{root}/{d}/map.json'
        if os.path.exists(f):
            mj = json.load(open(f))
            out.setdefault(mj.get('layout'), set()).update((w['x'], w['y']) for w in mj.get('warp_events', []))
    return out


PAIRS = (('gTileset_Building', 'gTileset_GenericBuilding'), ('gTileset_BuildingFrlg', 'gTileset_GenericBuilding2'))
SKIP += ('ENTRANCE', 'UNDERGROUND', 'SEDGWICK')


def _sources():
    L = json.load(open(f'{EXP}/data/layouts/layouts.json'))['layouts']
    return [l['id'] for l in L if (l.get('primary_tileset'), l.get('secondary_tileset')) in PAIRS
            and not any(k in l['id'] for k in SKIP) and l['width'] <= 14 and l['height'] <= 10]


def _mode(vals):
    return Counter(vals).most_common(1)[0][0] if vals else None


def harvest():
    """{theme: {'bg': (...), 'wall': [stamps], 'floor': [stamps]}}; a stamp is
    {'w','h','cells': {(dx, dy): raw u16}, 'y': top row (wall stamps)}."""
    themes = {}
    warps = _warp_cells()
    for lid in _sources():
        r = Room(lid)
        bad = {(x, y) for x, y in warps.get(lid, ()) if y < r.h - 1}
        mats = sorted((x, y) for x, y in warps.get(lid, ()) if y == r.h - 1)
        if not mats:
            continue
        g, W, H = r.g, r.w, r.h
        m = lambda v: v & 0x3FF
        wall0 = _mode([m(v) for v in g[0]])
        wall1 = _mode([m(v) for v in g[1]])
        shadow = _mode([m(v) for v in g[2]])
        floor = _mode([m(v) for row in g[3:] for v in row])
        edge = _mode([m(row[0]) for row in g[3:]])
        if edge == floor:
            edge = None
        key = (wall0, floor)
        th = themes.setdefault(key, {'template': lid, 'mat': [r.g[y][x] for x, y in mats], 'bg': {'wall0': g[0][[m(v) for v in g[0]].index(wall0)],
                                            'wall1': g[1][[m(v) for v in g[1]].index(wall1)],
                                            'shadow': g[2][[m(v) for v in g[2]].index(shadow)],
                                            'floor': next(v for row in g[3:] for v in row if m(v) == floor),
                                            'edge': next((row[0] for row in g[3:] if m(row[0]) == edge), None)},
                                     'wall': [], 'floor': [], 'sources': []})
        th['sources'].append(lid)

        def is_bg(x, y):
            v = m(g[y][x])
            if y == 0:
                return v == wall0
            if y == 1:
                return v == wall1
            if y == 2:
                return v == shadow
            if (x, y) in mats:
                return True
            return v == floor or (x == 0 and v == edge)
        obj = {(x, y) for y in range(H) for x in range(W) if not is_bg(x, y)}
        seen = set()
        for c in sorted(obj):
            if c in seen:
                continue
            comp, stack = [], [c]
            seen.add(c)
            while stack:
                x, y = stack.pop()
                comp.append((x, y))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        n = (x + dx, y + dy)
                        if n in obj and n not in seen:
                            seen.add(n); stack.append(n)
            xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
            w, h = x1 - x0 + 1, y1 - y0 + 1
            if w > 8 or h > 6 or (w * h > 30) or any(c in bad for c in comp):
                continue                                  # set pieces too big to reuse, stairs
            st = {'w': w, 'h': h, 'cells': {(x - x0, y - y0): g[y][x] for x, y in comp}, 'src': lid,
                  'side': 'l' if x0 == 0 else ('r' if x1 == W - 1 else None)}
            if y0 <= 2:
                if y1 > 3:
                    continue                              # wall-to-floor oddities (stairs, counters)
                st['y'] = y0
                th['wall'].append(st)
            elif y1 < H - 1 or w <= 2:
                th['floor'].append(st)
    for th in themes.values():
        for k in ('wall', 'floor'):
            uniq, sig = [], set()
            for st in th[k]:
                s = (st['w'], st['h'], st.get('y'), tuple(sorted(st['cells'].items())))
                if s not in sig:
                    sig.add(s); uniq.append(st)
            th[k] = uniq
    return themes


def _rugs(themes):
    """Rugs of any size from the 9-slice of LAYOUT_HOUSE1's rug, some with its table and
    chairs on top: added to the wood-floor theme's floor pieces."""
    r = Room('LAYOUT_HOUSE1')
    g = r.g
    sl = {'tl': g[3][1], 't': g[3][2], 'tr': g[3][7], 'l': g[4][1], 'c': g[4][5], 'r': g[4][7],
          'bl': g[6][1], 'b': g[6][2], 'br': g[6][7]}
    table = [[g[4][2], g[4][3], g[4][4]], [g[5][2], g[5][3], g[5][4]]]
    key = next((k for k in themes if themes[k]['template'] == 'LAYOUT_HOUSE1'), None)
    if key is None:
        return
    for w in (4, 5, 6, 7):
        for h in (3, 4, 5):
            for with_table in (False, True):
                if with_table and (w < 5 or h < 4):
                    continue
                cells = {}
                for y in range(h):
                    for x in range(w):
                        k = ('t' if y == 0 else 'b' if y == h - 1 else '') + ('l' if x == 0 else 'r' if x == w - 1 else '')
                        k = {'t': 't', 'b': 'b', 'l': 'l', 'r': 'r', '': 'c', 'tl': 'tl', 'tr': 'tr', 'bl': 'bl', 'br': 'br'}[k]
                        cells[(x, y)] = sl[k]
                if with_table:
                    ox, oy = (w - 3) // 2, (h - 2) // 2
                    for dy in range(2):
                        for dx in range(3):
                            cells[(ox + dx, oy + dy)] = table[dy][dx]
                themes[key]['floor'].append({'w': w, 'h': h, 'cells': cells, 'src': 'rug', 'side': None})


def _themes():
    T = harvest()
    _rugs(T)
    # keep themes with enough furniture to vary
    return {k: v for k, v in T.items() if len(v['wall']) >= 2 and len(v['floor']) >= 1}


def room(seed, themes, keys):
    rnd = random.Random(seed)
    key = keys[seed % len(keys)] if seed < len(keys) else rnd.choice(keys)
    th = themes[key]
    bg = th['bg']
    W = rnd.randint(8, 12)
    H = rnd.randint(7, 9)
    g = [[bg['wall0']] * W, [bg['wall1']] * W, [bg['shadow']] * W] + \
        [[bg['floor']] * W for _ in range(H - 3)]
    if bg['edge'] is not None and rnd.random() < 0.6:
        for y in range(3, H):
            g[y][0] = bg['edge']
    mw = len(th['mat'])
    mat_x = (W - mw) // 2 if rnd.random() < 0.7 else rnd.choice((1, W - mw - 1))
    for k, v in enumerate(th['mat']):
        g[H - 1][mat_x + k] = v
    used = [[False] * W for _ in range(H)]
    # keep an aisle from the mat into the room
    for y in range(H - 3, H):
        for k in range(mw):
            used[y][mat_x + k] = True
    def fits(st, x, y, pad=1):
        if x < 0 or y < 0 or x + st['w'] > W or y + st['h'] > H - 1:
            return False
        for (dx, dy) in st['cells']:
            for ex in range(-pad, pad + 1):
                for ey in range(-pad, pad + 1):
                    X, Y = x + dx + ex, y + dy + ey
                    if 0 <= X < W and 0 <= Y < H and used[Y][X] and not (pad and (ex or ey) and Y <= 2):
                        return False
        return True
    def put(st, x, y):
        for (dx, dy), v in st['cells'].items():
            g[y + dy][x + dx] = v
            used[y + dy][x + dx] = True
    # back wall: 2-5 pieces
    walls = th['wall'][:]
    rnd.shuffle(walls)
    n_wall = rnd.randint(3, 6)
    placed = 0
    for st in walls:
        if placed >= n_wall:
            break
        if st['side'] == 'l':
            xs = [0]
        elif st['side'] == 'r':
            xs = [W - st['w']]
        else:
            xs = list(range(0, W - st['w'] + 1))
            rnd.shuffle(xs)
        for x in xs:
            if all(not used[st['y'] + dy][x + dx] for (dx, dy) in st['cells']) and \
                    all(not used[y][x + dx] for (dx, dy) in st['cells'] for y in range(3)):
                put(st, x, st['y'])
                placed += 1
                break
    # floor: 1-4 pieces, roomier rooms get more
    floors = th['floor'][:]
    rnd.shuffle(floors)
    floors.sort(key=lambda st: -(st['w'] * st['h']) * rnd.uniform(0.5, 1.5))   # big pieces first
    n_floor = rnd.randint(2, 3 + (W * H) // 30)
    placed_f = small = 0
    rug = False
    for st in floors + [f for f in floors if f['w'] * f['h'] <= 2]:
        if placed_f >= n_floor:
            break
        if st['src'] == 'rug':
            if rug:
                continue
        if st['w'] * st['h'] <= 2:
            if small >= 2:
                continue
        cand = [(x, y) for y in range(3, H - 1) for x in range(W) if fits(st, x, y)]
        if not cand:
            continue
        x, y = rnd.choice(cand)
        snapshot = [row[:] for row in g], [row[:] for row in used]
        put(st, x, y)
        if not _reachable(g, W, H, mat_x):
            g[:], used[:] = snapshot
            continue
        placed_f += 1
        rug |= st['src'] == 'rug'
        small += st['w'] * st['h'] <= 2
    return {'theme': key, 'w': W, 'h': H, 'g': g, 'mat': mat_x, 'mw': mw, 'src': th['sources'], 'template': th['template']}


def _reachable(g, W, H, mat_x):
    free = lambda x, y: not (g[y][x] & COLL)
    start = (mat_x, H - 1)
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < W and 2 < ny < H and (nx, ny) not in seen and free(nx, ny):
                seen.add((nx, ny)); stack.append((nx, ny))
    total = {(x, y) for y in range(3, H) for x in range(W) if free(x, y)}
    return total <= seen


def build_all(n=N_LAYOUTS):
    themes = _themes()
    keys = sorted(themes, key=lambda k: -len(themes[k]['sources']))
    # weight the common Hoenn wood-floor look, but give every theme a share
    order = []
    for i in range(n):
        order.append(keys[0] if i % 3 else keys[(i // 3) % len(keys)])
    out, sigs = [], set()
    seed = 0
    while len(out) < n and seed < n * 20:
        th_key = order[len(out)]
        r = room(seed * 7919 + len(out), {th_key: themes[th_key]}, [th_key])
        sig = tuple(tuple(row) for row in r['g'])
        seed += 1
        if sig in sigs:
            continue
        sigs.add(sig)
        out.append(r)
    return out, themes


def write_all():
    rooms, themes = build_all()
    meta = []
    for i, r in enumerate(rooms, 1):
        name = f'SedgwickHouse{i:03d}'
        template = Room(r['template'])
        template.g = [row[:] for row in r['g']]
        template.w, template.h = r['w'], r['h']
        template.warps = []
        template.bg = []
        exits(template, tuple(r['mat'] + k for k in range(r['mw'])), r['h'] - 1)
        template.write(name, 'House')
        meta.append({'map': f'MAP_SEDGWICK_HOUSE{i:03d}', 'name': name, 'w': r['w'], 'h': r['h']})
    json.dump(meta, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'house_rooms.json'), 'w'), indent=1)
    return rooms


def interior_for(key):
    """1..N_LAYOUTS for a house key (its address, or 'x,y' of its door)."""
    return zlib.crc32(key.encode()) % N_LAYOUTS + 1


if __name__ == '__main__':
    if sys.argv[1:] == ['harvest']:
        T = harvest()
        for k, v in sorted(T.items(), key=lambda kv: -len(kv[1]['sources'])):
            print([hex(x) for x in k], len(v['sources']), 'wall', len(v['wall']), 'floor', len(v['floor']), v['sources'][:4])
    else:
        rooms = write_all()
        print(len(rooms), 'rooms written')
