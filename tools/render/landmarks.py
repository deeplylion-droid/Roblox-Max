"""
I luoghi sull'orizzonte della baia (come gli oggetti di scena dell'ufficio di FNAF):

  alle spalle  Splashland: statua di Mama Marina, insegna al neon, torre degli scivoli, piscina
               "Deep End" con le luci ancora accese, Snack Shack, torretta del bagnino, palme morte,
               ruota panoramica ferma sul vecchio pontile
  davanti      relitto di un peschereccio, boa con campana e luce verde
  a destra     traliccio radio con la luce rossa, albergo abbandonato con una finestra accesa
  a sinistra   edicola votiva su uno scoglio con un lume, gabbie di un allevamento ittico

build_landmarks() restituisce le posizioni delle luci che il motore anima (lampeggi, sfarfallii).
"""
from __future__ import annotations

import math

import bpy
import numpy as np

import env
import mascot
from common import collection, link, mesh_from_arrays, set_lightgroup
from geo import catmull, circle_profile, lathe, rbox, rect_profile, sphere, sweep, tube
from nodes import material

COL = 'env'


def P(yaw, dist, z=0.0):
    a = math.radians(yaw)
    return (dist * math.sin(a), dist * math.cos(a), z)


def facing(pos):
    """Yaw (gradi) da dare a un oggetto modellato con la faccia verso −Y perché guardi la barca."""
    return math.degrees(math.atan2(-pos[0], pos[1]))


def mat_cache(name, build):
    m = bpy.data.materials.get(name)
    return m if m else build(name)


def painted(name, color, rust=0.35, rough=0.55, metal=0.0, rust_scale=3.0):
    def b(n):
        m, g = material(n)
        co = g.texcoord('Object')
        r = g.smoothstep(1.0 - rust, 1.0 - rust + 0.08, g.noise(co, scale=rust_scale, detail=6.0, rough=0.65, distortion=0.4).fac)
        streak = g.noise(g.mapping(co, scale=(8.0, 8.0, 0.6)), scale=1.0, detail=4.0).fac
        col = g.mix(g.mul(g.smoothstep(0.55, 0.75, streak), 0.6), color, (0.18, 0.07, 0.03))
        col = g.mix(r, col, (0.16, 0.06, 0.025))
        g.output_material(g.principled(color=col, rough=g.mixf(r, rough, 0.9), metal=g.mixf(r, metal, 0.0),
                                       normal=g.bump(g.noise(co, scale=12.0, detail=4.0).fac, strength=0.2, distance=0.02)))
        return m
    return mat_cache(name, b)


def emissive(name, color, strength):
    def b(n):
        m, g = material(n)
        g.output_material(g.emission(color, strength))
        return m
    return mat_cache(name, b)


def point_light(name, loc, energy, color, radius=0.1):
    d = bpy.data.lights.new(name, 'POINT')
    d.energy = energy
    d.color = color
    d.shadow_soft_size = radius
    o = bpy.data.objects.new(name, d)
    collection(COL).objects.link(o)
    o.location = loc
    set_lightgroup(o, 'ambient')
    return o


def finish(obs):
    for o in obs:
        if o.type in ('MESH', 'CURVE', 'FONT'):
            set_lightgroup(o, 'ambient')
            if o.users_collection and o.users_collection[0].name != COL:
                link(o, COL)
    return obs


def transform(obs, loc, yaw_deg=0.0, pitch=0.0, roll=0.0, scale=1.0):
    from mathutils import Euler, Matrix
    bpy.context.view_layer.update()   # matrix_world deve riflettere posizione/scala appena impostate
    M = Matrix.Translation(loc) @ Euler((math.radians(pitch), math.radians(roll), math.radians(yaw_deg)), 'XYZ').to_matrix().to_4x4() @ Matrix.Scale(scale, 4)
    for o in obs:
        o.matrix_world = M @ o.matrix_world
    return obs


def text_obj(name, body, size, loc, rot_z, mat, extrude=0.25):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = size * 0.02
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    ob = bpy.data.objects.new(name, cu)
    collection(COL).objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, rot_z)
    ob.data.materials.append(mat)
    set_lightgroup(ob, 'ambient')
    return ob


# ───────────────────────── Splashland ─────────────────────────

def ground(yaw, s):
    return env.surface_at(yaw, s)


