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
    LIGHT_POINTS.update(landmarks.build_landmarks())
    LIGHT_POINTS['lighthouse'] = tuple(info['lighthouse'])
    parts, mats = boat.build_boat(fish_in_bucket=fish, rod=rod)
    parts['props'] += props.build_props()
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

def encode_layer(key, exr, space, width, rect=None, yaw_center=0.0, with_alpha=False, data=False, extra=None, quality=90):
    p = post.read_exr(exr)
    W, H = pano_size(width)
    alpha = p.get('alpha') if with_alpha else None
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

def job_world(q):
    build_scene(fish=0, rod=False)
    for o in coll_objects('boat'):
        o.visible_camera = False
    cam = panorama_camera()
    W, H = pano_size(q.pano_width)
    exr = os.path.join(CACHE, q.name, 'world.exr')
    t = time.time()
    render(exr, q.samples, (W, H), data_passes=('Mist', 'Object Index'))
    log('world render', round(time.time() - t), 's')
    encode_layer('world', exr, 'world', q.pano_width, data=True)
    write_globals(q.pano_width)


def job_boat(q):
    build_scene(fish=0, rod=False)
    for o in coll_objects('env'):
        o.visible_camera = False
    panorama_camera()
    W, H = pano_size(q.pano_width)
    exr = os.path.join(CACHE, q.name, 'boat.exr')
    t = time.time()
    render(exr, q.samples, (W, H), transparent=True, data_passes=('Alpha',))
    log('boat render', round(time.time() - t), 's')
    encode_layer('boat', exr, 'boat', q.pano_width, with_alpha=True)
    write_globals(q.pano_width)


def render_sprite(q, key, objs, space='boat', margin=12, holdout_boat=True, samples=None, extra=None, sea=False):
    """Rende visibili alla camera solo objs; la barca fa da maschera (holdout) se richiesto.
    sea=True: anche il mare fa da maschera (creature immerse, pure negli strati legati alla barca)."""
    boat_objs = renderable(coll_objects('boat'))
    env_objs = renderable(coll_objects('env'))
    keep = set(o.name for o in objs)
    saved = {o.name: (o.visible_camera, o.is_holdout) for o in boat_objs + env_objs}
    for o in env_objs:
        o.visible_camera = False
    for o in boat_objs:
        if o.name in keep:
            continue
        if holdout_boat and o.visible_camera:
            o.is_holdout = True
        else:
            o.visible_camera = False
    if space == 'world' or sea:
        sea_ob = bpy.data.objects.get('Sea')
        if sea_ob:
            sea_ob.visible_camera = True
            sea_ob.is_holdout = True
    pts = dense_points(objs)
    # media circolare: dietro la poppa gli angoli scavalcano ±180°
    ys = np.radians([yaw_of(p) for p in pts])
    yc = float(np.degrees(np.arctan2(np.mean(np.sin(ys)), np.mean(np.cos(ys)))))
    cam = bpy.context.scene.camera
    set_pano_yaw(cam, yc)
    rect = pano_rect(pts, q.pano_width, yc, margin)
    W, H = pano_size(q.pano_width)
    exr = os.path.join(CACHE, q.name, f'{key}.exr')
    t = time.time()
    render(exr, samples or q.samples, (W, H), region=rect, transparent=True, data_passes=('Alpha',))
    log(f'sprite {key} render', round(time.time() - t, 1), 's', rect)
    set_pano_yaw(cam, 0.0)
    for o in boat_objs + env_objs:
        if o.name in saved:
            o.visible_camera, o.is_holdout = saved[o.name]
    return encode_layer(key, exr, space, q.pano_width, rect=rect, yaw_center=round(yc, 4), with_alpha=True, extra=extra)


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


def job_creature(q):
    """Le creature nelle pose di gioco, come strati del panorama (vedi scena_creature.py).
    Variabile d'ambiente POSES=chiave1,chiave2 per renderne solo alcune."""
    import scena_creature
    build_scene(fish=0, rod=False)
    panorama_camera()
    only = [k for k in os.environ.get('POSES', '').split(',') if k]
    for key, (fn, space, sea) in scena_creature.POSES.items():
        if only and key not in only:
            continue
        before = set(bpy.data.objects.keys())
        fn()
        new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
        bpy.context.view_layer.update()
        # dove sono gli occhi (dall'occhio del pescatore): a lampara spenta si vedono solo loro
        eyes = [[round(float(o.matrix_world.translation[i] - EYE[i]), 4) for i in range(3)]
                for o in new if o.type == 'MESH' and 'Eye' in o.name and not o.name.startswith(('Toy', 'Duck'))]
        render_sprite(q, key, [o for o in new if o.type == 'MESH'], space=space, sea=sea, extra={'eyes': eyes})
        for o in new:
            o.hide_render = True
        bpy.context.view_layer.update()


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
    """I jumpscare delle creature (vedi jumpscare.py). JUMPSCARES=gulpy,molly,hatch per sceglierli."""
    import jumpscare
    who = [k for k in os.environ.get('JUMPSCARES', 'gulpy,molly,hatch').split(',') if k]
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


JOBS = {'world': job_world, 'boat': job_boat, 'props': job_props, 'creature': job_creature, 'reencode': job_reencode, 'tarp': job_tarp, 'jumpscare': job_jumpscare, 'binocolo': job_binocolo}


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
