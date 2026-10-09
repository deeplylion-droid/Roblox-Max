"""
Dettagli delle creature, da scegliere insieme (dopo le sagome C scelte dall'utente).

Per ogni creatura tre varianti della testa, da "più pesce" (A) a "più bambino" (C), con addosso
l'oggetto del parco: il salvagente a paperella (Gulpy), i braccioli (Molly), il giocattolo
luminoso (Hatch). Bozze di studio: non sono i modelli definitivi del gioco.

Uso: tools/.venv/bin/python tools/render/dettagli.py [gulpy|molly|hatch|all] [--fast] [--only A|B|C]
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import sdf  # noqa: E402
from common import CACHE, ROOT, reset_scene, set_lightgroup  # noqa: E402
from creature import eye_material, eyeball, sdf_object, skin_material, teeth_material  # noqa: E402
from geo import catmull, rbox, tube  # noqa: E402
from nodes import material  # noqa: E402

OUT = os.path.join(ROOT, 'docs', 'concept')
TMP = os.path.join(CACHE, 'dettagli')
F = np.float32
FAST = '--fast' in sys.argv
RES = 0.008 if FAST else 0.0045


def V(*a):
    return np.array(a, F)


def unit(v):
    v = np.asarray(v, F)
    return v / np.linalg.norm(v)


def chain(points, radii, k=0.03):
    parts = [sdf.round_cone(points[i], points[i + 1], radii[i], radii[i + 1]) for i in range(len(points) - 1)]
    return sdf.union(*parts, k=k) if k > 0 else sdf.union(*parts)


def torus_axis(c, n, R, r):
    """Toro con asse qualsiasi."""
    c, n = V(*c), unit(n)

    def f(p):
        q = p - c
        h = q @ n
        rad = q - h[:, None] * n
        return np.sqrt((np.linalg.norm(rad, axis=1) - R) ** 2 + h * h) - r
    return f


def ellipsoid_rot(c, radii, R):
    return sdf.rotate(sdf.ellipsoid(c, radii), R, center=c)


def above(q, up):
    """Semispazio dalla parte di 'up' rispetto al piano per q (dentro dove (p-q)·up > 0)."""
    up = unit(up)
    return sdf.plane(-up, float(np.dot(V(*q), up)))


class Frame:
    """Sistema locale di una testa: costruita dritta (faccia verso −Y, alto +Z), poi inclinata e spostata."""

    def __init__(self, pos, pitch=0.0, yaw=0.0):
        self.pos = V(*pos)
        self.R = (sdf.rot_matrix('z', yaw) @ sdf.rot_matrix('x', pitch)).astype(F)

    def field(self, f):
        """Campo locale → mondo."""
        R, c = self.R, self.pos
        return lambda p: f((p - c) @ R)

    def pt(self, q):
        return self.pos + self.R @ V(*q)

    def dir(self, d):
        return self.R @ V(*d)


def smooth01(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ───────────────────────── materiali ─────────────────────────

def mat_simple(name, color, rough=0.4, **kw):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    g.output_material(g.principled(color=color, rough=rough, **kw))
    return m


def pale_skin(name='PaleSkin', base=(0.20, 0.215, 0.205), dark=(0.065, 0.075, 0.08), belly=(0.30, 0.30, 0.285), irid=0.0):
    """La pelle di famiglia: grigio pallido tendente al verde, bagnata, a chiazze."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    return skin_material(name, base=base, dark=dark, belly=belly, accent=(0.26, 0.25, 0.22), rough=0.55, coat=0.35,
                         sss=0.12, sss_radius=(1.0, 0.45, 0.3), spots_scale=5.0, spots_amount=0.8, bump_scale=55.0,
                         bump=0.45, mouth=(0.10, 0.015, 0.02), irid=irid)


def milky_eye():
    m = bpy.data.materials.get('MilkEye')
    if m:
        return m
    return eye_material('MilkEye', iris=(0.80, 0.82, 0.80), iris_dark=(0.58, 0.60, 0.60), pupil='round', pupil_size=0.15,
                        shine=(0.7, 0.88, 1.0), shine_strength=0.9, sclera=(0.70, 0.70, 0.66))


def vinyl(name, color, stain=(0.25, 0.28, 0.12)):
    """Plastica gonfiabile scolorita, con macchie d'alga."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    n = g.noise(co, scale=14.0, detail=5.0, rough=0.6)
    dirt = g.smoothstep(0.55, 0.78, n.fac)
    col = g.mix(g.mul(dirt, 0.7), color, stain)
    g.output_material(g.principled(color=col, rough=0.32, coat=0.4, coat_rough=0.1, spec=0.6))
    return m


def glass(name, tint=(0.85, 1.0, 0.9), rough=0.03, ior=1.34):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    g.output_material(g.principled(color=tint, rough=rough, transmission=1.0, ior=ior, coat=0.5, coat_rough=0.02))
    return m


def glow(name, color, strength=5.0, base=None):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    g.output_material(g.principled(color=base or color, rough=0.3, emission=color, emission_strength=strength))
    return m


def wet_hair():
    return mat_simple('WetHair', (0.018, 0.016, 0.015), rough=0.22, coat=0.7, coat_rough=0.05)


def dark_throat():
    return mat_simple('Throat', (0.012, 0.002, 0.003), rough=0.45, coat=0.3)


def needle_teeth():
    m = bpy.data.materials.get('NeedleTeeth')
    if m:
        return m
    m, g = material('NeedleTeeth')
    g.output_material(g.principled(color=(0.85, 0.82, 0.70), rough=0.12, transmission=0.55, ior=1.5, sss=0.3,
                                   sss_radius=(1, 0.9, 0.7), sss_scale=0.004, coat=0.6))
    return m


# ───────────────────────── oggetti ─────────────────────────

def mesh(name, field, lo, hi, mat, res=None, attrs=None):
    ob = sdf_object(name, field, lo, hi, res=res or RES, attrs=attrs)
    ob.data.materials.append(mat)
    return ob


def teeth_mesh(name, pairs, mat=None):
    """pairs: [(base, tip, r)] → un'unica mesh di denti conici."""
    parts = [sdf.round_cone(b, t, r, r * 0.15) for b, t, r in pairs]
    pts = np.array([p for b, t, _ in pairs for p in (b, t)], F)
    lo, hi = pts.min(0) - 0.02, pts.max(0) + 0.02
    rmin = min(r for _, _, r in pairs)
    return mesh(name, sdf.union(*parts), lo, hi, mat or teeth_material(), res=max(min(RES, rmin / 2.5), 0.0012))


def eyes(prefix, centers, radius, look, mat=None):
    return [eyeball(f'{prefix}{i}', tuple(map(float, c)), radius, mat or milky_eye(), look=tuple(map(float, unit(look))))
            for i, c in enumerate(centers)]


def point_light(name, loc, energy, color, radius=0.01):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    set_lightgroup(ob, 'ambient')
    return ob


def area_light(name, loc, target, energy, color, size):
    from mathutils import Vector
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.color = color
    ld.size = size
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = d.to_track_quat('-Z', 'Y')
    set_lightgroup(ob, 'ambient')
    return ob


