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

# l'inquadratura fissa di ogni tana (latitudine bassa e alta del panorama parziale, lo sguardo al centro): di solito
# da −55° a +25° guardando a −15°; Lampy dorme attaccata al soffitto, e lì si guarda più in alto
INQUADRATURA = {'lampy': (-45.0, 35.0, -5.0)}


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
    import disegni_tane
    if nome in disegni_tane.DISEGNI:
        # i disegni dei bambini: a pastelli, con la mano di «Il ricordo» (disegni_tane.py)
        p = os.path.join(CACHE, 'tane', f'pastello_{nome}.png')
        return p if os.path.exists(p) else disegni_tane.DISEGNI[nome]()
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


# ───────────────────────── arredi veri (12 ottobre: niente scatole) ─────────────────────────

def legno_gonfio(name, color=(0.22, 0.13, 0.07)):
    """Legno rimasto anni sott'acqua: le assi (bande lungo x dell'oggetto) scurite e gonfie, la melma nelle commessure,
    le venature in rilievo."""
    def b(n):
        m, g = material(n)
        co = g.texcoord('Object')
        x, y, z = g.sep(co)
        venatura = g.noise(g.mapping(co, scale=(1.0, 1.0, 14.0)), scale=4.0, detail=6.0, distortion=1.5).fac
        assi = g.smoothstep(0.0, 0.02, g.math('PINGPONG', g.add(x, g.mul(venatura, 0.02)), 0.09))
        col = g.mix(g.mul(venatura, 0.5), color, g.mix(0.5, color, (0.06, 0.035, 0.02)))
        col = g.mix(g.sub(1.0, assi), col, (0.03, 0.04, 0.02))
        sl = g.smoothstep(0.5, 0.75, g.noise(co, scale=3.0, detail=8.0, rough=0.7, distortion=0.8).fac)
        col = g.mix(g.mul(sl, 0.7), col, (0.04, 0.05, 0.025))
        h = g.add(g.mul(venatura, 0.3), assi)
        g.output_material(g.principled(color=col, rough=0.7, normal=g.bump(h, strength=0.35, distance=0.01)))
        return m
    return grotte._mat(name, b)


def imbarca(o, gradi=5.0, asse='Z'):
    """Il legno gonfio non è più dritto: una curvatura leggera (modificatore Simple Deform)."""
    md = o.modifiers.new('Imbarcato', 'SIMPLE_DEFORM')
    md.deform_method = 'BEND'
    md.angle = math.radians(gradi)
    md.deform_axis = asse
    return o


def ruota_su(o, centro, ang):
    """Sposta e ruota attorno a Z un oggetto costruito attorno all'origine."""
    o.matrix_world = Matrix.Translation(Vector(centro)) @ Matrix.Rotation(ang, 4, 'Z') @ o.matrix_world
    return o


def armadio(name, pos, ang, w=1.3, d=0.62, h=2.2, ante=(105.0, 70.0), mat=None, buio=True):
    """Un armadio a due ante: la cassa (fondo, fianchi, cielo con la cornice, zoccolo), le ante a riquadri sui cardini,
    i pomelli; il legno gonfio e imbarcato. Il davanti guarda −y (prima della rotazione ang)."""
    mat = mat or legno_gonfio('TLegnoArmadio')
    obs = []
    t = 0.04
    obs.append(scatola(name + 'Fondo', (w, t, h), (0, d / 2 - t / 2, h / 2), mat=mat))
    for sx in (-1, 1):
        obs.append(imbarca(scatola(name + 'Fianco', (t, d, h), (sx * (w / 2 - t / 2), 0, h / 2), mat=mat), 4.0 * sx, 'Y'))
    obs.append(scatola(name + 'Cielo', (w + 0.1, d + 0.08, 0.08), (0, 0, h + 0.02), mat=mat))
    obs.append(scatola(name + 'Cornice', (w + 0.16, d + 0.12, 0.05), (0, -0.02, h + 0.08), mat=mat))
    obs.append(scatola(name + 'Zoccolo', (w, d, 0.12), (0, 0, 0.06), mat=mat))
    obs.append(scatola(name + 'Ripiano', (w - 2 * t, d - t, 0.03), (0, 0, h * 0.72), mat=mat))
    if buio:
        obs.append(scatola(name + 'Dentro', (w - 2 * t, 0.01, h - 0.2), (0, d / 2 - t - 0.01, h / 2), mat=grotte.semplice('THBuio', (0.01, 0.01, 0.01), rough=0.9)))
    pomo = grotte.semplice('TOttone', (0.35, 0.25, 0.10), rough=0.4, metal=1.0)
    for sx, a in ((-1, ante[0]), (1, ante[1])):
        wd = w / 2 - 0.01
        hinge = Vector((sx * w / 2, -d / 2, 0))
        R = Matrix.Rotation(math.radians(-sx * a), 4, 'Z')
        anta = []
        anta.append(scatola(name + 'Anta', (wd, 0.035, h - 0.16), (-sx * wd / 2, 0, h / 2), mat=mat))
        for zz in (0.32, 0.68):                                     # i riquadri in rilievo
            anta.append(scatola(name + 'Riquadro', (wd - 0.18, 0.02, h * 0.28), (-sx * wd / 2, -0.025, h * zz), mat=mat))
        anta.append(palla(name + 'Pomo', 0.025, (-sx * (wd - 0.07), -0.05, h * 0.5), mat=pomo))
        for o in anta:
            imbarca(o, 6.0 * sx, 'Z') if o.name.startswith(name + 'Anta') else None
            o.matrix_world = Matrix.Translation(hinge) @ R @ o.matrix_world
        obs += anta
    for o in obs:
        ruota_su(o, pos, ang)
    return obs


def sgabello(name, pos, mat=None, h=0.5):
    mat = mat or legno_gonfio('TLegnoSgabello')
    obs = [cilindro(name + 'Seduta', 0.2, 0.045, (0, 0, h), mat=mat, verts=28)]
    for k in range(3):
        a = 2 * math.pi * k / 3
        top = (0.13 * math.cos(a), 0.13 * math.sin(a), h - 0.02)
        bot = (0.21 * math.cos(a), 0.21 * math.sin(a), 0.0)
        o = tube(name + 'Gamba', [bot, top], 0.022, n=8, col=COL)
        o.data.materials.append(mat)
        obs.append(_lg(o))
    pts = [(0.17 * math.cos(a), 0.17 * math.sin(a), h * 0.35) for a in np.linspace(0, 2 * math.pi, 25)]
    o = tube(name + 'Anello', pts, 0.012, n=6, col=COL)
    o.data.materials.append(mat)
    obs.append(_lg(o))
    for o in obs:
        ruota_su(o, pos, 0.0)
    return obs


