"""
L'ANIMATORE — tavola di studio del mostro nuovo (dalla notte 2), da far approvare.

È l'animatore di Splashland, annegato dentro il costume di Mama Marina: il peluche blu marcito, gonfio
d'acqua, le cuciture strappate da cui esce la gommapiuma, la muffa, la melma dei nostri mostri, gli occhi
da cartone (uno che penzola, l'altro che manca, come nella statua). Nella bocca del costume, la faccia
dell'uomo annegato. Tre varianti che differiscono davvero per proporzioni, postura e quanto si vede di lui:

  A «Pupazzo»   il costume quasi intero, dritto e rigido come chi aspetta i bambini all'ingresso; la testa
                enorme; lui è in fondo alla bocca, si vede appena la faccia (occhi bianchi, bocca aperta)
  B «Fradicio»  il costume gonfio d'acqua che cede: curvo, la pancia che pende, la testa crollata di lato;
                le pinne sfondate da cui escono le sue mani; la faccia gonfia spinta fuori dalla bocca
  C «Sventrato» la testa del costume spaccata in due dalla bocca in su, le metà aperte come un cappuccio;
                lui alto e scheletrico esce fino alle spalle, il costume gli pende addosso come una pelle

Per ogni variante la figura intera e il primo piano della faccia. Bozze di studio: non sono i modelli
definitivi del gioco. Usa materiali, luci e strumenti di dettagli.py e skin.py, che restano come sono.
Coordinate: i piedi a z = 0, la faccia guarda −Y.

Uso: tools/.venv/bin/python tools/render/foxy_concept.py [--fast] [--only A|B|C] [--tavola]
     (--tavola rimonta la tavola dai pannelli già renderizzati, senza rifarli)
"""
from __future__ import annotations

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
from common import CACHE, ROOT, reset_scene  # noqa: E402
from creature import eyeball  # noqa: E402
from dettagli import V, chain, mat_simple, unit  # noqa: E402
from geo import catmull  # noqa: E402
from nodes import material  # noqa: E402

F = np.float32
FAST = D.FAST
RES = 0.0075 if FAST else 0.0045         # il costume
FINE = 0.004 if FAST else 0.0022         # la faccia dell'uomo (a fasce)
OUT = os.path.join(ROOT, 'docs', 'concept')
TMP = os.path.join(CACHE, 'foxy')


# ───────────────────────── geometria di servizio ─────────────────────────

def rot(yaw=0.0, pitch=0.0, roll=0.0):
    """Rotazione locale → mondo: prima roll (attorno a Y), poi pitch (X, positivo = faccia in giù), poi yaw (Z)."""
    return (sdf.rot_matrix('z', yaw) @ sdf.rot_matrix('x', pitch) @ sdf.rot_matrix('y', roll)).astype(F)


class Fr:
    """Un sistema locale (posizione + rotazione): la parte si costruisce dritta e poi si mette in posa."""

    def __init__(self, pos, R=None):
        self.pos = V(*pos)
        self.R = np.eye(3, dtype=F) if R is None else np.asarray(R, F)

    def field(self, f):
        R, c = self.R, self.pos
        return lambda p: f((p - c) @ R)

    def pt(self, q):
        return self.pos + self.R @ V(*q)

    def local(self, p):
        return (p - self.pos) @ self.R

    def dir(self, d):
        return self.R @ V(*d)


def mesh(name, field, lo, hi, mat, res=None, attrs=None):
    """Come dettagli.mesh, ma a fasce (il campo esatto solo vicino alla superficie): il costume è grande e pieno
    di rumore, la griglia intera sarebbe lentissima."""
    import time
    from creature import sdf_object
    t = time.time()
    ob = sdf_object(name, field, lo, hi, res=res or RES, attrs=attrs, banded=True)
    ob.data.materials.append(mat)
    print(f'  {name}: {len(ob.data.vertices)} vertici, {time.time() - t:.0f} s', flush=True)
    return ob


def tube(points, r0, r1, n=6):
    pts = catmull([V(*p) for p in points], n)
    m = len(pts)
    return sdf.union(*[sdf.round_cone(pts[i], pts[i + 1], r0 + (r1 - r0) * i / (m - 1), r0 + (r1 - r0) * (i + 1) / (m - 1))
                       for i in range(m - 1)])


def bounds(points, pad):
    pts = np.array(points, F)
    return pts.min(0) - pad, pts.max(0) + pad


def ragged(seed, scale, amp):
    n3 = sdf.Noise3(seed)
    return lambda p: (amp * n3(p, scale=scale, octaves=3)).astype(F)


def matted(seed, amp):
    """Il pelo fradicio: ciocche appiccicate a punta verso il basso (creste allungate in verticale) e grumi."""
    n1, n2 = sdf.Noise3(seed), sdf.Noise3(seed + 7)

    def f(p):
        q = p * V(1.0, 1.0, 0.28)
        streak = 1.0 - np.abs(n1(q, scale=0.022, octaves=2))
        clump = n2(p, scale=0.06, octaves=2)
        return (amp * (0.6 * streak ** 3 + 0.4 * clump)).astype(F)
    return f


def sag(seed, amp):
    """Pieghe verticali della stoffa che cede sotto il peso dell'acqua."""
    w = skin.wrinkles(seed, 0.09, 1.0, direction=(0, 0, 1))
    return lambda p: (amp * w(p)).astype(F)


# ───────────────────────── materiali ─────────────────────────

