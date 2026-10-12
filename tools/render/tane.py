"""
Le tane delle immersioni (lavoro approvato il 12 ottobre; aspetto DA APPROVARE): sette camerette sommerse, una per
bambino, rifatte dalla Madre con le cose della sua vita, in grotte laterali della grotta grande (docs/IMMERSIONI.md,
«Le tane»). Ognuna è un'inquadratura fissa come «sotto la barca»: un panorama parziale che si gira di 30° per parte.

Coordinate di una tana (metri, z in alto): il pavimento di sabbia è a z = 0, il sub entra da sud (−Y) e galleggia
in OCCHIO_T guardando avanti e un po' in giù (PITCH_T); la cameretta è una sala di roccia di circa 10 × 9 m, alta
4-5 m, con il tunnel d'ingresso alle spalle del sub.

Ogni tana ha tre pezzi:
  - la cameretta vuota (arredi, la cosa da trovare per il diario): è anche la tana vuota del mostro nuovo della
    notte dopo, che è già in giro;
  - il mostro addormentato nella sua forma di adesso (i modelli dei mostri, ricostruiti in una posa di sonno e
    portati nella stanza con una trasformazione), che nel gioco è uno strato sopra la cameretta;
  - la toppa del respiro (la stessa posa con il fiato preso), che il gioco dissolve sopra la posa.

Le cose da trovare (il diario) sono disegni, foto e oggetti dipinti con PIL (immagini in cache) su fogli e cartoncini.
"""
from __future__ import annotations

import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

import deco
import grotte
import sdf
from common import CACHE, collection, set_lightgroup
from geo import catmull, cylinder, lathe, rbox, sweep, tube, rect_profile
from nodes import material

COL = grotte.COL
F = np.float32

OCCHIO_T = (0.0, -2.7, 1.5)       # l'occhio del sub, appena entrato dal tunnel
PITCH_T = -15.0                   # lo sguardo al centro dell'inquadratura (come il frame del motore)
CENTRO = (0.0, 1.9, 0.0)          # dove dorme il mostro, di solito: in fondo al centro

ORDINE = ('gulpy', 'molly', 'hatch', 'robin', 'archie', 'lampy', 'fangy')


# ───────────────────────── la stanza ─────────────────────────

_N = sdf.Noise3(1207)


def stanza(p):
    """Il campo della cameretta: < 0 nell'acqua. Una sala bassa e larga, il tunnel d'ingresso alle spalle del sub."""
    p = np.asarray(p, F)
    d = sdf.ellipsoid((0.0, 1.1, 1.3), (4.7, 4.3, 3.3))(p)
    d = sdf.smin(d, sdf.capsule((0.0, -2.6, 1.5), (0.0, -10.0, 1.8), 1.6)(p), 1.0)
    d = d + 0.45 * _N(p, 2.6, 3) + 0.12 * _N(p + 30.0, 0.8, 2)
    d = sdf.smax(d, -p[:, 2] + 0.08 * _N(p * F(0.5), 1.0, 2), 0.35)      # il pavimento di sabbia a z ≈ 0
    return d.astype(F)


def build_stanza(res=0.07):
    f = lambda p: -stanza(p)
    v, fc, n = sdf.mesh_banded(f, (-7.5, -12.5, -1.0), (7.5, 7.5, 6.0), res=res, coarse=4)
    sab = np.clip((0.35 - v[:, 2]) / 0.3, 0, 1) * np.clip((n[:, 2] - 0.45) / 0.35, 0, 1)
    ob = grotte.mesh_obj('TanaRoccia', v, fc, {'sabbia': sab})
    ob.data.materials.append(grotte.rock_material())
    return ob, v, n, sab


def build_luci(tinta=(0.45, 0.80, 0.78)):
    """La luce dell'acqua che entra dal tunnel alle spalle del sub, un filo di luce diffusa nella stanza; la torcia
    (lantern) sull'occhio per il panorama."""
    from nodes import world
    w, g = world('TanaAcqua')
    w.lightgroup = 'ambient'
    g.output_world(g.background((0.0, 0.0, 0.0), 0.0))
    w.mist_settings.start = 0.0
    w.mist_settings.depth = grotte.MIST_DEPTH
    w.mist_settings.falloff = 'LINEAR'
    d = bpy.data.lights.new('TanaIngresso', 'AREA')
    d.energy = 900.0
    d.color = tinta
    d.size = 3.0
    o = bpy.data.objects.new('TanaIngresso', d)
    collection(COL).objects.link(o)
    o.location = (0.0, -8.5, 2.2)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(Vector((0.0, 1.0, -0.25)))
    set_lightgroup(o, 'ambient')
    d2 = bpy.data.lights.new('TanaDiffusa', 'POINT')
    d2.energy = 260.0
    d2.color = tinta
    d2.shadow_soft_size = 2.0
    o2 = bpy.data.objects.new('TanaDiffusa', d2)
    collection(COL).objects.link(o2)
    o2.location = (0.0, -0.5, 3.4)
    set_lightgroup(o2, 'ambient')


def build_vita(v, n, sab, seed=3):
    """Un po' della vita della grotta (meno che nella sala grande): anemoni e spugne sulle pareti, alghe sul fondo."""
    rr = np.random.default_rng(seed)
    an = grotte.per_oggetto('GrottaAnemone', rough=0.45, sss=0.6, tips=(0.10, 0.2))
    modelli = [grotte.anemone_mesh('TAnemone%d' % k, 140 + k, tent=18 + 4 * k, h=0.08 + 0.03 * k, r=0.03 + 0.01 * k) for k in range(2)]
    d = np.linalg.norm(v - np.array(OCCHIO_T), axis=1)
    ok = np.nonzero((sab < 0.05) & (d > 2.0) & (d < 9.0) & (v[:, 1] > -3.0))[0]
    for k, i in enumerate(rr.choice(ok, 60, replace=False)):
        grotte.istanza('Anemone', modelli[k % 2], tuple(v[i] - n[i] * 0.01), tuple(n[i]), rr.uniform(0, 6.28),
                       rr.uniform(1.0, 2.2), an, [(0.55, 0.36, 0.34), (0.58, 0.55, 0.48), (0.40, 0.30, 0.40)][k % 3])
    # ciottoli, conchiglie rotte e qualche masso sul pavimento, anche davanti al sub (se no la sabbia è vuota)
    sa_mat = grotte.per_oggetto('GrottaCiottolo', rough=0.5, sss=0.0)
    sassi = [grotte.sasso_mesh('TCiottolo%d' % k, 190 + k) for k in range(4)]
    for k in range(170):
        x, y = rr.uniform(-4.2, 4.2), rr.uniform(-2.2, 4.5)
        if stanza(np.array([[x, y, 0.25]], F))[0] > -0.1:
            continue
        sc = rr.uniform(0.03, 0.12) if rr.random() < 0.9 else rr.uniform(0.2, 0.45)
        g_ = rr.uniform(0.05, 0.16)
        grotte.istanza('Ciottolo', sassi[k % 4], (x, y, sc * 0.2), (rr.normal(0, 0.2), rr.normal(0, 0.2), 1),
                       rr.uniform(0, 6.28), sc, sa_mat, (g_, g_ * 0.95, g_ * 0.85))
    alga = grotte.alga_material()
    piedi = np.nonzero((sab > 0.6) & (np.abs(v[:, 0]) > 2.6) & (v[:, 1] > -2.0))[0]
    for c in rr.choice(piedi, 14, replace=False):
        for j in range(rr.integers(3, 7)):
            p0 = v[c] + np.array((*rr.normal(0, 0.2, 2), -0.05))
            L = rr.uniform(0.4, 1.6)
            ph = rr.uniform(0, 6.28)
            pts = [p0 + np.array((0.15 * L * t * math.sin(ph + t * 5.0), 0.1 * t, t * L)) for t in np.linspace(0, 1, 12)]
            ob = sweep('Alga', pts, rect_profile(rr.uniform(0.04, 0.08), 0.004), col=COL, cap=False,
                       up=(math.cos(ph), math.sin(ph), 0), scale=np.linspace(1.0, 0.3, 12))
            ob.data.materials.append(alga)
            ob.color = (0.10, 0.12, 0.03, 1.0)
            set_lightgroup(ob, 'ambient')


