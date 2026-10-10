/**
 * La canna da pesca disegnata dal motore: il fusto dal portacanna alla punta, che si piega e frusta con una fisica
 * a molla (il lancio, l'abboccata a strattoni, il recupero che piega secondo la tensione, il filo che si spezza).
 * Il manico e il mulinello, che non si muovono, restano uno strato renderizzato (rod_base). La geometria ricalca
 * tools/render/boat.py build_rod (coordinate dall'occhio del pescatore, metri, spazio della barca).
 */
import type { Vec3 } from '../engine/assets.ts';

/** il portacanna e la punta a riposo (senza il peso della cima), dall'occhio */
const GUN: Vec3 = [0.97, 1.1, -0.51];
const D: Vec3 = [1.05, 2.4, 1.12];
/** raggio del fusto al portacanna; si assottiglia fino a un quarto in punta (come il tubo del render) */
const R0 = 0.011 * 0.97;
const N = 24;
/** quanto la cima resta indietro quando la canna accelera (la frustata del lancio) */
export const ROD_INERTIA = 7.0;

/** asse attorno a cui la canna ruota nel portacanna: orizzontale, di traverso alla canna (+ alza la punta) */
const AXIS: Vec3 = (() => {
  const h = Math.hypot(D[0], D[1]);
  return [D[1] / h, -D[0] / h, 0];
})();

function rotate(p: Vec3, a: number): Vec3 {
  // Rodrigues attorno ad AXIS (passante per GUN)
  const [kx, ky, kz] = AXIS;
  const x = p[0] - GUN[0], y = p[1] - GUN[1], z = p[2] - GUN[2];
  const c = Math.cos(a), s = Math.sin(a);
  const dot = kx * x + ky * y + kz * z;
  const cx = ky * z - kz * y, cy = kz * x - kx * z, cz = kx * y - ky * x;
  return [
    GUN[0] + x * c + cx * s + kx * dot * (1 - c),
    GUN[1] + y * c + cy * s + ky * dot * (1 - c),
    GUN[2] + z * c + cz * s + kz * dot * (1 - c),
  ];
}

/** Un punto del fusto (u da 0 al portacanna a 1 in punta) con la piegatura e la rotazione date. */
export function rodPoint(u: number, bend: number, flex: number, tilt: number): Vec3 {
  // il peso della cima e la piegatura verso l'acqua (abboccata 1, recupero fino a 2): come build_rod, ma continua
  const sag = 0.06 * u * u + bend * 0.22 * u ** 2.2 + Math.max(0, bend - 1) * 0.36 * u ** 3;
  const k = flex * u ** 2.4;
  const p: Vec3 = [
    GUN[0] + D[0] * u - 0.06 * k,
    GUN[1] + D[1] * u - 0.05 * bend * u * u - 0.3 * k,
    GUN[2] + D[2] * u - sag + 0.26 * k,
  ];
  return tilt ? rotate(p, tilt) : p;
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
  /** la canna che ruota un poco nel portacanna (radianti, + punta su): segue il copione con una molla rigida */
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

  /** I punti del fusto dal portacanna alla punta. */
  points(): Vec3[] {
    const out: Vec3[] = [];
    for (let i = 0; i <= N; i++) out.push(rodPoint(i / N, this.bend.v, this.flex.v, this.tilt.v));
    return out;
  }

  /** I raggi del fusto, punto per punto (si assottiglia verso la punta). */
  radii(): number[] {
    const out: number[] = [];
    for (let i = 0; i <= N; i++) out.push(R0 * (1 - (0.75 * (i + 1)) / (N + 1)));
    return out;
  }

  tip(): Vec3 {
    return rodPoint(1, this.bend.v, this.flex.v, this.tilt.v);
  }

  /** Un punto lungo la canna (u da 0 a 1), per gli anelli. */
  at(u: number): Vec3 {
    return rodPoint(u, this.bend.v, this.flex.v, this.tilt.v);
  }
}
