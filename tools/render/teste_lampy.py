"""
LAMPY — dettagli della testa (notte 4, sagoma C «Sanguisuga», più grossa), da scegliere insieme.

Come per la prima notte (dettagli.py): il corpo della sagoma scelta e tre teste, da "più pesce" (A) a
"più bambina" (C), con addosso la cuffia da piscina di gomma a fiori. Lampy viene dalla lampreda: la bocca
è una ventosa rotonda piena di anelli di denti, sette pori branchiali per lato, il corpo d'anguilla.
Sta attaccata alla lenza per i due capi, come una sanguisuga che cammina: la testa in alto, con la lenza
che le entra in bocca, la coda più in basso con la ventosa di dietro; in mezzo un arco di carne grosso e
pesante (l'utente la vuole più grossa della sagoma). La lenza è nella scena come riferimento.

Bozze di studio: non sono i modelli definitivi del gioco. Usa materiali, luci, render e tavola di
dettagli.py, che resta com'è: la creatura si registra in D.CREATURES quando il modulo viene caricato.

Uso: tools/.venv/bin/python tools/render/teste_lampy.py [--fast] [--only A|B|C]
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
from common import set_lightgroup  # noqa: E402
from creature import sdf_object, teeth_material  # noqa: E402
from dettagli import Frame, V, chain, ellipsoid_rot, mat_simple, torus_axis, unit  # noqa: E402
from geo import catmull, rbox, tube  # noqa: E402

F = np.float32
FAST = D.FAST
SKIN_RES = 0.0045 if FAST else 0.003      # la pelle si estrae a fasce (sdf.mesh_banded): pori e anelli restano

# ───────────────────────── la lenza ─────────────────────────
# Dalla punta della canna (in alto, verso la barca: −Y) all'acqua (lontano: +Y). Lampy ci sta attaccata
# con la bocca in alto e con la coda più in basso; l'arco del corpo sta dalla parte di NL (verso l'alto).

LINE0 = V(0.0, -1.00, 2.80)
DL = V(0.0, 0.5, -0.8660254)              # giù per la lenza (60° sotto l'orizzonte: l'arco viene alto e stretto)
LINE1 = LINE0 + DL * 3.6
NL = V(0.0, -DL[2], DL[1])                # perpendicolare alla lenza, dalla parte dell'arco
MOUTH = LINE0 + DL * 1.0                  # dove la lenza entra in bocca
TAIL = LINE0 + DL * 2.40                  # dove la ventosa della coda si attacca
CAM = ((-1.97, -2.05, 2.56), (0, -0.08, 1.44), 52)


# La testa sta dritta e guarda chi guarda, girata di 30° verso la barca e un po' in su (verso la canna);
# il collo esce dalla nuca e sale nell'arco. La lenza le entra in bocca di sbieco, da sopra.
_c = unit(V(*CAM[0]) - MOUTH)
_w = unit(V(0, -1, 0.35) - (V(0, -1, 0.35) @ _c) * _c)
FACE = unit(_c * math.cos(math.radians(30)) + _w * math.sin(math.radians(30)))
UP = V(0, 0, 1)


class Head(Frame):
    """Sistema locale della testa con faccia (−Y locale) e alto (+Z locale) in direzioni qualsiasi."""

    def __init__(self, pos, face, up):
        y = -unit(face)
        z = unit(V(*up) - (V(*up) @ y) * y)
        self.pos = V(*pos)
        self.R = np.stack([np.cross(y, z), y, z], axis=1).astype(F)


def line_pt(s):
    return LINE0 + DL * s


# ───────────────────────── aiuti ─────────────────────────

def bounded(f, c, R, margin=0.05):
    """Valuta f solo vicino alla sfera (c, R) che contiene le sue forme; fuori basta la distanza dalla
    sfera, che con il margine non tocca le unioni morbide (k < margin)."""
    c = V(*c)

    def g(p):
        d = np.linalg.norm(p - c, axis=1) - R
        out = d.astype(F)
        m = d < margin
        if m.any():
            out[m] = f(p[m])
        return out
    return g


def ellipsoid_axes(c, radii, ax, ay, az):
    """Ellissoide con gli assi lungo tre direzioni del mondo (ortogonali)."""
    M = np.stack([unit(ax), unit(ay), unit(az)], axis=1).astype(F)
    c = V(*c)
    e = sdf.ellipsoid(V(0, 0, 0), radii)
    return lambda p: e((p - c) @ M)


def snap(field, pts, iters=5, eps=0.0015):
    """Porta i punti sulla superficie del campo; restituisce punti e normali."""
    p = np.atleast_2d(np.asarray(pts, F)).copy()
    n = None
    for _ in range(iters):
        d = field(p)
        g = np.stack([field(p + e) - field(p - e) for e in np.eye(3, dtype=F) * eps], axis=1)
        n = (g / (np.linalg.norm(g, axis=1, keepdims=True) + 1e-9)).astype(F)
        p = (p - d[:, None] * n).astype(F)
    return p, n


def skin_mesh(name, field, lo, hi, mat, attrs=None, res=None):
    ob = sdf_object(name, field, lo, hi, res=res or SKIN_RES, attrs=attrs, banded=True)
    ob.data.materials.append(mat)
    return ob


def teeth(name, pairs, mat):
    """Come D.teeth_mesh, ma ogni dente si valuta solo vicino a sé e la superficie si estrae a fasce."""
    parts = []
    for b, t, r in pairs:
        b, t = V(*b), V(*t)
        parts.append(bounded(sdf.round_cone(b, t, r, r * 0.15), (b + t) / 2, float(np.linalg.norm(t - b)) / 2 + r, margin=0.01))
    pts = np.array([p for b, t, _ in pairs for p in (b, t)], F)
    rmin = min(r for _, _, r in pairs)
    return skin_mesh(name, sdf.union(*parts), pts.min(0) - 0.02, pts.max(0) + 0.02, mat, res=max(min(D.RES, rmin / 2.5), 0.0012))


def ring_teeth(fr, rings, out=(0, -1, 0), axis_c=(0, 0, 0), inward=0.45, phase=0.0):
    """Anelli concentrici di denti nel sistema della testa: rings = [(raggio, y, n, lung, r)].
    I denti escono dalla superficie (verso out) e puntano verso il centro, come nella lampreda."""
    pairs = []
    c0 = V(*axis_c)
    for k, (rho, y, n, L, r) in enumerate(rings):
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * (k % 2) + phase) / n
            radial = V(math.cos(a), 0.0, math.sin(a))
            base = c0 + radial * rho + V(0, y, 0)
            d = unit(V(*out) - radial * inward)
            pairs.append((fr.pt(base), fr.pt(base + d * L), r))
    return pairs


def water():
    w = rbox('Water', (120, 120, 0.01), (0, 40.0, -0.005), bevel=0.0, col='set')
    w.data.materials.append(mat_simple('NightWater', (0.004, 0.012, 0.016), rough=0.04, spec=0.8))
    set_lightgroup(w, 'ambient')
    return w


def fishing_line():
    """La lenza: un filo di nylon chiaro, un po' più spesso del vero perché si veda nella bozza."""
    pts = np.array([line_pt(s) for s in np.linspace(-0.3, 3.75, 40)])
    ob = tube('Lenza', pts, 0.0028, n=8, col='set')
    ob.data.materials.append(mat_simple('Nylon', (0.80, 0.80, 0.74), rough=0.18, coat=0.6, transmission=0.3))
    set_lightgroup(ob, 'ambient')
    return ob


