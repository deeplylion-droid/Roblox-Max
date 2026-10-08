"""
Libreria minima di geometria per generare mesh stilizzate di alta qualità con numpy:
icosfere suddivise, superfici di rivoluzione (lathe), tori, rumore frattale, spostamenti,
normali smooth/flat, fusione, esportazione FBX ASCII e un renderer software per anteprime.
Unità: 1 = 1 stud. Asse verticale: +Y.
"""
from __future__ import annotations
import math
import numpy as np

# ───────────────────────── struttura ─────────────────────────

class Mesh:
    def __init__(self, V, F, UV=None, flat=False):
        self.V = np.asarray(V, dtype=np.float64).reshape(-1, 3)
        self.F = np.asarray(F, dtype=np.int64).reshape(-1, 3)
        self.UV = None if UV is None else np.asarray(UV, dtype=np.float64).reshape(-1, 2)
        self.flat = flat  # normali per faccia (cristalli) invece che smooth

    def copy(self):
        return Mesh(self.V.copy(), self.F.copy(), None if self.UV is None else self.UV.copy(), self.flat)

    @property
    def tris(self):
        return len(self.F)

    def bounds(self):
        return self.V.min(axis=0), self.V.max(axis=0)

    # trasformazioni (in place, ritorna self)
    def scale(self, sx, sy=None, sz=None):
        if sy is None:
            sy = sz = sx
        self.V *= np.array([sx, sy, sz])
        return self

    def translate(self, x, y, z):
        self.V += np.array([x, y, z])
        return self

    def rotate_y(self, deg):
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        self.V = self.V @ R.T
        return self

    def rotate_x(self, deg):
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        R = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        self.V = self.V @ R.T
        return self

    def rotate_z(self, deg):
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        self.V = self.V @ R.T
        return self

    def center_bottom(self):
        lo, hi = self.bounds()
        c = (lo + hi) / 2
        self.translate(-c[0], -lo[1], -c[2])
        return self

    def center(self):
        lo, hi = self.bounds()
        c = (lo + hi) / 2
        self.translate(-c[0], -c[1], -c[2])
        return self

    def fit(self, size):
        """Scala uniformemente perché la dimensione massima diventi `size`."""
        lo, hi = self.bounds()
        m = (hi - lo).max()
        if m > 0:
            self.scale(size / m)
        return self

    def face_normals(self):
        a, b, c = self.V[self.F[:, 0]], self.V[self.F[:, 1]], self.V[self.F[:, 2]]
        n = np.cross(b - a, c - a)
        l = np.linalg.norm(n, axis=1, keepdims=True)
        l[l == 0] = 1
        return n / l

    def vertex_normals(self):
        a, b, c = self.V[self.F[:, 0]], self.V[self.F[:, 1]], self.V[self.F[:, 2]]
        n = np.cross(b - a, c - a)  # pesate per area
        vn = np.zeros_like(self.V)
        for i in range(3):
            np.add.at(vn, self.F[:, i], n)
        l = np.linalg.norm(vn, axis=1, keepdims=True)
        l[l == 0] = 1
        return vn / l

    def fix_orientation(self):
        """Orienta tutte le facce verso l'esterno rispetto al baricentro (mesh stellate/convesse)."""
        c = self.V.mean(axis=0)
        fn = self.face_normals()
        centers = self.V[self.F].mean(axis=1)
        inward = np.einsum("ij,ij->i", fn, centers - c) < 0
        self.F[inward] = self.F[inward][:, [0, 2, 1]]
        return self

    def flip(self):
        self.F = self.F[:, [0, 2, 1]]
        return self

    def weld(self, eps=1e-6):
        """Unisce i vertici coincidenti (dopo lathe/merge) per normali smooth continue."""
        q = np.round(self.V / eps).astype(np.int64)
        _, idx, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
        self.V = self.V[idx]
        if self.UV is not None:
            self.UV = self.UV[idx]
        self.F = inv[self.F]
        # rimuove triangoli degeneri
        keep = (self.F[:, 0] != self.F[:, 1]) & (self.F[:, 1] != self.F[:, 2]) & (self.F[:, 0] != self.F[:, 2])
        self.F = self.F[keep]
        return self