def duck_ring(c, axis, R=0.135, r=0.055, up=(0, -1, 1)):
    """Il salvagente a paperella: anello gonfiabile giallo con la testa di papera davanti."""
    axis = unit(axis)
    u = np.asarray(up, F) - (np.asarray(up, F) @ axis) * axis
    u = unit(u)
    ring = torus_axis(c, axis, R, r)
    obs = [mesh('DuckRing', ring, V(*c) - (R + r + 0.02), V(*c) + (R + r + 0.02), vinyl('DuckVinyl', (0.86, 0.62, 0.10)), res=min(RES, 0.006))]
    base = V(*c) + u * (R + r * 0.4)
    head = base + u * 0.075 + V(0, -0.025, 0)
    fwd = unit(V(0, -1, -0.15))
    f = sdf.union(sdf.capsule(base, head, 0.045), sdf.sphere(head, 0.062), k=0.03)
    obs.append(mesh('DuckHead', f, np.minimum(base, head) - 0.09, np.maximum(base, head) + 0.09, vinyl('DuckVinyl', (0.86, 0.62, 0.10)), res=min(RES, 0.005)))
    bk = head + fwd * 0.07 + V(0, 0, -0.012)
    beak = ellipsoid_rot(bk, (0.040, 0.042, 0.016), np.eye(3, dtype=F))
    obs.append(mesh('DuckBeak', beak, bk - 0.06, bk + 0.06, vinyl('DuckBeakVinyl', (0.92, 0.33, 0.05)), res=0.003))
    for s in (-1, 1):
        e = head + V(s * 0.032, -0.047, 0.022)
        obs.append(mesh(f'DuckEye{s}', sdf.sphere(e, 0.0105), e - 0.02, e + 0.02, mat_simple('DuckEyePaint', (0.01, 0.01, 0.01), rough=0.2), res=0.0015))
    return obs


def armband(c, axis, color=(0.95, 0.40, 0.06)):
    """Bracciolo gonfiabile a due camere attorno all'avambraccio."""
    axis = unit(axis)
    f = sdf.union(torus_axis(V(*c) + axis * 0.024, axis, 0.050, 0.030), torus_axis(V(*c) - axis * 0.024, axis, 0.050, 0.030), k=0.012)
    obs = [mesh('Armband', f, V(*c) - 0.12, V(*c) + 0.12, vinyl('ArmbandVinyl', color), res=min(RES, 0.004))]
    band = torus_axis(c, axis, 0.074, 0.006)
    obs.append(mesh('ArmbandSeam', band, V(*c) - 0.10, V(*c) + 0.10, vinyl('ArmbandWhite', (0.85, 0.82, 0.74)), res=0.003))
    return obs


def toy_fish(pos, light=1.0):
    """Il giocattolo luminoso del parco: un pesciolino di plastica trasparente con la lucina dentro."""
    p = V(*pos)
    body = sdf.union(ellipsoid_rot(p, (0.022, 0.016, 0.034), np.eye(3, dtype=F)),
                     sdf.round_cone(p + V(0, 0, 0.026), p + V(0, 0, 0.050), 0.010, 0.020), k=0.008)
    tail = sdf.intersect(sdf.ellipsoid(p + V(0, 0, 0.058), (0.004, 0.022, 0.016)), above(p + V(0, 0, 0.048), (0, 0, 1)))
    f = sdf.union(body, tail, k=0.004)
    obs = [mesh('ToyFish', f, p - 0.08, p + 0.10, glow('ToyGlow', (0.20, 0.95, 0.75), 1.6, base=(0.15, 0.75, 0.6)), res=0.002)]
    for s in (-1, 1):
        e = p + V(s * 0.0165, -0.004, -0.012)
        obs.append(mesh(f'ToyEye{s}', sdf.sphere(e, 0.0045), e - 0.01, e + 0.01, mat_simple('ToyEyePaint', (0.02, 0.02, 0.03), rough=0.2), res=0.001))
    ring = torus_axis(p + V(0, 0, 0.062), (1, 0, 0), 0.008, 0.0016)
    obs.append(mesh('ToyRing', ring, p - 0.03 + V(0, 0, 0.06), p + 0.03 + V(0, 0, 0.06), mat_simple('ToyRingMetal', (0.7, 0.7, 0.7), rough=0.25, metal=1.0), res=0.001))
    point_light('ToyLight', tuple(map(float, p)), light, (0.35, 1.0, 0.85), radius=0.02)
    return obs


def hair_clump(points, r0=0.012, r1=0.002):
    """Ciocca di capelli bagnati: tubo che si assottiglia, appiccicato alle forme."""
    pts = catmull(points, 8)
    n = len(pts)
    return sdf.union(*[sdf.round_cone(pts[i], pts[i + 1], r0 + (r1 - r0) * i / n, r0 + (r1 - r0) * (i + 1) / n) for i in range(n - 1)])


def stalk(points, r0=0.010, r1=0.005, name='Stalk'):
    """Il peduncolo dell'esca: tubo di carne che si assottiglia."""
    pts = catmull(points, 10)
    n = len(pts)
    f = sdf.union(*[sdf.round_cone(pts[i], pts[i + 1], r0 + (r1 - r0) * i / n, r0 + (r1 - r0) * (i + 1) / n) for i in range(n - 1)])
    return mesh(name, f, pts.min(0) - 0.03, pts.max(0) + 0.03, pale_skin(), res=min(RES, 0.003))


# ───────────────────────── GULPY (sagoma C «Avvoltoio») ─────────────────────────
# Gigante curvo in piedi nell'acqua: la testa pende davanti al petto. Faccia verso −Y.

NECK_RING_C = V(0, -0.635, 2.355)
NECK_RING_AXIS = unit((0, -0.22, -0.22))


def gulpy_body():
    back = chain([V(0, 0.22, 1.00), V(0, 0.17, 1.55), V(0, 0.05, 2.05), V(0, -0.15, 2.42), V(0, -0.30, 2.52)], [0.17, 0.19, 0.20, 0.18, 0.13], k=0.06)
    chest = sdf.ellipsoid(V(0, -0.08, 1.78), (0.19, 0.15, 0.36))
    sh = sdf.union(sdf.ellipsoid(V(0.25, -0.05, 2.25), (0.12, 0.13, 0.10)), sdf.ellipsoid(V(-0.25, -0.05, 2.25), (0.12, 0.13, 0.10)), k=0.1)
    neck = chain([V(0, -0.28, 2.50), V(0, -0.52, 2.46), V(0, -0.74, 2.24), V(0, -0.84, 2.03)], [0.105, 0.098, 0.10, 0.09], k=0.04)
    # carne gonfia sopra e sotto il salvagente che stringe
    bulge = sdf.union(sdf.sphere(NECK_RING_C - NECK_RING_AXIS * 0.075, 0.112), sdf.sphere(NECK_RING_C + NECK_RING_AXIS * 0.075, 0.11), k=0.03)
    pinch = torus_axis(NECK_RING_C, NECK_RING_AXIS, 0.13, 0.05)
    spine_pts = catmull([V(0, 0.17, 1.55), V(0, 0.05, 2.05), V(0, -0.15, 2.42), V(0, -0.30, 2.52)], 3)
    bumps = []
    for i, c in enumerate(spine_pts[1:-1]):
        t = i / max(1, len(spine_pts) - 3)
        n = unit(V(0, 1.0 - 0.9 * t, 0.25 + 1.2 * t))
        bumps.append(sdf.sphere(c + n * (0.19 - 0.05 * t), 0.042))
    spine = sdf.union(*bumps)
    arms = []
    for s in (-1, 1):
        arms.append(chain([V(s * 0.27, -0.04, 2.22), V(s * 0.37, -0.22, 1.72), V(s * 0.33, -0.50, 1.32), V(s * 0.20, -0.72, 1.12)], [0.062, 0.045, 0.04, 0.034], k=0.03))
        arms.append(sdf.ellipsoid(V(s * 0.37, -0.22, 1.72), (0.05, 0.05, 0.05)))   # gomiti ossuti
        for j, dx in enumerate((-0.04, -0.013, 0.013, 0.04)):
            w = V(s * 0.20, -0.72, 1.12)
            k1 = w + V(s * 0.6 * dx, -0.08, -0.03)
            k2 = k1 + V(s * dx * 0.8, -0.12, -0.10)
            arms.append(chain([w, k1, k2], [0.022, 0.016, 0.010], k=0.01))
    body = sdf.union(back, chest, sh, neck, bulge, spine, *arms, k=0.05)
    body = sdf.subtract(body, pinch, k=0.02)

    def ribs(p):
        front = smooth01(-(p[:, 1] + 0.05), 0.0, 0.12) * smooth01(p[:, 2], 1.45, 1.6) * (1 - smooth01(p[:, 2], 2.05, 2.15))
        return (np.sin(p[:, 2] * 52.0) * 0.5 + 0.5) * front

    return sdf.displace(body, ribs, -0.0035)


