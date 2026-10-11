"""
Prove dell'atmosfera nuova (11 ottobre): la baia più buia, la foschia bassa sull'acqua e la nebbia volumetrica in
Cycles, illuminata dalla lampara. La luce che la nebbia diffonde dalla lampara finisce nel passo 'lamp' (i light
group di Cycles dividono per sorgente, anche dentro i volumi), così nel gioco l'alone cresce e cala col livello.

Il look di oggi e quello nuovo si rendono dalla stessa camera (l'occhio del pescatore, la vista come nel gioco:
90° in orizzontale, 12° verso il basso) e si compongono come il motore: ambient + peso·lamp + lantern, esposizione,
bloom, AgX col look noir, vignetta e grana. Per il look di oggi si aggiunge la nebbia del motore (shaders.ts).

Uso:
  tools/.venv/bin/python tools/render/atmosfera.py render <prima|dopo> [--yaw 0] [--pitch -12] [--creatura gulpy_sale]
                                                       [--samples 256] [--size 1600x900] [--nome prua]
  tools/.venv/bin/python tools/render/atmosfera.py componi        → docs/concept/atmosfera_*.jpg
"""
from __future__ import annotations

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from common import CACHE, EYE, ROOT, log  # noqa: E402

CONCEPT = os.path.join(ROOT, 'docs', 'concept')
OUT = os.path.join(CACHE, 'atmosfera')

# ───────────────────────── la nebbia ─────────────────────────

NEBBIA = {
    'raggio': 1700.0,        # la scatola della nebbia attorno alla barca (la riva è fra 400 e 1300 m)
    'alto': 160.0,
    'bassa': 0.050,          # densità (1/m) della foschia bassa al pelo dell'acqua
    'bassa_h': 1.2,          # quota (m) in cui la foschia bassa cala a 1/e
    'vicino': 0.014,         # la sacca di nebbia attorno alla barca, dove la lampara fa l'alone
    'vicino_r': 26.0,        # il suo raggio (m): oltre, il buio
    'alta': 0.0005,          # la nebbia rada che sale (fa la profondità e copre le luci lontane)
    'alta_h': 40.0,
    'colore': (0.80, 0.86, 0.92),
    'anisotropia': 0.55,     # diffusione in avanti: l'alone attorno alla lampara quando la si guarda
}

# quanto si abbassano le luci della scena (moltiplicatori)
BUIO = {
    'cielo': 0.30,           # il fondo del cielo (la luna nel cielo, le stelle, le nuvole)
    'luna': 0.15,
    'disco': 0.35,           # il disco della luna (oltre al cielo): il suo riflesso sull'acqua bucava la foschia            # la luce della luna sulla scena
    'paese': 0.35,           # finestre, lampioni, neon e lampade del paese
    'faro': 0.45,
    'chiarore': (0.0075, 0.0098, 0.0140),   # il chiarore sopra l'orizzonte (lineare, a cielo già abbassato)
    'luna_luoghi': 0.85,     # la luna che resta sui posti del binocolo (light linking: solo su di loro)
    'luoghi': 1.30,          # le luci dei posti del binocolo: più forti, devono bucare la nebbia
}


def scala_emissione(mat, k):
    """Moltiplica per k tutta l'emissione di un materiale (Principled ed Emission, anche se collegata a un grafo)."""
    nt = mat.node_tree
    if nt is None:
        return
    for n in list(nt.nodes):
        if n.type == 'BSDF_PRINCIPLED':
            sock = n.inputs['Emission Strength']
        elif n.type == 'EMISSION':
            sock = n.inputs['Strength']
        else:
            continue
        if sock.is_linked:
            src = sock.links[0].from_socket
            m = nt.nodes.new('ShaderNodeMath')
            m.operation = 'MULTIPLY'
            nt.links.new(src, m.inputs[0])
            m.inputs[1].default_value = k
            nt.links.new(m.outputs[0], sock)
        else:
            sock.default_value *= k


