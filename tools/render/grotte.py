"""
La grotta grande delle immersioni all'alba (look-dev, DA APPROVARE): la sala naturale scavata dal mare sotto lo
scoglio dell'edicola, dove arrivano le aperture delle tane (docs/IMMERSIONI.md, «Le grotte»).

Coordinate della grotta (metri, z in alto): l'occhio del sub è in OCCHIO, sospeso a mezz'acqua; avanti (+Y) in
fondo alla sala c'è l'apertura enorme della tana della Madre; dietro, in alto, l'imboccatura da cui si è scesi
(il pozzo da cui entra la luce dell'alba). Lo scoglio, la barca e il mare sopra non ci sono: dal pozzo si vede solo
la superficie chiara.

Come è fatta:
  - la roccia è un unico campo SDF (sdf.py): la sala è un'unione morbida di ellissoidi, il pozzo un cono, ogni tana
    un tunnel a gomito che si perde nel buio; il fondo è la superficie della sabbia (che scivola giù nella tana
    della Madre); i massi sono roccia aggiunta. Il rumore fa la roccia scavata dal mare; i dettagli fini li fa lo
    shader (bump). La sabbia è un attributo dei vertici ('sabbia') che lo shader usa per cambiare materiale;
  - la vita: anemoni e spugne sulle pareti, alghe a nastro sul fondo e sulle cenge, due banchi di pesciolini, i
    ciottoli; la neve marina (particelle) solo nelle anteprime (nel gioco le fa il motore);
  - i pezzi del parco trascinati giù dalla Madre: boe, pezzi di scivoli a tubo, il cartello di Splashland;
  - a ogni apertura una cosa del bambino appesa alla roccia (proposta): il salvagente a paperella di Gulpy, le
    ciocche coi codini e gli elastici rosa di Molly, il pesciolino luminoso di Hatch, la striscia di biglietti di
    Robin, la trombetta da festa di Archie, la cuffia a fiori di Lampy, gli occhialini neri di Fangy.

Luci (light group come la baia, common.py):
  - ambient: l'alba che scende dal pozzo (un faretto con le caustiche, il cielo chiaro della superficie) e i raggi
    nell'acqua (coni emissivi trasparenti, solo per la camera), più il pesciolino di Hatch che brilla da solo;
  - lantern: la torcia del sub. Nel panorama è una luce puntiforme sull'occhio, che illumina tutto attorno: il
    motore la ritaglia con il cono attorno allo sguardo e la accende o spegne. Nelle anteprime prospettiche è un
    faretto sulla camera.

L'acqua torbida non è un volume (costerebbe troppo): nel passo dati c'è la distanza (mist) e acqua() la cuoce
dopo il render nei passi di luce: l'assorbimento (il rosso sparisce per primo) e la luce diffusa dall'acqua
(una sfocatura larga della luce ambiente: vicino al pozzo l'acqua brilla, in fondo alla tana della Madre è nero).
"""
from __future__ import annotations

import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

import deco
import sdf
from common import collection, set_lightgroup
from geo import catmull, circle_profile, lathe, rect_profile, sweep, tube
from nodes import material, world

COL = 'grotta'
F = np.float32

OCCHIO = (0.0, 0.0, 0.0)          # l'occhio del sub nel panorama della grotta grande
LAT_MIN_G, LAT_MAX_G = -62.0, 62.0  # il panorama della grotta guarda più in alto e più in basso del mondo
MIST_DEPTH = 40.0                  # metri: il passo mist è lineare, 0 sull'occhio e 1 a MIST_DEPTH

# la direzione della luce dell'alba che scende dal pozzo (verso il basso, un po' in avanti)
SOLE = np.array((-0.10, 0.30, -1.0)) / np.linalg.norm((-0.10, 0.30, -1.0))
POZZO_BASSO = np.array((1.3, -4.0, 3.2))   # dove il pozzo sbuca nel soffitto della sala
POZZO_ALTO = np.array((2.6, -6.2, 15.0))   # oltre il bordo del campo: lì la roccia resta aperta sulla superficie

# Le tane: (chi, yaw dall'occhio in gradi, quota della bocca, raggio, piega del tunnel (gradi, + a destra)).
# L'ordine attorno alla sala segue l'arrivo dei mostri, da sinistra a destra (proposta).
TANE = [
    ('gulpy', -128.0, -0.7, 1.25, 35.0),
    ('molly', -88.0, 0.5, 1.00, -30.0),
    ('hatch', -48.0, -1.7, 0.80, 25.0),     # bassa e stretta, quasi sul fondo: un nascondiglio
    ('robin', 46.0, -1.1, 1.10, -30.0),
    ('archie', 88.0, 0.9, 1.05, 30.0),
    ('lampy', 128.0, 1.8, 0.95, -25.0),     # alta, vicino al soffitto: lei dorme attaccata in alto
    ('fangy', -160.0, -0.4, 0.95, 30.0),
]
MADRE = dict(a=(0.0, 14.5, -2.9), b=(0.0, 21.0, -6.2), c=(2.0, 28.0, -8.5), r=(3.7, 4.2, 3.6))


def _dir(yaw):
    y = math.radians(yaw)
    return np.array((math.sin(y), math.cos(y), 0.0))


# ───────────────────────── la roccia ─────────────────────────

_N = sdf.Noise3(907)
_N2 = sdf.Noise3(913)


def fondo_z(x, y):
    """La quota della sabbia: scende piano verso il fondo della sala, poi scivola giù nella tana della Madre;
    qualche duna morbida."""
    z = -2.6 - 0.05 * y
    z = z - 0.5 * np.maximum(y - 11.0, 0.0) ** 1.25
    p = np.stack([x * 0.35, y * 0.35, np.zeros_like(x)], 1).astype(F)
    return (z + 0.35 * _N2(p, 1.0, 2)).astype(F)


def tunnel(t):
    """Il tunnel di una tana: dritto dalla sala oltre la parete, poi piega di lato e scende nel buio."""
    chi, yaw, z, r, piega = t
    d = _dir(yaw)
    a = d * 3.0 + (0, 0, z)
    b = d * 16.5 + (0, 0, z - 0.3)
    c = b + _dir(yaw + piega) * 5.0 + (0, 0, -1.6)
    return a, b, c, r


def _massi():
    """Massi caduti dal soffitto sul fondo della sala: (centro, raggi)."""
    rr = np.random.default_rng(31)
    out = []
    for x, y, s in ((-4.6, 3.0, 1.2), (3.8, 9.5, 1.4), (6.0, -1.0, 0.9), (-2.2, 11.0, 0.8), (-6.8, 7.5, 1.3),
                    (2.4, -2.5, 0.6), (-1.0, 6.2, 0.5), (5.2, 4.8, 0.55), (-3.3, -3.6, 0.7)):
        zf = float(fondo_z(np.array([x], F), np.array([y], F))[0])
        out.append(((x, y, zf + s * 0.15), (s * rr.uniform(1.0, 1.4), s * rr.uniform(0.9, 1.3), s * 0.75)))
    return out


def cavita(p):
    """Il campo della grotta: < 0 nell'acqua, > 0 nella roccia (con il rumore della roccia scavata)."""
    p = np.asarray(p, F)
    d = sdf.ellipsoid((0.0, 3.0, 0.6), (7.0, 10.0, 4.8))(p)
    for c, r in (((-5.0, -1.5, 0.2), (4.0, 5.0, 3.8)), ((5.4, 5.5, -0.3), (4.0, 5.6, 4.0)),
                 ((-4.0, 9.0, 0.0), (4.2, 5.0, 4.0)), ((0.5, -5.0, 1.2), (4.5, 3.5, 3.4))):
        d = sdf.smin(d, sdf.ellipsoid(c, r)(p), 2.0)
    d = sdf.smin(d, sdf.round_cone(POZZO_BASSO, POZZO_ALTO, 2.4, 1.7)(p), 1.4)
    for t in TANE:
        a, b, c, r = tunnel(t)
        tn = np.minimum(sdf.capsule(a, b, r)(p), sdf.capsule(b, c, r * 0.9)(p))
        d = sdf.smin(d, tn, 0.7)
    m = MADRE
    tm = sdf.round_cone(m['a'], m['b'], m['r'][0], m['r'][1])(p)
    tm = np.minimum(tm, sdf.round_cone(m['b'], m['c'], m['r'][1], m['r'][2])(p))
    d = sdf.smin(d, tm, 0.8)        # raccordo stretto: la bocca ha un orlo, non è il proseguimento della sala
    # la roccia scavata dal mare: grandi bozze, poi le increspature e qualche cengia orizzontale
    n = 0.62 * _N(p, 3.2, 3) + 0.16 * _N(p + 50.0, 0.9, 2)
    cengie = 0.10 * np.sin(p[:, 2] * 3.1 + 2.0 * _N(p, 2.0, 1))
    d = d + n + cengie
    # la sabbia (il fondo) taglia l'acqua; i massi sono roccia
    d = sdf.smax(d, fondo_z(p[:, 0], p[:, 1]) - p[:, 2], 0.5)
    for c, r in _massi():
        ms = sdf.ellipsoid(c, r)(p) + 0.25 * _N(p + 9.0, 0.8, 2) * r[0]
        d = sdf.smax(d, -ms, 0.3)
    return d.astype(F)


