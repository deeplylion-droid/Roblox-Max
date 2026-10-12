"""
I disegni a pastelli a cera dei bambini di Splashland (idea dell'utente del 12 ottobre: «molto bambino e stilizzato»).

- «Il ricordo» (il finale B della notte extra, approvato il 12 ottobre): la sera della Night Splash (14 agosto 1997),
  davanti all'ingresso di Splashland, quattro bambini per mano. Tre hanno la faccia cancellata da uno scarabocchio nero
  (sotto si intravede ancora il sorriso) e una cosa sola a testa che dice chi erano: i braccioli (Molly), il salvagente
  a paperella (Gulpy), il giocattolo luminoso (Hatch). Il quarto (sei tu) è intatto, col berretto e la canna col
  pesciolino. Nel lago, la cosa con un occhio solo e i dentini bianchi.
- I disegni dell'alba (12 ottobre, DA APPROVARE): all'alba di ogni notte vinta, dalla prima alla quinta, sul banco
  c'è un disegno bagnato dei bambini di quella notte, com'erano prima della Madre (poi restano nel Diario):
  1 «La piscina»: Gulpy allo Snack Shack col panino gigante («HO FAME!»), Molly sul trampolino coi braccioli
    («GUARDAMI!»), gli occhi di Hatch nel tunnel dello scivolo e il suo giocattolo che brilla;
  2 «Il mio tesoro»: Robin sotto gli scivoli col mucchio delle cose prese agli altri, i biglietti della sala giochi
    attorno alle braccia, e una torcia che lo becca in faccia;
  3 «Tanti auguri»: la torta con le candeline, la festeggiata che piange, Archie con la trombetta che le spegne;
  4 «Sott'acqua»: la piscina vista di lato, un bambino che si sbraccia in superficie e sotto, con la cuffia a fiori,
    la bambina che gli tira le gambe ridendo (Lampy);
  5 «Marco Polo»: in mezzo alla piscina lui con gli occhialini neri, a braccia aperte, «MARCO!»; attorno «POLO!» (Fangy).

Come è fatto: un foglio (d'album o di quaderno a quadretti) con la sua grana, un campo di altezze; ogni colore è uno
strato in cui i tratti accumulano «pressione»; la cera si posa dove la grana sporge più della soglia che la pressione
abbassa, quindi i tratti leggeri restano puntinati e i bordi sfrangiati, quelli calcati coprono tutto. I tratti sono
linee tremolanti (la mano di un bambino di sette anni): sbavano, non chiudono, colorano fuori dai bordi a zig-zag. La
cera respinge l'acqua: bagnato, il disegno resta vivo e si rovina solo la carta.

Uso: tools/.venv/bin/python tools/render/pastelli.py <ricordo|piscina|tesoro|compleanno|sottacqua|marcopolo|tutti>
     [--uscita cartella] [--anteprima]
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

W, H = 2400, 1697          # un foglio A4 orizzontale, ~8 px per millimetro

# i pastelli (una scatola da 12 più qualcuno, un po' sbiaditi dagli anni)
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
    'verde_chiaro': (0.55, 0.80, 0.30),
    'marrone': (0.50, 0.31, 0.17),
    'viola': (0.47, 0.26, 0.58),
    'pesca': (0.98, 0.77, 0.62),
    'grigio': (0.55, 0.55, 0.58),
    'bianco': (0.95, 0.95, 0.92),
}


# ───────────────────────── il foglio ─────────────────────────

class Foglio:
    """Lo stato di un disegno: il generatore dei numeri a caso, la grana della carta, gli strati di colore."""

    def __init__(self, seme: int, tipo: str = 'album'):
        self.rng = np.random.default_rng(seme)
        self.tipo = tipo
        self.grana = self._carta()
        self.strati: list[Strato] = []

    def _carta(self):
        rng = self.rng
        fine = gaussian_filter(rng.standard_normal((H, W)), 0.9)
        medio = gaussian_filter(rng.standard_normal((H, W)), 2.6)
        fib = gaussian_filter(rng.standard_normal((H, W)), (0.8, 5.0))
        largo = gaussian_filter(rng.standard_normal((H // 8 + 1, W // 8 + 1)), 6.0)
        largo = np.kron(largo, np.ones((8, 8)))[:H, :W]
        liscia = self.tipo == 'quadretti'          # la carta del quaderno è più liscia: la cera prende di più
        h = (1.0 * fine / fine.std() + (0.5 if liscia else 0.7) * medio / medio.std() + 0.35 * fib / fib.std()
             + 0.4 * largo / largo.std())
        h = (h - h.min()) / (h.max() - h.min())
        return np.clip((h - (0.18 if liscia else 0.25)) / 0.6, 0, 1)


F: Foglio | None = None


def foglio(seme: int, tipo: str = 'album') -> Foglio:
    global F
    F = Foglio(seme, tipo)
    return F


def rnd():
    return F.rng


class Strato:
    """Un colore: la pressione accumulata dai suoi tratti."""

    def __init__(self, colore):
        self.c = np.array(PASTELLI[colore])
        self.p = np.zeros((H, W), np.float32)


def strato(colore):
    s = Strato(colore)
    F.strati.append(s)
    return s


# ───────────────────────── i tratti ─────────────────────────

def tremolio(pts, forza=1.0, passo=6.0):
    """Ricampiona la linea ogni `passo` pixel e la fa tremare: un'ondulazione lenta della mano più un tremito fine."""
    rng = rnd()
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
    dx, dy = np.gradient(x), np.gradient(y)
    nl = np.hypot(dx, dy) + 1e-6
    nx, ny = -dy / nl, dx / nl
    lento = gaussian_filter(rng.standard_normal(n), max(1.0, 60.0 / passo)) * 9.0
    fine = gaussian_filter(rng.standard_normal(n), 1.2) * 1.4
    off = forza * (lento / (np.abs(lento).max() + 1e-6) * min(7.0, 0.02 * tot + 2.0) + fine)
    return np.stack([x + nx * off, y + ny * off], 1)


def tratto(st: Strato, pts, larg=18.0, press=1.0, trema=1.0, rastremato=True):
    """Un tratto di pastello lungo la linea: la pressione sale all'inizio, cala alla fine, varia lungo il tratto."""
    rng = rnd()
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


def contorno(st, pts, larg=16.0, press=1.05, chiudi=True, sbava=0.04):
    """Un contorno disegnato in un colpo: non chiude bene (sbava un po' oltre o resta corto)."""
    pts = list(pts)
    if chiudi:
        extra = rnd().uniform(-sbava, sbava * 2)
        k = max(1, int(abs(extra) * len(pts)))
        pts = pts + pts[:k] if extra > 0 else pts + [pts[0]]
    tratto(st, pts, larg, press)


def cerchio(cx, cy, r, n=48, giri=1.0, schiaccia=1.0, fase=None):
    rng = rnd()
    fase = rng.uniform(0, 2 * math.pi) if fase is None else fase
    t = np.linspace(0, 2 * math.pi * giri, max(4, int(n * giri)))
    rr = r * (1 + 0.05 * np.sin(t * 2 + rng.uniform(0, 6)))
    return np.stack([cx + rr * np.cos(t + fase), cy + rr * schiaccia * np.sin(t + fase)], 1)


def riempi(st, maschera, angolo=25.0, passo=13.0, press=0.6, larg=20.0, fuori=10.0, buchi=0.08):
    """Il colore steso a zig-zag dentro una forma (maschera booleana), con qualche buco e qualche sbavatura fuori; dove
    la forma ha un buco la riga si spezza."""
    rng = rnd()
    ys, xs = np.nonzero(maschera)
    if len(xs) == 0:
        return
    a = math.radians(angolo)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    cx, cy = xs.mean(), ys.mean()
    u = (xs - cx) * ux + (ys - cy) * uy
    v = (xs - cx) * vx + (ys - cy) * vy
    righe = np.arange(v.min(), v.max() + passo, passo)
    zig = []
    verso = 1
    for vr in righe:
        sel = np.abs(v - vr) < passo * 0.5
        if not sel.any():
            continue
        uu = np.sort(u[sel])
        salti = np.nonzero(np.diff(uu) > passo * 2.5)[0]
        if len(salti):
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


def colora(colore, pts, press=0.75, angolo=None, passo=12, bordo='nero', larg_bordo=12, fuori=6):
    """Una forma colorata e ripassata col contorno (come fanno i bambini: prima il bordo o prima il colore, uguale)."""
    angolo = rnd().uniform(-40, 40) if angolo is None else angolo
    riempi(strato(colore), maschera_poligono(pts), angolo=angolo, passo=passo, press=press, fuori=fuori)
    if bordo:
        contorno(strato(bordo), pts, larg=larg_bordo, press=1.0)


def tondo(colore, cx, cy, r, press=0.8, schiaccia=1.0, bordo='nero', larg_bordo=11):
    riempi(strato(colore), maschera_cerchio(cx, cy, r, schiaccia), angolo=rnd().uniform(0, 90), passo=9, press=press, fuori=3)
    if bordo:
        contorno(strato(bordo), cerchio(cx, cy, r + 2, schiaccia=schiaccia), larg=larg_bordo, press=1.0)


# ───────────────────────── le lettere (stampatello da bambino) ─────────────────────────

