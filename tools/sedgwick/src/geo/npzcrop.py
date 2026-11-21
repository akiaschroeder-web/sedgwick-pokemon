"""Render a crop of the generated county straight from the region files."""
import sys, os, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geo import gen
from geo.county import OUT, REGION
from geo.tilerender import ts as load_ts


def crop(x0, y0, w, h, path):
    ids = [json.load(open(f'{gen.TSDIR}/{t}_metatiles.json')) for t in gen.TILESETS]
    im = Image.new('RGB', (w * 16, h * 16), (40, 40, 40))
    cache = {}
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            i, j = x // REGION, y // REGION
            if (i, j) not in cache:
                f = f'{OUT}/r_{i:02d}_{j:02d}.npz'
                if os.path.exists(f):
                    z = np.load(f, allow_pickle=True)
                    cache[(i, j)] = {'idx': z['idx'], 'table': z['table'].tolist()}
                else:
                    cache[(i, j)] = None
            d = cache[(i, j)]
            if d is None:
                continue
            k = d['idx'][y - j * REGION, x - i * REGION]
            t, nm = d['table'][k].split('|', 1)
            t = int(t)
            m = int(nm[5:], 16) if nm.startswith('prim:') else ids[t][nm]
            im.paste(load_ts(gen.TILESETS[t]).img(m), ((x - x0) * 16, (y - y0) * 16))
    im.save(path)


if __name__ == '__main__':
    a = sys.argv
    crop(int(a[1]), int(a[2]), int(a[3]), int(a[4]), a[5])
