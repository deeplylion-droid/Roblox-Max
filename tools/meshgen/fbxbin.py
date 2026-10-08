"""
Scrittore FBX binario 7.4 (formato Kaydara) in puro Python, sufficiente per mesh statiche:
Vertices, PolygonVertexIndex, normali per vertice di poligono, UV, un Model, Connections.
"""
from __future__ import annotations
import struct, time, zlib
import numpy as np

HEAD_MAGIC = b"Kaydara FBX Binary\x20\x20\x00\x1a\x00"
SENTINEL = b"\x00" * 13
FOOTER_ID = b"\xfa\xbc\xab\x09\xd0\xc8\xd4\x66\xb1\x76\xfb\x83\x1c\xf7\x26\x7e"
FOOTER_MAGIC = b"\xf8\x5a\x8c\x6a\xde\xf5\xd9\x7e\xec\xe9\x0c\xe3\x75\x8f\x29\x0b"
VERSION = 7400


class Node:
    def __init__(self, name, *props):
        self.name = name.encode() if isinstance(name, str) else name
        self.props = list(props)
        self.children = []

    def add(self, node):
        self.children.append(node)
        return node

    def n(self, name, *props):
        return self.add(Node(name, *props))


def _prop(p):
    if isinstance(p, bool):
        return b"C" + (b"\x01" if p else b"\x00")
    if isinstance(p, int):
        if -2**31 <= p < 2**31:
            return b"I" + struct.pack("<i", p)
        return b"L" + struct.pack("<q", p)
    if isinstance(p, float):
        return b"D" + struct.pack("<d", p)
    if isinstance(p, str):
        b = p.encode()
        return b"S" + struct.pack("<I", len(b)) + b
    if isinstance(p, bytes):
        return b"R" + struct.pack("<I", len(p)) + p
    if isinstance(p, np.ndarray):
        if p.dtype == np.float64:
            code, fmt = b"d", "<%dd"
        elif p.dtype == np.int32:
            code, fmt = b"i", "<%di"
        elif p.dtype == np.int64:
            code, fmt = b"l", "<%dq"
        elif p.dtype == np.float32:
            code, fmt = b"f", "<%df"
        else:
            raise TypeError(p.dtype)
        raw = struct.pack(fmt % len(p), *p.tolist())
        comp = zlib.compress(raw)
        return code + struct.pack("<III", len(p), 1, len(comp)) + comp
    raise TypeError(type(p))


def _encode(node, offset):
    props = b"".join(_prop(p) for p in node.props)
    body_children = b""
    if node.children or not node.props:
        # calcolo iterativo delle posizioni dei figli
        pos = offset + 13 + len(node.name) + len(props)
        parts = []
        for c in node.children:
            enc = _encode(c, pos)
            parts.append(enc)
            pos += len(enc)
        body_children = b"".join(parts) + SENTINEL
    total = 13 + len(node.name) + len(props) + len(body_children)
    end_offset = offset + total
    header = struct.pack("<III", end_offset, len(node.props), len(props)) + bytes([len(node.name)]) + node.name
    return header + props + body_children


def write_fbx(path, root_nodes):
    out = bytearray(HEAD_MAGIC + struct.pack("<I", VERSION))
    for n in root_nodes:
        out += _encode(n, len(out))
    out += SENTINEL
    out += FOOTER_ID
    out += b"\x00" * 4
    pad = ((len(out) + 15) & ~15) - len(out)
    if pad == 0:
        pad = 16
    out += b"\x00" * pad
    out += struct.pack("<I", VERSION)
    out += b"\x00" * 120
    out += FOOTER_MAGIC
    with open(path, "wb") as f:
        f.write(bytes(out))


def P70(parent, entries):
    p = parent.n("Properties70")
    for e in entries:
        p.n("P", *e)
    return p


