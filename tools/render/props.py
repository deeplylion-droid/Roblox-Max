"""
Oggetti di scena sulla barca (come l'ufficio di FNAF: tanti, quasi tutti davanti al giocatore).

  lanterna arrugginita, borraccia ammaccata, bambola di legno seduta sul banco che ti guarda,
  paperella di gomma di Splashland, barattolo con un occhio, occhialini da piscina appesi,
  rosario di conchiglie sotto la lampara, tacche incise sul banco, campanella a poppa,
  scatola di latta con mozziconi di candela, statuina di Mama Marina sul ponte di poppa.
"""
from __future__ import annotations

import math
import os

import bpy
import numpy as np

import mascot
import sdf
from common import CACHE, set_lightgroup, set_visibility
from creature import eye_material, eyeball, sdf_object
from geo import catmull, cylinder, lathe, rbox, rect_profile, sphere, sweep, tube
from nodes import material

LANTERN_HOOK = (-0.80, -0.27, 0.865)   # staffa sul capodibanda di sinistra, accanto al pescatore
LANTERN_POS = (-0.80, -0.27, 0.585)
DUCK_POS = (0.20, 2.22, 0.962)
FLASK_POS = (0.30, 0.99, 0.42)
TALLY_POS = (0.16, 0.905, 0.4215)
JAR_POS = (0.10, 1.80, -0.088)
GOGGLES_POS = (0.22, 2.112, 0.56)
ROSARY_TOP = (0.0, 2.76, 1.36)
STERN_BELL_TOP = (0.0, -2.79, 1.06)
TIN_POS = (-0.08, -2.02, 0.595)
FIGURINE_POS = (-0.04, -2.44, 0.595)  # sul ponte di poppa, davanti al dritto, rivolta verso il parco


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
    """Lanterna a petrolio (tipo Dietz) appesa accanto al pescatore: l'unica luce che guarda verso di te.
    È nel light group 'lantern', così il motore la fa tremolare e resta accesa anche a lampara spenta."""
    x, y, z = LANTERN_POS
    red = rusty_metal('LanternPaint', (0.30, 0.05, 0.04))
    obs = []
    base = lathe('LanternBase', [(0.0, 0.0), (0.075, 0.0), (0.078, 0.01), (0.075, 0.045), (0.05, 0.055)], n=24, close_bottom=True)
    globe = lathe('LanternGlobe', [(0.035, 0.055), (0.058, 0.09), (0.062, 0.13), (0.05, 0.17), (0.03, 0.19)], n=24)
    cap = lathe('LanternCap', [(0.04, 0.19), (0.065, 0.20), (0.05, 0.225), (0.02, 0.245), (0.0, 0.25)], n=24)
    for o, m in ((base, red), (globe, None), (cap, red)):
        o.location = (x, y, z)
        o.data.materials.append(m if m else mat('LanternGlass', color=(0.9, 0.86, 0.75), rough=0.12, transmission=0.9, ior=1.5))
        obs.append(o)
    set_visibility(globe, shadow=False)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        pts = [(x + 0.07 * math.cos(a), y + 0.07 * math.sin(a), z + 0.05), (x + 0.074 * math.cos(a), y + 0.074 * math.sin(a), z + 0.12),
               (x + 0.05 * math.cos(a), y + 0.05 * math.sin(a), z + 0.20)]
        w = tube('LanternWire', catmull(pts, 4), 0.003, n=5)
        w.data.materials.append(red)
        obs.append(w)
    hx, hy, hz = LANTERN_HOOK
    bail = [(x + 0.06 * math.cos(t), y, z + 0.25 + 0.07 * math.sin(t)) for t in np.linspace(0, math.pi, 12)]
    b = tube('LanternBail', bail, 0.0025, n=5)
    b.data.materials.append(red)
    obs.append(b)
    # staffa di ferro dal capodibanda
    iron = rusty_metal('BracketIron', (0.12, 0.11, 0.10))
    br = tube('LanternBracket', [(-0.95, hy, 0.74), (-0.93, hy, hz + 0.02), (hx, hy, hz + 0.02), (hx, hy, z + 0.33)], 0.008, n=6)
    br.data.materials.append(iron)
    obs.append(br)
    # fiamma e luce (gruppo 'lantern')
    flame = sphere('LanternFlame', 1.0, (x, y, z + 0.095), segs=12, rings=8, scale=(0.009, 0.009, 0.022))
    fm = bpy.data.materials.get('LanternFlameMat')
    if fm is None:
        fm, g = material('LanternFlameMat')
        g.output_material(g.emission((1.0, 0.55, 0.18), 45.0))
    flame.data.materials.append(fm)
    set_lightgroup(flame, 'lantern')
    wick = cylinder('LanternWick', 0.006, 0.02, (x, y, z + 0.065), verts=8)
    wick.data.materials.append(mat('BurntWick', color=(0.02, 0.02, 0.02), rough=0.9))
    obs.append(wick)
    ld = bpy.data.lights.new('LanternLight', 'POINT')
    ld.energy = 14.0
    ld.color = (1.0, 0.60, 0.28)
    ld.shadow_soft_size = 0.02
    lo = bpy.data.objects.new('LanternLight', ld)
    bpy.data.collections['boat'].objects.link(lo)
    lo.location = (x, y, z + 0.10)
    lo.lightgroup = 'lantern'
    return obs + [flame]


