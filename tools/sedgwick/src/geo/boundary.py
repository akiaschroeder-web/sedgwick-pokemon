"""Assemble boundary relations into rings and point-in-polygon test."""

def rings(rel, ways, nodes, role='outer'):
    segs = [ways[m][0] for t, m, r in rel[0] if t == 'w' and r in (role, '') and m in ways]
    segs = [s for s in segs if all(n in nodes for n in s)]
    out = []
    while segs:
        ring = list(segs.pop())
        while ring[0] != ring[-1]:
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]
                elif s[-1] == ring[-1]:
                    ring += s[::-1][1:]
                elif s[-1] == ring[0]:
                    ring = s[:-1] + ring
                elif s[0] == ring[0]:
                    ring = s[::-1][:-1] + ring
                else:
                    continue
                segs.pop(i)
                break
            else:
                break   # open ring (clipped by extract)
        out.append([(nodes[n][1], nodes[n][0]) for n in ring])   # (lon, lat)
    return out


def inside(pt, polys):
    x, y = pt
    c = False
    for ring in polys:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
    return c


def county_ring(rel, ways, nodes):
    """Outer ring tolerant of member ways missing from the extract: pieces are chained
    by nearest endpoint and the gaps bridged with straight lines (county lines here
    run along survey section lines, so a straight bridge is accurate)."""
    pieces = [[(nodes[x][1], nodes[x][0]) for x in ways[m][0]]
              for t, m, r in rel[0] if t == 'w' and r == 'outer' and m in ways]
    ring = pieces.pop(0)
    d = lambda a, b: (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
    while pieces:
        best = min([(d(ring[-1], p[0]), i, False) for i, p in enumerate(pieces)] +
                   [(d(ring[-1], p[-1]), i, True) for i, p in enumerate(pieces)])
        p = pieces.pop(best[1])
        ring += p[::-1] if best[2] else p
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring
