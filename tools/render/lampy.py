"""
LAMPY — modello definitivo (sagoma C «Sanguisuga», testa B «Bacio»), notte 4. In bozza: da approvare.

Un arco di carne attaccato alla lenza per i due capi, come una sanguisuga che cammina: la bocca tiene la lenza in
alto, dalla parte della canna, la ventosa della coda la tiene più in basso, a un palmo dal pelo dell'acqua; in mezzo
il corpo grosso e pesante sale ad arco sopra il filo. Viene dalla lampreda: la bocca è una ventosa piena di anelli
di denti, sette pori branchiali per lato dietro la testa, due pinne basse sul dorso verso la coda, il corpo d'anguilla
ad anelli. Da bambina in piscina tirava giù gli altri per le gambe, per scherzo: le è rimasta in testa la cuffia di
gomma a fiori. Ora tira la lenza.

La testa è la B «Bacio» della tavola (teste_lampy.lampy_b) rifinita: il cranio da neonato sotto la cuffia, gli occhi
tondi senza palpebre, al posto del naso due fessure; la ventosa è una bocca enorme a bacio con gli anelli di denti da
latte. Rispetto alla tavola l'orlo della cuffia passa sopra la nuca (il collo esce da sotto, come da una cuffia vera),
i fiori stanno in poche mesh, la bocca si apre e si chiude e gli anelli di denti girano. Il corpo è quello della
tavola, un po' più grosso. Colori approvati (10 ottobre), quelli della tavola: viola-magenta, più scuro sul dorso,
rosato sul ventre e sulle labbra; la cuffia bianca coi fiori fucsia e rosa.

Coordinate: il mare è z = 0. La lenza passa per BOCCA (dove le entra in bocca, in alto a sinistra) e per CODA (dove
la tiene la ventosa della coda, in basso a destra), nel piano y = 0; il pescatore sta verso −Y, la faccia lo guarda
e la testa e l'arco stanno dietro la lenza (y > 0). Nel gioco la posa si ricalcola dalla barca
(scena_creature.lampy_posa): il pescatore arriva come parametro; senza parametri build() rifà la posa di gioco
(POSA, numeri arrotondati). La lenza non fa parte del modello: nel gioco la disegna il motore, dalla punta della
canna alla bocca, poi alla ventosa della coda, poi in mare (scena_creature.lampy_lenza_punti).

Le parti che si muovono, per le toppe del gioco (come palpebre e aggrotta di robin.build): build(bocca=…) apre e
chiude la ventosa, da 0 (chiusa a bacio stretto sulla lenza) a 1 (spalancata a disco, con gli anelli di denti in
vista); BOCCA_RIPOSO è quella della posa, come nella tavola. build(denti=…) gira gli anelli di denti (gradi: gli anelli
vicini girano in versi opposti, come una macina). Cambiano solo la testa ('LampyHead'), i denti, la gola e la bava
della bocca: il corpo resta lo stesso, oggetto per oggetto.

Uso: tools/.venv/bin/python tools/render/lampy.py [--fast]          vetrina → docs/concept/lampy_vetrina.jpg
     tools/.venv/bin/python tools/render/lampy.py [--fast] --posa   la posa di gioco nella scena della barca, vista
                                                                    dall'occhio → docs/concept/pose_lampy*.jpg
     tools/.venv/bin/python tools/render/lampy.py --vetrina-tavola  rimonta la tavola della vetrina dai pannelli
     tools/.venv/bin/python tools/render/lampy.py --posa-tavole     rimonta le anteprime della posa dai pannelli
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import dettagli as D  # noqa: E402
import sdf  # noqa: E402
import skin  # noqa: E402
import teste_lampy as TL  # noqa: E402  (la bozza: pelle, gomma della cuffia, bava, aiuti)
from common import CACHE, EYE, ROOT, reset_scene  # noqa: E402
from creature import eyeball, sdf_object, teeth_material  # noqa: E402
from geo import catmull, rbox, tube  # noqa: E402

V, F, unit, chain = D.V, D.F, D.unit, D.chain
FAST = '--fast' in sys.argv
# la pelle è un campo solo (corpo e testa) tagliato in due mesh a risoluzioni diverse, che combaciano. Nel gioco
# Lampy sta a sei metri dall'occhio: lì un pixel del panorama è mezzo centimetro
RES_BODY = 0.005 if FAST else 0.0032      # il corpo
RES_HEAD = 0.0032 if FAST else 0.0020     # la testa con la bocca
RES_FINE = 0.0022 if FAST else 0.0013     # i pezzi piccoli (fiori, denti)

# ───────────────────────── la lenza e la testa ─────────────────────────

BOCCA = V(-0.62, 0.0, 1.02)               # dove la lenza entra in bocca
CODA = V(0.56, 0.0, 0.20)                 # dove la tiene la ventosa della coda
ACQUA = V(0.80, 0.30, -0.02)              # dove, dopo la coda, il filo entra in mare (verso il galleggiante)
# nel sistema locale della testa (faccia −Y, alto +Z), come teste_lampy.lampy_b:
Q_BOCCA = V(0.0, -0.325, -0.115)          # dove la lenza entra in bocca (sull'asse della bocca, che è −Y)
CRANIO = (V(0.0, 0.03, 0.05), (0.28, 0.28, 0.29))
OCCHI = [V(s * 0.10, -0.242, 0.082) for s in (-1, 1)]
R_OCCHIO = 0.036
NUCA = [V(0.08, 0.06, -0.08), V(0.30, 0.22, -0.04)]   # il collo esce da dietro a destra, sotto l'orlo della cuffia
# l'orlo della cuffia: davanti sopra l'arcata come nella tavola, dietro sopra la nuca (due piani, raccordati)
CAP_FRONTE = (V(0.0, -0.10, 0.0), V(0.0, 1.0, 0.75))
CAP_NUCA = (V(0.0, 0.20, 0.0), V(0.0, -0.45, 1.0))
BOCCA_RIPOSO = 0.5                        # l'apertura della ventosa nella posa (come nella tavola)
K_TESTA = 1.15                            # la testa più grande che nella tavola: il corpo è più grosso, e la faccia
                                          # deve restare quello che si legge per primo

# la posa di gioco (scena_creature.lampy_posa) in coordinate locali, arrotondata: è quella che build() fa senza
# parametri. Nel gioco i numeri si ricalcolano dalla barca.
POSA = {
    'viewer': (-1.97, -5.04, 1.09),
}


class Testa(D.Frame):
    """Sistema locale della testa (faccia −Y, alto +Z) con la faccia in una direzione qualsiasi, dritta, e
    ingrandita di S rispetto alle misure della tavola (come teste_fangy.Head)."""

    def __init__(self, face, S):
        y = -unit(face)
        z = unit(V(0, 0, 1) - (V(0, 0, 1) @ y) * y)
        self.R = np.stack([np.cross(y, z), y, z], axis=1).astype(F)
        self.S = float(S)
        self.pos = V(0, 0, 0)

    def field(self, f):
        R, c, S = self.R, self.pos, self.S
        return lambda p: f(((p - c) @ R) / S) * S

    def pt(self, q):
        return self.pos + self.R @ (V(*q) * self.S)

    def local(self, p):
        return ((p - self.pos) @ self.R) / self.S


def testa_frame(viewer):
    """Il sistema della testa: la faccia verso il pescatore (girata di ±40° al massimo da −Y e alzata o abbassata
    di 15°), dritta, grande K_TESTA, con la bocca esattamente sulla lenza in BOCCA."""
    d = V(*viewer) - BOCCA
    yaw = max(-40.0, min(40.0, math.degrees(math.atan2(float(d[0]), float(-d[1])))))
    pitch = max(-15.0, min(15.0, math.degrees(math.atan2(float(d[2]), float(np.hypot(d[0], d[1]))))))
    y, p = math.radians(yaw), math.radians(pitch)
    fr = Testa(V(math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)), K_TESTA)
    fr.pos = BOCCA - fr.R @ (Q_BOCCA * fr.S)
    return fr


# ───────────────────────── la ventosa ─────────────────────────

def ventosa(bocca):
    """La bocca a bacio aperta per 'bocca' (0 chiusa, 1 spalancata), nel sistema della testa: un dizionario con il
    centro delle labbra 'c' (spalancandosi scende un poco verso il mento: la lenza resta all'altezza di Q_BOCCA),
    la mezza larghezza 'a' e la mezza altezza 'h' dell'anello delle labbra, lo spessore 'r', le grinzette 'amp', il
    buco ('ha' × 'hv') e gli anelli di denti [(mezza larghezza, mezza altezza, y, n, lunghezza, raggio)].
    A BOCCA_RIPOSO è la bocca della tavola: labbra di raggio 0,098 e spessore 0,044, buco di 6 cm."""
    b = min(max(float(bocca), 0.0), 1.0)
    o = max(0.0, b - 0.5) / 0.5                    # quanto è spalancata oltre il riposo
    k = max(0.0, 0.5 - b) / 0.5                    # quanto è chiusa oltre il riposo
    a = 0.050 + 0.092 * b
    h = a * (0.86 + 0.06 * b)
    r = 0.050 - 0.012 * b
    c = V(0.0, -0.32 + 0.04 * b, -0.115 - 0.022 * o)
    ha = max(a - r, 0.0) * 1.1
    hv = max(h - r, 0.0) * 1.1
    # spalancandosi gli anelli si allargano meno del buco: quello di fuori resta sul bordo di dentro delle labbra e i
    # denti restano fitti (allargati come il buco si sparpagliavano)
    ha0, hv0 = 0.0572, 0.0456                      # il buco a riposo (bocca 0,5)
    hx = ha if o <= 0 else ha0 + (ha - ha0) * 0.65
    hz = hv if o <= 0 else hv0 + (hv - hv0) * 0.65
    anelli = []
    # (frazione del buco, minimo da chiusa, profondità dal piano delle labbra, quanti, lunghezza, raggio)
    for f, rmin, dy, n, L, rt in ((1.10, 0.040, -0.006, 18, 0.018, 0.0078), (0.90, 0.032, 0.012, 15, 0.019, 0.0074),
                                  (0.71, 0.025, 0.032, 12, 0.019, 0.0070), (0.54, 0.019, 0.052, 9, 0.018, 0.0066)):
        rx = max(hx * f, rmin)
        rz = max(hz * f, rmin * 0.9)
        anelli.append((rx, rz, float(c[1] + dy * (1.0 - 0.4 * o) + 0.045 * k), n, L, rt))
    return {'b': b, 'o': o, 'k': k, 'c': c, 'a': a, 'h': h, 'r': r, 'amp': 0.060 - 0.050 * b,
            'ha': max(ha, 0.007), 'hv': max(hv, 0.007), 'anelli': anelli}


def labbra(v, n=18, gonfio=0.3):
    """Le labbra a bacio attorno all'asse −Y: un anello ovale (mezza larghezza a, mezza altezza h) di tubo r, con le
    grinzette verticali e il labbro di sotto più gonfio (come teste_lampy.pucker_lips, ma ovale). Chiusa (a < r)
    l'anello si chiude in un bacio: una palla di labbra grinzose stretta attorno alla lenza."""
    c, a, h, r, amp = v['c'], v['a'], v['h'], v['r'], v['amp']

    def f(p):
        q = p - c
        x, z = q[:, 0], q[:, 2]
        rho = np.sqrt(x * x + z * z)
        e = np.sqrt((x / a) ** 2 + (z / h) ** 2)
        d = rho * (1.0 - 1.0 / np.maximum(e, 1e-4))     # distanza radiale dall'ovale (esatta per i cerchi)
        th = np.arctan2(z, x)
        rr = r * (1 + amp * np.cos(n * th)) * (1 + gonfio * np.clip(-z / (h + r), 0, 1))
        return np.sqrt(d * d + q[:, 1] ** 2) - rr
    return f


def testa_campo(v):
    """La testa B in coordinate locali con la bocca 'v' (ventosa()): il cranio da neonato, la faccia, l'arcata, il
    mento che scende con la bocca spalancata, le labbra. Restituisce il campo e i tagli (il buco della bocca con la
    gola, le orbite, le narici: due fessure che salgono un poco se il labbro di sopra si alza)."""
    c = v['c']
    cran = sdf.ellipsoid(*CRANIO)
    face = sdf.ellipsoid(V(0, -0.10, -0.05), (0.23, 0.19, 0.22))
    brow = sdf.ellipsoid(V(0, -0.246, 0.128), (0.16, 0.032, 0.03))
    chin = sdf.ellipsoid(V(0, -0.15 - 0.04 * v['o'], -0.16 - 0.08 * v['o']), (0.13, 0.10, 0.09))   # a riposo sta dentro la faccia
    head = sdf.union(cran, face, brow, chin, labbra(v), k=0.035)
    sockets = sdf.union(*[sdf.sphere(o - V(0, 0.010, 0), R_OCCHIO + 0.004) for o in OCCHI])
    top = float(c[2]) + v['h'] + v['r']                   # il labbro di sopra
    nz = 0.026 + max(0.0, top - 0.014) * 0.8
    nostrils = sdf.union(*[D.ellipsoid_rot(V(s * 0.016, -0.262, nz), (0.005, 0.012, 0.012), sdf.rot_matrix('y', s * 20))
                           for s in (-1, 1)])
    ha, hv = v['ha'], v['hv']
    hole = sdf.union(sdf.ellipsoid(c + V(0, -0.05, 0), (ha, 0.10, hv)),
                     sdf.capsule(c, V(0, -0.02, -0.06), max(min(ha, hv) * 0.62, 0.006)))
    return head, sdf.union(sockets, nostrils, hole)


def colori_bocca(fr, v):
    """Gli attributi del colore della bocca (mondo): 'mouth' (1 dentro la bocca, meno sulle labbra: rosso livido e
    bagnato) e 'blush' (le labbra rosate)."""
    c, a, h = v['c'], v['a'], v['h']

    def misura(p):
        q = fr.local(p)
        e = np.sqrt((q[:, 0] / a) ** 2 + ((q[:, 2] - c[2]) / h) ** 2)
        front = np.clip((float(c[1]) + 0.05 - q[:, 1]) / 0.03, 0, 1)
        return q, e * a, front

    def mouth(p):
        q, d, front = misura(p)
        inside = np.clip((max(a - v['r'], 0.004) * 1.05 - d) / 0.012, 0, 1) * (q[:, 1] > float(c[1]) - 0.04)
        lip = np.clip(1 - np.abs(d - a) / 0.05, 0, 1) * front * 0.42
        return np.maximum(inside, lip).astype(F)

    def blush(p):
        _, d, front = misura(p)
        return (np.clip(1 - np.abs(d - a) / 0.055, 0, 1) * front).astype(F)
    return mouth, blush


def denti(fr, v, giro, seed=17):
    """Gli anelli di denti da latte dentro la ventosa (come teste_lampy.ring_teeth): dentini bianchi e tondi, un
    po' disuguali, che escono dalla carne puntando in avanti e verso la lenza. giro: di quanti gradi girano gli
    anelli (quelli vicini in versi opposti). Spalancata, i denti si aprono a raggiera e guardano più avanti."""
    rng = np.random.default_rng(seed)
    pairs = []
    inward = 1.1 - 0.4 * v['o']
    for k, (rx, rz, y, n, L, rt) in enumerate(v['anelli']):
        verso = 1.0 if k % 2 == 0 else -1.0
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * (k % 2)) / n + math.radians(giro * verso)
            radial = V(math.cos(a), 0.0, math.sin(a))
            base = V(rx * math.cos(a), y, float(v['c'][2]) + rz * math.sin(a))
            d = unit(V(0, -1, 0) - radial * inward)
            s = rng.uniform(0.85, 1.12)
            pairs.append((fr.pt(base), fr.pt(base + d * L * s), rt * s * fr.S))
    # i dentini da latte hanno la punta tonda: coni corti e grassi
    parts = []
    for b, t, r in pairs:
        parts.append(TL.bounded(sdf.round_cone(b, t, r, r * 0.42), (b + t) / 2, float(np.linalg.norm(t - b)) / 2 + r, margin=0.01))
    pts = np.array([p for b, t, _ in pairs for p in (b, t)], F)
    ob = sdf_object('LampyTeeth', sdf.union(*parts), pts.min(0) - 0.02, pts.max(0) + 0.02, res=RES_FINE, banded=True)
    ob.data.materials.append(teeth_material())
    return ob


