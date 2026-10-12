"""
I bambini della foto del 1997 (il finale B «Il ricordo», tools/render/finali.py → foto_1997). Da approvare.

Bambini di 7-9 anni modellati con i campi SDF (come i mostri): la testa grande da bambino con gli occhi, il naso, la
bocca, le orecchie, i capelli o il berretto; il collo, le spalle strette, le braccia con gomito e polso e le mani con
le dita; la maglietta e i calzoncini estivi degli anni '90 con le pieghe; le gambe con le ginocchia, i calzini e le
scarpe da ginnastica. Ogni bambino ha una posa (dove stanno gomiti, mani e piedi) e i suoi vestiti.

Coordinate del bambino: i piedi a z = 0, la faccia verso −Y (dove sta la macchinetta), +X alla destra di chi guarda la
foto. Il bambino si mette nel mondo con una matrice (build(..., matrix=M)).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

import sdf as S
from common import set_lightgroup
from creature import eyeball, sdf_object
from nodes import material

F = np.float32


def V(*a):
    return np.array(a, F)


def unit(v):
    v = np.asarray(v, F)
    return v / max(1e-9, float(np.linalg.norm(v)))


@dataclass
class Posa:
    """Dove stanno le articolazioni (coordinate del bambino, metri). L e R sono i lati di chi guarda la foto."""
    altezza: float = 1.28
    gomito_l: tuple = (-0.19, 0.0, 0.80)
    mano_l: tuple = (-0.20, -0.02, 0.62)
    gomito_r: tuple = (0.19, 0.0, 0.80)
    mano_r: tuple = (0.20, -0.02, 0.62)
    piede_l: tuple = (-0.07, 0.0)
    piede_r: tuple = (0.07, 0.0)
    # la mano aperta (saluta) o chiusa (tiene qualcosa); la testa girata (gradi, verso +X) e inclinata
    aperta_l: bool = False
    aperta_r: bool = False
    testa_yaw: float = 0.0
    testa_tilt: float = 0.0


@dataclass
class Vestiti:
    maglia: tuple = (0.8, 0.2, 0.2)
    maglia_b: tuple | None = None          # il secondo colore: righe o fascia sul petto
    righe: bool = False
    calzoncini: tuple = (0.2, 0.3, 0.5)
    jeans: bool = False
    capelli: tuple = (0.12, 0.07, 0.03)
    taglio: str = 'corto'                   # corto, caschetto, coda
    berretto: tuple | None = None
    scarpe: tuple = (0.9, 0.9, 0.88)
    pelle: tuple = (0.80, 0.58, 0.45)
    occhi: tuple = (0.25, 0.15, 0.08)


def _mat(name, color, rough=0.5, **kw):
    m, g = material(name)
    g.output_material(g.principled(color=color, rough=rough, **kw))
    return m


def pelle_material(name, base):
    m, g = material(name)
    co = g.texcoord('Object')
    n = g.noise(co, scale=60.0, detail=3.0)
    blush = g.noise(co, scale=8.0, detail=2.0)
    col = g.mix(g.mul(g.smoothstep(0.5, 0.75, blush.fac), 0.25), base, (base[0] * 1.05, base[1] * 0.78, base[2] * 0.72))
    g.output_material(g.principled(color=col, rough=0.48, sss=0.35, sss_radius=(1.0, 0.45, 0.25), sss_scale=0.02,
                                   normal=g.bump(n.fac, strength=0.08, distance=0.002)))
    return m


def stoffa_material(name, c1, c2=None, righe=False, jeans=False):
    """Cotone estivo: la trama fine, le pieghe (rilievo largo) e, se c'è, la seconda tinta a righe o in fascia."""
    m, g = material(name)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    col = c1
    if c2 is not None:
        if righe:
            band, _ = g.wave(co, scale=22.0, kind='BANDS', axis='Z', profile='SIN')
            col = g.mix(g.smoothstep(0.45, 0.55, g.bw(band)), c1, c2)
        else:
            # una fascia sul petto (le magliette colorblock degli anni '90)
            fascia = g.mul(g.smoothstep(0.885, 0.89, z), g.smoothstep(0.985, 0.98, z))
            col = g.mix(fascia, c1, c2)
    weave = g.noise(co, scale=400.0, detail=2.0)
    folds = g.noise(g.mapping(co, scale=(9.0, 9.0, 3.0)), scale=2.0, detail=3.0, rough=0.5)
    if jeans:
        tw, _ = g.wave(g.mapping(co, rot=(0, 0.7, 0)), scale=300.0, kind='BANDS', axis='X')
        col = g.mix(g.mul(g.bw(tw), 0.25), col, (col[0] * 0.6, col[1] * 0.65, col[2] * 0.75))
    h = g.add(g.mul(folds.fac, 1.0), g.mul(weave.fac, 0.08))
    g.output_material(g.principled(color=col, rough=0.85, sheen=0.5, sheen_rough=0.4, normal=g.bump(h, strength=0.35, distance=0.01)))
    return m