def plush(name='Plush', base=(0.035, 0.11, 0.42), soak=1.0):
    """Il peluche blu di Mama Marina, fradicio: pelo appiccicato in ciocche, aloni d'acqua, colature di sporco,
    muffa a colonie (bianco-verde e nera), alga sul fondo; dentro (attributo 'inner') la gommapiuma marcia.
    Attributi: belly (la pancia color crema), cheek (le guance rosa), inner, slime."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    belly, cheek, inner = g.attr('belly'), g.attr('cheek'), g.attr('inner')
    # fibre: rumore stirato in verticale, ciocche
    fib = g.noise(g.mapping(co, scale=(260.0, 260.0, 38.0)), scale=1.0, detail=3.0, rough=0.6)
    clump = g.noise(co, scale=34.0, detail=4.0, rough=0.6, distortion=0.4)
    # la pancia color crema: il bordo mangiato, macchiata d'acqua; il sorriso dipinto rosso scuro attorno alla bocca
    bn = g.noise(co, scale=9.0, detail=5.0, rough=0.6)
    bm = g.smoothstep(0.40, 0.60, g.add(belly, g.mul(g.sub(bn.fac, 0.5), 1.5)))
    cream = g.mix(g.smoothstep(0.38, 0.68, bn.fac), (0.27, 0.25, 0.19), (0.075, 0.065, 0.04))
    col = g.mix(bm, base, cream)
    peel = g.smoothstep(0.45, 0.55, g.noise(co, scale=22.0, detail=4.0).fac)
    col = g.mix(g.mul(g.smoothstep(0.3, 0.7, g.attr('lip')), g.sub(1.0, g.mul(peel, 0.6))), col, (0.09, 0.012, 0.016))
    # le lacrime: colature nere e lucide che scendono dagli occhi (come la ruggine della statua)
    tears = g.clamp01(g.mul(g.attr('tears'), 1.3))
    col = g.mix(tears, col, (0.22, 0.065, 0.015))
    col = g.mix(g.mul(g.smoothstep(0.2, 0.8, cheek), 0.9), col, (0.58, 0.12, 0.20))
    # le punte delle ciocche più chiare, il fondo scuro e bagnato
    col = g.mix(g.mul(g.smoothstep(0.45, 0.75, fib.fac), 0.35), col, (0.62, 0.66, 0.70), blend='MULTIPLY')
    col = g.mix(g.mul(g.smoothstep(0.55, 0.30, clump.fac), 0.55 * soak), col, (0.25, 0.25, 0.28), blend='MULTIPLY')
    # aloni d'acqua (bordi più scuri) e colature di sporco dall'alto
    tide = g.noise(co, scale=3.2, detail=5.0, rough=0.55, distortion=0.8)
    ring = g.sub(1.0, g.math('ABSOLUTE', g.sub(g.mul(tide.fac, 2.0), 1.0)))
    col = g.mix(g.mul(g.smoothstep(0.90, 0.98, ring), 0.45), col, (0.10, 0.09, 0.06))
    streak = g.noise(g.mapping(co, scale=(24.0, 24.0, 1.8)), scale=1.0, detail=4.0, rough=0.5)
    col = g.mix(g.mul(g.smoothstep(0.55, 0.72, streak.fac), 0.65), col, (0.09, 0.08, 0.05), blend='MULTIPLY')
    # alga e fango in basso (stava sul fondo)
    low = g.smoothstep(0.75, 0.15, z)
    algae = g.noise(co, scale=9.0, detail=6.0, rough=0.6)
    col = g.mix(g.mul(low, g.smoothstep(0.35, 0.6, algae.fac)), col, (0.10, 0.13, 0.04))
    # muffa: chiazze irregolari bianco-verdastre a grappoli, col bordo scuro, e spruzzi di puntini neri
    where = g.smoothstep(0.50, 0.64, g.noise(co, scale=2.2, detail=4.0, distortion=0.6).fac)
    blot = g.noise(co, scale=11.0, detail=6.0, rough=0.7, distortion=1.4)
    cells = g.voronoi(g.vmath('ADD', co, g.vmath('SCALE', blot.color, scale=0.04)), scale=26.0, feature='F1')
    colony = g.mul(g.mul(g.smoothstep(0.42, 0.18, cells), g.smoothstep(0.42, 0.62, blot.fac)), where)
    fuzz = g.noise(co, scale=220.0, detail=2.0)
    col = g.mix(g.mul(colony, g.add(0.45, g.mul(fuzz.fac, 0.6))), col, (0.42, 0.47, 0.32))
    # muffa nera a macchie larghe, sfumate
    rot_ = g.noise(co, scale=3.0, detail=6.0, rough=0.65, distortion=0.9)
    col = g.mix(g.mul(g.smoothstep(0.52, 0.68, rot_.fac), 0.9), col, (0.010, 0.014, 0.010))
    edge = g.mul(g.mul(g.smoothstep(0.36, 0.42, blot.fac), g.smoothstep(0.50, 0.42, blot.fac)), where)
    col = g.mix(g.mul(edge, 0.6), col, (0.04, 0.045, 0.03))
    black = g.voronoi(co, scale=70.0, feature='F1')
    bm = g.mul(g.smoothstep(0.25, 0.08, black), g.smoothstep(0.55, 0.70, g.noise(co, scale=3.7, detail=4.0, distortion=0.8).fac))
    col = g.mix(g.mul(bm, 0.9), col, (0.012, 0.014, 0.010))
    # dentro: gommapiuma nera e marcia
    col = g.mix(g.smoothstep(0.3, 0.7, inner), col, (0.035, 0.028, 0.015))
    # melma: chiazze lucide e colature
    patch = g.noise(co, scale=4.5, detail=4.0, rough=0.55, distortion=0.7)
    drip = g.noise(g.mapping(co, scale=(30.0, 30.0, 2.4)), scale=1.0, detail=3.0)
    sl = g.mx(g.smoothstep(0.56, 0.64, patch.fac), g.mul(g.smoothstep(0.60, 0.70, drip.fac), 0.8))
    sl = g.clamp01(g.add(g.add(g.mul(sl, 0.8 * soak), g.attr('slime')), g.mul(tears, 0.9)))
    # fradicio dal basso: più scuro e bagnato verso i piedi
    wet = g.smoothstep(1.0, 0.2, z)
    col = g.mix(g.mul(wet, 0.55 * soak), col, (0.25, 0.25, 0.25), blend='MULTIPLY')
    sl = g.mx(sl, g.mul(wet, 0.5 * soak))
    col = g.mix(g.mul(sl, 0.5), col, (0.45, 0.55, 0.30), blend='MULTIPLY')
    h = g.add(g.mul(fib.fac, 0.7), g.mul(clump.fac, 0.5))
    nrm = g.bump(h, strength=0.55, distance=0.004)
    hs = g.noise(co, scale=120.0, detail=2.0)
    bsdf = g.principled(color=col, rough=g.mixf(sl, 0.82, 0.30), spec=0.3, normal=nrm,
                        sheen=g.mixf(sl, 0.8, 0.1), sheen_rough=0.35, sheen_tint=(0.55, 0.70, 1.0),
                        coat=g.mul(sl, 0.7), coat_rough=0.04, coat_tint=(0.80, 0.90, 0.62),
                        coat_normal=g.bump(g.add(sl, g.mul(hs.fac, 0.15)), strength=0.3, distance=0.002))
    g.output_material(bsdf)
    return m


def foam(dark=False):
    """La gommapiuma che esce dagli strappi: giallo ocra annerito, a pori, zuppa e marcia (dark: quella in fondo
    alle orbite, quasi nera)."""
    name = 'FoamDark' if dark else 'Foam'
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    pores = g.voronoi(co, scale=160.0, feature='F1')
    big = g.noise(co, scale=12.0, detail=5.0, rough=0.6, distortion=0.5)
    k = 0.35 if dark else 1.0
    col = g.mix(g.smoothstep(0.35, 0.7, big.fac), (0.30 * k, 0.21 * k, 0.07 * k), (0.09 * k, 0.06 * k, 0.025 * k))
    col = g.mix(g.mul(g.smoothstep(0.10, 0.02, pores), 0.8), col, (0.05, 0.035, 0.01))
    mold = g.mul(g.smoothstep(0.6, 0.72, g.noise(co, scale=7.0, detail=3.0).fac), 0.8)
    col = g.mix(mold, col, (0.13, 0.17, 0.07))
    wet = g.smoothstep(0.45, 0.6, g.noise(co, scale=5.0, detail=3.0).fac)
    nrm = g.bump(g.add(g.mul(pores, 3.0), big.fac), strength=0.6, distance=0.003)
    g.output_material(g.principled(color=col, rough=g.mixf(wet, 0.9, 0.35), sss=0.2, sss_radius=(1.0, 0.7, 0.3),
                                   sss_scale=0.01, normal=nrm, coat=g.mul(wet, 0.6), coat_rough=0.05))
    return m


def drowned():
    """La pelle dell'annegato: bianco-azzurrognola, gonfia, marmorizzata di vene viola e verdi, la melma."""
    m = bpy.data.materials.get('DrownedSkinMarmo')
    if m:
        return m
    skin.creature_skin('DrownedSkin', base=(0.30, 0.33, 0.33), dark=(0.10, 0.12, 0.15), light=(0.46, 0.47, 0.44),
                       vein=(0.16, 0.08, 0.20), mouth=(0.05, 0.010, 0.014), rough=0.5, sss=0.18, scale=1.0,
                       pores=1.2, blotch=1.2, slime_amount=0.55, slime_tint=(0.80, 0.88, 0.80))
    m = bpy.data.materials['DrownedSkin']
    m.name = 'DrownedSkinMarmo'
    # la marmorizzazione dell'annegato: reticolo di vene scure sopra al colore
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    src = bsdf.inputs['Base Color'].links[0].from_socket
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = 70.0
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 9.0
    add = nt.nodes.new('ShaderNodeVectorMath')
    add.operation = 'ADD'
    sc = nt.nodes.new('ShaderNodeVectorMath')
    sc.operation = 'SCALE'
    sc.inputs['Scale'].default_value = 0.03
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    nt.links.new(nz.outputs['Color'], sc.inputs[0])
    nt.links.new(tc.outputs['Object'], add.inputs[0])
    nt.links.new(sc.outputs['Vector'], add.inputs[1])
    nt.links.new(add.outputs['Vector'], vor.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.022
    mr.inputs['From Max'].default_value = 0.0
    mr.inputs['To Max'].default_value = 0.35
    nt.links.new(vor.outputs['Distance'], mr.inputs['Value'])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['B'].default_value = (0.20, 0.10, 0.22, 1)
    nt.links.new(mr.outputs['Result'], mix.inputs['Factor'])
    nt.links.new(src, mix.inputs['A'])
    # 'buio': dove l'uomo sparisce dentro il costume (il collo) la pelle va al nero
    att = nt.nodes.new('ShaderNodeAttribute')
    att.attribute_name = 'buio'
    dark = nt.nodes.new('ShaderNodeMix')
    dark.data_type = 'RGBA'
    dark.inputs['B'].default_value = (0.004, 0.004, 0.005, 1)
    nt.links.new(att.outputs['Fac'], dark.inputs['Factor'])
    nt.links.new(mix.outputs['Result'], dark.inputs['A'])
    nt.links.new(dark.outputs['Result'], bsdf.inputs['Base Color'])
    return m


def toon_eye():
    """L'occhio da cartone del costume: cupola di plastica bianca ingiallita, pupilla nera col riflesso dipinto, graffi."""
    m = bpy.data.materials.get('ToonEye')
    if m:
        return m
    m, g = material('ToonEye')
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    r = g.vmath('LENGTH', g.comb(g.sub(x, 0.05), g.sub(z, 0.05), 0.0))
    front = g.smoothstep(0.0, -0.5, y)
    pupil = g.mul(g.smoothstep(0.50, 0.46, r), front)
    hl = g.mul(g.smoothstep(0.14, 0.10, g.vmath('LENGTH', g.comb(g.add(x, 0.13), g.sub(z, 0.27), 0.0))), front)
    dirt = g.noise(co, scale=6.0, detail=5.0, rough=0.6)
    col = g.mix(g.smoothstep(0.35, 0.75, dirt.fac), (0.80, 0.76, 0.62), (0.42, 0.36, 0.22))
    col = g.mix(pupil, col, (0.008, 0.008, 0.01))
    col = g.mix(hl, col, (0.85, 0.85, 0.80))
    scr = g.noise(g.mapping(co, scale=(40.0, 3.0, 3.0)), scale=1.0, detail=2.0)
    g.output_material(g.principled(color=col, rough=g.add(0.12, g.mul(g.smoothstep(0.6, 0.75, scr.fac), 0.5)),
                                   coat=0.7, coat_rough=0.04))
    return m


def floor_material():
    """Le piastrelle bagnate della piscina: celesti scolorite, fughe nere, pozzanghere che riflettono."""
    m = bpy.data.materials.get('PoolTiles')
    if m:
        return m
    m, g = material('PoolTiles')
    co = g.texcoord('Object')
    br = g.node('ShaderNodeTexBrick')
    g.link(co, g.inp(br, 'Vector'))
    g.set(br, 'Scale', 6.0)
    g.set(br, 'Mortar Size', 0.012)
    g.set(br, 'Color1', (0.07, 0.11, 0.12, 1))
    g.set(br, 'Color2', (0.055, 0.09, 0.10, 1))
    g.set(br, 'Mortar', (0.015, 0.016, 0.014, 1))
    br.offset = 0.0
    br.squash = 1.0
    dirt = g.noise(co, scale=1.5, detail=6.0, rough=0.6)
    col = g.mix(g.smoothstep(0.35, 0.7, dirt.fac), g.out(br, 'Color'), (0.04, 0.05, 0.035), blend='MULTIPLY')
    puddle = g.smoothstep(0.48, 0.53, g.noise(co, scale=0.7, detail=3.0, distortion=0.4).fac)
    col = g.mix(g.mul(puddle, 0.6), col, (0.03, 0.035, 0.03))
    rough = g.mixf(puddle, 0.45, 0.02)
    g.output_material(g.principled(color=col, rough=rough, spec=0.5,
                                   normal=g.bump(g.out(br, 'Fac'), strength=0.25, distance=0.004, invert=True)))
    return m


# ───────────────────────── i pezzi del costume ─────────────────────────
# Il costume ha la sagoma della statua (mascot.py): testa e corpo sono un unico uovo di balena largo quanto
# un uomo con le braccia larghe, il sorriso sotto gli occhi, le pinne ai lati, la coda alzata dietro come un
# cuore, lo zampillo in cima; sotto escono le gambe di peluche con le zampe a sacco. Chi lo porta guarda fuori
# dalla bocca.

def head_outer(P):
    """La parte alta dell'uovo (la testa) in coordinate locali, con le guance: centro nell'origine, faccia −Y."""
    a = P['head_r']
    outer = sdf.ellipsoid((0, 0, 0), a)
    cheeks = sdf.union(*[sdf.sphere((s * 0.54 * a[0], -0.70 * a[1], -0.24 * a[2]), 0.13) for s in (-1, 1)])
    outer = sdf.union(outer, cheeks, k=0.09)
    outer = sdf.displace(outer, sag(P['seed'] + 1, 1.0), 0.010)
    outer = sdf.displace(outer, matted(P['seed'] + 2, 1.0), 0.004)
    outer = sdf.displace(outer, ragged(P['seed'], 0.16, 1.0), P['lumpy'])
    return outer


def mouth_cut(P):
    """Il sorriso aperto: un'ellisse piegata in su ai lati, passante nella parete davanti, con l'orlo strappato."""
    mw, mh, mz, curve = P['mouth']
    torn = ragged(P['seed'] + 3, 0.022, 0.014)

    def mouth(p):
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        zc = mz + curve * x * x
        q = np.sqrt((x / mw) ** 2 + ((z - zc) / mh) ** 2)
        d = (q - 1.0) * min(mw, mh) - torn(p)
        return np.maximum(d, y + 0.06)
    return mouth


def eye_pos(P, s):
    """Il centro dell'occhio da cartone sulla superficie della testa (s = +1 a destra di chi guarda il costume)."""
    a = P['head_r']
    x, z = s * 0.38 * a[0], 0.20 * a[2]
    y = -a[1] * math.sqrt(max(0.05, 1 - (x / a[0]) ** 2 - (z / a[2]) ** 2))
    return V(x, y + 0.02, z)


def jet_field(P):
    """Lo zampillo di peluche sulla testa (nella statua era una fontana): dita floscie che ricadono."""
    a = P['head_r']
    top = V(0, 0.0, a[2] * 0.97)
    parts = [sdf.round_cone(top - V(0, 0, 0.05), top + V(0, 0, 0.10), 0.055, 0.042)]
    rng = np.random.default_rng(P['seed'])
    for k in range(9):
        ang = 2 * math.pi * k / 9 + rng.uniform(-0.2, 0.2)
        d = V(math.cos(ang), math.sin(ang), 0)
        droop = P['jet_droop'] * rng.uniform(0.7, 1.3)
        pts = [top + V(0, 0, 0.09), top + V(0, 0, 0.13) + d * 0.06, top + d * 0.13 + V(0, 0, 0.10 - droop * 0.3),
               top + d * 0.17 + V(0, 0, 0.02 - droop * 0.8), top + d * 0.18 + V(0, 0, -0.04 - droop)]
        parts.append(tube(pts, 0.020, 0.010, n=4))
        parts.append(sdf.sphere(pts[-1], 0.016))
    return sdf.union(*parts, k=0.025)


def lashes(fr, s, eye_c, er, droop=0.0):
    """Le ciglia da cartone (tre per occhio), di gomma nera, piegate dall'acqua."""
    out = []
    for k in range(3):
        a = math.radians(62 + 26 * k) if s < 0 else math.radians(118 - 26 * k)
        b = eye_c + V(math.cos(a) * er * 0.95, -0.005, math.sin(a) * er * 0.98)
        t = b + V(math.cos(a) * 0.045, -0.03, math.sin(a) * 0.04 + 0.01 - droop * (k + 1) * 0.02)
        out.append(sdf.round_cone(fr.pt(b), fr.pt(t), 0.009, 0.0045))
    return sdf.union(*out)


def torn_patch(c, n, along, L, W, seed):
    """Uno strappo: fessura frastagliata lungo 'along' sul piano di normale n. Restituisce (taglio, gommapiuma).
    Il taglio si sottrae al costume; la gommapiuma marcia esce gonfia dallo strappo."""
    c, n, along = V(*c), unit(n), unit(along)
    side = unit(np.cross(n, along))
    rough = ragged(seed, 0.02, 0.012)

    def cut(p):
        q = p - c
        u, v = q @ along, q @ side
        w = W * np.clip(1.0 - (u / L) ** 2, 0.0, 1.0) ** 0.5 + rough(p)
        d = np.maximum(np.abs(v) - w, np.abs(u) - L)
        return np.maximum(d, np.abs(q @ n) - 0.10)

    blobs = []
    rng = np.random.default_rng(seed)
    for k in range(5):
        t = (k / 4 - 0.5) * 1.5 * L
        r = W * rng.uniform(0.8, 1.2)
        blobs.append(sdf.sphere(c + along * t - n * r * 0.35 + side * rng.uniform(-0.3, 0.3) * W, r))
    fm = sdf.displace(sdf.union(*blobs, k=W * 0.8), ragged(seed + 9, 0.012, 1.0), 0.008)
    return cut, fm


def threads(a, b, count, seed, length=0.12):
    """Fili di cucitura che pendono da uno strappo."""
    rng = np.random.default_rng(seed)
    a, b = V(*a), V(*b)
    out = []
    for k in range(count):
        p = a + (b - a) * rng.uniform(0, 1)
        sway = V(rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.0), 0)
        L = length * rng.uniform(0.5, 1.2)
        pts = [p, p + sway * 0.5 + V(0, -0.005, -L * 0.4), p + sway + V(0, 0, -L)]
        out.append(tube(pts, 0.0022, 0.0016, n=3))
    return sdf.union(*out)


