"""
Il jumpscare della quota mancata (notti 1-5: alle sei senza la quota). Da approvare.

La Madre si vede solo in parte: l'occhio. Dal posto del pescatore guardi giù oltre il bordo, a sinistra: prima solo
acqua scura sotto la luce della lampara; poi dal buio sale una cosa chiara e tonda, l'occhio (grande quanto la barca),
che si gira verso di te; negli ultimi fotogrammi è appena sotto la superficie e riempie il quadro, la pupilla puntata
su di te, l'acqua sopra che si gonfia e le ciglia che ondeggiano. La Madre intera resta per la notte 6.

Si vede attraverso l'acqua: qui il mare del panorama (che nel gioco fa da maschera) è nascosto e al suo posto c'è
un'acqua vera solo per questa scena (acqua()): la superficie di vetro con le onde (rifrange), sotto un volume che
assorbe il rosso e diffonde un poco (verde-blu, buio in fondo), la luce della lampara che entra (una luce sotto il pelo
dell'acqua, perché il vetro non lascia passare le ombre) e il pulviscolo in sospensione. I fotogrammi si rendono interi
(non sfondo più creatura): 8 a 10 al secondo come gli altri jumpscare, codificati allo stesso modo.

Il modello è quello della Madre (madre.py, dal ramo claude/madre-modello, non modificato): la testa senza il corpo,
gli occhi, le ciglia, le palpebre.

Uso: tools/.venv/bin/python tools/render/quota.py [--fast]   anteprima → docs/concept/jumpscare/js_quota_fotogrammi.jpg
     tools/.venv/bin/python tools/render/quota.py --finale   (dopo l'ok) public/assets/img/js_quota_00..07.webp e la voce
                                                             overlays.json → jumpscares.quota
     QUOTA_FOTOGRAMMI=0,7 per renderne solo alcuni (prove)
"""
from __future__ import annotations

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import env  # noqa: E402
import post  # noqa: E402
from common import CACHE, OUT_IMG, ROOT, collection, log, mesh_from_arrays, perspective_camera, render, set_lightgroup  # noqa: E402
from nodes import material  # noqa: E402

FAST = '--fast' in sys.argv
FINALE = '--finale' in sys.argv
FRAMES = 8
FPS = 10
COL = 'quota'
OVERLAYS = os.path.join(OUT_IMG, 'overlays.json')

# la camera: il pescatore si sporge dal suo posto oltre il bordo a sinistra e guarda giù (dal banco, a −42°, vedrebbe
# solo l'interno della fiancata): l'occhio sta sopra il capodibanda
CAM_POS = (-1.0, -0.45, 1.22)
CAM_YAW, CAM_PITCH, CAM_LENS = -84.0, -60.0, 22.0
# l'occhio, all'ultimo fotogramma: l'apice della calotta appena sotto il pelo dell'acqua, dove guarda il centro del quadro
APICE_Z = -0.85
# da dove parte: più in fondo, più sotto la barca (verso +X) e più a prua; girato via di tanti gradi
PARTENZA = {'giu': 6.2, 'verso_barca': 1.6, 'prua': 1.0, 'girato': 80.0, 'occhio_girato': 38.0}
# l'acqua che si gonfia sopra l'occhio (metri, per fotogramma) e quanto è larga
GONFIA = [0.0, 0.0, 0.0, 0.0, 0.03, 0.09, 0.18, 0.28]
GONFIA_SIGMA = 1.5
CAUSTICHE = None


def cam_dir():
    y, p = math.radians(CAM_YAW), math.radians(CAM_PITCH)
    return Vector((math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)))


def apice_finale():
    """Dove il centro del quadro tocca il mare, appena sotto."""
    d = cam_dir()
    t = (0.0 - CAM_POS[2]) / d.z
    p = Vector(CAM_POS) + d * t
    return Vector((p.x, p.y, APICE_Z))


# ───────────────────────── l'acqua ─────────────────────────

