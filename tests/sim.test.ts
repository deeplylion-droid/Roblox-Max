import { describe, expect, it } from 'vitest';
import { EXTRA_NIGHT, FOXY_PLACES, HOUR_SECONDS, LORE, MONSTERS, NIGHTS, YAW, canFeed, extraEndingEarned, extraLevels, extraMother, extraNight, type MonsterId, type NightConfig } from '../src/game/config.ts';
import { FOXY_FIRST_GRACE } from '../src/game/monsters.ts';
import { LORE_TEXT } from '../src/i18n.ts';
import type { GameEvent } from '../src/game/events.ts';
import { NightSim } from '../src/game/sim.ts';
import { Bot, SKILLS, playNight } from '../src/game/bot.ts';
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

  it('sotto il telone Molly non ti vede e aspetta senza offendersi; quando esci vuole di nuovo che la guardi', () => {
    const cfg: NightConfig = { ...N1, gulpy: { ...N1.gulpy, firstAt: 1e9 }, hatch: { ...N1.hatch, firstAt: 1e9 } };
    const sim = new NightSim(cfg, 11);
    sim.fish = 9;
    // appena si affaccia ti nascondi e resti sotto il telone a lungo (come per Hatch): non si arrabbia
    const ev = run(sim, cfg.molly.firstAt + cfg.molly.knock + cfg.molly.neglectMax * 3, (s) => {
      if (s.molly.state === 'peeking' && s.hide === 'out') s.toggleHide();
    });
    expect(sim.playing).toBe(true);
    expect(ev.some((e) => e.t === 'molly' && e.e === 'tantrum')).toBe(false);
    expect(sim.molly.state).toBe('peeking');
    // esci e la guardi: se ne va
    sim.toggleHide();
    const ev2 = run(sim, 15, (s) => s.setView(s.molly.yaw, false));
    expect(ev2.some((e) => e.t === 'molly' && e.e === 'giggle')).toBe(true);
    expect(sim.playing).toBe(true);
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
    foxy: undefined,
    gulpy: { ...N2.gulpy, firstAt: far },
    molly: { ...N2.molly, firstAt: far },
    hatch: { ...N2.hatch, firstAt: far },
    robin: { ...N2.robin!, firstAt: robinAt },
  };
}

describe('Il Foxy (dalla notte 2, col binocolo)', () => {
  /** La notte 2 con il solo Foxy (gli altri a casa), che compare subito. */
  function soloFoxy(over: Partial<NonNullable<NightConfig['foxy']>> = {}): NightConfig {
    const far = 1e9;
    return {
      ...N2,
      gulpy: { ...N2.gulpy, firstAt: far },
      molly: { ...N2.molly, firstAt: far },
      hatch: { ...N2.hatch, firstAt: far },
      robin: { ...N2.robin!, firstAt: far },
      foxy: { ...N2.foxy!, firstAt: 1, swap: 0, ...over },
    };
  }
  const guarda = (s: NightSim, i: number) => s.setBino({ yaw: FOXY_PLACES[i]!.yaw, pitch: FOXY_PLACES[i]!.pitch, fov: 9 });

  it('guardato col binocolo il suo tempo riparte; trascurato si sporge, lascia il posto e salta sulla barca', () => {
    const sim = new NightSim(soloFoxy(), 3);
    run(sim, 2);
    const f = sim.foxy!;
    expect(f.state).toBe('watching');
    // trovato una volta (finisce l'attesa più lunga della prima volta), poi lo si guarda ogni 20 s: non si muove mai
    for (let k = 0; k < 10; k++) {
      run(sim, 0.5, (s) => guarda(s, f.place));
      sim.setBino(null);
      run(sim, 20);
      expect(f.state).toBe('watching');
    }
    // trascurato: prima si sporge, poi il posto è vuoto, poi il salto
    const cfg = N2.foxy!;
    const ev = run(sim, cfg.leave + cfg.run + 1);
    expect(ev.some((e) => e.t === 'foxy' && e.e === 'lean')).toBe(true);
    expect(ev.some((e) => e.t === 'foxy' && e.e === 'leave')).toBe(true);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'foxy' });
  });

  it('la prima volta, finché non lo trovi, aspetta di più', () => {
    const sim = new NightSim(soloFoxy(), 3);
    run(sim, 1 + N2.foxy!.leave + 0.5);
    expect(sim.foxy!.state).not.toBe('gone');
    run(sim, N2.foxy!.leave * (FOXY_FIRST_GRACE - 1) + 1);
    expect(['gone', 'attack']).toContain(sim.foxy!.state);
  });

  it('si muove solo quando non lo guardi: sporto resta sporto finché lo guardi, poi torna al posto (o cambia posto)', () => {
    const sim = new NightSim(soloFoxy({ swap: 1 }), 3);
    run(sim, 2);
    const f = sim.foxy!;
    const prima = f.place;
    run(sim, 0.5, (s) => guarda(s, prima));
    sim.setBino(null);
    run(sim, N2.foxy!.lean + 1);
    expect(f.state).toBe('leaning');
    // cambiato posto quando hai abbassato il binocolo la prima volta
    expect(f.place).not.toBe(prima);
    run(sim, 3, (s) => guarda(s, f.place));
    expect(f.state).toBe('leaning');
    sim.setBino(null);
    run(sim, 0.2);
    expect(f.state).toBe('watching');
  });

  it('il giocatore esperto lo tiene d\'occhio e arriva alle sei', () => {
    for (const seed of [1, 2, 3]) {
      const sim = new NightSim(soloFoxy({ firstAt: N2.foxy!.firstAt, swap: N2.foxy!.swap }), seed);
      playNight(sim, SKILLS.expert!, seed);
      expect(sim.outcome.kind === 'dead' && sim.outcome.killer === 'foxy').toBe(false);
    }
  });
});