def roccia(p):
    return -cavita(p)


def mesh_obj(name, verts, faces, attrs=None):
    """Mesh grande da array numpy (molto più veloce di from_pydata), con attributi float per vertice."""
    verts = np.asarray(verts, F)
    faces = np.asarray(faces, np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.ravel())
    me.loops.add(faces.size)
    me.loops.foreach_set('vertex_index', faces.ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set('loop_start', np.arange(0, faces.size, 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(len(faces), bool))
    for k, v in (attrs or {}).items():
        a = me.attributes.new(k, 'FLOAT', 'POINT')
        a.data.foreach_set('value', np.asarray(v, F))
    me.update()
    ob = bpy.data.objects.new(name, me)
    collection(COL).objects.link(ob)
    set_lightgroup(ob, 'ambient')
    return ob


def build_rock(res=0.08):
    """La roccia della grotta (un'unica mesh). Restituisce (oggetto, vertici, normali, sabbia)."""
    import time
    t = time.time()
    v, f, n = sdf.mesh_banded(roccia, (-24.0, -22.0, -14.0), (24.0, 33.5, 13.0), res=res, coarse=4)
    zf = fondo_z(v[:, 0], v[:, 1])
    sab = np.clip((0.45 - (v[:, 2] - zf)) / 0.35, 0, 1) * np.clip((n[:, 2] - 0.45) / 0.35, 0, 1)
    ob = mesh_obj('GrottaRoccia', v, f, {'sabbia': sab})
    ob.data.materials.append(rock_material())
    ob.pass_index = 3
    print('[grotte] roccia: %d vertici, %d triangoli, %.0f s' % (len(v), len(f), time.time() - t), flush=True)
    return ob, v, n, sab


def rock_material():
    """Roccia scura e bagnata (lucida d'acqua), con la patina d'alghe sulle facce in su, chiazze di alghe
    calcaree rosate e qualche venatura chiara; la sabbia grigia e increspata dove l'attributo 'sabbia' è 1."""
    m = bpy.data.materials.get('GrottaRocciaMat')
    if m:
        return m
    m, g = material('GrottaRocciaMat')
    co = g.texcoord('Object')
    nz = g.sep(g.geometry('Normal'))[2]
    big = g.noise(co, scale=0.35, detail=4.0, rough=0.6).fac
    mid = g.noise(co, scale=2.2, detail=6.0, rough=0.62, distortion=0.3).fac
    cell = g.voronoi(co, scale=3.0, feature='DISTANCE_TO_EDGE')
    pits = g.voronoi(co, scale=11.0, feature='F1')
    # la roccia: quasi nera, un po' verde-bruna, con le facce più chiare dove sporgono
    rock = g.ramp(g.add(g.mul(big, 0.6), g.mul(mid, 0.4)),
                  [(0.30, (0.018, 0.020, 0.020)), (0.55, (0.040, 0.040, 0.036)), (0.75, (0.070, 0.064, 0.055))])
    vene = g.smoothstep(0.015, 0.0, cell)
    rock = g.mix(g.mul(g.mul(vene, g.smoothstep(0.6, 0.75, big)), 0.6), rock, (0.075, 0.072, 0.065))
    # patina d'alghe sulle facce che guardano in su
    patina = g.mul(g.smoothstep(0.25, 0.75, nz), g.smoothstep(0.35, 0.6, mid))
    rock = g.mix(patina, rock, (0.035, 0.050, 0.020))
    # chiazze rosate di alghe calcaree (poche: un colore malato nel buio)
    calc = g.mul(g.smoothstep(0.66, 0.74, g.noise(g.mapping(co, loc=(7, 3, 1)), scale=1.4, detail=5.0).fac),
                 g.smoothstep(0.6, 0.0, nz))
    rock = g.mix(calc, rock, (0.20, 0.07, 0.09))
    h_rock = g.add(g.mul(mid, 0.6), g.add(g.mul(cell, 0.8), g.mul(g.smoothstep(0.0, 0.12, pits), 0.25)))
    rough = g.mixf(patina, g.map_range(mid, 0.3, 0.7, 0.22, 0.45), 0.7)
    # la sabbia: grigia, increspata dalla corrente, con puntini scuri
    _, rip = g.wave(g.mapping(co, rot=(0, 0, 0.5)), scale=1.6, distortion=4.0, detail=3.0, detail_scale=0.8)
    grani = g.noise(co, scale=60.0, detail=2.0).fac
    sand = g.mix(g.smoothstep(0.55, 0.7, grani), (0.15, 0.145, 0.125), (0.07, 0.066, 0.058))
    sand = g.mix(g.mul(big, 0.6), sand, (0.08, 0.08, 0.068))
    sab = g.smoothstep(0.2, 0.8, g.attr('sabbia'))
    col = g.mix(sab, rock, sand)
    h = g.mixf(sab, h_rock, g.add(g.mul(rip, 0.6), g.mul(grani, 0.15)))
    g.output_material(g.principled(color=col, rough=g.mixf(sab, g.add(rough, 0.12), 0.85), spec=0.45,
                                   normal=g.bump(h, strength=g.mixf(sab, 0.45, 0.25), distance=0.03)))
    return m


# ───────────────────────── materiali piccoli ─────────────────────────

def _mat(name, build):
    m = bpy.data.materials.get(name)
    return m if m else build(name)


def plastica(name, color, rough=0.35, melma=0.45, color2=None, stripes=None):
    """Plastica del parco, sbiadita e coperta di melma verde-bruna a chiazze. color2/stripes: bande lungo z
    (oggetto) di passo stripes metri, per le boe."""
    def b(n):
        m, g = material(n)
        co = g.texcoord('Object')
        col = color
        if color2 is not None:
            col = g.mix(g.smoothstep(stripes * 0.45, stripes * 0.55, g.math('PINGPONG', g.sep(co)[2], stripes)),
                        color, color2)
        sl = g.smoothstep(1.0 - melma, 1.0 - melma + 0.25, g.noise(co, scale=5.0, detail=8.0, rough=0.7, distortion=0.8).fac)
        col = g.mix(g.mul(sl, 0.8), col, g.mix(0.5, col, (0.035, 0.045, 0.02)))
        g.output_material(g.principled(color=col, rough=g.mixf(sl, rough, 0.6), coat=0.3, coat_rough=0.2,
                                       normal=g.bump(g.noise(co, scale=25.0, detail=3.0).fac, strength=0.1, distance=0.004)))
        return m
    return _mat(name, b)


def semplice(name, color, rough=0.5, metal=0.0, sss=0.0, coat=0.0, emission=None, strength=0.0):
    def b(n):
        m, g = material(n)
        kw = dict(color=color, rough=rough, metal=metal, coat=coat)
        if sss:
            kw.update(sss=sss, sss_radius=(1.0, 0.5, 0.3), sss_scale=0.02)
        if emission is not None:
            kw.update(emission=emission, emission_strength=strength)
        g.output_material(g.principled(**kw))
        return m
    return _mat(name, b)


def per_oggetto(name, rough=0.55, sss=0.4, tips=None):
    """Materiale col colore preso dall'oggetto (Object Info): anemoni, spugne, alghe. tips: schiarisce verso
    l'alto (coordinate oggetto z), per le punte dei tentacoli."""
    def b(n):
        m, g = material(n)
        info = g.node('ShaderNodeObjectInfo')
        col = g.out(info, 'Color')
        rnd = g.out(info, 'Random')
        col = g.hsv(col, h=g.map_range(rnd, 0, 1, 0.47, 0.53), s=1.0, v=g.map_range(rnd, 0, 1, 0.8, 1.15))
        if tips:
            z = g.sep(g.texcoord('Object'))[2]
            col = g.mix(g.smoothstep(tips[0], tips[1], z), col, g.mix(0.5, col, (0.9, 0.85, 0.8)))
        co = g.texcoord('Object')
        g.output_material(g.principled(color=col, rough=rough, sss=sss, sss_radius=(1.0, 0.45, 0.3), sss_scale=0.03,
                                       normal=g.bump(g.noise(co, scale=40.0, detail=2.0).fac, strength=0.15, distance=0.003)))
        return m
    return _mat(name, b)


def alga_material():
    """Le alghe a nastro: verde oliva e bruno, traslucide (controluce dal pozzo si accendono)."""
    def b(n):
        m, g = material(n)
        info = g.node('ShaderNodeObjectInfo')
        col = g.out(info, 'Color')
        co = g.texcoord('Object')
        vena = g.noise(g.mapping(co, scale=(30.0, 30.0, 2.0)), scale=1.0, detail=3.0).fac
        col = g.mix(g.mul(vena, 0.5), col, g.mix(0.5, col, (0.02, 0.02, 0.0)))
        surf = g.principled(color=col, rough=0.4, spec=0.5)
        tr = g.translucent(g.mix(0.4, col, (0.25, 0.3, 0.05)))
        g.output_material(g.mix_shader(0.35, surf, tr))
        return m
    return _mat('GrottaAlga', b)


def corda_material():
    return semplice('GrottaCorda', (0.05, 0.045, 0.035), rough=0.85)


# ───────────────────────── utilità di piazzamento ─────────────────────────

def istanza(name, mesh, loc, normal=(0, 0, 1), spin=0.0, scale=1.0, mat=None, color=None):
    ob = bpy.data.objects.new(name, mesh)
    collection(COL).objects.link(ob)
    q = Vector((0, 0, 1)).rotation_difference(Vector(normal).normalized()) @ Quaternion((0, 0, 1), spin)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = q
    ob.location = loc
    ob.scale = (scale,) * 3 if np.isscalar(scale) else scale
    if mat is not None and not mesh.materials:
        mesh.materials.append(mat)
    if color is not None:
        ob.color = (*color, 1.0)
    set_lightgroup(ob, 'ambient')
    return ob


def da_oggetto(ob):
    """Copia la mesh di un oggetto costruito con i helper (geo) e lo toglie dalla scena: diventa un modello per le
    istanze."""
    me = ob.data
    bpy.data.objects.remove(ob)
    return me


def dentro_le_tane(P, margine=0.6):
    """Vero per i punti dentro i tunnel delle tane (oltre la bocca): lì niente anemoni né spugne, la bocca deve
    restare un buco nero e pulito dove si legge la cosa appesa."""
    P = np.asarray(P, F)
    out = np.zeros(len(P), bool)
    for t in TANE:
        a, b, c, r = tunnel(t)
        d = (b - a) / np.linalg.norm(b - a)
        start = a + d * 2.0
        for p0, p1 in ((start, b), (b, c)):
            ab = p1 - p0
            h = np.clip(((P - p0) @ ab) / float(ab @ ab), 0, 1)
            dist = np.linalg.norm(P - p0 - h[:, None] * ab, axis=1)
            out |= dist < r + margine
    return out


def campiona_pareti(v, n, sab, count, seed, dmin=2.5, dmax=12.5, zmin=-6.0, zmax=5.0, nz=(-1.0, 1.0), cluster=None):
    """Punti (posizione, normale) sulla roccia, lontano dalla sabbia, a distanza [dmin, dmax] dall'occhio.
    cluster=(centri, per_centro, raggio): a gruppi, come crescono davvero."""
    rr = np.random.default_rng(seed)
    d = np.linalg.norm(v - np.array(OCCHIO), axis=1)
    ok = (sab < 0.05) & (d > dmin) & (d < dmax) & (v[:, 2] > zmin) & (v[:, 2] < zmax) & (n[:, 2] >= nz[0]) & (n[:, 2] <= nz[1])
    ok &= ~dentro_le_tane(v)
    idx = np.nonzero(ok)[0]
    if cluster is None:
        pick = rr.choice(idx, size=min(count, len(idx)), replace=False)
        return v[pick], n[pick]
    from scipy.spatial import cKDTree
    ncent, per, rad = cluster
    cent = rr.choice(idx, size=ncent, replace=False)
    tree = cKDTree(v[idx])
    out = []
    for c in cent:
        near = tree.query_ball_point(v[c], rad)
        if near:
            out += list(rr.choice(near, size=min(per, len(near)), replace=False))
    out = idx[np.array(out, int)]
    return v[out], n[out]


# ───────────────────────── la vita ─────────────────────────

def anemone_mesh(name, seed, tent=22, h=0.12, r=0.04, lt=0.09):
    """Un anemone: la colonna (lathe) e la corona di tentacoli che si piegano in fuori e ricadono."""
    rr = np.random.default_rng(seed)
    obs = [lathe(name + 'Col', [(r * 1.25, -0.01), (r, 0.0), (r * 0.85, h * 0.5), (r * 1.05, h), (r * 0.6, h * 1.04)],
                 n=14, col=COL, close_top=True)]
    for k in range(tent):
        a = 2 * math.pi * k / tent + rr.normal(0, 0.08)
        ring = r * (0.65 if k % 2 else 0.9)
        L = lt * rr.uniform(0.7, 1.2)
        pts = []
        for t in np.linspace(0, 1, 7):
            out = ring + L * 0.55 * t
            up = L * (0.8 * t - 0.75 * t * t * rr.uniform(0.6, 1.2))
            pts.append((out * math.cos(a), out * math.sin(a), h + up))
        obs.append(tube(name + 'Ten', pts, 0.0055, n=6, col=COL, taper=0.35))
    me = _unisci(name, obs)
    return me


def _unisci(name, obs):
    """Unisce gli oggetti in una mesh sola (per le istanze) e li toglie dalla scena."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    me = ob.data
    me.name = name
    bpy.data.objects.remove(ob)
    return me


def spugna_mesh(name, seed):
    """Un ciuffo di spugne a tubo: 3-5 canne aperte in cima, scure dentro."""
    rr = np.random.default_rng(seed)
    obs = []
    for k in range(rr.integers(3, 6)):
        r = rr.uniform(0.025, 0.05)
        h = rr.uniform(0.10, 0.32)
        x, y = rr.normal(0, 0.05, 2)
        prof = [(r * 1.2, -0.02), (r, 0.0), (r * 1.1, h * 0.6), (r * 1.25, h), (r * 0.9, h * 0.98), (r * 0.8, h * 0.3)]
        o = lathe(name + 'T', prof, n=12, col=COL)
        o.location = (x, y, 0)
        o.rotation_euler = (rr.normal(0, 0.15), rr.normal(0, 0.15), 0)
        obs.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return _unisci(name, obs)


def sasso_mesh(name, seed, sub=2):
    """Un ciottolo: icosfera deformata e schiacciata."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1.0)
    ob = bpy.context.object
    rr = np.random.default_rng(seed)
    k = rr.uniform(0.6, 1.0, 3)
    for vtx in ob.data.vertices:
        c = np.array(vtx.co, F)[None]
        s = 1.0 + 0.18 * float(_N(c * 1.3 + seed, 1.0, 2)[0])
        vtx.co = Vector(c[0] * s * (1.0, k[1], k[2] * 0.6))
    bpy.ops.object.shade_smooth()
    me = ob.data
    me.name = name
    bpy.data.objects.remove(ob)
    return me


def pesce_mesh(name, L=0.09):
    """Un pesciolino argentato: fuso compresso ai lati e la coda a forbice (lungo +Y)."""
    n_a, ys = 10, np.linspace(-0.5, 0.5, 12) * L
    verts, faces = [], []
    for i, y in enumerate(ys):
        t = (y / L) + 0.5
        h = L * 0.13 * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.8 + 1e-4
        w = h * 0.45
        for k in range(n_a):
            a = 2 * math.pi * k / n_a
            verts.append((w * math.cos(a), y, h * math.sin(a)))
    for i in range(len(ys) - 1):
        for k in range(n_a):
            a, b = i * n_a + k, i * n_a + (k + 1) % n_a
            faces.append((a, b, b + n_a, a + n_a))
    c = len(verts)
    y0 = ys[0]
    verts += [(0, y0, 0), (0, y0 - L * 0.25, L * 0.14), (0, y0 - L * 0.2, 0), (0, y0 - L * 0.25, -L * 0.14)]
    faces += [(c, c + 1, c + 2), (c, c + 2, c + 3)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for p in me.polygons:
        p.use_smooth = True
    return me


def build_life(v, n, sab):
    """Anemoni, spugne, alghe, ciottoli, i banchi di pesciolini."""
    rr = np.random.default_rng(5)
    # anemoni: a gruppi sulle pareti e sulle cenge; colori pallidi e malati
    an_mat = per_oggetto('GrottaAnemone', rough=0.45, sss=0.6, tips=(0.10, 0.2))
    modelli = [anemone_mesh('Anemone%d' % k, 40 + k, tent=18 + 4 * k, h=0.08 + 0.03 * k, r=0.03 + 0.01 * k) for k in range(3)]
    colori = [(0.55, 0.36, 0.34), (0.58, 0.55, 0.48), (0.55, 0.32, 0.16), (0.40, 0.30, 0.40), (0.50, 0.42, 0.38)]
    P, N = campiona_pareti(v, n, sab, 0, 11, nz=(-0.3, 1.0), cluster=(24, 6, 0.6))
    for k, (p, nn) in enumerate(zip(P, N)):
        istanza('Anemone', modelli[k % 3], tuple(p - nn * 0.01), tuple(nn), rr.uniform(0, 6.28), rr.uniform(1.2, 2.6),
                an_mat, colori[(k // 6) % len(colori)])
    # spugne a tubo, gialle e arancio spente
    sp_mat = per_oggetto('GrottaSpugna', rough=0.8, sss=0.2)
    modelli = [spugna_mesh('Spugna%d' % k, 70 + k) for k in range(3)]
    P, N = campiona_pareti(v, n, sab, 0, 12, nz=(-0.2, 1.0), cluster=(12, 3, 0.8))
    for k, (p, nn) in enumerate(zip(P, N)):
        c = [(0.34, 0.25, 0.08), (0.30, 0.15, 0.06), (0.28, 0.27, 0.19)][k % 3]
        istanza('Spugna', modelli[k % 3], tuple(p - nn * 0.02), tuple(nn), rr.uniform(0, 6.28), rr.uniform(0.8, 2.0),
                sp_mat, c)
    # alghe a nastro: a ciuffi sulla sabbia vicino alle pareti e sulle cenge
    build_alghe(v, n, sab)
    # ciottoli e conchiglie rotte sul fondo
    sa_mat = per_oggetto('GrottaCiottolo', rough=0.5, sss=0.0)
    modelli = [sasso_mesh('Ciottolo%d' % k, 90 + k) for k in range(5)]
    cnt = 0
    while cnt < 420:
        x, y = rr.uniform(-9, 9), rr.uniform(-7, 13)
        zf = float(fondo_z(np.array([x], F), np.array([y], F))[0])
        if cavita(np.array([[x, y, zf + 0.25]], F))[0] > -0.1:
            continue
        s = rr.uniform(0.025, 0.10) if rr.random() < 0.9 else rr.uniform(0.12, 0.25)
        g = rr.uniform(0.05, 0.16)
        istanza('Ciottolo', modelli[cnt % 5], (x, y, zf + s * 0.2), (rr.normal(0, 0.2), rr.normal(0, 0.2), 1),
                rr.uniform(0, 6.28), s, sa_mat, (g, g * 0.95, g * 0.85))
        cnt += 1
    build_banchi()


def build_alghe(v, n, sab):
    rr = np.random.default_rng(17)
    mat = alga_material()
    # i piedi: punti di sabbia vicino alle pareti (sab alto, ma con roccia attorno) e cenge (normale in su)
    d = np.linalg.norm(v, axis=1)
    piedi = np.nonzero((sab > 0.6) & (d > 3.0) & (d < 12.0))[0]
    cenge = np.nonzero((sab < 0.05) & (n[:, 2] > 0.8) & (d > 3.0) & (d < 11.0))[0]
    centri = list(rr.choice(piedi, 14, replace=False)) + list(rr.choice(cenge, 10, replace=False))
    k = 0
    for c in centri:
        base = v[c]
        for j in range(rr.integers(4, 10)):
            p0 = base + np.array((*rr.normal(0, 0.25, 2), -0.05))
            L = rr.uniform(0.5, 2.3)
            w = rr.uniform(0.04, 0.10)
            ph = rr.uniform(0, 6.28)
            lean = rr.normal(0, 0.25, 2)
            pts = []
            for t in np.linspace(0, 1, 16):
                sway = 0.18 * L * t * math.sin(ph + t * 5.0)
                pts.append(p0 + np.array((lean[0] * t * L + sway, lean[1] * t * L + 0.4 * sway, t * L)))
            prof = rect_profile(w, 0.004)
            ob = sweep('Alga', pts, prof, col=COL, cap=False, up=(math.cos(ph), math.sin(ph), 0),
                       scale=np.linspace(0.5, 1.0, 16) ** 0.5 * np.concatenate([np.ones(12), np.linspace(1, 0.15, 4)]))
            ob.data.materials.append(mat)
            ob.color = (*[(0.10, 0.12, 0.03), (0.14, 0.09, 0.03), (0.07, 0.10, 0.04)][k % 3], 1.0)
            set_lightgroup(ob, 'ambient')
            k += 1


def build_banchi():
    """Due banchi di pesciolini: uno che gira in tondo a mezz'acqua, uno che fila lungo la parete destra."""
    rr = np.random.default_rng(23)
    me = pesce_mesh('Pesciolino')
    mat = semplice('GrottaPesciolino', (0.55, 0.60, 0.60), rough=0.28, metal=0.7)
    me.materials.append(mat)
    def pesce(p, dirv):
        ob = bpy.data.objects.new('Pesciolino', me)
        collection(COL).objects.link(ob)
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = Vector((0, 1, 0)).rotation_difference(Vector(dirv).normalized())
        ob.location = tuple(p)
        ob.scale = (rr.uniform(0.8, 1.25),) * 3
        set_lightgroup(ob, 'ambient')
    c = np.array((-3.2, 6.5, 0.9))
    for k in range(200):
        a = rr.uniform(0, 2 * math.pi)
        R = 1.5 + rr.normal(0, 0.28)
        z = rr.normal(0, 0.35) + 0.25 * math.sin(a * 2)
        p = c + (R * math.cos(a), R * math.sin(a) * 0.8, z)
        pesce(p, (-math.sin(a), math.cos(a) * 0.8, rr.normal(0, 0.1)))
    for k in range(140):
        t = rr.uniform(0, 1)
        p = np.array((5.2 - 1.5 * t, -1.0 + 7.0 * t, 1.6 + 0.6 * math.sin(t * 4))) + rr.normal(0, 0.3, 3) * (1, 1, 0.5)
        pesce(p, (-0.2 + rr.normal(0, 0.1), 1.0, rr.normal(0, 0.1)))


def build_neve(count=2600, radius=9.0, seed=3, center=OCCHIO):
    """La neve marina: puntini sospesi attorno alla camera (solo per le anteprime: nel gioco li fa il motore)."""
    rr = np.random.default_rng(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.0)
    ob = bpy.context.object
    me = ob.data
    bpy.data.objects.remove(ob)
    me.materials.append(semplice('GrottaNeve', (0.55, 0.58, 0.52), rough=0.9, sss=0.0))
    obs = []
    c = np.array(center)
    while len(obs) < count:
        p = c + rr.uniform(-radius, radius, 3)
        if np.linalg.norm(p - c) > radius or cavita(p[None].astype(F))[0] > -0.05:
            continue
        o = bpy.data.objects.new('Neve', me)
        collection(COL).objects.link(o)
        o.location = tuple(p)
        o.scale = (rr.uniform(0.003, 0.011),) * 3
        o.visible_shadow = False
        o.visible_diffuse = False
        o.visible_glossy = False
        set_lightgroup(o, 'ambient')
        obs.append(o)
    return obs


# ───────────────────────── i pezzi del parco ─────────────────────────

def poggia(x, y, sink=0.0):
    return float(fondo_z(np.array([x], F), np.array([y], F))[0]) - sink


def boa(name, loc, r=0.33):
    import geo
    o = geo.sphere(name, r, loc, segs=28, rings=14, col=COL)
    o.data.materials.append(plastica('GrottaBoa', (0.42, 0.035, 0.02), color2=(0.62, 0.60, 0.55), stripes=0.22, melma=0.5))
    rg = geo.cylinder(name + 'Anello', 0.05, 0.12, (loc[0], loc[1], loc[2] - r - 0.04), verts=12, col=COL)
    rg.data.materials.append(semplice('GrottaRuggine', (0.16, 0.06, 0.02), rough=0.8))
    for ob in (o, rg):
        set_lightgroup(ob, 'ambient')
    return [o, rg]


def scivolo(name, pts, color, r=0.5):
    """Un pezzo di scivolo a tubo: aperto alle due estremità (si vede dentro)."""
    ob = tube(name, catmull(pts, 8), r, n=28, col=COL, cap=False)
    ob.data.materials.append(plastica(name + 'Mat', color, rough=0.3, melma=0.4))
    inner = tube(name + 'Dentro', catmull(pts, 8), r * 0.92, n=28, col=COL, cap=False)
    inner.data.materials.append(plastica(name + 'Mat', color))
    # il bordo spezzato: un anello alle due bocche
    for o in (ob, inner):
        set_lightgroup(o, 'ambient')
    return [ob, inner]


def build_parco():
    """Le cose del parco che la Madre ha trascinato giù."""
    import geo
    obs = []
    # boe: una sul fondo, una che galleggia trattenuta dalla sua cima, una incastrata sotto il soffitto
    obs += boa('BoaFondo', (3.3, 3.6, poggia(3.3, 3.6) + 0.22))
    obs += boa('BoaSu', (-2.2, 8.2, 2.6))
    zf = poggia(-2.0, 8.0)
    obs.append(tube('BoaCima', catmull([(-2.0, 8.0, zf), (-2.3, 8.3, zf + 1.6), (-2.2, 8.2, 2.2)], 8), 0.012, n=6, col=COL))
    obs[-1].data.materials.append(corda_material())
    obs += boa('BoaSoffitto', (4.4, -1.6, 3.6), r=0.28)
    # pezzi di scivoli a tubo, coi colori di quelli del parco (landmarks.build_splashland)
    z1 = poggia(5.6, 8.0)
    obs += scivolo('ScivoloGiallo', [(4.4, 6.6, z1 + 0.3), (5.6, 8.2, z1 + 0.35), (6.0, 10.0, z1 + 0.45)], (0.75, 0.62, 0.10))
    z2 = poggia(-6.2, 2.0)
    obs += scivolo('ScivoloBlu', [(-5.4, 0.5, z2 + 0.2), (-6.4, 2.0, z2 + 1.0), (-6.9, 3.0, z2 + 2.6)], (0.10, 0.35, 0.65))
    z3 = poggia(2.2, 11.6)
    obs += scivolo('ScivoloRosso', [(1.4, 10.8, z3 + 0.25), (2.6, 11.8, z3 + 0.3)], (0.65, 0.12, 0.10), r=0.45)
    # il cartello di Splashland, inclinato e mezzo sepolto nella sabbia
    x, y = -3.4, 9.6
    z = poggia(x, y)
    rz = math.atan2(-x, y) + math.radians(12)     # il davanti (−Y locale) verso l'occhio
    board = geo.rbox('Cartello', (2.6, 0.07, 0.85), (0, 0, 0), bevel=0.02, col=COL)
    board.data.materials.append(plastica('CartelloTinta', (0.05, 0.30, 0.32), rough=0.5, melma=0.5))
    cu = bpy.data.curves.new('CartelloScritta', 'FONT')
    cu.body = 'SPLASHLAND'
    cu.font = deco.font('Limelight-Regular')
    cu.size = 0.42
    cu.extrude = 0.012
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    txt = bpy.data.objects.new('CartelloScritta', cu)
    collection(COL).objects.link(txt)
    txt.location = (0, -0.05, 0.02)
    txt.rotation_euler = (math.radians(90), 0, 0)
    txt.data.materials.append(plastica('CartelloLettere', (0.70, 0.12, 0.30), rough=0.4, melma=0.35))
    pali = [geo.cylinder('CartelloPalo', 0.05, 1.6, (sx, 0.06, -0.6), verts=10, col=COL) for sx in (-0.9, 0.9)]
    for p in pali:
        p.data.materials.append(semplice('GrottaRuggine', (0.16, 0.06, 0.02), rough=0.8))
    M = Matrix.Translation((x, y, z + 0.35)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(math.radians(-22), 4, 'X') @ Matrix.Rotation(math.radians(8), 4, 'Y')
    for o in [board, txt] + pali:
        o.matrix_world = M @ o.matrix_world
        set_lightgroup(o, 'ambient')
    obs += [board, txt] + pali
    return obs


# ───────────────────────── le aperture delle tane ─────────────────────────

def bocca(t):
    """Dove il tunnel della tana buca la parete della sala: (centro della bocca, punto d'appoggio sull'architrave,
    direzione del tunnel). Si cerca lungo l'asse il primo punto sopra la volta del tunnel che è roccia."""
    a, b, c, r = tunnel(t)
    d = (b - a) / np.linalg.norm(b - a)
    up = np.array((0.0, 0.0, 1.0))
    ts = np.linspace(0.0, 12.0, 241)
    q = a[None] + ts[:, None] * d[None] + up * (r + 0.25)
    rock = cavita(q.astype(F)) > 0
    i = int(np.argmax(rock)) if rock.any() else 120
    tm = ts[i] + 0.35
    centro = a + d * tm
    # l'appoggio: sali dall'asse finché trovi la roccia
    zs = np.linspace(0.0, r + 2.0, 200)
    col = centro[None] + zs[:, None] * up
    k = int(np.argmax(cavita(col.astype(F)) > 0))
    appoggio = centro + up * (zs[k] - 0.03)
    return centro, appoggio, d


def corda(name, a, b, sag=0.0):
    pts = [np.array(a) + (np.array(b) - np.array(a)) * t + np.array((0, 0, -sag * 4 * t * (1 - t))) for t in np.linspace(0, 1, 8)]
    o = tube(name, pts, 0.006, n=6, col=COL)
    o.data.materials.append(corda_material())
    set_lightgroup(o, 'ambient')
    return o


def sdf_obj(name, field, lo, hi, res, mat):
    v, f, _ = sdf.mesh(field, lo, hi, res=res)
    ob = mesh_obj(name, v, f)
    ob.data.materials.append(mat)
    return ob


def oggetto_gulpy():
    """Il salvagente a paperella (come quello che stringe il collo di Gulpy), appeso per la testa della papera."""
    c = np.array((0.0, 0.0, -0.62))
    R, r = 0.20, 0.08
    ring = sdf.displace(sdf.torus(c, R, r, axis='y'), lambda p: _N(p, 0.06, 2), 0.006)
    head = c + (0, 0, R + r * 0.3 + 0.10)
    duck = sdf.union(sdf.capsule(c + (0, 0, R + r * 0.4), head, 0.07), sdf.sphere(head, 0.095), k=0.05)
    beak = sdf.ellipsoid(head + (0, -0.10, -0.015), (0.06, 0.065, 0.02))
    eyes = sdf.union(*[sdf.sphere(head + (s * 0.05, -0.07, 0.035), 0.016) for s in (-1, 1)])
    giallo = plastica('PaperellaGialla', (0.86, 0.62, 0.10), rough=0.3, melma=0.5)
    obs = [sdf_obj('Paperella', sdf.union(ring, duck, k=0.03), c - 0.35, c + 0.45, 0.008, giallo),
           sdf_obj('PaperellaBecco', beak, head - 0.15, head + 0.15, 0.006, plastica('PaperellaBecco', (0.92, 0.33, 0.05))),
           sdf_obj('PaperellaOcchi', eyes, head - 0.12, head + 0.12, 0.005, semplice('PaperellaOcchi', (0.01, 0.01, 0.01), rough=0.2))]
    obs.append(corda('PaperellaCorda', (0, 0, 0), head + (0, 0, 0.08)))
    return obs


def oggetto_molly():
    """Due ciocche bagnate coi codini, legate dagli elastici rosa di Molly, appese a un filo."""
    rr = np.random.default_rng(8)
    obs = []
    capelli = semplice('MollyCapelli', (0.025, 0.018, 0.012), rough=0.3, coat=0.4)
    rosa = plastica('MollyElastico', (0.60, 0.07, 0.26), rough=0.4, melma=0.2)
    for s in (-1, 1):
        nodo = np.array((s * 0.14, 0.0, -0.22))
        obs.append(corda('MollyFilo%d' % s, (s * 0.05, 0, 0), nodo + (0, 0, 0.02), sag=0.02))
        for k in range(26):
            L = rr.uniform(0.32, 0.55)
            dx, dy = rr.normal(0, 0.012, 2)
            a = rr.uniform(0, 6.28)
            pts = [nodo + (dx * (1 + 4 * t) + 0.02 * t * math.cos(a) + 0.015 * math.sin(t * 7 + a),
                           dy * (1 + 4 * t) + 0.02 * t * math.sin(a), 0.03 - L * t) for t in np.linspace(0, 1, 9)]
            o = tube('MollyCiocca', pts, 0.0035, n=5, col=COL, taper=0.3)
            o.data.materials.append(capelli)
            obs.append(o)
        el = sdf_obj('MollyElastico', sdf.torus(nodo, 0.03, 0.011, axis='z'), nodo - 0.06, nodo + 0.06, 0.003, rosa)
        obs.append(el)
        pal = sdf.union(*[sdf.sphere(nodo + (0.03 * math.cos(a), 0.03 * math.sin(a), 0.0), 0.018) for a in (0.6, 3.6)])
        obs.append(sdf_obj('MollyPalline', pal, nodo - 0.07, nodo + 0.07, 0.003, rosa))
    for o in obs:
        set_lightgroup(o, 'ambient')
    return obs


def oggetto_hatch():
    """Il pesciolino luminoso del negozio del parco (quello che penzola davanti alla faccia di Hatch): acceso."""
    c = np.array((0.0, 0.0, -0.45))
    body = sdf.ellipsoid(c, (0.045, 0.10, 0.06))
    tail = sdf.ellipsoid(c + (0, 0.12, 0), (0.012, 0.05, 0.06))
    fins = sdf.ellipsoid(c + (0, 0.0, 0.06), (0.008, 0.04, 0.03))
    glow = _mat('HatchGiocattolo', lambda n: _glow(n))
    obs = [sdf_obj('HatchGiocattolo', sdf.union(body, tail, fins, k=0.012), c - 0.2, c + 0.2, 0.005, glow),
           sdf_obj('HatchOcchi', sdf.union(*[sdf.sphere(c + (s * 0.04, -0.05, 0.02), 0.011) for s in (-1, 1)]),
                   c - 0.1, c + 0.1, 0.003, semplice('HatchOcchiVernice', (0.02, 0.02, 0.03), rough=0.2)),
           corda('HatchFilo', (0, 0, 0), c + (0, 0, 0.06))]
    d = bpy.data.lights.new('HatchLuce', 'POINT')
    d.energy = 3.0
    d.color = (0.30, 1.0, 0.82)
    d.shadow_soft_size = 0.05
    lo = bpy.data.objects.new('HatchLuce', d)
    collection(COL).objects.link(lo)
    lo.location = tuple(c + (0, -0.12, 0))
    set_lightgroup(lo, 'ambient')
    obs.append(lo)
    return obs


def _glow(n):
    m, g = material(n)
    co = g.texcoord('Object')
    var = g.noise(co, scale=30.0).fac
    g.output_material(g.principled(color=(0.15, 0.75, 0.6), rough=0.3, emission=(0.20, 0.95, 0.75),
                                   emission_strength=g.map_range(var, 0, 1, 1.2, 2.2), coat=0.5))
    return m


def oggetto_robin():
    """La striscia dei biglietti della sala giochi di Robin, che pende attorcigliata."""
    pts = []
    for t in np.linspace(0, 1, 60):
        z = -0.95 * t
        pts.append((0.06 * math.sin(t * 9) + 0.10 * t, 0.05 * math.cos(t * 7), z))
    pts += [(0.1 + 0.07 * math.cos(a), 0.05 * math.sin(a), -0.95 - 0.05 * math.sin(a * 0.5)) for a in np.linspace(0, 4.5, 20)]
    pts = np.array(pts)
    ob = sweep('RobinBiglietti', pts, rect_profile(0.075, 0.002), col=COL, cap=False, up=(0, 1, 0))   # di piatto verso −Y
    # 'tick': i metri lungo la striscia, per le righe della perforazione
    seg = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    me = ob.data
    a = me.attributes.new('tick', 'FLOAT', 'POINT')
    a.data.foreach_set('value', np.repeat(seg, 4).astype(F))
    ob.data.materials.append(_mat('RobinBigliettiMat', _biglietti))
    set_lightgroup(ob, 'ambient')
    return [ob, corda('RobinChiodo', (0, 0, 0.02), (0, 0, -0.01))]


def _biglietti(n):
    m, g = material(n)
    tk = g.attr('tick')
    riga = g.smoothstep(0.004, 0.0, g.math('PINGPONG', g.add(tk, 0.0), 0.04))
    co = g.texcoord('Object')
    sl = g.smoothstep(0.55, 0.7, g.noise(co, scale=8.0, detail=4.0).fac)
    col = g.mix(riga, (0.80, 0.24, 0.02), (0.25, 0.04, 0.02))
    col = g.mix(sl, col, (0.20, 0.12, 0.04))
    g.output_material(g.principled(color=col, rough=0.7, sss=0.15, sss_radius=(1.0, 0.4, 0.2), sss_scale=0.01))
    return m


def oggetto_archie():
    """La trombetta da festa di Archie: il bocchino bianco e la lingua di carta a strisce arrotolata."""
    obs = []
    mp = lathe('ArchieBocchino', [(0.012, 0.0), (0.016, -0.04), (0.022, -0.09)], n=14, col=COL, close_top=True, close_bottom=True)
    mp.location = (0, 0, -0.08)
    mp.data.materials.append(plastica('ArchieBocchinoMat', (0.72, 0.70, 0.64), melma=0.3))
    obs.append(mp)
    pts = [(0, 0, -0.17), (0, -0.01, -0.30)]
    for a in np.linspace(0, 3.4 * math.pi, 50):
        rad = 0.10 * (1 - a / (3.8 * math.pi))
        pts.append((rad * math.sin(a), -0.01, -0.30 - 0.10 + rad * math.cos(a)))   # il ricciolo di piatto verso −Y
    pts = catmull(pts, 2)
    prof = [(0.028 * math.cos(t), 0.012 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 14, endpoint=False)]
    ob = sweep('ArchieTrombetta', pts, prof, col=COL, up=(0, 1, 0), scale=np.linspace(1.0, 0.7, len(pts)))
    ob.data.materials.append(_mat('ArchieCarta', _carta))
    obs.append(ob)
    obs.append(corda('ArchieLaccio', (0, 0, 0), (0, 0, -0.08)))
    for o in obs:
        set_lightgroup(o, 'ambient')
    return obs


def _carta(n):
    m, g = material(n)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    st = g.smoothstep(0.45, 0.55, g.math('PINGPONG', g.add(g.mul(z, 1.0), g.mul(y, 0.8)), 0.03))
    col = g.mix(st, (0.40, 0.03, 0.03), (0.70, 0.66, 0.58))
    sl = g.smoothstep(0.55, 0.7, g.noise(co, scale=10.0, detail=4.0).fac)
    col = g.mix(sl, col, (0.15, 0.13, 0.06))
    g.output_material(g.principled(color=col, rough=0.45, coat=0.4))
    return m


def oggetto_lampy():
    """La cuffia di gomma bianca coi fiori in rilievo, appesa per il cinturino."""
    c = np.array((0.0, 0.0, -0.40))
    R = 0.13
    cap = sdf.intersect(sdf.shell(sdf.ellipsoid(c, (R, R * 1.15, R)), 0.006), lambda p: c[2] - 0.01 - p[:, 2])
    cap = sdf.rotate(cap, sdf.rot_matrix('x', 180), center=c)    # la cupola in su
    rr = np.random.default_rng(4)
    fiori = []
    for k in range(13):
        th = rr.uniform(0.15, 1.35)
        ph = rr.uniform(0, 6.28)
        nrm = np.array((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph) * 1.15, math.cos(th)))
        cen = c + nrm * np.array((R, R * 1.15, R))
        # cinque petali sul piano tangente
        t1 = np.cross(nrm, (0, 0, 1) if abs(nrm[2]) < 0.9 else (1, 0, 0))
        t1 /= np.linalg.norm(t1)
        t2 = np.cross(nrm, t1)
        for j in range(5):
            a = 2 * math.pi * j / 5 + ph
            pc = cen + 0.018 * (math.cos(a) * t1 + math.sin(a) * t2)
            fiori.append(sdf.sphere(pc, 0.014))
    petali = sdf.union(*fiori)
    bianco = plastica('LampyCuffia', (0.72, 0.71, 0.66), rough=0.45, melma=0.4)
    obs = [sdf_obj('LampyCuffia', cap, c - 0.2, c + 0.2, 0.004, bianco),
           sdf_obj('LampyFiori', petali, c - 0.2, c + 0.2, 0.0035, _mat('LampyFioriMat', _fiori))]
    obs.append(corda('LampyCinturino', (0, 0, 0), c + (0, 0, R + 0.005), sag=0.0))
    return obs


def _fiori(n):
    m, g = material(n)
    info = g.texcoord('Object')
    v = g.voronoi(info, scale=14.0, out='Color')
    col = g.mix(g.smoothstep(0.45, 0.55, g.bw(v)), (0.70, 0.04, 0.32), (0.85, 0.35, 0.55))
    g.output_material(g.principled(color=col, rough=0.45, coat=0.3))
    return m


def oggetto_fangy():
    """Gli occhialini da piscina con le lenti dipinte di nero, appesi per l'elastico."""
    c = np.array((0.0, 0.0, -0.32))
    lenti = sdf.union(*[sdf.ellipsoid(c + (s * 0.055, 0, 0), (0.042, 0.026, 0.032)) for s in (-1, 1)])
    ponte = sdf.capsule(c + (-0.02, -0.005, 0.005), c + (0.02, -0.005, 0.005), 0.006)
    nero = semplice('FangyLenti', (0.008, 0.008, 0.01), rough=0.12, coat=1.0)
    obs = [sdf_obj('FangyOcchialini', lenti, c - 0.12, c + 0.12, 0.003, nero),
           sdf_obj('FangyPonte', ponte, c - 0.05, c + 0.05, 0.002, nero)]
    # l'elastico: dai due lati delle lenti sale ad arco fino all'appoggio
    pts = [(0.095 * math.cos(a), 0.01, c[2] + (-c[2]) * math.sin(a)) for a in np.linspace(math.pi, 0, 30)]
    o = tube('FangyElastico', pts, 0.008, n=6, col=COL)
    o.data.materials.append(semplice('FangyElasticoMat', (0.03, 0.05, 0.08), rough=0.6))
    obs.append(o)
    return obs


# più grandi del vero quelli piccoli, perché si leggano da lontano (come la trombetta di Archie)
SCALA = {'hatch': 1.7, 'fangy': 1.5, 'molly': 1.2, 'robin': 1.2}

OGGETTI = {'gulpy': oggetto_gulpy, 'molly': oggetto_molly, 'hatch': oggetto_hatch, 'robin': oggetto_robin,
           'archie': oggetto_archie, 'lampy': oggetto_lampy, 'fangy': oggetto_fangy}


def build_tane():
    """A ogni bocca la cosa del bambino, appesa all'architrave e girata verso l'occhio. Restituisce le bocche
    (per il manifest e per le camere delle anteprime)."""
    info = {}
    for t in TANE:
        chi = t[0]
        centro, appoggio, d = bocca(t)
        obs = OGGETTI[chi]()
        yaw = math.atan2(appoggio[0] - OCCHIO[0], appoggio[1] - OCCHIO[1])
        # un poco dentro la bocca e girato col davanti (−Y locale) verso l'occhio
        M = Matrix.Translation(Vector(appoggio)) @ Matrix.Rotation(-yaw, 4, 'Z') @ Matrix.Scale(SCALA.get(chi, 1.0), 4)
        for o in obs:
            o.matrix_world = M @ o.matrix_world
            set_lightgroup(o, 'ambient')
        info[chi] = {'bocca': centro, 'appoggio': appoggio, 'dir': d, 'raggio': t[3]}
    return info


# ───────────────────────── luci e acqua ─────────────────────────

def build_world():
    """Fuori dal pozzo: la superficie chiara dell'alba (si vede solo dal buco in alto)."""
    w, g = world('GrottaSuperficie')
    w.lightgroup = 'ambient'
    g.output_world(g.background((0.32, 0.62, 0.62), 2.2))
    w.mist_settings.start = 0.0
    w.mist_settings.depth = MIST_DEPTH
    w.mist_settings.falloff = 'LINEAR'
    return w


def build_alba(energy=26000.0, diffusa=3200.0):
    """L'alba che scende dal pozzo: un faretto con le caustiche (texture della luce) e i raggi nell'acqua."""
    d = bpy.data.lights.new('Alba', 'SPOT')
    d.energy = energy
    d.color = (0.72, 0.95, 0.90)
    d.spot_size = math.radians(34)
    d.spot_blend = 0.7
    d.shadow_soft_size = 0.8
    d.use_nodes = True
    nt = d.node_tree
    em = nt.nodes.get('Emission')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.feature = 'SMOOTH_F1'
    vo.inputs['Scale'].default_value = 26.0
    vo.inputs['Smoothness'].default_value = 0.3 if 'Smoothness' in vo.inputs else 0.3
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.0
    mr.inputs['From Max'].default_value = 0.6
    mr.inputs['To Min'].default_value = 1.9
    mr.inputs['To Max'].default_value = 0.45
    nt.links.new(tc.outputs['Normal'], vo.inputs['Vector'])
    nt.links.new(vo.outputs['Distance'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], em.inputs['Strength'])
    o = bpy.data.objects.new('Alba', d)
    collection(COL).objects.link(o)
    o.location = tuple(POZZO_ALTO - SOLE * 1.0 - np.array((0, 0, 2.0)))
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(Vector(SOLE))
    set_lightgroup(o, 'ambient')
    # la luce diffusa dall'acqua: una sfera grande e morbida sotto il pozzo (al posto del volume): le pareti vicine
    # all'imboccatura si vedono, in fondo alla sala si spegne e la tana della Madre resta nera
    d2 = bpy.data.lights.new('AlbaDiffusa', 'POINT')
    d2.energy = diffusa
    d2.color = (0.55, 0.85, 0.82)
    d2.shadow_soft_size = 2.5
    o2 = bpy.data.objects.new('AlbaDiffusa', d2)
    collection(COL).objects.link(o2)
    o2.location = (0.4, -1.2, 1.2)
    set_lightgroup(o2, 'ambient')
    # un filo di luce più avanti, perché il bordo della tana della Madre si stacchi dal suo buio
    d3 = bpy.data.lights.new('AlbaBordo', 'POINT')
    d3.energy = diffusa * 0.2
    d3.color = (0.45, 0.80, 0.80)
    d3.shadow_soft_size = 1.5
    o3 = bpy.data.objects.new('AlbaBordo', d3)
    collection(COL).objects.link(o3)
    o3.location = (0.0, 6.5, 0.8)
    set_lightgroup(o3, 'ambient')
    return o


def build_raggi(n=6, seed=2, top=None, spread=0.75, lunghezza=(8.5, 11.5), raggio=(0.35, 0.75), forza=0.045):
    """I raggi di luce nell'acqua torbida: coni emissivi e trasparenti, visibili solo alla camera, più tenui ai
    bordi (Layer Weight) e verso il fondo."""
    rr = np.random.default_rng(seed)
    m, g = material('GrottaRaggio')
    z = g.sep(g.texcoord('Generated'))[2]            # 0 in cima, 1 in fondo (vedi sotto)
    face = g.layer_weight(0.35, 'Facing')
    edge = g.pow(g.sub(1.0, face), 3.5)
    fade = g.mul(g.smoothstep(0.0, 0.12, z), g.smoothstep(1.0, 0.35, z))
    st = g.mul(g.mul(edge, fade), forza)
    g.output_material(g.add_shader(g.transparent(), g.emission((0.55, 0.85, 0.80), st)))
    obs = []
    top_c = POZZO_BASSO + np.array((0.0, 0.0, 2.2)) if top is None else np.asarray(top, float)
    for k in range(n):
        off = rr.normal(0, spread, 2)
        p0 = top_c + np.array((off[0], off[1], 0.0))
        L = rr.uniform(*lunghezza)
        r0 = rr.uniform(*raggio)
        dirv = SOLE + rr.normal(0, 0.03, 3)
        dirv /= np.linalg.norm(dirv)
        pts = [p0 + dirv * L * t for t in np.linspace(0, 1, 10)]
        ob = tube('Raggio', pts, r0, n=16, col=COL, cap=False, taper=1.6)
        ob.data.materials.append(m)
        ob.visible_shadow = False
        ob.visible_diffuse = False
        ob.visible_glossy = False
        ob.visible_transmission = False
        ob.visible_volume_scatter = False
        set_lightgroup(ob, 'ambient')
        obs.append(ob)
    return obs


def raggi():
    return [o for o in bpy.data.objects if o.name.startswith('Raggio')]


def render_con_raggi(exr, samples, size, data_passes=('Mist',), region=None):
    """Due render: la scena senza i raggi (i coni trasparenti rovinerebbero il passo mist: Cycles scrive i passi
    dati solo al primo incontro) e i soli raggi, con tutto il resto come maschera (holdout), senza rimbalzi e con
    pochi campioni (sono solo emissione). Restituisce i passi della scena con 'raggi' a parte."""
    from common import render
    import post
    sc = bpy.context.scene
    rg = raggi()
    for o in rg:
        o.visible_camera = False
    render(exr, samples, size, region=region, data_passes=data_passes)
    p = post.read_exr(exr)
    if not rg:
        return p
    salva = {o.name: (o.visible_camera, o.is_holdout) for o in bpy.data.objects if o.type in ('MESH', 'FONT', 'CURVE')}
    for o in bpy.data.objects:
        if o.type in ('MESH', 'FONT', 'CURVE'):
            o.is_holdout = not o.name.startswith('Raggio')
    for o in rg:
        o.visible_camera = True
    bounces = sc.cycles.max_bounces
    sc.cycles.max_bounces = 0
    exr_r = exr.replace('.exr', '_raggi.exr')
    render(exr_r, 8, size, region=region, groups=('ambient',), transparent=True, data_passes=(), denoise=False)
    sc.cycles.max_bounces = bounces
    for o in bpy.data.objects:
        if o.name in salva:
            o.visible_camera, o.is_holdout = salva[o.name]
    for o in rg:
        o.visible_camera = False
    p['raggi'] = post.read_exr(exr_r)['ambient']
    return p


def torcia_panorama(energy=260.0, occhio=OCCHIO):
    """La torcia nel panorama: una luce puntiforme sull'occhio (light group 'lantern'); il motore la ritaglia col
    cono attorno allo sguardo."""
    d = bpy.data.lights.new('Torcia', 'POINT')
    d.energy = energy
    d.color = (1.0, 0.93, 0.80)
    d.shadow_soft_size = 0.03
    o = bpy.data.objects.new('Torcia', d)
    collection(COL).objects.link(o)
    o.location = (occhio[0] + 0.15, occhio[1], occhio[2] - 0.12)
    set_lightgroup(o, 'lantern')
    return o


TORCIA_BLEND = 0.55     # il bordo del fascio della torcia nelle anteprime (1: sfumato del tutto)


def torcia_faretto(cam, target, energy=380.0, cone=42.0):
    """La torcia per le anteprime prospettiche: un faretto appena sotto e a destra della camera."""
    d = bpy.data.lights.new('TorciaFaretto', 'SPOT')
    d.energy = energy
    d.color = (1.0, 0.93, 0.80)
    d.spot_size = math.radians(cone)
    d.spot_blend = TORCIA_BLEND
    d.shadow_soft_size = 0.03
    o = bpy.data.objects.new('TorciaFaretto', d)
    collection(COL).objects.link(o)
    p = Vector(cam.location) + Vector((0.12, 0.0, -0.10))
    o.location = p
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(Vector(target) - p)
    set_lightgroup(o, 'lantern')
    return o


def build_grotta(neve=True, res=0.08):
    """Tutta la grotta grande. Restituisce le bocche delle tane."""
    build_world()
    # GROTTE_RES: roccia più grossolana per le prove veloci (es. 0.16)
    ob, v, n, sab = build_rock(float(os.environ.get('GROTTE_RES', res)))
    build_life(v, n, sab)
    build_parco()
    tane = build_tane()
    build_alba()
    build_raggi()
    if neve:
        build_neve()
    bocca_madre = np.array(MADRE['a']) + np.array((0.0, -1.0, 0.7))
    tane['madre'] = {'bocca': bocca_madre, 'appoggio': bocca_madre, 'dir': np.array((0.0, 1.0, -0.3)), 'raggio': MADRE['r'][0]}
    return tane


# ───────────────────────── l'acqua torbida (dopo il render) ─────────────────────────

SIGMA = np.array((0.10, 0.05, 0.045), F)   # assorbimento per metro (R, G, B): il rosso sparisce per primo
DIFFUSA = 0.55                               # quanto l'acqua rimanda della luce ambiente attorno (sfocata)
TORCIA_SCIA = np.array((0.010, 0.016, 0.016), F)   # la luce della torcia diffusa dall'acqua davanti al sub


def acqua(passes, blur_px, cone_mask=None, sigma=None, diffusa=None, sfocata=None, alpha=None):
    """Cuoce l'acqua torbida nei passi di luce (lineari): ambient = ambient·T + (1−T)·sfocata(ambient)·DIFFUSA,
    lantern = lantern·T² (andata e ritorno) + (1−T)·scia della torcia. T = exp(−σ·distanza) dal passo mist.
    cone_mask: per le anteprime prospettiche, la scia della torcia solo nel suo cono.
    Per gli strati ritagliati sopra un panorama (la posa di un mostro): sfocata è la luce sfocata del panorama sotto
    (la chiave 'sfocata' restituita per il panorama, ritagliata), alpha la copertura dello strato (l'acqua davanti al
    mostro si somma solo dove c'è il mostro; il resto lo fa il panorama)."""
    from scipy.ndimage import gaussian_filter
    sigma = SIGMA if sigma is None else np.asarray(sigma, F)
    diffusa = DIFFUSA if diffusa is None else diffusa
    d = np.clip(passes['mist'], 0, 1)[..., None] * MIST_DEPTH
    T = np.exp(-sigma * d)
    out = {}
    if 'ambient' in passes:
        a = passes['ambient'][..., :3]
        if sfocata is None:
            s = max(1, int(blur_px / 8))
            small = a[::s, ::s]
            small = np.minimum(small, np.percentile(small, 99.5))
            bl = np.stack([gaussian_filter(small[..., c], blur_px / s, mode='nearest') for c in range(3)], -1)
            bl = np.repeat(np.repeat(bl, s, 0), s, 1)[:a.shape[0], :a.shape[1]]
        else:
            bl = sfocata
        out['sfocata'] = bl
        tint = np.array((0.55, 1.0, 0.95), F)
        k = 1.0 if alpha is None else alpha[..., None]
        out['ambient'] = a * T + (1 - T) * bl * tint * diffusa * k
        if 'raggi' in passes:
            # i raggi stanno nell'acqua fra la camera e la roccia: si attenuano poco
            out['ambient'] = out['ambient'] + passes['raggi'][..., :3] * np.sqrt(T)
    if 'lantern' in passes:
        lt = passes['lantern'][..., :3]
        scia = (1 - np.exp(-0.12 * d)) * TORCIA_SCIA
        if cone_mask is not None:
            scia = scia * cone_mask[..., None]
        if alpha is not None:
            scia = scia * alpha[..., None]
        out['lantern'] = lt * T * T + scia
    return out
