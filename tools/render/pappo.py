"""
PAPPO — PROTOTIPO TECNICO per provare la modellazione SDF (design del personaggio ancora da decidere).
Coordinate locali: origine alla base (dove siede), faccia verso −Y, alto +Z. Altezza ~0,97 m.

Pose: open (0 chiusa … 1 spalancata), lids (0 aperti … 1 chiusi, felice), arms ('rest','up','grip','clap').
"""
from __future__ import annotations

import math

import bpy
import numpy as np

import sdf
from creature import (eye_material, eyeball, flesh_material, sdf_object, skin_material, teeth_material, tooth)
from nodes import material

HINGE = np.array((0.0, 0.06, 0.585), np.float32)
EYE_C = np.array((0.185, -0.175, 0.865), np.float32)
EYE_R = 0.122


def mouth_z(p):
    return 0.582 + 0.55 * p[:, 0] ** 2 + 0.06 * (p[:, 1] + 0.30)


def arm_points(kind, side):
    s = side
    sh = (s * 0.33, -0.05, 0.50)
    if kind == 'up':
        return sh, (s * 0.50, -0.22, 0.62), (s * 0.43, -0.33, 0.86), (0.0, -0.3, 1.0)
    if kind == 'grip':
        return sh, (s * 0.42, -0.32, 0.46), (s * 0.30, -0.56, 0.40), (0.0, -1.0, -0.3)
    if kind == 'clap':
        return sh, (s * 0.40, -0.30, 0.40), (s * 0.06, -0.44, 0.50), (-s * 1.0, -0.2, 0.3)
    return sh, (s * 0.43, -0.18, 0.36), (s * 0.22, -0.34, 0.34), (-s * 0.6, -0.5, -0.2)


def hand(wrist, direction, side, r=0.017):
    d = np.array(direction, np.float32)
    d /= np.linalg.norm(d)
    w = np.array(wrist, np.float32)
    # piano della mano: perpendicolare alla direzione con un asse "laterale"
    lat = np.cross(d, np.array((0, 0, 1), np.float32))
    if np.linalg.norm(lat) < 1e-3:
        lat = np.array((1, 0, 0), np.float32)
    lat /= np.linalg.norm(lat)
    parts = [sdf.ellipsoid(w + d * 0.035, (0.055, 0.055, 0.04))]
    for k, a in enumerate((-0.55, -0.18, 0.18, 0.55)):
        fd = d * math.cos(a) + lat * math.sin(a)
        base = w + d * 0.05 + lat * (a * 0.05)
        tip = base + fd * (0.055 if abs(a) > 0.3 else 0.065)
        parts.append(sdf.capsule(base, tip, r))
        parts.append(sdf.sphere(tip, r * 1.35))   # polpastrello da rana
    return sdf.union(*parts, k=0.012)


