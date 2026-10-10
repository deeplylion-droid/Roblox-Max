"""
ROBIN — modello definitivo (sagoma A «Granchio», testa B «Baffi»), in lavorazione.

Steso sul capodibanda come un ragno di mare: il busto piatto sopra il bordo, le zampe-raggio ad arco con le
ginocchia più alte della schiena, la coda che scende fuori bordo fino al mare. Viene dalla gallinella (le
pettorali a ventaglio, i raggi liberi che usa come zampette) e dal pesce gatto (i baffi). Un braccio
lunghissimo, a tre segmenti come i raggi, attraversa la barca fino al secchio e ne tira fuori un pesce per la
coda; l'altro si tiene al capodibanda. Da bambino nascondeva le cose degli altri sotto gli scivoli: la
striscia di biglietti della sala giochi gli si avvolge attorno alle braccia e il capo libero pende nel secchio.

La testa è la B «Baffi» della tavola (teste_robin.py), presa così com'è: larga e piatta da pesce gatto, con
le orecchie di un bambino e la corazza solo in cima. I baffi invece si rifanno qui: nella tavola il secchio
stava sotto la testa, qui è a più di un metro, e i baffi lunghi pendono verso di lui.

Colori approvati (10 ottobre), quelli della tavola: rosso corallo pieno verso il cremisi, più scuro e bagnato
sul dorso, rosato sul ventre; ventagli e zampette turchese elettrico a macchie blu; la melma tinta di rosso.
I biglietti sono arancio saturo con le scritte (nella tavola delle teste erano rimasti color pesca).

Coordinate come la tavola: il bordo della barca corre lungo X a y = 0 (capodibanda a z = 0,75); dentro la
barca è y < 0, fuori c'è il mare (z = 0). La faccia guarda −Y. Nel gioco il busto è girato rispetto al
capodibanda (scena_creature.robin_posa): per questo piedi, presa, secchio e direzione del bordo arrivano
come parametri; senza parametri build() rifà la posa di gioco (POSA, numeri arrotondati).

Uso: tools/.venv/bin/python tools/render/robin.py [--fast]          vetrina → cache/vetrina/robin_*.png
     tools/.venv/bin/python tools/render/robin.py [--fast] --posa   la posa di gioco nella scena della barca,
                                                                    vista dall'occhio → docs/concept/pose_robin*.jpg
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

import dettagli as D  # noqa: E402
import sdf  # noqa: E402
import teste_robin as T  # noqa: E402
from common import CACHE, EYE, ROOT, reset_scene  # noqa: E402
from creature import sdf_object  # noqa: E402
from geo import catmull  # noqa: E402
from nodes import material  # noqa: E402

V, F, unit, chain = D.V, D.F, D.unit, D.chain
FAST = '--fast' in sys.argv
# la pelle è un campo solo (corpo, arti, testa) tagliato in quattro mesh a risoluzioni diverse, che combaciano
RES_BODY = 0.0045 if FAST else 0.003      # busto, coda, zampe, braccia
RES_HEAD = 0.0028 if FAST else 0.0016     # la testa (è il mostro più vicino al pescatore)
RES_HAND = 0.0032 if FAST else 0.0017     # il braccio lungo con la mano, l'altra mano sul bordo
RES_FINE = 0.0018 if FAST else 0.0011     # pezzi sottili (baffi, gocce)

GUN = T.GUN                               # piano del capodibanda (0,75)
HEAD = T.HEAD                             # centro della testa, come nella tavola
SPALLA = {s: V(s * 0.085, -0.285, 0.895) for s in (-1, 1)}
# le basi delle zampe-raggio sui fianchi del busto (davanti, in mezzo, dietro), come nella tavola
BASI = {s: [V(s * 0.10, -0.09, 0.93), V(s * 0.11, 0.09, 0.935), V(s * 0.10, 0.25, 0.905)] for s in (-1, 1)}
CODA = list(T.TAIL) + [V(0, 0.75, -0.34)]     # la coda della tavola, che scende un po' di più in acqua
L_ALTRO = 0.62                            # braccio e avambraccio dell'altro braccio, in tutto: piegato a chela
PESCE_L = 0.28                            # il pesce rubato
VENTAGLI_YAW = 28.0                       # i ventagli della tavola girati all'indietro: le braccia passano davanti

# la posa di gioco (scena_creature.robin_posa) in coordinate locali, arrotondata: è quella che build() fa
# senza parametri. Nel gioco i numeri si ricalcolano dalla barca.
POSA = {
    'viewer': (-0.216, -1.517, 1.252),
    'bucket': (1.277, -0.916, 0.707),
    'reach': (1.172, -0.907, 0.992),
    'feet': [(-0.207, -0.173, 0.741), (-0.294, -0.272, 0.502), (-0.028, -0.123, 0.402),
             (0.410, 0.008, 0.422), (0.254, 0.164, 0.767), (0.281, 0.101, 0.462)],
    'grip': (-0.436, -0.329, 0.737),
    'lungo': (0.84, 0.54, 0.0),
}


def orizz(v):
    """Versore della parte orizzontale di v."""
    v = V(*v)
    v[2] = 0.0
    return unit(v)


def gomito(a, b, L, fuori):
    """Il gomito (o il ginocchio) tra a e b di un arto lungo L in tutto, a due segmenti uguali, spinto verso
    'fuori' (la parte di 'fuori' perpendicolare ad a→b)."""
    a, b = V(*a), V(*b)
    d = float(np.linalg.norm(b - a))
    h = math.sqrt(max(0.0, (L / 2) ** 2 - (d / 2) ** 2))
    ax = (b - a) / max(d, 1e-6)
    o = V(*fuori)
    o = unit(o - (o @ ax) * ax)
    return (a + b) / 2 + o * h


# ───────────────────────── la posa degli arti ─────────────────────────

def raggio(s, base, piede):
    """Una zampa-raggio: dalla base sul fianco il ginocchio sale in fuori, più alto della schiena (sagoma A),
    poi la parte libera scende ad arco fino alla punta appoggiata in 'piede'."""
    tip = V(*piede) + V(0, 0, 0.008)
    h = tip - base
    h[2] = 0.0
    d = float(np.linalg.norm(h))
    out = V(s, 0, 0)
    kn = base + h * 0.36 + out * 0.16
    kn[2] = max(base[2], tip[2]) + 0.28 + 0.12 * min(d, 0.8)
    lat = unit(out * 0.6 + (h / max(d, 1e-6)) * 0.4)
    m1 = kn + (tip - kn) * 0.38 + lat * 0.055 + V(0, 0, 0.03)
    m2 = kn + (tip - kn) * 0.74 + lat * 0.03
    return [base, kn, m1, m2, tip]


def braccio_lungo(polso):
    """Il braccio che ruba: tre segmenti come i raggi liberi della gallinella. Dalla spalla sale a un primo
    gomito alto (come le ginocchia delle zampe), attraversa la barca col segmento di mezzo e scende col terzo
    sul secchio. Restituisce spalla, i due gomiti e il polso."""
    sh = SPALLA[1]
    d = polso - sh
    e1 = sh + d * 0.25 + V(0, 0, 0.24) + V(0.04, 0, 0)
    e2 = sh + d * 0.62 + V(0, 0, 0.12)
    return [sh, e1, e2, polso]


def curve_braccia(A):
    """Le curve delle braccia come le modella corpo(), segmento per segmento: [(punti, r0, r1)], dalla spalla
    al polso. Ogni segmento del braccio lungo si incurva appena; i biglietti ci si avvolgono sopra."""
    sh, e1, e2, wr = A['lungo']
    lungo = [([p0, (p0 + p1) / 2 + V(0, 0, -0.018), p1], r0, r1)
             for (p0, p1), (r0, r1) in zip(((sh, e1), (e1, e2), (e2, wr)), ((0.036, 0.029), (0.029, 0.025), (0.025, 0.020)))]
    sh2, el2, wr2 = A['altro']
    altro = [([sh2, el2], 0.036, 0.027), ([el2, (el2 + wr2) / 2 + V(0, 0, 0.015), wr2], 0.027, 0.020)]
    return {'lungo': lungo, 'altro': altro}


def pose_arti(P):
    """Tutti i punti degli arti per i parametri della posa P (coordinate locali)."""
    fist = V(*P['reach'])
    a = orizz(fist - SPALLA[1])                         # dal braccio verso il pesce
    polso = fist - a * 0.075 + V(0, 0, 0.035)
    lungo = braccio_lungo(polso)
    lg = orizz(P['lungo'])
    dentro = V(lg[1], -lg[0], 0.0)
    if dentro[1] > 0:
        dentro = -dentro                                # dentro la barca è verso −Y
    grip = V(*P['grip'])
    wr2 = grip - dentro * 0.03 + V(0, 0, 0.075)          # il polso sopra il capodibanda, un po' in fuori
    el2 = gomito(SPALLA[-1], wr2, L_ALTRO, V(-1.0, 0.15, 0.6))   # il gomito in fuori, sopra il mare
    feet = [V(*f) for f in P['feet']]
    rays = []
    for k, s in enumerate((-1, -1, -1, 1, 1, 1)):
        rays.append((s, raggio(s, BASI[s][k % 3], feet[k])))
    return {'fist': fist, 'a': a, 'lungo': lungo, 'altro': [SPALLA[-1], el2, wr2], 'grip': grip, 'bordo': lg,
            'dentro': dentro, 'rays': rays}


# ───────────────────────── mani ─────────────────────────

def pugno(polso, presa, a):
    """La mano che stringe il pesce per la coda: le dita lunghe e palmate si chiudono attorno al pesce che pende
    (asse verticale in 'presa'), il pollice dall'altra parte. a: verso orizzontale dal polso al pesce."""
    side = unit(np.cross(V(0, 0, 1), a))
    kn, tp, cv = [], [], []
    for i in range(4):
        z = 0.024 - 0.016 * i
        kn.append(presa - a * 0.036 + side * 0.020 + V(0, 0, z + 0.008))
        tp.append(presa - a * 0.010 - side * 0.026 + V(0, 0, z - 0.004))
        cv.append(a * 0.050 - side * 0.004)
    hand = T.mano(polso, kn, tp, r0=0.0118, r1=0.0062, palmata=0.4, curve=cv)
    th, _ = T.tubo([polso + side * 0.012 - V(0, 0, 0.012), presa - a * 0.030 - side * 0.030 + V(0, 0, -0.030),
                    presa - a * 0.004 - side * 0.034 + V(0, 0, -0.040)], 0.0115, 0.0075, n=5, nodi=0.12)
    return sdf.union(hand, th, k=0.008)


