"""
ARCHIE — dettagli della testa (notte 3, sagoma C «Periscopio»), da scegliere insieme.

Come per la prima notte (tools/render/dettagli.py, che qui si usa senza toccarlo): il corpo della sagoma
scelta e tre teste, da "più pesce" (A) a "più bambino" (C), con addosso la cosa del parco: la pistola ad
acqua arancione del negozio, fusa nella mano. Viene dal pesce arciere (occhi grandi in alto sulla testa,
muso appuntito, bocca all'insù che fa da canna per sputare getti d'acqua, bande nere di traverso sul
corpo). Da bambino sfidava tutti a duello con la pistola ad acqua: ora un collo sottilissimo sale dritto
dall'acqua, la testa in cima si piega verso la lampara e la prende di mira, con la bocca e con la pistola.
Bozze di studio: non sono i modelli definitivi.

Colori (proposta da approvare, 10 ottobre): come gli animatronic di FNAF ogni mostro nuovo ha un colore
netto; Archie è giallo pieno con le bande nere del pesce arciere, la pancia giallo chiaro, la pistola
arancione che stacca dal giallo. Melma, chiazze e bagnato restano quelli di famiglia (la pelle colorata
di teste_robin.py). Con AgX un giallo scurito diventa oliva e uno troppo chiaro sbianca in crema: per
questo le chiazze sono dorate e non scure, e la luce della lampara è un po' più bassa che per Robin.

Coordinate come la sagoma: il mare è z = 0; Archie sale dall'acqua a y ≈ 0,45; la lampara è davanti a
lui (verso −Y), a sinistra (−X) e più in alto della testa, fuori dall'inquadratura. La macchina da presa
sta davanti a sinistra, quasi all'altezza della testa: la testa si vede di tre quarti, la pistola di fianco.

Uso: tools/.venv/bin/python tools/render/teste_archie.py [--fast] [--only A|B|C] [--tavola]
     (--tavola rimonta la tavola dai pannelli già renderizzati, senza rifarli)
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import dettagli as D  # noqa: E402
import sdf  # noqa: E402
import skin  # noqa: E402
import teste_robin as R  # noqa: E402  (la pelle colorata dei mostri nuovi e gli aiuti per tubi e mesh a fasce)
from creature import sdf_object  # noqa: E402
from geo import catmull  # noqa: E402

V, F, unit, chain = D.V, D.F, D.unit, D.chain
tubo, entro, fine = R.tubo, R.entro, R.fine
FAST = D.FAST
RES_BODY = 0.0045 if FAST else 0.003      # collo, braccio e testa: una mesh sola, valutata a fasce
RES_FINE = 0.0016 if FAST else 0.0011     # pezzi sottili (dita sulla pistola, capelli, bava)

LAMP = V(-0.55, -1.25, 2.70)              # la lampara (fuori campo): la luce calda viene da lì
HEAD = V(-0.04, 0.18, 2.36)               # centro della testa, in cima al collo
AIM = unit(LAMP - HEAD)                   # la testa la prende di mira
HEAD_PITCH = -math.degrees(math.asin(float(AIM[2])))
HEAD_YAW = math.degrees(math.asin(float(AIM[0]) / math.sqrt(1.0 - float(AIM[2]) ** 2)))
GUN = V(-0.21, 0.0, 1.86)                 # la pistola: cima dell'impugnatura
GUN_AIM = unit(LAMP - GUN)                # anche la pistola mira alla lampara
CAM = ((-1.00, -0.45, 2.30), (-0.12, 0.09, 2.12), 40)
TESTONE = 1.3                             # le teste da bambino (B, C) sono più grandi del vero

# i testi sotto i pannelli della tavola (nome della variante e spiegazione)
TESTI = {
    'A': ('A · Arciere', 'più pesce: la testa del pesce arciere, occhi\ngrandi in cima, muso a punta; la mandibola\nsporge all\'insù e fa da canna'),
    'B': ('B · Cerbottana', 'a metà: cranio e orecchie di bambino, gli\nocchi saliti sopra la testa; la bocca è un\ntubo di carne, come una cerbottana'),
    'C': ('C · Bambino', 'più bambino: le guance gonfie d\'acqua, un\nocchio chiuso per prendere la mira; le bande\nnere sugli occhi come pittura da guerra'),
}


# ───────────────────────── materiali ─────────────────────────

def pelle_archie():
    """Giallo pieno: dorso più dorato, fianchi giallo limone, gola giallo chiaro; le bande nere del pesce
    arciere ('seconda'); chiazze e vene dorate (scure farebbero oliva); melma appena gialla. Nell'albedo il
    giallo tira al verde: sotto la lampara, che è calda, torna giallo invece di andare verso l'arancio."""
    return R.pelle('ArchieSkinYellow', dorso=(0.76, 0.62, 0.0), fianco=(0.78, 0.76, 0.0), ventre=(0.88, 0.86, 0.24),
                   macchie=(0.80, 0.62, 0.0), seconda=(0.012, 0.010, 0.008), vene=(0.76, 0.50, 0.0),
                   placche=(0.95, 0.85, 0.40), guance=(0.98, 0.50, 0.22), bocca=(0.12, 0.02, 0.02),
                   melma=(1.0, 0.98, 0.72), sss=(1.0, 0.85, 0.25))


