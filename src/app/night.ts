/**
 * Una notte giocata: collega la simulazione (src/game) alla scena, all'audio e all'interfaccia.
 * Le creature sono strati del panorama (le pose renderizzate) che emergono dall'acqua o salgono da dietro il
 * bordo, e se ne vanno scendendo, secondo lo stato della simulazione; la vista da sotto il telone e i jumpscare sono immagini a
 * tutto schermo disegnate dentro la scena (prendono bloom, grana e vignetta come il resto).
 */
import type { LayerInfo, Vec3 } from '../engine/assets.ts';
import { dirPos, type AudioEngine, type Voice } from '../engine/audio.ts';
import type { BinoPlace, LayerDraw, LightGlow, Overlay, Stroke, TubeDraw } from '../engine/renderer.ts';
import { CHILD, RADIO_VOICE, speak, type Utterance } from '../engine/voice.ts';
import { FISHING, HOUR_SECONDS, NIGHTS, VIEW, YAW, angleDiff, type LampLevel, type MonsterId, type NightConfig } from '../game/config.ts';
import type { GameEvent } from '../game/events.ts';
import { LAMPY_FIRST_BEAT } from '../game/monsters.ts';
import { NightSim, type MotherCause } from '../game/sim.ts';
import { FISH_BY_ID } from '../game/catalog.ts';
import { LORE_TEXT, RADIO, RADIO_FINALE, STRINGS, type Lang, type RadioLine } from '../i18n.ts';
import { Hud } from './hud.ts';
import { dualText, pad } from './pad.ts';
import type { Options } from './save.ts';
import type { Sfx } from './sfx.ts';
import { FINALE_A, FINALE_B, FINALE_NESSUNO, FINALE_TUOI, between, sample, stillFrame, textAt, type CinematicScript, type EndingStill } from './cinematic.ts';
import type { Ending } from './save.ts';

/** Le cinematiche dei tre finali della notte 6. */
const ENDING_CINE: Record<Ending | 'B', CinematicScript> = { A: FINALE_A, tuoi: FINALE_TUOI, nessuno: FINALE_NESSUNO, B: FINALE_B };
import { Sonar } from './sonar.ts';
import { VIVO_DI, Vivi } from './vivi.ts';
import { Paura } from './paura.ts';
import { Rod } from './rod.ts';
import { ROD_COLORS } from './rod_colori.ts';
import type { Stage } from './stage.ts';

export interface OverlayTex {
  tex: WebGLTexture;
  scale: number;
}

export interface NightAssets {
  /** vista da sotto il telone: passo base e passo retroilluminato (la luce del giocattolo che fruga) */
  tarp: { base: OverlayTex; glow: OverlayTex; aspect: number } | null;
  /** fotogrammi dei jumpscare renderizzati, se ci sono */
  jumpscares: Partial<Record<MonsterId | 'mother' | 'quota', { frames: OverlayTex[]; fps: number; aspect: number }>>;
  /** ritratti dei pesci del Catalogo già renderizzati: id → URL dell'immagine */
  fish: Record<string, string>;
  /** i luoghi dell'orizzonte per il binocolo, e dove sta la luce rossa della videocamera */
  /** i posti del binocolo; foxy: le viste dello stesso posto col Foxy fermo e più vicino (se ci sono i render) */
  binocular: { places: { key: string; yaw: number; pitch: number; hfov: number; place: BinoPlace; foxy?: BinoPlace[] }[]; rec: Vec3 | null };
  /** le ultime inquadrature dei finali segreti (il molo, l'edicola), se ci sono i render */
  endings: Partial<Record<EndingStill, OverlayTex & { aspect: number; exposure: number }>>;
}

export interface NightStats {
  caught: number;
  fed: number;
  lore: string[];
  /** secondi giocati */
  time: number;
  /** pesci nel secchio alla fine (quelli oltre la quota servono alle immersioni all'alba) */
  bucket: number;
}

export type NightEnd =
  | { kind: 'won'; stats: NightStats; /** il finale che si è visto (notte 6; alla notte extra il finale B) */ ending?: Ending | 'B' }
  | { kind: 'dead'; killer: MonsterId | 'mother'; cause?: MotherCause; stats: NightStats; /** c'è stato un jumpscare (anche quello della quota) */ js?: boolean };

export interface NightDeps {
  stage: Stage;
  audio: AudioEngine;
  sfx: Sfx;
  ui: HTMLElement;
  canvas: HTMLCanvasElement;
  lang: Lang;
  options: Options;
  foundLore: string[];
  assets: NightAssets;
  /** quale notte (1, 2…); senza, la prima */
  night?: number;
  /** la config da giocare, se non è quella di NIGHTS (la notte extra, costruita dai livelli) */
  config?: NightConfig;
  /** il mostro sfamato all'alba (immersione): stanotte dorme (NightOptions.fed) */
  fed?: MonsterId | null;
  /** il finale della sesta notte (save.chooseEnding: dipende dai pesci lasciati nelle tane); senza, il finale A. Alla
   *  notte extra 'B': il finale «Il ricordo» (senza, l'alba normale) */
  ending?: Ending | 'B';
  seed: number;
  onEnd: (r: NightEnd) => void;
  onPause: () => void;
  /** nuova cattura (per il Catalogo) */
  onCatch?: (species: string, kg: number) => void;
  /** specie già nel Catalogo (per segnare le nuove) */
  knownSpecies?: Set<string>;
}

const D2R = Math.PI / 180;

// dove stanno le cose, dall'occhio del pescatore (coordinate dei render, metri)
const RADIO_AT: Vec3 = [-0.3, -1.51, -0.655];
const LAMP_AT: Vec3 = [0, 4.17, 0.55];
/** forza della lucina del voltmetro rispetto al render (l'utente: «troppo luminosa in gioco, riducila del 40%») */
const GAUGE_LIGHT = 0.6;
/** dove si sente Robin: steso sul bordo di sinistra verso prua, le zampe nel secchio */
const ROBIN_AT: Vec3 = dirPos(YAW.robin, 1.3, -22);
/** Archie: la testa in cima al collo, davanti alla prua, piegata sulla lampara (notte 3) */
const ARCHIE_AT: Vec3 = dirPos(YAW.archie, 5, 13);
/** notte 4: Lampy sulla lenza (la posa lampy_lenza; tools/render/cache/lampy_posa.json, «lenza_m», dall'occhio, spazio
 *  della barca): la bocca dove le entra la lenza, la ventosa della coda che la tiene, dove il filo entra in mare */
const LAMPY_MOUTH: Vec3 = [4.092, 4.388, -0.077];
const LAMPY_TAIL: Vec3 = [5.29, 3.751, -1.02];
const LAMPY_WATER: Vec3 = [5.696, 3.926, -1.273];
/** dove si sente Lampy: sotto di lei, dove la lenza entra in acqua */
const LAMPY_AT: Vec3 = [4.7, 4.1, -1.15];
const HATCH_AT: Vec3 = [0.35, -7.4, -0.6];
/** notte 5: Fangy nell'acqua a destra, dietro il pescatore: la testa (tools/render/cache/fangy_posa.json, «testa_m»,
 *  dall'occhio, spazio della barca) */
const FANGY_AT: Vec3 = [1.808, -0.7305, -0.298];
/** le lucine che lo annunciano: una fila sott'acqua che arriva dal largo girando verso di lui (quante, da quanti metri
 *  dall'occhio, da quanti gradi più a poppa, quanto sotto il pelo dell'acqua) */
const FANGY_ROW = 9;
const FANGY_FAR = 13;
const FANGY_SWING = 34;
const FANGY_DEEP = 0.6;
/** il respiro delle sue lucine (secondi per giro): calmo, poi più in fretta a ogni rumore che ha sentito */
const FANGY_BREATH = [3.2, 2.1, 1.35, 0.9];
/** il colore delle lucine (azzurre, come i pesci degli abissi) */
const FANGY_LIGHT: Vec3 = [0.3, 0.78, 1.0];
/** il pelo dell'acqua sotto l'occhio */
const WATER_Z = -1.25;
/** dove cade il galleggiante: davanti alla canna, verso il largo (radianti di yaw dall'occhio) */
const FLOAT_YAW = 40 * D2R;
/** distanza del galleggiante dall'occhio (metri): in attesa, e a fine recupero (lì è appena dietro il bordo) */
const FLOAT_FAR = 12;
const FLOAT_NEAR = 4;
/** quanto sale il galleggiante sopra la linea dritta, a metà volo (metri) */
const CAST_ARC = 1.8;
/** il galleggiante ha la luce chimica, come nella pesca di notte */
const FLOAT_LIGHT: Vec3 = [1.5, 0.42, 0.12];
/** il lancio (FISHING.castTime): la canna si carica fino a CAST_LOAD, poi la frustata (sul picco del fruscio del
 *  suono 'cast') fino a CAST_WHIP, poi il galleggiante vola fino al tonfo */
const CAST_LOAD = 0.12;
const CAST_WHIP = 0.27;
/** la canna nel lancio (gradi, + punta su e indietro): si alza caricandosi, scatta avanti, torna; la cima la segue
 *  con la sua inerzia (rod.ts), ed è lei a fare la frustata */
function castTilt(ct: number): number {
  if (ct < 0.13) return 10 * smooth01(ct / 0.13);
  if (ct < 0.25) return 10 - 16 * smooth01((ct - 0.13) / 0.12);
  if (ct < 0.6) return -6 * (1 - smooth01((ct - 0.25) / 0.35));
  return 0;
}
/** il galleggiante appeso alla punta (metri di filo) */
const HANG = 0.42;
/** la canna nel lancio, fotogramma per fotogramma ([fino a quale istante, strato]; pose renderizzate a parte,
 *  jobs.py props con PROPS=lancio): si alza e si carica, la frustata in avanti (il galleggiante parte con
 *  rod_f2) e la cima che torna */
const CAST_ROD: [number, string][] = [
  [0.04, 'rod0'], [0.08, 'rod_c1'], [0.14, 'rod_c2'], [0.18, 'rod_m'], [0.21, 'rod_f1'], [0.28, 'rod_f2'], [0.32, 'rod_f1'],
];
const BELL_YAW = -40;

/** Pose renderizzate nella scena (vedi tools/render/scena_creature.py). */
const POSE = {
  /** notte 6: la Madre sale accanto alla barca a sinistra, fuori la fronte e l'occhio (il finale A) */
  madre: 'madre_sale',
  gulpySale: 'gulpy_sale',
  gulpyPretende: 'gulpy_pretende',
  mollyRight: 'molly_destra',
  mollyLeft: 'molly_sinistra',
  hatchConta: 'hatch_conta',
  /** notte 2: Robin steso sul bordo col braccio nel secchio, e la sua testa con gli occhi strizzati (nella luce) */
  robin: 'robin_secchio',
  robinSquint: 'robin_strizza',
  robinBlink: 'robin_chiusi',
  /** le animazioni sulla barca (toppe della sola testa, tools/render/pose_animate.py) */
  gulpyJawOpen: 'gulpy_mascella_aperta',
  gulpyJawShut: 'gulpy_mascella_chiusa',
  hatchMouthHalf: 'hatch_bocca_mezza',
  hatchMouthShut: 'hatch_bocca_chiusa',
  /** notte 3: Archie fuori dall'acqua davanti alla prua, e le toppe della trombetta srotolata a metà e tutta */
  archie: 'archie_soffia',
  archieHornHalf: 'archie_trombetta_mezza',
  archieHornFull: 'archie_trombetta_tutta',
  /** la testa con la gola gonfia: il risucchio prima di soffiare */
  archieBreath: 'archie_fiato',
  /** notte 4: Lampy aggrappata alla lenza, e le toppe della ventosa chiusa e spalancata (coi denti girati) */
  lampy: 'lampy_lenza',
  lampyShut: 'lampy_bocca_chiusa',
  lampyOpen: 'lampy_bocca_aperta',
  /** notte 5: Fangy in ascolto, e le toppe della testa girata di scatto verso prua e verso poppa (la creatura intera:
   *  girando, la testa scopre e copre il corpo) */
  fangy: 'fangy_ascolta',
  fangyBow: 'fangy_testa_prua',
  fangyStern: 'fangy_testa_poppa',
} as const;

/** le toppe degli occhi di Molly sui due lati: il primo occhio (quello che ti fissa) e il secondo */
const MOLLY_EYES = {
  right: ['molly_destra_primo', 'molly_destra_secondo'],
  left: ['molly_sinistra_primo', 'molly_sinistra_secondo'],
} as const;

/** Una creatura sulla barca (vedi Night.aboard). */
interface Aboard {
  key: string;
  /** quanto è su: 1 in posa, 0 sparita dietro il bordo */
  p: number;
  /** sotto questo p la parte davanti alla barca (le mani sul bordo) è svanita */
  hands: number;
  /** quanto va in fuori mentre scende (frazione della discesa, in pixel di yaw del panorama) */
  out: number;
  /** la parte davanti alla barca (le mani sul bordo) resta ferma mentre svanisce: se scendesse col resto
   *  passerebbe attraverso lo scafo */
  handsStay?: boolean;
  /** spostamento in più (pixel del panorama) */
  recoil?: [number, number];
  light?: [number, number, number];
  opacity?: number;
  /** le toppe delle mascelle che entrano sopra questo strato (dove sono vuote, questo sfuma) */
  masks?: { key: string; k: number }[];
}

function approach(cur: number, target: number, rate: number, dt: number): number {
  return cur + (target - cur) * (1 - Math.exp(-rate * dt));
}

/** Verso il bersaglio a velocità costante: una corsa intera in `up` secondi a salire, in `down` a scendere. */
function toward(cur: number, target: number, up: number, down: number, dt: number): number {
  return target > cur ? Math.min(target, cur + dt / up) : Math.max(target, cur - dt / down);
}

/** Rallenta arrivando a 1 e accelera ripartendo da 1: una creatura che sale e si ferma, o che si lascia cadere. */
function ease(x: number): number {
  const t = Math.max(0, Math.min(1, x));
  return 1 - (1 - t) * (1 - t);
}

function smooth01(x: number): number {
  const t = Math.max(0, Math.min(1, x));
  return t * t * (3 - 2 * t);
}

function hash1(n: number): number {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
}

/** Rumore liscio in [-1, 1]. */
function noise1(x: number, seed: number): number {
  const i = Math.floor(x);
  const f = x - i;
  const u = f * f * (3 - 2 * f);
  const a = hash1(i + seed * 101.3) * 2 - 1;
  const b = hash1(i + 1 + seed * 101.3) * 2 - 1;
  return a + (b - a) * u;
}

/** Zoom in più sui fotogrammi del jumpscare di qualcuno, senza rifare il render: Soggy ti arriva proprio in faccia, alla
 *  FNAF (richiesta dell'utente del 12 ottobre: +20%). */
const JS_ZOOM: Partial<Record<MonsterId | 'mother' | 'quota', number>> = { foxy: 1.2 };

/** Camera a mano del jumpscare, in post: sobbalzo all'impatto, tremito rapido, rollio, un colpo di zoom a
 *  ogni fotogramma nuovo e una lenta spinta in avanti. Lo zoom copre sempre lo schermo, anche con lo
 *  spostamento e il rollio più grandi possibili in quell'istante. calm < 1 attenua tutto. */
function jumpscareCamera(t: number, fps: number, frames: number, aspect: number, calm: number): { offset: [number, number]; roll: number; zoom: number } {
  const amp = calm * (0.040 * Math.exp(-t * 2.2) + 0.012);
  const joltEnv = calm * Math.exp(-t * 6);
  const jolt = joltEnv * Math.cos(t * 38);
  const ox = amp * (0.7 * noise1(t * 26, 1) + 0.3 * noise1(t * 53, 2)) + 0.025 * jolt;
  const oy = amp * 0.8 * (0.7 * noise1(t * 24, 3) + 0.3 * noise1(t * 49, 4)) - 0.035 * jolt;
  const rollAmp = calm * (0.035 * Math.exp(-t * 2.5) + 0.010);
  const roll = rollAmp * noise1(t * 17, 5) + 0.015 * jolt;
  const mx = amp + 0.025 * joltEnv;
  const my = amp * 0.8 + 0.035 * joltEnv;
  const r = rollAmp + 0.015 * joltEnv;
  const cover = Math.max(
    (aspect * Math.cos(r) + Math.sin(r)) / (aspect * (1 - 2 * mx)),
    (aspect * Math.sin(r) + Math.cos(r)) / (1 - 2 * my),
  );
  const fi = Math.floor(t * fps);
  const punch = fi < frames ? calm * 0.025 * Math.exp(-(t - fi / fps) * 16) : 0;
  return { offset: [ox, oy], roll, zoom: cover * 1.005 + punch + 0.08 * smooth01(t / 1.9) };
}

function norm(v: Vec3): Vec3 {
  const l = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / l, v[1] / l, v[2] / l];
}

function angleBetween(a: Vec3, b: Vec3): number {
  const na = norm(a), nb = norm(b);
  return Math.acos(Math.max(-1, Math.min(1, na[0] * nb[0] + na[1] * nb[1] + na[2] * nb[2]))) / D2R;
}

type Target = 'rod' | 'bucket' | 'tarp' | 'lamp' | 'sonar' | null;

