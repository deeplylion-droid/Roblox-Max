"""
Oggetti di scena sulla barca (come l'ufficio di FNAF: tanti, quasi tutti davanti al giocatore).

  lanterna arrugginita, borraccia ammaccata, bambola di legno seduta sul banco che ti guarda,
  paperella di gomma di Splashland, barattolo con un occhio, occhialini da piscina appesi,
  rosario di conchiglie sotto la lampara, tacche incise sul banco, campanella a poppa,
  scatola di latta con mozziconi di candela, statuina di Mama Marina sulla console.
"""
from __future__ import annotations

import math
import os

import bpy
import numpy as np

import mascot
from common import CACHE, set_lightgroup, set_visibility
from creature import eye_material, eyeball
from geo import catmull, cylinder, lathe, rbox, rect_profile, sphere, sweep, tube
from nodes import material

LANTERN_POS = (-0.21, 2.38, 0.968)
DUCK_POS = (0.20, 2.22, 0.962)
FLASK_POS = (0.30, 0.99, 0.42)
DOLL_POS = (-0.22, 0.97, 0.42)
TALLY_POS = (0.04, 0.905, 0.4215)
JAR_POS = (0.10, 1.80, -0.088)
GOGGLES_POS = (0.22, 2.112, 0.56)
ROSARY_TOP = (0.0, 2.76, 1.36)
STERN_BELL_TOP = (0.0, -2.79, 1.06)
TIN_POS = (0.47, -1.97, 1.0)
FIGURINE_POS = (0.53, -2.14, 1.0)


def mat(name, **kw):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    g.output_material(g.principled(**kw))
    return m


def rusty_metal(name, color):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    r = g.smoothstep(0.5, 0.6, g.noise(co, scale=30.0, detail=6.0, rough=0.7).fac)
    col = g.mix(r, color, (0.18, 0.07, 0.03))
    g.output_material(g.principled(color=col, metal=g.mixf(r, 0.6, 0.0), rough=g.mixf(r, 0.45, 0.9),
                                   normal=g.bump(g.noise(co, scale=80.0, detail=3.0).fac, strength=0.2, distance=0.001)))
    return m


def lantern():
    """Lanterna a petrolio (tipo Dietz), spenta e arrugginita."""
    x, y, z = LANTERN_POS
    red = rusty_metal('LanternPaint', (0.30, 0.05, 0.04))
    obs = []
    base = lathe('LanternBase', [(0.0, 0.0), (0.075, 0.0), (0.078, 0.01), (0.075, 0.045), (0.05, 0.055)], n=24)
    globe = lathe('LanternGlobe', [(0.035, 0.055), (0.058, 0.09), (0.062, 0.13), (0.05, 0.17), (0.03, 0.19)], n=24)
    cap = lathe('LanternCap', [(0.04, 0.19), (0.065, 0.20), (0.05, 0.225), (0.02, 0.245), (0.0, 0.25)], n=24)
    for o, m in ((base, red), (globe, None), (cap, red)):
        o.location = (x, y, z)
        o.data.materials.append(m if m else mat('LanternGlass', color=(0.7, 0.68, 0.55), rough=0.15, transmission=0.85, ior=1.5))
        obs.append(o)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        pts = [(x + 0.07 * math.cos(a), y + 0.07 * math.sin(a), z + 0.05), (x + 0.074 * math.cos(a), y + 0.074 * math.sin(a), z + 0.12),
               (x + 0.05 * math.cos(a), y + 0.05 * math.sin(a), z + 0.20)]
        w = tube('LanternWire', catmull(pts, 4), 0.003, n=5)
        w.data.materials.append(red)
        obs.append(w)
    bail = [(x + 0.06 * math.cos(t), y, z + 0.25 + 0.07 * math.sin(t)) for t in np.linspace(0, math.pi, 12)]
    b = tube('LanternBail', bail, 0.0025, n=5)
    b.data.materials.append(red)
    obs.append(b)
    # stoppino bruciato e una falena morta sul fondo del vetro
    wick = cylinder('LanternWick', 0.008, 0.02, (x, y, z + 0.065), verts=8)
    wick.data.materials.append(mat('BurntWick', color=(0.02, 0.02, 0.02), rough=0.9))
    obs.append(wick)
    return obs


