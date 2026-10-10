"""
FANGY — dettagli della testa (notte 5, sagoma B «Mastino»), da scegliere insieme.

Come per la prima notte (dettagli.py): il corpo della sagoma scelta e tre teste, da "più pesce" (A) a
"più bambino" (C), con addosso gli occhialini da piscina con le lenti dipinte di nero, ormai incastrati
nella faccia. Fangy viene dal pesce vipera e dal pesce dente di sciabola: testa grande, zanne troppo lunghe
per chiudere la bocca, file di lucine (i fotofori) lungo il ventre. Da bambino giocava a Marco Polo a occhi
chiusi e vinceva sempre: ora è cieco e caccia a orecchio. La sagoma «Mastino»: curvo e basso nell'acqua,
la testa spinta avanti, le zanne che pendono, le nocche in acqua.

Colori (proposta da approvare): come gli animatronici di FNAF ogni mostro nuovo ha un colore netto. Fangy è
blu notte saturo, blu e non nero (più scuro sul dorso, più chiaro sul ventre, come i pesci degli abissi),
con le lucine azzurro-ciano accese; zanne pallide; gli occhialini di plastica gialla scolorita, come le
altre cose del parco, con le lenti dipinte di nero (sul blu si leggono subito).

Bozze di studio: non sono i modelli definitivi del gioco. Usa materiali, luci, render e tavola di
dettagli.py, che resta com'è: la creatura si registra in D.CREATURES quando il modulo viene caricato.

Uso: tools/.venv/bin/python tools/render/teste_fangy.py [--fast] [--only A|B|C | --tavola]
(--tavola ricompone la tavola dai pannelli in cache, dopo averne rifatto uno con --only)
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
from common import mesh_from_arrays, set_lightgroup  # noqa: E402
from creature import sdf_object  # noqa: E402
from dettagli import V, chain, mat_simple, unit  # noqa: E402
from geo import _frames, catmull, rbox  # noqa: E402
from nodes import material  # noqa: E402

F = np.float32
FAST = D.FAST
SKIN_RES = 0.0045 if FAST else 0.003      # la pelle si estrae a fasce (sdf.mesh_banded)

# ───────────────────────── la posa (sagoma B «Mastino») ─────────────────────────
# Fangy guarda verso −Y; il pelo dell'acqua è a z = 0. La schiena sale dall'acqua fino alla gobba delle
# spalle, la testa sta avanti, all'altezza delle spalle; le braccia lunghissime scendono fino all'acqua e
# ci appoggiano le nocche, come un mastino (o un gorilla). Tutto quello che sta sotto z = 0 non si vede.

SPINE = [V(0, 0.72, -0.28), V(0, 0.61, 0.08), V(0, 0.49, 0.43), V(0, 0.35, 0.72), V(0, 0.19, 0.89), V(0, 0.05, 0.93)]
SPINE_R = [0.125, 0.125, 0.135, 0.150, 0.142, 0.105]
SPALLA, GOMITO, POLSO, NOCCHE = V(0.20, 0.17, 0.83), V(0.31, -0.02, 0.49), V(0.27, -0.29, 0.085), V(0.275, -0.37, 0.0)
CAM = ((-0.55, -1.60, 0.95), (0, -0.10, 0.52), 40)

TESTI = {
    'A': ('A · Sciabola', 'più pesce: il testone del pesce dente di sciabola,\nle zanne del pesce vipera fuori dalla bocca;\nfossette per sentire, occhialini affondati nella carne'),
    'B': ('B · Molosso', 'a metà: muso da mastino che non si chiude,\nle zanne pendono dalle labbra; orecchie\numane enormi, girate in avanti ad ascoltare'),
    'C': ('C · Bambino', 'più bambino: un bambino in piscina, frangetta\nbagnata e occhialini neri; le lentiggini accese,\nla bocca aperta a chiamare «Marco!», piena di aghi'),
}


class Head(D.Frame):
    """Sistema locale della testa (faccia −Y, alto +Z): girata (yaw), china (pitch), piegata di lato (roll:
    la testa inclinata di chi ascolta) e ingrandita (scale) rispetto alle misure con cui è disegnata."""

    def __init__(self, pos, yaw=0.0, pitch=0.0, roll=0.0, scale=1.0):
        self.pos = V(*pos)
        self.R = (sdf.rot_matrix('z', yaw) @ sdf.rot_matrix('x', pitch) @ sdf.rot_matrix('y', roll)).astype(F)
        self.S = float(scale)

    def field(self, f):
        R, c, S = self.R, self.pos, self.S
        return lambda p: f(((p - c) @ R) / S) * S

    def pt(self, q):
        return self.pos + self.R @ (V(*q) * self.S)

    def local(self, p):
        return ((p - self.pos) @ self.R) / self.S


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


def around(f, pts, pad=0.05):
    """bounded() sulla sfera che contiene i punti."""
    P = np.atleast_2d(np.asarray(pts, F))
    c = (P.min(0) + P.max(0)) / 2
    return bounded(f, c, float(np.linalg.norm(P.max(0) - P.min(0))) / 2 + pad)


def ellipsoid_axes(c, radii, ax, ay, az):
    """Ellissoide con gli assi lungo tre direzioni (rese ortogonali: conta la prima, poi la seconda)."""
    ax = unit(ax)
    ay = unit(V(*ay) - (V(*ay) @ ax) * ax)
    az = V(*az) - (V(*az) @ ax) * ax - (V(*az) @ ay) * ay
    M = np.stack([ax, ay, unit(az)], axis=1).astype(F)
    c = V(*c)
    e = sdf.ellipsoid(V(0, 0, 0), radii)
    return lambda p: e((p - c) @ M)


def oval_ring(c, u, v, n, a, b, r):
    """Anello ovale nel piano (u, v) con semiassi a (lungo u) e b (lungo v), tubo di raggio r."""
    M = np.stack([unit(u), unit(v), unit(n)], axis=1).astype(F)
    c = V(*c)

    def f(p):
        q = (p - c) @ M
        rho = np.sqrt(q[:, 0] ** 2 + q[:, 1] ** 2)
        e = np.sqrt((q[:, 0] / a) ** 2 + (q[:, 1] / b) ** 2)
        d = rho * (1.0 - 1.0 / np.maximum(e, 1e-4))      # distanza radiale dall'ovale (esatta per i cerchi)
        return np.sqrt(d * d + q[:, 2] ** 2) - r
    return f


def snap(field, pts, iters=6, eps=0.0015):
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


def polyline(points, radii, k=0.0):
    """Tubo lungo una spezzata (raggi per punto), valutato solo vicino ai suoi punti."""
    f = chain([V(*p) for p in points], [float(r) for r in radii], k=k)
    return around(f, points, pad=max(radii) + 0.04)


def tubes(name, curves, mat, m=10):
    """Tanti tubi affusolati in un'unica mesh (zanne, denti, cinghia, fili di bava): curves = [(punti,
    raggi)]. Costruiti direttamente lungo la curva (niente campo): il fondo è chiuso, la punta finisce in un
    vertice."""
    verts, faces = [], []
    for P, R in curves:
        P, R = np.asarray(P, float), np.asarray(R, float)
        T, N, B = _frames(P)
        base = len(verts)
        for i in range(len(P)):
            for k in range(m):
                a = 2 * math.pi * k / m
                verts.append(P[i] + R[i] * (math.cos(a) * N[i] + math.sin(a) * B[i]))
        for i in range(len(P) - 1):
            for k in range(m):
                a0, a1 = base + i * m + k, base + i * m + (k + 1) % m
                faces.append((a0, a1, a1 + m, a0 + m))
        faces.append(tuple(base + k for k in range(m - 1, -1, -1)))
        tip = len(verts)
        verts.append(P[-1] + T[-1] * R[-1] * 0.6)
        last = base + (len(P) - 1) * m
        for k in range(m):
            faces.append((last + k, last + (k + 1) % m, tip))
    ob = mesh_from_arrays(name, np.array(verts), faces, smooth=True, col='creatures')
    ob.data.materials.append(mat)
    set_lightgroup(ob, 'ambient')
    return ob


def balls(name, centers, radii, mat, seg=14, rings=9):
    """Tante palline in un'unica mesh (le lucine): sfere UV costruite direttamente."""
    verts, faces = [], []
    for c, r in zip(centers, radii):
        c = np.asarray(c, float)
        base = len(verts)
        verts.append(c + (0, 0, r))
        for j in range(1, rings):
            th = math.pi * j / rings
            for k in range(seg):
                ph = 2 * math.pi * k / seg
                verts.append(c + r * np.array((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))))
        bot = len(verts)
        verts.append(c - (0, 0, r))
        for k in range(seg):
            faces.append((base, base + 1 + k, base + 1 + (k + 1) % seg))
        for j in range(rings - 2):
            r0, r1 = base + 1 + j * seg, base + 1 + (j + 1) * seg
            for k in range(seg):
                faces.append((r0 + k, r1 + k, r1 + (k + 1) % seg, r0 + (k + 1) % seg))
        last = base + 1 + (rings - 2) * seg
        for k in range(seg):
            faces.append((last + k, bot, last + (k + 1) % seg))
    ob = mesh_from_arrays(name, np.array(verts), faces, smooth=True, col='creatures')
    ob.data.materials.append(mat)
    set_lightgroup(ob, 'ambient')
    return ob


