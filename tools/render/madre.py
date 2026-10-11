"""
LA MADRE (Mama Marina) — il modello, notte 6, il finale. Da approvare.

Le decisioni dell'11 ottobre (docs/NOTTI_E_MOSTRI.md, «Notte 6»): la sagoma B «Occhio» della tavola
(docs/concept/madre_sagome.png, tools/render/madre_sagome.py sul ramo claude/madre-sagome), il colore bianco latte, e
per il jumpscare la bocca della sagoma A con i fanoni come le sbarre di un lettino.

Una balena enorme, una trentina di metri, quasi tutta sott'acqua: la pelle liscia bianco latte, bagnata, con la stessa
melma degli altri mostri. Sopra c'è ancora la vernice della mascotte del parco (mascot.py: il blu del dorso, la pancia
crema, le guance rosa, il sorriso rosso scuro), che si stacca a grandi croste e lascia vedere il bianco sotto. Il
sorriso dipinto parte dall'angolo della bocca e sale fino sotto l'occhio; l'occhio è grande quanto la barca (4,4 m),
azzurro come quello della mascotte, con le ciglia da cartone animato; sullo sfiatatoio il ciuffo d'acqua della statua.
La testa ha la fronte tonda (il melone, come i beluga), la gola a pieghe (come le balenottere), e in bocca i fanoni
sono le sbarre di un lettino: tonde, dritte, in fila, verniciate di bianco e scrostate, unite in fondo da un corrimano.
Sotto, le due pinne ripiegate sul ventre stringono i suoi piccoli, come la statua coi pesciolini in grembo.

Coordinate (metri): la Madre guarda −Y, l'alto è +Z, il mare a riposo è z = 0 (nel gioco la posa la inclina e la
alza: scena_creature.madre_posa). Gli occhi stanno sui fianchi, in alto, sotto le arcate: quello che guarda la barca
è il destro (−X).

Le parti che si muovono (per le toppe e il jumpscare): build(bocca=…) apre la mandibola sulla cerniera (0 chiusa,
1 spalancata, BOCCA_MAX gradi), con i fanoni che si distendono; build(viewer=…) gira gli occhi verso il pescatore.

Uso: tools/.venv/bin/python tools/render/madre.py [--fast]                 tavola della testa → docs/concept/madre_testa.jpg
     tools/.venv/bin/python tools/render/madre.py [--fast] --posa          la posa di gioco vista dall'occhio, di notte e
                                                                           all'alba → docs/concept/madre_posa.jpg
     tools/.venv/bin/python tools/render/madre.py --jumpscare-tavola [draft|preview|final]   la tavola dei fotogrammi
                     del jumpscare dagli EXR in cache/<qualità>/jumpscare (fatti con JS_ANTEPRIMA=1 JUMPSCARES=madre
                     jobs.py jumpscare) → docs/concept/jumpscare/js_madre_fotogrammi.jpg
     --testa-tavola, --posa-tavola   rimontano le tavole dai pannelli già fatti
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

import dettagli as D  # noqa: E402
import sdf  # noqa: E402
import skin  # noqa: E402
import teste_fangy as TF  # noqa: E402  (tubi, palline, snap, melma)
from common import CACHE, EYE, ROOT, reset_scene, set_lightgroup  # noqa: E402
from creature import sdf_object  # noqa: E402
from geo import catmull  # noqa: E402
from nodes import material  # noqa: E402

V, F, unit = D.V, D.F, D.unit
FAST = '--fast' in sys.argv
RES_HEAD = 0.05 if FAST else 0.032        # la testa (fuori dall'acqua nella posa, e il jumpscare da vicino)
RES_BODY = 0.11 if FAST else 0.075        # il corpo, sempre sott'acqua
TAGLIO = 4.0                              # y del taglio fra la mesh della testa e quella del corpo

# ───────────────────────── misure ─────────────────────────

# l'occhio destro (quello verso la barca) e il suo asse: in alto sul fianco, girato in fuori e in su. Il centro sta
# dentro la testa (OCCHIO_DENTRO metri sotto la pelle, lungo l'asse): fuori resta una calotta larga quasi quattro metri,
# grande quanto la barca, bombata come quella dei cartoni animati
OCCHIO_ASSE = unit((-0.75, -0.12, 0.65))
OCCHIO_R = 2.2
OCCHIO_DENTRO = 1.15
APERTURA = math.sqrt(OCCHIO_R ** 2 - OCCHIO_DENTRO ** 2)   # il raggio della calotta che resta fuori
SFIATATOIO = V(0.0, -2.0, 1.62)
CERNIERA = V(0.0, -0.9, -3.6)              # dove si apre la mandibola (l'angolo della bocca)
BOCCA_MAX = 62.0                           # gradi, a bocca spalancata
GOLA = V(0.0, -1.2, -3.7)                  # il buco nero in fondo alla bocca


def gape(y):
    """Quota del taglio della bocca (la linea delle labbra) lungo la testa."""
    return -3.85 + 0.03 * (y + 12.0)


def occhi():
    """I due occhi (centro, asse): il destro (−X) e il sinistro, specchiato."""
    return [(OCCHIO, OCCHIO_ASSE), (OCCHIO * V(-1, 1, 1), OCCHIO_ASSE * V(-1, 1, 1))]


def base_occhio(a):
    """Due assi perpendicolari all'asse dell'occhio: u in orizzontale, v verso l'alto."""
    v = V(0, 0, 1) - a * float(a[2])
    v = unit(v)
    u = unit(np.cross(v, a))
    return u, v


# ───────────────────────── i campi ─────────────────────────

def _testa_base():
    """Il cranio, il melone della fronte, il muso."""
    head = sdf.ellipsoid(V(0, -4.0, -2.4), (4.6, 7.2, 4.3))
    melon = sdf.ellipsoid(V(0, -7.6, -0.6), (3.8, 4.4, 3.1))
    snout = sdf.ellipsoid(V(0, -9.8, -3.1), (3.4, 3.4, 1.4))
    return sdf.union(head, melon, snout, k=1.4)


def _testa_intera():
    """La testa senza il taglio della bocca, con le arcate sopra gli occhi e le palpebre."""
    f = _testa_base()
    brows = []
    for c, a in occhi():
        u, v = base_occhio(a)
        brows.append(TF.ellipsoid_axes(c + v * (APERTURA + 0.25) + a * (OCCHIO_DENTRO - 0.2), (2.6, 0.9, 0.7), u, v, a))
    return sdf.union(f, *brows, k=1.0)


def _occhio():
    """Il centro dell'occhio: dove l'asse (da un punto in mezzo alla testa) esce dalla pelle, meno OCCHIO_DENTRO."""
    f = _testa_base()
    o = V(-1.2, -4.6, -1.2)
    t = np.linspace(0.0, 6.0, 601)
    P = (o + t[:, None] * OCCHIO_ASSE).astype(F)
    s = float(t[np.where(f(P) < 0)[0].max()])
    return (o + OCCHIO_ASSE * (s - OCCHIO_DENTRO)).astype(F)


