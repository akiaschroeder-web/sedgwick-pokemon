"""Straighten towns whose street grid is turned off north (railroad towns).

Gen 3 roads only run on the tile axes, so a grid turned a few degrees would
stair-step. Each tilted town gets a local rotation: full strength inside the
hull of its tilted streets, fading to nothing over FADE tiles outside it, so
the surrounding section-line roads are untouched. Every feature point (roads,
buildings, addresses, areas) goes through the same warp, so houses stay on
their lots."""
import math

FADE = 120


def bearing_mod90(p, q):
    a = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 90
    return a - 90 if a > 45 else a


def detect(F, min_len=20, tol=2.5):
    """Dominant non-zero grid angle among town streets and the points on that grid."""
    votes = {}
    for r in F['roads']:
        if r['cls'] not in ('street', 'service', 'alley'):
            continue
        for p, q in zip(r['pts'], r['pts'][1:]):
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            if L >= min_len:
                a = round(bearing_mod90(p, q) * 2) / 2
                votes[a] = votes.get(a, 0) + L
    tilted = {a: v for a, v in votes.items() if abs(a) >= 3}
    if not tilted:
        return None
    a0 = max(tilted, key=tilted.get)
    ang = sum(a * v for a, v in votes.items() if abs(a - a0) <= tol) / sum(v for a, v in votes.items() if abs(a - a0) <= tol)
    # only a real turned grid: at least 4 degrees, and a big share of all straight street length
    total = sum(votes.values())
    share = sum(v for a, v in votes.items() if abs(a - a0) <= tol) / total
    if abs(ang) < 4 or share < 0.25:
        return None
    pts = []
    for r in F['roads']:
        if r['cls'] not in ('street', 'service', 'alley'):
            continue
        for p, q in zip(r['pts'], r['pts'][1:]):
            if math.hypot(q[0] - p[0], q[1] - p[1]) >= min_len and abs(bearing_mod90(p, q) - ang) <= tol:
                pts += [p, q]
    return ang, hull(pts)


def hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def dist_outside(p, poly):
    """0 inside the convex polygon, else distance to it."""
    x, y = p
    inside = True
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]) < 0:
            inside = False
            break
    if inside:
        return 0.0
    best = 1e18
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def warp_fn(ang, poly, fade=FADE):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)

    def f(p):
        d = dist_outside(p, poly)
        if d >= fade:
            return p
        w = 1 - d / fade
        w = w * w * (3 - 2 * w)                    # smoothstep
        a = math.radians(-ang * w)
        dx, dy = p[0] - cx, p[1] - cy
        return (cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a))
    return f


def pinned(r, min_len=80, tol=2.0, dev=4.0):
    """Long straight section-line roads stay exactly where they are: chord within
    `tol` degrees of an axis and no point more than `dev` tiles off the chord."""
    p = r['pts']
    (ax, ay), (bx, by) = p[0], p[-1]
    L = math.hypot(bx - ax, by - ay)
    if L < min_len or abs(bearing_mod90(p[0], p[-1])) > tol:
        return False
    return all(abs((bx - ax) * (y - ay) - (by - ay) * (x - ax)) / L <= dev for x, y in p)


def axis_line(r):
    xs = [q[0] for q in r['pts']]; ys = [q[1] for q in r['pts']]
    if max(xs) - min(xs) < max(ys) - min(ys):
        return ('x', sum(xs) / len(xs), min(ys), max(ys))
    return ('y', sum(ys) / len(ys), min(xs), max(xs))


def apply(F, extra_rings=()):
    det = detect(F)
    if not det:
        return F, None
    ang, poly = det
    f = warp_fn(ang, poly)
    pins = [axis_line(r) for r in F['roads'] if pinned(r)]
    print('pinned roads', len(pins))
    for r in F['roads']:
        if pinned(r):
            continue
        orig = list(r['pts'])
        r['pts'] = [f(p) for p in r['pts']]
        # street ends that met a pinned road are re-attached to it along the street
        for end, nxt in ((0, 1), (-1, -2)):
            if len(orig) < 2:
                break
            ox, oy = orig[end]
            for ax, c, lo, hi in pins:
                on = (abs(ox - c) <= 3 and lo - 3 <= oy <= hi + 3) if ax == 'x' else (abs(oy - c) <= 3 and lo - 3 <= ox <= hi + 3)
                if not on:
                    continue
                (x1, y1), (x0, y0) = r['pts'][nxt], r['pts'][end]
                if ax == 'x' and x0 != x1:
                    t = (c - x1) / (x0 - x1)
                    r['pts'][end] = (c, y1 + (y0 - y1) * t)
                elif ax == 'y' and y0 != y1:
                    t = (c - y1) / (y0 - y1)
                    r['pts'][end] = (x1 + (x0 - x1) * t, c)
                break
    for r in F['rail']:
        r['pts'] = [f(p) for p in r['pts']]
    for b in F['buildings'] + F['areas']:
        b['poly'] = [f(p) for p in b['poly']]
        if b.get('holes'):
            b['holes'] = [[f(p) for p in h] for h in b['holes']]
    for a in F['addresses'] + F['pois'] + F.get('turns', []):
        a['x'], a['y'] = f((a['x'], a['y']))
    rings = [[f(p) for p in r] for r in extra_rings]
    return F, (ang, poly, rings)
