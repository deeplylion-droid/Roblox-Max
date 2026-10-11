"""
Le ultime inquadrature dei due finali segreti (docs/NOTTI_E_MOSTRI.md, «I finali»): due immagini fisse che il
motore mostra alla fine della cinematica con un lento movimento di camera.

⚠️ DA APPROVARE (anteprime in docs/concept/finali_*_anteprima.jpg):
  molo     «I tuoi»: il molo di legno del paese all'alba, il gozzo ormeggiato, e sulle assi bagnate sette file di
           piccole impronte che dalla scaletta in fondo al molo vanno verso il paese, una diversa per ogni mostro:
           le palmate di Gulpy, i piedini di Molly, le scarpette di Hatch (piccole, ma col passo lunghissimo),
           tante zampette per Robin (con la coda che striscia in mezzo), gli anelli della ventosa di Lampy (a
           distanza, come una sanguisuga che cammina), gli artigli sottili di Fangy (sulle nocche), la scia
           strisciante di Archie.
  edicola  «Nessuno»: l'edicola votiva dello scoglio da vicino, nella luce grigia del primo mattino, con le foto dei
           bambini (binocolo.lore_photos), sfocate dietro; davanti, appesa con una molletta a uno spago, una Polaroid
           nuova, l'unica non sbiadita, a fuoco: la barca di notte con la lampara accesa e la sagoma del pescatore,
           scattata da sotto, dal pelo dell'acqua, come da qualcuno che nuotava lì accanto. La Polaroid è un render
           vero della scena del gioco (polaroid_scene_image()); FINALI_RIUSA_FOTO=1 riusa quella già fatta.

La scena del molo usa la costa, il paese e il faro di env.py, spostati e girati in modo che la barca (che sta
nell'origine, col buco nel mare di env.build_sea) sia ormeggiata al molo, a 24° a sinistra del campanile.

Uso: tools/.venv/bin/python tools/render/finali.py [molo|edicola ...] [--fast]
       anteprima (1600×900, pochi campioni) → docs/concept/finali_<scena>_anteprima.jpg
     tools/.venv/bin/python tools/render/finali.py [molo|edicola ...] --finale
       (solo dopo l'approvazione) 2560×1440 → public/assets/img/fin_<scena>.webp, codificati come i jumpscare
       (post.encode_light_pass con la sua scala), e la voce overlays.json → endings.<scena>
"""
from __future__ import annotations

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

import env  # noqa: E402
import post  # noqa: E402
from common import (CACHE, EYE, OUT_IMG, ROOT, collection, log, mesh_from_arrays, perspective_camera,  # noqa: E402
                    render, reset_scene, set_lightgroup, set_visibility)
from geo import catmull, cylinder, rbox, sphere, tube  # noqa: E402
from nodes import material, world  # noqa: E402

FAST = '--fast' in sys.argv
FINALE = '--finale' in sys.argv
COL = 'finali'
OVERLAYS = os.path.join(OUT_IMG, 'overlays.json')
TEX = os.path.join(CACHE, 'finali')


def _mat(name, color, rough=0.5, metal=0.0, **kw):
    m, g = material(name)
    g.output_material(g.principled(color=color, rough=rough, metal=metal, **kw))
    return m


def _amb(obs):
    for o in obs:
        set_lightgroup(o, 'ambient')
    return obs


def boxes_mesh(name, boxes, mat, col=COL):
    """Tante scatole in una mesh sola: (centro, misure, rotazione z in radianti)."""
    verts, faces = [], []
    for (cx, cy, cz), (sx, sy, sz), rz in boxes:
        c, s = math.cos(rz), math.sin(rz)
        b = len(verts)
        for dz in (-0.5, 0.5):
            for dx, dy in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
                x, y = dx * sx, dy * sy
                verts.append((cx + x * c - y * s, cy + x * s + y * c, cz + dz * sz))
        faces += [(b, b + 3, b + 2, b + 1), (b + 4, b + 5, b + 6, b + 7), (b, b + 1, b + 5, b + 4),
                  (b + 1, b + 2, b + 6, b + 5), (b + 2, b + 3, b + 7, b + 6), (b + 3, b, b + 4, b + 7)]
    ob = mesh_from_arrays(name, np.array(verts), faces, smooth=False, col=col)
    ob.data.materials.append(mat)
    bev = ob.modifiers.new('B', 'BEVEL')
    bev.width = 0.006
    bev.segments = 2
    set_lightgroup(ob, 'ambient')
    return ob


# ═════════════════════════ il molo all'alba ═════════════════════════

PIER_YAW = env.VILLAGE_YAW - 3.0       # dove il molo tocca la riva (il campanile sta a +1.8, la gru a +3.5)
PIER_X = 2.35                          # asse del molo (la barca è nell'origine, il molo alla sua dritta)
PIER_W = 2.4
DECK_Z = 1.10                          # piano delle assi sul mare
Y_OUT, Y_LAND = -14.0, 9.0             # le due teste del molo: in fondo, verso il largo, e sulla banchina
Y_SHORE = 12.0                         # la riva (s = 0)
TEX_RES = 0.004                        # metri per pixel della maschera delle impronte
PRINT_SCALE = 1.3                      # le impronte un po' più grandi del vero, per leggersi da in piedi
SUN_DIR = Vector((-0.27, -0.95, 0.12)).normalized()    # il sole appena sorto sopra le colline del parco, davanti


def place_world(objs):
    """Sposta e gira costa, paese e faro: la riva a PIER_YAW finisce in (PIER_X, Y_SHORE), verso il largo = −Y."""
    sx, sy, _ = env.surface_at(PIER_YAW, 0.0)
    a = math.radians(PIER_YAW)
    R = Matrix.Rotation(a, 4, 'Z')
    s_new = Vector((PIER_X, Y_SHORE, 0.0))
    b_old = Vector((sx, sy, 0.0)) - R.inverted() @ s_new
    M = R @ Matrix.Translation(-b_old)
    for o in objs:
        if o.parent is None:
            o.matrix_world = M @ o.matrix_world