def gola(fr, v):
    """Il buio della gola dietro gli anelli di denti: comincia in fondo, dietro l'ultimo anello, ed è di un nero
    opaco (lucido, a bocca spalancata sembrava una palla nera in fondo alla bocca, un occhio)."""
    c = v['c']
    rg = max(min(v['ha'], v['hv']) * 0.56, 0.010)
    a, b = c + V(0, 0.07, 0), V(0, -0.04, -0.06)
    c0 = fr.pt((a + b) / 2)
    m = D.mat_simple('LampyThroatMat', (0.010, 0.002, 0.004), rough=0.85)
    return D.mesh('LampyThroat', fr.field(sdf.capsule(a, b, rg)), c0 - 0.22 * fr.S, c0 + 0.22 * fr.S, m, res=0.004)


# ───────────────────────── la cuffia a fiori ─────────────────────────

def cap_zona():
    """Dove la cuffia copre il cranio (campo locale, < 0 dentro): sopra i due piani dell'orlo, raccordati."""
    return sdf.intersect(D.above(*CAP_FRONTE), D.above(*CAP_NUCA), k=0.04)


def fiori(qs, ns, ss, petali=6):
    """I fiori di gomma in rilievo (petali a raggiera nel piano tangente e il bottone in mezzo, come
    teste_lampy.flower) per tanti fiori in un campo solo: ogni punto guarda solo il fiore più vicino.
    Restituisce il campo dei petali e quello dei bottoni."""
    qs, ns, ss = np.asarray(qs, F), np.asarray(ns, F), np.asarray(ss, F)
    t1 = np.cross(ns, V(0.3, 0.2, 1.0))
    t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
    t2 = np.cross(ns, t1)
    tree = cKDTree(qs)

    def petals(p):
        _, i = tree.query(p, workers=-1)
        q, n, s = qs[i], ns[i], ss[i][:, None]
        out = None
        for k in range(petali):
            ang = 2 * math.pi * k / petali
            dk = t1[i] * math.cos(ang) + t2[i] * math.sin(ang)
            ek = np.cross(n, dk)
            w = p - (q + dk * s * 0.62 + n * s * 0.08)
            ex = np.einsum('ij,ij->i', w, dk) / (s[:, 0] * 0.50)
            ey = np.einsum('ij,ij->i', w, ek) / (s[:, 0] * 0.30)
            ez = np.einsum('ij,ij->i', w, n) / (s[:, 0] * 0.16)
            k0 = np.sqrt(ex * ex + ey * ey + ez * ez)
            k1 = np.sqrt((ex / (s[:, 0] * 0.50)) ** 2 + (ey / (s[:, 0] * 0.30)) ** 2 + (ez / (s[:, 0] * 0.16)) ** 2)
            fk = k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)
            out = fk if out is None else sdf.smin(out, fk, s[:, 0] * 0.08)
        return out.astype(F)

    def buttons(p):
        _, i = tree.query(p, workers=-1)
        return (np.linalg.norm(p - (qs[i] + ns[i] * ss[i][:, None] * 0.16), axis=1) - ss[i] * 0.24).astype(F)
    return petals, buttons