# ogni lettera: tratti in un quadrato 0..1 (x a destra, y in basso)
_O = [(0.5, 0), (0.15, 0.12), (0.02, 0.5), (0.15, 0.88), (0.5, 1), (0.85, 0.88), (0.98, 0.5), (0.85, 0.12), (0.5, 0)]
LETTERE = {
    'A': [[(0, 1), (0.5, 0), (1, 1)], [(0.22, 0.6), (0.78, 0.6)]],
    'B': [[(0.1, 1), (0.1, 0), (0.6, 0.02), (0.85, 0.2), (0.6, 0.47), (0.1, 0.5)], [(0.6, 0.47), (0.92, 0.7), (0.65, 0.98), (0.1, 1)]],
    'C': [[(0.9, 0.15), (0.55, 0), (0.15, 0.15), (0.05, 0.5), (0.15, 0.85), (0.55, 1), (0.9, 0.85)]],
    'D': [[(0.05, 0), (0.05, 1)], [(0.05, 0), (0.55, 0.05), (0.9, 0.35), (0.9, 0.65), (0.55, 0.95), (0.05, 1)]],
    'E': [[(0.9, 0), (0.1, 0), (0.1, 1), (0.9, 1)], [(0.1, 0.5), (0.7, 0.5)]],
    'È': [[(0.9, 0), (0.1, 0), (0.1, 1), (0.9, 1)], [(0.1, 0.5), (0.7, 0.5)], [(0.3, -0.38), (0.6, -0.12)]],
    'F': [[(0.9, 0), (0.1, 0), (0.1, 1)], [(0.1, 0.5), (0.7, 0.5)]],
    'G': [[(0.9, 0.15), (0.6, 0), (0.25, 0.05), (0.05, 0.4), (0.1, 0.8), (0.45, 1), (0.85, 0.9), (0.9, 0.6), (0.55, 0.6)]],
    'H': [[(0.05, 0), (0.05, 1)], [(0.95, 0), (0.95, 1)], [(0.05, 0.5), (0.95, 0.5)]],
    'I': [[(0.5, 0), (0.5, 1)]],
    'K': [[(0.1, 0), (0.1, 1)], [(0.85, 0), (0.1, 0.55)], [(0.35, 0.4), (0.9, 1)]],
    'L': [[(0.1, 0), (0.1, 1), (0.9, 1)]],
    'M': [[(0.05, 1), (0.1, 0), (0.5, 0.6), (0.9, 0), (0.95, 1)]],
    'N': [[(0.05, 1), (0.05, 0), (0.95, 1), (0.95, 0)]],
    'O': [_O],
    'P': [[(0.1, 1), (0.1, 0), (0.6, 0.02), (0.9, 0.2), (0.85, 0.42), (0.5, 0.52), (0.1, 0.5)]],
    'R': [[(0.1, 1), (0.1, 0), (0.6, 0.02), (0.9, 0.2), (0.85, 0.42), (0.5, 0.52), (0.1, 0.5)], [(0.45, 0.52), (0.9, 1)]],
    'S': [[(0.88, 0.12), (0.55, 0), (0.18, 0.08), (0.12, 0.3), (0.45, 0.48), (0.85, 0.65), (0.85, 0.9), (0.45, 1), (0.08, 0.88)]],
    'T': [[(-0.15, 0.03), (1.15, 0)], [(0.5, 0), (0.5, 1)]],
    'U': [[(0.05, 0), (0.08, 0.75), (0.3, 1), (0.7, 1), (0.92, 0.75), (0.95, 0)]],
    'V': [[(0, 0), (0.5, 1), (1, 0)]],
    'W': [[(0, 0), (0.25, 1), (0.5, 0.4), (0.75, 1), (1, 0)]],
    'Y': [[(0, 0), (0.5, 0.5), (1, 0)], [(0.5, 0.5), (0.5, 1)]],
    'Z': [[(0.05, 0), (0.95, 0), (0.05, 1), (0.95, 1)]],
    '!': [[(0.5, 0), (0.5, 0.68)], [(0.5, 0.9), (0.52, 1)]],
    '?': [[(0.15, 0.2), (0.4, 0), (0.75, 0.05), (0.85, 0.3), (0.5, 0.55), (0.5, 0.72)], [(0.5, 0.9), (0.52, 1)]],
    "'": [[(0.5, 0), (0.42, 0.28)]],
    '-': [[(0.15, 0.55), (0.85, 0.5)]],
    '0': [[(0.5, 0), (0.15, 0.15), (0.1, 0.5), (0.2, 0.88), (0.5, 1), (0.8, 0.88), (0.9, 0.5), (0.8, 0.12), (0.5, 0)]],
    '1': [[(0.2, 0.22), (0.55, 0), (0.55, 1)]],
    '2': [[(0.1, 0.2), (0.4, 0), (0.8, 0.1), (0.85, 0.35), (0.1, 1), (0.95, 1)]],
    '3': [[(0.1, 0.1), (0.5, 0), (0.85, 0.15), (0.8, 0.38), (0.45, 0.5), (0.85, 0.62), (0.9, 0.85), (0.5, 1), (0.1, 0.9)]],
    '4': [[(0.7, 1), (0.7, 0), (0.05, 0.7), (0.95, 0.7)]],
    '5': [[(0.85, 0), (0.2, 0), (0.15, 0.45), (0.55, 0.4), (0.85, 0.6), (0.8, 0.9), (0.45, 1), (0.1, 0.9)]],
    '6': [[(0.8, 0.05), (0.4, 0.1), (0.1, 0.55), (0.2, 0.95), (0.65, 0.95), (0.8, 0.7), (0.5, 0.5), (0.15, 0.65)]],
    '7': [[(0.05, 0.02), (0.95, 0), (0.4, 1)]],
    '8': [[(0.5, 0.5), (0.15, 0.3), (0.25, 0.05), (0.5, 0), (0.75, 0.05), (0.85, 0.3), (0.5, 0.5), (0.15, 0.72), (0.25, 0.95),
           (0.5, 1), (0.75, 0.95), (0.85, 0.72), (0.5, 0.5)]],
    '9': [[(0.85, 0.35), (0.6, 0.05), (0.2, 0.1), (0.15, 0.4), (0.5, 0.5), (0.85, 0.3), (0.8, 0.7), (0.5, 1)]],
}
STRETTE = set("I1!'-")


def scrivi(colore, testo, x, y, alt, larg=14.0, press=1.1, spazio=0.32, specchia=(), salti=0.12, cresce=0.0):
    """Scrive in stampatello: lettere di misura un po' diversa, storte, che salgono o scendono; `specchia` sono gli
    indici delle lettere scritte al contrario (la S girata dei bambini). Restituisce dove finisce la scritta."""
    rng = rnd()
    st = strato(colore)
    cx = x
    for i, ch in enumerate(testo):
        if ch == ' ':
            cx += alt * 0.6
            continue
        a = alt * (1 + rng.uniform(-salti, salti)) * (1 + cresce * i)
        w = a * (0.62 if ch not in 'MW' else 0.9) * (0.3 if ch in STRETTE else 1.0)
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
    return cx


def fumetto(testo, x, y, alt, colore='nero', verso=(-1, 1), bordo='nero'):
    """Una nuvoletta coi bordi a onda attorno alla scritta, con la punta verso chi parla (verso: da che parte)."""
    rng = rnd()
    larg_t = sum(alt * (0.6 if c == ' ' else 0.62 * (0.3 if c in STRETTE else 1.0) + 0.32 * alt / alt) for c in testo)
    larg_t = len(testo) * alt * 0.86
    bx, by = x - alt * 0.5, y - alt * 1.05
    bw, bh = larg_t + alt * 0.8, alt * 2.1
    cx, cy = bx + bw / 2, by + bh / 2
    pts = []
    n = 40
    for k in range(n):
        t = 2 * math.pi * k / n
        r = 1.0 + 0.04 * math.sin(t * 9 + rng.uniform(0, 1))
        pts.append((cx + bw / 2 * r * math.cos(t), cy + bh / 2 * r * math.sin(t)))
    contorno(strato(bordo), pts, larg=10, press=1.0)
    # la punta
    px = cx + verso[0] * bw * 0.25
    py = cy + verso[1] * bh * 0.45
    tratto(strato(bordo), [(px - 20, py), (px + verso[0] * 70, py + verso[1] * 80), (px + 25, py + 4)], 10, 1.0)
    scrivi(colore, testo, x, y, alt, larg=max(9, alt * 0.17), press=1.25)
    return (px + verso[0] * 70, py + verso[1] * 80)


def stella(st, cx, cy, r, press=1.0):
    pts = []
    for k in range(6):
        a = -math.pi / 2 + k * 4 * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    tratto(st, pts, 11, press, trema=0.4)


def sole(cx, cy, r, raggi=12, faccia=True):
    tondo('giallo', cx, cy, r, press=1.1, bordo='arancione')
    st = strato('arancione')
    for k in range(raggi):
        a = 2 * math.pi * k / raggi + rnd().uniform(-0.06, 0.06)
        tratto(st, [(cx + (r + 18) * math.cos(a), cy + (r + 18) * math.sin(a)), (cx + (r + 70) * math.cos(a), cy + (r + 70) * math.sin(a))],
               14, 1.1, trema=0.3)
    if faccia:
        n = strato('nero')
        for sx in (-1, 1):
            tratto(n, cerchio(cx + sx * r * 0.33, cy - r * 0.12, r * 0.07, n=10), 8, 1.1)
        tratto(n, [(cx + r * 0.45 * math.cos(a), cy + r * 0.1 + r * 0.35 * math.sin(a)) for a in np.linspace(0.3, math.pi - 0.3, 10)], 8, 1.0)


def nuvola(cx, cy, s=1.0, colore='azzurro'):
    pts = []
    gobbe = [(-1.0, 0.1, 0.45), (-0.5, -0.25, 0.55), (0.1, -0.35, 0.6), (0.65, -0.15, 0.5), (1.0, 0.15, 0.4)]
    for gx, gy, gr in gobbe:
        for a in np.linspace(math.pi * 0.95, math.pi * 2.05, 8):
            pts.append((cx + (gx + gr * math.cos(a)) * 120 * s, cy + (gy + gr * math.sin(a)) * 120 * s))
    pts += [(cx + 1.3 * 120 * s, cy + 0.35 * 120 * s), (cx - 1.3 * 120 * s, cy + 0.35 * 120 * s)]
    contorno(strato(colore), pts, larg=11, press=1.0)


def onde(colore, y0, x0=-20, x1=W + 40, passo=58, ampiezza=16, larg=12, evita=None):
    """Una riga di onde a zig-zag; `evita(q)` falso dove non passare (si spezza)."""
    st = strato(colore)
    pts = [(x, y0 + ampiezza * (1 if (i % 2) else -1)) for i, x in enumerate(np.arange(x0, x1, passo))]
    pezzo = []
    for q in pts:
        if evita is None or evita(q):
            pezzo.append(q)
        else:
            if len(pezzo) > 1:
                tratto(st, pezzo, larg, 1.0, trema=0.4)
            pezzo = []
    if len(pezzo) > 1:
        tratto(st, pezzo, larg, 1.0, trema=0.4)


