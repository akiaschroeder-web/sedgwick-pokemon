"""Girl: Leaf with the hat replaced by wavy brown hair, a high ponytail tied with a
yellow bow and a cream streak in the bangs; maroon jacket with a yellow stripe,
dark shorts and socks, maroon boots, cream bag."""
import copy
from players import *

GIRL_PAL = [(115, 197, 164), (198, 116, 78), (255, 206, 168), (222, 148, 115), (142, 68, 50),
            (152, 46, 62), (78, 34, 36), (198, 82, 92), (96, 28, 44),
            (246, 236, 212), (208, 190, 160), (98, 96, 112), (60, 58, 72),
            (248, 200, 56), (208, 150, 40), (0, 0, 0)]

DOWN, UP, LEFT = (0, 3, 4), (1, 5, 6), (2, 7, 8)
HEX = '0123456789abcdef'

# new head tops (rows from 4 above the old hat down to the row above the eyes)
HEAD = {
    'down': [
        "....6dd66dd6....",
        "....6ed64de6....",
        "...6644114466...",
        "...6111444446...",
        "..611444444446..",
        ".66144444444446.",
        ".61444444444416.",
        ".64494444444446.",
        ".64941444414446.",
        ".46942222224464.",
        ".f444222222444f.",
    ],
    'up': [
        "....6dd66dd6....",
        "....6ed64de6....",
        "...6644114466...",
        "...6444114446...",
        "..644441144446..",
        ".61444411444416.",
        ".64444411444446.",
        ".64144411444146.",
        ".64444411444446.",
        ".46444414444464.",
        ".ff4144444414ff.",
    ],
    'left': [
        "..........6dd6..",
        ".........6de146.",
        "....66666666146.",
        "...6111444441466",
        "..61144444444146",
        ".614444444444146",
        ".694444444444146",
        ".649444444444146",
        ".649422444444146",
        "..642224444446f.",
        "..4222222444441f",
    ],
}


def recolor(d, rel, x, v):
    """Leaf's index v at row rel below the top of her hat."""
    if rel <= 8:                                   # hat (only reached in odd poses): hair
        return {9: 4, 10: 1, 12: 4, 11: 1}.get(v, v)
    if rel <= 11:                                  # face, hair at the sides
        return v
    if rel <= 14:                                  # maroon jacket, yellow stripe, cream bag
        v = {6: 5, 5: 7, 7: 7, 13: 9, 14: 10}.get(v, v)
        return 13 if rel == 13 and v in (5, 7) else v
    if rel == 15:                                  # shorts
        return {6: 8, 13: 9, 14: 10}.get(v, v)
    if rel == 16:                                  # black socks
        return {5: 12, 3: 12, 2: 12, 13: 9, 14: 10}.get(v, v)
    return {10: 5, 9: 7, 12: 8, 3: 12, 2: 12, 6: 8}.get(v, v)   # maroon boots


def fallback(fr, y, x, rel):
    return recolor(None, rel, x, fr[y][x]) if rel > 8 else {9: 4, 10: 1, 12: 4, 11: 1}.get(fr[y][x], fr[y][x])


def post(fr, d, flip, ox, oy):
    """Tie the bow on a fallback-edited head: the two bow rows go above its top."""
    top = next((y for y in range(len(fr)) if any(fr[y][ox:ox + 16])), None)
    if top is None or top < 2:
        return
    rows = HEAD[d][:2]
    if flip:
        rows = [r[::-1] for r in rows]
    for i, r in enumerate(rows):
        for x, c in enumerate(r):
            if c != '.' and fr[top - 2 + i][ox + x] == 0:
                fr[top - 2 + i][ox + x] = HEX.index(c)


def walking():
    src = load(f'{PEOPLE}/leaf/green_normal.png')
    out = copy.deepcopy(src)
    for f in range(9):
        fr = out[f]
        t = top_row(src[f])
        key = 'down' if f in DOWN else ('up' if f in UP else 'left')
        for i, r in enumerate(HEAD[key]):
            assert len(r) == 16, (key, i, r)
            fr[t - 2 + i] = [HEX.index(c) if c != '.' else 0 for c in r]
        for y in range(t + 9, 32):
            for x in range(16):
                fr[y][x] = recolor(key, y - t, x, fr[y][x])
    return out


def character():
    src = load(f'{PEOPLE}/leaf/green_normal.png')
    new = walking()
    templates, heads = {}, {}
    for f, d in {0: 'down', 1: 'up', 2: 'left'}.items():
        t = top_row(src[f])
        templates[d] = [src[f][t + r] for r in range(9)]
        heads[d] = ([src[f][t + r] for r in range(-2, 12)], [new[f][t + r] for r in range(-2, 12)])
    return templates, heads, -2, recolor, fallback, post


if __name__ == '__main__':
    import sys
    preview(walking(), GIRL_PAL, 10).save(sys.argv[1])
