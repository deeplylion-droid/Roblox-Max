"""
ROBIN — dettagli della testa (notte 2, sagoma A «Granchio»), da scegliere insieme.

Come per la prima notte (tools/render/dettagli.py, che qui si usa senza toccarlo): il corpo della sagoma
scelta e tre teste, da "più pesce" (A) a "più bambino" (C), con addosso la cosa del parco: la striscia
lunghissima di biglietti della sala giochi avvolta attorno alle braccia. Viene dalla gallinella (testa
corazzata, pettorali a ventaglio con i raggi liberi che usa come zampette sul fondo) e dal pesce gatto
(i barbigli). Da bambino nascondeva le cose degli altri sotto gli scivoli: ora, steso sul bordo della
barca come un ragno di mare, ruba i pesci dal secchio. Bozze di studio: non sono i modelli definitivi.

Colori (proposta da approvare, 10 ottobre): i mostri nuovi non sono più grigi come i primi tre, ognuno ha
un colore netto come in FNAF. Robin è rosso corallo come la gallinella vera (Chelidonichthys), più scuro e
più bagnato sul dorso, rosato sulla pancia; i ventagli e le zampette sono turchese elettrico a macchie blu;
la melma è tinta di rosso. Pelle, chiazze, vene e melma restano quelle di famiglia: cambia solo la tinta.

Coordinate come la sagoma: il bordo della barca corre lungo X a y = 0 (capodibanda a z = 0,75), dentro
la barca è y < 0, fuori c'è il mare (z = 0). La faccia guarda −Y, verso il secchio e il pescatore.

Uso: tools/.venv/bin/python tools/render/teste_robin.py [--fast] [--only A|B|C] [--tavola]
     (--tavola rimonta la tavola dai pannelli già renderizzati, senza rifarli)
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import boat  # noqa: E402
import dettagli as D  # noqa: E402
import sdf  # noqa: E402
import skin  # noqa: E402
from common import mesh_from_arrays, set_lightgroup  # noqa: E402
from creature import sdf_object  # noqa: E402
from geo import catmull, lathe, rbox, tube  # noqa: E402
from nodes import material  # noqa: E402

V, F, unit, chain = D.V, D.F, D.unit, D.chain
FAST = D.FAST
RES_BODY = 0.0045 if FAST else 0.003      # corpo, arti e testa: una mesh sola, valutata a fasce
RES_FINE = 0.0018 if FAST else 0.0012     # pezzi sottili (barbigli, spine, capelli)

GUN = 0.75                        # piano del capodibanda
BENCH = 0.40                      # piano del banco su cui sta il secchio
BUCKET = V(0.10, -0.84, BENCH)    # centro del fondo del secchio (il secchio zincato del gioco)
FISH = V(0.075, -0.855, 0.80)     # il pesce rubato, stretto nel pugno (centro della presa)
FISH_DIR = unit((-1.0, 0.0, 0.12))  # verso la testa del pesce
HEAD = V(0.0, -0.50, 0.90)        # centro della testa
CAM = V(-0.35, -1.70, 1.22)       # la macchina da presa: serve anche per far guardare gli occhi
HEAD_YAW, HEAD_PITCH = -15.0, -12.0   # la testa girata verso il pescatore: l'ha visto, ma non smette

# i testi sotto i pannelli della tavola (nome della variante e spiegazione)
TESTI = {
    'A': ('A · Corazza', 'più pesce: la testa corazzata della gallinella,\na placche e spine; i barbigli del pesce\ngatto pescano nel secchio'),
    'B': ('B · Baffi', 'a metà: testa larga e piatta da pesce gatto\ncon le orecchie di un bambino; i baffi\npendono fin dentro il secchio'),
    'C': ('C · Bambino', 'più bambino: ti guarda col dito sulle labbra,\n«zitto»; il sorriso da pesce gatto\nva oltre il dito, fino alle orecchie'),
}


# ───────────────────────── aiuti ─────────────────────────

def entro(f, lo, hi, margine=0.04):
    """Valuta il campo solo vicino alla sua scatola: fuori dà la distanza dalla scatola (stima per difetto).
    Così i pezzi piccoli non si calcolano su tutta la griglia."""
    lo, hi = V(*lo), V(*hi)

    def g(p):
        q = np.maximum(np.maximum(lo - p, p - hi), 0.0)
        d = np.linalg.norm(q, axis=1).astype(F)
        m = d < margine
        if m.any():
            d[m] = f(p[m])
        return d
    return g


def tubo(points, r0, r1, n=6, nodi=0.0):
    """Tubo morbido lungo una curva (catmull), dal raggio r0 al raggio r1; nodi > 0 gonfia le articolazioni
    sui punti di controllo interni (i raggi della gallinella sono a segmenti). Restituisce campo e punti."""
    pts = catmull([V(*p) for p in points], n)
    m = len(pts) - 1
    parts = [sdf.round_cone(pts[i], pts[i + 1], r0 + (r1 - r0) * i / m, r0 + (r1 - r0) * (i + 1) / m) for i in range(m)]
    if nodi > 0:
        for j in range(1, len(points) - 1):
            t = j / (len(points) - 1)
            parts.append(sdf.sphere(points[j], (r0 + (r1 - r0) * t) * (1.0 + nodi)))
    pad = max(r0, r1) * 1.6
    return entro(sdf.union(*parts, k=0.004), pts.min(0) - pad, pts.max(0) + pad), pts


def squash(f, c, s):
    """Campo schiacciato/stirato di (sx, sy, sz) attorno a c."""
    c, s = V(*c), V(*s)
    m = float(s.min())
    return lambda p: f((p - c) / s + c) * m


def placche(seed, centro, raggio, n, largo=0.0045):
    """Solchi tra le placche ossee (celle di Voronoi in 3D): 1 sul bordo tra due placche, 0 in mezzo."""
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(seed)
    pts = V(*centro) + (rng.random((n, 3)).astype(F) - 0.5) * 2 * V(*raggio)
    tree = cKDTree(pts)

    def f(p):
        d, _ = tree.query(p, k=2, workers=-1)
        e = (d[:, 1] - d[:, 0]).astype(F)
        return (1.0 - D.smooth01(e, 0.0, largo)).astype(F)
    return f


def fine(name, field, pts, mat, pad=0.03, res=None, attrs=None):
    """Mesh di un pezzo sottile, valutata a fasce in una scatola stretta attorno ai suoi punti."""
    P = np.concatenate([np.atleast_2d(np.asarray(p, F)) for p in pts])
    ob = sdf_object(name, field, P.min(0) - pad, P.max(0) + pad, res=res or RES_FINE, attrs=attrs, banded=True)
    ob.data.materials.append(mat)
    return ob


def mesh_obj(name, verts, faces, mat, attrs=None, smooth=True):
    ob = mesh_from_arrays(name, np.asarray(verts, float), faces, smooth=smooth, col='creatures')
    for an, vals in (attrs or {}).items():
        a = ob.data.attributes.new(an, 'FLOAT', 'POINT')
        a.data.foreach_set('value', np.asarray(vals, np.float32))
    ob.data.materials.append(mat)
    set_lightgroup(ob, 'ambient')
    return ob


def base_da(asse_z, verso=(0.3, 1.0, 0.0)):
    """Base ortonormale (colonne x, y, z) con la z lungo asse_z."""
    z = unit(asse_z)
    x = unit(np.cross(V(*verso), z))
    return np.stack([x, np.cross(z, x), z], axis=1).astype(F)


# ───────────────────────── materiali ─────────────────────────

def costante(v):
    """Attributo uguale su tutta la mesh."""
    return lambda p: np.full(len(p), v, F)


def pelle(name, dorso, fianco, ventre, macchie, seconda, puntini=None, vene=(0.10, 0.02, 0.03), placche=(0.85, 0.45, 0.35),
          guance=(0.70, 0.08, 0.10), bocca=(0.10, 0.015, 0.02), melma=(0.80, 0.92, 0.66), sss=(1.0, 0.35, 0.25)):
    """La pelle dei mostri nuovi: la stessa pelle di famiglia (bagnata, a chiazze, malata, con la melma
    lucida e le colature) ma con un colore netto. Attributi: 'ventre' (0 dorso, 1 pancia), 'seconda' (0..1,
    il secondo colore: zampette e pinne, oppure fasce), 'wart' (placche ossee), 'blush', 'mouth'."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    ven = g.attr('ventre')
    col = g.ramp(ven, [(0.0, dorso), (0.5, fianco), (1.0, ventre)])
    # chiazze della pelle malata e maculatura fine
    n1 = g.noise(co, scale=5.0, detail=4.0, rough=0.55, distortion=0.6)
    col = g.mix(g.mul(g.smoothstep(0.52, 0.64, n1.fac), 0.75), col, macchie)
    n2 = g.noise(co, scale=16.0, detail=3.0, rough=0.6)
    col = g.mix(g.mul(g.smoothstep(0.58, 0.72, n2.fac), 0.45), col, macchie)
    # vene sotto la pelle
    warp = g.vmath('ADD', co, g.vmath('SCALE', n1.color, scale=0.05))
    vv = g.voronoi(warp, scale=7.0, feature='DISTANCE_TO_EDGE')
    col = g.mix(g.mul(g.smoothstep(0.025, 0.0, vv), 0.35), col, vene)
    # il secondo colore con le sue macchie
    sec = g.attr('seconda')
    col = g.mix(sec, col, seconda)
    if puntini is not None:
        dots = g.voronoi(co, scale=48.0, feature='F1')
        col = g.mix(g.mul(sec, g.smoothstep(0.32, 0.20, dots)), col, puntini)
    # placche ossee, guance, bocca e orbite
    col = g.mix(g.mul(g.attr('wart'), 0.6), col, placche)
    col = g.mix(g.mul(g.attr('blush'), 0.55), col, guance)
    col = g.mix(g.smoothstep(0.3, 0.7, g.attr('mouth')), col, bocca)
    ao = g.ao(distance=0.03, samples=8)
    col = g.mix(g.sub(1.0, ao), col, (0.25, 0.22, 0.22), blend='MULTIPLY')
    # melma: chiazze lucide, colature verso il basso, ristagni nelle cavità; più bagnato sul dorso
    patch = g.noise(co, scale=4.2, detail=4.0, rough=0.55, distortion=0.7)
    pm = g.smoothstep(0.50, 0.60, patch.fac)
    streak = g.noise(g.mapping(co, scale=(28.0, 28.0, 2.6)), scale=1.0, detail=3.0, rough=0.5, distortion=0.3)
    dm = g.mul(g.smoothstep(0.56, 0.68, streak.fac), 0.9)
    cm = g.mul(g.smoothstep(0.25, 0.55, g.sub(1.0, ao)), 0.8)
    sl = g.clamp01(g.add(g.mx(g.mx(pm, dm), cm), g.mul(g.sub(1.0, ven), 0.25)))
    col = g.mix(g.mul(sl, 0.40), col, (melma[0] * 0.8, melma[1] * 0.8, melma[2] * 0.8), blend='MULTIPLY')
    r = g.mixf(sl, 0.50, 0.12)
    grain = g.noise(co, scale=55.0, detail=3.0, rough=0.6)
    nrm = g.bump(g.add(grain.fac, g.mul(g.attr('wart'), 2.0)), strength=0.4, distance=0.003)
    bub = g.voronoi(co, scale=160.0, feature='F1')
    coat_n = g.bump(g.add(g.mul(sl, 0.8), g.mul(g.mul(g.smoothstep(0.22, 0.05, bub), pm), 0.25)), strength=0.3, distance=0.002)
    g.output_material(g.principled(color=col, rough=r, coat=g.add(0.30, g.mul(sl, 0.65)), coat_rough=g.mixf(sl, 0.12, 0.03),
                                   coat_tint=melma, coat_normal=coat_n, sss=0.12, sss_radius=sss, sss_scale=0.03, normal=nrm))
    return m


