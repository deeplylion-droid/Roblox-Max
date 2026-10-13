"""
Il logo del gioco: l'insegna al neon (scelta dell'utente del 13 ottobre fra tre proposte, il neon, il cartello sbarrato
e il pastello; senza «MAMA MARINA'S», richiesta dell'utente; il risultato è da approvare). SPLASHLAND in tubi rosa
col carattere del parco (Limelight), con due lettere spente come l'insegna dell'ingresso (la S in mezzo e la N); dietro
la raggiera arancione, con due raggi spenti; sotto «is closed!» in corsivo rosso, storto, tutto acceso.

Il menu principale lo mostra al posto del titolo (src/app/screens.ts). Ogni tanto la S spenta prova a riaccendersi:
per quello c'è un secondo fotogramma, uguale col tubo della S acceso (più debole degli altri).

Escono in public/assets/img/logo/: logo.webp (l'insegna) e logo_tremolio.webp (la S che si riaccende), trasparenti,
larghi LARGHEZZA px, col bagliore attorno (sfuma a zero prima dei bordi). Le due immagini hanno lo stesso riquadro:
nel gioco stanno una sopra l'altra.

Uso: tools/.venv/bin/python tools/render/logo.py [cartella]
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt, gaussian_filter

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))
USCITA = os.path.join(RADICE, 'public', 'assets', 'img', 'logo')
FONTS = os.path.join(QUI, 'fonts')
LARGHEZZA = 1800

ROSA, ARANCIO, ROSSO = (1.0, 0.30, 0.62), (1.0, 0.52, 0.16), (1.0, 0.13, 0.10)
SPENTE = {4, 8}            # le lettere spente di SPLASHLAND: la S in mezzo e la N, come sull'insegna dell'ingresso
RAGGI_SPENTI = {3, 8}
TREMA = 4                  # la lettera che ogni tanto prova a riaccendersi
# il disegno sta in un quadro di 2200×1000; attorno, MARGINE px per parte perché il bagliore sfumi prima dei bordi
QW, QH, MARGINE = 2200, 1000, 260


def font(nome, px):
    p = os.path.join(FONTS, 'annuncio', nome + '.ttf')
    if not os.path.exists(p):
        p = os.path.join(FONTS, nome + '.ttf')
    return ImageFont.truetype(p, int(px))


def maschera(testo, f, W, H, x, y, gradi=0.0):
    """La maschera (0..1) di un testo con l'angolo in alto a sinistra in (x, y), girata attorno al suo centro."""
    im = Image.new('L', (W, H), 0)
    ImageDraw.Draw(im).text((x, y), testo, font=f, fill=255)
    if gradi:
        bb = im.getbbox()
        if bb:
            im = im.rotate(gradi, resample=Image.BICUBIC, center=((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2))
    return np.asarray(im, np.float32) / 255


def tubo(m, larg=4.6):
    """Il tubo del neon lungo il contorno della maschera: un profilo morbido centrato sul bordo delle lettere."""
    b = m > 0.5
    d = distance_transform_edt(b) - distance_transform_edt(~b)
    return np.exp(-(d / larg) ** 2)


def neon(colore, t, acceso=1.0):
    """La luce di un tubo acceso: l'anima quasi bianca, il vetro colorato, quattro aloni sempre più larghi."""
    c = np.array(colore, np.float32)
    anima = np.clip(t * 1.7 - 0.55, 0, 1)
    rgb = t[..., None] * c * 1.25 + anima[..., None] * (1 - c) * 0.9
    for s, k in ((5, 0.9), (14, 0.85), (36, 0.75), (90, 0.45)):
        rgb += gaussian_filter(t, s)[..., None] * c * k * (s / 5) ** 0.45
    return rgb * acceso


def spento(t):
    """Il tubo spento: vetro scuro con un filo di riflesso e un po' della luce dei tubi accesi accanto."""
    vetro = np.array([0.34, 0.17, 0.27], np.float32)
    rifl = np.clip(gaussian_filter(t, 0.8) - 0.5, 0, 1) * 0.7
    return t[..., None] * vetro + rifl[..., None] * np.array([0.6, 0.45, 0.55]) + gaussian_filter(t, 10)[..., None] * np.array([0.10, 0.03, 0.07])


def insegna(trema=False):
    """La luce dell'insegna (RGB lineare, può passare 1): con `trema`, la lettera TREMA accesa, più debole."""
    W, H = QW + 2 * MARGINE, QH + 2 * MARGINE
    ox = oy = MARGINE
    rgb = np.zeros((H, W, 3), np.float32)
    f = font('Limelight-Regular', 300)
    testo = 'SPLASHLAND'
    x0, y0 = ox + (QW - f.getlength(testo)) / 2, oy + 250
    tutte = maschera(testo, f, W, H, x0, y0)
    # la raggiera dietro (come sull'insegna dell'ingresso): tubi arancioni, due spenti; non passa sopra le lettere
    cx, cy = ox + QW * 0.5, oy + 480
    accesi, morti = Image.new('L', (W, H), 0), Image.new('L', (W, H), 0)
    da, dm = ImageDraw.Draw(accesi), ImageDraw.Draw(morti)
    for i, ang in enumerate(np.linspace(math.radians(195), math.radians(345), 13)):
        r0, r1 = 170, 400 if i % 2 else 330
        p0 = (cx + r0 * math.cos(ang), cy + r0 * math.sin(ang))
        p1 = (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))
        (dm if i in RAGGI_SPENTI else da).line([p0, p1], fill=255, width=7)
    da.arc([cx - 150, cy - 150, cx + 150, cy + 150], 190, 350, fill=255, width=7)
    via = gaussian_filter((tutte > 0.3).astype(np.float32), 9) > 0.03
    for im, acceso in ((accesi, True), (morti, False)):
        t = gaussian_filter(np.asarray(im, np.float32) / 255, 1.6)
        t = t / max(t.max(), 1e-3) * (~via)
        rgb += neon(ARANCIO, t, 0.55) if acceso else spento(t) * 0.8
    # SPLASHLAND, una lettera per volta (con la crenatura del carattere)
    for i, ch in enumerate(testo):
        t = tubo(maschera(ch, f, W, H, x0 + f.getlength(testo[:i]), y0))
        if i in SPENTE and not (trema and i == TREMA):
            rgb += spento(t)
        elif i in SPENTE:
            # il tubo che si riaccende a fatica: più debole, e il vetro spento si vede ancora un po'
            rgb += neon(ROSA, t, 0.7) + spento(t) * 0.4
        else:
            rgb += neon(ROSA, t)
    # «is closed!» in corsivo rosso, storto, tutto acceso
    f3 = font('Pacifico-Regular', 230)
    s3 = 'is closed!'
    rgb += neon(ROSSO, tubo(maschera(s3, f3, W, H, ox + QW * 0.5 - f3.getlength(s3) * 0.30, oy + 560, gradi=7), 3.2), 1.15)
    return rgb