def letto(name, pos, ang, w=1.25, L=2.1, lenzuolo=None, cuscino=None, seed=10):
    """Un lettino di legno: le sponde, la testiera a colonnine, la pediera, i piedi; il materasso morbido, il lenzuolo
    che cade ai lati, il cuscino. Il letto è lungo y (la testiera verso +y)."""
    mat = legno_gonfio('TLegnoLetto', (0.25, 0.15, 0.08))
    obs = []
    for sx in (-1, 1):
        obs.append(scatola(name + 'Sponda', (0.06, L, 0.18), (sx * w / 2, 0, 0.35), mat=mat))
        for sy in (-1, 1):
            obs.append(cilindro(name + 'Piede', 0.04, 0.5 if sy < 0 else 1.0, (sx * w / 2, sy * L / 2, (0.25 if sy < 0 else 0.5)), mat=mat, verts=12))
    obs.append(scatola(name + 'Testiera', (w, 0.06, 0.12), (0, L / 2, 0.98), mat=mat))
    obs.append(scatola(name + 'Testiera2', (w, 0.06, 0.12), (0, L / 2, 0.55), mat=mat))
    for k in range(7):
        x = -w / 2 + 0.15 + k * (w - 0.3) / 6
        obs.append(cilindro(name + 'Colonnina', 0.02, 0.43, (x, L / 2, 0.765), mat=mat, verts=10))
    obs.append(scatola(name + 'Pediera', (w, 0.06, 0.3), (0, -L / 2, 0.42), mat=mat))
    mat_m = grotte.plastica('TMaterasso', (0.42, 0.40, 0.33), rough=0.85, melma=0.6)
    obs.append(scatola(name + 'Materasso', (w - 0.08, L - 0.1, 0.2), (0, 0, 0.5), mat=mat_m, bevel=0.07))
    obs.append(telo(name + 'Lenzuolo', (w + 0.3, L - 0.2), (0, -0.05, 0.61), mat=lenzuolo or grotte.plastica('TLenzuolo', (0.45, 0.48, 0.52), melma=0.55),
                    onde=0.025, giu=0.32, seed=seed))
    obs.append(palla(name + 'Cuscino', 0.3, (0, L / 2 - 0.35, 0.66), mat=cuscino or grotte.plastica('TCuscino', (0.55, 0.55, 0.50), melma=0.5), scale=(1.4, 0.7, 0.35)))
    for o in obs:
        ruota_su(o, pos, ang)
    return obs


def trampolino(pos, ang):
    """Il trampolino vero della piscina: la tavola in vetroresina che si assottiglia e si piega appena, il supporto
    col fulcro, il basamento, la scaletta coi corrimano curvi. Lungo y, la punta verso −y."""
    bianco = grotte.plastica('TMBianco', (0.62, 0.62, 0.58), melma=0.45)
    blu = grotte.plastica('TMBlu', (0.06, 0.20, 0.45), rough=0.6, melma=0.4)
    cromo = grotte.semplice('TMCromo', (0.6, 0.6, 0.6), rough=0.25, metal=1.0)
    obs = []
    tav = scatola('Tavola', (0.55, 3.4, 0.06), (0, -0.7, 1.55), mat=blu, bevel=0.025)
    obs.append(imbarca(tav, -4.0, 'X'))
    obs.append(scatola('Basamento', (0.8, 1.0, 0.25), (0, 0.9, 0.12), mat=bianco, bevel=0.03))
    obs.append(scatola('Pilastro', (0.5, 0.6, 1.25), (0, 0.9, 0.85), mat=bianco, bevel=0.03))
    for sx in (-1, 1):
        o = tube('Fulcro', catmull([(sx * 0.3, 0.2, 0.1), (sx * 0.3, -0.05, 0.9), (sx * 0.28, -0.25, 1.5)], 6), 0.035, n=10, col=COL)
        o.data.materials.append(cromo)
        obs.append(_lg(o))
        o = tube('Corrimano', catmull([(sx * 0.35, 1.85, 0.0), (sx * 0.35, 1.7, 1.2), (sx * 0.35, 1.35, 1.75), (sx * 0.33, 1.1, 1.85)], 6), 0.025, n=10, col=COL)
        o.data.materials.append(cromo)
        obs.append(_lg(o))
    for k in range(5):
        z = 0.3 + k * 0.3
        obs.append(scatola('Gradino', (0.6, 0.12, 0.03), (0, 1.8 - k * 0.05, z), mat=cromo, bevel=0.005))
    for o in obs:
        ruota_su(o, pos, ang)
    return obs


def parete(yaw_deg, z, da=(0.0, 1.1)):
    """Dove la roccia della stanza incontra la direzione yaw (0 = in fondo, verso +y; 90 = a destra) alla quota z:
    il punto sulla parete e la normale verso l'acqua."""
    a = math.radians(yaw_deg)
    d = np.array((math.sin(a), math.cos(a), 0.0))
    p0 = np.array((da[0], da[1], z))
    t = np.linspace(0.5, 9.0, 200)
    P = (p0[None] + t[:, None] * d[None]).astype(F)
    k = int(np.argmax(stanza(P) > 0))
    p = P[max(k - 1, 0)]
    e = 0.05
    gr = np.array([(stanza((p + dd)[None].astype(F))[0] - stanza((p - dd)[None].astype(F))[0]) for dd in np.eye(3) * e])
    n = -gr / (np.linalg.norm(gr) + 1e-9)
    n[2] *= 0.3                         # i pannelli restano quasi verticali
    n /= np.linalg.norm(n)
    return p, n


def su_parete(o, yaw_deg, z, stacco=0.06, inclina=0.0):
    """Appoggia un pannello (costruito nel piano XY, con la faccia verso +Z) alla parete in direzione yaw, alla quota z."""
    p, n = parete(yaw_deg, z)
    q = Vector(tuple(n)).to_track_quat('Z', 'Y')
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = q @ __import__('mathutils').Quaternion((0, 0, 1), inclina)
    o.location = tuple(p + n * stacco)
    return o


def pannello(name, size, mat, seed=0, onde=0.01):
    """Un pannello sottile nel piano XY (piastrelle, carta da parati, manifesti), con le UV."""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=20, y_subdivisions=20, size=1.0, calc_uvs=True)
    o = bpy.context.object
    for c in list(o.users_collection):
        c.objects.unlink(o)
    collection(COL).objects.link(o)
    o.name = name
    rr = np.random.default_rng(seed)
    ph = rr.uniform(0, 6.28, 2)
    for vtx in o.data.vertices:
        x, y = vtx.co.x * size[0], vtx.co.y * size[1]
        vtx.co = Vector((x, y, onde * math.sin(x * 2.0 + ph[0]) * math.sin(y * 1.7 + ph[1])))
    o.data.materials.append(mat)
    return _lg(o)


def piastrelle_material(name='TMPiastrelle'):
    """Le piastrelle della piscina: quadrotte bianche e azzurre, le fughe annerite, qualche piastrella caduta (lì si
    vede la roccia scura), la melma a chiazze."""
    def b(n):
        m, g = material(n)
        co = g.texcoord('Object')
        q = g.vmath('SCALE', co, scale=1.0 / 0.15)
        f = g.vmath('FRACTION', q)
        fx, fy, _ = g.sep(f)
        bordo = g.mn(g.mn(fx, g.sub(1.0, fx)), g.mn(fy, g.sub(1.0, fy)))
        fuga = g.smoothstep(0.06, 0.03, bordo)
        cella = g.vmath('FLOOR', q)
        rnd = g.noise(g.vmath('SCALE', cella, scale=0.731), scale=3.7, detail=0.0).fac
        azzurra = g.smoothstep(0.62, 0.66, rnd)
        caduta = g.smoothstep(0.30, 0.27, rnd)
        col = g.mix(azzurra, (0.55, 0.58, 0.56), (0.10, 0.32, 0.45))
        col = g.mix(fuga, col, (0.05, 0.05, 0.04))
        col = g.mix(caduta, col, (0.02, 0.025, 0.02))
        sl = g.smoothstep(0.55, 0.8, g.noise(co, scale=1.5, detail=8.0, rough=0.7, distortion=0.8).fac)
        col = g.mix(g.mul(sl, 0.75), col, (0.035, 0.05, 0.025))
        rough = g.mixf(g.add(fuga, caduta), 0.15, 0.85)
        g.output_material(g.principled(color=col, rough=rough, coat=0.3, normal=g.bump(g.add(fuga, caduta), strength=0.4, distance=0.004, invert=True)))
        return m
    return grotte._mat(name, b)