def fin_blade(tip, d, length, width, thick, seed, torn=False):
    """La pinna: lama piatta e larga in fondo alla manica, di taglio verso chi guarda (normale ≈ −Y)."""
    d = unit(d)
    n = unit(V(0, -1, 0) - d * float(d[1]))
    blade = sdf.union(sdf.round_cone(tip, tip + d * length, width, width * 0.45),
                      sdf.sphere(tip + d * length * 0.35, width * 1.08), k=0.06)
    blade = sdf.intersect(blade, lambda p: np.abs((p - tip) @ n) - thick, k=0.025)
    if torn:
        # la punta sfondata: se ne va a brandelli, ne esce la mano
        blade = sdf.subtract(blade, sdf.displace(sdf.sphere(tip + d * length * 0.9, width * 1.15), ragged(seed, 0.02, 1.0), 0.03), k=0.01)
    return blade


# ───────────────────────── l'uomo ─────────────────────────

HINGE = V(0, -0.010, -0.026)       # la cerniera della mascella (davanti alle orecchie)


def jaw_rot(P, frac=1.0):
    return sdf.rot_matrix('x', P['jaw'] * frac)


def man_head_field(P):
    """La testa dell'annegato in coordinate locali (centro del cranio nell'origine, faccia verso −Y). Un teschio
    con la pelle sopra: arcate sopraccigliari forti, orbite profonde, zigomi in fuori e guance scavate, il naso
    mangiato, le labbra ritirate sui denti, la mascella spalancata di P['jaw'] gradi. P['bloat'] la gonfia (B)."""
    b = P['bloat']
    cran = sdf.ellipsoid((0, 0.012, 0.030), (0.074 + b * 0.5, 0.097, 0.088))
    face = sdf.ellipsoid((0, -0.036, -0.022), (0.060 + b, 0.066, 0.072))
    brow = sdf.capsule((-0.042, -0.086, 0.030), (0.042, -0.086, 0.030), 0.012)
    zyg = sdf.union(*[sdf.sphere((s * 0.050, -0.070, -0.004), 0.018 + b * 0.8) for s in (-1, 1)])
    nose = sdf.union(sdf.round_cone((0, -0.092, 0.022), (0, -0.108, -0.010), 0.006, 0.009),
                     sdf.sphere((0, -0.108, -0.016), 0.010),
                     *[sdf.sphere((s * 0.010, -0.100, -0.020), 0.0075) for s in (-1, 1)], k=0.006)
    muzzle = sdf.ellipsoid((0, -0.084, -0.040), (0.032 + b * 0.5, 0.020, 0.016))
    Rj = jaw_rot(P)
    jaw = sdf.rotate(sdf.union(sdf.ellipsoid((0, -0.046, -0.080), (0.050 + b * 0.8, 0.050, 0.026)),
                               sdf.sphere((0, -0.084, -0.096), 0.016 + b * 0.5),
                               sdf.ellipsoid((0, -0.084, -0.068), (0.027 + b * 0.5, 0.013, 0.009)), k=0.016), Rj, center=HINGE)
    neck = sdf.round_cone((0, 0.025, -0.08), (0, 0.035, P.get('neck_end', -0.24)), 0.050 + b, 0.058 + b)
    f = sdf.union(cran, face, k=0.035)
    f = sdf.union(f, brow, zyg, k=0.018)
    f = sdf.union(f, muzzle, k=0.014)
    f = sdf.union(f, nose, k=0.008)
    f = sdf.union(f, jaw, k=0.022)
    f = sdf.union(f, neck, k=0.035)
    # le guance scavate sotto gli zigomi (non in B, gonfio)
    if b < 0.01:
        for s in (-1, 1):
            f = sdf.subtract(f, sdf.ellipsoid((s * 0.056, -0.080, -0.044), (0.016, 0.018, 0.024)), k=0.012)
    # orbite profonde
    for s in (-1, 1):
        f = sdf.subtract(f, sdf.ellipsoid((s * 0.031, -0.090, 0.010), (0.020, 0.022, 0.016)), k=0.007)
    # le palpebre: quella di sopra cala a metà sull'occhio (lo sguardo spento), quella di sotto gonfia
    lid = P.get('lid', 0.35)
    for s in (-1, 1):
        e = V(s * 0.031, -0.085, 0.010)
        up_lid = sdf.intersect(sdf.sphere(e, 0.0150), sdf.plane(V(0, 0.25, -1), -float(V(0, 0.25, -1) @ (e + V(0, 0, 0.0128 * (1 - 2 * lid))))))
        low_lid = sdf.intersect(sdf.sphere(e + V(0, -0.001, -0.002), 0.0145), sdf.plane(V(0, 0.2, 1), -float(V(0, 0.2, 1) @ (e + V(0, 0, -0.009)))))
        f = sdf.union(f, up_lid, low_lid, k=0.003)
    # il naso mangiato: le narici sfondate
    f = sdf.subtract(f, sdf.union(*[sdf.ellipsoid((s * 0.007, -0.113, -0.018), (0.005, 0.010, 0.006)) for s in (-1, 1)]), k=0.002)
    # la bocca: dalle labbra ritirate fino in gola
    f = sdf.subtract(f, mouth_hole(P), k=0.004)
    f = sdf.displace(f, skin.wrinkles(P['seed'] + 11, 0.010, 1.0), 0.0010)
    f = sdf.displace(f, skin.bumps(P['seed'] + 12, 0.025, 1.0), 0.0015 + b * 0.1)
    return f


