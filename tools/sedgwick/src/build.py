"""Assemble Sedgwick secondary tilesets in decomp format.

Writes into the expansion checkout (data/tilesets/secondary/<name>/) and a
name -> metatile id index (JSON + C header) for the map generator.
"""
import json, os, struct, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib, street, house2, props, wheat, rural, farm2, commercial, gas, orig, civic, downtown, church, retail, suburb

EXP = lib.EXP
NUM_PRIMARY_TILES = 512
NUM_PRIMARY_METATILES = 512
MAX_SECONDARY_TILES = 512
MAX_SECONDARY_METATILES = 512
LAYER = {'NORMAL': 0, 'COVERED': 1, 'SPLIT': 2}
BEHAVIOR = {'MB_NORMAL': 0, 'MB_TALL_GRASS': 2, 'MB_TALL_WHEAT': 4, 'MB_ANIMATED_DOOR': 0x69, 'MB_NON_ANIMATED_DOOR': 0x60}

GRASS_BOTTOM = [[street.grass_px(x, y) for x in range(16)] for y in range(16)]


class Tileset:
    def __init__(self, name):
        self.name = name
        self.tiles = []          # list of 8x8 tuples
        self.index = {}          # tile -> (id, hflip, vflip)
        self.metatiles = []      # (name, entries[8], attr)
        self.palettes = {}       # slot -> 16 colours

    def tile_ref(self, t, pal):
        """Return a 16-bit tile entry for an 8x8 grid t using palette slot pal."""
        if all(v == 0 for row in t for v in row):
            return 0  # primary tile 0 is blank
        key = tuple(tuple(r) for r in t)
        if key not in self.index:
            tid = len(self.tiles)
            self.tiles.append(key)
            self.index[key] = (tid, 0, 0)
            h = tuple(r[::-1] for r in key)
            v = key[::-1]
            hv = tuple(r[::-1] for r in key[::-1])
            self.index.setdefault(h, (tid, 1, 0))
            self.index.setdefault(v, (tid, 0, 1))
            self.index.setdefault(hv, (tid, 1, 1))
        tid, hf, vf = self.index[key]
        return (NUM_PRIMARY_TILES + tid) | (hf << 10) | (vf << 11) | (pal << 12)

    def quads(self, g):
        for q in range(4):
            ox, oy = (q % 2) * 8, (q // 2) * 8
            yield [[g[oy + y][ox + x] for x in range(8)] for y in range(8)]

    def add(self, name, bottom, pal_b, top=None, pal_t=0, layer='NORMAL', beh='MB_NORMAL'):
        e = [self.tile_ref(t, pal_b) for t in self.quads(bottom)]
        if top is None:
            e += [0, 0, 0, 0]
        else:
            e += [self.tile_ref(t, pal_t) for t in self.quads(top)]
        attr = BEHAVIOR[beh] | (LAYER[layer] << 12)
        self.metatiles.append((name, e, attr))

    def add_q(self, name, bottom, top, layer='NORMAL', beh='MB_NORMAL'):
        """bottom/top: lists of four (8x8 grid, palette slot) or None (empty)."""
        def ref(item):
            if isinstance(item, int):
                return item               # raw entry (e.g. a primary tile such as Hoenn water)
            g, p = item
            return self.tile_ref(g, p) if g is not None else 0
        e = [ref(i) for i in bottom] + [ref(i) for i in top]
        attr = (beh if isinstance(beh, int) else BEHAVIOR[beh]) | (LAYER[layer] << 12)
        self.metatiles.append((name, e, attr))

    def write(self):
        assert len(self.tiles) <= MAX_SECONDARY_TILES, f'{self.name}: {len(self.tiles)} tiles'
        assert len(self.metatiles) <= MAX_SECONDARY_METATILES, f'{self.name}: {len(self.metatiles)} metatiles'
        out = f'{EXP}/data/tilesets/secondary/{self.name}'
        os.makedirs(out + '/palettes', exist_ok=True)
        n = len(self.tiles)
        rows = (n + 15) // 16
        im = Image.new('P', (128, rows * 8), 0)
        viewer = self.palettes.get(min(self.palettes))  # any palette, just for viewing
        flat = [c for col in viewer for c in col]
        im.putpalette(flat + [0] * (768 - len(flat)))
        for i, t in enumerate(self.tiles):
            for y in range(8):
                for x in range(8):
                    im.putpixel(((i % 16) * 8 + x, (i // 16) * 8 + y), t[y][x])
        im.save(out + '/tiles.png')
        for slot in range(16):
            cols = self.palettes.get(slot, [(0, 0, 0)] * 16)
            open(f'{out}/palettes/{slot:02d}.pal', 'w').write(lib.jasc(cols))
        with open(out + '/metatiles.bin', 'wb') as f:
            for _, e, _ in self.metatiles:
                f.write(struct.pack('<8H', *e))
        with open(out + '/metatile_attributes.bin', 'wb') as f:
            for _, _, a in self.metatiles:
                f.write(struct.pack('<H', a))
        index = {name: NUM_PRIMARY_METATILES + i for i, (name, _, _) in enumerate(self.metatiles)}
        return n, index


def camel(s):
    return ''.join(p[:1].upper() + p[1:] for p in s.replace('@', '_').split('_') if p)


ROOF_SLOTS = {'red': 8, 'brown': 9, 'charcoal': 10}
WALL_SLOTS = {'white': 11, 'tan': 12}


def quads(g16):
    return [[[g16[oy + y][ox + x] for x in range(8)] for y in range(8)] for ox, oy in ((0, 0), (8, 0), (0, 8), (8, 8))]


def residential():
    ts = Tileset('sedgwick_residential')
    P_STREET, P_PROPS = 6, 7
    ts.palettes[P_STREET] = street.PAL_STREET
    ts.palettes[P_PROPS] = props.PAL_PROPS
    for k, slot in ROOF_SLOTS.items():
        ts.palettes[slot] = house2.ROOF_VARIANTS[k]
    for k, slot in WALL_SLOTS.items():
        ts.palettes[slot] = house2.WALL_VARIANTS[k]

    ts.add('lawn', GRASS_BOTTOM, P_STREET)
    for name, (g, beh) in street.metatiles().items():
        ts.add(name, g, P_STREET, beh=beh)
    for name, (top, layer, beh) in props.metatiles().items():
        ts.add(name, GRASS_BOTTOM, P_STREET, top, P_PROPS, layer=layer, beh=beh)
    add_houses(ts, ROOF_SLOTS, WALL_SLOTS, P_STREET)
    asphalt = [[street.asph_px(x, y) for x in range(16)] for y in range(16)]
    for name, g in suburb.all_pieces().items():
        tall_top = name.startswith('water_tower') and name[-1] in '012'
        under = asphalt if name.startswith(('sedan', 'pickup')) else GRASS_BOTTOM   # parked at the curb
        ts.add(name, under, P_STREET, g, P_PROPS, layer='NORMAL' if tall_top else 'COVERED')
    lawn_q = quads(GRASS_BOTTOM)
    for name, qs in church.pieces().items():
        for roof, slot in ROOF_SLOTS.items():
            top = [(q, slot) if q is not None else (None, 0) for q in qs]
            ts.add_q(f'church_{name}_{roof}', [(lq, P_STREET) for lq in lawn_q], top, layer='NORMAL')
    return ts


def add_houses(ts, roof_slots, wall_slots, lawn_slot):
    lawn_q = quads(GRASS_BOTTOM)
    for pname, p in house2.pieces().items():
        variants = roof_slots if p['pal'] == 'roof' else wall_slots
        for vname, slot in variants.items():
            wall_slot = slot if p['pal'] == 'wall' else None
            bottom = []
            for q in range(4):
                u = p['under'][q]
                bottom.append((u, wall_slot) if u is not None else (lawn_q[q], lawn_slot))
            top = [(t, slot) for t in p['top']]
            ts.add_q(f'h_{pname}_{vname}', bottom, top, layer=p['layer'], beh=p['beh'])


RURAL_ROOF = {'green': 9}
RURAL_WALL = {'white': 10}
PROPS_TO_ROAD = {1: 15, 2: 12, 3: 12, 4: 13, 5: 9, 6: 10, 7: 14, 8: 15, 9: 3, 10: 4, 11: 5, 12: 14, 13: 15, 14: 11, 15: 4}
FARM_TO_ROAD = {rural.F_WD: 14, rural.F_CD: 7, rural.F_CL: 5, rural.F_G: 2, rural.F_GS: 1}


def rural_ts():
    ts = Tileset('sedgwick_rural')
    P_FIELD, P_CORN, P_ROAD, P_BARN, P_SHED = 6, 7, 8, 11, 12
    slot = {'field': P_FIELD, 'corn': P_CORN, 'milo': P_CORN, 'road': P_ROAD}
    ts.palettes[P_FIELD] = lib.PAL_FIELD
    ts.palettes[P_CORN] = rural.PAL_CORN
    ts.palettes[P_ROAD] = rural.PAL_ROAD
    ts.palettes[9] = house2.ROOF_VARIANTS['green']
    ts.palettes[10] = house2.WALL_VARIANTS['white']
    ts.palettes[P_BARN] = farm2.PAL_BARN
    ts.palettes[P_SHED] = farm2.PAL_SHED
    grass_road = [[rural.grass(x, y) for x in range(16)] for y in range(16)]
    lawn_q = quads(grass_road)
    ts.add('lawn', grass_road, P_ROAD)
    for name, (g, beh) in wheat.metatiles().items():
        ts.add(name, g, P_FIELD, beh=beh)
    for name, (g, beh) in wheat.corn_metatiles().items():
        ts.add(name, g, P_CORN, beh=beh)
    for name, (g, pk, beh, walk) in rural.metatiles().items():
        if pk == 'farm':
            if name == 'hay_bales':
                g = [[FARM_TO_ROAD.get(v, v) for v in row] for row in g]
                ts.add(name, g, P_ROAD, beh=beh)
            continue
        ts.add(name, g, slot[pk], beh=beh)
    for name, (top, layer, beh) in props.metatiles().items():
        if name.startswith(('mailbox', 'power_pole', 'chainlink', 'stop_sign')):
            top = [[PROPS_TO_ROAD.get(v, 0) if v else 0 for v in row] for row in top]
            ts.add(name, grass_road, P_ROAD, top, P_ROAD, layer=layer, beh=beh)
    add_houses(ts, RURAL_ROOF, RURAL_WALL, P_ROAD)
    # farm buildings from Vermilion's warehouse-roof art
    for prefix, kind, pslot in (('barn', 'barn', P_BARN), ('shed', 'shed', P_SHED)):
        k = farm2.kit()
        k.update(farm2.door_pieces(kind, tall=True))
        for pname, p in k.items():
            bottom = [(u, pslot) if u is not None else (lawn_q[q], P_ROAD) for q, u in enumerate(p['under'])]
            top = [(t, pslot) if t is not None else (None, 0) for t in p['top']]
            ts.add_q(f'{prefix}_{pname}', bottom, top, layer=p['layer'], beh=p['beh'])
    for d in (farm2.silo(), farm2.grain_elevator()):
        for name, g in d.items():
            ts.add(name, grass_road, P_ROAD, g, P_SHED, layer='NORMAL')
    return ts


def register_doors(ts, index, wall_slots):
    """Give every door metatile Pallet's opening animation (re-indexed to our palette)."""
    C = camel(ts.name)
    house2.door_anim_png(f'{EXP}/graphics/door_anims/sedgwick_house.png')
    path = f'{EXP}/src/field_door.c'
    s = open(path).read()
    decl = 'static const u8 sDoorAnimTiles_SedgwickHouse[] = INCGFX_U8("graphics/door_anims/sedgwick_house.png", ".4bpp");\n'
    if 'sDoorAnimTiles_SedgwickHouse' not in s:
        anchor = 'static const u8 sDoorAnimTiles_Pallet[] = INCGFX_U8("graphics/door_anims/pallet.png", ".4bpp");\n'
        s = s.replace(anchor, anchor + decl)
    start, end = f'    // Sedgwick County houses: {C}\n', f'    // end Sedgwick County houses: {C}\n'
    pals, entries = '', ''
    for vname, slot in wall_slots.items():
        pals += f'static const u8 sDoorAnimPalettes_SedgwickHouse_{C}_{camel(vname)}[] = {{{", ".join([str(slot)] * 8)}}};\n'
        mt = f'METATILE_{C}_{camel("h_wall_door_" + vname)}'
        entries += ('    {\n'
                    f'        .metatileNum = {mt},\n'
                    f'        .tileset = &gTileset_{C},\n'
                    '        .sound = DOOR_SOUND_NORMAL,\n'
                    '        .size = DOOR_SIZE_1x1,\n'
                    '        .tiles = sDoorAnimTiles_SedgwickHouse,\n'
                    f'        .palettes = sDoorAnimPalettes_SedgwickHouse_{C}_{camel(vname)}\n'
                    '    },\n')
    block = start + entries + end
    if start in s:
        a = s.index(start); b = s.index(end) + len(end)
        s = s[:a] + block + s[b:]
    else:
        t = s.index('    {},\n};', s.index('sDoorAnimGraphicsTable[] ='))
        s = s[:t] + block + s[t:]
    pstart, pend = f'// Sedgwick door palettes: {C}\n', f'// end Sedgwick door palettes: {C}\n'
    pblock = pstart + pals + pend
    if pstart in s:
        a = s.index(pstart); b = s.index(pend) + len(pend)
        s = s[:a] + pblock + s[b:]
    else:
        anchor = 'static const u8 sDoorAnimPalettes_Pallet[] = {8, 8, 8, 8, 8, 8, 8, 8};\n'
        s = s.replace(anchor, anchor + pblock)
    open(path, 'w').write(s)


CEL_SLOTS = {'mint': 9, 'brick': 10, 'beige': 11}


def commercial_ts():
    ts = Tileset('sedgwick_commercial')
    P_STREET, P_PROPS, P_CEL, P_GAS = 6, 7, 8, 12
    ts.palettes[P_STREET] = street.PAL_STREET
    ts.palettes[P_PROPS] = props.PAL_PROPS
    ts.palettes[P_CEL] = commercial.BASE_PALS[commercial.OTHER_PAL]
    for v, slot in CEL_SLOTS.items():
        ts.palettes[slot] = commercial.wall_palette(v)
    ts.palettes[P_GAS] = gas.PAL_GAS
    ts.add('lawn', GRASS_BOTTOM, P_STREET)
    for name, (g, beh) in street.metatiles().items():
        ts.add(name, g, P_STREET, beh=beh)
    for name, g in commercial.parking().items():
        ts.add(name, g, P_STREET)
    for name, (top, layer, beh) in props.metatiles().items():
        ts.add(name, GRASS_BOTTOM, P_STREET, top, P_PROPS, layer=layer, beh=beh)
    lawn_q = quads(GRASS_BOTTOM)
    base = commercial.BASE_PALS
    for m in commercial.IDS:
        p = commercial.PIECES[m]
        for v, wslot in CEL_SLOTS.items():
            def conv(g, q):
                if g == 'LAWN':
                    return (lawn_q[q], P_STREET)
                if g is None:
                    return (None, 0)
                pi = commercial.quad_palette(g)
                return (orig.index_quad(g, base[pi]), wslot if pi == commercial.WALL_PAL else P_CEL)
            bottom = [conv(g, q) for q, g in enumerate(p['bottom'])]
            top = [conv(g, q) for q, g in enumerate(p['top'])]
            beh = 'MB_ANIMATED_DOOR' if m == commercial.DOOR else 'MB_NORMAL'
            ts.add_q(f'cel_{m:03x}_{v}', bottom, top, layer=p['layer'], beh=beh)
    pad_g = gas.pad()
    ts.add('gas_pad', pad_g, P_GAS)
    top, pumps = gas.canopy(5)
    for name, g in top.items():
        ts.add(name, pad_g, P_GAS, g, P_GAS, layer='NORMAL')
    for name, g in pumps.items():
        ts.add(name, g, P_GAS)
    for name, g in gas.price_sign().items():
        ts.add(name, GRASS_BOTTOM, P_STREET, g, P_GAS, layer='NORMAL' if name.endswith('0') else 'COVERED')
    return ts


def city_ts():
    ts = Tileset('sedgwick_city')
    P_STREET, P_PROPS, P_NATURE = 6, 7, 8
    ts.palettes[P_STREET] = street.PAL_STREET
    ts.palettes[P_PROPS] = props.PAL_PROPS
    ts.palettes[P_NATURE] = civic.PAL_NATURE
    lawn_q = quads(GRASS_BOTTOM)
    W = civic.WATER_ENTRIES
    ts.add('lawn', GRASS_BOTTOM, P_STREET)
    for name, (g, beh) in street.metatiles().items():
        if name.startswith(('culdesac', 'bend44', 'bend28', 'diag21', 'drive')):
            continue                     # suburban pieces live in the residential tileset
        ts.add(name, g, P_STREET, beh=beh)
    for name, (top, layer, beh) in props.metatiles().items():
        ts.add(name, GRASS_BOTTOM, P_STREET, top, P_PROPS, layer=layer, beh=beh)
    for name, g in {**civic.bridge_pieces(), **civic.footbridge_pieces()}.items():
        ts.add_q(name, W, [(q, P_STREET) for q in quads(g)], layer='COVERED')
    for name, g in civic.interstate_pieces().items():
        ts.add(name, g, P_STREET)
    for name, g in civic.bank_pieces().items():
        ts.add_q(name, W, [(q, P_NATURE) for q in quads(g)], layer='COVERED')
    park = {**civic.park_props(), **civic.pavilion(4), **civic.ball_diamond()}
    for name, g in park.items():
        layer = 'NORMAL' if name.startswith('pavilion') and name[-1] in '01' else 'COVERED'
        ts.add(name, GRASS_BOTTOM, P_STREET, g, P_PROPS, layer=layer)
    plaza = civic.plaza_pieces()
    for name, g in plaza.items():
        ts.add(name, g, P_STREET)
    pieces, packed, origin = civic.landmark_from_png(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'custom', 'landmark.png'), plaza)
    if pieces:
        pals, assign = packed
        slots = [9, 10, 11, 12][:len(pals)]
        assert len(pals) <= 4, f'landmark needs {len(pals)} palettes'
        for i, p in enumerate(pals):
            ts.palettes[slots[i]] = p
        for name, (under, quads_) in pieces.items():
            ug = plaza[under] if under != 'lawn' else GRASS_BOTTOM
            top = []
            for g in quads_:
                if g is None:
                    top.append((None, 0))
                else:
                    pi = assign[id(g)]
                    top.append((orig.index_quad(g, pals[pi]), slots[pi]))
            abs_row = int(name.split('_')[2]) + origin[1]
            ts.add_q(name, [(q, P_STREET) for q in quads(ug)], top,
                     layer='NORMAL' if abs_row < 2 else 'COVERED')
        json.dump({'origin': origin, 'pieces': sorted(pieces)},
                  open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'custom', 'landmark_layout.json'), 'w'))
    return ts


DT_CEL = {'brick': 11, 'beige': 12}


def downtown_ts():
    ts = Tileset('sedgwick_downtown')
    P_STREET, P_PROPS = 6, 7
    ts.palettes[P_STREET] = street.PAL_STREET
    ts.palettes[P_PROPS] = props.PAL_PROPS
    ts.palettes[downtown.SLOT_GRAY] = downtown.PAL_GRAY
    ts.palettes[downtown.SLOT_TAN] = downtown.PAL_TAN
    ts.palettes[10] = commercial.BASE_PALS[commercial.OTHER_PAL]
    for v, slot in DT_CEL.items():
        ts.palettes[slot] = commercial.wall_palette(v)
    ts.add('lawn', GRASS_BOTTOM, P_STREET)
    for name, (g, beh) in street.metatiles().items():
        if name.startswith(('culdesac', 'bend', 'diag', 'drive')):
            continue
        ts.add(name, g, P_STREET, beh=beh)
    for name, (top, layer, beh) in props.metatiles().items():
        if name.startswith(('chainlink', 'privacy', 'mailbox', 'power_pole', 'rr_')):
            continue
        ts.add(name, GRASS_BOTTOM, P_STREET, top, P_PROPS, layer=layer, beh=beh)
    lawn_q = quads(GRASS_BOTTOM)
    def add_indexed(name, p):
        bottom = [(lawn_q[q], P_STREET) if b == 'LAWN' else b for q, b in enumerate(p['bottom'])]
        top = [(None, 0) if t is None else t for t in p['top']]
        ts.add_q(name, bottom, top, layer=p['layer'], beh=p['beh'])
    for m in downtown.all_rb_ids():
        add_indexed(f'rb_{m:03x}', downtown.rb_piece(m))
    for m in sorted({m for row in downtown.ARENA for m in row if m}):
        add_indexed(f'bf_{m:03x}', downtown.bf_piece(m))
    for name, g in downtown.sports_field().items():
        ts.add(name, GRASS_BOTTOM, P_STREET, g, P_PROPS, layer='COVERED')
    base = commercial.BASE_PALS
    for m in commercial.IDS:
        p = commercial.PIECES[m]
        for v, wslot in DT_CEL.items():
            def conv(g, q):
                if g == 'LAWN':
                    return (lawn_q[q], P_STREET)
                if g is None:
                    return (None, 0)
                pi = commercial.quad_palette(g)
                return (orig.index_quad(g, base[pi]), wslot if pi == commercial.WALL_PAL else 10)
            ts.add_q(f'cel_{m:03x}_{v}', [conv(g, q) for q, g in enumerate(p['bottom'])],
                     [conv(g, q) for q, g in enumerate(p['top'])], layer=p['layer'],
                     beh='MB_ANIMATED_DOOR' if m == commercial.DOOR else 'MB_NORMAL')
    return ts


def register_downtown_doors(ts):
    """Rustboro tower/tan doors and the Battle Dome door keep their own animations."""
    C = camel(ts.name)
    path = f'{EXP}/src/field_door.c'
    s = open(path).read()
    entries = [(f'rb_{downtown.TOWER_DOOR:03x}', 'RustboroGray', [downtown.SLOT_GRAY] * 8),
               (f'rb_{downtown.TAN_DOOR:03x}', 'RustboroTan', [downtown.SLOT_TAN] * 8),
               ('bf_28a', 'BattleDome', None)]
    pals = ''
    body = ''
    for name, gfx, slots in entries:
        if slots:
            pname = f'sDoorAnimPalettes_Sedgwick{C}_{gfx}'
            pals += f'static const u8 {pname}[] = {{{", ".join(map(str, slots))}}};\n'
        else:
            pname = f'sDoorAnimPalettes_{gfx}'
        body += ('    {\n'
                 f'        .metatileNum = METATILE_{C}_{camel(name)},\n'
                 f'        .tileset = &gTileset_{C},\n'
                 '        .sound = DOOR_SOUND_NORMAL,\n'
                 '        .size = DOOR_SIZE_1x2,\n'
                 f'        .tiles = sDoorAnimTiles_{gfx},\n'
                 f'        .palettes = {pname}\n'
                 '    },\n')
    start, end = f'    // Sedgwick doors: {C}\n', f'    // end Sedgwick doors: {C}\n'
    block = start + body + end
    if start in s:
        a = s.index(start); b = s.index(end) + len(end); s = s[:a] + block + s[b:]
    else:
        t = s.index('    {},\n};', s.index('sDoorAnimGraphicsTable[] ='))
        s = s[:t] + block + s[t:]
    pstart, pend = f'// Sedgwick door palettes (downtown): {C}\n', f'// end Sedgwick door palettes (downtown): {C}\n'
    pblock = pstart + pals + pend
    if pstart in s:
        a = s.index(pstart); b = s.index(pend) + len(pend); s = s[:a] + pblock + s[b:]
    else:
        anchor = 'static const u8 sDoorAnimPalettes_Pallet[] = {8, 8, 8, 8, 8, 8, 8, 8};\n'
        s = s.replace(anchor, anchor + pblock)
    open(path, 'w').write(s)


RT_CEL = {'beige': 9}


def retail_ts():
    ts = Tileset('sedgwick_retail')
    P_STREET, P_PROPS, P_CEL, P_GAS = 6, 7, 8, 12
    ts.palettes[P_STREET] = street.PAL_STREET
    ts.palettes[P_PROPS] = props.PAL_PROPS
    ts.palettes[P_CEL] = commercial.BASE_PALS[commercial.OTHER_PAL]
    for v, slot in RT_CEL.items():
        ts.palettes[slot] = commercial.wall_palette(v)
    BB = [10, 11]
    assert len(retail.PALS) <= 2
    for i, p in enumerate(retail.PALS):
        ts.palettes[BB[i]] = p
    ts.palettes[P_GAS] = gas.PAL_GAS
    ts.add('lawn', GRASS_BOTTOM, P_STREET)
    for name, (g, beh) in street.metatiles().items():
        if name.startswith(('culdesac', 'bend', 'diag')):
            continue
        ts.add(name, g, P_STREET, beh=beh)
    for name, g in commercial.parking().items():
        ts.add(name, g, P_STREET)
    for name, (top, layer, beh) in props.metatiles().items():
        if name.startswith(('chainlink', 'privacy', 'mailbox', 'rr_')):
            continue
        ts.add(name, GRASS_BOTTOM, P_STREET, top, P_PROPS, layer=layer, beh=beh)
    for name, g in suburb.vehicles().items():
        ts.add(name, [[street.asph_px(x, y) for x in range(16)] for y in range(16)], P_STREET, g, P_PROPS, layer='COVERED')
    lawn_q = quads(GRASS_BOTTOM)
    base = commercial.BASE_PALS
    for m in commercial.IDS:
        p = commercial.PIECES[m]
        for v, wslot in RT_CEL.items():
            def conv(g, q):
                if g == 'LAWN':
                    return (lawn_q[q], P_STREET)
                if g is None:
                    return (None, 0)
                pi = commercial.quad_palette(g)
                return (orig.index_quad(g, base[pi]), wslot if pi == commercial.WALL_PAL else P_CEL)
            ts.add_q(f'cel_{m:03x}_{v}', [conv(g, q) for q, g in enumerate(p['bottom'])],
                     [conv(g, q) for q, g in enumerate(p['top'])], layer=p['layer'],
                     beh='MB_ANIMATED_DOOR' if m == commercial.DOOR else 'MB_NORMAL')
    for m in retail.IDS:
        p = retail.PIECES[m]
        def conv(g, q):
            if g == 'LAWN':
                return (lawn_q[q], P_STREET)
            if g is None:
                return (None, 0)
            pi = retail.ASSIGN[id(g)]
            return (orig.index_quad(g, retail.PALS[pi]), BB[pi])
        ts.add_q(f'bb_{m:03x}', [conv(g, q) for q, g in enumerate(p['bottom'])],
                 [conv(g, q) for q, g in enumerate(p['top'])], layer=p['layer'],
                 beh='MB_NON_ANIMATED_DOOR' if m == retail.DOOR else 'MB_NORMAL')
    pad_g = gas.pad()
    ts.add('gas_pad', pad_g, P_GAS)
    top, pumps = gas.canopy(5)
    for name, g in top.items():
        ts.add(name, pad_g, P_GAS, g, P_GAS, layer='NORMAL')
    for name, g in pumps.items():
        ts.add(name, g, P_GAS)
    for name, g in gas.price_sign().items():
        ts.add(name, GRASS_BOTTOM, P_STREET, g, P_GAS, layer='NORMAL' if name.endswith('0') else 'COVERED')
    for name, g in retail.fastfood().items():
        if name.startswith('ff_sign'):
            ts.add(name, GRASS_BOTTOM, P_STREET, g, P_GAS, layer='NORMAL' if name.endswith('0') else 'COVERED')
        else:
            ts.add(name, GRASS_BOTTOM, P_STREET, g, P_GAS, layer='NORMAL' if name[-1] in '01' else 'COVERED')
    return ts


def register_cel_doors(ts):
    """Door animation for the Celadon-style storefront door in each wall colour."""
    C = camel(ts.name)
    door = commercial.PIECES[commercial.DOOR]
    pi = commercial.quad_palette(next(g for g in door['top'] if g not in (None, 'LAWN')))
    commercial.door_anim_png(f'{EXP}/graphics/door_anims/sedgwick_storefront.png', commercial.BASE_PALS[pi])
    path = f'{EXP}/src/field_door.c'
    s = open(path).read()
    decl = 'static const u8 sDoorAnimTiles_SedgwickStorefront[] = INCGFX_U8("graphics/door_anims/sedgwick_storefront.png", ".4bpp");\n'
    if 'sDoorAnimTiles_SedgwickStorefront' not in s:
        anchor = 'static const u8 sDoorAnimTiles_Pallet[] = INCGFX_U8("graphics/door_anims/pallet.png", ".4bpp");\n'
        s = s.replace(anchor, anchor + decl)
    start, end = f'    // Sedgwick storefront doors: {C}\n', f'    // end Sedgwick storefront doors: {C}\n'
    pals, entries = '', ''
    for v, wslot in CEL_SLOTS.items():
        slot = wslot if pi == commercial.WALL_PAL else 8
        pals += f'static const u8 sDoorAnimPalettes_SedgwickStorefront_{camel(v)}[] = {{{", ".join([str(slot)] * 8)}}};\n'
        entries += ('    {\n'
                    f'        .metatileNum = METATILE_{C}_{camel(f"cel_{commercial.DOOR:03x}_{v}")},\n'
                    f'        .tileset = &gTileset_{C},\n'
                    '        .sound = DOOR_SOUND_NORMAL,\n'
                    '        .size = DOOR_SIZE_1x1,\n'
                    '        .tiles = sDoorAnimTiles_SedgwickStorefront,\n'
                    f'        .palettes = sDoorAnimPalettes_SedgwickStorefront_{camel(v)}\n'
                    '    },\n')
    block = start + entries + end
    if start in s:
        a = s.index(start); b = s.index(end) + len(end)
        s = s[:a] + block + s[b:]
    else:
        t = s.index('    {},\n};', s.index('sDoorAnimGraphicsTable[] ='))
        s = s[:t] + block + s[t:]
    pstart, pend = '// Sedgwick storefront door palettes\n', '// end Sedgwick storefront door palettes\n'
    pblock = pstart + pals + pend
    if pstart in s:
        a = s.index(pstart); b = s.index(pend) + len(pend)
        s = s[:a] + pblock + s[b:]
    else:
        anchor = 'static const u8 sDoorAnimPalettes_Pallet[] = {8, 8, 8, 8, 8, 8, 8, 8};\n'
        s = s.replace(anchor, anchor + pblock)
    open(path, 'w').write(s)


def register(ts, ntiles):
    """Add the tileset to the decomp's C tables (idempotent)."""
    C = camel(ts.name)          # SedgwickResidential
    gfx = f'{EXP}/src/data/tilesets/graphics.h'
    mts = f'{EXP}/src/data/tilesets/metatiles.h'
    hdr = f'{EXP}/src/data/tilesets/headers.h'
    tiles_line = (f'const u32 gTilesetTiles_{C}[] = INCGFX_U32("data/tilesets/secondary/{ts.name}/tiles.png", '
                  f'".4bpp.fastSmol", "-num_tiles {ntiles} -Wnum_tiles");')
    s = open(gfx).read()
    if f'gTilesetTiles_{C}[]' in s:
        import re
        s = re.sub(rf'const u32 gTilesetTiles_{C}\[\] = .*?;', tiles_line, s)
    else:
        pals = ''.join(f'    INCGFX_U16("data/tilesets/secondary/{ts.name}/palettes/{i:02d}.pal", ".gbapal"),\n' for i in range(16))
        s += f'\n{tiles_line}\n\nconst u16 gTilesetPalettes_{C}[][16] =\n{{\n{pals}}};\n'
    open(gfx, 'w').write(s)
    s = open(mts).read()
    if f'gMetatiles_{C}[]' not in s:
        s += (f'\nconst u16 gMetatiles_{C}[] = INCBIN_U16("data/tilesets/secondary/{ts.name}/metatiles.bin");\n'
              f'const u16 gMetatileAttributes_{C}[] = INCBIN_U16("data/tilesets/secondary/{ts.name}/metatile_attributes.bin");\n')
        open(mts, 'w').write(s)
    th = f'{EXP}/include/tilesets.h'
    t = open(th).read()
    if f'gTileset_{C};' not in t:
        t = t.replace('extern const struct Tileset gTileset_PalletTown;\n',
                      'extern const struct Tileset gTileset_PalletTown;\n' + f'extern const struct Tileset gTileset_{C};\n')
        open(th, 'w').write(t)
    s = open(hdr).read()
    if f'gTileset_{C} =' not in s:
        s += (f'\nconst struct Tileset gTileset_{C} =\n{{\n    .isCompressed = TRUE,\n    .isSecondary = TRUE,\n'
              f'    .tiles = gTilesetTiles_{C},\n    .palettes = gTilesetPalettes_{C},\n'
              f'    .metatiles = gMetatiles_{C},\n    .metatileAttributes = gMetatileAttributes_{C},\n'
              f'    .callback = NULL,\n}};\n')
        open(hdr, 'w').write(s)


def write_labels(ts, index):
    C = camel(ts.name)
    path = f'{EXP}/include/constants/metatile_labels.h'
    s = open(path).read()
    start, end = f'// gTileset_{C}\n', f'// end gTileset_{C}\n'
    block = start + ''.join(f'#define METATILE_{C}_{camel(n)} 0x{i:03X}\n' for n, i in index.items()) + end
    if start in s:
        a = s.index(start)
        b = s.index(end) + len(end)
        s = s[:a] + block + s[b:]
    else:
        s = s.replace('#endif // GUARD_METATILE_LABELS_H', block + '\n#endif // GUARD_METATILE_LABELS_H')
    open(path, 'w').write(s)


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    for ts, walls in ((residential(), WALL_SLOTS), (rural_ts(), RURAL_WALL)):
        ntiles, index = ts.write()
        register(ts, ntiles)
        write_labels(ts, index)
        register_doors(ts, index, walls)
        json.dump(index, open(os.path.join(here, '..', f'{ts.name}_metatiles.json'), 'w'), indent=1)
        print(f'{ts.name}: {ntiles} tiles, {len(ts.metatiles)} metatiles, palettes {sorted(ts.palettes)}')
    ts = city_ts()
    ntiles, index = ts.write()
    register(ts, ntiles)
    write_labels(ts, index)
    json.dump(index, open(os.path.join(here, '..', f'{ts.name}_metatiles.json'), 'w'), indent=1)
    print(f'{ts.name}: {ntiles} tiles, {len(ts.metatiles)} metatiles, palettes {sorted(ts.palettes)}')
    ts = downtown_ts()
    ntiles, index = ts.write()
    register(ts, ntiles)
    write_labels(ts, index)
    register_downtown_doors(ts)
    json.dump(index, open(os.path.join(here, '..', f'{ts.name}_metatiles.json'), 'w'), indent=1)
    print(f'{ts.name}: {ntiles} tiles, {len(ts.metatiles)} metatiles, palettes {sorted(ts.palettes)}')
    ts = retail_ts()
    ntiles, index = ts.write()
    register(ts, ntiles)
    write_labels(ts, index)
    json.dump(index, open(os.path.join(here, '..', f'{ts.name}_metatiles.json'), 'w'), indent=1)
    print(f'{ts.name}: {ntiles} tiles, {len(ts.metatiles)} metatiles, palettes {sorted(ts.palettes)}')
    ts = commercial_ts()
    ntiles, index = ts.write()
    register(ts, ntiles)
    write_labels(ts, index)
    register_cel_doors(ts)
    json.dump(index, open(os.path.join(here, '..', f'{ts.name}_metatiles.json'), 'w'), indent=1)
    print(f'{ts.name}: {ntiles} tiles, {len(ts.metatiles)} metatiles, palettes {sorted(ts.palettes)}')