def _palpebre(f):
    """L'orbita e le palpebre: l'orlo di carne attorno alla calotta dell'occhio, la palpebra di sopra pesante (copre
    un po' l'occhio, come una mamma che guarda il figlio), quella di sotto più sottile."""
    lids = []
    for c, a in occhi():
        u, v = base_occhio(a)
        lids.append(D.torus_axis(c + a * OCCHIO_DENTRO, a, APERTURA + 0.05, 0.30))
        lids.append(TF.ellipsoid_axes(c + a * (OCCHIO_DENTRO + 0.25) + v * (APERTURA - 0.35), (2.1, 0.65, 0.70), u, v, a))
        lids.append(TF.ellipsoid_axes(c + a * (OCCHIO_DENTRO - 0.05) - v * (APERTURA - 0.05), (1.7, 0.30, 0.38), u, v, a))
    f = sdf.union(f, *lids, k=0.40)
    holes = sdf.union(*[sdf.sphere(c, OCCHIO_R + 0.05) for c, _ in occhi()])
    return sdf.subtract(f, holes, k=0.10)


OCCHIO = _occhio()


def _sopra(p):
    """Semispazio sopra le labbra (negativo dentro)."""
    return (gape(p[:, 1]) - p[:, 2]).astype(F)


def _sotto(p):
    return (p[:, 2] - gape(p[:, 1])).astype(F)


def _pieghe(f, centro_z, amp=0.05, passo=0.55):
    """La gola a pieghe: solchi lungo la testa, sotto (come le balenottere)."""
    def g(p):
        d = f(p)
        m = np.clip((centro_z - p[:, 2]) / 1.2, 0, 1)
        return (d + amp * m * (0.5 - 0.5 * np.cos(2 * math.pi * p[:, 0] / passo))).astype(F)
    return g


def mandibola():
    """La mandibola chiusa (nel suo sistema, che a bocca chiusa è quello della Madre): larga e piena, la gola a pieghe
    sotto, scavata dentro, con la lingua."""
    jaw = sdf.ellipsoid(V(0, -5.6, -4.4), (4.5, 7.4, 2.6))
    chin = sdf.ellipsoid(V(0, -10.6, -4.2), (3.0, 2.6, 1.3))
    outer = sdf.union(jaw, chin, k=1.0)
    outer = _pieghe(outer, -4.6)
    low = sdf.intersect(outer, _sotto, k=0.25)
    cavity = sdf.ellipsoid(V(0, -5.4, -3.5), (3.8, 6.6, 2.4))
    tongue = sdf.ellipsoid(V(0, -3.6, -4.9), (2.5, 4.4, 1.1))
    low = sdf.subtract(low, cavity, k=0.3)
    return sdf.union(low, tongue, k=0.6), outer


def corpo():
    """Il corpo che va giù dietro la testa, la gola gonfia, la gobba, la coda con le pinne, e le due pinne
    ripiegate sul ventre (i piccoli sono a parte, piccoli())."""
    throat = _pieghe(sdf.ellipsoid(V(0, 3.0, -4.6), (4.5, 4.5, 3.4)), -5.6)
    body = D.chain([V(0, 2.0, -2.7), V(0, 6.0, -3.0), V(0, 10.0, -3.6), V(0, 13.5, -4.1), V(0, 16.2, -4.4), V(0, 18.0, -4.5)],
                   [4.7, 4.6, 3.9, 2.6, 1.3, 0.7], k=1.2)
    hump = sdf.ellipsoid(V(0, 11.0, -0.1), (0.55, 1.8, 0.6))
    flukes = []
    for s in (-1, 1):
        flukes.append(TF.ellipsoid_axes(V(s * 2.6, 19.0, -4.5), (3.4, 1.15, 0.26), V(s, 0.45, 0), V(-0.45 * s, 1, 0), V(0, 0, 1)))
    f = sdf.union(body, throat, hump, *flukes, k=0.9)
    return sdf.union(f, *pinne(), k=0.9)


def pinne():
    """Le pinne ripiegate sotto il ventre come braccia che cullano: dal fianco scendono e girano verso il mezzo, col
    bordo davanti a bitorzoli (come le megattere)."""
    out = []
    for s in (-1, 1):
        pts = [V(s * 4.1, -0.4, -5.0), V(s * 4.0, 1.4, -7.4), V(s * 2.6, 3.3, -8.7), V(s * 0.8, 5.0, -8.6)]
        fin = D.chain(pts, [1.05, 0.95, 0.75, 0.45], k=0.5)
        # appiattita: tolta la carne sopra e sotto di un piano che segue la pinna
        knobs = [sdf.sphere(p + V(-s * 0.1, -0.55, 0.15), 0.32 - 0.05 * i) for i, p in enumerate(catmull(pts, 2)[1:6])]
        out.append(sdf.union(fin, *knobs, k=0.25))
    return out


def piccoli_campo():
    """I piccoli: quattro bambini rannicchiati fra le pinne e il ventre, la testa contro la pancia della Madre."""
    out = []
    for i, (x, y) in enumerate(((-1.5, 2.6), (1.4, 3.0), (-0.6, 4.3), (0.8, 5.1))):
        c = V(x, y, -7.95)
        s = 1.15 - 0.05 * i
        up = unit((0.15 * np.sign(x), 0.2, 1.0))
        fw = unit(np.cross(up, V(1, 0, 0)) * (1 if i % 2 else -1))
        head = sdf.sphere(c + up * 0.42 * s, 0.15 * s)
        body = D.chain([c + up * 0.27 * s, c - up * 0.12 * s], [0.12 * s, 0.10 * s], k=0.04)
        knee = c + fw * 0.30 * s
        legs = D.chain([c - up * 0.12 * s, knee + up * 0.05 * s, knee - up * 0.25 * s], [0.06 * s, 0.05 * s, 0.04 * s], k=0.03)
        arms = D.chain([c + up * 0.24 * s, c + fw * 0.26 * s + up * 0.08 * s, knee + up * 0.10 * s], [0.045 * s, 0.04 * s, 0.035 * s], k=0.03)
        out.append(sdf.union(head, body, legs, arms, k=0.05 * s))
    return sdf.union(*out)


