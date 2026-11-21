"""Boy: Red with the cap turned backwards, brown hair, navy jacket with a yellow
stripe over a yellow shirt, cream hood, khaki cargo pants, dark bag."""
import copy
from players import *

DOWN, UP, LEFT = (0, 3, 4), (1, 5, 6), (2, 7, 8)


def walking():
    src = load(f'{PEOPLE}/red/red_normal.png')
    out = copy.deepcopy(src)
    cap_back = [src[1][12 + r][:] for r in range(8)]      # back of Red's cap: strap and opening
    cap_front = [src[0][12 + r][:] for r in range(8)]     # front of Red's cap: brim
    for f in range(9):
        fr = out[f]
        t = top_row(src[f])
        if f in DOWN:
            for r in range(7):
                fr[t + r] = cap_back[r][:]
            row = cap_back[7][:]
            fr[t + 7] = [1 if v == 15 and 6 <= x <= 9 else v for x, v in enumerate(row)]   # hair through the strap
        elif f in UP:
            for r in range(8):
                fr[t + r] = cap_front[r][:]
        else:
            for r in range(8):                             # side: brim points backwards
                fr[t + r] = src[f][t + r][::-1]
        for y in range(32):
            rel = y - t
            for x in range(16):
                v = fr[y][x]
                if rel <= 7:                               # cap: navy, cream front panel, navy brim
                    if f in UP:
                        v = ({8: 6, 6: 1, 11: 9}.get(v, v) if 5 <= x <= 10 else {8: 6, 6: 1}.get(v, v)) if rel <= 5 else {8: 6, 6: 1, 9: 12, 10: 11}.get(v, v)
                    elif f in DOWN:
                        v = {8: 6, 6: 1}.get(v, v)
                    else:
                        v = {8: 6, 6: 1, 9: 12, 10: 11}.get(v, v)
                        if v == 11 and x >= 9 and rel <= 4:
                            v = 9
                elif rel <= 10:                            # hair and face
                    v = {6: 1, 8: 4}.get(v, v)
                elif rel <= 14:                            # jacket, shirt, bag
                    v = {8: 6, 13: 4, 14: 15}.get(v, v)    # bag yellow -> dark brown
                    centre = 5 <= x <= 10
                    if f in DOWN and centre and v in (15, 9, 10) and rel in (12, 13):
                        v = 13                             # yellow shirt
                    elif f in DOWN and centre and v in (9, 10) and rel == 14:
                        v = 12                             # jacket hem
                    elif v in (2, 3) and rel <= 12:
                        v = 13 if rel == 12 else (12 if v == 3 else 11)   # sleeves, yellow stripe
                    elif f in UP and rel == 12 and v in (12, 6, 11):
                        v = 13                             # stripe across the back
                    elif f in LEFT and rel == 12 and v in (12, 11):
                        v = 13
                elif rel <= 16:                            # pants
                    v = {7: 7, 6: 8, 5: 5, 13: 4, 14: 15}.get(v, v)
                else:                                      # shoes
                    v = {6: 12, 7: 11, 13: 4, 14: 15}.get(v, v)
                fr[y][x] = v
    return out


if __name__ == '__main__':
    import sys
    fr = walking()
    preview(fr, BOY_PAL).save(sys.argv[1])
