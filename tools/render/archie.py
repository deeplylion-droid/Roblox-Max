"""
ARCHIE — modello definitivo (sagoma C «Periscopio», testa A «Serpente»), notte 3.

Un collo sottilissimo e lunghissimo sale dritto dal mare accanto alla prua; in cima fa l'arco e la testa guarda
giù sulla lampara, con la trombetta da festa puntata sul vetro. Viene dal serpente di mare del Mediterraneo
(Ophisurus serpens): un'anguilla serpentiforme, il muso lungo e appuntito, i denti aguzzi fuori dalle labbra, le
narici a tubetto in punta, la pinna bassa lungo il dorso, niente braccia. Da bambino, alle feste di compleanno al
parco, spegneva lui le candeline degli altri bambini: ora soffia sulla lampara. La trombetta (la lingua di Menelik
di carta a strisce, con la piuma in punta) ha il bocchino fuso nelle labbra.

La testa è la A «Serpente» della tavola (teste_archie.archie_a) rifinita: più fine (è quella che nel jumpscare ti
arriva in faccia), le arcate sopra gli occhi un po' aggrottate, le labbra col bordo, i denti più lunghi davanti e
storti come quelli di una murena, le pieghe della gola. Colori approvati (10 ottobre), quelli della tavola: giallo
limone pieno a bande nere che girano tutto attorno al collo, la gola giallo chiaro, la carta rossa e bianca, la
piuma rosa; melma e chiazze di famiglia.

Coordinate: il mare è z = 0 e il collo sale dall'origine; la faccia guarda −Y, verso la lampara, che sta davanti
a lui e più in basso della testa. Nel gioco la posa si ricalcola dalla barca (scena_creature.archie_posa): la
lampara e il pescatore arrivano come parametri; senza parametri build() rifà la posa di gioco (POSA, numeri
arrotondati).

Le parti che si muovono, per le toppe del gioco (come palpebre e aggrotta di robin.build): build(srotolata=…)
srotola la trombetta, 0 tutta arrotolata stretta sotto il muso (com'è a riposo), 1 tutta distesa e gonfia verso la
lampara con la piuma in punta; build(fiato=…) gonfia la gola come un pallone (il risucchio prima di soffiare).
A 0 Archie è quello di sempre, oggetto per oggetto, e il collo e la testa restano dove sono in ogni variante.

Uso: tools/.venv/bin/python tools/render/archie.py [--fast]          vetrina → docs/concept/archie_vetrina.jpg
     tools/.venv/bin/python tools/render/archie.py [--fast] --posa   la posa di gioco nella scena della barca, vista
                                                                     dall'occhio → docs/concept/pose_archie*.jpg
     tools/.venv/bin/python tools/render/archie.py --jumpscare-tavola   la tavola dei fotogrammi del jumpscare dagli
                                    EXR in cache/draft/jumpscare → docs/concept/jumpscare/js_archie_fotogrammi.jpg
     nella vetrina: --srotolata 1 --fiato 1 per le varianti, --solo testa,insieme per alcune inquadrature soltanto
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
import teste_archie as TA  # noqa: E402  (la bozza della testa: materiali, labbra fuse, aiuti)
import teste_robin as R  # noqa: E402  (aiuti per tubi, campi e mesh)
from common import CACHE, EYE, ROOT, reset_scene  # noqa: E402
from creature import eyeball, sdf_object  # noqa: E402
from geo import catmull  # noqa: E402

V, F, unit, chain = D.V, D.F, D.unit, D.chain
tubo, entro, fine = R.tubo, R.entro, R.fine
FAST = '--fast' in sys.argv
# la pelle è un campo solo (collo e testa) tagliato in due mesh a risoluzioni diverse, che combaciano
RES_BODY = 0.0045 if FAST else 0.003      # il collo
RES_HEAD = 0.0028 if FAST else 0.0015     # la testa (nel jumpscare arriva a mezzo metro dall'occhio)
RES_FINE = 0.0018 if FAST else 0.0010     # pezzi sottili (denti, piuma, bava)

K = 1.30                                  # la testa A più grande del vero (nella tavola 1,15): a quasi cinque metri
                                          # dal pescatore deve leggersi accanto al cappello della lampara
HEAD = V(0.0, -0.20, 2.06)                # centro della testa (prima di puntarla sulla lampara)
# nel sistema locale della testa (dritta, faccia verso −Y, alto +Z), come teste_archie.archie_a:
QB = V(0.0, -0.214, -0.012)               # dove il bocchino esce dalle labbra
DB = unit(V(0.0, -1.0, 0.15))             # e verso dove punta
OCCHI = [V(s * 0.0285, -0.098, 0.021) for s in (-1, 1)]   # nella tavola sporgevano troppo, da rana: qui affondano
R_OCCHIO = 0.0136
ATTACCO = V(0.0, 0.125, -0.040)           # dove il collo entra nella testa: dietro e sotto, la nuca sporge sopra
PIEGA = 50.0                              # gradi: quanto il collo, in cima, si piega in avanti verso la testa
R_PIEGA = 0.30                            # il raggio di quella piega
K_CARTA = 1.45                            # la trombetta, più grande del vero come la testa
CARTA_L = 0.40                            # la lingua di carta, dal bocchino alla punta (metri)
PIUMA_L = 0.060                           # la piuma in punta

# la posa di gioco (scena_creature.archie_posa) in coordinate locali, arrotondata: è quella che build() fa senza
# parametri. Nel gioco i numeri si ricalcolano dalla barca.
POSA = {
    'lampara': (0.0, -0.9603, 1.8028),
    'viewer': (3.4159, -3.3521, 1.2528),
}


# ───────────────────────── la testa ─────────────────────────

def orienta(lampara, iters=24):
    """Yaw e pitch della testa (dettagli.Frame) perché la trombetta, che esce dal bocchino lungo DB, punti dritta sul
    vetro della lampara. DB sta più in su dell'asse della testa: la testa china il muso un po' di più."""
    L = V(*lampara)
    a = unit(L - HEAD)
    yaw = math.degrees(math.atan2(float(a[0]), float(-a[1])))
    pitch = -math.degrees(math.asin(float(a[2])))
    for _ in range(iters):
        fr = TA.Testa(tuple(map(float, HEAD)), pitch=pitch, yaw=yaw, k=K)
        p0 = fr.pt(QB)
        w = unit(L - p0)                                   # dove deve puntare la trombetta
        t = unit(fr.R @ DB)                                # dove punta adesso
        yaw += math.degrees(math.atan2(float(w[0]), float(-w[1])) - math.atan2(float(t[0]), float(-t[1])))
        pitch += math.degrees(math.asin(float(t[2])) - math.asin(float(w[2])))
    return yaw, pitch


def gape():
    """Lo squarcio della bocca, dalla punta del muso fin dietro l'occhio (un lato per verso): in fondo risale appena,
    il ghigno storto delle murene."""
    return [[V(s * 0.016, -0.200, -0.014), V(s * 0.034, -0.140, -0.024), V(s * 0.045, -0.072, -0.031),
             V(s * 0.047, -0.030, -0.033), V(s * 0.044, -0.004, -0.027)] for s in (-1, 1)]


def gola(fiato):
    """La gola gonfia (centro e semiassi, locali): a riposo appena gonfia, col fiato tesa come un pallone."""
    g = min(max(float(fiato), 0.0), 1.0)
    c = V(0, -0.030, -0.050) + (V(0, -0.046, -0.082) - V(0, -0.030, -0.050)) * g
    r = V(0.045, 0.088, 0.034) + (V(0.074, 0.118, 0.064) - V(0.045, 0.088, 0.034)) * g
    return c, r


def testa_campo(fiato=0.0):
    """La testa A in coordinate locali: il cranio lungo e basso, il muso appuntito con le narici a tubetto, la
    mascella, la gola (gonfia secondo 'fiato'), le arcate sopra gli occhi, le labbra cresciute attorno al bocchino.
    Restituisce il campo, i tagli (bocca, buco del bocchino, orbite, pori della linea laterale) e lo squarcio."""
    cran = sdf.ellipsoid(V(0, 0.03, 0.0), (0.052, 0.16, 0.058))
    snout = sdf.round_cone(V(0, -0.06, 0.002), V(0, -0.212, -0.004), 0.048, 0.014)
    jaw = chain([V(0, 0.02, -0.040), V(0, -0.10, -0.032), V(0, -0.200, -0.020)], [0.044, 0.032, 0.013], k=0.02)
    gc, gr = gola(fiato)
    gular = sdf.ellipsoid(gc, tuple(float(x) for x in gr))
    nares = sdf.union(*[sdf.round_cone(V(s * 0.010, -0.196, 0.006), V(s * 0.015, -0.214, -0.012), 0.0046, 0.0034) for s in (-1, 1)])
    # le arcate: una cresta morbida sopra ogni occhio, più bassa verso il muso (lo sguardo cattivo)
    brows = sdf.union(*[chain([o + V(s * 0.000, -0.026, 0.009), o + V(s * 0.004, -0.004, 0.0145), o + V(s * 0.002, 0.020, 0.016)],
                              [0.0042, 0.0068, 0.0050], k=0.004) for s, o in zip((-1, 1), OCCHI)])
    g = gape()
    # le labbra: un cordoncino sopra e sotto lo squarcio, i denti escono da lì
    lips = sdf.union(*[chain([p + V(np.sign(p[0]) * 0.002, 0, dz) for p in side], [0.0030, 0.0036, 0.0036, 0.0032, 0.0024], k=0.003)
                       for side in g for dz in (0.0045, -0.0045)])
    head = sdf.union(cran, snout, jaw, gular, nares, TA.labbra_fuse(QB, tuple(map(float, DB)), 0.0105, 0.0058), k=0.016)
    head = sdf.union(head, brows, k=0.012)
    head = sdf.union(head, lips, k=0.004)
    mouth = sdf.union(*[chain(side, [0.0026, 0.0034, 0.0032, 0.0028, 0.0018], k=0.002) for side in g])
    hole = sdf.round_cone(QB + DB * 0.01, QB - DB * 0.02, 0.0072, 0.0066)
    sockets = sdf.union(*[sdf.sphere(o, R_OCCHIO + 0.0012) for o in OCCHI])
    pores = sdf.union(*[sdf.sphere(V(s * 0.034, y, 0.022), 0.0026) for s in (-1, 1) for y in (-0.150, -0.125, -0.070, -0.045)])
    nostrils = sdf.union(*[sdf.sphere(V(s * 0.015, -0.216, -0.013), 0.0022) for s in (-1, 1)])
    cut = sdf.union(mouth, hole, sockets, pores, nostrils)
    # le pieghe della gola: solchi di traverso, che col fiato si tendono e spariscono
    fold_amp = 0.0016 * (1.0 - min(max(float(fiato), 0.0), 1.0))

    def pieghe(q):
        d = np.linalg.norm((q - gc) / (gr * V(0.95, 0.85, 1.05)), axis=1)
        m = (1.0 - D.smooth01(d, 0.80, 1.15)) * D.smooth01(-(q[:, 2] - gc[2]), -0.004, 0.020)
        return (np.sin(q[:, 1] * 260.0 + np.sin(q[:, 0] * 90.0) * 0.8) * m).astype(F)
    if fold_amp > 0:
        head = sdf.displace(head, pieghe, fold_amp)
    return head, cut, g, (mouth, hole, nostrils)


def testa_colori(q):
    """Gli attributi del colore sulla testa (coordinate locali): 'ventre' (la gola chiara), 'seconda' (le bande nere:
    quella che passa sugli occhi e quella dietro la nuca) e la maschera della testa."""
    m = sdf.ellipsoid(V(0, -0.03, -0.03), (0.11, 0.28, 0.16))(q) < 0.0
    ven = np.clip(0.5 - (q[:, 2] + 0.005) / 0.08, 0.0, 1.0)
    sec = TA.bande_testa(q, [(-0.098, 0.026, 0.018), (0.110, 0.030, 0.024)], zmin=-0.045)
    return ven, sec, m


def denti(fr, g):
    """I denti aguzzi che restano fuori dalle labbra, come nel serpente di mare: di sopra puntano in giù e in fuori,
    di sotto in su; davanti due zanne lunghe per lato, poi sempre più corti verso l'angolo della bocca. Ogni dente è
    un po' storto (piegato all'indietro, come i denti delle murene)."""
    rng = np.random.default_rng(31)
    parts, pts = [], []
    for side in g:
        s = float(np.sign(side[0][0]))
        for su, n, L0, r0, dz, dy in ((True, 7, 0.034, 0.0036, 0.0040, 0.0), (False, 6, 0.024, 0.0032, -0.0040, 0.008)):
            lab = catmull([p + V(s * 0.002, dy, dz) for p in side], 10)
            idx = np.linspace(0.03, 0.78, n) * (len(lab) - 1)
            for j, x in enumerate(idx):
                p = lab[int(round(x))]
                f = j / (n - 1)
                L = L0 * (1.0 if j < 2 else 0.72 - 0.30 * f) * rng.uniform(0.85, 1.12)
                out = unit(V(s * 0.55, -0.10 + rng.uniform(-0.12, 0.12), -1.0 if su else 1.0))
                back = unit(V(0, 1.0, 0))
                b = p - out * 0.003
                m = p + out * L * 0.55
                t = p + out * L + back * L * 0.22                  # la punta piegata all'indietro
                r = r0 * (1.0 if j < 2 else 0.85)
                parts.append(sdf.round_cone(fr.pt(b), fr.pt(m), r * fr.k, r * 0.62 * fr.k))
                parts.append(sdf.round_cone(fr.pt(m), fr.pt(t), r * 0.62 * fr.k, r * 0.12 * fr.k))
                pts += [fr.pt(b), fr.pt(t)]
    P = np.array(pts, F)
    ob = sdf_object('ArchieTeeth', sdf.union(*parts), P.min(0) - 0.012, P.max(0) + 0.012, res=RES_FINE, banded=True)
    ob.data.materials.append(D.needle_teeth())
    return ob


# ───────────────────────── il collo ─────────────────────────

def collo_dir(fr):
    """Il verso del collo dove entra nella testa: in su, piegato in avanti di PIEGA gradi verso dove guarda la testa."""
    h = unit(V(*fr.dir(V(0, -1.0, 0))[:2], 0.0))
    a = math.radians(PIEGA)
    return unit(h * math.sin(a) + V(0, 0, math.cos(a))), h


def collo_punti(fr):
    """La linea del collo, a periscopio: sale dritta dal mare dietro la testa, appena inclinata e con un filo di
    serpentina, e in cima si piega in avanti (PIEGA gradi, raggio R_PIEGA) entrando nella testa da dietro e da sotto;
    la testa, china sulla lampara, fa da gomito."""
    A = fr.pt(ATTACCO)
    tA, h = collo_dir(fr)
    a = math.radians(PIEGA)
    # la piega nel piano verticale (u avanti, w su): P(θ) = C + R(−cos θ, sin θ), θ da 0 (sale dritto) a PIEGA
    C = A + h * (R_PIEGA * math.cos(a)) - V(0, 0, R_PIEGA * math.sin(a))
    curva = [C + h * (-R_PIEGA * math.cos(t)) + V(0, 0, R_PIEGA * math.sin(t)) for t in np.linspace(0.0, a, 6)]
    base = curva[0]
    side = unit(np.cross(V(0, 0, 1), h))
    zs = (-0.60, -0.05, 0.50, 1.00, 1.42)
    up = []
    for z in zs:
        f = (base[2] - z) / (base[2] - zs[0])               # 0 in cima, 1 in fondo
        up.append(V(base[0], base[1], z) + h * (0.10 * f * f) + side * (0.035 * math.sin(f * 4.4)))
    return up + curva[:-1] + [A, A + tA * 0.04]


# il raggio del collo lungo la sua lunghezza (frazione da 0, in fondo al mare, a 1, dentro la nuca)
RAGGI = ((0.0, 0.088), (0.22, 0.080), (0.55, 0.065), (0.80, 0.054), (0.92, 0.050), (0.98, 0.054), (1.0, 0.056))


class Collo:
    """Il collo come campo (la distanza da una linea liscia, col raggio che cambia lungo la lunghezza) e gli
    attributi che servono ai colori: lunghezza d'arco, tangente, 'dorso' (1 sul dorso, −1 sulla gola)."""

    def __init__(self, pts, side):
        P = catmull(pts, 24).astype(F)
        T = np.gradient(P, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        B = np.cross(T, V(*side))
        B /= np.linalg.norm(B, axis=1, keepdims=True)
        self.P, self.T, self.B = P, T, B
        self.s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]).astype(F)
        self.tree = cKDTree(P)

    def raggio(self, sv):
        f, r = zip(*RAGGI)
        return np.interp(np.asarray(sv) / self.s[-1], f, r).astype(F)

    def query(self, p, lato=False):
        """Distanza dalla linea (proiettata sulla tangente: liscia, niente scalini), lunghezza d'arco e 'dorso'; con
        lato=True anche 'lato' (1 a sinistra, −1 a destra)."""
        d, i = self.tree.query(p, k=1, workers=-1)
        r = p - self.P[i]
        along = np.einsum('ij,ij->i', r, self.T[i])
        perp = r - along[:, None] * self.T[i]
        dist = np.linalg.norm(perp, axis=1)
        ends = ((i == 0) & (along < 0)) | ((i == len(self.P) - 1) & (along > 0))
        dist = np.where(ends, np.linalg.norm(r, axis=1), dist)
        rn = perp / (dist[:, None] + 1e-9)
        b = np.einsum('ij,ij->i', rn, self.B[i])
        out = (dist.astype(F), (self.s[i] + along).astype(F), b.astype(F))
        if lato:
            c = np.einsum('ij,ij->i', rn, np.cross(self.T[i], self.B[i]))
            out += (c.astype(F),)
        return out

    def campo(self, p):
        d, s, _ = self.query(p)
        # la pancia del serpente è un po' più piatta del dorso, e la carne fa piccoli rigonfiamenti
        return d - self.raggio(s) * (1.0 + 0.035 * np.sin(s * 7.0 + 1.3) * np.sin(s * 2.3))

    def at(self, sv):
        i = int(np.clip(np.searchsorted(self.s, sv), 0, len(self.s) - 1))
        return self.P[i], self.T[i], self.B[i]


