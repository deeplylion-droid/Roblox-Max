"""
«Il ricordo» (il finale B della notte extra): il disegno a pastelli a cera di uno dei bambini di quell'estate, al
posto della foto del 1997 (idea dell'utente, 12 ottobre: «molto bambino e stilizzato»). DA APPROVARE.

La sera della Night Splash, davanti all'ingresso di Splashland (la raggiera, l'insegna, lo striscione, le lucine):
quattro bambini che si tengono per mano; ai lati la ruota panoramica e la torre degli scivoli. Tre hanno la faccia
coperta da uno scarabocchio nero, come se qualcuno l'avesse cancellata dopo (sotto si intravede ancora il sorriso); il
quarto (sei tu) è intatto, col berretto e la canna col pesciolino. Sotto, il lago a onde e, nell'acqua, una sagoma scura
enorme con un occhio solo e i dentini bianchi. In un angolo la data, «26-7-97». La cera respinge l'acqua: bagnato, il
disegno resta vivo e si rovina solo la carta (la scena sul banco la fa finali.py).

Come è fatto: un foglio d'album (la grana della carta è un campo di altezze); ogni colore è uno strato in cui i tratti
accumulano «pressione»; la cera si posa dove la grana sporge più della soglia che la pressione abbassa, quindi i
tratti leggeri restano puntinati e i bordi sfrangiati, quelli calcati coprono tutto. I tratti sono linee tremolanti
(la mano di un bambino di sette anni): sbavano, non chiudono, colorano fuori dai bordi a zig-zag.

Uso: tools/.venv/bin/python tools/render/disegno_ricordo.py [uscita.png] [--seme N] [--anteprima]
(la bozza: docs/concept/ricordo_disegno_bozza.jpg; l'immagine intera: docs/concept/ricordo_disegno.webp, seme 7)
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter, map_coordinates

W, H = 2400, 1697          # un foglio A4 orizzontale, ~8 px per millimetro
SEED = int(sys.argv[sys.argv.index('--seme') + 1]) if '--seme' in sys.argv else 7
rng = np.random.default_rng(SEED)

# i pastelli (una scatola da 12, un po' sbiaditi dagli anni)
PASTELLI = {
    'nero': (0.13, 0.12, 0.14),
    'blu_notte': (0.11, 0.14, 0.38),
    'blu': (0.16, 0.30, 0.70),
    'azzurro': (0.36, 0.66, 0.88),
    'rosso': (0.84, 0.17, 0.16),
    'rosa': (0.94, 0.50, 0.66),
    'giallo': (0.98, 0.84, 0.22),
    'arancione': (0.97, 0.53, 0.16),
    'verde': (0.22, 0.58, 0.26),
    'marrone': (0.50, 0.31, 0.17),
    'viola': (0.47, 0.26, 0.58),
    'pesca': (0.98, 0.77, 0.62),
    'bianco': (0.95, 0.95, 0.92),
}


# ───────────────────────── la carta ─────────────────────────

def carta():
    """L'altezza della grana (0..1): la grana fine dell'album, un po' di fibre, e un'ondulazione larga."""
    fine = gaussian_filter(rng.standard_normal((H, W)), 0.9)
    medio = gaussian_filter(rng.standard_normal((H, W)), 2.6)
    # le fibre: rumore allungato in una direzione a caso per pezzo
    fib = gaussian_filter(rng.standard_normal((H, W)), (0.8, 5.0))
    largo = gaussian_filter(rng.standard_normal((H // 8 + 1, W // 8 + 1)), 6.0)
    largo = np.kron(largo, np.ones((8, 8)))[:H, :W]
    h = 1.0 * fine / fine.std() + 0.7 * medio / medio.std() + 0.35 * fib / fib.std() + 0.4 * largo / largo.std()
    h = (h - h.min()) / (h.max() - h.min())
    # la distribuzione: picchi più rari (la cera leggera prende solo quelli)
    return np.clip((h - 0.25) / 0.6, 0, 1)


GRANA = carta()


# ───────────────────────── i tratti ─────────────────────────

class Strato:
    """Un colore: la pressione accumulata dai suoi tratti."""

    def __init__(self, colore):
        self.c = np.array(PASTELLI[colore])
        self.p = np.zeros((H, W), np.float32)


STRATI: list[Strato] = []


def strato(colore):
    s = Strato(colore)
    STRATI.append(s)
    return s


def tremolio(pts, forza=1.0, passo=6.0):
    """Ricampiona la linea ogni `passo` pixel e la fa tremare: un'ondulazione lenta della mano più un tremito fine."""
    pts = np.asarray(pts, float)
    if len(pts) < 2:
        return pts
    seg = np.diff(pts, axis=0)
    lun = np.hypot(seg[:, 0], seg[:, 1])
    tot = lun.sum()
    if tot < 1:
        return pts
    s = np.concatenate([[0], np.cumsum(lun)])
    n = max(2, int(tot / passo))
    t = np.linspace(0, tot, n)
    x = np.interp(t, s, pts[:, 0])
    y = np.interp(t, s, pts[:, 1])
    # normale alla linea
    dx, dy = np.gradient(x), np.gradient(y)
    nl = np.hypot(dx, dy) + 1e-6
    nx, ny = -dy / nl, dx / nl
    lento = gaussian_filter(rng.standard_normal(n), max(1.0, 60.0 / passo)) * 9.0
    fine = gaussian_filter(rng.standard_normal(n), 1.2) * 1.4
    off = forza * (lento / (np.abs(lento).max() + 1e-6) * min(7.0, 0.02 * tot + 2.0) + fine)
    return np.stack([x + nx * off, y + ny * off], 1)


