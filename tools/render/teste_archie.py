"""
ARCHIE — dettagli della testa (notte 3, sagoma C «Periscopio»), da scegliere insieme. Rifatto il 10 ottobre
(l'utente: «la pistola non è bella, troviamo un altro sistema: che sia un serpente marino e ti soffia per
spegnere»).

Come per la prima notte (tools/render/dettagli.py, che qui si usa senza toccarlo): il corpo della sagoma
scelta e tre teste, da "più pesce" (A) a "più bambino" (C), con addosso la cosa del parco. Archie viene dal
serpente di mare del Mediterraneo (Ophisurus serpens): un'anguilla serpentiforme lunghissima e sottile, il
muso lungo e appuntito, i denti aguzzi, le narici a tubetto in punta al muso, una pinna bassa lungo il
dorso e niente pinne pettorali vistose (non ha braccia). Dal parco: una trombetta da festa, la lingua di
Menelik di carta a strisce con la piuma in punta, fusa nelle labbra (proposta da approvare). Da bambino,
alle feste di compleanno al parco, era lui a spegnere le candeline degli altri bambini: ora soffia, la
trombetta si srotola e il soffio spegne la lampara. Bozze di studio: non sono i modelli definitivi.

Colori (approvati il 10 ottobre): giallo limone pieno a bande nere, come i serpenti di mare veri; sul collo
gli anelli neri girano tutto attorno, come sul serpente di mare a bande. Melma, chiazze e bagnato restano
quelli di famiglia (la pelle colorata di teste_robin.py). Con AgX un giallo scurito diventa oliva e uno
troppo chiaro sbianca in crema: per questo le chiazze sono dorate e non scure, e la luce della lampara è
un po' più bassa che per Robin. La trombetta e il cappellino sono di carta rossa e bianca, la piuma rosa.

Coordinate come la sagoma: il mare è z = 0; Archie sale dall'acqua a y ≈ 0,45; la lampara è davanti a lui
(verso −Y), a sinistra (−X) e più in alto della testa, fuori dall'inquadratura. La macchina da presa sta
di fianco (a −X): la sagoma a periscopio si legge di profilo, il collo dritto e la testa piegata in cima.

Uso: tools/.venv/bin/python tools/render/teste_archie.py [--fast] [--only A|B|C] [--tavola]
     (--tavola rimonta la tavola dai pannelli già renderizzati, senza rifarli)
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import dettagli as D  # noqa: E402
import sdf  # noqa: E402
import skin  # noqa: E402
import teste_robin as R  # noqa: E402  (la pelle colorata dei mostri nuovi e gli aiuti per tubi e mesh a fasce)
from creature import sdf_object  # noqa: E402
from geo import catmull  # noqa: E402
from nodes import material  # noqa: E402

V, F, unit, chain = D.V, D.F, D.unit, D.chain
tubo, entro, fine = R.tubo, R.entro, R.fine
FAST = D.FAST
RES_BODY = 0.0045 if FAST else 0.003      # collo e testa: una mesh sola, valutata a fasce
RES_FINE = 0.0016 if FAST else 0.0011     # pezzi sottili (capelli, piuma, elastico, bava)

LAMP = V(-0.55, -1.25, 2.95)              # la lampara (fuori campo, più in alto della testa): la luce calda viene da lì
HEAD = V(-0.04, 0.18, 2.36)               # centro della testa, in cima al collo
AIM = unit(LAMP - HEAD)                   # la testa la prende di mira
HEAD_PITCH = -math.degrees(math.asin(float(AIM[2])))
HEAD_YAW = math.degrees(math.asin(float(AIM[0]) / math.sqrt(1.0 - float(AIM[2]) ** 2)))
CAM = ((-1.20, -0.14, 2.26), (-0.12, 0.05, 2.22), 36)
TESTONE = 1.3                             # le teste da bambino (B, C) sono più grandi del vero

# i testi sotto i pannelli della tavola (nome della variante e spiegazione)
TESTI = {
    'A': ('A · Serpente', 'più pesce: la testa del serpente di mare,\nlunga e appuntita, coi denti aguzzi fuori\ndalle labbra; stringe il bocchino'),
    'B': ('B · Anguilla', 'a metà: cranio e orecchie di bambino sul\nmuso lungo da anguilla; le labbra sono\ncresciute attorno al bocchino'),
    'C': ('C · Bambino', 'più bambino: le guance gonfie come per\nspegnere le candeline, il cappellino da\nfesta sformato e fradicio'),
}


# ───────────────────────── materiali ─────────────────────────

def pelle_archie():
    """Giallo pieno: dorso più dorato, fianchi giallo limone, gola giallo chiaro; le bande nere ('seconda');
    chiazze e vene dorate (scure farebbero oliva); melma appena gialla. Nell'albedo il giallo tira al verde:
    sotto la lampara, che è calda, torna giallo invece di andare verso l'arancio."""
    return R.pelle('ArchieSkinYellow', dorso=(0.76, 0.62, 0.0), fianco=(0.78, 0.76, 0.0), ventre=(0.88, 0.86, 0.24),
                   macchie=(0.80, 0.62, 0.0), seconda=(0.012, 0.010, 0.008), vene=(0.76, 0.50, 0.0),
                   placche=(0.95, 0.85, 0.40), guance=(0.95, 0.30, 0.16), bocca=(0.12, 0.02, 0.02),
                   melma=(1.0, 0.98, 0.72), sss=(1.0, 0.85, 0.25))


