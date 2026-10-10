/**
 * Numeri del gioco. Tutto ciò che si bilancia sta qui (vedi scripts/balance.ts).
 * Angoli in gradi: yaw 0 = prua, positivo verso dritta (destra), ±180 = poppa.
 */

export type LampLevel = 0 | 1 | 2;
export type MonsterId = 'gulpy' | 'molly' | 'hatch' | 'robin' | 'archie';
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
  /** il secchio sul banco di prua (boat.BUCKET_POS nei render: 18,1° dall'occhio) */
  bucket: 18,
  tarp: -16,
  stern: 180,
  mollyLeft: -68,
  mollyRight: 68,
  /** Robin, steso sul bordo di sinistra verso prua, con le mani nel secchio (notte 2) */
  robin: -38,
  /** Archie, il collo dritto fuori dall'acqua davanti alla prua, la testa piegata sulla lampara (notte 3; provvisorio
   *  finché non c'è la posa renderizzata) */
  archie: 12,
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
  /** tolleranza allo strappo: a tensione piena il filo regge ancora un attimo mentre la barra trema di rosso.
   *  Le prime notti ne danno di più (NightConfig.snapGrace: 0,5 s la prima, 0,35 la seconda); dalla terza resta
   *  questa, mai zero, se no la barra che trema non servirebbe a niente */
  snapGrace: 0.2,
  /** da solo, senza che tu tiri, il pesce porta la tensione al massimo fino a qui: non spezza il filo (in tutte le
   *  notti: perdere il pesce senza aver sbagliato niente sembrerebbe un errore del gioco) */
  pullFreeMax: 0.92,
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

export interface ArchieConfig {
  firstAt: number;
  cooldown: [number, number];
  /** secondi per salire dall'acqua (dopo l'avviso del sonar) */
  rise: number;
  /** il risucchio: secondi per spegnere la lampara prima che soffi */
  inhale: number;
  /** se la riaccendi mentre aspetta al buio, riprende fiato più in fretta: secondi */
  relight: number;
  /** quanto aspetta al buio prima di rituffarsi */
  dark: number;
  /** secondi per rituffarsi */
  dive: number;
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
  /** secondi di tolleranza allo strappo, se diversi da FISHING.snapGrace (le prime notti si sfumano) */
  snapGrace?: number;
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
  /** dalla notte 3 */
  archie?: ArchieConfig;
  hideTime: number;
  unhideTime: number;
}

const H = HOUR_SECONDS;

export const NIGHTS: Record<number, NightConfig> = {
  1: {
    night: 1,
    quota: 8,
    hourlyRamp: 0.1,
    // mezzo secondo di tolleranza allo strappo (dalla prova dell'utente: «si va subito in rosso e il pesce scappa
    // in una frazione di secondo»); si sfuma nelle notti dopo
    snapGrace: 0.5,
    guaranteedLoreAt: 4,
    loreChance: 0.08,
    exclusive: [
      ['molly', 'hatch'],
      ['gulpy', 'hatch'],
    ],
    minGapBetweenStarts: 6,
    // Gulpy un po' più raro (prova dell'utente: «appare troppo spesso, togliendoti pesci dalla quota»): +20% di pausa tra
    // una visita e l'altra. Giocatori simulati dopo questo e la tolleranza allo strappo (npm run sim -- 1 300):
    // esperto 100%, medio 96%, maldestro 86% (prima 100/92/73)
    gulpy: { firstAt: 1 * H + 6, cooldown: [82, 125], rise: 7, climb: 6, patience: 8, eat: 4.5 },
    molly: { firstAt: 2 * H + 8, cooldown: [43, 70], knock: 5, attention: 4.2, neglectMax: 8, tantrumMax: 6.5 },
    hatch: { firstAt: 3 * H + 6, cooldown: [52, 79], calls: 10, callInterval: 1.1, search: [8, 10.5] },
    hideTime: 0.7,
    unhideTime: 0.6,
  },
  // Notte 2: arriva Robin e la lampara consuma la batteria (docs/NOTTI_E_MOSTRI.md). I tre della prima notte
  // tornano prima e più spesso; Hatch può arrivare mentre c'è Molly. Il mare è più vivo: i pesci abboccano
  // circa tre volte più in fretta, se no la quota 10 non si fa. Giocatori simulati (npm run sim -- 2 300):
  // esperto 100%, medio 81%, maldestro 56-57% delle notti vinte (approvato il 10 ottobre). Quando la batteria
  // muore e canta la Madre, gli altri mostri scappano (approvato).
  2: {
    night: 2,
    quota: 10,
    hourlyRamp: 0.12,
    biteMul: 0.35,
    snapGrace: 0.35,
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
  // Notte 3: arriva Archie, il serpente di mare che soffia sulla lampara (docs/NOTTI_E_MOSTRI.md): quando prende
  // fiato la lampara va spenta, e tenuta spenta finché non si rituffa. Robin e Archie mai insieme: vogliono il
  // contrario dalla luce. Dalla terza notte la tolleranza allo strappo è quella normale (FISHING.snapGrace).
  // Quota 11. Giocatori simulati (npm run sim -- 3 300): esperto 100%, medio 71%, maldestro 50% (la seconda notte
  // 100/81/58): un passo più dura. Il maldestro muore ad Archie quando riaccende troppo presto e non rispegne in
  // tempo; impara un po' a ogni volta (bot.ts). Da approvare con la notte
  3: {
    night: 3,
    quota: 11,
    hourlyRamp: 0.13,
    biteMul: 0.33,
    guaranteedLoreAt: 3,
    loreChance: 0.08,
    exclusive: [
      ['gulpy', 'hatch'],
      ['robin', 'hatch'],
      ['robin', 'molly'],
      ['archie', 'robin'],
    ],
    minGapBetweenStarts: 5,
    gulpy: { firstAt: 0.9 * H, cooldown: [66, 100], rise: 6.5, climb: 5.5, patience: 7.5, eat: 4.5 },
    molly: { firstAt: 1.5 * H, cooldown: [42, 66], knock: 4.5, attention: 4.2, neglectMax: 7.5, tantrumMax: 6 },
    hatch: { firstAt: 2.4 * H, cooldown: [50, 76], calls: 10, callInterval: 1.05, search: [8, 10.5] },
    robin: { firstAt: 1.7 * H, cooldown: [85, 130], climb: 3.5, stealEvery: 3, scare: 2.5 },
    archie: { firstAt: 0.55 * H, cooldown: [60, 95], rise: 3, inhale: 4.5, relight: 2.2, dark: 7, dive: 2 },
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
