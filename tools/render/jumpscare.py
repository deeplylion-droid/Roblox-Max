"""
I jumpscare: la creatura, dalla sua posa di gioco, si lancia sul pescatore.

Sono fotogrammi a tutto schermo (non strati del panorama), visti dall'occhio del pescatore:
lo sfondo (mondo + barca) si rende una volta sola, la creatura in ogni fotogramma con il resto della
scena come maschera; poi si compongono e si codificano come gli altri render (overlays.json → jumpscares).
Molly si rende sul lato destro: per il sinistro il motore specchia l'immagine.

Uso: tools/.venv/bin/python tools/render/jobs.py jumpscare --quality preview   (JUMPSCARES=gulpy,molly,hatch)
"""
from __future__ import annotations

import math
import os
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

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
    o = (0.0, -2.45, 0.58)                            # in piedi sul ponte di poppa, già piegato su di te
    M0 = sc.M_of(o, yaw=sc.facing_yaw(o), pitch=38.0)
    obs = hatch.build(viewer=sc.to_local(M0, EYE))
    lights = [ob for ob in bpy.data.objects if ob.type == 'LIGHT' and ob.name.startswith('ToyLight')]
    for li in lights:
        li.data.energy = 3.0
    obs = sc.place(obs + lights, M0)
    head = hatch.HEAD.pos
    M1 = _toward_eye(M0, head, 0.34, extra_pitch=14.0)
    aim = M0 @ Vector(tuple(map(float, head)))
    return obs, M0, M1, aim


ATTACKS = {'gulpy': gulpy_attack, 'molly': molly_attack, 'hatch': hatch_attack}


# ───────────────────────── render ─────────────────────────

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
    d = (aim - Vector(EYE)).normalized()
    hor = math.hypot(d.x, d.y)
    max_up = math.tan(math.radians(22.0)) * hor
    d = Vector((d.x, d.y, min(d.z, max_up) - 0.06)).normalized()
    cam_target = tuple(Vector(EYE) + d * 2.0)
    perspective_camera(EYE, cam_target, lens=22.0, name='JumpCam')
    # la versione da approvare basta più piccola e con meno campioni (ci sono scosse e grana sopra)
    W, H = (1920, 1080) if q.name == 'final' else (960, 540) if q.name == 'preview' else (640, 360)
    samples = q.samples if q.name == 'final' else min(q.samples, 32)
    out_dir = os.path.join(CACHE, q.name, 'jumpscare')
    os.makedirs(out_dir, exist_ok=True)

    # sfondo: tutto tranne la creatura
    for o in meshes:
        o.hide_render = True
    bg_exr = os.path.join(out_dir, f'{who}_bg.exr')
    t = time.time()
    render(bg_exr, samples, (W, H), data_passes=())
    log(f'jumpscare {who} sfondo', round(time.time() - t), 's')
    for o in meshes:
        o.hide_render = False

    # la creatura in ogni fotogramma: il resto della scena fa da maschera
    scene_objs = renderable(coll_objects('boat')) + renderable(coll_objects('env'))
    keep = set(o.name for o in meshes)
    for o in scene_objs:
        if o.name not in keep and o.visible_camera:
            o.is_holdout = True
    bg = post_mod.read_exr(bg_exr)
    bg_lin = sum(bg[g][..., :3] for g in ('ambient', 'lamp', 'lantern') if g in bg)
    frames = []
    for i in range(FRAMES):
        u = ease(i / (FRAMES - 1))
        _set_creature(creature, base, M0inv, _lerp_matrix(M0, M1, u))
        exr = os.path.join(out_dir, f'{who}_{i:02d}.exr')
        t = time.time()
        render(exr, samples, (W, H), transparent=True, data_passes=('Alpha',))
        p = post_mod.read_exr(exr)
        fg = sum(p[g][..., :3] for g in ('ambient', 'lamp', 'lantern') if g in p)
        a = p['alpha'][..., None] if 'alpha' in p else np.ones(fg.shape[:2] + (1,), np.float32)
        comp = fg + bg_lin * (1 - np.clip(a, 0, 1))
        scale = post_mod.pick_scale(comp)
        fn = f'js_{who}_{i:02d}.webp'
        post_mod.save_webp(post_mod.encode_light_pass(comp, scale), os.path.join(OUT_IMG, fn), quality=88)
        frames.append({'file': fn, 'scale': scale})
        log(f'jumpscare {who} fotogramma {i}', round(time.time() - t, 1), 's')
    post_mod.update_manifest(overlays_path, f'jumpscares.{who}', {'frames': frames, 'fps': FPS, 'aspect': round(W / H, 4)})
