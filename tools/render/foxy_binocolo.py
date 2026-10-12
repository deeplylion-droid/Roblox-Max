"""
L'ANIMATORE nel binocolo — anteprima dei posti, da far approvare (non tocca le immagini del gioco).

Rifà le viste del binocolo di due luoghi (come binocolo.py, con la stessa scena e gli stessi dettagli di lore)
con dentro una sagoma provvisoria del mostro (la variante A della tavola, in bozza), in tre stadi:
  lontano    fermo nel suo posto, piccolo, ti guarda
  vicino     è sceso più vicino alla barca (lo hai trascurato)
  vuoto      il posto è vuoto: sta per saltare sulla barca

I luoghi proposti:
  scivoli    in cima alla torre degli scivoli, sotto il tetto rosso → poi giù, sulla battigia
  relitto    in piedi sulla tuga del peschereccio affondato → poi in acqua fino alla vita, davanti al relitto

Le immagini escono in tools/render/cache/foxy/bino/<luogo>_<stadio>.webp, codificate come quelle del gioco
(passo 'ambient' con la stessa scala del manifesto, la nebbia nel canale alfa): si possono provare nel gioco
vero sostituendole al volo (tools/render/foxy_binocolo_cattura.mjs), senza toccare public/.

Uso: tools/.venv/bin/python tools/render/foxy_binocolo.py [--luoghi scivoli,relitto] [--samples N]
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if '--fast' not in sys.argv:
    sys.argv.append('--fast')        # la sagoma provvisoria si estrae grossolana: da 170-460 m è alta 60-150 pixel

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image  # noqa: E402

import binocolo  # noqa: E402
import env  # noqa: E402
import foxy_concept as FX  # noqa: E402
import jobs  # noqa: E402
import post  # noqa: E402
from common import CACHE, EYE, ROOT, perspective_camera, render  # noqa: E402
from landmarks import facing, transform  # noqa: E402

OUT = os.path.join(CACHE, 'foxy', 'bino')
OVERLAYS = os.path.join(ROOT, 'public', 'assets', 'img', 'overlays.json')


def wreck_house_top():
    """Il centro del tetto della tuga del relitto (affondato di poppa e sbandato), in coordinate del mondo."""
    ob = bpy.data.objects['WreckHouse']
    bpy.context.view_layer.update()
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    top = max(pts, key=lambda v: v.z)
    c = sum(pts, Vector()) / 8
    return Vector((c.x, c.y, top.z - 0.35))


def spots():
    """{luogo: {stadio: (posizione dei piedi, yaw in più)}}."""
    tx, ty, tz = env.surface_at(193.0, 45.0)
    to_eye = Vector((EYE[0] - tx, EYE[1] - ty, 0)).normalized()
    side = Vector((-to_eye.y, to_eye.x, 0))
    top = Vector((tx, ty, tz + 21.8)) + to_eye * 2.4 + side * 0.6
    # ai piedi della torre, davanti agli scivoli: sulla battigia la foschia bassa sull'acqua lo nascondeva
    shore = Vector(env.surface_at(192.4, 28.0))
    wt = wreck_house_top()
    w_eye = Vector((EYE[0] - wt.x, EYE[1] - wt.y, 0)).normalized()
    water = Vector((wt.x, wt.y, -0.95)) + w_eye * 9.0 + Vector((-w_eye.y, w_eye.x, 0)) * 2.5
    return {
        'scivoli': {'lontano': (top, 0.0), 'vicino': (shore, 0.0), 'vuoto': None},
        'relitto': {'lontano': (wt, 0.0), 'vicino': (water, 0.0), 'vuoto': None},
    }


def aims(sp):
    """Dove puntare il binocolo per ogni stadio (yaw e pitch dall'occhio del pescatore al petto del mostro;
    il posto vuoto si guarda dove stava da lontano), per la cattura nel gioco."""
    out = {}
    for luogo, stadi in sp.items():
        far = stadi['lontano'][0]
        for stadio, spot in stadi.items():
            p = (spot[0] if spot else far) + Vector((0, 0, 1.3))
            d = p - Vector(EYE)
            out[f'{luogo}_{stadio}'] = {'yaw': math.degrees(math.atan2(d.x, d.y)),
                                        'pitch': math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))}
    return out


def build_figure():
    """La sagoma provvisoria: la variante A della tavola, intera."""
    before = set(bpy.data.objects)
    obs, _, _ = FX.build(FX.VARIANTS['A'])
    return [o for o in bpy.data.objects if o not in before and o.type == 'MESH']


def main():
    if '--mire' in sys.argv:
        # solo i punti di mira (per la cattura): bastano i luoghi, senza render
        from common import reset_scene
        import landmarks
        reset_scene()
        landmarks.build_landmarks()
        json.dump(aims(spots()), open(os.path.join(OUT, 'mire.json'), 'w'), indent=1)
        print(open(os.path.join(OUT, 'mire.json')).read())
        return
    luoghi = ['scivoli', 'relitto']
    if '--luoghi' in sys.argv:
        luoghi = sys.argv[sys.argv.index('--luoghi') + 1].split(',')
    samples = int(sys.argv[sys.argv.index('--samples') + 1]) if '--samples' in sys.argv else 48
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    jobs.build_scene(fish=0, rod=False)
    for o in jobs.coll_objects('boat'):
        o.visible_camera = False
    binocolo.lore_banner()
    binocolo.lore_statue_eye()
    binocolo.lore_wheel_child()
    binocolo.lore_camcorder()
    binocolo.lore_photos()
    binocolo.lore_tally()
    fill = binocolo.wreck_fill()
    for k in range(2):
        fl = bpy.data.objects.get(f'MarinaFlood{k}')
        if fl:
            fl.data.energy *= 0.3
    print('scena', round(time.time() - t0), 's', flush=True)
    fig = build_figure()
    for o in fig:
        from common import set_lightgroup
        set_lightgroup(o, 'ambient')
    bpy.context.view_layer.update()
    rest = {o.name: o.matrix_world.copy() for o in fig}
    places = {k: (t, h, r) for k, t, h, r in binocolo.places()}
    scales = {p['key']: p['scale'] for p in json.load(open(OVERLAYS))['binocular']['places']}
    for luogo in luoghi:
        target, hfov, (W, H) = places[luogo]
        if fill:
            fill.hide_render = luogo != 'relitto'
        perspective_camera(EYE, target, lens=18.0 / math.tan(math.radians(hfov) / 2), name=f'Bino_{luogo}')
        for stadio, spot in spots()[luogo].items():
            for o in fig:
                o.matrix_world = rest[o.name]
                o.hide_render = spot is None
            if spot is not None:
                pos, dyaw = spot
                transform(fig, tuple(pos), yaw_deg=facing(tuple(pos)) + dyaw)
            exr = os.path.join(OUT, f'{luogo}_{stadio}.exr')
            t = time.time()
            render(exr, samples, (W, H), data_passes=('Mist',))
            p = post.read_exr(exr)
            lin = post.rgb(p['ambient'])
            a8 = np.clip(np.clip(p['mist'], 0, 1) * 255 + 0.5, 0, 255).astype(np.uint8)
            rgb8 = np.asarray(post.encode_light_pass(lin, scales[luogo]))
            post.save_webp(Image.fromarray(np.dstack([rgb8, a8]), 'RGBA'), os.path.join(OUT, f'bino_{luogo}_{stadio}.webp'), quality=92)
            print('ok', luogo, stadio, round(time.time() - t), 's', flush=True)


# ───────────────────────── le viste definitive (il modello vero, con l'atmosfera) ─────────────────────────
# Per ogni luogo: il posto vuoto reso intero (bino_<luogo>.webp), poi l'animatore nei due stadi reso solo nel
# riquadro attorno a lui e incollato sul vuoto con la maschera del suo indice oggetto: fuori dalla sagoma le tre
# immagini sono identiche pixel per pixel (quando se ne va non si vede il salto). Stessa inquadratura, dimensione
# e scala di codifica: la scala si sceglie sul vuoto e vale per tutte e tre.
# Uso: ATMOSFERA=1 tools/.venv/bin/python tools/render/foxy_binocolo.py --definitivo [--luoghi ...] [--samples N]
# (con RENDER_OUT=<cartella> le immagini vanno lì e il manifesto non si tocca: per le prove)

IDX_FOXY = 7
STADI_DEF = (('foxy0', 'lontano'), ('foxy1', 'vicino'))
RIM = {'foxy0': 260.0, 'foxy1': 650.0}     # il filo di luce da dietro (watt): più vicino all'acqua c'è più foschia


def light_only(name, objs, loc, target, energy, color, size):
    """Una luce d'area che illumina solo gli oggetti dati (light linking)."""
    from common import set_lightgroup
    col = bpy.data.collections.new(name + 'Ric')
    for o in objs:
        col.objects.link(o)
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy, ld.color, ld.size = energy, color, size
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y')
    ob.light_linking.receiver_collection = col
    set_lightgroup(ob, 'ambient')
    return ob


