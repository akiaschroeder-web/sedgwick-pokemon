"""Demo: airport (runway, taxiway, apron, terminal, control tower, parked aircraft),
an aircraft plant and hangars, and an air base gate."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import Canvas, write_map
import retail

W, H = 44, 30
cv = Canvas(W, H, tileset='sedgwick_aviation')

# runway along the bottom
for x in range(2, W - 2):
    cv.set(x, 25, 'rwy_edge_n'); cv.set(x, 26, 'rwy_center'); cv.set(x, 27, 'rwy_edge_s')
for y in (25, 26, 27):
    cv.set(2, y, 'rwy_threshold'); cv.set(W - 3, y, 'rwy_threshold')
    cv.set(1, y, 'rwy_end_w'); cv.set(W - 2, y, 'rwy_end_e')
# parallel taxiway and connectors
for x in range(4, W - 4):
    cv.set(x, 22, 'twy_h')
for x in (6, 36):
    cv.set(x, 23, 'twy_v'); cv.set(x, 24, 'twy_hold')
# apron in front of the terminal
for y in range(13, 22):
    for x in range(4, 26):
        cv.set(x, y, 'apron')
for x in (8, 15):
    cv.set(x + 2, 13, 'apron_stand')
cv.place_piece_grid('jet', 6, 15, 4, 3)
cv.place_piece_grid('jet', 13, 15, 4, 3)
cv.place_piece_grid('cessna', 20, 17, 2, 2)
cv.place_piece_grid('cessna', 22, 19, 2, 2)

# terminal and control tower
cv.place_ids(retail.bigbox_plan(12), 6, 7, 'bb_{:03x}', doors={retail.DOOR})
cv.place_piece_grid('tower', 20, 6, 2, 5)
for y in range(3, 7):
    for x in range(6, 18):
        cv.set(x, y, 'lot_stalls_n' if y == 4 else 'asphalt')
cv.street_ew(0, 0, 30, lanes=1) if False else None

# aircraft plant (blue roof) and a grey hangar east of the apron
cv.hangar('plant', 28, 1, 12, door_width=4, roof_rows=2)
cv.hangar('hgr', 29, 10, 8, door_width=4, roof_rows=1)
for y in range(17, 22):
    for x in range(28, 40):
        cv.set(x, y, 'apron')

# air base gate on the access road
for y in range(0, 12):
    cv.set(1, y, 'road_edge_w'); cv.set(2, y, 'asphalt'); cv.set(3, y, 'asphalt'); cv.set(4, y, 'road_edge_e')
cv.set(2, 6, 'gate_arm', walk=False)
cv.set(0, 5, 'guard_booth_00', walk=False); cv.set(0, 6, 'guard_booth_01', walk=False)
for y in range(0, 12):
    if y not in (5, 6):
        cv.set(0, y, 'chainlink_v', walk=False)

mid = write_map(cv, 'SedgwickAviationDemo', 'LAYOUT_SEDGWICK_AVIATION_DEMO', 'Sedgwick aviation demo',
                secondary='gTileset_SedgwickAviation')
print(mid)