def melma_gialla():
    return skin.slime_material('SlimeYellow', tint=(0.95, 0.93, 0.62))


def plastica_arancio():
    """La plastica della pistola: arancio cupo e saturo (con AgX un arancio chiaro sbianca in pesca), lucida,
    graffiata, con le macchie d'alga."""
    return D.vinyl('ArchiePistolOrange', (0.66, 0.13, 0.0), stain=(0.16, 0.18, 0.06))


# ───────────────────────── il collo (sagoma C «Periscopio») ─────────────────────────
# Un collo sottilissimo che sale dritto dall'acqua: sotto il pelo dell'acqua il resto del corpo, sopra
# solo il collo, un braccio che ne esce basso e la testa in cima, piegata verso la luce.

NECK = [V(0.02, 0.50, -0.20), V(0.0, 0.47, 0.50), V(-0.01, 0.44, 1.20), V(-0.02, 0.41, 1.80), V(-0.025, 0.37, 2.10)]
NECK_R = [0.090, 0.078, 0.066, 0.058, 0.055]
SHOULDER = V(-0.075, 0.42, 0.55)          # il braccio esce dal collo poco sopra l'acqua
ELBOW = V(-0.34, 0.30, 1.22)


class Testa(D.Frame):
    """Il sistema locale della testa (dettagli.Frame: costruita dritta, faccia verso −Y, alto +Z), con in più
    una scala: le teste B e C, da bambino, sono più grandi del vero (un testone da bambola in cima a un collo
    da periscopio), così si leggono nella stessa inquadratura della A."""

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
    return NECK + [fr.pt(q), fr.pt(q + V(0, -0.06, 0.04))], NECK_R + [0.060, 0.064]


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


def bande_collo(collo, s_top, p):
    """Le bande nere del pesce arciere di traverso sul collo: larghe sul dorso, si stringono a cuneo verso la
    gola, che resta gialla chiara (come le bande del pesce, che non arrivano alla pancia)."""
    d, s, b = collo.query(p)
    wob = 0.004 * np.sin(p[:, 0] * 37.0 + p[:, 1] * 23.0) * np.sin(p[:, 2] * 19.0)
    s = s + wob
    w = 0.046 * np.clip((b + 0.85) / 0.6, 0.0, 1.0) ** 0.5
    out = np.zeros(len(p), F)
    for k in range(9):
        sk = s_top - 0.12 - 0.26 * k
        out = np.maximum(out, 1.0 - D.smooth01(np.abs(s - sk) - w, -0.006, 0.006))
    return out * (w > 0.004), np.clip(0.5 - 0.6 * b, 0.0, 1.0) ** 1.5


def vertebre(collo, s_top):
    """Le vertebre che sporgono lungo il dorso del collo."""
    parts = []
    for sv in np.arange(0.45, s_top - 0.08, 0.055):
        i = int(np.searchsorted(collo.s, sv))
        c, bk = collo.P[i], collo.B[i]
        r = float(np.interp(sv / collo.s[-1], np.linspace(0, 1, len(NECK_R)), NECK_R))
        parts.append(sdf.sphere(c + bk * r * 0.80, 0.017))
    return sdf.union(*parts)


def branchie(collo, s_top):
    """Tre fessure per lato sul collo, sotto la testa: corte lungo il collo, lunghe attorno."""
    slit = sdf.ellipsoid(V(0, 0, 0), (0.008, 0.026, 0.0055))      # (profondità, attorno al collo, lungo il collo)
    parts = []
    for j in range(3):
        sv = s_top - 0.15 - 0.032 * j
        i = int(np.searchsorted(collo.s, sv))
        c, t, bk = collo.P[i], collo.T[i], collo.B[i]
        lat = np.cross(t, bk)
        r = float(np.interp(sv / collo.s[-1], np.linspace(0, 1, len(NECK_R)), NECK_R))
        for s in (-1, 1):
            q = c + lat * s * r - bk * 0.010
            M = np.stack([lat, bk, t], axis=1).astype(F)
            parts.append(lambda p, q=q, M=M: slit((p - q) @ M))
    return sdf.union(*parts)


# ───────────────────────── la pistola ad acqua ─────────────────────────
# Costruita in un sistema locale: y lungo la canna (verso la lampara), z in su, x di fianco (+x verso la
# macchina da presa). L'origine è la cima dell'impugnatura.

def gun_frame():
    y = GUN_AIM
    z = unit(V(0, 0, 1) - (V(0, 0, 1) @ y) * y)
    x = np.cross(y, z)
    return np.stack([x, y, z], axis=1).astype(F)


GM = gun_frame()


def gp(q):
    """Punto locale della pistola → mondo."""
    return GUN + GM @ V(*q)


def gfield(f):
    """Campo locale della pistola → mondo."""
    return lambda p: f((p - GUN) @ GM)


GRIP0, GRIP1 = V(0, -0.008, 0.010), V(0, -0.052, -0.104)   # asse dell'impugnatura (locale)


def squash_x(f, k):
    """Campo schiacciato di fianco (x) del fattore k."""
    return lambda p: f(p * V(1.0 / k, 1.0, 1.0)) * k


