"""Boy: Red with the cap turned backwards, brown hair, navy jacket with a yellow
stripe over a yellow shirt, cream hood, khaki cargo pants, dark bag."""
import copy
from players import *

DOWN, UP, LEFT = (0, 3, 4), (1, 5, 6), (2, 7, 8)
DIRS = {0: 'down', 1: 'up', 2: 'left'}
HEAD_ROWS = 11      # cap (0-7), hair and face (8-10)


def recolor(d, rel, x, v):
    """Red's index v at row rel below the cap top, column x in his 16-wide box."""
    if rel <= 7:                                   # cap: navy, cream front panel, navy brim
        if d == 'up':
            if rel <= 5:
                return {8: 6, 6: 1, 11: 9 if 5 <= x <= 10 else 11}.get(v, v)
            return {8: 6, 6: 1, 9: 12, 10: 11}.get(v, v)
        if d == 'down':
            return {8: 6, 6: 1}.get(v, v)
        v = {8: 6, 6: 1, 9: 12, 10: 11}.get(v, v)
        return 9 if v == 11 and x >= 9 and rel <= 4 else v
    if rel <= 10:                                  # hair and face
        return {6: 1, 8: 4}.get(v, v)
    if rel <= 14:                                  # jacket, shirt, bag
        v = {8: 6, 13: 4, 14: 15}.get(v, v)        # yellow bag -> dark brown
        centre = 5 <= x <= 10
        if d == 'down' and centre and v in (15, 9, 10) and rel in (12, 13):
            return 13                              # yellow shirt
        if d == 'down' and centre and v in (9, 10) and rel == 14:
            return 12                              # jacket hem
        if v in (2, 3) and rel <= 12:
            return 13 if rel == 12 else (12 if v == 3 else 11)   # long sleeves, yellow stripe
        if d in ('up', 'left') and rel == 12 and v in (12, 6, 11):
            return 13
        return v
    if rel <= 16:                                  # khaki pants
        return {6: 8, 13: 4, 14: 15}.get(v, v)
    return {6: 12, 7: 11, 13: 4, 14: 15}.get(v, v)  # navy shoes


def walking():
    src = load(f'{PEOPLE}/red/red_normal.png')
    out = copy.deepcopy(src)
    cap_back = [src[1][12 + r][:] for r in range(8)]      # back of Red's cap: strap and opening
    cap_front = [src[0][12 + r][:] for r in range(8)]     # front of Red's cap: brim
    for f in range(9):
        fr = out[f]
        t = top_row(src[f])
        d = 'down' if f in DOWN else ('up' if f in UP else 'left')
        if d == 'down':
            for r in range(7):
                fr[t + r] = cap_back[r][:]
            fr[t + 7] = [1 if v == 15 and 6 <= x <= 9 else v for x, v in enumerate(cap_back[7])]
        elif d == 'up':
            for r in range(8):
                fr[t + r] = cap_front[r][:]
        else:
            for r in range(8):
                fr[t + r] = src[f][t + r][::-1]
        for y in range(32):
            for x in range(16):
                fr[y][x] = recolor(d, y - t, x, fr[y][x])
    return out


def fallback(fr, y, x, rel):
    """Cap pixel in a pose with no walking-frame match: brim rows become hair (cap worn
    backwards), crown rows go navy."""
    row = fr[y]
    brim = sum(v in (9, 10) for v in row) >= 3 and sum(v in (9, 10) for v in row) >= sum(v in (11, 12) for v in row)
    v = row[x]
    if brim:
        return {9: 1, 10: 4, 6: 1, 8: 6}.get(v, v)
    return {9: 12, 10: 11, 8: 6, 6: 1}.get(v, v)


def character():
    """(templates, heads, head_off, recolor) for apply_character."""
    src = load(f'{PEOPLE}/red/red_normal.png')
    new = walking()
    templates, heads = {}, {}
    for f, d in DIRS.items():
        t = top_row(src[f])
        templates[d] = [src[f][t + r] for r in range(8)]
        heads[d] = ([src[f][t + r] for r in range(HEAD_ROWS)], [new[f][t + r] for r in range(HEAD_ROWS)])
    return templates, heads, 0, recolor, fallback, None


if __name__ == '__main__':
    import sys
    preview(walking(), BOY_PAL).save(sys.argv[1])
