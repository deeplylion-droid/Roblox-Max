import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DiveRun, type DiveData } from '../src/app/dive_run.ts';

/** i dati veri del gioco (con i panorami segnaposto) */
const DATA = JSON.parse(readFileSync(new URL('../public/assets/img/immersioni.json', import.meta.url), 'utf8')) as DiveData;

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

  it('l’aria basta per due tane: nuotare e restare nelle tane non costa; uscendo dalla seconda si risale', () => {
    const r = new DiveRun(DATA, 5, 1);
    r.enter('grotta_grande');
    r.enter('tana_gulpy');
    expect(r.outOfAirOnLeave()).toBe(false);
    expect(r.airRunningOut()).toBe(false);
    r.enter('grotta_grande');
    expect(r.airRunningOut()).toBe(false);
    r.enter('tana_molly');
    // nella seconda tana l'aria sta finendo: il respiro diventa affannoso (l'unico segnale)
    expect(r.airRunningOut()).toBe(true);
    // dalla seconda tana non si torna nella grotta: l'aria è finita (la presentazione fa partire la risalita)
    expect(r.outOfAirOnLeave()).toBe(true);
    expect(r.dens).toEqual(['gulpy', 'molly']);
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
    // anche sotto la barca è un'inquadratura fissa (deciso l'11 ottobre sera); si risale dalla cima dell'ancora
    const sb = DATA.places.sotto_barca!;
    expect(sb.frame?.yawRange).toBe(30);
    expect((sb.lonMax ?? 180) - (sb.lonMin ?? -180)).toBeGreaterThanOrEqual(150);
    expect(sb.links.some((l) => l.ascend)).toBe(true);
    // i passaggi stanno dentro l'inquadratura
    for (const l of sb.links) expect(Math.abs(l.yaw - sb.frame!.yaw)).toBeLessThanOrEqual(sb.frame!.yawRange + 45);
  });
});

describe('Immersioni: la tana vuota e l’aria', () => {
  it('la tana vuota del mostro nuovo non costa aria (deciso l’11 ottobre sera): si vedono lo stesso due mostri', () => {
    expect(DATA.air.emptyDenFree).toBe(true);
    const r = new DiveRun(DATA, 2, 1);
    r.enter('grotta_grande');
    r.enter('tana_robin');
    expect(r.outOfAirOnLeave()).toBe(false);
    expect(r.airRunningOut()).toBe(false); // la tana vuota non conta: il respiro resta calmo
    r.enter('grotta_grande');
    r.enter('tana_gulpy');
    expect(r.outOfAirOnLeave()).toBe(false);
    r.enter('grotta_grande');
    r.enter('tana_molly');
    expect(r.outOfAirOnLeave()).toBe(true);
    expect(r.dens).toEqual(['robin', 'gulpy', 'molly']);
  });

  it('senza emptyDenFree la tana vuota conta come le altre', () => {
    const r = new DiveRun({ ...DATA, air: { maxDens: 2 } }, 2, 1);
    r.enter('grotta_grande');
    r.enter('tana_robin');
    r.enter('grotta_grande');
    r.enter('tana_gulpy');
    expect(r.outOfAirOnLeave()).toBe(true);
  });
});
