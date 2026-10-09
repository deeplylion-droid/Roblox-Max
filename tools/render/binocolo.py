"""
Il binocolo (easter egg): i luoghi dell'orizzonte renderizzati a parte ad alta risoluzione, con alcuni
dettagli di lore che si vedono solo così, criptici al massimo.

⚠️ I dettagli di lore sono una PROPOSTA DA APPROVARE (vedi docs/LORE.md, «Il binocolo»):
  ingresso   uno striscione nuovo, pulito: «NIGHT SPLASH ★ TONIGHT ★»
  statua     nell'orbita vuota di Mama Marina c'è una luce accesa, come un lumino dentro la testa
  ruota      una cabina accesa, con dentro un bambino seduto che guarda la barca
  albergo    nell'unica finestra accesa, una figura nera con la videocamera all'occhio, puntata sulla baia (REC)
  edicola    tre fotografie di bambini, i volti sbiaditi fino al bianco
  relitto    sul fasciame della prua, a vernice bianca, le tacche di tante notti contate

Ogni luogo è una camera prospettica dall'occhio del pescatore con un campo stretto. Si rende il passo
'ambient' (le luci lontane sono emissive) più la nebbia (mist) nel canale alfa: il motore lo disegna sopra
al panorama quando il binocolo è alzato. Uscite: public/assets/img/bino_<luogo>.webp, overlays.json →
binocular.
"""
from __future__ import annotations

import math
import os
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import env
from common import CACHE, EYE, OUT_IMG, ROOT, collection, log, perspective_camera, render, set_lightgroup
from geo import rbox, sphere, tube
from landmarks import emissive, facing, painted, point_light
from nodes import material

COL = 'env'
FONT = os.path.join(ROOT, 'public', 'fonts', 'Limelight-Regular.ttf')


def ground(yaw, s):
    return env.surface_at(yaw, s)


# ───────────────────────── dove guardare ─────────────────────────

def _wheel_frame():
    """Come build_ferris_wheel: il mozzo, il raggio, il piano della ruota."""
    sx, sy, sz = ground(-158.0, 0.0)
    d = math.hypot(sx, sy)
    ux, uy = -sx / d, -sy / d
    L = 55.0
    hx, hy, hz = sx + ux * (L - 8), sy + uy * (L - 8), 2.6 + 18.0
    px, py = -uy, ux
    return (hx, hy, hz), 15.0, (px, py)


def _gate():
    x, y, z = ground(167.0, 55.0)
    return (x, y, z), math.radians(facing((x, y, z)))


def _hotel_window():
    x, y, z = ground(124.0, 45.0)
    rz = math.radians(facing((x, y, z)))
    return (x + 12 * math.cos(rz) + 9.2 * math.sin(rz), y + 12 * math.sin(rz) - 9.2 * math.cos(rz), z + 5 * 3.4 + 1.6), rz


def _chapel():
    a = math.radians(-74.0)
    x, y = 92.0 * math.sin(a), 92.0 * math.cos(a)
    return (x, y), math.radians(facing((x, y, 0)))


def places():
    """(chiave, punto mirato, hfov in gradi, risoluzione)."""
    gx, gy, gz = _gate()[0]
    st = ground(180.0, 10.0)
    (hx, hy, hz), R, (px, py) = _wheel_frame()
    hw = _hotel_window()[0]
    cx, cy = _chapel()[0]
    sl = ground(193.0, 45.0)          # la torre degli scivoli (landmarks.py)
    lh = env.surface_at(env.LIGHTHOUSE_YAW, 22)
    vil = env.surface_at(env.VILLAGE_YAW, 30)
    a = math.radians(14.0)
    return [
        ('ingresso', (gx, gy, gz + 14.0), 6.0, (2048, 1152)),
        ('statua', (st[0], st[1], st[2] + 15.5), 4.2, (1600, 1600)),
        ('ruota', (hx - 3.75 * px, hy - 3.75 * py, hz + 4.1), 6.4, (1600, 1600)),
        ('scivoli', (sl[0], sl[1], sl[2] + 11.0), 7.5, (2048, 1152)),
        ('albergo', (hw[0], hw[1], hw[2] - 3.0), 5.0, (2048, 1152)),
        ('edicola', (cx, cy, 4.3), 10.0, (2048, 1152)),
        ('relitto', (170.0 * math.sin(a), 170.0 * math.cos(a), 2.5), 11.0, (2048, 1152)),
        ('faro', (lh[0], lh[1], lh[2] + 16.0), 3.2, (1600, 1600)),
        ('paese', (vil[0], vil[1], vil[2] + 12.0), 13.0, (2560, 1440)),
    ]