# ───────────────────────── i bambini ─────────────────────────

def mano(cx, cy, aperta=True):
    n = strato('nero')
    tratto(n, cerchio(cx, cy, 13, n=14, giri=1.1), 10, 1.0)
    if aperta:
        for k in range(5):
            a = -math.pi / 2 + (k - 2) * 0.42 + rnd().uniform(-0.1, 0.1)
            tratto(n, [(cx + 12 * math.cos(a), cy + 12 * math.sin(a)), (cx + 30 * math.cos(a), cy + 30 * math.sin(a))], 8, 0.95, trema=0.2)


def faccia(x, cy, r, tipo='sorriso'):
    """Gli occhi, la bocca e le guance. tipo: sorriso, urlo, chiusi, piange, risata, furbo, gonfio (guance piene)."""
    rng = rnd()
    f = strato('nero')
    if tipo in ('chiusi', 'risata', 'furbo'):
        for sx in (-1, 1):
            tratto(f, [(x + sx * r * 0.5, cy - r * 0.02), (x + sx * r * 0.36, cy - r * 0.12), (x + sx * r * 0.22, cy - r * 0.02)], 9, 1.15)
    else:
        for sx in (-1, 1):
            tratto(f, cerchio(x + sx * r * 0.36, cy - r * 0.04, r * 0.08, n=12, giri=1.3), 10, 1.2)
    if tipo in ('urlo', 'risata'):
        bocca = cerchio(x, cy + r * 0.38, r * 0.22, n=18, schiaccia=0.8 if tipo == 'urlo' else 0.55)
        riempi(strato('rosso'), maschera_cerchio(x, cy + r * 0.38, r * 0.2, 0.8 if tipo == 'urlo' else 0.55), angolo=0, passo=7, press=1.0, fuori=2)
        contorno(f, bocca, larg=10, press=1.1)
    elif tipo == 'piange':
        tratto(f, [(x + r * 0.32 * math.cos(a), cy + r * 0.48 - r * 0.2 * math.sin(a)) for a in np.linspace(0.3, math.pi - 0.3, 10)], 9, 1.0)
        lac = strato('azzurro')
        for sx in (-1, 1):
            tratto(lac, [(x + sx * r * 0.4, cy + r * 0.08), (x + sx * r * 0.44, cy + r * 0.3), (x + sx * r * 0.4, cy + r * 0.42)], 11, 1.2)
    elif tipo == 'gonfio':
        tondo('rosa', x - r * 0.45, cy + r * 0.25, r * 0.22, press=0.9, bordo=None)
        tondo('rosa', x + r * 0.45, cy + r * 0.25, r * 0.22, press=0.9, bordo=None)
        tratto(f, cerchio(x, cy + r * 0.35, r * 0.09, n=10), 9, 1.2)
    elif tipo == 'furbo':
        tratto(f, [(x - r * 0.35, cy + r * 0.35), (x + r * 0.1, cy + r * 0.42), (x + r * 0.4, cy + r * 0.25)], 9, 1.1)
    else:
        tratto(f, [(x + r * 0.5 * math.cos(a), cy + r * 0.2 + r * 0.36 * math.sin(a)) for a in np.linspace(0.25, math.pi - 0.25, 12)], 10, 1.1)
    if tipo not in ('gonfio',):
        g = strato('rosa')
        for sx in (-1, 1):
            riempi(g, maschera_cerchio(x + sx * r * 0.6, cy + r * 0.3, r * 0.13), angolo=40, passo=8, press=0.6, fuori=2)


def bambino(x, piedi, alt, maglia='rosso', capelli='marrone', gonna=False, codini=False, espressione='sorriso',
            cancellato=False, berretto=None, mano_sx=None, mano_dx=None, mani_aperte=True, gambe=True, corpo=True,
            braccioli=None, paperella=False, giocattolo=False, biglietti=False, cuffia_fiori=False, occhialini=False,
            cappellino=None, testa_r=None):
    """Un bambino come lo disegna un bambino: la testa tonda grande, il corpo (maglietta o vestito), le braccia a
    bastoncino verso le mani (dei vicini o dove servono), le mani a raggiera, le gambe, le scarpe. Le cose del parco
    (i braccioli di Molly, il salvagente a paperella di Gulpy, il giocattolo di Hatch, i biglietti di Robin, la cuffia a
    fiori di Lampy, gli occhialini neri di Fangy) e il berretto o il cappellino della festa. Restituisce le due mani e il
    centro della testa."""
    rng = rnd()
    r = testa_r or alt * 0.17
    cy = piedi - alt + r
    corpo_top = cy + r * 0.95
    corpo_bot = piedi - alt * 0.33
    nero = strato('nero')
    # la testa
    riempi(strato('pesca'), maschera_cerchio(x, cy, r * 0.96), angolo=rng.uniform(-30, 30), passo=12, press=0.55, fuori=4)
    contorno(nero, cerchio(x, cy, r, giri=1.06), larg=13, press=1.0)
    if cuffia_fiori:
        # la cuffia da piscina rosa coi fiori, tirata su tutta la testa
        cupola = [(x + r * 1.05 * math.cos(a), cy - r * 0.05 + r * 1.0 * math.sin(a)) for a in np.linspace(math.pi * 0.95, math.pi * 2.05, 22)]
        riempi(strato('rosa'), maschera_poligono(cupola), angolo=20, passo=9, press=1.05, fuori=3)
        contorno(nero, cupola, larg=11, press=1.0, chiudi=False)
        for k in range(4):
            fx, fy = x + rng.uniform(-0.6, 0.6) * r, cy - r * rng.uniform(0.35, 0.8)
            for j in range(5):
                a = 2 * math.pi * j / 5
                tondo('bianco', fx + 12 * math.cos(a), fy + 12 * math.sin(a), 8, press=1.3, bordo=None)
            tondo('giallo', fx, fy, 6, press=1.3, bordo=None)
    else:
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
        base = cy - r * 0.32
        cupola = [(x + r * 1.0 * math.cos(a), base + r * 0.78 * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 20)]
        riempi(strato(berretto), maschera_poligono(cupola), angolo=10, passo=10, press=0.95, fuori=3)
        contorno(nero, cupola + [cupola[0]], larg=12, press=1.0, chiudi=False)
        visiera = [(x + r * 0.3, base - r * 0.06), (x + r * 1.6, base + r * 0.02), (x + r * 1.55, base + r * 0.2), (x + r * 0.35, base + r * 0.12)]
        riempi(strato(berretto), maschera_poligono(visiera), angolo=0, passo=9, press=1.05, fuori=2)
        contorno(nero, visiera, larg=11, press=1.0)
    if cappellino:
        # il cappellino a cono della festa, storto, col pompon
        inc = rng.uniform(-0.25, 0.25)
        bx0, bx1 = x - r * 0.55, x + r * 0.55
        punta = (x + math.sin(inc) * r * 1.4, cy - r * 0.75 - r * 1.3)
        cono = [(bx0, cy - r * 0.72), (punta[0], punta[1]), (bx1, cy - r * 0.78)]
        riempi(strato(cappellino), maschera_poligono(cono), angolo=70, passo=9, press=1.0, fuori=3)
        contorno(nero, cono, larg=10, press=1.0)
        tondo('giallo', punta[0], punta[1] - 10, 16, press=1.1, bordo=None)
    if occhialini:
        # gli occhialini da piscina con le lenti dipinte di nero, e l'elastico
        for sx in (-1, 1):
            tondo('nero', x + sx * r * 0.36, cy - r * 0.04, r * 0.24, press=1.8, bordo=None)
        tratto(strato('blu'), [(x - r * 1.0, cy - r * 0.1), (x - r * 0.6, cy - r * 0.06)], 9, 1.1)
        tratto(strato('blu'), [(x + r * 0.6, cy - r * 0.06), (x + r * 1.0, cy - r * 0.1)], 9, 1.1)
        tratto(nero, [(x - r * 0.13, cy - r * 0.06), (x + r * 0.13, cy - r * 0.06)], 8, 1.1)
        bocca_tipo = espressione
        if bocca_tipo == 'urlo':
            bocca = cerchio(x, cy + r * 0.42, r * 0.22, n=18, schiaccia=0.8)
            riempi(strato('rosso'), maschera_cerchio(x, cy + r * 0.42, r * 0.2, 0.8), angolo=0, passo=7, press=1.0, fuori=2)
            contorno(nero, bocca, larg=10, press=1.1)
        else:
            tratto(nero, [(x + r * 0.45 * math.cos(a), cy + r * 0.25 + r * 0.3 * math.sin(a)) for a in np.linspace(0.3, math.pi - 0.3, 10)], 9, 1.0)
    else:
        faccia(x, cy, r, espressione)
    if cancellato:
        # poi qualcuno l'ha cancellata: uno scarabocchio nero calcato, a giri e a zig-zag, che lascia intravedere sotto
        # la faccia di prima
        sc = strato('nero')
        n = 90
        t = np.linspace(0, 2 * math.pi * rng.uniform(3.2, 4.2), n)
        rr = r * (0.45 + 0.6 * rng.random(n) ** 0.6)
        jit = gaussian_filter(rng.standard_normal(n), 1.5) * r * 0.1
        pts = np.stack([x + (rr + jit) * np.cos(t + rng.uniform(0, 6)) + rng.uniform(-6, 6),
                        cy + (rr - jit) * 0.9 * np.sin(t * rng.uniform(0.95, 1.05)) + rng.uniform(-6, 6)], 1)
        tratto(sc, pts, 8, 1.15, trema=0.35, rastremato=False)
        zz = []
        for k in range(7):
            yk = cy - r * 0.75 + k * r * 0.26
            half = r * math.sqrt(max(0.05, 1 - ((yk - cy) / (r * 1.05)) ** 2)) * 1.1
            zz.append((x - half + rng.uniform(-10, 10), yk) if k % 2 == 0 else (x + half + rng.uniform(-10, 10), yk))
        tratto(sc, zz, 9, 1.3, trema=0.25, rastremato=False)
    spalle = r * 1.05
    if corpo:
        if gonna:
            sagoma = [(x - spalle * 0.55, corpo_top), (x + spalle * 0.55, corpo_top), (x + spalle * 1.15, corpo_bot), (x - spalle * 1.15, corpo_bot)]
        else:
            sagoma = [(x - spalle, corpo_top), (x + spalle, corpo_top), (x + spalle * 0.95, corpo_bot), (x - spalle * 0.95, corpo_bot)]
        riempi(strato(maglia), maschera_poligono(sagoma), angolo=rng.uniform(60, 120), passo=13, press=0.7, fuori=9)
        contorno(nero, sagoma, larg=13, press=1.0)
        if paperella:
            # il salvagente a paperella attorno alla pancia, con la testa della paperella davanti
            py = corpo_bot - (corpo_bot - corpo_top) * 0.25
            ciambella = cerchio(x, py, spalle * 1.45, n=40, schiaccia=0.32)
            riempi(strato('giallo'), maschera_cerchio(x, py, spalle * 1.45, 0.32) & ~maschera_cerchio(x, py - 6, spalle * 0.95, 0.22),
                   angolo=0, passo=9, press=1.1, fuori=3)
            contorno(nero, ciambella, larg=11, press=1.0)
            hx, hy = x - spalle * 1.25, py - spalle * 0.45
            tondo('giallo', hx, hy, spalle * 0.33, press=1.1)
            becco = [(hx - spalle * 0.3, hy), (hx - spalle * 0.62, hy + spalle * 0.06), (hx - spalle * 0.3, hy + spalle * 0.14)]
            colora('arancione', becco, press=1.1, larg_bordo=8)
            tratto(nero, cerchio(hx - spalle * 0.08, hy - spalle * 0.08, 5, n=8), 7, 1.2)
    if gambe:
        for sx in (-1, 1):
            gx = x + sx * spalle * 0.42
            tratto(nero, [(gx, corpo_bot), (gx + sx * 6, piedi - 14)], 13, 1.05)
            sp = [(gx + sx * 6 + dx, piedi - 8 + dy) for dx, dy in [(-22, -10), (26 * sx + 4, -12), (30 * sx, 6), (-20, 8)]]
            riempi(strato('marrone' if not gonna else 'rosso'), maschera_poligono(sp), angolo=0, passo=8, press=0.9, fuori=2)
    mani = []
    for sx, dest in ((-1, mano_sx), (1, mano_dx)):
        sp = (x + sx * spalle * 0.92, corpo_top + 18)
        if dest is None:
            dest = (x + sx * spalle * 1.9, corpo_top + alt * 0.28)
        gomito = ((sp[0] + dest[0]) / 2 + sx * 6, (sp[1] + dest[1]) / 2 + 10)
        tratto(nero, [sp, gomito, dest], 12, 1.0)
        mani.append(dest)
        if braccioli:
            # i braccioli gonfiabili a metà braccio
            bx, by = (sp[0] + gomito[0]) / 2, (sp[1] + gomito[1]) / 2
            tondo(braccioli, bx, by, r * 0.3, press=1.15, schiaccia=0.8)
        if biglietti:
            # la striscia dei biglietti della sala giochi avvolta attorno al braccio
            st = strato('arancione')
            for k in range(5):
                u = 0.15 + 0.17 * k
                px, py = sp[0] + (dest[0] - sp[0]) * u, sp[1] + (dest[1] - sp[1]) * u
                tratto(st, [(px - 18, py - 14), (px + 18, py + 10)], 16, 1.2, trema=0.2)
    for (mx, my) in mani:
        mano(mx, my, mani_aperte)
    if giocattolo:
        # il giocattolo luminoso del negozio del parco, appeso a un filo dalla mano destra, coi raggi
        mx, my = mani[1]
        tratto(nero, [(mx, my + 10), (mx + 4, my + 70)], 6, 0.9)
        tondo('giallo', mx + 4, my + 92, 24, press=1.3, bordo='arancione')
        g = strato('giallo')
        for k in range(8):
            a = 2 * math.pi * k / 8
            tratto(g, [(mx + 4 + 34 * math.cos(a), my + 92 + 34 * math.sin(a)), (mx + 4 + 56 * math.cos(a), my + 92 + 56 * math.sin(a))], 8, 1.1, trema=0.2)
    return mani, (x, cy, r)