def pelle_robin():
    """Rosso pieno come la gallinella vera (deve leggersi ROSSO a colpo d'occhio, anche al buio, come un
    animatronic di FNAF): dorso più cupo e bagnato, pancia più chiara e appena rosata; zampette e pinne
    turchese elettrico a macchie blu; melma rossastra. Il rosso tira un filo verso il cremisi perché la
    lampara, calda, lo spinge verso l'arancio."""
    return pelle('RobinSkinRed', dorso=(0.36, 0.010, 0.014), fianco=(0.74, 0.030, 0.032), ventre=(0.88, 0.25, 0.20),
                 macchie=(0.30, 0.008, 0.018), seconda=(0.0, 0.50, 0.62), puntini=(0.01, 0.07, 0.48),
                 vene=(0.22, 0.0, 0.04), placche=(0.95, 0.36, 0.24), guance=(0.60, 0.02, 0.07), melma=(1.0, 0.55, 0.52))


def melma_rossa():
    return skin.slime_material('SlimeRed', tint=(0.90, 0.32, 0.26))


def biglietti_material():
    """I biglietti della sala giochi: carta arancio con la finestrella chiara stampata, la perforazione tra un
    biglietto e l'altro, fradici e macchiati d'alga. Attributi: 'tick' (metri lungo la striscia), 'side' (−1..1)."""
    m = bpy.data.materials.get('Tickets')
    if m:
        return m
    m, g = material('Tickets')
    co = g.texcoord('Object')
    tick, side = g.attr('tick'), g.attr('side')
    u = g.math('FRACT', g.div(tick, 0.052))
    a = g.math('ABSOLUTE', side)
    perf = g.smoothstep(0.045, 0.012, g.mn(u, g.sub(1.0, u)))            # perforazione
    # la finestrella chiara è piccola: sul braccio rosso il biglietto deve restare arancio
    win = g.mul(g.mul(g.smoothstep(0.26, 0.30, u), g.smoothstep(0.74, 0.70, u)), g.smoothstep(0.46, 0.40, a))
    # "scritte" nella finestrella: righe di segni scuri
    txt = g.noise(g.comb(g.mul(tick, 260.0), g.mul(side, 5.0), 0.0), scale=1.0, detail=1.0)
    rows = g.smoothstep(0.25, 0.0, g.math('ABSOLUTE', g.sub(g.math('FRACT', g.mul(g.add(side, 1.0), 1.6)), 0.5)))
    ink = g.mul(g.mul(win, g.smoothstep(0.5, 0.56, txt.fac)), g.sub(1.0, rows))
    col = g.mix(g.smoothstep(0.80, 0.92, a), (1.0, 0.46, 0.035), (0.75, 0.16, 0.10))   # bordino rosa scuro
    col = g.mix(win, col, (0.98, 0.80, 0.62))
    col = g.mix(ink, col, (0.40, 0.06, 0.04))
    col = g.mix(perf, col, (0.30, 0.10, 0.04))
    # carta fradicia: macchie d'alga e di sporco, scolorita a chiazze
    st = g.noise(co, scale=9.0, detail=5.0, rough=0.6)
    col = g.mix(g.mul(g.smoothstep(0.56, 0.72, st.fac), 0.75), col, (0.16, 0.15, 0.06))
    fade = g.noise(co, scale=3.0, detail=3.0)
    col = g.mix(g.mul(g.smoothstep(0.45, 0.7, fade.fac), 0.22), col, (0.95, 0.62, 0.50))
    bump = g.bump(g.add(g.mul(perf, 0.6), g.mul(st.fac, 0.3)), strength=0.25, distance=0.001)
    g.output_material(g.principled(color=col, rough=0.55, coat=0.35, coat_rough=0.15, sss=0.15,
                                   sss_radius=(1.0, 0.5, 0.3), sss_scale=0.004, normal=bump))
    return m


def ventaglio_material():
    """La membrana della pettorale, come la gallinella vera: turchese elettrico, più cupo verso la base, con le
    macchie blu e il bordo chiaro; traslucida controluce. Attributo 'bordo' (0 alla base, 1 al bordo)."""
    m = bpy.data.materials.get('FinWebTeal')
    if m:
        return m
    m, g = material('FinWebTeal')
    co = g.texcoord('Object')
    bordo = g.attr('bordo')
    n = g.noise(co, scale=30.0, detail=4.0, rough=0.6)
    col = g.mix(g.smoothstep(0.05, 0.55, bordo), (0.0, 0.09, 0.14), (0.0, 0.46, 0.58))
    dots = g.voronoi(co, scale=34.0, feature='F1')
    spot = g.mul(g.mul(g.smoothstep(0.30, 0.16, dots), g.smoothstep(0.20, 0.35, bordo)), g.smoothstep(0.90, 0.78, bordo))
    col = g.mix(spot, col, (0.01, 0.05, 0.42))
    col = g.mix(g.smoothstep(0.80, 0.95, bordo), col, (0.20, 0.85, 0.92))
    col = g.mix(g.mul(n.fac, 0.2), col, (0.0, 0.10, 0.12))
    veins = g.voronoi(co, scale=22.0, feature='DISTANCE_TO_EDGE')
    col = g.mix(g.mul(g.smoothstep(0.025, 0.0, veins), 0.35), col, (0.0, 0.06, 0.20))
    g.output_material(g.principled(color=col, rough=0.25, transmission=0.15, ior=1.36, sss=0.4, sss_radius=(0.3, 0.8, 1.0),
                                   sss_scale=0.01, coat=0.8, coat_rough=0.04, normal=g.bump(n.fac, strength=0.2, distance=0.002)))
    return m


