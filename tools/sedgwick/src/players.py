"""Original Wichita-region player characters (the user's designs), drawn as Gen 3
overworld sprites: 16x32 frames in the order the engine expects
(down, up, left standing; down x2, up x2, left x2 walking; right = left mirrored)."""
from PIL import Image

# ---- palettes (index 0 = transparent background colour)
BOY = {
    '.': (115, 197, 164), 'O': (32, 32, 48),
    's': (255, 213, 180), 'S': (222, 160, 123),
    'h': (172, 115, 65), 'H': (128, 78, 44), 'D': (82, 49, 32),
    'n': (82, 98, 156), 'N': (49, 57, 106), 'M': (32, 36, 72),
    'c': (246, 238, 213), 'C': (205, 190, 156),
    'y': (248, 196, 48), 'Y': (208, 144, 32),
    'k': (176, 150, 106), 'K': (128, 104, 72),
}
GIRL = {
    '.': (115, 197, 164), 'O': (32, 28, 40),
    's': (255, 218, 190), 'S': (226, 164, 132),
    'h': (190, 104, 72), 'H': (144, 66, 48), 'D': (92, 40, 36),
    'n': (186, 70, 80), 'N': (136, 42, 56), 'M': (88, 28, 40),
    'c': (246, 236, 212), 'C': (208, 190, 160),
    'y': (248, 200, 56), 'Y': (208, 150, 40),
    'k': (80, 80, 96), 'K': (48, 46, 58),
}


def frame(head, body, legs, dy=0):
    rows = ['.' * 16] * 32
    art = head + body + legs
    top = 32 - len(art) - 1 + dy
    for i, r in enumerate(art):
        assert len(r) == 16, (r, len(r))
        rows[top + i] = r
    return rows


def sheet(ch):
    H, B, L = ch['head'], ch['body'], ch['legs']
    frames = [
        frame(H['down'], B['down'], L['down'][0], -1),
        frame(H['up'], B['up'], L['up'][0], -1),
        frame(H['left'], B['left'], L['left'][0], -1),
        frame(H['down'], B['down'], L['down'][1]),
        frame(H['down'], B['down'], L['down'][2]),
        frame(H['up'], B['up'], L['up'][1]),
        frame(H['up'], B['up'], L['up'][2]),
        frame(H['left'], B['left'], L['left'][1]),
        frame(H['left'], B['left'], L['left'][2]),
    ]
    return frames


def to_image(frames, pal, scale=1):
    im = Image.new('RGB', (16 * len(frames), 32))
    for f, rows in enumerate(frames):
        for y, r in enumerate(rows):
            for x, c in enumerate(r):
                im.putpixel((f * 16 + x, y), pal[c])
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST) if scale > 1 else im