def exclude_from(light, objs):
    """Toglie gli oggetti dalla luce (light linking in esclusione)."""
    col = bpy.data.collections.new(light.name + 'Escl')
    for o in objs:
        col.objects.link(o)
    light.light_linking.receiver_collection = col
    for co in col.collection_objects:
        co.light_linking.link_state = 'EXCLUDE'


def screen_rect(cam, objs, W, H, pad=28):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    xs, ys = [], []
    for o in objs:
        for c in o.bound_box:
            v = world_to_camera_view(sc, cam, o.matrix_world @ Vector(c))
            xs.append(v.x * W)
            ys.append((1 - v.y) * H)
    x0, x1 = max(0, int(min(xs)) - pad), min(W, int(max(xs)) + pad)
    y0, y1 = max(0, int(min(ys)) - pad), min(H, int(max(ys)) + pad)
    return x0, y0, x1, y1


def mist_of(p):
    d = np.where(np.isfinite(p['depth']), p['depth'], 1e9)
    return np.sqrt(np.clip(d / 2500.0, 0.0, 1.0))


def definitivo():
    from scipy.ndimage import binary_dilation, gaussian_filter
    import animatore
    from common import OUT_IMG, set_lightgroup
    assert os.environ.get('ATMOSFERA'), 'le viste definitive vanno rese con ATMOSFERA=1'
    luoghi = ['scivoli', 'relitto']
    if '--luoghi' in sys.argv:
        luoghi = sys.argv[sys.argv.index('--luoghi') + 1].split(',')
    samples = int(sys.argv[sys.argv.index('--samples') + 1]) if '--samples' in sys.argv else 64
    out_dir = os.path.join(CACHE, 'foxy', 'bino_def')
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    jobs.build_scene(fish=0, rod=False)
    for o in jobs.coll_objects('boat'):
        o.visible_camera = False
    binocolo.lore_banner()
    binocolo.lore_statue_eye()
    binocolo.lore_wheel_child()
    binocolo.lore_camcorder()
    binocolo.lore_photos()
    binocolo.lore_tally()
    fill = binocolo.wreck_fill()
    for k in range(2):
        fl = bpy.data.objects.get(f'MarinaFlood{k}')
        if fl:
            fl.data.energy *= 0.3
    sp = spots()
    before = set(bpy.data.objects)
    animatore.build('riposo')
    fig = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    for o in fig:
        set_lightgroup(o, 'ambient')
        o.pass_index = IDX_FOXY
    # la luna dei posti del binocolo (atmosfera.py) prende anche lui
    lc = bpy.data.collections.get('LuoghiLuna')
    if lc:
        for o in fig:
            lc.objects.link(o)
    # il riempimento azzurro del relitto (binocolo.wreck_fill) non lo tocca: lo faceva blu saturo
    if fill:
        exclude_from(fill, fig)
    bpy.context.view_layer.update()
    rest = {o.name: o.matrix_world.copy() for o in fig}
    bpy.context.view_layer.use_pass_object_index = True
    bpy.context.view_layer.use_pass_z = True
    print('scena', round(time.time() - t0), 's', flush=True)
    places = {k: (t, h, r) for k, t, h, r in binocolo.places()}
    entries = []
    for luogo in luoghi:
        target, hfov, (W, H) = places[luogo]
        if fill:
            fill.hide_render = luogo != 'relitto'
        cam = perspective_camera(EYE, target, lens=18.0 / math.tan(math.radians(hfov) / 2), name=f'Bino_{luogo}')
        # il vuoto, intero
        for o in fig:
            o.hide_render = True
        exr = os.path.join(out_dir, f'{luogo}_vuoto.exr')
        t = time.time()
        # FOXY_RIUSA=1: il vuoto già reso si riusa (per ritoccare solo l'animatore)
        if not (os.environ.get('FOXY_RIUSA') and os.path.exists(exr)):
            render(exr, samples, (W, H), data_passes=('Depth',))
        p = post.read_exr(exr)
        base = post.rgb(p['ambient']).copy()
        bmist = mist_of(p)
        scale = post.pick_scale(base, pct=99.5)
        print('ok', luogo, 'vuoto', round(time.time() - t), 's', flush=True)
        outs = {'': (base, bmist)}
        for tag, stadio in STADI_DEF:
            pos, dyaw = sp[luogo][stadio]
            for o in fig:
                o.matrix_world = rest[o.name]
                o.hide_render = False
            transform(fig, tuple(pos), yaw_deg=facing(tuple(pos)) + dyaw)
            # un filo di luce fredda da dietro e dall'alto, solo su di lui: la sagoma si stacca dal fondo
            to_eye = (Vector(EYE) - pos)
            to_eye.z = 0
            to_eye.normalize()
            side = Vector((-to_eye.y, to_eye.x, 0))
            rim = light_only(f'FoxyRim_{luogo}_{tag}', fig, pos - to_eye * 3.0 + side * 1.6 + Vector((0, 0, 3.4)), pos + Vector((0, 0, 1.2)),
                             RIM[tag] * float(os.environ.get('FOXY_RIM', '1')), (0.70, 0.80, 1.0), 1.2)
            x0, y0, x1, y1 = screen_rect(cam, fig, W, H)
            exr = os.path.join(out_dir, f'{luogo}_{tag}.exr')
            t = time.time()
            render(exr, samples * 2, (W, H), region=(x0, y0, x1, y1), data_passes=('Depth', 'Object Index'))
            q = post.read_exr(exr)
            h_, w_ = y1 - y0, x1 - x0
            lin_r = post.rgb(q['ambient'])[:h_, :w_]
            mist_r = mist_of(q)[:h_, :w_]
            m = binary_dilation(np.abs(q['index'][:h_, :w_] - IDX_FOXY) < 0.5, iterations=2)
            m = np.clip(gaussian_filter(m.astype(np.float32), 1.0) * 1.4, 0, 1)
            # il render ha l'origine in basso? read_exr dà le righe dall'alto come l'immagine intera
            lin = base.copy()
            mi = bmist.copy()
            lin[y0:y1, x0:x1] = lin[y0:y1, x0:x1] * (1 - m[..., None]) + lin_r * m[..., None]
            mi[y0:y1, x0:x1] = mi[y0:y1, x0:x1] * (1 - m) + mist_r * m
            outs['_' + tag] = (lin, mi)
            rim.hide_render = True
            print('ok', luogo, tag, round(time.time() - t), 's', (x0, y0, x1, y1), flush=True)
        for suf, (lin, mi) in outs.items():
            rgb8 = np.asarray(post.encode_light_pass(lin, scale))
            a8 = np.clip(mi * 255 + 0.5, 0, 255).astype(np.uint8)
            # senza perdita: il vuoto e le versioni con l'animatore devono combaciare pixel per pixel fuori dalla sagoma
            # (la compressione con perdita cambia un po' tutta l'immagine se cambia un riquadro)
            post.save_webp(Image.fromarray(np.dstack([rgb8, a8]), 'RGBA'), os.path.join(OUT_IMG, f'bino_{luogo}{suf}.webp'), lossless=True)
        d = Vector(target) - Vector(EYE)
        entries.append({'key': luogo, 'file': f'bino_{luogo}.webp', 'scale': scale,
                        'yaw': round(math.degrees(math.atan2(d.x, d.y)), 3),
                        'pitch': round(math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), 3),
                        'hfov': hfov, 'aspect': round(W / H, 4)})
    if os.environ.get('RENDER_OUT'):
        # prove fuori dal gioco: il manifesto non si tocca
        json.dump(entries, open(os.path.join(OUT_IMG, 'bino_foxy_entries.json'), 'w'), indent=1)
        print('fatto (prova)', round(time.time() - t0), 's', flush=True)
        return
    old = json.load(open(OVERLAYS)).get('binocular', {})
    keep = [e for e in old.get('places', []) if e['key'] not in {x['key'] for x in entries}]
    post.update_manifest(OVERLAYS, 'binocular', {'places': sorted(keep + entries, key=lambda e: e['key']), 'rec': old.get('rec')})
    print('fatto', round(time.time() - t0), 's', flush=True)


if __name__ == '__main__':
    if '--definitivo' in sys.argv:
        definitivo()
    else:
        main()