# ───────────────────────── i posti del parco ─────────────────────────

def ruota(cx, cy, r):
    """La ruota panoramica: il cerchio, i raggi, le cabine colorate, le due gambe."""
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
        colora(cols[k], [(px - 24, py - 18), (px + 24, py - 18), (px + 20, py + 20), (px - 20, py + 20)], press=1.0, passo=8, larg_bordo=8)


def scivoli(cx, base, alt, largo=112, tunnel=False):
    """La torre degli scivoli: il palo, il tetto rosso a punta, i tubi colorati che girano attorno; con tunnel=True in
    basso la bocca nera del tubo. Restituisce il centro della bocca."""
    nero = strato('nero')
    tratto(nero, [(cx - 30, base), (cx - 26, base - alt)], 12, 1.0)
    tratto(nero, [(cx + 30, base), (cx + 28, base - alt)], 12, 1.0)
    colora('rosso', [(cx - 85, base - alt), (cx, base - alt - 140), (cx + 85, base - alt)], press=1.05, angolo=70, passo=10)
    cols = ['giallo', 'verde', 'rosso', 'azzurro', 'arancione']
    for k in range(5):
        y0 = base - alt + 60 + k * (alt - 90) / 5
        t = np.linspace(-0.2, math.pi + 0.2, 20)
        pts = [(cx + largo * math.cos(tt) * (1 if k % 2 else -1), y0 + largo * 0.46 * math.sin(tt)) for tt in t]
        tratto(strato(cols[k]), pts, 30, 1.05, trema=0.5)
    if tunnel:
        bx, by = cx + largo + 40, base - 60
        tratto(strato('arancione'), [(cx + largo * 0.6, base - 150), (bx - 20, by - 30), (bx + 30, by)], 60, 1.1, trema=0.3)
        tondo('nero', bx + 40, by + 4, 58, press=1.6, schiaccia=1.0, bordo='arancione', larg_bordo=16)
        return (bx + 40, by + 4)
    return None