def cuffia(fr, collo=None, n=54, seed=3):
    """La cuffia della tavola (teste_lampy.swim_cap): il guscio di gomma bianca sul cranio con l'orlo arrotolato e
    i fiori fitti in rilievo, fucsia, rosa e rosa chiaro coi bottoni bianchi. L'orlo passa sopra la nuca (cap_zona);
    collo: il campo del collo (mondo), che la cuffia non deve attraversare. I fiori sono quattro mesh:
    'LampyCapFlowers0..2' (un colore ciascuna) e 'LampyCapButtons'."""
    c, rad = CRANIO
    thick = 0.0045
    outer = sdf.ellipsoid(c, tuple(np.array(rad) + 0.007))
    zona = cap_zona()
    body = sdf.intersect(sdf.shell(outer, thick * 0.5), zona)
    # l'orlo arrotolato: una fascia più spessa lungo il bordo
    edge = sdf.intersect(sdf.shell(outer, thick * 1.4), sdf.intersect(zona, lambda p: -0.011 - zona(p)))
    capf = fr.field(sdf.union(body, edge, k=0.002))
    if collo is not None:
        capf = sdf.subtract(capf, lambda p: collo(p) - 0.012, k=0.006)
    wc, S = fr.pos, fr.S
    obs = [TL.skin_mesh('LampyCap', capf, wc - 0.42 * S, wc + 0.42 * S, TL.cap_material(), res=RES_FINE * 1.6)]
    # i fiori: direzioni spalmate sulla sfera (spirale di Fibonacci), solo dove la cuffia copre, un po' disuguali
    rng = np.random.default_rng(seed)
    ga = math.pi * (3 - math.sqrt(5))
    want, sizes, cols = [], [], []
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        d = V(r * math.cos(ga * i), r * math.sin(ga * i), z)
        p = c + d * 0.29
        size, col = float(rng.uniform(0.058, 0.074)), int(rng.integers(0, 3))
        if zona(p[None, :])[0] > -0.035:
            continue
        want.append(fr.pt(c + d * 0.5))
        sizes.append(size)
        cols.append(col)
    surf = fr.field(sdf.ellipsoid(c, tuple(np.array(rad) + 0.007 + thick * 0.5)))
    qs, ns = TL.snap(surf, want)
    if collo is not None:
        lontani = collo(qs) > 0.05
        qs, ns = qs[lontani], ns[lontani]
        sizes, cols = list(np.array(sizes)[lontani]), list(np.array(cols)[lontani])
    sizes, cols = np.array(sizes, F) * S, np.array(cols)
    for ci, (col, nome) in enumerate(TL.FLOWER_COLS):
        m = cols == ci
        if not m.any():
            continue
        pf, _ = fiori(qs[m], ns[m], sizes[m])
        obs.append(TL.skin_mesh(f'LampyCapFlowers{ci}', TL.bounded(pf, wc, 0.40 * S), wc - 0.42 * S, wc + 0.42 * S,
                                TL.rubber(nome, col, dirt=0.25), res=RES_FINE * 1.4))
    _, bt = fiori(qs, ns, sizes)
    obs.append(TL.skin_mesh('LampyCapButtons', TL.bounded(bt, wc, 0.40 * S), wc - 0.42 * S, wc + 0.42 * S,
                            TL.rubber('CapFlowerCenter', (0.95, 0.93, 0.88), dirt=0.25), res=RES_FINE * 1.4))
    return obs