export class Night {
  readonly sim: NightSim;
  readonly hud: Hud;
  private S: (typeof STRINGS)['it'];
  private sonar = new Sonar(384);
  private sonarEl: HTMLDivElement;
  private paused = false;
  private finished = false;
  private endTimer = 0;
  private endResult: NightEnd | null = null;
  // input
  private held = new Set<string>();
  private mouse = { x: 0.5, y: 0.5, inside: false, down: false };
  /** i bordi dello schermo girano lo sguardo; dopo uno scatto da tastiera (W A S D) non più, finché il mouse non si
   *  muove: se era rimasto fermo nella fascia del bordo, dopo lo scatto la vista continuava a girare da sola */
  private edgeArmed = true;
  private sonarOpen = false;
  /** binocolo: alzato (desiderato), quanto è alzato (0..1), campo dello zoom, inclinazione dello sguardo */
  private binoUp = false;
  private bino = 0;
  private binoFov = 9;
  private binoPitch = 2.5;
  private turnArmed = true;
  private reelByMouse = false;
  /** il recupero tenuto col grilletto destro del controller */
  private reelByPad = false;
  private hoverTarget: Target = null;
  // stato visivo (morbido)
  private v = { gSale: 0, gRise: 0, gPret: 0, mR: 0, mL: 0, hRise: 0, robin: 0, robinFear: 0, robinBlink: 0,
    gJaw: 0, gJawPhase: 0, gJawAmp: 0, mBlink1: 0, mBlink2: 0, hMouth: 0, hMouthT: 99, aRise: 0, aHornT: 0, aHornHalf: 0, aHornFull: 0, aFiato: 0, lRise: 0, lMouth: 0, lMouthT: 0, lClimb: 0,
    fRise: 0, fBow: 0, fStern: 0, fHead: 0, fHeadT: 1, fFlash: 0, fBreath: 0, fApp: 0, fRow: 0, mCalm: 0, mLift: 0, mdRise: 0, tarp: 0, toy: 0, toyX: -1, dawn: 0, rock: 0, dark: 0 };
  private gulpyDive = 0;
  /** quando è cominciata l'abboccata in corso (per il suggerimento nelle notti di Lampy) */
  private biteAt = -1;
  private js: { killer: MonsterId | 'mother' | 'quota'; t: number; yaw: number; scream: Voice | null } | null = null;
  private lineSway = 0;
  /** secondi dal lancio e dal tonfo del galleggiante (−1: niente da animare) */
  private castT = -1;
  private plopT = -1;
  private splashSeed = 0;
  /** cerchi sull'acqua attorno al galleggiante: età (s), centro, grandezza */
  private rings: { t: number; at: Vec3; size: number }[] = [];
  /** il galleggiante dell'ultimo fotogramma, e cosa gli succede quando la lenza torna su: recuperata a vuoto,
   *  sollevata col pesce, o persa col filo spezzato */
  private lastFloat: Vec3 | null = null;
  private retrieve: { t: number; from: Vec3; kind: 'reel' | 'lift' | 'lost' } | null = null;
  /** la canna disegnata dal motore (se c'è lo strato rod_base), il galleggiante che le pende dalla punta come un
   *  pendolo, da dove è partito nel lancio, e la ferrata (secondi da quando hai ferrato) */
  private rod = new Rod();
  private bob: { p: Vec3; q: Vec3 } | null = null;
  private castFrom: Vec3 | null = null;
  private strikeT = -1;
  /** i battiti di ciglia delle creature: attesa fino al prossimo, e quanto manca alla fine di quello in corso */
  private blinks: Record<string, { wait: number; t: number }> = {};
  // audio
  private loops: Record<string, Voice | null> = {};
  private radio: { t: number; next: number; utt: Utterance | null; hiss: Voice | null; lines?: RadioLine[] } | null = null;
  private bells: number[] = [];
  private creakTimer = 9;
  /** dopo il taglio di un finale su un altro posto: niente più scricchiolii della barca */
  private quiet = false;
  private lastHourShown = -1;
  private listeners: [EventTarget, string, EventListener][] = [];
  /** dove si sente Gulpy: lontano mentre sale, aggrappato alla prua quando pretende (dai render) */
  private gulpyFar: Vec3;
  private bowAt: Vec3;
  /** quale notte si gioca */
  readonly nightNo: number;
  /** ago del voltmetro (volt, velocità): una molla smorzata, come un ago vero */
  private needle = { v: 14.6, vel: 0 };
  private flickerTimer = 0;
  /** la lucina dietro il quadrante del voltmetro (0..1): trema con la lampara, muore con la batteria */
  private gaugeGlow = 1;
  /** la ninna nanna della Madre a batteria morta */
  private lullabyV: Voice | null = null;
  /** il risucchio di Archie in corso: si ferma quando smette di prendere fiato */
  private archieBreath: { stop(fade?: number): void } | null = null;
  /** la Madre (notte 6): la sua ninna nanna e la passata in corso, e da quanto è cominciato lo stato di prima (per i
   *  momenti dell'avvicinamento: il mare che si ferma, la lampara che trema, la ninna nanna) */
  private motherSong: Voice | null = null;
  private motherPassV: Voice | null = null;
  /** il suono dell'avvicinamento (12 s): si tronca se muori prima che finisca */
  private motherApproachV: Voice | null = null;
  private motherPrevT = 0;
  /** secondi saltati all'inizio del suono dell'avviso (12 s), perché finisca quando comincia la passata: nella notte 6
   *  l'avviso dura 10 s, nella 7 da 12 a 8 secondo il livello. Il mare che si calma, la luce che trema e la ninna nanna
   *  seguono il suono, quindi si spostano con lui (revisione della notte 6, punto 3) */
  private motherSkip = 0;
  /** la cinematica in corso (i finali): la sequenza, a che punto è, le voci da fermare se la si salta */
  private cine: { s: CinematicScript; t: number; voices: Voice[] } | null = null;
  /** le creature vive: il respiro, lo scatto quando le guardi, le gocce (vivi.ts) */
  private vivi = new Vivi();
  /** dove si vede ogni creatura viva (yaw in gradi, dall'ultimo fotogramma disegnato) */
  private viviYaw: Record<string, number> = {};
  /** il cuore, il respiro e la tensione (paura.ts) */
  private paura: Paura;
  /** i falsi allarmi: il prossimo (tempo della notte), quanti ne restano, il sussulto del cuore; da quanto è calmo */
  private falso = { next: 0, left: 0, boost: 0 };
  private calm = 0;
  /** il secchio svuotato dalla cinematica (i pesci non si disegnano) e il buio della cinematica (0..1) */
  private cineEmptyBucket = false;
  private cineBlack = 0;
  /** l'esposizione in più della scena (l'alba, il buio), quella del fotogramma in corso */
  private sceneEv = 0;

  constructor(private d: NightDeps) {
    this.S = STRINGS[d.lang];
    this.nightNo = d.config ? d.config.night : NIGHTS[d.night ?? 1] ? (d.night ?? 1) : 1;
    this.sim = new NightSim(d.config ?? NIGHTS[this.nightNo]!, d.seed, d.foundLore, { fed: d.fed ?? null });
    this.hud = new Hud(d.ui, d.lang);
    this.paura = new Paura(d.audio);
    // i falsi allarmi (più paura): dalla notte 2, uno o due per notte, il primo fra l'una e le tre circa
    if (this.nightNo >= 2) this.falso = { next: HOUR_SECONDS * (1 + 1.2 * Math.random()), left: Math.random() < 0.6 ? 2 : 1, boost: 0 };
    this.sonarEl = document.createElement('div');
    this.sonarEl.className = 'sonar-full';
    this.sonarEl.appendChild(this.sonar.canvas);
    const close = document.createElement('div');
    close.className = 'sonar-close';
    dualText(close, this.S.sonarClose, this.S.pad.sonarClose);
    this.sonarEl.appendChild(close);
    d.ui.appendChild(this.sonarEl);
    this.sonar.onPing = () => d.audio.play('sonar_ping', { pos: [0.3, -1.42, -0.5], gain: 0.25 });
    // l'eco della Madre: un bip lungo e basso, più forte quando si avvicina (solo a sonar aperto o quando arriva: tutta
    // la notte, ogni giro del fascio, sarebbe troppo)
    this.sonar.onMother = (near) => {
      if (this.sonarOpen || this.sim.mother?.near) d.audio.play('sonar_warn', { gain: 0.35 + 0.45 * near, rate: 0.5 });
    };
    // Molly sta dove l'hanno messa i render: lo sguardo va verificato verso quelle direzioni
    const L = d.stage.man.layers;
    this.gulpyFar = dirPos(L[POSE.gulpySale]?.yaw ?? -15, 7.5, -4);
    this.bowAt = dirPos(L[POSE.gulpyPretende]?.yaw ?? -20, 2.8, 6);
    if (L[POSE.mollyRight]) YAW.mollyRight = L[POSE.mollyRight]!.yaw;
    if (L[POSE.mollyLeft]) YAW.mollyLeft = L[POSE.mollyLeft]!.yaw;
    const st = d.stage;
    st.view.yaw = st.view.targetYaw = 12;
    st.view.hfov = 90;
    st.view.swell = 1;
    st.lampTarget = st.lampShown = 1;
    this.bind();
    this.hud.setLamp(1);
    this.hud.setQuota(0, this.sim.cfg.quota);
    this.hud.setClock(this.nightNo, 0, 0);
  }

  // ───────────────────────── avvio e chiusura ─────────────────────────

  start(): void {
    const a = this.d.audio;
    this.loops.sea = a.play('amb_sea', { loop: true, fadeIn: 3, gain: 0.9 });
    this.loops.wind = a.play('amb_wind', { loop: true, fadeIn: 4, gain: 0.5 });
    this.loops.drone = a.play('amb_drone', { loop: true, fadeIn: 6, gain: 0.35 });
    this.loops.lamp = a.play('amb_lamp', { loop: true, fadeIn: 2, gain: 0.5, pos: [0, 4.17, 0.55] });
    // la radio gracchia dopo un paio di secondi
    this.radio = { t: -2.2, next: 0, utt: null, hiss: null };
  }

  destroy(): void {
    this.paura.stop(0.3);
    for (const [t, ev, fn] of this.listeners) t.removeEventListener(ev, fn);
    this.listeners = [];
    for (const v of Object.values(this.loops)) v?.stop(0.4);
    this.loops = {};
    this.radio?.utt?.stop();
    this.radio?.hiss?.stop(0.2);
    this.radio = null;
    this.lullabyV?.stop(0.4);
    this.lullabyV = null;
    this.archieBreath?.stop(0.2);
    this.archieBreath = null;
    this.motherSong?.stop(0.4);
    this.motherPassV?.stop(0.4);
    for (const v of this.cine?.voices ?? []) v.stop(0.3);
    this.cine = null;
    this.motherApproachV?.stop(0.4);
    this.motherSong = this.motherPassV = this.motherApproachV = null;
    this.d.stage.lampSick = 0;
    this.d.sfx.stopLoops();
    this.hud.destroy();
    this.sonarEl.remove();
    this.d.audio.setMuffled(0);
    const st = this.d.stage;
    st.view.rockBoost = 0;
    st.view.hfov = 90;
    st.view.shake = 0;
    st.view.steady = st.view.swayYaw = st.view.swayPitch = 0;
    st.view.liftRoll = st.view.liftPitch = 0;
    st.view.swell = 1;
  }

  setPaused(p: boolean): void {
    this.paused = p;
    this.held.clear();
    this.mouse.down = false;
    this.reelByPad = false;
    this.sim.setReelHeld(false);
  }

  // ───────────────────────── input ─────────────────────────

  /** Il recupero è tenuto: Spazio, il clic sulla canna o il grilletto destro. */
  private reelHeld(): boolean {
    return this.held.has(' ') || (this.mouse.down && this.reelByMouse) || this.reelByPad;
  }

  private on(t: EventTarget, ev: string, fn: (e: Event) => void): void {
    t.addEventListener(ev, fn as EventListener);
    this.listeners.push([t, ev, fn as EventListener]);
  }

  private bind(): void {
    const c = this.d.canvas;
    this.on(window, 'keydown', (e) => this.keyDown(e as KeyboardEvent));
    this.on(window, 'keyup', (e) => {
      const k = (e as KeyboardEvent).key.toLowerCase();
      this.held.delete(k);
      if (k === ' ') this.sim.setReelHeld(this.reelHeld());
    });
    this.on(window, 'blur', () => {
      this.held.clear();
      this.mouse.down = false;
      this.reelByPad = false;
      this.sim.setReelHeld(false);
    });
    this.on(c, 'mousemove', (e) => {
      const m = e as MouseEvent;
      const x = m.clientX / innerWidth, y = m.clientY / innerHeight;
      if (Math.hypot((x - this.mouse.x) * innerWidth, (y - this.mouse.y) * innerHeight) > 6) this.edgeArmed = true;
      this.mouse.x = x;
      this.mouse.y = y;
      this.mouse.inside = true;
    });
    this.on(c, 'mouseleave', () => {
      this.mouse.inside = false;
    });
    this.on(c, 'mousedown', (e) => this.mouseDown(e as MouseEvent));
    this.on(c, 'contextmenu', (e) => e.preventDefault());
    this.on(window, 'mouseup', (e) => {
      if ((e as MouseEvent).button === 2) {
        this.binoUp = false;
        return;
      }
      this.mouse.down = false;
      if (this.reelByMouse) {
        this.reelByMouse = false;
        this.sim.setReelHeld(this.reelHeld());
      }
    });
    this.on(c, 'wheel', (e) => {
      const w = e as WheelEvent;
      if (this.paused || this.js) return;
      // col binocolo la rotella cambia lo zoom
      if (this.bino > 0.5) {
        this.binoFov = w.deltaY < 0 ? 4.5 : 9;
        return;
      }
      this.setLamp(this.sim.lamp + (w.deltaY < 0 ? 1 : -1));
    });
    this.on(this.hud.turnEl, 'mouseenter', () => {
      if (this.turnArmed) this.turn();
      this.turnArmed = false;
    });
    this.on(this.hud.turnEl, 'mouseleave', () => {
      this.turnArmed = true;
    });
    this.on(this.sonarEl, 'mousedown', () => this.toggleSonar(false));
  }

  private keyDown(e: KeyboardEvent): void {
    const k = e.key.toLowerCase();
    if (this.cine) {
      // la cinematica di un finale: Esc (o Invio, Spazio) la salta
      if (k === 'escape' || k === 'enter' || k === ' ') {
        e.preventDefault();
        this.skipCinematic();
      }
      return;
    }
    if (k === 'tab') e.preventDefault();
    if (k === 'escape') {
      if (!this.finished) this.d.onPause();
      return;
    }
    if (this.paused || this.finished || this.js) return;
    if (e.repeat) return;
    this.held.add(k);
    switch (k) {
      case ' ':
        e.preventDefault();
        if (this.sonarOpen) this.toggleSonar(false);
        this.sim.pressRod();
        this.sim.setReelHeld(true);
        break;
      case 'f':
        this.sim.throwFish();
        break;
      case 'c':
      case 'control':
        this.hideToggle();
        break;
      case 'q':
        this.setLamp(this.sim.lamp - 1);
        break;
      case 'e':
        // alza la lampara; dal massimo la spegne (gira in tondo: spenta, bassa, alta)
        this.setLamp(this.sim.lamp >= 2 ? 0 : this.sim.lamp + 1);
        break;
      // W A S D: voltarsi di scatto verso prua, a sinistra, verso poppa, a destra (come in FNAF); col binocolo alzato
      // A e D girano piano e W e S inclinano (vedi update)
      case 'w':
        if (this.bino <= 0.5) this.face(YAW.bow);
        break;
      case 'a':
        if (this.bino <= 0.5) this.face(-90);
        break;
      case 's':
        if (this.bino <= 0.5) this.face(YAW.stern);
        break;
      case 'd':
        if (this.bino <= 0.5) this.face(90);
        break;
      case 'arrowdown':
        this.turn();
        break;
      case 'tab':
        this.toggleSonar();
        break;
      case 'b':
        this.raiseBino(!this.binoUp);
        break;
    }
  }

  /**
   * Il controller (src/app/pad.ts), un fotogramma: gli stessi comandi della tastiera e del mouse. Torna di quanto
   * girare e inclinare lo sguardo (stick, −1..1; con la croce col binocolo alzato).
   *   RT lancia, ferra e (tenuto) recupera · LT (tenuto) o B il binocolo · LB e RB la luce (col binocolo lo zoom)
   *   A il telone · X il pesce · Y il sonar · croce: voltarsi di scatto · R3 voltarsi indietro · Start la pausa
   */
  private padControls(): [number, number] {
    const p = pad;
    if (this.cine) {
      // la cinematica di un finale: A, B o Start la saltano
      if (p.pressed('A') || p.pressed('B') || p.pressed('Start')) this.skipCinematic();
      return [0, 0];
    }
    if (p.pressed('Start')) {
      // lo stesso Start non deve anche riprendere dalla pausa appena aperta
      p.consume();
      if (!this.finished) this.d.onPause();
      return [0, 0];
    }
    // il grilletto lasciato smette di recuperare anche a notte finita
    if (this.reelByPad && !p.down('RT')) {
      this.reelByPad = false;
      this.sim.setReelHeld(this.reelHeld());
    }
    if (p.released('LT')) this.binoUp = false;
    if (this.finished || this.js) return [0, 0];
    // col controller in mano il mouse rimasto fermo sul bordo dello schermo non gira più lo sguardo
    if (p.active) this.edgeArmed = false;
    const bino = this.bino > 0.5;
    if (p.pressed('RT')) {
      if (this.sonarOpen) this.toggleSonar(false);
      this.sim.pressRod();
      this.reelByPad = true;
      this.sim.setReelHeld(true);
    }
    if (p.pressed('X')) this.sim.throwFish();
    if (p.pressed('A')) this.hideToggle();
    if (p.pressed('Y')) this.toggleSonar();
    if (p.pressed('B')) {
      if (this.sonarOpen) this.toggleSonar(false);
      else this.raiseBino(!this.binoUp);
    }
    if (p.pressed('LT')) this.raiseBino(true);
    // LB e RB come la rotella: la luce giù e su; col binocolo lo zoom
    if (p.pressed('LB')) {
      if (bino) this.binoFov = 9;
      else this.setLamp(this.sim.lamp - 1);
    }
    if (p.pressed('RB')) {
      if (bino) this.binoFov = 4.5;
      else this.setLamp(this.sim.lamp + 1);
    }
    if (p.pressed('R3')) this.turn();
    let [spin, tilt] = p.look();
    tilt = -tilt;
    if (bino) {
      // col binocolo la croce gira e inclina piano, come W A S D
      if (p.down('Left')) spin = -1;
      if (p.down('Right')) spin = 1;
      if (p.down('Up')) tilt = 1;
      if (p.down('Down')) tilt = -1;
    } else {
      // la croce: voltarsi di scatto verso prua, a sinistra, verso poppa, a destra (come W A S D)
      if (p.pressed('Up')) this.face(YAW.bow);
      if (p.pressed('Left')) this.face(-90);
      if (p.pressed('Down')) this.face(YAW.stern);
      if (p.pressed('Right')) this.face(90);
    }
    return [spin, tilt];
  }

  /** Il suggerimento `k` coi tasti del controller, se è quello in uso (e se il testo ne parla). */
  private hintText(k: keyof (typeof STRINGS)['it']['hints']): string {
    const padText = pad.active ? this.S.pad.hints[k] : undefined;
    return padText ? pad.glyphs(padText) : this.S.hints[k];
  }

  /** Alza o abbassa il binocolo; alzandolo vicino a un luogo lo sguardo si centra su di lui. */
  private raiseBino(up: boolean): void {
    if (up && !this.canBino()) return;
    if (up && !this.binoUp) {
      const view = this.d.stage.view;
      const p = this.binoPlaceNear(view.yaw, 0, 14);
      this.binoPitch = p ? p.pitch : 2.5;
      // (con la Madre vicina lo sguardo non si sposta da solo: mentre passa sotto la barca girarsi è la morte)
      if (p && !this.sim.mother?.near) view.targetYaw += ((((p.yaw - view.targetYaw) % 360) + 540) % 360) - 180;
    }
    this.binoUp = up;
  }

  /** Il luogo del binocolo più vicino allo sguardo, se è entro `k` volte la sua larghezza (o entro `deg` gradi). */
  private binoPlaceNear(yaw: number, k: number, deg = 0): { yaw: number; pitch: number } | null {
    let best: { d: number; yaw: number; pitch: number } | null = null;
    for (const p of this.d.assets.binocular.places) {
      const d = Math.abs(((p.yaw - yaw + 540) % 360) - 180);
      if (d < Math.max(deg, (p.hfov / 2) * k) && (!best || d < best.d)) best = { d, yaw: p.yaw, pitch: p.pitch };
    }
    return best;
  }

  /** Il binocolo si alza solo fuori dal telone, col sonar chiuso e senza un pesce in canna. */
  private canBino(): boolean {
    return !this.js && !this.finished && this.sim.hide === 'out' && !this.sonarOpen && this.sim.fishing.phase !== 'reeling';
  }

  private mouseDown(e: MouseEvent): void {
    if (e.button === 2) {
      if (!this.paused) this.raiseBino(true);
      return;
    }
    if (this.paused || this.finished || this.js || e.button !== 0) return;
    if (this.bino > 0.5) return;
    this.mouse.down = true;
    if (this.sim.hide !== 'out') {
      // sotto il telone il clic serve solo a uscire
      if (this.sim.hide === 'in') this.hideToggle();
      return;
    }
    const t = this.targetAt(this.mouse.x, this.mouse.y);
    if (t === 'bucket') this.sim.throwFish();
    else if (t === 'tarp') this.hideToggle();
    else if (t === 'lamp') this.setLamp(this.sim.lamp === 2 ? 0 : this.sim.lamp + 1);
    else if (t === 'sonar') this.toggleSonar(true);
    else if (t === 'rod' || this.sim.facing(YAW.rod, VIEW.rodHalfAngle)) {
      this.sim.pressRod();
      this.reelByMouse = true;
      this.sim.setReelHeld(true);
    }
  }

  private hideToggle(): void {
    if (this.sonarOpen) this.toggleSonar(false);
    this.sim.toggleHide();
  }

  /** La luce si regola anche da sotto il telone (Q, E e rotella: richiesta dell'utente, 11 ottobre sera). */
  private setLamp(l: number): void {
    const lv = Math.max(0, Math.min(2, l)) as LampLevel;
    this.sim.setLamp(lv);
  }

  private turn(): void {
    if (this.paused || this.finished || this.js || this.sim.hide !== 'out') return;
    const v = this.d.stage.view;
    v.targetYaw = v.targetYaw + 180;
    this.edgeArmed = false;
  }

  /** Voltarsi di scatto verso una direzione (gradi, spazio della barca), per la via più corta. */
  private face(yaw: number): void {
    if (this.paused || this.finished || this.js || this.sim.hide !== 'out' || this.sonarOpen) return;
    const v = this.d.stage.view;
    v.targetYaw += ((((yaw - v.targetYaw) % 360) + 540) % 360) - 180;
    this.edgeArmed = false;
  }