def dawn_sky():
    """Cielo della prima luce: verso il sole arancio e rosa, dalla parte opposta lilla, in alto azzurro spento;
    qualche striscia di nuvole accesa di rosa da sotto."""
    w, g = world('DawnSky')
    w.lightgroup = 'ambient'
    d = g.texcoord('Generated')
    dx, dy, dz = g.sep(d)
    sd = tuple(SUN_DIR)
    cs = g.vmath('DOT_PRODUCT', d, sd)
    c0 = g.math('MAXIMUM', cs, 0.0)
    up = g.clamp01(dz)
    toward = g.pow(g.mul(g.add(cs, 1.0), 0.5), 2.2)       # 0 dalla parte opposta, 1 verso il sole
    hor_away = (0.20, 0.16, 0.21)
    hor_sun = (0.95, 0.42, 0.17)
    horizon = g.mix(toward, hor_away, hor_sun)
    zenith = g.mix(toward, (0.050, 0.075, 0.150), (0.11, 0.11, 0.17))
    sky = g.mix(g.pow(up, 0.45), horizon, zenith)
    # alone del sole
    halo = g.add(g.mul(g.pow(c0, 24.0), 1.6), g.mul(g.pow(c0, 5.0), 0.35))
    sky = g.mix(1.0, sky, g.comb(g.mul(halo, 1.0), g.mul(halo, 0.55), g.mul(halo, 0.25)), blend='ADD', clamp=False)
    # disco del sole, appena sopra l'orizzonte
    disc = g.smoothstep(math.cos(math.radians(0.75)), math.cos(math.radians(0.6)), cs)
    sky = g.mix(1.0, sky, g.comb(g.mul(disc, 60.0), g.mul(disc, 34.0), g.mul(disc, 14.0)), blend='ADD', clamp=False)
    # nuvole a strisce su un piano alto, accese da sotto verso il sole
    inv = g.div(1.0, g.add(dz, 0.06))
    p = g.comb(g.mul(dx, inv), g.mul(g.mul(dy, inv), 3.5), 0.0)
    n1 = g.noise(p, scale=0.35, detail=6.0, rough=0.55, distortion=0.4)
    dens = g.mul(g.smoothstep(0.52, 0.70, n1.fac), g.smoothstep(0.02, 0.15, dz))
    dens = g.mul(dens, 0.85)
    lit = g.add(0.35, g.mul(toward, 1.6))
    cloud = g.comb(g.mul(lit, 0.42), g.mul(lit, 0.20), g.mul(lit, 0.18))
    sky = g.mix(dens, sky, cloud, clamp=False)
    # sotto l'orizzonte (si vede solo nei riflessi lontani): come l'orizzonte
    below = g.smoothstep(0.0, -0.02, dz)
    sky = g.mix(below, sky, horizon, clamp=False)
    g.output_world(g.background(sky, 1.0))
    w.cycles.sampling_method = 'MANUAL'
    w.cycles.sample_map_resolution = 1024
    w.mist_settings.start = 15.0
    w.mist_settings.depth = 900.0
    w.mist_settings.falloff = 'QUADRATIC'
    sun = bpy.data.lights.new('DawnSun', 'SUN')
    sun.energy = 2.6
    sun.color = (1.0, 0.62, 0.38)
    sun.angle = math.radians(1.2)
    ob = bpy.data.objects.new('DawnSun', sun)
    collection(COL).objects.link(ob)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = (-SUN_DIR).to_track_quat('-Z', 'Y')
    set_lightgroup(ob, 'ambient')
    return w


# ───────────────────────── le impronte ─────────────────────────

class Stamp:
    """Disegna sulla maschera (1 = bagnato) in coordinate del molo: x di traverso, y lungo il molo (metri)."""

    def __init__(self):
        self.x0 = PIER_X - PIER_W / 2
        self.y0 = Y_OUT
        self.W = int(round(PIER_W / TEX_RES))
        self.H = int(round((Y_LAND - Y_OUT) / TEX_RES))
        self.im = Image.new('L', (self.W, self.H), 0)
        self.d = ImageDraw.Draw(self.im)

    def px(self, x, y):
        return ((x - self.x0) / TEX_RES, (y - self.y0) / TEX_RES)

    @staticmethod
    def frame(pos, heading):
        """heading: direzione di marcia in radianti (0 = verso +Y). Locale: x a destra, y avanti."""
        c, s = math.cos(heading), math.sin(heading)

        def f(lx, ly):
            lx, ly = lx * PRINT_SCALE, ly * PRINT_SCALE
            return (pos[0] + lx * c + ly * s, pos[1] - lx * s + ly * c)
        return f

    def poly(self, f, pts, v=255):
        self.d.polygon([self.px(*f(x, y)) for x, y in pts], fill=v)

    def ellipse(self, f, cx, cy, rx, ry, rot=0.0, v=255, n=22):
        c, s = math.cos(rot), math.sin(rot)
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            x, y = rx * math.cos(a), ry * math.sin(a)
            pts.append((cx + x * c - y * s, cy + x * s + y * c))
        self.poly(f, pts, v)

    def line(self, f, pts, width, v=255):
        q = [self.px(*f(x, y)) for x, y in pts]
        w = max(1, int(round(width * PRINT_SCALE / TEX_RES)))
        self.d.line(q, fill=v, width=w, joint='curve')
        r = w / 2
        for x, y in (q[0], q[-1]):
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=v)

    def drips(self, rng, pos, n, spread, rmax=0.006):
        for _ in range(n):
            x, y = pos[0] + rng.normal(0, spread), pos[1] + rng.normal(0, spread)
            r = rng.uniform(0.002, rmax)
            self.ellipse(lambda a, b: (a, b), x, y, r, r * rng.uniform(0.7, 1.0), v=int(rng.uniform(150, 255)), n=10)


# le sagome delle impronte (metri, piede che va verso +y; side = −1 sinistro, +1 destro)

