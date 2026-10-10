"""
Sfondo del Catalogo: il banco della barca visto dall'alto, alla luce della lanterna, dove si appoggia il libro.

Le tavole verniciate del banco (lo stesso legno della barca), una cima arrotolata, qualche amo con un pezzo di
lenza e un piombo, un mozzicone di matita, gocce d'acqua e scaglie di pesce. Il centro resta libero: lì il gioco
disegna il libro (HTML), quindi la luce cade dall'alto a sinistra come sulle pagine.

Uso: tools/.venv/bin/python tools/render/catalogo.py [--fast]
Uscita: public/assets/img/catalogo/sfondo.webp (2560x1440)
"""
from __future__ import annotations

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from common import CACHE, ROOT, link, log, reset_scene  # noqa: E402
from geo import rbox, tube  # noqa: E402
from nodes import material  # noqa: E402

FAST = '--fast' in sys.argv
COL = 'boat'
OUT = os.path.join(ROOT, 'public', 'assets', 'img', 'catalogo')
W_M = 0.85                      # larghezza inquadrata (m): il libro aperto ne occupa circa due terzi
H_M = W_M * 9 / 16


def wood_material():
    """Legno verniciato consumato del banco (come WoodVarnish della barca), con le venature lungo X."""
    m, g = material('BenchWood')
    co = g.texcoord('Object')
    # venature: rumore stiratissimo lungo X (strisce irregolari, non bande periodiche)
    streak = g.noise(g.mapping(co, scale=(0.012, 1.0, 1.0)), scale=95.0, detail=7.0, rough=0.62)
    streak2 = g.noise(g.mapping(co, scale=(0.02, 1.0, 1.0)), scale=260.0, detail=4.0, rough=0.5)
    grain = g.smoothstep(0.35, 0.68, g.add(g.mul(streak.fac, 0.75), g.mul(streak2.fac, 0.25)))
    fine = g.noise(g.mapping(co, scale=(0.05, 1.0, 1.0)), scale=700.0, detail=4.0, rough=0.6)
    n = g.noise(co, scale=14.0, detail=6.0, rough=0.62)
    mixv = g.add(g.add(g.mul(grain, 0.45), g.mul(n.fac, 0.35)), g.mul(fine.fac, 0.2))
    base = g.ramp(mixv, [(0.22, (0.07, 0.034, 0.015)), (0.5, (0.16, 0.083, 0.036)), (0.8, (0.26, 0.145, 0.068))])
    wear = g.smoothstep(0.6, 0.7, g.noise(co, scale=2.6, detail=5.0, rough=0.7).fac)
    col = g.mix(wear, base, (0.30, 0.24, 0.17))
    # aloni d'acqua salata asciugata, più chiari
    salt = g.smoothstep(0.64, 0.7, g.noise(g.mapping(co, scale=(1.0, 1.0, 1.0)), scale=4.5, detail=3.0, rough=0.5).fac)
    col = g.mix(g.mul(salt, 0.35), col, (0.42, 0.38, 0.32))
    bump = g.bump(g.add(g.mul(grain, 0.6), g.add(g.mul(n.fac, 0.3), g.mul(fine.fac, 0.25))), strength=0.12, distance=0.0012)
    g.output_material(g.principled(color=col, rough=g.mixf(wear, 0.32, 0.72), coat=g.mixf(wear, 0.55, 0.0),
                                   coat_rough=0.14, normal=bump))
    return m


def simple(name, color, rough=0.5, metal=0.0, noise=0.0, scale=40.0):
    m, g = material(name)
    col = color
    if noise:
        n = g.noise(g.texcoord('Object'), scale=scale, detail=6.0, rough=0.6)
        col = g.mix(g.mul(n.fac, noise), color, tuple(c * 0.55 for c in color))
    g.output_material(g.principled(color=col, rough=rough, metal=metal))
    return m


def glass_drop():
    m, g = material('WaterDrop')
    g.output_material(g.principled(color=(0.9, 0.95, 1.0), rough=0.04, transmission=1.0, ior=1.33, coat=0.0))
    return m


def scale_material():
    """Scaglia di pesce: madreperla sottile, quasi trasparente."""
    m, g = material('FishScale')
    g.output_material(g.principled(color=(0.85, 0.88, 0.9), rough=0.12, metal=0.2, transmission=0.6, ior=1.45, thin_film=420.0, alpha=0.75))
    return m


