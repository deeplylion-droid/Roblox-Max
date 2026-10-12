"""
I jumpscare: la creatura, dalla sua posa di gioco, si lancia sul pescatore.

Sono fotogrammi a tutto schermo (non strati del panorama), visti dall'occhio del pescatore:
lo sfondo (mondo + barca) si rende una volta sola, la creatura in ogni fotogramma con il resto della
scena come maschera; poi si compongono e si codificano come gli altri render (overlays.json → jumpscares).
Molly si rende sul lato destro: per il sinistro il motore specchia l'immagine.
Archie (notte 3) arriva dopo che il vetro della lampara è esploso: nella sua scena la lampara è spenta.
Lampy (notte 4) arriva dalla lenza con la ventosa spalancata, e da un fotogramma all'altro gli anelli di denti girano.
Fangy (notte 5) si lancia dalla fiancata con le zanne avanti e tutte le lucine accese.
L'animatore (dalla notte 2) sale dall'acqua a prua e ti abbraccia; l'occhio che penzola dondola (SPIN).

Uso: tools/.venv/bin/python tools/render/jobs.py jumpscare --quality preview   (JUMPSCARES=gulpy,molly,hatch,robin;
JS_ANTEPRIMA=1 per lasciare i fotogrammi in cache senza toccare il gioco; Archie, Lampy e Fangy si chiedono a parte:
JUMPSCARES=archie, JUMPSCARES=lampy, JUMPSCARES=fangy, JUMPSCARES=foxy)
"""
from __future__ import annotations

import json
import math
import os
import time

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

import scena_creature as sc
from common import CACHE, EYE, OUT_IMG, log, perspective_camera, render

FRAMES = 8
FPS = 10


def ease(t):
    """Parte lento e arriva addosso di colpo."""
    return t * t * t * (t * (6 * t - 15) + 10) if t < 1 else 1.0


def _lerp_matrix(a: Matrix, b: Matrix, t: float) -> Matrix:
    la, ra, sa = a.decompose()
    lb, rb, sb = b.decompose()
    loc = la.lerp(lb, t)
    rot = ra.slerp(rb, t)
    scl = sa.lerp(sb, t)
    return Matrix.LocRotScale(loc, rot, scl)


def _toward_eye(M: Matrix, head_local, dist, extra_pitch=0.0):
    """Trasforma M in modo che il punto head_local finisca a 'dist' metri dall'occhio, sulla stessa linea,
    ruotando la creatura in avanti di extra_pitch gradi attorno alla testa."""
    h0 = M @ Vector(tuple(map(float, head_local)))
    eye = Vector(EYE)
    d = (h0 - eye).normalized()
    target = eye + d * dist
    # rotazione attorno all'asse orizzontale perpendicolare alla linea di vista
    axis = d.cross(Vector((0, 0, 1))).normalized()
    R = Matrix.Rotation(math.radians(extra_pitch), 4, axis)
    return Matrix.Translation(target) @ R @ Matrix.Translation(-h0) @ M


# ───────────────────────── le tre creature ─────────────────────────

def gulpy_attack():
    import gulpy
    obs = sc.gulpy_pretende()
    M0 = sc.LAST_M['gulpy_pretende']
    head = gulpy.HEAD.pt((0, -0.05, -0.18))         # dentro la bocca spalancata
    M1 = _toward_eye(M0, head, 0.42, extra_pitch=-14.0)
    aim = M0 @ Vector(tuple(map(float, head)))
    return obs, M0, M1, aim


def molly_attack():
    import molly as mo
    obs = sc.molly(+1)
    M0 = sc.LAST_M['molly_destra']
    face = mo.C
    M1 = _toward_eye(M0, face, 0.30, extra_pitch=0.0)
    # sale di scatto oltre il bordo: parte un po' più in alto e più vicina
    aim = M0 @ Vector(tuple(map(float, face)))
    return obs, M0, M1, aim