def presa_bordo(polso, presa, lungo, dentro):
    """La mano aggrappata al capodibanda: il palmo sopra il legno, le dita lunghe che scavalcano lo spigolo di
    dentro e scendono lungo la fiancata (come Molly, ma più lunghe e più magre)."""
    kn, tp, cv = [], [], []
    for dx, L in ((-0.048, 0.85), (-0.016, 1.0), (0.016, 0.95), (0.048, 0.8)):
        kn.append(presa + lungo * dx + dentro * 0.020 + V(0, 0, 0.034))
        tp.append(presa + lungo * dx * 1.25 + dentro * 0.085 + V(0, 0, -0.15 * L))
        cv.append(dentro * 0.03 + V(0, 0, 0.03))
    hand = T.mano(polso, kn, tp, r0=0.0125, r1=0.0058, palmata=0.6, curve=cv)
    th, _ = T.tubo([polso - lungo * 0.03, presa - lungo * 0.075 + dentro * 0.03 + V(0, 0, 0.02),
                    presa - lungo * 0.085 + dentro * 0.06 + V(0, 0, -0.05)], 0.0115, 0.0065, n=5, nodi=0.12)
    return sdf.union(hand, th, k=0.008)


# ───────────────────────── la testa (dalla tavola) ─────────────────────────

