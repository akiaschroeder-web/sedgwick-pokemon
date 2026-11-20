"""Interiors (batch 5): Hoenn and FireRed indoor rooms, reused and rearranged.

Each room starts from a vanilla layout's block data (metatile + collision +
elevation) and is edited with small grid operations. Exit mats warp to
MAP_DYNAMIC, so one interior map serves every building of its kind: the game
remembers which door the player came in by and sends them back to it.

Run after build.py; then rerun the demos so their doors point here."""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import EXP

GROUP = 'gMapGroup_SedgwickIndoor'
COLLIDE = 0x0C00


def _layouts():
    return {l['id']: l for l in json.load(open(f'{EXP}/data/layouts/layouts.json'))['layouts'] if 'id' in l}


class Room:
    def __init__(self, layout_id):
        l = _layouts()[layout_id]
        self.src = l
        self.w, self.h = l['width'], l['height']
        d = open(f"{EXP}/{l['blockdata_filepath']}", 'rb').read()
        v = struct.unpack(f'<{len(d) // 2}H', d)
        self.g = [list(v[y * self.w:(y + 1) * self.w]) for y in range(self.h)]
        self.warps = []          # (x, y, dest_map, dest_warp_id)
        self.bg = []             # (x, y, text) signs

    # ---- grid edits (cells are raw u16 block values)
    def get(self, x, y):
        return self.g[y][x]

    def set(self, x, y, v):
        self.g[y][x] = v

    def block(self, x, y, solid=True):
        self.g[y][x] = (self.g[y][x] & ~COLLIDE) | (0x0400 if solid else 0)

    def copy_rect(self, sx, sy, w, h, dx, dy):
        part = [row[sx:sx + w] for row in self.g[sy:sy + h]]
        for r, row in enumerate(part):
            self.g[dy + r][dx:dx + w] = row

    def insert_cols(self, at, cols):
        """Insert copies of the source columns `cols` (list of indices) before column `at`."""
        for row in self.g:
            add = [row[c] for c in cols]
            row[at:at] = add
        self.w += len(cols)

    def insert_rows(self, at, rows):
        self.g[at:at] = rows
        self.h += len(rows)

    # ---- output
    def write(self, name, title, music='MUS_LITTLEROOT'):
        lid = 'LAYOUT_' + _const(name)
        ldir = f'{EXP}/data/layouts/{name}'
        os.makedirs(ldir, exist_ok=True)
        open(f'{ldir}/map.bin', 'wb').write(b''.join(struct.pack('<H', v) for row in self.g for v in row))
        open(f'{ldir}/border.bin', 'wb').write(open(f"{EXP}/{self.src['border_filepath']}", 'rb').read())
        L = json.load(open(f'{EXP}/data/layouts/layouts.json'))
        entry = {'id': lid, 'name': f'{name}_Layout', 'width': self.w, 'height': self.h,
                 'primary_tileset': self.src['primary_tileset'], 'secondary_tileset': self.src['secondary_tileset'],
                 'border_filepath': f'data/layouts/{name}/border.bin',
                 'blockdata_filepath': f'data/layouts/{name}/map.bin',
                 'layout_version': self.src.get('layout_version', 'emerald')}
        for k in ('border_width', 'border_height'):
            if k in self.src:
                entry[k] = self.src[k]
        L['layouts'] = [l for l in L['layouts'] if l.get('id') != lid] + [entry]
        json.dump(L, open(f'{EXP}/data/layouts/layouts.json', 'w'), indent=2)
        open(f'{EXP}/data/layouts/layouts.json', 'a').write('\n')

        mdir = f'{EXP}/data/maps/{name}'
        os.makedirs(mdir, exist_ok=True)
        scripts = [f'{name}_MapScripts::\n\t.byte 0\n']
        bg = []
        for i, (x, y, text) in enumerate(self.bg):
            label, tl = f'{name}_EventScript_Sign{i + 1}', f'{name}_Text_Sign{i + 1}'
            bg.append({'type': 'sign', 'x': x, 'y': y, 'elevation': 0,
                       'player_facing_dir': 'BG_EVENT_PLAYER_FACING_NORTH', 'script': label})
            scripts.append(f'\n{label}::\n\tmsgbox {tl}, MSGBOX_SIGN\n\tend\n\n{tl}:\n\t.string "{text}$"\n')
        mj = {'id': 'MAP_' + _const(name), 'name': name, 'layout': lid, 'music': music,
              'region': 'REGION_HOENN', 'region_map_section': 'MAPSEC_LITTLEROOT_TOWN',
              'requires_flash': False, 'weather': 'WEATHER_NONE', 'map_type': 'MAP_TYPE_INDOOR',
              'allow_cycling': False, 'allow_escaping': False, 'allow_running': False,
              'show_map_name': False, 'battle_scene': 'MAP_BATTLE_SCENE_NORMAL', 'connections': None,
              'object_events': [],
              'warp_events': [{'x': x, 'y': y, 'elevation': 0, 'dest_map': m, 'dest_warp_id': str(w)}
                              for x, y, m, w in self.warps],
              'coord_events': [], 'bg_events': bg}
        json.dump(mj, open(f'{mdir}/map.json', 'w'), indent=2)
        open(f'{mdir}/scripts.inc', 'w').write(''.join(scripts))
        G = json.load(open(f'{EXP}/data/maps/map_groups.json'))
        if GROUP not in G['group_order']:
            G['group_order'].append(GROUP)
            G[GROUP] = []
        if name not in G[GROUP]:
            G[GROUP].append(name)
        json.dump(G, open(f'{EXP}/data/maps/map_groups.json', 'w'), indent=2)
        open(f'{EXP}/data/maps/map_groups.json', 'a').write('\n')
        es = open(f'{EXP}/data/event_scripts.s').read()
        inc = f'\t.include "data/maps/{name}/scripts.inc"\n'
        if inc not in es:
            anchor = '\t.include "data/maps/Underwater_Route125/scripts.inc"\n'
            es = es.replace(anchor, anchor + inc)
            open(f'{EXP}/data/event_scripts.s', 'w').write(es)
        return mj['id']