def print_gulpy(st, f, side, rng):
    """Palmata, come quella di una papera o di una rana: un triangolo pieno che dal tallone tondo si allarga fino al
    bordo davanti a festoni, con tre dita corte e larghe e le unghiette in punta."""
    sk = side * 0.004
    tips = [(-0.056 + sk, 0.092), (0.0 + sk, 0.108), (0.056 + sk, 0.092)]
    # il contorno: il tallone (mezzo cerchio dietro), i fianchi che si allargano, il bordo davanti a festoni
    pts = [(0.019 * math.cos(a), 0.019 * math.sin(a)) for a in np.linspace(0.0, -math.pi, 12)]
    pts += [(-0.030, 0.035), tips[0], (-0.028 + sk, 0.080), tips[1], (0.028 + sk, 0.080), tips[2], (0.030, 0.035)]
    st.poly(f, pts)
    for tx, ty in tips:
        st.line(f, [(0.0, 0.02), (tx * 0.9, ty * 0.95)], 0.016)
        st.ellipse(f, tx * 1.04, ty + 0.008, 0.004, 0.006, rot=-math.atan2(tx, ty))


def print_molly(st, f, side, rng):
    """Piedino da bambina: la pianta piena (tallone, la vita appena stretta dalla parte di dentro, la pianta larga) e i
    cinque ditini attaccati, l'alluce dalla parte di dentro."""
    edge_in, edge_out = [], []
    for t in np.linspace(0.0, 1.0, 24):
        y = -0.020 + 0.092 * t
        w = 0.017 + 0.011 * (t * t * (3 - 2 * t))
        pinch = 0.004 * math.exp(-((t - 0.45) / 0.16) ** 2)
        edge_out.append((side * w, y))
        edge_in.append((-side * (w - pinch), y))
    heel = [(0.017 * math.cos(a), -0.020 + 0.017 * math.sin(a)) for a in np.linspace(-math.pi, 0.0, 10)]
    if side > 0:
        heel = heel[::-1]
    st.poly(f, edge_in + [(0.0, 0.080)] + edge_out[::-1] + heel)
    st.ellipse(f, -side * 0.002, 0.072, 0.028, 0.015)
    for k in range(5):
        u = k / 4.0
        x = -side * (0.024 - 0.052 * u)
        y = 0.105 - 0.013 * u * u
        r = 0.0062 - 0.0020 * u
        st.ellipse(f, x, y, r, r * 1.15)


def print_hatch(st, f, side, rng):
    """Scarpetta da bambino: la suola con la vita stretta e il battistrada a righe di traverso."""
    pts = []
    for i in range(40):
        t = i / 39.0
        y = -0.012 + 0.15 * t
        w = 0.022 + 0.012 * math.sin(math.pi * min(1.0, t * 1.15)) - 0.007 * math.exp(-((t - 0.45) / 0.14) ** 2)
        pts.append((side * 0.004 * t + w, y))
    back = [(side * 0.004 * (i / 39.0) - (0.022 + 0.012 * math.sin(math.pi * min(1.0, i / 39.0 * 1.15))
             - 0.004 * math.exp(-((i / 39.0 - 0.45) / 0.14) ** 2)), -0.012 + 0.15 * i / 39.0) for i in range(39, -1, -1)]
    st.poly(f, pts + back)
    for k in range(13):
        y = 0.0 + k * 0.0105
        if 0.055 < y < 0.075:
            continue
        st.line(f, [(-0.04, y), (0.04, y)], 0.0035, v=60)


def print_robin(st, f, side, rng):
    """Zampette: un ventaglio di puntini per parte (i raggi liberi della gallinella)."""
    for k in range(4):
        a = side * (0.25 + 0.22 * k)
        r = 0.05 + 0.012 * rng.standard_normal()
        x, y = r * math.sin(a), r * math.cos(a) - 0.02
        st.ellipse(f, x, y, 0.0055, 0.008, rot=-a)


def print_lampy(st, f, side, rng):
    """L'anello della ventosa, con le tacche dei denti da latte dentro."""
    st.ellipse(f, 0.0, 0.0, 0.058, 0.055, n=40)
    st.ellipse(f, 0.0, 0.0, 0.041, 0.039, v=30, n=40)
    for ring, (r, n) in enumerate(((0.034, 16), (0.022, 10))):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * ring) / n
            st.ellipse(f, r * math.cos(a), r * math.sin(a), 0.0028, 0.0045, rot=a, v=220, n=8)
    st.ellipse(f, 0.0, 0.0, 0.009, 0.009, v=200)


def print_fangy(st, f, side, rng):
    """Artigli sottili: quattro graffi lunghi e storti che finiscono a punta, le nocche come macchie piccole."""
    for k in range(4):
        x0 = side * 0.004 + (k - 1.5) * 0.017
        bend = side * 0.012 + rng.normal(0, 0.003)
        pts = [(x0 + bend * (t ** 2) + (k - 1.5) * 0.010 * t, 0.03 + 0.12 * t) for t in np.linspace(0, 1, 8)]
        for i in range(len(pts) - 1):
            w = 0.0045 * (1 - i / (len(pts) - 1)) + 0.001
            st.line(f, [pts[i], pts[i + 1]], w)
        st.ellipse(f, x0, 0.012, 0.009, 0.012)


# (impronta, passo in metri, scarto di lato, mezza larghezza della corsia, seme)
TRAILS = {
    'gulpy': (print_gulpy, 0.34, 0.075, 0.09),
    'molly': (print_molly, 0.26, 0.055, 0.07),
    'hatch': (print_hatch, 0.62, 0.045, 0.06),
    'robin': (print_robin, 0.11, 0.035, 0.06),
    'lampy': (print_lampy, 0.48, 0.0, 0.05),
    'fangy': (print_fangy, 0.50, 0.08, 0.09),
    'archie': (None, 0.0, 0.0, 0.08),
}
# le corsie, da sinistra a destra guardando verso il paese; da dove sono saliti in fondo al molo
LANES = [('molly', -0.92, (-1.18, Y_OUT + 1.4)), ('gulpy', -0.60, (-0.55, Y_OUT + 0.02)),
         ('archie', -0.26, (-0.05, Y_OUT + 0.02)), ('lampy', 0.06, (0.45, Y_OUT + 0.02)),
         ('robin', 0.36, (1.18, Y_OUT + 0.8)), ('fangy', 0.66, (1.18, Y_OUT + 2.4)), ('hatch', 0.95, (1.18, Y_OUT + 3.6))]
