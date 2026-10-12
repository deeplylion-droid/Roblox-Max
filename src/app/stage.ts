/**
 * Il palcoscenico: renderer, sguardo e luci del paesaggio (faro, boa, neon, finestre).
 * Lo usano sia il menu (sfondo animato) sia la notte di gioco.
 */
import type { Manifest, Vec3 } from '../engine/assets.ts';
import { Renderer, type FrameParams, type LayerDraw, type LightGlow } from '../engine/renderer.ts';
import { View, apply } from '../engine/view.ts';

export function norm(v: Vec3): Vec3 {
  const l = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / l, v[1] / l, v[2] / l];
}

interface GlowDef {
  key: string;
  color: Vec3;
  radius: number;
  anim: (t: number) => number;
  /** solo nel binocolo: le luci messe per i posti visti da vicino (quelle attorno a Soggy), che a occhio nudo non si
   *  vedono; il raggio è già pensato per l'inquadratura stretta (night.ts lo stringe come gli altri) */
  bino?: boolean;
  /** dove sta, dall'occhio, se non è fra le luci del manifest (quelle che esistono solo nelle viste del binocolo: il
   *  render del mondo riscrive le sue luci e le perderebbe) */
  pos?: Vec3;
}

/** Luci del paesaggio che vivono anche nel motore (sfarfallii, lampeggi). */
const GLOWS: GlowDef[] = [
  { key: 'buoy', color: [0.2, 1.0, 0.35], radius: 0.004, anim: (t) => (t % 3.0 < 0.5 ? 2.5 : 0.05) },
  { key: 'mastTop', color: [1.0, 0.08, 0.05], radius: 0.003, anim: (t) => (t % 1.6 < 0.8 ? 1.6 : 0.02) },
  { key: 'mastMid', color: [1.0, 0.08, 0.05], radius: 0.0025, anim: (t) => ((t + 0.8) % 1.6 < 0.8 ? 1.2 : 0.02) },
  { key: 'candle', color: [1.0, 0.45, 0.15], radius: 0.006, anim: (t) => 0.5 + 0.25 * Math.sin(t * 13) * Math.sin(t * 7.3) },
  { key: 'neon', color: [1.0, 0.25, 0.55], radius: 0.02, anim: (t) => (Math.sin(t * 23) > 0.93 ? 0.05 : 0.35) },
  { key: 'deepEnd', color: [0.15, 0.95, 0.8], radius: 0.02, anim: (t) => 0.25 + 0.08 * Math.sin(t * 0.9) },
  { key: 'farmLamp', color: [0.85, 0.92, 1.0], radius: 0.003, anim: () => 0.6 },
  { key: 'wheelBulb', color: [1.0, 0.75, 0.4], radius: 0.002, anim: (t) => (Math.sin(t * 4.1) > 0.7 ? 0.0 : 0.8) },
  { key: 'hotelWindow', color: [1.0, 0.7, 0.35], radius: 0.002, anim: (t) => (Math.floor(t / 7) % 5 === 3 ? 0.0 : 0.5) },
  { key: 'marina', color: [0.5, 0.9, 0.8], radius: 0.03, anim: () => 0.04 },
  // le luci attorno a Soggy (render della sessione del Foxy, tools/render/foxy_binocolo.py; da approvare): il lampione
  // alla base degli scivoli, che ogni tanto perde un colpo; le due lampadine che pendono dal tetto della torre vicino a
  // lui, che si spengono e si riaccendono ognuna per conto suo; la lanterna del relitto, che trema come una fiamma.
  // Il lampione e la lanterna dalle posizioni della scena, le lampadine dalle viste (conta solo la direzione)
  { key: 'soggyLamp', pos: [-95.79, -426.21, 5.95], color: [0.9, 1.0, 0.75], radius: 0.004, anim: (t) => (Math.sin(t * 0.7) * Math.sin(t * 2.9) > 0.9 ? 0.12 : 0.7), bino: true },
  { key: 'soggyBulb1', pos: [-99.13, -427.85, 26.87], color: [1.0, 0.85, 0.6], radius: 0.003, anim: (t) => (Math.sin(t * 5.3) * Math.sin(t * 1.3) > 0.55 ? 0.03 : 0.45), bino: true },
  { key: 'soggyBulb2', pos: [-101.59, -427.27, 26.87], color: [1.0, 0.85, 0.6], radius: 0.003, anim: (t) => (Math.sin(t * 3.1 + 2) * Math.sin(t * 0.9) > 0.6 ? 0.03 : 0.45), bino: true },
  { key: 'soggyLantern', pos: [40.71, 162.8, 2.59], color: [1.0, 0.85, 0.6], radius: 0.004, anim: (t) => 0.55 + 0.2 * Math.sin(t * 11) * Math.sin(t * 6.7), bino: true },
];