def build_splashland(lights):
    obs = []
    # statua di Mama Marina sulla battigia, rivolta verso la baia
    x, y, z = ground(180.0, 10.0)
    obs += mascot.build_statue((x, y, z + 0.2), facing((x, y, z)), height=22.0)
    rz0 = math.radians(facing((x, y, z)))
    for k, (side, col) in enumerate(((-1, (0.25, 1.0, 0.75)), (1, (1.0, 0.30, 0.45)))):
        sd = bpy.data.lights.new(f'MarinaFlood{k}', 'SPOT')
        sd.energy = 90000
        sd.color = col
        sd.spot_size = math.radians(40)
        sd.spot_blend = 0.5
        so = bpy.data.objects.new(f'MarinaFlood{k}', sd)
        collection(COL).objects.link(so)
        so.location = (x + side * 9 * math.cos(rz0) + 12 * math.sin(rz0), y + side * 9 * math.sin(rz0) - 12 * math.cos(rz0), z + 0.5)
        from mathutils import Vector
        so.rotation_mode = 'QUATERNION'
        so.rotation_quaternion = (Vector((x, y, z + 13)) - Vector(so.location)).to_track_quat('-Z', 'Y')
        set_lightgroup(so, 'ambient')
    lights['marina'] = (x, y, z + 14.0)

    # ingresso art déco: due piloni a gradoni, raggiera e insegna al neon in Limelight
    import deco
    yaw, s_ = 167.0, 55.0
    x, y, z = ground(yaw, s_)
    rz = math.radians(facing((x, y, z)))
    cream = deco.deco_paint('GateCream', (0.62, 0.56, 0.44), grime=0.45)
    teal = deco.deco_paint('GateTeal', (0.10, 0.32, 0.32), grime=0.35)
    for side in (-1, 1):
        px = x + side * 21 * math.cos(rz)
        py = y + side * 21 * math.sin(rz)
        tob, top = deco.stepped_tower(f'GatePylon{side}', (px, py, z - 1), rz, (7.0, 7.0), 30.0, steps=4, shrink=0.78, mat=cream, fins=3, fin_mat=teal)
        obs += tob
        cap = neon_ball = sphere(f'GatePylonGlobe{side}', 1.2, (px, py, top + 1.0), segs=16, rings=8, col=COL)
        cap.data.materials.append(deco.neon_material('GateGlobe', (0.20, 0.95, 0.90), 18.0))
        obs.append(cap)
    beam = rbox('GateBeam', (46.0, 2.0, 3.0), (x, y, z + 15.5), rot=(0, 0, rz), bevel=0.3, col=COL)
    beam.data.materials.append(teal)
    obs.append(beam)
    obs += deco.sunburst('GateSun', (x + 1.2 * math.sin(rz), y - 1.2 * math.cos(rz), z + 17.0), rz, 14.0, rays=15, spread=170, width=0.05,
                         mat=deco.deco_paint('SunGold', (0.55, 0.40, 0.10), grime=0.3, rough=0.35))
    sign = deco.neon_text('SplashSign', 'SPLASHLAND', 6.5, (x + 1.6 * math.sin(rz), y - 1.6 * math.cos(rz), z + 21.0), rz,
                          deco.neon_material('NeonPink', (1.0, 0.22, 0.55), 10.0), extrude=0.35)
    sign.data.materials.append(deco.neon_material('NeonPinkDim', (1.0, 0.22, 0.55), 0.8))
    sign.data.materials.append(deco.deco_paint('NeonDead', (0.18, 0.06, 0.10), grime=0.2, rough=0.3))
    for i, st in enumerate('LLLLDLLLXL'):         # la seconda S è fioca, la N è morta
        sign.data.body_format[i].material_index = {'L': 0, 'D': 1, 'X': 2}[st]
    obs.append(sign)
    sub = deco.neon_text('SplashSub', "MAMA MARINA'S", 2.2, (x + 1.6 * math.sin(rz), y - 1.6 * math.cos(rz), z + 26.5), rz,
                         deco.neon_material('NeonCyan', (0.15, 0.95, 0.90), 8.0), extrude=0.2)
    obs.append(sub)
    lights['neon'] = (x, y, z + 21.0)
    point_light('NeonGlow', (x + 4 * math.sin(rz), y - 4 * math.cos(rz), z + 21), 26000, (1.0, 0.25, 0.55), radius=6.0)
    frame = painted('SignFrame', (0.55, 0.55, 0.58), rust=0.45, metal=0.6)

    # torre degli scivoli con tubi colorati sbiaditi
    yaw, s = 193.0, 45.0
    x, y, z = ground(yaw, s)
    steel = painted('TowerSteel', (0.62, 0.62, 0.60), rust=0.5, metal=0.5)
    H = 24.0
    for cx in (-3, 3):
        for cy in (-3, 3):
            obs.append(tube('TowerLeg', [(x + cx, y + cy, z - 1), (x + cx * 0.85, y + cy * 0.85, z + H)], 0.22, n=8, col=COL))
            obs[-1].data.materials.append(steel)
    for k in range(1, 6):
        zz = z + k * H / 5.5
        ring = sweep('TowerRing', [(x - 3, y - 3, zz), (x + 3, y - 3, zz), (x + 3, y + 3, zz), (x - 3, y + 3, zz), (x - 3, y - 3, zz)],
                     rect_profile(0.25, 0.25), col=COL)
        ring.data.materials.append(steel)
        obs.append(ring)
    roof = lathe('TowerRoof', [(5.0, 0.0), (0.2, 4.5)], n=4, col=COL)
    roof.location = (x, y, z + H)
    roof.rotation_euler = (0, 0, math.pi / 4)
    roof.data.materials.append(painted('RoofPaint', (0.55, 0.10, 0.08), rust=0.3))
    obs.append(roof)
    colors = [(0.75, 0.62, 0.10), (0.10, 0.35, 0.65), (0.65, 0.12, 0.10), (0.15, 0.50, 0.30)]
    for k, c in enumerate(colors):
        a0 = k * math.pi / 2
        turns = 1.6 + 0.3 * k
        pts = []
        for t in np.linspace(0, 1, 90):
            a = a0 + t * turns * 2 * math.pi
            r = 7.0 + 3.0 * t
            pts.append((x + r * math.cos(a), y + r * math.sin(a), z + H - 1.5 - t * (H - 3.0)))
        if k == 2:
            pts = pts[:52]   # tubo spezzato: finisce nel vuoto
        tubeob = tube(f'Slide{k}', pts, 0.85, n=14, col=COL)
        tubeob.data.materials.append(painted(f'SlidePaint{k}', c, rust=0.25, rough=0.35))
        obs.append(tubeob)

    # piscina Deep End: acqua con le luci accese
    yaw, s = 175.5, 22.0
    x, y, z = ground(yaw, s)
    rz = math.radians(facing((x, y, z)))
    rimm = painted('PoolTiles', (0.55, 0.65, 0.68), rust=0.2)
    rim = rbox('PoolRim', (32, 15, 1.2), (x, y, z - 0.2), rot=(0, 0, rz), bevel=0.1, col=COL)
    rim.data.materials.append(rimm)
    obs.append(rim)

    def pool_mat(n):
        m, g = material(n)
        co = g.texcoord('Object')
        caus = g.voronoi(co, scale=0.35, feature='SMOOTH_F1', out='Distance')
        e = g.add(1.6, g.mul(g.smoothstep(0.3, 0.0, caus), 2.5))
        g.output_material(g.add_shader(g.principled(color=(0.0, 0.05, 0.05), rough=0.05), g.emission((0.15, 0.95, 0.80), e)))
        return m
    water = rbox('DeepEndWater', (30, 13, 0.1), (x, y, z + 0.45), rot=(0, 0, rz), bevel=0.0, col=COL)
    water.data.materials.append(mat_cache('DeepEndWaterMat', pool_mat))
    obs.append(water)
    for k in (-1, 1):
        point_light(f'DeepEndLight{k}', (x + k * 8 * math.cos(rz), y + k * 8 * math.sin(rz), z + 2.5), 9000, (0.15, 0.95, 0.80), radius=3.0)
    lights['deepEnd'] = (x, y, z + 1.0)

    # Snack Shack con l'insegna a forma di pesce
    yaw, s = 186.0, 30.0
    x, y, z = ground(yaw, s)
    rz = math.radians(facing((x, y, z)))
    shack = rbox('SnackShack', (9, 6, 4.5), (x, y, z + 2.2), rot=(0, 0, rz), bevel=0.15, col=COL)
    shack.data.materials.append(painted('ShackPaint', (0.70, 0.62, 0.40), rust=0.35))
    obs.append(shack)
    fish = sphere('ShackFish', 1.0, (x, y, z + 8.5), segs=24, rings=12, col=COL, scale=(4.0, 0.6, 1.4))
    fish.rotation_euler = (0, 0, rz)
    fish.data.materials.append(painted('ShackFishPaint', (0.85, 0.45, 0.10), rust=0.3))
    obs.append(fish)
    for k in (-1, 1):
        obs.append(tube('ShackPole', [(x + k * 2 * math.cos(rz), y + k * 2 * math.sin(rz), z + 4.5), (x + k * 2 * math.cos(rz), y + k * 2 * math.sin(rz), z + 7.5)], 0.12, n=6, col=COL))
        obs[-1].data.materials.append(frame)

    # torretta del bagnino sulla battigia
    x, y, z = ground(178.5, 3.0)
    wood = painted('LifeguardWood', (0.75, 0.70, 0.62), rust=0.25)
    for cx in (-0.9, 0.9):
        for cy in (-0.9, 0.9):
            obs.append(tube('LgLeg', [(x + cx, y + cy, z - 0.5), (x + cx * 0.5, y + cy * 0.5, z + 3.2)], 0.08, n=6, col=COL))
            obs[-1].data.materials.append(wood)
    seat = rbox('LgSeat', (1.3, 1.3, 0.15), (x, y, z + 3.2), bevel=0.03, col=COL)
    seat.data.materials.append(wood)
    obs.append(seat)
    obs.append(tube('LgUmbrellaPole', [(x, y, z + 3.2), (x + 0.3, y, z + 6.0)], 0.04, n=6, col=COL))
    obs[-1].data.materials.append(frame)
    umb = lathe('LgUmbrella', [(0.05, 0.0), (1.6, -0.6), (1.7, -0.75)], n=12, col=COL)
    umb.location = (x + 0.3, y, z + 6.1)
    umb.rotation_euler = (0.25, -0.15, 0)
    umb.data.materials.append(painted('UmbrellaPaint', (0.75, 0.18, 0.12), rust=0.4))
    obs.append(umb)

    # palme morte lungo la spiaggia
    trunk_m = painted('PalmTrunk', (0.20, 0.15, 0.10), rust=0.0, rough=0.9)
    frond_m = painted('PalmFrond', (0.16, 0.13, 0.07), rust=0.0, rough=0.9)
    rr = np.random.default_rng(31)
    for k, yaw in enumerate((160, 163.5, 170, 189, 196.5, 199)):
        x, y, z = ground(yaw, 14 + rr.uniform(0, 20))
        h = rr.uniform(8, 11)
        lean = rr.uniform(-0.25, 0.25)
        top = (x + h * lean, y + rr.uniform(-1, 1), z + h)
        pts = catmull([(x, y, z - 0.5), (x + h * lean * 0.3, y, z + h * 0.5), top], 8)
        obs.append(tube(f'Palm{k}', pts, 0.28, n=8, col=COL, taper=0.6))
        obs[-1].data.materials.append(trunk_m)
        for f in range(7):
            a = 2 * math.pi * f / 7 + rr.uniform(-0.3, 0.3)
            droop = rr.uniform(2.5, 4.5)
            fp = [top, (top[0] + 1.8 * math.cos(a), top[1] + 1.8 * math.sin(a), top[2] + 0.4),
                  (top[0] + 3.2 * math.cos(a), top[1] + 3.2 * math.sin(a), top[2] - droop)]
            fr = sweep(f'Frond{k}_{f}', catmull(fp, 6), rect_profile(0.7, 0.05), col=COL, scale=np.linspace(1.0, 0.2, 13))
            fr.data.materials.append(frond_m)
            obs.append(fr)
    return obs