def pistola():
    """La pistola ad acqua del negozio: corpo arancione, canna con due anelli, mirino, grilletto nel
    ponticello, il serbatoio trasparente sopra (con dentro l'acqua torbida) e il tappo azzurro, l'ugello
    bianco in punta."""
    body = sdf.box((0, 0.040, 0.032), (0.0165, 0.072, 0.029), rounding=0.013)
    barrel = sdf.round_cone(V(0, 0.100, 0.046), V(0, 0.205, 0.050), 0.0165, 0.0115)
    rings = sdf.union(*[D.torus_axis(V(0, y, 0.046 + 0.004 * (y - 0.1) / 0.105), (0, 1, 0), 0.0165 - 0.005 * (y - 0.1) / 0.105, 0.0026) for y in (0.135, 0.168)])
    grip = squash_x(chain([GRIP0, (GRIP0 + GRIP1) / 2 + V(0, 0.004, 0), GRIP1], [0.021, 0.020, 0.023], k=0.01), 0.72)
    guard = sdf.intersect(D.torus_axis((0, 0.034, -0.004), (1, 0, 0), 0.025, 0.0045), sdf.plane(V(0, 0, 1), -0.004))
    trigger = sdf.round_cone(V(0, 0.026, 0.004), V(0, 0.033, -0.020), 0.0055, 0.0040)
    sight = sdf.box((0, 0.192, 0.064), (0.0028, 0.007, 0.006), rounding=0.002)
    neck = sdf.round_cone(V(0, -0.010, 0.055), V(0, -0.010, 0.075), 0.020, 0.024)    # dove si avvita il serbatoio
    f = sdf.union(body, barrel, rings, grip, guard, trigger, sight, neck, k=0.004)
    box = [gp((x, y, z)) for x in (-0.03, 0.03) for y in (-0.10, 0.24) for z in (-0.13, 0.08)]
    obs = [fine('Pistol', gfield(f), [np.array(box)], plastica_arancio(), pad=0.01, res=0.0016)]
    tank = sdf.ellipsoid(V(0, -0.010, 0.100), (0.036, 0.050, 0.040))
    c = gp((0, -0.010, 0.100))
    obs.append(D.mesh('PistolTank', gfield(sdf.shell(tank, 0.0022)), c - 0.08, c + 0.08, D.glass('ArchieTank', (1.0, 0.62, 0.30), rough=0.22), res=0.0016))
    water = sdf.intersect(sdf.ellipsoid(V(0, -0.010, 0.100), (0.0325, 0.0465, 0.0365)), sdf.plane(V(0, 0.15, 1), -0.088))
    obs.append(D.mesh('PistolWater', gfield(water), c - 0.08, c + 0.08, D.mat_simple('ArchieTankWater', (0.45, 0.50, 0.18), rough=0.08, coat=0.6, transmission=0.6), res=0.0016))
    cap = sdf.round_cone(V(0, -0.016, 0.133), V(0, -0.016, 0.147), 0.0135, 0.0125)
    c = gp((0, -0.016, 0.14))
    obs.append(D.mesh('PistolCap', gfield(cap), c - 0.03, c + 0.03, D.vinyl('ArchieCap', (0.02, 0.38, 0.52)), res=0.0012))
    nozzle = sdf.round_cone(V(0, 0.202, 0.050), V(0, 0.224, 0.0505), 0.0078, 0.0036)
    c = gp((0, 0.212, 0.05))
    obs.append(D.mesh('PistolNozzle', gfield(nozzle), c - 0.03, c + 0.03, D.vinyl('ArchieNozzle', (0.82, 0.80, 0.72)), res=0.001))
    return obs


