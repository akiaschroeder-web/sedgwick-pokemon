# Sedgwick County asset tools

Python scripts that generate the Sedgwick tilesets, door animations and demo maps
in this repository. Requires Python 3 and Pillow (`pip install pillow`).

    cd tools/sedgwick/src
    python3 build.py              # rebuild all tilesets, labels, door table entries
    python3 demo_neighborhood.py  # rebuild a demo map (also demo_rural / demo_commercial / demo_city)
    python3 maprender.py LAYOUT_SEDGWICK_DEMO out.png 2   # render any layout to a PNG

Run `build.py` before the demo scripts: map blocks refer to metatile ids, and ids
shift when tiles are added to a tileset.

| Script | Builds |
| --- | --- |
| `street.py` | streets, sidewalks, curbs, lane paint, diagonals, bends, cul-de-sacs, driveways |
| `house2.py` | houses re-indexed from FireRed's Pallet Town house (any roof x any siding) |
| `farm2.py` | barn, machine shed, silo, grain elevator (Vermilion warehouse-roof style) |
| `commercial.py`, `gas.py` | Celadon-style storefronts/apartments/offices, parking, gas station |
| `civic.py` | river banks, bridges, interstate, parks, confluence plaza and landmark slot |
| `wheat.py`, `rural.py` | wheat/corn/soy fields, gravel roads, two-lane highway, railroad |
| `props.py` | mailboxes, signs, signals, lights, poles, fences, hydrant |
| `orig.py` | helpers for reusing original FRLG/Emerald building art |
| `compose.py` | places named pieces on a grid and writes decomp maps |

Your own landmark sprite goes in `custom/landmark.png` (see `custom/README.txt`).
The `*_metatiles.json` files map piece names to metatile ids for the map generator.
