"""Demo: downtown blocks with stone towers, mid-rises, an Old Town brick row,
a historic hall and the domed arena."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import Canvas, write_map
import downtown

W, H = 50, 35
cv = Canvas(W, H, tileset='sedgwick_downtown')

# street grid: avenue at rows 15-19 (3 lanes), street at rows 31-34; N-S streets at cols 14 and 32
cv.street_ew(15, 0, W, lanes=3, center=True)
cv.street_ew(31, 0, W, lanes=2)
for x in (14, 32):
    cv.street_ns(x, 0, 15)
    cv.street_ns(x, 20, 31)
    cv.tee_from_north(x, 15, stop=False)
    cv.tee_from_south(x, 19)
    cv.tee_from_north(x, 31, stop=False)
    for y in (16, 17, 18):
        cv.set(x + 1, y, 'asphalt'); cv.set(x + 2, y, 'asphalt')
    cv.set(x + 1, 14, 'crosswalk_ew'); cv.set(x + 2, 14, 'crosswalk_ew')
    cv.set(x + 1, 20, 'crosswalk_ew'); cv.set(x + 2, 20, 'crosswalk_ew')
    cv.tall(x - 1, 14, 'traffic_signal')
    cv.tall(x + 4, 21, 'traffic_signal')

# west block: two stone towers
cv.place_ids(downtown.tower_plan(6, 9), 1, 0, 'rb_{:03x}', doors={downtown.TOWER_DOOR})
cv.place_ids(downtown.tower_plan(5, 6), 8, 4, 'rb_{:03x}', doors={downtown.TOWER_DOOR})
# centre block: historic hall
cv.place_ids(downtown.HALL, 19, 4, 'rb_{:03x}', doors=downtown.HALL_DOORS)
# east block: domed arena
cv.place_ids(downtown.ARENA, 37, 1, 'bf_{:03x}', doors=downtown.ARENA_DOORS)
# south blocks: Old Town brick row, a tan mid-rise, another tower
cv.cel_block(1, 22, 3, storeys=2, color='brick', doors=(0, 2))
cv.place_ids(downtown.tan_plan(9, 2), 19, 23, 'rb_{:03x}', doors={downtown.TAN_DOOR})
# school: tan building with its football field and track
cv.place_ids(downtown.tan_plan(9, 1), 37, 20, 'rb_{:03x}', doors={downtown.TAN_DOOR})
for r in range(5):
    for c in range(8):
        cv.set(37 + c, 26 + r, f'field_{c}{r}')
for x in (5, 24, 44):
    cv.tall(x, 14, 'streetlight')

mid = write_map(cv, 'SedgwickDowntownDemo', 'LAYOUT_SEDGWICK_DOWNTOWN_DEMO', 'Sedgwick downtown demo',
                secondary='gTileset_SedgwickDowntown')
print(mid)
