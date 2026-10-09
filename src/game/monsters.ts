import { LAMP, angleDiff, VIEW, YAW, type HatchConfig, type LampLevel, type MollyConfig, type MonsterId, type GulpyConfig, type Side } from './config.ts';
import type { GameEvent } from './events.ts';
import type { Rng } from './rng.ts';

/** Ciò che le creature possono sapere del pescatore e del mondo. */
export interface WorldView {
  time: number;
  hour: number;
  lamp: LampLevel;
  viewYaw: number;
  sonarOpen: boolean;
  /** completamente sotto il telone (non in transizione) */
  hidden: boolean;
  /** attività in base all'ora e alla lampara */
  activity: number;
  rng: Rng;
  emit: (e: GameEvent) => void;
  /** la regia autorizza l'inizio di un evento? */
  mayStart: (who: MonsterId) => boolean;
  /** notifica alla regia che un evento è iniziato */
  started: (who: MonsterId) => void;
}

export function isGazing(w: WorldView, yaw: number): boolean {
  return !w.hidden && !w.sonarOpen && Math.abs(angleDiff(w.viewYaw, yaw)) <= VIEW.gazeHalfAngle;
}

function cooldown(w: WorldView, range: [number, number]): number {
  return w.rng.range(range[0], range[1]) / w.activity;
}

// ───────────────────────── Gulpy: prua, va sfamato ─────────────────────────

export type GulpyState = 'dormant' | 'away' | 'rising' | 'climbing' | 'demanding' | 'eating' | 'leaving' | 'attack';

export class Gulpy {
  state: GulpyState = 'dormant';
  timer: number;
  /** 0..1 dentro lo stato corrente, per l'animazione */
  phase = 0;
  private stateTime = 0;
  private gurgleTimer = 0;

  constructor(private cfg: GulpyConfig) {
    this.timer = cfg.firstAt;
  }

  get present(): boolean {
    return this.state === 'rising' || this.state === 'climbing' || this.state === 'demanding' || this.state === 'eating';
  }

  /** Lanciargli un pesce ha senso solo quando è lì e ha fame. */
  get canBeFed(): boolean {
    return this.state === 'rising' || this.state === 'climbing' || this.state === 'demanding';
  }

  private go(s: GulpyState, t: number): void {
    this.state = s;
    this.timer = t;
    this.stateTime = t;
  }

  feed(w: WorldView): void {
    if (this.state === 'rising') {
      w.emit({ t: 'gulpy', e: 'fedEarly' });
      this.go('leaving', 2.2);
    } else {
      w.emit({ t: 'gulpy', e: 'fed' });
      this.go('eating', this.cfg.eat);
    }
  }

  update(dt: number, w: WorldView): void {
    this.timer -= dt;
    this.phase = this.stateTime > 0 ? 1 - Math.max(0, this.timer) / this.stateTime : 0;
    switch (this.state) {
      case 'dormant':
      case 'away':
        if (this.timer <= 0) {
          if (w.mayStart('gulpy')) {
            w.started('gulpy');
            w.emit({ t: 'gulpy', e: 'rise' });
            this.go('rising', this.cfg.rise);
            this.gurgleTimer = 1.0;
          } else {
            this.timer = w.rng.range(3, 6);
          }
        }
        break;
      case 'rising':
        this.gurgle(dt, w);
        if (this.timer <= 0) {
          w.emit({ t: 'gulpy', e: 'climb' });
          this.go('climbing', this.cfg.climb);
        }
        break;
      case 'climbing':
        this.gurgle(dt, w);
        if (this.timer <= 0) {
          w.emit({ t: 'gulpy', e: 'demand' });
          this.go('demanding', this.cfg.patience);
        }
        break;
      case 'demanding':
        this.gurgle(dt, w, 1.6);
        if (this.timer <= 0) {
          this.state = 'attack';
          w.emit({ t: 'gulpy', e: 'attack' });
        }
        break;
      case 'eating':
        if (this.timer <= 0) {
          w.emit({ t: 'gulpy', e: 'leave' });
          this.go('leaving', 2.2);
        }
        break;
      case 'leaving':
        if (this.timer <= 0) {
          w.emit({ t: 'gulpy', e: 'gone' });
          this.go('away', cooldown(w, this.cfg.cooldown));
        }
        break;
      case 'attack':
        break;
    }
  }

