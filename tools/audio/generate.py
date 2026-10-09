"""
Genera gli asset audio di SPLASHLAND IS CLOSED! (tutti sintetizzati, nessun campione esterno).

Uso:
  tools/.venv/bin/python tools/audio/generate.py                 # tutti gli id di docs/AUDIO.md
  tools/.venv/bin/python tools/audio/generate.py bell_toll 'lulu_*'   # solo alcuni (anche con * ?)
  opzioni: --spectro (PNG di controllo in tools/audio/cache/), --jobs N, --list

Uscite: public/assets/audio/<id>.ogg (Vorbis q6, 48 kHz) e public/assets/audio/manifest.json.
Ogni suono ha un seme fisso derivato dal suo id: il risultato è deterministico.
Dipendenze: numpy, scipy, soundfile (verifica con libvorbis), Pillow (spettrogrammi), ffmpeg con libvorbis.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import master  # noqa: E402
from dsp import rng_for  # noqa: E402
from sounds import load_all  # noqa: E402


def build(sid: str, spectro: bool) -> dict:
    reg = load_all()
    spec = reg[sid]
    t0 = time.time()
    raw = spec.fn(spec, rng_for(sid))
    y = master.finalize(raw, spec)
    res, dec = master.encode_and_verify(y, spec)
    if spectro:
        master.spectrogram_png(dec, os.path.join(master.CACHE, f'spec_{sid}.png'), title=sid)
    res['secs'] = time.time() - t0
    res['entry'] = master.manifest_entry(spec)
    return res


def fmt(r: dict) -> str:
    s = (f"{r['id']:<18} {r['duration']:7.3f}s  {r['channels']}ch  peak {r['peak_db']:6.2f}  "
         f"rms {r['rms_db']:6.1f}  act {r['active_rms_db']:6.1f}  head {r['head_ms']:4.1f}ms")
    if 'jump_ratio' in r:
        s += (f"  loop: jump {r['jump_ratio']:.2f}x  seam {r['seam_pct']:.0f}%"
              f" ({r['seam_click_db']:.0f} vs {r['ref_click_db']:.0f} dB)")
    return s + f"  [{r['secs']:.1f}s]"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('ids', nargs='*', help='id o pattern (es. creak_*); vuoto = tutti')
    ap.add_argument('--spectro', action='store_true', help='scrive gli spettrogrammi PNG in tools/audio/cache/')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    reg = load_all()
    if a.list:
        for sid, s in reg.items():
            print(f'{sid:<18} {s.dur:6.2f}s {s.channels}ch loop={s.loop} {s.category}')
        return
    if a.ids:
        ids = [sid for sid in reg if any(fnmatch.fnmatch(sid, p) for p in a.ids)]
        if not ids:
            sys.exit(f'nessun id corrisponde a {a.ids}')
    else:
        ids = list(reg)
    t0 = time.time()
    results = []
    if a.jobs > 1 and len(ids) > 1:
        with ProcessPoolExecutor(a.jobs) as ex:
            futs = {sid: ex.submit(build, sid, a.spectro) for sid in ids}
            for sid in ids:
                r = futs[sid].result()
                print(fmt(r), flush=True)
                results.append(r)
    else:
        for sid in ids:
            r = build(sid, a.spectro)
            print(fmt(r), flush=True)
            results.append(r)
    master.write_manifest({r['id']: r['entry'] for r in results}, replace=not a.ids)
    print(f'{len(results)} suoni in {time.time() - t0:.1f}s → {master.OUT}')


if __name__ == '__main__':
    main()
