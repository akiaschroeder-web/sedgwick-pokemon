"""Generate the whole county in regions.

  python3 geo/county.py warps          # detect turned town grids once (warps.pkl)
  python3 geo/county.py run [i j ...]  # generate regions (all if none given)
  python3 geo/county.py stitch         # county overview from the region thumbnails

Each region is REGION tiles square, generated with MARGIN tiles of context on
every side and cropped, so roads, houses and fields line up across seams
(every random choice is hashed on world coordinates)."""
import os, sys, pickle, time, json, glob
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geo import gen, extract, rectify
from geo.boundary import rings, county_ring

REGION, MARGIN = 1536, 96
OUT = '/home/claude/osm_in/county'
THUMB = 8                      # overview: 1 pixel per THUMB x THUMB tiles


def load_raw():
    return pickle.load(open('/home/claude/osm_in/raw.pkl', 'rb'))


def cities(raw):
    n, w, r = raw
    out = []
    for rid, (mem, t) in r.items():
        if t.get('boundary') == 'administrative' and t.get('admin_level') == '8':
            rs = [[extract.proj(lo, la) for lo, la in ring] for ring in rings(r[rid], w, n) if ring and ring[0] == ring[-1]]
            if rs:
                out.append((rid, t.get('name'), rs))
    return out


def find_warps():
    raw = load_raw()
    W = []
    for rid, name, rs in cities(raw):
        xs = [p[0] for q in rs for p in q]; ys = [p[1] for q in rs for p in q]
        bb = (int(min(xs)) - 250, int(min(ys)) - 250, int(max(xs)) + 250, int(max(ys)) + 250)
        F = extract.extract(raw, bb)
        det = rectify.detect(F)
        if det:
            print('turned grid:', name, round(det[0], 2))
            W.append({'city': name, 'ang': det[0], 'poly': det[1]})
    os.makedirs(OUT, exist_ok=True)
    pickle.dump(W, open(f'{OUT}/warps.pkl', 'wb'))


def apply_warps(F, warps, town):
    for wp in warps:
        f = rectify.warp_fn(wp['ang'], wp['poly'])
        xs = [p[0] for p in wp['poly']]; ys = [p[1] for p in wp['poly']]
        x0, y0, x1, y1 = F['bbox']
        if max(xs) + rectify.FADE < x0 or min(xs) - rectify.FADE > x1 or max(ys) + rectify.FADE < y0 or min(ys) - rectify.FADE > y1:
            continue
        F2, _ = rectify.apply_known(F, f)
        town = [[f(p) for p in ring] for ring in town]
    return F, town


def run_region(raw, cty, warps, ring, i, j, land_cache=None):
    from geo import town as T
    x0, y0 = i * REGION, j * REGION
    bb = (x0 - MARGIN, y0 - MARGIN, x0 + REGION + MARGIN, y0 + REGION + MARGIN)
    F = extract.extract(raw, bb)
    F['bbox'] = bb
    T.add_featured(F, bb)
    town = [q for _, _, rs in cty for q in rs
            if max(p[0] for p in q) >= bb[0] and min(p[0] for p in q) <= bb[2]
            and max(p[1] for p in q) >= bb[1] and min(p[1] for p in q) <= bb[3]]
    F, town = apply_warps(F, warps, town)
    land, canopy = T.nlcd_grids(bb)
    G = gen.Gen(F, town, land, canopy)
    tsg, names, walk = G.run()
    # outside the county line: leave it to the neighbouring county (blank)
    from PIL import ImageDraw
    m = Image.new('1', (G.W, G.H), 0)
    ImageDraw.Draw(m).polygon([(x - bb[0], y - bb[1]) for x, y in ring], fill=1)
    inside = np.array(m, bool)
    c = slice(MARGIN, MARGIN + REGION)
    tsg, names, walk, inside = tsg[c, c], names[c, c], walk[c, c], inside[c, c]
    # compact storage: per-tileset name tables
    table = {}
    idx = np.zeros(names.shape, np.uint16)
    for (t, nm) in set(zip(tsg.ravel().tolist(), names.ravel().tolist())):
        table[(t, nm)] = len(table)
    flat = [table[k] for k in zip(tsg.ravel().tolist(), names.ravel().tolist())]
    idx = np.array(flat, np.uint16).reshape(names.shape)
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(f'{OUT}/r_{i:02d}_{j:02d}.npz', idx=idx, walk=walk, inside=inside,
                        table=np.array([f'{t}|{nm}' for (t, nm) in table], object))
    signs = [(x - MARGIN - (i * 0), y - MARGIN, s) for x, y, s in G.signs
             if MARGIN <= x < MARGIN + REGION and MARGIN <= y < MARGIN + REGION]
    json.dump({'signs': signs, 'stats': G.stats}, open(f'{OUT}/r_{i:02d}_{j:02d}.json', 'w'))
    thumb(idx, inside, list(table), f'{OUT}/t_{i:02d}_{j:02d}.png')
    return G.stats


_avg = {}


def thumb(idx, inside, keys, path):
    from geo.tilerender import ts as load_ts
    ids = [json.load(open(f'{gen.TSDIR}/{t}_metatiles.json')) for t in gen.TILESETS]
    cols = np.zeros((len(keys), 3), np.float32)
    for k, (t, nm) in enumerate(keys):
        if (t, nm) not in _avg:
            m = int(nm[5:], 16) if nm.startswith('prim:') else ids[t][nm]
            _avg[(t, nm)] = np.array(load_ts(gen.TILESETS[t]).img(m)).reshape(-1, 3).mean(0)
        cols[k] = _avg[(t, nm)]
    img = cols[idx]
    img[~inside] = (40, 40, 40)
    H, W = idx.shape
    img = img[:H // THUMB * THUMB, :W // THUMB * THUMB].reshape(H // THUMB, THUMB, W // THUMB, THUMB, 3).mean((1, 3))
    Image.fromarray(img.astype(np.uint8)).save(path)


def grid():
    return (extract.WIDTH + REGION - 1) // REGION, (extract.HEIGHT + REGION - 1) // REGION


def run(which):
    raw = load_raw()
    n, w, r = raw
    cty = cities(raw)
    warps = pickle.load(open(f'{OUT}/warps.pkl', 'rb'))
    ring = [extract.proj(*p) for p in county_ring(r[973225], w, n)]
    gx, gy = grid()
    todo = which or [(i, j) for j in range(gy) for i in range(gx)]
    for i, j in todo:
        if os.path.exists(f'{OUT}/r_{i:02d}_{j:02d}.npz') and not which:
            continue
        t = time.time()
        try:
            st = run_region(raw, cty, warps, ring, i, j)
        except Exception:
            import traceback
            print(f'region {i},{j} FAILED', flush=True)
            traceback.print_exc()
            continue
        print(f'region {i},{j} {time.time() - t:.0f}s', st, flush=True)


def stitch():
    gx, gy = grid()
    S = REGION // THUMB
    out = Image.new('RGB', (gx * S, gy * S), (40, 40, 40))
    for p in glob.glob(f'{OUT}/t_*.png'):
        i, j = int(p[-9:-7]), int(p[-6:-4])
        out.paste(Image.open(p), (i * S, j * S))
    out.save(f'{OUT}/county.png')
    print(out.size)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'warps':
        find_warps()
    elif cmd == 'run':
        args = sys.argv[2:]
        run([(int(args[k]), int(args[k + 1])) for k in range(0, len(args), 2)])
    elif cmd == 'stitch':
        stitch()
