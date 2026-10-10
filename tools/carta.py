"""
Texture del libro del Catalogo (procedurali, ripetibili senza cuciture):
  public/assets/img/catalogo/carta.webp  carta vecchia color crema: fibre, macchie di umidità, puntini di ruggine
  public/assets/img/catalogo/cuoio.webp  cuoio scuro della copertina: grana a pallini, graffi, consumo

Uso: tools/.venv/bin/python tools/carta.py
"""
import os

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'public', 'assets', 'img', 'catalogo')
rng = np.random.default_rng(1997)


def periodic_noise(n, power, aniso=(1.0, 1.0)):
    """Rumore periodico 2D (si ripete senza cuciture) con spettro 1/f^power; aniso stira le frequenze."""
    fy = np.fft.fftfreq(n)[:, None] * aniso[1]
    fx = np.fft.fftfreq(n)[None, :] * aniso[0]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1.0
    spec = (rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))) / f ** power
    spec[0, 0] = 0
    x = np.real(np.fft.ifft2(spec))
    return (x - x.mean()) / (x.std() + 1e-9)


def blot(n, cx, cy, r, ring=False):
    """Macchia morbida (o alone ad anello) periodica."""
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    dx = np.minimum(np.abs(x - cx), n - np.abs(x - cx))
    dy = np.minimum(np.abs(y - cy), n - np.abs(y - cy))
    d = np.sqrt(dx ** 2 + dy ** 2) / r
    if ring:
        return np.exp(-((d - 1.0) / 0.08) ** 2) * 0.6 + np.exp(-(d / 0.95) ** 6) * 0.25
    return np.exp(-d ** 2)


def paper(n=1024):
    base = np.array([0.905, 0.855, 0.735])
    mott = periodic_noise(n, 1.6)                 # chiazze larghe
    fib = periodic_noise(n, 0.9, aniso=(1.0, 4.0))   # fibre corte orientate
    fine = periodic_noise(n, 0.3)
    v = 1.0 + 0.035 * mott + 0.018 * fib + 0.012 * fine
    img = base[None, None, :] * v[..., None]
    # alone d'umidità e puntini di ruggine (foxing)
    stain = np.zeros((n, n), np.float32)
    for _ in range(3):
        stain += blot(n, rng.uniform(0, n), rng.uniform(0, n), rng.uniform(90, 200), ring=True) * rng.uniform(0.5, 1.0)
    fox = np.zeros((n, n), np.float32)
    for _ in range(28):
        fox += blot(n, rng.uniform(0, n), rng.uniform(0, n), rng.uniform(1.5, 6.0)) * rng.uniform(0.3, 1.0)
    brown = np.array([0.62, 0.47, 0.28])
    img = img * (1 - 0.10 * stain[..., None]) + brown * 0.10 * stain[..., None]
    img = img * (1 - 0.35 * np.clip(fox, 0, 1)[..., None]) + np.array([0.55, 0.36, 0.18]) * 0.35 * np.clip(fox, 0, 1)[..., None]
    return np.clip(img, 0, 1)


def leather(n=512):
    base = np.array([0.20, 0.075, 0.05])
    # grana a pallini: rumore fine, soglia morbida, sfocato
    g = periodic_noise(n, 0.15)
    pebble = np.clip((g - 0.2) * 1.2, 0, 1)
    pebble = np.asarray(Image.fromarray((pebble * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
    wear = np.clip(periodic_noise(n, 1.8) * 0.5 + 0.3, 0, 1)
    v = 0.82 + 0.25 * pebble + 0.25 * wear
    img = base[None, None, :] * v[..., None]
    # graffi: righe chiare sottili
    yy, xx = np.mgrid[0:n, 0:n]
    for _ in range(40):
        x0, y0 = rng.uniform(0, n, 2)
        a = rng.uniform(0, np.pi)
        L = rng.uniform(10, 60)
        d = np.abs((xx - x0) * np.sin(a) - (yy - y0) * np.cos(a))
        t = (xx - x0) * np.cos(a) + (yy - y0) * np.sin(a)
        m = (d < 0.7) & (t > 0) & (t < L)
        img[m] = img[m] * 1.35 + 0.02
    return np.clip(img, 0, 1)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray((paper() * 255).astype(np.uint8)).save(os.path.join(OUT, 'carta.webp'), quality=86, method=6)
    Image.fromarray((leather() * 255).astype(np.uint8)).save(os.path.join(OUT, 'cuoio.webp'), quality=86, method=6)
    print('ok', os.listdir(OUT))