def flask():
    """Borraccia militare ammaccata, in piedi sul banco, con la custodia di tela."""
    x, y, z = FLASK_POS
    obs = []
    canvas = bpy.data.materials.get('Canvas') or mat('FlaskCanvas', color=(0.1, 0.12, 0.06), rough=0.8)
    body_f = sdf.union(sdf.ellipsoid((0, 0, 0.085), (0.075, 0.034, 0.085)), sdf.box((0, 0, 0.06), (0.07, 0.032, 0.06), 0.03), k=0.02)
    dent = sdf.sphere((0.05, -0.05, 0.12), 0.03)
    body_f = sdf.subtract(body_f, dent, k=0.01)
    body = sdf_object('Flask', body_f, (-0.09, -0.05, -0.01), (0.09, 0.05, 0.19), res=0.002, col='boat')
    body.data.materials.append(canvas)
    from mathutils import Matrix
    body.matrix_world = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(-28), 4, 'Z')
    obs.append(body)
    alu = mat('FlaskAlu', color=(0.55, 0.56, 0.55), metal=1.0, rough=0.35)
    neck = cylinder('FlaskNeck', 0.014, 0.022, (x, y, z + 0.178), verts=14)
    neck.data.materials.append(alu)
    obs.append(neck)
    capo = cylinder('FlaskCap', 0.018, 0.02, (x, y, z + 0.198), verts=14)
    capo.data.materials.append(mat('FlaskCapBlack', color=(0.02, 0.02, 0.02), rough=0.5))
    obs.append(capo)
    chain = [(x + 0.018 + 0.01 * math.sin(t * 3), y - 0.012 * t, z + 0.195 - 0.07 * t) for t in np.linspace(0, 1, 14)]
    c = tube('FlaskChain', chain, 0.0018, n=4)
    c.data.materials.append(alu)
    obs.append(c)
    return obs


# ───────────────────────── la bambola ─────────────────────────
# Vecchia marionetta da ventriloquo ripescata dal mare: arti troppo lunghi, collo sottile,
# mascella snodata che pende aperta, un occhio di vetro che ti fissa e un'orbita vuota.
# È accasciata di lato sul banco di prua, la testa ciondoloni ma con la faccia verso di te.