def zinco_opaco():
    """Lo zinco del secchio, ma vecchio e opaco: in queste tavole non deve rubare la scena con i riflessi."""
    m = bpy.data.materials.get('GalvanizedDull')
    if m:
        return m
    m, g = material('GalvanizedDull')
    co = g.texcoord('Object')
    sp = g.bw(g.voronoi(co, scale=40.0, out='Color'))
    dent = g.noise(co, scale=3.0, detail=3.0).fac
    col = g.mix(sp, (0.20, 0.21, 0.21), (0.32, 0.33, 0.32))
    col = g.mix(g.mul(g.smoothstep(0.55, 0.75, g.noise(co, scale=6.0, detail=4.0).fac), 0.6), col, (0.10, 0.08, 0.05))
    g.output_material(g.principled(color=col, metal=0.85, rough=g.map_range(sp, 0, 1, 0.45, 0.70), normal=g.bump(dent, strength=0.15, distance=0.01)))
    return m


def pesce_material():
    """Pesce del secchio: dorso blu-grigio scuro, fianchi e pancia d'argento, la linea laterale; bagnato.
    Attributo 'dorso' (0 pancia, 1 schiena)."""
    m = bpy.data.materials.get('BucketFishSkin')
    if m:
        return m
    m, g = material('BucketFishSkin')
    co = g.texcoord('Object')
    dorso = g.attr('dorso')
    n = g.noise(co, scale=60.0, detail=3.0)
    col = g.mix(g.smoothstep(0.42, 0.72, dorso), (0.42, 0.45, 0.45), (0.035, 0.055, 0.07))
    col = g.mix(g.mul(g.smoothstep(0.03, 0.0, g.math('ABSOLUTE', g.sub(dorso, 0.55))), 0.6), col, (0.02, 0.03, 0.035))
    col = g.mix(g.mul(n.fac, 0.3), col, (0.25, 0.27, 0.26))
    g.output_material(g.principled(color=col, metal=0.55, rough=0.22, coat=0.9, coat_rough=0.03, thin_film=300.0,
                                   normal=g.bump(n.fac, strength=0.15, distance=0.001)))
    return m


# ───────────────────────── la scena: bordo, banco, secchio ─────────────────────────

def pesce(name, coda, testa_verso, L=0.26, dorso=(0, 0, 1)):
    """Un pesce del secchio (argentato, l'occhio lattiginoso), dalla coda verso la testa."""
    d = unit(testa_verso)
    M = base_da(-d, verso=dorso if abs(float(np.dot(unit(dorso), d))) < 0.95 else (1, 0, 0))   # locale: +Z verso la coda, +Y il dorso
    c = V(*coda)
    body = sdf.union(sdf.ellipsoid(V(0, 0, -0.57 * L), (0.015, 0.035, 0.40 * L)),
                     sdf.ellipsoid(V(0, -0.003, -0.86 * L), (0.013, 0.027, 0.15 * L)),
                     sdf.round_cone(V(0, 0, -0.25 * L), V(0, 0, -0.05 * L), 0.009, 0.004),
                     D.ellipsoid_rot(V(0, 0.026, 0.006), (0.0035, 0.012, 0.050), sdf.rot_matrix('x', 42)),
                     D.ellipsoid_rot(V(0, -0.026, 0.006), (0.0035, 0.012, 0.050), sdf.rot_matrix('x', -42)),
                     sdf.ellipsoid(V(0, 0.034, -0.52 * L), (0.003, 0.016, 0.06)),
                     sdf.ellipsoid(V(0, -0.030, -0.40 * L), (0.003, 0.012, 0.03)), k=0.008)
    body = sdf.subtract(body, sdf.sphere(V(0, -0.004, -1.0 * L), 0.009), k=0.003)
    f = lambda p: body((p - c) @ M)
    tip = c + M @ V(0, 0, -L)
    dorso = lambda p: np.clip(0.5 + ((p - c) @ M)[:, 1] / 0.07, 0.0, 1.0)
    ob = sdf_object(name, f, np.minimum(c, tip) - 0.07, np.maximum(c, tip) + 0.07, res=0.0016, attrs={'dorso': dorso}, banded=True)
    ob.data.materials.append(pesce_material())
    obs = [ob]
    for s in (-1, 1):
        e = c + M @ V(s * 0.0125, 0.008, -0.88 * L)
        obs.append(D.mesh(f'{name}Eye{s}', sdf.sphere(e, 0.0078), e - 0.012, e + 0.012, D.mat_simple('DeadFishEye', (0.62, 0.64, 0.60), rough=0.15, coat=0.8), res=0.0012))
    return obs


def scena():
    mats = boat.make_materials()
    obs = []
    gw = rbox('Gunwale', (1.9, 0.075, 0.045), (0, 0.0, GUN - 0.0225), bevel=0.01, col='set')
    gw.data.materials.append(mats['wood_varnish'])
    wall = rbox('HullWall', (1.9, 0.02, GUN - 0.12), (0, -0.035, 0.06 + (GUN - 0.12) / 2), bevel=0.0, col='set')
    wall.data.materials.append(mats['hull_in'])
    bench = rbox('Bench', (1.9, 0.30, 0.035), (0, BUCKET[1], BENCH - 0.0175), bevel=0.006, col='set')
    bench.data.materials.append(mats['wood_varnish'])
    floor = rbox('Floor', (1.9, 1.7, 0.02), (0, -0.85, 0.07), bevel=0.0, col='set')
    floor.data.materials.append(mats['floor'])
    obs += [gw, wall, bench, floor]
    for x in (-0.62, 0.62):
        rib = rbox('Rib', (0.04, 0.03, GUN - 0.12), (x, -0.06, 0.06 + (GUN - 0.12) / 2), bevel=0.006, col='set')
        rib.data.materials.append(mats['hull_in'])
        obs.append(rib)
    water = rbox('Water', (8, 8, 0.01), (0, 4.05, 0.0), bevel=0.0, col='set')
    water.data.materials.append(D.mat_simple('NightWater', (0.004, 0.012, 0.016), rough=0.04, spec=0.8))
    obs.append(water)
    # il secchio zincato, come quello del gioco, con dentro i pesci della quota
    x, y, z = map(float, BUCKET)
    prof = [(0.0, 0.0), (0.125, 0.0), (0.128, 0.01), (0.155, 0.27), (0.162, 0.28), (0.158, 0.285)]
    b = lathe('Bucket', prof, n=40, col='set')
    so = b.modifiers.new('T', 'SOLIDIFY')
    so.thickness = 0.004
    b.location = (x, y, z)
    b.data.materials.append(zinco_opaco())
    handle = [(x + 0.158 * math.cos(a), y, z + 0.28 + 0.12 * math.sin(a)) for a in np.linspace(0.15, math.pi - 0.15, 13)]
    hb = tube('BucketHandle', handle, 0.004, n=6, col='set')
    hb.data.materials.append(mats['chrome'])
    obs += [b, hb]
    obs += pesce('BucketFish0', (x - 0.08, y + 0.05, z + 0.20), (0.9, -0.3, -0.25))
    obs += pesce('BucketFish1', (x + 0.07, y - 0.07, z + 0.17), (-0.6, 0.8, -0.1), dorso=(0.3, 0, 1))
    obs += pesce('BucketFish2', (x + 0.02, y + 0.09, z + 0.12), (-0.2, -0.9, -0.3), dorso=(-0.4, 0, 1))
    for o in obs:
        set_lightgroup(o, 'ambient')
    return obs