def carta_da_parati_material(name='TLCarta'):
    """La carta da parati a fiori, strappata: dove manca (i bordi frastagliati dal rumore) si vede la roccia."""
    def b(n):
        m, g = material(n)
        co = g.texcoord('Object')
        uv = g.texcoord('UV')
        ux, uy, _ = g.sep(uv)
        fiori = g.voronoi(g.vmath('SCALE', co, scale=7.0), scale=1.0, feature='F1')
        petali = g.smoothstep(0.32, 0.22, fiori)
        centro = g.smoothstep(0.12, 0.08, fiori)
        righe = g.smoothstep(0.45, 0.5, g.math('PINGPONG', g.sep(co)[0], 0.25))
        col = g.mix(g.mul(righe, 0.3), (0.55, 0.50, 0.40), (0.45, 0.42, 0.34))
        col = g.mix(petali, col, (0.55, 0.20, 0.30))
        col = g.mix(centro, col, (0.60, 0.50, 0.15))
        sl = g.smoothstep(0.5, 0.8, g.noise(co, scale=2.0, detail=8.0, rough=0.7, distortion=0.8).fac)
        col = g.mix(g.mul(sl, 0.8), col, (0.05, 0.06, 0.03))
        # lo strappo: tiene la carta dentro un bordo frastagliato
        bordo = g.mn(g.mn(ux, g.sub(1.0, ux)), g.mn(uy, g.sub(1.0, uy)))
        frast = g.noise(co, scale=2.5, detail=6.0, rough=0.7).fac
        tieni = g.smoothstep(0.02, 0.05, g.sub(g.add(bordo, g.mul(frast, 0.35)), 0.18))
        surf = g.principled(color=col, rough=0.75, sss=0.1, sss_radius=(1.0, 0.5, 0.3), sss_scale=0.01)
        g.output_material(g.mix_shader(tieni, g.transparent(), surf))
        return m
    return grotte._mat(name, b)


def lucine(name, a, b, n=26, sag=0.5, colori=((1.0, 0.75, 0.35), (1.0, 0.35, 0.3), (0.4, 0.8, 1.0), (0.5, 1.0, 0.5)), spente=0.35, seed=3):
    """Una fila di lucine della festa tesa fra due punti: il filo, le lampadine colorate (alcune spente)."""
    rr = np.random.default_rng(seed)
    a, b = np.array(a), np.array(b)
    pts = [a + (b - a) * t - np.array((0, 0, sag * 4 * t * (1 - t))) for t in np.linspace(0, 1, 40)]
    o = tube(name + 'Filo', pts, 0.006, n=5, col=COL)
    o.data.materials.append(grotte.corda_material())
    _lg(o)
    for k in range(n):
        t = (k + 0.5) / n
        p = a + (b - a) * t - np.array((0, 0, sag * 4 * t * (1 - t) + 0.06))
        c = colori[k % len(colori)]
        if rr.random() < spente:
            mat = grotte.semplice(f'TLucinaSpenta{k % len(colori)}', tuple(x * 0.25 for x in c), rough=0.2)
        else:
            mat = grotte.semplice(f'TLucina{k % len(colori)}', tuple(x * 0.4 for x in c), rough=0.2, emission=c, strength=3.0)
        palla(name + 'Lampadina', 0.035, tuple(p), mat=mat, scale=(1.0, 1.0, 1.4))


def manifesto(nome, testo_righe, colori, w=600, h=840):
    """Un manifesto o un cartello stampato (PIL): sfondo, righe di testo grandi; l'immagine in cache."""
    from PIL import Image, ImageDraw, ImageFont
    path = os.path.join(CACHE, 'tane', f'manifesto_{nome}.png')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = Image.new('RGB', (w, h), colori[0])
    dr = ImageDraw.Draw(im)
    fonts = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
    y = 40
    for testo, size, col, font in testo_righe:
        f = ImageFont.truetype(os.path.join(fonts, font + '.ttf'), size)
        tw = dr.textlength(testo, font=f)
        dr.text(((w - tw) / 2, y), testo, fill=col, font=f)
        y += size * 1.3
    dr.rectangle((0, 0, w - 1, h - 1), outline=colori[1], width=14)
    im.save(path)
    return path


def manifesto_su_parete(nome, righe, colori, yaw, z, size=(0.6, 0.84), inclina=0.0):
    path = manifesto(nome, righe, colori)
    o = pannello('Manifesto' + nome, size, immagine_material('TManifesto' + nome, path))
    return su_parete(o, yaw, z, stacco=0.05, inclina=inclina)


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
    # i manifesti dello Snack Shack sulle pareti (estate 1997)
    manifesto_su_parete('hotdog', [('HOT DOG', 100, (200, 40, 30), 'Limelight-Regular'), ('L. 3.000', 80, (30, 30, 30), 'Monoton-Regular'),
                                   ('SNACK SHACK', 50, (30, 60, 150), 'Limelight-Regular')], ((240, 220, 120), (200, 40, 30)), 35, 1.8)
    manifesto_su_parete('gelati', [('GELATI', 100, (30, 90, 160), 'Limelight-Regular'), ('ESTATE 1997', 60, (200, 40, 30), 'Limelight-Regular')],
                        ((235, 235, 225), (30, 90, 160)), 70, 1.5, inclina=0.15)
    manifesto_su_parete('patatine', [('PATATINE', 90, (200, 120, 20), 'Limelight-Regular'), ('MAXI', 120, (200, 40, 30), 'Monoton-Regular')],
                        ((250, 240, 200), (200, 120, 20)), -75, 1.7, inclina=-0.1)
    # la cosa da trovare: il disegno a pastelli, appeso al bancone
    trov = (-2.3, 2.05, 0.75)
    foglio('Trovato', disegno('gulpy'), (0.42, 0.32), trov, (math.radians(85), 0, 0.35))
    return {'trovato': trov, 'letto': CENTRO}


def sdf_ring(name, c, tilt, spin, mat, R=0.32, r=0.12):
    """Un salvagente a paperella (più semplice di quello di Gulpy): l'anello e la testa."""
    ring = sdf.torus((0, 0, 0), R, r, axis='z')
    head = sdf.union(sdf.capsule((0, -R, r * 0.5), (0, -R, r + 0.12), 0.09), sdf.sphere((0, -R - 0.02, r + 0.2), 0.12), k=0.06)
    lo, hi = -R - r - 0.15, R + r + 0.25
    v, f, _ = sdf.mesh(sdf.union(ring, head, k=0.03), (lo, lo, -r - 0.05), (hi, hi, r + 0.45), res=0.02)
    ob = grotte.mesh_obj(name, v, f)
    ob.data.materials.append(mat)
    ob.location = c
    ob.rotation_euler = (tilt, 0, spin)
    return ob


