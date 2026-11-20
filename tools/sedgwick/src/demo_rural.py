"""Demo farmland map for the rural tileset."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import Canvas, write_map

W, H = 40, 27
cv = Canvas(W, H, tileset='sedgwick_rural')

# K-42 style two-lane highway
for x in range(W):
    cv.set(x, 12, 'hwy_edge_n')
    cv.set(x, 13, 'hwy_center_dash_h' if (x // 2) % 2 else 'hwy_center_h')
    cv.set(x, 14, 'hwy_edge_s')
# section-line gravel road crossing it
for y in range(0, 12):
    cv.set(10, y, 'gravel_edge_w'); cv.set(11, y, 'gravel_edge_e')
cv.set(10, 12, 'hwy_gravel_join_n'); cv.set(11, 12, 'hwy_gravel_join_n')
cv.set(10, 14, 'hwy_gravel_join_s'); cv.set(11, 14, 'hwy_gravel_join_s')
for y in range(15, H):
    cv.set(10, y, 'gravel_edge_w'); cv.set(11, y, 'gravel_edge_e')
# railroad with a grade crossing
for x in range(W):
    cv.set(x, 17, 'rail_h')
cv.set(10, 17, 'rail_x_gravel_h'); cv.set(11, 17, 'rail_x_gravel_h')

# farmstead
cv.house(1, 2, 6, roof='green', wall='white', storeys=2, garage=None, mailbox=(9, 10), address='4410 N 279TH ST W')
cv.farm_building('barn', 13, 3, 5, roof_rows=1)
cv.block('silo', 18, 3)
cv.farm_building('shed', 21, 4, 6, roof_rows=1, door_at=1)
cv.set(14, 10, 'hay_bales', walk=False); cv.set(16, 10, 'hay_bales', walk=False)
# grain elevator by the tracks
cv.block('elevator', 30, 4)

# crops
cv.wheat_field(13, 19, 26, 26)
cv.wheat_field(0, 19, 9, 26, crop='corn')
for y in range(19, 26):
    for x in range(28, 39):
        cv.set(x, y, 'soybeans_n' if y == 19 else 'soybeans' if y < 23 else 'plowed')
for x in (3, 20, 34):
    cv.tall(x, 16, 'power_pole')

mid = write_map(cv, 'SedgwickRuralDemo', 'LAYOUT_SEDGWICK_RURAL_DEMO', 'Sedgwick rural demo',
                secondary='gTileset_SedgwickRural')
print(mid)
