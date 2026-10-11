import { describe, expect, it } from 'vitest';
import { View } from '../src/engine/view.ts';

/** Lo scatto di W A S D (night.ts, face): la via più corta verso quella direzione, aggiunta allo yaw desiderato. */
function face(v: View, yaw: number): void {
  v.targetYaw += ((((yaw - v.targetYaw) % 360) + 540) % 360) - 180;
}

/** Quanto manca (gradi, 0..180) fra due direzioni. */
function off(a: number, b: number): number {
  return Math.abs(((((a - b) % 360) + 540) % 360) - 180);
}

describe('Vista', () => {
  it('tanti scatti di W A S D sempre nello stesso verso: la vista si ferma ogni volta dove deve', () => {
    for (const dirs of [
      [0, -90, 180, 90], // in senso antiorario (W A S D)
      [0, 90, 180, -90], // in senso orario (W D S A)
    ]) {
      const v = new View();
      for (let i = 0; i < 40; i++) {
        face(v, dirs[i % 4]!);
        for (let f = 0; f < 60; f++) v.update(1 / 60, 16 / 9);
        expect(off(v.yaw, dirs[i % 4]!)).toBeLessThan(1);
      }
    }
  });

  it('girando di continuo (frecce o bordo dello schermo) per tanti giri la vista non scappa', () => {
    for (const dir of [-1, 1]) {
      const v = new View();
      for (let f = 0; f < 60 * 30; f++) {
        v.targetYaw += dir * 150 * (1 / 60);
        const before = v.yaw;
        v.update(1 / 60, 16 / 9);
        // a ogni fotogramma la vista si muove di poco, sempre nel verso giusto
        const step = ((((v.yaw - before) % 360) + 540) % 360) - 180;
        expect(Math.sign(step) === dir || Math.abs(step) < 1e-6).toBe(true);
        expect(Math.abs(step)).toBeLessThan(5);
      }
    }
  });
});
