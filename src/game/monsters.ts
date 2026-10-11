import { LAMP, angleDiff, VIEW, YAW, type ArchieConfig, type FangyConfig, type HatchConfig, type LampLevel, type LampyConfig, type MollyConfig, type MonsterId, type GulpyConfig, type RobinConfig, type Side } from './config.ts';
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

  /** Canta la Madre (batteria morta): torna giù e non risale finché la canzone non finisce. */
  retreat(w: WorldView): void {
    if (!this.present) return;
    w.emit({ t: 'gulpy', e: 'leave' });
    this.go('leaving', 2.2);
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

  /** Canta la Madre: smette di bussare e scivola via. */
  retreat(): void {
    if (this.state !== 'knocking' && this.state !== 'peeking' && this.state !== 'tantrum') return;
    this.state = 'leaving';
    this.timer = 2.4;
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

  /** Canta la Madre: la conta si interrompe, scende dalla poppa. */
  retreat(w: WorldView): void {
    if (this.state !== 'counting' && this.state !== 'boarding' && this.state !== 'searching') return;
    w.emit({ t: 'hatch', e: 'leave' });
    this.state = 'leaving';
    this.timer = 1.8;
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

// ───────────────────────── Robin: il secchio, si scaccia con la luce ─────────────────────────

export type RobinState = 'dormant' | 'away' | 'climbing' | 'stealing' | 'fleeing' | 'attack';

/** Il secchio dei pesci, come lo vede Robin. */
export interface Bucket {
  fish: number;
  take(): void;
}

/**
 * Robin sale sul bordo di sinistra verso prua e allunga le mani nel secchio: ogni stealEvery secondi
 * porta via un pesce, e se il secchio è vuoto prende te. Si scaccia guardandolo in faccia con la
 * lampara al massimo per scare secondi (anche mentre sale).
 */
export class Robin {
  state: RobinState = 'dormant';
  timer: number;
  /** secondi di luce in faccia accumulati (calano piano se la luce va via) */
  lit = 0;
  /** pesci portati via in questa visita */
  stolen = 0;
  private rattleTimer = 0;

  constructor(private cfg: RobinConfig) {
    this.timer = cfg.firstAt;
  }

  get present(): boolean {
    return this.state === 'climbing' || this.state === 'stealing';
  }

  /** 0..1: quanto manca a scacciarlo (per la grafica: si ritrae nella luce) */
  get fear(): number {
    return Math.min(1, this.lit / this.cfg.scare);
  }

  update(dt: number, w: WorldView, bucket: Bucket): void {
    this.timer -= dt;
    switch (this.state) {
      case 'dormant':
      case 'away':
        if (this.timer <= 0) {
          if (w.mayStart('robin')) {
            w.started('robin');
            w.emit({ t: 'robin', e: 'climb' });
            this.state = 'climbing';
            this.timer = this.cfg.climb;
            this.lit = 0;
            this.stolen = 0;
          } else {
            this.timer = w.rng.range(3, 6);
          }
        }
        break;
      case 'climbing':
        if (this.light(dt, w)) break;
        if (this.timer <= 0) {
          w.emit({ t: 'robin', e: 'reach' });
          this.state = 'stealing';
          this.timer = this.cfg.stealEvery;
          this.rattleTimer = 0;
        }
        break;
      case 'stealing':
        if (this.light(dt, w)) break;
        this.rattleTimer -= dt;
        if (this.rattleTimer <= 0) {
          w.emit({ t: 'robin', e: 'rattle' });
          this.rattleTimer = w.rng.range(0.9, 1.5);
        }
        if (this.timer <= 0) {
          if (bucket.fish > 0) {
            bucket.take();
            this.stolen++;
            w.emit({ t: 'robin', e: 'steal' });
            this.timer = this.cfg.stealEvery;
          } else {
            this.state = 'attack';
            w.emit({ t: 'robin', e: 'attack' });
          }
        }
        break;
      case 'fleeing':
        if (this.timer <= 0) {
          w.emit({ t: 'robin', e: 'gone' });
          this.state = 'away';
          this.timer = cooldown(w, this.cfg.cooldown);
        }
        break;
      case 'attack':
        break;
    }
  }

  /** Canta la Madre: scappa come davanti alla luce. */
  retreat(w: WorldView): void {
    if (!this.present) return;
    w.emit({ t: 'robin', e: 'scared' });
    this.state = 'fleeing';
    this.timer = 1.6;
  }

  /** La lampara al massimo in faccia: se è durata abbastanza scappa (vero = è scappato). */
  private light(dt: number, w: WorldView): boolean {
    const inFace = w.lamp === 2 && !w.hidden && !w.sonarOpen && Math.abs(angleDiff(w.viewYaw, YAW.robin)) <= VIEW.robinHalfAngle;
    if (inFace) {
      this.lit += dt;
      if (this.lit >= this.cfg.scare) {
        w.emit({ t: 'robin', e: 'scared' });
        this.state = 'fleeing';
        this.timer = 1.6;
        return true;
      }
    } else {
      this.lit = Math.max(0, this.lit - dt * 0.5);
    }
    return false;
  }
}

// ───────────────────────── Archie: la lampara, va spenta ─────────────────────────

export type ArchieState = 'dormant' | 'away' | 'rising' | 'inhaling' | 'waiting' | 'diving' | 'blowing' | 'attack';

/**
 * Archie sale dall'acqua davanti alla prua, il collo dritto, la testa piegata sulla lampara, e prende fiato nella
 * trombetta (il risucchio lungo): se alla fine la lampara è ancora accesa soffia, il vetro esplode e nel buio ti è
 * addosso. Se l'hai spenta aspetta al buio per dark secondi e si rituffa; se la riaccendi prima, riprende fiato più in
 * fretta (relight). Non serve guardarlo: conta solo la luce.
 */
export class Archie {
  state: ArchieState = 'dormant';
  timer: number;

  constructor(private cfg: ArchieConfig) {
    this.timer = cfg.firstAt;
  }

  get present(): boolean {
    return this.state === 'rising' || this.state === 'inhaling' || this.state === 'waiting' || this.state === 'blowing';
  }

  /** 0..1 del risucchio in corso (per la grafica e l'audio: la trombetta si arrotola, il fischio sale) */
  get breath(): number {
    if (this.state !== 'inhaling') return this.state === 'blowing' ? 1 : 0;
    return 1 - this.timer / this.inhaleTime;
  }

  private inhaleTime = 1;

  update(dt: number, w: WorldView): void {
    this.timer -= dt;
    switch (this.state) {
      case 'dormant':
      case 'away':
        if (this.timer <= 0) {
          if (w.mayStart('archie')) {
            w.started('archie');
            w.emit({ t: 'archie', e: 'rise' });
            this.state = 'rising';
            this.timer = this.cfg.rise;
          } else {
            this.timer = w.rng.range(3, 6);
          }
        }
        break;
      case 'rising':
        if (this.timer <= 0) this.inhale(w, this.cfg.inhale, 'inhale');
        break;
      case 'inhaling':
        if (this.timer <= 0) {
          if (w.lamp > 0) {
            // soffia: il vetro della lampara esplode (la simulazione la spegne), e un attimo dopo è addosso
            w.emit({ t: 'archie', e: 'blow' });
            this.state = 'blowing';
            this.timer = 0.9;
          } else {
            w.emit({ t: 'archie', e: 'wait' });
            this.state = 'waiting';
            this.timer = this.cfg.dark;
          }
        }
        break;
      case 'waiting':
        if (w.lamp > 0) this.inhale(w, this.cfg.relight, 'relight');
        else if (this.timer <= 0) {
          w.emit({ t: 'archie', e: 'dive' });
          this.state = 'diving';
          this.timer = this.cfg.dive;
        }
        break;
      case 'diving':
        if (this.timer <= 0) {
          w.emit({ t: 'archie', e: 'gone' });
          this.state = 'away';
          this.timer = cooldown(w, this.cfg.cooldown);
        }
        break;
      case 'blowing':
        if (this.timer <= 0) {
          this.state = 'attack';
          w.emit({ t: 'archie', e: 'attack' });
        }
        break;
      case 'attack':
        break;
    }
  }

  /** Canta la Madre: si rituffa (se non ha già soffiato). */
  retreat(w: WorldView): void {
    if (this.state !== 'rising' && this.state !== 'inhaling' && this.state !== 'waiting') return;
    w.emit({ t: 'archie', e: 'dive' });
    this.state = 'diving';
    this.timer = this.cfg.dive;
  }

  private inhale(w: WorldView, time: number, e: 'inhale' | 'relight'): void {
    w.emit({ t: 'archie', e });
    this.state = 'inhaling';
    this.timer = time;
    this.inhaleTime = time;
  }
}

// ───────────────────────── Lampy: la lenza, non va ferrata (notte 4) ─────────────────────────

export type LampyState = 'dormant' | 'away' | 'lurking' | 'ringing' | 'surfacing' | 'staring' | 'letting' | 'climbing' | 'attack';

/** Quello che Lampy sa della lenza (la simulazione gliela presta). */
export interface LampyLine {
  /** la lenza è in acqua e aspetta un'abboccata */
  waiting: boolean;
  /** la lenza è ancora sua (un'abboccata finta in corso) */
  held: boolean;
  /** la prende: l'abboccata finta comincia */
  grab(): boolean;
  /** la molla: il galleggiante torna su, l'esca è ancora lì */
  release(): void;
}

/**
 * Lampy, la lampreda con la cuffia da piscina (docs/NOTTI_E_MOSTRI.md): da bambina in piscina tirava giù gli altri per
 * le gambe, per scherzo; ora tira la lenza. Prende la lenza che aspetta in acqua e fa suonare il campanellino come
 * un'abboccata, ma con un ritmo perfetto: tre colpi uguali, e dopo il secondo una risatina sott'acqua. Dopo il terzo
 * affiora sulla lenza (scelto l'11 ottobre: «dopo i tre colpi»), ti guarda, poi molla e va giù (l'esca resta lì: chi
 * aspetta perde solo il tempo della sua visita).
 * Se ferri mentre ti tiene la lenza l'hai agganciata: risale la lenza fino alla canna, ed è addosso.
 */
export class Lampy {
  state: LampyState = 'dormant';
  timer: number;
  /** colpi del campanellino suonati in questa abboccata (1..3) */
  beats = 0;
  /** secondi passati dentro lo stato (per la grafica) */
  stateTime = 0;
  private lurked = 0;

  constructor(private cfg: LampyConfig) {
    this.timer = cfg.firstAt;
  }

  /** sulla lenza, che si veda o no */
  get present(): boolean {
    return this.state === 'ringing' || this.state === 'surfacing' || this.state === 'staring' || this.state === 'letting' ||
      this.state === 'climbing';
  }

  /** fuori dall'acqua, sulla lenza */
  get visible(): boolean {
    return this.state === 'surfacing' || this.state === 'staring' || this.state === 'letting' || this.state === 'climbing';
  }

  /** tiene la lenza: se ferri adesso l'hai agganciata */
  get holding(): boolean {
    return this.state === 'ringing' || this.state === 'surfacing' || this.state === 'staring';
  }

  /** 0..1: quanto è affiorata (sale dopo il terzo colpo, scende quando molla) */
  get rise(): number {
    switch (this.state) {
      case 'surfacing':
        return Math.min(1, this.stateTime / this.cfg.surface);
      case 'staring':
      case 'climbing':
        return 1;
      case 'letting':
        return Math.max(0, 1 - this.stateTime / LAMPY_LET);
      default:
        return 0;
    }
  }

  private go(s: LampyState, t: number): void {
    this.state = s;
    this.timer = t;
    this.stateTime = 0;
  }

  update(dt: number, w: WorldView, line: LampyLine): void {
    this.timer -= dt;
    this.stateTime += dt;
    // la lenza non è più sua (ti sei nascosto, hai lanciato un pesce a Gulpy): se ne va
    if ((this.state === 'ringing' || this.state === 'surfacing' || this.state === 'staring') && !line.held) {
      this.leave(w, false);
      return;
    }
    switch (this.state) {
      case 'dormant':
      case 'away':
        if (this.timer <= 0) {
          if (w.mayStart('lampy')) {
            w.started('lampy');
            this.go('lurking', w.rng.range(this.cfg.grab[0], this.cfg.grab[1]));
            this.lurked = 0;
          } else {
            this.timer = w.rng.range(3, 6);
          }
        }
        break;
      case 'lurking':
        this.lurked += dt;
        if (!line.waiting) {
          // aspetta che la lenza torni in acqua (il timer riparte da quando ci torna)
          this.timer = Math.max(this.timer, 0.6);
          if (this.lurked > this.cfg.lurkMax) this.go('away', cooldown(w, this.cfg.cooldown));
          break;
        }
        if (this.timer <= 0 && line.grab()) {
          w.emit({ t: 'lampy', e: 'grab' });
          this.beats = 0;
          this.go('ringing', LAMPY_FIRST_BEAT);
        }
        break;
      case 'ringing':
        if (this.timer <= 0) {
          this.beats++;
          w.emit({ t: 'lampy', e: 'beat', n: this.beats });
          if (this.beats === 2) w.emit({ t: 'lampy', e: 'giggle' });
          if (this.beats < 3) this.timer += this.cfg.beat;
          else {
            w.emit({ t: 'lampy', e: 'surface' });
            this.go('surfacing', this.cfg.surface);
          }
        }
        break;
      case 'surfacing':
        if (this.timer <= 0) this.go('staring', this.cfg.stay);
        break;
      case 'staring':
        if (this.timer <= 0) this.leave(w, true, line);
        break;
      case 'letting':
        if (this.timer <= 0) {
          w.emit({ t: 'lampy', e: 'gone' });
          this.go('away', cooldown(w, this.cfg.cooldown));
        }
        break;
      case 'climbing':
        if (this.timer <= 0) {
          this.state = 'attack';
          w.emit({ t: 'lampy', e: 'attack' });
        }
        break;
      case 'attack':
        break;
    }
  }

  /** Hai ferrato mentre ti teneva la lenza: l'hai agganciata, risale la lenza fino a te. */
  hook(w: WorldView): boolean {
    if (!this.holding) return false;
    w.emit({ t: 'lampy', e: 'hooked' });
    w.emit({ t: 'lampy', e: 'climb' });
    this.go('climbing', this.cfg.climb);
    return true;
  }

  /** Canta la Madre: molla la lenza e va giù (se non l'hai già agganciata). */
  retreat(w: WorldView, line?: LampyLine): void {
    if (this.state === 'lurking') this.go('away', cooldown(w, this.cfg.cooldown));
    else if (this.holding) this.leave(w, true, line);
  }

  /** Molla la lenza: se si vedeva (o stava per affiorare) va giù sotto i tuoi occhi, se no sparisce e basta. */
  private leave(w: WorldView, release: boolean, line?: LampyLine): void {
    if (release) line?.release();
    if (this.visible || this.state === 'staring') {
      w.emit({ t: 'lampy', e: 'let' });
      this.go('letting', LAMPY_LET);
    } else {
      w.emit({ t: 'lampy', e: 'gone' });
      this.go('away', cooldown(w, this.cfg.cooldown));
    }
  }
}

/** dal momento in cui prende la lenza al primo colpo del campanellino (s) */
export const LAMPY_FIRST_BEAT = 0.3;
/** quanto ci mette ad andare giù quando molla (s) */
export const LAMPY_LET = 0.9;

// ───────────────────────── Fangy: stare zitti (notte 5) ─────────────────────────

export type FangyState = 'dormant' | 'away' | 'approaching' | 'rising' | 'listening' | 'leaving' | 'attack';

/**
 * Fangy, il pesce vipera con gli occhialini dipinti di nero (docs/NOTTI_E_MOSTRI.md): da bambino giocava a Marco Polo
 * a occhi chiusi e vinceva sempre; ora è cieco e caccia a orecchio. Lo annuncia una fila di lucine che si accende
 * sott'acqua e si avvicina; poi sale accanto alla barca, dietro di te a destra, e ascolta. Ogni rumore (lanciare,
 * ferrare, recuperare, cambiare la lampara, buttare un pesce, infilarsi sotto il telone) lo fa voltare di scatto e lo
 * trattiene; al terzo ti è addosso. Se resti zitto abbastanza, se ne va.
 */
export class Fangy {
  state: FangyState = 'dormant';
  timer: number;
  /** i rumori che ha sentito in questa visita */
  heard = 0;
  /** secondi passati dentro lo stato (per la grafica) */
  stateTime = 0;
  private deaf = 0;
  private reelFor = 0;

  constructor(private cfg: FangyConfig) {
    this.timer = cfg.firstAt;
  }

  /** accanto alla barca (fuori dall'acqua o mentre sale e scende) */
  get present(): boolean {
    return this.state === 'rising' || this.state === 'listening' || this.state === 'leaving' || this.state === 'attack';
  }

  /** ascolta: adesso i rumori contano */
  get listening(): boolean {
    return this.state === 'rising' || this.state === 'listening';
  }

  /** 0..1: le lucine che arrivano sott'acqua (l'avviso) */
  get approach(): number {
    return this.state === 'approaching' ? Math.min(1, 1 - this.timer / this.cfg.approach) : this.present ? 1 : 0;
  }

  /** 0..1: quanto è salito accanto alla barca */
  get rise(): number {
    switch (this.state) {
      case 'rising':
        return Math.min(1, this.stateTime / this.cfg.rise);
      case 'listening':
      case 'attack':
        return 1;
      case 'leaving':
        return Math.max(0, 1 - this.stateTime / this.cfg.leave);
      default:
        return 0;
    }
  }

  private go(s: FangyState, t: number): void {
    this.state = s;
    this.timer = t;
    this.stateTime = 0;
  }

  update(dt: number, w: WorldView): void {
    this.timer -= dt;
    this.stateTime += dt;
    this.deaf = Math.max(0, this.deaf - dt);
    switch (this.state) {
      case 'dormant':
      case 'away':
        if (this.timer <= 0) {
          if (w.mayStart('fangy')) {
            w.started('fangy');
            w.emit({ t: 'fangy', e: 'approach' });
            this.heard = 0;
            this.go('approaching', this.cfg.approach);
          } else {
            this.timer = w.rng.range(3, 6);
          }
        }
        break;
      case 'approaching':
        if (this.timer <= 0) {
          w.emit({ t: 'fangy', e: 'rise' });
          this.go('rising', this.cfg.rise);
        }
        break;
      case 'rising':
        if (this.timer <= 0) this.go('listening', this.cfg.listen);
        break;
      case 'listening':
        if (this.timer <= 0) {
          w.emit({ t: 'fangy', e: 'leave' });
          this.go('leaving', this.cfg.leave);
        }
        break;
      case 'leaving':
        if (this.timer <= 0) {
          w.emit({ t: 'fangy', e: 'gone' });
          this.go('away', cooldown(w, this.cfg.cooldown));
        }
        break;
      case 'attack':
        break;
    }
  }

  /** Un rumore dalla barca: se ascolta lo sente (una volta per gesto), si volta di scatto e resta; al terzo è addosso. */
  hear(w: WorldView): void {
    if (!this.listening || this.deaf > 0) return;
    this.deaf = this.cfg.deaf;
    this.heard++;
    w.emit({ t: 'fangy', e: 'snap', n: this.heard });
    if (this.heard >= this.cfg.noises) {
      this.state = 'attack';
      w.emit({ t: 'fangy', e: 'attack' });
      return;
    }
    // ti ha sentito: resta ad ascoltare almeno un altro po'
    if (this.state === 'listening') this.timer = Math.max(this.timer, this.cfg.listen * 0.6);
  }

  /** Il mulinello mentre recuperi: un rumore dopo reelNoise secondi di recupero, e poi ancora ogni reelNoise (le pause
   *  brevi, quando molli perché il pesce strattona, non cancellano il conto: cala piano). */
  reel(dt: number, w: WorldView, held: boolean): void {
    if (!this.listening) {
      this.reelFor = 0;
      return;
    }
    if (!held) {
      this.reelFor = Math.max(0, this.reelFor - 0.4 * dt);
      return;
    }
    this.reelFor += dt;
    if (this.reelFor >= this.cfg.reelNoise) {
      this.reelFor = 0;
      this.hear(w);
    }
  }

  /** Canta la Madre: torna giù (se non ti è già addosso). */
  retreat(w: WorldView): void {
    if (this.state === 'approaching') this.go('away', cooldown(w, this.cfg.cooldown));
    else if (this.state === 'rising' || this.state === 'listening') {
      w.emit({ t: 'fangy', e: 'leave' });
      this.go('leaving', this.cfg.leave);
    }
  }
}
