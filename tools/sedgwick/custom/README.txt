Put your landmark sprite here as landmark.png:
  - transparent background (PNG with alpha), 1 image pixel = 1 game pixel
  - up to 64 px wide and 128 px tall (statue and rock together)
Then run:  python3 src/build.py  and  python3 src/demo_city.py
The sprite is centred on the confluence plaza with its base on the plaza centre.
Colours are split into a warm palette and a stone palette (15 colours each);
tiles above the base are drawn over the player, so they can walk behind it.