def fang(base, direction, L, r, bend=(0, 0, 0), n=8, tip=0.10):
    """Zanna: dalla base (raggio r) alla punta lungo direction, piegata ad arco di bend (spostamento della
    punta). Restituisce (punti, raggi) per tubes()."""
    b, d, c = V(*base), unit(direction), V(*bend)
    t = np.linspace(0.0, 1.0, n)
    pts = np.array([b + d * L * x + c * x * x for x in t])
    rad = r * (1.0 - (1.0 - tip) * t ** 1.15)
    return pts, rad


def local_curves(fr, curves):
    """Curve costruite nel sistema della testa → mondo."""
    return [(np.array([fr.pt(p) for p in P]), np.asarray(R) * fr.S) for P, R in curves]


def box_axes(c, half, ax, ay, az, rounding=0.0):
    """Scatola smussata con gli assi lungo tre direzioni."""
    M = np.stack([unit(ax), unit(ay), unit(az)], axis=1).astype(F)
    c = V(*c)
    b = sdf.box(V(0, 0, 0), half, rounding)
    return lambda p: b((p - c) @ M)


def ribbon(name, pts, nrms, width, thick, mat):
    """Nastro piatto (la cinghia) steso sulla pelle lungo pts, con le normali della pelle: largo width,
    spesso thick, con le due teste chiuse."""
    P, N = np.asarray(pts, float), np.asarray(nrms, float)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    W = np.cross(N, T)
    W /= np.linalg.norm(W, axis=1, keepdims=True)
    N = np.cross(T, W)
    prof = [(-width / 2, 0.0), (width / 2, 0.0), (width / 2, thick), (-width / 2, thick)]
    verts = [P[i] + W[i] * a + N[i] * b for i in range(len(P)) for a, b in prof]
    faces = []
    for i in range(len(P) - 1):
        for k in range(4):
            a0, a1 = i * 4 + k, i * 4 + (k + 1) % 4
            faces.append((a0, a0 + 4, a1 + 4, a1))
    faces += [(0, 1, 2, 3), tuple((len(P) - 1) * 4 + k for k in (3, 2, 1, 0))]
    ob = mesh_from_arrays(name, np.array(verts), faces, smooth=False, col='creatures')
    ob.data.materials.append(mat)
    set_lightgroup(ob, 'ambient')
    return ob


def arc(p0, p1, p2, n):
    """n punti su una curva morbida per tre punti (catmull), estremi compresi."""
    P = catmull([V(*p0), V(*p1), V(*p2)], 24)
    idx = np.linspace(0, len(P) - 1, n).round().astype(int)
    return P[idx]


# ───────────────────────── colori (proposta del 10 ottobre, da approvare) ─────────────────────────
# Come in FNAF, ogni mostro nuovo ha un colore netto e riconoscibile anche al buio. Fangy è blu notte
# SATURO: blu e non nero, col rosso e il verde tenuti bassi perché sotto la lampara calda non diventi grigio
# e sotto la luna e le lucine non viri al ceruleo (nel render la tinta scende di una decina di gradi verso
# il ciano: l'albedo sta sul blu-indaco). Più scuro sul dorso e più chiaro sul ventre (il chiaroscuro dei
# pesci); le lucine azzurro-ciano accese.

DORSO = (0.007, 0.011, 0.110)
FIANCO = (0.018, 0.030, 0.270)
VENTRE = (0.040, 0.075, 0.380)
MACCHIE = (0.003, 0.005, 0.050)
LABBRA = (0.13, 0.11, 0.32)          # le labbra livide da annegato
MELMA = (0.92, 0.96, 0.92)           # la stessa melma verdognola, ma appena velata: il blu non vira al ceruleo
LUCE = (0.10, 0.85, 1.0)             # i fotofori


def pelle_fangy():
    """Pelle blu bagnata e malata: chiaroscuro dorso-ventre, chiazze e vene scure, puntini argentati
    (le squame minute dei pesci degli abissi), sopra la melma lucida a chiazze e colature.
    Attributi: 'ventre' (0 dorso, 1 pancia), 'mouth' (dentro la bocca), 'labbra'."""
    m = bpy.data.materials.get('FangySkinMat')
    if m:
        return m
    m, g = material('FangySkinMat')
    co = g.texcoord('Object')
    ven = g.attr('ventre')
    col = g.ramp(ven, [(0.0, DORSO), (0.5, FIANCO), (1.0, VENTRE)])
    n1 = g.noise(co, scale=5.0, detail=4.0, rough=0.55, distortion=0.6)
    col = g.mix(g.mul(g.smoothstep(0.52, 0.64, n1.fac), 0.7), col, MACCHIE)
    n2 = g.noise(co, scale=16.0, detail=3.0, rough=0.6)
    col = g.mix(g.mul(g.smoothstep(0.58, 0.72, n2.fac), 0.4), col, MACCHIE)
    dots = g.voronoi(co, scale=75.0, feature='F1')
    col = g.mix(g.mul(g.smoothstep(0.15, 0.05, dots), g.mul(ven, 0.5)), col, (0.32, 0.50, 0.80))
    warp = g.vmath('ADD', co, g.vmath('SCALE', n1.color, scale=0.05))
    vv = g.voronoi(warp, scale=7.0, feature='DISTANCE_TO_EDGE')
    col = g.mix(g.mul(g.smoothstep(0.025, 0.0, vv), 0.45), col, (0.002, 0.004, 0.03))
    col = g.mix(g.mul(g.attr('labbra'), 0.85), col, LABBRA)
    col = g.mix(g.smoothstep(0.3, 0.7, g.attr('mouth')), col, (0.004, 0.003, 0.012))
    ao = g.ao(distance=0.03, samples=8)
    col = g.mix(g.sub(1.0, ao), col, (0.25, 0.25, 0.32), blend='MULTIPLY')
    # melma: chiazze lucide, colature verso il basso, ristagni nelle cavità; più bagnato sul dorso
    patch = g.noise(co, scale=4.2, detail=4.0, rough=0.55, distortion=0.7)
    pm = g.smoothstep(0.50, 0.60, patch.fac)
    streak = g.noise(g.mapping(co, scale=(28.0, 28.0, 2.6)), scale=1.0, detail=3.0, rough=0.5, distortion=0.3)
    dm = g.mul(g.smoothstep(0.56, 0.68, streak.fac), 0.9)
    cm = g.mul(g.smoothstep(0.25, 0.55, g.sub(1.0, ao)), 0.8)
    sl = g.clamp01(g.add(g.mx(g.mx(pm, dm), cm), g.mul(g.sub(1.0, ven), 0.2)))
    r = g.mixf(sl, 0.45, 0.10)
    grain = g.noise(co, scale=55.0, detail=3.0, rough=0.6)
    nrm = g.bump(grain.fac, strength=0.35, distance=0.003)
    bub = g.voronoi(co, scale=160.0, feature='F1')
    coat_n = g.bump(g.add(g.mul(sl, 0.8), g.mul(g.mul(g.smoothstep(0.22, 0.05, bub), pm), 0.25)), strength=0.3, distance=0.002)
    g.output_material(g.principled(color=col, rough=r, coat=g.add(0.30, g.mul(sl, 0.65)), coat_rough=g.mixf(sl, 0.12, 0.03),
                                   coat_tint=MELMA, coat_normal=coat_n, sss=0.10, sss_radius=(0.25, 0.55, 1.0),
                                   sss_scale=0.03, normal=nrm))
    return m


