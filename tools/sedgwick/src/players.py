"""Wichita-region player sprites, made by editing FireRed/LeafGreen's Red and Leaf.

Each sheet is read as palette indices, edited (cap turned backwards, hair, clothes)
and written with the character's own 16-colour palette."""
import os
from PIL import Image
from lib import EXP

PEOPLE = f'{EXP}/graphics/object_events/pics/people'

BOY_PAL = [(115, 197, 164), (160, 104, 60), (255, 206, 160), (222, 148, 115), (112, 62, 48),
           (176, 150, 106), (40, 44, 88), (210, 190, 146), (128, 104, 72),
           (246, 238, 213), (205, 190, 156), (92, 108, 170), (56, 64, 118),
           (248, 196, 48), (200, 140, 32), (0, 0, 0)]


def load(path):
    im = Image.open(path)
    w, h = im.size
    px = im.load()
    return [[[px[f * 16 + x, y] for x in range(16)] for y in range(32)] for f in range(w // 16)]


def top_row(fr):
    return next(y for y in range(32) if any(fr[y]))


def save(frames, pal, path):
    im = Image.new('P', (16 * len(frames), 32))
    im.putpalette([c for col in pal for c in col])
    for f, fr in enumerate(frames):
        for y in range(32):
            for x in range(16):
                im.putpixel((f * 16 + x, y), fr[y][x])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def preview(frames, pal, scale=8):
    im = Image.new('RGB', (16 * len(frames), 32))
    for f, fr in enumerate(frames):
        for y in range(32):
            for x in range(16):
                im.putpixel((f * 16 + x, y), pal[fr[y][x]])
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


# ---------------------------------------------------------------- applying a character to any sheet
SHEETS = ('normal', 'bike', 'surf', 'surf_run', 'fish', 'item', 'vs_seeker_bike')


def frames_of(path, fw):
    im = Image.open(path)
    w, h = im.size
    px = im.load()
    return [[[px[f * fw + x, y] for x in range(fw)] for y in range(h)] for f in range(w // fw)]


def find_head(fr, templates, rows):
    """Best (score, dir, flipped, ox, oy) of a head template (rows x 16) inside frame fr."""
    H, W = len(fr), len(fr[0])
    best = (0, None, False, 0, 0)
    for d, tmpl in templates.items():
        for flip in (False, True):
            t = [r[::-1] for r in tmpl] if flip else tmpl
            pts = [(x, y, t[y][x]) for y in range(rows) for x in range(16) if t[y][x]]
            for oy in range(0, H - rows + 1):
                for ox in range(0, W - 15):
                    hit = 0
                    for x, y, v in pts:
                        if fr[oy + y][ox + x] == v:
                            hit += 1
                    s = hit / len(pts)
                    if s > best[0]:
                        best = (s, d, flip, ox, oy)
    return best


def apply_character(src_sheet, fw, templates, heads, head_off, recolor, match_rows=8, fallback=None, post=None):
    """templates: dir -> source head rows (rel 0..match_rows-1, 16 wide);
    heads: dir -> (source rows, new rows) for rel head_off..; recolor(dir, rel, xr, v) -> v."""
    out = []
    for fr in src_sheet:
        fr = [row[:] for row in fr]
        s, d, flip, ox, oy = find_head(fr, templates, match_rows)
        if s < 0.2:
            out.append(fr)              # no person found: leave the frame alone
            continue
        if s < 0.75 and fallback:       # head drawn in an unusual pose: edit it row by row
            orig = [row[:] for row in fr]
            for y in range(len(fr)):
                for X in range(len(fr[0])):
                    if orig[y][X]:
                        xr = X - ox
                        fr[y][X] = fallback(orig, y, X, y - oy) if y - oy < match_rows else recolor(d, y - oy, 15 - xr if flip else xr, orig[y][X])
            if post:
                post(fr, d, flip, ox, oy)
            out.append(fr)
            continue
        srows, nrows = heads[d]
        if flip:
            srows = [r[::-1] for r in srows]
            nrows = [r[::-1] for r in nrows]
        for y in range(max(0, oy + head_off - 4), max(0, oy + head_off)):   # hair flicked up when running
            if sum(1 for x in range(16) if fr[y][ox + x]) >= 4:          # (a fishing rod is thinner)
                for x in range(16):
                    fr[y][ox + x] = 0
        orig = [row[:] for row in fr]
        for i, (sr, nr) in enumerate(zip(srows, nrows)):
            y = oy + head_off + i
            if not 0 <= y < len(fr):
                continue
            for x in range(16):
                X = ox + x
                if sr[x] == 0 and orig[y][X] != 0:
                    continue                    # something else overlaps the head here (rod, arm)
                if sr[x] == 0 and nr[x] == 0:
                    continue
                fr[y][X] = nr[x]
        done = {(oy + head_off + i, ox + x) for i, (sr, nr) in enumerate(zip(srows, nrows))
                for x in range(16) if 0 <= oy + head_off + i < len(fr) and not (sr[x] == 0 and orig[oy + head_off + i][ox + x] != 0)
                and not (sr[x] == 0 and nr[x] == 0)}
        for y in range(len(fr)):
            for X in range(len(fr[0])):
                if (y, X) in done or not orig[y][X]:
                    continue
                xr = X - ox
                if flip:
                    xr = 15 - xr
                fr[y][X] = recolor(d, y - oy, xr, orig[y][X])
        out.append(fr)
    return out


def save_frames(frames, pal, path):
    fw = len(frames[0][0])
    h = len(frames[0])
    im = Image.new('P', (fw * len(frames), h))
    im.putpalette([c for col in pal for c in col])
    for f, fr in enumerate(frames):
        for y in range(h):
            for x in range(fw):
                im.putpixel((f * fw + x, y), fr[y][x])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def preview_frames(frames, pal, scale=4):
    fw = len(frames[0][0]); h = len(frames[0])
    im = Image.new('RGB', (fw * len(frames), h))
    for f, fr in enumerate(frames):
        for y in range(h):
            for x in range(fw):
                im.putpixel((f * fw + x, y), pal[fr[y][x]])
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)
