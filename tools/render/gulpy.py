"""
GULPY — modello definitivo (sagoma C «Avvoltoio», testa B «Cerniera»), in lavorazione.

Un gigante curvo e scheletrico in piedi nell'acqua fino alla vita, davanti alla prua. La testa,
da quasi-uomo, pende davanti al petto; la mascella sganciata cade fino allo sterno, con i denti ad
ago e la bava. Il salvagente a paperella del parco gli stringe il collo.

Coordinate: faccia verso −Y (la barca), alto +Z, superficie del mare a z = 0.

Uso (vetrina): tools/.venv/bin/python tools/render/gulpy.py [--fast]
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
from common import CACHE, reset_scene  # noqa: E402
from creature import eyeball, sdf_object  # noqa: E402
from dettagli import (Frame, V, above, area_light, chain, ellipsoid_rot, hair_clump, mat_simple,  # noqa: E402
                      needle_teeth, torus_axis, unit, vinyl)

FAST = '--fast' in sys.argv
F = np.float32

RING_C = V(0, -0.635, 2.355)               # salvagente: centro e asse (lungo il collo)
RING_AXIS = unit((0, -0.22, -0.22))
HEAD = Frame((0, -0.905, 1.985), pitch=32)  # sistema locale della testa
VIEWER = V(-0.6, -3.6, 1.25)               # il pescatore, dalla barca


def below(q, down):
    return above(q, down)


# ───────────────────────── corpo ─────────────────────────

# dove spingono i gomiti quando le mani si aggrappano (x in fuori, y indietro, z in su; locale)
ELBOW_OUT = (0.8, 0.55, 0.3)
SHOULDER = (0.29, -0.05, 2.22)


def _elbow(sh, wr, side, L1, L2, out=None):
    """Gomito tra spalla e polso, spinto in fuori: rispetta più o meno le lunghezze di braccio e avambraccio."""
    d = float(np.linalg.norm(wr - sh))
    h = d / 2
    L = (L1 + L2) / 2
    b = math.sqrt(max(0.0, L * L - h * h))
    out = ELBOW_OUT if out is None else out
    o = V(side * out[0], out[1], out[2])
    axis = unit(wr - sh)
    o = unit(o - (o @ axis) * axis)
    return (sh + wr) / 2 + o * b


def body_field(grip=None):
    """grip: None (braccia che pendono) oppure (polso sinistro, polso destro) in coordinate locali:
    le mani afferrano il bordo e le dita si piegano verso l'interno della barca."""
    back = chain([V(0, 0.24, -0.20), V(0, 0.22, 0.95), V(0, 0.17, 1.55), V(0, 0.05, 2.05), V(0, -0.15, 2.42), V(0, -0.30, 2.52)], [0.17, 0.16, 0.18, 0.19, 0.17, 0.125], k=0.06)
    chest = sdf.ellipsoid(V(0, -0.07, 1.80), (0.185, 0.14, 0.34))
    belly = sdf.ellipsoid(V(0, 0.02, 1.25), (0.15, 0.12, 0.25))
    sh = sdf.union(*[sdf.ellipsoid(V(s * 0.25, -0.05, 2.25), (0.11, 0.12, 0.09)) for s in (-1, 1)], k=0.1)
    acromion = sdf.union(*[sdf.sphere(V(s * 0.31, -0.06, 2.27), 0.045) for s in (-1, 1)])
    clav = sdf.union(*[sdf.capsule(V(s * 0.03, -0.20, 2.17), V(s * 0.28, -0.12, 2.27), 0.018) for s in (-1, 1)])
    neck = chain([V(0, -0.28, 2.50), V(0, -0.52, 2.46), V(0, -0.74, 2.24), V(0, -0.84, 2.03)], [0.10, 0.093, 0.095, 0.085], k=0.04)
    # carne gonfia sopra e sotto il salvagente che stringe
    bulge = sdf.union(sdf.sphere(RING_C - RING_AXIS * 0.072, 0.108), sdf.sphere(RING_C + RING_AXIS * 0.072, 0.105), k=0.03)
    # costole: archi in rilievo sul davanti del torace, sterno, clavicole
    ribs = []
    for i in range(7):
        z = 1.56 + i * 0.072
        w = 0.17 - 0.004 * i
        pts = [V(-w, 0.02, z + 0.02), V(-w * 0.75, -0.13, z - 0.005), V(-0.045, -0.205, z - 0.04), V(0.045, -0.205, z - 0.04), V(w * 0.75, -0.13, z - 0.005), V(w, 0.02, z + 0.02)]
        ribs.append(hair_clump(pts, 0.010, 0.0095))
    sternum = chain([V(0, -0.205, 1.64), V(0, -0.21, 2.12)], [0.011, 0.014], k=0.01)
    spine = []
    sp = [V(0, 0.17, 1.55), V(0, 0.05, 2.05), V(0, -0.15, 2.42), V(0, -0.30, 2.52)]
    for i in range(9):
        t = i / 8
        j = min(int(t * 3), 2)
        u = t * 3 - j
        c = sp[j] * (1 - u) + sp[j + 1] * u
        n = unit(V(0, 1.0 - 0.9 * t, 0.25 + 1.2 * t))
        spine.append(sdf.sphere(c + n * (0.18 - 0.05 * t), 0.036))
    arms = []
    for i, s in enumerate((-1, 1)):
        sh_p = V(s * SHOULDER[0], SHOULDER[1], SHOULDER[2])
        if grip is None:
            el, wr = V(s * 0.38, -0.22, 1.70), V(s * 0.24, -0.66, 1.18)
            mid = V(s * 0.34, -0.48, 1.36)
        else:
            wr = V(*grip[i])
            el = _elbow(sh_p, wr, s, 0.78, 0.82)
            mid = (el + wr) / 2
        arms.append(chain([sh_p, el], [0.058, 0.042], k=0.02))
        arms.append(chain([el, mid, wr], [0.042, 0.036, 0.028], k=0.02))
        arms.append(sdf.ellipsoid(el + V(s * 0.012, 0.012, 0), (0.042, 0.042, 0.048)))      # gomito ossuto
        arms.append(sdf.sphere(wr + V(s * 0.015, 0.0, 0.01), 0.024))
        for j, (dx, L) in enumerate(((-0.042, 0.85), (-0.014, 1.0), (0.014, 0.97), (0.042, 0.8))):
            if grip is None:
                k1 = wr + V(s * 0.55 * dx, -0.10, -0.035)
                k2 = k1 + V(s * dx * 0.6, -0.12 * L, -0.10 * L)
                k3 = k2 + V(s * dx * 0.3, -0.06 * L, -0.11 * L)
            else:                                   # dita che scavalcano il bordo e scendono dentro la barca
                k1 = wr + V(dx * 1.2, -0.11, -0.005)
                k2 = k1 + V(dx * 0.5, -0.07, -0.10 * L)
                k3 = k2 + V(dx * 0.2, 0.025, -0.10 * L)
            arms.append(hair_clump([wr, k1, k2, k3], 0.019, 0.008))
            arms.append(sdf.sphere(k1, 0.0165))
            arms.append(sdf.sphere(k2, 0.0125))
    body = sdf.union(back, chest, belly, sh, acromion, clav, neck, bulge, *spine, *arms, k=0.045)
    body = sdf.union(body, *ribs, sternum, k=0.022)
    # ventre incavato sotto le costole
    body = sdf.subtract(body, sdf.ellipsoid(V(0, -0.24, 1.40), (0.13, 0.06, 0.12)), k=0.06)
    body = sdf.subtract(body, torus_axis(RING_C, RING_AXIS, 0.128, 0.05), k=0.02)
    # branchie sul collo, sotto la testa
    gills = sdf.union(*[ellipsoid_rot(V(s * 0.093, -0.775 - 0.012 * i, 2.19 - 0.04 * i), (0.007, 0.011, 0.032), sdf.rot_matrix('x', 25)) for s in (-1, 1) for i in range(3)])
    body = sdf.subtract(body, gills, k=0.004)
    body = sdf.displace(body, skin.ring_folds(RING_C - RING_AXIS * 0.06, RING_AXIS, 0.10, 0.05, freq=4, amp=0.0025), 1.0)
    body = sdf.displace(body, skin.ring_folds(RING_C + RING_AXIS * 0.06, RING_AXIS, 0.10, 0.05, freq=4, amp=0.0025), 1.0)
    body = sdf.displace(body, skin.bumps(51, 0.05, 0.004), 1.0)
    body = sdf.displace(body, skin.bumps(52, 0.012, 0.0012), 1.0)
    return body