def piscina(x0, y0, x1, y1, superficie=None):
    """La vasca: l'azzurro dentro, il bordo di piastrelle, le righe dell'acqua; superficie: la riga dell'acqua (vista
    di lato) se c'è."""
    riempi(strato('azzurro'), maschera_poligono([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), angolo=0, passo=15, press=0.9, larg=24, fuori=6, buchi=0.04)
    contorno(strato('blu'), [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], larg=16, press=1.1)
    for k in range(int((x1 - x0) / 70)):
        px = x0 + 35 + k * 70
        tratto(strato('blu'), [(px, y0 - 8), (px, y0 + 8)], 7, 0.9, trema=0.2)


# ───────────────────────── i disegni ─────────────────────────

def d_ricordo():
    foglio(7, 'album')
    ys = np.arange(H)[:, None]
    xs = np.arange(W)[None, :]
    rng = rnd()
    # il cielo della sera: una striscia blu notte calcata in alto, che scende a strappi; le stelle e la luna gialle
    cielo = strato('blu_notte')
    bordo = 470 + 60 * np.sin(xs / 210.0 + 1.3) + 35 * np.sin(xs / 77.0)
    m_cielo = (ys < bordo)
    riempi(cielo, m_cielo, angolo=-8, passo=15, press=0.95, larg=24, fuori=25, buchi=0.03)
    riempi(cielo, m_cielo & (ys < bordo - 120), angolo=12, passo=19, press=0.6, larg=22, fuori=20, buchi=0.1)
    gialli = strato('giallo')
    for (sx, sy, sr) in [(170, 100, 46), (420, 250, 38), (690, 80, 34), (1600, 130, 40), (1880, 330, 40), (2280, 300, 36),
                         (1180, 60, 30), (900, 300, 28), (2240, 60, 32), (320, 400, 30), (1450, 330, 26)]:
        stella(gialli, sx + rng.uniform(-15, 15), sy + rng.uniform(-10, 10), sr, press=1.25)
    lx, ly, lr = 2030, 170, 115
    est = [(lx + lr * math.cos(a), ly + lr * math.sin(a)) for a in np.linspace(math.radians(65), math.radians(295), 30)]
    c2x, c2y, r2 = lx + 58, ly - 8, lr * 0.86
    inn = [(c2x + r2 * math.cos(a), c2y + r2 * math.sin(a)) for a in np.linspace(math.radians(307), math.radians(53), 30)]
    falce = est + inn
    riempi(gialli, maschera_poligono(falce), angolo=45, passo=8, press=1.35, fuori=3)
    contorno(strato('arancione'), falce, larg=10, press=1.05)
    # ai lati dell'ingresso: la ruota panoramica e gli scivoli
    ruota(300, 760, 190)
    scivoli(2265, 1300, 640)
    # l'ingresso: i piloni rosa, la trave gialla con SPLASHLAND, la raggiera sopra
    nero = strato('nero')
    for (a, b) in [(560, 680), (1840, 1960)]:
        colora('rosa', [(a, 560), (b, 560 + rng.uniform(-6, 6)), (b + 6, 1300), (a - 4, 1300)], press=0.9, angolo=80, larg_bordo=14)
    colora('giallo', [(500, 450), (2020, 438), (2025, 570), (495, 582)], press=0.85, angolo=5, larg_bordo=14)
    rx, ry, rr = 1260, 440, 230
    riempi(strato('arancione'), maschera_cerchio(rx, ry, rr * 0.55) & (ys < ry), angolo=30, passo=10, press=1.1, fuori=4)
    for k in range(11):
        a = math.pi + (k + 0.5) * math.pi / 11
        tratto(strato('rosso' if k % 2 else 'arancione'), [(rx + rr * 0.62 * math.cos(a), ry + rr * 0.62 * math.sin(a)),
                                                            (rx + rr * 1.05 * math.cos(a), ry + rr * 1.05 * math.sin(a))], 20, 1.15)
    contorno(nero, [(rx + rr * 0.56 * math.cos(a), ry + rr * 0.56 * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 24)],
             larg=12, press=1.0, chiudi=False)
    scrivi('blu', 'SPLASHLAND', 620, 512, 92, larg=17, press=1.35, spazio=0.4, specchia=(4,))
    filo = [(680 + (1840 - 680) * t, 610 + 60 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 30)]
    tratto(nero, filo, 7, 0.75)
    cols = ['rosso', 'giallo', 'verde', 'azzurro', 'arancione', 'rosa']
    for j, t in enumerate(np.linspace(0.05, 0.95, 14)):
        px, py = 680 + (1840 - 680) * t, 610 + 60 * math.sin(math.pi * t) + 20
        riempi(strato(cols[j % len(cols)]), maschera_cerchio(px, py, 17), angolo=rng.uniform(0, 90), passo=7, press=1.2, fuori=2)
    contorno(strato('rosso'), [(770, 690), (1750, 682), (1738, 800), (782, 808)], larg=13, press=1.0)
    for (ax, ay) in [(770, 690), (1750, 682)]:
        tratto(nero, [(ax, ay), (ax + rng.uniform(-30, -10) if ax < 1000 else ax + rng.uniform(10, 30), 640)], 8, 0.9)
    scrivi('rosso', 'NIGHT SPLASH', 830, 748, 78, larg=15, press=1.3, spazio=0.36, cresce=-0.01)
    # il prato e il lago
    prato = (ys > 1300 + 18 * np.sin(xs / 150.0)) & (ys < 1420)
    verde = strato('verde')
    riempi(verde, prato, angolo=-5, passo=14, press=0.8, larg=22, fuori=14, buchi=0.06)
    for k in range(80):
        gx = rng.uniform(20, W - 20)
        tratto(verde, [(gx, 1325), (gx + rng.uniform(-14, 14), 1268)], 9, 0.95, trema=0.2)
    lago_top = 1440
    mx, my = 1420, 1700
    gobbe = []
    for ax in np.linspace(-1, 1, 40):
        gobbe.append((mx + ax * 620, my - 230 * math.sqrt(max(0.0, 1 - ax * ax)) - 30 * math.sin(ax * 9.0) ** 2 + rng.uniform(-6, 6)))
    m_sag = maschera_poligono(gobbe + [(mx + 640, H + 40), (mx - 640, H + 40)]) & (ys > lago_top + 30)
    occ_x, occ_y, occ_r = mx - 260, my - 130, 92
    occhio = maschera_cerchio(occ_x, occ_y, occ_r, 0.78)
    riempi(strato('azzurro'), (ys > lago_top + 6 * np.sin(xs / 90.0)) & ~occhio, angolo=0, passo=15, press=0.85, larg=24, fuori=10, buchi=0.05)
    ombra = strato('blu_notte')
    riempi(ombra, m_sag & ~occhio, angolo=15, passo=10, press=1.35, larg=22, fuori=5, buchi=0.01)
    riempi(ombra, m_sag & ~occhio, angolo=-35, passo=14, press=1.0, larg=20, fuori=3, buchi=0.03)
    contorno(strato('nero'), gobbe, larg=12, press=1.1, chiudi=False)
    contorno(strato('nero'), cerchio(occ_x, occ_y, occ_r + 4, schiaccia=0.78), larg=13, press=1.4)
    riempi(strato('giallo'), maschera_cerchio(occ_x + 12, occ_y + 6, 42, 0.95), angolo=20, passo=7, press=1.1, fuori=1)
    pupilla = strato('nero')
    riempi(pupilla, maschera_cerchio(occ_x + 15, occ_y + 8, 21, 1.0), angolo=0, passo=5, press=2.0, fuori=1)
    for k in range(7):
        a = math.pi * (1.15 + 0.7 * k / 6)
        tratto(pupilla, [(occ_x + (occ_r + 4) * math.cos(a), occ_y + (occ_r + 4) * 0.78 * math.sin(a)),
                         (occ_x + (occ_r + 34) * math.cos(a), occ_y + (occ_r + 34) * 0.78 * math.sin(a))], 8, 1.2, trema=0.2)
    denti, bordi = strato('bianco'), strato('nero')
    for k in range(9):
        u = (k + 0.5) / 9
        bx, by = mx - 120 + 520 * u, my - 105 + 25 * math.sin(u * 3.0)
        tri = [(bx - 19, by), (bx, by + 34), (bx + 19, by)]
        riempi(denti, maschera_poligono(tri), angolo=80, passo=6, press=1.5, fuori=1)
        tratto(bordi, tri, 7, 1.1, trema=0.15)
    tratto(bordi, [(mx - 120 + 520 * u, my - 105 + 25 * math.sin(u * 3.0)) for u in np.linspace(0, 1, 16)], 11, 1.3)
    fuori_occhio = lambda q: ((q[0] - occ_x) / (occ_r + 45)) ** 2 + ((q[1] - occ_y) / ((occ_r + 45) * 0.78)) ** 2 > 1.0  # noqa: E731
    for riga in range(5):
        onde('blu', lago_top + 34 + riga * 52, evita=fuori_occhio)
    # i quattro bambini per mano: Molly coi braccioli, Gulpy col salvagente a paperella, Hatch col giocattolo che brilla
    # (le facce cancellate), e tu
    piedi, alt = 1335, 480
    xs_b = [770, 1100, 1430, 1770]
    by = piedi - alt * 0.55
    mani_tra = [((xs_b[i] + xs_b[i + 1]) / 2 + rng.uniform(-8, 8), by + rng.uniform(-12, 12)) for i in range(3)]
    bambino(xs_b[0], piedi, alt * 0.97, 'rosso', 'marrone', gonna=True, codini=True, cancellato=True, mano_dx=mani_tra[0], braccioli='arancione')
    bambino(xs_b[1], piedi + 6, alt * 1.03, 'verde', 'nero', cancellato=True, mano_sx=mani_tra[0], mano_dx=mani_tra[1], paperella=True)
    bambino(xs_b[2], piedi - 4, alt * 0.95, 'viola', 'giallo', cancellato=True, mano_sx=mani_tra[1], mano_dx=mani_tra[2], giocattolo=True)
    mani, _ = bambino(xs_b[3], piedi + 2, alt * 1.0, 'azzurro', 'marrone', berretto='giallo', mano_sx=mani_tra[2], mano_dx=(xs_b[3] + 110, by - 30))
    canna(mani[1], alt)
    # la data della Night Splash (il braccialetto: 14·08·1997)
    scrivi('nero', '14-8-97', 80, 1378, 66, larg=11, press=1.2, spazio=0.32)


def canna(mano_pos, alt):
    """La canna giocattolo (marrone), il filo e il pesciolino arancione."""
    nero = strato('nero')
    mx, my = mano_pos
    cima = (mx + alt * 0.36, my - alt * 0.86)
    tratto(strato('marrone'), [(mx - 30, my + 26), cima], 15, 1.1)
    filo_fine = (cima[0] + 8, cima[1] + alt * 0.55)
    tratto(nero, [cima, (cima[0] + 6, cima[1] + alt * 0.3), filo_fine], 6, 0.8)
    px, py = filo_fine[0], filo_fine[1] + 30
    riempi(strato('arancione'), maschera_cerchio(px, py, 30, 0.55), angolo=0, passo=8, press=0.95, fuori=3)
    coda = [(px + 26, py), (px + 52, py - 18), (px + 50, py + 18)]
    riempi(strato('arancione'), maschera_poligono(coda), angolo=90, passo=8, press=0.95, fuori=3)
    contorno(nero, cerchio(px, py, 30, n=24, schiaccia=0.55), larg=9, press=1.0)
    contorno(nero, coda, larg=9, press=1.0)
    tratto(nero, cerchio(px - 14, py - 4, 4, n=8), 7, 1.2)


def panino(cx, cy, s=1.0):
    """Il panino gigante: pane, insalata, pomodoro, formaggio, pane."""
    w = 230 * s
    strati_p = [('marrone', 0.0, 34), ('giallo', 34, 18), ('rosso', 52, 20), ('verde_chiaro', 72, 18), ('marrone', 90, 40)]
    y = cy - 65 * s
    for colore, dy, hh in strati_p[::-1]:
        y0 = cy - 65 * s + dy * s
        pts = [(cx - w / 2 + 6, y0), (cx + w / 2 - 6, y0 - 4), (cx + w / 2, y0 + hh * s), (cx - w / 2, y0 + hh * s + 3)]
        if colore == 'marrone' and dy == 0.0:
            pts = [(cx + w / 2 * math.cos(a), y0 + 34 * s - 50 * s * math.sin(a)) for a in np.linspace(0, math.pi, 14)]
        colora(colore, pts, press=1.0, passo=9, larg_bordo=9)
    # i semini sul pane
    for k in range(8):
        tondo('bianco', cx + rnd().uniform(-0.35, 0.35) * w, cy - 45 * s + rnd().uniform(-12, 12), 5, press=1.3, bordo=None)


def d_piscina():
    """Notte 1: alla piscina di Splashland, di giorno. Gulpy allo Snack Shack col panino gigante, Molly sul trampolino
    coi braccioli, gli occhi di Hatch nel tunnel dello scivolo col suo giocattolo che brilla."""
    foglio(11, 'album')
    rng = rnd()
    ys = np.arange(H)[:, None]
    xs = np.arange(W)[None, :]
    cielo = (ys < 330 + 40 * np.sin(xs / 190.0) + 20 * np.sin(xs / 61.0))
    riempi(strato('azzurro'), cielo, angolo=-6, passo=15, press=0.8, larg=24, fuori=20, buchi=0.05)
    sole(240, 185, 95)
    nuvola(1000, 150, 0.9, 'blu')
    nuvola(1650, 210, 0.75, 'blu')
    # lo scivolo al centro, col tunnel: dentro due occhi e il giocattolo che brilla
    bocca = scivoli(980, 1110, 640, largo=150, tunnel=True)
    bx, by = bocca
    for sx in (-1, 1):
        tondo('bianco', bx + sx * 20, by - 6, 12, press=1.5, bordo=None)
        tondo('nero', bx + sx * 20 + 3, by - 4, 5, press=1.8, bordo=None)
    tondo('giallo', bx + 32, by + 32, 11, press=1.4, bordo=None)
    g = strato('giallo')
    for k in range(8):
        a = 2 * math.pi * k / 8
        tratto(g, [(bx + 32 + 16 * math.cos(a), by + 32 + 16 * math.sin(a)), (bx + 32 + 30 * math.cos(a), by + 32 + 30 * math.sin(a))], 6, 1.1, trema=0.2)
    fumetto('TROVAMI!', bx + 120, by - 180, 46, verso=(-1, 1))
    # la vasca, davanti
    riempi(strato('azzurro'), maschera_poligono([(380, 1210), (1750, 1195), (1765, 1560), (370, 1575)]), angolo=0, passo=15, press=0.95, larg=24, fuori=6, buchi=0.04)
    contorno(strato('blu'), [(380, 1210), (1750, 1195), (1765, 1560), (370, 1575)], larg=16, press=1.1)
    for riga in range(4):
        onde('blu', 1270 + riga * 75, x0=420, x1=1720, passo=52, ampiezza=12, larg=10)
    # il trampolino a sinistra: la scaletta e l'asse sopra l'acqua; Molly in punta coi braccioli
    nero = strato('nero')
    for lx in (150, 250):
        tratto(nero, [(lx, 1590), (lx + 6, 860)], 13, 1.05)
    for k in range(9):
        yk = 1530 - k * 80
        tratto(nero, [(150, yk), (252, yk - 3)], 10, 1.0)
    colora('rosso', [(240, 840), (760, 870), (758, 905), (238, 880)], press=1.0, angolo=4, passo=9, larg_bordo=11)
    _, testa = bambino(660, 862, 400, 'giallo', 'marrone', gonna=True, codini=True, espressione='urlo', braccioli='arancione',
                       mano_sx=(560, 600), mano_dx=(780, 590))
    fumetto('GUARDAMI!', 500, 330, 58, verso=(1, 1))
    # lo Snack Shack a destra: il chiosco, la tenda a strisce, l'insegna; Gulpy davanti col panino gigante
    colora('giallo', [(1840, 820), (2300, 805), (2305, 1290), (1845, 1300)], press=0.75, angolo=80, larg_bordo=14)
    colora('marrone', [(1880, 1010), (2260, 1000), (2262, 1060), (1882, 1070)], press=0.9, angolo=0, passo=9, larg_bordo=11)
    for k in range(6):
        x0 = 1800 + k * 90
        colora('rosso' if k % 2 == 0 else 'bianco', [(x0, 700), (x0 + 90, 700), (x0 + 95, 820), (x0 - 4, 825)], press=1.05, angolo=90, passo=9, larg_bordo=10)
    scrivi('rosso', 'SNACK', 1900, 640, 80, larg=15, press=1.3)
    for k in range(4):
        tondo(['rosso', 'verde', 'arancione', 'viola'][k], 1920 + k * 95, 930, 26, press=1.0)
    mani, testa = bambino(1990, 1580, 480, 'verde', 'nero', espressione='urlo', mano_sx=(1865, 1400), mano_dx=(2115, 1400))
    panino(1990, 1420, 1.0)
    fumetto('HO FAME!', 1480, 1075, 52, verso=(1, 1))
    # il prato in basso e la data
    prato = (ys > 1600 + 14 * np.sin(xs / 140.0))
    riempi(strato('verde'), prato, angolo=-4, passo=14, press=0.75, larg=22, fuori=10, buchi=0.06)
    scrivi('nero', 'AGOSTO 97', 1830, 1645, 52, larg=10, press=1.2, spazio=0.3)


def d_tesoro():
    """Notte 2: Robin sotto gli scivoli, col mucchio delle cose prese agli altri bambini e i biglietti della sala
    giochi attorno alle braccia; da destra la torcia di un grande lo becca in faccia. «IL MIO TESORO»."""
    foglio(23, 'quadretti')
    rng = rnd()
    ys = np.arange(H)[:, None]
    xs = np.arange(W)[None, :]
    # la sera: il cielo viola e blu, poche stelle
    cielo = (ys < 300 + 30 * np.sin(xs / 170.0))
    riempi(strato('viola'), cielo, angolo=-5, passo=16, press=0.85, larg=24, fuori=20, buchi=0.05)
    for (sx, sy) in [(300, 90), (760, 160), (1300, 70), (1900, 140), (2250, 230)]:
        stella(strato('giallo'), sx, sy, 32, press=1.2)
    # la torre degli scivoli: le quattro gambe lunghe, la piattaforma, i tubi che girano in alto, il tetto rosso; sotto,
    # fra le gambe, il buio dove nasconde le cose
    nero = strato('nero')
    for (x0, x1) in [(560, 600), (700, 712), (930, 918), (1060, 1020)]:
        tratto(nero, [(x0, 1530), (x1, 980)], 14, 1.05)
    colora('marrone', [(560, 960), (1080, 950), (1085, 1000), (556, 1010)], press=1.0, angolo=0, passo=9, larg_bordo=12)
    for (x0, x1) in [(700, 712), (930, 918)]:
        tratto(nero, [(x1, 960), (x1 + 4, 380)], 13, 1.0)
    colora('rosso', [(690, 380), (816, 230), (942, 378)], press=1.05, angolo=70, passo=10)
    cols = ['giallo', 'verde', 'azzurro', 'arancione']
    for k in range(4):
        y0 = 460 + k * 125
        tt = np.linspace(-0.2, math.pi + 0.2, 20)
        tratto(strato(cols[k]), [(816 + 240 * math.cos(u) * (1 if k % 2 else -1), y0 + 100 * math.sin(u)) for u in tt], 30, 1.05, trema=0.5)
    sotto = [(585, 1530), (600, 1020), (1040, 1015), (1060, 1530)]
    riempi(strato('nero'), maschera_poligono(sotto), angolo=-25, passo=18, press=0.55, larg=22, fuori=4, buchi=0.12)
    # il mucchio: il secchiello con la paletta, il pallone, l'orsetto, gli occhiali da sole, la paperella
    colora('rosso', [(640, 1370), (750, 1370), (735, 1500), (655, 1500)], press=1.15, larg_bordo=10)
    tratto(strato('nero'), [(648, 1372), (695, 1310), (742, 1372)], 8, 1.0)
    tratto(strato('azzurro'), [(760, 1330), (800, 1490)], 12, 1.2)
    tondo('bianco', 860, 1450, 58, press=1.1)
    for k, c in enumerate(['rosso', 'blu', 'giallo']):
        a0 = k * 2.1
        tratto(strato(c), [(860 + 56 * math.cos(a0 + u), 1450 + 56 * math.sin(a0 + u)) for u in np.linspace(0, 1.4, 8)], 16, 1.2)
    tondo('marrone', 975, 1455, 48, press=1.2)
    tondo('marrone', 975, 1385, 36, press=1.2)
    tondo('marrone', 948, 1355, 13, press=1.3)
    tondo('marrone', 1002, 1355, 13, press=1.3)
    tratto(strato('nero'), cerchio(965, 1382, 4, n=8), 6, 1.3)
    tratto(strato('nero'), cerchio(986, 1382, 4, n=8), 6, 1.3)
    tondo('nero', 700, 1290, 22, press=1.6)
    tondo('nero', 756, 1290, 22, press=1.6)
    tratto(strato('nero'), [(722, 1290), (734, 1290)], 7, 1.2)
    tondo('giallo', 900, 1310, 32, press=1.2)
    colora('arancione', [(926, 1305), (958, 1312), (926, 1320)], press=1.2, larg_bordo=7)
    # Robin, in piedi accanto alla torre, coi biglietti attorno alle braccia, gli occhi strizzati
    mani, (hx, hy, hr) = bambino(1300, 1530, 470, 'rosso', 'marrone', espressione='chiusi', biglietti=True,
                                 mano_sx=(1110, 1380), mano_dx=(1440, 1250))
    # il braccio del grande che entra da destra con la torcia, e il fascio giallo largo che gli arriva in faccia
    colora('blu', [(2400, 860), (2090, 880), (2085, 1010), (2400, 1000)], press=0.95, angolo=0, passo=11, larg_bordo=12)
    colora('pesca', [(2085, 885), (1985, 870), (1975, 1010), (2088, 1005)], press=0.85, larg_bordo=11)
    tx, ty = 1990, 940
    colora('grigio', [(tx, ty - 46), (tx - 230, ty - 50), (tx - 232, ty + 48), (tx, ty + 46)], press=1.15, angolo=0, passo=9, larg_bordo=12)
    colora('giallo', [(tx - 232, ty - 60), (tx - 262, ty - 66), (tx - 264, ty + 66), (tx - 232, ty + 60)], press=1.3, angolo=90, passo=7, larg_bordo=10)
    fascio = [(tx - 262, ty - 66), (hx - hr * 1.0, hy - hr * 1.7), (hx - hr * 1.0, hy + hr * 1.9), (tx - 262, ty + 66)]
    riempi(strato('giallo'), maschera_poligono(fascio), angolo=-6, passo=15, press=0.6, larg=22, fuori=6, buchi=0.08)
    for k in range(7):
        a = math.pi * (-0.55 + 0.18 * k)
        tratto(strato('arancione'), [(hx + hr * 1.25 * math.cos(a), hy + hr * 1.25 * math.sin(a)),
                                    (hx + hr * 1.65 * math.cos(a), hy + hr * 1.65 * math.sin(a))], 8, 1.0, trema=0.2)
    # la scritta con la freccia verso il mucchio
    scrivi('rosso', 'IL MIO TESORO', 1180, 560, 80, larg=14, press=1.3)
    tratto(strato('rosso'), [(1300, 650), (1150, 900), (980, 1250)], 12, 1.2)
    tratto(strato('rosso'), [(950, 1175), (975, 1262), (1050, 1225)], 12, 1.2)
    # il prato
    prato = (ys > 1520 + 12 * np.sin(xs / 130.0))
    riempi(strato('verde'), prato, angolo=-4, passo=14, press=0.7, larg=22, fuori=10, buchi=0.08)


def d_compleanno():
    """Notte 3: la festa di compleanno al parco. La torta con le candeline, la festeggiata che piange, gli altri coi
    cappellini, e Archie con la trombetta che le spegne tutte. «TANTI AUGURI»."""
    foglio(37, 'album')
    rng = rnd()
    # i festoni a bandierine e la scritta
    st = strato('nero')
    tratto(st, [(60, 140 + 80 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 30)][0:1] + [(60 + 2280 * t, 140 + 90 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 30)], 7, 0.8)
    cols = ['rosso', 'giallo', 'verde', 'azzurro', 'arancione', 'viola', 'rosa']
    for k, t in enumerate(np.linspace(0.04, 0.96, 16)):
        px, py = 60 + 2280 * t, 140 + 90 * math.sin(math.pi * t)
        colora(cols[k % len(cols)], [(px - 40, py + 2), (px + 40, py + 4), (px + 2, py + 95)], press=1.0, passo=8, larg_bordo=8)
    scrivi('rosso', 'TANTI AUGURI', 620, 430, 120, larg=19, press=1.35, spazio=0.4)
    # i palloncini
    for (bx, by, c) in [(170, 520, 'rosso'), (330, 640, 'azzurro'), (2080, 520, 'giallo'), (2240, 660, 'verde'), (1960, 700, 'viola')]:
        tondo(c, bx, by, 70, press=1.0, schiaccia=1.2)
        tratto(strato('nero'), [(bx, by + 84), (bx + 20, by + 200), (bx - 10, by + 330)], 6, 0.85)
    # i bambini dietro al tavolo: due a sinistra, la festeggiata in mezzo che piange, Archie a destra con la trombetta
    piedi = 1330
    bambino(520, piedi, 520, 'verde', 'giallo', espressione='sorriso', cappellino='azzurro', gambe=False, mano_sx=(380, 900), mano_dx=(640, 1050))
    bambino(820, piedi, 500, 'arancione', 'nero', espressione='sorriso', cappellino='verde', gambe=False, codini=True, gonna=True,
            mano_sx=(700, 1050), mano_dx=(940, 1050))
    bambino(1230, 1065, 560, 'rosa', 'marrone', espressione='piange', cappellino='rosa', gambe=False, gonna=True,
            mano_sx=(1090, 870), mano_dx=(1370, 870))
    mani, (ax, ay, ar) = bambino(1780, piedi, 520, 'blu', 'marrone', espressione='gonfio', cappellino='rosso', gambe=False,
                                 mano_sx=(1640, 1000), mano_dx=(1900, 1080))
    # il tavolo con la tovaglia, davanti a tutti
    colora('azzurro', [(260, 1080), (2140, 1068), (2160, 1200), (240, 1210)], press=0.8, angolo=0, passo=12, larg_bordo=13)
    for lx in (330, 2060):
        tratto(strato('marrone'), [(lx, 1205), (lx + 6, 1560)], 22, 1.1)
    # la torta rosa con la panna che cola, e le sette candeline
    tx, top, base = 1230, 880, 1075
    colora('rosa', [(tx - 240, top), (tx + 240, top - 6), (tx + 246, base), (tx - 244, base + 4)], press=0.95, angolo=85, larg_bordo=13)
    panna = [(tx - 250 + k * 50, top - 2 + (40 if k % 2 else 0)) for k in range(11)]
    tratto(strato('bianco'), panna, 26, 1.4, trema=0.3)
    fiamme = []
    for k in range(7):
        cx = tx - 180 + k * 60
        colora(cols[k % len(cols)], [(cx - 10, top - 110), (cx + 10, top - 112), (cx + 12, top - 6), (cx - 10, top - 4)], press=1.15, angolo=90, passo=6, larg_bordo=7)
        fiamme.append((cx, top - 130))
    # Archie soffia da destra: la trombetta a strisce srotolata fino alle candeline; le fiamme piegate, le ultime spente
    tromba = [(ax - ar * 0.2, ay + ar * 0.45)]
    for k in range(1, 9):
        u = k / 8
        tromba.append((ax - ar * 0.2 - (ax - ar * 0.2 - (tx + 230)) * u, ay + ar * 0.45 + (top - 150 - (ay + ar * 0.45)) * u + 30 * math.sin(u * math.pi)))
    tratto(strato('rosso'), tromba, 30, 1.2)
    for k in range(0, 8, 2):
        p0, p1 = tromba[k], tromba[k + 1]
        tratto(strato('bianco'), [p0, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)], 26, 1.5)
    tratto(strato('verde'), [tromba[-1], (tromba[-1][0] - 50, tromba[-1][1] - 30), (tromba[-1][0] - 80, tromba[-1][1] - 20)], 14, 1.2)
    for k, (fx, fy) in enumerate(fiamme):
        if k >= 4:
            # spenta: il filo di fumo grigio
            tratto(strato('grigio'), [(fx, fy + 18), (fx - 20, fy - 20), (fx + 6, fy - 60), (fx - 18, fy - 100)], 8, 1.0)
        else:
            # la fiammella a goccia, piegata via da Archie (verso sinistra)
            goccia = [(fx + 15 * math.cos(a), fy + 14 + 15 * math.sin(a)) for a in np.linspace(-0.6, math.pi + 0.6, 10)][::-1]
            goccia = [(fx - 48, fy - 26)] + goccia
            colora('arancione', goccia, press=1.2, larg_bordo=6, bordo='rosso')
            tondo('giallo', fx - 4, fy + 10, 7, press=1.3, bordo=None)
    # il pavimento e i regali per terra, coi nastri
    ys = np.arange(H)[:, None]
    riempi(strato('marrone'), ys > 1575, angolo=0, passo=16, press=0.8, larg=22, fuori=8, buchi=0.08)
    for (gx, gy, gw, gh, c, nastro) in [(520, 1575, 230, 190, 'verde', 'rosso'), (800, 1575, 160, 120, 'giallo', 'blu'),
                                         (1560, 1575, 260, 160, 'viola', 'giallo'), (1880, 1575, 170, 230, 'rosso', 'verde')]:
        colora(c, [(gx, gy - gh), (gx + gw, gy - gh - 4), (gx + gw + 4, gy), (gx - 2, gy)], press=1.0, larg_bordo=11)
        tratto(strato(nastro), [(gx + gw / 2, gy - gh - 2), (gx + gw / 2 + 4, gy)], 16, 1.25)
        tratto(strato(nastro), [(gx, gy - gh / 2), (gx + gw, gy - gh / 2 - 3)], 16, 1.25)
        tratto(strato(nastro), cerchio(gx + gw / 2 - 26, gy - gh - 20, 24, n=14, schiaccia=0.6), 10, 1.2)
        tratto(strato(nastro), cerchio(gx + gw / 2 + 26, gy - gh - 20, 24, n=14, schiaccia=0.6), 10, 1.2)