def mano():
    """La mano fusa nella pistola, in coordinate della pistola: il palmo dalla parte lontana
    dell'impugnatura, tre dita lunghissime che ci girano attorno davanti e finiscono dalla parte di chi
    guarda, coi polpastrelli neri affondati nella plastica; l'indice sul grilletto, il pollice che scavalca
    il corpo sotto il serbatoio e ci si incolla; tre radici di carne partono dalle dita e strisciano sul
    fianco della pistola fino alla canna; un collare gonfio dove l'impugnatura sparisce nel polso.
    Restituisce il campo locale, il polso e le punte delle dita (locali)."""
    a = unit(GRIP1 - GRIP0)
    e1 = unit(V(0, 1, 0) - (V(0, 1, 0) @ a) * a)            # avanti, perpendicolare all'impugnatura
    e2 = V(1, 0, 0)                                         # di fianco, verso chi guarda
    wrist = V(-0.010, -0.080, -0.080)
    palm = D.ellipsoid_rot(V(-0.016, -0.040, -0.034), (0.020, 0.030, 0.046), sdf.rot_matrix('x', -20))
    parts = [palm, sdf.round_cone(wrist, V(-0.016, -0.046, -0.050), 0.021, 0.022)]
    punte = []
    for k in range(3):
        c = GRIP0 + (GRIP1 - GRIP0) * (0.30 + 0.24 * k)
        pts = []
        for th in np.linspace(math.pi + 0.25, -0.25, 9):
            sink = 1.0 if th > 0.30 else 0.82                     # in fondo il polpastrello affonda nella plastica
            pts.append(c + (e2 * math.cos(th) * 0.0255 + e1 * math.sin(th) * 0.031) * sink)
        f, cp = tubo(pts, 0.0098 - 0.0006 * k, 0.0070 - 0.0005 * k, n=5, nodi=0.24)
        parts.append(f)
        punte.append(cp[-4:])
    idx, cp = tubo([V(-0.020, -0.016, 0.002), V(-0.022, 0.006, -0.004), V(-0.014, 0.022, -0.012), V(-0.004, 0.027, -0.014)], 0.0098, 0.0072, n=5, nodi=0.16)
    parts.append(idx)
    punte.append(cp[-2:])
    th, cp = tubo([V(-0.014, -0.044, 0.010), V(-0.004, -0.050, 0.040), V(0.012, -0.040, 0.050), V(0.020, -0.018, 0.046)], 0.0105, 0.0075, n=5, nodi=0.16)
    parts.append(th)
    punte.append(cp[-3:])
    # la membrana tra l'indice e il dito sotto
    parts.append(sdf.ellipsoid(V(-0.021, -0.006, -0.014), (0.004, 0.018, 0.012)))
    # le radici di carne: dalle dita e dal pollice strisciano sul fianco della pistola verso la canna
    for (y0, z0), dz, L in (((-0.020, 0.040), 0.040, 0.075), ((0.006, -0.004), 0.016, 0.10), ((0.022, -0.012), 0.004, 0.055)):
        f, _ = tubo([V(0.020, y0, z0), V(0.0185, y0 + 0.02, dz), V(0.0178, y0 + 0.02 + L * 0.6, dz + 0.004), V(0.012, y0 + 0.02 + L, dz + 0.002)], 0.0045, 0.0018, n=5)
        parts.append(f)
    collar = D.torus_axis(GRIP1 + a * -0.010 + V(0, -0.004, 0), a, 0.022, 0.011)
    parts.append(collar)
    return sdf.union(*parts, k=0.006), wrist, np.concatenate(punte)


# ───────────────────────── il corpo ─────────────────────────

def corpo(fr, head_local, attacco, cut_local=None, attrs_testa=None):
    """La mesh della pelle: collo, braccio, mano sulla pistola e testa, con gli attributi del colore.
    attrs_testa(q) → (ventre, seconda) in coordinate locali della testa, oppure None per i punti fuori
    dalla testa."""
    pts, radii = neck_path(fr, attacco)
    collo = Collo(pts)
    s_top = float(collo.s[np.argmin(np.linalg.norm(collo.P - fr.pt(attacco), axis=1))])
    neck = sdf.union(chain(pts, radii, k=0.05), vertebre(collo, s_top), k=0.010)
    hand_l, wrist_l, punte_l = mano()
    wrist = gp(wrist_l)
    upper, _ = tubo([SHOULDER, (SHOULDER + ELBOW) / 2 + V(-0.03, 0.0, 0.0), ELBOW], 0.030, 0.025, n=6)
    fore, _ = tubo([ELBOW, (ELBOW + wrist) / 2 + V(-0.035, 0.0, 0.0), wrist], 0.025, 0.020, n=8)
    head = entro(fr.field(head_local), HEAD - 0.36, HEAD + 0.36)
    hand = entro(gfield(hand_l), GUN - 0.16, GUN + 0.16)
    f = sdf.union(neck, upper, fore, sdf.sphere(ELBOW, 0.032), hand, head, k=0.03)
    cut = branchie(collo, s_top)
    if cut_local is not None:
        cut = sdf.union(cut, entro(fr.field(cut_local), HEAD - 0.32, HEAD + 0.32))
    f = sdf.subtract(f, cut, k=0.005)

    # attributi: la testa decide per sé, il braccio è giallo coi polpastrelli neri (come le pinne del pesce
    # arciere, orlate di nero), il collo ha le bande e la gola chiara
    braccio = cKDTree(np.concatenate([catmull([SHOULDER, ELBOW, wrist], 12), [gp(q) for q in punte_l]]))
    punte = cKDTree(np.array([gp(q) for q in punte_l]))

    def colore(p):
        sec, ven = bande_collo(collo, s_top, p)
        dn, _, _ = collo.query(p)
        da, _ = braccio.query(p, k=1, workers=-1)
        dt, _ = punte.query(p, k=1, workers=-1)
        arm = da < dn
        ven = np.where(arm, 0.45, ven).astype(F)
        sec = np.where(arm, 1.0 - D.smooth01(dt.astype(F), 0.016, 0.024), sec).astype(F)
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

    attrs = {'ventre': lambda p: get(p, 0), 'seconda': lambda p: get(p, 1)}
    return f, attrs


def pelle_mesh(f, attrs, extra=None):
    a = dict(attrs)
    a.update(extra or {})
    ob = sdf_object('ArchieSkin', f, V(-0.48, -0.30, 1.10), V(0.22, 0.62, 2.68), res=RES_BODY, attrs=a, banded=True)
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


def comune(obs):
    """Quello che hanno tutte e tre: la pistola e l'acqua che gocciola dall'ugello."""
    tip = gp((0, 0.226, 0.049))
    return obs + pistola() + [bava('PistolDrip', gocce=[(tip + V(0, 0, -0.004), 0.035)])]


