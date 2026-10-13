// Gli screenshot della pagina Steam (approvati il 13 ottobre): 1920×1080, nebbia accesa, presi dal gioco. Le scene
// della notte e dell'immersione sono la tela del motore, senza HUD; il Catalogo è la schermata intera, in inglese.
// I mostri sono messi in posa a mano (le loro animazioni ferme a un punto), la vista puntata dove serve.
// Escono in steam/screenshot/ nell'ordine della pagina (vedi steam/LEGGIMI.md).
// Uso: node scripts/steam_screenshot.mjs [url]   (url di partenza: http://localhost:5173/, con `npm run dev`)
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const base = (process.argv[2] ?? 'http://localhost:5173/').replace(/\/?$/, '/');
const out = 'steam/screenshot';
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({
  executablePath: process.env.CHROME ?? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const errors = [];

/** Una pagina del gioco in inglese, con la nebbia accesa, pronta per essere comandata (?step). */
async function gioco(night) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', (e) => errors.push(e.message));
  await page.addInitScript((night) => {
    localStorage.setItem('splashland.save.v1', JSON.stringify({ version: 1, rev: 2, lang: 'en', night, current: night, options: { quality: 1, fog: true, tutorial: false } }));
  }, night);
  await page.goto(`${base}?step`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__game?.step, null, { timeout: 300000, polling: 250 });
  return page;
}

/** La tela del motore come JPEG (qualità 95). */
async function tela(page, nome) {
  const url = await page.evaluate(() => {
    window.__game.step(0.0001);
    return document.querySelector('canvas').toDataURL('image/jpeg', 0.95);
  });
  fs.writeFileSync(`${out}/${nome}.jpg`, Buffer.from(url.split(',')[1], 'base64'));
  console.log(nome);
}

// ── la notte: la quinta, che ha tutti i mostri; tutti fermi, poi ognuno in posa dove serve ──
let page = await gioco(6);
await page.evaluate(() => {
  const g = window.__game;
  const a = g.app;
  a.title();
  a.intro(5);
  a.startNight();
  g.step(0.1, 45);
  const n = a.night;
  const s = n.sim;
  for (const k of ['gulpy', 'molly', 'hatch', 'robin', 'archie', 'lampy', 'fangy', 'foxy', 'mother']) if (s[k] && 'timer' in s[k]) s[k].timer = 1e9;
  if (s.foxy) s.foxy.update = () => {};
  const uv = n.updateVisuals.bind(n);
  n.updateVisuals = (dt) => {
    uv(dt);
    if (window.__posa) Object.assign(n.v, window.__posa);
  };
  const st = g.stage;
  const su = st.update.bind(st);
  st.update = (dt) => {
    if (window.__vista) Object.assign(st.view, window.__vista);
    su(dt);
  };
});
/** posa: i valori della grafica dei mostri; vista: yaw, pitch, campo; bino: il posto del binocolo; soggy: dove sta. */
const NOTTE = [
  ['01_molly', { posa: { mR: 0.9 }, vista: { yaw: 70, pitch: -9, hfov: 66 } }],
  ['02_hatch', { posa: { hRise: 0.9 }, vista: { yaw: 178, pitch: -2, hfov: 62 } }],
  ['03_binocolo_ingresso', { bino: { yaw: 166.985, pitch: 2.373 } }],
  ['05_archie', { posa: { aRise: 0.9 }, vista: { yaw: 8, pitch: 4, hfov: 62 } }],
  ['06_binocolo_soggy_al_relitto', { bino: { yaw: 13.955, pitch: 0.42 }, soggy: 'relitto' }],
];
for (const [nome, c] of NOTTE) {
  await page.evaluate((c) => {
    const g = window.__game;
    const n = g.app.night;
    const s = n.sim;
    window.__posa = c.posa ?? {};
    if (c.bino) {
      window.__vista = { yaw: c.bino.yaw, targetYaw: c.bino.yaw };
      n.binoUp = true;
      n.bino = 1;
      n.binoPitch = c.bino.pitch;
    } else {
      window.__vista = { ...c.vista, targetYaw: c.vista.yaw };
      n.binoUp = false;
      n.bino = 0;
    }
    if (s.foxy) {
      if (c.soggy) {
        s.foxy.state = 'leaning';
        s.foxy.place = s.foxy.places.findIndex((q) => q.id === c.soggy);
      } else s.foxy.state = 'dormant';
    }
    s.setLamp(2);
    g.step(0.05, 30);
  }, c);
  await tela(page, nome);
}
await page.close();

// ── il Catalogo, aperto sulla prima pagina degli scheletrici (tutti i pesci presi) ──
page = await gioco(1);
await page.evaluate(async () => {
  const C = await import('/src/game/catalog.ts');
  const app = window.__game.app;
  window.__game.step(1 / 30, 5);
  const caught = Object.fromEntries(C.FISH.map((f, k) => [f.id, { count: 1 + (k % 4), bestKg: f.kg[0] + (f.kg[1] - f.kg[0]) * 0.7 }]));
  app.screens.catalog({ caught, images: app.assets.fish, revealAll: false, onBack: () => {} });
  document.querySelector('.book-tabs .tab[data-k="1"]').click();
  document.querySelectorAll('.page.left .snap')[0].click();
});
await page.waitForTimeout(2500);
await page.screenshot({ path: `${out}/07_catalogo.jpg`, type: 'jpeg', quality: 95, timeout: 600000 });
console.log('07_catalogo');

// ── l'immersione dopo la prima notte: la tana di Molly e la grotta sotto la barca ──
await page.evaluate(() => {
  const g = window.__game;
  const a = g.app;
  a.title();
  a.intro(1);
  a.startNight();
  g.step(0.1, 45);
  const s = a.night.sim;
  for (const k of ['gulpy', 'molly', 'hatch']) if (s[k]) s[k].timer = 1e9;
  s.fish = s.cfg.quota + 2;
  s.caught = s.fish;
  s.time = s.nightLength - 0.3;
  g.step(0.05, 400);
  a.dive(2);
});
/** aspetta che l'immersione sia ferma in un posto (si guarda attorno) */
const pronta = async () => {
  for (let i = 0; i < 180; i++) {
    if (await page.evaluate(() => window.__game.app.diving?.phase === 'look')) return;
    await page.evaluate(() => window.__game.step(0.05, 10));
  }
  throw new Error("l'immersione non arriva");
};
await pronta();
for (const [posto, nome] of [['grotta_grande', '08_grotta_sotto_la_barca'], ['tana_molly', '04_tana_di_molly']]) {
  await page.evaluate((posto) => window.__game.app.diving.go(posto), posto);
  await page.evaluate(() => window.__game.step(0.05, 40));
  await pronta();
  await page.evaluate(() => window.__game.step(0.05, 60));
  await tela(page, nome);
}
await browser.close();
if (errors.length) console.log(`errori nella pagina:\n${[...new Set(errors)].join('\n')}`);
process.exit(errors.length ? 1 : 0);
