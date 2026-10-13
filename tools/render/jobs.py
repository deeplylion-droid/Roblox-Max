"""
Job di render di SPLASHLAND IS CLOSED!.

Uso:
  tools/.venv/bin/python tools/render/jobs.py <job> [<job> ...] [--quality draft|preview|final]

Job:
  world   panorama del mondo (mare, cielo, costa) senza la barca → strato 'world'
  boat    panorama della sola barca con alpha → strato 'boat'
  props   sprite che cambiano: pesci nel secchio, canna piegata
  (i mostri sono in creatures/*.py e si aggiungono qui come job dedicati)

Ogni strato produce in public/assets/img/:
  <layer>_ambient.webp, <layer>_lamp.webp  (passi di luce codificati, vedi post.py)
  world_data.webp                          (R = nebbia/mist, G = maschera acqua, B = cielo)
e una voce in public/assets/img/manifest.json.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import boat  # noqa: E402
import env  # noqa: E402
import landmarks  # noqa: E402
import post  # noqa: E402
import props  # noqa: E402
from common import (CACHE, EYE, LAT_MAX, LAT_MIN, OUT_IMG, QUALITY, IDX_WATER, log, pano_size,  # noqa: E402
                    panorama_camera, render, reset_scene)

MANIFEST = os.path.join(OUT_IMG, 'manifest.json')


# ───────────────────────── scena ─────────────────────────

LIGHT_POINTS = {}


def build_scene(fish=0, rod=False):
    reset_scene()
    info = env.build_environment(with_glow=True)
    LIGHT_POINTS.clear()
    prima = set(bpy.data.objects.keys())
    LIGHT_POINTS.update(landmarks.build_landmarks())
    luoghi = set(bpy.data.objects.keys()) - prima
    LIGHT_POINTS['lighthouse'] = tuple(info['lighthouse'])
    parts, mats = boat.build_boat(fish_in_bucket=fish, rod=rod)
    parts['props'] += props.build_props()
    if os.environ.get('ATMOSFERA'):
        # l'atmosfera dell'11 ottobre (atmosfera.py): la baia più buia e la nebbia volumetrica
        import atmosfera
        atmosfera.applica_buio(luoghi)
        atmosfera.costruisci_nebbia()
    return info, parts, mats


def coll_objects(name):
    c = bpy.data.collections.get(name)
    return list(c.all_objects) if c else []


def renderable(obs):
    return [o for o in obs if o.type in ('MESH', 'CURVE', 'META', 'SURFACE')]


def set_pano_yaw(cam, yaw_deg):
    cam.rotation_mode = 'XYZ'
    cam.rotation_euler = (math.radians(90), 0, -math.radians(yaw_deg))


def world_bbox(obs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in obs:
        oe = o.evaluated_get(dg)
        for c in oe.bound_box:
            pts.append(oe.matrix_world @ Vector(c))
    return np.array([tuple(p) for p in pts])


def pano_rect(points, width, yaw_center, margin=10):
    """Rettangolo in pixel (x0,y0,x1,y1) che contiene i punti, nel panorama ruotato di yaw_center."""
    W, H = pano_size(width)
    us, vs = [], []
    for p in points:
        d = np.array(p) - np.array(EYE)
        lon = math.degrees(math.atan2(d[0], d[1])) - yaw_center
        lon = (lon + 180) % 360 - 180
        lat = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
        us.append((0.5 + lon / 360.0) * W)
        vs.append((LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * H)
    x0 = max(int(min(us)) - margin, 0)
    x1 = min(int(math.ceil(max(us))) + margin, W)
    y0 = max(int(min(vs)) - margin, 0)
    y1 = min(int(math.ceil(max(vs))) + margin, H)
    return x0, y0, x1, y1


def dense_points(obs, n=400):
    """Campiona i vertici valutati (più preciso del bounding box per oggetti lunghi e vicini)."""
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in obs:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        if me is None:
            continue
        step = max(1, len(me.vertices) // n)
        mw = oe.matrix_world
        for i in range(0, len(me.vertices), step):
            pts.append(tuple(mw @ me.vertices[i].co))
        oe.to_mesh_clear()
    return pts


def yaw_of(p):
    d = np.array(p) - np.array(EYE)
    return math.degrees(math.atan2(d[0], d[1]))


# ───────────────────────── codifica ─────────────────────────

def encode_layer(key, exr, space, width, rect=None, yaw_center=0.0, with_alpha=False, data=False, extra=None, quality=90,
                 passes=None, copertura=None):
    """passes: i passi già letti (e magari ritoccati, come l'acqua cotta nella grotta) al posto dell'EXR (che può essere
    anche già letto). copertura: l'alfa vera dello strato (senza la nebbia, vedi job_boat); il colore si riscala sulla
    copertura, così dove lo strato non copre niente non resta la nebbia."""
    p = passes if passes is not None else (post.read_exr(exr) if isinstance(exr, str) else exr)
    if copertura is not None:
        k = np.clip(copertura / np.maximum(p['alpha'], 1e-4), 0.0, 1.0)[..., None]
        for g in ('ambient', 'lamp', 'lantern'):
            if g in p:
                p[g] = p[g] * k
        p['alpha'] = copertura
    if rect is not None:
        # Blender a volte rende una riga in più in fondo alla regione (i conti in float32 sul bordo): si taglia alle
        # misure del riquadro, se no l'immagine non combacia col rect
        h, w = rect[3] - rect[1], rect[2] - rect[0]
        p = {k: (v[:h, :w] if v.ndim >= 2 and v.shape[0] >= h and v.shape[1] >= w else v) for k, v in p.items()}
    W, H = pano_size(width)
    alpha = p.get('alpha') if with_alpha else None
    if 'depth' in p:
        # atmosfera (atmosfera.py): il mist del motore dalla distanza vera, sqrt(d / 2500 m) come nel mist di Blender,
        # e la luce della lampara diffusa lontano dalla nebbia smussata (Cycles la lascia a chiazze)
        import atmosfera
        d = np.where(np.isfinite(p['depth']), p['depth'], 1e9)
        p['mist'] = np.sqrt(np.clip(d / 2500.0, 0.0, 1.0))
        if 'lamp' in p:
            p['lamp'] = p['lamp'].copy()
            p['lamp'][..., :3] = atmosfera.liscia_lontano(p['lamp'][..., :3], np.clip(d / 2500.0, 0.0, 1.0),
                                                          sigma=width / 360.0)
    entry = {'space': space, 'yaw': yaw_center, 'rect': list(rect) if rect else [0, 0, W, H], 'passes': {}}
    total = 0
    for g in ('ambient', 'lamp', 'lantern'):
        if g not in p:
            continue
        lin = p[g][..., :3]
        if float(lin.max()) < 1e-4:
            continue                      # nessun contributo di questa luce nello strato
        a_ = alpha
        res = 1.0
        if g == 'lantern' and rect is None:
            # luce morbida: basta metà risoluzione per gli strati a panorama intero
            lin = lin.reshape(lin.shape[0] // 2, 2, lin.shape[1] // 2, 2, 3).mean(axis=(1, 3)) if lin.shape[0] % 2 == 0 and lin.shape[1] % 2 == 0 else lin[::2, ::2]
            a_ = None if alpha is None else alpha[: lin.shape[0] * 2: 2, : lin.shape[1] * 2: 2]
            res = 0.5
        scale = post.pick_scale(lin / np.maximum(a_[..., None], 1e-4) if a_ is not None else lin, a_)
        img = post.encode_light_pass(lin, scale, a_)
        fn = f'{key}_{g}.webp'
        total += post.save_webp(img, os.path.join(OUT_IMG, fn), quality=quality)
        entry['passes'][g] = {'file': fn, 'scale': scale, 'res': res}
    if data:
        mist = np.clip(p['mist'], 0, 1)
        idx = p['index']
        water = (np.abs(idx - IDX_WATER) < 0.5).astype(np.float32)
        sky = (idx < 0.5).astype(np.float32) * (mist > 0.999)
        rgb8 = np.dstack([mist, water, sky])
        from PIL import Image
        img = Image.fromarray((np.clip(rgb8, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')
        fn = f'{key}_data.webp'
        total += post.save_webp(img, os.path.join(OUT_IMG, fn), lossless=True)
        entry['data'] = fn
    if extra:
        entry.update(extra)
    post.update_manifest(MANIFEST, 'layers.' + key, entry)
    log(f'{key}: {total / 1e6:.2f} MB', entry['rect'])
    return entry


def write_globals(width):
    W, H = pano_size(width)
    post.update_manifest(MANIFEST, 'pano', {'width': W, 'height': H, 'latMin': LAT_MIN, 'latMax': LAT_MAX})
    sx, sy = boat.SCREEN_SIZE
    cx, cy, cz = boat.SCREEN_CENTER
    tilt = math.radians(boat.SCREEN_TILT)
    # angoli dello schermo del sonar (relativi all'occhio, x destra y avanti z alto)
    def rel(p):
        return [round(p[0] - EYE[0], 4), round(p[1] - EYE[1], 4), round(p[2] - EYE[2], 4)]
    up = np.array((0, -math.sin(tilt), math.cos(tilt))) * sy / 2
    right = np.array((-sx / 2, 0, 0))   # lo schermo guarda +Y: la destra del giocatore voltato è -X
    normal = np.array((0, math.cos(tilt), math.sin(tilt)))
    c = np.array((cx, cy, cz)) + normal * 0.0025
    corners = [c - right + up, c + right + up, c + right - up, c - right - up]
    post.update_manifest(MANIFEST, 'points', {
        'eye': list(EYE),
        'lamp': rel(boat.LAMP_POS),
        'rodTip': rel(boat.ROD_TIP),
        'bucket': rel(boat.BUCKET_POS),
        'tarp': rel(boat.TARP_POS),
        'sonarScreen': [rel(p) for p in corners],
        'sonarRound': False,
        'lighthouseYaw': env.LIGHTHOUSE_YAW,
        'moonYaw': env.MOON_YAW, 'moonElev': env.MOON_ELEV,
    })
    # luci animate dal motore (lampeggi, sfarfallii): direzioni dall'occhio
    if LIGHT_POINTS:
        post.update_manifest(MANIFEST, 'lights', {k: rel(v) for k, v in LIGHT_POINTS.items()})


# ───────────────────────── job ─────────────────────────

def campioni(q):
    """I campioni del job: quelli della qualità, o CAMPIONI=n; SOGLIA=x cambia la soglia del campionamento adattivo
    (più bassa: i pixel rumorosi, come l'acqua nella nebbia, prendono più campioni, il cielo si ferma prima)."""
    if os.environ.get('SOGLIA'):
        bpy.context.scene.cycles.adaptive_threshold = float(os.environ['SOGLIA'])
    return int(os.environ.get('CAMPIONI', q.samples))


def render_a_strisce(exr, samples, size, **kw):
    """Come render(), ma a strisce verticali (STRISCE=n, predefinito 1: tutto in una volta). Ogni striscia si
    salva appena finita e si salta se c'è già: un render di molte ore riparte da dove era arrivato se la macchina
    si ferma. Le strisce si rendono con un margine (il denoiser vuole il contesto ai bordi) e si cuciono tagliandolo.
    Restituisce i passi dell'immagine intera, come post.read_exr."""
    n = int(os.environ.get('STRISCE', '1'))
    W, H = size
    if n <= 1:
        render(exr, samples, size, **kw)
        return post.read_exr(exr)
    M = 48
    full = {}
    for i in range(n):
        a, b = i * W // n, (i + 1) * W // n
        x0, x1 = max(a - M, 0), min(b + M, W)
        part = exr.replace('.exr', f'_s{i}.exr')
        if os.path.exists(part):
            log(f'striscia {i + 1}/{n} già fatta')
            pezzi = [(a, b, x0, x1, part)]
        else:
            # le strisce ancora da fare si rendono in due metà, salvate ognuna: se la macchina si ferma si perde
            # al più mezza striscia
            m = (a + b) // 2
            pezzi = []
            for j, (pa, pb) in enumerate(((a, m), (m, b))):
                px0, px1 = max(pa - M, 0), min(pb + M, W)
                pp = exr.replace('.exr', f'_s{i}{"ab"[j]}.exr')
                if os.path.exists(pp):
                    log(f'striscia {i + 1}/{n}, metà {j + 1}: già fatta')
                else:
                    t = time.time()
                    render(pp, samples, size, region=(px0, 0, px1, H), **kw)
                    log(f'striscia {i + 1}/{n}, metà {j + 1} in', round(time.time() - t), 's')
                pezzi.append((pa, pb, px0, px1, pp))
        for pa, pb, px0, px1, path in pezzi:
            p = post.read_exr(path)
            for k, v in p.items():
                v = v[:H, :px1 - px0]
                if k not in full:
                    full[k] = np.zeros((H, W) + v.shape[2:], np.float32)
                full[k][:, pa:pb] = v[:, pa - px0:pb - px0]
    return full


def job_world(q):
    build_scene(fish=0, rod=False)
    for o in coll_objects('boat'):
        o.visible_camera = False
    cam = panorama_camera()
    W, H = pano_size(q.pano_width)
    exr = os.path.join(CACHE, q.name, 'world.exr')
    t = time.time()
    passes = ('Mist', 'Object Index')
    if os.environ.get('ATMOSFERA'):
        # con la nebbia il mist di Cycles si accumula nei volumi: le distanze vere vengono dal passo Depth
        bpy.context.scene.view_layers[0].use_pass_z = True
        passes += ('Depth',)
    p = render_a_strisce(exr, campioni(q), (W, H), data_passes=passes)
    log('world render', round(time.time() - t), 's')
    encode_layer('world', p, 'world', q.pano_width, data=True)
    write_globals(q.pano_width)


def job_boat(q):
    build_scene(fish=0, rod=False)
    atmo = bool(os.environ.get('ATMOSFERA'))
    for o in coll_objects('env'):
        if atmo and o.name == 'Nebbia':
            # solo la nebbia attorno alla barca: quella oltre (davanti al mare e al cielo) è già nello strato del
            # mondo. La densità dipende dalla posizione nel mondo, quindi stringere la scatola non la cambia
            d = o.dimensions
            o.scale = (3.4 / d.x, 7.0 / d.y, 3.4 / d.z)
            o.location = (0.0, 0.0, 1.2)
            continue
        if atmo and o.type == 'MESH':
            # con la nebbia: il mondo fa da maschera (la nebbia fra l'occhio e la barca resta nello strato)
            o.is_holdout = True
        else:
            o.visible_camera = False
    panorama_camera()
    W, H = pano_size(q.pano_width)
    exr = os.path.join(CACHE, q.name, 'boat.exr')
    t = time.time()
    p = render_a_strisce(exr, campioni(q), (W, H), transparent=True, data_passes=('Alpha',))
    log('boat render', round(time.time() - t), 's')
    copertura = None
    if atmo:
        # Cycles mette la nebbia anche nell'alfa (sul mare lo strato sarebbe velato di nebbia, che il mondo ha già):
        # l'alfa vera è la copertura della sola barca, da un render rapido senza la nebbia
        neb = bpy.data.objects['Nebbia']
        neb.hide_render = True
        mask = os.path.join(CACHE, q.name, 'boat_copertura.exr')
        if not os.path.exists(mask):
            render(mask, 4, (W, H), transparent=True, groups=('ambient',), data_passes=('Alpha',), denoise=False)
        neb.hide_render = False
        copertura = post.read_exr(mask)['alpha']
    encode_layer('boat', p, 'boat', q.pano_width, with_alpha=True, copertura=copertura)
    write_globals(q.pano_width)


def yaw_center(pts):
    """Il centro (yaw, gradi) di uno strato: la media circolare degli yaw dei punti (dietro la poppa gli angoli
    scavalcano ±180°)."""
    ys = np.radians([yaw_of(p) for p in pts])
    return float(np.degrees(np.arctan2(np.mean(np.sin(ys)), np.mean(np.cos(ys)))))


def render_sprite(q, key, objs, space='boat', margin=12, holdout_boat=True, samples=None, extra=None, sea=False,
                  holdout=(), rect_objs=None, yaw=None):
    """Rende visibili alla camera solo objs; la barca fa da maschera (holdout) se richiesto.
    sea=True: anche il mare fa da maschera (creature immerse, pure negli strati legati alla barca).
    holdout: altri oggetti che fanno da maschera come la barca: non si vedono ma coprono quello che sta dietro
    (e restano nelle ombre e nei riflessi). Servono alle toppe: lo strato con un pezzo solo della creatura.
    rect_objs: gli oggetti su cui si calcola il riquadro dello strato (predefinito objs).
    yaw: il centro dello strato in gradi (predefinito: la media degli yaw dei punti del riquadro); una toppa usa
    quello dello strato su cui va, così i pixel dei due strati coincidono uno a uno."""
    boat_objs = renderable(coll_objects('boat'))
    env_objs = renderable(coll_objects('env'))
    keep = set(o.name for o in objs)
    masks = [o for o in holdout if o.name not in keep]
    saved = {o.name: (o.visible_camera, o.is_holdout) for o in boat_objs + env_objs + masks}
    for o in env_objs:
        o.visible_camera = False
    for o in boat_objs:
        if o.name in keep:
            continue
        if holdout_boat and o.visible_camera:
            o.is_holdout = True
        else:
            o.visible_camera = False
    for o in masks:
        o.visible_camera = True
        o.is_holdout = True
    if space == 'world' or sea:
        sea_ob = bpy.data.objects.get('Sea')
        if sea_ob:
            sea_ob.visible_camera = True
            sea_ob.is_holdout = True
    pts = dense_points(objs if rect_objs is None else rect_objs)
    yc = yaw_center(pts) if yaw is None else float(yaw)
    cam = bpy.context.scene.camera
    set_pano_yaw(cam, yc)
    rect = pano_rect(pts, q.pano_width, yc, margin)
    W, H = pano_size(q.pano_width)
    exr = os.path.join(CACHE, q.name, f'{key}.exr')
    t = time.time()
    render(exr, samples or q.samples, (W, H), region=rect, transparent=True, data_passes=('Alpha',))
    log(f'sprite {key} render', round(time.time() - t, 1), 's', rect)
    set_pano_yaw(cam, 0.0)
    for o in boat_objs + env_objs + masks:
        if o.name in saved:
            o.visible_camera, o.is_holdout = saved[o.name]
    return encode_layer(key, exr, space, q.pano_width, rect=rect, yaw_center=round(yc, 4), with_alpha=True, extra=extra)


def pelo_dell_acqua(objs, yaw_c, rect, width, n=32):
    """Dove il mare taglia una creatura, visto dall'occhio: per n colonne equidistanti sul riquadro dello strato (la
    prima sul bordo sinistro, l'ultima sul destro) la riga del panorama (ruotato di yaw_c) in cui il pelo
    dell'acqua la taglia; dove la taglia più volte, la più in basso (la parte più vicina, quella che si vede). Le
    colonne dove non tocca l'acqua (fra le braccia, sotto la testa sporgente) si interpolano fra le vicine, oltre i
    capi resta l'ultima. Il gioco la usa quando la creatura emerge e si rituffa: lo strato scende tutto insieme, e
    sotto questa linea non si disegna (se no scivolerebbe davanti all'acqua più vicina). None se non tocca il mare.
    Il mare è quello vero della scena, con le onde e la calma vicino alla barca."""
    from mathutils.bvhtree import BVHTree
    sea = bpy.data.objects.get('Sea')
    if sea is None or not objs:
        return None
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(sea, dg)
    inv = sea.matrix_world.inverted()
    down = (inv.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()

    def water_z(x, y):
        hit = tree.ray_cast(inv @ Vector((x, y, 50.0)), down)
        return (sea.matrix_world @ hit[0]).z if hit[0] is not None else 0.0

    W, H = pano_size(width)
    us, vs = [], []
    for o in objs:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        if me is None:
            continue
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get('co', co)
        ev = np.empty(len(me.edges) * 2, dtype=np.int64)
        me.edges.foreach_get('vertices', ev)
        M = np.array(oe.matrix_world)
        oe.to_mesh_clear()
        P = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        ev = ev.reshape(-1, 2)
        # quanto sta sopra il mare ogni vertice: lontano dall'acqua basta il segno (le onde sono di pochi centimetri)
        f = np.where(P[:, 2] > 0, 1.0, -1.0)
        for i in np.nonzero(np.abs(P[:, 2]) < 0.6)[0]:
            f[i] = P[i, 2] - water_z(P[i, 0], P[i, 1])
        a, b = f[ev[:, 0]], f[ev[:, 1]]
        cross = a * b < 0
        if not cross.any():
            continue
        t = (a[cross] / (a[cross] - b[cross]))[:, None]
        X = P[ev[cross, 0]] + (P[ev[cross, 1]] - P[ev[cross, 0]]) * t
        d = X - np.array(EYE)
        lon = (np.degrees(np.arctan2(d[:, 0], d[:, 1])) - yaw_c + 180) % 360 - 180
        lat = np.degrees(np.arctan2(d[:, 2], np.hypot(d[:, 0], d[:, 1])))
        us.append((0.5 + lon / 360.0) * W)
        vs.append((LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * H)
    if not us:
        return None
    u, v = np.concatenate(us), np.concatenate(vs)
    x0, x1 = rect[0], rect[2]
    xs = x0 + (x1 - x0) * np.arange(n) / (n - 1)
    half = (x1 - x0) / (n - 1) / 2
    rows = np.full(n, np.nan)
    for i, x in enumerate(xs):
        m = np.abs(u - x) <= half
        if m.any():
            rows[i] = v[m].max()
    ok = ~np.isnan(rows)
    if not ok.any():
        return None
    return [round(float(r), 1) for r in np.interp(xs, xs[ok], rows[ok])]


def job_props(q):
    """Oggetti di scena come strati. Variabile d'ambiente PROPS=fish,rod,battery per renderne solo alcuni."""
    only = [k for k in os.environ.get('PROPS', '').split(',') if k]
    info, parts, mats = build_scene(fish=0, rod=False)
    panorama_camera()
    # pesci nel secchio
    if not only or 'fish' in only:
        for n in (2, 5, 9):
            fish = boat.build_bucket(mats, n, name=f'Fish{n}', with_body=False)
            render_sprite(q, f'fish{n}', fish)
            for o in fish:
                o.hide_render = True
    # canna: riposo, abboccata, recupero
    if not only or 'rod' in only:
        for bend, key in ((0.0, 'rod0'), (1.0, 'rod1'), (2.0, 'rod2')):
            obs, tip = boat.build_rod(mats, bend=bend, name=key)
            render_sprite(q, key, obs, extra={'tip': [round(float(tip[i] - EYE[i]), 4) for i in range(3)]})
            for o in obs:
                o.hide_render = True
    # la canna che il gioco piega in continuo: qui solo quello che non si muove (impugnatura, mulinello, il fusto
    # fino al portacanna). PROPS=rodbase
    if 'rodbase' in only:
        obs, gun = boat.build_rod(mats, name='rod_base', solo_base=True)
        render_sprite(q, 'rod_base', obs)
        for o in obs:
            o.hide_render = True
    # la canna nel lancio: si alza e si carica, poi la frustata in avanti (il gioco le sfoglia; vedi rodKey in
    # src/app/night.ts). PROPS=lancio
    if 'lancio' in only:
        for tilt, flex, key in ((7.0, 0.35, 'rod_c1'), (14.0, 0.8, 'rod_c2'), (5.0, 0.7, 'rod_m'),
                                (-3.0, -0.55, 'rod_f1'), (-6.0, -1.1, 'rod_f2')):
            obs, tip = boat.build_rod(mats, name=key, tilt=tilt, flex=flex)
            render_sprite(q, key, obs, extra={'tip': [round(float(tip[i] - EYE[i]), 4) for i in range(3)]})
            for o in obs:
                o.hide_render = True
    # la batteria della lampara (dalla notte 2): il quadrante senza ago, l'ago lo disegna il gioco. Due
    # strati uguali: col quadrante spento e acceso (retroilluminato); il gioco li dissolve (a batteria
    # morta la luce del voltmetro si spegne, quando è quasi scarica trema con la lampara)
    if not only or 'battery' in only:
        import batteria
        obs = batteria.build_battery(needle=None, glow=0.0)
        c, n, right, up = batteria.battery_frame()
        face = c + n * 0.0025 - np.array(EYE)
        r = batteria.GAUGE_R
        gauge = [[round(float(v[i]), 4) for i in range(3)] for v in (face, right * r, up * r)]
        render_sprite(q, 'battery', obs, extra={'gauge': gauge})
        batteria.set_glow(batteria.GLOW_STRENGTH)
        render_sprite(q, 'battery_lit', obs)
        for o in obs:
            o.hide_render = True


def nome_base(name):
    """Il nome di un oggetto senza il suffisso .001 che Blender aggiunge ai doppioni (quando una creatura si
    costruisce più volte nella stessa scena, come le toppe dopo la posa principale)."""
    head, dot, tail = name.rpartition('.')
    return head if dot and tail.isdigit() else name


def scegli(objs, nomi):
    """Gli oggetti il cui nome corrisponde a uno dei modelli in 'nomi' (fnmatch: 'RobinEye*', 'Fin?'); il
    suffisso .001 dei doppioni non conta. 'nomi' può anche essere una funzione nome → bool."""
    import fnmatch
    if callable(nomi):
        return [o for o in objs if nomi(nome_base(o.name))]
    return [o for o in objs if any(fnmatch.fnmatchcase(nome_base(o.name), n) for n in nomi)]


def yaw_dello_strato(key, fatti):
    """Il centro (yaw) dello strato 'key': reso in questo giro (fatti) o già nel manifest; None se non c'è."""
    if key in fatti:
        return fatti[key]
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            e = json.load(f).get('layers', {}).get(key)
        if e:
            return e['yaw']
    return None


def job_creature(q):
    """Le creature nelle pose di gioco, come strati del panorama (vedi scena_creature.py).
    Variabile d'ambiente POSES=chiave1,chiave2 per renderne solo alcune.

    Le voci di scena_creature.POSES sono chiave → (funzione, spazio, mare) oppure (funzione, spazio, mare, opzioni):
      funzione  costruisce la posa nella scena; gli oggetti nuovi che crea sono la creatura
      spazio    'boat' (lo strato si muove con la barca) o 'world' (sta nel mondo, col mare)
      mare      True: anche il mare fa da maschera (la parte sott'acqua non si vede)
      opzioni   un dizionario, facoltativo; serve soprattutto alle pose «a toppa»: uno strato con un pezzo solo
                della creatura (la testa con gli occhi strizzati, un battito di ciglia), nella stessa posa dello
                strato principale, che il gioco dissolve sopra di esso. Le chiavi:
        'visibili'  i nomi degli oggetti della creatura che restano visibili: modelli fnmatch ('RobinEye*'), il
                    suffisso .001 dei doppioni non conta (o una funzione nome → bool). Gli altri oggetti della
                    creatura fanno da maschera come la barca: non si vedono ma coprono quello che sta dietro (un
                    braccio davanti alla faccia la copre come nello strato principale) e restano nelle ombre e nei
                    riflessi. Il riquadro dello strato si calcola solo sui visibili. Senza: tutti visibili.
        'occhi'     se registrare gli occhi nel manifest (predefinito True; tra i visibili, gli oggetti che hanno
                    'Eye' nel nome). Una toppa che mostra gli stessi occhi dello strato principale mette False,
                    se no il gioco li fa brillare due volte al buio.
        'riquadro'  (facoltativo, con 'visibili') i nomi degli oggetti su cui si calcola il riquadro dello strato,
                    se deve essere più stretto dei visibili: una mascella che si sposta scopre il corpo dietro la
                    testa, che nella toppa va visibile ma non deve allargarla (vedi pose_animate.py).
        'luci'      (facoltativo) un modello fnmatch degli oggetti «lucina» della creatura (le lucine di Fangy,
                    'FangyLight*'): nel manifest vanno le loro posizioni dall'occhio, in 'luci': {'p': [[x, y, z]…],
                    'fila': […]} (il centro di ogni lucina, dalla sua proprietà 'centro' se c'è, e la sua 'fila'), così il
                    motore le accende e le fa pulsare da solo, come gli occhi.
        'yaw_di'    la chiave dello strato principale, su cui va la toppa. La toppa usa il suo stesso centro
                    (yaw), così i pixel dei due strati coincidono uno a uno: lo yaw si prende dallo strato reso
                    prima nello stesso giro o, se no, dal manifest (che deve venire dallo stesso render: la stessa
                    RENDER_OUT); se non c'è si calcola sulla creatura intera, visibili e maschere (quasi lo stesso
                    centro), e lo dice il log. Nel manifest la toppa porta 'base': la chiave dello strato principale
                    (il gioco deve muoverla come lui: per esempio la discesa dietro il bordo, che dipende
                    dall'altezza del riquadro, va presa dallo strato base). Senza: il centro si calcola sui visibili.
    Esempio (scena_creature.py: ROBIN_TESTA, ROBIN_TOPPA), una toppa con la sola testa:
        'robin_strizza': (lambda: robin_secchio(palpebre=0.75, aggrotta=1.0), 'boat', True,
                          {'visibili': ('RobinHead', 'RobinEye*', 'RobinLid*', ...), 'occhi': False,
                           'yaw_di': 'robin_secchio'}),
    e si rende come le altre: POSES=robin_strizza,robin_chiusi jobs.py creature --quality final (con la stessa
    RENDER_OUT dello strato principale, o insieme a lui). La funzione della toppa deve rifare la creatura
    identica a quella principale fuori dal pezzo che cambia (stessa posa, stessi parametri, e a 0 il modello
    non deve aggiungere né spostare niente), se no le maschere non combaciano."""
    import scena_creature
    import pose_animate
    build_scene(fish=0, rod=False)
    panorama_camera()
    only = [k for k in os.environ.get('POSES', '').split(',') if k]
    fatti = {}
    # le pose di gioco e le toppe delle animazioni (le mascelle, gli occhi di Gulpy, Molly e Hatch)
    poses = {**scena_creature.POSES, **pose_animate.TOPPE}
    if only:
        # nell'ordine di POSES=...: una creatura alla volta, base e toppe, così è pronta appena finisce
        poses = {k: poses[k] for k in only}
    for key, voce in poses.items():
        fn, space, sea = voce[:3]
        opts = voce[3] if len(voce) > 3 else {}
        before = set(bpy.data.objects.keys())
        fn()
        new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
        bpy.context.view_layer.update()
        meshes = [o for o in new if o.type == 'MESH']
        vis, masks = meshes, []
        if opts.get('visibili'):
            vis = scegli(meshes, opts['visibili'])
            masks = [o for o in meshes if o not in vis]
            if not vis:
                raise RuntimeError(f'{key}: nessun oggetto visibile tra {sorted(o.name for o in meshes)}')
            log(f'{key}: visibili', sorted(o.name for o in vis), '· maschera', len(masks), 'oggetti')
        extra = {}
        if opts.get('occhi', True):
            # dove sono gli occhi (dall'occhio del pescatore): a lampara spenta si vedono solo loro
            eyes = [[round(float(o.matrix_world.translation[i] - EYE[i]), 4) for i in range(3)]
                    for o in vis if 'Eye' in o.name and not o.name.startswith(('Toy', 'Duck'))]
            extra['eyes'] = eyes
        if opts.get('luci'):
            from mathutils import Vector
            luci = sorted(scegli(vis, (opts['luci'],)), key=lambda o: o.name)
            pos = [o.matrix_world @ (Vector(tuple(o['centro'])) if 'centro' in o.keys() else Vector((0, 0, 0)))
                   for o in luci]
            extra['luci'] = {'p': [[round(float(c[i] - EYE[i]), 4) for i in range(3)] for c in pos],
                             'fila': [str(o.get('fila', '')) for o in luci]}
            log(f'{key}: {len(luci)} lucine nel manifest')
        yaw = None
        base = opts.get('yaw_di')
        if base:
            extra['base'] = base
            yaw = yaw_dello_strato(base, fatti)
            if yaw is None:
                yaw = yaw_center(dense_points(meshes))
                log(f'{key}: lo strato {base} non c\'è, centro dalla creatura intera', round(yaw, 4))
        rect_objs = scegli(vis, opts['riquadro']) if opts.get('riquadro') else None
        # CAMPIONI=n per le anteprime veloci (i finali restano coi campioni della qualità)
        entry = render_sprite(q, key, vis, space=space, sea=sea, extra=extra or None, holdout=masks, yaw=yaw,
                              rect_objs=rect_objs, samples=campioni(q))
        fatti[key] = entry['yaw']
        if not base:
            # dove il mare la taglia (le toppe usano quella dello strato su cui vanno)
            pelo = pelo_dell_acqua(vis, entry['yaw'], entry['rect'], q.pano_width)
            if pelo:
                post.update_manifest(MANIFEST, f'layers.{key}.pelo', pelo)
        for o in new:
            o.hide_render = True
        bpy.context.view_layer.update()



def job_pelo(q):
    """Solo la linea del pelo dell'acqua (pelo_dell_acqua) delle creature già rese, senza rendere niente: rifà le
    pose di scena_creature.POSES (o quelle in POSES=...) e la scrive nelle loro voci del manifest, con lo yaw e il
    riquadro che hanno già. Le toppe la prendono dallo strato su cui vanno."""
    import scena_creature
    build_scene(fish=0, rod=False)
    only = [k for k in os.environ.get('POSES', '').split(',') if k]
    with open(MANIFEST) as f:
        man = json.load(f)
    width = man['pano']['width']
    for key, voce in scena_creature.POSES.items():
        opts = voce[3] if len(voce) > 3 else {}
        if (only and key not in only) or opts.get('yaw_di'):
            continue
        e = man['layers'].get(key)
        if not e:
            log(f'{key}: non è nel manifest')
            continue
        before = set(bpy.data.objects.keys())
        voce[0]()
        new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
        bpy.context.view_layer.update()
        meshes = [o for o in new if o.type == 'MESH']
        vis = scegli(meshes, opts['visibili']) if opts.get('visibili') else meshes
        pelo = pelo_dell_acqua(vis, e['yaw'], e['rect'], width)
        if pelo:
            post.update_manifest(MANIFEST, f'layers.{key}.pelo', pelo)
            log(f'{key}: pelo dell\'acqua dalla riga {min(pelo)} alla {max(pelo)} (riquadro {e["rect"]})')
        else:
            # una posa che non tocca più il mare non deve tenersi la linea vecchia
            if 'pelo' in e:
                post.update_manifest(MANIFEST, f'layers.{key}', {k: v for k, v in e.items() if k != 'pelo'})
            log(f'{key}: non tocca il mare')
        for o in new:
            o.hide_render = True

OVERLAYS = os.path.join(OUT_IMG, 'overlays.json')


def encode_overlay(key, exr, groups):
    """Immagine a tutto schermo (non panorama): ogni passo di luce in un webp, come gli strati."""
    p = post.read_exr(exr)
    entry = {}
    for g, name in groups.items():
        lin = p[g][..., :3]
        scale = post.pick_scale(lin)
        fn = f'{key}_{name}.webp'
        post.save_webp(post.encode_light_pass(lin, scale), os.path.join(OUT_IMG, fn), quality=90)
        entry[name] = {'file': fn, 'scale': scale}
    return entry


def job_tarp(q):
    """La vista da sotto il telone (vedi telone.py): passo base e passo della luce del giocattolo."""
    import telone
    from common import perspective_camera
    build_scene(fish=0, rod=False)
    # il telone è sopra il pescatore; gli oggetti sul banco di prua finirebbero dentro la tela
    for o in bpy.data.objects:
        if o.name in ('Tarp', 'TarpRope') or o.name.startswith(('Doll', 'Flask', 'Tally', 'Bucket')):
            o.hide_render = True
    # tutta la luce di fuori nel passo base; il passo 'lamp' resta per il giocattolo
    for o in bpy.data.objects:
        if o.lightgroup in ('lamp', 'lantern'):
            o.lightgroup = 'ambient'
    telone.simulate_drape()
    telone.toy_backlight()
    perspective_camera(telone.EYE_HIDDEN, telone.LOOK_AT, lens=22.0)
    W, H = (1920, 1080) if q.name == 'final' else (1280, 720) if q.name == 'preview' else (854, 480)
    exr = os.path.join(CACHE, q.name, 'tarp.exr')
    t = time.time()
    render(exr, q.samples, (W, H), data_passes=())
    log('tarp render', round(time.time() - t), 's')
    entry = encode_overlay('tarp', exr, {'ambient': 'base', 'lamp': 'glow'})
    entry['aspect'] = round(W / H, 4)
    post.update_manifest(OVERLAYS, 'tarp', entry)
    log('tarp', entry)


def job_jumpscare(q):
    """I jumpscare delle creature (vedi jumpscare.py). JUMPSCARES=gulpy,molly,hatch,robin per sceglierli."""
    import jumpscare
    who = [k for k in os.environ.get('JUMPSCARES', 'gulpy,molly,hatch,robin').split(',') if k]
    for w in who:
        jumpscare.run(q, w, post, OVERLAYS, build_scene, coll_objects, renderable)


def job_binocolo(q):
    """I luoghi dell'orizzonte per il binocolo (vedi binocolo.py). LUOGHI=ingresso,statua,... per sceglierli."""
    import binocolo
    binocolo.run(q, post, OVERLAYS, build_scene, coll_objects)


def job_reencode(q):
    """Ricodifica tutti gli strati del manifest dagli EXR in cache (senza rifare i render)."""
    with open(MANIFEST) as f:
        man = json.load(f)
    width = man['pano']['width']
    for key, e in man.get('layers', {}).items():
        exr = os.path.join(CACHE, q.name, f'{key}.exr')
        if not os.path.exists(exr):
            log('manca', exr)
            continue
        extra = {k: v for k, v in e.items() if k not in ('space', 'yaw', 'rect', 'passes', 'data')}
        encode_layer(key, exr, e['space'], width, rect=e['rect'], yaw_center=e['yaw'],
                     with_alpha=key != 'world', data=key == 'world', extra=extra or None)


def preview_composite(out_png, yaw=0.0, pitch=-12.0, lamp=1.0, ambient=1.0, extra_layers=(), exposure=0.5, size=(960, 540)):
    """Ricompone gli strati come il motore (per controllo): mondo + barca + sprite."""
    with open(MANIFEST) as f:
        man = json.load(f)
    W, H = man['pano']['width'], man['pano']['height']

    def load(key):
        e = man['layers'][key]
        acc, alpha = None, None
        for g, w in (('ambient', ambient), ('lamp', lamp)):
            pe = e['passes'].get(g)
            if not pe:
                continue
            c, a = post.decode_light_pass(os.path.join(OUT_IMG, pe['file']), pe['scale'])
            acc = c * w if acc is None else acc + c * w
            alpha = a if a is not None else alpha
        return e, acc, alpha

    def to_full(e, img, alpha):
        full = np.zeros((H, W, 3), np.float32)
        fa = np.zeros((H, W), np.float32)
        x0, y0, x1, y1 = e['rect']
        full[y0:y1, x0:x1] = img
        fa[y0:y1, x0:x1] = alpha if alpha is not None else 1.0
        shift = int(round(e['yaw'] / 360.0 * W))
        return np.roll(full, shift, axis=1), np.roll(fa, shift, axis=1)

    e, world, _ = load('world')
    comp = world.copy()
    for key in ('boat',) + tuple(extra_layers):
        e, img, a = load(key)
        img, a = to_full(e, img, a)
        comp = comp * (1 - a[..., None]) + img * a[..., None]
    view = post.pano_to_view(comp, yaw, pitch, 90, size, man['pano']['latMin'], man['pano']['latMax'])
    post.save_png(post.tonemap(view, exposure), out_png)


def job_bordo(q):
    """Il bordo della barca visto dall'occhio: per ogni direzione (yaw da −180° a 179,5°, passo 0,5°) l'altezza
    angolare del capodibanda, nello spazio della barca. Il gioco ci taglia le creature che scendono dietro il
    bordo quando se ne vanno (manifest points.sheer, gradi)."""
    import scena_creature as sc
    pts = []
    for side in (-1, 1):
        for t in np.linspace(-0.985, 0.985, 3000):
            x, ztop = sc.gunwale_at(float(t) * boat.HALF, side)
            pts.append((x + side * 0.02, float(t) * boat.HALF, ztop))
    # lo specchio di poppa, da un fianco all'altro
    t = -0.985
    xl, zl = sc.gunwale_at(t * boat.HALF, -1)
    xr, zr = sc.gunwale_at(t * boat.HALF, 1)
    for u in np.linspace(0.0, 1.0, 600):
        pts.append((xl + (xr - xl) * u, t * boat.HALF - 0.02, zl + (zr - zl) * u))
    P = np.array(pts) - np.array(EYE)
    yaw = np.degrees(np.arctan2(P[:, 0], P[:, 1]))
    el = np.degrees(np.arctan2(P[:, 2], np.hypot(P[:, 0], P[:, 1])))
    out = []
    for b in np.arange(-180.0, 180.0, 0.5):
        d = np.abs((yaw - b + 180.0) % 360.0 - 180.0)
        near = d < 0.3
        out.append(float(el[near].max()) if near.any() else float(el[np.argmin(d)]))
    post.update_manifest(MANIFEST, 'points.sheer', [round(e, 3) for e in out])
    log('bordo: %d direzioni, da %.1f° a %.1f°' % (len(out), min(out), max(out)))


# ───────────────────────── la grotta grande delle immersioni (look-dev, da approvare) ─────────────────────────

CONCEPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs', 'concept')


def grotte_vista(q, nome, pos, target, lens, size, torcia=False, pesi=None, esposizione=0.0, samples=None, cono=42.0,
                 acqua=None):
    """Un'anteprima prospettica della grotta (la scena deve essere già costruita): render, acqua cotta, tone mapping
    del gioco → docs/concept/<nome>.jpg."""
    import grotte
    from common import perspective_camera
    from PIL import Image
    cam = perspective_camera(pos, target, lens=lens, name='Cam_' + nome)
    luce = grotte.torcia_faretto(cam, target, cone=cono) if torcia else None
    exr = os.path.join(CACHE, q.name, f'{nome}.exr')
    t = time.time()
    p = grotte.render_con_raggi(exr, samples or q.samples, size)
    log(nome, 'render', round(time.time() - t), 's')
    # i parametri della composizione accanto all'EXR: si può ricomporre senza rendere (job grotte_ricomponi)
    par = dict(nome=nome, lens=lens, size=list(size), torcia=torcia, pesi=pesi, esposizione=esposizione, cono=cono,
               acqua=acqua or {})
    with open(exr.replace('.exr', '.json'), 'w') as f:
        json.dump(par, f)
    out = grotte_componi(exr, par, p)
    if luce is not None:
        bpy.data.objects.remove(luce)
    log('anteprima', out)
    return out


def grotte_componi(exr, par, p=None):
    """Dall'EXR (e da quello dei raggi) all'anteprima: acqua cotta, tone mapping del gioco → docs/concept/<nome>.jpg."""
    import grotte
    from PIL import Image
    if p is None:
        p = post.read_exr(exr)
        r = exr.replace('.exr', '_raggi.exr')
        if os.path.exists(r):
            p['raggi'] = post.read_exr(r)['ambient']
    # la scia della torcia solo nel suo cono (il faretto è quasi sulla camera)
    W, H = par['size']
    lens, cono = par['lens'], par['cono']
    tx = 18.0 / lens
    xs = (np.arange(W) + 0.5) / W * 2 - 1
    ys = ((np.arange(H) + 0.5) / H * 2 - 1) * H / W
    X, Y = np.meshgrid(xs * tx, ys * tx)
    ang = np.degrees(np.arctan(np.hypot(X, Y)))
    cone = np.clip((cono / 2 - ang) / (cono * 0.25), 0, 1).astype(np.float32)
    baked = grotte.acqua(p, blur_px=W / 10, cone_mask=cone, **par.get('acqua', {}))
    pesi = par.get('pesi') or {'ambient': 1.0, 'lantern': 1.0 if par['torcia'] else 0.0}
    lin = post.compose(baked, pesi)
    img = post.tonemap(lin, par['esposizione'] + GROTTE_ESPOSIZIONE)
    os.makedirs(CONCEPT, exist_ok=True)
    out = os.path.join(CONCEPT, par['nome'] + '.jpg')
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(out, quality=90)
    return out


GROTTE_ESPOSIZIONE = float(os.environ.get('GROTTE_ESPOSIZIONE', '0'))   # correzione per le prove di ricomposizione


def job_grotte_ricomponi(q):
    """Ricompone le anteprime della grotta dagli EXR in cache (dopo aver cambiato l'acqua o l'esposizione)."""
    import glob
    for js in sorted(glob.glob(os.path.join(CACHE, q.name, 'grotte_*.json'))):
        with open(js) as f:
            par = json.load(f)
        log('ricomposta', grotte_componi(js.replace('.json', '.exr'), par))
    import grotte
    tiles = [(chi, os.path.join(CONCEPT, f'grotte_tana_{chi}.jpg')) for chi, *_ in grotte.TANE]
    if all(os.path.exists(t) for _, t in tiles):
        from PIL import Image
        tavola_tane(tiles, Image.open(tiles[0][1]).size)


def _grotte_scena(neve=True):
    import grotte
    reset_scene()
    return grotte.build_grotta(neve=neve)


def job_grotte_anteprime(q):
    """Le anteprime prospettiche della grotta grande (docs/concept/grotte_anteprima*.jpg), da approvare."""
    import grotte
    tane = _grotte_scena(neve=True)
    s = q.persp_scale
    big = (round(1600 * s), round(900 * s))
    # la vista d'insieme: da dietro, sotto il pozzo, verso la tana della Madre
    grotte_vista(q, 'grotte_anteprima_insieme', (-0.6, -4.6, 1.4), (0.4, 9.0, -1.6), 14.0, big, esposizione=0.6)
    # la tana della Madre dall'occhio, con la torcia (non arriva fin laggiù)
    grotte_vista(q, 'grotte_anteprima_madre', grotte.OCCHIO, (0.0, 12.0, -2.4), 20.0, big, torcia=True, esposizione=0.6)
    # la torcia su un'apertura: quella di Gulpy, dall'occhio
    g = tane['gulpy']
    grotte_vista(q, 'grotte_anteprima_torcia', grotte.OCCHIO, tuple(g['appoggio'] + np.array((0, 0, -0.9))), 26.0, big,
                 torcia=True, esposizione=0.6)


def job_grotte_tane(q):
    """Le sette aperture da vicino, con la torcia: una tavola (docs/concept/grotte_anteprima_tane.jpg)."""
    import grotte
    tane = _grotte_scena(neve=True)
    s = q.persp_scale
    size = (round(720 * s), round(480 * s))
    tiles = []
    for chi, *_ in grotte.TANE:
        t = tane[chi]
        a = t['appoggio']
        d = a - np.array(grotte.OCCHIO)
        d[2] = 0
        d /= np.linalg.norm(d)
        pos = a - d * 3.0 + np.array((0, 0, -0.35))
        tgt = a + np.array((0, 0, -0.45))
        out = grotte_vista(q, f'grotte_tana_{chi}', tuple(pos), tuple(tgt), 30.0, size, torcia=True, esposizione=0.6,
                           cono=50.0)
        tiles.append((chi, out))
    tavola_tane(tiles, size)


def tavola_tane(tiles, size):
    """Mette insieme le sette bocche da vicino in una tavola (4 × 2) col nome di ognuno."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = size
    sheet = Image.new('RGB', (W * 4, H * 2), (8, 10, 12))
    font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'Limelight-Regular.ttf'), max(14, H // 14))
    dr = ImageDraw.Draw(sheet)
    for k, (chi, path) in enumerate(tiles):
        im = Image.open(path)
        x, y = (k % 4) * W, (k // 4) * H
        sheet.paste(im, (x, y))
        dr.text((x + 12, y + 8), chi.capitalize(), fill=(230, 220, 200), font=font)
        os.remove(path)
    out = os.path.join(CONCEPT, 'grotte_anteprima_tane.jpg')
    sheet.save(out, quality=88)
    log('tavola', out)


def job_sotto_anteprima(q):
    """«Sotto la barca», inquadratura fissa: l'anteprima veloce da approvare (docs/concept/sotto_barca_anteprima.jpg)
    come la vede il gioco (90° in orizzontale) e una più larga con tutto il campo in cui si gira (150°)."""
    import sotto_barca as sb
    reset_scene()
    sb.build_sotto_barca(neve=True)
    s = q.persp_scale
    size = (round(1600 * s), round(900 * s))
    grotte_vista(q, 'sotto_barca_anteprima', sb.OCCHIO_SB, sb.GUARDA_SB, 18.0, size, esposizione=0.3, acqua=sb.ACQUA)
    grotte_vista(q, 'sotto_barca_anteprima_larga', sb.OCCHIO_SB, sb.GUARDA_SB, 9.6, size, esposizione=0.3, acqua=sb.ACQUA)


def render_a_strisce(nome, q, samples, W, H, strisce=8, sov=24):
    """Rende il panorama (la camera della scena) a strisce orizzontali che restano in cache (cache/<qualità>/
    <nome>_<W>_s<k>.exr): se il container si riavvia, si riparte dalla striscia che mancava. Le strisce si
    sovrappongono di sov righe, che poi si tagliano (il denoise sbaglia ai bordi). Restituisce i passi interi, con i
    raggi ('raggi') a parte."""
    import grotte
    S = H // strisce
    parti = []
    t = time.time()
    for k in range(strisce):
        y0, y1 = k * S, (H if k == strisce - 1 else (k + 1) * S)
        r0, r1 = max(0, y0 - sov), min(H, y1 + sov)
        exr = os.path.join(CACHE, q.name, f'{nome}_{W}_s{k}.exr')
        fatto = exr.replace('.exr', '.ok')
        if not os.path.exists(fatto):
            grotte.render_con_raggi(exr, samples, (W, H), data_passes=('Mist', 'Object Index'), region=(0, r0, W, r1))
            with open(fatto, 'w') as f:
                f.write('ok')
            log(f'{nome} striscia {k + 1}/{strisce}', round(time.time() - t), 's')
        p = post.read_exr(exr)
        if os.path.exists(exr.replace('.exr', '_raggi.exr')):          # nelle tane non ci sono raggi
            p['raggi'] = post.read_exr(exr.replace('.exr', '_raggi.exr'))['ambient']
        parti.append({c: v[y0 - r0: y1 - r0, :W] for c, v in p.items()})
    return {c: np.concatenate([pp[c] for pp in parti], 0) for c in parti[0]}


def codifica_posto(nome, passes, p, sky, cartella):
    """I passi di un posto delle immersioni come li legge il motore: ambient e lantern (a metà risoluzione) in gamma 4
    con la loro scale; il dato come quello del mondo: R = sqrt(distanza / 2500 m), G = 0,1 (quanto trema), B = sky
    (la superficie). Restituisce la voce 'pano' del posto."""
    import grotte
    from PIL import Image
    os.makedirs(cartella, exist_ok=True)
    pano = {}
    for g in ('ambient', 'lantern'):
        lin = passes[g][..., :3]
        if g == 'lantern':
            lin = lin.reshape(lin.shape[0] // 2, 2, lin.shape[1] // 2, 2, 3).mean(axis=(1, 3))
        scale = post.pick_scale(lin)
        fn = f'{nome}_{g}.webp'
        post.save_webp(post.encode_light_pass(lin, scale), os.path.join(cartella, fn))
        pano[g] = {'file': 'immersioni/' + fn, 'scale': scale}
    mist = np.clip(p['mist'], 0, 1)
    dist = np.where(mist > 0.999, 2500.0, mist * grotte.MIST_DEPTH)
    data = np.dstack([np.sqrt(np.clip(dist / 2500.0, 0, 1)), np.full_like(mist, 0.1), sky.astype(np.float32)])
    post.save_webp(Image.fromarray((data * 255 + 0.5).astype(np.uint8), 'RGB'),
                   os.path.join(cartella, f'{nome}_data.webp'), lossless=True)
    pano['data'] = f'immersioni/{nome}_data.webp'
    return pano


def job_sotto(q):
    """«Sotto la barca», il render finale (approvato l'11 ottobre sera): un'inquadratura fissa come le camerette, cioè
    un panorama PARZIALE (160° × 95°, da −45° a +50° di latitudine) centrato sulla direzione in cui guarda il sub, con
    il frame (si gira di 30° per parte e di 6° in su e in giù). Stessa codifica della grotta grande; file in
    public/assets/img/immersioni/sotto_barca_*.webp e la voce del posto in sotto_barca_posto.json."""
    import grotte
    import sotto_barca as sb
    reset_scene()
    sb.build_sotto_barca(neve=False)
    sup = bpy.data.objects.get('SottoSuperficie')
    sup.pass_index = 2                                   # la superficie: B del passo dati
    occhio = np.array(sb.OCCHIO_SB)
    d = np.array(sb.GUARDA_SB) - occhio
    yaw0 = math.degrees(math.atan2(d[0], d[1]))
    pitch0 = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    LON, LAT_MIN, LAT_MAX = 80.0, -45.0, 50.0
    cam = panorama_camera(location=tuple(occhio), name='SottoCam')
    cam.data.longitude_min = math.radians(-LON)
    cam.data.longitude_max = math.radians(LON)
    cam.data.latitude_min = math.radians(LAT_MIN)
    cam.data.latitude_max = math.radians(LAT_MAX)
    set_pano_yaw(cam, yaw0)
    grotte.torcia_panorama(occhio=tuple(occhio))
    px = q.pano_width / 360.0                            # la stessa densità della grotta grande
    W = int(round(2 * LON * px / 2)) * 2
    H = int(round((LAT_MAX - LAT_MIN) * px / 2)) * 2
    samples = int(os.environ.get('GROTTE_CAMPIONI', min(q.samples, 64)))
    t = time.time()
    p = render_a_strisce('sotto_barca', q, samples, W, H, strisce=4)
    log('sotto la barca render', round(time.time() - t), 's', p['ambient'].shape)
    passes = grotte.acqua(p, blur_px=360.0 * px / 24, **sb.ACQUA)
    sky = np.abs(p['index'] - 2) < 0.5
    pano = codifica_posto('sotto_barca', passes, p, sky, os.path.join(OUT_IMG, 'immersioni'))

    def dirz(v):
        e = np.array(v) - occhio
        y = math.degrees(math.atan2(e[0], e[1])) - yaw0
        return round((y + 180) % 360 - 180, 1), round(math.degrees(math.atan2(e[2], math.hypot(e[0], e[1]))), 1)
    cy, cp = dirz(sb.BOCCA)
    a, b = np.array(sb.PRUA_CIMA), np.array(sb.ANCORA)
    ry, rp = dirz(a + (b - a) * 0.04)                    # la cima, in alto vicino alla prua: si clicca per risalire
    posto = {'_nota': "Sotto la barca (render finale, tools/render/sotto_barca.py): inquadratura fissa, panorama "
                      "parziale; l'acqua torbida è già cotta nei passi di luce.",
             'pano': pano, 'size': [W, H], 'latMin': LAT_MIN, 'latMax': LAT_MAX, 'lonMin': -LON, 'lonMax': LON,
             'yaw': 0, 'rays': 1.0,
             'frame': {'yaw': 0, 'pitch': round(pitch0, 1), 'yawRange': 30, 'pitchRange': 6},
             'links': [{'to': 'grotta_grande', 'yaw': cy, 'pitch': cp,
                        'r': round(math.degrees(math.atan2(sb.BOCCA_R, float(np.linalg.norm(np.array(sb.BOCCA) - occhio)))), 1),
                        'label': 'cave'},
                       {'ascend': True, 'yaw': ry, 'pitch': rp, 'r': 7, 'label': 'ascend'}],
             'acquaCotta': True}
    with open(os.path.join(OUT_IMG, 'immersioni', 'sotto_barca_posto.json'), 'w') as f:
        json.dump(posto, f, indent=1, ensure_ascii=False)
    log('sotto la barca: posto scritto', json.dumps(posto['links']), json.dumps(posto['frame']))
    pv = post.tonemap(post.compose(passes, {'ambient': 1.0}), 0.3)
    post.save_png(pv, os.path.join(CACHE, q.name, 'sotto_barca_pano.png'))


def tavola(nomi_file, size, out, cols=4, titoli=None, cancella=True):
    """Mette insieme le immagini in una tavola (cols per riga) col titolo di ognuna; cancella le immagini."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = size
    rows = (len(nomi_file) + cols - 1) // cols
    sheet = Image.new('RGB', (W * cols, H * rows), (8, 10, 12))
    font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'Limelight-Regular.ttf'), max(14, H // 14))
    dr = ImageDraw.Draw(sheet)
    for k, path in enumerate(nomi_file):
        im = Image.open(path).resize((W, H))
        x, y = (k % cols) * W, (k // cols) * H
        sheet.paste(im, (x, y))
        if titoli:
            dr.text((x + 12, y + 8), titoli[k], fill=(230, 220, 200), font=font)
        if cancella:
            os.remove(path)
    sheet.save(out, quality=88)
    log('tavola', out)


def job_tane_anteprime(q):
    """Le anteprime delle tane (da approvare): docs/concept/tane_camerette.jpg (le sette camerette vuote viste
    dall'ingresso, con la torcia) e docs/concept/tane_pose.jpg (i sette mostri addormentati da vicino). TANE=gulpy,molly
    per farne solo alcune (le tavole si fanno quando ci sono tutte e sette)."""
    import tane
    global CONCEPT
    concept, CONCEPT = CONCEPT, os.path.join(CACHE, 'tane_tessere')    # le singole viste restano in cache
    try:
        _tane_anteprime(q, tane)
    finally:
        CONCEPT = concept
    fatte = [os.path.join(CACHE, 'tane_tessere', f'tane_cameretta_{c}.jpg') for c in tane.ORDINE]
    if all(os.path.exists(f) for f in fatte):
        tit = [c.capitalize() for c in tane.ORDINE]
        s = q.persp_scale
        size = (round(960 * s), round(540 * s))
        tavola(fatte, size, os.path.join(CONCEPT, 'tane_camerette.jpg'), titoli=tit, cancella=False)
        tavola([os.path.join(CACHE, 'tane_tessere', f'tane_posa_{c}.jpg') for c in tane.ORDINE], size,
               os.path.join(CONCEPT, 'tane_pose.jpg'), titoli=tit, cancella=False)


def _tane_anteprime(q, tane):
    import grotte
    grotte.TORCIA_BLEND = 1.0          # la macchia della torcia sulla sabbia, morbida (12 ottobre)
    chi_tutti = [c for c in os.environ.get('TANE', ','.join(tane.ORDINE)).split(',') if c]
    s = q.persp_scale
    size = (round(960 * s), round(540 * s))
    for chi in chi_tutti:
        reset_scene()
        info = tane.build_tana(chi)
        tgt = (tane.OCCHIO_T[0], tane.OCCHIO_T[1] + 10.0, tane.OCCHIO_T[2] + 10.0 * math.tan(math.radians(tane.PITCH_T)))
        grotte_vista(q, f'tane_cameretta_{chi}', tane.OCCHIO_T, tgt, 15.0, size, torcia=True, esposizione=0.5, cono=45.0,
                    pesi={'ambient': 1.0, 'lantern': 0.6})
        obs = tane.mostro(chi, info)
        P = world_bbox([o for o in obs if o.type == 'MESH'])
        c = (P.min(0) + P.max(0)) / 2
        r = float(np.linalg.norm(P.max(0) - P.min(0))) / 2
        # la camera della posa: dalla parte del sub, alla sua quota (mai dentro il soffitto), a una distanza che lo
        # contiene tutto
        d = np.array(tane.OCCHIO_T) - c
        d[2] = 0.0
        d /= np.linalg.norm(d)
        pos = c + d * max(2.4, r * 2.2)
        pos[2] = min(max(pos[2], 0.8), 2.6)
        grotte_vista(q, f'tane_posa_{chi}', tuple(pos), tuple(c), 24.0, size, torcia=True, esposizione=0.5, cono=50.0)


def job_tane(q):
    """Le tane delle immersioni, render finali (12 ottobre) nel formato del motore (docs/IMMERSIONI.md, «Come si
    aggiungono i posti veri»), e il collegamento in public/assets/img/immersioni.json.

    Per ogni tana: la cameretta vuota come panorama parziale (inquadratura fissa: 160° × 80°, da −55° a +25°, frame
    a −15° che si gira di 30° per parte; passi ambient, lantern e dati come la grotta grande, con l'acqua cotta) — è
    anche la tana vuota del mostro nuovo; poi il mostro addormentato come strato ritagliato con l'alfa (la stanza fa
    da maschera e gli fa la luce) e la toppa del respiro (la stessa posa col fiato preso), con la stessa acqua della
    stanza davanti; le direzioni del mostro (dove si clicca per il pesce), delle bolle e della cosa da trovare.
    TANE=gulpy,molly per farne solo alcune; GROTTE_CAMPIONI per i campioni (64)."""
    import tane
    path_dati = os.path.join(OUT_IMG, 'immersioni.json')
    for chi in [c for c in os.environ.get('TANE', ','.join(tane.ORDINE)).split(',') if c]:
        voce = tana_finale(q, chi)
        with open(path_dati) as f:
            dati = json.load(f)
        posto = dati['places'][f'tana_{chi}']
        for k in ('tint', 'panoEmpty'):
            posto.pop(k, None)
        posto.update(voce)
        with open(path_dati, 'w') as f:
            f.write(json.dumps(dati, indent=1, ensure_ascii=False) + '\n')
        log(f'tana {chi}: posto aggiornato in immersioni.json')


def tana_finale(q, chi):
    import grotte
    import tane
    from PIL import Image
    reset_scene()
    info = tane.build_tana(chi, res=0.05)
    occhio = np.array(tane.OCCHIO_T)
    LON = 80.0
    LAT_MIN, LAT_MAX, PITCH = tane.INQUADRATURA.get(chi, (-55.0, 25.0, tane.PITCH_T))
    cam = panorama_camera(location=tuple(occhio), name='TanaCam')
    cam.data.longitude_min = math.radians(-LON)
    cam.data.longitude_max = math.radians(LON)
    cam.data.latitude_min = math.radians(LAT_MIN)
    cam.data.latitude_max = math.radians(LAT_MAX)
    grotte.torcia_panorama(occhio=tuple(occhio))
    px = q.pano_width / 360.0
    W = int(round(2 * LON * px / 2)) * 2
    H = int(round((LAT_MAX - LAT_MIN) * px / 2)) * 2
    samples = int(os.environ.get('GROTTE_CAMPIONI', min(q.samples, 64)))
    cartella = os.path.join(OUT_IMG, 'immersioni')
    # ── la cameretta vuota
    t = time.time()
    p = render_a_strisce(f'tana_{chi}', q, samples, W, H, strisce=4)
    log(f'tana {chi}: cameretta', round(time.time() - t), 's')
    stanza = grotte.acqua(p, blur_px=360.0 * px / 24)
    pano = codifica_posto(f'tana_{chi}', stanza, p, np.zeros_like(p['mist']), cartella)
    post.save_png(post.tonemap(post.compose(stanza, {'ambient': 1.0, 'lantern': 0.6}), 0.5),
                  os.path.join(CACHE, q.name, f'tana_{chi}_pano.png'))

    def dirz(v):
        e = np.array(v) - occhio
        return math.degrees(math.atan2(e[0], e[1])), math.degrees(math.atan2(e[2], math.hypot(e[0], e[1])))

    def pixel(v):
        yaw, pitch = dirz(v)
        return (yaw + LON) / (2 * LON) * W, (LAT_MAX - pitch) / (LAT_MAX - LAT_MIN) * H

    # ── il mostro che dorme e la toppa del respiro: strati ritagliati, la stanza fa da maschera
    stanza_obs = [o for o in bpy.data.objects if o.type in ('MESH', 'FONT', 'CURVE')]
    strati = []
    rect = None
    for fiato in (0.0, 1.0):
        prima = set(bpy.data.objects.keys())
        obs = tane.mostro(chi, info, fiato=fiato)
        mesh = [o for o in obs if o.type == 'MESH']
        if rect is None:
            pts = np.array(dense_points(mesh, n=3000))
            uv = np.array([pixel(v) for v in pts])
            m = 24
            rect = [max(0, int(uv[:, 0].min()) - m), max(0, int(uv[:, 1].min()) - m),
                    min(W, int(math.ceil(uv[:, 0].max())) + m), min(H, int(math.ceil(uv[:, 1].max())) + m)]
            c = (pts.min(0) + pts.max(0)) / 2
            sy, sp = dirz(c)
            raggio = max(abs(uv[:, 0] - pixel(c)[0]).max(), abs(uv[:, 1] - pixel(c)[1]).max()) / px * 0.8
            testa = [o for o in mesh if 'Head' in o.name] or mesh
            hb = world_bbox(testa)
            by, bp = dirz((hb.min(0) + hb.max(0)) / 2 + np.array((0, 0, 0.15)))
        for o in stanza_obs:
            o.is_holdout = True
        exr = os.path.join(CACHE, q.name, f'tana_{chi}_{"respiro" if fiato else "posa"}.exr')
        t = time.time()
        render(exr, samples, (W, H), region=tuple(rect), transparent=True, data_passes=('Alpha', 'Mist'))
        log(f'tana {chi}: {"respiro" if fiato else "posa"}', round(time.time() - t), 's', rect)
        for o in stanza_obs:
            o.is_holdout = False
        sp_ = post.read_exr(exr)
        h_, w_ = rect[3] - rect[1], rect[2] - rect[0]
        sp_ = {k: v[:h_, :w_] for k, v in sp_.items()}
        alpha = np.clip(sp_['alpha'], 0, 1)
        cotto = grotte.acqua(sp_, blur_px=1, sfocata=stanza['sfocata'][rect[1]:rect[3], rect[0]:rect[2]], alpha=alpha)
        passes = {}
        nome = f'tana_{chi}_{"respiro" if fiato else "posa"}'
        for g in ('ambient', 'lantern'):
            lin = cotto[g][..., :3]
            scale = post.pick_scale(lin / np.maximum(alpha[..., None], 1e-4), alpha)
            post.save_webp(post.encode_light_pass(lin, scale, alpha), os.path.join(cartella, f'{nome}_{g}.webp'))
            passes[g] = {'file': f'immersioni/{nome}_{g}.webp', 'scale': scale}
        strato = {'passes': passes, 'rect': list(rect)}
        if fiato:
            strato['breath'] = BREATH.get(chi, 4.2)
        strati.append(strato)
        for nm in set(bpy.data.objects.keys()) - prima:
            o = bpy.data.objects.get(nm)
            if o is not None:
                bpy.data.objects.remove(o)
    fy, fp = dirz(info['trovato'])
    voce = {
        '_nota': f"La tana di {chi.capitalize()} (render finale, tools/render/tane.py): la cameretta vuota è anche la tana "
                 "vuota del mostro nuovo; il mostro che dorme e la toppa del respiro sono strati sopra. L'acqua è cotta.",
        'pano': pano, 'size': [W, H], 'latMin': LAT_MIN, 'latMax': LAT_MAX, 'lonMin': -LON, 'lonMax': LON, 'yaw': 0,
        'frame': {'yaw': 0, 'pitch': PITCH, 'yawRange': 30, 'pitchRange': 4},
        'rays': 0.12, 'acquaCotta': True,
        'sleeper': {'yaw': round(sy, 1), 'pitch': round(sp, 1), 'r': round(max(6.0, raggio), 1), 'layers': strati,
                    'bubbles': {'yaw': round(by, 1), 'pitch': round(bp, 1)}},
        'find': {'lore': f'den_{chi}', 'yaw': round(fy, 1), 'pitch': round(fp, 1), 'r': 5},
    }
    return voce


# il periodo del respiro nel sonno, per mostro (secondi): i grandi respirano lenti, Fangy lentissimo
BREATH = {'gulpy': 5.0, 'molly': 3.8, 'hatch': 4.2, 'robin': 3.6, 'archie': 4.6, 'lampy': 3.4, 'fangy': 6.5}


def job_grotte(q):
    """Il panorama a 360° della grotta grande per il motore delle immersioni (docs/IMMERSIONI.md, «Come si aggiungono i
    posti veri»): sfera intera (latitudine da −90° a 90°, larghezza = quella della qualità, altezza la metà), passi
    ambient e lantern (la torcia sull'occhio, a metà risoluzione) codificati come gli altri render (gamma 4 con la loro
    scale), e il passo dati come quello del mondo: R = sqrt(distanza / 2500 m), G = quanto trema l'immagine (0,1),
    B = la superficie vista dal pozzo. L'acqua torbida approvata nelle anteprime è già cotta nei passi (GROTTE_ACQUA=0
    per averli crudi). Si rende a strisce che restano in cache: se il container si riavvia, si riparte dalla striscia
    che mancava. File in public/assets/img/immersioni/grotta_grande_*.webp e la voce del posto in
    grotta_grande_posto.json (da copiare in immersioni.json)."""
    import grotte
    tane = _grotte_scena(neve=False)
    cam = panorama_camera(location=grotte.OCCHIO, name='GrottaCam')
    cam.data.latitude_min = math.radians(-90.0)
    cam.data.latitude_max = math.radians(90.0)
    grotte.torcia_panorama()
    W = q.pano_width
    H = W // 2
    samples = int(os.environ.get('GROTTE_CAMPIONI', min(q.samples, 64)))
    t = time.time()
    p = render_a_strisce('grotta', q, samples, W, H)
    log('grotta render', round(time.time() - t), 's', p['ambient'].shape)
    if os.environ.get('GROTTE_ACQUA', '1') != '0':
        passes = grotte.acqua(p, blur_px=W / 24)
    else:
        passes = {'ambient': p['ambient'][..., :3] + p['raggi'][..., :3], 'lantern': p['lantern'][..., :3]}
    cartella = os.path.join(OUT_IMG, 'immersioni')
    os.makedirs(cartella, exist_ok=True)
    pano = {}
    for g in ('ambient', 'lantern'):
        lin = passes[g][..., :3]
        if g == 'lantern':
            lin = lin.reshape(lin.shape[0] // 2, 2, lin.shape[1] // 2, 2, 3).mean(axis=(1, 3))
        scale = post.pick_scale(lin)
        fn = f'grotta_grande_{g}.webp'
        post.save_webp(post.encode_light_pass(lin, scale), os.path.join(cartella, fn))
        pano[g] = {'file': 'immersioni/' + fn, 'scale': scale}
    mist = np.clip(p['mist'], 0, 1)
    sky = ((p['index'] < 0.5) & (mist > 0.999)).astype(np.float32)
    dist = np.where(mist > 0.999, 2500.0, mist * grotte.MIST_DEPTH)
    from PIL import Image
    data = np.dstack([np.sqrt(np.clip(dist / 2500.0, 0, 1)), np.full_like(mist, 0.1), sky])
    post.save_webp(Image.fromarray((data * 255 + 0.5).astype(np.uint8), 'RGB'),
                   os.path.join(cartella, 'grotta_grande_data.webp'), lossless=True)
    pano['data'] = 'immersioni/grotta_grande_data.webp'

    def dirz(v):
        d = np.array(v) - np.array(grotte.OCCHIO)
        return round(math.degrees(math.atan2(d[0], d[1])), 1), round(math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))), 1)
    links = []
    pz_yaw, pz_pitch = dirz(grotte.POZZO_BASSO)
    links.append({'to': 'sotto_barca', 'yaw': pz_yaw, 'pitch': pz_pitch, 'r': 14, 'label': 'back'})
    for chi, t_ in tane.items():
        yaw, pitch = dirz(t_['bocca'])
        dist_ = float(np.linalg.norm(t_['bocca'] - np.array(grotte.OCCHIO)))
        r = round(math.degrees(math.atan2(t_['raggio'], dist_)), 1)
        if chi == 'madre':
            links.append({'note': 'mother', 'yaw': yaw, 'pitch': pitch, 'r': r})
        else:
            links.append({'to': f'tana_{chi}', 'yaw': yaw, 'pitch': pitch, 'r': r})
    posto = {'_nota': "La grotta grande (render finale, tools/render/grotte.py): l'acqua torbida è già cotta nei passi "
                      "di luce, come nelle anteprime approvate; la nebbia del motore qui va tenuta bassa.",
             'pano': pano, 'size': [W, H], 'latMin': -90, 'latMax': 90, 'yaw': 0,
             'look': {'yaw': 0, 'pitch': -4}, 'rays': 0.25, 'links': links,
             'acquaCotta': os.environ.get('GROTTE_ACQUA', '1') != '0'}
    with open(os.path.join(cartella, 'grotta_grande_posto.json'), 'w') as f:
        json.dump(posto, f, indent=1, ensure_ascii=False)
    log('grotta grande: posto scritto', json.dumps(links))
    # anteprime di controllo: il panorama ridotto e due viste come nel gioco
    pv = post.tonemap(post.compose(passes, {'ambient': 1.0}), 0.6)
    post.save_png(np.asarray(Image.fromarray((pv * 255).astype(np.uint8)).resize((2048, 1024))) / 255.0,
                  os.path.join(CACHE, q.name, 'grotta_pano.png'))
    for nome, (yaw, pitch) in (('avanti', (0.0, -4.0)), ('pozzo', (pz_yaw, pz_pitch))):
        v = post.pano_to_view(pv, yaw, pitch, 90, (960, 540), -90.0, 90.0)
        post.save_png(v, os.path.join(CACHE, q.name, f'grotta_vista_{nome}.png'))


JOBS = {'grotte': job_grotte, 'tane': job_tane, 'tane_anteprime': job_tane_anteprime, 'sotto': job_sotto, 'sotto_anteprima': job_sotto_anteprima, 'grotte_ricomponi': job_grotte_ricomponi, 'grotte_anteprime': job_grotte_anteprime, 'grotte_tane': job_grotte_tane,
        'world': job_world, 'boat': job_boat, 'props': job_props, 'creature': job_creature, 'reencode': job_reencode, 'tarp': job_tarp, 'jumpscare': job_jumpscare, 'binocolo': job_binocolo, 'bordo': job_bordo, 'pelo': job_pelo}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('jobs', nargs='+')
    ap.add_argument('--quality', default='draft', choices=list(QUALITY))
    ap.add_argument('--fast', action='store_true', help='creature con mesh più grossolane (prove di posa)')
    a = ap.parse_args(argv)
    q = QUALITY[a.quality]
    os.makedirs(OUT_IMG, exist_ok=True)
    for j in a.jobs:
        log('== job', j, q.name)
        JOBS[j](q)


if __name__ == '__main__':
    main()