# ───────────────────────── texture dipinte ─────────────────────────

def _tex_path(name):
    d = os.path.join(CACHE, 'binocolo')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)


def banner_texture():
    W, H = 2400, 300
    im = Image.new('RGB', (W, H), (232, 226, 210))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(4)
    # bordo a onde e bollicine, come i volantini del parco
    for x in range(0, W, 60):
        d.ellipse((x, -18, x + 60, 22), fill=(40, 168, 176))
        d.ellipse((x, H - 22, x + 60, H + 18), fill=(40, 168, 176))
    for _ in range(40):
        r = int(rng.integers(6, 16))
        x, y = int(rng.integers(0, W)), int(rng.integers(40, H - 40))
        d.ellipse((x - r, y - r, x + r, y + r), outline=(40, 168, 176), width=3)
    f = ImageFont.truetype(FONT, 150)
    # Limelight non ha la stella: il testo si scrive a pezzi e le ★ si disegnano a mano
    parts = 'NIGHT SPLASH ★ TONIGHT ★'.split('★')
    star = 118
    w = sum(d.textlength(t, font=f) for t in parts) + star * (len(parts) - 1)
    b = d.textbbox((0, 72), 'N', font=f)
    cy = (b[1] + b[3]) / 2

    def star_at(x, y, fill):
        R, r = star * 0.46, star * 0.46 * 0.42
        pts = [(x + (R if i % 2 == 0 else r) * math.sin(i * math.pi / 5), y - (R if i % 2 == 0 else r) * math.cos(i * math.pi / 5)) for i in range(10)]
        d.polygon(pts, fill=fill)

    for dx, fill in ((5, (120, 20, 70)), (0, (226, 44, 128))):
        x = (W - w) / 2 + dx
        for i, t in enumerate(parts):
            d.text((x, 72 + dx), t, font=f, fill=fill)
            x += d.textlength(t, font=f)
            if i < len(parts) - 1:
                star_at(x + star / 2, cy + dx, fill)
                x += star
    path = _tex_path('striscione.png')
    im.save(path)
    return path


