"""
Il gozzo del pescatore: scafo a doppia punta, interni dipinti verde acqua, pagliolato,
banchi, ordinate, capodibanda, coperta di prua, console di poppa con sonar e radio,
lampara a pressione sul buttafuori, canna con campanellino, secchio, telone, remi.

Prua verso +Y. Linea di galleggiamento z = 0. Tutte le misure in metri.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from common import EYE, collection, link, mesh_from_arrays, set_lightgroup, set_visibility
from geo import (catmull, circle_profile, cylinder, lathe, rbox, rect_profile, sphere, subdivide, sweep, tube)
from nodes import material

L = 5.6
HALF = L / 2

# punti notevoli usati anche dal gioco (manifest)
LAMP_POS = (0.0, 3.62, 1.80)          # centro della reticella incandescente
WORK_LIGHT = (0.0, 2.04, 0.80)        # lampadina di servizio sotto il bordo della coperta di prua
ROD_BUTT = (0.86, 0.30, 0.40)
ROD_GUNWALE = (0.97, 0.55, 0.74)
ROD_TIP = (2.02, 2.95, 1.86)
BUCKET_POS = (0.40, 1.62, -0.09)
TARP_POS = (-0.44, 1.52, -0.09)
CONSOLE_POS = (0.36, -2.08, 0.60)     # base della console sul ponte di poppa
SCREEN_CENTER = (0.36, -1.915, 0.84)
SCREEN_SIZE = (0.20, 0.15)


# ───────────────────────── forma dello scafo ─────────────────────────

def beam(t):
    t = np.asarray(t, float)
    bow = (1 - np.clip(np.abs(t), 0, 1) ** 2.0) ** 0.62
    stern = (1 - np.clip(np.abs(t), 0, 1) ** 2.3) ** 0.55
    return 1.0 * np.where(t > 0, bow, stern)


def sheer(t):
    t = np.asarray(t, float)
    return np.where(t > 0, 0.70 + 0.30 * t ** 2, 0.70 + 0.22 * t ** 2)


def keel(t):
    t = np.asarray(t, float)
    return -0.30 + 0.30 * np.abs(t) ** 3.2


def section_p(t):
    t = np.asarray(t, float)
    return 1.9 - 0.75 * np.maximum(t, 0) ** 2 - 0.45 * np.maximum(-t, 0) ** 2


def hull_point(t, s, side=1.0):
    """t ∈ [-1,1] lungo lo scafo, s ∈ [0,1] dalla chiglia al capodibanda."""
    B, S, K, p = beam(t), sheer(t), keel(t), section_p(t)
    z = K + (S - K) * s
    x = side * B * (1 - (1 - s) ** p) ** (1 / p)
    # leggera svasatura in alto
    x = x * (1 + 0.04 * s ** 3)
    return x, t * HALF, z


def half_width_at(y, z):
    """Semilarghezza interna (approssimata) dello scafo alla quota z nella sezione y."""
    t = np.clip(y / HALF, -0.999, 0.999)
    S, K = float(sheer(t)), float(keel(t))
    if z <= K:
        return 0.0
    s = min((z - K) / (S - K), 1.0)
    x, _, _ = hull_point(t, s)
    return float(x) - 0.035


def build_hull(mats):
    ny, ns = 140, 30
    ts = np.linspace(-0.994, 0.994, ny)
    # più stazioni verso le estremità
    ts = np.sign(ts) * np.abs(ts) ** 0.9
    ks = np.arange(-ns, ns + 1)
    verts, sec, faces = [], [], []
    for t in ts:
        for k in ks:
            s = abs(k) / ns
            x, y, z = hull_point(t, s, 1.0 if k >= 0 else -1.0)
            verts.append((float(x), float(y), float(z)))
            sec.append(s)
    m = len(ks)
    for i in range(ny - 1):
        for j in range(m - 1):
            a = i * m + j
            # normali verso l'esterno: ordine scelto per la dritta (x>0)
            faces.append((a, a + m, a + m + 1, a + 1))
    ob = mesh_from_arrays('Hull', np.array(verts), faces, smooth=True, col='boat')
    attr = ob.data.attributes.new('sec', 'FLOAT', 'POINT')
    attr.data.foreach_set('value', sec)
    # verifica orientamento: la normale a centro barca, dritta, deve puntare a +X
    me = ob.data
    me.update()
    mid = (ny // 2) * m + (m - 1) - 3
    poly_normals = [p for p in me.polygons if abs(p.center.y) < 0.1 and p.center.x > 0.8]
    if poly_normals and poly_normals[0].normal.x < 0:
        for p in me.polygons:
            p.flip()
        me.update()
    sol = ob.modifiers.new('Planks', 'SOLIDIFY')
    sol.thickness = 0.032
    sol.offset = -1.0
    sol.material_offset = 1
    sol.material_offset_rim = 2
    sol.use_even_offset = True
    for mt in (mats['hull_out'], mats['hull_in'], mats['wood_varnish']):
        ob.data.materials.append(mt)
    set_lightgroup(ob, 'ambient')
    return ob


def sheer_curve(side, n=90, t0=-0.985, t1=0.985, s=1.0, inset=0.0, dz=0.0):
    pts = []
    for t in np.linspace(t0, t1, n):
        x, y, z = hull_point(t, s, side)
        pts.append((float(x) - side * inset, float(y), float(z) + dz))
    return np.array(pts)


def build_structure(mats):
    obs = []
    # capodibanda (gunwale) su entrambi i lati
    for side in (1, -1):
        path = sheer_curve(side, inset=-0.012, dz=0.012)
        ob = sweep(f'Gunwale{side}', path, rect_profile(0.085, 0.045, bevel=0.012), col='boat')
        ob.data.materials.append(mats['wood_varnish'])
        obs.append(ob)
        # serretta (listello interno che regge i banchi)
        path = sheer_curve(side, n=60, t0=-0.75, t1=0.80, s=0.62, inset=0.045)
        ob = sweep(f'Riser{side}', path, rect_profile(0.03, 0.05, bevel=0.006), col='boat')
        ob.data.materials.append(mats['hull_in'])
        obs.append(ob)
    # ruota di prua e dritto di poppa (salgono oltre il capodibanda)
    stem = catmull([(0, HALF * 0.97, -0.12), (0, HALF * 1.0, 0.45), (0, HALF * 1.025, 0.95), (0, HALF * 1.0, 1.30)], 10)
    ob = sweep('Stem', stem, rect_profile(0.075, 0.10, bevel=0.015), col='boat', up=(1, 0, 0))
    ob.data.materials.append(mats['wood_varnish'])
    obs.append(ob)
    stern = catmull([(0, -HALF * 0.97, -0.12), (0, -HALF * 1.0, 0.45), (0, -HALF * 1.02, 0.86), (0, -HALF * 0.99, 1.10)], 10)
    ob = sweep('SternPost', stern, rect_profile(0.075, 0.10, bevel=0.015), col='boat', up=(1, 0, 0))
    ob.data.materials.append(mats['wood_varnish'])
    obs.append(ob)
    # ordinate interne
    for y in np.arange(-2.25, 2.30, 0.27):
        t = y / HALF
        pts = []
        for k in np.linspace(-1, 1, 41):
            s = abs(k) * 0.97
            x, yy, z = hull_point(t, s, 1.0 if k >= 0 else -1.0)
            nx = 0.032 + 0.018
            pts.append((float(x) - math.copysign(nx, k if k != 0 else 1), float(yy), float(z) + 0.02))
        pts = np.array(pts)
        pts = pts[np.abs(pts[:, 0]) > 0.03] if len(pts) > 3 else pts
        ob = sweep(f'Rib{y:.2f}', pts, rect_profile(0.045, 0.03, bevel=0.006), col='boat', up=(0, 1, 0))
        ob.data.materials.append(mats['hull_in'])
        obs.append(ob)
    # pagliolato
    z_floor = -0.10
    for i, x in enumerate(np.arange(-0.54, 0.55, 0.124)):
        ys = np.linspace(-2.2, 2.3, 300)
        ok = [y for y in ys if half_width_at(y, z_floor + 0.01) > abs(x) + 0.07]
        if len(ok) < 2:
            continue
        y0, y1 = min(ok), max(ok)
        if y1 - y0 < 0.3:
            continue
        ob = rbox(f'Floor{i}', (0.112, y1 - y0, 0.022), (x, (y0 + y1) / 2, z_floor), bevel=0.004, segments=2)
        ob.data.materials.append(mats['floor'])
        obs.append(ob)
    # banchi (thwarts)
    for name, y, w in (('ThwartSeat', EYE[1] + 0.02, 0.26), ('ThwartFwd', 0.98, 0.24)):
        hw = half_width_at(y, 0.40) + 0.01
        ob = rbox(name, (2 * hw, w, 0.04), (0, y, 0.40), bevel=0.008)
        ob.data.materials.append(mats['wood_varnish'])
        obs.append(ob)
    # coperta di prua
    y0, y1 = 2.12, 2.74
    zt = 0.92
    hw0 = half_width_at(y0, zt) + 0.03
    deck_pts = []
    for y in np.linspace(y0, y1, 16):
        hw = max(half_width_at(y, zt) + 0.03, 0.04)
        deck_pts.append((y, hw))
    verts, faces = [], []
    for y, hw in deck_pts:
        verts += [(-hw, y, zt + (y - y0) * 0.10), (hw, y, zt + (y - y0) * 0.10)]
    for i in range(len(deck_pts) - 1):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))
    deck = mesh_from_arrays('Foredeck', np.array(verts), faces, smooth=False, col='boat')
    so = deck.modifiers.new('T', 'SOLIDIFY')
    so.thickness = 0.03
    deck.data.materials.append(mats['hull_in'])
    obs.append(deck)
    beam_ob = rbox('ForedeckBeam', (2 * hw0, 0.07, 0.06), (0, y0, zt - 0.02), bevel=0.01)
    beam_ob.data.materials.append(mats['wood_varnish'])
    obs.append(beam_ob)
    # paratia sotto la coperta
    bh = rbox('ForeBulkhead', (2 * hw0 - 0.1, 0.025, zt + 0.1), (0, y0 + 0.02, (zt - 0.12) / 2), bevel=0.004)
    bh.data.materials.append(mats['hull_in'])
    obs.append(bh)
    # ponte di poppa
    y0, y1 = -2.68, -1.88
    za = 0.58
    verts, faces = [], []
    for y in np.linspace(y0, y1, 14):
        hw = max(half_width_at(y, za) + 0.03, 0.05)
        verts += [(-hw, y, za), (hw, y, za)]
    for i in range(13):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))
    ad = mesh_from_arrays('AftDeck', np.array(verts), faces, smooth=False, col='boat')
    so = ad.modifiers.new('T', 'SOLIDIFY')
    so.thickness = 0.03
    ad.data.materials.append(mats['hull_in'])
    obs.append(ad)
    hw1 = half_width_at(y1, za) + 0.03
    ab = rbox('AftBulkhead', (2 * hw1 - 0.05, 0.025, za + 0.1), (0, y1 - 0.01, (za - 0.12) / 2), bevel=0.004)
    ab.data.materials.append(mats['hull_in'])
    obs.append(ab)
    # cassa motore
    em = rbox('EngineBox', (0.56, 0.62, 0.40), (0, -1.38, 0.10), bevel=0.02)
    em.data.materials.append(mats['wood_varnish'])
    obs.append(em)
    for ob in obs:
        set_lightgroup(ob, 'ambient')
    return obs


# ───────────────────────── materiali ─────────────────────────

def make_materials():
    mats = {}

    # legno verniciato consumato
    m, g = material('WoodVarnish')
    co = g.texcoord('Object')
    grain_c, grain = g.wave(g.mapping(co, scale=(1.0, 0.12, 1.0)), scale=26.0, distortion=3.5, detail=4.0, detail_scale=2.0, kind='BANDS', axis='X')
    n = g.noise(co, scale=22.0, detail=6.0, rough=0.6)
    base = g.ramp(g.add(g.mul(grain, 0.55), g.mul(n.fac, 0.45)), [(0.25, (0.105, 0.052, 0.022)), (0.55, (0.20, 0.105, 0.045)), (0.85, (0.30, 0.17, 0.08))])
    wear = g.smoothstep(0.62, 0.70, g.noise(co, scale=3.0, detail=5.0, rough=0.7).fac)
    col = g.mix(wear, base, (0.33, 0.27, 0.20))
    bump = g.bump(g.add(grain, g.mul(n.fac, 0.3)), strength=0.12, distance=0.004)
    g.output_material(g.principled(color=col, rough=g.mixf(wear, 0.34, 0.75), coat=g.mixf(wear, 0.6, 0.0), coat_rough=0.12, normal=bump))
    mats['wood_varnish'] = m

    # interno dipinto verde acqua, scrostato, sporco sul fondo
    m, g = material('HullInside')
    co = g.texcoord('Object')
    _, _, z = g.sep(co)
    n1 = g.noise(co, scale=6.0, detail=8.0, rough=0.62)
    chip = g.smoothstep(0.66, 0.70, g.noise(co, scale=2.2, detail=7.0, rough=0.7).fac)
    paint = g.ramp(n1.fac, [(0.3, (0.16, 0.34, 0.31)), (0.7, (0.24, 0.45, 0.40))])
    grain_c, grain = g.wave(g.mapping(co, scale=(0.1, 1.0, 0.1)), scale=12.0, distortion=6.0, detail=3.0, kind='BANDS', axis='Y')
    wood = g.ramp(grain, [(0.2, (0.12, 0.08, 0.05)), (0.8, (0.22, 0.15, 0.09))])
    col = g.mix(chip, paint, wood)
    grime = g.mul(g.smoothstep(0.35, -0.15, z), 0.75)
    col = g.mix(grime, col, (0.035, 0.04, 0.03))
    ao = g.ao(0.25, 8)
    col = g.mix(g.sub(1.0, ao), col, (0.02, 0.025, 0.02))
    bump = g.bump(g.add(g.mul(chip, 0.5), g.mul(n1.fac, 0.15)), strength=0.25, distance=0.002)
    wet = g.smoothstep(0.0, -0.12, z)
    g.output_material(g.principled(color=col, rough=g.mixf(wet, g.mixf(chip, 0.55, 0.8), 0.18), normal=bump))
    mats['hull_in'] = m

    # esterno bianco con fascia blu e antivegetativa
    m, g = material('HullOutside')
    co = g.texcoord('Object')
    _, y, z = g.sep(co)
    sec = g.attr('sec')
    n = g.noise(co, scale=5.0, detail=6.0, rough=0.6)
    white = g.ramp(n.fac, [(0.3, (0.55, 0.55, 0.52)), (0.7, (0.72, 0.72, 0.68))])
    blue = (0.04, 0.14, 0.32)
    red = (0.22, 0.05, 0.035)
    band = g.smoothstep(0.86, 0.875, sec)
    col = g.mix(band, white, blue)
    under = g.smoothstep(0.06, 0.04, z)
    col = g.mix(under, col, red)
    stripe = g.mul(g.smoothstep(0.80, 0.81, sec), g.smoothstep(0.835, 0.825, sec))
    col = g.mix(stripe, col, (0.55, 0.42, 0.08))
    # occhio apotropaico sulla prua (entrambi i lati)
    yy = g.sub(y, 2.42)
    zz = g.sub(z, 0.66)
    e = g.add(g.mul(g.mul(yy, yy), 1.0 / 0.16 ** 2), g.mul(g.mul(zz, zz), 1.0 / 0.075 ** 2))
    eye_white = g.smoothstep(1.05, 0.95, e)
    pupil = g.smoothstep(0.30, 0.22, e)
    col = g.mix(eye_white, col, (0.75, 0.72, 0.62))
    col = g.mix(pupil, col, (0.02, 0.02, 0.05))
    plank = g.smoothstep(0.035, 0.0, g.math('ABSOLUTE', g.sub(g.math('FRACT', g.mul(sec, 9.0)), 0.5)))
    bump = g.bump(g.add(plank, g.mul(n.fac, 0.1)), strength=0.15, distance=0.004)
    g.output_material(g.principled(color=col, rough=0.45, normal=bump, coat=0.2))
    mats['hull_out'] = m

    # pagliolato: legno grigio consumato, chiazze bagnate
    m, g = material('Floorboards')
    co = g.texcoord('Object')
    grain_c, grain = g.wave(g.mapping(co, scale=(1.0, 0.06, 1.0)), scale=14.0, distortion=8.0, detail=4.0, kind='BANDS', axis='X')
    n = g.noise(co, scale=8.0, detail=6.0, rough=0.6)
    col = g.ramp(g.add(g.mul(grain, 0.5), g.mul(n.fac, 0.5)), [(0.2, (0.06, 0.05, 0.04)), (0.55, (0.15, 0.13, 0.10)), (0.85, (0.24, 0.21, 0.17))])
    wet = g.smoothstep(0.55, 0.62, g.noise(co, scale=1.4, detail=4.0, rough=0.5).fac)
    col = g.mix(g.mul(wet, 0.6), col, (0.03, 0.03, 0.025))
    bump = g.bump(grain, strength=0.18, distance=0.003)
    g.output_material(g.principled(color=col, rough=g.mixf(wet, 0.8, 0.08), normal=bump))
    mats['floor'] = m

    # metallo zincato (secchio)
    m, g = material('Galvanized')
    co = g.texcoord('Object')
    sp = g.voronoi(co, scale=40.0, out='Color')
    spn = g.bw(sp)
    dent = g.noise(co, scale=3.0, detail=3.0).fac
    col = g.mix(spn, (0.42, 0.44, 0.45), (0.62, 0.64, 0.64))
    g.output_material(g.principled(color=col, metal=1.0, rough=g.map_range(spn, 0, 1, 0.22, 0.45), normal=g.bump(dent, strength=0.15, distance=0.01)))
    mats['galvanized'] = m

    # tela cerata del telone
    m, g = material('Canvas')
    co = g.texcoord('Object')
    weave1, _ = g.wave(co, scale=180.0, kind='BANDS', axis='X', profile='SIN')
    weave2, _ = g.wave(co, scale=180.0, kind='BANDS', axis='Y', profile='SIN')
    wv = g.mul(g.bw(weave1), g.bw(weave2))
    n = g.noise(co, scale=4.0, detail=6.0, rough=0.6)
    col = g.ramp(n.fac, [(0.3, (0.07, 0.085, 0.045)), (0.75, (0.13, 0.15, 0.08))])
    stains = g.smoothstep(0.6, 0.7, g.noise(co, scale=2.0, detail=4.0).fac)
    col = g.mix(g.mul(stains, 0.5), col, (0.05, 0.05, 0.03))
    g.output_material(g.principled(color=col, rough=0.7, sheen=0.4, sheen_tint=(0.4, 0.45, 0.3), normal=g.bump(wv, strength=0.12, distance=0.001)))
    mats['canvas'] = m

    def simple(name, color, rough, metal=0.0, coat=0.0, **kw):
        m, g = material(name)
        g.output_material(g.principled(color=color, rough=rough, metal=metal, coat=coat, **kw))
        return m

    mats['brass'] = simple('Brass', (0.55, 0.38, 0.14), 0.32, 1.0)
    mats['chrome'] = simple('Chrome', (0.75, 0.75, 0.75), 0.18, 1.0)
    mats['enamel_green'] = simple('EnamelGreen', (0.03, 0.12, 0.07), 0.35, coat=0.5)
    mats['enamel_white'] = simple('EnamelWhite', (0.82, 0.80, 0.74), 0.25, coat=0.6)
    mats['black_plastic'] = simple('BlackPlastic', (0.015, 0.015, 0.017), 0.42)
    mats['grey_plastic'] = simple('GreyPlastic', (0.10, 0.10, 0.095), 0.5)
    mats['rubber'] = simple('Rubber', (0.01, 0.01, 0.01), 0.8)
    mats['rust'] = simple('RustIron', (0.12, 0.05, 0.025), 0.85, 0.3)
    mats['red_plastic'] = simple('RedPlastic', (0.45, 0.03, 0.02), 0.4)
    mats['blue_plastic'] = simple('BluePlastic', (0.03, 0.10, 0.30), 0.45)
    mats['cork'] = simple('Cork', (0.32, 0.20, 0.10), 0.9)
    mats['carbon'] = simple('RodBlank', (0.02, 0.02, 0.025), 0.25, coat=0.8)
    mats['cord'] = simple('Cord', (0.75, 0.70, 0.55), 0.85)

    m, g = material('Glass')
    g.output_material(g.principled(color=(1, 1, 1), rough=0.02, transmission=1.0, ior=1.5))
    mats['glass'] = m

    m, g = material('ScreenGlass')
    g.output_material(g.principled(color=(0.0, 0.02, 0.01), rough=0.08, coat=1.0, emission=(0.10, 0.85, 0.40), emission_strength=0.05))
    mats['screen'] = m

    m, g = material('Mantle')
    g.output_material(g.emission((1.0, 0.86, 0.66), 45.0))
    mats['mantle'] = m

    # rete da pesca: filo scuro (sparse alpha)
    m, g = material('Rope')
    co = g.texcoord('Object')
    tw, _ = g.wave(co, scale=60.0, kind='BANDS', axis='Z', distortion=2.0)
    g.output_material(g.principled(color=(0.42, 0.36, 0.26), rough=0.85, normal=g.bump(g.bw(tw), strength=0.4, distance=0.003)))
    mats['rope'] = m
    return mats


# ───────────────────────── oggetti ─────────────────────────

def build_lampara(mats):
    obs = []
    base = np.array((0.0, 2.42, 0.93))
    tip = np.array((0.0, 3.55, 2.42))
    pole = tube('LampPole', [base, (base + tip) / 2, tip], 0.028, n=12)
    pole.data.materials.append(mats['chrome'])
    obs.append(pole)
    # staffa
    br = tube('LampBracket', [(0, 2.40, 0.90), (0, 2.55, 0.93)], 0.04, n=10)
    br.data.materials.append(mats['rust'])
    obs.append(br)
    lx, ly, lz = LAMP_POS
    chain = tube('LampChain', [(lx, tip[1], tip[2]), (lx, ly, lz + 0.40)], 0.006, n=6)
    chain.data.materials.append(mats['rust'])
    obs.append(chain)
    # cappello riflettente (verde fuori, bianco dentro)
    hood = lathe('LampHood', [(0.02, lz + 0.42), (0.09, lz + 0.40), (0.20, lz + 0.31), (0.27, lz + 0.20), (0.285, lz + 0.18)], n=40)
    so = hood.modifiers.new('T', 'SOLIDIFY')
    so.thickness = 0.008
    so.material_offset = 1
    hood.data.materials.append(mats['enamel_green'])
    hood.data.materials.append(mats['enamel_white'])
    hood.location = (lx, ly, 0)
    obs.append(hood)
    # vetro, reticella, serbatoio
    glass = lathe('LampGlass', [(0.055, lz - 0.09), (0.062, lz), (0.055, lz + 0.10)], n=28)
    glass.location = (lx, ly, 0)
    glass.data.materials.append(mats['glass'])
    # il vetro non deve bloccare la luce della reticella (niente caustiche in Cycles)
    set_visibility(glass, camera=True, shadow=False, diffuse=True, glossy=True, transmission=True, scatter=False)
    obs.append(glass)
    mantle = sphere('LampMantle', 0.026, (lx, ly, lz), segs=16, rings=10, scale=(1, 1, 1.3))
    mantle.data.materials.append(mats['mantle'])
    set_lightgroup(mantle, 'lamp')
    tank = lathe('LampTank', [(0.0, lz - 0.24), (0.07, lz - 0.235), (0.085, lz - 0.17), (0.075, lz - 0.11), (0.04, lz - 0.095)], n=28, close_bottom=True)
    tank.location = (lx, ly, 0)
    tank.data.materials.append(mats['brass'])
    obs.append(tank)
    for k in range(3):
        a = 2 * math.pi * k / 3
        rod = tube(f'LampRod{k}', [(lx + 0.07 * math.cos(a), ly + 0.07 * math.sin(a), lz - 0.10), (lx + 0.07 * math.cos(a), ly + 0.07 * math.sin(a), lz + 0.19)], 0.004, n=6)
        rod.data.materials.append(mats['brass'])
        obs.append(rod)
    # luce: punto + spot verso il basso (gruppo 'lamp')
    pd = bpy.data.lights.new('LampPoint', 'POINT')
    pd.energy = 260.0
    pd.color = (1.0, 0.70, 0.42)
    pd.shadow_soft_size = 0.03
    po = bpy.data.objects.new('LampPoint', pd)
    collection('boat').objects.link(po)
    po.location = (lx, ly, lz)
    set_lightgroup(po, 'lamp')
    sd = bpy.data.lights.new('LampSpot', 'SPOT')
    sd.energy = 900.0
    sd.color = (1.0, 0.72, 0.45)
    sd.spot_size = math.radians(150)
    sd.spot_blend = 0.6
    sd.shadow_soft_size = 0.05
    so_ = bpy.data.objects.new('LampSpot', sd)
    collection('boat').objects.link(so_)
    so_.location = (lx, ly, lz + 0.01)
    so_.rotation_euler = (0, 0, 0)  # punta verso -Z
    set_lightgroup(so_, 'lamp')
    # luce di servizio: lampadina in gabbietta sul palo, illumina l'interno della barca
    wx, wy, wz = WORK_LIGHT
    bulb = sphere('WorkBulb', 0.022, (wx, wy, wz), segs=12, rings=8, scale=(1, 1, 1.2))
    bm = bpy.data.materials.get('WorkBulbMat')
    if bm is None:
        bm, g = material('WorkBulbMat')
        g.output_material(g.emission((1.0, 0.78, 0.52), 30.0))
    bulb.data.materials.append(bm)
    set_lightgroup(bulb, 'lamp')
    for k in range(4):
        a = 2 * math.pi * k / 4
        cg = tube(f'WorkCage{k}', [(wx + 0.035 * math.cos(a), wy + 0.035 * math.sin(a), wz - 0.04), (wx + 0.035 * math.cos(a), wy + 0.035 * math.sin(a), wz + 0.05)], 0.0025, n=5)
        cg.data.materials.append(mats['rust'])
        obs.append(cg)
    # paralume: il bulbo illumina verso poppa e verso il basso
    shade = lathe('WorkShade', [(0.0, wz + 0.07), (0.03, wz + 0.068), (0.055, wz + 0.03), (0.065, wz - 0.005)], n=20)
    shade.location = (wx, wy, 0)
    shade.data.materials.append(mats['enamel_green'])
    obs.append(shade)
    wd = bpy.data.lights.new('WorkLight', 'POINT')
    wd.energy = 34.0
    wd.color = (1.0, 0.74, 0.48)
    wd.shadow_soft_size = 0.02
    wo = bpy.data.objects.new('WorkLight', wd)
    collection('boat').objects.link(wo)
    wo.location = (wx, wy - 0.04, wz - 0.03)
    set_lightgroup(wo, 'lamp')
    for ob in obs:
        set_lightgroup(ob, 'ambient')
    return obs + [mantle, bulb]


def build_rod(mats, bend=0.0, name='Rod'):
    """bend: 0 = a riposo, 1 = abboccata, 2 = recupero sotto sforzo."""
    butt = np.array(ROD_BUTT)
    gun = np.array(ROD_GUNWALE)
    tip = np.array(ROD_TIP)
    d = tip - gun
    pts = []
    n = 24
    for i in range(n + 1):
        u = i / n
        p = gun + d * u
        sag = 0.06 * u * u + bend * (0.22 * u ** 2.2 + (0.18 if bend > 1.5 else 0.0) * u ** 3)
        p = p + np.array((0.0, -0.05 * bend * u ** 2, -sag))
        pts.append(p)
    path = np.vstack([butt, pts])
    blank = tube(name, path, 0.011, n=10, taper=0.25)
    blank.data.materials.append(mats['carbon'])
    obs = [blank]
    grip = tube(name + 'Grip', [butt, butt + (gun - butt) * 0.85], 0.017, n=10)
    grip.data.materials.append(mats['cork'])
    obs.append(grip)
    # mulinello sotto l'impugnatura
    rp = butt + (gun - butt) * 0.6 + np.array((0.0, 0.0, -0.06))
    spool = cylinder(name + 'Spool', 0.032, 0.05, tuple(rp), rot=(math.radians(90), 0, math.radians(-25)), verts=20)
    spool.data.materials.append(mats['grey_plastic'])
    obs.append(spool)
    handle = tube(name + 'Handle', [rp + np.array((0.04, 0.0, 0.0)), rp + np.array((0.09, 0.0, 0.03))], 0.004, n=6)
    handle.data.materials.append(mats['black_plastic'])
    obs.append(handle)
    # anelli
    for k, u in enumerate((0.25, 0.45, 0.62, 0.78, 0.9)):
        i = int(u * n)
        ring = sphere(name + f'Guide{k}', 0.008 * (1.2 - u * 0.6), tuple(pts[i] + np.array((0, 0, -0.012))), segs=8, rings=6)
        ring.data.materials.append(mats['chrome'])
        obs.append(ring)
    # campanellino d'ottone sulla punta
    bell = lathe(name + 'Bell', [(0.0, -0.028), (0.012, -0.026), (0.016, -0.012), (0.013, 0.0), (0.006, 0.006), (0.0, 0.008)], n=16)
    bell.location = tuple(pts[-2] + np.array((0, 0, -0.02)))
    bell.data.materials.append(mats['brass'])
    obs.append(bell)
    for ob in obs:
        set_lightgroup(ob, 'ambient')
    return obs, pts[-1]


def build_rod_holder(mats):
    p0 = np.array(ROD_GUNWALE) + np.array((-0.015, -0.03, -0.12))
    p1 = np.array(ROD_GUNWALE) + np.array((0.01, 0.06, 0.06))
    h = tube('RodHolder', [p0, p1], 0.025, n=12)
    h.data.materials.append(mats['chrome'])
    set_lightgroup(h, 'ambient')
    return [h]


def fish_mesh(name, length=0.24, height=0.06, loc=(0, 0, 0), rot=(0, 0, 0), mat=None):
    """Pesce semplice: corpo affusolato + coda."""
    n = 18
    pts = []
    for k in range(n + 1):
        u = k / n
        r = height * (math.sin(math.pi * min(u * 1.15, 1.0)) ** 0.8) * (1 - 0.45 * u)
        pts.append((r * 0.45 + 1e-4, (u - 0.5) * length))
    ob = lathe(name, [(r, z) for r, z in pts], n=12)
    ob.scale = (1.0, 1.0 / 0.45 * 0.45, 1.0)
    # schiaccia ai lati
    for v in ob.data.vertices:
        v.co.y *= 2.2
    tail = mesh_from_arrays(name + 'Tail', np.array([(0, 0, -length / 2 - 0.002), (0, 0.05, -length / 2 - 0.06), (0, -0.05, -length / 2 - 0.06)]), [(0, 1, 2)], col='boat')
    for o in (ob, tail):
        o.location = loc
        o.rotation_euler = rot
        if mat:
            o.data.materials.append(mat)
    return [ob, tail]


def fish_material():
    m, g = material('FishSkin')
    co = g.texcoord('Object')
    _, _, z = g.sep(co)
    n = g.noise(co, scale=40.0, detail=3.0).fac
    stripes, _ = g.wave(co, scale=25.0, kind='BANDS', axis='Z', distortion=3.0)
    col = g.mix(g.mul(g.bw(stripes), 0.4), (0.55, 0.60, 0.62), (0.10, 0.18, 0.25))
    g.output_material(g.principled(color=col, metal=0.6, rough=0.25, coat=0.8, thin_film=320.0, normal=g.bump(n, strength=0.2, distance=0.002)))
    return m


def build_bucket(mats, fish_count=0, name='Bucket', with_body=True):
    x, y, z = BUCKET_POS
    prof = [(0.0, 0.0), (0.125, 0.0), (0.128, 0.01), (0.155, 0.27), (0.162, 0.28), (0.158, 0.285)]
    b = lathe(name, prof, n=40)
    so = b.modifiers.new('T', 'SOLIDIFY')
    so.thickness = 0.004
    b.location = (x, y, z)
    b.data.materials.append(mats['galvanized'])
    obs = [b]
    if not with_body:
        bpy.data.objects.remove(b)
        obs = []
    handle = []
    for k in range(13):
        a = math.pi * k / 12
        handle.append((x + 0.158 * math.cos(a), y, z + 0.28 + 0.13 * math.sin(a) * 0.9))
    if with_body:
        hb = tube(name + 'Handle', handle, 0.004, n=6, cap=True)
        hb.data.materials.append(mats['chrome'])
        obs.append(hb)
        # acqua sul fondo
        w = cylinder(name + 'Water', 0.13, 0.002, (x, y, z + 0.06), verts=32)
        w.data.materials.append(bpy.data.materials.get('Water') or mats['glass'])
        obs.append(w)
    if fish_count:
        fm = fish_material()
        rr = np.random.default_rng(3)
        rim = z + 0.28
        for i in range(fish_count):
            a = 2 * math.pi * (i / max(fish_count, 1)) + rr.uniform(-0.4, 0.4)
            rad = rr.uniform(0.03, 0.09) if fish_count > 2 else rr.uniform(0.02, 0.06)
            ln = rr.uniform(0.21, 0.27)
            zz = rim - 0.10 + 0.006 * i
            parts = fish_mesh(f'{name}Fish{i}', length=ln, loc=(x + rad * math.cos(a), y + rad * math.sin(a), zz),
                              rot=(math.pi + rr.uniform(-0.45, 0.45), rr.uniform(-0.45, 0.45), a), mat=fm)
            obs += parts
    for ob in obs:
        set_lightgroup(ob, 'ambient')
    return obs


def build_tarp(mats):
    """Telone ripiegato: un 'cuscino' di tela con pieghe."""
    x, y, z = TARP_POS
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z + 0.09))
    ob = bpy.context.object
    ob.name = 'Tarp'
    ob.scale = (0.40, 0.62, 0.16)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    link(ob, 'boat')
    sub = ob.modifiers.new('S', 'SUBSURF')
    sub.levels = 3
    sub.render_levels = 3
    bpy.ops.object.modifier_apply(modifier='S')
    rr = np.random.default_rng(5)
    for v in ob.data.vertices:
        c = v.co
        fold = 0.012 * math.sin((c.y - y) * 38 + rr.uniform(-0.2, 0.2)) + 0.008 * math.sin((c.x - x) * 55)
        c.z += fold if c.z > z + 0.05 else 0.0
        c.x += 0.01 * math.sin(c.z * 40)
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(mats['canvas'])
    ob.rotation_euler = (0, 0, math.radians(8))
    set_lightgroup(ob, 'ambient')
    # corda che lo lega
    rope = tube('TarpRope', [(x - 0.22, y + 0.05, z + 0.02), (x - 0.15, y + 0.06, z + 0.19), (x + 0.15, y + 0.09, z + 0.19), (x + 0.22, y + 0.10, z + 0.02)], 0.008, n=8)
    rope.data.materials.append(mats['rope'])
    set_lightgroup(rope, 'ambient')
    return [ob, rope]


def build_console(mats):
    x, y, z = CONSOLE_POS
    obs = []
    body = rbox('Console', (0.50, 0.34, 0.40), (x, y, z + 0.20), bevel=0.015)
    body.data.materials.append(mats['wood_varnish'])
    obs.append(body)
    # sonar: scatola nera inclinata verso il giocatore
    sc_ = rbox('SonarBox', (0.30, 0.10, 0.24), (SCREEN_CENTER[0], SCREEN_CENTER[1] - 0.06, SCREEN_CENTER[2]), rot=(math.radians(-8), 0, 0), bevel=0.012)
    sc_.data.materials.append(mats['black_plastic'])
    obs.append(sc_)
    sw, sh = SCREEN_SIZE
    scr = rbox('SonarScreen', (sw, 0.006, sh), SCREEN_CENTER, rot=(math.radians(-8), 0, 0), bevel=0.0)
    scr.data.materials.append(mats['screen'])
    obs.append(scr)
    for k, dx in enumerate((-0.10, -0.06, 0.06, 0.10)):
        kn = cylinder(f'SonarKnob{k}', 0.011, 0.02, (SCREEN_CENTER[0] + dx, SCREEN_CENTER[1] + 0.01, SCREEN_CENTER[2] - 0.10), rot=(math.radians(90), 0, 0), verts=12)
        kn.data.materials.append(mats['grey_plastic'])
        obs.append(kn)
    # radio VHF sul lato sinistro della console
    rad = rbox('Radio', (0.20, 0.16, 0.07), (x - 0.13, y + 0.02, z + 0.44), bevel=0.008)
    rad.data.materials.append(mats['grey_plastic'])
    obs.append(rad)
    disp = rbox('RadioDisplay', (0.08, 0.004, 0.025), (x - 0.13, y + 0.10, z + 0.45), bevel=0.0)
    m_disp = bpy.data.materials.get('RadioLCD')
    if m_disp is None:
        m_disp, g = material('RadioLCD')
        g.output_material(g.emission((1.0, 0.45, 0.08), 2.0))
    disp.data.materials.append(m_disp)
    obs.append(disp)
    mic = rbox('RadioMic', (0.05, 0.03, 0.09), (x - 0.27, y + 0.05, z + 0.34), rot=(0, math.radians(20), 0), bevel=0.01)
    mic.data.materials.append(mats['black_plastic'])
    obs.append(mic)
    coil = [(x - 0.20 + 0.012 * math.cos(t * 7), y + 0.06 + 0.012 * math.sin(t * 7), z + 0.43 - t * 0.04) for t in np.linspace(0, 1.6, 60)]
    cord = tube('MicCord', coil, 0.003, n=6)
    cord.data.materials.append(mats['black_plastic'])
    obs.append(cord)
    # santino di Santa Brina incastrato nella cornice
    card = rbox('Santino', (0.055, 0.002, 0.085), (x + 0.20, y + 0.172, z + 0.30), rot=(0, math.radians(-6), 0), bevel=0.0)
    m_card = bpy.data.materials.get('SantinoMat')
    if m_card is None:
        m_card, g = material('SantinoMat')
        co = g.texcoord('Object')
        x_, _, z_ = g.sep(co)
        d = g.add(g.mul(g.mul(x_, x_), 1 / 0.016 ** 2), g.mul(g.mul(g.sub(z_, 0.01), g.sub(z_, 0.01)), 1 / 0.03 ** 2))
        fig = g.smoothstep(1.0, 0.8, d)
        halo_d = g.add(g.mul(g.mul(x_, x_), 1 / 0.02 ** 2), g.mul(g.mul(g.sub(z_, 0.03), g.sub(z_, 0.03)), 1 / 0.02 ** 2))
        halo = g.mul(g.smoothstep(1.0, 0.85, halo_d), g.smoothstep(0.55, 0.7, halo_d))
        col = g.mix(fig, (0.62, 0.55, 0.40), (0.10, 0.18, 0.35))
        col = g.mix(halo, col, (0.75, 0.55, 0.12))
        g.output_material(g.principled(color=col, rough=0.6))
    card.data.materials.append(m_card)
    obs.append(card)
    for ob in obs:
        set_lightgroup(ob, 'ambient')
    return obs


def build_props(mats):
    obs = []
    # remi appoggiati sui banchi
    for side in (1, -1):
        xx = side * 0.55
        shaft = tube(f'Oar{side}', [(xx, -1.75, 0.47), (xx + side * 0.06, 1.15, 0.48)], 0.022, n=10)
        shaft.data.materials.append(mats['wood_varnish'])
        blade = rbox(f'OarBlade{side}', (0.02, 0.62, 0.13), (xx + side * 0.07, 1.42, 0.50), rot=(0, math.radians(side * 70), 0), bevel=0.006)
        blade.data.materials.append(mats['wood_varnish'])
        obs += [shaft, blade]
    # rotolo di cima sulla coperta di prua
    coil = []
    for t in np.linspace(0, 1, 260):
        a = t * 2 * math.pi * 5.5
        r = 0.12 - 0.035 * (t * 5.5 % 1.0) * 0.4 - t * 0.02
        coil.append((-0.18 + r * math.cos(a), 2.40 + r * math.sin(a), 0.965 + 0.016 * math.sin(t * 40) + t * 0.035))
    rope = tube('CoilRope', coil, 0.011, n=8)
    rope.data.materials.append(mats['rope'])
    obs.append(rope)
    # ancora arrugginita
    anc = tube('Anchor', [(0.20, 2.30, 0.97), (0.20, 2.58, 0.99)], 0.018, n=8)
    anc.data.materials.append(mats['rust'])
    obs.append(anc)
    for s in (-1, 1):
        fl = tube(f'AnchorFluke{s}', [(0.20, 2.30, 0.97), (0.20 + s * 0.10, 2.26, 1.01), (0.20 + s * 0.13, 2.32, 1.03)], 0.012, n=8)
        fl.data.materials.append(mats['rust'])
        obs.append(fl)
    # tanica rossa e cassetta
    can = rbox('FuelCan', (0.20, 0.30, 0.26), (-0.32, -1.70, 0.03), rot=(0, 0, math.radians(12)), bevel=0.025)
    can.data.materials.append(mats['red_plastic'])
    obs.append(can)
    crate = rbox('Crate', (0.42, 0.30, 0.20), (-0.42, -0.86, 0.01), rot=(0, 0, math.radians(-6)), bevel=0.01)
    crate.data.materials.append(mats['blue_plastic'])
    obs.append(crate)
    # galleggianti di sughero sulla cassetta (rete)
    rr = np.random.default_rng(9)
    for i in range(7):
        f = sphere(f'Float{i}', 0.035, (-0.42 + rr.uniform(-0.15, 0.15), -0.86 + rr.uniform(-0.1, 0.1), 0.13 + rr.uniform(0, 0.04)), segs=10, rings=6, scale=(1, 1, 0.6))
        f.data.materials.append(mats['cork'])
        obs.append(f)
    for ob in obs:
        set_lightgroup(ob, 'ambient')
    return obs


def build_player_proxy():
    """Corpo del pescatore: invisibile alla camera, proietta solo l'ombra."""
    obs = []
    ex, ey, ez = EYE
    parts = [
        ('PTorso', [(0, ey - 0.04, 0.45), (0, ey - 0.06, 1.05)], 0.17),
        ('PHead', [(0, ey - 0.02, 1.13), (0, ey - 0.02, 1.30)], 0.11),
        ('PThighL', [(-0.12, ey, 0.46), (-0.14, ey + 0.45, 0.46)], 0.075),
        ('PThighR', [(0.12, ey, 0.46), (0.14, ey + 0.45, 0.46)], 0.075),
        ('PShinL', [(-0.14, ey + 0.45, 0.46), (-0.15, ey + 0.55, -0.05)], 0.06),
        ('PShinR', [(0.14, ey + 0.45, 0.46), (0.15, ey + 0.55, -0.05)], 0.06),
        ('PArmL', [(-0.22, ey - 0.05, 1.0), (-0.26, ey + 0.25, 0.62)], 0.05),
        ('PArmR', [(0.22, ey - 0.05, 1.0), (0.26, ey + 0.25, 0.62)], 0.05),
    ]
    for name, pts, r in parts:
        ob = tube(name, pts, r, n=10)
        set_visibility(ob, camera=False, shadow=True, diffuse=False, glossy=False, transmission=False, scatter=False)
        obs.append(ob)
    return obs


def build_boat(fish_in_bucket=3, rod=True):
    mats = make_materials()
    parts = {}
    parts['hull'] = [build_hull(mats)]
    parts['structure'] = build_structure(mats)
    parts['lampara'] = build_lampara(mats)
    parts['holder'] = build_rod_holder(mats)
    parts['tarp'] = build_tarp(mats)
    parts['console'] = build_console(mats)
    parts['props'] = build_props(mats)
    parts['player'] = build_player_proxy()
    if rod:
        parts['rod'], tip = build_rod(mats)
    parts['bucket'] = build_bucket(mats, fish_in_bucket)
    return parts, mats
