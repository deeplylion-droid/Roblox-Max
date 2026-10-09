import { describe, expect, it } from 'vitest';
import { HOUR_SECONDS, NIGHTS, YAW, type NightConfig } from '../src/game/config.ts';
import type { GameEvent } from '../src/game/events.ts';
import { NightSim } from '../src/game/sim.ts';
import { SKILLS, playNight } from '../src/game/bot.ts';

const N1 = NIGHTS[1]!;

function run(sim: NightSim, seconds: number, each?: (s: NightSim) => void, dt = 1 / 30): GameEvent[] {
  const out: GameEvent[] = [];
  for (let t = 0; t < seconds && sim.playing; t += dt) {
    each?.(sim);
    sim.update(dt);
    out.push(...sim.drainEvents());
  }
  return out;
}

/** notte senza mostri per provare la pesca */
function quiet(): NightConfig {
  const far = 1e9;
  return {
    ...N1,
    pappo: { ...N1.pappo, firstAt: far },
    lulu: { ...N1.lulu, firstAt: far },
    cucu: { ...N1.cucu, firstAt: far },
  };
}

describe('NightSim', () => {
  it('è deterministica a parità di seed e input', () => {
    const a = playNight(new NightSim(N1, 42), SKILLS.average!, 7);
    const b = playNight(new NightSim(N1, 42), SKILLS.average!, 7);
    expect(a.outcome).toEqual(b.outcome);
    expect(a.time).toBeCloseTo(b.time, 6);
    expect(a.fish).toBe(b.fish);
  });

  it('suona le ore e finisce alle 6 con la quota', () => {
    const sim = new NightSim(quiet(), 1);
    sim.fish = N1.quota;
    const ev = run(sim, HOUR_SECONDS * 6 + 1);
    expect(ev.filter((e) => e.t === 'hour').map((e) => (e as { hour: number }).hour)).toEqual([1, 2, 3, 4, 5, 6]);
    expect(sim.outcome).toEqual({ kind: 'won' });
  });

  it('senza quota alle 6 si sveglia la Madre', () => {
    const sim = new NightSim(quiet(), 1);
    run(sim, HOUR_SECONDS * 6 + 1);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'mother' });
  });

  it('pesca: lancio, abboccata, recupero e cattura', () => {
    const sim = new NightSim(quiet(), 3);
    sim.setView(YAW.rod, false);
    expect(sim.pressRod()).toBe(true);
    const ev = run(sim, 40, (s) => {
      if (s.fishing.phase === 'bite') s.pressRod();
      if (s.fishing.phase === 'reeling') s.setReelHeld(s.fishing.tension < 0.6 && !s.fishing.pulling);
      if (s.fishing.phase === 'idle' && s.landedCount === 0) s.pressRod();
    });
    expect(ev.some((e) => e.t === 'bite')).toBe(true);
    expect(ev.some((e) => e.t === 'landed')).toBe(true);
    expect(sim.landedCount).toBeGreaterThan(0);
  });

  it('tenere sempre premuto spezza il filo', () => {
    const sim = new NightSim(quiet(), 5);
    sim.setView(YAW.rod, false);
    sim.pressRod();
    const ev = run(sim, 30, (s) => {
      if (s.fishing.phase === 'bite') s.pressRod();
      s.setReelHeld(true);
    });
    expect(ev.some((e) => e.t === 'lineSnap')).toBe(true);
  });

  it('non si può lanciare guardando altrove', () => {
    const sim = new NightSim(quiet(), 5);
    sim.setView(180, false);
    expect(sim.pressRod()).toBe(false);
  });

  it('la lampara alta fa abboccare prima', () => {
    const wait = (lamp: 0 | 1 | 2) => {
      let total = 0;
      for (let seed = 1; seed <= 30; seed++) {
        const sim = new NightSim(quiet(), seed);
        sim.setLamp(lamp);
        sim.setView(YAW.rod, false);
        sim.pressRod();
        let t = 0;
        while (sim.fishing.phase !== 'bite' && t < 60) {
          sim.update(0.05);
          t += 0.05;
        }
        total += t;
      }
      return total / 30;
    };
    expect(wait(2)).toBeLessThan(wait(1));
    expect(wait(1)).toBeLessThan(wait(0));
  });

  it('Pappo affamato ti mangia se non lo sfami', () => {
    const sim = new NightSim(N1, 9);
    const ev = run(sim, N1.pappo.firstAt + 30);
    expect(ev.some((e) => e.t === 'pappo' && e.e === 'attack')).toBe(true);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'pappo' });
  });

  it('Pappo se ne va contento se gli lanci un pesce', () => {
    const sim = new NightSim(N1, 9);
    sim.fish = 3;
    sim.setView(0, false);
    const ev = run(sim, N1.pappo.firstAt + 30, (s) => {
      if (s.pappo.state === 'demanding') s.throwFish();
    });
    expect(ev.some((e) => e.t === 'pappo' && e.e === 'fed')).toBe(true);
    expect(sim.fish).toBe(2);
    expect(sim.pappo.state).not.toBe('attack');
  });

  it('Lulù se ne va se la guardi, affonda la barca se la ignori', () => {
    const cfg: NightConfig = { ...N1, pappo: { ...N1.pappo, firstAt: 1e9 }, cucu: { ...N1.cucu, firstAt: 1e9 } };
    const good = new NightSim(cfg, 11);
    good.fish = 9;
    const evGood = run(good, cfg.lulu.firstAt + 25, (s) => s.setView(s.lulu.state === 'peeking' ? s.lulu.yaw : 0, false));
    expect(evGood.some((e) => e.t === 'lulu' && e.e === 'giggle')).toBe(true);
    expect(good.playing).toBe(true);

    const bad = new NightSim(cfg, 11);
    run(bad, cfg.lulu.firstAt + 40, (s) => s.setView(s.lulu.side === 'left' ? 90 : -90, false));
    expect(bad.outcome).toEqual({ kind: 'dead', killer: 'lulu' });
  });

  it('Cucù ti trova se non sei sotto il telone, ti risparmia se ti nascondi', () => {
    const cfg: NightConfig = { ...N1, pappo: { ...N1.pappo, firstAt: 1e9 }, lulu: { ...N1.lulu, firstAt: 1e9 } };
    const bad = new NightSim(cfg, 13);
    run(bad, cfg.cucu.firstAt + 20);
    expect(bad.outcome).toEqual({ kind: 'dead', killer: 'cucu' });

    const good = new NightSim(cfg, 13);
    good.fish = 9;
    const ev = run(good, cfg.cucu.firstAt + 40, (s) => {
      if (s.cucu.state === 'counting' && s.cucu.count >= 3 && s.hide === 'out') s.toggleHide();
      if (s.cucu.state === 'away' && s.hide === 'in') s.toggleHide();
    });
    expect(ev.some((e) => e.t === 'cucu' && e.e === 'leave')).toBe(true);
    expect(good.playing).toBe(true);
  });

  it('uscire dal telone mentre Cucù cerca è fatale', () => {
    const cfg: NightConfig = { ...N1, pappo: { ...N1.pappo, firstAt: 1e9 }, lulu: { ...N1.lulu, firstAt: 1e9 } };
    const sim = new NightSim(cfg, 13);
    run(sim, cfg.cucu.firstAt + 40, (s) => {
      if (s.cucu.state === 'counting' && s.hide === 'out') s.toggleHide();
      if (s.cucu.state === 'searching' && s.hide === 'in') s.toggleHide();
    });
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'cucu' });
  });

  it('il frammento di lore garantito arriva alla quarta cattura', () => {
    const sim = new NightSim(quiet(), 21);
    sim.setView(YAW.rod, false);
    run(sim, 400, (s) => {
      if (s.fishing.phase === 'idle' || s.fishing.phase === 'bite') s.pressRod();
      if (s.fishing.phase === 'reeling') s.setReelHeld(s.fishing.tension < 0.6 && !s.fishing.pulling);
    });
    expect(sim.landedCount).toBeGreaterThanOrEqual(4);
    expect(sim.loreThisNight[0]).toBe('pacifier');
  });

  it('un bot esperto supera quasi sempre la prima notte', () => {
    let wins = 0;
    for (let seed = 1; seed <= 40; seed++) {
      const sim = playNight(new NightSim(N1, seed), SKILLS.expert!, seed);
      if (sim.outcome.kind === 'won') wins++;
    }
    expect(wins).toBeGreaterThanOrEqual(34);
  });
});