  private toggleSonar(open = !this.sonarOpen): void {
    if (this.sim.hide !== 'out' && open) return;
    if (open && this.sim.blackout) {
      // a batteria morta lo schermo resta nero: il tasto scatta a vuoto
      this.d.audio.play('lamp_switch', { gain: 0.25, rate: 1.3 });
      return;
    }
    this.sonarOpen = open;
    this.sonarEl.classList.toggle('show', open);
    this.d.audio.play(open ? 'radio_on' : 'radio_off', { gain: 0.25 });
  }

  /** Su cosa sta il puntatore (direzione dall'occhio, spazio della barca). */
  private targetAt(x: number, y: number): Target {
    const view = this.d.stage.view;
    const dir = view.unproject(x, 1 - y) as Vec3;
    const P = this.d.stage.man.points;
    const near = (p: Vec3, deg: number) => angleBetween(dir, p) < deg;
    if (near(P.bucket, 8)) return 'bucket';
    if (near(P.tarp, 10)) return 'tarp';
    const sc = P.sonarScreen;
    const sonarC: Vec3 = [(sc[0][0] + sc[2][0]) / 2, (sc[0][1] + sc[2][1]) / 2, (sc[0][2] + sc[2][2]) / 2];
    if (near(sonarC, 9)) return 'sonar';
    if (near(P.lamp, 6)) return 'lamp';
    // la canna: dal calcio alla punta
    const butt: Vec3 = [0.86, 0.85, -0.85];
    const tip = P.rodTip;
    for (let i = 0; i <= 10; i++) {
      const s = i / 10;
      const p: Vec3 = [butt[0] + (tip[0] - butt[0]) * s, butt[1] + (tip[1] - butt[1]) * s, butt[2] + (tip[2] - butt[2]) * s];
      if (near(p, 4.5)) return 'rod';
    }
    return null;
  }

  // ───────────────────────── aggiornamento ─────────────────────────

  update(dt: number): void {
    const st = this.d.stage;
    const view = st.view;
    if (this.paused) return;
    const sim = this.sim;
    const [padSpin, padTilt] = this.padControls();
    // (il controller può aver messo in pausa)
    if (this.paused) return;

    // sguardo
    if (!this.js && sim.hide === 'out' && !this.sonarOpen && !this.finished) {
      const reeling = sim.fishing.phase === 'reeling';
      let spin = 0;
      const edge = 0.2;
      const mx = this.mouse.x;
      if (this.mouse.inside && !reeling && this.edgeArmed) {
        if (mx < edge) spin = -(((edge - mx) / edge) ** 1.5);
        else if (mx > 1 - edge) spin = ((mx - (1 - edge)) / edge) ** 1.5;
      }
      // le frecce girano piano; A e D solo col binocolo (senza, voltano di scatto: keyDown)
      if ((this.bino > 0.5 && this.held.has('a')) || this.held.has('arrowleft')) spin = -1;
      if ((this.bino > 0.5 && this.held.has('d')) || this.held.has('arrowright')) spin = 1;
      // lo stick del controller (morbido: pad.look); fermo, non toglie niente al mouse e alla tastiera
      if (padSpin) spin = padSpin;
      // col binocolo si gira piano, in proporzione allo zoom; su e giù coi bordi alto e basso
      const zoomK = this.bino > 0 ? view.hfov / 90 : 1;
      view.targetYaw += spin * 150 * this.d.options.sensitivity * dt * zoomK;
      if (this.bino > 0.5) {
        let tilt = 0;
        if (this.mouse.inside) {
          const my = this.mouse.y;
          if (my < edge) tilt = ((edge - my) / edge) ** 1.5;
          else if (my > 1 - edge) tilt = -(((my - (1 - edge)) / edge) ** 1.5);
        }
        if (this.held.has('w') || this.held.has('arrowup')) tilt = 1;
        if (this.held.has('s')) tilt = -1;
        if (padTilt) tilt = padTilt;
        this.binoPitch = Math.max(-8, Math.min(12, this.binoPitch + tilt * 30 * zoomK * dt));
        // vicino a un luogo, quando smetti di girare lo sguardo ci scivola sopra da solo (centrarlo a mano è scomodo, e
        // fuori dal luogo si vede il panorama lontano, che da vicino è sgranato)
        if (spin === 0 && tilt === 0 && !sim.mother?.near) {
          const p = this.binoPlaceNear(view.targetYaw, 1.1);
          if (p) {
            const k = 1 - Math.exp(-3.2 * dt);
            view.targetYaw += (((((p.yaw - view.targetYaw) % 360) + 540) % 360) - 180) * k;
            this.binoPitch += (p.pitch - this.binoPitch) * k;
          }
        }
      }
    }
    if (!this.canBino()) this.binoUp = false;
    this.bino = approach(this.bino, this.binoUp ? 1 : 0, 7, dt);
    if (this.bino < 0.001) this.bino = 0;
    if (!this.js) {
      const e = smooth01(this.bino);
      view.hfov = 90 + (this.binoFov - 90) * e;
      view.pitch = -12 + (this.binoPitch + 12) * e;
      // le mani che reggono il binocolo: un tremolio lento e il respiro
      const t = this.d.stage.time;
      const kick = this.castKick();
      view.swayYaw = e * (0.10 * Math.sin(t * 0.9) + 0.05 * Math.sin(t * 2.3 + 1.0) + 0.03 * Math.sin(t * 5.1)) + kick[0];
      view.swayPitch = e * (0.08 * Math.sin(t * 0.7 + 2.0) + 0.04 * Math.sin(t * 1.9)) + kick[1];
      view.steady = 0.75 * e;
    }
    // mentre guardi nel binocolo non vedi la barca: Molly non si sente guardata
    sim.setView(view.yaw, this.sonarOpen || this.bino > 0.5, this.sonarOpen);
    // dove guarda il binocolo (il Foxy si controlla così)
    sim.setBino(this.bino > 0.5 && !this.js ? { yaw: view.yaw, pitch: view.pitch, fov: view.hfov } : null);
    if (!this.finished) sim.update(dt);
    for (const e of sim.drainEvents()) this.handle(e);

    this.updateVisuals(dt);
    this.updateVivi(dt);
    this.updateFear(dt);
    this.updateAudio(dt);
    this.updateRadio(dt);
    this.updateHud(dt);
    // a batteria morta il sonar tace: niente ping, niente avvisi
    if (!sim.blackout) this.sonar.update(dt, sim);

    // fine della notte: la scena finisce di raccontare, poi si passa allo schermo dei risultati
    if (this.finished && this.endResult) {
      this.endTimer -= dt;
      if (this.endTimer <= 0) {
        const r = this.endResult;
        this.endResult = null;
        // il segnale salta: l'urlo si tronca insieme all'immagine, poi c'è solo la statica
        this.js?.scream?.stop(0.03);
        this.d.onEnd(r);
      }
    }
  }

  private stats(): NightStats {
    const s = this.sim;
    return { caught: s.caught, fed: s.fed, lore: [...s.loreThisNight], time: s.time, bucket: s.fish };
  }

  private handle(e: GameEvent): void {
    const a = this.d.audio;
    const fx = this.d.sfx;
    const S = this.S;
    // le didascalie degli eventi («Molly si affaccia») sono un'opzione a parte, spenta di default
    const cap = (t: string) => this.d.options.captions && this.hud.caption(t);
    const sideName = (side: 'left' | 'right') => (side === 'left' ? S.captions.left : S.captions.right);
    const molly = this.sim.molly;
    const mollyAt = () => dirPos(molly.yaw, 1.15, -18);
    switch (e.t) {
      case 'hour':
        this.bells = Array.from({ length: e.hour }, (_, i) => 0.4 + i * 2.3);
        if (e.hour < 6) cap(S.captions.bell);
        break;
      case 'cast':
        a.play('cast', { pos: [1.2, 2.0, 0.2] });
        this.castT = 0;
        break;
      case 'plop':
        a.play('plop', { pos: this.floatPos(), gain: 0.8 });
        this.plopT = 0;
        this.splashSeed = Math.random() * 1000;
        this.ripple(1, 0);
        this.ripple(0.7, -0.2);
        this.ripple(0.45, -0.45);
        break;
      case 'bite':
        this.biteAt = this.sim.time;
        pad.rumble('bite');
        a.play(Math.random() < 0.5 ? 'rod_bell_1' : 'rod_bell_2', { pos: this.d.stage.man.points.rodTip });
        this.ripple(0.6, 0);
        this.rod.kick(4);
        break;
      case 'baitStolen':
        a.play('splash_s1', { pos: this.floatPos(), gain: 0.5 });
        this.ripple(0.8, 0);
        this.retrieveFloat('reel');
        this.hud.toast(S.baitStolen, '', 1.8);
        break;
      case 'hooked':
        this.strikeT = 0;
        this.loops.reel = a.play('reel_loop', { loop: true, gain: 0, pos: [0.86, 0.85, -0.6] });
        this.loops.tension = a.play('line_tension', { loop: true, gain: 0, pos: [1.6, 2.6, 0.1] });
        break;
      case 'fishPull':
        a.play(['splash_s1', 'splash_s2', 'splash_s3'][Math.floor(Math.random() * 3)]!, { pos: this.floatPos(), gain: 0.7 });
        this.lineSway = (Math.random() < 0.5 ? -1 : 1) * (0.4 + Math.random() * 0.4);
        this.ripple(0.9, 0);
        this.rod.kick(5, -2);
        break;
      case 'lineSnap':
        a.play('line_snap', { pos: this.d.stage.man.points.rodTip });
        this.retrieveFloat('lost');
        // il carico se ne va di colpo: la punta scatta su e vibra
        this.rod.kick(-14, 6);
        this.hud.toast(S.lineSnap, '', 1.8);
        this.stopReel();
        break;
      case 'fishEscaped':
        a.play('splash_s2', { pos: this.floatPos(), gain: 0.5 });
        this.ripple(1, 0);
        this.rod.kick(-6, 2);
        this.retrieveFloat('reel');
        this.hud.toast(S.escaped, '', 1.8);
        this.stopReel();
        break;
      case 'landed': {
        this.stopReel();
        this.retrieveFloat('lift');
        a.play('fish_out', { pos: [1.2, 2.0, -0.4] });
        if (e.lore) {
          const lt = LORE_TEXT[this.d.lang][e.lore];
          this.hud.toast(lt?.title ?? '', S.loreFound, 3.2);
        } else if (e.species) {
          setTimeout(() => a.play('fish_bucket', { pos: this.d.stage.man.points.bucket }), 700);
          const sp = FISH_BY_ID[e.species];
          const L = this.d.lang;
          if (sp) {
            const known = this.d.knownSpecies?.has(sp.id) ?? true;
            this.hud.catchCard({
              img: this.d.assets.fish[sp.id] ?? null,
              name: sp.name[L],
              meta: `${S.families[sp.family]} · ${S.rarities[sp.rarity]}`,
              kg: `${e.kg < 1 ? e.kg.toFixed(2) : e.kg.toFixed(1)} ${S.kg}`,
              desc: sp.desc[L] ?? sp.desc.it,
              family: sp.family,
              isNew: known ? null : S.newSpecies,
            });
            this.d.knownSpecies?.add(sp.id);
          } else {
            this.hud.toast(e.species, `${S.caught} · ${e.kg.toFixed(2)} ${S.kg}`, 2.4);
          }
          this.d.onCatch?.(e.species, e.kg);
        }
        break;
      }
      case 'lamp':
        this.d.stage.lampTarget = e.level;
        if (e.level === 0) this.d.stage.lampDip = 0;
        a.play('lamp_switch', { pos: [0, 4.17, 0.55], gain: 0.7 });
        this.hud.setLamp(e.level);
        break;
      case 'hideStart':
        a.play('tarp_in', { gain: 0.9 });
        this.stopReel();
        break;
      case 'unhideStart':
        a.play('tarp_out', { gain: 0.9 });
        break;
      case 'hidden':
        this.loops.tarp = a.play('amb_tarp', { loop: true, fadeIn: 0.6, gain: 0.7 });
        break;
      case 'unhidden':
        this.loops.tarp?.stop(0.5);
        this.loops.tarp = null;
        break;
      case 'throwFish':
        a.play('fish_throw', { pos: [0.2, 1.8, -0.2] });
        break;
      case 'denied':
        if (e.reason === 'noFish') this.hud.toast(S.denied.noFish, '', 1.4);
        else if (e.reason === 'notFacing' && this.sim.gulpy.canBeFed) this.hud.toast(S.denied.notFacing, '', 1.2);
        else if (e.reason === 'dark' || e.reason === 'broken') {
          // l'interruttore scatta, ma non succede niente
          a.play('lamp_switch', { pos: LAMP_AT, gain: 0.35, rate: 0.85 });
          this.hud.toast(e.reason === 'dark' ? S.denied.dark : S.denied.broken, '', 1.4);
        }
        break;
      case 'archie':
        switch (e.e) {
          case 'rise':
            fx.archieRise(ARCHIE_AT);
            cap(S.captions.archieRise);
            break;
          case 'inhale':
          case 'relight': {
            this.archieBreath?.stop(0.1);
            const cfg = this.sim.cfg.archie!;
            this.archieBreath = fx.archieInhale(ARCHIE_AT, e.e === 'inhale' ? cfg.inhale : cfg.relight, e.e === 'relight');
            cap(S.captions.archieInhale);
            break;
          }
          case 'wait':
            this.archieBreath?.stop(0.25);
            this.archieBreath = null;
            fx.archieWait(ARCHIE_AT);
            cap(S.captions.archieWait);
            break;
          case 'blow':
            this.archieBreath?.stop(0.05);
            this.archieBreath = null;
            fx.archieBlow(ARCHIE_AT, LAMP_AT);
            // il vetro esplode: un lampo, poi il buio
            this.d.stage.lampDip = 1;
            cap(S.captions.archieBlow);
            break;
          case 'dive':
            this.archieBreath?.stop(0.3);
            this.archieBreath = null;
            fx.archieDive(ARCHIE_AT);
            cap(S.captions.archieDive);
            break;
          default:
            break;
        }
        break;
      case 'lampy':
        switch (e.e) {
          case 'grab':
            // prende la lenza: il galleggiante va sotto come per un pesce, ma non suona niente
            this.biteAt = this.sim.time;
            this.ripple(0.5, 0);
            fx.lampyGrab(this.floatPos());
            break;
          case 'beat':
            // un colpo del campanellino, sempre uguale e sempre a tempo: la canna dà lo stesso strattone
            fx.lampyBell(this.d.stage.man.points.rodTip);
            this.rod.kick(3.2);
            if (e.n === 1) cap(S.captions.lampyBeat);
            break;
          case 'giggle':
            fx.lampyGiggle(LAMPY_AT);
            cap(S.captions.lampyGiggle);
            break;
          case 'surface':
            fx.lampySurface(LAMPY_AT);
            cap(S.captions.lampySurface);
            break;
          case 'let':
            fx.lampyLet(LAMPY_AT);
            cap(S.captions.lampyLet);
            break;
          case 'hooked':
            // l'hai agganciata: la canna si piega tutta
            this.rod.kick(8, -3);
            break;
          case 'climb':
            fx.lampyClimb(LAMPY_AT);
            cap(S.captions.lampyClimb);
            break;
          default:
            break;
        }
        break;
      case 'fangy':
        switch (e.e) {
          case 'approach':
            fx.fangyApproach(dirPos(YAW.fangy + FANGY_SWING, FANGY_FAR, -6));
            cap(S.captions.fangyApproach);
            break;
          case 'rise':
            fx.fangyRise(FANGY_AT);
            cap(S.captions.fangyRise);
            break;
          case 'snap':
            // ti ha sentito: la testa scatta verso prua, dove hai fatto rumore, e le lucine si accendono tutte
            this.v.fHead = 1;
            this.v.fHeadT = 1.8;
            this.v.fFlash = 1;
            fx.fangySnap(FANGY_AT, e.n ?? 1);
            cap(S.captions.fangySnap);
            break;
          case 'leave':
            fx.fangyLeave(FANGY_AT);
            cap(S.captions.fangyLeave);
            break;
          default:
            break;
        }
        break;
      case 'foxy': {
        // il Foxy (grafica provvisoria finché non arrivano i render; i suoni sono i file foxy_*, da approvare)
        const at = this.sim.foxy?.places[e.place ?? 0];
        switch (e.e) {
          case 'lean':
            // si sporge mentre non lo guardi: laggiù, appena udibile, il costume che si svuota d'acqua
            if (at) fx.foxyNear(dirPos(at.yaw, 9, 0));
            cap(S.captions.foxyLean);
            break;
          case 'leave':
            // il posto è vuoto: un tonfo lontano, poi qualcosa che corre sull'acqua verso la barca (finisce sul salto)
            if (at) fx.foxyLeave(dirPos(at.yaw, 6, 0), this.sim.foxy?.timer ?? 3.2);
            cap(S.captions.foxyLeave);
            break;
          default:
            break;
        }
        break;
      }
      case 'robin': {
        const bucket = this.d.stage.man.points.bucket;
        switch (e.e) {
          case 'climb':
            fx.robinClimb(ROBIN_AT);
            cap(S.captions.robinClimb);
            break;
          case 'reach':
            fx.robinRattle(bucket);
            cap(S.captions.robinRattle);
            break;
          case 'rattle':
            fx.robinRattle(bucket);
            break;
          case 'steal':
            fx.robinSteal(bucket, ROBIN_AT);
            cap(S.captions.robinSteal);
            break;
          case 'scared':
            fx.robinScared(ROBIN_AT);
            cap(S.captions.robinScared);
            break;
          default:
            break;
        }
        break;
      }
      case 'battery':
        if (e.e === 'low') {
          // l'ago entra nel rosso: la lampara comincia a tremolare
          cap(S.captions.lampSick);
        } else {
          // l'ultimo sfrigolio, poi il buio: si spengono lampara e sonar
          a.play('lamp_flicker', { pos: LAMP_AT, gain: 0.9, rate: 0.8 });
          this.d.stage.lampDip = 1;
          if (this.sonarOpen) this.toggleSonar(false);
          cap(S.captions.lampDead);
        }
        break;
      case 'lullaby':
        if (e.e === 'start') {
          // dal fondo, piano: il carillon della Madre (lo stesso del menu), ovattato, che si apre salendo.
          // Dura quanto la canzone: se finisce prima delle sei, la Madre sale.
          this.lullabyV = a.play('mus_title', { loop: false, gain: 0, lowpass: 320 });
          this.lullabyV?.setGain(0.95, 5);
          this.lullabyV?.setLowpass(5000, 16);
          cap(S.captions.lullaby);
        }
        break;
      case 'gulpy':
        switch (e.e) {
          case 'rise':
            fx.emerge('gulpy', this.gulpyFar);
            cap(S.captions.bowGurgle);
            break;
          case 'gurgle':
            fx.gurgle(this.sim.gulpy.state === 'rising' ? this.gulpyFar : this.bowAt, this.sim.gulpy.state === 'demanding' ? 1.2 : 0.8);
            break;
          case 'climb':
            // si rituffa e riemerge aggrappato alla prua: un tonfo, poi lo scafo che cede sotto il suo peso
            this.gulpyDive = 1;
            a.play('splash_big', { pos: this.gulpyFar, gain: 0.6 });
            setTimeout(() => fx.grab(this.bowAt), 2200);
            cap(S.captions.bowClimb);
            break;
          case 'demand':
            fx.gurgle(this.bowAt, 1.4);
            cap(S.captions.bowDemand);
            break;
          case 'fed':
            fx.chew(this.bowAt);
            cap(S.captions.bowEat);
            break;
          case 'fedEarly':
            fx.chew(this.gulpyFar);
            cap(S.captions.bowEat);
            break;
          case 'leave':
            a.play('splash_big', { pos: this.bowAt, gain: 0.8 });
            cap(S.captions.bowLeave);
            break;
          default:
            break;
        }
        break;
      case 'molly':
        switch (e.e) {
          case 'knock':
            fx.knock(mollyAt());
            cap(`${S.captions.knock} · ${sideName(e.side)}`);
            break;
          case 'peek':
            fx.peek(mollyAt());
            cap(`${S.captions.peek} · ${sideName(e.side)}`);
            break;
          case 'giggle':
            fx.giggle(mollyAt());
            cap(S.captions.giggle);
            break;
          case 'whine':
            fx.whine(mollyAt());
            cap(S.captions.whine);
            break;
          case 'tantrum':
            fx.tantrum(mollyAt());
            cap(S.captions.tantrum);
            break;
          case 'calm':
            cap(S.captions.calm);
            break;
          case 'gone':
            a.play('splash_s2', { pos: mollyAt(), gain: 0.6 });
            cap(S.captions.mollyLeave);
            break;
          default:
            break;
        }
        break;
      case 'hatch':
        switch (e.e) {
          case 'count': {
            const n = e.n ?? 1;
            const words = S.hatchCount;
            const text = e.last ? `${words[words.length - 1]} ${S.hatchReady}` : words[Math.min(n, words.length) - 1]!;
            speak(this.d.audio, text, { ...CHILD, pitch: 250, gain: 0.55 }, { pos: HATCH_AT, bus: 'sfx', maxDuration: e.last ? 2.6 : 0.9 });
            this.v.hMouthT = 0;
            if (this.d.options.subtitles) this.hud.subtitle(S.hatchName, text);
            if (n === 1) fx.emerge('hatch', HATCH_AT);
            break;
          }
          case 'board':
            fx.board([0, -2.2, -0.6]);
            cap(S.captions.hatchBoard);
            break;
          case 'step':
            fx.step(dirPos(180 + this.sim.hatch.lureX * 35, 1.6, -30));
            cap(S.captions.hatchStep);
            break;
          case 'sniff':
            fx.sniff(dirPos(180 + this.sim.hatch.lureX * 35, 1.2, -20));
            cap(S.captions.hatchSniff);
            break;
          case 'leave':
            setTimeout(() => a.play('splash_big', { pos: [0, -3.2, -1.25], gain: 0.8 }), 900);
            cap(S.captions.hatchLeave);
            break;
          default:
            break;
        }
        break;
      case 'mother': {
        // la Madre (notte 6): i momenti dell'avvicinamento (il mare che si ferma, la lampara che trema, la ninna nanna)
        // seguono il tempo dello stato in updateMother
        const mo = this.sim.mother!;
        switch (e.e) {
          case 'call':
            fx.motherCall(dirPos(mo.angle, 60, -12));
            cap(S.captions.motherCall);
            break;
          case 'approach':
            this.motherSkip = Math.max(0, this.d.audio.duration('madre_approach') - mo.approachTime);
            this.motherApproachV = fx.motherApproach(this.motherSkip);
            cap(S.captions.motherApproach);
            break;
          case 'pass':
            // il mouse rimasto nella fascia del bordo non gira più lo sguardo da solo (sarebbe la morte senza un gesto):
            // gira di nuovo solo se lo muovi (revisione dell'11 ottobre)
            this.edgeArmed = false;
            this.motherPassV?.stop(1);
            this.motherPassV = fx.motherPass(e.n ?? 1);
            cap(S.captions.motherPass);
            break;
          case 'leave':
            // la ninna nanna si spegne mentre se ne va; la passata finisce da sola
            this.motherSong?.stop(4.5);
            this.motherSong = null;
            cap(S.captions.motherLeave);
            break;
          default:
            break;
        }
        break;
      }
      case 'dead':
        this.finished = true;
        this.sim.setReelHeld(false);
        this.stopReel();
        // l'avvicinamento della Madre non continua sopra il jumpscare o il buio
        this.motherApproachV?.stop(0.2);
        this.motherApproachV = null;
        if (e.killer === 'mother' && this.sim.outcome.kind === 'dead' && this.sim.outcome.cause === 'moved') {
          // ti sei mosso mentre passava sotto la barca: ti prende dal basso
          this.motherSong?.stop(0.05);
          this.motherPassV?.stop(0.05);
          this.motherSong = this.motherPassV = null;
          this.startJumpscare('mother');
          this.endResult = { kind: 'dead', killer: 'mother', cause: 'moved', stats: this.stats() };
          const seq = this.d.assets.jumpscares.mother;
          this.endTimer = seq ? seq.frames.length / seq.fps : 1.9;
        } else if (e.killer === 'mother') {
          const o = this.sim.outcome;
          const cause = o.kind === 'dead' ? o.cause : undefined;
          this.endResult = { kind: 'dead', killer: 'mother', cause, stats: this.stats() };
          this.endTimer = 4.5;
          const quota = this.d.assets.jumpscares.quota;
          if (!cause && quota) {
            // la quota mancata alle sei (deciso l'11 ottobre sera): l'occhio della Madre sale da sotto la barca e ti
            // guarda attraverso l'acqua; la Madre intera si vede solo nella notte 6
            this.lullabyV?.stop(0.2);
            this.lullabyV = null;
            this.motherSong?.stop(0.2);
            this.motherSong = null;
            this.startJumpscare('quota');
            this.endResult = { kind: 'dead', killer: 'mother', stats: this.stats(), js: true };
            this.endTimer = quota.frames.length / quota.fps;
          } else if (cause === 'lullaby') {
            // la canzone è finita al buio: sotto la barca sale qualcosa di enorme
            this.lullabyV?.stop(0.2);
            this.lullabyV = null;
            this.motherSong?.stop(0.2);
            this.motherSong = null;
            a.play('splash_big', { pos: [0, 1.2, -2.2], gain: 1, rate: 0.7 });
            a.play('mus_madre', { gain: 1 });
            this.d.stage.view.shake = this.d.options.reduceFlash ? 0.4 : 1.6;
          } else {
            // le campane della festa, ovattate, e sotto la Madre che si sveglia (se cantava, la canzone sfuma)
            this.lullabyV?.stop(2);
            this.lullabyV = null;
            this.motherSong?.stop(2);
            this.motherSong = null;
            a.play('bell_dawn', { pos: dirPos(BELL_YAW, 5, 4), gain: 0.35, lowpass: 900 });
            a.play('mus_madre', { gain: 0.9 });
            this.hud.toast(S.sixAm, S.quotaMissed, 4);
          }
        } else {
          // (se stava arrivando la Madre, la sua ninna nanna si tronca col segnale)
          this.motherSong?.stop(0.2);
          this.motherSong = null;
          this.startJumpscare(e.killer);
          this.endResult = { kind: 'dead', killer: e.killer, stats: this.stats() };
          // il segnale salta appena finisce l'assalto, prima che l'immagine resti ferma
          const seq = this.d.assets.jumpscares[e.killer];
          this.endTimer = seq ? seq.frames.length / seq.fps : 1.2;
        }
        break;
      case 'won':
        this.finished = true;
        this.stopReel();
        // salvo all'alba: il carillon si spegne
        this.lullabyV?.stop(3);
        this.lullabyV = null;
        this.motherSong?.stop(3);
        this.motherSong = null;
        // il finale con la cinematica: alla notte 6 sempre (A o uno dei segreti), alla notte extra il finale B se
        // l'App l'ha deciso (vinta con tutti, Madre compresa, almeno a 10)
        const ending = this.nightNo === 6 ? (this.d.ending ?? 'A') : this.d.ending === 'B' ? 'B' : undefined;
        this.endResult = { kind: 'won', stats: this.stats(), ...(ending ? { ending } : {}) };
        this.endTimer = 7;
        a.play('bell_dawn', { pos: dirPos(BELL_YAW, 5, 4), gain: 0.8, lowpass: 3000 });
        this.loops.drone?.stop(3);
        this.loops.drone = null;
        this.hud.toast(S.sixAm, `${S.survived} · ${S.quotaMet}`, 6);
        // le altre notti, e la notte extra vinta con impostazioni più facili, hanno l'alba normale
        if (ending) {
          // il finale della notte 6, la cinematica: il finale A (la Madre sale accanto alla barca, si prende il secchio e
          // torna giù coi figli; poi sorge il sole e la radio) o uno dei due segreti, «I tuoi» e «Nessuno», secondo i
          // pesci lasciati nelle tane (save.chooseEnding); alla notte extra il finale B «Il ricordo»
          const cine = ENDING_CINE[ending];
          this.startCinematic(cine);
          this.endTimer = cine.length + 0.2;
        } else {
          setTimeout(() => a.play('mus_6am', { gain: 0.85 }), 1500);
          this.loops.dawn = a.play('amb_dawn', { loop: true, fadeIn: 4, gain: 0.8 });
        }
        break;
      default:
        break;
    }
  }