def capelli_material(name, c):
    m, g = material(name)
    co = g.texcoord('Object')
    strand = g.noise(g.mapping(co, scale=(60.0, 60.0, 6.0)), scale=4.0, detail=4.0)
    col = g.mix(g.smoothstep(0.3, 0.8, strand.fac), (c[0] * 0.6, c[1] * 0.6, c[2] * 0.6), (c[0] * 1.3, c[1] * 1.25, c[2] * 1.2))
    g.output_material(g.principled(color=col, rough=0.45, spec=0.6, normal=g.bump(strand.fac, strength=0.5, distance=0.004)))
    return m


def occhio_material(name, iride):
    m, g = material(name)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    r = g.vmath('LENGTH', g.comb(x, z, 0.0))
    front = g.smoothstep(0.1, -0.3, y)
    iris = g.mul(g.smoothstep(0.50, 0.46, r), front)
    pupil = g.mul(g.smoothstep(0.24, 0.21, r), front)
    col = g.mix(iris, (0.88, 0.86, 0.82), iride)
    col = g.mix(pupil, col, (0.01, 0.01, 0.01))
    g.output_material(g.principled(color=col, rough=0.2, coat=1.0, coat_rough=0.02))
    return m


# ───────────────────────── i pezzi ─────────────────────────

def _testa(c, yaw, tilt):
    """La testa in coordinate del bambino, centrata in c, girata di yaw (verso +X) e inclinata di tilt (gradi).
    Restituisce (campo della testa, punti utili: occhi, attaccatura dei capelli, sommità, orecchie)."""
    R = S.rot_matrix('z', yaw) @ S.rot_matrix('x', tilt)

    def q(*p):
        return c + R @ V(*p)
    cran = S.ellipsoid(q(0, 0.012, 0.02), (0.076, 0.086, 0.088))
    face = S.ellipsoid(q(0, -0.028, -0.03), (0.062, 0.058, 0.064))
    cheeks = S.union(S.sphere(q(-0.034, -0.05, -0.028), 0.03), S.sphere(q(0.034, -0.05, -0.028), 0.03))
    chin = S.sphere(q(0, -0.052, -0.074), 0.024)
    nose = S.round_cone(q(0, -0.072, -0.002), q(0, -0.086, -0.022), 0.008, 0.0115)
    ears = S.union(S.ellipsoid(q(-0.078, 0.002, -0.005), (0.012, 0.02, 0.028)), S.ellipsoid(q(0.078, 0.002, -0.005), (0.012, 0.02, 0.028)))
    f = S.union(cran, face, cheeks, chin, k=0.025)
    f = S.union(f, nose, k=0.008)
    f = S.union(f, ears, k=0.006)
    # le orbite e la bocca (un taglio appena sorridente)
    eyes = [q(-0.028, -0.059, 0.006), q(0.028, -0.059, 0.006)]
    sockets = S.union(*[S.ellipsoid(e + R @ V(0, -0.006, 0), (0.015, 0.008, 0.011)) for e in eyes])
    f = S.subtract(f, sockets, k=0.005)
    # le palpebre di sopra e un accenno di quelle di sotto (gli occhi non sporgono)
    lids = S.union(*[S.ellipsoid(e + R @ V(0, -0.0055, 0.0098), (0.0155, 0.0072, 0.0042)) for e in eyes],
                   *[S.ellipsoid(e + R @ V(0, -0.0045, -0.0112), (0.013, 0.005, 0.003)) for e in eyes])
    f = S.union(f, lids, k=0.003)
    mouth = S.ellipsoid(q(0, -0.086, -0.046), (0.019, 0.006, 0.0035))
    f = S.subtract(f, mouth, k=0.004)
    pts = {'eyes': eyes, 'top': q(0, 0.0, 0.11), 'brow': q(0, -0.07, 0.04), 'R': R, 'c': c}
    return f, pts