class Campo:
    """La pelle della Madre con la bocca aperta di `bocca` (0..1): il campo, i pezzi per gli attributi, il sistema
    della mandibola."""

    def __init__(self, bocca=0.0):
        self.bocca = float(bocca)
        self.alpha = BOCCA_MAX * self.bocca
        self.Rj = sdf.rot_matrix('x', self.alpha)
        self.intera = _palpebre(_testa_intera())
        upper = sdf.intersect(self.intera, _sopra, k=0.3)
        low, self.jaw_outer = mandibola()
        self.low_local = low
        self.body = corpo()
        rest = sdf.union(upper, self.body, k=1.0)
        gola = sdf.ellipsoid(GOLA, (1.3, 1.7, 1.1))
        rest = sdf.subtract(rest, gola, k=0.3)
        self.upper = upper
        f = sdf.union(rest, self.low, k=0.15 if self.bocca < 0.05 else 0.5)
        if self.bocca < 0.05:
            # a bocca chiusa: il solco delle labbra, appena sotto la pelle
            closed = f

            def groove(p):
                return np.maximum(np.maximum(np.abs(p[:, 2] - gape(p[:, 1])) - 0.07, -(closed(p) + 0.35)), p[:, 1] - CERNIERA[1]).astype(F)
            f = sdf.subtract(f, groove, k=0.05)
        self.f = f

    def to_jaw(self, p):
        """Dal mondo della Madre al sistema della mandibola chiusa."""
        return ((p - CERNIERA) @ self.Rj + CERNIERA).astype(F)

    def jaw_pt(self, q):
        """Un punto della mandibola chiusa → dove sta con la bocca aperta."""
        return (CERNIERA + self.Rj @ (V(*q) - CERNIERA)).astype(F)

    def low(self, p):
        return self.low_local(self.to_jaw(p))

    # ── attributi della pelle (vernice e bocca), valutati sui vertici ──

    def is_jaw(self, p):
        return self.low(p) < np.minimum(self.upper(p), self.body(p)) + 0.02

    def attr_mouth(self, p):
        """1 dentro la bocca: il palato (la faccia del taglio), la cavità della mandibola, la lingua, la gola."""
        up = np.clip((-self.intera(p) - 0.25) / 0.2, 0, 1) * (np.abs(_sopra(p)) < 0.25)
        q = self.to_jaw(p)
        lowm = np.clip((-self.jaw_outer(q) - 0.2) / 0.2, 0, 1) * self.is_jaw(p)
        gola = np.clip(1.4 - np.linalg.norm((p - GOLA) / V(1.3, 1.7, 1.1), axis=1), 0, 1)
        return np.clip(np.maximum(np.maximum(up, lowm), gola), 0, 1).astype(F)

    def attr_gola(self, p):
        return np.clip((1.45 - np.linalg.norm((p - GOLA) / V(1.3, 1.7, 1.1), axis=1)) / 0.3, 0, 1).astype(F)

    def attr_ventre(self, p):
        """La pancia crema della mascotte: tutta la mandibola e la gola, e sotto il corpo."""
        zl = np.where(p[:, 1] < 2.0, -4.2, -4.2 - 0.12 * (p[:, 1] - 2.0))
        body = np.clip((zl - p[:, 2]) / 0.25 + 0.5, 0, 1)
        return np.maximum(body, self.is_jaw(p).astype(F)).astype(F)

    def attr_guancia(self, p):
        """Le guance rosa: un tondo sotto e dietro ogni occhio, sopra l'angolo della bocca."""
        out = np.zeros(len(p), F)
        for s in (-1, 1):
            c = V(s * 4.0, -2.2, -1.9)
            out = np.maximum(out, np.exp(-np.sum((p - c) ** 2, axis=1) / 1.25 ** 2))
        return np.clip(out * 1.6 - 0.25, 0, 1).astype(F)

    def sorriso_punti(self):
        """Il sorriso dipinto: dall'angolo della bocca sale e si arriccia fino sotto l'occhio (posato sulla pelle)."""
        out = []
        for s in (-1, 1):
            want = catmull([V(s * 3.4, -11.5, -3.75), V(s * 4.3, -6.0, -3.6), V(s * 4.55, -1.4, -3.3), V(s * 4.55, -0.9, -2.4),
                            V(s * 4.4, -1.8, -1.55), V(s * 4.1, -3.0, -1.25)], 10)
            pts, _ = TF.snap(self.f if self.bocca < 0.05 else Campo(0.0).f, want)
            out.append(pts)
        return out

    def attr_sorriso(self, p):
        """Il sorriso rosso scuro, largo una trentina di centimetri, più sottile in punta."""
        if not hasattr(self, '_sorr'):
            self._sorr = self.sorriso_punti()
        q = p
        if self.bocca >= 0.05:
            # sulla mandibola il sorriso va con lei (nel sistema chiuso)
            q = np.where(self.is_jaw(p)[:, None], self.to_jaw(p), p)
        out = np.zeros(len(p), F)
        for pts in self._sorr:
            n = len(pts)
            w = np.linspace(0.20, 0.11, n)
            for i in range(n - 1):
                a, b = pts[i], pts[i + 1]
                ab = b - a
                t = np.clip(((q - a) @ ab) / float(ab @ ab), 0, 1)
                d = np.linalg.norm(q - (a + t[:, None] * ab), axis=1)
                ww = w[i] + (w[i + 1] - w[i]) * t
                out = np.maximum(out, np.clip((ww - d) / 0.03, 0, 1))
        return out.astype(F)


# ───────────────────────── i pezzi ─────────────────────────

def fanoni(c: Campo):
    """I fanoni come le sbarre di un lettino: in fila lungo i due lati del palato, dritti, tondi, uniti in fondo da un
    corrimano. Pendono dalla mascella; a bocca chiusa sono corti e piegati dentro la mandibola, a bocca aperta si
    distendono fino a dove arriva la mandibola. Restituisce le curve per TF.tubes (sbarre e corrimano)."""
    bars, rails = [], []
    apri = min(1.0, c.bocca * 1.6)
    for s in (-1, 1):
        ends = []
        for y in np.arange(-11.2, -1.4, 0.34):
            z0 = gape(y) + 0.05
            # il bordo del palato a questa y: dove finisce la testa, sopra le labbra
            xs = np.linspace(0.0, 5.0, 101)
            P = np.stack([s * xs, np.full_like(xs, y), np.full_like(xs, z0)], axis=1).astype(F)
            inside = c.intera(P) < 0
            if not inside.any():
                continue
            edge = float(xs[np.where(inside)[0].max()])
            x = s * max(edge - 0.85, 0.3)
            top = V(x, y, z0 + 0.15)
            # quanto è lungo: di più a metà del palato, e non oltre la mandibola aperta
            t = (y + 11.2) / 9.8
            L = 2.1 + 0.6 * math.sin(math.pi * t)
            d = float(np.linalg.norm(top[1:] - CERNIERA[1:]))
            L = min(L, 0.85 * d * math.sin(math.radians(max(c.alpha, 1.0))) + 0.4)
            L = 0.35 + (L - 0.35) * apri
            down = unit((-s * 0.06, 0.0, -1.0))
            pts = np.array([top + down * L * k for k in np.linspace(0, 1, 6)])
            rr = np.linspace(0.085, 0.07, 6)
            bars.append((pts, rr))
            ends.append(pts[-1])
        if apri > 0.2 and len(ends) > 2:
            E = np.array(ends)
            rails.append((catmull(E, 3), np.full(len(catmull(E, 3)), 0.105)))
    return bars, rails


def ciglia():
    """Le ciglia da cartone animato (come la mascotte): tre per occhio, grosse, nere e lucide, sull'orlo della palpebra
    di sopra verso la coda; escono dall'occhio e si arricciano all'indietro e in su, come una falce."""
    out = []
    for c, a in occhi():
        u, v = base_occhio(a)
        back = V(0, 1, 0) - a * float(a[1])
        back = unit(back)
        R = APERTURA + 0.30
        for th, L in ((55.0, 2.3), (85.0, 2.7), (115.0, 2.3)):
            t = math.radians(th)
            r = unit(math.cos(t) * back + math.sin(t) * v)
            b = c + a * (OCCHIO_DENTRO + 0.30) + r * R
            p1 = b + r * L * 0.40 + a * L * 0.08
            p2 = p1 + r * L * 0.25 + back * L * 0.10 + a * L * 0.10
            p3 = p2 + back * L * 0.25 + a * L * 0.05 - r * L * 0.02
            P = catmull([b - r * 0.3, b, p1, p2, p3], 5)
            n = len(P)
            out.append((P, 0.30 * (1.0 - 0.90 * (np.arange(n) / (n - 1)) ** 1.4)))
    return out