# ───────────────────────── il corpo (sagoma A «Granchio») ─────────────────────────
# Steso sul bordo come un ragno di mare: il busto piatto sopra il capodibanda, i gomiti e le ginocchia più
# alti della schiena, la coda che scende fuori bordo fino al mare. Le braccia sono il primo paio di raggi
# liberi; dietro, su ogni fianco, altri tre raggi a zampetta. Le pettorali a ventaglio si aprono dietro la
# testa, come fa la gallinella quando si spaventa.

SPINE = [V(0, -0.36, 0.89), V(0, -0.16, 0.93), V(0, 0.06, 0.94), V(0, 0.26, 0.90)]
TAIL = [V(0, 0.26, 0.90), V(0, 0.46, 0.75), V(0, 0.60, 0.47), V(0, 0.68, 0.16), V(0, 0.72, -0.06)]


def braccio_pose(s, shh=False):
    """Punti del braccio (spalla, gomito, polso). s = +1 il braccio che pesca nel secchio, s = −1 l'altro,
    appoggiato al banco (nella C sale alla bocca: il polso lo decide la mano)."""
    sh = V(s * 0.085, -0.285, 0.895)
    if s > 0:
        return sh, V(0.35, -0.48, 1.16), V(0.11, -0.75, 0.95)
    if shh:
        return sh, V(-0.31, -0.63, 0.66), None
    return sh, V(-0.39, -0.47, 1.12), V(-0.34, -0.76, 0.50)


def raggi():
    """Le tre zampe-raggio di ogni fianco: base, ginocchio, punti della parte libera fino alla punta."""
    out = []
    for s in (-1, 1):
        out.append((s, [V(s * 0.10, -0.09, 0.93), V(s * 0.42, -0.17, 1.30), V(s * 0.57, -0.33, 0.95), V(s * 0.62, -0.56, 0.60), V(s * 0.63, -0.71, 0.405)]))
        out.append((s, [V(s * 0.11, 0.09, 0.935), V(s * 0.47, 0.18, 1.32), V(s * 0.61, 0.13, 1.06), V(s * 0.66, 0.05, 0.86), V(s * 0.67, 0.01, 0.765)]))
        out.append((s, [V(s * 0.10, 0.25, 0.905), V(s * 0.40, 0.45, 1.19), V(s * 0.52, 0.47, 0.86), V(s * 0.56, 0.30, 0.52), V(s * 0.57, 0.12, 0.30)]))
    return out


def mano(polso, nocche, punte, r0=0.0125, r1=0.0055, palmata=0.7, curve=None):
    """Mano palmata: dita lunghissime dal polso alle nocche alle punte, la membrana tra le dita vicine."""
    parts = [sdf.sphere(polso, 0.022)]
    fingers = []
    for i, (k, t) in enumerate(zip(nocche, punte)):
        mid = (k + t) / 2 + (curve[i] if curve is not None else V(0, 0, 0))
        f, cp = tubo([polso + (k - polso) * 0.25, k, mid, t], r0, r1, n=6, nodi=0.12)
        parts.append(f)
        fingers.append(cp)
    for a, b in zip(fingers[:-1], fingers[1:]):
        n = min(len(a), len(b))
        for j in range(0, int(n * palmata), 2):
            parts.append(sdf.capsule(a[j], b[j], 0.0032))
    return sdf.union(*parts, k=0.008)


def corpo(head_field, shh_wrist=None):
    """Il campo del corpo intero (busto, coda, braccia, raggi, collo) unito alla testa."""
    torso = squash(chain(SPINE, [0.085, 0.12, 0.13, 0.11], k=0.05), (0, 0, 0.92), (1.0, 1.0, 0.78))
    tail = chain(TAIL, [0.11, 0.085, 0.07, 0.06, 0.05], k=0.04)
    belly = sdf.ellipsoid(V(0, 0.0, 0.825), (0.10, 0.14, 0.07))          # la pancia che si appoggia al bordo
    sp = catmull(SPINE[1:] + TAIL[1:3], 3)
    bumps = sdf.union(*[sdf.sphere(c + V(0, 0, 0.085 - 0.02 * i / len(sp)), 0.022 - 0.008 * i / len(sp)) for i, c in enumerate(sp)])
    neck = chain([SPINE[0], V(0, -0.44, 0.90)], [0.085, 0.08], k=0.02)
    parts = [torso, tail, belly, bumps, neck, head_field]
    for s in (-1, 1):
        sh, el, wr = braccio_pose(s, shh=shh_wrist is not None)
        if wr is None:
            wr = shh_wrist
        upper, _ = tubo([sh, el], 0.036, 0.027)
        fore, _ = tubo([el, (el + wr) / 2 + V(0, 0, 0.02), wr], 0.027, 0.020)
        parts += [upper, fore, sdf.sphere(el, 0.033)]
        if s > 0:
            # sopra il secchio: le dita si chiudono attorno al pesce appena tirato fuori
            kn = [wr + V(dx, -0.065, -0.035) for dx in (-0.033, -0.011, 0.011, 0.033)]
            tp = [V(FISH[0] - 0.026 + 0.017 * i, FISH[1] - 0.004, FISH[2] - 0.046) for i in range(4)]
            parts.append(mano(wr, kn, tp, curve=[V(0, -0.045, 0.01)] * 4))
        elif shh_wrist is None:
            # appoggiata al banco, le dita aperte a ventaglio sul legno
            kn = [wr + V(dx, -0.05, -0.05) for dx in (-0.05, -0.017, 0.017, 0.05)]
            tp = [wr + V(dx * 2.6, -0.22, -0.094) for dx in (-0.05, -0.017, 0.017, 0.05)]
            parts.append(mano(wr, kn, tp, curve=[V(0, 0, 0.03)] * 4))
    for s, pts in raggi():
        f, _ = tubo(pts, 0.026, 0.0075, n=6, nodi=0.18)
        parts.append(f)
    f = sdf.union(*parts, k=0.022)

    def ribs(p):
        """Pieghe della pelle sulle costole, sui fianchi."""
        side = D.smooth01(np.abs(p[:, 0]), 0.05, 0.10) * (1 - D.smooth01(np.abs(p[:, 0]), 0.14, 0.17))
        band = D.smooth01(p[:, 1], -0.28, -0.20) * (1 - D.smooth01(p[:, 1], 0.18, 0.26)) * D.smooth01(p[:, 2], 0.84, 0.88)
        return (np.sin(p[:, 1] * 60.0) * 0.5 + 0.5) * side * band
    return sdf.displace(f, ribs, -0.003)


def gills():
    """Le branchie: tre fessure per lato sul collo, dietro la testa."""
    return sdf.union(*[D.ellipsoid_rot(V(s * 0.079, -0.385 + 0.028 * i, 0.905), (0.006, 0.010, 0.032), sdf.rot_matrix('y', s * 20)) for s in (-1, 1) for i in range(3)])


def zampette():
    """Punti lungo le zampe-raggio, col parametro t (0 alla base, 1 alla punta): servono per colorarle."""
    P, T = [], []
    for _, pts in raggi():
        c = catmull(pts, 14)
        P.append(c)
        T.append(np.linspace(0.0, 1.0, len(c)))
    return np.concatenate(P).astype(F), np.concatenate(T).astype(F)


def attr_robin(fr, faccia=0.0):
    """Gli attributi del colore: 'ventre' (la pancia rosata sotto il busto e sotto la testa; nella C anche la
    faccia) e 'seconda' (le zampe-raggio, che dalla base rossa diventano turchesi)."""
    from scipy.spatial import cKDTree
    P, T = zampette()
    tree = cKDTree(P)

    def ventre(p):
        v = np.full(len(p), 0.35, F)
        torso = (np.abs(p[:, 0]) < 0.18) & (p[:, 1] > -0.44) & (p[:, 1] < 0.34) & (p[:, 2] > 0.72) & (p[:, 2] < 1.08)
        v[torso] = D.smooth01(1.02 - p[torso, 2], 0.0, 0.20)
        q = (p - fr.pos) @ fr.R
        near = np.linalg.norm(q, axis=1) < 0.20
        vh = D.smooth01(-q[:, 2], -0.07, 0.07) * 0.85 + 0.05
        if faccia:
            vh = np.maximum(vh, D.smooth01(-q[:, 1], 0.05, 0.09) * faccia)
        v[near] = vh[near]
        return v

    def seconda(p):
        d, i = tree.query(p, k=1, workers=-1)
        return ((1.0 - D.smooth01(d.astype(F), 0.034, 0.05)) * D.smooth01(T[i], 0.03, 0.13)).astype(F)
    return {'ventre': ventre, 'seconda': seconda}