def build_ferris_wheel(lights):
    obs = []
    yaw = -158.0
    sx, sy, sz = ground(yaw, 0.0)
    d_shore = math.hypot(sx, sy)
    # pontile: dalla riva verso la barca
    deck_m = painted('PierDeck', (0.30, 0.26, 0.20), rust=0.0, rough=0.85)
    L = 55.0
    ux, uy = -sx / d_shore, -sy / d_shore
    cx, cy = sx + ux * L / 2, sy + uy * L / 2
    rz = math.atan2(uy, ux) - math.pi / 2
    deck = rbox('Pier', (7, L, 0.6), (cx, cy, 2.6), rot=(0, 0, rz), bevel=0.05, col=COL)
    deck.data.materials.append(deck_m)
    obs.append(deck)
    for k in range(10):
        t = k / 9
        for side in (-1, 1):
            px = sx + ux * L * t + side * 3.0 * math.cos(rz)
            py = sy + uy * L * t + side * 3.0 * math.sin(rz)
            obs.append(tube('PierPile', [(px, py, -4), (px, py, 2.4)], 0.25, n=8, col=COL))
            obs[-1].data.materials.append(deck_m)
    # la ruota, col piano rivolto verso la barca
    hx, hy, hz = sx + ux * (L - 8), sy + uy * (L - 8), 2.6 + 18.0
    R = 15.0
    frame = painted('WheelFrame', (0.80, 0.78, 0.72), rust=0.45, metal=0.4, rust_scale=6.0)
    # asse del piano: perpendicolare alla direzione verso la barca
    px, py = -uy, ux   # direzione orizzontale nel piano della ruota

    def wp(a, r):
        return (hx + r * math.cos(a) * px, hy + r * math.cos(a) * py, hz + r * math.sin(a))
    for r_, t_ in ((R, 0.28), (R - 1.4, 0.18)):
        ring = [wp(2 * math.pi * k / 96, r_) for k in range(97)]
        obs.append(tube('WheelRim', ring, t_, n=8, col=COL))
        obs[-1].data.materials.append(frame)
    n_sp = 16
    for k in range(n_sp):
        a = 2 * math.pi * k / n_sp
        obs.append(tube('Spoke', [wp(a, 0.6), wp(a, R)], 0.10, n=6, col=COL))
        obs[-1].data.materials.append(frame)
    hub = sphere('WheelHub', 1.0, (hx, hy, hz), segs=16, rings=8, col=COL)
    hub.data.materials.append(frame)
    obs.append(hub)
    for side in (-1, 1):
        for lean in (-1, 1):
            base = (hx + side * 2.0 * ux + lean * 7.0 * px, hy + side * 2.0 * uy + lean * 7.0 * py, 2.9)
            obs.append(tube('WheelLeg', [base, (hx + side * 0.8 * ux, hy + side * 0.8 * uy, hz)], 0.30, n=8, col=COL))
            obs[-1].data.materials.append(frame)
    gcols = [(0.70, 0.12, 0.10), (0.75, 0.62, 0.12), (0.10, 0.32, 0.62), (0.12, 0.55, 0.35)]
    missing = {3, 7, 12}
    for k in range(n_sp):
        if k in missing:
            continue
        a = 2 * math.pi * k / n_sp + math.pi / n_sp
        ax, ay, az = wp(a, R)
        tilt = 0.6 if k == 10 else 0.0       # una cabina appesa storta
        cab = rbox(f'Gondola{k}', (1.7, 1.7, 1.6), (ax, ay, az - 1.7), rot=(0, tilt, math.atan2(py, px)), bevel=0.25, col=COL)
        cab.data.materials.append(painted(f'GondolaPaint{k % 4}', gcols[k % 4], rust=0.4, rough=0.4))
        obs.append(cab)
        obs.append(tube('GondolaArm', [(ax, ay, az), (ax, ay, az - 0.9)], 0.06, n=5, col=COL))
        obs[-1].data.materials.append(frame)
    # una lampadina ancora accesa sul cerchio
    bx, by, bz = wp(math.radians(70), R)
    b = sphere('WheelBulb', 0.35, (bx, by, bz), segs=8, rings=6, col=COL)
    b.data.materials.append(emissive('WheelBulbMat', (1.0, 0.75, 0.40), 25.0))
    obs.append(b)
    lights['wheelBulb'] = (bx, by, bz)
    lights['wheelHub'] = (hx, hy, hz)
    return obs


