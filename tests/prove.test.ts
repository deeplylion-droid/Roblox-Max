import { describe, expect, it } from 'vitest';
import { NIGHTS } from '../src/game/config.ts';
import { NightSim } from '../src/game/sim.ts';
import { JUMPSCARE_TASTI, notteDelTasto } from '../src/app/prove.ts';

// le scorciatoie delle build di prova (src/app/prove.ts): la notte vinta adesso e la morte con un jumpscare a scelta
describe('scorciatoie di prova', () => {
  it('Alt+V: la notte vinta adesso, con la quota piena, un pesce in più per le tane e le sei', () => {
    const sim = new NightSim(NIGHTS[2]!, 7);
    sim.update(1);
    sim.drainEvents();
    sim.provaVinci();
    expect(sim.outcome).toEqual({ kind: 'won' });
    // almeno un pesce oltre la quota: all'alba si può scendere nelle tane e lasciarlo a qualcuno
    expect(sim.fish).toBeGreaterThanOrEqual(NIGHTS[2]!.quota + 1);
    expect(sim.hour).toBe(6);
    expect(sim.drainEvents()).toContainEqual({ t: 'won' });
    // a notte finita non fa più niente
    sim.provaVinci();
    sim.provaMorte('gulpy');
    expect(sim.outcome).toEqual({ kind: 'won' });
    expect(sim.drainEvents()).toEqual([]);
  });

  it('Alt+Maiusc + numero: la morte con il jumpscare di quel mostro', () => {
    for (const [code, js] of Object.entries(JUMPSCARE_TASTI)) {
      const sim = new NightSim(NIGHTS[1]!, 3);
      sim.update(1);
      sim.drainEvents();
      sim.provaMorte(js.killer, js.cause);
      expect(sim.outcome, code).toEqual(js.cause ? { kind: 'dead', killer: js.killer, cause: js.cause } : { kind: 'dead', killer: js.killer });
      expect(sim.drainEvents(), code).toContainEqual({ t: 'dead', killer: js.killer });
    }
  });

  it('i dieci tasti dei jumpscare: ogni mostro, la Madre e la quota mancata', () => {
    expect(Object.keys(JUMPSCARE_TASTI).sort()).toEqual(['Digit0', 'Digit1', 'Digit2', 'Digit3', 'Digit4', 'Digit5', 'Digit6', 'Digit7', 'Digit8', 'Digit9']);
    const chi = Object.values(JUMPSCARE_TASTI).map((j) => `${j.killer}${j.cause ? ':' + j.cause : ''}`);
    expect(new Set(chi).size).toBe(10);
    expect(chi).toContain('mother:moved');
    expect(chi).toContain('mother');
  });

  it('Alt + numero sul titolo: la notte dal codice del tasto, qualunque sia la tastiera', () => {
    expect(notteDelTasto('Digit3')).toBe(3);
    expect(notteDelTasto('Digit7')).toBe(7);
    expect(notteDelTasto('KeyV')).toBe(0);
    expect(notteDelTasto('Numpad3')).toBe(0);
  });
});