def luce_material():
    return D.glow('FangyLight', LUCE, 16.0, base=(0.45, 0.90, 1.0))


def lente_dipinta():
    """Le lenti dipinte di nero: vernice data a mano, a pennellate grosse che si vedono nel lucido, scrostata
    in qualche punto (sotto, la plastica chiara della lente). Serve anche per le colature sulla guancia."""
    m = bpy.data.materials.get('GogglePaint')
    if m:
        return m
    m, g = material('GogglePaint')
    co = g.texcoord('Object')
    strokes = g.noise(g.mapping(co, scale=(30.0, 30.0, 420.0)), scale=1.0, detail=4.0, rough=0.65)
    chips = g.noise(co, scale=150.0, detail=2.0, rough=0.5)
    chip = g.smoothstep(0.70, 0.73, chips.fac)
    col = g.mix(chip, (0.006, 0.006, 0.008), (0.45, 0.55, 0.58))
    g.output_material(g.principled(color=col, rough=g.mixf(chip, 0.38, 0.5), coat=0.25, coat_rough=0.25, spec=0.4,
                                   normal=g.bump(strokes.fac, strength=0.9, distance=0.002)))
    return m


def plastica_occhialini():
    """La plastica degli occhialini da bambino: gialla come le cose del parco, scolorita e macchiata
    d'alga; sul blu stacca subito."""
    return D.vinyl('GoggleVinyl', (0.92, 0.66, 0.10), stain=(0.30, 0.32, 0.16))


# ───────────────────────── il corpo ─────────────────────────

class Body:
    """Il corpo comune alle tre teste: la schiena curva, le braccia fino all'acqua, il collo che entra
    nella testa (neck: il punto dove entra, neck_r: quanto è grosso lì)."""

    def __init__(self, neck, neck_r):
        ctrl = SPINE + [V(*neck)]
        n = 10
        self.pts = catmull(ctrl, n).astype(F)
        self.r = np.interp(np.arange(len(self.pts)) / n, np.arange(len(ctrl)), SPINE_R + [neck_r]).astype(F)
        tan = np.gradient(self.pts, axis=0)
        self.tan = (tan / np.linalg.norm(tan, axis=1, keepdims=True)).astype(F)
        up = V(0, 0, 1)[None, :] - (self.tan @ V(0, 0, 1))[:, None] * self.tan
        self.dors = (up / np.linalg.norm(up, axis=1, keepdims=True)).astype(F)      # il dorso: in su e indietro
        self.n3 = sdf.Noise3(57)

    def arm_pts(self, s):
        sh, el, wr = (P * V(s, 1, 1) for P in (SPALLA, GOMITO, POLSO))
        return [sh, (sh + el) / 2 + V(s * 0.02, 0, 0), el, (el + wr) / 2, wr]

    def arm(self, s):
        """Braccio lunghissimo e magro, il gomito ossuto in fuori; la mano piantata nell'acqua sulle nocche,
        le dita piegate sotto (si vedono solo le nocche)."""
        pts = self.arm_pts(s)
        el, wr, kn = pts[2], pts[4], NOCCHE * V(s, 1, 1)
        f = [chain(pts, [0.064, 0.046, 0.040, 0.036, 0.030], k=0.025),
             sdf.sphere(el + V(s * 0.012, 0.022, 0.0), 0.040),
             sdf.sphere(pts[0] + V(s * 0.012, 0.0, 0.01), 0.068)]                    # la spalla
        hand_dir = unit(kn - wr)
        side = V(1, 0, 0)
        back = unit(np.cross(side, hand_dir)) * -1.0
        f.append(ellipsoid_axes((wr + kn) / 2 + back * 0.006, (0.048, 0.062, 0.020), side, hand_dir, back))
        for j, dx in enumerate((-0.036, -0.012, 0.012, 0.036)):
            k0 = kn + V(dx, -0.004 * (1.5 - abs(j - 1.5)), 0.0)
            f.append(sdf.sphere(k0 + back * 0.006, 0.0165))
            f.append(chain([k0, k0 + V(dx * 0.15, 0.012, -0.05), k0 + V(dx * 0.25, 0.045, -0.10)], [0.0145, 0.012, 0.010], k=0.006))
        th = wr + V(-s * 0.035, -0.035, -0.04)
        f.append(chain([wr + V(-s * 0.02, -0.01, -0.01), th, th + V(-s * 0.01, -0.03, -0.07)], [0.016, 0.013, 0.010], k=0.008))
        return around(sdf.union(*f, k=0.02), [pts[0], kn], pad=0.12)

    def field(self):
        k = len(self.pts)
        idx = np.linspace(0, k - 1, 24).astype(int)
        spine = chain([self.pts[i] for i in idx], [float(self.r[i]) for i in idx], k=0.05)
        a = unit(V(0, -0.30, 0.46))
        dors = unit(np.cross(a, V(1, 0, 0)))
        thorax = ellipsoid_axes(V(0, 0.305, 0.69), (0.175, 0.27, 0.155), V(1, 0, 0), a, dors)
        # scapole che sporgono dalla gobba, vertebre in fila sulla schiena
        scap = []
        for s in (-1, 1):
            c = V(s * 0.095, 0.345, 0.88)
            nn = unit(V(s * 0.62, 0.57, 0.54))
            along = unit(V(0, -0.69, 0.73))
            scap.append(ellipsoid_axes(c, (0.05, 0.085, 0.028), np.cross(along, nn), along, nn))
        vert = []
        for i in range(k):
            if self.pts[i, 2] < 0.02 or i % 2:
                continue
            u = i / (k - 1)
            vert.append(sdf.sphere(self.pts[i] + self.dors[i] * (self.r[i] - 0.004), 0.024 - 0.008 * u))
        vert = around(sdf.union(*vert), self.pts[self.pts[:, 2] > 0.0], pad=0.08)
        body = sdf.union(spine, thorax, *scap, vert, self.arm(-1), self.arm(1), k=0.04)

        def ribs(p):
            q = p - V(0, 0.305, 0.69)
            t = q @ a
            side = smooth(np.abs(q[:, 0]), 0.06, 0.13)
            low = smooth(-(q @ dors), -0.06, 0.04)
            inside = np.clip(1.0 - np.abs(t) / 0.21, 0, 1)
            return ((0.5 + 0.5 * np.cos(2 * np.pi * t / 0.046)) ** 3 * side * low * inside).astype(F)

        def lumps(p):
            return (0.004 * self.n3(p, scale=0.06, octaves=2)).astype(F)

        return sdf.displace(sdf.displace(body, ribs, -0.0055), lumps, 1.0)

    def gills(self):
        """Tre fessure branchiali per lato, sul collo."""
        parts = []
        i0 = int(np.searchsorted(-self.pts[:, 1], -0.13))
        for j, t in enumerate((0.0, 0.33, 0.66)):
            i = min(len(self.pts) - 1, i0 + int(t * 8))
            c, r, tg = self.pts[i], self.r[i], self.tan[i]
            for s in (-1, 1):
                nn = V(s, 0, 0)
                ud = unit(np.cross(tg, nn))
                parts.append(ellipsoid_axes(c + nn * (r * 0.92) - self.dors[i] * 0.01, (0.009, 0.011, 0.040), nn, tg, ud))
        return around(sdf.union(*parts), [p for p in self.pts[i0:i0 + 8]], pad=0.15)

    def light_rows(self):
        """Le file di lucine lungo il ventre, a passo regolare perché si leggano come file: due vicine alla
        linea di mezzo, dalla gola fino all'acqua, e due più in fuori, più piccole, che si fermano prima.
        Restituisce i punti di partenza (da posare sulla pelle) e i raggi."""
        z = self.pts[:, 2]
        top = int(np.argmin(np.abs(self.pts[:, 1] - 0.13)))           # fino al petto, sotto il collo
        bot = int(np.argmin(np.abs(z - 0.03)))
        want, rr = [], []
        for xo, rad, n, j0 in ((0.048, 0.0115, 11, 0), (0.125, 0.0090, 11, 3)):
            for j in range(j0, n):
                i = int(round(bot + (top - bot) * (j + 0.5) / n))
                c, r = self.pts[i], self.r[i]
                for s in (-1, 1):
                    want.append(c - self.dors[i] * r * 1.05 + V(s * xo, 0, 0))
                    rr.append(rad)
        return want, rr

    def ventre(self, fr, head_r):
        """Il chiaroscuro del pesce: dorso scuro, ventre chiaro. Per ogni punto l'asse più vicino (schiena,
        collo, braccia) e il suo 'dorso'; sulla testa conta l'alto e il basso della testa."""
        P, U = [self.pts], [self.dors]
        for s in (-1, 1):
            A = catmull(self.arm_pts(s) + [NOCCHE * V(s, 1, 1)], 8).astype(F)
            T = np.gradient(A, axis=0)
            T /= np.linalg.norm(T, axis=1, keepdims=True)
            ref = unit(V(s, 0.35, 0.45))
            up = ref[None, :] - (T @ ref)[:, None] * T
            P.append(A)
            U.append((up / np.linalg.norm(up, axis=1, keepdims=True)).astype(F))
        P, U = np.concatenate(P), np.concatenate(U)
        tree = cKDTree(P)

        def f(p):
            _, i = tree.query(p, workers=-1)
            d = p - P[i]
            dn = d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-9)
            body = np.clip(0.5 - 0.75 * np.einsum('ij,ij->i', dn, U[i]), 0, 1)
            q = fr.local(p)
            head = np.clip(0.42 - 3.2 * q[:, 2], 0, 1)
            w = np.clip(1 - (np.linalg.norm(p - fr.pos, axis=1) - head_r * 0.55) / (head_r * 0.35), 0, 1)
            return (body * (1 - w) + head * w).astype(F)
        return f


