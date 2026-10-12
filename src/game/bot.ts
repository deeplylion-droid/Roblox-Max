import { HOUR_SECONDS, NIGHT_HOURS, YAW, angleDiff, type LampLevel } from './config.ts';
import { LAMPY_FIRST_BEAT } from './monsters.ts';
import { Rng } from './rng.ts';
import type { NightSim } from './sim.ts';

/**
 * Giocatore automatico: serve per i test, per il bilanciamento (scripts/balance.ts) e per
 * collaudare il gioco vero nel browser. Ha tempi di reazione umani e gira lo sguardo a
 * velocità finita, così sbaglia come sbaglierebbe una persona.
 */
export interface BotSkill {
  name: string;
  reaction: [number, number];
  /** gradi al secondo */
  turnSpeed: number;
  /** soglie di tensione: rilascia sopra hi, tiene sotto lo */
  reelHi: number;
  reelLo: number;
  /** ritardo nel percepire uno strattone */
  pullReaction: number;
  lampPolicy: 'greedy' | 'steady' | 'off';
  /** a che hatch si nasconde */
  hideAtCount: number;
  /** quanto resta al buio con Archie che aspetta, rispetto a quanto serve (sotto 1 riaccende troppo presto) */
  archiePatience: number;
  /** probabilità di riconoscere un'abboccata di Lampy dal ritmo e dalla risatina, al secondo colpo */
  lampyEar: number;
  /** con Fangy che ascolta, quante volte al secondo ci si dimentica e si fa un gesto rumoroso */
  fangySlip: number;
  /** a ogni visita di Fangy, la probabilità di continuare a pescare lo stesso (il pesce in canna, l'abboccata)… */
  fangyGreed: number;
  /** …e quella di smettere appena lo si sente voltarsi */
  fangyStop: number;
  /** la Madre: con un pesce in canna quando arriva, la probabilità di provare a finirlo prima che passi sotto… */
  motherGreed: number;
  /** …e mentre passa, quante volte al secondo scappa un movimento (lo sguardo che si sposta, un gesto) */
  motherSlip: number;
  /** ogni quanto si alza il binocolo per controllare il Foxy, in frazioni del tempo che lui aspetta prima di lasciare il
   *  posto (un giocatore impara il ritmo della notte): fra un minimo e un massimo */
  foxyEvery: [number, number];
}

export const SKILLS: Record<string, BotSkill> = {
  expert: { name: 'expert', reaction: [0.25, 0.6], turnSpeed: 420, reelHi: 0.72, reelLo: 0.3, pullReaction: 0.12, lampPolicy: 'greedy', hideAtCount: 6, archiePatience: 1.15, lampyEar: 0.998, fangySlip: 0.004, fangyGreed: 0.03, fangyStop: 1, motherGreed: 0.01, motherSlip: 0.0003, foxyEvery: [0.45, 0.6] },
  average: { name: 'average', reaction: [0.5, 1.2], turnSpeed: 260, reelHi: 0.68, reelLo: 0.25, pullReaction: 0.3, lampPolicy: 'steady', hideAtCount: 6, archiePatience: 1.0, lampyEar: 0.97, fangySlip: 0.03, fangyGreed: 0.15, fangyStop: 0.8, motherGreed: 0.12, motherSlip: 0.003, foxyEvery: [0.5, 0.75] },
  sloppy: { name: 'sloppy', reaction: [0.9, 2.2], turnSpeed: 170, reelHi: 0.8, reelLo: 0.2, pullReaction: 0.55, lampPolicy: 'steady', hideAtCount: 8, archiePatience: 0.8, lampyEar: 0.9, fangySlip: 0.07, fangyGreed: 0.3, fangyStop: 0.55, motherGreed: 0.3, motherSlip: 0.008, foxyEvery: [0.55, 0.9] },
};

export class Bot {
  yaw = 0;
  private rng: Rng;
  private targetYaw = 0;
  private seen = new Map<string, number>();
  private pullSeenFor = 0;

