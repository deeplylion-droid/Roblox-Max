import { existsSync } from 'node:fs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { RITRATTI, mostriDellaNotte, ritrattoSrc, scegliRitratto } from '../src/app/ritratti.ts';
import { loadSave, meet } from '../src/app/save.ts';
import { EXTRA_NIGHT, NIGHTS, extraLevels, extraNight } from '../src/game/config.ts';

describe('Il ritratto del menu principale', () => {
  it('al primo avvio, senza nessun mostro incontrato, Molly', () => {
    expect(scegliRitratto([], null)).toBe('molly');
    // anche se si sono incontrati solo mostri che il ritratto non ce l'hanno ancora
    expect(scegliRitratto(['foxy'], null)).toBe('molly');
  });

  it('poi uno dei mostri incontrati che ha il ritratto, diverso dall’ultima volta se ce n’è più d’uno', () => {
    const seen = [...RITRATTI];
    for (let i = 0; i < 20; i++) {
      const r = scegliRitratto(seen, 'molly', () => i / 20);
      expect(seen).toContain(r);
      if (seen.length > 1) expect(r).not.toBe('molly');
    }
  });

  it('ogni ritratto ha le sue tre immagini (ferma e i due fotogrammi dello scatto), Molly compresa', () => {
    expect(RITRATTI).toContain('molly');
    for (const m of RITRATTI) {
      const r = ritrattoSrc(m);
      for (const f of [r.calmo, ...r.scatti]) expect(existsSync(`public/${f}`), f).toBe(true);
    }
  });

  it('i file: il ritratto fermo e i due fotogrammi dello scatto', () => {
    expect(ritrattoSrc('molly')).toEqual({
      calmo: 'assets/img/ritratti/molly.webp',
      scatti: ['assets/img/ritratti/molly_scatto1.webp', 'assets/img/ritratti/molly_scatto2.webp'],
    });
  });

  it('i mostri di una notte: la prima ha Gulpy, Molly e Hatch; la notte extra solo quelli chiamati', () => {
    expect(mostriDellaNotte(NIGHTS[1]!)).toEqual(['gulpy', 'molly', 'hatch']);
    expect(mostriDellaNotte(NIGHTS[2]!)).toContain('robin');
    const lv = { ...extraLevels(0), lampy: 5 };
    expect(mostriDellaNotte(extraNight(lv))).toEqual(['lampy']);
    expect(EXTRA_NIGHT).toBe(7);
  });
});

describe('I mostri incontrati nel salvataggio', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('una notte che comincia aggiunge i suoi mostri, una volta sola', () => {
    vi.stubGlobal('localStorage', { getItem: () => null, setItem: () => {} });
    const d = loadSave();
    expect(d.seen).toEqual([]);
    meet(d, ['gulpy', 'molly', 'hatch']);
    meet(d, ['molly', 'robin']);
    expect(d.seen).toEqual(['gulpy', 'molly', 'hatch', 'robin']);
  });

  it('i salvataggi di prima: i mostri delle notti già vinte', () => {
    vi.stubGlobal('localStorage', { getItem: () => JSON.stringify({ version: 1, night: 3, current: 3 }), setItem: () => {} });
    expect(loadSave().seen).toEqual(['gulpy', 'molly', 'hatch', 'robin']);
    vi.stubGlobal('localStorage', { getItem: () => JSON.stringify({ version: 1, night: 3, seen: ['molly', 'nessuno'], ritratto: 'molly' }), setItem: () => {} });
    const d = loadSave();
    expect(d.seen).toEqual(['molly']);
    expect(d.ritratto).toBe('molly');
  });
});
