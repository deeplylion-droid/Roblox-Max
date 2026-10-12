"""
L'ANIMATORE nel binocolo — la tavola dell'anteprima: per ogni luogo proposto i tre stadi (lontano, vicino, vuoto)
come si vedono nel gioco col binocolo alzato a zoom massimo (foto di foxy_binocolo_cattura.mjs).

Uso: tools/.venv/bin/python tools/render/foxy_binocolo_tavola.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from common import CACHE, ROOT  # noqa: E402

DIR = os.path.join(CACHE, 'foxy', 'bino')
OUT = os.path.join(ROOT, 'docs', 'concept', 'foxy_binocolo.jpg')

LUOGHI = [
    ('scivoli', 'Torre degli scivoli (460 m)', 'in cima alla torre, sotto il tetto rosso', 'sceso sulla battigia, ai piedi degli scivoli'),
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
    d.text((gap, 18), "L'ANIMATORE nel binocolo — i posti proposti, tre stadi · da approvare", fill=(235, 228, 210), font=tf)
    d.text((gap, 58), "foto del gioco vero (notte 2, binocolo alzato, zoom massimo); il mostro è una sagoma provvisoria (la variante A in bozza)",
           fill=(170, 166, 156), font=sf)
    y = head
    for key, title, far, near in LUOGHI:
        d.text((gap, y + 8), title, fill=(255, 179, 92), font=hf)
        y += row_head
        for i, (st, label) in enumerate(STADI):
            x = gap + i * (W + gap)
            im = Image.open(os.path.join(DIR, f'gioco_{key}_{st}.png')).convert('RGB')
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


if __name__ == '__main__':
    main()
