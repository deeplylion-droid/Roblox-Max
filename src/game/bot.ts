import { YAW, angleDiff, type LampLevel } from './config.ts';
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
}

export const SKILLS: Record<string, BotSkill> = {
  expert: { name: 'expert', reaction: [0.25, 0.6], turnSpeed: 420, reelHi: 0.72, reelLo: 0.3, pullReaction: 0.12, lampPolicy: 'greedy', hideAtCount: 6 },
  average: { name: 'average', reaction: [0.5, 1.2], turnSpeed: 260, reelHi: 0.68, reelLo: 0.25, pullReaction: 0.3, lampPolicy: 'steady', hideAtCount: 6 },
  sloppy: { name: 'sloppy', reaction: [0.9, 2.2], turnSpeed: 170, reelHi: 0.8, reelLo: 0.2, pullReaction: 0.55, lampPolicy: 'steady', hideAtCount: 8 },
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

    const hatchThreat = this.noticed('hatch', hatch.state === 'counting' && hatch.count >= this.skill.hideAtCount) || hatch.state === 'boarding';
    const hatchNear = hatch.state === 'counting' || hatch.state === 'boarding' || hatch.state === 'searching';
    const gulpyHungry = this.noticed('gulpy', gulpy.canBeFed);
    const mollyNeeds = this.noticed('molly', molly.state === 'peeking' || molly.state === 'tantrum');

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

    if (mollyNeeds) {
      this.turnTo(molly.yaw, dt);
    } else if (gulpyHungry && s.fish > 0 && fishing.phase !== 'reeling') {
      if (this.turnTo(YAW.bow, dt)) s.throwFish();
    } else if (gulpyHungry && s.fish > 0 && gulpy.state === 'demanding' && gulpy.timer < 3) {
      if (this.turnTo(YAW.bow, dt)) s.throwFish();
    } else {
      // pesca
      if (this.turnTo(YAW.rod - 10, dt)) {
        if (fishing.phase === 'idle') s.pressRod();
        else if (fishing.phase === 'bite' && this.noticed('bite', true)) s.pressRod();
        else if (fishing.phase === 'reeling') {
          this.pullSeenFor = fishing.pulling ? this.pullSeenFor + dt : 0;
          const pullFelt = this.pullSeenFor > this.skill.pullReaction;
          wantReel = (fishing.tension < this.skill.reelLo) || (!pullFelt && fishing.tension < this.skill.reelHi);
        }
      }
      if (fishing.phase !== 'bite') this.seen.delete('bite');
    }

    // lampara
    const anyone = gulpy.present || molly.present || hatch.present || molly.state === 'knocking';
    let lamp: LampLevel = 1;
    if (this.skill.lampPolicy === 'greedy') lamp = anyone ? 1 : 2;
    else if (this.skill.lampPolicy === 'off') lamp = 0;
    s.setLamp(lamp);
    this.finish(dt, wantReel);
  }

  private finish(_dt: number, reel: boolean): void {
    this.sim.setReelHeld(reel);
    this.sim.setView(this.yaw, false);
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
