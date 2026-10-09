"""
Attrezzatura da pesca di scena (richiesta dall'utente, tutta di scena: non serve al gioco):
  collezione   tavola appesa al fianco destro dietro al pescatore: galleggianti di ogni tipo, ami
               arrugginiti, un cucchiaino, i piombi, una boccia di vetro nella sua rete
  baracchino   radio CB fissata alla paratia di prua, display rosso, microfono a spirale, antenna a stilo
  reti         un mucchio di rete buttato sul pagliolo a prua e una rete gettata sul bordo destro,
               simulate come stoffa (si calcolano una volta e si tengono in cache)

Le posizioni stanno lontane da dove si affacciano Molly (fianchi a metà barca), da dove Gulpy si
aggrappa (bordo sinistro e punta di prua) e dagli oggetti del gioco (canna, secchio, telone).
"""
from __future__ import annotations

import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from common import CACHE, link, log, set_lightgroup
from geo import catmull, cylinder, lathe, rbox, sphere, tube
from nodes import material

BOARD_Y = -1.10                # tavola della collezione, fianco destro dietro al pescatore
BOARD_Z = 0.60
CB_POS = (0.27, 2.03, 0.74)    # centro del baracchino (davanti alla paratia di prua, a destra)
ANTENNA_BASE = (0.47, 2.30, 0.93)
BULKHEAD_FACE_Y = 2.1275       # faccia della paratia di prua verso il pescatore


def _mat(name, **kw):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    g.output_material(g.principled(**kw))
    return m


def _rusty(name, base=(0.32, 0.30, 0.28), metal=0.8):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    r = g.smoothstep(0.42, 0.62, g.noise(co, scale=60.0, detail=5.0, rough=0.7).fac)
    col = g.mix(r, base, (0.22, 0.09, 0.03))
    g.output_material(g.principled(color=col, metal=g.mixf(r, metal, 0.0), rough=g.mixf(r, 0.35, 0.85)))
    return m


def _painted_float(name, top, bottom, split=0.0):
    """Galleggiante verniciato a due colori (taglio orizzontale in coordinate oggetto), sbeccato."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    _, _, z = g.sep(co)
    k = g.smoothstep(split - 0.002, split + 0.002, z)
    col = g.mix(k, bottom, top)
    chips = g.smoothstep(0.78, 0.84, g.noise(co, scale=90.0, detail=3.0).fac)
    col = g.mix(chips, col, (0.55, 0.50, 0.42))
    g.output_material(g.principled(color=col, rough=0.38, coat=0.4))
    return m


def _wall_frame(y, z, side=+1):
    """Sistema locale sul fianco interno: origine sulla murata, x lungo la barca, y verso l'interno, z su per la murata."""
    from boat import half_width_at
    xw = half_width_at(y, z)
    # pendenza della murata: si apre andando in su
    dx = half_width_at(y, z + 0.05) - half_width_at(y, z - 0.05)
    up = Vector((side * dx, 0.0, 0.10)).normalized()
    inward = Vector((-side * 0.10, 0.0, dx)).normalized()
    along = Vector((0.0, 1.0, 0.0))
    origin = Vector((side * (xw + 0.0), y, z))
    return origin, along, inward, up


def _place(obs, M):
    for o in obs:
        o.matrix_world = M @ o.matrix_world


# ───────────────────────── collezione di galleggianti e ami ─────────────────────────

def _hook(name, size, mat):
    """Amo: gambo, curva e punta con l'ardiglione (tubo sottile), occhiello in cima. Locale: pende lungo −z."""
    s = size
    pts = [(0, 0, 0), (0, 0, -0.55 * s), (0.02 * s, 0, -0.80 * s), (0.16 * s, 0, -0.95 * s), (0.30 * s, 0, -0.85 * s),
           (0.34 * s, 0, -0.62 * s), (0.30 * s, 0, -0.50 * s)]
    hook = tube(name, catmull(pts, 6), 0.035 * s + 0.0006, n=6, cap=True)
    barb = tube(name + 'Barb', [(0.30 * s, 0, -0.50 * s), (0.26 * s, 0, -0.60 * s)], 0.02 * s + 0.0004, n=5, cap=True)
    eye = tube(name + 'Eye', [(0.06 * s * math.cos(a), 0, 0.06 * s + 0.06 * s * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12)],
               0.025 * s + 0.0005, n=5, cap=False)
    for o in (hook, barb, eye):
        o.data.materials.append(mat)
    return [hook, barb, eye]


