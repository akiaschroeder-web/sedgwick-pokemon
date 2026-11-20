"""Place named Sedgwick metatiles on a grid and write a real decomp map.

This is the seed of the GIS map generator: it works in terms of street pieces,
houses and props by name, and handles collision, elevation, mailboxes and their
address signs."""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

EXP = lib.EXP
HERE = os.path.dirname(os.path.abspath(__file__))
WALK = 0x3000      # elevation 3, passable
BLOCK = 0x0400     # collision 1


class Canvas:
    def __init__(self, w, h, tileset='sedgwick_residential'):
        self.w, self.h = w, h
        self.ids = json.load(open(os.path.join(HERE, '..', f'{tileset}_metatiles.json')))
        self.ids['water'] = 0x170          # Hoenn calm water from the primary tileset
        self.cells = [[('lawn', True)] * w for _ in range(h)]
        self.signs = []   # (x, y, text)

    def set(self, x, y, name, walk=True):
        if 0 <= x < self.w and 0 <= y < self.h:
            assert name in self.ids, name
            self.cells[y][x] = (name, walk)

    def get(self, x, y):
        return self.cells[y][x][0]

    # ---- streets
    def street_ew(self, y, x0, x1, lanes=2, center=False):
        """E-W street: sidewalk edge at row y, asphalt rows y+1..y+lanes, edge at y+lanes+1."""
        for x in range(x0, x1):
            self.set(x, y, 'road_edge_n')
            for i in range(lanes):
                name = 'asphalt'
                if center and lanes % 2 == 1 and i == lanes // 2:
                    name = 'center_yellow_h'
                self.set(x, y + 1 + i, name)
            self.set(x, y + lanes + 1, 'road_edge_s')

    def street_ns(self, x, y0, y1):
        for y in range(y0, y1):
            self.set(x, y, 'road_edge_w')
            self.set(x + 1, y, 'asphalt')
            self.set(x + 2, y, 'asphalt')
            self.set(x + 3, y, 'road_edge_e')

    def tee_from_south(self, x, y_edge):
        """N-S street (columns x..x+3) meets an E-W street whose south edge is row y_edge."""
        self.set(x, y_edge, 'block_corner_sw')
        self.set(x + 1, y_edge, 'asphalt')
        self.set(x + 2, y_edge, 'asphalt')
        self.set(x + 3, y_edge, 'block_corner_se')

    def tee_from_north(self, x, y_edge, stop=True):
        """N-S street meets an E-W street whose north edge is row y_edge."""
        self.set(x, y_edge, 'block_corner_nw')
        self.set(x + 1, y_edge, 'asphalt')
        self.set(x + 2, y_edge, 'asphalt')
        self.set(x + 3, y_edge, 'block_corner_ne')
        if stop:
            self.set(x + 1, y_edge - 1, 'stop_bar_h')
            self.set(x + 2, y_edge - 1, 'stop_bar_h')

    def culdesac(self, x, y):
        """6x6 bulb; its stub (columns x+1..x+4) opens north at row y."""
        import math
        for r in range(6):
            for c in range(6):
                name = f'culdesac_{c}{r}'
                if name in self.ids:
                    self.set(x + c, y + r, name)
                else:
                    px, py = c * 16 + 8, r * 16 + 8
                    inside = math.hypot(px - 48, py - 52) < 40 or (py < 52 and abs(px - 48) < 20)
                    self.set(x + c, y + r, 'asphalt' if inside else 'lawn')

    # ---- houses
    def house(self, x, y, width, roof='red', wall='white', storeys=1, garage='r', windows=2,
              mailbox=None, address=None):
        """Pallet-style house. Returns (garage_columns, door_xy, bottom_row)."""
        import house2
        rows = house2.plan(width, storeys, garage, windows)
        garage_cols, door = [], None
        for r, row in enumerate(rows):
            for c, piece in enumerate(row):
                variant = roof if piece.startswith('roof') else wall
                walk = piece == 'wall_door'
                self.set(x + c, y + r, f'h_{piece}_{variant}', walk=walk)
                if piece == 'wall_gar_a':
                    garage_cols.append(x + c)
                if walk:
                    door = (x + c, y + r)
        if mailbox is not None:
            mx, my = mailbox
            self.set(mx, my, 'mailbox', walk=False)
            if address:
                self.signs.append((mx, my, address))
        return garage_cols, door, y + len(rows) - 1

    def church(self, x, y, width=8, roof='charcoal', wall='white'):
        """Two-storey Pallet-style body with a centred steeple; (x, y) is the top of
        the steeple, the house roof starts two rows lower. Returns the door position."""
        import house2
        rows = house2.plan(width, 2, None, windows=width)
        # centre the door under the steeple, windows either side
        inner = width - 2
        door_col = width // 2 - 1
        lower = ['wall_l'] + ['wall_sid'] * inner + ['wall_r']
        lower[door_col] = 'wall_door'
        i = 1
        while i + 1 < door_col:
            lower[i], lower[i + 1] = 'wall_win_a', 'wall_win_b'
            i += 2
        i = door_col + 1
        while i + 1 < width - 1:
            lower[i], lower[i + 1] = 'wall_win_a', 'wall_win_b'
            i += 2
        rows[-1] = lower
        door = None
        for r, row in enumerate(rows):
            for c, piece in enumerate(row):
                variant = roof if piece.startswith('roof') else wall
                walk = piece == 'wall_door'
                self.set(x + c, y + 2 + r, f'h_{piece}_{variant}', walk=walk)
                if walk:
                    door = (x + c, y + 2 + r)
        sx = x + width // 2 - 1
        for r in range(4):
            for c in range(2):
                self.set(sx + c, y + r, f'church_steeple_{c}{r}_{roof}', walk=False)
        return door

    def driveway(self, x, y_top, y_street_edge):
        for y in range(y_top, y_street_edge):
            self.set(x, y, 'drive_l')
            self.set(x + 1, y, 'drive_r')
        self.set(x, y_street_edge, 'drive_apron_l')
        self.set(x + 1, y_street_edge, 'drive_apron_r')

    def tall(self, x, y, base):
        """Two-tile prop: base_top at y-1, base_bottom at y."""
        self.set(x, y - 1, base + '_top', walk=False)
        self.set(x, y, base + '_bottom', walk=False)

    def wheat_field(self, x0, y0, x1, y1, crop='wheat'):
        for y in range(y0, y1):
            for x in range(x0, x1):
                n, s, w, e = y == y0, y == y1 - 1, x == x0, x == x1 - 1
                tag = ('n' if n else 's' if s else '') + ('w' if w else 'e' if e else '')
                self.set(x, y, crop + '_' + tag if tag else crop)

    def farm_building(self, kind, x, y, width, roof_rows=1, tall=True, door_at=None):
        """kind 'barn' or 'shed' (Vermilion-style metal roof). Returns the bottom row."""
        import farm2
        rows = farm2.plan(width, roof_rows, door_at, tall)
        for r, row in enumerate(rows):
            for c, piece in enumerate(row):
                self.set(x + c, y + r, f'{kind}_{piece}', walk=False)
        return y + len(rows) - 1

    def cel_block(self, x, y, units, storeys=2, color='mint', ac=(), doors=(0,)):
        """Celadon-style flat-roofed building. Returns (bottom_row, door_positions)."""
        import commercial
        rows = commercial.plan(units, storeys, ac, doors)
        doors_xy = []
        for r, row in enumerate(rows):
            for c, m in enumerate(row):
                walk = m == commercial.DOOR
                self.set(x + c, y + r, f'cel_{m:03x}_{color}', walk=walk)
                if walk:
                    doors_xy.append((x + c, y + r))
        return y + len(rows) - 1, doors_xy

    def place_ids(self, rows, x, y, fmt, doors=()):
        """Place a grid of source metatile ids (None = leave the ground) using a name
        format such as 'rb_{:03x}'. Door ids are walkable; everything else blocks."""
        for r, row in enumerate(rows):
            for c, m in enumerate(row):
                if m is None:
                    continue
                self.set(x + c, y + r, fmt.format(m), walk=m in doors)
        return y + len(rows) - 1

    def block(self, prefix, x, y, walk=False):
        """Place a multi-tile building whose pieces are named prefix_<col><row>."""
        for name in self.ids:
            if name.startswith(prefix + '_') and len(name) == len(prefix) + 3 and name[-2:].isdigit():
                c, r = int(name[-2]), int(name[-1])
                self.set(x + c, y + r, name, walk=walk)

    # ---- output
    def blockdata(self):
        out = bytearray()
        for row in self.cells:
            for name, walk in row:
                if name == 'water':
                    out += struct.pack('<H', self.ids[name] | 0x0000)   # surfable water: elevation 0
                else:
                    out += struct.pack('<H', self.ids[name] | (WALK if walk else BLOCK))
        return bytes(out)