def spruzzo():
    """Il ciuffo d'acqua dello sfiatatoio, come quello della statua: una colonna che sale e ricade a ombrello in nove
    getti, con le gocce in punta e intorno. Curve per TF.tubes e centri e raggi delle gocce."""
    rng = np.random.default_rng(3)
    base = SFIATATOIO + V(0, 0, -0.1)
    top = base + V(0.0, -0.10, 2.5)
    col = (np.array([base, base + V(0, -0.02, 0.6), base + V(0, -0.05, 1.3), top]), np.array([0.30, 0.24, 0.20, 0.17]))
    curves, drops, rads = [col], [], []
    for k in range(9):
        ang = 2 * math.pi * k / 9 + 0.3
        d = V(math.cos(ang), math.sin(ang), 0)
        h = rng.uniform(0.25, 0.45)
        P = catmull([top, top + d * 0.6 + V(0, 0, h * 1.3), top + d * 1.35 + V(0, 0, h * 0.3), top + d * 1.7 - V(0, 0, 0.8)], 5)
        n = len(P)
        curves.append((P, 0.13 * (1.0 - 0.6 * np.arange(n) / (n - 1))))
        for j in range(3):
            drops.append(P[-1] + d * rng.uniform(0.0, 0.25) + V(0, 0, -0.15 - 0.35 * j) + rng.normal(0, 0.06, 3))
            rads.append(rng.uniform(0.05, 0.09))
    for _ in range(25):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.2, 1.3)
        drops.append(top + V(math.cos(a) * r, math.sin(a) * r, rng.uniform(-1.2, 0.4)))
        rads.append(rng.uniform(0.025, 0.06))
    return curves, drops, rads


# ───────────────────────── materiali ─────────────────────────

LATTE = (0.86, 0.86, 0.84)                 # il bianco latte della pelle
LATTE_OMBRA = (0.70, 0.72, 0.73)           # le chiazze grigio perla
VENA = (0.48, 0.55, 0.66)                  # le vene azzurrine sotto la pelle
BLU = (0.035, 0.13, 0.46)                  # il blu della mascotte, sbiadito (mascot.py: 0.20, 0.36, 0.62)
CREMA = (0.80, 0.58, 0.30)                 # la pancia crema
ROSA = (0.80, 0.30, 0.36)                  # le guance
ROSSO = (0.26, 0.025, 0.04)                # il sorriso e le labbra
CARNE = (0.36, 0.12, 0.13)                 # dentro la bocca
SPORCO = (0.16, 0.17, 0.10)                # lo sporco e l'alga sotto l'orlo delle croste
MELMA = (0.84, 0.93, 0.72)                 # la stessa melma verdognola degli altri


def pelle_madre():
    """La pelle bianco latte, liscia e bagnata, con la vernice della mascotte sopra che si stacca a grandi croste.
    Attributi: 'ventre', 'guancia', 'sorriso', 'mouth', 'gola'. Coordinate dell'oggetto in metri."""
    m = bpy.data.materials.get('MadreSkinMat')
    if m:
        return m
    m, g = material('MadreSkinMat')
    co = g.texcoord('Object')
    # ── la pelle: bianco latte, chiazze grigio perla appena accennate, vene azzurrine, graffi chiari ──
    n1 = g.noise(co, scale=0.32, detail=4.0, rough=0.55, distortion=0.4)
    pelle = g.mix(g.mul(g.smoothstep(0.52, 0.72, n1.fac), 0.55), LATTE, LATTE_OMBRA)
    n2 = g.noise(co, scale=1.6, detail=3.0, rough=0.6)
    pelle = g.mix(g.mul(g.smoothstep(0.58, 0.72, n2.fac), 0.30), pelle, LATTE_OMBRA)
    warp = g.vmath('ADD', co, g.vmath('SCALE', n1.color, scale=0.6))
    vv = g.voronoi(warp, scale=0.9, feature='DISTANCE_TO_EDGE')
    pelle = g.mix(g.mul(g.smoothstep(0.035, 0.0, vv), 0.35), pelle, VENA)
    scr = g.noise(g.mapping(co, scale=(9.0, 0.35, 9.0)), scale=1.0, detail=3.0, rough=0.5)
    pelle = g.mix(g.mul(g.smoothstep(0.66, 0.70, scr.fac), 0.5), pelle, (0.92, 0.91, 0.88))
    # ── la vernice della mascotte: blu sopra, crema sotto, guance rosa, il sorriso ──
    ven, gua, sor = g.attr('ventre'), g.attr('guancia'), g.attr('sorriso')
    mouth, gola = g.attr('mouth'), g.attr('gola')
    vern = g.mix(g.smoothstep(0.3, 0.7, ven), BLU, CREMA)
    vern = g.mix(g.mul(gua, 0.85), vern, ROSA)
    vern = g.mix(sor, vern, ROSSO)
    # sbiadita a chiazze dal sole e dal sale, e screpolata (la crettatura delle vernici vecchie)
    fade = g.noise(co, scale=0.9, detail=3.0, rough=0.5)
    vern = g.mix(g.mul(g.smoothstep(0.50, 0.80, fade.fac), 0.30), vern, (0.55, 0.62, 0.70))
    crack = g.voronoi(g.vmath('ADD', co, g.vmath('SCALE', fade.color, scale=0.3)), scale=1.7, feature='DISTANCE_TO_EDGE')
    crepa = g.mul(g.smoothstep(0.012, 0.003, crack), g.smoothstep(0.4, 0.6, fade.fac))
    vern = g.mix(g.mul(crepa, 0.55), vern, SPORCO)
    # dove resta la vernice: grandi croste di un paio di metri, staccate cella per cella (più scrostata a chiazze
    # larghe), con l'orlo frastagliato e qualche scaglia più piccola saltata dentro le croste; mai dentro la bocca
    sto = g.noise(co, scale=0.7, detail=6.0, rough=0.7)
    wco = g.vmath('ADD', co, g.vmath('SCALE', g.vmath('SUBTRACT', sto.color, (0.5, 0.5, 0.5)), scale=2.2))
    rnd = g.bw(g.voronoi(wco, scale=0.42, feature='F1', out='Color'))
    quanta = g.noise(co, scale=0.11, detail=2.0)
    p = g.map_range(quanta.fac, 0.35, 0.65, 0.47, 0.66)
    # l'orlo frastagliato: la soglia mossa da un rumore fine, così le croste non sono piastrelle
    fine = g.noise(co, scale=7.0, detail=4.0, rough=0.7)
    resta = g.smoothstep(p, g.add(p, 0.004), g.add(rnd, g.mul(g.sub(fine.fac, 0.5), 0.06)))
    rnd2 = g.bw(g.voronoi(wco, scale=1.9, feature='F1', out='Color'))
    resta = g.mul(resta, g.smoothstep(0.07, 0.075, g.add(rnd2, g.mul(g.sub(fine.fac, 0.5), 0.05))))
    resta = g.mul(resta, g.sub(1.0, g.smoothstep(0.2, 0.5, mouth)))
    # l'orlo delle croste: la vernice alzata più chiara, e sulla pelle appena scoperta una riga di sporco
    vicino = g.bw(g.voronoi(g.vmath('ADD', wco, (0.06, 0.04, 0.05)), scale=0.42, feature='F1', out='Color'))
    resta_v = g.smoothstep(p, g.add(p, 0.004), g.add(vicino, g.mul(g.sub(fine.fac, 0.5), 0.06)))
    alzata = g.mul(resta, g.sub(1.0, resta_v))
    orlo = g.mul(g.sub(1.0, resta), resta_v)
    vern = g.mix(g.mul(alzata, 0.5), vern, (0.85, 0.86, 0.84))
    col = g.mix(resta, pelle, vern)
    col = g.mix(g.mul(orlo, 0.65), col, SPORCO)
    # ── dentro la bocca: carne scura, la gola nera ──
    carne = g.mix(g.smoothstep(0.55, 0.75, g.noise(co, scale=1.4, detail=3.0).fac), CARNE, (0.22, 0.06, 0.07))
    carne = g.mix(gola, carne, (0.006, 0.003, 0.003))
    col = g.mix(g.smoothstep(0.2, 0.6, mouth), col, carne)
    ao = g.ao(distance=0.6, samples=8)
    col = g.mix(g.sub(1.0, ao), col, (0.30, 0.30, 0.34), blend='MULTIPLY')
    # ── la melma: chiazze lucide, colature verso il basso, ristagni nelle pieghe; dappertutto un velo bagnato ──
    patch = g.noise(co, scale=0.9, detail=4.0, rough=0.55, distortion=0.7)
    pm = g.smoothstep(0.50, 0.60, patch.fac)
    streak = g.noise(g.mapping(co, scale=(6.0, 6.0, 0.55)), scale=1.0, detail=3.0, rough=0.5, distortion=0.3)
    dm = g.mul(g.smoothstep(0.56, 0.68, streak.fac), 0.9)
    cm = g.mul(g.smoothstep(0.25, 0.55, g.sub(1.0, ao)), 0.8)
    sl = g.clamp01(g.mx(g.mx(pm, dm), g.mx(cm, g.mul(mouth, 0.8))))
    col = g.mix(g.mul(sl, 0.25), col, (MELMA[0] * 0.9, MELMA[1] * 0.9, MELMA[2] * 0.85), blend='MULTIPLY')
    r = g.mixf(resta, 0.30, 0.55)
    r = g.mixf(sl, r, 0.07)
    # il rilievo: lo spessore della vernice (lo scalino all'orlo delle croste), le crepe, la grana della pelle
    grain = g.noise(co, scale=14.0, detail=3.0, rough=0.6)
    h = g.add(g.mul(resta, 1.0), g.add(g.mul(alzata, 0.9), g.mul(crepa, -0.25)))
    h = g.add(h, g.mul(grain.fac, 0.12))
    nrm = g.bump(h, strength=0.55, distance=0.012)
    bub = g.voronoi(co, scale=26.0, feature='F1')
    coat_n = g.bump(g.add(g.mul(sl, 0.8), g.mul(g.mul(g.smoothstep(0.22, 0.05, bub), pm), 0.25)), strength=0.3, distance=0.01)
    g.output_material(g.principled(color=col, rough=r, coat=g.add(0.35, g.mul(sl, 0.6)), coat_rough=g.mixf(sl, 0.10, 0.025),
                                   coat_tint=MELMA, coat_normal=coat_n, sss=0.12, sss_radius=(1.0, 0.55, 0.40),
                                   sss_scale=0.06, normal=nrm))
    return m