def _mano(polso, dirz, aperta):
    """La mano: il palmo e le dita (aperte e un po' allargate per salutare, o piegate a tenere qualcosa)."""
    d = unit(dirz)
    side = unit(np.cross(d, V(0, -1, 0)) if abs(d[1]) < 0.9 else np.cross(d, V(1, 0, 0)))
    nrm = unit(np.cross(side, d))
    palm_c = polso + d * 0.032
    palm = S.ellipsoid(palm_c, (0.026, 0.026, 0.026))
    parts = [S.union(S.sphere(polso + d * 0.012, 0.021), S.sphere(palm_c, 0.025), k=0.015)]
    for k, off in enumerate((-0.015, -0.005, 0.005, 0.015)):
        base = palm_c + d * 0.022 + side * off
        L = (0.030, 0.034, 0.033, 0.027)[k]
        spread = (off * 1.2 if aperta else 0.0)
        tip = base + d * L + side * spread if aperta else base + d * L * 0.5 - nrm * L * 0.55
        parts.append(S.capsule(base, tip, 0.0068))
    tb = palm_c - side * 0.02 - nrm * 0.004
    parts.append(S.capsule(tb, tb + d * 0.018 - side * 0.016 - nrm * (0.0 if aperta else 0.012), 0.0075))
    del palm
    return S.union(*parts, k=0.006)


@dataclass
class Bambino:
    posa: Posa = field(default_factory=Posa)
    vestiti: Vestiti = field(default_factory=Vestiti)


