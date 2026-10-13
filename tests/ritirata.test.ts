import { describe, expect, it } from 'vitest';
import { ROBIN_FUGA_S, ROBIN_SCENDE_S, ROBIN_TORNA_S, robinFrame, robinFugaFrames, robinStep } from '../src/app/ritirata.ts';

const DT = 1 / 60;

/** fa andare Robin verso target per t secondi, fotogramma per fotogramma: gli stati visti */
function run(s: { p: number; go: number }, target: 0 | 1, t: number, n = 6) {
  const seen: { p: number; go: number; frame: number }[] = [];
  for (let i = 0; i < Math.round(t / DT); i++) {
    s = robinStep(s.p, s.go, target, DT, n);
    seen.push({ ...s, frame: robinFrame(s.go, n) });
  }
  return { s, seen };
}

describe('la ritirata di Robin', () => {
  it('conta i fotogrammi del manifest di fila da 1', () => {
    expect(robinFugaFrames((k) => ['robin_ritirata_1', 'robin_ritirata_2', 'robin_ritirata_3'].includes(k))).toBe(3);
    expect(robinFugaFrames((k) => k === 'robin_ritirata_2')).toBe(0);
  });

  it('scacciato: prima la fuga, tutti i fotogrammi in ordine, poi la discesa dall\'ultimo', () => {
    const { s, seen } = run({ p: 1, go: 0 }, 0, ROBIN_FUGA_S + ROBIN_SCENDE_S + 0.1);
    expect(s).toEqual({ p: 0, go: 1 });
    const frames = seen.map((x) => x.frame);
    // ogni fotogramma si vede, in ordine, e nessuno torna indietro
    expect([...new Set(frames)]).toEqual([0, 1, 2, 3, 4, 5, 6]);
    expect(frames.every((f, i) => i === 0 || f >= frames[i - 1]!)).toBe(true);
    // finché fugge non scende; scende solo dall'ultimo fotogramma
    expect(seen.filter((x) => x.p < 1).every((x) => x.frame === 6)).toBe(true);
    // ogni fotogramma resta per qualche fotogramma del gioco (rapida ma continua: ~16 al secondo)
    for (let f = 1; f <= 5; f++) expect(frames.filter((x) => x === f).length).toBeGreaterThanOrEqual(3);
  });

  it('la fuga e la discesa stanno dentro il tempo della fuga nel gioco (1,6 s)', () => {
    const { s } = run({ p: 1, go: 0 }, 0, 1.6);
    expect(s.p).toBe(0);
  });

  it('quando torna sale nell\'ultimo fotogramma e poi la fuga va all\'indietro fino alla posa', () => {
    const { s, seen } = run({ p: 0, go: 1 }, 1, 1.2 + ROBIN_TORNA_S + 0.1);
    expect(s).toEqual({ p: 1, go: 0 });
    expect(seen.filter((x) => x.p < 1).every((x) => x.frame === 6)).toBe(true);
    const frames = seen.map((x) => x.frame);
    expect(frames.every((f, i) => i === 0 || f <= frames[i - 1]!)).toBe(true);
    expect(frames.at(-1)).toBe(0);
  });

  it('sparito, la fuga resta all\'ultimo fotogramma (pronto per tornare)', () => {
    expect(robinStep(0, 0.3, 0, DT, 6)).toEqual({ p: 0, go: 1 });
  });

  it('senza i fotogrammi fa come prima: scende subito', () => {
    const r = robinStep(1, 0, 0, 0.1, 0);
    expect(r.go).toBe(0);
    expect(r.p).toBeCloseTo(1 - 0.1 / ROBIN_SCENDE_S, 6);
    expect(robinFrame(0.9, 0)).toBe(0);
  });
});