def testa(turn, pitch, viewer):
    """La testa B «Baffi» presa così com'è dalla tavola (teste_robin.robin_b), girata di 'turn' gradi e alzata
    di 'pitch' (come HEAD_YAW e HEAD_PITCH della tavola), con gli occhi che guardano 'viewer'.
    robin_b costruisce anche il corpo della tavola e le cose comuni (biglietti, ventagli, pesce): per il tempo
    della chiamata quelle due funzioni si sostituiscono, così si prendono solo il campo della testa (da unire
    al corpo nuovo), i tagli (bocca, narici, orecchie, orbite), gli attributi del colore e i pezzi a parte
    (gola, denti, occhi, bava). I baffi della tavola pendono dritti: si buttano e si rifanno (baffi())."""
    salva = {k: getattr(T, k) for k in ('HEAD', 'HEAD_YAW', 'HEAD_PITCH', 'CAM', 'corpo_mesh', 'comune')}
    preso = {}

    def corpo_mesh(fr, hf, cut=None, attrs=None, **kw):
        preso.update(fr=fr, hf=hf, cut=cut, attrs=attrs or {})

    T.HEAD, T.HEAD_YAW, T.HEAD_PITCH, T.CAM = HEAD, float(turn), float(pitch), V(*viewer)
    T.corpo_mesh, T.comune = corpo_mesh, (lambda obs, shh_wrist=None: obs)
    try:
        obs, _, _ = T.robin_b()
    finally:
        for k, v in salva.items():
            setattr(T, k, v)
    pezzi = []
    for o in obs:
        if o is None:
            continue
        if o.name.startswith('RobinBarbels'):
            me = o.data
            bpy.data.objects.remove(o)
            bpy.data.meshes.remove(me)
            continue
        pezzi.append(o)
    return preso['fr'], preso['hf'], preso['cut'], preso['attrs'], pezzi


def baffi(fr, verso):
    """I baffi del pesce gatto, con le radici della tavola: i due lunghi dagli angoli della bocca scendono e
    piegano verso il secchio ('verso': orizzontale), come se il pesce lo sentissero col gusto; i quattro corti
    sotto il mento pendono e piegano appena."""
    verso = orizz(verso)
    bb, pts = [], []
    for s in (-1, 1):
        r = fr.pt((s * 0.118, -0.104, -0.034))
        p = [r, r + fr.dir((s * 0.040, -0.045, 0.0)) + V(0, 0, -0.035)]
        for a_, b_ in ((0.025, 0.075), (0.05, 0.08), (0.065, 0.07), (0.07, 0.05), (0.06, 0.025), (0.035, -0.012)):
            p.append(p[-1] + verso * a_ + V(0, 0, -b_))
        f, cp = T.tubo(p, 0.0085, 0.0022, n=6)
        bb.append(f)
        pts.append(cp)
        for q, L in (((s * 0.020, -0.146, -0.074), 1.0), ((s * 0.052, -0.130, -0.072), 0.85)):
            r = fr.pt(q)
            p = [r, r + fr.dir((s * 0.004, -0.02, 0.0)) + V(0, 0, -0.035 * L), r + verso * 0.03 * L + V(0, 0, -0.085 * L),
                 r + verso * 0.055 * L + V(0, 0, -0.125 * L)]
            f, cp = T.tubo(p, 0.0045, 0.0015, n=5)
            bb.append(f)
            pts.append(cp)
    return T.fine('RobinBarbels', sdf.union(*bb), pts, T.pelle_robin(), res=RES_FINE, attrs={'ventre': T.costante(0.6)})


# ───────────────────────── il corpo ─────────────────────────

def corpo(hf, A):
    """Il campo del corpo intero: busto, coda, collo, il braccio lungo con la mano che stringe il pesce, l'altro
    braccio aggrappato al bordo, le sei zampe-raggio; unito alla testa."""
    torso = T.squash(chain(T.SPINE, [0.085, 0.12, 0.13, 0.11], k=0.05), (0, 0, 0.92), (1.0, 1.0, 0.78))
    tail = chain(CODA, [0.11, 0.085, 0.07, 0.06, 0.05, 0.04], k=0.04)
    belly = sdf.ellipsoid(V(0, 0.0, 0.825), (0.10, 0.14, 0.07))          # la pancia che si appoggia al bordo
    sp = catmull(T.SPINE[1:] + T.TAIL[1:3], 3)
    bumps = sdf.union(*[sdf.sphere(c + V(0, 0, 0.085 - 0.02 * i / len(sp)), 0.022 - 0.008 * i / len(sp)) for i, c in enumerate(sp)])
    neck = chain([T.SPINE[0], V(0, -0.44, 0.90)], [0.085, 0.08], k=0.02)
    parts = [torso, tail, belly, bumps, neck, hf]
    C = curve_braccia(A)
    # il braccio lungo: tre segmenti a nodi, i gomiti ossuti
    sh, e1, e2, wr = A['lungo']
    for pts, r0, r1 in C['lungo']:
        parts.append(T.tubo(pts, r0, r1, n=6, nodi=0.10)[0])
    parts += [sdf.sphere(e1, 0.034), sdf.sphere(e2, 0.029)]
    lo = np.minimum(wr, A['fist']) - 0.11
    hi = np.maximum(wr, A['fist']) + 0.11
    parts.append(T.entro(pugno(wr, A['fist'], A['a']), lo, hi))
    # l'altro braccio, aggrappato al capodibanda
    sh2, el2, wr2 = A['altro']
    parts += [T.tubo(pts, r0, r1)[0] for pts, r0, r1 in C['altro']] + [sdf.sphere(el2, 0.033)]
    g = A['grip']
    parts.append(T.entro(presa_bordo(wr2, g, A['bordo'], A['dentro']), np.minimum(wr2, g) - 0.2, np.maximum(wr2, g) + 0.2))
    for s, pts in A['rays']:
        f, _ = T.tubo(pts, 0.026, 0.0075, n=6, nodi=0.18)
        parts.append(f)
    f = sdf.union(*parts, k=0.022)

    def ribs(p):
        """Pieghe della pelle sulle costole, sui fianchi (come nella tavola)."""
        side = D.smooth01(np.abs(p[:, 0]), 0.05, 0.10) * (1 - D.smooth01(np.abs(p[:, 0]), 0.14, 0.17))
        band = D.smooth01(p[:, 1], -0.28, -0.20) * (1 - D.smooth01(p[:, 1], 0.18, 0.26)) * D.smooth01(p[:, 2], 0.84, 0.88)
        return (np.sin(p[:, 1] * 60.0) * 0.5 + 0.5) * side * band
    return sdf.displace(f, ribs, -0.003)