  private stopReel(): void {
    this.loops.reel?.stop(0.1);
    this.loops.tension?.stop(0.1);
    this.loops.reel = this.loops.tension = null;
  }

  private startJumpscare(killer: MonsterId | 'mother' | 'quota'): void {
    // la camera si gira dove la creatura parte (la posa di gioco da cui partono i fotogrammi); la Madre viene da sotto,
    // dove stai guardando
    const L = this.d.stage.man.layers;
    const yaw =
      killer === 'mother'
        ? this.d.stage.view.yaw
        : killer === 'quota'
        ? -50
        : killer === 'gulpy'
        ? (L[POSE.gulpyPretende]?.yaw ?? 0)
        : killer === 'molly'
          ? this.sim.molly.yaw
          : killer === 'robin'
            ? (L[POSE.robin]?.yaw ?? YAW.robin)
            : killer === 'archie'
              ? YAW.archie
              : killer === 'lampy'
                ? YAW.lampy
                : killer === 'fangy'
                  ? YAW.fangy
                  : killer === 'foxy'
                    ? (this.sim.foxy?.places[this.sim.foxy.place]?.yaw ?? 180)
                    : (L[POSE.hatchConta]?.yaw ?? 180);
    this.binoUp = false;
    this.bino = 0;
    this.d.stage.view.swayYaw = this.d.stage.view.swayPitch = this.d.stage.view.steady = 0;
    if (this.sonarOpen) this.toggleSonar(false);
    const reduce = this.d.options.reduceFlash;
    this.js = { killer, t: 0, yaw, scream: this.d.sfx.jumpscare(killer) };
    pad.rumble('scare');
    this.d.stage.view.shake = reduce ? 0.6 : 3.2;
  }

  // ───────────────────────── grafica ─────────────────────────

  private updateVisuals(dt: number): void {
    const sim = this.sim;
    const v = this.v;
    const st = this.d.stage;
    const g = sim.gulpy, m = sim.molly, h = sim.hatch;

    // Gulpy: emerge lontano davanti alla prua, si rituffa e riappare aggrappato alla prua
    let saleT = 0, riseT = 0, pretT = 0;
    if (g.state === 'rising') {
      saleT = 1;
      riseT = smooth01(g.phase * 1.4);
    } else if (g.state === 'climbing') {
      const p = g.phase;
      saleT = p < 0.3 ? 1 : 0;
      riseT = p < 0.3 ? 1 - smooth01(p / 0.3) : 0;
      pretT = p > 0.45 ? 1 : 0;
      if (p > 0.45 && v.gPret < 0.05 && this.gulpyDive > 0) {
        // la lampara sfarfalla proprio mentre lui si aggrappa
        st.lampDip = 1;
        this.d.audio.play('lamp_flicker', { pos: [0, 4.17, 0.55], gain: 0.6 });
        this.gulpyDive = 0;
      }
    } else if (g.state === 'demanding' || g.state === 'eating') {
      pretT = 1;
    } else if (g.state === 'leaving') {
      // nutrito presto torna giù da lontano; altrimenti lascia la prua
      saleT = v.gSale > 0.05 ? 1 : 0;
      riseT = 0;
      pretT = 0;
    } else if (g.state === 'attack') {
      pretT = v.gPret > 0.5 ? 1 : 0;
    }
    // al largo emerge dall'acqua (si vede solo quello che sta sopra il pelo dell'acqua: niente dissolvenza)
    v.gSale = saleT > v.gSale ? 1 : approach(v.gSale, saleT, 1.5, dt);
    v.gRise = approach(v.gRise, riseT, 4, dt);
    // alla prua sale da dietro il bordo; se ne va lasciandosi ricadere giù
    v.gPret = toward(v.gPret, pretT, 0.7, 1.0, dt);
    if (v.gRise < 0.02 && saleT === 0) v.gSale = approach(v.gSale, 0, 6, dt);

    // Molly: sale dal suo lato e si affaccia sul bordo, scivola giù quando è contenta
    const mollyShown = m.state === 'peeking' || m.state === 'tantrum' || m.state === 'attack';
    const rT = mollyShown && m.side === 'right' ? 1 : 0;
    const lT = mollyShown && m.side === 'left' ? 1 : 0;
    v.mR = toward(v.mR, rT, 0.6, 0.9, dt);
    v.mL = toward(v.mL, lT, 0.6, 0.9, dt);

    // Hatch: emerge piano dietro la poppa per contare; quando sale a bordo si rituffa
    const counting = h.state === 'counting';
    v.hRise = toward(v.hRise, counting ? 1 : 0, 1.6, 0.9, dt);

    // Archie: il collo esce dall'acqua davanti alla prua e ci torna quando si rituffa. Mentre sale e mentre aspetta
    // al buio prende fiato nella trombetta, che si srotola a metà e si riavvolge; mentre fa il risucchio la tiene
    // arrotolata stretta; quando soffia si distende tutta
    const ar = sim.archie;
    const archieT = ar && (ar.present || ar.state === 'attack') ? 1 : 0;
    const cfgA = sim.cfg.archie;
    v.aRise = toward(v.aRise, archieT, cfgA?.rise ?? 3, cfgA?.dive ?? 2, dt);
    const idle = ar && (ar.state === 'rising' || ar.state === 'waiting');
    if (idle) v.aHornT += dt;
    else v.aHornT = 0;
    // un respiro ogni 3,4 s: la trombetta si srotola in 0,6 s, resta un attimo, si riavvolge in 0,9 s
    const hb = v.aHornT % 3.4;
    const breath = !idle ? 0 : hb < 0.6 ? smooth01(hb / 0.6) : hb < 0.9 ? 1 : hb < 1.8 ? 1 - smooth01((hb - 0.9) / 0.9) : 0;
    v.aHornHalf = approach(v.aHornHalf, breath, 18, dt);
    v.aHornFull = approach(v.aHornFull, ar && (ar.state === 'blowing' || ar.state === 'attack') ? 1 : 0, 25, dt);
    // il risucchio: la gola si gonfia per tutto il tempo che prende fiato; quando soffia si sgonfia di colpo, se
    // l'hai spenta in tempo si sgonfia piano, in un sospiro, mentre aspetta al buio
    if (ar?.state === 'inhaling') v.aFiato = Math.max(v.aFiato, ar.breath);
    else v.aFiato = Math.max(0, v.aFiato - dt / (ar?.state === 'blowing' || ar?.state === 'attack' ? 0.3 : 1.5));

    // Lampy: affiora sulla lenza dopo il terzo colpo e torna giù quando molla; mentre ti guarda apre e chiude piano la
    // ventosa (un giro ogni 2,6 s); se l'hai agganciata la spalanca e risale un poco la lenza verso la canna
    const lp = sim.lampy;
    v.lRise = approach(v.lRise, lp ? (lp.state === 'attack' ? 1 : lp.rise) : 0, 14, dt);
    v.lMouthT = lp?.visible ? v.lMouthT + dt : 0;
    const lHooked = lp?.state === 'climbing' || lp?.state === 'attack';
    v.lMouth = approach(v.lMouth, lHooked ? 1 : lp?.visible ? -Math.sin((v.lMouthT * 2 * Math.PI) / 2.6) : 0, lHooked ? 10 : 5, dt);
    v.lClimb = lp?.state === 'climbing' ? Math.min(1, lp.stateTime / (sim.cfg.lampy?.climb ?? 1)) : lp?.state === 'attack' ? 1 : 0;

    // Fangy: sale dall'acqua accanto alla barca e ci torna. A ogni rumore gira la testa di scatto verso prua (dove fai
    // rumore), la tiene lì un poco e torna a fissarti; mentre ascolta in silenzio ogni tanto la volta verso poppa,
    // come per sentire meglio. Le lucine respirano più in fretta a ogni rumore che ha sentito, e al rumore si
    // accendono tutte insieme
    const fg = sim.fangy;
    v.fRise = approach(v.fRise, fg ? (fg.state === 'attack' ? 1 : fg.rise) : 0, 14, dt);
    // la fila di lucine sott'acqua: segue l'arrivo e, se lui torna indietro (canta la Madre), sfuma invece di sparire
    if (fg?.state === 'approaching') v.fApp = fg.approach;
    v.fRow = approach(v.fRow, fg?.state === 'approaching' ? 1 : 0, 3, dt);
    if (fg?.state === 'attack') {
      // ti è addosso: la testa ti guarda (come nel jumpscare)
      v.fHead = 0;
      v.fHeadT = 99;
    } else if (fg && fg.listening) {
      v.fHeadT -= dt;
      if (v.fHeadT <= 0) {
        if (v.fHead !== 0) {
          v.fHead = 0;
          v.fHeadT = 1.8 + Math.random() * 2.6;
        } else if (fg.state === 'listening') {
          v.fHead = -1;
          v.fHeadT = 0.7 + Math.random() * 0.7;
        } else v.fHeadT = 0.6;
      }
    } else {
      v.fHead = 0;
      v.fHeadT = 1.4;
    }
    // la testa gira di scatto (fra due immagini una dissolvenza lenta mostrerebbe due teste)
    v.fBow = toward(v.fBow, v.fHead === 1 ? 1 : 0, 0.07, 0.1, dt);
    v.fStern = toward(v.fStern, v.fHead === -1 ? 1 : 0, 0.07, 0.1, dt);
    v.fFlash = Math.max(0, v.fFlash - dt / 1.1);
    v.fBreath += dt / FANGY_BREATH[Math.min(FANGY_BREATH.length - 1, fg?.heard ?? 0)]!;

    // Robin: sale dal mare sul bordo mentre arriva e ruba; scacciato scivola giù in mare. La luce in faccia cresce
    // mentre lo scacci, e se ne va ancora abbagliato
    const rb = sim.robin;
    const robinT = rb && (rb.present || rb.state === 'attack') ? 1 : 0;
    v.robin = toward(v.robin, robinT, 1.2, 0.7, dt);
    const fearT = rb ? (rb.state === 'fleeing' ? 1 : rb.present ? rb.fear : 0) : 0;
    v.robinFear = approach(v.robinFear, fearT, 10, dt);
    v.robinBlink = this.blinker('robin', dt, [2.5, 6]);

    // Gulpy alla prua muove piano la mascella mentre pretende; quando mangia mastica in fretta
    const eating = g.state === 'eating';
    v.gJawPhase += dt * ((2 * Math.PI) / (eating ? 0.8 : 5.5));
    v.gJawAmp = approach(v.gJawAmp, g.state === 'demanding' || eating ? 1 : 0, 3, dt);
    v.gJaw = v.gJawAmp * Math.sin(v.gJawPhase);
    // Molly sbatte gli occhi: il primo e poi, storto, il secondo
    [v.mBlink1, v.mBlink2] = this.blinkPair('molly', dt, [2.8, 6.5], 0.11);
    // Hatch chiude la bocca a ogni numero della conta (si chiude in fretta, si riapre più piano)
    v.hMouthT += dt;
    const ht = v.hMouthT;
    v.hMouth = ht < 0.12 ? smooth01(ht / 0.12) : ht < 0.2 ? 1 : ht < 0.5 ? 1 - smooth01((ht - 0.2) / 0.3) : 0;

    this.updateBattery(dt);
    this.updateRod(dt);

    // la lenza: il lancio, il tonfo, i cerchi sull'acqua
    if (this.castT >= 0) this.castT = this.castT > 4 ? -1 : this.castT + dt;
    if (this.plopT >= 0) this.plopT = this.plopT > 4 ? -1 : this.plopT + dt;
    this.lineSway *= Math.exp(-0.9 * dt);
    for (const r of this.rings) r.t += dt;
    this.rings = this.rings.filter((r) => r.t < 2.6);
    const fp = sim.fishing.phase;
    if (sim.fishing.lineOut) this.lastFloat = this.floatPos();
    if (this.retrieve) {
      this.retrieve.t += dt;
      if (fp !== 'rebait' && fp !== 'landing') this.retrieve = null;
    }

    // telone: la tela scende sulla testa
    v.tarp = sim.hideAmount;
    const searching = h.state === 'searching' || (h.state === 'leaving' && sim.hidden);
    v.toy = approach(v.toy, searching ? 1 : h.state === 'boarding' && sim.hide !== 'out' ? 0.4 : 0, 3, dt);
    v.toyX = approach(v.toyX, h.lureX, 4, dt);

    // dondolio di Molly (più forte se arrabbiata)
    v.rock = approach(v.rock, sim.rocking * (this.d.options.reduceFlash ? 0.5 : 1), 2, dt);
    st.view.rockBoost = v.rock;

    // alba alle 6: il cielo si schiarisce, il mare si calma (nel finale della notte 6 il sole sorge dopo, quando lei se
    // n'è andata)
    if (sim.outcome.kind === 'won' && !this.cine) v.dawn = Math.min(1, v.dawn + dt / 5);
    // la Madre ti prende (la quota mancata, la canzone finita, o ti sei mosso): il buio, più in fretta se ti ha preso da sotto
    if (sim.outcome.kind === 'dead' && sim.outcome.killer === 'mother') {
      const moved = sim.outcome.cause === 'moved';
      if (!moved || (this.js?.t ?? 0) > 0.55) v.dark = Math.min(1, v.dark + dt / (moved ? 0.9 : 4));
    }
    this.updateMother(dt);
    st.view.swell = (1 - 0.7 * v.dawn) * (1 - 0.92 * v.mCalm);

    // jumpscare
    if (this.js) {
      this.js.t += dt;
      const t = this.js.t;
      const view = st.view;
      view.targetYaw = this.js.yaw;
      view.hfov = approach(view.hfov, 34, 6, dt);
      // senza i fotogrammi renderizzati, il jumpscare zooma sulla posa della creatura
      if (!this.d.assets.jumpscares[this.js.killer]) {
        if (this.js.killer === 'gulpy') v.gPret = 1;
        else if (this.js.killer === 'hatch') v.hRise = 1;
        else if (this.js.killer === 'robin') v.robin = 1;
        else if (this.js.killer === 'archie') v.aRise = 1;
        else if (this.js.killer === 'lampy') v.lRise = 1;
        else if (this.js.killer === 'fangy') v.fRise = 1;
        else if (this.js.killer === 'mother') {
          // (finché non c'è il suo render) la barca sbalzata in su, lo sguardo che cade verso l'acqua, poi il buio
          view.hfov = 90;
          view.pitch = approach(view.pitch, -55, 2.2, dt);
          if (!this.d.options.reduceFlash) view.shake = Math.max(view.shake, 2.4 * Math.exp(-t * 1.5));
        }
        // il Foxy non ha ancora una posa: buio e scossa (provvisorio)
        else if (this.js.killer === 'foxy') v.dark = Math.min(1, t * 4);
        else if (this.sim.molly.side === 'right') v.mR = 1;
        else v.mL = 1;
      }
      if (t < 0.12 && !this.d.options.reduceFlash) st.lampDip = 1;
    }
    if (this.cine) this.playCinematic(dt);
    st.update(dt);
  }