def mouth_hole(P):
    """La bocca spalancata: dal labbro di sopra (ritirato sui denti) a quello di sotto, che scende con la mascella."""
    up = V(0, -0.094, -0.047)
    low = jaw_rot(P) @ (V(0, -0.090, -0.064) - HINGE) + HINGE
    c = (up + low) / 2
    hz = float(np.linalg.norm(up - low)) / 2 + 0.006
    return sdf.union(sdf.ellipsoid(c + V(0, -0.004, 0), (0.027, 0.030, hz)),
                     sdf.ellipsoid(c + V(0, 0.030, -0.004), (0.034, 0.040, hz + 0.008)), k=0.01)


def man_mouth_attr(P):
    m = mouth_hole(P)
    return lambda p: np.clip(-m(p) / 0.006 + 0.6, 0, 1).astype(F)


def man_teeth(P, fr):
    """Denti lunghi e gialli, scalzati (le gengive ritirate): qualcuno manca."""
    Rj = jaw_rot(P)
    pairs = []
    rng = np.random.default_rng(P['seed'] + 5)
    for row in (0, 1):
        for i in range(-4, 5):
            if rng.random() < P.get('missing_teeth', 0.3):
                continue
            x = i * 0.0058
            y = -0.093 + 0.0011 * i * i
            if row == 0:
                b_, t_ = V(x, y - 0.002, -0.038), V(x, y - 0.0045, -0.054 - rng.uniform(0, 0.005))
            else:
                b_ = Rj @ (V(x, y + 0.002, -0.074) - HINGE) + HINGE
                t_ = Rj @ (V(x, y - 0.001, -0.059 + rng.uniform(0, 0.003)) - HINGE) + HINGE
            pairs.append((fr.pt(b_), fr.pt(t_), 0.0030 if abs(i) < 3 else 0.0034))
    m = mat_simple('ManTeeth', (0.50, 0.42, 0.24), rough=0.30, coat=0.5)
    return D.teeth_mesh('ManTeeth', pairs, m)


def snap(field, pts, iters=6, eps=0.0015):
    """Porta i punti sulla superficie del campo (passi di Newton lungo il gradiente)."""
    q = np.array(pts, F)
    for _ in range(iters):
        d = field(q)
        g = sdf.gradient_normals(field, q, eps)
        q = q - d[:, None] * g
    return q, sdf.gradient_normals(field, q, eps)


def man_hair(P, fr, head_local):
    """Capelli neri bagnati e radi: ciocche incollate al cranio e alla fronte, qualcuna che pende."""
    rng = np.random.default_rng(P['seed'] + 6)
    parts = []
    for k in range(P.get('hair', 26)):
        a = rng.uniform(-1.25, 1.25)
        top = V(0.05 * math.sin(a) * 0.4, 0.03 + rng.uniform(-0.02, 0.03), 0.118)
        if abs(a) < 0.75:   # davanti: sulla fronte
            mid = V(0.055 * math.sin(a), -0.070, 0.085)
            end = V(0.065 * math.sin(a) + rng.uniform(-0.01, 0.01), -0.095, 0.050 - rng.uniform(0, 0.035))
        else:               # ai lati: dietro le orecchie
            mid = V(0.080 * math.sin(a), 0.0, 0.080)
            end = V(0.085 * math.sin(a), 0.02 + rng.uniform(-0.02, 0.02), -0.02 - rng.uniform(0, 0.05))
        q, n = snap(head_local, [top, mid, end])
        pts = catmull(list(q + n * 0.003), 5)
        parts.append(D.hair_clump([fr.pt(p) for p in pts], r0=0.0040, r1=0.0012))
    f = sdf.union(*parts, k=0.003)
    return mesh('ManHair', f, fr.pos - 0.15, fr.pos + 0.15, D.wet_hair(), res=0.0018 if not FAST else 0.0025)


def man_head(P, fr, cut=None):
    """La testa dell'uomo in posa (fr), con gli occhi lattiginosi, i denti, i capelli, la bava."""
    local = man_head_field(P)
    f = fr.field(local)
    if cut is not None:
        f = sdf.intersect(f, cut)
    mouth = man_mouth_attr(P)

    def sockets(p):
        q = fr.local(p)
        o = np.zeros(len(p), F)
        for s in (-1, 1):
            o = np.maximum(o, np.exp(-np.sum(((q - V(s * 0.031, -0.090, 0.008)) / V(0.026, 0.03, 0.022)) ** 2, axis=1)))
        return o

    def buio(p):
        q = fr.local(p)
        return (np.clip((-0.135 - q[:, 2]) / 0.03, 0, 1) * 0.97).astype(F)

    attrs = {'mouth': lambda p: mouth(fr.local(p)), 'buio': buio, 'scar': lambda p: np.zeros(len(p), F),
             'blush': sockets,
             'slime': lambda p: (np.clip(1.0 - np.abs(fr.local(p)[:, 2] + 0.06) / 0.05, 0, 1) * (fr.local(p)[:, 1] < -0.07)).astype(F)}
    obs = [mesh('ManHead', f, fr.pos - 0.2, fr.pos + 0.2, drowned(), res=FINE, attrs=attrs)]
    eye_m = skin.cloudy_eye('DrownedEye', sclera=(0.52, 0.50, 0.44), iris=(0.60, 0.64, 0.63), pupil_col=(0.50, 0.52, 0.52),
                            iris_r=0.5, pupil=0.13)
    for s in (-1, 1):
        c = fr.pt((s * 0.031, -0.085, 0.010))
        look = fr.dir((s * P.get('eye_spread', 0.12), -1.0, P.get('eye_up', 0.15)))
        obs.append(eyeball(f'ManEye{s}', tuple(map(float, c)), 0.0122, eye_m, look=tuple(map(float, unit(look)))))
    obs.append(man_teeth(P, fr))
    if P.get('hair', 26):
        obs.append(man_hair(P, fr, local))
    # bava dalla bocca aperta
    sl = skin.slime_material('Slime', tint=(0.70, 0.82, 0.55))
    Rj = jaw_rot(P)
    lowlip = lambda x: fr.pt(Rj @ (V(x, -0.094, -0.072) - HINGE) + HINGE)
    g = sdf.union(skin.strand(fr.pt((0.012, -0.096, -0.044)), lowlip(0.014), 0.010, r=0.0013),
                  skin.strand(fr.pt((-0.016, -0.095, -0.043)), lowlip(-0.012), 0.006, r=0.0011),
                  skin.drip(lowlip(-0.004) + fr.dir((0, -0.004, -0.010)), 0.05, r0=0.0025, r1=0.0045),
                  skin.drip(lowlip(0.016) + fr.dir((0, -0.002, -0.012)), 0.03, r0=0.002, r1=0.0035))
    c = fr.pt((0, -0.09, -0.07))
    obs.append(mesh('ManDrool', g, c - 0.13, c + 0.13, sl, res=0.0010 if not FAST else 0.0018))
    return obs