def immagine(rgb):
    """Dalla luce all'immagine trasparente: l'alfa è quanto è chiaro, il colore è la luce divisa per l'alfa; ai bordi
    il bagliore sfuma a zero (se no, sopra il ritratto si vedrebbe un rettangolo)."""
    H, W, _ = rgb.shape
    alfa = np.clip(rgb.max(-1) * 1.15, 0, 1)
    col = np.clip(rgb / np.maximum(alfa[..., None], 1e-4), 0, 1)
    yy, xx = np.mgrid[:H, :W]
    bordo = np.minimum.reduce([xx, W - 1 - xx, yy, H - 1 - yy]).astype(np.float32)
    k = np.clip(bordo / (MARGINE * 0.8), 0, 1)
    alfa *= k * k * (3 - 2 * k)
    return col, alfa


def main(cartella=USCITA):
    os.makedirs(cartella, exist_ok=True)
    quadri = [immagine(insegna(trema)) for trema in (False, True)]
    # lo stesso riquadro per tutte e due (quello del fotogramma più largo): nel gioco stanno una sopra l'altra
    unione = np.maximum(quadri[0][1], quadri[1][1])
    ys, xs = np.nonzero(unione > 2 / 255)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    for (col, alfa), nome in zip(quadri, ('logo', 'logo_tremolio')):
        rgba = np.dstack([col, alfa])
        im = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA').crop(box)
        im = im.resize((LARGHEZZA, round(im.height * LARGHEZZA / im.width)), Image.LANCZOS)
        p = os.path.join(cartella, nome + '.webp')
        im.save(p, quality=92, alpha_quality=100, method=6)
        print('logo', p, im.size, os.path.getsize(p) // 1024, 'KB', flush=True)
    # dove stanno le lettere nell'immagine (in frazioni), per allinearle al menu nel CSS
    t = np.nonzero(quadri[0][1][box[1]:box[3], box[0]:box[2]] > 0.5)
    bw, bh = box[2] - box[0], box[3] - box[1]
    print('tubi accesi: x %.3f–%.3f, y %.3f–%.3f; altezza/larghezza %.4f' % (t[1].min() / bw, t[1].max() / bw, t[0].min() / bh, t[0].max() / bh, bh / bw))


if __name__ == '__main__':
    main(*sys.argv[1:2])