# ───────────────────────── piccoli aiuti per gli arredi ─────────────────────────

def _lg(obs):
    for o in obs if isinstance(obs, (list, tuple)) else [obs]:
        set_lightgroup(o, 'ambient')
    return obs


def scatola(name, size, loc, rot=(0, 0, 0), mat=None, bevel=0.01):
    o = rbox(name, size, loc, rot=rot, bevel=bevel, segments=2, col=COL)
    if mat is not None:
        o.data.materials.append(mat)
    return _lg(o)


def cilindro(name, r, h, loc, rot=(0, 0, 0), mat=None, verts=20):
    o = cylinder(name, r, h, loc, rot=rot, verts=verts, col=COL)
    if mat is not None:
        o.data.materials.append(mat)
    return _lg(o)


def palla(name, r, loc, mat=None, scale=(1, 1, 1)):
    import geo
    o = geo.sphere(name, r, loc, segs=20, rings=10, col=COL, scale=scale)
    if mat is not None:
        o.data.materials.append(mat)
    return _lg(o)


def scritta(name, body, size, loc, rot, mat, extrude=0.01, font='Limelight-Regular'):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.font = deco.font(font)
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    ob = bpy.data.objects.new(name, cu)
    collection(COL).objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    ob.data.materials.append(mat)
    return _lg(ob)


def telo(name, size, loc, rot=(0, 0, 0), mat=None, onde=0.08, seed=0, giu=0.0):
    """Un telo (asciugamano, striscione, benda): un piano suddiviso, mosso dal rumore e che cade in giù ai bordi."""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=24, size=1.0)
    o = bpy.context.object
    for c in list(o.users_collection):
        c.objects.unlink(o)
    collection(COL).objects.link(o)
    o.name = name
    rr = np.random.default_rng(seed)
    ph = rr.uniform(0, 6.28, 3)
    for vtx in o.data.vertices:
        x, y = vtx.co.x * size[0], vtx.co.y * size[1]
        z = onde * (math.sin(x * 3.1 + ph[0]) * 0.6 + math.sin(y * 2.3 + ph[1]) * 0.4)
        z -= giu * (abs(vtx.co.x) * 2) ** 2
        vtx.co = Vector((x, y, z))
    for p in o.data.polygons:
        p.use_smooth = True
    o.location = loc
    o.rotation_euler = rot
    if mat is not None:
        o.data.materials.append(mat)
    return _lg(o)


def legno(name='TanaLegno', color=(0.20, 0.12, 0.06)):
    return grotte.plastica(name, color, rough=0.75, melma=0.5)


def strisce_material(name, c1, c2, passo=0.18, asse=0, melma=0.4):
    """Bande di due colori lungo un asse dell'oggetto (tende a strisce, asciugamani, tovaglie)."""
    def b(n):
        m, g = material(n)
        co = g.texcoord('Object')
        x = g.sep(co)[asse]
        band = g.smoothstep(0.45, 0.55, g.math('PINGPONG', x, passo))
        col = g.mix(band, c1, c2)
        sl = g.smoothstep(1.0 - melma, 1.0 - melma + 0.25, g.noise(co, scale=5.0, detail=8.0, rough=0.7, distortion=0.8).fac)
        col = g.mix(g.mul(sl, 0.8), col, g.mix(0.5, col, (0.035, 0.045, 0.02)))
        g.output_material(g.principled(color=col, rough=0.8, sheen=0.3))
        return m
    return grotte._mat(name, b)


def immagine_material(name, path, rough=0.6, emission=0.0):
    """Un foglio o una foto: l'immagine sul piano (coordinate UV della griglia), con la carta che si scurisce
    bagnata ai bordi."""
    def b(n):
        m, g = material(n)
        uv = g.texcoord('UV')
        col, _ = g.image(path, uv, extension='CLIP')
        x, y, _ = g.sep(uv)
        bordo = g.mul(g.smoothstep(0.0, 0.08, x), g.mul(g.smoothstep(1.0, 0.92, x), g.mul(g.smoothstep(0.0, 0.08, y), g.smoothstep(1.0, 0.92, y))))
        col = g.mix(g.sub(1.0, bordo), col, g.mul(col, 0.55))
        kw = dict(color=col, rough=rough, sss=0.1, sss_radius=(1.0, 0.5, 0.3), sss_scale=0.005)
        if emission:
            kw.update(emission=col, emission_strength=emission)
        g.output_material(g.principled(**kw))
        return m
    return grotte._mat(name, b)


def foglio(name, path, size, loc, rot, curva=0.02, emission=0.0):
    """Un foglio di carta (o una foto) col suo disegno: piano con le UV, appena incurvato."""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=1.0, calc_uvs=True)
    o = bpy.context.object
    for c in list(o.users_collection):
        c.objects.unlink(o)
    collection(COL).objects.link(o)
    o.name = name
    for vtx in o.data.vertices:
        x, y = vtx.co.x * size[0], vtx.co.y * size[1]
        vtx.co = Vector((x, y, curva * math.sin(vtx.co.x * 3.0) + curva * 0.5 * vtx.co.y ** 2))
    o.location = loc
    o.rotation_euler = rot
    o.data.materials.append(immagine_material(name + 'Mat', path, emission=emission))
    return _lg(o)


# ───────────────────────── le cose da trovare (immagini) ─────────────────────────

def _carta(w, h, colore=(232, 226, 205)):
    from PIL import Image
    im = Image.new('RGB', (w, h), colore)
    return im