def melma_gialla():
    return skin.slime_material('SlimeYellow', tint=(0.95, 0.93, 0.62))


def carta_festa(name, pois=False):
    """La carta della trombetta e del cappellino: rossa e bianca, fradicia (macchie d'alga, scolorita a
    chiazze, lucida d'acqua). La trombetta è a strisce a spirale (attributi 'tick', metri lungo il tubo, e
    'ang', giri attorno); il cappellino a pois. Il rosso è cupo: con AgX un rosso chiaro sbianca in rosa."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    if pois:
        dots = g.voronoi(co, scale=34.0, feature='F1')
        bianco = g.smoothstep(0.30, 0.24, dots)
    else:
        u = g.math('FRACT', g.add(g.div(g.attr('tick'), 0.030), g.attr('ang')))
        bianco = g.mul(g.smoothstep(0.46, 0.50, u), g.smoothstep(0.96, 0.92, u))
    col = g.mix(bianco, (0.60, 0.030, 0.045), (0.84, 0.81, 0.72))
    st = g.noise(co, scale=14.0, detail=5.0, rough=0.6)
    col = g.mix(g.mul(g.smoothstep(0.58, 0.74, st.fac), 0.6), col, (0.22, 0.22, 0.09))
    fade = g.noise(co, scale=4.0, detail=3.0)
    col = g.mix(g.mul(g.smoothstep(0.50, 0.75, fade.fac), 0.30), col, (0.66, 0.50, 0.46))
    g.output_material(g.principled(color=col, rough=0.45, coat=0.5, coat_rough=0.08, sss=0.15, sss_radius=(1.0, 0.6, 0.5),
                                   sss_scale=0.003, normal=g.bump(st.fac, strength=0.25, distance=0.001)))
    return m


def piuma_material():
    """Le piume rosa della trombetta e il pompon del cappellino, zuppi."""
    return D.mat_simple('PartyFeather', (0.80, 0.16, 0.36), rough=0.45, sheen=0.8, coat=0.4, coat_rough=0.1)


# ───────────────────────── il collo (sagoma C «Periscopio») ─────────────────────────
# Un collo sottilissimo che sale dritto dall'acqua: sotto il pelo dell'acqua il resto del corpo, sopra
# solo il collo, lungo e liscio come un'anguilla, e la testa in cima piegata verso la luce.

NECK = [V(0.02, 0.50, -0.20), V(0.0, 0.47, 0.50), V(-0.01, 0.44, 1.20), V(-0.02, 0.41, 1.80), V(-0.025, 0.37, 2.10)]
NECK_R = [0.085, 0.072, 0.058, 0.050, 0.047]


class Testa(D.Frame):
    """Il sistema locale della testa (dettagli.Frame: costruita dritta, faccia verso −Y, alto +Z), con in più
    una scala: le teste da bambino sono più grandi del vero (un testone da bambola in cima a un collo da
    periscopio), così si leggono nella stessa inquadratura."""

    def __init__(self, pos, pitch=0.0, yaw=0.0, k=1.0):
        super().__init__(pos, pitch, yaw)
        self.k = k

    def field(self, f):
        M, c, k = self.R, self.pos, self.k
        return lambda p: f(((p - c) @ M) / k) * k

    def pt(self, q):
        return self.pos + self.R @ (V(*q) * self.k)

    def local(self, p):
        return ((p - self.pos) @ self.R) / self.k


def frame(k=1.0, dyaw=0.0):
    return Testa(tuple(map(float, HEAD)), pitch=HEAD_PITCH, yaw=HEAD_YAW + dyaw, k=k)


def neck_path(fr, attacco):
    """I punti del collo fino alla testa: l'ultimo tratto entra nella nuca dal basso ('attacco', locale)."""
    q = V(*attacco)
    return NECK + [fr.pt(q), fr.pt(q + V(0, -0.06, 0.04))], NECK_R + [0.054, 0.060]


class Collo:
    """La linea del collo (catmull fitta) per gli attributi: lunghezza d'arco, tangente, 'dorso' (la parte
    del collo che guarda via dalla barca e, in cima, verso l'alto)."""

    def __init__(self, pts):
        P = catmull(pts, 24).astype(F)
        T = np.gradient(P, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        B = np.cross(T, V(1, 0, 0))
        B /= np.linalg.norm(B, axis=1, keepdims=True)
        self.P, self.T, self.B = P, T, B
        self.s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]).astype(F)
        self.tree = cKDTree(P)

    def query(self, p):
        """Distanza dalla linea, lunghezza d'arco (continua: proiettata sulla tangente, altrimenti i bordi
        delle bande vengono a scalini) e 'dorso' (1 sul dorso, −1 sulla gola)."""
        d, i = self.tree.query(p, k=1, workers=-1)
        r = p - self.P[i]
        along = np.einsum('ij,ij->i', r, self.T[i])
        r -= along[:, None] * self.T[i]
        rn = r / (np.linalg.norm(r, axis=1, keepdims=True) + 1e-9)
        b = np.einsum('ij,ij->i', rn, self.B[i])
        return d.astype(F), (self.s[i] + along).astype(F), b.astype(F)

    def raggio(self, sv):
        return float(np.interp(sv / self.s[-1], np.linspace(0, 1, len(NECK_R)), NECK_R))