# ───────────────────────── il corpo ─────────────────────────

def arco_geometria():
    """La corda (la lenza tra bocca e coda): il verso giù per la lenza DL, la normale NL dalla parte dell'arco (in su)
    e la profondità W (via dal pescatore)."""
    DL = unit(CODA - BOCCA)
    NL = unit(V(0, 0, 1) - (V(0, 0, 1) @ DL) * DL)
    return DL, NL, V(0, 1, 0)


# il raggio del corpo lungo la linea (frazione dalla nuca alla coda): grosso e pesante in mezzo, come nella tavola,
# un poco più grosso
RAGGI = ((0.0, 0.15), (0.10, 0.20), (0.30, 0.26), (0.55, 0.265), (0.78, 0.225), (0.92, 0.165), (1.0, 0.13))


class Arco:
    """Il corpo: dalla nuca sale ad arco sopra la lenza e scende fino alla ventosa della coda, che la tiene in CODA.
    Il campo (tubo morbido con gli anelli fitti da sanguisuga, le pieghe larghe sul lato concavo, i bozzi molli, le
    pinne basse sul dorso, la ventosa), il ventre chiaro e i pori branchiali (come teste_lampy.Arch, ma con i capi
    dove dice la posa)."""

    def __init__(self, fr):
        DL, NL, W = arco_geometria()
        Lc = float(np.linalg.norm(CODA - BOCCA))
        P = lambda u: BOCCA + DL * Lc * u
        ctrl = [fr.pt(NUCA[0]), fr.pt(NUCA[1]),
                P(0.30) + NL * 0.64 + W * 0.30,
                P(0.62) + NL * 0.66 + W * 0.20,
                P(0.92) + NL * 0.48 + W * 0.10,
                CODA + NL * 0.20 + W * 0.02,
                CODA + NL * 0.07]
        self.pts = catmull(ctrl, 14).astype(F)
        seg = np.linalg.norm(np.diff(self.pts, axis=0), axis=1)
        self.s = np.concatenate([[0.0], np.cumsum(seg)]).astype(F)
        self.u = self.s / self.s[-1]
        f, r = zip(*RAGGI)
        self.r = np.interp(self.u, f, r).astype(F)
        tan = np.gradient(self.pts, axis=0)
        self.tan = (tan / np.linalg.norm(tan, axis=1, keepdims=True)).astype(F)
        inner = -NL[None, :] - (self.tan @ -NL)[:, None] * self.tan           # il lato concavo, verso la lenza
        self.inner = (inner / (np.linalg.norm(inner, axis=1, keepdims=True) + 1e-9)).astype(F)
        self.DL, self.NL, self.W = DL, NL, W
        self.fr = fr
        self.tree = cKDTree(self.pts)
        self.n3 = sdf.Noise3(41)
        # dove la linea esce dalla testa: lì cominciano il collo, i pori e i colori del corpo
        out = np.linalg.norm(self.pts - fr.pos, axis=1) > 0.30 * fr.S
        self.s_collo = float(self.s[int(np.argmax(out))])

    def base(self):
        idx = np.linspace(0, len(self.pts) - 1, 20).astype(int)
        body = chain([self.pts[i] for i in idx], [float(self.r[i]) for i in idx], k=0.06)
        # due pinne dorsali basse verso la coda, come la lampreda
        fins = []
        for u0, u1, hgt in ((0.58, 0.72, 0.06), (0.76, 0.93, 0.08)):
            for u in np.linspace(u0, u1, 6):
                i = int(np.searchsorted(self.u, u))
                out = -self.inner[i]
                lat = unit(np.cross(self.tan[i], out))
                w = math.sin(math.pi * (u - u0) / (u1 - u0)) ** 0.6
                c = self.pts[i] + out * (self.r[i] + hgt * 0.35 * w)
                fins.append(TL.ellipsoid_axes(c, (0.013, 0.05, hgt * w + 0.004), lat, self.tan[i], out))
        # la ventosa della coda, schiacciata sulla lenza (il disco steso lungo il filo, l'orlo carnoso)
        cup = TL.ellipsoid_axes(CODA + self.NL * 0.02, (0.20, 0.19, 0.075), self.W, self.DL, self.NL)
        lip = D.torus_axis(CODA, self.NL, 0.17, 0.035)
        return sdf.union(body, *fins, cup, lip, k=0.035)

    def detail(self, p):
        """Anelli fitti da sanguisuga (storti, non da tubo), pieghe larghe sul lato concavo, bozzi molli."""
        _, i = self.tree.query(p, workers=-1)
        s, c, r = self.s[i], self.pts[i], self.r[i]
        side = np.einsum('ij,ij->i', p - c, self.inner[i]) / np.maximum(r, 1e-3)
        inner = np.clip(side, 0.0, 1.0)
        wob = self.n3(p, scale=0.09, octaves=2)
        rings = (0.5 + 0.5 * np.cos(2 * np.pi * s / 0.048 + 2.2 * wob)) ** 4
        folds = (0.5 + 0.5 * np.cos(2 * np.pi * s / 0.12 + 1.5 * wob)) ** 1.5
        ends = np.clip((s - self.s_collo) / 0.08, 0, 1) * np.clip((0.97 - self.u[i]) / 0.05, 0, 1)
        lumps = self.n3(p + 7.0, scale=0.05, octaves=2)
        return (-(0.0032 * rings * (0.6 + 0.8 * np.abs(wob)) + 0.010 * folds * inner ** 1.5) * ends + 0.006 * lumps).astype(F)

    def field(self):
        return sdf.displace(self.base(), self.detail, 1.0)

    def collo(self):
        """Il collo fino a poco dietro la testa (mondo): la cuffia non lo deve attraversare."""
        m = self.s < self.s_collo + 0.25
        P, R = self.pts[m], self.r[m]
        idx = np.linspace(0, len(P) - 1, 8).astype(int)
        return chain([P[i] for i in idx], [float(R[i]) for i in idx], k=0.03)

    def belly(self, p):
        """Il ventre chiaro: il lato dell'arco verso la lenza."""
        _, i = self.tree.query(p, workers=-1)
        side = np.einsum('ij,ij->i', p - self.pts[i], self.inner[i]) / np.maximum(self.r[i], 1e-3)
        return np.clip(side * 1.4 - 0.2, 0.0, 1.0).astype(F)

    def pori(self, field):
        """Sette pori branchiali per lato, in fila sul collo dietro la testa: buchi tondi con l'orlo."""
        holes, rims, allp = [], [], []
        for side in (-1, 1):
            want = []
            for k in range(7):
                i = int(np.searchsorted(self.s, self.s_collo + 0.07 + 0.052 * k))
                c, r = self.pts[i], self.r[i]
                bn = unit(np.cross(self.tan[i], self.inner[i]))
                bn = bn if bn @ self.W * side > 0 else -bn
                want.append(c + bn * r * 0.93 + self.inner[i] * r * 0.30)
            pts, nrm = TL.snap(field, want)
            allp += list(pts)
            for q, n in zip(pts, nrm):
                holes.append(sdf.sphere(q - n * 0.002, 0.0135))
                rims.append(D.torus_axis(q + n * 0.001, n, 0.0175, 0.0062))
        allp = np.array(allp)
        c = (allp.min(0) + allp.max(0)) / 2
        R = float(np.linalg.norm(allp.max(0) - allp.min(0))) / 2 + 0.03
        return TL.bounded(sdf.union(*rims), c, R), TL.bounded(sdf.union(*holes), c, R)