# ───────────────────────── testa (sistema locale) ─────────────────────────

def head_local():
    cran = sdf.ellipsoid(V(0, 0.01, 0.03), (0.10, 0.11, 0.12))
    crest = sdf.ellipsoid(V(0, 0.02, 0.135), (0.012, 0.08, 0.025))
    brow = sdf.ellipsoid(V(0, -0.088, 0.036), (0.090, 0.040, 0.030))
    maxilla = chain([V(0, -0.07, -0.02), V(0, -0.115, -0.10), V(0, -0.122, -0.145)], [0.078, 0.058, 0.05], k=0.02)
    cheekbones = sdf.union(*[sdf.sphere(V(s * 0.07, -0.077, -0.027), 0.031) for s in (-1, 1)])
    # mandibola a U (non un blocco pieno), con il mento e il pavimento della bocca
    jaw = sdf.union(hair_clump([V(-0.068, -0.10, -0.39), V(-0.05, -0.132, -0.43), V(0, -0.145, -0.447), V(0.05, -0.132, -0.43), V(0.068, -0.10, -0.39)], 0.019, 0.019),
                    sdf.sphere(V(0, -0.142, -0.458), 0.023),
                    sdf.ellipsoid(V(0, -0.10, -0.415), (0.058, 0.04, 0.011)),
                    *[chain([V(s * 0.068, -0.10, -0.39), V(s * 0.085, -0.055, -0.20), V(s * 0.09, -0.01, -0.06)], [0.019, 0.015, 0.017], k=0.01) for s in (-1, 1)])
    membrane = sdf.union(*[sdf.ellipsoid(V(s * 0.08, -0.05, -0.22), (0.009, 0.05, 0.17)) for s in (-1, 1)])
    head = sdf.union(cran, crest, brow, maxilla, cheekbones, jaw, membrane, k=0.03)
    # palpebre pesanti sugli occhietti
    lids = []
    for s in (-1, 1):
        e = V(s * 0.044, -0.105, 0.0)
        shell = sdf.subtract(sdf.sphere(e, 0.026), sdf.sphere(e, 0.0172))
        lids.append(sdf.intersect(shell, above(e + V(0, 0, 0.004), (0, 0.3, 1)), k=0.002))
    cut = sdf.union(
        *[sdf.sphere(V(s * 0.09, -0.115, -0.08), 0.032) for s in (-1, 1)],              # guance scavate
        *[sdf.sphere(V(s * 0.105, -0.02, 0.0), 0.04) for s in (-1, 1)],                 # tempie
        *[sdf.sphere(V(s * 0.044, -0.112, 0.0), 0.0215) for s in (-1, 1)],             # orbite
        *[sdf.ellipsoid(V(s * 0.015, -0.166, -0.085), (0.005, 0.01, 0.015)) for s in (-1, 1)],   # narici a fessura
        sdf.ellipsoid(V(0, -0.115, -0.265), (0.058, 0.07, 0.115)),                      # bocca spalancata
    )
    head = sdf.subtract(head, cut, k=0.006)
    head = sdf.union(head, *lids, k=0.003)
    head = sdf.displace(head, skin.wrinkles(61, 0.014, 0.0012, center=V(0, -0.06, -0.22), radius=0.2, direction=(0, 0, 1)), 1.0)
    head = sdf.displace(head, skin.wrinkles(62, 0.010, 0.0010, center=V(0, -0.10, 0.04), radius=0.06, direction=(1, 0, 0)), 1.0)
    return head