  constructor(
    private sim: NightSim,
    private skill: BotSkill,
    seed = 1,
  ) {
    this.rng = new Rng(seed ^ 0x5bd1e995);
  }

  /** Vero se 'key' è vero da almeno un tempo di reazione. */
  private noticed(key: string, cond: boolean): boolean {
    if (!cond) {
      this.seen.delete(key);
      return false;
    }
    const now = this.sim.time;
    if (!this.seen.has(key)) this.seen.set(key, now + this.rng.range(this.skill.reaction[0], this.skill.reaction[1]));
    return now >= this.seen.get(key)!;
  }

  private turnTo(yaw: number, dt: number): boolean {
    this.targetYaw = yaw;
    const d = angleDiff(this.targetYaw, this.yaw);
    const step = this.skill.turnSpeed * dt;
    this.yaw = Math.abs(d) <= step ? this.targetYaw : this.yaw + Math.sign(d) * step;
    this.yaw = angleDiff(this.yaw, 0);
    return Math.abs(angleDiff(this.yaw, yaw)) < 12;
  }

  step(dt: number): void {
    const s = this.sim;
    if (!s.playing) return;
    const { gulpy, molly, hatch, fishing } = s;
    let wantReel = false;
    // sotto il telone il binocolo non si alza
    if (s.hide !== 'out') {
      this.bino = null;
      this.foxyLook = -1;
    }

    const hatchThreat = this.noticed('hatch', hatch.state === 'counting' && hatch.count >= this.skill.hideAtCount) || hatch.state === 'boarding';
    const hatchNear = hatch.state === 'counting' || hatch.state === 'boarding' || hatch.state === 'searching';
    const gulpyHungry = this.noticed('gulpy', gulpy.canBeFed);
    const mollyNeeds = this.noticed('molly', molly.state === 'peeking' || molly.state === 'tantrum');
    const robinThere = this.noticed('robin', !!s.robin?.present);

    // la Madre arriva: ci si ferma dov'è e non ci si muove finché non se n'è andata (anche sotto il telone)
    if (this.motherStill(dt)) {
      this.finish(dt, false);
      return;
    }

    // Fangy ascolta (o le sue lucine stanno arrivando): niente gesti rumorosi, salvo le dimenticanze
    const quiet = this.fangyQuiet(dt);

    // Archie prende fiato: si spegne la lampara qualunque cosa si stia facendo (anche sotto il telone)
    const archieDark = this.archieDark(dt);
    if (archieDark && !s.blackout && !s.lampBroken) s.setLamp(0);

    // sotto il telone: esce solo quando Hatch se n'è andato davvero
    if (s.hide === 'in') {
      if (this.noticed('hatchGone', !hatchNear)) s.toggleHide();
      this.finish(dt, false);
      return;
    }
    if (s.hide !== 'out') {
      this.finish(dt, false);
      return;
    }

    // il Foxy: quando tocca, e se non c'è niente di più urgente, si alza il binocolo e lo si cerca nel suo posto (se
    // arriva qualcosa di urgente mentre lo si cerca, si abbassa il binocolo)
    const threat = hatchThreat || (hatchNear && hatch.state !== 'counting') || mollyNeeds || robinThere || (gulpyHungry && s.fish > 0);
    if (this.foxyCheck(dt, !threat && fishing.phase !== 'reeling' && fishing.phase !== 'bite', threat)) {
      this.finish(dt, false);
      return;
    }

    if (hatchThreat || (hatchNear && hatch.state !== 'counting')) {
      // prima sfama Gulpy se è già lì e ci si riesce in fretta
      if (gulpyHungry && s.fish > 0 && hatch.state === 'counting' && hatch.count < 9) {
        if (this.turnTo(YAW.bow, dt)) s.throwFish();
      } else {
        s.toggleHide();
      }
      this.finish(dt, false);
      return;
    }

    let scaring = false;
    if (mollyNeeds) {
      this.turnTo(molly.yaw, dt);
    } else if (robinThere && !(gulpyHungry && s.fish > 0 && gulpy.state === 'demanding' && gulpy.timer < 2.5)) {
      // Robin nel secchio: girarsi e sparargli in faccia la lampara al massimo
      this.turnTo(YAW.robin, dt);
      scaring = true;
    } else if (gulpyHungry && s.fish > 0 && quiet && !(gulpy.state === 'demanding' && gulpy.timer < 1.5 && (s.fangy?.heard ?? 0) < 1)) {
      // con Fangy che ascolta Gulpy si sfama solo all'ultimo, e solo se Fangy non ha ancora sentito niente
      this.turnTo(YAW.bow, dt);
    } else if (gulpyHungry && s.fish > 0 && fishing.phase !== 'reeling') {
      if (this.turnTo(YAW.bow, dt)) s.throwFish();
    } else if (gulpyHungry && s.fish > 0 && gulpy.state === 'demanding' && gulpy.timer < 3) {
      if (this.turnTo(YAW.bow, dt)) s.throwFish();
    } else if (quiet) {
      // zitti: guardare la canna senza toccarla (un pesce che abbocca si lascia andare)
      this.turnTo(YAW.rod - 10, dt);
    } else {
      // pesca
      if (this.turnTo(YAW.rod - 10, dt)) {
        if (fishing.phase === 'idle') s.pressRod();
        else if (fishing.phase === 'bite' && this.strike()) s.pressRod();
        else if (fishing.phase === 'reeling') {
          this.pullSeenFor = fishing.pulling ? this.pullSeenFor + dt : 0;
          const pullFelt = this.pullSeenFor > this.skill.pullReaction;
          wantReel = (fishing.tension < this.skill.reelLo) || (!pullFelt && fishing.tension < this.skill.reelHi);
        }
      }
      if (fishing.phase !== 'bite') {
        this.seen.delete('bite');
        this.biteAt = -1;
      }
    }

    // lampara (al buio non c'è niente da fare: la batteria è morta; con Fangy che ascolta non si tocca)
    if (!s.blackout && !s.lampBroken && !quiet) {
      const anyone = gulpy.present || molly.present || hatch.present || molly.state === 'knocking';
      let lamp: LampLevel = 1;
      if (scaring) lamp = 2;
      else if (this.skill.lampPolicy === 'greedy') lamp = anyone || !this.canAffordHigh() ? 1 : 2;
      else if (this.skill.lampPolicy === 'off') lamp = 0;
      // Archie: restare al buio finché non si rituffa (chi ha poca pazienza riaccende prima)
      if (archieDark) lamp = 0;
      s.setLamp(lamp);
    }
    this.finish(dt, wantReel);
  }

