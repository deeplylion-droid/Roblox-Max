"""Confronta gli strati resi con la nebbia (cartella dei render) con quelli del gioco (la serie senza nebbia): stessa
inquadratura (riquadro e yaw), sagoma allineata al pixel (l'alfa), e quanto cambia la luce. Scrive una tavola per
strato: in alto la serie senza nebbia, sotto quella nuova; da sinistra la lampara spenta, bassa e alta (pesi 0, 1, 1,7
come il motore), sul fondo del mondo di ciascuna serie dietro lo strato.

Uso: tools/.venv/bin/python tools/render/confronta_serie.py <cartella_render> <chiave> [<chiave> ...] [--tavole <cartella>]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IMG = os.path.join(ROOT, 'public', 'assets', 'img')
ENC_GAMMA = 4.0
PESI = (0.0, 1.0, 1.7)


def decode(path, scale):
    im = np.asarray(Image.open(path)).astype(np.float32) / 255.0
    c = np.power(im[..., :3], ENC_GAMMA) * scale
    a = im[..., 3] if im.shape[-1] == 4 else np.ones(im.shape[:2], np.float32)
    return c, a


def passi(cartella, passes, rect=None, res_full=True):
    out = {}
    a = None
    for g, p in passes.items():
        c, al = decode(os.path.join(cartella, p['file']), p['scale'])
        if p.get('res', 1.0) != 1.0:
            # mezza risoluzione: si riporta alle misure dello strato
            h, w = (rect[3] - rect[1], rect[2] - rect[0]) if rect else (c.shape[0] * 2, c.shape[1] * 2)
            c = np.asarray(Image.fromarray(np.uint8(np.clip(c / p['scale'], 0, 1) ** (1 / ENC_GAMMA) * 255)).resize((w, h)),
                           np.float32) / 255.0
            c = c ** ENC_GAMMA * p['scale']
        out[g] = c
        if g == 'ambient' or a is None:
            a = al
    return out, a


def tono(lin, ev=0.5):
    import post
    return post.tonemap(lin, ev)


def fondo(man_e, rect, senza):
    """Il mondo (della serie) dietro lo strato, ritagliato sul riquadro (solo strati nel riquadro del panorama)."""
    w = man_e['senza']['passes'] if senza and 'senza' in man_e else man_e['passes']
    x0, y0, x1, y1 = rect
    tot = 0
    for g, p in w.items():
        c, _ = decode(os.path.join(IMG, p['file']), p['scale'])
        if p.get('res', 1.0) != 1.0:
            c = np.repeat(np.repeat(c, 2, 0), 2, 1)
        tot = tot + c[y0:y1, x0:x1] * (1.0 if g != 'lamp' else 0.0)
    lamp = None
    if 'lamp' in w:
        c, _ = decode(os.path.join(IMG, w['lamp']['file']), w['lamp']['scale'])
        lamp = c[y0:y1, x0:x1]
    return tot, lamp


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    tav = sys.argv[sys.argv.index('--tavole') + 1] if '--tavole' in sys.argv else None
    if tav:
        args = [a for a in args if a != tav]
    src, keys = args[0], args[1:]
    rman = json.load(open(os.path.join(src, 'manifest.json')))
    man = json.load(open(os.path.join(IMG, 'manifest.json')))
    ok = True
    for k in keys:
        e, r = man['layers'][k], rman['layers'][k]
        vecchi = e['senza']['passes'] if 'senza' in e else e['passes']
        cartella_nuovi = IMG if 'senza' in e and e['passes'] == r['passes'] else src
        stessi = list(e['rect']) == list(r['rect']) and abs(e['yaw'] - r['yaw']) < 1e-3
        pv, av = passi(IMG, vecchi, e['rect'])
        pn, an = passi(cartella_nuovi, r['passes'], r['rect'])
        if av.shape != an.shape:
            print(f'{k}: MISURE DIVERSE {av.shape} {an.shape}')
            ok = False
            continue
        d = np.abs(av - an)
        iou = float(np.minimum(av, an).sum() / max(np.maximum(av, an).sum(), 1e-6))
        # la sagoma: i pixel coperti a metà o più in una serie e non nell'altra
        bordo = int(((av > 0.5) != (an > 0.5)).sum())
        m = av > 0.5

        def lum(p, g):
            return float(p[g][m].mean()) if g in p and m.any() else 0.0
        rap = {g: round(lum(pn, g) / max(lum(pv, g), 1e-6), 2) for g in ('ambient', 'lamp', 'lantern')}
        print(f'{k}: inquadratura {"uguale" if stessi else "DIVERSA"} · alfa IoU {iou:.4f}, diff max {d.max():.3f}, '
              f'pixel di sagoma diversi {bordo} · luce nuova/vecchia {rap}')
        ok = ok and stessi and bordo < max(20, 0.002 * m.sum())
        if tav:
            os.makedirs(tav, exist_ok=True)
            righe = []
            for p, a, senza in ((pv, av, True), (pn, an, False)):
                bg, bgl = fondo(man['layers']['world'], e['rect'], senza)
                riga = []
                for w in PESI:
                    lin = p.get('ambient', 0) * 1.0 + p.get('lamp', 0) * w + p.get('lantern', 0)
                    back = bg + (bgl * w if bgl is not None else 0)
                    comp = lin * a[..., None] + back * (1 - a[..., None])
                    riga.append(np.asarray(tono(comp), np.float32))
                righe.append(np.concatenate(riga, 1))
            im = np.concatenate(righe, 0)
            Image.fromarray(np.uint8(np.clip(im, 0, 1) * 255 + 0.5)).save(os.path.join(tav, f'{k}.jpg'), quality=88)
    print('tutto allineato' if ok else 'ATTENZIONE: qualcosa non combacia')


if __name__ == '__main__':
    main()