def water_surface_material():
    m, g = material('QuotaWaterSurface')
    co = g.texcoord('Object')
    n = g.noise(co, scale=2.2, detail=6.0, rough=0.6)
    n2 = g.noise(co, scale=9.0, detail=3.0)
    nrm = g.bump(g.add(n.fac, g.mul(n2.fac, 0.35)), strength=0.42, distance=0.05)
    g.output_material(g.principled(color=(1.0, 1.0, 1.0), rough=0.035, ior=1.333, transmission=1.0, spec=0.5, normal=nrm))
    return m


def water_volume_material():
    """Il mare di notte: assorbe il rosso subito, il verde e il blu più piano; un poco di torbido in avanti."""
    m, g = material('QuotaWaterVolume')
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    ab = nt.nodes.new('ShaderNodeVolumeAbsorption')
    ab.inputs['Color'].default_value = (0.10, 0.50, 0.46, 1)
    ab.inputs['Density'].default_value = 0.24
    scat = nt.nodes.new('ShaderNodeVolumeScatter')
    scat.inputs['Color'].default_value = (0.25, 0.62, 0.56, 1)
    scat.inputs['Density'].default_value = 0.022
    scat.inputs['Anisotropy'].default_value = 0.55
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(ab.outputs[0], add.inputs[0])
    nt.links.new(scat.outputs[0], add.inputs[1])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(add.outputs[0], out.inputs['Volume'])
    return m


def surface_z(X, Y, i, centre):
    """Le onde del mare (calme vicino alla barca, come env.build_sea) e il gonfiore sopra l'occhio."""
    Z = env.sea_height(X, Y)
    rb = np.hypot(X / 1.25, Y / 3.0)
    near = np.clip((rb - 1.0) / (3.2 - 1.0), 0.0, 1.0)
    Z = Z * (0.15 + 0.85 * near * near * (3 - 2 * near))
    r2 = (X - centre[0]) ** 2 + (Y - centre[1]) ** 2
    return Z + GONFIA[i] * np.exp(-r2 / (2 * GONFIA_SIGMA ** 2))


def acqua(i, centre, half=16.0, step=0.07):
    """La superficie (vetro, senza ombre) per il fotogramma i, e il volume sotto. Restituisce (superficie, volume)."""
    for n in ('QuotaWater', 'QuotaVolume'):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o)
    cx, cy = centre[0], centre[1]
    xs = np.arange(cx - half, cx + half + 1e-6, step)
    ys = np.arange(cy - half, cy + half + 1e-6, step)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Z = surface_z(X, Y, i, centre)
    nx, ny = X.shape
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    # dentro lo scafo non c'è acqua (come env.build_sea)
    t = np.clip(verts[:, 1] / 2.8, -1, 1)
    hb = np.where(t > 0, (1 - np.abs(t) ** 2.0) ** 0.62, (1 - np.abs(t) ** 2.3) ** 0.55) * 0.70
    inside = (np.abs(verts[:, 0]) < hb - 0.02) & (np.abs(verts[:, 1]) < 2.7)
    faces = []
    for a in range(nx - 1):
        for b in range(ny - 1):
            f = (a * ny + b, (a + 1) * ny + b, (a + 1) * ny + b + 1, a * ny + b + 1)
            if inside[f[0]] and inside[f[1]] and inside[f[2]] and inside[f[3]]:
                continue
            faces.append(f)
    surf = mesh_from_arrays('QuotaWater', verts, faces, smooth=True, col=COL)
    surf.data.materials.append(water_surface_material() if not bpy.data.materials.get('QuotaWaterSurface')
                               else bpy.data.materials['QuotaWaterSurface'])
    surf.visible_shadow = False
    set_lightgroup(surf, 'ambient')
    # il volume: una scatola chiusa appena sotto le onde, fino in fondo
    top, bot = -0.09, -45.0
    bv = [(cx - half, cy - half, bot), (cx + half, cy - half, bot), (cx + half, cy + half, bot), (cx - half, cy + half, bot),
          (cx - half, cy - half, top), (cx + half, cy - half, top), (cx + half, cy + half, top), (cx - half, cy + half, top)]
    bf = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    vol = mesh_from_arrays('QuotaVolume', np.array(bv), bf, smooth=False, col=COL)
    vol.data.materials.append(bpy.data.materials.get('QuotaWaterVolume') or water_volume_material())
    set_lightgroup(vol, 'ambient')
    galleggianti(i, centre)
    return surf, vol