def build_field(open_=0.0, lids=0.15, arms='rest'):
    theta = math.radians(3 + 62 * open_)
    gap = 0.004 + 0.01 * open_
    cheeks = sdf.union(sdf.sphere((0.265, -0.15, 0.64), 0.115), sdf.sphere((-0.265, -0.15, 0.64), 0.115))
    head = sdf.union(
        sdf.ellipsoid((0, -0.05, 0.665), (0.40, 0.33, 0.245)),
        sdf.ellipsoid((0, -0.21, 0.645), (0.29, 0.14, 0.125)),           # muso
        sdf.sphere((EYE_C[0], EYE_C[1] + 0.075, EYE_C[2] - 0.03), 0.112),
        sdf.sphere((-EYE_C[0], EYE_C[1] + 0.075, EYE_C[2] - 0.03), 0.112),
        k=0.07,
    )
    # palpebre: calotte sopra gli occhi
    def lid(sx):
        c = np.array((sx * EYE_C[0], EYE_C[1], EYE_C[2]), np.float32)
        h = EYE_R * (0.80 - 1.65 * lids)
        cap = sdf.intersect(sdf.sphere(c, EYE_R + 0.014), sdf.plane((0, 0.30, -1), float(c[2] + h)), k=0.02)
        return cap
    head = sdf.union(head, lid(1), lid(-1), k=0.012)
    head = sdf.subtract(head, sdf.union(sdf.sphere((0.05, -0.355, 0.70), 0.012), sdf.sphere((-0.05, -0.355, 0.70), 0.012)), k=0.006)

    def upper(p):
        d = sdf.smax(head(p), mouth_z(p) + gap / 2 - p[:, 2], 0.018)
        return sdf.smin(d, cheeks(p), 0.05)   # guance paffute: coprono gli angoli della bocca

    jaw_shape = sdf.union(
        sdf.ellipsoid((0, -0.07, 0.535), (0.37, 0.30, 0.11)),
        sdf.ellipsoid((0, -0.20, 0.53), (0.26, 0.14, 0.085)),
        k=0.05,
    )
    R = sdf.rot_matrix('x', math.degrees(theta))   # la mascella ruota in giù attorno alla cerniera

    def jaw(p):
        q = (p - HINGE) @ R + HINGE    # ruota il punto nel riferimento della mascella chiusa
        return sdf.smax(jaw_shape(q), q[:, 2] - (mouth_z(q) - gap / 2), 0.018)

    body = sdf.union(
        sdf.ellipsoid((0, 0.02, 0.35), (0.40, 0.35, 0.36)),
        sdf.ellipsoid((0, -0.09, 0.27), (0.34, 0.29, 0.27)),
        k=0.08,
    )
    # gambe da rana ripiegate
    legs = []
    for s in (1, -1):
        hip, knee, ankle = (s * 0.27, 0.14, 0.20), (s * 0.43, -0.20, 0.27), (s * 0.40, 0.02, 0.07)
        legs += [sdf.round_cone(hip, knee, 0.13, 0.085), sdf.round_cone(knee, ankle, 0.075, 0.05),
                 sdf.round_cone(ankle, (s * 0.44, -0.30, 0.03), 0.05, 0.035),
                 sdf.ellipsoid((s * 0.44, -0.33, 0.025), (0.085, 0.095, 0.022))]
        for a in (-0.5, -0.15, 0.2, 0.55):
            base = np.array((s * 0.44, -0.36, 0.025), np.float32)
            tip = base + np.array((s * math.sin(a) * 0.15, -math.cos(a) * 0.15, -0.005), np.float32)
            legs += [sdf.capsule(base, tip, 0.02), sdf.sphere(tip, 0.028)]
        legs.append(sdf.ellipsoid((s * 0.44, -0.44, 0.02), (0.11, 0.08, 0.012)))   # palmatura
    arm_parts = []
    for s in (1, -1):
        sh, el, wr, hd = arm_points(arms, s)
        arm_parts += [sdf.round_cone(sh, el, 0.07, 0.058), sdf.round_cone(el, wr, 0.056, 0.045), hand(wr, hd, s)]
    lower = sdf.union(body, *legs, k=0.05)
    lower = sdf.union(lower, *arm_parts, k=0.03)

    def field(p):
        d = sdf.smin(upper(p), jaw(p), 0.012)
        d = sdf.smin(d, lower(p), 0.07)
        return d

    def torso(p):
        d = sdf.smin(upper(p), jaw(p), 0.012)
        return sdf.smin(d, body(p), 0.07)

    wart_f = sdf.warts(7, (0, 0.05, 0.6), (0.5, 0.45, 0.45), 520, 0.032)

    def wart_mask(p):
        back = np.clip((p[:, 1] + 0.05) / 0.2, 0, 1)
        top = np.clip((p[:, 2] - 0.70) / 0.1, 0, 1)
        side = np.clip((np.abs(p[:, 0]) - 0.30) / 0.1, 0, 1)
        return np.maximum(np.maximum(back, top), side) * wart_f(p)

    full = sdf.displace(field, wart_mask, 0.011)
    return full, dict(upper=upper, jaw=jaw, head=head, torso=torso, theta=theta, gap=gap, R=R, wart=wart_mask)