def _const(name):
    out = ''
    for i, c in enumerate(name):
        if c.isupper() and i and name[i - 1] != '_' and not name[i - 1].isupper():
            out += '_'
        out += c
    return out.upper().replace('B1_F', 'B1F').replace('1_F', '1F')


def exits(room, xs, y):
    """Door mats: every mat tile goes back to whichever door the player came in by."""
    for x in xs:
        room.warps.append((x, y, 'MAP_DYNAMIC', 'WARP_ID_DYNAMIC'))


# ---------------------------------------------------------------- the rooms
def ranch_house():
    """Ranch house main floor (Brendan's house) with stairs down to a finished basement."""
    up = Room('LAYOUT_LITTLEROOT_TOWN_BRENDANS_HOUSE_1F')
    exits(up, (8, 9), 8)
    up.warps.append((8, 2, 'MAP_SEDGWICK_RANCH_HOUSE_B1F', 0))       # warp 2: stairs
    up.write('SedgwickRanchHouse_1F', 'Ranch house')
    down = Room('LAYOUT_SOOTOPOLIS_CITY_MYSTERY_EVENTS_HOUSE_B1F')
    down.warps.append((3, 1, 'MAP_SEDGWICK_RANCH_HOUSE_1F', 2))
    down.write('SedgwickRanchHouse_B1F', 'Basement')


def farmhouse():
    r = Room('LAYOUT_HOUSE2_FRLG')
    exits(r, (3, 4, 5), 7)
    r.write('SedgwickFarmhouse', 'Farmhouse')


def gas_station():
    """Convenience store: Hoenn Poke Mart as-is (counter, coolers, snack aisles)."""
    r = Room('LAYOUT_MART')
    exits(r, (3, 4), 7)
    r.write('SedgwickGasStation', 'Gas station', music='MUS_POKE_MART')


def big_box_store():
    """FireRed Mart widened into a big-box store: the shelf pair (columns 7-9) repeated
    into five aisles, and a second run of shelving inserted below the first."""
    r = Room('LAYOUT_MART_FRLG')
    for _ in range(4):
        r.insert_cols(10, [7, 8, 9])
    W = r.w
    extra = []
    for sy in (3, 4, 5, 6):
        row = list(r.g[sy])
        row[0] = r.g[5][0]                                # left wall edge
        for x in range(1, 7):
            row[x] = r.g[5][5]                            # plain floor
        extra.append(row)
    r.insert_rows(7, extra)
    exits(r, (3, 4, 5), r.h - 2)
    r.write('SedgwickBigBoxStore', 'Big-box store', music='MUS_POKE_MART')


def school():
    r = Room('LAYOUT_RUSTBORO_CITY_POKEMON_SCHOOL')
    exits(r, (5, 6), 10)
    r.write('SedgwickSchool', 'School', music='MUS_SCHOOL')


def church():
    """Sanctuary from FireRed's Viridian school: long table as the altar, rows of
    benches as pews either side of a centre aisle, the mat at the back."""
    r = Room('LAYOUT_VIRIDIAN_CITY_SCHOOL')
    g = r.g
    wall_top = (g[0][0], g[0][1], g[0][3])               # window band: left, middle, right
    wall_mid = (g[1][0], g[1][1], g[1][3])
    shade = (g[2][0], g[2][1], g[2][3])
    for x in range(r.w):
        k = 0 if x == 0 else (2 if x == r.w - 1 else 1)
        g[0][x], g[1][x], g[2][x] = wall_top[k], wall_mid[k], shade[k]
    floor, edge = g[4][1], g[4][0]
    table_top, table_bot = (g[3][4], g[3][5]), (g[4][4], g[4][5])
    stool = g[5][4]
    body = []
    for y in range(3, 3 + 9):
        body.append([edge] + [floor] * (r.w - 2) + [g[4][r.w - 1]])
    body[0][4], body[0][5] = table_top                    # altar
    body[1][4], body[1][5] = table_bot
    for y in (3, 5, 7):                                   # pews
        for x in (1, 2, 3, 6, 7, 8):
            body[y][x] = stool | 0x0400
    g[3:7] = body
    r.h = len(g)
    exits(r, (3, 4, 5), r.h - 2)
    r.write('SedgwickChurch', 'Church', music='MUS_LITTLEROOT')


def hangar():
    """Hangar / aircraft plant floor from Stern's Shipyard; the stairs are walled over."""
    r = Room('LAYOUT_SLATEPORT_CITY_STERNS_SHIPYARD_1F')
    for x in (2, 3, 4):
        r.set(x, 0, r.get(5, 0)); r.set(x, 1, r.get(5, 1)); r.set(x, 2, r.get(5, 2))
    exits(r, (2, 3), 14)
    r.write('SedgwickHangar', 'Hangar')


ROOMS = (ranch_house, farmhouse, gas_station, big_box_store, school, church, hangar)

if __name__ == '__main__':
    for fn in ROOMS:
        fn()
        print(fn.__name__)
