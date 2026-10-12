"""
L'ANIMATORE — modello definitivo (variante B «Fradicio», scelta l'11 ottobre). Il nome lo sceglie l'utente.

L'animatore di Splashland annegato dentro il costume di Mama Marina. Il costume gonfio d'acqua cede: curvo,
la pancia che pende, la testa della balena crollata di lato. Dalle pinne sfondate escono le sue mani, lunghe
e ossute, con le dita aperte; la sua faccia gonfia è spinta fuori dalla bocca del costume, sopra il labbro di
stoffa. L'occhio sinistro da cartone è strappato via, il destro penzola da un brandello e dondola.

I pezzi (peluche fradicio, gommapiuma, la testa dell'uomo, le mani, la melma) sono quelli della tavola
(foxy_concept.py); qui ci sono le pose:
  riposo      in piedi, le braccia che pendono e le mani aperte (il binocolo)
  abbraccio   le braccia alzate verso chi guarda, le dita aperte (il jumpscare: «Lo spettacolo finiva sempre
              con un abbraccio.»)
e 'occhio' (gradi) fa dondolare l'occhio che penzola.

Coordinate: i piedi a z = 0, la faccia guarda −Y.

Uso (vetrina): tools/.venv/bin/python tools/render/animatore.py [--fast] [--tavola]
     (tavola dei fotogrammi del jumpscare, dagli js_foxy_* del gioco: animatore.py --js-tavola)
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import foxy_concept as FX  # noqa: E402
import sdf  # noqa: E402
from common import CACHE, ROOT, reset_scene  # noqa: E402
from dettagli import V  # noqa: E402

FAST = FX.FAST
TMP = os.path.join(CACHE, 'animatore')
OUT = os.path.join(ROOT, 'docs', 'concept')

# la variante B della tavola, con le mani definitive e il collo dell'uomo nascosto sotto il labbro di stoffa
BASE = dict(FX.VARIANTS['B'])
BASE.update(
    bony=True, hand_k=1.25, hand_spread=0.95, curl=0.22, hand_res=0.0018,
    neck_end=-0.15,
    macera=2.2, labbra_gonfie=True,
)

POSE = {
    'riposo': dict(),
    # le braccia si alzano verso chi guarda, i gomiti in fuori, le mani aperte che vengono avanti per l'abbraccio
    'abbraccio': dict(
        armR=((0.66, -0.58, 1.02), (0.46, -0.94, 0.98)),
        armL=((-0.64, -0.52, 1.04), (-0.44, -0.90, 1.00)),
        hand_dir={1: (-0.55, -1.0, 0.10), -1: (0.55, -1.0, 0.12)},
        hand_up={1: (1.0, 0.1, 0.25), -1: (-1.0, 0.1, 0.25)},
        curl=0.38, fin_len=0.20,
    ),
}

EYE_HANG = V(0.05, -0.06, -0.36)


def face_point(P):
    """Dove sta la faccia dell'uomo (come in foxy_concept.build), per mettere le mani attorno a lei."""
    hfr = FX.Fr(V(*P['head_c']), FX.rot(P['head_yaw'], P['head_pitch'], P['head_roll']))
    mfr = FX.Fr(hfr.pt(P['man_off']), hfr.R @ FX.rot(*P['man_rot']))
    return mfr.pt((0, -0.10, 0.0))


# l'abbraccio del jumpscare: le mani ai lati della faccia, appena davanti a lei e un po' sotto, con le dita che si
# chiudono verso le guance (davanti di più finirebbero sull'obiettivo: la faccia arriva a mezzo metro dalla camera).
# Per ogni lato: polso rispetto alla faccia, gomito rispetto al polso, verso delle dita (x verso l'esterno del lato)
ABBRACCIO = {'polso': (0.36, -0.06, -0.14), 'gomito': (0.24, 0.30, -0.10), 'dita': (-0.85, -0.30, 0.35)}


def params(posa='riposo', occhio=0.0):
    """I parametri della posa; occhio: di quanti gradi dondola l'occhio che penzola (avanti +, indietro −)."""
    P = dict(BASE)
    P.update(POSE[posa])
    if posa == 'abbraccio':
        f = face_point(P)
        A = ABBRACCIO
        for s, key in ((1, 'armR'), (-1, 'armL')):
            sx = V(s, 1, 1)
            wrist = f + V(*A['polso']) * sx
            elbow = wrist + V(*A['gomito']) * sx
            d = (wrist - elbow) / np.linalg.norm(wrist - elbow)
            P[key] = (tuple(map(float, elbow)), tuple(map(float, wrist - d * 0.17)))
        P['hand_dir'] = {s: tuple(map(float, V(*A['dita']) * V(s, 1, 1))) for s in (1, -1)}
        P['hand_up'] = {s: (0.0, 0.3, 1.0) for s in (1, -1)}
    R = sdf.rot_matrix('x', -occhio) @ sdf.rot_matrix('y', occhio * 0.35)
    P['eye_hang'] = tuple(map(float, R @ EYE_HANG))
    P['eye_look'] = tuple(map(float, R @ V(-0.3, -0.5, -0.8)))
    return P


