/**
 * Avvio del gioco. Per ora: visore della scena dalla barca (motore grafico + controlli),
 * su cui si innestano la notte, l'audio e l'interfaccia.
 */
import { loadLayer, loadManifest } from './engine/assets.ts';
import { Renderer, type LightGlow } from './engine/renderer.ts';
import { View } from './engine/view.ts';
import type { Vec3 } from './engine/assets.ts';

const canvas = document.getElementById('scene') as HTMLCanvasElement;

function norm(v: Vec3): Vec3 {
  const l = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / l, v[1] / l, v[2] / l];
}

async function boot(): Promise<void> {
  const man = await loadManifest();
  const r = new Renderer(canvas, man);
  // ?extra=chiave1,chiave2: strati in più (es. le pose delle creature); quelli nel mondo vanno prima della barca
  const params0 = new URLSearchParams(location.search);
  const extra = (params0.get('extra') ?? '').split(',').filter((k) => k && man.layers[k]);
  const worldExtra = extra.filter((k) => man.layers[k]!.space === 'world');
  const boatExtra = extra.filter((k) => man.layers[k]!.space !== 'world');
  const keys = ['world', ...worldExtra, 'boat', 'rod0', 'fish5', ...boatExtra].filter((k) => man.layers[k]);
  for (const k of keys) r.addLayer(await loadLayer(r.gl, man, k));
  const view = new View();
  const params = new URLSearchParams(location.search);
  view.yaw = view.targetYaw = Number(params.get('yaw') ?? 0);
  let lampLevel = Number(params.get('lamp') ?? 1);
  let lampNow = lampLevel;
  let mouseX = 0.5;
  const held = new Set<string>();
  addEventListener('keydown', (e) => {
    held.add(e.key.toLowerCase());
    if (e.key === 'q' || e.key === 'Q') lampLevel = Math.max(0, lampLevel - 1);
    if (e.key === 'e' || e.key === 'E') lampLevel = Math.min(2, lampLevel + 1);
    if (e.key === 's' || e.key === 'ArrowDown') view.targetYaw += 180;
  });
  addEventListener('keyup', (e) => held.delete(e.key.toLowerCase()));
  canvas.addEventListener('mousemove', (e) => (mouseX = e.clientX / innerWidth));
  canvas.addEventListener('mouseleave', () => (mouseX = 0.5));

  const lights = man.lights ?? {};
  const glowDefs: { key: string; color: Vec3; radius: number; anim: (t: number) => number }[] = [
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
  ];

  let last = performance.now();
  const t0 = last;
  function frame(now: number): void {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    const t = (now - t0) / 1000;
    // rotazione: bordi dello schermo (come FNAF) o A/D
    const edge = 0.22;
    let spin = 0;
    if (mouseX < edge) spin = -(((edge - mouseX) / edge) ** 1.5);
    else if (mouseX > 1 - edge) spin = ((mouseX - (1 - edge)) / edge) ** 1.5;
    if (held.has('a') || held.has('arrowleft')) spin = -1;
    if (held.has('d') || held.has('arrowright')) spin = 1;
    view.targetYaw += spin * 160 * dt;
    view.update(dt, r.aspect);
    lampNow += (lampLevel - lampNow) * (1 - Math.exp(-dt * 10));
    const flicker = 1 + 0.03 * Math.sin(t * 31) * Math.sin(t * 17.3) + (Math.random() < 0.004 ? -0.4 : 0);
    const glows: LightGlow[] = [];
    for (const g of glowDefs) {
      const p = lights[g.key];
      if (!p) continue;
      const k = g.anim(t);
      glows.push({ dir: norm(p), color: [g.color[0] * k, g.color[1] * k, g.color[2] * k], radius: g.radius });
    }
    const lampW = [0, 1, 1.7][Math.round(lampNow)] ?? 1;
    r.render(view, {
      time: t,
      ambient: 1,
      lamp: (lampNow < 0.5 ? lampNow * 2 * 1 : lampNow <= 1 ? 1 : 1 + (lampNow - 1) * 0.7) * flicker * (lampW > 0 || lampNow > 0.02 ? 1 : 0),
      lantern: 1 + 0.08 * Math.sin(t * 9.0) * Math.sin(t * 5.3),
      exposure: 1.0,
      fade: 1,
      flash: 0,
      flashColor: [1, 1, 1],
      beamAngle: t * 0.55,
      glows,
      layers: keys,
      sonar: null,
      sonarGain: 1,
      line: null,
    });
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  (window as unknown as { __game: unknown }).__game = { view, renderer: r };
}

boot().catch((e) => {
  console.error(e);
  document.getElementById('ui')!.textContent = String(e);
});