def tana_molly():
    """Il trampolino della piscina dentro la stanza, le piastrelle della piscina sulle pareti, gli specchi ossidati, le
    medaglie di nuoto, la corsia galleggiante, gli elastici rosa (1997)."""
    rr = np.random.default_rng(12)
    trampolino((1.9, 1.1, 0.0), math.radians(-8))
    # le piastrelle della piscina: pannelli strappati via dalla Deep End e appoggiati alle pareti, e una fascia bassa
    tile = piastrelle_material()
    for k, (yaw, z, sz) in enumerate(((-70, 1.3, (2.2, 1.8)), (-35, 1.6, (2.6, 2.0)), (5, 1.5, (2.4, 2.2)), (40, 1.4, (2.0, 1.7)),
                                       (75, 1.2, (1.8, 1.6)), (-100, 0.9, (1.6, 1.2)), (100, 0.9, (1.6, 1.2)))):
        su_parete(pannello('Piastrelle', sz, tile, seed=k, onde=0.03), yaw, z, stacco=0.08, inclina=rr.normal(0, 0.05))
    manifesto_su_parete('profondita', [('2,5 m', 150, (20, 30, 40), 'Monoton-Regular'), ('DEEP END', 70, (120, 20, 20), 'Limelight-Regular')],
                        ((205, 210, 205), (20, 60, 120)), -12, 2.55, size=(0.7, 0.5))
    # gli specchi ossidati, con la cornice
    specchio = grotte.semplice('TMSpecchio', (0.30, 0.34, 0.33), rough=0.12, metal=1.0)
    cornice = legno_gonfio('TMCornice', (0.30, 0.22, 0.10))
    for k, (yaw, z) in enumerate(((-55, 1.2), (25, 1.3), (60, 1.0))):
        c = su_parete(pannello('Cornice', (0.95, 1.45), cornice, seed=20 + k), yaw, z, stacco=0.14, inclina=rr.normal(0, 0.06))
        sp = su_parete(pannello('Specchio', (0.8, 1.3), specchio, seed=30 + k, onde=0.0), yaw, z, stacco=0.17, inclina=rr.normal(0, 0.06))
    # le medaglie appese a una cordicella
    oro = grotte.semplice('TMOro', (0.8, 0.6, 0.2), rough=0.3, metal=1.0)
    nastro = grotte.plastica('TMNastro', (0.10, 0.20, 0.60), melma=0.2)
    pa, _ = parete(-25, 2.6)
    pb, _ = parete(20, 2.6)
    pts = [pa + (pb - pa) * t - np.array((0, 0, 0.35 * 4 * t * (1 - t))) for t in np.linspace(0, 1, 30)]
    tube('Cordicella', pts, 0.008, n=6, col=COL).data.materials.append(grotte.corda_material())
    for k in range(8):
        t = (k + 1) / 9
        p = pa + (pb - pa) * t - np.array((0, 0, 0.35 * 4 * t * (1 - t)))
        cilindro('Medaglia', 0.11, 0.015, (p[0], p[1], p[2] - 0.45), rot=(math.radians(90), 0, 0), mat=oro)
        scatola('Nastro', (0.05, 0.01, 0.35), (p[0], p[1], p[2] - 0.2), mat=nastro, bevel=0.0)
    # la corsia galleggiante della piscina, tirata da una parete all'altra
    galleggianti = [grotte.plastica('TMCorsia%d' % k, c, rough=0.3, melma=0.3) for k, c in enumerate(((0.55, 0.05, 0.05), (0.62, 0.60, 0.55), (0.05, 0.20, 0.55)))]
    qa, _ = parete(-80, 2.9)
    qb, _ = parete(70, 3.1)
    for k in range(40):
        t = k / 39
        p = qa + (qb - qa) * t - np.array((0, 0, 0.6 * 4 * t * (1 - t)))
        cilindro('Galleggiante', 0.09, 0.2, tuple(p), rot=(0, math.radians(90), math.atan2(qb[1] - qa[1], qb[0] - qa[0])),
                 mat=galleggianti[(k // 3) % 3], verts=12)
    arancio = grotte.plastica('TMBraccioli', (0.70, 0.30, 0.04), rough=0.3, melma=0.35)
    for k in range(6):
        palla('Bracciolo', 0.1, (rr.uniform(-3, 3), rr.uniform(0, 3.5), 0.08), mat=arancio, scale=(1.6, 1.0, 0.8))
    rosa = grotte.plastica('MollyElastico', (0.60, 0.07, 0.26), rough=0.4, melma=0.2)
    for k in range(14):
        palla('Elastico', 0.03, (rr.uniform(-2.5, 2.5), rr.uniform(0.5, 3.5), 0.02), mat=rosa, scale=(1.0, 1.0, 0.35))
    # la foto sul trampolino
    trov = (1.85, 0.2, 1.62)
    foglio('Trovato', disegno('molly'), (0.30, 0.24), trov, (0, 0, math.radians(8)), curva=0.005)
    return {'trovato': trov, 'letto': (-0.6, 2.0, 0.0)}


def tana_hatch():
    """Piena di nascondigli: tre armadi spalancati (in quello in fondo si è rannicchiato lui), una capanna di
    asciugamani tra due sedie, i numeri della conta col gesso sulle pareti (1997)."""
    rr = np.random.default_rng(13)
    legn = legno_gonfio('THLegno', (0.22, 0.13, 0.07))
    armadio('ArmadioS', (-3.0, 2.4, 0.0), math.radians(40), ante=(110, 80), mat=legn)
    armadio('ArmadioC', (0.0, 3.5, 0.0), 0.0, w=1.5, h=2.3, ante=(115, 105), mat=legn)
    armadio('ArmadioD', (3.1, 2.2, 0.0), math.radians(-40), ante=(60, 120), mat=legn)
    # la capanna di asciugamani: un manico di scopa fra due sedie, due teli a spiovente
    tel = strisce_material('THAsciugamani', (0.55, 0.15, 0.10), (0.15, 0.35, 0.55), passo=0.3, asse=1)
    c, a = np.array((2.5, 0.9)), math.radians(70)        # il bastone punta lontano: dal sub si vede l'apertura
    ux, uy = math.cos(a), math.sin(a)
    for sgn in (-1, 1):
        sedia(f'Sedia{sgn}', (c[0] + sgn * 1.0 * ux, c[1] + sgn * 1.0 * uy, 0.0), a + (math.pi / 2 if sgn > 0 else -math.pi / 2), legn)
    o = tube('Bastone', [(c[0] - 1.25 * ux, c[1] - 1.25 * uy, 0.95), (c[0] + 1.25 * ux, c[1] + 1.25 * uy, 0.95)], 0.025, n=8, col=COL)
    o.data.materials.append(legn)
    _lg(o)
    for sgn in (-1, 1):
        telo('Asciugamano', (2.5, 1.2), (c[0] - sgn * 0.45 * uy, c[1] + sgn * 0.45 * ux, 0.5),
             rot=(sgn * math.radians(-58), 0, a), mat=tel, onde=0.04, seed=4 + sgn)
    # i numeri della conta col gesso sulle pareti, da 1 a 10 tutt'attorno, e il «10» enorme sopra l'armadio in fondo
    gesso = grotte.semplice('THGesso', (0.75, 0.74, 0.70), rough=0.9)
    for k in range(10):
        yaw = -110 + k * 24
        p, n = parete(yaw, 1.9 + 0.35 * math.sin(k * 1.7))
        t = scritta('Numero', str(k + 1), 0.55, (0, 0, 0), (0, 0, 0), gesso, extrude=0.004, font='Monoton-Regular')
        t.rotation_mode = 'QUATERNION'
        t.rotation_quaternion = Vector(tuple(n)).to_track_quat('Z', 'Y')
        t.location = tuple(p + n * 0.06)
    # le tacche della conta, tante, sulla parete di sinistra
    for k in range(18):
        p, n = parete(-140 + k * 1.6, 1.2 + 0.15 * (k % 3))
        o = tube('Tacca', [p + n * 0.05, p + n * 0.05 + np.array((0, 0, 0.35))], 0.012, n=4, col=COL)
        o.data.materials.append(gesso)
        _lg(o)
    trov = (-2.3, 1.6, 0.9)
    foglio('Trovato', disegno('hatch'), (0.42, 0.30), trov, (math.radians(70), 0, 0.6))
    return {'trovato': trov, 'letto': (0.0, 3.2, 0.0), 'armadio': (0.0, 3.5, 0.0)}


def sedia(name, pos, ang, mat):
    """Una sedia di legno semplice: seduta, quattro gambe, lo schienale a stecche."""
    obs = [scatola(name + 'Seduta', (0.45, 0.45, 0.04), (0, 0, 0.46), mat=mat)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(cilindro(name + 'Gamba', 0.022, 0.46 if sy < 0 else 0.95, (sx * 0.19, sy * 0.19, 0.23 if sy < 0 else 0.475), mat=mat, verts=8))
    for k in range(3):
        obs.append(scatola(name + 'Stecca', (0.38, 0.025, 0.06), (0, 0.19, 0.62 + k * 0.12), mat=mat))
    for o in obs:
        ruota_su(o, pos, ang)
    return obs


def tana_robin():
    """Un mucchio di cose rubate agli altri bambini (scarpe, giocattoli, oggetti smarriti) avvolto nei biglietti; un
    cabinato della sala giochi rovesciato, il cartello degli oggetti smarriti."""
    rr = np.random.default_rng(14)
    colori = [(0.6, 0.08, 0.06), (0.08, 0.25, 0.6), (0.75, 0.6, 0.1), (0.15, 0.45, 0.2), (0.6, 0.3, 0.55), (0.75, 0.72, 0.65)]
    mats = [grotte.plastica('TRCosa%d' % k, c, rough=0.4, melma=0.35) for k, c in enumerate(colori)]
    for k in range(320):
        a = rr.uniform(0, 6.28)
        r = 1.7 * math.sqrt(rr.uniform(0, 1))
        h = 0.9 * (1 - (r / 1.8) ** 2) + rr.uniform(0, 0.1)
        c = (CENTRO[0] + r * math.cos(a), CENTRO[1] + r * math.sin(a) * 0.8, h * rr.uniform(0.3, 1.0))
        kind = k % 5
        m = mats[rr.integers(0, len(mats))]
        rot = tuple(rr.uniform(0, 6.28, 3))
        if kind == 0:
            scarpa('Scarpa', c, rot, m)
        elif kind == 1:
            palla('Pallina', rr.uniform(0.05, 0.12), c, mat=m)
        elif kind == 2:
            o = lathe('Secchiello', [(0.07, 0.0), (0.09, 0.14), (0.085, 0.14), (0.065, 0.01)], n=14, col=COL, close_bottom=True)
            o.location, o.rotation_euler = c, rot
            o.data.materials.append(m)
            _lg(o)
        elif kind == 3:
            o = lathe('Paletta', [(0.03, 0.0), (0.03, 0.25), (0.08, 0.3), (0.0, 0.42)], n=8, col=COL)
            o.location, o.rotation_euler = c, rot
            o.data.materials.append(m)
            _lg(o)
        else:
            o = sdf_anello('Braccialetto', rr.uniform(0.04, 0.07), m)
            o.location, o.rotation_euler = c, rot
    for k in range(7):
        a = rr.uniform(0, 6.28)
        pts = [(CENTRO[0] + (0.2 + 1.5 * t) * math.cos(a + t * 2), CENTRO[1] + (0.2 + 1.5 * t) * math.sin(a + t * 2) * 0.8,
                0.95 * (1 - t) ** 1.5 + 0.03) for t in np.linspace(0, 1, 30)]
        ob = sweep('Biglietti', pts, rect_profile(0.065, 0.002), col=COL, cap=False, up=(0, 0, 1))
        ob.data.materials.append(grotte.plastica('TRBiglietti', (0.80, 0.24, 0.02), melma=0.3))
        _lg(ob)
    # il cabinato della sala giochi (il distributore dei biglietti), rovesciato contro la parete di destra
    cab = grotte.plastica('TRCabinato', (0.10, 0.08, 0.25), rough=0.4, melma=0.4)
    obs = [scatola('Cabinato', (0.7, 0.65, 1.7), (0, 0, 0.85), mat=cab, bevel=0.03),
           scatola('Schermo', (0.55, 0.02, 0.45), (0, -0.33, 1.25), mat=grotte.semplice('TRSchermo', (0.02, 0.05, 0.04), rough=0.1, emission=(0.05, 0.25, 0.15), strength=0.6)),
           scatola('Fessura', (0.25, 0.02, 0.04), (0, -0.33, 0.7), mat=grotte.semplice('THBuio', (0.01, 0.01, 0.01), rough=0.9))]
    obs.append(scritta('Marquee', 'TICKETS', 0.16, (0, -0.34, 1.6), (math.radians(90), 0, 0), grotte.plastica('TRMarquee', (0.85, 0.55, 0.05), melma=0.2), extrude=0.01))
    M = Matrix.Translation((3.0, 1.6, 0.35)) @ Matrix.Rotation(math.radians(-55), 4, 'Z') @ Matrix.Rotation(math.radians(70), 4, 'Y')
    for o in obs:
        o.matrix_world = M @ o.matrix_world
    manifesto_su_parete('smarriti', [('OGGETTI', 80, (30, 30, 30), 'Limelight-Regular'), ('SMARRITI', 80, (30, 30, 30), 'Limelight-Regular'),
                                     ('SPLASHLAND', 50, (150, 30, 60), 'Limelight-Regular')], ((210, 200, 170), (60, 40, 30)), -40, 2.0, size=(0.8, 0.6))
    trov = (1.6, 0.4, 0.04)
    foglio('Trovato', disegno('robin'), (0.40, 0.30), trov, (0, 0, math.radians(-20)), curva=0.01)
    return {'trovato': trov, 'letto': CENTRO}


def scarpa(name, c, rot, mat):
    """Una scarpetta da bambino (suola, tomaia arrotondata)."""
    o = palla(name, 0.1, c, mat=mat, scale=(0.55, 1.25, 0.5))
    o.rotation_euler = rot
    return o


def sdf_anello(name, R, mat):
    v, f, _ = sdf.mesh(sdf.torus((0, 0, 0), R, R * 0.18, axis='z'), (-R * 1.4,) * 2 + (-R * 0.4,), (R * 1.4,) * 2 + (R * 0.4,), res=R * 0.08)
    ob = grotte.mesh_obj(name, v, f)
    ob.data.materials.append(mat)
    return ob


def tana_archie():
    """Una festa di compleanno sommersa (maggio 1999): il tavolo con la tovaglia, le torte con le candeline spente, i
    cappellini, i palloncini, lo striscione degli auguri, le lucine della festa sulle pareti."""
    rr = np.random.default_rng(15)
    c = np.array(CENTRO) + np.array((0.0, 0.3, 0.0))
    tov = strisce_material('TATovaglia', (0.62, 0.60, 0.55), (0.45, 0.06, 0.08), passo=0.12, asse=0)
    legn = legno_gonfio('TALegno')
    cilindro('Tavolo', 1.0, 0.06, (c[0], c[1], 0.78), mat=legn, verts=48)
    cilindro('Gamba', 0.08, 0.76, (c[0], c[1], 0.38), mat=legn)
    for k in range(3):
        a = 2 * math.pi * k / 3
        o = tube('Piede', [(c[0], c[1], 0.05), (c[0] + 0.45 * math.cos(a), c[1] + 0.45 * math.sin(a), 0.02)], 0.035, n=8, col=COL)
        o.data.materials.append(legn)
        _lg(o)
    telo('Tovaglia', (2.2, 2.2), (c[0], c[1], 0.81), mat=tov, onde=0.02, giu=0.2, seed=7)
    rosa = grotte.plastica('TATorta', (0.70, 0.45, 0.50), melma=0.4)
    for k, (dx, dy) in enumerate(((-0.4, 0.1), (0.38, -0.15), (0.0, 0.5))):
        o = lathe('Torta', [(0.24, 0.0), (0.25, 0.12), (0.2, 0.13), (0.2, 0.2), (0.0, 0.21)], n=28, col=COL, close_bottom=True)
        o.location = (c[0] + dx, c[1] + dy, 0.84)
        o.data.materials.append(rosa)
        _lg(o)
        for j in range(7):
            a = 2 * math.pi * j / 7
            cilindro('Candelina', 0.012, 0.09, (c[0] + dx + 0.13 * math.cos(a), c[1] + dy + 0.13 * math.sin(a), 1.09),
                     mat=grotte.plastica('TACandela%d' % (j % 3), [(0.1, 0.3, 0.7), (0.7, 0.6, 0.1), (0.15, 0.5, 0.2)][j % 3]))
    for k in range(8):
        a = rr.uniform(0, 6.28)
        r = rr.uniform(1.3, 2.8)
        o = lathe('Cappellino', [(0.09, 0.0), (0.0, 0.24)], n=16, col=COL, close_bottom=True)
        o.location = (c[0] + r * math.cos(a), c[1] + r * math.sin(a), 0.02)
        o.rotation_euler = (rr.normal(0, 0.8), rr.normal(0, 0.8), 0)
        o.data.materials.append(grotte._mat('ArchieCarta', grotte._carta))
        _lg(o)
    cols = [(0.6, 0.05, 0.08), (0.08, 0.2, 0.6), (0.7, 0.55, 0.05), (0.1, 0.45, 0.15), (0.55, 0.15, 0.5)]
    for k in range(11):
        p = (c[0] + rr.normal(0, 1.8), c[1] + rr.normal(0, 1.2), rr.uniform(2.6, 3.6))
        palla('Palloncino', 0.2, p, mat=grotte.plastica('TAPalloncino%d' % (k % 5), cols[k % 5], rough=0.2, melma=0.15), scale=(1, 1, 1.2))
        tube('Spago', [(p[0], p[1], p[2] - 0.24), ((p[0] + c[0]) / 2, (p[1] + c[1]) / 2, p[2] * 0.5), (c[0], c[1], 0.8)],
             0.004, n=4, col=COL).data.materials.append(grotte.corda_material())
    # lo striscione degli auguri teso sulla parete in fondo, e le lucine della festa tutt'attorno
    pa, _ = parete(-30, 2.9)
    pb, _ = parete(30, 2.9)
    mid = (pa + pb) / 2
    fondo = strisce_material('TAStriscione', (0.62, 0.60, 0.55), (0.62, 0.60, 0.55), passo=1.0)
    st = pannello('Striscione', (float(np.linalg.norm(pb - pa)) * 0.9, 0.6), fondo, seed=8, onde=0.06)
    su_parete(st, 0, 2.9, stacco=0.25)
    scritta('Auguri', 'TANTI AUGURI', 0.38, tuple(np.array(st.location) + np.array((0, -0.03, 0))), (math.radians(90), 0, 0),
            grotte.plastica('TAScritta', (0.45, 0.06, 0.08), melma=0.2), extrude=0.008)
    for k, (y0, y1, z) in enumerate(((-100, -30, 3.0), (-30, 40, 3.2), (40, 110, 3.0), (-120, -60, 2.2), (60, 120, 2.2))):
        a_, _ = parete(y0, z)
        b_, _ = parete(y1, z)
        lucine(f'Lucine{k}', a_ + np.array((0, 0, 0)), b_, n=24, sag=0.45, seed=k)
    manifesto_su_parete('festa', [('FESTA', 90, (200, 40, 60), 'Limelight-Regular'), ('MAGGIO 1999', 60, (40, 40, 120), 'Limelight-Regular')],
                        ((235, 220, 170), (200, 40, 60)), 70, 1.6, size=(0.6, 0.45))
    trov = (c[0] - 0.55, c[1] - 0.6, 0.85)
    foglio('Trovato', disegno('archie'), (0.36, 0.26), trov, (math.radians(4), 0, math.radians(15)), curva=0.004)
    return {'trovato': trov, 'letto': tuple(c)}


def tana_lampy():
    """La cameretta di una neonata del 2003: la carta da parati a fiori strappata, la culla con la giostrina di
    pesciolini, la vaschetta da bagno, le cuffie a fiori appese."""
    rr = np.random.default_rng(16)
    c = np.array(CENTRO)
    carta = carta_da_parati_material()
    for k, (yaw, z, sz) in enumerate(((-75, 1.6, (2.4, 2.4)), (-40, 1.8, (2.6, 2.8)), (-5, 1.9, (2.8, 2.6)), (30, 1.8, (2.6, 2.8)),
                                       (65, 1.6, (2.4, 2.4)), (100, 1.3, (1.8, 1.8)), (-110, 1.3, (1.8, 1.8)))):
        su_parete(pannello('CartaParati', sz, carta, seed=40 + k, onde=0.05), yaw, z, stacco=0.07, inclina=rr.normal(0, 0.04))
    bianco = grotte.plastica('TLBianco', (0.62, 0.60, 0.56), melma=0.45)
    # la culla: il fondo, le testate arcuate, le sbarre tornite
    scatola('CullaFondo', (1.3, 0.75, 0.06), (c[0], c[1], 0.45), mat=bianco)
    for s_ in (-1, 1):
        o = lathe('Testata', [(0.0, 0.0), (0.4, 0.0), (0.4, 0.5), (0.3, 0.62), (0.0, 0.66)], n=4, col=COL)
        o.location = (c[0] + s_ * 0.66, c[1], 0.2)
        o.rotation_euler = (0, 0, math.radians(45))
        o.scale = (0.08, 1.4, 1.0)
        o.data.materials.append(bianco)
        _lg(o)
        for k in range(10):
            x = c[0] - 0.58 + k * 0.13
            o = lathe('Sbarra', [(0.015, 0.0), (0.022, 0.08), (0.013, 0.2), (0.022, 0.32), (0.015, 0.42)], n=8, col=COL)
            o.location = (x, c[1] + s_ * 0.37, 0.48)
            o.data.materials.append(bianco)
            _lg(o)
        scatola('Corrimano', (1.3, 0.05, 0.04), (c[0], c[1] + s_ * 0.37, 0.92), mat=bianco)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cilindro('Piede', 0.03, 0.45, (c[0] + sx * 0.6, c[1] + sy * 0.32, 0.22), mat=bianco, verts=8)
    telo('Copertina', (1.2, 0.7), (c[0], c[1], 0.5), mat=grotte.plastica('TLCopertina', (0.55, 0.35, 0.45), melma=0.5), onde=0.03, seed=9)
    # la giostrina: appesa alla volta sopra la culla
    asta = (c[0], c[1], 1.75)
    tube('GiostrinaFilo', [(c[0], c[1], 3.4), asta], 0.006, n=5, col=COL).data.materials.append(grotte.corda_material())
    cols = [(0.7, 0.4, 0.05), (0.1, 0.4, 0.6), (0.65, 0.15, 0.3), (0.2, 0.5, 0.2), (0.75, 0.7, 0.2)]
    cilindro('GiostrinaDisco', 0.3, 0.03, asta, mat=bianco, verts=24)
    for k in range(5):
        a = 2 * math.pi * k / 5
        p = (asta[0] + 0.32 * math.cos(a), asta[1] + 0.32 * math.sin(a), asta[2] - 0.3)
        tube('GiostrinaFiletto', [(p[0], p[1], asta[2]), p], 0.003, n=4, col=COL).data.materials.append(grotte.corda_material())
        palla('Pesciolino', 0.08, p, mat=grotte.plastica('TLPesce%d' % k, cols[k], rough=0.25, melma=0.2), scale=(0.5, 1.4, 0.8))
    o = lathe('Vaschetta', [(0.42, 0.0), (0.46, 0.25), (0.48, 0.30), (0.44, 0.30), (0.40, 0.05)], n=28, col=COL, close_bottom=True)
    o.location = (-2.4, 1.6, 0.0)
    o.scale = (1.4, 0.9, 1.0)
    o.data.materials.append(grotte.plastica('TLVasca', (0.15, 0.40, 0.55), melma=0.5))
    _lg(o)
    palla('Paperella', 0.08, (-2.3, 1.5, 0.3), mat=grotte.plastica('PaperellaGialla', (0.86, 0.62, 0.10), rough=0.3, melma=0.5), scale=(1.0, 1.3, 0.9))
    fiori = grotte._mat('LampyFioriMat', grotte._fiori)
    for k in range(6):
        p, n = parete(55 + k * 9, 1.6 + 0.3 * math.sin(k * 1.3))
        palla('Cuffia', 0.13, tuple(p + n * 0.18), mat=fiori, scale=(1.0, 1.1, 0.8))
    manifesto_su_parete('lampy', [('BENVENUTA!', 70, (170, 60, 110), 'Limelight-Regular'), ('LUGLIO 2003', 55, (60, 60, 60), 'Limelight-Regular')],
                        ((240, 215, 225), (170, 60, 110)), -20, 2.3, size=(0.6, 0.4))
    trov = (c[0] + 0.25, c[1] - 0.1, 0.56)
    foglio('Trovato', disegno('lampy'), (0.30, 0.22), trov, (0, 0, math.radians(-12)), curva=0.004)
    return {'trovato': trov, 'letto': tuple(c), 'soffitto': (c[0], c[1], 3.5)}


def tana_fangy():
    """Bende per gli occhi, occhialini dipinti di nero, il gioco del Marco Polo; attorno al letto conchiglie appese
    che tintinnano (agosto 2008). Sulle pareti, le cose del lido: i cartelli, il salvagente arancione."""
    rr = np.random.default_rng(17)
    c = np.array(CENTRO)
    letto('Letto', (c[0], c[1], 0.0), 0.0, seed=10)
    conch = grotte.plastica('TFConchiglia', (0.70, 0.62, 0.52), rough=0.35, melma=0.25)
    for k in range(48):
        a = 2 * math.pi * k / 48
        x, y = c[0] + 1.35 * math.cos(a), c[1] + 1.75 * math.sin(a)
        top = 3.2 + 0.4 * rr.uniform()
        z = rr.uniform(1.0, 2.3)
        tube('Filo', [(x, y, top), (x, y, z + 0.06)], 0.003, n=4, col=COL).data.materials.append(grotte.corda_material())
        o = lathe('Conchiglia', [(0.0, 0.0), (0.05, 0.02), (0.06, 0.06), (0.02, 0.09)], n=10, col=COL)
        o.location = (x, y, z)
        o.rotation_euler = (rr.uniform(0, 3), rr.uniform(0, 3), 0)
        o.data.materials.append(conch)
        _lg(o)
    benda = grotte.plastica('TFBenda', (0.10, 0.10, 0.12), melma=0.3)
    for k in range(5):
        telo('Benda', (0.9, 0.08), (rr.uniform(-3, 3), rr.uniform(0, 4), 0.03), rot=(0, 0, rr.uniform(0, 3)), mat=benda, onde=0.02, seed=20 + k)
    nero = grotte.semplice('FangyLenti', (0.008, 0.008, 0.01), rough=0.12, coat=1.0)
    sgabello('Sgabello', (1.6, 1.0, 0.0))
    for s_ in (-1, 1):
        palla('Lente', 0.045, (1.6 + s_ * 0.06, 1.0, 0.56), mat=nero, scale=(1.0, 0.6, 0.8))
    # le cose del lido sulle pareti: il cartello del Marco Polo, il calendario di agosto 2008, il salvagente
    manifesto_su_parete('marco', [('MARCO?', 110, (180, 30, 30), 'Limelight-Regular'), ('POLO!', 110, (30, 60, 150), 'Limelight-Regular'),
                                  ('si gioca a occhi chiusi', 36, (60, 60, 60), 'Limelight-Regular')], ((225, 225, 210), (30, 60, 150)), -35, 1.9, size=(0.8, 0.7))
    manifesto_su_parete('agosto', [('AGOSTO', 80, (40, 40, 40), 'Limelight-Regular'), ('2008', 120, (180, 30, 30), 'Monoton-Regular')],
                        ((230, 230, 220), (90, 90, 90)), 40, 2.0, size=(0.5, 0.6))
    p, n = parete(75, 1.5)
    o = sdf_ring('Salvagente', tuple(p + n * 0.2), 0.0, 0.0, grotte.plastica('TFSalvagente', (0.75, 0.30, 0.05), melma=0.4))
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector(tuple(n)).to_track_quat('Z', 'Y')
    for k in range(3):
        cilindro('Tubo', 0.07, 1.4, (-2.0 + k * 0.3, 1.0, 0.07), rot=(0, math.radians(90), rr.uniform(0, 3)),
                 mat=grotte.plastica('TFTubo%d' % k, [(0.6, 0.1, 0.4), (0.1, 0.5, 0.6), (0.7, 0.6, 0.1)][k], melma=0.3))
    trov = (-0.9, 0.3, 0.02)
    foglio('Trovato', disegno('fangy'), (0.42, 0.30), trov, (0, 0, math.radians(25)), curva=0.006)
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
    """Disteso sul fianco sopra la pila di salvagenti, di traverso davanti al sub, gli occhi chiusi e la mascella
    rilassata (deciso il 12 ottobre: addormentato davvero)."""
    import gulpy
    o = (CENTRO[0] + 0.9, CENTRO[1] - 0.2, 0.95)
    M = M_tana(o, yaw=_verso_occhio(o) + 8.0, roll=-88.0, scale=0.95 * (1.0 + 0.03 * fiato))
    obs = gulpy.build(viewer=_loc(M, (o[0], o[1] - 3.0, 0.0)), mascella=5.0 + 3.0 * fiato)
    chiudi_occhi(obs, 'GulpyEye', 'GulpyHead')
    # dove il modello finisce (sotto il pelo dell'acqua, nelle pose in mare) un salvagente grande lo fascia: sembra
    # che ne stia scivolando fuori
    anello = sdf_ring('SalvagenteGrande', (0.0, 0.0, 0.0), 0.0, 0.0, grotte.plastica('PaperellaGialla', (0.86, 0.62, 0.10), rough=0.3, melma=0.5), R=0.42, r=0.15)
    anello.location = (0.0, -0.05, 0.10)
    obs.append(anello)
    return _metti(obs, M)


def chiudi_occhi(obs, prefisso, pelle):
    """Gli occhi chiusi dei mostri senza palpebre: il bulbo prende la pelle della testa (la palpebra abbassata)."""
    sk = next((o.data.materials[0] for o in obs if o.name.startswith(pelle) and o.data.materials), None)
    if sk is None:
        return
    for o in obs:
        if o.name.startswith(prefisso) and o.type == 'MESH':
            o.data.materials.clear()
            o.data.materials.append(sk)
            o.scale = tuple(x * 1.12 for x in o.scale)


def dorme_molly(info, fiato=0.0):
    """Sotto una coperta di asciugamani con i braccioli sopra, tirata fino al mento: fuori solo la testa e le mani che
    stringono l'orlo (il modello ha solo testa e mani: l'orlo della coperta prende il posto del capodibanda della barca).
    Un occhio chiuso, quello che scivola via socchiuso."""
    import molly as mo
    o = info['letto']
    M = M_tana((o[0], o[1], 0.0), yaw=_verso_occhio(o), pitch=-12.0, scale=1.35 * (1.0 + 0.02 * fiato))
    obs = mo.build(viewer=_loc(M, (o[0], o[1] - 3.0, 0.3)), palpebre=(1.0, 0.55))
    obs.append(coperta(mo.GUN_TOP, fiato))
    return _metti(obs, M)


def coperta(top, fiato=0.0):
    """La coperta di asciugamani (coordinate locali di Molly: l'orlo corre lungo X a y = 0, quota top): davanti cade
    fino alla sabbia, dietro fa la gobba del corpo che non c'è."""
    nx, ny = 48, 60
    xs = np.linspace(-0.85, 0.85, nx)
    ys = np.linspace(-0.75, 1.9, ny)
    V_, Fc = [], []
    rr = np.random.default_rng(31)
    ph = rr.uniform(0, 6.28, 4)
    for y in ys:
        for x in xs:
            lato = max(0.0, 1.0 - (abs(x) / 0.85) ** 4)
            if y < 0.03:
                # davanti: l'orlo scende ripido subito (le dita che lo stringono si vedono), poi cade fino alla sabbia
                d = 0.03 - y
                z = (top - 0.24 * (1.0 - math.exp(-d / 0.035))) * max(0.0, 1.0 - d / 0.78) ** 0.55
            else:
                z = top * (1.0 - (y / 1.9) ** 2) * (1.0 + 0.04 * fiato * math.sin(math.pi * y / 1.9))
            z = z * (0.25 + 0.75 * lato) + 0.03 * math.sin(x * 9 + ph[0]) * math.sin(y * 7 + ph[1])
            V_.append((x, y - 0.012, max(z, 0.0) + 0.012))
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            Fc.append((a, a + 1, a + nx + 1))
            Fc.append((a, a + nx + 1, a + nx))
    ob = grotte.mesh_obj('MollyCoperta', np.array(V_), np.array(Fc))
    ob.data.materials.append(strisce_material('TMAsciugamani', (0.55, 0.12, 0.30), (0.62, 0.60, 0.55), passo=0.22, asse=0))
    return ob


def corpo_rannicchiato():
    """Il corpo di Hatch (hatch.body_field) rannicchiato (deciso il 12 ottobre): seduto sul fondo dell'armadio, le
    ginocchia al petto e le braccia strette attorno alle gambe, come un bambino nascosto a nascondino. Busto e testa
    restano quelli del modello (la testa cade in avanti con la trasformazione); cambiano gambe e braccia."""
    import hatch as ha
    from dettagli import V, chain, hair_clump
    import skin
    torso = chain([V(0, 0.06, 1.48), V(0, 0.02, 2.02), V(0, -0.17, 2.40), V(0, -0.33, 2.55)], [0.10, 0.112, 0.112, 0.092], k=0.05)
    pelvis = sdf.ellipsoid(V(0, 0.06, 1.46), (0.13, 0.09, 0.08))
    sh = sdf.union(*[sdf.ellipsoid(V(s * 0.17, -0.21, 2.43), (0.072, 0.078, 0.062)) for s in (-1, 1)], k=0.08)
    neck = chain([V(0, -0.33, 2.55), V(0, -0.47, 2.56)], [0.064, 0.058], k=0.02)
    parts = [torso, pelvis, sh, neck]
    for i in range(6):
        z = 1.86 + i * 0.075
        yc = 0.02 - 0.42 * (z - 1.86)
        w = 0.105 - 0.004 * i
        pts = [V(-w, yc + 0.05, z + 0.015), V(-w * 0.78, yc - 0.06, z), V(-0.03, yc - 0.105, z - 0.03), V(0.03, yc - 0.105, z - 0.03), V(w * 0.78, yc - 0.06, z), V(w, yc + 0.05, z + 0.015)]
        parts.append(hair_clump(pts, 0.009, 0.0085))
    for s in (-1, 1):
        # le gambe piegate: la coscia sale davanti al petto, lo stinco ridiscende, i piedi sotto il bacino
        # (tutto dietro y = −0,44: davanti a −0,47 il modello taglia il corpo per la cucitura del collo)
        hip, knee, ankle = V(s * 0.09, 0.02, 1.42), V(s * 0.13, -0.36, 2.02), V(s * 0.11, -0.28, 1.38)
        parts.append(chain([hip, hip + (knee - hip) * 0.35, knee], [0.05, 0.052, 0.034], k=0.02))
        parts.append(chain([knee, knee + (ankle - knee) * 0.3, ankle], [0.034, 0.036, 0.022], k=0.02))
        parts.append(sdf.ellipsoid(knee + V(0, -0.02, 0), (0.042, 0.045, 0.042)))
        for dx in (-0.025, 0.0, 0.025):
            toe = ankle + V(dx * 1.6, -0.11, -0.06)
            parts.append(hair_clump([ankle, (ankle + toe) / 2 + V(0, 0, 0.012), toe], 0.016, 0.006))
        # le braccia attorno agli stinchi, le mani che si stringono davanti
        sh_p, el, wr = V(s * 0.18, -0.22, 2.41), V(s * 0.30, -0.36, 2.00), V(s * 0.07, -0.40, 1.78)
        parts.append(chain([sh_p, el], [0.040, 0.027], k=0.015))
        parts.append(chain([el, wr], [0.027, 0.020], k=0.015))
        parts.append(sdf.sphere(el, 0.031))
        for dx, L in ((-0.03, 0.85), (-0.01, 1.0), (0.01, 0.97), (0.03, 0.8)):
            k1 = wr + V(-s * 0.05 * L, 0.01 + dx * 0.5, -0.03)
            k2 = k1 + V(-s * 0.04 * L, 0.03, -0.02)
            parts.append(hair_clump([wr, k1, k2], 0.0145, 0.006))
    body = sdf.union(*parts, k=0.03)
    body = sdf.displace(body, skin.bumps(81, 0.04, 0.003), 1.0)
    return sdf.displace(body, skin.bumps(82, 0.01, 0.0009), 1.0)


def dorme_hatch(info, fiato=0.0):
    """Rannicchiato in fondo all'armadio, le ginocchia al petto (deciso il 12 ottobre), la testa china sulle
    ginocchia, la bocca chiusa, l'esca del giocattolo che si accende e si spegne piano."""
    import hatch
    a = info.get('armadio', (0.0, 3.3, 0.0))
    o = (a[0], a[1] - 0.05, -1.30 * 0.95)
    M = M_tana(o, yaw=_verso_occhio(o), pitch=12.0 + 2.0 * fiato, scale=0.95)
    orig = hatch.body_field
    hatch.body_field = corpo_rannicchiato
    try:
        obs = hatch.build(viewer=_loc(M, (a[0], a[1] - 1.0, 0.0)), bocca=0.0)
    finally:
        hatch.body_field = orig
    luci = [x for x in bpy.data.objects if x.type == 'LIGHT' and x.name.startswith('ToyLight')]
    for li in luci:
        li.data.energy = 3.0 + 3.0 * fiato
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
    o = (c[0] + 0.1, c[1], 0.62)
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
