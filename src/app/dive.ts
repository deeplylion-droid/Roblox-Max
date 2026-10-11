/**
 * L'immersione all'alba (docs/IMMERSIONI.md): scendi con le bombole sotto la barca e nuoti da un posto all'altro
 * come con le telecamere di FNAF. Le grotte sono panorami a 360° (uno strato del mondo a sfera intera) in cui ti
 * guardi attorno; le camerette delle tane sono inquadrature fisse (un panorama parziale che si gira di 30° per parte,
 * deciso l'11 ottobre). I passaggi si cliccano e si passa con una dissolvenza (le bolle e il respiro dell'erogatore). La
 * torcia segue lo sguardo con un piccolo ritardo, l'acqua è torbida (la nebbia del passo dati, le particelle, i raggi
 * dall'alto, un tremolio), il manometro dice quanta aria resta. Nelle tane i mostri dormono: cliccandone uno col pesce
 * glielo lasci, e la notte dopo non viene.
 *
 * Le regole stanno in DiveRun (dive_run.ts), i posti nel file di dati: questo modulo non sa niente dei segnaposto.
 * Un solo posto alla volta sta in memoria: i panorami si caricano quando ci arrivi e si liberano quando te ne vai.
 */
import { ASSET_BASE, type LayerInfo, type LoadedLayer, type PassInfo, type Vec3 } from '../engine/assets.ts';
import type { AudioEngine, Voice } from '../engine/audio.ts';
import { dirPos } from '../engine/audio.ts';
import { textureFromImage, type GL } from '../engine/gl.ts';
import type { LayerDraw } from '../engine/renderer.ts';
import { apply, wrap180 } from '../engine/view.ts';
import type { MonsterId } from '../game/config.ts';
import { STRINGS, type Lang } from '../i18n.ts';
import { DiveRun, type DiveData, type DiveLink, type DivePano, type DivePlace } from './dive_run.ts';
import type { Options } from './save.ts';
import type { Stage } from './stage.ts';

export const DIVE_DATA_URL = ASSET_BASE + 'img/immersioni.json';

/**
 * I suoni delle immersioni. Quelli nuovi non ci sono ancora: quando arrivano basta metterli nel manifest dell'audio
 * con questi nomi e il motore li usa al posto dei ripieghi (i suoni della barca, ovattati).
 * TODO suoni nuovi (da fare e approvare, docs/AUDIO.md):
 *  - dive_amb: l'ambiente sott'acqua (il ronzio sordo, la roccia che scricchiola lontano);
 *  - dive_breath: il respiro nell'erogatore, in loop (inspira, espira con le bolle);
 *  - dive_bubbles: la raffica di bolle delle dissolvenze fra un posto e l'altro;
 *  - dive_air_low: l'avviso del manometro;
 *  - dive_sleep_<mostro>: il respiro nel sonno di ognuno (dive_sleep_gulpy, dive_sleep_molly…), le conchiglie di Fangy;
 *  - dive_mother: il respiro enorme dal fondo della grotta grande.
 */
const SND = {
  amb: ['dive_amb', 'amb_drone'],
  breath: ['dive_breath'],
  bubbles: ['dive_bubbles', 'splash_s1'],
  descend: ['dive_descend', 'splash_big'],
  airLow: ['dive_air_low', 'sonar_warn'],
  offer: ['dive_offer', 'plop'],
  mother: ['dive_mother'],
} as const;

/** Il respiro nel sonno: il suono nuovo, o un ripiego dove c'è (Gulpy ha già il respiro della notte). */
function sleepSounds(who: MonsterId): string[] {
  return [`dive_sleep_${who}`, ...(who === 'gulpy' ? ['gulpy_breath_1', 'gulpy_breath_2'] : [])];
}

export interface DiveResult {
  /** il mostro sfamato (dorme la notte dopo) */
  fed: MonsterId | null;
  /** le tane viste */
  dens: MonsterId[];
}

export interface DiveDeps {
  stage: Stage;
  audio: AudioEngine;
  ui: HTMLElement;
  canvas: HTMLCanvasElement;
  lang: Lang;
  options: Options;
  data: DiveData;
  /** la notte che viene dopo questa alba */
  nextNight: number;
  /** pesci avanzati alle sei oltre la quota */
  spare: number;
  onEnd: (r: DiveResult) => void;
}

