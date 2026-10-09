"""
Post-produzione dei render: lettura EXR multilayer, anteprime con lo stesso tone mapping
del gioco (AgX approssimato + look notturno), codifica dei passi in WebP/PNG per il motore.

Codifica dei passi di luce (lineari, HDR): si salva  clamp(x / scale)^(1/4)  in 8 bit e lo
shader ricostruisce  x = tex^4 * scale. La gamma 4 dà molta precisione nei neri della notte
(0,001 → livello ~45) e lo 'scale' (nel manifest) fissa il bianco; ciò che lo supera (luna,
reticella della lampara) si satura e viene ripreso dal bloom nel motore.
"""
from __future__ import annotations

import io
import json
import os

import numpy as np
import OpenEXR
from PIL import Image

AGX = np.array([[0.842479062253094, 0.0423282422610123, 0.0423756549057051],
                [0.0784335999999992, 0.878468636469772, 0.0784336],
                [0.0792237451477643, 0.0791661274605434, 0.879142973793104]])
AGX_INV = np.array([[1.19687900512017, -0.0528968517574562, -0.0529716355144438],
                    [-0.0980208811401368, 1.15190312990417, -0.0980434501171241],
                    [-0.0990297440797205, -0.0989611768448433, 1.15107367264116]])
MIN_EV, MAX_EV = -12.47393, 4.026069


def read_exr(path: str) -> dict[str, np.ndarray]:
    out = {}
    with OpenEXR.File(path) as f:
        for part in f.parts:
            for k, v in part.channels.items():
                a = np.asarray(v.pixels, dtype=np.float32)
                name = k.split('.')[0] if k.endswith('.V') else k
                out[name] = a
    return out


def rgb(a: np.ndarray) -> np.ndarray:
    return a[..., :3] if a.ndim == 3 else np.repeat(a[..., None], 3, axis=2)


