import type { LampLevel, MonsterId, Side } from './config.ts';

/** Eventi emessi dalla simulazione: l'audio e la grafica li consumano una volta sola. */
export type GameEvent =
  | { t: 'hour'; hour: number }
  | { t: 'cast' }
  | { t: 'plop' }
  | { t: 'bite' }
  | { t: 'baitStolen' }
  | { t: 'hooked'; species: string }
  | { t: 'fishPull' }
  | { t: 'lineSnap' }
  | { t: 'fishEscaped' }
  | { t: 'landed'; species: string | null; lore: string | null; kg: number }
  | { t: 'rebaited' }
  | { t: 'lamp'; level: LampLevel }
  | { t: 'hideStart' }
  | { t: 'hidden' }
  | { t: 'unhideStart' }
  | { t: 'unhidden' }
  | { t: 'throwFish' }
  | { t: 'denied'; reason: 'noFish' | 'noTarget' | 'busy' | 'notFacing' | 'dark' | 'broken' }
  | { t: 'gulpy'; e: 'rise' | 'gurgle' | 'climb' | 'demand' | 'fed' | 'fedEarly' | 'leave' | 'gone' | 'attack' }
  | { t: 'molly'; e: 'knock' | 'peek' | 'giggle' | 'whine' | 'tantrum' | 'calm' | 'leave' | 'gone' | 'attack'; side: Side }
  | { t: 'hatch'; e: 'count' | 'board' | 'step' | 'sniff' | 'leave' | 'gone' | 'attack'; n?: number; last?: boolean }
  | { t: 'robin'; e: 'climb' | 'reach' | 'rattle' | 'steal' | 'scared' | 'gone' | 'attack' }
  | { t: 'archie'; e: 'rise' | 'inhale' | 'relight' | 'wait' | 'blow' | 'dive' | 'gone' | 'attack' }
  | { t: 'battery'; e: 'low' | 'dead' }
  | { t: 'lullaby'; e: 'start' | 'end' }
  | { t: 'dead'; killer: MonsterId | 'mother' }
  | { t: 'won' };

export type GameEventType = GameEvent['t'];