def planks(rng, mat):
    obs = []
    w, gap = 0.15, 0.006
    n = int(math.ceil(H_M / (w + gap))) + 2
    y0 = -(n * (w + gap)) / 2
    for i in range(n):
        y = y0 + i * (w + gap) + w / 2
        z = -0.02 + rng.uniform(-0.002, 0.002)
        ob = rbox(f'Plank{i}', (W_M + 0.4, w, 0.04), (rng.uniform(-0.1, 0.1), y, z), rot=(rng.uniform(-0.004, 0.004), 0, rng.uniform(-0.003, 0.003)),
                  bevel=0.004, col=COL)
        # coordinate dell'oggetto = coordinate del mondo: le venature non si ripetono uguali su ogni tavola
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
        ob.select_set(False)
        ob.data.materials.append(mat)
        obs.append(ob)
    # fessure scure fra le tavole
    under = rbox('Under', (W_M + 1.0, H_M + 1.0, 0.01), (0, 0, -0.07), bevel=0.0, col=COL)
    under.data.materials.append(simple('Gap', (0.01, 0.008, 0.006), rough=0.9))
    obs.append(under)
    return obs


def rope_coil(rng, c, mat):
    pts = []
    turns, r0, r1 = 4.2, 0.012, 0.062
    for t in np.linspace(0, 1, 420):
        a = t * turns * 2 * math.pi
        r = r0 + (r1 - r0) * t
        pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), 0.0058 + 0.0015 * math.sin(a * 3.1)))
    # il capo libero che scappa via
    a = turns * 2 * math.pi
    ex, ey = c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a)
    for k in range(1, 30):
        u = k / 29
        pts.append((ex + 0.16 * u, ey - 0.06 * u + 0.02 * math.sin(u * 5), 0.0058))
    P = np.array(pts)
    seg = np.diff(P, axis=0)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(seg, axis=1))])
    tot = L[-1]
    m = int(tot / 0.0012)
    u = np.linspace(0, tot, m)
    C = np.stack([np.interp(u, L, P[:, k]) for k in range(3)], 1)
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    up = np.array([0.0, 0.0, 1.0])
    N = np.cross(T, up)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    B = np.cross(T, N)
    obs = []
    for k in range(3):
        ph = u / 0.011 * 2 * math.pi + k * 2 * math.pi / 3
        S = C + 0.0029 * (np.cos(ph)[:, None] * N + np.sin(ph)[:, None] * B)
        ob = tube(f'RopeStrand{k}', [tuple(p) for p in S], 0.0031, n=8, col=COL)
        ob.data.materials.append(mat)
        obs.append(ob)
    return obs


def hook(name, c, ang, size, steel):
    """Amo a J: gambo dritto, curva, punta con l'ardiglione e l'occhiello."""
    pts = [(0, size * 0.95 * (1 - t), 0) for t in np.linspace(0, 1, 18)]
    curve = []
    for t in np.linspace(0, math.pi * 1.05, 22):
        curve.append((size * 0.28 * (1 - math.cos(t)), -size * 0.28 * math.sin(t), 0))
    pts = pts + curve[1:]
    ca, sa = math.cos(ang), math.sin(ang)
    P = [(c[0] + x * ca - y * sa, c[1] + x * sa + y * ca, 0.004) for x, y, _ in pts]
    ob = tube(name, P, size * 0.03, n=6, col=COL)
    ob.data.materials.append(steel)
    eye = tube(name + 'Eye', [(P[0][0] + size * 0.03 * math.cos(t), P[0][1] + size * 0.03 * math.sin(t), 0.004)
                              for t in np.linspace(0, 2 * math.pi, 16)], size * 0.02, n=6, col=COL)
    eye.data.materials.append(steel)
    return [ob, eye], P[0]


def pencil(c, ang, wood, paint, lead):
    L, r = 0.075, 0.0045
    ca, sa = math.cos(ang), math.sin(ang)
    d = Vector((ca, sa, 0))
    base = Vector((c[0], c[1], r))
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r, depth=L, location=base + d * (L / 2))
    body = link(bpy.context.object, COL)
    body.rotation_euler = (0, math.pi / 2, ang)
    body.data.materials.append(paint)
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=r, radius2=0.0009, depth=0.016, location=base + d * (L + 0.008))
    tip = link(bpy.context.object, COL)
    tip.rotation_euler = (0, math.pi / 2, ang)
    tip.data.materials.append(wood)
    bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=0.0011, radius2=0.0, depth=0.004, location=base + d * (L + 0.0175))
    gr = link(bpy.context.object, COL)
    gr.rotation_euler = (0, math.pi / 2, ang)
    gr.data.materials.append(lead)
    return [body, tip, gr]