def corpo_mesh(fr, head_field, cut=None, attrs=None, shh_wrist=None, faccia=0.0):
    f = corpo(head_field, shh_wrist=shh_wrist)
    c = gills()
    if cut is not None:
        c = sdf.union(c, cut)
    f = sdf.subtract(f, c, k=0.005)
    a = attr_robin(fr, faccia)
    a.update(attrs or {})
    ob = sdf_object('RobinSkin', f, V(-0.78, -1.02, -0.08), V(0.78, 0.80, 1.40), res=RES_BODY, attrs=a, banded=True)
    ob.data.materials.append(pelle_robin())
    return ob


# ───────────────────────── i ventagli ─────────────────────────

def ventagli():
    """Le pettorali a ventaglio, aperte dietro la testa verso chi guarda: sette spine che si irraggiano dalla
    spalla, la membrana scura tesa tra l'una e l'altra col bordo smerlato e azzurrognolo."""
    obs = []
    up = unit(V(0, 0.35, 1.0))
    for s in (-1, 1):
        B = V(s * 0.11, -0.31, 0.93)
        lat = V(s, 0, 0)
        ths = np.radians(np.linspace(-25, 80, 7))
        rays = []
        for i, th in enumerate(ths):
            t = i / (len(ths) - 1)
            L = 0.19 + 0.09 * math.sin(math.pi * t)
            d = math.cos(th) * lat + math.sin(th) * up
            pts = [B + d * L * u + V(0, -0.035, 0) * math.sin(math.pi * u) for u in np.linspace(0, 1, 13)]   # incavato verso di noi
            rays.append(np.array(pts, F))
        verts, faces, bordo = [], [], []
        nr, nc = len(rays[0]) - 1, 5
        for i in range(len(rays) - 1):
            a, b = rays[i], rays[i + 1]
            o = len(verts)
            for c in range(nc + 1):
                cc = c / nc
                lim = 1.0 - 0.22 * math.sin(math.pi * cc)       # smerlo: in mezzo la membrana si ferma prima
                for j in range(nr + 1):
                    u = j / nr * lim
                    k = min(int(u * nr), nr - 1)
                    w = u * nr - k
                    pa = a[k] * (1 - w) + a[k + 1] * w
                    pb = b[k] * (1 - w) + b[k + 1] * w
                    verts.append(pa * (1 - cc) + pb * cc)
                    bordo.append(u)
            for c in range(nc):
                for j in range(nr):
                    q = o + c * (nr + 1) + j
                    faces.append((q, q + 1, q + 1 + nr + 1, q + nr + 1))
        ob = mesh_obj(f'FinWeb{s}', verts, faces, ventaglio_material(), attrs={'bordo': bordo})
        sol = ob.modifiers.new('S', 'SOLIDIFY')
        sol.thickness = 0.0025
        sol.offset = 0.0
        obs.append(ob)
        spines = [tubo(r[::3], 0.0105, 0.0028, n=4, nodi=0.12)[0] for r in rays]
        obs.append(fine(f'FinSpines{s}', sdf.union(*spines), rays, pelle_robin(), res=0.0025, attrs={'seconda': costante(1.0), 'ventre': costante(0.3)}))
    return obs


# ───────────────────────── i biglietti ─────────────────────────

def nastro(name, pts, wdir, larghezza=0.030):
    """Nastro piatto lungo pts, largo 'larghezza' nella direzione wdir (una per punto)."""
    pts = np.asarray(pts, F)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    verts, faces, tick, side = [], [], [], []
    for i, (p, w) in enumerate(zip(pts, wdir)):
        verts += [p - w * larghezza / 2, p + w * larghezza / 2]
        tick += [s[i], s[i]]
        side += [-1.0, 1.0]
        if i:
            a = 2 * (i - 1)
            faces.append((a, a + 1, a + 3, a + 2))
    ob = mesh_obj(name, verts, faces, biglietti_material(), attrs={'tick': tick, 'side': side})
    sol = ob.modifiers.new('S', 'SOLIDIFY')
    sol.thickness = 0.0012
    sol.offset = 0.0
    return ob


def elica(a, b, r, giri, fase=0.0, n_per_giro=28):
    """Spire attorno al segmento a→b (un avambraccio): punti e direzioni della larghezza del nastro, che
    resta steso sulla pelle."""
    a, b = V(*a), V(*b)
    ax = unit(b - a)
    u = unit(np.cross(ax, V(0.3, 0.2, 1.0)))
    v = np.cross(ax, u)
    n = max(8, int(giri * n_per_giro))
    pts, wd = [], []
    for i in range(n + 1):
        t = i / n
        th = fase + 2 * math.pi * giri * t
        rad = math.cos(th) * u + math.sin(th) * v
        tg = unit((b - a) + (-math.sin(th) * u + math.cos(th) * v) * (2 * math.pi * giri * r))
        pts.append(a + (b - a) * t + rad * r)
        wd.append(unit(np.cross(rad, tg)))
    return np.array(pts, F), np.array(wd, F)


def libero(pts, w0, n=8, torsione=0.0):
    """Tratto libero del nastro (anse che pendono): curva morbida, la larghezza trasportata lungo la curva
    a partire da w0, con un po' di torsione."""
    P = catmull([V(*p) for p in pts], n)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    W = [unit(w0 - (w0 @ T[0]) * T[0])]
    for i in range(1, len(P)):
        w = unit(W[-1] - (W[-1] @ T[i]) * T[i])
        if torsione:
            ang = torsione / len(P)
            w = unit(w * math.cos(ang) + np.cross(T[i], w) * math.sin(ang))
        W.append(w)
    return np.array(P, F), np.array(W, F)


def biglietti(shh_wrist=None):
    """La striscia di biglietti: un capo che pende nel secchio, le spire attorno al braccio che ruba, un'ansa
    sotto il collo, le spire attorno all'altro braccio, e il resto che cade sul banco e giù fino al pagliolo."""
    shF, elF, wrF = braccio_pose(1)
    shN, elN, wrN = braccio_pose(-1, shh=shh_wrist is not None)
    if wrN is None:
        wrN = shh_wrist
    P, W = [], []

    def add(p, w, skip=0):
        P.append(p[skip:])
        W.append(w[skip:])

    # il capo libero che pende nel secchio, poi le spire attorno all'avambraccio, dal polso al gomito
    h1, w1 = elica(wrF + (elF - wrF) * 0.08, elF + (wrF - elF) * 0.12, 0.031, 5.5, fase=0.3)
    p0, w0 = libero([BUCKET + V(0.10, 0.02, 0.20), BUCKET + V(0.12, 0.0, 0.33), wrF + V(0.05, -0.02, -0.04), h1[0]], V(1, 0, 0), n=6)
    add(p0[:-1], w0[:-1])
    add(h1, w1)
    # il braccio, dal gomito alla spalla
    h2, w2 = elica(elF + (shF - elF) * 0.08, shF + (elF - shF) * 0.25, 0.037, 3.5, fase=1.0)
    j, jw = libero([h1[-1], elF + V(0.03, -0.02, 0.05), h2[0]], w1[-1], n=4)
    add(j[1:-1], jw[1:-1])
    add(h2, w2)
    # l'ansa sotto il collo, da una spalla all'altra
    h3, w3 = elica(shN + (elN - shN) * 0.25, elN + (shN - elN) * 0.08, 0.037, 3.5, fase=2.0)
    p3, pw3 = libero([h2[-1], V(0.10, -0.40, 0.76), V(0.0, -0.44, 0.72), V(-0.10, -0.42, 0.76), h3[0]], w2[-1], n=8, torsione=1.2)
    add(p3[1:-1], pw3[1:-1])
    add(h3, w3)
    # l'altro avambraccio
    h4, w4 = elica(elN + (wrN - elN) * 0.10, wrN + (elN - wrN) * 0.10, 0.031, 5.5, fase=0.5)
    j, jw = libero([h3[-1], elN + V(-0.03, 0.0, 0.05), h4[0]], w3[-1], n=4)
    add(j[1:-1], jw[1:-1])
    add(h4, w4)
    # il resto: giù sul banco a zig-zag, oltre il bordo del banco e fino al pagliolo
    e = h4[-1]
    rest = [e, e + V(-0.03, -0.03, -0.10), V(e[0] - 0.12, -0.80, BENCH + 0.015), V(e[0] - 0.20, -0.90, BENCH + 0.004),
            V(e[0] - 0.12, -0.97, BENCH + 0.004), V(e[0] - 0.16, -1.02, BENCH - 0.06), V(e[0] - 0.22, -1.06, 0.20), V(e[0] - 0.30, -1.10, 0.085)]
    p5, w5 = libero(rest, w4[-1], n=8, torsione=2.0)
    add(p5[1:], w5[1:])
    return [nastro('Tickets', np.concatenate(P), np.concatenate(W))]