def bande_collo(collo, s_top, p):
    """Gli anelli neri attorno al collo, come sul serpente di mare a bande: girano tutto attorno, un po' più
    stretti sulla gola, che resta giallo chiaro."""
    d, s, b = collo.query(p)
    s = s + 0.004 * np.sin(p[:, 0] * 37.0 + p[:, 1] * 23.0) * np.sin(p[:, 2] * 19.0)
    w = 0.042 * (0.70 + 0.30 * np.clip((b + 1.0) / 2.0, 0.0, 1.0))
    out = np.zeros(len(p), F)
    for k in range(10):
        sk = s_top - 0.11 - 0.24 * k
        out = np.maximum(out, 1.0 - D.smooth01(np.abs(s - sk) - w, -0.006, 0.006))
    return out, np.clip(0.5 - 0.6 * b, 0.0, 1.0) ** 1.5


def pinna(collo, s_top):
    """La pinna bassa lungo il dorso, come sul serpente di mare: una lama sottile che corre su tutto il collo e
    muore poco dietro la testa."""
    lama = sdf.ellipsoid(V(0, 0, 0), (0.0045, 0.024, 0.032))      # (di fianco, in altezza, lungo il collo)
    parts, pts = [], []
    for sv in np.arange(1.0, s_top - 0.10, 0.04):
        i = int(np.searchsorted(collo.s, sv))
        c, t, bk = collo.P[i], collo.T[i], collo.B[i]
        h = 0.65 + 0.35 * min(1.0, (s_top - 0.10 - sv) / 0.4)      # si abbassa verso la testa
        q = c + bk * (collo.raggio(sv) + 0.002)
        M = np.stack([np.cross(t, bk), bk, t], axis=1).astype(F)
        parts.append(entro(lambda p, q=q, M=M, h=h: lama(((p - q) @ M) / V(1.0, h, 1.0)) * h, q - 0.04, q + 0.04))
        pts.append(q)
    P = np.array(pts, F)
    return entro(sdf.union(*parts), P.min(0) - 0.05, P.max(0) + 0.05)


def branchie(collo, s_top):
    """Tre fessure per lato sul collo, sotto la testa: corte lungo il collo, lunghe attorno."""
    slit = sdf.ellipsoid(V(0, 0, 0), (0.008, 0.026, 0.0055))      # (profondità, attorno al collo, lungo il collo)
    parts = []
    for j in range(3):
        sv = s_top - 0.15 - 0.032 * j
        i = int(np.searchsorted(collo.s, sv))
        c, t, bk = collo.P[i], collo.T[i], collo.B[i]
        lat = np.cross(t, bk)
        for s in (-1, 1):
            q = c + lat * s * collo.raggio(sv) - bk * 0.010
            M = np.stack([lat, bk, t], axis=1).astype(F)
            parts.append(lambda p, q=q, M=M: slit((p - q) @ M))
    return sdf.union(*parts)


# ───────────────────────── il corpo ─────────────────────────

def corpo(fr, head_local, attacco, cut_local=None, attrs_testa=None):
    """La pelle: collo con la pinna e testa, con gli attributi del colore. attrs_testa(q) → (ventre, seconda,
    maschera) in coordinate locali della testa: la testa decide per sé, il resto ha gli anelli del collo."""
    pts, radii = neck_path(fr, attacco)
    collo = Collo(pts)
    s_top = float(collo.s[np.argmin(np.linalg.norm(collo.P - fr.pt(attacco), axis=1))])
    neck = sdf.union(chain(pts, radii, k=0.05), pinna(collo, s_top), k=0.008)
    head = entro(fr.field(head_local), HEAD - 0.36, HEAD + 0.36)
    f = sdf.union(neck, head, k=0.03)
    cut = branchie(collo, s_top)
    if cut_local is not None:
        cut = sdf.union(cut, entro(fr.field(cut_local), HEAD - 0.32, HEAD + 0.32))
    f = sdf.subtract(f, cut, k=0.005)

    def colore(p):
        sec, ven = bande_collo(collo, s_top, p)
        if attrs_testa is not None:
            vt, st, m = attrs_testa(fr.local(p))
            ven = np.where(m, vt, ven).astype(F)
            sec = np.where(m, st, sec).astype(F)
        return ven, sec

    cache = {}

    def get(p, k):
        key = (len(p), float(p[0, 0]), float(p[-1, 2]))
        if key not in cache:
            cache.clear()
            cache[key] = colore(p)
        return cache[key][k]

    return f, {'ventre': lambda p: get(p, 0), 'seconda': lambda p: get(p, 1)}


def pelle_mesh(f, attrs, extra=None):
    a = dict(attrs)
    a.update(extra or {})
    ob = sdf_object('ArchieSkin', f, V(-0.30, -0.36, 1.10), V(0.24, 0.62, 2.72), res=RES_BODY, attrs=a, banded=True)
    ob.data.materials.append(pelle_archie())
    return ob


def bava(name, fili=(), gocce=()):
    """Lo strato di melma: fili di bava tesi che si afflosciano, gocce che pendono."""
    parts, pts = [], []
    for a, b, sag in fili:
        a, b = V(*a), V(*b)
        parts.append(skin.strand(a, b, sag, r=0.0016))
        pts += [a, b, (a + b) / 2 - V(0, 0, sag)]
    for a, L in gocce:
        a = V(*a)
        parts.append(skin.drip(a, L, r0=0.0022, r1=0.0042))
        pts += [a, a - V(0, 0, L)]
    return fine(name, sdf.union(*parts), [np.array(pts, F)], melma_gialla(), pad=0.012, res=0.0011)