def occhio_madre():
    """L'occhio azzurro della mascotte, ma vero: il bianco lattiginoso con le venuzze, l'iride azzurra a raggi,
    la pupilla nera grande, tutto bagnato. Coordinate dell'oggetto: sfera di raggio 1, guarda −Y."""
    m = bpy.data.materials.get('MadreEye')
    if m:
        return m
    m, g = material('MadreEye')
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    r = g.vmath('LENGTH', g.comb(x, z, 0.0))
    front = g.smoothstep(0.1, -0.3, y)
    iris = g.mul(g.smoothstep(0.56, 0.52, r), front)
    pupil = g.mul(g.smoothstep(0.30, 0.27, r), front)
    ang = g.math('ARCTAN2', z, x)
    rays = g.noise(g.comb(g.mul(ang, 6.0), g.mul(r, 4.0), 0.0), scale=3.0, detail=4.0, rough=0.6)
    irc = g.mix(g.smoothstep(0.35, 0.7, rays.fac), (0.02, 0.12, 0.36), (0.10, 0.48, 0.85))
    irc = g.mix(g.smoothstep(0.44, 0.55, r), irc, (0.01, 0.04, 0.12))
    sclera = g.mix(g.smoothstep(0.6, 1.0, r), (0.80, 0.80, 0.76), (0.72, 0.62, 0.58))
    vn = g.noise(co, scale=3.0)
    vv = g.voronoi(g.vmath('ADD', co, g.vmath('SCALE', vn.color, scale=0.35)), scale=3.0, feature='DISTANCE_TO_EDGE')
    vene = g.mul(g.mul(g.smoothstep(0.018, 0.0, vv), g.smoothstep(0.62, 0.95, r)), g.smoothstep(0.45, 0.6, vn.fac))
    sclera = g.mix(g.mul(vene, 0.8), sclera, (0.50, 0.10, 0.10))
    col = g.mix(iris, sclera, irc)
    col = g.mix(pupil, col, (0.004, 0.004, 0.006))
    g.output_material(g.principled(color=col, rough=0.25, coat=1.0, coat_rough=0.015, spec=0.6, sss=0.08,
                                   sss_radius=(1.0, 0.6, 0.5), sss_scale=0.05))
    return m


def ciglia_material():
    m = bpy.data.materials.get('MadreLash')
    if m:
        return m
    m, g = material('MadreLash')
    co = g.texcoord('Object')
    n = g.noise(co, scale=3.0, detail=3.0)
    g.output_material(g.principled(color=(0.012, 0.012, 0.016), rough=0.30, coat=0.8, coat_rough=0.04, coat_tint=MELMA,
                                   normal=g.bump(n.fac, strength=0.2, distance=0.01)))
    return m


def fanoni_material():
    """Le sbarre del lettino: vernice bianca smaltata, scheggiata (sotto il corno scuro del fanone), con la melma."""
    m = bpy.data.materials.get('MadreBaleen')
    if m:
        return m
    m, g = material('MadreBaleen')
    co = g.texcoord('Object')
    chips = g.noise(co, scale=3.5, detail=5.0, rough=0.65)
    chip = g.smoothstep(0.60, 0.63, chips.fac)
    col = g.mix(chip, (0.80, 0.79, 0.74), (0.07, 0.055, 0.045))
    streak = g.noise(g.mapping(co, scale=(5.0, 5.0, 0.6)), scale=1.0, detail=3.0)
    col = g.mix(g.mul(g.smoothstep(0.55, 0.75, streak.fac), 0.5), col, (0.30, 0.32, 0.20))
    g.output_material(g.principled(color=col, rough=g.mixf(chip, 0.28, 0.55), coat=0.7, coat_rough=0.04, coat_tint=MELMA,
                                   normal=g.bump(chip, strength=0.4, distance=0.006)))
    return m