def _palline(name, pts, rads, mat, flat=1.0):
    ico = np.array([(0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)], float)
    tri = [(0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2), (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5)]
    verts, faces = [], []
    for p, r in zip(pts, rads):
        b = len(verts)
        verts += [tuple(np.array(p) + v * np.array((r, r, r * flat))) for v in ico]
        faces += [(b + x, b + y, b + z) for x, y, z in tri]
    ob = mesh_from_arrays(name, np.array(verts), faces, smooth=True, col=COL)
    sub = ob.modifiers.new('S', 'SUBSURF')
    sub.levels = sub.render_levels = 2
    ob.data.materials.append(mat)
    set_lightgroup(ob, 'ambient')
    return ob


def galleggianti(i, centre):
    """Sul pelo dell'acqua qualche fiocco di schiuma e di alga (fanno leggere la superficie, sopra l'occhio); dagli
    ultimi fotogrammi, le bolle che salgono dall'occhio."""
    for n in ('QuotaFoam', 'QuotaBubbles'):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o)
    rng = np.random.default_rng(31)
    n = 140
    X = centre[0] + rng.uniform(-3.2, 2.2, n)
    Y = centre[1] + rng.uniform(-2.6, 2.6, n)
    # la corrente li sposta un poco da un fotogramma all'altro
    X, Y = X + 0.02 * i, Y - 0.015 * i
    keep = np.abs(X) > 0.8
    X, Y = X[keep], Y[keep]
    Z = surface_z(X, Y, i, centre) + 0.004
    foam = bpy.data.materials.get('QuotaFoam')
    if foam is None:
        foam, g = material('QuotaFoam')
        g.output_material(g.principled(color=(0.62, 0.66, 0.58), rough=0.7, sss=0.2))
    _palline('QuotaFoam', list(zip(X, Y, Z)), rng.uniform(0.008, 0.035, len(X)), foam, flat=0.25)
    nb = [0, 0, 0, 6, 18, 40, 70, 100][i]
    if nb:
        rb = np.random.default_rng(100 + i)
        bx = centre[0] + rb.normal(0, 0.9, nb)
        by = centre[1] + rb.normal(0, 0.9, nb)
        top = surface_z(bx, by, i, centre) - 0.03
        bz = top - rb.uniform(0.0, 1.0, nb) ** 1.5 * 2.5
        bub = bpy.data.materials.get('QuotaBubble')
        if bub is None:
            bub, g = material('QuotaBubble')
            g.output_material(g.principled(color=(1.0, 1.0, 1.0), rough=0.0, ior=0.75, transmission=1.0))
        _palline('QuotaBubbles', list(zip(bx, by, bz)), rb.uniform(0.006, 0.03, nb), bub)


def pulviscolo(centre, n=900):
    """Le particelle in sospensione davanti all'occhio: danno la profondità e la scala."""
    rng = np.random.default_rng(12)
    verts, faces = [], []
    ico = [(0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)]
    tri = [(0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2), (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5)]
    for _ in range(n):
        p = np.array((centre[0] + rng.uniform(-3.5, 3.5), centre[1] + rng.uniform(-3.0, 3.0), -rng.uniform(0.25, 7.0) ** 1.0))
        r = rng.uniform(0.002, 0.007)
        b = len(verts)
        verts += [tuple(p + np.array(v) * r) for v in ico]
        faces += [(b + x, b + y, b + z) for x, y, z in tri]
    ob = mesh_from_arrays('QuotaMotes', np.array(verts), faces, smooth=True, col=COL)
    m, g = material('QuotaMotes')
    g.output_material(g.principled(color=(0.75, 0.80, 0.72), rough=0.6, sss=0.3))
    ob.data.materials.append(m)
    set_lightgroup(ob, 'ambient')
    return ob


