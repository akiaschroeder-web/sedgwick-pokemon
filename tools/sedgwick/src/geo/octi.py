"""Snap polylines to 0/45/90 degree legs between integer points (so diagonal
streets rasterise as regular staircases that the 45-degree pieces can follow)."""
import math


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (ax, ay), (bx, by) = pts[0], pts[-1]
    L = math.hypot(bx - ax, by - ay) or 1
    dmax, idx = 0, 0
    for i, (x, y) in enumerate(pts[1:-1], 1):
        d = abs((bx - ax) * (ay - y) - (ax - x) * (by - ay)) / L
        if d > dmax:
            dmax, idx = d, i
    if dmax <= eps:
        return [pts[0], pts[-1]]
    return rdp(pts[:idx + 1], eps)[:-1] + rdp(pts[idx:], eps)


def legs(a, b, axis_tol=0.18):
    """Integer a -> b as axis/diagonal legs. Nearly axis-aligned segments stay one
    straight leg (the small offset is taken by a short diagonal in the middle)."""
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    adx, ady = abs(dx), abs(dy)
    sx, sy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
    d = min(adx, ady)
    if adx >= ady:
        s = adx - d
        h1 = s // 2
        p1 = (ax + sx * h1, ay)
        p2 = (p1[0] + sx * d, p1[1] + sy * d)
    else:
        s = ady - d
        h1 = s // 2
        p1 = (ax, ay + sy * h1)
        p2 = (p1[0] + sx * d, p1[1] + sy * d)
    out = [a, p1, p2, b]
    return [p for i, p in enumerate(out) if i == 0 or p != out[i - 1]]


def snap(pts, eps=1.5, min_diag=3):
    p = [(int(round(x)), int(round(y))) for x, y in rdp(pts, eps)]
    out = [p[0]]
    for i, (a, b) in enumerate(zip(p, p[1:])):
        a = out[-1]
        if a == b:
            continue
        dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
        last = i == len(p) - 2
        if not last and min(dx, dy) < min_diag and max(dx, dy) > 4 * min(dx, dy):
            # small sideways offset on a long run: keep it straight, the next leg absorbs it
            b = (b[0], a[1]) if dx >= dy else (a[0], b[1])
        out += legs(a, b)[1:]
    return out
