"""Demo commercial strip: storefronts, apartments, parking, a gas station and signals."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import Canvas, write_map

W, H = 40, 26
cv = Canvas(W, H, tileset='sedgwick_commercial')

# Arterial (E-W) and a cross street (N-S) with a signalised intersection
cv.street_ew(14, 0, W, lanes=3, center=True)        # edge 14, asphalt 15-17, edge 18
cv.street_ns(24, 0, 14)
cv.street_ns(24, 19, H)
cv.tee_from_north(24, 14, stop=False)
cv.tee_from_south(24, 18)
for y in (15, 16, 17):
    cv.set(25, y, 'asphalt'); cv.set(26, y, 'asphalt')
cv.set(25, 13, 'crosswalk_ew'); cv.set(26, 13, 'crosswalk_ew')
cv.set(25, 19, 'crosswalk_ew'); cv.set(26, 19, 'crosswalk_ew')
cv.tall(23, 13, 'traffic_signal')
cv.tall(28, 20, 'traffic_signal')

# Strip mall with its parking lot facing the arterial
bottom, doors = cv.cel_block(1, 1, 5, storeys=1, color='beige', ac=(1, 3), doors=(0, 1, 2, 3, 4))
for y in range(bottom + 1, 14):
    for x in range(1, 21):
        cv.set(x, y, 'asphalt')
for x in range(1, 21):
    cv.set(x, bottom + 3, 'lot_stalls_n')
    cv.set(x, bottom + 6, 'lot_stalls_s')
    cv.set(x, bottom + 7, 'lot_stalls_n')
cv.set(10, 14, 'drive_apron_l'); cv.set(11, 14, 'drive_apron_r')

# Apartments east of the cross street
cv.cel_block(29, 0, 2, storeys=2, color='mint', ac=(0,), doors=(1,))
cv.cel_block(29, 7, 2, storeys=1, color='brick', doors=(0,)) if False else None

# Gas station south-west of the intersection
for y in range(20, 25):
    for x in range(11, 21):
        cv.set(x, y, 'gas_pad')
for c in range(5):
    cv.set(12 + c, 20, f'gas_canopy_{c}0')
    cv.set(12 + c, 21, f'gas_canopy_{c}1')
    cv.set(12 + c, 22, f'gas_pumps_{c}0', walk=(c in (0, 4)) is False and False)
cv.set(12, 22, 'gas_pumps_00', walk=False); cv.set(16, 22, 'gas_pumps_40', walk=False)
for x in range(11, 21):
    cv.set(x, 19, 'asphalt')
cv.set(10, 21, 'gas_sign_00', walk=False); cv.set(10, 22, 'gas_sign_01', walk=False)
# office building beside the gas station
cv.cel_block(1, 20, 2, storeys=1, color='brick', doors=(1,))

# Second office block across the cross street
cv.cel_block(30, 20, 2, storeys=1, color='mint', ac=(1,), doors=(0,))

# doors into the batch-5 interiors (interiors.py)
cv.link_doors(0, 19, 6, 26, 'MAP_SEDGWICK_GAS_STATION')
mid = write_map(cv, 'SedgwickCommercialDemo', 'LAYOUT_SEDGWICK_COMMERCIAL_DEMO', 'Sedgwick commercial demo',
                secondary='gTileset_SedgwickCommercial')
print(mid)
