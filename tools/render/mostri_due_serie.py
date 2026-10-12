"""Mette nel gioco i mostri e i jumpscare resi con l'atmosfera (ATMOSFERA=1), tenendo quelli di prima come serie
«senza nebbia» (l'opzione «Nebbia»), con la stessa convenzione di atmosfera_due_serie.py per il mondo e la barca.

Per ogni strato scelto (manifest.json → layers) e ogni jumpscare scelto (overlays.json → jumpscares):
- la prima volta i file di adesso diventano <nome>_senza.webp e la voce prende `senza` (strati: {'passes': …};
  jumpscare: {'frames': […]}) coi loro file e scale; se `senza` c'è già, la serie senza nebbia resta quella e si
  sostituiscono solo i file con la nebbia;
- i file nuovi arrivano dalla cartella dei render (RENDER_OUT) coi nomi di sempre, con le loro scale.
Il resto della voce (riquadro, yaw, occhi, pelo, base) resta quello del gioco: le inquadrature devono essere le stesse,
e se il riquadro o lo yaw del render nuovo sono diversi l'installazione si ferma (una toppa spostata di un pixel non
combacia più con la sua base). Si ferma anche se il manifest della cartella dei render è più vecchio dei file (le
scale non sono ancora scritte, vedi «Attenzione alle scale» in docs/ATMOSFERA.md).

Uso: python3 tools/render/mostri_due_serie.py <cartella_render> <radice del repository>
                              [--strati gulpy_sale,gulpy_pretende,...] [--mostri gulpy,molly,...] [--jumpscare gulpy,...]
                              [--prova]
--mostri prende tutti gli strati del mostro che ci sono nella cartella dei render (le pose e le toppe: <mostro>_*);
--prova controlla e dice cosa farebbe, senza toccare niente.
"""
import argparse
import json
import os
import shutil
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('src')
ap.add_argument('worktree')
ap.add_argument('--strati', default='')
ap.add_argument('--mostri', default='')
ap.add_argument('--jumpscare', default='')
ap.add_argument('--prova', action='store_true')
a = ap.parse_args()

src = Path(a.src)
img = Path(a.worktree) / 'public' / 'assets' / 'img'


def senza_name(fn: str) -> str:
    stem, ext = os.path.splitext(fn)
    return f'{stem}_senza{ext}'


def keep_old(fn: str) -> str:
    """Il file di adesso diventa <nome>_senza (se non c'è già) e torna il nuovo nome."""
    new = senza_name(fn)
    if not (img / new).exists() and not a.prova:
        shutil.move(img / fn, img / new)
    return new


def scale_scritte(manifest: Path, files) -> None:
    """Un file più nuovo del suo manifest ha ancora la scala del render di prima (come in atmosfera_due_serie.py)."""
    t = manifest.stat().st_mtime
    nuovi = [f.name for f in files if f.stat().st_mtime > t + 120]
    if nuovi:
        raise SystemExit(f'{manifest.name} è più vecchio di {", ".join(nuovi)}: le scale non sono ancora scritte, aspetta la fine del job')


def copy(f: str) -> None:
    if not a.prova:
        shutil.copy2(src / f, img / f)


def load(p: Path):
    return json.load(open(p))


def dump(p: Path, d) -> None:
    if a.prova:
        return
    with open(p, 'w') as f:
        f.write(json.dumps(d, indent=1, sort_keys=True))


man = load(img / 'manifest.json')
strati = [k for k in a.strati.split(',') if k]
mostri = [k for k in a.mostri.split(',') if k]
if mostri:
    rman = load(src / 'manifest.json')
    for m in mostri:
        trovati = sorted(k for k in rman['layers'] if k.startswith(m + '_') or k == m)
        if not trovati:
            raise SystemExit(f'{m}: nessuno strato nella cartella dei render')
        strati += [k for k in trovati if k not in strati]
if strati:
    rman = load(src / 'manifest.json')
    # prima tutti i controlli, poi si tocca qualcosa: un'installazione a metà lascerebbe una toppa senza la sua base
    for key in strati:
        e, r = man['layers'].get(key), rman['layers'].get(key)
        if e is None or r is None:
            raise SystemExit(f'{key}: manca nel {"gioco" if e is None else "render"}')
        if list(r['rect']) != list(e['rect']) or abs(float(r['yaw']) - float(e['yaw'])) > 1e-3:
            raise SystemExit(f'{key}: inquadratura diversa (riquadro {r["rect"]} yaw {r["yaw"]}, nel gioco {e["rect"]} yaw {e["yaw"]})')
        if r.get('base') != e.get('base'):
            raise SystemExit(f'{key}: base diversa ({r.get("base")} invece di {e.get("base")})')
        scale_scritte(src / 'manifest.json', [src / p['file'] for p in r['passes'].values()])
        if 'senza' not in e and any(not (img / p['file']).exists() for p in e['passes'].values()):
            raise SystemExit(f'{key}: mancano i file di adesso, da tenere come serie senza nebbia')
    for key in strati:
        e, r = man['layers'][key], rman['layers'][key]
        if 'senza' not in e:
            e['senza'] = {'passes': {g: {**p, 'file': keep_old(p['file'])} for g, p in e['passes'].items()}}
        for p in r['passes'].values():
            copy(p['file'])
        e['passes'] = r['passes']
        print(key, 'nebbia', {g: p['scale'] for g, p in r['passes'].items()}, '· senza', {g: p['file'] for g, p in e['senza']['passes'].items()})
    dump(img / 'manifest.json', man)

js = [k for k in a.jumpscare.split(',') if k]
if js:
    ov = load(img / 'overlays.json')
    rov = load(src / 'overlays.json')
    for k in js:
        e, r = ov['jumpscares'].get(k), rov.get('jumpscares', {}).get(k)
        if e is None or r is None:
            raise SystemExit(f'jumpscare {k}: manca nel {"gioco" if e is None else "render"}')
        if len(r['frames']) != len(e['frames']) or r['fps'] != e['fps'] or abs(r['aspect'] - e['aspect']) > 1e-3:
            raise SystemExit(f'jumpscare {k}: fotogrammi diversi ({len(r["frames"])} a {r["fps"]}/s, nel gioco {len(e["frames"])} a {e["fps"]}/s)')
        scale_scritte(src / 'overlays.json', [src / f['file'] for f in r['frames']])
    for k in js:
        e, r = ov['jumpscares'][k], rov['jumpscares'][k]
        if 'senza' not in e:
            e['senza'] = {'frames': [{**f, 'file': keep_old(f['file'])} for f in e['frames']]}
        for f in r['frames']:
            copy(f['file'])
        e['frames'] = r['frames']
        print('jumpscare', k, 'scale', [f['scale'] for f in r['frames']], '· senza', e['senza']['frames'][0]['file'], '…')
    dump(img / 'overlays.json', ov)
if a.prova:
    print('(prova: niente è stato toccato)')
