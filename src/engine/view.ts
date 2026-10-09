/**
 * Sguardo del pescatore e moto della barca.
 * Assi come i render: x destra, y avanti, z alto. Yaw positivo = girarsi a destra.
 */

export type Mat3 = Float32Array; // colonna-maggiore, come vuole WebGL

const D2R = Math.PI / 180;

function rotZ(deg: number): number[] {
  // ruotare lo sguardo a destra di +yaw: il vettore avanti (0,1,0) va verso +x
  const a = -deg * D2R;
  const c = Math.cos(a), s = Math.sin(a);
  return [c, s, 0, -s, c, 0, 0, 0, 1];
}

function rotX(deg: number): number[] {
  // pitch positivo = guardare in su: (0,1,0) va verso +z
  const a = deg * D2R;
  const c = Math.cos(a), s = Math.sin(a);
  return [1, 0, 0, 0, c, s, 0, -s, c];
}

function rotY(deg: number): number[] {
  // roll positivo = inclinazione verso destra
  const a = deg * D2R;
  const c = Math.cos(a), s = Math.sin(a);
  return [c, 0, -s, 0, 1, 0, s, 0, c];
}

/** a · b per matrici 3×3 colonna-maggiore. */
export function mul(a: number[], b: number[]): number[] {
  const o = new Array(9).fill(0);
  for (let c = 0; c < 3; c++) {
    for (let r = 0; r < 3; r++) {
      let s = 0;
      for (let k = 0; k < 3; k++) s += a[k * 3 + r]! * b[c * 3 + k]!;
      o[c * 3 + r] = s;
    }
  }
  return o;
}

export function apply(m: number[] | Float32Array, v: [number, number, number]): [number, number, number] {
  return [
    m[0]! * v[0] + m[3]! * v[1] + m[6]! * v[2],
    m[1]! * v[0] + m[4]! * v[1] + m[7]! * v[2],
    m[2]! * v[0] + m[5]! * v[1] + m[8]! * v[2],
  ];
}

export function transpose(m: number[]): number[] {
  return [m[0]!, m[3]!, m[6]!, m[1]!, m[4]!, m[7]!, m[2]!, m[5]!, m[8]!];
}

export class View {
  /** gradi */
  yaw = 0;
  targetYaw = 0;
  pitch = -12;
  hfov = 90;
  /** oscillazioni */
  private t = 0;
  rockBoost = 0; // 0..1 (Molly che dondola la barca)
  /** 1 = mare normale, 0 = piatto come uno specchio (la Madre) */
  swell = 1;
  shake = 0;
  private shakeSeed = 0;
  /** matrici risultanti */
  boatRot: number[] = rotZ(0);
  worldRot: number[] = rotZ(0);
  /** moto della barca rispetto al mare: direzione nello spazio barca → spazio mondo */
  motion: number[] = rotZ(0);
  tanX = 1;
  tanY = 0.56;
  /** inclinazione attuale della barca (gradi), utile per l'audio e la UI */
  roll = 0;

  update(dt: number, aspect: number): void {
    this.t += dt;
    // avvicinamento morbido allo yaw desiderato (gira per la via più corta)
    let d = ((this.targetYaw - this.yaw + 540) % 360) - 180;
    const k = 1 - Math.exp(-dt * 14);
    this.yaw += d * k;
    this.yaw = ((this.yaw + 540) % 360) - 180;
    const t = this.t;
    // la barca si muove rispetto al mare (onda lunga + rollio) e la testa respira appena
    const rb = this.rockBoost;
    const sw = this.swell;
    const roll = sw * (1.1 * Math.sin(t * 0.55) + 0.45 * Math.sin(t * 1.37 + 1.2)) + rb * 7.5 * Math.sin(t * 2.1) * (0.7 + 0.3 * Math.sin(t * 0.7));
    const pitch = sw * (0.7 * Math.sin(t * 0.43 + 2.1) + 0.25 * Math.sin(t * 1.1)) + rb * 2.0 * Math.sin(t * 1.6 + 0.5);
    const heave = sw * 0.35 * Math.sin(t * 0.8 + 0.3);
    this.roll = roll;
    this.shakeSeed += dt * 60;
    const sh = this.shake;
    const shx = sh * (Math.sin(this.shakeSeed * 1.7) + Math.sin(this.shakeSeed * 2.9)) * 0.6;
    const shy = sh * (Math.sin(this.shakeSeed * 2.3 + 1) + Math.sin(this.shakeSeed * 3.7)) * 0.6;
    this.shake = Math.max(0, this.shake - dt * 2.2);
    const breath = 0.18 * Math.sin(t * 1.25);
    // spazio barca: solo lo sguardo del pescatore
    this.boatRot = mul(rotZ(this.yaw + shx), mul(rotX(this.pitch + breath + shy), rotY(shx * 0.3)));
    // spazio mondo: la barca rolla/beccheggia rispetto all'orizzonte
    const boatMotion = mul(rotY(roll), rotX(pitch + heave));
    this.motion = boatMotion;
    this.worldRot = mul(boatMotion, this.boatRot);
    this.tanX = Math.tan((this.hfov / 2) * D2R);
    this.tanY = this.tanX / aspect;
    const maxTanY = Math.tan(34 * D2R);
    if (this.tanY > maxTanY) {
      this.tanY = maxTanY;
      this.tanX = maxTanY * aspect;
    }
  }

  /** Direzione (spazio barca, dall'occhio) → coordinate schermo 0..1 (null se dietro). */
  project(dir: [number, number, number], world = false): [number, number] | null {
    const m = transpose(world ? this.worldRot : this.boatRot);
    const c = apply(m, dir);
    if (c[1] <= 1e-4) return null;
    return [0.5 + (c[0] / c[1] / this.tanX) * 0.5, 0.5 + (c[2] / c[1] / this.tanY) * 0.5];
  }

  /** Coordinate schermo 0..1 (y in su) → direzione nello spazio barca. */
  unproject(u: number, v: number): [number, number, number] {
    const x = (u * 2 - 1) * this.tanX;
    const z = (v * 2 - 1) * this.tanY;
    const n = Math.hypot(x, 1, z);
    return apply(this.boatRot, [x / n, 1 / n, z / n]);
  }
}

export function yawOf(dir: [number, number, number]): number {
  return Math.atan2(dir[0], dir[1]) / D2R;
}

export function elevOf(dir: [number, number, number]): number {
  return Math.atan2(dir[2], Math.hypot(dir[0], dir[1])) / D2R;
}