def hatch_attack():
    import hatch
    # dalla sua posa di gioco (in acqua dietro la poppa, piegato sulla barca) si avventa su di te.
    # In piedi sul ponte di poppa non si può: è così alto che la testa finirebbe sopra di te, fuori quadro.
    obs = sc.hatch_conta()
    M0 = sc.LAST_M['hatch_conta']
    for li in bpy.data.objects:
        if li.type == 'LIGHT' and li.name.startswith('ToyLight'):
            li.data.energy = 6.0                       # da vicino basta meno che a qualche metro
    head = hatch.HEAD.pos
    M1 = _toward_eye(M0, head, 0.34, extra_pitch=14.0)
    aim = M0 @ Vector(tuple(map(float, head)))
    return obs, M0, M1, aim


def robin_attack():
    import robin as ro
    # il secchio è vuoto: la mano esce dal secchio senza pesce, le arcate aggrottate; si stacca dal bordo e ti
    # salta in faccia (la testa, larga quasi mezzo metro, si ferma a due spanne dall'occhio)
    M0, kw = sc.robin_posa()
    sc.LAST_M['robin_secchio'] = M0
    obs = sc.place(ro.build(**kw, fish=False, aggrotta=1.0), M0)
    head = ro.HEAD
    M1 = _toward_eye(M0, head, 0.44, extra_pitch=12.0)
    # la camera mira un po' sotto il centro della testa: alla fine nel quadro restano anche la bocca e i denti
    aim = M0 @ Vector(tuple(float(v) for v in head + np.array((0.0, 0.0, -0.08))))
    return obs, M0, M1, aim


def _lampara_esplosa():
    """La lampara è appena esplosa: il vetro non c'è più, la reticella e la lampadina di servizio sono spente, e con
    loro tutto quello che illumina la lampara (le sue luci, il bagliore sul mare). Restano la luna e la lanterna."""
    for o in bpy.data.objects:
        if o.name.startswith('LampGlass') or o.lightgroup == 'lamp':
            o.hide_render = True


def _occhi_accesi(obs, forza=2.5):
    """Gli occhi che brillano al buio, come nel gioco a lampara spenta (la stessa tinta verdognola)."""
    for o in obs:
        if o.type != 'MESH' or 'Eye' not in o.name or not o.data.materials:
            continue
        m = o.data.materials[0].copy()
        m.name = o.data.materials[0].name + 'Buio'
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                n.inputs['Emission Color'].default_value = (0.55, 0.70, 0.62, 1.0)
                n.inputs['Emission Strength'].default_value = forza
        o.data.materials[0] = m


def archie_attack():
    import archie as ar
    # ha soffiato con la lampara accesa e il vetro è esploso: nel buio la trombetta si è riavvolta di scatto, gli occhi
    # brillano; si stacca dalla lampara e ti viene addosso. La testa si gira verso di te, di tre quarti (il muso ti
    # passa appena a sinistra, si vedono l'occhio acceso e la fila di zanne) e ti guarda un po' dall'alto; il collo resta
    # dietro la testa
    _lampara_esplosa()
    M0, kw = sc.archie_posa()
    sc.LAST_M['archie_soffia'] = M0
    obs = sc.place(ar.build(**kw), M0)
    _occhi_accesi(obs)
    fr = ar.testa_frame(kw['lampara'])
    R0 = M0.to_3x3()
    h0 = M0 @ Vector(tuple(map(float, ar.HEAD)))
    f0 = (R0 @ Vector(tuple(map(float, fr.dir((0.0, -1.0, 0.0)))))).normalized()
    v = (h0 - Vector(EYE)).normalized()
    vh = Vector((v.x, v.y, 0.0)).normalized()
    left = Vector((0.0, 0.0, 1.0)).cross(vh)
    side = math.radians(ARCHIE_JS['lato'])
    want = (-vh * math.cos(side) + left * math.sin(side)).normalized()
    turn = math.atan2(want.y, want.x) - math.atan2(f0.y, f0.x)
    q = Quaternion((0.0, 0.0, 1.0), turn)
    f1 = q @ f0
    axis = f1.cross(Vector((0.0, 0.0, 1.0))).normalized()
    q = Quaternion(axis, math.radians(ARCHIE_JS['muso']) - math.asin(max(-1.0, min(1.0, f1.z)))) @ q
    target = Vector(EYE) + v * ARCHIE_JS['dist'] - left * ARCHIE_JS['destra']
    M1 = Matrix.Translation(target) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h0) @ M0
    # la camera mira un po' sotto il centro della testa: alla fine nel quadro restano le mascelle coi denti
    aim = M0 @ Vector(tuple(float(x) for x in ar.HEAD + np.array((0.0, 0.0, -0.05))))
    return obs, M0, M1, aim