# ───────────────────────── le teste ─────────────────────────

def sulla_pelle(f, pts, off=0.0, iters=6, eps=0.0008):
    """Porta i punti (locali) sulla superficie del campo f (locale) e li stacca di 'off' lungo la normale:
    così i capelli stanno appiccicati alla pelle invece di affondare nella fronte o volarle sopra."""
    P = np.array(pts, F)
    for _ in range(iters + 1):
        g = np.stack([f(P + e) - f(P - e) for e in np.eye(3, dtype=F) * eps], axis=1)
        n = g / (np.linalg.norm(g, axis=1, keepdims=True) + 1e-9)
        P = P - f(P)[:, None] * n
    return P + n * off


def bande_testa(q, barre, zmin=-0.20):
    """Bande nere di traverso sulla testa (verticali, come sul pesce): barre = [(y centro, mezza larghezza in
    alto, mezza larghezza in basso)], in coordinate locali; svaniscono sotto zmin (la gola resta chiara)."""
    out = np.zeros(len(q), F)
    z = np.clip((q[:, 2] + 0.10) / 0.20, 0.0, 1.0)
    for yc, wt, wb in barre:
        w = wb + (wt - wb) * z
        wob = 0.004 * np.sin(q[:, 2] * 90.0 + yc * 40.0)
        out = np.maximum(out, 1.0 - D.smooth01(np.abs(q[:, 1] - yc + wob) - w, -0.0025, 0.0025))
    return out * D.smooth01(q[:, 2], zmin - 0.015, zmin + 0.015)


def archie_a():
    """A · Arciere: la testa del pesce arciere. Stretta e alta, il profilo del dorso dritto fino alla punta
    del muso, gli occhi enormi in alto sotto il filo del dorso; la mandibola sporge oltre il muso e sale, e
    in punta la bocca è un anellino di labbra attorno a un buco tondo: la canna da cui sputa. Una banda
    nera passa sugli occhi, un'altra sulla nuca."""
    fr = frame(1.15)                                   # un po' più grande del vero, come le teste B e C
    mass = sdf.ellipsoid(V(0, 0.01, -0.02), (0.070, 0.21, 0.105))
    snout = sdf.round_cone(V(0, -0.10, -0.005), V(0, -0.240, 0.000), 0.058, 0.010)
    head = sdf.intersect(sdf.union(mass, snout, k=0.05), sdf.plane(V(0, -0.20, 1.0), -0.052), k=0.06)   # dorso dritto
    jaw = chain([V(0, -0.02, -0.085), V(0, -0.16, -0.046), V(0, -0.268, 0.004)], [0.048, 0.028, 0.0105], k=0.02)
    sdir = unit(V(0, -1.0, 0.35))                                                       # dove sputa
    spout = D.torus_axis(V(0, -0.263, 0.010), sdir, 0.0105, 0.0048)
    bulges = sdf.union(*[sdf.ellipsoid(V(s * 0.050, -0.088, 0.034), (0.030, 0.042, 0.036)) for s in (-1, 1)])
    operc = sdf.union(*[D.ellipsoid_rot(V(s * 0.050, 0.075, -0.028), (0.024, 0.055, 0.075), sdf.rot_matrix('x', -15)) for s in (-1, 1)])
    head = sdf.union(head, jaw, spout, bulges, operc, k=0.02)
    # la bocca: uno squarcio corto e obliquo dalla punta agli angoli, e il buco tondo in punta
    gape = [V(0, -0.258, 0.006), V(0.026, -0.226, -0.012), V(0.036, -0.192, -0.030)]
    hole = sdf.round_cone(V(0, -0.263, 0.010) + sdir * 0.012, V(0, -0.263, 0.010) - sdir * 0.025, 0.0062, 0.0050)
    mouth = sdf.union(*[chain([gape[0], gape[1] * V(s, 1, 1), gape[2] * V(s, 1, 1)], [0.0035, 0.0040, 0.0028], k=0.003) for s in (-1, 1)], hole)
    edge = sdf.union(*[chain([V(s * 0.068, 0.020, 0.055), V(s * 0.074, 0.050, -0.010), V(s * 0.064, 0.030, -0.085)], [0.0035, 0.0040, 0.0030], k=0.002) for s in (-1, 1)])
    nares = sdf.union(*[sdf.sphere(V(s * 0.018, -0.190, 0.010), 0.0050) for s in (-1, 1)])
    sockets = sdf.union(*[sdf.sphere(V(s * 0.060, -0.088, 0.036), 0.028) for s in (-1, 1)])

    def testa(q):
        m = sdf.ellipsoid(V(0, -0.02, -0.01), (0.12, 0.30, 0.16))(q) < 0.0
        ven = np.clip(0.5 - q[:, 2] / 0.12, 0.0, 1.0)
        sec = bande_testa(q, [(-0.088, 0.036, 0.022), (0.105, 0.032, 0.024)], zmin=-0.085)
        return ven, sec, m

    def bocca(p):
        q = fr.local(p)
        return (mouth(q) < 0.005).astype(F)

    f, attrs = corpo(fr, head, (0, 0.14, -0.085), cut_local=sdf.union(mouth, edge, nares, sockets), attrs_testa=testa)
    obs = [pelle_mesh(f, attrs, {'mouth': bocca})]
    pairs = []
    for s in (-1, 1):
        lato = catmull([gape[0], gape[1] * V(s, 1, 1), gape[2] * V(s, 1, 1)], 3)
        for a in lato[1:-1]:
            pairs.append((fr.pt(a + V(0, 0.002, -0.0050)), fr.pt(a + V(0, 0.002, 0.0020)), 0.0020 * fr.k))   # sulla mandibola, in su
    obs.append(D.teeth_mesh('ArchieTeeth', pairs, D.needle_teeth()))
    obs += D.eyes('ArchieEye', [fr.pt((s * 0.060, -0.088, 0.036)) for s in (-1, 1)], 0.031 * fr.k, AIM)
    tip = fr.pt((0, -0.268, -0.002))
    obs.append(bava('ArchieSlime', fili=[(fr.pt((0.022, -0.226, -0.002)), fr.pt((0.024, -0.226, -0.012)), 0.004)],
                    gocce=[(tip, 0.05), (fr.pt((-0.030, -0.200, -0.024)), 0.03)]))
    return (comune(obs), *TESTI['A'])