def smooth(x, a, b):
    return D.smooth01(x, a, b)


# ───────────────────────── occhialini ─────────────────────────

def goggles(fr, head, lenses, a, b, strap_up=0.05, width=0.016, snap_field=None, swell=True, paint_drips=(0, 1)):
    """Gli occhialini da piscina, ormai incastrati nella faccia.
    head: campo locale della testa; lenses: i due centri (locali, vicino alla pelle); a, b: mezza larghezza
    e mezza altezza della lente; la cinghia (larga width) gira attorno alla testa e dietro sale di strap_up.
    snap_field: dove posare la cinghia (la testa, oppure testa e capelli); swell: la carne gonfia ai lati
    della cinghia (no se la cinghia passa sopra i capelli); paint_drips: da quali lenti cola la vernice.
    Restituisce i campi locali da aggiungere (la carne cresciuta attorno alle coppe e alla cinghia) e da
    togliere (gli incavi, il solco della cinghia) e gli oggetti: coppe, lenti nere, linguette, ponticello,
    cinghia, colature di vernice."""
    q, n = snap(head, lenses)
    Z = V(0, 0, 1)
    add, cut, rims, domes, lugs, inner, outer = [], [], [], [], [], [], []
    frames = []
    for i in range(2):
        u = unit(np.cross(Z, n[i]))
        v = np.cross(n[i], u)
        s = 1.0 if q[i][0] > 0 else -1.0
        frames.append((u, v, s))
        add.append(oval_ring(q[i] - n[i] * 0.002, u, v, n[i], a + 0.012, b + 0.011, 0.0105))
        cut.append(ellipsoid_axes(q[i] - n[i] * 0.004, (a - 0.001, b - 0.001, 0.010), u, v, n[i]))
        rims.append(oval_ring(q[i] + n[i] * 0.003, u, v, n[i], a + 0.0035, b + 0.0035, 0.0062))
        domes.append(ellipsoid_axes(q[i] - n[i] * 0.0015, (a - 0.001, b - 0.001, 0.0075), u, v, n[i]))
        # la linguetta dove si aggancia la cinghia, sul lato esterno della coppa
        lc = q[i] + u * s * (a + 0.012) + n[i] * 0.002
        lugs.append(box_axes(lc, (0.011, 0.0035, width * 0.42), u * s, n[i], v, 0.0025))
        inner.append(q[i] - u * s * (a + 0.006) + n[i] * 0.004)
        outer.append(q[i] + u * s * (a + 0.020) + n[i] * 0.001)
    sf = snap_field or head
    # la cinghia: dalle linguette tutt'intorno alla testa, dietro un po' più su
    sides = []
    for i in range(2):
        p0 = outer[i]
        s = 1.0 if p0[0] > 0 else -1.0
        phi0 = math.atan2(p0[0], -p0[1])
        want = []
        for t in np.linspace(0, 1, 12)[1:]:
            phi = phi0 + (s * math.pi - phi0) * t
            z = p0[2] + strap_up * math.sin(t * math.pi / 2)
            want.append(V(math.sin(phi) * 0.32, -math.cos(phi) * 0.32, z))
        P, N = snap(sf, [p0] + want)
        sides.append((P, N))
    strap = np.concatenate([sides[0][0], sides[1][0][::-1][1:]])
    snrm = np.concatenate([sides[0][1], sides[1][1][::-1][1:]])
    # la carne gonfia lungo la cinghia (un cordone appena sotto la pelle che sporge di 4 mm) e il canale
    # in cui la cinghia affonda (un cilindro quasi tutto fuori dalla pelle, che ne scava solo il fondo)
    if swell:
        rs = width * 0.9
        add.append(polyline(strap - snrm * (rs - 0.004), [rs] * len(strap)))
    rt = width * 0.56
    cut.append(polyline(strap + snrm * (rt - 0.0025), [rt] * len(strap)))
    # il ponticello sul naso
    mid = (inner[0] + inner[1]) / 2 + V(0, -0.03, 0)
    mq, mn = snap(head, [mid])
    bridge = [inner[0], (inner[0] + mq[0]) / 2 + mn[0] * 0.006, mq[0] + mn[0] * 0.007, (inner[1] + mq[0]) / 2 + mn[0] * 0.006, inner[1]]
    obs = []
    c0 = fr.pt((q[0] + q[1]) / 2)
    obs.append(D.mesh('GoggleFrame', fr.field(sdf.union(*rims, *lugs)), c0 - 0.14, c0 + 0.14, plastica_occhialini(), res=0.0016))
    obs.append(D.mesh('GoggleLens', fr.field(sdf.union(*domes)), c0 - 0.14, c0 + 0.14, lente_dipinta(), res=0.0014))
    Pw = np.array([fr.pt(p) for p in strap])
    Nw = np.array([fr.dir(nn) for nn in snrm])
    Ps = catmull(Pw, 3)
    Ns = catmull(Nw, 3)
    Ns /= np.linalg.norm(Ns, axis=1, keepdims=True)
    obs.append(ribbon('GoggleStrap', Ps - Ns * 0.002 * fr.S, Ns, width * fr.S, 0.0032 * fr.S, plastica_occhialini()))
    cb = catmull(bridge, 4)
    obs.append(tubes('GoggleBridge', local_curves(fr, [(cb, np.full(len(cb), 0.0045))]), plastica_occhialini()))
    # le colature: la vernice nera che è scesa dal bordo della lente sulla guancia
    drips_c = []
    for i in paint_drips:
        u, v, s = frames[i]
        for off, L in ((-0.35, 0.055), (0.25, 0.035)):
            p0 = q[i] - v * (b + 0.012) + u * a * off
            want = [p0] + [p0 + V(0, 0, -L * t) - n[i] * 0.004 for t in (0.25, 0.5, 0.75, 1.0)]
            P, N = snap(sf, want)
            P = P + N * 0.0035
            drips_c.append((P, np.array([0.0048, 0.0042, 0.0036, 0.0034, 0.0048])))
    if drips_c:
        obs.append(tubes('GogglePaintDrips', local_curves(fr, drips_c), lente_dipinta(), m=8))
    return add, cut, obs


