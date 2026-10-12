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
    shore = Vector(env.surface_at(192.6, 6.0))
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


if __name__ == '__main__':
    main()