def archie_b():
    """B · Cerbottana: il cranio tondo e le orecchie di un bambino, ma gli occhi sono saliti in cima alla
    testa, su due cupole di carne; il naso non c'è più e la bocca è un tubo di carne ad anelli che finisce
    in due labbra a ciambella, puntato alla luce come una cerbottana."""
    fr = frame(TESTONE)
    tdir = unit(V(0, -1.0, 0.20))
    t0, t1 = V(0, -0.060, -0.036), V(0, -0.060, -0.036) + tdir * 0.205
    cran = sdf.ellipsoid(V(0, 0.045, 0.022), (0.084, 0.100, 0.098))
    mounds = sdf.union(*[sdf.ellipsoid(V(s * 0.042, -0.035, 0.084), (0.033, 0.036, 0.030)) for s in (-1, 1)])
    brow = sdf.ellipsoid(V(0, -0.064, 0.046), (0.066, 0.030, 0.024))
    cheeks = sdf.union(*[sdf.sphere(V(s * 0.048, -0.044, -0.042), 0.040) for s in (-1, 1)])
    tube = sdf.round_cone(t0, t1, 0.050, 0.020)

    def anelli(q):
        """Gli anelli del tubo, come un tubo di gomma."""
        u = (q - t0) @ tdir
        on = D.smooth01(u, 0.04, 0.07) * (1.0 - D.smooth01(u, 0.18, 0.20))
        return (np.sin(u * 150.0) * 0.5 + 0.5) * on

    tube = sdf.displace(tube, anelli, 0.0028)
    lips = D.torus_axis(t1 + tdir * 0.002, tdir, 0.016, 0.0095)
    # le orecchie a sventola: attaccate davanti, il bordo libero dietro che si stacca dal cranio, la conca
    # che guarda in fuori e in avanti (verso chi guarda)
    ec = [V(s * 0.094, 0.030, 0.004) for s in (-1, 1)]
    en = [V(s * math.cos(math.radians(38)), -math.sin(math.radians(38)), 0) for s in (-1, 1)]
    ears = sdf.union(*[D.ellipsoid_rot(c, (0.012, 0.028, 0.044), sdf.rot_matrix('z', -s * 38)) for s, c in zip((-1, 1), ec)])
    helix = sdf.union(*[sdf.intersect(D.torus_axis(c + n * 0.007, n, 0.024, 0.0045), sdf.plane(V(0, 0, -1), -0.010)) for c, n in zip(ec, en)])
    head = sdf.union(cran, mounds, brow, cheeks, tube, lips, ears, helix, k=0.018)
    hole = sdf.round_cone(t1 + tdir * 0.02, t1 - tdir * 0.03, 0.0085, 0.0070)
    slits = sdf.union(*[D.ellipsoid_rot(V(s * 0.012, -0.112, 0.016), (0.0035, 0.010, 0.003), sdf.rot_matrix('x', -10)) for s in (-1, 1)])
    concha = sdf.union(*[D.ellipsoid_rot(c + n * 0.010 + V(0, -0.004, -0.006), (0.006, 0.010, 0.016), sdf.rot_matrix('z', -s * 38)) for s, c, n in zip((-1, 1), ec, en)])
    sockets = sdf.union(*[sdf.sphere(V(s * 0.042, -0.048, 0.094), 0.022) for s in (-1, 1)])

    # le lentiggini del bambino sulle guance gonfie: puntini bruni (metà del nero delle bande)
    rng = np.random.default_rng(8)
    lent = []
    for s in (-1, 1):
        for _ in range(18):
            lent.append(V(s * 0.048, -0.044, -0.042) + unit(V(s * rng.uniform(0.2, 1.0), rng.uniform(-1.0, -0.1), rng.uniform(-0.3, 0.7))) * 0.040)
    lent = cKDTree(np.array(lent, F))

    def testa(q):
        m = sdf.ellipsoid(V(0, -0.05, 0.0), (0.14, 0.27, 0.17))(q) < 0.0
        ven = np.clip(0.55 - (q[:, 2] + 0.01) / 0.10, 0.0, 1.0)
        sec = bande_testa(q, [(-0.046, 0.032, 0.020)], zmin=0.02)          # le macchie nere attorno agli occhi
        sec = np.maximum(sec, bande_testa(q, [(0.085, 0.024, 0.018)], zmin=-0.06))   # la banda dietro le orecchie
        d, _ = lent.query(q, k=1, workers=-1)
        sec = np.maximum(sec, 0.5 * (1.0 - D.smooth01(d.astype(F), 0.0038, 0.0052)))
        return ven, sec, m

    def bocca(p):
        q = fr.local(p)
        return np.maximum((hole(q) < 0.004).astype(F), (concha(q) < 0.002).astype(F) * 0.55)

    f, attrs = corpo(fr, head, (0, 0.06, -0.090), cut_local=sdf.union(hole, slits, concha, sockets), attrs_testa=testa)
    obs = [pelle_mesh(f, attrs, {'mouth': bocca})]
    # dentini da latte in cerchio dentro il buco
    pairs = []
    lat = unit(np.cross(tdir, V(0, 0, 1)))
    up = np.cross(lat, tdir)
    for k in range(8):
        a = 2 * math.pi * k / 8
        r = lat * math.cos(a) + up * math.sin(a)
        base = t1 - tdir * 0.004 + r * 0.0105
        pairs.append((fr.pt(base), fr.pt(base - r * 0.006 + tdir * 0.002), 0.0022 * fr.k))
    obs.append(D.teeth_mesh('ArchieTeeth', pairs))
    obs += D.eyes('ArchieEye', [fr.pt((s * 0.042, -0.050, 0.094)) for s in (-1, 1)], 0.0235 * fr.k, AIM)
    tip = fr.pt(t1 + tdir * 0.006 + V(0, 0, -0.012))
    obs.append(bava('ArchieSlime', gocce=[(tip, 0.06), (fr.pt(t1 + V(0.010, -0.002, -0.010)), 0.035)]))
    strands, hp = [], []
    for a in (-1.25, -1.0, -0.8, -0.6, -0.35, 0.25, 0.65):   # pochi capelli radi, incollati al cranio
        q = [V(0, 0.045, 0.022) + unit(d) * np.array((0.086, 0.102, 0.100), F) for d in ((a * 0.3, 0.2, 1.0), (a, 0.55, 0.65), (a * 1.1, 0.75, 0.0))]
        q = [fr.pt(x) for x in sulla_pelle(head, q, off=0.004)]
        strands.append(tubo(q, 0.0075 * fr.k, 0.0025 * fr.k, n=6)[0])
        hp.append(q)
    obs.append(fine('ArchieHair', sdf.union(*strands, k=0.006), hp, D.wet_hair(), res=RES_FINE))
    return (comune(obs), *TESTI['B'])


