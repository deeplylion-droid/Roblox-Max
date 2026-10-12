"""
La luce delle lampade nella nebbia del mondo, ripulita dopo il render (12 ottobre, segnalazione dell'utente: «sul lato
sinistro della barca la nebbia sembra pixellare la luce»).

Il passo della lanterna, e in parte quello della lampara, esce da Cycles a chiazze. È la diffusione nella nebbia di una
luce piccola, trovata con pochi campioni: il denoiser la lascia maculata (atmosfera.liscia_lontano lo sistemava solo
per la lampara e solo lontano). Sull'acqua scura, nel gioco, si vedeva come una luce «pixellata» dal lato della
lanterna. Qui ogni pixel prende la media del suo intorno, mezzo grado vicino alla barca e un grado oltre i 15-60 m.
Restano com'erano i punti molto più chiari del loro intorno, cioè i riflessi veri sull'acqua: il motore li fa ancora
tremolare.

Uso: python3 tools/render/liscia_nebbia.py <cartella delle immagini> [--passi lamp,lantern] [--prova cartella]
Con --prova scrive lì le immagini invece di sostituirle.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, median_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post  # noqa: E402


def decode(path: str, scale: float) -> np.ndarray:
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float32) / 255.0
    return a ** post.ENC_GAMMA * scale


def media(img: np.ndarray, sigma: float, w: np.ndarray) -> np.ndarray:
    """Media gaussiana pesata (convoluzione normalizzata); il panorama gira in orizzontale."""
    mode = ('nearest', 'wrap')
    den = gaussian_filter(w, sigma, mode=mode)
    num = np.stack([gaussian_filter(img[..., c] * w, sigma, mode=mode) for c in range(img.shape[2])], axis=-1)
    return num / np.maximum(den, 1e-6)[..., None]


def liscia(lin: np.ndarray, dist: np.ndarray, ppd: float) -> np.ndarray:
    ones = np.ones(lin.shape[:2], np.float32)
    vicino = media(lin, 0.5 * ppd, ones)
    lontano = media(lin, 1.0 * ppd, ones)
    wf = np.clip((dist - 15.0) / 45.0, 0.0, 1.0)
    wf = (wf * wf * (3 - 2 * wf))[..., None]
    base = vicino * (1 - wf) + lontano * wf
    # i riflessi veri: molto più chiari della loro media (le chiazze arrivano a una volta e mezza) e più grandi di un
    # pixel (i puntini isolati sono lucciole del render, la mediana 3×3 li toglie)
    r = median_filter(lin.mean(axis=2) / np.maximum(base.mean(axis=2), 1e-7), size=3, mode='nearest')
    tieni = np.clip((r - 1.8) / 1.0, 0.0, 1.0)
    tieni = (tieni * tieni * (3 - 2 * tieni))[..., None]
    return base * (1 - tieni) + lin * tieni


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('img')
    ap.add_argument('--passi', default='lamp,lantern')
    ap.add_argument('--prova', default='')
    a = ap.parse_args()
    man = json.load(open(os.path.join(a.img, 'manifest.json')))
    world = man['layers']['world']
    data = np.asarray(Image.open(os.path.join(a.img, world['data'])).convert('RGB')).astype(np.float32) / 255.0
    mist = data[..., 0]
    for g in a.passi.split(','):
        p = world['passes'][g]
        path = os.path.join(a.img, p['file'])
        lin = decode(path, p['scale'])
        H, W = lin.shape[:2]
        m = mist
        if m.shape != (H, W):
            m = np.asarray(Image.fromarray((mist * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255.0
        dist = m * m * 2500.0
        out = liscia(lin, dist, W / 360.0)
        dest = os.path.join(a.prova, p['file']) if a.prova else path
        size = post.save_webp(post.encode_light_pass(out, p['scale']), dest)
        print(g, f'{W}x{H}', 'scala', p['scale'], '->', dest, size // 1024, 'KB')


if __name__ == '__main__':
    main()
