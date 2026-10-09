"""
Installa i render finali preparati da finale.sh (tools/render/cache/final_out) in public/assets/img.

Solo se tutti i job del panorama sono finiti bene (la larghezza del panorama è unica per tutti gli strati).
Copia il manifest del panorama con i file dei suoi strati e, delle sovrapposizioni, solo il telone:
i jumpscare e il binocolo restano quelli già in public (fatti dopo l'avvio della coda).
Uso: tools/.venv/bin/python tools/render/installa_finale.py
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'tools', 'render', 'cache', 'final_out')
PUB = os.path.join(ROOT, 'public', 'assets', 'img')
LOG = os.path.join(ROOT, 'tools', 'render', 'cache', 'finale.log')


def main():
    log = open(LOG).read()
    for j in ('world', 'boat', 'props', 'creature'):
        if not re.search(rf'^EXIT {j} 0$', log, re.M):
            sys.exit(f'il job {j} non è finito bene: niente installazione')
    files = set()

    def collect(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ('file', 'data') and isinstance(v, str):
                    files.add(v)
                collect(v)
        elif isinstance(x, list):
            for v in x:
                collect(v)
    man = json.load(open(os.path.join(OUT, 'manifest.json')))
    collect(man)
    ov_out = json.load(open(os.path.join(OUT, 'overlays.json')))
    ov_pub = json.load(open(os.path.join(PUB, 'overlays.json')))
    if 'tarp' in ov_out and re.search(r'^EXIT tarp 0$', log, re.M):
        ov_pub['tarp'] = ov_out['tarp']
        collect(ov_out['tarp'])
    for f in sorted(files):
        shutil.copy2(os.path.join(OUT, f), os.path.join(PUB, f))
    shutil.copy2(os.path.join(OUT, 'manifest.json'), os.path.join(PUB, 'manifest.json'))
    with open(os.path.join(PUB, 'overlays.json'), 'w') as f:
        json.dump(ov_pub, f, indent=1)
    print(len(files), 'file installati in', PUB)


if __name__ == '__main__':
    main()