def zona_tubo(pts, r, piano=None):
    """Zona attorno a una spezzata (capsule di raggio r); con piano = (c, n), solo dalla parte di n."""
    z = sdf.union(*[sdf.capsule(a, b, r) for a, b in zip(pts[:-1], pts[1:])])
    if piano is not None:
        z = sdf.intersect(z, D.above(*piano))
    return z


def pezzi_pelle(f, A):
    """Il campo della pelle tagliato in quattro mesh che combaciano (stesso campo, zone disgiunte): la testa dal
    collo in avanti, il braccio lungo dal primo segmento fino alla mano, l'avambraccio con la mano sul bordo, e
    il resto (RobinSkin). Così testa e dita si fanno fini senza una griglia enorme. [(nome, campo, lo, hi, res)]"""
    sh, e1, e2, wr = A['lungo']
    fist = A['fist']
    c1 = sh + (e1 - sh) * 0.55
    arm_pts = [c1, e1, e2, wr, fist, fist + V(0, 0, -0.06)]
    zA = zona_tubo(arm_pts, 0.10, (c1, e1 - sh))
    sh2, el2, wr2 = A['altro']
    g, dn = A['grip'], A['dentro']
    c2 = el2 + (wr2 - el2) * 0.35
    grip_pts = [c2, wr2, g + V(0, 0, 0.03), g + dn * 0.07 + V(0, 0, -0.16)]
    zG = sdf.subtract(zona_tubo(grip_pts, 0.09, (c2, wr2 - el2)), zA)
    zH = sdf.subtract(sdf.intersect(sdf.sphere(HEAD, 0.27), D.above(V(0, -0.33, 0), (0, -1, 0))), sdf.union(zA, zG))
    out = []
    for name, z, pts, r, res in (('RobinHead', zH, [HEAD], 0.28, RES_HEAD), ('RobinArm', zA, arm_pts, 0.11, RES_HAND),
                                 ('RobinGrip', zG, grip_pts, 0.10, RES_HAND)):
        P = np.array(pts, F)
        out.append((name, sdf.intersect(f, z), P.min(0) - r, P.max(0) + r, res))
    pts = [V(*p) for p in (*A['lungo'][:2], *A['altro'], A['grip'])] + [q for _, r in A['rays'] for q in r]
    pts += [V(-0.2, -0.40, 0.70), V(0.2, 0.80, 0.0)]
    lo = np.min(pts, axis=0) - 0.09
    hi = np.max(pts, axis=0) + 0.09
    lo[2] = -0.05                     # sotto il mare non serve: nel gioco il mare fa da maschera
    out.append(('RobinSkin', sdf.subtract(f, sdf.union(zA, zG, zH)), lo, hi, RES_BODY))
    return out


def attributi(fr, A):
    """Gli attributi del colore (come nella tavola): 'ventre' (la pancia rosata sotto il busto e sotto la testa)
    e 'seconda' (le zampe-raggio, rosse alla base e turchesi per il resto)."""
    from scipy.spatial import cKDTree
    P, Tt = [], []
    for _, pts in A['rays']:
        c = catmull(pts, 14)
        P.append(c)
        Tt.append(np.linspace(0.0, 1.0, len(c)))
    P, Tt = np.concatenate(P).astype(F), np.concatenate(Tt).astype(F)
    tree = cKDTree(P)

    def ventre(p):
        v = np.full(len(p), 0.35, F)
        torso = (np.abs(p[:, 0]) < 0.18) & (p[:, 1] > -0.44) & (p[:, 1] < 0.34) & (p[:, 2] > 0.72) & (p[:, 2] < 1.08)
        v[torso] = D.smooth01(1.02 - p[torso, 2], 0.0, 0.20)
        q = (p - fr.pos) @ fr.R
        near = np.linalg.norm(q, axis=1) < 0.20
        vh = D.smooth01(-q[:, 2], -0.07, 0.07) * 0.85 + 0.05
        v[near] = vh[near]
        return v

    def seconda(p):
        d, i = tree.query(p, k=1, workers=-1)
        return ((1.0 - D.smooth01(d.astype(F), 0.034, 0.05)) * D.smooth01(Tt[i], 0.03, 0.13)).astype(F)
    return {'ventre': ventre, 'seconda': seconda}


def ventagli():
    """Le pettorali a ventaglio della tavola (teste_robin.ventagli), girate all'indietro di VENTAGLI_YAW attorno
    alla loro base: nella tavola le braccia andavano avanti, qui partono di lato e le avrebbero bucate."""
    from mathutils import Matrix
    obs = T.ventagli()
    for o in obs:
        xs = np.empty(len(o.data.vertices) * 3, F)
        o.data.vertices.foreach_get('co', xs)
        s = 1 if xs[0::3].mean() > 0 else -1                # da che parte sta (i nomi possono avere .001)
        b = (s * 0.11, -0.31, 0.93)
        o.matrix_world = (Matrix.Translation(b) @ Matrix.Rotation(math.radians(s * VENTAGLI_YAW), 4, 'Z')
                          @ Matrix.Translation(tuple(-v for v in b)) @ o.matrix_world)
    return obs


# ───────────────────────── i biglietti ─────────────────────────

TICKET = 0.052          # lunghezza di un biglietto lungo la striscia (larga 3,4 cm)


