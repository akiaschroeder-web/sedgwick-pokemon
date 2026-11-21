"""Write the Wichita-region player sprites and hook them into the game (idempotent).

Overworld: graphics/object_events/pics/people/sedgwick/{boy,girl}/*.png
Palettes:  graphics/object_events/palettes/sedgwick_{boy,girl}.pal
Battle:    graphics/trainers/back_pics/sedgwick_{boy,girl}.png

The player avatar (walk, run, bike, surf, fish, field move) and the battle back
sprite then use these for both genders; underwater keeps Brendan/May's sprites."""
import os, re
import players, players_boy, players_girl, players_back
from lib import EXP, jasc

PEOPLE = players.PEOPLE
OUT = f'{PEOPLE}/sedgwick'
SHEETS = {'surf_run': 16, 'bike': 32, 'fish': 32, 'item': 16}
CHARS = {
    'boy': dict(mod=players_boy, pal=players.BOY_PAL, src=('red', 'red'), rows=8, back='red', C='Boy'),
    'girl': dict(mod=players_girl, pal=players_girl.GIRL_PAL, src=('leaf', 'green'), rows=9, back='leaf', C='Girl'),
}


def sprites():
    for who, c in CHARS.items():
        mod, pal = c['mod'], c['pal']
        tm, hd, off, rc, fb, po = mod.character()
        players.save_frames(mod.walking(), pal, f'{OUT}/{who}/normal.png')
        for sheet, fw in SHEETS.items():
            src = players.frames_of(f'{PEOPLE}/{c["src"][0]}/{c["src"][1]}_{sheet}.png', fw)
            out = players.apply_character(src, fw, tm, hd, off, rc, match_rows=c['rows'], fallback=fb, post=po)
            players.save_frames(out, pal, f'{OUT}/{who}/{sheet}.png')
        open(f'{EXP}/graphics/object_events/palettes/sedgwick_{who}.pal', 'w').write(jasc(pal))
        backs = [getattr(players_back, who)(g) for g in players_back.frames(c['back'])]
        players_back.save(backs, players_back.BOY_BACK_PAL if who == 'boy' else pal,
                          f'{EXP}/graphics/trainers/back_pics/sedgwick_{who}.png')


# ---------------------------------------------------------------- C hookup
BEGIN, END = '// sedgwick players begin\n', '// sedgwick players end\n'


def block(path, text, anchor=None, before=False):
    """Insert (or replace) our marked block; at `anchor` if given, else at end of file."""
    s = open(path).read()
    body = BEGIN + text + END
    if BEGIN in s:
        a = s.index(BEGIN)
        b = s.index(END) + len(END)
        s = s[:a] + body + s[b:]
    elif anchor:
        assert anchor in s, (path, anchor)
        i = s.index(anchor) + (0 if before else len(anchor))
        s = s[:i] + body + s[i:]
    else:
        s = s + '\n' + body
    open(path, 'w').write(s)


KINDS = ('NORMAL', 'BIKE', 'SURF', 'FIELD_MOVE', 'FISH')