def flask():
    """Borraccia militare ammaccata con la custodia di tela."""
    x, y, z = FLASK_POS
    obs = []
    body = sphere('Flask', 1.0, (x, y, z + 0.034), segs=32, rings=16, scale=(0.085, 0.11, 0.034))
    canvas = bpy.data.materials.get('Canvas') or mat('FlaskCanvas', color=(0.1, 0.12, 0.06), rough=0.8)
    body.data.materials.append(canvas)
    body.rotation_euler = (0, 0, math.radians(-25))
    obs.append(body)
    neck = cylinder('FlaskNeck', 0.013, 0.03, (x + 0.05, y + 0.1, z + 0.034), rot=(math.radians(90), 0, math.radians(-25)), verts=12)
    alu = mat('FlaskAlu', color=(0.55, 0.56, 0.55), metal=1.0, rough=0.35)
    neck.data.materials.append(alu)
    obs.append(neck)
    capo = cylinder('FlaskCap', 0.017, 0.018, (x + 0.06, y + 0.12, z + 0.034), rot=(math.radians(90), 0, math.radians(-25)), verts=12)
    capo.data.materials.append(mat('FlaskCapBlack', color=(0.02, 0.02, 0.02), rough=0.5))
    obs.append(capo)
    chain = [(x + 0.06 + 0.015 * math.cos(t), y + 0.12 - 0.04 * t, z + 0.005 + 0.002 * math.sin(t * 9)) for t in np.linspace(0, 1.2, 14)]
    c = tube('FlaskChain', chain, 0.0018, n=4)
    c.data.materials.append(alu)
    obs.append(c)
    return obs


def doll_face_material():
    m = bpy.data.materials.get('DollFace')
    if m:
        return m
    m, g = material('DollFace')
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    wood = g.ramp(g.noise(co, scale=40.0, detail=3.0).fac, [(0.3, (0.40, 0.27, 0.15)), (0.7, (0.55, 0.38, 0.22))])
    skin = (0.80, 0.70, 0.58)
    # capelli dipinti sulla parte alta e dietro
    hair = g.smoothstep(0.15, 0.25, g.add(z, g.mul(y, 0.9)))
    col = g.mix(hair, skin, (0.10, 0.05, 0.03))
    front = g.smoothstep(0.0, -0.5, y)

    def dot(cx, cz, r):
        d = g.vmath('LENGTH', g.comb(g.sub(x, cx), g.sub(z, cz), 0.0))
        return g.mul(g.smoothstep(r, r * 0.7, d), front)
    eye_l = dot(-0.33, 0.12, 0.13)
    eye_r = dot(0.33, 0.12, 0.13)
    col = g.mix(eye_l, col, (0.01, 0.01, 0.01))
    # l'occhio destro è stato grattato via: si vede il legno
    col = g.mix(eye_r, col, wood)
    cheeks = g.add(dot(-0.48, -0.22, 0.2), dot(0.48, -0.22, 0.2))
    col = g.mix(g.mul(cheeks, 0.6), col, (0.75, 0.30, 0.28))
    mouth = g.mul(dot(0.0, -0.40, 0.16), g.smoothstep(-0.36, -0.42, z))
    col = g.mix(mouth, col, (0.55, 0.05, 0.05))
    # crepa che attraversa la faccia
    crack = g.mul(g.smoothstep(0.035, 0.0, g.math('ABSOLUTE', g.sub(g.add(x, g.mul(z, 0.6)), g.mul(g.noise(co, scale=6.0).fac, 0.2)))), front)
    col = g.mix(crack, col, (0.05, 0.03, 0.02))
    chip = g.smoothstep(0.62, 0.66, g.noise(co, scale=5.0, detail=5.0).fac)
    col = g.mix(chip, col, wood)
    g.output_material(g.principled(color=col, rough=g.mixf(chip, 0.45, 0.8), coat=0.3))
    return m


