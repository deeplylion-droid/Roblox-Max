"""
I disegni a pastelli delle cose da trovare nelle tane (DA APPROVARE, 12 ottobre): fatti con la stessa mano del disegno
di «Il ricordo» (disegno_ricordo.py: la carta d'album, la cera che si posa sulla grana, i tratti tremolanti di un
bambino di sette anni), così tutti i disegni dei bambini si somigliano.

    gulpy   lui con la bocca enorme davanti allo Snack Shack, e un panino più grande di lui: «IO E IL PANINO»
    hatch   il foglio della conta: i numeri da 1 a 10 scritti e riscritti, e in mezzo «DIECI! CHI C'È C'È»
    robin   la lista delle cose prese, con le crocette; l'ultima riga: «ANCORA»
    archie  il biglietto d'auguri: la torta con sette candeline, una spenta; «TANTI AUGURI»
    fangy   fatto a occhi bendati: scarabocchi che non si toccano, e in mezzo «MARCO?»

La foto di Molly e il braccialetto dell'ospedale di Lampy non sono disegni (tane.disegno).

Uso: tools/.venv/bin/python tools/render/disegni_tane.py [chi ...]   (le immagini in tools/render/cache/tane/pastello_*.png)
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import disegno_ricordo as DR  # noqa: E402

# le lettere che il disegno di «Il ricordo» non usava (stesso stampatello: tratti in un quadrato 0..1)
DR.LETTERE.update({
    'B': [[(0.1, 1), (0.1, 0), (0.6, 0.03), (0.85, 0.22), (0.6, 0.47), (0.1, 0.48)], [(0.1, 0.48), (0.7, 0.52), (0.92, 0.75), (0.65, 0.98), (0.1, 1)]],
    'C': [[(0.88, 0.15), (0.55, 0), (0.18, 0.12), (0.05, 0.5), (0.18, 0.88), (0.55, 1), (0.9, 0.85)]],
    'E': [[(0.9, 0.02), (0.1, 0), (0.1, 1), (0.92, 1)], [(0.1, 0.5), (0.75, 0.48)]],
    'F': [[(0.9, 0.02), (0.1, 0), (0.1, 1)], [(0.1, 0.5), (0.72, 0.48)]],
    'K': [[(0.1, 0), (0.1, 1)], [(0.9, 0), (0.12, 0.55)], [(0.35, 0.4), (0.92, 1)]],
    'M': [[(0.05, 1), (0.08, 0), (0.5, 0.6), (0.92, 0), (0.95, 1)]],
    'O': [[(0.5, 0), (0.15, 0.12), (0.03, 0.5), (0.18, 0.9), (0.55, 1), (0.88, 0.82), (0.97, 0.45), (0.8, 0.1), (0.45, 0.02)]],
    'R': [[(0.1, 1), (0.1, 0), (0.6, 0.02), (0.88, 0.22), (0.6, 0.48), (0.1, 0.5)], [(0.4, 0.5), (0.92, 1)]],
    'U': [[(0.08, 0), (0.1, 0.75), (0.4, 1), (0.75, 0.95), (0.92, 0.7), (0.92, 0)]],
    'V': [[(0, 0), (0.5, 1), (1, 0)]],
    'Z': [[(0.05, 0.02), (0.95, 0), (0.05, 1), (0.95, 0.98)]],
    '?': [[(0.1, 0.25), (0.35, 0.02), (0.75, 0.05), (0.85, 0.3), (0.5, 0.55), (0.48, 0.75)], [(0.47, 0.93), (0.5, 1)]],
    '!': [[(0.5, 0), (0.48, 0.72)], [(0.47, 0.92), (0.5, 1)]],
    "'": [[(0.5, 0), (0.4, 0.3)]],
    '0': [[(0.5, 0), (0.15, 0.2), (0.1, 0.7), (0.45, 1), (0.85, 0.75), (0.9, 0.25), (0.55, 0)]],
    '1': [[(0.2, 0.25), (0.6, 0), (0.6, 1)]],
    '3': [[(0.1, 0.1), (0.55, 0), (0.85, 0.2), (0.45, 0.48), (0.88, 0.7), (0.6, 1), (0.08, 0.9)]],
    '4': [[(0.7, 1), (0.7, 0), (0.05, 0.68), (0.95, 0.68)]],
    '5': [[(0.85, 0.02), (0.2, 0), (0.15, 0.45), (0.6, 0.4), (0.9, 0.65), (0.6, 1), (0.1, 0.9)]],
    '8': [[(0.5, 0.48), (0.15, 0.25), (0.45, 0), (0.85, 0.22), (0.5, 0.48), (0.1, 0.75), (0.45, 1), (0.9, 0.78), (0.5, 0.48)]],
    'X': [[(0.05, 0), (0.95, 1)], [(0.95, 0), (0.05, 1)]],
})

W, H = DR.W, DR.H


def _nuovo(seme):
    DR.STRATI.clear()
    DR.rng = np.random.default_rng(seme)


def _scrivi(colore, testo, x, y, alt, **kw):
    DR.scrivi(DR.strato(colore), testo, x, y, alt, **kw)


def _rett(st, x0, y0, x1, y1, press=1.0, larg=16):
    DR.contorno(st, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], larg=larg, press=press)


def gulpy():
    """Lui con la bocca enorme davanti allo Snack Shack, e un panino più grande di lui."""
    _nuovo(101)
    ys = np.arange(H)[:, None]
    xs = np.arange(W)[None, :]
    # il prato e il cielo
    DR.riempi(DR.strato('verde'), ys > 1350 + 20 * np.sin(xs / 140.0), angolo=-5, passo=18, press=0.55, larg=22, buchi=0.15)
    DR.riempi(DR.strato('azzurro'), ys < 260 + 30 * np.sin(xs / 190.0), angolo=8, passo=20, press=0.45, larg=22, buchi=0.2)
    # lo Snack Shack: il bancone rosso, la tenda a strisce rosse e bianche, l'insegna
    rosso = DR.strato('rosso')
    DR.riempi(rosso, DR.maschera_poligono([(150, 820), (900, 800), (920, 1360), (140, 1370)]), angolo=20, passo=14, press=0.85)
    for k in range(6):
        x0 = 120 + k * 135
        DR.riempi(rosso if k % 2 == 0 else DR.strato('bianco'), DR.maschera_poligono([(x0, 600), (x0 + 135, 590), (x0 + 150, 790), (x0 + 10, 800)]), angolo=70, passo=12, press=0.9)
    DR.contorno(DR.strato('nero'), [(110, 590), (950, 580), (960, 800), (110, 810)], larg=14)
    _scrivi('blu', 'SNACK', 260, 470, 120, larg=16)
    # lui: la testa enorme con la bocca spalancata (più grande della faccia), il corpo piccolo
    pesca = DR.strato('pesca')
    hx, hy, hr = 1350, 820, 260
    DR.riempi(pesca, DR.maschera_cerchio(hx, hy, hr), angolo=35, passo=13, press=0.7)
    DR.contorno(DR.strato('marrone'), DR.cerchio(hx, hy, hr), larg=16)
    bocca = DR.cerchio(hx + 20, hy + 70, 170, schiaccia=0.75)
    DR.riempi(DR.strato('rosso'), DR.maschera_cerchio(hx + 20, hy + 70, 170, 0.75), angolo=60, passo=10, press=1.2)
    DR.contorno(DR.strato('nero'), bocca, larg=16)
    for k in range(9):           # i dentini
        a = math.pi * (0.15 + 0.7 * k / 8)
        x, y = hx + 20 + 165 * math.cos(a + math.pi), hy + 70 - 125 * math.sin(a + math.pi) * -1
        DR.tratto(DR.strato('bianco'), [(x, y - 30), (x + 12, y + 20)], larg=14, press=1.3)
    for s_ in (-1, 1):
        DR.riempi(DR.strato('nero'), DR.maschera_cerchio(hx + s_ * 95, hy - 140, 26), press=1.3, passo=7)
    nero = DR.strato('blu')
    DR.tratto(nero, [(hx, hy + hr), (hx, hy + hr + 320)], larg=40)
    for s_ in (-1, 1):
        DR.tratto(nero, [(hx, hy + hr + 320), (hx + s_ * 90, 1520)], larg=26)
        DR.tratto(DR.strato('pesca'), [(hx, hy + hr + 90), (hx + s_ * 210, hy + hr + 40)], larg=22)
    # il panino gigante, più grande di lui, a destra
    px, py = 1950, 780
    DR.riempi(DR.strato('arancione'), DR.maschera_cerchio(px, py - 120, 330, 0.45), angolo=10, passo=14, press=0.8)
    DR.riempi(DR.strato('verde'), DR.maschera_poligono([(px - 360, py - 40), (px + 360, py - 50), (px + 320, py + 30), (px - 330, py + 40)]), passo=10, press=1.0)
    DR.riempi(DR.strato('marrone'), DR.maschera_poligono([(px - 340, py + 30), (px + 330, py + 25), (px + 300, py + 110), (px - 310, py + 120)]), passo=12, press=0.95)
    DR.riempi(DR.strato('arancione'), DR.maschera_cerchio(px, py + 200, 320, 0.33), angolo=-10, passo=14, press=0.8)
    for k in range(9):
        DR.riempi(DR.strato('bianco'), DR.maschera_cerchio(px - 200 + k * 50, py - 230 + (k % 3) * 25, 9, 1.6), press=1.3, passo=5)
    _scrivi('nero', 'IO E IL PANINO', 1120, 180, 120, larg=16, specchia=())
    return _finisci('gulpy')


def hatch():
    """Il foglio della conta: i numeri da 1 a 10 scritti e riscritti in colonne storte, sempre più fitti, e in mezzo
    «DIECI! CHI C'È C'È» calcato in rosso."""
    _nuovo(102)
    colori = ['blu', 'blu_notte', 'nero', 'viola', 'blu']
    y = 120
    k = 0
    while y < H - 120:
        x = 90 + DR.rng.uniform(-30, 30)
        alt = 95 - 30 * (y / H)
        while x < W - 160:
            n = (k % 10) + 1
            _scrivi(colori[(k // 10) % len(colori)], str(n) if n < 10 else '10', x, y, alt, larg=12, press=0.9 + 0.3 * (y / H))
            x += alt * (1.3 if n < 10 else 2.1) + DR.rng.uniform(5, 40)
            k += 1
        y += alt * 1.35
    # sopra, calcato in rosso, la fine della conta
    DR.riempi(DR.strato('bianco'), DR.maschera_poligono([(380, 620), (2050, 600), (2080, 1060), (360, 1080)]), passo=9, press=1.6, larg=24)
    _scrivi('rosso', 'DIECI!', 520, 740, 220, larg=26, press=1.5)
    _scrivi('rosso', "CHI C'E C'E", 470, 990, 170, larg=22, press=1.4, specchia=(2,))
    return _finisci('hatch')


def robin():
    """La lista delle cose prese (su un foglio a righe): ogni riga un disegnino e la crocetta; l'ultima «ANCORA»."""
    _nuovo(103)
    righe = DR.strato('azzurro')
    for y in range(160, H - 80, 150):
        DR.tratto(righe, [(60, y), (W - 60, y + 4)], larg=4, press=0.5, trema=0.1)
    disegnini = [('rosso', 'scarpa'), ('blu', 'macchina'), ('nero', 'occhiali'), ('blu', 'cappello'), ('arancione', 'palla'),
                 ('rosa', 'braccialetto'), ('giallo', 'biglietti')]
    for i, (col, cosa) in enumerate(disegnini):
        y = 160 + i * 150 + 75
        st = DR.strato(col)
        x = 420
        if cosa == 'palla':
            DR.riempi(st, DR.maschera_cerchio(x, y, 58), press=0.9)
        elif cosa == 'occhiali':
            for s_ in (-1, 1):
                DR.contorno(st, DR.cerchio(x + s_ * 75, y, 50), larg=12)
        else:
            DR.riempi(st, DR.maschera_poligono([(x - 160, y - 48), (x + 160, y - 52), (x + 170, y + 48), (x - 165, y + 52)]), press=0.85)
        # la crocetta, e accanto un'altra crocetta più piccola: rubata due volte
        for (cx_, r_) in ((800, 48), (960, 30)):
            DR.tratto(DR.strato('nero'), [(cx_ - r_, y - r_), (cx_ + r_, y + r_)], larg=14, press=1.3)
            DR.tratto(DR.strato('nero'), [(cx_ + r_, y - r_), (cx_ - r_, y + r_)], larg=14, press=1.3)
    _scrivi('rosso', 'ANCORA', 300, 160 + 7 * 150 + 90, 150, larg=22, press=1.5)
    _scrivi('rosso', 'ANCORA', 1300, 160 + 7 * 150 + 60, 110, larg=18, press=1.2)
    _scrivi('rosso', 'ANCORA', 1500, 160 + 4 * 150 + 75, 130, larg=20, press=1.3, cresce=0.04)
    return _finisci('robin')


