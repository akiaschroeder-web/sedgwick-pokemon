"""Demo: the river confluence with a park, plaza and monument, a road bridge and the interstate."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import Canvas, write_map

W, H = 40, 32
cv = Canvas(W, H, tileset='sedgwick_city')

# Arkansas River (E-W): bank row 17, water 18-21, bank row 22
for x in range(W):
    cv.set(x, 17, 'bank_n')
    for y in range(18, 22):
        cv.set(x, y, 'water')
    cv.set(x, 22, 'bank_s')
# Little Arkansas (N-S) flowing in from the north: bank col 8, water 9-10, bank col 11
for y in range(0, 17):
    cv.set(8, y, 'bank_w'); cv.set(9, y, 'water'); cv.set(10, y, 'water'); cv.set(11, y, 'bank_e')
cv.set(8, 17, 'bank_out_nw'); cv.set(9, 17, 'water'); cv.set(10, 17, 'water'); cv.set(11, 17, 'bank_out_ne')

# footbridges onto the point
for x in range(8, 12):
    cv.set(x, 12, 'footbridge_ew')
for y in range(17, 23):
    cv.set(14, y, 'footbridge_ns')

# Confluence plaza and monument on the point between the rivers
for r in range(6):
    for c in range(6):
        cv.set(12 + c, 10 + r, f'plaza_{c}{r}')
# the project's own landmark sprite, centred on the plaza (see custom/README.txt)
import json
lay_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'custom', 'landmark_layout.json')
if os.path.exists(lay_path) and 'landmark_0_5' in cv.ids or any(k.startswith('landmark_') for k in cv.ids):
    lay = json.load(open(lay_path))
    ox, oy = lay['origin']
    for name in lay['pieces']:
        _, c, r = name.split('_')
        x, y = 12 + ox + int(c), 10 + oy + int(r)
        cv.set(x, y, name, walk=(oy + int(r)) < 2)
for x in (12, 17):
    cv.set(x, 16, 'bench', walk=False) if False else None

# park west of the Little Arkansas
for c in range(4):
    for r in range(3):
        cv.set(1 + c, 1 + r, f'pavilion_{c}{r}', walk=r < 2)
cv.set(2, 3, 'picnic_table', walk=False) if False else None
cv.set(1, 6, 'playground_slide', walk=False)
cv.set(3, 6, 'swings', walk=False); cv.set(4, 6, 'swings', walk=False)
cv.set(6, 6, 'bench', walk=False); cv.set(6, 4, 'trash_can', walk=False)
cv.set(6, 2, 'picnic_table', walk=False)
for r in range(4):
    for c in range(4):
        cv.set(2 + c, 10 + r, f'diamond_{c}{r}')

# McLean Blvd-style street and its bridge over the Arkansas
cv.street_ns(26, 0, 17)
for y in range(17, 23):
    cv.set(26, y, 'bridge_ns_w'); cv.set(27, y, 'asphalt'); cv.set(28, y, 'asphalt'); cv.set(29, y, 'bridge_ns_e')
cv.street_ns(26, 23, 24)
for y in (5, 11):
    cv.tall(25, y, 'streetlight')

# Interstate along the south edge
rows = ['i_shoulder_n', 'i_lane_dash', 'i_lane', 'i_median_n', 'i_median_s', 'i_lane_dash', 'i_lane', 'i_shoulder_s']
for i, name in enumerate(rows):
    for x in range(W):
        cv.set(x, 24 + i, name)

mid = write_map(cv, 'SedgwickCityDemo', 'LAYOUT_SEDGWICK_CITY_DEMO', 'Sedgwick city demo',
                secondary='gTileset_SedgwickCity')
print(mid)