const D2R = Math.PI / 180;
const MONSTER_NAME: Record<MonsterId, string> = { gulpy: 'Gulpy', molly: 'Molly', hatch: 'Hatch', robin: 'Robin', archie: 'Archie', lampy: 'Lampy', fangy: 'Fangy' };

function dirOf(yaw: number, pitch: number): Vec3 {
  const a = yaw * D2R, e = pitch * D2R;
  return [Math.sin(a) * Math.cos(e), Math.cos(a) * Math.cos(e), Math.sin(e)];
}

function angle(a: Vec3, b: Vec3): number {
  return Math.acos(Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]))) / D2R;
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, text = ''): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  e.className = cls;
  if (text) e.textContent = text;
  return e;
}

async function texture(gl: GL, file: string, wrap: number): Promise<WebGLTexture> {
  const r = await fetch(ASSET_BASE + 'img/' + file);
  if (!r.ok) throw new Error(`asset mancante: ${file}`);
  const bmp = await createImageBitmap(await r.blob(), { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
  const t = textureFromImage(gl, bmp, { wrapS: wrap });
  bmp.close();
  return t;
}

/** Uno strato del posto da disegnare, con il periodo del respiro se è una toppa che si dissolve sopra la posa. */
interface Draw {
  d: LayerDraw;
  breath?: number;
}

/** Come Promise.all per le texture di uno strato, ma se una non si carica cancella quelle già create (e rifiuta). */
async function settle(gl: GL, ps: (Promise<WebGLTexture> | null)[]): Promise<(WebGLTexture | null)[]> {
  const res = await Promise.allSettled(ps.map((p) => p ?? Promise.resolve(null)));
  const failed = res.find((x): x is PromiseRejectedResult => x.status === 'rejected');
  const ok = res.map((x) => (x.status === 'fulfilled' ? x.value : null));
  if (failed) {
    for (const t of ok) if (t) gl.deleteTexture(t);
    throw failed.reason;
  }
  return ok;
}

type Phase = 'loading' | 'in' | 'look' | 'out' | 'ascend' | 'done';

/** Un punto cliccabile del posto, con la sua etichetta sullo schermo. */
interface Spot {
  dir: Vec3;
  r: number;
  link?: DiveLink;
  sleeper?: boolean;
  el: HTMLDivElement | null;
}

export class Dive {
  readonly run: DiveRun;
  private phase: Phase = 'loading';
  /** luminosità della scena (dissolvenze), 0..1 */
  private fade = 0;
  /** le bolle dell'erogatore davanti alla maschera, 0..1 */
  private burst = 1;
  private time = 0;
  /** chiavi degli strati del posto caricato (nel renderer) */
  private keys: string[] = [];
  private draws: Draw[] = [];
  /** gli stessi strati come li vuole il renderer (non si rifà la lista a ogni fotogramma) */
  private layerList: LayerDraw[] = [];
  private spots: Spot[] = [];
  private hover: Spot | null = null;
  private goingTo: string | null = null;
  private torchYaw = 0;
  private torchPitch = 0;
  private held = new Set<string>();
  private mouse = { x: 0.5, y: 0.5, inside: false };
  private listeners: [EventTarget, string, EventListener][] = [];
  private loops: Voice[] = [];
  private breathTimer = 2;
  private root: HTMLDivElement;
  private gauge: HTMLCanvasElement;
  private capEl: HTMLDivElement;
  private hintEl: HTMLDivElement;
  private spotsEl: HTMLDivElement;
  private buttonsEl: HTMLDivElement;
  private confirmEl: HTMLDivElement | null = null;
  private capTimer = 0;
  private hintTimer = 0;
  /** dove sta l'ago disegnato (per non ridisegnare il manometro quando non si muove) */
  private gaugeShown = -1;
  /** i bordi dello schermo girano lo sguardo; dopo un tasto di direzione non più finché il mouse non si muove (come
   *  sulla barca: se il mouse era rimasto fermo nella fascia del bordo, la vista continuava a girare da sola) */
  private edgeArmed = true;
  private destroyed = false;

  constructor(private d: DiveDeps) {
    this.run = new DiveRun(d.data, d.nextNight, d.spare);
    const S = this.S;
    this.root = el('div', 'hud dive-hud');
    this.spotsEl = el('div', 'dive-spots');
    this.buttonsEl = el('div', 'dive-buttons');
    this.gauge = el('canvas', 'dive-gauge');
    this.gauge.width = this.gauge.height = 176;
    this.capEl = el('div', 'dive-cap');
    this.hintEl = el('div', 'hud-hint', S.dive.hint);
    const up = el('button', 'dive-up', S.dive.ascend);
    up.type = 'button';
    up.addEventListener('click', (e) => {
      e.stopPropagation();
      this.ascend();
    });
    this.root.append(this.spotsEl, this.buttonsEl, this.gauge, this.capEl, this.hintEl, up);
    d.ui.appendChild(this.root);
  }

  get S() {
    return STRINGS[this.d.lang];
  }

  async start(): Promise<void> {
    const v = this.d.stage.view;
    v.swell = 0;
    v.rockBoost = 0;
    v.hfov = 90;
    this.bind();
    for (const ids of [SND.amb, SND.breath]) {
      const id = this.sound(ids);
      // l'ambiente della barca, sott'acqua, si sente solo ovattato
      if (id) this.loops.push(...[this.d.audio.play(id, { loop: true, fadeIn: 2, gain: 0.8, lowpass: id.startsWith('dive_') ? undefined : 380 })].filter((x): x is Voice => !!x));
    }
    this.play(SND.descend, { gain: 0.8, lowpass: 900 });
    this.caption(this.S.dive.loading, 30);
    // se il primo posto non si carica l'errore arriva all'App, che passa alla notte dopo (le texture sono già liberate)
    await this.load(this.run.place);
    this.arrive();
  }

  // ───────────────────────── posti ─────────────────────────

  /**
   * Carica il panorama del posto (e i suoi strati) nel renderer, liberando prima quello di adesso (un posto solo in
   * memoria). Non tocca DiveRun: si entra nel posto (aria, tane viste) solo quando il caricamento è riuscito. Se un file
   * manca, libera le texture che aveva già creato e rifiuta.
   */
  private async load(id: string): Promise<void> {
    this.unload();
    const p = this.d.data.places[id]!;
    const r = this.d.stage.renderer;
    const gl = r.gl;
    const man = this.d.stage.man;
    const state = p.den ? this.run.denState(p.den) : null;
    const pano: DivePano = state === 'empty' && p.panoEmpty ? p.panoEmpty : p.pano;
    // il panorama del posto ha le sue latitudini: il riquadro si esprime in pixel del panorama del mondo
    const W = man.pano.width, H = man.pano.height;
    const toWorldY = (lat: number) => ((man.pano.latMax - lat) / (man.pano.latMax - man.pano.latMin)) * H;
    const lonMin = p.lonMin ?? -180, lonMax = p.lonMax ?? 180;
    const rectOf = (x0: number, y0: number, x1: number, y1: number): [number, number, number, number] => {
      const [pw, ph] = p.size;
      const lat = (y: number) => p.latMax - (y / ph) * (p.latMax - p.latMin);
      const x = (px: number) => (0.5 + (lonMin + (px / pw) * (lonMax - lonMin)) / 360) * W;
      return [x(x0), toWorldY(lat(y0)), x(x1), toWorldY(lat(y1))];
    };
    const fullPano = lonMax - lonMin >= 360;
    const layer = async (key: string, passes: Partial<Record<'ambient' | 'lamp' | 'lantern', PassInfo>>, data: string | undefined, rect: [number, number, number, number], full: boolean): Promise<LoadedLayer> => {
      const wrap = full ? gl.REPEAT : gl.CLAMP_TO_EDGE;
      const info: LayerInfo = { space: 'world', yaw: p.yaw ?? 0, rect, passes, ...(data ? { data } : {}) };
      const [amb, lamp, lantern, dat] = await settle(gl, [
        passes.ambient ? texture(gl, passes.ambient.file, wrap) : null,
        passes.lamp ? texture(gl, passes.lamp.file, wrap) : null,
        passes.lantern ? texture(gl, passes.lantern.file, wrap) : null,
        data ? texture(gl, data, wrap) : null,
      ]);
      return { key, info, amb: amb!, lamp: lamp!, lantern: lantern!, data: dat! };
    };
    const loads: Promise<{ l: LoadedLayer; draw: Draw }>[] = [];
    const panoKey = `dive:${id}`;
    const { data, ...passes } = pano;
    loads.push(layer(panoKey, passes, data, rectOf(0, 0, p.size[0], p.size[1]), fullPano).then((l) => ({ l, draw: { d: { key: panoKey, ...(p.tint ? { tint: p.tint } : {}) } } })));
    if (state === 'asleep') {
      p.sleeper?.layers?.forEach((s, i) => {
        const key = `${panoKey}:${i}`;
        loads.push(layer(key, s.passes, undefined, rectOf(...s.rect), false).then((l) => ({ l, draw: { d: { key }, breath: s.breath } })));
      });
    }
    const res = await Promise.allSettled(loads);
    const done = res.flatMap((x) => (x.status === 'fulfilled' ? [x.value] : []));
    const failed = res.find((x): x is PromiseRejectedResult => x.status === 'rejected');
    if (failed || this.destroyed) {
      for (const { l } of done) for (const t of [l.amb, l.lamp, l.lantern, l.data]) if (t) gl.deleteTexture(t);
      if (failed) throw failed.reason;
      return;
    }
    for (const { l, draw } of done) {
      r.addLayer(l);
      this.keys.push(l.key);
      this.draws.push(draw);
      this.layerList.push(draw.d);
    }
  }

  private unload(): void {
    for (const k of this.keys) this.d.stage.renderer.removeLayer(k);
    this.keys = [];
    this.draws = [];
    this.layerList = [];
    this.spotsEl.replaceChildren();
    this.buttonsEl.replaceChildren();
    this.spots = [];
    this.hover = null;
  }

  private buildSpots(p: DivePlace, state: ReturnType<DiveRun['denState']> | null): void {
    const yaw0 = p.yaw ?? 0;
    this.buttonsEl.replaceChildren();
    for (const l of this.run.visibleLinks()) {
      const label = l.label ? this.S.dive.links[l.label] : undefined;
      if (l.button) {
        // un tasto sullo schermo (nelle inquadrature fisse, «torna alla grotta»)
        const b = el('button', 'dive-back', label ?? '←');
        b.type = 'button';
        b.addEventListener('click', (e) => {
          e.stopPropagation();
          if (!this.confirmEl) this.follow(l);
        });
        this.buttonsEl.append(b);
        continue;
      }
      const e = el('div', 'dive-spot');
      if (label) e.append(el('span', '', label));
      this.spotsEl.append(e);
      this.spots.push({ dir: dirOf(l.yaw + yaw0, l.pitch), r: l.r, link: l, el: e });
    }
    if (state === 'asleep' && p.sleeper) this.spots.push({ dir: dirOf(p.sleeper.yaw + yaw0, p.sleeper.pitch), r: p.sleeper.r, sleeper: true, el: null });
  }

  /** Appena arrivati in un posto (caricato, e già dentro in DiveRun): i punti cliccabili, lo sguardo, la dissolvenza in
   *  entrata, le didascalie. Se intanto è partita la risalita (il tasto, l'aria finita) non si arriva più. */
  private arrive(): void {
    if (this.destroyed || this.phase === 'ascend' || this.phase === 'done') return;
    const p = this.run.current;
    this.buildSpots(p, p.den ? this.run.denState(p.den) : null);
    this.capEl.classList.remove('show');
    const v = this.d.stage.view;
    const look = p.frame ?? p.look;
    if (look) {
      v.yaw = v.targetYaw = look.yaw + (p.yaw ?? 0);
      v.pitch = look.pitch;
      this.torchYaw = v.yaw;
      this.torchPitch = v.pitch;
    }
    this.phase = 'in';
    if (p.den && this.run.denState(p.den) === 'empty') this.caption(this.S.dive.emptyDen, 5);
    this.breathTimer = 1.5;
  }

  private go(to: string): void {
    const ok = this.run.canEnter(to);
    if (ok === 'tooFar') {
      this.caption(this.S.dive.tooFar, 3.5);
      return;
    }
    if (ok !== 'ok' || this.phase !== 'look') return;
    this.goingTo = to;
    this.phase = 'out';
    this.hintEl.classList.remove('show');
    this.play(SND.bubbles, { gain: 0.6, lowpass: 700 });
  }

  /** Al buio: carica il posto e ci entra. Se non si carica si torna dov'eri (ricaricandolo: quello di prima è già stato
   *  liberato), e se nemmeno quello si carica si risale. Senza aria spesa né tane contate per il posto mancato. */
  private travel(to: string): void {
    const from = this.run.place;
    this.load(to).then(
      () => {
        if (this.phase !== 'loading') return;
        this.run.enter(to);
        this.arrive();
      },
      (e: unknown) => {
        console.error(e);
        if (this.phase !== 'loading' || this.destroyed) return;
        this.load(from).then(
          () => {
            this.arrive();
            this.caption(this.S.dive.blocked, 4);
          },
          (e2: unknown) => {
            console.error(e2);
            this.ascend();
          },
        );
      },
    );
  }

  private ascend(): void {
    if (this.phase === 'ascend' || this.phase === 'done') return;
    this.closeConfirm();
    this.phase = 'ascend';
    this.play(SND.bubbles, { gain: 0.8, lowpass: 900 });
  }

  // ───────────────────────── il pesce ─────────────────────────

  private offer(): void {
    const who = this.run.current.den;
    if (!who) return;
    const S = this.S.dive;
    if (this.run.fed) return this.caption(S.alreadyFed, 3);
    if (this.run.fish <= 0) return this.caption(S.noFish, 4);
    const box = el('div', 'dive-confirm');
    box.append(el('p', '', S.offer(MONSTER_NAME[who])));
    const yes = el('button', '', S.offerYes);
    const no = el('button', '', S.offerNo);
    yes.type = no.type = 'button';
    yes.addEventListener('click', (e) => {
      e.stopPropagation();
      this.closeConfirm();
      if (this.run.feed() === 'ok') {
        // TODO render: il pesce posato accanto al letto (una toppa nella tana, quando ci sono le camerette vere)
        this.play(SND.offer, { gain: 0.7, lowpass: 600 });
        this.caption(S.offered(MONSTER_NAME[who]), 5);
      }
    });
    no.addEventListener('click', (e) => {
      e.stopPropagation();
      this.closeConfirm();
    });
    const row = el('div', 'row');
    row.append(yes, no);
    box.append(row);
    this.confirmEl = box;
    this.root.append(box);
  }

  private closeConfirm(): void {
    this.confirmEl?.remove();
    this.confirmEl = null;
  }

  // ───────────────────────── input ─────────────────────────

  private on(t: EventTarget, ev: string, fn: (e: Event) => void): void {
    t.addEventListener(ev, fn as EventListener);
    this.listeners.push([t, ev, fn as EventListener]);
  }

  private bind(): void {
    const c = this.d.canvas;
    this.on(window, 'keydown', (e) => {
      const k = (e as KeyboardEvent).key.toLowerCase();
      this.held.add(k);
      if (['a', 'd', 'w', 's', 'arrowleft', 'arrowright', 'arrowup', 'arrowdown'].includes(k)) this.edgeArmed = false;
      if (k === 'escape') this.closeConfirm();
    });
    this.on(window, 'keyup', (e) => this.held.delete((e as KeyboardEvent).key.toLowerCase()));
    this.on(window, 'blur', () => this.held.clear());
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
    this.on(c, 'mousedown', (e) => {
      if ((e as MouseEvent).button !== 0 || this.confirmEl || this.phase !== 'look') return;
      const h = this.hover;
      if (!h) return;
      if (h.sleeper) this.offer();
      else if (h.link) this.follow(h.link);
    });
  }

  /** Segue un passaggio (o la risalita, o una cosa da guardare). */
  private follow(l: DiveLink): void {
    if (this.phase !== 'look') return;
    if (l.ascend) this.ascend();
    else if (l.to) this.go(l.to);
    else if (l.note) {
      this.caption(this.S.dive.notes[l.note] ?? '', 5);
      if (l.note === 'mother') this.play(SND.mother, { gain: 0.9 });
    }
  }

  // ───────────────────────── aggiornamento ─────────────────────────

  update(dt: number): void {
    if (this.destroyed) return;
    this.time += dt;
    const st = this.d.stage;
    const v = st.view;
    // sguardo: bordi dello schermo, A/D, W/S (anche in su e in giù, per vedere la luce e il fondo)
    if (!this.confirmEl && this.phase !== 'ascend') {
      const edge = 0.2;
      let spin = 0, tilt = 0;
      const { x: mx, y: my } = this.mouse;
      if (this.mouse.inside && this.edgeArmed) {
        if (mx < edge) spin = -(((edge - mx) / edge) ** 1.5);
        else if (mx > 1 - edge) spin = ((mx - (1 - edge)) / edge) ** 1.5;
        if (my < edge * 0.8) tilt = ((edge * 0.8 - my) / (edge * 0.8)) ** 1.5;
        else if (my > 1 - edge * 0.8) tilt = -(((my - (1 - edge * 0.8)) / (edge * 0.8)) ** 1.5);
      }
      const k = this.held;
      if (k.has('a') || k.has('arrowleft')) spin = -1;
      if (k.has('d') || k.has('arrowright')) spin = 1;
      if (k.has('w') || k.has('arrowup')) tilt = 1;
      if (k.has('s') || k.has('arrowdown')) tilt = -1;
      // sott'acqua ci si gira più piano che sulla barca
      v.targetYaw += spin * 110 * this.d.options.sensitivity * dt;
      v.pitch = Math.max(-60, Math.min(60, v.pitch + tilt * 60 * this.d.options.sensitivity * dt));
    }
    // inquadratura fissa (le camerette): lo sguardo resta nel campo, ±yawRange e ±pitchRange attorno al centro
    const fr = this.phase === 'loading' ? undefined : this.run.current.frame;
    if (fr) {
      const c = fr.yaw + (this.run.current.yaw ?? 0);
      const off = wrap180(v.targetYaw - c);
      v.targetYaw = c + Math.max(-fr.yawRange, Math.min(fr.yawRange, off));
      v.pitch = Math.max(fr.pitch - fr.pitchRange, Math.min(fr.pitch + fr.pitchRange, v.pitch));
      v.hfov = 90;
    }
    // si galleggia: un ondeggiare lento
    const t = this.time;
    v.swayYaw = 0.6 * Math.sin(t * 0.37) + 0.25 * Math.sin(t * 0.91 + 1.3);
    v.swayPitch = 0.5 * Math.sin(t * 0.29 + 2.0) + 0.2 * Math.sin(t * 0.77);
    st.update(dt);
    // la torcia segue lo sguardo con un piccolo ritardo, e la mano trema appena
    const lag = 1 - Math.exp(-dt * 5);
    this.torchYaw = wrap180(this.torchYaw + wrap180(v.yaw - this.torchYaw) * lag);
    this.torchPitch += (v.pitch - this.torchPitch) * lag;

    // dissolvenze
    switch (this.phase) {
      case 'in':
        this.fade = Math.min(1, this.fade + dt / 0.9);
        if (this.fade >= 1) {
          this.phase = 'look';
          if (!this.run.dens.length && this.run.place === this.d.data.start) {
            this.hintEl.classList.add('show');
            this.hintTimer = 8;
          }
        }
        break;
      case 'out':
        this.fade = Math.max(0, this.fade - dt / 0.7);
        if (this.fade <= 0 && this.goingTo) {
          const to = this.goingTo;
          this.goingTo = null;
          this.phase = 'loading';
          this.travel(to);
        }
        break;
      case 'ascend':
        this.fade = Math.max(0, this.fade - dt / 1.6);
        if (this.fade <= 0) {
          this.phase = 'done';
          this.d.onEnd({ fed: this.run.fed, dens: [...this.run.dens] });
        }
        break;
      default:
        break;
    }
    const wantBurst = this.phase === 'out' || this.phase === 'ascend' || this.phase === 'loading' ? 1 : this.phase === 'in' ? 1 - this.fade : 0;
    this.burst += (wantBurst - this.burst) * (1 - Math.exp(-dt * 6));
    if (this.burst < 0.01) this.burst = 0;

    // l'aria
    this.run.update(dt);
    for (const e of this.run.drainEvents()) {
      if (e.t === 'airLow') {
        this.caption(this.S.dive.airLow, 4);
        this.play(SND.airLow, { gain: 0.6, lowpass: 1200 });
      } else if (e.t === 'airOut') {
        this.caption(this.S.dive.airOut, 4);
        this.ascend();
      }
    }

    // il respiro del mostro che dorme
    const p = this.run.current;
    if (this.phase === 'look' && p.den && this.run.denState(p.den) === 'asleep') {
      this.breathTimer -= dt;
      if (this.breathTimer <= 0) {
        this.breathTimer = 4.2;
        const s = p.sleeper;
        this.play(sleepSounds(p.den), { gain: 0.5, lowpass: 600, ...(s ? { pos: dirPos(s.yaw + (p.yaw ?? 0), 3, s.pitch) } : {}) });
      }
    }
    if (this.hintTimer > 0) {
      this.hintTimer -= dt;
      if (this.hintTimer <= 0) this.hintEl.classList.remove('show');
    }
    if (this.capTimer > 0) {
      this.capTimer -= dt;
      if (this.capTimer <= 0) this.capEl.classList.remove('show');
    }
    this.updateSpots();
    this.drawGauge();
  }

  private updateSpots(): void {
    const v = this.d.stage.view;
    const look = this.phase === 'look' && !this.confirmEl;
    let best: Spot | null = null;
    if (look && this.mouse.inside) {
      const m = apply(v.motion, v.unproject(this.mouse.x, 1 - this.mouse.y));
      let bestA = Infinity;
      for (const s of this.spots) {
        const a = angle(m, s.dir);
        if (a < s.r && a < bestA) {
          bestA = a;
          best = s;
        }
      }
    }
    if (best !== this.hover) this.d.canvas.style.cursor = best ? 'pointer' : '';
    this.hover = best;
    for (const s of this.spots) {
      if (!s.el) continue;
      const q = look ? v.project(s.dir, true) : null;
      const on = !!q && q[0] > -0.1 && q[0] < 1.1 && q[1] > -0.1 && q[1] < 1.1;
      s.el.classList.toggle('show', on);
      s.el.classList.toggle('hover', s === best);
      if (on) s.el.style.transform = `translate(${(q[0] * 100).toFixed(2)}vw, ${((1 - q[1]) * 100).toFixed(2)}vh)`;
    }
  }

  /** Il manometro delle bombole: un ago come quello del voltmetro della batteria (TODO render: il quadrante vero). */
  private drawGauge(): void {
    // l'ago trema solo quando l'aria è poca: altrimenti si ridisegna solo quando si muove
    const air = this.run.air;
    const shake = air < 0.2 ? 0.02 * Math.sin(this.time * 37) * Math.sin(this.time * 11.3) : 0;
    const f = Math.max(0, Math.min(1, air)) + shake;
    if (Math.abs(f - this.gaugeShown) < 0.0015) return;
    this.gaugeShown = f;
    const g = this.gauge.getContext('2d');
    if (!g) return;
    const n = this.gauge.width, c = n / 2, R = n * 0.42;
    g.clearRect(0, 0, n, n);
    g.fillStyle = 'rgba(18,22,20,0.82)';
    g.strokeStyle = 'rgba(200,190,160,0.55)';
    g.lineWidth = 3;
    g.beginPath();
    g.arc(c, c, R + 8, 0, Math.PI * 2);
    g.fill();
    g.stroke();
    const a0 = -Math.PI * 1.25, a1 = Math.PI * 0.25; // da sinistra in basso (vuoto) a destra in basso (pieno)
    const at = (f: number) => a0 + (a1 - a0) * f;
    // la zona rossa e le tacche
    g.lineWidth = 7;
    g.strokeStyle = 'rgba(170,30,25,0.8)';
    g.beginPath();
    g.arc(c, c, R - 6, at(0), at(0.18));
    g.stroke();
    g.strokeStyle = 'rgba(220,210,180,0.7)';
    g.lineWidth = 2;
    for (let i = 0; i <= 10; i++) {
      const a = at(i / 10), l = i % 5 === 0 ? 14 : 8;
      g.beginPath();
      g.moveTo(c + Math.cos(a) * (R - 2), c + Math.sin(a) * (R - 2));
      g.lineTo(c + Math.cos(a) * (R - 2 - l), c + Math.sin(a) * (R - 2 - l));
      g.stroke();
    }
    g.fillStyle = 'rgba(220,210,180,0.75)';
    g.font = `${Math.round(n * 0.085)}px Limelight, Georgia, serif`;
    g.textAlign = 'center';
    g.fillText(this.S.dive.air, c, c + R * 0.55);
    // l'ago
    const a = at(f);
    g.strokeStyle = '#8c1a12';
    g.lineWidth = 3.5;
    g.beginPath();
    g.moveTo(c - Math.cos(a) * 10, c - Math.sin(a) * 10);
    g.lineTo(c + Math.cos(a) * (R - 12), c + Math.sin(a) * (R - 12));
    g.stroke();
    g.fillStyle = '#111';
    g.beginPath();
    g.arc(c, c, 6, 0, Math.PI * 2);
    g.fill();
  }

  render(): void {
    if (this.destroyed) return;
    const st = this.d.stage;
    const w = this.d.data.water;
    const p = this.run.current;
    // le toppe del respiro si dissolvono sopra la posa
    for (const dr of this.draws) if (dr.breath) dr.d.opacity = 0.5 - 0.5 * Math.cos((this.time / dr.breath) * Math.PI * 2);
    const tdir = dirOf(this.torchYaw + 0.4 * Math.sin(this.time * 2.3), this.torchPitch + 0.3 * Math.sin(this.time * 1.7));
    const yaw0 = p.yaw ?? 0;
    const bubbles = p.den && this.run.denState(p.den) === 'asleep' && p.sleeper?.bubbles ? [{ dir: dirOf(p.sleeper.bubbles.yaw + yaw0, p.sleeper.bubbles.pitch), k: 1 }] : [];
    st.frame({
      layers: this.layerList,
      ambient: 1,
      lamp: 0,
      lantern: 1 + 0.04 * Math.sin(this.time * 13) * Math.sin(this.time * 7.1),
      exposure: st.brightness + w.exposure,
      fade: this.fade,
      glows: [],
      fog: { color: w.fog, density: w.fogDensity },
      torch: { dir: tdir, cos: Math.cos(w.torchAngle * D2R) },
      water: {
        rayColor: w.rayColor,
        rays: p.rays ?? 0.3,
        snowColor: w.snowColor,
        snow: 1,
        glowColor: w.glowColor,
        torchOn: 1,
        bubbles,
        burst: this.burst,
      },
    });
  }

  // ───────────────────────── varie ─────────────────────────

  private caption(text: string, seconds: number): void {
    if (!text) return;
    this.capEl.textContent = text;
    this.capEl.classList.add('show');
    this.capTimer = seconds;
  }

  /** Il primo suono della lista che esiste (i nuovi prima, poi i ripieghi). */
  private sound(ids: readonly string[]): string | null {
    return ids.find((id) => this.d.audio.has(id)) ?? null;
  }

  private play(ids: readonly string[], o: Parameters<AudioEngine['play']>[1] = {}): void {
    const id = this.sound(ids);
    if (!id) return;
    // i suoni nuovi sono già fatti per stare sott'acqua; i ripieghi della barca si ovattano
    this.d.audio.play(id, id.startsWith('dive_') ? { ...o, lowpass: undefined } : o);
  }

  destroy(): void {
    this.destroyed = true;
    for (const [t, ev, fn] of this.listeners) t.removeEventListener(ev, fn);
    this.listeners = [];
    for (const l of this.loops) l.stop(0.6);
    this.loops = [];
    this.unload();
    this.root.remove();
    this.d.canvas.style.cursor = '';
    const v = this.d.stage.view;
    v.swell = 1;
    v.swayYaw = v.swayPitch = 0;
    v.pitch = -12;
    v.hfov = 90;
  }
}

/** Carica il file dei posti delle immersioni. */
export async function loadDiveData(): Promise<DiveData> {
  const r = await fetch(DIVE_DATA_URL);
  if (!r.ok) throw new Error('dati delle immersioni non trovati');
  return (await r.json()) as DiveData;
}
