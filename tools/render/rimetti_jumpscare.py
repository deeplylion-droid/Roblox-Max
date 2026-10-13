"""Rimette nel gioco i fotogrammi con la nebbia di un jumpscare ricomposti (per esempio con JS_RIPRENDI=1 dopo una
ripulitura dello sfondo), quando la serie senza nebbia c'è già: copia solo i js_<chi>_*.webp nuovi e le loro scale in
overlays.json. La serie senza resta com'è (mostri_due_serie.py la prima volta la crea; rilanciarlo non la tocca, ma
questo non controlla altro che i fotogrammi).

Uso: python3 tools/render/rimetti_jumpscare.py <cartella_render> <radice del repository> <chi> [<chi> ...]
"""
import json
import os
import shutil
import sys

src, repo, chi = sys.argv[1], sys.argv[2], sys.argv[3:]
img = os.path.join(repo, 'public', 'assets', 'img')
p = os.path.join(img, 'overlays.json')
ov = json.load(open(p))
rov = json.load(open(os.path.join(src, 'overlays.json')))
for k in chi:
    e, r = ov['jumpscares'][k], rov['jumpscares'][k]
    if 'senza' not in e or len(r['frames']) != len(e['frames']):
        raise SystemExit(f'{k}: manca la serie senza o cambiano i fotogrammi')
    t = os.path.getmtime(os.path.join(src, 'overlays.json'))
    if any(os.path.getmtime(os.path.join(src, f['file'])) > t + 120 for f in r['frames']):
        raise SystemExit(f'{k}: overlays.json della cartella dei render è più vecchio dei fotogrammi')
    for f in r['frames']:
        shutil.copy2(os.path.join(src, f['file']), os.path.join(img, f['file']))
    e['frames'] = r['frames']
    print(k, [f['scale'] for f in r['frames']])
with open(p, 'w') as f:
    f.write(json.dumps(ov, indent=1, sort_keys=True))
