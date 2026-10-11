/**
 * Numeri del gioco. Tutto ciò che si bilancia sta qui (vedi scripts/balance.ts).
 * Angoli in gradi: yaw 0 = prua, positivo verso dritta (destra), ±180 = poppa.
 */

export type LampLevel = 0 | 1 | 2;
export type MonsterId = 'gulpy' | 'molly' | 'hatch' | 'robin' | 'archie' | 'lampy' | 'fangy';
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
  /** Lampy aggrappata alla lenza, oltre la punta della canna: dove la lenza le entra in bocca (notte 4, la posa
   *  lampy_lenza di scena_creature.py) */
  lampy: 43,
  /** Fangy nell'acqua accanto alla barca, a destra un po' dietro il pescatore: dove sta la testa (notte 5, la posa
   *  fangy_ascolta di scena_creature.py) */
  fangy: 112,
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

export interface LampyConfig {
  firstAt: number;
  cooldown: [number, number];
  /** quando è pronta aspetta che la lenza sia in acqua, poi la prende dopo questi secondi */
  grab: [number, number];
  /** se la lenza non va in acqua per tanto tempo, se ne va senza farsi vedere (s) */
  lurkMax: number;
  /** i tre colpi del campanellino: sempre lo stesso intervallo (è il suo segnale, insieme alla risatina) */
  beat: number;
  /** dopo il terzo colpo affiora sulla lenza: secondi per salire */
  surface: number;
  /** quanto resta lì a guardarti prima di mollare la lenza */
  stay: number;
  /** se la ferri, secondi per risalire la lenza fino alla canna */
  climb: number;
}

