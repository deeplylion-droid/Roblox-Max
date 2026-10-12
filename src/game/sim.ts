import { FISHING, FOXY_PLACES, HOUR_SECONDS, LAMP, LORE, LORE_PER_NIGHT, NIGHT_HOURS, VIEW, YAW, angleDiff, type LampLevel, type MonsterId, type NightConfig } from './config.ts';
import type { GameEvent } from './events.ts';
import { Fishing, type Catch } from './fishing.ts';
import { Archie, Fangy, Foxy, Hatch, Lampy, Molly, Gulpy, Mother, Robin, SONAR_WARN, type LampyLine, type WorldView } from './monsters.ts';
import { Rng } from './rng.ts';

/** come si muore con la Madre: la ninna nanna finita al buio, o ti sei mosso mentre passava sotto la barca (notte 6);
 *  senza causa, la quota mancata alle sei */
export type MotherCause = 'lullaby' | 'moved';
export type Outcome = { kind: 'playing' } | { kind: 'won' } | { kind: 'dead'; killer: MonsterId | 'mother'; cause?: MotherCause };
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
  /** il sonar (o il binocolo) come lo tiene il pescatore, anche al buio quando lo schermo resta nero */
  private sonarAsked = false;
  /** il sonar è davvero aperto e consuma la batteria (il binocolo alzato no) */
  private sonarDrain = false;
  reelHeld = false;
  outcome: Outcome = { kind: 'playing' };
  readonly fishing: Fishing;
  readonly gulpy: Gulpy;
  readonly molly: Molly;
  readonly hatch: Hatch;
  /** dalla notte 2 */
  readonly robin: Robin | null;
  /** dalla notte 3 */
  readonly archie: Archie | null;
  /** dalla notte 4 */
  readonly lampy: Lampy | null;
  /** dalla notte 5 */
  readonly fangy: Fangy | null;
  /** la notte 6: la Madre */
  readonly mother: Mother | null;
  /** dalla notte 2: il Foxy, da tenere d'occhio col binocolo */
  readonly foxy: Foxy | null;
  /** il binocolo alzato: dove guarda e quanto è largo il campo (null: abbassato) */
  private binoView: { yaw: number; pitch: number; fov: number } | null = null;
  /** la lenza come la vede Lampy */
  private readonly lampyLine: LampyLine;
  /** Archie ha soffiato con la lampara accesa: il vetro è esploso, non si riaccende più */
  lampBroken = false;
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
    this.fishing.reelMul = cfg.reelMul ?? 1;
    this.gulpy = new Gulpy(cfg.gulpy);
    this.molly = new Molly(cfg.molly);
    this.hatch = new Hatch(cfg.hatch);
    this.robin = cfg.robin ? new Robin(cfg.robin) : null;
    this.archie = cfg.archie ? new Archie(cfg.archie) : null;
    this.lampy = cfg.lampy ? new Lampy(cfg.lampy) : null;
    this.fangy = cfg.fangy ? new Fangy(cfg.fangy) : null;
    this.mother = cfg.mother ? new Mother(cfg.mother) : null;
    this.foxy = cfg.foxy ? new Foxy(cfg.foxy, FOXY_PLACES) : null;
    const fishing = this.fishing;
    this.lampyLine = {
      get waiting() {
        return fishing.phase === 'waiting';
      },
      get held() {
        return fishing.fake !== false;
      },
      grab: () => fishing.fakeBite(),
      release: () => fishing.endFake(this.lamp, this.cfg.biteMul),
    };
    this.world = {
      time: 0,
      hour: 0,
      lamp: 1,
      viewYaw: 0,
      sonarOpen: false,
      hidden: false,
      bino: null,
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

  /**
   * Dove guardi. `away`: gli occhi sono lontani dalla barca (il sonar aperto o il binocolo alzato). `sonar`: il sonar è
   * davvero aperto e consuma la batteria (il binocolo no); assente, vale come `away`.
   */
  setView(yaw: number, away: boolean, sonar = away): void {
    this.viewYaw = yaw;
    // aprire il sonar (o alzare il binocolo) mentre la Madre passa sotto la barca è un gesto (tenerlo aperto no, anche
    // se al buio si spegne)
    if (away && !this.sonarAsked) this.stir();
    this.sonarAsked = away;
    // al buio anche il sonar è spento
    this.sonarOpen = away && !this.blackout;
    this.sonarDrain = sonar && !this.blackout;
  }

  /** Il binocolo: dove guarda (gradi) e quanto è largo il campo, o null se è abbassato. */
  setBino(v: { yaw: number; pitch: number; fov: number } | null): void {
    this.binoView = v;
  }

  setReelHeld(held: boolean): void {
    this.reelHeld = held;
  }

  /** Un gesto del pescatore: se la Madre sta passando sotto la barca, lo prende (notte 6). */
  private stir(): void {
    if (this.mother?.passing && this.playing) this.mother.moved(this.world);
  }

  /** Clic sulla canna / Spazio: lancia oppure ferra. */
  pressRod(): boolean {
    if (!this.playing) return false;
    this.stir();
    if (this.hide !== 'out' || this.sonarOpen) {
      this.emit({ t: 'denied', reason: 'busy' });
      return false;
    }
    if (!this.facing(YAW.rod, VIEW.rodHalfAngle)) {
      this.emit({ t: 'denied', reason: 'notFacing' });
      return false;
    }
    // l'abboccata era di Lampy: l'hai agganciata, risale la lenza
    if (this.lampy?.holding && this.fishing.fake === 'held') {
      this.fishing.fake = 'hooked';
      return this.lampy.hook(this.world);
    }
    const done = this.fishing.press(() => this.nextCatch());
    // il lancio e la ferrata fanno rumore (Fangy)
    if (done) this.fangy?.hear(this.world);
    return done;
  }

  throwFish(): boolean {
    if (!this.playing) return false;
    this.stir();
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
    this.fangy?.hear(this.world);
    return true;
  }

  toggleHide(): boolean {
    if (!this.playing) return false;
    this.stir();
    if (this.hide === 'out') {
      this.fishing.abandon();
      this.hide = 'goingIn';
      this.hideTimer = this.cfg.hideTime;
      this.sonarOpen = false;
      this.sonarDrain = false;
      this.emit({ t: 'hideStart' });
      this.fangy?.hear(this.world);
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
    this.stir();
    if (this.blackout) {
      this.emit({ t: 'denied', reason: 'dark' });
      return;
    }
    if (this.lampBroken) {
      this.emit({ t: 'denied', reason: 'broken' });
      return;
    }
    this.lamp = level;
    this.emit({ t: 'lamp', level });
    // il commutatore scatta: rumore (Fangy)
    this.fangy?.hear(this.world);
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
    w.bino = this.hide === 'out' ? this.binoView : null;
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
    this.archie?.update(dt, w);
    this.lampy?.update(dt, w, this.lampyLine);
    this.fangy?.update(dt, w);
    if (this.mother) this.updateMother(dt, w);
    this.foxy?.update(dt, w);
    // il mulinello mentre recuperi (Fangy)
    this.fangy?.reel(dt, w, this.reelHeld && this.fishing.phase === 'reeling' && this.hide === 'out' && !this.sonarOpen);
    if (this.archie?.state === 'blowing' && !this.lampBroken) {
      // il soffio di Archie: il vetro della lampara esplode, buio
      this.lampBroken = true;
      if (this.lamp !== 0) {
        this.lamp = 0;
        this.emit({ t: 'lamp', level: 0 });
      }
    }

    const killer: MonsterId | null =
      this.hatch.state === 'attack'
        ? 'hatch'
        : this.molly.state === 'attack'
          ? 'molly'
          : this.gulpy.state === 'attack'
            ? 'gulpy'
            : this.robin?.state === 'attack'
              ? 'robin'
              : this.archie?.state === 'attack'
                ? 'archie'
                : this.lampy?.state === 'attack'
                  ? 'lampy'
                  : this.fangy?.state === 'attack'
                    ? 'fangy'
                    : this.foxy?.state === 'attack'
                      ? 'foxy'
                      : null;
    if (killer) {
      this.die(killer);
      return;
    }
    if (this.mother?.state === 'attack') {
      this.die('mother', 'moved');
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
    this.battery -= dt * (b.drain[this.lamp] + (this.sonarDrain ? b.sonar : 0));
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
      this.retreatAll();
    }
  }

  /** I figli tornano giù tutti insieme: quando canta la Madre, o quando arriva lei (notte 6). */
  private retreatAll(): void {
    const w = this.world;
    this.gulpy.retreat(w);
    this.molly.retreat();
    this.hatch.retreat(w);
    this.robin?.retreat(w);
    this.archie?.retreat(w);
    this.lampy?.retreat(w, this.lampyLine);
    this.fangy?.retreat(w);
  }

  /**
   * La Madre (notte 6): quando comincia ad avvicinarsi i figli tornano giù; mentre passa sotto la barca il mulinello
   * tenuto è un gesto (lo sguardo lo controlla lei; il telone toccato mentre passa lo prende toggleHide, ma quello
   * tirato mentre si avvicinava può finire di muoversi da solo, come la vista che si ferma).
   */
  private updateMother(dt: number, w: WorldView): void {
    const m = this.mother!;
    const before = m.state;
    m.update(dt, w);
    if (m.state === 'approaching' && before !== 'approaching') this.retreatAll();
    if (m.passing && this.reelHeld) m.moved(w);
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
    // al massimo LORE_PER_NIGHT frammenti per notte: ognuno prende il posto di un pesce, e il bilanciamento delle notti è
    // fatto con quanti ne uscivano quando c'erano solo i due della prima notte
    if (remaining.length > 0 && this.loreThisNight.length < LORE_PER_NIGHT) {
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
    if (this.archie && waiting(this.archie.state)) add('archie', YAW.archie, this.archie.timer);
    if (this.lampy && waiting(this.lampy.state)) add('lampy', YAW.lampy, this.lampy.timer);
    if (this.fangy && waiting(this.fangy.state)) add('fangy', YAW.fangy, this.fangy.timer);
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
      case 'archie':
        return (this.archie?.present ?? false) || this.archie?.state === 'diving';
      case 'lampy':
        return (this.lampy?.present ?? false) || this.lampy?.state === 'lurking';
      case 'fangy':
        return (this.fangy?.present ?? false) || this.fangy?.state === 'approaching';
      case 'foxy':
        // sta nel suo posto per tutta la notte: non ferma gli altri
        return false;
    }
  }

  private mayStart(who: MonsterId, ignoreGap = false): boolean {
    if (!ignoreGap && this.time - this.lastStart < this.cfg.minGapBetweenStarts) return false;
    for (const [a, b] of this.cfg.exclusive) {
      if (who === a && this.active(b)) return false;
      if (who === b && this.active(a)) return false;
    }
    // niente nuovi eventi negli ultimi secondi prima dell'alba, né mentre canta la Madre o mentre lei è vicina (e
    // nemmeno appena prima che arrivi: i figli lo sanno)
    if (this.nightLength - this.time < 12) return false;
    if (this.blackout) return false;
    if (this.mother && (this.mother.near || this.mother.nextPassIn(this.time) < 8)) return false;
    return true;
  }

  private die(killer: MonsterId | 'mother', cause?: MotherCause): void {
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