# gli anelli del collo: dalla nuca in giù, (distanza dal precedente, mezza larghezza, inclinazione) — irregolari come
# sui serpenti veri, non a passo fisso: un collo a strisce regolari sembrerebbe un palo da barbiere
ANELLI = ((0.11, 0.040, 0.10), (0.21, 0.034, -0.15), (0.27, 0.046, 0.05), (0.19, 0.030, 0.22), (0.26, 0.044, -0.08),
          (0.23, 0.050, 0.14), (0.30, 0.038, -0.20), (0.20, 0.046, 0.06), (0.25, 0.052, -0.12), (0.22, 0.040, 0.18),
          (0.28, 0.050, 0.0), (0.24, 0.046, -0.10), (0.26, 0.050, 0.12))


def bande_collo(collo, s_top, p):
    """Gli anelli neri attorno al collo, come sul serpente di mare a bande: girano tutto attorno, un po' storti e
    sghembi, più stretti sulla gola, che resta giallo chiaro; il bordo è appena frastagliato."""
    _, s, b, c = collo.query(p, lato=True)
    s = s + 0.005 * np.sin(p[:, 0] * 37.0 + p[:, 1] * 23.0) * np.sin(p[:, 2] * 19.0)
    gola = 0.70 + 0.30 * np.clip((b + 1.0) / 2.0, 0.0, 1.0)
    out = np.zeros(len(p), F)
    sk = s_top
    for passo, w, inc in ANELLI:
        sk -= passo
        r = float(collo.raggio(sk))
        out = np.maximum(out, 1.0 - D.smooth01(np.abs(s - sk + inc * r * c) - w * gola, -0.006, 0.006))
    return out, np.clip(0.5 - 0.6 * b, 0.0, 1.0) ** 1.5