def man_hand(wrist, fwd, n_curl, seed, spread=0.3, k=1.0, elbow=None, bony=False, nails=None, up=None):
    """La mano dell'annegato che esce dalla pinna sfondata. bony: la mano del modello definitivo, lunga e ossuta,
    con le nocche gonfie e le dita aperte (nails: lista in cui aggiungere i campi delle unghie scure; up: dove
    guarda il dorso della mano)."""
    fwd = unit(fwd)
    side = unit(np.cross(fwd, V(0, 0, 1) if up is None else V(*up)))
    if np.linalg.norm(side) < 1e-3:
        side = V(1, 0, 0)
    down = unit(np.cross(side, fwd))
    rng = np.random.default_rng(seed)
    wrist = V(*wrist)
    palm_c = wrist + fwd * 0.05 * k
    root = wrist - fwd * 0.22 if elbow is None else V(*elbow)
    if bony:
        # avambraccio magro coi tendini, polso ossuto, palmo lungo e piatto
        parts = [sdf.round_cone(root, wrist - fwd * 0.03, 0.026 * k, 0.017 * k),
                 sdf.sphere(wrist - fwd * 0.03, 0.020 * k),
                 sdf.round_cone(wrist - fwd * 0.03, palm_c + fwd * 0.02 * k, 0.019 * k, 0.026 * k),
                 sdf.ellipsoid(palm_c + fwd * 0.025 * k, (0.040 * k, 0.040 * k, 0.016 * k))]
        parts[-1] = sdf.rotate(parts[-1], np.stack([side, fwd, -down], axis=1).astype(F), center=palm_c + fwd * 0.025 * k)
        for t in (-1, 0, 1):
            parts.append(sdf.capsule(root + side * t * 0.008 * k - down * 0.010 * k, wrist - fwd * 0.04 + side * t * 0.007 * k - down * 0.006 * k, 0.0045 * k))
    else:
        parts = [sdf.round_cone(root, wrist - fwd * 0.03, 0.030 * k, 0.022 * k),
                 sdf.sphere(wrist - fwd * 0.03, 0.024 * k),
                 sdf.round_cone(wrist - fwd * 0.03, palm_c, 0.024 * k, 0.036 * k),
                 sdf.ellipsoid(palm_c + fwd * 0.02 * k, (0.045 * k, 0.045 * k, 0.045 * k))]
    for i in range(4):
        a = (i / 3 - 0.5) * spread
        d = fwd * math.cos(a) + side * math.sin(a)
        base = palm_c + d * 0.05 * k + side * (i - 1.5) * 0.004
        c1 = n_curl * rng.uniform(0.7, 1.2)
        if bony:
            L = (0.21 - abs(i - 1.5) * 0.022) * k
            r = (0.0085 * k, 0.0062 * k, 0.0052 * k, 0.0036 * k)
            kn = 0.0098 * k
        else:
            L = (0.15 - abs(i - 1.5) * 0.016) * k
            r = (0.0105 * k, 0.0085 * k, 0.0075 * k, 0.0055 * k)
            kn = 0.0105 * k
        p1 = base + d * L * 0.45
        d2 = unit(d * math.cos(c1) + down * math.sin(c1))
        p2 = p1 + d2 * L * 0.32
        d3 = unit(d * math.cos(c1 * 2) + down * math.sin(c1 * 2))
        p3 = p2 + d3 * L * 0.26
        parts.append(chain([base, p1, p2, p3], list(r), k=0.004))
        for q in (base, p1, p2):
            parts.append(sdf.sphere(q, kn if q is not base else kn * 1.15))
        if nails is not None:
            nails.append(sdf.ellipsoid(p3 - d3 * 0.006 * k - down * 0.0025 * k, (0.0045 * k, 0.0045 * k, 0.0045 * k)))
    thumb_b = palm_c - side * 0.035 * k
    tp = thumb_b + unit(fwd - side * 0.8 + down * 0.3) * (0.10 if bony else 0.07) * k
    parts.append(chain([thumb_b, (thumb_b + tp) / 2, tp], [0.012 * k, 0.010 * k, 0.007 * k] if bony else [0.014 * k, 0.012 * k, 0.009 * k], k=0.006))
    if nails is not None:
        nails.append(sdf.sphere(tp, 0.005 * k))
    f = sdf.union(*parts, k=0.008 if bony else 0.012)
    f = sdf.displace(f, skin.wrinkles(seed + 3, 0.008, 1.0), 0.0012)
    return f


# ───────────────────────── il costume intero, in posa ─────────────────────────

