"""A hand-laid demo neighbourhood that exercises every residential piece.
Writes MAP_SEDGWICK_DEMO into the expansion checkout so it opens in Porymap."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import Canvas, write_map

W, H = 38, 30
cv = Canvas(W, H)

# --- streets
cv.street_ew(7, 0, W, lanes=2)                    # Elm St: edge 7, asphalt 8-9, edge 10
cv.street_ew(18, 0, W, lanes=3, center=True)      # Central Ave: edge 18, asphalt 19-21, edge 22
cv.street_ns(17, 11, 18)                          # Oak St
cv.tee_from_south(17, 10)
cv.tee_from_north(17, 18)
cv.set(18, 10, 'crosswalk_ew'); cv.set(19, 10, 'crosswalk_ew')
cv.culdesac(29, 11)                               # Maple Ct
cv.tee_from_south(30, 10)

def drive(h, y_edge):
    g, d, bottom = h
    if g:
        cv.driveway(g[0], bottom + 1, y_edge)

# --- north side of Elm St
drive(cv.house(1, 3, 6, 'red', 'white', garage='r', mailbox=(0, 6), address='1204 ELM ST'), 7)
drive(cv.house(8, 3, 6, 'brown', 'tan', garage='l', mailbox=(14, 6), address='1212 ELM ST'), 7)
drive(cv.house(16, 1, 6, 'charcoal', 'white', storeys=2, garage='r', mailbox=(15, 6), address='1220 ELM ST'), 7)
cv.house(24, 3, 5, 'red', 'tan', garage=None, mailbox=(29, 6), address='1228 ELM ST')
drive(cv.house(31, 3, 6, 'brown', 'white', garage='l', mailbox=(37, 6), address='1236 ELM ST'), 7)

# --- facing Central Ave
drive(cv.house(1, 13, 7, 'charcoal', 'tan', garage='r', mailbox=(0, 17), address='1201 CENTRAL AVE'), 18)
cv.house(9, 12, 6, 'red', 'white', storeys=2, garage=None, mailbox=(15, 17), address='1209 CENTRAL AVE')
cv.house(22, 14, 5, 'brown', 'tan', garage=None, mailbox=(21, 17), address='1221 CENTRAL AVE')

# --- street furniture
cv.tall(7, 6, 'streetlight')
cv.tall(22, 6, 'streetlight')
cv.tall(16, 17, 'stop_sign')
cv.set(30, 6, 'hydrant', walk=False)
for x in range(1, 7):
    cv.set(x, 1, 'chainlink_h', walk=False)
for x in range(8, 14):
    cv.set(x, 1, 'privacy_h', walk=False)
for x in (4, 10, 26, 32):
    cv.tall(x, 25, 'power_pole')
cv.church(14, 23, width=8, roof='charcoal', wall='white')

# doors into the batch-5 interiors (interiors.py)
cv.link_doors(12, 20, 23, H - 1, 'MAP_SEDGWICK_CHURCH')
cv.link_doors(0, 0, W - 1, 19, 'MAP_SEDGWICK_RANCH_HOUSE_1F')
mid = write_map(cv, 'SedgwickDemo', 'LAYOUT_SEDGWICK_DEMO', 'Sedgwick demo')
print(mid, W, H, len(cv.signs), 'mailboxes')