def tonemap(lin: np.ndarray, exposure_ev: float = 0.0, contrast: float = 1.12, saturation: float = 1.08) -> np.ndarray:
    """Lineare (Rec.709) → sRGB 0..1. Identico a src/engine/shaders (tonemap)."""
    x = np.maximum(lin * (2.0 ** exposure_ev), 1e-10)
    x = x @ AGX  # AGX è scritta per riga: v' = v · M (equivale a mat3 GLSL colonna)
    x = np.clip(np.log2(x), MIN_EV, MAX_EV)
    x = (x - MIN_EV) / (MAX_EV - MIN_EV)
    x2 = x * x
    x4 = x2 * x2
    x = 15.5 * x4 * x2 - 40.14 * x4 * x + 31.96 * x4 - 6.868 * x2 * x + 0.4298 * x2 + 0.1191 * x - 0.00232
    # look: contrasto attorno al grigio medio e saturazione
    luma = (x * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
    x = luma + (x - luma) * saturation
    x = 0.5 + (x - 0.5) * contrast
    x = x @ AGX_INV
    x = np.clip(x, 0.0, 1.0)
    return x


def srgb_encode(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def srgb_decode(x):
    return np.where(x <= 0.04045, x / 12.92, np.power((x + 0.055) / 1.055, 2.4))


def save_png(arr01: np.ndarray, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray((np.clip(arr01, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


def compose(passes: dict, weights: dict) -> np.ndarray:
    acc = None
    for k, w in weights.items():
        if k in passes:
            c = rgb(passes[k]).astype(np.float32) * w
            acc = c if acc is None else acc + c
    return acc


def preview(exr: str, out_png: str, weights=None, exposure=0.0, background=None, max_width=None):
    p = read_exr(exr)
    weights = weights or {'ambient': 1.0, 'lamp': 1.0}
    lin = compose(p, weights)
    if background is not None and 'alpha' in p:
        a = p['alpha'][..., None]
        lin = lin + np.array(background) * (1 - a)
    img = tonemap(lin, exposure)
    if max_width and img.shape[1] > max_width:
        im = Image.fromarray((img * 255).astype(np.uint8))
        im = im.resize((max_width, round(img.shape[0] * max_width / img.shape[1])), Image.LANCZOS)
        os.makedirs(os.path.dirname(out_png), exist_ok=True)
        im.save(out_png)
    else:
        save_png(img, out_png)
    return out_png


# ───────────────────────── codifica per il gioco ─────────────────────────

ENC_GAMMA = 4.0


def pick_scale(lin: np.ndarray, alpha=None, pct=99.7, floor=0.25, ceil=6.0) -> float:
    m = lin.max(axis=-1)
    if alpha is not None:
        m = m[alpha > 0.5]
    if m.size == 0:
        return 1.0
    s = float(np.percentile(m, pct))
    s = min(max(s, floor), ceil)
    # arrotonda a 2 cifre significative
    e = np.floor(np.log10(s))
    return float(np.ceil(s / 10 ** (e - 1)) * 10 ** (e - 1))


def encode_light_pass(lin: np.ndarray, scale: float, alpha=None) -> Image.Image:
    """Lineare premoltiplicato → 8 bit con gamma 4 (colore dritto se c'è alpha)."""
    c = lin[..., :3].astype(np.float32)
    if alpha is not None:
        a = alpha[..., None]
        c = np.where(a > 1e-4, c / np.maximum(a, 1e-4), 0.0)
    enc = np.power(np.clip(c / scale, 0.0, 1.0), 1.0 / ENC_GAMMA)
    # dithering triangolare: evita il banding nelle sfumature scure della notte
    rng = np.random.default_rng(1)
    d = (rng.random(enc.shape) - rng.random(enc.shape)) / 255.0
    u8 = np.clip((enc + d) * 255 + 0.5, 0, 255).astype(np.uint8)
    if alpha is not None:
        a8 = np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8)
        return Image.fromarray(np.dstack([u8, a8]), 'RGBA')
    return Image.fromarray(u8, 'RGB')


def decode_light_pass(path: str, scale: float):
    """Inverso di encode_light_pass (per le anteprime): restituisce (lineare dritto, alpha|None)."""
    a = np.asarray(Image.open(path)).astype(np.float32) / 255.0
    rgb_ = np.power(a[..., :3], ENC_GAMMA) * scale
    alpha = a[..., 3] if a.shape[-1] == 4 else None
    return rgb_, alpha


def save_webp(img: Image.Image, path: str, quality=90, lossless=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, 'WEBP', quality=quality, method=6, lossless=lossless, exact=True)
    return os.path.getsize(path)


def update_manifest(path: str, key: str, entry):
    """Aggiorna una voce del manifest; 'a.b' scrive data['a']['b']."""
    data = {}
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    node = data
    parts = key.split('.')
    for k in parts[:-1]:
        node = node.setdefault(k, {})
    node[parts[-1]] = entry
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=1, sort_keys=True)


# ───────────────────────── vista prospettica dal panorama (come nel gioco) ─────────────────────────

def pano_to_view(pano: np.ndarray, yaw_deg: float, pitch_deg: float = -12.0, hfov_deg: float = 90.0,
                 size=(960, 540), lat_min=-58.0, lat_max=36.0, roll_deg: float = 0.0) -> np.ndarray:
    """Riproietta un panorama equirettangolare (H×W×C) in una vista prospettica."""
    W, H = size
    ph, pw = pano.shape[:2]
    tx = np.tan(np.radians(hfov_deg) / 2)
    ty = tx * H / W
    xs = (np.arange(W) + 0.5) / W * 2 - 1
    ys = 1 - (np.arange(H) + 0.5) / H * 2
    X, Y = np.meshgrid(xs * tx, ys * ty)
    # direzione in spazio camera: x destra, y alto, z avanti
    d = np.stack([X, Y, np.ones_like(X)], -1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    r = np.radians(roll_deg)
    cr, sr = np.cos(r), np.sin(r)
    dx = d[..., 0] * cr - d[..., 1] * sr
    dy = d[..., 0] * sr + d[..., 1] * cr
    dz = d[..., 2]
    p = np.radians(pitch_deg)
    cp, sp = np.cos(p), np.sin(p)
    dy2 = dy * cp + dz * sp
    dz2 = -dy * sp + dz * cp
    yw = np.radians(yaw_deg)
    cy, sy = np.cos(yw), np.sin(yw)
    wx = dx * cy + dz2 * sy        # mondo: x destra
    wy = -dx * sy + dz2 * cy       # mondo: y avanti
    wz = dy2
    lon = np.arctan2(wx, wy)
    lat = np.arctan2(wz, np.hypot(wx, wy))
    u = (0.5 + lon / (2 * np.pi)) * pw
    v = (np.radians(lat_max) - lat) / np.radians(lat_max - lat_min) * ph
    ui = np.clip(u.astype(int) % pw, 0, pw - 1)
    vi = np.clip(v.astype(int), 0, ph - 1)
    return pano[vi, ui]
