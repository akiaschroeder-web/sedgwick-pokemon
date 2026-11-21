"""Saffron City (FireRed) city buildings for downtown Wichita, copied from the
original map: cobblestone plaza, green-roof shophouses, yellow flat-roof
apartment blocks, and the Silph Co. tower (any height: its window band repeats).
Pieces keep FRLG's art and colours; build.metro_ts() repacks the colours."""
import orig

SRC = orig.Source('general_frlg', 'saffron_city_frlg', frlg=True)
GROUND = 0x2e9                                   # clean cobblestone

# 4 x 5 shophouse (green roof, yellow walls); the door version swaps the lower rows
HOUSE = [[0x295, 0x296, 0x296, 0x297],
         [0x29d, 0x29e, 0x29e, 0x29f],
         [0x2a5, 0x2a6, 0x28f, 0x2a7],
         [0x298, 0x299, 0x29b, 0x29c],
         [0x2a0, 0x2a1, 0x2a3, 0x2a4]]
HOUSE_DOOR_ROWS = [[0x2be, 0x2bf, 0x2af, 0x29c],
                   [0x2ae, 0x284, 0x28c, 0x2a4]]
HOUSE_DOOR = 0x284

# 5-wide apartment block: roof (3 rows), window rows (repeat), base row
APT_ROOF = [[0x281, 0x282, 0x282, 0x285, 0x286],
            [0x288, 0x289, 0x289, 0x28d, 0x28e],
            [0x290, 0x291, 0x292, 0x293, 0x294]]
APT_WIN = [0x298, 0x299, 0x29a, 0x29b, 0x29c]
APT_BASE = [0x2a0, 0x2a1, 0x2a2, 0x2a3, 0x2a4]

# 9-wide tower: crown (6 rows), window band (repeat), base with the entrance (3 rows)
TOWER_CROWN = [[0x2a8, 0x2a9, 0x2a9, 0x2c5, 0x2c6, 0x2c7, 0x2a9, 0x2a9, 0x2aa],
               [0x2b0, 0x2b1, 0x2b1, 0x2cd, 0x2ce, 0x2cf, 0x2b1, 0x2b1, 0x2b2],
               [0x2b0, 0x2b1, 0x2b1, 0x2cd, 0x2ce, 0x2cf, 0x2b1, 0x2b1, 0x2b2],
               [0x2b0, 0x2b1, 0x2b1, 0x2cd, 0x2ce, 0x2cf, 0x2b1, 0x2b1, 0x2b2],
               [0x2b8, 0x2b9, 0x2b9, 0x2d5, 0x2d6, 0x2d7, 0x2b9, 0x2b9, 0x2ba],
               [0x2c0, 0x2c1, 0x2c2, 0x2c2, 0x2c2, 0x2c2, 0x2c2, 0x2c3, 0x2c4]]
TOWER_WIN = [0x2c8, 0x2c9, 0x2ca, 0x2ca, 0x2ca, 0x2ca, 0x2ca, 0x2cb, 0x2cc]
TOWER_BASE = [[0x2c8, 0x2c9, 0x2ca, 0x2ab, 0x2ac, 0x2ad, 0x2ca, 0x2cb, 0x2cc],
              [0x2d0, 0x2d1, 0x2ca, 0x2b3, 0x2b4, 0x2b5, 0x2ca, 0x2d2, 0x2d3],
              [0x2d8, 0x2d9, 0x2d4, 0x2bb, 0x2bc, 0x2bd, 0x2d4, 0x2da, 0x2db]]
TOWER_DOOR = 0x2b4


def ids():
    s = {GROUND, HOUSE_DOOR}
    for block in (HOUSE, HOUSE_DOOR_ROWS, APT_ROOF, [APT_WIN, APT_BASE], TOWER_CROWN, [TOWER_WIN], TOWER_BASE):
        for row in block:
            s.update(row)
    return sorted(s)


DOORS = {HOUSE_DOOR, TOWER_DOOR}


def house_plan(units, door_unit=0):
    rows = [[] for _ in range(5)]
    for u in range(units):
        for r in range(5):
            src = HOUSE_DOOR_ROWS[r - 3] if (u == door_unit and r >= 3) else HOUSE[r]
            rows[r] += src
    return rows


def apt_plan(units, floors):
    rows = [sum((list(row) for _ in range(units)), []) for row in APT_ROOF]
    rows += [APT_WIN * units for _ in range(max(1, floors))]
    rows.append(APT_BASE * units)
    return rows


def tower_plan(floors):
    return [list(r) for r in TOWER_CROWN] + [list(TOWER_WIN) for _ in range(max(1, floors))] + [list(r) for r in TOWER_BASE]
