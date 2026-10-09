import { HOUR_SECONDS, LAMP, LORE, NIGHT_HOURS, VIEW, YAW, angleDiff, type LampLevel, type MonsterId, type NightConfig } from './config.ts';
import type { GameEvent } from './events.ts';
import { Fishing, type Catch } from './fishing.ts';
import { Cucu, Lulu, Pappo, type WorldView } from './monsters.ts';
import { Rng } from './rng.ts';

export type Outcome = { kind: 'playing' } | { kind: 'won' } | { kind: 'dead'; killer: MonsterId | 'mother' };
export type HideState = 'out' | 'goingIn' | 'in' | 'goingOut';

/**
 * Una notte di LAMPARA, senza grafica né audio: deterministica a parità di seed e input.
 * Il presentatore chiama i metodi di input, poi update(dt), poi drainEvents().
 */
export class NightSim {
  readonly rng: Rng;
  time = 0;
  hour = 0;
  /** pesci nel secchio (contano per la quota) */
  fish = 0;
  caught = 0;
  fed = 0;
  landedCount = 0;
  lamp: LampLevel = 1;
  hide: HideState = 'out';
  hideTimer = 0;
  viewYaw = 0;
  sonarOpen = false;
  reelHeld = false;
  outcome: Outcome = { kind: 'playing' };
  readonly fishing: Fishing;
  readonly pappo: Pappo;
  readonly lulu: Lulu;
  readonly cucu: Cucu;
  readonly foundLore: Set<string>;
  readonly loreThisNight: string[] = [];
  private events: GameEvent[] = [];
  private lastStart = -1e9;
  private world: WorldView;

  constructor(
    readonly cfg: NightConfig,
    seed: number,
    foundLore: Iterable<string> = [],
  ) {
    this.rng = new Rng(seed);
    this.foundLore = new Set(foundLore);
    const emit = (e: GameEvent) => this.events.push(e);
    this.fishing = new Fishing(this.rng, emit);
    this.pappo = new Pappo(cfg.pappo);
    this.lulu = new Lulu(cfg.lulu);
    this.cucu = new Cucu(cfg.cucu);
    this.world = {
      time: 0,
      hour: 0,
      lamp: 1,
      viewYaw: 0,
      sonarOpen: false,
      hidden: false,
      activity: 1,
      rng: this.rng,
      emit,
      mayStart: (who) => this.mayStart(who),
      started: () => {
        this.lastStart = this.time;
      },
    };
  }

  get hidden(): boolean {
    return this.hide === 'in';
  }

  /** 0 = fuori, 1 = completamente sotto il telone (per l'animazione) */
  get hideAmount(): number {
    switch (this.hide) {
      case 'out':
        return 0;
      case 'in':
        return 1;
      case 'goingIn':
        return 1 - this.hideTimer / this.cfg.hideTime;
      case 'goingOut':
        return this.hideTimer / this.cfg.unhideTime;
    }
  }

  get playing(): boolean {
    return this.outcome.kind === 'playing';
  }

  get nightLength(): number {
    return HOUR_SECONDS * NIGHT_HOURS;
  }

  get activity(): number {
    return (1 + this.cfg.hourlyRamp * this.hour) * LAMP.activity[this.lamp];
  }

  /** quanto dondola la barca (0..1), per la grafica e l'audio */
  get rocking(): number {
    return this.lulu.rocking;
  }

  facing(yaw: number, halfAngle: number): boolean {
    return Math.abs(angleDiff(this.viewYaw, yaw)) <= halfAngle;
  }

  // ───────── input ─────────

  setView(yaw: number, sonarOpen: boolean): void {
    this.viewYaw = yaw;
    this.sonarOpen = sonarOpen;
  }

  setReelHeld(held: boolean): void {
    this.reelHeld = held;
  }

  /** Clic sulla canna / Spazio: lancia oppure ferra. */
  pressRod(): boolean {
    if (!this.playing) return false;
    if (this.hide !== 'out' || this.sonarOpen) {
      this.emit({ t: 'denied', reason: 'busy' });
      return false;
    }
    if (!this.facing(YAW.rod, VIEW.rodHalfAngle)) {
      this.emit({ t: 'denied', reason: 'notFacing' });
      return false;
    }
    return this.fishing.press(() => this.nextCatch());
  }

  throwFish(): boolean {
    if (!this.playing) return false;
    if (this.hide !== 'out' || this.sonarOpen) {
      this.emit({ t: 'denied', reason: 'busy' });
      return false;
    }
    if (!this.pappo.canBeFed) {
      this.emit({ t: 'denied', reason: 'noTarget' });
      return false;
    }
    if (!this.facing(YAW.bow, VIEW.bowHalfAngle)) {
      this.emit({ t: 'denied', reason: 'notFacing' });
      return false;
    }
    if (this.fish <= 0) {
      this.emit({ t: 'denied', reason: 'noFish' });
      return false;
    }
    // per prendere il pesce si molla la canna
    this.fishing.abandon();
    this.fish--;
    this.fed++;
    this.emit({ t: 'throwFish' });
    this.pappo.feed(this.world);
    return true;
  }