def d_sottacqua():
    """Notte 4: la piscina vista di lato. Sopra, un bambino che si sbraccia; sotto, con la cuffia a fiori, la bambina
    che gli tira le gambe ridendo (Lampy). Le bollicine, «AH AH AH»."""
    foglio(41, 'album')
    rng = rnd()
    ys = np.arange(H)[:, None]
    xs = np.arange(W)[None, :]
    sup = 640 + 22 * np.sin(xs / 120.0)
    riempi(strato('azzurro'), ys < 260 + 30 * np.sin(xs / 200.0), angolo=-5, passo=15, press=0.7, larg=24, fuori=16, buchi=0.06)
    sole(2150, 160, 85)
    # le pareti della vasca a piastrelle, ai lati, e il fondo
    for (a, b) in [(0, 150), (2250, 2400)]:
        riempi(strato('bianco'), maschera_poligono([(a, 560), (b, 560), (b, H), (a, H)]), angolo=0, passo=10, press=0.7, fuori=2)
        for k in range(14):
            tratto(strato('azzurro'), [(a, 600 + k * 80), (b, 600 + k * 80)], 7, 0.9, trema=0.2)
        tratto(strato('azzurro'), [((a + b) / 2, 560), ((a + b) / 2, H)], 7, 0.9, trema=0.2)
    acqua = (ys > sup) & (ys < 1600)
    riempi(strato('azzurro'), acqua, angolo=0, passo=14, press=1.0, larg=24, fuori=4, buchi=0.03)
    riempi(strato('blu'), acqua & (ys > 1100), angolo=10, passo=22, press=0.45, larg=22, fuori=4, buchi=0.15)
    riempi(strato('bianco'), (ys >= 1600), angolo=0, passo=12, press=0.7, fuori=2)
    for k in range(16):
        tratto(strato('azzurro'), [(150 + k * 140, 1600), (150 + k * 140, H)], 7, 0.9, trema=0.2)
    # la scaletta a destra
    for lx in (2120, 2200):
        tratto(strato('grigio'), [(lx, 480), (lx, 1250)], 14, 1.1)
    for k in range(8):
        tratto(strato('grigio'), [(2120, 560 + k * 90), (2200, 560 + k * 90)], 10, 1.0)
    # il bambino in superficie: la testa e le braccia fuori, che si sbraccia; il corpo sotto, verso il basso
    vx = 1120
    mani, (hx, hy, hr) = bambino(vx, 1150, 600, 'giallo', 'nero', espressione='urlo', mano_sx=(930, 380), mano_dx=(1310, 360), gambe=False)
    for sx in (-1, 1):
        gx = vx + sx * 44
        tratto(strato('nero'), [(gx, 952), (gx + sx * 12, 1300)], 13, 1.05)
    # gli schizzi attorno alle mani
    for (mx, my) in mani:
        for k in range(6):
            a = -math.pi / 2 + rng.uniform(-1.2, 1.2)
            tratto(strato('blu'), [(mx + 40 * math.cos(a), my + 40 * math.sin(a)), (mx + 85 * math.cos(a), my + 85 * math.sin(a))], 9, 1.0, trema=0.2)
    fumetto('AIUTO!', 1350, 230, 56, verso=(-1, 1))
    # Lampy sotto: la cuffia a fiori, che ride e gli tiene le caviglie
    bambino(vx - 210, 1590, 380, 'viola', 'marrone', cuffia_fiori=True, espressione='risata', gonna=True,
            mano_sx=(vx - 40, 1300), mano_dx=(vx + 50, 1305))
    for k in range(9):
        tratto(strato('blu'), cerchio(vx - 250 + rng.uniform(-60, 60), 1250 - k * 70, 14 + k * 2, n=14), 8, 1.0)
    scrivi('blu_notte', 'AH AH AH', 330, 1150, 58, larg=12, press=1.3, cresce=-0.02)
    # la superficie, sopra a tutto: la riga a onde
    onde('blu', 640, passo=60, ampiezza=14, larg=14)
    # un salvagente che galleggia
    tondo('rosso', 1780, 630, 80, press=1.1, schiaccia=0.35)
    tondo('azzurro', 1780, 630, 34, press=0.9, schiaccia=0.35, bordo=None)