  /** Archie: spenta quando lo si sente prendere fiato (col tempo di reazione), e per il tempo che serve mentre aspetta. */
  private archieDark(dt: number): boolean {
    const a = this.sim.archie;
    if (!a) return false;
    // chi ha riacceso troppo presto e l'ha sentito riprendere fiato, la volta dopo aspetta di più
    if (a.state === 'inhaling' && this.archieSeen === 'waiting') this.archieRelights++;
    if (a.state === 'away' || a.state === 'dormant') this.archieRelights = 0;
    this.archieSeen = a.state;
    const inhaling = this.noticed('archie', a.state === 'inhaling');
    if (a.state === 'waiting') {
      this.archieWait += dt;
      const cfg = this.sim.cfg.archie!;
      return this.archieWait < cfg.dark * (this.skill.archiePatience + 0.35 * this.archieRelights);
    }
    this.archieWait = 0;
    return inhaling;
  }

  /**
   * Quando ferrare: dopo il tempo di reazione; nelle notti di Lampy non prima del secondo colpo del campanellino (per
   * sentire se è a tempo), e mai se l'abboccata è sua e la si è riconosciuta (dal ritmo e dalla risatina) o la si
   * vede già affiorata sulla lenza.
   */
  private strike(): boolean {
    const s = this.sim;
    if (this.biteAt < 0) {
      this.biteAt = s.time;
      this.lampyKnown = null;
    }
    if (!this.noticed('bite', true)) return false;
    const l = s.cfg.lampy;
    if (!l) return true;
    if (s.time - this.biteAt < LAMPY_FIRST_BEAT + l.beat + 0.15) return false;
    if (!s.fishing.fake) return true;
    // la si vede quando è fuori almeno a metà
    if ((s.lampy?.rise ?? 0) >= 0.5) return false;
    if (this.lampyKnown === null) this.lampyKnown = this.rng.chance(this.skill.lampyEar);
    return !this.lampyKnown;
  }

