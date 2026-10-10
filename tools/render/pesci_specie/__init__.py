"""
Il registro delle specie del Catalogo per tools/render/pesci.py: raccoglie le voci dei cinque file di
famiglia (scheletrici, zombi, glitchati, corrotti, sanguinanti) in SPECIE = {id: Specie}.

Ogni file di famiglia è solo dati: una voce per specie (forma, aspetto, famiglia, piano corporeo, ed
eventuali extra). Le classi e gli aiuti sono in base.py, il brief per gli agenti delle famiglie in PIANO.md.
Gli id sono quelli di src/game/catalog.ts (che qui si legge soltanto, per controllare).
"""
from __future__ import annotations

import os
import re

from . import corrotti, glitchati, sanguinanti, scheletrici, zombi
from .base import FAMIGLIE, PIANI, Specie

# i cinque prototipi approvati (uno per famiglia): devono restare identici
PROTOTIPI = ['sgombrato', 'orrata', 'salpa_sfasata', 'trigliocchi', 'barracruda']

# file di famiglia → famiglia del gioco
FILE_FAMIGLIA = {
    'scheletrici': 'skeletal',
    'zombi': 'zombie',
    'glitchati': 'glitch',
    'corrotti': 'corrupt',
    'sanguinanti': 'bleeding',
}

SPECIE: dict[str, Specie] = {}
ORIGINE: dict[str, str] = {}      # id → file di famiglia dove è registrata
for _mod in (scheletrici, zombi, glitchati, corrotti, sanguinanti):
    _nome = _mod.__name__.rsplit('.', 1)[-1]
    for _id, _sp in _mod.SPECIE.items():
        if _id in SPECIE:
            raise ValueError(f'specie {_id!r} registrata due volte ({ORIGINE[_id]} e {_nome})')
        if _sp.famiglia not in FAMIGLIE:
            raise ValueError(f'{_id}: famiglia {_sp.famiglia!r} sconosciuta (una di {FAMIGLIE})')
        if _sp.piano not in PIANI:
            raise ValueError(f'{_id}: piano {_sp.piano!r} sconosciuto (uno di {sorted(PIANI)})')
        SPECIE[_id] = _sp
        ORIGINE[_id] = _nome

_RADICE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
_CATALOGO_TS = os.path.join(_RADICE, 'src', 'game', 'catalog.ts')
_STR = r"'((?:[^'\\]|\\.)*)'"


def catalogo() -> dict:
    """Le voci di src/game/catalog.ts: id → {nome, vero, sci, famiglia, desc} (solo lettura)."""
    testo = open(_CATALOGO_TS, encoding='utf-8').read()
    voce = re.compile(r"f\(" + _STR + r",\s*" + _STR + r",\s*" + _STR + r",\s*\[" + _STR + r",\s*" + _STR + r",\s*" + _STR +
                      r"\],\s*'(\w+)',\s*'(\w+)',\s*\[[^\]]*\],\s*'(\w+)',\s*[\d.]+,\s*" + _STR, re.S)
    out = {}
    for m in voce.finditer(testo):
        fid, nome, _en, vero, _vero_en, sci, fam, _rar, _pull, desc = m.groups()
        pulisci = (lambda s: s.replace("\\'", "'"))
        out[fid] = {'nome': pulisci(nome), 'vero': pulisci(vero), 'sci': sci, 'famiglia': fam, 'desc': pulisci(desc)}
    return out


def controlla(stampa=print) -> list:
    """Controlla il registro contro il catalogo: id sconosciuti, famiglie diverse da quelle del gioco, e
    quante specie mancano per famiglia. Restituisce la lista dei problemi."""
    cat = catalogo()
    problemi = []
    for fid, sp in SPECIE.items():
        if fid not in cat:
            problemi.append(f'{fid}: non è nel catalogo (src/game/catalog.ts)')
            continue
        attesa = cat[fid]['famiglia']
        if FILE_FAMIGLIA[ORIGINE[fid]] != attesa:
            problemi.append(f'{fid}: è in {ORIGINE[fid]}.py ma nel catalogo è {attesa}')
        if sp.famiglia not in (attesa, 'normale'):
            problemi.append(f'{fid}: famiglia {sp.famiglia} ma nel catalogo è {attesa}')
    for nome, fam in FILE_FAMIGLIA.items():
        tutte = [k for k, v in cat.items() if v['famiglia'] == fam]
        fatte = [k for k in tutte if k in SPECIE and SPECIE[k].famiglia == fam]
        prova = [k for k in tutte if k in SPECIE and SPECIE[k].famiglia == 'normale']
        mancano = [k for k in tutte if k not in SPECIE]
        stampa(f'{nome:12s} {len(fatte):2d}/{len(tutte)} fatte, {len(prova)} solo come prova del piano (normale), '
               f'mancano {len(mancano)}: {", ".join(mancano)}')
    for p in problemi:
        stampa('  !', p)
    return problemi
