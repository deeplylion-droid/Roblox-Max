/**
 * Le regole di un'immersione all'alba (docs/IMMERSIONI.md), senza grafica né audio: dove sei, quali passaggi si
 * vedono, quali tane sono vuote, l'aria, il pesce. La presentazione (src/app/dive.ts) chiama i metodi e legge lo stato;
 * i test la provano da sola.
 *
 * I posti, i passaggi e le tane stanno in un file di dati (public/assets/img/immersioni.json, tipo DiveData): quando
 * arrivano i panorami veri basta aggiungerli lì.
 */
import type { PassInfo, Vec3 } from '../engine/assets.ts';
import { ARRIVAL, canFeed, type MonsterId } from '../game/config.ts';

/** I passi di un panorama a 360° di un posto (come gli strati del manifest dei render). */
export interface DivePano {
  ambient?: PassInfo;
  lantern?: PassInfo;
  lamp?: PassInfo;
  /** R = sqrt(distanza / 2500 m) per la nebbia dell'acqua, G = quanto trema l'immagine */
  data?: string;
}

/** Un punto cliccabile del panorama: un passaggio verso un altro posto, la risalita o una cosa da guardare. Gradi. */
export interface DiveLink {
  to?: string;
  ascend?: boolean;
  /** una cosa che si guarda soltanto (il fondo della Madre): una didascalia (STRINGS.dive.notes) */
  note?: string;
  yaw: number;
  pitch: number;
  /** raggio cliccabile (gradi) */
  r: number;
  /** testo che compare passandoci sopra (STRINGS.dive.links); senza, niente */
  label?: string;
  /** un tasto sullo schermo invece di un punto del panorama (nelle inquadrature fisse: «torna alla grotta») */
  button?: boolean;
}

/** Uno strato ritagliato sopra il panorama (la posa del mostro che dorme, la toppa del respiro). */
export interface DiveSprite {
  passes: { ambient?: PassInfo; lantern?: PassInfo };
  /** riquadro in pixel del panorama del posto */
  rect: [number, number, number, number];
  /** toppa del respiro: periodo in secondi con cui si dissolve sopra la posa */
  breath?: number;
}

export interface DivePlace {
  pano: DivePano;
  /** larghezza e altezza del panorama (pixel) */
  size: [number, number];
  /** latitudini del bordo basso e alto del panorama (−90, 90 per la sfera intera) */
  latMin: number;
  latMax: number;
  /** longitudini del bordo sinistro e destro (gradi; senza, −180 e 180: il panorama intero). Un'inquadratura fissa
   *  (frame) è un panorama parziale, largo il campo visivo più quanto si gira */
  lonMin?: number;
  lonMax?: number;
  /** inquadratura fissa, come una telecamera di FNAF (le camerette delle tane, deciso l'11 ottobre): lo sguardo resta
   *  entro yawRange gradi a destra e a sinistra di yaw, e entro pitchRange in su e in giù di pitch. Senza, ci si
   *  guarda attorno a 360° (la grotta grande) */
  frame?: { yaw: number; pitch: number; yawRange: number; pitchRange: number };
  /** gradi di cui è ruotato il panorama */
  yaw?: number;
  /** tinta (un panorama riusato per più posti, come i segnaposto) */
  tint?: Vec3;
  /** dove guardi quando arrivi */
  look?: { yaw: number; pitch: number };
  /** quanta luce scende dall'alto (raggi) */
  rays?: number;
  /** è la tana di questo mostro */
  den?: MonsterId;
  /** panorama della tana vuota, se diverso (se la posa è dipinta nel panorama invece che in sleeper.layers) */
  panoEmpty?: DivePano;
  /** l'acqua torbida è già cotta nei passi del render (le grotte vere): la nebbia del motore scende a
   *  WaterLook.fogDensityCooked, se no si raddoppia */
  acquaCotta?: boolean;
  /** suoni in loop del posto (la Madre che respira dal fondo della grotta grande): dove stanno, in gradi e metri */
  sounds?: { id: string; yaw: number; pitch: number; dist?: number; gain?: number }[];
  /** il mostro che dorme: dove si clicca per lasciargli il pesce, i suoi strati, da dove salgono le bolle */
  sleeper?: { yaw: number; pitch: number; r: number; layers?: DiveSprite[]; bubbles?: { yaw: number; pitch: number } };
  links: DiveLink[];
}

/** Regole dell'aria (decise l'11 ottobre sera): l'aria basta per maxDens tane; il tempo dentro le tane è libero e
 *  nuotare non costa. Non c'è un indicatore: quando lasci l'ultima tana l'aria è finita e si risale da soli. */
export interface AirRules {
  maxDens: number;
  /** la tana vuota del mostro nuovo non costa aria (non conta fra le due): deciso l'11 ottobre sera */
  emptyDenFree?: boolean;
}

