"""Geometria procedurale di base: sweep di profili lungo curve, tubi, lathe, box smussati."""
from __future__ import annotations

import math

import bpy
import numpy as np

from common import link, mesh_from_arrays


def _frames(path: np.ndarray, up=(0.0, 0.0, 1.0)):
    """Frame a trasporto parallelo lungo una polilinea."""
    n = len(path)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    up = np.array(up, float)
    N = np.zeros_like(path)
    B = np.zeros_like(path)
    n0 = np.cross(T[0], up)
    if np.linalg.norm(n0) < 1e-6:
        n0 = np.cross(T[0], [1.0, 0, 0])
    n0 /= np.linalg.norm(n0)
    N[0] = n0
    B[0] = np.cross(T[0], N[0])
    for i in range(1, n):
        v = N[i - 1] - np.dot(N[i - 1], T[i]) * T[i]
        N[i] = v / (np.linalg.norm(v) + 1e-12)
        B[i] = np.cross(T[i], N[i])
    return T, N, B


def sweep(name, path, profile, col='boat', closed_profile=True, cap=True, up=(0, 0, 1), scale=None, smooth=True):
    """profile: lista di (u, v) nel piano (N, B). scale: array per punto del path (o None)."""
    path = np.asarray(path, float)
    prof = np.asarray(profile, float)
    T, N, B = _frames(path, up)
    m = len(prof)
    verts = []
    for i, p in enumerate(path):
        s = 1.0 if scale is None else scale[i]
        for u, v in prof:
            verts.append(p + s * (u * N[i] + v * B[i]))
    faces = []
    for i in range(len(path) - 1):
        for j in range(m if closed_profile else m - 1):
            a = i * m + j
            b = i * m + (j + 1) % m
            faces.append((a, b, b + m, a + m))
    if cap and closed_profile:
        faces.append(tuple(range(m - 1, -1, -1)))
        last = (len(path) - 1) * m
        faces.append(tuple(last + j for j in range(m)))
    ob = mesh_from_arrays(name, np.array(verts), faces, smooth=smooth, col=col)
    return ob


def circle_profile(r, n=12):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def rect_profile(w, h, bevel=0.0, n_round=3):
    """Rettangolo w×h centrato, con angoli arrotondati opzionali."""
    if bevel <= 0:
        return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    pts = []
    corners = [(w / 2 - bevel, h / 2 - bevel, 0), (-w / 2 + bevel, h / 2 - bevel, 90),
               (-w / 2 + bevel, -h / 2 + bevel, 180), (w / 2 - bevel, -h / 2 + bevel, 270)]
    for cx, cy, a0 in corners:
        for k in range(n_round + 1):
            a = math.radians(a0 + 90 * k / n_round)
            pts.append((cx + bevel * math.cos(a), cy + bevel * math.sin(a)))
    return pts


def tube(name, path, radius, n=12, col='boat', cap=True, taper=None):
    path = np.asarray(path, float)
    scale = None
    if taper is not None:
        scale = np.linspace(1.0, taper, len(path))
    return sweep(name, path, circle_profile(radius, n), col=col, cap=cap, scale=scale)


def lathe(name, profile_rz, n=32, col='boat', smooth=True, close_top=False, close_bottom=False):
    """profile_rz: lista (r, z) dal basso verso l'alto; rivoluzione attorno a Z."""
    prof = np.asarray(profile_rz, float)
    verts = []
    for r, z in prof:
        for k in range(n):
            a = 2 * math.pi * k / n
            verts.append((r * math.cos(a), r * math.sin(a), z))
    faces = []
    m = len(prof)
    for i in range(m - 1):
        for k in range(n):
            a = i * n + k
            b = i * n + (k + 1) % n
            faces.append((a, b, b + n, a + n))
    if close_bottom:
        c = len(verts)
        verts.append((0, 0, prof[0][1]))
        for k in range(n):
            faces.append((c, (k + 1) % n, k))
    if close_top:
        c = len(verts)
        verts.append((0, 0, prof[-1][1]))
        base = (m - 1) * n
        for k in range(n):
            faces.append((c, base + k, base + (k + 1) % n))
    return mesh_from_arrays(name, np.array(verts), faces, smooth=smooth, col=col)


def rbox(name, size, loc, rot=(0, 0, 0), bevel=0.01, segments=3, col='boat'):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        mod = ob.modifiers.new('Bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = 'ANGLE'
        mod.harden_normals = False
        bpy.ops.object.shade_smooth()
        ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
    return link(ob, col)


def cylinder(name, radius, depth, loc, rot=(0, 0, 0), verts=24, col='boat', bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    if bevel > 0:
        mod = ob.modifiers.new('Bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
    bpy.ops.object.shade_smooth()
    return link(ob, col)


def sphere(name, radius, loc, segs=24, rings=12, col='boat', scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc, segments=segs, ring_count=rings)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.shade_smooth()
    return link(ob, col)


def subdivide(ob, levels=2):
    mod = ob.modifiers.new('Subd', 'SUBSURF')
    mod.levels = levels
    mod.render_levels = levels
    return mod


def catmull(points, n=8):
    P = np.asarray(points, float)
    out = []
    for i in range(len(P) - 1):
        p0 = P[max(i - 1, 0)]
        p1, p2 = P[i], P[i + 1]
        p3 = P[min(i + 2, len(P) - 1)]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    return np.array(out)
