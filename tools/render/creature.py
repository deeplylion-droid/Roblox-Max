"""
Strumenti comuni per i Piccoli: mesh da SDF con attributi colore, occhi, denti, pelle bagnata.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

import sdf
from common import collection, mesh_from_arrays, set_custom_normals, set_lightgroup
from nodes import material


def sdf_object(name, field, lo, hi, res=0.006, attrs=None, col='creatures', matrix=None):
    """Crea un oggetto mesh dal campo; attrs: {nome: f(p)->(N,) o (N,3)} valutati sui vertici."""
    V, Fc, N = sdf.mesh(field, lo, hi, res)
    ob = mesh_from_arrays(name, V, Fc.tolist(), smooth=True, col=col)
    set_custom_normals(ob, N)
    if attrs:
        for an, fn in attrs.items():
            vals = np.asarray(fn(V), dtype=np.float32)
            if vals.ndim == 1:
                a = ob.data.attributes.new(an, 'FLOAT', 'POINT')
                a.data.foreach_set('value', vals)
            else:
                a = ob.data.color_attributes.new(an, 'FLOAT_COLOR', 'POINT')
                rgba = np.concatenate([vals, np.ones((len(vals), 1), np.float32)], axis=1)
                a.data.foreach_set('color', rgba.ravel())
    if matrix is not None:
        ob.matrix_world = matrix
    set_lightgroup(ob, 'ambient')
    return ob


def skin_material(name, base, dark, belly, accent=(0.9, 0.8, 0.5), rough=0.38, coat=0.65, sss=0.18,
                  sss_radius=(1.0, 0.45, 0.25), spots_scale=7.0, spots_amount=0.6, bump_scale=60.0, bump=0.25,
                  mouth=(0.28, 0.04, 0.05), irid=0.0):
    """Pelle anfibia bagnata. Attributi: 'belly', 'wart', 'mouth', 'blush' (float)."""
    m, g = material(name)
    co = g.texcoord('Object')
    belly_w = g.attr('belly')
    wart_w = g.attr('wart')
    mouth_w = g.attr('mouth')
    blush_w = g.attr('blush')
    n1 = g.noise(co, scale=spots_scale, detail=4.0, rough=0.55, distortion=0.6)
    blot = g.smoothstep(0.52, 0.62, n1.fac)
    col = g.mix(g.mul(blot, spots_amount), base, dark)
    n2 = g.noise(co, scale=spots_scale * 3.0, detail=2.0)
    col = g.mix(g.mul(g.smoothstep(0.55, 0.7, n2.fac), 0.35), col, dark)
    col = g.mix(g.smoothstep(0.2, 0.8, belly_w), col, belly)
    col = g.mix(g.mul(wart_w, 0.55), col, accent)
    col = g.mix(g.mul(blush_w, 0.45), col, (0.80, 0.42, 0.40))
    throat_w = g.attr('throat')
    mouth_col = g.mix(g.mul(throat_w, 0.92), mouth, (0.012, 0.004, 0.004))
    col = g.mix(g.smoothstep(0.3, 0.7, mouth_w), col, mouth_col)
    fine = g.noise(co, scale=bump_scale, detail=3.0, rough=0.6)
    h = g.add(fine.fac, g.mul(wart_w, 2.5))
    nrm = g.bump(h, strength=bump, distance=0.003)
    r = g.mixf(g.smoothstep(0.3, 0.7, mouth_w), rough, 0.25)
    bsdf = g.principled(color=col, rough=r, coat=coat, coat_rough=0.06, sss=sss, sss_radius=sss_radius,
                        sss_scale=0.035, normal=nrm, coat_normal=nrm, thin_film=irid * 400.0)
    g.output_material(bsdf)
    return m


def eye_material(name, iris=(0.85, 0.62, 0.12), iris_dark=(0.35, 0.18, 0.02), pupil='round', pupil_size=0.38,
                 shine=(0.75, 0.95, 0.35), shine_strength=1.6, sclera=(0.05, 0.04, 0.03), lid_dark=0.0):
    """Occhio visto lungo -Y locale: iride radiale, pupilla (round|slit_h|slit_v), cornea lucida, tapetum."""
    m, g = material(name)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    r = g.vmath('LENGTH', g.comb(x, z, 0.0))
    # coordinate normalizzate sulla superficie anteriore (raggio 1)
    if pupil == 'slit_h':
        pd = g.vmath('LENGTH', g.comb(g.mul(x, 0.55), g.mul(z, 1.9), 0.0))
    elif pupil == 'slit_v':
        pd = g.vmath('LENGTH', g.comb(g.mul(x, 2.2), g.mul(z, 0.6), 0.0))
    else:
        pd = r
    front = g.smoothstep(0.0, -0.4, y)
    iris_mask = g.mul(g.smoothstep(0.86, 0.80, r), front)
    pupil_mask = g.mul(g.smoothstep(pupil_size + 0.03, pupil_size - 0.03, pd), front)
    ang = g.math('ARCTAN2', z, x)
    streaks = g.noise(g.comb(g.mul(ang, 4.0), g.mul(r, 3.0), 0.0), scale=3.0, detail=4.0, rough=0.6)
    irc = g.mix(g.smoothstep(0.35, 0.7, streaks.fac), iris_dark, iris)
    irc = g.mix(g.smoothstep(0.45, 0.85, r), irc, g.comb(iris_dark[0] * 0.5, iris_dark[1] * 0.5, iris_dark[2] * 0.5))
    col = g.mix(iris_mask, sclera, irc)
    col = g.mix(pupil_mask, col, (0.004, 0.004, 0.006))
    # tapetum: bagliore tenue (domina solo al buio, alla luce la pupilla resta nera)
    glow = g.add(g.mul(pupil_mask, 0.16), g.mul(iris_mask, 0.05))
    em = g.mul(glow, shine_strength)
    bsdf = g.principled(color=col, rough=0.35, coat=1.0, coat_rough=0.02, spec=0.6, emission=shine, emission_strength=em)
    g.output_material(bsdf)
    return m


def eyeball(name, center, radius, mat, look=(0.0, -1.0, 0.0), col='creatures'):
    """Sfera con il polo anteriore (−Y locale) orientato verso 'look'."""
    from mathutils import Vector
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=center, segments=48, ring_count=24)
    ob = bpy.context.object
    ob.name = name
    bpy.ops.object.shade_smooth()
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    collection(col).objects.link(ob)
    # le coordinate Object del materiale sono in unità del raggio: scala la mesh a 1 e l'oggetto a radius
    for v in ob.data.vertices:
        v.co = v.co / radius
    ob.scale = (radius, radius, radius)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = Vector((-look[0], -look[1], -look[2])).to_track_quat('Y', 'Z')
    ob.data.materials.append(mat)
    set_lightgroup(ob, 'ambient')
    return ob


def tooth(name, base, tip, r, mat, col='creatures'):
    """Dente conico arrotondato."""
    f = sdf.round_cone(base, tip, r, r * 0.18)
    b, t = np.array(base), np.array(tip)
    lo = np.minimum(b, t) - r * 1.3
    hi = np.maximum(b, t) + r * 1.3
    ob = sdf_object(name, f, lo, hi, res=max(r / 5.0, 0.0012), col=col)
    ob.data.materials.append(mat)
    return ob


def teeth_material():
    m = bpy.data.materials.get('Teeth')
    if m:
        return m
    m, g = material('Teeth')
    g.output_material(g.principled(color=(0.78, 0.74, 0.62), rough=0.3, sss=0.3, sss_radius=(1, 0.8, 0.6), sss_scale=0.004, coat=0.5))
    return m


def flesh_material(name='Flesh', color=(0.42, 0.07, 0.08)):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    n = g.noise(co, scale=40.0, detail=3.0)
    col = g.mix(g.mul(n.fac, 0.4), color, (color[0] * 0.5, color[1] * 0.5, color[2] * 0.5))
    g.output_material(g.principled(color=col, rough=0.25, coat=0.8, sss=0.4, sss_radius=(1, 0.3, 0.2), sss_scale=0.02,
                                   normal=g.bump(n.fac, strength=0.3, distance=0.002)))
    return m


def place(obs, location, yaw_deg=0.0, pitch_deg=0.0, scale=1.0):
    """Sposta un gruppo di oggetti costruiti nell'origine locale (faccia verso −Y)."""
    from mathutils import Euler, Matrix
    M = Matrix.Translation(location) @ Euler((math.radians(pitch_deg), 0, math.radians(yaw_deg)), 'XYZ').to_matrix().to_4x4() @ Matrix.Scale(scale, 4)
    for o in obs:
        o.matrix_world = M @ o.matrix_world
    return obs