# ───────────────────────── le teste ─────────────────────────

def frame():
    return D.Frame(tuple(map(float, HEAD)), pitch=HEAD_PITCH, yaw=HEAD_YAW)


def look():
    return unit(CAM - HEAD)


def barbiglio(fr, q, passi, r0=0.0075, r1=0.0018):
    """Un barbiglio: parte dalla testa (coordinate locali) e pende (passi nel mondo)."""
    pts = [fr.pt(q)]
    for d in passi:
        pts.append(pts[-1] + V(*d))
    f, cp = tubo(pts, r0, r1, n=6)
    return f, cp


def osso(fr, pl, zmin=None):
    """Attributo 'wart' della pelle: le placche ossee della corazza più chiare e in rilievo, i solchi scuri;
    solo sulla testa (e, con zmin, solo in cima)."""
    def f(p):
        q = (p - fr.pos) @ fr.R
        near = 1.0 - D.smooth01(np.linalg.norm(q * V(1.0, 0.85, 1.0), axis=1), 0.16, 0.21)
        if zmin is not None:
            near = near * D.smooth01(q[:, 2], zmin - 0.01, zmin + 0.015)
        return ((1.0 - pl(q)) * near * 0.85).astype(F)
    return f


def bava(name, fili=(), gocce=()):
    """Lo strato di melma: fili di bava tesi tra due punti che si afflosciano, gocce che pendono."""
    parts, pts = [], []
    for a, b, sag in fili:
        a, b = V(*a), V(*b)
        parts.append(skin.strand(a, b, sag, r=0.0016))
        pts += [a, b, (a + b) / 2 - V(0, 0, sag)]
    for a, L in gocce:
        a = V(*a)
        parts.append(skin.drip(a, L, r0=0.0022, r1=0.0042))
        pts += [a, a - V(0, 0, L)]
    return fine(name, sdf.union(*parts), [np.array(pts, F)], melma_rossa(), pad=0.012, res=0.0011)


def comune(obs, shh_wrist=None):
    """Quello che hanno tutte e tre: i biglietti, i ventagli, il pesce rubato."""
    return obs + biglietti(shh_wrist) + ventagli() + pesce('StolenFish', FISH - FISH_DIR * 0.15, FISH_DIR, L=0.30, dorso=(0, 0, 1))


def robin_a():
    """A · Corazza: la testa della gallinella, una scatola d'osso a placche con le spine all'indietro, gli
    occhi in cima sotto le arcate, il muso a due lobi; sotto, i barbigli del pesce gatto."""
    fr = frame()
    cran = sdf.ellipsoid(V(0, 0.03, 0.005), (0.122, 0.15, 0.08))
    snout = sdf.ellipsoid(V(0, -0.085, -0.022), (0.10, 0.09, 0.062))
    box = sdf.intersect(sdf.union(cran, snout, k=0.045), sdf.plane(V(0, 0, 1), -0.064), k=0.014)   # tetto piatto
    cheeks = sdf.union(*[sdf.ellipsoid(V(s * 0.097, -0.015, -0.027), (0.036, 0.095, 0.046)) for s in (-1, 1)])
    brows = sdf.union(*[sdf.ellipsoid(V(s * 0.066, -0.045, 0.060), (0.040, 0.050, 0.021)) for s in (-1, 1)])
    lobes = sdf.union(*[sdf.ellipsoid(V(s * 0.041, -0.158, -0.032), (0.034, 0.032, 0.028)) for s in (-1, 1)])
    head = sdf.union(box, cheeks, brows, lobes, k=0.02)
    pl = placche(11, (0, 0, 0), (0.15, 0.20, 0.10), 140)
    head = sdf.displace(head, pl, -0.0035)
    spines = []
    for s in (-1, 1):
        spines.append(sdf.round_cone(V(s * 0.046, -0.180, -0.030), V(s * 0.058, -0.222, -0.022), 0.010, 0.0015))
        spines.append(sdf.round_cone(V(s * 0.100, 0.090, 0.000), V(s * 0.158, 0.215, 0.004), 0.013, 0.002))
        spines.append(sdf.round_cone(V(s * 0.092, 0.110, -0.045), V(s * 0.135, 0.205, -0.072), 0.011, 0.0018))
        spines.append(sdf.round_cone(V(s * 0.085, -0.020, 0.062), V(s * 0.105, 0.040, 0.085), 0.008, 0.0015))
    for y in (0.03, 0.075, 0.12):
        spines.append(sdf.round_cone(V(0, y, 0.058), V(0, y + 0.045, 0.098), 0.009, 0.0015))   # la cresta della nuca
    head = sdf.union(head, *spines, k=0.006)
    sockets = sdf.union(*[sdf.sphere(V(s * 0.067, -0.062, 0.046), 0.025) for s in (-1, 1)])
    mouth = sdf.ellipsoid(V(0, -0.118, -0.068), (0.076, 0.048, 0.017))
    hf = entro(fr.field(head), HEAD - 0.30, HEAD + 0.30)
    cut = entro(fr.field(sdf.union(sockets, mouth)), HEAD - 0.25, HEAD + 0.25)
    obs = [corpo_mesh(fr, hf, cut=cut, attrs={'wart': osso(fr, pl)})]
    c0 = fr.pt((0, -0.09, -0.066))
    obs.append(D.mesh('RobinThroat', fr.field(sdf.ellipsoid(V(0, -0.09, -0.066), (0.068, 0.04, 0.012))), c0 - 0.1, c0 + 0.1, D.dark_throat(), res=0.003))
    pairs = []
    for i in range(11):
        t = i / 10 - 0.5
        x = t * 0.13
        y = -0.158 + 0.11 * t * t
        pairs.append((fr.pt((x, y + 0.006, -0.055)), fr.pt((x * 0.95, y + 0.010, -0.072)), 0.0042))
    obs.append(D.teeth_mesh('RobinTeeth', pairs, D.needle_teeth()))
    obs += D.eyes('RobinEye', [fr.pt((s * 0.067, -0.058, 0.046)) for s in (-1, 1)], 0.0225, look())
    bb, pts = [], []
    for s in (-1, 1):
        f1, p1 = barbiglio(fr, (s * 0.050, -0.135, -0.080), [(s * 0.010, -0.040, -0.050), (s * 0.010, -0.035, -0.080), (-0.005 * s, -0.010, -0.090), (0.0, 0.010, -0.060)], 0.0075, 0.0022)
        f2, p2 = barbiglio(fr, (s * 0.078, -0.105, -0.072), [(s * 0.030, -0.025, -0.040), (s * 0.020, -0.020, -0.075), (s * 0.006, 0.0, -0.075)], 0.0065, 0.002)
        bb += [f1, f2]
        pts += [p1, p2]
    obs.append(fine('RobinBarbels', sdf.union(*bb), pts, pelle_robin(), attrs={'ventre': costante(0.6)}))
    obs.append(bava('RobinSlime', fili=[(fr.pt((-0.035, -0.150, -0.074)), fr.pt((0.030, -0.152, -0.074)), 0.035)],
                    gocce=[(fr.pt((-0.012, -0.152, -0.076)), 0.06), (fr.pt((0.045, -0.140, -0.075)), 0.035)]))
    return (comune(obs), *TESTI['A'])