def pinna(collo, s_top):
    """La pinna bassa lungo il dorso: una lama sottile che corre su tutto il collo, si abbassa verso la testa e muore
    poco dietro la nuca (come nella tavola)."""
    lama = sdf.ellipsoid(V(0, 0, 0), (0.0045, 0.024, 0.032))      # (di fianco, in altezza, lungo il collo)
    parts, pts = [], []
    for sv in np.arange(0.55, s_top - 0.12, 0.04):
        c, t, bk = collo.at(sv)
        h = 0.65 + 0.35 * min(1.0, (s_top - 0.12 - sv) / 0.4)
        q = c + bk * (float(collo.raggio(sv)) + 0.002)
        M = np.stack([np.cross(t, bk), bk, t], axis=1).astype(F)
        parts.append(entro(lambda p, q=q, M=M, h=h: lama(((p - q) @ M) / V(1.0, h, 1.0)) * h, q - 0.04, q + 0.04))
        pts.append(q)
    P = np.array(pts, F)
    return entro(sdf.union(*parts), P.min(0) - 0.05, P.max(0) + 0.05)


def branchie(collo, s_top):
    """Tre fessure per lato sul collo, sotto la nuca: corte lungo il collo, lunghe attorno."""
    slit = sdf.ellipsoid(V(0, 0, 0), (0.008, 0.026, 0.0055))      # (profondità, attorno al collo, lungo il collo)
    parts = []
    for j in range(3):
        sv = s_top - 0.17 - 0.034 * j
        c, t, bk = collo.at(sv)
        lat = np.cross(t, bk)
        for s in (-1, 1):
            q = c + lat * s * float(collo.raggio(sv)) - bk * 0.010
            M = np.stack([lat, bk, t], axis=1).astype(F)
            parts.append(lambda p, q=q, M=M: slit((p - q) @ M))
    return sdf.union(*parts)