  private gurgle(dt: number, w: WorldView, rate = 1): void {
    this.gurgleTimer -= dt * rate;
    if (this.gurgleTimer <= 0) {
      w.emit({ t: 'gulpy', e: 'gurgle' });
      this.gurgleTimer = w.rng.range(2.2, 3.6);
    }
  }
}

// ───────────────────────── Molly: fianchi, va guardata ─────────────────────────

export type MollyState = 'dormant' | 'away' | 'knocking' | 'peeking' | 'tantrum' | 'leaving' | 'attack';

/** secondi di preavviso dell'ecoscandaglio prima che una creatura arrivi */
export const SONAR_WARN = 5;

export class Molly {
  state: MollyState = 'dormant';
  side: Side = 'left';
  timer: number;
  attention = 0;
  neglect = 0;
  tantrum = 0;
  private knockTimer = 0;
  private whined = false;
  /** il lato della prossima visita è già deciso (serve all'avviso del sonar) */
  private sidePicked = false;

  constructor(private cfg: MollyConfig) {
    this.timer = cfg.firstAt;
  }

  get yaw(): number {
    return this.side === 'left' ? YAW.mollyLeft : YAW.mollyRight;
  }

  get present(): boolean {
    return this.state === 'peeking' || this.state === 'tantrum' || this.state === 'leaving';
  }

  /** 0..1: quanto forte dondola la barca */
  get rocking(): number {
    if (this.state === 'tantrum') return 0.35 + 0.65 * (this.tantrum / this.cfg.tantrumMax);
    if (this.state === 'peeking') return 0.25 * Math.max(0, (this.neglect - this.cfg.neglectMax * 0.5) / (this.cfg.neglectMax * 0.5));
    return 0;
  }

  update(dt: number, w: WorldView): void {
    this.timer -= dt;
    switch (this.state) {
      case 'dormant':
      case 'away':
        if (!this.sidePicked && this.timer <= SONAR_WARN) {
          this.side = w.rng.chance(0.5) ? 'left' : 'right';
          this.sidePicked = true;
        }
        if (this.timer <= 0) {
          if (w.mayStart('molly')) {
            w.started('molly');
            this.sidePicked = false;
            this.state = 'knocking';
            this.timer = this.cfg.knock;
            this.knockTimer = 0;
          } else {
            this.timer = w.rng.range(3, 6);
          }
        }
        break;
      case 'knocking':
        this.knockTimer -= dt;
        if (this.knockTimer <= 0) {
          w.emit({ t: 'molly', e: 'knock', side: this.side });
          this.knockTimer = 1.7;
        }
        if (this.timer <= 0) {
          this.state = 'peeking';
          this.attention = 0;
          this.neglect = 0;
          this.tantrum = 0;
          this.whined = false;
          w.emit({ t: 'molly', e: 'peek', side: this.side });
        }
        break;
      case 'peeking':
        if (isGazing(w, this.yaw)) {
          this.attention += dt;
          this.neglect = Math.max(0, this.neglect - dt * 0.5);
          if (this.attention >= this.cfg.attention) {
            w.emit({ t: 'molly', e: 'giggle', side: this.side });
            this.state = 'leaving';
            this.timer = 2.4;
          }
        } else {
          this.neglect += dt;
          if (!this.whined && this.neglect > this.cfg.neglectMax * 0.55) {
            this.whined = true;
            w.emit({ t: 'molly', e: 'whine', side: this.side });
          }
          if (this.neglect >= this.cfg.neglectMax) {
            this.state = 'tantrum';
            this.tantrum = 0;
            w.emit({ t: 'molly', e: 'tantrum', side: this.side });
          }
        }
        break;
      case 'tantrum':
        if (isGazing(w, this.yaw)) {
          this.tantrum -= dt * 1.4;
          if (this.tantrum <= 0) {
            // si calma: torna a sbirciare, ma vuole ancora attenzioni
            this.state = 'peeking';
            this.neglect = this.cfg.neglectMax * 0.4;
            this.attention = Math.min(this.attention, this.cfg.attention * 0.5);
            this.whined = true;
            w.emit({ t: 'molly', e: 'calm', side: this.side });
          }
        } else {
          this.tantrum += dt;
          if (this.tantrum >= this.cfg.tantrumMax) {
            this.state = 'attack';
            w.emit({ t: 'molly', e: 'attack', side: this.side });
          }
        }
        break;
      case 'leaving':
        if (this.timer <= 0) {
          w.emit({ t: 'molly', e: 'gone', side: this.side });
          this.state = 'away';
          this.timer = cooldown(w, this.cfg.cooldown);
        }
        break;
      case 'attack':
        break;
    }
  }
}