def collezione():
    """Tavola di legno vecchio avvitata alla murata destra, con una fila di chiodi: a ogni chiodo pende un
    pezzo della collezione del pescatore."""
    origin, along, inward, up = _wall_frame(BOARD_Y, BOARD_Z, side=+1)
    R = Matrix((along, up, -inward)).transposed()        # locale: x lungo la barca, y su per la murata, z fuori dalla murata
    # la tavola si stacca dalle ordinate di 4 cm
    M = Matrix.Translation(origin + inward * 0.045) @ R.to_4x4()
    obs = []
    wood = bpy.data.materials.get('BoardWoodOld')
    if wood is None:
        wood, g = material('BoardWoodOld')
        co = g.texcoord('Object')
        grain = g.noise(g.mapping(co, scale=(1.0, 14.0, 1.0)), scale=9.0, detail=6.0, rough=0.6)
        col = g.ramp(grain.fac, [(0.3, (0.16, 0.11, 0.07)), (0.7, (0.30, 0.22, 0.14))])
        g.output_material(g.principled(color=col, rough=0.8, normal=g.bump(grain.fac, strength=0.3, distance=0.002)))
    board = rbox('FloatBoard', (0.66, 0.20, 0.018), (0.0, 0.0, 0.0), bevel=0.004)
    board.data.materials.append(wood)
    obs.append(board)
    nail_m = _rusty('NailRust', base=(0.25, 0.24, 0.22))
    line_m = _mat('FishLineOld', color=(0.55, 0.55, 0.50), rough=0.4)
    items = []
    xs = np.linspace(-0.28, 0.28, 8)
    for i, x in enumerate(xs):
        n = cylinder(f'BoardNail{i}', 0.0025, 0.03, (float(x), 0.07, -0.024), rot=(math.radians(90), 0, 0), verts=8)
        n.data.materials.append(nail_m)
        obs.append(n)
        items.append((float(x), 0.07, -0.04))
    # 1 galleggiante tondo bianco e rosso
    def hang_line(i, length):
        x, y, z = items[i]
        ln = tube(f'BoardLine{i}', [(x, y, z), (x + 0.002, y - length, z - 0.004)], 0.0007, n=4, cap=False)
        ln.data.materials.append(line_m)
        obs.append(ln)
        return (x + 0.002, y - length, z - 0.004)

    p = hang_line(0, 0.04)
    b = sphere('FloatBall', 0.02, (p[0], p[1] - 0.02, p[2]), segs=16, rings=10)
    b.data.materials.append(_painted_float('FloatRedWhite', (0.75, 0.06, 0.04), (0.85, 0.83, 0.78)))
    obs.append(b)
    # 2 galleggiante a penna arancio con fascia nera
    p = hang_line(1, 0.02)
    q = lathe('FloatQuill', [(0.0, 0.0), (0.004, 0.01), (0.009, 0.06), (0.010, 0.09), (0.006, 0.13), (0.002, 0.155), (0.0, 0.16)], n=12)
    q.data.materials.append(_painted_float('FloatOrangeQuill', (0.95, 0.35, 0.03), (0.10, 0.10, 0.09), split=0.10))
    q.matrix_world = Matrix.Translation((p[0], p[1], p[2])) @ Matrix.Rotation(math.radians(90), 4, 'X')
    obs.append(q)
    # 3 sughero con l'amo sotto
    p = hang_line(2, 0.03)
    c = cylinder('FloatCork', 0.017, 0.045, (p[0], p[1] - 0.025, p[2]), rot=(math.radians(90), 0, 0), verts=14)
    cork = bpy.data.materials.get('CorkOld')
    if cork is None:
        cork, g = material('CorkOld')
        co = g.texcoord('Object')
        n1 = g.noise(co, scale=180.0, detail=3.0, rough=0.7)
        col = g.ramp(n1.fac, [(0.3, (0.28, 0.18, 0.10)), (0.7, (0.48, 0.34, 0.20))])
        g.output_material(g.principled(color=col, rough=0.9, normal=g.bump(n1.fac, strength=0.4, distance=0.001)))
    c.data.materials.append(cork)
    obs.append(c)
    hk = _hook('BoardHook3', 0.035, _rusty('HookRust', base=(0.40, 0.40, 0.42), metal=1.0))
    _place(hk, Matrix.Translation((p[0], p[1] - 0.055, p[2])) @ Matrix.Rotation(math.radians(-90), 4, 'X'))
    obs += hk
    # 4 amo grosso arrugginito
    p = hang_line(3, 0.015)
    hk = _hook('BoardHookBig', 0.075, _rusty('HookRust', base=(0.40, 0.40, 0.42), metal=1.0))
    _place(hk, Matrix.Translation((p[0], p[1], p[2])) @ Matrix.Rotation(math.radians(-90), 4, 'X'))
    obs += hk
    # 5 cucchiaino ondulante con l'ancoretta
    p = hang_line(4, 0.02)
    spoon_pts = []
    for k in range(13):
        t = k / 12
        w = 0.016 * math.sin(math.pi * t) ** 0.7
        spoon_pts.append((w, 0.07 * t))
    sp = lathe('SpoonLure', [(r_, z_) for r_, z_ in spoon_pts], n=16)
    sp.data.materials.append(_mat('SpoonSilver', color=(0.75, 0.75, 0.72), metal=1.0, rough=0.22))
    sp.matrix_world = (Matrix.Translation((p[0], p[1], p[2])) @ Matrix.Rotation(math.radians(90), 4, 'X')
                       @ Matrix.Diagonal((1.0, 0.25, 1.0, 1.0)))
    obs.append(sp)
    for k in range(3):
        a = 2 * math.pi * k / 3
        hk = _hook(f'SpoonTreble{k}', 0.02, _rusty('HookRust', base=(0.40, 0.40, 0.42), metal=1.0))
        _place(hk, Matrix.Translation((p[0], p[1] - 0.075, p[2])) @ Matrix.Rotation(math.radians(-90), 4, 'X') @ Matrix.Rotation(a, 4, 'Z'))
        obs += hk
    # 6 boccia di vetro verde nella sua rete di spago
    p = hang_line(5, 0.012)
    gc = (p[0], p[1] - 0.07, p[2] - 0.005)
    gl = sphere('GlassFloat', 0.06, gc, segs=24, rings=16)
    gl.data.materials.append(_mat('GlassFloatGreen', color=(0.35, 0.55, 0.40), rough=0.06, transmission=0.85, ior=1.5, coat=0.3))
    obs.append(gl)
    twine = _mat('TwineDark', color=(0.20, 0.16, 0.11), rough=0.9)
    for k in range(6):
        a = math.pi * k / 6
        ring = [(gc[0] + 0.0615 * math.cos(t) * math.cos(a), gc[1] + 0.0615 * math.sin(t), gc[2] + 0.0615 * math.cos(t) * math.sin(a))
                for t in np.linspace(0, 2 * math.pi, 24)]
        tw = tube(f'GlassNet{k}', ring, 0.0015, n=4, cap=False)
        tw.data.materials.append(twine)
        obs.append(tw)
    # 7 tre galleggiantini colorati sulla stessa lenza
    p = hang_line(6, 0.12)
    for k, col in enumerate(((0.85, 0.12, 0.05), (0.90, 0.70, 0.05), (0.15, 0.55, 0.12))):
        bb = sphere(f'FloatSmall{k}', 0.011, (p[0], p[1] + 0.03 + 0.035 * k, p[2]), segs=12, rings=8)
        bb.data.materials.append(_painted_float(f'FloatSmallPaint{k}', col, col))
        obs.append(bb)
    # 8 due piombi a goccia
    p = hang_line(7, 0.05)
    lead = _mat('LeadDull', color=(0.22, 0.23, 0.24), metal=0.6, rough=0.55)
    for k in range(2):
        d = lathe(f'LeadSinker{k}', [(0.0, 0.0), (0.008, 0.006), (0.010, 0.016), (0.006, 0.026), (0.002, 0.03), (0.0, 0.031)], n=12)
        d.data.materials.append(lead)
        d.matrix_world = Matrix.Translation((p[0] + 0.012 * k, p[1] - 0.035 * k, p[2])) @ Matrix.Rotation(math.radians(90), 4, 'X')
        obs.append(d)
    # qualche amo piantato nella tavola come in un puntaspilli
    for k in range(5):
        hk = _hook(f'BoardPinHook{k}', 0.018, _rusty('HookRust', base=(0.40, 0.40, 0.42), metal=1.0))
        _place(hk, Matrix.Translation((-0.22 + 0.1 * k, -0.06, -0.012)) @ Matrix.Rotation(math.radians(70 + 25 * k), 4, 'Y'))
        obs += hk
    _place(obs, M)
    return obs