def pieghe_arco(collo, s0, s1):
    """Le pieghe della pelle dentro l'arco, dove il collo si piega e la carne si schiaccia (sulla gola)."""
    def f(p):
        _, s, b = collo.query(p)
        m = D.smooth01(s, s0, s0 + 0.05) * (1.0 - D.smooth01(s, s1 - 0.05, s1)) * D.smooth01(-b, 0.2, 0.7)
        return (np.sin(s * 150.0) * 0.5 + 0.5) * m
    return f


# ───────────────────────── la trombetta da festa ─────────────────────────

def spirale(Lc, r_in=0.0095, passo=0.0105):
    """I giri della carta arrotolata: una spirale stretta (ogni giro più largo del passo) che contiene la lunghezza Lc,
    dal raggio di fuori a r_in (la punta, al centro). Restituisce i giri e il raggio di fuori."""
    if Lc <= 1e-4:
        return 0.0, r_in
    a = math.pi * passo
    b = 2 * math.pi * r_in
    n = (-b + math.sqrt(b * b + 4 * a * Lc)) / (2 * a)
    return n, r_in + passo * n


def trombetta(fr, srotolata=0.0):
    """La trombetta da festa fusa nelle labbra: il bocchino bianco che esce dalla bocca, poi la lingua di carta a
    strisce. srotolata = 0: la carta tutta arrotolata sotto il muso in una spirale stretta (schiacciata, com'è a
    riposo); 1: tutta distesa e gonfia, dritta sulla lampara (un filo cadente: la carta è bagnata), la piuma rosa in
    punta; in mezzo il primo tratto è disteso e gonfio, il resto ancora arrotolato in fondo. Le strisce stanno sulla
    carta ('tick', metri dal bocchino), così nelle varianti restano al loro posto."""
    k = K_CARTA
    s = min(max(float(srotolata), 0.0), 1.0)
    m0 = fr.pt(QB)
    d = unit(fr.dir(DB))
    down = unit(V(0, 0, -1) - (V(0, 0, -1) @ d) * d)
    side = unit(np.cross(d, down))
    obs = []
    # il bocchino: un cannello bianco con il collarino dove è incollata la carta
    m1 = m0 + d * 0.050
    boc = sdf.union(sdf.round_cone(m0 - d * 0.025, m1, 0.0080 * k, 0.0088 * k),
                    D.torus_axis(m1 - d * 0.006, d, 0.0088 * k, 0.0022 * k), k=0.002)
    obs.append(fine('ArchieMouthpiece', boc, [np.array([m0 - d * 0.03, m1 + d * 0.01], F)],
                    D.vinyl('PartyMouthpieceVinyl', (0.86, 0.84, 0.76)), pad=0.02, res=RES_FINE))
    # la carta: il tratto disteso (lungo d, un filo cadente) e poi la spirale che curva sotto
    Ls = s * CARTA_L
    path, a, b = [], [], []
    a_gonfia, b_gonfia = 0.0105 * k, 0.0098 * k            # gonfia: quasi tonda
    a_piatta, b_piatta = 0.0120 * k, 0.0032 * k            # arrotolata: schiacciata (e più larga)
    a_bocc = 0.0088 * k                                    # incollata al bocchino
    start = m1 - d * 0.008
    n1 = int(round(60 * s)) + 2 if Ls > 1e-4 else 0       # tutta arrotolata: la spirale parte dal bocchino
    droop = 0.020 * s
    for i in range(n1 + 1):
        t = i / max(n1, 1)
        path.append(start + d * (Ls * t) + down * (droop * t * t))
    tick = [Ls * i / max(n1, 1) for i in range(n1 + 1)]
    for tk in tick:
        g = D.smooth01(tk, 0.0, 0.035)                     # dal collarino si gonfia
        a.append(a_bocc + (a_gonfia - a_bocc) * g)
        b.append(a_bocc + (b_gonfia - a_bocc) * g)
    Lc = CARTA_L - Ls
    n, r_out = spirale(Lc)
    if n > 0:
        dd = unit(path[-1] - path[-2]) if n1 > 0 else d
        dn = unit(down - (down @ dd) * dd)
        c = path[-1] + dn * r_out
        passo = (r_out - 0.0095) / max(n, 1e-6)
        m = max(8, int(round(46 * n)))
        for i in range(1, m + 1):
            phi = 2 * math.pi * n * i / m
            r = r_out - passo * phi / (2 * math.pi)
            path.append(c + r * (-dn * math.cos(phi) + dd * math.sin(phi)))
            tick.append(tick[-1] + float(np.linalg.norm(path[-1] - path[-2])))
            # da gonfia a schiacciata nel primo quarto di giro (all'inizio, se è tutta arrotolata, dal bocchino)
            u = D.smooth01(phi, 0.0, 1.6)
            g0 = D.smooth01(tick[-1], 0.0, 0.035)
            a0 = a_bocc + (a_gonfia - a_bocc) * g0
            b0 = a_bocc + (b_gonfia - a_bocc) * g0
            a.append(a0 + (a_piatta - a0) * u)
            b.append(b0 + (b_piatta - b0) * u)
    P = np.array(path, F)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    ss = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    verts, faces, tk, ang = [], [], [], []
    seg = 20
    for i, (p, t) in enumerate(zip(P, T)):
        nn = np.cross(side, t)
        for j in range(seg):
            th = 2 * math.pi * j / seg
            verts.append(p + side * a[i] * math.cos(th) + nn * b[i] * math.sin(th))
            tk.append(ss[i])
            ang.append(j / seg)
    for i in range(len(P) - 1):
        for j in range(seg):
            q0, q1 = i * seg + j, i * seg + (j + 1) % seg
            faces.append((q0, q1, q1 + seg, q0 + seg))
    cidx = len(verts)
    verts.append(P[-1] + T[-1] * min(a[-1], b[-1]) * 0.6)  # la punta chiusa, appena tonda
    tk.append(ss[-1])
    ang.append(0.0)
    o = (len(P) - 1) * seg
    for j in range(seg):
        faces.append((o + j, o + (j + 1) % seg, cidx))
    ob = R.mesh_obj('ArchieBlower', verts, faces, TA.carta_festa('PartyPaper'), attrs={'tick': tk, 'ang': ang})
    obs.append(ob)
    # la piuma in fondo: ciocche rosa appiccicate dall'acqua. Arrotolata, la punta sta al centro della spirale e le
    # ciocche escono di fianco (in mezzo ai giri di carta non ci passano)
    end = P[-1]
    td = unit(P[-1] - P[-3])
    rng = np.random.default_rng(3)
    giro = min(1.0, n / 0.6)                               # quanto è arrotolata la punta
    ciocche, cp = [], []
    for i in range(12):
        v = unit(td + V(*rng.normal(0.0, 0.55, 3)))
        if giro > 0:
            v = unit(v * (1.0 - 0.7 * giro) + side * (1.0 if i % 2 else -1.0) * 1.2 * giro)
        Lp = rng.uniform(0.75, 1.0) * PIUMA_L
        pts = [end - td * 0.004, end + v * Lp * 0.5 + V(0, 0, -0.004), end + v * Lp + V(0, 0, -0.014)]
        ciocche.append(tubo(pts, 0.0032 * k, 0.0007 * k, n=5)[0])
        cp.append(np.array(pts, F))
    obs.append(fine('ArchieFeather', sdf.union(*ciocche, k=0.003), cp, TA.piuma_material(), pad=0.008, res=RES_FINE))
    return obs