# ───────────────────────── corpo: l'arco della sanguisuga ─────────────────────────

def arch_points(start, back):
    """Linea mediana: dalla nuca (start, verso back) su in un arco alto, poi giù fino alla ventosa della coda."""
    mid = (MOUTH + TAIL) / 2
    ctrl = [start,
            start + back * 0.28,
            mid - DL * 0.30 + NL * 0.58,
            mid + DL * 0.12 + NL * 0.64,
            TAIL - DL * 0.10 + NL * 0.48,
            TAIL + NL * 0.20,
            TAIL + NL * 0.07]
    return catmull(ctrl, 14).astype(F)


def arch_radius(u):
    """Spessore lungo il corpo (u = 0 alla testa, 1 alla coda): grosso e pesante in mezzo."""
    return np.interp(u, [0.0, 0.10, 0.30, 0.55, 0.78, 0.92, 1.0], [0.15, 0.19, 0.245, 0.25, 0.215, 0.16, 0.13]).astype(F)


class Arch:
    """Il corpo comune alle tre varianti: campo, attributi (ventre chiaro) e pori branchiali."""

    def __init__(self, start, back, neck_r=0.15):
        self.pts = arch_points(V(*start), unit(back))
        seg = np.linalg.norm(np.diff(self.pts, axis=0), axis=1)
        self.s = np.concatenate([[0.0], np.cumsum(seg)]).astype(F)
        self.u = self.s / self.s[-1]
        self.r = arch_radius(self.u)
        self.r[:4] = np.minimum(self.r[:4], np.linspace(neck_r, self.r[4], 4))
        tan = np.gradient(self.pts, axis=0)
        self.tan = tan / np.linalg.norm(tan, axis=1, keepdims=True)
        inner = -NL[None, :] - (self.tan @ -NL)[:, None] * self.tan     # lato concavo, verso la lenza
        self.inner = inner / (np.linalg.norm(inner, axis=1, keepdims=True) + 1e-9)
        self.tree = cKDTree(self.pts)
        self.n3 = sdf.Noise3(41)

    def base(self):
        idx = np.linspace(0, len(self.pts) - 1, 18).astype(int)
        body = chain([self.pts[i] for i in idx], [float(self.r[i]) for i in idx], k=0.06)
        # due pinne dorsali basse sul dorso, verso la coda (come la lampreda)
        fins = []
        for u0, u1, hgt in ((0.58, 0.72, 0.055), (0.76, 0.93, 0.075)):
            for u in np.linspace(u0, u1, 5):
                i = int(np.searchsorted(self.u, u))
                out = -self.inner[i]
                w = math.sin(math.pi * (u - u0) / (u1 - u0)) ** 0.6
                c = self.pts[i] + out * (self.r[i] + hgt * 0.35 * w)
                fins.append(ellipsoid_axes(c, (0.012, 0.05, hgt * w + 0.004), V(1, 0, 0), self.tan[i], out))
        # la ventosa della coda, schiacciata sulla lenza
        cup = ellipsoid_axes(TAIL + NL * 0.02, (0.20, 0.19, 0.075), V(1, 0, 0), DL, NL)
        lip = torus_axis(TAIL + NL * 0.0, NL, 0.17, 0.035)
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
        ends = np.clip((self.u[i] - 0.09) / 0.08, 0, 1) * np.clip((0.97 - self.u[i]) / 0.05, 0, 1)
        lumps = self.n3(p + 7.0, scale=0.05, octaves=2)
        return (-(0.0032 * rings * (0.6 + 0.8 * np.abs(wob)) + 0.010 * folds * inner ** 1.5) * ends + 0.006 * lumps).astype(F)

    def belly(self, p):
        _, i = self.tree.query(p, workers=-1)
        side = np.einsum('ij,ij->i', p - self.pts[i], self.inner[i]) / np.maximum(self.r[i], 1e-3)
        return np.clip(side * 1.4 - 0.2, 0.0, 1.0).astype(F)

    def field(self):
        return sdf.displace(self.base(), self.detail, 1.0)

    def gill_pores(self, field):
        """Sette pori branchiali per lato, in fila sul collo dietro la testa: buchi tondi con l'orlo."""
        holes, rims, allp = [], [], []
        for side in (-1, 1):
            want = []
            for k in range(7):
                i = int(np.searchsorted(self.s, 0.42 + 0.052 * k))
                c, r = self.pts[i], self.r[i]
                bn = unit(np.cross(self.tan[i], self.inner[i]))
                bn = bn if bn[0] * side > 0 else -bn
                want.append(c + bn * r * 0.93 + self.inner[i] * r * 0.30)
            pts, nrm = snap(field, want)
            allp += list(pts)
            for q, n in zip(pts, nrm):
                holes.append(sdf.sphere(q - n * 0.002, 0.0135))
                rims.append(torus_axis(q + n * 0.001, n, 0.0175, 0.0062))
        allp = np.array(allp)
        c = (allp.min(0) + allp.max(0)) / 2
        R = float(np.linalg.norm(allp.max(0) - allp.min(0))) / 2 + 0.03
        return bounded(sdf.union(*rims), c, R), bounded(sdf.union(*holes), c, R)