def head_attrs():
    R, c = HEAD.R, HEAD.pos

    def loc(p):
        return (p - c) @ R

    def mouth(p):
        q = loc(p)
        m = np.clip(1.0 - np.linalg.norm((q - V(0, -0.10, -0.265)) / V(0.06, 0.06, 0.12), axis=1), 0, 1) * (q[:, 1] > -0.17)
        for s in (-1, 1):
            m = np.maximum(m, np.clip(1.0 - np.linalg.norm((q - V(s * 0.015, -0.16, -0.085)) / V(0.008, 0.012, 0.018), axis=1), 0, 1))
            m = np.maximum(m, 0.7 * np.clip(1.0 - np.linalg.norm((q - V(s * 0.044, -0.11, 0.0)) / V(0.024, 0.024, 0.024), axis=1), 0, 1))
        return m

    def slime(p):
        q = loc(p)
        return np.clip(1.0 - np.linalg.norm((q - V(0, -0.12, -0.27)) / V(0.09, 0.08, 0.2), axis=1), 0, 1)

    def scar(p):
        return np.zeros(len(p), F)

    return {'mouth': mouth, 'slime': slime, 'scar': scar}


def teeth_pairs():
    rng = np.random.default_rng(9)
    pairs = []
    for i in range(13):
        t = i / 12 - 0.5
        if rng.random() < 0.12:
            continue                                   # qualche dente manca
        x = t * 0.105
        y = -0.142 + abs(t) * 0.05
        L = rng.uniform(0.028, 0.05) * (1 - 0.5 * abs(t))
        pairs.append((HEAD.pt((x, y, -0.142)), HEAD.pt((x * 0.92, y + 0.006, -0.142 - L)), 0.0055))
        L2 = rng.uniform(0.025, 0.045) * (1 - 0.5 * abs(t))
        pairs.append((HEAD.pt((x, y + 0.006, -0.388)), HEAD.pt((x * 0.92, y + 0.012, -0.388 + L2)), 0.005))
    return pairs