# ───────────────────────── la melma ─────────────────────────

def bava(fr):
    """Melma gialla vera: un filo di bava tra le labbra all'angolo della bocca, gocce dalla punta della mascella e dal
    bocchino (dove la gola, gonfiandosi, non arriva: così nelle varianti non si muovono)."""
    fili = [(fr.pt((0.040, -0.088, -0.026)), fr.pt((0.041, -0.090, -0.040)), 0.004),
            (fr.pt((-0.040, -0.088, -0.026)), fr.pt((-0.041, -0.090, -0.040)), 0.004)]
    gocce = [(fr.pt((0.0, -0.198, -0.031)), 0.055), (fr.pt((0.022, -0.180, -0.030)), 0.030),
             (fr.pt((-0.004, -0.222, -0.024)), 0.040)]
    parts, pts = [], []
    for a, b_, sag in fili:
        parts.append(skin.strand(a, b_, sag, r=0.0016))
        pts += [a, b_, (a + b_) / 2 - V(0, 0, sag)]
    for a, L in gocce:
        parts.append(skin.drip(a, L, r0=0.0022, r1=0.0042))
        pts += [a, a - V(0, 0, L)]
    return fine('ArchieSlime', sdf.union(*parts), [np.array(pts, F)], TA.melma_gialla(), pad=0.012, res=RES_FINE)