def tratto(st: Strato, pts, larg=18.0, press=1.0, trema=1.0, rastremato=True):
    """Un tratto di pastello lungo la linea: la pressione sale all'inizio, cala alla fine, varia lungo il tratto."""
    p = tremolio(pts, trema)
    if len(p) < 2:
        return
    x0, y0 = np.floor(p.min(0) - larg).astype(int)
    x1, y1 = np.ceil(p.max(0) + larg).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, W - 1), min(y1, H - 1)
    if x1 <= x0 or y1 <= y0:
        return
    im = Image.new('L', (x1 - x0 + 1, y1 - y0 + 1), 0)
    d = ImageDraw.Draw(im)
    n = len(p)
    # la pressione lungo il tratto
    pr = press * (0.85 + 0.3 * gaussian_filter(rng.random(n), 3.0))
    if rastremato and n > 4:
        k = np.minimum(1.0, np.minimum(np.arange(n), np.arange(n)[::-1]) / max(2.0, n * 0.12))
        pr = pr * (0.45 + 0.55 * k)
    lw = larg * (0.9 + 0.2 * gaussian_filter(rng.random(n), 4.0))
    for i in range(n - 1):
        v = int(np.clip(pr[i] * 180, 0, 255))
        w = max(2, int(lw[i]))
        a = (p[i][0] - x0, p[i][1] - y0)
        b = (p[i + 1][0] - x0, p[i + 1][1] - y0)
        d.line([a, b], fill=v, width=w)
        d.ellipse([b[0] - w / 2, b[1] - w / 2, b[0] + w / 2, b[1] + w / 2], fill=v)
    m = np.asarray(im, np.float32) / 180.0
    m = gaussian_filter(m, 0.8)
    st.p[y0:y1 + 1, x0:x1 + 1] += m


def poligono(pts, chiudi=True):
    pts = [tuple(p) for p in pts]
    if chiudi:
        pts = pts + [pts[0]]
    return pts


def contorno(st, pts, larg=16.0, press=1.05, chiudi=True, sbava=0.04):
    """Un contorno disegnato in un colpo: non chiude bene (sbava un po' oltre o resta corto)."""
    pts = list(pts)
    if chiudi:
        extra = rng.uniform(-sbava, sbava * 2)
        m = len(pts)
        k = max(1, int(abs(extra) * m))
        pts = pts + pts[:k] if extra > 0 else pts + [pts[0]]
    tratto(st, pts, larg, press)


def cerchio(cx, cy, r, n=48, giri=1.0, schiaccia=1.0, fase=None):
    fase = rng.uniform(0, 2 * math.pi) if fase is None else fase
    t = np.linspace(0, 2 * math.pi * giri, int(n * giri))
    rr = r * (1 + 0.05 * np.sin(t * 2 + rng.uniform(0, 6)))
    return np.stack([cx + rr * np.cos(t + fase), cy + rr * schiaccia * np.sin(t + fase)], 1)


def riempi(st, maschera, angolo=25.0, passo=13.0, press=0.6, larg=20.0, fuori=10.0, buchi=0.08):
    """Il colore steso a zig-zag dentro una forma (maschera booleana), con qualche buco e qualche sbavatura fuori."""
    ys, xs = np.nonzero(maschera)
    if len(xs) == 0:
        return
    a = math.radians(angolo)
    ux, uy = math.cos(a), math.sin(a)          # lungo le righe
    vx, vy = -uy, ux                           # attraverso
    # coordinate ruotate
    cx, cy = xs.mean(), ys.mean()
    u = (xs - cx) * ux + (ys - cy) * uy
    v = (xs - cx) * vx + (ys - cy) * vy
    v0, v1 = v.min(), v.max()
    righe = np.arange(v0, v1 + passo, passo)
    zig = []
    verso = 1
    for vr in righe:
        sel = np.abs(v - vr) < passo * 0.5
        if not sel.any():
            continue
        uu = np.sort(u[sel])
        salti = np.nonzero(np.diff(uu) > passo * 2.5)[0]
        if len(salti):
            # la riga attraversa un buco: ogni pezzo è un tratto a sé
            if zig:
                tratto(st, zig, larg, press, trema=0.6)
                zig = []
            ini = np.concatenate([[0], salti + 1])
            fin = np.concatenate([salti, [len(uu) - 1]])
            for i0, i1 in zip(ini, fin):
                b0 = uu[i0] - rng.uniform(-fuori, fuori * 1.5) * 0.5
                b1 = uu[i1] + rng.uniform(-fuori, fuori * 1.5) * 0.5
                if b1 - b0 > larg * 0.6:
                    tratto(st, [(cx + b0 * ux + vr * vx, cy + b0 * uy + vr * vy), (cx + b1 * ux + vr * vx, cy + b1 * uy + vr * vy)],
                           larg, press, trema=0.4)
            continue
        a0, a1 = uu.min() - rng.uniform(-fuori, fuori * 1.5), uu.max() + rng.uniform(-fuori, fuori * 1.5)
        if rng.random() < buchi:
            # un pezzo saltato
            if zig:
                tratto(st, zig, larg, press)
                zig = []
            continue
        p0 = (cx + a0 * ux + vr * vx, cy + a0 * uy + vr * vy)
        p1 = (cx + a1 * ux + vr * vx, cy + a1 * uy + vr * vy)
        zig += [p0, p1] if verso > 0 else [p1, p0]
        verso = -verso
        if len(zig) > 24:
            tratto(st, zig, larg, press, trema=0.6)
            zig = zig[-1:]
    if len(zig) > 1:
        tratto(st, zig, larg, press, trema=0.6)