export interface FangyConfig {
  firstAt: number;
  cooldown: [number, number];
  /** l'avviso: la fila di lucine che si avvicina sott'acqua (s) */
  approach: number;
  /** secondi per salire accanto alla barca */
  rise: number;
  /** quanto resta ad ascoltare se non fai rumore (s); ogni rumore lo trattiene almeno un poco */
  listen: number;
  /** al rumore numero tanti ti è addosso (la regola: al terzo) */
  noises: number;
  /** dopo un rumore, per quanto non ne sente un altro (s): lo stesso gesto conta una volta sola */
  deaf: number;
  /** il mulinello: recuperare fa un rumore dopo questi secondi, e poi ancora ogni tanti */
  reelNoise: number;
  /** secondi per andarsene */
  leave: number;
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
  /** in lavorazione: esiste (test, simulazioni, ?notte=N nelle prove) ma il gioco non la propone ancora */
  bozza?: boolean;
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
  /** dalla notte 4 */
  lampy?: LampyConfig;
  /** dalla notte 5 */
  fangy?: FangyConfig;
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
  // Notte 4: arriva Lampy, che prende la lenza e suona il campanellino a tempo (docs/NOTTI_E_MOSTRI.md): tre colpi
  // uguali e una risatina, poi affiora e ti guarda e molla (l'esca resta lì); ferrare è morire. È lei la protagonista:
  // viene presto e spesso. Gulpy passa più di rado (mangiava metà della quota), gli altri un po' più spesso della terza
  // notte e i pesci abboccano più in fretta. Lampy non viene con Hatch (ci si nasconde e la lenza resta lì) né con
  // Archie (due cose da sentire nello stesso momento). Quota 12. Approvata l'11 ottobre; la difficoltà la prova l'utente
  4: {
    night: 4,
    quota: 12,
    hourlyRamp: 0.15,
    biteMul: 0.21,
    guaranteedLoreAt: 3,
    loreChance: 0.08,
    exclusive: [
      ['gulpy', 'hatch'],
      ['robin', 'hatch'],
      ['robin', 'molly'],
      ['archie', 'robin'],
      ['lampy', 'hatch'],
      ['lampy', 'archie'],
    ],
    minGapBetweenStarts: 5,
    gulpy: { firstAt: 1.0 * H, cooldown: [105, 150], rise: 6.5, climb: 5.5, patience: 7.5, eat: 4.5 },
    molly: { firstAt: 1.6 * H, cooldown: [36, 58], knock: 4.5, attention: 4.2, neglectMax: 7.5, tantrumMax: 6 },
    hatch: { firstAt: 2.5 * H, cooldown: [46, 72], calls: 10, callInterval: 1.05, search: [8, 10.5] },
    robin: { firstAt: 1.9 * H, cooldown: [72, 112], climb: 3.5, stealEvery: 3, scare: 2.5 },
    archie: { firstAt: 1.2 * H, cooldown: [70, 110], rise: 3, inhale: 4.5, relight: 2.2, dark: 7, dive: 2 },
    lampy: { firstAt: 0.45 * H, cooldown: [42, 68], grab: [1.5, 4], lurkMax: 30, beat: 0.62, surface: 0.6, stay: 2.4, climb: 1.1 },
    battery: { drain: [0, 1 / 700, 1 / 320], sonar: 1 / 1100, low: 0.15, lullaby: 64 },
    hideTime: 0.7,
    unhideTime: 0.6,
  },
  // Notte 5: arriva Fangy, che è cieco e caccia a orecchio (docs/NOTTI_E_MOSTRI.md): lo annunciano le lucine che si
  // avvicinano sott'acqua; accanto alla barca ascolta, e ogni rumore (lanciare, ferrare, il mulinello, la lampara, un
  // pesce a Gulpy, il telone) lo fa voltare; al terzo è addosso. Va contro tutto il resto: con lui non vengono Hatch
  // (nascondersi fa rumore), Archie (spegnere la lampara) né Robin (accenderla al massimo); Gulpy sì (sfamarlo è un
  // rumore). Fangy viene meno spesso degli altri protagonisti, ma ogni visita ferma la pesca (gli altri sono più radi
  // e i pesci abboccano più in fretta). Quota 11: ogni visita ferma la pesca per una decina di secondi. Approvata l'11
  // ottobre (giocatori simulati: esperto 96%, medio 81%, maldestro 53%)
  5: {
    night: 5,
    quota: 11,
    hourlyRamp: 0.16,
    biteMul: 0.12,
    guaranteedLoreAt: 3,
    loreChance: 0.08,
    exclusive: [
      ['gulpy', 'hatch'],
      ['robin', 'hatch'],
      ['robin', 'molly'],
      ['archie', 'robin'],
      ['lampy', 'hatch'],
      ['lampy', 'archie'],
      ['fangy', 'hatch'],
      ['fangy', 'archie'],
      ['fangy', 'robin'],
    ],
    minGapBetweenStarts: 5,
    gulpy: { firstAt: 1.0 * H, cooldown: [120, 170], rise: 6.5, climb: 5.5, patience: 7.5, eat: 4.5 },
    molly: { firstAt: 1.6 * H, cooldown: [36, 58], knock: 4.5, attention: 4.2, neglectMax: 7.5, tantrumMax: 6 },
    hatch: { firstAt: 2.5 * H, cooldown: [46, 72], calls: 10, callInterval: 1.05, search: [8, 10.5] },
    robin: { firstAt: 1.9 * H, cooldown: [100, 150], climb: 3.5, stealEvery: 3, scare: 2.5 },
    archie: { firstAt: 1.2 * H, cooldown: [95, 145], rise: 3, inhale: 4.5, relight: 2.2, dark: 7, dive: 2 },
    lampy: { firstAt: 0.8 * H, cooldown: [75, 110], grab: [1.5, 4], lurkMax: 30, beat: 0.62, surface: 0.6, stay: 2.4, climb: 1.1 },
    fangy: { firstAt: 0.4 * H, cooldown: [85, 125], approach: 5, rise: 1.4, listen: 7, noises: 3, deaf: 0.8, reelNoise: 1.2, leave: 2 },
    battery: { drain: [0, 1 / 700, 1 / 320], sonar: 1 / 1100, low: 0.15, lullaby: 64 },
    hideTime: 0.7,
    unhideTime: 0.6,
  },
};

/** La notte in cui arriva ogni mostro (uno nuovo per notte dalla seconda; deciso il 10 ottobre). */
export const ARRIVAL: Record<MonsterId, number> = { gulpy: 1, molly: 1, hatch: 1, robin: 2, archie: 3, lampy: 4, fangy: 5 };

/** I mostri che girano nella notte n (tutti quelli arrivati fin lì: nelle notti avanzate tornano tutti). */
export function monstersOfNight(n: number): MonsterId[] {
  return (Object.keys(ARRIVAL) as MonsterId[]).filter((m) => ARRIVAL[m] <= n);
}

/**
 * Le immersioni all'alba (docs/IMMERSIONI.md): il pesce lasciato accanto a un mostro addormentato lo tiene a dormire
 * tutta la notte dopo. Si può sfamare chi gira nella notte n, tranne il mostro nuovo di quella notte: la sua tana è
 * vuota, è già in giro (deciso l'11 ottobre). La prima notte non c'è un'alba prima, quindi niente.
 */
export function canFeed(n: number, who: MonsterId): boolean {
  return n >= 2 && ARRIVAL[who] < n;
}

export function angleDiff(a: number, b: number): number {
  let d = (a - b) % 360;
  if (d > 180) d -= 360;
  if (d < -180) d += 360;
  return d;
}