# ───────────────────────── orecchie, lucine, bava, acqua ─────────────────────────

def ear(c, out, fwd, h=0.06, w=0.04, th=0.009):
    """Orecchio umano a conchiglia girato in avanti (Fangy caccia a orecchio): una lamina ovale col bordo
    arrotolato e la conca scavata, il lobo in basso. Campo locale."""
    c = V(*c)
    n = unit(unit(out) * 0.6 + unit(fwd) * 0.4)
    up = V(0, 0, 1) - (V(0, 0, 1) @ n) * n
    up = unit(up)
    t = np.cross(up, n)
    plate = ellipsoid_axes(c + n * 0.004, (w, h, th * 1.6), t, up, n)
    bowl = ellipsoid_axes(c + n * 0.015, (w * 0.66, h * 0.70, th * 1.5), t, up, n)
    helix = oval_ring(c + n * 0.008, t, up, n, w * 0.9, h * 0.93, th * 0.6)
    lobe = sdf.sphere(c + n * 0.004 - up * h * 0.86, w * 0.34)
    root = ellipsoid_axes(c - n * 0.012, (w * 0.55, h * 0.55, 0.02), t, up, n)
    return sdf.union(sdf.subtract(plate, bowl, k=0.004), helix, lobe, root, k=0.008)


def cups(pts, nrm, radii):
    """Le coppette delle lucine: per ogni punto l'incavo e l'orlo (si valuta solo la lucina più vicina)."""
    pts, nrm, radii = np.asarray(pts, F), np.asarray(nrm, F), np.asarray(radii, F)
    tree = cKDTree(pts)

    def near(p):
        _, i = tree.query(p, workers=-1)
        return p - pts[i], nrm[i], radii[i]

    def holes(p):
        d, n, r = near(p)
        return np.linalg.norm(d + n * (r * 0.25)[:, None], axis=1) - r * 1.08

    def rims(p):
        d, n, r = near(p)
        dd = d - n * (r * 0.15)[:, None]
        h = np.einsum('ij,ij->i', dd, n)
        rad = np.linalg.norm(dd - h[:, None] * n, axis=1)
        return np.sqrt((rad - r * 1.3) ** 2 + h * h) - r * 0.42

    return around(holes, pts, 0.05), around(rims, pts, 0.05)


def goo_material():
    """La melma della bava: verdognola e lattiginosa, lucidissima (la stessa delle gocce di Lampy). Meno
    trasparente della melma di skin.py, così nella bozza si legge come bava e non come ghiaccioli di vetro."""
    m = bpy.data.materials.get('FangyGoo')
    if m:
        return m
    m, g = material('FangyGoo')
    g.output_material(g.principled(color=(0.62, 0.74, 0.50), rough=0.04, transmission=0.45, ior=1.36, coat=1.0, coat_rough=0.01,
                                   sss=0.5, sss_radius=(0.6, 0.8, 0.4), sss_scale=0.01))
    return m


def drips(name, field, anchors, rng, lmin=0.025, lmax=0.05):
    """Bava che cola: gocce grasse di melma appese ai punti (posati sulla superficie). Corte: sotto la bocca
    le gocce lunghe e chiare si confondevano con le zanne."""
    pts, _ = snap(field, anchors)
    parts = []
    for q in pts:
        L = rng.uniform(lmin, lmax)
        parts.append(skin.drip(q + V(0, 0, 0.004), L, r0=0.0065, r1=rng.uniform(0.010, 0.013)))
    lo, hi = pts.min(0) - 0.03, pts.max(0) + 0.03
    lo[2] -= lmax + 0.03
    return D.mesh(name, sdf.union(*parts), lo, hi, goo_material(), res=0.002)


def strands(fr, pairs, r=0.0022, sag=0.03):
    """Fili di bava fra due punti (locali), che si afflosciano in mezzo: curve per tubes()."""
    out = []
    for a, b, sg in pairs:
        a, b = fr.pt(a), fr.pt(b)
        t = np.linspace(0, 1, 9)
        P = np.array([a * (1 - x) + b * x + V(0, 0, -sg * 4 * x * (1 - x)) for x in t])
        R = r * (0.55 + 0.45 * np.abs(2 * t - 1))
        out.append((P, R))
    return out


def water_material():
    """Il mare di notte: nero e bagnato, con le onde lunghe e le increspature che rompono i riflessi (uno
    specchio perfetto rifletteva il corpo e le file di lucine, e Fangy sembrava in piedi su due gambe)."""
    m = bpy.data.materials.get('FangyWater')
    if m:
        return m
    m, g = material('FangyWater')
    co = g.texcoord('Object')
    swell = g.noise(g.mapping(co, scale=(1.0, 2.6, 1.0)), scale=2.4, detail=2.0)
    chop = g.noise(co, scale=14.0, detail=2.0, rough=0.5)
    h = g.add(swell.fac, g.mul(chop.fac, 0.25))
    # liscia ma ondulata: i riflessi si rompono in strisce, senza l'alone grigio di un'acqua ruvida
    g.output_material(g.principled(color=(0.003, 0.009, 0.013), rough=0.05, spec=0.5, normal=g.bump(h, strength=0.32, distance=0.03)))
    return m


def water():
    w = rbox('Water', (120, 120, 0.01), (0, 40.0, -0.005), bevel=0.0, col='set')
    w.data.materials.append(water_material())
    set_lightgroup(w, 'ambient')
    return w


def ripples():
    """Le increspature dove le mani e la pancia entrano nell'acqua: anelli bassi e lucidi."""
    parts, pts = [], []
    for c, radii in (((-0.275, -0.37), (0.075, 0.13, 0.20)), ((0.275, -0.37), (0.075, 0.13, 0.20)), ((0.0, 0.58), (0.19, 0.27))):
        for j, R in enumerate(radii):
            parts.append(D.torus_axis(V(c[0], c[1], 0.0), (0, 0, 1), R, 0.0042 - 0.0009 * j))
            pts += [V(c[0] - R, c[1] - R, 0), V(c[0] + R, c[1] + R, 0)]
    P = np.array(pts)
    return D.mesh('Ripples', sdf.union(*parts), P.min(0) - 0.02, P.max(0) + 0.02,
                  mat_simple('RippleWater', (0.006, 0.016, 0.022), rough=0.03, spec=0.9, coat=0.6), res=0.0022)


# ───────────────────────── montaggio ─────────────────────────

def fangy_finish(fr, head, cut=None, head_r=0.30, neck=(0, 0.12, -0.04), neck_r=0.10, head_lights=(), attrs_extra=None):
    """Unisce testa e corpo, scava le branchie e le coppette delle lucine; crea la pelle, le lucine (con un
    po' di luce vera sulla pelle bagnata attorno), l'acqua e le increspature.
    head, cut: campi locali della testa; head_lights: [(punto locale, raggio)] delle lucine della testa."""
    head_r = head_r * fr.S
    body = Body(fr.pt(neck), neck_r)
    hw = bounded(fr.field(head), fr.pos, head_r)
    f = sdf.union(body.field(), hw, k=0.05)
    if cut is not None:
        f = sdf.subtract(f, bounded(fr.field(cut), fr.pos, head_r), k=0.005)
    f = sdf.subtract(f, body.gills(), k=0.006)
    want, rr = body.light_rows()
    want += [fr.pt(p) for p, _ in head_lights]
    rr += [r for _, r in head_lights]
    pts, nrm = snap(f, want)
    keep = pts[:, 2] > 0.01
    pts, nrm, rr = pts[keep], nrm[keep], np.asarray(rr, F)[keep]
    holes, rims = cups(pts, nrm, rr)
    f = sdf.subtract(sdf.union(f, rims, k=0.003), holes, k=0.002)
    attrs = {'ventre': body.ventre(fr, head_r)}
    attrs.update(attrs_extra or {})
    lo = np.minimum(V(-0.43, -0.46, -0.035), fr.pos - head_r)
    hi = np.maximum(V(0.43, 0.84, 1.10), fr.pos + head_r)
    lo[2] = -0.035
    obs = [skin_mesh('FangySkin', f, lo, hi, pelle_fangy(), attrs=attrs)]
    obs.append(balls('FangyLights', pts - nrm * (rr * 0.30)[:, None], rr * 0.95, luce_material()))
    for j, (q, n_) in enumerate(zip(pts, nrm)):
        if j % 3 == 0:
            D.point_light(f'Fotoforo{j}', tuple(map(float, q + n_ * 0.018)), 0.10, (0.25, 0.85, 1.0), radius=0.006)
    obs += [water(), ripples()]
    return obs, f


