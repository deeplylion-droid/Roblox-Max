"""La cima della sagoma di una creatura nel mondo, per il gioco: per n colonne equidistanti sul riquadro dello strato
(la prima sul bordo sinistro, l'ultima sul destro, come il pelo dell'acqua) la riga del panorama del primo pixel pieno
dall'alto, dall'alfa del passo ambient. Il motore la usa per non far vedere le luci lontane del paesaggio attraverso una
creatura grande (la Madre accanto alla barca ha dietro la candela dell'edicola). None dove la colonna è vuota.

Uso: python3 tools/render/cima.py madre_sale [altre chiavi...]  (scrive layers.<chiave>.cima nel manifest)
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post  # noqa: E402

IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'public', 'assets', 'img')
MANIFEST = os.path.join(IMG, 'manifest.json')


def cima(alpha: np.ndarray, rect, n: int = 32, soglia: int = 128):
    x0, y0, x1, y1 = rect
    h, w = alpha.shape
    out = []
    for i in range(n):
        x = round(i * (w - 1) / (n - 1))
        # qualche colonna attorno, per non farsi ingannare da un pixel isolato (una goccia, un filo d'alga)
        col = alpha[:, max(0, x - 2):x + 3].max(axis=1)
        rows = np.nonzero(col >= soglia)[0]
        out.append(round(float(y0 + rows[0] * (y1 - y0) / h), 1) if len(rows) else None)
    return out


def main(keys):
    with open(MANIFEST) as f:
        man = json.load(f)
    for key in keys:
        e = man['layers'].get(key)
        if not e:
            print(f'{key}: non è nel manifest')
            continue
        im = Image.open(os.path.join(IMG, e['passes']['ambient']['file']))
        if im.mode != 'RGBA':
            print(f'{key}: il passo ambient non ha l\'alfa')
            continue
        c = cima(np.asarray(im)[:, :, 3], e['rect'])
        post.update_manifest(MANIFEST, f'layers.{key}.cima', c)
        piene = [r for r in c if r is not None]
        print(f'{key}: cima dalla riga {min(piene)} alla {max(piene)} ({len(piene)} colonne su {len(c)})')


if __name__ == '__main__':
    main(sys.argv[1:])