def disegno(nome):
    """Disegna a pastelli (PIL) la cosa da trovare di una tana e restituisce il percorso dell'immagine."""
    from PIL import Image, ImageDraw, ImageFilter
    path = os.path.join(CACHE, 'tane', f'trovato_{nome}.png')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rr = np.random.default_rng(len(nome) * 17)
    W, H = 512, 384
    im = _carta(W, H)
    dr = ImageDraw.Draw(im)

    def segno(pts, col, w=6):
        pts = [(x + rr.normal(0, 1.5), y + rr.normal(0, 1.5)) for x, y in pts]
        dr.line(pts, fill=col, width=w, joint='curve')

    def cerchio(c, r, col, w=6, fill=None):
        a = np.linspace(0, 2 * np.pi, 40)
        pts = [(c[0] + r * math.cos(t) * rr.uniform(0.95, 1.05), c[1] + r * math.sin(t) * rr.uniform(0.95, 1.05)) for t in a]
        if fill:
            dr.polygon(pts, fill=fill)
        segno(pts, col, w)
    if nome == 'gulpy':
        # un bambino con la bocca enorme davanti allo Snack Shack, e un panino più grande di lui
        dr.rectangle((40, 120, 230, 330), outline=(180, 30, 30), width=6)
        for k in range(6):
            dr.rectangle((40 + k * 32, 90, 72 + k * 32, 125), fill=(200, 40, 40) if k % 2 == 0 else (240, 240, 230))
        dr.text((60, 140), 'SNACK', fill=(30, 30, 160))
        cerchio((340, 220), 60, (40, 40, 40))
        dr.chord((300, 210, 380, 290), 0, 180, fill=(150, 20, 20))
        segno([(340, 280), (340, 360)], (40, 40, 40))
        segno([(340, 300), (300, 330)], (40, 40, 40))
        segno([(340, 300), (380, 330)], (40, 40, 40))
        cerchio((450, 160), 45, (170, 110, 40), fill=(220, 170, 80))
        segno([(410, 160), (490, 160)], (40, 140, 40), 8)
        dr.text((300, 30), 'IO E IL PANINO GIGANTE', fill=(40, 40, 40))
    elif nome == 'molly':
        # una foto: la bambina in cima al trampolino, i braccioli, le braccia alzate
        im = Image.new('RGB', (W, H), (90, 150, 190))
        dr = ImageDraw.Draw(im)
        dr.rectangle((0, 280, W, H), fill=(40, 110, 160))
        dr.rectangle((60, 170, 300, 186), fill=(230, 230, 220))
        dr.rectangle((70, 186, 90, 300), fill=(200, 200, 190))
        cerchio((260, 110), 24, (240, 200, 170), fill=(240, 200, 170))
        dr.rectangle((246, 134, 274, 172), fill=(210, 40, 90))
        segno([(250, 140), (225, 90)], (240, 200, 170))
        segno([(270, 140), (295, 90)], (240, 200, 170))
        for x in (226, 294):
            cerchio((x, 112), 10, (240, 120, 30), fill=(240, 140, 40))
        im = im.filter(ImageFilter.GaussianBlur(1.2))
        dr = ImageDraw.Draw(im)
        dr.rectangle((0, 0, W - 1, H - 1), outline=(240, 236, 220), width=18)
        dr.text((30, 350), 'GUARDAMI! - giugno 1997', fill=(60, 60, 60))
    elif nome == 'hatch':
        # la conta: i numeri da 1 a 10 scritti e riscritti, sempre più fitti
        for k in range(70):
            x, y = rr.uniform(10, W - 40), rr.uniform(10, H - 30)
            dr.text((x, y), str(rr.integers(1, 11)), fill=(30, 30, 120) if k % 3 else (160, 20, 20))
        dr.text((140, 170), '...DIECI! CHI C\'E\' C\'E\'', fill=(10, 10, 10))
    elif nome == 'robin':
        # una pagina di quaderno: l'elenco delle cose prese, con le crocette
        for y in range(40, H, 24):
            dr.line((20, y, W - 20, y), fill=(150, 170, 210), width=1)
        righe = ['scarpe rosse', 'macchinina', 'occhiali da sole', 'cappellino blu', 'pallone', 'braccialetto',
                 '1000 biglietti', 'ANCORA']
        for k, t in enumerate(righe):
            dr.text((60, 28 + k * 24 * 1.3), f'[x] {t}', fill=(40, 40, 50))
    elif nome == 'archie':
        # il biglietto d'auguri, con le candeline disegnate e una spenta
        dr.rectangle((20, 20, W - 20, H - 20), outline=(200, 40, 40), width=8)
        dr.text((150, 50), 'TANTI AUGURI!', fill=(200, 40, 40))
        dr.rectangle((150, 200, 360, 300), fill=(240, 200, 220), outline=(150, 60, 90), width=5)
        for k in range(7):
            x = 170 + k * 28
            dr.rectangle((x, 160, x + 8, 200), fill=(60, 120, 200))
            if k != 3:
                cerchio((x + 4, 148), 7, (240, 160, 30), fill=(250, 200, 50))
        dr.text((140, 320), 'per il compleanno di tutti', fill=(60, 60, 60))
    elif nome == 'lampy':
        # il braccialetto dell'ospedale da neonata, disegnato come un cartoncino: e una manina
        dr.rounded_rectangle((60, 140, 450, 230), 30, fill=(250, 210, 225), outline=(200, 120, 150), width=4)
        dr.text((100, 165), 'NEONATA  -  KG 3,1', fill=(80, 40, 60))
        cerchio((260, 320), 30, (230, 180, 160), fill=(240, 200, 180))
        dr.text((120, 40), 'non lasciarla mai andare', fill=(80, 80, 80))
    elif nome == 'fangy':
        # un disegno fatto a occhi bendati: scarabocchi che non si toccano, e in mezzo "MARCO?"
        for k in range(14):
            pts = [(rr.uniform(20, W - 20), rr.uniform(20, H - 20)) for _ in range(5)]
            segno(pts, (30, 30, 30), 4)
        dr.text((200, 180), 'MARCO?', fill=(160, 20, 20))
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    im.save(path)
    return path


# ───────────────────────── gli arredi delle sette tane ─────────────────────────
# Ogni funzione costruisce la cameretta senza il mostro e restituisce dove sono la cosa da trovare (per il diario)
# e il letto (dove dorme il mostro).