def build(P):
    """Costruisce la variante P. Restituisce (oggetti, punto della faccia, sistema della testa dell'uomo)."""
    obs = []
    pl = plush('Plush', soak=P['soak'])
    fm = foam()
    sl = skin.slime_material('Slime', tint=(0.70, 0.82, 0.55))
    thread_m = mat_simple('Thread', (0.02, 0.02, 0.025), rough=0.5)

    # — il corpo: la metà bassa dell'uovo, inclinata di P['lean'] —
    hip = V(*P['hip'])
    tr = Fr(hip, rot(pitch=P['lean'], roll=P.get('torso_roll', 0.0)))
    br = P['body_r']
    body = tr.field(sdf.union(sdf.ellipsoid((0, 0, br[2]), br),
                              sdf.ellipsoid((0, -br[1] * 0.20, br[2] * 0.55 - P['belly_drop']), (br[0] * 0.93, br[1] * 0.95, br[2] * 0.62)),
                              k=0.15))
    # la testa: la metà alta dell'uovo, un guscio di gommapiuma; si unisce al corpo senza collo
    # (le orbite degli occhi strappati si scavano nella testa intera, prima di spaccarla in C)
    hfr = Fr(V(*P['head_c']), rot(P['head_yaw'], P['head_pitch'], P['head_roll']))
    split = P.get('split')
    ER = P.get('eye_r', 0.068)
    ho = head_outer(P)
    hW = hfr.field(ho)
    hs = lambda q: np.maximum(ho(q), -(ho(q) + 0.045))
    for s, state in P['eyes'].items():
        if state != 'ok':
            sock = sdf.displace(sdf.sphere(eye_pos(P, s) + V(0, -0.01, 0), ER * 1.15), ragged(P['seed'] + 70 + s, 0.015, 1.0), 0.015)
            hs = sdf.subtract(hs, sock, k=0.01)
    shell = hfr.field(split(hs, P) if split else hs)

    def hl(q):
        """Da un punto della testa intera (locale) al punto dove sta dopo lo strappo di C."""
        q = V(*q)
        if not split:
            return q
        return split_rot(1 if q[0] >= 0 else -1) @ (q - SPLIT_HINGE) + SPLIT_HINGE

    # la coda alzata dietro, con le due pinne a cuore (B: crollata a terra)
    tp = [tr.pt(q) if i < 2 else V(*q) for i, q in enumerate(P['tail'])]
    tail = tube(tp, 0.15, 0.07, n=5)
    td = unit(tp[-1] - tp[-2])
    tside = unit(np.cross(td, V(0, 0, 1))) if abs(td[2]) < 0.95 else V(1, 0, 0)
    flukes = sdf.union(*[fin_blade(tp[-1], unit(td * 0.4 + tside * s), 0.24, 0.10, 0.035, P['seed'] + 30 + s) for s in (-1, 1)], k=0.04)
    # le gambe di peluche e le zampe a sacco
    legs = []
    for s, (k_, a_) in ((1, P['legR']), (-1, P['legL'])):
        h = tr.pt((s * br[0] * 0.45, 0, br[2] * 0.35))
        knee, ankle = V(*k_), V(*a_)
        legs.append(tube([h, knee, ankle], 0.15, 0.115, n=4))
        legs.append(sdf.ellipsoid(ankle + V(0, -0.08, -ankle[2] + 0.065), (0.14, 0.21, 0.07)))
    # le braccia: maniche che finiscono nelle pinne (B, C: sfondate, ne escono le mani dell'uomo)
    arms, hands = [], []
    for s, pts in ((1, P['armR']), (-1, P['armL'])):
        sh = tr.pt((s * br[0] * 0.80, -0.03, br[2] * 1.55))
        pts = [sh] + [V(*q) for q in pts]
        arms.append(tube(pts, 0.12, 0.075, n=5))
        d = unit(pts[-1] - pts[-2])
        torn = P['fin'] == 'hands'
        arms.append(fin_blade(pts[-1] - d * 0.08, d, P.get('fin_len', 0.40), 0.19, 0.045, P['seed'] + 50 + s, torn=torn))
        if torn:
            hands.append((pts[-1] + d * 0.17, d, s))
    suit = sdf.union(body, tail, flukes, k=0.07)
    suit = sdf.union(suit, *legs, k=0.06)
    suit = sdf.union(suit, *arms, k=0.08)
    suit = sdf.displace(suit, matted(P['seed'] + 20, 1.0), 0.005)
    suit = sdf.displace(suit, sag(P['seed'] + 21, 1.0), 0.013)
    suit = sdf.displace(suit, ragged(P['seed'] + 22, 0.16, 1.0), P['lumpy'])
    # dentro la testa è vuoto: il corpo non ci entra
    suit = sdf.subtract(suit, lambda p: hW(p) + 0.045, k=0.02)
    f = sdf.union(suit, shell, k=0.10 if not split else 0.03)
    if not split:
        f = sdf.subtract(f, hfr.field(mouth_cut(P)), k=0.008)
    # gli strappi, da cui esce la gommapiuma
    foam_parts, foam_c, th, socket_foam, socket_c = [], [], [], [], []
    th_c = []          # i capi di ogni gruppo di fili: ogni gruppo ha la sua mesh, in un riquadro stretto
    for i, (c, n, along, L, W) in enumerate(P['tears'](tr, br)):
        cut, fpart = torn_patch(c, n, along, L, W, P['seed'] + 40 + i)
        f = sdf.subtract(f, cut, k=0.004)
        foam_parts.append(fpart)
        foam_c.append(c)
        th.append(threads(V(*c) - unit(along) * L * 0.8, V(*c) + unit(along) * L * 0.8, 6, P['seed'] + 45 + i, 0.10))
        th_c.append([V(*c) - unit(along) * L, V(*c) + unit(along) * L, V(*c) - V(0, 0, 0.14)])
    # gli occhi da cartone, uno per lato: 'ok' al suo posto (storto, con le ciglia), 'hang' che penzola da un
    # brandello di stoffa fuori dall'orbita sfondata, 'gone' strappato via (resta l'orbita con la gommapiuma marcia)
    em = toon_eye()
    for s, state in P['eyes'].items():
        ec = eye_pos(P, s)
        if state == 'ok':
            c = hfr.pt(ec)
            obs.append(eyeball(f'ToonEye{s}', tuple(map(float, c)), ER, em, look=tuple(map(float, unit(hfr.dir(P.get('eye_ok_look', (0.15, -1, 0.0))))))))
            obs.append(mesh(f'Lashes{s}', lashes(hfr, s, ec, ER, droop=0.6), c - 0.15, c + 0.15,
                            mat_simple('Lash', (0.015, 0.015, 0.02), rough=0.35, coat=0.5), res=0.0022))
            continue
        socket_foam.append(hfr.field(sdf.displace(sdf.sphere(hl(ec + V(0, 0.085, 0)), ER * 0.95), ragged(P['seed'] + 71 + s, 0.01, 1.0), 0.012)))
        socket_c.append(hfr.pt(hl(ec)))
        if state == 'hang':
            top = hfr.pt(hl(ec + V(0, -0.02, -0.03)))
            bottom = top + V(*P['eye_hang'])
            # il brandello: una striscia di stoffa blu, e i fili che lo tengono
            mid = top + (bottom - top) * 0.5 + V(0.01, -0.03, 0)
            strip = tube([top, mid, bottom + V(0, 0, ER * 0.85)], 0.015, 0.007, n=6)
            obs.append(mesh('EyeStrip', strip, np.minimum(top, bottom) - 0.08, np.maximum(top, bottom) + 0.08, pl, res=0.002 if not FAST else 0.0035))
            th.append(sdf.union(*[tube([top + V(dx, 0, 0), mid + V(dx * 2, -0.01, 0.02), bottom + V(dx * 0.5, 0.0, ER * 0.9)], 0.0018, 0.0015, n=4)
                                  for dx in (-0.012, 0.008, 0.016)]))
            th_c.append([top, bottom])
            obs.append(eyeball('ToonEyeHang', tuple(map(float, bottom)), ER, em, look=tuple(map(float, unit(V(*P['eye_look']))))))
    # lo zampillo (C: spezzato con la testa)
    jet = hfr.field(split(jet_field(P), P) if split else jet_field(P))
    f = sdf.union(f, jet, k=0.03)

    # attributi del peluche: pancia color crema, guance rosa, il dentro della testa nero
    belly_fr = Fr(tr.pt((0, -br[1] * 0.9, br[2] * 0.85)), tr.R)
    a = P['head_r']
    cheek_l = [V(s * 0.54 * a[0], -0.80 * a[1], -0.24 * a[2]) for s in (-1, 1)]

    def belly(p):
        q = belly_fr.local(p)
        d = (q[:, 0] / (br[0] * 0.72)) ** 2 + (q[:, 2] / (br[2] * 0.62)) ** 2
        return (np.clip((1.0 - d) / 0.12, 0, 1) * (q[:, 1] < 0.05)).astype(F)

    def cheek(p):
        q = hfr.local(p)
        if split:
            q = split_local_inverse(q)
        return np.clip(sum(np.exp(-np.sum((q - c) ** 2, axis=1) / 0.085 ** 2) for c in cheek_l), 0, 1).astype(F)

    mw, mh, mz, curve = P['mouth']

    def lip(p):
        if split:
            return np.zeros(len(p), F)
        q = hfr.local(p)
        x, z = q[:, 0], q[:, 2]
        e = np.sqrt((x / (mw + 0.035)) ** 2 + ((z - mz - curve * x * x) / (mh + 0.035)) ** 2)
        return (np.clip((1.0 - e) / 0.08, 0, 1) * (q[:, 1] < -0.05)).astype(F)

    def inner(p):
        q = hfr.local(p)
        if split:
            q = split_local_inverse(q)
        return np.clip((-ho(q) - 0.010) / 0.012, 0, 1).astype(F)

    def tears(p):
        q = hfr.local(p)
        if split:
            q = split_local_inverse(q)
        out = np.zeros(len(p), F)
        for s in (-1, 1):
            e = eye_pos(P, s)
            for off, w in ((0.0, 1.0), (0.035 * s, 0.7), (-0.03 * s, 0.5)):
                wob = 0.010 * np.sin(q[:, 2] * 31.0 + s * 2.0 + off * 90)
                dx = np.abs(q[:, 0] - e[0] - off - wob)
                below = np.clip((e[2] - q[:, 2]) / 0.6, 0, 1)
                lane = np.exp(-(dx / (0.008 + 0.03 * below)) ** 2) * (q[:, 2] < e[2] + 0.02) * np.exp(-below * (1.4 + 1.5 * (1 - w)))
                out = np.maximum(out, w * lane * (q[:, 1] < -0.05))
        return out.astype(F)

    lo = np.minimum(hip - V(1.25, 1.0, hip[2]), V(-1.3, -1.1, 0.0))
    hi = np.maximum(hip + V(1.25, 1.4, 2.0), V(1.3, 1.4, 2.6))
    obs.append(mesh('Costume', f, lo, hi, pl, attrs={'belly': belly, 'cheek': cheek, 'inner': inner, 'lip': lip, 'tears': tears}))
    obs.append(mesh('FoamTears', sdf.union(*foam_parts), *bounds(foam_c, 0.35), fm, res=min(RES, 0.004)))
    obs.append(mesh('FoamSockets', sdf.union(*socket_foam), *bounds(socket_c, 0.2), foam(dark=True), res=min(RES, 0.004)))
    for i, (tf, tc) in enumerate(zip(th, th_c)):
        obs.append(mesh(f'Threads{i}', tf, *bounds(tc, 0.06), thread_m, res=0.0012 if not FAST else 0.002))

    # — le mani dell'uomo che escono dalle pinne sfondate (B, C) —
    if hands:
        nails = []
        hd = P.get('hand_dir', {})
        hf = sdf.union(*[man_hand(t, hd.get(s, d), P['curl'], P['seed'] + 60 + s, spread=P.get('hand_spread', 0.3), k=P.get('hand_k', 1.0),
                                  bony=P.get('bony', False), nails=nails, elbow=t - unit(hd.get(s, d)) * 0.24 if s in hd else None,
                                  up=P.get('hand_up', {}).get(s)) for t, d, s in hands])
        obs.append(mesh('ManHands', hf, *bounds([h[0] for h in hands], 0.40), drowned(), res=P.get('hand_res', 0.0025) if not FAST else 0.004))
        if P.get('bony'):
            obs.append(mesh('ManNails', sdf.union(*nails), *bounds([h[0] for h in hands], 0.40),
                            mat_simple('Nails', (0.06, 0.05, 0.035), rough=0.3, coat=0.6), res=0.0015 if not FAST else 0.003))

    # — l'uomo dentro —
    mfr = Fr(hfr.pt(P['man_off']), hfr.R @ rot(*P['man_rot']))
    obs += man_head(P, mfr)
    if P.get('man_body'):
        obs += P['man_body'](P, mfr, hfr, hl)

    # — melma: gocce dall'orlo della bocca del costume, fili di bava tra le labbra di stoffa, colature sul corpo —
    dr = []
    rng = np.random.default_rng(P['seed'] + 90)
    if not split:
        lipf = lambda x, up: hfr.pt((x, -a[1] * math.sqrt(max(0.05, 1 - (x / a[0]) ** 2 - ((mz + curve * x * x + up * mh) / a[2]) ** 2)) + 0.012,
                                     mz + curve * x * x + up * mh * 0.92))
        for k in range(P.get('drips', 7)):
            x = rng.uniform(-0.8, 0.8) * mw
            L = rng.uniform(0.03, 0.10)
            dr.append((skin.drip(lipf(x, -1), L, r0=0.003, r1=rng.uniform(0.005, 0.008)), [lipf(x, -1), lipf(x, -1) - V(0, 0, L)]))
        for k in range(P.get('strands', 3)):
            x = rng.uniform(-0.7, 0.7) * mw
            x2 = x + rng.uniform(-0.05, 0.05)
            dr.append((skin.strand(lipf(x, 1), lipf(x2, -1), mh * rng.uniform(0.3, 0.8), r=0.0022), [lipf(x, 1), lipf(x2, -1) - V(0, 0, mh)]))
    for c in P.get('body_drips', []):
        L = rng.uniform(0.05, 0.12)
        dr.append((skin.drip(V(*c), L, r0=0.003, r1=0.006), [V(*c), V(*c) - V(0, 0, L)]))
    # ogni goccia ha la sua mesh in un riquadro stretto (sono sottili: su tutta la figura la griglia non sta in memoria)
    for i, (df, pts) in enumerate(dr):
        obs.append(mesh(f'Drip{i}', df, *bounds(pts, 0.03), sl, res=0.0018 if not FAST else 0.003))
    face = mfr.pt((0, -0.10, 0.0))
    return obs, face, mfr


