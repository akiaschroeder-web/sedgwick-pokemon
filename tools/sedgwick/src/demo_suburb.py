"""Demo: newer suburb pieces - split-levels, detached garages, sheds, a mobile home
row, the water tower, a bus stop and cars parked along the street."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import Canvas, write_map

W, H = 40, 24
cv = Canvas(W, H)
cv.street_ew(9, 0, W, lanes=2)            # edge 9, asphalt 10-11, edge 12

def drive(h, edge):
    g, d, bottom = h
    if g:
        cv.driveway(g[0], bottom + 1, edge)

# north side: split-levels with attached garages, a ranch with a detached garage and shed
drive(cv.split_level(1, 2, 'brown', 'tan'), 9)
drive(cv.split_level(12, 2, 'charcoal', 'white'), 9)
cv.house(23, 4, 5, 'red', 'white', garage=None, mailbox=(28, 8), address='310 N PRAIRIE LN')
cv.detached_garage(29, 4, 'red', 'white')
cv.driveway(30, 7, 9)
cv.shed(33, 1, 'charcoal', 'tan')
cv.place_piece_grid('water_tower', 37, 1, 2, 4)

# cars parked along the north curb lane
for x, car, f in ((8, 'sedan_red', 'e'), (19, 'pickup_white', 'e'), (24, 'sedan_silver', 'w'), (33, 'pickup_green', 'e')):
    cv.car(x, 10, car, f, curb=True)

# bus stop on the south side
cv.place_piece_grid('bus_shelter', 3, 13, 2, 2)

# mobile home row
for i, (roof, wall) in enumerate((('charcoal', 'white'), ('brown', 'tan'), ('charcoal', 'tan'), ('brown', 'white'))):
    cv.house(8 + i * 8, 16, 6, roof, wall, garage=None, windows=2)

# doors into the batch-5 interiors (interiors.py)
cv.link_doors(0, 0, W - 1, H - 1, 'MAP_SEDGWICK_RANCH_HOUSE_1F')
mid = write_map(cv, 'SedgwickSuburbDemo', 'LAYOUT_SEDGWICK_SUBURB_DEMO', 'Sedgwick suburb demo')
print(mid)
