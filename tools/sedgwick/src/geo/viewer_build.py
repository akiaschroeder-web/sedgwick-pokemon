"""Package the generated county for the browser map viewer.
  atlas.png      every metatile used, 16x16, ATLAS_COLS per row (index 0 = outside the county)
  colors.json    average colour per metatile (for zoomed-out drawing)
  r_IJ.png       region tile indices: index = R + 256*G
  county.png     1/8-scale overview
  signs.json     [[x, y, text], ...] world tile coords, every mailbox / address sign
  spots.json     [{cat, name, x, y}, ...] places to jump to: every gym, plus ../spots.json
  meta.json      grid, region size, map size"""
import glob, json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geo import gen, extract
from geo.county import OUT, REGION, grid
from geo.tilerender import ts as load_ts

DST = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/viewer'
ATLAS_COLS = 32


def spots(doors):
    """Gyms (at their built door when the region recorded one) then the hand-kept list."""
    from geo import gyms
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out = []
    for g in gyms.load():
        x, y = doors.get(g['id']) or extract.proj(g['lon'], g['lat'])
        out.append({'cat': 'Gyms', 'name': g['name'], 'x': int(x), 'y': int(y)})
    from geo import services
    for s in services.load():
        if s['kind'] == 'lab':
            out.append({'cat': 'Landmarks', 'name': s['name'], 'x': s['x'] + 3, 'y': s['y'] + 4})
        if s['kind'] == 'pc':
            out.append({'cat': 'Pokémon Centers', 'name': s['name'].replace(' Pokémon Center', ''),
                        'x': s['x'] + services.PC_DOOR[0], 'y': s['y'] + services.PC_DOOR[1]})
    extra = os.path.join(here, 'spots.json')
    if os.path.exists(extra):
        for s in json.load(open(extra))['spots']:
            x, y = extract.proj(s['lon'], s['lat'])
            out.append({'cat': s.get('cat', 'Places'), 'name': s['name'], 'x': int(x), 'y': int(y)})
    return out


def main():
    os.makedirs(DST, exist_ok=True)
    ids = [json.load(open(f'{gen.TSDIR}/{t}_metatiles.json')) for t in gen.TILESETS]
    keys = ['void']
    kidx = {'void': 0}
    files = sorted(glob.glob(f'{OUT}/r_*.npz'))
    regions = []
    signs = []
    doors = {}
    for f in files:
        i, j = int(f[-9:-7]), int(f[-6:-4])
        d = np.load(f, allow_pickle=True)
        table = d['table'].tolist()
        remap = np.zeros(len(table), np.uint16)
        for k, key in enumerate(table):
            if key not in kidx:
                kidx[key] = len(keys); keys.append(key)
            remap[k] = kidx[key]
        g = remap[d['idx']]
        g[~d['inside']] = 0
        if not g.any():
            continue
        rgb = np.zeros(g.shape + (3,), np.uint8)
        rgb[..., 0] = g & 255
        rgb[..., 1] = g >> 8
        Image.fromarray(rgb).save(f'{DST}/r_{i:02d}_{j:02d}.png', optimize=True)
        regions.append([i, j])
        js = json.load(open(f[:-4] + '.json'))
        for x, y, s in js['signs']:
            signs.append([int(i * REGION + x), int(j * REGION + y), s])
        for g in js.get('gyms', []):
            doors[g['id']] = (int(i * REGION + g['door'][0]), int(j * REGION + g['door'][1]))
    # atlas + average colours
    rows = (len(keys) + ATLAS_COLS - 1) // ATLAS_COLS
    atlas = Image.new('RGB', (ATLAS_COLS * 16, rows * 16), (24, 26, 30))
    cols = [[24, 26, 30]]
    names = ['outside the county']
    for k, key in enumerate(keys[1:], 1):
        t, nm = key.split('|', 1)
        t = int(t)
        m = int(nm[5:], 16) if nm.startswith('prim:') else ids[t][nm]
        im = load_ts(gen.TILESETS[t]).img(m)
        atlas.paste(im, ((k % ATLAS_COLS) * 16, (k // ATLAS_COLS) * 16))
        cols.append([int(v) for v in np.array(im).reshape(-1, 3).mean(0)])
        names.append(nm)
    atlas.save(f'{DST}/atlas.png', optimize=True)
    json.dump({'colors': cols, 'names': names}, open(f'{DST}/colors.json', 'w'))
    Image.open(f'{OUT}/county.png').save(f'{DST}/county.png', optimize=True)
    json.dump(signs, open(f'{DST}/signs.json', 'w'), separators=(',', ':'))
    json.dump(spots(doors), open(f'{DST}/spots.json', 'w'), indent=0)
    gx, gy = grid()
    json.dump({'region': REGION, 'gx': gx, 'gy': gy, 'width': extract.WIDTH, 'height': extract.HEIGHT,
               'thumb': 8, 'atlasCols': ATLAS_COLS, 'regions': regions,
               'metersPerTile': extract.METERS_PER_TILE,
               'proj': {'lon0': extract.LON0, 'lat0': extract.LAT0, 'kx': extract.KX, 'ky': extract.KY}},
              open(f'{DST}/meta.json', 'w'))
    print(len(keys), 'metatiles,', len(regions), 'regions,', len(signs), 'signs')


if __name__ == '__main__':
    main()