def d_marcopolo():
    """Notte 5: Marco Polo in piscina. In mezzo lui con gli occhialini dipinti di nero, a braccia aperte, «MARCO!»;
    attorno gli altri a pelo d'acqua, «POLO!» (Fangy)."""
    foglio(53, 'quadretti')
    rng = rnd()
    ys = np.arange(H)[:, None]
    xs = np.arange(W)[None, :]
    riempi(strato('azzurro'), ys < 300 + 30 * np.sin(xs / 180.0), angolo=-5, passo=15, press=0.75, larg=24, fuori=16, buchi=0.06)
    sole(200, 170, 90)
    scivoli(2150, 820, 420, largo=90)
    # i bambini nell'acqua: si vedono testa, spalle e braccia; l'acqua li copre dal petto in giù
    pelo = 1010
    cols = ['rosso', 'verde', 'arancione', 'rosa']
    attorno = [(330, 0.9), (720, 0.95), (1680, 0.92), (2060, 0.88)]
    for k, (bx, s) in enumerate(attorno):
        bambino(bx, pelo + 230, 470 * s, cols[k], ['marrone', 'giallo', 'nero', 'marrone'][k], espressione='risata' if k % 2 else 'sorriso',
                codini=(k == 1), gambe=False, mani_aperte=True, mano_sx=(bx - 120, pelo - 40), mano_dx=(bx + 120, pelo - 60))
    # lui: gli occhialini neri, la bocca aperta, le braccia larghe
    bambino(1200, pelo + 250, 560, 'blu', 'nero', espressione='urlo', occhialini=True, gambe=False,
            mano_sx=(900, pelo - 260), mano_dx=(1500, pelo - 270))
    acqua = (ys > pelo + 10 * np.sin(xs / 90.0)) & (ys < 1640)
    riempi(strato('azzurro'), acqua, angolo=0, passo=14, press=0.95, larg=24, fuori=4, buchi=0.03)
    for riga in range(4):
        onde('blu', pelo + 40 + riga * 140, passo=64, ampiezza=14, larg=12)
    contorno(strato('blu'), [(60, pelo - 20), (2340, pelo - 26), (2350, 1650), (50, 1655)], larg=16, press=1.1)
    fumetto('MARCO!', 1000, 230, 66, verso=(1, 1))
    fumetto('POLO!', 160, 520, 50, verso=(1, 1))
    fumetto('POLO!', 1760, 470, 50, verso=(1, 1))
    fumetto('POLO!', 560, 360, 44, verso=(1, 1))