DOLL_HIPS = np.array((-0.28, 0.99, 0.465))
EYE_POINT = np.array((0.0, -0.55, 1.25))


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _frame(z_axis, face_dir):
    """Matrice 3×3 (colonne = assi locali X, Y, Z in coordinate mondo): Z lungo z_axis, −Y verso face_dir."""
    z = _unit(z_axis)
    f = _unit(face_dir)
    f = _unit(f - np.dot(f, z) * z)
    y = -f
    x = np.cross(y, z)
    return np.stack([x, y, z], axis=1)


def _matrix_world(R, t):
    from mathutils import Matrix
    M = Matrix.Identity(4)
    for i in range(3):
        for j in range(3):
            M[i][j] = float(R[i, j])
        M[i][3] = float(t[i])
    return M


def doll_head_field():
    """Testa in coordinate locali (faccia verso −Y, alto +Z), alta ~15 cm."""
    skull = sdf.ellipsoid((0, 0.0, 0.004), (0.060, 0.064, 0.082))
    brow = sdf.ellipsoid((0, -0.050, 0.024), (0.052, 0.018, 0.013))
    nose = sdf.round_cone((0, -0.057, 0.006), (0, -0.074, -0.012), 0.009, 0.006)
    cheeks = sdf.union(sdf.sphere((0.030, -0.048, -0.012), 0.020), sdf.sphere((-0.030, -0.048, -0.012), 0.020))
    ears = sdf.union(sdf.ellipsoid((0.059, 0.006, 0.0), (0.008, 0.013, 0.020)), sdf.ellipsoid((-0.059, 0.006, 0.0), (0.008, 0.013, 0.020)))
    head = sdf.union(skull, brow, nose, cheeks, ears, k=0.012)
    sockets = sdf.union(sdf.sphere((0.024, -0.058, 0.008), 0.018), sdf.sphere((-0.024, -0.058, 0.008), 0.018))
    head = sdf.subtract(head, sockets, k=0.004)
    # mascella da marionetta: un blocco tagliato con due scanalature, che pende aperto
    jaw_box = sdf.box((0, -0.045, -0.056), (0.021, 0.036, 0.027), 0.010)
    main = sdf.subtract(head, sdf.box((0, -0.045, -0.056), (0.0232, 0.038, 0.0285), 0.009), k=0.002)
    drop = np.array((0, -0.002, -0.012), np.float32)

    def jaw(p):
        q = p - drop
        return np.maximum(head(q), jaw_box(q))
    throat = sdf.ellipsoid((0, -0.03, -0.046), (0.019, 0.034, 0.024))
    main = sdf.subtract(main, throat, k=0.002)
    return sdf.union(main, jaw), dict(jaw_box=jaw_box, drop=drop)


