"""Countryside environment: fills open land with things that belong there, so the
county isn't empty between towns. Every choice is hashed on world coordinates.

  terraces       grass contour strips across crop fields (Kansas fields have them)
  ponds          farm stock ponds in pasture and prairie (Hoenn banks via the shore pass)
  shelterbelts   tree rows along some half-mile field lines
  field_life     lone field trees, oil pumpjacks on gravel pads, hay bales on stubble
  pasture_life   cattle, corral pens, flower patches
  flowers        wildflower patches in prairie, terraces and open town lawns"""
import math
import numpy as np
from geo.gen import (RES, RUR, h32, vnoise, G_FIELD, G_MEADOW, G_PRAIRIE, G_WATER, G_LAWN, G_PARK, G_WOOD)

Q = 322                     # half a mile in tiles


def _free(G, x, y, w, h):
    if x < 1 or y < 1 or x + w >= G.W - 1 or y + h >= G.H - 1:
        return False
    if G.road_ring_cache[y:y + h, x:x + w].any() or G.occupied[y:y + h, x:x + w].any():
        return False
    return all((x + i, y + j) not in G.obj for i in range(w) for j in range(h))


def prepare(G):
    G.road_ring_cache = G.road_ring() | G.rail


def terraces(G):
    """Wavy 2-tile grass strips every ~56 tiles across each field; half the fields run
    them east-west, half north-south (contours differ field to field)."""
    H, W = G.H, G.W
    field = (G.ground == G_FIELD) & ~G.zone
    if not field.any():
        return
    ys, xs = np.mgrid[0:H, 0:W]
    nz = vnoise(H, W, G.ox, G.oy, 40, 'terrace') * 18 + vnoise(H, W, G.ox, G.oy, 11, 'terrace2') * 4
    fid = G.field_id
    orient = (np.vectorize(lambda f: h32('ter', int(f)) & 1)(fid) if fid.size < 4_000_000
              else ((fid * 2654435761) >> 7) & 1).astype(bool)
    u = np.where(orient, xs + G.ox, ys + G.oy) + nz
    strip = (np.mod(u, 48) < 3) & field
    G.ground[strip] = G_PRAIRIE               # grass with drifts of tall grass: wild encounters
    G.terrace = strip
    G.stats['terrace_tiles'] = int(strip.sum())


def ponds(G):
    """Stock ponds: one chance per 64x64 cell of pasture / prairie, 4-8 tiles across."""
    H, W = G.H, G.W
    ring = G.road_ring()
    n = 0
    for cy in range((-G.oy) % 64, H - 16, 64):
        for cx in range((-G.ox) % 64, W - 16, 64):
            hs = h32('pond', cx + G.ox, cy + G.oy)
            g = G.ground[cy + 8, cx + 8]
            if g not in (G_MEADOW, G_PRAIRIE) or G.zone[cy + 8, cx + 8] or hs % 100 >= 14:
                continue
            rx, ry = 3 + hs % 4, 2 + (hs >> 3) % 3
            px, py = cx + 8 + (hs >> 6) % 40, cy + 8 + (hs >> 12) % 40
            if px + rx + 3 >= W or py + ry + 3 >= H:
                continue
            box = (slice(py - ry - 2, py + ry + 3), slice(px - rx - 2, px + rx + 3))
            if ring[box].any() or G.zone[box].any() or not np.isin(G.ground[box], (G_MEADOW, G_PRAIRIE)).all():
                continue
            yy, xx = np.mgrid[box]
            wob = 0.85 + 0.3 * ((xx * 7 + yy * 13 + hs) % 5) / 5
            m = ((xx - px) / rx) ** 2 + ((yy - py) / ry) ** 2 <= wob
            G.ground[box][m] = G_WATER
            n += 1
    G.stats['ponds'] = n


def _tree(G, x, y):
    ts = RES if G.zone[y, x] else RUR
    for (i, j), m in zip(((0, 0), (1, 0), (0, 1), (1, 1)), ('1d4', '1d5', '1e4', '1e5')):
        G.put(x + i, y + j, ts, 'prim:' + m, False)
    G.occupied[y:y + 2, x:x + 2] = True


