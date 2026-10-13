"""
La nebbia dello sfondo di un jumpscare, ripulita dopo il render (13 ottobre, Madre con la nebbia: il mare vicino alla
barca usciva a chiazze arancio-grigie).

È lo stesso difetto di liscia_nebbia.py per il mondo: la luce della lanterna e della lampara diffusa nella nebbia,
trovata con 64 campioni, il denoiser la lascia maculata. Qui si lisciano solo i passi lamp e lantern dello sfondo
(<chi>_bg.exr), fuori dalla barca (la copertura di <chi>_bg_barca.exr): ogni pixel prende la media pesata del suo
intorno, e restano com'erano i punti molto più chiari del loro intorno, cioè i riflessi veri. Il passo ambient non si
tocca: ci sono i monti, il paese e le onde lontane, che con la media diventerebbero macchie.

La prima volta l'originale si tiene come <chi>_bg_originale.exr e si liscia sempre quello. Poi si ricompongono i
fotogrammi con JS_RIPRENDI=1, che riusa sfondo e fotogrammi in cache.

Uso: tools/.venv/bin/python tools/render/liscia_sfondo_jumpscare.py madre [--sigma 12] [--cache tools/render/cache/final/jumpscare]
"""
import argparse
import os
import shutil
import sys

import numpy as np
import OpenEXR
from scipy.ndimage import gaussian_filter, median_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post  # noqa: E402

PASSI = ('lamp', 'lantern')


def media(img: np.ndarray, sigma: float, w: np.ndarray) -> np.ndarray:
    """Media gaussiana pesata (convoluzione normalizzata)."""
    den = gaussian_filter(w, sigma, mode='nearest')
    num = np.stack([gaussian_filter(img[..., c] * w, sigma, mode='nearest') for c in range(3)], axis=-1)
    return num / np.maximum(den, 1e-6)[..., None]


def liscia(lin: np.ndarray, w: np.ndarray, sigma: float) -> np.ndarray:
    base = media(lin, sigma, w + 1e-4)
    # i riflessi veri: molto più chiari della loro media e più grandi di un pixel (come in liscia_nebbia.py)
    r = median_filter(lin.mean(axis=2) / np.maximum(base.mean(axis=2), 1e-7), size=3, mode='nearest')
    tieni = np.clip((r - 1.8) / 1.0, 0.0, 1.0)
    tieni = (tieni * tieni * (3 - 2 * tieni))[..., None]
    out = base * (1 - tieni) + lin * tieni
    return out * w[..., None] + lin * (1 - w[..., None])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('chi')
    ap.add_argument('--sigma', type=float, default=12.0)
    ap.add_argument('--cache', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'final', 'jumpscare'))
    a = ap.parse_args()
    bg = os.path.join(a.cache, f'{a.chi}_bg.exr')
    orig = os.path.join(a.cache, f'{a.chi}_bg_originale.exr')
    if not os.path.exists(orig):
        shutil.copy2(bg, orig)
    barca = np.clip(post.read_exr(os.path.join(a.cache, f'{a.chi}_bg_barca.exr'))['alpha'], 0.0, 1.0)
    # fuori dalla barca, col bordo un po' allargato: la barca non sporca il mare
    w = np.clip(1 - gaussian_filter(barca, 1.5) * 2, 0, 1).astype(np.float32)
    parts = []
    with OpenEXR.File(orig) as f:
        for p in f.parts:
            ch = {}
            for k, v in p.channels.items():
                px = np.array(v.pixels)
                if p.name() in PASSI:
                    px[..., :3] = liscia(px[..., :3].astype(np.float32), w, a.sigma).astype(px.dtype)
                ch[k] = px
            parts.append(OpenEXR.Part(dict(p.header), ch, name=p.name()))
    OpenEXR.File(parts).write(bg)
    o, n = post.read_exr(orig), post.read_exr(bg)
    for g in PASSI:
        print(g, 'luce nuova/originale', round(float(n[g][..., :3].mean() / o[g][..., :3].mean()), 4))
    print('->', bg)


if __name__ == '__main__':
    main()
