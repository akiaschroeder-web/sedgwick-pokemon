"""Demo: floodway canal, a lake with a dock, a golf hole, a cemetery, the botanical
conservatory, a zoo gate and a windbreak of Hoenn trees."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import Canvas, write_map

W, H = 40, 28
cv = Canvas(W, H, tileset='sedgwick_city')

# floodway ("Big Ditch"): concrete channel running north-south
for y in range(H):
    cv.set(1, y, 'canal_w')
    cv.set(2, y, 'water'); cv.set(3, y, 'water')
    cv.set(4, y, 'canal_e')

# lake with banks and a dock
x0, y0, x1, y1 = 7, 2, 17, 9
for x in range(x0 + 1, x1):
    cv.set(x, y0, 'bank_n'); cv.set(x, y1, 'bank_s')
for y in range(y0 + 1, y1):
    cv.set(x0, y, 'bank_w'); cv.set(x1, y, 'bank_e')
    for x in range(x0 + 1, x1):
        cv.set(x, y, 'water')
cv.set(x0, y0, 'bank_in_nw'); cv.set(x1, y0, 'bank_in_ne'); cv.set(x0, y1, 'bank_in_sw'); cv.set(x1, y1, 'bank_in_se')
for y in range(6, 9):
    cv.set(12, y, 'dock_ns')
cv.set(12, 5, 'dock_end')
cv.set(12, 9, 'dock_ns')

# golf hole: tee, fairway, bunker, green with flag
cv.set(21, 3, 'tee_box')
for x in range(22, 33):
    for y in (2, 3, 4):
        cv.set(x, y, 'fairway')
cv.set(29, 5, 'bunker')
cv.set(33, 3, 'golf_green'); cv.set(33, 3, 'golf_flag')

# cemetery with an iron fence
for x in range(20, 32):
    cv.set(x, 11, 'iron_fence', walk=False)
for r, y in enumerate(range(13, 18, 2)):
    for x in range(21, 31, 2):
        cv.set(x, y, 'cross_stone' if (x + r) % 4 == 1 else 'headstone', walk=False)

# botanical conservatory and zoo gate
cv.place_piece_grid('conservatory', 7, 13, 4, 3)
cv.place_piece_grid('zoo_gate', 34, 13, 3, 2)

# windbreak along the south edge
cv.tree_row(6, 38, 22)

mid = write_map(cv, 'SedgwickNatureDemo', 'LAYOUT_SEDGWICK_NATURE_DEMO', 'Sedgwick nature demo',
                secondary='gTileset_SedgwickCity')
print(mid)