def archie():
    """Il biglietto d'auguri: la torta rosa con sette candeline, una spenta; «TANTI AUGURI»."""
    _nuovo(104)
    _scrivi('rosso', 'TANTI AUGURI', 330, 270, 210, larg=24, press=1.3)
    cx, cy = W / 2, 1150
    DR.riempi(DR.strato('rosa'), DR.maschera_poligono([(cx - 620, cy - 200), (cx + 620, cy - 210), (cx + 600, cy + 330), (cx - 610, cy + 340)]), passo=13, press=0.85)
    DR.riempi(DR.strato('bianco'), DR.maschera_poligono([(cx - 640, cy - 240), (cx + 640, cy - 250), (cx + 630, cy - 150), (cx - 630, cy - 140)]), passo=9, press=1.3)
    DR.contorno(DR.strato('marrone'), [(cx - 640, cy - 240), (cx + 640, cy - 250), (cx + 600, cy + 330), (cx - 610, cy + 340)], larg=14)
    for k in range(7):
        x = cx - 480 + k * 160
        DR.tratto(DR.strato(['blu', 'giallo', 'verde', 'blu', 'rosa', 'giallo', 'verde'][k]), [(x, cy - 250), (x + 5, cy - 470)], larg=40, press=1.1)
        if k != 3:
            DR.riempi(DR.strato('arancione'), DR.maschera_cerchio(x + 4, cy - 540, 38, 1.5), press=1.2, passo=6)
            DR.riempi(DR.strato('giallo'), DR.maschera_cerchio(x + 4, cy - 530, 18, 1.5), press=1.3, passo=5)
        else:
            DR.tratto(DR.strato('nero'), [(x + 4, cy - 490), (x - 10, cy - 560), (x + 20, cy - 620), (x, cy - 680)], larg=8, press=0.8)
    return _finisci('archie')


