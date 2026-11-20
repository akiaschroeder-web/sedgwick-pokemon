"""Render a decomp map layout to PNG (both games), for style reference."""
import json, struct, sys, os
from PIL import Image
EXP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import load_jasc

def ts_dir(sym):
    # gTileset_General -> general ; gTileset_PalletTown_Frlg -> pallet_town_frlg
    import re
    name=sym.replace('gTileset_','')
    s=re.sub(r'(?<!^)(?<!_)(?=[A-Z])','_',name).lower()
    for base in ('primary','secondary'):
        p=f'{EXP}/data/tilesets/{base}/{s}'
        if os.path.isdir(p): return p
        if os.path.isdir(p+'_frlg'): return p+'_frlg'
    raise FileNotFoundError(s)

def load_tiles(p):
    im=Image.open(p); w,h=im.size; px=im.load()
    return [[[px[tx*8+x,ty*8+y]&15 for x in range(8)] for y in range(8)] for ty in range(h//8) for tx in range(w//8)]

def render_layout(layout_id, out, scale=1):
    L=json.load(open(f'{EXP}/data/layouts/layouts.json'))['layouts']
    lay=[l for l in L if l.get('id')==layout_id][0]
    frlg = 'Frlg' in lay['primary_tileset'] or 'frlg' in lay['primary_tileset'].lower()
    NT,NM,NP = (640,640,7) if frlg else (512,512,6)
    P=ts_dir(lay['primary_tileset']); S=ts_dir(lay['secondary_tileset'])
    tiles=load_tiles(P+'/tiles.png'); tilesS=load_tiles(S+'/tiles.png')
    pals=[load_jasc(f'{P if i<NP else S}/palettes/{i:02d}.pal') for i in range(13)]
    mtP=open(P+'/metatiles.bin','rb').read(); mtS=open(S+'/metatiles.bin','rb').read()
    W,H=lay['width'],lay['height']
    blk=open(f"{EXP}/{lay['blockdata_filepath']}",'rb').read()
    img=Image.new('RGB',(W*16,H*16)); px=img.load()
    for i in range(W*H):
        m=struct.unpack('<H',blk[i*2:i*2+2])[0]&0x3ff
        d,mi=(mtP,m) if m<NM else (mtS,m-NM)
        if mi*16+16>len(d): continue
        e=struct.unpack('<8H',d[mi*16:mi*16+16])
        ox,oy=(i%W)*16,(i//W)*16
        for layer in range(2):
            for q in range(4):
                v=e[layer*4+q]; t,hf,vf,pl=v&0x3ff,v>>10&1,v>>11&1,v>>12
                tl=tiles[t] if t<NT else (tilesS[t-NT] if t-NT<len(tilesS) else None)
                if tl is None or pl>12: continue
                for y in range(8):
                    for x in range(8):
                        c=tl[7-y if vf else y][7-x if hf else x]
                        if layer and c==0: continue
                        px[ox+(q%2)*8+x,oy+(q//2)*8+y]=pals[pl][c]
    if scale!=1: img=img.resize((img.width*scale,img.height*scale),Image.NEAREST)
    img.save(out); return img.size

if __name__=='__main__':
    print(render_layout(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 1))