# ───────────────────────── la bava ─────────────────────────

def bava(name, field, anchors, rng, lmin=0.035, lmax=0.075):
    """Bava che cola dai punti (posati sulla superficie del campo): gocce grasse di melma appese, come
    teste_lampy.drips, ma ogni goccia si valuta solo vicino a sé e la superficie si estrae a fasce."""
    pts, _ = TL.snap(field, anchors)
    parts = []
    for q in pts:
        L = float(rng.uniform(lmin, lmax))
        a = q + V(0, 0, 0.006)
        parts.append(TL.bounded(skin.drip(a, L, r0=0.0085, r1=float(rng.uniform(0.012, 0.016))), a - V(0, 0, L / 2),
                                L / 2 + 0.03, margin=0.01))
    lo, hi = pts.min(0) - 0.03, pts.max(0) + 0.03
    lo[2] -= lmax + 0.03
    ob = sdf_object(name, sdf.union(*parts), lo, hi, res=0.0025, banded=True)
    ob.data.materials.append(TL.goo_material())
    return ob


# ───────────────────────── costruzione ─────────────────────────

def build(viewer=None, bocca=BOCCA_RIPOSO, denti_giro=0.0, solo_testa=False):
    """Lampy sulla lenza, in coordinate locali. viewer: dove guardano la faccia e gli occhi (il pescatore).
    bocca: l'apertura della ventosa, da 0 (chiusa) a 1 (spalancata); denti_giro: di quanti gradi girano gli anelli di
    denti. Gli occhi sono gli oggetti 'LampyEye0' e 'LampyEye1'. La pelle è tagliata in due mesh che combaciano:
    'LampyHead' (la testa fino alla nuca) e 'LampySkin' (il corpo); solo_testa=True fa solo la testa con i suoi
    pezzi (per le inquadrature della bocca: il corpo non cambia)."""
    P = dict(POSA)
    if viewer is not None:
        P['viewer'] = viewer
    vw = V(*P['viewer'])
    fr = testa_frame(vw)
    v = ventosa(bocca)
    hl, cut_l = testa_campo(v)
    arco = Arco(fr)
    S = fr.S
    head = TL.bounded(fr.field(hl), fr.pos, 0.50 * S)
    f = sdf.union(arco.field(), head, k=0.06)
    f = sdf.subtract(f, TL.bounded(fr.field(cut_l), fr.pos, 0.50 * S), k=0.006)
    rims, holes = arco.pori(f)
    f = sdf.subtract(sdf.union(f, rims, k=0.004), holes, k=0.003)
    mouth, blush = colori_bocca(fr, v)

    def belly(p):
        """Ventre chiaro: il lato dell'arco verso la lenza e, sulla testa, la parte di sotto."""
        q = fr.local(p)
        near = np.clip(1 - (np.linalg.norm(p - fr.pos, axis=1) - 0.26 * S) / (0.12 * S), 0, 1)
        under = np.clip(-q[:, 2] / 0.18 + 0.15, 0, 1)
        return np.maximum(arco.belly(p) * (1 - near), near * under).astype(F)
    attrs = {'belly': belly, 'mouth': mouth, 'blush': blush}
    # la testa: dentro una sfera (ci sta anche il labbro di sotto a bocca spalancata), dalla parte della faccia
    # rispetto al piano che taglia il collo dietro la nuca
    n0, n1 = fr.pt(NUCA[0]), fr.pt(NUCA[1])
    tn = unit(n1 - n0)
    zona = sdf.intersect(sdf.sphere(fr.pos, 0.50 * S), D.above(n1 + tn * 0.02, -tn))
    pelle = TL.lampy_skin()
    obs = []
    ob = sdf_object('LampyHead', sdf.intersect(f, zona), fr.pos - 0.52 * S, fr.pos + 0.52 * S, res=RES_HEAD, attrs=attrs,
                    banded=True)
    ob.data.materials.append(pelle)
    obs.append(ob)
    if not solo_testa:
        lo = np.minimum(arco.pts.min(0), fr.pos) - 0.34
        hi = np.maximum(arco.pts.max(0), fr.pos) + 0.34
        lo[2] = max(lo[2], -0.04)                 # sotto il mare non serve: nel gioco il mare fa da maschera
        ob = sdf_object('LampySkin', sdf.subtract(f, zona), lo, hi, res=RES_BODY, attrs=attrs, banded=True)
        ob.data.materials.append(pelle)
        obs.append(ob)
    # gli occhi tondi senza palpebre, lattiginosi, che guardano il pescatore
    for i, o in enumerate(OCCHI):
        e = fr.pt(o)
        obs.append(eyeball(f'LampyEye{i}', tuple(map(float, e)), R_OCCHIO * S, D.milky_eye(), look=tuple(map(float, unit(vw - e)))))
    obs.append(denti(fr, v, denti_giro))
    obs.append(gola(fr, v))
    obs += cuffia(fr, arco.collo())
    # la bava: dal labbro di sotto e, sul corpo, dal sotto dell'arco e dalla ventosa della coda
    rng = np.random.default_rng(12)
    c, lip = v['c'], v['h'] + v['r'] * 1.2
    obs.append(bava('LampySlimeMouth', f, [fr.pt(c + V(0.0, -0.01, -lip)), fr.pt(c + V(0.055, 0.0, -lip * 0.85))], rng))
    if not solo_testa:
        anchors = []
        for u in (0.30, 0.45, 0.57):
            i = int(np.searchsorted(arco.u, u))
            anchors.append(arco.pts[i] + arco.inner[i] * arco.r[i] + V(0.0, 0.04 * math.sin(9 * u), 0.0))
        anchors += [CODA - arco.NL * 0.07 + arco.DL * 0.12, CODA - arco.NL * 0.06 - arco.DL * 0.10 + V(0, -0.08, 0)]
        obs.append(bava('LampySlime', f, anchors, rng))
    return obs