def gulpy_gills():
    return sdf.union(*[ellipsoid_rot(V(s * 0.097, -0.775 - 0.012 * i, 2.19 - 0.04 * i), (0.008, 0.012, 0.034), sdf.rot_matrix('x', 25)) for s in (-1, 1) for i in range(3)])


def gulpy_finish(head_field, extra_cut=None, attrs=None):
    f = sdf.union(gulpy_body(), head_field, k=0.035)
    f = sdf.subtract(f, gulpy_gills(), k=0.006)
    if extra_cut is not None:
        f = sdf.subtract(f, extra_cut, k=0.008)
    obs = [mesh('GulpySkin', f, V(-0.62, -1.18, 1.0), V(0.62, 0.55, 2.72), pale_skin(), attrs=attrs)]
    obs += duck_ring(NECK_RING_C, NECK_RING_AXIS)
    return obs


def gulpy_a():
    """A · Sacco: becco lungo e piatto, occhietti alla base; sotto il becco un sacco di pelle che pende."""
    fr = Frame((0, -0.905, 1.975), pitch=52)
    skull = sdf.union(sdf.ellipsoid(V(0, 0, 0), (0.078, 0.09, 0.072)), sdf.ellipsoid(V(0, 0.02, 0.05), (0.03, 0.08, 0.03)), k=0.03)
    bill = sdf.union(sdf.ellipsoid(V(0, -0.21, -0.025), (0.052, 0.20, 0.022)), sdf.ellipsoid(V(0, -0.39, -0.03), (0.022, 0.03, 0.016)), k=0.02)
    rims = sdf.union(*[chain([V(s * 0.05, -0.04, -0.045), V(s * 0.05, -0.22, -0.055), V(s * 0.016, -0.40, -0.04)], [0.012, 0.010, 0.007], k=0.006) for s in (-1, 1)])
    head = fr.field(sdf.union(skull, bill, rims, k=0.02))
    obs = gulpy_finish(head)
    pouch = fr.field(sdf.union(sdf.ellipsoid(V(0, -0.20, -0.11), (0.062, 0.18, 0.10)), sdf.sphere(V(0, -0.12, -0.20), 0.085), k=0.07))
    c0 = fr.pt((0, -0.15, -0.12))
    obs.append(mesh('Pouch', pouch, c0 - 0.30, c0 + 0.30, pouch_material(), res=min(RES, 0.005)))
    for i, (q, ang) in enumerate((((0.02, -0.12, -0.20), 20), ((-0.025, -0.24, -0.12), -35), ((0.0, -0.06, -0.15), 80))):
        c = fr.pt(q)
        fish = fr.field(ellipsoid_rot(V(*q), (0.018, 0.055, 0.024), sdf.rot_matrix('x', ang)))
        obs.append(mesh(f'SwallowedFish{i}', fish, c - 0.08, c + 0.08, mat_simple('SwallowedFish', (0.03, 0.035, 0.03), rough=0.4), res=0.004))
    obs += eyes('GulpyEye', [fr.pt((s * 0.05, -0.055, 0.02)) for s in (-1, 1)], 0.0145, fr.dir((0, -1, 0.1)))
    return obs, 'A · Sacco', 'più pesce: becco lungo, occhietti alla base;\nla gola è un sacco di pelle trasparente,\npieno di quello che ha mangiato'


def pouch_material():
    m = bpy.data.materials.get('PouchSkin')
    if m:
        return m
    m, g = material('PouchSkin')
    co = g.texcoord('Object')
    veins = g.voronoi(co, scale=22.0, feature='DISTANCE_TO_EDGE')
    vmask = g.smoothstep(0.035, 0.0, veins)
    col = g.mix(g.mul(vmask, 0.8), (0.55, 0.45, 0.42), (0.30, 0.06, 0.08))
    g.output_material(g.principled(color=col, rough=0.3, transmission=0.45, ior=1.36, sss=0.6, sss_radius=(1.0, 0.5, 0.4),
                                   sss_scale=0.03, coat=0.6, coat_rough=0.05))
    return m


def gulpy_b():
    """B · Cerniera: cranio allungato da quasi-uomo; la mascella sganciata pende fino al petto."""
    fr = Frame((0, -0.905, 1.985), pitch=32)
    cran = sdf.ellipsoid(V(0, 0.01, 0.03), (0.10, 0.11, 0.12))
    brow = sdf.ellipsoid(V(0, -0.085, 0.035), (0.088, 0.038, 0.028))
    maxilla = chain([V(0, -0.07, -0.02), V(0, -0.115, -0.10), V(0, -0.12, -0.145)], [0.078, 0.058, 0.05], k=0.02)
    cheekbones = sdf.union(sdf.sphere(V(0.068, -0.075, -0.025), 0.03), sdf.sphere(V(-0.068, -0.075, -0.025), 0.03))
    jaw = sdf.union(chain([V(0, -0.12, -0.38), V(0, -0.13, -0.47)], [0.05, 0.042], k=0.01),
                    *[chain([V(s * 0.068, -0.10, -0.39), V(s * 0.085, -0.055, -0.20), V(s * 0.09, -0.01, -0.06)], [0.019, 0.015, 0.017], k=0.01) for s in (-1, 1)])
    membrane = sdf.union(*[sdf.ellipsoid(V(s * 0.08, -0.05, -0.22), (0.009, 0.05, 0.17)) for s in (-1, 1)])
    head = sdf.union(cran, brow, maxilla, cheekbones, jaw, membrane, k=0.03)
    cut = sdf.union(sdf.sphere(V(0.09, -0.115, -0.08), 0.032), sdf.sphere(V(-0.09, -0.115, -0.08), 0.032),
                    sdf.sphere(V(0.044, -0.115, 0.0), 0.021), sdf.sphere(V(-0.044, -0.115, 0.0), 0.021),
                    sdf.ellipsoid(V(0.015, -0.165, -0.085), (0.006, 0.01, 0.014)), sdf.ellipsoid(V(-0.015, -0.165, -0.085), (0.006, 0.01, 0.014)),
                    sdf.ellipsoid(V(0, -0.115, -0.265), (0.058, 0.07, 0.115)))
    obs = gulpy_finish(fr.field(head), extra_cut=fr.field(cut))
    th = fr.field(sdf.ellipsoid(V(0, -0.06, -0.265), (0.062, 0.05, 0.13)))
    c0 = fr.pt((0, -0.06, -0.265))
    obs.append(mesh('GulpyThroat', th, c0 - 0.18, c0 + 0.18, dark_throat(), res=0.005))
    pairs = []
    for i in range(9):
        t = i / 8 - 0.5
        x = t * 0.10
        y = -0.14 + abs(t) * 0.05
        pairs.append((fr.pt((x, y, -0.14)), fr.pt((x * 0.9, y + 0.008, -0.14 - 0.04 * (1 - abs(t)))), 0.0065))
        pairs.append((fr.pt((x, y + 0.005, -0.385)), fr.pt((x * 0.9, y + 0.012, -0.385 + 0.04 * (1 - abs(t)))), 0.006))
    obs.append(teeth_mesh('GulpyTeeth', pairs, needle_teeth()))
    obs += eyes('GulpyEye', [fr.pt((s * 0.044, -0.105, 0.0)) for s in (-1, 1)], 0.0165, fr.dir((0, -1, 0.05)))
    return obs, 'B · Cerniera', 'a metà: cranio da quasi-uomo,\nla mascella sganciata\npende sul petto'