def doll():
    """Bambola di legno snodata, seduta sul banco di prua, rivolta verso il giocatore."""
    x, y, z = DOLL_POS
    obs = []
    paint = bpy.data.materials.get('DollDress')
    if paint is None:
        paint, g = material('DollDress')
        co = g.texcoord('Object')
        chip = g.smoothstep(0.6, 0.65, g.noise(co, scale=25.0, detail=5.0).fac)
        col = g.mix(chip, (0.10, 0.20, 0.42), (0.45, 0.30, 0.17))
        g.output_material(g.principled(color=col, rough=0.5, coat=0.2))
    wood = mat('DollWood', color=(0.48, 0.33, 0.19), rough=0.6)
    torso = sphere('DollTorso', 1.0, (x, y + 0.01, z + 0.10), segs=24, rings=12, scale=(0.055, 0.042, 0.085))
    torso.data.materials.append(paint)
    obs.append(torso)
    collar = sphere('DollCollar', 1.0, (x, y - 0.002, z + 0.175), segs=20, rings=8, scale=(0.045, 0.035, 0.012))
    collar.data.materials.append(mat('DollCollarWhite', color=(0.75, 0.72, 0.65), rough=0.6))
    obs.append(collar)
    hx, hy, hz = x + 0.01, y - 0.005, z + 0.245
    head = sphere('DollHead', 1.0, (0, 0, 0), segs=32, rings=16)
    head.data.materials.append(doll_face_material())
    head.scale = (0.05, 0.05, 0.058)
    head.location = (hx, hy, hz)
    head.rotation_euler = (math.radians(6), math.radians(-14), 0)   # testa inclinata: inquietante
    obs.append(head)
    # gambe che penzolano oltre il bordo del banco
    for s in (-1, 1):
        hip = (x + s * 0.025, y - 0.01, z + 0.025)
        knee = (x + s * 0.03, y - 0.10, z + 0.02)
        foot = (x + s * 0.034, y - 0.125, z - 0.085)
        for a, b, r in ((hip, knee, 0.017), (knee, foot, 0.014)):
            l = tube('DollLeg', [a, b], r, n=10)
            l.data.materials.append(wood)
            obs.append(l)
        kn = sphere('DollKnee', 0.019, knee, segs=10, rings=6)
        kn.data.materials.append(wood)
        obs.append(kn)
        sh = sphere('DollShoe', 1.0, (foot[0], foot[1] - 0.012, foot[2] - 0.006), segs=12, rings=6, scale=(0.018, 0.03, 0.015))
        sh.data.materials.append(mat('DollShoeBlack', color=(0.02, 0.02, 0.02), rough=0.4, coat=0.5))
        obs.append(sh)
        shoulder = (x + s * 0.055, y, z + 0.16)
        elbow = (x + s * 0.075, y - 0.01, z + 0.085)
        hand = (x + s * 0.07, y - 0.035, z + 0.03)
        for a, b, r in ((shoulder, elbow, 0.013), (elbow, hand, 0.011)):
            l = tube('DollArm', [a, b], r, n=8)
            l.data.materials.append(wood)
            obs.append(l)
        hb = sphere('DollHand', 0.014, hand, segs=10, rings=6)
        hb.data.materials.append(wood)
        obs.append(hb)
    return obs


def duck():
    """Paperella di gomma di Splashland."""
    x, y, z = DUCK_POS
    yellow = mat('RubberYellow', color=(0.80, 0.58, 0.05), rough=0.45, coat=0.2)
    orange = mat('RubberOrange', color=(0.85, 0.25, 0.03), rough=0.45)
    obs = []
    body = sphere('DuckBody', 1.0, (x, y, z + 0.032), segs=24, rings=12, scale=(0.045, 0.06, 0.035))
    body.data.materials.append(yellow)
    head = sphere('DuckHead', 0.03, (x, y - 0.035, z + 0.075), segs=20, rings=10)
    head.data.materials.append(yellow)
    beak = sphere('DuckBeak', 1.0, (x, y - 0.066, z + 0.072), segs=12, rings=6, scale=(0.017, 0.015, 0.007))
    beak.data.materials.append(orange)
    obs += [body, head, beak]
    for s in (-1, 1):
        e = sphere('DuckEye', 0.0055, (x + s * 0.016, y - 0.058, z + 0.085), segs=8, rings=6)
        e.data.materials.append(mat('DuckEyeBlack', color=(0.01, 0.01, 0.01), rough=0.2, coat=1.0))
        obs.append(e)
    return obs