def sulla_pelle(f, pts, off=0.0, iters=6, eps=0.0008):
    """Porta i punti (locali) sulla superficie del campo f (locale) e li stacca di 'off' lungo la normale:
    così capelli ed elastico stanno appiccicati alla pelle invece di affondare o di volarle sopra."""
    P = np.array(pts, F)
    for _ in range(iters + 1):
        g = np.stack([f(P + e) - f(P - e) for e in np.eye(3, dtype=F) * eps], axis=1)
        n = g / (np.linalg.norm(g, axis=1, keepdims=True) + 1e-9)
        P = P - f(P)[:, None] * n
    return P + n * off


# ───────────────────────── la trombetta da festa ─────────────────────────

def carta_tubo(name, path, a, b, side, mat, seg=18):
    """Il tubo di carta: un'ellisse (semiassi a di fianco, lungo 'side', e b nel piano del ricciolo, uno per
    punto) spazzata lungo un percorso piano; attributi 'tick' (metri lungo il tubo) e 'ang' (giri attorno)
    per le strisce."""
    P = np.asarray(path, F)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    verts, faces, tick, ang = [], [], [], []
    for i, (p, t) in enumerate(zip(P, T)):
        n = np.cross(side, t)
        for j in range(seg):
            th = 2 * math.pi * j / seg
            verts.append(p + side * a[i] * math.cos(th) + n * b[i] * math.sin(th))
            tick.append(s[i])
            ang.append(j / seg)
    for i in range(len(P) - 1):
        for j in range(seg):
            q0, q1 = i * seg + j, i * seg + (j + 1) % seg
            faces.append((q0, q1, q1 + seg, q0 + seg))
    # il fondo chiuso, in punta
    c = len(verts)
    verts.append(P[-1])
    tick.append(s[-1])
    ang.append(0.0)
    o = (len(P) - 1) * seg
    for j in range(seg):
        faces.append((o + j, o + (j + 1) % seg, c))
    return R.mesh_obj(name, verts, faces, mat, attrs={'tick': tick, 'ang': ang})


def trombetta(fr, q, d_loc=(0.0, -1.0, 0.15), L=0.17, giri=1.6, k=1.3):
    """La trombetta da festa fusa nelle labbra: il bocchino bianco che esce dalla bocca, il tubo di carta a
    strisce gonfio e dritto (sta soffiando: un filo cadente, la carta è bagnata), la punta ancora arrotolata
    sotto in un ricciolo, la piuma rosa zuppa in fondo al ricciolo. q: dove esce il bocchino (locale)."""
    m0 = fr.pt(q)
    d = unit(fr.R @ V(*d_loc))
    down = unit(V(0, 0, -1) - (V(0, 0, -1) @ d) * d)
    obs = []
    m1 = m0 + d * 0.050
    bocchino = sdf.round_cone(m0 - d * 0.025, m1 + d * 0.012, 0.0080 * k, 0.0092 * k)
    obs.append(D.mesh('PartyMouthpiece', bocchino, np.minimum(m0, m1) - 0.05, np.maximum(m0, m1) + 0.05,
                      D.vinyl('PartyMouthpieceVinyl', (0.86, 0.84, 0.76)), res=0.0012))
    path, a, b = [], [], []
    n1 = 40
    for i in range(n1 + 1):
        t = i / n1
        path.append(m1 - d * 0.010 + d * (L * t) + down * (0.022 * t * t))
        a.append(k * (0.0088 + (0.0125 - 0.0088) * D.smooth01(t, 0.0, 0.10)))     # stretta dove è incollata al bocchino
        b.append(k * (0.0088 + (0.0095 - 0.0088) * D.smooth01(t, 0.0, 0.10)))
    dd = unit(path[-1] - path[-2])
    dn = unit(down - (down @ dd) * dd)
    r0, r1 = 0.040 * k, 0.012 * k
    c = path[-1] + dn * r0
    n2 = 70
    for i in range(1, n2 + 1):
        t = i / n2
        phi = 2 * math.pi * giri * t
        r = r0 + (r1 - r0) * t
        path.append(c + r * (-dn * math.cos(phi) + dd * math.sin(phi)))
        a.append(0.0125 * k)
        b.append(k * (0.0095 + (0.0034 - 0.0095) * D.smooth01(t, 0.0, 0.12)))     # arrotolata è piatta
    obs.append(carta_tubo('PartyBlower', path, a, b, unit(np.cross(d, down)), carta_festa('PartyPaper')))
    # la piuma in fondo: ciocche rosa appiccicate dall'acqua
    end = path[-1]
    td = unit(path[-1] - path[-3])
    rng = np.random.default_rng(3)
    ciocche, cp = [], []
    for _ in range(11):
        v = unit(td + V(*rng.normal(0.0, 0.65, 3)))
        Lp = rng.uniform(0.030, 0.050) * k
        pts = [end, end + v * Lp * 0.5 + V(0, 0, -0.004), end + v * Lp + V(0, 0, -0.014)]
        ciocche.append(tubo(pts, 0.0030 * k, 0.0007 * k, n=5)[0])
        cp.append(np.array(pts, F))
    obs.append(fine('PartyFeather', sdf.union(*ciocche, k=0.003), cp, piuma_material(), pad=0.008, res=0.0010))
    return obs