def maschera_poligono(pts):
    im = Image.new('1', (W, H), 0)
    ImageDraw.Draw(im).polygon([tuple(map(float, p)) for p in pts], fill=1)
    return np.asarray(im, bool)


def maschera_cerchio(cx, cy, r, schiaccia=1.0):
    yy, xx = np.ogrid[:H, :W]
    return ((xx - cx) / r) ** 2 + ((yy - cy) / (r * schiaccia)) ** 2 <= 1.0


# ───────────────────────── le lettere (stampatello da bambino) ─────────────────────────

# ogni lettera: tratti in un quadrato 0..1 (x a destra, y in basso)
LETTERE = {
    'A': [[(0, 1), (0.5, 0), (1, 1)], [(0.22, 0.6), (0.78, 0.6)]],
    'D': [[(0.05, 0), (0.05, 1)], [(0.05, 0), (0.55, 0.05), (0.9, 0.35), (0.9, 0.65), (0.55, 0.95), (0.05, 1)]],
    'G': [[(0.9, 0.15), (0.6, 0), (0.25, 0.05), (0.05, 0.4), (0.1, 0.8), (0.45, 1), (0.85, 0.9), (0.9, 0.6), (0.55, 0.6)]],
    'H': [[(0.05, 0), (0.05, 1)], [(0.95, 0), (0.95, 1)], [(0.05, 0.5), (0.95, 0.5)]],
    'I': [[(0.5, 0), (0.5, 1)]],
    'L': [[(0.1, 0), (0.1, 1), (0.9, 1)]],
    'N': [[(0.05, 1), (0.05, 0), (0.95, 1), (0.95, 0)]],
    'P': [[(0.1, 1), (0.1, 0), (0.6, 0.02), (0.9, 0.2), (0.85, 0.42), (0.5, 0.52), (0.1, 0.5)]],
    'S': [[(0.88, 0.12), (0.55, 0), (0.18, 0.08), (0.12, 0.3), (0.45, 0.48), (0.85, 0.65), (0.85, 0.9), (0.45, 1), (0.08, 0.88)]],
    'T': [[(0, 0.02), (1, 0)], [(0.5, 0), (0.5, 1)]],
    '2': [[(0.1, 0.2), (0.4, 0), (0.8, 0.1), (0.85, 0.35), (0.1, 1), (0.95, 1)]],
    '6': [[(0.8, 0.05), (0.4, 0.1), (0.1, 0.55), (0.2, 0.95), (0.65, 0.95), (0.8, 0.7), (0.5, 0.5), (0.15, 0.65)]],
    '7': [[(0.05, 0.02), (0.95, 0), (0.4, 1)]],
    '9': [[(0.85, 0.35), (0.6, 0.05), (0.2, 0.1), (0.15, 0.4), (0.5, 0.5), (0.85, 0.3), (0.8, 0.7), (0.5, 1)]],
    '-': [[(0.15, 0.55), (0.85, 0.5)]],
}


def scrivi(st, testo, x, y, alt, larg=14.0, press=1.1, spazio=0.32, specchia=(), salti=0.12, cresce=0.0):
    """Scrive in stampatello: lettere di misura un po' diversa, storte, che salgono o scendono; `specchia` sono gli
    indici delle lettere scritte al contrario (la S girata dei bambini)."""
    cx = x
    for i, ch in enumerate(testo):
        if ch == ' ':
            cx += alt * 0.6
            continue
        a = alt * (1 + rng.uniform(-salti, salti)) * (1 + cresce * i)
        w = a * (0.62 if ch not in 'MW' else 0.9) * (0.3 if ch in 'I1' else 1.0)
        dy = rng.uniform(-0.08, 0.08) * alt + cresce * i * alt * -0.4
        rot = math.radians(rng.uniform(-7, 7))
        for s in LETTERE[ch]:
            pts = []
            for (u, v) in s:
                if i in specchia:
                    u = 1 - u
                px, py = (u - 0.5) * w, (v - 0.5) * a
                rx = px * math.cos(rot) - py * math.sin(rot)
                ry = px * math.sin(rot) + py * math.cos(rot)
                pts.append((cx + w / 2 + rx, y + dy + ry))
            tratto(st, pts, larg, press, trema=0.35)
        cx += w + alt * spazio


# ───────────────────────── il disegno ─────────────────────────

