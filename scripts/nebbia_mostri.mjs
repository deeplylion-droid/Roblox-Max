// Prova dell'opzione «Nebbia» sui mostri: le pose nel visore con le due serie e la lampara spenta, bassa e alta, e il
// cambio di serie a notte in corso. Uso: node scripts/nebbia_mostri.mjs <cartella> <chiave>[,<toppa>…] [...]
// (con npx vite su localhost:5173)
import { chromium } from 'playwright-core';

const [out, ...gruppi] = process.argv.slice(2);
const base = 'http://localhost:5173/';
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});
const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
const errori = [];
page.on('pageerror', (e) => errori.push(e.message));
page.on('console', (m) => m.type() === 'warning' || m.type() === 'error' ? errori.push(m.text()) : null);
const man = await (await fetch(base + 'assets/img/manifest.json')).json();
for (const g of gruppi) {
  const keys = g.split(',');
  const e = man.layers[keys[0]];
  for (const senza of [true, false]) {
    for (const lamp of [0, 1, 2]) {
      const url = `${base}?viewer&extra=${g}&yaw=${e.yaw.toFixed(1)}&pitch=-4&lamp=${lamp}${senza ? '&senza' : ''}`;
      await page.goto(url, { waitUntil: 'load' });
      await page.waitForFunction(() => window.__game, null, { timeout: 60000 });
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${out}/${keys[0]}_${senza ? 'senza' : 'nebbia'}_${lamp}.png` });
    }
  }
}
// il cambio a notte in corso: tutti gli strati con la voce senza passano all'altra serie, gli altri restano
await page.goto(base + '?notte=1', { waitUntil: 'load' });
await page.waitForFunction(() => window.__game?.app, null, { timeout: 120000 });
const serie = () =>
  page.evaluate(() => {
    const r = window.__game.renderer;
    const o = {};
    for (const [k, l] of r.layers) if (l.info.senza) o[k] = l.info.passes.ambient.file;
    const js = window.__game.app.assets?.jumpscares ?? {};
    return { strati: o, js: Object.keys(js).length };
  });
const prima = await serie();
for (const on of [true, false, true]) {
  await page.evaluate((on) => {
    const a = window.__game.app;
    a.save.options.fog = on;
    a.applyOptions();
    a.swapFog(on);
    return a.fogSwap;
  }, on);
  console.log('nebbia', on, JSON.stringify(await serie()));
}
console.log('prima', JSON.stringify(prima));
console.log('errori', errori.slice(0, 10).join(' | ') || 'nessuno');
await browser.close();
