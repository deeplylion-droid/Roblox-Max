import { describe, expect, it } from 'vitest';
import { HOUR_SECONDS, NIGHTS, YAW, type NightConfig } from '../src/game/config.ts';
import type { GameEvent } from '../src/game/events.ts';
import { NightSim } from '../src/game/sim.ts';
import { SKILLS, playNight } from '../src/game/bot.ts';
import { Fishing } from '../src/game/fishing.ts';
import { Rng } from '../src/game/rng.ts';

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
    gulpy: { ...N1.gulpy, firstAt: far },
    molly: { ...N1.molly, firstAt: far },
    hatch: { ...N1.hatch, firstAt: far },
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

  it('Gulpy affamato ti mangia se non lo sfami', () => {
    const sim = new NightSim(N1, 9);
    const ev = run(sim, N1.gulpy.firstAt + 30);
    expect(ev.some((e) => e.t === 'gulpy' && e.e === 'attack')).toBe(true);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'gulpy' });
  });

  it('Gulpy se ne va contento se gli lanci un pesce', () => {
    const sim = new NightSim(N1, 9);
    sim.fish = 3;
    sim.setView(0, false);
    const ev = run(sim, N1.gulpy.firstAt + 30, (s) => {
      if (s.gulpy.state === 'demanding') s.throwFish();
    });
    expect(ev.some((e) => e.t === 'gulpy' && e.e === 'fed')).toBe(true);
    expect(sim.fish).toBe(2);
    expect(sim.gulpy.state).not.toBe('attack');
  });

  it('Molly se ne va se la guardi, affonda la barca se la ignori', () => {
    const cfg: NightConfig = { ...N1, gulpy: { ...N1.gulpy, firstAt: 1e9 }, hatch: { ...N1.hatch, firstAt: 1e9 } };
    const good = new NightSim(cfg, 11);
    good.fish = 9;
    const evGood = run(good, cfg.molly.firstAt + 25, (s) => s.setView(s.molly.state === 'peeking' ? s.molly.yaw : 0, false));
    expect(evGood.some((e) => e.t === 'molly' && e.e === 'giggle')).toBe(true);
    expect(good.playing).toBe(true);

    const bad = new NightSim(cfg, 11);
    run(bad, cfg.molly.firstAt + 40, (s) => s.setView(s.molly.side === 'left' ? 90 : -90, false));
    expect(bad.outcome).toEqual({ kind: 'dead', killer: 'molly' });
  });

  it('Hatch ti trova se non sei sotto il telone, ti risparmia se ti nascondi', () => {
    const cfg: NightConfig = { ...N1, gulpy: { ...N1.gulpy, firstAt: 1e9 }, molly: { ...N1.molly, firstAt: 1e9 } };
    const bad = new NightSim(cfg, 13);
    run(bad, cfg.hatch.firstAt + 20);
    expect(bad.outcome).toEqual({ kind: 'dead', killer: 'hatch' });

    const good = new NightSim(cfg, 13);
    good.fish = 9;
    const ev = run(good, cfg.hatch.firstAt + 40, (s) => {
      if (s.hatch.state === 'counting' && s.hatch.count >= 6 && s.hide === 'out') s.toggleHide();
      if (s.hatch.state === 'away' && s.hide === 'in') s.toggleHide();
    });
    expect(ev.some((e) => e.t === 'hatch' && e.e === 'leave')).toBe(true);
    expect(good.playing).toBe(true);
  });

  it('uscire dal telone mentre Hatch cerca è fatale', () => {
    const cfg: NightConfig = { ...N1, gulpy: { ...N1.gulpy, firstAt: 1e9 }, molly: { ...N1.molly, firstAt: 1e9 } };
    const sim = new NightSim(cfg, 13);
    run(sim, cfg.hatch.firstAt + 40, (s) => {
      if (s.hatch.state === 'counting' && s.hide === 'out') s.toggleHide();
      if (s.hatch.state === 'searching' && s.hide === 'in') s.toggleHide();
    });
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'hatch' });
  });

  it('il sonar avvisa qualche secondo prima che arrivi una creatura, dal lato giusto', () => {
    const cfg = { ...quiet(), molly: { ...N1.molly, firstAt: 30 } };
    const sim = new NightSim(cfg, 5);
    run(sim, 22);
    expect(sim.incoming()).toEqual([]);
    run(sim, 5);
    const inc = sim.incoming();
    expect(inc.length).toBe(1);
    expect(inc[0]!.who).toBe('molly');
    const yaw = inc[0]!.yaw;
    // quando bussa, lo fa dal lato annunciato
    const ev = run(sim, 6);
    const knock = ev.find((e) => e.t === 'molly' && e.e === 'knock');
    expect(knock).toBeTruthy();
    expect(sim.molly.yaw).toBe(yaw);
  });

  it('il frammento di lore garantito arriva alla quarta cattura', () => {
    const sim = new NightSim(quiet(), 21);
    sim.setView(YAW.rod, false);
    run(sim, 400, (s) => {
      if (s.fishing.phase === 'idle' || s.fishing.phase === 'bite') s.pressRod();
      if (s.fishing.phase === 'reeling') s.setReelHeld(s.fishing.tension < 0.6 && !s.fishing.pulling);
    });
    expect(sim.landedCount).toBeGreaterThanOrEqual(4);
    expect(sim.loreThisNight[0]).toBe('wristband');
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

// ───────────────────────── notte 2: Robin e la batteria ─────────────────────────

const N2 = NIGHTS[2]!;

/** notte 2 senza i mostri della prima notte (Robin solo se richiesto) */
function quiet2(robinAt = 1e9): NightConfig {
  const far = 1e9;
  return {
    ...N2,
    gulpy: { ...N2.gulpy, firstAt: far },
    molly: { ...N2.molly, firstAt: far },
    hatch: { ...N2.hatch, firstAt: far },
    robin: { ...N2.robin!, firstAt: robinAt },
  };
}

describe('Notte 2', () => {
  it('la prima notte non ha né Robin né batteria', () => {
    const sim = new NightSim(quiet(), 1);
    sim.setLamp(2);
    run(sim, 200);
    expect(sim.robin).toBeNull();
    expect(sim.battery).toBe(1);
    expect(sim.blackout).toBe(false);
  });

  it('la lampara consuma la batteria; al buio sale la ninna nanna e, se finisce prima delle sei, la Madre', () => {
    const sim = new NightSim(quiet2(), 2);
    sim.setLamp(2);
    const b = N2.battery!;
    const ev = run(sim, 1 / b.drain[2] + 1);
    expect(ev.some((e) => e.t === 'battery' && e.e === 'low')).toBe(true);
    expect(ev.some((e) => e.t === 'battery' && e.e === 'dead')).toBe(true);
    expect(sim.blackout).toBe(true);
    expect(sim.lamp).toBe(0);
    // al buio la lampara non si riaccende e il sonar non si apre
    sim.setLamp(2);
    sim.setView(0, true);
    expect(sim.lamp).toBe(0);
    expect(sim.sonarOpen).toBe(false);
    const ev2 = run(sim, b.lullaby + 1);
    expect(ev2.some((e) => e.t === 'lullaby' && e.e === 'end')).toBe(true);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'mother', cause: 'lullaby' });
  });

  it('con la lampara bassa la batteria arriva alle sei', () => {
    const sim = new NightSim(quiet2(), 3);
    sim.fish = N2.quota;
    run(sim, HOUR_SECONDS * 6 + 1);
    expect(sim.blackout).toBe(false);
    expect(sim.outcome).toEqual({ kind: 'won' });
  });

  it('Robin porta via un pesce alla volta e, col secchio vuoto, prende te', () => {
    const r = N2.robin!;
    const sim = new NightSim(quiet2(10), 4);
    sim.fish = 2;
    sim.setView(YAW.rod, false);
    const ev = run(sim, 10 + r.climb + r.stealEvery * 3 + 1);
    expect(ev.filter((e) => e.t === 'robin' && e.e === 'steal').length).toBe(2);
    expect(sim.fish).toBe(0);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'robin' });
  });

  it('la lampara al massimo in faccia scaccia Robin; guardare la canna non basta', () => {
    const r = N2.robin!;
    const sim = new NightSim(quiet2(10), 5);
    sim.fish = 3;
    sim.setLamp(2);
    sim.setView(YAW.rod, false);
    run(sim, 10 + r.climb + 0.5);
    expect(sim.robin!.state).toBe('stealing');
    sim.setView(YAW.robin, false);
    const ev = run(sim, r.scare + 0.2);
    expect(ev.some((e) => e.t === 'robin' && e.e === 'scared')).toBe(true);
    expect(sim.fish).toBe(3);
    expect(sim.playing).toBe(true);
  });

  it('quando canta la Madre i mostri se ne vanno e non tornano finché la canzone non finisce', () => {
    const r = N2.robin!;
    const sim = new NightSim(quiet2(10), 6);
    sim.fish = 5;
    sim.setView(YAW.rod, false);
    run(sim, 10 + r.climb + 0.5);
    expect(sim.robin!.state).toBe('stealing');
    // la batteria muore mentre Robin ruba
    sim.battery = 1e-6;
    const ev = run(sim, 2);
    expect(sim.blackout).toBe(true);
    expect(ev.some((e) => e.t === 'robin' && e.e === 'scared')).toBe(true);
    // per tutta la canzone nessuno sale a bordo: si muore solo per la Madre
    const ev2 = run(sim, N2.battery!.lullaby);
    expect(ev2.some((e) => e.t === 'robin' && (e.e === 'climb' || e.e === 'steal'))).toBe(false);
    expect(ev2.some((e) => e.t === 'gulpy' || e.t === 'molly' || e.t === 'hatch')).toBe(false);
    expect(sim.fish).toBe(5);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'mother', cause: 'lullaby' });
  });

  it('un bot esperto supera quasi sempre la seconda notte', () => {
    let wins = 0;
    for (let seed = 1; seed <= 30; seed++) {
      const sim = playNight(new NightSim(N2, seed), SKILLS.expert!, seed);
      if (sim.outcome.kind === 'won') wins++;
    }
    expect(wins).toBeGreaterThanOrEqual(26);
  });
});