def luce_sottacqua():
    """La luce della lampara che entra in acqua: una luce a cono appena sotto il pelo, sulla linea dalla lampara al
    punto dove guardi, che scende verso il fondo (fa il cono nel torbido e illumina l'occhio)."""
    import boat
    lamp = Vector(boat.LAMP_POS)
    target = apice_finale()
    d = (target - lamp)
    t = (-0.12 - lamp.z) / d.z
    pos = lamp + d * t
    ld = bpy.data.lights.new('QuotaUnderwaterLamp', 'SPOT')
    ld.energy = 2600.0
    ld.color = (1.0, 0.80, 0.55)
    ld.spot_size = math.radians(75)
    ld.spot_blend = 0.8
    ld.shadow_soft_size = 0.9
    # le caustiche: la luce passa dalle onde e sull'occhio arriva a reticolo (un voronoi sulla direzione, che si muove
    # da un fotogramma all'altro: CAUSTICHE.inputs['W'])
    global CAUSTICHE
    from nodes import Graph
    ld.use_nodes = True
    g = Graph(ld.node_tree)
    co = g.texcoord('Normal')
    vor = g.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE', voronoi_dimensions='4D')
    g.set(vor, 'Vector', co)
    g.set(vor, 'Scale', 7.0)
    g.set(vor, 'W', 0.0)
    CAUSTICHE = vor
    lines = g.smoothstep(0.07, 0.0, g.out(vor, 'Distance'))
    strength = g.add(0.45, g.mul(lines, 2.6))
    em = g.node('ShaderNodeEmission')
    g.set(em, 'Color', (1.0, 1.0, 1.0, 1.0))
    g.set(em, 'Strength', strength)
    outl = g.node('ShaderNodeOutputLight')
    g.link(em.outputs[0], outl.inputs['Surface'])
    ob = bpy.data.objects.new('QuotaUnderwaterLamp', ld)
    collection(COL).objects.link(ob)
    ob.location = pos
    aim = Vector((target.x, target.y, -6.0)) + (target - lamp).normalized() * 1.5
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = (aim - pos).to_track_quat('-Z', 'Y')
    # nei riflessi dell'occhio bagnato sarebbe una macchia enorme: lì c'è solo il punto luce qui sotto
    ob.visible_glossy = False
    set_lightgroup(ob, 'lamp')
    # il punto luce nell'occhio: piccolo, freddo, solo nei riflessi (l'occhio è vivo)
    cd = bpy.data.lights.new('QuotaCatchLight', 'POINT')
    cd.energy = 60.0
    cd.color = (0.85, 0.95, 1.0)
    cd.shadow_soft_size = 0.06
    co_ = bpy.data.objects.new('QuotaCatchLight', cd)
    collection(COL).objects.link(co_)
    co_.location = pos + (target - pos) * 0.35 + Vector((0.0, 0.0, -0.15))
    co_.visible_diffuse = False
    co_.visible_camera = False
    co_.visible_transmission = False
    co_.visible_volume_scatter = False
    set_lightgroup(co_, 'lamp')
    return ob


# ───────────────────────── la Madre: l'occhio ─────────────────────────

