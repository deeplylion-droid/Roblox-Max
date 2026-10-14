"""
I testi della pagina Steam pronti da incollare su Steamworks: per ogni lingua un file in steam/testi/ con la
descrizione breve e quella lunga («About this game») col formato di Steam ([h2], [list], [i]…).

Li prende da steam/PAGINA.md (inglese e italiano) e da steam/PAGINA_lingue.md (le altre sette lingue): si cambia il
testo lì e si rifanno i file con questo script. Le righe dei paragrafi, che nei .md vanno a capo per leggerli meglio,
qui sono unite: su Steam ogni a capo resta un a capo.

Uso: tools/.venv/bin/python tools/steam_testi.py
"""
import os
import re

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEAM = os.path.join(RADICE, 'steam')
USCITA = os.path.join(STEAM, 'testi')

# il nome della lingua nei .md → (codice del gioco, la lingua come la chiama Steamworks, da approvare)
LINGUE = {
    'English': ('en', 'English', False),
    'Italiano': ('it', 'Italian', False),
    'Español': ('es', 'Spanish - Spain', True),
    'Français': ('fr', 'French', True),
    'Deutsch': ('de', 'German', True),
    'Português (Brasil)': ('pt', 'Portuguese - Brazil', True),
    '简体中文': ('zh', 'Simplified Chinese', True),
    '日本語': ('ja', 'Japanese', True),
    '한국어': ('ko', 'Korean', True),
}
# cinese, giapponese e coreano senza spazi fra le righe unite (il coreano ha gli spazi fra le parole, ma i suoi
# paragrafi nei .md stanno su una riga sola)
CJK = re.compile(r'[　-ヿ㐀-鿿＀-￯가-힯]')


def unisci(righe):
    """Le righe di un paragrafo in una sola."""
    out = ''
    for r in (r.strip() for r in righe):
        if out and not (CJK.match(out[-1]) or CJK.match(r[:1])):
            out += ' '
        out += r
    return out


def in_linea(s):
    """Grassetto e corsivo dentro una riga."""
    s = re.sub(r'\*\*(.+?)\*\*', r'[b]\1[/b]', s)
    return re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'[i]\1[/i]', s)


def bbcode(testo):
    """Il testo di una descrizione lunga (Markdown semplice) col formato di Steam."""
    blocchi = [b.split('\n') for b in re.split(r'\n\s*\n', testo.strip())]
    out = []
    for righe in blocchi:
        if righe[0].startswith('- '):
            voci = []
            for r in righe:
                if r.startswith('- '):
                    voci.append([r[2:]])
                else:
                    voci[-1].append(r)
            out.append('[list]\n' + '\n'.join('[*]' + in_linea(unisci(v)) for v in voci) + '\n[/list]')
            continue
        p = unisci(righe)
        if re.fullmatch(r'\*\*[^*]+\*\*', p):
            out.append('[h2]' + p[2:-2] + '[/h2]')
        elif re.fullmatch(r'\*[^*]+\*', p):
            out.append('[i]' + p[1:-1] + '[/i]')
        else:
            out.append(in_linea(p))
    # dopo un titolo niente riga vuota: Steam lo mette già staccato
    testo = ''
    for i, b in enumerate(out):
        if i:
            testo += '\n' if out[i - 1].startswith('[h2]') else '\n\n'
        testo += b
    return testo


def sezione(md, titolo, fine=None):
    """Il testo fra il titolo «## titolo» e il «## » dopo."""
    a = md.index('\n## ' + titolo)
    a = md.index('\n', a + 1)
    b = md.find('\n## ', a)
    return md[a:b if b >= 0 else len(md)]


def brevi(testo):
    """Le descrizioni brevi: «**Lingua** (N caratteri)» e la citazione sotto."""
    out = {}
    for m in re.finditer(r'\*\*([^*]+)\*\* \(\d+ caratteri\)\n\n((?:> .*\n?)+)', testo):
        out[m.group(1)] = unisci(r[2:] for r in m.group(2).strip().split('\n'))
    return out


def lunghe(testo):
    """Le descrizioni lunghe: una per «### Lingua»."""
    parti = re.split(r'\n### (.+)\n', testo)
    return {parti[i].strip(): parti[i + 1] for i in range(1, len(parti) - 1, 2)}


def main():
    breve, lunga = {}, {}
    for nome in ('PAGINA.md', 'PAGINA_lingue.md'):
        with open(os.path.join(STEAM, nome), encoding='utf-8') as f:
            md = f.read()
        breve.update(brevi(sezione(md, 'Descrizione breve')))
        lunga.update(lunghe(sezione(md, 'Descrizione lunga')))
    os.makedirs(USCITA, exist_ok=True)
    for nome, (codice, steam, da_approvare) in LINGUE.items():
        b = breve[nome]
        if len(b) > 300:
            raise SystemExit(f'{nome}: la descrizione breve ha {len(b)} caratteri (massimo 300)')
        testa = [f'SPLASHLAND IS CLOSED! · i testi della pagina Steam · {nome}',
                 f'Su Steamworks: Store page admin, lingua «{steam}».']
        if da_approvare:
            testa.append('DA APPROVARE: traduzione automatica, da far rileggere a un madrelingua prima di incollarla.')
        corpo = '\n'.join(testa) + (
            f'\n\n===== Descrizione breve (Short description, {len(b)} caratteri su 300) =====\n\n{b}\n'
            f'\n===== Descrizione lunga (About this game) =====\n\n{bbcode(lunga[nome])}\n')
        with open(os.path.join(USCITA, codice + '.txt'), 'w', encoding='utf-8') as f:
            f.write(corpo)
        print(codice, len(b))


if __name__ == '__main__':
    main()