def build(nome, b: Bambino, matrix, col='finali', res=0.0035):
    """Il bambino nel mondo (matrix: da coordinate del bambino al mondo). Restituisce (oggetti, punti utili nel mondo:
    il centro della testa, gli occhi)."""
    p, w = b.posa, b.vestiti
    H = p.altezza
    k = H / 1.28
    hip = 0.60 * k
    sh_z = 0.995 * k
    neck_top = 1.035 * k
    head_c = V(0, 0.0, neck_top + 0.085)
    sh_l, sh_r = V(-0.135 * k, 0.0, sh_z), V(0.135 * k, 0.0, sh_z)
    obs = []

    def mesh(name, f, lo, hi, mat, r=res):
        o = sdf_object(f'{nome}{name}', f, lo, hi, res=r, col=col, matrix=matrix, banded=True)
        o.data.materials.append(mat)
        set_lightgroup(o, 'ambient')
        obs.append(o)
        return o

    head, hp = _testa(head_c, p.testa_yaw, p.testa_tilt)
    neck = S.capsule(V(0, 0.005, sh_z - 0.02), V(0, 0.0, neck_top + 0.02), 0.037)
    # le braccia: spalla → gomito → polso, un po' più sottili verso il polso; le mani
    arms, sleeves, hands = [], [], []
    for sh, el, ha, op in ((sh_l, V(*p.gomito_l), V(*p.mano_l), p.aperta_l), (sh_r, V(*p.gomito_r), V(*p.mano_r), p.aperta_r)):
        el = el * V(1, 1, k)
        ha = ha * V(1, 1, k)
        d = unit(ha - el)
        wrist = ha - d * 0.045
        arms.append(S.union(S.round_cone(sh, el, 0.037, 0.03), S.round_cone(el, wrist, 0.029, 0.023), k=0.012))
        sleeves.append(S.round_cone(sh + V(0, 0, 0.0), sh + unit(el - sh) * 0.10, 0.044, 0.041))
        hands.append(_mano(wrist, d, op))
    # le gambe: anca → ginocchio → caviglia, coi piedi dove dice la posa
    legs, socks, shoes = [], [], []
    for sx, (fx, fy) in ((-1, p.piede_l), (1, p.piede_r)):
        top = V(sx * 0.065 * k, 0.0, hip)
        ank = V(fx, fy, 0.075)
        knee = (top + ank) / 2 + V(0, -0.012, 0.02)
        legs.append(S.union(S.round_cone(top, knee, 0.052, 0.038), S.round_cone(knee, ank, 0.036, 0.026), k=0.015))
        socks.append(S.round_cone(ank + V(0, 0, 0.065), ank, 0.03, 0.03))
        shoe = S.union(S.ellipsoid(V(fx, fy - 0.035, 0.035), (0.045, 0.095, 0.042)),
                       S.ellipsoid(V(fx, fy + 0.01, 0.06), (0.04, 0.05, 0.04)), k=0.02)
        shoes.append(S.intersect(shoe, S.plane((0, 0, -1), 0.0)))
    skin = pelle_material(f'{nome}Pelle', w.pelle)
    body_lo, body_hi = V(-0.6, -0.5, -0.02), V(0.6, 0.5, H + 0.15)
    mesh('Pelle', S.union(head, neck, *arms, *hands, *legs, k=0.006), body_lo, body_hi, skin)
    # la maglietta: il busto da bambino (la pancetta, le spalle strette), le maniche corte, le pieghe in vita
    torso = S.union(S.ellipsoid(V(0, 0.005, (hip + sh_z) / 2 + 0.02 * k), (0.125 * k, 0.085, (sh_z - hip) / 2 + 0.045)),
                    S.ellipsoid(V(0, 0.0, sh_z - 0.035), (0.16 * k, 0.085, 0.055)), k=0.06)
    torso = S.union(torso, *sleeves, k=0.02)
    pieghe = lambda q: 0.004 * np.sin(q[:, 2] * 90.0 + q[:, 0] * 25.0) * np.exp(-((q[:, 2] - hip - 0.06) / 0.08) ** 2)  # noqa: E731
    torso = S.displace(torso, pieghe, 1.0)
    torso = S.subtract(torso, S.capsule(V(0, -0.01, sh_z + 0.04), V(0, -0.01, sh_z + 0.1), 0.045), k=0.01)
    mesh('Maglia', torso, body_lo, body_hi, stoffa_material(f'{nome}Maglia', w.maglia, w.maglia_b, w.righe))
    # i calzoncini: il bacino e le due gambe larghe fin sopra il ginocchio
    sx_l, sx_r = V(-0.065 * k, 0.0, hip), V(0.065 * k, 0.0, hip)
    mid = lambda a, fxy: a + (V(fxy[0], fxy[1], 0.075) - a) * 0.38  # noqa: E731
    shorts = S.union(S.ellipsoid(V(0, 0.005, hip + 0.035), (0.135 * k, 0.088, 0.075)),
                     S.round_cone(sx_l + V(0, 0, 0.02), mid(sx_l, p.piede_l), 0.068, 0.058),
                     S.round_cone(sx_r + V(0, 0, 0.02), mid(sx_r, p.piede_r), 0.068, 0.058), k=0.03)
    mesh('Calzoncini', shorts, body_lo, body_hi, stoffa_material(f'{nome}Calz', w.calzoncini, jeans=w.jeans))
    mesh('Calzini', S.union(*socks), body_lo, body_hi, _mat(f'{nome}Calzini', (0.92, 0.92, 0.9), rough=0.9), r=res)
    mesh('Scarpe', S.union(*shoes), body_lo, body_hi, _mat(f'{nome}Scarpe', w.scarpe, rough=0.55), r=res)
    # i capelli: una calotta sopra la testa, che lascia scoperta la faccia, coi ciuffi della frangia
    R, c = hp['R'], hp['c']

    def q(*a):
        return c + R @ V(*a)
    if w.berretto is None:
        calotta = S.ellipsoid(q(0, 0.016, 0.03), (0.084, 0.094, 0.094))
        faccia = S.union(S.box(q(0, -0.09, -0.05), (0.07, 0.06, 0.075), 0.02), S.box(q(0, 0.0, -0.11), (0.1, 0.1, 0.05)))
        hair = S.subtract(calotta, faccia, k=0.01)
        frangia = S.ellipsoid(q(0, -0.07, 0.045), (0.062, 0.024, 0.024))
        hair = S.union(hair, frangia, k=0.02)
        if w.taglio == 'caschetto':
            hair = S.union(hair, S.ellipsoid(q(0, 0.02, -0.03), (0.09, 0.085, 0.065)), k=0.02)
            hair = S.subtract(hair, S.box(q(0, -0.1, -0.05), (0.065, 0.06, 0.08), 0.02), k=0.01)
        if w.taglio == 'coda':
            hair = S.union(hair, S.round_cone(q(0, 0.09, 0.02), q(0, 0.12, -0.13), 0.035, 0.02), k=0.02)
        tex = lambda pp: 0.0015 * np.sin(pp[:, 0] * 900.0 + pp[:, 2] * 300.0)  # noqa: E731
        hair = S.displace(hair, tex, 1.0)
        mesh('Capelli', hair, body_lo, body_hi, capelli_material(f'{nome}Capelli', w.capelli), r=res * 0.8)
    else:
        # i capelli corti sotto il berretto, e il berretto con la visiera
        nuca = S.subtract(S.ellipsoid(q(0, 0.02, 0.0), (0.082, 0.09, 0.08)), S.box(q(0, -0.09, -0.04), (0.08, 0.07, 0.09), 0.02), k=0.01)
        mesh('Capelli', nuca, body_lo, body_hi, capelli_material(f'{nome}Capelli', w.capelli), r=res * 0.8)
        # il berretto da baseball: la cupola bassa a spicchi e la visiera lunga, appena piegata in giù
        crown = S.intersect(S.ellipsoid(q(0, 0.012, 0.038), (0.086, 0.094, 0.072)), S.plane(tuple(R @ V(0, 0, -1)), float(np.dot(R @ V(0, 0, 1), q(0, 0, 0.036)))))
        visor = S.intersect(S.ellipsoid(q(0, -0.105, 0.036), (0.068, 0.07, 0.006)), S.plane(tuple(R @ V(0, 1, 0)), float(-np.dot(R @ V(0, 1, 0), q(0, -0.06, 0)))))
        cap = S.union(crown, visor, k=0.006)
        cap = S.union(cap, S.sphere(q(0, 0.01, 0.108), 0.007))
        mesh('Berretto', cap, body_lo, body_hi, stoffa_material(f'{nome}Berretto', w.berretto), r=res * 0.8)
    # gli occhi veri (sfere col colore dell'iride), guardano verso la macchinetta
    from mathutils import Matrix, Vector
    M = matrix if matrix is not None else Matrix.Identity(4)
    eyes_w = []
    om = occhio_material(f'{nome}Occhio', w.occhi)
    for e in hp['eyes']:
        ew = M @ Vector(tuple(float(x) for x in e))
        look = (M.to_3x3() @ Vector(tuple(float(x) for x in (R @ V(0, -1, 0))))).normalized()
        o = eyeball(f'{nome}Occhio', tuple(ew), 0.0108 * (M.to_scale()[0]), om, look=tuple(look), col=col)
        obs.append(o)
        eyes_w.append(np.array(ew))
    head_w = np.array(M @ Vector(tuple(float(x) for x in head_c)))
    return obs, {'head': head_w, 'eyes': eyes_w, 'top': np.array(M @ Vector(tuple(float(x) for x in hp['top'])))}


def mano_mondo(b: Bambino, lato, matrix):
    """Dove sta la mano (nel mondo), per appoggiarci qualcosa (la canna giocattolo)."""
    from mathutils import Vector
    k = b.posa.altezza / 1.28
    m = V(*(b.posa.mano_l if lato == 'l' else b.posa.mano_r)) * V(1, 1, k)
    return np.array(matrix @ Vector(tuple(float(x) for x in m)))


def math_ok():
    return math.pi