def drips(name, field, anchors, rng, lmin=0.05, lmax=0.13):
    """Bava che cola dai punti più bassi (posati sulla superficie): gocce lunghe di melma."""
    pts, _ = snap(field, anchors)
    parts = []
    for q in pts:
        L = rng.uniform(lmin, lmax)
        parts.append(skin.drip(q + V(0, 0, 0.006), L, r0=0.0075, r1=rng.uniform(0.010, 0.014)))
    lo, hi = pts.min(0) - 0.03, pts.max(0) + 0.03
    lo[2] -= lmax + 0.03
    return D.mesh(name, sdf.union(*parts), lo, hi, skin.slime_material(), res=0.0025)


def lampy_finish(fr, head_local, cut_local=None, head_r=0.42, neck_r=0.15, attrs_extra=None, drip_local=()):
    """Unisce testa e corpo, apre i pori branchiali, aggiunge la bava, la lenza e l'acqua.
    drip_local: punti (della testa) da cui cola la bava, oltre a quelli sotto l'arco e la coda."""
    body = Arch(fr.pos + fr.dir((0, 1, 0)) * 0.05, fr.dir((0, 1, 0)), neck_r=neck_r)
    head = bounded(fr.field(head_local), fr.pos, head_r)
    f = sdf.union(body.field(), head, k=0.06)
    if cut_local is not None:
        f = sdf.subtract(f, bounded(fr.field(cut_local), fr.pos, head_r), k=0.006)
    rims, holes = body.gill_pores(f)
    f = sdf.subtract(sdf.union(f, rims, k=0.004), holes, k=0.003)
    attrs = {'belly': body.belly}
    attrs.update(attrs_extra or {})
    lo = np.minimum(body.pts.min(0), fr.pos) - 0.46
    hi = np.maximum(body.pts.max(0), fr.pos) + 0.46
    lo[0], hi[0] = min(-0.36, fr.pos[0] - 0.46), max(0.36, fr.pos[0] + 0.46)
    obs = [skin_mesh('LampySkin', f, lo, hi, D.pale_skin(), attrs=attrs), fishing_line(), water()]
    # la bava: dal sotto dell'arco (dove il ventre guarda in giù), dalla ventosa della coda, dalla bocca
    anchors = []
    for u in (0.27, 0.43, 0.55):
        i = int(np.searchsorted(body.u, u))
        anchors.append(body.pts[i] + body.inner[i] * body.r[i] + V(0.04 * math.sin(9 * u), 0, 0))
    anchors += [TAIL - NL * 0.07 + DL * 0.12, TAIL - NL * 0.06 - DL * 0.10 + V(-0.08, 0, 0)]
    anchors += [fr.pt(q) for q in drip_local]
    obs.append(drips('LampySlime', f, anchors, np.random.default_rng(12)))
    return obs