def labbra_fuse(q, d_loc, R0=0.0115, r0=0.0062):
    """Le labbra cresciute attorno al bocchino (in coordinate della testa): un anello di carne e tre radici
    che strisciano avanti sulla plastica."""
    q, d = V(*q), unit(V(*d_loc))
    lat = unit(np.cross(d, V(0, 0, 1)))
    up = np.cross(lat, d)
    parts = [D.torus_axis(q, d, R0, r0)]
    for a in (0.6, 2.4, 4.4):
        r = lat * math.cos(a) + up * math.sin(a)
        f, _ = tubo([q + r * R0 * 0.9, q + d * 0.012 + r * 0.0095, q + d * 0.026 + r * 0.0086], 0.0030, 0.0012, n=4)
        parts.append(f)
    return sdf.union(*parts, k=0.004)


# ───────────────────────── le teste ─────────────────────────

def bande_testa(q, barre, zmin=-0.20):
    """Bande nere di traverso sulla testa: barre = [(y centro, mezza larghezza in alto, mezza larghezza in
    basso)], in coordinate locali; svaniscono sotto zmin (la gola resta chiara)."""
    out = np.zeros(len(q), F)
    z = np.clip((q[:, 2] + 0.10) / 0.20, 0.0, 1.0)
    for yc, wt, wb in barre:
        w = wb + (wt - wb) * z
        wob = 0.004 * np.sin(q[:, 2] * 90.0 + yc * 40.0)
        out = np.maximum(out, 1.0 - D.smooth01(np.abs(q[:, 1] - yc + wob) - w, -0.0025, 0.0025))
    return out * D.smooth01(q[:, 2], zmin - 0.015, zmin + 0.015)


def zanne(fr, lato, n, su=True, L=(0.010, 0.016), r=0.0024, fuori=0.25):
    """Denti aguzzi lungo un lato della bocca (punti locali): di sopra puntano in giù, di sotto in su, un po'
    in fuori, così si vedono a bocca chiusa come quelli del serpente di mare."""
    pts = catmull(lato, 6)
    idx = np.linspace(0, len(pts) - 1, n).round().astype(int)
    rng = np.random.default_rng(len(lato) + n + int(su))
    pairs = []
    for i in idx:
        p = pts[i]
        out = unit(V(np.sign(p[0]) if abs(p[0]) > 1e-4 else 0.0, 0.0, 0.0) * fuori + V(0, 0, -1.0 if su else 1.0))
        Lt = rng.uniform(*L)
        pairs.append((fr.pt(p - out * 0.002), fr.pt(p + out * Lt), r * fr.k))
    return pairs


def archie_a():
    """A · Serpente: la testa del serpente di mare. Lunga, stretta e bassa, il muso appuntito con le narici a
    tubetto che pendono in punta; la bocca è uno squarcio lungo fino sotto l'occhio, coi denti aguzzi che
    restano fuori dalle labbra; gli occhi piccoli in una banda nera; la gola gonfia d'aria per soffiare.
    La trombetta esce dalla punta delle mascelle, che la stringono."""
    fr = frame(1.15)                                   # un po' più grande del vero, come le teste B e C
    cran = sdf.ellipsoid(V(0, 0.03, 0.0), (0.052, 0.16, 0.058))
    snout = sdf.round_cone(V(0, -0.06, 0.002), V(0, -0.212, -0.004), 0.048, 0.014)
    jaw = chain([V(0, 0.02, -0.040), V(0, -0.10, -0.032), V(0, -0.200, -0.020)], [0.044, 0.032, 0.013], k=0.02)
    gular = sdf.ellipsoid(V(0, -0.03, -0.058), (0.048, 0.095, 0.042))        # la gola gonfia: sta soffiando
    nares = sdf.union(*[sdf.round_cone(V(s * 0.010, -0.196, 0.006), V(s * 0.015, -0.214, -0.012), 0.0046, 0.0034) for s in (-1, 1)])
    qb, db = V(0, -0.214, -0.012), (0.0, -1.0, 0.15)
    head = sdf.union(cran, snout, jaw, gular, nares, labbra_fuse(qb, db, 0.0105, 0.0058), k=0.016)
    # lo squarcio della bocca, dalla punta fin sotto l'occhio
    gape = [[V(s * 0.016, -0.200, -0.014), V(s * 0.034, -0.140, -0.024), V(s * 0.046, -0.060, -0.030), V(s * 0.046, -0.020, -0.034)] for s in (-1, 1)]
    mouth = sdf.union(*[chain(g, [0.0026, 0.0034, 0.0032, 0.0022], k=0.002) for g in gape])
    hole = sdf.round_cone(qb + unit(V(*db)) * 0.01, qb - unit(V(*db)) * 0.02, 0.0072, 0.0066)
    sockets = sdf.union(*[sdf.sphere(V(s * 0.041, -0.098, 0.029), 0.0145) for s in (-1, 1)])
    pores = sdf.union(*[sdf.sphere(V(s * 0.034, y, 0.022), 0.0026) for s in (-1, 1) for y in (-0.150, -0.125, -0.070, -0.045)])   # pori della linea laterale

    def testa(q):
        m = sdf.ellipsoid(V(0, -0.03, -0.01), (0.11, 0.28, 0.14))(q) < 0.0
        ven = np.clip(0.5 - (q[:, 2] + 0.005) / 0.08, 0.0, 1.0)
        sec = bande_testa(q, [(-0.098, 0.026, 0.018), (0.110, 0.030, 0.024)], zmin=-0.045)
        return ven, sec, m

    def bocca(p):
        q = fr.local(p)
        return np.maximum((mouth(q) < 0.003).astype(F), (hole(q) < 0.004).astype(F))

    f, attrs = corpo(fr, head, (0, 0.12, -0.060), cut_local=sdf.union(mouth, hole, sockets, pores), attrs_testa=testa)
    obs = [pelle_mesh(f, attrs, {'mouth': bocca})]
    pairs = []
    for g in gape:
        pairs += zanne(fr, [p + V(0, 0, 0.003) for p in g], 6, su=True, L=(0.018, 0.030), r=0.0034, fuori=0.55)
        pairs += zanne(fr, [p + V(0, 0.010, -0.003) for p in g], 5, su=False, L=(0.014, 0.022), r=0.0030, fuori=0.55)
    obs.append(D.teeth_mesh('ArchieTeeth', pairs, D.needle_teeth()))
    obs += D.eyes('ArchieEye', [fr.pt((s * 0.041, -0.098, 0.029)) for s in (-1, 1)], 0.0155 * fr.k, AIM)
    obs += trombetta(fr, qb, db)
    obs.append(bava('ArchieSlime', fili=[(fr.pt((0.030, -0.150, -0.024)), fr.pt((0.032, -0.150, -0.036)), 0.004)],
                    gocce=[(fr.pt((0.0, -0.205, -0.030)), 0.05), (fr.pt((-0.036, -0.120, -0.034)), 0.035)]))
    return (obs, *TESTI['A'])


