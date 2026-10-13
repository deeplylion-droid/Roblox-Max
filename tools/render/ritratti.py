"""
I ritratti del menu principale (scelta dell'utente del 13 ottobre: la proposta A «Il ritratto», come il titolo di FNAF;
il risultato è da approvare). Un mostro da vicino, nel buio, dalla barca, con la sua posa di gioco: a destra la faccia,
a sinistra il buio della baia dove sta il menu. Il gioco li mostra in src/app/ritratti.ts.

Tre passi, perché costruire i mostri è lungo (10-15 minuti l'uno) e il render no:
  scena <uscita.blend> <chi,chi…>   costruisce mondo, barca e mostri (ognuno nella sua posa di gioco) e li salva
  rendi <scena.blend> <chi> <uscita.png> [W H campioni]   il ritratto (CAMERE: inquadratura e luci di ognuno)
  immagini <chi> <ritratto.png>      le immagini del gioco in public/assets/img/ritratti: <chi>.webp, il ritratto
                                     fermo, e <chi>_scatto1/2.webp, i due fotogrammi dello scatto col segnale disturbato

Uso: tools/.venv/bin/python tools/render/ritratti.py scena tools/render/cache/ritratti.blend molly,hatch,gulpy
     tools/.venv/bin/python tools/render/ritratti.py rendi tools/render/cache/ritratti.blend molly /tmp/molly.png 1920 1080 40
     tools/.venv/bin/python tools/render/ritratti.py immagini molly /tmp/molly.png
"""
import math
import os
import sys
import time

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
RADICE = os.path.dirname(os.path.dirname(QUI))
USCITA = os.path.join(RADICE, 'public', 'assets', 'img', 'ritratti')

# Per ognuno: la posa (scena_creature), la distanza della camera dalla faccia (m), l'obiettivo (mm), dove sta la faccia
# nel quadro (frazione della larghezza dal centro, a destra), l'altezza della camera rispetto alla faccia (m), la luce
# calda da sotto (come la lanterna) e il controluce freddo (la luna), in watt; ty alza il punto guardato (m), per le
# teste lunghe; ev l'esposizione (Fangy è blu scuro); occhi: la faccia fra i suoi occhi (per Robin, Archie, Lampy e Fangy: la scena salvata la mette altrove)
CAMERE = {
    'molly': dict(posa='molly', dist=1.25, lens=28.0, dx=0.17, dz=-0.15, key=2.5, rim=4.0),
    'hatch': dict(posa='hatch_conta', dist=1.3, lens=32.0, dx=0.18, dz=-0.20, key=2.0, rim=3.0),
    'gulpy': dict(posa='gulpy_pretende', dist=2.6, lens=30.0, dx=0.16, dz=-0.30, key=3.5, rim=3.0, ty=0.25),
    'robin': dict(posa='robin_secchio', dist=1.1, lens=28.0, dx=0.17, dz=-0.15, key=2.0, rim=3.0, occhi=True),
    'archie': dict(posa='archie_soffia', dist=1.2, lens=35.0, dx=0.12, dz=-0.10, key=2.5, rim=3.0, occhi=True),
    'lampy': dict(posa='lampy_lenza', dist=1.9, lens=30.0, dx=0.18, dz=-0.15, key=2.0, rim=3.0, occhi=True),
    'fangy': dict(posa='fangy_ascolta', dist=1.5, lens=30.0, dx=0.17, dz=-0.05, key=6.0, rim=4.0, ty=0.12, ev=0.9, occhi=True),
}


