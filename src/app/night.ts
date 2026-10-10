/**
 * Una notte giocata: collega la simulazione (src/game) alla scena, all'audio e all'interfaccia.
 * Le creature sono strati del panorama (le pose renderizzate) che emergono dall'acqua o salgono da dietro il
 * bordo, e se ne vanno scendendo, secondo lo stato della simulazione; la vista da sotto il telone e i jumpscare sono immagini a
 * tutto schermo disegnate dentro la scena (prendono bloom, grana e vignetta come il resto).
 */
import type { Vec3 } from '../engine/assets.ts';
import { dirPos, type AudioEngine, type Voice } from '../engine/audio.ts';
import type { BinoPlace, LayerDraw, LightGlow, Overlay, Stroke } from '../engine/renderer.ts';
import { CHILD, RADIO_VOICE, speak, type Utterance } from '../engine/voice.ts';
import { FISHING, HOUR_SECONDS, NIGHTS, VIEW, YAW, type LampLevel, type MonsterId } from '../game/config.ts';
import type { GameEvent } from '../game/events.ts';
import { NightSim } from '../game/sim.ts';
import { FISH_BY_ID } from '../game/catalog.ts';
import { LORE_TEXT, RADIO, STRINGS, type Lang } from '../i18n.ts';
import { Hud } from './hud.ts';
import type { Options } from './save.ts';
import type { Sfx } from './sfx.ts';
import { Sonar } from './sonar.ts';
import type { Stage } from './stage.ts';

export interface OverlayTex {
  tex: WebGLTexture;
  scale: number;
}

export interface NightAssets {
  /** vista da sotto il telone: passo base e passo retroilluminato (la luce del giocattolo che fruga) */
  tarp: { base: OverlayTex; glow: OverlayTex; aspect: number } | null;
  /** fotogrammi dei jumpscare renderizzati, se ci sono */
  jumpscares: Partial<Record<MonsterId, { frames: OverlayTex[]; fps: number; aspect: number }>>;
  /** ritratti dei pesci del Catalogo già renderizzati: id → URL dell'immagine */
  fish: Record<string, string>;
  /** i luoghi dell'orizzonte per il binocolo, e dove sta la luce rossa della videocamera */
  binocular: { places: { key: string; yaw: number; pitch: number; hfov: number; place: BinoPlace }[]; rec: Vec3 | null };
}

export interface NightStats {
  caught: number;
  fed: number;
  lore: string[];
  /** secondi giocati */
  time: number;
}

export type NightEnd = { kind: 'won'; stats: NightStats } | { kind: 'dead'; killer: MonsterId | 'mother'; cause?: 'lullaby'; stats: NightStats };

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
const HATCH_AT: Vec3 = [0.35, -7.4, -0.6];
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
const CAST_WHIP = 0.24;
const BELL_YAW = -40;