// ───────────────────────── Hatch: poppa, nascondino ─────────────────────────

/** secondi tra l'ultimo hatch e il momento in cui è davvero a bordo */
export const BOARD_TIME = 1.3;

export type HatchState = 'dormant' | 'away' | 'counting' | 'boarding' | 'searching' | 'leaving' | 'attack';

export class Hatch {
  state: HatchState = 'dormant';
  timer: number;
  count = 0;
  /** posizione della lucina durante la perquisizione (-1..1 da sinistra a destra) */
  lureX = 0;
  private stepTimer = 0;
  private searchTotal = 0;

  constructor(private cfg: HatchConfig) {
    this.timer = cfg.firstAt;
  }

  get present(): boolean {
    return this.state === 'counting' || this.state === 'boarding' || this.state === 'searching' || this.state === 'leaving';
  }

  /** 0..1 avanzamento della conta (per il sonar e la grafica in acqua) */
  get countProgress(): number {
    if (this.state === 'counting') return this.count / this.cfg.calls;
    return this.state === 'boarding' || this.state === 'searching' ? 1 : 0;
  }

  get searchProgress(): number {
    return this.state === 'searching' && this.searchTotal > 0 ? 1 - this.timer / this.searchTotal : 0;
  }

  update(dt: number, w: WorldView, hiding: { hidden: boolean }): void {
    this.timer -= dt;
    switch (this.state) {
      case 'dormant':
      case 'away':
        if (this.timer <= 0) {
          if (w.mayStart('hatch')) {
            w.started('hatch');
            this.state = 'counting';
            this.count = 0;
            this.timer = 0.4;
          } else {
            this.timer = w.rng.range(3, 6);
          }
        }
        break;
      case 'counting':
        if (this.timer <= 0) {
          this.count++;
          const last = this.count >= this.cfg.calls;
          w.emit({ t: 'hatch', e: 'count', n: this.count, last });
          if (last) {
            // l'ultimo hatch: si arrampica sulla poppa
            this.state = 'boarding';
            this.timer = BOARD_TIME;
            w.emit({ t: 'hatch', e: 'board' });
          } else {
            this.timer = this.cfg.callInterval;
          }
        }
        break;
      case 'boarding':
        if (this.timer <= 0) {
          // è a bordo: se non sei già sotto il telone ti trova
          if (!hiding.hidden) {
            this.state = 'attack';
            w.emit({ t: 'hatch', e: 'attack' });
            break;
          }
          this.state = 'searching';
          this.searchTotal = w.rng.range(this.cfg.search[0], this.cfg.search[1]);
          this.timer = this.searchTotal;
          this.stepTimer = 0.5;
          this.lureX = -1;
        }
        break;
      case 'searching': {
        if (!hiding.hidden) {
          this.state = 'attack';
          w.emit({ t: 'hatch', e: 'attack' });
          break;
        }
        const p = this.searchProgress;
        this.lureX = Math.sin(p * Math.PI * 2.2 - Math.PI / 2) * 0.9;
        this.stepTimer -= dt;
        if (this.stepTimer <= 0) {
          const sniff = w.rng.chance(0.3);
          w.emit({ t: 'hatch', e: sniff ? 'sniff' : 'step' });
          this.stepTimer = w.rng.range(0.6, 1.3);
        }
        if (this.timer <= 0) {
          w.emit({ t: 'hatch', e: 'leave' });
          this.state = 'leaving';
          this.timer = 1.8;
        }
        break;
      }
      case 'leaving':
        if (this.timer <= 0) {
          w.emit({ t: 'hatch', e: 'gone' });
          this.state = 'away';
          this.timer = cooldown(w, this.cfg.cooldown);
        }
        break;
      case 'attack':
        break;
    }
  }
}

export function lampActivity(lamp: LampLevel): number {
  return LAMP.activity[lamp];
}
