"""
Modellazione per campi di distanza con segno (SDF) in numpy: le creature si "scolpiscono"
unendo morbidamente primitive (sfere, ellissoidi, capsule, coni arrotondati), poi si estrae
la superficie con marching cubes e le normali dal gradiente del campo (ombreggiatura liscia).

Convenzione: f(p) < 0 dentro, > 0 fuori. p è un array (N, 3) float32.
"""
from __future__ import annotations

import math

import numpy as np

F = np.float32


def _v(x):
    return np.asarray(x, dtype=F)


# ───────────────────────── primitive ─────────────────────────

def sphere(c, r):
    c = _v(c)
    return lambda p: np.linalg.norm(p - c, axis=1) - r


def ellipsoid(c, radii):
    c, r = _v(c), _v(radii)

    def f(p):
        q = (p - c)
        k0 = np.linalg.norm(q / r, axis=1)
        k1 = np.linalg.norm(q / (r * r), axis=1)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)
    return f


def capsule(a, b, r):
    a, b = _v(a), _v(b)
    ba = b - a
    bb = float(np.dot(ba, ba))

    def f(p):
        pa = p - a
        h = np.clip((pa @ ba) / bb, 0.0, 1.0)
        return np.linalg.norm(pa - h[:, None] * ba, axis=1) - r
    return f


def round_cone(a, b, r1, r2):
    """Cono arrotondato da a (raggio r1) a b (raggio r2) — Inigo Quilez."""
    a, b = _v(a), _v(b)
    ba = b - a
    l2 = float(np.dot(ba, ba))
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2

    def f(p):
        pa = p - a
        y = pa @ ba
        z = y - l2
        xv = pa * l2 - y[:, None] * ba
        x2 = np.einsum('ij,ij->i', xv, xv)
        y2 = y * y * l2
        z2 = z * z * l2
        k = np.sign(rr) * rr * rr * x2
        out = np.empty(len(p), dtype=F)
        c1 = np.sign(z) * a2 * z2 > k
        c2 = (~c1) & (np.sign(y) * a2 * y2 < k)
        c3 = ~(c1 | c2)
        out[c1] = np.sqrt(x2[c1] + z2[c1]) * il2 - r2
        out[c2] = np.sqrt(x2[c2] + y2[c2]) * il2 - r1
        out[c3] = (np.sqrt(x2[c3] * a2 * il2) + y[c3] * rr) * il2 - r1
        return out
    return f


def torus(c, R, r, axis='z'):
    c = _v(c)
    ax = {'x': 0, 'y': 1, 'z': 2}[axis]
    others = [i for i in range(3) if i != ax]

    def f(p):
        q = p - c
        qx = np.sqrt(q[:, others[0]] ** 2 + q[:, others[1]] ** 2) - R
        return np.sqrt(qx * qx + q[:, ax] ** 2) - r
    return f


def box(c, half, rounding=0.0):
    c, h = _v(c), _v(half)

    def f(p):
        q = np.abs(p - c) - (h - rounding)
        outside = np.linalg.norm(np.maximum(q, 0.0), axis=1)
        inside = np.minimum(np.max(q, axis=1), 0.0)
        return outside + inside - rounding
    return f


def plane(n, d):
    """Semispazio n·p + d < 0 dentro."""
    n = _v(n) / np.linalg.norm(n)
    return lambda p: p @ n + d


# ───────────────────────── operazioni ─────────────────────────

def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def union(*fs, k=0.0):
    def f(p):
        d = fs[0](p)
        for g in fs[1:]:
            e = g(p)
            d = smin(d, e, k) if k > 0 else np.minimum(d, e)
        return d
    return f


def subtract(a, b, k=0.0):
    """a meno b."""
    def f(p):
        da, db = a(p), b(p)
        return smax(da, -db, k) if k > 0 else np.maximum(da, -db)
    return f


def intersect(a, b, k=0.0):
    def f(p):
        da, db = a(p), b(p)
        return smax(da, db, k) if k > 0 else np.maximum(da, db)
    return f


def shell(a, thickness):
    return lambda p: np.abs(a(p)) - thickness


def translate(a, t):
    t = _v(t)
    return lambda p: a(p - t)


def rotate(a, R, center=(0, 0, 0)):
    """R: matrice 3×3 (rotazione dell'oggetto)."""
    R = np.asarray(R, dtype=F)
    c = _v(center)
    return lambda p: a((p - c) @ R + c)


def mirror_x(a):
    def f(p):
        q = p.copy()
        q[:, 0] = np.abs(q[:, 0])
        return a(q)
    return f


def displace(a, g, amount):
    return lambda p: a(p) - amount * g(p)


