"""Generate any town from its OSM boundary relation, with NLCD land cover and
tree canopy when the rasters cover it.
  python3 geo/town.py <relation_id> <name> [crop name,x,y,w,h ...]"""
import glob, pickle, sys, os, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geo import gen, extract, rectify, nlcd
from geo.boundary import rings
from geo.cheney import crop, overview, OUT

NLCD_DIR = '/home/claude/nlcd_in'


def box_mean(a, r):
    a = a.astype(np.float32)
    c = np.pad(a, ((r + 1, r), (r + 1, r)), mode='edge').cumsum(0).cumsum(1)
    s = c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]
    return s / (2 * r + 1) ** 2


GROUPS = [(82,), (71, 52, 95), (81,), (41, 42, 43, 90), (11,), (21,), (22, 23, 24), (31,)]


def mode_filter(land, r):
    """Majority vote over a (2r+1)^2 window per class group: removes 30 m speckle
    (single misclassified cells) while keeping real field and wood shapes."""
    scores = np.stack([box_mean(np.isin(land, g), r) for g in GROUPS])
    best = scores.argmax(0)
    rep = np.array([g[0] for g in GROUPS], land.dtype)
    out = rep[best]
    keep = np.isin(land, (22, 23, 24, 11))         # never smooth away buildings or ponds
    out[keep] = land[keep]
    out[land == 250] = 250
    return out


def nlcd_grids(bb, warp=None):
    lcf = glob.glob(f'{NLCD_DIR}/Annual_NLCD_LndCov_2025*.tiff')
    tcf = glob.glob(f'{NLCD_DIR}/nlcd_tcc_*_2025*.tiff')
    if not lcf:
        return None, None
    x0, y0, x1, y1 = bb
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float64) + 0.5
    # organic edges: wobble the sample point a few tiles so 30 m cells don't show as squares
    wx = 4 * np.sin(ys / 9.0) + 3 * np.sin((xs + ys) / 13.0)
    wy = 4 * np.sin(xs / 11.0) + 3 * np.cos((xs - ys) / 15.0)
    lon, lat = extract.unproj(xs + wx, ys + wy)
    land = mode_filter(nlcd.Raster(lcf[0]).sample(lon, lat), 30)
    canopy = None
    if tcf:
        t = nlcd.Raster(tcf[0]).sample(lon, lat).astype(np.float32)
        bad = t > 100
        t[bad] = 0
        canopy = box_mean(t, 5)
        canopy[bad] = 255
    cover = (land != 250).mean()
    print('NLCD covers %.0f%% of the map' % (cover * 100))
    return (land if cover > 0 else None), (canopy if cover > 0 else None)


def add_featured(F, bb):
    """Hand-placed addresses (featured.json): placed before all others, with a fixed look."""
    import json
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'featured.json')
    for a in json.load(open(path))['addresses']:
        x, y = extract.proj(a['lon'], a['lat'])
        if bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]:
            F['addresses'] = [q for q in F['addresses'] if not (q['num'] == a['num'] and q['street'] == a['street'])]
            F['addresses'].append({'x': x, 'y': y, 'num': a['num'], 'street': a['street'], 'tags': {},
                                   'featured': True, 'style': a.get('style', {})})


def run(rel_id, name, margin=250):
    raw = pickle.load(open('/home/claude/osm_in/raw.pkl', 'rb'))
    n, w, r = raw
    town = [[extract.proj(lo, la) for lo, la in ring] for ring in rings(r[rel_id], w, n)]
    xs = [p[0] for ring in town for p in ring]; ys = [p[1] for ring in town for p in ring]
    bb = (int(min(xs)) - margin, int(min(ys)) - margin, int(max(xs)) + margin, int(max(ys)) + margin)
    F = extract.extract(raw, bb)
    F['bbox'] = bb
    add_featured(F, bb)
    del raw
    F, info = rectify.apply(F, town)
    if info:
        print('straightened grid by %.2f deg' % info[0])
        town = info[2]
    land, canopy = nlcd_grids(bb)
    t = time.time()
    G = gen.Gen(F, town, land, canopy)
    tsg, names, walk = G.run()
    print('generated in %.1fs' % (time.time() - t), G.stats)
    pickle.dump((G.ox, G.oy, tsg, names, walk, G.signs), open(f'/home/claude/osm_in/{name}_cells.pkl', 'wb'))
    overview(G, tsg, names, f'{OUT}/{name}_overview.png')
    return G, tsg, names


if __name__ == '__main__':
    G, tsg, names = run(int(sys.argv[1]), sys.argv[2])
    for spec in sys.argv[3:]:
        nm, x, y, w, h = spec.split(',')
        crop(G, tsg, names, int(x), int(y), int(w), int(h), f'{OUT}/{sys.argv[2]}_{nm}.png')