def archie_b():
    """B · Anguilla: un cranio tondo e calvo da bambino, con le orecchie a sventola e le lentiggini, ma la
    faccia è tirata avanti in un muso lungo da anguilla coi denti aguzzi agli angoli; le labbra da bambino
    sono cresciute attorno al bocchino della trombetta; le guance appena gonfie."""
    fr = frame(TESTONE)
    cran = sdf.ellipsoid(V(0, 0.040, 0.025), (0.080, 0.095, 0.092))
    face = sdf.ellipsoid(V(0, -0.040, -0.012), (0.064, 0.072, 0.062))
    snout = sdf.round_cone(V(0, -0.060, -0.018), V(0, -0.168, -0.014), 0.040, 0.017)
    jaw = chain([V(0, 0.0, -0.056), V(0, -0.090, -0.046), V(0, -0.160, -0.030)], [0.040, 0.030, 0.014], k=0.02)
    cheeks = sdf.union(*[sdf.sphere(V(s * 0.046, -0.042, -0.036), 0.034) for s in (-1, 1)])
    brow = sdf.ellipsoid(V(0, -0.070, 0.040), (0.060, 0.024, 0.018))
    # le orecchie a sventola: attaccate davanti, il bordo libero dietro, la conca in fuori e in avanti
    ec = [V(s * 0.090, 0.030, 0.006) for s in (-1, 1)]
    en = [V(s * math.cos(math.radians(38)), -math.sin(math.radians(38)), 0) for s in (-1, 1)]
    ears = sdf.union(*[D.ellipsoid_rot(c, (0.011, 0.024, 0.038), sdf.rot_matrix('z', -s * 38)) for s, c in zip((-1, 1), ec)])
    helix = sdf.union(*[sdf.intersect(D.torus_axis(c + n * 0.007, n, 0.020, 0.0042), sdf.plane(V(0, 0, -1), -0.008)) for c, n in zip(ec, en)])
    qb, db = V(0, -0.176, -0.020), (0.0, -1.0, 0.15)
    head = sdf.union(cran, face, snout, jaw, cheeks, brow, ears, helix, labbra_fuse(qb, db, 0.0125, 0.0078), k=0.018)
    gape = [[V(s * 0.020, -0.160, -0.030), V(s * 0.040, -0.110, -0.040), V(s * 0.054, -0.060, -0.046)] for s in (-1, 1)]
    mouth = sdf.union(*[chain(g, [0.0026, 0.0032, 0.0022], k=0.002) for g in gape])
    hole = sdf.round_cone(qb + unit(V(*db)) * 0.01, qb - unit(V(*db)) * 0.02, 0.0072, 0.0066)
    concha = sdf.union(*[D.ellipsoid_rot(c + n * 0.009 + V(0, -0.003, -0.005), (0.0055, 0.009, 0.014), sdf.rot_matrix('z', -s * 38)) for s, c, n in zip((-1, 1), ec, en)])
    sockets = sdf.union(*[sdf.sphere(V(s * 0.036, -0.080, 0.024), 0.0175) for s in (-1, 1)])
    # le lentiggini del bambino sulle guance: puntini bruni (metà del nero delle bande)
    rng = np.random.default_rng(8)
    lent = []
    for s in (-1, 1):
        for _ in range(16):
            lent.append(V(s * 0.046, -0.042, -0.036) + unit(V(s * rng.uniform(0.2, 1.0), rng.uniform(-1.0, -0.1), rng.uniform(-0.2, 0.8))) * 0.034)
    lent = cKDTree(np.array(lent, F))

    def testa(q):
        m = sdf.ellipsoid(V(0, -0.04, 0.0), (0.13, 0.24, 0.16))(q) < 0.0
        ven = np.clip(0.55 - (q[:, 2] + 0.015) / 0.09, 0.0, 1.0)
        sec = bande_testa(q, [(-0.080, 0.020, 0.016)], zmin=-0.004)          # la banda sugli occhi
        sec = np.maximum(sec, bande_testa(q, [(0.085, 0.024, 0.018)], zmin=-0.06))   # e quella dietro le orecchie
        d, _ = lent.query(q, k=1, workers=-1)
        sec = np.maximum(sec, 0.5 * (1.0 - D.smooth01(d.astype(F), 0.0036, 0.0050)))
        return ven, sec, m

    def bocca(p):
        q = fr.local(p)
        return np.maximum.reduce([(mouth(q) < 0.003).astype(F), (hole(q) < 0.004).astype(F), (concha(q) < 0.002).astype(F) * 0.55])

    f, attrs = corpo(fr, head, (0, 0.06, -0.090), cut_local=sdf.union(mouth, hole, concha, sockets), attrs_testa=testa)
    obs = [pelle_mesh(f, attrs, {'mouth': bocca})]
    pairs = []
    for g in gape:
        pairs += zanne(fr, [p + V(0, 0, 0.003) for p in g], 4, su=True, L=(0.011, 0.018), r=0.0026, fuori=0.45)
        pairs += zanne(fr, [p + V(0, 0.006, -0.003) for p in g], 3, su=False, L=(0.009, 0.014), r=0.0024, fuori=0.45)
    obs.append(D.teeth_mesh('ArchieTeeth', pairs, D.needle_teeth()))
    obs += D.eyes('ArchieEye', [fr.pt((s * 0.036, -0.078, 0.024)) for s in (-1, 1)], 0.0175 * fr.k, AIM)
    obs += trombetta(fr, qb, db)
    obs.append(bava('ArchieSlime', gocce=[(fr.pt((0.010, -0.170, -0.034)), 0.05), (fr.pt((-0.052, -0.064, -0.050)), 0.035)]))
    return (obs, *TESTI['B'])