# ───────────────────────── baracchino CB ─────────────────────────

def baracchino():
    """Radio CB anni '80 fissata sotto la coperta di prua: frontale nero con manopole, strumento a lancetta,
    display rosso, microfono appeso al gancio col cavo a spirale; antenna a stilo sul bordo destro."""
    x, y, z = CB_POS
    obs = []
    case_m = bpy.data.materials.get('CBCase')
    if case_m is None:
        case_m, g = material('CBCase')
        co = g.texcoord('Object')
        n = g.noise(co, scale=40.0, detail=5.0)
        scratch = g.smoothstep(0.8, 0.86, g.noise(g.mapping(co, scale=(1.0, 8.0, 1.0)), scale=60.0).fac)
        col = g.mix(scratch, (0.035, 0.035, 0.038), (0.28, 0.27, 0.25))
        g.output_material(g.principled(color=col, metal=0.7, rough=g.mixf(n.fac, 0.35, 0.6)))
    depth = BULKHEAD_FACE_Y - (y - 0.10)
    yc = BULKHEAD_FACE_Y - depth / 2
    body = rbox('CBBody', (0.17, depth, 0.055), (x, yc, z), bevel=0.004)
    body.data.materials.append(case_m)
    obs.append(body)
    front_y = BULKHEAD_FACE_Y - depth
    face = rbox('CBFace', (0.172, 0.006, 0.057), (x, front_y - 0.002, z), bevel=0.002)
    face.data.materials.append(_mat('CBFacePlastic', color=(0.02, 0.02, 0.022), rough=0.45))
    obs.append(face)
    # staffa a U avvitata sotto la trave della coperta
    steel = _rusty('CBBracket', base=(0.45, 0.45, 0.46))
    for sx in (-1, 1):
        arm = rbox(f'CBBracket{sx}', (0.004, 0.06, 0.12), (x + sx * 0.088, yc, z + 0.045), bevel=0.001)
        arm.data.materials.append(steel)
        obs.append(arm)
        knob = cylinder(f'CBBracketKnob{sx}', 0.012, 0.012, (x + sx * 0.097, yc, z), rot=(0, math.radians(90), 0), verts=12)
        knob.data.materials.append(_mat('CBKnobBlack', color=(0.015, 0.015, 0.015), rough=0.5))
        obs.append(knob)
    # manopole sul frontale
    for k, dx in enumerate((-0.062, -0.035, 0.05)):
        kn = cylinder(f'CBKnob{k}', 0.0085 if k < 2 else 0.012, 0.012, (x + dx, front_y - 0.009, z - 0.008), rot=(math.radians(90), 0, 0), verts=14)
        kn.data.materials.append(_mat('CBKnobBlack', color=(0.015, 0.015, 0.015), rough=0.5))
        obs.append(kn)
    # display del canale: due cifre rosse accese
    disp = rbox('CBDisplay', (0.03, 0.002, 0.014), (x + 0.012, front_y - 0.006, z + 0.008), bevel=0.0005)
    dm = _mat('CBDisplayLED', color=(0.02, 0.0, 0.0), rough=0.2, emission=(1.0, 0.12, 0.04), emission_strength=5.0)
    disp.data.materials.append(dm)
    set_lightgroup(disp, 'ambient')
    obs.append(disp)
    # strumento a lancetta
    meter = rbox('CBMeter', (0.03, 0.002, 0.018), (x - 0.012, front_y - 0.006, z + 0.008), bevel=0.0005)
    meter.data.materials.append(_mat('CBMeterFace', color=(0.75, 0.70, 0.52), rough=0.5, emission=(0.9, 0.6, 0.25), emission_strength=0.4))
    obs.append(meter)
    needle = tube('CBNeedle', [(x - 0.016, front_y - 0.0075, z + 0.0005), (x - 0.006, front_y - 0.0075, z + 0.014)], 0.0004, n=4)
    needle.data.materials.append(_mat('CBNeedleRed', color=(0.6, 0.02, 0.02), rough=0.4))
    obs.append(needle)
    # microfono appeso al gancio sulla paratia, col cavo a spirale
    mic_at = (x + 0.15, BULKHEAD_FACE_Y - 0.025, z - 0.035)
    mic = rbox('CBMic', (0.05, 0.03, 0.075), mic_at, bevel=0.012)
    mic.data.materials.append(case_m)
    obs.append(mic)
    ptt = rbox('CBMicButton', (0.012, 0.008, 0.03), (mic_at[0] - 0.026, mic_at[1], mic_at[2] + 0.005), bevel=0.003)
    ptt.data.materials.append(_mat('CBKnobBlack', color=(0.015, 0.015, 0.015), rough=0.5))
    obs.append(ptt)
    hook = rbox('CBMicHook', (0.02, 0.012, 0.012), (mic_at[0], BULKHEAD_FACE_Y - 0.006, mic_at[2] + 0.045), bevel=0.002)
    hook.data.materials.append(steel)
    obs.append(hook)
    coil = []
    a0 = (x + 0.07, front_y + 0.03, z - 0.028)
    a1 = (mic_at[0], mic_at[1], mic_at[2] - 0.04)
    for i in range(160):
        t = i / 159
        sag = 0.09 * math.sin(math.pi * t)
        cx = a0[0] + (a1[0] - a0[0]) * t
        cy = a0[1] + (a1[1] - a0[1]) * t
        cz = a0[2] + (a1[2] - a0[2]) * t - sag
        ang = t * 2 * math.pi * 26
        coil.append((cx + 0.007 * math.cos(ang), cy + 0.007 * math.sin(ang), cz + 0.007 * math.sin(ang) * 0.3))
    cc = tube('CBMicCord', coil, 0.0016, n=5, cap=False)
    cc.data.materials.append(_mat('CBCordBlack', color=(0.02, 0.02, 0.02), rough=0.35))
    obs.append(cc)
    # antenna a stilo sul bordo destro della prua, col cavo coassiale che scende al baracchino
    ax, ay, az = ANTENNA_BASE
    base = cylinder('CBAntennaBase', 0.016, 0.05, (ax, ay, az + 0.025), verts=14)
    base.data.materials.append(steel)
    obs.append(base)
    spring = tube('CBAntennaSpring', [(ax + 0.003 * math.cos(t * 9), ay + 0.003 * math.sin(t * 9), az + 0.05 + 0.04 * t / (2 * math.pi))
                                      for t in np.linspace(0, 2 * math.pi, 60)], 0.0022, n=5, cap=False)
    spring.data.materials.append(steel)
    obs.append(spring)
    whip = []
    for i in range(30):
        t = i / 29
        whip.append((ax - 0.05 * t * t, ay - 0.10 * t * t, az + 0.09 + 1.25 * t))
    w = tube('CBAntennaWhip', whip, 0.0028, n=6, cap=True, taper=0.45)
    w.data.materials.append(_mat('CBWhipSteel', color=(0.55, 0.55, 0.55), metal=1.0, rough=0.3))
    obs.append(w)
    coax = catmull([(ax, ay, az + 0.01), (ax - 0.02, ay - 0.03, az - 0.05), (ax - 0.08, ay - 0.12, z + 0.06),
                    (x + 0.05, BULKHEAD_FACE_Y - 0.03, z + 0.02), (x + 0.07, BULKHEAD_FACE_Y - 0.02, z)], 8)
    cx_ = tube('CBCoax', coax, 0.0035, n=6, cap=True)
    cx_.data.materials.append(_mat('CBCordBlack', color=(0.02, 0.02, 0.02), rough=0.35))
    obs.append(cx_)
    return obs