def biglietto_texture(path):
    """Un biglietto della sala giochi, che si ripete lungo la striscia: carta arancio saturo, la cornice e le
    scritte rosso scuro (SPLASHLAND, 1 TICKET, il numero), i forellini della perforazione ai due capi.
    x lungo la striscia, y di traverso."""
    W, H = 640, 370
    im = Image.new('RGB', (W, H), (246, 118, 14))
    d = ImageDraw.Draw(im)
    ink = (128, 20, 8)
    try:
        big = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 88)
        mid = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 64)
        small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
    except OSError:
        big = mid = small = ImageFont.load_default()
    d.rectangle((34, 22, W - 34, H - 22), outline=ink, width=9)
    d.rectangle((52, 40, W - 52, H - 40), outline=ink, width=3)
    for txt, font, y in (('SPLASHLAND', big, 66), ('1 TICKET', mid, 178)):
        w = d.textlength(txt, font=font)
        d.text(((W - w) / 2, y), txt, fill=ink, font=font)
    d.text((76, 270), 'Nº 040217', fill=ink, font=small)
    w = d.textlength('★ ★ ★', font=small)
    d.text((W - 76 - w, 270), '★ ★ ★', fill=ink, font=small)
    # la perforazione: forellini lungo i due lati corti (tra un biglietto e l'altro)
    for x in (0, W):
        for y in np.linspace(14, H - 14, 9):
            d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(70, 16, 6))
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    im.save(path)
    return path


def biglietti_material():
    """La striscia di biglietti: la stampa del biglietto ripetuta (attributi 'tick', metri lungo la striscia, e
    'side', −1..1 di traverso), carta fradicia e lucida d'acqua, macchie d'alga e di sporco che la scuriscono
    senza sbiadirla: deve restare arancio saturo anche sotto la lampara."""
    m = bpy.data.materials.get('TicketsOrange')
    if m:
        return m
    path = biglietto_texture(os.path.join(CACHE, 'robin_biglietto.png'))
    m, g = material('TicketsOrange')
    co = g.texcoord('Object')
    u = g.math('FRACT', g.div(g.attr('tick'), TICKET))
    v = g.mul(g.add(g.attr('side'), 1.0), 0.5)
    col, _ = g.image(path, g.comb(u, v, 0.0), extension='REPEAT')
    # poche macchie d'alga, piccole: scuriscono a chiazze senza spegnere l'arancio
    st = g.noise(co, scale=9.0, detail=5.0, rough=0.6)
    col = g.mix(g.mul(g.smoothstep(0.62, 0.76, st.fac), 0.45), col, (0.16, 0.10, 0.02))
    wet = g.noise(co, scale=6.0, detail=3.0)
    bump = g.bump(g.mul(st.fac, 0.3), strength=0.2, distance=0.001)
    g.output_material(g.principled(color=col, rough=g.map_range(wet.fac, 0.3, 0.7, 0.55, 0.25), coat=0.35, coat_rough=0.12,
                                   normal=bump))
    return m


def spire(pts, r0, r1, giri, fase=0.0, t0=0.07, t1=0.90, gioco=0.0045, n_per_giro=28):
    """Le spire della striscia attorno a un segmento di braccio (la curva 'pts' col raggio da r0 a r1, come lo
    modella corpo()), dal tratto t0 al tratto t1 della lunghezza: la striscia resta stesa sulla pelle, a 'gioco'
    di distanza anche dove il braccio si incurva e si assottiglia. Punti e direzioni della larghezza del nastro,
    come teste_robin.elica (che invece gira attorno alla corda dritta, a raggio fisso)."""
    C = catmull([V(*p) for p in pts], 24)
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))])
    n = max(8, int(giri * n_per_giro))
    ss = np.linspace(t0, t1, n + 1) * s[-1]
    P = np.stack([np.interp(ss, s, C[:, k]) for k in range(3)], axis=1).astype(F)
    Tg = np.gradient(P, axis=0)
    Tg /= np.linalg.norm(Tg, axis=1, keepdims=True)
    u = unit(np.cross(Tg[0], V(0.3, 0.2, 1.0)))
    L = ss[-1] - ss[0]
    out_p, out_w = [], []
    for i in range(n + 1):
        u = unit(u - (u @ Tg[i]) * Tg[i])                # la base si trasporta lungo la curva
        v = np.cross(Tg[i], u)
        th = fase + 2 * math.pi * giri * i / n
        r = r0 + (r1 - r0) * ss[i] / s[-1] + gioco
        rad = math.cos(th) * u + math.sin(th) * v
        tg = unit(Tg[i] * L + (-math.sin(th) * u + math.cos(th) * v) * (2 * math.pi * giri * r))
        out_p.append(P[i] + rad * r)
        out_w.append(unit(np.cross(rad, tg)))
    return np.array(out_p, F), np.array(out_w, F)


