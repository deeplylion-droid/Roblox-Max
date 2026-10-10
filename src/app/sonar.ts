/**
 * Sonar della console: cerchio con la barca al centro, fascio che gira, pesci e ombre delle creature.
 * Disegnato su un canvas che il renderer mappa sullo schermo tondo (e a tutto schermo con Tab).
 */
import { YAW } from '../game/config.ts';
import type { NightSim } from '../game/sim.ts';

interface Blip {
  a: number; // angolo (gradi, 0 = prua, + a destra)
  r: number; // 0..1 dal centro
  size: number;
  kind: 'fish' | 'big';
  life: number;
}

export class Sonar {
  readonly canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private sweep = 0;
  private blips: Blip[] = [];
  private fish: { a: number; r: number; v: number }[] = [];
  onPing: (() => void) | null = null;
  onContact: ((big: boolean) => void) | null = null;
  /** un'ombra di avviso è passata sotto il fascio (bip diverso) */
  onWarn: (() => void) | null = null;

  constructor(size = 384) {
    this.canvas = document.createElement('canvas');
    this.canvas.width = this.canvas.height = size;
    this.ctx = this.canvas.getContext('2d')!;
    for (let i = 0; i < 14; i++) this.fish.push({ a: Math.random() * 360, r: 0.25 + Math.random() * 0.7, v: (Math.random() - 0.5) * 8 });
  }

  /** contatti attuali delle creature: angolo e distanza (0 = sotto la barca, 1 = bordo) */
  private contacts(sim: NightSim): { a: number; r: number; warn?: boolean }[] {
    const out: { a: number; r: number; warn?: boolean }[] = [];
    // avviso: l'ombra grande di chi sta per arrivare, dal suo lato, che si avvicina
    for (const c of sim.incoming()) out.push({ a: c.yaw, r: 0.55 + 0.4 * Math.min(1, c.eta / 5), warn: true });
    const g = sim.gulpy;
    if (g.state === 'rising') out.push({ a: -12, r: 0.75 - 0.5 * g.phase });
    else if (g.state === 'climbing' || g.state === 'demanding' || g.state === 'eating') out.push({ a: 0, r: 0.18 });
    const m = sim.molly;
    if (m.state === 'knocking' || m.present) out.push({ a: m.side === 'left' ? -75 : 75, r: m.state === 'knocking' ? 0.3 : 0.16 });
    const rb = sim.robin;
    if (rb?.present) out.push({ a: YAW.robin, r: rb.state === 'climbing' ? 0.3 : 0.15 });
    const h = sim.hatch;
    if (h.state === 'counting') out.push({ a: 180, r: 0.85 - 0.6 * h.countProgress });
    else if (h.state === 'boarding' || h.state === 'searching') out.push({ a: 180 + (h.lureX ?? 0) * 25, r: 0.12 });
    return out;
  }

  update(dt: number, sim: NightSim): void {
    const prev = this.sweep;
    this.sweep = (this.sweep + dt * 120) % 360; // un giro ogni 3 s
    if (this.sweep < prev) this.onPing?.();
    const lampBoost = [0.6, 1, 1.6][sim.lamp] ?? 1;
    for (const f of this.fish) {
      f.a = (f.a + f.v * dt + 360) % 360;
      f.r += Math.sin(performance.now() / 1700 + f.a) * 0.0006;
    }
    const crossed = (a: number) => {
      const s0 = prev, s1 = this.sweep;
      const x = ((a % 360) + 360) % 360;
      return s0 <= s1 ? x > s0 && x <= s1 : x > s0 || x <= s1;
    };
    for (const f of this.fish) {
      if (crossed(f.a) && Math.random() < 0.55 * lampBoost) this.blips.push({ a: f.a, r: f.r, size: 2.5, kind: 'fish', life: 1 });
    }
    for (const c of this.contacts(sim)) {
      if (crossed(c.a)) {
        this.blips.push({ a: c.a, r: c.r, size: c.warn ? 16 : 9, kind: 'big', life: 1 });
        if (c.warn) this.onWarn?.();
        else this.onContact?.(true);
      }
    }
    for (const b of this.blips) b.life -= dt / 2.8;
    this.blips = this.blips.filter((b) => b.life > 0);
    this.draw();
  }

  private draw(): void {
    const c = this.ctx;
    const S = this.canvas.width;
    const R = S * 0.46;
    const cx = S / 2, cy = S / 2;
    c.globalCompositeOperation = 'source-over';
    c.fillStyle = 'rgba(0, 8, 4, 1)';
    c.fillRect(0, 0, S, S);
    c.strokeStyle = 'rgba(60, 255, 150, 0.22)';
    c.lineWidth = 1.5;
    for (const k of [0.33, 0.66, 1]) {
      c.beginPath();
      c.arc(cx, cy, R * k, 0, Math.PI * 2);
      c.stroke();
    }
    c.beginPath();
    c.moveTo(cx - R, cy);
    c.lineTo(cx + R, cy);
    c.moveTo(cx, cy - R);
    c.lineTo(cx, cy + R);
    c.stroke();
    // scia del fascio
    const a = ((this.sweep - 90) * Math.PI) / 180;
    for (let i = 0; i < 24; i++) {
      const aa = a - (i * Math.PI) / 120;
      c.strokeStyle = `rgba(60, 255, 150, ${0.35 * (1 - i / 24)})`;
      c.lineWidth = 3;
      c.beginPath();
      c.moveTo(cx, cy);
      c.lineTo(cx + Math.cos(aa) * R, cy + Math.sin(aa) * R);
      c.stroke();
    }
    for (const b of this.blips) {
      const ba = ((b.a - 90) * Math.PI) / 180;
      const x = cx + Math.cos(ba) * R * b.r, y = cy + Math.sin(ba) * R * b.r;
      const g = c.createRadialGradient(x, y, 0, x, y, b.size * 2.2);
      const col = b.kind === 'big' ? '255, 120, 90' : '90, 255, 160';
      g.addColorStop(0, `rgba(${col}, ${0.95 * b.life})`);
      g.addColorStop(1, `rgba(${col}, 0)`);
      c.fillStyle = g;
      c.beginPath();
      c.arc(x, y, b.size * 2.2, 0, Math.PI * 2);
      c.fill();
    }
    // la barca al centro
    c.fillStyle = 'rgba(200, 255, 220, 0.9)';
    c.beginPath();
    c.moveTo(cx, cy - 10);
    c.lineTo(cx + 5, cy + 7);
    c.lineTo(cx - 5, cy + 7);
    c.closePath();
    c.fill();
    // scanline
    c.fillStyle = 'rgba(0, 0, 0, 0.18)';
    for (let y = 0; y < S; y += 3) c.fillRect(0, y, S, 1);
  }
}