def applica_buio(luoghi):
    """luoghi: i nomi degli oggetti dei posti del binocolo (landmarks.py); il resto di 'env' è il paese, il faro, il
    cielo e il mare."""
    import bpy
    sc = bpy.context.scene
    w = sc.world
    for n in w.node_tree.nodes:
        if n.type == 'BACKGROUND':
            n.inputs['Strength'].default_value *= BUIO['cielo']
        # il disco: moon_strength = disc * 22 in env.build_sky
        if n.type == 'MATH' and n.operation == 'MULTIPLY' and abs(n.inputs[1].default_value - 22.0) < 1e-6:
            n.inputs[1].default_value *= BUIO['disco']
    # un chiarore appena più chiaro sopra l'orizzonte, perché le sagome della riva ci si stacchino contro
    from nodes import Graph
    g = Graph(w.node_tree, clear=False)
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    src = bg.inputs['Color'].links[0].from_socket
    _, _, dz = g.sep(g.texcoord('Generated'))
    banda = g.mul(g.smoothstep(0.16, 0.0, dz), g.smoothstep(-0.02, 0.005, dz))
    k = 1.0 / BUIO['cielo']
    c = BUIO['chiarore']
    g.link(g.mix(1.0, src, g.comb(g.mul(banda, c[0] * k), g.mul(banda, c[1] * k), g.mul(banda, c[2] * k)),
                 blend='ADD', clamp=False), bg.inputs['Color'])
    moon = bpy.data.objects.get('Moon')
    if moon:
        # una seconda luna, legata solo ai posti del binocolo: il chiaro di luna resta su di loro, così si leggono
        # contro le colline buie dietro (con la luna abbassata dappertutto la ruota e la torre sparivano)
        col = bpy.data.collections.new('LuoghiLuna')
        for n in luoghi:
            o = bpy.data.objects.get(n)
            if o is not None and o.type == 'MESH':
                col.objects.link(o)
        d2 = moon.data.copy()
        d2.energy = moon.data.energy * BUIO['luna_luoghi']
        m2 = bpy.data.objects.new('MoonLuoghi', d2)
        bpy.data.collections['env'].objects.link(m2)
        m2.rotation_mode = moon.rotation_mode
        m2.rotation_quaternion = moon.rotation_quaternion
        m2.lightgroup = 'ambient'
        m2.light_linking.receiver_collection = col
        moon.data.energy *= BUIO['luna']
    env_col = bpy.data.collections['env']
    fatti = set()
    for o in list(env_col.all_objects):
        nome = o.name
        faro = nome.startswith(('Lighthouse', 'KeeperHouse'))
        k = BUIO['faro'] if faro else BUIO['luoghi'] if nome in luoghi else BUIO['paese']
        if o.type == 'LIGHT':
            if nome.startswith('Moon'):
                continue
            o.data.energy *= k
            continue
        if o.type != 'MESH':
            continue
        for slot in o.material_slots:
            m = slot.material
            if m is None or m.name in fatti:
                continue
            fatti.add(m.name)
            scala_emissione(m, k)
    # meno lampioni lungo i tornanti del paese: uno su tre
    lamp_m = bpy.data.materials.get('StreetLamp')
    k = 0
    for o in list(env_col.all_objects):
        if o.type == 'MESH' and o.material_slots and o.material_slots[0].material is lamp_m:
            if k % 3:
                o.hide_render = True
            k += 1