# ───────────────────────── la lenza (solo per vetrina e anteprime) ─────────────────────────

def lenza_obj(punti, name='LampyLenzaRiferimento'):
    """La lenza come riferimento nelle vetrine e nelle anteprime (nel gioco la disegna il motore): un filo di nylon
    chiaro per i punti dati (mondo), un po' più spesso del vero perché si veda."""
    P = np.array([np.asarray(p, float) for p in punti])
    pts = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        for t in np.linspace(0, 1, 12)[1:]:
            pts.append(a + (b - a) * t)
    ob = tube(name, np.array(pts), 0.0028, n=8, col='set')
    ob.data.materials.append(D.mat_simple('Nylon', (0.80, 0.80, 0.74), rough=0.18, coat=0.6, transmission=0.3))
    return ob


# ───────────────────────── vetrina ─────────────────────────

SHOTS = {
    # (camera, bersaglio, lente), in coordinate locali di Lampy (il pescatore sta verso −Y)
    'insieme': ((-1.55, -2.85, 1.55), (0.0, 0.10, 0.80), 30),
    'testa': ((-0.42, -0.95, 1.20), (-0.60, 0.20, 1.10), 48),
    'fuori': ((1.85, 2.70, 1.75), (0.0, 0.20, 0.80), 30),
}
# la ventosa da vicino, nelle tre aperture: (titolo, bocca, giro dei denti)
VENTOSE = (('chiusa (bocca 0)', 0.0, 0.0), ('a riposo (bocca 0,5)', BOCCA_RIPOSO, 0.0),
           ('spalancata (bocca 1), denti girati di 10°', 1.0, 10.0))