def robin_b():
    """B · Baffi: la testa larga e piatta del pesce gatto su un cranio da quasi-bambino, con le orecchie;
    i baffi lunghissimi pendono dentro il secchio, la corazza è rimasta solo in cima."""
    fr = frame()
    cran = sdf.ellipsoid(V(0, 0.05, 0.028), (0.118, 0.12, 0.096))
    face = sdf.ellipsoid(V(0, -0.065, -0.026), (0.148, 0.10, 0.060))
    lipU = chain([V(-0.122, -0.098, -0.034), V(-0.07, -0.142, -0.036), V(0, -0.160, -0.036), V(0.07, -0.142, -0.036), V(0.122, -0.098, -0.034)], [0.010, 0.016, 0.017, 0.016, 0.010], k=0.01)
    lipL = chain([V(-0.112, -0.096, -0.056), V(-0.06, -0.136, -0.062), V(0, -0.150, -0.064), V(0.06, -0.136, -0.062), V(0.112, -0.096, -0.056)], [0.010, 0.015, 0.016, 0.015, 0.010], k=0.01)
    nose = sdf.ellipsoid(V(0, -0.140, 0.006), (0.030, 0.022, 0.016))
    brow = sdf.ellipsoid(V(0, -0.072, 0.050), (0.085, 0.035, 0.022))
    ears = sdf.union(*[D.ellipsoid_rot(V(s * 0.166, 0.052, 0.014), (0.017, 0.040, 0.052), sdf.rot_matrix('z', s * 38)) for s in (-1, 1)])   # a sventola
    lids = sdf.union(*[sdf.ellipsoid(V(s * 0.072, -0.118, 0.044), (0.030, 0.016, 0.014)) for s in (-1, 1)])
    head = sdf.union(cran, face, lipU, lipL, nose, brow, ears, lids, k=0.018)
    top = placche(23, (0, 0, 0), (0.15, 0.20, 0.12), 110)
    head = sdf.displace(head, lambda p: top(p) * D.smooth01(p[:, 2], 0.045, 0.07), -0.004)
    spines = [sdf.round_cone(V(s * 0.118, 0.060, -0.030), V(s * 0.172, 0.150, -0.040), 0.012, 0.002) for s in (-1, 1)]
    spines += [sdf.round_cone(V(0, y, 0.110), V(0, y + 0.04, 0.145), 0.008, 0.0015) for y in (0.02, 0.07)]
    head = sdf.union(head, *spines, k=0.006)
    mouth = chain([V(-0.118, -0.098, -0.045), V(-0.06, -0.140, -0.050), V(0, -0.158, -0.052), V(0.06, -0.140, -0.050), V(0.118, -0.098, -0.045)], [0.008, 0.014, 0.016, 0.014, 0.008], k=0.004)
    nostrils = sdf.union(*[sdf.sphere(V(s * 0.016, -0.158, 0.002), 0.0065) for s in (-1, 1)])
    concha = sdf.union(*[sdf.sphere(V(s * 0.176, 0.040, 0.012), 0.015) for s in (-1, 1)])
    sockets = sdf.union(*[sdf.sphere(V(s * 0.072, -0.118, 0.028), 0.020) for s in (-1, 1)])
    hf = entro(fr.field(head), HEAD - 0.30, HEAD + 0.30)
    cut = entro(fr.field(sdf.union(mouth, nostrils, concha, sockets)), HEAD - 0.25, HEAD + 0.25)
    def orbite(p):
        q = (p - fr.pos) @ fr.R
        d = np.minimum(np.linalg.norm(q - V(0.072, -0.118, 0.028), axis=1), np.linalg.norm(q - V(-0.072, -0.118, 0.028), axis=1))
        return np.clip(1.0 - (d - 0.015) / 0.014, 0.0, 1.0)

    obs = [corpo_mesh(fr, hf, cut=cut, attrs={'wart': osso(fr, top, zmin=0.05), 'mouth': orbite})]
    c0 = fr.pt((0, -0.11, -0.047))
    obs.append(D.mesh('RobinThroat', fr.field(sdf.ellipsoid(V(0, -0.11, -0.047), (0.10, 0.04, 0.008))), c0 - 0.12, c0 + 0.12, D.dark_throat(), res=0.0025))
    pairs = []
    for i in range(13):
        t = i / 12 - 0.5
        x = t * 0.18
        y = -0.156 + 0.17 * t * t
        pairs.append((fr.pt((x, y + 0.004, -0.040)), fr.pt((x, y + 0.002, -0.050)), 0.003))
        pairs.append((fr.pt((x, y + 0.004, -0.058)), fr.pt((x, y + 0.002, -0.049)), 0.003))
    obs.append(D.teeth_mesh('RobinTeeth', pairs))
    obs += D.eyes('RobinEye', [fr.pt((s * 0.072, -0.108, 0.028)) for s in (-1, 1)], 0.0150, look())
    bb, pts = [], []
    for s in (-1, 1):
        f1, p1 = barbiglio(fr, (s * 0.118, -0.104, -0.034), [(s * 0.045, -0.050, -0.030), (s * 0.030, -0.040, -0.090), (s * 0.010, -0.030, -0.110), (-s * 0.010, -0.005, -0.110), (-s * 0.015, 0.010, -0.080)], 0.0085, 0.0022)
        f2, p2 = barbiglio(fr, (s * 0.020, -0.146, -0.074), [(s * 0.004, -0.020, -0.035), (s * 0.006, -0.010, -0.050)], 0.0045, 0.0015)
        f3, p3 = barbiglio(fr, (s * 0.052, -0.130, -0.072), [(s * 0.012, -0.018, -0.035), (s * 0.014, -0.008, -0.055)], 0.0045, 0.0015)
        bb += [f1, f2, f3]
        pts += [p1, p2, p3]
    obs.append(fine('RobinBarbels', sdf.union(*bb), pts, pelle_robin(), attrs={'ventre': costante(0.6)}))
    obs.append(bava('RobinSlime', fili=[(fr.pt((s * 0.085, -0.125, -0.042)), fr.pt((s * 0.080, -0.122, -0.060)), 0.012) for s in (-1, 1)],
                    gocce=[(fr.pt((-0.030, -0.150, -0.070)), 0.075), (fr.pt((0.040, -0.142, -0.068)), 0.045)]))
    return (comune(obs), *TESTI['B'])


def shh_hand(fr, s=-1):
    """La mano sulla bocca, «zitto»: un pugno lasco davanti al mento, l'indice dritto in piedi sulle labbra
    con l'unghia nera verso chi guarda (è l'unghia a far leggere il dito come un dito), il pollice
    ripiegato sulle altre dita. In coordinate locali della testa (s: da che parte arriva il braccio);
    restituisce il campo, il polso (nel mondo) e le unghie [(centro, raggi)] in coordinate locali."""
    X = V(s, 1, 1)
    wrist = V(0.078, -0.098, -0.225) * X
    palm = D.ellipsoid_rot(V(0.040, -0.122, -0.158) * X, (0.032, 0.022, 0.034), sdf.rot_matrix('y', -20 * s))
    parts = [palm, sdf.round_cone(wrist, V(0.050, -0.118, -0.170) * X, 0.020, 0.022)]
    # l'indice: dalla nocca sale davanti alla bocca e si ferma appena sopra il labbro
    idx, _ = tubo([V(0.020, -0.136, -0.128) * X, V(0.010, -0.130, -0.098) * X, V(0.003, -0.122, -0.068) * X, V(0.0, -0.116, -0.044) * X], 0.0115, 0.0088, n=5, nodi=0.12)
    parts.append(idx)
    # medio, anulare, mignolo chiusi a pugno: le nocche in fila davanti, le punte nel palmo
    for k in range(3):
        x0, z0 = 0.030 + 0.013 * k, -0.140 - 0.013 * k
        f, _ = tubo([V(x0, -0.138, z0) * X, V(x0 - 0.006, -0.152, z0 - 0.012) * X, V(x0 - 0.012, -0.146, z0 - 0.026) * X,
                     V(x0 - 0.014, -0.130, z0 - 0.030) * X], 0.0105 - 0.0008 * k, 0.0085 - 0.0008 * k, n=4, nodi=0.15)
        parts.append(f)
    th, _ = tubo([V(0.066, -0.116, -0.176) * X, V(0.040, -0.150, -0.172) * X, V(0.016, -0.150, -0.160) * X], 0.0105, 0.008, n=4)
    parts.append(th)
    nails = [(V(0.0, -0.1245, -0.050) * X, (0.0070, 0.0030, 0.0100)),          # l'indice, verso chi guarda
             (V(0.012, -0.1575, -0.157) * X, (0.0058, 0.0028, 0.0070))]          # il pollice
    return sdf.union(*parts, k=0.007), fr.pt(wrist), nails