def doll_face_material():
    """Biacca bianca, occhi cerchiati di nero, guance rosse, sorriso cucito fino alle guance."""
    m = bpy.data.materials.get('DollFace')
    if m:
        return m
    m, g = material('DollFace')
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    ax = g.math('ABSOLUTE', x)
    grain_c, grain = g.wave(g.mapping(co, scale=(1.0, 1.0, 0.25)), scale=60.0, distortion=6.0, detail=3.0, kind='BANDS', axis='X')
    wood = g.ramp(grain, [(0.2, (0.16, 0.10, 0.06)), (0.8, (0.30, 0.20, 0.12))])
    paint = (0.90, 0.87, 0.80)
    chip = g.smoothstep(0.66, 0.70, g.noise(co, scale=55.0, detail=6.0, rough=0.7).fac)
    col = g.mix(chip, paint, wood)
    front = g.smoothstep(-0.02, -0.05, y)
    ink = (0.015, 0.012, 0.012)
    red = (0.55, 0.03, 0.05)
    smudge = g.mul(g.noise(co, scale=180.0, detail=2.0).fac, 0.006)
    # occhi cerchiati di nero (sbavati)
    for sx in (1, -1):
        d = g.vmath('LENGTH', g.comb(g.sub(x, sx * 0.024), 0.0, g.sub(z, 0.008)))
        ring = g.mul(g.smoothstep(g.add(0.027, smudge), 0.022, d), front)
        col = g.mix(ring, col, ink)
    # guance rosse
    for sx in (1, -1):
        d = g.vmath('LENGTH', g.comb(g.sub(x, sx * 0.038), 0.0, g.add(z, 0.016)))
        cheek = g.mul(g.smoothstep(0.014, 0.009, d), front)
        col = g.mix(g.mul(cheek, 0.9), col, (0.72, 0.12, 0.12))
    # sorriso cucito: dagli angoli della bocca sale fino alle guance
    t = g.math('MAXIMUM', g.sub(ax, 0.022), 0.0)
    zc = g.add(-0.028, g.mul(g.mul(t, t), 22.0))
    line = g.smoothstep(0.0024, 0.0008, g.math('ABSOLUTE', g.sub(z, zc)))
    line = g.mul(g.mul(line, g.smoothstep(0.056, 0.050, ax)), front)
    col = g.mix(line, col, red)
    stitch = g.mul(g.smoothstep(0.30, 0.12, g.math('ABSOLUTE', g.sub(g.math('FRACT', g.mul(ax, 140.0)), 0.5))),
                   g.smoothstep(0.0062, 0.003, g.math('ABSOLUTE', g.sub(z, zc))))
    stitch = g.mul(g.mul(stitch, g.smoothstep(0.024, 0.030, ax)), g.mul(g.smoothstep(0.056, 0.050, ax), front))
    col = g.mix(stitch, col, ink)
    # labbra e bocca spalancata (la mascella pende)
    lips = g.mul(g.smoothstep(0.005, 0.0, g.math('ABSOLUTE', g.sub(z, -0.027))), g.smoothstep(0.026, 0.020, ax))
    col = g.mix(g.mul(lips, front), col, red)
    inside = g.mul(g.smoothstep(-0.024, -0.031, z), g.smoothstep(0.024, 0.020, ax))
    inside = g.mul(inside, g.smoothstep(-0.050, -0.038, y))
    col = g.mix(inside, col, (0.01, 0.004, 0.004))
    # l'orbita destra è vuota: nero pieno
    sock = g.smoothstep(0.019, 0.013, g.vmath('LENGTH', g.comb(g.add(x, 0.024), g.add(y, 0.058), g.sub(z, 0.008))))
    col = g.mix(sock, col, (0.004, 0.003, 0.003))
    # sopracciglia dipinte, alte e sottili
    for sx in (1, -1):
        d = g.math('ABSOLUTE', g.sub(z, g.add(0.050, g.mul(g.mul(g.sub(x, sx * 0.024), g.sub(x, sx * 0.024)), -14.0))))
        arch = g.mul(g.mul(g.smoothstep(0.0022, 0.0008, d), g.smoothstep(0.017, 0.0, g.math('ABSOLUTE', g.sub(x, sx * 0.024)))), front)
        col = g.mix(arch, col, ink)
    # alghe dietro la testa, crepa sulla faccia
    algae = g.smoothstep(0.66, 0.76, g.noise(g.mapping(co, scale=(1.0, 1.0, 2.5)), scale=30.0, detail=5.0).fac)
    algae = g.mul(algae, g.smoothstep(-0.03, 0.02, y))
    col = g.mix(g.mul(algae, 0.8), col, (0.07, 0.10, 0.04))
    crack = g.mul(g.smoothstep(0.0022, 0.0, g.math('ABSOLUTE', g.sub(g.add(x, g.mul(z, 0.8)), g.add(0.016, g.mul(g.noise(co, scale=40.0).fac, 0.014))))), front)
    col = g.mix(crack, col, (0.03, 0.02, 0.012))
    nrm = g.bump(g.add(g.mul(chip, 0.6), g.mul(crack, -1.0)), strength=0.35, distance=0.0008)
    g.output_material(g.principled(color=col, rough=g.mixf(chip, 0.32, 0.75), coat=g.mixf(chip, 0.45, 0.0), normal=nrm))
    return m