// ───────────────────────── notte 3: Archie ─────────────────────────

const N3 = NIGHTS[3]!;

/** notte 3 con il solo Archie (dal secondo archieAt) */
function quiet3(archieAt = 10): NightConfig {
  const far = 1e9;
  return {
    ...N3,
    gulpy: { ...N3.gulpy, firstAt: far },
    molly: { ...N3.molly, firstAt: far },
    hatch: { ...N3.hatch, firstAt: far },
    robin: { ...N3.robin!, firstAt: far },
    archie: { ...N3.archie!, firstAt: archieAt },
  };
}

describe('Notte 3', () => {
  const a = N3.archie!;

  it('le prime due notti non hanno Archie', () => {
    expect(new NightSim(quiet(), 1).archie).toBeNull();
    expect(new NightSim(quiet2(), 1).archie).toBeNull();
  });

  it('se alla fine del risucchio la lampara è accesa, Archie soffia: il vetro esplode e ti è addosso', () => {
    const sim = new NightSim(quiet3(), 1);
    sim.setView(YAW.rod, false);
    const ev = run(sim, 10 + a.rise + a.inhale + 0.3);
    expect(ev.some((e) => e.t === 'archie' && e.e === 'blow')).toBe(true);
    expect(sim.lamp).toBe(0);
    expect(sim.lampBroken).toBe(true);
    // col vetro rotto la lampara non si riaccende
    sim.setLamp(1);
    expect(sim.lamp).toBe(0);
    run(sim, 1.2);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'archie' });
  });

  it('spenta in tempo, Archie aspetta al buio e si rituffa', () => {
    const sim = new NightSim(quiet3(), 2);
    run(sim, 10 + a.rise + a.inhale * 0.6);
    expect(sim.archie!.state).toBe('inhaling');
    sim.setLamp(0);
    const ev = run(sim, a.inhale * 0.4 + a.dark + a.dive + 0.5);
    expect(ev.some((e) => e.t === 'archie' && e.e === 'wait')).toBe(true);
    expect(ev.some((e) => e.t === 'archie' && e.e === 'gone')).toBe(true);
    expect(sim.playing).toBe(true);
    expect(sim.lampBroken).toBe(false);
    sim.setLamp(1);
    expect(sim.lamp).toBe(1);
  });

  it('riaccesa troppo presto, riprende fiato più in fretta: si salva solo rispegnendo', () => {
    const sim = new NightSim(quiet3(), 3);
    run(sim, 10 + a.rise + 0.5);
    sim.setLamp(0);
    run(sim, a.inhale + a.dark * 0.5);
    expect(sim.archie!.state).toBe('waiting');
    sim.setLamp(1);
    const ev = run(sim, a.relight * 0.5);
    expect(ev.some((e) => e.t === 'archie' && e.e === 'relight')).toBe(true);
    sim.setLamp(0);
    run(sim, a.relight + a.dark + a.dive + 0.5);
    expect(sim.playing).toBe(true);
    expect(sim.archie!.state).toBe('away');
  });

  it('quando canta la Madre si rituffa anche Archie', () => {
    const sim = new NightSim(quiet3(), 4);
    run(sim, 10 + a.rise + 0.5);
    expect(sim.archie!.state).toBe('inhaling');
    sim.battery = 1e-6;
    const ev = run(sim, a.dive + 0.5);
    expect(ev.some((e) => e.t === 'archie' && e.e === 'dive')).toBe(true);
    expect(sim.archie!.present).toBe(false);
  });

  it('un bot esperto supera quasi sempre la terza notte', () => {
    let wins = 0;
    for (let seed = 1; seed <= 30; seed++) {
      const sim = playNight(new NightSim(N3, seed), SKILLS.expert!, seed);
      if (sim.outcome.kind === 'won') wins++;
    }
    expect(wins).toBeGreaterThanOrEqual(26);
  });
});