  toggleHide(): boolean {
    if (!this.playing) return false;
    if (this.hide === 'out') {
      this.fishing.abandon();
      this.hide = 'goingIn';
      this.hideTimer = this.cfg.hideTime;
      this.sonarOpen = false;
      this.emit({ t: 'hideStart' });
      return true;
    }
    if (this.hide === 'in') {
      this.hide = 'goingOut';
      this.hideTimer = this.cfg.unhideTime;
      this.emit({ t: 'unhideStart' });
      return true;
    }
    return false;
  }

  setLamp(level: LampLevel): void {
    if (!this.playing || level === this.lamp) return;
    this.lamp = level;
    this.emit({ t: 'lamp', level });
  }

  drainEvents(): GameEvent[] {
    const e = this.events;
    this.events = [];
    return e;
  }

  // ───────── simulazione ─────────

  update(dt: number): void {
    if (!this.playing) return;
    this.time += dt;
    const h = Math.min(NIGHT_HOURS, Math.floor(this.time / HOUR_SECONDS));
    while (this.hour < h) {
      this.hour++;
      this.emit({ t: 'hour', hour: this.hour });
    }
    if (this.time >= this.nightLength) {
      this.endOfNight();
      return;
    }

    // telone
    if (this.hide === 'goingIn' || this.hide === 'goingOut') {
      this.hideTimer -= dt;
      if (this.hideTimer <= 0) {
        this.hide = this.hide === 'goingIn' ? 'in' : 'out';
        this.emit({ t: this.hide === 'in' ? 'hidden' : 'unhidden' });
      }
    }

    const w = this.world;
    w.time = this.time;
    w.hour = this.hour;
    w.lamp = this.lamp;
    w.viewYaw = this.viewYaw;
    w.sonarOpen = this.sonarOpen;
    w.hidden = this.hidden;
    w.activity = this.activity;

    this.pappo.update(dt, w);
    this.lulu.update(dt, w);
    this.cucu.update(dt, w, { hidden: this.hidden });

    const killer: MonsterId | null =
      this.cucu.state === 'attack' ? 'cucu' : this.lulu.state === 'attack' ? 'lulu' : this.pappo.state === 'attack' ? 'pappo' : null;
    if (killer) {
      this.die(killer);
      return;
    }

    const landed = this.fishing.update(dt, {
      lamp: this.lamp,
      reelHeld: this.reelHeld,
      facingRod: this.facing(YAW.rod, VIEW.rodHalfAngle) && !this.sonarOpen,
      busy: this.hide !== 'out',
    });
    if (landed) this.land(landed);
  }

  private land(c: Catch): void {
    this.landedCount++;
    if (c.lore) {
      this.foundLore.add(c.lore);
      this.loreThisNight.push(c.lore);
    } else {
      this.fish++;
      this.caught++;
    }
  }

  private nextCatch(): Catch {
    const remaining = LORE.filter((l) => l.night <= this.cfg.night && !this.foundLore.has(l.id));
    const n = this.landedCount + 1;
    let lore: string | null = null;
    if (remaining.length > 0) {
      if (n === this.cfg.guaranteedLoreAt && this.loreThisNight.length === 0) lore = remaining[0]!.id;
      else if (n > 1 && this.rng.chance(this.cfg.loreChance)) lore = this.rng.pick(remaining).id;
    }
    if (lore) return { species: null, lore, kg: 0 };
    const species = Fishing.rollSpecies(this.rng);
    return { species, lore: null, kg: this.rng.range(species.kg[0], species.kg[1]) };
  }

  /** il Piccolo è "in scena" (per le regole di esclusione della regia) */
  active(who: MonsterId): boolean {
    switch (who) {
      case 'pappo':
        return this.pappo.present || this.pappo.state === 'leaving';
      case 'lulu':
        return this.lulu.state === 'knocking' || this.lulu.present;
      case 'cucu':
        return this.cucu.present;
    }
  }

  private mayStart(who: MonsterId): boolean {
    if (this.time - this.lastStart < this.cfg.minGapBetweenStarts) return false;
    for (const [a, b] of this.cfg.exclusive) {
      if (who === a && this.active(b)) return false;
      if (who === b && this.active(a)) return false;
    }
    // niente nuovi eventi negli ultimi secondi prima dell'alba
    if (this.nightLength - this.time < 12) return false;
    return true;
  }

  private die(killer: MonsterId | 'mother'): void {
    this.outcome = { kind: 'dead', killer };
    this.emit({ t: 'dead', killer });
  }

  private endOfNight(): void {
    if (this.fish >= this.cfg.quota) {
      this.outcome = { kind: 'won' };
      this.emit({ t: 'won' });
    } else {
      this.die('mother');
    }
  }

  private emit(e: GameEvent): void {
    this.events.push(e);
  }
}