SHOT_VENTOSA = ((-0.78, -0.88, 1.20), (-0.62, 0.05, 1.10), 55)


def mare():
    """Il mare della vetrina: nero e bagnato, con le onde lunghe e le increspature che rompono i riflessi delle luci
    di studio (come teste_fangy.water: uno specchio li mostrava interi)."""
    from nodes import material
    m = bpy.data.materials.get('LampySea')
    if m is None:
        m, g = material('LampySea')
        co = g.texcoord('Object')
        swell = g.noise(g.mapping(co, scale=(1.0, 2.6, 1.0)), scale=2.4, detail=2.0)
        chop = g.noise(co, scale=14.0, detail=2.0, rough=0.5)
        h = g.add(swell.fac, g.mul(chop.fac, 0.25))
        g.output_material(g.principled(color=(0.003, 0.009, 0.013), rough=0.08, spec=0.5, normal=g.bump(h, strength=0.4, distance=0.03)))
    w = rbox('Water', (120, 120, 0.01), (0, 40.0, -0.005), bevel=0.0, col='set')
    w.data.materials.append(m)
    w.lightgroup = 'ambient'
    return w


def _luci(M, h):
    """Le luci di studio delle altre vetrine, attorno alla testa h (mondo): la lampara calda dalla barca, la luna
    fredda da dietro, poco riempimento."""
    from mathutils import Vector
    R = M.to_3x3()
    rel = lambda v: tuple(h + np.array(R @ Vector(v)))
    D.area_light('Key', rel((-1.6, -1.8, 0.6)), tuple(h), 60, (1.0, 0.74, 0.46), 0.6)
    D.area_light('Rim', rel((1.4, 2.2, 1.6)), tuple(h + (0.0, 0.0, -0.3)), 160, (0.55, 0.72, 1.0), 0.8)
    D.area_light('Fill', rel((1.2, -2.0, 0.2)), tuple(h), 12, (0.55, 0.65, 0.85), 1.6)


def scena_vetrina(variante=None):
    """La scena della vetrina: Lampy nella posa di gioco sulla lenza (scena_creature.lampy_posa), sul mare, con la
    lenza di riferimento dalla punta della canna; resa AgX. variante = (bocca, giro): solo la testa. Restituisce la
    trasformazione della posa."""
    import scena_creature as SC
    from mathutils import Vector
    sc = reset_scene()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.cycles.use_denoising = True
    w = bpy.data.worlds.new('Night')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.010, 0.014, 0.022, 1)
    w.lightgroup = 'ambient'
    mare()
    M, kw = SC.lampy_posa()
    if variante is None:
        SC.place(build(**kw), M)
    else:
        SC.place(build(**kw, bocca=variante[0], denti_giro=variante[1], solo_testa=True), M)
    lenza_obj(SC.lampy_lenza_punti(M))
    h = np.array(M @ Vector(tuple(map(float, testa_frame(kw['viewer']).pos))))
    _luci(M, h)
    return M


def _camera(M, cl, ct, lens):
    from mathutils import Vector
    sc = bpy.context.scene
    cam = sc.camera
    if cam is None:
        cam_d = bpy.data.cameras.new('Cam')
        cam_d.sensor_width = 36.0
        cam_d.clip_start = 0.02
        cam = bpy.data.objects.new('Cam', cam_d)
        sc.collection.objects.link(cam)
        sc.camera = cam
    cam.data.lens = lens
    a, b = M @ Vector(cl), M @ Vector(ct)
    cam.location = a
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = (b - a).to_track_quat('-Z', 'Y')
    return cam


def showcase(shots=('insieme', 'testa', 'fuori'), ventose=True):
    """La vetrina: tools/render/cache/vetrina/lampy_<inquadratura>.png, la ventosa da vicino nelle tre aperture
    (lampy_ventosa_<i>.png, solo la testa) e la tavola docs/concept/lampy_vetrina.jpg."""
    out = []
    os.makedirs(os.path.join(CACHE, 'vetrina'), exist_ok=True)
    W, H = (720, 540) if FAST else (960, 720)          # la tavola li riduce a 480 × 360

    def setup():
        sc = bpy.context.scene
        sc.render.resolution_x, sc.render.resolution_y = W, H
        sc.render.resolution_percentage = 100
        sc.cycles.samples = 32 if FAST else 64
        sc.render.image_settings.file_format = 'PNG'
        return sc
    if shots:
        M = scena_vetrina()
        sc = setup()
        for name in shots:
            _camera(M, *SHOTS[name])
            path = os.path.join(CACHE, 'vetrina', f'lampy_{name}.png')
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            out.append(path)
            print('ok', path, flush=True)
    if ventose:
        for i, (_, b, g) in enumerate(VENTOSE):
            M = scena_vetrina((b, g))
            sc = setup()
            _camera(M, *SHOT_VENTOSA)
            path = os.path.join(CACHE, 'vetrina', f'lampy_ventosa_{i}.png')
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            out.append(path)
            print('ok', path, flush=True)
    if shots and ventose:
        tavola_vetrina()
    return out


def _font(size, bold=False):
    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else ''), size)
    except OSError:
        return ImageFont.load_default()


def tavola_vetrina(size=(480, 360)):
    """La tavola della vetrina: sopra le tre inquadrature (insieme, testa, da dietro), sotto la ventosa nelle tre
    aperture, con le didascalie → docs/concept/lampy_vetrina.jpg."""
    W, H = size
    cap = 30
    sheet = Image.new('RGB', (3 * W, 2 * (H + cap)), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    font = _font(15)
    titoli = ['insieme, dalla parte della barca', 'la testa', 'da dietro: pori, pinne, ventosa della coda']
    righe = [[os.path.join(CACHE, 'vetrina', f'lampy_{n}.png') for n in ('insieme', 'testa', 'fuori')],
             [os.path.join(CACHE, 'vetrina', f'lampy_ventosa_{i}.png') for i in range(len(VENTOSE))]]
    for r, (paths, tt) in enumerate(zip(righe, (titoli, ['ventosa ' + t for t, _, _ in VENTOSE]))):
        for i, (p, t) in enumerate(zip(paths, tt)):
            im = Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS)
            y = r * (H + cap)
            sheet.paste(im, (i * W, y))
            d.text((i * W + 8, y + H + 6), t, fill=(225, 225, 220), font=font)
    dst = os.path.join(ROOT, 'docs', 'concept', 'lampy_vetrina.jpg')
    sheet.save(dst, quality=90)
    print('tavola', dst, flush=True)
    return dst


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