def gulpy_c():
    """C · Bambino: la faccia del bambino dello Snack Shack, piccola sul corpo enorme; la bocca è uno
    spacco verticale che dal labbro scende sotto il mento."""
    fr = Frame((0, -0.905, 1.975), pitch=38)
    head = sdf.union(sdf.sphere(V(0, 0, 0), 0.115), sdf.ellipsoid(V(0, -0.06, -0.04), (0.094, 0.07, 0.095)),
                     sdf.sphere(V(0.056, -0.095, -0.075), 0.033), sdf.sphere(V(-0.056, -0.095, -0.075), 0.033),
                     sdf.sphere(V(0, -0.105, -0.125), 0.03), sdf.sphere(V(0, -0.142, -0.045), 0.0135),
                     sdf.ellipsoid(V(0, -0.098, 0.012), (0.072, 0.024, 0.016)),
                     sdf.ellipsoid(V(0.114, 0.0, -0.01), (0.014, 0.027, 0.037)), sdf.ellipsoid(V(-0.114, 0.0, -0.01), (0.014, 0.027, 0.037)),
                     k=0.03)
    sockets = sdf.union(sdf.sphere(V(0.042, -0.112, -0.012), 0.021), sdf.sphere(V(-0.042, -0.112, -0.012), 0.021))
    split = sdf.union(ellipsoid_rot(V(0, -0.118, -0.135), (0.013, 0.045, 0.065), sdf.rot_matrix('x', -25)),
                      ellipsoid_rot(V(0.029, -0.128, -0.093), (0.025, 0.02, 0.005), sdf.rot_matrix('y', -28)),
                      ellipsoid_rot(V(-0.029, -0.128, -0.093), (0.025, 0.02, 0.005), sdf.rot_matrix('y', 28)))
    Rt = fr.R.T

    def loc(p):
        return (p - fr.pos) @ fr.R

    def blush(p):
        q = loc(p)
        d = np.minimum(np.linalg.norm(q - V(0.058, -0.11, -0.07), axis=1), np.linalg.norm(q - V(-0.058, -0.11, -0.07), axis=1))
        return np.clip(1.0 - d / 0.04, 0.0, 1.0)

    def dark(p):
        q = loc(p)
        d = np.minimum(np.linalg.norm(q - V(0.042, -0.115, -0.012), axis=1), np.linalg.norm(q - V(-0.042, -0.115, -0.012), axis=1))
        sock = np.clip(1.0 - (d - 0.01) / 0.015, 0.0, 1.0)
        r = q - V(0, -0.118, -0.135)
        slit = np.clip(1.0 - np.abs(r[:, 0]) / 0.016, 0, 1) * np.clip(1.0 - np.abs(r[:, 2]) / 0.075, 0, 1) * (q[:, 1] > -0.14)
        return np.maximum(sock, slit)

    _ = Rt
    obs = gulpy_finish(fr.field(head), extra_cut=fr.field(sdf.union(sockets, split)), attrs={'blush': blush, 'mouth': dark})
    th = fr.field(ellipsoid_rot(V(0, -0.095, -0.135), (0.010, 0.035, 0.055), sdf.rot_matrix('x', -25)))
    c0 = fr.pt((0, -0.095, -0.135))
    obs.append(mesh('GulpyThroat', th, c0 - 0.09, c0 + 0.09, dark_throat(), res=0.003))
    pairs = []
    for i in range(10):
        t = i / 9
        z = -0.185 + 0.085 * t
        y = -0.105 - 0.03 * t
        for sx in (-1, 1):
            pairs.append((fr.pt((sx * 0.013, y, z)), fr.pt((sx * 0.004, y - 0.004, z - 0.003)), 0.0032))
    obs.append(teeth_mesh('GulpyTeeth', pairs))
    obs += eyes('GulpyEye', [fr.pt((sx * 0.042, -0.105, -0.012)) for sx in (-1, 1)], 0.0165, fr.dir((0, -1, 0.05)))
    strands = []
    for a in np.linspace(-1, 1, 7):
        d0 = unit(V(0.10 * a, 0.35, 1.0))
        d1 = unit(V(0.50 * a, -0.20, 0.95))
        d2 = unit(V(0.62 * a, -0.55, 0.62))
        strands.append(hair_clump([fr.pt(d * 0.117) for d in (d0, d1, d2)], 0.010, 0.003))
    obs.append(mesh('GulpyHair', sdf.union(*strands, k=0.008), fr.pos - 0.16, fr.pos + 0.16, wet_hair(), res=min(RES, 0.003)))
    return obs, 'C · Bambino', 'più bambino: la faccia del bambino dello\nSnack Shack, piccola sul corpo enorme;\nla bocca si apre in verticale, sotto il mento'


# ───────────────────────── MOLLY (sagoma C «Dita») ─────────────────────────
# Quasi tutta sott'acqua: testa e dita lunghissime aggrappate al bordo. Vista dal posto del pescatore:
# il bordo corre lungo X a y=0; dentro la barca è y<0 (verso la camera), fuori y>0.

GUN_TOP = 0.785


def molly_scene():
    obs = []
    wood = mat_simple('GunwaleWood', (0.12, 0.035, 0.018), rough=0.35, coat=0.6)
    paint = mat_simple('HullTeal', (0.07, 0.20, 0.20), rough=0.55)
    obs.append(rbox('Gunwale', (1.6, 0.075, 0.045), (0, 0.0, GUN_TOP - 0.0225), bevel=0.01, col='set'))
    obs[-1].data.materials.append(wood)
    wall = rbox('HullWall', (1.6, 0.02, 0.62), (0, -0.03, GUN_TOP - 0.045 - 0.31), bevel=0.0, col='set')
    wall.data.materials.append(paint)
    obs.append(wall)
    for x in (-0.55, 0.55):
        rib = rbox('Rib', (0.04, 0.03, 0.6), (x, -0.05, GUN_TOP - 0.36), bevel=0.006, col='set')
        rib.data.materials.append(paint)
        obs.append(rib)
    water = rbox('Water', (8, 8, 0.01), (0, 4.03, 0.0), bevel=0.0, col='set')
    water.data.materials.append(mat_simple('NightWater', (0.004, 0.012, 0.016), rough=0.04, spec=0.8))
    obs.append(water)
    for o in obs:
        set_lightgroup(o, 'ambient')
    return obs