def acqua_material():
    m = bpy.data.materials.get('MadreSpray')
    if m:
        return m
    m, g = material('MadreSpray')
    co = g.texcoord('Object')
    n = g.noise(co, scale=6.0, detail=3.0)
    g.output_material(g.principled(color=(0.80, 0.90, 0.92), rough=0.06, transmission=0.55, ior=1.33, sss=0.5,
                                   sss_radius=(0.8, 0.9, 1.0), sss_scale=0.05, coat=0.6,
                                   normal=g.bump(n.fac, strength=0.5, distance=0.02)))
    return m


def piccoli_material():
    m = bpy.data.materials.get('MadreKids')
    if m:
        return m
    m, g = material('MadreKids')
    co = g.texcoord('Object')
    n = g.noise(co, scale=4.0, detail=4.0)
    col = g.mix(g.smoothstep(0.45, 0.7, n.fac), (0.40, 0.43, 0.40), (0.22, 0.25, 0.22))
    g.output_material(g.principled(color=col, rough=0.45, coat=0.6, coat_rough=0.05, coat_tint=MELMA, sss=0.2,
                                   sss_radius=(1.0, 0.5, 0.4), sss_scale=0.02))
    return m


# ───────────────────────── costruzione ─────────────────────────

POSA = {'viewer': (-9.0, -2.0, 1.5)}       # sostituito dalla posa di gioco (scena_creature.madre_posa)


def build(viewer=None, bocca=0.0, piccoli=True, spruzzo_on=True, corpo_on=True):
    """La Madre in coordinate locali. viewer: dove guardano gli occhi (il pescatore); bocca: 0 chiusa, 1 spalancata.
    Oggetti: 'MadreHead' (la testa, y < TAGLIO), 'MadreSkin' (il corpo), 'MadreEye0/1' (gli occhi, il destro è 0),
    'MadreLashes', 'MadreBaleen' (le sbarre), 'MadreRail' (i corrimano), 'MadreSpray', 'MadreKids', 'MadreSlime'."""
    viewer = V(*(viewer if viewer is not None else POSA['viewer']))
    c = Campo(bocca)
    attrs = {'ventre': c.attr_ventre, 'guancia': c.attr_guancia, 'sorriso': c.attr_sorriso, 'mouth': c.attr_mouth,
             'gola': c.attr_gola}
    pelle = pelle_madre()
    obs = []
    cut_h = lambda p: (p[:, 1] - TAGLIO).astype(F)          # noqa: E731
    lo, hi = V(-6.2, -14.6, -9.6), V(6.2, TAGLIO + 0.2, 3.6)
    if c.bocca > 0.05:
        jaw_lo = np.array([c.jaw_pt(q) for q in ((x, y, z) for x in (-5, 5) for y in (-13.5, 2) for z in (-7.5, -1.5))])
        lo, hi = np.minimum(lo, jaw_lo.min(0) - 0.4), np.maximum(hi, jaw_lo.max(0) + 0.4)
        hi[1] = TAGLIO + 0.2
    ob = sdf_object('MadreHead', sdf.intersect(c.f, cut_h), lo, hi, res=RES_HEAD, attrs=attrs, banded=True)
    ob.data.materials.append(pelle)
    obs.append(ob)
    if corpo_on:
        ob = sdf_object('MadreSkin', sdf.intersect(c.f, lambda p: -cut_h(p)), V(-7.0, TAGLIO - 0.2, -11.2), V(7.0, 21.6, 2.4),
                        res=RES_BODY, attrs=attrs, banded=True)
        ob.data.materials.append(pelle)
        obs.append(ob)
    # gli occhi, girati verso il pescatore (dentro l'orbita, al massimo di 40° dall'asse)
    from creature import eyeball
    for i, (ce, a) in enumerate(occhi()):
        look = unit(viewer - ce)
        if float(look @ a) < math.cos(math.radians(40)):
            k = np.cross(a, look)
            k = unit(k) if np.linalg.norm(k) > 1e-6 else unit(np.cross(a, V(0, 0, 1)))
            t = math.radians(40)
            look = (a * math.cos(t) + np.cross(k, a) * math.sin(t)).astype(F)
        if i == 1:
            look = a
        e = eyeball(f'MadreEye{i}', tuple(map(float, ce)), OCCHIO_R, occhio_madre(), look=tuple(map(float, look)))
        obs.append(e)
    obs.append(TF.tubes('MadreLashes', ciglia(), ciglia_material(), m=14))
    bars, rails = fanoni(c)
    obs.append(TF.tubes('MadreBaleen', bars, fanoni_material(), m=12))
    if rails:
        obs.append(TF.tubes('MadreRail', rails, fanoni_material(), m=12))
    if spruzzo_on:
        curves, drops, rads = spruzzo()
        obs.append(TF.tubes('MadreSpray', curves, acqua_material(), m=12))
        obs.append(TF.balls('MadreSprayDrops', drops, rads, acqua_material()))
    if piccoli and corpo_on:
        ob = sdf_object('MadreKids', piccoli_campo(), V(-2.6, 1.6, -9.0), V(2.6, 6.4, -6.8), res=0.03)
        ob.data.materials.append(piccoli_material())
        obs.append(ob)
    # la melma che cola: dalle palpebre di sotto, dal mento, dalle ciglia
    anchors = []
    for ce, a in occhi():
        u, v = base_occhio(a)
        for k in (-0.6, -0.2, 0.25, 0.7):
            anchors.append(ce + a * OCCHIO_DENTRO - v * (APERTURA + 0.3) + u * 1.6 * k)
    anchors += [V(s * 2.0, -12.4, -3.9) for s in (-1, 1)]
    pts, _ = TF.snap(c.f, anchors)
    rng = np.random.default_rng(7)
    parts = [skin.drip(q + V(0, 0, 0.02), rng.uniform(0.25, 0.65), r0=0.035, r1=rng.uniform(0.055, 0.08)) for q in pts]
    lo_d, hi_d = pts.min(0) - 0.2, pts.max(0) + 0.2
    lo_d[2] -= 0.9
    obs.append(D.mesh('MadreSlime', sdf.union(*parts), lo_d, hi_d, TF.goo_material(), res=0.02))
    return obs


# ───────────────────────── la tavola della testa ─────────────────────────

def _font(size, bold=False):
    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else ''), size)
    except OSError:
        return ImageFont.load_default()


def _camera(M, cl, ct, lens):
    from mathutils import Vector
    sc = bpy.context.scene
    cam = sc.camera
    if cam is None:
        cam_d = bpy.data.cameras.new('Cam')
        cam_d.sensor_width = 36.0
        cam_d.clip_start = 0.05
        cam_d.clip_end = 2000.0
        cam = bpy.data.objects.new('Cam', cam_d)
        sc.collection.objects.link(cam)
        sc.camera = cam
    cam.data.lens = lens
    a, b = M @ Vector(tuple(map(float, cl))), M @ Vector(tuple(map(float, ct)))
    cam.location = a
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = (b - a).to_track_quat('-Z', 'Y')
    return cam


def _pt(*q):
    return tuple(float(x) for x in q)


