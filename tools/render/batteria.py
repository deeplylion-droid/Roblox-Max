"""
La batteria della lampara (notte 2, docs/NOTTI_E_MOSTRI.md): una vecchia batteria d'auto sul banco di
prua, a destra del secchio, con i cavi che corrono lungo lo scafo fino al palo della lampara e un
voltmetro ad ago su una staffa, girato verso il pescatore.

Sta fuori da tutti i fotogrammi dei jumpscare già renderizzati (le camere larghe 79° attorno alla
creatura: Gulpy arriva al massimo a 14° a destra, Molly comincia a 37°, Hatch è a poppa): qui siamo a
circa 26° a destra, all'altezza del banco. L'ago lo disegna il gioco (il quadrante qui è senza ago);
nell'anteprima c'è un ago di prova.

Uso: tools/.venv/bin/python tools/render/batteria.py [--fast] [--vicino]   → docs/concept/batteria_anteprima.jpg
     (--vicino: primo piano, docs/concept/batteria_vicino.jpg)
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

from common import CACHE, EYE, ROOT, perspective_camera, set_lightgroup  # noqa: E402
from geo import catmull, cylinder, rbox, tube  # noqa: E402
from nodes import material  # noqa: E402

FAST = '--fast' in sys.argv
BENCH_TOP = 0.42
BATTERY_POS = (0.735, 0.975, BENCH_TOP)     # centro della base, sul banco di prua a destra del secchio
BATTERY_SIZE = (0.17, 0.26, 0.18)           # larga, lunga (verso prua), alta
GAUGE_R = 0.040                             # raggio del quadrante
GAUGE_TILT = 28.0                           # quadrante inclinato all'indietro verso l'occhio
GAUGE_SPAN = (-50.0, 50.0)                  # angolo dell'ago da batteria scarica a piena (gradi)


def _mat(name, color, rough=0.5, metal=0.0, **kw):
    m, g = material(name)
    g.output_material(g.principled(color=color, rough=rough, metal=metal, **kw))
    return m


def plastic_worn(name='BatteryPlastic'):
    """Plastica nera della cassa: opaca, consumata chiara sugli spigoli, un velo di salsedine."""
    m, g = material(name)
    co = g.texcoord('Object')
    n = g.noise(co, scale=38.0, detail=6.0)
    salt = g.smoothstep(0.62, 0.78, n.fac)
    col = g.mix(salt, (0.018, 0.019, 0.02), (0.11, 0.11, 0.10))
    g.output_material(g.principled(color=col, rough=0.62))
    return m


def gauge_face_texture(path, needle=None):
    """Quadrante del voltmetro: crema, scala 10-15 V con la zona rossa in basso, la scritta VOLT."""
    S = 512
    im = Image.new('RGB', (S, S), (16, 16, 16))
    d = ImageDraw.Draw(im)
    c = S / 2
    d.ellipse((8, 8, S - 8, S - 8), fill=(214, 204, 176))
    try:
        big = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 46)
        small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 44)
    except OSError:
        big = small = ImageFont.load_default()
    a0, a1 = GAUGE_SPAN

    def ang(v):   # 10..15 V → angolo dell'ago (0° = in alto)
        return math.radians(a0 + (a1 - a0) * (v - 10.0) / 5.0)
    r0, r1 = S * 0.36, S * 0.43
    # zona rossa (batteria scarica) e zona verde (carica)
    for v0, v1, col in ((10.0, 11.6, (176, 36, 26)), (12.4, 15.0, (58, 108, 52))):
        pts = []
        for v in np.linspace(v0, v1, 30):
            a = ang(v)
            pts.append((c + r1 * math.sin(a), c - r1 * math.cos(a)))
        for v in np.linspace(v1, v0, 30):
            a = ang(v)
            pts.append((c + (r1 - 22) * math.sin(a), c - (r1 - 22) * math.cos(a)))
        d.polygon(pts, fill=col)
    # tacche ogni mezzo volt, lunghe sui volt interi; i numeri solo su 10, 12 e 14 (da lontano si leggono)
    for i, v in enumerate(np.linspace(10.0, 15.0, 11)):
        a = ang(v)
        rr = r0 if i % 2 == 0 else r0 + 18
        d.line((c + rr * math.sin(a), c - rr * math.cos(a), c + r1 * math.sin(a), c - r1 * math.cos(a)), fill=(24, 22, 20), width=7 if i % 2 == 0 else 4)
        if i % 4 == 0:
            t = str(int(round(v)))
            rt = r0 - 46
            w = d.textlength(t, font=small)
            d.text((c + rt * math.sin(a) - w / 2, c - rt * math.cos(a) - 24), t, fill=(24, 22, 20), font=small)
    w = d.textlength('VOLT', font=big)
    d.text((c - w / 2, c + 40), 'VOLT', fill=(30, 28, 26), font=big)
    if needle is not None:
        a = ang(10.0 + 5.0 * needle)
        d.line((c, c, c + S * 0.40 * math.sin(a), c - S * 0.40 * math.cos(a)), fill=(150, 20, 16), width=9)
    d.ellipse((c - 22, c - 22, c + 22, c + 22), fill=(20, 20, 20))
    im = im.filter(ImageFilter.GaussianBlur(1.0))
    # ingiallito e macchiato dall'umidità
    a = np.asarray(im).astype(np.float32)
    rng = np.random.default_rng(12)
    small = (rng.random((S // 32, S // 32)) * 255).astype(np.uint8)
    n = np.asarray(Image.fromarray(small).resize((S, S), Image.BICUBIC)).astype(np.float32) / 255.0
    a *= (0.88 + 0.12 * n[..., None])
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(path)
    return path


GLOW_COLOR = (1.0, 0.62, 0.28)               # la lampadina dietro il quadrante: ambra, come i cruscotti vecchi
GLOW_STRENGTH = 4.0


def face_material(name, path, glow=0.0):
    """Il quadrante sotto il vetro: carta opaca con sopra uno strato lucido (il vetro, senza rifrazione).
    Retroilluminato (richiesta dell'utente: «fallo illuminato così è più importante»): la carta lascia
    passare la luce ambra della lampadina, l'inchiostro no. glow = forza dell'emissione (0 = spento)."""
    m, g = material(name)
    col, _ = g.image(path, g.texcoord('UV'), extension='CLIP')
    lit = g.mix(1.0, col, GLOW_COLOR, blend='MULTIPLY')
    g.output_material(g.principled(color=col, rough=0.6, coat=0.8, coat_rough=0.08, emission=lit, emission_strength=glow))
    return m


def set_glow(strength):
    """Accende o spegne la retroilluminazione del quadrante (tra un render e l'altro dello stesso oggetto)."""
    m = bpy.data.materials.get('GaugeFaceMat')
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            n.inputs['Emission Strength'].default_value = strength


def battery_frame():
    """Assi del voltmetro: centro del quadrante, normale (verso l'occhio), destra e su sul quadrante."""
    x, y, z = BATTERY_POS
    sx, sy, sz = BATTERY_SIZE
    base = np.array((x, y - sy / 2 + 0.055, z + sz + 0.075))
    to_eye = np.array(EYE) - base
    to_eye[2] = 0
    to_eye /= np.linalg.norm(to_eye)
    t = math.radians(GAUGE_TILT)
    n = to_eye * math.cos(t) + np.array((0, 0, 1.0)) * math.sin(t)
    # destra e su come le vede chi guarda il quadrante (dall'occhio, cioè lungo −n)
    right = np.cross((0, 0, 1.0), n)
    right /= np.linalg.norm(right)
    up = np.cross(n, right)
    return base, n, right, up


def build_battery(needle=None, glow=GLOW_STRENGTH):
    """La batteria con morsetti, pinze, cavi fino al palo della lampara e il voltmetro (col quadrante
    retroilluminato di forza glow). Restituisce gli oggetti."""
    obs = []
    x, y, z = BATTERY_POS
    sx, sy, sz = BATTERY_SIZE
    body = rbox('BatteryBody', (sx, sy, sz - 0.02), (x, y, z + (sz - 0.02) / 2), bevel=0.008, segments=3)
    body.data.materials.append(plastic_worn())
    obs.append(body)
    lid = rbox('BatteryLid', (sx + 0.006, sy + 0.006, 0.024), (x, y, z + sz - 0.012), bevel=0.005, segments=2)
    lid.data.materials.append(_mat('BatteryLidMat', (0.035, 0.036, 0.038), rough=0.5))
    obs.append(lid)
    # tappi delle celle in fila
    caps = _mat('BatteryCaps', (0.06, 0.06, 0.065), rough=0.45)
    for k in range(6):
        c = cylinder(f'BatteryCap{k}', 0.011, 0.008, (x, y - sy / 2 + 0.07 + k * 0.026, z + sz + 0.004), verts=12)
        c.data.materials.append(caps)
        obs.append(c)
    # etichetta sbiadita sul fianco verso il pescatore (−Y)
    lab = rbox('BatteryLabel', (sx * 0.8, 0.002, sz * 0.42), (x, y - sy / 2 - 0.001, z + sz * 0.55), bevel=0.0)
    lab.data.materials.append(_mat('BatteryLabelMat', (0.36, 0.10, 0.07), rough=0.7))
    obs.append(lab)
    # poli di piombo e pinze a coccodrillo
    lead = _mat('BatteryLead', (0.36, 0.36, 0.38), rough=0.4, metal=0.8)
    clips = {+1: _mat('ClipRed', (0.55, 0.04, 0.03), rough=0.45), -1: _mat('ClipBlack', (0.02, 0.02, 0.02), rough=0.45)}
    insul = {+1: _mat('CableRed', (0.42, 0.03, 0.02), rough=0.55), -1: _mat('CableBlack', (0.015, 0.015, 0.016), rough=0.6)}
    pole_base = np.array((0.0, 2.40, 0.93))
    for s in (+1, -1):
        px, py, pz = x + s * 0.045, y - sy / 2 + 0.025, z + sz
        post = cylinder(f'BatteryPost{s}', 0.009, 0.022, (px, py, pz + 0.011), verts=12)
        post.data.materials.append(lead)
        obs.append(post)
        clip = rbox(f'BatteryClip{s}', (0.018, 0.05, 0.016), (px, py + 0.012, pz + 0.026), rot=(math.radians(-8), 0, 0), bevel=0.003)
        clip.data.materials.append(clips[s])
        obs.append(clip)
        # il cavo: dalla pinza, sopra la batteria verso prua, giù dal banco e lungo l'interno dello scafo
        pts = [(px, py + 0.04, pz + 0.03), (px + s * 0.01, y + 0.02, z + sz + 0.04), (x + s * 0.03, y + sy / 2 + 0.03, z + sz - 0.02),
               (0.70 + s * 0.012, 1.22, BENCH_TOP + 0.02), (0.55 + s * 0.012, 1.55, 0.45), (0.30 + s * 0.01, 2.0, 0.62),
               tuple(pole_base + np.array((0.03 * s, -0.02, 0.0)))]
        cable = tube(f'BatteryCable{s}', catmull(pts, 10), 0.006, n=8)
        cable.data.materials.append(insul[s])
        obs.append(cable)
    # il voltmetro su una staffa, girato verso l'occhio
    c, n, right, up = battery_frame()
    steel = _mat('GaugeSteel', (0.08, 0.08, 0.085), rough=0.35, metal=0.9)
    stem = tube('GaugeStem', [(c[0], c[1], z + sz), tuple(c - n * 0.02)], 0.006, n=8)
    stem.data.materials.append(steel)
    obs.append(stem)
    bez = cylinder('GaugeBezel', GAUGE_R + 0.008, 0.024, tuple(c - n * 0.0135), verts=32)
    bez.rotation_mode = 'QUATERNION'
    from mathutils import Vector
    bez.rotation_quaternion = Vector(tuple(n)).to_track_quat('Z', 'Y')
    bez.data.materials.append(steel)
    obs.append(bez)
    tex = gauge_face_texture(os.path.join(CACHE, 'batteria_quadrante.png' if needle is None else 'batteria_quadrante_ago.png'), needle)
    # il quadrante: un disco con le UV del quadrato del quadrante
    verts, faces, uvs = [tuple(c + n * 0.0025)], [], [(0.5, 0.5)]
    N = 48
    for i in range(N):
        a = 2 * math.pi * i / N
        p = c + n * 0.0025 + (right * math.cos(a) + up * math.sin(a)) * GAUGE_R
        verts.append(tuple(p))
        uvs.append((0.5 + 0.5 * math.cos(a) * (GAUGE_R / (GAUGE_R + 0.0)) * 0.97, 0.5 + 0.5 * math.sin(a) * 0.97))
    for i in range(N):
        faces.append((0, 1 + i, 1 + (i + 1) % N))
    me = bpy.data.meshes.new('GaugeFace')
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    face = bpy.data.objects.new('GaugeFace', me)
    bpy.data.collections['boat'].objects.link(face) if 'boat' in bpy.data.collections else bpy.context.scene.collection.objects.link(face)
    face.data.materials.append(face_material('GaugeFaceMat', tex, glow))
    obs.append(face)
    # la maniglia di gomma da una parte all'altra del coperchio
    strap = tube('BatteryStrap', catmull([(x - sx / 2 - 0.004, y + 0.03, z + sz - 0.03), (x - sx * 0.3, y + 0.03, z + sz + 0.05),
                                          (x + sx * 0.3, y + 0.03, z + sz + 0.05), (x + sx / 2 + 0.004, y + 0.03, z + sz - 0.03)], 8), 0.008, n=8)
    strap.data.materials.append(_mat('BatteryStrapMat', (0.025, 0.025, 0.027), rough=0.7))
    obs.append(strap)
    for o in obs:
        set_lightgroup(o, 'ambient')
    return obs


def preview():
    """Anteprima da approvare: la scena del gioco vista dal posto del pescatore verso il banco di prua."""
    import jobs
    close = '--vicino' in sys.argv
    # nel primo piano niente pesci nel secchio (da così vicino si vede che sono sagome per il panorama)
    jobs.build_scene(fish=0 if close else 5, rod=True)
    build_battery(needle=0.72)
    sc = bpy.context.scene
    target = (0.70, 0.94, 0.66) if close else (0.55, 0.98, 0.55)
    perspective_camera(EYE, target, lens=110.0 if close else 26.0, name='BatteryCam')
    W, H = (960, 540) if FAST else (1600, 900)
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 24 if FAST else 64
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'PNG'
    name = 'batteria_vicino' if close else 'batteria_anteprima'
    path = os.path.join(CACHE, f'{name}.png')
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    out = os.path.join(ROOT, 'docs', 'concept', f'{name}.jpg')
    Image.open(path).convert('RGB').save(out, quality=90)
    print('anteprima', out, flush=True)


if __name__ == '__main__':
    preview()
