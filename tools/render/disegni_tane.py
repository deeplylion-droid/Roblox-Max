"""
I disegni a pastelli delle cose da trovare nelle tane (DA APPROVARE, 12 ottobre): fatti con pastelli.py, la stessa
mano dei disegni dell'alba e di «Il ricordo». I soggetti non ripetono i cinque disegni dell'alba (la piscina, il
tesoro di Robin, la festa di Archie, Lampy sott'acqua, Marco Polo):

    gulpy   il menù dello Snack Shack, coi disegnini e i prezzi, e tutto cerchiato: «!!!»
    hatch   il foglio della conta: i numeri da 1 a 10 scritti e riscritti, e in mezzo «10! CHI C'È C'È»
    robin   gli scaffali dei premi della sala giochi, coi biglietti che costano, e lui che li vuole tutti: «!!!»
    archie  tutti i compleanni dell'anno: dodici torte, una per mese, con le candeline cancellate col nero (1999)
    fangy   io: lui con gli occhialini dipinti di nero, calcati fino a bucare la carta, e «IO»

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
import pastelli as P  # noqa: E402

W, H = P.W, P.H


def gulpy():
    """Il menù dello Snack Shack (su un foglio a quadretti): ogni riga il disegnino e il prezzo, e alla fine un cerchio
    rosso attorno a tutto con la freccia e «!!!». Niente parole italiane (docs/LOCALIZZAZIONE.md): resta solo «HOT DOG»,
    uguale in tutte le lingue; patatine, gelato e panino si riconoscono dal disegno (da approvare)."""
    P.foglio(201, 'quadretti')
    P.scrivi('rosso', 'MENU', 900, 190, 190, larg=26, press=1.4)
    righe = [('HOT DOG', '3000'), ('PATATINE', '2000'), ('GELATO', '1500'), ('PANINO', '4000')]
    for k, (cosa, prezzo) in enumerate(righe):
        y = 470 + k * 300
        x = 330
        if cosa == 'HOT DOG':
            P.colora('arancione', [(x - 150, y - 40), (x + 150, y - 50), (x + 160, y + 40), (x - 150, y + 45)], press=0.9)
            P.tratto(P.strato('rosso'), [(x - 140, y), (x - 50, y - 20), (x + 40, y + 10), (x + 140, y - 10)], larg=16, press=1.2)
        elif cosa == 'PATATINE':
            P.colora('rosso', [(x - 90, y - 20), (x + 90, y - 20), (x + 70, y + 110), (x - 70, y + 110)], press=0.9)
            for j in range(6):
                P.tratto(P.strato('giallo'), [(x - 70 + j * 28, y - 20), (x - 80 + j * 30, y - 130)], larg=18, press=1.2)
        elif cosa == 'GELATO':
            P.colora('marrone', [(x - 60, y - 10), (x + 60, y - 10), (x, y + 140)], press=0.8)
            P.tondo('rosa', x, y - 60, 70, press=1.0)
        else:
            P.panino(x, y, 0.55)
        if cosa == 'HOT DOG':
            P.scrivi('blu', cosa, 560, y, 96, larg=15, press=1.1)
        P.scrivi('nero', prezzo, 1700, y, 100, larg=15, press=1.15)
    # il cerchio attorno a tutto, calcato due volte, e la freccia
    giro = P.cerchio(1200, 900, 1050, giri=1.9, schiaccia=0.62)
    P.tratto(P.strato('rosso'), giro, larg=22, press=1.5, trema=1.6)
    P.tratto(P.strato('rosso'), [(2050, 1450), (1900, 1330), (1860, 1420)], larg=20, press=1.4)
    fine = P.scrivi('rosso', '!!!', 1720, 1560, 150, larg=24, press=1.6)
    assert fine < W - 60, fine         # i «!» restano sul foglio
    return 'gulpy', dict(pieghe=(True, False), strappo=True, angolo=False, macchie=2)


def hatch():
    """Il foglio della conta: i numeri da 1 a 10 scritti e riscritti in righe storte, sempre più calcati e fitti, e in
    mezzo, sopra a tutto, «10! CHI C'È C'È» in rosso. Il «10!» si legge nel gioco ed è uguale in tutte le lingue
    (docs/LOCALIZZAZIONE.md: niente italiano leggibile nelle scene); «CHI C'È C'È», più piccolo, non si legge."""
    P.foglio(202, 'album')
    rng = P.rnd()
    colori = ['blu', 'blu_notte', 'nero', 'viola']
    y, k = 130, 0
    while y < H - 110:
        x = 90 + rng.uniform(-30, 30)
        alt = 92 - 26 * (y / H)
        while x < W - 170:
            n = (k % 10) + 1
            P.scrivi(colori[(k // 10) % len(colori)], str(n), x, y, alt, larg=12, press=0.85 + 0.45 * (y / H))
            x += alt * (1.25 if n < 10 else 2.0) + rng.uniform(5, 40)
            k += 1
        y += alt * 1.35
    P.riempi(P.strato('bianco'), P.maschera_poligono([(360, 600), (2060, 585), (2090, 1080), (340, 1100)]), passo=9, press=1.6, larg=24)
    P.scrivi('rosso', '10!', 960, 770, 300, larg=30, press=1.6)
    P.scrivi('rosso', "CHI C'È C'È", 560, 1010, 150, larg=22, press=1.4, specchia=(2,))
    return 'hatch', dict(pieghe=(True, True), strappo=False, angolo=True, macchie=2)


def robin():
    """Gli scaffali dei premi della sala giochi: l'orso enorme, la palla, la macchinina, ognuno col suo prezzo in
    biglietti; lui piccolo davanti, i biglietti attorno alle braccia, e sopra il fumetto «!!!» (prima «VOGLIO TUTTO»:
    niente parole italiane nelle scene, docs/LOCALIZZAZIONE.md; da approvare)."""
    P.foglio(203, 'album')
    for y in (520, 980, 1440):
        P.colora('marrone', [(120, y), (2280, y - 10), (2280, y + 50), (120, y + 60)], press=0.85)
    # l'orso, enorme, sullo scaffale in alto
    P.tondo('marrone', 600, 330, 150, press=0.9)
    P.tondo('marrone', 600, 140, 95, press=0.9)
    for s in (-1, 1):
        P.tondo('marrone', 600 + s * 80, 60, 38, press=0.9)
        P.tondo('nero', 600 + s * 35, 130, 12, press=1.3, bordo=None)
    P.scrivi('rosso', '5000', 820, 330, 110, larg=16, press=1.3)
    P.tondo('rosso', 1500, 420, 90, press=1.0)
    P.scrivi('rosso', '800', 1640, 430, 90, larg=14)
    P.colora('blu', [(380, 880), (680, 880), (700, 960), (360, 960)], press=1.0)
    for x in (430, 640):
        P.tondo('nero', x, 965, 32, press=1.2)
    P.scrivi('rosso', '1200', 750, 900, 90, larg=14)
    P.colora('rosa', [(1500, 760), (1750, 760), (1800, 960), (1450, 960)], press=0.9)
    P.scrivi('rosso', '300', 1850, 880, 80, larg=13)
    P.bambino(1150, 1650, 520, maglia='verde', capelli='nero', espressione='sorriso', biglietti=True,
              mano_sx=(980, 1300), mano_dx=(1320, 1290))
    P.fumetto('!!!', 1450, 1130, 90, verso=(-1, 1))
    return 'robin', dict(pieghe=(False, True), strappo=False, angolo=False, macchie=3)


def archie():
    """Tutti i compleanni dell'anno: dodici torte in fila, una per mese (le iniziali dei mesi sotto), ognuna con le sue
    candeline; tutte le fiammelle cancellate col nero, calcato. In alto «1999»."""
    P.foglio(204, 'quadretti')
    P.scrivi('blu', '1999', 960, 170, 150, larg=22, press=1.3)
    mesi = 'GFMAMGLASOND'
    for k in range(12):
        cx = 250 + (k % 6) * 380
        cy = 720 + (k // 6) * 640
        P.colora(['rosa', 'giallo', 'azzurro', 'verde_chiaro'][k % 4], [(cx - 130, cy - 60), (cx + 130, cy - 65), (cx + 125, cy + 120), (cx - 125, cy + 125)], press=0.85)
        for j in range(3 + k % 4):
            x = cx - 90 + j * (180 / max(1, 2 + k % 4))
            P.tratto(P.strato(['blu', 'rosso', 'verde'][j % 3]), [(x, cy - 65), (x + 3, cy - 170)], larg=22, press=1.1)
            P.tondo('arancione', x + 2, cy - 200, 20, press=1.0, bordo=None)
            # la fiammella cancellata
            P.tratto(P.strato('nero'), P.cerchio(x + 2, cy - 200, 30, giri=2.6), larg=12, press=1.4, trema=1.4)
        P.scrivi('nero', mesi[k], cx - 20, cy + 230, 80, larg=13)
    return 'archie', dict(pieghe=(True, True), strappo=True, angolo=False, macchie=2)


def fangy():
    """Io: un bambino grande in mezzo al foglio, con gli occhialini da piscina dipinti di nero, calcati tante volte
    (la cera lucida); sotto «IO»; niente altro sul foglio."""
    P.foglio(205, 'album')
    P.bambino(1200, 1450, 1200, maglia='blu', capelli='nero', espressione='sorriso', occhialini=True,
              mano_sx=(850, 1050), mano_dx=(1550, 1060))
    # gli occhialini ripassati e ripassati, fino a sbordare
    for k in range(4):
        for s in (-1, 1):
            P.tratto(P.strato('nero'), P.cerchio(1200 + s * 80, 470, 70 + 6 * k, giri=1.3), larg=24, press=1.6, trema=1.2)
    P.scrivi('nero', 'IO', 1080, 1580, 120, larg=20, press=1.4)
    return 'fangy', dict(pieghe=(False, True), strappo=False, angolo=True, macchie=2)


DISEGNI = {'gulpy': gulpy, 'hatch': hatch, 'robin': robin, 'archie': archie, 'fangy': fangy}


def fai(chi):
    nome, carta = DISEGNI[chi]()
    img, alfa = P.invecchia(P.componi(), **carta)
    # sul fondo della tana non c'è trasparenza: dove la carta è strappata resta la sabbia (il colore scuro sotto)
    img = img * alfa[..., None] + np.array([0.09, 0.09, 0.08]) * (1 - alfa[..., None])
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'tane', f'pastello_{nome}.png')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).resize((W // 2, H // 2), Image.LANCZOS).save(path)
    print('disegno', path, flush=True)
    return path


def main():
    chi = [a for a in sys.argv[1:] if a in DISEGNI] or list(DISEGNI)
    for c in chi:
        fai(c)


if __name__ == '__main__':
    main()