# ───────────────────────── la cuffia a fiori ─────────────────────────

def cap_material():
    return D.vinyl('CapRubber', (0.36, 0.66, 0.64), stain=(0.22, 0.27, 0.13))


FLOWER_COLS = [((0.95, 0.22, 0.52), 'CapFlowerPink'), ((0.95, 0.78, 0.22), 'CapFlowerYellow'), ((0.90, 0.88, 0.80), 'CapFlowerWhite')]


def flower(c, n, size, petals=6):
    """Fiore di gomma in rilievo: petali a raggiera nel piano tangente, bottone in mezzo."""
    n = unit(n)
    t1 = unit(np.cross(n, V(0.3, 0.2, 1.0)))
    t2 = np.cross(n, t1)
    parts = []
    for k in range(petals):
        a = 2 * math.pi * k / petals
        d = t1 * math.cos(a) + t2 * math.sin(a)
        pc = c + d * size * 0.62 + n * size * 0.08
        parts.append(ellipsoid_axes(pc, (size * 0.50, size * 0.30, size * 0.16), d, np.cross(n, d), n))
    petals_f = sdf.union(*parts, k=size * 0.08)
    button = sdf.sphere(c + n * size * 0.16, size * 0.24)
    return petals_f, button


def swim_cap(fr, center, radii, plane_q, plane_n, flowers, thick=0.0045, tear=None, name='Cap'):
    """La cuffia: un guscio di gomma sul cranio (ellissoide center/radii, in coordinate della testa),
    tagliato da un piano; l'orlo arrotolato; i fiori in rilievo. tear: campo (locale) dello strappo."""
    outer = sdf.ellipsoid(V(*center), tuple(np.array(radii) + 0.007))
    region = D.above(plane_q, plane_n)
    body = sdf.intersect(sdf.shell(outer, thick * 0.5), region)
    edge = sdf.intersect(sdf.shell(outer, thick * 1.4), sdf.intersect(region, D.above(V(*plane_q) + unit(plane_n) * 0.011, -unit(plane_n))))
    capf = sdf.union(body, edge, k=0.002)
    if tear is not None:
        capf = sdf.subtract(capf, tear, k=0.003)
    wc = fr.pos
    obs = [skin_mesh(name, fr.field(capf), wc - 0.42, wc + 0.42, cap_material(), res=0.003)]
    # i fiori: posati sulla superficie esterna della cuffia
    outer_w = fr.field(sdf.ellipsoid(V(*center), tuple(np.array(radii) + 0.007 + thick * 0.5)))
    want = [fr.pt(V(*center) + unit(d) * 0.5) for d, _, _ in flowers]
    pts, nrm = snap(outer_w, want)
    for k, ((d, size, ci), q, n) in enumerate(zip(flowers, pts, nrm)):
        pf, bt = flower(q, n, size)
        col, nm = FLOWER_COLS[ci]
        obs.append(D.mesh(f'{name}Flower{k}', pf, q - size * 1.4, q + size * 1.4, D.vinyl(nm, col, stain=(0.3, 0.3, 0.18)), res=size / 14))
        obs.append(D.mesh(f'{name}Button{k}', bt, q - size * 0.6, q + size * 0.6, D.vinyl('CapFlowerButton', (0.95, 0.82, 0.30), stain=(0.3, 0.3, 0.18)), res=size / 16))
    return obs


