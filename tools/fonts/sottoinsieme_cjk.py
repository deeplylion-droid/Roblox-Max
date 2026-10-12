"""
Il font del cinese, del giapponese o del coreano per il gioco, coi soli caratteri dei suoi testi (lingue a cui il gioco
potrebbe arrivare: scelta dell'utente del 12 ottobre sera). Un font intero di questi pesa 10-25 MB; il sottoinsieme
coi caratteri dei testi qualche centinaio di KB.

Prende Noto Serif (SC, JP o KR; OFL, da Google Fonts: è il fratello di Source Serif 4, il font dei testi del gioco),
lo riduce ai caratteri che escono da tools/fonts/testi_lingua.mjs (più la punteggiatura e le cifre) e lo scrive in
public/fonts/cjk-<lingua>.woff2. Poi la lingua va aggiunta a CJK_FONTS in src/app/fonts_lingua.ts.
Va rifatto ogni volta che cambiano i testi di quella lingua.

Uso: tools/.venv/bin/python tools/fonts/sottoinsieme_cjk.py <zh|ja|ko> [--testi file.txt]
(con --testi prende i caratteri da un file invece che dai testi del gioco: per le prove)
"""
import os
import subprocess
import sys
import urllib.request

from fontTools import subset

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))
GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl/'
FONT = {
    'zh': ('NotoSerifSC[wght].ttf', GF + 'notoserifsc/NotoSerifSC%5Bwght%5D.ttf'),
    'ja': ('NotoSerifJP[wght].ttf', GF + 'notoserifjp/NotoSerifJP%5Bwght%5D.ttf'),
    'ko': ('NotoSerifKR[wght].ttf', GF + 'notoserifkr/NotoSerifKR%5Bwght%5D.ttf'),
}
# sempre: la punteggiatura larga, le cifre, i segni che i testi potrebbero usare anche se oggi non ci sono
SEMPRE = '　、。，．・：；？！「」『』（）〈〉《》【】〜ー…‥0123456789０１２３４５６７８９'


def main():
    argomenti = sys.argv[1:]
    testi = None
    if '--testi' in argomenti:
        i = argomenti.index('--testi')
        testi = open(argomenti[i + 1], encoding='utf-8').read()
        del argomenti[i:i + 2]
    lingua = argomenti[0]
    nome, url = FONT[lingua]
    cache = os.path.join(RADICE, 'tools', 'render', 'cache', 'fonts')
    sorgente = os.path.join(cache, nome)
    if not os.path.exists(sorgente):
        os.makedirs(cache, exist_ok=True)
        urllib.request.urlretrieve(url, sorgente)
    if testi is None:
        testi = subprocess.run(['node', '--experimental-strip-types', '--no-warnings', os.path.join(QUI, 'testi_lingua.mjs'), lingua],
                               cwd=RADICE, check=True, capture_output=True, text=True).stdout
    caratteri = sorted(set(c for c in testi + SEMPRE if not c.isspace() or c == '　'))
    out = os.path.join(RADICE, 'public', 'fonts', f'cjk-{lingua}.woff2')
    opts = subset.Options()
    opts.flavor = 'woff2'
    opts.layout_features = ['*']
    opts.name_IDs = ['*']
    font = subset.load_font(sorgente, opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=''.join(caratteri))
    sub.subset(font)
    subset.save_font(font, out, opts)
    print(lingua, len(caratteri), 'caratteri ->', out, os.path.getsize(out) // 1024, 'KB')


if __name__ == '__main__':
    main()