def biglietti(A, P):
    """La striscia: il capo libero pende nel secchio, poi le spire attorno al braccio che ruba (dal polso alla
    spalla, gomito dopo gomito), un'ansa sotto il collo, le spire attorno all'altro braccio, e il resto che
    scavalca il capodibanda accanto alla mano e scende lungo la fiancata di dentro."""
    sh, e1, e2, wr = A['lungo']
    sh2, el2, wr2 = A['altro']
    bk = V(*P['bucket'])
    C = curve_braccia(A)
    out_P, out_W = [], []

    def add(p, w):
        out_P.append(p)
        out_W.append(w)

    # il braccio lungo dal polso alla spalla: i segmenti al contrario, ognuno con le sue spire
    segs = [(pts[::-1], r1, r0) for pts, r0, r1 in reversed(C['lungo'])]
    eliche = [spire(p, r0, r1, giri, fase=0.4 + 1.3 * i) for i, ((p, r0, r1), giri) in enumerate(zip(segs, (5.5, 5.0, 4.0)))]
    knots = [e2, e1]
    # il capo libero: dal fondo del secchio sale sopra il bordo e arriva al polso
    h0, w0 = eliche[0]
    tip = bk + orizz(A['fist'] - bk) * 0.05 + V(0, 0, -0.14)
    side = unit(np.cross(V(0, 0, 1), A['a']))
    p0, pw0 = T.libero([tip, bk + orizz(A['fist'] - bk) * 0.10 + V(0, 0, -0.02), wr + V(0, 0, -0.05), h0[0]], side, n=6)
    add(p0[:-1], pw0[:-1])
    for i, (h, w) in enumerate(eliche):
        add(h, w)
        if i + 1 < len(eliche):
            nxt = eliche[i + 1][0]
            j, jw = T.libero([h[-1], knots[i] + V(0, 0, 0.045), nxt[0]], w[-1], n=4)
            add(j[1:-1], jw[1:-1])
    # l'ansa sotto il collo, da una spalla all'altra
    (pu, ru0, ru1), (pf, rf0, rf1) = C['altro']
    h3, w3 = spire(pu, ru0, ru1, 3.5, fase=2.0, t0=0.22, t1=0.92)
    hl, wl = eliche[-1]
    p3, pw3 = T.libero([hl[-1], V(0.10, -0.40, 0.77), V(0.0, -0.45, 0.73), V(-0.10, -0.42, 0.77), h3[0]], wl[-1], n=8, torsione=1.2)
    add(p3[1:-1], pw3[1:-1])
    add(h3, w3)
    h4, w4 = spire(pf, rf0, rf1, 4.5, fase=0.5, t0=0.10, t1=0.88)
    j, jw = T.libero([h3[-1], el2 + V(0, 0, 0.05), h4[0]], w3[-1], n=4)
    add(j[1:-1], jw[1:-1])
    add(h4, w4)
    # il resto: passa sopra il capodibanda accanto alla mano e ricade fuori bordo, fino in mare (dentro, lungo la
    # fiancata, avrebbe toccato le ordinate)
    e = h4[-1]
    lg, dn = A['bordo'], A['dentro']
    g = A['grip']
    rest = [e, g + lg * 0.10 + V(0, 0, 0.026), g + lg * 0.12 - dn * 0.05 + V(0, 0, 0.012), g + lg * 0.13 - dn * 0.075 + V(0, 0, -0.06),
            g + lg * 0.11 - dn * 0.09 + V(0, 0, -0.30), g + lg * 0.16 - dn * 0.12 + V(0, 0, -0.62), g + lg * 0.12 - dn * 0.16 + V(0, 0, -0.80)]
    p5, w5 = T.libero(rest, w4[-1], n=8, torsione=2.0)
    add(p5[1:], w5[1:])
    ob = T.nastro('Tickets', np.concatenate(out_P), np.concatenate(out_W), larghezza=0.034)
    ob.data.materials[0] = biglietti_material()
    return [ob]


# ───────────────────────── il pesce rubato e la melma ─────────────────────────

def giu_pesce(A, P):
    """Il verso del pesce rubato, dalla coda alla testa: pende, piegato appena verso il centro del secchio."""
    return unit(V(0, 0, -1) + orizz(V(*P['bucket']) - A['fist']) * 0.25)


def pesce_rubato(A, P):
    """Il pesce appena tirato fuori dal secchio, preso per la coda: pende a testa in giù sopra la bocca del
    secchio, col fianco verso il pescatore. Ha la pelle dei pesci del secchio (boat.fish_material), argentata a
    bande: quella della tavola, scura, contro il secchio non si vedeva. Gli occhi del pesce si rinominano: il
    gioco fa brillare al buio gli oggetti che hanno 'Eye' nel nome."""
    import boat
    fist = A['fist']
    giu = giu_pesce(A, P)
    view = orizz(V(*P['viewer']) - fist)
    dorso = unit(np.cross(view, V(0, 0, 1)))
    obs = T.pesce('StolenFish', fist + V(0, 0, 0.045), giu, L=PESCE_L, dorso=tuple(dorso))
    obs[0].data.materials[0] = boat.fish_material()
    for o in obs:
        o.name = o.name.replace('Eye', 'Occhio')
    return obs


def melma(A, P, pesce=True):
    """Melma vera (rossa): gocce dalle dita e dal pesce, una pozza sul capodibanda sotto la pancia, colature
    che pendono dallo spigolo di dentro del bordo."""
    rng = np.random.default_rng(21)
    fili, gocce = [], []
    for _, pts in A['rays']:
        if rng.random() < 0.6:
            gocce.append((pts[-2] + V(0, 0, -0.012), rng.uniform(0.02, 0.05)))
    fist = A['fist']
    gocce.append((fist + V(0.0, 0.0, -0.035) + A['a'] * 0.02, 0.05))
    if pesce:                                            # dalla bocca del pesce, che pende un po' storto
        gocce.append((fist + V(0, 0, 0.045) + giu_pesce(A, P) * (PESCE_L * 0.99), 0.04))
    g, lg, dn = A['grip'], A['bordo'], A['dentro']
    for dx in (-0.045, 0.0, 0.04):
        gocce.append((g + lg * dx * 1.25 + dn * 0.088 + V(0, 0, -0.15), rng.uniform(0.02, 0.04)))
    # sotto la pancia: colature dallo spigolo di dentro del capodibanda
    c = V(0, 0, GUN)
    for t in (-0.10, -0.03, 0.06):
        gocce.append((c + lg * t + dn * 0.046 + V(0, 0, -0.012), rng.uniform(0.04, 0.09)))
    obs = [T.bava('RobinSlimeDrops', fili=fili, gocce=gocce)]
    pool = D.ellipsoid_rot(c + V(0, 0, 0.0005), (0.16, 0.034, 0.0025), np.stack([lg, dn, V(0, 0, 1)], axis=1).astype(F))
    obs.append(T.fine('RobinSlimePool', pool, [np.array([c - 0.18, c + 0.18], F)], T.melma_rossa(), pad=0.02, res=0.0012))
    return obs


# ───────────────────────── costruzione ─────────────────────────