DISEGNI = {'ricordo': d_ricordo, 'piscina': d_piscina, 'tesoro': d_tesoro, 'compleanno': d_compleanno,
           'sottacqua': d_sottacqua, 'marcopolo': d_marcopolo}
# la carta di ognuno: le pieghe (verticale, orizzontale), il quaderno strappato (i buchi della spirale a sinistra),
# l'angolo strappato, le macchie d'acqua del lago
CARTA = {
    'ricordo': dict(pieghe=(True, True), strappo=False, angolo=False, macchie=0),
    'piscina': dict(pieghe=(True, False), strappo=False, angolo=False, macchie=2),
    'tesoro': dict(pieghe=(False, True), strappo=True, angolo=False, macchie=2),
    'compleanno': dict(pieghe=(True, True), strappo=False, angolo=True, macchie=3),
    'sottacqua': dict(pieghe=(True, False), strappo=False, angolo=True, macchie=2),
    'marcopolo': dict(pieghe=(False, True), strappo=True, angolo=False, macchie=3),
}


def componi():
    """Stende gli strati sulla carta nell'ordine in cui sono stati disegnati."""
    carta_col = np.array([0.965, 0.95, 0.905])
    img = np.ones((H, W, 3)) * carta_col
    img *= (0.975 + 0.03 * F.grana)[..., None]
    if F.tipo == 'quadretti':
        # i quadretti da mezzo centimetro, stampati in grigio-azzurro
        yy, xx = np.mgrid[:H, :W]
        riga = (np.abs(((xx + 20) % 40) - 20) < 1.2) | (np.abs(((yy + 13) % 40) - 20) < 1.2)
        img = img * (1 - 0.22 * riga[..., None] * np.array([0.5, 0.3, 0.05]))
    g = F.grana
    for st in F.strati:
        if st.p.max() <= 0:
            continue
        soglia = 1.0 - np.clip(st.p, 0, 2.2) * 0.62
        cov = np.clip((g - soglia + 0.06) / 0.12, 0, 1)
        cov *= np.clip(st.p * 3.0, 0, 1)
        a = (cov * 0.93)[..., None]
        sotto = img
        mix = 0.78 * st.c + 0.22 * (st.c * sotto / np.maximum(sotto.max(-1, keepdims=True), 1e-3))
        img = sotto * (1 - a) + mix * a
    return img


def invecchia(img, pieghe=(True, True), strappo=False, angolo=False, macchie=0):
    """Gli anni e il lago: la carta ingiallita verso i bordi, le pieghe, i puntini di umidità, le aloni delle macchie
    d'acqua; il foglio strappato dal quaderno (i buchi della spirale) o con un angolo strappato: lì è trasparente."""
    rng = rnd()
    yy, xx = np.mgrid[:H, :W]
    bordo = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy)) / 260.0
    ing = np.clip(1 - bordo, 0, 1) ** 2
    giallo = np.array([0.93, 0.84, 0.62])
    img = img * (1 - 0.22 * ing[..., None]) + giallo * 0.22 * ing[..., None] * img.mean(-1, keepdims=True) / 0.9
    if pieghe[0]:
        d = xx - (W * 0.5 + 6)
        img = img * (1 - (np.exp(-(d / 3.0) ** 2) * 0.16 + np.exp(-(d / 22.0) ** 2) * 0.05 * np.sign(d))[..., None])
    if pieghe[1]:
        d = yy - (H * 0.5 - 4)
        img = img * (1 - (np.exp(-(d / 3.0) ** 2) * 0.16 + np.exp(-(d / 22.0) ** 2) * 0.05 * np.sign(d))[..., None])
    for k in range(40):
        cx, cy = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(2, 9)
        m = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))
        img = img * (1 - 0.18 * m[..., None] * np.array([0.3, 0.55, 0.9]))
    for k in range(macchie):
        # una macchia d'acqua: la carta un po' più scura dentro e l'alone marrone sul bordo, dove l'acqua si è fermata
        cx, cy = rng.uniform(0.1, 0.9) * W, rng.uniform(0.1, 0.9) * H
        rx, ry = rng.uniform(150, 420), rng.uniform(120, 330)
        ang = np.arctan2(yy - cy, xx - cx)
        rr = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) * (1 + 0.12 * np.sin(ang * 5 + rng.uniform(0, 6)) + 0.06 * np.sin(ang * 13))
        dentro = np.clip(1 - rr, 0, 1) ** 0.3 * (rr < 1)
        alone = np.exp(-((rr - 1.0) / 0.025) ** 2)
        img = img * (1 - 0.05 * dentro[..., None]) * (1 - 0.22 * alone[..., None] * np.array([0.25, 0.45, 0.8]))
    alfa = np.ones((H, W))
    if strappo:
        # strappato dal quaderno: il bordo sinistro sfrangiato e i buchi della spirale
        bordo_sx = 26 + 10 * gaussian_filter(rng.standard_normal(H), 3) + 6 * gaussian_filter(rng.standard_normal(H), 0.8)
        alfa[xx < bordo_sx[:, None]] = 0
        for k in range(int(H / 100)):
            cy = 50 + k * 100
            alfa[((xx - 70) ** 2 + (yy - cy) ** 2) < 15 ** 2] = 0
    if angolo:
        # un angolo strappato (in basso a destra), sfrangiato
        t = (W - xx) + (H - yy) - 170 - 18 * gaussian_filter(rng.standard_normal(W + H), 2)[np.clip((xx - yy + H).astype(int), 0, W + H - 1)]
        alfa[t < 0] = 0
    alfa = gaussian_filter(alfa, 0.7)
    return np.clip(img, 0, 1), alfa


def main():
    nomi = [a for a in sys.argv[1:] if not a.startswith('--')]
    uscita = sys.argv[sys.argv.index('--uscita') + 1] if '--uscita' in sys.argv else '.'
    if uscita in nomi:
        nomi.remove(uscita)
    if not nomi or nomi == ['tutti']:
        nomi = list(DISEGNI)
    os.makedirs(uscita, exist_ok=True)
    for nome in nomi:
        DISEGNI[nome]()
        img, alfa = invecchia(componi(), **CARTA[nome])
        rgba = np.dstack([img, alfa])
        im = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA')
        out = os.path.join(uscita, f'pastelli_{nome}.webp')
        im.save(out, quality=92, method=6)
        if '--anteprima' in sys.argv:
            prev = Image.new('RGB', (W // 2, H // 2), (24, 22, 26))
            small = im.resize((W // 2, H // 2), Image.LANCZOS)
            prev.paste(small, (0, 0), small)
            prev.save(os.path.join(uscita, f'pastelli_{nome}_anteprima.jpg'), quality=88)
        print('disegno', nome, out, flush=True)


if __name__ == '__main__':
    main()