def cap_flowers(center, plane_q, plane_n, n=44, size=(0.058, 0.074), margin=0.05, seed=3, R=0.29):
    """Fiori fitti su tutta la cuffia: direzioni spalmate sulla sfera (spirale di Fibonacci), tenute solo
    dove la cuffia copre, con un po' di disordine nella grandezza e nei colori."""
    rng = np.random.default_rng(seed)
    out = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        d = V(r * math.cos(ga * i), r * math.sin(ga * i), z)
        p = V(*center) + d * R
        if (p - V(*plane_q)) @ unit(plane_n) < margin:
            continue
        out.append((tuple(d), float(rng.uniform(*size)), int(rng.integers(0, 3))))
    return out


# ───────────────────────── A · Lampreda ─────────────────────────

def disc_funnel(rim_y, rim_R, rim_r, cav_c, cav_r, fringe=0, fringe_r=0.012, seed=5):
    """La ventosa: orlo a ciambella attorno all'asse −Y, con la frangia di papille molli e disuguali;
    la cavità a imbuto da togliere."""
    rng = np.random.default_rng(seed)
    rim = torus_axis(V(0, rim_y, 0), V(0, 1, 0), rim_R, rim_r)
    parts = [rim]
    for k in range(fringe):
        a = 2 * math.pi * (k + rng.uniform(0.2, 0.8)) / fringe
        rd = V(math.cos(a), 0, math.sin(a))
        fr_ = fringe_r * rng.uniform(0.6, 1.25)
        c = V(0, rim_y - rim_r * rng.uniform(0.1, 0.6), 0) + rd * (rim_R + rim_r * rng.uniform(0.75, 1.05))
        parts.append(ellipsoid_axes(c, (fr_ * 1.7, fr_, fr_ * 0.8), rd, V(0, 1, 0), np.cross(rd, V(0, 1, 0))))
    cavity = sdf.ellipsoid(V(*cav_c), cav_r)
    return sdf.union(*parts, k=0.008), cavity


def oriented(c, radii, n, along=(0, 1, 0)):
    """Ellissoide posato su una superficie: raggi (normale, lungo 'along', di traverso)."""
    n = unit(n)
    a = V(*along) - (V(*along) @ n) * n
    a = unit(a)
    return ellipsoid_axes(c, radii, n, a, np.cross(n, a))


CRAN_C, CRAN_R = V(0, 0.03, 0.02), (0.29, 0.29, 0.28)


def cap_tear(d, length=0.12):
    """Lo strappo della cuffia (sul cranio grande) e la carne che ne esce."""
    n = unit(d)
    c = CRAN_C + n * 0.295
    return oriented(c, (0.04, length, 0.032), n), oriented(c - n * 0.004, (0.034, length * 1.05, 0.036), n)


TEAR_A = V(-0.35, 0.45, 0.82)      # dove la cuffia di A si è strappata
CAP_Q, CAP_N = (0, -0.03, 0.0), (0, 1.0, 0.75)   # l'orlo della cuffia: dietro gli occhi, sulla fronte