def shelterbelts(G):
    """Rows of trees along a third of the half-mile lines between fields (the
    mile lines carry the section roads)."""
    n = 0
    for k in range((G.ox // Q) * Q + Q, G.ox + G.W, Q):
        if (k // Q) % 2 == 0:
            continue
        x = k - G.ox
        for s0 in range((G.oy // Q) * Q, G.oy + G.H, Q):
            if h32('belt-v', k, s0) % 2:
                continue
            for wy in range(s0 + 6, s0 + Q - 6, 2):
                y = wy - G.oy
                if 0 <= y < G.H - 2 and 1 <= x < G.W - 2 and not G.zone[y, x] and \
                        G.ground[y, x] in (G_FIELD, G_MEADOW, G_PRAIRIE) and _free(G, x, y, 2, 2):
                    _tree(G, x, y); n += 1
    for k in range((G.oy // Q) * Q + Q, G.oy + G.H, Q):
        if (k // Q) % 2 == 0:
            continue
        y = k - G.oy
        for s0 in range((G.ox // Q) * Q, G.ox + G.W, Q):
            if h32('belt-h', k, s0) % 2:
                continue
            for wx in range(s0 + 6, s0 + Q - 6, 2):
                x = wx - G.ox
                if 1 <= y < G.H - 2 and 0 <= x < G.W - 2 and not G.zone[y, x] and \
                        G.ground[y, x] in (G_FIELD, G_MEADOW, G_PRAIRIE) and _free(G, x, y, 2, 2):
                    _tree(G, x, y); n += 1
    G.stats['belt_trees'] = n


def field_life(G):
    """Per 28x28 cell of cropland: a lone tree or two, a pumpjack on a gravel pad, or hay
    bales; and tree clumps along the terrace strips."""
    n = 0
    ter = getattr(G, 'terrace', None)
    if ter is not None:
        ys, xs = np.nonzero(ter[::3, ::3])
        for y, x in zip(ys * 3, xs * 3):
            hs = h32('tclump', x + G.ox, y + G.oy)
            if hs % 23:
                continue
            for k in range(2 + hs % 3):
                tx, ty = x + 2 * k - 2, y - 1 + (h32(hs, k) % 2)
                if _free(G, tx, ty, 2, 2):
                    _tree(G, tx, ty)
            n += 1
    for cy in range((-G.oy) % 28, G.H - 8, 28):
        for cx in range((-G.ox) % 28, G.W - 8, 28):
            hs = h32('field', cx + G.ox, cy + G.oy)
            x, y = cx + 4 + (hs >> 8) % 20, cy + 4 + (hs >> 16) % 20
            if y + 4 >= G.H or x + 4 >= G.W or G.ground[y, x] != G_FIELD or G.zone[y, x]:
                continue
            roll = hs % 100
            if roll < 22 and _free(G, x, y, 2, 2):
                _tree(G, x, y); n += 1
                if roll < 8 and _free(G, x + 2, y, 2, 2):
                    _tree(G, x + 2, y)
            elif roll < 25 and _free(G, x - 1, y - 1, 4, 4):
                for j in range(4):
                    for i in range(4):
                        G.put(x - 1 + i, y - 1 + j, RUR, 'gravel', True)
                for c in range(2):
                    for r in range(2):
                        G.put(x + c, y + r, RUR, f'pumpjack_{c}{r}', False)
                G.occupied[y - 1:y + 3, x - 1:x + 3] = True
                n += 1
            elif roll < 45:
                # hay bales in a loose row (they read on any crop, look best on stubble)
                for k in range(3 + hs % 4):
                    bx = x + k * 3
                    if _free(G, bx, y, 1, 1):
                        G.put(bx, y, RUR, 'hay_bales', False)
                        G.occupied[y, bx] = True
                n += 1
    G.stats['field_features'] = n


def pasture_life(G):
    """Cattle in small herds, the odd corral pen, flower patches."""
    n = 0
    for cy in range((-G.oy) % 36, G.H - 10, 36):
        for cx in range((-G.ox) % 36, G.W - 10, 36):
            hs = h32('pasture', cx + G.ox, cy + G.oy)
            x, y = cx + 3 + (hs >> 8) % 26, cy + 3 + (hs >> 16) % 26
            if y + 8 >= G.H or x + 10 >= G.W or G.zone[y, x] or G.ground[y, x] != G_MEADOW:
                continue
            roll = hs % 100
            if roll < 30:
                for k in range(2 + hs % 4):
                    bx, by = x + (h32(hs, k) % 9), y + (h32(k, hs) % 6)
                    if G.ground[by, bx] == G_MEADOW and _free(G, bx, by, 1, 1):
                        G.put(bx, by, RUR, 'cow_holstein' if h32('c', bx, by) & 1 else 'cow_angus', False)
                        G.occupied[by, bx] = True
                n += 1
            elif roll < 38 and _free(G, x, y, 9, 6) and (G.ground[y:y + 6, x:x + 9] == G_MEADOW).all():
                for i in range(9):
                    G.put(x + i, y, RUR, 'corral_h', False); G.put(x + i, y + 5, RUR, 'corral_h', False)
                for j in range(1, 5):
                    G.put(x, y + j, RUR, 'corral_v', False); G.put(x + 8, y + j, RUR, 'corral_v', False)
                G.put(x + 4, y + 5, RUR, 'lawn', True)                    # the gate gap
                for k in range(2):
                    G.put(x + 2 + 3 * k, y + 2 + k, RUR, 'cow_angus' if k else 'cow_holstein', False)
                G.occupied[y:y + 6, x:x + 9] = True
                n += 1
    G.stats['pasture_features'] = n


def flowers(G):
    """Wildflower patches on prairie, pasture, terraces and open lawns."""
    n = 0
    nz = vnoise(G.H, G.W, G.ox, G.oy, 9, 'flower')
    for cy in range((-G.oy) % 24, G.H - 6, 24):
        for cx in range((-G.ox) % 24, G.W - 6, 24):
            hs = h32('flower', cx + G.ox, cy + G.oy)
            x, y = cx + (hs >> 8) % 18, cy + (hs >> 16) % 18
            g = G.ground[y, x]
            chance = {G_PRAIRIE: 30, G_MEADOW: 22, G_PARK: 30, G_LAWN: 12}.get(g, 0)
            if hs % 100 >= chance:
                continue
            for j in range(4):
                for i in range(5):
                    xx, yy = x + i, y + j
                    if nz[yy, xx] > 0.35 and G.ground[yy, xx] == g and _free(G, xx, yy, 1, 1):
                        G.put(xx, yy, RES if G.zone[yy, xx] else RUR, 'prim:004', True)
            n += 1
    G.stats['flower_patches'] = n