def photo_texture(seed):
    """Fototessera sbiadita di un bambino: il volto è scolorito fino al bianco."""
    rng = np.random.default_rng(seed)
    W, H = 300, 380
    im = Image.new('RGB', (W, H), (236, 230, 214))
    d = ImageDraw.Draw(im)
    bg = tuple(int(v) for v in rng.integers(90, 140, 3))
    d.rectangle((20, 20, W - 20, H - 70), fill=bg)
    cx, cy = W / 2, 150
    hair = tuple(int(v) for v in (rng.integers(30, 80), rng.integers(22, 50), rng.integers(10, 30)))
    d.ellipse((cx - 70, cy - 85, cx + 70, cy + 60), fill=hair)
    d.rectangle((cx - 95, cy + 70, cx + 95, H - 70), fill=tuple(int(v) for v in rng.integers(60, 200, 3)))
    d.ellipse((cx - 55, cy - 60, cx + 55, cy + 75), fill=(250, 248, 242))
    im = im.filter(ImageFilter.GaussianBlur(2.2))
    # macchie d'acqua e ingiallito
    a = np.asarray(im).astype(np.float32)
    n = rng.random((H // 10 + 1, W // 10 + 1))
    n = np.kron(n, np.ones((10, 10)))[:H, :W]
    a *= (0.85 + 0.15 * n[..., None])
    a[..., 2] *= 0.86
    path = _tex_path(f'foto_{seed}.png')
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(path)
    return path


def tally_texture():
    """Tacche a vernice bianca: gruppi da cinque, tante notti."""
    W, H = 1600, 420
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(9)
    x, row = 40, 0
    marks = 63
    for i in range(marks):
        g = i % 5
        y0 = 30 + row * 190
        if g < 4:
            xx = x + g * 34 + int(rng.integers(-4, 5))
            d.line((xx, y0 + int(rng.integers(0, 10)), xx + int(rng.integers(-8, 8)), y0 + 150), fill=(226, 222, 210, 235), width=13)
        else:
            d.line((x - 18, y0 + 120, x + 4 * 34 + 8, y0 + 30), fill=(226, 222, 210, 235), width=12)
            x += 4 * 34 + 70
            if x > W - 200:
                x, row = 40, row + 1
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    path = _tex_path('tacche.png')
    im.save(path)
    return path


def image_material(name, path, rough=0.7, alpha=False, emit=0.0):
    m, g = material(name)
    col, a = g.image(path, g.texcoord('UV'), extension='CLIP')
    co = g.texcoord('Object')
    n = g.noise(co, scale=8.0, detail=4.0)
    col = g.mix(g.mul(g.smoothstep(0.55, 0.8, n.fac), 0.25), col, (0.25, 0.22, 0.18))
    kw = {'alpha': a} if alpha else {}
    if emit:
        kw.update(emission=col, emission_strength=emit)
    g.output_material(g.principled(color=col, rough=rough, **kw))
    return m


def quad(name, center, right, up, w, h, mat, sag=0.0, segs=24):
    """Rettangolo (uv 0..1) centrato in center, lati lungo right e up; sag: si affloscia al centro."""
    c, r, u = np.array(center, float), np.array(right, float), np.array(up, float)
    verts, faces, uvs = [], [], []
    rows = 4
    for j in range(rows + 1):
        for i in range(segs + 1):
            s, t = i / segs, j / rows
            p = c + r * (s - 0.5) * w + u * (t - 0.5) * h
            p = p - u * sag * 4 * s * (1 - s)
            verts.append(tuple(p))
            uvs.append((s, t))
    for j in range(rows):
        for i in range(segs):
            a = j * (segs + 1) + i
            faces.append((a, a + 1, a + segs + 2, a + segs + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    ob = bpy.data.objects.new(name, me)
    collection(COL).objects.link(ob)
    ob.data.materials.append(mat)
    set_lightgroup(ob, 'ambient')
    return ob


# ───────────────────────── i dettagli di lore ─────────────────────────

def lore_banner():
    (x, y, z), rz = _gate()
    fwd = np.array((math.sin(rz), -math.cos(rz), 0.0))
    right = np.array((math.cos(rz), math.sin(rz), 0.0))
    c = np.array((x, y, z + 12.2)) + fwd * 1.6
    mat = image_material('BannerMat', banner_texture(), rough=0.8)
    ob = quad('NightSplashBanner', c, right, (0, 0, 1), 24.0, 3.0, mat, sag=0.35)
    rope = painted('BannerRope', (0.5, 0.48, 0.44), rust=0.0, rough=0.9)
    obs = [ob]
    for s in (-1, 1):
        a = c + right * s * 12.0 + np.array((0, 0, 1.5))
        b = np.array((x, y, z + 15.0)) + right * s * 13.5 + fwd * 1.0
        obs.append(tube('BannerRope', [tuple(a), tuple(b)], 0.04, n=5, col=COL))
        obs[-1].data.materials.append(rope)
    return obs


def lore_statue_eye():
    import mascot
    x, y, z = ground(180.0, 10.0)
    yaw = facing((x, y, z))
    M = Matrix.Translation((x, y, z + 0.2)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Scale(22.0, 4)
    sock = Vector(tuple(float(v) for v in mascot.EYE_R)) + Vector((0, 0.07, 0))
    p = M @ sock
    ember = sphere('StatueEyeEmber', 0.32, tuple(p), segs=16, rings=8, col=COL)
    ember.data.materials.append(emissive('StatueEyeGlow', (1.0, 0.5, 0.18), 6.0))
    li = point_light('StatueEyeLight', tuple(M @ (sock + Vector((0, 0.01, 0)))), 120.0, (1.0, 0.55, 0.25), radius=0.3)
    return [ember, li]


def lore_wheel_child():
    (hx, hy, hz), R, (px, py) = _wheel_frame()
    k = 5
    a = 2 * math.pi * k / 16 + math.pi / 16
    ax, ay, az = hx + R * math.cos(a) * px, hy + R * math.cos(a) * py, hz + R * math.sin(a)
    g = bpy.data.objects.get(f'Gondola{k}')
    if g:
        g.hide_render = True
    # la cabina aperta sta un po' davanti al piano della ruota, così i cerchi non coprono il bambino
    tb = -np.array((ax, ay, 0.0))
    tb /= np.linalg.norm(tb)
    c = np.array((ax, ay, az - 1.7)) + tb * 1.1
    rz = math.atan2(py, px)
    paint = painted('GondolaPaint1', (0.75, 0.62, 0.12), rust=0.4, rough=0.4)
    obs = []
    # cabina aperta: pavimento, tetto, montanti, sponde basse
    obs.append(rbox('OpenCabFloor', (1.7, 1.7, 0.12), tuple(c + (0, 0, -0.8)), rot=(0, 0, rz), bevel=0.04, col=COL))
    obs.append(rbox('OpenCabRoof', (1.8, 1.8, 0.14), tuple(c + (0, 0, 0.8)), rot=(0, 0, rz), bevel=0.06, col=COL))
    cr, sr = math.cos(rz), math.sin(rz)
    for i in (-1, 1):
        for j in (-1, 1):
            q = c + np.array((0.8 * i * cr - 0.8 * j * sr, 0.8 * i * sr + 0.8 * j * cr, 0))
            obs.append(rbox('OpenCabPost', (0.08, 0.08, 1.6), tuple(q), rot=(0, 0, rz), bevel=0.01, col=COL))
    for i, (dx, dy, w, d) in enumerate(((0, -0.82, 1.7, 0.06), (0, 0.82, 1.7, 0.06), (-0.82, 0, 0.06, 1.7), (0.82, 0, 0.06, 1.7))):
        q = c + np.array((dx * cr - dy * sr, dx * sr + dy * cr, -0.45))
        obs.append(rbox('OpenCabSide', (w, d, 0.62), tuple(q), rot=(0, 0, rz), bevel=0.01, col=COL))
    for o in obs:
        o.data.materials.append(paint)
    # rivolto verso la barca (la barca è nell'origine)
    to_boat = -np.array((ax, ay, 0.0))
    to_boat /= np.linalg.norm(to_boat)
    side = np.array((-to_boat[1], to_boat[0], 0.0))
    # la parete di fondo, chiara e illuminata: il bambino ci si staglia davanti
    wall_m = painted('OpenCabWall', (0.85, 0.78, 0.55), rust=0.15, rough=0.7)
    back = quad('OpenCabBack', tuple(c - to_boat * 0.8 + np.array((0, 0, 0.0))), side, (0, 0, 1), 1.6, 1.55, wall_m, segs=2)
    obs.append(back)
    # il bambino seduto, di spalle alla luce: una sagoma scura
    dark = painted('ChildSilhouette', (0.012, 0.010, 0.012), rust=0.0, rough=0.9)
    body = c + np.array((0, 0, -0.48)) - to_boat * 0.1
    obs.append(tube('ChildBody', [tuple(body), tuple(body + (0, 0, 0.5))], 0.17, n=10, col=COL))
    obs.append(sphere('ChildHead', 0.13, tuple(body + (0, 0, 0.7)), segs=16, rings=8, col=COL))
    for o in obs[-2:]:
        o.data.materials.append(dark)
    # la lampadina sotto il tetto, fra il bambino e la parete: illumina la parete, non lui
    bulb_p = c + np.array((0, 0, 0.62)) - to_boat * 0.55
    bulb = sphere('OpenCabBulb', 0.06, tuple(bulb_p), segs=10, rings=6, col=COL)
    bulb.data.materials.append(emissive('OpenCabBulbMat', (1.0, 0.72, 0.38), 30.0))
    obs.append(bulb)
    obs.append(point_light('OpenCabLight', tuple(bulb_p - to_boat * 0.05), 260.0, (1.0, 0.7, 0.4), radius=0.06))
    return obs


def lore_camcorder():
    """Nella finestra accesa, una figura nera in controluce con una videocamera all'occhio, puntata sulla
    baia; la lucina rossa del REC (il motore la fa lampeggiare)."""
    (wx, wy, wz), rz = _hotel_window()
    out = np.array((math.sin(rz), -math.cos(rz), 0.0))
    right = np.array((math.cos(rz), math.sin(rz), 0.0))
    base = np.array((wx, wy, wz)) + out * 0.16
    black = painted('FigureBlack', (0.008, 0.008, 0.009), rust=0.0, rough=0.9)
    obs = []
    hip = base + np.array((0, 0, -0.78)) + right * 0.12
    neck = hip + np.array((0, 0, 0.62))
    obs.append(tube('FigTorso', [tuple(hip), tuple(neck)], 0.21, n=12, col=COL))
    head = neck + np.array((0, 0, 0.22)) + out * 0.02
    obs.append(sphere('FigHead', 0.12, tuple(head), segs=16, rings=8, col=COL))
    # le braccia alzate a reggere la videocamera davanti alla faccia
    cam_c = head + out * 0.2 - right * 0.06
    for s_ in (-1, 1):
        sh = neck + right * s_ * 0.2 - np.array((0, 0, 0.05))
        el = sh + out * 0.16 - np.array((0, 0, 0.22)) + right * s_ * 0.05
        obs.append(tube('FigArm', [tuple(sh), tuple(el), tuple(cam_c + right * s_ * 0.05)], 0.055, n=8, col=COL))
    yaw = math.atan2(-wx, -wy)      # verso la barca
    d = np.array((math.sin(yaw), math.cos(yaw), -0.03))
    obs.append(rbox('Camcorder', (0.14, 0.32, 0.16), tuple(cam_c), rot=(0, 0, -yaw), bevel=0.02, col=COL))
    obs.append(tube('CamLens', [tuple(cam_c + d * 0.14), tuple(cam_c + d * 0.27)], 0.055, n=12, col=COL))
    for o in obs:
        o.data.materials.append(black)
    rec_p = cam_c + d * 0.08 + np.array((0, 0, 0.1))
    rec = sphere('CamRec', 0.03, tuple(rec_p), segs=8, rings=6, col=COL)
    rec.data.materials.append(emissive('CamRecMat', (1.0, 0.04, 0.03), 60.0))
    obs.append(rec)
    return obs, tuple(float(v) for v in rec_p)


def lore_photos():
    """Tre fotografie in cornice, in piedi fra i lumini dell'edicola, appena inclinate all'indietro."""
    (x, y), rz = _chapel()
    base_z = 3.6

    def lp(lx, ly, lz):
        return np.array((x + lx * math.cos(rz) - ly * math.sin(rz), y + lx * math.sin(rz) + ly * math.cos(rz), base_z + lz))
    right = np.array((math.cos(rz), math.sin(rz), 0.0))
    back = np.array((-math.sin(rz), math.cos(rz), 0.0))      # verso il muro dei teschi
    lean = math.radians(12)
    up = np.array((0.0, 0.0, 1.0)) * math.cos(lean) + back * math.sin(lean)
    front = np.cross(up, right)
    if front @ back > 0:
        front = -front
    obs = []
    frame = painted('PhotoFrame', (0.18, 0.12, 0.07), rust=0.0, rough=0.6)
    for i, lx in enumerate((-0.7, 0.0, 0.7)):
        c = lp(lx, 0.25, 1.12 + (0.04 if i == 1 else 0.0))     # sul primo ripiano sopra gli scogli
        fr = quad(f'PhotoFrame{i}', tuple(c), right, up, 0.5, 0.62, frame, segs=2)
        so = fr.modifiers.new('T', 'SOLIDIFY')
        so.thickness = 0.04
        obs.append(fr)
        mat = image_material(f'PhotoMat{i}', photo_texture(31 + i), rough=0.5)
        obs.append(quad(f'Photo{i}', tuple(c + front * 0.03), right, up, 0.4, 0.5, mat, segs=2))
    return obs


def lore_tally():
    """Le tacche a vernice bianca sul relitto. La tuga è affondata a filo d'acqua (il relitto è sprofondato di
    poppa), quindi le tacche stanno sul fasciame della prua, la parte fuori dall'acqua che guarda la barca."""
    hull = bpy.data.objects.get('WreckHull')
    if not hull:
        return []
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = hull.evaluated_get(dg)
    me = ev.to_mesh()
    M = ev.matrix_world
    N = M.to_3x3().inverted().transposed()
    eye = Vector(EYE)
    pts, nrm = [], []
    for v in me.vertices:
        w = M @ v.co
        n = (N @ v.normal).normalized()
        if 1.2 < w.z < 4.5 and n.dot((eye - w).normalized()) > 0.55:
            pts.append(w)
            nrm.append(n)
    ev.to_mesh_clear()
    if not pts:
        return []
    c = sum(pts, Vector()) / len(pts)
    nw = sum(nrm, Vector()).normalized()
    up = Vector((0, 0, 1))
    right = up.cross(nw).normalized()
    up = nw.cross(right).normalized()
    mat = image_material('TallyMat', tally_texture(), rough=0.8, alpha=True)
    w = 3.2
    return [quad('WreckTally', tuple(c + nw * 0.12), tuple(right), tuple(up), w, w * 420 / 1600, mat, segs=2)]


def wreck_fill():
    """Il relitto sta fra la barca e la luna: il lato con le tacche è in controluce. La luna che si riflette
    sul mare davanti al relitto gli rimanda un po' di luce fredda dal basso (una luce d'area larga e debole,
    accesa solo per il suo render)."""
    house = bpy.data.objects.get('WreckHouse')
    if not house:
        return None
    bpy.context.view_layer.update()
    c = house.matrix_world.translation
    to_eye = (Vector(EYE) - c)
    to_eye.z = 0
    to_eye.normalize()
    pos = c + to_eye * 22.0
    pos.z = 0.4
    ld = bpy.data.lights.new('WreckSeaFill', 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = 26.0, 6.0
    ld.energy = float(os.environ.get('RELITTO_FILL', '3500'))
    ld.color = (0.60, 0.72, 1.0)
    ob = bpy.data.objects.new('WreckSeaFill', ld)
    collection(COL).objects.link(ob)
    ob.location = pos
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = (Vector((c.x, c.y, c.z + 1.0)) - pos).to_track_quat('-Z', 'Y')
    set_lightgroup(ob, 'ambient')
    return ob


# ───────────────────────── render ─────────────────────────

def run(q, post_mod, overlays_path, build_scene, coll_objects):
    build_scene(fish=0, rod=False)
    for o in coll_objects('boat'):
        o.visible_camera = False
    lore_banner()
    lore_statue_eye()
    lore_wheel_child()
    _, rec = lore_camcorder()
    lore_photos()
    lore_tally()
    out_dir = os.path.join(CACHE, q.name, 'binocolo')
    os.makedirs(out_dir, exist_ok=True)
    only = [k for k in os.environ.get('LUOGHI', '').split(',') if k]
    fill = wreck_fill()
    # i fari colorati della statua, pensati per la vista a occhio nudo, bruciano la pancia nello zoom
    for k in range(2):
        fl = bpy.data.objects.get(f'MarinaFlood{k}')
        if fl:
            fl.data.energy *= 0.3
    entries = []
    for key, target, hfov, (W, H) in places():
        if only and key not in only:
            continue
        if fill:
            fill.hide_render = key != 'relitto'
        d = Vector(target) - Vector(EYE)
        yaw = math.degrees(math.atan2(d.x, d.y))
        pitch = math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
        lens = 18.0 / math.tan(math.radians(hfov) / 2)
        perspective_camera(EYE, target, lens=lens, name=f'Bino_{key}')
        scale = {'draft': 0.5, 'preview': 0.75}.get(q.name, 1.0)
        w, h = int(W * scale) // 2 * 2, int(H * scale) // 2 * 2
        samples = {'draft': q.samples, 'preview': 40}.get(q.name, min(q.samples, 64))
        exr = os.path.join(out_dir, f'{key}.exr')
        t = time.time()
        render(exr, samples, (w, h), data_passes=('Mist',))
        p = post_mod.read_exr(exr)
        lin = post_mod.rgb(p['ambient'])
        mist = np.clip(p['mist'], 0, 1)
        sc = post_mod.pick_scale(lin, pct=99.5)
        rgb8 = np.asarray(post_mod.encode_light_pass(lin, sc))
        a8 = np.clip(mist * 255 + 0.5, 0, 255).astype(np.uint8)
        fn = f'bino_{key}.webp'
        post_mod.save_webp(Image.fromarray(np.dstack([rgb8, a8]), 'RGBA'), os.path.join(OUT_IMG, fn), quality=90)
        entries.append({'key': key, 'file': fn, 'scale': sc, 'yaw': round(yaw, 3), 'pitch': round(pitch, 3), 'hfov': hfov, 'aspect': round(w / h, 4)})
        log(f'binocolo {key}', round(time.time() - t), 's', f'{w}x{h}', f'yaw {yaw:.1f} pitch {pitch:.2f}')
    old = {}
    if os.path.exists(overlays_path):
        import json
        old = json.load(open(overlays_path)).get('binocular', {})
    keep = [e for e in old.get('places', []) if e['key'] not in {x['key'] for x in entries}]
    rec_rel = [round(rec[i] - EYE[i], 3) for i in range(3)]
    post_mod.update_manifest(overlays_path, 'binocular', {'places': sorted(keep + entries, key=lambda e: e['key']), 'rec': rec_rel})
