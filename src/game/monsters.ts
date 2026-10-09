import { LAMP, angleDiff, VIEW, YAW, type CucuConfig, type LampLevel, type LuluConfig, type MonsterId, type PappoConfig, type Side } from './config.ts';
import type { GameEvent } from './events.ts';
import type { Rng } from './rng.ts';

/** Ciò che i Piccoli possono sapere del pescatore e del mondo. */
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

// ───────────────────────── Pappo: prua, va sfamato ─────────────────────────

export type PappoState = 'dormant' | 'away' | 'rising' | 'climbing' | 'demanding' | 'eating' | 'leaving' | 'attack';

export class Pappo {
  state: PappoState = 'dormant';
  timer: number;
  /** 0..1 dentro lo stato corrente, per l'animazione */
  phase = 0;
  private stateTime = 0;
  private gurgleTimer = 0;

  constructor(private cfg: PappoConfig) {
    this.timer = cfg.firstAt;
  }

  get present(): boolean {
    return this.state === 'rising' || this.state === 'climbing' || this.state === 'demanding' || this.state === 'eating';
  }

  /** Lanciargli un pesce ha senso solo quando è lì e ha fame. */
  get canBeFed(): boolean {
    return this.state === 'rising' || this.state === 'climbing' || this.state === 'demanding';
  }

  private go(s: PappoState, t: number): void {
    this.state = s;
    this.timer = t;
    this.stateTime = t;
  }

  feed(w: WorldView): void {
    if (this.state === 'rising') {
      w.emit({ t: 'pappo', e: 'fedEarly' });
      this.go('leaving', 2.2);
    } else {
      w.emit({ t: 'pappo', e: 'fed' });
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
          if (w.mayStart('pappo')) {
            w.started('pappo');
            w.emit({ t: 'pappo', e: 'rise' });
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
          w.emit({ t: 'pappo', e: 'climb' });
          this.go('climbing', this.cfg.climb);
        }
        break;
      case 'climbing':
        this.gurgle(dt, w);
        if (this.timer <= 0) {
          w.emit({ t: 'pappo', e: 'demand' });
          this.go('demanding', this.cfg.patience);
        }
        break;
      case 'demanding':
        this.gurgle(dt, w, 1.6);
        if (this.timer <= 0) {
          this.state = 'attack';
          w.emit({ t: 'pappo', e: 'attack' });
        }
        break;
      case 'eating':
        if (this.timer <= 0) {
          w.emit({ t: 'pappo', e: 'leave' });
          this.go('leaving', 2.2);
        }
        break;
      case 'leaving':
        if (this.timer <= 0) {
          w.emit({ t: 'pappo', e: 'gone' });
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
      w.emit({ t: 'pappo', e: 'gurgle' });
      this.gurgleTimer = w.rng.range(2.2, 3.6);
    }
  }
}

// ───────────────────────── Lulù: fianchi, va guardata ─────────────────────────

export type LuluState = 'dormant' | 'away' | 'knocking' | 'peeking' | 'tantrum' | 'leaving' | 'attack';

export class Lulu {
  state: LuluState = 'dormant';
  side: Side = 'left';
  timer: number;
  attention = 0;
  neglect = 0;
  tantrum = 0;
  private knockTimer = 0;
  private whined = false;

  constructor(private cfg: LuluConfig) {
    this.timer = cfg.firstAt;
  }

  get yaw(): number {
    return this.side === 'left' ? YAW.luluLeft : YAW.luluRight;
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
        if (this.timer <= 0) {
          if (w.mayStart('lulu')) {
            w.started('lulu');
            this.side = w.rng.chance(0.5) ? 'left' : 'right';
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
          w.emit({ t: 'lulu', e: 'knock', side: this.side });
          this.knockTimer = 1.7;
        }
        if (this.timer <= 0) {
          this.state = 'peeking';
          this.attention = 0;
          this.neglect = 0;
          this.tantrum = 0;
          this.whined = false;
          w.emit({ t: 'lulu', e: 'peek', side: this.side });
        }
        break;
      case 'peeking':
        if (isGazing(w, this.yaw)) {
          this.attention += dt;
          this.neglect = Math.max(0, this.neglect - dt * 0.5);
          if (this.attention >= this.cfg.attention) {
            w.emit({ t: 'lulu', e: 'giggle', side: this.side });
            this.state = 'leaving';
            this.timer = 2.4;
          }
        } else {
          this.neglect += dt;
          if (!this.whined && this.neglect > this.cfg.neglectMax * 0.55) {
            this.whined = true;
            w.emit({ t: 'lulu', e: 'whine', side: this.side });
          }
          if (this.neglect >= this.cfg.neglectMax) {
            this.state = 'tantrum';
            this.tantrum = 0;
            w.emit({ t: 'lulu', e: 'tantrum', side: this.side });
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
            w.emit({ t: 'lulu', e: 'calm', side: this.side });
          }
        } else {
          this.tantrum += dt;
          if (this.tantrum >= this.cfg.tantrumMax) {
            this.state = 'attack';
            w.emit({ t: 'lulu', e: 'attack', side: this.side });
          }
        }
        break;
      case 'leaving':
        if (this.timer <= 0) {
          w.emit({ t: 'lulu', e: 'gone', side: this.side });
          this.state = 'away';
          this.timer = cooldown(w, this.cfg.cooldown);
        }
        break;
      case 'attack':
        break;
    }
  }
}

// ───────────────────────── Cucù: poppa, nascondino ─────────────────────────

/** secondi tra l'ultimo cucù e il momento in cui è davvero a bordo */
export const BOARD_TIME = 1.3;

export type CucuState = 'dormant' | 'away' | 'counting' | 'boarding' | 'searching' | 'leaving' | 'attack';

export class Cucu {
  state: CucuState = 'dormant';
  timer: number;
  count = 0;
  /** posizione della lucina durante la perquisizione (-1..1 da sinistra a destra) */
  lureX = 0;
  private stepTimer = 0;
  private searchTotal = 0;

  constructor(private cfg: CucuConfig) {
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
          if (w.mayStart('cucu')) {
            w.started('cucu');
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
          w.emit({ t: 'cucu', e: 'count', n: this.count, last });
          if (last) {
            // l'ultimo cucù: si arrampica sulla poppa
            this.state = 'boarding';
            this.timer = BOARD_TIME;
            w.emit({ t: 'cucu', e: 'board' });
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
            w.emit({ t: 'cucu', e: 'attack' });
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
          w.emit({ t: 'cucu', e: 'attack' });
          break;
        }
        const p = this.searchProgress;
        this.lureX = Math.sin(p * Math.PI * 2.2 - Math.PI / 2) * 0.9;
        this.stepTimer -= dt;
        if (this.stepTimer <= 0) {
          const sniff = w.rng.chance(0.3);
          w.emit({ t: 'cucu', e: sniff ? 'sniff' : 'step' });
          this.stepTimer = w.rng.range(0.6, 1.3);
        }
        if (this.timer <= 0) {
          w.emit({ t: 'cucu', e: 'leave' });
          this.state = 'leaving';
          this.timer = 1.8;
        }
        break;
      }
      case 'leaving':
        if (this.timer <= 0) {
          w.emit({ t: 'cucu', e: 'gone' });
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
