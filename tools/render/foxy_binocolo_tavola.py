"""
L'ANIMATORE nel binocolo — la tavola dell'anteprima: per ogni luogo proposto i tre stadi (lontano, vicino, vuoto)
come si vedono nel gioco col binocolo alzato a zoom massimo (foto di foxy_binocolo_cattura.mjs).

Uso: tools/.venv/bin/python tools/render/foxy_binocolo_tavola.py [--def]
(--def: le viste definitive, col modello vero e l'atmosfera → docs/concept/animatore_binocolo.jpg)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from common import CACHE, ROOT  # noqa: E402

DIR = os.path.join(CACHE, 'foxy', 'bino')
DEF = '--def' in sys.argv
OUT = os.path.join(ROOT, 'docs', 'concept', 'animatore_binocolo.jpg' if DEF else 'foxy_binocolo.jpg')

LUOGHI = [
    ('scivoli', 'Torre degli scivoli (460 m)', 'in cima alla torre, sotto il tetto rosso',
     'sceso ai piedi della torre, davanti agli scivoli' if DEF else 'sceso sulla battigia, ai piedi degli scivoli'),
    ('relitto', 'Il relitto (170 m)', 'in piedi sulla tuga del peschereccio affondato', 'in acqua fino alla vita, davanti al relitto'),
]
STADI = [('lontano', '1 · lontano, fermo'), ('vicino', '2 · più vicino'), ('vuoto', '3 · il posto è vuoto')]


def main():
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf'
    tf = ImageFont.truetype(font.format('-Bold'), 30)
    hf = ImageFont.truetype(font.format('-Bold'), 24)
    lf = ImageFont.truetype(font.format('-Bold'), 20)
    sf = ImageFont.truetype(font.format(''), 18)
    W, H = 720, 556
    gap, head, row_head, foot = 16, 96, 44, 64
    sheet = Image.new('RGB', (W * 3 + gap * 4, head + len(LUOGHI) * (row_head + H + foot) + gap), (12, 14, 19))
    d = ImageDraw.Draw(sheet)
    if DEF:
        d.text((gap, 18), "L'ANIMATORE nel binocolo — viste definitive (modello B, atmosfera), tre stadi", fill=(235, 228, 210), font=tf)
        d.text((gap, 58), "foto del gioco vero (notte 2, binocolo alzato, zoom massimo, dondolio fermo); la nebbia del motore si somma ancora a quella resa",
               fill=(170, 166, 156), font=sf)
    else:
        d.text((gap, 18), "L'ANIMATORE nel binocolo — i posti proposti, tre stadi · da approvare", fill=(235, 228, 210), font=tf)
        d.text((gap, 58), "foto del gioco vero (notte 2, binocolo alzato, zoom massimo); il mostro è una sagoma provvisoria (la variante A in bozza)",
               fill=(170, 166, 156), font=sf)
    y = head
    for key, title, far, near in LUOGHI:
        d.text((gap, y + 8), title, fill=(255, 179, 92), font=hf)
        y += row_head
        for i, (st, label) in enumerate(STADI):
            x = gap + i * (W + gap)
            im = Image.open(os.path.join(DIR, f'gioco{"_def" if DEF else ""}_{key}_{st}.png')).convert('RGB')
            w0, h0 = im.size
            cw = int(h0 * 1.30)
            im = im.crop(((w0 - cw) // 2, 0, (w0 + cw) // 2, h0)).resize((W, H), Image.LANCZOS)
            sheet.paste(im, (x, y))
            d.text((x + 4, y + H + 8), label, fill=(235, 228, 210), font=lf)
            note = {'lontano': far, 'vicino': near, 'vuoto': 'subito dopo: salta sulla barca (jumpscare)'}[st]
            d.text((x + 4, y + H + 34), note, fill=(190, 186, 176), font=sf)
        y += H + foot
    sheet.save(OUT, quality=92)
    print(OUT)


def tavola_webp(src, serie='', out=None, scale=None):
    """Tavola di prova direttamente dalle immagini (senza il gioco): per luogo il vuoto, fermo e più vicino, decodificati
    con la scala e tonemappati come il motore, con un riquadro ingrandito attorno all'animatore."""
    import json
    import numpy as np
    import post
    entries = {e['key']: e for e in json.load(open(os.path.join(src, f'bino_foxy_entries{serie}.json')))}
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf'
    tf = ImageFont.truetype(font.format('-Bold'), 28)
    lf = ImageFont.truetype(font.format('-Bold'), 18)
    W, H = 720, 405
    gap, head = 14, 64
    rows = [k for k in ('scivoli', 'relitto') if k in entries]
    sheet = Image.new('RGB', (W * 3 + gap * 4, head + len(rows) * (H + 40)), (12, 14, 19))
    d = ImageDraw.Draw(sheet)
    d.text((gap, 16), "L'ANIMATORE nel binocolo, ingrandito — prova" + (' (senza nebbia)' if serie else ' (con la nebbia)'),
           fill=(235, 228, 210), font=tf)
    y = head
    for key in rows:
        sc = entries[key]['scale']
        ims = []
        for st in ('', '_foxy0', '_foxy1'):
            lin, _ = post.decode_light_pass(os.path.join(src, f'bino_{key}{st}{serie}.webp'), sc)
            ims.append(lin)
        diff = np.abs(ims[1] - ims[0]).sum(-1) + np.abs(ims[2] - ims[0]).sum(-1)
        for i, (lin, lab) in enumerate(zip(ims, ('vuoto', 'fermo', 'più vicino'))):
            im = Image.fromarray((np.clip(post.tonemap(lin, 1.0), 0, 1) * 255 + 0.5).astype(np.uint8))
            x = gap + i * (W + gap)
            sheet.paste(im.resize((W, H), Image.LANCZOS), (x, y))
            # riquadro ingrandito attorno a lui (dove l'immagine cambia)
            # (la compressione con perdita cambia un poco tutta l'immagine: conta solo dove cambia davvero)
            dd = np.abs(ims[i] - ims[0]).sum(-1) if i else diff
            m = dd > max(0.05, float(np.percentile(dd, 99.7)))
            ys, xs = np.nonzero(m)
            if len(xs):
                cx, cy = int(xs.mean()), int(ys.mean())
                r = 90
                crop = im.crop((cx - r, cy - r, cx + r, cy + r)).resize((200, 200), Image.LANCZOS)
                sheet.paste(crop, (x + W - 206, y + 6))
                d.rectangle((x + W - 207, y + 5, x + W - 5, y + 207), outline=(255, 179, 92))
            d.text((x + 4, y + H + 8), f'{key}: {lab}', fill=(235, 228, 210), font=lf)
        y += H + 40
    out = out or os.path.join(ROOT, 'docs', 'concept', f'animatore_binocolo_grande{serie}.jpg')
    sheet.save(out, quality=90)
    print(out)


if __name__ == '__main__':
    if '--webp' in sys.argv:
        a = sys.argv[sys.argv.index('--webp') + 1]
        tavola_webp(a, '_senza' if '--senza' in sys.argv else '')
        sys.exit(0)
    main()