def mesh_fbx(path, V, F, normals_per_corner, uv, name="Mesh"):
    """V (n,3) float; F (m,3) int; normals_per_corner (m*3,3); uv (n,2)."""
    V = np.asarray(V, np.float64)
    F = np.asarray(F, np.int64)
    geom_id, model_id = 1000000, 2000000
    t = time.localtime()

    header = Node("FBXHeaderExtension")
    header.n("FBXHeaderVersion", 1003)
    header.n("FBXVersion", VERSION)
    header.n("EncryptionType", 0)
    ts = header.n("CreationTimeStamp")
    ts.n("Version", 1000)
    for k, v in (("Year", t.tm_year), ("Month", t.tm_mon), ("Day", t.tm_mday), ("Hour", t.tm_hour), ("Minute", t.tm_min), ("Second", t.tm_sec), ("Millisecond", 0)):
        ts.n(k, v)
    header.n("Creator", "VivaioMeshGen")
    file_id = Node("FileId", bytes(range(16)))
    ctime = Node("CreationTime", time.strftime("%Y-%m-%d %H:%M:%S:000", t))
    creator = Node("Creator", "VivaioMeshGen")

    gs = Node("GlobalSettings")
    gs.n("Version", 1000)
    P70(gs, [
        ("UpAxis", "int", "Integer", "", 1), ("UpAxisSign", "int", "Integer", "", 1),
        ("FrontAxis", "int", "Integer", "", 2), ("FrontAxisSign", "int", "Integer", "", 1),
        ("CoordAxis", "int", "Integer", "", 0), ("CoordAxisSign", "int", "Integer", "", 1),
        ("OriginalUpAxis", "int", "Integer", "", 1), ("OriginalUpAxisSign", "int", "Integer", "", 1),
        ("UnitScaleFactor", "double", "Number", "", 1.0), ("OriginalUnitScaleFactor", "double", "Number", "", 1.0),
        ("AmbientColor", "ColorRGB", "Color", "", 0.0, 0.0, 0.0), ("DefaultCamera", "KString", "", "", "Producer Perspective"),
        ("TimeMode", "enum", "", "", 11), ("TimeSpanStart", "KTime", "Time", "", 0), ("TimeSpanStop", "KTime", "Time", "", 46186158000),
        ("CustomFrameRate", "double", "Number", "", 24.0),
    ])

    docs = Node("Documents")
    docs.n("Count", 1)
    doc = docs.n("Document", 3000000, "", "Scene")
    P70(doc, [("SourceObject", "object", "", ""), ("ActiveAnimStackName", "KString", "", "", "")])
    doc.n("RootNode", 0)
    refs = Node("References")

    defs = Node("Definitions")
    defs.n("Version", 100)
    defs.n("Count", 3)
    defs.n("ObjectType", "GlobalSettings").n("Count", 1)
    ot = defs.n("ObjectType", "Geometry")
    ot.n("Count", 1)
    ot.n("PropertyTemplate", "FbxMesh")
    ot2 = defs.n("ObjectType", "Model")
    ot2.n("Count", 1)
    ot2.n("PropertyTemplate", "FbxNode")

    objs = Node("Objects")
    geom = objs.n("Geometry", geom_id, f"{name}\x00\x01Geometry", "Mesh")
    geom.n("Vertices", V.reshape(-1))
    idx = F.copy()
    idx[:, 2] = -idx[:, 2] - 1
    geom.n("PolygonVertexIndex", idx.reshape(-1).astype(np.int32))
    geom.n("GeometryVersion", 124)
    ln = geom.n("LayerElementNormal", 0)
    ln.n("Version", 101)
    ln.n("Name", "")
    ln.n("MappingInformationType", "ByPolygonVertex")
    ln.n("ReferenceInformationType", "Direct")
    ln.n("Normals", np.asarray(normals_per_corner, np.float64).reshape(-1))
    luv = geom.n("LayerElementUV", 0)
    luv.n("Version", 101)
    luv.n("Name", "UVMap")
    luv.n("MappingInformationType", "ByPolygonVertex")
    luv.n("ReferenceInformationType", "IndexToDirect")
    luv.n("UV", np.asarray(uv, np.float64).reshape(-1))
    luv.n("UVIndex", F.reshape(-1).astype(np.int32))
    layer = geom.n("Layer", 0)
    layer.n("Version", 100)
    le = layer.n("LayerElement")
    le.n("Type", "LayerElementNormal")
    le.n("TypedIndex", 0)
    le2 = layer.n("LayerElement")
    le2.n("Type", "LayerElementUV")
    le2.n("TypedIndex", 0)

    model = objs.n("Model", model_id, f"{name}\x00\x01Model", "Mesh")
    model.n("Version", 232)
    P70(model, [
        ("Lcl Translation", "Lcl Translation", "", "A", 0.0, 0.0, 0.0),
        ("Lcl Rotation", "Lcl Rotation", "", "A", 0.0, 0.0, 0.0),
        ("Lcl Scaling", "Lcl Scaling", "", "A", 1.0, 1.0, 1.0),
        ("DefaultAttributeIndex", "int", "Integer", "", 0),
    ])
    model.n("Shading", True)
    model.n("Culling", "CullingOff")

    conns = Node("Connections")
    conns.n("C", "OO", model_id, 0)
    conns.n("C", "OO", geom_id, model_id)
    takes = Node("Takes")
    takes.n("Current", "")

    write_fbx(path, [header, file_id, ctime, creator, gs, docs, refs, defs, objs, conns, takes])