# Archie alla fine del jumpscare: a quanti metri dall'occhio arriva il centro della testa (e di quanto a destra della
# linea dello sguardo, perché il muso e la trombetta restino nel quadro), di quanti gradi il muso passa a sinistra della
# camera e quanto guarda in giù (gradi, negativo). Di tre quarti: di fronte il muso lungo si accorcia e la testa non si
# legge più, di profilo ti passa accanto
ARCHIE_JS = {'dist': 0.52, 'destra': 0.05, 'lato': 28.0, 'muso': -12.0}

def lampy_attack():
    import lampy as la
    # l'hai agganciata: è risalita per la lenza e ti salta in faccia, la ventosa spalancata a disco con gli anelli di
    # denti da latte che girano come una macina (quelli vicini in versi opposti: da un fotogramma all'altro, SPIN), la
    # cuffia a fiori, gli occhi tondi senza palpebre fissi su di te. Parte dalla posa sulla lenza (lì la faccia ti
    # guarda già) e viene dritta sulla linea dello sguardo; il corpo ad arco le resta dietro
    M0, kw = sc.lampy_posa()
    sc.LAST_M['lampy_lenza'] = M0
    obs = sc.place(la.build(**kw, bocca=1.0, denti_giro=0.0), M0)
    fr = la.testa_frame(la.V(*kw['viewer']))
    v = la.ventosa(1.0)
    bocca = tuple(float(x) for x in fr.pt(v['c']))
    M1 = _toward_eye(M0, bocca, LAMPY_JS['dist'], extra_pitch=LAMPY_JS['pitch'])
    aim = M0 @ Vector(bocca)
    teeth = next(o for o in obs if o.name.startswith('LampyTeeth'))

    def spin(i):
        if i == 0:
            return
        nuovo = la.denti(fr, v, LAMPY_JS['giro'] * i)
        vecchio = teeth.data
        teeth.data = nuovo.data
        bpy.data.objects.remove(nuovo)
        bpy.data.meshes.remove(vecchio)
    SPIN['lampy'] = spin
    return obs, M0, M1, aim


# Lampy alla fine del jumpscare: a quanti metri dall'occhio arriva il centro della ventosa (spalancata è larga 40 cm: le
# riempie mezzo quadro), quanto si china in avanti (gradi), di quanti gradi girano gli anelli di denti a ogni fotogramma
LAMPY_JS = {'dist': 0.62, 'pitch': 0.0, 'giro': 9.0}

