// L'ANIMATORE nel binocolo: foto del gioco vero con il binocolo alzato sui luoghi proposti, con le immagini
// rifatte da foxy_binocolo.py sostituite al volo (public/ non si tocca). Per ogni luogo e stadio una foto a
// zoom massimo; poi la tavola docs/concept/foxy_binocolo.jpg si monta con foxy_binocolo_tavola.py.
// Uso (con il server di sviluppo già acceso: npx vite --port 5197):
//   node tools/render/foxy_binocolo_cattura.mjs [http://localhost:5197] [luoghi=scivoli,relitto]
import { chromium } from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';

const [base = 'http://localhost:5197', luoghi = 'scivoli,relitto'] = process.argv.slice(2);
const DIR = path.resolve('tools/render/cache/foxy/bino');
const STADI = ['lontano', 'vicino', 'vuoto'];
const MIRE = JSON.parse(fs.readFileSync(path.join(DIR, 'mire.json'), 'utf8'));
// FOXY_DEF=<cartella>: le viste definitive di foxy_binocolo.py --definitivo (RENDER_OUT=<cartella>): bino_<luogo>.webp
// (vuoto), _foxy0 (lontano), _foxy1 (vicino), con la loro scala in bino_foxy_entries.json
const DEF = process.env.FOXY_DEF;
const DEF_FILE = { lontano: '_foxy0', vicino: '_foxy1', vuoto: '' };
const DEF_SCALE = DEF ? Object.fromEntries(JSON.parse(fs.readFileSync(path.join(DEF, 'bino_foxy_entries.json'), 'utf8')).map((e) => [e.key, e.scale])) : {};

const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});

for (const luogo of luoghi.split(',')) {
  for (const stadio of STADI) {
    const file = DEF ? path.join(DEF, `bino_${luogo}${DEF_FILE[stadio]}.webp`) : path.join(DIR, `bino_${luogo}_${stadio}.webp`);
    if (!fs.existsSync(file)) {
      console.log('manca', file);
      continue;
    }
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    page.on('pageerror', (e) => console.log('[pageerror]', e.message));
    await page.route(`**/bino_${luogo}.webp*`, (r) => r.fulfill({ path: file, contentType: 'image/webp' }));
    if (DEF) {
      await page.route('**/overlays.json*', async (r) => {
        const res = await r.fetch();
        const j = await res.json();
        for (const p of j.binocular.places) if (p.key in DEF_SCALE) p.scale = DEF_SCALE[p.key];
        await r.fulfill({ response: res, json: j });
      });
    }
    // ?notte=2: il mostro arriva dalla seconda notte; ?step: il tempo avanza solo quando lo diciamo noi
    await page.goto(`${base}/?notte=2&step`, { waitUntil: 'load' });
    await page.waitForFunction(() => window.__game?.step, null, { timeout: 600000, polling: 500 });
    // l'avviso iniziale («premi un tasto»), poi il titolo
    const nuova = page.getByText(/^(Nuova partita|New game)$/).first();
    for (let i = 0; i < 60 && !(await nuova.isVisible()); i++) {
      await page.keyboard.press('Space');
      await page.evaluate(() => window.__game.step(0.05, 10));
      await page.waitForTimeout(300);
    }
    await nuova.click({ timeout: 60000 });
    // l'intro dura qualche secondo: si fa avanzare il tempo a passi
    for (let i = 0; i < 200; i++) {
      const ok = await page.evaluate(() => !!window.__game.app.night);
      if (ok) break;
      await page.evaluate(() => window.__game.step(0.05, 4));
    }
    await page.evaluate((luogo) => {
      const n = window.__game.app.night;
      const p = n.d.assets.binocular.places.find((q) => q.key === luogo);
      const v = n.d.stage.view;
      v.yaw = v.targetYaw = p.yaw;
      n.raiseBino(true);
      n.binoFov = 4.5;
      n.binoPitch = p.pitch;
    }, luogo);
    await page.evaluate(() => window.__game.step(0.05, 30));
    // il binocolo, quando lo sguardo è fermo, scivola da solo sul centro del luogo: lo si punta sul mostro
    // (mire.json, da foxy_binocolo.py --mire) e si fa un solo passo brevissimo, che non lo sposta
    await page.evaluate((m) => {
      const n = window.__game.app.night;
      const v = n.d.stage.view;
      v.yaw = v.targetYaw = m.yaw;
      n.binoPitch = m.pitch;
      // per la foto si ferma il dondolio della barca (nel gioco le mani ne compensano solo una parte)
      v.swell = 0;
      v.rockBoost = 0;
      window.__game.step(0.001, 2);
    }, MIRE[`${luogo}_${stadio}`]);
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(DIR, `gioco${DEF ? '_def' : ''}_${luogo}_${stadio}.png`), timeout: 600000 });
    console.log('ok', luogo, stadio);
    await page.close();
  }
}
await browser.close();