def _rel(p):
    return [round(float(p[i] - EYE[i]), 4) for i in range(3)]


def ingombro(obs, M, lenza):
    """Dove sta la posa vista dall'occhio del pescatore (per la regia del gioco): yaw e pitch minimi e massimi di
    tutti i pezzi e della parte che si vede davvero (senza quello che coprono la barca e il mare), della testa e del
    corpo; dove stanno la testa e gli occhi (gradi, e metri dall'occhio); e i punti della lenza dall'occhio (la punta
    della canna, la bocca, la ventosa della coda, l'entrata in mare): il motore la deve disegnare per quei punti."""
    import jobs
    from mathutils import Vector
    meshes = [o for o in obs if o.type == 'MESH']
    pts = np.array(jobs.dense_points(meshes, n=2500))
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
    vis = np.array(vis) & (pts[:, 2] > 0.0)
    fr = testa_frame(POSA['viewer'])
    head = M @ Vector(tuple(map(float, fr.pos)))
    eyes = [o for o in meshes if 'Eye' in o.name]
    out = {
        'tutto': _span(pts),
        'visibile': _span(pts[vis]),
        'testa': _dir(head),
        'testa_m': _rel(head),
        'distanza_testa': round(float(math.dist(tuple(head), EYE)), 2),
        'quota_testa': round(float(head[2]), 2),
        'occhi': [_dir(o.matrix_world.translation) for o in eyes],
        'occhi_m': [_rel(o.matrix_world.translation) for o in eyes],
        'lenza_m': {k: _rel(p) for k, p in zip(('punta', 'bocca', 'coda', 'acqua'), lenza)},
        'lenza': {k: _dir(p) for k, p in zip(('punta', 'bocca', 'coda', 'acqua'), lenza)},
    }
    for k, n in (('testa_mesh', 'LampyHead'), ('corpo', 'LampySkin')):
        o = bpy.data.objects.get(n)
        if o:
            out[k] = _span(jobs.dense_points([o], n=2500))
    return out


POSE_ANTEPRIME = {
    # (yaw, pitch, lente): la vista del gioco (90° di campo) girata verso la canna, e una più stretta su Lampy
    'pose_lampy': (24.0, -6.0, 18.0),
    'pose_lampy_vicino': (None, -4.0, 40.0),
}


def anteprima_posa():
    """Anteprima della posa lampy_lenza senza toccare il gioco (come robin.anteprima_posa): la scena del gioco con la
    batteria (dalla notte 2 c'è sempre), la canna, la posa da scena_creature e la lenza di riferimento per i punti
    della posa; la camera prospettica dall'occhio del pescatore come la vista del gioco (90° di campo) e una più
    stretta su Lampy. Scrive i pannelli in cache e l'ingombro in cache/lampy_posa.json."""
    import batteria
    import jobs
    import scena_creature as SC
    from common import perspective_camera
    jobs.build_scene(fish=5, rod=True)
    batteria.build_battery(needle=0.72)
    before = set(bpy.data.objects.keys())
    SC.POSES['lampy_lenza'][0]()
    bpy.context.view_layer.update()
    new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
    M = SC.LAST_M['lampy_lenza']
    lenza = SC.lampy_lenza_punti(M)
    info = ingombro(new, M, lenza)
    lenza_obj(lenza)
    print('ingombro', json.dumps(info), flush=True)
    with open(os.path.join(CACHE, 'lampy_posa.json'), 'w') as fh:
        json.dump(info, fh, indent=1)
    sc = bpy.context.scene
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.resolution_percentage = 100
    sc.render.resolution_x, sc.render.resolution_y = (960, 540) if FAST else (1600, 900)
    sc.cycles.samples = 24 if FAST else 64
    out = []
    for name, (yaw, pitch, lens) in POSE_ANTEPRIME.items():
        if yaw is None:
            yaw = info['testa'][0] + 3.0
        t = (EYE[0] + math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)),
             EYE[1] + math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)), EYE[2] + math.sin(math.radians(pitch)))
        perspective_camera(EYE, t, lens=lens, name='LampyCam_' + name)
        path = os.path.join(CACHE, f'{name}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('pannello', path, flush=True)
    return out, info


def anteprima_tavole(paths=None):
    """Le anteprime della posa con la scritta «da approvare» → docs/concept/pose_lampy.jpg e pose_lampy_vicino.jpg
    (dai pannelli in cache, senza rifarli)."""
    paths = paths or [os.path.join(CACHE, f'{n}.png') for n in POSE_ANTEPRIME]
    font = _font(22, bold=True)
    out = []
    for p in paths:
        im = Image.open(p).convert('RGB')
        d = ImageDraw.Draw(im)
        txt = 'LAMPY · posa lampy_lenza · da approvare'
        d.rectangle((0, 0, int(d.textlength(txt, font=font)) + 24, 38), fill=(14, 14, 16))
        d.text((12, 7), txt, fill=(240, 190, 110), font=font)
        dst = os.path.join(ROOT, 'docs', 'concept', os.path.basename(p).replace('.png', '.jpg'))
        im.save(dst, quality=90)
        out.append(dst)
        print('anteprima', dst, flush=True)
    return out


if __name__ == '__main__':
    if '--posa' in sys.argv:
        anteprima_posa()
        anteprima_tavole()
    elif '--posa-tavole' in sys.argv:
        anteprima_tavole()
    elif '--vetrina-tavola' in sys.argv:
        tavola_vetrina()
    elif '--solo' in sys.argv:
        solo = sys.argv[sys.argv.index('--solo') + 1].split(',')
        showcase(tuple(s for s in solo if s in SHOTS), ventose='ventosa' in solo)
    else:
        showcase()