# ───────────────────────── costruzione ─────────────────────────

def build(lampara=None, viewer=None, srotolata=0.0, fiato=0.0):
    """Archie nella posa della lampara, in coordinate locali. lampara: il centro del vetro della lampara (la
    trombetta la punta); viewer: dove guardano gli occhi (il pescatore). srotolata: la trombetta, da 0 (arrotolata)
    a 1 (tutta distesa); fiato: la gola, da 0 a 1 (gonfia). Gli occhi sono gli oggetti 'ArchieEye0' e 'ArchieEye1'.
    La pelle è tagliata in due mesh che combaciano: 'ArchieHead' (la testa fino alla nuca) e 'ArchieSkin' (il
    collo); le varianti cambiano solo la trombetta ('ArchieMouthpiece', 'ArchieBlower', 'ArchieFeather') e la testa."""
    P = dict(POSA)
    for key, v in (('lampara', lampara), ('viewer', viewer)):
        if v is not None:
            P[key] = v
    L, vw = V(*P['lampara']), V(*P['viewer'])
    yaw, pitch = orienta(L)
    fr = TA.Testa(tuple(map(float, HEAD)), pitch=pitch, yaw=yaw, k=K)
    hl, cut_l, g, (mouth_l, hole_l, nostril_l) = testa_campo(fiato)
    h = unit(V(*fr.dir(V(0, -1, 0))[:2], 0.0))
    side = unit(np.cross(V(0, 0, 1), h))
    pts = collo_punti(fr)
    collo = Collo(pts, side)
    s_top = float(collo.s[np.argmin(np.linalg.norm(collo.P - fr.pt(ATTACCO), axis=1))])
    neck = sdf.union(collo.campo, pinna(collo, s_top), k=0.008)
    neck = sdf.displace(neck, pieghe_arco(collo, s_top - 0.36, s_top - 0.02), -0.0022)
    neck = sdf.displace(neck, skin.bumps(41, 0.05, 0.0025), 1.0)
    head = entro(fr.field(hl), HEAD - 0.36, HEAD + 0.36)
    f = sdf.union(neck, head, k=0.03)
    gills = branchie(collo, s_top)
    f = sdf.subtract(f, sdf.union(gills, entro(fr.field(cut_l), HEAD - 0.32, HEAD + 0.32)), k=0.005)

    def colori(p):
        sec, ven = bande_collo(collo, s_top, p)
        vt, st, m = testa_colori(fr.local(p))
        return np.where(m, vt, ven).astype(F), np.where(m, st, sec).astype(F)
    cache = {}

    def get(p, i):
        key = (len(p), float(p[0, 0]), float(p[-1, 2]))
        if key not in cache:
            cache.clear()
            cache[key] = colori(p)
        return cache[key][i]

    def bocca(p):
        q = fr.local(p)
        m = np.maximum.reduce([(mouth_l(q) < 0.003).astype(F), (hole_l(q) < 0.004).astype(F), (nostril_l(q) < 0.002).astype(F)])
        return np.maximum(m, (gills(p) < 0.003).astype(F))
    attrs = {'ventre': lambda p: get(p, 0), 'seconda': lambda p: get(p, 1), 'mouth': bocca}
    # la testa: dentro una sfera, oltre il piano che taglia il collo poco prima dell'attacco
    tA, _ = collo_dir(fr)
    zona = sdf.intersect(entro(fr.field(sdf.sphere(V(0, -0.01, -0.03), 0.31)), HEAD - 0.45, HEAD + 0.45),
                         D.above(fr.pt(ATTACCO) - tA * 0.05, tA))
    pelle = TA.pelle_archie()
    obs = []
    ob = sdf_object('ArchieHead', sdf.intersect(f, zona), HEAD - 0.36, HEAD + 0.36, res=RES_HEAD, attrs=attrs, banded=True)
    ob.data.materials.append(pelle)
    obs.append(ob)
    Pn = np.array(pts, F)
    lo, hi = Pn.min(0) - 0.15, Pn.max(0) + 0.15
    lo[2] = -0.62
    ob = sdf_object('ArchieSkin', sdf.subtract(f, zona), lo, hi, res=RES_BODY, attrs=attrs, banded=True)
    ob.data.materials.append(pelle)
    obs.append(ob)
    for i, o in enumerate(OCCHI):
        e = fr.pt(o)
        obs.append(eyeball(f'ArchieEye{i}', tuple(map(float, e)), R_OCCHIO * K, skin.cloudy_eye(),
                           look=tuple(map(float, unit(vw - e)))))
    obs.append(denti(fr, g))
    obs += trombetta(fr, srotolata)
    obs.append(bava(fr))
    return obs


