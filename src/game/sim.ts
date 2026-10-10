import { FISHING, HOUR_SECONDS, LAMP, LORE, NIGHT_HOURS, VIEW, YAW, angleDiff, type LampLevel, type MonsterId, type NightConfig } from './config.ts';
import type { GameEvent } from './events.ts';
import { Fishing, type Catch } from './fishing.ts';
import { Hatch, Molly, Gulpy, Robin, SONAR_WARN, type WorldView } from './monsters.ts';
import { Rng } from './rng.ts';

export type Outcome = { kind: 'playing' } | { kind: 'won' } | { kind: 'dead'; killer: MonsterId | 'mother'; cause?: 'lullaby' };
export type HideState = 'out' | 'goingIn' | 'in' | 'goingOut';

/**
 * Una notte di SPLASHLAND IS CLOSED!, senza grafica né audio: deterministica a parità di seed e input.
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
  readonly gulpy: Gulpy;
  readonly molly: Molly;
  readonly hatch: Hatch;
  /** dalla notte 2 */
  readonly robin: Robin | null;
  /** carica della batteria, da 1 a 0 (solo se la notte ce l'ha) */
  battery = 1;
  /** la batteria è morta: lampara e sonar spenti, sale la ninna nanna */
  blackout = false;
  /** secondi che restano alla ninna nanna della Madre dopo il buio */
  lullaby = 0;
  private batteryLowSaid = false;
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
    this.fishing.snapGrace = cfg.snapGrace ?? FISHING.snapGrace;
    this.gulpy = new Gulpy(cfg.gulpy);
    this.molly = new Molly(cfg.molly);
    this.hatch = new Hatch(cfg.hatch);
    this.robin = cfg.robin ? new Robin(cfg.robin) : null;
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
    return this.molly.rocking;
  }

  facing(yaw: number, halfAngle: number): boolean {
    return Math.abs(angleDiff(this.viewYaw, yaw)) <= halfAngle;
  }

  // ───────── input ─────────

  setView(yaw: number, sonarOpen: boolean): void {
    this.viewYaw = yaw;
    // al buio anche il sonar è spento
    this.sonarOpen = sonarOpen && !this.blackout;
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
    if (!this.gulpy.canBeFed) {
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
    this.gulpy.feed(this.world);
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
    if (this.blackout) {
      this.emit({ t: 'denied', reason: 'dark' });
      return;
    }
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

    // batteria: la lampara e il sonar consumano; quando muore sale la ninna nanna della Madre
    if (this.cfg.battery) {
      if (!this.blackout) this.drainBattery(dt, this.cfg.battery);
      else {
        this.lullaby -= dt;
        if (this.lullaby <= 0) {
          this.emit({ t: 'lullaby', e: 'end' });
          this.die('mother', 'lullaby');
          return;
        }
      }
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

    this.gulpy.update(dt, w);
    this.molly.update(dt, w);
    this.hatch.update(dt, w, { hidden: this.hidden });
    this.robin?.update(dt, w, {
      fish: this.fish,
      take: () => {
        this.fish--;
      },
    });

    const killer: MonsterId | null =
      this.hatch.state === 'attack'
        ? 'hatch'
        : this.molly.state === 'attack'
          ? 'molly'
          : this.gulpy.state === 'attack'
            ? 'gulpy'
            : this.robin?.state === 'attack'
              ? 'robin'
              : null;
    if (killer) {
      this.die(killer);
      return;
    }

    const landed = this.fishing.update(dt, {
      lamp: this.lamp,
      reelHeld: this.reelHeld,
      facingRod: this.facing(YAW.rod, VIEW.rodHalfAngle) && !this.sonarOpen,
      busy: this.hide !== 'out',
      biteMul: this.cfg.biteMul,
    });
    if (landed) this.land(landed);
  }

  private drainBattery(dt: number, b: NonNullable<NightConfig['battery']>): void {
    this.battery -= dt * (b.drain[this.lamp] + (this.sonarOpen ? b.sonar : 0));
    if (!this.batteryLowSaid && this.battery < b.low) {
      this.batteryLowSaid = true;
      this.emit({ t: 'battery', e: 'low' });
    }
    if (this.battery <= 0) {
      this.battery = 0;
      this.blackout = true;
      this.sonarOpen = false;
      if (this.lamp !== 0) {
        this.lamp = 0;
        this.emit({ t: 'lamp', level: 0 });
      }
      this.emit({ t: 'battery', e: 'dead' });
      this.lullaby = b.lullaby;
      this.emit({ t: 'lullaby', e: 'start' });
      // quando canta la Madre i bambini scappano (come in FNAF, quando salta la corrente resta solo
      // Freddy): niente più visite fino alla fine della canzone (approvato il 10 ottobre)
      const w = this.world;
      this.gulpy.retreat(w);
      this.molly.retreat();
      this.hatch.retreat(w);
      this.robin?.retreat(w);
    }
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
    const species = Fishing.rollSpecies(this.rng, {
      night: this.cfg.night,
      lamp: this.lamp,
      hour: this.hour,
      near: { gulpy: this.gulpy.present, molly: this.molly.present, hatch: this.hatch.present },
    });
    return { species, lore: null, kg: this.rng.range(species.kg[0], species.kg[1]) };
  }

  /**
   * Creature che arriveranno entro pochi secondi (se la regia le lascia partire): l'ecoscandaglio
   * ne mostra l'ombra dal lato giusto. yaw in gradi come lo sguardo.
   */
  incoming(): { who: MonsterId; yaw: number; eta: number }[] {
    const out: { who: MonsterId; yaw: number; eta: number }[] = [];
    if (!this.playing) return out;
    const waiting = (s: string) => s === 'dormant' || s === 'away';
    const add = (who: MonsterId, yaw: number, timer: number) => {
      if (timer <= SONAR_WARN && this.mayStart(who, true)) out.push({ who, yaw, eta: Math.max(0, timer) });
    };
    if (waiting(this.gulpy.state)) add('gulpy', YAW.bow, this.gulpy.timer);
    if (waiting(this.molly.state)) add('molly', this.molly.yaw, this.molly.timer);
    if (waiting(this.hatch.state)) add('hatch', YAW.stern, this.hatch.timer);
    if (this.robin && waiting(this.robin.state)) add('robin', YAW.robin, this.robin.timer);
    return out;
  }

  /** la creatura è "in scena" (per le regole di esclusione della regia) */
  active(who: MonsterId): boolean {
    switch (who) {
      case 'gulpy':
        return this.gulpy.present || this.gulpy.state === 'leaving';
      case 'molly':
        return this.molly.state === 'knocking' || this.molly.present;
      case 'hatch':
        return this.hatch.present;
      case 'robin':
        return this.robin?.present ?? false;
    }
  }

  private mayStart(who: MonsterId, ignoreGap = false): boolean {
    if (!ignoreGap && this.time - this.lastStart < this.cfg.minGapBetweenStarts) return false;
    for (const [a, b] of this.cfg.exclusive) {
      if (who === a && this.active(b)) return false;
      if (who === b && this.active(a)) return false;
    }
    // niente nuovi eventi negli ultimi secondi prima dell'alba, né mentre canta la Madre
    if (this.nightLength - this.time < 12) return false;
    if (this.blackout) return false;
    return true;
  }

  private die(killer: MonsterId | 'mother', cause?: 'lullaby'): void {
    this.outcome = cause ? { kind: 'dead', killer, cause } : { kind: 'dead', killer };
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