/** L'aspetto dell'acqua (WaterFx e la nebbia del passo dati). */
export interface WaterLook {
  fog: Vec3;
  fogDensity: number;
  /** la nebbia nei posti con l'acqua già cotta nel render (DivePlace.acquaCotta) */
  fogDensityCooked?: number;
  rayColor: Vec3;
  snowColor: Vec3;
  glowColor: Vec3;
  /** mezzo angolo del cono della torcia (gradi) */
  torchAngle: number;
  /** esposizione in più (stop) rispetto alla luminosità scelta nelle opzioni */
  exposure: number;
}

export interface DiveData {
  start: string;
  air: AirRules;
  water: WaterLook;
  places: Record<string, DivePlace>;
}

/** Com'è una tana per la notte che viene: chiusa (il mostro non è ancora arrivato), vuota (è il nuovo della notte,
 *  già in giro), con il mostro che dorme. */
export type DenState = 'locked' | 'empty' | 'asleep';

export class DiveRun {
  place: string;
  /** le tane in cui sei entrato in questa immersione, in ordine */
  readonly dens: MonsterId[] = [];
  /** le tane che sono costate aria (di solito tutte quelle viste; vedi AirRules.emptyDenFree) */
  private spent: MonsterId[] = [];
  /** il mostro a cui hai lasciato il pesce */
  fed: MonsterId | null = null;
  /** pesci portati giù (al massimo uno) */
  fish: number;

  constructor(
    readonly data: DiveData,
    /** la notte che viene dopo questa alba */
    readonly nextNight: number,
    /** pesci avanzati alle sei oltre la quota */
    spare: number,
  ) {
    this.place = data.start;
    this.fish = Math.min(1, Math.max(0, spare));
  }

  get current(): DivePlace {
    return this.data.places[this.place]!;
  }

  denState(who: MonsterId): DenState {
    if (ARRIVAL[who] > this.nextNight) return 'locked';
    return canFeed(this.nextNight, who) ? 'asleep' : 'empty';
  }

  /** I passaggi che si vedono nel posto: quelli verso le tane dei mostri non ancora arrivati no («notte dopo notte se
   *  ne aggiungono»), né quelli verso posti che non esistono nei dati. */
  visibleLinks(): DiveLink[] {
    return this.current.links.filter((l) => {
      if (!l.to) return true;
      const p = this.data.places[l.to];
      if (!p) return false;
      return !p.den || this.denState(p.den) !== 'locked';
    });
  }

  /** Si può entrare? Una tana nuova costa aria: dopo maxDens tane non ce n'è più per un'altra (nel gioco non succede:
   *  uscendo dall'ultima tana si risale, outOfAirOnLeave; resta per sicurezza, se i dati collegassero due tane). */
  canEnter(to: string): 'ok' | 'tooFar' | 'missing' {
    const p = this.data.places[to];
    if (!p) return 'missing';
    if (p.den && this.costsAir(p.den) && this.spent.length >= this.data.air.maxDens) return 'tooFar';
    return 'ok';
  }

  /** Entrare in questa tana costerebbe aria? (non se l'hai già vista, né la tana vuota con emptyDenFree) */
  private costsAir(who: MonsterId): boolean {
    if (this.spent.includes(who)) return false;
    return !(this.data.air.emptyDenFree && this.denState(who) === 'empty');
  }

  enter(to: string): boolean {
    if (this.canEnter(to) !== 'ok') return false;
    this.place = to;
    const p = this.current;
    if (p.den && !this.dens.includes(p.den)) this.dens.push(p.den);
    if (p.den && this.costsAir(p.den)) this.spent.push(p.den);
    return true;
  }

  /** Sei nell'ultima tana che costa aria (la seconda)? Lì l'aria sta finendo: l'erogatore dà un respiro affannoso,
   *  l'unico segnale (niente sullo schermo; deciso l'11 ottobre sera). */
  airRunningOut(): boolean {
    return !!this.current.den && this.spent.length >= this.data.air.maxDens;
  }

  /** Uscendo dalla tana in cui sei, l'aria finisce? Sì dall'ultima tana che costa aria (la seconda): invece di tornare
   *  nella grotta si risale. */
  outOfAirOnLeave(): boolean {
    return this.airRunningOut();
  }

  /** Lascia il pesce accanto al mostro della tana in cui sei. */
  feed(): 'ok' | 'noFish' | 'already' | 'notHere' {
    const who = this.current.den;
    if (!who || this.denState(who) !== 'asleep') return 'notHere';
    if (this.fed) return 'already';
    if (this.fish <= 0) return 'noFish';
    this.fish--;
    this.fed = who;
    return 'ok';
  }
}
