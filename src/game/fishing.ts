import { FISH, RARITY_WEIGHT, type FishSpecies } from './catalog.ts';
import { FISHING, LAMP, type LampLevel, type Species } from './config.ts';
import type { GameEvent } from './events.ts';
import type { Rng } from './rng.ts';

export type FishingPhase = 'idle' | 'casting' | 'waiting' | 'bite' | 'reeling' | 'landing' | 'rebait';

export interface Catch {
  species: Species | null;
  lore: string | null;
  kg: number;
}

/**
 * Pesca con la canna: lancio → attesa → abboccata (campanellino) → recupero con tensione.
 * La tensione sale tenendo premuto (molto se il pesce strattona) e scende rilasciando:
 * a 1 il filo si spezza, a 0 troppo a lungo il pesce si slama.
 */
export class Fishing {
  phase: FishingPhase = 'idle';
  timer = 0;
  tension = 0;
  progress = 0;
  pulling = false;
  private pullTimer = 0;
  private slackTime = 0;
  private lookAwayTime = 0;
  current: Catch | null = null;
  /** valore 0..1 per animare la canna (0 riposo, 1 abboccata, 2 recupero) */
  get bend(): number {
    if (this.phase === 'bite') return 1;
    if (this.phase === 'reeling') return 1 + Math.min(1, this.tension * 1.2);
    return 0;
  }
  get lineOut(): boolean {
    return this.phase === 'waiting' || this.phase === 'bite' || this.phase === 'reeling';
  }

  constructor(
    private rng: Rng,
    private emit: (e: GameEvent) => void,
  ) {}

  /** Clic sulla canna / Spazio. Restituisce true se ha avuto effetto. */
  press(nextCatch: () => Catch): boolean {
    if (this.phase === 'idle') {
      this.phase = 'casting';
      this.timer = FISHING.castTime;
      this.emit({ t: 'cast' });
      return true;
    }
    if (this.phase === 'bite') {
      this.current = nextCatch();
      this.phase = 'reeling';
      this.tension = 0.4;
      this.progress = 0;
      this.slackTime = 0;
      this.lookAwayTime = 0;
      this.pullTimer = this.rng.range(0.3, 0.8);
      this.pulling = false;
      this.emit({ t: 'hooked', species: this.current.species?.id ?? 'lore' });
      return true;
    }
    return false;
  }

  /** Abbandona la canna (nascondersi, voltarsi): il pesce in recupero scappa. */
  abandon(): void {
    if (this.phase === 'reeling') {
      this.emit({ t: 'fishEscaped' });
      this.toRebait();
    } else if (this.phase === 'bite') {
      this.emit({ t: 'baitStolen' });
      this.toRebait();
    }
  }

  private toRebait(): void {
    this.phase = 'rebait';
    this.timer = FISHING.rebaitTime;
    this.current = null;
    this.tension = 0;
    this.progress = 0;
    this.pulling = false;
  }

  update(dt: number, o: { lamp: LampLevel; reelHeld: boolean; facingRod: boolean; busy: boolean; biteMul?: number }): Catch | null {
    switch (this.phase) {
      case 'idle':
        return null;
      case 'casting':
        this.timer -= dt;
        if (this.timer <= 0) {
          this.phase = 'waiting';
          const [a, b] = FISHING.biteWait;
          this.timer = this.rng.range(a, b) * LAMP.biteTime[o.lamp] * (o.biteMul ?? 1);
          this.emit({ t: 'plop' });
        }
        return null;
      case 'waiting':
        // la lampara accelera (o rallenta) l'attesa in corso
        this.timer -= dt / LAMP.biteTime[o.lamp];
        if (this.timer <= 0) {
          this.phase = 'bite';
          this.timer = FISHING.biteWindow;
          this.emit({ t: 'bite' });
        }
        return null;
      case 'bite':
        this.timer -= dt;
        if (this.timer <= 0) {
          this.emit({ t: 'baitStolen' });
          this.toRebait();
        }
        return null;
      case 'rebait':
        this.timer -= dt;
        if (this.timer <= 0) {
          this.phase = 'idle';
          this.emit({ t: 'rebaited' });
        }
        return null;
      case 'landing':
        this.timer -= dt;
        if (this.timer <= 0) {
          const c = this.current;
          this.current = null;
          this.phase = 'idle';
          return c;
        }
        return null;
      case 'reeling':
        return this.updateReel(dt, o);
    }
  }

