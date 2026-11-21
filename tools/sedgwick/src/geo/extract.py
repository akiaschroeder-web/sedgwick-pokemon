"""OSM -> classified features in county tile coordinates.

Projection: equirectangular about the county's middle latitude, METERS_PER_TILE
metres per metatile, origin at the county's north-west corner. x grows east,
y grows south, same as the game's map grid."""
import math, pickle, os

METERS_PER_TILE = 2.5
LON0, LAT0 = -97.8084, 37.9128          # county NW corner (bbox)
LON1, LAT1 = -97.1521, 37.4735
LATM = (LAT0 + LAT1) / 2
KX = 111320 * math.cos(math.radians(LATM)) / METERS_PER_TILE
KY = 110950 / METERS_PER_TILE
WIDTH = int((LON1 - LON0) * KX) + 1
HEIGHT = int((LAT0 - LAT1) * KY) + 1


def proj(lon, lat):
    return ((lon - LON0) * KX, (LAT0 - lat) * KY)


def unproj(x, y):
    return (LON0 + x / KX, LAT0 - y / KY)


PAVED = {'asphalt', 'paved', 'concrete', 'chipseal', ''}
UNPAVED = {'gravel', 'unpaved', 'dirt', 'compacted', 'fine_gravel', 'ground', 'sand', 'grass', 'pebblestone'}


def road_class(t):
    h = t.get('highway')
    if h == 'construction':                       # OSM lags: treat as built
        h = t.get('construction', 'residential')
        t = dict(t, highway=h)
    s = t.get('surface', '')
    if h in ('motorway', 'motorway_link'):
        return 'motorway'
    if h in ('trunk', 'primary', 'secondary', 'trunk_link', 'primary_link', 'secondary_link'):
        return 'highway'
    if h in ('tertiary', 'tertiary_link', 'residential', 'unclassified', 'living_street', 'road'):
        return 'gravel' if s in UNPAVED else 'street'
    if h == 'track':
        return 'track'
    if h == 'service':
        sv = t.get('service', '')
        if sv == 'alley':
            return 'alley'
        if sv == 'driveway':
            return 'driveway'
        if sv in ('parking_aisle', 'drive-through'):
            return None
        return 'gravel' if s in UNPAVED else 'service'
    return None


AREA = [  # (tag, values, class) checked in order
    ('natural', ('water',), 'water'), ('landuse', ('reservoir', 'basin'), 'water'), ('waterway', ('riverbank',), 'water'),
    ('natural', ('wood',), 'wood'), ('landuse', ('forest',), 'wood'),
    ('landuse', ('farmland',), 'farmland'), ('landuse', ('meadow', 'grass'), 'meadow'), ('natural', ('grassland', 'scrub'), 'meadow'),
    ('landuse', ('farmyard',), 'farmyard'),
    ('landuse', ('cemetery',), 'cemetery'), ('amenity', ('grave_yard',), 'cemetery'),
    ('leisure', ('park', 'recreation_ground', 'playground', 'pitch', 'golf_course', 'sports_centre'), 'park'),
    ('landuse', ('recreation_ground', 'village_green'), 'park'),
    ('amenity', ('parking',), 'parking'),
    ('landuse', ('residential',), 'residential'), ('landuse', ('commercial', 'retail'), 'commercial'),
    ('landuse', ('industrial',), 'industrial'),
]


def area_class(t):
    for k, vals, c in AREA:
        if t.get(k) in vals:
            return c
    return None