def fangy_attack():
    import fangy as fa
    # ti ha sentito tre volte: si lancia dalla fiancata con la testa avanti, le zanne puntate su di te e tutte le lucine
    # accese (nel gioco al rumore si accendono tutte insieme). Parte dalla posa di gioco, dove la faccia cieca ti guarda
    # già, e viene dritto sulla linea dello sguardo; il corpo e le braccia gli restano dietro, sotto il bordo
    M0, kw = sc.fangy_posa()
    sc.LAST_M['fangy_ascolta'] = M0
    obs = sc.place(fa.build(**kw, testa=0.0, luci=1.0), M0)
    testa = tuple(float(x) for x in fa.HEAD)
    M1 = _toward_eye(M0, testa, FANGY_JS['dist'], extra_pitch=FANGY_JS['pitch'])
    # la camera mira un po' sotto il centro della testa: alla fine nel quadro restano la bocca e le zanne
    aim = M0 @ Vector(tuple(float(x) for x in fa.HEAD + np.array((0.0, 0.0, -0.06))))
    return obs, M0, M1, aim


# Fangy alla fine del jumpscare: a quanti metri dall'occhio arriva il centro della testa, e quanto si china in avanti
# (gradi: le zanne vengono verso la camera)
FANGY_JS = {'dist': 0.55, 'pitch': 6.0}

def foxy_attack():
    import animatore as an
    # l'animatore (dalla notte 2): l'hai trascurato e dal relitto è venuto fino alla barca. La camera guarda il bordo a
    # prua sulla dritta, appena in basso, col mare e la foschia chiara dietro: lui sale da sotto il capodibanda (la
    # sagoma si stacca contro la foschia), poi ti viene addosso e ti abbraccia. Alla fine la sua faccia, fuori dalla
    # bocca del costume, riempie il quadro a mezzo metro; le mani ossute entrano dai lati e dal basso con le dita aperte
    # vicine all'obiettivo; l'occhio da cartone dondola di lato. «Lo spettacolo finiva sempre con un abbraccio.»
    before = set(bpy.data.objects)
    _, face = an.build('abbraccio', occhio=0.0)
    obs = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    J = FOXY_JS
    eye = Vector(EYE)
    a = math.radians(J['yaw'])
    hor = Vector((math.sin(a), math.cos(a), 0.0))
    pos = eye + hor * J['parte']
    pos.z = J['z']
    t = eye - pos
    M0 = Matrix.Translation(pos) @ Matrix.Rotation(math.atan2(t.x, -t.y), 4, 'Z')
    # la camera: verso il bordo, appena in basso
    aim = eye + hor * J['mira_dist']
    aim.z = J['mira_z']
    d = cam_dir(aim)
    face_l = Vector(tuple(map(float, face)))
    # a metà: è salito sul bordo, dove stava (la faccia sopra il capodibanda)
    Mmid = Matrix.Translation((0.0, 0.0, J['sale'])) @ Matrix.Translation(-hor * J['avanza']) @ M0
    # alla fine: la faccia sulla linea della camera, a J['dist'] metri, girata verso di te e un po' all'indietro
    yaw1 = math.atan2(-d.x, d.y)
    R1 = Matrix.Rotation(yaw1, 4, 'Z') @ Matrix.Rotation(math.radians(J['indietro']), 4, 'X')
    M1 = Matrix.Translation(eye + d * J['dist']) @ R1 @ Matrix.Translation(-face_l)

    def path(u):
        u = J['parte_da'] + (1 - J['parte_da']) * u
        k = J['meta']
        if u < k:
            return _lerp_matrix(M0, Mmid, (u / k) ** 0.9)
        w = (u - k) / (1 - k)
        return _lerp_matrix(Mmid, M1, w * w * (3 - 2 * w) * 0.35 + w ** 1.6 * 0.65)
    PATH['foxy'] = path
    # l'occhio che dondola, di lato: si ruotano i vertici dell'occhio, del brandello e dei suoi fili attorno al punto in
    # cui il brandello esce dall'orbita (nelle coordinate della creatura, prima di metterla in scena)
    swing = [o for o in obs if o.name.startswith(('ToonEyeHang', 'EyeStrip'))]
    threads = sorted((o for o in obs if o.name.startswith('Threads')), key=lambda o: o.name)
    if threads:
        swing.append(threads[-1])
    strip = next(o for o in obs if o.name.startswith('EyeStrip'))
    top = max((strip.matrix_world @ v.co for v in strip.data.vertices), key=lambda v: v.z)
    local = {o.name: (o.matrix_world.copy(), [v.co.copy() for v in o.data.vertices]) for o in swing}
    # la luce calda dalla parte della lanterna, solo sulla faccia dell'uomo (gli occhi lattiginosi e i denti bagnati
    # brillano, il costume resta scuro): si muove con lui, quindi lo illumina uguale in ogni fotogramma
    faccia = [o for o in obs if o.type == 'MESH' and o.name.startswith(('ManHead', 'ManEye', 'ManTeeth', 'ManDrool', 'ManHair'))]
    col = bpy.data.collections.new('FoxyFacciaLuce')
    for o in faccia:
        col.objects.link(o)
    to_eye = Vector((0.0, -1.0, 0.25)).normalized()       # la creatura guarda −Y
    ld = bpy.data.lights.new('FoxyFaccia', 'AREA')
    ld.energy, ld.color, ld.size = J['luce'], (1.0, 0.62, 0.30), 0.18
    lo = bpy.data.objects.new('FoxyFaccia', ld)
    bpy.context.scene.collection.objects.link(lo)
    # nel sistema della creatura: davanti alla faccia, verso chi guarda e un po' dalla parte della lanterna (che a
    # metà percorso, girata la creatura, è a sinistra della camera)
    lp = face_l + to_eye * 0.40 + Vector((-0.22, 0.0, 0.10))
    lo.location = lp
    lo.rotation_mode = 'QUATERNION'
    lo.rotation_quaternion = (face_l - lp).to_track_quat('-Z', 'Y')
    lo.light_linking.receiver_collection = col
    lo.lightgroup = 'lantern'
    obs.append(lo)
    bpy.context.view_layer.update()
    for o in obs:
        o.matrix_world = M0 @ o.matrix_world

    def dondola(i):
        side, fwd = J['occhio_lato'][i], J['occhio_avanti'][i]
        Rw = Matrix.Translation(top) @ (Matrix.Rotation(math.radians(-fwd), 4, 'X') @ Matrix.Rotation(math.radians(-side), 4, 'Y')) \
            @ Matrix.Translation(-top)
        for o in swing:
            Mw, cos = local[o.name]
            k = Mw.inverted() @ Rw @ Mw
            for v, c in zip(o.data.vertices, cos):
                v.co = k @ c
            o.data.update()
    SPIN['foxy'] = dondola
    return obs, M0, M1, aim