def build(viewer=None, bucket=None, reach=None, feet=None, grip=None, lungo=None, fish=True):
    """Robin nella posa del secchio, in coordinate locali. viewer: dove guardano gli occhi e verso cui si gira la
    testa; bucket: il centro della bocca del secchio; reach: dove la mano stringe il pesce; feet: le punte
    delle sei zampe (tre per lato: davanti, in mezzo, dietro; prima il lato −X); grip: dove l'altra mano si
    aggrappa al capodibanda; lungo: la direzione del capodibanda (orizzontale). fish=False: la mano senza il
    pesce. Gli occhi sono gli oggetti 'RobinEye0' e 'RobinEye1'."""
    P = dict(POSA)
    for k, v in (('viewer', viewer), ('bucket', bucket), ('reach', reach), ('feet', feet), ('grip', grip), ('lungo', lungo)):
        if v is not None:
            P[k] = v
    A = pose_arti(P)
    vw = V(*P['viewer'])
    # la testa si gira verso il pescatore (gli occhi fanno il resto) e alza la faccia verso di lui
    d = vw - HEAD
    turn = max(-45.0, min(45.0, math.degrees(math.atan2(float(d[0]), float(-d[1])))))
    elev = math.degrees(math.atan2(float(d[2]), float(np.hypot(d[0], d[1]))))
    pitch = -max(-5.0, min(22.0, elev * 0.85))
    fr, hf, cut, attrs, obs = testa(turn, pitch, vw)
    obs.append(baffi(fr, V(*P['bucket']) - HEAD))
    f = sdf.subtract(corpo(hf, A), sdf.union(T.gills(), cut), k=0.005)
    a = attributi(fr, A)
    a.update(attrs)
    skin_m = T.pelle_robin()
    for name, fld, lo, hi, res in pezzi_pelle(f, A):
        ob = sdf_object(name, fld, lo, hi, res=res, attrs=a, banded=True)
        ob.data.materials.append(skin_m)
        obs.insert(0, ob)
    obs += ventagli()
    obs += biglietti(A, P)
    if fish:
        obs += pesce_rubato(A, P)
    obs += melma(A, P, pesce=fish)
    return obs


# ───────────────────────── vetrina ─────────────────────────

def _set_barca():
    """Il pezzo di barca attorno a Robin, nelle coordinate del gioco: scafo, capodibanda, ordinate, banchi, il
    telone e i remi, il secchio coi pesci. Niente bambola e niente batteria: qui conta Robin."""
    import boat
    mats = boat.make_materials()
    obs = [boat.build_hull(mats)] + boat.build_structure(mats) + boat.build_tarp(mats) + boat.build_bucket(mats, 5)
    obs += boat.build_props(mats)
    # il mare un filo più basso del vero: a z = 0 passerebbe dentro la barca, sopra il pagliolo
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.13))
    sea = bpy.context.object
    sea.data.materials.append(D.mat_simple('NightSea', (0.004, 0.012, 0.016), rough=0.06, spec=0.8))
    return obs


SHOTS = {
    # (riferimento, camera, bersaglio, lente): camera e bersaglio rispetto alla testa o al pugno, nelle
    # coordinate della barca
    'insieme': ('testa', (1.20, -1.00, 0.55), (0.36, 0.36, -0.06), 22),
    'testa': ('testa', (0.50, -0.46, 0.16), (0.0, 0.0, -0.03), 50),
    'mano': ('pugno', (-0.38, -0.52, 0.16), (0.0, 0.0, -0.08), 45),
    'fuori': ('testa', (-1.70, -0.55, 0.62), (-0.34, 0.30, -0.16), 26),
}


def scena_vetrina():
    """La scena della vetrina: Robin nella posa di gioco sul capodibanda (scena_creature.robin_posa), in un pezzo
    di barca, con le luci di studio delle altre vetrine: la lanterna calda davanti e in basso, la luna fredda
    da dietro, la lampara da prua sul braccio, poco riempimento; resa AgX. Restituisce i riferimenti delle
    inquadrature (testa e pugno, nelle coordinate della barca)."""
    from mathutils import Vector
    import scena_creature as SC
    sc = reset_scene()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.cycles.use_denoising = True
    w = bpy.data.worlds.new('Night')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.010, 0.014, 0.022, 1)
    _set_barca()
    M, kw = SC.robin_posa()
    SC.place(build(**kw), M)
    h = np.array(M @ Vector(tuple(map(float, HEAD))))
    p = np.array(M @ Vector(tuple(map(float, kw['reach']))))
    D.area_light('Key', tuple(h + (0.30, -1.10, -0.35)), tuple(h), 40, (1.0, 0.72, 0.44), 0.4)
    D.area_light('Rim', tuple(h + (-0.60, 1.40, 1.50)), tuple(h + (0.2, 0.1, 0.0)), 130, (0.55, 0.72, 1.0), 0.6)
    D.area_light('Bow', (0.0, 2.6, 1.6), tuple((h + p) / 2), 60, (1.0, 0.80, 0.55), 0.5)
    D.area_light('Fill', tuple(h + (1.40, -1.20, 0.70)), tuple(h), 10, (0.55, 0.65, 0.85), 1.6)
    return {'testa': h, 'pugno': p}