def costruisci_nebbia():
    """La nebbia: una scatola attorno alla barca col volume. La densità è la foschia bassa sull'acqua (sfilacciata
    dal rumore, che cala in fretta salendo) più una nebbia rada e alta; sotto il pelo dell'acqua niente."""
    import bpy
    from common import collection, set_lightgroup
    from nodes import material
    P = NEBBIA
    R, H = P['raggio'], P['alto']
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, H / 2 - 1.0))
    ob = bpy.context.object
    ob.name = 'Nebbia'
    ob.scale = (2 * R, 2 * R, H + 2.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    collection('env').objects.link(ob)
    m, g = material('Nebbia')
    co = g.geometry('Position')
    x, y, z = g.sep(co)
    # banchi grandi (decine di metri) schiacciati in orizzontale, con le sfilacciature più fini dentro
    banchi = g.noise(g.mapping(co, scale=(0.020, 0.020, 0.11)), scale=1.0, detail=4.0, rough=0.55, distortion=0.6)
    fili = g.noise(g.mapping(co, scale=(0.09, 0.05, 0.45)), scale=1.0, detail=3.0, rough=0.5)
    var = g.add(g.mul(g.smoothstep(0.30, 0.72, banchi.fac), 1.25), g.mul(g.sub(fili.fac, 0.5), 0.6))
    var = g.math('MAXIMUM', g.add(var, 0.18), 0.05)
    bassa = g.mul(g.math('EXPONENT', g.mul(z, -1.0 / P['bassa_h'])), g.mul(var, P['bassa']))
    alta = g.mul(g.math('EXPONENT', g.mul(z, -1.0 / P['alta_h'])), g.mul(g.add(0.7, g.mul(banchi.fac, 0.6)), P['alta']))
    r2 = g.add(g.mul(x, x), g.mul(y, y))
    vicino = g.mul(g.math('EXPONENT', g.mul(r2, -1.0 / P['vicino_r'] ** 2)),
                   g.mul(g.math('EXPONENT', g.mul(z, -1.0 / 9.0)), g.mul(g.add(0.6, g.mul(var, 0.4)), P['vicino'])))
    dens = g.mul(g.add(g.add(bassa, alta), vicino), g.smoothstep(-0.25, 0.05, z))
    vol = g.node('ShaderNodeVolumePrincipled')
    g.set(vol, 'Color', (*P['colore'], 1.0))
    g.set(vol, 'Density', dens)
    g.set(vol, 'Anisotropy', P['anisotropia'])
    out = g.node('ShaderNodeOutputMaterial')
    g.nt.links.new(vol.outputs[0], out.inputs['Volume'])
    ob.data.materials.append(m)
    set_lightgroup(ob, 'ambient')
    sc = bpy.context.scene
    sc.cycles.volume_bounces = 1
    sc.cycles.volume_step_rate = 4.0
    sc.cycles.volume_max_steps = 512
    return ob


# ───────────────────────── render ─────────────────────────

def arg(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def job_render():
    import bpy
    import jobs
    import post
    from common import perspective_camera, render
    modo = sys.argv[2]
    yaw = float(arg('--yaw', 0.0))
    pitch = float(arg('--pitch', -12.0))
    samples = int(arg('--samples', 256))
    W, H = (int(v) for v in arg('--size', '1600x900').split('x'))
    creatura = arg('--creatura', '')
    nome = arg('--nome', 'prua')
    # la scena (come jobs.build_scene) si costruisce una volta sola e si salva: i mostri e la costa fatti a SDF
    # richiedono minuti. Gli oggetti dei posti del binocolo portano la proprietà 'luogo'
    blend = os.path.join(OUT, f'scena_{creatura or "vuota"}.blend')
    if os.path.exists(blend) and '--ricostruisci' not in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=blend)
    else:
        import boat
        import env
        import landmarks
        import props
        from common import reset_scene
        reset_scene()
        env.build_environment(with_glow=True)
        prima = set(bpy.data.objects.keys())
        landmarks.build_landmarks()
        for n in set(bpy.data.objects.keys()) - prima:
            bpy.data.objects[n]['luogo'] = 1
        parts, mats = boat.build_boat(fish_in_bucket=0, rod=False)
        parts['props'] += props.build_props()
        if creatura:
            import scena_creature
            scena_creature.POSES[creatura][0]()
        os.makedirs(OUT, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend)
    luoghi = {o.name for o in bpy.data.objects if 'luogo' in o.keys()}
    w = bpy.context.scene.world
    w.mist_settings.start = 0.0
    w.mist_settings.depth = 2500.0
    w.mist_settings.falloff = 'LINEAR'
    if modo == 'dopo':
        applica_buio(luoghi)
        if '--senza-nebbia' not in sys.argv:
            costruisci_nebbia()
    a, e = math.radians(yaw), math.radians(pitch)
    d = (math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))
    tgt = (EYE[0] + d[0], EYE[1] + d[1], EYE[2] + d[2])
    perspective_camera(EYE, tgt, lens=18.0, sensor=36.0)   # 90° in orizzontale, come la vista del gioco
    exr = os.path.join(OUT, f'{nome}_{modo}.exr')
    t = time.time()
    render(exr, samples, (W, H), data_passes=('Mist',))
    dt = time.time() - t
    log(f'atmosfera {nome} {modo}: {dt:.0f} s a {W}x{H}, {samples} campioni')
    with open(os.path.join(OUT, f'{nome}_{modo}.tempo'), 'w') as f:
        f.write(f'{dt:.1f} {W} {H} {samples}\n')