  /** Fangy: zitti da quando sale accanto alla barca finché non torna giù (mentre le lucine arrivano i rumori non contano:
   *  si finisce di recuperare); ogni tanto ci si dimentica per un attimo. */
  private fangyQuiet(dt: number): boolean {
    const f = this.sim.fangy;
    const near = !!f && f.listening;
    // a ogni visita: si continua a pescare lo stesso? e, sentito il primo scatto della testa, si smette?
    if (f && f.state === 'rising' && this.fangySeen !== 'rising') {
      this.fangyGreedy = this.rng.chance(this.skill.fangyGreed);
      this.fangyHeard = 0;
    }
    this.fangySeen = f?.state ?? '';
    if (f && this.fangyGreedy && f.heard > this.fangyHeard) {
      this.fangyHeard = f.heard;
      if (this.rng.chance(this.skill.fangyStop)) this.fangyGreedy = false;
    }
    if (!this.noticed('fangy', near) || this.fangyGreedy) return false;
    if (this.slipT > 0) {
      this.slipT -= dt;
      return false;
    }
    if (this.rng.chance(this.skill.fangySlip * dt)) this.slipT = 0.6;
    return true;
  }

  /**
   * La Madre: mentre arriva si continua a pescare (i figli sono tutti giù), ci si ferma un attimo prima che passi sotto
   * la barca e non ci si muove finché non si è allontanata; chi ha un pesce in canna a volte non vuole mollarlo e
   * recupera ancora quando lei è già sotto; mentre passa, ogni tanto scappa un movimento.
   */
  private motherStill(dt: number): boolean {
    const m = this.sim.mother;
    if (!m) return false;
    if (m.state === 'approaching' && this.motherSeen !== 'approaching') this.motherGreedy = this.rng.chance(this.skill.motherGreed);
    this.motherSeen = m.state;
    if (m.state === 'approaching') {
      const left = this.sim.cfg.mother!.approach - m.stateTime;
      const greedy = this.motherGreedy && this.sim.fishing.phase === 'reeling';
      return left <= (greedy ? -0.4 : this.skill.reaction[1] + 0.4);
    }
    if (m.passing) {
      if (this.rng.chance(this.skill.motherSlip * dt)) this.yaw = angleDiff(this.yaw + (this.rng.chance(0.5) ? 9 : -9), 0);
      return true;
    }
    // se n'è andata: si riparte quando ce ne si accorge
    return m.state === 'leaving' && !this.noticed('motherGone', true);
  }

  private motherSeen = '';
  private motherGreedy = false;