def molly_hands():
    """Due mani con dita lunghissime e palmate agganciate al bordo; avambracci col bracciolo."""
    parts, bands, tips = [], [], []
    for s in (-1, 1):
        hx = s * 0.25
        wrist = V(hx, 0.075, GUN_TOP + 0.075)
        fa = V(hx * 1.12, 0.19, 0.62)
        parts.append(sdf.ellipsoid(V(hx, 0.045, GUN_TOP + 0.045), (0.062, 0.045, 0.026)))
        parts.append(chain([V(hx * 1.25, 0.26, 0.25), fa, wrist], [0.032, 0.03, 0.026], k=0.02))
        for j, (dx, L, bend) in enumerate(((-0.056, 0.80, 0.004), (-0.019, 1.0, -0.003), (0.019, 0.95, 0.002), (0.056, 0.72, -0.004))):
            x = hx + dx
            k0 = V(x, 0.036, GUN_TOP + 0.032)
            k1 = V(x + bend, -0.004, GUN_TOP + 0.046)
            k2 = V(x + bend * 1.5, -0.056, GUN_TOP + 0.008)
            k3 = V(x + bend * 2.5, -0.066, GUN_TOP - 0.13 * L)
            k4 = V(x + bend * 3.0, -0.052, GUN_TOP - 0.245 * L)
            parts.append(hair_clump([k0, k1, k2, k3, k4], 0.0135, 0.0062))
            tips.append((k4, unit(k4 - k3)))
        for j in range(3):
            a = hx - 0.056 + 0.0373 * j + 0.0187
            parts.append(sdf.ellipsoid(V(a, 0.006, GUN_TOP + 0.04), (0.019, 0.03, 0.0045)))   # membrana tra le dita
        th = [V(hx - s * 0.062, 0.07, GUN_TOP + 0.05), V(hx - s * 0.092, 0.058, GUN_TOP + 0.01), V(hx - s * 0.097, 0.034, GUN_TOP - 0.035)]
        parts.append(hair_clump(th, 0.0135, 0.007))
        bands.append((fa + (wrist - fa) * 0.62, unit(wrist - fa)))
    return sdf.union(*parts, k=0.01), bands, tips


def molly_finish(head_field, cut=None, attrs=None):
    hands, bands, tips = molly_hands()
    neck = chain([V(0, 0.32, 0.10), V(0, 0.25, 0.55), V(0, 0.19, 0.86)], [0.065, 0.06, 0.062], k=0.03)
    f = sdf.union(neck, head_field, k=0.03)
    if cut is not None:
        f = sdf.subtract(f, cut, k=0.006)
    obs = molly_scene()
    obs.append(mesh('MollySkin', f, V(-0.30, -0.12, 0.05), V(0.30, 0.45, 1.36), pale_skin(), attrs=attrs))
    obs.append(mesh('MollyHands', hands, V(-0.40, -0.12, 0.2), V(0.40, 0.36, 0.95), pale_skin(), res=min(RES, 0.003)))
    nails = sdf.union(*[ellipsoid_rot(t + d * 0.002 + V(0, -0.004, 0), (0.0065, 0.004, 0.011), np.eye(3, dtype=F)) for t, d in tips])
    obs.append(mesh('MollyNails', nails, V(-0.40, -0.12, 0.5), V(0.40, 0.0, 0.8), mat_simple('Nails', (0.03, 0.03, 0.028), rough=0.2, coat=0.8), res=0.0015))
    for c, ax in bands:
        obs += armband(c, ax)
    return obs


def molly_a():
    """A · Cupola: la testa del barreleye; gli occhi a tubo galleggiano dentro una cupola trasparente."""
    base = sdf.union(sdf.ellipsoid(V(0, 0.15, 0.97), (0.11, 0.12, 0.15)), sdf.ellipsoid(V(0, 0.08, 0.92), (0.07, 0.06, 0.07)), k=0.04)
    dome_in = sdf.ellipsoid(V(0, 0.145, 1.075), (0.098, 0.108, 0.13))
    pits = sdf.union(sdf.sphere(V(0.032, 0.035, 0.965), 0.013), sdf.sphere(V(-0.032, 0.035, 0.965), 0.013))
    obs = molly_finish(base, cut=sdf.union(dome_in, pits))
    dome = sdf.intersect(sdf.shell(sdf.ellipsoid(V(0, 0.145, 1.075), (0.112, 0.122, 0.145)), 0.0035), above((0, 0, 0.985), (0, 0, 1)))
    obs.append(mesh('Dome', dome, V(-0.14, 0.0, 0.97), V(0.14, 0.3, 1.24), glass('DomeGlass', (0.82, 1.0, 0.88)), res=0.0025))
    for s in (-1, 1):
        a, b = V(s * 0.036, 0.17, 1.07), V(s * 0.036, 0.085, 1.055)
        obs.append(mesh(f'TubeEye{s}', sdf.round_cone(a, b, 0.026, 0.023), np.minimum(a, b) - 0.04, np.maximum(a, b) + 0.04, mat_simple('TubeEyeBody', (0.05, 0.06, 0.055), rough=0.3, coat=0.8), res=0.002))
        obs.append(mesh(f'TubeLens{s}', sdf.sphere(b + V(0, -0.006, 0), 0.0215), b - 0.04, b + 0.04, glow('LensGlow', (0.30, 1.0, 0.35), 1.6, base=(0.15, 0.6, 0.2)), res=0.0015))
    mouth = sdf.subtract(torus_axis(V(0, 0.035, 0.875), (0, 1, 0), 0.016, 0.0075), sdf.sphere(V(0, 0.03, 0.875), 0.009))
    obs.append(mesh('SunfishMouth', mouth, V(-0.04, 0.0, 0.84), V(0.04, 0.07, 0.91), pale_skin(), res=0.0015))
    obs.append(teeth_mesh('Beak', [(V(0, 0.04, 0.882), V(0, 0.026, 0.879), 0.007), (V(0, 0.04, 0.868), V(0, 0.026, 0.871), 0.007)]))
    return obs, 'A · Cupola', 'più pesce: la testa del barreleye; gli occhi\na tubo, verdi, ti seguono dentro la cupola'


