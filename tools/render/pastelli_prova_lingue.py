"""
Le prove dei disegni a pastello nelle lingue a cui il gioco potrebbe arrivare (scelta dell'utente del 12 ottobre sera:
spagnolo, francese, tedesco, portoghese, cinese, giapponese, coreano).

I testi qui sotto sono PROVE, DA FAR CONTROLLARE A UN MADRELINGUA: servono a vedere che la mano del bambino sappia
scriverli (le lettere accentate, i caratteri presi dallo scheletro di un font) e che ognuno stia al suo posto nel
disegno. Non vanno nel gioco: quelli veri, approvati, si mettono in SCRITTE di pastelli.py.

Uso: tools/.venv/bin/python tools/render/pastelli_prova_lingue.py <lingua ...|tutte> [--uscita docs/concept/lingue]
Per ogni lingua fa un provino due per due dei quattro disegni con scritte (pastelli_<lingua>_prova.jpg).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pastelli as P  # noqa: E402

PROVE = {
    'es': {'TROVAMI!': '¡ENCUÉNTRAME!', 'GUARDAMI!': '¡MÍRAME!', 'HO FAME!': '¡TENGO HAMBRE!', 'IL MIO TESORO': 'MI TESORO',
           'TANTI AUGURI': '¡FELIZ CUMPLEAÑOS!', 'AIUTO!': '¡SOCORRO!', 'AH AH AH': 'JA JA JA'},
    'fr': {'TROVAMI!': 'TROUVE-MOI!', 'GUARDAMI!': 'REGARDE-MOI!', 'HO FAME!': "J'AI FAIM!", 'AGOSTO 97': 'AOÛT 97',
           'IL MIO TESORO': 'MON TRÉSOR', 'TANTI AUGURI': 'JOYEUX ANNIVERSAIRE', 'AIUTO!': 'AU SECOURS!', 'AH AH AH': 'HA HA HA'},
    'de': {'TROVAMI!': 'FINDE MICH!', 'GUARDAMI!': 'GUCK MAL!', 'HO FAME!': 'ICH HAB HUNGER!', 'AGOSTO 97': 'AUGUST 97',
           'IL MIO TESORO': 'MEIN SCHATZ', 'TANTI AUGURI': 'ALLES GUTE!', 'AIUTO!': 'HILFE!', 'AH AH AH': 'HA HA HA'},
    'pt': {'TROVAMI!': 'ME ACHA!', 'GUARDAMI!': 'OLHA PRA MIM!', 'HO FAME!': 'TÔ COM FOME!', 'IL MIO TESORO': 'MEU TESOURO',
           'TANTI AUGURI': 'PARABÉNS!', 'AIUTO!': 'SOCORRO!', 'AH AH AH': 'HA HA HA'},
    'zh': {'TROVAMI!': '来找我！', 'GUARDAMI!': '看我！', 'HO FAME!': '我饿了！', 'AGOSTO 97': '97年8月', 'IL MIO TESORO': '我的宝贝',
           'TANTI AUGURI': '生日快乐', 'AIUTO!': '救命！', 'AH AH AH': '哈哈哈'},
    'ja': {'TROVAMI!': 'みつけて！', 'GUARDAMI!': 'みてて！', 'HO FAME!': 'おなかすいた！', 'AGOSTO 97': '97ねん8がつ',
           'IL MIO TESORO': 'ぼくのたからもの', 'TANTI AUGURI': 'おたんじょうび おめでとう', 'AIUTO!': 'たすけて！', 'AH AH AH': 'あはは'},
    'ko': {'TROVAMI!': '나 찾아봐!', 'GUARDAMI!': '나 좀 봐!', 'HO FAME!': '배고파!', 'AGOSTO 97': '97년 8월', 'IL MIO TESORO': '내 보물',
           'TANTI AUGURI': '생일 축하해!', 'AIUTO!': '살려줘!', 'AH AH AH': '하하하'},
}
CON_SCRITTE = ['piscina', 'tesoro', 'compleanno', 'sottacqua']


def provino(lingua, uscita):
    P.LINGUA = lingua
    P.SCRITTE[lingua] = PROVE[lingua]
    w, h = 800, round(P.H * 800 / P.W)
    foglio = Image.new('RGB', (2 * w + 30, 2 * h + 70), (32, 30, 34))
    for k, nome in enumerate(CON_SCRITTE):
        P._TRADOTTE.clear()
        P.DISEGNI[nome]()
        img, alfa = P.invecchia(P.componi(), **P.CARTA[nome])
        im = Image.fromarray((np.dstack([img, alfa]) * 255 + 0.5).astype(np.uint8), 'RGBA').resize((w, h), Image.LANCZOS)
        foglio.paste(im, (10 + (k % 2) * (w + 10), 50 + (k // 2) * (h + 10)), im)
        print(lingua, nome, 'tradotte:', len(P._TRADOTTE), flush=True)
    ImageDraw.Draw(foglio).text((12, 14), f'PROVA {lingua}: testi da far controllare a un madrelingua, non nel gioco', fill=(240, 190, 110))
    out = os.path.join(uscita, f'pastelli_{lingua}_prova.jpg')
    foglio.save(out, quality=86)
    print('provino', out, flush=True)


def main():
    argomenti = sys.argv[1:]
    uscita = 'docs/concept/lingue'
    if '--uscita' in argomenti:
        i = argomenti.index('--uscita')
        uscita = argomenti[i + 1]
        del argomenti[i:i + 2]
    lingue = list(PROVE) if not argomenti or argomenti == ['tutte'] else argomenti
    os.makedirs(uscita, exist_ok=True)
    for lingua in lingue:
        provino(lingua, uscita)


if __name__ == '__main__':
    main()
