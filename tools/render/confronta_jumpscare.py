"""Confronta i fotogrammi di un jumpscare resi con la nebbia (cartella dei render) con quelli del gioco (la serie senza
nebbia): una tavola con la serie senza in alto e quella con la nebbia sotto, col tono del motore, e la luce media di
ogni fotogramma.

Uso: tools/.venv/bin/python tools/render/confronta_jumpscare.py <cartella_render> <chi> <tavola.jpg>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import post  # noqa: E402
from confronta_serie import IMG, decode  # noqa: E402

src, chi, out = sys.argv[1:4]
e = json.load(open(os.path.join(IMG, 'overlays.json')))['jumpscares'][chi]
r = json.load(open(os.path.join(src, 'overlays.json')))['jumpscares'][chi]
vecchi = e['senza']['frames'] if 'senza' in e else e['frames']
cartella = IMG if 'senza' in e and e['frames'] == r['frames'] else src
righe = []
for frames, cart in ((vecchi, IMG), (r['frames'], cartella)):
    riga = []
    for f in frames:
        c, _ = decode(os.path.join(cart, f['file']), f['scale'])
        riga.append(c)
    righe.append(riga)
print(chi, 'luce nebbia/senza per fotogramma', [round(float(n.mean() / max(v.mean(), 1e-6)), 2) for v, n in zip(*righe)])
W, H = 480, 270
tav = Image.new('RGB', (W * len(righe[0]), H * 2))
for y, riga in enumerate(righe):
    for x, c in enumerate(riga):
        im = Image.fromarray(np.uint8(np.clip(post.tonemap(c, 0.5), 0, 1) * 255 + 0.5)).resize((W, H), Image.LANCZOS)
        tav.paste(im, (x * W, y * H))
tav.save(out, quality=88)