def molly_b():
    """B · Luna: faccia piatta e tonda come un pesce luna, occhioni bianchi, i codini della bambina."""
    n3 = sdf.Noise3(7)
    disc = sdf.union(sdf.ellipsoid(V(0, 0.16, 1.02), (0.23, 0.055, 0.25)), torus_axis(V(0, 0.165, 1.02), (0, 1, 0), 0.20, 0.035), k=0.03)
    disc = sdf.displace(disc, lambda p: n3(p, scale=0.035, octaves=3), 0.004)
    sockets = sdf.union(sdf.sphere(V(0.11, 0.115, 1.07), 0.052), sdf.sphere(V(-0.11, 0.115, 1.07), 0.052))
    lips = sdf.round_cone(V(0, 0.12, 0.87), V(0, 0.085, 0.865), 0.026, 0.018)
    head = sdf.union(disc, sockets, lips, k=0.02)
    cut = sdf.sphere(V(0, 0.07, 0.865), 0.011)
    obs = molly_finish(head, cut=cut)
    obs += eyes('MollyEye', [V(s * 0.11, 0.098, 1.072) for s in (-1, 1)], 0.044, (0, -1, -0.15))
    obs.append(teeth_mesh('Beak', [(V(0, 0.085, 0.874), V(0, 0.072, 0.871), 0.006), (V(0, 0.085, 0.858), V(0, 0.072, 0.861), 0.006)]))
    hair = []
    for s in (-1, 1):
        root = V(s * 0.10, 0.17, 1.245)
        bob = root + V(s * 0.035, -0.012, 0.028)
        for k, (dx, dy, L) in enumerate(((0.0, 0.0, 1.0), (0.012, 0.01, 0.85), (-0.01, 0.012, 0.9), (0.02, -0.004, 0.75))):
            hair.append(hair_clump([root + V(dx * s, dy, 0.0), bob + V(dx * s, dy, 0.005), bob + V(s * (0.035 + dx), dy + 0.01, -0.03),
                                    bob + V(s * (0.05 + dx), dy + 0.02, -0.11 * L), bob + V(s * (0.045 + dx), dy + 0.03, -0.19 * L)], 0.014, 0.002))
        obs.append(mesh(f'Bobble{s}', sdf.union(sdf.sphere(bob + V(-s * 0.012, -0.004, 0.0), 0.017), sdf.sphere(bob + V(s * 0.012, -0.004, 0.006), 0.017), k=0.004),
                        bob - 0.06, bob + 0.06, vinyl('BobblePink', (0.95, 0.30, 0.55), stain=(0.3, 0.3, 0.2)), res=0.0018))
    obs.append(mesh('Pigtails', sdf.union(*hair, k=0.008), V(-0.32, 0.08, 0.95), V(0.32, 0.30, 1.36), wet_hair(), res=0.0022))
    return obs, 'B · Luna', 'a metà: faccia piatta e tonda come un pesce\nluna, occhioni bianchi, i codini della bambina'


def molly_c():
    """C · Bambina: faccia di bambina con le orbite vuote; gli occhi veri galleggiano nella fronte trasparente."""
    hc = V(0, 0.16, 0.975)
    head = sdf.union(sdf.ellipsoid(hc, (0.10, 0.11, 0.155)), sdf.ellipsoid(V(0, 0.10, 0.925), (0.08, 0.05, 0.08)),
                     sdf.sphere(V(0.05, 0.08, 0.925), 0.028), sdf.sphere(V(-0.05, 0.08, 0.925), 0.028),
                     sdf.sphere(V(0, 0.047, 0.95), 0.010), sdf.sphere(V(0, 0.085, 0.866), 0.024), k=0.025)
    forehead = sdf.ellipsoid(V(0, 0.14, 1.06), (0.094, 0.10, 0.098))
    sockets = sdf.union(sdf.sphere(V(0.037, 0.058, 0.985), 0.02), sdf.sphere(V(-0.037, 0.058, 0.985), 0.02))
    smile = chain([V(-0.024, 0.052, 0.893), V(0, 0.046, 0.886), V(0.024, 0.052, 0.893)], [0.0025, 0.003, 0.0025], k=0.002)

    def blush(p):
        d = np.minimum(np.linalg.norm(p - V(0.055, 0.055, 0.925), axis=1), np.linalg.norm(p - V(-0.055, 0.055, 0.925), axis=1))
        return np.clip(1.0 - d / 0.035, 0.0, 1.0)

    def holes(p):
        d = np.minimum(np.linalg.norm(p - V(0.037, 0.06, 0.985), axis=1), np.linalg.norm(p - V(-0.037, 0.06, 0.985), axis=1))
        return np.clip(1.0 - (d - 0.01) / 0.013, 0.0, 1.0)

    obs = molly_finish(head, cut=sdf.union(forehead, sockets, smile), attrs={'blush': blush, 'mouth': holes})
    bulb = sdf.intersect(sdf.shell(sdf.ellipsoid(V(0, 0.14, 1.06), (0.104, 0.11, 0.108)), 0.003), above((0, 0, 1.0), (0, 0, 1)))
    obs.append(mesh('ForeheadBulb', bulb, V(-0.13, 0.0, 0.99), V(0.13, 0.28, 1.19), glass('BulbFluid', (0.95, 1.0, 0.85), ior=1.36), res=0.002))
    obs += eyes('MollyEye', [V(s * 0.035, 0.10, 1.065) for s in (-1, 1)], 0.026, (0, -1, -0.2))
    strands = []
    for a in (0.0, 0.35, 0.7, 1.0):
        for sg in (-1, 1):
            top = V(sg * (0.07 + 0.025 * a), 0.16 + 0.03 * a, 1.03)
            side = V(sg * (0.102 + 0.02 * a), 0.12 + 0.03 * a, 0.93)
            low = V(sg * (0.12 + 0.03 * a), 0.03, GUN_TOP + 0.016)
            tip = V(sg * (0.13 + 0.035 * a), -0.022, GUN_TOP + 0.012)
            strands.append(hair_clump([top, side, low, tip], 0.016, 0.004))
    obs.append(mesh('MollyHair', sdf.union(*strands, k=0.01), V(-0.3, -0.12, 0.6), V(0.3, 0.32, 1.1), wet_hair(), res=min(RES, 0.003)))
    return obs, 'C · Bambina', 'più bambina: faccia di bambina, orbite vuote;\ngli occhi galleggiano nella fronte trasparente'


# ───────────────────────── HATCH (sagoma C «Spilungone») ─────────────────────────
# Altissimo e piegato in avanti; l'esca (il giocattolo luminoso) gli penzola davanti alla faccia.

def hatch_body(raise_right=False, wrist_r=None):
    torso = chain([V(0, 0.06, 1.50), V(0, 0.02, 2.02), V(0, -0.17, 2.40), V(0, -0.33, 2.55)], [0.10, 0.115, 0.115, 0.095], k=0.05)
    sh = sdf.union(sdf.ellipsoid(V(0.17, -0.21, 2.43), (0.075, 0.08, 0.065)), sdf.ellipsoid(V(-0.17, -0.21, 2.43), (0.075, 0.08, 0.065)), k=0.08)
    neck = chain([V(0, -0.33, 2.55), V(0, -0.46, 2.56)], [0.065, 0.06], k=0.02)
    parts = [torso, sh, neck]
    for s in (-1, 1):
        if raise_right and s == 1:
            parts.append(chain([V(0.18, -0.22, 2.41), V(0.33, -0.50, 2.27), wrist_r], [0.04, 0.026, 0.021], k=0.02))
            parts.append(sdf.sphere(V(0.33, -0.50, 2.27), 0.03))
            continue
        parts.append(chain([V(s * 0.18, -0.22, 2.41), V(s * 0.23, -0.36, 1.92), V(s * 0.21, -0.47, 1.45)], [0.04, 0.026, 0.021], k=0.02))
        parts.append(sdf.sphere(V(s * 0.23, -0.36, 1.92), 0.03))
        w = V(s * 0.21, -0.47, 1.45)
        for dx in (-0.03, -0.01, 0.01, 0.03):
            k1 = w + V(dx, -0.03, -0.10)
            parts.append(chain([w, k1, k1 + V(dx * 0.5, -0.02, -0.13)], [0.015, 0.011, 0.006], k=0.008))
    return sdf.union(*parts, k=0.035)


def hatch_finish(head_field, cut=None, raise_right=False, wrist_r=None, mat=None, attrs=None):
    f = sdf.union(hatch_body(raise_right, wrist_r), head_field, k=0.03)
    if cut is not None:
        f = sdf.subtract(f, cut, k=0.006)
    return [mesh('HatchSkin', f, V(-0.42, -0.98, 1.30), V(0.42, 0.25, 2.95), mat or pale_skin(), attrs=attrs)]


