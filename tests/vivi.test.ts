import { describe, expect, it } from 'vitest';
import type { LayerInfo } from '../src/engine/assets.ts';
import { VIVI, Vivi, twitchEnvelope } from '../src/app/vivi.ts';

const base: LayerInfo = { space: 'boat', yaw: 0, rect: [100, 200, 300, 600], passes: {} };

/** fa andare le creature vive per `secs` secondi; restituisce chi ha scattato e quante gocce */
function run(v: Vivi, secs: number, o: { presence?: number; looked?: boolean; quiet?: boolean } = {}) {
  const twitched: string[] = [];
  let drips = 0;
  for (let t = 0; t < secs; t += 1 / 30) {
    v.update(1 / 30, { gulpy: o.presence ?? 1 }, () => o.looked ?? true, o.quiet ?? false, (id) => twitched.push(id), () => drips++);
  }
  return { twitched, drips };
}

describe('Le creature vive', () => {
  it('lo scatto arriva in fretta, resta un attimo e torna a zero', () => {
    expect(twitchEnvelope(-0.1)).toBe(0);
    expect(twitchEnvelope(0)).toBe(0);
    expect(twitchEnvelope(0.07)).toBeCloseTo(1);
    expect(twitchEnvelope(0.2)).toBe(1);
    expect(twitchEnvelope(0.6)).toBeGreaterThan(0);
    expect(twitchEnvelope(0.6)).toBeLessThan(1);
    expect(twitchEnvelope(0.9)).toBe(0);
  });

  it('scatta solo se la guardi, dopo che è tutta fuori da un po’, e non troppo spesso', () => {
    expect(run(new Vivi(() => 0.5), 20, { looked: false }).twitched).toEqual([]);
    expect(run(new Vivi(() => 0.5), 20, { quiet: true }).twitched).toEqual([]);
    expect(run(new Vivi(() => 0.5), 20, { presence: 0.5 }).twitched).toEqual([]);
    const n = run(new Vivi(() => 0.5), 30).twitched.length;
    // la prima dopo 7 s, poi una ogni 9,5 s
    expect(n).toBeGreaterThanOrEqual(2);
    expect(n).toBeLessThanOrEqual(4);
  });

  it('chi è uscito dall’acqua gocciola, piano', () => {
    const { drips } = run(new Vivi(() => 0.5), 20);
    expect(drips).toBeGreaterThan(5);
    expect(drips).toBeLessThan(20);
    expect(run(new Vivi(() => 0.5), 20, { quiet: true }).drips).toBe(0);
  });

  it('il respiro è piccolo, attorno alla base della posa; senza la creatura niente warp', () => {
    const v = new Vivi(() => 0.5);
    expect(v.warp('gulpy', base)).toBeUndefined();
    run(v, 3);
    const w = v.warp('gulpy', base)!;
    expect(w.anchor).toEqual([200, 600]);
    expect(Math.abs(w.scale - 1)).toBeLessThanOrEqual(VIVI.gulpy!.amp + 1e-9);
    // il collo sta fra la base e la cima
    expect(w.neck).toBeGreaterThan(200);
    expect(w.neck).toBeLessThan(600);
  });
});