# L'animatore. yaw/parte/z: da dove parte (gradi dall'occhio, metri, quota dei piedi: sotto il capodibanda);
# mira_dist/mira_z: il punto del bordo che guarda la camera; sale/avanza: a metà corsa è salito sul bordo; dist: a quanti
# metri arriva la sua faccia (sulla linea della camera); indietro: gradi di cui si piega all'indietro alla fine (la
# faccia, che nel costume pende in giù, ti guarda); parte_da: al fotogramma 0 è già partito; meta: a che punto della
# corsa è sul bordo; luce: watt della luce sulla faccia; l'occhio dondola di lato (gradi, + in fuori) e un po' avanti
FOXY_JS = {'yaw': 45.0, 'parte': 2.25, 'z': -1.05, 'mira_dist': 2.6, 'mira_z': 0.95,
           'sale': 0.80, 'avanza': 0.20, 'dist': 0.46, 'indietro': -14.0, 'parte_da': 0.06, 'meta': 0.42, 'luce': 6.0,
           'occhio_lato': [25.0, 32.0, 40.0, 46.0, 52.0, 44.0, 30.0, 22.0],
           'occhio_avanti': [0.0, -6.0, -12.0, -8.0, 4.0, 10.0, 6.0, -4.0]}

ATTACKS = {'gulpy': gulpy_attack, 'molly': molly_attack, 'hatch': hatch_attack, 'robin': robin_attack,
           'archie': archie_attack, 'lampy': lampy_attack, 'fangy': fangy_attack, 'foxy': foxy_attack}