def build(name='Pappo', open_=0.0, lids=0.15, arms='rest', res=0.0055, bib=True, tongue=True):
    field, parts = build_field(open_, lids, arms)
    R = parts['R']

    def mouth_attr(p):
        du = p[:, 2] - (mouth_z(p) + parts['gap'] / 2)
        q = (p - HINGE) @ R + HINGE
        dj = (mouth_z(q) - parts['gap'] / 2) - q[:, 2]
        inside = parts['head'](p) < -0.012
        near = np.exp(-np.maximum(np.minimum(du, dj), 0.0) / 0.010)
        # sottile linea scura delle labbra anche sulla pelle esterna
        lip = 0.5 * np.exp(-(np.minimum(np.abs(du), np.abs(dj)) / 0.006) ** 2) * (p[:, 1] < -0.12)
        return np.maximum(np.where(inside, near, 0.0), lip).astype(np.float32)

    def throat(p):
        return np.clip((p[:, 1] + 0.26) / 0.22, 0, 1).astype(np.float32)

    def belly(p):
        return (np.clip((-p[:, 1] - 0.10) / 0.12, 0, 1) * np.clip((0.55 - p[:, 2]) / 0.07, 0, 1)).astype(np.float32)

    def blush(p):
        out = np.zeros(len(p), np.float32)
        for s in (1, -1):
            c = np.array((s * 0.25, -0.26, 0.66), np.float32)
            out += 0.6 * np.exp(-np.sum((p - c) ** 2, axis=1) / 0.055 ** 2)
        return out

    obs = []
    body = sdf_object(name, field, (-0.62, -0.75, -0.05), (0.62, 0.50, 1.05), res=res,
                      attrs={'belly': belly, 'wart': parts['wart'], 'mouth': mouth_attr, 'blush': blush, 'throat': throat})
    skin = bpy.data.materials.get('PappoSkin') or skin_material(
        'PappoSkin', base=(0.22, 0.27, 0.065), dark=(0.07, 0.09, 0.025), belly=(0.66, 0.58, 0.33),
        accent=(0.55, 0.52, 0.18), spots_scale=6.0, spots_amount=0.7, mouth=(0.32, 0.05, 0.06))
    body.data.materials.append(skin)
    obs.append(body)

    em = bpy.data.materials.get('PappoEye') or eye_material('PappoEye', iris=(0.95, 0.66, 0.10), iris_dark=(0.42, 0.20, 0.02),
                                                            pupil='slit_h', pupil_size=0.42, shine=(0.85, 1.0, 0.35), shine_strength=1.2)
    for s in (1, -1):
        c = (s * EYE_C[0], EYE_C[1], EYE_C[2])
        obs.append(eyeball(f'{name}Eye{s}', c, EYE_R, em, look=(s * 0.22, -1.0, 0.05)))

    tm = teeth_material()
    # due dentini da latte davanti
    for s in (1, -1):
        x = s * 0.045
        y = front_y(parts['upper'], x, 0.60) + 0.012
        zt = float(mouth_z(np.array([[x, y, 0]], np.float32))[0]) + parts['gap'] / 2
        obs.append(tooth(f'{name}Milk{s}', (x, y, zt + 0.01), (x, y - 0.004, zt - 0.032), 0.019, tm))
    # file di denti aguzzi più dentro (si vedono solo a bocca aperta)
    if open_ > 0.15:
        for k, x in enumerate(np.linspace(-0.25, 0.25, 13)):
            if abs(x) < 0.07:
                continue
            y = front_y(parts['upper'], x, 0.60) + 0.035
            zt = float(mouth_z(np.array([[x, y, 0]], np.float32))[0]) + parts['gap'] / 2
            obs.append(tooth(f'{name}TU{k}', (x, y, zt + 0.006), (x * 0.97, y + 0.005, zt - 0.03 - 0.01 * open_), 0.009, tm))
        for k, x in enumerate(np.linspace(-0.24, 0.24, 12)):
            y = front_y(parts['upper'], x, 0.56) + 0.04
            zc = float(mouth_z(np.array([[x, y, 0]], np.float32))[0]) - parts['gap'] / 2
            base = np.array((x, y, zc - 0.006), np.float32)
            tip = base + np.array((0, 0.004, 0.028 + 0.008 * open_), np.float32)
            Rt = parts['R'].T
            base = (base - HINGE) @ Rt + HINGE
            tip = (tip - HINGE) @ Rt + HINGE
            obs.append(tooth(f'{name}TL{k}', tuple(base), tuple(tip), 0.008, tm))
    if tongue and open_ > 0.05:
        Rt = parts['R'].T

        def tongue_f(p):
            q = (p - HINGE) @ R + HINGE
            return sdf.ellipsoid((0, -0.10, 0.575), (0.17, 0.17, 0.045))(q)
        tb = sdf_object(f'{name}Tongue', tongue_f, (-0.25, -0.45, 0.25), (0.25, 0.15, 0.75), res=0.006)
        tb.data.materials.append(flesh_material('PappoTongue', (0.55, 0.12, 0.16)))
        obs.append(tb)
    if bib:
        obs.append(build_bib(name, parts['torso']))
    return obs