def cappellino(fr, head):
    """Il cappellino da festa a cono, di cartone a pois, fradicio: si è afflosciato e la punta ricade di lato;
    in cima il pompon è una palla di fili zuppi; l'elastico passa sotto il mento."""
    obs = []
    base = V(-0.012, 0.012, 0.094)
    path = [fr.pt(base + d) for d in (V(0, 0, -0.012), V(-0.004, 0.006, 0.040), V(-0.018, 0.016, 0.078), V(-0.050, 0.018, 0.098), V(-0.080, 0.012, 0.094))]
    cone, cp = tubo(path, 0.052 * fr.k, 0.0045 * fr.k, n=8)
    n3 = sdf.Noise3(12)
    cone = sdf.displace(cone, lambda p: n3(p, scale=0.018, octaves=2), 0.0025)        # cartone stropicciato
    obs.append(fine('PartyHat', cone, [cp], carta_festa('PartyHatPaper', pois=True), pad=0.08, res=RES_FINE * 1.4))
    tip = cp[-1]
    pomp = sdf.displace(sdf.sphere(tip + V(0, 0, -0.008), 0.017 * fr.k), lambda p: n3(p, scale=0.005, octaves=2), 0.004)
    obs.append(fine('PartyHatPompom', pomp, [np.array([tip])], piuma_material(), pad=0.04, res=0.0012))
    # l'elastico, da una tempia all'altra sotto il mento, appiccicato alla pelle
    q = [V(-0.072, 0.000, 0.070), V(-0.084, -0.012, 0.000), V(-0.060, -0.040, -0.080), V(0.0, -0.050, -0.122),
         V(0.060, -0.040, -0.080), V(0.084, -0.012, 0.000), V(0.072, 0.000, 0.070)]
    q = [fr.pt(x) for x in sulla_pelle(head, q, off=0.0022)]
    el, ep = tubo(q, 0.0016 * fr.k, 0.0016 * fr.k, n=8)
    obs.append(fine('PartyHatElastic', el, [ep], D.mat_simple('Elastic', (0.55, 0.52, 0.48), rough=0.4, coat=0.5), pad=0.01))
    return obs


