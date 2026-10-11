import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DiveRun, type DiveData } from '../src/app/dive_run.ts';

/** i dati veri del gioco (con i panorami segnaposto) */
const DATA = JSON.parse(readFileSync(new URL('../public/assets/img/immersioni.json', import.meta.url), 'utf8')) as DiveData;

function walk(r: DiveRun, seconds: number, dt = 0.1) {
  const ev: string[] = [];
  for (let t = 0; t < seconds; t += dt) {
    r.update(dt);
    ev.push(...r.drainEvents().map((e) => e.t));
  }
  return ev;
}

describe('Immersioni: i dati', () => {
  it('ogni passaggio porta a un posto che esiste, e ogni posto ha il suo panorama', () => {
    expect(DATA.places[DATA.start]).toBeDefined();
    for (const [id, p] of Object.entries(DATA.places)) {
      expect(p.pano.ambient ?? p.pano.lantern, id).toBeDefined();
      for (const l of p.links) if (l.to) expect(DATA.places[l.to], `${id} → ${l.to}`).toBeDefined();
    }
  });

  it('c’è una tana per ognuno dei sette mostri', () => {
    const dens = Object.values(DATA.places).map((p) => p.den).filter(Boolean);
    expect(new Set(dens)).toEqual(new Set(['gulpy', 'molly', 'hatch', 'robin', 'archie', 'lampy', 'fangy']));
  });
});

describe('Immersioni: le regole', () => {
  it('dopo la prima notte si vedono le tane dei tre e quella di Robin, vuota; le altre no', () => {
    const r = new DiveRun(DATA, 2, 1);
    r.enter('grotta_grande');
    const to = r.visibleLinks().map((l) => l.to).filter(Boolean);
    expect(to).toContain('tana_gulpy');
    expect(to).toContain('tana_robin');
    expect(to).not.toContain('tana_archie');
    expect(r.denState('robin')).toBe('empty');
    expect(r.denState('gulpy')).toBe('asleep');
    expect(r.denState('fangy')).toBe('locked');
  });

  it('giù si porta un pesce solo, e lo si lascia a un mostro solo (non al nuovo della notte)', () => {
    const r = new DiveRun(DATA, 3, 4);
    expect(r.fish).toBe(1);
    r.enter('grotta_grande');
    r.enter('tana_archie');
    expect(r.feed()).toBe('notHere'); // la tana di Archie è vuota: arriva stanotte
    r.enter('grotta_grande');
    r.enter('tana_molly');
    expect(r.feed()).toBe('ok');
    expect(r.fed).toBe('molly');
    expect(r.feed()).toBe('already');
  });

  it('senza pesci avanzati non si sfama nessuno', () => {
    const r = new DiveRun(DATA, 2, 0);
    r.enter('grotta_grande');
    r.enter('tana_gulpy');
    expect(r.feed()).toBe('noFish');
  });

  it('l’aria scende a ogni tana e basta per due; poi l’avviso e la risalita', () => {
    const r = new DiveRun(DATA, 5, 1);
    r.enter('grotta_grande');
    expect(walk(r, 60)).toEqual([]);
    expect(r.air).toBe(1); // nuotare nella grotta non costa
    r.enter('tana_gulpy');
    walk(r, DATA.air.denSeconds + 1);
    expect(r.air).toBeCloseTo(1 - DATA.air.perDen, 5);
    r.enter('grotta_grande');
    r.enter('tana_molly');
    r.enter('grotta_grande');
    expect(r.canEnter('tana_hatch')).toBe('tooFar');
    expect(r.canEnter('tana_molly')).toBe('ok'); // in una tana già vista si torna
    const ev = walk(r, DATA.air.reserveSeconds + 10);
    expect(ev).toEqual(['airLow', 'airOut']);
    expect(r.air).toBe(0);
  });
});

describe('Immersioni: le camerette', () => {
  it('sono inquadrature fisse che si girano di 30° per parte, e da ognuna si torna alla grotta grande', () => {
    for (const p of Object.values(DATA.places)) {
      if (!p.den) continue;
      expect(p.frame?.yawRange, p.den).toBe(30);
      // il panorama parziale copre il campo visivo (90°) più quanto si gira
      expect((p.lonMax ?? 180) - (p.lonMin ?? -180)).toBeGreaterThanOrEqual(90 + 2 * p.frame!.yawRange);
      expect(p.links.some((l) => l.to === 'grotta_grande')).toBe(true);
    }
    expect(DATA.places.grotta_grande!.frame).toBeUndefined();
  });
});

describe('Immersioni: la tana vuota e l’aria', () => {
  it('di solito la tana vuota conta fra le due; con emptyDenFree no (da confermare)', () => {
    const base = new DiveRun(DATA, 2, 1);
    base.enter('grotta_grande');
    base.enter('tana_robin');
    base.enter('grotta_grande');
    base.enter('tana_gulpy');
    base.enter('grotta_grande');
    expect(base.canEnter('tana_molly')).toBe('tooFar');

    const free = new DiveRun({ ...DATA, air: { ...DATA.air, emptyDenFree: true } }, 2, 1);
    free.enter('grotta_grande');
    free.enter('tana_robin');
    expect(free.air).toBe(1);
    free.enter('grotta_grande');
    free.enter('tana_gulpy');
    free.enter('grotta_grande');
    expect(free.canEnter('tana_molly')).toBe('ok');
    expect(free.dens).toEqual(['robin', 'gulpy']);
  });
});