def _shots():
    """Le inquadrature della tavola, in coordinate della Madre: (camera, bersaglio, lente, titolo, bocca aperta,
    mare)."""
    a, u, v = OCCHIO_ASSE, *base_occhio(OCCHIO_ASSE)
    e = OCCHIO
    return {
        'insieme': (_pt(-38.0, 2.0, -9.0), _pt(0.0, 3.0, -4.0), 30, 'tutta, fuori dall\'acqua: 30 m; sotto, i piccoli', False, False),
        'fronte': (_pt(*(e + a * 13.0 + V(0, -3.0, 0.3))), _pt(*(e + V(0.6, -1.6, -0.6))), 28, 'la fronte e l\'occhio, dalla barca', False, True),
        'occhio': (_pt(*(e + a * 7.2 + v * 0.6 - u * 0.4)), _pt(*(e + v * 0.6)), 45, 'l\'occhio con le ciglia', False, True),
        'sorriso': (_pt(-10.5, -4.5, -1.6), _pt(-4.2, -2.6, -2.4), 32, 'il sorriso fino sotto l\'occhio, la guancia', False, False),
        'croste': (_pt(-6.0, -10.0, 3.2), _pt(-2.4, -7.2, 0.9), 40, 'la fronte: le croste di vernice', False, True),
        'bocca': (_pt(-2.5, -24.0, -10.0), _pt(0.0, -6.0, -6.0), 30, 'la bocca spalancata: i fanoni a sbarre', True, False),
    }


def scena_studio():
    """La scena della tavola: la Madre nella posa di gioco (inclinata come in scena_creature.madre_posa, ma senza
    la barca), il mare nero, le luci di studio a scala della balena."""
    import scena_creature as SC
    sc = reset_scene()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.cycles.use_denoising = True
    w = bpy.data.worlds.new('Night')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.012, 0.016, 0.026, 1)
    w.lightgroup = 'ambient'
    acqua = TF.water()
    acqua.scale = (1.0, 1.0, 1.0)
    M, kw = SC.madre_posa()
    return M, kw, acqua


def _luci(M):
    from mathutils import Vector
    w = lambda q: tuple(M @ Vector(tuple(map(float, q))))     # noqa: E731
    h = OCCHIO + V(0.5, -1.5, 0.0)
    D.area_light('Key', w(OCCHIO + OCCHIO_ASSE * 16 + V(0, 6, 4)), w(h), 6000, (1.0, 0.74, 0.46), 4.0)
    D.area_light('Rim', w(V(12, 14, 12)), w(V(0, -4, -1)), 14000, (0.55, 0.72, 1.0), 6.0)
    D.area_light('Fill', w(V(-14, -22, 2)), w(V(0, -5, -2)), 2500, (0.55, 0.65, 0.85), 8.0)
    D.area_light('Under', w(V(-12, 6, -16)), w(V(0, 3, -7)), 5000, (0.50, 0.70, 0.80), 8.0)


