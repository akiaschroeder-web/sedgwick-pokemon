"""Minimal OSM PBF reader (no osmium): protobuf classes are built at runtime from
hand-written descriptors of fileformat.proto / osmformat.proto."""
import struct, zlib, lzma
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

F = descriptor_pb2.FieldDescriptorProto
OPT, REQ, REP = F.LABEL_OPTIONAL, F.LABEL_REQUIRED, F.LABEL_REPEATED
T = {'string': F.TYPE_STRING, 'bytes': F.TYPE_BYTES, 'int32': F.TYPE_INT32, 'int64': F.TYPE_INT64,
     'uint32': F.TYPE_UINT32, 'sint64': F.TYPE_SINT64, 'msg': F.TYPE_MESSAGE}

SCHEMA = {
    'BlobHeader': [('type', 1, 'string', OPT), ('indexdata', 2, 'bytes', OPT), ('datasize', 3, 'int32', OPT)],
    'Blob': [('raw', 1, 'bytes', OPT), ('raw_size', 2, 'int32', OPT), ('zlib_data', 3, 'bytes', OPT),
             ('lzma_data', 4, 'bytes', OPT)],
    'StringTable': [('s', 1, 'bytes', REP)],
    'DenseNodes': [('id', 1, 'sint64', REP), ('lat', 8, 'sint64', REP), ('lon', 9, 'sint64', REP),
                   ('keys_vals', 10, 'int32', REP)],
    'Node': [('id', 1, 'sint64', OPT), ('keys', 2, 'uint32', REP), ('vals', 3, 'uint32', REP),
             ('lat', 8, 'sint64', OPT), ('lon', 9, 'sint64', OPT)],
    'Way': [('id', 1, 'int64', OPT), ('keys', 2, 'uint32', REP), ('vals', 3, 'uint32', REP),
            ('refs', 8, 'sint64', REP)],
    'Relation': [('id', 1, 'int64', OPT), ('keys', 2, 'uint32', REP), ('vals', 3, 'uint32', REP),
                 ('roles_sid', 8, 'int32', REP), ('memids', 9, 'sint64', REP), ('types', 10, 'int32', REP)],
    'PrimitiveGroup': [('nodes', 1, 'Node', REP), ('dense', 2, 'DenseNodes', OPT), ('ways', 3, 'Way', REP),
                       ('relations', 4, 'Relation', REP)],
    'PrimitiveBlock': [('stringtable', 1, 'StringTable', OPT), ('primitivegroup', 2, 'PrimitiveGroup', REP),
                       ('granularity', 17, 'int32', OPT), ('lat_offset', 19, 'int64', OPT),
                       ('lon_offset', 20, 'int64', OPT)],
}


def _classes():
    fd = descriptor_pb2.FileDescriptorProto(name='osmpbf_min.proto', package='osmmin', syntax='proto2')
    for name, fields in SCHEMA.items():
        m = fd.message_type.add(name=name)
        for fname, num, typ, lab in fields:
            f = m.field.add(name=fname, number=num, label=lab)
            if typ in T:
                f.type = T[typ]
            else:
                f.type = F.TYPE_MESSAGE
                f.type_name = '.osmmin.' + typ
            if lab == REP and typ not in ('bytes', 'string') and typ in T:
                f.options.packed = True
    pool = descriptor_pool.DescriptorPool()
    pool.Add(fd)
    return {n: message_factory.GetMessageClass(pool.FindMessageTypeByName('osmmin.' + n)) for n in SCHEMA}


C = _classes()


def blocks(path):
    with open(path, 'rb') as f:
        while True:
            hl = f.read(4)
            if not hl:
                return
            h = C['BlobHeader'].FromString(f.read(struct.unpack('>I', hl)[0]))
            b = C['Blob'].FromString(f.read(h.datasize))
            if b.raw:
                data = b.raw
            elif b.zlib_data:
                data = zlib.decompress(b.zlib_data)
            elif b.lzma_data:
                data = lzma.decompress(b.lzma_data)
            else:
                raise ValueError('unsupported blob compression')
            if h.type == 'OSMData':
                yield C['PrimitiveBlock'].FromString(data)


def read(path):
    """Returns nodes {id: (lat, lon, tags|None)}, ways {id: (refs, tags)}, relations {id: (members, tags)}."""
    nodes, ways, rels = {}, {}, {}
    for pb in blocks(path):
        st = [s.decode('utf-8') for s in pb.stringtable.s]
        g = (pb.granularity or 100) * 1e-9
        la0, lo0 = pb.lat_offset * 1e-9, pb.lon_offset * 1e-9
        for grp in pb.primitivegroup:
            if grp.HasField('dense'):
                d = grp.dense
                kv = list(d.keys_vals)
                k = 0
                i = la = lo = 0
                for di, dla, dlo in zip(d.id, d.lat, d.lon):
                    i += di; la += dla; lo += dlo
                    tags = None
                    if kv:
                        while kv[k] != 0:
                            tags = tags or {}
                            tags[st[kv[k]]] = st[kv[k + 1]]
                            k += 2
                        k += 1
                    nodes[i] = (la0 + la * g, lo0 + lo * g, tags)
            for n in grp.nodes:
                tags = {st[a]: st[b] for a, b in zip(n.keys, n.vals)} or None
                nodes[n.id] = (la0 + n.lat * g, lo0 + n.lon * g, tags)
            for w in grp.ways:
                refs, r = [], 0
                for d_ in w.refs:
                    r += d_; refs.append(r)
                ways[w.id] = (refs, {st[a]: st[b] for a, b in zip(w.keys, w.vals)})
            for rl in grp.relations:
                mem, m = [], 0
                for role, dm, t in zip(rl.roles_sid, rl.memids, rl.types):
                    m += dm
                    mem.append(('nwr'[t], m, st[role]))
                rels[rl.id] = (mem, {st[a]: st[b] for a, b in zip(rl.keys, rl.vals)})
    return nodes, ways, rels
