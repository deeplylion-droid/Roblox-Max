import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fogLayerKeys, layerSeries, loadLayer, type LayerInfo, type Manifest } from '../src/engine/assets.ts';
import type { GL } from '../src/engine/gl.ts';
import { jumpscareFrames, loadNightAssets, swapFogAssets } from '../src/app/overlays.ts';

// L'opzione «Nebbia»: due serie di immagini. Gli strati e i jumpscare che hanno la voce `senza` cambiano serie, gli
// altri restano uguali (un lavoro a metà non rompe niente).

const pass = (file: string) => ({ file, scale: 1, res: 1 });

function strato(nome: string, senza: boolean): LayerInfo {
  const p = { ambient: pass(`${nome}_ambient.webp`), lamp: pass(`${nome}_lamp.webp`) };
  const s = { ambient: pass(`${nome}_ambient_senza.webp`), lamp: pass(`${nome}_lamp_senza.webp`) };
  return { space: 'boat', yaw: 0, rect: [10, 20, 110, 220], passes: p, ...(senza ? { senza: { passes: s } } : {}) } as unknown as LayerInfo;
}

const man = {
  pano: { width: 8192, height: 2139, latMin: -40, latMax: 50 },
  layers: {
    world: { ...strato('world', true), space: 'world', rect: [0, 0, 8192, 2139], data: 'world_data.webp', senza: { passes: strato('world', true).senza!.passes, data: 'world_data_senza.webp' } },
    boat: strato('boat', true),
    gulpy_pretende: strato('gulpy_pretende', true),
    gulpy_mascella_chiusa: { ...strato('gulpy_mascella_chiusa', true), base: 'gulpy_pretende' },
    // un mostro non ancora rifatto con la nebbia: uguale nelle due serie
    molly_destra: strato('molly_destra', false),
    rod0: strato('rod0', false),
  },
} as unknown as Manifest;

/** Un contesto WebGL finto: ogni texture è un oggetto con un numero; tiene il conto di quelle cancellate. */
function fakeGl() {
  let n = 0;
  const deleted: unknown[] = [];
  const gl = new Proxy(
    {
      createTexture: () => ({ id: ++n }),
      deleteTexture: (t: unknown) => deleted.push(t),
    } as Record<string, unknown>,
    { get: (o, k) => (k in o ? o[k as string] : typeof k === 'string' && k === k.toUpperCase() ? 1 : () => undefined) },
  );
  return { gl: gl as unknown as GL, deleted };
}

let chiesti: string[] = [];
let overlays: unknown = {};

beforeEach(() => {
  chiesti = [];
  vi.stubGlobal('fetch', async (url: string) => {
    const f = url.replace(/^.*img\//, '');
    chiesti.push(f);
    if (f === 'overlays.json') return new Response(JSON.stringify(overlays));
    if (f.endsWith('.json')) return new Response('', { status: 404 });
    return new Response('x');
  });
  vi.stubGlobal('createImageBitmap', async () => ({ close() {} }));
});
afterEach(() => vi.unstubAllGlobals());

describe('strati nelle due serie', () => {
  it('con la nebbia spenta prende i file senza; gli strati senza la voce restano uguali', () => {
    expect(layerSeries(man.layers.gulpy_pretende!, true).passes.ambient!.file).toBe('gulpy_pretende_ambient_senza.webp');
    expect(layerSeries(man.layers.gulpy_pretende!, false).passes.ambient!.file).toBe('gulpy_pretende_ambient.webp');
    expect(layerSeries(man.layers.molly_destra!, true)).toBe(man.layers.molly_destra);
    // riquadro, yaw e base sono quelli dello strato: la toppa resta allineata alla sua base
    const t = layerSeries(man.layers.gulpy_mascella_chiusa!, true);
    expect(t.rect).toEqual([10, 20, 110, 220]);
    expect(t.base).toBe('gulpy_pretende');
    expect(layerSeries(man.layers.world!, true).data).toBe('world_data_senza.webp');
  });

  it('cambiano serie tutti gli strati caricati che hanno la voce senza, non solo il mondo e la barca', () => {
    const caricati = ['world', 'boat', 'rod0', 'gulpy_pretende', 'gulpy_mascella_chiusa', 'molly_destra', 'dive_x'];
    expect(fogLayerKeys(man, caricati)).toEqual(['world', 'boat', 'gulpy_pretende', 'gulpy_mascella_chiusa']);
  });

  it('loadLayer carica i file della serie scelta', async () => {
    const { gl } = fakeGl();
    await loadLayer(gl, man, 'gulpy_mascella_chiusa', true);
    expect(chiesti.sort()).toEqual(['gulpy_mascella_chiusa_ambient_senza.webp', 'gulpy_mascella_chiusa_lamp_senza.webp']);
    chiesti = [];
    await loadLayer(gl, man, 'molly_destra', true);
    expect(chiesti.sort()).toEqual(['molly_destra_ambient.webp', 'molly_destra_lamp.webp']);
  });
});

describe('jumpscare nelle due serie', () => {
  const fr = (k: string, s = '') => Array.from({ length: 3 }, (_, i) => ({ file: `js_${k}_0${i}${s}.webp`, scale: 1 }));
  beforeEach(() => {
    overlays = {
      tarp: { base: { file: 'tarp_base.webp', scale: 1 }, glow: { file: 'tarp_glow.webp', scale: 1 }, aspect: 1.7778 },
      jumpscares: {
        gulpy: { frames: fr('gulpy'), fps: 10, aspect: 1.7778, senza: { frames: fr('gulpy', '_senza') } },
        madre: { frames: fr('madre'), fps: 10, aspect: 1.7778, senza: { frames: fr('madre', '_senza') } },
        // non ancora rifatto: uguale nelle due serie
        molly: { frames: fr('molly'), fps: 10, aspect: 1.7778 },
      },
    };
  });

  it('jumpscareFrames sceglie la serie solo se c’è', () => {
    const j = (overlays as { jumpscares: Record<string, Parameters<typeof jumpscareFrames>[0]> }).jumpscares;
    expect(jumpscareFrames(j.gulpy!, true)[0]!.file).toBe('js_gulpy_00_senza.webp');
    expect(jumpscareFrames(j.gulpy!, false)[0]!.file).toBe('js_gulpy_00.webp');
    expect(jumpscareFrames(j.molly!, true)[0]!.file).toBe('js_molly_00.webp');
  });

  it('all’avvio carica la serie dell’opzione; a notte in corso la cambia e libera le texture vecchie', async () => {
    const { gl, deleted } = fakeGl();
    const assets = await loadNightAssets(gl, true);
    expect(chiesti).toContain('js_gulpy_00_senza.webp');
    expect(chiesti).toContain('js_madre_02_senza.webp');
    expect(chiesti).not.toContain('js_gulpy_00.webp');
    const vecchi = assets.jumpscares.gulpy!.frames.map((f) => f.tex);
    const molly = assets.jumpscares.molly;
    chiesti = [];
    await swapFogAssets(gl, assets, false);
    expect(chiesti.sort()).toEqual([...fr('gulpy'), ...fr('madre')].map((f) => f.file).sort());
    // la Madre resta 'mother' nel gioco
    expect(assets.jumpscares.mother!.frames).toHaveLength(3);
    expect(deleted).toEqual(expect.arrayContaining(vecchi));
    // Molly, senza la serie senza nebbia, non si ricarica
    expect(assets.jumpscares.molly).toBe(molly);
    // e si torna indietro
    chiesti = [];
    await swapFogAssets(gl, assets, true);
    expect(chiesti).toContain('js_gulpy_01_senza.webp');
  });
});