def frame_madre(ma, a_world, v_world, ce_world):
    """La trasformazione che porta l'asse dell'occhio su a_world, il suo «su» (le ciglia) su v_world e il centro
    dell'occhio in ce_world."""
    a_l = Vector(tuple(float(x) for x in ma.OCCHIO_ASSE))
    _, v_l = ma.base_occhio(ma.OCCHIO_ASSE)
    v_l = Vector(tuple(float(x) for x in v_l))
    L = Matrix((a_l, v_l, a_l.cross(v_l))).transposed()
    vw = (v_world - a_world * v_world.dot(a_world)).normalized()
    W = Matrix((a_world, vw, a_world.cross(vw))).transposed()
    R = (W @ L.transposed()).to_4x4()
    c_l = Vector(tuple(float(x) for x in ma.OCCHIO))
    return Matrix.Translation(ce_world - R @ c_l) @ R


def poses():
    """Per ogni fotogramma: (centro dell'occhio, asse della testa, «su», quanto l'occhio è girato via)."""
    import madre as ma
    apex1 = apice_finale()
    a1 = (Vector(CAM_POS) - apex1).normalized()
    up_img = Vector((0, 0, 1)) - cam_dir() * cam_dir().z
    up_img.normalize()
    side = a1.cross(up_img).normalized()
    out = []
    for i in range(FRAMES):
        t = i / (FRAMES - 1)
        u = t ** 1.3                                  # sale dal buio, sempre più in fretta
        k = (1 - u)
        apex = apex1 + Vector((PARTENZA['verso_barca'] * k ** 1.3, PARTENZA['prua'] * k ** 1.3, -PARTENZA['giu'] * k))
        ang = math.radians(PARTENZA['girato']) * k ** 1.2
        R = Matrix.Rotation(ang, 3, side)
        a = (R @ a1).normalized()
        v = (R @ up_img).normalized()
        ce = apex - a * float(ma.OCCHIO_R)
        # l'occhio nell'orbita: girato via fino a metà, poi scatta su di te negli ultimi fotogrammi
        s = min(1.0, max(0.0, (t - 0.45) / 0.45))
        eye_off = math.radians(PARTENZA['occhio_girato']) * (1 - s * s * (3 - 2 * s))
        out.append((ce, a, v, eye_off, apex))
    return out


def build_madre():
    import madre as ma
    t = time.time()
    obs = ma.build(viewer=tuple(float(x) for x in (ma.OCCHIO + ma.OCCHIO_ASSE * 30.0)), bocca=0.0, piccoli=False,
                   spruzzo_on=False, corpo_on=False)
    log('madre costruita', round(time.time() - t), 's', len(obs), 'oggetti')
    base = {o.name: o.matrix_world.copy() for o in obs}
    lash = bpy.data.objects.get('MadreLashes')
    wave = None
    if lash:
        wave = lash.modifiers.new('Ondeggia', 'WAVE')
        wave.height = 0.10
        wave.width = 1.4
        wave.narrowness = 1.2
        wave.speed = 0.0
        wave.use_normal = False
    return obs, base, wave


def place(obs, base, M, i, eye_off, side_world, wave):
    import madre as ma
    for o in obs:
        o.matrix_world = M @ base[o.name]
    # l'occhio destro (MadreEye0) girato via nell'orbita, attorno al suo centro
    e = bpy.data.objects.get('MadreEye0')
    if e and eye_off:
        c = M @ Vector(tuple(float(x) for x in ma.occhi()[0][0]))
        R = Matrix.Rotation(eye_off, 4, side_world)
        e.matrix_world = Matrix.Translation(c) @ R @ Matrix.Translation(-c) @ e.matrix_world
    if wave:
        wave.time_offset = -6.0 * i
        wave.height = 0.04 + 0.12 * (i / (FRAMES - 1))
    bpy.context.view_layer.update()


# ───────────────────────── render ─────────────────────────