def build(posa='riposo', occhio=0.0, **extra):
    """Costruisce l'animatore nell'origine (extra: parametri in più, per esempio il peluche del binocolo).
    Restituisce (oggetti, punto della faccia)."""
    P = params(posa, occhio)
    P.update(extra)
    obs, face, _ = FX.build(P)
    return obs, face


# ───────────────────────── vetrina ─────────────────────────

SHOTS = [
    ('insieme', 'riposo', 0.0, ((-1.25, -4.6, 1.25), (0.0, -0.15, 1.05), 50), (720, 1040), 'in piedi, dalla parte della barca'),
    ('fianco', 'riposo', 0.0, ((-3.9, -2.3, 1.25), (0.0, 0.0, 1.0), 50), (720, 1040), 'di fianco: la coda della balena a terra'),
    ('faccia', 'riposo', 0.0, ((-0.22, -1.62, 1.20), None, 62), (720, 620), 'la faccia fuori dalla bocca, le orbite, i denti'),
    ('abbraccio', 'abbraccio', 18.0, ((-2.7, -3.0, 1.45), (0.0, -0.55, 1.08), 50), (720, 1040), "l'abbraccio (jumpscare): le mani avanti"),
]


def render_shots():
    os.makedirs(TMP, exist_ok=True)
    done = {}
    for key, posa, occhio, (loc, tgt, lens), (W, H), _ in SHOTS:
        blend = os.path.join(TMP, f'{posa}_{occhio:g}.blend')
        if blend not in done:
            reset_scene()
            _, face = build(posa, occhio)
            done[blend] = face
            bpy.ops.wm.save_as_mainfile(filepath=blend)
        face = done[blend]
        bpy.ops.wm.open_mainfile(filepath=blend)
        if FAST:
            W, H = W // 2, H // 2
        FX._setup_into(None, tgt if tgt is not None else tuple(map(float, face + V(0, 0, -0.03))), face, loc, lens, W, H)
        sc = bpy.context.scene
        sc.render.filepath = os.path.join(TMP, f'{key}.png')
        bpy.ops.render.render(write_still=True)
        print('ok', key, flush=True)


def tavola():
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf'
    tf = ImageFont.truetype(font.format('-Bold'), 30)
    sf = ImageFont.truetype(font.format(''), 20)
    ims = [Image.open(os.path.join(TMP, f'{k}.png')).convert('RGB') for k, *_ in SHOTS]
    H = 900
    ims = [im.resize((int(im.size[0] * H / im.size[1]), H), Image.LANCZOS) for im in ims]
    gap, head, foot = 14, 70, 44
    W = sum(im.size[0] for im in ims) + gap * (len(ims) + 1)
    sheet = Image.new('RGB', (W, head + H + foot), (12, 14, 19))
    d = ImageDraw.Draw(sheet)
    d.text((gap, 18), "L'ANIMATORE — modello definitivo (variante B «Fradicio»)", fill=(235, 228, 210), font=tf)
    x = gap
    for im, (_, _, _, _, _, label) in zip(ims, SHOTS):
        sheet.paste(im, (x, head))
        d.text((x + 4, head + H + 10), label, fill=(200, 196, 184), font=sf)
        x += im.size[0] + gap
    path = os.path.join(OUT, 'animatore_vetrina.jpg' if not FAST else 'animatore_vetrina_bozza.jpg')
    sheet.save(path, quality=92)
    print('tavola', path, flush=True)


def tavola_jumpscare(tile=(480, 270), exposure=0.0):
    """I fotogrammi finali del jumpscare in una tavola 4×2, come le altre di docs/concept/jumpscare: decodificati dalle
    immagini del gioco con la loro scala (overlays.json → jumpscares.foxy) e tonemappati come il motore.
    → docs/concept/jumpscare/js_foxy_finale_fotogrammi.jpg"""
    import json
    import post
    from common import OUT_IMG
    js = json.load(open(os.path.join(OUT_IMG, 'overlays.json')))['jumpscares']['foxy']
    W, H = tile
    gap = 8
    sheet = Image.new('RGB', (4 * W + 5 * gap, 2 * H + 3 * gap), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
    for i, fr in enumerate(js['frames']):
        lin, _ = post.decode_light_pass(os.path.join(OUT_IMG, fr['file']), fr['scale'])
        im = Image.fromarray((np.clip(post.tonemap(lin, exposure), 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').resize((W, H), Image.LANCZOS)
        x, y = gap + (i % 4) * (W + gap), gap + (i // 4) * (H + gap)
        sheet.paste(im, (x, y))
        d.text((x + 8, y + 6), str(i), fill=(220, 220, 220), font=font)
    dst = os.path.join(ROOT, 'docs', 'concept', 'jumpscare', 'js_foxy_finale_fotogrammi.jpg')
    sheet.save(dst, quality=92)
    print('tavola', dst, flush=True)


if __name__ == '__main__':
    if '--js-tavola' in sys.argv:
        tavola_jumpscare()
        sys.exit(0)
    if '--tavola' not in sys.argv:
        render_shots()
    tavola()
