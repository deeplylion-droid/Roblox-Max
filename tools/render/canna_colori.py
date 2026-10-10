"""
I colori del fusto della canna per il motore (src/app/rod_colori.ts), presi dal render della canna intera a riposo
(lo strato rod0, i suoi tre passi di luce): così il fusto che il gioco piega in continuo ha la stessa luce del
render, punto per punto e lato per lato (il riflesso della lampara compreso), e si accende e si spegne con la
lampara come gli strati. Dice anche da dove il fusto esce dal portacanna, visto dall'occhio (u0): fin lì lo copre
lo strato del manico (rod_base), da lì in poi lo disegna il motore.

Uso: tools/.venv/bin/python tools/render/canna_colori.py
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IMG = os.path.join(ROOT, 'public', 'assets', 'img')
OUT = os.path.join(ROOT, 'src', 'app', 'rod_colori.ts')
PASSES = (('ambient', 'amb'), ('lamp', 'lamp'), ('lantern', 'lant'))

# come boat.py (ROD_GUNWALE, ROD_TIP, build_rod_holder) e common.EYE, dall'occhio
EYE = np.array((0.0, -0.55, 1.25))
GUN = np.array((0.97, 0.55, 0.74)) - EYE
TIP = np.array((2.02, 2.95, 1.86)) - EYE
D = TIP - GUN
HOLDER = (GUN + np.array((-0.015, -0.03, -0.12)), GUN + np.array((0.01, 0.06, 0.06)), 0.025)
LAMP_AT = np.array((0.0, 4.17, 0.55))          # come night.ts
N = 24                                         # punti del fusto (rod.ts)
BANDS = (-0.9, -0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.7, 0.9)   # dal lato verso la lampara all'altro (in mezze larghezze)
RINGS = (0.25, 0.45, 0.62, 0.78, 0.9)          # gli anelli di build_rod


def rest(u):
    """Il fusto a riposo (build_rod con bend 0): il peso della cima."""
    return GUN + D * u - np.array((0.0, 0.0, 0.06 * u * u))


def radius(u):
    """Il raggio del tubo di build_rod (rastremazione per indice di punto, butt compreso: 26 punti)."""
    return 0.011 * (1.0 - 0.75 * (1 + 24 * u) / 25)


def occluded_by_holder(p, r):
    """Il raggio dall'occhio a p passa dentro il portacanna (un tubo di raggio HOLDER[2] tra i due capi)?"""
    a, b, R = HOLDER
    # punto più vicino tra il segmento occhio→p e il segmento a→b
    d1, d2 = p, b - a
    r0 = -a
    A, E, F = d1 @ d1, d2 @ d2, d2 @ r0
    c, bb = d1 @ r0, d1 @ d2
    den = A * E - bb * bb
    s = np.clip((bb * F - c * E) / den, 0, 1) if den > 1e-12 else 0.0
    t = np.clip((bb * s + F) / E, 0, 1)
    s = np.clip((bb * t - c) / A, 0, 1)
    dist = np.linalg.norm(d1 * s - (a + d2 * t))
    # il fusto si vede se almeno il suo bordo esce dal profilo del portacanna (e il portacanna sta davanti)
    return dist < R + r * 0.2 and s < 0.999


def pano_xy(p, man, e):
    W, H = man['pano']['width'], man['pano']['height']
    lat0, lat1 = man['pano']['latMin'], man['pano']['latMax']
    yaw = math.degrees(math.atan2(p[0], p[1])) - e['yaw']
    yaw = (yaw + 180) % 360 - 180
    lat = math.degrees(math.atan2(p[2], math.hypot(p[0], p[1])))
    return W / 2 + yaw / 360 * W, (lat1 - lat) / (lat1 - lat0) * H


def load_passes(man, key):
    e = man['layers'][key]
    out = {}
    for g, pe in e['passes'].items():
        a = np.asarray(Image.open(os.path.join(IMG, pe['file'])).convert('RGBA')).astype(np.float32) / 255.0
        lin = (a[..., :3] ** 4) * pe['scale']              # come dec() dello shader (gamma 4)
        out[g] = (lin, a[..., 3])
    return e, out


def sample(img, x, y):
    """Bilineare (img H×W×C o H×W)."""
    h, w = img.shape[:2]
    x = min(max(x, 0), w - 1.001)
    y = min(max(y, 0), h - 1.001)
    x0, y0 = int(x), int(y)
    fx, fy = x - x0, y - y0
    a = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    b = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy


def main():
    with open(os.path.join(IMG, 'manifest.json')) as f:
        man = json.load(f)
    e, passes = load_passes(man, 'rod0')
    x0, y0, x1, y1 = e['rect']
    any_img = next(iter(passes.values()))[0]
    ih, iw = any_img.shape[:2]

    def img_xy(p):
        px, py = pano_xy(p, man, e)
        return (px - x0) / (x1 - x0) * iw, (py - y0) / (y1 - y0) * ih

    # da dove il fusto esce dal portacanna, visto dall'occhio
    us = np.linspace(0, 0.2, 401)
    hidden = [occluded_by_holder(rest(u), radius(u)) for u in us]
    last = max([i for i, h in enumerate(hidden) if h], default=0)
    u0 = float(us[min(len(us) - 1, last + 1)])
    # verifica sull'alfa del render: lo strato ha la barca come maschera, il portacanna ci copre il fusto
    alpha = passes['ambient'][1]
    vis = []
    for u in us:
        x, y = img_xy(rest(u))
        vis.append(float(sample(alpha, x, y)))
    # la fine del tratto coperto (alfa < 0,5) nei primi centimetri del fusto
    gap = [float(u) for u, a in zip(us, vis) if a < 0.5 and u < 0.15]
    gap_end = max(gap) if gap else 0.0
    print(f'u0 geometrico {u0:.4f}  ·  fine del tratto coperto nel render {gap_end:.4f}')
    u0 = round(max(u0, gap_end) + 0.004, 4)

    pts = []
    for i in range(N + 1):
        u = u0 + (1 - u0) * i / N
        p = rest(u)
        q = rest(min(1.0, u + 0.01)) if u < 0.99 else p + (p - rest(u - 0.01))
        x, y = img_xy(p)
        xq, yq = img_xy(q)
        tx, ty = xq - x, yq - y
        l = math.hypot(tx, ty) or 1.0
        tx, ty = tx / l, ty / l
        nx, ny = -ty, tx
        # il lato verso la lampara (in 3D, proiettato): da lì partono le fasce (la normale guarda via dalla lampara,
        # così la fascia −0,8 sta dalla sua parte; come drawTube in src/engine/renderer.ts)
        lp = p + 0.05 * (LAMP_AT - p) / np.linalg.norm(LAMP_AT - p)
        lx, ly = img_xy(lp)
        if (lx - x) * nx + (ly - y) * ny > 0:
            nx, ny = -nx, -ny
        # mezza larghezza in pixel dell'immagine (lo strato è a risoluzione piena del panorama)
        dist = float(np.linalg.norm(p))
        hw = radius(u) / dist * man['pano']['width'] / (2 * math.pi) * iw / (x1 - x0)
        bands = {}
        for g, (lin, _) in passes.items():
            row = []
            for s in BANDS:
                # più campioni lungo il fusto, per non prendere un anello o un granello di rumore
                acc = np.zeros(3)
                for k in (-1.5, -0.75, 0.0, 0.75, 1.5):
                    acc += sample(lin, x + nx * hw * s + tx * k, y + ny * hw * s + ty * k)
                row.append([round(float(v), 5) for v in acc / 5])
            bands[g] = row
        pts.append({'u': round(u, 4), 'hw': round(hw, 2), 'bands': bands})

    # gli anelli e la campanella: il loro colore nel render (al centro)
    rings = []
    for u in RINGS:
        p = rest(u) + np.array((0.0, 0.0, -0.012))
        x, y = img_xy(p)
        rings.append({'u': u, 'r': round(0.008 * (1.2 - u * 0.6), 4),
                      'col': {g: [round(float(v), 5) for v in sample(lin, x, y)] for g, (lin, _) in passes.items()}})
    p = rest(0.96) + np.array((0.0, 0.0, -0.02))
    x, y = img_xy(p)
    bell = {g: [round(float(v), 5) for v in sample(lin, x, y)] for g, (lin, _) in passes.items()}
    # lungo il fusto: mediana su tre punti (un anello o un granello di rumore non fanno una macchia); l'ultimo
    # punto, sulla punta larga meno di un pixel, prende i colori del penultimo (lì ci sono la campanella e il filo)
    for g, _ in PASSES:
        arr = np.array([q['bands'][g] for q in pts])
        med = arr.copy()
        for i in range(1, len(pts) - 1):
            med[i] = np.median(arr[i - 1:i + 2], axis=0)
        med[-1] = med[-2]
        for i, q in enumerate(pts):
            q['bands'][g] = np.round(med[i], 5).tolist()
    from boat import ROD_BASE_U
    if ROD_BASE_U < u0 + 0.008:
        print(f'ATTENZIONE: boat.ROD_BASE_U ({ROD_BASE_U}) deve superare u0 ({u0}) di almeno 0,008')
    js = {
        'u0': u0,
        'bands': list(BANDS),
        'points': [{'u': q['u'], **{k: q['bands'][g] for g, k in PASSES}} for q in pts],
        'rings': [{'u': r['u'], 'r': r['r'], **{k: r['col'][g] for g, k in PASSES}} for r in rings],
        'bell': {k: bell[g] for g, k in PASSES},
    }
    with open(OUT, 'w') as f:
        f.write('// Generato da tools/render/canna_colori.py dal render della canna intera (strato rod0): non modificare a mano.\n')
        f.write('// u0: da dove il fusto esce da dietro il portacanna, visto dall\'occhio. Per ogni punto del fusto (da u0 alla\n')
        f.write('// punta) i colori lineari delle fasce, dal lato verso la lampara all\'altro, per passo di luce come gli strati.\n')
        f.write('export const ROD_COLORS = ' + json.dumps(js, separators=(',', ':')) + ' as const;\n')
    print('scritto', OUT, 'u0 =', u0)
    for i in (0, 6, 12, 18, 24):
        b = pts[i]['bands']
        print(i, pts[i]['u'], 'hw', pts[i]['hw'], 'amb', b['ambient'][2], 'lamp', b['lamp'][0], b['lamp'][2], b['lamp'][4])


if __name__ == '__main__':
    main()