def write_map(cv, map_name, layout_id, title, group='gMapGroup_Sedgwick', secondary='gTileset_SedgwickResidential'):
    ldir = f'{EXP}/data/layouts/{map_name}'
    os.makedirs(ldir, exist_ok=True)
    open(f'{ldir}/map.bin', 'wb').write(cv.blockdata())
    lawn = struct.pack('<H', cv.ids['lawn'] | WALK)
    open(f'{ldir}/border.bin', 'wb').write(lawn * 4)

    L = json.load(open(f'{EXP}/data/layouts/layouts.json'))
    entry = {'id': layout_id, 'name': f'{map_name}_Layout', 'width': cv.w, 'height': cv.h,
             'primary_tileset': 'gTileset_General', 'secondary_tileset': secondary,
             'border_filepath': f'data/layouts/{map_name}/border.bin',
             'blockdata_filepath': f'data/layouts/{map_name}/map.bin', 'layout_version': 'emerald'}
    L['layouts'] = [l for l in L['layouts'] if l.get('id') != layout_id] + [entry]
    json.dump(L, open(f'{EXP}/data/layouts/layouts.json', 'w'), indent=2)
    open(f'{EXP}/data/layouts/layouts.json', 'a').write('\n')

    mdir = f'{EXP}/data/maps/{map_name}'
    os.makedirs(mdir, exist_ok=True)
    bg = []
    scripts = [f'{map_name}_MapScripts::\n\t.byte 0\n']
    for i, (x, y, text) in enumerate(cv.signs):
        label = f'{map_name}_EventScript_Mailbox{i + 1}'
        tlabel = f'{map_name}_Text_Mailbox{i + 1}'
        bg.append({'type': 'sign', 'x': x, 'y': y, 'elevation': 0,
                   'player_facing_dir': 'BG_EVENT_PLAYER_FACING_ANY', 'script': label})
        scripts.append(f'\n{label}::\n\tmsgbox {tlabel}, MSGBOX_SIGN\n\tend\n')
        scripts.append(f'\n{tlabel}:\n\t.string "{text}$"\n')
    mid = 'MAP_' + ''.join('_' + c if c.isupper() and i else c for i, c in enumerate(map_name)).upper()
    mj = {'id': mid, 'name': map_name, 'layout': layout_id, 'music': 'MUS_LITTLEROOT',
          'region': 'REGION_HOENN', 'region_map_section': 'MAPSEC_LITTLEROOT_TOWN',
          'requires_flash': False, 'weather': 'WEATHER_SUNNY', 'map_type': 'MAP_TYPE_TOWN',
          'allow_cycling': True, 'allow_escaping': False, 'allow_running': True,
          'show_map_name': True, 'battle_scene': 'MAP_BATTLE_SCENE_NORMAL', 'connections': None,
          'object_events': [], 'warp_events': [], 'coord_events': [], 'bg_events': bg}
    json.dump(mj, open(f'{mdir}/map.json', 'w'), indent=2)
    open(f'{mdir}/scripts.inc', 'w').write(''.join(scripts))

    G = json.load(open(f'{EXP}/data/maps/map_groups.json'))
    if group not in G['group_order']:
        G['group_order'].append(group)
        G[group] = []
    if map_name not in G[group]:
        G[group].append(map_name)
    json.dump(G, open(f'{EXP}/data/maps/map_groups.json', 'w'), indent=2)
    open(f'{EXP}/data/maps/map_groups.json', 'a').write('\n')

    es = open(f'{EXP}/data/event_scripts.s').read()
    inc = f'\t.include "data/maps/{map_name}/scripts.inc"\n'
    if inc not in es:
        anchor = '\t.include "data/maps/Underwater_Route125/scripts.inc"\n'
        es = es.replace(anchor, anchor + inc)
        open(f'{EXP}/data/event_scripts.s', 'w').write(es)
    return mid