def front_y(field, x, z):
    ys = np.linspace(0.1, -0.6, 400, dtype=np.float32)
    P = np.stack([np.full_like(ys, x), ys, np.full_like(ys, z)], axis=1)
    d = field(P)
    idx = np.where(d > 0)[0]
    return float(ys[idx[0]]) if len(idx) else -0.3


def build_bib(name, field):
    def bib_f(p):
        off = field(p) - 0.014
        sh = np.abs(off) - 0.0045
        ang = np.arctan2(p[:, 0], -p[:, 1])
        lower = 0.335 + 0.014 * np.sin(ang * 22.0) + 0.10 * (np.abs(p[:, 0]) / 0.24) ** 2
        region = np.maximum(lower - p[:, 2], p[:, 2] - 0.50)
        front = np.maximum(p[:, 1] + 0.12, np.abs(p[:, 0]) - 0.25)
        return np.maximum(np.maximum(sh, region), front)
    ob = sdf_object(f'{name}Bib', bib_f, (-0.5, -0.55, 0.25), (0.5, 0.15, 0.60), res=0.004)
    m = bpy.data.materials.get('PappoBib')
    if m is None:
        m, g = material('PappoBib')
        co = g.texcoord('Object')
        x, y, z = g.sep(co)
        weave = g.noise(co, scale=300.0, detail=2.0).fac
        dirt = g.smoothstep(0.55, 0.75, g.noise(co, scale=9.0, detail=4.0).fac)
        col = g.mix(g.mul(dirt, 0.6), (0.78, 0.76, 0.66), (0.30, 0.34, 0.20))
        # pesciolino ricamato al centro (ellisse + coda), azzurro
        bx, bz = g.sub(x, 0.0), g.sub(z, 0.415)
        body = g.add(g.mul(g.mul(bx, bx), 1 / 0.05 ** 2), g.mul(g.mul(bz, bz), 1 / 0.022 ** 2))
        fishm = g.smoothstep(1.05, 0.9, body)
        tx = g.sub(x, 0.065)
        tail = g.mul(g.smoothstep(0.0, 0.005, tx), g.smoothstep(0.03, 0.025, tx))
        tail = g.mul(tail, g.smoothstep(g.mul(tx, 0.9), g.mul(tx, 0.7), g.math('ABSOLUTE', bz)))
        stitch = g.add(fishm, tail)
        col = g.mix(g.clamp01(stitch), col, (0.10, 0.30, 0.62))
        eye = g.smoothstep(0.009, 0.006, g.vmath('LENGTH', g.comb(g.add(x, 0.028), 0.0, g.sub(z, 0.415))))
        col = g.mix(eye, col, (0.05, 0.05, 0.08))
        nrm = g.bump(g.add(weave, g.mul(stitch, 2.0)), strength=0.3, distance=0.001)
        g.output_material(g.principled(color=col, rough=0.75, sheen=0.5, sss=0.1, normal=nrm))
    ob.data.materials.append(m)
    return ob