def doll_wood_material():
    m = bpy.data.materials.get('DollWoodWet')
    if m:
        return m
    m, g = material('DollWoodWet')
    co = g.texcoord('Object')
    grain_c, grain = g.wave(g.mapping(co, scale=(0.3, 0.3, 1.0)), scale=90.0, distortion=8.0, detail=3.0, kind='BANDS', axis='Z')
    col = g.ramp(grain, [(0.2, (0.08, 0.05, 0.03)), (0.8, (0.20, 0.13, 0.08))])
    algae = g.smoothstep(0.58, 0.70, g.noise(co, scale=25.0, detail=5.0).fac)
    col = g.mix(g.mul(algae, 0.85), col, (0.05, 0.08, 0.03))
    salt = g.smoothstep(0.70, 0.78, g.noise(co, scale=60.0, detail=4.0).fac)
    col = g.mix(g.mul(salt, 0.5), col, (0.55, 0.55, 0.50))
    g.output_material(g.principled(color=col, rough=0.45, coat=0.5, coat_rough=0.15,
                                   normal=g.bump(g.add(grain, g.mul(algae, 0.5)), strength=0.25, distance=0.0008)))
    return m


def doll_swimsuit_material():
    m = bpy.data.materials.get('DollSwimsuit')
    if m:
        return m
    m, g = material('DollSwimsuit')
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    stripes = g.smoothstep(0.45, 0.55, g.math('FRACT', g.mul(z, 38.0)))
    col = g.mix(stripes, (0.62, 0.10, 0.08), (0.72, 0.68, 0.60))
    chip = g.smoothstep(0.6, 0.64, g.noise(co, scale=45.0, detail=6.0).fac)
    col = g.mix(chip, col, (0.18, 0.12, 0.07))
    algae = g.smoothstep(0.6, 0.72, g.noise(co, scale=22.0, detail=5.0).fac)
    col = g.mix(g.mul(algae, 0.7), col, (0.06, 0.08, 0.03))
    g.output_material(g.principled(color=col, rough=0.55, coat=0.2))
    return m