def archie_c():
    """C · Bambino: la faccia del bambino che sfidava tutti a duello. Le guance gonfie d'acqua, le labbra
    strette a beccuccio per sputare, un occhio chiuso per prendere la mira e l'altro spalancato, bianco e
    enorme; le bande nere del pesce gli scendono sugli occhi come la pittura da guerra; la frangia bagnata
    incollata alla fronte."""
    # la faccia si gira un po' verso chi guarda (la mira la prende l'occhio aperto, sopra la pistola)
    fr = frame(TESTONE, dyaw=-20.0)
    sdir = unit(V(0, -1.0, 0.30))
    cran = sdf.ellipsoid(V(0, 0.010, 0.015), (0.082, 0.092, 0.100))
    cheeks = sdf.union(*[sdf.sphere(V(s * 0.044, -0.056, -0.042), 0.042) for s in (-1, 1)])
    chin = sdf.sphere(V(0, -0.060, -0.092), 0.024)
    nose = sdf.sphere(V(0, -0.094, -0.004), 0.0125)
    brow = sdf.ellipsoid(V(0, -0.078, 0.034), (0.064, 0.020, 0.015))
    ears = sdf.union(*[sdf.ellipsoid(V(s * 0.084, 0.006, -0.010), (0.013, 0.024, 0.032)) for s in (-1, 1)])
    mc = V(0, -0.100, -0.060)
    lips = D.torus_axis(mc, sdir, 0.0115, 0.0090)
    lid = D.ellipsoid_rot(V(0.035, -0.080, 0.012), (0.022, 0.013, 0.016), sdf.rot_matrix('y', -8))    # l'occhio chiuso, gonfio
    head = sdf.union(cran, cheeks, chin, nose, brow, ears, lips, lid, k=0.024)
    hole = sdf.round_cone(mc + sdir * 0.012, mc - sdir * 0.012, 0.0055, 0.0045)
    socket = sdf.sphere(V(-0.035, -0.074, 0.012), 0.021)
    crease = chain([V(0.014, -0.092, 0.010), V(0.035, -0.0935, 0.008), V(0.056, -0.087, 0.012)], [0.0020, 0.0028, 0.0020], k=0.002)
    crow = sdf.union(*[chain([V(0.060, -0.080, 0.012 + dz), V(0.072, -0.068, 0.016 + 1.8 * dz)], [0.0016, 0.0010], k=0.001) for dz in (-0.008, 0.0, 0.008)])
    nostrils = sdf.union(*[sdf.sphere(V(s * 0.0065, -0.100, -0.012), 0.0035) for s in (-1, 1)])

    def testa(q):
        m = sdf.ellipsoid(V(0, -0.01, -0.01), (0.13, 0.15, 0.16))(q) < 0.0
        ven = np.clip(0.80 - np.maximum(q[:, 1] + 0.05, 0.0) * 6.0 - np.maximum(q[:, 2] - 0.06, 0.0) * 6.0, 0.25, 0.85)
        # pittura da guerra: una striscia nera dritta su ogni occhio, dalla fronte alla guancia
        stripe = np.zeros(len(q), F)
        for s in (-1, 1):
            w = 0.0125 + 0.004 * np.clip((q[:, 2] - 0.0) / 0.08, 0.0, 1.0)
            wob = 0.002 * np.sin(q[:, 2] * 120.0 + s)
            stripe = np.maximum(stripe, 1.0 - D.smooth01(np.abs(q[:, 0] - s * 0.035 + wob) - w, -0.002, 0.002))
        stripe *= D.smooth01(q[:, 2], -0.070, -0.055) * (q[:, 1] < -0.02)
        # la pittura lascia scoperti gli occhi: quello aperto resta bianco in un anello giallo, quello chiuso
        # si legge come una palpebra gonfia con la piega
        de = np.minimum(np.linalg.norm(q - V(-0.035, -0.074, 0.012), axis=1), np.linalg.norm(q - V(0.035, -0.084, 0.012), axis=1))
        stripe *= D.smooth01(de, 0.022, 0.026)
        sec = np.maximum(stripe, bande_testa(q, [(0.060, 0.026, 0.020)], zmin=-0.08))   # la banda dietro le orecchie
        return ven, sec, m

    def blush(p):
        q = fr.local(p)
        d = np.minimum(np.linalg.norm(q - V(0.064, -0.066, -0.046), axis=1), np.linalg.norm(q - V(-0.064, -0.066, -0.046), axis=1))
        return np.clip(1.0 - d / 0.024, 0.0, 1.0)

    def bocca(p):
        q = fr.local(p)
        return np.maximum((hole(q) < 0.003).astype(F), (crease(q) < 0.0025).astype(F) * 0.75)

    cut = sdf.union(hole, socket, crease, crow, nostrils)
    f, attrs = corpo(fr, head, (0, 0.035, -0.088), cut_local=cut, attrs_testa=testa)
    obs = [pelle_mesh(f, attrs, {'mouth': bocca, 'blush': blush})]
    obs += D.eyes('ArchieEye', [fr.pt((-0.035, -0.071, 0.012))], 0.0200 * fr.k, AIM)
    tip = fr.pt(mc + sdir * 0.016 + V(0, 0, -0.008))
    obs.append(bava('ArchieSlime', fili=[(fr.pt(mc + V(-0.008, -0.004, -0.008)), fr.pt(mc + V(0.010, -0.004, -0.009)), 0.004)],
                    gocce=[(tip, 0.07), (fr.pt((0.030, -0.088, -0.074)), 0.045), (fr.pt((-0.028, -0.090, -0.072)), 0.03)]))
    # la frangia bagnata incollata alla fronte, il resto dei capelli appiccicato al cranio
    strands, hp = [], []
    hc, hr = V(0, 0.010, 0.015), np.array((0.084, 0.094, 0.102), F)
    rng = np.random.default_rng(5)
    for a in np.linspace(-1, 1, 15):
        L = rng.uniform(0.0, 1.0)                               # ciocche di lunghezza diversa, appuntite
        q = [V(0.012 * a, 0.060, 0.112), V(0.036 * a, -0.030, 0.116), V(0.044 * a, -0.078, 0.085), V(0.047 * a, -0.098, 0.054 - 0.014 * L)]
        q = [fr.pt(x) for x in sulla_pelle(head, q, off=0.0055)]
        strands.append(tubo(q, 0.0090 * fr.k, 0.0016 * fr.k, n=6)[0])
        hp.append(q)
    for a in (-1.0, -0.6, 0.6, 1.0):
        q = [hc + unit(d) * hr for d in ((0.3 * a, 0.5, 1.0), (a, 0.6, 0.3), (a, 0.5, -0.35))]
        q = [fr.pt(x) for x in sulla_pelle(head, q, off=0.006)]
        strands.append(tubo(q, 0.0090 * fr.k, 0.0030 * fr.k, n=6)[0])
        hp.append(q)
    obs.append(fine('ArchieHair', sdf.union(*strands, k=0.004), hp, D.wet_hair(), res=RES_FINE))
    return (comune(obs), *TESTI['C'])


# ───────────────────────── tavola ─────────────────────────

# le luci di dettagli.setup sono riferite a 'subject': la luce calda deve venire dalla lampara, davanti a
# lui in alto a sinistra, quindi il riferimento sta dove la lampara è a (−1,0; −1,5; −0,15) da lui
D.CREATURES['archie'] = {
    'title': 'ARCHIE — dettagli della testa (notte 3, sagoma C «Periscopio»), mira alla lampara · colori: proposta da approvare',
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
