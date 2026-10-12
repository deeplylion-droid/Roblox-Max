import { describe, expect, it } from 'vitest';
import type { Manifest } from '../src/engine/assets.ts';
import type { Renderer } from '../src/engine/renderer.ts';
import { Stage } from '../src/app/stage.ts';

// due luci del manifest: la candela dell'edicola (a sinistra, yaw −74°) e il neon (dietro, yaw 167°); in più quelle
// attorno a Soggy, scritte nel codice: il lampione e le lampadine agli scivoli (yaw −167°), la lanterna al relitto
// (yaw 14°), che si vedono solo col binocolo
const man = {
  pano: { width: 4096, height: 1024, latMin: -40, latMax: 50 },
  layers: {},
  lights: {
    candle: [-88.44, 25.91, 2.65],
    neon: [104.98, -454.17, 26.32],
  },
} as unknown as Manifest;

/** Il palcoscenico che guarda verso `yaw` con quel campo visivo (il binocolo: pochi gradi). */
function stage(yaw: number, pitch: number, hfov: number): Stage {
  const s = new Stage({} as Renderer, man);
  s.fog = false;
  s.view.yaw = s.view.targetYaw = yaw;
  s.view.pitch = pitch;
  s.view.hfov = hfov;
  s.view.update(0, 16 / 9);
  return s;
}

const hue = (dir: number[]) => Math.round((Math.atan2(dir[0]!, dir[1]!) * 180) / Math.PI);

describe('Le luci del paesaggio', () => {
  it('a occhio nudo ci sono tutte, anche quelle fuori dallo schermo; il lampione di Soggy no', () => {
    const g = stage(0, -12, 90).landscapeGlows();
    expect(g.map((x) => hue(x.dir)).sort((a, b) => a - b)).toEqual([-74, 167]);
  });

  it('col binocolo sugli scivoli: il lampione e le due lampadine sì, le luci lontane dall’inquadratura no', () => {
    const g = stage(-167, 1.8, 7.5).landscapeGlows([], 1);
    expect(g.map((x) => hue(x.dir))).toEqual([-167, -167, -167]);
    // al relitto c'è la lanterna
    expect(stage(14, 0.4, 11).landscapeGlows([], 1).map((x) => hue(x.dir))).toEqual([14]);
  });

  it('il lampione si accende col binocolo, non tutto d’un colpo', () => {
    const s = stage(-167, 1.8, 7.5);
    const half = s.landscapeGlows([], 0.5)[0]!;
    const full = s.landscapeGlows([], 1)[0]!;
    expect(half.color[0]).toBeCloseTo(full.color[0] / 2);
    expect(s.landscapeGlows([], 0).map((x) => hue(x.dir))).not.toContain(-167);
  });
});