def fangy():
    """Disegnato a occhi bendati: scarabocchi che non si toccano e non chiudono, un pesce senza occhi, e in mezzo,
    calcato in rosso, «MARCO?»."""
    _nuovo(105)
    rr = DR.rng
    for k in range(16):
        c = DR.strato(['nero', 'blu', 'viola', 'verde'][k % 4])
        x, y = rr.uniform(150, W - 150), rr.uniform(150, H - 150)
        pts = [(x, y)]
        for j in range(rr.integers(4, 9)):
            x += rr.uniform(-260, 260)
            y += rr.uniform(-200, 200)
            pts.append((float(np.clip(x, 60, W - 60)), float(np.clip(y, 60, H - 60))))
        DR.tratto(c, pts, larg=rr.uniform(10, 20), press=rr.uniform(0.7, 1.2), trema=2.0)
    # il pesce senza occhi: il contorno che non chiude, spostato rispetto al colore
    DR.riempi(DR.strato('azzurro'), DR.maschera_cerchio(1500, 1150, 230, 0.5), passo=16, press=0.6)
    DR.contorno(DR.strato('blu_notte'), DR.cerchio(1440, 1100, 240, schiaccia=0.5), larg=14, sbava=0.3)
    _scrivi('rosso', 'MARCO?', 700, 700, 230, larg=26, press=1.5, salti=0.3)
    return _finisci('fangy')


def _finisci(nome):
    img = DR.invecchia(DR.componi())
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'tane', f'pastello_{nome}.png')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).resize((W // 2, H // 2), Image.LANCZOS).save(path)
    print('disegno', path, flush=True)
    return path


DISEGNI = {'gulpy': gulpy, 'hatch': hatch, 'robin': robin, 'archie': archie, 'fangy': fangy}


def main():
    chi = [a for a in sys.argv[1:] if a in DISEGNI] or list(DISEGNI)
    for c in chi:
        DISEGNI[c]()


if __name__ == '__main__':
    main()