def jar():
    """Barattolo d'acqua torbida con un occhio che galleggia."""
    x, y, z = JAR_POS
    obs = []
    glass = lathe('JarGlass', [(0.0, 0.0), (0.045, 0.0), (0.05, 0.01), (0.05, 0.11), (0.04, 0.125), (0.04, 0.135)], n=28)
    glass.location = (x, y, z)
    glass.data.materials.append(mat('JarGlassMat', color=(0.85, 0.9, 0.8), rough=0.05, transmission=1.0, ior=1.5))
    set_visibility(glass, shadow=False)
    obs.append(glass)
    water = lathe('JarWater', [(0.0, 0.004), (0.046, 0.004), (0.046, 0.10), (0.0, 0.10)], n=28)
    water.location = (x, y, z)
    water.data.materials.append(mat('JarWaterMat', color=(0.55, 0.62, 0.35), rough=0.1, transmission=0.9, ior=1.33))
    set_visibility(water, shadow=False)
    obs.append(water)
    lid = cylinder('JarLid', 0.043, 0.02, (x, y, z + 0.14), verts=24)
    lid.data.materials.append(rusty_metal('JarLidMetal', (0.40, 0.40, 0.38)))
    obs.append(lid)
    em = bpy.data.materials.get('JarEye') or eye_material('JarEye', iris=(0.25, 0.45, 0.35), iris_dark=(0.05, 0.12, 0.08),
                                                         pupil='round', pupil_size=0.3, shine=(0.6, 0.9, 0.6), shine_strength=0.6,
                                                         sclera=(0.70, 0.62, 0.52))
    obs.append(eyeball('JarEyeball', (x + 0.006, y + 0.004, z + 0.058), 0.024, em, look=(0.15, -1.0, 0.35)))
    return obs


def goggles():
    """Occhialini da piscina per bambini appesi a un chiodo."""
    x, y, z = GOGGLES_POS
    obs = []
    nail = tube('Nail', [(x, y + 0.01, z + 0.05), (x, y - 0.02, z + 0.05)], 0.003, n=5)
    nail.data.materials.append(rusty_metal('NailIron', (0.3, 0.3, 0.3)))
    obs.append(nail)
    lens = mat('GoggleLens', color=(0.45, 0.20, 0.55), rough=0.05, transmission=0.6, coat=1.0)
    frame = mat('GoggleFrame', color=(0.85, 0.30, 0.55), rough=0.4)
    for s in (-1, 1):
        l = sphere('GoggleLens', 1.0, (x + s * 0.032, y - 0.006, z - 0.03), segs=16, rings=8, scale=(0.026, 0.012, 0.02))
        l.data.materials.append(lens)
        obs.append(l)
    bridge = tube('GoggleBridge', [(x - 0.008, y - 0.008, z - 0.028), (x + 0.008, y - 0.008, z - 0.028)], 0.003, n=5)
    bridge.data.materials.append(frame)
    obs.append(bridge)
    strap = [(x - 0.058, y - 0.004, z - 0.03)] + [(x + 0.06 * math.cos(t), y - 0.002, z + 0.045 + 0.02 * math.sin(t)) for t in np.linspace(math.pi, 0, 12)] + [(x + 0.058, y - 0.004, z - 0.03)]
    st = sweep('GoggleStrap', strap, rect_profile(0.004, 0.012))
    st.data.materials.append(frame)
    obs.append(st)
    return obs