def showcase(shots=('insieme', 'testa', 'mano', 'fuori')):
    """La vetrina: tools/render/cache/vetrina/robin_<inquadratura>.png."""
    from mathutils import Vector
    out = []
    ref = scena_vetrina()
    sc = bpy.context.scene
    cam_d = bpy.data.cameras.new('Cam')
    cam_d.sensor_width = 36.0
    cam_d.clip_start = 0.02
    cam = bpy.data.objects.new('Cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    W, H = (720, 540) if FAST else (1440, 1080)
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.cycles.samples = 32 if FAST else 160
    sc.render.image_settings.file_format = 'PNG'
    os.makedirs(os.path.join(CACHE, 'vetrina'), exist_ok=True)
    for name in shots:
        r, cl, ct, lens = SHOTS[name]
        c0 = ref[r]
        cam_d.lens = lens
        cam.location = tuple(c0 + cl)
        cam.rotation_mode = 'QUATERNION'
        cam.rotation_quaternion = (Vector(tuple(c0 + ct)) - Vector(tuple(c0 + cl))).to_track_quat('-Z', 'Y')
        path = os.path.join(CACHE, 'vetrina', f'robin_{name}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('ok', path, flush=True)
    return out


# ───────────────────────── la posa nella scena del gioco ─────────────────────────

def _angoli(pts):
    """Yaw e pitch (gradi) dei punti visti dall'occhio: yaw positivo a destra, come nel gioco."""
    d = np.atleast_2d(np.asarray(pts, float)) - np.array(EYE)
    return np.degrees(np.arctan2(d[:, 0], d[:, 1])), np.degrees(np.arctan2(d[:, 2], np.hypot(d[:, 0], d[:, 1])))


def _span(pts):
    y, p = _angoli(pts)
    return {'yaw': [round(float(y.min()), 1), round(float(y.max()), 1)], 'pitch': [round(float(p.min()), 1), round(float(p.max()), 1)]}


def _dir(p):
    y, pt = _angoli([tuple(p)])
    return [round(float(y[0]), 1), round(float(pt[0]), 1)]


def ingombro(obs):
    """Dove sta la posa vista dall'occhio del pescatore (per la regia del gioco): yaw e pitch minimi e massimi di
    tutti i pezzi ('tutto') e della parte che si vede davvero ('visibile': senza quello che lo scafo e il mare
    nascondono, cioè la coda in acqua e le zampe sulla fiancata di fuori), dei pezzi principali, e dove stanno
    la testa e gli occhi (gradi, e metri dall'occhio)."""
    import jobs
    from mathutils import Vector
    meshes = [o for o in obs if o.type == 'MESH']
    pts = np.array(jobs.dense_points(meshes, n=2500))
    # visibile: il primo oggetto che il raggio dall'occhio incontra è Robin stesso (si parte 15 cm avanti,
    # fuori dal corpo invisibile del pescatore, che fa solo ombra)
    dg = bpy.context.evaluated_depsgraph_get()
    sc = bpy.context.scene
    nomi = {o.name for o in meshes}
    eye = np.array(EYE)
    vis = []
    for p in pts:
        d = p - eye
        L = float(np.linalg.norm(d))
        d /= L
        hit, _, _, _, ob, _ = sc.ray_cast(dg, Vector(tuple(eye + d * 0.15)), Vector(tuple(d)), distance=L - 0.15 - 0.003)
        vis.append((not hit) or (ob is not None and ob.name in nomi))
    vis = np.array(vis)
    head = bpy.data.objects['RobinSkin'].matrix_world @ Vector(tuple(map(float, HEAD)))
    eyes = [o for o in meshes if 'Eye' in o.name]
    out = {
        'tutto': _span(pts),
        'visibile': _span(pts[vis]),
        'testa': _dir(head),
        'testa_m': [round(float(head[i] - EYE[i]), 3) for i in range(3)],
        'distanza_testa': round(float(math.dist(tuple(head), EYE)), 2),
        'occhi': [_dir(o.matrix_world.translation) for o in eyes],
        'occhi_m': [[round(float(o.matrix_world.translation[i] - EYE[i]), 4) for i in range(3)] for o in eyes],
    }
    for k, n in (('testa_mesh', 'RobinHead'), ('braccio', 'RobinArm'), ('mano_bordo', 'RobinGrip'), ('corpo', 'RobinSkin'),
                 ('biglietti', 'Tickets'), ('pesce', 'StolenFish')):
        o = bpy.data.objects.get(n)
        if o:
            out[k] = _span(jobs.dense_points([o], n=2500))
    # quanto resta lontano dalla mano di Gulpy sul capodibanda di sinistra (gulpy_pretende, y = 1,2)
    import scena_creature as SC
    xg, zg = SC.gunwale_at(1.2, -1)
    out['da_gulpy_m'] = round(float(np.min(np.linalg.norm(pts - np.array((xg + 0.02, 1.2, zg)), axis=1))), 2)
    out['gulpy_mano'] = _dir((xg + 0.02, 1.2, zg))
    return out


def anteprima_posa():
    """Anteprima della posa robin_secchio senza toccare il gioco (come batteria.preview): la scena del gioco,
    la batteria della notte 2, la posa da scena_creature, e la camera prospettica dall'occhio del pescatore
    come la vista del gioco (90° di campo, guardando un po' a sinistra della prua) e una più stretta sul mostro.
    Scrive docs/concept/pose_robin.jpg e pose_robin_vicino.jpg, e l'ingombro in cache/robin_posa.json."""
    import batteria
    import jobs
    import scena_creature as SC
    from common import perspective_camera
    jobs.build_scene(fish=5, rod=True)
    batteria.build_battery(needle=0.72)
    before = set(bpy.data.objects.keys())
    SC.POSES['robin_secchio'][0]()
    bpy.context.view_layer.update()
    new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
    info = ingombro(new)
    print('ingombro', json.dumps(info), flush=True)
    with open(os.path.join(CACHE, 'robin_posa.json'), 'w') as fh:
        json.dump(info, fh, indent=1)
    sc = bpy.context.scene
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.resolution_percentage = 100
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.cycles.samples = 32 if FAST else 64
    out = []
    # la vista del gioco (90° di campo, 16:9) girata un po' a sinistra della prua: dentro ci sono la faccia e il
    # secchio; poi una più stretta sul mostro. Con --fast le mesh sono grossolane e i campioni pochi
    for name, (yaw, pitch, lens) in {
        'pose_robin': (-12.0, -12.0, 18.0),
        'pose_robin_vicino': (-31.0, -11.0, 32.0),
    }.items():
        t = (EYE[0] + math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)),
             EYE[1] + math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)), EYE[2] + math.sin(math.radians(pitch)))
        perspective_camera(EYE, t, lens=lens, name='RobinCam_' + name)
        path = os.path.join(CACHE, f'{name}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        dst = os.path.join(ROOT, 'docs', 'concept', f'{name}.jpg')
        Image.open(path).convert('RGB').save(dst, quality=90)
        out.append(dst)
        print('anteprima', dst, flush=True)
    return out, info


if __name__ == '__main__':
    if '--posa' in sys.argv:
        anteprima_posa()
    else:
        showcase()