# ───────────────────────── A · Sciabola ─────────────────────────

def fangy_a():
    """A · Sciabola: la testa grande del pesce dente di sciabola, ossuta, con le creste e l'opercolo; la
    bocca enorme non si chiude più: le sciabole di sopra pendono davanti alla mandibola calata, quelle di
    sotto salgono fuori dal muso e si incrociano come nel pesce vipera. Fossette in fila sulle guance, sulla
    mascella e sul cranio (il pesce sente le vibrazioni così); gli occhialini affondati nella carne sotto
    la visiera ossea, piccoli sul testone."""
    fr = Head((0, -0.19, 0.85), yaw=-7, pitch=10, roll=6, scale=1.14)
    cran = sdf.ellipsoid(V(0, 0.03, 0.03), (0.13, 0.165, 0.115))
    brow = sdf.ellipsoid(V(0, -0.088, 0.07), (0.118, 0.08, 0.06))
    visor = sdf.ellipsoid(V(0, -0.118, 0.085), (0.12, 0.05, 0.03))           # la visiera ossea sopra gli occhialini
    snout = sdf.ellipsoid(V(0, -0.158, -0.018), (0.102, 0.088, 0.058))
    cheeks = sdf.union(*[sdf.ellipsoid(V(s * 0.088, -0.06, -0.03), (0.05, 0.08, 0.065)) for s in (-1, 1)])
    jaw = sdf.union(*[chain([V(s * 0.10, 0.05, -0.075), V(s * 0.09, -0.08, -0.14), V(s * 0.052, -0.178, -0.158), V(0, -0.21, -0.158)],
                            [0.034, 0.039, 0.036, 0.034], k=0.02) for s in (-1, 1)], k=0.02)
    throat = sdf.ellipsoid(V(0, -0.03, -0.115), (0.09, 0.12, 0.06))
    ridges = sdf.union(*[chain([V(s * 0.045, -0.13, 0.09), V(s * 0.062, -0.02, 0.152), V(s * 0.05, 0.10, 0.145)], [0.012, 0.017, 0.012], k=0.01) for s in (-1, 1)])
    # l'opercolo, la placca che copre le branchie dei pesci, con la fessura dietro
    opercles = sdf.union(*[ellipsoid_axes(V(s * 0.112, 0.035, -0.05), (0.075, 0.03, 0.075), V(0, 1, 0.15), V(s, 0, 0), V(0, -0.15, 1))
                           for s in (-1, 1)])
    head = sdf.union(cran, brow, visor, snout, cheeks, jaw, throat, ridges, opercles, k=0.03)
    slits = sdf.union(*[ellipsoid_axes(V(s * 0.118, 0.105, -0.055), (0.009, 0.03, 0.068), V(0, 1, 0), V(s, 0, 0), V(0, 0, 1)) for s in (-1, 1)])
    mouth = sdf.union(sdf.ellipsoid(V(0, -0.115, -0.10), (0.092, 0.125, 0.036)), sdf.ellipsoid(V(0, -0.045, -0.09), (0.07, 0.10, 0.04)), slits)
    # le fossette della linea laterale, in fila sulle guance, sulla mascella e sulla fronte
    want = []
    for s in (-1, 1):
        want += list(arc((s * 0.10, -0.15, 0.005), (s * 0.13, -0.05, 0.0), (s * 0.13, 0.07, 0.02), 8))
        want += list(arc((s * 0.07, -0.17, -0.15), (s * 0.105, -0.07, -0.15), (s * 0.11, 0.03, -0.12), 7))
        want += list(arc((s * 0.03, -0.165, 0.115), (s * 0.05, -0.08, 0.16), (s * 0.06, 0.04, 0.17), 5))
    pq, pn = snap(head, want)
    pits = around(sdf.union(*[sdf.sphere(q - n * 0.002, 0.0068) for q, n in zip(pq, pn)]), pq, 0.04)
    add, gcut, gobs = goggles(fr, head, [V(s * 0.060, -0.15, 0.048) for s in (-1, 1)], 0.030, 0.022, strap_up=0.04)
    head = sdf.union(head, *add, k=0.016)
    cut = sdf.union(mouth, pits, *gcut)

    def attr_mouth(p):
        q = fr.local(p)
        e = np.linalg.norm((q - V(0, -0.09, -0.10)) / V(0.095, 0.14, 0.045), axis=1)
        return np.clip((1.15 - e) / 0.2, 0, 1).astype(F)

    lights = [(V(s * 0.06 + s * 0.05 * t, -0.17 + 0.19 * t, -0.17 + 0.02 * t), 0.0068) for s in (-1, 1) for t in np.linspace(0, 1, 7)]
    lights += [(V(s * 0.112, -0.085, -0.02), 0.011) for s in (-1, 1)]                 # la lucina grande sotto l'occhio
    obs, skin_f = fangy_finish(fr, head, cut, head_lights=lights, attrs_extra={'mouth': attr_mouth})
    obs += gobs
    c0 = fr.pt((0, -0.06, -0.10))
    obs.append(D.mesh('FangyThroat', fr.field(sdf.ellipsoid(V(0, -0.06, -0.10), (0.065, 0.10, 0.03))), c0 - 0.16, c0 + 0.16, D.dark_throat(), res=0.004))
    # le zanne: sciabole di sopra che pendono davanti alla mandibola, zanne di sotto fuori dal muso, aghi in fila
    fangs = []
    for s in (-1, 1):
        fangs.append(fang((s * 0.046, -0.214, -0.055), (s * 0.06, -0.16, -1), 0.29, 0.0125, bend=(0, 0.04, 0)))
        fangs.append(fang((s * 0.078, -0.19, -0.058), (s * 0.12, -0.10, -1), 0.15, 0.0085, bend=(0, 0.02, 0)))
        fangs.append(fang((s * 0.094, -0.14, -0.066), (s * 0.15, -0.05, -1), 0.075, 0.0065))
        fangs.append(fang((s * 0.026, -0.212, -0.132), (s * 0.05, -0.45, 1), 0.17, 0.0105))       # le zanne del pesce vipera
        fangs.append(fang((s * 0.072, -0.172, -0.13), (s * 0.40, -0.30, 1), 0.125, 0.0092, bend=(0, 0.025, 0)))
        fangs.append(fang((s * 0.086, -0.12, -0.128), (s * 0.30, -0.20, 1), 0.07, 0.0062))
        for t in np.linspace(0.1, 0.9, 5):
            x = s * (0.02 + 0.06 * t)
            fangs.append(fang((x, -0.205 + 0.07 * t * t, -0.068), (s * 0.1, -0.3, -1), 0.034 + 0.014 * (1 - t), 0.0036))
            fangs.append(fang((x * 0.95, -0.19 + 0.07 * t * t, -0.132), (s * 0.1, -0.35, 1), 0.03 + 0.012 * (1 - t), 0.0034))
    obs.append(tubes('FangyFangs', local_curves(fr, fangs), D.needle_teeth()))
    # la bava: fili fra le zanne, gocce dal mento e dalle punte
    obs.append(tubes('FangyDrool', strands(fr, [((-0.046, -0.235, -0.16), (-0.05, -0.20, -0.15), 0.02),
                                                 ((0.046, -0.235, -0.18), (0.074, -0.19, -0.125), 0.025),
                                                 ((-0.078, -0.205, -0.12), (-0.074, -0.17, -0.13), 0.012)]), goo_material()))
    obs.append(drips('FangySlime', skin_f, [fr.pt((0.0, -0.21, -0.18)), fr.pt((-0.04, -0.19, -0.185)), fr.pt((0.06, -0.16, -0.185))],
                     np.random.default_rng(5)))
    return (obs, *TESTI['A'])