# I pezzi che cambiano da un fotogramma all'altro (oltre a muoversi): funzione del numero del fotogramma, preparata
# dall'attacco (i denti di Lampy che girano)
SPIN = {}

# Una luce calda vicino all'occhio, dalla parte della lanterna, che illumina soltanto la creatura (si accende dopo lo
# sfondo): Robin ha la lampara alle spalle e da vicino la sua faccia sarebbe nera; così esce dal buio man mano che
# arriva addosso. energia in watt, dist in metri dall'occhio verso la lanterna
FILL = {'robin': {'energy': 3.0, 'dist': 0.35},
        # Archie arriva nel buio (la lampara è esplosa): lo illuminano la lanterna, la luna alle spalle e questa luce
        'archie': {'energy': 3.0, 'dist': 0.35},
        # Lampy arriva da destra della prua: la lampara le prende il fianco, questa la faccia
        'lampy': {'energy': 3.0, 'dist': 0.35},
        # Fangy arriva da dietro a destra, con la lampara alle spalle del pescatore: la faccia la fanno questa luce e le
        # sue lucine
        'fangy': {'energy': 3.0, 'dist': 0.35},
        # l'animatore sale dall'acqua a prua, con la luce di lato: la sua faccia esce dal buio della bocca del costume
        # (la luce della barca gli sta alle spalle; la faccia la illumina una luce sua, vedi foxy_attack: il costume
        # resta scuro)
        'foxy': {'energy': 4.0, 'dist': 0.45}}