def _cb_display_texture():
    """Display a sette segmenti: canale 16 (lo stesso della radio che chiama all'inizio della notte)."""
    from PIL import Image, ImageDraw
    path = os.path.join(CACHE, 'tex', 'cb_display.png')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    W, H = 256, 128
    im = Image.new('RGB', (W, H), (8, 0, 0))
    d = ImageDraw.Draw(im)
    seg = {'1': 'bc', '6': 'acdefg'}

    def digit(x0, ch):
        on, off = (255, 40, 20), (40, 4, 2)
        coords = {
            'a': (x0 + 18, 14, x0 + 82, 26), 'b': (x0 + 82, 22, x0 + 94, 62), 'c': (x0 + 82, 70, x0 + 94, 110),
            'd': (x0 + 18, 104, x0 + 82, 116), 'e': (x0 + 6, 70, x0 + 18, 110), 'f': (x0 + 6, 22, x0 + 18, 62),
            'g': (x0 + 18, 59, x0 + 82, 71)}
        for s, box in coords.items():
            d.rectangle(box, fill=on if s in seg[ch] else off)
    digit(20, '1')
    digit(136, '6')
    im = im.transpose(Image.FLIP_TOP_BOTTOM)
    im.save(path)
    return path


# ───────────────────────── reti ─────────────────────────