def run():
    import jobs
    jobs.build_scene(fish=0, rod=True)
    collection(COL)
    sea = bpy.data.objects.get('Sea')
    if sea:
        sea.hide_render = True
    glow = [o for o in bpy.data.objects if o.name.startswith('LampGlow')]
    for o in glow:
        o.hide_render = True
    luce_sottacqua()
    obs, base, wave = build_madre()
    ps = poses()
    apex1 = ps[-1][4]
    pulviscolo(apex1)
    target = Vector(CAM_POS) + cam_dir() * 2.0
    perspective_camera(CAM_POS, tuple(target), lens=CAM_LENS, name='QuotaCam')
    if FINALE:
        W, H, samples = 1920, 1080, int(os.environ.get('JS_SAMPLES', '96'))
    else:
        W, H, samples = (640, 360, 16) if FAST else (960, 540, 32)
    only = [int(x) for x in os.environ.get('QUOTA_FOTOGRAMMI', '').split(',') if x != '']
    out_dir = os.path.join(CACHE, 'final' if FINALE else 'preview', 'quota')
    os.makedirs(out_dir, exist_ok=True)
    frames = []
    up_img = Vector((0, 0, 1)) - cam_dir() * cam_dir().z
    for i, (ce, a, v, eye_off, apex) in enumerate(ps):
        if only and i not in only:
            continue
        import madre as ma
        M = frame_madre(ma, a, v, ce)
        side_world = a.cross(up_img.normalized()).normalized()
        place(obs, base, M, i, eye_off, side_world, wave)
        acqua(i, apex1)
        if CAUSTICHE is not None:
            CAUSTICHE.inputs['W'].default_value = 0.35 * i
        # il punto luce nell'occhio solo quando c'è la pupilla da vicino (prima, nel torbido, è un alone fermo)
        cl = bpy.data.objects.get('QuotaCatchLight')
        if cl:
            cl.hide_render = i < FRAMES - 2
        exr = os.path.join(out_dir, f'quota_{i:02d}.exr')
        t = time.time()
        render(exr, samples, (W, H), data_passes=())
        log(f'quota fotogramma {i}', round(time.time() - t), 's', 'apice', tuple(round(x, 2) for x in apex))
        p = post.read_exr(exr)
        comp = sum(p[g][..., :3] for g in ('ambient', 'lamp', 'lantern') if g in p)
        if FINALE:
            scale = post.pick_scale(comp)
            fn = f'js_quota_{i:02d}.webp'
            post.save_webp(post.encode_light_pass(comp, scale), os.path.join(OUT_IMG, fn), quality=88)
            frames.append({'file': fn, 'scale': scale})
        else:
            frames.append(i)
    if FINALE and not only:
        post.update_manifest(OVERLAYS, 'jumpscares.quota', {'frames': frames, 'fps': FPS, 'aspect': round(W / H, 4)})
    if not FINALE:
        tavola(out_dir)


def tavola(out_dir, tile=(480, 270), exposure=0.5):
    """I fotogrammi in fila (4×2) col tono del motore → docs/concept/jumpscare/js_quota_fotogrammi.jpg"""
    W, H = tile
    sheet = Image.new('RGB', (4 * W, 2 * H))
    d = ImageDraw.Draw(sheet)
    for i in range(FRAMES):
        exr = os.path.join(out_dir, f'quota_{i:02d}.exr')
        if not os.path.exists(exr):
            continue
        p = post.read_exr(exr)
        comp = sum(p[g][..., :3] for g in ('ambient', 'lamp', 'lantern') if g in p)
        im = Image.fromarray((post.tonemap(comp, exposure) * 255 + 0.5).astype(np.uint8), 'RGB').resize((W, H), Image.LANCZOS)
        sheet.paste(im, ((i % 4) * W, (i // 4) * H))
        d.text(((i % 4) * W + 8, (i // 4) * H + 6), str(i), fill=(200, 200, 200))
    dst = os.path.join(ROOT, 'docs', 'concept', 'jumpscare', 'js_quota_fotogrammi.jpg')
    sheet.save(dst, quality=90)
    log('tavola', dst)


if __name__ == '__main__':
    if '--tavola' in sys.argv:
        tavola(os.path.join(CACHE, 'preview', 'quota'))
    else:
        run()
