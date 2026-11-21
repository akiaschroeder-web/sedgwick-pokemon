"""Pilot: generate Cheney and render previews."""
import pickle, sys, os, time, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geo import gen, extract
from geo.boundary import rings
from geo.tilerender import ts as load_ts

OUT = '/tmp/claude-0/-home-claude/ad9970a3-1954-519d-ae87-8426714996c9/scratchpad'


def main():
    F = pickle.load(open('/home/claude/osm_in/cheney.pkl', 'rb'))
    raw = pickle.load(open('/home/claude/osm_in/raw.pkl', 'rb'))
    n, w, r = raw
    town = [[extract.proj(lo, la) for lo, la in ring] for ring in rings(r[129818], w, n)]
    del raw
    from geo import rectify
    F, info = rectify.apply(F, town)
    if info:
        print('straightened grid by %.2f deg' % info[0])
        town = info[2]
    t = time.time()
    G = gen.Gen(F, town)
    tsg, names, walk = G.run()
    print('generated in %.1fs' % (time.time() - t), G.stats)
    pickle.dump((G.ox, G.oy, tsg, names, walk, G.signs), open('/home/claude/osm_in/cheney_cells.pkl', 'wb'))
    return G, tsg, names


def metatile_id(G, t, name):
    if name.startswith('prim:'):
        return int(name[5:], 16)
    return G.ids[t][name]


def overview(G, tsg, names, path, scale=1):
    H, W = names.shape
    tsn = gen.TILESETS
    avg = {}
    img = np.zeros((H, W, 3), np.uint8)
    for y in range(H):
        for x in range(W):
            k = (tsg[y, x], names[y, x])
            if k not in avg:
                im = load_ts(tsn[k[0]]).img(metatile_id(G, *k))
                avg[k] = np.array(im).reshape(-1, 3).mean(0).astype(np.uint8)
            img[y, x] = avg[k]
    Image.fromarray(img).resize((W * scale, H * scale), Image.NEAREST).save(path)


def crop(G, tsg, names, x0, y0, w, h, path, scale=1):
    im = Image.new('RGB', (w * 16, h * 16))
    for y in range(h):
        for x in range(w):
            k = (tsg[y0 + y, x0 + x], names[y0 + y, x0 + x])
            im.paste(load_ts(gen.TILESETS[k[0]]).img(metatile_id(G, *k)), (x * 16, y * 16))
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(path)


if __name__ == '__main__':
    G, tsg, names = main()
    overview(G, tsg, names, f'{OUT}/cheney_overview.png')
    import sys
    for spec in sys.argv[1:]:
        name, x, y, w, h = spec.split(',')
        crop(G, tsg, names, int(x), int(y), int(w), int(h), f'{OUT}/cheney_{name}.png')
    print('done')