NET_VERSION = 4


def net_material(cells=20.0, name='FishingNet'):
    """Rete da pesca di nylon: maglie a rombo larghe (alpha), spago spesso coi nodi, verde-azzurro sbiadito,
    sporca di alghe. Maglie grandi e filo spesso: a due metri si deve leggere come rete, non come erba.
    cells: maglie lungo il lato del telo (circa 8 cm l'una)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    uv = g.texcoord('UV')
    u, v, _ = g.sep(uv)
    N = float(cells)
    a = g.mul(g.add(u, v), N)
    b = g.mul(g.sub(u, v), N)
    fa = g.math('FRACT', a)
    fb = g.math('FRACT', b)
    da = g.mn(fa, g.sub(1.0, fa))
    db = g.mn(fb, g.sub(1.0, fb))
    la = g.sub(1.0, g.smoothstep(0.075, 0.115, da))
    lb = g.sub(1.0, g.smoothstep(0.075, 0.115, db))
    knot = g.mul(g.sub(1.0, g.smoothstep(0.12, 0.18, da)), g.sub(1.0, g.smoothstep(0.12, 0.18, db)))
    alpha = g.clamp01(g.add(g.mx(la, lb), knot))
    co = g.texcoord('Object')
    n = g.noise(co, scale=4.0, detail=5.0)
    col = g.ramp(n.fac, [(0.3, (0.05, 0.20, 0.17)), (0.6, (0.09, 0.30, 0.25)), (0.85, (0.20, 0.26, 0.18))])
    algae = g.smoothstep(0.62, 0.78, g.noise(co, scale=13.0, detail=4.0).fac)
    col = g.mix(g.mul(algae, 0.7), col, (0.06, 0.11, 0.03))
    surf = g.principled(color=col, rough=0.6, sheen=0.2)
    g.output_material(g.mix_shader(alpha, g.transparent(), surf))
    return m


def _cloth_net(name, size, center, res, pins, colliders, frames, settings):
    """Simula un telo di rete (piano a griglia con uv) e lo restituisce come mesh fissa; in cache per le volte dopo."""
    path = os.path.join(CACHE, 'mesh', f'{name}_v{NET_VERSION}.npz')
    if os.path.exists(path):
        d = np.load(path)
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in d['verts']], [], [tuple(f) for f in d['faces']])
        uv = me.uv_layers.new(name='UVMap')
        uvs = d['uvs']
        for li, lp in enumerate(me.loops):
            uv.data[li].uv = tuple(uvs[lp.vertex_index])
        ob = bpy.data.objects.new(name, me)
        link(ob, 'boat')
        for p in me.polygons:
            p.use_smooth = True
        return ob
    sc = bpy.context.scene
    W, L = size
    nx, ny = int(W / res), int(L / res)
    xs = np.linspace(-W / 2, W / 2, nx + 1)
    ys = np.linspace(-L / 2, L / 2, ny + 1)
    verts, uvs, pin_w = [], [], []
    for j, yy in enumerate(ys):
        for i, xx in enumerate(xs):
            p = pins(float(xx), float(yy), i, j, nx, ny)
            verts.append(p[0])
            pin_w.append(p[1])
            uvs.append(((xx + W / 2) / W, (yy + L / 2) / L))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    me = bpy.data.meshes.new(name + 'Sim')
    me.from_pydata(verts, [], faces)
    sheet = bpy.data.objects.new(name + 'Sim', me)
    sc.collection.objects.link(sheet)
    sheet.location = center
    vg = sheet.vertex_groups.new(name='Pin')
    for i, w in enumerate(pin_w):
        if w > 0:
            vg.add([i], w, 'REPLACE')
    cl = sheet.modifiers.new('Cloth', 'CLOTH')
    st = cl.settings
    st.quality = settings.get('quality', 10)
    st.mass = settings.get('mass', 0.08)
    st.tension_stiffness = settings.get('tension', 8.0)
    st.compression_stiffness = settings.get('compression', 2.0)
    st.shear_stiffness = settings.get('shear', 2.0)
    st.bending_stiffness = settings.get('bending', 0.05)
    st.air_damping = settings.get('air', 4.0)
    st.vertex_group_mass = 'Pin'
    st.shrink_min = settings.get('shrink', 0.0)
    cs = cl.collision_settings
    cs.distance_min = 0.006
    cs.collision_quality = 5
    cs.use_self_collision = settings.get('self', False)
    if cs.use_self_collision:
        cs.self_distance_min = 0.006
    cl.point_cache.frame_start = 1
    cl.point_cache.frame_end = frames
    added = []
    for o in colliders:
        if o.modifiers.get('Collision') is None:
            o.modifiers.new('Collision', 'COLLISION')
            o.collision.thickness_outer = 0.01
            o.collision.cloth_friction = 8.0
            added.append(o)
    bpy.context.view_layer.update()
    sc.frame_set(1)
    for f in range(1, frames + 1):
        sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = sheet.evaluated_get(dg)
    me2 = bpy.data.meshes.new_from_object(ev)
    mw = sheet.matrix_world.copy()
    me2.transform(mw)
    bpy.data.objects.remove(sheet, do_unlink=True)
    for o in added:
        o.modifiers.remove(o.modifiers['Collision'])
    sc.frame_set(1)
    vs = np.array([v.co[:] for v in me2.vertices], np.float32)
    fs = np.array([p.vertices[:] for p in me2.polygons], np.int32)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(path, verts=vs, faces=fs, uvs=np.array(uvs, np.float32))
    log(f'rete {name} simulata:', len(vs), 'vertici, z', round(float(vs[:, 2].min()), 3), '…', round(float(vs[:, 2].max()), 3))
    ob = bpy.data.objects.new(name, me2)
    link(ob, 'boat')
    uv = me2.uv_layers.get('UVMap') or me2.uv_layers.new(name='UVMap')
    for li, lp in enumerate(me2.loops):
        uv.data[li].uv = uvs[lp.vertex_index]
    for p in me2.polygons:
        p.use_smooth = True
    return ob


def _colliders(names_prefix):
    out = []
    for o in bpy.data.objects:
        if o.type == 'MESH' and any(o.name == n or (n.endswith('*') and o.name.startswith(n[:-1])) for n in names_prefix):
            out.append(o)
    return out


def _cork_line(net_ob, edge_uv_v, count, name):
    """Sugheri lungo un bordo della rete (cercati sulla mesh già simulata)."""
    me = net_ob.data
    uvl = me.uv_layers['UVMap'].data
    best = {}
    for lp_i, lp in enumerate(me.loops):
        u, v = uvl[lp_i].uv
        if abs(v - edge_uv_v) < 0.012:
            k = int(round(u * (count - 1)))
            if abs(u * (count - 1) - k) < 0.08:
                best[k] = net_ob.matrix_world @ me.vertices[lp.vertex_index].co
    obs = []
    fl = bpy.data.materials.get('NetFloatOrange')
    if fl is None:
        fl, g = material('NetFloatOrange')
        co = g.texcoord('Object')
        dirt = g.smoothstep(0.55, 0.8, g.noise(co, scale=30.0, detail=4.0).fac)
        col = g.mix(dirt, (0.85, 0.30, 0.04), (0.25, 0.16, 0.08))
        g.output_material(g.principled(color=col, rough=0.45, coat=0.3))
    for k, p in sorted(best.items()):
        c = sphere(f'{name}{k}', 0.035, tuple(p), segs=16, rings=10, scale=(1.0, 1.0, 0.8))
        c.data.materials.append(fl)
        obs.append(c)
    return obs


def reti():
    """Un mucchio di rete buttato sul pagliolo a prua (oltre il banco) e una rete gettata sul bordo destro."""
    obs = []
    rr = np.random.default_rng(17)
    # 1 il mucchio: un telo di rete accartocciato che cade nello spazio tra il banco di prua e la paratia
    def heap_pins(x, y, i, j, nx, ny):
        a = 2.2 * (x * 0.8 + y * 0.6)
        z = 0.32 + 0.10 * math.sin(a) + 0.06 * math.sin(2.7 * x - 1.9 * y) + 0.01 * float(rr.normal())
        # accartocciato: il telo parte già raccolto in un fagotto stretto
        return (x * 0.60 + 0.05 * math.sin(7 * y), y * 0.55 + 0.04 * math.sin(6 * x), z), 0.0
    heap = _cloth_net('NetHeap', (1.6, 1.6), (0.05, 1.62, 0.0), 0.03, heap_pins,
                      _colliders(['Floor*', 'Hull', 'ThwartFwd', 'ForeBulkhead', 'Foredeck', 'ForedeckBeam']),
                      70, {'mass': 0.05, 'tension': 6.0, 'compression': 4.0, 'bending': 0.25, 'air': 3.0, 'shrink': -0.4})
    heap.data.materials.append(net_material(20.0, 'FishingNetHeap'))
    obs.append(heap)
    obs += _cork_line(heap, 1.0, 6, 'HeapCork')
    # 2 la rete gettata sul bordo destro: metà dentro, metà fuori
    from boat import half_width_at, sheer, HALF
    yc = 1.80
    zg = float(sheer(yc / HALF))
    xg = half_width_at(yc, zg - 0.02) + 0.035

    def side_pins(x, y, i, j, nx, ny):
        # di traverso sul capodibanda: dentro scende verso il pagliolo, fuori penzola lungo il fasciame
        py = y + 0.08 * x
        if abs(x) < 0.05:
            return (x, py, zg + 0.012 + 0.015 * math.sin(5 * y)), 1.0
        if x < 0:                                    # dentro la barca
            return (x * 0.8, py, zg + 0.012 - (abs(x) - 0.05) * 0.55), 0.0
        return (0.05 + (x - 0.05) * 0.25, py, zg + 0.012 - (x - 0.05) * 0.95), 0.0
    side = _cloth_net('NetSide', (1.0, 0.65), (xg, yc, 0.0), 0.025, side_pins,
                      _colliders(['Hull', 'Floor*', 'ThwartFwd']), 60,
                      {'mass': 0.05, 'tension': 6.0, 'bending': 0.02, 'air': 3.0})
    side.data.materials.append(net_material(12.0, 'FishingNetSide'))
    obs.append(side)
    obs += _cork_line(side, 0.0, 4, 'SideCork')
    return obs