def doll():
    obs = []
    hips = DOLL_HIPS
    spine = _unit((-0.74, 0.12, 0.66))           # accasciata verso la sua destra (−x)
    neck_base = hips + spine * 0.165
    neck_dir = _unit((-0.70, 0.06, 0.71))
    head_base = neck_base + neck_dir * 0.05
    head_up = _unit((-0.72, 0.04, 0.69))          # testa ciondoloni, piegata di lato
    head_c = head_base + head_up * 0.074
    R_head = _frame(head_up, EYE_POINT - head_c)  # ...ma la faccia guarda il giocatore

    # testa (coordinate locali → matrix_world, così il materiale lavora in locale)
    hf, hinfo = doll_head_field()
    head = sdf_object('DollHead', hf, (-0.08, -0.10, -0.12), (0.08, 0.08, 0.10), res=0.0013, col='boat')
    head.data.materials.append(doll_face_material())
    head.matrix_world = _matrix_world(R_head, head_c)
    obs.append(head)
    em = bpy.data.materials.get('DollGlassEye') or eye_material('DollGlassEye', iris=(0.45, 0.62, 0.72), iris_dark=(0.10, 0.18, 0.25),
                                                                pupil='round', pupil_size=0.36, shine=(0.7, 0.9, 1.0), shine_strength=0.5,
                                                                sclera=(0.80, 0.76, 0.66))
    eye_local = np.array((0.024, -0.054, 0.008))
    eye_w = head_c + R_head @ eye_local
    obs.append(eyeball('DollEyeL', tuple(eye_w), 0.0165, em, look=tuple(_unit(EYE_POINT - eye_w)), col='boat'))

    # torso con il costume a righe dipinto
    face_t = EYE_POINT - hips
    R_t = _frame(spine, face_t)
    torso_f = sdf.union(sdf.ellipsoid((0, 0, 0.030), (0.046, 0.034, 0.042)), sdf.ellipsoid((0, 0.0, 0.080), (0.034, 0.026, 0.034)),
                        sdf.ellipsoid((0, -0.004, 0.128), (0.054, 0.034, 0.046)), sdf.round_cone((0, 0, 0.16), (0, 0, 0.175), 0.017, 0.013), k=0.022)
    torso = sdf_object('DollTorso', torso_f, (-0.07, -0.06, -0.03), (0.07, 0.06, 0.20), res=0.0018, col='boat')
    torso.data.materials.append(doll_swimsuit_material())
    torso.matrix_world = _matrix_world(R_t, hips)
    obs.append(torso)

    # arti lunghi e snodati (coordinate mondo)
    ax = R_t[:, 0]                                  # asse delle spalle (sinistra della bambola = +x locale)
    sh_l = neck_base + ax * 0.052 - spine * 0.012
    sh_r = neck_base - ax * 0.052 - spine * 0.012
    hip_l = hips + ax * 0.032
    hip_r = hips - ax * 0.032
    pose = {
        # braccio destro: gomito appoggiato sul banco, mano che pende oltre il bordo
        'arm_r': [sh_r, np.array((-0.47, 0.965, 0.442)), np.array((-0.53, 0.885, 0.432))],
        'hand_r': (np.array((-0.53, 0.885, 0.432)), _unit((-0.15, -0.25, -1.0))),
        # braccio sinistro: molle sul grembo, ciondola davanti al banco fin quasi al pagliolato
        'arm_l': [sh_l, np.array((-0.30, 0.925, 0.505)), np.array((-0.245, 0.855, 0.395))],
        'hand_l': (np.array((-0.245, 0.855, 0.395)), _unit((0.1, -0.05, -1.0))),
        # gamba destra piegata giù dal bordo, piede storto
        'leg_r': [hip_r, np.array((-0.335, 0.875, 0.468)), np.array((-0.365, 0.86, 0.315))],
        'foot_r': (np.array((-0.365, 0.86, 0.315)), _unit((-0.6, -0.5, -0.2))),
        # gamba sinistra distesa lungo il banco, piede girato all'insù
        'leg_l': [hip_l, np.array((-0.13, 0.955, 0.458)), np.array((-0.02, 0.975, 0.447))],
        'foot_l': (np.array((-0.02, 0.975, 0.447)), _unit((0.3, -0.2, 0.9))),
    }
    parts = []
    joints = []
    for key, r0, r1 in (('arm_r', 0.0135, 0.011), ('arm_l', 0.0135, 0.011), ('leg_r', 0.018, 0.014), ('leg_l', 0.018, 0.014)):
        pts = pose[key]
        parts.append(sdf.round_cone(pts[0], pts[1], r0, r1))
        parts.append(sdf.round_cone(pts[1], pts[2], r1 * 0.95, r1 * 0.75))
        for p_ in pts:
            joints.append(sdf.sphere(p_, r0 * 1.15))
    for key in ('hand_r', 'hand_l'):
        w, d = pose[key]
        side = _unit(np.cross(d, (0, 1.0, 0)))
        parts.append(sdf.ellipsoid(w + d * 0.016, (0.011, 0.011, 0.011)))
        for k, a in enumerate((-0.30, -0.10, 0.10, 0.30)):
            base = w + d * 0.022 + side * (a * 0.03)
            tip = base + _unit(d + side * a * 0.6) * (0.050 if abs(a) < 0.2 else 0.042)   # dita troppo lunghe
            parts.append(sdf.round_cone(base, tip, 0.0032, 0.0022))
    for key in ('foot_r', 'foot_l'):
        a_, d = pose[key]
        parts.append(sdf.round_cone(a_, a_ + d * 0.045, 0.012, 0.010))
    limbs_f = sdf.union(sdf.union(*parts, k=0.004), *joints, k=0.003)
    lo = np.minimum.reduce([np.min(np.array(v), axis=0) if isinstance(v, list) else v[0] for v in pose.values()]) - 0.08
    hi = np.maximum.reduce([np.max(np.array(v), axis=0) if isinstance(v, list) else v[0] for v in pose.values()]) + 0.08
    limbs = sdf_object('DollLimbs', limbs_f, tuple(lo), tuple(hi), res=0.0016, col='boat')
    limbs.data.materials.append(doll_wood_material())
    obs.append(limbs)
    # collo sottile
    neck = tube('DollNeck', [neck_base - spine * 0.01, head_base + head_up * 0.012], 0.0075, n=10)
    neck.data.materials.append(doll_wood_material())
    obs.append(neck)

    # braccialetto di Splashland al polso che ciondola
    wr = pose['arm_l'][2]
    d_arm = _unit(pose['arm_l'][2] - pose['arm_l'][1])
    u1 = _unit(np.cross(d_arm, (1.0, 0, 0)))
    u2 = np.cross(d_arm, u1)
    ring = [tuple(wr - d_arm * 0.012 + 0.0115 * (math.cos(t) * u1 + math.sin(t) * u2)) for t in np.linspace(0, 2 * math.pi, 25)]
    band = tube('DollWristband', ring, 0.0028, n=6)
    band.data.materials.append(mat('WristbandPink', color=(0.75, 0.15, 0.45), rough=0.4, coat=0.3))
    obs.append(band)

    # capelli bagnati: ciocche che pendono per gravità, alcune sulla faccia
    rr = np.random.default_rng(41)
    hair_m = mat('DollHair', color=(0.015, 0.012, 0.010), rough=0.25, coat=0.6)
    for k in range(22):
        th = rr.uniform(-0.9, 0.9) * math.pi
        ph = rr.uniform(0.15, 0.75)
        local = np.array((0.046 * math.cos(th) * math.sin(ph * math.pi / 2 + 0.6), 0.050 * math.sin(th) * 0.9 + 0.012, 0.066 * math.cos(ph * 1.1)))
        if local[1] < -0.035 and local[2] < 0.0:
            continue
        start = head_c + R_head @ local
        length = rr.uniform(0.05, 0.11)
        pts = [start]
        cur = start.copy()
        drift = np.array((rr.uniform(-0.01, 0.01), rr.uniform(-0.015, 0.005), 0.0))
        for i in range(8):
            cur = cur + np.array((0, 0, -length / 8)) + drift / 8 + rr.normal(0, 0.0015, 3)
            pts.append(cur.copy())
        h_ = tube(f'DollHair{k}', catmull(pts, 3), 0.0011, n=4, taper=0.4)
        h_.data.materials.append(hair_m)
        obs.append(h_)

    # cirripedi sulla spalla e su una guancia: viene dal mare
    barn_m = mat('Barnacle', color=(0.62, 0.60, 0.52), rough=0.8)
    spots = [sh_r + rr.normal(0, 0.012, 3) for _ in range(9)] + [head_c + R_head @ np.array((-0.034, -0.030, -0.018)) + rr.normal(0, 0.004, 3) for _ in range(3)]
    for k, sp in enumerate(spots):
        n_ = _unit(sp - (neck_base if k < 9 else head_c))
        r_ = rr.uniform(0.0025, 0.0045)
        bn = sdf_object(f'Barnacle{k}', sdf.round_cone(sp - n_ * 0.002, sp + n_ * r_ * 1.2, r_, r_ * 0.45),
                        tuple(sp - 0.012), tuple(sp + 0.012), res=0.0007, col='boat')
        bn.data.materials.append(barn_m)
        obs.append(bn)
    for o in obs:
        set_lightgroup(o, 'ambient')
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
    obs.append(eyeball('JarEyeball', (x + 0.006, y + 0.004, z + 0.058), 0.024, em, look=(0.15, -1.0, 0.35), col='boat'))
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
        if o.type == 'MESH' and o.lightgroup == '':
            set_lightgroup(o, 'ambient')
    return obs