def testa_frame(lampara=None):
    """Il sistema locale della testa nella posa (serve alle inquadrature e al jumpscare)."""
    L = V(*(POSA['lampara'] if lampara is None else lampara))
    yaw, pitch = orienta(L)
    return TA.Testa(tuple(map(float, HEAD)), pitch=pitch, yaw=yaw, k=K)


# ───────────────────────── vetrina ─────────────────────────

def _set_barca():
    """Il pezzo di barca attorno ad Archie, nelle coordinate del gioco: scafo, capodibanda e coperta di prua, la
    lampara sul buttafuori (con le sue luci: è lei che lo illumina). Il mare un filo più basso del vero, come nella
    vetrina di Robin (a z = 0 passerebbe dentro la barca, sopra il pagliolo)."""
    import boat
    mats = boat.make_materials()
    obs = [boat.build_hull(mats)] + boat.build_structure(mats) + boat.build_lampara(mats)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.13))
    sea = bpy.context.object
    sea.data.materials.append(D.mat_simple('NightSea', (0.004, 0.012, 0.016), rough=0.06, spec=0.8))
    return obs


SHOTS = {
    # (riferimento, camera, bersaglio, lente): camera e bersaglio rispetto alla testa, nelle coordinate della barca
    # (la lampara è lì accanto: le camere stanno fuori dal suo cappello)
    'insieme': ('testa', (1.55, -1.75, -0.45), (-0.25, 0.05, -0.75), 24),
    'testa': ('testa', (-0.30, -0.70, -0.20), (-0.06, -0.02, -0.06), 45),
    'fuori': ('testa', (-1.75, 2.55, -0.45), (0.05, 0.0, -0.75), 28),
    'bocca': ('testa', (-0.12, -0.42, -0.10), (-0.13, -0.02, -0.06), 70),
}


def _argomento(nome, default=None):
    """Il valore che segue 'nome' sulla riga di comando (o default)."""
    return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else default


# la variante della vetrina (--srotolata, --fiato): a 0 è l'Archie di sempre
VARIANTE = {'srotolata': float(_argomento('--srotolata', 0.0)), 'fiato': float(_argomento('--fiato', 0.0))}


def scena_vetrina():
    """La scena della vetrina: Archie nella posa di gioco accanto alla prua (scena_creature.archie_posa), in un
    pezzo di barca con la lampara accesa; la luna fredda da dietro, poco riempimento; resa AgX. Restituisce i
    riferimenti delle inquadrature (la testa, nelle coordinate della barca)."""
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
    M, kw = SC.archie_posa()
    SC.place(build(**kw, **VARIANTE), M)
    h = np.array(M @ Vector(tuple(map(float, HEAD))))
    D.area_light('Rim', tuple(h + (2.2, 2.6, 1.6)), tuple(h + (0.0, 0.0, -0.4)), 260, (0.55, 0.72, 1.0), 0.8)
    D.area_light('Fill', tuple(h + (-0.6, -2.4, -0.4)), tuple(h + (0.0, 0.0, -0.4)), 14, (0.55, 0.65, 0.85), 1.6)
    return {'testa': h}


