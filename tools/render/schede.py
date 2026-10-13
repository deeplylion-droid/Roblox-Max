"""
Le foto delle schede della notte extra (13 ottobre, fra le rifiniture scelte dall'utente; da approvare): sopra il nome
di ognuno dei nove, la sua faccia, come nella Custom Night di FNAF. Niente render nuovi: i sette mostri vengono dai
ritratti del menu (public/assets/img/ritratti, tools/render/ritratti.py), la Madre dal suo strato della notte 6 (la
testa che sale accanto alla barca, con l'occhio: i passi di luce del gioco ricomposti), Soggy da un fotogramma del suo
jumpscare (la faccia dentro il costume di Mama Marina), scurito come i ritratti. Tutte con lo stesso buio ai bordi,
per stare insieme.

Uso: tools/.venv/bin/python tools/render/schede.py [--prova <foglio.jpg>]
"""
import json
import os
import sys

import numpy as np
from PIL import Image

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))
IMG = os.path.join(RADICE, 'public', 'assets', 'img')
USCITA = os.path.join(IMG, 'schede')
LATO = 224  # in gioco la foto è larga 112 px: il doppio, per gli schermi fitti

# chi: (immagine, centro del ritaglio in frazioni dell'immagine, lato del ritaglio in frazioni dell'altezza, luce,
# nebbia). «strato:<nome>» è uno strato del gioco (manifest.json), coi suoi passi di luce sommati. La luce schiarisce i
# ritratti più bui (la foto in gioco è piccola); i fotogrammi dei jumpscare hanno la nebbia chiara davanti: si toglie
# il grigio di fondo e si scuriscono come i ritratti.
SCHEDE = {
    'gulpy': ('ritratti/gulpy.webp', 0.655, 0.54, 0.82, 1.5, False),
    'molly': ('ritratti/molly.webp', 0.67, 0.50, 0.75, 1.15, False),
    'hatch': ('ritratti/hatch.webp', 0.67, 0.50, 0.85, 1.1, False),
    'robin': ('ritratti/robin.webp', 0.66, 0.52, 0.85, 1.0, False),
    'archie': ('ritratti/archie.webp', 0.62, 0.55, 0.85, 1.2, False),
    'lampy': ('ritratti/lampy.webp', 0.64, 0.58, 0.80, 1.15, False),
    'fangy': ('ritratti/fangy.webp', 0.68, 0.62, 0.75, 1.3, False),
    'mother': ('strato:madre_sale', 0.606, 0.345, 0.61, 0.85, False),
    'foxy': ('js_foxy_05.webp', 0.55, 0.47, 0.80, 0.85, True),
}


def strato(nome, esposizione=4.0):
    """Uno strato del gioco come lo vedi: i passi (ambiente, lampara, lanterna) decodificati (tex^4 · scala, come il
    motore) e sommati, una curva morbida per le luci, sul buio della baia dove lo strato è trasparente."""
    with open(os.path.join(IMG, 'manifest.json'), encoding='utf-8') as f:
        passi = json.load(f)['layers'][nome]['passes']
    luce, alfa = 0, 0
    for p in passi.values():
        t = np.asarray(Image.open(os.path.join(IMG, p['file'])).convert('RGBA')).astype(np.float32) / 255
        luce = luce + t[..., :3] ** 4 * p['scale']
        alfa = np.maximum(alfa, t[..., 3:])
    x = luce * esposizione
    c = (x / (1 + x)) ** (1 / 2.2)
    fondo = np.array([5, 8, 13], np.float32) / 255
    return Image.fromarray((np.clip(c * alfa + fondo * (1 - alfa), 0, 1) * 255 + 0.5).astype(np.uint8))


def scheda(src, cx, cy, lato, luce, nebbia):
    im = strato(src[7:]) if src.startswith('strato:') else Image.open(os.path.join(IMG, src)).convert('RGB')
    W, H = im.size
    s = round(H * lato)
    x0 = min(max(0, round(W * cx - s / 2)), W - s)
    y0 = min(max(0, round(H * cy - s / 2)), H - s)
    a = np.asarray(im.crop((x0, y0, x0 + s, y0 + s)).resize((LATO, LATO), Image.LANCZOS)).astype(np.float32) / 255
    if nebbia:
        # il grigio della nebbia sotto i neri: via; poi più contrasto (le ombre scendono più delle luci), meno colore
        nero = np.percentile(a.mean(axis=2), 2)
        a = np.clip((a - nero) / (1 - nero), 0, 1) ** 1.35
        g = a.mean(axis=2, keepdims=True)
        a = g + (a - g) * 0.85
    a = a * luce
    # il buio ai bordi, uguale per tutte
    y, x = np.mgrid[0:LATO, 0:LATO] / (LATO - 1) * 2 - 1
    r = np.sqrt(x * x + y * y)
    a = a * np.clip(1.25 - 0.55 * r ** 2, 0, 1)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def main():
    os.makedirs(USCITA, exist_ok=True)
    fatte = []
    for chi, (src, cx, cy, lato, luce, nebbia) in SCHEDE.items():
        im = scheda(src, cx, cy, lato, luce, nebbia)
        im.save(os.path.join(USCITA, f'{chi}.webp'), quality=86, method=6)
        fatte.append(im)
        print('scheda', chi, flush=True)
    if '--prova' in sys.argv:
        foglio = Image.new('RGB', (LATO * len(fatte) + 8 * (len(fatte) - 1), LATO), (20, 20, 24))
        for i, im in enumerate(fatte):
            foglio.paste(im, (i * (LATO + 8), 0))
        foglio.save(sys.argv[sys.argv.index('--prova') + 1], quality=90)


if __name__ == '__main__':
    main()
