/**
 * La canna da pesca disegnata dal motore: il fusto dal portacanna alla punta, che si piega e frusta con una fisica
 * a molla (il lancio, l'abboccata a strattoni, il recupero che piega secondo la tensione, il filo che si spezza).
 * Il manico, il mulinello e il fusto fin dove esce da dietro il portacanna (U0, visto dall'occhio), che non si
 * muovono, restano uno strato renderizzato (rod_base): da lì il motore disegna il resto, con i colori presi dal render
 * della canna intera (rod_colori.ts). La geometria ricalca tools/render/boat.py build_rod (coordinate dall'occhio
 * del pescatore, metri, spazio della barca). La canna sta nel portacanna: non ruota lì dentro, si piega dopo.
 */
import type { Vec3 } from '../engine/assets.ts';
import { ROD_COLORS } from './rod_colori.ts';

/** il portacanna e la punta a riposo (senza il peso della cima), dall'occhio */
const GUN: Vec3 = [0.97, 1.1, -0.51];
const D: Vec3 = [1.05, 2.4, 1.12];
/** da dove il fusto esce da dietro il portacanna (frazione della canna): fin lì lo copre lo strato del manico */
export const U0 = ROD_COLORS.u0;
const N = ROD_COLORS.points.length - 1;
/** quanto la cima resta indietro quando la canna accelera (la frustata del lancio) */
export const ROD_INERTIA = 7.0;

/** asse attorno a cui la canna si piega su e giù: orizzontale, di traverso alla canna (+ alza la punta) */
const AXIS: Vec3 = (() => {
  const h = Math.hypot(D[0], D[1]);
  return [D[1] / h, -D[0] / h, 0];
})();

/** Il fusto a riposo (il peso della cima, come build_rod). */
function rest(u: number): Vec3 {
  return [GUN[0] + D[0] * u, GUN[1] + D[1] * u, GUN[2] + D[2] * u - 0.06 * u * u];
}

/** dove la canna esce dal portacanna: il perno delle sue flessioni */
const EXIT = rest(U0);

function rotate(p: Vec3, a: number): Vec3 {
  // Rodrigues attorno ad AXIS (passante per EXIT)
  const [kx, ky, kz] = AXIS;
  const x = p[0] - EXIT[0], y = p[1] - EXIT[1], z = p[2] - EXIT[2];
  const c = Math.cos(a), s = Math.sin(a);
  const dot = kx * x + ky * y + kz * z;
  const cx = ky * z - kz * y, cy = kz * x - kx * z, cz = kx * y - ky * x;
  return [
    EXIT[0] + x * c + cx * s + kx * dot * (1 - c),
    EXIT[1] + y * c + cy * s + ky * dot * (1 - c),
    EXIT[2] + z * c + cz * s + kz * dot * (1 - c),
  ];
}

function smooth(a: number, b: number, x: number): number {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

/** Un punto del fusto (u da 0 al portacanna a 1 in punta) con la piegatura data. Da U0 in giù non si muove (è lo
 *  strato del manico); dopo, ogni flessione parte da zero e senza spigolo. */
export function rodPoint(u: number, bend: number, flex: number, tilt: number): Vec3 {
  const w = Math.max(0, (u - U0) / (1 - U0));
  // la piegatura verso l'acqua (abboccata 1, recupero fino a 2)
  const sag = bend * 0.22 * w ** 2.2 + Math.max(0, bend - 1) * 0.36 * w ** 3;
  const k = flex * w ** 2.4;
  const r = rest(u);
  const p: Vec3 = [r[0] - 0.06 * k, r[1] - 0.05 * bend * w * w - 0.3 * k, r[2] - sag + 0.26 * k];
  // il lancio e la ferrata alzano la canna: si piega su a partire dal portacanna (l'angolo cresce nel primo tratto)
  return tilt ? rotate(p, tilt * smooth(0, 0.45, w)) : p;
}

/** Il raggio del fusto al punto u: come il tubo del render (si assottiglia fino a un quarto in punta). */
export function rodRadius(u: number): number {
  return 0.011 * (1 - (0.75 * (1 + 24 * u)) / 25);
}

/** Una molla smorzata (pulsazione w, smorzamento z) che insegue un bersaglio. */
class Spring {
  v = 0;
  vel = 0;
  constructor(
    public w: number,
    public z: number,
  ) {}
  step(target: number, dt: number, push = 0): void {
    const a = this.w * this.w * (target - this.v) - 2 * this.z * this.w * this.vel + push;
    this.vel += a * dt;
    this.v += this.vel * dt;
  }
}

export class Rod {
  /** piegatura verso l'acqua: 0 a riposo, 1 abboccata, 2 recupero sotto sforzo */
  private bend = new Spring(2 * Math.PI * 2.6, 0.32);
  /** la cima: + resta indietro e su (caricata), − scatta in avanti e giù (la frustata) */
  private flex = new Spring(2 * Math.PI * 4.2, 0.2);
  /** quanto la canna si alza piegandosi dal portacanna (radianti, + punta su): segue il copione con una molla rigida */
  private tilt = new Spring(2 * Math.PI * 7, 1.0);
  private tiltVelPrev = 0;

  /** Avanza la fisica: bend e tilt (gradi) sono i bersagli del momento. */
  update(dt: number, bend: number, tiltDeg: number): void {
    const n = Math.max(1, Math.ceil(dt / (1 / 240)));
    const h = dt / n;
    for (let i = 0; i < n; i++) {
      this.tilt.step((tiltDeg * Math.PI) / 180, h);
      // quando la canna accelera la cima resta indietro (inerzia): si flette contro l'accelerazione
      const acc = (this.tilt.vel - this.tiltVelPrev) / h;
      this.tiltVelPrev = this.tilt.vel;
      this.flex.step(0, h, -ROD_INERTIA * acc);
      this.bend.step(bend, h);
    }
  }

  /** Un colpo: uno strattone del pesce (bend > 0 giù), lo scatto del filo che si spezza (bend < 0 su). */
  kick(bend: number, flex = 0): void {
    this.bend.vel += bend;
    this.flex.vel += flex;
  }

  /** I punti del fusto da U0 alla punta (gli stessi dei colori di rod_colori.ts). */
  points(): Vec3[] {
    const out: Vec3[] = [];
    for (let i = 0; i <= N; i++) out.push(this.at(ROD_COLORS.points[i]!.u));
    return out;
  }

  /** I raggi del fusto, punto per punto. */
  radii(): number[] {
    return ROD_COLORS.points.map((p) => rodRadius(p.u));
  }

  tip(): Vec3 {
    return this.at(1);
  }

  /** Un punto lungo la canna (u da 0 a 1), per gli anelli. */
  at(u: number): Vec3 {
    return rodPoint(u, this.bend.v, this.flex.v, this.tilt.v);
  }
}