# ───────────────────────── davanti ─────────────────────────

def build_wreck(lights):
    import boat
    obs = []
    yaw, dist = 14.0, 170.0
    cx, cy, _ = P(yaw, dist)
    S = 3.4
    verts, faces = [], []
    ny, ns = 60, 18
    for i, t in enumerate(np.linspace(-0.98, 0.98, ny)):
        for k in range(-ns, ns + 1):
            s_ = abs(k) / ns
            x, y, z = boat.hull_point(t, s_, 1.0 if k >= 0 else -1.0)
            verts.append((float(x) * S, float(y) * S, float(z) * S))
    m = 2 * ns + 1
    for i in range(ny - 1):
        for j in range(m - 1):
            a = i * m + j
            faces.append((a, a + m, a + m + 1, a + 1))
    hull = mesh_from_arrays('WreckHull', np.array(verts), faces, smooth=True, col=COL)
    so = hull.modifiers.new('T', 'SOLIDIFY')
    so.thickness = 0.12
    rusty = painted('WreckRust', (0.22, 0.20, 0.18), rust=0.65, metal=0.3, rust_scale=1.5)
    hull.data.materials.append(rusty)
    obs.append(hull)
    house = rbox('WreckHouse', (3.6, 3.0, 2.8), (0, -2.5, 2.9), bevel=0.15, col=COL)
    house.data.materials.append(painted('WreckHousePaint', (0.55, 0.52, 0.46), rust=0.55))
    obs.append(house)
    obs.append(tube('WreckMast', [(0, 1.5, 2.2), (0, 2.0, 11.0)], 0.18, n=8, col=COL))
    obs[-1].data.materials.append(rusty)
    obs.append(tube('WreckBoom', [(0, 2.0, 8.5), (2.5, 4.5, 6.0)], 0.10, n=6, col=COL))
    obs[-1].data.materials.append(rusty)
    for side in (-1, 1):
        obs.append(tube('WreckGantry', [(side * 2.2, -8.0, 1.5), (side * 1.6, -8.6, 6.0), (-side * 1.6, -8.6, 6.0)], 0.15, n=6, col=COL))
        obs[-1].data.materials.append(rusty)
    # cavi del sartiame
    for a, b in (((0, 2.0, 11.0), (0, 8.5, 2.6)), ((0, 2.0, 11.0), (-1.5, -2.0, 4.0))):
        obs.append(tube('WreckStay', [a, b], 0.025, n=4, col=COL))
        obs[-1].data.materials.append(rusty)
    # affondato di poppa, prua fuori dall'acqua, sbandato
    transform(obs, (cx, cy, -2.6), yaw_deg=-yaw + 25, pitch=24, roll=-14)
    return obs