  /**
   * Il Foxy col binocolo: quando tocca (e si è liberi) ci si gira verso il posto dove lo si è visto l'ultima volta e lo
   * si guarda per un tempo di reazione; se lì non c'è si guarda nell'altro posto. Visto sporto, il controllo dopo arriva
   * prima. Vero finché il binocolo è alzato.
   */
  private foxyCheck(dt: number, free: boolean, threat: boolean): boolean {
    const s = this.sim;
    const f = s.foxy;
    if (!f || f.state === 'dormant' || f.state === 'attack' || s.hide !== 'out' || (threat && this.foxyLook >= 0)) {
      this.foxyLook = -1;
      this.bino = null;
      return false;
    }
    const every = () => s.cfg.foxy!.leave * this.rng.range(this.skill.foxyEvery[0], this.skill.foxyEvery[1]);
    if (this.foxyNext < 0) this.foxyNext = s.time + every();
    if (this.foxyLook < 0) {
      if (s.time < this.foxyNext || !free) return false;
      this.foxyLook = this.foxyBelief;
      this.foxyTried = 0;
      this.foxyHold = -1;
      this.foxyTurn = this.snapTo(f.places[this.foxyLook]!.yaw);
    }
    const p = f.places[this.foxyLook]!;
    if (this.foxyTurn > 0) {
      this.foxyTurn -= dt;
      this.bino = null;
      if (this.foxyTurn > 0) return true;
      this.yaw = p.yaw;
    }
    this.turnTo(p.yaw, dt);
    if (Math.abs(angleDiff(this.yaw, p.yaw)) > 1) {
      this.bino = null;
      return true;
    }
    // alzato il binocolo sul posto: un attimo per alzarlo e per capire cosa si vede
    this.bino = { yaw: this.yaw, pitch: p.pitch, fov: 9 };
    if (this.foxyHold < 0) this.foxyHold = 0.4 + this.rng.range(this.skill.reaction[0], this.skill.reaction[1]);
    this.foxyHold -= dt;
    if (this.foxyHold > 0) return true;
    const there = f.place === this.foxyLook && f.stage !== null;
    if (there) {
      this.foxyBelief = this.foxyLook;
      const k = f.stage === 1 ? 0.6 : 1;
      this.foxyNext = s.time + k * every();
      this.foxyLook = -1;
      this.bino = null;
      // e di scatto si torna verso la canna (W)
      this.yaw = YAW.rod - 10;
      return false;
    }
    if (this.foxyTried + 1 < f.places.length) {
      // non c'è: si prova nell'altro posto
      this.foxyTried++;
      this.foxyLook = (this.foxyLook + 1) % f.places.length;
      this.foxyHold = -1;
      this.foxyTurn = this.snapTo(f.places[this.foxyLook]!.yaw);
      return true;
    }
    // non c'è da nessuna parte: sta arrivando, e non c'è niente da fare
    this.foxyNext = s.time + 5;
    this.foxyLook = -1;
    this.bino = null;
    return false;
  }

  /** Un posto alle spalle si raggiunge voltandosi di scatto (S): mezzo secondo. Uno davanti girando lo sguardo. */
  private snapTo(yaw: number): number {
    return Math.abs(angleDiff(this.yaw, yaw)) > 90 ? 0.35 + 0.15 : 0;
  }

  private bino: { yaw: number; pitch: number; fov: number } | null = null;
  private foxyNext = -1;
  private foxyLook = -1;
  private foxyHold = -1;
  private foxyTried = 0;
  private foxyTurn = 0;
  private foxyBelief = 0;
  private slipT = 0;
  private fangySeen = '';
  private fangyGreedy = false;
  private fangyHeard = 0;
  private biteAt = -1;
  private lampyKnown: boolean | null = null;
  private archieWait = 0;
  private archieSeen = '';
  private archieRelights = 0;

  /** Con la batteria, la lampara alta solo se resta carica per tenerla bassa fino alle sei (più un margine per Robin). */
  private canAffordHigh(): boolean {
    const b = this.sim.cfg.battery;
    if (!b) return true;
    const left = HOUR_SECONDS * NIGHT_HOURS - this.sim.time;
    return this.sim.battery > b.drain[1] * left * 1.05 + 0.06;
  }

  private finish(_dt: number, reel: boolean): void {
    this.sim.setReelHeld(reel);
    // col binocolo alzato gli occhi sono lontani dalla barca (per Molly vale come il sonar), ma non consuma
    this.sim.setView(this.yaw, this.bino !== null, false);
    this.sim.setBino(this.bino);
  }
}

/** Gioca una notte intera e restituisce il risultato. */
export function playNight(sim: NightSim, skill: BotSkill, seed = 1, dt = 1 / 30): NightSim {
  const bot = new Bot(sim, skill, seed);
  let guard = 0;
  while (sim.playing && guard++ < 200000) {
    bot.step(dt);
    sim.update(dt);
    sim.drainEvents();
  }
  return sim;
}
