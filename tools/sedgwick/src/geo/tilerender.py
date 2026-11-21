"""Render cells (tileset, metatile_id) to an image using built tilesets."""
import struct, os
from PIL import Image
from lib import EXP, load_jasc

_cache = {}


class TS:
    def __init__(self, secondary):
        P = f'{EXP}/data/tilesets/primary/general'
        S = f'{EXP}/data/tilesets/secondary/{secondary}'
        def tiles(p):
            im = Image.open(p + '/tiles.png'); px = im.load(); w, h = im.size
            return [[[px[tx * 8 + x, ty * 8 + y] & 15 for x in range(8)] for y in range(8)]
                    for ty in range(h // 8) for tx in range(w // 8)]
        self.tp, self.ts = tiles(P), tiles(S)
        self.pals = [load_jasc(f'{P if i < 6 else S}/palettes/{i:02d}.pal') for i in range(13)]
        self.mp = open(P + '/metatiles.bin', 'rb').read()
        self.ms = open(S + '/metatiles.bin', 'rb').read()
        self.imgs = {}

    def img(self, m):
        if m in self.imgs:
            return self.imgs[m]
        d, i = (self.mp, m) if m < 512 else (self.ms, m - 512)
        out = Image.new('RGB', (16, 16), (255, 0, 255))
        if i * 16 + 16 <= len(d):
            e = struct.unpack('<8H', d[i * 16:i * 16 + 16])
            px = out.load()
            for layer in range(2):
                for q in range(4):
                    v = e[layer * 4 + q]
                    t, hf, vf, pl = v & 0x3ff, v >> 10 & 1, v >> 11 & 1, v >> 12
                    tl = self.tp[t] if t < 512 else (self.ts[t - 512] if t - 512 < len(self.ts) else None)
                    if tl is None or pl > 12:
                        continue
                    for y in range(8):
                        for x in range(8):
                            c = tl[7 - y if vf else y][7 - x if hf else x]
                            if layer and c == 0:
                                continue
                            px[(q % 2) * 8 + x, (q // 2) * 8 + y] = self.pals[pl][c]
        self.imgs[m] = out
        return out


def ts(name):
    if name not in _cache:
        _cache[name] = TS(name)
    return _cache[name]
