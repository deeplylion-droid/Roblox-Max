"""Mette nel gioco le immagini con l'atmosfera tenendo quelle di prima come serie «senza nebbia» (l'opzione «Nebbia»).

Per il mondo e la barca (manifest.json), per i posti del binocolo scelti e per il telone (overlays.json):
- i file di adesso diventano <nome>_senza.webp e la voce prende `senza` con i loro file e scale (solo la prima volta:
  se `senza` c'è già, la serie senza nebbia resta quella e si sostituiscono solo i file con la nebbia);
- i file nuovi arrivano dalla cartella dei render (RENDER_OUT) coi nomi di sempre, con le loro scale;
- i posti del binocolo nuovi hanno `fog: 0` (la nebbia è già nel render), quelli senza nebbia la prendono dal motore;
- la voce `atmosfera` del manifest (nebbia del motore e bagliori).
Pano e riquadri restano quelli del gioco (una bozza a 2048 si stira sugli stessi riquadri).

Uso: python3 tools/render/atmosfera_due_serie.py <cartella_render> <radice del repository> [--mondo] [--barca] [--luoghi a,b,c] [--telone]
                              [--densita x] [--gain x] [--radius x]
"""
import argparse
import json
import os
import shutil
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('src')
ap.add_argument('worktree')
ap.add_argument('--mondo', action='store_true')
ap.add_argument('--barca', action='store_true')
ap.add_argument('--luoghi', default='')
ap.add_argument('--telone', action='store_true')
ap.add_argument('--densita', type=float, default=1 / 50000)
ap.add_argument('--gain', type=float, default=0.6)
ap.add_argument('--radius', type=float, default=2.0)
a = ap.parse_args()

src = Path(a.src)
img = Path(a.worktree) / 'public' / 'assets' / 'img'


def senza_name(fn: str) -> str:
    stem, ext = os.path.splitext(fn)
    return f'{stem}_senza{ext}'


def keep_old(fn: str) -> str:
    """Il file di adesso diventa <nome>_senza (se non c'è già) e torna il nuovo nome."""
    new = senza_name(fn)
    if not (img / new).exists():
        shutil.move(img / fn, img / new)
    return new


def load(p: Path):
    return json.load(open(p))


def dump(p: Path, d) -> None:
    with open(p, 'w') as f:
        f.write(json.dumps(d, indent=1, sort_keys=True))


man = load(img / 'manifest.json')
rman = load(src / 'manifest.json')
for key, on in (('world', a.mondo), ('boat', a.barca)):
    if not on:
        continue
    e = man['layers'][key]
    if 'senza' not in e:
        old_passes = {g: {**p, 'file': keep_old(p['file'])} for g, p in e['passes'].items()}
        senza = {'passes': old_passes}
        if e.get('data'):
            senza['data'] = keep_old(e['data'])
        e['senza'] = senza
    r = rman['layers'][key]
    for p in r['passes'].values():
        shutil.copy2(src / p['file'], img / p['file'])
    if r.get('data'):
        shutil.copy2(src / r['data'], img / r['data'])
        e['data'] = r['data']
    e['passes'] = r['passes']
    print(key, 'nebbia', {g: p['scale'] for g, p in r['passes'].items()}, '· senza', {g: p['file'] for g, p in e['senza']['passes'].items()})
man['atmosfera'] = {'fog': {'color': [0.003, 0.004, 0.006], 'density': a.densita}, 'glows': {'gain': a.gain, 'radius': a.radius}}
dump(img / 'manifest.json', man)

luoghi = [k for k in a.luoghi.split(',') if k]
if luoghi or a.telone:
    ov = load(img / 'overlays.json')
    rov = load(src / 'overlays.json')
    places = {p['key']: p for p in ov['binocular']['places']}
    rplaces = {p['key']: p for p in rov['binocular']['places']}
    for k in luoghi:
        p, r = places[k], rplaces[k]
        if p.get('foxy'):
            raise SystemExit(f'{k}: è un posto del Foxy, le sue viste senza nebbia vanno fatte a parte')
        if 'senza' not in p:
            p['senza'] = {'file': keep_old(p['file']), 'scale': p['scale']}
        shutil.copy2(src / r['file'], img / r['file'])
        p.update({'file': r['file'], 'scale': r['scale'], 'fog': 0})
        print('binocolo', k, 'scala', r['scale'], '· senza', p['senza']['file'])
    if a.telone:
        t, r = ov['tarp'], rov['tarp']
        if 'senza' not in t:
            t['senza'] = {'base': {**t['base'], 'file': keep_old(t['base']['file'])}, 'glow': {**t['glow'], 'file': keep_old(t['glow']['file'])}}
        for g in ('base', 'glow'):
            shutil.copy2(src / r[g]['file'], img / r[g]['file'])
            t[g] = r[g]
        print('telone', {g: r[g]['scale'] for g in ('base', 'glow')})
    dump(img / 'overlays.json', ov)
print('atmosfera', man['atmosfera'])
