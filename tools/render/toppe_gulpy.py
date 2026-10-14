"""
Le toppe della mascella di Gulpy con la paperella (14 ottobre, trovato facendo il trailer). Le toppe
(gulpy_mascella_aperta e gulpy_mascella_chiusa, tools/render/pose_animate.py) sono renderizzate con la sola testa; il
loro riquadro però prende in alto anche un pezzo della paperella che Gulpy ha sul capo. Il motore, mentre la mascella
si muove, toglie la posa dove la toppa è vuota (shaders.ts, maskOf): dentro il riquadro la paperella spariva e restava
un rettangolo di buio sopra la testa, a ogni morso.

Qui, nella fascia in alto del riquadro (sopra la mascella, dove la toppa e la posa devono essere uguali), sotto la
toppa si mette la posa: passo per passo (ambiente, lampara, lanterna), in luce lineare, con l'alfa di ogni passo, per
le due serie (con la nebbia e senza). Sotto la fascia la toppa resta com'è. Se serve una scala più alta per i colori
nuovi, il manifest la segue. Rifarlo è innocuo: dove la paperella c'è già non cambia niente.

Uso: tools/.venv/bin/python tools/render/toppe_gulpy.py [--prova <foglio.jpg>]
"""
import json
import os
import sys

import numpy as np
from PIL import Image

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import post  # noqa: E402

IMG = os.path.join(os.path.dirname(os.path.dirname(QUI)), 'public', 'assets', 'img')
MANIFEST = os.path.join(IMG, 'manifest.json')
POSA = 'gulpy_pretende'
TOPPE = ['gulpy_mascella_aperta', 'gulpy_mascella_chiusa']
# la fascia (frazioni dell'altezza del riquadro della toppa): piena fino a FASCIA, poi sfuma in SFUMA. La mascella e gli
# occhi stanno sotto la metà
FASCIA, SFUMA = 0.24, 0.06


def passo(nome, info):
    """Un passo di uno strato: (lineare dritto, alfa)."""
    lin, a = post.decode_light_pass(os.path.join(IMG, info['file']), info['scale'])
    return lin, (a if a is not None else np.ones(lin.shape[:2], np.float32))


def nel_riquadro(x, r, q):
    """L'immagine x (riquadro r del panorama) vista nel riquadro q, vuota fuori."""
    h, w = q[3] - q[1], q[2] - q[0]
    out = np.zeros((h, w) + x.shape[2:], np.float32)
    x0, y0, x1, y1 = max(r[0], q[0]), max(r[1], q[1]), min(r[2], q[2]), min(r[3], q[3])
    if x1 > x0 and y1 > y0:
        out[y0 - q[1]:y1 - q[1], x0 - q[0]:x1 - q[0]] = x[y0 - r[1]:y1 - r[1], x0 - r[0]:x1 - r[0]]
    return out


def main():
    with open(MANIFEST, encoding='utf-8') as f:
        man = json.load(f)
    L = man['layers']
    prove = []
    for toppa in TOPPE:
        q = L[toppa]['rect']
        r = L[POSA]['rect']
        for serie in ('', 'senza'):
            pt = L[toppa]['senza']['passes'] if serie else L[toppa]['passes']
            pb = L[POSA]['senza']['passes'] if serie else L[POSA]['passes']
            for chi, info in pt.items():
                lp, ap = passo(toppa, info)
                lb, ab = passo(POSA, pb[chi])
                h, w = ap.shape
                lb = nel_riquadro(lb, r, q)[:h, :w]
                ab = nel_riquadro(ab, r, q)[:h, :w]
                y = (np.arange(h, dtype=np.float32) / h)[:, None]
                k = 1 - np.clip((y - FASCIA) / SFUMA, 0, 1)
                # la posa sotto la toppa (premoltiplicato), solo nella fascia
                pre = lp * ap[..., None] + k[..., None] * lb * (ab * (1 - ap))[..., None]
                alfa = ap + k * ab * (1 - ap)
                dritto = np.where(alfa[..., None] > 1e-4, pre / np.maximum(alfa, 1e-4)[..., None], 0)
                serve = float(np.percentile(dritto.max(axis=2)[alfa > 0.05], 99.9))
                scala = info['scale']
                if serve > scala * 1.001:
                    scala = round(serve, 4)
                    print(f'{toppa} {serie or "nebbia"} {chi}: scala {info["scale"]} → {scala}')
                    info['scale'] = scala
                post.save_webp(post.encode_light_pass(pre, scala, alpha=alfa), os.path.join(IMG, info['file']), quality=90)
                if chi == 'ambient':
                    prove.append((np.clip(lp * ap[..., None] * 4, 0, 1), np.clip(pre * 4, 0, 1)))
            print('toppa', toppa, serie or 'nebbia', flush=True)
    with open(MANIFEST + '.tmp', 'w') as f:
        json.dump(man, f, indent=1, sort_keys=True)
    os.replace(MANIFEST + '.tmp', MANIFEST)
    if '--prova' in sys.argv:
        # prima e dopo, il passo dell'ambiente di ogni toppa (schiarito)
        col = [np.concatenate([a, b], axis=1) for a, b in prove]
        hh = max(c.shape[0] for c in col)
        col = [np.pad(c, ((0, hh - c.shape[0]), (0, 8), (0, 0))) for c in col]
        im = np.concatenate(col, axis=1) ** (1 / 2.2)
        Image.fromarray((im * 255 + 0.5).astype(np.uint8)).save(sys.argv[sys.argv.index('--prova') + 1], quality=90)


if __name__ == '__main__':
    main()
