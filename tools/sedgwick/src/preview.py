import sys
from PIL import Image
from lib import to_image, hflip, vflip
def compose(layout, tiles, pals, scale=3, bg=None):
    """layout: list of rows of entries: None | name | (name,hf,vf); tiles: name->(grid,palkey)"""
    H=len(layout); W=max(len(r) for r in layout)
    im=Image.new('RGBA',(W*16,H*16),(30,30,30,255))
    for r,row in enumerate(layout):
        for c,e in enumerate(row):
            if e is None: continue
            if isinstance(e,str): e=(e,False,False)
            name,hf,vf=e
            g,pk=tiles[name]
            if hf: g=hflip(g)
            if vf: g=vflip(g)
            if bg is not None: im.paste(bg,(c*16,r*16))
            im.alpha_composite(to_image(g,pals[pk]),(c*16,r*16))
    return im.resize((im.width*scale,im.height*scale),Image.NEAREST)