def lampy_a():
    """A · Lampreda: un cranio enorme e tondo, davanti la ventosa con la frangia di papille e gli anelli
    di denti gialli fino in gola; occhietti sui lati, la cuffia a fiori strappata dove il cranio è cresciuto."""
    fr = Head(MOUTH - FACE * 0.30, FACE, UP)
    cran = sdf.ellipsoid(CRAN_C, CRAN_R)
    snout = sdf.round_cone(V(0, -0.16, 0), V(0, -0.27, 0), 0.20, 0.18)
    rim, cavity = disc_funnel(-0.30, 0.150, 0.046, (0, -0.39, 0), (0.128, 0.16, 0.128), fringe=64, fringe_r=0.0105)
    tear, bulge = cap_tear(TEAR_A)
    head = sdf.union(cran, snout, rim, bulge, k=0.045)
    throat = sdf.capsule(V(0, -0.22, 0), V(0, 0.02, 0), 0.030)
    cut = sdf.union(cavity, throat)

    def mouth(p):
        q = (p - fr.pos) @ fr.R
        rad = np.sqrt(q[:, 0] ** 2 + q[:, 2] ** 2)
        return (np.clip((0.12 - rad) / 0.02, 0, 1) * np.clip((-0.18 - q[:, 1]) / 0.02, 0, 1) * (q[:, 1] > -0.34)).astype(F)

    obs = lampy_finish(fr, head, cut, attrs_extra={'mouth': mouth}, drip_local=[(0.03, -0.33, -0.17), (-0.10, -0.32, -0.13)])
    c0 = fr.pt((0, -0.08, 0))
    obs.append(D.mesh('LampyThroat', fr.field(sdf.capsule(V(0, -0.21, 0), V(0, 0.04, 0), 0.028)), c0 - 0.25, c0 + 0.25, D.dark_throat(), res=0.004))

    def ybowl(rho):
        return -0.39 + 0.16 * math.sqrt(max(0.0, 1 - (rho / 0.128) ** 2))

    rings = [(rho, ybowl(rho) + 0.003, n, L, r) for rho, n, L, r in
             ((0.100, 26, 0.026, 0.0080), (0.080, 20, 0.029, 0.0088), (0.060, 15, 0.032, 0.0095), (0.042, 10, 0.033, 0.0100))]
    horn = mat_simple('HornTeeth', (0.82, 0.66, 0.30), rough=0.2, coat=0.7, sss=0.3, sss_radius=(1.0, 0.7, 0.3), sss_scale=0.005)
    obs.append(teeth('LampyTeeth', ring_teeth(fr, rings, inward=0.8), horn))
    # la "lingua" a pistone in fondo all'imbuto, con la sua placca di denti
    tongue = [(fr.pt((x, -0.225, z)), fr.pt((x * 1.2, -0.25, z * 1.2)), 0.008) for x, z in ((-0.016, -0.012), (0.0, 0.004), (0.016, -0.012))]
    obs.append(teeth('LampyTongue', tongue, horn))
    head_w = fr.field(sdf.union(cran, snout, k=0.045))
    for sx in (-1, 1):
        q, n = snap(head_w, [fr.pt(CRAN_C + unit(V(sx * 0.85, -0.48, 0.15)) * 0.32)])
        obs += D.eyes(f'LampyEye{sx}', [q[0] - n[0] * 0.012], 0.025, n[0] + fr.dir((0, -0.5, 0)))
    flowers = [f for f in cap_flowers(CRAN_C, CAP_Q, CAP_N) if unit(V(*f[0])) @ unit(TEAR_A) < 0.93]
    obs += swim_cap(fr, CRAN_C, CRAN_R, CAP_Q, CAP_N, flowers, tear=tear)
    return obs, 'A · Lampreda', 'più pesce: un cranio enorme e tondo, davanti\nla ventosa con gli anelli di denti gialli;\nla cuffia a fiori si è strappata dove è cresciuto'


# ───────────────────────── B · Bacio ─────────────────────────

def pucker_lips(c, R, r, n=26, amp=0.05, squash=0.85):
    """Labbra a bacio attorno all'asse −Y: una ciambella carnosa un po' più larga che alta, il labbro di
    sotto più gonfio, le grinzette verticali delle labbra."""
    c = V(*c)

    def f(p):
        q = p - c
        x, z = q[:, 0], q[:, 2] / squash
        rho = np.sqrt(x * x + z * z)
        th = np.arctan2(z, x)
        rr = r * (1 + amp * np.cos(n * th)) * (1 + 0.3 * np.clip(-z / (R + r), 0, 1))
        return np.sqrt((rho - R) ** 2 + q[:, 1] ** 2) - rr
    return f


def place_head(local_mouth):
    """Sistema della testa con la bocca (punto locale) esattamente sulla lenza."""
    fr = Head((0, 0, 0), FACE, UP)
    fr.pos = MOUTH - fr.R @ V(*local_mouth)
    return fr