def hookup():
    E = EXP
    # constants: object ids, palette tags, avatar choice
    ids = ''.join(f'    OBJ_EVENT_GFX_SEDGWICK_{c["C"].upper()}_{k},\n' for c in CHARS.values() for k in KINDS)
    block(f'{E}/include/constants/event_objects.h', ids, anchor='    NUM_OBJ_EVENT_GFX,\n', before=True)
    s = open(f'{E}/include/constants/event_objects.h').read()
    if 'OBJ_EVENT_PAL_TAG_SEDGWICK_BOY' not in s:
        s = s.replace('#define OBJ_EVENT_PAL_TAG_SS_ANNE                 0x1133\n',
                      '#define OBJ_EVENT_PAL_TAG_SS_ANNE                 0x1133\n'
                      '#define OBJ_EVENT_PAL_TAG_SEDGWICK_BOY           0x1134\n'
                      '#define OBJ_EVENT_PAL_TAG_SEDGWICK_GIRL          0x1135\n')
    # the avatar: our characters (underwater keeps Brendan/May)
    def avatar(m):
        gender, state, frlg, emerald = m.group(1), m.group(2), m.group(3), m.group(4)
        who = 'BOY' if gender == 'MALE' else 'GIRL'
        kind = {'NORMAL': 'NORMAL', 'MACH_BIKE': 'BIKE', 'ACRO_BIKE': 'BIKE', 'SURFING': 'SURF',
                'FIELD_MOVE': 'FIELD_MOVE', 'FISHING': 'FISH', 'WATERING': 'FIELD_MOVE',
                'VSSEEKER': 'FIELD_MOVE'}.get(state)
        if kind is None:
            return m.group(0)
        return (f'#define PLAYER_AVATAR_GFX_{gender}_{state} (SEDGWICK_PLAYERS ? OBJ_EVENT_GFX_SEDGWICK_{who}_{kind} : '
                f'(IS_FRLG ? {frlg} : {emerald}))')
    s = re.sub(r'#define PLAYER_AVATAR_GFX_(MALE|FEMALE)_([A-Z_]+?) +\(IS_FRLG \? (\w+) *: (\w+)\)', avatar, s)
    if '#define SEDGWICK_PLAYERS' not in s:
        s = s.replace('#include "constants/map_event_ids.h"\n',
                      '#include "constants/map_event_ids.h"\n\n'
                      '// Wichita-region protagonists (tools/sedgwick/src/players_build.py)\n'
                      '#define SEDGWICK_PLAYERS TRUE\n', 1)
    open(f'{E}/include/constants/event_objects.h', 'w').write(s)

    # graphics
    P = 'graphics/object_events/pics/people/sedgwick'
    gfx = ''
    for who, c in CHARS.items():
        C = c['C']
        gfx += (f'const u16 gObjectEventPic_Sedgwick{C}Normal[] = INCGFX_U16("{P}/{who}/normal.png", ".4bpp", "-mwidth 2 -mheight 4");\n'
                f'const u16 gObjectEventPic_Sedgwick{C}SurfRun[] = INCGFX_U16("{P}/{who}/surf_run.png", ".4bpp", "-mwidth 2 -mheight 4");\n'
                f'const u16 gObjectEventPic_Sedgwick{C}Bike[] = INCGFX_U16("{P}/{who}/bike.png", ".4bpp", "-mwidth 4 -mheight 4");\n'
                f'const u16 gObjectEventPic_Sedgwick{C}Fish[] = INCGFX_U16("{P}/{who}/fish.png", ".4bpp", "-mwidth 4 -mheight 4");\n'
                f'const u16 gObjectEventPic_Sedgwick{C}Item[] = INCGFX_U16("{P}/{who}/item.png", ".4bpp", "-mwidth 2 -mheight 4");\n'
                f'const u16 gObjectEventPal_Sedgwick{C}[] = INCGFX_U16("graphics/object_events/palettes/sedgwick_{who}.pal", ".gbapal");\n')
    block(f'{E}/src/data/object_events/object_event_graphics.h', gfx)

    pics = ''
    for c in CHARS.values():
        C = c['C']
        walk = ''.join(f'    overworld_frame(gObjectEventPic_Sedgwick{C}Normal, 2, 4, {i}),\n' for i in range(9))
        run = ''.join(f'    overworld_frame(gObjectEventPic_Sedgwick{C}SurfRun, 2, 4, {i}),\n' for i in range(3, 14))
        surf = ''.join(f'    overworld_frame(gObjectEventPic_Sedgwick{C}SurfRun, 2, 4, {i}),\n'
                       for i in (0, 1, 2, 0, 0, 1, 1, 2, 2, 0, 1, 2))
        pics += (f'static const struct SpriteFrameImage sPicTable_Sedgwick{C}Normal[] = {{\n{walk}{run}}};\n\n'
                 f'static const struct SpriteFrameImage sPicTable_Sedgwick{C}Bike[] = {{\n'
                 f'    overworld_ascending_frames(gObjectEventPic_Sedgwick{C}Bike, 4, 4),\n}};\n\n'
                 f'static const struct SpriteFrameImage sPicTable_Sedgwick{C}Surf[] = {{\n{surf}}};\n\n'
                 f'static const struct SpriteFrameImage sPicTable_Sedgwick{C}Item[] = {{\n'
                 f'    overworld_ascending_frames(gObjectEventPic_Sedgwick{C}Item, 2, 4),\n}};\n\n'
                 f'static const struct SpriteFrameImage sPicTable_Sedgwick{C}Fish[] = {{\n'
                 f'    overworld_ascending_frames(gObjectEventPic_Sedgwick{C}Fish, 4, 4),\n}};\n\n')
    block(f'{E}/src/data/object_events/object_event_pic_tables.h', pics)

    spec = {  # kind: (size, w, h, tracks, anims, pics)
        'Normal': (512, 16, 32, 'TRACKS_FOOT', 'sAnimTable_BrendanMayNormal', 'Normal'),
        'Bike': (512, 32, 32, 'TRACKS_BIKE_TIRE', 'sAnimTable_Standard', 'Bike'),
        'Surf': (256, 16, 32, 'TRACKS_FOOT', 'sAnimTable_Surfing', 'Surf'),
        'FieldMove': (256, 16, 32, 'TRACKS_FOOT', 'sAnimTable_FieldMove', 'Item'),
        'Fish': (512, 32, 32, 'TRACKS_FOOT', 'sAnimTable_Fishing', 'Fish'),
    }
    infos, externs, ptrs, pals = '', '', '', ''
    for c in CHARS.values():
        C = c['C']
        pals += f'    {{gObjectEventPal_Sedgwick{C},            OBJ_EVENT_PAL_TAG_SEDGWICK_{C.upper()}}},\n'
        for kind, (size, w, h, tracks, anims, pic) in spec.items():
            name = f'gObjectEventGraphicsInfo_Sedgwick{C}{kind}'
            infos += (f'const struct ObjectEventGraphicsInfo {name} = {{\n'
                      f'    .tileTag = TAG_NONE,\n    .paletteTag = OBJ_EVENT_PAL_TAG_SEDGWICK_{C.upper()},\n'
                      f'    .reflectionPaletteTag = OBJ_EVENT_PAL_TAG_BRIDGE_REFLECTION,\n    .size = {size},\n'
                      f'    .width = {w},\n    .height = {h},\n    .paletteSlot = PALSLOT_PLAYER,\n'
                      f'    .shadowSize = SHADOW_SIZE_M,\n    .inanimate = FALSE,\n    .compressed = FALSE,\n'
                      f'    .tracks = {tracks},\n    .oam = &gObjectEventBaseOam_{w}x{h},\n'
                      f'    .subspriteTables = sOamTables_{w}x{h},\n    .anims = {anims},\n'
                      f'    .images = sPicTable_Sedgwick{C}{pic},\n    .affineAnims = gDummySpriteAffineAnimTable,\n}};\n\n')
            externs += f'extern const struct ObjectEventGraphicsInfo {name};\n'
            K = {'Normal': 'NORMAL', 'Bike': 'BIKE', 'Surf': 'SURF', 'FieldMove': 'FIELD_MOVE', 'Fish': 'FISH'}[kind]
            ptrs += f'    [OBJ_EVENT_GFX_SEDGWICK_{C.upper()}_{K}] = &{name},\n'
    block(f'{E}/src/data/object_events/object_event_graphics_info.h', infos)
    ptr_path = f'{E}/src/data/object_events/object_event_graphics_info_pointers.h'
    s = open(ptr_path).read()
    if 'gObjectEventGraphicsInfo_SedgwickBoyNormal;' not in s:
        s = s.replace('extern const struct ObjectEventGraphicsInfo gObjectEventGraphicsInfo_RedNormal;\n',
                      externs + 'extern const struct ObjectEventGraphicsInfo gObjectEventGraphicsInfo_RedNormal;\n', 1)
        open(ptr_path, 'w').write(s)
    block(ptr_path, ptrs, anchor='    [OBJ_EVENT_GFX_APRICORN_TREE] =            &gObjectEventGraphicsInfo_ApricornTree,\n')
    block(f'{E}/src/event_object_movement.c', pals,
          anchor='    {gObjectEventPal_RubySapphireMay,       OBJ_EVENT_PAL_TAG_RS_MAY},\n')

    block(f'{E}/src/field_player_avatar.c',
          ''.join(f'    case OBJ_EVENT_GFX_SEDGWICK_GIRL_{k}:\n' for k in KINDS),
          anchor='    case OBJ_EVENT_GFX_GREEN_VS_SEEKER_BIKE:\n')

    # battle back sprites: Brendan/May's back pics are replaced by ours (5 frames, Kanto animation)
    tr = f'{E}/src/data/graphics/trainers.h'
    block(tr, ''.join(
        f'const u8 gTrainerBackPic_Sedgwick{c["C"]}[] = INCGFX_U8("graphics/trainers/back_pics/sedgwick_{w}.png", ".4bpp");\n'
        f'const u16 gTrainerBackPicPalette_Sedgwick{c["C"]}[] = INCGFX_U16("graphics/trainers/back_pics/sedgwick_{w}.png", ".gbapal");\n'
        for w, c in CHARS.items()),
        anchor='const u16 gTrainerBackPicPalette_Leaf[] = INCGFX_U16("graphics/trainers/back_pics/leaf.png", ".gbapal");\n')
    s = open(tr).read()
    for old, C in (('TRAINER_BACK_PIC(4, gTrainerBackPic_Brendan, gTrainerPalette_Brendan, sBackAnims_Hoenn)', 'Boy'),
                   ('TRAINER_BACK_PIC(4, gTrainerBackPic_May, gTrainerPalette_May, sBackAnims_Hoenn)', 'Girl')):
        new = f'TRAINER_BACK_PIC(5, gTrainerBackPic_Sedgwick{C}, gTrainerBackPicPalette_Sedgwick{C}, sBackAnims_Kanto)'
        s = s.replace(old, new, 1)
    open(tr, 'w').write(s)


if __name__ == '__main__':
    sprites()
    hookup()
    print('players written and hooked up')
