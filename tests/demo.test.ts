import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DISEGNI_ALBA } from '../src/app/disegni.ts';
import { ARRIVAL } from '../src/game/config.ts';
import { ARRIVO, DISEGNI, elenco, fileIn, pianoDemo, type Manifesti } from '../scripts/demo.ts';

const leggi = (f: string) => JSON.parse(readFileSync('public/assets/' + f, 'utf8'));
const manifesti = (): Manifesti => ({
  img: leggi('img/manifest.json'),
  overlays: leggi('img/overlays.json'),
  immersioni: leggi('img/immersioni.json'),
  audio: leggi('audio/manifest.json'),
});
const FILE = elenco('public/assets');
/** i file che i manifest nominano, rispetto ad assets/ */
function usati(m: Manifesti): Set<string> {
  const out = new Set<string>();
  for (const x of [m.img, m.overlays, m.immersioni]) for (const f of fileIn(x)) out.add('img/' + f);
  for (const f of fileIn(m.audio)) out.add('audio/' + f);
  return out;
}

describe('La demo leggera (scripts/demo.ts)', () => {
  it('le notti dei mostri e i disegni delle albe sono quelli del gioco', () => {
    expect(ARRIVO).toEqual(ARRIVAL);
    expect(DISEGNI).toEqual(DISEGNI_ALBA);
  });

  const p = pianoDemo(manifesti(), 2, FILE);
  const m = p.manifesti;

  it('restano le cose delle prime due notti', () => {
    const strati = Object.keys(m.img.layers);
    for (const k of ['world', 'boat', 'battery', 'battery_lit', 'gulpy_sale', 'hatch_conta', 'molly_destra', 'robin_secchio', 'robin_ritirata_1', 'sagoma_nebbia'])
      expect(strati, k).toContain(k);
    // il jumpscare della quota mancata (la Madre vista in parte) c'è dalla prima notte
    expect(Object.keys(m.overlays.jumpscares!).sort()).toEqual(['foxy', 'gulpy', 'hatch', 'molly', 'quota', 'robin']);
    expect(Object.keys(m.immersioni.places).sort()).toEqual(['grotta_grande', 'sotto_barca', 'tana_gulpy', 'tana_hatch', 'tana_molly', 'tana_robin']);
    // della Madre restano il jumpscare (la quota mancata) e la musica (la canzone finita al buio)
    for (const k of ['js_madre', 'mus_madre', 'js_foxy', 'foxy_near', 'sleep_robin', 'stir_robin', 'robin_steal', 'mus_title']) expect(m.audio, k).toHaveProperty(k);
  });

  it('se ne vanno i mostri delle notti dopo, la Madre, i finali e la notte extra', () => {
    const via = (k: string) => /^(archie|lampy|fangy|madre)_/.test(k);
    expect(Object.keys(m.img.layers).filter(via)).toEqual([]);
    expect(m.overlays.endings).toEqual({});
    expect(Object.keys(m.audio).filter((k) => via(k) || /^(js|sleep|stir)_(archie|lampy|fangy)$/.test(k) || k.startsWith('finale_'))).toEqual([]);
    for (const f of ['img/ritratti/archie.webp', 'img/ritratti/fangy_scatto2.webp', 'img/schede/molly.webp', 'img/schede/mother.webp', 'img/disegni/pastelli_compleanno.webp', 'img/disegni/pastelli_marcopolo.webp', 'img/disegni/pastelli_sottacqua_ja.webp', 'img/fin_ricordo.webp', 'img/js_archie_00.webp', 'img/js_madre_00_senza.webp', 'img/immersioni/tana_fangy_posa_ambient.webp', 'audio/madre_lullaby.ogg'])
      expect(p.via, f).toContain(f);
    for (const f of ['img/ritratti/molly.webp', 'img/ritratti/robin_scatto1.webp', 'img/disegni/pastelli_tesoro.webp', 'img/disegni/pastelli_piscina_en.webp', 'img/js_quota_00.webp', 'audio/js_madre.ogg'])
      expect(p.via, f).not.toContain(f);
  });

  it('nessun file che serve ancora viene cancellato, e quelli che servono ci sono tutti', () => {
    const resta = usati(m);
    expect(p.via.filter((f) => resta.has(f))).toEqual([]);
    expect([...resta].filter((f) => !FILE.includes(f))).toEqual([]);
  });

  it('il gioco intero resta com’è', () => {
    const tutto = pianoDemo(manifesti(), 7, FILE);
    expect(tutto.via).toEqual([]);
    expect(tutto.manifesti).toEqual(manifesti());
  });
});