def lampy_b():
    """B · Bacio: il cranio tondo da neonato sotto la cuffia, occhioni bianchi, il naso schiacciato; la
    ventosa è una bocca umana con le labbra a bacio, piena di anelli di denti da latte."""
    fr = place_head((0, -0.315, -0.10))
    cran = sdf.ellipsoid(V(0, 0.03, 0.05), (0.28, 0.28, 0.29))
    face = sdf.ellipsoid(V(0, -0.10, -0.03), (0.22, 0.18, 0.21))
    brow = sdf.ellipsoid(V(0, -0.252, 0.118), (0.15, 0.032, 0.03))
    nose = sdf.union(sdf.round_cone(V(0, -0.262, 0.07), V(0, -0.292, 0.012), 0.014, 0.022), sdf.sphere(V(0, -0.29, 0.012), 0.024), k=0.01)
    lips = pucker_lips((0, -0.30, -0.10), 0.075, 0.036)
    head = sdf.union(cran, face, brow, nose, lips, k=0.035)
    sockets = sdf.union(*[sdf.sphere(V(sx * 0.092, -0.258, 0.072), 0.037) for sx in (-1, 1)])
    nostrils = sdf.union(*[ellipsoid_rot(V(sx * 0.013, -0.312, 0.004), (0.006, 0.01, 0.004), np.eye(3, dtype=F)) for sx in (-1, 1)])
    hole = sdf.union(sdf.ellipsoid(V(0, -0.34, -0.10), (0.044, 0.09, 0.044)), sdf.capsule(V(0, -0.30, -0.10), V(0, -0.02, -0.05), 0.03))
    cut = sdf.union(sockets, nostrils, hole)

    def attrs_mouth(p):
        """1 dentro la bocca, mezzo sulle labbra (rosso livido e bagnato)."""
        q = (p - fr.pos) @ fr.R
        d = np.sqrt(q[:, 0] ** 2 + ((q[:, 2] + 0.10) / 0.85) ** 2)
        inside = np.clip((0.05 - d) / 0.012, 0, 1) * (q[:, 1] > -0.33)
        lip = np.clip(1 - np.abs(d - 0.075) / 0.045, 0, 1) * np.clip((-0.25 - q[:, 1]) / 0.03, 0, 1) * 0.5
        return np.maximum(inside, lip).astype(F)

    obs = lampy_finish(fr, head, cut, attrs_extra={'mouth': attrs_mouth},
                       drip_local=[(0.0, -0.33, -0.165), (0.05, -0.32, -0.15)])
    c0 = fr.pt((0, -0.17, -0.08))
    obs.append(D.mesh('LampyThroat', fr.field(sdf.capsule(V(0, -0.27, -0.10), V(0, -0.04, -0.06), 0.028)), c0 - 0.22, c0 + 0.22, D.dark_throat(), res=0.004))
    rings = [(0.050, -0.300, 15, 0.016, 0.0072), (0.039, -0.282, 12, 0.017, 0.0068), (0.029, -0.262, 9, 0.017, 0.0064)]
    obs.append(teeth('LampyMilkTeeth', ring_teeth(fr, rings, axis_c=(0, 0, -0.10), inward=1.1), teeth_material()))
    obs += D.eyes('LampyEye', [fr.pt((sx * 0.092, -0.252, 0.072)) for sx in (-1, 1)], 0.032, fr.dir((0, -1, -0.05)))
    flowers = cap_flowers(V(0, 0.03, 0.05), CAP_Q_B, CAP_N)
    obs += swim_cap(fr, V(0, 0.03, 0.05), (0.28, 0.28, 0.29), CAP_Q_B, CAP_N, flowers)
    return obs, 'B · Bacio', 'a metà: il cranio da neonato sotto la cuffia,\nocchioni bianchi; la ventosa è una bocca\ncon le labbra a bacio e anelli di denti da latte'


CAP_Q_B = (0, -0.12, 0.0)


# ───────────────────────── C · Bambina ─────────────────────────

