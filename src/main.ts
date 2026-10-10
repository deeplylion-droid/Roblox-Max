/**
 * Avvio di SPLASHLAND IS CLOSED!: carica i render e l'audio, poi passa la mano all'App
 * (avvertenza → titolo → notte). Con ?yaw=…, ?extra=… o ?viewer apre invece il visore della scena,
 * utile per controllare i render (gli screenshot di scripts/shoot.mjs).
 */
import { App } from './app/app.ts';
import { loadNightAssets } from './app/overlays.ts';
import { loadSave } from './app/save.ts';
import { Screens } from './app/screens.ts';
import { Sfx } from './app/sfx.ts';
import { Stage } from './app/stage.ts';
import { loadLayer, loadManifest } from './engine/assets.ts';
import { AudioEngine } from './engine/audio.ts';
import { Renderer } from './engine/renderer.ts';
import { detectLang } from './i18n.ts';

const canvas = document.getElementById('scene') as HTMLCanvasElement;
const ui = document.getElementById('ui') as HTMLDivElement;

/** Strati della notte, nell'ordine in cui vanno caricati (le pose delle creature possono mancare). */
const GAME_LAYERS = ['world', 'boat', 'rod0', 'rod1', 'rod2', 'fish2', 'fish5', 'fish9', 'gulpy_sale', 'hatch_conta', 'gulpy_pretende', 'molly_destra', 'molly_sinistra', 'battery', 'battery_lit', 'robin_secchio', 'robin_strizza', 'robin_chiusi', 'rod_c1', 'rod_c2', 'rod_m', 'rod_f1', 'rod_f2', 'rod_base',
  'gulpy_mascella_aperta', 'gulpy_mascella_chiusa', 'molly_destra_primo', 'molly_destra_secondo', 'molly_sinistra_primo',
  'molly_sinistra_secondo', 'hatch_bocca_mezza', 'hatch_bocca_chiusa',
  // notte 3: Archie e le sue toppe (la trombetta a metà e tutta, la gola gonfia)
  'archie_soffia', 'archie_trombetta_mezza', 'archie_trombetta_tutta', 'archie_fiato'];

/** ?speed=N accelera il tempo di gioco (per le prove automatiche nel browser senza GPU). */
const SPEED = Math.max(0.1, Number(new URLSearchParams(location.search).get('speed') ?? 1) || 1);

function loop(step: (dt: number) => void): void {
  let last = performance.now();
  const frame = (now: number) => {
    const dt = Math.min(0.05, (now - last) / 1000) * SPEED;
    last = now;
    // il prossimo fotogramma si chiede prima: un errore in un fotogramma non deve fermare il gioco
    requestAnimationFrame(frame);
    step(dt);
  };
  requestAnimationFrame(frame);
}

async function boot(): Promise<void> {
  const params = new URLSearchParams(location.search);
  const save = loadSave();
  const lang = save.lang ?? detectLang();
  const screens = new Screens(ui, lang);
  screens.loading(0);
  const man = await loadManifest();
  const r = new Renderer(canvas, man);
  const stage = new Stage(r, man);
  const viewer = params.has('yaw') || params.has('extra') || params.has('viewer');

  if (viewer) {
    // visore: la scena con gli strati richiesti; ?extra=chiave1,chiave2 per le pose delle creature
    const extra = (params.get('extra') ?? '').split(',').filter((k) => k && man.layers[k]);
    const worldExtra = extra.filter((k) => man.layers[k]!.space === 'world');
    const boatExtra = extra.filter((k) => man.layers[k]!.space !== 'world');
    const keys = ['world', ...worldExtra, 'boat', 'rod0', 'fish5', ...boatExtra].filter((k) => man.layers[k]);
    for (const [i, k] of keys.entries()) {
      r.addLayer(await loadLayer(r.gl, man, k));
      screens.loading((i + 1) / keys.length);
    }
    screens.clear();
    const view = stage.view;
    view.yaw = view.targetYaw = Number(params.get('yaw') ?? 0);
    if (params.has('pitch')) view.pitch = Number(params.get('pitch'));
    if (params.has('fov')) view.hfov = Number(params.get('fov'));
    stage.lampTarget = stage.lampShown = Number(params.get('lamp') ?? 1);
    const held = new Set<string>();
    addEventListener('keydown', (e) => {
      held.add(e.key.toLowerCase());
      if (e.key === 'q' || e.key === 'Q') stage.lampTarget = Math.max(0, stage.lampTarget - 1);
      if (e.key === 'e' || e.key === 'E') stage.lampTarget = Math.min(2, stage.lampTarget + 1);
    });
    addEventListener('keyup', (e) => held.delete(e.key.toLowerCase()));
    loop((dt) => {
      if (held.has('a') || held.has('arrowleft')) view.targetYaw -= 120 * dt;
      if (held.has('d') || held.has('arrowright')) view.targetYaw += 120 * dt;
      stage.update(dt);
      stage.frame({ layers: keys });
    });
    (window as unknown as { __game: unknown }).__game = { stage, renderer: r };
    return;
  }

  const keys = GAME_LAYERS.filter((k) => man.layers[k]);
  const audio = new AudioEngine();
  await audio.load();
  for (const [i, k] of keys.entries()) {
    r.addLayer(await loadLayer(r.gl, man, k));
    screens.loading((i + 1) / (keys.length + 1));
  }
  const assets = await loadNightAssets(r.gl);
  screens.clear();
  const app = new App(stage, audio, new Sfx(audio), canvas, ui, assets, save, lang);
  app.begin();
  // ?step: niente ciclo continuo, il tempo avanza solo con __game.step (catture fotogramma per fotogramma)
  if (!params.has('step')) loop((dt) => app.frame(dt));
  const step = (dt: number, n = 1) => {
    for (let i = 0; i < n; i++) app.frame(dt);
  };
  (window as unknown as { __game: unknown }).__game = { app, stage, renderer: r, audio, step };
}

boot().catch((e) => {
  console.error(e);
  ui.textContent = String(e);
});