STAIR_X = PIER_X + 1.0                 # dove convergono, in cima al molo (la scala del paese sta a destra)


def lane_path(lane_x, start, seed):
    """Polilinea del cammino di una corsia: sale dal bordo, prende la corsia serpeggiando, in cima converge."""
    r = np.random.default_rng(seed)
    ys = np.arange(start[1], Y_LAND - 0.3, 0.02)
    ph1, ph2 = r.uniform(0, 6.3, 2)
    xs = []
    for y in ys:
        t_in = np.clip((y - start[1]) / 2.6, 0, 1)
        t_in = t_in * t_in * (3 - 2 * t_in)
        wander = 0.07 * math.sin(y * 0.45 + ph1) + 0.035 * math.sin(y * 1.3 + ph2)
        x = PIER_X + lane_x + wander
        t_out = np.clip((y - (Y_LAND - 5.0)) / 4.8, 0, 1)
        t_out = t_out * t_out * (3 - 2 * t_out)
        x = x * (1 - 0.7 * t_out) + (STAIR_X + lane_x * 0.3) * 0.7 * t_out
        xs.append(start[0] + PIER_X + (x - start[0] - PIER_X) * t_in)
    return np.stack([xs, ys], axis=1)


def walk(path, step):
    """Punti a distanza 'step' lungo la polilinea, con la direzione."""
    seg = np.diff(path, axis=0)
    L = np.concatenate([[0.0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])
    out = []
    for s in np.arange(0.15, L[-1], step):
        i = min(np.searchsorted(L, s) - 1, len(seg) - 1)
        t = (s - L[i]) / max(L[i + 1] - L[i], 1e-9)
        p = path[i] + seg[i] * t
        out.append((p, math.atan2(seg[i][0], seg[i][1])))
    return out


def footprints_texture():
    """La maschera delle sette file (bianco = bagnato). Restituisce il percorso del png."""
    os.makedirs(TEX, exist_ok=True)
    path = os.path.join(TEX, 'molo_impronte.png')
    st = Stamp()
    rng = np.random.default_rng(1997)
    ident = lambda a, b: (a, b)  # noqa: E731
    for k, (who, lane_x, start) in enumerate(LANES):
        fn, step, side_off, _ = TRAILS[who]
        pth = lane_path(lane_x, start, 31 + k)
        # le gocce dove sono saliti dall'acqua
        st.drips(rng, (start[0] + PIER_X, start[1] + 0.2), 40, 0.12)
        if who == 'archie':
            # la scia: un nastro che serpeggia, più largo e più sottile a tratti
            ys = pth[:, 1]
            xs = pth[:, 0] + 0.07 * np.sin(ys * 2 * math.pi / 0.7)
            pts = np.stack([xs, ys], axis=1)
            for i in range(0, len(pts) - 1):
                w = 0.035 + 0.018 * math.sin(ys[i] * 1.7) + 0.008 * math.sin(ys[i] * 9.0)
                st.line(ident, [tuple(pts[i]), tuple(pts[i + 1])], w, v=235)
            for i in range(0, len(pts), 40):
                st.drips(rng, tuple(pts[i]), 3, 0.05, 0.004)
            continue
        for j, (p, h) in enumerate(walk(pth, step)):
            side = -1 if j % 2 == 0 else 1
            if who == 'lampy':
                side = 1
            off = side * side_off
            q = (p[0] + off * math.cos(h), p[1] - off * math.sin(h))
            f = Stamp.frame(q, h + rng.normal(0, 0.06) + side * 0.06)
            fn(st, f, side, rng)
            if who == 'robin':
                # la coda che striscia in mezzo, a tratti
                f0 = Stamp.frame((p[0], p[1]), h)
                if j % 3 != 2:
                    st.line(f0, [(0.0, -0.05), (0.004 * math.sin(j), 0.06)], 0.010, v=170)
            if rng.random() < 0.35:
                st.drips(rng, q, 4, 0.05, 0.004)
    im = st.im.filter(ImageFilter.GaussianBlur(1.6))
    # l'acqua non bagna uguale dappertutto: un po' di variazione e i bordi che asciugano
    a = np.asarray(im).astype(np.float32) / 255.0
    n = np.random.default_rng(5).random((a.shape[0] // 24 + 2, a.shape[1] // 24 + 2))
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((a.shape[1], a.shape[0]), Image.BILINEAR)) / 255.0
    a = np.clip(a * (1.05 + 0.3 * n), 0, 1)
    # la riga 0 dell'immagine è in alto, la v delle texture parte dal basso: in basso c'è il fondo del molo
    Image.fromarray((np.flipud(a) * 255 + 0.5).astype(np.uint8)).save(path)
    return path


def deck_material(mask_path):
    """Assi vecchie e grigie, umide di rugiada; dove sono passati è bagnato fradicio: scuro e lucido."""
    m, g = material('PierDeck')
    pos = g.geometry('Position')
    x, y, z = g.sep(pos)
    u = g.div(g.sub(x, PIER_X - PIER_W / 2), PIER_W)
    v = g.div(g.sub(y, Y_OUT), Y_LAND - Y_OUT)
    col_m, _ = g.image(mask_path, g.comb(u, v, 0.0), extension='CLIP', colorspace='Non-Color')
    wet = g.bw(col_m)
    plank = g.math('FLOOR', g.div(y, 0.21))
    pr = g.noise(g.comb(plank, 0.0, 0.0), scale=3.7, detail=0.0).fac
    grain = g.noise(g.comb(g.mul(x, 0.6), g.mul(y, 26.0), plank), scale=3.0, detail=6.0, rough=0.6).fac
    base = g.ramp(g.add(g.mul(pr, 0.6), g.mul(grain, 0.5)),
                  [(0.25, (0.20, 0.185, 0.165)), (0.55, (0.31, 0.29, 0.265)), (0.85, (0.40, 0.38, 0.35))])
    moss = g.smoothstep(0.62, 0.78, g.noise(pos, scale=1.4, detail=5.0).fac)
    base = g.mix(g.mul(moss, 0.5), base, (0.05, 0.07, 0.035))
    # bagnato fradicio: il legno diventa quasi nero e lucido, e riflette come l'acqua (meno della vernice)
    col = g.mix(wet, base, g.mix(1.0, base, (0.07, 0.065, 0.065), blend='MULTIPLY'))
    rough = g.mixf(wet, g.add(0.6, g.mul(grain, 0.2)), 0.05)
    nrm = g.bump(grain, strength=g.mixf(wet, 0.35, 0.08), distance=0.002)
    g.output_material(g.principled(color=col, rough=rough, normal=nrm, spec=g.mixf(wet, 0.5, 0.28)))
    return m


def build_pier():
    """Il molo di legno: assi di traverso con le fessure, travi, pali incrostati, bitte, la scaletta in fondo, la
    banchina di pietra sotto la scogliera e la scala che sale al paese."""
    import deco
    obs = []
    planks = []
    y = Y_OUT
    r = np.random.default_rng(3)
    while y < Y_LAND - 0.1:
        w = 0.20 + r.uniform(-0.01, 0.01)
        planks.append(((PIER_X + r.normal(0, 0.01), y + w / 2, DECK_Z - 0.025 + r.normal(0, 0.004)),
                       (PIER_W + r.uniform(-0.03, 0.05), w - 0.014, 0.05), r.normal(0, 0.004)))
        y += w
    obs.append(boxes_mesh('PierDeck', planks, deck_material(footprints_texture())))
    timber = _mat('PierTimber', (0.07, 0.06, 0.05), rough=0.8)
    beams = [((PIER_X + s * 0.85, (Y_OUT + Y_LAND) / 2, DECK_Z - 0.13), (0.16, Y_LAND - Y_OUT, 0.2), 0.0) for s in (-1, 1)]
    beams += [((PIER_X, yy, DECK_Z - 0.32), (PIER_W + 0.1, 0.18, 0.22), 0.0) for yy in np.arange(Y_OUT + 0.2, Y_LAND, 3.0)]
    beams += [((PIER_X + s * (PIER_W / 2 + 0.05), (Y_OUT + Y_LAND) / 2, DECK_Z - 0.02), (0.1, Y_LAND - Y_OUT, 0.16), 0.0) for s in (-1, 1)]
    obs.append(boxes_mesh('PierBeams', beams, timber))
    # pali: legno scuro, bagnato e incrostato fino alla linea di marea
    m, g = material('PierPile')
    pos = g.geometry('Position')
    _, _, z = g.sep(pos)
    n = g.noise(pos, scale=9.0, detail=6.0).fac
    tide = g.smoothstep(0.55, 0.25, z)
    col = g.mix(tide, g.mix(n, (0.09, 0.075, 0.06), (0.15, 0.13, 0.11)), g.mix(n, (0.03, 0.04, 0.03), (0.10, 0.12, 0.08)))
    g.output_material(g.principled(color=col, rough=g.mixf(tide, 0.8, 0.3),
                                   normal=g.bump(n, strength=0.6, distance=0.02)))
    for yy in np.arange(Y_OUT + 0.2, Y_LAND, 3.0):
        for s in (-1, 1):
            o = cylinder('PierPile', 0.13, DECK_Z + 3.0, (PIER_X + s * 1.05, yy, (DECK_Z - 3.0) / 2 + 0.05), verts=14, col=COL)
            o.data.materials.append(m)
            obs.append(o)
    # bitte di ghisa e le cime della barca (a prua e a poppa)
    iron = _mat('BollardIron', (0.03, 0.03, 0.032), rough=0.45, metal=0.6)
    rope = _mat('MooringRope', (0.33, 0.29, 0.21), rough=0.9)
    bitts = [(PIER_X - 0.85, -4.4), (PIER_X - 0.85, 4.6), (PIER_X + 0.85, -10.0), (PIER_X + 0.85, 7.4)]
    for bx, by in bitts:
        o = cylinder('Bollard', 0.09, 0.32, (bx, by, DECK_Z + 0.16), verts=16, col=COL)
        o.data.materials.append(iron)
        t = cylinder('BollardTop', 0.12, 0.05, (bx, by, DECK_Z + 0.33), verts=16, col=COL)
        t.data.materials.append(iron)
        obs += [o, t]
    for (bx, by), (ex, ey, ez) in (((bitts[0]), (0.25, -2.55, 0.95)), ((bitts[1]), (0.18, 2.75, 1.0))):
        a = Vector((ex, ey, ez))
        b = Vector((bx, by, DECK_Z + 0.24))
        pts = []
        for t in np.linspace(0, 1, 16):
            p = a.lerp(b, t)
            p.z -= 0.35 * 4 * t * (1 - t)
            pts.append(tuple(p))
        o = tube('MooringLine', pts, 0.014, n=8, col=COL)
        o.data.materials.append(rope)
        obs.append(o)
        coil = [(bx + 0.13 * math.cos(k * 0.6), by + 0.13 * math.sin(k * 0.6), DECK_Z + 0.02 + 0.012 * k / 6) for k in range(24)]
        o = tube('RopeCoil', coil, 0.013, n=6, col=COL)
        o.data.materials.append(rope)
        obs.append(o)
    # parabordi tra il gozzo e il molo
    fender = _mat('Fender', (0.30, 0.05, 0.04), rough=0.5)
    for fy in (-1.2, 1.4):
        o = sphere('Fender', 0.11, (PIER_X - PIER_W / 2 - 0.08, fy, 0.72), segs=16, rings=10, col=COL, scale=(1, 1, 1.8))
        o.data.materials.append(fender)
        obs.append(o)
    # la scaletta di ferro in fondo al molo (da lì sono saliti)
    rust = _mat('LadderRust', (0.16, 0.07, 0.04), rough=0.6, metal=0.3)
    for s in (-1, 1):
        o = tube('LadderRail', [(PIER_X + s * 0.25, Y_OUT - 0.08, -1.2), (PIER_X + s * 0.25, Y_OUT - 0.08, DECK_Z + 0.6),
                                (PIER_X + s * 0.25, Y_OUT + 0.25, DECK_Z + 0.75), (PIER_X + s * 0.25, Y_OUT + 0.4, DECK_Z)],
                 0.02, n=8, col=COL)
        o.data.materials.append(rust)
        obs.append(o)
    for zz in np.arange(-0.9, DECK_Z, 0.3):
        o = tube('LadderRung', [(PIER_X - 0.25, Y_OUT - 0.08, zz), (PIER_X + 0.25, Y_OUT - 0.08, zz)], 0.016, n=6, col=COL)
        o.data.materials.append(rust)
        obs.append(o)
    # la banchina di pietra sotto la scogliera e la scala che sale al paese, lungo la parete
    stone = deco.deco_paint('QuayStone', (0.36, 0.33, 0.29), grime=0.6)
    q = rbox('Quay', (26.0, 7.0, 4.4), (PIER_X + 3.0, Y_LAND + 2.6, DECK_Z + 0.05 - 2.2), bevel=0.06, col=COL)
    q.data.materials.append(stone)
    obs.append(q)
    ch = float(env.cliff_height(np.array([PIER_YAW]))[0])
    steps = []
    for k in range(70):
        zt = DECK_Z + 0.1 + 0.24 * (k + 1)
        s_wall = -16.0 * math.log(max(1e-3, 1 - zt / ch))
        yf = Y_SHORE + s_wall - 1.4
        xk = PIER_X + 4.0 + 0.33 * k
        h = min(zt, 5.0)
        steps.append(((xk, yf + 3.0, zt - h / 2), (0.36, 6.0, h), 0.0))
    st_ob = boxes_mesh('VillageStair', steps, stone)
    obs.append(st_ob)
    lampm = deco.neon_material('QuayLamp', (1.0, 0.6, 0.25), 18.0)
    for k, (lx, ly) in enumerate(((PIER_X - 0.9, Y_LAND + 0.5), (PIER_X + 9.0, Y_LAND + 0.6))):
        o = tube('QuayLampPost', [(lx, ly, DECK_Z + 0.1), (lx, ly, DECK_Z + 3.6), (lx + 0.3, ly, DECK_Z + 3.8)], 0.05, n=8, col=COL)
        o.data.materials.append(iron)
        bulb = sphere('QuayLampBulb', 0.12, (lx + 0.35, ly, DECK_Z + 3.65), segs=12, rings=8, col=COL)
        bulb.data.materials.append(lampm)
        obs += [o, bulb]
    return _amb(obs)


def scena_molo():
    reset_scene()
    collection(COL)
    dawn_sky()
    env.build_sea()
    before = set(bpy.data.objects.keys())
    env.build_coast()
    env.build_village()
    env.build_lighthouse()
    env.build_stacks()
    import landmarks
    landmarks.build_landmarks()
    place_world([bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before])
    # all'alba la campana non è più accesa
    bl = bpy.data.objects.get('BelfryLamp')
    if bl:
        bl.data.energy *= 0.15
    import boat
    parts, _ = boat.build_boat(fish_in_bucket=0, rod=True)
    for o in parts['player']:
        bpy.data.objects.remove(o)
    build_pier()
    # dalla testa del molo verso il largo: le impronte vengono dalla scaletta in fondo e passano sotto la camera,
    # verso il paese che sta alle spalle; il sole basso fa brillare le assi bagnate
    cam = perspective_camera((PIER_X + 0.3, Y_LAND - 1.6, DECK_Z + 1.45), (PIER_X - 0.9, Y_LAND - 24.0, DECK_Z - 3.2),
                             lens=20.0, name='MoloCam')
    cam.data.dof.use_dof = False
    return {'ev': 0.2, 'haze': (0.30, 0.22, 0.24), 'haze_amt': 0.3, 'groups': ('ambient',)}


# ═════════════════════════ l'edicola da vicino ═════════════════════════

def polaroid_scene_image(path):
    """La foto: la barca di notte vista dal pelo dell'acqua, a sinistra di poppa, la lampara accesa e il pescatore
    seduto in controluce. È la scena del gioco (jobs.build_scene), col pescatore reso visibile come sagoma."""
    import jobs
    jobs.build_scene(fish=3, rod=True)
    dark = _mat('FisherDark', (0.005, 0.005, 0.005), rough=0.9)
    for name in ('PTorso', 'PHead', 'PThighL', 'PThighR', 'PShinL', 'PShinR', 'PArmL', 'PArmR'):
        o = bpy.data.objects.get(name)
        if o:
            set_visibility(o, camera=True)
            o.data.materials.clear()
            o.data.materials.append(dark)
    ex, ey, ez = EYE
    cap = cylinder('FisherCap', 0.115, 0.07, (0.0, ey - 0.02, ez + 0.12), verts=20, col='boat')
    brim = cylinder('FisherBrim', 0.17, 0.012, (0.0, ey + 0.02, ez + 0.085), verts=20, col='boat')
    for o in (cap, brim):
        o.data.materials.append(dark)
        set_lightgroup(o, 'ambient')
    perspective_camera((-5.6, -3.2, 0.08), (0.0, 0.5, 1.45), lens=40.0, name='PolaroidCam', roll=math.radians(-6))
    exr = os.path.join(TEX, 'polaroid.exr')
    S = 512 if (FAST or not FINALE) else 900
    render(exr, 24 if not FINALE else 96, (S, S), data_passes=())
    p = post.read_exr(exr)
    lin = sum(post.rgb(p[k]) for k in ('ambient', 'lamp', 'lantern') if k in p)
    img = post.tonemap(lin, exposure_ev=2.3)
    # Polaroid: neri slavati verdastri, alte luci calde, colori stanchi, morbida, grana e vignetta
    l = (img * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
    img = l + (img - l) * 0.8
    img = 0.07 + img * 0.88
    img = img * np.array([1.04, 1.0, 0.9]) + np.array([-0.012, 0.012, 0.018]) * (1 - l)
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    rr = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    img = img * (1 - 0.35 * np.clip(rr - 0.45, 0, 1) ** 1.5)[..., None]
    rng = np.random.default_rng(6)
    img = img + rng.normal(0, 0.025, img.shape) * (1 - l * 0.6)
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
    # il cartoncino: 88×107 mm, la foto quadrata 79×79 mm, il bordo largo in basso
    k = 10
    card = Image.new('RGB', (88 * k, 107 * k), (238, 236, 228))
    card.paste(im.resize((79 * k, 79 * k), Image.LANCZOS), (int(4.5 * k), 6 * k))
    a = np.asarray(card).astype(np.float32)
    n = np.random.default_rng(8).random((a.shape[0] // 8 + 1, a.shape[1] // 8 + 1))
    n = np.kron(n, np.ones((8, 8)))[:a.shape[0], :a.shape[1]]
    a *= 0.97 + 0.03 * n[..., None]
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(path)
    return path


def polaroid_material(path):
    m, g = material('PolaroidNew')
    col, _ = g.image(path, g.texcoord('UV'), extension='CLIP')
    _, v, _ = g.sep(g.texcoord('UV'))
    u, _, _ = g.sep(g.texcoord('UV'))
    in_photo = g.mul(g.mul(g.smoothstep(0.045, 0.055, u), g.smoothstep(0.955, 0.945, u)),
                     g.mul(g.smoothstep(0.205, 0.215, v), g.smoothstep(0.946, 0.936, v)))
    g.output_material(g.principled(color=col, rough=g.mixf(in_photo, 0.7, 0.18), coat=g.mul(in_photo, 0.6), coat_rough=0.08))
    return m


def scena_edicola():
    os.makedirs(TEX, exist_ok=True)
    pol_path = os.path.join(TEX, 'polaroid.png')
    # FINALI_RIUSA_FOTO=1: la Polaroid già fatta (per provare luce e inquadratura dell'edicola)
    if not (os.environ.get('FINALI_RIUSA_FOTO') and os.path.exists(pol_path)):
        polaroid_scene_image(pol_path)
    import binocolo
    import jobs
    from landmarks import painted
    jobs.build_scene(fish=0, rod=False)
    # le foto di binocolo.photo_texture hanno le macchie a quadretti da 10 px: da lontano non si vedono, da vicino sì.
    # Qui si ingrandiscono e si ammorbidiscono
    orig = binocolo.photo_texture

    def smooth_photo(seed, style='print'):
        p = orig(seed, style)
        im = Image.open(p)
        im = im.resize((im.width * 3, im.height * 3), Image.BICUBIC).filter(ImageFilter.GaussianBlur(9))
        q = p.replace('.png', '_vicino.png')
        im.save(q)
        return q
    binocolo.photo_texture = smooth_photo
    binocolo.lore_photos()
    binocolo.photo_texture = orig
    # il mattino grigio al posto della notte: niente luna, cielo coperto
    for n in ('Moon',):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o)
    w, g = world('GreyMorning')
    w.lightgroup = 'ambient'
    d = g.texcoord('Generated')
    _, _, dz = g.sep(d)
    up = g.clamp01(dz)
    n = g.noise(d, scale=6.0, detail=5.0, rough=0.6).fac
    sky = g.mix(g.pow(up, 0.5), (1.6, 1.65, 1.75), (1.05, 1.12, 1.28))
    sky = g.mix(g.mul(g.smoothstep(0.4, 0.75, n), 0.25), sky, (1.8, 1.8, 1.82))
    sky = g.mix(g.smoothstep(0.0, -0.05, dz), sky, (0.30, 0.33, 0.36))
    g.output_world(g.background(sky, 1.0))
    w.mist_settings.start = 30.0
    w.mist_settings.depth = 600.0
    w.mist_settings.falloff = 'QUADRATIC'
    soft = bpy.data.lights.new('OvercastSun', 'SUN')
    soft.energy = 1.2
    soft.color = (0.85, 0.88, 0.95)
    soft.angle = math.radians(40)
    so = bpy.data.objects.new('OvercastSun', soft)
    collection(COL).objects.link(so)
    so.rotation_mode = 'QUATERNION'
    so.rotation_quaternion = Vector((0.2, 0.9, -0.5)).normalized().to_track_quat('-Z', 'Y')
    set_lightgroup(so, 'ambient')
    # i lumini sono quasi consumati: la fiamma resta, la luce conta poco contro il mattino
    for o in bpy.data.objects:
        if o.name.startswith('ChapelCandle'):
            o.data.energy *= 0.03
    vm = bpy.data.materials.get('VotiveRed')
    if vm:
        for nd in vm.node_tree.nodes:
            if nd.type == 'EMISSION':
                nd.inputs['Strength'].default_value = 0.7
    # l'edicola: lo scoglio spunta dentro il pavimento (da lontano non si vede): da vicino si spiana
    (x, y), rz = binocolo._chapel()
    base_z = 3.6
    rock = bpy.data.objects['ChapelRock']
    bpy.context.view_layer.update()
    Mi = rock.matrix_world.inverted()
    M = rock.matrix_world
    for v in rock.data.vertices:
        wv = M @ v.co
        if wv.z > base_z - 0.05 and math.hypot(wv.x - x, wv.y - y) < 4.5:
            wv.z = base_z - 0.05
            v.co = Mi @ wv

    def lp(lx, ly, lz):
        return Vector((x + lx * math.cos(rz) - ly * math.sin(rz), y + lx * math.sin(rz) + ly * math.cos(rz), base_z + lz))
    floor = rbox('ChapelFloor', (4.6, 3.6, 0.2), tuple(lp(0, -0.3, -0.1)), rot=(0, 0, rz), bevel=0.03, col=COL)
    floor.data.materials.append(painted('ChapelFloorStone', (0.32, 0.30, 0.27), rust=0.0, rough=0.85))
    set_lightgroup(floor, 'ambient')
    # la Polaroid nuova, appesa con una molletta a uno spago teso fra le due pareti, davanti all'edicola: le foto
    # vecchie restano più di un metro dietro, sfocate
    right0 = Vector((math.cos(rz), math.sin(rz), 0.0))
    front0 = Vector((math.sin(rz), -math.cos(rz), 0.0))       # verso il mare, dove sta chi guarda
    zz = Vector((0.0, 0.0, 1.0))
    ly_s, lz_s = -1.05, 1.58
    pts = []
    for t in np.linspace(0, 1, 25):
        lx = -2.02 + 4.04 * t
        pts.append(tuple(lp(lx, ly_s, lz_s - 0.05 * 4 * t * (1 - t))))
    string = tube('OfferingString', pts, 0.0011, n=6, col=COL)
    string.data.materials.append(_mat('StringMat', (0.42, 0.36, 0.28), rough=0.85))
    lx_p = 0.22
    sag = 0.05 * 4 * ((lx_p + 2.02) / 4.04) * (1 - (lx_p + 2.02) / 4.04)
    hook = lp(lx_p, ly_s, lz_s - sag)
    yaw, roll = math.radians(9), math.radians(-4)
    r1 = right0 * math.cos(yaw) + front0 * math.sin(yaw)
    r2 = r1 * math.cos(roll) + zz * math.sin(roll)
    u2 = zz * math.cos(roll) - r1 * math.sin(roll)
    n2 = r2.cross(u2)
    pw, ph = 0.088, 0.107
    centre = hook - u2 * (ph / 2 + 0.012)
    binocolo.quad('PolaroidNew', tuple(centre), tuple(r2), tuple(u2), pw, ph, polaroid_material(pol_path), segs=6)
    # la molletta di legno che stringe il bordo alto, con la molla di ferro
    wood = _mat('ClothespinWood', (0.55, 0.42, 0.26), rough=0.7)
    for k, side in enumerate((-1, 1)):
        c = hook + u2 * 0.006 + n2 * side * 0.0035
        pin = rbox('Clothespin', (0.010, 0.0045, 0.072), tuple(c), bevel=0.0015, col=COL)
        pin.rotation_mode = 'QUATERNION'
        pin.rotation_quaternion = Matrix((tuple(r2), tuple(n2), tuple(u2))).transposed().to_quaternion()
        pin.data.materials.append(wood)
    spring = cylinder('ClothespinSpring', 0.0045, 0.012, tuple(hook + u2 * 0.012), verts=12, col=COL)
    spring.rotation_mode = 'QUATERNION'
    spring.rotation_quaternion = n2.to_track_quat('Z', 'Y')
    spring.data.materials.append(_mat('SpringSteel', (0.5, 0.5, 0.52), rough=0.35, metal=1.0))
    for o in bpy.data.objects:
        if o.name.startswith(('OfferingString', 'Clothespin', 'PolaroidNew')):
            set_lightgroup(o, 'ambient')
    # la camera: un medio tele a un metro e un quarto, poca profondità di campo; la Polaroid è un quarto del quadro
    eye = centre + front0 * 1.25 + right0 * 0.14 + zz * 0.05
    target = centre - right0 * 0.07 + zz * 0.005
    cam = perspective_camera(tuple(eye), tuple(target), lens=60.0, name='EdicolaCam')
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (centre - eye).length
    cam.data.dof.aperture_fstop = 1.4
    return {'ev': 0.0, 'haze': (0.62, 0.64, 0.68), 'haze_amt': 0.5, 'groups': ('ambient',)}


# ═════════════════════════ render ═════════════════════════

SCENES = {'molo': scena_molo, 'edicola': scena_edicola}


def run(key):
    t = time.time()
    info = SCENES[key]()
    if FINALE:
        W, H, samples = 2560, 1440, 256
    else:
        W, H, samples = (960, 540, 12) if FAST else (1600, 900, 24)
    out_dir = os.path.join(CACHE, 'final' if FINALE else 'preview', 'finali')
    exr = os.path.join(out_dir, f'{key}.exr')
    render(exr, samples, (W, H), data_passes=('Mist',))
    p = post.read_exr(exr)
    lin = sum(post.rgb(p[g]) for g in info['groups'] if g in p)
    # la foschia del mattino sulle cose lontane
    if 'mist' in p:
        f = np.clip(p['mist'], 0, 1)[..., None] * info['haze_amt']
        lin = lin * (1 - f) + np.array(info['haze']) * f
    log(f'finale {key}', round(time.time() - t), 's')
    if FINALE:
        scale = post.pick_scale(lin)
        fn = f'fin_{key}.webp'
        post.save_webp(post.encode_light_pass(lin, scale), os.path.join(OUT_IMG, fn), quality=90)
        post.update_manifest(OVERLAYS, f'endings.{key}', {'file': fn, 'scale': scale, 'aspect': round(W / H, 4),
                                                          'exposure': info['ev']})
        return
    img = post.tonemap(lin, exposure_ev=info['ev'])
    out = os.path.join(ROOT, 'docs', 'concept', f'finali_{key}_anteprima.jpg')
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(out, quality=90)
    log('anteprima', out)


if __name__ == '__main__':
    keys = [a for a in sys.argv[1:] if not a.startswith('--')] or list(SCENES)
    for k in keys:
        run(k)