def rosary():
    """Rosario di conchiglie appeso al palo della lampara."""
    x, y, z = ROSARY_TOP
    obs = []
    pts = []
    for t in np.linspace(0, 1, 40):
        a = t * math.pi
        pts.append((x + 0.06 * math.sin(a), y - 0.02 * math.sin(a), z - 0.30 * math.sin(a * 0.5) - 0.02))
    cord = tube('RosaryCord', pts, 0.0015, n=4)
    cord.data.materials.append(mat('RosaryCordMat', color=(0.35, 0.30, 0.22), rough=0.9))
    obs.append(cord)
    shell = mat('ShellMat', color=(0.80, 0.74, 0.62), rough=0.4, coat=0.4, sss=0.2)
    for k, t in enumerate(np.linspace(0.08, 0.92, 11)):
        p = pts[int(t * (len(pts) - 1))]
        s = sphere(f'Shell{k}', 1.0, p, segs=10, rings=6, scale=(0.011, 0.006, 0.013))
        s.data.materials.append(shell)
        obs.append(s)
    # pendaglio: una conchiglia più grande con un buco
    p = pts[len(pts) // 2]
    big = sphere('ShellPendant', 1.0, (p[0], p[1], p[2] - 0.03), segs=14, rings=8, scale=(0.022, 0.008, 0.026))
    big.data.materials.append(shell)
    obs.append(big)
    return obs


def tally_marks():
    """Tacche incise sul banco di prua: qualcuno contava le notti."""
    from PIL import Image, ImageDraw
    path = os.path.join(CACHE, 'tex', 'tally.png')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    W, H = 512, 200
    im = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(im)
    rr = np.random.default_rng(23)
    x0 = 20
    groups = [5, 5, 5, 5, 3]
    for n in groups:
        for i in range(min(n, 4)):
            xx = x0 + i * 16 + rr.integers(-2, 3)
            d.line([(xx, 30 + rr.integers(-4, 4)), (xx + rr.integers(-3, 4), 170 + rr.integers(-4, 4))], fill=255, width=6)
        if n == 5:
            d.line([(x0 - 8, 140), (x0 + 60, 55)], fill=255, width=6)
        x0 += 95
    im.save(path)
    x, y, z = TALLY_POS
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(x, y, z))
    ob = bpy.context.object
    ob.name = 'TallyDecal'
    ob.scale = (0.16, 0.0625, 1.0)
    m, g = material('TallyMat')
    co = g.texcoord('UV')
    c, _ = g.image(path, co, colorspace='Non-Color')
    cut = g.bw(c)
    carved = g.principled(color=(0.06, 0.035, 0.02), rough=0.9, normal=g.bump(cut, strength=0.8, distance=0.002, invert=True))
    g.output_material(g.mix_shader(cut, g.transparent(), carved))
    ob.data.materials.append(m)
    return [ob]


def stern_bell():
    x, y, z = STERN_BELL_TOP
    obs = []
    cord = tube('BellCord', [(x, y, z), (x + 0.01, y, z - 0.09)], 0.002, n=4)
    cord.data.materials.append(mat('BellCordMat', color=(0.55, 0.12, 0.10), rough=0.8))
    obs.append(cord)
    bell = lathe('SternBell', [(0.0, 0.0), (0.012, -0.002), (0.022, -0.018), (0.028, -0.04), (0.031, -0.045)], n=20)
    bell.location = (x + 0.01, y, z - 0.09)
    bell.data.materials.append(bpy.data.materials.get('Brass') or mat('BrassBell', color=(0.55, 0.38, 0.14), metal=1.0, rough=0.3))
    obs.append(bell)
    return obs


def candle_tin():
    x, y, z = TIN_POS
    obs = []
    tin = lathe('CandleTin', [(0.0, 0.0), (0.05, 0.0), (0.052, 0.035), (0.048, 0.036)], n=24)
    tin.location = (x, y, z)
    tin.data.materials.append(rusty_metal('TinMetal', (0.45, 0.45, 0.43)))
    obs.append(tin)
    wax = mat('CandleWax', color=(0.80, 0.76, 0.66), rough=0.5, sss=0.4, sss_radius=(1.0, 0.8, 0.5))
    for k, (dx, dy, h) in enumerate(((-0.02, 0.0, 0.03), (0.015, 0.015, 0.045), (0.018, -0.02, 0.02))):
        c = cylinder(f'CandleStub{k}', 0.011, h, (x + dx, y + dy, z + 0.005 + h / 2), verts=12)
        c.data.materials.append(wax)
        obs.append(c)
        w = cylinder(f'CandleWick{k}', 0.0015, 0.008, (x + dx, y + dy, z + 0.005 + h + 0.004), verts=6)
        w.data.materials.append(mat('BurntWick', color=(0.02, 0.02, 0.02), rough=0.9))
        obs.append(w)
    return obs


def figurine():
    return mascot.build_figurine(FIGURINE_POS, 180.0, height=0.13)


def build_props():
    obs = []
    for f in (lantern, flask, doll, duck, jar, goggles, rosary, tally_marks, stern_bell, candle_tin, figurine):
        obs += f()
    for o in obs:
        if o.type == 'MESH':
            set_lightgroup(o, 'ambient')
    return obs