def stella(st, cx, cy, r, press=1.0):
    pts = []
    for k in range(6):
        a = -math.pi / 2 + k * 4 * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    tratto(st, pts, 11, press, trema=0.4)


def bambino(x, piedi, alt, maglia, capelli, gonna=False, codini=False, cancellato=True, berretto=None, mano_sx=None,
            mano_dx=None, canna=False, testa_r=None):
    """Un bambino come lo disegna un bambino: la testa tonda grande, il corpo (maglietta o vestito), le braccia a
    bastoncino verso le mani dei vicini, le mani a raggiera, le gambe, le scarpe. Restituisce le due mani."""
    r = testa_r or alt * 0.17
    cy = piedi - alt + r
    corpo_top = cy + r * 0.95
    corpo_bot = piedi - alt * 0.33
    # la testa (pesca) e la faccia
    pelle = strato('pesca')
    riempi(pelle, maschera_cerchio(x, cy, r * 0.96), angolo=rng.uniform(-30, 30), passo=12, press=0.55, fuori=4)
    nero = strato('nero')
    contorno(nero, cerchio(x, cy, r, giri=1.06), larg=13, press=1.0)
    # i capelli: scarabocchi sopra la testa
    cap = strato(capelli)
    for k in range(9):
        a = math.pi * (1.05 + 0.9 * k / 8)
        p0 = (x + r * 0.95 * math.cos(a), cy + r * 0.95 * math.sin(a))
        p1 = (x + r * 1.25 * math.cos(a + 0.12), cy + r * 1.22 * math.sin(a + 0.12))
        tratto(cap, [p0, p1, (x + r * 0.9 * math.cos(a + 0.3), cy + r * 0.92 * math.sin(a + 0.3))], 13, 0.95)
    if codini:
        for sx in (-1, 1):
            bx = x + sx * r * 1.05
            tratto(cap, [(bx, cy - r * 0.2), (bx + sx * r * 0.45, cy + r * 0.25), (bx + sx * r * 0.3, cy + r * 0.75)], 15, 1.0)
            tratto(strato('rosso'), cerchio(bx + sx * r * 0.08, cy - r * 0.18, r * 0.12, n=16), 10, 1.0)
    if berretto:
        # il berretto sopra la fronte (la cupola sopra gli occhi) e la visiera di lato
        b = strato(berretto)
        base = cy - r * 0.32
        cupola = [(x + r * 1.0 * math.cos(a), base + r * 0.78 * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 20)]
        riempi(b, maschera_poligono(cupola), angolo=10, passo=10, press=0.95, fuori=3)
        contorno(nero, cupola + [cupola[0]], larg=12, press=1.0, chiudi=False)
        visiera = [(x + r * 0.3, base - r * 0.06), (x + r * 1.6, base + r * 0.02), (x + r * 1.55, base + r * 0.2), (x + r * 0.35, base + r * 0.12)]
        riempi(b, maschera_poligono(visiera), angolo=0, passo=9, press=1.05, fuori=2)
        contorno(nero, visiera, larg=11, press=1.0)
    # la faccia: due occhi a pallino, il sorriso, le guance (tutti l'avevano)
    f = strato('nero')
    for sx in (-1, 1):
        tratto(f, cerchio(x + sx * r * 0.36, cy - r * 0.02, r * 0.08, n=12, giri=1.3), 10, 1.2)
    sorriso = [(x + r * 0.5 * math.cos(a), cy + r * 0.2 + r * 0.36 * math.sin(a)) for a in np.linspace(0.25, math.pi - 0.25, 12)]
    tratto(f, sorriso, 10, 1.1)
    guance = strato('rosa')
    for sx in (-1, 1):
        riempi(guance, maschera_cerchio(x + sx * r * 0.6, cy + r * 0.3, r * 0.13), angolo=40, passo=8, press=0.6, fuori=2)
    if cancellato:
        # poi qualcuno l'ha cancellata: uno scarabocchio nero calcato, a giri e a zig-zag, che lascia intravedere sotto
        # la faccia di prima (un pezzo di sorriso, un occhio)
        sc = strato('nero')
        n = 90
        t = np.linspace(0, 2 * math.pi * rng.uniform(3.2, 4.2), n)
        rr = r * (0.45 + 0.6 * rng.random(n) ** 0.6)
        jit = gaussian_filter(rng.standard_normal(n), 1.5) * r * 0.1
        pts = np.stack([x + (rr + jit) * np.cos(t + rng.uniform(0, 6)) + rng.uniform(-6, 6),
                        cy + (rr - jit) * 0.9 * np.sin(t * rng.uniform(0.95, 1.05)) + rng.uniform(-6, 6)], 1)
        tratto(sc, pts, 8, 1.15, trema=0.35, rastremato=False)
        # e il zig-zag veloce da una parte all'altra
        zz = []
        for k in range(7):
            yk = cy - r * 0.75 + k * r * 0.26
            half = r * math.sqrt(max(0.05, 1 - ((yk - cy) / (r * 1.05)) ** 2)) * 1.1
            zz.append((x - half + rng.uniform(-10, 10), yk) if k % 2 == 0 else (x + half + rng.uniform(-10, 10), yk))
        tratto(sc, zz, 9, 1.3, trema=0.25, rastremato=False)
    # il corpo
    mg = strato(maglia)
    spalle = r * 1.05
    if gonna:
        corpo = [(x - spalle * 0.55, corpo_top), (x + spalle * 0.55, corpo_top), (x + spalle * 1.15, corpo_bot), (x - spalle * 1.15, corpo_bot)]
    else:
        corpo = [(x - spalle, corpo_top), (x + spalle, corpo_top), (x + spalle * 0.95, corpo_bot), (x - spalle * 0.95, corpo_bot)]
    riempi(mg, maschera_poligono(corpo), angolo=rng.uniform(60, 120), passo=13, press=0.7, fuori=9)
    contorno(nero, corpo, larg=13, press=1.0)
    # le gambe e le scarpe
    gamba_top = corpo_bot
    for sx in (-1, 1):
        gx = x + sx * spalle * 0.42
        tratto(nero, [(gx, gamba_top), (gx + sx * 6, piedi - 14)], 13, 1.05)
        sc = strato('marrone' if not gonna else 'rosso')
        sp = [(gx + sx * 6 + dx, piedi - 8 + dy) for dx, dy in [(-22, -10), (26 * sx + 4, -12), (30 * sx, 6), (-20, 8)]]
        riempi(sc, maschera_poligono(sp), angolo=0, passo=8, press=0.9, fuori=2)
    # le braccia: dalle spalle alle mani (dei vicini o abbassate)
    mani = []
    for sx, dest in ((-1, mano_sx), (1, mano_dx)):
        sp = (x + sx * spalle * 0.92, corpo_top + 18)
        if dest is None:
            dest = (x + sx * spalle * 1.9, corpo_top + alt * 0.28)
        gomito = ((sp[0] + dest[0]) / 2 + sx * 6, (sp[1] + dest[1]) / 2 + 10)
        tratto(nero, [sp, gomito, dest], 12, 1.0)
        mani.append(dest)
    # le mani a raggiera (cinque dita)
    for (mx, my) in mani:
        tratto(nero, cerchio(mx, my, 13, n=14, giri=1.1), 10, 1.0)
        for k in range(5):
            a = -math.pi / 2 + (k - 2) * 0.42 + rng.uniform(-0.1, 0.1)
            tratto(nero, [(mx + 12 * math.cos(a), my + 12 * math.sin(a)), (mx + 30 * math.cos(a), my + 30 * math.sin(a))], 8, 0.95,
                   trema=0.2)
    if canna:
        # la canna giocattolo (marrone), il filo e il pesciolino arancione
        mx, my = mani[1]
        cima = (mx + alt * 0.36, my - alt * 0.86)
        tratto(strato('marrone'), [(mx - 30, my + 26), cima], 15, 1.1)
        filo_fine = (cima[0] + 8, cima[1] + alt * 0.55)
        tratto(nero, [cima, (cima[0] + 6, cima[1] + alt * 0.3), filo_fine], 6, 0.8)
        pesce = strato('arancione')
        px, py = filo_fine[0], filo_fine[1] + 30
        corpo_p = cerchio(px, py, 30, n=24, schiaccia=0.55)
        riempi(pesce, maschera_cerchio(px, py, 30, 0.55), angolo=0, passo=8, press=0.95, fuori=3)
        coda = [(px + 26, py), (px + 52, py - 18), (px + 50, py + 18)]
        riempi(pesce, maschera_poligono(coda), angolo=90, passo=8, press=0.95, fuori=3)
        contorno(nero, corpo_p, larg=9, press=1.0)
        contorno(nero, coda, larg=9, press=1.0)
        tratto(nero, cerchio(px - 14, py - 4, 4, n=8), 7, 1.2)
    return mani