def hatch_a():
    """A · Pescatrice: testa grande e tonda, la bocca spalancata con i denti di vetro rivolti all'indietro."""
    fr = Frame((0, -0.60, 2.56), pitch=10)
    head = sdf.union(sdf.ellipsoid(V(0, 0, 0), (0.17, 0.165, 0.125)), sdf.ellipsoid(V(0, -0.055, -0.075), (0.16, 0.145, 0.07)), k=0.04)
    head = sdf.displace(head, sdf.warts(3, (0, 0, 0), (0.18, 0.18, 0.13), 70, 0.024), 0.007)
    mouth = sdf.ellipsoid(V(0, -0.14, -0.03), (0.135, 0.10, 0.042))
    obs = hatch_finish(fr.field(head), cut=fr.field(mouth))
    c0 = fr.pt((0, -0.05, -0.03))
    obs.append(mesh('HatchThroat', fr.field(sdf.ellipsoid(V(0, -0.05, -0.03), (0.125, 0.08, 0.036))), c0 - 0.15, c0 + 0.15, dark_throat(), res=0.004))

    def front_y(x, z, cy, ry, rx, rz, cz):
        return cy - ry * math.sqrt(max(0.0, 1 - (x / rx) ** 2 - ((z - cz) / rz) ** 2))

    pairs = []
    rng = np.random.default_rng(4)
    for i in range(13):
        t = i / 12 - 0.5
        x = t * 0.24
        zu = -0.03 + 0.042 * math.sqrt(max(0.0, 1 - (x / 0.135) ** 2))
        yu = front_y(x, zu, 0.0, 0.165, 0.17, 0.125, 0.0) + 0.012
        L = rng.uniform(0.035, 0.07)
        pairs.append((fr.pt((x, yu, zu + 0.004)), fr.pt((x * 0.92, yu + 0.035, zu - L)), 0.0065))
        zl = -0.03 - 0.042 * math.sqrt(max(0.0, 1 - (x / 0.135) ** 2))
        yl = front_y(x, zl, -0.055, 0.145, 0.16, 0.07, -0.075) + 0.012
        L2 = rng.uniform(0.04, 0.08)
        pairs.append((fr.pt((x, yl, zl - 0.004)), fr.pt((x * 0.92, yl + 0.04, zl + L2)), 0.007))
    obs.append(teeth_mesh('HatchTeeth', pairs, needle_teeth()))
    obs += eyes('HatchEye', [fr.pt((sx * 0.075, -0.105, 0.085)) for sx in (-1, 1)], 0.016, fr.dir((0, -1, 0.35)))
    obs.append(stalk([fr.pt((0, -0.07, 0.12)), fr.pt((0, -0.12, 0.31)), fr.pt((0, -0.27, 0.33)), fr.pt((0, -0.33, 0.20)), fr.pt((0, -0.335, 0.14))], 0.012, 0.004))
    obs += toy_fish(tuple(fr.pt((0, -0.335, 0.075))))
    return obs, 'A · Pescatrice', 'più pesce: testa tonda da rana pescatrice,\nbocca spalancata, denti di vetro all\'indietro'


def hatch_b():
    """B · Accetta: testa sottile come una lama, argentata, occhi a tubo e lucine sotto il mento."""
    fr = Frame((0, -0.62, 2.56), pitch=8)
    blade = sdf.union(sdf.ellipsoid(V(0, 0, 0), (0.05, 0.17, 0.12)), sdf.ellipsoid(V(0, -0.02, -0.12), (0.04, 0.13, 0.11)),
                      sdf.ellipsoid(V(0, 0.03, 0.115), (0.012, 0.12, 0.03)), k=0.04)
    tubes = sdf.union(*[sdf.round_cone(V(sx * 0.03, 0.03, 0.11), V(sx * 0.03, -0.10, 0.165), 0.032, 0.029) for sx in (-1, 1)])
    head = sdf.union(blade, tubes, k=0.015)
    mouth = sdf.ellipsoid(V(0, -0.17, -0.04), (0.018, 0.03, 0.04))
    silver = pale_skin('SilverSkin', base=(0.45, 0.48, 0.50), dark=(0.16, 0.18, 0.20), belly=(0.60, 0.62, 0.62), irid=0.9)
    obs = hatch_finish(fr.field(head), cut=fr.field(mouth), mat=silver)
    for sx in (-1, 1):
        lens = fr.pt((sx * 0.03, -0.108, 0.168))
        obs.append(mesh(f'TubeLens{sx}', sdf.sphere(lens, 0.027), lens - 0.04, lens + 0.04, glow('HatchLens', (0.65, 0.85, 1.0), 1.2, base=(0.5, 0.6, 0.7)), res=0.0015))
    dots = []
    for i in range(9):
        t = 0.1 + 0.8 * i / 8
        y = 0.10 - 0.22 * t
        zb = -0.12 - 0.11 * math.sqrt(max(0.0, 1 - ((y + 0.02) / 0.13) ** 2))
        for sx in (-1, 1):
            dots.append(sdf.sphere(fr.pt((sx * 0.016, y, zb + 0.022)), 0.0075))
    c0 = fr.pt((0, -0.02, -0.2))
    obs.append(mesh('Photophores', sdf.union(*dots), c0 - 0.2, c0 + 0.2, glow('Photophore', (0.45, 0.75, 1.0), 3.0), res=0.0015))
    obs.append(teeth_mesh('HatchTeeth', [(fr.pt((x, -0.165, -0.008)), fr.pt((x, -0.17, -0.032)), 0.004) for x in (-0.01, 0.0, 0.01)] +
                          [(fr.pt((x, -0.165, -0.072)), fr.pt((x, -0.17, -0.048)), 0.004) for x in (-0.01, 0.0, 0.01)]))
    obs.append(stalk([fr.pt((0, -0.12, 0.14)), fr.pt((0, -0.22, 0.25)), fr.pt((0, -0.34, 0.20)), fr.pt((0, -0.37, 0.08))], 0.010, 0.004))
    obs += toy_fish(tuple(fr.pt((0, -0.372, 0.01))))
    return obs, 'B · Accetta', 'a metà: testa sottile come una lama, argentata,\nocchi a tubo e lucine sotto il mento'


