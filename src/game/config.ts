/**
 * Numeri del gioco. Tutto ciò che si bilancia sta qui (vedi scripts/balance.ts).
 * Angoli in gradi: yaw 0 = prua, positivo verso dritta (destra), ±180 = poppa.
 */

export type LampLevel = 0 | 1 | 2;
export type MonsterId = 'gulpy' | 'molly' | 'hatch' | 'robin';
export type Side = 'left' | 'right';

export const HOUR_SECONDS = 75;
export const NIGHT_HOURS = 6;

/** Moltiplicatori della lampara: velocità di abboccata e attività delle creature. */
export const LAMP = {
  biteTime: [2.2, 1.0, 0.55] as const,
  activity: [0.6, 1.0, 1.6] as const,
};

/** Dove stanno le cose attorno al pescatore (devono coincidere coi render). */
export const YAW = {
  rod: 31,
  bow: 0,
  bucket: 13,
  tarp: -16,
  stern: 180,
  mollyLeft: -68,
  mollyRight: 68,
  /** Robin, steso sul bordo di sinistra verso prua, con le mani nel secchio (notte 2) */
  robin: -38,
};

export const VIEW = {
  /** semiangolo entro cui un oggetto si considera "guardato" */
  gazeHalfAngle: 30,
  /** per lanciare/recuperare bisogna essere rivolti verso la canna */
  rodHalfAngle: 55,
  /** per lanciare un pesce a Gulpy bisogna guardare verso prua */
  bowHalfAngle: 70,
  /** per scacciare Robin bisogna guardarlo in faccia (più stretto: la canna è vicina al secchio) */
  robinHalfAngle: 20,
};

export const FISHING = {
  castTime: 1.0,
  biteWait: [6, 12] as const,
  biteWindow: 2.15,
  rebaitTime: 2.0,
  landTime: 1.3,
  /** recupero */
  reelSpeed: 0.38,
  tensionHold: 0.28,
  tensionPullHold: 1.25,
  tensionPullFree: 0.12,
  tensionRelax: 0.55,
  slackEscape: 1.1,
  lookAwayEscape: 1.4,
};

export interface Species {
  id: string;
  weight: number;
  strength: number; // 0..1: frequenza/durata degli strattoni
  kg: [number, number];
}


export interface LoreItem {
  id: string;
  night: number;
}

export const LORE: LoreItem[] = [
  { id: 'wristband', night: 1 },
  { id: 'clipping', night: 1 },
];

export interface GulpyConfig {
  firstAt: number;
  cooldown: [number, number];
  rise: number;
  climb: number;
  patience: number;
  eat: number;
}

export interface MollyConfig {
  firstAt: number;
  cooldown: [number, number];
  knock: number;
  attention: number;
  neglectMax: number;
  tantrumMax: number;
}

export interface HatchConfig {
  firstAt: number;
  cooldown: [number, number];
  calls: number;
  callInterval: number;
  search: [number, number];
}

export interface RobinConfig {
  firstAt: number;
  cooldown: [number, number];
  /** secondi per salire sul bordo (dopo l'avviso del sonar) */
  climb: number;
  /** ogni quanti secondi allunga le mani nel secchio: porta via un pesce, o te se il secchio è vuoto */
  stealEvery: number;
  /** secondi di lampara al massimo in faccia per scacciarlo */
  scare: number;
}

/** La batteria della lampara e del sonar (dalla notte 2). Carica da 1 a 0. */
export interface BatteryConfig {
  /** consumo al secondo per livello della lampara (spenta, bassa, alta) */
  drain: [number, number, number];
  /** consumo in più col sonar aperto */
  sonar: number;
  /** sotto questa carica la lampara tremola */
  low: number;
  /** quando la batteria muore sale la ninna nanna della Madre: se finisce prima delle sei, la Madre sale */
  lullaby: number;
}

export interface NightConfig {
  night: number;
  quota: number;
  /** aumento dell'attività per ora di gioco (0.08 = +8%/h) */
  hourlyRamp: number;
  /** attesa dell'abboccata rispetto alla prima notte (0.8 = i pesci abboccano prima); assente: 1 */
  biteMul?: number;
  /** cattura (1-based) che garantisce un frammento di lore */
  guaranteedLoreAt: number;
  loreChance: number;
  /** regia: coppie di creature che non possono essere attivi insieme */
  exclusive: [MonsterId, MonsterId][];
  minGapBetweenStarts: number;
  gulpy: GulpyConfig;
  molly: MollyConfig;
  hatch: HatchConfig;
  /** dalla notte 2 */
  robin?: RobinConfig;
  battery?: BatteryConfig;
  hideTime: number;
  unhideTime: number;
}

const H = HOUR_SECONDS;

export const NIGHTS: Record<number, NightConfig> = {
  1: {
    night: 1,
    quota: 8,
    hourlyRamp: 0.1,
    guaranteedLoreAt: 4,
    loreChance: 0.08,
    exclusive: [
      ['molly', 'hatch'],
      ['gulpy', 'hatch'],
    ],
    minGapBetweenStarts: 6,
    gulpy: { firstAt: 1 * H + 6, cooldown: [68, 104], rise: 7, climb: 6, patience: 8, eat: 4.5 },
    molly: { firstAt: 2 * H + 8, cooldown: [43, 70], knock: 5, attention: 4.2, neglectMax: 8, tantrumMax: 6.5 },
    hatch: { firstAt: 3 * H + 6, cooldown: [52, 79], calls: 10, callInterval: 1.1, search: [8, 10.5] },
    hideTime: 0.7,
    unhideTime: 0.6,
  },
  // Notte 2: arriva Robin e la lampara consuma la batteria (docs/NOTTI_E_MOSTRI.md). I tre della prima notte
  // tornano prima e più spesso; Hatch può arrivare mentre c'è Molly. Il mare è più vivo: i pesci abboccano
  // circa tre volte più in fretta, se no la quota 10 non si fa. Giocatori simulati (npm run sim -- 2 300):
  // esperto 100%, medio 81%, maldestro 56% delle notti vinte.
  2: {
    night: 2,
    quota: 10,
    hourlyRamp: 0.12,
    biteMul: 0.35,
    guaranteedLoreAt: 3,
    loreChance: 0.08,
    exclusive: [
      ['gulpy', 'hatch'],
      ['robin', 'hatch'],
      ['robin', 'molly'],
    ],
    minGapBetweenStarts: 5,
    gulpy: { firstAt: 0.8 * H, cooldown: [64, 98], rise: 6.5, climb: 5.5, patience: 7.5, eat: 4.5 },
    molly: { firstAt: 1.3 * H, cooldown: [40, 64], knock: 4.5, attention: 4.2, neglectMax: 7.5, tantrumMax: 6 },
    hatch: { firstAt: 2.3 * H, cooldown: [48, 74], calls: 10, callInterval: 1.05, search: [8, 10.5] },
    robin: { firstAt: 0.9 * H, cooldown: [70, 110], climb: 3.5, stealEvery: 3, scare: 2.5 },
    battery: { drain: [0, 1 / 700, 1 / 320], sonar: 1 / 1100, low: 0.15, lullaby: 64 },
    hideTime: 0.7,
    unhideTime: 0.6,
  },
};

export function angleDiff(a: number, b: number): number {
  let d = (a - b) % 360;
  if (d > 180) d -= 360;
  if (d < -180) d += 360;
  return d;
}
