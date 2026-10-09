"""
Icona PROVVISORIA (da approvare): la "S" al neon rosa dell'insegna di Splashland, mezza spenta, sul mare
di notte con il riflesso. Scrive build/icon.png (1024) per Electron e public/favicon.png (64) per il web.
Uso: tools/.venv/bin/python tools/icona.py
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, 'public', 'fonts', 'Limelight-Regular.ttf')
N = 1024


def icon():
    # fondo: notte, più chiaro verso l'orizzonte
    y = np.linspace(0, 1, N)[:, None]
    top, hor = np.array((5, 8, 16)), np.array((18, 30, 46))
    sky = top + (hor - top) * np.clip(y / 0.66, 0, 1) ** 2
    sea = np.array((4, 10, 16)) + np.zeros((N, 1, 3))
    img = np.where(y[..., None] < 0.66, sky[:, None, :] * np.ones((1, N, 1)), sea * np.ones((1, N, 1)))
    base = Image.fromarray(img.astype(np.uint8), 'RGB').convert('RGBA')
    # la S al neon: tubo bianco-rosa con l'alone
    f = ImageFont.truetype(FONT, 760)
    s = Image.new('L', (N, N), 0)
    d = ImageDraw.Draw(s)
    w = d.textlength('S', font=f)
    d.text(((N - w) / 2, -40), 'S', font=f, fill=255)
    # la metà bassa è fioca (come le lettere che muoiono nell'insegna)
    m = np.asarray(s).astype(np.float32) / 255.0
    yy = np.arange(N)[:, None] / N
    lit = np.where(yy < 0.47, 1.0, 0.5)
    pink = np.array((255, 60, 150), np.float32)
    glow = np.asarray(s.filter(ImageFilter.GaussianBlur(38))).astype(np.float32) / 255.0
    glow2 = np.asarray(s.filter(ImageFilter.GaussianBlur(12))).astype(np.float32) / 255.0
    out = np.asarray(base).astype(np.float32)
    out[..., :3] += (glow * 1.6 * lit)[..., None] * pink * 0.55
    out[..., :3] += (glow2 * lit)[..., None] * pink * 0.6
    core = (m * lit)[..., None]
    out[..., :3] = out[..., :3] * (1 - core) + core * np.array((255, 214, 236))
    dead = (m * (1 - lit) * 0.9)[..., None]
    out[..., :3] = out[..., :3] * (1 - dead) + dead * np.array((70, 22, 44))
    # riflesso nell'acqua, spezzato dalle onde
    refl = np.flipud(out[: int(N * 0.66)])[: N - int(N * 0.66)].copy()
    rows = np.arange(refl.shape[0])
    for r in rows:
        refl[r] = np.roll(refl[r], int(8 * np.sin(r * 0.21)), axis=0)
    k = (0.38 * (1 - rows / len(rows)))[:, None, None]
    out[int(N * 0.66):, :, :3] = out[int(N * 0.66):, :, :3] * (1 - k) + refl[..., :3] * k
    # bordi arrotondati
    mask = Image.new('L', (N, N), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, N - 1, N - 1), radius=180, fill=255)
    out[..., 3] = np.asarray(mask)
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')
    os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
    im.save(os.path.join(ROOT, 'build', 'icon.png'))
    im.resize((64, 64), Image.LANCZOS).save(os.path.join(ROOT, 'public', 'favicon.png'))
    print('build/icon.png, public/favicon.png')


if __name__ == '__main__':
    icon()