def build_buoy(lights):
    obs = []
    x, y, _ = P(38.0, 70.0)
    green = painted('BuoyGreen', (0.05, 0.30, 0.12), rust=0.4, rough=0.5)
    fl = lathe('BuoyFloat', [(0.0, -1.0), (1.1, -0.9), (1.2, 0.0), (1.1, 0.55), (0.0, 0.62)], n=24, col=COL)
    fl.data.materials.append(green)
    obs.append(fl)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        obs.append(tube('BuoyCage', [(0.8 * math.cos(a), 0.8 * math.sin(a), 0.5), (0.25 * math.cos(a), 0.25 * math.sin(a), 3.6)], 0.05, n=6, col=COL))
        obs[-1].data.materials.append(green)
    bell = lathe('BuoyBell', [(0.0, 2.5), (0.12, 2.48), (0.22, 2.3), (0.30, 1.95), (0.33, 1.9)], n=20, col=COL)
    bell.data.materials.append(painted('BuoyBellBronze', (0.40, 0.28, 0.12), rust=0.3, metal=0.9, rough=0.4))
    obs.append(bell)
    lamp = sphere('BuoyLamp', 0.18, (0, 0, 3.8), segs=12, rings=8, col=COL)
    lamp.data.materials.append(emissive('BuoyLampMat', (0.2, 1.0, 0.35), 18.0))
    obs.append(lamp)
    transform(obs, (x, y, 0.0), yaw_deg=10, pitch=4, roll=-6)
    point_light('BuoyLight', (x, y, 3.9), 60, (0.2, 1.0, 0.35), radius=0.15)
    lights['buoy'] = (x, y, 3.8)
    return obs


