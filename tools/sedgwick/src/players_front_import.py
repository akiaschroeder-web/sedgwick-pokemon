"""Front sprites from the artist's pixel art (custom/source/{boy,girl}_front_art.png).

The art is drawn on a ~16 px grid at about 95 px tall; Gen 3 trainer pictures are 64x64,
so each figure is cut out, resampled onto a grid that fits it in 62 rows (outlines win
any cell they cover a fair share of), re-outlined, and reduced to 15 colours."""
import os
from collections import Counter, deque
from PIL import Image
from lib import EXP

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'custom', 'source')
BG = (115, 197, 164)


def cutout(path):
    im = Image.open(path).convert('RGBA')
    w, h = im.size
    px = im.load()
    fig = [[px[x, y][3] > 128 for x in range(w)] for y in range(h)]
    if all(px[0, 0][3] > 128 for _ in (0,)):                 # opaque: flood the light checkerboard away
        def bg(c):
            r, g, b, _ = c
            return min(r, g, b) > 185 and max(r, g, b) - min(r, g, b) < 18
        seen = [[False] * w for _ in range(h)]
        q = deque((x, y) for x in range(w) for y in (0, h - 1))
        q.extend((x, y) for y in range(h) for x in (0, w - 1))
        while q:
            x, y = q.popleft()
            if seen[y][x] or not bg(px[x, y]):
                continue
            seen[y][x] = True
            fig[y][x] = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx]:
                    q.append((nx, ny))
    ys = [y for y in range(h) if any(fig[y])]
    xs = [x for x in range(w) if any(fig[y][x] for y in ys)]
    return im, fig, (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def resample(im, fig, box, rows=62):
    """Each target pixel takes the most common colour in the middle of its source cell,
    which keeps the artist's flat colours and hard edges; then the silhouette is re-outlined."""
    px = im.load()
    x0, y0, x1, y1 = box
    s = (y1 - y0) / rows
    cols = round((x1 - x0) / s)
    out = [[None] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            cx, cy, h = x0 + (c + .5) * s, y0 + (r + .5) * s, s * 0.3
            xs = range(int(cx - h), int(cx + h) + 1)
            ys = range(int(cy - h), int(cy + h) + 1)
            cells = [px[x, y][:3] for y in ys for x in xs
                     if 0 <= x < im.width and 0 <= y < im.height and fig[y][x]]
            if len(cells) < len(xs) * len(ys) * 0.5:
                continue
            k = Counter((p[0] // 10, p[1] // 10, p[2] // 10) for p in cells).most_common(1)[0][0]
            sel = [p for p in cells if (p[0] // 10, p[1] // 10, p[2] // 10) == k]
            out[r][c] = tuple(sum(p[i] for p in sel) // len(sel) for i in range(3))
    for r in range(rows):
        for c in range(cols):
            if out[r][c] and any(not (0 <= r + dr < rows and 0 <= c + dc < cols) or out[r + dr][c + dc] is None
                                 for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[r][c] = (0, 0, 0)
    return out


def to_sprite(grid, colours=15):
    rows, cols = len(grid), len(grid[0])
    pts = [grid[r][c] for r in range(rows) for c in range(cols) if grid[r][c]]
    sample = Image.new('RGB', (len(pts), 1))
    sample.putdata(pts)
    q = sample.quantize(colours, method=Image.Quantize.MEDIANCUT, kmeans=8)
    pal = sorted({tuple(q.getpalette()[i * 3:i * 3 + 3]) for i in range(colours)}, key=sum)
    full = [BG] + pal + [(0, 0, 0)] * (15 - len(pal))
    g = [[0] * 64 for _ in range(64)]
    ox, oy = (64 - cols) // 2, 64 - rows - 1
    for r in range(rows):
        for c in range(cols):
            p = grid[r][c]
            if p:
                g[oy + r][ox + c] = min(range(1, 1 + len(pal)),
                                        key=lambda k: sum((p[j] - full[k][j]) ** 2 for j in range(3)))
    return g, full


def build(who):
    im, fig, box = cutout(os.path.join(SRC, f'{who}_front_art.png'))
    return to_sprite(resample(im, fig, box))


def save(g, pal, path):
    im = Image.new('P', (64, 64))
    im.putpalette([c for col in pal for c in col])
    for y in range(64):
        for x in range(64):
            im.putpixel((x, y), g[y][x])
    im.save(path)


def install():
    """Write graphics/trainers/front_pics/sedgwick_{boy,girl}.png and use them for the player
    (trainer card, intro, link battles) in place of Brendan/May's front pictures."""
    for who in ('boy', 'girl'):
        g, pal = build(who)
        save(g, pal, f'{EXP}/graphics/trainers/front_pics/sedgwick_{who}.png')
    import players_build
    tr = f'{EXP}/src/data/graphics/trainers.h'
    s = open(tr).read()
    decl = ''.join(f'const u32 gTrainerFrontPic_Sedgwick{C}[] = INCGFX_U32("graphics/trainers/front_pics/sedgwick_{w}.png", ".4bpp.smol");\n'
                   f'const u16 gTrainerPalette_Sedgwick{C}[] = INCGFX_U16("graphics/trainers/front_pics/sedgwick_{w}.png", ".gbapal");\n'
                   for w, C in (('boy', 'Boy'), ('girl', 'Girl')))
    B, E = '// sedgwick front pics begin\n', '// sedgwick front pics end\n'
    if B in s:
        s = s[:s.index(B)] + B + decl + E + s[s.index(E) + len(E):]
    else:
        anchor = 'const u16 gTrainerPalette_Red[] = INCGFX_U16("graphics/trainers/front_pics/red.png", ".gbapal");\n'
        s = s.replace(anchor, anchor + B + decl + E)
    s = s.replace('.frontPic = TRAINER_FRONT_PIC(gTrainerFrontPic_Brendan, gTrainerPalette_Brendan),',
                  '.frontPic = TRAINER_FRONT_PIC(gTrainerFrontPic_SedgwickBoy, gTrainerPalette_SedgwickBoy),', 1)
    s = s.replace('.frontPic = TRAINER_FRONT_PIC(gTrainerFrontPic_May, gTrainerPalette_May),',
                  '.frontPic = TRAINER_FRONT_PIC(gTrainerFrontPic_SedgwickGirl, gTrainerPalette_SedgwickGirl),', 1)
    open(tr, 'w').write(s)


if __name__ == '__main__':
    import sys
    outs = []
    for who in ('boy', 'girl'):
        g, pal = build(who)
        im = Image.new('RGB', (64, 64))
        for y in range(64):
            for x in range(64):
                im.putpixel((x, y), pal[g[y][x]])
        outs.append(im.resize((448, 448), Image.NEAREST))
    o = Image.new('RGB', (906, 448), (30, 30, 36))
    o.paste(outs[0], (0, 0)); o.paste(outs[1], (458, 0))
    o.save(sys.argv[1])