  /**
   * La Madre (notte 6). Mentre si avvicina (10 s): a 3,5 s il mare si ferma (come nel suono dell'avvicinamento), a 6 e a
   * 9 s la lampara trema, da 8 s sale la sua ninna nanna. Mentre passa sotto, la barca si solleva piano sul suo dorso e
   * s'inclina da sinistra a destra; quando se n'è andata il mare torna. Nei finali comanda la cinematica.
   */
  private updateMother(dt: number): void {
    const mo = this.sim.mother;
    const v = this.v;
    const st = this.d.stage;
    if (!mo) return;
    const t0 = this.motherPrevT;
    const t = mo.stateTime;
    this.motherPrevT = t;
    // i momenti dell'avviso, sul suono: il mare si calma a 3,5 s, la luce trema a 6 e 9 s, la ninna nanna a 8 s
    const k = this.motherSkip;
    const crossed = (x: number) => mo.state === 'approaching' && t0 < x - k && t >= x - k && t - t0 < 1;
    if (crossed(6) || crossed(9)) st.lampDip = Math.max(st.lampDip, this.d.options.reduceFlash ? 0.4 : 0.75);
    if (crossed(8) && !this.motherSong && !this.finished) {
      this.motherSong = this.d.sfx.motherLullaby();
      this.motherSong?.setGain(1, 3);
      if (this.d.options.captions) this.hud.caption(this.S.captions.motherLullaby);
    }
    const calm =
      (mo.state === 'approaching' && t >= 3.5 - k) || mo.state === 'passing' || mo.state === 'leaving' || mo.state === 'attack';
    v.mCalm = approach(v.mCalm, calm ? 1 : 0, calm ? 1.4 : 0.25, dt);
    // la barca sul suo dorso: su piano mentre passa, di colpo se ti prende
    const liftT = mo.state === 'passing' ? 1 : mo.state === 'attack' ? 3 : 0;
    v.mLift = approach(v.mLift, liftT, mo.state === 'attack' ? 6 : liftT > 0 ? 0.35 : 0.5, dt);
    const p = mo.state === 'passing' ? Math.min(1, t / mo.passTime) : mo.state === 'leaving' ? 1 : 0.5;
    if (!this.cine) {
      st.view.liftPitch = 1.6 * v.mLift;
      st.view.liftRoll = -2.4 * v.mLift * Math.cos(Math.PI * p);
    }
  }

  /** Comincia una cinematica (un finale): niente più comandi, l'interfaccia lascia il posto alle bande nere. */
  private startCinematic(s: CinematicScript): void {
    this.cine = { s, t: 0, voices: [] };
    this.binoUp = false;
    this.bino = 0;
    if (this.sonarOpen) this.toggleSonar(false);
    this.stopReel();
    this.hud.cinema(true);
  }

  /** La cinematica salta alla fine (Esc): le sue voci si spengono, poi i risultati. */
  private skipCinematic(): void {
    const c = this.cine;
    if (!c) return;
    for (const v of c.voices) v.stop(0.25);
    c.voices = [];
    this.radio?.utt?.stop();
    this.radio?.hiss?.stop(0.2);
    this.radio = null;
    c.t = c.s.length;
    this.cineBlack = 1;
    this.endTimer = Math.min(this.endTimer, 0.3);
  }

  /** Un passo della cinematica: lo sguardo, la luce, le creature, la barca, i suoni, le scritte e il buio. */
  private playCinematic(dt: number): void {
    const c = this.cine!;
    const s = c.s;
    const t0 = c.t;
    const t = Math.min(s.length, (c.t += dt));
    const st = this.d.stage;
    const view = st.view;
    const v = this.v;
    const [yaw, pitch, hfov] = sample(s.view, t);
    view.yaw = view.targetYaw = yaw;
    view.pitch = pitch;
    view.hfov = hfov;
    view.swayYaw = view.swayPitch = view.steady = 0;
    if (s.dawn) v.dawn = sample(s.dawn, t);
    if (s.lamp) st.lampTarget = sample(s.lamp, t);
    const cr = s.creatures ?? {};
    if (cr.gulpy) {
      v.gRise = sample(cr.gulpy, t);
      v.gSale = v.gRise > 0.001 ? 1 : 0;
    }
    if (cr.archie) v.aRise = sample(cr.archie, t);
    if (cr.lampy) v.lRise = sample(cr.lampy, t);
    if (cr.fangy) v.fRise = sample(cr.fangy, t);
    if (cr.hatch) v.hRise = sample(cr.hatch, t);
    if (cr.madre) v.mdRise = sample(cr.madre, t);
    const soft = this.d.options.reduceFlash ? 0.5 : 1;
    if (s.tilt) {
      const [roll, pt] = sample(s.tilt, t);
      view.liftRoll = roll * soft;
      view.liftPitch = pt * soft;
    }
    this.cineBlack = s.black ? sample(s.black, t) : 0;
    for (const x of between(s.sounds, t0, t)) {
      const vo = this.d.audio.play(x.id, { gain: x.gain ?? 1, loop: x.loop, fadeIn: x.fadeIn });
      if (vo) c.voices.push(vo);
    }
    for (const x of between(s.events, t0, t)) {
      if (x.e === 'emptyBucket') this.cineEmptyBucket = true;
      else if (x.e === 'shake') view.shake = Math.max(view.shake, 0.9 * soft);
      else if (x.e === 'lampOff') st.lampTarget = 0;
      else if (x.e === 'dip') st.lampDip = this.d.options.reduceFlash ? 0.6 : 1;
      else if (x.e === 'radio') this.radio = { t: -0.8, next: 0, utt: null, hiss: null, lines: RADIO_FINALE[this.d.lang] };
      else if (x.e === 'quiet') {
        // il taglio su un altro posto: il mare e i rumori della notte si spengono di colpo
        for (const k of Object.keys(this.loops)) {
          this.loops[k]?.stop(0.04);
          this.loops[k] = null;
        }
        this.quiet = true;
      }
    }
    this.hud.cineText(textAt(s, t, this.d.lang));
  }

  /** Batteria (dalla notte 2): l'ago del voltmetro e la lampara che trema quando è quasi scarica. */
  private updateBattery(dt: number): void {
    const sim = this.sim;
    const b = sim.cfg.battery;
    const st = this.d.stage;
    if (!b) return;
    // l'ago: nel rosso proprio quando la carica scende sotto la soglia bassa; la lampara alta lo fa calare un
    // poco (la batteria sotto sforzo), a batteria morta batte sul fermo
    const c = sim.battery;
    const rest = c >= b.low ? 11.2 + 3.4 * ((c - b.low) / (1 - b.low)) : 10.1 + 1.1 * (c / b.low);
    const load = [0, 0.06, 0.2][sim.lamp]! + (this.sonarOpen ? 0.05 : 0);
    const target = sim.blackout ? 9.5 : rest - load;
    const n = this.needle;
    n.vel += ((target - n.v) * 38 - n.vel * 8) * dt;
    n.v += n.vel * dt;
    if (n.v < 9.85) {
      n.v = 9.85;
      n.vel = -n.vel * 0.3;
    }
    // la luce del quadrante: piena finché la batteria regge, cala quando è quasi scarica e ne segue i cali,
    // si spegne con lei
    const glowT = sim.blackout ? 0 : (c < b.low ? 0.55 + 0.45 * (c / b.low) : 1) * (1 - 0.85 * st.lampDip);
    this.gaugeGlow = approach(this.gaugeGlow, glowT, sim.blackout ? 14 : 20, dt);
    // quasi scarica: la reticella trema, e ogni tanto la luce cala di colpo con uno sfrigolio
    const sick = !sim.blackout && sim.lamp > 0 && c < b.low ? 0.4 + 0.6 * (1 - c / b.low) : 0;
    st.lampSick = approach(st.lampSick, sick, 2, dt);
    if (sick > 0 && !this.finished) {
      this.flickerTimer -= dt;
      if (this.flickerTimer <= 0) {
        st.lampDip = Math.max(st.lampDip, 0.3 + 0.5 * Math.random() * sick);
        this.d.audio.play('lamp_flicker', { pos: LAMP_AT, gain: 0.25 + 0.4 * sick, rate: 0.9 + Math.random() * 0.2 });
        this.flickerTimer = (3.2 - 2.4 * sick) * (0.5 + Math.random());
      }
    }
  }

  /** L'ago in radianti (0 = in alto, positivo a destra), con un filo di tremolio. */
  private needleAngle(): number {
    const t = this.d.stage.time;
    const jitter = (0.012 + 0.05 * this.d.stage.lampSick) * noise1(t * 11, 7);
    const volts = this.needle.v + (this.sim.blackout ? 0 : jitter);
    return (-50 + (100 * (volts - 10)) / 5) * D2R;
  }

  /** Il cuore, il respiro e la tensione (paura.ts), e i falsi allarmi. */
  private updateFear(dt: number): void {
    const sim = this.sim;
    const quiet = !!this.js || !!this.cine || this.finished;
    const danger = this.dangerNow();
    this.calm = danger > 0.05 ? 0 : this.calm + dt;
    this.updateFalseAlarms(dt, quiet);
    // trattieni il fiato quando devi stare immobile: la Madre che passa sotto, Hatch che cerca
    const hold = sim.mother?.state === 'passing' || sim.hatch.state === 'searching';
    this.paura.update(dt, Math.min(1, Math.max(danger, this.falso.boost)), { hold, hidden: sim.hide !== 'out', quiet });
  }

  /**
   * Il pericolo di adesso (0..1) dagli stati dei mostri: quanto batte il cuore, quanto è corto il respiro, quanta
   * tensione nella musica. Al massimo (sopra PEAK) la musica tace: la Madre che passa, Hatch che cerca, il Foxy che
   * corre verso la barca. Numeri da approvare.
   */
  private dangerNow(): number {
    const s = this.sim;
    let d = 0;
    const up = (x: number) => {
      if (x > d) d = x;
    };
    const g = s.gulpy;
    if (g.state === 'rising') up(0.25);
    else if (g.state === 'climbing') up(0.4);
    else if (g.state === 'demanding') up(0.55 + 0.35 * g.phase);
    const mo = s.molly;
    if (mo.state === 'knocking') up(0.35);
    else if (mo.state === 'peeking') up(0.45 + 0.4 * mo.rocking);
    else if (mo.state === 'tantrum') up(0.8 + 0.12 * mo.rocking);
    const h = s.hatch;
    // se sei già sotto il telone mentre conta, un po' meno
    if (h.state === 'counting') up((0.45 + 0.45 * h.countProgress) * (s.hide === 'out' ? 1 : 0.8));
    else if (h.state === 'boarding') up(0.9);
    else if (h.state === 'searching') up(0.95);
    else if (h.state === 'leaving') up(0.3);
    const r = s.robin;
    if (r?.state === 'climbing') up(0.35);
    else if (r?.state === 'stealing') up(s.fish <= 1 ? 0.75 : 0.55);
    const a = s.archie;
    if (a?.state === 'rising') up(0.3);
    else if (a?.state === 'inhaling') up(0.55);
    else if (a?.state === 'waiting') up(0.65);
    else if (a?.state === 'blowing') up(0.9);
    const l = s.lampy;
    if (l?.state === 'ringing') up(0.45);
    else if (l?.state === 'surfacing') up(0.6);
    else if (l?.state === 'staring') up(0.75);
    else if (l?.state === 'climbing') up(0.9);
    const f = s.fangy;
    if (f?.state === 'approaching') up(0.4);
    else if (f?.state === 'rising') up(0.55);
    else if (f?.state === 'listening') up(0.72 + 0.08 * f.heard);
    const m = s.mother;
    if (m?.state === 'approaching') up(0.7);
    else if (m?.state === 'passing') up(1);
    else if (m?.state === 'leaving') up(0.4);
    const fx = s.foxy;
    if (fx?.state === 'leaning') up(0.3);
    else if (fx?.state === 'gone') up(0.96);
    // a batteria morta, mentre la ninna nanna va avanti
    if (s.blackout) up(0.5 + 0.4 * (1 - s.lullaby / (s.cfg.battery?.lullaby ?? 60)));
    return d;
  }

  /**
   * I falsi allarmi (più paura, idea approvata il 12 ottobre; da approvare i dettagli): rari e innocui, solo quando
   * è tutto calmo da almeno 20 s. I colpi sullo scafo di Molly, da un lato, senza nessuno; o un tonfo in acqua
   * dietro di te. Il cuore sussulta (il pericolo sale per un momento e torna giù piano).
   */
  private updateFalseAlarms(dt: number, quiet: boolean): void {
    const f = this.falso;
    f.boost = Math.max(0, f.boost - dt * 0.1);
    if (quiet || f.left <= 0 || this.sim.time < f.next) return;
    if (this.calm < 20 || this.sim.hide !== 'out' || this.sonarOpen || this.bino > 0.1) {
      f.next = this.sim.time + 6;
      return;
    }
    const cap = (t: string) => this.d.options.captions && this.hud.caption(t);
    if (Math.random() < 0.6) {
      const right = Math.random() < 0.5;
      this.d.sfx.knock(dirPos(right ? YAW.mollyRight : YAW.mollyLeft, 1.4, -30));
      cap(this.S.captions.knock);
    } else {
      this.d.audio.play('splash_small', { pos: dirPos(180 + (Math.random() * 80 - 40), 7, -6), gain: 0.9 });
      cap(this.S.captions.falseSplash);
    }
    f.boost = 0.45;
    f.left--;
    f.next = this.sim.time + HOUR_SECONDS * (1.2 + 1.3 * Math.random());
  }

  /** Le creature vive: quanto è fuori ognuna, se la stai guardando, lo scatto e le gocce (vivi.ts). */
  private updateVivi(dt: number): void {
    const v = this.v;
    const presence: Record<string, number> = {
      gulpy: Math.max(v.gSale > 0.002 ? v.gSale * ease(v.gRise) : 0, v.gPret),
      mollyR: v.mR,
      mollyL: v.mL,
      hatch: ease(v.hRise),
      robin: v.robin,
      archie: ease(v.aRise),
      lampy: ease(v.lRise),
      fangy: ease(v.fRise),
      madre: ease(v.mdRise),
    };
    const view = this.d.stage.view;
    const looked = (id: string) => {
      const y = this.viviYaw[id];
      return y !== undefined && Math.abs(angleDiff(view.yaw, y)) < 18 && this.sim.hide === 'out' && this.bino < 0.5;
    };
    const at = (id: string, dist: number) => dirPos(this.viviYaw[id] ?? 0, dist, -12);
    this.vivi.update(dt, presence, looked, !!this.js || !!this.cine || this.finished, (id) => this.d.sfx.twitch(at(id, 2.6)), (id) => this.d.sfx.drip(at(id, 2.4), 0.35 + 0.3 * Math.random()));
  }