/** Pose renderizzate nella scena (vedi tools/render/scena_creature.py). */
const POSE = {
  gulpySale: 'gulpy_sale',
  gulpyPretende: 'gulpy_pretende',
  mollyRight: 'molly_destra',
  mollyLeft: 'molly_sinistra',
  hatchConta: 'hatch_conta',
  /** notte 2: ancora da modellare (si disegna quando il render c'è) */
  robin: 'robin_secchio',
} as const;

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
  private sonarOpen = false;
  /** binocolo: alzato (desiderato), quanto è alzato (0..1), campo dello zoom, inclinazione dello sguardo */
  private binoUp = false;
  private bino = 0;
  private binoFov = 9;
  private binoPitch = 2.5;
  private turnArmed = true;
  private reelByMouse = false;
  private hoverTarget: Target = null;
  // stato visivo (morbido)
  private v = { gSale: 0, gRise: 0, gPret: 0, mR: 0, mL: 0, hRise: 0, robin: 0, tarp: 0, toy: 0, toyX: -1, dawn: 0, rock: 0, dark: 0 };
  private gulpyDive = 0;
  private js: { killer: MonsterId; t: number; yaw: number; scream: Voice | null } | null = null;
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
  // audio
  private loops: Record<string, Voice | null> = {};
  private radio: { t: number; next: number; utt: Utterance | null; hiss: Voice | null } | null = null;
  private bells: number[] = [];
  private creakTimer = 9;
  private lastHourShown = -1;
  private heart = 0;
  private listeners: [EventTarget, string, EventListener][] = [];
  /** dove si sente Gulpy: lontano mentre sale, aggrappato alla prua quando pretende (dai render) */
  private gulpyFar: Vec3;
  private bowAt: Vec3;
  /** quale notte si gioca */
  readonly nightNo: number;
  /** ago del voltmetro (volt, velocità): una molla smorzata, come un ago vero */
  private needle = { v: 13.8, vel: 0 };
  private flickerTimer = 0;
  /** la lucina dietro il quadrante del voltmetro (0..1): trema con la lampara, muore con la batteria */
  private gaugeGlow = 1;
  /** la ninna nanna della Madre a batteria morta */
  private lullabyV: Voice | null = null;

  constructor(private d: NightDeps) {
    this.S = STRINGS[d.lang];
    this.nightNo = NIGHTS[d.night ?? 1] ? (d.night ?? 1) : 1;
    this.sim = new NightSim(NIGHTS[this.nightNo]!, d.seed, d.foundLore);
    this.hud = new Hud(d.ui, d.lang);
    this.sonarEl = document.createElement('div');
    this.sonarEl.className = 'sonar-full';
    this.sonarEl.appendChild(this.sonar.canvas);
    const close = document.createElement('div');
    close.className = 'sonar-close';
    close.textContent = this.S.sonarClose;
    this.sonarEl.appendChild(close);
    d.ui.appendChild(this.sonarEl);
    this.sonar.onPing = () => d.audio.play('sonar_ping', { pos: [0.3, -1.42, -0.5], gain: 0.25 });
    this.sonar.onWarn = () => d.sfx.sonarWarn();
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
    for (const [t, ev, fn] of this.listeners) t.removeEventListener(ev, fn);
    this.listeners = [];
    for (const v of Object.values(this.loops)) v?.stop(0.4);
    this.loops = {};
    this.radio?.utt?.stop();
    this.radio?.hiss?.stop(0.2);
    this.radio = null;
    this.lullabyV?.stop(0.4);
    this.lullabyV = null;
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
  }

  setPaused(p: boolean): void {
    this.paused = p;
    this.held.clear();
    this.mouse.down = false;
    this.sim.setReelHeld(false);
  }

  // ───────────────────────── input ─────────────────────────

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
      if (k === ' ') this.sim.setReelHeld(this.mouse.down && this.reelByMouse);
    });
    this.on(window, 'blur', () => {
      this.held.clear();
      this.mouse.down = false;
      this.sim.setReelHeld(false);
    });
    this.on(c, 'mousemove', (e) => {
      const m = e as MouseEvent;
      this.mouse.x = m.clientX / innerWidth;
      this.mouse.y = m.clientY / innerHeight;
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
        this.sim.setReelHeld(this.held.has(' '));
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
        this.setLamp(this.sim.lamp + 1);
        break;
      case 's':
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

  /** Alza o abbassa il binocolo; alzandolo lo sguardo va all'altezza del luogo più vicino. */
  private raiseBino(up: boolean): void {
    if (up && !this.canBino()) return;
    if (up && !this.binoUp) {
      const yaw = this.d.stage.view.yaw;
      let best: { d: number; pitch: number } | null = null;
      for (const p of this.d.assets.binocular.places) {
        const d = Math.abs(((p.yaw - yaw + 540) % 360) - 180);
        if (d < 14 && (!best || d < best.d)) best = { d, pitch: p.pitch };
      }
      this.binoPitch = best ? best.pitch : 2.5;
    }
    this.binoUp = up;
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

  private setLamp(l: number): void {
    const lv = Math.max(0, Math.min(2, l)) as LampLevel;
    if (this.sim.hide !== 'out') return;
    this.sim.setLamp(lv);
  }

  private turn(): void {
    if (this.paused || this.finished || this.js || this.sim.hide !== 'out') return;
    const v = this.d.stage.view;
    v.targetYaw = v.targetYaw + 180;
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

    // sguardo
    if (!this.js && sim.hide === 'out' && !this.sonarOpen && !this.finished) {
      const reeling = sim.fishing.phase === 'reeling';
      let spin = 0;
      const edge = 0.2;
      const mx = this.mouse.x;
      if (this.mouse.inside && !reeling) {
        if (mx < edge) spin = -(((edge - mx) / edge) ** 1.5);
        else if (mx > 1 - edge) spin = ((mx - (1 - edge)) / edge) ** 1.5;
      }
      if (this.held.has('a') || this.held.has('arrowleft')) spin = -1;
      if (this.held.has('d') || this.held.has('arrowright')) spin = 1;
      // col binocolo si gira piano, in proporzione allo zoom; su e giù coi bordi alto e basso
      const zoomK = this.bino > 0 ? view.hfov / 90 : 1;
      view.targetYaw += spin * 150 * this.d.options.sensitivity * dt * zoomK;
      if (this.bino > 0.5 && this.mouse.inside) {
        const my = this.mouse.y;
        let tilt = 0;
        if (my < edge) tilt = ((edge - my) / edge) ** 1.5;
        else if (my > 1 - edge) tilt = -(((my - (1 - edge)) / edge) ** 1.5);
        if (this.held.has('w') || this.held.has('arrowup')) tilt = 1;
        this.binoPitch = Math.max(-8, Math.min(12, this.binoPitch + tilt * 30 * zoomK * dt));
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
    sim.setView(view.yaw, this.sonarOpen || this.bino > 0.5);
    if (!this.finished) sim.update(dt);
    for (const e of sim.drainEvents()) this.handle(e);

    this.updateVisuals(dt);
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
    return { caught: s.caught, fed: s.fed, lore: [...s.loreThisNight], time: s.time };
  }

  private handle(e: GameEvent): void {
    const a = this.d.audio;
    const fx = this.d.sfx;
    const S = this.S;
    const cap = (t: string) => this.d.options.subtitles && this.hud.caption(t);
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
        a.play(Math.random() < 0.5 ? 'rod_bell_1' : 'rod_bell_2', { pos: this.d.stage.man.points.rodTip });
        this.ripple(0.6, 0);
        break;
      case 'baitStolen':
        a.play('splash_s1', { pos: this.floatPos(), gain: 0.5 });
        this.ripple(0.8, 0);
        this.retrieveFloat('reel');
        this.hud.toast(S.baitStolen, '', 1.8);
        break;
      case 'hooked':
        this.loops.reel = a.play('reel_loop', { loop: true, gain: 0, pos: [0.86, 0.85, -0.6] });
        this.loops.tension = a.play('line_tension', { loop: true, gain: 0, pos: [1.6, 2.6, 0.1] });
        break;
      case 'fishPull':
        a.play(['splash_s1', 'splash_s2', 'splash_s3'][Math.floor(Math.random() * 3)]!, { pos: this.floatPos(), gain: 0.7 });
        this.lineSway = (Math.random() < 0.5 ? -1 : 1) * (0.4 + Math.random() * 0.4);
        this.ripple(0.9, 0);
        break;
      case 'lineSnap':
        a.play('line_snap', { pos: this.d.stage.man.points.rodTip });
        this.retrieveFloat('lost');
        this.hud.toast(S.lineSnap, '', 1.8);
        this.stopReel();
        break;
      case 'fishEscaped':
        a.play('splash_s2', { pos: this.floatPos(), gain: 0.5 });
        this.ripple(1, 0);
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
        else if (e.reason === 'dark') {
          // l'interruttore scatta, ma non succede niente
          a.play('lamp_switch', { pos: LAMP_AT, gain: 0.35, rate: 0.85 });
          this.hud.toast(S.denied.dark, '', 1.4);
        }
        break;
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
      case 'dead':
        this.finished = true;
        this.sim.setReelHeld(false);
        this.stopReel();
        if (e.killer === 'mother') {
          const o = this.sim.outcome;
          const cause = o.kind === 'dead' ? o.cause : undefined;
          this.endResult = { kind: 'dead', killer: 'mother', cause, stats: this.stats() };
          this.endTimer = 4.5;
          if (cause === 'lullaby') {
            // la canzone è finita al buio: sotto la barca sale qualcosa di enorme
            this.lullabyV?.stop(0.2);
            this.lullabyV = null;
            a.play('splash_big', { pos: [0, 1.2, -2.2], gain: 1, rate: 0.7 });
            a.play('mus_madre', { gain: 1 });
            this.d.stage.view.shake = this.d.options.reduceFlash ? 0.4 : 1.6;
          } else {
            // le campane della festa, ovattate, e sotto la Madre che si sveglia (se cantava, la canzone sfuma)
            this.lullabyV?.stop(2);
            this.lullabyV = null;
            a.play('bell_dawn', { pos: dirPos(BELL_YAW, 5, 4), gain: 0.35, lowpass: 900 });
            a.play('mus_madre', { gain: 0.9 });
            this.hud.toast(S.sixAm, S.quotaMissed, 4);
          }
        } else {
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
        this.endResult = { kind: 'won', stats: this.stats() };
        this.endTimer = 7;
        a.play('bell_dawn', { pos: dirPos(BELL_YAW, 5, 4), gain: 0.8, lowpass: 3000 });
        setTimeout(() => a.play('mus_6am', { gain: 0.85 }), 1500);
        this.loops.dawn = a.play('amb_dawn', { loop: true, fadeIn: 4, gain: 0.8 });
        this.loops.drone?.stop(3);
        this.loops.drone = null;
        this.hud.toast(S.sixAm, `${S.survived} · ${S.quotaMet}`, 6);
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

  private startJumpscare(killer: MonsterId): void {
    // la camera si gira dove la creatura parte (la posa di gioco da cui partono i fotogrammi)
    const L = this.d.stage.man.layers;
    const yaw =
      killer === 'gulpy'
        ? (L[POSE.gulpyPretende]?.yaw ?? 0)
        : killer === 'molly'
          ? this.sim.molly.yaw
          : killer === 'robin'
            ? (L[POSE.robin]?.yaw ?? YAW.robin)
            : (L[POSE.hatchConta]?.yaw ?? 180);
    this.binoUp = false;
    this.bino = 0;
    this.d.stage.view.swayYaw = this.d.stage.view.swayPitch = this.d.stage.view.steady = 0;
    if (this.sonarOpen) this.toggleSonar(false);
    const reduce = this.d.options.reduceFlash;
    this.js = { killer, t: 0, yaw, scream: this.d.sfx.jumpscare(killer) };
    this.d.stage.view.shake = reduce ? 0.6 : 3.2;
    this.loops.heart?.stop(0.1);
    this.loops.heart = null;
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
    v.gSale = approach(v.gSale, saleT, saleT > v.gSale ? 3 : 1.5, dt);
    v.gRise = approach(v.gRise, riseT, 4, dt);
    // alla prua sale da dietro il bordo; se ne va lasciandosi ricadere giù
    v.gPret = toward(v.gPret, pretT, 0.45, 1.0, dt);
    if (v.gRise < 0.02 && saleT === 0) v.gSale = approach(v.gSale, 0, 6, dt);

    // Molly: si affaccia di colpo dal suo lato, scivola giù quando è contenta
    const mollyShown = m.state === 'peeking' || m.state === 'tantrum' || m.state === 'attack';
    const rT = mollyShown && m.side === 'right' ? 1 : 0;
    const lT = mollyShown && m.side === 'left' ? 1 : 0;
    v.mR = toward(v.mR, rT, 0.35, 0.9, dt);
    v.mL = toward(v.mL, lT, 0.35, 0.9, dt);

    // Hatch: emerge piano dietro la poppa per contare; quando sale a bordo si rituffa
    const counting = h.state === 'counting';
    v.hRise = toward(v.hRise, counting ? 1 : 0, 1.6, 0.9, dt);

    // Robin: sul bordo mentre sale e ruba; nella luce si ritrae, abbassandosi dietro il bordo
    const rb = sim.robin;
    const robinT = rb && rb.present ? 1 - 0.6 * rb.fear : rb?.state === 'attack' ? 1 : 0;
    v.robin = toward(v.robin, robinT, 0.6, 0.5, dt);

    this.updateBattery(dt);

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

    // alba alle 6: il cielo si schiarisce, il mare si calma
    if (sim.outcome.kind === 'won') v.dawn = Math.min(1, v.dawn + dt / 5);
    if (sim.outcome.kind === 'dead' && sim.outcome.killer === 'mother') v.dark = Math.min(1, v.dark + dt / 4);
    st.view.swell = 1 - 0.7 * v.dawn;

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
        else if (this.sim.molly.side === 'right') v.mR = 1;
        else v.mL = 1;
      }
      if (t < 0.12 && !this.d.options.reduceFlash) st.lampDip = 1;
    }
    st.update(dt);
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
    const rest = c >= b.low ? 11.6 + 2.2 * ((c - b.low) / (1 - b.low)) : 10.2 + 1.4 * (c / b.low);
    const load = [0, 0.06, 0.2][sim.lamp]! + (sim.sonarOpen ? 0.05 : 0);
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

  private layerDraws(): (string | LayerDraw)[] {
    const v = this.v;
    const man = this.d.stage.man;
    const sim = this.sim;
    const layers: (string | LayerDraw)[] = ['world'];
    const has = (k: string) => !!man.layers[k];
    // creature nel mondo: emergono dal pelo dell'acqua (lo strato scende e si taglia al galleggiamento)
    const rise = (key: string, opacity: number, r: number): LayerDraw | null => {
      const info = man.layers[key];
      if (!info || opacity < 0.002) return null;
      return { key, opacity, shift: [0, this.wavePx(key, r)], clipY: info.rect[3] - 3 };
    };
    const gs = rise(POSE.gulpySale, v.gSale, v.gRise);
    if (gs) layers.push(gs);
    const hc = rise(POSE.hatchConta, v.hRise > 0.002 ? 1 : 0, ease(v.hRise));
    if (hc) layers.push(hc);
    // creature sulla barca: salgono e scendono dietro il bordo. Mentre si muovono, la parte che nella posa si
    // vedeva contro il mare passa sotto la barca, che la copre; le mani sul bordo restano sopra e mollano la
    // presa per prime
    const aboard: LayerDraw[] = [];
    for (const [key, p] of this.aboard()) {
      if (!has(key) || p < 0.002) continue;
      if (p >= 0.999) {
        aboard.push({ key });
        continue;
      }
      const shift: [number, number] = [0, this.sinkPx(key, p)];
      layers.push({ key, shift, part: 'back' });
      const hands = smooth01((p - 0.75) / 0.25);
      if (hands > 0.002) aboard.push({ key, shift, part: 'front', opacity: hands });
    }
    layers.push('boat');
    if (sim.cfg.battery && has('battery')) {
      layers.push('battery');
      // il voltmetro retroilluminato (lo stesso strato col quadrante acceso, dissolto sopra)
      if (has('battery_lit') && this.gaugeGlow > 0.002) layers.push({ key: 'battery_lit', opacity: this.gaugeGlow * GAUGE_LIGHT });
    }
    layers.push(this.rodKey());
    const n = sim.fish;
    if (n > 0) layers.push(n <= 3 ? 'fish2' : n <= 6 ? 'fish5' : 'fish9');
    layers.push(...aboard);
    return layers;
  }

  /** Le creature sulla barca e quanto sono su (1 in posa, 0 sparite dietro il bordo). */
  private aboard(): [string, number][] {
    const v = this.v;
    return [
      [POSE.gulpyPretende, v.gPret],
      [POSE.mollyRight, v.mR],
      [POSE.mollyLeft, v.mL],
      [POSE.robin, v.robin],
    ];
  }

  /** Di quanto (pixel del panorama) è scesa dietro il bordo una creatura sulla barca: p = 1 in posa, 0 sparita. */
  private sinkPx(key: string, p: number): number {
    const info = this.d.stage.man.layers[key];
    return info ? (1 - ease(p)) * (info.rect[3] - info.rect[1] + 8) : 0;
  }

  /** Di quanto è sotto il pelo dell'acqua una creatura in mare (r = 1 tutta fuori): segue anche l'onda, di un soffio. */
  private wavePx(key: string, r: number): number {
    const info = this.d.stage.man.layers[key];
    if (!info) return 0;
    const t = this.d.stage.time;
    const bob = 1.6 * Math.sin(t * 0.9 + key.length) + 0.7 * Math.sin(t * 2.3);
    return (1 - r) * (info.rect[3] - info.rect[1]) + bob;
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

  /** La canna da disegnare: dritta, piegata all'abboccata, piegatissima in recupero; nella frustata del lancio flette. */
  private rodKey(): string {
    const f = this.sim.fishing;
    const bend = f.bend;
    const whip = f.phase === 'casting' && this.castT >= CAST_LOAD + 0.03 && this.castT < CAST_WHIP + 0.06;
    return bend >= 1.4 ? 'rod2' : bend >= 0.5 || whip ? 'rod1' : 'rod0';
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
    const tip = man.layers[this.rodKey()]?.tip ?? man.points.rodTip;
    const hang: Vec3 = [tip[0], tip[1], tip[2] - 0.42];
    let end: Vec3 | null = null;
    let sag = 0;
    let light = 1;
    if (f.phase === 'casting' && this.castT >= 0) {
      const ct = this.castT;
      if (ct < CAST_WHIP) {
        const k = ct < CAST_LOAD ? smooth01(ct / CAST_LOAD) : 1 - smooth01((ct - CAST_LOAD) / (CAST_WHIP - CAST_LOAD));
        end = [hang[0] - 0.05 * k, hang[1] - 0.32 * k, hang[2] + 0.18 * k];
      } else {
        // il volo rallenta verso l'arrivo (il filo che corre via frena il galleggiante); dietro, una scia della sua luce
        const u = Math.min(1, (ct - CAST_WHIP) / (FISHING.castTime - CAST_WHIP));
        const land = this.floatAt(FLOAT_FAR);
        const fly = (u: number): Vec3 => {
          const s = 1 - (1 - Math.max(0, u)) ** 1.8;
          return [hang[0] + (land[0] - hang[0]) * s, hang[1] + (land[1] - hang[1]) * s, hang[2] + (land[2] - hang[2]) * s + CAST_ARC * 4 * s * (1 - s)];
        };
        end = fly(u);
        sag = 0.06 * u;
        const trail: Vec3[] = [];
        for (let i = 0; i <= 6; i++) trail.push(fly(u - 0.1 * (1 - i / 6)));
        const c = FLOAT_LIGHT;
        out.strokes.push({ points: trail.reverse(), alpha: 0.5 * (1 - u * 0.6), color: [c[0] * 0.5, c[1] * 0.5, c[2] * 0.5], width: 1.6 });
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
      end = [hang[0] + 0.03 * Math.sin(t * 1.3), hang[1] + 0.04 * Math.sin(t * 0.9 + 1), hang[2]];
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
    if (js) {
      const seq = A.jumpscares[js.killer];
      if (seq && seq.frames.length) {
        const i = Math.min(seq.frames.length - 1, Math.floor(js.t * seq.fps));
        const fr = seq.frames[i]!;
        // Molly è renderizzata a destra: dal lato sinistro l'immagine si specchia
        const flipX = js.killer === 'molly' && this.sim.molly.side === 'left';
        const cam = jumpscareCamera(js.t, seq.fps, seq.frames.length, seq.aspect, this.d.options.reduceFlash ? 0.35 : 1);
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
    // [strato, intensità, di quanto è sceso (pixel del panorama)]: gli occhi scendono con la creatura e
    // spariscono sotto il pelo dell'acqua o dietro il bordo
    const shown: [string, number, number][] = [
      [POSE.gulpySale, v.gSale, this.wavePx(POSE.gulpySale, v.gRise)],
      [POSE.hatchConta, v.hRise > 0.002 ? 1 : 0, this.wavePx(POSE.hatchConta, ease(v.hRise))],
      ...this.aboard().map(([key, p]): [string, number, number] => [key, p > 0.002 ? 1 : 0, this.sinkPx(key, p)]),
    ];
    for (const [key, k, drop] of shown) {
      const info = st.man.layers[key];
      if (!info?.eyes || k < 0.05) continue;
      const water = info.space === 'world' ? pano.latMax - (info.rect[3] - 3) * degPx : null;
      const pulse = 0.85 + 0.15 * Math.sin(st.time * 1.7 + key.length);
      const a = k * dark * pulse;
      for (const e of info.eyes) {
        const yaw = Math.atan2(e[0], e[1]);
        const el = Math.atan2(e[2], Math.hypot(e[0], e[1])) - drop * degPx * D2R;
        const limit = water ?? this.sheerAt(yaw / D2R);
        if (limit === null ? drop > 0 : el / D2R < limit + 0.3) continue;
        const c = Math.cos(el);
        const g: LightGlow = { dir: [c * Math.sin(yaw), c * Math.cos(yaw), Math.sin(el)], color: [0.55 * a, 0.7 * a, 0.62 * a], radius: 0.0022 };
        (info.space === 'world' ? out.world : out.boat).push(g);
      }
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
    const places = this.bino > 0
      ? B.places.filter((p) => Math.abs(((p.yaw - st.view.yaw + 540) % 360) - 180) < p.hfov / 2 + st.view.hfov * 0.75 + 2).map((p) => p.place)
      : [];
    // gli aloni delle luci lontane sono pensati per la vista normale: col binocolo si stringono
    let glows = st.landscapeGlows(eyes.world);
    if (be > 0) {
      const k = 1 - be * (1 - Math.min(1, (st.view.hfov / 90) * 1.6));
      glows = glows.map((g) => ({ ...g, radius: g.radius * k, color: [g.color[0] * (1 - 0.35 * be), g.color[1] * (1 - 0.35 * be), g.color[2] * (1 - 0.35 * be)] }));
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
      // a batteria morta lo schermo del sonar è nero
      sonar: binoOn || this.sim.blackout ? null : this.sonar.canvas,
      gauge: this.sim.cfg.battery && !binoOn ? { angle: this.needleAngle(), alpha: 1 } : null,
      sonarGain: 0.9 + 0.2 * Math.sin(st.time * 2.3),
      ambient: 1 + v.dawn * 1.6,
      exposure: st.brightness + dawnExposure * 0.5,
      flash,
      flashColor,
      glitch,
      fade: 1 - v.dark * 0.9,
      glows,
      boatGlows: binoOn ? [] : tk ? [...eyes.boat, ...tk.glows] : eyes.boat,
    });
  }

  // ───────────────────────── audio ─────────────────────────

  private updateAudio(dt: number): void {
    const a = this.d.audio;
    const sim = this.sim;
    const v = this.v;
    a.setListenerYaw(this.d.stage.view.yaw);
    a.setMuffled(v.tarp * 0.8);
    this.d.sfx.rock(v.rock);
    this.d.sfx.toy(v.toy, dirPos(180 + v.toyX * 35, 1.3, -15));
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
    if (this.creakTimer <= 0) {
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
    // battito del cuore quando qualcosa sta per prenderti
    let danger = 0;
    if (sim.gulpy.state === 'demanding') danger = Math.max(danger, 0.4 + 0.6 * sim.gulpy.phase);
    if (sim.molly.state === 'tantrum') danger = Math.max(danger, 0.6 + 0.4 * (sim.molly.tantrum / sim.cfg.molly.tantrumMax));
    if (sim.hatch.state === 'counting') danger = Math.max(danger, sim.hatch.countProgress * (sim.hide === 'out' ? 1 : 0.4));
    if (sim.hatch.state === 'searching') danger = Math.max(danger, 0.7);
    if (sim.robin?.state === 'stealing') danger = Math.max(danger, sim.fish <= 1 ? 0.8 : 0.45);
    if (sim.blackout && sim.cfg.battery) danger = Math.max(danger, 0.3 + 0.6 * (1 - sim.lullaby / sim.cfg.battery.lullaby));
    if (this.js || this.finished) danger = 0;
    this.heart = approach(this.heart, danger, 2, dt);
    if (this.heart > 0.05 && !this.loops.heart) this.loops.heart = a.play('heartbeat', { loop: true, gain: 0 });
    if (this.loops.heart) {
      this.loops.heart.setGain(this.heart * 0.8, 0.1);
      this.loops.heart.setRate(0.9 + this.heart * 0.5);
      if (this.heart < 0.02) {
        this.loops.heart.stop(0.3);
        this.loops.heart = null;
      }
    }
  }

  /** La chiamata alla radio dell'inizio della notte, con i sottotitoli. */
  private updateRadio(dt: number): void {
    const r = this.radio;
    if (!r) return;
    const prev = r.t;
    r.t += dt;
    const lines = (RADIO[this.nightNo] ?? RADIO[1]!)[this.d.lang];
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
    hud.reel(f.phase === 'reeling' && sim.hide === 'out', f.tension, f.progress, f.strain);
    // il nome di ciò che sta sotto il puntatore
    let target: Target = null;
    if (sim.hide === 'out' && !this.sonarOpen && !this.js && this.mouse.inside) target = this.targetAt(this.mouse.x, this.mouse.y);
    if (target !== this.hoverTarget) {
      this.hoverTarget = target;
      this.d.canvas.style.cursor = target ? 'pointer' : 'crosshair';
    }
    const label = target ? S.labels[target] : '';
    hud.hover(label, this.mouse.x * innerWidth, this.mouse.y * innerHeight);
    hud.showTurn(sim.hide === 'out' && !this.js && !this.finished && this.mouse.inside && this.mouse.y > 0.88);
    hud.setVisible(!this.js);
    // suggerimenti della prima notte
    let hint = '';
    if (!this.finished && !this.js) {
      if (sim.hide === 'in') hint = S.hints.unhide;
      else if (sim.hatch.state === 'counting') hint = S.hints.hide;
      else if (sim.gulpy.canBeFed && sim.fish > 0) hint = sim.facing(YAW.bow, VIEW.bowHalfAngle) ? S.hints.throw : '';
      else if (sim.robin?.present && !sim.blackout) hint = S.hints.robin;
      else if (f.phase === 'bite') hint = S.hints.hook;
      else if (f.phase === 'reeling') hint = S.hints.reel;
      else if (sim.molly.present || sim.gulpy.present) hint = '';
      else if (f.phase === 'idle' && sim.facing(YAW.rod, VIEW.rodHalfAngle) && sim.landedCount < 2) hint = S.hints.cast;
      else if (sim.time < 25 && !sim.facing(YAW.rod, VIEW.rodHalfAngle)) hint = S.look;
    }
    hud.hint(hint);
    // la radio: i sottotitoli spariscono da soli se non c'è chiamata in corso
    if (!this.radio && sim.hatch.state !== 'counting' && sim.hatch.state !== 'boarding') hud.subtitle('', '');
  }
}