# ───────────────────────── B · Molosso ─────────────────────────

def fangy_b():
    """B · Molosso: a metà fra il pesce e il bambino. Cranio tondo da quasi-uomo, muso corto e largo da
    mastino con le labbra che pendono, la mandibola in avanti; le zanne di sopra pendono dalle labbra fin
    sotto il mento, quelle di sotto salgono davanti al labbro. Orecchie umane enormi, girate in avanti ad
    ascoltare; gli occhialini incastrati sotto la fronte grinzosa, una fila di lucine lungo le labbra."""
    fr = Head((0, -0.18, 0.855), yaw=-9, pitch=8, roll=-7, scale=1.10)
    cran = sdf.ellipsoid(V(0, 0.035, 0.05), (0.122, 0.14, 0.125))
    brow = sdf.ellipsoid(V(0, -0.078, 0.088), (0.10, 0.06, 0.05))
    eyes_plane = sdf.ellipsoid(V(0, -0.10, 0.03), (0.11, 0.065, 0.06))       # la faccia sotto la fronte, dove stanno le lenti
    muzzle = sdf.ellipsoid(V(0, -0.142, -0.032), (0.105, 0.085, 0.07))
    flews = sdf.union(*[sdf.ellipsoid(V(s * 0.072, -0.152, -0.10), (0.05, 0.062, 0.07)) for s in (-1, 1)])
    jaw = sdf.union(sdf.ellipsoid(V(0, -0.135, -0.152), (0.088, 0.105, 0.04)), sdf.sphere(V(0, -0.212, -0.155), 0.034), k=0.02)
    nose = sdf.ellipsoid(V(0, -0.207, 0.0), (0.036, 0.03, 0.024))
    cheekbones = sdf.union(*[sdf.sphere(V(s * 0.082, -0.10, 0.005), 0.04) for s in (-1, 1)])
    base = sdf.union(cran, brow, eyes_plane, muzzle, flews, jaw, nose, cheekbones, k=0.035)

    def wrinkles(p):
        """Le pieghe della fronte e del muso del mastino."""
        fore = (0.5 + 0.5 * np.cos(2 * np.pi * (p[:, 2] + 2.2 * p[:, 0] ** 2) / 0.024)) ** 2
        fore *= smooth(-p[:, 1], 0.03, 0.08) * smooth(p[:, 2], 0.06, 0.09) * (1 - smooth(p[:, 2], 0.115, 0.135))
        d = np.sqrt(p[:, 0] ** 2 + ((p[:, 2] + 0.01) * 1.3) ** 2)
        muz = (0.5 + 0.5 * np.cos(2 * np.pi * d / 0.026)) ** 3 * smooth(d, 0.04, 0.06) * (1 - smooth(d, 0.10, 0.12))
        muz *= smooth(-p[:, 1], 0.12, 0.17) * smooth(p[:, 2], -0.08, -0.05)
        return (fore + 0.7 * muz).astype(F)

    head = sdf.displace(base, wrinkles, -0.0045)
    ears = sdf.union(*[ear(V(s * 0.132, -0.005, -0.03), V(s, 0, 0), V(0, -1, 0), h=0.09, w=0.06, th=0.012) for s in (-1, 1)])
    add, gcut, gobs = goggles(fr, head, [V(s * 0.052, -0.18, 0.032) for s in (-1, 1)], 0.029, 0.021, strap_up=0.095)
    head = sdf.union(head, ears, *add, k=0.014)
    nostrils = sdf.union(*[ellipsoid_axes(V(s * 0.014, -0.234, -0.004), (0.006, 0.014, 0.011), V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)) for s in (-1, 1)])
    mouth = sdf.union(sdf.ellipsoid(V(0, -0.168, -0.126), (0.074, 0.075, 0.016)), sdf.ellipsoid(V(0, -0.10, -0.12), (0.06, 0.08, 0.026)))
    cut = sdf.union(nostrils, mouth, *gcut)

    def attr_mouth(p):
        q = fr.local(p)
        e = np.linalg.norm((q - V(0, -0.14, -0.126)) / V(0.08, 0.10, 0.026), axis=1)
        return np.clip((1.15 - e) / 0.2, 0, 1).astype(F)

    def attr_lips(p):
        """L'orlo livido delle labbra pendenti."""
        q = fr.local(p)
        e = np.linalg.norm((q - V(0, -0.15, -0.125)) / V(0.115, 0.10, 0.04), axis=1)
        return (np.clip(1 - np.abs(e - 1.0) / 0.22, 0, 1) * smooth(-q[:, 1], 0.08, 0.14)).astype(F)

    lights = [(p, 0.0066) for s in (-1, 1) for p in arc((s * 0.045, -0.23, -0.13), (s * 0.10, -0.20, -0.125), (s * 0.13, -0.12, -0.10), 6)]
    obs, skin_f = fangy_finish(fr, head, cut, head_lights=lights, attrs_extra={'mouth': attr_mouth, 'labbra': attr_lips})
    obs += gobs
    c0 = fr.pt((0, -0.12, -0.125))
    obs.append(D.mesh('FangyThroat', fr.field(sdf.ellipsoid(V(0, -0.12, -0.125), (0.06, 0.08, 0.016))), c0 - 0.15, c0 + 0.15, D.dark_throat(), res=0.004))
    fangs = []
    for s in (-1, 1):
        fangs.append(fang((s * 0.072, -0.19, -0.12), (s * 0.08, -0.12, -1), 0.25, 0.0118, bend=(0, 0.03, 0)))
        fangs.append(fang((s * 0.094, -0.15, -0.115), (s * 0.15, -0.05, -1), 0.13, 0.0080, bend=(0, 0.015, 0)))
        fangs.append(fang((s * 0.048, -0.226, -0.142), (s * 0.12, -0.25, 1), 0.105, 0.0095, bend=(0, 0.02, 0)))
        for t in np.linspace(0.15, 0.85, 4):
            fangs.append(fang((s * (0.012 + 0.03 * t), -0.236 + 0.02 * t, -0.14), (s * 0.05, -0.2, 1), 0.022, 0.0042))
    obs.append(tubes('FangyFangs', local_curves(fr, fangs), D.needle_teeth()))
    obs.append(tubes('FangyDrool', strands(fr, [((-0.072, -0.205, -0.22), (-0.06, -0.19, -0.16), 0.03),
                                                 ((0.072, -0.20, -0.26), (0.09, -0.16, -0.16), 0.04)]), goo_material()))
    obs.append(drips('FangySlime', skin_f, [fr.pt((s * 0.075, -0.16, -0.17)) for s in (-1, 1)] + [fr.pt((0.0, -0.21, -0.19))],
                     np.random.default_rng(8)))
    return (obs, *TESTI['B'])


# ───────────────────────── C · Bambino ─────────────────────────