  private layerDraws(): (string | LayerDraw)[] {
    const v = this.v;
    const man = this.d.stage.man;
    const sim = this.sim;
    const layers: (string | LayerDraw)[] = ['world'];
    const has = (k: string) => !!man.layers[k];
    // creature nel mondo: emergono dal pelo dell'acqua (lo strato scende e si taglia al galleggiamento)
    const rise = (key: string, opacity: number, r: number, masks?: { key: string; k: number }[]): LayerDraw | null => {
      const info = this.baseOf(key);
      if (!info || !has(key) || opacity < 0.002) return null;
      const pelo = info.pelo ? { x0: info.rect[0], x1: info.rect[2], rows: info.pelo } : undefined;
      return { key, opacity, shift: [0, this.wavePx(key, r)], clipY: info.rect[3] - 3, pelo, masks };
    };
    // la Madre (notte 6, il finale A): emerge accanto alla barca a sinistra, dietro a tutti
    const md = rise(POSE.madre, v.mdRise > 0.002 ? 1 : 0, ease(v.mdRise));
    if (md) layers.push(md);
    const gs = rise(POSE.gulpySale, v.gSale, v.gRise);
    if (gs) layers.push(gs);
    // Hatch che conta, e la bocca che si chiude a ogni numero: prima la toppa mezza chiusa, poi sopra quella chiusa
    const hr = ease(v.hRise);
    const hm = v.hMouth;
    const kHalf = has(POSE.hatchMouthHalf) ? (hm < 0.5 ? hm / 0.5 : 1) : 0;
    const kShut = has(POSE.hatchMouthShut) ? (hm < 0.5 ? 0 : (hm - 0.5) / 0.5) : 0;
    const hc = rise(POSE.hatchConta, v.hRise > 0.002 ? 1 : 0, hr, [{ key: POSE.hatchMouthHalf, k: kHalf }, { key: POSE.hatchMouthShut, k: kShut }]);
    if (hc) {
      layers.push(hc);
      const half = rise(POSE.hatchMouthHalf, kHalf, hr, [{ key: POSE.hatchMouthShut, k: kShut }]);
      if (half) layers.push(half);
      const shut = rise(POSE.hatchMouthShut, kShut, hr);
      if (shut) layers.push(shut);
    }
    // Fangy accanto alla barca (notte 5), e le toppe della testa girata: verso prua quando ti sente, verso poppa quando
    // ascolta
    if (v.fRise > 0.002) {
      const fr = ease(v.fRise);
      const kBow = has(POSE.fangyBow) ? v.fBow : 0;
      const kStern = has(POSE.fangyStern) ? v.fStern : 0;
      const fb = rise(POSE.fangy, 1, fr, [{ key: POSE.fangyBow, k: kBow }, { key: POSE.fangyStern, k: kStern }]);
      if (fb) {
        layers.push(fb);
        const stern = rise(POSE.fangyStern, kStern, fr, [{ key: POSE.fangyBow, k: kBow }]);
        if (stern) layers.push(stern);
        const bow = rise(POSE.fangyBow, kBow, fr);
        if (bow) layers.push(bow);
      }
    }
    // Archie davanti alla prua, e le toppe della trombetta (a metà nel respiro, tutta quando soffia)
    const arr = ease(v.aRise);
    const kHorn = has(POSE.archieHornHalf) ? v.aHornHalf : 0;
    const kFull = has(POSE.archieHornFull) ? v.aHornFull : 0;
    const ac = rise(POSE.archie, v.aRise > 0.002 ? 1 : 0, arr, [{ key: POSE.archieHornHalf, k: kHorn }, { key: POSE.archieHornFull, k: kFull }]);
    if (ac) {
      layers.push(ac);
      const half = rise(POSE.archieHornHalf, kHorn * (1 - kFull), arr, [{ key: POSE.archieHornFull, k: kFull }]);
      if (half) layers.push(half);
      const full = rise(POSE.archieHornFull, kFull, arr);
      if (full) layers.push(full);
      const fiato = has(POSE.archieBreath) ? rise(POSE.archieBreath, smooth01(v.aFiato) * (1 - kFull), arr) : null;
      if (fiato) layers.push(fiato);
    }
    // Lampy sulla lenza (notte 4): affiora tagliata al pelo dell'acqua; le toppe della ventosa, chiusa e spalancata,
    // sopra la posa (che la tiene a riposo); agganciata, risale un poco la lenza verso la canna
    const lr = ease(v.lRise);
    if (v.lRise > 0.002) {
      const kOpen = has(POSE.lampyOpen) ? Math.max(0, v.lMouth) : 0;
      const kShut = has(POSE.lampyShut) ? Math.max(0, -v.lMouth) : 0;
      const climb = this.lampyClimbPx(v.lClimb);
      const lay = (key: string, op: number, masks?: { key: string; k: number }[]): LayerDraw | null => {
        const d = rise(key, op, lr, masks);
        if (!d) return null;
        d.shift = [d.shift![0] + climb[0], d.shift![1] + climb[1]];
        return d;
      };
      const base = lay(POSE.lampy, 1, [{ key: POSE.lampyShut, k: kShut }, { key: POSE.lampyOpen, k: kOpen }]);
      if (base) {
        layers.push(base);
        const shut = lay(POSE.lampyShut, kShut);
        if (shut) layers.push(shut);
        const open = lay(POSE.lampyOpen, kOpen);
        if (open) layers.push(open);
      }
    }
    // creature sulla barca: salgono e scendono dietro il bordo. Mentre si muovono, la parte che nella posa si
    // vedeva contro il mare passa sotto la barca, che la copre; le mani sul bordo restano sopra e mollano la
    // presa per prime
    const aboard: LayerDraw[] = [];
    for (const a of this.aboard()) {
      const k = a.opacity ?? 1;
      if (!has(a.key) || a.p < 0.002 || k < 0.002) continue;
      const d = this.sinkPx(a.key, a.p);
      const shift: [number, number] = [a.out * d + (a.recoil?.[0] ?? 0), d + (a.recoil?.[1] ?? 0)];
      const masks = a.masks;
      if (a.p >= 0.999) {
        aboard.push({ key: a.key, shift, opacity: k, light: a.light, masks });
        continue;
      }
      layers.push({ key: a.key, shift, part: 'back', opacity: k, light: a.light, masks });
      const hands = smooth01((a.p - a.hands) / (1 - a.hands));
      const handsShift: [number, number] = a.handsStay ? [a.recoil?.[0] ?? 0, a.recoil?.[1] ?? 0] : shift;
      if (hands > 0.002) aboard.push({ key: a.key, shift: handsShift, part: 'front', opacity: hands * k, light: a.light, masks });
    }
    layers.push('boat');
    if (sim.cfg.battery && has('battery')) {
      layers.push('battery');
      // il voltmetro retroilluminato (lo stesso strato col quadrante acceso, dissolto sopra)
      if (has('battery_lit') && this.gaugeGlow > 0.002) layers.push({ key: 'battery_lit', opacity: this.gaugeGlow * GAUGE_LIGHT });
    }
    // la canna: il manico e il mulinello sono uno strato, il fusto lo disegna il motore (render: tubes)
    layers.push(has('rod_base') ? 'rod_base' : this.rodKey());
    const n = sim.fish;
    if (n > 0 && !this.cineEmptyBucket) layers.push(n <= 3 ? 'fish2' : n <= 6 ? 'fish5' : 'fish9');
    layers.push(...aboard);
    // le creature vive: ogni posa e le sue toppe prendono il respiro e lo scatto della creatura
    const pano = man.pano;
    for (const d of layers) {
      if (typeof d === 'string') continue;
      const id = VIVO_DI[d.key];
      const base = id ? this.baseOf(d.key) : undefined;
      if (!id || !base) continue;
      d.warp = this.vivi.warp(id, base);
      this.viviYaw[id] = base.yaw + (((base.rect[0] + base.rect[2]) / 2 / pano.width) - 0.5) * 360;
    }
    return layers;
  }

  /** Le creature sulla barca: salgono e scendono dietro il bordo, le mani sul bordo mollano la presa per prime. */
  private aboard(): Aboard[] {
    const v = this.v;
    const L = this.d.stage.man.layers;
    // Gulpy: la mascella va avanti e indietro fra la toppa più aperta e quella più chiusa, passando per la posa
    const kOpen = L[POSE.gulpyJawOpen] ? smooth01(Math.max(0, v.gJaw)) : 0;
    const kShut = L[POSE.gulpyJawShut] ? smooth01(Math.max(0, -v.gJaw)) : 0;
    const gulpy = { p: v.gPret, hands: 0.8, out: 0, handsStay: true };
    const out: Aboard[] = [
      { key: POSE.gulpyPretende, ...gulpy, masks: [{ key: POSE.gulpyJawOpen, k: kOpen }, { key: POSE.gulpyJawShut, k: kShut }] },
      { key: POSE.gulpyJawOpen, ...gulpy, opacity: kOpen },
      { key: POSE.gulpyJawShut, ...gulpy, opacity: kShut },
    ];
    // Molly: gli occhi che sbattono, sui due lati
    for (const [side, key, p] of [['right', POSE.mollyRight, v.mR], ['left', POSE.mollyLeft, v.mL]] as const) {
      const molly = { p, hands: 0.8, out: 0, handsStay: true };
      out.push({ key, ...molly });
      out.push({ key: MOLLY_EYES[side][0], ...molly, opacity: v.mBlink1 });
      out.push({ key: MOLLY_EYES[side][1], ...molly, opacity: v.mBlink2 });
    }
    // Robin è steso sul bordo: testa, braccio e zampe stanno sopra la barca. Il corpo sopra il mare sale e scende
    // di lato, dal mare; quello che sta sopra la barca compare e svanisce in fretta sul posto (scivolando passerebbe
    // attraverso il legno). Nella luce piena trema e si ritrae un poco, la faccia si accende di luce calda (la
    // lanterna, dalla parte del pescatore) e strizza gli occhi
    const f = v.robinFear;
    const t = this.d.stage.time;
    const recoil: [number, number] = [-(9 + 3 * noise1(t * 21, 5)) * f, (12 + 3 * noise1(t * 19, 6)) * f];
    const light: [number, number, number] = [1, 1, 1 + 2.2 * f];
    const squint = smooth01(f * 1.6);
    out.push({ key: POSE.robin, p: v.robin, hands: 0.75, out: -0.45, handsStay: true, recoil, light });
    out.push({ key: POSE.robinSquint, p: v.robin, hands: 0.75, out: -0.45, handsStay: true, recoil, light, opacity: squint });
    // ogni tanto sbatte gli occhi (non quando li strizza nella luce)
    out.push({ key: POSE.robinBlink, p: v.robin, hands: 0.75, out: -0.45, handsStay: true, recoil, light, opacity: v.robinBlink * (1 - squint) });
    return out;
  }

  /** Di quanto (pixel del panorama) è scesa dietro il bordo una creatura sulla barca: p = 1 in posa, 0 sparita. */
  private sinkPx(key: string, p: number): number {
    const info = this.baseOf(key);
    return info ? (1 - ease(p)) * (info.rect[3] - info.rect[1] + 8) : 0;
  }

  /**
   * Vero se una direzione cade dietro la sagoma di una creatura del mondo (sotto la cima, manifest → cima), con lo strato
   * sceso di `drop` pixel: per le luci lontane del paesaggio, che se no si vedrebbero attraverso la Madre.
   */
  private behind(key: string, drop: number, dir: Vec3): boolean {
    const info = this.d.stage.man.layers[key];
    const c = info?.cima;
    if (!info || !c || c.length < 2) return false;
    const pano = this.d.stage.man.pano;
    const yaw = Math.atan2(dir[0], dir[1]) / D2R;
    const el = Math.atan2(dir[2], Math.hypot(dir[0], dir[1])) / D2R;
    const col = (0.5 + ((((yaw - info.yaw + 540) % 360) - 180) / 360)) * pano.width;
    const [x0, , x1] = info.rect;
    if (col < x0 || col > x1) return false;
    const f = ((col - x0) / (x1 - x0)) * (c.length - 1);
    const i = Math.min(c.length - 2, Math.floor(f));
    const a = c[i], b = c[i + 1];
    if (a == null || b == null) return false;
    const row = a + (b - a) * (f - i) + drop;
    return el < pano.latMax - (row * (pano.latMax - pano.latMin)) / pano.height;
  }

  /** Lo strato della posa (per una toppa, quello su cui va): la toppa sale e scende insieme a lui. */
  private baseOf(key: string): LayerInfo | undefined {
    const L = this.d.stage.man.layers;
    const info = L[key];
    return info?.base ? L[info.base] ?? info : info;
  }

  /** Due occhi che sbattono, il secondo in ritardo di `delay` secondi: [primo, secondo], ognuno da 0 a 1. */
  private blinkPair(id: string, dt: number, every: [number, number], delay: number, len = 0.17): [number, number] {
    const pick = () => every[0] + Math.random() * (every[1] - every[0]);
    const b = (this.blinks[id] ??= { wait: pick(), t: -1 });
    if (b.t >= 0) {
      b.t += dt;
      if (b.t > len + delay) {
        b.t = -1;
        b.wait = pick();
      }
    } else if ((b.wait -= dt) <= 0) {
      b.t = 0;
    }
    const k = (x: number) => (x >= 0 && x <= len ? Math.min(1, 1.8 * Math.sin((Math.PI * x) / len)) : 0);
    return b.t >= 0 ? [k(b.t), k(b.t - delay)] : [0, 0];
  }

  /** Battito di ciglia: chiuso (fino a 1) per un attimo ogni tanto, a intervalli a caso fra every[0] e every[1] s. */
  private blinker(id: string, dt: number, every: [number, number], len = 0.17): number {
    const pick = () => every[0] + Math.random() * (every[1] - every[0]);
    const b = (this.blinks[id] ??= { wait: pick(), t: 0 });
    if (b.t > 0) {
      b.t = Math.max(0, b.t - dt);
      if (b.t === 0) b.wait = pick();
    } else if ((b.wait -= dt) <= 0) {
      b.t = len;
    }
    return b.t > 0 ? Math.min(1, 1.8 * Math.sin(Math.PI * (1 - b.t / len))) : 0;
  }

  /** Agganciata, Lampy risale un poco la lenza verso la punta della canna: lo spostamento del suo strato (pixel). */
  private lampyClimbPx(c: number): [number, number] {
    if (c <= 0) return [0, 0];
    const pano = this.d.stage.man.pano;
    const px = pano.height / (pano.latMax - pano.latMin);
    const tip = this.d.stage.man.points.rodTip;
    const yaw = (p: Vec3) => Math.atan2(p[0], p[1]) / D2R;
    const el = (p: Vec3) => Math.atan2(p[2], Math.hypot(p[0], p[1])) / D2R;
    const k = 0.35 * smooth01(c);
    return [(yaw(tip) - yaw(LAMPY_MOUTH)) * px * k, -(el(tip) - el(LAMPY_MOUTH)) * px * k];
  }

  /** Il suggerimento durante un'abboccata: nelle notti di Lampy si aspetta il secondo colpo del campanellino, poi si
   *  dice di ferrare se è un pesce e di non ferrare se è lei (quello che sente chi ascolta il ritmo). */
  /** Il suggerimento dell'abboccata: «ferra» solo col tutorial (`tut`); la regola di Lampy (tre colpi uguali) sempre. */
  private biteHint(tut: boolean): string {
    const sim = this.sim;
    const l = sim.cfg.lampy;
    if (!l) return tut ? this.hintText('hook') : '';
    if (sim.fishing.fake) return sim.lampy?.holding && sim.lampy.beats >= 2 ? this.hintText('lampy') : '';
    return tut && sim.time - this.biteAt >= LAMPY_FIRST_BEAT + l.beat ? this.hintText('hook') : '';
  }

  /** Di quanto è sotto il pelo dell'acqua una creatura in mare (r = 1 tutta fuori): a r = 0 la cima è scesa fino
   *  al pelo dell'acqua più basso; segue anche l'onda, di un soffio. */
  private wavePx(key: string, r: number): number {
    const info = this.baseOf(key);
    if (!info) return 0;
    const t = this.d.stage.time;
    // la fase viene dallo strato della posa: le toppe ondeggiano insieme a lei (se no si staccano di qualche pixel)
    const phase = (this.d.stage.man.layers[key]?.base ?? key).length;
    const bob = 1.6 * Math.sin(t * 0.9 + phase) + 0.7 * Math.sin(t * 2.3);
    const bottom = info.pelo ? Math.max(...info.pelo) : info.rect[3];
    return (1 - r) * (bottom - info.rect[1]) + bob;
  }

  /** La riga del pelo dell'acqua di una creatura nel mare nella colonna x del panorama del suo strato (senza la
   *  linea, il fondo del riquadro). */
  private waterRow(info: LayerInfo, x: number): number {
    const pelo = info.pelo;
    if (!pelo || pelo.length < 2) return info.rect[3] - 3;
    const f = Math.max(0, Math.min(1, (x - info.rect[0]) / (info.rect[2] - info.rect[0]))) * (pelo.length - 1);
    const i = Math.min(Math.floor(f), pelo.length - 2);
    return pelo[i]! + (pelo[i + 1]! - pelo[i]!) * (f - i);
  }

  /** Quali occhi di uno strato sono chiusi in questo momento (un battito di ciglia). */
  private shutEyes(key: string, eyes: Vec3[]): boolean[] {
    const v = this.v;
    if (key === POSE.robin) return eyes.map(() => v.robinBlink > 0.5 || v.robinFear > 0.6);
    if (key === POSE.mollyRight || key === POSE.mollyLeft) {
      const hi = eyes.reduce((best, e, i) => (e[2] > eyes[best]![2] ? i : best), 0);
      return eyes.map((_, i) => (i === hi ? v.mBlink1 > 0.5 : v.mBlink2 > 0.5));
    }
    return eyes.map(() => false);
  }

  /** Altezza (gradi) del bordo della barca visto dall'occhio, nella direzione yaw (gradi, spazio della barca). */
  private sheerAt(yaw: number): number | null {
    const sh = this.d.stage.man.points.sheer;
    if (!sh?.length) return null;
    const n = sh.length;
    const f = ((((yaw + 180) / 360) % 1) + 1) % 1 * n;
    const i = Math.floor(f);
    const t = f - i;
    return sh[i % n]! * (1 - t) + sh[(i + 1) % n]! * t;
  }

  /** La canna da disegnare: dritta, piegata all'abboccata, piegatissima in recupero; nel lancio le pose del lancio. */
  private rodKey(): string {
    const f = this.sim.fishing;
    if (f.phase === 'casting' && this.castT >= 0) {
      const L = this.d.stage.man.layers;
      for (const [until, key] of CAST_ROD) if (this.castT < until) return L[key] ? key : 'rod0';
      return 'rod0';
    }
    const bend = f.bend;
    return bend >= 1.4 ? 'rod2' : bend >= 0.5 ? 'rod1' : 'rod0';
  }

  /** La canna disegnata dal motore: quanto si piega e quanto ruota nel portacanna secondo la pesca; e il
   *  galleggiante appeso alla punta, che le dondola dietro come un pendolo. */
  private updateRod(dt: number): void {
    const f = this.sim.fishing;
    const t = this.d.stage.time;
    let bend = 0;
    if (f.phase === 'waiting') bend = 0.06 + 0.03 * Math.sin(t * 1.3);
    else if (f.phase === 'bite') bend = 0.3 + 0.8 * Math.max(0, Math.sin(t * 10.5)) ** 4;  // gli strattoni dell'abboccata
    else if (f.phase === 'reeling') bend = 1 + 1.2 * Math.min(1, f.tension) + (f.pulling ? 0.25 * (0.5 + 0.5 * Math.sin(t * 19)) : 0);
    else if (f.phase === 'landing') bend = 0.7;
    let tilt = 0;
    if (f.phase === 'casting' && this.castT >= 0) tilt = castTilt(this.castT);
    if (this.strikeT >= 0) {
      // la ferrata: un colpo secco verso l'alto
      this.strikeT += dt;
      if (this.strikeT < 0.35) tilt += 7 * Math.sin((Math.PI * this.strikeT) / 0.35);
      else this.strikeT = -1;
    }
    if (f.phase === 'landing') tilt += 5;
    // la barca che dondola muove appena la cima
    bend += 0.04 * this.d.stage.view.roll * Math.sin(t * 0.8);
    this.rod.update(dt, bend, tilt);

    // il galleggiante appeso (Verlet, con il filo lungo HANG)
    const tip = this.rod.tip();
    if (!this.bob || f.phase === 'waiting' || f.phase === 'bite' || f.phase === 'reeling') {
      const p: Vec3 = [tip[0], tip[1], tip[2] - HANG];
      this.bob = { p, q: [p[0], p[1], p[2]] };
    } else {
      const b = this.bob;
      const k = Math.exp(-1.1 * dt);
      const n: Vec3 = [b.p[0] + (b.p[0] - b.q[0]) * k, b.p[1] + (b.p[1] - b.q[1]) * k, b.p[2] + (b.p[2] - b.q[2]) * k - 9.8 * dt * dt];
      const dx = n[0] - tip[0], dy = n[1] - tip[1], dz = n[2] - tip[2];
      const d = Math.hypot(dx, dy, dz) || 1;
      b.q = b.p;
      b.p = [tip[0] + (dx / d) * HANG, tip[1] + (dy / d) * HANG, tip[2] + (dz / d) * HANG];
    }
    // nel lancio il galleggiante parte da dov'è all'istante della frustata
    if (f.phase === 'casting' && this.castT >= CAST_WHIP && !this.castFrom) this.castFrom = [...this.bob.p] as Vec3;
    if (f.phase !== 'casting') this.castFrom = null;
  }

  /** Il fusto della canna da disegnare, con gli anelli e la campanella in punta, se c'è lo strato del manico. I
   *  colori vengono dal render della canna intera (rod_colori.ts), illuminati come gli strati. */
  private rodTubes(): TubeDraw[] {
    if (!this.d.stage.man.layers['rod_base']) return [];
    const C = ROD_COLORS;
    const blank: TubeDraw = {
      points: this.rod.points(),
      radius: this.rod.radii(),
      bands: C.bands,
      amb: C.points.map((p) => p.amb),
      lamp: C.points.map((p) => p.lamp),
      lant: C.points.map((p) => p.lant),
      light: LAMP_AT,
    };
    // un colore solo, uguale in tutte le fasce (gli anelli cromati, la campanella d'ottone)
    const flat = (c: readonly number[], n: number) => Array.from({ length: n }, () => Array.from({ length: 3 }, () => c));
    const out: TubeDraw[] = [blank];
    for (const r of C.rings) {
      // l'anello sotto il fusto: un puntino lungo quanto è largo
      const a = this.rod.at(r.u - 0.004), b = this.rod.at(r.u + 0.004);
      const da = 0.012 + r.r * 0.3;
      out.push({
        points: [[a[0], a[1], a[2] - da], [b[0], b[1], b[2] - da]],
        radius: [r.r * 0.8, r.r * 0.8],
        bands: [-0.5, 0, 0.5],
        amb: flat(r.amb, 2),
        lamp: flat(r.lamp, 2),
        lant: flat(r.lant, 2),
        light: LAMP_AT,
      });
    }
    // la campanella d'ottone appesa sotto la punta
    const tip = this.rod.tip();
    out.push({
      points: [[tip[0], tip[1], tip[2] - 0.012], [tip[0], tip[1], tip[2] - 0.04]],
      radius: [0.006, 0.013],
      bands: [-0.5, 0, 0.5],
      amb: flat(C.bell.amb, 2),
      lamp: flat(C.bell.lamp, 2),
      lant: flat(C.bell.lant, 2),
      light: LAMP_AT,
    });
    return out;
  }