def scena(out, chi):
    os.environ['ATMOSFERA'] = '1'
    import bpy
    from mathutils import Vector

    import jobs
    import scena_creature as sc
    from common import log
    t0 = time.time()
    jobs.build_scene()
    # la nebbia volumetrica no (il gioco parte senza): il buio della baia sì
    neb = bpy.data.objects.get('Nebbia')
    if neb:
        bpy.data.objects.remove(neb, do_unlink=True)

    def centro(obs):
        dg = bpy.context.evaluated_depsgraph_get()
        pts = [o.evaluated_get(dg).matrix_world @ Vector(c) for o in obs for c in o.evaluated_get(dg).bound_box]
        return sum(pts, Vector()) / len(pts)

    pose = {'molly': lambda: sc.molly(+1), 'hatch_conta': sc.hatch_conta, 'gulpy_pretende': sc.gulpy_pretende,
            'robin_secchio': lambda: sc.robin_secchio(), 'archie_soffia': lambda: sc.archie_soffia(),
            'lampy_lenza': lambda: sc.lampy_lenza(), 'fangy_ascolta': lambda: sc.fangy_ascolta()}
    for c in chi:
        prima = set(bpy.data.objects.keys())
        pose[CAMERE[c]['posa']]()
        nuovi = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - prima]
        for o in nuovi:
            o['ritratto'] = c
        # la faccia: il punto fra gli occhi, o il centro della testa
        occhi = [o for o in nuovi if o.type == 'MESH' and o.name.startswith(c.capitalize() + 'Eye') and 'Lid' not in o.name]
        teste = [o for o in nuovi if o.type == 'MESH' and any(k in o.name for k in ('Head', 'Testa'))]
        bpy.context.scene[f'faccia_{c}'] = list(centro(occhi or teste or [o for o in nuovi if o.type == 'MESH']))
        log(c, len(nuovi), 'oggetti', round(time.time() - t0), 's')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out), compress=False)
    log('salvata', out, round(time.time() - t0), 's')


def rendi(blend, chi, out, W=1920, H=1080, S=40):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    import numpy as np
    from mathutils import Vector
    from PIL import Image

    import post
    from common import EYE, perspective_camera, render
    P = CAMERE[chi]
    sc = bpy.context.scene
    for o in bpy.data.objects:
        c = o.get('ritratto')
        if c is not None:
            o.hide_render = o.hide_viewport = c != chi
    # la faccia: fra gli occhi del mostro (solo i suoi: Robin ha in mano un pesce con gli occhi), se no quella salvata
    occhi = [o for o in bpy.data.objects if o.get('ritratto') == chi and o.type == 'MESH' and o.name.startswith(chi.capitalize() + 'Eye')]
    if occhi and P.get('occhi'):
        dg = bpy.context.evaluated_depsgraph_get()
        pts = [o.evaluated_get(dg).matrix_world @ Vector(c) for o in occhi for c in o.evaluated_get(dg).bound_box]
        face = sum(pts, Vector()) / len(pts)
    else:
        face = Vector(sc[f'faccia_{chi}'])
    d = (face - Vector(EYE)).normalized()
    cam_pos = face - d * P['dist'] + Vector((0, 0, P['dz']))
    look = (face - cam_pos).normalized()
    right = look.cross(Vector((0, 0, 1))).normalized()
    L = (face - cam_pos).length
    # la faccia a dx della larghezza a destra del centro: la camera guarda un po' più a sinistra
    target = face - right * math.tan(math.atan(18.0 / P['lens'])) * 2 * P['dx'] * L + Vector((0, 0, P.get('ty', 0.0)))
    cam = perspective_camera(tuple(cam_pos), tuple(target), lens=P['lens'])
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = L
    cam.data.dof.aperture_fstop = 2.0

    def luce(nome, pos, energia, colore, gruppo, raggio):
        ld = bpy.data.lights.new(nome, 'POINT')
        ld.energy, ld.color, ld.shadow_soft_size = energia, colore, raggio
        lo = bpy.data.objects.new(nome, ld)
        sc.collection.objects.link(lo)
        lo.location = pos
        lo.lightgroup = gruppo

    # la luce calda da sotto, dalla parte della barca (come la lanterna), e un controluce freddo da dietro (la luna)
    luce('RitrattoKey', face - look * L * 0.55 - right * 0.25 + Vector((0, 0, -0.35)), P['key'], (1.0, 0.62, 0.30), 'lantern', 0.08)
    luce('RitrattoRim', face + look * 0.9 + right * 0.5 + Vector((0, 0, 0.6)), P['rim'], (0.55, 0.70, 1.0), 'ambient', 0.15)
    exr = os.path.splitext(out)[0] + '.exr'
    render(exr, S, (W, H), data_passes=())
    p = post.read_exr(exr)
    lin = post.rgb(p['ambient']) + 0.35 * post.rgb(p['lamp']) + post.rgb(p['lantern'])
    Image.fromarray((np.clip(post.tonemap(lin, P.get('ev', 0.4)), 0, 1) * 255 + 0.5).astype(np.uint8)).save(out)
    print('ritratto', out, flush=True)