# ───────────────────────── le tre varianti ─────────────────────────

def tears_a(tr, br):
    # la cucitura del fianco aperta, uno strappo sotto la pancia
    return [(tr.pt((br[0] * 0.86, -br[1] * 0.40, br[2] * 1.05)), tr.dir((0.9, -0.45, 0)), tr.dir((0, 0, 1)), 0.20, 0.04),
            (tr.pt((-br[0] * 0.30, -br[1] * 0.90, br[2] * 0.42)), tr.dir((-0.3, -1, -0.3)), tr.dir((1, 0, 0.3)), 0.11, 0.03)]


def tears_b(tr, br):
    return [(tr.pt((0.05, -br[1] * 0.97, br[2] * 0.70)), tr.dir((0, -1, 0)), tr.dir((0.15, 0, 1)), 0.30, 0.055),
            (tr.pt((-br[0] * 0.88, -br[1] * 0.30, br[2] * 1.10)), tr.dir((-1, -0.3, 0)), tr.dir((0, 0, 1)), 0.18, 0.045),
            (tr.pt((br[0] * 0.60, -br[1] * 0.70, br[2] * 0.40)), tr.dir((0.7, -0.7, -0.3)), tr.dir((1, 0, 0.5)), 0.10, 0.035)]


def tears_c(tr, br):
    return [(tr.pt((br[0] * 0.78, -br[1] * 0.58, br[2] * 0.85)), tr.dir((0.8, -0.6, 0)), tr.dir((0.2, 0, 1)), 0.26, 0.05),
            (tr.pt((-br[0] * 0.55, -br[1] * 0.82, br[2] * 0.45)), tr.dir((-0.5, -0.9, 0)), tr.dir((0, 0, 1)), 0.16, 0.04)]


SPLIT_HINGE = V(0, 0.22, -0.36)
SPLIT_ANG = 38.0


def split_rot(s):
    return (sdf.rot_matrix('y', s * SPLIT_ANG) @ sdf.rot_matrix('x', -6.0)).astype(F)


def split_c(f, P):
    """La testa spaccata in due dalla bocca in su: le due metà si aprono di lato come un cappuccio."""
    out = []
    for s in (1, -1):
        jag = ragged(P['seed'] + 100 + s, 0.03, 0.03)
        half = sdf.intersect(f, lambda p, s=s: -(s * p[:, 0]) + 0.010 + jag(p))
        out.append(sdf.rotate(half, split_rot(s), center=SPLIT_HINGE))
    return sdf.union(*out)


def split_local_inverse(q):
    """Da un punto delle metà aperte al punto della testa intera (per i colori dipinti)."""
    out = q.copy()
    for s in (1, -1):
        R = split_rot(s)
        back = (q - SPLIT_HINGE) @ R + SPLIT_HINGE
        m = (s * back[:, 0]) > -0.02
        out[m] = back[m]
    return out


def man_body_c(P, mfr, hfr, hl):
    """C: lui esce dal costume fino al petto (clavicole, spalle magre, costole) e si apre la strada: le braccia
    lunghe piegate coi gomiti in fuori, le mani aggrappate ai due lembi della testa spaccata, a tenerli aperti."""
    f = sdf.union(
        sdf.round_cone(mfr.pt((0, 0.03, -0.10)), mfr.pt((0, 0.04, -0.22)), 0.052, 0.064),
        sdf.ellipsoid(mfr.pt((0, 0.05, -0.36)), (0.20, 0.11, 0.16)),
        tube([mfr.pt((-0.18, 0.04, -0.25)), mfr.pt((0, -0.035, -0.235)), mfr.pt((0.18, 0.04, -0.25))], 0.019, 0.019, n=4),
        k=0.04)
    for s in (-1, 1):
        f = sdf.union(f, sdf.sphere(mfr.pt((s * 0.21, 0.06, -0.28)), 0.058), k=0.05)
    ribs = [tube([mfr.pt((-0.16, 0.02, -0.32 - i * 0.042 + 0.02)), mfr.pt((0, -0.07, -0.32 - i * 0.042)),
                  mfr.pt((0.16, 0.02, -0.32 - i * 0.042 + 0.02))], 0.010, 0.010, n=4) for i in range(4)]
    f = sdf.union(f, *ribs, k=0.02)
    k = P.get('hand_k', 1.0)
    for s in (-1, 1):
        sh = mfr.pt((s * 0.21, 0.06, -0.28))
        elbow = hfr.pt((s * 0.44, 0.02, -0.12))
        wrist = hfr.pt(hl((s * 0.36, -0.20, 0.16)))
        f = sdf.union(f, chain([sh, elbow], [0.042, 0.032], k=0.0), sdf.sphere(elbow, 0.036), k=0.03)
        f = sdf.union(f, man_hand(wrist, unit(hfr.dir((s * 1.0, -0.25, -0.9))), 0.85, P['seed'] + 130 + s, spread=0.45, k=k, elbow=elbow), k=0.02)
    f = sdf.displace(f, skin.wrinkles(P['seed'] + 120, 0.015, 1.0), 0.0015)
    return [mesh('ManChest', f, mfr.pos - V(0.75, 0.5, 0.75), mfr.pos + V(0.75, 0.5, 0.25), drowned(), res=0.003 if not FAST else 0.005,
                 attrs={'slime': lambda p: np.full(len(p), 0.3, F)})]