def tavola_testa_render(only=None):
    """I pannelli della tavola della testa: tools/render/cache/madre/madre_<inquadratura>.png."""
    import scena_creature as SC
    out_dir = os.path.join(CACHE, 'madre')
    os.makedirs(out_dir, exist_ok=True)
    M, kw, acqua = scena_studio()
    chiusa = SC.place(build(**kw), M)
    aperta = None
    _luci(M)
    sc = bpy.context.scene
    W, H = (640, 480) if FAST else (960, 720)
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 24 if FAST else 64
    sc.render.image_settings.file_format = 'PNG'
    out = []
    for name, (cl, ct, lens, _, aperta_on, mare) in _shots().items():
        if only and name not in only:
            continue
        if aperta_on and aperta is None:
            aperta = SC.place(build(**kw, bocca=1.0, piccoli=False, spruzzo_on=False, corpo_on=False), M)
        for o in chiusa:
            o.hide_render = aperta_on and o.name.startswith(('MadreHead', 'MadreBaleen', 'MadreRail', 'MadreSlime', 'MadreEye',
                                                             'MadreLashes'))
        for o in aperta or []:
            o.hide_render = not aperta_on
        acqua.hide_render = not mare
        _camera(M, cl, ct, lens)
        path = os.path.join(out_dir, f'madre_{name}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('ok', path, flush=True)
    return out


def tavola_testa(size=(480, 360)):
    """La tavola: sei pannelli 3×2 con le didascalie → docs/concept/madre_testa.jpg."""
    W, H = size
    cap = 30
    shots = _shots()
    top = 44
    sheet = Image.new('RGB', (3 * W, top + 2 * (H + cap)), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    font = _font(15)
    d.text((10, 10), 'LA MADRE · Mama Marina · la testa', fill=(235, 235, 230), font=_font(22, True))
    d.text((3 * W - 190, 14), 'da approvare', fill=(240, 190, 110), font=_font(18, True))
    for i, (name, s) in enumerate(shots.items()):
        p = os.path.join(CACHE, 'madre', f'madre_{name}.png')
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS)
        x, y = (i % 3) * W, top + (i // 3) * (H + cap)
        sheet.paste(im, (x, y))
        d.text((x + 8, y + H + 6), s[3], fill=(225, 225, 220), font=font)
    dst = os.path.join(ROOT, 'docs', 'concept', 'madre_testa.jpg')
    sheet.save(dst, quality=90)
    print('tavola', dst, flush=True)
    return dst


# ───────────────────────── la posa nella scena del gioco ─────────────────────────

def _angoli(pts):
    d = np.atleast_2d(np.asarray(pts, float)) - np.array(EYE)
    return np.degrees(np.arctan2(d[:, 0], d[:, 1])), np.degrees(np.arctan2(d[:, 2], np.hypot(d[:, 0], d[:, 1])))


def _span(pts):
    y, p = _angoli(pts)
    return {'yaw': [round(float(y.min()), 1), round(float(y.max()), 1)], 'pitch': [round(float(p.min()), 1), round(float(p.max()), 1)]}


def ingombro(obs, M):
    """Dove sta la posa vista dall'occhio del pescatore: yaw e pitch di quello che sta sopra il mare, dove sta
    l'occhio (gradi, metri), a che distanza dal bordo."""
    import boat
    import jobs
    from mathutils import Vector
    meshes = [o for o in obs if o.type == 'MESH']
    pts = np.array(jobs.dense_points(meshes, n=4000))
    fuori = pts[pts[:, 2] > 0.0]
    e = M @ Vector(tuple(map(float, OCCHIO)))
    y, p = _angoli([tuple(e)])
    bordo = boat.half_width_at(float(e.y), 0.75) if hasattr(boat, 'half_width_at') else 1.1
    return {
        'fuori': _span(fuori) if len(fuori) else None,
        'quota_max': round(float(pts[:, 2].max()), 2),
        'occhio': [round(float(y[0]), 1), round(float(p[0]), 1)],
        'occhio_m': [round(float(e[i] - EYE[i]), 3) for i in range(3)],
        'occhio_quota': round(float(e.z), 2),
        'occhio_dal_bordo': round(float(abs(e.x) - bordo - OCCHIO_R), 2),
    }


def alba():
    """L'alba sulla scena del gioco (per l'anteprima): il cielo che si schiarisce, caldo all'orizzonte dalla parte
    dell'imboccatura della baia (dietro a sinistra), il sole appena sorto; la luna e le stelle spente."""
    from nodes import world
    from env import yaw_dir
    w, g = world('Alba')
    w.lightgroup = 'ambient'
    d = g.texcoord('Generated')
    dx, dy, dz = g.sep(d)
    sd = yaw_dir(-140.0, 4.0)
    cosang = g.vmath('DOT_PRODUCT', d, sd)
    up = g.clamp01(dz)
    sky = g.mix(g.pow(up, 0.45), (0.85, 0.52, 0.34), (0.16, 0.26, 0.48))
    sky = g.mix(g.mul(g.pow(g.math('MAXIMUM', cosang, 0.0), 6.0), 0.8), sky, (1.0, 0.62, 0.32))
    sky = g.mix(g.smoothstep(0.0, -0.05, dz), sky, (0.10, 0.12, 0.16))
    g.output_world(g.background(sky, 0.9))
    bpy.context.scene.world = w
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and o.name == 'Moon':
            o.data.energy = 0.0
    sun = bpy.data.lights.new('Sole', 'SUN')
    sun.energy = 3.0
    sun.color = (1.0, 0.72, 0.48)
    sun.angle = math.radians(1.0)
    so = bpy.data.objects.new('Sole', sun)
    bpy.context.scene.collection.objects.link(so)
    from mathutils import Vector
    so.rotation_mode = 'QUATERNION'
    so.rotation_quaternion = Vector((-sd[0], -sd[1], -sd[2])).to_track_quat('-Z', 'Y')
    so.lightgroup = 'ambient'


POSE_ANTEPRIME = {
    # (nome, yaw, pitch, lente, alba): la vista del gioco (90° di campo) girata a sinistra verso la Madre
    'notte': (None, 4.0, 18.0, False),
    'alba': (None, 4.0, 18.0, True),
}


def anteprima_posa():
    """La posa di gioco (scena_creature.madre_sale) nella scena della barca, vista dall'occhio del pescatore con la
    vista del gioco (90° di campo), di notte con la lampara e all'alba. Pannelli in cache/madre, l'ingombro in
    cache/madre/madre_posa.json."""
    import batteria
    import jobs
    import scena_creature as SC
    from common import perspective_camera
    jobs.build_scene(fish=5, rod=True)
    batteria.build_battery(needle=0.72)
    before = set(bpy.data.objects.keys())
    SC.madre_sale()
    bpy.context.view_layer.update()
    new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
    info = ingombro(new, SC.LAST_M['madre_sale'])
    print('ingombro', json.dumps(info), flush=True)
    out_dir = os.path.join(CACHE, 'madre')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'madre_posa.json'), 'w') as fh:
        json.dump(info, fh, indent=1)
    sc = bpy.context.scene
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.resolution_percentage = 100
    sc.render.resolution_x, sc.render.resolution_y = (960, 540) if FAST else (1600, 900)
    sc.cycles.samples = 20 if FAST else 48
    out = []
    for name, (yaw, pitch, lens, dawn) in POSE_ANTEPRIME.items():
        if dawn:
            alba()
        if yaw is None:
            yaw = info['occhio'][0] + 8.0
        t = (EYE[0] + math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)),
             EYE[1] + math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)), EYE[2] + math.sin(math.radians(pitch)))
        perspective_camera(EYE, t, lens=lens, name='MadreCam_' + name)
        path = os.path.join(out_dir, f'madre_posa_{name}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('pannello', path, flush=True)
    return out, info


def tavola_posa():
    """Le due anteprime della posa (notte, alba) una sopra l'altra, con la scritta «da approvare» →
    docs/concept/madre_posa.jpg."""
    ims = []
    font = _font(22, bold=True)
    for name in POSE_ANTEPRIME:
        im = Image.open(os.path.join(CACHE, 'madre', f'madre_posa_{name}.png')).convert('RGB')
        if im.width > 1280:
            im = im.resize((1280, round(im.height * 1280 / im.width)), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        txt = f'LA MADRE · posa madre_sale · {"all\'alba" if name == "alba" else "di notte, con la lampara"} · da approvare'
        d.rectangle((0, 0, int(d.textlength(txt, font=font)) + 24, 38), fill=(14, 14, 16))
        d.text((12, 7), txt, fill=(240, 190, 110), font=font)
        ims.append(im)
    sheet = Image.new('RGB', (ims[0].width, sum(i.height for i in ims) + 8 * (len(ims) - 1)), (14, 14, 16))
    y = 0
    for im in ims:
        sheet.paste(im, (0, y))
        y += im.height + 8
    dst = os.path.join(ROOT, 'docs', 'concept', 'madre_posa.jpg')
    sheet.save(dst, quality=90)
    print('anteprima', dst, flush=True)
    return dst


# ───────────────────────── la tavola del jumpscare ─────────────────────────

def tavola_jumpscare(q='draft', tile=(320, 180), exposure=0.5):
    """I fotogrammi del jumpscare della Madre in una tavola 4×2, come le altre di docs/concept/jumpscare: ricomposti
    dagli EXR in cache/<qualità>/jumpscare (la creatura sopra lo sfondo, come fa jumpscare.run) e resi col tono del
    motore (post.tonemap). → docs/concept/jumpscare/js_madre_fotogrammi.jpg"""
    import post
    d = os.path.join(CACHE, q, 'jumpscare')
    bg = post.read_exr(os.path.join(d, 'madre_bg.exr'))
    bg_lin = sum(bg[g][..., :3] for g in ('ambient', 'lamp', 'lantern') if g in bg)
    W, H = tile
    sheet = Image.new('RGB', (4 * W, 2 * H))
    font = _font(14)
    for i in range(8):
        p = post.read_exr(os.path.join(d, f'madre_{i:02d}.exr'))
        fg = sum(p[g][..., :3] for g in ('ambient', 'lamp', 'lantern') if g in p)
        a = p['alpha'][..., None] if 'alpha' in p else np.ones(fg.shape[:2] + (1,), np.float32)
        comp = fg + bg_lin * (1 - np.clip(a, 0, 1))
        im = Image.fromarray((post.tonemap(comp, exposure) * 255 + 0.5).astype(np.uint8), 'RGB').resize((W, H), Image.LANCZOS)
        ImageDraw.Draw(im).text((6, 4), str(i), fill=(230, 230, 225), font=font)
        sheet.paste(im, ((i % 4) * W, (i // 4) * H))
    dst = os.path.join(ROOT, 'docs', 'concept', 'jumpscare', 'js_madre_fotogrammi.jpg')
    sheet.save(dst, quality=90)
    print('tavola', dst, flush=True)
    return dst


def _argomento(flag, default=None):
    i = sys.argv.index(flag)
    return sys.argv[i + 1] if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--') else default


if __name__ == '__main__':
    if '--posa' in sys.argv:
        anteprima_posa()
        tavola_posa()
    elif '--posa-tavola' in sys.argv:
        tavola_posa()
    elif '--jumpscare-tavola' in sys.argv:
        q = _argomento('--jumpscare-tavola', 'draft')
        tavola_jumpscare(q if q in ('draft', 'preview', 'final') else 'draft')
    elif '--testa-tavola' in sys.argv:
        tavola_testa()
    else:
        only = _argomento('--solo') if '--solo' in sys.argv else None
        tavola_testa_render(only.split(',') if only else None)
        tavola_testa()