def slime_bits():
    """Melma vera: fili di bava tra i denti e la mascella, gocce dal mento e dai denti, gocce dal salvagente."""
    rng = np.random.default_rng(23)
    mouth = []
    for x, sag in ((-0.035, 0.02), (-0.012, 0.035), (0.012, 0.03), (0.034, 0.018), (0.0, 0.05)):
        a = HEAD.pt((x, -0.135, -0.165))
        b = HEAD.pt((x * 0.85, -0.14, -0.375))
        mouth.append(skin.strand(a, b, sag, 0.0016))
    for x in (-0.03, 0.0, 0.028):
        mouth.append(skin.drip(HEAD.pt((x, -0.15, -0.205)), rng.uniform(0.015, 0.03), 0.0018, 0.0035))
    for x, L in ((-0.02, 0.06), (0.008, 0.035), (0.03, 0.05)):
        mouth.append(skin.drip(HEAD.pt((x, -0.155, -0.47)), L, 0.003, 0.0055))
    pts = np.array([HEAD.pt(q) for q in ((-0.1, -0.2, -0.1), (0.1, -0.05, -0.62))], F)
    out = [('GulpySlimeMouth', sdf.union(*mouth), pts.min(0) - 0.08, pts.max(0) + 0.08)]
    up = unit(V(0, -1, 1) - (V(0, -1, 1) @ RING_AXIS) * RING_AXIS)
    low = RING_C - up * 0.17
    ring = sdf.union(*[skin.drip(low + V(dx, 0, 0), L, 0.003, 0.005) for dx, L in ((-0.05, 0.05), (0.03, 0.09), (0.07, 0.03))])
    out.append(('GulpySlimeRing', ring, low - V(0.12, 0.06, 0.13), low + V(0.12, 0.06, 0.02)))
    return out


# ───────────────────────── salvagente ─────────────────────────