export class Stage {
  readonly view = new View();
  time = 0;
  /** livello della lampara mostrato (0..2, morbido) */
  lampShown = 1;
  lampTarget = 1;
  /** calo improvviso della lampara (sfarfallio) */
  lampDip = 0;
  /** batteria quasi scarica (dalla notte 2): la reticella trema e ronza di più (0..1) */
  lampSick = 0;
  /** luminosità scelta nelle opzioni */
  brightness = 1;
  /** l'opzione «Nebbia»: spenta, il panorama è quello di prima e il motore fa la sua nebbia di sempre */
  fog = true;

  constructor(
    readonly renderer: Renderer,
    readonly man: Manifest,
  ) {}

  /** Direzione di un punto attaccato alla barca, nello spazio mondo (per i bagliori coperti dallo scafo). */
  boatToWorld(p: Vec3): Vec3 {
    return norm(apply(this.view.motion, p) as Vec3);
  }

  update(dt: number): void {
    this.time += dt;
    this.view.update(dt, this.renderer.aspect);
    this.lampShown += (this.lampTarget - this.lampShown) * (1 - Math.exp(-dt * 9));
    this.lampDip = Math.max(0, this.lampDip - dt * 3);
  }

  /** Intensità del passo "lampara" in base al livello (0 spenta, 1 bassa, 2 alta) con lo sfarfallio. */
  lampWeight(): number {
    const t = this.time;
    const l = this.lampShown;
    const base = l <= 1 ? l : 1 + (l - 1) * 0.7;
    const sick = this.lampSick;
    const flicker = 1 + (0.03 + 0.09 * sick) * Math.sin(t * 31) * Math.sin(t * 17.3) - 0.07 * sick * Math.abs(Math.sin(t * 61.7) * Math.sin(t * 7.1));
    return Math.max(0, base * flicker * (1 - 0.75 * this.lampDip));
  }

  /** Le luci del paesaggio. `bino` è quanto è alzato il binocolo (0..1): accende quelle che si vedono solo lì e lascia
   *  fuori quelle lontane dall'inquadratura stretta, che non si vedrebbero e toglierebbero posto (16 al massimo). */
  landscapeGlows(extra: LightGlow[] = [], bino = 0): LightGlow[] {
    const lights = this.man.lights ?? {};
    const atm = this.fog ? this.man.atmosfera?.glows : undefined;
    const out: LightGlow[] = [];
    for (const g of GLOWS) {
      const p = g.pos ?? lights[g.key];
      if (!p || atm?.off?.includes(g.key) || (g.bino && bino <= 0)) continue;
      const dir = norm(p);
      if (bino > 0 && !this.onScreen(dir, 0.5)) continue;
      const k = g.anim(this.time) * (atm?.gain ?? 1) * (g.bino ? bino : 1);
      out.push({ dir, color: [g.color[0] * k, g.color[1] * k, g.color[2] * k], radius: g.radius * (atm?.radius ?? 1) });
    }
    return out.concat(extra).slice(0, 16);
  }

  /** La direzione (nel mondo) cade nell'inquadratura, con un margine in frazioni di schermo per l'alone? */
  private onScreen(dir: Vec3, margin: number): boolean {
    const s = this.view.project(dir, true);
    return s !== null && s[0] > -margin && s[0] < 1 + margin && s[1] > -margin && s[1] < 1 + margin;
  }

  frame(p: Partial<FrameParams> & { layers: (string | LayerDraw)[] }): void {
    const t = this.time;
    this.renderer.render(this.view, {
      time: t,
      ambient: 1,
      lamp: this.lampWeight(),
      lantern: 1 + 0.08 * Math.sin(t * 9.0) * Math.sin(t * 5.3),
      exposure: this.brightness,
      fade: 1,
      flash: 0,
      flashColor: [1, 1, 1],
      beamAngle: t * 0.55,
      glows: this.landscapeGlows(),
      sonar: null,
      sonarGain: 1,
      line: null,
      fog: this.fog ? this.man.atmosfera?.fog : undefined,
      ...p,
    });
  }
}