  private updateReel(dt: number, o: { reelHeld: boolean; facingRod: boolean; busy: boolean }): Catch | null {
    const strength = this.current?.species?.strength ?? 0.5;
    // strattoni del pesce
    this.pullTimer -= dt;
    if (this.pullTimer <= 0) {
      this.pulling = !this.pulling;
      if (this.pulling) {
        this.pullTimer = this.rng.range(0.35, 0.6 + strength * 0.6);
        this.emit({ t: 'fishPull' });
      } else {
        this.pullTimer = this.rng.range(0.7, 1.9 - strength * 0.8);
      }
    }
    const holding = o.reelHeld && o.facingRod && !o.busy;
    if (holding) {
      this.progress += FISHING.reelSpeed * dt * (this.pulling ? 0.35 : 1.0);
      this.tension += (this.pulling ? FISHING.tensionPullHold * (0.7 + strength * 0.6) : FISHING.tensionHold) * dt;
    } else {
      this.tension += (this.pulling ? FISHING.tensionPullFree : -FISHING.tensionRelax) * dt;
      if (this.pulling) this.progress = Math.max(0, this.progress - 0.05 * dt);
    }
    this.tension = Math.max(0, this.tension);
    if (!o.facingRod) {
      this.lookAwayTime += dt;
      if (this.lookAwayTime > FISHING.lookAwayEscape) {
        this.emit({ t: 'fishEscaped' });
        this.toRebait();
        return null;
      }
    } else {
      this.lookAwayTime = 0;
    }
    if (this.tension >= 1) {
      this.emit({ t: 'lineSnap' });
      this.toRebait();
      return null;
    }
    if (this.tension < 0.03) {
      this.slackTime += dt;
      if (this.slackTime > FISHING.slackEscape) {
        this.emit({ t: 'fishEscaped' });
        this.toRebait();
        return null;
      }
    } else {
      this.slackTime = 0;
    }
    if (this.progress >= 1) {
      this.phase = 'landing';
      this.timer = FISHING.landTime;
      const c = this.current!;
      this.emit({ t: 'landed', species: c.species?.id ?? null, lore: c.lore, kg: c.kg });
    }
    return null;
  }

  /** Estrae la specie del prossimo pesce. */
  /** Quale specie abbocca: dal Catalogo, fra quelle che possono abboccare adesso, pesate per rarità. */
  static rollSpecies(rng: Rng, ctx: BiteContext): Species {
    const pool = FISH.filter((s) => canBite(s, ctx));
    const f = rng.weighted((pool.length ? pool : FISH).map((s) => ({ item: s, weight: RARITY_WEIGHT[s.rarity] })));
    return { id: f.id, weight: RARITY_WEIGHT[f.rarity], strength: f.strength, kg: f.kg };
  }
}

/** Il momento dell'abboccata: notte, lampara, ora e creature nei paraggi. */
export interface BiteContext {
  night: number;
  lamp: LampLevel;
  hour: number;
  near: { gulpy: boolean; molly: boolean; hatch: boolean };
}

export function canBite(s: FishSpecies, c: BiteContext): boolean {
  const w = s.when;
  if (!w) return true;
  if (w.night && c.night < w.night) return false;
  if (w.lamp === 'dark' && c.lamp !== 0) return false;
  if (w.lamp === 'bright' && c.lamp !== 2) return false;
  if (w.from !== undefined && c.hour < w.from) return false;
  if (w.near === 'any') return c.near.gulpy || c.near.molly || c.near.hatch;
  if (w.near) return c.near[w.near];
  return true;
}
