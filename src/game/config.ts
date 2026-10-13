/**
 * Numeri del gioco. Tutto ciò che si bilancia sta qui (vedi scripts/balance.ts).
 * Angoli in gradi: yaw 0 = prua, positivo verso dritta (destra), ±180 = poppa.
 */

export type LampLevel = 0 | 1 | 2;
export type MonsterId = 'gulpy' | 'molly' | 'hatch' | 'robin' | 'archie' | 'lampy' | 'fangy' | 'foxy';
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

/**
 * I posti dove sta il Foxy, quelli che si guardano col binocolo (direzione dall'occhio, gradi; le viste in
 * overlays.json → binocular): la torre degli scivoli alle spalle (460 m) e il relitto davanti alla prua (170 m), da
 * dove salta in acqua e arriva alla barca. Scelti con la tavola del Foxy (notte fra l'11 e il 12 ottobre): l'albergo
 * Miramare, a 885 m, lo avrebbe fatto di pochi pixel.
 */
/** il nome del Foxy nel gioco (scelto dall'utente il 12 ottobre); nel codice resta «foxy» */
export const FOXY_NAME = 'Soggy';

export const FOXY_PLACES: { id: string; yaw: number; pitch: number }[] = [
  { id: 'scivoli', yaw: -167, pitch: 1.8 },
  { id: 'relitto', yaw: 13.955, pitch: 0.42 },
];

export const VIEW = {
  /** semiangolo entro cui un oggetto si considera "guardato" */
  gazeHalfAngle: 30,
  /** per lanciare/recuperare bisogna essere rivolti verso la canna */
  rodHalfAngle: 55,
  /** per lanciare un pesce a Gulpy bisogna guardare verso prua */
  bowHalfAngle: 70,
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
  /** trovata nella tana di questo mostro durante le immersioni (non si pesca): night è la notte in cui arriva */
  den?: MonsterId;
}

/** Frammenti al massimo in una notte (deciso l'11 ottobre sera, coi dieci frammenti nuovi: il bilanciamento resta quello). */
export const LORE_PER_NIGHT = 2;