def archie_c():
    """C · Bambino: la faccia del bambino che spegneva le candeline degli altri. Le guance gonfie a palla, le
    sopracciglia su per lo sforzo, gli occhi spalancati sulla luce, le labbra strette sul bocchino della
    trombetta; il cappellino da festa sformato e fradicio, l'elastico sotto il mento, la frangia bagnata."""
    fr = frame(TESTONE, dyaw=-25.0)    # la faccia si gira un po' verso chi guarda
    cran = sdf.ellipsoid(V(0, 0.010, 0.015), (0.082, 0.092, 0.100))
    cheeks = sdf.union(*[sdf.sphere(V(s * 0.046, -0.052, -0.042), 0.047) for s in (-1, 1)])     # gonfie a palla
    chin = sdf.sphere(V(0, -0.058, -0.096), 0.024)
    nose = sdf.sphere(V(0, -0.098, -0.002), 0.0125)
    brows = sdf.union(*[chain([V(s * 0.016, -0.086, 0.044), V(s * 0.036, -0.086, 0.054), V(s * 0.056, -0.076, 0.048)], [0.0055, 0.0065, 0.0050], k=0.004) for s in (-1, 1)])
    ears = sdf.union(*[sdf.ellipsoid(V(s * 0.084, 0.006, -0.010), (0.013, 0.024, 0.032)) for s in (-1, 1)])
    qb, db = V(0, -0.106, -0.058), (0.0, -1.0, 0.20)
    head = sdf.union(cran, cheeks, chin, nose, ears, brows, labbra_fuse(qb, db, 0.0110, 0.0085), k=0.022)
    hole = sdf.round_cone(qb + unit(V(*db)) * 0.01, qb - unit(V(*db)) * 0.02, 0.0072, 0.0066)
    sockets = sdf.union(*[sdf.sphere(V(s * 0.035, -0.074, 0.016), 0.020) for s in (-1, 1)])
    nostrils = sdf.union(*[sdf.sphere(V(s * 0.0065, -0.104, -0.010), 0.0035) for s in (-1, 1)])

    def testa(q):
        m = sdf.ellipsoid(V(0, -0.01, -0.01), (0.13, 0.15, 0.16))(q) < 0.0
        ven = np.clip(0.80 - np.maximum(q[:, 1] + 0.05, 0.0) * 6.0 - np.maximum(q[:, 2] - 0.06, 0.0) * 6.0, 0.25, 0.85)
        sec = bande_testa(q, [(0.062, 0.026, 0.020)], zmin=-0.08)          # la banda dietro le orecchie
        return ven, sec, m

    def blush(p):
        q = fr.local(p)
        d = np.minimum(np.linalg.norm(q - V(0.060, -0.074, -0.040), axis=1), np.linalg.norm(q - V(-0.060, -0.074, -0.040), axis=1))
        return np.clip(1.0 - d / 0.032, 0.0, 1.0)

    def bocca(p):
        return (hole(fr.local(p)) < 0.004).astype(F)

    f, attrs = corpo(fr, head, (0, 0.035, -0.088), cut_local=sdf.union(hole, sockets, nostrils), attrs_testa=testa)
    obs = [pelle_mesh(f, attrs, {'mouth': bocca, 'blush': blush})]
    obs += D.eyes('ArchieEye', [fr.pt((s * 0.035, -0.071, 0.016)) for s in (-1, 1)], 0.0195 * fr.k, AIM)
    obs += trombetta(fr, qb, db)
    obs += cappellino(fr, head)
    obs.append(bava('ArchieSlime', gocce=[(fr.pt((0.022, -0.094, -0.072)), 0.06), (fr.pt((-0.020, -0.096, -0.074)), 0.04)]))
    # la frangia bagnata che esce da sotto il cappellino e si incolla alla fronte
    strands, hp = [], []
    rng = np.random.default_rng(5)
    for a in np.linspace(-1, 1, 13):
        Lc = rng.uniform(0.0, 1.0)
        q = [V(0.030 * a, 0.010, 0.112), V(0.040 * a, -0.050, 0.100), V(0.046 * a, -0.084, 0.072), V(0.048 * a, -0.096, 0.056 - 0.012 * Lc)]
        q = [fr.pt(x) for x in sulla_pelle(head, q, off=0.0055)]
        strands.append(tubo(q, 0.0090 * fr.k, 0.0016 * fr.k, n=6)[0])
        hp.append(q)
    for a in (-1.0, -0.6, 0.6, 1.0):
        q = [V(0.050 * a, 0.020, 0.090), V(0.080 * a, 0.010, 0.040), V(0.084 * a, 0.0, -0.010)]
        q = [fr.pt(x) for x in sulla_pelle(head, q, off=0.006)]
        strands.append(tubo(q, 0.0085 * fr.k, 0.0025 * fr.k, n=6)[0])
        hp.append(q)
    obs.append(fine('ArchieHair', sdf.union(*strands, k=0.004), hp, D.wet_hair(), res=RES_FINE))
    return (obs, *TESTI['C'])


# ───────────────────────── tavola ─────────────────────────

# le luci di dettagli.setup sono riferite a 'subject': la luce calda deve venire dalla lampara, davanti a
# lui in alto a sinistra, quindi il riferimento sta dove la lampara è a (−1,0; −1,5; −0,15) da lui
D.CREATURES['archie'] = {
    'title': 'ARCHIE — serpente di mare, sagoma C «Periscopio» · colori approvati · trombetta da festa: proposta da approvare',
    'variants': [archie_a, archie_b, archie_c],
    'cam': CAM,
    'subject': tuple(map(float, LAMP + V(1.0, 1.5, 0.15))), 'key': 32, 'rim': 120,
}


def tavola():
    """Rimonta la tavola dai tre pannelli già renderizzati (in cache), con i testi delle varianti."""
    panels = [(os.path.join(D.TMP, f'archie_{k}.png'), *TESTI[k]) for k in 'ABC']
    return D.compose('archie', panels)


if __name__ == '__main__':
    if '--tavola' in sys.argv:
        print('tavola', tavola(), flush=True)
        raise SystemExit
    only = None
    if '--only' in sys.argv:
        only = 'ABC'.index(sys.argv[sys.argv.index('--only') + 1])
    for i in range(3):
        if only is not None and i != only:
            continue
        D.render_variant('archie', i)
        print('ok archie', 'ABC'[i], flush=True)
    if only is None:
        print('tavola', tavola(), flush=True)