# ───────────────────────── composizione come il motore ─────────────────────────

PITCH = {'poppa': -3.0}   # come in job_render (--pitch)
PESI = {'alta': 1.7, 'bassa': 1.0, 'spenta': 0.0}   # stage.lampWeight(): livello 2 → 1 + 0,7


def nebbia_motore(c, mist, W, H, yaw, pitch):
    """La nebbia di distanza del motore di oggi (WORLD_FS in src/engine/shaders.ts), senza il banco che si muove."""
    dist = mist * 2500.0
    fog = 1.0 - np.exp(-dist / 3200.0)
    sky = mist > 0.999
    # latitudine di ogni pixel (per lo schiarimento del cielo all'orizzonte)
    tx = math.tan(math.radians(45.0))
    ty = tx * H / W
    ys = 1 - (np.arange(H) + 0.5) / H * 2
    lat = np.degrees(np.arctan2(ys * ty, 1.0)) + pitch
    horizon = np.exp(-np.abs(np.radians(lat)) * 22.0)[:, None] * np.ones((1, W))
    fog = np.where(sky, horizon * 0.35, fog)
    col = np.array((0.006, 0.010, 0.017))
    f = np.clip(fog, 0, 0.92)[..., None]
    return c * (1 - f) + col * f


def finale(lin, exposure=1.0):
    """FINAL_FS: bloom, esposizione, AgX col look noir, vignetta, grana."""
    import post
    from scipy.ndimage import gaussian_filter
    H, W = lin.shape[:2]
    br = np.maximum(lin - 0.6, 0.0)
    bl = np.zeros_like(lin)
    for rad, w in ((W / 160, 0.5), (W / 50, 0.35), (W / 16, 0.15)):
        bl += gaussian_filter(br, (rad, rad, 0)) * w
    hdr = (lin + bl * 0.16 * 4.0) * (2.0 ** exposure)
    col = post.tonemap(hdr, 0.0)
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = (xx + 0.5) / W - 0.5, (yy + 0.5) / H - 0.5
    r2 = cx * cx + cy * cy
    s = np.clip((r2 - 0.08) / (0.6 - 0.08), 0, 1)
    col = col * (1 - 0.55 * (s * s * (3 - 2 * s)))[..., None]
    rng = np.random.default_rng(3)
    g = rng.random((H, W)) - 0.5
    col = col + (g * 0.035)[..., None] * (0.6 + 0.4 * (1 - col.mean(-1, keepdims=True)))
    return np.clip(col, 0, 1)


def carica(nome, modo):
    import post
    p = post.read_exr(os.path.join(OUT, f'{nome}_{modo}.exr'))
    g = lambda k: p[k][..., :3] if k in p else 0.0
    return g('ambient'), g('lamp'), g('lantern'), p['mist']