VARIANTS = {
    'A': dict(
        label='A · Pupazzo', seed=11, soak=0.7, lumpy=0.004,
        desc='il costume quasi intero, dritto, le pinne aperte\nper l\'abbraccio come la statua; in fondo al sorriso\nsi vede appena la sua faccia, gli occhi bianchi',
        hip=(0, 0, 0.52), lean=-3.0, body_r=(0.50, 0.44, 0.56), belly_drop=0.02,
        head_c=(0, -0.01, 1.78), head_r=(0.50, 0.44, 0.40), head_yaw=0.0, head_pitch=3.0, head_roll=5.0, jet_droop=0.10,
        mouth=(0.30, 0.12, -0.15, 0.9), eyes={1: 'ok', -1: 'hang'}, eye_hang=(-0.06, -0.06, -0.30), eye_look=(0.4, -0.7, -0.4),
        man_off=(0.0, -0.20, -0.14), man_rot=(0.0, 3.0, 3.0), bloat=0.004, jaw=24.0, missing_teeth=0.35,
        tail=[(0, 0.40, 0.45), (0, 0.62, 0.95), (0.02, 0.66, 1.55)],
        legR=((0.23, -0.04, 0.32), (0.24, -0.02, 0.10)), legL=((-0.23, -0.04, 0.32), (-0.24, -0.02, 0.10)),
        armR=((0.72, -0.10, 1.32), (0.88, -0.16, 1.44)), armL=((-0.72, -0.08, 1.30), (-0.88, -0.14, 1.40)),
        fin='whole', tears=tears_a, drips=8, strands=3, body_drips=[(0.36, -0.36, 1.10), (-0.14, -0.42, 0.66)],
        face_cam=((-0.12, -1.25, 1.70), 62),
    ),
    'B': dict(
        label='B · Fradicio', seed=23, soak=1.3, lumpy=0.012,
        desc='il costume gonfio d\'acqua che cede: curvo, la pancia\nche pende, la testa crollata di lato; dalle pinne sfondate\nescono le sue mani. La faccia gonfia spinta fuori dalla bocca',
        hip=(0, 0.10, 0.46), lean=22.0, body_r=(0.54, 0.47, 0.54), belly_drop=0.16, torso_roll=-4.0,
        head_c=(0.18, -0.42, 1.40), head_r=(0.50, 0.44, 0.40), head_yaw=-10.0, head_pitch=20.0, head_roll=-36.0, jet_droop=0.26,
        mouth=(0.27, 0.13, -0.10, 0.5), eyes={-1: 'gone', 1: 'hang'}, eye_hang=(0.05, -0.06, -0.36), eye_look=(-0.3, -0.5, -0.8),
        man_off=(0.0, -0.31, -0.125), man_rot=(0.0, -16.0, 14.0), bloat=0.016, jaw=32.0, missing_teeth=0.5, lid=0.15,
        tail=[(0, 0.42, 0.30), (0, 0.80, 0.20), (0.10, 1.25, 0.12)],
        legR=((0.26, -0.18, 0.30), (0.28, -0.08, 0.10)), legL=((-0.22, -0.06, 0.32), (-0.24, 0.04, 0.10)),
        armR=((0.64, -0.36, 0.86), (0.60, -0.52, 0.52)), armL=((-0.64, -0.26, 0.88), (-0.62, -0.38, 0.50)),
        fin='hands', fin_len=0.22, curl=0.55, hand_k=1.55, tears=tears_b, drips=10, strands=4,
        body_drips=[(0.30, -0.62, 0.80), (-0.15, -0.58, 0.62), (0.0, -0.52, 0.48)],
        face_cam=((-0.22, -1.62, 1.20), 62),
    ),
    'C': dict(
        label='C · Sventrato', seed=37, soak=1.0, lumpy=0.008,
        desc='la testa del costume spaccata in due dalla bocca in su,\nle metà aperte come un cappuccio: lui, alto e scheletrico,\nesce fino al petto; il costume gli pende addosso come una pelle',
        hip=(0, 0.02, 0.62), lean=6.0, body_r=(0.44, 0.40, 0.52), belly_drop=0.06,
        head_c=(0, 0.04, 1.84), head_r=(0.48, 0.43, 0.39), head_yaw=0.0, head_pitch=0.0, head_roll=0.0, jet_droop=0.20,
        split=split_c, mouth=(0.28, 0.12, -0.15, 0.9), eyes={1: 'gone', -1: 'hang'}, eye_hang=(-0.03, -0.06, -0.38), eye_look=(0.2, -0.7, -0.6),
        man_off=(0.0, -0.10, 0.20), man_rot=(6.0, 8.0, 9.0), bloat=-0.004, jaw=36.0, missing_teeth=0.4, hair=10,
        man_body=man_body_c, eye_up=0.05,
        tail=[(0, 0.38, 0.40), (0, 0.66, 0.70), (0.05, 0.80, 0.55)],
        legR=((0.19, -0.06, 0.40), (0.20, -0.02, 0.10)), legL=((-0.19, 0.0, 0.40), (-0.21, 0.03, 0.10)),
        armR=((0.56, -0.10, 1.10), (0.58, -0.16, 0.74)), armL=((-0.54, -0.04, 1.10), (-0.58, -0.06, 0.72)),
        fin='whole', fin_len=0.36, curl=0.35, hand_k=1.35, tears=tears_c, drips=0, strands=0,
        body_drips=[(0.30, -0.34, 1.30), (-0.22, -0.36, 1.10)],
        face_cam=((-0.24, -1.30, 2.10), 52),
    ),
}


# ───────────────────────── scena, render, tavola ─────────────────────────

def render_variant(key):
    P = VARIANTS[key]
    os.makedirs(TMP, exist_ok=True)
    sc = reset_scene()
    obs, face, mfr = build(P)
    names = [o.name for o in obs]
    keep = {n: bpy.data.objects[n] for n in names}
    # due inquadrature con la stessa scena: si salva la scena come .blend per non ricostruire
    blend = os.path.join(TMP, f'{key}.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    out = []
    W, H = (360, 520) if FAST else (720, 1040)
    full_cam = ((-1.15, -4.6, 1.25), (0.0, -0.10, 1.20), 50)
    for kind in ('intero', 'faccia'):
        bpy.ops.wm.open_mainfile(filepath=blend)
        sc = bpy.context.scene
        if kind == 'intero':
            loc, tgt, lens = full_cam
            w_, h_ = W, H
        else:
            (loc, lens), tgt = P['face_cam'], tuple(map(float, face + V(0, 0, -0.02)))
            w_, h_ = W, int(W * 0.86)
        _setup_into(sc, tgt, face, loc, lens, w_, h_)
        path = os.path.join(TMP, f'{key}_{kind}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('ok', key, kind, flush=True)
    return out


def _setup_into(sc_unused, target, face, cam_loc, lens, W, H):
    """Come scene(), ma sopra la scena caricata dal .blend (gli oggetti del mostro ci sono già)."""
    objs = [o for o in bpy.data.objects]
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.max_bounces = 8
    sc.cycles.transmission_bounces = 8
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.cycles.use_denoising = True
    w = bpy.data.worlds.new('Notte')
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.006, 0.009, 0.016, 1)
    cam_d = bpy.data.cameras.new('Cam')
    cam_d.lens = lens
    cam_d.sensor_fit = 'VERTICAL' if H > W else 'HORIZONTAL'
    cam_d.sensor_width = 36.0
    cam_d.sensor_height = 36.0
    cam = bpy.data.objects.new('Cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    from mathutils import Vector
    cam.location = cam_loc
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = (Vector(target) - Vector(cam_loc)).to_track_quat('-Z', 'Y')
    lights(face)
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
    fl = bpy.context.object
    fl.data.materials.append(floor_material())
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 20 if FAST else 128
    sc.render.image_settings.file_format = 'PNG'


def lights(face):
    """La lampara calda da davanti e dal basso (dalla barca), la luna fredda dietro e di lato, quasi niente
    riempimento; una lucina calda davanti alla bocca del costume, per staccare la faccia dal buio."""
    s = np.array(face, float)
    D.area_light('Key', tuple(s + (-1.1, -2.1, -1.0)), tuple(s), 110, (1.0, 0.62, 0.32), 0.5)
    D.area_light('Rim', tuple(s + (1.3, 1.5, 0.9)), tuple(s - (0, 0, 0.6)), 150, (0.42, 0.60, 1.0), 0.7)
    D.area_light('Rim2', tuple(s + (-1.5, 1.2, 0.3)), tuple(s - (0, 0, 0.8)), 70, (0.38, 0.56, 1.0), 0.7)
    D.area_light('Fill', tuple(s + (1.6, -2.2, 0.6)), tuple(s), 3, (0.55, 0.65, 0.85), 2.0)
    D.point_light('FaceFill', tuple(s + (0.03, -0.32, -0.04)), 0.5, (1.0, 0.78, 0.55), radius=0.04)


def tavola():
    keys = 'ABC'
    cols = []
    for k in keys:
        a = Image.open(os.path.join(TMP, f'{k}_intero.png')).convert('RGB')
        b = Image.open(os.path.join(TMP, f'{k}_faccia.png')).convert('RGB')
        cols.append((a, b))
    W = cols[0][0].size[0]
    Ha, Hb = cols[0][0].size[1], cols[0][1].size[1]
    gap = 16
    head, foot = 84, 150
    big = 1 if FAST else 2
    sheet = Image.new('RGB', (W * 3 + gap * 4, head + Ha + gap + Hb + foot), (12, 14, 19))
    d = ImageDraw.Draw(sheet)
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf'
    try:
        tf = ImageFont.truetype(font.format('-Bold'), 17 * big)
        lf = ImageFont.truetype(font.format('-Bold'), 16 * big)
        sf = ImageFont.truetype(font.format(''), 11 * big)
    except OSError:
        tf = lf = sf = ImageFont.load_default()
    d.text((gap, 14), "L'ANIMATORE — tre varianti (notte 2): figura intera e primo piano · da approvare", fill=(235, 228, 210), font=tf)
    d.text((gap, 14 + 21 * big), "l'animatore di Splashland annegato dentro il costume di Mama Marina", fill=(170, 166, 156), font=sf)
    for i, (k, (a, b)) in enumerate(zip(keys, cols)):
        x = gap + i * (W + gap)
        sheet.paste(a, (x, head))
        sheet.paste(b, (x, head + Ha + gap))
        P = VARIANTS[k]
        y = head + Ha + gap + Hb + 10
        d.text((x + 4, y), P['label'], fill=(255, 179, 92), font=lf)
        d.multiline_text((x + 4, y + 20 * big), P['desc'], fill=(200, 196, 184), font=sf, spacing=4)
    path = os.path.join(OUT, 'foxy_varianti.jpg' if not FAST else 'foxy_varianti_bozza.jpg')
    sheet.save(path, quality=92)
    return path


def prova_uomo(key):
    """Solo la testa dell'uomo, di tre quarti: per mettere a punto la faccia."""
    P = dict(VARIANTS[key])
    reset_scene()
    fr = Fr(V(0, 0, 1.6), rot(-28.0, 0.0, 0.0))
    man_head(P, fr)
    sc = bpy.context.scene
    _setup_into(sc, (0, -0.05, 1.59), (0, -0.1, 1.6), (0, -0.75, 1.62), 70, 480, 480)
    bpy.data.objects['FaceFill'].data.energy = 2.0
    sc.render.filepath = os.path.join(TMP, f'uomo_{key}.png')
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    if '--uomo' in sys.argv:
        prova_uomo(sys.argv[sys.argv.index('--uomo') + 1])
        sys.exit(0)
    if '--tavola' not in sys.argv:
        keys = 'ABC'
        if '--only' in sys.argv:
            keys = sys.argv[sys.argv.index('--only') + 1]
        for k in keys:
            render_variant(k)
    if '--only' not in sys.argv:
        print('tavola', tavola(), flush=True)