describe('Pesca', () => {
  const fish = () => ({ species: { id: 'prova', weight: 1, strength: 1, kg: [1, 2] as [number, number] }, lore: null, kg: 1 });
  const hooked = () => {
    const ev: GameEvent[] = [];
    const f = new Fishing(new Rng(3), (e) => ev.push(e));
    f.snapGrace = N1.snapGrace!;
    f.phase = 'bite';
    f.press(fish);
    return { f, ev };
  };
  const step = (f: Fishing, held: boolean, secs: number) => {
    for (let t = 0; t < secs; t += 1 / 60) f.update(1 / 60, { lamp: 1, reelHeld: held, facingRod: true, busy: false });
  };

  it('a tensione piena il filo regge mezzo secondo e la barra trema; mollando in tempo si salva', () => {
    const { f, ev } = hooked();
    let guard = 0;
    while (f.tension < 1 && guard++ < 600) step(f, true, 1 / 60);
    expect(f.tension).toBe(1);
    step(f, true, 0.3);
    expect(f.phase).toBe('reeling');
    expect(f.strain).toBeGreaterThan(0.4);
    step(f, false, 0.5);
    expect(ev.some((e) => e.t === 'lineSnap')).toBe(false);
    // tirando ancora a tensione piena, oltre il mezzo secondo il filo si spezza
    guard = 0;
    while (f.tension < 1 && guard++ < 600) step(f, true, 1 / 60);
    step(f, true, 0.6);
    expect(ev.some((e) => e.t === 'lineSnap')).toBe(true);
  });

  it('il pesce da solo non spezza il filo', () => {
    const { f, ev } = hooked();
    step(f, false, 8);
    expect(ev.some((e) => e.t === 'lineSnap')).toBe(false);
  });

  it('la tolleranza allo strappo si sfuma nelle prime notti, ma non sparisce', () => {
    const grace = [1, 2].map((n) => new NightSim(NIGHTS[n]!, 1).fishing.snapGrace);
    expect(grace[0]).toBe(0.5);
    expect(grace[1]).toBeLessThan(grace[0]!);
    expect(new NightSim({ ...NIGHTS[2]!, snapGrace: undefined }, 1).fishing.snapGrace).toBeLessThan(grace[1]!);
    expect(new NightSim({ ...NIGHTS[2]!, snapGrace: undefined }, 1).fishing.snapGrace).toBeGreaterThan(0);
  });
});