def liscia_lontano(lamp, mist, sigma=None):
    """La luce della lampara che la nebbia diffonde lontano (dove si vede il cielo o la riva) è debole e
    liscissima, ma Cycles la trova con pochi campioni e il denoiser la lascia a chiazze. Oltre una trentina di
    metri la si sostituisce con la sua media su un intorno largo, una convoluzione normalizzata sui soli pixel
    lontani: così non ci entrano la reticella e la barca, che sono vicine."""
    from scipy.ndimage import gaussian_filter
    H, W = mist.shape
    sigma = sigma or W / 90.0
    dist = mist * 2500.0
    w = np.clip((dist - 15.0) / 45.0, 0.0, 1.0)
    w = w * w * (3 - 2 * w)
    num = gaussian_filter(lamp * w[..., None], (sigma, sigma, 0))
    den = gaussian_filter(w, sigma)[..., None]
    liscia = num / np.maximum(den, 1e-4)
    return lamp * (1 - w[..., None]) + liscia * w[..., None]


def immagine(nome, modo, livello, motore_fog):
    amb, lamp, lant, mist = carica(nome, modo)
    if modo == 'dopo':
        # il passo mist di Cycles si accumula anche nei volumi: le distanze vere vengono dal render senza nebbia
        # (stessa camera, stessa scena); per il panorama servirà il passo Depth
        vero = os.path.join(OUT, f'{nome}_prima.exr')
        lamp = liscia_lontano(lamp, carica(nome, 'prima')[3] if os.path.exists(vero) else mist)
    lin = amb + PESI[livello] * lamp + lant
    if motore_fog:
        H, W = mist.shape
        lin = nebbia_motore(lin, mist, W, H, 0.0, PITCH.get(nome, -12.0))
    return finale(lin)


def salva_jpg(arr, path, q=92):
    from PIL import Image
    Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path, quality=q)
    log('scritto', path)


def etichetta(arr, testo):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))
    d = ImageDraw.Draw(im)
    fonts = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
    try:
        ttf = [f for f in os.listdir(fonts) if f.lower().endswith('.ttf')]
        font = ImageFont.truetype(os.path.join(fonts, ttf[0]), max(18, im.width // 45))
    except Exception:
        font = ImageFont.load_default()
    d.text((im.width // 40, im.height // 30), testo, fill=(225, 215, 190), font=font)
    return np.asarray(im).astype(np.float32) / 255.0


def job_componi():
    os.makedirs(CONCEPT, exist_ok=True)
    for liv in ('alta', 'bassa', 'spenta'):
        salva_jpg(immagine('prua', 'dopo', liv, False), os.path.join(CONCEPT, f'atmosfera_prua_{liv}.jpg'))
    prima = etichetta(immagine('prua', 'prima', 'alta', True), 'Prima: il look di oggi (lampara alta)')
    dopo = etichetta(immagine('prua', 'dopo', 'alta', False), 'Dopo: nebbia volumetrica, scena più buia (lampara alta)')
    salva_jpg(np.concatenate([prima, dopo], axis=0), os.path.join(CONCEPT, 'atmosfera_prima_dopo.jpg'))
    for extra in ('poppa',):
        if os.path.exists(os.path.join(OUT, f'{extra}_dopo.exr')):
            salva_jpg(immagine(extra, 'dopo', 'alta', False), os.path.join(CONCEPT, f'atmosfera_{extra}_alta.jpg'))
            if os.path.exists(os.path.join(OUT, f'{extra}_prima.exr')):
                a = etichetta(immagine(extra, 'prima', 'alta', True), 'Prima')
                b = etichetta(immagine(extra, 'dopo', 'alta', False), 'Dopo')
                salva_jpg(np.concatenate([a, b], axis=0), os.path.join(CONCEPT, f'atmosfera_{extra}_prima_dopo.jpg'))


if __name__ == '__main__':
    {'render': job_render, 'componi': job_componi}[sys.argv[1]]()