def robin_c():
    """C · Bambino: la faccia del bambino che rubava le cose, che ti guarda col dito sulle labbra; il
    sorriso va oltre il dito, da pesce gatto, e dagli angoli della bocca pendono due barbigli."""
    fr = frame()
    head = sdf.union(sdf.ellipsoid(V(0, 0.0, 0.004), (0.093, 0.102, 0.118)),
                     sdf.sphere(V(0.047, -0.070, -0.036), 0.032), sdf.sphere(V(-0.047, -0.070, -0.036), 0.032),
                     sdf.sphere(V(0, -0.074, -0.086), 0.029), sdf.sphere(V(0, -0.106, -0.004), 0.0125),
                     sdf.ellipsoid(V(0, -0.086, 0.036), (0.068, 0.022, 0.016)),
                     sdf.ellipsoid(V(0.095, 0.0, -0.006), (0.014, 0.026, 0.035)), sdf.ellipsoid(V(-0.095, 0.0, -0.006), (0.014, 0.026, 0.035)),
                     k=0.026)
    # sulla nuca la corazza della gallinella che buca la pelle: tre placche e due spine
    crust = sdf.union(*[sdf.ellipsoid(V(x, 0.06, 0.085 + z), (0.028, 0.03, 0.012)) for x, z in ((-0.03, 0.0), (0.03, 0.0), (0.0, 0.02))])
    crust = sdf.union(crust, *[sdf.round_cone(V(s * 0.07, 0.07, 0.02), V(s * 0.12, 0.16, 0.03), 0.010, 0.0018) for s in (-1, 1)], k=0.006)
    # le palpebre di sopra calate a metà: lo sguardo furbo di chi sa di averla fatta
    lids = sdf.union(*[D.ellipsoid_rot(V(s * 0.038, -0.088, 0.024), (0.023, 0.014, 0.0105), sdf.rot_matrix('y', s * 12)) for s in (-1, 1)])
    hand, wrist, unghie = shh_hand(fr, -1)
    sockets = sdf.union(sdf.sphere(V(0.038, -0.094, 0.016), 0.0205), sdf.sphere(V(-0.038, -0.094, 0.016), 0.0205))
    grin = chain([V(-0.088, -0.028, -0.048), V(-0.062, -0.074, -0.058), V(-0.03, -0.094, -0.062), V(0, -0.100, -0.063),
                  V(0.03, -0.094, -0.062), V(0.062, -0.074, -0.058), V(0.088, -0.028, -0.048)], [0.0025, 0.005, 0.0065, 0.007, 0.0065, 0.005, 0.0025], k=0.003)

    def loc(p):
        return (p - fr.pos) @ fr.R

    def blush(p):
        q = loc(p)
        d = np.minimum(np.linalg.norm(q - V(0.052, -0.088, -0.03), axis=1), np.linalg.norm(q - V(-0.052, -0.088, -0.03), axis=1))
        return np.clip(1.0 - d / 0.035, 0.0, 1.0)

    def dark(p):
        q = loc(p)
        d = np.minimum(np.linalg.norm(q - V(0.038, -0.096, 0.016), axis=1), np.linalg.norm(q - V(-0.038, -0.096, 0.016), axis=1))
        return np.clip(1.0 - (d - 0.012) / 0.012, 0.0, 1.0)

    # la mano e l'avambraccio restano del rosso del corpo, più cupo della faccia: così il dito si stacca
    # dalle labbra
    faccia = attr_robin(fr, 0.6)['ventre']
    avambraccio = sdf.capsule(braccio_pose(-1, shh=True)[1], wrist, 0.05)

    def ventre(p):
        v = faccia(p)
        m = (hand(loc(p)) < 0.004) | (avambraccio(p) < 0.0)
        v[m] = 0.30
        return v

    hf = entro(fr.field(sdf.union(head, crust, hand, k=0.006)), HEAD - 0.32, HEAD + 0.32)
    cut = entro(fr.field(sdf.union(sockets, grin)), HEAD - 0.25, HEAD + 0.25)
    obs = [corpo_mesh(fr, hf, cut=cut, attrs={'blush': blush, 'mouth': dark, 'ventre': ventre}, shh_wrist=wrist)]
    nails = sdf.union(*[sdf.ellipsoid(c, r) for c, r in unghie])
    obs.append(fine('RobinNails', fr.field(nails), [np.array([fr.pt(c) for c, _ in unghie])],
                    D.mat_simple('Nails', (0.03, 0.03, 0.028), rough=0.2, coat=0.8), pad=0.02, res=0.0012))
    c0 = fr.pt((0, -0.080, -0.060))
    obs.append(D.mesh('RobinThroat', fr.field(sdf.ellipsoid(V(0, -0.080, -0.060), (0.075, 0.02, 0.007))), c0 - 0.1, c0 + 0.1, D.dark_throat(), res=0.002))
    pairs = []
    for i in range(16):
        t = i / 15 - 0.5
        x = t * 0.15
        y = -0.098 + 0.24 * t * t
        z = -0.062 + 0.05 * t * t
        pairs.append((fr.pt((x, y + 0.004, z + 0.008)), fr.pt((x, y - 0.002, z + 0.001)), 0.0028))
        pairs.append((fr.pt((x, y + 0.004, z - 0.008)), fr.pt((x, y - 0.002, z - 0.001)), 0.0028))
    obs.append(D.teeth_mesh('RobinTeeth', pairs))
    obs += D.eyes('RobinEye', [fr.pt((s * 0.038, -0.081, 0.015)) for s in (-1, 1)], 0.0165, look())
    bb, pts = [], []
    for s in (-1, 1):
        f1, p1 = barbiglio(fr, (s * 0.086, -0.032, -0.052), [(s * 0.020, -0.020, -0.050), (s * 0.010, -0.020, -0.080), (0.0, -0.010, -0.070)], 0.0055, 0.0016)
        bb.append(f1)
        pts.append(p1)
    obs.append(fine('RobinBarbels', sdf.union(*bb), pts, pelle_robin(), attrs={'ventre': costante(0.6)}))
    strands, hp = [], []
    for a in np.linspace(-1, 1, 8):
        d0 = unit(V(0.15 * a, 0.40, 1.0))
        d1 = unit(V(0.55 * a, -0.15, 0.95))
        d2 = unit(V(0.70 * a, -0.62, 0.50))
        q = [fr.pt(d * 0.118) for d in (d0, d1, d2)]
        strands.append(tubo(q, 0.010, 0.003, n=6)[0])
        hp.append(q)
    obs.append(fine('RobinHair', sdf.union(*strands, k=0.008), hp, D.wet_hair(), res=0.0015))
    c2 = fr.pt((0, -0.088, 0.024))
    lid = sdf_object('RobinLids', fr.field(lids), c2 - 0.08, c2 + 0.08, res=0.0015, attrs={'ventre': costante(0.65)})
    lid.data.materials.append(pelle_robin())
    obs.append(lid)
    obs.append(bava('RobinSlime', fili=[(fr.pt((0.040, -0.090, -0.056)), fr.pt((0.060, -0.078, -0.066)), 0.010)],
                    gocce=[(fr.pt((0.066, -0.072, -0.064)), 0.07)]))
    return (comune(obs, shh_wrist=wrist), *TESTI['C'])


# ───────────────────────── tavola ─────────────────────────

def con_la_barca(variant):
    """Il render di dettagli.py mette in scena solo quello che la variante costruisce: qui si aggiunge anche
    il pezzo di barca (capodibanda, banco, secchio coi pesci) su cui sta Robin."""
    def run():
        obs, label, desc = variant()
        return obs + scena(), label, desc
    run.__name__ = variant.__name__
    return run


# le luci di dettagli.setup sono riferite a 'subject': Robin sta basso sul bordo e la lampara vera pende dal
# palo sopra di lui, quindi il riferimento si alza perché la luce calda arrivi di lato e un po' dall'alto
D.CREATURES['robin'] = {
    'title': 'ROBIN — dettagli della testa (sagoma A «Granchio»), dal posto del pescatore · colori: proposta da approvare',
    'variants': [con_la_barca(v) for v in (robin_a, robin_b, robin_c)],
    'cam': (tuple(map(float, CAM)), (0.0, -0.56, 0.80), 50),
    'subject': (0, -0.45, 1.30), 'key': 70, 'rim': 50,
}


def tavola():
    """Rimonta la tavola dai tre pannelli già renderizzati (in cache), con i testi delle varianti."""
    panels = [(os.path.join(D.TMP, f'robin_{k}.png'), *TESTI[k]) for k in 'ABC']
    return D.compose('robin', panels)


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
        D.render_variant('robin', i)
        print('ok robin', 'ABC'[i], flush=True)
    if only is None:
        print('tavola', tavola(), flush=True)
