"""
Il relitto nel binocolo con la nebbia accesa (segnalazione dell'utente del 13 ottobre: «se guardi col binocolo la nave
affondata non vedi nemmeno i segni sullo scafo a causa del rumore della nebbia»). Il relitto è il posto più basso del
binocolo, sull'acqua: la foschia bassa lo copriva quasi tutto, le tacche sullo scafo e Soggy compresi.

Il relitto, i suoi segni, la lanterna col riflesso e Soggy si prendono in parte (FORZA) dalla stessa vista senza
nebbia, un po' più scura (GUADAGNO) perché la baia con la nebbia è più buia; il resto (il cielo, i monti, l'acqua e la
nebbia attorno) resta quello del render con la nebbia, così i bordi del riquadro combaciano ancora col mondo. Cosa è
«relitto» lo dice la vista senza nebbia: i pixel che si staccano dalla loro riga (l'acqua e il cielo sono quasi uguali
in orizzontale), più vicini dei monti (il mist nell'alfa) e dentro un'ellisse attorno al relitto e ai posti di Soggy.

Parte sempre dalle viste rese con la nebbia piena (se no ripeterlo schiarirebbe ogni volta di più): di base quelle
installate nel commit ORIGINALI, oppure quelle della cartella data con --da (per esempio dopo aver rifatto il
binocolo). Scrive bino_relitto.webp, bino_relitto_foxy0.webp e bino_relitto_foxy1.webp in public/assets/img (la
serie senza nebbia, `_senza`, non cambia; scale e manifest neppure).

Uso: tools/.venv/bin/python tools/render/relitto_nebbia.py [--da <cartella>] [--prova <cartella per le tavole>]
"""
import argparse
import io
import os
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
RADICE = os.path.dirname(os.path.dirname(QUI))
IMG = os.path.join(RADICE, 'public', 'assets', 'img')
# il commit in cui le viste del relitto con la nebbia piena erano nel gioco
ORIGINALI = 'adb26db'
VISTE = ('bino_relitto', 'bino_relitto_foxy0', 'bino_relitto_foxy1')
FORZA = 0.6
GUADAGNO = 0.8


def leggi(dati):
    """Una vista del binocolo: la luce (lineare, divisa per la scala: tex^4) e il mist nell'alfa."""
    a = np.asarray(Image.open(io.BytesIO(dati)).convert('RGBA')).astype(np.float32) / 255
    return a[..., :3] ** 4, a[..., 3]


def originale(nome, da):
    if da:
        with open(os.path.join(da, nome + '.webp'), 'rb') as f:
            return f.read()
    return subprocess.run(['git', '-C', RADICE, 'show', f'{ORIGINALI}:public/assets/img/{nome}.webp'], check=True, capture_output=True).stdout


def peso(senza, mist_senza):
    """Quanto prendere dalla vista senza nebbia (0..1): il relitto e Soggy sì, cielo, monti e acqua no."""
    H, W = mist_senza.shape
    lum = senza.mean(-1)
    riga = np.median(lum, axis=1, keepdims=True)
    stacco = np.clip((np.abs(lum - riga) / (riga + 0.004) - 0.45) / 0.35, 0, 1)
    # i monti e il cielo hanno il mist attorno a 0,5; il relitto e l'acqua davanti meno
    vicino = np.clip((0.48 - mist_senza) / 0.04, 0, 1)
    yy, xx = np.mgrid[:H, :W]
    e = ((xx / W - 0.50) / 0.20) ** 2 + ((yy / H - 0.42) / 0.30) ** 2
    ellisse = np.clip((1.0 - e) / 0.25, 0, 1)
    return gaussian_filter(stacco * vicino * ellisse, 2.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--da', help='cartella con le viste rese con la nebbia piena (di base: il commit ORIGINALI)')
    ap.add_argument('--prova', help='scrive qui una tavola prima/dopo invece di toccare il gioco')
    a = ap.parse_args()
    for nome in VISTE:
        nebbia, mist = leggi(originale(nome, a.da))
        with open(os.path.join(IMG, nome + '_senza.webp'), 'rb') as f:
            senza, mist_senza = leggi(f.read())
        w = peso(senza, mist_senza)[..., None]
        out = nebbia * (1 - FORZA * w) + senza * GUADAGNO * FORZA * w
        rgb8 = (np.clip(out, 0, 1) ** 0.25 * 255 + 0.5).astype(np.uint8)
        a8 = (mist * 255 + 0.5).astype(np.uint8)
        im = Image.fromarray(np.dstack([rgb8, a8]), 'RGBA')
        if a.prova:
            os.makedirs(a.prova, exist_ok=True)
            vedi = lambda x: Image.fromarray((np.clip((y := np.clip(x * 15, 0, None)) / (1 + y), 0, 1) ** (1 / 2.2) * 255).astype(np.uint8))
            tav = Image.new('RGB', (nebbia.shape[1], nebbia.shape[0] * 2))
            tav.paste(vedi(nebbia), (0, 0))
            tav.paste(vedi(out), (0, nebbia.shape[0]))
            tav.resize((tav.width // 2, tav.height // 2)).save(os.path.join(a.prova, nome + '.jpg'), quality=88)
        else:
            im.save(os.path.join(IMG, nome + '.webp'), 'WEBP', quality=90, method=6, exact=True)
        print(nome, 'peso medio', round(float(w.mean()), 4), 'massimo', round(float(w.max()), 3), flush=True)


if __name__ == '__main__':
    main()