def rot_matrix(axis, deg):
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    if axis == 'x':
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], F)
    if axis == 'y':
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], F)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], F)


# ───────────────────────── rumore ─────────────────────────

class Noise3:
    """Rumore a valori su reticolo 3D (liscio, deterministico), per pelle e bitorzoli."""

    def __init__(self, seed=0):
        r = np.random.default_rng(seed)
        self.perm = np.concatenate([r.permutation(256)] * 2).astype(np.int64)
        self.vals = r.uniform(-1, 1, 256).astype(F)

    def _h(self, ix, iy, iz):
        p = self.perm
        return self.vals[p[p[p[ix & 255] + (iy & 255)] + (iz & 255)]]

    def __call__(self, p, scale=1.0, octaves=3):
        out = np.zeros(len(p), F)
        amp, norm = 1.0, 0.0
        q = p / scale
        for o in range(octaves):
            x, y, z = q[:, 0] + o * 31.7, q[:, 1] + o * 17.1, q[:, 2] + o * 7.3
            ix, iy, iz = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64), np.floor(z).astype(np.int64)
            fx, fy, fz = x - ix, y - iy, z - iz
            ux, uy, uz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
            acc = np.zeros(len(p), F)
            for dx in (0, 1):
                wx = ux if dx else 1 - ux
                for dy in (0, 1):
                    wy = uy if dy else 1 - uy
                    for dz in (0, 1):
                        wz = uz if dz else 1 - uz
                        acc += wx * wy * wz * self._h(ix + dx, iy + dy, iz + dz)
            out += amp * acc
            norm += amp
            amp *= 0.5
            q = q * 2.0
        return out / norm


def warts(seed, center, extent, count, radius):
    """Campo di bitorzoli: 1 sul centro di ogni verruca, 0 lontano. Usa un KD-tree."""
    from scipy.spatial import cKDTree
    r = np.random.default_rng(seed)
    pts = _v(center) + (r.random((count, 3)).astype(F) - 0.5) * 2 * _v(extent)
    rad = r.uniform(0.5, 1.0, count).astype(F) * radius
    tree = cKDTree(pts)

    def f(p):
        d, i = tree.query(p, k=1, workers=-1)
        x = np.clip(1.0 - d / rad[i], 0.0, 1.0)
        return (x * x * (3 - 2 * x)).astype(F)
    return f


# ───────────────────────── estrazione della superficie ─────────────────────────

def mesh(field, lo, hi, res=0.006, chunk=2_000_000):
    """Marching cubes sul campo nel box [lo, hi]. Restituisce (verts, faces, normals)."""
    from skimage.measure import marching_cubes
    lo, hi = _v(lo), _v(hi)
    n = np.ceil((hi - lo) / res).astype(int) + 1
    xs = np.linspace(lo[0], hi[0], n[0], dtype=F)
    ys = np.linspace(lo[1], hi[1], n[1], dtype=F)
    zs = np.linspace(lo[2], hi[2], n[2], dtype=F)
    vol = np.empty((n[0], n[1], n[2]), F)
    # valutazione a fette per contenere la memoria
    YY, ZZ = np.meshgrid(ys, zs, indexing='ij')
    yz = np.stack([YY.ravel(), ZZ.ravel()], axis=1)
    step = max(1, chunk // len(yz))
    for i0 in range(0, n[0], step):
        i1 = min(n[0], i0 + step)
        P = np.empty(((i1 - i0) * len(yz), 3), F)
        P[:, 0] = np.repeat(xs[i0:i1], len(yz))
        P[:, 1:] = np.tile(yz, (i1 - i0, 1))
        vol[i0:i1] = field(P).reshape(i1 - i0, n[1], n[2])
    spacing = tuple(float((hi[k] - lo[k]) / (n[k] - 1)) for k in range(3))
    verts, faces, _, _ = marching_cubes(vol, level=0.0, spacing=spacing)
    verts = verts.astype(F) + lo
    normals = gradient_normals(field, verts, res * 0.5)
    # orienta i triangoli come il gradiente (normali verso l'esterno)
    a, b, c = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    fn = np.cross(b - a, c - a)
    agree = np.einsum('ij,ij->i', fn, normals[faces[:, 0]] + normals[faces[:, 1]] + normals[faces[:, 2]])
    if np.mean(agree > 0) < 0.5:
        faces = faces[:, ::-1]
    return verts, faces, normals


def gradient_normals(field, pts, eps):
    e = F(eps)
    g = np.empty_like(pts)
    for k in range(3):
        d = np.zeros(3, F)
        d[k] = e
        g[:, k] = field(pts + d) - field(pts - d)
    g /= np.linalg.norm(g, axis=1, keepdims=True) + 1e-12
    return g