def lampy_c():
    """C · Bambina: un testone tondo da bambina piccola, guance piene, la cuffia allacciata sotto il mento;
    ride a occhi stretti, e la bocca è una O perfetta piena di anelli di dentini, con dentro la lenza."""
    fr = place_head((0, -0.262, -0.105))
    cran = sdf.ellipsoid(V(0, 0.03, 0.07), (0.25, 0.26, 0.26))
    face = sdf.ellipsoid(V(0, -0.08, -0.05), (0.19, 0.17, 0.17))
    cheeks = sdf.union(*[sdf.sphere(V(sx * 0.098, -0.175, -0.055), 0.074) for sx in (-1, 1)])
    chin = sdf.sphere(V(0, -0.175, -0.165), 0.05)
    nose = sdf.union(sdf.sphere(V(0, -0.255, -0.005), 0.019), sdf.round_cone(V(0, -0.235, 0.05), V(0, -0.252, 0.0), 0.012, 0.016), k=0.01)
    lips = sdf.union(torus_axis(V(0, -0.248, -0.105), V(0, 1, 0), 0.048, 0.019), k=0.0)
    base = sdf.union(cran, face, cheeks, chin, nose, lips, k=0.03)
    sockets = sdf.union(*[sdf.sphere(V(sx * 0.078, -0.226, 0.048), 0.033) for sx in (-1, 1)])
    # occhi che ridono: le palpebre lasciano scoperta solo una mezzaluna a ∩ (sopra calata, sotto spinta su
    # dalle guance)
    lids = []
    for sx in (-1, 1):
        e = V(sx * 0.078, -0.212, 0.048)
        sh = sdf.subtract(sdf.sphere(e, 0.038), sdf.sphere(e, 0.0305))
        low = sdf.sphere(e + V(0, 0, -0.040), 0.042)          # sotto quest'arco: palpebra di sotto
        high = sdf.sphere(e + V(0, 0, -0.026), 0.042)         # sopra quest'arco: palpebra di sopra
        keep = lambda p, low=low, high=high: np.minimum(low(p), -high(p))
        lids.append(sdf.intersect(sh, keep))
    head = sdf.union(sdf.subtract(base, sockets, k=0.004), *lids, k=0.004)
    hole = sdf.union(sdf.ellipsoid(V(0, -0.29, -0.105), (0.031, 0.08, 0.031)), sdf.capsule(V(0, -0.25, -0.105), V(0, -0.02, -0.06), 0.026))
    nostrils = sdf.union(*[sdf.sphere(V(sx * 0.009, -0.268, -0.016), 0.0055) for sx in (-1, 1)])
    cut = sdf.union(hole, nostrils)

    def loc(p):
        return (p - fr.pos) @ fr.R

    def blush(p):
        q = loc(p)
        d = np.minimum(np.linalg.norm(q - V(0.10, -0.235, -0.06), axis=1), np.linalg.norm(q - V(-0.10, -0.235, -0.06), axis=1))
        dl = np.abs(np.sqrt(q[:, 0] ** 2 + (q[:, 2] + 0.105) ** 2) - 0.048)
        lipm = np.clip(1 - dl / 0.022, 0, 1) * (q[:, 1] < -0.22)
        return np.maximum(np.clip(1.0 - d / 0.06, 0.0, 1.0), lipm).astype(F)

    def mouth(p):
        q = loc(p)
        d = np.sqrt(q[:, 0] ** 2 + (q[:, 2] + 0.105) ** 2)
        return (np.clip((0.034 - d) / 0.008, 0, 1) * (q[:, 1] > -0.27)).astype(F)

    obs = lampy_finish(fr, head, cut, attrs_extra={'blush': blush, 'mouth': mouth}, drip_local=[(0.0, -0.25, -0.135), (-0.03, -0.24, -0.13)])
    c0 = fr.pt((0, -0.15, -0.09))
    obs.append(D.mesh('LampyThroat', fr.field(sdf.capsule(V(0, -0.23, -0.105), V(0, -0.04, -0.07), 0.024)), c0 - 0.2, c0 + 0.2, D.dark_throat(), res=0.004))
    rings = [(0.031, -0.250, 13, 0.012, 0.0052), (0.026, -0.232, 11, 0.012, 0.0050), (0.021, -0.214, 9, 0.011, 0.0047), (0.017, -0.196, 7, 0.010, 0.0044)]
    obs.append(teeth('LampyMilkTeeth', ring_teeth(fr, rings, axis_c=(0, 0, -0.105), inward=1.2), teeth_material()))
    obs += D.eyes('LampyEye', [fr.pt((sx * 0.078, -0.212, 0.048)) for sx in (-1, 1)], 0.029, fr.dir((0, -1, 0.1)))
    # la cuffia, allacciata sotto il mento con la cinghietta che affonda nelle guance
    cc, cr = V(0, 0.03, 0.07), (0.25, 0.26, 0.26)
    flowers = cap_flowers(cc, CAP_Q_C, CAP_N, size=(0.05, 0.064), R=0.26)
    obs += swim_cap(fr, cc, cr, CAP_Q_C, CAP_N, flowers)
    skin_w = fr.field(sdf.union(cran, face, cheeks, chin, k=0.03))
    path = [V(sx * 0.215, -0.07, -0.01) for sx in (-1,)] + [V(-0.17, -0.14, -0.15), V(-0.08, -0.19, -0.215), V(0, -0.20, -0.228),
                                                              V(0.08, -0.19, -0.215), V(0.17, -0.14, -0.15), V(0.215, -0.07, -0.01)]
    pts, nrm = snap(skin_w, [fr.pt(q) for q in path])
    pts = pts + nrm * 0.004
    strap = D.hair_clump(list(pts), 0.0085, 0.0085)
    obs.append(D.mesh('CapStrap', strap, pts.min(0) - 0.03, pts.max(0) + 0.03, cap_material(), res=0.0028))
    return obs, 'C · Bambina', 'più bambina: un testone da bimba piccola,\nla cuffia allacciata sotto il mento; ride a occhi\nstretti e la bocca è una O piena di dentini'


CAP_Q_C = (0, -0.14, 0.03)


# ───────────────────────── scena ─────────────────────────

D.CREATURES['lampy'] = {
    'title': 'LAMPY — dettagli della testa (notte 4, sagoma C «Sanguisuga», più grossa), con la lenza',
    'variants': [lampy_a, lampy_b, lampy_c],
    'cam': CAM,
    'subject': (0, -0.2, 1.4), 'key': 45, 'rim': 160,
}


if __name__ == '__main__':
    only = None
    if '--only' in sys.argv:
        only = 'ABC'.index(sys.argv[sys.argv.index('--only') + 1])
    panels = []
    for i in range(len(D.CREATURES['lampy']['variants'])):
        if only is not None and i != only:
            continue
        panels.append(D.render_variant('lampy', i))
        print('ok lampy', 'ABC'[i], flush=True)
    if only is None and len(panels) == 3:
        print('tavola', D.compose('lampy', panels), flush=True)