def duck_ring():
    c, axis = RING_C, RING_AXIS
    R, r = 0.135, 0.056
    up = unit(V(0, -1, 1) - (V(0, -1, 1) @ axis) * axis)
    ring = torus_axis(c, axis, R, r)
    ring = sdf.displace(ring, skin.bumps(71, 0.03, 0.0018), 1.0)          # un po' sgonfio
    seams = sdf.union(torus_axis(c + axis * (r * 0.98), axis, R, 0.0035), torus_axis(c - axis * (r * 0.98), axis, R, 0.0035))
    base = c + up * (R + r * 0.4)
    head = base + up * 0.075 + V(0, -0.025, 0)
    duck = sdf.union(sdf.capsule(base, head, 0.045), sdf.sphere(head, 0.062), k=0.03)
    fwd = unit(V(0, -1, -0.15))
    bk = head + fwd * 0.07 + V(0, 0, -0.012)
    beak = sdf.union(sdf.ellipsoid(bk, (0.040, 0.042, 0.014)), sdf.ellipsoid(bk + V(0, 0.004, -0.015), (0.034, 0.036, 0.008)), k=0.004)
    eyes = sdf.union(*[sdf.sphere(head + V(s * 0.033, -0.046, 0.022), 0.0105) for s in (-1, 1)])
    glints = sdf.union(*[sdf.sphere(head + V(s * 0.036, -0.054, 0.027), 0.0035) for s in (-1, 1)])
    valve = sdf.round_cone(c - up * (R - 0.01) + axis * (r * 0.7), c - up * (R - 0.01) + axis * (r * 1.05), 0.008, 0.007)
    return [('DuckRing', sdf.union(ring, duck, k=0.02), (0.86, 0.62, 0.10)), ('DuckSeams', seams, (0.78, 0.55, 0.08)),
            ('DuckBeak', beak, (0.92, 0.33, 0.05)), ('DuckEyes', eyes, None), ('DuckGlints', glints, 'white'),
            ('DuckValve', valve, (0.85, 0.82, 0.74))]


# ───────────────────────── costruzione ─────────────────────────

