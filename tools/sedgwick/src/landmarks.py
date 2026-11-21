"""Landmark buildings cut straight out of FireRed maps (block data rectangles):
the standard Gym, Pokémon Center and Poké Mart, Pewter's museum, Fuchsia's Safari Zone entrance and zoo pens."""
import json, struct
import orig
from lib import EXP

_layouts = {l['id']: l for l in json.load(open(f'{EXP}/data/layouts/layouts.json'))['layouts'] if 'id' in l}
_src = {}


def grid(layout):
    l = _layouts[layout]
    d = open(f"{EXP}/{l['blockdata_filepath']}", 'rb').read()
    v = struct.unpack(f'<{len(d) // 2}H', d)
    W = l['width']
    return [[v[y * W + x] & 0x3ff for x in range(W)] for y in range(l['height'])]


def source(secondary):
    if secondary not in _src:
        _src[secondary] = orig.Source('general_frlg', secondary, frlg=True)
    return _src[secondary]


# name: (layout, secondary tileset dir, x0, y0, w, h, door cells (col,row) within the cut)
CUTS = {
    'gym':    ('LAYOUT_PEWTER_CITY', 'pewter_city_frlg', 12, 12, 7, 5, [(3, 4)]),
    'museum': ('LAYOUT_PEWTER_CITY', 'pewter_city_frlg', 12, 0, 11, 7, [(5, 5)]),
    'safari': ('LAYOUT_FUCHSIA_CITY', 'fuchsia_city_frlg', 22, 0, 6, 6, [(2, 5)]),
    'pen_pool': ('LAYOUT_FUCHSIA_CITY', 'fuchsia_city_frlg', 5, 6, 7, 5, []),
    'lab':    ('LAYOUT_PALLET_TOWN', 'pallet_town_frlg', 13, 9, 7, 5, [(3, 4)]),
    'pc':     ('LAYOUT_PEWTER_CITY', 'pewter_city_frlg', 15, 21, 5, 5, [(2, 4)]),
    'mart':   ('LAYOUT_PEWTER_CITY', 'pewter_city_frlg', 26, 15, 4, 4, [(2, 3)]),
    'pen_sand': ('LAYOUT_FUCHSIA_CITY', 'fuchsia_city_frlg', 12, 6, 7, 5, []),
}


def cut(name):
    layout, sec, x0, y0, w, h, doors = CUTS[name]
    g = grid(layout)
    return [row[x0:x0 + w] for row in g[y0:y0 + h]], sec, doors


def pieces():
    """{piece name: (orig piece dict, is_door)} for every cell of every cut."""
    out = {}
    for name in CUTS:
        rows, sec, doors = cut(name)
        src = source(sec)
        for r, row in enumerate(rows):
            for c, m in enumerate(row):
                out[f'lm_{name}_{c}{r}'] = (src.piece(m), (c, r) in doors)
    return out


def plan(name):
    rows, _, _ = cut(name)
    return [[f'lm_{name}_{c}{r}' for c in range(len(rows[0]))] for r in range(len(rows))]