def ruota(cx, cy, r):
    """La ruota panoramica come la disegna un bambino: il cerchio, i raggi, le cabine colorate, le due gambe."""
    nero = strato('nero')
    tratto(nero, [(cx, cy), (cx - r * 0.75, cy + r * 1.35)], 14, 1.0)
    tratto(nero, [(cx, cy), (cx + r * 0.75, cy + r * 1.35)], 14, 1.0)
    contorno(strato('viola'), cerchio(cx, cy, r, n=60, giri=1.05), larg=16, press=1.1)
    for k in range(8):
        a = k * math.pi / 4 + 0.2
        tratto(nero, [(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))], 8, 0.85, trema=0.3)
    cols = ['rosso', 'giallo', 'verde', 'azzurro', 'arancione', 'rosa', 'blu', 'rosso']
    for k in range(8):
        a = k * math.pi / 4 + 0.2
        px, py = cx + r * math.cos(a), cy + r * math.sin(a) + 26
        q = [(px - 24, py - 18), (px + 24, py - 18), (px + 20, py + 20), (px - 20, py + 20)]
        riempi(strato(cols[k]), maschera_poligono(q), angolo=rng.uniform(0, 90), passo=8, press=1.0, fuori=3)
        contorno(nero, q, larg=8, press=0.95)