describe('Frammenti da ripescare', () => {
  it('ogni frammento ha titolo e testo in italiano e in inglese', () => {
    for (const l of LORE) for (const lang of ['it', 'en'] as const) expect(LORE_TEXT[lang][l.id]?.body, `${l.id} ${lang}`).toBeTruthy();
  });

  it('dalla notte 2 se ne ripescano di nuovi anche con quelli della prima già nel Diario', () => {
    for (const n of [2, 3, 4, 5]) {
      const giaTrovati = LORE.filter((l) => l.night < n).map((l) => l.id);
      const sim = new NightSim(NIGHTS[n]!, 11, giaTrovati);
      playNight(sim, SKILLS.expert!, 11);
      expect(sim.loreThisNight.some((id) => LORE.find((l) => l.id === id)!.night === n), `notte ${n}`).toBe(true);
    }
  });
});

describe('Notte 2', () => {
  it('la prima notte non ha né Robin né batteria', () => {
    const sim = new NightSim(quiet(), 1);
    sim.setLamp(2);
    run(sim, 200);
    expect(sim.robin).toBeNull();
    expect(sim.battery).toBe(1);
    expect(sim.blackout).toBe(false);
  });

  it('il binocolo alzato tiene gli occhi lontani dalla barca ma non consuma la batteria; il sonar aperto sì', () => {
    const conBinocolo = new NightSim(quiet2(), 2);
    conBinocolo.setLamp(0);
    run(conBinocolo, 60, (s) => s.setView(0, true, false));
    expect(conBinocolo.sonarOpen).toBe(true);
    expect(conBinocolo.battery).toBe(1);
    const colSonar = new NightSim(quiet2(), 2);
    colSonar.setLamp(0);
    run(colSonar, 60, (s) => s.setView(0, true));
    expect(colSonar.battery).toBeCloseTo(1 - 60 * N2.battery!.sonar, 2);
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

  it('la lampara al massimo scaccia Robin anche senza guardarlo; con la luce bassa ruba', () => {
    const r = N2.robin!;
    // luce al massimo e lo sguardo sulla canna (deciso dall'utente l'11 ottobre: non serve guardarlo): scappa prima di
    // arrivare al secchio
    const a = new NightSim(quiet2(10), 5);
    a.fish = 3;
    a.setLamp(2);
    a.setView(YAW.rod, false);
    const ev = run(a, 10 + r.climb + r.stealEvery + 0.5);
    expect(ev.some((e) => e.t === 'robin' && e.e === 'scared')).toBe(true);
    expect(ev.some((e) => e.t === 'robin' && e.e === 'steal')).toBe(false);
    expect(a.fish).toBe(3);
    expect(a.playing).toBe(true);
    // luce bassa, anche guardandolo: ruba
    const b = new NightSim(quiet2(10), 5);
    b.fish = 3;
    b.setLamp(1);
    b.setView(YAW.robin, false);
    const ev2 = run(b, 10 + r.climb + r.stealEvery + 0.5);
    expect(ev2.some((e) => e.t === 'robin' && e.e === 'steal')).toBe(true);
    expect(b.fish).toBe(2);
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
    foxy: undefined,
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


const N4 = NIGHTS[4]!;

/** la quarta notte con la sola Lampy; i pesci veri abboccano tardissimo, così l'abboccata è sua */
function quiet4(lampyAt = 5): NightConfig {
  const far = 1e9;
  return {
    ...N4,
    foxy: undefined,
    biteMul: 50,
    gulpy: { ...N4.gulpy, firstAt: far },
    molly: { ...N4.molly, firstAt: far },
    hatch: { ...N4.hatch, firstAt: far },
    robin: { ...N4.robin!, firstAt: far },
    archie: { ...N4.archie!, firstAt: far },
    lampy: { ...N4.lampy!, firstAt: lampyAt },
  };
}

/** lancia e aspetta che la lenza sia in acqua */
function castLine(sim: NightSim): void {
  sim.setView(YAW.rod, false);
  sim.pressRod();
  run(sim, 1.2);
  expect(sim.fishing.phase).toBe('waiting');
}

/** gli eventi con l'istante in cui arrivano */
function timed(sim: NightSim, seconds: number, until?: (e: GameEvent) => boolean): { e: GameEvent; t: number }[] {
  const out: { e: GameEvent; t: number }[] = [];
  const dt = 1 / 60;
  for (let t = 0; t < seconds && sim.playing; t += dt) {
    sim.update(dt);
    for (const e of sim.drainEvents()) {
      out.push({ e, t: sim.time });
      if (until?.(e)) return out;
    }
  }
  return out;
}

const isLampy = (e: GameEvent, what: string) => e.t === 'lampy' && e.e === what;

describe('Notte 4', () => {
  const l = N4.lampy!;

  it('le prime tre notti non hanno Lampy', () => {
    expect(new NightSim(quiet(), 1).lampy).toBeNull();
    expect(new NightSim(quiet3(), 1).lampy).toBeNull();
  });

  it('Lampy prende la lenza e suona tre colpi a tempo perfetto, con la risatina dopo il secondo, poi affiora', () => {
    const sim = new NightSim(quiet4(), 1);
    castLine(sim);
    const ev = timed(sim, 5 + l.grab[1] + 3, (e) => isLampy(e, 'surface'));
    const grab = ev.find((x) => isLampy(x.e, 'grab'));
    expect(grab).toBeDefined();
    // la canna si piega come per un pesce, ma il campanellino non è quello di un'abboccata vera
    expect(ev.some((x) => x.e.t === 'bite')).toBe(false);
    const beats = ev.filter((x) => isLampy(x.e, 'beat'));
    expect(beats.map((x) => (x.e as { n?: number }).n)).toEqual([1, 2, 3]);
    expect(beats[1]!.t - beats[0]!.t).toBeCloseTo(l.beat, 1);
    expect(beats[2]!.t - beats[1]!.t).toBeCloseTo(l.beat, 1);
    const giggle = ev.find((x) => isLampy(x.e, 'giggle'))!;
    expect(giggle.t).toBeGreaterThanOrEqual(beats[1]!.t);
    expect(giggle.t).toBeLessThan(beats[2]!.t);
    expect(ev.at(-1)!.t).toBeGreaterThanOrEqual(beats[2]!.t);
    expect(sim.lampy!.visible).toBe(true);
    expect(sim.fishing.phase).toBe('bite');
  });

  it('aspettando, Lampy ti guarda e molla: l’esca resta e la lenza torna ad aspettare', () => {
    const sim = new NightSim(quiet4(), 2);
    castLine(sim);
    const ev = timed(sim, 5 + l.grab[1] + 2 + l.surface + l.stay + 2, (e) => isLampy(e, 'gone'));
    expect(ev.some((x) => isLampy(x.e, 'let'))).toBe(true);
    expect(ev.some((x) => isLampy(x.e, 'gone'))).toBe(true);
    expect(ev.some((x) => x.e.t === 'baitStolen')).toBe(false);
    expect(sim.playing).toBe(true);
    expect(sim.fishing.phase).toBe('waiting');
    expect(sim.lampy!.present).toBe(false);
  });

  it('ferrare l’abboccata di Lampy è fatale: l’hai agganciata, risale la lenza ed è addosso', () => {
    const sim = new NightSim(quiet4(), 3);
    castLine(sim);
    timed(sim, 5 + l.grab[1] + 1, (e) => isLampy(e, 'beat'));
    expect(sim.pressRod()).toBe(true);
    const ev = timed(sim, l.climb + 0.3);
    expect(ev.some((x) => isLampy(x.e, 'hooked'))).toBe(true);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'lampy' });
  });

  it('anche quando è già affiorata, ferrare la aggancia', () => {
    const sim = new NightSim(quiet4(), 4);
    castLine(sim);
    timed(sim, 5 + l.grab[1] + 3, (e) => isLampy(e, 'surface'));
    run(sim, l.surface + 0.2);
    expect(sim.lampy!.state).toBe('staring');
    sim.pressRod();
    run(sim, l.climb + 0.3);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'lampy' });
  });

  it('se ti nascondi sotto il telone mentre suona, Lampy molla la lenza e se ne va', () => {
    const sim = new NightSim(quiet4(), 5);
    castLine(sim);
    timed(sim, 5 + l.grab[1] + 1, (e) => isLampy(e, 'beat'));
    sim.toggleHide();
    const ev = timed(sim, 1.5);
    expect(ev.some((x) => isLampy(x.e, 'gone'))).toBe(true);
    expect(sim.lampy!.present).toBe(false);
    expect(sim.playing).toBe(true);
  });

  it('quando canta la Madre Lampy molla la lenza', () => {
    const sim = new NightSim(quiet4(), 6);
    castLine(sim);
    timed(sim, 5 + l.grab[1] + 1, (e) => isLampy(e, 'beat'));
    sim.battery = 1e-6;
    run(sim, 1.5);
    expect(sim.lampy!.present).toBe(false);
    expect(sim.playing).toBe(true);
  });

  it('un bot esperto supera quasi sempre la quarta notte', () => {
    let wins = 0;
    for (let seed = 1; seed <= 30; seed++) {
      const sim = playNight(new NightSim(N4, seed), SKILLS.expert!, seed);
      if (sim.outcome.kind === 'won') wins++;
    }
    expect(wins).toBeGreaterThanOrEqual(26);
  });
});

const N5 = NIGHTS[5]!;

/** la quinta notte col solo Fangy; i pesci abboccano tardissimo */
function quiet5(fangyAt = 3): NightConfig {
  const far = 1e9;
  return {
    ...N5,
    foxy: undefined,
    biteMul: 50,
    gulpy: { ...N5.gulpy, firstAt: far },
    molly: { ...N5.molly, firstAt: far },
    hatch: { ...N5.hatch, firstAt: far },
    robin: { ...N5.robin!, firstAt: far },
    archie: { ...N5.archie!, firstAt: far },
    lampy: { ...N5.lampy!, firstAt: far },
    fangy: { ...N5.fangy!, firstAt: fangyAt },
  };
}

const isFangy = (e: GameEvent, what: string) => e.t === 'fangy' && e.e === what;

/** aspetta che Fangy sia salito accanto alla barca e ascolti */
function untilListening(sim: NightSim): void {
  const f = sim.cfg.fangy!;
  timed(sim, 3 + f.approach + 1, (e) => isFangy(e, 'rise'));
  run(sim, f.rise + 0.1);
  expect(sim.fangy!.state).toBe('listening');
}

describe('Notte 5', () => {
  const f = N5.fangy!;

  it('la quinta notte si gioca, e le prime quattro non hanno Fangy', () => {
    expect(N5.bozza).toBeFalsy();
    expect(new NightSim(quiet4(), 1).fangy).toBeNull();
    expect(new NightSim(quiet5(), 1).fangy).not.toBeNull();
  });

  it('lo annunciano le lucine, sale accanto alla barca e ascolta; se resti zitto torna giù', () => {
    const sim = new NightSim(quiet5(), 1);
    const ev = timed(sim, 3 + f.approach + f.rise + f.listen + f.leave + 2, (e) => isFangy(e, 'gone'));
    const fangy = ev.filter((x) => x.e.t === 'fangy');
    expect(fangy.map((x) => (x.e as { e: string }).e)).toEqual(['approach', 'rise', 'leave', 'gone']);
    const at = (what: string) => fangy.find((x) => isFangy(x.e, what))!.t;
    expect(at('rise') - at('approach')).toBeCloseTo(f.approach, 1);
    expect(at('leave') - at('rise')).toBeCloseTo(f.rise + f.listen, 1);
    expect(sim.playing).toBe(true);
    expect(sim.fangy!.present).toBe(false);
  });

  it('ogni rumore lo fa voltare; al terzo è addosso', () => {
    const sim = new NightSim(quiet5(), 2);
    untilListening(sim);
    const snaps: number[] = [];
    for (const lamp of [2, 1, 2] as const) {
      sim.setLamp(lamp);
      for (const e of run(sim, f.deaf + 0.1)) if (e.t === 'fangy' && e.e === 'snap') snaps.push(e.n!);
    }
    expect(snaps).toEqual([1, 2, 3]);
    expect(sim.outcome).toEqual({ kind: 'dead', killer: 'fangy' });
  });

  it('un gesto solo conta un rumore solo (due scatti del commutatore di fila)', () => {
    const sim = new NightSim(quiet5(), 3);
    untilListening(sim);
    sim.setLamp(2);
    sim.setLamp(1);
    const ev = run(sim, 0.3);
    expect(ev.filter((e) => e.t === 'fangy' && e.e === 'snap')).toHaveLength(1);
    expect(sim.fangy!.heard).toBe(1);
  });

  it('dopo un rumore resta ad ascoltare almeno un altro po', () => {
    const sim = new NightSim(quiet5(), 4);
    untilListening(sim);
    run(sim, f.listen - 0.5);
    sim.setLamp(2);
    run(sim, 1);
    expect(sim.fangy!.state).toBe('listening');
    expect(sim.playing).toBe(true);
  });

  it('quando canta la Madre torna giù', () => {
    const sim = new NightSim(quiet5(), 5);
    untilListening(sim);
    sim.battery = 1e-6;
    run(sim, 1.5);
    expect(sim.fangy!.listening).toBe(false);
    expect(sim.playing).toBe(true);
  });

  it('un bot esperto supera quasi sempre la quinta notte', () => {
    let wins = 0;
    for (let seed = 1; seed <= 30; seed++) {
      const sim = playNight(new NightSim(N5, seed), SKILLS.expert!, seed);
      if (sim.outcome.kind === 'won') wins++;
    }
    expect(wins).toBeGreaterThanOrEqual(26);
  });
});

const N6 = NIGHTS[6]!;

/** la sesta notte con la sola Madre (i figli lontanissimi, salvo `keep`); i pesci abboccano tardissimo */
function quiet6(keep: Partial<NightConfig> = {}): NightConfig {
  const far = 1e9;
  return {
    ...N6,
    biteMul: 50,
    gulpy: { ...N6.gulpy, firstAt: far },
    molly: { ...N6.molly, firstAt: far },
    hatch: { ...N6.hatch, firstAt: far },
    robin: { ...N6.robin!, firstAt: far },
    archie: { ...N6.archie!, firstAt: far },
    lampy: { ...N6.lampy!, firstAt: far },
    fangy: { ...N6.fangy!, firstAt: far },
    ...keep,
  };
}

const isMother = (e: GameEvent, what: string) => e.t === 'mother' && e.e === what;

/** fa avanzare fino all'inizio della prima passata sotto la barca, più `extra` secondi */
function untilPassing(sim: NightSim, extra = 0.8): void {
  const m = sim.cfg.mother!;
  run(sim, m.passes[0]! + m.approach - sim.time + extra);
  expect(sim.mother!.passing).toBe(true);
}

describe('Notte 6', () => {
  const m = N6.mother!;

  it('la Madre c’è solo nella sesta notte', () => {
    expect(new NightSim(quiet5(), 1).mother).toBeNull();
    expect(new NightSim(quiet6(), 1).mother).not.toBeNull();
  });

  it('arriva alle ore fisse e passa sotto la barca; se resti fermo se ne va', () => {
    const sim = new NightSim(quiet6(), 1);
    const ev = timed(sim, m.passes[0]! + m.approach + m.pass[0]! + m.leave + 1, (e) => isMother(e, 'gone'));
    const mother = ev.filter((x) => x.e.t === 'mother' && (x.e as { e: string }).e !== 'call');
    expect(mother.map((x) => (x.e as { e: string }).e)).toEqual(['approach', 'pass', 'leave', 'gone']);
    const at = (what: string) => mother.find((x) => isMother(x.e, what))!.t;
    expect(at('approach')).toBeCloseTo(m.passes[0]!, 0);
    expect(at('leave') - at('pass')).toBeCloseTo(m.pass[0]!, 0);
    expect(sim.playing).toBe(true);
  });

  it('quando arriva i figli tornano giù e non risalgono finché è vicina', () => {
    const sim = new NightSim(quiet6({ molly: { ...N6.molly, firstAt: m.passes[0]! - 12 } }), 2);
    run(sim, m.passes[0]! - 1);
    expect(sim.molly.state === 'knocking' || sim.molly.present).toBe(true);
    run(sim, 3.5);
    expect(sim.molly.present).toBe(false);
    run(sim, m.approach + m.pass[0]! - 3);
    expect(sim.molly.present || sim.molly.state === 'knocking').toBe(false);
    expect(sim.playing).toBe(true);
  });

  it('mentre passa sotto, un gesto qualunque e ti prende', () => {
    for (const gesture of [(s: NightSim) => s.setLamp(2), (s: NightSim) => s.toggleHide(), (s: NightSim) => s.setReelHeld(true), (s: NightSim) => s.setView(s.viewYaw, true)]) {
      const sim = new NightSim(quiet6(), 3);
      untilPassing(sim);
      gesture(sim);
      run(sim, 0.2);
      expect(sim.outcome).toEqual({ kind: 'dead', killer: 'mother', cause: 'moved' });
    }
  });

  it('lo sguardo: un tremito si perdona, girarsi no', () => {
    const still = new NightSim(quiet6(), 4);
    untilPassing(still);
    still.setView(still.viewYaw + m.still * 0.6, false);
    run(still, 1);
    expect(still.playing).toBe(true);
    const turned = new NightSim(quiet6(), 4);
    untilPassing(turned);
    turned.setView(turned.viewYaw + 25, false);
    run(turned, 0.2);
    expect(turned.outcome).toEqual({ kind: 'dead', killer: 'mother', cause: 'moved' });
  });

  it('se ti eri appena girato, la vista che si ferma da sola non conta', () => {
    const sim = new NightSim(quiet6(), 5);
    run(sim, m.passes[0]! + m.approach - sim.time + 0.05);
    expect(sim.mother!.passing).toBe(true);
    sim.setView(sim.viewYaw + 6, false);
    run(sim, 0.2);
    sim.setView(sim.viewYaw + 3, false);
    run(sim, 1.5);
    expect(sim.playing).toBe(true);
  });

  it('il sonar (o il binocolo) già aperto prima che passi non conta, nemmeno se la batteria muore', () => {
    for (const dies of ['prima', 'durante']) {
      const sim = new NightSim(quiet6(), 7);
      run(sim, sim.cfg.mother!.passes[0]! + 2, (s) => s.setView(s.viewYaw, true));
      if (dies === 'prima') sim.battery = 1e-6;
      untilPassing(sim);
      if (dies === 'durante') sim.battery = 1e-6;
      run(sim, 1, (s) => s.setView(s.viewYaw, true));
      expect(sim.blackout).toBe(true);
      expect(sim.playing).toBe(true);
    }
  });

  it('il telone tirato appena prima che passi finisce di muoversi senza colpa', () => {
    const sim = new NightSim(quiet6(), 8);
    run(sim, m.passes[0]! + m.approach - sim.time - 0.3);
    expect(sim.mother!.state).toBe('approaching');
    sim.toggleHide();
    run(sim, 1.5);
    expect(sim.hide).toBe('in');
    expect(sim.playing).toBe(true);
  });

  it('mentre si avvicina ci si può ancora muovere', () => {
    const sim = new NightSim(quiet6(), 6);
    run(sim, m.passes[0]! + 2);
    expect(sim.mother!.state).toBe('approaching');
    sim.setLamp(2);
    sim.setView(90, false);
    run(sim, 1);
    expect(sim.playing).toBe(true);
  });

  it('un bot esperto supera spesso la sesta notte', () => {
    let wins = 0;
    for (let seed = 1; seed <= 30; seed++) {
      const sim = playNight(new NightSim(N6, seed), SKILLS.expert!, seed);
      if (sim.outcome.kind === 'won') wins++;
    }
    expect(wins).toBeGreaterThanOrEqual(22);
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

// ───────────────────────── notte 7: la notte extra coi livelli ─────────────────────────

/** quante volte ogni mostro entra in scena in una notte giocata dal bot */
function visits(cfg: NightConfig, seed: number): Record<MonsterId, number> & { won: boolean } {
  const sim = new NightSim(cfg, seed);
  const bot = new Bot(sim, SKILLS.expert!, seed);
  const n = Object.fromEntries(MONSTERS.map((m) => [m, 0])) as Record<MonsterId, number>;
  const was = new Set<MonsterId>();
  const dt = 1 / 30;
  while (sim.playing) {
    bot.step(dt);
    sim.update(dt);
    sim.drainEvents();
    for (const m of MONSTERS) {
      const on = sim.active(m);
      if (on && !was.has(m)) n[m]++;
      if (on) was.add(m);
      else was.delete(m);
    }
  }
  return { ...n, won: sim.outcome.kind === 'won' };
}

describe('Notte 7, la notte extra', () => {
  it('è la notte 7, con la batteria, e i livelli fuori scala si riportano fra 0 e 20', () => {
    const cfg = extraNight(extraLevels(5));
    expect(cfg.night).toBe(EXTRA_NIGHT);
    expect(cfg.battery).toBeDefined();
    expect(extraNight({ ...extraLevels(0), lampy: 99 }).lampy).toEqual(extraNight({ ...extraLevels(0), lampy: 20 }).lampy);
    expect(extraNight({ ...extraLevels(0), lampy: -3 }).lampy).toBeUndefined();
  });

  it('al livello 5 ogni mostro è come nella notte in cui arriva', () => {
    const cfg = extraNight(extraLevels(5));
    expect(cfg.gulpy).toEqual(NIGHTS[1]!.gulpy);
    expect(cfg.molly).toEqual(NIGHTS[1]!.molly);
    expect(cfg.hatch).toEqual(NIGHTS[1]!.hatch);
    expect(cfg.robin).toEqual(NIGHTS[2]!.robin);
    expect(cfg.archie).toEqual(NIGHTS[3]!.archie);
    expect(cfg.lampy).toEqual(NIGHTS[4]!.lampy);
    expect(cfg.fangy).toEqual(NIGHTS[5]!.fangy);
  });

  it('al livello 0 il mostro non viene', () => {
    for (const who of MONSTERS) {
      // tutti a 10 tranne lui
      const v = visits(extraNight({ ...extraLevels(10), [who]: 0 }), 3);
      expect(v[who], who).toBe(0);
    }
    // tutti a 0: la notte è solo pesca
    const v = visits(extraNight(extraLevels(0)), 4);
    for (const who of MONSTERS) expect(v[who], who).toBe(0);
    expect(v.won).toBe(true);
  });

  it('a livello alto il mostro viene più spesso', () => {
    for (const who of MONSTERS) {
      let low = 0;
      let high = 0;
      for (let seed = 1; seed <= 4; seed++) {
        low += visits(extraNight({ ...extraLevels(0), [who]: 2 }), seed)[who];
        high += visits(extraNight({ ...extraLevels(0), [who]: 20 }), seed)[who];
      }
      expect(high, who).toBeGreaterThan(low * 1.3);
      expect(low, who).toBeGreaterThan(0);
    }
  });

  it('il bot esperto vince quasi sempre a livelli bassi', () => {
    let wins = 0;
    for (let seed = 1; seed <= 20; seed++) {
      const sim = playNight(new NightSim(extraNight(extraLevels(3)), seed * 7919), SKILLS.expert!, seed);
      if (sim.outcome.kind === 'won') wins++;
    }
    expect(wins).toBeGreaterThanOrEqual(18);
  });

  it('Soggy (il Foxy): a 0 non c’è, al 5 è come nella notte 2, più alto è più impaziente; con lui il recupero è più svelto', () => {
    expect(extraNight(extraLevels(0)).foxy).toBeUndefined();
    expect(extraNight(extraLevels(0)).reelMul).toBeUndefined();
    const f5 = extraNight({ ...extraLevels(0), foxy: 5 });
    expect(f5.foxy).toEqual(NIGHTS[2]!.foxy);
    expect(f5.reelMul).toBeGreaterThan(1);
    let prev = Infinity;
    for (let l = 1; l <= 20; l++) {
      const f = extraNight({ ...extraLevels(0), foxy: l }).foxy!;
      expect(f.leave, `livello ${l}`).toBeLessThanOrEqual(prev);
      expect(f.lean, `livello ${l}`).toBeLessThan(f.leave);
      prev = f.leave;
    }
  });

  it('la Madre: a 0 non viene, al 10 è come nella notte 6, al 20 passa più volte e avvisa meno', () => {
    expect(extraMother(0)).toBeUndefined();
    expect(extraNight(extraLevels(0)).mother).toBeUndefined();
    expect(extraNight({ ...extraLevels(0), mother: 10 }).mother).toEqual(NIGHTS[6]!.mother);
    const m20 = extraMother(20)!;
    expect(m20.passes.length).toBe(5);
    expect(m20.pass.length).toBe(5);
    // in tutto sta sotto la barca più a lungo che al 10 (cinque passate da 12 a 20 s contro tre da 10 a 20)
    const sum = (x: number[]) => x.reduce((a, b) => a + b, 0);
    expect(sum(m20.pass)).toBeGreaterThan(sum(extraMother(10)!.pass));
    expect(m20.approach).toBeLessThan(extraMother(10)!.approach);
    expect(extraMother(1)!.passes.length).toBe(1);
    // le passate stanno tutte dentro la notte, in ordine
    for (let l = 1; l <= 20; l++) {
      const m = extraMother(l)!;
      expect(m.passes.length, `livello ${l}`).toBe(m.pass.length);
      for (let i = 1; i < m.passes.length; i++) expect(m.passes[i]!).toBeGreaterThan(m.passes[i - 1]!);
      expect(m.passes.at(-1)! + m.approach + Math.max(...m.pass)).toBeLessThan(6 * HOUR_SECONDS);
    }
  });

  it('con la Madre a 0 non passa mai; a 20 passa cinque volte', () => {
    const count = (lv: number) => {
      const sim = new NightSim(extraNight({ ...extraLevels(0), mother: lv }), 5);
      let passes = 0;
      let was = false;
      // fermi e zitti tutta la notte: lei passa e se ne va
      while (sim.playing) {
        sim.update(1 / 10);
        sim.drainEvents();
        const under = sim.mother?.state === 'passing';
        if (under && !was) passes++;
        was = under;
      }
      return passes;
    };
    expect(count(0)).toBe(0);
    expect(count(20)).toBe(5);
  });

  it('il finale speciale solo con tutti, Madre compresa, almeno a 10', () => {
    expect(extraEndingEarned(extraLevels(10))).toBe(true);
    expect(extraEndingEarned(extraLevels(20))).toBe(true);
    expect(extraEndingEarned({ ...extraLevels(20), mother: 9 })).toBe(false);
    expect(extraEndingEarned({ ...extraLevels(20), lampy: 0 })).toBe(false);
    expect(extraEndingEarned(extraLevels(5))).toBe(false);
  });

  it('tutti a 20, Madre compresa, è difficilissima ma possibile: l\'esperto la vince qualche volta', () => {
    // decisione dell'utente dell'11 ottobre; con npm run sim -- 7 300 20 l'esperto vince circa il 9% delle notti
    let wins = 0;
    for (let seed = 1; seed <= 60; seed++) {
      if (playNight(new NightSim(extraNight(extraLevels(20)), seed * 7919), SKILLS.expert!, seed).outcome.kind === 'won') wins++;
    }
    expect(wins).toBeGreaterThanOrEqual(2);
    expect(wins).toBeLessThanOrEqual(15);
  });

  it('i livelli fino al 10 non dipendono dal ritocco del 20', () => {
    // il tratto dal 10 al 20 parte esattamente dal 10
    const c10 = extraNight(extraLevels(10));
    const c11 = extraNight(extraLevels(11));
    for (const who of ['gulpy', 'molly', 'hatch', 'robin', 'archie', 'lampy', 'fangy'] as const) {
      const a = c10[who]!.cooldown;
      const b = c11[who]!.cooldown;
      expect(Math.abs(b[0] - a[0]), who).toBeLessThan(6);
    }
  });

  it('più alti i livelli, meno notti vinte', () => {
    const rate = (lv: number) => {
      let wins = 0;
      for (let seed = 1; seed <= 16; seed++) {
        if (playNight(new NightSim(extraNight(extraLevels(lv)), seed * 7919), SKILLS.average!, seed).outcome.kind === 'won') wins++;
      }
      return wins;
    };
    expect(rate(3)).toBeGreaterThan(rate(15));
  });
});

describe('Immersioni all’alba: il mostro sfamato', () => {
  /** gli eventi «parte» di ogni mostro (il primo che emette quando arriva) */
  const START: Record<string, string> = { gulpy: 'rise', molly: 'knock', hatch: 'count', robin: 'climb', archie: 'rise', lampy: 'grab', fangy: 'approach' };
  const started = (ev: GameEvent[], who: string) => ev.some((e) => e.t === who && (e as { e?: string }).e === START[who]);

  it('si sfama chi gira nella notte, tranne il mostro nuovo (la sua tana è vuota); la prima notte niente', () => {
    expect(canFeed(1, 'gulpy')).toBe(false);
    expect(canFeed(2, 'gulpy')).toBe(true);
    expect(canFeed(2, 'robin')).toBe(false);
    expect(canFeed(3, 'robin')).toBe(true);
    expect(canFeed(3, 'archie')).toBe(false);
    expect(canFeed(4, 'fangy')).toBe(false);
    expect(canFeed(6, 'fangy')).toBe(true);
  });

  it('il mostro sfamato dorme tutta la notte: non parte mai e il sonar non lo annuncia', () => {
    for (const who of ['gulpy', 'molly', 'hatch', 'robin', 'archie', 'lampy', 'fangy'] as const) {
      // Archie, Lampy e Fangy si sfamano solo dopo il loro arrivo: la sesta notte non c'è ancora, si usa una quinta che fa
      // da sesta (con tutti e sette i mostri)
      const base = ['archie', 'lampy', 'fangy'].includes(who) ? { ...NIGHTS[5]!, night: 6 } : NIGHTS[3]!;
      // gli altri mostri non vengono (se no ti uccidono prima e la prova finisce presto)
      // il Foxy no: senza binocolo ti salta addosso prima delle sei
      const cfg = { ...base, foxy: undefined } as NightConfig;
      for (const m of ['gulpy', 'molly', 'hatch', 'robin', 'archie', 'lampy', 'fangy'] as const) {
        const c = (cfg as unknown as Record<string, { firstAt: number } | undefined>)[m];
        if (m !== who && c) (cfg as unknown as Record<string, unknown>)[m] = { ...c, firstAt: 1e9 };
      }
      const play = (fed: typeof who | null) => {
        const sim = new NightSim(cfg, 11, [], { fed });
        let warned = false;
        const ev = run(sim, HOUR_SECONDS * 6 + 1, (s) => {
          s.fish = 99; // niente morti per Gulpy o Robin a secchio vuoto: si guarda solo chi arriva
          if (s.incoming().some((i) => i.who === who)) warned = true;
        });
        return { sim, warned, ev };
      };
      // controllo: senza pesce arriva (la prova non è vuota)
      const ctl = play(null);
      expect(ctl.warned || started(ctl.ev, who), who).toBe(true);
      const fed = play(who);
      expect(fed.sim.asleep).toBe(who);
      expect(started(fed.ev, who), who).toBe(false);
      expect(fed.warned, who).toBe(false);
      expect(fed.sim.time, who).toBeGreaterThan(HOUR_SECONDS * 6 - 1);
    }
  });

  it('gli altri mostri vengono lo stesso', () => {
    const sim = new NightSim({ ...NIGHTS[2]!, foxy: undefined }, 5, [], { fed: 'gulpy' });
    const ev = run(sim, HOUR_SECONDS * 3, (s) => {
      s.fish = 99;
      if (s.hatch.state === 'counting' && s.hide === 'out') s.toggleHide();
      if (s.hatch.state === 'away' && s.hide === 'in') s.toggleHide();
    });
    expect(started(ev, 'gulpy')).toBe(false);
    expect(started(ev, 'molly') || started(ev, 'robin')).toBe(true);
  });

  it('il mostro nuovo della notte non si può sfamare: l’opzione non conta', () => {
    const sim = new NightSim({ ...NIGHTS[2]!, foxy: undefined }, 3, [], { fed: 'robin' });
    expect(sim.asleep).toBeNull();
    const ev = run(sim, HOUR_SECONDS * 2, (s) => {
      s.fish = 99;
    });
    expect(started(ev, 'robin')).toBe(true);
  });

  it('resta deterministica anche col mostro sfamato', () => {
    const a = playNight(new NightSim(NIGHTS[2]!, 42, [], { fed: 'molly' }), SKILLS.average!, 7);
    const b = playNight(new NightSim(NIGHTS[2]!, 42, [], { fed: 'molly' }), SKILLS.average!, 7);
    expect(a.outcome).toEqual(b.outcome);
    expect(a.fish).toBe(b.fish);
  });

  it('sfamare Gulpy lascia nel secchio i pesci che si sarebbe mangiato', () => {
    const a = playNight(new NightSim(NIGHTS[2]!, 9, [], { fed: 'gulpy' }), SKILLS.expert!, 9);
    expect(a.fed).toBe(0);
  });
});

describe('Le cose delle tane', () => {
  it('non si pescano di notte: si trovano solo giù nelle tane', () => {
    for (const n of [1, 2, 3, 4, 5, 6]) {
      for (const seed of [1, 2, 3]) {
        const sim = new NightSim(NIGHTS[n]!, seed, []);
        playNight(sim, SKILLS.expert!, seed);
        for (const id of sim.loreThisNight) expect(LORE.find((l) => l.id === id)!.den, `notte ${n}: ${id}`).toBeUndefined();
      }
    }
  });
});