def showcase(shots=('insieme', 'testa', 'fuori', 'bocca')):
    """La vetrina: tools/render/cache/vetrina/archie_<inquadratura>.png (con una variante,
    archie_<inquadratura>_s<srotolata>_f<fiato>.png), e la tavola docs/concept/archie_vetrina.jpg."""
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
    sc.cycles.samples = 32 if FAST else 128
    sc.render.image_settings.file_format = 'PNG'
    os.makedirs(os.path.join(CACHE, 'vetrina'), exist_ok=True)
    coda = ''
    if any(VARIANTE.values()):
        coda = '_s{srotolata:g}_f{fiato:g}'.format(**VARIANTE)
    for name in shots:
        r, cl, ct, lens = SHOTS[name]
        c0 = ref[r]
        cam_d.lens = lens
        cam.location = tuple(c0 + cl)
        cam.rotation_mode = 'QUATERNION'
        cam.rotation_quaternion = (Vector(tuple(c0 + ct)) - Vector(tuple(c0 + cl))).to_track_quat('-Z', 'Y')
        path = os.path.join(CACHE, 'vetrina', f'archie_{name}{coda}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('ok', path, flush=True)
    if len(out) == 4 and not coda:
        tavola_vetrina(out)
    return out


def tavola_vetrina(paths=None, size=(480, 360)):
    """Le quattro inquadrature della vetrina in una tavola 2×2 → docs/concept/archie_vetrina.jpg."""
    if paths is None:
        paths = [os.path.join(CACHE, 'vetrina', f'archie_{n}.png') for n in ('insieme', 'testa', 'fuori', 'bocca')]
    W, H = size
    sheet = Image.new('RGB', (2 * W, 2 * H))
    for i, p in enumerate(paths):
        im = Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS)
        sheet.paste(im, ((i % 2) * W, (i // 2) * H))
    dst = os.path.join(ROOT, 'docs', 'concept', 'archie_vetrina.jpg')
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


def ingombro(obs):
    """Dove sta la posa vista dall'occhio del pescatore (per la regia del gioco): yaw e pitch minimi e massimi di
    tutti i pezzi ('tutto') e della parte che si vede davvero ('visibile': senza quello che lo scafo e il mare
    nascondono), dei pezzi principali, e dove stanno la testa, gli occhi e la punta della trombetta distesa."""
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
    vis = np.array(vis)
    # sotto il pelo dell'acqua non si vede (nel gioco il mare fa da maschera)
    vis &= pts[:, 2] > 0.0
    head = bpy.data.objects['ArchieHead'].matrix_world @ Vector(tuple(map(float, HEAD)))
    eyes = [o for o in meshes if 'Eye' in o.name]
    out = {
        'tutto': _span(pts),
        'visibile': _span(pts[vis]),
        'testa': _dir(head),
        'testa_m': [round(float(head[i] - EYE[i]), 3) for i in range(3)],
        'distanza_testa': round(float(math.dist(tuple(head), EYE)), 2),
        'quota_testa': round(float(head[2]), 2),
        'occhi': [_dir(o.matrix_world.translation) for o in eyes],
        'occhi_m': [[round(float(o.matrix_world.translation[i] - EYE[i]), 4) for i in range(3)] for o in eyes],
    }
    for k, n in (('testa_mesh', 'ArchieHead'), ('collo', 'ArchieSkin'), ('trombetta', 'ArchieBlower')):
        o = bpy.data.objects.get(n)
        if o:
            out[k] = _span(jobs.dense_points([o], n=2500))
    return out


def anteprima_posa():
    """Anteprima della posa archie_soffia senza toccare il gioco (come robin.anteprima_posa): la scena del gioco con
    la batteria (dalla notte 2 c'è sempre), la canna, la posa da scena_creature, e la camera prospettica dall'occhio
    del pescatore come la vista del gioco (90° di campo, guardando avanti un po' a destra della prua: dentro ci sono
    la lampara, Archie e la canna) e una più stretta sul mostro. Scrive docs/concept/pose_archie.jpg e
    pose_archie_vicino.jpg, e l'ingombro in cache/archie_posa.json."""
    import batteria
    import jobs
    import scena_creature as SC
    from common import perspective_camera
    jobs.build_scene(fish=5, rod=True)
    batteria.build_battery(needle=0.72)
    before = set(bpy.data.objects.keys())
    SC.POSES['archie_soffia'][0]()
    bpy.context.view_layer.update()
    new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
    info = ingombro(new)
    print('ingombro', json.dumps(info), flush=True)
    with open(os.path.join(CACHE, 'archie_posa.json'), 'w') as fh:
        json.dump(info, fh, indent=1)
    sc = bpy.context.scene
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.resolution_percentage = 100
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.cycles.samples = 32 if FAST else 64
    out = []
    hy, hp = info['testa']
    for name, (yaw, pitch, lens) in {
        'pose_archie': (6.0, -6.0, 18.0),
        'pose_archie_vicino': (hy + 1.0, hp - 6.0, 34.0),
    }.items():
        t = (EYE[0] + math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)),
             EYE[1] + math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)), EYE[2] + math.sin(math.radians(pitch)))
        perspective_camera(EYE, t, lens=lens, name='ArchieCam_' + name)
        path = os.path.join(CACHE, f'{name}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('pannello', path, flush=True)
    return out, info


def anteprima_tavole(paths=None):
    """Le anteprime della posa con la scritta «da approvare» → docs/concept/pose_archie.jpg e pose_archie_vicino.jpg
    (dai pannelli in cache, senza rifarli)."""
    paths = paths or [os.path.join(CACHE, f'{n}.png') for n in ('pose_archie', 'pose_archie_vicino')]
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    except OSError:
        font = ImageFont.load_default()
    out = []
    for p in paths:
        im = Image.open(p).convert('RGB')
        d = ImageDraw.Draw(im)
        txt = 'ARCHIE · posa archie_soffia · da approvare'
        d.rectangle((0, 0, int(d.textlength(txt, font=font)) + 24, 38), fill=(14, 14, 16))
        d.text((12, 7), txt, fill=(240, 190, 110), font=font)
        dst = os.path.join(ROOT, 'docs', 'concept', os.path.basename(p).replace('.png', '.jpg'))
        im.save(dst, quality=90)
        out.append(dst)
        print('anteprima', dst, flush=True)
    return out


# ───────────────────────── la tavola del jumpscare ─────────────────────────

def tavola_jumpscare(q='draft', tile=(320, 180), exposure=0.5):
    """I fotogrammi del jumpscare di Archie in una tavola 4×2, come le altre di docs/concept/jumpscare: ricomposti
    dagli EXR in cache/<qualità>/jumpscare (la creatura sopra lo sfondo, come fa jumpscare.run) e resi col tono del
    motore (post.tonemap). → docs/concept/jumpscare/js_archie_fotogrammi.jpg"""
    import post
    d = os.path.join(CACHE, q, 'jumpscare')
    bg = post.read_exr(os.path.join(d, 'archie_bg.exr'))
    bg_lin = sum(bg[g][..., :3] for g in ('ambient', 'lamp', 'lantern') if g in bg)
    W, H = tile
    sheet = Image.new('RGB', (4 * W, 2 * H))
    for i in range(8):
        p = post.read_exr(os.path.join(d, f'archie_{i:02d}.exr'))
        fg = sum(p[g][..., :3] for g in ('ambient', 'lamp', 'lantern') if g in p)
        a = p['alpha'][..., None] if 'alpha' in p else np.ones(fg.shape[:2] + (1,), np.float32)
        comp = fg + bg_lin * (1 - np.clip(a, 0, 1))
        im = Image.fromarray((post.tonemap(comp, exposure) * 255 + 0.5).astype(np.uint8), 'RGB').resize((W, H), Image.LANCZOS)
        sheet.paste(im, ((i % 4) * W, (i // 4) * H))
    dst = os.path.join(ROOT, 'docs', 'concept', 'jumpscare', 'js_archie_fotogrammi.jpg')
    sheet.save(dst, quality=90)
    print('tavola', dst, flush=True)
    return dst


if __name__ == '__main__':
    if '--posa' in sys.argv:
        anteprima_posa()
        anteprima_tavole()
    elif '--posa-tavole' in sys.argv:
        anteprima_tavole()
    elif '--jumpscare-tavola' in sys.argv:
        q = _argomento('--jumpscare-tavola', 'draft')
        tavola_jumpscare(q if q in ('draft', 'preview', 'final') else 'draft')
    elif '--vetrina-tavola' in sys.argv:
        tavola_vetrina()
    elif '--solo' in sys.argv:
        showcase(tuple(_argomento('--solo').split(',')))
    else:
        showcase()