def build(rng):
    obs = []
    obs += planks(rng, wood_material())
    rope = simple('Rope', (0.42, 0.34, 0.22), rough=0.85, noise=0.6, scale=180.0)
    steel = simple('Steel', (0.62, 0.6, 0.56), rough=0.18, metal=1.0)
    line = simple('Line', (0.75, 0.78, 0.74), rough=0.2)
    obs += rope_coil(rng, (-0.385, -0.205), rope)
    # ami e un pezzo di lenza, in alto a destra
    for k, (x, y, a, s) in enumerate(((0.335, 0.15, 0.6, 0.05), (0.39, 0.105, -0.9, 0.042), (0.31, 0.09, 2.4, 0.046))):
        hs, eye = hook(f'Hook{k}', (x, y), a, s, steel)
        obs += hs
        if k == 0:
            pts = [eye] + [(eye[0] - 0.02 * t - 0.008 * math.sin(t * 2), eye[1] + 0.05 * t, 0.002) for t in np.linspace(0.05, 1.8, 24)]
            ob = tube('Line', pts, 0.0005, n=5, col=COL)
            ob.data.materials.append(line)
            obs.append(ob)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0065, location=(0.395, 0.17, 0.0065), segments=16, ring_count=10)
    lead = link(bpy.context.object, COL)
    lead.scale = (1.0, 1.0, 0.8)
    lead.data.materials.append(simple('Lead', (0.2, 0.2, 0.21), rough=0.55, metal=0.6, noise=0.3, scale=90.0))
    obs.append(lead)
    obs += pencil((0.33, -0.2), 2.75, simple('PencilWood', (0.55, 0.38, 0.22), rough=0.7),
                  simple('PencilPaint', (0.3, 0.035, 0.03), rough=0.45), simple('Graphite', (0.05, 0.05, 0.05), rough=0.35, metal=0.4))
    # le tacche incise sul banco a contare le notti (GDD), sul bordo sinistro
    cut = simple('Cut', (0.03, 0.017, 0.01), rough=0.9)
    x0, y0 = -0.395, 0.035
    for grp in range(3):
        gx = x0 + grp * 0.027
        for k in range(4):
            ob = rbox(f'Tally{grp}_{k}', (0.0016, 0.022, 0.004), (gx + k * 0.0042, y0 + rng.uniform(-0.001, 0.001), 0.0),
                      rot=(0, 0, rng.uniform(-0.06, 0.06)), bevel=0.0, col=COL)
            ob.data.materials.append(cut)
            obs.append(ob)
        ob = rbox(f'Tally{grp}_x', (0.0016, 0.026, 0.004), (gx + 0.0063, y0, 0.0), rot=(0, 0, -1.05), bevel=0.0, col=COL)
        ob.data.materials.append(cut)
        obs.append(ob)
    # gocce d'acqua e scaglie sparse ai bordi (il centro lo copre il libro)
    drop = glass_drop()
    scl = scale_material()

    def edge_point():
        while True:
            x, y = rng.uniform(-W_M / 2, W_M / 2), rng.uniform(-H_M / 2, H_M / 2)
            if abs(x) > 0.30 or abs(y) > 0.19:
                return x, y

    for i in range(16):
        x, y = edge_point()
        r = rng.uniform(0.0025, 0.006)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, r * 0.25), segments=16, ring_count=8)
        d = link(bpy.context.object, COL)
        d.scale = (rng.uniform(1.0, 1.6), 1.0, 0.22)
        d.rotation_euler = (0, 0, rng.uniform(0, math.pi))
        d.data.materials.append(drop)
        obs.append(d)
    for i in range(14):
        x, y = edge_point()
        r = rng.uniform(0.003, 0.005)
        bpy.ops.mesh.primitive_circle_add(vertices=14, radius=r, fill_type='NGON', location=(x, y, 0.0015))
        s = link(bpy.context.object, COL)
        s.rotation_euler = (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(0, math.pi))
        s.scale = (1.0, rng.uniform(0.75, 0.95), 1.0)
        s.data.materials.append(scl)
        obs.append(s)
    return obs


def lights():
    from dettagli import area_light
    # la lanterna: in alto a sinistra, calda; la luna: fredda e debole da destra
    ld = bpy.data.lights.new('Lantern', 'POINT')
    ld.energy = 5.5
    ld.color = (1.0, 0.6, 0.3)
    ld.shadow_soft_size = 0.05
    ob = bpy.data.objects.new('Lantern', ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (-0.34, 0.25, 0.32)
    area_light('Moon', (0.7, -0.15, 0.7), (0.0, 0.0, 0.0), 1.2, (0.55, 0.68, 1.0), 0.5)


def camera():
    cd = bpy.data.cameras.new('Cam')
    cd.type = 'ORTHO'
    cd.ortho_scale = W_M
    cam = bpy.data.objects.new('Cam', cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (0, 0, 1.5)
    cam.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera = cam


def main():
    t0 = time.time()
    sc = reset_scene()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    w = bpy.data.worlds.new('Night')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.02, 0.026, 0.036, 1)
    rng = np.random.default_rng(23)
    build(rng)
    lights()
    camera()
    W, H = (1280, 720) if FAST else (2560, 1440)
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 16 if FAST else 96
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'PNG'
    os.makedirs(os.path.join(CACHE, 'catalogo'), exist_ok=True)
    png = os.path.join(CACHE, 'catalogo', 'sfondo.png')
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    os.makedirs(OUT, exist_ok=True)
    Image.open(png).convert('RGB').save(os.path.join(OUT, 'sfondo.webp'), quality=84, method=6)
    log('catalogo sfondo', round(time.time() - t0), 's', f'{W}x{H}')


if __name__ == '__main__':
    main()
