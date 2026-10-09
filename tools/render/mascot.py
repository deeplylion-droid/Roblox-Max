"""
MAMA MARINA — la mascotte di Splashland: balena-mamma da cartone animato anni '90, a braccia
(pinne) aperte, con tre pesciolini in grembo. "Mama Marina loves her little ones!"

Modellata a scala unitaria (alta ~1,05) con faccia verso −Y; si scala e si ruota al piazzamento.
  build_statue(): statua di vetroresina alta ~22 m, scrostata, senza l'occhio destro, colature di ruggine
  build_figurine(): souvenir di plastica, pulito (piccola scheggiatura)
"""
from __future__ import annotations

import math

import bpy
import numpy as np

import sdf
from creature import sdf_object
from nodes import material

EYE_L = np.array((-0.125, -0.255, 0.865), np.float32)
EYE_R = np.array((0.125, -0.255, 0.865), np.float32)
EYE_RAD = 0.072


def body_field(missing_eye=False):
    body = sdf.ellipsoid((0, 0.0, 0.36), (0.34, 0.30, 0.38))
    head = sdf.ellipsoid((0, -0.03, 0.80), (0.34, 0.30, 0.25))
    cheeks = sdf.union(sdf.sphere((-0.20, -0.20, 0.75), 0.10), sdf.sphere((0.20, -0.20, 0.75), 0.10))
    # pinne aperte per l'abbraccio
    fins = []
    for s in (1, -1):
        R = sdf.rot_matrix('y', s * -28.0) @ sdf.rot_matrix('z', s * 12.0)
        fin = sdf.rotate(sdf.ellipsoid((s * 0.50, -0.10, 0.62), (0.22, 0.05, 0.10)), R, center=(s * 0.30, -0.06, 0.55))
        fins.append(fin)
    # coda con le pinne caudali dietro la testa (sagoma a cuore)
    tail = sdf.union(
        sdf.round_cone((0, 0.20, 0.10), (0, 0.42, 0.62), 0.16, 0.06),
        sdf.ellipsoid((0.13, 0.46, 0.70), (0.15, 0.04, 0.07)),
        sdf.ellipsoid((-0.13, 0.46, 0.70), (0.15, 0.04, 0.07)),
        k=0.05,
    )
    # zampillo dello sfiatatoio (era una fontana vera)
    jet = [sdf.round_cone((0, 0.0, 0.98), (0.0, -0.01, 1.20), 0.035, 0.022)]
    for k in range(7):
        a = 2 * math.pi * k / 7
        tip = (0.11 * math.cos(a), -0.01 + 0.08 * math.sin(a), 1.13 - 0.05 * abs(math.sin(a * 0.5)))
        jet.append(sdf.round_cone((0, -0.01, 1.21), tip, 0.022, 0.010))
        jet.append(sdf.sphere(tip, 0.016))
    hat = sdf.union(*jet, k=0.02)
    f = sdf.union(body, head, k=0.12)
    f = sdf.union(f, cheeks, k=0.05)
    f = sdf.union(f, *fins, k=0.06)
    f = sdf.union(f, tail, k=0.08)
    f = sdf.union(f, hat, k=0.015)
    # sorriso inciso
    def smile(p):
        x = p[:, 0]
        zc = 0.70 + 0.9 * x ** 2
        groove = np.sqrt((p[:, 2] - zc) ** 2 + np.maximum(np.abs(x) - 0.17, 0) ** 2) - 0.012
        front = p[:, 1] + 0.24
        return np.maximum(groove, front)
    f = sdf.subtract(f, smile, k=0.006)
    # orbite oculari
    f = sdf.subtract(f, sdf.sphere(EYE_L + np.array((0, 0.035, 0), np.float32), EYE_RAD * 0.98), k=0.01)
    f = sdf.subtract(f, sdf.sphere(EYE_R + np.array((0, 0.035, 0), np.float32), EYE_RAD * (1.25 if missing_eye else 0.98)), k=0.01)
    # tre pesciolini in grembo
    for k, (x, z) in enumerate(((-0.12, 0.43), (0.0, 0.36), (0.12, 0.43))):
        fish = sdf.union(sdf.ellipsoid((x, -0.31, z), (0.065, 0.035, 0.042)),
                         sdf.ellipsoid((x + 0.07, -0.30, z), (0.02, 0.012, 0.035)), k=0.01)
        f = sdf.union(f, fish, k=0.01)
    # basamento
    plinth = sdf.box((0, 0.05, -0.04), (0.42, 0.40, 0.05), 0.02)
    f = sdf.union(f, plinth, k=0.02)
    return f