def scivoli(cx, base, alt):
    """La torre degli scivoli: il palo, il tetto rosso a punta, i tubi colorati che girano attorno."""
    nero = strato('nero')
    tratto(nero, [(cx - 30, base), (cx - 26, base - alt)], 12, 1.0)
    tratto(nero, [(cx + 30, base), (cx + 28, base - alt)], 12, 1.0)
    tetto = [(cx - 85, base - alt), (cx, base - alt - 140), (cx + 85, base - alt)]
    riempi(strato('rosso'), maschera_poligono(tetto), angolo=70, passo=10, press=1.05, fuori=4)
    contorno(nero, tetto, larg=12, press=1.0)
    cols = ['giallo', 'verde', 'rosso', 'azzurro', 'arancione']
    for k in range(5):
        y0 = base - alt + 60 + k * (alt - 90) / 5
        t = np.linspace(-0.2, math.pi + 0.2, 20)
        pts = [(cx + 112 * math.cos(tt) * (1 if k % 2 else -1), y0 + 52 * math.sin(tt)) for tt in t]
        tratto(strato(cols[k]), pts, 30, 1.05, trema=0.5)


def disegno():
    ys = np.arange(H)[:, None]
    xs = np.arange(W)[None, :]
    # ── il cielo della sera: una striscia blu notte calcata in alto, che scende a strappi; le stelle e la luna gialle
    cielo = strato('blu_notte')
    bordo = 470 + 60 * np.sin(xs / 210.0 + 1.3) + 35 * np.sin(xs / 77.0)
    m_cielo = (ys < bordo)
    riempi(cielo, m_cielo, angolo=-8, passo=15, press=0.95, larg=24, fuori=25, buchi=0.03)
    riempi(cielo, m_cielo & (ys < bordo - 120), angolo=12, passo=19, press=0.6, larg=22, fuori=20, buchi=0.1)
    gialli = strato('giallo')
    for (sx, sy, sr) in [(170, 100, 46), (420, 250, 38), (690, 80, 34), (1600, 130, 40), (1880, 330, 40), (2280, 300, 36),
                         (1180, 60, 30), (900, 300, 28), (2240, 60, 32), (320, 400, 30), (1450, 330, 26)]:
        stella(gialli, sx + rng.uniform(-15, 15), sy + rng.uniform(-10, 10), sr, press=1.25)
    # la luna: una falce (l'arco esterno e quello interno), gialla col bordo arancione
    lx, ly, lr = 2030, 170, 115
    est = [(lx + lr * math.cos(a), ly + lr * math.sin(a)) for a in np.linspace(math.radians(65), math.radians(295), 30)]
    c2x, c2y, r2 = lx + 58, ly - 8, lr * 0.86
    ang_i = np.linspace(math.radians(295 + 12), math.radians(65 - 12), 30)
    inn = [(c2x + r2 * math.cos(a), c2y + r2 * math.sin(a)) for a in ang_i]
    falce = est + inn
    riempi(gialli, maschera_poligono(falce), angolo=45, passo=8, press=1.35, fuori=3)
    contorno(strato('arancione'), falce, larg=10, press=1.05)

    # ── sullo sfondo, ai lati dell'ingresso: la ruota panoramica a sinistra, gli scivoli a destra
    ruota(300, 760, 190)
    scivoli(2265, 1300, 640)

    # ── l'ingresso di Splashland: i due piloni rosa, la trave gialla con SPLASHLAND, la raggiera sopra
    rosa = strato('rosa')
    nero = strato('nero')
    pil_y0, pil_y1 = 560, 1300
    for (a, b) in [(560, 680), (1840, 1960)]:
        q = [(a, pil_y0), (b, pil_y0 + rng.uniform(-6, 6)), (b + 6, pil_y1), (a - 4, pil_y1)]
        riempi(rosa, maschera_poligono(q), angolo=80, passo=12, press=0.9, fuori=8)
        contorno(nero, q, larg=14, press=1.0)
    trave = [(500, 450), (2020, 438), (2025, 570), (495, 582)]
    riempi(strato('giallo'), maschera_poligono(trave), angolo=5, passo=12, press=0.85, fuori=8)
    contorno(nero, trave, larg=14, press=1.0)
    rx, ry, rr = 1260, 440, 230
    semi = maschera_cerchio(rx, ry, rr * 0.55) & (ys < ry)
    riempi(strato('arancione'), semi, angolo=30, passo=10, press=1.1, fuori=4)
    for k in range(11):
        a = math.pi + (k + 0.5) * math.pi / 11
        tratto(strato('rosso' if k % 2 else 'arancione'), [(rx + rr * 0.62 * math.cos(a), ry + rr * 0.62 * math.sin(a)),
                                                            (rx + rr * 1.05 * math.cos(a), ry + rr * 1.05 * math.sin(a))], 20, 1.15)
    contorno(nero, [(rx + rr * 0.56 * math.cos(a), ry + rr * 0.56 * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 24)],
             larg=12, press=1.0, chiudi=False)
    # SPLASHLAND sulla trave (la seconda S girata, come la scrive un bambino)
    scrivi(strato('blu'), 'SPLASHLAND', 620, 512, 92, larg=17, press=1.35, spazio=0.4, specchia=(4,))
    # le lucine: un filo che pende sotto la trave, coi pallini colorati
    filo = [(680 + (1840 - 680) * t, 610 + 60 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 30)]
    tratto(nero, filo, 7, 0.75)
    cols = ['rosso', 'giallo', 'verde', 'azzurro', 'arancione', 'rosa']
    for j, t in enumerate(np.linspace(0.05, 0.95, 14)):
        px, py = 680 + (1840 - 680) * t, 610 + 60 * math.sin(math.pi * t) + 20
        riempi(strato(cols[j % len(cols)]), maschera_cerchio(px, py, 17), angolo=rng.uniform(0, 90), passo=7, press=1.2, fuori=2)
    # lo striscione appeso fra i piloni, con NIGHT SPLASH
    stri = [(770, 690), (1750, 682), (1738, 800), (782, 808)]
    contorno(strato('rosso'), stri, larg=13, press=1.0)
    for (ax, ay) in [(770, 690), (1750, 682)]:
        tratto(nero, [(ax, ay), (ax + rng.uniform(-30, -10) if ax < 1000 else ax + rng.uniform(10, 30), 640)], 8, 0.9)
    scrivi(strato('rosso'), 'NIGHT SPLASH', 830, 748, 78, larg=15, press=1.3, spazio=0.36, cresce=-0.01)

    # ── il prato (una striscia verde) e il lago in basso, a onde
    verde = strato('verde')
    prato = (ys > 1300 + 18 * np.sin(xs / 150.0)) & (ys < 1420)
    riempi(verde, prato, angolo=-5, passo=14, press=0.8, larg=22, fuori=14, buchi=0.06)
    for k in range(80):
        gx = rng.uniform(20, W - 20)
        tratto(verde, [(gx, 1325), (gx + rng.uniform(-14, 14), 1268)], 9, 0.95, trema=0.2)
    lago_top = 1440
    # la cosa nell'acqua: una sagoma enorme e gobba sotto le onde, con un occhio solo, grande e bianco, che ti guarda,
    # e una bocca lunga coi dentini (il bambino l'ha vista)
    mx, my = 1420, 1700
    gobbe = []
    for k, ax in enumerate(np.linspace(-1, 1, 40)):
        hx = mx + ax * 620
        hy = my - 230 * math.sqrt(max(0.0, 1 - ax * ax)) - 30 * math.sin(ax * 9.0) ** 2 + rng.uniform(-6, 6)
        gobbe.append((hx, hy))
    sagoma = gobbe + [(mx + 640, H + 40), (mx - 640, H + 40)]
    m_sag = maschera_poligono(sagoma) & (ys > lago_top + 30)
    occ_x, occ_y, occ_r = mx - 260, my - 130, 92
    occhio = maschera_cerchio(occ_x, occ_y, occ_r, 0.78)
    # l'acqua chiara stesa per prima, girando attorno all'occhio
    acqua = (ys > lago_top + 6 * np.sin(xs / 90.0)) & ~occhio
    riempi(strato('azzurro'), acqua, angolo=0, passo=15, press=0.85, larg=24, fuori=10, buchi=0.05)
    ombra = strato('blu_notte')
    riempi(ombra, m_sag & ~occhio, angolo=15, passo=10, press=1.35, larg=22, fuori=5, buchi=0.01)
    riempi(ombra, m_sag & ~occhio, angolo=-35, passo=14, press=1.0, larg=20, fuori=3, buchi=0.03)
    contorno(strato('nero'), gobbe, larg=12, press=1.1, chiudi=False)
    neroc = strato('nero')
    contorno(neroc, cerchio(occ_x, occ_y, occ_r + 4, schiaccia=0.78), larg=13, press=1.4)
    riempi(strato('giallo'), maschera_cerchio(occ_x + 12, occ_y + 6, 42, 0.95), angolo=20, passo=7, press=1.1, fuori=1)
    pupilla = strato('nero')
    riempi(pupilla, maschera_cerchio(occ_x + 15, occ_y + 8, 21, 1.0), angolo=0, passo=5, press=2.0, fuori=1)
    for k in range(7):
        a = math.pi * (1.15 + 0.7 * k / 6)
        p0 = (occ_x + (occ_r + 4) * math.cos(a), occ_y + (occ_r + 4) * 0.78 * math.sin(a))
        p1 = (occ_x + (occ_r + 34) * math.cos(a), occ_y + (occ_r + 34) * 0.78 * math.sin(a))
        tratto(pupilla, [p0, p1], 8, 1.2, trema=0.2)
    # la bocca: una riga lunga coi dentini bianchi a triangolo
    bocca = [(mx - 120 + 520 * u, my - 105 + 25 * math.sin(u * 3.0)) for u in np.linspace(0, 1, 16)]
    denti = strato('bianco')
    bordi = strato('nero')
    for k in range(9):
        u = (k + 0.5) / 9
        bx, by = mx - 120 + 520 * u, my - 105 + 25 * math.sin(u * 3.0)
        tri = [(bx - 19, by), (bx, by + 34), (bx + 19, by)]
        riempi(denti, maschera_poligono(tri), angolo=80, passo=6, press=1.5, fuori=1)
        tratto(bordi, tri, 7, 1.1, trema=0.15)
    tratto(bordi, bocca, 11, 1.3)
    # le onde blu sopra tutto
    blu = strato('blu')
    fuori_occhio = lambda q: ((q[0] - occ_x) / (occ_r + 45)) ** 2 + ((q[1] - occ_y) / ((occ_r + 45) * 0.78)) ** 2 > 1.0
    for riga in range(5):
        y0 = lago_top + 34 + riga * 52
        onde = [(x, y0 + 16 * (1 if (i % 2) else -1)) for i, x in enumerate(np.arange(-20, W + 40, 58))]
        # le onde passano sopra a tutto, ma non sull'occhio: lì il bambino ha girato attorno
        pezzo = []
        for q in onde:
            if fuori_occhio(q):
                pezzo.append(q)
            else:
                if len(pezzo) > 1:
                    tratto(blu, pezzo, 12, 1.0, trema=0.4)
                pezzo = []
        if len(pezzo) > 1:
            tratto(blu, pezzo, 12, 1.0, trema=0.4)

    # ── i quattro bambini per mano, sul prato davanti all'ingresso
    piedi = 1335
    alt = 480
    xs_b = [770, 1100, 1430, 1770]
    braccia_y = piedi - alt * 0.55
    mani_tra = [((xs_b[i] + xs_b[i + 1]) / 2 + rng.uniform(-8, 8), braccia_y + rng.uniform(-12, 12)) for i in range(3)]
    bambino(xs_b[0], piedi, alt * 0.97, 'rosso', 'marrone', gonna=True, codini=True, mano_dx=mani_tra[0])
    bambino(xs_b[1], piedi + 6, alt * 1.03, 'verde', 'nero', mano_sx=mani_tra[0], mano_dx=mani_tra[1])
    bambino(xs_b[2], piedi - 4, alt * 0.95, 'viola', 'giallo', gonna=True, mano_sx=mani_tra[1], mano_dx=mani_tra[2])
    bambino(xs_b[3], piedi + 2, alt * 1.0, 'azzurro', 'marrone', cancellato=False, berretto='giallo', mano_sx=mani_tra[2],
            mano_dx=(xs_b[3] + 110, braccia_y - 30), canna=True)

    # ── la data, a pastello nero, piccola, in basso a sinistra sul prato
    scrivi(strato('nero'), '26-7-97', 80, 1378, 66, larg=11, press=1.2, spazio=0.32)