# ───────────────────────── a destra ─────────────────────────

def build_radio_mast(lights):
    obs = []
    x, y, z = ground(100.0, 320.0)
    H = 46.0
    steel = painted('MastSteel', (0.55, 0.50, 0.48), rust=0.5, metal=0.5)
    legs = []
    for k in range(3):
        a = 2 * math.pi * k / 3
        legs.append(((x + 4 * math.cos(a), y + 4 * math.sin(a), z - 1), (x + 0.4 * math.cos(a), y + 0.4 * math.sin(a), z + H)))
    for a, b in legs:
        obs.append(tube('MastLeg', [a, b], 0.25, n=6, col=COL))
        obs[-1].data.materials.append(steel)
    for k in range(1, 10):
        t = k / 10
        ring = []
        for a, b in legs + [legs[0]]:
            ring.append(tuple(np.array(a) * (1 - t) + np.array(b) * t))
        obs.append(tube('MastBrace', ring, 0.08, n=4, col=COL, cap=False))
        obs[-1].data.materials.append(steel)
    red = emissive('MastRed', (1.0, 0.05, 0.03), 60.0)
    for zz, key in ((H + 0.6, 'mastTop'), (H * 0.55, 'mastMid')):
        o = sphere('MastLight', 0.45, (x, y, z + zz), segs=8, rings=6, col=COL)
        o.data.materials.append(red)
        obs.append(o)
        lights[key] = (x, y, z + zz)
    return obs


def build_hotel(lights):
    """Albergo Miramare in stile streamline: corpo lungo con un'estremità tonda, fasce orizzontali,
    insegna verticale al neon (metà lettere morte), coronamento a gradoni. Una sola finestra accesa."""
    import deco
    obs = []
    yaw, s_ = 124.0, 45.0
    x, y, z = ground(yaw, s_)
    rz = math.radians(facing((x, y, z)))
    wall = env.house_material('HotelWall', (0.58, 0.54, 0.46), lit_ratio=0.0)
    body = rbox('Hotel', (48, 18, 27), (x, y, z + 13.5), rot=(0, 0, rz), bevel=0.3, col=COL)
    body.data.materials.append(wall)
    obs.append(body)
    ex, ey = x + 24 * math.cos(rz), y + 24 * math.sin(rz)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=9.0, depth=27, location=(ex, ey, z + 13.5))
    rnd = link(bpy.context.object, COL)
    rnd.data.materials.append(wall)
    obs.append(rnd)
    slab = deco.deco_paint('HotelBands', (0.36, 0.34, 0.31), grime=0.45)
    for k in range(1, 8):
        b_ = rbox('HotelBand', (49.0, 19.2, 0.45), (x, y, z + k * 3.4), rot=(0, 0, rz), bevel=0.1, col=COL)
        b_.data.materials.append(slab)
        obs.append(b_)
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=9.6, depth=0.45, location=(ex, ey, z + k * 3.4))
        rb = link(bpy.context.object, COL)
        rb.data.materials.append(slab)
        obs.append(rb)
    tob, top = deco.stepped_tower('HotelCrown', (x - 10 * math.cos(rz), y - 10 * math.sin(rz), z + 27), rz, (14.0, 10.0), 9.0, steps=3, shrink=0.7, mat=wall, fins=3, fin_mat=slab)
    obs += tob
    # insegna verticale sulla curva
    bx, by = ex + 9.4 * math.sin(rz), ey - 9.4 * math.cos(rz)
    blade = rbox('HotelBlade', (1.4, 0.8, 24.0), (bx, by, z + 17.0), rot=(0, 0, rz), bevel=0.15, col=COL)
    blade.data.materials.append(deco.deco_paint('BladeDark', (0.08, 0.06, 0.08), grime=0.3))
    obs.append(blade)
    sign = deco.neon_text('HotelSign', 'MIRAMARE', 2.6, (bx + 0.6 * math.sin(rz), by - 0.6 * math.cos(rz), z + 17.0), rz,
                          deco.neon_material('NeonRed', (1.0, 0.10, 0.08), 12.0), vertical=True, extrude=0.15)
    sign.data.materials.append(deco.deco_paint('NeonDeadRed', (0.16, 0.05, 0.05), grime=0.2, rough=0.3))
    for i, st in enumerate('LXLLXLXL'):
        sign.data.body_format[i if i == 0 else i * 2].material_index = 0 if st == 'L' else 1
    obs.append(sign)
    lights['hotelSign'] = (bx, by, z + 17.0)
    # l'unica finestra accesa
    win = rbox('HotelLitWindow', (1.6, 0.2, 2.0), (x + 12 * math.cos(rz) + 9.2 * math.sin(rz), y + 12 * math.sin(rz) - 9.2 * math.cos(rz), z + 5 * 3.4 + 1.6), rot=(0, 0, rz), bevel=0.0, col=COL)
    win.data.materials.append(emissive('HotelWindowMat', (1.0, 0.70, 0.35), 14.0))
    obs.append(win)
    lights['hotelWindow'] = tuple(win.location)
    return obs