def build(grip=None, viewer=None, lo=None, hi=None):
    """grip: polsi (locali) se si aggrappa al bordo; viewer: dove guardano gli occhi (locale).
    lo/hi: box del corpo (si allarga quando le braccia si allungano verso la barca)."""
    viewer = VIEWER if viewer is None else V(*viewer)
    rb = 0.008 if FAST else 0.005
    rh = 0.003 if FAST else 0.0016
    obs = []
    if grip is not None:
        # il riquadro del corpo deve contenere anche i gomiti, spinti in fuori dalle mani aggrappate
        lo = V(-0.62, -1.0, -0.02) if lo is None else V(*lo)
        hi = V(0.62, 0.48, 2.72) if hi is None else V(*hi)
        for i, sd in enumerate((-1, 1)):
            sh = V(sd * SHOULDER[0], SHOULDER[1], SHOULDER[2])
            wr = V(*grip[i])
            el = _elbow(sh, wr, sd, 0.78, 0.82)
            for p in (sh, el, wr):
                lo = np.minimum(lo, p - 0.14)
                hi = np.maximum(hi, p + 0.14)
    sk = skin.creature_skin('GulpySkin', base=(0.19, 0.205, 0.19), dark=(0.06, 0.07, 0.065), light=(0.33, 0.345, 0.32),
                            vein=(0.12, 0.13, 0.18), rough=0.68, sss=0.10, scale=1.3)
    # corpo e testa sono lo stesso campo, tagliato al salvagente (la cucitura resta sotto l'anello)
    head_w = HEAD.field(head_local())
    full = sdf.union(body_field(grip), head_w, k=0.035)
    head_zone = sdf.intersect(above(RING_C, RING_AXIS), sdf.sphere(HEAD.pos, 0.55))
    head_zone2 = sdf.intersect(above(RING_C - RING_AXIS * 0.01, RING_AXIS), sdf.sphere(HEAD.pos, 0.56))
    body = sdf_object('GulpyBody', sdf.subtract(full, head_zone), lo if lo is not None else V(-0.62, -1.0, -0.02),
                      hi if hi is not None else V(0.62, 0.48, 2.72), res=rb, banded=True)
    body.data.materials.append(sk)
    head = sdf_object('GulpyHead', sdf.intersect(full, head_zone2), V(-0.14, -1.12, 1.45), V(0.14, -0.58, 2.40), res=rh,
                      attrs=head_attrs(), banded=True)
    head.data.materials.append(sk)
    obs += [body, head]
    for s in (-1, 1):
        e = HEAD.pt((s * 0.044, -0.105, 0.0))
        obs.append(eyeball(f'GulpyEye{s}', tuple(map(float, e)), 0.0168, skin.cloudy_eye(), look=tuple(map(float, unit(viewer - e)))))
    # fondo della bocca scuro: dalla bocca spalancata non si deve vedere attraverso
    th = HEAD.field(sdf.union(sdf.ellipsoid(V(0, -0.05, -0.27), (0.06, 0.045, 0.14)), sdf.ellipsoid(V(0, -0.075, -0.40), (0.05, 0.04, 0.03)), k=0.03))
    c0 = HEAD.pt((0, -0.05, -0.30))
    thr = sdf_object('GulpyThroat', th, c0 - 0.25, c0 + 0.25, res=0.004 if FAST else 0.002, banded=True)
    thr.data.materials.append(mat_simple('GulpyThroatFlesh', (0.035, 0.008, 0.01), rough=0.3, coat=0.9, coat_rough=0.05))
    obs.append(thr)
    tp = teeth_pairs()
    tf = sdf.union(*[sdf.round_cone(b, t, r, r * 0.15) for b, t, r in tp])
    pts = np.array([p for b, t, _ in tp for p in (b, t)], F)
    te = sdf_object('GulpyTeeth', tf, pts.min(0) - 0.02, pts.max(0) + 0.02, res=0.0011)
    te.data.materials.append(needle_teeth())
    obs.append(te)
    for name, fld, lo, hi in slime_bits():
        sl = sdf_object(name, fld, lo, hi, res=0.0016 if FAST else 0.0009, banded=True)
        sl.data.materials.append(skin.slime_material())
        obs.append(sl)
    for name, f, col in duck_ring():
        o = sdf_object(name, f, RING_C - 0.32, RING_C + 0.32, res=0.004 if FAST else 0.0018, banded=True)
        if col is None:
            o.data.materials.append(mat_simple('DuckEyePaint', (0.01, 0.01, 0.01), rough=0.25))
        elif col == 'white':
            o.data.materials.append(mat_simple('DuckGlintPaint', (0.85, 0.85, 0.82), rough=0.3))
        else:
            o.data.materials.append(vinyl(name + 'Vinyl', col))
        obs.append(o)
    return obs


# ───────────────────────── vetrina ─────────────────────────

SHOTS = {
    'insieme': ((-0.85, -3.05, 1.35), (0.0, -0.55, 1.72), 36),
    'testa': ((-0.42, -1.85, 1.60), (0.0, -0.92, 1.80), 50),
}


def showcase(shots=('insieme', 'testa')):
    from mathutils import Vector
    out = []
    sc = reset_scene()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.cycles.use_denoising = True
    w = bpy.data.worlds.new('Night')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.010, 0.014, 0.022, 1)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0.0))
    sea = bpy.context.object
    sea.data.materials.append(mat_simple('NightSea', (0.004, 0.012, 0.016), rough=0.06, spec=0.8))
    build()
    s = np.array((0, -0.7, 1.85))
    # la lampara della barca (calda, davanti e un po' sotto), la luna dietro
    area_light('Key', (-0.7, -3.0, 1.75), tuple(s), 70, (1.0, 0.74, 0.46), 0.45)
    area_light('Rim', (0.9, 1.4, 3.4), tuple(s), 220, (0.55, 0.72, 1.0), 0.5)
    area_light('Fill', (1.4, -2.6, 2.2), tuple(s), 6, (0.55, 0.65, 0.85), 1.6)
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
        path = os.path.join(CACHE, 'vetrina', f'gulpy_{name}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('ok', path, flush=True)
    return out


if __name__ == '__main__':
    showcase()
