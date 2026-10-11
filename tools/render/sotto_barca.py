"""
«Sotto la barca» (immersioni all'alba, DA APPROVARE): il primo posto della discesa, un'inquadratura fissa come le
camerette (deciso dall'utente l'11 ottobre: si gira di 30° a destra e a sinistra e di pochi gradi in su e in giù).

Coordinate della baia (common.py): la barca è all'origine con la prua verso +Y, il mare a z = 0. Il sub galleggia
qualche metro sotto e dietro la poppa e guarda avanti, un po' in su:
  - in alto, la chiglia della nostra barca scura contro la superficie chiara dell'alba;
  - dalla prua, la cima dell'ancora che scende obliqua davanti a lui e si perde nel buio in basso;
  - davanti, la parete sommersa dello scoglio dell'edicola, con l'imboccatura della grotta (un buco nero nella roccia,
    da cui si va alla grotta grande).

La roccia, la luce, i raggi e l'acqua torbida sono quelli della grotta (grotte.py); la barca è quella vera
(boat.py), con la lampara spenta.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

import boat
import grotte
import sdf
from common import collection, set_lightgroup
from geo import catmull, tube
from nodes import material, world

COL = grotte.COL
F = np.float32

OCCHIO_SB = (2.2, -8.0, -3.4)        # l'occhio del sub: dietro la poppa, 3,4 m sotto la superficie
GUARDA_SB = (0.8, 8.0, -1.6)         # il centro dell'inquadratura (verso la parete)
PRUA_CIMA = (0.0, 2.75, 0.05)        # dove la cima esce dalla prua
ANCORA = (-1.2, 6.6, -26.0)          # dove sta l'ancora, giù nel buio ai piedi della parete
BOCCA = (4.4, 9.6, -8.0)             # il centro dell'imboccatura della grotta
BOCCA_R = 3.0
# l'acqua di qui: meno luce rimandata che nella grotta (se no il buco dell'imboccatura si schiarisce come la roccia)
ACQUA = {'diffusa': 0.22}


def parete(p):
    """La parete sommersa dello scoglio: un piano rugoso che guarda verso la barca (−Y), con le cengie, che si
    allarga verso il fondo; l'imboccatura è un tunnel che entra nella roccia e scende."""
    p = np.asarray(p, F)
    # la parete si incurva all'indietro ai lati (lo scoglio è un promontorio) e si allarga verso il fondo
    q = np.stack([p[:, 0] * 0.09, p[:, 2] * 0.09, np.zeros(len(p), F)], 1).astype(F)
    # la parete gira attorno al sub come un'insenatura: ai lati dell'inquadratura c'è ancora roccia (sempre più
    # lontana nell'acqua torbida), non uno spigolo
    y0 = (9.0 + 0.04 * (-p[:, 2]) + 0.6 * np.sin(p[:, 0] * 0.35) - 0.010 * (p[:, 0] - 2.0) ** 2
          + 3.5 * grotte._N2(q, 1.0, 3))                               # grandi sporgenze e rientranze
    d = y0 - p[:, 1]                                                    # < 0 nella roccia (oltre il piano)
    d = -d
    d = d - (0.65 * grotte._N(p, 3.0, 3) + 0.18 * grotte._N(p + 40.0, 0.9, 2)
             + 0.10 * np.sin(p[:, 2] * 3.1 + 2.0 * grotte._N(p, 2.0, 1)))
    b = np.array(BOCCA)
    tun = np.minimum(sdf.capsule(b - (0, 2.0, 0), b + (0.5, 6.0, -1.5), BOCCA_R)(p),
                     sdf.capsule(b + (0.5, 6.0, -1.5), b + (3.5, 11.0, -4.0), BOCCA_R * 0.9)(p))
    d = sdf.smin(d, tun, 0.6)                                           # il tunnel è acqua (< 0)
    return d.astype(F)                                                  # > 0 nella roccia


def build_parete(res=0.10):
    v, f, n = sdf.mesh_banded(parete, (-42.0, -16.0, -32.0), (46.0, 28.0, 3.0), res=res, coarse=4)
    ob = grotte.mesh_obj('SottoParete', v, f, {'sabbia': np.zeros(len(v), F)})
    ob.data.materials.append(grotte.rock_material())
    print('[sotto] parete: %d triangoli' % len(f), flush=True)
    return ob, v, n


def superficie_material():
    """La superficie vista da sotto: chiara e mossa (la finestra di Snell all'alba), più scura verso l'orizzonte."""
    m, g = material('SottoSuperficie')
    co = g.texcoord('Object')
    onde = g.voronoi(g.mapping(co, scale=(0.9, 0.9, 1.0)), scale=1.0, feature='SMOOTH_F1')
    luce = g.map_range(onde, 0.0, 0.7, 1.6, 0.6)
    x, y, _ = g.sep(co)
    dist = g.vmath('LENGTH', g.comb(g.sub(x, OCCHIO_SB[0]), g.sub(y, OCCHIO_SB[1]), 0.0))
    fin = g.smoothstep(14.0, 4.0, dist)                  # lontano la superficie riflette il buio del fondo
    col = g.mix(fin, (0.02, 0.06, 0.07), (0.50, 0.80, 0.76))
    g.output_material(g.emission(col, g.mul(luce, 0.75)))
    return m