def _fill_light(cfg):
    from props import LANTERN_POS
    eye = Vector(EYE)
    d = (Vector(LANTERN_POS) - eye).normalized()
    ld = bpy.data.lights.new('JumpFill', 'POINT')
    ld.energy = cfg['energy']
    ld.color = (1.0, 0.60, 0.28)
    ld.shadow_soft_size = 0.05
    lo = bpy.data.objects.new('JumpFill', ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = eye + d * cfg['dist']
    lo.lightgroup = 'lantern'
    return lo


# ───────────────────────── render ─────────────────────────

def cam_dir(aim):
    """La direzione della camera del jumpscare verso il punto mirato (non più su di 22°, e un filo più in basso)."""
    d = (aim - Vector(EYE)).normalized()
    hor = math.hypot(d.x, d.y)
    max_up = math.tan(math.radians(22.0)) * hor
    return Vector((d.x, d.y, min(d.z, max_up) - 0.06)).normalized()


# Percorsi su misura (al posto della corsa dritta da M0 a M1 con ease): funzione di u = i/(FRAMES-1) → matrice,
# preparata dall'attacco (l'animatore prima sale sul bordo, poi ti viene addosso)
PATH = {}

def _set_creature(obs, base, M0inv, M):
    for o in obs:
        o.matrix_world = M @ M0inv @ base[o.name]
    bpy.context.view_layer.update()


def run(q, who, post_mod, overlays_path, build_scene, coll_objects, renderable):
    """Rende i fotogrammi di un jumpscare e li scrive in public/assets/img (funzioni di scena da jobs.py)."""
    build_scene(fish=0, rod=False)
    before = set(bpy.data.objects.keys())
    obs, M0, M1, aim = ATTACKS[who]()
    new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
    creature = [o for o in new if o.type in ('MESH', 'LIGHT')]
    meshes = [o for o in creature if o.type == 'MESH']
    base = {o.name: o.matrix_world.copy() for o in creature}
    M0inv = M0.inverted()
    # la camera guarda la creatura, un po' sotto la testa (come quando alzi gli occhi di scatto)
    d = cam_dir(aim)
    cam_target = tuple(Vector(EYE) + d * 2.0)
    perspective_camera(EYE, cam_target, lens=22.0, name='JumpCam')
    # la versione da approvare basta più piccola e con meno campioni (ci sono scosse e grana sopra)
    W, H = (1920, 1080) if q.name == 'final' else (960, 540) if q.name == 'preview' else (640, 360)
    samples = q.samples if q.name == 'final' else min(q.samples, 32)
    # JS_SAMPLES: meno campioni per il finale (ogni fotogramma resta a schermo un decimo di secondo, con la scossa e
    # la grana del nastro sopra; col denoise 64 bastano e il render dura la metà)
    if os.environ.get('JS_SAMPLES'):
        samples = int(os.environ['JS_SAMPLES'])
    out_dir = os.path.join(CACHE, q.name, 'jumpscare')
    os.makedirs(out_dir, exist_ok=True)
    # JS_ANTEPRIMA=1: i fotogrammi restano in cache (da approvare), senza toccare il gioco
    anteprima = bool(os.environ.get('JS_ANTEPRIMA'))
    out_img = os.path.join(out_dir, 'anteprima') if anteprima else OUT_IMG
    os.makedirs(out_img, exist_ok=True)

    # sfondo: tutto tranne la creatura
    for o in meshes:
        o.hide_render = True
    bg_exr = os.path.join(out_dir, f'{who}_bg.exr')
    t = time.time()
    render(bg_exr, samples, (W, H), data_passes=())
    log(f'jumpscare {who} sfondo', round(time.time() - t), 's')
    for o in meshes:
        o.hide_render = False
    if who in FILL:
        _fill_light(FILL[who])

    # la creatura in ogni fotogramma: il resto della scena fa da maschera
    scene_objs = renderable(coll_objects('boat')) + renderable(coll_objects('env'))
    keep = set(o.name for o in meshes)
    for o in scene_objs:
        # (la nebbia dell'atmosfera resta com'è: un volume in holdout bucherebbe la creatura)
        if o.name not in keep and o.visible_camera and o.name != 'Nebbia':
            o.is_holdout = True
    bg = post_mod.read_exr(bg_exr)
    bg_lin = sum(bg[g][..., :3] for g in ('ambient', 'lamp', 'lantern') if g in bg)
    frames = []
    for i in range(FRAMES):
        if who in SPIN:
            SPIN[who](i)
        if who in PATH:
            M = PATH[who](i / (FRAMES - 1))
        else:
            M = _lerp_matrix(M0, M1, ease(i / (FRAMES - 1)))
        _set_creature(creature, base, M0inv, M)
        exr = os.path.join(out_dir, f'{who}_{i:02d}.exr')
        t = time.time()
        render(exr, samples, (W, H), transparent=True, data_passes=('Alpha',))
        p = post_mod.read_exr(exr)
        fg = sum(p[g][..., :3] for g in ('ambient', 'lamp', 'lantern') if g in p)
        a = p['alpha'][..., None] if 'alpha' in p else np.ones(fg.shape[:2] + (1,), np.float32)
        comp = fg + bg_lin * (1 - np.clip(a, 0, 1))
        scale = post_mod.pick_scale(comp)
        fn = f'js_{who}_{i:02d}.webp'
        post_mod.save_webp(post_mod.encode_light_pass(comp, scale), os.path.join(out_img, fn), quality=88)
        frames.append({'file': fn, 'scale': scale})
        log(f'jumpscare {who} fotogramma {i}', round(time.time() - t, 1), 's')
    if anteprima:
        with open(os.path.join(out_img, f'{who}.json'), 'w') as f:
            json.dump({'frames': frames, 'fps': FPS, 'aspect': round(W / H, 4)}, f, indent=1)
        log(f'jumpscare {who}: anteprima in', out_img, '(il gioco non la vede)')
        return
    post_mod.update_manifest(overlays_path, f'jumpscares.{who}', {'frames': frames, 'fps': FPS, 'aspect': round(W / H, 4)})