  /** La frustata del lancio nella vista (gradi di yaw e pitch): caricando si alza un poco, col colpo scatta giù. */
  private castKick(): [number, number] {
    const ct = this.castT;
    if (ct < 0 || ct > 0.9 || this.sim.fishing.phase !== 'casting') return [0, 0];
    const calm = this.d.options.reduceFlash ? 0.5 : 1;
    let p: number, y: number;
    if (ct < CAST_LOAD) {
      const k = smooth01(ct / CAST_LOAD);
      p = 1.1 * k;
      y = -0.4 * k;
    } else if (ct < CAST_WHIP) {
      const k = smooth01((ct - CAST_LOAD) / (CAST_WHIP - CAST_LOAD));
      p = 1.1 - 2.3 * k;
      y = -0.4 + k;
    } else {
      const k = 1 - smooth01((ct - CAST_WHIP) / (0.9 - CAST_WHIP));
      p = -1.2 * k;
      y = 0.6 * k;
    }
    return [y * calm, p * calm];
  }

  /** Un punto del pelo dell'acqua davanti alla canna, a `dist` metri dall'occhio, spostato di lato di `side`. */
  private waterAt(dist: number, side: number): Vec3 {
    const c = Math.cos(FLOAT_YAW), s = Math.sin(FLOAT_YAW);
    return [dist * s + side * c, dist * c - side * s, WATER_Z];
  }

  /** Il galleggiante in acqua a `dist` metri (dall'occhio, spazio della barca), con l'onda e gli strattoni del pesce. */
  private floatAt(dist: number): Vec3 {
    const f = this.sim.fishing;
    const t = this.d.stage.time;
    const side = this.lineSway + 0.12 * Math.sin(t * 0.7) + (f.phase === 'reeling' && f.pulling ? 0.06 * Math.sin(t * 23) : 0);
    const p = this.waterAt(dist, side);
    p[2] += 0.035 * Math.sin(t * 1.9) + 0.02 * Math.sin(t * 3.1 + 1);
    return p;
  }

  /** Il galleggiante adesso: al largo, più vicino mentre recuperi. */
  private floatPos(): Vec3 {
    const f = this.sim.fishing;
    return this.floatAt(f.phase === 'reeling' ? FLOAT_FAR + (FLOAT_NEAR - FLOAT_FAR) * f.progress : FLOAT_FAR);
  }

  /** Un cerchio che si allarga attorno al galleggiante (grandezza 0..1), che parte fra `delay` secondi se negativo. */
  private ripple(size: number, delay: number): void {
    const at = this.floatPos();
    at[2] = WATER_Z;
    this.rings.push({ t: delay, at, size });
  }

  /** La lenza torna su (il galleggiante parte da dov'era nell'ultimo fotogramma). */
  private retrieveFloat(kind: 'reel' | 'lift' | 'lost'): void {
    const from = this.lastFloat ?? this.waterAt(FLOAT_FAR, 0);
    this.retrieve = { t: 0, from: [from[0], from[1], from[2]], kind };
  }

  /** Di quanti gradi un punto (dall'occhio, spazio della barca) sta sopra il bordo della barca. */
  private aboveRail(p: Vec3): number {
    const yaw = Math.atan2(p[0], p[1]) / D2R;
    const el = Math.atan2(p[2], Math.hypot(p[0], p[1])) / D2R;
    return el - (this.sheerAt(yaw) ?? -90);
  }

  /** Lenza, galleggiante con la sua luce, schizzi e cerchi sull'acqua. Il lancio: il galleggiante appeso alla
   *  punta oscilla indietro mentre la canna si carica, la frustata lo strappa via, vola in arco e cade col tonfo;
   *  poi il filo si posa. Quello che sta dietro il bordo della barca non si vede. */
  private tackle(): { line: Stroke | null; strokes: Stroke[]; glows: LightGlow[] } {
    const out = { line: null as Stroke | null, strokes: [] as Stroke[], glows: [] as LightGlow[] };
    const f = this.sim.fishing;
    const man = this.d.stage.man;
    const t = this.d.stage.time;
    const live = !!man.layers['rod_base'];
    const tip = live ? this.rod.tip() : man.layers[this.rodKey()]?.tip ?? man.points.rodTip;
    // appeso alla punta: dondola come un pendolo dietro alla canna che si muove
    const hang: Vec3 = live && this.bob ? this.bob.p : [tip[0], tip[1], tip[2] - HANG];
    let end: Vec3 | null = null;
    let sag = 0;
    let light = 1;
    if (f.phase === 'casting' && this.castT >= 0) {
      const ct = this.castT;
      if (ct < CAST_WHIP) {
        if (live) end = hang;
        else {
          const k = ct < CAST_LOAD ? smooth01(ct / CAST_LOAD) : 1 - smooth01((ct - CAST_LOAD) / (CAST_WHIP - CAST_LOAD));
          end = [hang[0] - 0.05 * k, hang[1] - 0.32 * k, hang[2] + 0.18 * k];
        }
      } else {
        // il volo rallenta verso l'arrivo (il filo che corre via frena il galleggiante); dietro, una scia della sua luce
        const u = Math.min(1, (ct - CAST_WHIP) / (FISHING.castTime - CAST_WHIP));
        const land = this.floatAt(FLOAT_FAR);
        // parte da dove l'ha lasciato la frustata, anche se la canna intanto torna
        const rt = man.layers['rod_f2']?.tip ?? tip;
        const from: Vec3 = live && this.castFrom ? this.castFrom : [rt[0], rt[1], rt[2] - HANG];
        const fly = (u: number): Vec3 => {
          const s = 1 - (1 - Math.max(0, u)) ** 1.8;
          return [from[0] + (land[0] - from[0]) * s, from[1] + (land[1] - from[1]) * s, from[2] + (land[2] - from[2]) * s + CAST_ARC * 4 * s * (1 - s)];
        };
        end = fly(u);
        sag = 0.06 * u;
        const trail: Vec3[] = [];
        for (let i = 0; i <= 6; i++) trail.push(fly(u - 0.1 * (1 - i / 6)));
        const c = FLOAT_LIGHT;
        out.strokes.push({ points: trail.reverse(), alpha: 0.5 * (1 - u * 0.6), color: [c[0] * 0.5, c[1] * 0.5, c[2] * 0.5], width: 1.6 });
      }
    } else if (f.lineOut && f.fake && this.sim.lampy) {
      // la lenza la tiene Lampy (notte 4): mentre suona tira sott'acqua il galleggiante verso di sé; affiorata, la lenza
      // le entra in bocca, passa sotto l'arco fino alla ventosa della coda e scende in mare. I punti della posa
      // scendono con lo strato quando affiora e quando va giù, e salgono con lei se l'hai agganciata
      const lp = this.sim.lampy;
      const r = ease(this.v.lRise);
      if (r < 0.003) {
        const ring = lp.state === 'ringing' ? smooth01(lp.stateTime / (LAMPY_FIRST_BEAT + 2 * (this.sim.cfg.lampy?.beat ?? 0.6))) : 1;
        const fp = this.floatPos();
        end = [fp[0] + (LAMPY_WATER[0] - fp[0]) * ring, fp[1] + (LAMPY_WATER[1] - fp[1]) * ring, WATER_Z - 0.04];
        sag = 0.1;
        light = 0;
      } else {
        const pano = this.d.stage.man.pano;
        const degPx = (pano.latMax - pano.latMin) / pano.height;
        const drop = this.wavePx(POSE.lampy, r);
        const [cx, cy] = this.lampyClimbPx(this.v.lClimb);
        const move = (p: Vec3): Vec3 => {
          const hd = Math.hypot(p[0], p[1]);
          const yaw = Math.atan2(p[0], p[1]) + cx * degPx * D2R;
          const el = Math.atan2(p[2], hd) - (drop + cy) * degPx * D2R;
          return [hd * Math.sin(yaw), hd * Math.cos(yaw), Math.max(WATER_Z, hd * Math.tan(el))];
        };
        const mouth = move(LAMPY_MOUTH);
        const tail = move(LAMPY_TAIL);
        const pts: Vec3[] = [];
        const seg = (a: Vec3, b: Vec3, n: number, s0: number) => {
          for (let i = pts.length ? 1 : 0; i <= n; i++) {
            const s = i / n;
            pts.push([a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, a[2] + (b[2] - a[2]) * s - s0 * 4 * s * (1 - s)]);
          }
        };
        seg(tip, mouth, 14, 0.1);
        seg(mouth, tail, 6, 0.02);
        seg(tail, LAMPY_WATER, 3, 0);
        out.line = { points: pts, alpha: 0.85 };
      }
    } else if (f.lineOut) {
      end = this.floatPos();
      const reeling = f.phase === 'reeling';
      // appena caduto, il filo si posa piano sull'acqua
      const settle = this.plopT >= 0 ? smooth01(this.plopT / 0.7) : 1;
      sag = reeling ? 0.04 + 0.1 * (1 - Math.min(1, f.tension * 2)) : 0.06 + 0.49 * settle;
      if (f.phase === 'bite') {
        // abbocca: il galleggiante va sotto e torna su, la luce si spegne nell'acqua
        const dip = Math.max(0, 0.5 * Math.sin(t * 9) + 0.5 * Math.sin(t * 4.3 + 1));
        end[2] -= 0.12 * dip;
        light = 1 - 0.85 * dip;
      } else if (reeling) {
        // trascinato dal pesce, mezzo sommerso
        light = 0.5 + 0.2 * Math.sin(t * 13);
      }
    } else if (this.retrieve) {
      const r = this.retrieve;
      if (r.kind === 'lost') {
        // filo spezzato: dalla punta pende un pezzo di lenza; il galleggiante resta in acqua, va alla deriva e la
        // sua luce si spegne
        const sw = 0.06 * Math.sin(t * 2.1);
        out.line = { points: [tip, [tip[0] + sw, tip[1] + 0.08, tip[2] - 0.3], [tip[0] + 1.6 * sw, tip[1] + 0.14, tip[2] - 0.62]], alpha: 0.7 };
        const k = Math.max(0, 1 - r.t / 2.5);
        const drift: Vec3 = [r.from[0] + 0.15 * r.t, r.from[1] + 0.25 * r.t, WATER_Z + 0.03 * Math.sin(t * 1.9)];
        if (k > 0.01 && this.aboveRail(drift) > 0) {
          const c = FLOAT_LIGHT;
          out.glows.push({ dir: norm(drift), color: [c[0] * k, c[1] * k, c[2] * k], radius: 0.0017 });
        }
      } else {
        // recuperata a vuoto (veloce, radente) o sollevata col pesce: il galleggiante torna alla punta e ci resta appeso
        const dur = r.kind === 'lift' ? FISHING.landTime * 0.8 : 0.55;
        const u = smooth01(r.t / dur);
        const arc = (r.kind === 'lift' ? 0.7 : 0.25) * 4 * u * (1 - u);
        end = [r.from[0] + (hang[0] - r.from[0]) * u, r.from[1] + (hang[1] - r.from[1]) * u, r.from[2] + (hang[2] - r.from[2]) * u + arc];
      }
    } else if (f.phase === 'idle') {
      // pronto per il lancio: pende dalla punta e dondola
      end = live ? hang : [hang[0] + 0.03 * Math.sin(t * 1.3), hang[1] + 0.04 * Math.sin(t * 0.9 + 1), hang[2]];
    }
    if (end) {
      const pts: Vec3[] = [];
      for (let i = 0; i <= 18; i++) {
        const s = i / 18;
        // il filo lento pende e, dove tocca l'acqua, ci si stende sopra fino al galleggiante
        const z = tip[2] + (end[2] - tip[2]) * s - sag * 4 * s * (1 - s);
        pts.push([tip[0] + (end[0] - tip[0]) * s, tip[1] + (end[1] - tip[1]) * s, Math.max(z, Math.min(WATER_Z, end[2]))]);
      }
      // la lenza sta fuori dalla barca: sotto il bordo la copre lo scafo
      const shown: Vec3[] = [];
      let prev: { p: Vec3; d: number } | null = null;
      for (const p of pts) {
        const d = this.aboveRail(p);
        if (d >= 0) {
          shown.push(p);
          prev = { p, d };
          continue;
        }
        if (prev) {
          const k = prev.d / (prev.d - d);
          shown.push([prev.p[0] + (p[0] - prev.p[0]) * k, prev.p[1] + (p[1] - prev.p[1]) * k, prev.p[2] + (p[2] - prev.p[2]) * k]);
        }
        break;
      }
      if (shown.length >= 2) out.line = { points: shown, alpha: 0.85 };
      if (shown.length === pts.length && light > 0.01) {
        const c = FLOAT_LIGHT;
        out.glows.push({ dir: norm(end), color: [c[0] * light, c[1] * light, c[2] * light], radius: 0.0017 });
      }
    }
    // il tonfo: un lampo bianco nello schizzo e qualche goccia che ricade
    const pt = this.plopT;
    if (pt >= 0 && pt < 0.6 && f.lineOut) {
      const at = this.floatAt(FLOAT_FAR);
      if (this.aboveRail(at) > 0) {
        if (pt < 0.25) {
          const k = 0.7 * (1 - pt / 0.25);
          out.glows.push({ dir: norm(at), color: [0.8 * k, 0.9 * k, 1.0 * k], radius: 0.0035 });
        }
        for (let i = 0; i < 7; i++) {
          const a = hash1(this.splashSeed + i * 7.1) * Math.PI * 2;
          const vh = 0.35 + 0.5 * hash1(this.splashSeed + i * 3.3);
          const vz = 1.5 + 1.1 * hash1(this.splashSeed + i * 5.9);
          const z = vz * pt - 4.9 * pt * pt;
          if (z <= 0) continue;
          const k = 0.9 * (1 - pt / 0.6);
          const d: Vec3 = [at[0] + Math.cos(a) * vh * pt, at[1] + Math.sin(a) * vh * pt, at[2] + z];
          out.glows.push({ dir: norm(d), color: [0.55 * k, 0.6 * k, 0.68 * k], radius: 0.0009 });
        }
      }
    }
    // i cerchi sull'acqua: si allargano e svaniscono (schiacciati dalla prospettiva radente); vicino alla barca
    // il pezzo dietro il bordo non si vede
    for (const r of this.rings) {
      if (r.t <= 0) continue;
      const rad = r.size * (0.06 + 1.1 * (1 - Math.exp(-r.t * 1.8)));
      const alpha = 0.5 * r.size * Math.exp(-r.t * 1.3) * Math.min(1, r.t * 10);
      if (alpha < 0.01) continue;
      let run: Vec3[] = [];
      for (let i = 0; i <= 28; i++) {
        const a = (i / 28) * Math.PI * 2;
        const q: Vec3 = [r.at[0] + Math.cos(a) * rad, r.at[1] + Math.sin(a) * rad, WATER_Z];
        if (this.aboveRail(q) > 0.1) {
          run.push(q);
          if (i < 28) continue;
        }
        if (run.length >= 2) out.strokes.push({ points: run, alpha, color: [0.5, 0.58, 0.66], width: 1.1, even: true });
        run = [];
      }
    }
    return out;
  }

  private overlay(): Overlay | null {
    const v = this.v;
    const js = this.js;
    const A = this.d.assets;
    // l'ultima inquadratura di un finale segreto: l'immagine ferma col lento movimento di camera
    const still = this.cine ? stillFrame(this.cine.s, this.cine.t) : null;
    const img = still ? A.endings[still.key] : undefined;
    if (still && img) {
      // il punto (cx, cy) al centro dello schermo, senza mai uscire dall'immagine
      const lim = 0.5 - 0.5 / Math.max(1, still.zoom);
      const ox = Math.max(-lim, Math.min(lim, still.cx - 0.5));
      const oy = Math.max(-lim, Math.min(lim, 0.5 - still.cy));
      // l'esposizione del render, al posto di quella della notte (la luminosità di base, 1, e l'alba): resta solo la
      // luminosità scelta nelle opzioni
      const ev = img.exposure - 1 - this.sceneEv;
      return { base: img.tex, baseScale: img.scale, wBase: 2 ** ev, aspect: img.aspect, alpha: still.alpha, zoom: still.zoom, offset: [ox, oy] };
    }
    if (js) {
      const seq = A.jumpscares[js.killer];
      if (seq && seq.frames.length) {
        const i = Math.min(seq.frames.length - 1, Math.floor(js.t * seq.fps));
        const fr = seq.frames[i]!;
        // Molly è renderizzata a destra: dal lato sinistro l'immagine si specchia
        const flipX = js.killer === 'molly' && this.sim.molly.side === 'left';
        const cam = jumpscareCamera(js.t, seq.fps, seq.frames.length, seq.aspect, this.d.options.reduceFlash ? 0.35 : 1);
        cam.zoom *= JS_ZOOM[js.killer] ?? 1;
        return { base: fr.tex, baseScale: fr.scale, wBase: 1, aspect: seq.aspect, alpha: Math.min(1, js.t * 12), flipX, ...cam };
      }
      return null;
    }
    if (v.tarp <= 0.001 || !A.tarp) return null;
    const tp = A.tarp;
    // la tela scende dall'alto mentre ti copri
    const k = smooth01(v.tarp);
    const searchX = 0.5 + 0.38 * v.toyX;
    const bob = 0.04 * Math.sin(this.d.stage.time * 2.7);
    return {
      base: tp.base.tex,
      baseScale: tp.base.scale,
      glow: tp.glow.tex,
      glowScale: tp.glow.scale,
      // la tela cerata lascia passare poco: la si intravede appena, finché non passa la luce di Hatch
      wBase: 1.6 + 1.6 * this.d.stage.lampWeight() / 1.7,
      wGlow: 1.2 * v.toy,
      blob: [searchX, 0.74 + bob, 0.24, 0.015],
      aspect: tp.aspect,
      alpha: k,
      offset: [0, (1 - k) * 0.6],
    };
  }

  /** Occhi delle creature in scena: col buio della lampara spenta restano solo loro (riflesso della luna). */
  private eyeGlows(): { world: LightGlow[]; boat: LightGlow[] } {
    const st = this.d.stage;
    const dark = Math.max(0, 1 - st.lampShown * 1.4);
    const out = { world: [] as LightGlow[], boat: [] as LightGlow[] };
    if (dark <= 0.01) return out;
    const v = this.v;
    const pano = st.man.pano;
    const degPx = (pano.latMax - pano.latMin) / pano.height;
    // [strato, intensità, di quanto è sceso e di quanto è andato di lato (pixel del panorama)]: gli occhi
    // scendono con la creatura e spariscono sotto il pelo dell'acqua o dietro il bordo
    const shown: [string, number, number, number][] = [
      [POSE.madre, v.mdRise > 0.002 ? 1 : 0, this.wavePx(POSE.madre, ease(v.mdRise)), 0],
      [POSE.gulpySale, v.gSale, this.wavePx(POSE.gulpySale, v.gRise), 0],
      [POSE.hatchConta, v.hRise > 0.002 ? 1 : 0, this.wavePx(POSE.hatchConta, ease(v.hRise)), 0],
      [POSE.archie, v.aRise > 0.002 ? 1 : 0, this.wavePx(POSE.archie, ease(v.aRise)), 0],
      [POSE.lampy, v.lRise > 0.002 ? 1 : 0, this.wavePx(POSE.lampy, ease(v.lRise)) + this.lampyClimbPx(v.lClimb)[1], this.lampyClimbPx(v.lClimb)[0]],
      ...this.aboard().map((a): [string, number, number, number] => {
        const d = this.sinkPx(a.key, a.p);
        return [a.key, a.p > 0.002 ? a.opacity ?? 1 : 0, d, a.out * d];
      }),
    ];
    for (const [key, k, drop, side] of shown) {
      const info = st.man.layers[key];
      if (!info?.eyes || k < 0.05) continue;
      // nel mondo (e Lampy, che sta sulla lenza oltre la barca) gli occhi spariscono sotto il pelo dell'acqua
      const inSea = info.space === 'world' || key === POSE.lampy;
      const base = this.baseOf(key) ?? info;
      const pulse = 0.85 + 0.15 * Math.sin(st.time * 1.7 + key.length);
      const a = k * dark * pulse;
      // gli occhi chiusi (un battito di ciglia) non brillano: per Molly il primo occhio è il più alto dei due
      const shut = this.shutEyes(key, info.eyes);
      for (const [ei, e] of info.eyes.entries()) {
        if (shut[ei]) continue;
        const yaw = Math.atan2(e[0], e[1]) + (side * 360 / pano.width) * D2R;
        const el = Math.atan2(e[2], Math.hypot(e[0], e[1])) - drop * degPx * D2R;
        const col = (0.5 + ((((yaw / D2R - base.yaw + 540) % 360) - 180) / 360)) * pano.width;
        const limit = inSea ? pano.latMax - this.waterRow(base, col) * degPx : this.sheerAt(yaw / D2R);
        if (limit === null ? drop > 0 : el / D2R < limit + 0.3) continue;
        const c = Math.cos(el);
        const g: LightGlow = { dir: [c * Math.sin(yaw), c * Math.cos(yaw), Math.sin(el)], color: [0.55 * a, 0.7 * a, 0.62 * a], radius: 0.0022 };
        (info.space === 'world' ? out.world : out.boat).push(g);
      }
    }
    return out;
  }