def tana_gulpy():
    """Il chiosco degli snack del parco smontato e rimontato: carte di merendine, cestini del pranzo, una pila di
    salvagenti a paperella su cui dorme."""
    rr = np.random.default_rng(11)
    rosso = grotte.plastica('TGRosso', (0.45, 0.04, 0.03), melma=0.45)
    tenda = strisce_material('TGTenda', (0.45, 0.04, 0.03), (0.62, 0.60, 0.55), passo=0.25, asse=0)
    # il chiosco a sinistra: il bancone, i montanti, la tenda a strisce, l'insegna
    scatola('Bancone', (2.6, 0.9, 1.05), (-3.0, 2.6, 0.5), rot=(0, 0, 0.35), mat=rosso)
    for dx in (-1.25, 1.25):
        x = -3.0 + dx * math.cos(0.35)
        y = 2.6 + dx * math.sin(0.35)
        cilindro('Montante', 0.05, 2.4, (x, y, 1.2), mat=grotte.semplice('GrottaRuggine', (0.16, 0.06, 0.02), rough=0.8))
    telo('Tenda', (2.9, 1.2), (-3.0, 2.3, 2.35), rot=(math.radians(-25), 0, 0.35), mat=tenda, onde=0.04, giu=0.05)
    scritta('Insegna', 'SNACK SHACK', 0.34, (-2.85, 1.9, 2.75), (math.radians(80), 0, 0.35),
            grotte.plastica('TGInsegna', (0.75, 0.62, 0.10), melma=0.3), extrude=0.03)
    # la pila di salvagenti a paperella: il letto
    duck = grotte.plastica('PaperellaGialla', (0.86, 0.62, 0.10), rough=0.3, melma=0.5)
    for k in range(18):
        a = rr.uniform(0, 6.28)
        r = rr.uniform(0.0, 1.2)
        c = (CENTRO[0] + r * math.cos(a), CENTRO[1] + r * math.sin(a) * 0.7, 0.12 + 0.18 * (k // 5))
        o = sdf_ring('Salvagente', c, rr.uniform(0.0, 0.5), rr.uniform(0, 6.28), duck)
    # carte di merendine e cestini del pranzo sparsi
    colori = [(0.7, 0.1, 0.1), (0.1, 0.3, 0.7), (0.8, 0.6, 0.1), (0.2, 0.5, 0.2), (0.7, 0.3, 0.6)]
    # lo scaffale delle merendine dietro il bancone
    scaffale = legno('TGScaffale', (0.25, 0.15, 0.08))
    for j in range(3):
        scatola('Ripiano', (2.2, 0.35, 0.04), (-3.3, 3.2, 0.6 + j * 0.55), rot=(0, 0, 0.35), mat=scaffale)
        for i in range(8):
            scatola('Merendina', (0.18, 0.12, 0.26), (-4.2 + i * 0.26 * math.cos(0.35), 2.9 + i * 0.26 * math.sin(0.35), 0.76 + j * 0.55),
                    rot=(0, rr.normal(0, 0.2), 0.35 + rr.normal(0, 0.1)), mat=grotte.plastica('TGCarta%d' % ((i + j) % 5), colori[(i + j) % 5], rough=0.3, melma=0.3))
    for k in range(90):
        x, y = rr.uniform(-4.0, 3.5), rr.uniform(-1.2, 3.8)
        scatola('Carta', (rr.uniform(0.12, 0.25), rr.uniform(0.06, 0.12), 0.01), (x, y, 0.02),
                rot=(rr.normal(0, 0.2), rr.normal(0, 0.2), rr.uniform(0, 6.28)),
                mat=grotte.plastica('TGCarta%d' % (k % 5), colori[k % 5], rough=0.3, melma=0.3), bevel=0.0)
    for k in range(8):
        x, y = rr.uniform(1.2, 3.6), rr.uniform(-0.5, 3.2)
        scatola('Cestino', (0.32, 0.18, 0.22), (x, y, 0.12), rot=(0, 0, rr.uniform(0, 3)),
                mat=grotte.plastica('TGCestino%d' % k, colori[(k + 2) % 5], rough=0.4, melma=0.5))
    # la cosa da trovare: il disegno a pastelli, appeso al bancone
    trov = (-2.3, 2.05, 0.75)
    foglio('Trovato', disegno('gulpy'), (0.42, 0.32), trov, (math.radians(85), 0, 0.35))
    return {'trovato': trov, 'letto': CENTRO}


def sdf_ring(name, c, tilt, spin, mat):
    """Un salvagente a paperella (più semplice di quello di Gulpy): l'anello e la testa."""
    R, r = 0.32, 0.12
    ring = sdf.torus((0, 0, 0), R, r, axis='z')
    head = sdf.union(sdf.capsule((0, -R, r * 0.5), (0, -R, r + 0.12), 0.09), sdf.sphere((0, -R - 0.02, r + 0.2), 0.12), k=0.06)
    v, f, _ = sdf.mesh(sdf.union(ring, head, k=0.03), (-0.5, -0.6, -0.15), (0.5, 0.5, 0.5), res=0.02)
    ob = grotte.mesh_obj(name, v, f)
    ob.data.materials.append(mat)
    ob.location = c
    ob.rotation_euler = (tilt, 0, spin)
    return ob


def tana_molly():
    """Il trampolino della piscina dentro la stanza, specchi dappertutto, le medaglie di nuoto, gli elastici rosa."""
    rr = np.random.default_rng(12)
    bianco = grotte.plastica('TMBianco', (0.62, 0.62, 0.58), melma=0.45)
    # il trampolino: la tavola che sporge sopra il letto, la scaletta
    scatola('Tavola', (0.6, 3.2, 0.08), (1.6, 1.4, 1.6), rot=(math.radians(-4), 0, 0), mat=bianco)
    scatola('Piedistallo', (0.5, 0.5, 1.5), (1.6, -0.1, 0.75), mat=bianco)
    for dx in (-0.25, 0.25):
        cilindro('Scaletta', 0.025, 1.9, (1.6 + dx, -0.5, 0.8), rot=(math.radians(-15), 0, 0),
                 mat=grotte.semplice('TMCromo', (0.6, 0.6, 0.6), rough=0.25, metal=1.0))
    # gli specchi: rettangoli lucidi appoggiati e appesi alla roccia, con la cornice
    specchio = grotte.semplice('TMSpecchio', (0.30, 0.34, 0.33), rough=0.12, metal=1.0)   # specchi ossidati, scuri
    cornice = grotte.plastica('TMCornice', (0.55, 0.42, 0.20), melma=0.4)
    for k, (x, y, a) in enumerate(((-3.9, 1.5, 1.2), (-3.2, 3.8, 0.6), (3.8, 3.4, -0.7), (4.2, 0.8, -1.3), (-1.0, 4.6, 0.05))):
        z = 1.0 + rr.uniform(0.0, 0.6)
        scatola('Cornice', (0.9, 0.08, 1.4), (x, y, z), rot=(rr.normal(0, 0.08), 0, a), mat=cornice)
        scatola('Specchio', (0.8, 0.02, 1.3), (x - 0.05 * math.sin(a), y - 0.05 * math.cos(a) * -1, z), rot=(0, 0, a), mat=specchio, bevel=0.0)
    # le medaglie appese a una cordicella
    oro = grotte.semplice('TMOro', (0.8, 0.6, 0.2), rough=0.3, metal=1.0)
    nastro = grotte.plastica('TMNastro', (0.10, 0.20, 0.60), melma=0.2)
    for k in range(6):
        x = -2.2 + k * 0.45
        z = 2.4 - 0.1 * math.sin(k)
        cilindro('Medaglia', 0.11, 0.015, (x, 4.3, z - 0.35), rot=(math.radians(90), 0, 0), mat=oro)
        scatola('Nastro', (0.05, 0.01, 0.3), (x, 4.32, z - 0.15), mat=nastro, bevel=0.0)
    tube('Cordicella', [(-2.5, 4.35, 2.45), (-1.0, 4.35, 2.3), (0.4, 4.35, 2.45)], 0.008, n=6, col=COL).data.materials.append(grotte.corda_material())
    # la corsia galleggiante della piscina, tirata da una parete all'altra sopra il letto
    galleggianti = [grotte.plastica('TMCorsia%d' % k, c, rough=0.3, melma=0.3) for k, c in enumerate(((0.55, 0.05, 0.05), (0.62, 0.60, 0.55), (0.05, 0.20, 0.55)))]
    for k in range(34):
        t = k / 33
        p = (-4.0 + 8.0 * t, 3.2 - 1.2 * t, 2.6 - 0.5 * math.sin(math.pi * t))
        cilindro('Galleggiante', 0.09, 0.2, p, rot=(0, math.radians(90), -0.15), mat=galleggianti[(k // 3) % 3], verts=12)
    # i braccioli sparsi
    arancio = grotte.plastica('TMBraccioli', (0.70, 0.30, 0.04), rough=0.3, melma=0.35)
    for k in range(6):
        palla('Bracciolo', 0.1, (rr.uniform(-3, 3), rr.uniform(0, 3.5), 0.08), mat=arancio, scale=(1.6, 1.0, 0.8))
    # gli elastici rosa sparsi sulla sabbia
    rosa = grotte.plastica('MollyElastico', (0.60, 0.07, 0.26), rough=0.4, melma=0.2)
    for k in range(14):
        x, y = rr.uniform(-2.5, 2.5), rr.uniform(0.5, 3.5)
        o = palla('Elastico', 0.03, (x, y, 0.02), mat=rosa, scale=(1.0, 1.0, 0.35))
    # la cosa da trovare: la foto sul trampolino
    trov = (1.6, 0.4, 1.66)
    foglio('Trovato', disegno('molly'), (0.30, 0.24), trov, (0, 0, math.radians(8)), curva=0.005)
    return {'trovato': trov, 'letto': (-0.6, 2.0, 0.0)}


def tana_hatch():
    """Piena di nascondigli: armadi, una tenda fatta di asciugamani; i numeri della conta scritti sulle pareti."""
    rr = np.random.default_rng(13)
    legn = legno('THLegno', (0.22, 0.13, 0.07))
    armadi = [(-3.2, 2.6, 0.5), (0.0, 3.6, 0.0), (3.3, 2.4, -0.5)]
    for k, (x, y, a) in enumerate(armadi):
        h = 3.3 if k == 1 else 2.4
        scatola('Armadio', (1.4, 0.7, h), (x, y, h / 2), rot=(0, 0, a), mat=legn)
        # le ante aperte, sui cardini degli spigoli davanti
        ca, sa = math.cos(a), math.sin(a)
        for sgn in (-1, 1):
            hx, hy = x + sgn * 0.7 * ca + 0.35 * sa, y + sgn * 0.7 * sa - 0.35 * ca      # il cardine (davanti è −y locale)
            ang = a + sgn * math.radians(rr.uniform(70, 115))
            w = 0.68
            scatola('Anta', (w, 0.04, h - 0.1), (hx - sgn * (w / 2) * math.cos(ang) * -1, hy - sgn * (w / 2) * math.sin(ang) * -1, h / 2),
                    rot=(0, 0, ang), mat=legn)
    # l'armadio grande in fondo è vuoto dentro (scuro): lì dorme Hatch
    scatola('ArmadioDentro', (1.25, 0.05, 3.1), (0.0, 3.27, 1.6), mat=grotte.semplice('THBuio', (0.01, 0.01, 0.01), rough=0.9))
    # la tenda di asciugamani a destra: due teli a capanna su un bastone tra due sedie
    tel = strisce_material('THAsciugamani', (0.55, 0.15, 0.10), (0.15, 0.35, 0.55), passo=0.3, asse=1)
    tx, ty = 2.6, 0.8
    cilindro('Bastone', 0.03, 2.4, (tx, ty, 1.3), rot=(math.radians(90), 0, math.radians(-25)), mat=legn)
    for sgn in (-1, 1):
        scatola('Sedia', (0.45, 0.45, 1.3), (tx + 1.05 * math.sin(math.radians(-25)) * sgn * -1, ty + 1.05 * math.cos(math.radians(-25)) * sgn, 0.65), rot=(0, 0, math.radians(-25)), mat=legn)
        telo('Asciugamano', (2.4, 1.6), (tx + sgn * 0.55 * math.cos(math.radians(-25)), ty + sgn * 0.55 * math.sin(math.radians(-25)), 0.66),
             rot=(sgn * math.radians(55), 0, math.radians(-25 + 90)), mat=tel, onde=0.05, seed=4 + sgn)
    # i numeri della conta scritti col gesso sulle pareti
    gesso = grotte.semplice('THGesso', (0.75, 0.74, 0.70), rough=0.9)
    for k in range(10):
        a = math.radians(-60 + k * 13)
        r = 4.3
        x, y = r * math.sin(a), 1.1 + r * math.cos(a) * 0.9
        scritta('Numero', str(k + 1), 0.6, (x, y, 2.2 + 0.3 * math.sin(k)), (math.radians(90), 0, -a + math.pi),
                gesso, extrude=0.005, font='Monoton-Regular')
    trov = (-2.6, 1.9, 1.1)
    foglio('Trovato', disegno('hatch'), (0.42, 0.32), trov, (math.radians(80), 0, 0.5))
    return {'trovato': trov, 'letto': (0.0, 3.2, 0.0)}


def tana_robin():
    """Un mucchio di cose rubate agli altri bambini (scarpe, giocattoli, oggetti smarriti) e i biglietti della sala
    giochi."""
    rr = np.random.default_rng(14)
    colori = [(0.6, 0.08, 0.06), (0.08, 0.25, 0.6), (0.75, 0.6, 0.1), (0.15, 0.45, 0.2), (0.6, 0.3, 0.55), (0.75, 0.72, 0.65)]
    mats = [grotte.plastica('TRCosa%d' % k, c, rough=0.4, melma=0.35) for k, c in enumerate(colori)]
    # il mucchio: tante piccole cose ammucchiate a cupola
    for k in range(260):
        a = rr.uniform(0, 6.28)
        r = 1.6 * math.sqrt(rr.uniform(0, 1))
        h = 0.9 * (1 - (r / 1.7) ** 2) + rr.uniform(0, 0.1)
        c = (CENTRO[0] + r * math.cos(a), CENTRO[1] + r * math.sin(a) * 0.8, h * rr.uniform(0.3, 1.0))
        kind = k % 4
        m = mats[rr.integers(0, len(mats))]
        rot = tuple(rr.uniform(0, 6.28, 3))
        if kind == 0:
            scatola('Scarpa', (0.26, 0.10, 0.09), c, rot=rot, mat=m)
        elif kind == 1:
            palla('Pallina', rr.uniform(0.05, 0.12), c, mat=m)
        elif kind == 2:
            scatola('Giocattolo', tuple(rr.uniform(0.08, 0.2, 3)), c, rot=rot, mat=m)
        else:
            cilindro('Secchiello', 0.07, 0.12, c, rot=rot, mat=m, verts=12)
    # i biglietti: strisce arancio che pendono e si avvolgono sul mucchio
    for k in range(6):
        a = rr.uniform(0, 6.28)
        pts = [(CENTRO[0] + (0.2 + 1.4 * t) * math.cos(a + t * 2), CENTRO[1] + (0.2 + 1.4 * t) * math.sin(a + t * 2) * 0.8,
                0.95 * (1 - t) ** 1.5 + 0.03) for t in np.linspace(0, 1, 30)]
        ob = sweep('Biglietti', pts, rect_profile(0.065, 0.002), col=COL, cap=False, up=(0, 0, 1))
        ob.data.materials.append(grotte.plastica('TRBiglietti', (0.80, 0.24, 0.02), melma=0.3))
        _lg(ob)
    trov = (1.9, 0.6, 0.05)
    foglio('Trovato', disegno('robin'), (0.30, 0.40), trov, (0, 0, math.radians(-20)), curva=0.01)
    return {'trovato': trov, 'letto': CENTRO}


def tana_archie():
    """Una festa di compleanno sommersa: il tavolo con la tovaglia, le torte con le candeline spente, i cappellini,
    i palloncini che galleggiano, lo striscione degli auguri."""
    rr = np.random.default_rng(15)
    c = np.array(CENTRO) + np.array((0.0, 0.3, 0.0))
    tov = strisce_material('TATovaglia', (0.62, 0.60, 0.55), (0.45, 0.06, 0.08), passo=0.12, asse=0)
    cilindro('Tavolo', 0.95, 0.06, (c[0], c[1], 0.78), mat=tov, verts=40)
    cilindro('Gamba', 0.08, 0.76, (c[0], c[1], 0.38), mat=legno('TALegno'))
    telo('Tovaglia', (2.0, 2.0), (c[0], c[1], 0.80), mat=tov, onde=0.02, giu=0.18, seed=7)
    rosa = grotte.plastica('TATorta', (0.70, 0.45, 0.50), melma=0.4)
    for k, (dx, dy) in enumerate(((-0.35, 0.1), (0.35, -0.15), (0.0, 0.45))):
        cilindro('Torta', 0.22, 0.18, (c[0] + dx, c[1] + dy, 0.93), mat=rosa, verts=24)
        for j in range(7):
            a = 2 * math.pi * j / 7
            cilindro('Candelina', 0.012, 0.09, (c[0] + dx + 0.14 * math.cos(a), c[1] + dy + 0.14 * math.sin(a), 1.065),
                     mat=grotte.plastica('TACandela%d' % (j % 3), [(0.1, 0.3, 0.7), (0.7, 0.6, 0.1), (0.15, 0.5, 0.2)][j % 3]))
    # i cappellini a cono
    for k in range(6):
        a = rr.uniform(0, 6.28)
        r = rr.uniform(1.2, 2.6)
        o = lathe('Cappellino', [(0.09, 0.0), (0.0, 0.24)], n=16, col=COL, close_bottom=True)
        o.location = (c[0] + r * math.cos(a), c[1] + r * math.sin(a), 0.02)
        o.rotation_euler = (rr.normal(0, 0.8), rr.normal(0, 0.8), 0)
        o.data.materials.append(grotte._mat('ArchieCarta', grotte._carta))
        _lg(o)
    # i palloncini che galleggiano, legati al tavolo o incastrati sotto la volta
    cols = [(0.6, 0.05, 0.08), (0.08, 0.2, 0.6), (0.7, 0.55, 0.05), (0.1, 0.45, 0.15), (0.55, 0.15, 0.5)]
    for k in range(9):
        p = (c[0] + rr.normal(0, 1.8), c[1] + rr.normal(0, 1.2), rr.uniform(2.6, 3.8))
        palla('Palloncino', 0.2, p, mat=grotte.plastica('TAPalloncino%d' % (k % 5), cols[k % 5], rough=0.2, melma=0.15), scale=(1, 1, 1.2))
        tube('Spago', [(p[0], p[1], p[2] - 0.24), ((p[0] + c[0]) / 2, (p[1] + c[1]) / 2, p[2] * 0.5), (c[0], c[1], 0.8)],
             0.004, n=4, col=COL).data.materials.append(grotte.corda_material())
    # lo striscione degli auguri, teso fra due spuntoni della parete in fondo
    fondo = strisce_material('TAStriscione', (0.62, 0.60, 0.55), (0.62, 0.60, 0.55), passo=1.0)
    telo('Striscione', (4.4, 0.55), (0.0, 4.6, 2.9), rot=(math.radians(85), 0, 0), mat=fondo, onde=0.05, giu=0.06, seed=8)
    scritta('Auguri', 'TANTI AUGURI', 0.36, (0.0, 4.5, 2.92), (math.radians(85), 0, 0),
            grotte.plastica('TAScritta', (0.45, 0.06, 0.08), melma=0.2), extrude=0.008)
    trov = (c[0] - 0.55, c[1] - 0.55, 0.84)
    foglio('Trovato', disegno('archie'), (0.30, 0.22), trov, (math.radians(4), 0, math.radians(15)), curva=0.004)
    return {'trovato': trov, 'letto': tuple(c)}


def tana_lampy():
    """Una culla con la giostrina di pesciolini, una vaschetta da bagno, le cuffie a fiori appese."""
    rr = np.random.default_rng(16)
    c = np.array(CENTRO)
    bianco = grotte.plastica('TLBianco', (0.62, 0.60, 0.56), melma=0.45)
    # la culla: il fondo, le sbarre, le testate
    scatola('CullaFondo', (1.3, 0.75, 0.08), (c[0], c[1], 0.45), mat=bianco)
    for s in (-1, 1):
        scatola('Testata', (0.06, 0.8, 0.9), (c[0] + s * 0.66, c[1], 0.55), mat=bianco)
        for k in range(9):
            x = c[0] - 0.6 + k * 0.15
            cilindro('Sbarra', 0.015, 0.45, (x, c[1] + s * 0.38, 0.72), mat=bianco, verts=8)
    for s in (-1, 1):
        cilindro('Piede', 0.03, 0.45, (c[0] + s * 0.6, c[1] + 0.3, 0.22), mat=bianco, verts=8)
        cilindro('Piede', 0.03, 0.45, (c[0] + s * 0.6, c[1] - 0.3, 0.22), mat=bianco, verts=8)
    telo('Copertina', (1.2, 0.7), (c[0], c[1], 0.52), mat=grotte.plastica('TLCopertina', (0.55, 0.35, 0.45), melma=0.5), onde=0.03, seed=9)
    # la giostrina: appesa alla volta sopra la culla, i pesciolini di plastica in giro
    asta = (c[0], c[1], 1.75)
    tube('GiostrinaFilo', [(c[0], c[1], 3.4), asta], 0.006, n=5, col=COL).data.materials.append(grotte.corda_material())
    cols = [(0.7, 0.4, 0.05), (0.1, 0.4, 0.6), (0.65, 0.15, 0.3), (0.2, 0.5, 0.2), (0.75, 0.7, 0.2)]
    for k in range(5):
        a = 2 * math.pi * k / 5
        p = (asta[0] + 0.35 * math.cos(a), asta[1] + 0.35 * math.sin(a), asta[2] - 0.25)
        tube('GiostrinaFiletto', [asta, p], 0.003, n=4, col=COL).data.materials.append(grotte.corda_material())
        palla('Pesciolino', 0.08, p, mat=grotte.plastica('TLPesce%d' % k, cols[k], rough=0.25, melma=0.2), scale=(0.5, 1.4, 0.8))
    # la vaschetta da bagno, a sinistra
    o = lathe('Vaschetta', [(0.42, 0.0), (0.46, 0.25), (0.48, 0.30), (0.44, 0.30), (0.40, 0.05)], n=28, col=COL, close_bottom=True)
    o.location = (-2.4, 1.6, 0.0)
    o.scale = (1.4, 0.9, 1.0)
    o.data.materials.append(grotte.plastica('TLVasca', (0.15, 0.40, 0.55), melma=0.5))
    _lg(o)
    # le cuffie a fiori appese alla parete
    fiori = grotte._mat('LampyFioriMat', grotte._fiori)
    for k in range(5):
        p = (2.6 + k * 0.35, 3.6 - k * 0.3, 1.8 + 0.25 * math.sin(k * 1.3))
        palla('Cuffia', 0.13, p, mat=fiori, scale=(1.0, 1.1, 0.8))
    trov = (c[0] + 0.25, c[1] - 0.1, 0.58)
    foglio('Trovato', disegno('lampy'), (0.30, 0.22), trov, (0, 0, math.radians(-12)), curva=0.004)
    return {'trovato': trov, 'letto': tuple(c), 'soffitto': (c[0], c[1], 3.5)}


def tana_fangy():
    """Bende per gli occhi, occhialini dipinti di nero, il gioco del Marco Polo; attorno al letto conchiglie appese
    che tintinnano."""
    rr = np.random.default_rng(17)
    c = np.array(CENTRO)
    legn = legno('TFLegno', (0.18, 0.11, 0.06))
    scatola('Letto', (1.4, 2.4, 0.35), (c[0], c[1], 0.25), mat=legn)
    telo('Lenzuolo', (1.5, 2.5), (c[0], c[1], 0.45), mat=grotte.plastica('TFLenzuolo', (0.45, 0.48, 0.52), melma=0.55), onde=0.05, giu=0.15, seed=10)
    # le conchiglie appese tutt'attorno al letto
    conch = grotte.plastica('TFConchiglia', (0.70, 0.62, 0.52), rough=0.35, melma=0.25)
    for k in range(44):
        a = 2 * math.pi * k / 44
        x, y = c[0] + 1.3 * math.cos(a), c[1] + 1.7 * math.sin(a)
        top = 3.2 + 0.4 * rr.uniform()
        z = rr.uniform(1.0, 2.2)
        tube('Filo', [(x, y, top), (x, y, z + 0.06)], 0.003, n=4, col=COL).data.materials.append(grotte.corda_material())
        o = lathe('Conchiglia', [(0.0, 0.0), (0.05, 0.02), (0.06, 0.06), (0.02, 0.09)], n=10, col=COL)
        o.location = (x, y, z)
        o.rotation_euler = (rr.uniform(0, 3), rr.uniform(0, 3), 0)
        o.data.materials.append(conch)
        _lg(o)
    # le bende appese e buttate
    benda = grotte.plastica('TFBenda', (0.10, 0.10, 0.12), melma=0.3)
    for k in range(5):
        telo('Benda', (0.9, 0.08), (rr.uniform(-3, 3), rr.uniform(0, 4), 0.03), rot=(0, 0, rr.uniform(0, 3)), mat=benda, onde=0.02, seed=20 + k)
    # gli occhialini dipinti di nero, su uno sgabello
    nero = grotte.semplice('FangyLenti', (0.008, 0.008, 0.01), rough=0.12, coat=1.0)
    scatola('Sgabello', (0.4, 0.4, 0.5), (1.6, 1.0, 0.25), mat=legn)
    for s in (-1, 1):
        palla('Lente', 0.045, (1.6 + s * 0.06, 1.0, 0.53), mat=nero, scale=(1.0, 0.6, 0.8))
    # il Marco Polo: il cartello della piscina con le regole del gioco, e i tubi galleggianti
    scritta('MarcoPolo', 'MARCO? POLO!', 0.42, (-2.4, 3.3, 1.9), (math.radians(88), 0, 0.55),
            grotte.semplice('THGesso', (0.75, 0.74, 0.70), rough=0.9), extrude=0.004)
    for k in range(3):
        cilindro('Tubo', 0.07, 1.4, (-2.0 + k * 0.3, 1.0, 0.07), rot=(0, math.radians(90), rr.uniform(0, 3)),
                 mat=grotte.plastica('TFTubo%d' % k, [(0.6, 0.1, 0.4), (0.1, 0.5, 0.6), (0.7, 0.6, 0.1)][k], melma=0.3))
    trov = (-0.9, 0.3, 0.02)
    foglio('Trovato', disegno('fangy'), (0.42, 0.32), trov, (0, 0, math.radians(25)), curva=0.006)
    return {'trovato': trov, 'letto': tuple(c)}


ARREDI = {'gulpy': tana_gulpy, 'molly': tana_molly, 'hatch': tana_hatch, 'robin': tana_robin, 'archie': tana_archie,
          'lampy': tana_lampy, 'fangy': tana_fangy}


# ───────────────────────── i mostri addormentati ─────────────────────────

def M_tana(origin, yaw=0.0, roll=0.0, pitch=0.0, scale=1.0):
    """Da coordinate locali del mostro (faccia verso −Y, alto +Z) alla tana: traslazione, yaw (Z), rollio (Y, per
    sdraiarlo su un fianco), beccheggio (X), scala."""
    return (Matrix.Translation(tuple(map(float, origin))) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
            @ Matrix.Rotation(math.radians(roll), 4, 'Y') @ Matrix.Rotation(math.radians(pitch), 4, 'X')
            @ Matrix.Scale(scale, 4))


def _metti(obs, M):
    bpy.context.view_layer.update()
    for o in obs:
        o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    return obs


def _verso_occhio(o):
    """Lo yaw che volta la faccia (−y locale) verso l'occhio del sub."""
    return math.degrees(math.atan2(OCCHIO_T[0] - o[0], o[1] - OCCHIO_T[1]))


def _loc(M, p):
    v = M.inverted() @ Vector(tuple(map(float, p)))
    return np.array((v.x, v.y, v.z), F)


def dorme_gulpy(info, fiato=0.0):
    """Accasciato sulla pila di salvagenti, la schiena all'indietro e la mascella che pende aperta (sdraiato su un
    fianco non si leggeva: il corpo spariva dietro la pila)."""
    import gulpy
    o = (CENTRO[0] + 0.1, CENTRO[1] + 0.5, -0.35)
    M = M_tana(o, yaw=_verso_occhio(o) + 18.0, pitch=-16.0, scale=1.0 * (1.0 + 0.03 * fiato))
    obs = gulpy.build(viewer=_loc(M, (o[0], o[1] - 2.0, 0.0)), mascella=12.0 + 4.0 * fiato)
    return _metti(obs, M)


def dorme_molly(info, fiato=0.0):
    """Su un fianco sulla sabbia, abbracciata ai braccioli; l'occhio che scivola via resta socchiuso."""
    import molly as mo
    o = info['letto']
    M = M_tana((o[0], o[1], 0.62), yaw=_verso_occhio(o) + 15.0, roll=82.0, scale=1.4 * (1.0 + 0.02 * fiato))
    obs = mo.build(viewer=_loc(M, OCCHIO_T), palpebre=(1.0, 0.55))
    return _metti(obs, M)


def dorme_hatch(info, fiato=0.0):
    """Rannicchiato dentro l'armadio aperto, curvo, l'esca del giocattolo che si accende e si spegne piano."""
    import hatch
    o = (0.0, 3.3, 0.0)
    M = M_tana(o, yaw=_verso_occhio(o), pitch=18.0 + 2.0 * fiato, scale=0.95)
    obs = hatch.build(viewer=_loc(M, (0.0, 0.0, 0.0)), bocca=0.0)
    luci = [x for x in bpy.data.objects if x.type == 'LIGHT' and x.name.startswith('ToyLight')]
    for li in luci:
        li.data.energy = 4.0
    return _metti(obs + luci, M)


def dorme_robin(info, fiato=0.0):
    """Disteso sul mucchio come un granchio sul bottino, gli occhi chiusi."""
    import robin as ro
    o = (CENTRO[0], CENTRO[1] - 0.2, 0.25)
    M = M_tana(o, yaw=_verso_occhio(o) + 20.0, scale=1.25 * (1.0 + 0.02 * fiato))
    obs = ro.build(viewer=_loc(M, OCCHIO_T), fish=False, palpebre=1.0)
    return _metti(obs, M)


def dorme_archie(info, fiato=0.0):
    """Avvolto come un serpente attorno al tavolo della festa, la testa appoggiata sul tavolo; a ogni respiro la
    trombetta si srotola un poco."""
    import archie as ar
    c = np.array(info['letto'])
    o = (c[0], c[1], 0.0)
    M = M_tana(o, yaw=_verso_occhio(o) - 20.0, scale=1.0)
    orig_head, orig_collo = ar.HEAD, ar.collo_punti
    tav = _loc(M, (c[0], c[1], 0.0))
    ar.HEAD = np.array((tav[0] + 0.15, tav[1] - 0.55, 1.02), F)

    def collo_a_spirale(fr):
        A = fr.pt(ar.ATTACCO)
        tA, h = ar.collo_dir(fr)
        # le spire attorno alla gamba del tavolo, sulla sabbia, poi su fino alla testa sul bordo del tavolo
        pts = []
        for t in np.linspace(0.0, 1.0, 26):
            a = 2 * math.pi * 1.6 * t + 1.0
            r = 1.25 - 0.15 * t
            pts.append(np.array((tav[0] + r * math.cos(a), tav[1] + r * math.sin(a), 0.11 + 0.05 * t), F))
        base = A - tA * 0.35 - np.array((0, 0, 0.45), F)
        pts.append(base)
        return pts + [A - tA * 0.12, A, A + tA * 0.04]
    ar.collo_punti = collo_a_spirale
    try:
        obs = ar.build(lampara=tuple(_loc(M, (c[0] + 0.3, c[1] + 0.2, 0.8))), viewer=tuple(_loc(M, OCCHIO_T)),
                       srotolata=0.05 + 0.25 * fiato, fiato=fiato)
    finally:
        ar.HEAD, ar.collo_punti = orig_head, orig_collo
    return _metti(obs, M)


def dorme_lampy(info, fiato=0.0):
    """Attaccata con la ventosa al soffitto sopra la culla, a testa in giù; non ha palpebre e dorme a occhi aperti."""
    import lampy as la
    s = info.get('soffitto', (CENTRO[0], CENTRO[1], 3.5))
    M = M_tana((s[0], s[1], s[2] + 0.2), yaw=_verso_occhio(s) + 30.0, pitch=180.0, scale=1.2 * (1.0 + 0.02 * fiato))
    obs = la.build(viewer=tuple(_loc(M, (s[0], s[1], 0.5))), bocca=0.15 + 0.1 * fiato)
    return _metti(obs, M)


def dorme_fangy(info, fiato=0.0):
    """Raggomitolato sul letto, gli occhialini neri, le lucine del ventre quasi spente che respirano lentissime."""
    import fangy as fa
    c = info['letto']
    o = (c[0] + 0.1, c[1], 0.78)
    M = M_tana(o, yaw=_verso_occhio(o) - 70.0, roll=80.0, scale=1.25 * (1.0 + 0.02 * fiato))
    obs = fa.build(viewer=tuple(_loc(M, OCCHIO_T)), testa=-15.0, luci=0.12 + 0.1 * fiato)
    # gli anelli sull'acqua della posa in mare non servono
    via = [x for x in bpy.data.objects if x.name.startswith('FangyRipples')]
    nomi = {x.name for x in via}
    obs = [x for x in obs if x.name not in nomi]
    for x in via:
        bpy.data.objects.remove(x)
    return _metti(obs, M)


DORME = {'gulpy': dorme_gulpy, 'molly': dorme_molly, 'hatch': dorme_hatch, 'robin': dorme_robin, 'archie': dorme_archie,
         'lampy': dorme_lampy, 'fangy': dorme_fangy}


def build_tana(chi, res=0.07, vita=True):
    """La cameretta di chi, senza il mostro. Restituisce info (la cosa da trovare, il letto, ...)."""
    build_luci()
    ob, v, n, sab = build_stanza(float(os.environ.get('GROTTE_RES', res)))
    if vita:
        build_vita(v, n, sab, seed=ORDINE.index(chi) + 3)
    return ARREDI[chi]()


def mostro(chi, info, fiato=0.0):
    """Il mostro addormentato nella sua tana (gli oggetti nuovi della scena)."""
    prima = set(bpy.data.objects.keys())
    DORME[chi](info, fiato=fiato)
    return [o for o in bpy.data.objects if o.name not in prima]