export const LORE: LoreItem[] = [
  { id: 'wristband', night: 1 },
  { id: 'clipping', night: 1 },
  // approvati l'11 ottobre sera: due per notte dalla 2 alla 6 (prima c'erano solo i due della notte 1)
  { id: 'clipping_snack', night: 2 },
  { id: 'tickets', night: 2 },
  { id: 'flyer', night: 3 },
  { id: 'clipping_birthday', night: 3 },
  { id: 'swim_cap', night: 4 },
  { id: 'clipping_lido', night: 4 },
  { id: 'goggles', night: 5 },
  { id: 'clipping_seventh', night: 5 },
  { id: 'clipping_storm', night: 6 },
  { id: 'notebook', night: 6 },
  // le cose da trovare nelle tane delle immersioni (12 ottobre, approvate il 13): una per tana, non si pescano
  { id: 'den_gulpy', night: 1, den: 'gulpy' },
  { id: 'den_molly', night: 1, den: 'molly' },
  { id: 'den_hatch', night: 1, den: 'hatch' },
  { id: 'den_robin', night: 2, den: 'robin' },
  { id: 'den_archie', night: 3, den: 'archie' },
  { id: 'den_lampy', night: 4, den: 'lampy' },
  { id: 'den_fangy', night: 5, den: 'fangy' },
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

/** Il Foxy (dalla notte 2, deciso l'11 ottobre sera): va tenuto d'occhio col binocolo. */
export interface FoxyConfig {
  /** secondi dall'inizio della notte prima che compaia nel suo posto */
  firstAt: number;
  /** secondi senza guardarlo prima che si sporga verso di te */
  lean: number;
  /** secondi senza guardarlo prima che lasci il posto: il posto è vuoto, sta arrivando */
  leave: number;
  /** secondi dal posto vuoto al salto sulla barca */
  run: number;
  /** probabilità che cambi posto quando smetti di guardarlo (se i posti sono due) */
  swap: number;
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

/**
 * La Madre (notte 6): per tutta la notte la sua ombra gira lontana sul sonar; poche volte si avvicina e passa sotto
 * la barca, e mentre passa serve l'immobilità totale (nessun gesto, lo sguardo fermo). I figli tornano giù appena
 * arriva e non risalgono finché non se n'è andata.
 */
export interface MotherConfig {
  /** quando comincia ad avvicinarsi, una volta per passata (secondi dall'inizio della notte) */
  passes: number[];
  /** l'avviso: quanto ci mette ad arrivare sotto la barca (s) */
  approach: number;
  /** quanto dura ogni passata sotto la barca (s), una per passata; sempre più lunghe */
  pass: number[];
  /** quanto ci mette ad allontanarsi, prima che i figli possano tornare (s) */
  leave: number;
  /** di quanti gradi si può girare lo sguardo durante la passata senza che se ne accorga (un tremito) */
  still: number;
  /** quanti secondi impiega l'ombra lontana a fare il giro della barca sul sonar */
  circle: number;
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
  /** recupero più veloce (1,3 = il 30% in meno di tempo per tirare su un pesce); assente: 1. Dalla notte 2 compensa il
   *  tempo che si passa col binocolo per il Foxy (indicazione dell'utente, 11 ottobre sera: «se devi bilanciare, riduci il
   *  tempo necessario per tirare su i pesci») */
  reelMul?: number;
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
  /** dalla notte 6 */
  mother?: MotherConfig;
  /** dalla notte 2: il Foxy, da tenere d'occhio col binocolo */
  foxy?: FoxyConfig;
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
    // una visita e l'altra. Dopo la pesca più corta la notte era di nuovo troppo facile (prova dell'utente del 12
    // ottobre: «leggermente troppo facile», nella prima notte non c'è Soggy): Molly e Hatch tornano un 15% più spesso
    // (tolgono tempo alla pesca, non pesci). Giocatori simulati (npm run sim -- 1 300): esperto 100%, medio 92%,
    // maldestro 73%, di nuovo vicino all'obiettivo del maldestro al 75% (prima 100/96/86)
    gulpy: { firstAt: 1 * H + 6, cooldown: [82, 125], rise: 7, climb: 6, patience: 8, eat: 4.5 },
    molly: { firstAt: 2 * H + 8, cooldown: [37, 60], knock: 5, attention: 4.2, neglectMax: 8, tantrumMax: 6.5 },
    hatch: { firstAt: 3 * H + 6, cooldown: [44, 67], calls: 10, callInterval: 1.1, search: [8, 10.5] },
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
    reelMul: 1.1,
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
    foxy: { firstAt: 0.9 * H, lean: 46, leave: 85, run: 3.5, swap: 0.15 },
    battery: { drain: [0, 1 / 560, 1 / 240], sonar: 1 / 800, low: 0.15, lullaby: 64 },
    hideTime: 0.7,
    unhideTime: 0.6,
  },
  // Notte 3: arriva Archie, il serpente di mare che soffia sulla lampara (docs/NOTTI_E_MOSTRI.md): quando prende
  // fiato la lampara va spenta, e tenuta spenta finché non si rituffa. Robin e Archie mai insieme: vogliono il
  // contrario dalla luce. Dalla terza notte la tolleranza allo strappo è quella normale (FISHING.snapGrace).
  // Quota 11. Giocatori simulati (npm run sim -- 3 300): esperto 100%, medio 71%, maldestro 50% (la seconda notte
  // 100/81/58): un passo più dura. Il maldestro muore ad Archie quando riaccende troppo presto e non rispegne in
  // tempo; impara un po' a ogni volta (bot.ts). Approvata l'11 ottobre con la notte.
  3: {
    night: 3,
    quota: 11,
    hourlyRamp: 0.13,
    biteMul: 0.33,
    reelMul: 1.06,
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
    foxy: { firstAt: 0.7 * H, lean: 44, leave: 82, run: 3.2, swap: 0.2 },
    archie: { firstAt: 0.55 * H, cooldown: [60, 95], rise: 3, inhale: 4.5, relight: 2.2, dark: 7, dive: 2 },
    battery: { drain: [0, 1 / 560, 1 / 240], sonar: 1 / 800, low: 0.15, lullaby: 64 },
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
    reelMul: 1.15,
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
    foxy: { firstAt: 0.6 * H, lean: 40, leave: 72, run: 3, swap: 0.3 },
    archie: { firstAt: 1.2 * H, cooldown: [70, 110], rise: 3, inhale: 4.5, relight: 2.2, dark: 7, dive: 2 },
    lampy: { firstAt: 0.45 * H, cooldown: [42, 68], grab: [1.5, 4], lurkMax: 30, beat: 0.62, surface: 0.6, stay: 2.4, climb: 1.1 },
    battery: { drain: [0, 1 / 560, 1 / 240], sonar: 1 / 800, low: 0.15, lullaby: 64 },
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
    reelMul: 1.08,
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
    foxy: { firstAt: 0.5 * H, lean: 36, leave: 66, run: 3, swap: 0.35 },
    archie: { firstAt: 1.2 * H, cooldown: [95, 145], rise: 3, inhale: 4.5, relight: 2.2, dark: 7, dive: 2 },
    lampy: { firstAt: 0.8 * H, cooldown: [75, 110], grab: [1.5, 4], lurkMax: 30, beat: 0.62, surface: 0.6, stay: 2.4, climb: 1.1 },
    fangy: { firstAt: 0.4 * H, cooldown: [85, 125], approach: 5, rise: 1.4, listen: 7, noises: 3, deaf: 0.8, reelNoise: 1.2, leave: 2 },
    battery: { drain: [0, 1 / 560, 1 / 240], sonar: 1 / 800, low: 0.15, lullaby: 64 },
    hideTime: 0.7,
    unhideTime: 0.6,
  },
  // Notte 6: la Madre, il finale (approvato l'11 ottobre, docs/NOTTI_E_MOSTRI.md). Tornano tutti e sette i figli e la
  // regia ne manda di più insieme; tre volte (verso le 2, le 4 e le 5:30) arriva lei: i figli tornano giù, e mentre
  // passa sotto la barca (10, 15, 20 s) serve l'immobilità totale. Quota 10 (nella proposta 12: ma ogni passata ferma
  // la pesca per una trentina di secondi; giocatori simulati: esperto 86%, medio 68%, maldestro 34%). Giocabile dalla
  // notte del 12 ottobre: c'è il suo aspetto (la posa del finale A e il jumpscare, scelti col via libera dell'utente)
  6: {
    night: 6,
    quota: 10,
    hourlyRamp: 0.17,
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
    minGapBetweenStarts: 4,
    gulpy: { firstAt: 0.9 * H, cooldown: [110, 155], rise: 6.5, climb: 5.5, patience: 7.5, eat: 4.5 },
    molly: { firstAt: 1.3 * H, cooldown: [34, 54], knock: 4.5, attention: 4.2, neglectMax: 7.5, tantrumMax: 6 },
    hatch: { firstAt: 2.3 * H, cooldown: [44, 68], calls: 10, callInterval: 1.05, search: [8, 10.5] },
    robin: { firstAt: 1.6 * H, cooldown: [95, 140], climb: 3.5, stealEvery: 3, scare: 2.5 },
    archie: { firstAt: 1.1 * H, cooldown: [90, 135], rise: 3, inhale: 4.5, relight: 2.2, dark: 7, dive: 2 },
    lampy: { firstAt: 0.7 * H, cooldown: [70, 105], grab: [1.5, 4], lurkMax: 30, beat: 0.62, surface: 0.6, stay: 2.4, climb: 1.1 },
    fangy: { firstAt: 0.5 * H, cooldown: [80, 120], approach: 5, rise: 1.4, listen: 7, noises: 3, deaf: 0.8, reelNoise: 1.2, leave: 2 },
    mother: { passes: [2 * H - 10, 4 * H - 10, 5.5 * H - 10], approach: 10, pass: [10, 15, 20], leave: 6, still: 4, circle: 70 },
    battery: { drain: [0, 1 / 560, 1 / 240], sonar: 1 / 800, low: 0.15, lullaby: 64 },
    hideTime: 0.7,
    unhideTime: 0.6,
  },
};

/** La notte in cui arriva un mostro (la prima che lo ha). I suggerimenti sulle sue regole si vedono solo quella notte
 *  (scelta dell'utente del 12 ottobre sera), o sempre con «Tutorial sempre attivo»; nella notte extra no. */
export function debutNight(who: MonsterId | 'mother'): number {
  for (let n = 1; NIGHTS[n]; n++) if (NIGHTS[n]![who]) return n;
  return Infinity;
}

// ───────────────────────── Notte 7: la notte extra ─────────────────────────
// Come la «custom night» di FNAF: per ognuno dei sette mostri si sceglie un livello da 0 (non viene) a 20
// (feroce). La config non sta in NIGHTS: si costruisce dai livelli con extraNight(). Approvata il 13 ottobre
// con la notte (docs/NOTTI_E_MOSTRI.md, «Notte 7 · La notte extra»).

/** il numero della notte extra (la 6 è il posto della Madre) */
export const EXTRA_NIGHT = 7;
export const EXTRA_MAX = 20;

/** i sette mostri delle notti, i figli (il Foxy non è uno di loro: non ha una tana e si guarda col binocolo) */
export type NightMonster = Exclude<MonsterId, 'foxy'>;

/** i sette mostri, nell'ordine in cui arrivano nelle notti (è anche l'ordine della schermata dei livelli) */
export const MONSTERS: NightMonster[] = ['gulpy', 'molly', 'hatch', 'robin', 'archie', 'lampy', 'fangy'];

/** chi si sceglie nella notte extra: i sette mostri, ottava la Madre (deciso dall'utente l'11 ottobre) e nono il Foxy,
 *  Soggy (deciso il 12 ottobre) */
export type ExtraId = NightMonster | 'mother' | 'foxy';
export const EXTRA_IDS: ExtraId[] = [...MONSTERS, 'mother', 'foxy'];

export type ExtraLevels = Record<ExtraId, number>;

export function extraLevels(level: number): ExtraLevels {
  return { gulpy: level, molly: level, hatch: level, robin: level, archie: level, lampy: level, fangy: level, mother: level, foxy: level };
}

/** Le preimpostazioni della schermata (approvate il 13 ottobre). */
export const EXTRA_PRESETS: { id: string; levels: ExtraLevels }[] = [
  { id: 'all0', levels: extraLevels(0) },
  { id: 'all5', levels: extraLevels(5) },
  { id: 'all10', levels: extraLevels(10) },
  { id: 'all20', levels: extraLevels(20) },
  // i tre della prima notte, ma feroci
  { id: 'first3', levels: { gulpy: 15, molly: 15, hatch: 15, robin: 0, archie: 0, lampy: 0, fangy: 0, mother: 0, foxy: 0 } },
];

/** un livello valido: intero da 0 a EXTRA_MAX */
export function clampLevel(n: number): number {
  return Math.max(0, Math.min(EXTRA_MAX, Math.round(Number.isFinite(n) ? n : 0)));
}

type Num = Record<string, number | [number, number]>;

/**
 * Ogni mostro ha tre punti di riferimento, e fra l'uno e l'altro i numeri si sfumano in linea retta:
 * - livello 1, «calmo»: arriva tardi e torna di rado (le pause sono 1,6 volte quelle della notte in cui arriva);
 * - livello 5, «come la sua notte»: i numeri della notte in cui arriva per la prima volta (Gulpy, Molly e Hatch
 *   la prima, Robin la seconda, Archie la terza, Lampy la quarta, Fangy la quinta);
 * - livello 20, «feroce»: arriva subito e ha meno pazienza che nella quinta notte. Le pause del punto feroce (quasi
 *   la metà di quelle della sua notte) danno solo la pendenza fra il 5 e il 10: dal 10 al 20 le pause restano quelle
 *   del 10 (monsterAt), se no tutti a 20 era impossibile.
 * Le regole che il giocatore impara (i dieci della conta, i tre colpi di Lampy, il terzo rumore di Fangy) non cambiano
 * mai: cambiano solo la frequenza e la pazienza.
 */
/** chi ha i tre punti di riferimento: i sette mostri e il Foxy (la Madre ha i suoi numeri, extraMother) */
type Anchored = NightMonster | 'foxy';

const EXTRA_ANCHORS: Record<Anchored, { calm: Num; debut: Num; fierce: Num }> = {
  gulpy: {
    calm: { firstAt: 2.2 * H, cooldown: [131, 200], rise: 7, climb: 6, patience: 8.5, eat: 4.5 },
    debut: { firstAt: 1 * H + 6, cooldown: [82, 125], rise: 7, climb: 6, patience: 8, eat: 4.5 },
    fierce: { firstAt: 0.3 * H, cooldown: [68, 102], rise: 5.5, climb: 4.5, patience: 6.5, eat: 4.5 },
  },
  molly: {
    calm: { firstAt: 3 * H, cooldown: [69, 112], knock: 5, attention: 4.2, neglectMax: 8.5, tantrumMax: 7 },
    debut: { firstAt: 2 * H + 8, cooldown: [37, 60], knock: 5, attention: 4.2, neglectMax: 8, tantrumMax: 6.5 },
    fierce: { firstAt: 0.4 * H, cooldown: [34, 54], knock: 4, attention: 4.5, neglectMax: 6.5, tantrumMax: 5.2 },
  },
  hatch: {
    calm: { firstAt: 3.8 * H, cooldown: [83, 126], calls: 10, callInterval: 1.15, search: [7.5, 10] },
    debut: { firstAt: 3 * H + 6, cooldown: [44, 67], calls: 10, callInterval: 1.1, search: [8, 10.5] },
    fierce: { firstAt: 0.6 * H, cooldown: [35, 55], calls: 10, callInterval: 0.9, search: [9, 12] },
  },
  robin: {
    calm: { firstAt: 1.8 * H, cooldown: [112, 176], climb: 4, stealEvery: 3.4, scare: 2.4 },
    debut: { firstAt: 0.9 * H, cooldown: [70, 110], climb: 3.5, stealEvery: 3, scare: 2.5 },
    fierce: { firstAt: 0.3 * H, cooldown: [50, 78], climb: 2.8, stealEvery: 2.4, scare: 2.8 },
  },
  archie: {
    calm: { firstAt: 1.5 * H, cooldown: [96, 152], rise: 3.4, inhale: 5, relight: 2.4, dark: 6.5, dive: 2 },
    debut: { firstAt: 0.55 * H, cooldown: [60, 95], rise: 3, inhale: 4.5, relight: 2.2, dark: 7, dive: 2 },
    fierce: { firstAt: 0.25 * H, cooldown: [42, 68], rise: 2.5, inhale: 3.6, relight: 1.8, dark: 8.5, dive: 2 },
  },
  lampy: {
    calm: { firstAt: 1.4 * H, cooldown: [67, 109], grab: [2, 5], lurkMax: 30, beat: 0.62, surface: 0.6, stay: 2.4, climb: 1.1 },
    debut: { firstAt: 0.45 * H, cooldown: [42, 68], grab: [1.5, 4], lurkMax: 30, beat: 0.62, surface: 0.6, stay: 2.4, climb: 1.1 },
    fierce: { firstAt: 0.2 * H, cooldown: [30, 50], grab: [1, 3], lurkMax: 40, beat: 0.62, surface: 0.6, stay: 2.4, climb: 1 },
  },
  fangy: {
    calm: { firstAt: 1.5 * H, cooldown: [136, 200], approach: 5.5, rise: 1.4, listen: 6, noises: 3, deaf: 0.8, reelNoise: 1.3, leave: 2 },
    debut: { firstAt: 0.4 * H, cooldown: [85, 125], approach: 5, rise: 1.4, listen: 7, noises: 3, deaf: 0.8, reelNoise: 1.2, leave: 2 },
    fierce: { firstAt: 0.2 * H, cooldown: [58, 88], approach: 4, rise: 1.2, listen: 8.5, noises: 3, deaf: 0.8, reelNoise: 1.0, leave: 2 },
  },
  // il Foxy non torna a visite: sta nel suo posto tutta la notte. Il livello cambia quando compare e quanto aspetta
  // prima di sporgersi e di lasciare il posto (la sua pazienza), la corsa fino alla barca e quanto spesso cambia posto.
  // Il punto «come la sua notte» è la notte 2 (approvato il 13 ottobre)
  foxy: {
    calm: { firstAt: 1.8 * H, lean: 60, leave: 110, run: 4, swap: 0.1 },
    debut: { firstAt: 0.9 * H, lean: 46, leave: 85, run: 3.5, swap: 0.15 },
    fierce: { firstAt: 0.3 * H, lean: 30, leave: 54, run: 2.6, swap: 0.45 },
  },
};

function mix(a: Num, b: Num, t: number): Num {
  const out: Num = {};
  const r = (x: number) => Math.round(x * 100) / 100;
  for (const k of Object.keys(a)) {
    const x = a[k]!;
    const y = b[k]!;
    out[k] = Array.isArray(x) && Array.isArray(y) ? [r(x[0] + (y[0] - x[0]) * t), r(x[1] + (y[1] - x[1]) * t)] : r((x as number) + ((y as number) - (x as number)) * t);
  }
  return out;
}

/** i numeri di un mostro al livello dato (da 1 a EXTRA_MAX) */
function monsterAt(who: Anchored, level: number): Num {
  const a = EXTRA_ANCHORS[who];
  if (level <= 5) return mix(a.calm, a.debut, (level - 1) / 4);
  // oltre il 5 la curva sale piano all'inizio e più in fretta verso il 20, se no il 10 è già quasi impossibile
  const up = (l: number) => mix(a.debut, a.fierce, ((l - 5) / 15) ** 1.5);
  if (level <= 10) return up(level);
  // dal 10 al 20 un tratto a sé (decisione dell'utente dell'11 ottobre: tutti a 20 dev'essere difficilissima ma
  // possibile). Le pause fra una visita e l'altra restano quelle del 10, mentre pazienza, avvisi, velocità e primo
  // arrivo vanno fino al punto feroce: dal 10 al 20 i mostri non tornano più spesso, ma ogni visita è più cattiva.
  // Con le pause del punto feroce anche al 20 l'esperto non vinceva quasi mai (docs/NOTTI_E_MOSTRI.md)
  const at10 = up(10);
  // (il Foxy non ha pause: per lui dal 10 al 20 si va dritti al punto feroce)
  return mix(at10, at10.cooldown ? { ...a.fierce, cooldown: at10.cooldown } : a.fierce, (level - 10) / 10);
}

/**
 * La Madre nella notte extra (confermato dall'utente l'11 ottobre): il suo livello dice quante volte passa sotto la
 * barca, quanto dura ogni passata e quanto avvisa prima. La meccanica è quella della notte 6 (MotherConfig). Numeri
 * approvati il 13 ottobre:
 * - 0: non viene;
 * - 1: una passata sola, a metà notte, di 8 s, con più avviso (12 s) e un tremito in più perdonato;
 * - 10: esattamente come nella notte 6 (tre passate, verso le 2, le 4 e le 5:30, di 10, 15 e 20 s);
 * - 20: cinque passate, da 12 a 20 s, con meno avviso (8 s) e meno tremito perdonato (più lunghe di così, con tutti a
 *   20 non resta il tempo per la quota).
 * Le passate sono un numero intero (1 + livello/5, arrotondato); le durate e gli avvisi si sfumano.
 */
const MOTHER_SLOTS: Record<number, number[]> = {
  // quando comincia ad avvicinarsi, per numero di passate (ore della notte; come nella notte 6, 10 s prima)
  1: [3],
  2: [2.5, 5],
  3: [2, 4, 5.5],
  4: [1.5, 3, 4.25, 5.5],
  5: [1, 2, 3, 4.25, 5.5],
};

export function extraMother(level: number): MotherConfig | undefined {
  const l = clampLevel(level);
  if (l === 0) return undefined;
  // da 1 a 10 e da 10 a 20 in linea retta
  const at = (v1: number, v10: number, v20: number) => Math.round((l <= 10 ? v1 + ((v10 - v1) * (l - 1)) / 9 : v10 + ((v20 - v10) * (l - 10)) / 10) * 10) / 10;
  const n = 1 + Math.round((l / EXTRA_MAX) * 4);
  const first = at(8, 10, 12);
  const last = at(8, 20, 20);
  const pass = Array.from({ length: n }, (_, i) => (n === 1 ? first : Math.round((first + ((last - first) * i) / (n - 1)) * 10) / 10));
  return {
    passes: MOTHER_SLOTS[n]!.map((h) => h * H - 10),
    approach: at(12, 10, 8),
    pass,
    leave: 6,
    still: at(5, 4, 3),
    circle: 70,
  };
}

/**
 * Il finale speciale della notte extra si vede solo vincendola con tutti, Madre compresa, almeno a 10 (confermato
 * dall'utente l'11 ottobre: è il finale B «Il ricordo», la cinematica FINALE_B col disegno a pastelli); con impostazioni
 * più facili all'alba c'è l'alba normale.
 */
export const EXTRA_ENDING_MIN = 10;

export function extraEndingEarned(levels: ExtraLevels): boolean {
  return EXTRA_IDS.every((who) => clampLevel(levels[who] ?? 0) >= EXTRA_ENDING_MIN);
}

/** Gulpy, Molly e Hatch ci sono in ogni notte (il gioco li disegna sempre): al livello 0 il
 *  primo arrivo è ben oltre le sei, cioè non arrivano mai (come nei test, quiet()). */
const NEVER = 1e9;

/** quanto è più veloce il recupero nella notte extra quando c'è il Foxy (come reelMul delle notti 2-5) */
const FOXY_REEL = 1.1;

/**
 * La config della notte extra dai livelli dei sette mostri. Quota 10 (approvata il 13 ottobre): la notte quinta ne chiede 11
 * coi suoi tre mostri radi; qui possono venire tutti insieme. I pesci abboccano in fretta come nella quinta notte,
 * la batteria è quella dalla notte 2 in poi, la regia tiene le esclusioni della quinta notte (chi chiede il
 * contrario dell'altro non viene insieme a lui).
 */
export function extraNight(levels: ExtraLevels): NightConfig {
  const lv = (who: Anchored) => clampLevel(levels[who] ?? 0);
  const on = (who: Anchored) => lv(who) > 0;
  const at = <T>(who: Anchored) => monsterAt(who, lv(who)) as unknown as T;
  const off = <T extends { firstAt: number }>(who: NightMonster): T => ({ ...(monsterAt(who, 1) as unknown as T), firstAt: NEVER });
  return {
    night: EXTRA_NIGHT,
    quota: 10,
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
    gulpy: on('gulpy') ? at<GulpyConfig>('gulpy') : off<GulpyConfig>('gulpy'),
    molly: on('molly') ? at<MollyConfig>('molly') : off<MollyConfig>('molly'),
    hatch: on('hatch') ? at<HatchConfig>('hatch') : off<HatchConfig>('hatch'),
    robin: on('robin') ? at<RobinConfig>('robin') : undefined,
    archie: on('archie') ? at<ArchieConfig>('archie') : undefined,
    lampy: on('lampy') ? at<LampyConfig>('lampy') : undefined,
    fangy: on('fangy') ? at<FangyConfig>('fangy') : undefined,
    foxy: on('foxy') ? at<FoxyConfig>('foxy') : undefined,
    // il tempo col binocolo si ripaga tirando su i pesci più in fretta, come nelle notti 2-5 (decisione dell'utente)
    ...(on('foxy') ? { reelMul: FOXY_REEL } : {}),
    mother: extraMother(levels.mother ?? 0),
    battery: { drain: [0, 1 / 700, 1 / 320], sonar: 1 / 1100, low: 0.15, lullaby: 64 },
    hideTime: 0.7,
    unhideTime: 0.6,
  };
}

/** La notte in cui arriva ogni mostro (uno nuovo per notte dalla seconda; deciso il 10 ottobre). */
export const ARRIVAL: Record<NightMonster, number> = { gulpy: 1, molly: 1, hatch: 1, robin: 2, archie: 3, lampy: 4, fangy: 5 };

/**
 * Le immersioni all'alba (docs/IMMERSIONI.md): il pesce lasciato accanto a un mostro addormentato lo tiene a dormire
 * tutta la notte dopo. Si può sfamare chi gira nella notte n, tranne il mostro nuovo di quella notte: la sua tana è
 * vuota, è già in giro (deciso l'11 ottobre). La prima notte non c'è un'alba prima, quindi niente.
 */
export function canFeed(n: number, who: MonsterId): boolean {
  // il Foxy non ha una tana
  if (who === 'foxy') return false;
  return n >= 2 && ARRIVAL[who] < n;
}

export function angleDiff(a: number, b: number): number {
  let d = (a - b) % 360;
  if (d > 180) d -= 360;
  if (d < -180) d += 360;
  return d;
}