def fangy_c():
    """C · Bambino: la testa tonda di un bambino in piscina, spinta avanti su un collo lungo e sottile, con
    gli occhialini neri (la vernice è colata sulla guancia come una lacrima) e la frangetta bagnata sotto la
    cinghia; le orecchie a sventola, la testa piegata ad ascoltare. La bocca è aperta come a chiamare
    «Marco!» ma è piena di aghi lunghissimi che pendono fin sotto il mento; sulle guance le lentiggini sono
    lucine accese."""
    fr = Head((0, -0.215, 0.85), yaw=-12, pitch=6, roll=12, scale=1.2)
    cran = sdf.sphere(V(0, 0.02, 0.045), 0.112)
    face = sdf.ellipsoid(V(0, -0.045, -0.035), (0.092, 0.08, 0.095))
    cheeks = sdf.union(*[sdf.sphere(V(s * 0.056, -0.087, -0.05), 0.040) for s in (-1, 1)])
    chin = sdf.sphere(V(0, -0.092, -0.112), 0.028)
    nose = sdf.union(sdf.sphere(V(0, -0.128, -0.006), 0.0135), sdf.round_cone(V(0, -0.112, 0.03), V(0, -0.126, -0.0), 0.010, 0.012), k=0.01)
    lips = oval_ring(V(0, -0.121, -0.068), V(1, 0, 0), V(0, 0, 1), V(0, -1, 0), 0.040, 0.022, 0.0065)
    base = sdf.union(cran, face, cheeks, chin, nose, lips, k=0.022)
    # i capelli bagnati, a scodella: un guscio sul cranio, più basso dietro, con le ciocche
    hair_shell = sdf.intersect(sdf.subtract(sdf.sphere(V(0, 0.02, 0.045), 0.124), sdf.sphere(V(0, 0.02, 0.045), 0.104)),
                               D.above(V(0, -0.10, 0.066), (0, 0.45, 1.0)))

    def locks(p):
        ang = np.arctan2(p[:, 0], -(p[:, 1] - 0.02))
        return ((0.5 + 0.5 * np.cos(ang * 22.0 + 6.0 * p[:, 2])) ** 2).astype(F)

    hair = sdf.displace(hair_shell, locks, -0.004)
    ears = sdf.union(*[ear(V(s * 0.116, 0.0, -0.01), V(s, 0, 0), V(0, -0.5, 0), h=0.048, w=0.034, th=0.008) for s in (-1, 1)])
    hair = sdf.subtract(hair, sdf.union(*[sdf.sphere(V(s * 0.12, 0.0, -0.01), 0.045) for s in (-1, 1)]), k=0.006)
    hair_snap = sdf.union(base, hair)
    add, gcut, gobs = goggles(fr, base, [V(s * 0.040, -0.104, 0.024) for s in (-1, 1)], 0.026, 0.019, strap_up=0.035,
                              width=0.013, snap_field=hair_snap, swell=False, paint_drips=(0,))
    head = sdf.union(base, ears, *add, k=0.012)
    mouth = sdf.union(sdf.ellipsoid(V(0, -0.115, -0.068), (0.034, 0.03, 0.015)), sdf.ellipsoid(V(0, -0.075, -0.066), (0.03, 0.05, 0.022)))
    nostrils = sdf.union(*[sdf.sphere(V(s * 0.0075, -0.137, -0.015), 0.0045) for s in (-1, 1)])
    cut = sdf.union(mouth, nostrils, *gcut)

    def attr_mouth(p):
        q = fr.local(p)
        e = np.linalg.norm((q - V(0, -0.10, -0.068)) / V(0.036, 0.05, 0.017), axis=1)
        return np.clip((1.1 - e) / 0.2, 0, 1).astype(F)

    def attr_lips(p):
        q = fr.local(p)
        e = np.sqrt((q[:, 0] / 0.040) ** 2 + ((q[:, 2] + 0.068) / 0.022) ** 2)
        return (np.clip(1 - np.abs(e - 1.0) / 0.45, 0, 1) * smooth(-q[:, 1], 0.09, 0.11)).astype(F)

    # le lentiggini accese sulle guance e sul naso, e una fila di lucine sotto la mascella
    rng = np.random.default_rng(21)
    lights = []
    for s in (-1, 1):
        for _ in range(8):
            a, rad = rng.uniform(0, 2 * math.pi), 0.022 * math.sqrt(rng.uniform(0.05, 1))
            lights.append((V(s * 0.060 + rad * math.cos(a) * 0.9, -0.12, -0.030 + rad * math.sin(a) * 0.7), float(rng.uniform(0.0032, 0.0046))))
        lights.append((V(s * 0.014, -0.135, 0.004), 0.0034))
        lights += [(V(s * (0.025 + 0.05 * t), -0.085 + 0.08 * t, -0.13 + 0.02 * t), 0.0050) for t in np.linspace(0, 1, 5)]
    obs, skin_f = fangy_finish(fr, head, cut, head_r=0.24, neck=(0, 0.07, -0.075), neck_r=0.068, head_lights=lights,
                               attrs_extra={'mouth': attr_mouth, 'labbra': attr_lips})
    obs += gobs
    hp = fr.pos
    obs.append(skin_mesh('FangyHair', fr.field(sdf.subtract(hair, sdf.union(*gcut), k=0.002)), hp - 0.27, hp + 0.27, D.wet_hair(), res=0.0024))
    # la frangetta: ciocche appiccicate alla fronte fino al bordo degli occhialini
    locks_c = []
    for x, L in ((-0.066, 0.9), (-0.04, 1.0), (-0.012, 0.8), (0.015, 1.0), (0.042, 0.85), (0.068, 0.95)):
        p0 = V(x * 0.85, -0.07, 0.118)
        p1 = V(x * 1.0, -0.102, 0.092)
        p2 = V(x * 1.05 + 0.006, -0.114, 0.072 - 0.014 * L)
        q, n = snap(base, [p0, p1, p2])
        P = catmull(q + n * 0.005, 4)
        locks_c.append((np.array([fr.pt(v) for v in P]), np.linspace(0.0125, 0.004, len(P))))
    obs.append(tubes('FangyFringe', locks_c, D.wet_hair(), m=10))
    c0 = fr.pt((0, -0.09, -0.068))
    obs.append(D.mesh('FangyThroat', fr.field(sdf.ellipsoid(V(0, -0.09, -0.068), (0.03, 0.04, 0.014))), c0 - 0.08, c0 + 0.08, D.dark_throat(), res=0.002))
    fangs = []
    for s in (-1, 1):
        fangs.append(fang((s * 0.013, -0.115, -0.057), (s * 0.06, -0.45, -1), 0.17, 0.0078, bend=(0, 0.025, 0)))
        fangs.append(fang((s * 0.030, -0.112, -0.059), (s * 0.15, -0.42, -1), 0.12, 0.0062, bend=(0, 0.018, 0)))
        fangs.append(fang((s * 0.021, -0.114, -0.080), (s * 0.10, -0.42, 1), 0.07, 0.0058, bend=(0, 0.012, 0)))
        for t in np.linspace(0.0, 1.0, 3):
            fangs.append(fang((s * (0.006 + 0.02 * t), -0.112, -0.060), (0, -0.2, -1), 0.010, 0.0030))
            fangs.append(fang((s * (0.008 + 0.02 * t), -0.112, -0.077), (0, -0.2, 1), 0.009, 0.0028))
    obs.append(tubes('FangyFangs', local_curves(fr, fangs), D.needle_teeth()))
    obs.append(tubes('FangyDrool', strands(fr, [((-0.013, -0.15, -0.20), (-0.006, -0.12, -0.085), 0.02),
                                                 ((0.029, -0.135, -0.18), (0.02, -0.12, -0.085), 0.015)], r=0.0016), goo_material()))
    obs.append(drips('FangySlime', skin_f, [fr.pt((0.0, -0.108, -0.135)), fr.pt((0.02, -0.10, -0.13))], np.random.default_rng(3)))
    return (obs, *TESTI['C'])


# ───────────────────────── scena ─────────────────────────

D.CREATURES['fangy'] = {
    'title': 'FANGY — dettagli della testa (notte 5, sagoma B «Mastino»), nell\'acqua · colori da approvare',
    'variants': [fangy_a, fangy_b, fangy_c],
    'cam': CAM,
    'subject': (0, -0.15, 0.70), 'key': 40, 'rim': 170,
}


if __name__ == '__main__':
    if '--tavola' in sys.argv:
        # solo la tavola, dai pannelli già in cache (dopo aver rifatto un pannello con --only)
        panels = [(os.path.join(D.TMP, f'fangy_{k}.png'), *TESTI[k]) for k in 'ABC']
        print('tavola', D.compose('fangy', panels), flush=True)
        sys.exit(0)
    only = None
    if '--only' in sys.argv:
        only = 'ABC'.index(sys.argv[sys.argv.index('--only') + 1])
    panels = []
    for i in range(len(D.CREATURES['fangy']['variants'])):
        if only is not None and i != only:
            continue
        panels.append(D.render_variant('fangy', i))
        print('ok fangy', 'ABC'[i], flush=True)
    if only is None and len(panels) == 3:
        print('tavola', D.compose('fangy', panels), flush=True)