def build_superficie():
    bpy.ops.mesh.primitive_plane_add(size=120.0, location=(0, 0, 0.0))
    ob = bpy.context.object
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    collection(COL).objects.link(ob)
    ob.name = 'SottoSuperficie'
    ob.data.materials.append(superficie_material())
    ob.visible_shadow = False
    set_lightgroup(ob, 'ambient')
    return ob


def build_cima():
    """La cima dell'ancora: dalla prua scende obliqua e un po' in curva fino al buio."""
    a, b = np.array(PRUA_CIMA), np.array(ANCORA)
    pts = [a + (b - a) * t + np.array((0.6 * math.sin(t * math.pi), 0.0, 0.0)) for t in np.linspace(0, 1, 30)]
    ob = tube('CimaAncora', catmull(pts, 3), 0.026, n=8, col=COL)
    ob.data.materials.append(grotte.semplice('CimaMat', (0.16, 0.13, 0.08), rough=0.8))
    set_lightgroup(ob, 'ambient')
    # qualche filo d'alga impigliato nella cima
    alga = grotte.alga_material()
    rr = np.random.default_rng(9)
    for k in range(5):
        t = rr.uniform(0.15, 0.6)
        p0 = a + (b - a) * t
        q = [p0 + np.array((0.03 * j * math.sin(j + k), 0.02 * j, -0.12 * j)) for j in range(6)]
        o = tube('CimaAlga', q, 0.006, n=5, col=COL, taper=0.3)
        o.data.materials.append(alga)
        o.color = (0.10, 0.12, 0.03, 1.0)
        set_lightgroup(o, 'ambient')
    return ob


def build_barca():
    """La barca vera, con la lampara spenta (all'alba): da sotto si vede solo lo scafo."""
    parts, _ = boat.build_boat(fish_in_bucket=0, rod=False)
    # l'opera viva vista da sotto: vernice antivegetativa scura, con la peluria d'alghe e i denti di cane
    scafo = parts['hull'][0]
    scafo.data.materials.clear()
    scafo.data.materials.append(grotte.plastica('SottoCarena', (0.03, 0.016, 0.012), rough=0.75, melma=0.35))
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and o.name not in ('Alba', 'AlbaDiffusa', 'AlbaBordo'):
            o.data.energy = 0.0
        if o.lightgroup == 'lamp':
            o.lightgroup = 'ambient'
            if o.type == 'MESH':
                o.hide_render = True
    return parts


def build_luci():
    w, g = world('SottoAcqua')
    w.lightgroup = 'ambient'
    # tutt'attorno il verde-blu dell'acqua, più chiaro verso l'alto, nero in basso
    z = g.sep(g.texcoord('Generated'))[2]          # nel mondo: la direzione dello sguardo
    col = g.ramp(g.map_range(z, -1.0, 1.0, 0.0, 1.0),
                 [(0.0, (0.0, 0.0, 0.0)), (0.45, (0.004, 0.012, 0.013)), (0.6, (0.02, 0.05, 0.05)), (1.0, (0.10, 0.20, 0.20))])
    g.output_world(g.background(col, 1.0))
    w.mist_settings.start = 0.0
    w.mist_settings.depth = grotte.MIST_DEPTH
    w.mist_settings.falloff = 'LINEAR'
    # il sole dell'alba attraverso la superficie: un faretto largo con le caustiche, la luce diffusa dall'acqua
    sole = grotte.build_alba(energy=60000.0, diffusa=900.0)
    sole.location = (-6.0, -14.0, 14.0)
    from mathutils import Vector
    sole.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(Vector((0.25, 0.75, -1.0)))
    sole.data.spot_size = math.radians(70)
    sole.data.shadow_soft_size = 0.4
    d = bpy.data.objects.get('AlbaDiffusa')
    d.location = (2.5, 3.0, -7.0)
    d.data.energy = 600.0
    b = bpy.data.objects.get('AlbaBordo')
    b.location = (3.0, 4.0, -5.0)
    grotte.build_raggi(n=9, seed=5, top=(1.0, 0.0, -0.2), spread=4.0, lunghezza=(10.0, 16.0), raggio=(0.4, 0.9), forza=0.035)


def build_sotto_barca(res=0.10, neve=True):
    """Tutta la scena; restituisce i punti utili (occhio, bocca della grotta, cima)."""
    import os
    build_luci()
    build_superficie()
    build_barca()
    build_cima()
    build_parete(float(os.environ.get('GROTTE_RES', res)))
    if neve:
        grotte.build_neve(count=2000, radius=10.0, center=OCCHIO_SB)
    return {'occhio': OCCHIO_SB, 'bocca': BOCCA, 'prua': PRUA_CIMA, 'ancora': ANCORA}