def hatch_c():
    """C · Bambino: faccia lunga da bambino che conta a occhi chiusi, la mano di traverso sugli occhi;
    l'esca gli spunta dal ciuffo."""
    fr = Frame((0, -0.60, 2.56), pitch=18)
    head = sdf.union(sdf.ellipsoid(V(0, 0, 0), (0.088, 0.098, 0.145)), sdf.ellipsoid(V(0, -0.055, -0.115), (0.056, 0.05, 0.05)),
                     sdf.sphere(V(0.045, -0.07, -0.045), 0.028), sdf.sphere(V(-0.045, -0.07, -0.045), 0.028),
                     sdf.sphere(V(0, -0.098, -0.02), 0.012),
                     sdf.sphere(V(0.037, -0.074, 0.03), 0.021), sdf.sphere(V(-0.037, -0.074, 0.03), 0.021), k=0.022)
    crease = sdf.union(*[chain([V(sx * 0.02, -0.093, 0.03), V(sx * 0.037, -0.097, 0.025), V(sx * 0.054, -0.092, 0.031)], [0.0022, 0.0028, 0.0022], k=0.002) for sx in (-1, 1)])
    grin = chain([V(-0.056, -0.072, -0.07), V(-0.028, -0.093, -0.084), V(0.0, -0.099, -0.088), V(0.028, -0.093, -0.084), V(0.056, -0.072, -0.07)],
                 [0.004, 0.009, 0.011, 0.009, 0.004], k=0.004)
    # la mano destra di traverso sugli occhi, le dita lunghe un po' aperte
    palm = sdf.ellipsoid(V(0.085, -0.095, 0.03), (0.03, 0.02, 0.045))
    fingers = []
    for dz, L in ((-0.026, 0.86), (-0.004, 1.0), (0.018, 1.0), (0.040, 0.9)):
        b = V(0.075, -0.112, 0.03 + dz)
        m = V(0.0, -0.118, 0.034 + dz * 1.12)
        t = V(-0.082 * L, -0.098, 0.04 + dz * 1.35)
        fingers.append(hair_clump([b, m, t], 0.0115, 0.0068))
    hand = sdf.union(palm, *fingers, k=0.008)
    wrist = fr.pt((0.10, -0.075, -0.02))
    obs = hatch_finish(fr.field(sdf.union(head, hand, k=0.006)), cut=fr.field(sdf.union(crease, grin)), raise_right=True, wrist_r=wrist)
    c0 = fr.pt((0, -0.08, -0.084))
    obs.append(mesh('HatchThroat', fr.field(sdf.ellipsoid(V(0, -0.08, -0.084), (0.05, 0.02, 0.011))), c0 - 0.07, c0 + 0.07, dark_throat(), res=0.002))
    pairs = []
    for i in range(14):
        t = i / 13 - 0.5
        x = t * 0.09
        y = -0.098 + 0.09 * t * t
        z = -0.088 + 0.07 * t * t
        pairs.append((fr.pt((x, y + 0.004, z + 0.009)), fr.pt((x, y - 0.002, z + 0.001)), 0.0031))
        pairs.append((fr.pt((x, y + 0.004, z - 0.009)), fr.pt((x, y - 0.002, z - 0.001)), 0.0031))
    obs.append(teeth_mesh('HatchTeeth', pairs))
    obs.append(stalk([fr.pt((0, 0.0, 0.14)), fr.pt((0, -0.08, 0.26)), fr.pt((0, -0.20, 0.25)), fr.pt((0, -0.245, 0.13))], 0.012, 0.0045))
    obs += toy_fish(tuple(fr.pt((0, -0.248, 0.06))))
    strands = [hair_clump([fr.pt(unit(V(a * 0.4, 0.3, 1.0)) * 0.15), fr.pt(unit(V(a, -0.35, 0.8)) * 0.15), fr.pt(unit(V(a * 1.1, -0.7, 0.45)) * 0.14)], 0.009, 0.003)
               for a in (-0.7, -0.35, 0.35, 0.7)]
    obs.append(mesh('HatchHair', sdf.union(*strands, k=0.006), fr.pos - 0.2, fr.pos + 0.2, wet_hair(), res=0.003))
    return obs, 'C · Bambino', 'più bambino: faccia lunga da bambino che conta\na occhi chiusi, con la mano sugli occhi'


# ───────────────────────── scena, render, tavola ─────────────────────────

CREATURES = {
    'gulpy': {
        'title': 'GULPY — dettagli della testa (sagoma C «Avvoltoio»)',
        'variants': [gulpy_a, gulpy_b, gulpy_c],
        'cam': ((-1.30, -2.40, 1.66), (0, -0.88, 1.92), 55),
        'subject': (0, -0.85, 1.9), 'key': 55, 'rim': 170,
    },
    'molly': {
        'title': 'MOLLY — dettagli della testa (sagoma C «Dita»), vista dal posto del pescatore',
        'variants': [molly_a, molly_b, molly_c],
        'cam': ((0.16, -0.92, 1.30), (0, 0.10, 0.93), 34),
        'subject': (0, 0.12, 0.95), 'key': 22, 'rim': 70,
    },
    'hatch': {
        'title': 'HATCH — dettagli della testa (sagoma C «Spilungone»)',
        'variants': [hatch_a, hatch_b, hatch_c],
        'cam': ((-0.55, -2.15, 2.28), (0, -0.66, 2.50), 45),
        'subject': (0, -0.6, 2.45), 'key': 30, 'rim': 120,
    },
}


def setup(spec):
    sc = reset_scene()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.cycles.use_denoising = True
    w = bpy.data.worlds.new('Studio')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.010, 0.013, 0.021, 1)
    w.lightgroup = 'ambient'
    (cl, ct, lens) = spec['cam']
    cam_d = bpy.data.cameras.new('Cam')
    cam_d.lens = lens
    cam_d.sensor_width = 36.0
    cam = bpy.data.objects.new('Cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    from mathutils import Vector
    cam.location = cl
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = (Vector(ct) - Vector(cl)).to_track_quat('-Z', 'Y')
    s = np.array(spec['subject'], float)
    # la lampara (calda, dal basso e di lato), la luna dietro (fredda), quasi niente riempimento
    area_light('Key', tuple(s + (-1.0, -1.5, -0.15)), tuple(s), spec['key'], (1.0, 0.74, 0.46), 0.5)
    area_light('Rim', tuple(s + (0.9, 1.3, 1.3)), tuple(s), spec['rim'], (0.55, 0.72, 1.0), 0.45)
    area_light('Fill', tuple(s + (1.2, -1.6, 0.4)), tuple(s), spec['key'] * 0.10, (0.55, 0.65, 0.85), 1.6)
    return sc


def render_variant(key, idx):
    spec = CREATURES[key]
    sc = setup(spec)
    _, label, desc = spec['variants'][idx]()
    W, H = (400, 560) if FAST else (640, 900)
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 24 if FAST else 64
    sc.render.image_settings.file_format = 'PNG'
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, f'{key}_{"ABC"[idx]}.png')
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path, label, desc


def compose(key, panels):
    spec = CREATURES[key]
    ims = [Image.open(p).convert('RGB') for p, _, _ in panels]
    W, H = ims[0].size
    gap = 14
    head, foot = 70, (165 if not FAST else 120)
    sheet = Image.new('RGB', (W * len(ims) + gap * (len(ims) + 1), H + head + foot), (14, 16, 22))
    d = ImageDraw.Draw(sheet)
    try:
        big = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30 if not FAST else 18)
        lab = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 28 if not FAST else 16)
        small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20 if not FAST else 12)
    except OSError:
        big = lab = small = ImageFont.load_default()
    d.text((gap, 18), spec['title'], fill=(235, 228, 210), font=big)
    for i, (im, (_, label, desc)) in enumerate(zip(ims, panels)):
        x = gap + i * (W + gap)
        sheet.paste(im, (x, head))
        d.text((x + 6, head + H + 10), label, fill=(255, 179, 92), font=lab)
        d.multiline_text((x + 6, head + H + 48 if not FAST else head + H + 32), desc, fill=(200, 196, 184), font=small, spacing=4)
    name = f'{key}_dettagli{"_bozza" if FAST else ""}.png'
    sheet.save(os.path.join(OUT, name))
    return os.path.join(OUT, name)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    which = [a for a in args if a in (*CREATURES, 'all')]
    keys = list(CREATURES) if not which or which[0] == 'all' else [which[0]]
    only = None
    if '--only' in sys.argv:
        only = 'ABC'.index(sys.argv[sys.argv.index('--only') + 1])
    for k in keys:
        panels = []
        for i in range(3):
            if only is not None and i != only:
                continue
            panels.append(render_variant(k, i))
            print('ok', k, 'ABC'[i], flush=True)
        if only is None:
            print('tavola', compose(k, panels), flush=True)
