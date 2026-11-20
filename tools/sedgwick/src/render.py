import sys, struct
from PIL import Image, ImageDraw
def load_pal(p):
    L=open(p).read().split('\n')[3:19]
    return [tuple(int(x) for x in l.split()) for l in L]
def load_tiles(png):
    im=Image.open(png); w,h=im.size; px=im.load()
    tiles=[]
    for ty in range(h//8):
        for tx in range(w//8):
            tiles.append([[px[tx*8+x,ty*8+y]&15 for x in range(8)] for y in range(8)])
    return tiles
def render(primary, secondary, out, mt_dir, start=0, count=None, cols=16, scale=2, label=True, ntiles_p=512, npals_p=6):
    tilesP=load_tiles(primary+'/tiles.png'); pals=[]
    for i in range(16):
        src = primary if i<npals_p else (secondary or primary)
        pals.append(load_pal(f'{src}/palettes/{i:02d}.pal'))
    tilesS=load_tiles(secondary+'/tiles.png') if secondary else []
    data=open(mt_dir+'/metatiles.bin','rb').read()
    n=len(data)//16; count=count or n-start
    rows=(count+cols-1)//cols
    img=Image.new('RGB',(cols*16,rows*16),(255,0,255))
    px=img.load()
    for m in range(start,start+count):
        e=struct.unpack('<8H',data[m*16:m*16+16])
        ox=((m-start)%cols)*16; oy=((m-start)//cols)*16
        for layer in range(2):
            for q in range(4):
                v=e[layer*4+q]; t=v&0x3ff; hf=v>>10&1; vf=v>>11&1; pl=v>>12
                tl = tilesP[t] if t<ntiles_p else (tilesS[t-ntiles_p] if t-ntiles_p<len(tilesS) else None)
                if tl is None: continue
                for y in range(8):
                    for x in range(8):
                        c=tl[7-y if vf else y][7-x if hf else x]
                        if layer==1 and c==0: continue
                        px[ox+(q%2)*8+x, oy+(q//2)*8+y]=pals[pl][c]
    img=img.resize((img.width*scale,img.height*scale),Image.NEAREST)
    if label:
        d=ImageDraw.Draw(img)
        for m in range(start,start+count):
            ox=((m-start)%cols)*16*scale; oy=((m-start)//cols)*16*scale
            d.text((ox+1,oy),hex(m)[2:],fill=(255,255,255))
    img.save(out)
if __name__=='__main__':
    a=sys.argv
    render(a[1], a[2] if a[2]!='-' else None, a[3], a[4], int(a[5]), int(a[6]), ntiles_p=int(a[7]), npals_p=int(a[8]))