def extract(raw, bbox=None):
    """bbox = (x0, y0, x1, y1) in tile coords; features touching it are kept."""
    nodes, ways, rels = raw
    P = {}

    def pts(refs):
        out = []
        for r in refs:
            if r not in nodes:
                return None
            if r not in P:
                la, lo, _ = nodes[r]
                P[r] = proj(lo, la)
            out.append(P[r])
        return out

    def keep(p):
        if bbox is None:
            return True
        x0, y0, x1, y1 = bbox
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        return max(xs) >= x0 and min(xs) <= x1 and max(ys) >= y0 and min(ys) <= y1

    F = {'roads': [], 'areas': [], 'buildings': [], 'rail': [], 'addresses': [], 'pois': [], 'turns': []}
    for wid, (refs, t) in ways.items():
        if not t:
            continue
        p = pts(refs)
        if not p or not keep(p):
            continue
        if 'building' in t:
            F['buildings'].append({'id': wid, 'poly': p, 'tags': t})
            continue
        rc = road_class(t) if 'highway' in t else None
        if rc:
            F['roads'].append({'id': wid, 'cls': rc, 'pts': p, 'name': t.get('name', ''),
                               'bridge': t.get('bridge') == 'yes', 'oneway': t.get('oneway') == 'yes',
                               'link': t.get('highway', '').endswith('_link'),
                               'lanes': t.get('lanes')})
            continue
        if t.get('railway') in ('rail', 'disused', 'abandoned', 'spur', 'siding') and 'area' not in t:
            F['rail'].append({'id': wid, 'pts': p, 'state': t['railway'], 'service': t.get('service', '')})
            continue
        ac = area_class(t)
        if ac and refs[0] == refs[-1]:
            F['areas'].append({'id': wid, 'cls': ac, 'poly': p, 'tags': t})
    # multipolygon areas (outer rings only; inners become holes)
    from geo.boundary import rings
    for rid, (mem, t) in rels.items():
        if t.get('type') != 'multipolygon':
            continue
        ac = area_class(t)
        isb = 'building' in t
        if not ac and not isb:
            continue
        rel = (mem, t)
        outer = [[proj(*q) for q in r] for r in rings(rel, ways, nodes, 'outer') if r and r[0] == r[-1]]
        inner = [[proj(*q) for q in r] for r in rings(rel, ways, nodes, 'inner') if r and r[0] == r[-1]]
        for o in outer:
            if keep(o):
                (F['buildings'] if isb else F['areas']).append(
                    {'id': -rid, 'cls': ac, 'poly': o, 'holes': inner, 'tags': t})
    for nid, (la, lo, t) in nodes.items():
        if not t:
            continue
        x, y = proj(lo, la)
        if bbox and not (bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]):
            continue
        if t.get('highway') in ('turning_circle', 'turning_loop'):
            F['turns'].append({'x': x, 'y': y})
        if 'addr:housenumber' in t:
            F['addresses'].append({'x': x, 'y': y, 'num': t['addr:housenumber'], 'street': t.get('addr:street', ''), 'tags': t})
        elif any(k in t for k in ('amenity', 'shop', 'man_made', 'leisure', 'tourism', 'office')):
            F['pois'].append({'x': x, 'y': y, 'tags': t})
    # building ways that carry an address count as address points too
    for b in F['buildings']:
        t = b['tags']
        if 'addr:housenumber' in t:
            xs = [q[0] for q in b['poly']]; ys = [q[1] for q in b['poly']]
            F['addresses'].append({'x': sum(xs) / len(xs), 'y': sum(ys) / len(ys), 'num': t['addr:housenumber'],
                                   'street': t.get('addr:street', ''), 'tags': t, 'building': b['id']})
    return F


if __name__ == '__main__':
    import sys
    raw = pickle.load(open('/home/claude/osm_in/raw.pkl', 'rb'))
    print('county grid', WIDTH, 'x', HEIGHT, 'tiles')
    x0, y0 = proj(-97.797, 37.652)
    x1, y1 = proj(-97.748, 37.612)
    bb = (int(x0), int(y0), int(x1), int(y1))
    F = extract(raw, bb)
    F['bbox'] = bb
    pickle.dump(F, open('/home/claude/osm_in/cheney.pkl', 'wb'))
    print('cheney bbox', bb, {k: len(v) for k, v in F.items() if isinstance(v, list)})