def merge(*meshes):
    V, F, UV = [], [], []
    off = 0
    has_uv = all(m.UV is not None for m in meshes)
    for m in meshes:
        V.append(m.V)
        F.append(m.F + off)
        if has_uv:
            UV.append(m.UV)
        off += len(m.V)
    return Mesh(np.vstack(V), np.vstack(F), np.vstack(UV) if has_uv else None, flat=all(m.flat for m in meshes))


# ───────────────────────── primitive ─────────────────────────

def icosphere(subdiv=3, radius=1.0):
    t = (1 + 5 ** 0.5) / 2
    V = np.array([
        [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
        [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
        [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1],
    ], dtype=np.float64)
    F = np.array([
        [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
        [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
        [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
        [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
    ])
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    for _ in range(subdiv):
        cache = {}
        newF = []
        Vl = V.tolist()

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k in cache:
                return cache[k]
            p = np.array(Vl[a]) + np.array(Vl[b])
            p /= np.linalg.norm(p)
            Vl.append(p.tolist())
            cache[k] = len(Vl) - 1
            return cache[k]

        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            newF += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        V = np.array(Vl)
        F = np.array(newF)
    m = Mesh(V * radius, F)
    m.UV = spherical_uv(m.V)
    return m


def spherical_uv(V):
    n = V / np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-9)
    u = 0.5 + np.arctan2(n[:, 2], n[:, 0]) / (2 * math.pi)
    v = 0.5 - np.arcsin(np.clip(n[:, 1], -1, 1)) / math.pi
    return np.stack([u, v], axis=1)


def lathe(profile, segments=48, close_top=True, close_bottom=True, smooth_seam=True):
    """
    Rivoluzione attorno a Y di un profilo [(r, y), ...] dal basso verso l'alto.
    r=0 ai capi chiude automaticamente. Ritorna una mesh saldata con UV cilindriche.
    """
    prof = [(float(r), float(y)) for r, y in profile]
    rings = []
    for r, y in prof:
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ring.append([r * math.cos(a), y, r * math.sin(a)])
        rings.append(ring)
    V = np.array(rings).reshape(-1, 3)
    F = []
    n = segments
    for j in range(len(prof) - 1):
        for i in range(n):
            a = j * n + i
            b = j * n + (i + 1) % n
            c = (j + 1) * n + i
            d = (j + 1) * n + (i + 1) % n
            F.append([a, c, b])
            F.append([b, c, d])
    V = V.tolist()
    if close_bottom and prof[0][0] > 1e-9:
        V.append([0, prof[0][1], 0])
        ci = len(V) - 1
        for i in range(n):
            F.append([i, (i + 1) % n, ci])
    if close_top and prof[-1][0] > 1e-9:
        V.append([0, prof[-1][1], 0])
        ci = len(V) - 1
        base = (len(prof) - 1) * n
        for i in range(n):
            F.append([base + (i + 1) % n, base + i, ci])
    m = Mesh(np.array(V), np.array(F))
    m.weld(1e-7)
    m.UV = cylindrical_uv(m.V)
    return m


def cylindrical_uv(V):
    lo, hi = V.min(axis=0), V.max(axis=0)
    u = 0.5 + np.arctan2(V[:, 2], V[:, 0]) / (2 * math.pi)
    h = max(hi[1] - lo[1], 1e-9)
    v = 1 - (V[:, 1] - lo[1]) / h
    return np.stack([u, v], axis=1)


def torus(R=1.0, r=0.25, seg_major=64, seg_minor=24, arc=360.0, tilt_profile=None):
    V, F = [], []
    closed = abs(arc - 360) < 1e-6
    nmaj = seg_major if closed else seg_major + 1
    for i in range(nmaj):
        a = math.radians(arc) * i / seg_major
        ca, sa = math.cos(a), math.sin(a)
        for j in range(seg_minor):
            b = 2 * math.pi * j / seg_minor
            x = (R + r * math.cos(b)) * ca
            z = (R + r * math.cos(b)) * sa
            y = r * math.sin(b)
            V.append([x, y, z])
    span = seg_major if closed else seg_major
    for i in range(span):
        i2 = (i + 1) % nmaj if closed else i + 1
        for j in range(seg_minor):
            j2 = (j + 1) % seg_minor
            a = i * seg_minor + j
            b = i * seg_minor + j2
            c = i2 * seg_minor + j
            d = i2 * seg_minor + j2
            F.append([a, b, c])
            F.append([b, d, c])
    m = Mesh(np.array(V), np.array(F))
    if not closed:
        # tappi alle estremità
        for ring_start in (0, (nmaj - 1) * seg_minor):
            idxs = list(range(ring_start, ring_start + seg_minor))
            center = m.V[idxs].mean(axis=0)
            m.V = np.vstack([m.V, center])
            ci = len(m.V) - 1
            caps = []
            for j in range(seg_minor):
                caps.append([idxs[j], idxs[(j + 1) % seg_minor], ci])
            m.F = np.vstack([m.F, np.array(caps)])
    m.fix_orientation()
    m.UV = spherical_uv(m.V)
    return m


# ───────────────────────── rumore ─────────────────────────

def _hash3(ix, iy, iz, seed):
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 97531) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0xFFFFFF)


def value_noise(P, seed=0, freq=1.0):
    """Rumore di valore trilineare con interpolazione smoothstep. P: (n,3) → (n,) in [-1,1]."""
    Q = P * freq
    i0 = np.floor(Q).astype(np.int64)
    f = Q - i0
    f = f * f * (3 - 2 * f)
    out = np.zeros(len(P))
    for dx in (0, 1):
        wx = f[:, 0] if dx else 1 - f[:, 0]
        for dy in (0, 1):
            wy = f[:, 1] if dy else 1 - f[:, 1]
            for dz in (0, 1):
                wz = f[:, 2] if dz else 1 - f[:, 2]
                h = _hash3(i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz, seed)
                out += wx * wy * wz * h
    return out * 2 - 1


def fbm(P, seed=0, octaves=4, freq=1.0, gain=0.5, lacunarity=2.0):
    total, amp, norm = np.zeros(len(P)), 1.0, 0.0
    for o in range(octaves):
        total += amp * value_noise(P, seed + o * 17, freq)
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / norm


def displace_radial(mesh, amount_fn):
    """Sposta i vertici lungo la direzione dal centro: amount_fn(V) → (n,) fattore moltiplicativo del raggio."""
    c = mesh.V.mean(axis=0)
    d = mesh.V - c
    r = np.linalg.norm(d, axis=1, keepdims=True)
    r[r == 0] = 1
    f = amount_fn(mesh.V).reshape(-1, 1)
    mesh.V = c + d * f
    return mesh


def displace_normal(mesh, amount):
    n = mesh.vertex_normals()
    mesh.V = mesh.V + n * np.asarray(amount).reshape(-1, 1)
    return mesh


def gaussian_bumps(V, centers, sigmas, heights):
    """Somma di gaussiane direzionali (su sfera unitaria) → fattore 1 + somma."""
    n = V / np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-9)
    out = np.ones(len(V))
    for c, s, h in zip(centers, sigmas, heights):
        c = np.asarray(c) / np.linalg.norm(c)
        dot = np.clip(n @ c, -1, 1)
        ang = np.arccos(dot)
        out += h * np.exp(-(ang ** 2) / (2 * s * s))
    return out


# ───────────────────────── FBX ASCII ─────────────────────────

def _fmt(a):
    return ",".join(f"{x:.6g}" for x in a)


def export_fbx(mesh, path, name="Mesh"):
    """Scrive un FBX ASCII 7.4 con normali (smooth o per faccia) e UV, compatibile con l'importer Roblox."""
    V = mesh.V
    F = mesh.F
    verts = V.reshape(-1)
    idx = F.copy()
    idx[:, 2] = -idx[:, 2] - 1  # ultimo indice del poligono negato (FBX)
    poly = idx.reshape(-1)
    if mesh.flat:
        fn = mesh.face_normals()
        normals = np.repeat(fn, 3, axis=0).reshape(-1)
    else:
        vn = mesh.vertex_normals()
        normals = vn[F].reshape(-1)
    uv = mesh.UV if mesh.UV is not None else spherical_uv(V)
    uvs = uv.reshape(-1)
    uvidx = F.reshape(-1)
    lines = [
        "; FBX 7.4.0 project file",
        "FBXHeaderExtension:  {", "\tFBXHeaderVersion: 1003", "\tFBXVersion: 7400", '\tCreator: "VivaioMeshGen"', "}",
        "GlobalSettings:  {", "\tVersion: 1000", "\tProperties70:  {",
        '\t\tP: "UpAxis", "int", "Integer", "",1', '\t\tP: "UpAxisSign", "int", "Integer", "",1',
        '\t\tP: "FrontAxis", "int", "Integer", "",2', '\t\tP: "FrontAxisSign", "int", "Integer", "",1',
        '\t\tP: "CoordAxis", "int", "Integer", "",0', '\t\tP: "CoordAxisSign", "int", "Integer", "",1',
        '\t\tP: "UnitScaleFactor", "double", "Number", "",1',
        "\t}", "}",
        "Definitions:  {", "\tVersion: 100", "\tCount: 2",
        '\tObjectType: "Model" {', "\t\tCount: 1", "\t}", '\tObjectType: "Geometry" {', "\t\tCount: 1", "\t}", "}",
        "Objects:  {",
        f'\tGeometry: 1000, "Geometry::{name}", "Mesh" {{',
        f"\t\tVertices: *{len(verts)} {{", f"\t\t\ta: {_fmt(verts)}", "\t\t}",
        f"\t\tPolygonVertexIndex: *{len(poly)} {{", f"\t\t\ta: {','.join(str(int(x)) for x in poly)}", "\t\t}",
        "\t\tGeometryVersion: 124",
        "\t\tLayerElementNormal: 0 {", "\t\t\tVersion: 101", '\t\t\tName: ""',
        '\t\t\tMappingInformationType: "ByPolygonVertex"', '\t\t\tReferenceInformationType: "Direct"',
        f"\t\t\tNormals: *{len(normals)} {{", f"\t\t\t\ta: {_fmt(normals)}", "\t\t\t}", "\t\t}",
        "\t\tLayerElementUV: 0 {", "\t\t\tVersion: 101", '\t\t\tName: "UVMap"',
        '\t\t\tMappingInformationType: "ByPolygonVertex"', '\t\t\tReferenceInformationType: "IndexToDirect"',
        f"\t\t\tUV: *{len(uvs)} {{", f"\t\t\t\ta: {_fmt(uvs)}", "\t\t\t}",
        f"\t\t\tUVIndex: *{len(uvidx)} {{", f"\t\t\t\ta: {','.join(str(int(x)) for x in uvidx)}", "\t\t\t}", "\t\t}",
        "\t\tLayer: 0 {", "\t\t\tVersion: 100",
        "\t\t\tLayerElement:  {", '\t\t\t\tType: "LayerElementNormal"', "\t\t\t\tTypedIndex: 0", "\t\t\t}",
        "\t\t\tLayerElement:  {", '\t\t\t\tType: "LayerElementUV"', "\t\t\t\tTypedIndex: 0", "\t\t\t}",
        "\t\t}", "\t}",
        f'\tModel: 2000, "Model::{name}", "Mesh" {{', "\t\tVersion: 232", "\t\tProperties70:  {",
        '\t\t\tP: "Lcl Translation", "Lcl Translation", "", "A",0,0,0',
        '\t\t\tP: "Lcl Rotation", "Lcl Rotation", "", "A",0,0,0',
        '\t\t\tP: "Lcl Scaling", "Lcl Scaling", "", "A",1,1,1',
        "\t\t}", "\t\tShading: T", '\t\tCulling: "CullingOff"', "\t}", "}",
        "Connections:  {", '\tC: "OO",2000,0', '\tC: "OO",1000,2000', "}",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ───────────────────────── renderer di anteprima ─────────────────────────

def render(mesh, path, size=420, color=(120, 170, 240), yaw=35, pitch=22, bg=(236, 243, 252), wire=False):
    """Painter's algorithm con shading Lambert + rim light, per controllare le forme senza Roblox."""
    from PIL import Image, ImageDraw
    V = mesh.V.copy()
    lo, hi = V.min(axis=0), V.max(axis=0)
    c = (lo + hi) / 2
    V -= c
    radius = np.linalg.norm(hi - lo) / 2 or 1
    V /= radius
    ya, pa = math.radians(yaw), math.radians(pitch)
    Ry = np.array([[math.cos(ya), 0, math.sin(ya)], [0, 1, 0], [-math.sin(ya), 0, math.cos(ya)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(pa), -math.sin(pa)], [0, math.sin(pa), math.cos(pa)]])
    V = V @ Ry.T @ Rx.T
    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img)
    fn = np.cross(V[mesh.F[:, 1]] - V[mesh.F[:, 0]], V[mesh.F[:, 2]] - V[mesh.F[:, 0]])
    l = np.linalg.norm(fn, axis=1, keepdims=True)
    l[l == 0] = 1
    fn /= l
    depth = V[mesh.F][:, :, 2].mean(axis=1)
    order = np.argsort(depth)
    light = np.array([0.4, 0.8, 0.45])
    light /= np.linalg.norm(light)
    base = np.array(color, dtype=float)
    scale = size * 0.42
    for fi in order:
        n = fn[fi]
        if n[2] < -0.05 and not wire:
            continue  # back-face (camera guarda lungo -Z → facce verso +Z visibili)
        lam = max(0.0, float(n @ light))
        rim = max(0.0, 1 - abs(n[2])) ** 3 * 0.25
        shade = 0.28 + 0.72 * lam + rim
        col = tuple(int(min(255, v * shade)) for v in base)
        pts = [(size / 2 + V[i, 0] * scale, size / 2 - V[i, 1] * scale) for i in mesh.F[fi]]
        draw.polygon(pts, fill=col, outline=(col if not wire else (40, 40, 60)))
    img.save(path)
    return path


# ───────────────────────── glTF binario (formato accettato dall'importer Roblox) ─────────────────────────

def export_glb(mesh, path, name="Mesh"):
    """Esporta in GLB 2.0 con POSITION, NORMAL (smooth o flat), TEXCOORD_0 e indici uint32."""
    import json, struct
    if mesh.flat:
        V = mesh.V[mesh.F].reshape(-1, 3)
        N = np.repeat(mesh.face_normals(), 3, axis=0)
        UV = (mesh.UV if mesh.UV is not None else spherical_uv(mesh.V))[mesh.F].reshape(-1, 2)
        F = np.arange(len(V), dtype=np.uint32)
    else:
        V = mesh.V
        N = mesh.vertex_normals()
        UV = mesh.UV if mesh.UV is not None else spherical_uv(V)
        F = mesh.F.reshape(-1).astype(np.uint32)
    V32, N32, UV32 = V.astype(np.float32), N.astype(np.float32), UV.astype(np.float32)

    def pad4(b):
        return b + b"\x00" * ((4 - len(b) % 4) % 4)

    chunks = [V32.tobytes(), N32.tobytes(), UV32.tobytes(), F.tobytes()]
    views, offset, blob = [], 0, b""
    for c in chunks:
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(c)})
        c = pad4(c)
        blob += c
        offset += len(c)
    gltf = {
        "asset": {"version": "2.0", "generator": "VivaioMeshGen"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}, "indices": 3, "mode": 4}]}],
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": views,
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(V32), "type": "VEC3", "min": V32.min(0).tolist(), "max": V32.max(0).tolist()},
            {"bufferView": 1, "componentType": 5126, "count": len(N32), "type": "VEC3"},
            {"bufferView": 2, "componentType": 5126, "count": len(UV32), "type": "VEC2"},
            {"bufferView": 3, "componentType": 5125, "count": len(F), "type": "SCALAR"},
        ],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(b"glTF" + struct.pack("<II", 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(blob), 0x004E4942) + blob)