def scatto(img, seme, forte, cx, cy):
    """Un fotogramma dello scatto: il quadro sobbalza (e col secondo la faccia viene avanti), i colori si separano,
    bande che saltano come un nastro, neve, righe chiare, meno colore."""
    import numpy as np
    rng = np.random.default_rng(seme)
    H, W, _ = img.shape
    out = img.copy()
    if not forte:
        # la faccia viene avanti di colpo: lo stesso quadro ingrandito attorno alla faccia
        from PIL import Image
        k = 1.08
        w2, h2 = W / k, H / k
        x0, y0 = min(max(cx * W - w2 * cx, 0), W - w2), min(max(cy * H - h2 * cy, 0), H - h2)
        im = Image.fromarray((out * 255).astype(np.uint8)).crop((x0, y0, x0 + w2, y0 + h2)).resize((W, H), Image.LANCZOS)
        out = np.asarray(im).astype(np.float32) / 255
    out = np.roll(out, (14, -22) if forte else (-6, 10), axis=(0, 1))
    sh = (10, -8) if forte else (6, -5)
    out = np.stack([np.roll(out[..., 0], sh[0], axis=1), out[..., 1], np.roll(out[..., 2], sh[1], axis=1)], -1)
    for _ in range(11 if forte else 5):
        y = int(rng.integers(0, H - 40))
        h = int(rng.integers(4, 46))
        out[y:y + h] = np.roll(out[y:y + h], int(rng.integers(-90, 90) if forte else rng.integers(-40, 40)), axis=1)
    out = out * 0.82 + rng.random((H, W, 1)).astype(np.float32) * (0.20 if forte else 0.12)
    for _ in range(5 if forte else 3):
        y = int(rng.integers(0, H))
        out[y:y + 2] = np.clip(out[y:y + 2] + 0.35, 0, 1)
    l = out.mean(-1, keepdims=True)
    out = l + (out - l) * 0.7
    return np.clip((out - 0.5) * 1.15 + 0.5, 0, 1)


def immagini(chi, png):
    import numpy as np
    from PIL import Image
    os.makedirs(USCITA, exist_ok=True)
    im = Image.open(png).convert('RGB')
    im.save(os.path.join(USCITA, f'{chi}.webp'), quality=88, method=6)
    a = np.asarray(im).astype(np.float32) / 255
    cx = 0.5 + CAMERE[chi]['dx']
    for i, forte in ((1, True), (2, False)):
        s = scatto(a, 7 + i, forte, cx, 0.5)
        Image.fromarray((s * 255 + 0.5).astype(np.uint8)).save(os.path.join(USCITA, f'{chi}_scatto{i}.webp'), quality=80, method=6)
    print('immagini', chi, USCITA, flush=True)


if __name__ == '__main__':
    cmd, *a = sys.argv[1:]
    if cmd == 'scena':
        scena(a[0], a[1].split(','))
    elif cmd == 'rendi':
        rendi(a[0], a[1], a[2], *map(int, a[3:6]))
    elif cmd == 'immagini':
        immagini(a[0], a[1])
    else:
        sys.exit(__doc__)
