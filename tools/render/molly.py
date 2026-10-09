"""
MOLLY — modello definitivo (sagoma C «Dita», testa B «Luna»), in lavorazione.

Quasi tutta sott'acqua, si aggrappa al bordo della barca con le dita lunghissime e palmate e ti
fissa da sopra il bordo con la faccia piatta e tonda del pesce luna. Porta i braccioli arancioni e
i codini da bambina con gli elastici rosa.

Coordinate come nelle tavole: il bordo della barca corre lungo X a y = 0 (sopra a z = GUN_TOP);
dentro la barca è y < 0, fuori y > 0. Faccia verso −Y.

Uso (vetrina): tools/.venv/bin/python tools/render/molly.py [--fast]
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import sdf  # noqa: E402
import skin  # noqa: E402
from common import CACHE, ROOT, reset_scene  # noqa: E402
from creature import sdf_object  # noqa: E402
from dettagli import (GUN_TOP, V, above, area_light, chain, ellipsoid_rot, hair_clump, mat_simple,  # noqa: E402
                      molly_scene, torus_axis, unit, vinyl, wet_hair)

FAST = '--fast' in sys.argv
F = np.float32

C = V(0, 0.165, 1.03)                      # centro del disco della faccia
EYE_RS = (0.044, 0.048)                     # gli occhi non sono uguali: il destro è più grande e più basso
EYES = [V(-0.104, 0.099, 1.074), V(0.108, 0.097, 1.058)]
EYE_R = 0.046
TILT = 11.0                                 # la testa piegata di lato, come una bambina curiosa
MOUTH = V(0, 0.083, 0.862)
VIEWER = V(0.16, -0.92, 1.30)               # il pescatore (per lo sguardo)


def below(q, down):
    """Semispazio dalla parte di 'down' (stessa convenzione di above)."""
    return above(q, down)


# ───────────────────────── testa ─────────────────────────

def head_field():
    disc = sdf.union(sdf.ellipsoid(C, (0.23, 0.058, 0.26)), torus_axis(C, (0, 1, 0), 0.205, 0.038), k=0.035)
    back = sdf.ellipsoid(C + V(0, 0.045, 0.0), (0.19, 0.06, 0.22))
    brows = sdf.union(*[ellipsoid_rot(V(s * 0.103, 0.114, 1.123), (0.062, 0.02, 0.019), sdf.rot_matrix('y', s * 14)) for s in (-1, 1)])
    mounds = sdf.union(*[sdf.sphere(e + V(0, 0.027, -0.004), r + 0.011) for e, r in zip(EYES, EYE_RS)])
    snout = sdf.round_cone(V(0, 0.135, 0.878), V(0, 0.098, 0.866), 0.036, 0.026)
    lips = torus_axis(MOUTH + V(0, 0.008, 0), (0, 1, 0), 0.0165, 0.0095)
    cheeks = sdf.union(*[sdf.ellipsoid(V(s * 0.088, 0.118, 0.93), (0.05, 0.014, 0.042)) for s in (-1, 1)])
    neck = chain([V(0, 0.33, 0.10), V(0, 0.27, 0.55), V(0, 0.225, 0.86), V(0, 0.21, 0.98)], [0.068, 0.062, 0.06, 0.07], k=0.04)
    f = sdf.union(disc, back, brows, mounds, snout, lips, cheeks, neck, k=0.025)
    f = sdf.subtract(f, sdf.union(*[sdf.sphere(e, r + 0.0008) for e, r in zip(EYES, EYE_RS)]), k=0.003)
    # palpebre spesse: la superiore cade su un terzo dell'occhio, l'inferiore è un cuscinetto gonfio
    lids = []
    for e, r in zip(EYES, EYE_RS):
        shell = sdf.subtract(sdf.sphere(e, r + 0.009), sdf.sphere(e, r + 0.0006))
        lids.append(sdf.intersect(shell, above(e + V(0, 0, 0.32 * r), (0, 0.35, 1)), k=0.003))
        lids.append(sdf.intersect(shell, below(e - V(0, 0, 0.60 * r), (0, 0.30, -1)), k=0.003))
    f = sdf.union(f, *lids, k=0.004)
    # parassiti sul bordo (piccoli bitorzoli chiari)
    rng = np.random.default_rng(5)
    par = []
    for _ in range(26):
        a = rng.uniform(-2.4, -0.7) if rng.random() < 0.6 else rng.uniform(0.7, 2.4)
        p = C + V(math.cos(a) * 0.205, -0.02 + rng.uniform(-0.01, 0.02), math.sin(a) * 0.205 + 0.0)
        par.append(sdf.sphere(p, rng.uniform(0.0025, 0.0045)))
    f = sdf.union(f, *par, k=0.002)
    # tagli: bocca, narici, branchie, orbite (per l'occhio), cicatrici
    cut = sdf.union(
        sdf.sphere(MOUTH - V(0, 0.012, 0), 0.0118),
        *[sdf.ellipsoid(V(s * 0.021, 0.106, 0.933), (0.004, 0.008, 0.007)) for s in (-1, 1)],
        *[sdf.ellipsoid(V(s * 0.205, 0.17, 0.885), (0.006, 0.014, 0.016)) for s in (-1, 1)],
        sdf.capsule(V(0.04, 0.104, 1.20), V(0.165, 0.112, 1.045), 0.0022),
        sdf.capsule(V(0.055, 0.104, 1.19), V(0.17, 0.112, 1.06), 0.0016),
        sdf.capsule(V(-0.17, 0.112, 0.96), V(-0.11, 0.109, 0.86), 0.0018),
    )
    f = sdf.subtract(f, cut, k=0.003)
    # superficie: dentelli fitti del pesce luna, bozze larghe, grinze attorno a bocca e occhi
    den = skin.bumps(11, 0.0045, 0.00075)

    def denticles(p):
        rim = np.clip((np.linalg.norm((p - C)[:, [0, 2]], axis=1) - 0.09) / 0.12, 0.25, 1.0)
        return den(p) * rim
    f = sdf.displace(f, denticles, 1.0)
    f = sdf.displace(f, skin.bumps(12, 0.035, 0.0022), 1.0)
    f = sdf.displace(f, skin.wrinkles(13, 0.011, 0.0011, center=MOUTH, radius=0.075, direction=(0, 1, 0)), 1.0)
    for i, e in enumerate(EYES):
        f = sdf.displace(f, skin.wrinkles(20 + i, 0.009, 0.0009, center=e, radius=0.085, direction=(0, 1, 0)), 1.0)
    f = sdf.displace(f, skin.bumps(14, 0.012, 0.0009), 1.0)
    return f


def head_attrs():
    def mouth(p):
        d = np.linalg.norm(p - (MOUTH - V(0, 0.012, 0)), axis=1)
        m = np.clip(1.0 - (d - 0.006) / 0.008, 0, 1)
        for s in (-1, 1):
            m = np.maximum(m, np.clip(1.0 - np.linalg.norm((p - V(s * 0.021, 0.106, 0.933)) / V(0.007, 0.012, 0.01), axis=1), 0, 1))
            m = np.maximum(m, np.clip(1.0 - np.linalg.norm((p - V(s * 0.205, 0.17, 0.885)) / V(0.012, 0.02, 0.022), axis=1), 0, 1))
        return m

    def slime(p):
        d = np.linalg.norm(p - MOUTH, axis=1)
        m = np.clip(1.0 - d / 0.035, 0, 1)
        for e, r in zip(EYES, EYE_RS):
            m = np.maximum(m, np.clip(1.0 - (np.linalg.norm(p - e, axis=1) - r) / 0.012, 0, 1))
        return m

    def scar(p):
        out = np.zeros(len(p), F)
        for a, b in ((V(0.04, 0.104, 1.20), V(0.165, 0.112, 1.045)), (V(-0.17, 0.112, 0.96), V(-0.11, 0.109, 0.86))):
            ab = b - a
            t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
            d = np.linalg.norm(p - (a + t[:, None] * ab), axis=1)
            out = np.maximum(out, np.clip(1.0 - d / 0.007, 0, 1))
        rim = np.abs(np.linalg.norm((p - C)[:, [0, 2]], axis=1) - 0.205) < 0.03
        return np.maximum(out, rim * 0.25)

    return {'mouth': mouth, 'slime': slime, 'scar': scar}


def pigtails():
    """Codini: ciocche bagnate raccolte dagli elastici rosa, che ricadono lungo il bordo della faccia."""
    rng = np.random.default_rng(8)
    clumps, bands, balls = [], [], []
    for s in (-1, 1):
        root = V(s * 0.10, 0.178, 1.245)
        bob = root + V(s * 0.022, -0.004, 0.026)
        for k in range(40):
            j = V(*rng.normal(0, 0.0055, 3))
            r0 = root + V(rng.uniform(-0.014, 0.014), rng.uniform(-0.005, 0.009), rng.uniform(-0.005, 0.004))
            L = rng.uniform(0.75, 1.15)
            spread = rng.uniform(-0.012, 0.018)
            pts = [r0, bob + j * 0.3, bob + V(s * (0.03 + spread), 0.012, 0.004) + j,
                   bob + V(s * (0.055 + spread), 0.02, -0.07 * L) + j, bob + V(s * (0.062 + spread * 1.5), 0.028, -0.15 * L) + j * 1.4,
                   bob + V(s * (0.058 + spread * 2), 0.03, -0.22 * L) + j * 2]
            clumps.append(hair_clump(pts, rng.uniform(0.0035, 0.0062), 0.0010))
        axis = unit(V(s * 0.6, 0.1, 0.8))
        bands.append(torus_axis(bob, axis, 0.012, 0.0028))
        side = unit(np.cross(axis, V(0, 1, 0)))
        balls += [sdf.sphere(bob + side * 0.019 + V(0, -0.006, 0), 0.0155), sdf.sphere(bob - side * 0.019 + V(0, -0.006, 0), 0.0155)]
    return sdf.union(*clumps, k=0.0035), sdf.union(*bands), sdf.union(*balls)


# ───────────────────────── mani e braccioli ─────────────────────────

FINGERS = ((-0.056, 0.80, 0.004), (-0.019, 1.0, -0.003), (0.019, 0.95, 0.002), (0.056, 0.72, -0.004))


def finger_points(hx, dx, L, bend):
    x = hx + dx
    return [V(x, 0.036, GUN_TOP + 0.032), V(x + bend, -0.004, GUN_TOP + 0.047), V(x + bend * 1.5, -0.057, GUN_TOP + 0.008),
            V(x + bend * 2.5, -0.067, GUN_TOP - 0.13 * L), V(x + bend * 3.0, -0.053, GUN_TOP - 0.245 * L)]


def hand_field(s):
    """Una mano (s = -1 sinistra, +1 destra): campo della pelle, campo delle unghie, bracciolo (centro, asse)."""
    parts, nails = [], []
    folds = []
    if True:
        hx = s * 0.25
        wrist = V(hx, 0.08, GUN_TOP + 0.07)
        fa = V(hx * 1.12, 0.19, 0.62)
        parts.append(chain([V(hx * 1.25, 0.26, 0.25), fa, wrist], [0.031, 0.029, 0.025], k=0.02))
        parts.append(sdf.sphere(wrist + V(s * 0.018, 0.0, 0.006), 0.012))                      # osso del polso
        parts.append(sdf.ellipsoid(V(hx, 0.050, GUN_TOP + 0.048), (0.064, 0.048, 0.024)))       # dorso
        paths = [finger_points(hx, dx, L, b) for dx, L, b in FINGERS]
        for pts, (dx, L, b) in zip(paths, FINGERS):
            parts.append(hair_clump(pts, 0.0150, 0.0078))
            for kk, r in ((1, 0.0155), (2, 0.0143), (3, 0.0125)):
                parts.append(sdf.sphere(pts[kk], r))
                d = unit(pts[kk + 1] - pts[kk - 1])
                folds.append(skin.ring_folds(pts[kk], d, r, 0.006, freq=2, amp=0.00028))
            parts.append(sdf.capsule(V(hx + dx * 0.55, 0.088, GUN_TOP + 0.066), pts[0] + V(0, 0.0, 0.009), 0.0042))   # tendini
            tip, prev = pts[-1], pts[-2]
            d = unit(tip - prev)
            dorsal = unit(np.cross(d, V(1, 0, 0)))
            if dorsal[1] > 0:
                dorsal = -dorsal
            nails.append(ellipsoid_rot(tip + dorsal * 0.0055 + d * 0.003, (0.0078, 0.0028, 0.0135), _frame(d, dorsal)))
        # membrane tra le dita fino a metà della seconda falange
        for a_pts, b_pts in zip(paths[:-1], paths[1:]):
            for t in np.linspace(0.0, 1.75, 12):
                i0 = min(int(t), 2)
                u = t - i0
                pa = a_pts[i0] * (1 - u) + a_pts[i0 + 1] * u
                pb = b_pts[i0] * (1 - u) + b_pts[i0 + 1] * u
                parts.append(sdf.capsule(pa, pb, 0.0034))
        th = [V(hx - s * 0.062, 0.07, GUN_TOP + 0.05), V(hx - s * 0.092, 0.058, GUN_TOP + 0.01), V(hx - s * 0.097, 0.034, GUN_TOP - 0.035)]
        parts.append(hair_clump(th, 0.0135, 0.0075))
        band = (fa + (wrist - fa) * 0.62, unit(wrist - fa))
    f = sdf.union(*parts, k=0.007)
    for fo in folds:
        f = sdf.displace(f, fo, 1.0)
    f = sdf.displace(f, skin.bumps(31, 0.006, 0.00035), 1.0)
    return f, sdf.union(*nails), band


def _frame(d, up):
    """Matrice di rotazione che porta l'asse Z locale su d e l'asse Y locale su up (per gli ellissoidi)."""
    z = unit(d)
    y = unit(up - (up @ z) * z)
    x = np.cross(y, z)
    return np.stack([x, y, z], axis=1).astype(F)   # colonne = assi locali: (p-c) @ R dà le coordinate locali


def armband(c, axis):
    axis = unit(axis)
    chambers = sdf.union(torus_axis(c + axis * 0.024, axis, 0.050, 0.030), torus_axis(c - axis * 0.024, axis, 0.050, 0.030), k=0.012)
    chambers = sdf.displace(chambers, skin.bumps(41, 0.02, 0.0015), 1.0)
    seam = torus_axis(c, axis, 0.074, 0.0055)
    side = unit(np.cross(axis, V(0, 1, 0)))
    up = unit(np.cross(side, axis))
    valve_base = c + axis * 0.024 + up * 0.077
    valve = sdf.union(sdf.round_cone(valve_base - up * 0.004, valve_base + up * 0.012, 0.007, 0.006), sdf.sphere(valve_base + up * 0.014, 0.0075), k=0.003)
    return chambers, seam, valve


# ───────────────────────── costruzione ─────────────────────────

def build(res_head=None, res_hands=None):
    rh = res_head or (0.004 if FAST else 0.0015)
    rn = res_hands or (0.003 if FAST else 0.0011)
    obs = []
    skin_m = skin.creature_skin('MollySkin', base=(0.205, 0.215, 0.215), dark=(0.065, 0.07, 0.075), light=(0.36, 0.375, 0.37),
                                vein=(0.13, 0.15, 0.19), rough=0.66, sss=0.10)
    head = sdf_object('MollyHead', head_field(), V(-0.29, 0.03, 0.70), V(0.29, 0.33, 1.33), res=rh, attrs=head_attrs(), banded=True)
    head.data.materials.append(skin_m)
    from creature import eyeball
    looks = [unit(VIEWER - EYES[0]), unit(VIEWER - EYES[1] + V(0.35, 0.0, -0.25))]   # un occhio ti guarda, l'altro scivola via
    head_obs = [head]
    for i, (e, r) in enumerate(zip(EYES, EYE_RS)):
        head_obs.append(eyeball(f'MollyEye{i}', tuple(map(float, e)), r, skin.cloudy_eye(), look=tuple(map(float, looks[i]))))
    beak = sdf.union(ellipsoid_rot(MOUTH + V(0, 0.004, 0.0062), (0.0085, 0.006, 0.0042), np.eye(3, dtype=F)),
                     ellipsoid_rot(MOUTH + V(0, 0.004, -0.0062), (0.0085, 0.006, 0.0042), np.eye(3, dtype=F)))
    bk = sdf_object('MollyBeak', beak, MOUTH - 0.03, MOUTH + 0.03, res=0.0008)
    bk.data.materials.append(mat_simple('BeakBone', (0.62, 0.58, 0.46), rough=0.45))
    head_obs.append(bk)
    hair, bands_f, balls = pigtails()
    hr = sdf_object('MollyHair', hair, V(-0.27, 0.05, 0.80), V(0.27, 0.30, 1.34), res=0.0012 if not FAST else 0.0025, banded=True)
    hr.data.materials.append(mat_simple('WetHairDark', (0.026, 0.021, 0.018), rough=0.42, coat=0.25, coat_rough=0.15))
    head_obs.append(hr)
    el = sdf_object('MollyHairBands', bands_f, V(-0.2, 0.1, 1.2), V(0.2, 0.25, 1.32), res=0.001)
    el.data.materials.append(mat_simple('ElasticBand', (0.35, 0.05, 0.12), rough=0.5))
    head_obs.append(el)
    bb = sdf_object('MollyBobbles', balls, V(-0.2, 0.1, 1.2), V(0.2, 0.25, 1.32), res=0.0012)
    bb.data.materials.append(vinyl('BobblePink', (0.92, 0.30, 0.52), stain=(0.30, 0.28, 0.22)))
    head_obs.append(bb)
    tilt_group(head_obs, C, TILT)
    obs += head_obs
    for name, fld, lo, hi in slime_bits():
        sl = sdf_object(name, fld, lo, hi, res=0.0015 if FAST else 0.0008, banded=True)
        sl.data.materials.append(skin.slime_material())
        obs.append(sl)
    bands = []
    for s in (-1, 1):
        hx = s * 0.25
        hand, nails, band = hand_field(s)
        bands.append(band)
        hd = sdf_object(f'MollyHand{s}', hand, V(hx - 0.13, -0.095, 0.50), V(hx + 0.13, 0.24, 0.90), res=rn, banded=True)
        hd.data.materials.append(skin_m)
        obs.append(hd)
        nl = sdf_object(f'MollyNails{s}', nails, V(hx - 0.12, -0.10, 0.48), V(hx + 0.12, 0.0, 0.85), res=0.0008)
        nl.data.materials.append(mat_simple('NailsDark', (0.05, 0.045, 0.04), rough=0.45))
        obs.append(nl)
    for i, (c, ax) in enumerate(bands):
        ch, seam, valve = armband(c, ax)
        a = sdf_object(f'Armband{i}', ch, c - 0.12, c + 0.12, res=0.0018)
        a.data.materials.append(vinyl('ArmbandVinyl', (0.95, 0.40, 0.06)))
        b = sdf_object(f'ArmbandSeam{i}', seam, c - 0.1, c + 0.1, res=0.0015)
        b.data.materials.append(vinyl('ArmbandWhite', (0.85, 0.82, 0.74)))
        v = sdf_object(f'ArmbandValve{i}', valve, c - 0.12, c + 0.12, res=0.001)
        v.data.materials.append(vinyl('ArmbandWhite', (0.85, 0.82, 0.74)))
        obs += [a, b, v]
    return obs


def tilt_point(p, deg=TILT):
    """Dove finisce un punto della testa dopo la piega laterale (stessa rotazione di tilt_group)."""
    a = math.radians(deg)
    q = np.asarray(p, F) - C
    R = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]], F)
    return C + R @ q


def slime_bits():
    """Melma vera, in pezzi con box stretti: [(nome, campo, lo, hi)].
    Gocce dalla bocca e dai polpastrelli, fili tra le dita, pozze e colature sul legno e sulla fiancata."""
    rng = np.random.default_rng(17)
    out = []
    m = tilt_point(MOUTH)
    mouth = sdf.union(*[skin.drip(tilt_point(MOUTH + V(dx, -0.004, -0.017)), L, 0.0026, 0.0048) for dx, L in ((-0.006, 0.045), (0.007, 0.028))])
    out.append(('MollySlimeMouth', mouth, m - V(0.04, 0.04, 0.09), m + V(0.04, 0.03, 0.02)))
    for s in (-1, 1):
        hx = s * 0.25
        parts = []
        paths = [finger_points(hx, dx, L, b) for dx, L, b in FINGERS]
        for pts in paths:
            if rng.random() < 0.75:
                parts.append(skin.drip(pts[-1] + V(0, -0.002, -0.004), rng.uniform(0.012, 0.035), 0.0022, 0.0042))
        for a_pts, b_pts in zip(paths[:-1], paths[1:]):
            parts.append(skin.strand(a_pts[2] + V(0, -0.006, -0.004), b_pts[2] + V(0, -0.006, -0.006), rng.uniform(0.008, 0.02), 0.0013))
            parts.append(skin.strand(a_pts[3] + V(0, -0.008, 0), b_pts[3] + V(0, -0.008, 0.01), rng.uniform(0.01, 0.025), 0.0011))
        # pozza sul bordo e colature sulla fiancata interna
        parts.append(sdf.ellipsoid(V(hx + s * 0.01, -0.012, GUN_TOP + 0.0005), (0.075, 0.03, 0.0022)))
        for dxx in (-0.03, 0.012, 0.045):
            x = hx + dxx
            L = rng.uniform(0.08, 0.20)
            parts.append(sdf.ellipsoid(V(x, -0.0405, GUN_TOP - 0.05 - L / 2), (0.007 + 0.003 * rng.random(), 0.0018, L / 2)))
            parts.append(skin.drip(V(x, -0.043, GUN_TOP - 0.05 - L), 0.012, 0.003, 0.005))
        out.append((f'MollySlimeHand{s}', sdf.union(*parts, k=0.002), V(hx - 0.13, -0.075, 0.48), V(hx + 0.13, 0.05, 0.80)))
    return out


def tilt_group(obs, pivot, deg):
    """Piega la testa di lato (rotazione attorno all'asse di vista, dal centro della faccia)."""
    from mathutils import Matrix
    bpy.context.view_layer.update()
    M = Matrix.Translation(tuple(map(float, pivot))) @ Matrix.Rotation(math.radians(deg), 4, 'Y') @ Matrix.Translation(tuple(map(float, -pivot)))
    for o in obs:
        o.matrix_world = M @ o.matrix_world


# ───────────────────────── vetrina ─────────────────────────

SHOTS = {
    'insieme': ((0.16, -0.92, 1.30), (0.0, 0.10, 0.93), 34),
    'faccia': ((0.07, -0.50, 1.12), (0.0, 0.12, 1.03), 55),
}


def showcase(shots=('insieme', 'faccia')):
    from mathutils import Vector
    out = []
    sc = reset_scene()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.cycles.use_denoising = True
    w = bpy.data.worlds.new('Night')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.010, 0.014, 0.022, 1)
    molly_scene()
    build()
    s = np.array((0, 0.12, 0.95))
    # la lanterna del pescatore illumina dal basso, la luna da dietro
    area_light('Key', tuple(s + (-0.7, -1.1, -0.55)), tuple(s), 30, (1.0, 0.70, 0.40), 0.35)
    area_light('Rim', tuple(s + (0.9, 1.3, 1.3)), tuple(s), 90, (0.55, 0.72, 1.0), 0.45)
    area_light('Fill', tuple(s + (1.2, -1.6, 0.4)), tuple(s), 2.5, (0.55, 0.65, 0.85), 1.6)
    cam_d = bpy.data.cameras.new('Cam')
    cam_d.sensor_width = 36.0
    cam = bpy.data.objects.new('Cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    W, H = (540, 720) if FAST else (1080, 1440)
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.cycles.samples = 32 if FAST else 160
    sc.render.image_settings.file_format = 'PNG'
    os.makedirs(os.path.join(CACHE, 'vetrina'), exist_ok=True)
    for name in shots:
        cl, ct, lens = SHOTS[name]
        cam_d.lens = lens
        cam.location = cl
        cam.rotation_mode = 'QUATERNION'
        cam.rotation_quaternion = (Vector(ct) - Vector(cl)).to_track_quat('-Z', 'Y')
        path = os.path.join(CACHE, 'vetrina', f'molly_{name}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('ok', path, flush=True)
    return out


if __name__ == '__main__':
    showcase()