def regions(p):
    """Colori dipinti come attributi: belly, cheek, mouth, fish (indice colore), hat, plinth."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    belly = np.clip((-y - 0.12) / 0.08, 0, 1) * np.clip((0.62 - z) / 0.08, 0, 1) * np.clip((z - 0.05) / 0.05, 0, 1)
    cheek = np.zeros(len(p), np.float32)
    for s in (1, -1):
        cheek += np.exp(-((x - s * 0.20) ** 2 + (y + 0.27) ** 2 + (z - 0.76) ** 2) / 0.045 ** 2)
    zc = 0.70 + 0.9 * x ** 2
    mouth = (np.abs(z - zc) < 0.02) & (np.abs(x) < 0.19) & (y < -0.2)
    fish = np.zeros(len(p), np.float32)
    for k, (fx, fz) in enumerate(((-0.12, 0.43), (0.0, 0.36), (0.12, 0.43))):
        d = ((x - fx - 0.02) / 0.1) ** 2 + ((y + 0.31) / 0.05) ** 2 + ((z - fz) / 0.06) ** 2
        fish = np.where(d < 1.0, (k + 1) / 3.0, fish)
    hat = (z > 1.01).astype(np.float32)
    band = np.zeros(len(p), np.float32)
    plinth = (z < 0.01).astype(np.float32)
    return belly, cheek, mouth.astype(np.float32), fish, hat, band, plinth


def paint_material(name, weathered=True):
    m, g = material(name)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    belly, cheek, mouth, fish = g.attr('belly'), g.attr('cheek'), g.attr('mouth'), g.attr('fish')
    hat, band, plinth = g.attr('hat'), g.attr('band'), g.attr('plinth')
    rust_a = g.attr('rust')
    body_c = (0.20, 0.36, 0.62)
    col = g.mix(g.smoothstep(0.3, 0.7, belly), body_c, (0.85, 0.80, 0.68))
    col = g.mix(g.mul(cheek, 0.7), col, (0.90, 0.40, 0.45))
    col = g.mix(hat, col, (0.62, 0.80, 0.92))
    col = g.mix(band, col, (0.08, 0.14, 0.45))
    fishcol = g.ramp(fish, [(0.30, (0.95, 0.45, 0.10)), (0.60, (0.95, 0.80, 0.10)), (0.95, (0.25, 0.70, 0.30))], interp='CONSTANT')
    col = g.mix(g.smoothstep(0.1, 0.2, fish), col, fishcol)
    col = g.mix(mouth, col, (0.35, 0.05, 0.08))
    col = g.mix(plinth, col, (0.35, 0.33, 0.30))
    rough = 0.35
    if weathered:
        # vernice scrostata (sotto il primer grigio), sporco che cola, ruggine sotto l'occhio mancante
        peel = g.smoothstep(0.58, 0.62, g.noise(co, scale=6.0, detail=6.0, rough=0.65, distortion=0.5).fac)
        col = g.mix(peel, col, (0.42, 0.42, 0.40))
        streak = g.noise(g.mapping(co, scale=(30.0, 30.0, 1.5)), scale=1.0, detail=4.0).fac
        grime = g.mul(g.smoothstep(0.5, 0.8, streak), g.smoothstep(0.9, 0.2, z))
        col = g.mix(g.mul(grime, 0.6), col, (0.06, 0.07, 0.05))
        col = g.mix(g.clamp01(g.mul(rust_a, 1.4)), col, (0.26, 0.08, 0.02))
        rough = g.mixf(peel, 0.45, 0.85)
    g.output_material(g.principled(color=col, rough=rough, coat=0.0 if weathered else 0.6,
                                   normal=g.bump(g.noise(co, scale=40.0, detail=3.0).fac, strength=0.15 if weathered else 0.03, distance=0.002)))
    return m


def eye_material(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    r = g.vmath('LENGTH', g.comb(x, g.sub(z, 0.12), 0.0))
    front = g.smoothstep(0.0, -0.5, y)
    pupil = g.mul(g.smoothstep(0.47, 0.42, r), front)
    hl = g.mul(g.smoothstep(0.13, 0.09, g.vmath('LENGTH', g.comb(g.add(x, 0.18), g.sub(z, 0.32), 0.0))), front)
    col = g.mix(pupil, (0.85, 0.85, 0.82), (0.01, 0.01, 0.015))
    col = g.mix(hl, col, (0.95, 0.95, 0.95))
    g.output_material(g.principled(color=col, rough=0.2, coat=0.8))
    return m


def build(name, missing_eye, weathered, res, col='env'):
    f = body_field(missing_eye)
    def rust(p):
        # colature di ruggine dall'orbita vuota (e un po' dall'altra)
        out = np.zeros(len(p), np.float32)
        for c, w in ((EYE_R, 1.0 if missing_eye else 0.0), (EYE_L, 0.35)):
            if w == 0:
                continue
            dx = np.abs(p[:, 0] - c[0])
            below = np.clip((c[2] - p[:, 2]) / 0.35, 0, 1)
            lanes = np.exp(-(dx / (0.012 + 0.03 * below)) ** 2) * (p[:, 2] < c[2] + 0.02) * np.exp(-below * 1.5)
            out = np.maximum(out, w * lanes * (p[:, 1] < -0.05))
        return out
    belly, cheek, mouth, fish, hat, band, plinth = (lambda P: regions(P)[0]), (lambda P: regions(P)[1]), (lambda P: regions(P)[2]), \
        (lambda P: regions(P)[3]), (lambda P: regions(P)[4]), (lambda P: regions(P)[5]), (lambda P: regions(P)[6])
    ob = sdf_object(name, f, (-0.80, -0.50, -0.12), (0.80, 0.62, 1.30), res=res,
                    attrs={'belly': belly, 'cheek': cheek, 'mouth': mouth, 'fish': fish, 'hat': hat, 'band': band,
                           'plinth': plinth, 'rust': rust}, col=col)
    ob.data.materials.append(paint_material(name + 'Paint', weathered))
    obs = [ob]
    em = eye_material('MarinaEye')
    from creature import eyeball
    for c, missing in ((EYE_L, False), (EYE_R, missing_eye)):
        if missing:
            continue
        e = eyeball(name + 'Eye', tuple(c), EYE_RAD, em, look=(0.0, -1.0, 0.05), col=col)
        obs.append(e)
    # ciglia da cartone animato
    lash_m = bpy.data.materials.get('MarinaLash')
    if lash_m is None:
        lash_m, g = material('MarinaLash')
        g.output_material(g.principled(color=(0.02, 0.02, 0.03), rough=0.4))
    for c, missing in ((EYE_L, False), (EYE_R, missing_eye)):
        side = np.sign(c[0])
        for k in range(3):
            a = math.radians(55 + 30 * k)
            base = c + np.array((side * EYE_RAD * math.cos(a) * 0.9, -0.02, EYE_RAD * math.sin(a) * 0.95), np.float32)
            tip = base + np.array((side * 0.03 * math.cos(a), -0.012, 0.03 * math.sin(a) + 0.01), np.float32)
            lf = sdf.capsule(base, tip, 0.006)
            lo, hi = np.minimum(base, tip) - 0.01, np.maximum(base, tip) + 0.01
            lo_ = sdf_object(name + f'Lash{k}', lf, lo, hi, res=0.0025, col=col)
            lo_.data.materials.append(lash_m)
            obs.append(lo_)
    return obs


def place(obs, location, yaw_deg, scale):
    from mathutils import Euler, Matrix
    bpy.context.view_layer.update()   # matrix_world deve riflettere posizione/scala appena impostate
    M = Matrix.Translation(location) @ Euler((0, 0, math.radians(yaw_deg)), 'XYZ').to_matrix().to_4x4() @ Matrix.Scale(scale, 4)
    for o in obs:
        o.matrix_world = M @ o.matrix_world
    return obs


def build_statue(location, facing_yaw_deg, height=22.0):
    obs = build('MamaMarina', missing_eye=True, weathered=True, res=0.009)
    return place(obs, location, facing_yaw_deg, height)


def build_figurine(location, facing_yaw_deg, height=0.12):
    obs = build('MarinaFigurine', missing_eye=False, weathered=False, res=0.012, col='boat')   # oggetto della barca, non del paesaggio
    return place(obs, location, facing_yaw_deg, height)
