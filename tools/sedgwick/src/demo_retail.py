"""Demo: a big-box store with its parking lot, a fast-food restaurant and a gas station."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import Canvas, write_map
import retail

W, H = 40, 26
cv = Canvas(W, H, tileset='sedgwick_retail')
cv.street_ew(20, 0, W, lanes=3, center=True)   # edge 20, asphalt 21-23, edge 24

cv.place_ids(retail.bigbox_plan(12), 2, 1, 'bb_{:03x}', doors={retail.DOOR})
for y in range(6, 20):
    for x in range(1, 16):
        cv.set(x, y, 'asphalt')
for x in range(1, 16):
    cv.set(x, 8, 'lot_stalls_n'); cv.set(x, 11, 'lot_stalls_s'); cv.set(x, 12, 'lot_stalls_n'); cv.set(x, 15, 'lot_stalls_s')
    cv.set(x, 16, 'lot_stalls_n')
for x, y, car, f in ((2, 10, 'sedan_red', 'w'), (6, 10, 'pickup_white', 'e'), (11, 10, 'sedan_black', 'w'), (4, 14, 'sedan_silver', 'e')):
    cv.car(x, y, car, f)
cv.set(8, 20, 'drive_apron_l'); cv.set(9, 20, 'drive_apron_r')

# fast food
cv.place_piece_grid('ff', 19, 12, 4, 3)
for y in range(15, 20):
    for x in range(18, 25):
        cv.set(x, y, 'asphalt')
cv.set(25, 15, 'ff_sign_00', walk=False); cv.set(25, 16, 'ff_sign_01', walk=False)
cv.set(20, 20, 'drive_apron_l'); cv.set(21, 20, 'drive_apron_r')

# gas station
for y in range(13, 20):
    for x in range(28, 39):
        cv.set(x, y, 'gas_pad')
for c in range(5):
    cv.set(30 + c, 14, f'gas_canopy_{c}0'); cv.set(30 + c, 15, f'gas_canopy_{c}1')
    cv.set(30 + c, 16, f'gas_pumps_{c}0', walk=c not in (0, 4))
cv.set(37, 11, 'gas_sign_00', walk=False); cv.set(37, 12, 'gas_sign_01', walk=False)
cv.set(32, 20, 'drive_apron_l'); cv.set(33, 20, 'drive_apron_r')

mid = write_map(cv, 'SedgwickRetailDemo', 'LAYOUT_SEDGWICK_RETAIL_DEMO', 'Sedgwick retail demo',
                secondary='gTileset_SedgwickRetail')
print(mid)