# ───────────────────────── a sinistra ─────────────────────────

def skull_mesh():
    """Teschio stilizzato (usato in copie collegate)."""
    import sdf as S
    from creature import sdf_object
    me = bpy.data.meshes.get('SkullMesh')
    if me:
        return me
    cran = S.ellipsoid((0, 0.01, 0.03), (0.075, 0.09, 0.08))
    face = S.ellipsoid((0, -0.045, -0.02), (0.06, 0.05, 0.06))
    jaw = S.box((0, -0.05, -0.075), (0.042, 0.035, 0.02), 0.015)
    f = S.union(cran, face, jaw, k=0.02)
    f = S.subtract(f, S.union(S.sphere((0.027, -0.09, 0.0), 0.022), S.sphere((-0.027, -0.09, 0.0), 0.022),
                              S.round_cone((0, -0.095, -0.035), (0, -0.085, -0.02), 0.012, 0.006)), k=0.006)
    ob = sdf_object('SkullProto', f, (-0.1, -0.15, -0.12), (0.1, 0.12, 0.13), res=0.004, col=COL)
    me = ob.data
    me.name = 'SkullMesh'
    m, g = material('SkullBone')
    co = g.texcoord('Object')
    n = g.noise(co, scale=40.0, detail=4.0).fac
    g.output_material(g.principled(color=g.mix(g.mul(n, 0.5), (0.62, 0.56, 0.44), (0.30, 0.24, 0.16)), rough=0.6))
    me.materials.append(m)
    bpy.data.objects.remove(ob)
    return me


def build_chapel(lights):
    """Edicola votiva su uno scoglio, con il muro dei teschi (il culto delle anime del purgatorio)
    e una distesa di lumini rossi. Il tocco folk alla Grim Fandango."""
    import deco
    obs = []
    x, y, _ = P(-74.0, 92.0)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=1.0, location=(x, y, 0))
    rock = link(bpy.context.object, COL)
    rock.name = 'ChapelRock'
    for v in rock.data.vertices:
        c = np.array(v.co)
        n = env.value_noise_2d(np.array([c[0] * 3 + c[2]]), np.array([c[1] * 3 - c[2]]), 61, 0.7, 4)[0]
        v.co = v.co * (1 + 0.35 * n)
    rock.scale = (7.0, 6.0, 4.0)
    bpy.ops.object.shade_smooth()
    rock.data.materials.append(bpy.data.materials.get('Limestone') or painted('ChapelRockMat', (0.25, 0.23, 0.20), rust=0.0, rough=0.9))
    obs.append(rock)
    rz = math.radians(facing((x, y, 0)))
    white = deco.deco_paint('ChapelWhite', (0.70, 0.66, 0.58), grime=0.5)
    W, D, H = 4.4, 2.6, 4.2
    base_z = 3.6

    def lp(lx, ly, lz):
        return (x + lx * math.cos(rz) - ly * math.sin(rz), y + lx * math.sin(rz) + ly * math.cos(rz), base_z + lz)
    back = rbox('ChapelBack', (W, 0.3, H), lp(0, D / 2, H / 2), rot=(0, 0, rz), bevel=0.05, col=COL)
    back.data.materials.append(white)
    obs.append(back)
    for side in (-1, 1):
        wall = rbox('ChapelSide', (0.35, D, H), lp(side * W / 2, 0, H / 2), rot=(0, 0, rz), bevel=0.05, col=COL)
        wall.data.materials.append(white)
        obs.append(wall)
    roof = rbox('ChapelRoof', (W + 0.8, D + 0.8, 0.35), lp(0, 0, H + 0.2), rot=(0, 0, rz), bevel=0.08, col=COL)
    roof.data.materials.append(deco.deco_paint('ChapelRoofTiles', (0.35, 0.12, 0.08), grime=0.4))
    obs.append(roof)
    pedi = rbox('ChapelPediment', (W * 0.6, 0.35, 1.1), lp(0, -D / 2 + 0.2, H + 0.9), rot=(0, 0, rz), bevel=0.05, col=COL)
    pedi.data.materials.append(white)
    obs.append(pedi)
    crs = rbox('ChapelCross', (0.12, 0.12, 1.2), lp(0, -D / 2 + 0.2, H + 2.0), rot=(0, 0, rz), bevel=0.0, col=COL)
    crs.data.materials.append(white)
    obs.append(crs)
    # muro dei teschi: file ordinate sugli scaffali in fondo
    me = skull_mesh()
    rr = np.random.default_rng(13)
    shelf_m = deco.deco_paint('ChapelShelf', (0.25, 0.16, 0.10), grime=0.3)
    for row in range(5):
        lz = 0.55 + row * 0.72
        sh = rbox('ChapelShelf', (W - 0.5, 0.45, 0.06), lp(0, D / 2 - 0.35, lz - 0.12), rot=(0, 0, rz), bevel=0.0, col=COL)
        sh.data.materials.append(shelf_m)
        obs.append(sh)
        for k in range(14):
            lx = -W / 2 + 0.45 + k * (W - 0.9) / 13
            o = bpy.data.objects.new('Skull', me)
            bpy.data.collections[COL].objects.link(o)
            o.location = lp(lx, D / 2 - 0.35, lz)
            o.rotation_euler = (rr.normal(0, 0.1), rr.normal(0, 0.08), rz + rr.normal(0, 0.25))
            o.scale = (1.5,) * 3
            set_lightgroup(o, 'ambient')
            obs.append(o)
    # lumini rossi sul davanzale e sugli scogli davanti
    red_glass = deco.neon_material('VotiveRed', (1.0, 0.18, 0.08), 14.0)
    for k in range(26):
        lx = rr.uniform(-W / 2 + 0.4, W / 2 - 0.4)
        ly = rr.uniform(-D / 2 - 0.3, D / 2 - 0.6)
        c = cylinder_at('Votive', 0.07, 0.16, lp(lx, ly, 0.08), red_glass)
        obs.append(c)
    for k, (lx, ly) in enumerate(((-0.8, -0.3), (0.9, -0.2), (0.0, 0.4))):
        point_light(f'ChapelCandle{k}', lp(lx, ly, 0.6), 35, (1.0, 0.35, 0.12), radius=0.05)
    lights['candle'] = lp(0, 0, 0.3)
    return obs