  /**
   * Le lucine di Fangy (spazio del mondo, disegnate una per una). Mentre arriva, una fila sott'acqua che viene dal
   * largo sulla sua direzione; accanto alla barca, quelle del suo corpo (dal manifest, con la posa della testa) che
   * salgono e scendono con lui. Respirano: si accendono in fila lungo ogni fila, dalla gola verso l'acqua, poi calano
   * insieme; al rumore si accendono tutte. Sotto il pelo dell'acqua sono più fioche e più larghe, dietro il bordo
   * della barca non si vedono.
   */
  private fangyLights(): LightGlow[] {
    const fg = this.sim.fangy;
    const out: LightGlow[] = [];
    if (!fg || (this.v.fRow < 0.01 && this.v.fRise < 0.002)) return out;
    const v = this.v;
    const st = this.d.stage;
    const pano = st.man.pano;
    const degPx = (pano.latMax - pano.latMin) / pano.height;
    // più forti al buio, ma si vedono anche con la lampara accesa
    const dark = Math.max(0, 1 - st.lampShown * 1.4);
    const gain = (0.3 + 0.5 * dark) * (1 + 1.3 * v.fFlash);
    const phase = v.fBreath % 1;
    // il respiro: la luce arriva in fila (s = 0 la prima della fila, 1 l'ultima), resta, poi cala tutta insieme
    const breath = (s: number) => {
      const on = smooth01((phase - 0.55 * s) / 0.12);
      const off = 1 - smooth01((phase - 0.72) / 0.28);
      return 0.12 + 0.88 * Math.max(v.fFlash, on * off);
    };
    const glow = (p: Vec3, k: number, under: boolean, wide = 1): void => {
      const n = norm(p);
      const a = k * gain * (under ? 0.45 : 1);
      out.push({ dir: n, color: [FANGY_LIGHT[0] * a, FANGY_LIGHT[1] * a, FANGY_LIGHT[2] * a], radius: (under ? 0.0034 : 0.0011) * wide });
    };
    if (v.fRise < 0.002) {
      // la fila arriva dal largo girando verso la barca: la testa davanti, le altre in scia lungo la stessa strada, e
      // si accendono una dopo l'altra mentre si avvicina (se torna indietro, sfuma)
      const k = v.fApp;
      const near = Math.hypot(FANGY_AT[0], FANGY_AT[1]) + 1.2;
      for (let i = 0; i < FANGY_ROW; i++) {
        const s = i / (FANGY_ROW - 1);
        const u = Math.max(0, k - s * 0.16);
        const lit = smooth01((k * 1.8 - s * 0.6) / 0.3);
        if (lit < 0.01) continue;
        const r = FANGY_FAR + (near - FANGY_FAR) * smooth01(u);
        const yaw = (YAW.fangy + FANGY_SWING * (1 - u) ** 1.5) * D2R;
        glow([Math.sin(yaw) * r, Math.cos(yaw) * r, WATER_Z - FANGY_DEEP], lit * v.fRow * (0.5 + 0.8 * breath(s)), true, 1.6);
      }
      return out;
    }
    // accanto alla barca: le lucine del corpo, con la posa della testa che si vede di più
    const L = st.man.layers;
    const base = L[POSE.fangy];
    if (!base?.luci) return out;
    const drop = this.wavePx(POSE.fangy, ease(v.fRise));
    const poses: [LayerInfo | undefined, number][] = [
      [base, Math.max(0, 1 - v.fBow - v.fStern)],
      [L[POSE.fangyBow], v.fBow],
      [L[POSE.fangyStern], v.fStern],
    ];
    const rows = new Map<string, number>();
    for (const f of base.luci.fila) rows.set(f, (rows.get(f) ?? 0) + 1);
    for (const [info, w] of poses) {
      if (!info?.luci || w < 0.01) continue;
      const seen = new Map<string, number>();
      info.luci.p.forEach((p, i) => {
        const fila = info.luci!.fila[i] ?? '';
        const j = seen.get(fila) ?? 0;
        seen.set(fila, j + 1);
        const s = j / Math.max(1, (rows.get(fila) ?? 1) - 1);
        const yaw = Math.atan2(p[0], p[1]);
        const el = Math.atan2(p[2], Math.hypot(p[0], p[1])) - drop * degPx * D2R;
        const col = (0.5 + ((((yaw / D2R - base.yaw + 540) % 360) - 180) / 360)) * pano.width;
        const water = pano.latMax - this.waterRow(base, col) * degPx;
        const sheer = this.sheerAt(yaw / D2R);
        if (sheer !== null && el / D2R < sheer + 0.15) return;
        const under = el / D2R < water;
        if (under && el / D2R < water - 6) return;
        const c = Math.cos(el);
        glow([c * Math.sin(yaw), c * Math.cos(yaw), Math.sin(el)], w * breath(s), under);
      });
    }
    return out;
  }

  render(): void {
    const st = this.d.stage;
    const v = this.v;
    const js = this.js;
    const eyes = this.eyeGlows();
    let flash = 0;
    let flashColor: [number, number, number] = [0.55, 0.02, 0.03];
    if (js && !this.d.options.reduceFlash) flash = Math.max(0, 0.55 - js.t * 2.5);
    else if (v.dawn > 0) {
      // l'alba: una velatura calda che sale dall'orizzonte
      flash = 0.16 * v.dawn;
      flashColor = [0.95, 0.62, 0.42];
    }
    const dawnExposure = v.dawn * 0.9 - v.dark * 4;
    this.sceneEv = dawnExposure * 0.5;
    // jumpscare: nastro VHS rovinato, più forte all'impatto e a strappi
    let glitch = 0;
    if (js) {
      const spike = hash1(Math.floor(js.t * 7) + 3) > 0.72 ? 0.35 : 0;
      glitch = Math.min(1, 0.3 + 0.55 * Math.exp(-js.t * 4) + spike) * (this.d.options.reduceFlash ? 0.4 : 1);
    }
    // binocolo: solo il mondo (niente barca), i luoghi ad alta risoluzione, la luce rossa della videocamera
    const binoOn = this.bino > 0.5;
    const be = smooth01(this.bino);
    // la lenza e il galleggiante: non sotto il telone, non nel binocolo
    const tk = this.sim.hide === 'out' && !binoOn ? this.tackle() : null;
    const man = st.man;
    let layers = this.layerDraws();
    if (binoOn) layers = layers.filter((d) => man.layers[typeof d === 'string' ? d : d.key]?.space === 'world');
    const B = this.d.assets.binocular;
    // il Foxy nel suo posto: la vista del posto con lui (fermo o più vicino) al posto di quella vuota
    const fx = this.sim.foxy;
    const fxStage = fx?.stage ?? null;
    const fxAt = fx && fxStage !== null ? fx.places[fx.place]!.id : undefined;
    const places = this.bino > 0
      ? B.places
        .filter((p) => Math.abs(((p.yaw - st.view.yaw + 540) % 360) - 180) < p.hfov / 2 + st.view.hfov * 0.75 + 2)
        .map((p) => (p.key === fxAt && fxStage !== null && p.foxy?.[fxStage] ? p.foxy[fxStage]! : p.place))
      : [];
    // gli aloni delle luci lontane sono pensati per la vista normale: col binocolo si stringono. Quelle che la Madre ha
    // dietro (la candela dell'edicola) non si vedono attraverso di lei
    const madreDrop = v.mdRise > 0.002 ? this.wavePx(POSE.madre, ease(v.mdRise)) : null;
    const land = madreDrop === null ? st.landscapeGlows([], be) : st.landscapeGlows([], be).filter((g) => !this.behind(POSE.madre, madreDrop, g.dir));
    let glows = land.concat(eyes.world).slice(0, 16);
    if (be > 0) {
      const k = 1 - be * (1 - Math.min(1, (st.view.hfov / 90) * 1.6));
      glows = glows.map((g) => ({ ...g, radius: g.radius * k, color: [g.color[0] * (1 - 0.35 * be), g.color[1] * (1 - 0.35 * be), g.color[2] * (1 - 0.35 * be)] }));
    }
    // il Foxy nel suo posto, finché non ci sono le sue viste renderizzate: due occhi rossi che ti guardano; più vicino,
    // più grandi e più bassi; col posto vuoto niente
    if (this.bino > 0 && fx && fx.stage !== null && !B.places.find((p) => p.key === fxAt)?.foxy) {
      const p = fx.places[fx.place]!;
      const lean = fx.stage === 1;
      for (const s of [-1, 1]) {
        const yaw = ((p.yaw + s * (lean ? 0.09 : 0.06)) * Math.PI) / 180;
        const pit = ((p.pitch - (lean ? 0.35 : 0)) * Math.PI) / 180;
        const k = lean ? 1.6 : 1;
        glows.push({ dir: [Math.sin(yaw) * Math.cos(pit), Math.cos(yaw) * Math.cos(pit), Math.sin(pit)], color: [1.6 * k * be, 0.08 * be, 0.05 * be], radius: 0.0007 * k });
      }
    }
    if (this.bino > 0 && B.rec && Math.floor(st.time / 0.6) % 2 === 0) {
      glows.push({ dir: norm(B.rec), color: [2.4 * be, 0.05 * be, 0.04 * be], radius: 0.0011 });
    }
    this.hud.root.style.opacity = String(1 - 0.8 * be);
    st.frame({
      layers,
      bino: this.bino > 0 ? { amount: be, places } : null,
      overlay: this.overlay(),
      line: tk?.line ?? null,
      strokes: tk?.strokes,
      // la canna resta finché si vede la barca: sotto il telone la copre la tela, come il resto
      tubes: binoOn ? [] : this.rodTubes(),
      // a batteria morta lo schermo del sonar è nero
      sonar: binoOn || this.sim.blackout ? null : this.sonar.canvas,
      gauge: this.sim.cfg.battery && !binoOn ? { angle: this.needleAngle(), alpha: 1 } : null,
      sonarGain: 0.9 + 0.2 * Math.sin(st.time * 2.3),
      ambient: 1 + v.dawn * 1.6,
      exposure: st.brightness + dawnExposure * 0.5,
      flash,
      flashColor,
      glitch,
      fade: (1 - v.dark * 0.9) * (1 - this.cineBlack),
      glows,
      boatGlows: binoOn ? [] : tk ? [...eyes.boat, ...tk.glows] : eyes.boat,
      glowSprites: be > 0
        ? this.fangyLights().map((g) => {
          const k = 1 - be * (1 - Math.min(1, (st.view.hfov / 90) * 1.6));
          const a = 1 - 0.35 * be;
          return { ...g, radius: g.radius * k, color: [g.color[0] * a, g.color[1] * a, g.color[2] * a] as Vec3 };
        })
        : this.fangyLights(),
    });
  }

  // ───────────────────────── audio ─────────────────────────

  private updateAudio(dt: number): void {
    const a = this.d.audio;
    const sim = this.sim;
    const v = this.v;
    a.setListenerYaw(this.d.stage.view.yaw);
    a.setMuffled(v.tarp * 0.8);
    this.d.sfx.rock(this.js ? 0 : v.rock);
    this.d.sfx.toy(this.js ? 0 : v.toy, dirPos(180 + v.toyX * 35, 1.3, -15));
    // Fangy che respira dietro le spalle mentre ascolta
    const fg = sim.fangy;
    this.d.sfx.fangyListen(fg?.present && fg.state !== 'attack' && !this.js && !this.finished ? ease(v.fRise) : 0, FANGY_AT);
    // il mare che si ferma quando arriva la Madre (e torna quando se ne va)
    this.loops.sea?.setGain(0.9 * (1 - 0.85 * v.mCalm), 0.1);
    // sibilo della lampara col livello
    this.loops.lamp?.setGain([0.0, 0.45, 0.8][sim.lamp]! * (1 - 0.6 * this.d.stage.lampDip), 0.05);
    // campane delle ore
    for (let i = 0; i < this.bells.length; i++) {
      this.bells[i]! -= dt;
      if (this.bells[i]! <= 0) {
        a.play('bell_toll', { pos: dirPos(BELL_YAW, 5, 4), gain: 0.55, lowpass: 2600 });
        this.bells.splice(i, 1);
        i--;
      }
    }
    // scricchiolii (più fitti quando Molly dondola la barca)
    this.creakTimer -= dt * (1 + v.rock * 6);
    if (this.creakTimer <= 0 && !this.quiet) {
      const k = 1 + Math.floor(Math.random() * 4);
      a.play(`creak_${k}`, { pos: dirPos(Math.random() * 360 - 180, 1.5, -25), gain: 0.35 + v.rock * 0.6 });
      this.creakTimer = 7 + Math.random() * 9;
    }
    // recupero: mulinello e filo teso
    const f = sim.fishing;
    if (f.phase === 'reeling') {
      const reelOn = sim.reelHeld && sim.hide === 'out' ? 0.6 : 0;
      this.loops.reel?.setGain(reelOn, 0.05);
      this.loops.reel?.setRate(0.85 + f.progress * 0.4);
      this.loops.tension?.setGain(Math.max(0, f.tension - 0.35) * 1.4, 0.05);
      this.loops.tension?.setRate(0.8 + f.tension * 0.6);
    }
    // la ninna nanna: negli ultimi secondi il carillon si scarica e rallenta, come la molla che finisce
    if (this.lullabyV && sim.blackout && sim.cfg.battery) {
      const left = sim.lullaby;
      this.lullabyV.setRate(left < 6 ? 0.55 + 0.45 * Math.max(0, left / 6) : 1);
    }
    // il battito del cuore ora è in paura.ts (updateFear), col respiro e la tensione
  }

  /** La chiamata alla radio dell'inizio della notte, con i sottotitoli. */
  private updateRadio(dt: number): void {
    const r = this.radio;
    if (!r) return;
    const prev = r.t;
    r.t += dt;
    const lines = r.lines ?? (RADIO[this.nightNo] ?? RADIO[1]!)[this.d.lang];
    const a = this.d.audio;
    if (prev < 0 && r.t >= 0) {
      a.play('radio_on', { pos: RADIO_AT, gain: 0.8 });
      r.hiss = a.play('radio_static', { loop: true, pos: RADIO_AT, gain: 0.25, fadeIn: 0.3 });
    }
    while (r.next < lines.length && r.t >= lines[r.next]!.at) {
      const line = lines[r.next]!;
      const after = lines[r.next + 1];
      if (line.text) {
        const max = after ? after.at - line.at : 2;
        r.utt = speak(a, line.text, RADIO_VOICE, { maxDuration: max, pos: RADIO_AT });
        if (this.d.options.subtitles) this.hud.subtitle(this.S.radioName, line.text);
      } else {
        this.hud.subtitle('', '');
        a.play('radio_off', { pos: RADIO_AT, gain: 0.8 });
        r.hiss?.stop(0.2);
        this.radio = null;
        return;
      }
      r.next++;
    }
  }

  // ───────────────────────── interfaccia ─────────────────────────

  private updateHud(dt: number): void {
    const sim = this.sim;
    const S = this.S;
    const hud = this.hud;
    hud.update(dt);
    const hour = Math.min(6, Math.floor(sim.time / HOUR_SECONDS));
    const minutes = sim.outcome.kind === 'playing' ? ((sim.time % HOUR_SECONDS) / HOUR_SECONDS) * 60 : 0;
    const shownHour = sim.outcome.kind === 'won' || (sim.outcome.kind === 'dead' && sim.outcome.killer === 'mother') ? 6 : hour;
    const key = shownHour * 100 + Math.floor(minutes / 10);
    if (key !== this.lastHourShown) {
      this.lastHourShown = key;
      hud.setClock(this.nightNo, shownHour, minutes);
    }
    hud.setQuota(sim.fish, sim.cfg.quota);
    const f = sim.fishing;
    // finita la notte (l'alba, il finale) i comandi sono fermi: la barra del mulinello non serve più
    hud.reel(f.phase === 'reeling' && sim.hide === 'out' && !this.finished, f.tension, f.progress, f.strain);
    // il nome di ciò che sta sotto il puntatore
    let target: Target = null;
    if (sim.hide === 'out' && !this.sonarOpen && !this.js && this.mouse.inside && !pad.active) target = this.targetAt(this.mouse.x, this.mouse.y);
    if (target !== this.hoverTarget) {
      this.hoverTarget = target;
      this.d.canvas.style.cursor = target ? 'pointer' : 'crosshair';
    }
    const label = target ? S.labels[target] : '';
    hud.hover(label, this.mouse.x * innerWidth, this.mouse.y * innerHeight);
    hud.showTurn(sim.hide === 'out' && !this.js && !this.finished && this.mouse.inside && !pad.active && this.mouse.y > 0.88);
    hud.setVisible(!this.js);
    // i suggerimenti. Quelli della pesca e dei comandi della prima notte (lanciare, ferrare, recuperare, guardarsi
    // attorno, il pesce a Gulpy, il telone) sono il tutorial: solo nella notte 1, o sempre con l'opzione «Tutorial
    // sempre attivo» (prova dell'utente del 12 ottobre). Le regole dei mostri delle notti dopo restano
    const tut = this.nightNo === 1 || this.d.options.tutorial;
    let hint = '';
    if (!this.finished && !this.js) {
      const mo = sim.mother;
      if (mo && (mo.state === 'passing' || (mo.state === 'approaching' && mo.stateTime > 3.5 - this.motherSkip))) hint = this.hintText('mother');
      else if (sim.hide === 'in') hint = tut ? this.hintText('unhide') : '';
      else if (sim.fangy?.listening) hint = this.hintText('fangy');
      else if (sim.hatch.state === 'counting') hint = tut ? this.hintText('hide') : '';
      else if (sim.gulpy.canBeFed && sim.fish > 0) hint = tut && sim.facing(YAW.bow, VIEW.bowHalfAngle) ? this.hintText('throw') : '';
      else if (sim.robin?.present && !sim.blackout) hint = this.hintText('robin');
      else if (sim.archie?.state === 'inhaling' && sim.lamp > 0) hint = this.hintText('archie');
      else if (sim.archie?.state === 'waiting') hint = this.hintText('archieWait');
      else if (sim.foxy?.state === 'gone' && this.bino > 0.5) hint = this.hintText('foxyGone');
      else if (sim.foxy && sim.foxy.stage !== null && !sim.foxy.everSeen) hint = this.hintText('foxy');
      else if (f.phase === 'bite') hint = this.biteHint(tut);
      else if (f.phase === 'reeling') hint = tut ? this.hintText('reel') : '';
      else if (sim.molly.present || sim.gulpy.present) hint = '';
      else if (tut && f.phase === 'idle' && sim.facing(YAW.rod, VIEW.rodHalfAngle) && sim.landedCount < 2) hint = this.hintText('cast');
      else if (tut && sim.time < 25 && !sim.facing(YAW.rod, VIEW.rodHalfAngle)) hint = pad.active ? pad.glyphs(S.pad.look) : S.look;
    }
    hud.hint(hint);
    // la radio: i sottotitoli spariscono da soli se non c'è chiamata in corso
    if (!this.radio && sim.hatch.state !== 'counting' && sim.hatch.state !== 'boarding') hud.subtitle('', '');
  }
}
