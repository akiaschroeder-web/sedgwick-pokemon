"""Reuse original FRLG / Emerald building art: pull metatiles straight out of a
tileset pair, keep both layers and flips, and repack every colour the chosen
pieces use into as few 16-colour palettes as possible.

Recolouring a building is then a palette swap: same tiles, different colours.
"""
import struct
from PIL import Image
from lib import EXP, load_jasc


class Source:
    def __init__(self, primary, secondary, frlg=True):
        self.P = f'{EXP}/data/tilesets/primary/{primary}'
        self.S = f'{EXP}/data/tilesets/secondary/{secondary}'
        self.NT, self.NM, self.NP = (640, 640, 7) if frlg else (512, 512, 6)
        self.frlg = frlg
        self.tp = self._tiles(self.P)
        self.ts = self._tiles(self.S)
        self.pals = [load_jasc(f'{self.P if i < self.NP else self.S}/palettes/{i:02d}.pal') for i in range(13)]
        self.mtP = open(self.P + '/metatiles.bin', 'rb').read()
        self.mtS = open(self.S + '/metatiles.bin', 'rb').read()
        self.atS = open(self.S + '/metatile_attributes.bin', 'rb').read()

    @staticmethod
    def _tiles(path):
        im = Image.open(path + '/tiles.png')
        px = im.load()
        w, h = im.size
        return [[[px[tx * 8 + x, ty * 8 + y] & 15 for x in range(8)] for y in range(8)]
                for ty in range(h // 8) for tx in range(w // 8)]

    def entries(self, m):
        if m >= self.NM:
            i = m - self.NM
            e = struct.unpack('<8H', self.mtS[i * 16:i * 16 + 16])
            if self.frlg:
                a = struct.unpack('<I', self.atS[i * 4:i * 4 + 4])[0]
                layer = (a >> 29) & 3
                self.last_beh = None          # FRLG behaviours use a different numbering
            else:
                a = struct.unpack('<H', self.atS[i * 2:i * 2 + 2])[0]
                layer = (a >> 12) & 0xF
                self.last_beh = a & 0xFF
        else:
            e = struct.unpack('<8H', self.mtP[m * 16:m * 16 + 16])
            layer = 0
            self.last_beh = 0
        return e, layer

    def quad_rgb(self, v):
        """8x8 grid of RGB tuples (None = transparent) for one tile entry."""
        t, hf, vf, pl = v & 0x3ff, v >> 10 & 1, v >> 11 & 1, v >> 12
        src = self.tp[t] if t < self.NT else (self.ts[t - self.NT] if t - self.NT < len(self.ts) else None)
        if src is None or pl > 12:
            return None
        g = [[None if c == 0 else self.pals[pl][c] for c in row] for row in src]
        if hf:
            g = [r[::-1] for r in g]
        if vf:
            g = g[::-1]
        return g

    def piece(self, m, ground_pals=(0, 1)):
        """Metatile m as {'bottom': [4 quads], 'top': [4 quads], 'layer'}.
        A quad is an 8x8 RGB grid, None (empty) or 'LAWN' (replace with our ground)."""
        e, layer = self.entries(m)
        bottom, top = [], []
        for q in range(4):
            tv = self.quad_rgb(e[4 + q])
            bv_raw = e[q]
            top_opaque = tv is not None and all(c is not None for row in tv for c in row)
            if top_opaque or (bv_raw >> 12) in ground_pals:
                bottom.append('LAWN')
            else:
                bottom.append(self.quad_rgb(bv_raw) or 'LAWN')
            if tv is not None and all(c is None for row in tv for c in row):
                tv = None
            top.append(tv)
        return dict(bottom=bottom, top=top, layer=['NORMAL', 'COVERED', 'SPLIT'][min(layer, 2)])


def hflip_piece(p):
    def fq(g):
        return g if g in (None, 'LAWN') else [r[::-1] for r in g]
    sw = lambda L: [fq(L[1]), fq(L[0]), fq(L[3]), fq(L[2])]
    return dict(bottom=sw(p['bottom']), top=sw(p['top']), layer=p['layer'])


def pack(pieces, max_colors=15):
    """Assign every non-lawn quad to a palette so each palette holds <= 15 colours.
    Returns (palettes [list of colour lists], assign {id(quad): palette index})."""
    quads = []
    for p in pieces:
        for g in p['bottom'] + p['top']:
            if g not in (None, 'LAWN'):
                quads.append(g)
    sets = []
    for g in quads:
        sets.append(frozenset(c for row in g for c in row if c is not None))
    pals = []      # list of sets
    order = sorted(range(len(quads)), key=lambda i: -len(sets[i]))
    assign = {}
    for i in order:
        s = sets[i]
        best, best_add = None, None
        for pi, ps in enumerate(pals):
            add = len(s - ps)
            if len(ps) + add <= max_colors and (best is None or add < best_add):
                best, best_add = pi, add
        if best is None:
            pals.append(set(s))
            best = len(pals) - 1
        else:
            pals[best] |= s
        assign[id(quads[i])] = best
    pal_lists = [[(255, 0, 255)] + sorted(ps, key=lambda c: (sum(c), c)) for ps in pals]
    for pl in pal_lists:
        pl += [(0, 0, 0)] * (16 - len(pl))
    return pal_lists, assign


def index_quad(g, pal):
    lut = {c: i for i, c in enumerate(pal) if i}
    return [[0 if c is None else lut[c] for c in row] for row in g]


def piece_indexed(src, m, palmap, ground_pals=()):
    """Like Source.piece but keeps the original 4bpp indices: each quad becomes
    (8x8 index grid, our palette slot) using palmap {source palette: our slot}.
    Ground palettes become 'LAWN'. Use when a source palette is copied whole."""
    e, layer = src.entries(m)
    def grid(v):
        t, hf, vf, pl = v & 0x3ff, v >> 10 & 1, v >> 11 & 1, v >> 12
        g = src.tp[t] if t < src.NT else src.ts[t - src.NT]
        g = [list(r) for r in g]
        if hf:
            g = [r[::-1] for r in g]
        if vf:
            g = g[::-1]
        return g, pl
    bottom, top = [], []
    for q in range(4):
        tg, tp = grid(e[4 + q])
        top_empty = all(v == 0 for r in tg for v in r)
        top_opaque = all(v != 0 for r in tg for v in r)
        bg, bp = grid(e[q])
        if top_opaque or bp in ground_pals:
            bottom.append('LAWN')
        else:
            bottom.append((bg, palmap[bp]))
        top.append(None if top_empty else (tg, palmap[tp]))
    return dict(bottom=bottom, top=top, layer=['NORMAL', 'COVERED', 'SPLIT'][min(layer, 2)],
                beh=getattr(src, 'last_beh', 0) or 0)


def merge_close_colors(pieces, max_pals, max_colors=15):
    """Merge the closest colour pairs (in place) until the pieces pack into max_pals
    palettes. Near-duplicate shades in FRLG art make this nearly invisible."""
    import math
    def quads():
        for p in pieces:
            for L in (p['bottom'], p['top']):
                for g in L:
                    if g not in (None, 'LAWN'):
                        yield g
    while True:
        pals, _ = pack(pieces, max_colors)
        if len(pals) <= max_pals:
            return
        cols = sorted({c for g in quads() for r in g for c in r if c is not None})
        best = None
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                d = math.dist(cols[i], cols[j])
                if best is None or d < best[0]:
                    best = (d, cols[i], cols[j])
        _, a, b = best
        keep = tuple((x + y) // 2 for x, y in zip(a, b))
        for g in quads():
            for r in g:
                for k, c in enumerate(r):
                    if c == a or c == b:
                        r[k] = keep