def cylinder_at(name, r, h, loc, mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=r, depth=h, location=loc)
    o = link(bpy.context.object, COL)
    o.name = name
    o.data.materials.append(mat)
    set_lightgroup(o, 'ambient')
    return o


def build_fish_farm(lights):
    obs = []
    x0, y0, _ = P(-98.0, 235.0)
    hdpe = painted('FarmHDPE', (0.03, 0.03, 0.035), rust=0.1, rough=0.6)
    net = painted('FarmNet', (0.05, 0.06, 0.05), rust=0.0, rough=0.9)
    for k, (dx, dy) in enumerate(((0, 0), (22, 8), (-20, 12))):
        cx, cy = x0 + dx, y0 + dy
        for zz, tt in ((0.25, 0.35), (1.25, 0.08)):
            ring = [(cx + 9 * math.cos(a), cy + 9 * math.sin(a), zz) for a in np.linspace(0, 2 * math.pi, 49)]
            obs.append(tube('FarmRing', ring, tt, n=8, col=COL))
            obs[-1].data.materials.append(hdpe)
        for a in np.linspace(0, 2 * math.pi, 17)[:-1]:
            obs.append(tube('FarmPost', [(cx + 9 * math.cos(a), cy + 9 * math.sin(a), 0.3), (cx + 9 * math.cos(a), cy + 9 * math.sin(a), 1.25)], 0.05, n=4, col=COL))
            obs[-1].data.materials.append(hdpe)
        nt = lathe('FarmNet', [(8.8, 0.3), (8.6, -6.0), (0.5, -7.0)], n=32, col=COL)
        nt.location = (cx, cy, 0)
        nt.data.materials.append(net)
        obs.append(nt)
    barge = rbox('FarmBarge', (7, 4, 2.4), (x0 + 6, y0 - 14, 0.8), rot=(0, 0, 0.4), bevel=0.15, col=COL)
    barge.data.materials.append(painted('BargePaint', (0.55, 0.50, 0.20), rust=0.5))
    obs.append(barge)
    obs.append(tube('BargePost', [(x0 + 6, y0 - 14, 2.0), (x0 + 6, y0 - 14, 5.0)], 0.06, n=5, col=COL))
    obs[-1].data.materials.append(hdpe)
    lampo = sphere('BargeLamp', 0.2, (x0 + 6, y0 - 14, 5.1), segs=8, rings=6, col=COL)
    lampo.data.materials.append(emissive('BargeLampMat', (0.85, 0.92, 1.0), 20.0))
    obs.append(lampo)
    point_light('BargeLight', (x0 + 6, y0 - 14, 5.0), 400, (0.85, 0.92, 1.0), radius=0.2)
    lights['farmLamp'] = (x0 + 6, y0 - 14, 5.1)
    return obs


def build_landmarks():
    lights = {}
    obs = []
    obs += build_splashland(lights)
    obs += build_ferris_wheel(lights)
    obs += build_wreck(lights)
    obs += build_buoy(lights)
    obs += build_radio_mast(lights)
    obs += build_hotel(lights)
    obs += build_chapel(lights)
    obs += build_fish_farm(lights)
    finish(obs)
    return lights