def componi():
    """Stende gli strati sulla carta nell'ordine in cui sono stati disegnati."""
    carta_col = np.array([0.965, 0.95, 0.905])
    img = np.ones((H, W, 3)) * carta_col
    # un po' di ombra della grana sulla carta stessa
    img *= (0.975 + 0.03 * GRANA)[..., None]
    g = GRANA
    for st in STRATI:
        if st.p.max() <= 0:
            continue
        # la cera si posa dove la grana sporge sopra la soglia che la pressione abbassa
        soglia = 1.0 - np.clip(st.p, 0, 2.2) * 0.62
        cov = np.clip((g - soglia + 0.06) / 0.12, 0, 1)
        cov *= np.clip(st.p * 3.0, 0, 1)                      # dove non c'è il tratto, niente
        a = (cov * 0.93)[..., None]
        # la cera sopra altra cera si mescola un po' (sottrattivo): il giallo sul blu tira al verde
        sotto = img
        mix = 0.78 * st.c + 0.22 * (st.c * sotto / np.maximum(sotto.max(-1, keepdims=True), 1e-3))
        img = sotto * (1 - a) + mix * a
    return img


def invecchia(img):
    """Gli anni: la carta ingiallita verso i bordi, la piega in quattro (il foglio è stato piegato), qualche macchia."""
    yy, xx = np.mgrid[:H, :W]
    bordo = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy)) / 260.0
    ing = np.clip(1 - bordo, 0, 1) ** 2
    giallo = np.array([0.93, 0.84, 0.62])
    img = img * (1 - 0.22 * ing[..., None]) + giallo * 0.22 * ing[..., None] * img.mean(-1, keepdims=True) / 0.9
    # le pieghe: una verticale e una orizzontale, un filo d'ombra e la cera crepata lungo la piega
    for (asse, pos) in ((1, W * 0.5 + 6), (0, H * 0.5 - 4)):
        d = (xx - pos) if asse == 1 else (yy - pos)
        ombra = np.exp(-(d / 3.0) ** 2) * 0.16 + np.exp(-(d / 22.0) ** 2) * 0.05 * np.sign(d)
        img = img * (1 - ombra[..., None])
    # le macchioline (puntini di umidità)
    for k in range(40):
        cx, cy = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(2, 9)
        m = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))
        img = img * (1 - 0.18 * m[..., None] * np.array([0.3, 0.55, 0.9]))
    return np.clip(img, 0, 1)


def main():
    out = next((a for a in sys.argv[1:] if not a.startswith('--') and not a.isdigit()), 'ricordo_disegno.png')
    disegno()
    img = invecchia(componi())
    im = Image.fromarray((img * 255 + 0.5).astype(np.uint8))
    im.save(out)
    if '--anteprima' in sys.argv:
        im.resize((W // 2, H // 2), Image.LANCZOS).save(os.path.splitext(out)[0] + '_anteprima.jpg', quality=88)
    print('disegno', out, im.size)


if __name__ == '__main__':
    main()
